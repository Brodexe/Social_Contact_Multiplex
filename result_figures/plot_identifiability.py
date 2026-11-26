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

# ---------------------------------------------------------------------------
#
#  Sample layout in mfa_xy_data.txt (written by mean_field_approx.save_xy_data)
#
#    split_point is None -> each run writes ONE full-window sample (t = 0..T-1).
#    split_point = sp    -> each run writes TWO samples, back to back:
#                           pre-quarantine  (t = 0..sp-1), then
#                           post-quarantine (t = sp..T-1).
#
#  Samples are therefore grouped by the window they cover (read from their
#  x-values), never by their index parity in the file:
#    half 0 = sample starts at t = 0 (pre-quarantine half, or a full window)
#    half 1 = sample starts at t > 0 (post-quarantine half)
#
#  even_or_odd keeps its old meaning for callers:
#    0 = half 0 only, 1 = half 1 only, 2 = every half present, on one axes.
#  The "Quarantine Start" line is drawn only when both halves are present.
#
# ---------------------------------------------------------------------------

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

# Blocks whose x-values start at the sample's x offset (0 or split_point).
# "Given Newly Infected Ratio" is NOT one of them: its pre-quarantine x starts at 1.
_OFFSET_KEYS = ('y_model values', 'w1 True (Mean Node Degree)', 'n_i Predicted (Identifiability)')


# ---------------------------------------------------------------------------
#  Sample helpers
# ---------------------------------------------------------------------------
def _series(sample, key):
    """Return {absolute t: value} for an x/y block of a sample (empty if absent)."""
    if key not in sample:
        return {}
    xs = sample[key]['x']
    ys = sample[key]['y']
    return {int(t): float(y) for t, y in zip(xs, ys)}


def _start_t(sample):
    """The sample's x offset (0 for a pre-quarantine or full-window sample), or None."""
    for key in _OFFSET_KEYS:
        if key in sample and sample[key]['x']:
            return int(sample[key]['x'][0])
    return None


def _half(sample):
    """0 if the sample starts at t = 0, 1 if it starts later (post-quarantine), None if unknown."""
    start = _start_t(sample)
    if start is None:
        return None
    return 0 if start == 0 else 1


def _groups(samples, even_or_odd, require=()):
    """{half: [sample indices]} for the halves selected by even_or_odd.

    require: block names every returned sample must contain.
    """
    groups = {}
    for i, s in enumerate(samples):
        h = _half(s)
        if h is None or any(key not in s for key in require):
            continue
        if even_or_odd != 2 and h != even_or_odd:
            continue
        groups.setdefault(h, []).append(i)
    return dict(sorted(groups.items()))


def _split_t(samples, groups, key):
    """Midpoint between the last pre-quarantine t and the first post-quarantine t.

    None unless both halves are present, so full-window runs get no split line.
    """
    if 0 not in groups or 1 not in groups:
        return None
    pre_ts = [t for i in groups[0] for t in _series(samples[i], key)]
    post_ts = [t for i in groups[1] for t in _series(samples[i], key)]
    if not pre_ts or not post_ts:
        return None
    return (max(pre_ts) + min(post_ts)) / 2


def _pre_partner(samples, i):
    """For a post-quarantine sample i, the pre-quarantine half of the SAME run, or None.

    save_xy_data writes the pre half immediately before the post half, and the two
    windows are contiguous. Anything else (e.g. the previous entry is another full-window
    run) is rejected rather than borrowed from.
    """
    if i == 0 or _half(samples[i]) != 1 or _half(samples[i - 1]) != 0:
        return None
    pre_ts = _series(samples[i - 1], 'y_model values')
    if not pre_ts or max(pre_ts) + 1 != _start_t(samples[i]):
        return None
    return samples[i - 1]


def _check_homogeneous(samples, indices):
    """Warn when the samples being averaged came from different configurations.

    mean_field_approx.py appends to mfa_xy_data.txt unless clear=True, so a file can
    silently mix runs with different sizes or adherence levels.
    """
    for field in ('Number of nodes', 'Adhering proportion'):
        values = {str(samples[i].get(field)) for i in indices}
        if len(values) > 1:
            print(f"Warning: averaging samples with different '{field}': {sorted(values)}")


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


def _plot_mean(series_list, color, linestyle, label, key, legend_added, band=True):
    """Plot the across-sample mean (and ± std band) of series_list; return the aggregate."""
    t, mean, std, count = _aggregate(series_list)
    if len(t) == 0:
        return t, mean, std, count
    plt.plot(t, mean, color=color, linestyle=linestyle,
             label=label if key not in legend_added else '_nolegend_')
    legend_added.add(key)
    if band:
        _plot_band(t, mean, std, count, color)
    return t, mean, std, count


def _sample_count_note(groups):
    return ', '.join(f"{'pre/full' if h == 0 else 'post'}: n={len(idx)}" for h, idx in groups.items())


