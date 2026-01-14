import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize
import random
import pickle 

# Global matplotlib settings
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

# Load all 5 consecutive samples
network0_samples = extract_mfa.parse_sample_data("experiment_data/yjmob0_runs.txt")
network1_samples = extract_mfa.parse_sample_data("experiment_data/yjmob1_runs.txt")
network2_samples = extract_mfa.parse_sample_data("experiment_data/yjmob2_runs.txt")
network3_samples = extract_mfa.parse_sample_data("experiment_data/yjmob3_runs.txt")
network4_samples = extract_mfa.parse_sample_data("experiment_data/yjmob4_runs.txt")
# File for optimization over all intervals together (with split point for quarantine beginning)
yjmob_full_samples = extract_mfa.parse_sample_data("experiment_data/yjmob5_runs.txt")

all_samples = [network0_samples, network1_samples, network2_samples, network3_samples, network4_samples]

post_quarantine_samples = all_samples[2:]  # Samples after quarantine begins

# Population
n = network0_samples[0]["Number of nodes"]

# Combine infected & informed, degree time-series across all post-quarantine samples
inf_inf_runs = []
k_q_runs = []
infection_runs = []
# Iterate vertically over runs
for i in range(len(post_quarantine_samples[0])):
    cur_inf_inf_run = []
    cur_k_q_run = []
    cur_inf_run = []
    for sample in post_quarantine_samples:
        # Combine pieces of inf & inf time-series from each sample
        cur_inf_inf = sample[i]["Informed and Infected"]["y"]
        cur_inf_inf = [val / n for val in cur_inf_inf]  # Normalize by population
        cur_inf_inf_run.extend(cur_inf_inf)
        # Combine pieces of dynamic degree time-series from each sample
        cur_k_q = sample[i]["Dynamic degree"]["y"]
        cur_k_q_run.extend(cur_k_q)
    inf_inf_runs.append(cur_inf_inf_run)
    k_q_runs.append(cur_k_q_run)

days_per_sample = 15
split_point = 30  # Quarantine begins after the second sample (day 30)

k_q_true_mean = np.mean(np.array(k_q_runs), axis=0)
k_q_std = np.std(np.array(k_q_runs), axis=0)
i_prime_mean = np.mean(np.array(inf_inf_runs), axis=0)
i_prime_std = np.std(np.array(inf_inf_runs), axis=0)

