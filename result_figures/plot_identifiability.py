import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
import pickle

# Global matplotlib settings for publication-quality figures
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "figure.titlesize": 24,
    "lines.linewidth": 2.5,
})

# even_or_odd = 0: only pre-quarantine halves (even-indexed samples)
# even_or_odd = 1: only post-quarantine halves (odd-indexed samples)
# even_or_odd = 2: all samples
CURVE_COLORS = {
    'y_true':  '#2196F3',  # blue
    'y_model': '#FF5722',  # orange-red
    'y_pred':  '#4CAF50',  # green
}

# Color scheme for identifiability plot: one family per quantity.
ID_COLORS = {
    'n_i_true': '#1565C0',  # dark blue
    'n_i_pred': '#64B5F6',  # light blue
    'n_r_true': '#C62828',  # dark red
    'n_r_pred': '#EF9A9A',  # light red
}

def plot_model(samples, even_or_odd=2):
    plt.figure(figsize=(12, 7))

    results_list = []
    legend_added = set()

    # Determine split point between pre/post quarantine when plotting all samples
    split_t = None
    if even_or_odd == 2:
        pre_max = None
        post_min = None
        for i, s in enumerate(samples):
            if 'y_model values' not in s:
                continue
            t = s['y_model values']['x']
            if not t:
                continue
            if i % 2 == 0:
                pre_max = max(t) if pre_max is None else max(pre_max, max(t))
            else:
                post_min = min(t) if post_min is None else min(post_min, min(t))
        if pre_max is not None and post_min is not None:
            split_t = (pre_max + post_min) / 2

    for i, sample in enumerate(samples):

        if not (even_or_odd == 2 or i % 2 == even_or_odd):
            continue

        if 'y_pred all runs' not in sample or 'y_model values' not in sample:
            continue

        y_pred_runs = sample['y_pred all runs']['y']
        y_model_vals = sample['y_model values']['y']
        t_vals = np.array(sample['y_model values']['x'])

        y_pred_runs = [run for run in y_pred_runs if len(run) > 0]
        if not y_pred_runs or not y_model_vals:
            continue

        # Align run lengths (pad with last value if necessary)
        max_len = max(len(run) for run in y_pred_runs)
        for run in y_pred_runs:
            while len(run) < max_len:
                run.append(run[-1])

        y_pred_arr = np.array(y_pred_runs)
        y_pred_mean = np.mean(y_pred_arr, axis=0)
        y_pred_std = np.std(y_pred_arr, axis=0)
        y_model_arr = np.array(y_model_vals)

        # y_true: newly infected from simulation
        y_true_arr = None
        t_vals_true = None
        if 'Given Newly Infected Ratio' in sample:
            t_vals_true = np.array(sample['Given Newly Infected Ratio']['x'])
            y_true_raw = np.array(sample['Given Newly Infected Ratio']['y'])
            min_len = min(len(t_vals_true), len(y_true_raw))
            t_vals_true = t_vals_true[:min_len]
            y_true_arr = y_true_raw[:min_len]

        # --- Plot y_true (newly infected) ---
        if y_true_arr is not None:
            label = 'y_true (Newly Infected)' if 'y_true' not in legend_added else '_nolegend_'
            legend_added.add('y_true')
            plt.plot(
                t_vals_true, y_true_arr,
                color=CURVE_COLORS['y_true'], linestyle='-',
                label=label
            )

        # --- Plot y_pred (estimator mean ± std) ---
        label = 'y_pred (Estimator Mean)' if 'y_pred' not in legend_added else '_nolegend_'
        legend_added.add('y_pred')
        plt.plot(
            t_vals, y_pred_mean,
            color=CURVE_COLORS['y_pred'], linestyle=':',
            label=label
        )
        plt.fill_between(
            t_vals, y_pred_mean - y_pred_std, y_pred_mean + y_pred_std,
            alpha=0.15, color=CURVE_COLORS['y_pred']
        )

        results_list.append({
            "sample_index": i,
            "time_points": t_vals,
            "t_vals_true": t_vals_true,
            "y_true": y_true_arr,
            "y_model": y_model_arr,
            "y_pred_mean": y_pred_mean,
            "y_pred_std": y_pred_std,
        })

    if split_t is not None:
        plt.axvline(split_t, color='gray', linestyle='--', linewidth=1.5, label='Quarantine Start')

    plt.xlabel('Time (days)')
    plt.ylabel(r'Newly Infected ($\eta_i$)')
    if even_or_odd == 0:
        plt.title(r'Identifiability Test (Pre-Quarantine)')
    elif even_or_odd == 1:
        plt.title(r'Identifiability Test (Post-Quarantine)')
    else:
        plt.title(r'Identifiability Test: Estimator vs True')
    plt.legend()
    plt.grid(True)

    plt.savefig(
        "result_figures/identifiability_results.pdf",
        format="pdf",
        bbox_inches="tight"
    )

    plt.show()

    with open("result_figures/plot_identifiability_data.pkl", "wb") as f:
        pickle.dump(results_list, f)


