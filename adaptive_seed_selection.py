import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import SIR
import random
import correlated_graphs
from collections import Counter
from copy import deepcopy
import py4cytoscape as p4c

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

ping_cytoscape = True

p = 0.05

# Simulation parameters (network-independent)
T = 100
HETEROGENEOUS_BETA = True  # True: node-wise beta drawn from power-law distribution; False: scalar beta for all nodes
beta = 0.15  # Used directly when HETEROGENEOUS_BETA=False; ignored when True
beta_L = 0.05   # Lower bound for heterogeneous beta
beta_R = 0.25   # Upper bound for heterogeneous beta
Gamma  = 2      # Shape parameter: higher values skew beta toward beta_R
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05
adherence = 1.0
num_simulations = 10
batch_interval = 1  # Seeds and cost updated once every batch_interval steps
q = "r"
# Try introducing random infections in intervals to better differentiate methods
introduced_infections = (0, 1) # (fraction of population, time step to introduce)

# DEFAULT_NETWORK = "capstone_proj_data/rc_weighted_contact_bin14.gml"
DEFAULT_NETWORK = nx.erdos_renyi_graph(200, p)

# Network-dependent globals — populated by initialize()
contact_network   = None
initial_contact   = None
initial_edge_count = None
n                 = None
social_network    = None
initial_social    = None
K                 = None
injection_times   = None
_num_to_infect    = None
infection_candidates = None
baseline_runs     = None
global_betas      = None  # List of beta maps (one per simulation), computed once in initialize()

def make_initial_state(graph):
    nodes = list(graph.nodes())
    num_infected = int(init * len(nodes))
    infected = set(random.sample(nodes, num_infected))
    return {node: (1 if node in infected else 0) for node in nodes}


def sample_betas(num_nodes, beta_low, beta_high, lam=2.0, seed=None):
    rng = np.random.default_rng(seed)
    u = rng.uniform(0, 1, size=num_nodes)
    return beta_low + (beta_high - beta_low) * u ** lam

def laplacian_rank_beta(G, betas, alpha=0.1, seed=None):
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())
    n = len(nodes)

    A = nx.to_numpy_array(G, nodelist=nodes)
    D = np.diag(A.sum(axis=1))
    L = D - A

    z = rng.normal(0, 1, n)
    z_prime = (np.eye(n) + alpha * L) @ z

    order = np.argsort(z_prime)
    sorted_nodes = [nodes[i] for i in order]
    sorted_betas = betas[order]

    return dict(zip(sorted_nodes, sorted_betas))

def compute_node_beta(_state_dict, graph):
    if not HETEROGENEOUS_BETA:
        return beta

    betas = sample_betas(len(graph.nodes()), beta_L, beta_R, lam=Gamma)
    return laplacian_rank_beta(graph, betas)


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

def baseline_infections(sim_index=0):
    contact_network = deepcopy(initial_contact)
    social_network = deepcopy(initial_social)

    full_dynamics = None

    prev_state_dict = make_initial_state(contact_network)
    static_beta = global_betas[sim_index]
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
            beta=static_beta,
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

