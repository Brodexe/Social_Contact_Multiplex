"""Joint on-disk store for cost curves produced by adaptive_seed_selection.py and milp.py.

Each script computes its own cost curve (a list of per-simulation cost-over-time
lists) and calls push_curve() to merge it into a shared pickle file. Since the two
scripts are normally run separately, plotting is a manual step: once the curves you
want are present in the store (run either script, in either order), call
plot_joint_cost_comparison() -- or just run this file directly -- to render the
combined figure with whichever of the four methods have been pushed so far.
"""

import os
import pickle

import numpy as np
import matplotlib.pyplot as plt

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
}


def load_all(path=STORE_PATH):
    """Return the dict of {label: cost_curves array} currently in the shared store."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)


def push_curve(label, cost_curves, path=STORE_PATH):
    """Merge this method's cost curves (list of per-simulation cost lists) into the shared store."""
    if label not in METHOD_STYLE:
        raise ValueError(f"Unknown method label {label!r}; expected one of {list(METHOD_STYLE)}")

    data = load_all(path)
    data[label] = np.asarray(cost_curves)

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
        arr = data[label]
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


if __name__ == "__main__":
    plot_joint_cost_comparison()
