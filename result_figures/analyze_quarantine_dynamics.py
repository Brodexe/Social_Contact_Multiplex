import os
import pickle
import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

# ---------------------------
#  Settings & output filename
# ---------------------------
PKL_FILENAME = "result_figures/analyze_quarantine_dynamics_data.pkl"

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

read_file = "experiment_data/mfa_xy_data.txt"
# read_file = ("experiment_data/a_1.0")
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

# k_0 = samples[0]['w1 True (Mean Node Degree)']['y'][-1]
k_0 = samples[0]['w1 Estimated']['y'][-1]
# k_q = samples[1]['w1 True (Mean Node Degree)']['y'][-1]
k_q = samples[1]['w1 Estimated']['y'][-1]
split_point = int(samples[1]['w1 True (Mean Node Degree)']['x'][0])
adhering_proportion = samples[1].get('Adhering proportion', None)
population = samples[0]['Number of nodes']

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

# --------------
#
#  Naive adherence calculation check: Simple deviation of k_q from k_eff
#
# --------------

# Expected degree under full adherence
def k_expected(informed_and_infected, current_time):
    assert current_time <= len(informed_and_infected), "Current time exceeds data length"
    k_expected_t = [k_0 * (1 - (2 * informed_and_infected[time]))
                    for time in range(current_time)]
    expected_k = (1 / len(k_expected_t)) * sum(k_expected_t)
    return expected_k

# Compute adherence estimates per run using naive formula
adherence_ests = []
for s in range(num_simulations):
    k_eff = k_expected(inf_inf_runs[s], T)

    adherence_est = 1 - ((k_q - k_eff) / (k_q)) if k_q != 0 else 0
    adherence_ests.append(adherence_est)

adherence_ests = np.array(adherence_ests)
adherence_mean = float(np.mean(adherence_ests))
print("Naive approximation for adherence (avg over runs):", adherence_mean)

# Compute true k_q time-series (average over runs)
k_q_runs = []
for r in range(num_simulations):
    index = r * 2 + 1
    k_q_lst = samples[index]['Dynamic degree']['y']
    k_q_runs.append(k_q_lst)

k_q_true_mean = np.mean(k_q_runs, axis=0)  # shape: (T,)
k_q_true_std = np.std(k_q_runs, axis=0)

# -------------
#
#  Two-stage (f, adherence) estimation per run
#
#  Jointly fitting f and adherence is not identifiable: only their product enters
#  the k_q model, so many (f, adherence) pairs reproduce the same trajectory. Instead:
#    Stage 1: on days where informed-and-infected is low, treat that as a proxy for
#             low infection overall, plug in a fixed f, and solve for adherence alone.
#    Stage 2: with adherence fixed at its Stage 1 value, solve for f alone using the
#             remaining days.
#
# -------------

# Parameter bounds
S_RANGE = (1.0, 2.0)
ADHERENCE_RANGE = (0.0, 1.0)

# Proportion of informed-and-infected below which a day counts as "low infected" (tweakable)
LOW_INFECTED_THRESHOLD = 0.05
# Value plugged in for f while solving for adherence on low-infected days
FIXED_F_LOW = 2.0

def two_stage_estimate(i_prime_series, k_q_series, low_threshold=LOW_INFECTED_THRESHOLD,
                        fixed_f_low=FIXED_F_LOW, f_range=S_RANGE, adherence_range=ADHERENCE_RANGE):
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

# List of optimal parameters per run
best_S_lst = []
best_adh_lst = []

# Iterate over runs in samples
for r in range(num_simulations):
    adherence_est, f_est = two_stage_estimate(inf_inf_runs[r], k_q_runs[r])
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

# ---------------------------
# Plot <k_q> true vs estimated
# ---------------------------
fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

# Shift x values by split_point
xvals = np.arange(split_point, split_point + T)

ax.plot(
    xvals,
    k_q_true_mean,
    label=r'True $\langle k_q \rangle$',
    color='#1f77b4'
)

ax.plot(
    xvals,
    k_q_est_best,
    label=r'Estimated $\langle k_q \rangle$ (best params)',
    color='#ff7f0e',
    linestyle='--'
)

