"""
drive_seed_selection.py — Run adaptive seed-selection for one contact network.

Usage
-----
    python drive_seed_selection.py [bin_index]

bin_index : int in [1, 19]  (default: 10)
    Selects the network file for the chosen DATASET option.

Without an argument the script uses bin 10 and produces the standard single
comparison plot.  With an explicit bin index it produces a dual figure:
contact-network visualization on the left, full method comparison on the right,
saved to  capstone_result_figures/dual_bin{bin_index}.pdf

Scale experiment
----------------
    python drive_seed_selection.py scale

Runs adaptive_seed_selection.run_methods() once per scale in SCALES, injecting
scale into _core_over_btw_score / _core_over_deg_score.  Each scale's curves go to
its own AdaptSelect_coreness_scale_experiment_scale{scale}.pkl (never to
cost_curves_data.pkl); point cost_curve_store's plot functions at one by path.

Robustness experiment (cascade time x seed set size)
----------------------------------------------------
    python drive_seed_selection.py robustness [hill-climb] [milp] [random] [--plot-only]

Runs each chosen method for every cascade time in CASCADE_TIMES (batch interval;
None = no information cascade) and seed set size in SEED_FRACTIONS on
asm.CONTACT_NETWORK_PATH / asm.SOCIAL_NETWORK_PATH, stores the curves in
robustness_experiment.pkl, then plots one total-cost heatmap per method
(cost_curve_store.plot_robustness_heatmaps). Every method, random included, is
run for every (cascade time, seed size) cell. Running a method clears that
method's old robustness results first. Methods default to hill-climb + random.

Correlation ablation
--------------------
    python drive_seed_selection.py correlation [hill-climb] [milp] [random] [--plot-only]

Holds rc_contact_network_bin{CORRELATION_BIN}.gml fixed and rebuilds the social
layer for each (social, contact) cell of the high/low x high/low matrix in
CORRELATION_CONDITIONS (Correlate3.partial_rank_mapping, top/bottom
CORRELATION_EXTREME_FRACTION of nodes), cascade time CORRELATION_CASCADE. Stores curves in correlation_ablation.pkl and
plots cost_curve_store.plot_correlation_ablation. Random runs once, on the
observed social layer, and is drawn as a single curve.

Social rule sweep
-----------------
    python drive_seed_selection.py social-rule

Runs hill2 on rc_contact_network_bin{9..18}.gml (with asm.SOCIAL_NETWORK_PATH) and
distills the social rule-based [degree, coreness] rule vector (5 bins each) for each, writing
every vector plus their nearest-bin mean to social_rule_based_sweep.txt.

--plot-only skips the runs and re-plots whatever is already stored, e.g. after
running methods separately:  ... robustness milp  then  ... robustness hill-climb milp random --plot-only
"""

import sys
import os
from enum import Enum, auto


class Dataset(Enum):
    rc           = auto()
    high_school  = auto()


# ── CHOOSE DATASET HERE ───────────────────────────────────────────────────────
DATASET = Dataset.rc
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import networkx as nx
import adaptive_seed_selection as asm

# ── argument parsing ──────────────────────────────────────────────────────────
DEFAULT_BIN = 15
BIN_RANGE   = range(13, 20)   # 1 … 19 inclusive

# ── scale experiment ──────────────────────────────────────────────────────────
SCALES = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
SCALE_STORE_TEMPLATE = "AdaptSelect_coreness_scale_experiment_scale{scale}.pkl"

def run_scale_experiment():
    # Initialize once so every scale shares the same baselines, betas and injections.
    asm.initialize(asm.CONTACT_NETWORK_PATH, asm.SOCIAL_NETWORK_PATH)
    for scale in SCALES:
        store_path = SCALE_STORE_TEMPLATE.format(scale=scale)
        print(f"\n[scale] {scale} -> {store_path}")
        asm.run_methods(scale=scale, store_path=store_path)
    print("[done] Scale experiment complete.")

# ── shared helpers for the robustness / correlation experiments ──────────────
import cost_curve_store
import Correlate1
import Correlate3

