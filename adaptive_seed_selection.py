import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import networkx as nx
import SIR
import random
from itertools import combinations
import correlated_graphs
from collections import Counter
import py4cytoscape as p4c
from copy import deepcopy
from collections import defaultdict 

# Global matplotlib settings
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "lines.linewidth": 2.5,
})

# Consistent figure size for all plots (suitable for Overleaf inclusion)
FIGURE_SIZE_LINE = (10, 6)
FIGURE_SIZE_BAR = (14, 8)

n = 200
p = 0.05

contact_network = nx.erdos_renyi_graph(n, p, seed=42)
initial_contact = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
social_network = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)[0]
initial_social = deepcopy(social_network)

T = 100
# Homogeneous beta: everyone equally susceptible
beta = 0.15
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05
adherence = 1.0
num_simulations = 10
batch_interval = 1  # Seeds and cost updated once every batch_interval steps
q = "r"
# Try introducing random infections in intervals to better differentiate methods
introduced_infections = (0, T) # (fraction of population, time step to introduce)

K = 150 # Number of seeds to select at each batch

# Pre-generate infection targets so every method sees the same nodes targeted per
# simulation and per injection time step.  Shape: [num_simulations][num_injection_steps]
injection_times = [t for t in range(1, T) if t % introduced_infections[1] == 0]
_num_to_infect = int(introduced_infections[0] * n)
infection_candidates = [
    [random.sample(list(initial_contact.nodes()), min(_num_to_infect, n)) for _ in injection_times]
    for _ in range(num_simulations)
]

# Returns newly infected at a given time step
def given_at_time(time, sirs_dynamics, contact_graph):
    if time > 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1 and sirs_dynamics[time-1][node] != 1)
    # Initial condition. We say that n_i(0) = i(0)
    elif time == 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1)

    # i = sum(1 for node in contact_graph.nodes() if sirs_dynamics[time][node] == 1)

    return new_i
    # return i

def baseline_infections(sim_index=0):
    contact_network = deepcopy(initial_contact)
    social_network = deepcopy(initial_social)

    full_dynamics = None
    prev_state_dict = None
    baseline_newly_counts = []

    for t_cur in range(T):
        if t_cur % introduced_infections[1] == 0 and t_cur > 0:
            new_infections = infection_candidates[sim_index][injection_times.index(t_cur)]
            for node in new_infections:
                if prev_state_dict[node] == 2:
                    prev_state_dict[node] = 1

        simulation_results = SIR.Simulate_SIR(
            contact_network=contact_network,
            social_network=social_network,
            T=1,
            q=False,
            beta=beta,
            gamma=gamma,
            mu=mu,
            init=init,
            initial_state_dict=prev_state_dict,
        )

        contact_network = deepcopy(initial_contact)
        sirs_dynamics = simulation_results[4]
        prev_state_dict = sirs_dynamics[-1]
        full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics

        current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
        baseline_newly_counts.append(current_new_i)

    baseline_newly_frac = [count / n for count in baseline_newly_counts]
    return baseline_newly_counts, baseline_newly_frac

# Collect per-timestep newly infected counts from baseline runs
baseline_runs = []
for i in range(num_simulations):
    baseline_newly_counts, _ = baseline_infections(i)
    baseline_runs.append(baseline_newly_counts)

