import networkx as nx
import numpy as np
import random
import math
import matplotlib.pyplot as plt
import find_seeds
import correlated_graphs
import IM
from copy import deepcopy
import pickle as pkl


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


# ---------------------------------------------------------------------------------------
# Misinformation (optional; off unless Simulate_SIR is called with misinfo=True)
#
# A second cascade competes with information on the social network. Misinformers start
# as a seed set at begin_q just like informers, and every non-adherer is one of them:
# with misinformation on, non-adherence is no longer a fixed label but the misinformed
# state itself. The people the adherence draw leaves out are misinformation seeds;
# anyone misinformed later stops adhering (never quarantines, and one already
# quarantining breaks it off); anyone won back by information adheres again.
# Misinformation spreads by the same mechanism as information (IC / LT / FJ), with its
# own cascade value (misinfo_val: IC p, LT threshold, or FJ kappa; default the same).
#
# misinfo_mode:
#   "takeover" -- each side converts the other side's members it reaches (seeds of
#                 either kind never switch). LT only converts with a strict majority of
#                 active predecessors, so a node can't flip back and forth every tick.
#   "collide"  -- only uninformed people can be reached; whoever reaches them first
#                 keeps them and no one switches sides afterwards.
# Someone reached by both sides in the same tick goes to one of them at random (LT: to
# the side with more active predecessors, at random on a tie). A person in both seed
# sets is an information seed.
#
# FJ: misinformation has its own belief field xm, spread from its own seeds exactly as
# information's field x is from information seeds (each seed set pinned at 1), so x is
# the same field as without misinformation. Each tick a person not yet on a side is
# reached by information with probability x^kappa and by misinformation with
# probability xm^kappa_m (with takeover, a non-seed on the other side is too). Edge
# cutting uses x as before, but zero for misinformed people, since they don't quarantine.
# ---------------------------------------------------------------------------------------
MISINFO_MODES = ("takeover", "collide")


def misinfo_seed_set(social_network, misinfo_seeds, non_adhering, informed):
    """Initial misinformed set: the explicit misinformation seeds (a list/set, or a count
    drawn like find_seeds.find_seed_set, with probability proportional to degree^2, from
    people who aren't information seeds) plus every non-adherer, minus information seeds."""
    informed = set(informed)
    if isinstance(misinfo_seeds, (set, list)):
        chosen = set(misinfo_seeds)
    elif isinstance(misinfo_seeds, int) and misinfo_seeds > 0:
        degrees = dict(social_network.degree())
        nodes = [u for u in degrees if u not in informed]
        if misinfo_seeds > len(nodes):
            raise ValueError(f"Cannot choose {misinfo_seeds} misinformation seeds: only "
                             f"{len(nodes)} people aren't information seeds")
        probs = np.array([degrees[u] ** 2 + 1e-6 for u in nodes])
        chosen = set(np.random.choice(nodes, size=misinfo_seeds, replace=False, p=probs / probs.sum()))
    else:
        chosen = set()
    return (chosen | set(non_adhering)) - informed


def set_info_label(contact_network, social_network, node, label):
    """Label a node 'Informed', 'Misinformed' or 'Uninformed' in both layers. With
    misinformation on, adherence follows it: only the misinformed don't adhere."""
    adheres = 'No' if label == 'Misinformed' else 'Yes'
    for g in (contact_network, social_network):
        g.nodes[node]['Informed?'] = label
        g.nodes[node]['Adheres?'] = adheres


def break_quarantine(g_init, g, nodes, quarantine_statuses, already_quarantining):
    """Newly misinformed people stop quarantining: their contacts are restored (except to
    people still quarantining) and their quarantine status cleared."""
    for u in sorted(nodes):
        if quarantine_statuses[u] > 0 or u in already_quarantining:
            quarantine_statuses[u] = 0
            restore_edges(g_init, g, u, already_quarantining)
            while u in already_quarantining:
                already_quarantining.remove(u)


