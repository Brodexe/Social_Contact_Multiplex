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
initial_network = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
social_network = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)[0]
social_network = nx.erdos_renyi_graph(n, p, seed=24)

initial_social = deepcopy(social_network)
T = 100
# Homogeneous beta: everyone equally susceptible
beta = 0.15
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05
adherence = 1.0
num_simulations = 10
q = "r"
# Try introducing random infections in intervals to better differentiate methods
introduced_infections = (0.5, 10) # (fraction of population, time step to introduce)

# Returns newly infected at a given time step
def given_at_time(time, sirs_dynamics, contact_graph):
    if time > 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1 and sirs_dynamics[time-1][node] != 1)
    # Initial condition. We say that n_i(0) = i(0)
    elif time == 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1)

    return new_i

def baseline_infections():
    # Run SIR with no seeds, to get baseline infection curve for comparison
    simulation_results = SIR.Simulate_SIR(
        contact_network=contact_network,
        social_network=social_network,
        T=T,
        q=False,
        beta=beta,
        gamma=gamma,
        mu=mu,
        init=init,
    )

    sirs_dynamics = simulation_results[4]
    baseline_newly_counts = [given_at_time(t, sirs_dynamics, contact_network) for t in range(T)]
    baseline_newly_frac = [count / n for count in baseline_newly_counts]

    return baseline_newly_counts, baseline_newly_frac

# Compute alpha_w stochasticly based on newly infected relative to baseline
n_i_sums = []
for _ in range(num_simulations):
    baseline_newly_counts, _ = baseline_infections()
    n_i_sums.append(sum(baseline_newly_counts))
stochastic_max_n_i = max(n_i_sums)

# Global utility function: Find a small seed set which minimizes infection spread,
# while maximizing number of live edges in the network.
# newly_infected: array of newly infected ratios at each time step
# total_edges: integer number of edges in the original contact network
# live_edges: array EDGES that are live at each step
# seed_set_size: integer size of the seed set
def global_cost_function(newly_infected, live_edges, seed_set_size, t_cur):
    # NOTE: for now assume cost is uniform across all edges
    all_edges = initial_network.edges()

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
    I_0 = init * n

    # Adjust penalty weights so that each term contributes equally to cost function
    removal_cost = 1
    # NOTE: changed cost. Maybe the estimate for n_i was too high, causing the term to be undervalued?
    # alpha_w = 1 / (0.05 * n * T - I_0) # Assumption: n_i(0) = I_0, as in previous paper
    beta_w = 1 / (T * edge_cost_bound)
    gamma_w = 1 / (n)

    alpha_w = 1 / stochastic_max_n_i

    # return beta_w * removal_cost * total_edge_removal_cost, cost_elements
    # return alpha_w * np.sum(newly_infected) + beta_w * removal_cost * total_edge_removal_cost + gamma_w * seed_set_size, cost_elements
    return alpha_w * np.sum(newly_infected), cost_elements

def stepwise_cost_function(newly_infected_t, live_edges_t, seed_set_size):
    """
    Single-step cost: only considers what happened at time t.
    
    newly_infected_t : int, number of new infections this step
    live_edges_t     : list of edges alive at this step
    seed_set_size    : int, number of seeds active this step
    """

    # NOTE: for now assume cost is uniform across all edges
    all_edges = initial_network.edges()

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
    for _ in range(num_simulations):
        baseline_newly_counts, _ = baseline_infections()
        n_i_sums.append(sum(baseline_newly_counts))
    max_sum = max(n_i_sums)

    alpha_w = 1 / max_sum

    return (alpha_w * newly_infected_t
            + beta_w * removed_edges_t
            + gamma_w * seed_set_size)