# None = no information cascade: info never spreads past the seeds, and seeds are
# re-chosen every step (batch_interval = NO_CASCADE_BATCH_INTERVAL).
NO_CASCADE_BATCH_INTERVAL = 1
DEFAULT_EXPERIMENT_METHODS = ["hill-climb", "random"]


def _set_cascade(module, cascade):
    """Point a seed-selection module (asm or milp) at one cascade time."""
    if cascade is None:
        module.information_spread = False
        module.batch_interval = NO_CASCADE_BATCH_INTERVAL
    else:
        module.information_spread = True
        module.batch_interval = cascade


def _run_cost_curves(method):
    """Run one method on its already-initialized module; return its per-batch cost curves."""
    if method == "hill-climb":
        return asm.hill2()[1]
    if method == "random":
        return asm.random_seed_selection()[1]
    if method == "degree":
        return asm.degree_based_selection()[1]
    if method == "milp":
        import milp
        return milp.milp_seed_selection_stepwise()[1]
    raise ValueError(method)


def _comparison_curves(result):
    """(cost_curves, edge_curves, newly_infected_counts, newly_infected_frac, full_dynamics)
    from a seed-selection policy's result. hill2, degree_based_selection and
    random_seed_selection all start (winner, cost, infection_term, edge_term, edge, counts,
    frac, dynamics, tagged, ...); hill2 adds batch_seed_sets before the alpha/beta curves."""
    return result[1], result[4], result[5], result[6], result[7]


def _module_for(method):
    if method == "milp":
        import milp
        return milp
    return asm


def _push(method, key, curves, path):
    module = _module_for(method)
    cost_curve_store.push_experiment_curve(
        cost_curve_store.METHOD_ALIASES[method], key, curves,
        batch_interval=module.batch_interval, T=module.T, path=path)


def _parse_experiment_args(args):
    """[methods...] [--plot-only] -> (methods, plot_only). Methods default to hill-climb + random."""
    plot_only = "--plot-only" in args
    methods = [a.lower() for a in args if a != "--plot-only"] or list(DEFAULT_EXPERIMENT_METHODS)
    bad = [m for m in methods if m not in cost_curve_store.EXPERIMENT_METHODS]
    if bad:
        sys.exit(f"Unknown method(s) {bad}; choose from {list(cost_curve_store.EXPERIMENT_METHODS)}")
    return methods, plot_only


def _initialize_modules(methods, contact_path, social_path):
    """Initialize only the modules the chosen methods need; return them."""
    modules = []
    if "hill-climb" in methods or "random" in methods:
        asm.initialize(contact_path, social_path)
        modules.append(asm)
    if "milp" in methods:
        import milp
        milp.initialize(contact_path, social_path)
        modules.append(milp)
    return modules


# ── Experiment 1: cascade time x seed set size robustness ────────────────────
#   python drive_seed_selection.py robustness [hill-climb] [milp] [random] [--plot-only]
CASCADE_TIMES  = [None, 5, 10, 15]          # batch intervals; None = no cascade
SEED_FRACTIONS = [round(0.1 * i, 2) for i in range(1, 11)]   # 10%, 20%, ..., 100% of n
def run_robustness_experiment(methods):
    path = cost_curve_store.ROBUSTNESS_STORE_PATH
    # Drop each method's previous robustness results so no stale cells (old seed
    # sizes, or random's old cascade-duplicated rows) survive a rerun.
    for method in methods:
        cost_curve_store.clear_experiment_label(cost_curve_store.METHOD_ALIASES[method], path)
    # Initialize once so every configuration shares the same betas, injections and baselines.
    _initialize_modules(methods, asm.CONTACT_NETWORK_PATH, asm.SOCIAL_NETWORK_PATH)

    for frac in SEED_FRACTIONS:
        if "hill-climb" in methods or "random" in methods:
            asm.K = max(1, int(frac * asm.n))
        if "milp" in methods:
            import milp
            milp.seed_fraction = frac

        for method in ("hill-climb", "milp", "random"):
            if method not in methods:
                continue
            for cascade in CASCADE_TIMES:
                _set_cascade(_module_for(method), cascade)
                print(f"\n[robustness] {method}: cascade={cascade}, seeds={frac:.0%}")
                _push(method, (cascade, frac), _run_cost_curves(method), path)

    print("[done] Robustness experiment complete.")


