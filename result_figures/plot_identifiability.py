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
def plot_identifiability_results(samples, even_or_odd=2):
    plt.figure(figsize=(12, 7))

    results_list = []

    for i, sample in enumerate(samples):

        if not (even_or_odd == 2 or i % 2 == even_or_odd):
            continue

        if 'y_pred all runs' not in sample or 'y_true values' not in sample:
            continue

        y_pred_runs = sample['y_pred all runs']['y']
        y_true_vals = sample['y_true values']['y']
        t_vals = np.array(sample['y_true values']['x'])

        y_pred_runs = [run for run in y_pred_runs if len(run) > 0]
        if not y_pred_runs or not y_true_vals:
            continue

        # Align run lengths (pad with last value if necessary)
        max_len = max(len(run) for run in y_pred_runs)
        for run in y_pred_runs:
            while len(run) < max_len:
                run.append(run[-1])

        y_pred_arr = np.array(y_pred_runs)
        y_pred_mean = np.mean(y_pred_arr, axis=0)
        y_pred_std = np.std(y_pred_arr, axis=0)
        y_true_arr = np.array(y_true_vals)

        # --- Plot model eval (true params) and retrieve its color ---
        line = plt.plot(
            t_vals, y_true_arr,
            label=f'Model eval (β = {0.15 - 0.015 * i:.3f})', linestyle='-'
        )[0]

        color = line.get_color()

        # Estimator mean ± std in the same color, dashed
        plt.plot(
            t_vals, y_pred_mean,
            color=color, linestyle='--',
            label=f'Estimator mean (β = {0.15 - 0.015 * i:.3f})'
        )
        plt.fill_between(
            t_vals, y_pred_mean - y_pred_std, y_pred_mean + y_pred_std,
            alpha=0.15, color=color
        )

        results_list.append({
            "sample_index": i,
            "time_points": t_vals,
            "y_true": y_true_arr,
            "y_pred_mean": y_pred_mean,
            "y_pred_std": y_pred_std,
        })

    plt.xlabel('Time (days)')
    plt.ylabel(r'Newly Infected ($n_i$)')
    if even_or_odd == 0:
        plt.title(r'Identifiability Test (Pre-Quarantine)')
    elif even_or_odd == 1:
        plt.title(r'Identifiability Test (Post-Quarantine)')
    else:
        plt.title(r'Identifiability Test: Estimator vs Model Eval with True Params')
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

if __name__ == "__main__":
    samples = extract_mfa.parse_sample_data('experiment_data/mfa_xy_data.txt')
    plot_identifiability_results(samples, even_or_odd=2)
