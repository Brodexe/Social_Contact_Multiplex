"""
Simulation state behind the interactive viewer, independent of how it is served.

app/server.py exposes this over HTTP (FastAPI, one Workspace of up to
MAX_MULTIPLEXES Sessions per browser tab);
app/browser_api.py exposes it to the static build, where it runs inside the
visitor's browser under Pyodide. Network/dataset paths are relative to the repo
root, so the working directory must be the repo root (or the unpacked bundle).
"""

import math
import random
from copy import deepcopy
from functools import lru_cache
from typing import Literal, Optional

import networkx as nx
import numpy as np
from pydantic import BaseModel, Field

from app import networks, seeding
from app.engine import MultiplexSIRS
from app.seeding import SeedPolicyRun

# Fields that determine the two networks (everything else is dynamics); the built
# networks and their layouts/metrics are cached on these.
NETWORK_FIELDS = ("contact_model", "contact_n", "contact_p", "clustering", "sbm_blocks",
                  "sbm_mixing", "hs_bin", "rc_bin", "social_model", "social_n", "khop_k",
                  "social_density", "correlation", "net_seed")
MAX_NODES = 400
MAX_MULTIPLEXES = 3


# Bounds keep a public deployment from being asked for arbitrarily expensive runs.
# Network fields are described in app/networks.py.
class ScenarioConfig(BaseModel):
    contact_model: Literal["er", "sbm", "hs_bin", "rc_bin"] = "er"
    contact_n: int = Field(200, ge=10, le=MAX_NODES)
    contact_p: float = Field(0.05, ge=0, le=1)
    # sbm only: number of clusters, share of block-model edges between clusters, and
    # share of all edges placed by triadic closure
    sbm_blocks: int = Field(4, ge=1, le=20)
    sbm_mixing: float = Field(0.1, ge=0, le=1)
    clustering: float = Field(0.3, ge=0, le=1)
    hs_bin: int = Field(1, ge=1, le=19)             # only for contact_model == "hs_bin"
    rc_bin: int = Field(15, ge=1, le=19)            # only for contact_model == "rc_bin"
    social_model: Literal["khop", "correlated", "hs_survey", "rc_survey"] = "khop"
    social_n: int = Field(200, ge=10, le=MAX_NODES)  # khop / correlated; must match the contact network
    khop_k: int = Field(2, ge=1, le=6)
    social_density: float = Field(0.1, ge=0, le=1)  # khop: share of all pairs that are ties
    correlation: float = Field(0.5, ge=-1, le=1)    # correlated: c
    net_seed: int = 42
    mechanism: Literal["ic", "lt", "FJ"] = "ic"
    mech_val: float = Field(0.02, ge=0, le=1000)    # IC p, LT threshold, or FJ kappa
    # IC only, weighted social layers only (the Reality Commons survey): use each tie's
    # weight as its own cascade probability instead of the single p above
    ic_tie_weights: bool = False
    # Competing misinformation (SIR.competing_spread_step). Off by default. With it on,
    # every non-adherer is also a misinformation seed, and only the misinformed don't adhere.
    misinfo: bool = False
    misinfo_seeds: int = Field(5, ge=0, le=MAX_NODES)  # beyond the non-adherers
    misinfo_mode: Literal["takeover", "collide"] = "takeover"
    misinfo_val: Optional[float] = Field(None, ge=0, le=1000)  # None: same as mech_val
    q_mode: Literal["r", "period", "fixed", "off"] = "r"
    q_period: int = Field(14, ge=2, le=1000)        # only used when q_mode == "fixed"
    adherence: float = Field(0.8, ge=0, le=1)
    seeds: int = Field(5, ge=0, le=1000)
    begin_q: int = Field(0, ge=0, le=100000)
    init: float = Field(0.05, ge=0, le=1)
    heterogeneous_beta: bool = True
    beta: float = Field(0.15, ge=0, le=1)           # only used when heterogeneous_beta is False
    gamma: float = Field(0.07, ge=0, le=1)
    mu: float = Field(0.05, ge=0, le=1)
    mc: int = Field(1000, ge=1, le=5000)
    rng_seed: Optional[int] = None
    # Seed selection (app/seeding.py). "none" keeps the single degree^2-weighted seeding
    # at begin_q above; any other strategy re-selects seeds every batch_interval ticks
    # from t = 0, so `seeds` and `begin_q` are unused.
    seed_algo: Literal["none", "hill", "degree", "cob", "random", "milp"] = "none"
    seed_k: Optional[int] = Field(None, ge=0, le=MAX_NODES)  # None: 3/4 of the nodes, as in the research scripts
    batch_interval: int = Field(2, ge=1, le=200)
    info_spread: bool = True                         # info spreads within a batch (else seeds only)
    cost_infections: bool = True
    cost_edges: bool = True
    cost_seeds: bool = False
    cost_baselines: int = Field(10, ge=1, le=50)     # no-quarantine runs normalizing the infection term
    baseline_horizon: int = Field(100, ge=1, le=1000)  # ticks each baseline run covers up front (research T)