# network: NetworkX graph, or string path to GML file
def initialize(network=DEFAULT_NETWORK):
    """Load a contact network and run baseline simulations.  Must be called
    once before any simulation function (hill2, degree_based_selection, etc.)."""
    global contact_network, initial_contact, initial_edge_count, n
    global social_network, initial_social, K
    global injection_times, _num_to_infect, infection_candidates, baseline_runs
    global global_betas

    contact_network = nx.read_gml(network) if isinstance(network, str) else network
    isolated_nodes = [node for node in contact_network.nodes()
                      if contact_network.degree(node) == 0]
    contact_network.remove_nodes_from(isolated_nodes)
    contact_network = nx.convert_node_labels_to_integers(contact_network, first_label=0)

    initial_contact    = deepcopy(contact_network)
    initial_edge_count = contact_network.number_of_edges()
    n                  = len(contact_network.nodes())

    # NOTE: structure of social network doesn't matter for this experiment
    social_network = nx.DiGraph()
    social_network.add_nodes_from(contact_network.nodes())
    initial_social = deepcopy(social_network)

    K = int((3/4) * n)  # Number of seeds to select at each batch

    # Pre-generate infection targets so every method sees the same nodes targeted per
    # simulation and per injection time step.  Shape: [num_simulations][num_injection_steps]
    injection_times  = [t for t in range(1, T) if t % introduced_infections[1] == 0]
    _num_to_infect   = int(introduced_infections[0] * n)
    infection_candidates = [
        [random.sample(list(initial_contact.nodes()), min(_num_to_infect, n))
         for _ in injection_times]
        for _ in range(num_simulations)
    ]

    if n == 0:
        baseline_runs = []
        global_betas = []
        return

    # Compute beta maps once so every solver and baseline uses identical values per simulation
    global_betas = [compute_node_beta(None, initial_contact) for _ in range(num_simulations)]

    # Collect per-timestep newly infected counts from baseline runs
    baseline_runs = []
    for i in range(num_simulations):
        baseline_newly_counts, _ = baseline_infections(i)
        baseline_runs.append(baseline_newly_counts)


def build_tagged_network(beta_map):
    """Return a copy of initial_contact annotated with node 'beta'/'node_id' attributes
    and edge 'cost' attributes drawn from GML edge weights where present."""
    tagged = deepcopy(initial_contact)
    bm = beta_map if isinstance(beta_map, dict) else {node: beta_map for node in tagged.nodes()}
    nx.set_node_attributes(tagged, bm, "beta")
    nx.set_node_attributes(tagged, {node: node for node in tagged.nodes()}, "node_id")
    for u, v, data in tagged.edges(data=True):
        if 'weight' in data:
            tagged[u][v]['cost'] = data['weight']
    return tagged

def send_to_cytoscape(tagged_network, title="Contact Network"):
    if ping_cytoscape:
        p4c.create_network_from_networkx(tagged_network, title=title)


# Global utility function: Find a small seed set which minimizes infection spread,
# while maximizing number of live edges in the network.
# newly_infected: array of newly infected ratios at each time step
# total_edges: integer number of edges in the original contact network
# live_edges: array EDGES that are live at each step
# seed_set_size: integer size of the seed set
def global_cost_function(newly_infected, live_edges, seed_set_size, t_cur):
    all_edges = initial_contact.edges()

    edge_cost_dict = {(u, v): data.get('weight', 1) for u, v, data in initial_contact.edges(data=True)}

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

    # return beta_w * total_edge_removal_cost, cost_elements
    # return alpha_w * np.sum(newly_infected) + beta_w * total_edge_removal_cost + gamma_w * seed_set_size, cost_elements
    return alpha_w * np.sum(newly_infected) + beta_w * total_edge_removal_cost, cost_elements
    # return alpha_w * np.sum(newly_infected), cost_elements

def hill_climb():
    k = K  # Max number of seeds to flip per batch
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

        # Utility initialization
        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        # Randomly initialize K many seeds
        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0 for node in contact_network.nodes()])
        prev_seed_vec = seed_vec.copy()

        cost_lst = []
        states_at_time = None
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]

        live_edge_at_time = None
        edge_counts = []
        last_batch_cost = None
        newly_infected_at_time = []
        newly_infected_frac_per_sim = []

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
                beta=static_beta, gamma=gamma, mu=mu, init=init,
                # Quarantine mode: quarantine until recovery
                q=q,
                adherence=adherence,
                # Start quarantine immediately
                begin_q=0,
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
                            delta = (last_batch_cost - cost) / (hamming_dist * num_active)

                        utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

                last_batch_cost = cost

                # Save current seed vec before flipping
                prev_seed_vec = seed_vec.copy()

                # Flip phase
                flip_bound = random.randint(1, k)
                for _ in range(flip_bound):
                    node = random.choice(list(contact_network.nodes()))
                    g = utilities[node]
                    if seed_vec[node] == 0:
                        flip_prob = 1 - 1.0 / (g + epsilon)
                        flip_prob = max(flip_prob, 0)
                        if random.random() < flip_prob:
                            # Flip this node ON, flip a random current seed OFF
                            current_seeds = [n for n in contact_network.nodes() if seed_vec[n] == 1]
                            if current_seeds:
                                drop_node = random.choice(current_seeds)
                                seed_vec[node] = 1
                                seed_vec[drop_node] = 0
                    else:
                        flip_prob = 1.0 / (g + epsilon)
                        flip_prob = min(flip_prob, 1.0)
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

    tagged = build_tagged_network(global_betas[0])
    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_state_vectors, tagged

