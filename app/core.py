"""
Simulation state behind the interactive viewer, independent of how it is served.

app/server.py exposes this over HTTP (FastAPI, one Session per browser tab);
app/browser_api.py exposes it to the static build, where it runs inside the
visitor's browser under Pyodide. Network/dataset paths are relative to the repo
root, so the working directory must be the repo root (or the unpacked bundle).
"""

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
NETWORK_FIELDS = ("contact_model", "contact_n", "contact_p", "clustering", "hs_bin",
                  "social_model", "social_n", "khop_k", "social_density", "correlation",
                  "net_seed")
MAX_NODES = 400


# Bounds keep a public deployment from being asked for arbitrarily expensive runs.
# Network fields are described in app/networks.py.
class ScenarioConfig(BaseModel):
    contact_model: Literal["er", "clustered", "hs_bin"] = "er"
    contact_n: int = Field(200, ge=10, le=MAX_NODES)
    contact_p: float = Field(0.05, ge=0, le=1)
    clustering: float = Field(0.5, ge=0, le=1)      # only for contact_model == "clustered"
    hs_bin: int = Field(1, ge=1, le=19)             # only for contact_model == "hs_bin"
    social_model: Literal["khop", "correlated", "hs_survey"] = "khop"
    social_n: int = Field(200, ge=10, le=MAX_NODES)  # khop / correlated; must match the contact network
    khop_k: int = Field(2, ge=1, le=6)
    social_density: float = Field(0.1, ge=0, le=1)  # khop: share of all pairs that are ties
    correlation: float = Field(0.5, ge=-1, le=1)    # correlated: c
    net_seed: int = 42
    mechanism: Literal["ic", "lt", "FJ"] = "ic"
    mech_val: float = Field(0.02, ge=0, le=1000)    # IC p, LT threshold, or FJ kappa
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


# ---------------------------------------------------------------- networks ---

def _normalized_layout(G, seed):
    """Force-directed layout scaled into (roughly) the unit disk."""
    # Each iteration is O(n^2); larger graphs settle well enough in fewer
    pos = nx.spring_layout(G, seed=seed, iterations=300 if G.number_of_nodes() <= 200 else 100)
    xy = np.array([pos[u] for u in G.nodes()])
    xy -= xy.mean(axis=0)
    r = np.linalg.norm(xy, axis=1)
    xy /= max(np.percentile(r, 97), 1e-9)
    # Pull far-flung outliers (e.g. isolated nodes) back to the rim
    r = np.linalg.norm(xy, axis=1)
    over = r > 1.05
    xy[over] *= (1.05 / r[over])[:, None]
    return {u: [round(float(x), 4), round(float(y), 4)] for u, (x, y) in zip(G.nodes(), xy)}


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

    contact_pos = _normalized_layout(contact, seed=7)
    social_pos = _normalized_layout(social_u, seed=11)

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
        "layout": {
            "contact": [contact_pos[u] for u in nodes],
            "social": [social_pos[u] for u in nodes],
        },
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

        if cfg.seed_algo == "none":
            sim = MultiplexSIRS(
                deepcopy(contact), deepcopy(social),
                beta=beta, gamma=cfg.gamma, mu=cfg.mu, init=cfg.init,
                q=q, q_mech=(cfg.mechanism, mech_val), adherence=float(cfg.adherence),
                begin_q=cfg.begin_q, seeds=int(cfg.seeds), mc=cfg.mc,
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
                # Baselines draw from their own stream (see seeding.BaselineRuns)
                baseline_seed=None if cfg.rng_seed is None else cfg.rng_seed + 7919,
            )

        self.sim, self.config, self.static = sim, cfg, static
        self.edge_index = [tuple(e) for e in static["contact_edges"]]
        n = static["n"]
        self.beta_values = ([round(float(het_betas[u]), 4) for u in range(n)]
                            if cfg.heterogeneous_beta else [float(cfg.beta)] * n)

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


def options():
    return {"high_school": networks.hs_info(), "max_nodes": MAX_NODES,
            "defaults": ScenarioConfig().model_dump(), "seed_algorithms": seeding.ALGORITHMS}