def fj_belief_update(social_network, x, stubborn):
    """One Friedkin-Johnsen step: x_i <- (s_i + sum_j x_j) / (1 + deg_i), s_i = 0 off the
    stubborn set, whose beliefs stay pinned at 1 (as Simulate_SIR's FJ update does)."""
    return {node: 1.0 if node in stubborn
            else sum(x[nb] for nb in social_network.neighbors(node)) / (1 + social_network.degree(node))
            for node in social_network.nodes()}


def competing_spread_step(social_network, mech_type, mech_val, misinfo_val, informed, misinformed,
                          info_seeds, misinfo_seeds, mode="takeover", fj_x=None, fj_xm=None, mc=1000):
    """One tick of information and misinformation spreading side by side on the social
    network (see the block comment above). Both sides spread from the start-of-tick sets.
    Returns (informed, misinformed, fj_x, fj_xm, info_prob_matrix) as new objects;
    info_prob_matrix is IM.IC_prob_matrix's marginals for information under IC, else None."""
    I, M = set(informed), set(misinformed)
    takeover = mode == "takeover"
    prob_matrix = None
    reach_I, reach_M = set(), set()
    count_I = count_M = None  # LT: active predecessors per side, for ties and takeovers

    if mech_type == "ic":
        if I:
            prob_matrix, reached = IM.IC_prob_matrix(social_network, S=list(I), p=mech_val, mc=mc)
            reach_I = set(reached) - I
        if M:
            reach_M = set(IM.IC_prob_matrix(social_network, S=list(M), p=misinfo_val, mc=mc)[1]) - M
    elif mech_type == "lt":
        if I:
            reach_I = set(IM.lt_prob_matrix(social_network, S=list(I), threshold=mech_val)[1]) - I
        if M:
            reach_M = set(IM.lt_prob_matrix(social_network, S=list(M), threshold=misinfo_val)[1]) - M
        count_I = {u: sum(1 for p in social_network.predecessors(u) if p in I) for u in reach_I | reach_M}
        count_M = {u: sum(1 for p in social_network.predecessors(u) if p in M) for u in reach_I | reach_M}
    elif mech_type == "FJ":
        fj_x = fj_belief_update(social_network, fj_x, info_seeds)
        fj_xm = fj_belief_update(social_network, fj_xm, misinfo_seeds)
        # One draw per side for each person that side could still win
        for node in social_network.nodes():
            if node not in I and (node not in M or (takeover and node not in misinfo_seeds)):
                if random.random() < fj_x[node] ** mech_val:
                    reach_I.add(node)
            if node not in M and (node not in I or (takeover and node not in info_seeds)):
                if random.random() < fj_xm[node] ** misinfo_val:
                    reach_M.add(node)
    else:
        raise ValueError(f"Unknown spread mechanism {mech_type!r}")

    new_I, new_M = set(I), set(M)
    for u in sorted(reach_I | reach_M):
        if u in I:  # only misinformation can reach an informed person
            if takeover and u not in info_seeds and (count_M is None or count_M[u] > count_I[u]):
                new_I.discard(u)
                new_M.add(u)
        elif u in M:
            if takeover and u not in misinfo_seeds and (count_I is None or count_I[u] > count_M[u]):
                new_M.discard(u)
                new_I.add(u)
        elif u in reach_I and u in reach_M:  # uninformed, reached by both this tick
            if count_I is not None and count_I[u] != count_M[u]:
                to_info = count_I[u] > count_M[u]
            else:
                to_info = random.random() < 0.5
            (new_I if to_info else new_M).add(u)
        else:
            (new_I if u in reach_I else new_M).add(u)
    return new_I, new_M, fj_x, fj_xm, prob_matrix


