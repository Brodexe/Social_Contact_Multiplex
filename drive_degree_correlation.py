"""
drive_degree_correlation.py — Inter-layer degree correlation across contact bins.

Usage
-----
    python drive_degree_correlation.py

For every interval (bin) b, compares the contact layer
capstone_proj_data/rc_contact_network_bin{b}.gml against the single social layer
capstone_proj_data/rc_social_network.gml using Correlate1.degree_correlation_over_time:
the Pearson correlation between each active student's contact degree and their
social degree (social degree counted among that bin's active students only).

- Nodes are matched on their GML "label" (the participant ID), which lines up
  across the rc_* contact/social files.
- "Active" = non-isolated in that bin's contact network (isolated nodes in the
  GML are students with no recorded contact in the interval).
- The social GML is directed; it is treated as undirected here, so a tie in
  either direction counts once toward degree.

Saves capstone_result_figures/degree_correlation_by_bin.pdf.
"""

import os

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

import Correlate1

BINS                = range(1, 20)  # 1 … 19 inclusive
CONTACT_TEMPLATE    = "capstone_proj_data/rc_contact_network_bin{bin}.gml"
SOCIAL_NETWORK_PATH = "capstone_proj_data/rc_social_network.gml"
SAVE_PATH           = "capstone_result_figures/degree_correlation_by_bin.pdf"

plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
})


def load_contact_bins(bins=BINS):
    """Return (bin_numbers, contact_graphs) with isolated nodes removed."""
    found, graphs = [], []
    for b in bins:
        path = CONTACT_TEMPLATE.format(bin=b)
        if not os.path.exists(path):
            print(f"[skip] {path} not found")
            continue
        H = nx.Graph(nx.read_gml(path))
        H.remove_nodes_from([u for u in list(H.nodes()) if H.degree(u) == 0])
        found.append(b)
        graphs.append(H)
    return found, graphs


def plot_correlation_bars(bins, correlations, save_path=SAVE_PATH):
    values = np.array([c["degree_correlation"] for c in correlations], dtype=float)
    x = np.arange(len(bins))

    fig, ax = plt.subplots(figsize=(14, 6.5))
    heights = np.nan_to_num(values, nan=0.0)
    ax.bar(x, heights, width=0.72, color="C0", edgecolor="white", linewidth=2, zorder=3)
    for xi, v in zip(x, values):
        if not np.isfinite(v):
            ax.text(xi, 0.02, "n/a", ha="center", va="bottom", fontsize=11, color="#666666")

    ax.axhline(0, color="black", linewidth=0.8, zorder=4)
    # Active-student count under each bin: tiny bins give unreliable correlations.
    ax.set_xticks(x, [f"{b}\n{c['active_nodes']}" for b, c in zip(bins, correlations)], fontsize=13)
    ax.set_xlabel("Interval (bin) number  /  active students")
    ax.set_ylabel("Pearson degree correlation")
    ax.set_title("Inter-Layer Degree Correlation (Social vs. Contact) by Interval")

    finite = values[np.isfinite(values)]
    lo = min(0.0, finite.min()) if finite.size else -1.0
    hi = max(0.0, finite.max()) if finite.size else 1.0
    pad = 0.1 * max(hi - lo, 0.1)
    ax.set_ylim(lo - pad, hi + pad)
    ax.grid(True, axis="y", linewidth=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    fig.tight_layout()
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


if __name__ == "__main__":
    social = nx.read_gml(SOCIAL_NETWORK_PATH).to_undirected()
    bins, contact_graphs = load_contact_bins()

    correlations = Correlate1.degree_correlation_over_time(social, contact_graphs)

    print(f"{'bin':>4}  {'active':>6}  {'r':>7}")
    for b, c in zip(bins, correlations):
        print(f"{b:>4}  {c['active_nodes']:>6}  {c['degree_correlation']:>7.3f}")

    plot_correlation_bars(bins, correlations)
