"""
MILP-based seed selection

alpha_w * I_proxy + beta_w * edge_removal_cost

Decision variables (all binary):
    x_v  in {0,1}  -- node v is in the seed set
    y_e  in {0,1}  -- edge e remains live (1) or is removed (0)
    z_e  in {0,1}  -- edge e is "active": live AND neither endpoint is a seed
                      serves as a static proxy for infection risk

z_e = y_e * (1 - x_u) * (1 - x_v)  is linearized with 4 constraints per edge:
    (a)  z_e + x_u                <=  1
    (b)  z_e + x_v                <=  1
    (c)  z_e        - y_e         <=  0
    (d)  z_e        - y_e + x_u + x_v  >=  0

Variable ordering in the solver vector:
    [x_0 .. x_{N-1},  y_0 .. y_{E-1},  z_0 .. z_{E-1}]
"""

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix
import networkx as nx
from copy import deepcopy
import random
import correlated_graphs
import SIR
import matplotlib.pyplot as plt
import cost_curve_store

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

q = "r"
adherence = 1.0
n = 200
p = 0.05
T = 100

contact_network = nx.erdos_renyi_graph(n, p, seed=42)
nx.set_edge_attributes(contact_network, 1, 'weight')
initial_contact = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
social_network = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)[0]
initial_social = deepcopy(social_network)

beta = 0.15
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05
num_simulations = 10

batch_interval = 2  # MILP is re-solved and cost updated once every batch_interval steps
information_spread = True

# Returns newly infected at a given time step
def given_at_time(time, sirs_dynamics, contact_graph):
    if time > 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1 and sirs_dynamics[time-1][node] != 1)
    # Initial condition. We say that n_i(0) = i(0)
    elif time == 0:
        new_i = sum(1 for node in contact_graph.nodes() 
                                if sirs_dynamics[time][node] == 1)

    return new_i

def baseline_infections():
    contact_network = deepcopy(initial_contact)
    social_network = deepcopy(initial_social)

    full_dynamics = None
    prev_state_dict = None
    baseline_newly_counts = []

    for t_cur in range(T):
        simulation_results = SIR.Simulate_SIR(
            contact_network=contact_network,
            social_network=social_network,
            T=1,
            q=False,
            beta=beta,
            gamma=gamma,
            mu=mu,
            init=init,
            initial_state_dict=prev_state_dict,
        )

        contact_network = deepcopy(initial_contact)
        sirs_dynamics = simulation_results[4]
        prev_state_dict = sirs_dynamics[-1]
        full_dynamics = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics

        current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
        baseline_newly_counts.append(current_new_i)

    baseline_newly_frac = [count / n for count in baseline_newly_counts]
    return baseline_newly_counts, baseline_newly_frac

# Collect per-timestep newly infected counts from baseline runs
baseline_runs = []
for _ in range(num_simulations):
    baseline_newly_counts, _ = baseline_infections()
    baseline_runs.append(baseline_newly_counts)