def plot_mfa_estimated_degree():
    plotting_samples = [sample[0] for sample in all_samples]

    def align_true_to_est(sample):
        x_est = np.array(sample["w1 Estimated"]["x"])
        y_est = np.array(sample["w1 Estimated"]["y"])

        x_true = np.array(sample["w1 True (Mean Node Degree)"]["x"])
        y_true = np.array(sample["w1 True (Mean Node Degree)"]["y"])

        mask = np.isin(x_true, x_est)
        return x_est, y_est, y_true[mask]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    piecewise_pre_color = "#ff7f0e"
    piecewise_post_color = "#d62728"

    true_interval_means = []

    # =============================
    # TRUE mean degree (piecewise) — SOLID
    # =============================
    for i, sample in enumerate(plotting_samples):
        x_local, _, y_true_local = align_true_to_est(sample)
        t_global = x_local + i * days_per_sample
        color = piecewise_pre_color if i < 2 else piecewise_post_color

        ax.plot(
            t_global,
            y_true_local,
            color=color,
            linestyle="-",
            linewidth=3
        )

    # TRUE pre/post means — SOLID
    pre_quarantine_mean = np.mean(true_interval_means[:2])
    post_quarantine_mean = np.mean(true_interval_means[2:])

    ax.hlines(
        pre_quarantine_mean,
        xmin=0,
        xmax=2 * days_per_sample,
        colors=piecewise_pre_color,
        linestyles="-",
        linewidth=4
    )

    ax.hlines(
        post_quarantine_mean,
        xmin=2 * days_per_sample,
        xmax=5 * days_per_sample,
        colors=piecewise_post_color,
        linestyles="-",
        linewidth=4
    )

    # =============================
    # ESTIMATED mean degree — DOTTED
    # =============================
    for i, sample in enumerate(plotting_samples):
        x_local, _, _ = align_true_to_est(sample)
        t_global = x_local + i * days_per_sample

        runs_interp = [
            np.interp(x_local, sample["w1 all runs"]["x"], run_y)
            for run_y in sample["w1 all runs"]["y"]
        ]

        runs_array = np.array(runs_interp)
        mean_est = runs_array.mean(axis=0)
        std_est = runs_array.std(axis=0)

        color = piecewise_pre_color if i < 2 else piecewise_post_color

        ax.plot(
            t_global,
            mean_est,
            color=color,
            linestyle="--",
            linewidth=3,
            label=r"$\langle k_0 \rangle$ (known network changes)" if i == 0 else
                  r"$\langle k_q \rangle$ (known network changes)" if i == 2 else None
        )

        ax.fill_between(
            t_global,
            mean_est - std_est,
            mean_est + std_est,
            color=color,
            alpha=0.25
        )

    # =============================
    # FULL YJMOB optimizations
    # =============================
    full_pre_color = "#2ca02c"
    full_post_color = "#9467bd"

    # --- Full pre ---
    full_pre = yjmob_full_samples[0]
    x_pre = np.array(full_pre["w1 Estimated"]["x"])
    runs_pre = np.array(full_pre["w1 all runs"]["y"])

    mean_pre = runs_pre.mean(axis=0)
    std_pre = runs_pre.std(axis=0)

    ax.plot(
        x_pre,
        mean_pre,
        color=full_pre_color,
        linestyle="--",
        linewidth=3.5,
        label=r"$\langle k_0 \rangle$ (SIRS dynamics only)"
    )

    ax.fill_between(
        x_pre,
        mean_pre - std_pre,
        mean_pre + std_pre,
        color=full_pre_color,
        alpha=0.20
    )

    x_true_pre = np.array(full_pre["w1 True (Mean Node Degree)"]["x"])
    y_true_pre = np.array(full_pre["w1 True (Mean Node Degree)"]["y"])
    mask_pre = np.isin(x_true_pre, x_pre)

    ax.plot(
        x_pre,
        y_true_pre[mask_pre],
        color=full_pre_color,
        linestyle="-",
        linewidth=3
    )

    # --- Full post ---
    full_post = yjmob_full_samples[1]
    x_post = np.array(full_post["w1 Estimated"]["x"])
    runs_post = np.array(full_post["w1 all runs"]["y"])

    mean_post = runs_post.mean(axis=0)
    std_post = runs_post.std(axis=0)

    ax.plot(
        x_post,
        mean_post,
        color=full_post_color,
        linestyle="--",
        linewidth=3.5,
        label=r"$\langle k_q \rangle$ (SIRS dynamics only)"
    )

    ax.fill_between(
        x_post,
        mean_post - std_post,
        mean_post + std_post,
        color=full_post_color,
        alpha=0.20
    )

    x_true_post = np.array(full_post["w1 True (Mean Node Degree)"]["x"])
    y_true_post = np.array(full_post["w1 True (Mean Node Degree)"]["y"])
    mask_post = np.isin(x_true_post, x_post)

    ax.plot(
        x_post,
        y_true_post[mask_post],
        color=full_post_color,
        linestyle="-",
        linewidth=3
    )

    ax.axvline(
        split_point,
        color="gray",
        linestyle="--",
        linewidth=2,
        label="Quarantine begins"
    )

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Mean Node Degree ⟨k⟩")
    ax.set_title("Estimated Degree on YJMob100k Dataset")

    ax.set_xlim(0, 75)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.30),
    ncol=2)

    plt.tight_layout()
    plt.savefig("result_figures/YJMOB_k_est.pdf", format="pdf", bbox_inches="tight")
    plt.show()
    plt.close(fig)


plot_mfa_estimated_degree()

#----------------
#
#  Determine quarantine adherence from MFA estimated degrees on the dataset
#
#----------------

# First 2 networks: pre-quarantine
pre_q_sample0 = network0_samples[0]
pre_q_sample1 = network1_samples[0]
k_0_est_1 = pre_q_sample0["w1 True (Mean Node Degree)"]["y"][-1]
k_0_est_2 = pre_q_sample1["w1 True (Mean Node Degree)"]["y"][-1]
# Assumption: networks are relatively unchanged before quarantining begins
k_0 = (k_0_est_1 + k_0_est_2) / 2

# -------------
# Joint optimization (S, adherence) per-run
# -------------
def mse_loss(params, i_prime_cur):
    S, adherence_val = params
    k_q_est = np.array([k_0 * (1 - S * adherence_val * i_prime_cur[t]) for t in range(len(i_prime_mean))])
    mse = np.mean((k_q_true_mean - k_q_est) ** 2)
    return mse

