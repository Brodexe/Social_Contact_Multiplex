"""Joint on-disk store for cost curves produced by adaptive_seed_selection.py and milp.py.

Each script computes its own cost curve (a list of per-simulation cost-over-time
lists) -- plus, optionally, the raw per-batch "cost elements" (newly_infected_sum,
total_edge_removal_cost) that global_cost_function returns alongside the weighted
scalar cost -- and calls push_curve() to merge it into a shared pickle file. Since
the scripts are normally run separately, plotting is a manual step: once the curves
you want are present in the store (run any subset of the scripts, in any order),
call plot_joint_cost_comparison() and/or plot_joint_cost_elements() -- or just run
this file directly -- to render the figures with whichever methods have been pushed
so far.

plot_joint_cost_comparison() renders the weighted total cost (unchanged).
plot_joint_cost_elements() is a separate figure: the raw infection-term and
edge-term curves are on a totally different scale than the weighted cost, so they
are not overlaid on the same axes. Each method keeps its own color from
METHOD_STYLE; the infection-term curve uses a lighter shade of that color with
triangle markers, and the edge-term curve uses an even lighter shade with circle
markers.
"""

import os
import pickle

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Global matplotlib settings (matches adaptive_seed_selection.py / milp.py)
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "lines.linewidth": 2.5,
})

FIGURE_SIZE_LINE = (10, 6)

STORE_PATH = "cost_curves_data.pkl"

# Canonical label -> color, and the fixed legend/plot order.
METHOD_STYLE = {
    "Degree-Based": "C1",
    "Random Seeds": "C3",
    "Adaptive":     "C0",
    "MILP":         "C2",
    "MILP-Local":   "C4",
}


def _lighten(color, amount):
    """Blend `color` toward white by `amount` in [0, 1] (0 = original color, 1 = white)."""
    r, g, b = mcolors.to_rgb(color)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def _normalize_entry(value):
    """Normalize a stored value to {'cost': arr, 'infection': arr|None, 'edge': arr|None}.
    Older store entries are a bare cost-curve array rather than a dict; wrap those so
    both formats can be read the same way."""
    if isinstance(value, dict):
        return value
    return {"cost": value, "infection": None, "edge": None}


def load_all(path=STORE_PATH):
    """Return the dict of {label: entry} currently in the shared store."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)


def push_curve(label, cost_curves, infection_curves=None, edge_curves=None, path=STORE_PATH):
    """Merge this method's cost curve -- and, optionally, its raw infection-term /
    edge-term cost-element curves (each a list of per-simulation lists, same shape
    as cost_curves) -- into the shared store."""
    if label not in METHOD_STYLE:
        raise ValueError(f"Unknown method label {label!r}; expected one of {list(METHOD_STYLE)}")

    data = load_all(path)
    entry = {"cost": np.asarray(cost_curves)}
    if infection_curves is not None:
        entry["infection"] = np.asarray(infection_curves)
    if edge_curves is not None:
        entry["edge"] = np.asarray(edge_curves)
    data[label] = entry

    with open(path, "wb") as f:
        pickle.dump(data, f)


def plot_joint_cost_comparison(path=STORE_PATH,
                                save_path="capstone_result_figures/joint_cost_comparison.pdf"):
    """Plot mean +/- std cost-over-time for whichever of the four methods
    (Degree-Based, Random Seeds, Adaptive, MILP) are currently in the shared store."""
    data = load_all(path)
    labels = [l for l in METHOD_STYLE if l in data]
    if not labels:
        print(f"No cost curves found in {path}; run adaptive_seed_selection.py and/or milp.py first.")
        return
    missing = [l for l in METHOD_STYLE if l not in data]
    if missing:
        print(f"Note: no data yet for {missing}; plotting {labels} only.")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    for label in labels:
        arr = _normalize_entry(data[label])["cost"]
        mean = arr.mean(axis=0)
        std = arr.std(axis=0)
        time = np.arange(len(mean))
        color = METHOD_STYLE[label]
        ax.plot(time, mean, label=label, color=color, linewidth=2.6, zorder=3)
        ax.fill_between(time, mean - std, mean + std, color=color, alpha=0.20, zorder=2)

    ax.set_xlabel("Time (in days)")
    ax.set_ylabel("Cost")
    ax.set_title("Cost Comparison of Seed Selection Methods")
    ax.legend(loc="upper center", ncols=len(labels), fontsize=12,
              bbox_to_anchor=(0.5, -0.18), bbox_transform=ax.transAxes)
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    plt.show()


def plot_joint_cost_elements(path=STORE_PATH,
                              save_path="capstone_result_figures/joint_cost_elements_comparison.pdf"):
    """Plot mean infection-term and edge-term curves (the raw, unweighted
    cost_elements from global_cost_function) for whichever methods have pushed
    element data. A separate figure from plot_joint_cost_comparison -- these are
    raw counts, not the weighted total cost, and live on a very different scale.

    Each method keeps its METHOD_STYLE color; infection-term uses a lighter shade
    with triangle markers, edge-term an even lighter shade with circle markers.
    """
    data = load_all(path)
    entries = {label: _normalize_entry(data[label]) for label in METHOD_STYLE if label in data}
    labels = [label for label in METHOD_STYLE
              if label in entries and entries[label].get("infection") is not None
              and entries[label].get("edge") is not None]
    if not labels:
        print(f"No cost-element curves found in {path}; re-run the seed-selection scripts "
              f"(they now push infection/edge element curves alongside cost) first.")
        return
    missing = [l for l in METHOD_STYLE if l not in labels]
    if missing:
        print(f"Note: no element data yet for {missing}; plotting {labels} only.")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    for label in labels:
        entry = entries[label]
        base_color = METHOD_STYLE[label]

        infection_arr = entry["infection"]
        infection_mean = infection_arr.mean(axis=0)
        time = np.arange(len(infection_mean))
        ax.plot(time, infection_mean, label=f"{label} (infection)",
                 color=_lighten(base_color, 0.15), marker="^", markersize=6,
                 markevery=max(1, len(time) // 25), linewidth=2.2, zorder=3)

        edge_arr = entry["edge"]
        edge_mean = edge_arr.mean(axis=0)
        ax.plot(time, edge_mean, label=f"{label} (edge)",
                 color=_lighten(base_color, 0.55), marker="o", markersize=6,
                 markevery=max(1, len(time) // 25), linewidth=2.2, zorder=3)

    ax.set_xlabel("Time (in days)")
    ax.set_ylabel("Cost Element (raw, unweighted)")
    ax.set_title("Cost Element Comparison of Seed Selection Methods")
    ax.legend(loc="upper center", ncols=min(len(labels), 2), fontsize=10,
              bbox_to_anchor=(0.5, -0.22), bbox_transform=ax.transAxes)
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.34)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    plot_joint_cost_comparison()
    plot_joint_cost_elements()
