import networkx as nx
import SIR
import correlated_graphs
import matplotlib.pyplot as plt
from copy import deepcopy
import pickle
import numpy as np
import pandas as pd
import random
import find_seeds
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset, zoomed_inset_axes


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

n = 200
T = 100
NUM_SEEDS = 200

beta = 0.15 # Infection rate
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05 # Initial infected portion

contact_network = nx.erdos_renyi_graph(n=n, p=0.05, seed=42)
n_contact = contact_network.number_of_nodes()

social_network = correlated_graphs.create_social_graph(contact_network, nE = 2 * n_contact)[0]
social_network = social_network.to_directed()

def informed_vs_noninformed(plot_data=False):
    T_runs = []
    Y_runs_informed = []
    Y_runs_noninformed = []

    num_trials = 25

    for _ in range(num_trials):
        data_inf = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
            q=True
        )[2]
        T_runs.append(data_inf[0])
        Y_runs_informed.append(data_inf[1])

        data_noninf = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
            q=False
        )[2]
        Y_runs_noninformed.append(data_noninf[1])

    x = T_runs[0]

    y_informed = np.array(Y_runs_informed)
    y_noninformed = np.array(Y_runs_noninformed)

    mean_inf = np.mean(y_informed, axis=0)
    std_inf = np.std(y_informed, axis=0)

    mean_noninf = np.mean(y_noninformed, axis=0)
    std_noninf = np.std(y_noninformed, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_inf, label='With quarantine', color='blue')
        ax.fill_between(x, mean_inf - std_inf, mean_inf + std_inf, color='blue', alpha=0.3)

        ax.plot(x, mean_noninf, label='Without quarantine', color='red')
        ax.fill_between(x, mean_noninf - std_noninf, mean_noninf + std_noninf, color='red', alpha=0.3)

        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Permanent Quarantine')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig('result_figures/informed_vs_noninformed.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_inf, std_inf), (x, mean_noninf, std_noninf)

def const_quarantines(plot_data=False):
    quarantine_constant = 14
    num_trials = 25

    T_runs = []
    Y_runs_quarantine = []
    Y_runs_noquarantine = []

    adherence = 1.0

    for _ in range(num_trials):
        data1 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=quarantine_constant, adherence=adherence
        )[2]
        T_runs.append(data1[0])
        Y_runs_quarantine.append(data1[1])

        data2 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=False
        )[2]
        Y_runs_noquarantine.append(data2[1])

    x = T_runs[0]
    y_q = np.array(Y_runs_quarantine)
    y_noq = np.array(Y_runs_noquarantine)

    mean_q = np.mean(y_q, axis=0)
    std_q = np.std(y_q, axis=0)

    mean_noq = np.mean(y_noq, axis=0)
    std_noq = np.std(y_noq, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_q, label=f'With constant quarantine (q={quarantine_constant})', color='blue')
        ax.fill_between(x, mean_q - std_q, mean_q + std_q, color='blue', alpha=0.3)

        ax.plot(x, mean_noq, label='Without quarantine', color='red')
        ax.fill_between(x, mean_noq - std_noq, mean_noq + std_noq, color='red', alpha=0.3)

        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Constant Quarantine')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig('result_figures/const_quarantines.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_q, std_q), (x, mean_noq, std_noq)

def normal_dist_quarantines(plot_data=False):
    num_trials = 25

    T_runs = []
    Y_runs_normal = []
    Y_runs_noquarantine = []

    adherence = 1.0

    for _ in range(num_trials):
        data1 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=True, adherence=adherence
        )[2]
        T_runs.append(data1[0])
        Y_runs_normal.append(data1[1])

        data2 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=False
        )[2]
        Y_runs_noquarantine.append(data2[1])

    x = T_runs[0]
    y_norm = np.array(Y_runs_normal)
    y_noq = np.array(Y_runs_noquarantine)

    mean_norm = np.mean(y_norm, axis=0)
    std_norm = np.std(y_norm, axis=0)

    mean_noq = np.mean(y_noq, axis=0)
    std_noq = np.std(y_noq, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_norm, label='With Normal Dist. Quarantine', color='blue')
        ax.fill_between(x, mean_norm - std_norm, mean_norm + std_norm, color='blue', alpha=0.3)

        ax.plot(x, mean_noq, label='Without Quarantine', color='red')
        ax.fill_between(x, mean_noq - std_noq, mean_noq + std_noq, color='red', alpha=0.3)

        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Normally Distributed Quarantine')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig('result_figures/normal_dist_quarantines.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_norm, std_norm), (x, mean_noq, std_noq)

