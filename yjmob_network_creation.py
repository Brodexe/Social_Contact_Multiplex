import networkx as nx
import py4cytoscape as p4c
import numpy as np
import random

ping_cytoscape = False

# Sampled from YJMob100k dataset #2
file_path = "experiment_data/yjmob_1000_sample.csv"

# Enum of sample sizes — change SAMPLE_SIZE_IDX to select a different size
SAMPLE_SIZES = (200, 500, 750, 1000)
SAMPLE_SIZE_IDX = 3  # 0 → 100, 1 → 250, 2 → 500, 3 → 1000
sample_size = SAMPLE_SIZES[SAMPLE_SIZE_IDX]

lines = []

# Read all lines
with open(file_path, 'r') as f:
    header = next(f).strip()  # read header
    for line in f:
        lines.append(line.strip())

# Select sample_size distinct user IDs and filter all data to only those users
all_user_ids = list({line.split(',')[0] for line in lines})
random.seed(42)
selected_users = set(random.sample(all_user_ids, sample_size))
lines = [line for line in lines if line.split(',')[0] in selected_users]

# Create a dictionary from day intervals to their respective data
interval = 15
day_data_initial = {}
for line in lines:
    user_id, day, time, x_coord, y_coord = line.split(',')
    day = int(day)
    interval_key = day // interval
    if interval_key not in day_data_initial:
        day_data_initial[interval_key] = []
    day_data_initial[interval_key].append((
        user_id,
        # Treat intervals as one continuous "day"
        (day % interval) * 48 + int(time),
        (float(x_coord), float(y_coord))
    ))

# Sort day_data_initial by key
day_data_initial = dict(sorted(day_data_initial.items()))

# Create dictionaries within each interval for their respective users
day_data_final = {}
# Iterate over (key, value) pairs in the interval dictionary
for interval_key, interval in day_data_initial.items():
    # Create a new dictionary for each interval
    user_dict = {}
    for record in interval:
        # Obtain user_id
        user_id = record[0]
        if user_id not in user_dict:
            user_dict[user_id] = []
        # Append the record to the user's list
        user_dict[user_id].append((
            record[1],
            record[2]
        ))
    # Assign the user dictionary to the finalized day data
    day_data_final[interval_key] = user_dict

# Now, day_data_final is structured as:
# { interval_key: { user_id: [ (time, (x coord, y coord)), ... ] } }

# Determine collisions within each interval (will correspond to edges in the graph)
#   A collision is defined as two users being in the same (x_coord, y_coord) within a 2 time unit window
# Collisions stored as {(user1, user2): count}
contact_networks = []
all_collisions = {}

for interval_key, interval_data in day_data_final.items():
    collision_data = {}

    # Cartesian distance
    def distance(coords1, coords2):
        return ((coords1[0] - coords2[0]) ** 2 + (coords1[1] - coords2[1]) ** 2) ** 0.5

    # Iterate through each user and their time-coordinates
    for userID, user_data in interval_data.items():
        user_time_length = len(user_data)
        for t_index in range(user_time_length):
            # Since we care about collisions within a 2 time unit window,
            # check current and next coordinate
            cur_coord = user_data[t_index][1]
            next_coord = None
            if t_index == user_time_length - 1:
                next_coord = cur_coord  # No next coord, stay the same
            else:
                next_coord = user_data[t_index + 1][1]  # Get next coord

            # Compare to all other users
            for other_userID, other_user_data in interval_data.items():
                if other_userID == userID:
                    continue
                other_time_length = len(other_user_data)
                if other_time_length < user_time_length:
                    continue  # More comparisons happen when other user has fewer time points
                            # This avoid redundancy
                else:
                    other_coord = other_user_data[t_index][1]
                    # Check distance for current coords
                    if distance(cur_coord, other_coord) == 0 or distance(next_coord, other_coord) == 0:
                        # Record collision
                        edge = tuple(sorted((userID, other_userID)))
                        # Record collision in local collision data
                        if edge not in collision_data:
                            collision_data[edge] = 1
                        else:
                            collision_data[edge] += 1
                        # Record collision in global collision data
                        if edge not in all_collisions:
                            all_collisions[edge] = 1
                        else:
                            all_collisions[edge] += 1

    #---------------
    # Contact network creation
    #---------------

    # Create an undirected contact network from collision data
    contact_network = nx.Graph()
    for edge in collision_data.keys():
        contact_network.add_edge(edge[0], edge[1])

    contact_networks.append(contact_network)

#---------------
# Social network creation based on global collision frequency
#---------------

# Compute the 75th percentile of the collision count distribution
collision_counts = np.array(list(all_collisions.values()))
percentile_75 = np.percentile(collision_counts, 75)

social_network = nx.Graph()
for edge, count in all_collisions.items():
    if count >= percentile_75:
        social_network.add_edge(edge[0], edge[1])

# Make the social network directed
social_network = social_network.to_directed()

#---------------
# Ensure all networks have the same nodes
#---------------

# Find the union of all nodes across all intervals
all_nodes = set()
for contact_network in contact_networks:
    all_nodes.update(contact_network.nodes())

# Add missing nodes to each interval's social and contact networks
for i in range(len(contact_networks)):
    contact_network = contact_networks[i]
    for node in all_nodes:
        if node not in contact_network:
            contact_network.add_node(node)
        if node not in social_network:
            social_network.add_node(node)

# Create a single consistent mapping: original user_id -> consecutive integer 0,1,2,...
all_nodes = sorted(all_nodes)
mapping = {old_label: new_id for new_id, old_label in enumerate(all_nodes)}

# Apply the SAME mapping to ALL contact and social networks, updating the lists
for i in range(len(contact_networks)):
    contact_networks[i] = nx.relabel_nodes(contact_networks[i], mapping)
social_network = nx.relabel_nodes(social_network, mapping)

# Now save the relabeled graphs
for interval_key in day_data_final.keys():  # Use interval keys for naming
    # Find the index corresponding to this interval_key
    i = list(day_data_final.keys()).index(interval_key)
    contact_network = contact_networks[i]

    # Print mean node degree for contact network
    degrees = [deg for node, deg in contact_network.degree()]
    mean_degree = sum(degrees) / len(degrees)
    print(f"Interval {interval_key}: Contact Network Mean Node Degree: {mean_degree}")

    social_network = social_network

    if ping_cytoscape:
        cyto_social = nx.to_undirected(social_network)
        # Relabel social network nodes to (len(all_nodes) + original_id) to avoid overlap
        cyto_social = nx.relabel_nodes(cyto_social, {old_label: len(all_nodes) + old_label for old_label in cyto_social.nodes()})
        union_network = nx.union(contact_network, cyto_social)

        p4c.create_network_from_networkx(union_network, title=f"YJMob Networks {interval_key}", collection="YJMob Networks")

    # Print number of edges in social, contact networks
    print(f"Interval {interval_key}: Contact Network Edges: {contact_network.number_of_edges()}")
    print(f"Social Network Edges: {social_network.number_of_edges()}")

    nx.write_gml(contact_network, f"experiment_data/yjmob_{sample_size}_contact{interval_key}.gml")
    nx.write_gml(social_network, f"experiment_data/yjmob_{sample_size}_social.gml")
