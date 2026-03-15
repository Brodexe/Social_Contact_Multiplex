import numpy as np
import random
import networkx as nx
import copy

# Returns probability matrix of node i being informed
# S: Nodes that are already informed
# p: Probability of activation (can be a scalar or a vector)
# mc: Number of Monte Carlo simulations
# quarantining: List of nodes currently quarantining
def IC_prob_matrix(g, S, p, mc=1000, quarantining=None):
    if S == []:
        raise ValueError("S cannot be empty")

    n = len(g.nodes())
    quarantine_list = []

    for _ in range(mc):
        A = S[:]                     # active set starts with seeds
        new_ones = []
        
        for node in S:               # only seeds attempt activation (same mechanics)
            out_neighbors = list(g.successors(node))
            
            if isinstance(p, (int, float)):
                # homogeneous case - uniform probability on every edge
                success = [u for u in out_neighbors if random.uniform(0, 1) < p]
            elif isinstance(p, np.ndarray):
                # heterogeneous case - edge-specific probability p[node, u]
                # (works whether p is dense or you pass a full adjacency matrix)
                success = [u for u in out_neighbors if random.uniform(0, 1) < p[node, u]]
            else:
                raise TypeError("p must be a float (homogeneous) or np.ndarray (n x n weighted adjacency matrix)")
            
            new_ones += success
        
        # add newly activated nodes (union semantics - a node activates if at least one incoming edge from S succeeds)
        new_active = list(set(new_ones) - set(A))
        A += new_active
        A = list(set(A))
        
        # record the outcome of this Monte-Carlo run
        one_run = np.zeros((1, n))
        for node in A:
            one_run[0][node] = 1
        quarantine_list.append(one_run)

    # average over all simulations → marginal activation probability vector
    quarantine_matrix = np.array(quarantine_list)
    quarantine_matrix = np.mean(quarantine_matrix, axis=0)   # shape (1, n)

    # final informed set: one stochastic realization drawn from the marginal probabilities
    A_final = [node for node in g.nodes() if random.uniform(0, 1) < quarantine_matrix[0][node]]

    return quarantine_matrix, A_final

def IC(g, S, p, mc=1000):
    spread = []

    for _ in range(mc):
        A = set(S)               # All activated nodes
        new_active = set(S)      # Nodes activated in last round

        while new_active:
            next_active = set()

            for node in new_active:
                for neighbor in g.successors(node):
                    if neighbor not in A:
                        if random.random() < p:
                            next_active.add(neighbor)

            A |= next_active
            new_active = next_active

        spread.append(len(A))

    return np.mean(spread), list(A)

# k: Number of nodes that are allowed to be informed
def greedy_for_ic(g,k,p,mc,S=None):
    if S == None: S = []
    spread = []

    for _ in range(k):  # k nodes of maximimum influence
        best_spread = 0
        for j in g.nodes():  # Look at nodes not yet in the set
            if j in S:
                continue
            s = IC(g, S + [j], p, mc)[0]
            if s > best_spread:
                best_spread, node = s, j
        S.append(node)
        spread.append(best_spread)

    return S, spread

def lt_prob_matrix(g, S, threshold=1, quarantining=None):
    if S == []: raise ValueError("S cannot be empty")

    A = S[:]
    quarantine_vector = np.zeros((1, len(g.nodes())))

    for node in g.nodes():
        if node not in A:  # Not yet informed
            total_influence = len(
                [pred for pred in g.predecessors(node) if pred in A]
            )
            if total_influence >= threshold:
                A.append(node)

    for node in A:
        # if node in quarantining:
        quarantine_vector[0][node] = 1

    return quarantine_vector[0], A  # Return the average probability matrix and the final set of informed nodes

# k: # of seeds nodes that can be chosen to inform
def greedy_for_lt(g, seed_candidates, k=3, threshold=1):
    selected_seeds = set()
    current_spread = 0

    for _ in range(k):
        best_node = None
        best_spread = -1

        # Evaluate each candidate node
        for node in set(seed_candidates) - selected_seeds:
            # Temporarily add node to selected seeds
            temp_seeds = selected_seeds | {node}
            # Compute influence spread with temporary seed set
            spread = len(LT(g, threshold, temp_seeds))
            
            # Update best node if spread is larger
            if spread > best_spread:
                best_spread = spread
                best_node = node

        # If a best node is found, add it to selected seeds
        if best_node is not None:
            selected_seeds.add(best_node)
            current_spread = best_spread
        else:
            break

    return selected_seeds, current_spread

def LT(g, threshold, initial_active: set = None):
    # Initialize active nodes
    active = set(initial_active) if initial_active else set()
    influence_result = set(active)  # Track all influenced nodes
    new_ones = True  # Flag to track new activations

    while new_ones == True:
        new_ones = False
        for node in g.nodes():
            if node not in influence_result:  # Not yet influenced
                # Sum weights from active predecessors
                total_influence = len(
                    [pred for pred in g.predecessors(node) if pred in influence_result]
                )
                # Check if threshold is exceeded
                if total_influence >= threshold:
                    influence_result.add(node)
                    new_ones = True

    return list(influence_result)

# Greedy influence maximization algorithm for small networks
# Gives a ranking of nodes by influence spread, 
# and the cumulative spread as we add more nodes to the seed set
# target: desired spread to reach
# S: minimal seed set to reach target
def greedy_for_ic_target(g, p, mc, target, S_init=None):
    if S_init is None:
        S_init = []

    S = copy.deepcopy(S_init)
    ranking = []
    cumulative_spread = []

    # Current spread of initial seeds
    current_spread = IC(g, S, p, mc)[0] if S else 0

    if current_spread >= target:
        return S, ranking, cumulative_spread

    remaining_nodes = set(g.nodes()) - set(S)

    while remaining_nodes:

        best_spread = -1
        best_node = None

        for node in remaining_nodes:
            spread = IC(g, S + [node], p, mc)[0]

            if spread > best_spread:
                best_spread = spread
                best_node = node

        # Add best node
        S.append(best_node)
        ranking.append(best_node)
        cumulative_spread.append(best_spread)

        remaining_nodes.remove(best_node)
        current_spread = best_spread

        # Stop once target is reached
        if current_spread >= target:
            break

    return S, ranking, cumulative_spread