def jaccard_similarity(num_runs=20, bins=10, plot_data=False):
    H = nx.read_gml('experiment_data/Freeman3.gml')
    H = nx.convert_node_labels_to_integers(H, first_label=0)
    contact_graph = H.to_undirected()

    all_bin_means = []

    for _ in range(num_runs):
        social_graph, sim = correlated_graphs.create_social_graph(
            contact_graph,
            nE=2 * contact_graph.number_of_edges()
        )
        I = social_graph.to_undirected()

        data = [(sim[pair], int(I.has_edge(*pair))) for pair in sim]
        df = pd.DataFrame(data, columns=['similarity', 'edge'])

        df['bin'] = pd.cut(df['similarity'], bins=bins)
        bin_means = df.groupby('bin')['edge'].mean()
        all_bin_means.append(bin_means.values)

    all_bin_means = np.array(all_bin_means)

    mean_bin_means = np.mean(all_bin_means, axis=0)
    std_bin_means = np.std(all_bin_means, axis=0)

    bin_labels = bin_means.index.astype(str)

    if plot_data:
        x = np.arange(len(bin_labels))

        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

        ax.bar(
            x,
            mean_bin_means,
            yerr=std_bin_means,
            capsize=6,
            alpha=0.85,
            edgecolor="black",
            linewidth=1.3
        )

        ax.set_title(
            "Correlation Between Social and Contact Networks",
            pad=20
        )

        ax.set_xlabel("Jaccard Similarity Bin")
        ax.set_ylabel("Probability of Edge Existence")

        ax.set_xticks(x)
        ax.set_xticklabels(bin_labels, rotation=45)

        ax.grid(axis="y", linestyle="--", alpha=0.4)

        plt.tight_layout()
        plt.savefig('result_figures/jaccard_similarity.pdf', bbox_inches='tight')
        plt.close()

    return df, bin_means

def random_vs_nonrandom_seeds(num_comparisons, plot_data=False):
    num_trials = 50

    infections_random = []
    infections_nonrandom = []

    degree_dict = dict(contact_network.degree())
    sorted_nodes = sorted(degree_dict, key=degree_dict.get, reverse=True)

    random_seeds = [
        random.choice(list(contact_network.nodes()))
        for _ in range(num_comparisons)
    ]

    non_random_seeds = find_seeds.find_seed_set(
        social_graph=deepcopy(contact_network),
        num_seeds=num_comparisons,
        exponent=20 # Strictly degree-based
    )

    for i in range(1, num_comparisons + 1):
        inner_random_avg = []
        for _ in range(num_trials):
            data_random = SIR.Simulate_SIR(
                contact_network=deepcopy(contact_network),
                social_network=deepcopy(social_network),
                T=T,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=100,
                adherence=1.0,
                seeds=random_seeds[:i]
            )[2]
            inner_random_avg.append(np.mean(data_random[1]))

        infections_random.append(inner_random_avg)

        inner_nonrandom_avg = []
        for _ in range(num_trials):
            data_nonrandom = SIR.Simulate_SIR(
                contact_network=deepcopy(contact_network),
                social_network=deepcopy(social_network),
                T=T,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=100,
                adherence=1.0,
                seeds=non_random_seeds[:i]
            )[2]
            inner_nonrandom_avg.append(np.mean(data_nonrandom[1]))

        infections_nonrandom.append(inner_nonrandom_avg)

    avg_infections_random = np.array(
        [np.mean(run) for run in infections_random]
    )
    std_infections_random = np.array(
        [np.std(run) for run in infections_random]
    )

    avg_infections_nonrandom = np.array(
        [np.mean(run) for run in infections_nonrandom]
    )
    std_infections_nonrandom = np.array(
        [np.std(run) for run in infections_nonrandom]
    )

    if plot_data:
        x = np.arange(1, num_comparisons + 1)
        width = 0.35

        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

        ax.bar(
            x - width / 2,
            avg_infections_random,
            width,
            yerr=std_infections_random,
            capsize=6,
            label="Random Seeds",
            color="orange",
            alpha=0.75
        )

        ax.bar(
            x + width / 2,
            avg_infections_nonrandom,
            width,
            yerr=std_infections_nonrandom,
            capsize=6,
            label="Non-Random Seeds",
            color="blue",
            alpha=0.75
        )

        y_max = max(
            np.max(avg_infections_random + std_infections_random),
            np.max(avg_infections_nonrandom + std_infections_nonrandom)
        )

        y_min = min(
            np.min(avg_infections_random - std_infections_random),
            np.min(avg_infections_nonrandom - std_infections_nonrandom)
        )

        ax.set_ylim(y_min - 1, y_max + 1)

        ax.set_xlabel("Number of Seeds")
        ax.set_ylabel("# of Infected")
        ax.set_title("Random vs Degree-Based Seed Selection")

        ax.legend(frameon=False)
        ax.grid(axis="y", linestyle="--", alpha=0.6)

        plt.tight_layout()
        plt.savefig('result_figures/random_vs_nonrandom_seeds.pdf', bbox_inches='tight')
        plt.close()

    return (
        (x, avg_infections_random, std_infections_random),
        (x, avg_infections_nonrandom, std_infections_nonrandom),
    )

