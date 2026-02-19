import IM
import SIR
import networkx as nx
import matplotlib.pyplot as plt
import correlated_graphs
import py4cytoscape as p4c
import random as random
import numpy as np
import find_seeds
import parse
from copy import deepcopy

# 2 ways that graphs can be saved in this code: Pinging Cytoscape via py4cytoscape, or saving a graph to gml file.
# Change this to True if you want Cytoscape to be pinged from py4cytoscape
ping_cytoscape = False

# Change to True if you want to save to a gml file
save_gmls = False

# Change to True if you want to plot using matplotlib
draw_inline = True

# Change to True if you want to view the comparison of our algorithm with random selection
edge_removal_comparison = True

#------- 
#
#  Generate the contact network
#
#-------

T = 100
Repeat = 1

# Epidemic parameters
beta = 0.3  # Infection rate
gamma = 0.03  # Recovery rate
mu = 0.05  # Immunity loss rate
init = 0.05
verbose = False
q = False

# Specify the filename
filename = 'contact_network_text.txt'
# Create the graph from the file
contact_graph = parse.parse(filename)

# Relabel nodes in parsed graph to avoid off by 1 errors in SIR.py
# Create a mapping from old node to new node: i -> i - 1
mapping = {node: node - 1 for node in contact_graph.nodes()}

# Relabel the nodes
contact_graph = nx.relabel_nodes(contact_graph, mapping)

# Save to a GML file
if save_gmls == True:
    nx.write_gml(contact_graph, "initial_contact_network.gml")

if ping_cytoscape == True:
    # Check Cytoscape connection
    p4c.cytoscape_ping()
    # Send the NetworkX graph to Cytoscape
    p4c.create_network_from_networkx(contact_graph, collection="My NetworkX Graph", title="Initial Contact")


#---------
#
#  Generate the social network
#
#---------

social_graph = correlated_graphs.create_w_k_hop_correlation(contact_graph, k=1)[0]   # Create a 1-hop graph from contact network

if save_gmls == True:
    nx.write_gml(social_graph, "initial_social_network.gml")

if ping_cytoscape == True:
    # # Check Cytoscape connection
    p4c.cytoscape_ping()
    # Send the NetworkX graph to Cytoscape
    p4c.create_network_from_networkx(social_graph, collection="My NetworkX Graph", title="Initial Social")

# The tuple (G, state) is stored in state_tuple variable
state_tuple = SIR.Simulate_SIR(social_network=social_graph,contact_network=contact_graph,T=T,beta=beta,
                               gamma=gamma,mu=mu,init=init,average_data=False,q=q)
contact_graph = state_tuple[0]
infection_statuses = state_tuple[1] # Giving these variables their own names for simplicity

label = ""
for triple in infection_statuses:
    # Recall: infection_statuses consists of ordered triples.
    current_status = triple[1]

    if current_status == 0:
        label = "Susceptible"
    elif current_status == 1:
        label = "Infected"
    elif current_status == 2:
        label = "Recovered"

    nx.set_node_attributes(contact_graph, {triple: label}, "label")

#---------
#
#  Draw one graph below the other
#
#---------

if draw_inline == True:
    pos1 = nx.random_layout(social_graph)

    # Create positions for the second graph, placing nodes below G1
    pos2 = {}
    y_offset = -2  # Vertical distance to shift G2 below G1
    for node in pos1:
        x, y = pos1[node]  # Get x, y from G1's position
        pos2[node] = (x, y + y_offset)  # Same x, lower y

    # Draw the first graph
    nx.draw(social_graph, pos1, with_labels=True, node_color='blue', node_size=100, font_size=12, label='Social Network')

    num_edges = len(contact_graph.edges())

    # Draw the second graph on the same plot
    nx.draw(contact_graph, pos2, with_labels=True, node_color='lightgreen', node_size=100, font_size=12, label='Contact Network')

    # Display the plot
    plt.show()


#----------
#
#  Influence Maximization for Social Network -> Informed Contact Network Algorithm
#
#----------

"""
Algorithm:
Informing_Contact(social network, contact network, seed nodes)

Informed <-- node set from running IM.py Greedy(params)

for i <-- 1 to n:
    if A[i] in Informed and B[i] in Infected:
        remove all of B[i]'s neighboring edges

"""

print("infection_statuses: ", infection_statuses)