# Stochastic hill-climber that considers exactly one seed swap per batch step.
# For each node in a shuffled order, it tentatively swaps it in/out (removing the
# lowest-softmax-utility active seed when adding, or a random non-seed when removing),
# accepts the first cost-improving swap, and updates per-node utilities with EWMA of
# the cost delta — mirroring the Hill2.py Hamming-distance logic but driven by the
# global cost function instead.
def hill2():
    EWMA_alpha = 0.5

    winner_sets = []
    all_cost_curves = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_state_vectors = []

    for i in range(num_simulations):
        print("Hill-Climb Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0
                             for node in contact_network.nodes()])
        new_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        cost_lst = []
        states_at_time = None
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]

        live_edge_at_time = None
        edge_counts = []
        last_batch_cost = None
        newly_infected_at_time = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # Seed set to modify
            S_new = seed_vec.copy()
            # Seet set to revert to if needed
            S_save = seed_vec.copy()

            # Introduce infections at batch boundary
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2:
                        prev_state_dict[node] = 1

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network, social_network=social_network,
                T=0,
                beta=static_beta, gamma=gamma, mu=mu, init=init,
                q=q,
                adherence=adherence,
                begin_q=0,
                seeds=new_seed_set,
                initial_state_dict=prev_state_dict
            )

            contact_network = deepcopy(initial_contact)
            sirs_states = simulation_results[4]
            prev_state_dict = sirs_states[-1]
            states_at_time = sirs_states if states_at_time is None else states_at_time + sirs_states

            current_new_i = given_at_time(t_cur, states_at_time, contact_network)
            newly_infected_at_time.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            graph_vec = simulation_results[10]
            live_edges = [list(edge_set) for edge_set in graph_vec]
            live_edge_at_time = live_edges if live_edge_at_time is None else live_edge_at_time + live_edges
            edge_counts.append(len(live_edges[-1]))

            # Perform swapping operation only at batch boundaries
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, _ = global_cost_function(newly_infected_at_time, live_edge_at_time, len(new_seed_set), t_cur)
                cost_lst.append(cost)
                # NOTE: Hamming should be here?
                delta = (last_batch_cost - cost) if last_batch_cost is not None else 0.0

                for node in contact_network.nodes():
                    # EWMA utility update for the candidate node
                    utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

                # If swap was not an improvement, revert to last accepted seed_vec
                if last_batch_cost is not None and cost <= last_batch_cost:
                    seed_vec = S_new
                else:
                    seed_vec = S_save

                # Single-swap hill-climb: iterate nodes in random order, accept first improvement
                nodes = list(contact_network.nodes())
                random.shuffle(nodes)

                S_new = seed_vec.copy()
                S_save = seed_vec.copy()

                #--------------
                #
                #  Perform atmost 1 swap-per batch
                #   Accept if cost improves
                #
                #--------------

                for node in nodes:
                    # If this node is not a seed
                    if seed_vec[node] == 0:
                        # Try adding this node: remove the active seed with lowest softmax utility
                        active_seeds = [j for j in contact_network.nodes() if seed_vec[j] == 1]
                        if not active_seeds:
                            continue
                        weights = np.array([np.exp(-utilities[j]) for j in active_seeds])
                        probs = weights / weights.sum()
                        drop_node = np.random.choice(active_seeds, p=probs)
                        S_new[drop_node] = 0
                        S_new[node] = 1
                        break
                    # If this node is currently a seed
                    else:
                        # Try removing this node: add a random non-seed to compensate
                        non_seeds = [j for j in contact_network.nodes() if seed_vec[j] == 0]
                        if not non_seeds:
                            continue
                        add_node = random.choice(non_seeds)
                        S_new[node] = 0
                        S_new[add_node] = 1
                        break

                new_seed_set = [j for j in contact_network.nodes() if S_new[j] == 1]
                last_batch_cost = cost

        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]
        winner_sets.append(final_seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_at_time)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_state_vectors.append(states_at_time)

    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    tagged = build_tagged_network(global_betas[0])
    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_state_vectors, tagged

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
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]
        full_live_edges = None
        edge_counts = []
        seed_set = None
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # Current view of the graph with original edge weights preserved
            current_graph = nx.Graph()
            current_graph.add_nodes_from(contact_network.nodes())
            if full_live_edges:
                live_edge_set = set(tuple(sorted(e)) for e in full_live_edges[-1])
                for u, v, data in initial_contact.edges(data=True):
                    if tuple(sorted((u, v))) in live_edge_set:
                        current_graph.add_edge(u, v, **data)
            else:
                current_graph.add_edges_from(initial_contact.edges(data=True))

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
                beta=static_beta,
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

    tagged = build_tagged_network(global_betas[0])
    return winner_sets[0], all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics, tagged

