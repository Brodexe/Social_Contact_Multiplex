import random

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


# ============================================================
# Read networks
# ============================================================

def read_social(fname):
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

    return G


def read_contact_time_zero(fname, duration):
    """
    Read H(0): the first contact graph over `duration` seconds.
    """
    df = pd.read_csv(
        fname,
        sep=r"\s+",
        header=None,
        names=["t", "i", "j", "Ci", "Cj"]
    )

    df = df.sort_values("t").reset_index(drop=True)

    start_time = int(df["t"].min())
    end_time = start_time + duration

    first_contacts = df[
        (df["t"] >= start_time) &
        (df["t"] < end_time)
    ]

    H = nx.Graph()
    H.graph["start_time"] = start_time
    H.graph["end_time"] = end_time

    for row in first_contacts.itertuples(index=False):
        H.add_node(row.i, node_class=row.Ci)
        H.add_node(row.j, node_class=row.Cj)

        if H.has_edge(row.i, row.j):
            H[row.i][row.j]["weight"] += 1
        else:
            H.add_edge(row.i, row.j, weight=1)

    return H


# ============================================================
# Degree-preserving randomization of H
# ============================================================

def degree_preserving_rewire(H, n_swaps, random_seed=123):
    """
    Degree-preserving swaps:

        (u, v), (w, x) -> (u, x), (w, v)

    Reject self-loops and duplicate edges.
    """
    rng = random.Random(random_seed)

    H_random = H.copy()
    successful_swaps = 0
    attempts = 0
    max_attempts = max(1000, n_swaps * 100)

    while successful_swaps < n_swaps and attempts < max_attempts:
        attempts += 1

        edges = list(H_random.edges())

        if len(edges) < 2:
            break

        (u, v), (w, x) = rng.sample(edges, 2)

        if len({u, v, w, x}) < 4:
            continue

        if rng.random() < 0.5:
            u, v = v, u

        if rng.random() < 0.5:
            w, x = x, w

        H_random.remove_edge(u, v)
        H_random.remove_edge(w, x)

        valid_swap = (
            u != x and
            w != v and
            not H_random.has_edge(u, x) and
            not H_random.has_edge(w, v)
        )

        if valid_swap:
            H_random.add_edge(u, x)
            H_random.add_edge(w, v)
            successful_swaps += 1
        else:
            H_random.add_edge(u, v)
            H_random.add_edge(w, x)

    print(
        f"Successful degree-preserving swaps: "
        f"{successful_swaps}/{n_swaps}"
    )

    return H_random


# ============================================================
# Partial degree-rank mappings
# ============================================================

def partial_rank_mapping(
    G,
    H,
    social_group,
    contact_group,
    extreme_fraction=0.25,
    random_seed=123
):
    """
    Create a contact-node relabeling.

    social_group:
        "high" or "low"

    contact_group:
        "high" or "low"

    The specified extreme groups are mapped by rank.
    All remaining nodes are mapped randomly.

    This makes these three conditions distinct:

        high social -> high contact
        high social -> low contact
        low social  -> high contact
    """
    rng = random.Random(random_seed)

    nodes = list(H.nodes())
    n_nodes = len(nodes)

    n_extreme = max(1, int(np.ceil(n_nodes * extreme_fraction)))

    contact_high_to_low = sorted(
        nodes,
        key=lambda u: (H.degree(u), str(u)),
        reverse=True
    )

    social_high_to_low = sorted(
        nodes,
        key=lambda u: (G.degree(u), str(u)),
        reverse=True
    )

    if contact_group == "high":
        selected_contact_nodes = contact_high_to_low[:n_extreme]
    elif contact_group == "low":
        selected_contact_nodes = contact_high_to_low[-n_extreme:]
    else:
        raise ValueError("contact_group must be 'high' or 'low'.")

    if social_group == "high":
        selected_social_nodes = social_high_to_low[:n_extreme]
    elif social_group == "low":
        selected_social_nodes = social_high_to_low[-n_extreme:]
    else:
        raise ValueError("social_group must be 'high' or 'low'.")

    # Map the requested extreme groups directly.
    mapping = dict(
        zip(selected_contact_nodes, selected_social_nodes)
    )

    # Randomly map all remaining contact nodes to remaining social nodes.
    remaining_contact_nodes = [
        u for u in nodes
        if u not in selected_contact_nodes
    ]

    remaining_social_nodes = [
        u for u in nodes
        if u not in selected_social_nodes
    ]

    rng.shuffle(remaining_social_nodes)

    mapping.update(
        dict(zip(remaining_contact_nodes, remaining_social_nodes))
    )

    H_mapped = nx.relabel_nodes(
        H,
        mapping,
        copy=True
    )

    return H_mapped, mapping


