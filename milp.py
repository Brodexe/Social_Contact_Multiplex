"""
MILP-based seed selection for epidemic control.


alpha_w * I_proxy + beta_w * edge_removal_cost + gamma_w * seed_set_size

Decision variables (all binary):
    x_v  in {0,1}  -- node v is in the seed set
    y_e  in {0,1}  -- edge e remains live (1) or is removed (0)
    z_e  in {0,1}  -- edge e is "active": live AND neither endpoint is a seed
                      serves as a static proxy for infection risk

z_e = y_e * (1 - x_u) * (1 - x_v)  is linearized with 4 constraints per edge:
    (a)  z_e - y_e          <=  0
    (b)  z_e + x_u          <=  1
    (c)  z_e + x_v          <=  1
    (d)  z_e - y_e + x_u + x_v  >=  0   (forces z_e=1 when y_e=1, x_u=x_v=0)

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
from adaptive_seed_selection import (given_at_time, global_cost_function,
                                        introduced_infections)

q = "r"
adherence = 1
n = 200
p = 0.05
T = 100

contact_network = nx.erdos_renyi_graph(n, p, seed=42)
initial_contact = deepcopy(contact_network)
initial_edge_count = contact_network.number_of_edges()
social_network = correlated_graphs.create_social_graph(contact_network, 2 * initial_edge_count)[0]
social_network = nx.erdos_renyi_graph(n, p, seed=24)
initial_social = deepcopy(social_network)


beta = 0.15
gamma = 0.07 # Recovery rate
mu = 0.05 # Immunity loss rate
init = 0.05
num_simulations = 10


def milp_seed_selection():
    """
    Solve the MILP, then simulate num_simulations runs with the optimal seeds
    and edge removals.  Returns results in the same format as hill_climb() and
    degree_based_selection().
    """
    K = int(0.025 * n)

    nodes = list(initial_contact.nodes())
    edges = list(initial_contact.edges())
    N = len(nodes)
    E = len(edges)

    node_idx = {v: i for i, v in enumerate(nodes)}

    # ------------------------------------------------------------------ #
    #  Cost weights  (identical to global_cost_function)                  #
    # ------------------------------------------------------------------ #
    edge_cost_bound = E          # uniform edge cost = 1
    beta_w  = 1.0 / (T * edge_cost_bound)
    gamma_w = 1.0 / n
    alpha_w = 1.0 / stochastic_max_n_i

    # ------------------------------------------------------------------ #
    #  Objective  c^T v  (minimise)                                       #
    #                                                                     #
    #  x_v : +gamma_w          (seed set size penalty)                   #
    #  y_e : -beta_w           (more live edges  => less removal cost)   #
    #  z_e : +alpha_w * beta   (active edge  =>  infection proxy)        #
    #                                                                     #
    #  The constant  +beta_w * E  is dropped (doesn't affect solution).  #
    # ------------------------------------------------------------------ #
    n_vars = N + 2 * E
    c = np.zeros(n_vars)
    c[:N]       = gamma_w
    c[N:N+E]    = -beta_w
    c[N+E:]     = alpha_w * beta

    # ------------------------------------------------------------------ #
    #  Variable bounds and integrality                                    #
    # ------------------------------------------------------------------ #
    X_bounds    = Bounds(lb=np.zeros(n_vars), ub=np.ones(n_vars))
    integrality = np.ones(n_vars)   # all binary

    # ------------------------------------------------------------------ #
    #  Constraint matrix                                                  #
    #  Row 0          : sum(x_v) <= K                                    #
    #  Rows 1+4i..+3  : linearisation constraints for edge i             #
    # ------------------------------------------------------------------ #
    n_con  = 1 + 4 * E
    A      = lil_matrix((n_con, n_vars))
    lb_con = np.full(n_con, -np.inf)
    ub_con = np.full(n_con,  np.inf)

    # Seed budget
    A[0, :N] = 1.0
    ub_con[0] = K

    for i, (u, v) in enumerate(edges):
        ui = node_idx[u]
        vi = node_idx[v]
        yi = N + i          # y_e column
        zi = N + E + i      # z_e column
        r  = 1 + 4 * i

        # (a)  z_e - y_e <= 0
        A[r,   zi] =  1;  A[r,   yi] = -1
        ub_con[r]  =  0

        # (b)  z_e + x_u <= 1
        A[r+1, zi] =  1;  A[r+1, ui] =  1
        ub_con[r+1] = 1

        # (c)  z_e + x_v <= 1
        A[r+2, zi] =  1;  A[r+2, vi] =  1
        ub_con[r+2] = 1

        # (d)  z_e - y_e + x_u + x_v >= 0
        A[r+3, zi] =  1;  A[r+3, yi] = -1
        A[r+3, ui] =  1;  A[r+3, vi] =  1
        lb_con[r+3] = 0

    lc = LinearConstraint(csr_matrix(A), lb_con, ub_con)

    # ------------------------------------------------------------------ #
    #  Solve                                                              #
    # ------------------------------------------------------------------ #
    print("Solving MILP ...")
    res = milp(c=c, bounds=X_bounds, constraints=[lc], integrality=integrality)

    if not res.success:
        print(f"MILP solver failed: {res.message}")
        return [], [], [], [], [], []

    x_sol = np.round(res.x[:N]).astype(int)
    y_sol = np.round(res.x[N:N+E]).astype(int)
    z_sol = np.round(res.x[N+E:]).astype(int)

    milp_seeds   = [nodes[i] for i in range(N) if x_sol[i] == 1]
    milp_removed = {edges[i] for i in range(E) if y_sol[i] == 0}

    # Report objective components (add back the dropped constant for clarity)
    infection_proxy    = alpha_w * beta * float(np.sum(z_sol))
    edge_removal_cost  = beta_w  * float(np.sum(1 - y_sol))
    seed_cost          = gamma_w * len(milp_seeds)
    milp_obj           = infection_proxy + edge_removal_cost + seed_cost

    print(f"MILP objective : {milp_obj:.6f}")
    print(f"  infection proxy  (alpha_w*beta*sum z_e) : {infection_proxy:.6f}")
    print(f"  edge removal     (beta_w *sum(1-y_e))   : {edge_removal_cost:.6f}")
    print(f"  seed set size    (gamma_w*|S|)           : {seed_cost:.6f}")
    print(f"  seeds selected   : {len(milp_seeds)} / {N}")
    print(f"  edges kept live  : {int(np.sum(y_sol))} / {E}  "
          f"(removed {len(milp_removed)})")
    print(f"  unprotected edges: {int(np.sum(z_sol))}")

    # ------------------------------------------------------------------ #
    #  Simulate with MILP-chosen seeds + pre-removed edges               #
    #  (mirrors degree_based_selection loop structure)                    #
    # ------------------------------------------------------------------ #
    all_cost_curves          = []
    winner_sets              = []
    all_edge_curves          = []
    all_newly_infected_counts = []
    all_newly_infected_frac  = []
    all_full_dynamics        = []

    # Base network with MILP edge removals permanently applied
    milp_contact_base = deepcopy(initial_contact)
    milp_contact_base.remove_edges_from(milp_removed)

    for sim_i in range(num_simulations):
        print(f"MILP simulation {sim_i}")

        contact_network = deepcopy(milp_contact_base)
        social_network  = deepcopy(initial_social)

        cost_lst                  = []
        full_dynamics             = None
        prev_state_dict           = None
        full_live_edges           = None
        edge_counts               = []
        newly_infected_per_sim    = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            # Optional random new infections (same as other methods)
            if t_cur % introduced_infections[1] == 0 and t_cur > 0:
                num_to_infect = int(introduced_infections[0] * n)
                candidates    = list(contact_network.nodes())
                new_inf_nodes = random.sample(candidates,
                                              min(num_to_infect, len(candidates)))
                for node in new_inf_nodes:
                    prev_state_dict[node] = 0

            simulation_results = SIR.Simulate_SIR(
                contact_network     = contact_network,
                social_network      = social_network,
                T                   = 1,
                beta                = beta,
                gamma               = gamma,
                mu                  = mu,
                init                = init,
                q                   = q,
                adherence           = adherence,
                begin_q             = 0,
                seeds               = milp_seeds,
                initial_state_dict  = prev_state_dict,
            )

            # Reset to MILP-modified base (preserves pre-removed edges)
            contact_network = deepcopy(milp_contact_base)

            sirs_dynamics   = simulation_results[4]
            prev_state_dict = sirs_dynamics[-1]
            full_dynamics   = (sirs_dynamics if full_dynamics is None
                               else full_dynamics + sirs_dynamics)

            current_new_i = given_at_time(t_cur, full_dynamics, contact_network)
            newly_infected_per_sim.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            graph_vec       = simulation_results[10]
            live_edges      = [list(network) for network in graph_vec]
            full_live_edges = (live_edges if full_live_edges is None
                               else full_live_edges + live_edges)
            edge_counts.append(len(live_edges[-1]))

            cost, _ = global_cost_function(
                newly_infected_per_sim, full_live_edges, len(milp_seeds), t_cur
            )
            cost_lst.append(cost)

        winner_sets.append(milp_seeds)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_per_sim)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return (milp_seeds, all_cost_curves, all_edge_curves,
            all_newly_infected_counts, all_newly_infected_frac, all_full_dynamics)


if __name__ == "__main__":
    (milp_seeds,
     milp_cost_curves,
     milp_edge_curves,
     milp_newly_counts,
     milp_newly_frac,
     milp_dynamics_list) = milp_seed_selection()

    print(f"\nFinal MILP seed set ({len(milp_seeds)} nodes): {sorted(milp_seeds)}")

    # Quick summary statistics across simulations
    mean_cost  = np.mean([c[-1] for c in milp_cost_curves])
    mean_infec = np.mean([sum(counts) for counts in milp_newly_counts])
    print(f"Mean final cost (across {num_simulations} sims): {mean_cost:.6f}")
    print(f"Mean total new infections                      : {mean_infec:.1f}")