# Global utility function: Find a small seed set which minimizes infection spread,
# while maximizing number of live edges in the network.
# newly_infected: array of newly infected ratios at each time step
# total_edges: integer number of edges in the original contact network
# live_edges: array EDGES that are live at each step
def global_cost_function(newly_infected, live_edges, t_cur):
    # NOTE: for now assume cost is uniform across all edges
    all_edges = initial_contact.edges()

    # Some cost function f: V -> Reals that maps edges to cost of removal
    edge_cost_dict = {(u, v): data.get('weight', 1) for u, v, data in initial_contact.edges(data=True)}

    # Compute total possible cost of edge removals (if all edges were removed)
    edge_cost_bound = sum(edge_cost_dict[edge] for edge in all_edges)

    total_edge_removal_cost = 0
    # Compute sum of removed edges at each time step
    for t in range(t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    cost_elements = (np.sum(newly_infected), total_edge_removal_cost)

    # Adjust penalty weights so that each term contributes equally to cost function
    removal_cost = 1

    g = sum(max(run[t] for run in baseline_runs) for t in range(t_cur + 1))

    alpha_w = 1 / g if g > 0 else 1.0
    beta_w = 1 / ((t_cur + 1) * edge_cost_bound)

    # Print cost components
    print(f"Cost components at time {t_cur}:")
    print(f"  Newly infected sum: {np.sum(newly_infected)}")
    print(f"  Total edge removal cost: {total_edge_removal_cost}")
    print(f" alpha_w: {alpha_w:.4f}, beta_w: {beta_w:.4f}")

    return alpha_w * np.sum(newly_infected) + beta_w * removal_cost * total_edge_removal_cost, cost_elements

def milp_seed_selection_stepwise():
    """
    Step-wise MILP seed selection: re-solve the MILP at each batch boundary,
    using the SIRS state from the previous batch to update alpha_w.

    alpha_w_t = 1 / max(current_infected_count, 1)
      -- inversely proportional to the number currently infected, replacing
         the global baseline-max normalization used in the one-shot version.

    Seeds and edge removals are chosen fresh at each batch boundary and held
    fixed for the remainder of the batch (not accumulated). The constraint
    matrix is built once; only the objective vector c changes.
    """
    nodes = list(initial_contact.nodes())
    edges = list(initial_contact.edges())
    N = len(nodes)
    E = len(edges)
    node_idx = {v: i for i, v in enumerate(nodes)}

    edge_cost_bound = sum(data.get('weight', 1) for _, _, data in initial_contact.edges(data=True))
    beta_w  = 1.0 / (T * edge_cost_bound)
    edge_weights = np.array([initial_contact[u][v].get('weight', 1) for u, v in edges])

    K = n  # unconstrained seed budget

    # ------------------------------------------------------------------ #
    #  Constraint matrix  (built once; reused every step)                 #
    # ------------------------------------------------------------------ #
    n_vars = N + 2 * E
    n_con  = 1 + 4 * E
    A      = lil_matrix((n_con, n_vars))
    lb_con = np.full(n_con, -np.inf)
    ub_con = np.full(n_con,  np.inf)

    A[0, :N] = 1.0
    ub_con[0] = K

    for i, (u, v) in enumerate(edges):
        ui = node_idx[u]
        vi = node_idx[v]
        yi = N + i
        zi = N + E + i
        r  = 1 + 4 * i
        A[r,   zi] =  1;  A[r,   ui] =  1;  ub_con[r]   = 1
        A[r+1, zi] =  1;  A[r+1, vi] =  1;  ub_con[r+1] = 1
        A[r+2, zi] =  1;  A[r+2, yi] = -1;  ub_con[r+2] = 0
        A[r+3, zi] =  1;  A[r+3, yi] = -1;  A[r+3, ui] = 1;  A[r+3, vi] = 1;  lb_con[r+3] = 0

    lc          = LinearConstraint(csr_matrix(A), lb_con, ub_con)
    X_bounds    = Bounds(lb=np.zeros(n_vars), ub=np.ones(n_vars))
    integrality = np.ones(n_vars)

    # t_batch=0: no information spread at all (seeds/removals are re-solved and applied
    #   every tick) -- one T=1 call every tick.
    # t_batch=batch_interval: one call per batch, run only at batch boundaries, letting
    #   info spread across the whole batch_interval window before the next MILP re-solve.
    t_batch = 0
    if information_spread:
        t_batch = batch_interval

    all_cost_curves           = []
    winner_sets               = []   # list[sim] of list[step] of seed lists
    all_edge_curves           = []
    all_newly_infected_counts = []
    all_newly_infected_frac   = []
    all_full_dynamics         = []

    for sim_i in range(num_simulations):
        print(f"MILP step-wise simulation {sim_i}")

        social_network  = deepcopy(initial_social)

        cost_lst                    = []
        full_dynamics               = None
        prev_state_dict             = None
        full_live_edges             = None
        edge_counts                 = []
        newly_infected_per_sim      = []
        newly_infected_frac_per_sim = []
        seeds_per_step              = []
        milp_seeds_t                = []
        milp_removed_t              = set()

        for t_cur in range(T):

            # --- Re-solve the MILP only at batch boundaries; hold seeds/removals
            #     fixed for the rest of the batch otherwise ---
            if t_cur % batch_interval == 0:
                # --- alpha_w from previous batch's infection state ---
                if prev_state_dict is None:
                    current_infected_count = max(int(n * init), 1)
                else:
                    current_infected_count = max(
                        sum(1 for s in prev_state_dict.values() if s == 1), 1
                    )
                alpha_w = 1.0 / current_infected_count

                # --- Objective for this batch (only alpha_w changes) ---
                # x (seed selection) has no cost term: only edge count and
                # infection proxy are optimized.
                c = np.zeros(n_vars)
                c[N:N+E] = -beta_w * edge_weights
                c[N+E:]  = alpha_w

                # --- Solve MILP ---
                res = milp(c=c, bounds=X_bounds, constraints=[lc], integrality=integrality)

                if not res.success:
                    print(f"  MILP failed at sim={sim_i} t={t_cur}: {res.message}")
                    milp_seeds_t   = []
                    milp_removed_t = set()
                else:
                    x_sol = np.round(res.x[:N]).astype(int)
                    y_sol = np.round(res.x[N:N+E]).astype(int)
                    milp_seeds_t   = [nodes[i] for i in range(N) if x_sol[i] == 1]
                    milp_removed_t = {edges[i] for i in range(E) if y_sol[i] == 0}

            seeds_per_step.append(milp_seeds_t)

            # --- Fresh contact network with this batch's MILP edge removals ---
            contact_network = deepcopy(initial_contact)
            contact_network.remove_edges_from(milp_removed_t)

            # With information diffusion enabled, only re-simulate at batch boundaries -- one
            # call covers the whole batch_interval window, letting info actually reach non-seed
            # nodes. Without it, advance one real step every tick.
            call_now = (t_cur % batch_interval == 0) if information_spread else True
            if call_now:
                simulation_results = SIR.Simulate_SIR(
                    contact_network    = contact_network,
                    social_network     = social_network,
                    T                  = t_batch,
                    beta               = beta,
                    gamma              = gamma,
                    mu                 = mu,
                    init               = init,
                    q                  = q,
                    adherence          = adherence,
                    begin_q            = 0,
                    seeds              = milp_seeds_t,
                    initial_state_dict = prev_state_dict,
                )

                # Reset contact_network to base (removes quarantine-induced edge changes)
                contact_network = deepcopy(initial_contact)
                contact_network.remove_edges_from(milp_removed_t)

                sirs_dynamics   = simulation_results[4]
                prev_state_dict = sirs_dynamics[-1]
                full_dynamics   = (sirs_dynamics if full_dynamics is None
                                   else full_dynamics + sirs_dynamics)

                graph_vec       = simulation_results[10]
                live_edges      = [list(network) for network in graph_vec]
                full_live_edges = (live_edges if full_live_edges is None
                                   else full_live_edges + live_edges)

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)
            edge_counts.append(len(full_live_edges[t_cur]))

            # Compute cost only at batch boundaries (or the final step)
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, _ = global_cost_function(
                    newly_infected_per_sim, full_live_edges, t_cur
                )
                cost_lst.append(cost)

        winner_sets.append(seeds_per_step)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return (winner_sets, all_cost_curves, all_edge_curves,
            all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics)