def compare_infections_adherence(adherence, plot_data=False):
    num_trials = 25

    T_runs = []
    Y_runs_full_adherence = []
    Y_runs_partial_adherence = []

    for i in range(num_trials):
        data1 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, num_seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init, q="r"
        )[2]
        T_runs.append(data1[0])
        Y_runs_full_adherence.append(data1[1])

        data2 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, num_seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init,q="r", adherence=adherence
        )[2]
        Y_runs_partial_adherence.append(data2[1])

    x = T_runs[0]
    y_full = np.array(Y_runs_full_adherence)
    y_partial = np.array(Y_runs_partial_adherence)

    mean_full = np.mean(y_full, axis=0)
    std_full = np.std(y_full, axis=0)

    mean_partial = np.mean(y_partial, axis=0)
    std_partial = np.std(y_partial, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_full, label=f'With full adherence', color='blue')
        ax.fill_between(x, mean_full - std_full, mean_full + std_full, color='blue', alpha=0.3)

        ax.plot(x, mean_partial, label='With partial adherence', color='red')
        ax.fill_between(x, mean_partial - std_partial, mean_partial + std_partial, color='red', alpha=0.3)

        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Constant Quarantine')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig('result_figures/compare_infections_adherence.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_full, std_full), (x, mean_partial, std_partial)

def r_quarantine(plot_data=False):
    num_trials = 5

    T_runs = []
    Y_runs_r_quarantine = []
    Y_runs_noquarantine = []

    for _ in range(num_trials):
        data1 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init,
             q="r", adherence=1.0
        )[2]
        T_runs.append(data1[0])
        Y_runs_r_quarantine.append(data1[1])

        data2 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=False
        )[2]
        Y_runs_noquarantine.append(data2[1])

    x = T_runs[0]
    y_rq = np.array(Y_runs_r_quarantine)
    y_noq = np.array(Y_runs_noquarantine)

    mean_rq = np.mean(y_rq, axis=0)
    std_rq = np.std(y_rq, axis=0)

    mean_noq = np.mean(y_noq, axis=0)
    std_noq = np.std(y_noq, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_rq, label='With quarantine', color='blue')
        ax.fill_between(x, mean_rq - std_rq, mean_rq + std_rq, color='blue', alpha=0.3)

        ax.plot(x, mean_noq, label='Without quarantine', color='red')
        ax.fill_between(x, mean_noq - std_noq, mean_noq + std_noq, color='red', alpha=0.3)

        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Quarantine Until Recovery')
        ax.legend()
        ax.grid(True)

        plt.show()
        plt.tight_layout()
        plt.savefig('result_figures/r_quarantine.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_rq, std_rq), (x, mean_noq, std_noq)

def permanent_quarantine(plot_data=False):
    num_trials = 25

    T_runs = []
    Y_runs_quarantine = []
    Y_runs_noquarantine = []

    for _ in range(num_trials):
        data1 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, num_seeds=NUM_SEEDS,
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=T, adherence=1.0
        )[2]
        T_runs.append(data1[0])
        Y_runs_quarantine.append(data1[1])

        data2 = SIR.Simulate_SIR(
            contact_network=deepcopy(contact_network),
            social_network=deepcopy(social_network),
            T=T, 
            beta=beta, gamma=gamma, mu=mu, init=init,
             q=False
        )[2]
        Y_runs_noquarantine.append(data2[1])

    x = T_runs[0]
    y_q = np.array(Y_runs_quarantine)
    y_noq = np.array(Y_runs_noquarantine)
    mean_q = np.mean(y_q, axis=0)
    std_q = np.std(y_q, axis=0)
    mean_noq = np.mean(y_noq, axis=0)
    std_noq = np.std(y_noq, axis=0)

    if plot_data:
        fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)
        ax.plot(x, mean_q, label='With quarantine', color='blue')
        ax.fill_between(x, mean_q - std_q, mean_q + std_q, color='blue', alpha=0.3)
        ax.plot(x, mean_noq, label='Without quarantine', color='red')
        ax.fill_between(x, mean_noq - std_noq, mean_noq + std_noq, color='red', alpha=0.3)
        ax.set_xlabel('Time (days)')
        ax.set_ylabel('# of Infected')
        ax.set_title('SIR with Permanent Quarantine')
        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig('result_figures/permanent_quarantine.pdf', bbox_inches='tight')
        plt.close()

    return (x, mean_q, std_q), (x, mean_noq, std_noq)