# ============================================================
# Create all five contact-layer conditions
# ============================================================

def make_contact_layer_conditions(
    G,
    H,
    n_swaps=1000,
    extreme_fraction=0.25
):
    """
    Construct five conditions:

        observed:
            Original H

        rewired:
            Degree-preserving randomized H

        high_social_high_contact:
            Top social-degree nodes mapped to top contact-degree nodes

        high_social_low_contact:
            Top social-degree nodes mapped to bottom contact-degree nodes

        low_social_high_contact:
            Bottom social-degree nodes mapped to top contact-degree nodes
    """
    common_nodes = list(set(G.nodes()) & set(H.nodes()))

    G_common = G.subgraph(common_nodes).copy()
    H_common = H.subgraph(common_nodes).copy()

    H_rewired = degree_preserving_rewire(
        H=H_common,
        n_swaps=n_swaps,
        random_seed=123
    )

    H_high_social_high_contact, map_high_high = partial_rank_mapping(
        G=G_common,
        H=H_rewired,
        social_group="high",
        contact_group="high",
        extreme_fraction=extreme_fraction,
        random_seed=101
    )

    H_high_social_low_contact, map_high_low = partial_rank_mapping(
        G=G_common,
        H=H_rewired,
        social_group="high",
        contact_group="low",
        extreme_fraction=extreme_fraction,
        random_seed=202
    )

    H_low_social_high_contact, map_low_high = partial_rank_mapping(
        G=G_common,
        H=H_rewired,
        social_group="low",
        contact_group="high",
        extreme_fraction=extreme_fraction,
        random_seed=303
    )

    conditions = {
        "observed": H_common,
        "rewired": H_rewired,
        "high_social_high_contact": H_high_social_high_contact,
        "high_social_low_contact": H_high_social_low_contact,
        "low_social_high_contact": H_low_social_high_contact
    }

    mappings = {
        "high_social_high_contact": map_high_high,
        "high_social_low_contact": map_high_low,
        "low_social_high_contact": map_low_high
    }

    return G_common, conditions, mappings


# ============================================================
# Correlation-controlled social layer (correlation ablation)
# ============================================================

def make_correlated_social(contact, social, correlation, random_seed=123):
    """
    Relabel `social` onto `contact`'s nodes so that inter-layer degree
    alignment is controlled by `correlation` in [-1, 1].

    Positive correlation reuses partial_rank_mapping with the two layers' roles
    swapped: here the contact layer is held fixed and the SOCIAL layer is
    relabeled. The top `correlation` fraction of social nodes (by social
    degree) are mapped, rank for rank, onto the top `correlation` fraction of
    contact nodes (by contact degree); every remaining social node is mapped
    onto a remaining contact node at random.

    Negative correlation is the anti-aligned mirror: the top |correlation|
    fraction of social nodes are mapped in reverse rank onto the BOTTOM
    |correlation| fraction of contact nodes (highest social degree -> lowest
    contact degree, second highest -> second lowest, ...); the rest are random.

        correlation =  1 -> full degree-rank alignment (maximum achievable
                            correlation for these two degree sequences)
        correlation =  0 -> pure random relabeling (~zero correlation)
        correlation = -1 -> full reverse-rank alignment (most negative
                            achievable correlation)

    The social layer's own structure (degree sequence, clustering, direction)
    is untouched; only which contact node each social node sits on changes.
    `correlation` is a rank-alignment amount, not a target Pearson value --
    measure the result with Correlate1.degree_correlation_over_time.

    Both graphs must share the same node set.
    """
    if set(contact.nodes()) != set(social.nodes()):
        raise ValueError("contact and social must share the same node set.")
    if not -1 <= correlation <= 1:
        raise ValueError("correlation must be in [-1, 1].")

    if correlation < 0:
        # Not delegated to partial_rank_mapping: its "low" group is ordered
        # high-to-low, so pairing it with a "high" group gives the wrong
        # within-group order (and at fraction 1 it collapses to +1 alignment).
        rng = random.Random(random_seed)
        nodes = list(social.nodes())
        n_extreme = max(1, int(np.ceil(len(nodes) * -correlation)))

        social_high_to_low = sorted(
            nodes, key=lambda u: (social.degree(u), str(u)), reverse=True)
        contact_low_to_high = sorted(
            nodes, key=lambda u: (contact.degree(u), str(u)))

        selected_social = social_high_to_low[:n_extreme]
        selected_contact = contact_low_to_high[:n_extreme]
        mapping = dict(zip(selected_social, selected_contact))

        chosen_social, chosen_contact = set(selected_social), set(selected_contact)
        remaining_social = [u for u in nodes if u not in chosen_social]
        remaining_contact = [u for u in nodes if u not in chosen_contact]
        rng.shuffle(remaining_contact)
        mapping.update(zip(remaining_social, remaining_contact))

        return nx.relabel_nodes(social, mapping, copy=True), mapping

    if correlation == 0:
        # partial_rank_mapping always rank-aligns at least one node, so the
        # zero-correlation case is a plain random permutation instead.
        rng = random.Random(random_seed)
        social_nodes = list(social.nodes())
        contact_nodes = list(contact.nodes())
        rng.shuffle(contact_nodes)
        mapping = dict(zip(social_nodes, contact_nodes))
        return nx.relabel_nodes(social, mapping, copy=True), mapping

    # Argument names follow partial_rank_mapping's original roles: its `H` is
    # the graph being relabeled (our social layer) and its `G` the fixed
    # reference (our contact layer).
    return partial_rank_mapping(
        G=contact,
        H=social,
        social_group="high",
        contact_group="high",
        extreme_fraction=correlation,
        random_seed=random_seed
    )