# ── Experiment 3: inter-layer correlation ablation ───────────────────────────
#   python drive_seed_selection.py correlation [hill-climb] [milp] [random] [--plot-only]
# (social group, contact group) cells of the high/low x high/low matrix, as in
# Correlate3.make_contact_layer_conditions: the top/bottom CORRELATION_EXTREME_FRACTION
# of social nodes (by social degree) are rank-mapped onto the top/bottom fraction of
# contact nodes (by contact degree); every other node is placed at random.
CORRELATION_CONDITIONS        = [("high", "high"), ("high", "low"), ("low", "high"), ("low", "low")]
CORRELATION_EXTREME_FRACTION  = 0.25
CORRELATION_CASCADE = 5
CORRELATION_BIN     = 10
CORRELATION_SEED    = 123   # fixed so every module builds identical correlated social layers

def _measured_correlation(contact, social):
    """Pearson inter-layer degree correlation (Correlate1), social treated as undirected."""
    return Correlate1.degree_correlation_over_time(social.to_undirected(), [contact])[0]["degree_correlation"]


def _social_for_condition(contact, social, social_group, contact_group):
    """Relabel `social` onto `contact`'s nodes for one (social, contact) high/low cell.
    The contact layer is held fixed and the SOCIAL layer is relabeled, so the two layers
    swap roles relative to partial_rank_mapping's argument names (its G is the fixed
    reference, its H the graph being relabeled, and its group names follow G / H)."""
    return Correlate3.partial_rank_mapping(
        G=contact, H=social,
        social_group=contact_group,   # group of G (= contact layer here)
        contact_group=social_group,   # group of H (= social layer here)
        extreme_fraction=CORRELATION_EXTREME_FRACTION,
        random_seed=CORRELATION_SEED)


def run_correlation_experiment(methods):
    path = cost_curve_store.CORRELATION_STORE_PATH
    # Drop each method's previous correlation results so no stale cells survive a rerun.
    for method in methods:
        cost_curve_store.clear_experiment_label(cost_curve_store.METHOD_ALIASES[method], path)
    contact_path = f"capstone_proj_data/rc_contact_network_bin{CORRELATION_BIN}.gml"
    modules = _initialize_modules(methods, contact_path, asm.SOCIAL_NETWORK_PATH)
    for module in modules:
        _set_cascade(module, CORRELATION_CASCADE)
    observed_social = {module: module.initial_social for module in modules}

    ref = modules[0]
    measured = {"observed": _measured_correlation(ref.initial_contact, ref.initial_social)}
    print(f"[correlation] observed social layer: r = {measured['observed']:.3f}")

    for cond in CORRELATION_CONDITIONS:
        # Same contact layer every time; only the social layer's placement changes.
        for module in modules:
            module.initial_social, _ = _social_for_condition(
                module.initial_contact, observed_social[module], *cond)
        measured[cond] = _measured_correlation(ref.initial_contact, ref.initial_social)
        print(f"\n[correlation] {cond[0]} social -> {cond[1]} contact  ->  measured r = {measured[cond]:.3f}")

        for method in ("hill-climb", "milp"):
            if method in methods:
                _push(method, cond, _run_cost_curves(method), path)

    if "random" in methods:
        # Random's seed choices ignore the social layer's alignment: one run, on the
        # observed (unpermuted) social network, stands in for every correlation.
        asm.initial_social = observed_social[asm]
        print("\n[correlation] random (single, correlation-independent curve)")
        _push("random", cost_curve_store.RANDOM_ALL_KEY, _run_cost_curves("random"), path)

    cost_curve_store.push_experiment_meta("measured_correlation", measured, path)
    print("[done] Correlation ablation complete.")


# ── Experiment 4: social rule-based rule vectors across contact bins ─────────
#   python drive_seed_selection.py social-rule
# For each rc_contact_network_bin{b}.gml (b in SOCIAL_RULE_BINS, paired with
# asm.SOCIAL_NETWORK_PATH), runs hill2 and distills the social rule-based rule
# ([deg, core] bin vector, SOCIAL_RULE_NUM_BINS bins each) from its accepted seed
# sets -- the same rule asm.social_rule_based() would use. Every rule, then the
# element-wise mean snapped to the nearest bin, goes to SOCIAL_RULE_SWEEP_FILE.
SOCIAL_RULE_BINS      = range(9, 19)   # 9 ... 18 inclusive
SOCIAL_RULE_NUM_BINS  = 5
SOCIAL_RULE_SWEEP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "social_rule_based_sweep.txt")

