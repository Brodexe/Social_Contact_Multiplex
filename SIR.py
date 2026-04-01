import networkx as nx
import numpy as np
import random
import math
import matplotlib.pyplot as plt
import find_seeds
import correlated_graphs
import IM
from copy import deepcopy

# NOTE: undirected dynamics; node-wise
def sirs_step(G, state, L, beta, gamma, mu):
    new_state = state.copy()

    for u in G.nodes:
        if state[u] == 1:
            for v in G.neighbors(u):
                if isinstance(beta, float):
                    beta_val = beta
                else:
                    beta_val = beta[u]
                if state[v] == 0 and L[u] == 0:
                    if random.random() < beta_val:
                        new_state[v] = 1

    for u in G.nodes:
        if state[u] == 1:
            if random.random() < gamma:
                new_state[u] = 2

    for u in G.nodes:
        if state[u] == 2:
            if random.random() < mu:
                new_state[u] = 0

    return new_state

def transition(L, P_prime):
    all_0s = [i for i in range(len(L)) if L[i] == 0]
    all_1s = [i for i in range(len(L)) if L[i] == 1]

    t0 = np.random.choice(all_0s, size=P_prime)
    t1 = np.random.choice(all_1s, size=P_prime)

    if P_prime > 0:
        for i in t0:
            L[i] = 1
    elif P_prime < 0:
        for i in t1:
            L[i] = 0

    return L

def update_N_P(P, N, n, a=0.5, v=0.05):
    X = (P - N) / n
    X_prime = (1 - X) * v * np.exp(a * X) - (1 + X) * v * np.exp(-a * X)  # Compute X'

    P_prime = math.ceil((n * X_prime) / 2.0)

    P = P + P_prime
    N = N - P_prime

    return P_prime, P, N

# g: A graph, (mean, std): Parameters assoc. with taking P(edge removal) as a normal dist. sample, 
#   w/ threshold as another param.
def quarantine_edge_removal(g, node, states, quarantine_statuses, already_quarantining):
    # Boolean value; Checks if "Informed" is an attribute of the node under consideration
    is_informed = g.nodes[node].get('Informed?') == 'Informed'
    is_adhering = g.nodes[node].get('Adheres?') == 'Yes'

    # Check if node's state is 1 (active)
    if states[node] == 1 and is_informed == True and is_adhering == True:
        quarantine_statuses[node] = 1  # Set quarantine status to 1 (quarantining)
        # Get all neighbors of current node
        neighbors = list(g.neighbors(node))
        # print("Number of neighbors to remove for node ", node, ": ", len(neighbors))
        # Remove edges to all neighbors
        for neighbor in neighbors:
            g.remove_edge(node, neighbor)

        already_quarantining.append(node)
    
    return quarantine_statuses
        
def restore_edges(g_init, g, node, already_quarantining):
    initial_connections = [(node, neighbor) for neighbor in g_init.neighbors(node)]
    # Don't add back edges to neighbors that are still in quarantine
    quarantining_neighbors = [(node, neighbor) for neighbor in g_init.neighbors(node) if neighbor in already_quarantining]
    # Find the difference between the two sets
    set_diff = set(initial_connections) - set(quarantining_neighbors)

    g.add_edges_from(set_diff)

    if node in already_quarantining:
        already_quarantining.remove(node)

    return g


