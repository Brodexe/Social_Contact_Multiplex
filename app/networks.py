"""
Contact / social network construction for the interactive viewer.

A scenario picks one contact model and one social model independently:

  contact  "er"         Erdos-Renyi G(n, p)
           "clustered"  same density as G(n, p), but a `clustering` share of the
                        edges are placed by triadic closure (closing a triangle on a
                        random path u-v-w), so clustering can be dialled up from ER's
           "hs_bin"     one non-empty time bin of the high-school contact data

  social   "khop"       correlated_graphs.create_social_graph: pairs sampled by rank
                        of their K-hop ego-network Jaccard similarity on the contact
                        graph, `density` x (all pairs) ties
           "correlated" edge-level correlation c in [-1, 1] with the contact graph:
                        c = 1 copies the contact edges, c = -1 takes exactly the
                        non-edges (the complement), c = 0 is independent at the
                        contact graph's density, and in between each pair is drawn
                        with a probability interpolating those cases (see below)
           "hs_survey"  the high-school friendship survey

Node counts must agree across the two layers (people are matched by index), and
build() raises NetworkMismatchError when they don't. The one exception is a
high-school contact bin paired with the survey: both come from the same student
IDs, so they're aligned on the students present in both (as in
adaptive_seed_selection.initialize).
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


class NetworkMismatchError(ValueError):
    pass


# ------------------------------------------------------------------ contact ---

def er_graph(n, p, seed):
    return nx.erdos_renyi_graph(n, p, seed=seed)


def clustered_graph(n, p, clustering, seed):
    """Random graph with G(n, p)'s expected edge count, round(p * n(n-1)/2), where each
    new edge closes a triangle with probability `clustering` and is a uniformly random
    pair otherwise. clustering = 0 is G(n, m); raising it raises the clustering
    coefficient while keeping density fixed."""
    rng = random.Random(seed)
    m = round(p * n * (n - 1) / 2)
    G = nx.empty_graph(n)
    edges = []

    def add(u, v):
        if u != v and not G.has_edge(u, v):
            G.add_edge(u, v)
            edges.append((u, v))
            return True
        return False

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
            # random edge instead, so early sparse stages and saturated neighbourhoods
            # still make progress
        add(rng.randrange(n), rng.randrange(n))
    return G


@lru_cache(maxsize=None)
def _hs_bin_raw(b):
    G = nx.read_gml(f"{HS_DIR}/high_school_contact_bin{b}.gml")
    G.remove_nodes_from([u for u in list(G.nodes()) if G.degree(u) == 0])
    return G


@lru_cache(maxsize=None)
def _hs_social_raw():
    return nx.read_gml(HS_SOCIAL_PATH)


def hs_info():
    """Node counts per bin (alone, and aligned with the survey), and the survey's size."""
    social = _hs_social_raw()
    bins = []
    for b in HS_BINS:
        G = _hs_bin_raw(b)
        bins.append({"bin": b, "n": G.number_of_nodes(), "edges": G.number_of_edges(),
                     "n_with_survey": sum(1 for u in G if social.has_node(u))})
    return {"bins": bins, "survey_n": social.number_of_nodes()}


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
        "clustered": f"Clustered random (n={cfg.contact_n}, p={cfg.contact_p:g}, clustering={cfg.clustering:g})",
        "hs_bin": f"High school contact bin {cfg.hs_bin}",
    }[cfg.contact_model]
    social = {
        "khop": f"{cfg.khop_k}-hop similarity social (density {cfg.social_density:g})",
        "correlated": f"correlated social (c={cfg.correlation:g})",
        "hs_survey": "high school survey social",
    }[cfg.social_model]
    return f"{contact} + {social}"


def build(cfg):
    """Return (contact Graph, social DiGraph, node display names, heterogeneous beta map),
    both graphs on nodes 0..n-1."""
    seed = cfg.net_seed

    # Contact layer
    if cfg.contact_model == "hs_bin":
        if cfg.hs_bin not in HS_BINS:
            raise ValueError(f"High school bin {cfg.hs_bin} has no contacts; choose one of {HS_BINS}")
        raw = _hs_bin_raw(cfg.hs_bin)
        if cfg.social_model == "hs_survey":
            survey = _hs_social_raw()
            order = [u for u in raw.nodes() if survey.has_node(u)]
            contact, social = _relabel(raw, order), _relabel(survey, order)
        else:
            order = list(raw.nodes())
            contact, social = _relabel(raw, order), None
        names = [f"Student {u}" for u in order]
    else:
        if cfg.contact_model == "er":
            contact = er_graph(cfg.contact_n, cfg.contact_p, seed)
        else:
            contact = clustered_graph(cfg.contact_n, cfg.contact_p, cfg.clustering, seed)
        names = [str(u) for u in range(cfg.contact_n)]
        social = None

    n_contact = contact.number_of_nodes()

    # Social layer (the hs_bin + hs_survey pair was aligned above)
    if social is None:
        if cfg.social_model == "hs_survey":
            survey = _hs_social_raw()
            n_social = survey.number_of_nodes()
        else:
            n_social = cfg.social_n
        if n_social != n_contact:
            fix = (f"the survey has a fixed {n_social} students, so set the contact network's "
                   f"nodes to {n_social}" if cfg.social_model == "hs_survey" else
                   f"set the social network's nodes to {n_contact}")
            raise NetworkMismatchError(
                f"Node counts don't match: the contact network has {n_contact} nodes but the "
                f"social network has {n_social}; {fix}.")
        if cfg.social_model == "hs_survey":
            order = list(survey.nodes())
            social = _relabel(survey, order)
            names = [f"Student {u}" for u in order]
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
