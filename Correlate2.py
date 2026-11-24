import os
import random
from datetime import datetime

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


def read_social(fname):
    """
    Read the static undirected social network.

    Expected file columns:
        node1  node2  w

    An edge is added only when w == 1.
    """
    df = pd.read_csv(
        fname,
        sep=r"\s+",
        header=None,
        names=["node1", "node2", "w"]
    )

    G = nx.Graph()

    for node1, node2, w in df.itertuples(index=False):
        if w == 1:
            G.add_edge(node1, node2)

    print(G)
    input()
    return G


def read_contact(fname, duration):
    """
    Read SocioPatterns contact data into disjoint temporal contact graphs.

    Expected file columns:
        t  i  j  Ci  Cj

    Parameters
    ----------
    fname : str
        Contact-data filename.

    duration : int
        Duration of each contact-network snapshot, in seconds.

    Returns
    -------
    temporal_graphs : list[nx.Graph]
        Undirected graphs ordered in time.
    """
    if duration <= 0:
        raise ValueError("duration must be positive.")

    df = pd.read_csv(
        fname,
        sep=r"\s+",
        header=None,
        names=["t", "i", "j", "Ci", "Cj"]
    )

    df = df.sort_values("t").reset_index(drop=True)

    if df.empty:
        return []

    first_time = int(df["t"].min())
    last_time = int(df["t"].max())

    # Assign each contact record to one disjoint time window.
    df["window_start"] = (
        ((df["t"] - first_time) // duration) * duration + first_time
    )

    temporal_graphs = []

    for window_start in range(first_time, last_time + 1, duration):
        window_end = window_start + duration
        contacts = df[df["window_start"] == window_start]

        H_t = nx.Graph()
        H_t.graph["start_time"] = window_start
        H_t.graph["end_time"] = window_end

        for row in contacts.itertuples(index=False):
            H_t.add_node(row.i, **{"class": row.Ci})
            H_t.add_node(row.j, **{"class": row.Cj})

            # Edge weight = number of 20-second contacts in this window.
            if H_t.has_edge(row.i, row.j):
                H_t[row.i][row.j]["weight"] += 1
            else:
                H_t.add_edge(row.i, row.j, weight=1)

        print(H_t)
        temporal_graphs.append(H_t)

    return temporal_graphs


def sirs_step_temporal(H_t, state, informed, beta, gamma, mu):
    """
    Perform one SIRS step using the current temporal contact graph H_t.

    States:
        0 = susceptible
        1 = infected
        2 = recovered

    An informed infected node does not transmit infection, matching
    the logic in your original code.
    """
    new_state = state.copy()
    new_infections = 0

    # Infection uses only edges in the current contact snapshot.
    for u in H_t.nodes():
        if state.get(u, 0) == 1:

            # Informed infected nodes do not spread disease.
            if informed.get(u, 0) == 1:
                continue

            for v in H_t.neighbors(u):
                # Use new_state to prevent counting the same new infection twice.
                if new_state.get(v, 0) == 0:
                    if random.random() < beta:
                        new_state[v] = 1
                        new_infections += 1

    # Recovery.
    for u in H_t.nodes():
        if state.get(u, 0) == 1:
            if random.random() < gamma:
                new_state[u] = 2

    # Loss of immunity.
    for u in H_t.nodes():
        if state.get(u, 0) == 2:
            if random.random() < mu:
                new_state[u] = 0

    return new_state, new_infections


def simulate_temporal_multiplex(
    G,
    temporal_graphs,
    information_seeds,
    epidemic_seeds,
    activation_probability,
    beta,
    gamma,
    mu,
    iterations=250
):
    """
    Simulate information diffusion and SIRS epidemic diffusion.

    G
        Static UNDIRECTED social network. It stays unchanged.

    temporal_graphs
        Evolving UNDIRECTED contact network snapshots.

    information_seeds
        Iterable of initially informed nodes.

    epidemic_seeds
        Iterable of initially infected nodes.

    Returns
    -------
    results : dict
        Mean and standard deviation of new infections over time.
    """
    all_nodes = set(G.nodes())

    for H_t in temporal_graphs:
        all_nodes.update(H_t.nodes())

    information_seeds = set(information_seeds)
    epidemic_seeds = set(epidemic_seeds)

    all_new_infections = []

    for _ in range(iterations):

        # Initially, every node is susceptible.
        state = {u: 0 for u in all_nodes}

        # Mark epidemic seeds as infected.
        for u in epidemic_seeds:
            if u in state:
                state[u] = 1

        # Information diffusion state on the static social graph.
        informed_nodes = set(information_seeds)
        newly_informed = set(information_seeds)

        new_infections_this_run = []

        for H_t in temporal_graphs:

            # Information diffusion on the unchanged UNDIRECTED social network.
            next_informed = set()

            for u in newly_informed:
                if u in G:
                    for v in G.neighbors(u):
                        if v not in informed_nodes:
                            if random.random() < activation_probability:
                                next_informed.add(v)

            newly_informed = next_informed
            informed_nodes.update(newly_informed)

            informed = {
                u: int(u in informed_nodes)
                for u in all_nodes
            }

            # Epidemic diffusion on the evolving contact graph.
            state, new_cases = sirs_step_temporal(
                H_t=H_t,
                state=state,
                informed=informed,
                beta=beta,
                gamma=gamma,
                mu=mu
            )

            new_infections_this_run.append(new_cases)

        all_new_infections.append(new_infections_this_run)

    return {
        "time": [
            H_t.graph["start_time"]
            for H_t in temporal_graphs
        ],
        "mean_new_infections": np.mean(all_new_infections, axis=0),
        "std_new_infections": np.std(all_new_infections, axis=0)
    }


def plot_new_infections(
    results,
    save_path="capstone_result_figures/temporal_new_infections.pdf",
):
    """Plot mean new infections across temporal contact snapshots and save as PDF."""
    timestamps = [
        datetime.fromtimestamp(t)
        for t in results["time"]
    ]

    mean_cases = results["mean_new_infections"]
    std_cases = results["std_new_infections"]

    plt.figure(figsize=(12, 5))

    plt.plot(
        timestamps,
        mean_cases,
        color="tab:red",
        linewidth=2,
        label="Mean new infections"
    )

    plt.fill_between(
        timestamps,
        mean_cases - std_cases,
        mean_cases + std_cases,
        color="tab:red",
        alpha=0.20,
        label="± 1 standard deviation"
    )

    plt.axhline(0, color="black", linestyle="--", linewidth=0.8)

    plt.xlabel("Time", fontsize=14)
    plt.ylabel("New infections", fontsize=14)
    plt.title("Infection Spread Through the Temporal Contact Network", fontsize=15)
    plt.legend()
    plt.grid(alpha=0.25)

    fig = plt.gcf()
    fig.autofmt_xdate()
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


G = read_social("HighSchool2013_facebook_known_pairs.csv")
# print(G)
# exit(1)

temporal_graphs = read_contact(
    "HighSchool2013_proximity_net.csv",
    duration=3600
)


# ------------------------------------------------------------
# Run the empirical temporal-contact model
# ------------------------------------------------------------

results = simulate_temporal_multiplex(
    G=G,
    temporal_graphs=temporal_graphs,
    information_seeds=np.random.choice([u for u in G.nodes()], size=10, replace=False).tolist(),
    epidemic_seeds=np.random.choice([u for u in G.nodes()], size=10, replace=False).tolist(),
    activation_probability=0.20,
    beta=0.15,
    gamma=0.10,
    mu=0.05,
    iterations=250
)

plot_new_infections(results)


'''
# ------------------------------------------------------------
# NULL MODEL: social network is also the contact network.
#
# Uncomment these lines and run simulate_temporal_multiplex()
# again to use the static social network as every contact layer.
# This produces perfect social-contact degree correlation.
# ------------------------------------------------------------

null_temporal_graphs = []
for H_t in temporal_graphs:
    H_null = G.copy()

    # Preserve the timing of the empirical temporal snapshots.
    H_null.graph["start_time"] = H_t.graph["start_time"]
    H_null.graph["end_time"] = H_t.graph["end_time"]

    null_temporal_graphs.append(H_null)

null_results = simulate_temporal_multiplex(
    G=G,
    temporal_graphs=null_temporal_graphs,
    information_seeds=np.random.choice([u for u in G.nodes()], size=10, replace=False).tolist(),
    epidemic_seeds=np.random.choice([u for u in G.nodes()], size=10, replace=False).tolist(),
    activation_probability=0.20,
    beta=0.15,
    gamma=0.10,
    mu=0.05,
    iterations=250
)

plot_new_infections(
    null_results,
    save_path="capstone_result_figures/temporal_new_infections_null.pdf",
)
'''