# ---------------------------------------------------------------- networks ---

def _normalized_layout(G, seed):
    """Force-directed layout scaled into (roughly) the unit disk."""
    # Each iteration is O(n^2); larger graphs settle well enough in fewer
    pos = nx.spring_layout(G, seed=seed, iterations=300 if G.number_of_nodes() <= 200 else 100)
    return _fit_disc(G.nodes(), [pos[u] for u in G.nodes()])


def _fit_disc(nodes, xy):
    """Center positions and scale them into (roughly) the unit disk."""
    xy = np.array(xy, dtype=float)
    xy -= xy.mean(axis=0)
    r = np.linalg.norm(xy, axis=1)
    xy /= max(np.percentile(r, 97), 1e-9)
    # Pull far-flung outliers (e.g. isolated nodes) back to the rim
    r = np.linalg.norm(xy, axis=1)
    over = r > 1.05
    xy[over] *= (1.05 / r[over])[:, None]
    return {u: [round(float(x), 4), round(float(y), 4)] for u, (x, y) in zip(nodes, xy)}


def _communities(G, seed):
    """Louvain communities, largest first; returns (community index per node, communities)."""
    comms = sorted((sorted(c) for c in nx.community.louvain_communities(G, seed=seed)),
                   key=lambda c: (-len(c), c[0]))
    label = {u: k for k, c in enumerate(comms) for u in c}
    return label, comms


def _cluster_layout(G, comms, seed):
    """Each community as its own island: laid out by force on its own, given an area in
    proportion to its size, and packed out from the centre largest first along a
    golden-angle spiral. People without ties (one-person communities) ring the rim."""
    groups = [c for c in comms if len(c) > 1]
    loners = [c[0] for c in comms if len(c) == 1]
    pos, placed = {}, []
    for k, c in enumerate(groups):
        r = math.sqrt(len(c))
        ang, d = 2.39996 * k, 0.0
        while True:
            cx, cy = d * math.cos(ang), d * math.sin(ang)
            if all(math.hypot(cx - px, cy - py) >= r + pr + 0.8 for px, py, pr in placed):
                break
            d += 0.25
        placed.append((cx, cy, r))
        sp = nx.spring_layout(G.subgraph(c), seed=seed, iterations=60)
        xy = np.array([sp[u] for u in c], dtype=float)
        xy -= xy.mean(axis=0)
        xy *= 0.9 * r / max(float(np.linalg.norm(xy, axis=1).max()), 1e-9)
        for u, (x, y) in zip(c, xy):
            pos[u] = (cx + x, cy + y)
    extent = max((math.hypot(cx, cy) + r for cx, cy, r in placed), default=1.0)
    scale = (0.9 if loners else 1.0) / extent
    out = {u: [round(x * scale, 4), round(y * scale, 4)] for u, (x, y) in pos.items()}
    for k, u in enumerate(loners):
        a = 2 * math.pi * k / len(loners)
        out[u] = [round(1.02 * math.cos(a), 4), round(1.02 * math.sin(a), 4)]
    return out


def _grid_layout(G, comm_of):
    """Everyone on a square grid inside the disc, row by row, ordered by community
    (largest first) and by degree within one, so communities read as contiguous runs."""
    order = sorted(G.nodes(), key=lambda u: (comm_of[u], -G.degree(u), u))
    n = len(order)
    side = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / side)
    step = 1.4 / max(side - 1, 1)
    out = {}
    for k, u in enumerate(order):
        r, c = divmod(k, side)
        out[u] = [round((c - (side - 1) / 2) * step, 4), round(((rows - 1) / 2 - r) * step, 4)]
    return out