def random_seed_selection():
    all_cost_curves = []
    winner_sets = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("Random Seed Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        cost_lst = []
        full_dynamics = None
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]
        full_live_edges = None
        edge_counts = []
        seed_set = None
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # At batch boundary: select K random seeds
            if t_cur % batch_interval == 0:
                seed_set = random.sample(list(contact_network.nodes()), K)

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2:
                        prev_state_dict[node] = 1

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=0,
                beta=static_beta,
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

    tagged = build_tagged_network(global_betas[0])
    return winner_sets[0], all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics, tagged


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
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]
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
                beta=static_beta,
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

    tagged = build_tagged_network(global_betas[0])
    return all_cost_curves, all_edge_curves, all_newly_counts, all_newly_frac, all_full_dynamics, tagged


def plot_beta_histogram(tagged_network, bins=20):
    """Histogram of per-node transmission rates, illustrating the power-law assignment."""
    betas = [data['beta'] for _, data in tagged_network.nodes(data=True) if 'beta' in data]
    if not betas:
        print("No beta attributes found on tagged network nodes.")
        return

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax.hist(betas, bins=bins, edgecolor='black', color='steelblue')
    ax.set_xlabel("Transmission Rate (beta)")
    ax.set_ylabel("Node Count")
    ax.set_title("Distribution of Node-Level Transmission Rates")
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig("capstone_result_figures/beta_histogram.pdf", format="pdf", bbox_inches="tight")
    plt.show()