# k: # of nodes we are allowed to choose in I.M.
def Informing(k, social_network, contact_network, num_seeds):
    # Side effect: Sets "seed" attribute in social network
    seeds = find_seeds.find_seed_set(social_network, exponent=1, num_seeds=num_seeds)

    # Sets "seed" attribute in contact network too
    for node in seeds:
        # Set attribute for node 1
        nx.set_node_attributes(contact_network, {node: {'Seed?': 'Initial Seed'}})

    print("seeds: ", seeds)

    maximization_result = IM.greedy_for_ic(g=social_network,k=k,S=seeds)
    max_influence_nodes = maximization_result[0]

    print("Influence Maximization Results (Greedy Algorithm): ", max_influence_nodes)

    edges_to_remove = []

    for node in max_influence_nodes:
        if infection_statuses[node][1] == 1:
            # Get all neighbors of the target node
            neighbors = list(contact_network.neighbors(node))

            # Set attribute for node 1
            nx.set_node_attributes(social_network, {node: {'Informed?': 'Informed'}})
            nx.set_node_attributes(contact_network, {node: {'Informed?': 'Informed'}})

            # Remove edges between the node and its neighbors
            edges_to_remove = [(node, neighbor) for neighbor in neighbors]
            print("edges_to_remove: ", edges_to_remove)
            contact_network.remove_edges_from(edges_to_remove)

    return contact_network, edges_to_remove

#------------
#
# Simulate some changes to the contact network
#
#------------

final_contact = Informing(3, social_network=social_graph, contact_network=contact_graph, num_seeds=12)[0]

if ping_cytoscape == True:
    # Check Cytoscape connection
    p4c.cytoscape_ping()
    # Send the NetworkX graph to Cytoscape
    p4c.create_network_from_networkx(final_contact, collection="My NetworkX Graph", title="Final Contact")

    # Check Cytoscape connection
    p4c.cytoscape_ping()
    # Send the NetworkX graph to Cytoscape
    p4c.create_network_from_networkx(social_graph, collection="My NetworkX Graph", title="Final Social")

if save_gmls == True:
    nx.write_gml(contact_graph, "final_contact_network.gml")
    nx.write_gml(social_graph, "final_social_graph.gml")

if draw_inline == True:
    # Draw the first graph
    nx.draw(social_graph, pos1, with_labels=True, node_color='lightblue', node_size=100, font_size=12, label='Social Network')

    num_edges = len(contact_graph.edges())
    # print("Number of edges after informing algorithm:", num_edges)
    # Draw the second graph on the same plot
    nx.draw(contact_graph, pos2, with_labels=True, node_color='lightgreen', node_size=100, font_size=12, label='Contact Network')
    print("Final contact network:")
    print(contact_graph.nodes(data=True))
    # Display the plot
    plt.show()


# ---------
#
#  Results of the above algorithm when varying k
#
# ---------

def RunExample():
    edge_vals = [] # y vals to plot
    for new_k in range(1,11):
    # Reset graph to original state each iteration
        save_contact = deepcopy(contact_graph)  # Fresh copy each time
        save_social = deepcopy(social_graph)
        
        # Run the function with current k
        new_graph = Informing(new_k, save_social, save_contact, num_seeds=12)[0]
        
        # Count edges after modification
        edge_vals.append(len(new_graph.edges()))

    x = list(range(len(edge_vals))) # Simply the x values to plot

    # Now edge removal with no heuristic (randomly chosen nodes)
    seeds = [x for x in range(0,6)] # This is an arbitrary selection of seeds
    x_2 = [] # New set of stuff to plot
    edge_vals2 = [] # y vals to plot
    for i in range(1,11):
        copy_graph = deepcopy(contact_graph) # Want to work on a fresh graph each time

        for _ in range(0,i):
            random_node = random.choice(seeds)
            # random_node = random.randint(1, len(contact_graph) - 1)

            if infection_statuses[random_node][1] == 1:
                # Get all neighbors of the target node
                neighbors = list(contact_graph.neighbors(random_node))

                # Remove edges between the node and its neighbors
                edges_to_remove = [(random_node, neighbor) for neighbor in neighbors]
                copy_graph.remove_edges_from(edges_to_remove)

        edge_vals2.append(len(copy_graph.edges()))

    x_2 = list(range(len(edge_vals2))) # x values to plot

    # Create the plot
    plt.plot(x, edge_vals, 'b-o', label='Informing Algorithm')  # Add label for blue line
    plt.plot(x_2, edge_vals2, 'r-o', label='Random')           # Add label for red line
    plt.xlabel('k values')
    plt.ylabel('edge count')
    plt.title('k vs edge count')
    plt.grid(True)
    plt.legend()  # Add the legend
    plt.show()

if edge_removal_comparison == True:
    RunExample()