def _network_key(cfg):
    return tuple(getattr(cfg, f) for f in NETWORK_FIELDS)


@lru_cache(maxsize=6)
def _static_payload(key):
    cfg = ScenarioConfig(**dict(zip(NETWORK_FIELDS, key)))
    contact, social, names, betas = networks.build(cfg)
    nodes = sorted(contact.nodes())
    n = len(nodes)
    social_u = social.to_undirected()

    contact_core = nx.core_number(nx.Graph(contact))
    social_core = nx.core_number(social_u)
    contact_btw = seeding.betweenness(contact)
    social_btw = seeding.betweenness(social)
    # Overlap: share of social ties (undirected) that are also contacts
    shared = sum(1 for a, b in social_u.edges() if contact.has_edge(a, b))

    contact_g = nx.Graph(contact)
    contact_comm, contact_comms = _communities(contact_g, seed=7)
    social_comm, social_comms = _communities(social_u, seed=11)
    positions = {
        "force": (_normalized_layout(contact, seed=7), _normalized_layout(social_u, seed=11)),
        "cluster": (_cluster_layout(contact_g, contact_comms, seed=7),
                    _cluster_layout(social_u, social_comms, seed=11)),
        "grid": (_grid_layout(contact_g, contact_comm), _grid_layout(social_u, social_comm)),
    }

    contact_edges = [[int(min(a, b)), int(max(a, b))] for a, b in contact.edges()]
    social_edges = [[int(a), int(b)] for a, b in social.edges()]

    payload = {
        "label": networks.describe(cfg),
        "summary": {
            "contact_edges": contact.number_of_edges(),
            "social_ties": social_u.number_of_edges(),
            "contact_clustering": round(nx.average_clustering(contact), 3),
            "social_clustering": round(nx.average_clustering(social_u), 3),
            "overlap": round(shared / max(1, social_u.number_of_edges()), 3),
        },
        "n": n,
        "names": names,
        "contact_edges": contact_edges,
        "social_edges": social_edges,
        # Positions per layout style ("force", "cluster", "grid") and layer
        "layout": {style: {"contact": [c[u] for u in nodes], "social": [s[u] for u in nodes]}
                   for style, (c, s) in positions.items()},
        "communities": {"contact": [contact_comm[u] for u in nodes],
                        "social": [social_comm[u] for u in nodes]},
        "metrics": {
            "contact_degree": [contact.degree(u) for u in nodes],
            "social_in": [social.in_degree(u) for u in nodes],
            "social_out": [social.out_degree(u) for u in nodes],
            "contact_core": [contact_core[u] for u in nodes],
            "social_core": [social_core[u] for u in nodes],
            "contact_btw": [round(contact_btw[u], 5) for u in nodes],
            "social_btw": [round(social_btw[u], 5) for u in nodes],
        },
    }
    if cfg.social_model == "rc_survey":
        # Relationship-type weights (see networks.RC_TIE_TYPES), one per social edge
        payload["social_weights"] = [round(float(d.get("weight", 0)), 3)
                                     for _, _, d in social.edges(data=True)]
        payload["tie_types"] = networks.RC_TIE_TYPES
        payload["tie_note"] = networks.RC_TIE_NOTE
    return payload, contact, social, betas


@lru_cache(maxsize=6)
def _seed_metrics(key):
    """Per-node degree / coreness / betweenness for the seed-selection chart. The social
    values are on the undirected social network, as visualize_adaptive.py computes them."""
    payload, contact, social, _ = _static_payload(key)
    nodes = sorted(contact.nodes())
    social_u = social.to_undirected()
    m = payload["metrics"]
    social_btw = seeding.betweenness(social_u)
    return {
        "social": {
            "degree": [social_u.degree(u) for u in nodes],
            "coreness": m["social_core"],
            "betweenness": [round(social_btw[u], 5) for u in nodes],
        },
        "contact": {
            "degree": m["contact_degree"],
            "coreness": m["contact_core"],
            "betweenness": m["contact_btw"],
        },
    }


# -------------------------------------------------------------- simulation ---

