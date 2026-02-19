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

n = 100
p = 0.05
contact_network = nx.erdos_renyi_graph(n, p, seed=42)
initial_network = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
social_network = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)[0]
T = 100
beta = 0.15
gamma = 0.05
mu = 0.03
init = 0.10
adherence = 1.0
num_simulations = 10

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
    # Compute sum of costs of removed edges at each time step
    for t in range(t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    cost_elements = (np.sum(newly_infected), total_edge_removal_cost, seed_set_size)
    I_0 = init * n

    # Adjust penalty weights so that each term contributes equally to cost function
    removal_cost = 1
    alpha_w = 1 / (n * T - I_0) # Assumption: n_i(0) = I_0, as in previous paper

    beta_w = 1 / (T * edge_cost_bound)
    gamma_w = 1 / (n)

    return alpha_w * np.sum(newly_infected) + beta_w * removal_cost * np.sum(edge_removals) + gamma_w * seed_set_size, cost_elements

def given_at_time(time, sirs_dynamics, contact_graph):
    if time > 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1 and sirs_dynamics[time-1][node] != 1)
    # Initial condition. We say that n_i(0) = i(0)
    elif time == 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1)

    return (new_i)

# Algorithm to adaptively select seeds at each time step,
# based on previous utilities of each node
def hill_climb():
    # Total number of seeds
    K = int(n / 4)
    # Number of seeds allowed to flip from 1 to 0 (
    #  or vice versa) in each iteration of the search
    # k = int(K / 2)
    k = K
    # Adjustable parameter for EWMA update of utilities
    EWMA_alpha = 1.0

    winner_sets = []
    all_cost_curves = []

    for i in range(num_simulations):
        print("Simulation: ", i)

        #------------
        #
        #  Variable initialization
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

        for t_cur in range(T):
            # Create seed set from seed vector
            seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

            #------------
            #
            #  Adaptive seed selection algorithm
            #
            #------------

            # Run one step of SIR simulation with current seed set
            simulation_results = SIR.Simulate_SIR(contact_network=contact_network,social_network=social_network,T=1,beta=beta,gamma=gamma,mu=mu,init=init,
                            q="r",adherence=adherence,begin_q=0,seeds=seed_set,initial_state_dict=prev_state_dict)
            sirs_dynamics = simulation_results[4]

            # These states will be fed back into SIRS simulation for next time step
            prev_state_dict = sirs_dynamics[0]

            # Update full dynamics time series
            full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics
            newly_infected = [given_at_time(t, full_dynamics, contact_network) for t in range(t_cur + 1)]
            graph_vec = simulation_results[10] # Updated contact network edge lists after edge removals

            # Extract list of live edges at each time step
            live_edges = [list(network) for network in graph_vec]

            print("Number of edges in last snapshot: ", len(live_edges[-1]))

            full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges

            cost, _ = global_cost_function(newly_infected, full_live_edges, len(seed_set), t_cur)
            cost_lst.append(cost)

            # Update utilities based on cost
            for node in contact_network.nodes():
                if node in seed_set:
                    if t_cur == 0:
                        delta = 0  # No previous cost to compare to in the first iteration
                    else:
                        # Compute marginal contribution of this node to cost reduction
                        delta = cost_lst[t_cur] - cost_lst[t_cur-1]  # Change in cost since last iteration

                    # If node is in seed set, increase utility if it contributed to lower cost
                    utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

            # Randomly flip up to k seeds based on utilities:
            # 0->1 with probability proportional to utility, 1->0 with probability proportional to (1 - utility)
            flip_bound = random.randint(1, k)
            for _ in range(flip_bound):
                node = random.choice(list(contact_network.nodes()))
                # Bring in new seed with probability proportional to utility, 
                # or remove existing seed with probability proportional to (1 - utility)
                if seed_vec[node] == 0:
                    flip_prob = utilities[node]
                    if random.random() < flip_prob:
                        seed_vec[node] = 1
                else:
                    flip_prob = (1 - utilities[node])
                    if random.random() < flip_prob:
                        seed_vec[node] = 0

        # Now we have the final seed vector
        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        winner_sets.append(final_seed_set)
        all_cost_curves.append(cost_lst)

    # Pick most frequently set of seeds from winner sets
    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    return most_common_seed_set, all_cost_curves