def plot_full_comparison(
    methods,
    edge_mode="fraction",
    infect_mode="fraction",
):
    """
    Parameters
    ----------
    methods : list of dicts, each with keys:
        'label'       : str   – display name (e.g. "Hill Climb")
        'color'       : str   – matplotlib color (e.g. "C0")
        'cost_curves' : list of lists
        'edge_curves' : list of lists
        'counts'      : list of lists   (newly-infected counts)
        'frac'        : list of lists   (newly-infected fractions)
    Any number of methods ≥ 1 is accepted.
    """

    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    for m in methods:
        edges = np.array(m["edge_curves"])
        if edge_mode == "fraction":
            edges = edges / initial_edge_count
        inf_data = m["frac"] if infect_mode == "fraction" else m["counts"]
        m["_c_mean"], m["_c_std"] = stats(m["cost_curves"])
        m["_e_mean"], m["_e_std"] = stats(edges)
        m["_i_mean"], m["_i_std"] = stats(inf_data)

    time = np.arange(len(methods[0]["_c_mean"]))

    COST_LW    = 2.6
    COMP_LW    = 1.2
    COST_ALPHA = 0.20
    COMP_ALPHA = 0.07

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_inf = ax.twinx()

    # ── background: edges (left axis) ───────────────────────────────────────
    for m in methods:
        ax.plot(time, m["_e_mean"], label=f"{m['label']} – Edges", color=m["color"],
                linestyle=(0, (4, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax.fill_between(time, m["_e_mean"] - m["_e_std"], m["_e_mean"] + m["_e_std"],
                        color=m["color"], alpha=COMP_ALPHA, zorder=1)

    # ── background: infected (right axis) ───────────────────────────────────
    inf_max = max((m["_i_mean"] + m["_i_std"]).max() for m in methods)
    ax_inf.set_ylim(0, inf_max)

    for m in methods:
        ax_inf.plot(time, m["_i_mean"], label=f"{m['label']} – Infected", color=m["color"],
                    linestyle=(0, (1, 2)), linewidth=COMP_LW, alpha=0.55, zorder=2)
        ax_inf.fill_between(time, m["_i_mean"] - m["_i_std"], m["_i_mean"] + m["_i_std"],
                            color=m["color"], alpha=COMP_ALPHA, zorder=1)

    # ── foreground: cost (left axis) ─────────────────────────────────────────
    for m in methods:
        ax.plot(time, m["_c_mean"], label=f"{m['label']} – Cost", color=m["color"],
                linestyle="-", linewidth=COST_LW, zorder=4)
        ax.fill_between(time, m["_c_mean"] - m["_c_std"], m["_c_mean"] + m["_c_std"],
                        color=m["color"], alpha=COST_ALPHA, zorder=3)

    # ── axis labels ──────────────────────────────────────────────────────────
    edge_ylabel   = "Live Edges"
    infect_ylabel = "Newly Infected Fraction" if infect_mode == "fraction" else "Number of Newly Infected"

    ax.set_xlabel("Time Step")
    ax.set_ylabel(f"Global Cost / {edge_ylabel}")
    ax_inf.set_ylabel(infect_ylabel, labelpad=10)
    ax.set_title("Cost Comparison of Intervention Methods")

    # ── combined legend: cost curves first, then edge/infected ───────────────
    n = len(methods)
    handles_l, labels_l = ax.get_legend_handles_labels()
    handles_r, labels_r = ax_inf.get_legend_handles_labels()
    # left axis order: edges (first n), then cost (last n)
    all_handles = handles_l[-n:] + handles_l[:-n] + handles_r
    all_labels  = labels_l[-n:]  + labels_l[:-n]  + labels_r
    ax.legend(all_handles, all_labels, ncols=2, fontsize=10,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              bbox_transform=ax.transAxes)

    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.32)
    fig.savefig("capstone_result_figures/full_comparison.pdf", format="pdf", bbox_inches="tight")
    plt.show()

def plot_prevalence_and_new_infections(
    methods,
    infect_mode="fraction",
):
    """
    Parameters
    ----------
    methods : list of dicts, each with keys:
        'label'         : str   – display name
        'color'         : str   – matplotlib color
        'counts'        : list of lists   (newly-infected counts per run)
        'frac'          : list of lists   (newly-infected fractions per run)
        'dynamics_list' : list of list of dict  (full state vectors per run)
    Any number of methods ≥ 1 is accepted.
    """

    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    def prevalence_curves(dynamics_list):
        curves = []
        for dyn in dynamics_list:
            curve = [sum(1 for v in state_dict.values() if v == 1) / n for state_dict in dyn]
            curves.append(curve)
        return curves

    for m in methods:
        prev = prevalence_curves(m["dynamics_list"])
        m["_prev_mean"], m["_prev_std"] = stats(prev)
        ni_data = m["frac"] if infect_mode == "fraction" else m["counts"]
        m["_ni_mean"], m["_ni_std"] = stats(ni_data)

    time = np.arange(len(methods[0]["_ni_mean"]))
    ni_label = "Newly Infected Fraction" if infect_mode == "fraction" else "Newly Infected Count"

    fig, ax_prev = plt.subplots(figsize=FIGURE_SIZE_LINE)
    ax_ni = ax_prev.twinx()

    # Left axis: prevalence (solid)
    for m in methods:
        ax_prev.plot(time, m["_prev_mean"], label=f"{m['label']} – Prevalence",
                     color=m["color"], linestyle="-", linewidth=2.5)
        ax_prev.fill_between(time, m["_prev_mean"] - m["_prev_std"],
                             m["_prev_mean"] + m["_prev_std"], color=m["color"], alpha=0.15)

    # Right axis: new infections (dashed)
    for m in methods:
        ax_ni.plot(time, m["_ni_mean"], label=f"{m['label']} – {ni_label}",
                   color=m["color"], linestyle="--", linewidth=1.5, alpha=0.7)
        ax_ni.fill_between(time, m["_ni_mean"] - m["_ni_std"],
                           m["_ni_mean"] + m["_ni_std"], color=m["color"], alpha=0.07)

    ax_prev.set_xlabel("Time Step")
    ax_prev.set_ylabel("Prevalence (Fraction Infected)")
    ax_ni.set_ylabel(ni_label, labelpad=10)
    ax_prev.set_title("Prevalence and Newly Infected by Method")

    handles_l, labels_l = ax_prev.get_legend_handles_labels()
    handles_r, labels_r = ax_ni.get_legend_handles_labels()
    ax_prev.legend(handles_l + handles_r, labels_l + labels_r, fontsize=8, ncols=2)

    ax_prev.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig("capstone_result_figures/prevalence_and_new_infections.pdf", format="pdf")
    plt.show()

if __name__ == "__main__":
    initialize()

    # Run hill2 (single-swap per batch, accept first improvement)
    _, hill_cost_curves, hill_edge_curves, hill_newly_counts, hill_newly_frac, hill_dynamics_list, tagged_contact_hill = hill2()

    # Run degree baseline
    _, degree_cost_curves, degree_edge_curves, degree_newly_counts, degree_newly_frac, degree_dynamics_list, tagged_contact_degree = degree_based_selection()

    # # Run no-quarantine baseline
    # nq_cost_curves, nq_edge_curves, nq_newly_counts, nq_newly_frac, nq_dynamics_list, _ = no_quarantine_baseline_runs()

    # Run random seed selection baseline
    _, rand_cost_curves, rand_edge_curves, rand_newly_counts, rand_newly_frac, rand_dynamics_list, tagged_contact_rand = random_seed_selection()

    # Cytoscape visualization (uses tagged network from first solver)
    send_to_cytoscape(tagged_contact_hill, title="Contact Network (Hill Climb)")

    # Beta distribution histogram
    plot_beta_histogram(tagged_contact_hill)

    # Assemble methods — comment out any entry to exclude it from the plots
    comparison_methods = [
        {
            "label": "Hill Climb", "color": "C0",
            "cost_curves": hill_cost_curves, "edge_curves": hill_edge_curves,
            "counts": hill_newly_counts, "frac": hill_newly_frac,
            "dynamics_list": hill_dynamics_list,
        },
        {
            "label": "Degree-Based", "color": "C1",
            "cost_curves": degree_cost_curves, "edge_curves": degree_edge_curves,
            "counts": degree_newly_counts, "frac": degree_newly_frac,
            "dynamics_list": degree_dynamics_list,
        },
        # {
        #     "label": "No Quarantine", "color": "C2",
        #     "cost_curves": nq_cost_curves, "edge_curves": nq_edge_curves,
        #     "counts": nq_newly_counts, "frac": nq_newly_frac,
        #     "dynamics_list": nq_dynamics_list,
        # },
        {
            "label": "Random Seeds", "color": "C3",
            "cost_curves": rand_cost_curves, "edge_curves": rand_edge_curves,
            "counts": rand_newly_counts, "frac": rand_newly_frac,
            "dynamics_list": rand_dynamics_list,
        },
    ]

    plot_full_comparison(comparison_methods, edge_mode="fraction", infect_mode="fraction")
    plot_prevalence_and_new_infections(comparison_methods, infect_mode="fraction")