def plot_all_quarantine():
    # --- Load data ---
    data_perm, data_noq = permanent_quarantine()
    data_gauss, _ = normal_dist_quarantines()

    # Convert x to numpy array (all x are the same)
    x = np.array(data_noq[0])

    # Store results: (mean_vals, std_vals)
    results = {
        "No Quarantine": (np.array(data_noq[1]), np.array(data_noq[2])),
        "Permanent Quarantine": (np.array(data_perm[1]), np.array(data_perm[2])),
        "Gaussian Quarantine": (np.array(data_gauss[1]), np.array(data_gauss[2])),
    }

    colors = ['blue', 'green', 'purple']

    fig, ax = plt.subplots(figsize=FIGURE_SIZE_LINE)

    # --- Plot main curves ---
    for i, (label, (mean_vals, std_vals)) in enumerate(results.items()):
        mean_vals = np.array(mean_vals)
        std_vals = np.array(std_vals)

        ax.plot(x, mean_vals, label=label, color=colors[i])
        ax.fill_between(
            x,
            mean_vals - std_vals,
            mean_vals + std_vals,
            color=colors[i],
            alpha=0.3
        )

    # --- Main plot labels ---
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("# of Infected")
    ax.set_title("SIRS Infections Under Different Quarantine Strategies")

    ax.legend(
        loc="upper right",
    )

    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig('result_figures/all_quarantine_strategies.pdf', bbox_inches='tight')
    plt.close()

    return results

def run_simulations():
    data0 = informed_vs_noninformed()
    data1 = const_quarantines()
    data2 = normal_dist_quarantines()
    data3 = r_quarantine()
    data4 = permanent_quarantine()
    data5 = random_vs_nonrandom_seeds(num_comparisons=10)
    data6 = jaccard_similarity(num_runs=20, bins=10)

    return data0, data1, data2, data3, data4, data5, data6

def SIR_pickle_dump(filename='experiment_data/pickles.pkl'):
    presets = {'T': T, 'beta': beta, 'gamma': gamma, 'mu': mu, 'init': init}

    data = run_simulations()

    with open(filename, 'wb') as f:
        f.truncate(0)
        all_data = {
            'SIR Default presets': presets,
            'Informed vs Non-Informed': data[0],
            'Constant Quarantines': data[1],
            'Normal Dist. Quarantines': data[2],
            'Quarantine Upon Recovery': data[3],
            'Permanent Quarantine': data[4],
            'Jaccard Similarity': data[5]
        }
        pickle.dump(all_data, f)

def pickle_load(filename='experiment_data/pickles.pkl'):
    with open(filename, 'rb') as file:
        data = pickle.load(file)

    print(data)

if __name__ == "__main__":
    r_quarantine(plot_data=True)
    # plot_all_quarantine()
    # random_vs_nonrandom_seeds(4, plot_data=True)
    # r_quarantine(plot_data=True)
    # const_quarantines(plot_data=True)
    # permanent_quarantine(plot_data=True)
    # random_vs_nonrandom_seeds(3, plot_data=True)
    # jaccard_similarity(plot_data=True)