import pandas as pd
import networkx as nx
from collections import defaultdict

ALL_NODES = set(range(1, 85))

# ==============================================================================
#  SOCIAL NETWORK
#  - Undirected
#  - Each survey timestamp becomes an edge attribute named by that date string
#    with value = relationship type string (e.g. "2008-09-09": "CloseFriend")
#  - If a pair reports multiple relationship types at the same timestamp,
#    the values are comma-joined (e.g. "CloseFriend,SocializeTwicePerWeek")
#  - No weights, no direction reversal, no binning
# ==============================================================================

social_file = "capstone_proj_data/RelationshipsFromSurveys.csv"
df_social = pd.read_csv(social_file)
df_social['survey.date'] = pd.to_datetime(df_social['survey.date'], errors='coerce')
df_social = df_social.dropna(subset=['survey.date'])

social_network = nx.Graph()
social_network.add_nodes_from(ALL_NODES)

# Collect relations per (u, v, date) triple, then write to graph
edge_ts_relations = defaultdict(lambda: defaultdict(set))
# edge_ts_relations[(u,v)][date_str] = {rel1, rel2, ...}

for _, row in df_social.iterrows():
    a = int(row['id.A'])
    b = int(row['id.B'])
    if a == b:
        continue
    u, v = min(a, b), max(a, b)
    rel = str(row['relationship'])
    date_str = 's_' + row['survey.date'].strftime('%Y%m%d')
    edge_ts_relations[(u, v)][date_str].add(rel)

for (u, v), ts_map in edge_ts_relations.items():
    # Each date becomes an edge attribute: date_str -> "Rel1,Rel2"
    attrs = {date: ",".join(sorted(rels)) for date, rels in ts_map.items()}
    social_network.add_edge(u, v, **attrs)

print(f"Social network — nodes: {social_network.number_of_nodes()}, edges: {social_network.number_of_edges()}")
unique_dates = sorted({d for ts_map in edge_ts_relations.values() for d in ts_map})
print(f"Survey dates found: {unique_dates}")
for u, v, d in sorted(social_network.edges(data=True)):
    print(f"  {u} — {v} : {d}")


# ==============================================================================
#  CONTACT NETWORK
#  - One unified undirected graph
#  - Each raw timestamp becomes a boolean edge attribute
#    (e.g. "2008-09-18 12:00:00": True)
# ==============================================================================

contact_file = "capstone_proj_data/Proximity.csv"
df_contact = pd.read_csv(contact_file)

df_contact['time'] = pd.to_datetime(df_contact['time'], errors='coerce')
df_contact = df_contact.dropna(subset=['time', 'user.id', 'remote.user.id.if.known'])
df_contact['u'] = df_contact[['user.id', 'remote.user.id.if.known']].min(axis=1).astype(int)
df_contact['v'] = df_contact[['user.id', 'remote.user.id.if.known']].max(axis=1).astype(int)

contact_network = nx.Graph()
contact_network.add_nodes_from(ALL_NODES)

for _, row in df_contact.iterrows():
    u, v = int(row['u']), int(row['v'])
    if u == v:
        continue
    ts = 'c_' + row['time'].strftime('%Y%m%d_%H%M%S')
    if not contact_network.has_edge(u, v):
        contact_network.add_edge(u, v)
    contact_network.edges[u, v][ts] = True

print(f"\nContact network — nodes: {contact_network.number_of_nodes()}, edges: {contact_network.number_of_edges()}")
print(f"Unique timestamps recorded as edge attributes: {len(df_contact['time'].unique())}")


# ==============================================================================
#  SAVE
# ==============================================================================

nx.write_gml(social_network,  "capstone_proj_data/rc_social_simple.gml")
nx.write_gml(contact_network, "capstone_proj_data/rc_contact_simple.gml")
print("\nSaved rc_social_simple.gml and rc_contact_simple.gml")