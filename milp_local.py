"""
MILP-based seed selection -- local/structural horizon-bound variant of milp.py.

Two deltas from milp.py:

(1) Horizon bounds for alpha_w / beta_w are local structural quantities instead of
    simulated-baseline / graph-wide bounds:
      - beta_w's denominator is the max weighted-degree sum reachable by a strict
        K-sized seed set (sum of the K largest node degrees), not "every edge in
        the graph." No baseline simulation needed.
      - alpha_w's denominator is the summed weighted-degree of nodes that were
        *actually* infected at each tick in the window (an upper bound on that
        tick's transmission opportunities), not a separately-simulated
        no-intervention counterfactual. This removes the baseline_infections()
        Monte Carlo pass entirely.
    Both bounds are "sum of degree over a node subset," so they share the same
    kind of looseness (double-counting when two subset members share an edge)
    rather than one term being simulation-grounded and the other a static cap.

(2) The seed-budget constraint is an equality (sum(x) == K), not sum(x) <= K, so
    every batch places exactly K = (3/4) * n seeds rather than merely being
    permitted to.

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
init = 0.05
num_simulations = 10

batch_interval = 2  # MILP is re-solved and cost updated once every batch_interval steps
information_spread = True

# Shared with adaptive_seed_selection.py / milp.py: identical contact network, social
# network, edge weights, and per-simulation heterogeneous beta maps (see
# network_setup.py) so all approaches are compared against the exact same setup.
_shared = network_setup.load_shared_network(min_simulations=num_simulations)
contact_network = deepcopy(_shared["contact_network"])
initial_contact = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
n = len(contact_network.nodes())

social_network = deepcopy(_shared["social_network"])
initial_social = deepcopy(social_network)

global_betas = _shared["global_betas"][:num_simulations]

# --- Strict seed budget + its structural (non-simulated) degree bound ---
K = int((3/4) * n)  # Seed budget, enforced as an EQUALITY constraint below

node_degree = dict(initial_contact.degree(weight='weight'))
# Loose upper bound on total edge-weight reachable by any exactly-K-sized seed set
# (sum of the K largest degrees; double-counts edges between two high-degree seeds,
# same looseness as the infection-degree bound below -- kept simple on purpose).
top_K_degree_sum = sum(sorted(node_degree.values(), reverse=True)[:K])

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

# Global utility function: Find a small seed set which minimizes infection spread,
# while maximizing number of live edges in the network.
# newly_infected: array of newly infected counts at each time step
# live_edges: array of live EDGES at each step
# state_series: array of {node: state} dicts at each absolute tick (0=S, 1=I, 2=R)
def global_cost_function(newly_infected, live_edges, state_series, t_cur):
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
    window_len = t_cur - window_start + 1

    total_edge_removal_cost = 0
    infection_degree_bound = 0
    # Compute sum of removed edges, and sum of infected-node degree, at each time
    # step since the last batch selection
    for t in range(window_start, t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)
        total_edge_removal_cost += edge_removals

        infected_nodes = [node for node in node_degree if state_series[t][node] == 1]
        infection_degree_bound += sum(node_degree[node] for node in infected_nodes)

    newly_infected_sum = np.sum(newly_infected[window_start:t_cur + 1])

    cost_elements = (newly_infected_sum, total_edge_removal_cost)

    # Local/structural horizon bounds (see module docstring): alpha_w scales against
    # the realized infection-degree bound for this window; beta_w scales against the
    # max degree-sum reachable by the strict K-seed budget. No baseline simulation.
    removal_cost = 1

    alpha_w = 1 / infection_degree_bound if infection_degree_bound > 0 else 1.0
    beta_w = 1 / (window_len * top_K_degree_sum)

    # Print cost components
    print(f"Cost components at time {t_cur}:")
    print(f"  Newly infected sum: {newly_infected_sum}")
    print(f"  Total edge removal cost: {total_edge_removal_cost}")
    print(f"  Infection-degree bound: {infection_degree_bound}, top-K degree sum: {top_K_degree_sum}")
    print(f" alpha_w: {alpha_w:.4f}, beta_w: {beta_w:.4f}")

    return alpha_w * newly_infected_sum + beta_w * removal_cost * total_edge_removal_cost, cost_elements

def milp_seed_selection_stepwise():
    """
    Step-wise MILP seed selection: re-solve the MILP at each batch boundary,
    using local structural-bound normalization to weight the objective for that batch.

    alpha_w_t = 1 / (window_len_t * infection_degree_now), beta_w_t = 1 / (window_len_t * top_K_degree_sum)
      -- identical in form to global_cost_function's weighting, computed prospectively
         (using the state known at the start of the batch) so it can weight the MILP
         objective before that batch's simulation has run.

    Seeds and edge removals are chosen fresh at each batch boundary and held
    fixed for the remainder of the batch (not accumulated). The constraint
    matrix is built once; only the objective vector c changes. The seed-budget
    constraint is an EQUALITY (sum(x) == K): every batch places exactly K seeds.
    """
    nodes = list(initial_contact.nodes())
    edges = list(initial_contact.edges())
    N = len(nodes)
    E = len(edges)
    node_idx = {v: i for i, v in enumerate(nodes)}

    edge_weights = np.array([initial_contact[u][v].get('weight', 1) for u, v in edges])

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
    lb_con[0] = K  # strict budget: exactly K seeds every batch, not "up to K"

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
        print(f"MILP-local step-wise simulation {sim_i}")

        social_network  = deepcopy(initial_social)
        static_beta     = global_betas[sim_i]

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
                # --- alpha_w / beta_w over the window this batch will cover, using
                #     ONLY state known at solve time (prev_state_dict) -- identical
                #     structural-bound normalization to global_cost_function, just
                #     computed prospectively so it can weight the MILP objective. ---
                if batch_interval == 1:
                    window_start = 0
                    window_end = t_cur
                else:
                    window_start = t_cur
                    window_end = min(t_cur + batch_interval, T) - 1
                window_len = window_end - window_start + 1

                if prev_state_dict is None:
                    current_infection_degree = 0
                else:
                    current_infection_degree = sum(
                        node_degree[v] for v in node_degree if prev_state_dict[v] == 1
                    )
                g = current_infection_degree * window_len
                alpha_w = 1.0 / g if g > 0 else 1.0
                beta_w = 1.0 / (window_len * top_K_degree_sum)

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
                cost, _ = global_cost_function(
                    newly_infected_per_sim, full_live_edges, full_dynamics, t_cur
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
                newly_infected_per_sim, full_live_edges, full_dynamics, t_cur
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
    print(f"\nStep-wise MILP-local: avg seeds/step across all sims = {avg_seeds:.1f} (budget K = {K})")

    # Quick summary statistics across simulations
    mean_cost  = np.mean([c[-1] for c in milp_cost_curves])
    mean_infec = np.mean([sum(counts) for counts in milp_newly_counts])
    print(f"Mean final cost (across {num_simulations} sims): {mean_cost:.6f}")
    print(f"Mean total new infections                      : {mean_infec:.1f}")

    # Push this run's cost curve into the store shared with milp.py / adaptive_seed_selection.py.
    # Once the others have also been run, call cost_curve_store.plot_joint_cost_comparison()
    # (e.g. `python cost_curve_store.py`) to render the combined figure.
    cost_curve_store.push_curve("MILP-Local", milp_cost_curves)