class Session:
    def __init__(self):
        self.sim = None
        self.config = None
        self.static = None
        self.edge_index = None
        self.beta_values = None

    def reset(self, cfg: ScenarioConfig):
        static, contact, social, het_betas = _static_payload(_network_key(cfg))

        # Network construction seeds the global RNGs from net_seed; reseed so the
        # dynamics are either reproducible (rng_seed) or fresh, never tied to net_seed.
        random.seed(cfg.rng_seed)
        np.random.seed(cfg.rng_seed if cfg.rng_seed is not None else None)

        beta = het_betas if cfg.heterogeneous_beta else float(cfg.beta)
        q = {"r": "r", "period": True, "off": False}.get(cfg.q_mode)
        if cfg.q_mode == "fixed":
            q = max(2, int(cfg.q_period))  # Simulate_SIR treats ints > 1 as a fixed period
        mech_val = cfg.mech_val if cfg.mechanism != "lt" else int(round(cfg.mech_val))
        if cfg.ic_tie_weights:
            if cfg.mechanism != "ic" or "social_weights" not in static:
                raise ValueError("Per-tie cascade probabilities need independent cascade and a weighted "
                                 "social network (the Reality Commons relationship survey)")
            # IM.IC_prob_matrix reads p[u, v] for the tie u -> v (as SIR.Simulate_SIR allows)
            mech_val = nx.to_numpy_array(social, nodelist=range(static["n"]), weight="weight")

        misinfo = {}
        if cfg.misinfo:
            mis_val = cfg.misinfo_val
            if mis_val is None:
                mis_val = mech_val  # includes per-tie weights under IC
            elif cfg.mechanism == "lt":
                mis_val = int(round(mis_val))
            misinfo = dict(misinfo=True, misinfo_seeds=int(cfg.misinfo_seeds),
                           misinfo_mode=cfg.misinfo_mode, misinfo_val=mis_val)

        if cfg.seed_algo == "none":
            sim = MultiplexSIRS(
                deepcopy(contact), deepcopy(social),
                beta=beta, gamma=cfg.gamma, mu=cfg.mu, init=cfg.init,
                q=q, q_mech=(cfg.mechanism, mech_val), adherence=float(cfg.adherence),
                begin_q=cfg.begin_q, seeds=int(cfg.seeds), mc=cfg.mc, **misinfo,
            )
        else:
            terms = [t for t in seeding.COST_TERMS if getattr(cfg, f"cost_{t}")]
            if not terms:
                raise ValueError("Pick at least one cost term (infections, edge removals or seeds)")
            sim = SeedPolicyRun(
                deepcopy(contact), deepcopy(social),
                beta=beta, gamma=cfg.gamma, mu=cfg.mu, init=cfg.init,
                q=q, q_mech=(cfg.mechanism, mech_val), adherence=float(cfg.adherence), mc=cfg.mc,
                algorithm=cfg.seed_algo, k=cfg.seed_k, batch_interval=cfg.batch_interval,
                info_spread=cfg.info_spread, cost_terms=terms, baseline_runs=cfg.cost_baselines,
                baseline_horizon=cfg.baseline_horizon,
                # Baselines draw from their own stream (see seeding.BaselineRuns)
                baseline_seed=None if cfg.rng_seed is None else cfg.rng_seed + 7919,
                misinfo=misinfo,
            )

        self.sim, self.config, self.static = sim, cfg, static
        self.edge_index = [tuple(e) for e in static["contact_edges"]]
        n = static["n"]
        self.beta_values = ([round(float(het_betas[u]), 4) for u in range(n)]
                            if cfg.heterogeneous_beta else [float(cfg.beta)] * n)

    @property
    def collecting_baselines(self):
        return isinstance(self.sim, SeedPolicyRun) and self.sim.collecting_baselines

    def step(self):
        """One tick, or while a seed strategy is still collecting its no-quarantine
        baselines, one more baseline run (no tick)."""
        if self.collecting_baselines:
            self.sim.baseline_step()
        else:
            self.sim.step()

    def snapshot(self):
        sim = self.sim
        n, t = sim.n, sim.t
        state = [int(sim.state[u]) for u in range(n)]
        informed = [1 if u in sim.informed else 0 for u in range(n)]
        live = sim.contact
        cut = [i for i, (a, b) in enumerate(self.edge_index) if not live.has_edge(a, b)]
        q_days = [t - sim.quarantine_since[u] if u in sim.quarantine_since else -1 for u in range(n)]
        planned = sim.d if sim.d is not None else None

        snap = {
            "t": t,
            "state": state,
            "informed": informed,
            "quarantine_days": q_days,
            "quarantine_planned": planned,
            "cut_edges": cut,
            "live_degree": [live.degree(u) for u in range(n)],
            "state_since": [sim.state_since[u] for u in range(n)],
            "times_infected": [sim.times_infected[u] for u in range(n)],
            "informed_at": [sim.informed_at.get(u, -1) for u in range(n)],
            "new_infected": [int(u) for u in sim.new_infected],
            "new_informed": sim.new_informed,
            "counts": {
                "S": state.count(0), "I": state.count(1), "R": state.count(2),
                "informed": sum(informed),
                "quarantining": sum(1 for d in q_days if d >= 0),
                "cut_edges": len(cut),
            },
        }
        if sim.fj_x is not None:
            snap["belief"] = [round(float(sim.fj_x[u]), 4) for u in range(n)]
        if self.config.misinfo:
            misinformed = [1 if u in sim.misinformed else 0 for u in range(n)]
            snap["misinformed"] = misinformed
            snap["misinformed_at"] = [sim.misinformed_at.get(u, -1) for u in range(n)]
            snap["new_misinformed"] = [int(u) for u in sim.new_misinformed]
            snap["misinfo_seeds"] = sorted(int(u) for u in sim.misinfo_seed_nodes)
            snap["misinfo_mode"] = self.config.misinfo_mode
            snap["counts"]["misinformed"] = sum(misinformed)
            if sim.fj_xm is not None:
                snap["misbelief"] = [round(float(sim.fj_xm[u]), 4) for u in range(n)]
        # Seeds informed directly (by a strategy, or the begin_q draw) rather than by spread
        if isinstance(sim, SeedPolicyRun):
            snap["seeds"] = sim.seeds
            snap["policy"] = sim.snapshot_info()
        else:
            snap["seeds"] = sorted(int(u) for u in (sim.initial_informed_lst or []))
        return snap

    def reset_payload(self):
        """Response body for a reset: config, static network payload, t=0 snapshot."""
        static = {**self.static, "beta": self.beta_values,
                  "adheres": [1 if u in self.sim.adhering else 0 for u in range(self.sim.n)]}
        if isinstance(self.sim, SeedPolicyRun):
            static["policy"] = {**self.sim.static_info(),
                                "metrics": _seed_metrics(_network_key(self.config))}
        return {"config": self.config.model_dump(), "static": static, "snapshot": self.snapshot()}


