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

batch_interval = 5  # MILP is re-solved and cost updated once every batch_interval steps
information_spread = True

# Beta-generation params, only used when initialize() is given a custom network
# (a shared network's betas come pre-generated from network_setup's own copies of
# these same parameters -- see network_setup.generate_global_betas).
HETEROGENEOUS_BETA = True  # True: node-wise beta drawn from power-law distribution; False: scalar beta for all nodes
beta = 0.15  # Used directly when HETEROGENEOUS_BETA=False; ignored when True
beta_L = 0.05   # Lower bound for heterogeneous beta
beta_R = 0.25   # Upper bound for heterogeneous beta
Gamma  = 2      # Shape parameter: higher values skew beta toward beta_R

# Network-dependent globals -- populated by initialize()
contact_network     = None
initial_contact     = None
initial_edge_count  = None
n                   = None
social_network      = None
initial_social      = None
global_betas        = None
baseline_runs       = None


def compute_node_beta(graph):
    if not HETEROGENEOUS_BETA:
        return beta
    return network_setup.laplacian_smooth_beta(graph, beta_L, beta_R, lam=Gamma)


# network: None to use the synthetic network shared with adaptive_seed_selection.py
#   (see network_setup.py) -- both approaches then compare against an identical
#   contact network, social network, and set of per-simulation heterogeneous beta
#   maps. Pass an nx.Graph or a string path to a GML file to run against a specific
#   network instead; in that case the beta maps are generated locally for that
#   network only, independent of the shared cache.
# social: None to synthesize a social network from the contact network via
#   correlated_graphs.create_social_graph (used whenever `network` is also a
#   custom graph/path). Pass an nx.Graph or a string path to a GML file to use a
#   real social network instead -- e.g. rc_social_network.gml. GML node identity
#   comes from the "label" field (nx.read_gml's default), which for the rc_*
#   dataset is the real participant ID and lines up across the contact/social
#   pair, so nodes are intersected on that label and remapped to a shared set of
#   integer ids before use. Ignored when `network` is None.
def initialize(network=None, social=None):
    """Load a contact network and run baseline simulations. Must be called once
    before milp_seed_selection_stepwise() / no_quarantine_baseline_runs()."""
    global contact_network, initial_contact, initial_edge_count, n
    global social_network, initial_social, global_betas, baseline_runs

    if network is None:
        shared = network_setup.load_shared_network(min_simulations=num_simulations)
        contact_network = deepcopy(shared["contact_network"])
        social_network  = deepcopy(shared["social_network"])
        global_betas    = shared["global_betas"][:num_simulations]
    else:
        contact_network = nx.read_gml(network) if isinstance(network, str) else network
        isolated_nodes = [node for node in contact_network.nodes()
                          if contact_network.degree(node) == 0]
        contact_network.remove_nodes_from(isolated_nodes)

        if social is None:
            contact_network = nx.convert_node_labels_to_integers(contact_network, first_label=0)

            # Social network needs real edge structure: information diffusion (IC/LT/FJ) in
            # SIR.Simulate_SIR spreads over social_network's edges, so an edgeless graph means
            # the informed set can never grow past the initial seeds.
            social_network, _ = correlated_graphs.create_social_graph(
                contact_network, 2 * contact_network.number_of_edges())
        else:
            social_network = nx.read_gml(social) if isinstance(social, str) else social

            # Contact and social GML files aren't guaranteed to cover identical node
            # sets, so intersect them on label first, then remap that shared set onto
            # integers 0..n-1 with ONE mapping applied to both graphs -- node ids must
            # agree exactly between the two networks.
            common_nodes = [node for node in contact_network.nodes() if social_network.has_node(node)]
            contact_network = contact_network.subgraph(common_nodes).copy()
            social_network  = social_network.subgraph(common_nodes).copy()
            mapping = {node: i for i, node in enumerate(contact_network.nodes())}
            contact_network = nx.relabel_nodes(contact_network, mapping)
            social_network  = nx.relabel_nodes(social_network, mapping)

        global_betas = [compute_node_beta(contact_network) for _ in range(num_simulations)]

    initial_contact    = deepcopy(contact_network)
    initial_edge_count = contact_network.number_of_edges()
    n                  = len(contact_network.nodes())
    initial_social     = deepcopy(social_network)

    # Collect per-timestep newly infected counts from baseline (no-quarantine) runs
    baseline_runs = []
    for sim_i in range(num_simulations):
        baseline_newly_counts, _ = baseline_infections(sim_i)
        baseline_runs.append(baseline_newly_counts)


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
    edge_cost_bound = sum(edge_cost_dict.values())  # cost of losing every edge in one step

    # Only accumulate cost since the most recent batch selection. When seeds are
    # reselected every single step (batch_interval == 1) there is no distinct batch
    # to window against, so fall back to summing over the entire history instead.
    if batch_interval == 1:
        window_start = 0
    else:
        window_start = (t_cur // batch_interval) * batch_interval
    window_len = t_cur - window_start + 1

    total_edge_removal_cost = 0
    # Compute sum of removed edges at each time step since the last batch selection
    for t in range(window_start, t_cur + 1):
        removed_edges = set(all_edges) - set(live_edges[t])
        edge_removals = sum(edge_cost_dict[edge] for edge in removed_edges)

        total_edge_removal_cost += edge_removals

    newly_infected_sum = np.sum(newly_infected[window_start:t_cur + 1])

    # Adjust penalty weights so that each term contributes equally to cost function.
    # g: no-quarantine counterfactual bound (see baseline_infections) -- more
    # quarantine can only ever reduce infections, so this is a true upper bound.
    # h: static worst case instead -- N steps into the batch, the most edge cost
    # you could possibly have incurred is N * (sum of every edge's removal cost),
    # i.e. every edge in the graph gone at every step. A full-quarantine simulated
    # "counterfactual" bound doesn't actually bound this: aggressive quarantine
    # suppresses spread so effectively that it can rack up LESS cumulative edge
    # cost than a realistic, imperfect policy that lets the epidemic reach more
    # nodes over the window -- letting the real numerator exceed that "bound".
    removal_cost = 1

    g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, t_cur + 1))
    h = window_len * edge_cost_bound

    alpha_w = 1 / g if g > 0 else 1.0
    beta_w = 1 / h if h > 0 else 1.0

    # cost_elements carries alpha_w/beta_w alongside the raw sums so downstream
    # plotting (cost_curve_store.plot_joint_cost_elements) can show each term
    # weighted the same way it contributes to the returned cost, rather than as
    # raw, differently-scaled counts.
    cost_elements = (newly_infected_sum, total_edge_removal_cost, alpha_w, beta_w)

    # Cap each term at 1 so the maximum possible total cost per step is 2.
    infection_term = min(alpha_w * newly_infected_sum, 1.0)
    edge_term = min(beta_w * removal_cost * total_edge_removal_cost, 1.0)
    return infection_term + edge_term, cost_elements

