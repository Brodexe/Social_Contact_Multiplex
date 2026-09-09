import os
import pickle
import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

# ---------------------------
#  Settings & output filename
# ---------------------------
PKL_FILENAME_TEMPLATE = "result_figures/analyze_quarantine_dynamics_data_{label}.pkl"

# Data files to compare, one per true adherence level
READ_FILES = [
    "experiment_data/a_0.2",
    "experiment_data/a_0.4",
    "experiment_data/a_0.6",
]
RUN_COLORS = ['#1f77b4', '#2ca02c', '#d62728']

# Global matplotlib settings for publication-quality figures
plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 16,
    "lines.linewidth": 2.5,
})

# Consistent figure size for all plots
FIGURE_SIZE_LINE = (10, 6)
FIGURE_SIZE_BAR = (14, 8)

# Parameter bounds
S_RANGE = (1.0, 2.0)
ADHERENCE_RANGE = (0.0, 1.0)

# Proportion of informed-and-infected below which a day counts as "low infected" (tweakable)
LOW_INFECTED_THRESHOLD = 0.05
# Value plugged in for f while solving for adherence on low-infected days
FIXED_F_LOW = 2.0

# Index (0-based) into the post-quarantine series used as the anchor point for
# estimate_a_then_f -- index 1 is the 2nd point after quarantine begins.
ANCHOR_IDX = 1

# For the adherence bar plot: per run, only the window from quarantine start until
# newly-infected ratio first drops below this is considered (the noisy/degenerate tail
# is dropped). Loosened from an initial 0.025 -- at 0.025 nearly every run in the
# current (small, "for faster testing") dataset was already below threshold within a
# day or two of quarantine starting, leaving almost nothing to fit.
NEW_INFECTION_CUTOFF = 0.01
# Runs truncated to fewer than this many post-quarantine timesteps are dropped as too
# short to fit; surviving runs are then cut down to exactly this length so every run
# within an adherence level lines up.
MIN_TRUNCATED_LENGTH = 5


def two_stage_estimate(i_prime_series, k_q_series, k_0, low_threshold=LOW_INFECTED_THRESHOLD,
                        fixed_f_low=FIXED_F_LOW, f_range=S_RANGE, adherence_range=ADHERENCE_RANGE):
    # Jointly fitting f and adherence is not identifiable: only their product enters
    # the k_q model, so many (f, adherence) pairs reproduce the same trajectory. Instead:
    #   Stage 1: on days where informed-and-infected is low, treat that as a proxy for
    #            low infection overall, plug in a fixed f, and solve for adherence alone.
    #   Stage 2: with adherence fixed at its Stage 1 value, solve for f alone using the
    #            remaining days.
    i_prime_series = np.asarray(i_prime_series)
    k_q_series = np.asarray(k_q_series)

    low_mask = i_prime_series <= low_threshold
    stage1_mask = low_mask if np.any(low_mask) else np.ones_like(low_mask)

    res_a = minimize(
        lambda params: float(np.mean((k_q_series[stage1_mask]
                                       - k_0 * (1 - fixed_f_low * params[0] * i_prime_series[stage1_mask])) ** 2)),
        x0=[0.5], bounds=[adherence_range], method='L-BFGS-B'
    )
    adherence_est = float(res_a.x[0])

    stage2_mask = ~low_mask if np.any(~low_mask) else np.ones_like(low_mask)
    res_f = minimize(
        lambda params: float(np.mean((k_q_series[stage2_mask]
                                       - k_0 * (1 - params[0] * adherence_est * i_prime_series[stage2_mask])) ** 2)),
        x0=[1.5], bounds=[f_range], method='L-BFGS-B'
    )
    f_est = float(res_f.x[0])

    return adherence_est, f_est


