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

def _series(sample, key):
    """Return {absolute t: value} for an x/y block of a sample (empty if absent)."""
    if key not in sample:
        return {}
    xs = sample[key]['x']
    ys = sample[key]['y']
    return {int(t): float(y) for t, y in zip(xs, ys)}


def _aggregate(series_list):
    """Mean/std across samples at each absolute t.

    series_list: list of {t: value}, one per sample. A t missing from some
    samples is averaged over the samples that have it; `count` records how many.
    """
    ts = sorted(set().union(*series_list)) if series_list else []
    mean, std, count = [], [], []
    for t in ts:
        vals = [s[t] for s in series_list if t in s]
        mean.append(np.mean(vals))
        std.append(np.std(vals))
        count.append(len(vals))
    return np.array(ts, dtype=int), np.array(mean), np.array(std), np.array(count)


def _plot_band(t, mean, std, count, color):
    """Shade mean ± std only where more than one sample contributes."""
    mask = count > 1
    if mask.any():
        plt.fill_between(t, mean - std, mean + std, where=mask,
                         alpha=0.15, color=color)


def _parities(even_or_odd):
    # Pre (even) and post (odd) halves are aggregated separately so the two
    # curves stay disjoint at the quarantine split.
    return [0, 1] if even_or_odd == 2 else [even_or_odd]


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

    for parity in _parities(even_or_odd):
        model_series, true_series, used = [], [], []
        for i, sample in enumerate(samples):
            if i % 2 != parity or 'y_model values' not in sample:
                continue
            m = _series(sample, 'y_model values')
            if not m:
                continue
            model_series.append(m)
            used.append(i)
            t = _series(sample, 'Given Newly Infected Ratio')
            if t:
                true_series.append(t)

        if not model_series:
            continue

        t_model, model_mean, model_std, model_n = _aggregate(model_series)
        t_true, true_mean, true_std, true_n = _aggregate(true_series)

        # --- Plot y_true (newly infected, mean across samples) ---
        if len(t_true) > 0:
            label = 'y_true (Newly Infected)' if 'y_true' not in legend_added else '_nolegend_'
            legend_added.add('y_true')
            plt.plot(
                t_true, true_mean,
                color=CURVE_COLORS['y_true'], linestyle='-',
                label=label
            )

        # --- Plot y_model (mean ± std across samples) ---
        label = 'y_model (Sample Mean)' if 'y_model' not in legend_added else '_nolegend_'
        legend_added.add('y_model')
        plt.plot(
            t_model, model_mean,
            color=CURVE_COLORS['y_model'], linestyle=':',
            label=label
        )
        _plot_band(t_model, model_mean, model_std, model_n, CURVE_COLORS['y_model'])

        results_list.append({
            "half": parity,
            "sample_indices": used,
            "t_model": t_model,
            "y_model_mean": model_mean,
            "y_model_std": model_std,
            "y_model_n": model_n,
            "t_true": t_true,
            "y_true_mean": true_mean,
            "y_true_std": true_std,
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
#  Delta plot: one-step change in newly infected, model vs. ground truth.
#
#    Model:        y_model(t) - n_i(t-1)
#    Ground truth: n_i(t)     - n_i(t-1)
#
#    Each is computed per sample, then averaged across samples at each t;
#    the std band is across samples (absent where only one sample exists).
#
#    Time alignment (from mean_field_approx.save_xy_data):
#      - "y_model values" x = absolute t, starting at x_ofs (0 or split_point).
#        y_model(t) is the model's n_i(t) using the true w1, w2.
#      - "Given Newly Infected Ratio" x = absolute t, starting at 1 for the
#        pre-quarantine half (n_i(0) is the seed count, not written) and at
#        split_point for the post-quarantine half.
#    Both series are keyed by absolute t, so n_i(t-1) is looked up by t-1.
#    The deltas are only defined for t >= 2 (n_i(t-1) must itself be a real
#    newly-infected value, i.e. t-1 >= 1).
#
#    For a post-quarantine sample, n_i(split_point - 1) lives in the paired
#    pre-quarantine sample (index i-1), so it is borrowed from there.
#
# ---------------------------------------------------------------------------
def _n_i_lookup(sample):
    if 'Given Newly Infected Ratio' not in sample:
        return {}
    xs = sample['Given Newly Infected Ratio']['x']
    ys = sample['Given Newly Infected Ratio']['y']
    return {int(t): float(y) for t, y in zip(xs, ys)}


def delta_model(samples, even_or_odd=2, t_min=2):
    plt.figure(figsize=(12, 7))

    results_list = []
    legend_added = set()

    # Same pre/post split detection as plot_model
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

    for parity in _parities(even_or_odd):
        model_series, true_series, used = [], [], []
        for i, sample in enumerate(samples):
            if i % 2 != parity:
                continue
            if 'y_model values' not in sample or 'Given Newly Infected Ratio' not in sample:
                continue

            y_model = _series(sample, 'y_model values')
            if not y_model:
                continue

            # n_i keyed by absolute t; borrow the preceding half's values for t-1 lookups
            own_n_i = _n_i_lookup(sample)
            n_i = dict(own_n_i)
            if i % 2 == 1 and i - 1 >= 0:
                for t, y in _n_i_lookup(samples[i - 1]).items():
                    n_i.setdefault(t, y)

            # Model delta: y_model(t) - n_i(t-1)
            model_series.append({t: v - n_i[t - 1] for t, v in y_model.items()
                                 if t >= t_min and (t - 1) in n_i})
            # Ground-truth delta: n_i(t) - n_i(t-1), over this sample's own t range
            true_series.append({t: own_n_i[t] - n_i[t - 1] for t in own_n_i
                                if t >= t_min and (t - 1) in n_i})
            used.append(i)

        if not model_series:
            continue

        t_model, delta_model_mean, delta_model_std, delta_model_n = _aggregate(model_series)
        t_true, delta_true_mean, delta_true_std, _ = _aggregate(true_series)

        # --- Plot ground-truth delta (mean across samples) ---
        if len(t_true) > 0:
            label = r'True $\Delta\eta_i$' if 'y_true' not in legend_added else '_nolegend_'
            legend_added.add('y_true')
            plt.plot(
                t_true, delta_true_mean,
                color=CURVE_COLORS['y_true'], linestyle='-',
                label=label
            )

        # --- Plot model delta (mean ± std across samples) ---
        if len(t_model) > 0:
            label = r'Model $\Delta\eta_i$ (Sample Mean)' if 'y_model' not in legend_added else '_nolegend_'
            legend_added.add('y_model')
            plt.plot(
                t_model, delta_model_mean,
                color=CURVE_COLORS['y_model'], linestyle=':',
                label=label
            )
            _plot_band(t_model, delta_model_mean, delta_model_std, delta_model_n,
                       CURVE_COLORS['y_model'])

        results_list.append({
            "half": parity,
            "sample_indices": used,
            "t_model": t_model,
            "delta_model_mean": delta_model_mean,
            "delta_model_std": delta_model_std,
            "delta_model_n": delta_model_n,
            "t_true": t_true,
            "delta_true_mean": delta_true_mean,
            "delta_true_std": delta_true_std,
        })

    if split_t is not None:
        plt.axvline(split_t, color='gray', linestyle='--', linewidth=1.5, label='Quarantine Start')

    plt.axhline(0, color='black', linewidth=0.8)
    plt.xlabel('Time (days)')
    plt.ylabel(r'$\Delta$ Newly Infected ($\eta_i(t) - \eta_i(t-1)$)')
    if even_or_odd == 0:
        plt.title(r'One-Step Change in $\eta_i$ (Pre-Quarantine)')
    elif even_or_odd == 1:
        plt.title(r'One-Step Change in $\eta_i$ (Post-Quarantine)')
    else:
        plt.title(r'One-Step Change in $\eta_i$: Estimator vs True')
    plt.legend()
    plt.grid(True)

    plt.savefig(
        "result_figures/delta_model_results.pdf",
        format="pdf",
        bbox_inches="tight"
    )

    plt.show()

    with open("result_figures/delta_model_data.pkl", "wb") as f:
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
    # plot_identifiability_results(samples, even_or_odd=2)
    delta_model(samples, even_or_odd=0, t_min=2)