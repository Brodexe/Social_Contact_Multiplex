import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import networkx as nx
import random
from collections import Counter
from itertools import combinations
import IM
import correlated_graphs

n = 50
p = 0.05
contact_network = nx.erdos_renyi_graph(n, p, seed=42)
social_network = correlated_graphs.create_social_graph(contact_network, 2 * contact_network.number_of_edges())[0]

giant_component = max(nx.strongly_connected_components(social_network), key=len)

# Target: 95% of nodes influenced
pi_min, _, _ = IM.greedy_for_ic_target(social_network, p=0.3, mc=1000, target=0.75 * n, S_init=None)

print("Set of seeds selected by greedy algorithm: ", pi_min)

t_p = None
theta = None

def count_simple_paths_k(source, target, k):
    def dfs(node, visited, depth):
        if depth > k:
            return 0
        if node == target:
            return 1
        
        count = 0
        for neighbor in social_network.successors(node):
            if neighbor not in visited:
                count += dfs(neighbor, visited | {neighbor}, depth + 1)
        return count

    return dfs(source, {source}, 0)

def r_ball(g, source, r, include_self=True):
    nodes = set(nx.single_source_shortest_path_length(g, source, cutoff=r).keys())
    if not include_self:
        nodes.discard(source)
    return nodes

def intersection_of_r_balls(g, nodes, r):
    if not nodes:
        return set()
    
    balls = [r_ball(g, v, r) for v in nodes]
    return set.intersection(*balls)

p_to_k = (sum([p ** k for k in range(1, t_p - theta + 1)])) ** len(pi_min)

prod = 1
for i, seed in enumerate(pi_min):
    k = i + 1
    intersection = intersection_of_r_balls(social_network, pi_min, r=k)
    prod *= sum([count_simple_paths_k(node, target=seed, k=t_p - theta)] for node in intersection)