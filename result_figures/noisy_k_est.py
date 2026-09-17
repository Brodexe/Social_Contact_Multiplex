# ---------------------------------------------------------------------------
# Data generation order — ALL 6 runs below write to the SAME
# experiment_data/mfa_xy_data.txt, in this exact order (each run appends a
# pre-/post-quarantine sample pair, i.e. 2 entries). The plotting logic below
# assumes samples[0:6] are the 3 Gaussian levels and samples[6:12] are the
# 3 Poisson levels, in the order listed here.
#
# clear=True truncates write_file AND regenerates a new random network, so use
# it ONLY on run 1; use clear=False on runs 2-6 so they append to the same file
# and reuse the same network as run 1 (otherwise the "True <k>" curve won't be
# comparable across noise levels).
#
#   1. clear=True,  noise_type="gaussian", gaussian_noise_scale=0.33   (sigma)
#   2. clear=False, noise_type="gaussian", gaussian_noise_scale=0.165  (1/2 sigma)
#   3. clear=False, noise_type="gaussian", gaussian_noise_scale=0.11   (1/3 sigma)
#   4. clear=False, noise_type="poisson", poisson_noise_scale=1/9
#   5. clear=False, noise_type="poisson", poisson_noise_scale=1/4
#   6. clear=False, noise_type="poisson", poisson_noise_scale=1
# ---------------------------------------------------------------------------

import extract_mfa
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "font.size": 18,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 14,
    "lines.linewidth": 2.5,
})

FIGURE_SIZE_LINE = (12, 6)


def align_true_to_est(sample):
    x_est = np.array(sample["w1 Estimated"]["x"])
    y_est = np.array(sample["w1 Estimated"]["y"])
    x_true = np.array(sample["w1 True (Mean Node Degree)"]["x"])
    y_true = np.array(sample["w1 True (Mean Node Degree)"]["y"])
    mask = np.isin(x_true, x_est)
    return x_est, y_est, y_true[mask]


def mean_std(runs):
    runs = np.array(runs)
    return runs.mean(axis=0), runs.std(axis=0)


def plot_k_est(noise_groups, title, out_path):
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    # True <k> (same underlying network for all noise levels — use the first group's sample)
    _, first_pre, first_post, _ = noise_groups[0]
    x_pre0, _, y_true_pre = align_true_to_est(first_pre)
    x_post0, _, y_true_post = align_true_to_est(first_post)

    ax.plot(x_pre0, y_true_pre, color="black", linestyle="-", label="True ⟨k⟩", zorder=5)
    ax.plot(x_post0, y_true_post, color="black", linestyle="-", zorder=5)

    split_point = x_pre0[-1] + 1

    for label, pre, post, color in noise_groups:
        x_pre, y_pre_est, _ = align_true_to_est(pre)
        x_post, y_post_est, _ = align_true_to_est(post)

        pre_mean, pre_std = mean_std(pre["w1 all runs"]["y"])
        post_mean, post_std = mean_std(post["w1 all runs"]["y"])

        ax.plot(x_pre, y_pre_est, color=color, linestyle="--",
                label=f"Estimated ⟨k⟩ ({label})")
        ax.plot(x_post, y_post_est, color=color, linestyle="--")

        ax.fill_between(x_pre, pre_mean - pre_std, pre_mean + pre_std,
                        color=color, alpha=0.2)
        ax.fill_between(x_post, post_mean - post_std, post_mean + post_std,
                        color=color, alpha=0.2)

    ax.axvline(split_point, color="black", linestyle="--", linewidth=2,
               label="Quarantine begins")

    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Mean Node Degree ⟨k⟩")
    ax.set_title(title)

    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.show()
    plt.close(fig)


# All 12 samples (6 Gaussian, then 6 Poisson) live in one file, in that order.
samples = extract_mfa.parse_sample_data("experiment_data/mfa_xy_data.txt")

# ---------------------------
# Gaussian noise plot
# ---------------------------
gaussian_samples = samples[0:6]

# samples[0,1]: sigma=1, samples[2,3]: sigma=1/2, samples[4,5]: sigma=1/3
gaussian_groups = [
    (r"data = $\mu \pm \mathcal{N}(0,\sigma^2)$", gaussian_samples[0], gaussian_samples[1], "#1f77b4"),
    (r"data = $\mu \pm (1/2)\mathcal{N}(0,\sigma^2)$", gaussian_samples[2], gaussian_samples[3], "#ff7f0e"),
    (r"data = $\mu \pm (1/3)\mathcal{N}(0,\sigma^2)$", gaussian_samples[4], gaussian_samples[5], "#d62728"),
]

plot_k_est(gaussian_groups, "⟨k⟩ Estimation Under Gaussian Measurement Noise",
           "result_figures/noisy_k_est.pdf")

# ---------------------------
# Poisson noise plot
# ---------------------------
poisson_samples = samples[6:12]

# samples[0,1]: scale=1/9, samples[2,3]: scale=1/4, samples[4,5]: scale=1
poisson_groups = [
    (r"data = $\mu \pm \mathrm{Pois}(\lambda=\sigma^2)$", poisson_samples[0], poisson_samples[1], "#1f77b4"),
    (r"data = $\mu \pm (1/2) \mathrm{Pois}(\lambda=\sigma^2)$", poisson_samples[2], poisson_samples[3], "#ff7f0e"),
    (r"data = $\mu \pm (1/3) \mathrm{Pois}(\lambda=\sigma^2)$", poisson_samples[4], poisson_samples[5], "#d62728"),
]

plot_k_est(poisson_groups, "⟨k⟩ Estimation Under Poisson Measurement Noise",
           "result_figures/noisy_k_est_poisson.pdf")
