import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
import math

# Plot results from sensitivity analysis experiments

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

# Consistent figure size for all plots (suitable for Overleaf inclusion)
FIGURE_SIZE_LINE = (10, 6)
FIGURE_SIZE_BAR = (14, 8)

# parameter_name: string indicating which parameter was varied
# value_range: list of parameter values that were tested
def plot_sensitivity_results(file_path, parameter_name, value_range):
    samples = extract_mfa.parse_sample_data(file_path)

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    max_length = 0
    true_k0 = None

    for i, sample in enumerate(samples):
        w1_runs = sample['w1 all runs']['y']

        w1_array = np.array(w1_runs)
        mean_w1 = np.mean(w1_array, axis=0)
        std_w1 = np.std(w1_array, axis=0)
        time_points = np.arange(w1_array.shape[1])

        # --- Plot estimate and retrieve color ---
        line, = ax.plot(
            time_points,
            mean_w1,
            label=f'({parameter_name} = {value_range[i]})'
        )

        color = line.get_color()

        # Std band (same color, faded)
        ax.fill_between(
            time_points,
            mean_w1 - std_w1,
            mean_w1 + std_w1,
            color=color,
            alpha=0.15
        )

        # Save true value once (assumed constant across samples)
        true_k0 = sample['w1 True (Mean Node Degree)']['y'][-1]

        # True reference line
        ax.hlines(
            y=true_k0,
            xmin=0,
            xmax=time_points[-1],
            colors=color,
            linestyles='--',
        )

    ax.set_xlabel("Time (days)")
    ax.set_ylabel(r"Estimated $\langle k_0 \rangle$")
    ax.set_title(f"Sensitivity Analysis: {parameter_name}")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(f'result_figures/sensitivity_{parameter_name}.pdf', bbox_inches='tight')
    plt.show()

    plt.close()

seed_range = [5, 10, 15]
seed_file = "experiment_data/sensitivity_num_seeds.txt"
init_range = [0.025, 0.05, 0.10]
init_file = "experiment_data/sensitivity_init.txt"
density_range = [0.03, 0.04, 0.05]
density_file = "experiment_data/sensitivity_density.txt"

plot_sensitivity_results(seed_file, "Number of Seeds", seed_range)
plot_sensitivity_results(init_file, "Initial Infected", init_range)
plot_sensitivity_results(density_file, "Contact Network Density", density_range)

