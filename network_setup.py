"""
Shared network + heterogeneous-beta generation for the synthetic Erdos-Renyi
comparison network used by both adaptive_seed_selection.py and milp.py.

Both scripts previously built their own Erdos-Renyi contact network, social
network, and (for adaptive_seed_selection.py) per-simulation heterogeneous
beta maps independently, so a side-by-side comparison was never actually
running against the same network. This module is the single source of truth
for that shared setup: call load_shared_network() to get back an identical
contact network, social network, and list of per-simulation beta maps.

Run this file directly (`python network_setup.py`) to (re)generate the cache
file explicitly; load_shared_network() will also auto-generate it on first
use, and will regenerate/extend it if the generation parameters below have
changed or more simulations are requested than are cached.
"""

import os
import pickle
import random

import numpy as np
import networkx as nx

import correlated_graphs

# --- Generation parameters (single source of truth for the shared network) ---
n = 200
p = 0.05
SEED = 42

HETEROGENEOUS_BETA = True  # True: node-wise beta drawn from power-law distribution; False: scalar beta for all nodes
beta = 0.15                # Used directly when HETEROGENEOUS_BETA=False; ignored when True

beta_L = 0.05   # Lower bound for heterogeneous beta
beta_R = 0.25   # Upper bound for heterogeneous beta
Gamma  = 2      # Shape parameter: higher values skew beta toward beta_R

num_simulations = 10  # Default number of per-simulation beta maps to generate

SHARED_NETWORK_PATH = "shared_network.pkl"


def laplacian_smooth_beta(G, beta_low, beta_high, lam=2.0, alpha=20, seed=None):
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())
    n_nodes = len(nodes)

    A = nx.to_numpy_array(G, nodelist=nodes)
    D = np.diag(A.sum(axis=1))
    L = D - A

    z = rng.normal(0, 1, n_nodes)
    # Solve for beta vector which is smooth over the graph
    z_prime = np.linalg.inv(np.eye(n_nodes) + alpha * L) @ z

    # Empirical-uniform values in the order induced by z_prime, then inverse-CDF shape
    u = (np.argsort(np.argsort(z_prime)) + 0.5) / n_nodes
    betas = beta_low + (beta_high - beta_low) * u ** lam

    return dict(zip(nodes, betas))


def generate_global_betas(graph, num_sims, start_index=0):
    """List of num_sims beta maps (or scalars), deterministic given SEED + start_index."""
    if not HETEROGENEOUS_BETA:
        return [beta for _ in range(num_sims)]
    return [laplacian_smooth_beta(graph, beta_L, beta_R, lam=Gamma, seed=SEED + start_index + i)
            for i in range(num_sims)]


def _current_params():
    return {
        "n": n, "p": p, "seed": SEED,
        "HETEROGENEOUS_BETA": HETEROGENEOUS_BETA,
        "beta_L": beta_L, "beta_R": beta_R, "Gamma": Gamma, "beta": beta,
    }


def build_shared_network(num_sims=None):
    sims = num_simulations if num_sims is None else num_sims

    random.seed(SEED)
    np.random.seed(SEED)

    contact_network = nx.erdos_renyi_graph(n, p, seed=SEED)
    isolated_nodes = [node for node in contact_network.nodes() if contact_network.degree(node) == 0]
    contact_network.remove_nodes_from(isolated_nodes)
    contact_network = nx.convert_node_labels_to_integers(contact_network, first_label=0)
    nx.set_edge_attributes(contact_network, 1, "weight")

    initial_edge_count = contact_network.number_of_edges()
    social_network, _ = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)

    global_betas = generate_global_betas(contact_network, sims)

    return {
        "contact_network": contact_network,
        "social_network": social_network,
        "global_betas": global_betas,
        "params": _current_params(),
    }


def load_shared_network(path=SHARED_NETWORK_PATH, min_simulations=None):
    """Load the cached shared network, generating/extending it as needed.

    Regenerates from scratch if the cache is missing or was built with
    different generation parameters than the ones currently set on this
    module. If the cache is otherwise valid but has fewer beta maps than
    min_simulations requires, extends it in place (same network, more betas)
    rather than rebuilding the topology.
    """
    needed_sims = num_simulations if min_simulations is None else min_simulations

    data = None
    changed = False
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = pickle.load(f)
        if data.get("params") != _current_params():
            print(f"[network_setup] Cached network at {path} was generated with "
                  f"different parameters than the current config -- regenerating.")
            data = None

    if data is None:
        data = build_shared_network(needed_sims)
        changed = True
    elif len(data["global_betas"]) < needed_sims:
        have = len(data["global_betas"])
        print(f"[network_setup] Cached network only has {have} beta maps cached; "
              f"extending to {needed_sims}.")
        extra = generate_global_betas(data["contact_network"], needed_sims - have, start_index=have)
        data["global_betas"] = data["global_betas"] + extra
        changed = True

    if changed:
        with open(path, "wb") as f:
            pickle.dump(data, f)

    return data


if __name__ == "__main__":
    data = build_shared_network()
    with open(SHARED_NETWORK_PATH, "wb") as f:
        pickle.dump(data, f)
    print(f"Generated shared network: {data['contact_network'].number_of_nodes()} nodes, "
          f"{data['contact_network'].number_of_edges()} edges, "
          f"{len(data['global_betas'])} beta maps -> {SHARED_NETWORK_PATH}")