# ============================================================
# Multiplex SIRS simulation
# ============================================================

def sirs_step(H, state, informed_nodes, beta, gamma, mu, rng):
    """
    state:
        0 = susceptible
        1 = infected
        2 = recovered
    """
    new_state = state.copy()
    new_infections = 0

    # Disease spreads through H.
    for u in H.nodes():
        if state[u] == 1 and u not in informed_nodes:
            for v in H.neighbors(u):
                if new_state[v] == 0 and rng.random() < beta:
                    new_state[v] = 1
                    new_infections += 1

    # Recovery and loss of immunity.
    for u in state:
        if state[u] == 1 and rng.random() < gamma:
            new_state[u] = 2

        elif state[u] == 2 and rng.random() < mu:
            new_state[u] = 0

    return new_state, new_infections


def simulate_one_condition(
    G,
    H,
    information_seeds,
    epidemic_seeds,
    activation_probability,
    beta,
    gamma,
    mu,
    simulation_steps,
    rng
):
    """
    Run one realization of the static pair (G, H).
    """
    nodes = list(H.nodes())

    state = {u: 0 for u in nodes}

    for u in epidemic_seeds:
        state[u] = 1

    informed_nodes = set(information_seeds)
    newly_informed = set(information_seeds)

    new_infections_over_time = []

    for _ in range(simulation_steps):

        # Information spreads through G.
        next_informed = set()

        for u in newly_informed:
            for v in G.neighbors(u):
                if v not in informed_nodes:
                    if rng.random() < activation_probability:
                        next_informed.add(v)

        newly_informed = next_informed
        informed_nodes.update(newly_informed)

        # Disease spreads through H.
        state, new_cases = sirs_step(
            H=H,
            state=state,
            informed_nodes=informed_nodes,
            beta=beta,
            gamma=gamma,
            mu=mu,
            rng=rng
        )

        new_infections_over_time.append(new_cases)

    return new_infections_over_time


