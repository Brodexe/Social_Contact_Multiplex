"""
Contact / social network construction for the interactive viewer.

A scenario picks one contact model and one social model independently:

  contact  "er"         Erdos-Renyi G(n, p)
           "sbm"        stochastic block model with G(n, p)'s edge count: `sbm_blocks`
                        clusters, a `sbm_mixing` share of the block-model edges running
                        between clusters, and a `clustering` share of all edges placed by
                        triadic closure, so community structure and the clustering
                        coefficient are set independently (see sbm_graph)
           "hs_bin"     one non-empty time bin of the high-school contact data
           "rc_bin"     one time bin of the Reality Commons (MIT Social Evolution)
                        proximity data, rc_weighted_contact_bin{i}.gml: each edge's
                        weight is the share of the other bins that also contain it

  social   "khop"       correlated_graphs.create_social_graph: pairs sampled by rank
                        of their K-hop ego-network Jaccard similarity on the contact
                        graph, `density` x (all pairs) ties
           "correlated" edge-level correlation c in [-1, 1] with the contact graph:
                        c = 1 copies the contact edges, c = -1 takes exactly the
                        non-edges (the complement), c = 0 is independent at the
                        contact graph's density, and in between each pair is drawn
                        with a probability interpolating those cases (see below)
           "hs_survey"  the high-school friendship survey
           "rc_survey"  the Reality Commons relationship survey, rc_social_network.gml
                        (directed, weighted by relationship type; see RC_TIE_TYPES)

Node counts must agree across the two layers (people are matched by index), and
build() raises NetworkMismatchError when they don't. The exceptions are a real
contact bin paired with its own survey (high-school bin + survey, Reality Commons
bin + survey): both come from the same participant IDs, so they're aligned on the
people present in both (as in adaptive_seed_selection.initialize).
"""

import random
from functools import lru_cache

import networkx as nx
import numpy as np

import correlated_graphs
import network_setup

HS_DIR = "capstone_proj_data"
HS_SOCIAL_PATH = f"{HS_DIR}/high_school_social.gml"
# Bins 2, 3, 7, 8, 11, 12, 16 and 17 of the 19 time bins contain no contacts
HS_BINS = [1, 4, 5, 6, 9, 10, 13, 14, 15, 18, 19]