def estimate_a_then_f(i_prime_run, k_q_run, k_0, f_anchor=FIXED_F_LOW, anchor_idx=ANCHOR_IDX):
    # k_q = k_0 * (1 - f * a * i_prime) only pins down the product f*a, not f
    # and a separately -- except near the start of quarantining, where f is
    # known exactly (=2, an initial-condition property). Anchor there to
    # solve for p = f*a as a single variable, then divide by the known f to
    # recover adherence.
    i_prime_run = np.asarray(i_prime_run, dtype=float)
    k_q_run = np.asarray(k_q_run, dtype=float)

    p0 = (1.0 - k_q_run[anchor_idx] / k_0) / i_prime_run[anchor_idx]
    a_est = p0 / f_anchor

    # Work backwards: with adherence pinned at a_est, solve for f at every
    # timestep using the same k_q relation. Since adherence is actually
    # constant, f should stay at f_anchor throughout; any drift away from it
    # is the degeneracy re-emerging away from the anchor point.
    with np.errstate(divide='ignore', invalid='ignore'):
        f_series = (1.0 - k_q_run / k_0) / (a_est * i_prime_run)
    f_series[i_prime_run == 0] = np.nan

    return a_est, f_series


def truncate_at_new_infection_cutoff(i_prime_run, k_q_run, new_infected_ratio_run, cutoff=NEW_INFECTION_CUTOFF):
    # Keep only the window from quarantine start through the first day newly-infected
    # ratio drops below cutoff (inclusive) -- once infections have died down the k_q
    # signal driving the f/adherence fit is dominated by noise, so the tail is dropped.
    new_infected_ratio_run = np.asarray(new_infected_ratio_run)
    below = np.where(new_infected_ratio_run < cutoff)[0]
    end = int(below[0]) + 1 if below.size > 0 else len(new_infected_ratio_run)
    return np.asarray(i_prime_run)[:end], np.asarray(k_q_run)[:end], end


def compute_adherence_bar_estimate(res, f_anchor=FIXED_F_LOW, anchor_idx=ANCHOR_IDX,
                                    cutoff=NEW_INFECTION_CUTOFF, min_length=MIN_TRUNCATED_LENGTH):
    i_prime_runs = res["inf_inf_runs"]
    k_q_runs = res["k_q_runs"]
    new_infected_ratio_runs = res["new_infected_ratio_runs"]

    # Per-run truncation leaves runs of inconsistent length -- drop anything too short
    # to fit, then cut the survivors down to a common length so they can be averaged.
    surviving_runs = []
    for i_prime_run, k_q_run, new_infected_ratio_run in zip(i_prime_runs, k_q_runs, new_infected_ratio_runs):
        i_prime_trunc, k_q_trunc, length = truncate_at_new_infection_cutoff(
            i_prime_run, k_q_run, new_infected_ratio_run, cutoff=cutoff)
        if length >= min_length:
            surviving_runs.append((i_prime_trunc[:min_length], k_q_trunc[:min_length]))

    num_surviving = len(surviving_runs)
    num_total = len(i_prime_runs)

    if num_surviving == 0:
        print(f"WARNING: no runs long enough for adherence bar (true a = {res['adhering_proportion']}); skipping.")
        return None

    a_est_lst = [
        estimate_a_then_f(i_prime_trunc, k_q_trunc, res["k_0"], f_anchor=f_anchor, anchor_idx=anchor_idx)[0]
        for i_prime_trunc, k_q_trunc in surviving_runs
    ]
    a_est_mean = float(np.mean(a_est_lst))

    return a_est_mean, num_surviving, num_total


