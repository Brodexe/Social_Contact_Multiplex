import extract_mfa
import matplotlib.pyplot as plt
import numpy as np
import pickle

# ============================================================
# Global matplotlib settings
# ============================================================

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

# ============================================================
# Output files
# ============================================================

PKL_FILENAME = "result_figures/plot_infected_informed_data.pkl"

FIG_GROUPED_PDF = "result_figures/quarantine_dynamics_by_adherence.pdf"
FIG_SINGLE_PDF  = "result_figures/joint_informed_infected_dynamics.pdf"

FIGURE_SIZE_LINE = (10, 6)

# ============================================================
# Adherence data locations
# ============================================================

ADHERENCE_FILES = {
    0.2: "experiment_data/a_0.2",
    0.4: "experiment_data/a_0.4",
    0.6: "experiment_data/a_0.6",
    0.8: "experiment_data/a_0.8",
    0.9: "experiment_data/a_0.9",
    1.0: "experiment_data/a_1.0",
}

# ============================================================
# Grouped adherence plot
# ============================================================

def plot_groups_by_adherence(show=False):

    colors = {
        0.2: '#1f77b4',
        0.4: '#ff7f0e',
        0.6: '#2ca02c',
        0.8: '#d62728',
        0.9: '#9467bd',
        1.0: '#127b8f',
    }

    styles = {
        'Infected':            'solid',
        'Informed & Infected': 'dashed',
        'Informed':            'dotted'
    }

    fig, ax = plt.subplots(figsize=(14, 8))
    saved_output = {"grouped_results": {}}

    legend_handles = []
    legend_labels = []

    for a, filepath in ADHERENCE_FILES.items():

        samples = extract_mfa.parse_sample_data(filepath)
        samples = [samples[i] for i in range(len(samples)) if i % 2 == 1]

        if not samples:
            continue

        n = samples[0]['Number of nodes']
        T = len(samples[0]['SIR Infections']['y'])
        split_point = int(samples[0]['Informed']['x'][0])

        t = split_point + np.arange(T)

        infected_arr = np.vstack([s['SIR Infections']['y'] for s in samples]) / n
        informed_arr = np.vstack([s['Informed']['y'] for s in samples]) / n
        inf_inf_arr  = np.vstack([s['Informed and Infected']['y'] for s in samples]) / n

        curves = {
            'Infected': (infected_arr.mean(0), infected_arr.std(0)),
            'Informed': (informed_arr.mean(0), informed_arr.std(0)),
            'Informed & Infected': (inf_inf_arr.mean(0), inf_inf_arr.std(0)),
        }

        saved_output["grouped_results"][a] = {
            "n": n,
            "time": t.tolist()
        }

        for name, (mean, std) in curves.items():

            line, = ax.plot(
                t, mean,
                color=colors[a],
                linestyle=styles[name],
                label=f"{name} (a={a})"
            )

            ax.fill_between(
                t, mean - std,
                mean + std,
                color=colors[a],
                alpha=0.18
            )

            legend_handles.append(line)
            legend_labels.append(f"{name} (a={a})")

            # saved_output["grouped_results"][a][f"{name}_mean"] = mean.tolist()
            # saved_output["grouped_results"][a][f"{name}_std"]  = std.tolist()

    ax.set_xlabel("Time step")
    ax.set_ylabel("Fraction of population")
    ax.set_title("Quarantine dynamics by adherence level")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)

    ax.legend(
        handles=legend_handles,
        labels=legend_labels,
        ncol=3,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.28),
        frameon=True
    )

    fig.tight_layout()
    fig.savefig(FIG_GROUPED_PDF, format="pdf", bbox_inches="tight")
    plt.close(fig)

    with open(PKL_FILENAME, "wb") as f:
        pickle.dump(saved_output, f)

    if show:
        plt.show()

    print(f"Saved grouped adherence figure → {FIG_GROUPED_PDF}")

# ============================================================
# Single adherence plot
# ============================================================

def plot_one_adherence_group(samples):
    if not samples:
        return

    split_point = int(samples[1]['Informed']['x'][0])  # Quarantine start index

    # Separate even (pre-quarantine) and odd (post-quarantine) samples
    pre_samples  = [samples[i] for i in range(len(samples)) if i % 2 == 0]
    post_samples = [samples[i] for i in range(len(samples)) if i % 2 == 1]

    # Determine consistent lengths
    T_pre  = min(len(s['SIR Infections']['y']) for s in pre_samples)
    T_post = min(len(s['SIR Infections']['y']) for s in post_samples)

    # Time vectors
    t_pre  = np.arange(T_pre)
    t_post = T_pre + np.arange(T_post) 

    # Flatten pre- and post-quarantine separately
    def stack_samples(arr_name, group, length):
        return np.vstack([s[arr_name]['y'][:length] for s in group])

    infected_pre = stack_samples('SIR Infections', pre_samples, T_pre)
    infected_post = stack_samples('SIR Infections', post_samples, T_post)

    informed_pre = stack_samples('Informed', pre_samples, T_pre)
    informed_post = stack_samples('Informed', post_samples, T_post)

    inf_inf_pre = stack_samples('Informed and Infected', pre_samples, T_pre)
    inf_inf_post = stack_samples('Informed and Infected', post_samples, T_post)

    # Combine pre- and post- arrays for plotting
    t = np.concatenate([t_pre, t_post])
    infected_arr = np.concatenate([infected_pre.mean(0), infected_post.mean(0)])
    informed_arr = np.concatenate([informed_pre.mean(0), informed_post.mean(0)])
    inf_inf_arr  = np.concatenate([inf_inf_pre.mean(0), inf_inf_post.mean(0)])

    # For std bands
    infected_std = np.concatenate([infected_pre.std(0), infected_post.std(0)])
    informed_std = np.concatenate([informed_pre.std(0), informed_post.std(0)])
    inf_inf_std  = np.concatenate([inf_inf_pre.std(0), inf_inf_post.std(0)])

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    # Plotting helper
    def plot_band(mean, std, label, color):
        ax.plot(t, mean, label=label, color=color)
        ax.fill_between(t, mean - std, mean + std, color=color, alpha=0.22)

    plot_band(informed_arr, informed_std, "Informed", "#2ca02c")
    plot_band(inf_inf_arr, inf_inf_std, "Informed & Infected", "#ff7f0e")
    plot_band(infected_arr, infected_std, "Infected", "#d62728")

    ax.set_title("Information and Infection Dynamics")

    # Vertical dotted line at quarantine start
    ax.axvline(split_point, color='k', linestyle=':', linewidth=2, label="Quarantine Start")

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Fraction of population")
    # ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)

    # Inset legend
    ax.legend(loc='center right', fontsize=16, frameon=True)

    fig.tight_layout()
    fig.savefig(FIG_SINGLE_PDF, format="pdf", bbox_inches="tight")
    plt.show()

    plt.close(fig)

    print(f"Saved single adherence figure → {FIG_SINGLE_PDF}")


if __name__ == "__main__":
    read_file = "experiment_data/mfa_xy_data.txt"
    samples = extract_mfa.parse_sample_data(read_file)
    plot_one_adherence_group(samples)