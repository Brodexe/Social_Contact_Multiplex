import pandas as pd
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def plot_degree_correlation(correlations):
    """
    Plot degree correlation between the social graph and contact graphs.

    Parameters
    ----------
    correlations : list[dict]
        Output of degree_correlation_over_time().
    """
    timestamps = [
        datetime.fromtimestamp(item["start_time"])
        for item in correlations
    ]

    values = [
        item["degree_correlation"]
        for item in correlations
    ]

    plt.figure(figsize=(12, 5))

    plt.plot(
        timestamps,
        values,
        marker="o",
        linewidth=1.5,
        markersize=4,
        color="tab:blue",
        label="Degree correlation"
    )

    plt.axhline(0, color="black", linewidth=0.8, linestyle="--")
    plt.xlabel("Time", fontsize=14)
    plt.ylabel("Pearson degree correlation", fontsize=14)
    plt.title("Social vs. Contact-Network Degree Correlation Over Time", fontsize=15)
    plt.ylim(-1.05, 1.05)
    plt.legend()
    plt.grid(alpha=0.25)

    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()


def degree_correlation_over_time(G, temporal_graphs):
    """
    Compute the Pearson correlation between contact degree and social degree
    at every temporal contact snapshot.

    Parameters
    ----------
    G : nx.Graph
        Static social graph.

    temporal_graphs : list[nx.Graph]
        Contact graphs returned by read_contact().

    Returns
    -------
    results : list[dict]
        One record per temporal graph, containing time and correlation.
        Correlation is np.nan when it cannot be computed, e.g. an empty
        graph or no variation in one of the degree sequences.
    """
    results = []

    for H in temporal_graphs:
        active_nodes = list(H.nodes())

        # Only students appearing in this contact snapshot are considered.
        if len(active_nodes) < 2:
            correlation = np.nan
        else:
            # Contact degree in the current temporal snapshot.
            contact_degrees = np.array(
                [H.degree(node) for node in active_nodes],
                dtype=float
            )

            # Social degree among the same active students only.
            # If an active student is absent from G, its degree is 0.
            active_social_graph = G.subgraph(active_nodes)
            social_degrees = np.array(
                [active_social_graph.degree(node) if node in G else 0
                 for node in active_nodes],
                dtype=float
            )

            # Pearson correlation is undefined if either list is constant.
            if np.std(contact_degrees) == 0 or np.std(social_degrees) == 0:
                correlation = np.nan
            else:
                correlation = np.corrcoef(
                    contact_degrees,
                    social_degrees
                )[0, 1]

        results.append({
            "start_time": H.graph.get("start_time"),
            "end_time": H.graph.get("end_time"),
            "active_nodes": len(active_nodes),
            "degree_correlation": correlation
        })

    return results

def read_social(fname):
    # Read an Excel file with no header:
    # column 0 = node 1, column 1 = node 2, column 2 = w
    df = pd.read_csv(fname, header=None, names=["node1", "node2", "w"], delimiter=' ')

    # Create an undirected NetworkX graph
    G = nx.Graph()

    # Add an edge only for rows where w == 1
    for node1, node2, w in df.itertuples(index=False):
        # print(node1, node2, w)
        if w == 1:
            G.add_edge(node1, node2)

    return G


def read_contact(fname, duration):
    """
    Read a SocioPatterns contact file and return temporal contact graphs.

    Parameters
    ----------
    fname : str
        Path to the tab- or whitespace-separated contact file.
        Expected columns: t, i, j, Ci, Cj

    duration : int
        Length of each temporal aggregation window, in seconds.
        For example, duration=20 returns one graph per original interval;
        duration=300 returns one graph per five-minute window.

    Returns
    -------
    graphs : list[nx.Graph]
        One undirected graph per time window. Each graph has:
          - graph["start_time"]
          - graph["end_time"]
          - node attribute "class"
          - edge attribute "weight": number of 20-second contact records
            between that pair during the window.
    """
    if duration <= 0:
        raise ValueError("duration must be a positive number of seconds.")

    # r"\s+" supports tabs or spaces in the original SocioPatterns file.
    df = pd.read_csv(
        fname,
        sep=r"\s+",
        header=None,
        names=["t", "i", "j", "Ci", "Cj"]
    )

    df = df.sort_values("t").reset_index(drop=True)

    if df.empty:
        return []

    first_time = df["t"].min()
    last_time = df["t"].max()

    # Assign each contact to a window beginning at first_time.
    df["window_start"] = (
        ((df["t"] - first_time) // duration) * duration + first_time
    )

    graphs = []

    # Include windows even if no contacts occur within them.
    for window_start in range(first_time, last_time + 1, duration):
        window_end = window_start + duration
        contacts = df[df["window_start"] == window_start]

        G = nx.Graph()
        G.graph["start_time"] = window_start
        G.graph["end_time"] = window_end

        for row in contacts.itertuples(index=False):
            # Store each student's class as a node attribute.
            G.add_node(row.i, **{"class": row.Ci})
            G.add_node(row.j, **{"class": row.Cj})

            # Each row represents one 20-second contact observation.
            if G.has_edge(row.i, row.j):
                G[row.i][row.j]["weight"] += 1
            else:
                G.add_edge(row.i, row.j, weight=1)

        print(G)
        graphs.append(G)

    return graphs


if __name__ == "__main__":
    temporal_graphs = read_contact("HighSchool2013_proximity_net.csv", duration=3600)
    print([H for H in temporal_graphs])

    G = read_social("HighSchool2013_facebook_known_pairs.csv")
    print(G)

    correlations = degree_correlation_over_time(G, temporal_graphs)
    print(correlations)

    plot_degree_correlation(correlations)