def plot_adherence_bar_combined(results, colors=RUN_COLORS, f_anchor=FIXED_F_LOW, anchor_idx=ANCHOR_IDX,
                                 cutoff=NEW_INFECTION_CUTOFF, min_length=MIN_TRUNCATED_LENGTH):
    # One grouped bar chart (target vs. observed adherence, per true-adherence level)
    # instead of a separate figure per level.
    true_a_lst = []
    target_lst = []
    observed_lst = []
    bar_colors = []
    for res, color in zip(results, colors):
        estimate = compute_adherence_bar_estimate(
            res, f_anchor=f_anchor, anchor_idx=anchor_idx, cutoff=cutoff, min_length=min_length)
        if estimate is None:
            continue
        a_est_mean, _, _ = estimate

        true_a_lst.append(res['adhering_proportion'])
        target_lst.append(res['adhering_proportion'])
        observed_lst.append(a_est_mean)
        bar_colors.append(color)

    x = np.arange(len(true_a_lst))
    width = 0.35

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_BAR)

    bars_target = ax.bar(x - width / 2, target_lst, width, label='Target $a$', color='#7f7f7f')
    bars_obs = ax.bar(x + width / 2, observed_lst, width, label=r'Observed $\hat{a}$', color=bar_colors)
    ax.bar_label(bars_target, fmt='%.3f')
    ax.bar_label(bars_obs, fmt='%.3f')

    ax.set_xticks(x)
    ax.set_xticklabels([f'{a:.1f}' for a in true_a_lst])
    ax.set_xlabel('True adherence')
    ax.set_ylabel('Adherence')
    ymax = max(target_lst + observed_lst)
    ax.set_ylim(0, ymax * 1.15)
    ax.set_title('Adherence estimates across true adherence levels')
    ax.legend()
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig('result_figures/f_degeneration_combined.pdf', bbox_inches='tight')
    plt.close()


