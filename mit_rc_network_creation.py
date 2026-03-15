import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import timedelta
import numpy as np

# Create weighted, undirected social network from Reality Commons Social Evolution dataset
# Weights will represent cascade probabilities
# Relationship types present in Reality Commons dataset:
# 1. Close friends, 2. socialize twice per week
# 3. Political discussant, 4. Facebook tagged photo, 5. Twitter like 

#---------------
#
#  Generate social network from Social Evolution survey data
#
#---------------

# If a pair of users have multiple relationship types, 
# we will take the maximum weight among those types as the edge weight in the social network
# Reason for not doing sum: close friend is already a strong relationship, and is explicit in the data
social_file = "capstone_proj_data/RelationshipsFromSurveys.csv"
with open(social_file, 'r') as file:
    header = next(file)  # Skip header

# === CONFIGURE WEIGHTS ===
relationship_to_weight = {
    "CloseFriend": 0.09,
    "SocializeTwicePerWeek": 0.07,
    "PoliticalDiscussant": 0.05,
    "FacebookAllTaggedPhotos": 0.03,
    "BlogLivejournalTwitter": 0.01
}

# === LOAD CSV ===
df = pd.read_csv(social_file)

# === BUILD DIRECTED NETWORK (reversed: B → A, max weight per direction) ===
social_network = nx.DiGraph()
edge_max_weight = {}

for _, row in df.iterrows():
    a = int(row['id.A'])
    b = int(row['id.B'])
    if a == b:
        continue  # skip self-loops
    
    rel = row['relationship']
    w = relationship_to_weight.get(rel, 0.0)
    
    # REVERSED direction: if A reports B, arrow goes B → A
    u, v = b, a
    key = (u, v)
    if key not in edge_max_weight or w > edge_max_weight[key]:
        edge_max_weight[key] = w

for (u, v), w in edge_max_weight.items():
    social_network.add_edge(u, v, weight=w)

# === ENSURE ALL NODES 1–84 ARE PRESENT ===
ALL_NODES = set(range(1, 85))  # 1 to 84 inclusive
social_network.add_nodes_from(ALL_NODES)

# === OUTPUT ===
print("Directed edges (reversed: nominee → nominator) with max weights:")
for u, v, data in sorted(social_network.edges(data=True)):
    print(f"{u} → {v} : {data['weight']:.2f}")

print(f"\nNodes: {social_network.number_of_nodes()}  (should be 84)")
print(f"Directed edges: {social_network.number_of_edges()}")

#---------------
#
#  Create contact network from Social Evolution proximity data
#  - Stochastic: each measurement is an independent Bernoulli trial with p = prob2
#  - Per bin: edge exists if at least one trial succeeds for the pair (simple graph)
#  - Unified: per-bin binary indicators + count of realized contact bins
#
#---------------

contact_file = "capstone_proj_data/Proximity.csv"

# === 1. Load CSV ===
df = pd.read_csv(contact_file)

# === 2. Preprocess ===
df['time'] = pd.to_datetime(df['time'], errors='coerce')
df['prob2'] = pd.to_numeric(df['prob2'], errors='coerce')

# Keep rows with valid time and prob2 (including 0 for completeness)
df = df.dropna(subset=['time'])
df = df[df['prob2'].notna()].copy()

# Create undirected edge keys (symmetric)
df['u'] = df[['user.id', 'remote.user.id.if.known']].min(axis=1).astype(int)
df['v'] = df[['user.id', 'remote.user.id.if.known']].max(axis=1).astype(int)

# Bin into periods (floor to start of bin)
df['bin_start'] = df['time'].dt.floor('30D')

# Get sorted unique bins and assign 0-based index
unique_bins = sorted(df['bin_start'].unique())
bin_to_idx = {date: i for i, date in enumerate(unique_bins)}

print(f"Found {len(unique_bins)} distinct bins.")

# === 3. Build list of separate per-bin networks (stochastic, simple graphs) ===
per_bin_networks = []