def _title(base, even_or_odd, groups, samples):
    """Base title, a pre/post suffix when one half is selected, and the sample counts."""
    file_has_post = 1 in _groups(samples, 2)
    if even_or_odd == 0 and file_has_post:
        suffix = ' (Pre-Quarantine)'
    elif even_or_odd == 1:
        suffix = ' (Post-Quarantine)'
    else:
        suffix = ''
    return f"{base}{suffix}\n[{_sample_count_note(groups)}]"


def _finish(title, ylabel, split_t, pdf_path, pkl_path, results_list):
    if split_t is not None:
        plt.axvline(split_t, color='gray', linestyle='--', linewidth=1.5, label='Quarantine Start')
    plt.xlabel('Time (days)')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
    plt.show()
    with open(pkl_path, "wb") as f:
        pickle.dump(results_list, f)


# ---------------------------------------------------------------------------
#
#  Model plot: y_model (the paper's eta_i model at the true <k>, r) vs. true eta_i,
#  each averaged across samples at each absolute t.
#
#    t_min = 1 by default: the code's t = 0 entry of "eta_i" is the prevalence i(0),
#    not a newly-infected fraction, so there is no true value to compare y_model(0) to.
#
# ---------------------------------------------------------------------------
def plot_model(samples, even_or_odd=2, t_min=1):
    plt.figure(figsize=(12, 7))

    groups = _groups(samples, even_or_odd, require=('y_model values',))
    split_t = _split_t(samples, groups, 'y_model values')

    results_list = []
    legend_added = set()

    for half, indices in groups.items():
        _check_homogeneous(samples, indices)

        model_series = [{t: v for t, v in _series(samples[i], 'y_model values').items() if t >= t_min}
                        for i in indices]
        true_series = [{t: v for t, v in _series(samples[i], 'Given Newly Infected Ratio').items() if t >= t_min}
                       for i in indices]
        true_series = [s for s in true_series if s]

        t_true, true_mean, true_std, true_n = _plot_mean(
            true_series, CURVE_COLORS['y_true'], '-', 'y_true (Newly Infected)', 'y_true', legend_added)
        t_model, model_mean, model_std, model_n = _plot_mean(
            model_series, CURVE_COLORS['y_model'], ':', 'y_model (Sample Mean)', 'y_model', legend_added)

        results_list.append({
            "half": half,
            "sample_indices": indices,
            "t_model": t_model,
            "y_model_mean": model_mean,
            "y_model_std": model_std,
            "y_model_n": model_n,
            "t_true": t_true,
            "y_true_mean": true_mean,
            "y_true_std": true_std,
            "y_true_n": true_n,
        })

    base = 'Identifiability Test' if even_or_odd != 2 else 'Identifiability Test: Estimator vs True'
    _finish(_title(base, even_or_odd, groups, samples), r'Newly Infected ($\eta_i$)', split_t,
            "result_figures/identifiability_results.pdf",
            "result_figures/plot_identifiability_data.pkl", results_list)


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
#      - "Given Newly Infected Ratio" x = absolute t, starting at 1 for a sample
#        that starts at t = 0 (n_i(0) is the prevalence, not written) and at
#        split_point for a post-quarantine sample.
#    The deltas are only defined for t >= 2 (n_i(t-1) must itself be a real
#    newly-infected value, i.e. t-1 >= 1).
#
#    For a post-quarantine sample, n_i(split_point - 1) lives in the pre-quarantine
#    half of the same run; _pre_partner finds it and refuses unrelated samples.
#
# ---------------------------------------------------------------------------
def _n_i_lookup(sample):
    return _series(sample, 'Given Newly Infected Ratio')