def analyze_file(read_file):
    # ---------------------------
    #  Load samples
    # ---------------------------
    samples = extract_mfa.parse_sample_data(read_file)

    # Shorten every sample to first 70 time steps (T = 100 days, quarantine at day 30) for faster testing
    #   Can comment out for full runs
    for sample in samples:
        for key in sample:
            if isinstance(sample[key], dict) and 'y' in sample[key]:
                sample[key]['y'] = sample[key]['y'][:70]
                sample[key]['x'] = sample[key]['x'][:70]

    k_0 = samples[0]['w1 True (Mean Node Degree)']['y'][-1]
    k_q = samples[1]['w1 True (Mean Node Degree)']['y'][-1]
    split_point = int(samples[1]['w1 True (Mean Node Degree)']['x'][0])
    adhering_proportion = samples[1].get('Adhering proportion', None)
    population = samples[0]['Number of nodes']

    print(f"\n=== {read_file} ===")
    print("k_0:", k_0)
    print("k_q:", k_q)
    print("split_point:", split_point)
    print("adhering_proportion:", adhering_proportion)
    print("population:", population)

    # Only post-quarantine (odd) samples count as runs
    num_simulations_total = len(samples)
    assert num_simulations_total % 2 == 0, f"Number of samples should be even for split optimizations. Number: {len(samples)}"
    num_simulations = int(num_simulations_total / 2)

    # ---------------------------
    #  Build list of informed&infected proportions per run (post-quarantine)
    # ---------------------------
    inf_inf_runs = []
    for r in range(num_simulations):
        index = r * 2 + 1  # odd indices
        informed_and_infected = samples[index]['Informed and Infected']['y']
        proportions = [x / population for x in informed_and_infected]
        inf_inf_runs.append(proportions)

    # Collection of i_prime curves
    inf_inf_runs = np.array(inf_inf_runs)  # shape: (runs, T_after_q)
    T = inf_inf_runs.shape[1]

    # Average informed&infected proportion over runs (i_prime)
    i_prime = np.mean(inf_inf_runs, axis=0)  # shape: (T,)

    # Compute true k_q time-series (average over runs)
    k_q_runs = []
    for r in range(num_simulations):
        index = r * 2 + 1
        k_q_lst = samples[index]['Dynamic degree']['y']
        k_q_runs.append(k_q_lst)

    k_q_true_mean = np.mean(k_q_runs, axis=0)  # shape: (T,)
    k_q_true_std = np.std(k_q_runs, axis=0)

    # Newly-infected ratio per run (post-quarantine), used to find where the epidemic
    # has died down enough that the k_q signal degenerates (see plot_adherence_bar).
    new_infected_ratio_runs = []
    for r in range(num_simulations):
        index = r * 2 + 1
        new_infected_ratio_runs.append(samples[index]['Given Newly Infected Ratio']['y'])

    # -------------
    #  Two-stage (f, adherence) estimation per run
    # -------------
    best_S_lst = []
    best_adh_lst = []
    for r in range(num_simulations):
        adherence_est, f_est = two_stage_estimate(inf_inf_runs[r], k_q_runs[r], k_0)
        best_S_lst.append(f_est)
        best_adh_lst.append(adherence_est)

    best_S = float(np.mean(best_S_lst))
    best_adherence = float(np.mean(best_adh_lst))
    S_std = float(np.std(best_S_lst))
    adherence_std = float(np.std(best_adh_lst))

    print("Best S (avg over runs):", best_S)
    print("Best Adherence (avg over runs):", best_adherence)
    print("S std:", S_std, "adherence std:", adherence_std)
    print("Approximate adherence confidence interval (95%):", (best_adherence - 1.96 * (adherence_std / np.sqrt(num_simulations)),
                                             best_adherence + 1.96 * (adherence_std / np.sqrt(num_simulations))))

    k_q_est_best = np.array([k_0 * (1 - best_S * best_adherence * i_prime[t]) for t in range(len(i_prime))])

    # per-run k_q estimates for computing mean/std bands
    k_q_est_runs = []
    for r in range(num_simulations):
        run_est = np.array([k_0 * (1 - best_S_lst[r] * best_adh_lst[r] * inf_inf_runs[r][t]) for t in range(len(i_prime))])
        k_q_est_runs.append(run_est)
    k_q_est_runs = np.array(k_q_est_runs)
    k_q_est_mean = np.mean(k_q_est_runs, axis=0)
    k_q_est_std = np.std(k_q_est_runs, axis=0)

    xvals = np.arange(split_point, split_point + T)

    # ---------------------------
    #
    # CUMULATIVE OPTIMIZATION: estimate adherence time-series per run
    #
    # ---------------------------
    cumulative_adh = np.zeros((num_simulations, T))  # runs x time
    for r in range(num_simulations):
        i_prime_run = inf_inf_runs[r]
        k_q_run = k_q_runs[r]
        for t in range(1, T + 1):     # use first t points (t from 1..T)
            adh_est, _ = two_stage_estimate(i_prime_run[:t], k_q_run[:t], k_0)
            cumulative_adh[r, t - 1] = adh_est

    adh_mean = np.mean(cumulative_adh, axis=0)
    adh_std = np.std(cumulative_adh, axis=0)
    t_vals = np.arange(split_point, split_point + T)

    return {
        "read_file": read_file,
        "k_0": float(k_0),
        "k_q": float(k_q),
        "split_point": int(split_point),
        "adhering_proportion": adhering_proportion,
        "population": int(population),
        "num_simulations": int(num_simulations),
        "time_after_q": int(T),
        "i_prime_mean": i_prime,
        "inf_inf_runs": inf_inf_runs,
        "xvals": xvals,
        "k_q_true_mean": k_q_true_mean,
        "k_q_true_std": k_q_true_std,
        "k_q_runs": np.array(k_q_runs),
        "new_infected_ratio_runs": new_infected_ratio_runs,
        "best_S_lst": best_S_lst,
        "best_adh_lst": best_adh_lst,
        "best_S_mean": best_S,
        "best_adh_mean": best_adherence,
        "best_S_std": S_std,
        "best_adh_std": adherence_std,
        "k_q_est_best": k_q_est_best,
        "k_q_est_runs": k_q_est_runs,
        "k_q_est_mean": k_q_est_mean,
        "k_q_est_std": k_q_est_std,
        "cumulative_adh": cumulative_adh,
        "adh_mean": adh_mean,
        "adh_std": adh_std,
        "t_vals": t_vals,
    }


# ---------------------------
#  Run analysis for every adherence level
# ---------------------------
results = [analyze_file(read_file) for read_file in READ_FILES]