def no_quarantine_baseline_runs():
    """
    Simulate with no quarantine (q=False) and no seeds.
    Cost = infections term only; edge removal cost = 0.
    """
    all_cost_curves = []
    all_edge_curves = []
    all_newly_counts = []
    all_newly_frac = []
    all_full_dynamics = []

    for i in range(num_simulations):
        print("No-Quarantine Simulation:", i)

        contact_network = deepcopy(initial_contact)
        social_network  = deepcopy(initial_social)

        cost_lst = []
        full_dynamics = None
        prev_state_dict = None
        full_live_edges = None
        edge_counts = []
        newly_infected_per_sim = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network,
                social_network=social_network,
                T=1,
                beta=beta,
                gamma=gamma,
                mu=mu,
                init=init,
                q=False,
                initial_state_dict=prev_state_dict,
            )

            contact_network = deepcopy(initial_contact)
            sirs_dynamics   = simulation_results[4]
            prev_state_dict = sirs_dynamics[-1]
            full_dynamics   = sirs_dynamics if full_dynamics is None else full_dynamics + sirs_dynamics

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            graph_vec       = simulation_results[10]
            live_edges      = [list(network) for network in graph_vec]
            full_live_edges = live_edges if full_live_edges is None else full_live_edges + live_edges
            edge_counts.append(len(live_edges[-1]))

            cost, _ = global_cost_function(
                newly_infected_per_sim, full_live_edges, t_cur
            )
            cost_lst.append(cost)

        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_counts.append(newly_infected_per_sim)
        all_newly_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return all_cost_curves, all_edge_curves, all_newly_counts, all_newly_frac, all_full_dynamics


if __name__ == "__main__":
    (winner_sets,
     milp_cost_curves,
     milp_edge_curves,
     milp_newly_counts,
     milp_newly_frac,
     milp_dynamics_list) = milp_seed_selection_stepwise()

    avg_seeds = np.mean([[len(s) for s in sim] for sim in winner_sets])
    print(f"\nStep-wise MILP: avg seeds/step across all sims = {avg_seeds:.1f}")

    # Quick summary statistics across simulations
    mean_cost  = np.mean([c[-1] for c in milp_cost_curves])
    mean_infec = np.mean([sum(counts) for counts in milp_newly_counts])
    print(f"Mean final cost (across {num_simulations} sims): {mean_cost:.6f}")
    print(f"Mean total new infections                      : {mean_infec:.1f}")

    # Push this run's cost curve into the store shared with adaptive_seed_selection.py.
    # Once adaptive_seed_selection.py has also been run, call
    # cost_curve_store.plot_joint_cost_comparison() (e.g. `python cost_curve_store.py`)
    # to render the combined 4-curve figure.
    cost_curve_store.push_curve("MILP", milp_cost_curves)
