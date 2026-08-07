import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import SIR
import random
import correlated_graphs
import cost_curve_store
import network_setup
import pickle
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

ping_cytoscape = False

# Simulation parameters (network-independent)
T = 100
HETEROGENEOUS_BETA = True  # True: node-wise beta drawn from power-law distribution; False: scalar beta for all nodes
beta = 0.15  # Used directly when HETEROGENEOUS_BETA=False; ignored when True
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05

beta_L = 0.05   # Lower bound for heterogeneous beta
beta_R = 0.25   # Upper bound for heterogeneous beta
Gamma  = 2      # Shape parameter: higher values skew beta toward beta_R

adherence = 1.0
num_simulations = 10

batch_interval = 2  # Seeds and cost updated once every batch_interval steps
information_spread = True

q = "r"
# Try introducing random infections in intervals to better differentiate methods
introduced_infections = (0, 1) # (fraction of population, time step to introduce)

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
    return {node: (1 if random.random() < init else 0) for node in nodes}


# Delegates to network_setup.laplacian_smooth_beta so custom-network runs (e.g.
# drive_seed_selection.py's per-bin GML networks) use the same beta-generation
# logic as the shared synthetic network built by network_setup.py.
def compute_node_beta(_state_dict, graph):
    if not HETEROGENEOUS_BETA:
        return beta

    return network_setup.laplacian_smooth_beta(graph, beta_L, beta_R, lam=Gamma)


def compute_beta_clustering(beta_map, graph=None):
    """Print Moran's I and avg neighbor beta difference to check spatial structure."""
    if graph is None:
        graph = initial_contact
    if not isinstance(beta_map, dict):
        print("Beta clustering: scalar beta (no heterogeneity), skipping.")
        return

    nodes = list(graph.nodes())
    betas = np.array([beta_map[node] for node in nodes])
    z = betas - betas.mean()
    node_idx = {node: i for i, node in enumerate(nodes)}
    edges = list(graph.edges())

    cross_sum = sum(z[node_idx[u]] * z[node_idx[v]] for u, v in edges)
    W = 2 * len(edges)
    variance_sum = float(np.sum(z ** 2))
    morans_i = (len(nodes) / W) * (2 * cross_sum / variance_sum) if W > 0 and variance_sum > 0 else 0.0

    avg_neighbor_diff = np.mean([abs(betas[node_idx[u]] - betas[node_idx[v]]) for u, v in edges]) if edges else 0.0

    print(f"[Betas]  Moran's I = {morans_i:.4f}")
    print(f"[Betas]  Avg |beta_u - beta_v| over edges = {avg_neighbor_diff:.4f}"
          f"  (std = {betas.std():.4f}, range = [{betas.min():.3f}, {betas.max():.3f}])")


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

