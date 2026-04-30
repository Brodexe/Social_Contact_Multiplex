import networkx as nx
import pandas as pd
import py4cytoscape as p4c

ping_cytoscape = True

# (1) Social network
social_df = pd.read_csv('capstone_proj_data/high_school_social.csv', sep=' ', header=None, names=['u', 'v'])
social_network = nx.from_pandas_edgelist(social_df, source='u', target='v')
social_network = social_network.to_undirected()
nx.set_node_attributes(social_network, {n: str(n) for n in social_network.nodes()}, 'name')

# (2) Contact networks from HS_data split into 19 sequential time bins
hs_df = pd.read_csv('capstone_proj_data/HS_data.csv', sep=' ', header=None, names=['t', 'u', 'v'])

hs_df['bin'] = pd.cut(hs_df['t'], bins=19, labels=False)
partitions = [hs_df[hs_df['bin'] == i] for i in range(19)]

contact_networks = []
for part in partitions:
    G = nx.from_pandas_edgelist(part, source='u', target='v')
    # (3) Remove isolated nodes (nodes without connections)
    isolates = list(nx.isolates(G))
    G.remove_nodes_from(isolates)
    # (4) Make undirected
    G = G.to_undirected()
    nx.set_node_attributes(G, {n: str(n) for n in G.nodes()}, 'name')
    contact_networks.append(G)

# Save the contact networks and social network as GMLs
nx.write_gml(social_network, 'capstone_proj_data/high_school_social.gml')
for i, G in enumerate(contact_networks):
    nx.write_gml(G, f'capstone_proj_data/high_school_contact_bin{i+1}.gml')

if ping_cytoscape:
    p4c.cytoscape_ping()

    p4c.create_network_from_networkx(social_network, title='HS Social Network', collection='High School Networks')

    for i, G in enumerate(contact_networks):
        if G.number_of_nodes() == 0:
            continue
        p4c.create_network_from_networkx(G, title=f'HS Contact Bin {i+1}', collection='High School Networks')