# Std band for estimates
ax.fill_between(
    xvals,
    k_q_est_mean - k_q_est_std,
    k_q_est_mean + k_q_est_std,
    color='#ff7f0e',
    alpha=0.25,
    label=r'Estimate $\pm$ 1 std (all runs)'
)

# Std band for true k_q
ax.fill_between(
    xvals,
    k_q_true_mean - k_q_true_std,
    k_q_true_mean + k_q_true_std,
    color='#1f77b4',
    alpha=0.2,
    label=r'True $\pm$ 1 std'
)

ax.set_xlabel('Time (days)')
ax.set_ylabel(r'$\langle k_q \rangle$')
ax.set_title(r'$\langle k_q \rangle$ Parameter Optimization vs Ground Truth')
ax.legend()
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('result_figures/kq_true_vs_estimated.pdf', bbox_inches='tight')
plt.show()

plt.close()

# ---------------------------
#
# CUMULATIVE OPTIMIZATION: estimate adherence time-series per run
#
# ---------------------------

# Compute for each run r: adh_hat_r[t] = estimate using data up to t
cumulative_adh = np.zeros((num_simulations, T))  # runs x time

# Iterate over runs in samples
for r in range(num_simulations):
    # Infected and informed time-series for this run
    i_prime_run = inf_inf_runs[r]  # length T
    # Dynamic degree time-series for this run
    k_q_run = k_q_runs[r]  # length T

    #--------------
    # Two-stage adherence/f estimate for each cumulative window
    #--------------
    for t in range(1, T + 1):     # use first t points (t from 1..T)
        adh_est, _ = two_stage_estimate(i_prime_run[:t], k_q_run[:t])
        cumulative_adh[r, t-1] = adh_est

# Compute mean and std across runs for each t
adh_mean = np.mean(cumulative_adh, axis=0)
adh_std = np.std(cumulative_adh, axis=0)

# Shift t values by split_point
t_vals = np.arange(split_point, split_point + T)

# ---------------------------
# Plot cumulative adherence
# ---------------------------
fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

ax.plot(
    t_vals,
    adh_mean,
    color='#ff7f0e',
    linestyle='--',
    label='Estimated adherence (mean)'
)

ax.fill_between(
    t_vals,
    adh_mean - adh_std,
    adh_mean + adh_std,
    color='#ff7f0e',
    alpha=0.25,
    label=r'$\pm$ 1 std over runs'
)

# Horizontal line: true adherence
ax.hlines(
    y=adhering_proportion,
    xmin=t_vals[0],
    xmax=t_vals[-1],
    colors='black',
    linestyles='solid',
    label='True adherence'
)

ax.set_xlabel('Time (days)')
ax.set_ylabel('Estimated adherence')
ax.set_title('Cumulative Adherence Estimate')
ax.set_ylim(0, 1.05)
ax.legend()
ax.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig('result_figures/adherence.pdf', bbox_inches='tight')
plt.show()

plt.close()


# ---------------------------
# Save results to PKL
# ---------------------------
save_dict = {
    "k_0": float(k_0),
    "k_q": float(k_q),
    "split_point": int(split_point),
    "adhering_proportion": adhering_proportion,
    "population": int(population),
    "num_simulations": int(num_simulations),
    "time_after_q": int(T),
    "i_prime_mean": i_prime.tolist(),
    "inf_inf_runs": inf_inf_runs.tolist(),
    "k_q_true": k_q_true_mean.tolist(),
    "best_S_lst": [float(x) for x in best_S_lst],
    "best_adh_lst": [float(x) for x in best_adh_lst],
    "best_S_mean": best_S,
    "best_adh_mean": best_adherence,
    "best_S_std": S_std,
    "best_adh_std": adherence_std,
    "k_q_est_runs": k_q_est_runs.tolist(),
    "k_q_est_mean": k_q_est_mean.tolist(),
    "k_q_est_std": k_q_est_std.tolist(),
    "cumulative_adh_runs": cumulative_adh.tolist(),
    "cumulative_adh_mean": adh_mean.tolist(),
    "cumulative_adh_std": adh_std.tolist(),
    "t_vals": t_vals.tolist()
}

# safe write
try:
    with open(PKL_FILENAME, "wb") as f:
        pickle.dump(save_dict, f)
except Exception as e:
    print("Error saving PKL:", e)