for bin_date, group in df.groupby('bin_start', sort=True):
    if group.empty:
        continue
    
    G = nx.Graph()
    # Convert datetimes to strings to avoid GML write error
    G.graph['bin_start']    = bin_date.strftime('%Y-%m-%d')
    G.graph['bin_end']      = (bin_date + timedelta(days=29)).strftime('%Y-%m-%d')
    G.graph['bin_index']    = bin_to_idx[bin_date]
    G.graph['description']  = f"{bin_date.date()} – {(bin_date + timedelta(days=29)).date()}"
    
    # === ENSURE ALL NODES 1–84 ARE PRESENT ===
    G.add_nodes_from(ALL_NODES)
    
    # For each measurement: simulate Bernoulli trial
    group = group.copy()
    group['realized'] = np.random.random(len(group)) < group['prob2']
    
    # Keep only rows where contact was realized
    realized = group[group['realized']]
    
    if not realized.empty:
        # Take unique undirected pairs (at least one realization → edge exists)
        unique_pairs = realized[['u', 'v']].drop_duplicates()
        
        for _, row in unique_pairs.iterrows():
            G.add_edge(int(row['u']), int(row['v']))  # unweighted
    
    per_bin_networks.append(G)
    
    # Report
    if G.number_of_edges() > 0:
        print(f"Bin {G.graph['description']:<24} | "
              f"Nodes: {G.number_of_nodes():4d} | "
              f"Edges: {G.number_of_edges():4d}")
    else:
        print(f"Bin {G.graph['description']:<24} | empty (no contacts realized) — still has 84 nodes")

# Summary
print(f"\nCreated {len(per_bin_networks)} separate contact networks (stochastic realizations).")
if per_bin_networks:
    print(f"From: {min(g.graph['bin_start'] for g in per_bin_networks)}")
    print(f"  To: {max(g.graph['bin_end']   for g in per_bin_networks)}")

# === 4. Build SINGLE unified contact network with per-bin binary indicators ===
G_unified = nx.Graph()
G_unified.graph['name'] = "Unified Contact Network – stochastic realization per bin"
G_unified.graph['num_bins'] = len(unique_bins)
G_unified.graph['bin_starts'] = [d.date().isoformat() for d in unique_bins]

# === ENSURE ALL NODES 1–84 ARE PRESENT ===
G_unified.add_nodes_from(ALL_NODES)

# Simulate per bin and store binary indicators
bin_realized_pairs = {}

for bin_date, group in df.groupby('bin_start', sort=True):
    bin_idx = bin_to_idx[bin_date]
    attr_name = f"contact_bin_{bin_idx}"   # renamed for clarity: 0/1 realized
    
    # Simulate Bernoulli trials
    group = group.copy()
    group['realized'] = np.random.random(len(group)) < group['prob2']
    
    # Unique pairs that had at least one realization in this bin
    realized = group[group['realized']]
    if not realized.empty:
        unique_pairs = realized[['u', 'v']].drop_duplicates()
        bin_realized_pairs[bin_idx] = set(tuple(sorted([r['u'], r['v']])) for _, r in unique_pairs.iterrows())
        
        for _, row in unique_pairs.iterrows():
            u, v = int(row['u']), int(row['v'])
            G_unified.add_edge(u, v, **{attr_name: 1})
    else:
        bin_realized_pairs[bin_idx] = set()

# Fill missing bin attributes with 0 for all existing edges
for u, v in G_unified.edges():
    for bin_idx in range(len(unique_bins)):
        attr = f"contact_bin_{bin_idx}"
        G_unified.edges[u, v][attr] = G_unified.edges[u, v].get(attr, 0)

# Count number of bins where contact was realized
for u, v in G_unified.edges():
    total = sum(G_unified.edges[u, v][f"contact_bin_{i}"] for i in range(len(unique_bins)))
    if total > 0:
        G_unified.edges[u, v]['total_realized_contacts'] = total

print(f"\nUnified network (stochastic per-bin realizations):")
print(f"  Nodes: {G_unified.number_of_nodes():4d}  (should be 84)")
print(f"  Edges: {G_unified.number_of_edges():4d}")
print(f"  Bin-specific binary attributes: {len(unique_bins)}")
print(f"  Edges with total_realized_contacts > 0: {sum(1 for d in G_unified.edges.values() if d.get('total_realized_contacts', 0) > 0)}")

if G_unified.number_of_edges() > 0:
    totals = [d['total_realized_contacts'] for d in G_unified.edges.values() if 'total_realized_contacts' in d]
    if totals:
        print(f"  Total realized contacts range: {min(totals)} - {max(totals)}")

# Save networks
nx.write_gml(social_network, "capstone_proj_data/rc_social_network.gml")
print("Saved social network → rc_social_network.gml")

for i, G in enumerate(per_bin_networks):
    fname = f"capstone_proj_data/rc_contact_network_bin{i+1}.gml"
    nx.write_gml(G, fname)
    print(f"Saved {fname}  ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")

nx.write_gml(G_unified, "capstone_proj_data/rc_contact_unified_all_bins.gml")
print(f"Saved unified network → rc_contact_unified_all_bins.gml "
      f"({G_unified.number_of_nodes()} nodes, {G_unified.number_of_edges()} edges)")