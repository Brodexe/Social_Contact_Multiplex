import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random
from copy import deepcopy

k_hop_simulation = False

def create_correlated_digraph(base_graph, correlation_factor, base_probability=0.01):
    """
    Creates a directed graph A where edge existence correlates with 
    an undirected base graph B, with better sparsity control
    correlation_factor: float between 0 and 1, controls correlation strength
    base_probability: float between 0 and 1, controls overall density
    """
    num_nodes = len(base_graph.nodes()) 

    # Create empty directed graph A
    A = nx.DiGraph()
    A.add_nodes_from(range(num_nodes))
    
    # Get edges from base graph (undirected)
    b_edges = set(base_graph.edges())
    
    # Consider all possible directed edges
    possible_edges = [(i, j) for i in range(num_nodes) 
                     for j in range(num_nodes) if i != j]
    
    # For each possible directed edge in A
    for edge in possible_edges:
        edge_undirected = tuple(sorted(edge))
        
        # Base probability modified by correlation
        if edge_undirected in b_edges:
            # Edges present in B get a boost
            prob = base_probability * (1 + correlation_factor)
        else:
            # Edges not in B get reduced probability
            prob = base_probability * (1 - correlation_factor)
            
        # Cap probability at 1
        prob = min(prob, 1.0)
        
        # Add directed edge probabilistically
        if np.random.random() < prob:
            A.add_edge(*edge)
    
    return A

def create_w_k_hop_correlation(base_graph, k):
    x_vals, y_vals = [], []

    # Initialize an empty unweighted graph
    correlated_graph = nx.DiGraph()
    
    # Add all nodes from the base graph to the correlated graph
    correlated_graph.add_nodes_from(base_graph.nodes())
    nodes = list(base_graph.nodes()) # Node list we will be working with
    
    # Compute Jaccard similarity for each pair of nodes based on k-hop neighborhoods
    for idx_i, i in enumerate(nodes):
        # Get the k-hop neighborhood of node i (ego graph with radius k)
        i_neighbors = set(nx.ego_graph(base_graph, i, radius=k).nodes())
        for j in nodes[idx_i + 1:]:  # Avoid duplicate pairs (i,j) and (j,i)
            # Get the k-hop neighborhood of node j
            j_neighbors = set(nx.ego_graph(base_graph, j, radius=k).nodes())
            
            # Compute intersection and union
            intersection = len(i_neighbors & j_neighbors)
            union = len(i_neighbors | j_neighbors)
            
            # Handle division by zero
            if union == 0:
                similarity = 0.0
            else:
                similarity = intersection / union
            
            # Add an edge with probability equal to the Jaccard similarity
            if random.random() < similarity:
                correlated_graph.add_edge(i, j)  # Unweighted edge

            x_vals.append(similarity)
            y_vals.append(1 if correlated_graph.has_edge(i, j) else 0)

    return correlated_graph, (x_vals, y_vals)  # Return the graph, similarity matrix, and x,y values for plotting

def jaccard_similarity(set1, set2):
    set1, set2 = set(set1), set(set2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0

def create_social_graph(H, nE=None):
    if nE == None:
        nE = H.number_of_edges() * 2  # Default to twice the number of edges in H

    # Ego networks and Jaccard similarity
    K = 2
    N = sorted(H.nodes())
    Ego = {u: list(nx.ego_graph(H, u, radius=K).nodes()) for u in N}

    # Compute Jaccard similarity for each pair
    sim = {(N[i], N[j]): jaccard_similarity(Ego[N[i]], Ego[N[j]])
        for i in range(len(N) - 1) for j in range(i + 1, len(N))}

    # Rank similarities (high sim → low rank → high probability)
    sorted_pairs = sorted(sim.items(), key=lambda x: x[1], reverse=True)
    ranks = {pair: rank + 1 for rank, (pair, _) in enumerate(sorted_pairs)}

    # Build edge list and sampling probabilities
    A = list(ranks.keys())
    prob = [1 / ranks[pair] for pair in A]
    prob = [p / sum(prob) for p in prob]

    # Sample edges based on rank-weighted probability
    sampled_indices = np.random.choice(len(A), size=nE, replace=False, p=prob)
    sampled_edges = [A[i] for i in sampled_indices]

    # Build directed social graph G
    G = nx.DiGraph()
    G.add_nodes_from(H.nodes())
    for (u, v) in sampled_edges:
        if random.choice([0, 1]) == 0:
            G.add_edge(u, v)
        else:
            G.add_edge(v, u)

    return G, sim