# q: Set to True if you want quarantine with fixed/variable periods and edge restoration after quarantine ends
#    Set to False to disable quarantine entirely
#    Set to "r" if you want quarantine (edges removed on infection) but restore edges immediately upon recovery (no fixed period)
#    Note: the FJ mechanism supports q="r", q=False, or q=True. FJ always uses partial per-edge
#          belief-based removal; q only changes how cut edges are restored.
# q_mech: Tuple controlling the information-spread / opinion model:
#   ("ic", p)         — Independent Cascade; p is a diffusion probability (float) or weighted adjacency matrix
#   ("lt", threshold) — Linear Threshold; threshold is an int/float
#   ("FJ", kappa)     — Friedkin-Johnsen opinion dynamics; kappa > 1 shapes the adoption hazard. Beliefs evolve per
#                       x_i(t+1) = (s_i + sum_j x_j) / (1 + deg_i), with s_i = 1 for seeds and 0 otherwise.
#                       Each step, an uninformed node becomes informed (absorbing) with probability x_i^kappa,
#                       so larger kappa slows adoption and lets low-conviction nodes trickle in over time.
#                       Edge removal is PARTIAL and per-edge for both q="r" and q=True: each live edge (i,j) is
#                       cut independently with probability 1 - e^{-(x_i + x_j)}, so higher shared conviction
#                       raises the chance of severing that tie (a node may lose some ties and keep others).
#                       With q="r", a belief-removed edge is restored when one of its endpoints recovers.
#                       With q=True, it is restored after a fixed quarantine period (a sampled Normal(14,2)
#                       delay, or the integer period if q was passed as an int).
# adherence: Set to a float value between 0 and 1. Ratio of individuals that will adhere to quarantine measures.
#            Can also be a list of nodes that adhere to quarantine
# seeds: a list of seed nodes for information spread. If None, seeds are chosen randomly.
# initial_state_dict: Optional dictionary mapping node -> state (0=S, 1=I, 2=R). If provided, uses this instead of random initial infections.
# misinfo: Set to True to add competing misinformation (see the block comment above competing_spread_step).
#          Off by default, in which case nothing below changes. With it on, every non-adherer
#          is a misinformation seed and adherence becomes "not misinformed".
# misinfo_seeds: extra misinformation seeds beyond the non-adherers: a list/set of nodes, or a count
#          drawn with probability proportional to social degree^2 (as find_seeds does for `seeds`).
# misinfo_mode: "takeover" (each side can convert the other's members) or "collide" (first come, kept).
# misinfo_val: misinformation's IC p / LT threshold / FJ kappa; None uses q_mech's value.
def Simulate_SIR(contact_network, social_network, T, beta, gamma, mu, init,
                 q=False, q_mech=("ic", 0.02), adherence=None, begin_q=0, seeds=None, initial_state_dict=None,
                 misinfo=False, misinfo_seeds=None, misinfo_mode="takeover", misinfo_val=None):

    if begin_q is None:
        begin_q = 0

    mech_type, mech_val = q_mech
    if misinfo:
        if misinfo_mode not in MISINFO_MODES:
            raise ValueError(f"misinfo_mode must be one of {MISINFO_MODES}")
        if misinfo_val is None:
            misinfo_val = mech_val

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

    # FJ edge-restoration period (q=True). None => sample per edge from Normal(14,2);
    # an int => fixed period for every belief-removed edge.
    fj_fixed_period = None

    # If an int is passed as q, we assume it is the quarantine period for all individuals
    if isinstance(q, int) and q > 1:  # > 1 excludes the boolean cases
        d = [q for _ in range(n)]
        fj_fixed_period = q
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

    # FJ opinion-dynamics state (only used when mech_type == "FJ")
    fj_x = {node: 0.0 for node in contact_network.nodes()} if mech_type == "FJ" else None
    fj_s = None  # Prior beliefs; populated at begin_q once seeds are known
    fj_removed_edges = set()       # q="r": belief-removed edges, restored on endpoint recovery
    fj_edge_restore_at = {}        # q=True: belief-removed edge -> timestep to restore

    # NOTE
    avg_avg_just = []

    # Use a set for the informed population from the very beginning to avoid duplicates
    informed = set()
    previous_informed = set()

    # Misinformation (only used when misinfo is True)
    misinformed = set()
    info_seed_set, misinfo_seed_nodes = set(), set()
    fj_xm = None  # FJ: misinformation's belief field
    misinformed_series = []  # Hold list of misinformed at each time step

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

            if misinfo:
                # Misinformers: the explicit misinformation seeds plus every non-adherer
                info_seed_set = set(informed)
                misinformed = misinfo_seed_set(social_network, misinfo_seeds, non_adhering, informed)
                misinfo_seed_nodes = set(misinformed)
                for node in informed:
                    set_info_label(contact_network, social_network, node, 'Informed')
                for node in misinformed:
                    set_info_label(contact_network, social_network, node, 'Misinformed')

            if mech_type == "FJ":
                # s_i = 1 for seeds, 0 for everyone else
                fj_s = {node: (1.0 if node in informed else 0.0)
                        for node in social_network.nodes()}
                if misinfo:  # misinformation's own field, pinned at 1 on its seeds
                    fj_xm = {node: (1.0 if node in misinformed else 0.0) for node in social_network.nodes()}
                # Seeds are stubborn: pin their beliefs at 1.0 from the start
                for node in social_network.nodes():
                    fj_x[node] = fj_s[node]

        #  Influence spreads. Note this is a standalone `if`, not an `elif` off the seeding
        #  branch above: when T_param == 1 (a single-tick call with spread requested), both
        #  the initial seeding AND one round of spread must happen within that same tick.
        if (t > begin_q) or (t == begin_q and T_param == 1):
            if misinfo:
                # Information and misinformation compete; each spreads if it has anyone
                if informed or misinformed:
                    prev_I, prev_M = informed, misinformed
                    informed, misinformed, fj_x, fj_xm, prob_matrix = competing_spread_step(
                        social_network, mech_type, mech_val, misinfo_val, informed, misinformed,
                        info_seed_set, misinfo_seed_nodes, misinfo_mode, fj_x=fj_x, fj_xm=fj_xm, mc=1000)
                    if prob_matrix is not None and isinstance(mech_val, float):
                        quarantine_prob_matrix[t] = prob_matrix
                    for node in informed - prev_I:
                        set_info_label(contact_network, social_network, node, 'Informed')
                    for node in misinformed - prev_M:
                        set_info_label(contact_network, social_network, node, 'Misinformed')
                    # Misinformed people don't quarantine: anyone just misinformed breaks it off
                    break_quarantine(G_initial, contact_network, misinformed - prev_M,
                                     quarantine_statuses, already_quarantining)
            # Can only spread if there are some seed nodes
            elif initial_informed_lst != []:
                if mech_type == "ic":
                    ic_results = IM.IC_prob_matrix(social_network, S=list(informed), p=mech_val, mc=1000, quarantining=quarantine_statuses)
                    prob_matrix = ic_results[0]
                    new_informed_list = ic_results[1]
                    if isinstance(mech_val, float):
                        quarantine_prob_matrix[t] = prob_matrix
                elif mech_type == "lt":
                    lt_results = IM.lt_prob_matrix(social_network, threshold=mech_val, S=list(informed), quarantining=quarantine_statuses)
                    prob_matrix = lt_results[0]
                    new_informed_list = lt_results[1]
                elif mech_type == "FJ":
                    # Linear FJ belief update; seeds stay pinned at 1.0
                    new_fj_x = {}
                    for node in social_network.nodes():
                        if fj_s[node] == 1.0:  # stubborn seed: belief stays pinned
                            new_fj_x[node] = 1.0
                        else:
                            neighbor_belief_sum = sum(fj_x[nb] for nb in social_network.neighbors(node))
                            deg = social_network.degree(node)
                            new_fj_x[node] = (fj_s[node] + neighbor_belief_sum) / (1 + deg)
                    fj_x = new_fj_x

                    # Absorbing per-step adoption: an uninformed node becomes informed
                    # this step with probability x_i^kappa (mech_val is kappa, kappa > 1).
                    # Larger kappa suppresses low-conviction nodes, stretching adoption
                    # over time even after the belief field has equilibrated.
                    kappa = mech_val
                    new_informed_list = [node for node in social_network.nodes()
                                         if node not in informed
                                         and random.random() < fj_x[node] ** kappa]

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

        # FJ + q=True: restore edges whose fixed quarantine period has elapsed (before re-cutting)
        if mech_type == "FJ" and q is True and fj_x is not None:
            for (a, b) in [e for e, rt in fj_edge_restore_at.items() if t >= rt]:
                contact_network.add_edge(a, b)
                del fj_edge_restore_at[(a, b)]

        # 1. Cut valid ties first (quarantine on the pre-step graph)
        if q is not False:
            if mech_type == "FJ":
                # Partial, per-edge belief-based removal for ALL quarantine modes (q="r" and q=True).
                # Each live edge (i,j) is cut independently with probability 1 - e^{-(x_i + x_j)};
                # higher shared conviction raises the chance of severing the tie, and a node can
                # lose some ties while keeping others.
                if t > begin_q and fj_x is not None:
                    # Misinformed people don't quarantine, so their conviction cuts no ties
                    cut_x = fj_x if not misinfo else {
                        u: (0.0 if u in misinformed else x) for u, x in fj_x.items()}
                    for (u, v) in list(contact_network.edges()):
                        if random.random() < 1.0 - math.exp(-(cut_x[u] + cut_x[v])):
                            contact_network.remove_edge(u, v)
                            e = (min(u, v), max(u, v))
                            if q == "r":
                                # restored when an endpoint recovers
                                fj_removed_edges.add(e)
                            elif q is True:
                                # restored after a fixed/sampled quarantine period
                                period = fj_fixed_period if fj_fixed_period is not None \
                                    else abs(round(np.random.normal(loc=14, scale=2)))
                                fj_edge_restore_at[e] = t + period
            else:
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

            # Record who is currently informed (absorbing set, tracked via node attribute)
            if is_informed:
                    infm_current.append(u)

                    # Record who is currently infected and informed
                    if state[u] == 1:
                        i_prime_current.append(u)

            # At t==0, the state transition logic will not suffice. So check if anyone needs to be quarantined
            # Determine what quarantines need to be made
            if copy_state[u] != state[u] or t == 0:
                # Record in state changes the time at which said change occurred
                state_changes[u] = (u, state[u], t)

            # Handle restoration and quarantine duration tracking only when q is True (fixed/variable period).
            # FJ uses edge-based restoration (handled above), so skip the node-based path for it.
            if q is True and mech_type != "FJ":
                if is_informed and (1 <= quarantine_statuses[u] <= d[u]):
                    quarantine_statuses[u] += 1
                    # If the quarantine time has been reached, end quarantine and restore edges
                    if quarantine_statuses[u] >= d[u]:
                        quarantine_statuses[u] = 0   # Reset quarantine counter
                        restore_edges(G_initial, contact_network, u, already_quarantining=already_quarantining)

            # Immediate restoration on recovery when q == "r"
            if q == "r" and state[u] == 2 and copy_state[u] != 2:  # Just recovered this step
                quarantine_statuses[u] = 0
                if mech_type == "FJ":
                    # Re-add only the belief-removed edges incident to u
                    for (a, b) in [e for e in fj_removed_edges if u in e]:
                        contact_network.add_edge(a, b)
                        fj_removed_edges.discard((a, b))
                else:
                    restore_edges(G_initial, contact_network, u, already_quarantining=already_quarantining)

        informed_infected_series.append(i_prime_current)
        informed_series.append(infm_current)
        misinformed_series.append(sorted(misinformed))

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

    # misinformed_series (index 11) is a list of empty lists unless misinfo is on
    return contact_network, state_changes, infection_data, quarantine_prob_matrix, state_series, social_network, dynamic_degree, informed_infected_series, informed_series, adhering, all_edges, misinformed_series