import pickle
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import networkx as nx
from scipy.stats import gaussian_kde

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

# Validated categorical triple (blue / orange / aqua) -- the first three slots of
# the standard categorical order, the only run of it that clears all-pairs CVD/
# normal-vision separation for scatter/small-multiples charts (see dataviz skill).
METRIC_COLORS = {
    "degree": "#2a78d6",
    "coreness": "#eb6834",
    "betweenness": "#1baf7a",
}

# Primary ink: reads as a consistent "distribution overlay" against any of the three
# bar colors above, so it stays fixed across panels rather than picked per-metric.
DISTRIBUTION_CURVE_COLOR = "#0b0b0b"

DATA_PATH = "adaptive_seed_data.pkl"
SELECTED_COUNTS_OUT_PATH = "capstone_result_figures/adaptive_selected_seed_counts_by_metric_bin.pdf"

# Real-world sweep (dual_optimization_driver.py --methods adaptive) output and its
# per-network-bin figures. Distinct naming from SELECTED_COUNTS_OUT_PATH's "bin" --
# that one means degree/coreness/betweenness histogram bins (num_bins); this one
# means which rc_weighted_contact_bin{i}.gml network the figure came from.
REAL_WORLD_DATA_PATH = "adaptive_real_world.pkl"
REAL_WORLD_OUT_TEMPLATE = "capstone_result_figures/adaptive_selected_seed_counts_real_world_bin{i}.pdf"
REAL_WORLD_HEATMAP_OUT_PATH = "capstone_result_figures/adaptive_selected_seed_metric_heatmaps.pdf"


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


def _node_metrics_and_selection(social_network, batch_seed_sets):
    """Returns (selected_mask, {"Degree": values, "Coreness": values, "Betweenness":
    values}) for every node in social_network, aligned to the same node order, where
    selected_mask marks nodes chosen as a seed at least once across batch_seed_sets."""
    freq = selection_frequency(batch_seed_sets)

    undirected = social_network.to_undirected()
    degree = dict(undirected.degree())
    coreness = nx.core_number(undirected)
    betweenness = nx.betweenness_centrality(undirected)

    nodes = list(social_network.nodes())
    selected = np.array([freq.get(node, 0) > 0 for node in nodes])
    values_by_metric = {
        "Degree": np.array([degree[node] for node in nodes], dtype=float),
        "Coreness": np.array([coreness[node] for node in nodes], dtype=float),
        "Betweenness": np.array([betweenness[node] for node in nodes], dtype=float),
    }
    return selected, values_by_metric


