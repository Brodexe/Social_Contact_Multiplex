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

# STORE_PATH = "AdaptSelect_coreness_scale_experiment_scale1.0.pkl"
STORE_PATH = "cost_curves_data.pkl"

# Canonical label -> color, and the fixed legend/plot order.
METHOD_STYLE = {
    "Degree-Based": "C1",
    "Core over Btw": "C5",
    "Core over Deg": "C6",
    "Core Alone":   "C7",
    "Random Seeds": "C3",
    "Social Rule-Based": "C8",
    "Adaptive":     "C0",
    "MILP":         "C2",
    "MILP-Local":   "C4",
}


# ── experiment stores (drive_seed_selection.py robustness / correlation) ─────
# Experiment curves are keyed by configuration rather than by method alone:
#   robustness:  {label: {(cascade_time, seed_fraction): cost_array}}
#   correlation: {label: {(social_group, contact_group): cost_array}}  (Random Seeds: {"all": cost_array})
# plus a reserved "_meta" entry for side information (e.g. measured correlations).
ROBUSTNESS_STORE_PATH  = "robustness_experiment.pkl"
CORRELATION_STORE_PATH = "correlation_ablation.pkl"
META_KEY = "_meta"
RANDOM_ALL_KEY = "all"  # Random Seeds' single, configuration-independent curve

# User-facing method names for the experiments -> canonical METHOD_STYLE labels.
METHOD_ALIASES = {
    "hill-climb": "Adaptive",
    "milp":       "MILP",
    "random":     "Random Seeds",
}
EXPERIMENT_METHODS = tuple(METHOD_ALIASES)  # ("hill-climb", "milp", "random")


def resolve_methods(methods):
    """Map any mix of aliases ("hill-climb", "milp", "random") or canonical labels
    ("Adaptive", "MILP", "Random Seeds") to canonical labels, in METHOD_STYLE order."""
    labels = set()
    for m in methods:
        label = METHOD_ALIASES.get(str(m).lower(), m)
        if label not in METHOD_STYLE:
            raise ValueError(f"Unknown method {m!r}; choose from {list(METHOD_ALIASES)}")
        labels.add(label)
    return [l for l in METHOD_STYLE if l in labels]


def push_experiment_curve(label, key, cost_curves, batch_interval=1, T=None, path=ROBUSTNESS_STORE_PATH):
    """Store one method's cost curves for one experiment configuration `key`.
    Per-batch curves are expanded to per-tick (see push_curve) so configurations
    with different batch intervals share a T-tick time axis."""
    if label not in METHOD_STYLE:
        raise ValueError(f"Unknown method label {label!r}; expected one of {list(METHOD_STYLE)}")
    if batch_interval > 1:
        if T is None:
            raise ValueError("T must be given when batch_interval > 1.")
        cost_curves = _expand_to_ticks(cost_curves, batch_interval, T)
    data = load_all(path)
    data.setdefault(label, {})[key] = np.asarray(cost_curves, dtype=float)
    with open(path, "wb") as f:
        pickle.dump(data, f)


def clear_experiment_label(label, path):
    """Remove every stored configuration for one method label (no-op if absent)."""
    data = load_all(path)
    if data.pop(label, None) is not None:
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[store] cleared previous {label} results from {path}")


def clear_labels(labels, path=STORE_PATH):
    """Remove the given method labels from the joint store (absent labels are ignored),
    so a re-run leaves no stale curves from methods it no longer produces."""
    data = load_all(path)
    removed = [l for l in labels if data.pop(l, None) is not None]
    if removed:
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[store] cleared previous {removed} results from {path}")


def push_experiment_meta(name, value, path):
    """Store side information (e.g. measured correlations) alongside experiment curves."""
    data = load_all(path)
    data.setdefault(META_KEY, {})[name] = value
    with open(path, "wb") as f:
        pickle.dump(data, f)


def _lookup(table, key):
    """dict lookup for numeric keys that tolerates float rounding (0.5 vs 0.50000001)."""
    if key in table:
        return table[key]
    return next((v for k, v in table.items()
                 if isinstance(k, (int, float)) and np.isclose(k, key)), None)


def _total_cost(arr, aggregate):
    """Per-simulation total cost over time -> (mean, std) across simulations.
    aggregate="sum": cost summed over every tick; "mean": time-averaged cost."""
    per_sim = arr.sum(axis=1) if aggregate == "sum" else arr.mean(axis=1)
    return float(per_sim.mean()), float(per_sim.std())


def _cascade_label(cascade):
    return "None" if cascade is None else str(cascade)


ROBUSTNESS_BASELINE = "Random Seeds"