# ---------------------------
# Plot <k_q> true vs estimated, one figure per adherence level
# ---------------------------
for res in results:
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    ax.plot(res["xvals"], res["k_q_true_mean"], label=r'True $\langle k_q \rangle$', color='#1f77b4')
    ax.plot(res["xvals"], res["k_q_est_best"], label=r'Estimated $\langle k_q \rangle$ (best params)',
            color='#ff7f0e', linestyle='--')

    ax.fill_between(res["xvals"], res["k_q_est_mean"] - res["k_q_est_std"], res["k_q_est_mean"] + res["k_q_est_std"],
                     color='#ff7f0e', alpha=0.25, label=r'Estimate $\pm$ 1 std (all runs)')
    ax.fill_between(res["xvals"], res["k_q_true_mean"] - res["k_q_true_std"], res["k_q_true_mean"] + res["k_q_true_std"],
                     color='#1f77b4', alpha=0.2, label=r'True $\pm$ 1 std')

    ax.set_xlabel('Time (days)')
    ax.set_ylabel(r'$\langle k_q \rangle$')
    ax.set_title(r'$\langle k_q \rangle$ Parameter Optimization vs Ground Truth (adherence = %.1f)' % res["adhering_proportion"])
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    label = f'a{res["adhering_proportion"]:.1f}'
    plt.savefig(f'result_figures/kq_true_vs_estimated_{label}.pdf', bbox_inches='tight')
    plt.close()

plot_adherence_bar_combined(results)

# ---------------------------
# Plot cumulative adherence estimates for all adherence levels together
# ---------------------------
fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

for res, color in zip(results, RUN_COLORS):
    label = res["adhering_proportion"]
    adh_mean_plot = res["adh_mean"]

    ax.plot(
        res["t_vals"], adh_mean_plot, color=color, linestyle='--',
        label=f'Estimated (true adherence = {label:.1f})'
    )
    ax.fill_between(
        res["t_vals"], adh_mean_plot - res["adh_std"], adh_mean_plot + res["adh_std"],
        color=color, alpha=0.2
    )
    ax.hlines(
        y=res["adhering_proportion"], xmin=res["t_vals"][0], xmax=res["t_vals"][-1],
        colors=color, linestyles='solid', alpha=0.6
    )

ax.set_xlabel('Time (days)')
ax.set_ylabel('Estimated adherence')
ax.set_title('Cumulative Adherence Estimate Across Adherence Levels')
ax.set_ylim(0, 1.05)
ax.legend()
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('result_figures/adherence_comparison.pdf', bbox_inches='tight')
plt.show()

plt.close()


# ---------------------------
# Save results to PKL, one per adherence level
# ---------------------------
for res in results:
    label = f'a{res["adhering_proportion"]:.1f}'
    save_dict = {
        "k_0": res["k_0"],
        "k_q": res["k_q"],
        "split_point": res["split_point"],
        "adhering_proportion": res["adhering_proportion"],
        "population": res["population"],
        "num_simulations": res["num_simulations"],
        "time_after_q": res["time_after_q"],
        "i_prime_mean": res["i_prime_mean"].tolist(),
        "inf_inf_runs": res["inf_inf_runs"].tolist(),
        "k_q_true": res["k_q_true_mean"].tolist(),
        "best_S_lst": [float(x) for x in res["best_S_lst"]],
        "best_adh_lst": [float(x) for x in res["best_adh_lst"]],
        "best_S_mean": res["best_S_mean"],
        "best_adh_mean": res["best_adh_mean"],
        "best_S_std": res["best_S_std"],
        "best_adh_std": res["best_adh_std"],
        "k_q_est_runs": res["k_q_est_runs"].tolist(),
        "k_q_est_mean": res["k_q_est_mean"].tolist(),
        "k_q_est_std": res["k_q_est_std"].tolist(),
        "cumulative_adh_runs": res["cumulative_adh"].tolist(),
        "cumulative_adh_mean": res["adh_mean"].tolist(),
        "cumulative_adh_std": res["adh_std"].tolist(),
        "t_vals": res["t_vals"].tolist(),
    }

    try:
        with open(PKL_FILENAME_TEMPLATE.format(label=label), "wb") as f:
            pickle.dump(save_dict, f)
    except Exception as e:
        print("Error saving PKL:", e)