def _plot_selected_seed_counts(social_network, batch_seed_sets, out_path, num_bins=10,
                                show=True, title_suffix=""):
    """Groups nodes by their own raw degree/coreness/betweenness value, and for each
    group counts how many *selected* seeds (freq > 0) fall in it. Each metric has a
    different raw scale, so each gets its own subplot with its own group edges."""
    selected, values_by_metric = _node_metrics_and_selection(social_network, batch_seed_sets)
    degrees = values_by_metric["Degree"]
    corenesses = values_by_metric["Coreness"]
    betweennesses = values_by_metric["Betweenness"]

    def counts_per_bin(values):
        bin_edges = np.linspace(values.min(), values.max(), num_bins + 1)
        bin_idx = np.clip(np.digitize(values[selected], bin_edges[1:-1]), 0, num_bins - 1)
        counts = np.zeros(num_bins, dtype=int)
        for b in bin_idx:
            counts[b] += 1
        return counts, bin_edges

    metrics = [
        ("Degree", degrees, *counts_per_bin(degrees), METRIC_COLORS["degree"]),
        ("Coreness", corenesses, *counts_per_bin(corenesses), METRIC_COLORS["coreness"]),
        ("Betweenness", betweennesses, *counts_per_bin(betweennesses), METRIC_COLORS["betweenness"]),
    ]

    bin_centers = np.arange(num_bins)
    bar_handle = curve_handle = None

    fig, axes = plt.subplots(1, 3, figsize=(FIGURE_SIZE[0] * 2.4, FIGURE_SIZE[1]),
                              gridspec_kw={"wspace": 0.45})
    for ax, (label, raw_values, counts, edges, color) in zip(axes, metrics):
        bar_handle = ax.bar(bin_centers, counts, color=color, alpha=0.8, label="Selected Seeds")
        ax.set_xticks(bin_centers)
        fmt = "{:.0f}-{:.0f}" if label != "Betweenness" else "{:.4f}-{:.4f}"
        ax.set_xticklabels([fmt.format(edges[b], edges[b + 1]) for b in range(num_bins)],
                            rotation=45, ha="right")
        ax.set_xlabel(label)
        ax.set_ylabel("Number of Selected Seeds")
        ax.set_title(f"By {label}")
        ax.grid(True, linewidth=0.4, axis="y")

        # Network-wide distribution of this metric, as a smooth density curve (KDE,
        # not a re-binned histogram) sharing the panel's x-axis but its own density
        # y-axis. Drawn translucent and behind the bars -- it's context, not the focus.
        # Skipped when raw_values has zero spread (e.g. every node has the same
        # betweenness in a small/sparse real-world bin) -- gaussian_kde can't fit a
        # density to a degenerate, constant distribution.
        ax_density = ax.twinx()
        if np.ptp(raw_values) > 0:
            kde = gaussian_kde(raw_values)
            grid = np.linspace(edges[0], edges[-1], 200)
            density = kde(grid)
            # Map the raw-value grid onto the same bin_centers coordinate space the bars
            # sit in: bin edges are equal-width in value space (np.linspace), so this is
            # a straight linear remap of [edges[0], edges[-1]] -> [-0.5, num_bins - 0.5].
            x_curve = (grid - edges[0]) / (edges[-1] - edges[0]) * num_bins - 0.5

            curve_handle = ax_density.plot(x_curve, density, color=DISTRIBUTION_CURVE_COLOR,
                                            linewidth=2, alpha=0.55, label="Network Distribution")[0]
            ax_density.fill_between(x_curve, density, color=DISTRIBUTION_CURVE_COLOR, alpha=0.12)
        ax_density.set_ylim(bottom=0)
        ax_density.set_yticks([])
        ax_density.set_ylabel("")

        # Bars stay visually on top of the (background) density curve.
        ax.set_zorder(ax_density.get_zorder() + 1)
        ax.patch.set_visible(False)

    fig.suptitle(f"Selected Seed Counts by Degree, Coreness, and Betweenness{title_suffix}", y=0.99)
    legend_handles = [h for h in (bar_handle, curve_handle) if h is not None]
    fig.legend(handles=legend_handles, loc="upper center",
               ncols=len(legend_handles), bbox_to_anchor=(0.5, 0.91), fontsize=14)
    # subplots_adjust (not tight_layout, which mishandles the twinx density axes)
    # reserves headroom above the axes for the suptitle + legend and widens the
    # gaps between panels so each y-axis label clears its neighbor.
    fig.subplots_adjust(top=0.78, bottom=0.28, left=0.06, right=0.98, wspace=0.45)
    fig.savefig(out_path, format="pdf", bbox_inches="tight", pad_inches=0.1)
    if show:
        plt.show()
    plt.close(fig)


def plot_selected_seed_counts_by_metric_bin(path=DATA_PATH, out_path=SELECTED_COUNTS_OUT_PATH, num_bins=10):
    data = load_data(path)
    _plot_selected_seed_counts(data["social_network"], data["batch_seed_sets"], out_path,
                                num_bins=num_bins, show=True)


def plot_selected_seed_counts_for_real_world_bins(path=REAL_WORLD_DATA_PATH,
                                                    out_template=REAL_WORLD_OUT_TEMPLATE, num_bins=10):
    """Load adaptive_real_world.pkl (dual_optimization_driver.py's Adaptive-only sweep
    across the rc_weighted_contact_bin{i}.gml real-world networks) and render the same
    selected-seed-counts figure as plot_selected_seed_counts_by_metric_bin, once per
    network bin, saving each to disk without displaying it."""
    data = load_data(path)
    # Display numbering starts at 1 regardless of the underlying dict keys (which
    # trace back to the specific rc_weighted_contact_bin{i}.gml file) -- only the
    # title shown in the plot is renumbered; out_path still uses the real bin_index
    # so filenames stay traceable to their source network file.
    for display_index, bin_index in enumerate(sorted(data["results"].keys()), start=1):
        bin_data = data["results"][bin_index]
        out_path = out_template.format(i=bin_index)
        print(f"Plotting real-world bin {bin_index} -> {out_path}")
        _plot_selected_seed_counts(bin_data["social_network"], bin_data["batch_seed_sets"], out_path,
                                    num_bins=num_bins, show=False,
                                    title_suffix=f" (Network Bin {display_index})")