# Global utility function: Find a small seed set which minimizes infection spread,
# while maximizing number of live edges in the network.
# newly_infected: array of newly infected ratios at each time step
# total_edges: integer number of edges in the original contact network
# live_edges: array EDGES that are live at each step
# seed_set_size: integer size of the seed set
def global_cost_function(newly_infected, live_edges, seed_set_size, t_cur):
    # NOTE: for now assume cost is uniform across all edges
    all_edges = initial_contact.edges()

    # Some cost function f: V -> Reals that maps edges to cost of removal
    edge_cost_dict = {edge: 1 for edge in all_edges}

    # Compute total possible cost of edge removals (if all edges were removed)
    edge_cost_bound = sum(edge_cost_dict[edge] for edge in all_edges)

    total_edge_removal_cost = 0
    # Compute sum of removed edges at each time step
    for t in range(t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    cost_elements = (np.sum(newly_infected), total_edge_removal_cost, seed_set_size)

    # Adjust penalty weights so that each term contributes equally to cost function
    removal_cost = 1
    g = sum(max(run[t] for run in baseline_runs) for t in range(t_cur + 1))

    alpha_w = 1 / g if g > 0 else 1.0
    beta_w = 1 / ((t_cur + 1) * edge_cost_bound)
    gamma_w = 1 / (n)

    # Print cost components
    print(f"Cost components at time {t_cur}:")
    print(f"  Newly infected sum: {np.sum(newly_infected)}")
    print(f"  Total edge removal cost: {total_edge_removal_cost}")
    print(f"  Seed set size: {seed_set_size}")
    print(f" alpha_w: {alpha_w:.4f}, beta_w: {beta_w:.4f}, gamma_w: {gamma_w:.4f}")

    # return beta_w * removal_cost * total_edge_removal_cost, cost_elements
    # return alpha_w * np.sum(newly_infected) + beta_w * removal_cost * total_edge_removal_cost + gamma_w * seed_set_size, cost_elements
    # return alpha_w * np.sum(newly_infected) + beta_w * removal_cost * total_edge_removal_cost, cost_elements
    return alpha_w * np.sum(newly_infected), cost_elements

def stepwise_cost_function(newly_infected_t, live_edges_t, seed_set_size):
    """
    Single-step cost: only considers what happened at time t.
    
    newly_infected_t : int, number of new infections this step
    live_edges_t     : list of edges alive at this step
    seed_set_size    : int, number of seeds active this step
    """

    # NOTE: for now assume cost is uniform across all edges
    all_edges = initial_contact.edges()

    removed_edges_t = len(set(all_edges) - set(live_edges_t))

    # Some cost function f: V -> Reals that maps edges to cost of removal
    edge_cost_dict = {edge: 1 for edge in all_edges}

    # Compute total possible cost of edge removals (if all edges were removed)
    edge_cost_bound = sum(edge_cost_dict[edge] for edge in all_edges)

    I_0 = init * n

    # alpha_w = 1 / (0.05 * n * T - I_0) # Assumption: n_i(0) = I_0, as in previous paper
    beta_w = 1 / (T * edge_cost_bound) # Assumption: all edges have cost 1
    gamma_w = 1 / (n)

    # Compute alpha_w stochasticly based on newly infected relative to baseline
    n_i_sums = []
    for i in range(num_simulations):
        baseline_newly_counts, _ = baseline_infections(i)
        n_i_sums.append(sum(baseline_newly_counts))
    max_sum = max(n_i_sums)

    alpha_w = 1 / max_sum

    return (alpha_w * newly_infected_t
            + beta_w * removed_edges_t
            + gamma_w * seed_set_size)

def hill_climb():
    K = 150
    k = int(K / 2)
    EWMA_alpha = 0.5
    epsilon = 1e-6  # Small constant to avoid division by zero

    winner_sets = []
    all_cost_curves = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_state_vectors = []

    for i in range(num_simulations):
        print("Simulation: ", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        # Randomly initialized utilities
        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        # Randomly initialize K many seeds
        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0 for node in contact_network.nodes()])
        prev_seed_vec = seed_vec.copy()

        cost_lst = []
        states_at_time = None
        prev_state_dict = None
        live_edge_at_time = None
        edge_counts = []
        last_batch_cost = None
        newly_infected_at_time = []
        newly_infected_frac_per_sim = []
        cur_informed = set()

        for t_cur in range(T):
            seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2: # Only infect if node is currently susceptible
                        prev_state_dict[node] = 1  # Infect these nodes at the start of this time step

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network, social_network=social_network,
                # Stepwise simulation: t=0 => no information spread beyond the current seeds
                T=0,
                beta=beta, gamma=gamma, mu=mu, init=init,
                # Quarantine mode: quarantine until recovery
                q=q,
                adherence=adherence,
                # Start quarantine immediately
                begin_q=0,
                # seeds=list(set(seed_set).union(cur_informed)),
                seeds=seed_set,
                # States from end of last step
                initial_state_dict=prev_state_dict
            )

            # Reset contact so initial connections are always known (but may be removed by quarantine)
            contact_network = deepcopy(initial_contact)
            # List of dictionaries
            sirs_states = simulation_results[4]
            # Dictionary from node to state at the end of this time step, to be fed into next step
            prev_state_dict = sirs_states[-1]
            # List of state dicts over time
            states_at_time = sirs_states if states_at_time is None else states_at_time + sirs_states

            new_informed = simulation_results[8][-1]
            cur_informed.update(new_informed)
            # Current new infections this step
            current_new_i = given_at_time(t_cur, states_at_time, contact_network)
            newly_infected_at_time.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            # Live edges this step
            graph_vec = simulation_results[10]
            live_edges = [list(edge_set) for edge_set in graph_vec]

            # Update time-series of live edges
            live_edge_at_time = live_edges if live_edge_at_time is None else live_edge_at_time + live_edges
            edge_counts.append(len(live_edges[-1]))

            # At batch boundary: compute cost, update utilities, flip seeds
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, _ = global_cost_function(newly_infected_at_time, live_edge_at_time, len(seed_set), t_cur)
                cost_lst.append(cost)

                # Stability-weighted utility update for active seeds
                num_active = max(sum(seed_vec), 1)
                hamming_dist = max(np.sum(seed_vec != prev_seed_vec), 1)

                for node in contact_network.nodes():
                    if seed_vec[node] == 1:
                        if last_batch_cost is None:
                            delta = 0.0
                        else:
                            delta = (cost - last_batch_cost) / (hamming_dist * num_active)

                        utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

                last_batch_cost = cost

                # Save current seed vec before flipping
                prev_seed_vec = seed_vec.copy()

                # Flip phase with revised probabilities (size-preserving)
                flip_bound = random.randint(1, k)
                for _ in range(flip_bound):
                    node = random.choice(list(contact_network.nodes()))
                    g = utilities[node]
                    if seed_vec[node] == 0:
                        flip_prob = 1.0 / (g + epsilon)
                        flip_prob = min(flip_prob, 1.0)
                        if random.random() < flip_prob:
                            # Flip this node ON, flip a random current seed OFF
                            current_seeds = [n for n in contact_network.nodes() if seed_vec[n] == 1]
                            if current_seeds:
                                drop_node = random.choice(current_seeds)
                                seed_vec[node] = 1
                                seed_vec[drop_node] = 0
                    else:
                        flip_prob = 1.0 - 1.0 / (g + epsilon)
                        flip_prob = max(flip_prob, 0.0)
                        if random.random() < flip_prob:
                            # Flip this node OFF, flip a random non-seed ON
                            non_seeds = [n for n in contact_network.nodes() if seed_vec[n] == 0]
                            if non_seeds:
                                add_node = random.choice(non_seeds)
                                seed_vec[node] = 0
                                seed_vec[add_node] = 1

        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        winner_sets.append(final_seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_at_time)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_state_vectors.append(states_at_time)

    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_state_vectors