# network: None to use the synthetic network shared with milp.py (see
#   network_setup.py) -- both approaches then compare against an identical
#   contact network, social network, and set of per-simulation heterogeneous
#   beta maps. Pass an nx.Graph or a string path to a GML file to run against
#   a specific network instead (e.g. drive_seed_selection.py's per-bin runs);
#   in that case the beta maps are generated locally for that network only,
#   independent of the shared cache.
# social: None to synthesize a social network from the contact network via
#   correlated_graphs.create_social_graph (used whenever `network` is also a
#   custom graph/path). Pass an nx.Graph or a string path to a GML file to use
#   a real social network instead -- e.g. rc_social_network.gml. GML node
#   identity comes from the "label" field (nx.read_gml's default), which for
#   the rc_* dataset is the real participant ID and lines up across the
#   contact/social pair, so nodes are intersected on that label and remapped
#   to a shared set of integer ids before use. Ignored when `network` is None.
def initialize(network=None, social=None):
    """Load a contact network and run baseline simulations.  Must be called
    once before any simulation function (hill2, degree_based_selection, etc.)."""
    global contact_network, initial_contact, initial_edge_count, n
    global social_network, initial_social, K
    global injection_times, _num_to_infect, infection_candidates, baseline_runs
    global global_betas

    if network is None:
        shared = network_setup.load_shared_network(min_simulations=num_simulations)
        contact_network = deepcopy(shared["contact_network"])
        social_network  = deepcopy(shared["social_network"])
        global_betas    = shared["global_betas"][:num_simulations]
    else:
        contact_network = nx.read_gml(network) if isinstance(network, str) else network
        isolated_nodes = [node for node in contact_network.nodes()
                          if contact_network.degree(node) == 0]
        contact_network.remove_nodes_from(isolated_nodes)

        if social is None:
            contact_network = nx.convert_node_labels_to_integers(contact_network, first_label=0)

            # Social network needs real edge structure: information diffusion (IC/LT/FJ) in
            # SIR.Simulate_SIR spreads over social_network's edges, so an edgeless graph means
            # the informed set can never grow past the initial seeds.
            social_network, _ = correlated_graphs.create_social_graph(
                contact_network, 2 * contact_network.number_of_edges())
        else:
            social_network = nx.read_gml(social) if isinstance(social, str) else social

            # Contact and social GML files aren't guaranteed to cover identical node
            # sets, so intersect them on label first, then remap that shared set onto
            # integers 0..n-1 with ONE mapping applied to both graphs -- code elsewhere
            # (e.g. hill2's seed_vec) indexes nodes as plain array positions, so contact
            # and social node ids must agree exactly.
            common_nodes = [node for node in contact_network.nodes() if social_network.has_node(node)]
            contact_network = contact_network.subgraph(common_nodes).copy()
            social_network  = social_network.subgraph(common_nodes).copy()
            mapping = {node: i for i, node in enumerate(contact_network.nodes())}
            contact_network = nx.relabel_nodes(contact_network, mapping)
            social_network  = nx.relabel_nodes(social_network, mapping)

        global_betas = [compute_node_beta(None, contact_network) for _ in range(num_simulations)]

    initial_contact    = deepcopy(contact_network)
    initial_edge_count = contact_network.number_of_edges()
    n                  = len(contact_network.nodes())
    initial_social     = deepcopy(social_network)

    K = int((3/4) * n)  # Number of seeds to select at each batch

    for beta_map in global_betas:
        compute_beta_clustering(beta_map, initial_contact)

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

    # Collect per-timestep newly infected counts from baseline (no-quarantine) runs
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
    edge_cost_bound = sum(edge_cost_dict.values())  # cost of losing every edge in one step

    # Only accumulate cost since the most recent batch selection. When seeds are
    # reselected every single step (batch_interval == 1) there is no distinct batch
    # to window against, so fall back to summing over the entire history instead.
    if batch_interval == 1:
        window_start = 0
    else:
        window_start = (t_cur // batch_interval) * batch_interval
    window_len = t_cur - window_start + 1

    total_edge_removal_cost = 0
    # Compute sum of removed edges at each time step since the last batch selection
    for t in range(window_start, t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    newly_infected_sum = np.sum(newly_infected[window_start:t_cur + 1])

    # Adjust penalty weights so that each term contributes equally to cost function.
    # g: no-quarantine counterfactual bound (see baseline_infections) -- more
    # quarantine can only ever reduce infections, so this is a true upper bound.
    # h: static worst case instead -- N steps into the batch, the most edge cost
    # you could possibly have incurred is N * (sum of every edge's removal cost),
    # i.e. every edge in the graph gone at every step. A full-quarantine simulated
    # "counterfactual" bound doesn't actually bound this: aggressive quarantine
    # suppresses spread so effectively that it can rack up LESS cumulative edge
    # cost than a realistic, imperfect policy that lets the epidemic reach more
    # nodes over the window -- letting the real numerator exceed that "bound".
    g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, t_cur + 1))
    h = window_len * edge_cost_bound

    alpha_w = 1 / g if g > 0 else 1.0
    beta_w = 1 / h if h > 0 else 1.0
    gamma_w = 1 / (n)

    # cost_elements carries alpha_w/beta_w alongside the raw sums so downstream
    # plotting (cost_curve_store.plot_joint_cost_elements) can show each term
    # weighted the same way it contributes to the returned cost, rather than as
    # raw, differently-scaled counts.
    cost_elements = (newly_infected_sum, total_edge_removal_cost, seed_set_size, alpha_w, beta_w)

    # Print cost components
    # print(f"Cost components at time {t_cur}:")
    # print(f"  Newly infected sum: {np.sum(newly_infected)}")
    # print(f"  Total edge removal cost: {total_edge_removal_cost}")
    # print(f"  Seed set size: {seed_set_size}")
    # print(f" alpha_w: {alpha_w:.4f}, beta_w: {beta_w:.4f}, gamma_w: {gamma_w:.4f}")

    # return beta_w * total_edge_removal_cost, cost_elements
    # return alpha_w * np.sum(newly_infected) + beta_w * total_edge_removal_cost + gamma_w * seed_set_size, cost_elements
    # Cap each term at 1 so the maximum possible total cost per step is 2.
    infection_term = min(alpha_w * newly_infected_sum, 1.0)
    edge_term = min(beta_w * total_edge_removal_cost, 1.0)
    return infection_term + edge_term, cost_elements
    # return alpha_w * newly_infected_sum, cost_elements

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
    all_infection_term_curves = []
    all_edge_term_curves = []
    all_alpha_w_curves = []
    all_beta_w_curves = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_state_vectors = []
    all_batch_seed_sets = []  # per-simulation list of per-batch seed sets (list of node ids)

    # t_batch=0: no information spread at all (seeds are quarantined if infected, but info
    #   never reaches non-seed nodes) -- one T=1 call every tick.
    # t_batch=batch_interval: one call per batch, run only at batch boundaries, letting info
    #   spread across the whole batch_interval window before the next seed refinement.
    t_batch = 0
    if information_spread:
        t_batch = batch_interval

    for i in range(num_simulations):
        print("Hill-Climb Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0
                             for node in contact_network.nodes()])
        new_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        cost_lst = []
        infection_term_lst = []
        edge_term_lst = []
        alpha_w_lst = []
        beta_w_lst = []
        states_at_time = None
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]

        live_edge_at_time = None
        edge_counts = []
        last_batch_cost = None
        newly_infected_at_time = []
        newly_infected_frac_per_sim = []
        batch_seed_sets = []  # this simulation's seed set at each batch

        for t_cur in range(T):
            # Record the seed set that will be used for this batch
            if t_cur % batch_interval == 0:
                batch_seed_sets.append(list(new_seed_set))

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

            # With information diffusion enabled, only re-simulate at batch boundaries -- one
            # call covers the whole batch_interval window, letting info actually reach non-seed
            # nodes. Without it, advance one real step every tick.
            call_now = (t_cur % batch_interval == 0) if information_spread else True
            if call_now:
                simulation_results = SIR.Simulate_SIR(
                    contact_network=contact_network, social_network=social_network,
                    T=t_batch,
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

                graph_vec = simulation_results[10]
                live_edges = [list(edge_set) for edge_set in graph_vec]
                live_edge_at_time = live_edges if live_edge_at_time is None else live_edge_at_time + live_edges

            current_new_i = given_at_time(t_cur, states_at_time, contact_network)
            newly_infected_at_time.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)
            edge_counts.append(len(live_edge_at_time[t_cur]))

            # Perform swapping operation only at batch boundaries
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, cost_elements = global_cost_function(newly_infected_at_time, live_edge_at_time, len(new_seed_set), t_cur)
                print(f"Hill-Climb, {t_cur}, {cost}")
                cost_lst.append(cost)
                infection_term_lst.append(cost_elements[0])
                edge_term_lst.append(cost_elements[1])
                alpha_w_lst.append(cost_elements[3])
                beta_w_lst.append(cost_elements[4])
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
        all_infection_term_curves.append(infection_term_lst)
        all_edge_term_curves.append(edge_term_lst)
        all_alpha_w_curves.append(alpha_w_lst)
        all_beta_w_curves.append(beta_w_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_at_time)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_state_vectors.append(states_at_time)
        all_batch_seed_sets.append(batch_seed_sets)

    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    tagged = build_tagged_network(global_betas[0])
    return (most_common_seed_set, all_cost_curves, all_infection_term_curves, all_edge_term_curves,
            all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_state_vectors,
            tagged, all_batch_seed_sets, all_alpha_w_curves, all_beta_w_curves)