def plot_selected_seed_metric_heatmaps(path=REAL_WORLD_DATA_PATH, out_path=REAL_WORLD_HEATMAP_OUT_PATH,
                                        num_bins=10, show=True):
    """Condense the per-network-bin selected-seed distributions (one bar-chart panel
    per bin -- see plot_selected_seed_counts_for_real_world_bins) into a single trend
    view: one heatmap per metric (degree/coreness/betweenness), x-axis = network bin
    (1..19), y-axis = metric-value bin, color = fraction of that bin's selected seeds
    falling in each metric bin. Bin edges are shared across all network bins (computed
    from the pooled metric values across every bin's social network), so the y-axis
    means the same thing in every column and a shift across bins reads as a diagonal
    or banding trend rather than noise from re-binning each column independently.

    Columns are normalized to sum to 1 (a fraction, not a raw count) so bins with
    different node/seed counts remain visually comparable.
    """
    data = load_data(path)
    bin_indices = sorted(data["results"].keys())

    # Compute each bin's raw metric values + selected mask once, up front, so global
    # (pooled) bin edges can be derived per metric before any heatmap column is filled.
    per_bin = {}
    for bin_index in bin_indices:
        bin_data = data["results"][bin_index]
        selected, values_by_metric = _node_metrics_and_selection(
            bin_data["social_network"], bin_data["batch_seed_sets"])
        per_bin[bin_index] = (selected, values_by_metric)

    metrics = [("Degree", METRIC_COLORS["degree"]),
               ("Coreness", METRIC_COLORS["coreness"]),
               ("Betweenness", METRIC_COLORS["betweenness"])]

    fig, axes = plt.subplots(1, 3, figsize=(FIGURE_SIZE[0] * 2.6, FIGURE_SIZE[1] * 1.4),
                              gridspec_kw={"wspace": 0.9})
    for ax, (metric_name, color) in zip(axes, metrics):
        pooled = np.concatenate([values_by_metric[metric_name] for _, values_by_metric in per_bin.values()])
        edges = np.linspace(pooled.min(), pooled.max(), num_bins + 1)

        grid = np.zeros((num_bins, len(bin_indices)))
        for col, bin_index in enumerate(bin_indices):
            selected, values_by_metric = per_bin[bin_index]
            sel_values = values_by_metric[metric_name][selected]
            if len(sel_values) == 0:
                continue
            bin_idx = np.clip(np.digitize(sel_values, edges[1:-1]), 0, num_bins - 1)
            counts = np.zeros(num_bins)
            for b in bin_idx:
                counts[b] += 1
            grid[:, col] = counts / counts.sum()

        # Sequential = one hue, light -> dark (see dataviz skill), anchored to this
        # metric's existing brand color so it reads as the same series as the
        # per-bin bar charts above rather than an unrelated colormap.
        cmap = mcolors.LinearSegmentedColormap.from_list(f"{metric_name}_seq", ["#ffffff", color])

        im = ax.imshow(grid, aspect="auto", origin="lower", cmap=cmap, vmin=0)
        ax.set_xticks(np.arange(len(bin_indices)))
        ax.set_xticklabels(np.arange(1, len(bin_indices) + 1))
        ax.set_yticks(np.arange(num_bins))
        # Scientific notation (not "{:.4f}") for Betweenness -- its raw values are
        # small enough that 4 decimal places either collide/truncate or all render
        # as the same rounded string, and the longer strings are what crammed into
        # each other against the neighboring panel's colorbar/labels.
        fmt = "{:.0f}-{:.0f}" if metric_name != "Betweenness" else "{:.1e}-{:.1e}"
        ax.set_yticklabels([fmt.format(edges[b], edges[b + 1]) for b in range(num_bins)],
                            fontsize=12)
        ax.set_xlabel("Network Bin")
        ax.set_ylabel(metric_name, labelpad=10)
        ax.set_title(f"By {metric_name}", pad=10)
        fig.colorbar(im, ax=ax, label="Fraction of Selected Seeds", shrink=0.85, pad=0.04)

    fig.suptitle("Selected Seed Distribution Trends Across Real-World Network Bins", y=0.99)
    fig.subplots_adjust(top=0.86, bottom=0.15, left=0.05, right=0.98, wspace=0.9)
    fig.savefig(out_path, format="pdf", bbox_inches="tight", pad_inches=0.1)
    print(f"Saved trend heatmap figure to {out_path}")
    if show:
        plt.show()
    plt.close(fig)


# Which figure set running this file produces. Change SELECTED_MODE to switch:
# 0 -> single_config (adaptive_seed_data.pkl), 1 -> real_world (adaptive_real_world.pkl).
PLOT_MODES = ("single_config", "real_world")
SELECTED_MODE = 1

if __name__ == "__main__":
    mode = PLOT_MODES[SELECTED_MODE]
    if mode == "single_config":
        plot_selected_seed_counts_by_metric_bin()
    elif mode == "real_world":
        plot_selected_seed_counts_for_real_world_bins()
        plot_selected_seed_metric_heatmaps()