def run_social_rule_sweep(contact_bins=SOCIAL_RULE_BINS, bins=SOCIAL_RULE_NUM_BINS,
                          out_path=SOCIAL_RULE_SWEEP_FILE):
    bin_counts = (bins, bins)
    rules = {}
    with open(out_path, "w") as f:
        f.write(asm.RULE_FILE_HEADER)
        for b in contact_bins:
            contact_path = f"capstone_proj_data/rc_contact_network_bin{b}.gml"
            print(f"\n[social-rule] Loading {contact_path}")
            asm.initialize(contact_path, asm.SOCIAL_NETWORK_PATH)
            if asm.n == 0:
                print(f"[skip] bin {b} -- empty network, skipping.")
                f.write(f"\n# rc_contact_network_bin{b}: empty network, skipped\n")
                continue

            asm.hill2()
            rule, counts, _ = asm.social_rule_from_seed_sets(asm.hill2_accepted_seed_sets, bins)
            rules[b] = rule
            print(f"[social-rule] bin {b}: rule = {list(rule)} "
                  f"(seen {counts[rule]} / {sum(counts.values())} times; B = {bins})")

            f.write(f"\n# rc_contact_network_bin{b} (n = {asm.n}; seen {counts[rule]} / "
                    f"{sum(counts.values())} times)\n")
            f.write(asm.format_rule_lines(rule, bin_counts))
            f.flush()   # keep finished bins on disk if a later bin crashes

        if rules:
            raw_mean = np.mean(np.array(list(rules.values()), dtype=float), axis=0)
            mean_rule = np.clip(np.rint(raw_mean), 0, bins - 1).astype(int)
            f.write(f"\n# mean over bins {list(rules)}, snapped to the nearest bin "
                    f"(raw mean: {' '.join(f'{v:.6g}' for v in raw_mean)})\n")
            f.write(asm.format_rule_lines(mean_rule, bin_counts))
            print(f"\n[social-rule] mean rule = {mean_rule.tolist()} (raw {raw_mean.tolist()})")

    print(f"[done] Social rule sweep written to {out_path}")


if len(sys.argv) > 1 and sys.argv[1] == "social-rule":
    run_social_rule_sweep()
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "scale":
    run_scale_experiment()
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "robustness":
    _methods, _plot_only = _parse_experiment_args(sys.argv[2:])
    if not _plot_only:
        run_robustness_experiment(_methods)
    # Always plot hill-climb + MILP (whichever are stored) as % improvement over random,
    # regardless of which methods this invocation just ran.
    cost_curve_store.plot_robustness_heatmaps(
        path=cost_curve_store.ROBUSTNESS_STORE_PATH,
        cascade_times=CASCADE_TIMES, seed_fractions=SEED_FRACTIONS)
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "correlation":
    _methods, _plot_only = _parse_experiment_args(sys.argv[2:])
    if not _plot_only:
        run_correlation_experiment(_methods)
    cost_curve_store.plot_correlation_ablation(
        methods=_methods, path=cost_curve_store.CORRELATION_STORE_PATH,
        conditions=CORRELATION_CONDITIONS)
    sys.exit(0)

if len(sys.argv) > 1:
    bins_to_run  = [int(sys.argv[1])]
    show_network = True
else:
    bins_to_run  = list(BIN_RANGE)
    show_network = True
os.makedirs("capstone_result_figures", exist_ok=True)

# ── plotting helpers ──────────────────────────────────────────────────────────