def delta_model(samples, even_or_odd=2, t_min=2):
    plt.figure(figsize=(12, 7))

    groups = _groups(samples, even_or_odd, require=('y_model values', 'Given Newly Infected Ratio'))
    split_t = _split_t(samples, groups, 'y_model values')

    results_list = []
    legend_added = set()

    for half, indices in groups.items():
        _check_homogeneous(samples, indices)
        model_series, true_series = [], []
        for i in indices:
            sample = samples[i]
            y_model = _series(sample, 'y_model values')
            own_n_i = _n_i_lookup(sample)
            n_i = dict(own_n_i)
            partner = _pre_partner(samples, i)
            if partner is not None:
                for t, y in _n_i_lookup(partner).items():
                    n_i.setdefault(t, y)

            model_series.append({t: v - n_i[t - 1] for t, v in y_model.items()
                                 if t >= t_min and (t - 1) in n_i})
            true_series.append({t: own_n_i[t] - n_i[t - 1] for t in own_n_i
                                if t >= t_min and (t - 1) in n_i})

        t_true, d_true_mean, d_true_std, d_true_n = _plot_mean(
            true_series, CURVE_COLORS['y_true'], '-', r'True $\Delta\eta_i$', 'y_true', legend_added)
        t_model, d_model_mean, d_model_std, d_model_n = _plot_mean(
            model_series, CURVE_COLORS['y_model'], ':', r'Model $\Delta\eta_i$ (Sample Mean)', 'y_model',
            legend_added)

        results_list.append({
            "half": half,
            "sample_indices": indices,
            "t_model": t_model,
            "delta_model_mean": d_model_mean,
            "delta_model_std": d_model_std,
            "delta_model_n": d_model_n,
            "t_true": t_true,
            "delta_true_mean": d_true_mean,
            "delta_true_std": d_true_std,
            "delta_true_n": d_true_n,
        })

    plt.axhline(0, color='black', linewidth=0.8)
    base = r'One-Step Change in $\eta_i$' + ('' if even_or_odd != 2 else ': Estimator vs True')
    _finish(_title(base, even_or_odd, groups, samples), r'$\Delta$ Newly Infected ($\eta_i(t) - \eta_i(t-1)$)',
            split_t, "result_figures/delta_model_results.pdf",
            "result_figures/delta_model_data.pkl", results_list)


# ---------------------------------------------------------------------------
#
#  Identifiability plot: true vs. predicted n_i and n_r time-series,
#  each averaged across samples at each absolute t (± std band).
#
#    Pulls from these blocks in mfa_xy_data.txt:
#      - Given Newly Infected Ratio       (true n_i, already a ratio)
#      - Newly Recovered                  (true newly recovered, raw counts;
#                                          divided by that sample's node count)
#      - n_i Predicted (Identifiability)  (n_i_pred from reduced model)
#      - n_r Predicted (Identifiability)  (n_r_pred from inverting model)
#
#    show_samples=True also draws every sample's curves faintly behind the means.
#    t_min = 1 by default, for the same t = 0 reason as plot_model.
#
# ---------------------------------------------------------------------------
def _node_count(sample, default=200):
    try:
        n = int(sample.get('Number of nodes'))
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def plot_identifiability_results(samples, even_or_odd=2, t_min=1, show_samples=False):
    plt.figure(figsize=(12, 7))

    required = ('n_i Predicted (Identifiability)', 'n_r Predicted (Identifiability)')
    groups = _groups(samples, even_or_odd, require=required)
    split_t = _split_t(samples, groups, 'n_i Predicted (Identifiability)')

    results_list = []
    legend_added = set()

    for half, indices in groups.items():
        _check_homogeneous(samples, indices)
        per_quantity = {'n_i_true': [], 'n_i_pred': [], 'n_r_true': [], 'n_r_pred': []}

        for i in indices:
            sample = samples[i]
            n = _node_count(sample)
            per_quantity['n_i_pred'].append(_series(sample, 'n_i Predicted (Identifiability)'))
            per_quantity['n_r_pred'].append(_series(sample, 'n_r Predicted (Identifiability)'))
            per_quantity['n_i_true'].append(_series(sample, 'Given Newly Infected Ratio'))
            per_quantity['n_r_true'].append({t: v / n for t, v in _series(sample, 'Newly Recovered').items()})

        per_quantity = {q: [{t: v for t, v in s.items() if t >= t_min} for s in lst if s]
                        for q, lst in per_quantity.items()}

        if show_samples:
            for q, lst in per_quantity.items():
                for s in lst:
                    ts = sorted(s)
                    plt.plot(ts, [s[t] for t in ts], color=ID_COLORS[q], alpha=0.15, linewidth=1,
                             label='_nolegend_')

        styles = {
            'n_i_true': ('-', r'True $\eta_i$'),
            'n_i_pred': ('--', r'Predicted $\eta_i$'),
            'n_r_true': ('-', r'True $\eta_r$'),
            'n_r_pred': ('--', r'Predicted $\eta_r$'),
        }
        entry = {"half": half, "sample_indices": indices}
        for q, (ls, label) in styles.items():
            t, mean, std, count = _plot_mean(per_quantity[q], ID_COLORS[q], ls, label, q, legend_added)
            entry.update({f"{q}_t": t, f"{q}_mean": mean, f"{q}_std": std, f"{q}_n": count})
        results_list.append(entry)

    base = r'Identifiability: True vs Predicted $\eta_i$, $\eta_r$'
    _finish(_title(base, even_or_odd, groups, samples), 'Ratio', split_t,
            "result_figures/identifiability_n_i_n_r.pdf",
            "result_figures/plot_identifiability_n_i_n_r_data.pkl", results_list)


if __name__ == "__main__":
    samples = extract_mfa.parse_sample_data('experiment_data/mfa_xy_data.txt')
    plot_model(samples, even_or_odd=2)
    # delta_model(samples, even_or_odd=2)
    # plot_identifiability_results(samples, even_or_odd=2)