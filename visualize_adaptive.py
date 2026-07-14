import pickle
from collections import Counter

import matplotlib.pyplot as plt
import networkx as nx

# Global matplotlib settings (matches adaptive_seed_selection.py)
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
})

FIGURE_SIZE = (10, 6)

DATA_PATH = "adaptive_seed_data.pkl"
OUT_PATH = "capstone_result_figures/adaptive_freq_vs_degree_coreness.pdf"


def load_data(path=DATA_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)


def selection_frequency(batch_seed_sets):
    """Counts how many (run, batch) selections included each node."""
    counts = Counter()
    for run in batch_seed_sets:
        for batch in run:
            counts.update(batch)
    return counts


def plot_frequency_vs_degree_coreness(path=DATA_PATH, out_path=OUT_PATH):
    data = load_data(path)
    social_network = data["social_network"]
    batch_seed_sets = data["batch_seed_sets"]

    freq = selection_frequency(batch_seed_sets)

    # Degree and coreness are undirected notions; the social network is stored as a DiGraph.
    undirected = social_network.to_undirected()
    degree = dict(undirected.degree())
    coreness = nx.core_number(undirected)

    nodes = list(social_network.nodes())
    frequencies = [freq.get(node, 0) for node in nodes]
    degrees = [degree[node] for node in nodes]
    corenesses = [coreness[node] for node in nodes]

    fig, ax_deg = plt.subplots(figsize=FIGURE_SIZE)
    ax_core = ax_deg.twinx()

    ax_deg.scatter(frequencies, degrees, color="steelblue", alpha=0.7, label="Degree")
    ax_core.scatter(frequencies, corenesses, color="firebrick", marker="^", alpha=0.7, label="Coreness")

    ax_deg.set_xlabel("Selection Frequency (Adaptive Approach)")
    ax_deg.set_ylabel("Degree", color="steelblue")
    ax_core.set_ylabel("Coreness", color="firebrick")
    ax_deg.tick_params(axis="y", labelcolor="steelblue")
    ax_core.tick_params(axis="y", labelcolor="firebrick")

    handles = ax_deg.get_legend_handles_labels()[0] + ax_core.get_legend_handles_labels()[0]
    labels = ax_deg.get_legend_handles_labels()[1] + ax_core.get_legend_handles_labels()[1]
    ax_deg.legend(handles, labels, loc="upper left")

    ax_deg.set_title("Node Selection Frequency vs. Degree and Coreness")
    ax_deg.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    plot_frequency_vs_degree_coreness()
