"""Joint on-disk store for cost curves produced by adaptive_seed_selection.py and milp.py.

Each script computes its own cost curve (a list of per-simulation cost-over-time
lists) -- plus, optionally, the raw per-batch "cost elements" (newly_infected_sum,
total_edge_removal_cost) and the alpha_w/beta_w that weight them into the returned
scalar cost (alpha_w * newly_infected_sum + beta_w * total_edge_removal_cost) --
and calls push_curve() to merge it into a shared pickle file. Since the scripts are
normally run separately, plotting is a manual step: once the curves you want are
present in the store (run any subset of the scripts, in any order), call
plot_joint_cost_comparison() and/or plot_joint_cost_elements() -- or just run this
file directly -- to render the figures with whichever methods have been pushed so
far.

plot_joint_cost_comparison() renders the weighted total cost (unchanged); it is
already on the theoretical [0, ~2] scale (each term normalized against a baseline
bound), not raw counts.
plot_joint_cost_elements() is a separate figure showing alpha_w * infection-term and
beta_w * edge-term -- i.e. each raw element weighted the same way it contributes to
the total cost above, so both terms sit on that same normalized scale and are
overlaid on one shared axis. Requires alpha/beta curves to have been pushed
alongside the raw infection/edge curves; older entries missing them are skipped.
Each method keeps its own color from METHOD_STYLE; the weighted infection-term
curve uses a lighter shade of that color with triangle markers, and the weighted
edge-term curve uses an even lighter shade with circle markers.
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


def _expand_to_ticks(curves, batch_interval, T):
    """Expand each per-simulation curve from one value per batch to one value per tick,
    repeating each batch's value across the ticks it covers. Batches are
    [i*batch_interval, min((i+1)*batch_interval, T)) -- segments of length
    batch_interval, except a possibly shorter final segment when T isn't a multiple of
    batch_interval -- matching how adaptive_seed_selection.py / milp.py / milp_local.py
    only append a cost value at batch boundaries (and at t_cur == T-1)."""
    expanded = []
    for sim in curves:
        row = []
        for i, value in enumerate(sim):
            start = i * batch_interval
            end = min(start + batch_interval, T)
            row.extend([value] * (end - start))
        expanded.append(row)
    return expanded


def _normalize_entry(value):
    """Normalize a stored value to {'cost': arr, 'infection': arr|None, 'edge': arr|None,
    'alpha': arr|None, 'beta': arr|None}. Older store entries are a bare cost-curve array,
    or a dict missing the alpha/beta weight curves; fill in the missing keys so both
    formats can be read the same way."""
    if isinstance(value, dict):
        entry = dict(value)
        entry.setdefault("infection", None)
        entry.setdefault("edge", None)
        entry.setdefault("alpha", None)
        entry.setdefault("beta", None)
        return entry
    return {"cost": value, "infection": None, "edge": None, "alpha": None, "beta": None}


def load_all(path=STORE_PATH):
    """Return the dict of {label: entry} currently in the shared store."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)