def _draw_network(ax, G, title):
    """Contact-network panel: nodes coloured/sized by degree, edges by weight."""
    degrees = dict(G.degree())
    pos     = nx.kamada_kawai_layout(G)

    # Edge widths + alphas proportional to weight, normalised to [0.3, 2.5]
    edges   = list(G.edges())
    weights = np.array([G[u][v].get("weight", 1.0) for u, v in edges], dtype=float)
    w_range = weights.max() - weights.min()
    w_norm  = (weights - weights.min()) / w_range if w_range > 0 else np.ones_like(weights)
    edge_lw    = 0.3 + 2.2 * w_norm
    edge_alpha = 0.20 + 0.45 * w_norm   # heavier edges are more opaque

    for (u, v), lw, alpha in zip(edges, edge_lw, edge_alpha):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.plot([x0, x1], [y0, y1], color="#999999", lw=lw,
                alpha=float(alpha), zorder=1)

    # Nodes: size + colour by degree
    node_list  = list(G.nodes())
    deg_vals   = np.array([degrees[nd] for nd in node_list], dtype=float)
    d_range    = deg_vals.max() - deg_vals.min()
    d_norm_arr = (deg_vals - deg_vals.min()) / d_range if d_range > 0 else np.ones_like(deg_vals)
    node_sizes = 30 + 120 * d_norm_arr

    cmap  = cm.plasma
    cnorm = mcolors.Normalize(vmin=deg_vals.min(), vmax=deg_vals.max())
    sc = ax.scatter(
        [pos[nd][0] for nd in node_list],
        [pos[nd][1] for nd in node_list],
        c=deg_vals, cmap=cmap, norm=cnorm,
        s=node_sizes, zorder=2,
        linewidths=0.5, edgecolors="white",
    )

    ax.set_title(title, pad=10)
    ax.set_axis_off()

    cb = plt.colorbar(sc, ax=ax, fraction=0.036, pad=0.02)
    cb.set_label("Node Degree", fontsize=10)
    cb.ax.tick_params(labelsize=8)


def _draw_comparison(ax, ax_inf, methods, initial_edge_count, bin_idx):
    """Full-comparison content drawn into caller-supplied twin axes."""
    def stats(arr):
        a = np.array(arr)
        return np.mean(a, axis=0), np.std(a, axis=0)

    for m in methods:
        edges = np.array(m["edge_curves"]) / initial_edge_count
        m["_c_mean"], m["_c_std"] = stats(m["cost_curves"])
        m["_e_mean"], m["_e_std"] = stats(edges)
        m["_i_mean"], m["_i_std"] = stats(m["frac"])

    time = np.arange(len(methods[0]["_c_mean"]))

    COST_LW = 2.6;  COMP_LW = 1.2
    COST_A  = 0.20; COMP_A  = 0.07

    # -- edges (dash, left axis)
    for m in methods:
        ax.plot(time, m["_e_mean"], color=m["color"],
                linestyle=(0, (4, 2)), linewidth=COMP_LW, alpha=0.55,
                label=f"{m['label']} – Edges", zorder=2)
        ax.fill_between(time,
                        m["_e_mean"] - m["_e_std"],
                        m["_e_mean"] + m["_e_std"],
                        color=m["color"], alpha=COMP_A, zorder=1)

    # -- newly infected (dot, right axis)
    inf_max = max((m["_i_mean"] + m["_i_std"]).max() for m in methods)
    ax_inf.set_ylim(0, inf_max * 1.15)
    for m in methods:
        ax_inf.plot(time, m["_i_mean"], color=m["color"],
                    linestyle=(0, (1, 2)), linewidth=COMP_LW, alpha=0.55,
                    label=f"{m['label']} – Infected", zorder=2)
        ax_inf.fill_between(time,
                            m["_i_mean"] - m["_i_std"],
                            m["_i_mean"] + m["_i_std"],
                            color=m["color"], alpha=COMP_A, zorder=1)

    # -- cost (solid, left axis)
    for m in methods:
        ax.plot(time, m["_c_mean"], color=m["color"],
                linestyle="-", linewidth=COST_LW,
                label=f"{m['label']} – Cost", zorder=4)
        ax.fill_between(time,
                        m["_c_mean"] - m["_c_std"],
                        m["_c_mean"] + m["_c_std"],
                        color=m["color"], alpha=COST_A, zorder=3)

    ax.set_xlabel("Time Step")
    ax.set_ylabel("Global Cost / Live Edge Fraction")
    ax_inf.set_ylabel("Newly Infected Fraction", labelpad=10)
    ax.set_title(f"Method Comparison — bin {bin_idx}", pad=10)
    ax.grid(True, linewidth=0.4)

    # Combined legend: cost rows first, then edges, then infected
    n_m = len(methods)
    h_l, la_l = ax.get_legend_handles_labels()
    h_r, la_r = ax_inf.get_legend_handles_labels()
    all_h  = h_l[-n_m:] + h_l[:-n_m] + h_r
    all_la = la_l[-n_m:] + la_l[:-n_m] + la_r
    ax.legend(all_h, all_la, ncols=2, fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, -0.18),
              bbox_transform=ax.transAxes)


