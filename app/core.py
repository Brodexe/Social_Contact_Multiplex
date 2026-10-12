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

import network_setup
from app.engine import MultiplexSIRS

NETWORKS = {
    "synthetic": "Synthetic ER (shared_network.pkl, n≈200)",
    "high_school": "High school (contact bin 1 + survey social)",
}


# Bounds keep a public deployment from being asked for arbitrarily expensive runs.
class ScenarioConfig(BaseModel):
    network: Literal["synthetic", "high_school"] = "synthetic"
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


# ---------------------------------------------------------------- networks ---

def _load_network(name):
    """Return (contact Graph, social DiGraph, node display names, heterogeneous beta map)."""
    if name == "synthetic":
        shared = network_setup.load_shared_network()
        contact = shared["contact_network"]
        social = shared["social_network"]
        names = [str(u) for u in contact.nodes()]
        return contact, social, names, shared["global_betas"][0]

    if name == "high_school":
        contact = nx.read_gml("capstone_proj_data/high_school_contact_bin1.gml")
        social = nx.read_gml("capstone_proj_data/high_school_social.gml")
        contact.remove_nodes_from([u for u in list(contact.nodes()) if contact.degree(u) == 0])
        # Same alignment as adaptive_seed_selection.initialize: intersect on label, then
        # map both graphs onto 0..n-1 with one shared mapping.
        common = [u for u in contact.nodes() if social.has_node(u)]
        contact = contact.subgraph(common).copy()
        social = social.subgraph(common).copy()
        mapping = {u: i for i, u in enumerate(contact.nodes())}
        names = [f"Student {u}" for u in contact.nodes()]
        contact = nx.relabel_nodes(contact, mapping)
        social = nx.relabel_nodes(social, mapping)
        # The survey graph is undirected, but IM's diffusion walks successors(); treat
        # each friendship as a tie in both directions.
        if not social.is_directed():
            social = social.to_directed()
        betas = network_setup.laplacian_smooth_beta(
            contact, network_setup.beta_L, network_setup.beta_R, lam=network_setup.Gamma,
            seed=network_setup.SEED)
        return contact, social, names, betas

    raise ValueError(f"unknown network {name!r}")


def _normalized_layout(G, seed):
    """Force-directed layout scaled into (roughly) the unit disk."""
    pos = nx.spring_layout(G, seed=seed, iterations=300)
    xy = np.array([pos[u] for u in G.nodes()])
    xy -= xy.mean(axis=0)
    r = np.linalg.norm(xy, axis=1)
    xy /= max(np.percentile(r, 97), 1e-9)
    # Pull far-flung outliers (e.g. isolated nodes) back to the rim
    r = np.linalg.norm(xy, axis=1)
    over = r > 1.05
    xy[over] *= (1.05 / r[over])[:, None]
    return {u: [round(float(x), 4), round(float(y), 4)] for u, (x, y) in zip(G.nodes(), xy)}


@lru_cache(maxsize=4)
def _static_payload(name):
    contact, social, names, betas = _load_network(name)
    nodes = sorted(contact.nodes())
    n = len(nodes)
    social_u = social.to_undirected()

    contact_core = nx.core_number(nx.Graph(contact))
    social_core = nx.core_number(social_u)
    contact_btw = nx.betweenness_centrality(contact)
    social_btw = nx.betweenness_centrality(social)

    contact_pos = _normalized_layout(contact, seed=7)
    social_pos = _normalized_layout(social_u, seed=11)

    contact_edges = [[int(min(a, b)), int(max(a, b))] for a, b in contact.edges()]
    social_edges = [[int(a), int(b)] for a, b in social.edges()]

    payload = {
        "network": name,
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


# -------------------------------------------------------------- simulation ---

class Session:
    def __init__(self):
        self.sim = None
        self.config = None
        self.static = None
        self.edge_index = None
        self.beta_values = None

    def reset(self, cfg: ScenarioConfig):
        static, contact, social, het_betas = _static_payload(cfg.network)

        if cfg.rng_seed is not None:
            random.seed(cfg.rng_seed)
            np.random.seed(cfg.rng_seed)

        beta = het_betas if cfg.heterogeneous_beta else float(cfg.beta)
        q = {"r": "r", "period": True, "off": False}.get(cfg.q_mode)
        if cfg.q_mode == "fixed":
            q = max(2, int(cfg.q_period))  # Simulate_SIR treats ints > 1 as a fixed period
        mech_val = cfg.mech_val if cfg.mechanism != "lt" else int(round(cfg.mech_val))

        sim = MultiplexSIRS(
            deepcopy(contact), deepcopy(social),
            beta=beta, gamma=cfg.gamma, mu=cfg.mu, init=cfg.init,
            q=q, q_mech=(cfg.mechanism, mech_val), adherence=float(cfg.adherence),
            begin_q=cfg.begin_q, seeds=int(cfg.seeds), mc=cfg.mc,
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
        return snap

    def reset_payload(self):
        """Response body for a reset: config, static network payload, t=0 snapshot."""
        return {
            "config": self.config.model_dump(),
            "static": {**self.static, "beta": self.beta_values,
                       "adheres": [1 if u in self.sim.adhering else 0 for u in range(self.sim.n)]},
            "snapshot": self.snapshot(),
        }


def options():
    return {"networks": NETWORKS, "defaults": ScenarioConfig().model_dump()}