def push_curve(label, cost_curves, infection_curves=None, edge_curves=None,
               alpha_curves=None, beta_curves=None, batch_interval=1, T=None, path=STORE_PATH):
    """Merge this method's cost curve -- and, optionally, its raw infection-term /
    edge-term cost-element curves, plus the alpha_w/beta_w curves that weight them
    into the returned cost (each a list of per-simulation lists, same shape as
    cost_curves) -- into the shared store.

    alpha_curves/beta_curves let plot_joint_cost_elements() show
    alpha_w * infection and beta_w * edge -- the actual weighted contributions,
    on the same [0, ~1]-ish scale as the total cost -- instead of raw counts.

    If the caller only computed one value per batch (cost updated once every
    batch_interval ticks, per adaptive_seed_selection.py / milp.py / milp_local.py),
    pass batch_interval and T so each value is expanded (repeated) to fill the
    T-tick segment it covers -- giving every method a full T-tick curve even when
    they use different batch intervals, so they still overlay on a shared time axis
    in the joint plots. Leave batch_interval=1 if the curves already have one value
    per tick.
    """
    if label not in METHOD_STYLE:
        raise ValueError(f"Unknown method label {label!r}; expected one of {list(METHOD_STYLE)}")

    if batch_interval > 1:
        if T is None:
            raise ValueError("T must be given when batch_interval > 1, to know how many "
                              "ticks to expand each batch's value across.")
        cost_curves = _expand_to_ticks(cost_curves, batch_interval, T)
        if infection_curves is not None:
            infection_curves = _expand_to_ticks(infection_curves, batch_interval, T)
        if edge_curves is not None:
            edge_curves = _expand_to_ticks(edge_curves, batch_interval, T)
        if alpha_curves is not None:
            alpha_curves = _expand_to_ticks(alpha_curves, batch_interval, T)
        if beta_curves is not None:
            beta_curves = _expand_to_ticks(beta_curves, batch_interval, T)

    data = load_all(path)
    entry = {"cost": np.asarray(cost_curves)}
    if infection_curves is not None:
        entry["infection"] = np.asarray(infection_curves)
    if edge_curves is not None:
        entry["edge"] = np.asarray(edge_curves)
    if alpha_curves is not None:
        entry["alpha"] = np.asarray(alpha_curves)
    if beta_curves is not None:
        entry["beta"] = np.asarray(beta_curves)
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
    """Plot mean alpha_w * infection-term and beta_w * edge-term curves, each capped
    at 1 per step -- i.e. each cost_elements term from global_cost_function weighted
    and capped exactly the way it contributes to the returned cost
    (min(alpha_w * newly_infected_sum, 1) + min(beta_w * total_edge_removal_cost, 1))
    -- for whichever methods have pushed both the raw element curves and the
    alpha/beta weight curves. A separate figure from plot_joint_cost_comparison, but
    on the same normalized scale: the two terms plotted here sum (per time step) to
    that figure's total cost.

    Since both terms are now normalized the same way, they share a single axis.
    Each method keeps its METHOD_STYLE color; the weighted infection term uses a
    lighter shade with triangle markers, the weighted edge term an even lighter
    shade with circle markers.
    """
    data = load_all(path)
    entries = {label: _normalize_entry(data[label]) for label in METHOD_STYLE if label in data}
    labels = [label for label in METHOD_STYLE
              if label in entries and entries[label].get("infection") is not None
              and entries[label].get("edge") is not None
              and entries[label].get("alpha") is not None
              and entries[label].get("beta") is not None]
    if not labels:
        print(f"No weighted cost-element curves found in {path}; re-run the seed-selection scripts "
              f"(they now push alpha_w/beta_w curves alongside infection/edge elements) first.")
        return
    missing = [l for l in METHOD_STYLE if l not in labels]
    if missing:
        print(f"Note: no weighted element data yet for {missing} (stale entry missing alpha/beta, "
              f"or not yet run); plotting {labels} only.")

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    lines = []
    for label in labels:
        entry = entries[label]
        base_color = METHOD_STYLE[label]

        # Cap each term at 1 per step, matching global_cost_function's capped terms.
        weighted_infection_mean = np.minimum(entry["alpha"] * entry["infection"], 1.0).mean(axis=0)
        time = np.arange(len(weighted_infection_mean))
        line, = ax.plot(time, weighted_infection_mean, label=f"{label} (infection, weighted)",
                 color=_lighten(base_color, 0.15), marker="^", markersize=6,
                 markevery=max(1, len(time) // 25), linewidth=2.2, zorder=3)
        lines.append(line)

        weighted_edge_mean = np.minimum(entry["beta"] * entry["edge"], 1.0).mean(axis=0)
        line, = ax.plot(time, weighted_edge_mean, label=f"{label} (edge, weighted)",
                 color=_lighten(base_color, 0.55), marker="o", markersize=6,
                 markevery=max(1, len(time) // 25), linewidth=2.2, zorder=3)
        lines.append(line)

    ax.set_xlabel("Time (in days)")
    ax.set_ylabel("Weighted Cost Contribution")
    ax.set_title("Cost Element Comparison of Seed Selection Methods")
    ax.legend(lines, [l.get_label() for l in lines], loc="upper center",
              ncols=min(len(labels), 2), fontsize=10,
              bbox_to_anchor=(0.5, -0.22), bbox_transform=ax.transAxes)
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.34)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    plot_joint_cost_comparison()
    plot_joint_cost_elements()