class Workspace:
    """Up to MAX_MULTIPLEXES independent multiplexes, each its own Session (any
    scenario), keyed by slot 0..MAX_MULTIPLEXES-1 and advanced together."""

    def __init__(self):
        self.slots = {}

    def _check_slot(self, slot):
        if not 0 <= slot < MAX_MULTIPLEXES:
            raise ValueError(f"Multiplex slot must be 0..{MAX_MULTIPLEXES - 1}")

    def reset(self, slot, cfg):
        self._check_slot(slot)
        session = self.slots.get(slot) or Session()
        session.reset(cfg)  # raises before touching the slot on a bad scenario
        self.slots[slot] = session
        return session.reset_payload()

    def remove(self, slot):
        self.slots.pop(slot, None)
        return {"slots": sorted(self.slots)}

    def step(self):
        """Advance every multiplex one tick. While any of them is still collecting its
        baseline runs, a step only advances that collection (one run each) and the rest
        hold, so all of them start their experiments, and keep ticking, together.
        Returns {"phase", "snapshots": {slot: snapshot, or None if it held}}."""
        if not self.slots:
            raise ValueError("No simulation; call /api/reset first")
        collecting = {k for k, sess in self.slots.items() if sess.collecting_baselines}
        stepping = collecting or set(self.slots)
        for k in sorted(stepping):
            self.slots[k].step()
        return {"phase": "baseline" if collecting else "run",
                "snapshots": {k: (sess.snapshot() if k in stepping else None)
                              for k, sess in self.slots.items()}}


def options():
    return {"high_school": networks.hs_info(), "reality_commons": networks.rc_info(),
            "max_nodes": MAX_NODES, "max_multiplexes": MAX_MULTIPLEXES,
            "defaults": ScenarioConfig().model_dump(), "seed_algorithms": seeding.ALGORITHMS}
