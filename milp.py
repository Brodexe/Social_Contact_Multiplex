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
import network_setup
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
T = 100

gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.2
num_simulations = 10

batch_interval = 2  # MILP is re-solved and cost updated once every batch_interval steps
information_spread = True

# Shared with adaptive_seed_selection.py: identical contact network, social
# network, edge weights, and per-simulation heterogeneous beta maps (see
# network_setup.py) so both approaches are compared against the exact same setup.
_shared = network_setup.load_shared_network(min_simulations=num_simulations)
contact_network = deepcopy(_shared["contact_network"])
initial_contact = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
n = len(contact_network.nodes())

social_network = deepcopy(_shared["social_network"])
initial_social = deepcopy(social_network)

global_betas = _shared["global_betas"][:num_simulations]

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

def baseline_infections(sim_index=0):
    contact_network = deepcopy(initial_contact)
    social_network = deepcopy(initial_social)

    full_dynamics = None
    prev_state_dict = None
    static_beta = global_betas[sim_index]
    baseline_newly_counts = []

    for t_cur in range(T):
        simulation_results = SIR.Simulate_SIR(
            contact_network=contact_network,
            social_network=social_network,
            T=1,
            q=False,
            beta=static_beta,
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

# Edge-cost analogue of baseline_infections(): every node is informed from t=0 with
# full adherence, so any infected node quarantines (and its edges get cut) as soon as
# possible under the module's actual q="r" restoration policy. This is the realistic
# worst case for edge loss -- "what a maximal-but-real quarantine policy costs" --
# rather than the static, dynamics-free "every edge in the graph is gone" bound.
def baseline_edge_removals(sim_index=0):
    contact_network = deepcopy(initial_contact)
    social_network = deepcopy(initial_social)

    all_edges = initial_contact.edges()
    edge_cost_dict = {(u, v): data.get('weight', 1) for u, v, data in initial_contact.edges(data=True)}
    all_nodes = list(contact_network.nodes())

    prev_state_dict = None
    static_beta = global_betas[sim_index]
    baseline_edge_costs = []

    for t_cur in range(T):
        simulation_results = SIR.Simulate_SIR(
            contact_network=contact_network,
            social_network=social_network,
            T=1,
            q=q,
            q_mech=("lt", 1),  # every node is already seeded; avoid IC's 1000-trial Monte Carlo per tick
            beta=static_beta,
            gamma=gamma,
            mu=mu,
            init=init,
            adherence=1.0,
            seeds=all_nodes,
            initial_state_dict=prev_state_dict,
        )

        contact_network = deepcopy(initial_contact)
        sirs_dynamics = simulation_results[4]
        prev_state_dict = sirs_dynamics[-1]

        graph_vec = simulation_results[10]
        live_edges_t = list(graph_vec[-1])
        removed_edges = set(all_edges) - set(live_edges_t)
        edge_removal_cost = sum(edge_cost_dict[edge] for edge in removed_edges)
        baseline_edge_costs.append(edge_removal_cost)

    return baseline_edge_costs

# Collect per-timestep newly infected counts from baseline (no-quarantine) runs
baseline_runs = []
for _sim_i in range(num_simulations):
    baseline_newly_counts, _ = baseline_infections(_sim_i)
    baseline_runs.append(baseline_newly_counts)

# Collect per-timestep edge-removal costs from baseline (full-quarantine) runs
edge_baseline_runs = []
for _sim_i in range(num_simulations):
    edge_baseline_runs.append(baseline_edge_removals(_sim_i))

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

    # Only accumulate cost since the most recent batch selection. When seeds are
    # reselected every single step (batch_interval == 1) there is no distinct batch
    # to window against, so fall back to summing over the entire history instead.
    if batch_interval == 1:
        window_start = 0
    else:
        window_start = (t_cur // batch_interval) * batch_interval

    total_edge_removal_cost = 0
    # Compute sum of removed edges at each time step since the last batch selection
    for t in range(window_start, t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    newly_infected_sum = np.sum(newly_infected[window_start:t_cur + 1])

    # Adjust penalty weights so that each term contributes equally to cost function.
    # Both are counterfactual-simulation bounds now, not one dynamic (infections) and
    # one static worst-case (edges): g comes from the no-quarantine baseline, h from
    # the full-quarantine baseline (see baseline_infections / baseline_edge_removals).
    removal_cost = 1

    g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, t_cur + 1))
    h = sum(max(run[t] for run in edge_baseline_runs) for t in range(window_start, t_cur + 1))

    alpha_w = 1 / g if g > 0 else 1.0
    beta_w = 1 / h if h > 0 else 1.0

    # cost_elements carries alpha_w/beta_w alongside the raw sums so downstream
    # plotting (cost_curve_store.plot_joint_cost_elements) can show each term
    # weighted the same way it contributes to the returned cost, rather than as
    # raw, differently-scaled counts.
    cost_elements = (newly_infected_sum, total_edge_removal_cost, alpha_w, beta_w)

    # Print cost components
    print(f"Cost components at time {t_cur}:")
    print(f"  Newly infected sum: {newly_infected_sum}")
    print(f"  Total edge removal cost: {total_edge_removal_cost}")
    print(f" alpha_w: {alpha_w:.4f}, beta_w: {beta_w:.4f}")

    return alpha_w * newly_infected_sum + beta_w * removal_cost * total_edge_removal_cost, cost_elements

def milp_seed_selection_stepwise():
    """
    Step-wise MILP seed selection: re-solve the MILP at each batch boundary,
    using baseline-run normalization to weight the objective for that batch.

    alpha_w_t = 1 / g_t, beta_w_t = 1 / h_t, where g_t comes from the no-quarantine
    baseline and h_t from the full-quarantine baseline (baseline_runs / edge_baseline_runs)
      -- identical in form to global_cost_function/adaptive_seed_selection's cost
         weighting, computed over the window of the upcoming batch: [t_cur,
         min(t_cur + batch_interval, T) - 1] (or, with batch_interval == 1, the
         cumulative window [0, t_cur], matching the "no distinct batch" case).

    Seeds and edge removals are chosen fresh at each batch boundary and held
    fixed for the remainder of the batch (not accumulated). The constraint
    matrix is built once; only the objective vector c changes.
    """
    nodes = list(initial_contact.nodes())
    edges = list(initial_contact.edges())
    N = len(nodes)
    E = len(edges)
    node_idx = {v: i for i, v in enumerate(nodes)}

    edge_weights = np.array([initial_contact[u][v].get('weight', 1) for u, v in edges])

    K = int((3/4) * n)  # Seed budget, matches adaptive_seed_selection.py

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
    all_infection_term_curves = []
    all_edge_term_curves      = []
    all_alpha_w_curves        = []
    all_beta_w_curves         = []
    winner_sets               = []   # list[sim] of list[step] of seed lists
    all_edge_curves           = []
    all_newly_infected_counts = []
    all_newly_infected_frac   = []
    all_full_dynamics         = []

    for sim_i in range(num_simulations):
        print(f"MILP step-wise simulation {sim_i}")

        social_network  = deepcopy(initial_social)
        static_beta     = global_betas[sim_i]

        cost_lst                    = []
        infection_term_lst          = []
        edge_term_lst               = []
        alpha_w_lst                 = []
        beta_w_lst                  = []
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
                # --- alpha_w / beta_w over the window this batch will cover, using
                #     baseline_runs/edge_baseline_runs -- identical normalization to
                #     global_cost_function, just computed prospectively so it can
                #     weight the MILP objective before this batch's simulation runs.
                if batch_interval == 1:
                    window_start = 0
                    window_end = t_cur
                else:
                    window_start = t_cur
                    window_end = min(t_cur + batch_interval, T) - 1

                g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, window_end + 1))
                h = sum(max(run[t] for run in edge_baseline_runs) for t in range(window_start, window_end + 1))
                alpha_w = 1.0 / g if g > 0 else 1.0
                beta_w = 1.0 / h if h > 0 else 1.0

                # --- Objective for this batch (alpha_w and beta_w change) ---
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
                    beta               = static_beta,
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
                cost, cost_elements = global_cost_function(
                    newly_infected_per_sim, full_live_edges, t_cur
                )
                cost_lst.append(cost)
                infection_term_lst.append(cost_elements[0])
                edge_term_lst.append(cost_elements[1])
                alpha_w_lst.append(cost_elements[2])
                beta_w_lst.append(cost_elements[3])

        winner_sets.append(seeds_per_step)
        all_cost_curves.append(cost_lst)
        all_infection_term_curves.append(infection_term_lst)
        all_edge_term_curves.append(edge_term_lst)
        all_alpha_w_curves.append(alpha_w_lst)
        all_beta_w_curves.append(beta_w_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return (winner_sets, all_cost_curves, all_infection_term_curves, all_edge_term_curves, all_edge_curves,
            all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics,
            all_alpha_w_curves, all_beta_w_curves)


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
        static_beta     = global_betas[i]

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
                beta=static_beta,
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
     milp_infection_curves,
     milp_edge_term_curves,
     milp_edge_curves,
     milp_newly_counts,
     milp_newly_frac,
     milp_dynamics_list,
     milp_alpha_w_curves,
     milp_beta_w_curves) = milp_seed_selection_stepwise()

    avg_seeds = np.mean([[len(s) for s in sim] for sim in winner_sets])
    print(f"\nStep-wise MILP: avg seeds/step across all sims = {avg_seeds:.1f}")

    # Quick summary statistics across simulations
    mean_cost  = np.mean([c[-1] for c in milp_cost_curves])
    mean_infec = np.mean([sum(counts) for counts in milp_newly_counts])
    print(f"Mean final cost (across {num_simulations} sims): {mean_cost:.6f}")
    print(f"Mean total new infections                      : {mean_infec:.1f}")

    # Push this run's cost curve -- plus raw infection/edge cost-element curves and the
    # alpha_w/beta_w that weight them into the returned cost -- into the store shared
    # with adaptive_seed_selection.py. Once adaptive_seed_selection.py has also been
    # run, call cost_curve_store.plot_joint_cost_comparison() / plot_joint_cost_elements()
    # (e.g. `python cost_curve_store.py`) to render the combined figures.
    cost_curve_store.push_curve("MILP", milp_cost_curves,
                                 infection_curves=milp_infection_curves, edge_curves=milp_edge_term_curves,
                                 alpha_curves=milp_alpha_w_curves, beta_curves=milp_beta_w_curves)