# ── main loop ─────────────────────────────────────────────────────────────────

for bin_idx in bins_to_run:
    if DATASET is Dataset.rc:
        network_path = f"capstone_proj_data/rc_weighted_contact_bin{bin_idx}.gml"
    else:
        network_path = f"capstone_proj_data/high_school_contact_bin{bin_idx}.gml"

    # ── initialisation (baseline sims run here) ───────────────────────────────
    print(f"\n[init] Loading {network_path}")
    asm.initialize(network_path)
    if asm.n == 0:
        print(f"[skip] bin {bin_idx} — empty network, skipping.")
        continue

    # ── run all four methods ──────────────────────────────────────────────────
    print("[run] Hill Climb (hill2) …")
    hill_cc, hill_ec, hill_nc, hill_nf, hill_dyn = _comparison_curves(asm.hill2())

    print("[run] Degree-Based Selection …")
    deg_cc, deg_ec, deg_nc, deg_nf, deg_dyn = _comparison_curves(asm.degree_based_selection())

    # print("[run] No-Quarantine Baseline …")
    # nq_cc, nq_ec, nq_nc, nq_nf, nq_dyn = asm.no_quarantine_baseline_runs()

    print("[run] Random Seed Selection …")
    rand_cc, rand_ec, rand_nc, rand_nf, rand_dyn = _comparison_curves(asm.random_seed_selection())

    comparison_methods = [
        {
            "label": "Hill Climb", "color": "C0",
            "cost_curves": hill_cc, "edge_curves": hill_ec,
            "counts": hill_nc, "frac": hill_nf, "dynamics_list": hill_dyn,
        },
        {
            "label": "DegrBased", "color": "C1",
            "cost_curves": deg_cc, "edge_curves": deg_ec,
            "counts": deg_nc, "frac": deg_nf, "dynamics_list": deg_dyn,
        },
        # {
        #     "label": "No Quarantine", "color": "C2",
        #     "cost_curves": nq_cc, "edge_curves": nq_ec,
        #     "counts": nq_nc, "frac": nq_nf, "dynamics_list": nq_dyn,
        # },
        {
            "label": "Random Seeds", "color": "C3",
            "cost_curves": rand_cc, "edge_curves": rand_ec,
            "counts": rand_nc, "frac": rand_nf, "dynamics_list": rand_dyn,
        },
    ]

    # ── produce figure ────────────────────────────────────────────────────────
    if show_network:
        fig = plt.figure(figsize=(24, 9))
        gs  = gridspec.GridSpec(
            1, 2,
            width_ratios=[2, 3],
            figure=fig,
            left=0.03, right=0.97,
            top=0.88,  bottom=0.20,
            wspace=0.30,
        )

        ax_net  = fig.add_subplot(gs[0])
        ax_comp = fig.add_subplot(gs[1])
        ax_inf  = ax_comp.twinx()

        _draw_network(
            ax_net,
            asm.initial_contact,
            f"Contact Network\nbin {bin_idx}  ({asm.n} nodes, {asm.initial_edge_count} edges)",
        )
        _draw_comparison(ax_comp, ax_inf, comparison_methods, asm.initial_edge_count, bin_idx)

        fig.suptitle(
            f"Adaptive Seed Selection — {os.path.basename(network_path)}",
            fontsize=15, y=0.97,
        )

        out_path = f"capstone_result_figures/dual_bin{bin_idx}.pdf"
        fig.savefig(out_path, format="pdf", bbox_inches="tight")
        print(f"[saved] {out_path}")
        plt.close(fig)

print("[done] All bins processed.")