# ---------------------------
#
# CUMULATIVE OPTIMIZATION: estimate adherence time-series per run
#
# ---------------------------

num_runs = len(inf_inf_runs)
num_postq_intvs = 3  # Number of post-quarantine simulations
T_post = 45  # Total days after quarantine begins (3 samples of 15 days each)
S_RANGE = (1, 2)
ADHERENCE_RANGE = (0, 1)
adhering_proportion = float(network2_samples[0]["Adhering proportion"])

# Compute for each run r: adh_hat_r[t] = estimate using data up to t
cumulative_adh = np.zeros((num_runs, T_post))  # runs x time

# Treat i', <k_q>_t as one time-series per run, irrespective of intervals from dataset
# Iterate over runs
for r in range(num_runs):
    # Infected and informed time-series for this run
    i_prime_run = inf_inf_runs[r]  # length T
    # Dynamic degree time-series for this run
    k_q_run = k_q_runs[r]  # length T

    #--------------
    # Optimize adherence estimate, scale factor for each t
    #--------------
    for t in range(1, T_post + 1):     # use first t points (t from 1..T)
        # Define cumulative slices of the time-series
        i_prime_subset = np.array(i_prime_run[:t])
        k_q_true_subset = np.array(k_q_run[:t])

        # Objective function for this slice: MSE between true k_q and estimated k_q for the respective run
        def mse_slice(params):
            # Parameters to optimize: S, adherence
            S_val, adh_val = params
            k_q_est_slice = k_0 * (1 - S_val * adh_val * i_prime_subset)
            
            return float(np.mean((k_q_true_subset - k_q_est_slice) ** 2))

        res = minimize(mse_slice, x0=[random.uniform(1,2), random.uniform(0,1)], bounds=[S_RANGE, ADHERENCE_RANGE], method='L-BFGS-B')
        # store adherence estimate
        cumulative_adh[r, t-1] = float(res.x[1])

# Compute mean and std across runs for each t
adh_mean = np.mean(cumulative_adh, axis=0)
adh_std = np.std(cumulative_adh, axis=0)

# Shift t values by split_point
t_vals = np.arange(split_point, split_point + T_post)

# ---------------------------
# Plot cumulative adherence
# ---------------------------
fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

ax.plot(t_vals, adh_mean, linewidth=2.5, color='#ff7f0e',
        label='Estimated adherence (mean)')
ax.fill_between(
    t_vals,
    adh_mean - adh_std,
    adh_mean + adh_std,
    color='#ff7f0e',
    alpha=0.25,
    label='± 1 std over runs'
)

# True adherence reference
ax.hlines(
    y=adhering_proportion,
    xmin=t_vals[0],
    xmax=t_vals[-1],
    colors='blue',
    linestyles='--',
    linewidth=2,
    label='True adherence'
)

ax.set_xlabel('Time (days)')
ax.set_ylabel('Estimated adherence')
ax.set_title('Cumulative Adherence Estimate')
ax.set_ylim(0, 1.05)
ax.grid(True, alpha=0.3)
ax.legend(frameon=False)

plt.tight_layout()

plt.savefig(
    "result_figures/YJMOB_adherence.pdf",
    format="pdf",
    bbox_inches="tight"
)
plt.show()

plt.close(fig)

# ---------------------------
# Save results to PKL
# ---------------------------
PKL_FILENAME = "result_figures/cumulative_adherence_results.pkl"  # <-- Added definition

save_dict = {
    "k_0": float(k_0),
    "split_point": int(split_point),
    "adhering_proportion": float(adhering_proportion),
    "population": int(n),
    "num_simulations": int(num_runs),
    "time_after_q": int(T_post),
    # "i_prime_mean": i_prime_mean.tolist(),
    # "inf_inf_runs": [run.tolist() for run in inf_inf_runs],
    # "k_q_true_mean": k_q_true_mean.tolist(),
    # "k_q_true_runs": [run.tolist() for run in k_q_runs],
    # "cumulative_adh_runs": cumulative_adh.tolist(),
    # "cumulative_adh_mean": adh_mean.tolist(),
    # "cumulative_adh_std": adh_std.tolist(),
    # "t_vals": t_vals.tolist()
}

# safe write
try:
    with open(PKL_FILENAME, "wb") as f:
        pickle.dump(save_dict, f)
    print(f"Results successfully saved to {PKL_FILENAME}")
except Exception as e:
    print("Error saving PKL:", e)