def milp_seed_selection_stepwise():
    """
    Step-wise MILP seed selection: re-solve the MILP at each batch boundary,
    using baseline-run normalization to weight the objective for that batch.

    alpha_w_t = 1 / g_t, beta_w_t = 1 / h_t, where g_t comes from the no-quarantine
    baseline (baseline_runs) and h_t is the static worst-case edge-cost bound --
    window length times the cost of losing every edge in the graph (see
    global_cost_function)
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
    edge_cost_bound = edge_weights.sum()  # cost of losing every edge in one step

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
                #     baseline_runs / the static edge-cost bound -- identical
                #     normalization to global_cost_function, just computed
                #     prospectively so it can weight the MILP objective before this
                #     batch's simulation runs.
                if batch_interval == 1:
                    window_start = 0
                    window_end = t_cur
                else:
                    window_start = t_cur
                    window_end = min(t_cur + batch_interval, T) - 1
                window_len = window_end - window_start + 1

                g = sum(max(run[t] for run in baseline_runs) for t in range(window_start, window_end + 1))
                h = window_len * edge_cost_bound
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
                print(f"MILP, {t_cur}, {cost}")
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
            print(f"No-Quarantine, {t_cur}, {cost}")
            cost_lst.append(cost)

        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_counts.append(newly_infected_per_sim)
        all_newly_frac.append(newly_infected_frac_per_sim)
        all_full_dynamics.append(full_dynamics)

    return all_cost_curves, all_edge_curves, all_newly_counts, all_newly_frac, all_full_dynamics


if __name__ == "__main__":
    # ── CHOOSE NETWORK FILES HERE ───────────────────────────────────────────
    # Swap these two paths to run against a different contact/social pair (or set
    # both to None to fall back to the synthetic network shared with
    # adaptive_seed_selection.py). Keep in sync with adaptive_seed_selection.py's
    # own CONTACT_NETWORK_PATH / SOCIAL_NETWORK_PATH so both approaches are
    # compared against the exact same setup.
    # CONTACT_NETWORK_PATH = "capstone_proj_data/rc_weighted_contact_bin14.gml"
    # SOCIAL_NETWORK_PATH  = "capstone_proj_data/rc_social_network.gml"

    CONTACT_NETWORK_PATH = None
    SOCIAL_NETWORK_PATH = None


    # ─────────────────────────────────────────────────────────────────────────

    initialize(CONTACT_NETWORK_PATH, SOCIAL_NETWORK_PATH)

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
                                 alpha_curves=milp_alpha_w_curves, beta_curves=milp_beta_w_curves,
                                 batch_interval=batch_interval, T=T)
