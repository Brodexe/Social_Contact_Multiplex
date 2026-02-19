import networkx as nx
import numpy as np
import IM

# Probabilistic way of finding seed nodes, given an initial set
#   P_i(seed) = (d_i)^k / sum_j ((d_j)^k)
# n is the number of seeds we want
# exponent to control degree weighting
def find_seed_set(social_graph, num_seeds, exponent=1):
    # Get degrees of all nodes
    degrees = dict(social_graph.degree())  # {node: degree}

    # Calculate probabilities
    nodes = list(degrees.keys())
    epsilon = 1e-6  # tiny bump to prevent 0 probabilities
    probs = [(degrees[node] ** exponent) + epsilon for node in nodes]
    total = sum(probs)
    probs = [p / total for p in probs]

    if np.count_nonzero(probs) < num_seeds:
        raise ValueError(f"Cannot choose {num_seeds} seeds — only {np.count_nonzero(probs)} nodes have non-zero probability.")

    # Create the initial seed set
    seed_set = list(np.random.choice(nodes, size=num_seeds, replace=False, p=probs))

    for node in seed_set:
        nx.set_node_attributes(social_graph, {node: {'is_seed': 'Seed'}})

    return seed_set

# lt == True: linear threshold model. lt == False: independent cascade model
def initialize_social_IM(social_network,k=None,p=0.3,num_seeds=1,lt_threshold = None):
    seeds = find_seed_set(social_network, num_seeds, exponent=1)
    if lt_threshold == None:
        result = IM.greedy_for_ic(social_network, k, seeds, p)
    else:
        result = IM.greedy_for_lt(social_network, seeds, k, lt_threshold)
    max_influence = result[0]
    spread = result[1]

    return max_influence