RC_SOCIAL_PATH = f"{HS_DIR}/rc_social_network.gml"
# Bins 1, 2, 4, 6, 7 and 19 have five or fewer people with any contact
RC_BINS = [3, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

# Reality Commons survey relationship types and the weights mit_rc_network_creation.py
# gives them, strongest relationship first. Weights represent cascade probabilities. A
# pair reporting several types takes the maximum weight, not the sum: close friendship
# is already a strong relationship and is explicit in the data. Ties run nominee ->
# nominator: if A names B, the arrow is B -> A.
RC_TIE_TYPES = [
    {"type": "CloseFriend", "label": "Close friend", "weight": 0.09},
    {"type": "SocializeTwicePerWeek", "label": "Socializes twice a week", "weight": 0.07},
    {"type": "PoliticalDiscussant", "label": "Political discussant", "weight": 0.05},
    {"type": "FacebookAllTaggedPhotos", "label": "Tagged together on Facebook", "weight": 0.03},
    {"type": "BlogLivejournalTwitter", "label": "Blog / LiveJournal / Twitter", "weight": 0.01},
]
RC_TIE_NOTE = ("Weights represent cascade probabilities. A pair reporting several relationship types gets "
               "the strongest one's weight (the maximum, not the sum), since a close friendship is already "
               "a strong relationship and is explicit in the data. Ties run nominee → nominator: if A "
               "names B, the arrow is B → A.")


class NetworkMismatchError(ValueError):
    pass


# ------------------------------------------------------------------ contact ---

def er_graph(n, p, seed):
    return nx.erdos_renyi_graph(n, p, seed=seed)


def sbm_blocks(n, blocks):
    """Block index of each node: `blocks` contiguous, near-equal blocks."""
    blocks = max(1, min(blocks, n))
    return [min(blocks - 1, u * blocks // n) for u in range(n)]


def sbm_graph(n, p, blocks, mixing, clustering, seed):
    """Stochastic block model with G(n, p)'s expected edge count, round(p * n(n-1)/2),
    whose community structure and clustering coefficient are set separately.

    Nodes fall into `blocks` near-equal clusters. Each new edge closes a triangle (on a
    random path u-v-w) with probability `clustering`; otherwise it is a block-model
    pair: between two clusters with probability `mixing`, else inside one cluster
    (chosen in proportion to its number of pairs). So `blocks` sets how many clusters
    there are, `mixing` how separated they are (0: none between, 1 - 1/blocks: no
    structure), and `clustering` how likely a node's neighbours are to know each
    other, all at a fixed density. Triadic closure mostly stays inside a cluster, so
    it sharpens communities slightly too. Each node's block is stored as `block`."""
    rng = random.Random(seed)
    m = min(round(p * n * (n - 1) / 2), n * (n - 1) // 2)
    block = sbm_blocks(n, blocks)
    members = {}
    for u, b in enumerate(block):
        members.setdefault(b, []).append(u)
    groups = [g for g in members.values() if len(g) > 1]
    pair_counts = [len(g) * (len(g) - 1) / 2 for g in groups]
    multi = len(members) > 1

    G = nx.empty_graph(n)
    nx.set_node_attributes(G, {u: b for u, b in enumerate(block)}, "block")
    edges = []

    def add(u, v):
        if u != v and not G.has_edge(u, v):
            G.add_edge(u, v)
            edges.append((u, v))
            return True
        return False

    def block_pair():
        if multi and (not groups or rng.random() < mixing):
            u = rng.randrange(n)
            while True:
                v = rng.randrange(n)
                if block[v] != block[u]:
                    return u, v
        g = rng.choices(groups, weights=pair_counts)[0]
        u, v = rng.sample(g, 2)
        return u, v

    misses = 0
    while len(edges) < m:
        if edges and rng.random() < clustering:
            u, v = edges[rng.randrange(len(edges))]
            if rng.random() < 0.5:
                u, v = v, u
            nbrs = list(G.adj[u])
            w = nbrs[rng.randrange(len(nbrs))]
            if add(v, w):
                continue
            # No open path here (w == v, or the triangle is already closed): place a
            # block-model edge instead, so sparse starts and saturated neighbourhoods
            # still make progress
        # Once the clusters are nearly full (dense p with little mixing), fall back to
        # uniform pairs rather than retrying forever
        u, v = block_pair() if misses < 200 else (rng.randrange(n), rng.randrange(n))
        misses = 0 if add(u, v) else misses + 1
    return G


@lru_cache(maxsize=None)
def _hs_bin_raw(b):
    G = nx.read_gml(f"{HS_DIR}/high_school_contact_bin{b}.gml")
    G.remove_nodes_from([u for u in list(G.nodes()) if G.degree(u) == 0])
    return G


@lru_cache(maxsize=None)
def _hs_social_raw():
    return nx.read_gml(HS_SOCIAL_PATH)


@lru_cache(maxsize=None)
def _rc_bin_raw(b):
    # Isolated participants dropped, as adaptive_seed_selection.initialize does
    G = nx.read_gml(f"{HS_DIR}/rc_weighted_contact_bin{b}.gml")
    G.remove_nodes_from([u for u in list(G.nodes()) if G.degree(u) == 0])
    return G


@lru_cache(maxsize=None)
def _rc_social_raw():
    return nx.read_gml(RC_SOCIAL_PATH)


def _bin_info(bins, raw, survey):
    return [{"bin": b, "n": raw(b).number_of_nodes(), "edges": raw(b).number_of_edges(),
             "n_with_survey": sum(1 for u in raw(b) if survey.has_node(u))} for b in bins]


def hs_info():
    """Node counts per bin (alone, and aligned with the survey), and the survey's size."""
    social = _hs_social_raw()
    return {"bins": _bin_info(HS_BINS, _hs_bin_raw, social), "survey_n": social.number_of_nodes()}


def rc_info():
    """As hs_info, for Reality Commons, plus the survey's relationship-type weights."""
    social = _rc_social_raw()
    return {"bins": _bin_info(RC_BINS, _rc_bin_raw, social), "survey_n": social.number_of_nodes(),
            "tie_types": RC_TIE_TYPES, "tie_note": RC_TIE_NOTE}


def rc_tie_type(weight):
    """The relationship type a Reality Commons tie weight stands for (weights are distinct)."""
    return min(RC_TIE_TYPES, key=lambda t: abs(t["weight"] - weight))["type"]


# ------------------------------------------------------------------- social ---

def khop_social(contact, k, density, seed):
    n = contact.number_of_nodes()
    pairs = n * (n - 1) // 2
    nE = min(pairs, round(density * pairs))
    # create_social_graph draws from the global RNGs, as in network_setup
    random.seed(seed)
    np.random.seed(seed)
    social, _ = correlated_graphs.create_social_graph(contact, nE, K=k)
    return social


def correlated_social(contact, c, seed):
    """Social graph whose edges correlate with the contact graph's at level c.

    With q the contact density and e the indicator that a pair is a contact edge,
    each pair becomes a (two-way) social tie independently with probability
        c >= 0:  e ? c + (1-c) q : (1-c) q        (keep contact edges, plus noise)
        c <  0:  e ? (1-|c|) q   : |c| + (1-|c|) q (prefer non-edges)
    so c = 1 reproduces the contact edges, c = -1 the complement, c = 0 is G(n, q)."""
    n = contact.number_of_nodes()
    A = nx.to_numpy_array(contact, nodelist=range(n)) > 0
    iu, ju = np.triu_indices(n, 1)
    e = A[iu, ju]
    q = e.mean() if len(e) else 0.0
    if c >= 0:
        prob = np.where(e, c + (1 - c) * q, (1 - c) * q)
    else:
        a = -c
        prob = np.where(e, (1 - a) * q, a + (1 - a) * q)
    keep = np.random.default_rng(seed).random(len(prob)) < prob
    G = nx.DiGraph()
    G.add_nodes_from(range(n))
    for u, v in zip(iu[keep].tolist(), ju[keep].tolist()):
        G.add_edge(u, v)
        G.add_edge(v, u)
    return G


# -------------------------------------------------------------------- build ---

def _relabel(G, order):
    return nx.relabel_nodes(G.subgraph(order).copy(), {u: i for i, u in enumerate(order)})


def describe(cfg):
    contact = {
        "er": f"ER random (n={cfg.contact_n}, p={cfg.contact_p:g})",
        "sbm": (f"SBM (n={cfg.contact_n}, p={cfg.contact_p:g}, {cfg.sbm_blocks} clusters, "
                f"mixing {cfg.sbm_mixing:g}, closure {cfg.clustering:g})"),
        "hs_bin": f"High school contact bin {cfg.hs_bin}",
        "rc_bin": f"Reality Commons contact bin {cfg.rc_bin}",
    }[cfg.contact_model]
    social = {
        "khop": f"{cfg.khop_k}-hop similarity social (density {cfg.social_density:g})",
        "correlated": f"correlated social (c={cfg.correlation:g})",
        "hs_survey": "high school survey social",
        "rc_survey": "Reality Commons survey social",
    }[cfg.social_model]
    return f"{contact} + {social}"


# Real-data contact layers, each with the survey drawn from the same participant IDs:
# contact_model -> (valid bins, bin loader, social_model, survey loader, name prefix)
REAL = {
    "hs_bin": (HS_BINS, _hs_bin_raw, "hs_survey", _hs_social_raw, "Student"),
    "rc_bin": (RC_BINS, _rc_bin_raw, "rc_survey", _rc_social_raw, "Participant"),
}
SURVEYS = {"hs_survey": (_hs_social_raw, "Student"), "rc_survey": (_rc_social_raw, "Participant")}


def build(cfg):
    """Return (contact Graph, social DiGraph, node display names, heterogeneous beta map),
    both graphs on nodes 0..n-1."""
    seed = cfg.net_seed

    # Contact layer
    if cfg.contact_model in REAL:
        bins, bin_raw, own_survey, survey_raw, prefix = REAL[cfg.contact_model]
        b = cfg.hs_bin if cfg.contact_model == "hs_bin" else cfg.rc_bin
        if b not in bins:
            raise ValueError(f"Contact bin {b} has too few contacts; choose one of {bins}")
        raw = bin_raw(b)
        if cfg.social_model == own_survey:
            survey = survey_raw()
            order = [u for u in raw.nodes() if survey.has_node(u)]
            contact, social = _relabel(raw, order), _relabel(survey, order)
        else:
            order = list(raw.nodes())
            contact, social = _relabel(raw, order), None
        names = [f"{prefix} {u}" for u in order]
    else:
        if cfg.contact_model == "er":
            contact = er_graph(cfg.contact_n, cfg.contact_p, seed)
        else:
            contact = sbm_graph(cfg.contact_n, cfg.contact_p, cfg.sbm_blocks, cfg.sbm_mixing,
                                cfg.clustering, seed)
        names = [str(u) for u in range(cfg.contact_n)]
        social = None

    n_contact = contact.number_of_nodes()

    # Social layer (a real bin + its own survey was aligned above)
    if social is None:
        if cfg.social_model in SURVEYS:
            survey_raw, prefix = SURVEYS[cfg.social_model]
            survey = survey_raw()
            n_social = survey.number_of_nodes()
        else:
            n_social = cfg.social_n
        if n_social != n_contact:
            fix = (f"the survey has a fixed {n_social} people, so set the contact network's "
                   f"nodes to {n_social}" if cfg.social_model in SURVEYS else
                   f"set the social network's nodes to {n_contact}")
            raise NetworkMismatchError(
                f"Node counts don't match: the contact network has {n_contact} nodes but the "
                f"social network has {n_social}; {fix}.")
        if cfg.social_model in SURVEYS:
            order = list(survey.nodes())
            social = _relabel(survey, order)
            names = [f"{prefix} {u}" for u in order]
        elif cfg.social_model == "khop":
            social = khop_social(contact, cfg.khop_k, cfg.social_density, seed)
        else:
            social = correlated_social(contact, cfg.correlation, seed)

    # IM's diffusion walks successors(); an undirected tie counts in both directions
    if not social.is_directed():
        social = social.to_directed()
    social.add_nodes_from(range(n_contact))

    betas = network_setup.laplacian_smooth_beta(
        contact, network_setup.beta_L, network_setup.beta_R, lam=network_setup.Gamma, seed=seed)
    return contact, social, names, betas