# Degree based selection: at each time step, select top K nodes by degree in the CURRENT contact network as seeds
# Allows re-selection
def degree_based_selection():
    all_cost_curves = []
    winner_sets = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("Degree-based Simulation:", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        cost_lst = []
        full_dynamics = None
        prev_state_dict = None
        full_live_edges = None
        edge_counts = []
        seed_set = None
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # Current view of the graph
            current_graph = nx.Graph()
            # Ensure all nodes are present
            current_graph.add_nodes_from(contact_network.nodes())
            # Add edges from latest live edge time-series
            current_graph.add_edges_from(
                full_live_edges[-1] if full_live_edges else contact_network.edges()
            )

            # At batch boundary: select new seeds
            if t_cur % batch_interval == 0:
                degree_dict = dict(current_graph.degree())
                seed_set = sorted(degree_dict, key=lambda node: degree_dict[node], reverse=True)[:K]

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2:  # Only infect if node is currently susceptible
                        prev_state_dict[node] = 1
                infected_count = sum(1 for v in prev_state_dict.values() if v == 1)
                print(f"t={t_cur}: infected in prev_state_dict after injection = {infected_count}")

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=0,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=q,
                adherence=adherence,
                begin_q=0,
                seeds=seed_set,
                initial_state_dict=prev_state_dict
            )

            contact_network = deepcopy(initial_contact)

            sirs_dynamics = simulation_results[4]
            prev_state_dict = sirs_dynamics[-1]

            full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics
            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            graph_vec = simulation_results[10]
            live_edges = [list(network) for network in graph_vec]
            full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges
            edge_counts.append(len(live_edges[-1]))

            # At batch boundary: compute cost
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, _ = global_cost_function(
                    newly_infected_per_sim,
                    full_live_edges,
                    len(seed_set),
                    t_cur
                )
                cost_lst.append(cost)

        winner_sets.append(seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return winner_sets[0], all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics

def no_quarantine_baseline_runs():
    """
    Simulate with no quarantine (q=False) and no seeds.
    Cost = infections term only; edge removal cost = 0.
    """
    all_cost_curves = []
    all_edge_curves = []
    all_newly_counts = []
    all_newly_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("No-Quarantine Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        cost_lst = []
        full_dynamics = None
        prev_state_dict = None
        edge_counts = []
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2:
                        prev_state_dict[node] = 1

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=1,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=False,
                adherence=adherence,
                begin_q=0,
                initial_state_dict=prev_state_dict,
            )

            contact_network = deepcopy(initial_contact)
            sirs_dynamics = simulation_results[4]
            prev_state_dict = sirs_dynamics[-1]
            full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            graph_vec = simulation_results[10]
            live_edges = [list(network) for network in graph_vec]
            edge_counts.append(len(live_edges[-1]))

            # Cost = infections term only (no edge removal, no seeds)
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                g = max(sum(run[:t_cur + 1]) for run in baseline_runs)
                alpha_w = 1 / g if g > 0 else 1.0
                cost = alpha_w * np.sum(newly_infected_per_sim)
                cost_lst.append(cost)

        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_counts.append(newly_infected_per_sim)
        all_newly_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return all_cost_curves, all_edge_curves, all_newly_counts, all_newly_frac, all_full_dynamics


def plot_full_comparison(
    hill_cost_curves, degree_cost_curves,
    hill_edge_curves, degree_edge_curves,
    hill_counts, hill_frac,
    degree_counts, degree_frac,
    nq_cost_curves, nq_edge_curves,
    nq_counts, nq_frac,
    edge_mode="fraction",
    infect_mode="fraction",
):

    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    # --- cost ---
    hill_c_mean,   hill_c_std   = stats(hill_cost_curves)
    degree_c_mean, degree_c_std = stats(degree_cost_curves)
    nq_c_mean,     nq_c_std     = stats(nq_cost_curves)

    # --- edges ---
    hill_edges   = np.array(hill_edge_curves)
    degree_edges = np.array(degree_edge_curves)
    nq_edges     = np.array(nq_edge_curves)
    if edge_mode == "fraction":
        hill_edges   = hill_edges   / initial_edge_count
        degree_edges = degree_edges / initial_edge_count
        nq_edges     = nq_edges     / initial_edge_count
    hill_e_mean,   hill_e_std   = stats(hill_edges)
    degree_e_mean, degree_e_std = stats(degree_edges)
    nq_e_mean,     nq_e_std     = stats(nq_edges)

    # --- infected ---
    hill_i_mean,   hill_i_std   = stats(hill_frac   if infect_mode == "fraction" else hill_counts)
    degree_i_mean, degree_i_std = stats(degree_frac if infect_mode == "fraction" else degree_counts)
    nq_i_mean,     nq_i_std     = stats(nq_frac     if infect_mode == "fraction" else nq_counts)

    time = np.arange(len(hill_c_mean))

    # ── visual vocabulary ────────────────────────────────────────────────────
    COST_LW    = 2.6
    COMP_LW    = 1.2
    COST_ALPHA = 0.20
    COMP_ALPHA = 0.07

    hill_color   = "C0"
    degree_color = "C1"
    nq_color     = "C2"

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_inf = ax.twinx()  # right axis for infected fraction

    # ── background: edges (left axis) ───────────────────────────────────────
    for mean, std, label, color in [
        (hill_e_mean,   hill_e_std,   "Hill Climb – Edges",      hill_color),
        (degree_e_mean, degree_e_std, "Degree-Based – Edges",    degree_color),
        (nq_e_mean,     nq_e_std,     "No Quarantine – Edges",   nq_color),
    ]:
        ax.plot(time, mean, label=label, color=color,
                linestyle=(0, (4, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax.fill_between(time, mean - std, mean + std,
                        color=color, alpha=COMP_ALPHA, zorder=1)

    # ── background: infected (right axis) ───────────────────────────────────
    inf_max = max(
        (hill_i_mean   + hill_i_std).max(),
        (degree_i_mean + degree_i_std).max(),
        (nq_i_mean     + nq_i_std).max(),
    )
    ax_inf.set_ylim(0, inf_max)

    for mean, std, label, color in [
        (hill_i_mean,   hill_i_std,   "Hill Climb – Infected",    hill_color),
        (degree_i_mean, degree_i_std, "Degree-Based – Infected",  degree_color),
        (nq_i_mean,     nq_i_std,     "No Quarantine – Infected", nq_color),
    ]:
        ax_inf.plot(time, mean, label=label, color=color,
                    linestyle=(0, (1, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax_inf.fill_between(time, mean - std, mean + std,
                            color=color, alpha=COMP_ALPHA, zorder=1)

    # ── foreground: cost (left axis) ─────────────────────────────────────────
    for mean, std, label, color in [
        (hill_c_mean,   hill_c_std,   "Hill Climb – Cost",    hill_color),
        (degree_c_mean, degree_c_std, "Degree-Based – Cost",  degree_color),
        (nq_c_mean,     nq_c_std,     "No Quarantine – Cost", nq_color),
    ]:
        ax.plot(time, mean, label=label, color=color,
                linestyle="-", linewidth=COST_LW, zorder=4)
        ax.fill_between(time, mean - std, mean + std,
                        color=color, alpha=COST_ALPHA, zorder=3)

    # ── axis labels ──────────────────────────────────────────────────────────
    edge_ylabel   = "Live Edges"  if edge_mode   == "fraction" else "Live Edges"
    infect_ylabel = "Newly Infected Fraction" if infect_mode == "fraction" else "Number of Newly Infected"

    ax.set_xlabel("Time Step")
    ax.set_ylabel(f"Global Cost / {edge_ylabel}")
    ax_inf.set_ylabel(infect_ylabel, labelpad=10)

    ax.set_title("Adaptive Hill Climb vs Degree-Based – Cost & Components")

    # ── combined legend (cost first) ─────────────────────────────────────────
    handles_l, labels_l = ax.get_legend_handles_labels()
    handles_r, labels_r = ax_inf.get_legend_handles_labels()
    all_handles = handles_l[-3:] + handles_l[:-3] + handles_r
    all_labels  = labels_l[-3:]  + labels_l[:-3]  + labels_r
    ax.legend(all_handles, all_labels, ncols=2, fontsize=8)

    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig("capstone_result_figures/full_comparison.pdf", format="pdf")
    plt.show()

def plot_prevalence_and_new_infections(
    hill_counts, hill_frac,
    degree_counts, degree_frac,
    hill_dynamics_list, degree_dynamics_list,
    nq_counts, nq_frac,
    nq_dynamics_list,
    infect_mode="fraction",
):
    """
    Parameters
    ----------
    hill_dynamics_list : list of list of dict
        For each simulation, the full_dynamics: a list of T state dicts.
    degree_dynamics_list : same structure for degree-based runs.
    nq_dynamics_list : same structure for no-quarantine baseline runs.
    """

    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    # Compute prevalence (fraction in state 1) per simulation per timestep
    def prevalence_curves(dynamics_list):
        curves = []
        for dyn in dynamics_list:
            curve = [sum(1 for v in state_dict.values() if v == 1) / n for state_dict in dyn]
            curves.append(curve)
        return curves

    hill_prev   = prevalence_curves(hill_dynamics_list)
    degree_prev = prevalence_curves(degree_dynamics_list)
    nq_prev     = prevalence_curves(nq_dynamics_list)

    hill_prev_mean,   hill_prev_std   = stats(hill_prev)
    degree_prev_mean, degree_prev_std = stats(degree_prev)
    nq_prev_mean,     nq_prev_std     = stats(nq_prev)

    hill_data   = hill_frac   if infect_mode == "fraction" else hill_counts
    degree_data = degree_frac if infect_mode == "fraction" else degree_counts
    nq_data     = nq_frac     if infect_mode == "fraction" else nq_counts
    hill_ni_mean,   hill_ni_std   = stats(hill_data)
    degree_ni_mean, degree_ni_std = stats(degree_data)
    nq_ni_mean,     nq_ni_std     = stats(nq_data)

    time = np.arange(len(hill_ni_mean))

    hill_color   = "C0"
    degree_color = "C1"
    nq_color     = "C2"

    fig, ax_prev = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_ni = ax_prev.twinx()

    # Left axis: prevalence (solid)
    for mean, std, label, color in [
        (hill_prev_mean,   hill_prev_std,   "Hill Climb – Prevalence",    hill_color),
        (degree_prev_mean, degree_prev_std, "Degree-Based – Prevalence",  degree_color),
        (nq_prev_mean,     nq_prev_std,     "No Quarantine – Prevalence", nq_color),
    ]:
        ax_prev.plot(time, mean, label=label, color=color, linestyle="-", linewidth=2.5)
        ax_prev.fill_between(time, mean - std, mean + std, color=color, alpha=0.15)

    # Right axis: new infections (dashed)
    ni_label = "Newly Infected Fraction" if infect_mode == "fraction" else "Newly Infected Count"
    for mean, std, label, color in [
        (hill_ni_mean,   hill_ni_std,   f"Hill Climb – {ni_label}",    hill_color),
        (degree_ni_mean, degree_ni_std, f"Degree-Based – {ni_label}",  degree_color),
        (nq_ni_mean,     nq_ni_std,     f"No Quarantine – {ni_label}", nq_color),
    ]:
        ax_ni.plot(time, mean, label=label, color=color, linestyle="--", linewidth=1.5, alpha=0.7)
        ax_ni.fill_between(time, mean - std, mean + std, color=color, alpha=0.07)

    ax_prev.set_xlabel("Time Step")
    ax_prev.set_ylabel("Prevalence (Fraction Infected)")
    ax_ni.set_ylabel(ni_label, labelpad=10)
    ax_prev.set_title("Prevalence and Newly Infected: Hill Climb vs Degree-Based")

    handles_l, labels_l = ax_prev.get_legend_handles_labels()
    handles_r, labels_r = ax_ni.get_legend_handles_labels()
    ax_prev.legend(handles_l + handles_r, labels_l + labels_r, fontsize=8, ncols=2)

    ax_prev.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig("capstone_result_figures/prevalence_and_new_infections.pdf", format="pdf")
    plt.show()

if __name__ == "__main__":
    # Run hill climb
    _, hill_cost_curves, hill_edge_curves, hill_newly_counts, hill_newly_frac, hill_dynamics_list = hill_climb()

    # Run degree baseline
    _, degree_cost_curves, degree_edge_curves, degree_newly_counts, degree_newly_frac, degree_dynamics_list = degree_based_selection()

    # Run no-quarantine baseline
    nq_cost_curves, nq_edge_curves, nq_newly_counts, nq_newly_frac, nq_dynamics_list = no_quarantine_baseline_runs()

    # Plot comparison
    plot_full_comparison(
        hill_cost_curves, degree_cost_curves,
        hill_edge_curves, degree_edge_curves,
        hill_newly_counts, hill_newly_frac,
        degree_newly_counts, degree_newly_frac,
        nq_cost_curves, nq_edge_curves,
        nq_newly_counts, nq_newly_frac,
        edge_mode="fraction",
        infect_mode="fraction",
    )

    plot_prevalence_and_new_infections(
        hill_newly_counts, hill_newly_frac,
        degree_newly_counts, degree_newly_frac,
        hill_dynamics_list, degree_dynamics_list,
        nq_newly_counts, nq_newly_frac,
        nq_dynamics_list,
        infect_mode="fraction",
    )