def simulate_all_conditions(
    G,
    contact_conditions,
    n_information_seeds=10,
    n_epidemic_seeds=10,
    activation_probability=0.20,
    beta=0.15,
    gamma=0.10,
    mu=0.05,
    simulation_steps=25,
    iterations=250,
    random_seed=123
):
    """
    Run all five conditions using the same initial seed sets per iteration.
    """
    seed_rng = random.Random(random_seed)

    nodes = list(contact_conditions["observed"].nodes())

    required_nodes = (
        n_information_seeds +
        n_epidemic_seeds
    )

    if len(nodes) < required_nodes:
        raise ValueError(
            f"Need {required_nodes} nodes for distinct seed sets, "
            f"but only have {len(nodes)} nodes."
        )

    all_results = {
        name: []
        for name in contact_conditions
    }

    for _ in range(iterations):

        selected_nodes = seed_rng.sample(
            nodes,
            required_nodes
        )

        information_seeds = set(
            selected_nodes[:n_information_seeds]
        )

        epidemic_seeds = set(
            selected_nodes[n_information_seeds:]
        )

        for name, H in contact_conditions.items():

            condition_rng = random.Random(
                seed_rng.randint(0, 10**9)
            )

            curve = simulate_one_condition(
                G=G,
                H=H,
                information_seeds=information_seeds,
                epidemic_seeds=epidemic_seeds,
                activation_probability=activation_probability,
                beta=beta,
                gamma=gamma,
                mu=mu,
                simulation_steps=simulation_steps,
                rng=condition_rng
            )

            all_results[name].append(curve)

    mean_results = {
        name: np.mean(curves, axis=0)
        for name, curves in all_results.items()
    }

    return mean_results


# ============================================================
# Plot five curves
# ============================================================

def plot_five_conditions(mean_results):
    colors = {
        "observed": "black",
        "rewired": "tab:blue",
        "high_social_high_contact": "tab:red",
        "high_social_low_contact": "tab:orange",
        "low_social_high_contact": "tab:green"
    }

    labels = {
        "observed": "(G, H)",
        "rewired": "(G, randomized H)",
        "high_social_high_contact": (
            "High social / high contact"
        ),
        "high_social_low_contact": (
            "High social / low contact"
        ),
        "low_social_high_contact": (
            "Low social / high contact"
        )
    }

    plt.figure(figsize=(12, 6))

    for name, curve in mean_results.items():
        time = np.arange(1, len(curve) + 1)

        plt.plot(
            time,
            curve,
            linewidth=2,
            marker="o",
            markersize=4,
            color=colors[name],
            label=labels[name]
        )

    plt.axhline(
        0,
        color="black",
        linestyle="--",
        linewidth=0.8
    )

    plt.xlabel("Simulation time", fontsize=14)
    plt.ylabel("Mean new infections", fontsize=14)

    plt.title(
        "New Infections Across Five Contact-Layer Conditions",
        fontsize=15
    )

    plt.grid(alpha=0.25)
    plt.legend(fontsize=10)
    plt.tight_layout()

    plt.savefig(
        "Five_Conditions_New_Infections.png",
        dpi=200
    )

    plt.show()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    SOCIAL_FILE = "HighSchool2013_facebook_known_pairs.csv"
    CONTACT_FILE = "HighSchool2013_proximity_net.csv"

    # First hourly contact graph H(0).
    DURATION = 3600

    # Number of accepted contact-edge swaps.
    N_SWAPS = 1000

    # Top/bottom 25% define high and low degree groups.
    EXTREME_FRACTION = 0.25

    N_INFORMATION_SEEDS = 10
    N_EPIDEMIC_SEEDS = 10

    ACTIVATION_PROBABILITY = 0.20
    BETA = 0.15
    GAMMA = 0.10
    MU = 0.05

    SIMULATION_STEPS = 25
    ITERATIONS = 250


    G = read_social(SOCIAL_FILE)

    H0 = read_contact_time_zero(
        CONTACT_FILE,
        duration=DURATION
    )

    G_common, contact_conditions, mappings = make_contact_layer_conditions(
        G=G,
        H=H0,
        n_swaps=N_SWAPS,
        extreme_fraction=EXTREME_FRACTION
    )

    for name, H in contact_conditions.items():
        print(
            name,
            "| nodes:",
            H.number_of_nodes(),
            "| edges:",
            H.number_of_edges()
        )

    print(
        "Degree sequence preserved after rewiring:",
        sorted(dict(contact_conditions["observed"].degree()).values()) ==
        sorted(dict(contact_conditions["rewired"].degree()).values())
    )

    mean_results = simulate_all_conditions(
        G=G_common,
        contact_conditions=contact_conditions,
        n_information_seeds=N_INFORMATION_SEEDS,
        n_epidemic_seeds=N_EPIDEMIC_SEEDS,
        activation_probability=ACTIVATION_PROBABILITY,
        beta=BETA,
        gamma=GAMMA,
        mu=MU,
        simulation_steps=SIMULATION_STEPS,
        iterations=ITERATIONS,
        random_seed=123
    )

    plot_five_conditions(mean_results)
