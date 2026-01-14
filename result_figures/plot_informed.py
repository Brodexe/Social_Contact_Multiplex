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
    "lines.linewidth": 2.5,
})

FIGURE_SIZE_LINE = (10, 6)

read_file = "experiment_data/mfa_xy_data.txt"

samples = extract_mfa.parse_sample_data(read_file)

# Get split point
split_point = int(samples[1]['Informed']['x'][0])

# Collect informed runs (all odd samples)
informed_runs = []
for i, sample in enumerate(samples):
    if i % 2 == 1 and 'Informed' in sample:
        informed_runs.append(sample['Informed']['y'][:100]) # Limit to first 100 time points

informed_array = np.array(informed_runs)
informed_mean = np.mean(informed_array, axis=0)
informed_std = np.std(informed_array, axis=0)

# Prepare time series with zeros before split_point
T = int(split_point + informed_mean.shape[0])  # total time including zeros
time = np.arange(T)

informed_full = np.zeros(T)
informed_full[split_point:] = informed_mean

informed_std_full = np.zeros(T)
informed_std_full[split_point:] = informed_std

fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

ax.plot(time, informed_full, color='blue', label='Mean Informed')
ax.fill_between(time,
                informed_full - informed_std_full,
                informed_full + informed_std_full,
                color='blue', alpha=0.3)

ax.vlines(split_point, ymin=0, ymax=200, colors='gray', linestyles='dashed', label='Quarantine Begins')

ax.set_xlabel("Time (days)")
ax.set_ylabel("# of Informed")
ax.set_title("Information Dynamics")
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('result_figures/proportion_informed.pdf', bbox_inches='tight')
plt.show()

plt.close()

# ---------------------------
# Save results to PKL
# ---------------------------
PKL_FILENAME = "result_figures/proportion_informed_results.pkl"

save_dict = {
    "split_point": int(split_point),
    "time": time.tolist(),
    "informed_mean_full": informed_full.tolist(),
    "informed_std_full": informed_std_full.tolist(),
    "informed_mean_post_split": informed_mean.tolist(),
    "informed_std_post_split": informed_std.tolist(),
    "informed_runs_raw": [run.tolist() for run in informed_runs],
    "num_runs": len(informed_runs),
    "total_time_points": int(T)
}

# Safe write
try:
    with open(PKL_FILENAME, "wb") as f:
        pickle.dump(save_dict, f)
    print(f"Results successfully saved to {PKL_FILENAME}")
except Exception as e:
    print("Error saving PKL:", e)