# At each time step, choose the K nodes with highest degree 
#  in the contact network as seeds for the next time step
# At each time step, choose the K nodes with highest degree 
# in the contact network as seeds for the next time step
def degree_based_selection():
    contact_network = deepcopy(initial_network)
    K = 1

    all_cost_curves = []
    winner_sets = []

    for i in range(num_simulations):
        print("Degree-based Simulation:", i)

        cost_lst = []

        full_dynamics = None
        prev_state_dict = None
        full_live_edges = None

        for t_cur in range(T):
            # --- Select top-K highest degree nodes ---
            current_graph = nx.Graph()
            current_graph.add_edges_from(full_live_edges[-1] if full_live_edges else contact_network.edges())
            
            # Rank nodes by degree in the modified contact network (after edge removals)
            degree_dict = dict(current_graph.degree())

            sorted_nodes = sorted(degree_dict, key=degree_dict.get, reverse=True)
            seed_set = sorted_nodes[:K]

            # --- Run one-step SIR ---
            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=1,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q="r",
                adherence=adherence,
                begin_q=0,
                seeds=seed_set,
                initial_state_dict=prev_state_dict
            )

            sirs_dynamics = simulation_results[4]
            prev_state_dict = sirs_dynamics[0]

            # Accumulate full time-series
            full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics

            newly_infected = [given_at_time(t, full_dynamics, contact_network) for t in range(t_cur + 1)]

            graph_vec = simulation_results[10]
            live_edges = [list(network) for network in graph_vec]

            print("Number of edges in last snapshot: ", len(live_edges[-1]))

            full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges

            cost, _ = global_cost_function(
                newly_infected,
                full_live_edges,
                len(seed_set),
                t_cur
            )

            cost_lst.append(cost)

        winner_sets.append(seed_set)
        all_cost_curves.append(cost_lst)

    # Test: see if every element of full_live_edges is the same
    if full_live_edges:
        first_snapshot_edges = set(full_live_edges[0])
        for snapshot_edges in full_live_edges[1:]:
            if set(snapshot_edges) != first_snapshot_edges:
                print("Live edges differ across time steps.")
                break
        else:
            print("Live edges are the same across all time steps.")

    return winner_sets[0], all_cost_curves

def plot_comparison(hill_cost_curves, degree_cost_curves):
    hill_cost_curves = np.array(hill_cost_curves)
    degree_cost_curves = np.array(degree_cost_curves)

    # Mean and std across simulations
    hill_mean = np.mean(hill_cost_curves, axis=0)
    hill_std = np.std(hill_cost_curves, axis=0)

    degree_mean = np.mean(degree_cost_curves, axis=0)
    degree_std = np.std(degree_cost_curves, axis=0)

    time = np.arange(len(hill_mean))

    plt.figure()  # No figsize — use global defaults

    # Hill climb
    plt.plot(time, hill_mean, label="Hill Climb (Adaptive)")
    plt.fill_between(time,
                     hill_mean - hill_std,
                     hill_mean + hill_std,
                     alpha=0.2)

    # Degree-based
    plt.plot(time, degree_mean, label="Degree-Based")
    plt.fill_between(time,
                     degree_mean - degree_std,
                     degree_mean + degree_std,
                     alpha=0.2)

    plt.xlabel("Time Step")
    plt.ylabel("Global Cost")
    plt.title("Adaptive Hill Climb vs Degree-Based Selection")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# See what the cost would be if every node where informed at the start,
#  vs if no node was informed
def all_seeds_no_seeds():
    nodes = contact_network.nodes()

    # Inform every node
    all_inform_cost = []
    for i in range(num_simulations):
        print("Executing run # ", i)
        
        simulation_results = SIR.Simulate_SIR(contact_network=contact_network,social_network=social_network,T=T,beta=beta,gamma=gamma,mu=mu,init=init,
                q="r",adherence=adherence,begin_q=0,seeds=nodes)
        sirs_dynamics = simulation_results[4]
        newly_infected = [given_at_time(t, sirs_dynamics, contact_network, n) for t in range(T)]
        graph_vec = simulation_results[10] # Updated contact network edge lists after edge removals
        # Extract list of live edges at each time step
        live_edges = [list(network) for network in graph_vec]

        cost_a, _ = global_cost_function(newly_infected, initial_edge_count, live_edges, n)
        all_inform_cost.append(cost_a)

    all_inform_cost = np.mean(all_inform_cost)

    # Inform no nodes
    no_inform_cost = []
    for i in range(num_simulations):
        print("Executing run # ", i)

        simulation_results = SIR.Simulate_SIR(contact_network=contact_network,social_network=social_network,T=T,beta=beta,gamma=gamma,mu=mu,init=init,
                q=False)
        sirs_dynamics = simulation_results[4]
        newly_infected = [given_at_time(t, sirs_dynamics, contact_network, n) for t in range(T)]
        graph_vec = simulation_results[10] # Updated contact network edge lists after edge removals
        # Extract list of live edges at each time step
        live_edges = [list(network) for network in graph_vec]

        cost_n, _ = global_cost_function(newly_infected, initial_edge_count, live_edges, n)
        no_inform_cost.append(cost_n)

    no_inform_cost = np.mean(no_inform_cost)

    return all_inform_cost, no_inform_cost

if __name__ == "__main__":
    # cost_all_informed, cost_none_informed = all_seeds_no_seeds()

    # print("Cost when all individuals are informed initially: ", cost_all_informed)
    # print("Cost when no individuals are informed initially: ", cost_none_informed)

    # Run hill climb
    _, hill_cost_curves = hill_climb()

    # Run degree baseline
    _, degree_cost_curves = degree_based_selection()

    # Plot comparison
    plot_comparison(hill_cost_curves, degree_cost_curves)