def hill_climb(): 
    # Total number of seeds
    K = int(0.025 * n)
    # K = 2

    # Number of seeds allowed to flip from 1 to 0 (
    # or vice versa) in each iteration of the search
    # k = int(K / 2) 
    # k = int(0.025 * n)  # Allow some of population to flip each iteration, can adjust as needed
    k = 2

    # Adjustable parameter for EWMA update of utilities
    EWMA_alpha = 0.5

    winner_sets = [] 
    all_cost_curves = [] 
    all_edge_curves = [] 
    all_newly_infected_counts = [] 
    all_newly_infected_frac = [] 
    all_full_dynamics = []

    for i in range(num_simulations): 
        print("Simulation: ", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_network)
        social_network = deepcopy(initial_social)

        #------------
        #
        # Variable initialization
        #
        #------------

        # Utilities: dictionary from node to utility
        # Initialize node utilities to Uniform(0,1)
        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()} 

        # Randomly select K seeds
        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0 for node in contact_network.nodes()]) 

        # Holds costs for each seed set across all runs
        cost_lst = [] 

        # Holds the whole time-series of states
        full_dynamics = None 

        # Holds a single vector of states, from the previous time step
        prev_state_dict = None 

        # List of lists of live edges at each time step
        full_live_edges = None 
        edge_counts = [] 

        # Store old seeds to continue informing them in the next time step, 
        # even if they are not selected as seeds again
        seed_set_history = set() 

        newly_infected_per_sim = [] 
        newly_infected_frac_per_sim = [] 

        for t_cur in range(T): 
            # Create seed set from seed vector
            seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1] 
            seed_set_history.update(seed_set) 

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                num_to_infect = int(introduced_infections[0] * n)
                candidates = list(contact_network.nodes())
                new_infections = random.sample(candidates, min(num_to_infect, len(candidates)))
                for node in new_infections:
                    prev_state_dict[node] = 0  # Infect these nodes at the start of this time step

            #------------
            #
            # Adaptive seed selection algorithm
            #
            #------------

            # Run one step of SIR simulation with current seed set
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
                seeds=list(seed_set_history),
                # seeds=list(contact_network.nodes()),  # Inform everyone, to get accurate utilities even for non-seeds
                initial_state_dict=prev_state_dict
            ) 

            # Reset contact network. Reason: edge restoration function depends on initial contact structure,
            # so we need to preserve it. Quarantines will still function as expected, since they
            # happen before the SIRS step
            contact_network = deepcopy(initial_network) 
            sirs_dynamics = simulation_results[4] 

            # These states will be fed back into SIRS simulation for next time step
            prev_state_dict = sirs_dynamics[-1] 

            # Update full dynamics time series
            full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics 

            # Compute newly infected at this step
            current_new_i = given_at_time(t_cur, full_dynamics, contact_network) 

            # Append to newly infected time-series
            newly_infected_per_sim.append(current_new_i) 
            newly_infected_frac_per_sim.append(current_new_i / n) 

            graph_vec = simulation_results[10]  # Updated contact network edge lists after edge removals
            # Extract list of live edges at each time step
            live_edges = [list(network) for network in graph_vec] 
            # Append to live edge time-series
            full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges 
            edge_counts.append(len(live_edges[-1])) 

            # cost, _ = global_cost_function(newly_infected_per_sim, full_live_edges, len(seed_set), t_cur) 
            # cost_lst.append(cost) 

            cost = stepwise_cost_function(
                current_new_i,
                full_live_edges[-1],
                len(seed_set)
            )
            cost_lst.append(cost)

            # Update utilities based on cost
            for node in contact_network.nodes(): 
                if node in seed_set: 
                    if t_cur == 0: 
                        delta = 0  # No previous cost to compare to in the first iteration
                    else: 
                        # Compute marginal contribution of this node to cost reduction
                        delta = cost_lst[t_cur] - cost_lst[t_cur-1]  # Change in cost since last iteration

                    # Lower marginal cost (delta) should correspond to higher utility, reflected in update rule dictionary
                    utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node] 

            # Randomly flip up to k seeds based on utilities:
            # Bring in new seeds with high utility (low marginal cost)
            # Remove current seeds with low utility (high marginal cost)
            flip_bound = random.randint(1, k) 
            for _ in range(flip_bound): 
                node = random.choice(list(contact_network.nodes())) 
                if seed_vec[node] == 0:
                    flip_prob = 1 - utilities[node] 
                    if random.random() < flip_prob: 
                        seed_vec[node] = 1 
                else: 
                    flip_prob = utilities[node] 
                    if random.random() < flip_prob: 
                        seed_vec[node] = 0 

        # Now we have the final seed vector
        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1] 

        winner_sets.append(final_seed_set) 
        all_cost_curves.append(cost_lst) 
        all_edge_curves.append(edge_counts) 
        all_newly_infected_counts.append(newly_infected_per_sim) 
        all_newly_infected_frac.append(newly_infected_frac_per_sim) 
        all_full_dynamics.append(full_dynamics)

    # Pick most frequently set of seeds from winner sets
    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets) 
    most_common_seed_set = seed_set_counts.most_common(1)[0][0] 

    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics

def hill_climb_stability_weighted():
    K = int(0.025 * n)
    k = 2
    EWMA_alpha = 0.5
    epsilon = 1e-6  # Small constant to avoid division by zero

    winner_sets = []
    all_cost_curves = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("Simulation: ", i)

        contact_network = deepcopy(initial_network)
        social_network = deepcopy(initial_social)

        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0 for node in contact_network.nodes()])
        prev_seed_vec = seed_vec.copy()

        cost_lst = []
        full_dynamics = None
        prev_state_dict = None
        full_live_edges = None
        edge_counts = []
        seed_set_history = set()
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]
            seed_set_history.update(seed_set)

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                num_to_infect = int(introduced_infections[0] * n)
                candidates = list(contact_network.nodes())
                new_infections = random.sample(candidates, min(num_to_infect, len(candidates)))
                for node in new_infections:
                    prev_state_dict[node] = 0  # Infect these nodes at the start of this time step

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=1,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=q,
                adherence=adherence,
                begin_q=0,
                seeds=list(seed_set_history),
                initial_state_dict=prev_state_dict
            )

            contact_network = deepcopy(initial_network)
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

            cost, _ = global_cost_function(newly_infected_per_sim, full_live_edges, len(seed_set), t_cur)
            cost_lst.append(cost)

            # cost = stepwise_cost_function(
            #     current_new_i,
            #     full_live_edges[-1],
            #     len(seed_set)
            # )
            # cost_lst.append(cost)

            # Stability-weighted utility update for active seeds
            num_active = max(sum(seed_vec), 1)
            hamming_dist = max(np.sum(seed_vec != prev_seed_vec), 1)

            for node in contact_network.nodes():
                if seed_vec[node] == 1:
                    if t_cur == 0:
                        delta = 0.0
                    else:
                        delta = (cost_lst[t_cur] - cost_lst[t_cur - 1]) / (hamming_dist * num_active)

                    utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

            # Save current seed vec before flipping
            prev_seed_vec = seed_vec.copy()

            # Flip phase with revised probabilities
            flip_bound = random.randint(1, k)
            for _ in range(flip_bound):
                node = random.choice(list(contact_network.nodes()))
                g = utilities[node]
                if seed_vec[node] == 0:
                    flip_prob = 1.0 / (g + epsilon)
                    # Clamp to [0, 1] since 1/(G+eps) can exceed 1 for small G
                    flip_prob = min(flip_prob, 1.0)
                    if random.random() < flip_prob:
                        seed_vec[node] = 1
                else:
                    flip_prob = 1.0 - 1.0 / (g + epsilon)
                    flip_prob = max(flip_prob, 0.0)
                    if random.random() < flip_prob:
                        seed_vec[node] = 0

        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        winner_sets.append(final_seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics

# Degree based selection: at each time step, select top K nodes by degree in the CURRENT contact network as seeds
# Allows re-selection
def degree_based_selection():
    K = int(0.025 * n)
    # K = 5

    all_cost_curves = []
    winner_sets = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("Degree-based Simulation:", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_network)
        social_network = deepcopy(initial_social)

        cost_lst = []
        full_dynamics = None
        prev_state_dict = None
        full_live_edges = None
        edge_counts = []

        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # Current view of the graph
            current_graph = nx.Graph()
            current_graph.add_edges_from(
                full_live_edges[-1] if full_live_edges else contact_network.edges()
            )

            # Select top K nodes by current degree — no exclusions
            degree_dict = dict(current_graph.degree())
            seed_set = sorted(degree_dict, key=lambda n: degree_dict[n], reverse=True)[:K]

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                num_to_infect = int(introduced_infections[0] * n)
                candidates = list(contact_network.nodes())
                new_infections = random.sample(candidates, min(num_to_infect, len(candidates)))
                for node in new_infections:
                    prev_state_dict[node] = 0

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=1,
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

            contact_network = deepcopy(initial_network)

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

            cost, _ = global_cost_function(
                newly_infected_per_sim,
                full_live_edges,
                len(seed_set),
                t_cur
            )
            cost_lst.append(cost)

            # cost = stepwise_cost_function(
            #     current_new_i,
            #     full_live_edges[-1],
            #     len(seed_set)
            # )
            # cost_lst.append(cost)

        winner_sets.append(seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return winner_sets[0], all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics

def plot_full_comparison(
    hill_cost_curves, degree_cost_curves,
    hill_edge_curves, degree_edge_curves,
    hill_counts, hill_frac,
    degree_counts, degree_frac,
    edge_mode="fraction",
    infect_mode="fraction",
):

    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    # --- cost ---
    hill_c_mean,   hill_c_std   = stats(hill_cost_curves)
    degree_c_mean, degree_c_std = stats(degree_cost_curves)

    # --- edges ---
    hill_edges   = np.array(hill_edge_curves)
    degree_edges = np.array(degree_edge_curves)
    if edge_mode == "fraction":
        hill_edges   = hill_edges   / initial_edge_count
        degree_edges = degree_edges / initial_edge_count
    hill_e_mean,   hill_e_std   = stats(hill_edges)
    degree_e_mean, degree_e_std = stats(degree_edges)

    # --- infected ---
    hill_i_mean,   hill_i_std   = stats(hill_frac   if infect_mode == "fraction" else hill_counts)
    degree_i_mean, degree_i_std = stats(degree_frac if infect_mode == "fraction" else degree_counts)

    time = np.arange(len(hill_c_mean))

    # ── visual vocabulary ────────────────────────────────────────────────────
    COST_LW    = 2.6
    COMP_LW    = 1.2
    COST_ALPHA = 0.20
    COMP_ALPHA = 0.07

    hill_color   = "C0"
    degree_color = "C1"

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_inf = ax.twinx()  # right axis for infected fraction

    # ── background: edges (left axis) ───────────────────────────────────────
    for mean, std, label, color in [
        (hill_e_mean,   hill_e_std,   "Hill Climb – Edges",   hill_color),
        (degree_e_mean, degree_e_std, "Degree-Based – Edges", degree_color),
    ]:
        ax.plot(time, mean, label=label, color=color,
                linestyle=(0, (4, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax.fill_between(time, mean - std, mean + std,
                        color=color, alpha=COMP_ALPHA, zorder=1)

    # ── background: infected (right axis) ───────────────────────────────────
    inf_max = max(
        (hill_i_mean   + hill_i_std).max(),
        (degree_i_mean + degree_i_std).max(),
    )
    ax_inf.set_ylim(0, inf_max)

    for mean, std, label, color in [
        (hill_i_mean,   hill_i_std,   "Hill Climb – Infected",   hill_color),
        (degree_i_mean, degree_i_std, "Degree-Based – Infected", degree_color),
    ]:
        ax_inf.plot(time, mean, label=label, color=color,
                    linestyle=(0, (1, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax_inf.fill_between(time, mean - std, mean + std,
                            color=color, alpha=COMP_ALPHA, zorder=1)

    # ── foreground: cost (left axis) ─────────────────────────────────────────
    for mean, std, label, color in [
        (hill_c_mean,   hill_c_std,   "Hill Climb – Cost",   hill_color),
        (degree_c_mean, degree_c_std, "Degree-Based – Cost", degree_color),
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
    all_handles = handles_l[-2:] + handles_l[:-2] + handles_r
    all_labels  = labels_l[-2:]  + labels_l[:-2]  + labels_r
    ax.legend(all_handles, all_labels, ncols=2, fontsize=8)

    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig("capstone_result_figures/full_comparison.pdf", format="pdf")
    plt.show()

def plot_prevalence_and_new_infections(
    hill_counts, hill_frac,
    degree_counts, degree_frac,
    hill_dynamics_list, degree_dynamics_list,
    infect_mode="fraction",
):
    """
    Parameters
    ----------
    hill_dynamics_list : list of list of dict
        For each simulation, the full_dynamics: a list of T state dicts.
    degree_dynamics_list : same structure for degree-based runs.
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

    hill_prev = prevalence_curves(hill_dynamics_list)
    degree_prev = prevalence_curves(degree_dynamics_list)

    hill_prev_mean, hill_prev_std = stats(hill_prev)
    degree_prev_mean, degree_prev_std = stats(degree_prev)

    hill_data = hill_frac if infect_mode == "fraction" else hill_counts
    degree_data = degree_frac if infect_mode == "fraction" else degree_counts
    hill_ni_mean, hill_ni_std = stats(hill_data)
    degree_ni_mean, degree_ni_std = stats(degree_data)

    time = np.arange(len(hill_ni_mean))

    hill_color = "C0"
    degree_color = "C1"

    fig, ax_prev = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_ni = ax_prev.twinx()

    # Left axis: prevalence (solid)
    for mean, std, label, color in [
        (hill_prev_mean, hill_prev_std, "Hill Climb – Prevalence", hill_color),
        (degree_prev_mean, degree_prev_std, "Degree-Based – Prevalence", degree_color),
    ]:
        ax_prev.plot(time, mean, label=label, color=color, linestyle="-", linewidth=2.5)
        ax_prev.fill_between(time, mean - std, mean + std, color=color, alpha=0.15)

    # Right axis: new infections (dashed)
    ni_label = "Newly Infected Fraction" if infect_mode == "fraction" else "Newly Infected Count"
    for mean, std, label, color in [
        (hill_ni_mean, hill_ni_std, f"Hill Climb – {ni_label}", hill_color),
        (degree_ni_mean, degree_ni_std, f"Degree-Based – {ni_label}", degree_color),
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
    # _, hill_cost_curves, hill_edge_curves, hill_newly_counts, hill_newly_frac, hill_dynamics_list = hill_climb()

    # Run stability-weighted hill climb
    _, hill_cost_curves, hill_edge_curves, hill_newly_counts, hill_newly_frac, hill_dynamics_list = hill_climb_stability_weighted()

    # Run degree baseline
    _, degree_cost_curves, degree_edge_curves, degree_newly_counts, degree_newly_frac, degree_dynamics_list = degree_based_selection()

    # Plot comparison
    plot_full_comparison(
        hill_cost_curves, degree_cost_curves,
        hill_edge_curves, degree_edge_curves,
        hill_newly_counts, hill_newly_frac,
        degree_newly_counts, degree_newly_frac,
        edge_mode="fraction",
        infect_mode="fraction",
    )

    plot_prevalence_and_new_infections(
        hill_newly_counts, hill_newly_frac,
        degree_newly_counts, degree_newly_frac,
        hill_dynamics_list, degree_dynamics_list,
        infect_mode="fraction",
    )