# ---------------------------------------------------------------------------
#
#  Identifiability plot: true vs. predicted n_i and n_r time-series.
#
#    Pulls from these blocks in mfa_xy_data.txt:
#      - Given Newly Infected Ratio       (true n_i, already a ratio)
#      - Newly Recovered                  (true newly recovered, raw counts;
#                                          divided by node count for n_r ratio)
#      - n_i Predicted (Identifiability)  (n_i_pred from reduced model)
#      - n_r Predicted (Identifiability)  (n_r_pred from inverting model)
#
#    even_or_odd: same convention as plot_model. 0 = pre-q halves only,
#                 1 = post-q halves only, 2 = all samples on one axes.
#
# ---------------------------------------------------------------------------
def plot_identifiability_results(samples, even_or_odd=2):
    plt.figure(figsize=(12, 7))

    results_list = []
    legend_added = set()

    # Determine split point between pre/post quarantine when plotting all samples.
    # Anchored to the n_i_pred time axis so the split line lines up with the
    # identifiability series specifically.
    split_t = None
    if even_or_odd == 2:
        pre_max = None
        post_min = None
        for i, s in enumerate(samples):
            if 'n_i Predicted (Identifiability)' not in s:
                continue
            t = s['n_i Predicted (Identifiability)']['x']
            if not t:
                continue
            if i % 2 == 0:
                pre_max = max(t) if pre_max is None else max(pre_max, max(t))
            else:
                post_min = min(t) if post_min is None else min(post_min, min(t))
        if pre_max is not None and post_min is not None:
            split_t = (pre_max + post_min) / 2

    # Pull node count from the first sample so we can convert "Newly Recovered"
    # raw counts into a ratio. Fall back to 200 (the default in the SIR script)
    # if the field is missing.
    node_count = None
    for s in samples:
        if 'Number of nodes' in s:
            try:
                node_count = int(s['Number of nodes'])
            except (TypeError, ValueError):
                pass
            break
    if node_count is None or node_count <= 0:
        node_count = 200

    for i, sample in enumerate(samples):

        if not (even_or_odd == 2 or i % 2 == even_or_odd):
            continue

        # Need at minimum the two predicted series to plot anything meaningful.
        if 'n_i Predicted (Identifiability)' not in sample or \
           'n_r Predicted (Identifiability)' not in sample:
            continue

        # --- Predicted n_i ---
        n_i_pred_x = np.array(sample['n_i Predicted (Identifiability)']['x'])
        n_i_pred_y = np.array(sample['n_i Predicted (Identifiability)']['y'])
        m = min(len(n_i_pred_x), len(n_i_pred_y))
        n_i_pred_x, n_i_pred_y = n_i_pred_x[:m], n_i_pred_y[:m]

        # --- Predicted n_r ---
        n_r_pred_x = np.array(sample['n_r Predicted (Identifiability)']['x'])
        n_r_pred_y = np.array(sample['n_r Predicted (Identifiability)']['y'])
        m = min(len(n_r_pred_x), len(n_r_pred_y))
        n_r_pred_x, n_r_pred_y = n_r_pred_x[:m], n_r_pred_y[:m]

        # --- True n_i (newly infected ratio) ---
        n_i_true_x, n_i_true_y = None, None
        if 'Given Newly Infected Ratio' in sample:
            n_i_true_x = np.array(sample['Given Newly Infected Ratio']['x'])
            n_i_true_y = np.array(sample['Given Newly Infected Ratio']['y'])
            m = min(len(n_i_true_x), len(n_i_true_y))
            n_i_true_x, n_i_true_y = n_i_true_x[:m], n_i_true_y[:m]

        # --- True n_r (newly recovered ratio = count / n) ---
        n_r_true_x, n_r_true_y = None, None
        if 'Newly Recovered' in sample:
            n_r_true_x = np.array(sample['Newly Recovered']['x'])
            n_r_true_raw = np.array(sample['Newly Recovered']['y'], dtype=float)
            m = min(len(n_r_true_x), len(n_r_true_raw))
            n_r_true_x = n_r_true_x[:m]
            n_r_true_y = n_r_true_raw[:m] / node_count

        # --- Plot true n_i ---
        if n_i_true_x is not None and len(n_i_true_x) > 0:
            label = r'True $\eta_i$' if 'n_i_true' not in legend_added else '_nolegend_'
            legend_added.add('n_i_true')
            plt.plot(
                n_i_true_x, n_i_true_y,
                color=ID_COLORS['n_i_true'], linestyle='-',
                label=label
            )

        # --- Plot predicted n_i ---
        label = r'Predicted $\eta_i$' if 'n_i_pred' not in legend_added else '_nolegend_'
        legend_added.add('n_i_pred')
        plt.plot(
            n_i_pred_x, n_i_pred_y,
            color=ID_COLORS['n_i_pred'], linestyle='--',
            label=label
        )

        # --- Plot true n_r ---
        if n_r_true_x is not None and len(n_r_true_x) > 0:
            label = r'True $\eta_r$' if 'n_r_true' not in legend_added else '_nolegend_'
            legend_added.add('n_r_true')
            plt.plot(
                n_r_true_x, n_r_true_y,
                color=ID_COLORS['n_r_true'], linestyle='-',
                label=label
            )

        # --- Plot predicted n_r ---
        label = r'Predicted $\eta_r$' if 'n_r_pred' not in legend_added else '_nolegend_'
        legend_added.add('n_r_pred')
        plt.plot(
            n_r_pred_x, n_r_pred_y,
            color=ID_COLORS['n_r_pred'], linestyle='--',
            label=label
        )

        results_list.append({
            "sample_index": i,
            "n_i_true_x": n_i_true_x,
            "n_i_true_y": n_i_true_y,
            "n_i_pred_x": n_i_pred_x,
            "n_i_pred_y": n_i_pred_y,
            "n_r_true_x": n_r_true_x,
            "n_r_true_y": n_r_true_y,
            "n_r_pred_x": n_r_pred_x,
            "n_r_pred_y": n_r_pred_y,
        })

    if split_t is not None:
        plt.axvline(split_t, color='gray', linestyle='--', linewidth=1.5,
                    label='Quarantine Start')

    plt.xlabel('Time (days)')
    plt.ylabel('Ratio')
    if even_or_odd == 0:
        plt.title(r'Identifiability: True vs Predicted $\eta_i$, $\eta_r$ (Pre-Quarantine)')
    elif even_or_odd == 1:
        plt.title(r'Identifiability: True vs Predicted $\eta_i$, $\eta_r$ (Post-Quarantine)')
    else:
        plt.title(r'Identifiability: True vs Predicted $\eta_i$, $\eta_r$')
    plt.legend()
    plt.grid(True)

    plt.savefig(
        "result_figures/identifiability_n_i_n_r.pdf",
        format="pdf",
        bbox_inches="tight"
    )

    plt.show()

    with open("result_figures/plot_identifiability_n_i_n_r_data.pkl", "wb") as f:
        pickle.dump(results_list, f)


if __name__ == "__main__":
    samples = extract_mfa.parse_sample_data('experiment_data/mfa_xy_data.txt')
    plot_identifiability_results(samples, even_or_odd=2)