def plot_robustness_heatmaps(methods=("hill-climb", "milp"), path=ROBUSTNESS_STORE_PATH,
                             cascade_times=(None, 5, 10, 15),
                             seed_fractions=tuple(round(0.1 * i, 2) for i in range(1, 11)),
                             contact_bins=tuple(range(9, 19)),
                             show_avg=True,
                             aggregate="sum",
                             save_path="capstone_result_figures/robustness_heatmaps.pdf"):
    """Experiment 1: one heatmap per method under consideration (hill-climb and/or
    MILP, whichever are in the store), cascade time (batch interval) on y,
    seed-set size on x. For each contact network (rc_contact_network_bin{b}) the
    value is the % improvement over Random Seeds on that same network at the same
    (cascade time, seed size): 100 * (random_cost - method_cost) / random_cost,
    using mean total cost over time. Positive = cheaper than random. Random itself
    is the baseline and gets no panel. Panels share one color scale centered at 0.

    show_avg=True:  each cell is one color, the mean improvement over contact_bins
                    (networks missing either side are left out of the mean).
    show_avg=False: each cell is split into len(contact_bins) vertical slices, one
                    per network in contact_bins order (left to right); faint lines
                    separate slices, bold lines separate (cascade, seed size) cells."""
    data = load_all(path)
    labels = [l for l in resolve_methods(methods) if l != ROBUSTNESS_BASELINE]
    present = [l for l in labels if l in data]
    for l in labels:
        if l not in data:
            print(f"Note: no robustness data for {l} in {path}; skipping it.")
    if not present:
        print(f"No hill-climb / MILP robustness data found in {path}; "
              "run `python drive_seed_selection.py robustness hill-climb` (or milp) first.")
        return
    if ROBUSTNESS_BASELINE not in data:
        print(f"No {ROBUSTNESS_BASELINE} data in {path}; run "
              "`python drive_seed_selection.py robustness random` first -- it is the baseline.")
        return

    contact_bins = list(contact_bins)
    n_casc, n_frac, n_bins = len(cascade_times), len(seed_fractions), len(contact_bins)

    def cost_grid(label):
        """(cascade, seed size, contact bin) -> mean total cost; NaN where missing.
        Keys are (cascade, frac, bin); older 2-tuple keys (single network) are ignored."""
        grid = np.full((n_casc, n_frac, n_bins), np.nan)
        for k, v in data[label].items():
            if not (isinstance(k, tuple) and len(k) == 3) or k[2] not in contact_bins:
                continue
            r = next((i for i, t in enumerate(cascade_times) if t == k[0]), None)
            c = next((i for i, f in enumerate(seed_fractions) if np.isclose(f, k[1])), None)
            if r is not None and c is not None:
                grid[r, c, contact_bins.index(k[2])] = _total_cost(v, aggregate)[0]
        return grid

    baseline = cost_grid(ROBUSTNESS_BASELINE)
    with np.errstate(divide="ignore", invalid="ignore"):
        # Per-network improvement: each method vs random on the same network.
        per_bin = {label: 100.0 * (baseline - cost_grid(label)) / baseline for label in present}
    for g in per_bin.values():
        g[~np.isfinite(g)] = np.nan   # missing cell on either side, or random cost of 0

    if show_avg:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)   # all-NaN cells -> NaN
            grids = {label: np.nanmean(g, axis=2) for label, g in per_bin.items()}
        counts = {label: np.isfinite(g).sum(axis=2) for label, g in per_bin.items()}
    else:
        # Flatten (seed size, bin) into columns: cell c spans columns c*n_bins ... (c+1)*n_bins-1.
        grids = {label: g.reshape(n_casc, n_frac * n_bins) for label, g in per_bin.items()}

    finite = np.concatenate([g[np.isfinite(g)] for g in grids.values()])
    if finite.size == 0:
        print("No cells have both a method result and a random baseline for the "
              "requested cascade times / seed sizes / contact networks.")
        return
    # Diverging scale centered on 0 (= same as random): blue better, red worse.
    lim = max(np.abs(finite).max(), 1e-9)
    cmap = plt.get_cmap("RdBu").copy()
    cmap.set_bad("#e6e6e6")
    norm = mcolors.Normalize(vmin=-lim, vmax=lim)

    # Panel width grows with the number of seed-size columns so annotations / slices stay legible.
    panel_w = max(6.2, (0.85 if show_avg else 1.4) * n_frac + 1.5)
    cell_fs = 13 if n_frac <= 5 else 10
    fig, axes = plt.subplots(1, len(present), figsize=(panel_w * len(present) + 1.2, 6.2),
                             squeeze=False, constrained_layout=True)
    axes = axes[0]
    for ax, label in zip(axes, present):
        grid = grids[label]
        # extent keeps cell (r, c) centered at (c, r) in both modes, so ticks/lines line up.
        im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, norm=norm, aspect="auto",
                       interpolation="nearest",
                       extent=(-0.5, n_frac - 0.5, n_casc - 0.5, -0.5))
        if show_avg:
            for r in range(n_casc):
                for c in range(n_frac):
                    val = grid[r, c]
                    if np.isfinite(val):
                        # Dark ink near the pale center, white ink on saturated ends.
                        ink = "white" if abs(norm(val) - 0.5) > 0.3 else "#1a1a1a"
                        ax.text(c, r, f"{val:+.1f}%",
                                ha="center", va="center", fontsize=cell_fs, color=ink)
                        if counts[label][r, c] < n_bins:   # flag means over fewer networks
                            ax.text(c + 0.45, r + 0.45, f"n={counts[label][r, c]}",
                                    ha="right", va="bottom", fontsize=7, color=ink)
                    else:
                        ax.text(c, r, "n/a", ha="center", va="center", fontsize=cell_fs - 1, color="#666666")
        else:
            # Faint per-network slice separators inside each cell.
            slice_x = [c - 0.5 + k / n_bins for c in range(n_frac) for k in range(1, n_bins)]
            ax.vlines(slice_x, -0.5, n_casc - 0.5, colors="white", linewidth=0.5, alpha=0.55, zorder=2)

        ax.set_xticks(range(n_frac), [f"{int(round(f * 100))}%" for f in seed_fractions])
        ax.set_yticks(range(n_casc), [_cascade_label(t) for t in cascade_times])
        if show_avg:
            ax.set_xlabel("Seed set size (% of nodes)")
        else:
            ax.set_xlabel(f"Seed set size (% of nodes)\nslices in each cell: contact bin "
                          f"{contact_bins[0]} → {contact_bins[-1]} (left to right)")
        ax.set_ylabel("Cascade time (steps)")
        title = "Hill Climb" if label == "Adaptive" else label
        ax.set_title(title, fontsize=18)
        # Bold (cascade time x seed size) cell separators, drawn above the faint slice lines.
        ax.set_xticks(np.arange(-0.5, n_frac, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n_casc, 1), minor=True)
        if show_avg:
            ax.grid(which="minor", color="white", linewidth=2)
        else:
            ax.grid(which="minor", color="#1a1a1a", linewidth=2.2, zorder=3)
            ax.set_axisbelow(False)
        ax.tick_params(which="minor", length=0)
        for spine in ax.spines.values():
            spine.set_visible(not show_avg)
            spine.set_color("#1a1a1a")
            spine.set_linewidth(2.2)

    cb = fig.colorbar(im, ax=list(axes), fraction=0.046, pad=0.02)
    cb.set_label("% improvement over random\n(" +
                 ("total cost over time" if aggregate == "sum" else "time-averaged cost") +
                 (f",\nmean over {n_bins} contact networks" if show_avg else ",\nper contact network") + ")")
    fig.suptitle("Improvement over Random Seeds by Cascade Time,\nSeed Set Size and Contact Network",
                 fontsize=20)
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


