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
DEFAULT_BIN = 25
BIN_RANGE   = range(13, 20)   # 1 … 19 inclusive

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
    _, hill_cc, hill_ec, hill_nc, hill_nf, hill_dyn = asm.hill2()

    print("[run] Degree-Based Selection …")
    _, deg_cc, deg_ec, deg_nc, deg_nf, deg_dyn = asm.degree_based_selection()

    # print("[run] No-Quarantine Baseline …")
    # nq_cc, nq_ec, nq_nc, nq_nf, nq_dyn = asm.no_quarantine_baseline_runs()

    print("[run] Random Seed Selection …")
    _, rand_cc, rand_ec, rand_nc, rand_nf, rand_dyn = asm.random_seed_selection()

    comparison_methods = [
        {
            "label": "Hill Climb", "color": "C0",
            "cost_curves": hill_cc, "edge_curves": hill_ec,
            "counts": hill_nc, "frac": hill_nf, "dynamics_list": hill_dyn,
        },
        {
            "label": "Degree-Based", "color": "C1",
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