# q: Set to True if you want quarantine with fixed/variable periods and edge restoration after quarantine ends
#    Set to False to disable quarantine entirely
#    Set to "r" if you want quarantine (edges removed on infection) but restore edges immediately upon recovery (no fixed period)
# lt_threshold: Set to none for independent cascade model, or an int value for linear threshold model
# adherence: Set to a float value between 0 and 1. Ratio of individuals that will adhere to quarantine measures.
#            Can also be a list of nodes that adhere to quarantine
# seeds: a list of seed nodes for information spread. If None, seeds are chosen randomly.
# initial_state_dict: Optional dictionary mapping node -> state (0=S, 1=I, 2=R). If provided, uses this instead of random initial infections.
# p: diffusion probability for indepedent cascade model (only used if lt_threshold is None). Can be a scalar or weighted adjacency matrix.
def Simulate_SIR(contact_network, social_network, T, beta, gamma, mu, init,
                 q=False, lt_threshold=None, adherence=None, begin_q=0, seeds=None, initial_state_dict=None, p=0.02):

    if begin_q is None:
        begin_q = 0

    if social_network is None:
        social_network = correlated_graphs.create_social_graph(contact_network)[0]

    # 2 modes: T==0 => no information spread
    #          T==1 => information spread for 1 step
    # Both involve 1 step
    T_param = T
    if T_param == 0:
        T_param = 0
        # T must be >= 1
        T = 1

    n = len(contact_network.nodes())
    N = n - 1
    P = n - N

    adhering = set()  # Set to hold nodes that do not adhere to quarantine measures
    # Randomly select a subset of nodes that will not adhere to quarantine measures
    if isinstance(adherence, float) and 0 <= adherence <= 1:
        adhering = set(np.random.choice(contact_network.nodes(), size=int((adherence) * n), replace=False))
    # Keep adhering individuals from parameters if provided as a list
    elif isinstance(adherence, set):
        adhering = adherence

    non_adhering = set(contact_network.nodes()) - adhering

    # Set labels for non-adhering nodes
    for node in non_adhering:
        nx.set_node_attributes(contact_network, {node: {'Adheres?': 'No'}})
        nx.set_node_attributes(social_network, {node: {'Adheres?': 'No'}})

    # Set labels for adhering nodes
    for node in adhering:
        nx.set_node_attributes(contact_network, {node: {'Adheres?': 'Yes'}})
        nx.set_node_attributes(social_network, {node: {'Adheres?': 'Yes'}})

    # We are saving the initial state of G so we know what connections to restore later
    G_initial = deepcopy(contact_network)

    # Initial state dictionary (0: susceptible, 1: infected, 2: recovered)
    # Handle user-provided initial_state_dict
    if initial_state_dict is not None:
        state = initial_state_dict.copy()  # Use provided dictionary directly
    elif isinstance(init, (list, set)):
        # Treat init as a collection of initially infected nodes
        infected_nodes = set(init)
        state = {u: 1 if u in infected_nodes else 0 for u in range(n)}
    else:
        # Fall back to original random initialization using 'init' probability
        state = {u: np.random.choice(a=[1, 0], size=1, p=[init, 1 - init])[0]
                    for u in range(n)}  # Note: Initial setup only uses 0 and 1

    state_changes = []
    # Record initial states at T=0
    for u in range(n):
        state_changes.append((u, state[u], 0))

    # L[i] == 0: Can't infect. L[i] == 1: Can infect
    L = [0 for _ in range(N)] + [1 for _ in range(P)]
    PList = [P]
    Inf = [len([u for u in state.keys() if state[u] == 1])]

    # If an int is passed as q, we assume it is the quarantine period for all individuals
    if isinstance(q, int) and q > 1:  # > 1 excludes the boolean cases
        d = [q for _ in range(n)]
        q = True  # Force to True so restoration happens after fixed period

    elif q == "r":
        # If q is "r", we will restore edges immediately after recovery; 
        # no fixed quarantine period needed
        d = None  # Not used in "r" mode
    # By default (q=True), quarantine period ~ Normal, restore after period ends
    elif q is True:
        # d[i]: # of days individual i chooses to quarantine
        samples_array = np.random.normal(loc=14, scale=2, size=n)
        # Take abs. value of the quarantine period samples, and round to nearest int. val.
        d = [abs(round(x)) for x in samples_array]
    else:
        # q is False - no quarantine at all
        d = None

    # Holds dynamic quarantine lengths (only used when q is True or int)
    quarantine_statuses = [0 for _ in range(n)]
    quarantine_prob_matrix = np.zeros((T, n))  # T x n matrix: hold probabilities of quarantine for each node at each time step
    #  Initialize every node to 'Uninformed'
    for node in contact_network.nodes():
        nx.set_node_attributes(contact_network, {node: {'Informed?': 'Uninformed'}})
    for node in social_network.nodes():
        nx.set_node_attributes(social_network, {node: {'Informed?': 'Uninformed'}})

    quarantine_series = []   # Hold list of quarantining individuals at each time step
    state_series = []        # Hold state of all nodes at each time step
    informed_series = []     # Hold list of informed at each time step
    all_edges = []           # Hold list of contact network edges at each time step (after removals)

    dynamic_degree = []

    # Save informed and infected count over time
    # Used when determining expected # of edges removed (extract_mfa.py)
    informed_infected_series = []
    
    # Keep track of who is already quarantining (so we don't restore their edges prematurely)
    already_quarantining = []

    # NOTE
    avg_avg_just = []

    # Use a set for the informed population from the very beginning to avoid duplicates
    informed = set()
    previous_informed = set()

    for t in range(T):

        #-------------
        #
        #  Make social network changes
        #
        #-------------

        # People are unaware of disease spread/quarantining measures
        if t < begin_q:
            pass  # informed remains empty set

        #  People become aware of need to quarantine at time t==begin_q
        elif t == begin_q:
            initial_informed_lst = []
            # Get the initial set of informed nodes
            if isinstance(seeds, set) or isinstance(seeds, list):
                initial_informed_lst = seeds
            elif isinstance(seeds, int) and seeds > 0:
                num_seeds = seeds
                initial_informed_lst = find_seeds.find_seed_set(social_network, num_seeds=num_seeds, exponent=2)
            # Handle cases where no seeds are provided
            elif seeds is None or seeds == [] or seeds == 0:
                initial_informed_lst = []

            # Convert to set if not already a set
            informed = set(initial_informed_lst)

            # NOTE: Non-adhering can still be informed

            # Set labels for informed set
            for node in informed:
                nx.set_node_attributes(contact_network, {node: {'Informed?': 'Informed'}})
                nx.set_node_attributes(social_network, {node: {'Informed?': 'Informed'}})

        #  Influence spreads
        elif (t > begin_q) or (T_param == 1):
            # Can only spread if there are some seed nodes
            if initial_informed_lst != []:
                if lt_threshold == None:  # If we are using I.C., that is
                    ic_results = IM.IC_prob_matrix(social_network, S=list(informed), p=p, mc=1000, quarantining=quarantine_statuses)
                    prob_matrix = ic_results[0]
                    new_informed_list = ic_results[1]
                else:
                    lt_results = IM.lt_prob_matrix(social_network, threshold=lt_threshold, S=list(informed), quarantining=quarantine_statuses)
                    prob_matrix = lt_results[0]
                    new_informed_list = lt_results[1]

                # NOTE: Generate new case for p as a matrix of activation probabilities
                if isinstance(p, float):
                    quarantine_prob_matrix[t] = prob_matrix

                assert len(informed) > 0, "Informed set is empty!"

                # Convert new activations to set to remove internal duplicates
                new_informed_list = set(new_informed_list)

                # Update the master informed set with proper union
                informed = informed.union(new_informed_list)

                # Only mark newly informed nodes
                for node in new_informed_list:
                    nx.set_node_attributes(contact_network, {node: {'Informed?': 'Informed'}})
                    nx.set_node_attributes(social_network, {node: {'Informed?': 'Informed'}})

        new_informed = informed - previous_informed
        previous_informed = informed.copy()

        #-------------
        #
        #  Make contact network changes
        #
        #-------------

        # Dynamic updates
        P_prime, P, N = update_N_P(P, N, n)
        L = transition(L, P_prime)

        # Snapshot state before any changes this timestep
        copy_state = deepcopy(state)

        # Trigger nodes: currently infected nodes, plus newly informed nodes that are infected.
        # These are computed from the PRE-step state so that quarantine decisions are made
        # on the basis of known infection status, before disease can spread further.
        currently_infected = set([u for u in range(n) if state[u] == 1])
        trigger_nodes = currently_infected | set([u for u in new_informed if state[u] == 1])

        # 1. Cut valid ties first (quarantine on the pre-step graph)
        if q is not False:
            for u in trigger_nodes:
                quarantine_statuses = quarantine_edge_removal(contact_network, u, state, quarantine_statuses, already_quarantining)

        # 2. Then run SIRS dynamics on the pruned contact network
        state = sirs_step(contact_network, state, L, beta, gamma, mu)

        # List of nodes that would quarantine ideally
        i_prime_current = []
        infm_current = []

        # Analyze state changes across all nodes
        for u in range(n):
            # Boolean value; Checks if "Informed" is an attribute of the node under consideration
            is_informed = contact_network.nodes[u].get('Informed?') == 'Informed'

            # Record who is currently informed
            if is_informed == True:
                    infm_current.append(u)

                    # Record who is currently infected and informed
                    if state[u] == 1:
                        i_prime_current.append(u)

            # At t==0, the state transition logic will not suffice. So check if anyone needs to be quarantined
            # Determine what quarantines need to be made
            if copy_state[u] != state[u] or t == 0:
                # Record in state changes the time at which said change occurred
                state_changes[u] = (u, state[u], t)

            # Handle restoration and quarantine duration tracking only when q is True (fixed/variable period)
            if q is True:
                if is_informed and (1 <= quarantine_statuses[u] <= d[u]):
                    quarantine_statuses[u] += 1
                    # If the quarantine time has been reached, end quarantine and restore edges
                    if quarantine_statuses[u] >= d[u]:
                        quarantine_statuses[u] = 0   # Reset quarantine counter
                        restore_edges(G_initial, contact_network, u, already_quarantining=already_quarantining)

            # Immediate restoration on recovery when q == "r"
            if q == "r" and state[u] == 2 and copy_state[u] != 2:  # Just recovered this step
                quarantine_statuses[u] = 0
                restore_edges(G_initial, contact_network, u, already_quarantining=already_quarantining)

        informed_infected_series.append(i_prime_current)
        informed_series.append(infm_current)

        quarantine_series.append(quarantine_statuses.copy())
        state_series.append(state.copy())

        live_edges = contact_network.edges()
        all_edges.append(live_edges)

        # quick diagnostics
        m_init = G_initial.number_of_edges()
        m_now = contact_network.number_of_edges()
        actual_removed_cumulative = m_init - m_now

        # who is currently quarantining (status>0)
        current_quarantining = [i for i, qv in enumerate(quarantine_statuses) if qv > 0]
        num_current_q = len(current_quarantining)

        # nodes that *just* started quarantining this timestep:
        # those in trigger_nodes that are informed and adhering
        just_started = set()
        for u in trigger_nodes:
            if contact_network.nodes[u].get('Informed?') == 'Informed' and contact_network.nodes[u].get('Adheres?') == 'Yes':
                just_started.add(u)

        # avg degree in initial graph of those who just started
        if len(just_started) > 0:
            avg_deg_just = np.mean([G_initial.degree(u) for u in just_started])
        else:
            avg_deg_just = None

        avg_avg_just.append(avg_deg_just)

        # print(f"t={t} edges_init={m_init} edges_now={m_now} removed_cumulative={actual_removed_cumulative} #cur_q={num_current_q} #just_start={len(just_started)} avg_deg_just={avg_deg_just}")

        # Update infection count for plotting
        Inf.append(len([u for u in state.keys() if state[u] == 1]))
        PList.append(P)

        # Assign attributes to each node
        for i, _, _ in state_changes:
            contact_network.nodes[i]['Infection Status'] = state_changes[i][1]
            contact_network.nodes[i]['Timestamp'] = state_changes[i][2]

        dynamic_degree.append(np.mean([degree for _, degree in contact_network.degree()]))

    infection_data = []
    # Store initial infection data
    x_data = [t for t in range(T + 1)]  # Time points
    y_data_inf = Inf  # Infection frequency
    infection_data.append(x_data)
    infection_data.append(y_data_inf)
    
    # See how far off avg. actually removed is from expected (k_0)
    # print("Average of avg. degrees of just-started quarantining nodes, over all time steps: ", np.mean([x for x in avg_avg_just if x is not None]))

    return contact_network, state_changes, infection_data, quarantine_prob_matrix, state_series, social_network, dynamic_degree, informed_infected_series, informed_series, adhering, all_edges