CORRELATION_CONDITIONS = (("high", "high"), ("high", "low"), ("low", "high"), ("low", "low"))


def _condition_label(cond, sep=" / "):
    social, contact = cond
    return f"{social.capitalize()} social{sep}{contact.capitalize()} contact"


def plot_correlation_ablation(methods=("hill-climb", "random"), path=CORRELATION_STORE_PATH,
                              conditions=CORRELATION_CONDITIONS, aggregate="sum",
                              save_path="capstone_result_figures/correlation_ablation.pdf"):
    """Experiment 3: effect of inter-layer degree alignment on cost, for any
    subset of "hill-climb", "milp", "random". Each condition is a
    (social group, contact group) cell of the high/low x high/low matrix
    (Correlate3.partial_rank_mapping): high/low-degree social nodes placed on
    high/low-degree contact nodes, everything else random.

    Left:  mean cost over time -- one curve per condition for each adaptive
           method (shades of the method's color, in `conditions` order), and a
           single dashed curve for Random Seeds, whose seed choices don't depend
           on the social layer's placement.
    Right: total cost per condition (mean +/- std across simulations), with
           Random Seeds as a horizontal reference line.
    X tick labels carry the measured Pearson degree correlation when stored."""
    conditions = [tuple(c) for c in conditions]
    data = load_all(path)
    labels = resolve_methods(methods)
    present = [l for l in labels if l in data]
    for l in labels:
        if l not in data:
            print(f"Note: no correlation-ablation data for {l} in {path}; skipping it.")
    if not present:
        print(f"No correlation-ablation data in {path}; run `python drive_seed_selection.py correlation` first.")
        return
    measured = data.get(META_KEY, {}).get("measured_correlation", {})

    fig, (ax_t, ax_c) = plt.subplots(1, 2, figsize=(20, 7.5), constrained_layout=True)

    # Small horizontal offsets so error bars of different methods don't overlap.
    adaptive = [l for l in present if l != "Random Seeds"]
    offsets = {l: (k - (len(adaptive) - 1) / 2) * 0.12 for k, l in enumerate(adaptive)}

    for label in present:
        base = METHOD_STYLE[label]
        name = "Hill Climb" if label == "Adaptive" else label
        if label == "Random Seeds":
            arr = data[label].get(RANDOM_ALL_KEY)
            if arr is None:
                continue
            mean = arr.mean(axis=0)
            ax_t.plot(np.arange(len(mean)), mean, color=base, linestyle="--", linewidth=2.2,
                      label=f"{name} (any condition)", zorder=4)
            tot_mean, tot_std = _total_cost(arr, aggregate)
            ax_c.axhline(tot_mean, color=base, linestyle="--", linewidth=2.2, label=name, zorder=2)
            ax_c.axhspan(tot_mean - tot_std, tot_mean + tot_std, color=base, alpha=0.10, zorder=1)
            continue

        xs, ys, es = [], [], []
        for i, cond in enumerate(conditions):
            arr = data[label].get(cond)
            if arr is None:
                continue
            shade = _lighten(base, 0.70 * (1 - i / max(1, len(conditions) - 1)))
            mean = arr.mean(axis=0)
            ax_t.plot(np.arange(len(mean)), mean, color=shade, linewidth=2.0,
                      label=f"{name}, {_condition_label(cond)}", zorder=3)
            tot_mean, tot_std = _total_cost(arr, aggregate)
            xs.append(i + offsets[label]); ys.append(tot_mean); es.append(tot_std)
        if xs:
            ax_c.errorbar(xs, ys, yerr=es, color=base, marker="o", markersize=9, linestyle="none",
                          elinewidth=2.2, capsize=5, label=name, zorder=3)

    ax_t.set_xlabel("Time (in days)")
    ax_t.set_ylabel("Cost")
    ax_t.set_title("Cost over Time by Degree Alignment")
    ax_t.grid(True, linewidth=0.4)
    ax_t.legend(fontsize=11, ncols=2, loc="upper center", bbox_to_anchor=(0.5, -0.14))

    tick_labels = []
    for cond in conditions:
        r = measured.get(cond) if measured else None
        text = _condition_label(cond, sep="\n")
        tick_labels.append(text if r is None or not np.isfinite(r) else f"{text}\n(r = {r:.2f})")
    ax_c.set_xticks(range(len(conditions)), tick_labels)
    ax_c.set_xlim(-0.5, len(conditions) - 0.5)
    ax_c.set_xlabel("Degree alignment condition (measured Pearson r)")
    ax_c.set_ylabel("Total cost over time" if aggregate == "sum" else "Time-averaged cost")
    ax_c.set_title("Total Cost by Inter-Layer Degree Alignment")
    ax_c.grid(True, linewidth=0.4)
    ax_c.legend(fontsize=13, loc="upper center", bbox_to_anchor=(0.5, -0.24), ncols=3)

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


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
    ax.legend(loc="upper center", ncols=min(len(labels), 4), fontsize=12,
              bbox_to_anchor=(0.5, -0.18), bbox_transform=ax.transAxes)
    ax.grid(True, linewidth=0.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


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
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    fig.savefig(save_path, format="pdf", bbox_inches="tight")
    print(f"[saved] {save_path}")
    plt.close(fig)  # non-blocking: review the PDF afterwards


if __name__ == "__main__":
    # python cost_curve_store.py                                -> joint comparison figures
    # python cost_curve_store.py robustness  [hill-climb milp random]
    # python cost_curve_store.py correlation [hill-climb milp random]
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("robustness", "correlation"):
        chosen = sys.argv[2:] or ["hill-climb", "random"]
        if sys.argv[1] == "robustness":
            plot_robustness_heatmaps()   # hill-climb + MILP vs random, whichever are stored
        else:
            plot_correlation_ablation(methods=chosen)
    else:
        plot_joint_cost_comparison()
        plot_joint_cost_elements()