# Degree based selection: at each time step, select top K nodes by degree in the CURRENT contact network as seeds
# Allows re-selection
def degree_based_selection():
    all_cost_curves = []
    all_infection_term_curves = []
    all_edge_term_curves = []
    all_alpha_w_curves = []
    all_beta_w_curves = []
    winner_sets = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    # t_batch=0: no information spread at all (seeds are quarantined if infected, but info
    #   never reaches non-seed nodes) -- one T=1 call every tick.
    # t_batch=batch_interval: one call per batch, run only at batch boundaries, letting info
    #   spread across the whole batch_interval window before the next seed refinement.
    t_batch = 0
    if information_spread:
        t_batch = batch_interval

    for i in range(num_simulations):
        print("Degree-based Simulation:", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        cost_lst = []
        infection_term_lst = []
        edge_term_lst = []
        alpha_w_lst = []
        beta_w_lst = []
        full_dynamics = None
        prev_state_dict = make_initial_state(contact_network)
        static_beta = global_betas[i]
        full_live_edges = None
        edge_counts = []
        seed_set = None
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # At batch boundary: select new seeds from the most recently known graph
            if t_cur % batch_interval == 0:
                current_graph = nx.Graph()
                current_graph.add_nodes_from(contact_network.nodes())
                if full_live_edges:
                    live_edge_set = set(tuple(sorted(e)) for e in full_live_edges[-1])
                    for u, v, data in initial_contact.edges(data=True):
                        if tuple(sorted((u, v))) in live_edge_set:
                            current_graph.add_edge(u, v, **data)
                else:
                    current_graph.add_edges_from(initial_contact.edges(data=True))

                degree_dict = dict(current_graph.degree())
                seed_set = sorted(degree_dict, key=lambda node: degree_dict[node], reverse=True)[:K]

            # Introduce random new infections
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                new_infections = infection_candidates[i][injection_times.index(t_cur)]
                for node in new_infections:
                    if prev_state_dict[node] == 2:  # Only infect if node is currently susceptible
                        prev_state_dict[node] = 1

            # With information diffusion enabled, only re-simulate at batch boundaries -- one
            # call covers the whole batch_interval window. Without it, advance one real step
            # every tick.
            call_now = (t_cur % batch_interval == 0) if information_spread else True
            if call_now:
                simulation_results = SIR.Simulate_SIR(
                    contact_network=contact_network,
                    social_network=social_network,
                    T=t_batch,
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

                graph_vec = simulation_results[10]
                live_edges = [list(network) for network in graph_vec]
                full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)
            edge_counts.append(len(full_live_edges[t_cur]))

            # At batch boundary: compute cost
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, cost_elements = global_cost_function(
                    newly_infected_per_sim,
                    full_live_edges,
                    len(seed_set),
                    t_cur
                )
                print(f"Degree-based, {t_cur}, {cost}")
                cost_lst.append(cost)
                infection_term_lst.append(cost_elements[0])
                edge_term_lst.append(cost_elements[1])
                alpha_w_lst.append(cost_elements[3])
                beta_w_lst.append(cost_elements[4])

        winner_sets.append(seed_set)
        all_cost_curves.append(cost_lst)
        all_infection_term_curves.append(infection_term_lst)
        all_edge_term_curves.append(edge_term_lst)
        all_alpha_w_curves.append(alpha_w_lst)
        all_beta_w_curves.append(beta_w_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    tagged = build_tagged_network(global_betas[0])
    return (winner_sets[0], all_cost_curves, all_infection_term_curves, all_edge_term_curves,
            all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics, tagged,
            all_alpha_w_curves, all_beta_w_curves)

def random_seed_selection():
    all_cost_curves = []
    all_infection_term_curves = []
    all_edge_term_curves = []
    all_alpha_w_curves = []
    all_beta_w_curves = []
    winner_sets = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_full_dynamics = []

    # t_batch=0: no information spread at all (seeds are quarantined if infected, but info
    #   never reaches non-seed nodes) -- one T=1 call every tick.
    # t_batch=batch_interval: one call per batch, run only at batch boundaries, letting info
    #   spread across the whole batch_interval window before the next seed refinement.
    t_batch = 0
    if information_spread:
        t_batch = batch_interval

    for i in range(num_simulations):
        print("Random Seed Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        cost_lst = []
        infection_term_lst = []
        edge_term_lst = []
        alpha_w_lst = []
        beta_w_lst = []
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

            # With information diffusion enabled, only re-simulate at batch boundaries -- one
            # call covers the whole batch_interval window. Without it, advance one real step
            # every tick.
            call_now = (t_cur % batch_interval == 0) if information_spread else True
            if call_now:
                simulation_results = SIR.Simulate_SIR(
                    contact_network=contact_network,
                    social_network=social_network,
                    T=t_batch,
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

                graph_vec = simulation_results[10]
                live_edges = [list(network) for network in graph_vec]
                full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)
            edge_counts.append(len(full_live_edges[t_cur]))

            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, cost_elements = global_cost_function(
                    newly_infected_per_sim,
                    full_live_edges,
                    len(seed_set),
                    t_cur
                )
                print(f"Random Seed, {t_cur}, {cost}")
                cost_lst.append(cost)
                infection_term_lst.append(cost_elements[0])
                edge_term_lst.append(cost_elements[1])
                alpha_w_lst.append(cost_elements[3])
                beta_w_lst.append(cost_elements[4])

        winner_sets.append(seed_set)
        all_cost_curves.append(cost_lst)
        all_infection_term_curves.append(infection_term_lst)
        all_edge_term_curves.append(edge_term_lst)
        all_alpha_w_curves.append(alpha_w_lst)
        all_beta_w_curves.append(beta_w_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    tagged = build_tagged_network(global_betas[0])
    return (winner_sets[0], all_cost_curves, all_infection_term_curves, all_edge_term_curves,
            all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics, tagged,
            all_alpha_w_curves, all_beta_w_curves)


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
                if batch_interval == 1:
                    window_start = 0
                else:
                    window_start = (t_cur // batch_interval) * batch_interval
                g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, t_cur + 1))
                alpha_w = 1 / g if g > 0 else 1.0
                cost = alpha_w * np.sum(newly_infected_per_sim[window_start:t_cur + 1])
                print(f"No-Quarantine, {t_cur}, {cost}")
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
    # ── CHOOSE NETWORK FILES HERE ───────────────────────────────────────────
    # Swap these two paths to run against a different contact/social pair (or set
    # both to None to fall back to the synthetic network shared with milp.py).
    # CONTACT_NETWORK_PATH = "capstone_proj_data/rc_weighted_contact_bin14.gml"
    # SOCIAL_NETWORK_PATH  = "capstone_proj_data/rc_social_network.gml"

    CONTACT_NETWORK_PATH = None
    SOCIAL_NETWORK_PATH = None

    # ─────────────────────────────────────────────────────────────────────────

    initialize(CONTACT_NETWORK_PATH, SOCIAL_NETWORK_PATH)

    # Run hill2 (single-swap per batch, accept first improvement) -- the "adaptive" approach
    (_, hill_cost_curves, hill_infection_curves, hill_edge_term_curves, hill_edge_curves,
     hill_newly_counts, hill_newly_frac, hill_dynamics_list, tagged_contact_hill,
     hill_batch_seed_sets, hill_alpha_w_curves, hill_beta_w_curves) = hill2()

    # Save every seed set of every batch of every run of the adaptive approach, along with
    # the social network it was selected against, for visualize_adaptive.py.
    with open("adaptive_seed_data.pkl", "wb") as f:
        pickle.dump({
            "batch_seed_sets": hill_batch_seed_sets,  # [sim][batch] -> list of node ids
            "social_network": initial_social,
        }, f)

    # Run degree baseline
    (_, degree_cost_curves, degree_infection_curves, degree_edge_term_curves, degree_edge_curves,
     degree_newly_counts, degree_newly_frac, degree_dynamics_list, tagged_contact_degree,
     degree_alpha_w_curves, degree_beta_w_curves) = degree_based_selection()

    # Run random seed selection baseline
    (_, rand_cost_curves, rand_infection_curves, rand_edge_term_curves, rand_edge_curves,
     rand_newly_counts, rand_newly_frac, rand_dynamics_list, tagged_contact_rand,
     rand_alpha_w_curves, rand_beta_w_curves) = random_seed_selection()

    # Cytoscape visualization (uses tagged network from first solver)
    send_to_cytoscape(tagged_contact_hill, title="Contact Network (Hill Climb)")

    # Beta distribution histogram
    # plot_beta_histogram(tagged_contact_hill)

    # Push this run's cost curves -- plus raw infection/edge cost-element curves and the
    # alpha_w/beta_w that weight them into the returned cost -- into the store shared
    # with milp.py. Once milp.py has also been run, call
    # cost_curve_store.plot_joint_cost_comparison() / plot_joint_cost_elements() (e.g.
    # `python cost_curve_store.py`) to render the combined figures.
    cost_curve_store.push_curve("Degree-Based", degree_cost_curves,
                                 infection_curves=degree_infection_curves, edge_curves=degree_edge_term_curves,
                                 alpha_curves=degree_alpha_w_curves, beta_curves=degree_beta_w_curves,
                                 batch_interval=batch_interval, T=T)
    cost_curve_store.push_curve("Random Seeds", rand_cost_curves,
                                 infection_curves=rand_infection_curves, edge_curves=rand_edge_term_curves,
                                 alpha_curves=rand_alpha_w_curves, beta_curves=rand_beta_w_curves,
                                 batch_interval=batch_interval, T=T)
    cost_curve_store.push_curve("Adaptive", hill_cost_curves,
                                 infection_curves=hill_infection_curves, edge_curves=hill_edge_term_curves,
                                 alpha_curves=hill_alpha_w_curves, beta_curves=hill_beta_w_curves,
                                 batch_interval=batch_interval, T=T)
