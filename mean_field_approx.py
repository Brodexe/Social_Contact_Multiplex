import SIR
import networkx as nx
import correlated_graphs
import find_seeds
from copy import deepcopy
import numpy as np
from scipy.optimize import minimize
import random
import os
import sys
import pickle as pkl
import ast
import shelve

#----------
#
#  Mean-field approximation for SIR model: n_i = beta * <k> (1 - n_r / gamma - r) * (n_r / gamma)
#  Assuming n_i, n_r, SIR parameters are known, this gives us the constrained, non-linear optimization problem:
#    y = w1 * x1 * (x2 - w2), where <w1, w2> are the model weights to be learned (mean node degree, recovered ratio, respectively).
#
#----------

social_graph = None
contact_graph = None

# Generate contact graph
n = 200  # number of nodes
p = 0.05  # probability of edge

load_initial = False
  # Set to True if you want to existing epidemic states from pickle file
clear = False  # Set clear to True if you want to use a new network or clear data files. False if you want to keep the existing one.
verbose = True  # Set verbose to True if you want to see detailed output during optimization
mode = None  # None (standard) or "adherence" or "YJMOB" or "sensitivity analysis"
if sys.argv[-1] == "yjmob mode":
    mode = "YJMOB"
elif sys.argv[-1] == "adherence mode":
    mode = "adherence"
elif sys.argv[-1] == "sensitivity analysis mode":
    mode = "sensitivity analysis"

file_index = None   # Used for reading from network files, choosing write file names
yjmob_size = None  # Network size for YJMOB dataset (100, 250, 500, or 1000)
# Form: python mean_field_approx.py <file index> <size>
# Used with YJMOB dataset
if mode == "YJMOB":
    file_index = int(sys.argv[1])
    yjmob_size = int(sys.argv[2])

    # For initial interval, we do not load previous states
    # Note: previous states are always saved after each run, and overwrite the existing file
    if file_index >= 1 and file_index != 5:
        load_initial = True

write_file = "experiment_data/mfa_xy_data.txt"
# Overwrite write_file if provided as command line argument

# Form: python mean_field_approx.py <write_file> <adherence>
# Used when running multiple simulations with different adherence levels
if mode == "adherence":
    write_file = sys.argv[1]
elif mode == "YJMOB":
    write_file = f"experiment_data/yjmob{file_index}_runs.txt"
elif mode == "sensitivity analysis":
    write_file = sys.argv[3]

adherence = 1.0 # Proportion of individuals who sever contact edges upon infection
# Overwrite adherence if provided as command line argument
if mode == "adherence":
    adherence = float(sys.argv[2])

initial_states = None
seeds = None
adhering = None
if load_initial == True:
    # Load initial states from pickle file if it exists
    try:
        with open("experiment_data/mfa_initial_state.pkl", "rb") as f:
            unpickled_data = pkl.load(f)
            # Dictionary of node states
            initial_states = unpickled_data.get("New Initial States", None)
            # List of informed individuals
            seeds = unpickled_data.get("New Informed", None)
            # Set of adhering individuals
            adhering = unpickled_data.get("Adhering", None)

    except (FileNotFoundError, OSError, ValueError, pkl.UnpicklingError, EOFError) as e:
        initial_states = None
        seeds = None
        adhering = None

# Simulation parameters
T = 100
beta = 0.15  # Infection rate
gamma = 0.07  # Recovery rate
mu = 0.05  # Immunity loss rate
init = 0.1 # Initial infected portion
q = "r"  # Quarantine type: indiviuals restore edges when recovered
split_point = 30  # Set to None if you want to optimize over the full SIR simulation, or a specific time point to split the optimization
density_social = None  # Set to None for default density, or an integer number of edges in the social graph
noisy_data = True  # If True, add measurement noise to newly infected/recovered measurements
noise_type = "poisson"  # "gaussian" or "poisson" (used only when noisy_data is True)
gaussian_noise_scale = 0    # Gaussian noise scale: std of added noise = gaussian_noise_scale * sqrt(p(1-p)/n) (used only when noise_type == "gaussian")
poisson_noise_scale = (1)  # Poisson noise scale: variance of added noise = poisson_noise_scale * (true count) (used only when noise_type == "poisson")

# YJMOB mode: First, run optimization for each time interval separately
#             Next, run optimization over the entire time period with split at the QUARANTINE boundary
#                 This way, we aren't assuming knowledge of exogeneous changes in the underlying contact networks
if mode == "YJMOB":
    T = 15
    split_point = None

    # Pre-quarantine
    if file_index <= 1:
        adherence = 0.0
    # file_index 2 and 5: Simple adherence parameter cases, 
    #   not based on some previous adhering list
    elif file_index == 2 or file_index == 5:
        adherence = 1.0  # Proceed with partial adherence
    # Overwrite with static adhering list past this point,
    #  as they've been determined in file_index 2 run
    elif file_index >= 3:
        adherence = adhering

# Overwrite parameters if provided as command line arguments for sensitivity analysis
elif mode == "sensitivity analysis":
    print(sys.argv[1])
    seeds = ast.literal_eval(sys.argv[1])  # List of seed nodes
    init = float(sys.argv[2])  # Initial infected proportion
    split_point = None  # No split for sensitivity analysis. Only care about pre-quarantine

# Clear data files
def truncate_files():
    files_to_truncate = ["experiment_data/mfa_contact.gml", "experiment_data/mfa_social.gml", write_file]
    for file in files_to_truncate:
        if os.path.exists(file):
            with open(file, 'w') as f:
                f.truncate(0)

    # Clear data from mfa_seeds.npy if it exists
    if os.path.exists("experiment_data/mfa_seeds.npy"):
        os.remove("experiment_data/mfa_seeds.npy")

if clear:
    truncate_files()

try:
    if not os.path.exists("experiment_data/mfa_contact.gml") or not os.path.exists("experiment_data/mfa_social.gml"):
        raise FileNotFoundError

    # Rewrite graphs if mode is YJMOB
    if mode == "YJMOB":
        contact_idx = min(file_index, 4)
        contact_path = f"experiment_data/yjmob_{yjmob_size}_contact{contact_idx}.gml"
        social_path = f"experiment_data/yjmob_{yjmob_size}_social.gml"
        if not os.path.exists(contact_path):
            print(f"Error: YJMOB contact network file '{contact_path}' not found. Exiting.")
            sys.exit(1)
        if not os.path.exists(social_path):
            print(f"Error: YJMOB social network file '{social_path}' not found. Exiting.")
            sys.exit(1)
        contact_graph = nx.read_gml(contact_path)
        social_graph = nx.read_gml(social_path)
        n = contact_graph.number_of_nodes()

        # Find initial seed set only for the first post-quarantine interval
        if file_index == 2 or file_index == 5:
            seeds = find_seeds.find_seed_set(contact_graph, 10, 2)
            # Convert from numpy string array to list of integers
            seeds = [int(x) for x in seeds]

    else:
        # By default, use these
        contact_graph = nx.read_gml("experiment_data/mfa_contact.gml") 
        social_graph = nx.read_gml("experiment_data/mfa_social.gml")

        # Find seed set so we have less variability in the simulation
        seeds = find_seeds.find_seed_set(contact_graph, 10, 2) if seeds is None else seeds

        # Convert from numpy string array to list of integers
        seeds = [int(x) for x in seeds]

        # Write seeds to mfa_seeds.npy
        np.save("experiment_data/mfa_seeds.npy", np.array(seeds))

    # Convert node labels from strings to integers
    contact_graph = nx.relabel_nodes(contact_graph, lambda x: int(x))
    social_graph = nx.relabel_nodes(social_graph, lambda x: int(x))

except (FileNotFoundError, OSError, ValueError, nx.NetworkXError) as e:
    print("No valid graphs found in mfa_*.gml. Generating new graphs.")

    contact_graph = nx.erdos_renyi_graph(n, p, seed=42)
    social_graph = correlated_graphs.create_social_graph(contact_graph, nE=density_social)[0]

    # Read seed set from mfa_seeds.npy if it exists
    try:
        seeds = np.load("experiment_data/mfa_seeds.npy").tolist() if seeds is None else seeds
    except (FileNotFoundError, OSError, ValueError) as e:
        seeds = None

    # Convert node labels from strings to integers
    contact_graph = nx.relabel_nodes(contact_graph, lambda x: int(x))
    social_graph = nx.relabel_nodes(social_graph, lambda x: int(x))

    nx.write_gml(contact_graph, "experiment_data/mfa_contact.gml")
    nx.write_gml(social_graph, "experiment_data/mfa_social.gml")

SIR_results = SIR.Simulate_SIR(
    contact_network=deepcopy(contact_graph),
    social_network=deepcopy(social_graph),
    T=T, beta=beta, gamma=gamma, mu=mu, init=init,
    q=q, adherence=adherence, begin_q=split_point, 
    seeds=seeds, initial_state_dict=initial_states, q_mech=("ic", 0.02)
)

true_dynamics = SIR_results[4]
# Represents true degree over time, to be used in MFA optimization
deg_lst = SIR_results[6]
dynamic_deg = deepcopy(deg_lst) 
informed_and_infected = SIR_results[7]
informed = SIR_results[8]
adhering = SIR_results[9]

# Write to initial_state.pkl for next run (if applicable)
new_initial_state_dict = true_dynamics[-1]
new_informed = informed[-1]
# Write new initial states to pickle file for future use
with open("experiment_data/mfa_initial_state.pkl", "wb") as f:
    f.truncate(0)

    data_to_pickle = {
        "New Initial States": new_initial_state_dict,
        "New Informed": new_informed,
        "Adhering": adhering
    }
    pkl.dump(data_to_pickle, f)

# Write SIR results to pickle file for YJMOB full optimization later
if mode == "YJMOB" and file_index != 5:
    cur_dynamics = deepcopy(true_dynamics)
    cur_deg_lst = deepcopy(deg_lst)
    cur_informed_and_infected = deepcopy(informed_and_infected)
    cur_informed = deepcopy(informed)
    cur_adhering = deepcopy(adhering)

    with shelve.open("experiment_data/yjmob_dynamics_shelve") as db:
        db[f"Interval {file_index}"] = {
            "True Dynamics": cur_dynamics,
            "Dynamic Degree": cur_deg_lst,
            "Informed and Infected": cur_informed_and_infected,
            "Informed": cur_informed,
            "Adhering": cur_adhering
        }

# file_index == 5: Already completed all intervals individually, time to do full optimization
# Will involve overwriting some existing variables:
#     Necessary SIR data already obtained from the 5 intervals -> now combine
if mode == "YJMOB" and file_index == 5:
    split_point = 30
    T = 75

    # Extract true_dynamics, dynamic_deg from all intervals into single list
    # Overwrite whatever they were previously
    true_dynamics = []
    deg_lst = []
    informed_and_infected = []
    informed = []
    adhering = []

    with shelve.open("experiment_data/yjmob_dynamics_shelve") as db:
        # Iterate over the intervals you know exist
        for interval in range(5):
            interval_data = db.get(f"Interval {interval}")

            true_dynamics.extend(interval_data["True Dynamics"])
            deg_lst.extend(interval_data["Dynamic Degree"])
            informed_and_infected.extend(interval_data["Informed and Infected"])
            informed.extend(interval_data["Informed"])
            adhering.extend(interval_data["Adhering"])

    # Now, true_dynamics and deg_lst should have full 75 time steps from all YJMOB intervals

    # Update dynamic_deg for consistency
    dynamic_deg = deepcopy(deg_lst)

# Pre-compute per-timestep flow measurements once; optionally clobber with Gaussian noise.
# Doing this once ensures every call to given_at_time(t) sees the same noisy draw for a
# given t, keeping the optimizer loss and y_pred estimates consistent within each run.
_raw_new_r = []
_raw_new_i = []
for _t in range(T):
    if _t > 0:
        _r = sum(1 for node in contact_graph.nodes()
                 if true_dynamics[_t][node] == 2 and true_dynamics[_t - 1][node] != 2) / n
        _i = sum(1 for node in contact_graph.nodes()
                 if true_dynamics[_t][node] == 1 and true_dynamics[_t - 1][node] != 1) / n
    else:
        _r = sum(1 for node in contact_graph.nodes() if true_dynamics[0][node] == 2) / n
        _i = sum(1 for node in contact_graph.nodes() if true_dynamics[0][node] == 1) / n
    if noisy_data:
        if noise_type == "poisson":
            lam_r = max(_r * n / poisson_noise_scale, 0)
            lam_i = max(_i * n / poisson_noise_scale, 0)
            _r = poisson_noise_scale * np.random.poisson(lam_r) / n
            _i = poisson_noise_scale * np.random.poisson(lam_i) / n
        else:
            _r += np.random.normal(0, gaussian_noise_scale * np.sqrt(_r * (1 - _r) / n))
            _i += np.random.normal(0, gaussian_noise_scale * np.sqrt(_i * (1 - _i) / n))
    _raw_new_r.append(_r)
    _raw_new_i.append(_i)

def given_at_time(time):
    new_r_ratio = _raw_new_r[time]
    new_i_ratio = _raw_new_i[time]
    x1 = beta * (new_r_ratio / gamma)
    x2 = 1 - (new_r_ratio / gamma)
    return (x1, x2, new_i_ratio)

# New infections time-series step; use state dict
def y_true(time):
    # if time == 0:
    #     return sum(1 for node in contact_graph.nodes() if true_dynamics[0][node] == 1) / n
    # return sum(1 for node in contact_graph.nodes() if true_dynamics[time][node] == 1
    #            and true_dynamics[time - 1][node] != 1) / n
    x1, x2, _ = given_at_time(time)
    return (true_w[time][0] * x1) * (x2 - true_w[time][1])

# Use model to compute newly infected step
def y_model(time):
    x1, x2, _ = given_at_time(time)
    return (true_w[time][0] * x1) * (x2 - true_w[time][1])

def loss(params, w1_run_avg, prev_w2, T_gen, eps_w1, eps_w2):
    w1, w2 = params
    x1, x2, _ = given_at_time(T_gen)
    y_pred = (w1 * x1) * (x2 - w2)

    penalties = 0
    # Model constraints
    if w1 > binomial_bound or w1 < 0 or w2 > 1 or w2 < 0:
        penalties += 1000
        
    # Convergence constraints
    if w1_run_avg is not None:
        delta = abs(w1 - w1_run_avg)
        if delta > eps_w1:
            penalties += 100 * (delta - eps_w1)**2

    # Smoothness constraints
    if prev_w2 is not None:
        delta = abs(w2 - prev_w2)
        if delta > eps_w2:
            penalties += 100 * (delta - eps_w2)**2

    return ((y_pred - y_true(T_gen)) ** 2) + penalties

if split_point is not None:
    seg1 = deg_lst[:split_point]
    mean1 = np.mean(seg1)
    seg2 = deg_lst[split_point:]
    mean2 = np.mean(seg2)
    #  Split mean_degrees into two halves with their own respective means
    mean_degrees = [mean1] * len(seg1) + [mean2] * len(seg2)
else:
    mean_degrees = [np.mean(deg_lst) for _ in range(T)]   # Mean degree of contact network over time
binomial_bound = n * p + np.sqrt(n * p * (1 - p))

# Compute true w1 and w2 values: Mean degree and fraction of recovered nodes
true_w = []
for time in range(T):
    true_w1 = mean_degrees[time]
    true_w2 = sum(1 for node in contact_graph.nodes() if true_dynamics[time][node] == 2) / n  # Recovered portion
    true_w.append((true_w1, true_w2))

# eps_w1: Controls exploration of w1
# eps_w2: Controls smoothness of w2
def optimize_segment(start=0, end=T, bounds = [(1, binomial_bound), (0, 1)],eps_w1=binomial_bound, eps_w2=0.075, num_runs=25):

    #---------
    #
    #  Optimization problem: y = w1 * x1 * (x2 - w2), where w1, w2 are unknown (mean node degree and fraction of recovered nodes, respectively)
    #
    #----------

    w1_avg = []
    w2_avg = []
    y_pred_all_runs = []
    # Multiple runs to average out randomness
    for _ in range(num_runs):
        w1_estimates = []
        w1_run_avg = None
        temp = eps_w1
        w2_estimates = []
        y_pred_estimates = []
        prev_w2 = None

        # Optimize over the given time segment
        for t in range(start, end):
            T_gen = t
            init_guess = None
            eps_w1 = temp * ((1 - t/T)**0.5)  # Polynomial root decay of eps_w1 over time

            if w1_run_avg == None or prev_w2 == None:
                init_guess = [random.uniform(1, binomial_bound), true_w[T_gen][1]]
            else:
                #  Scipy will handle bounds issues here if they occur
                init_guess = [w1_run_avg + random.uniform(-eps_w1, eps_w1), prev_w2 + random.uniform(-eps_w2, eps_w2)]

            result = None
            result = minimize(lambda params: loss(params, w1_run_avg, prev_w2, T_gen, eps_w1=eps_w1, eps_w2=eps_w2), init_guess, method='L-BFGS-B', bounds=bounds)

            w1 = result.x[0]
            w1_estimates.append(w1)
            w1_run_avg = np.mean(w1_estimates)  # Update run average for w1
            w2 = result.x[1]
            w2_estimates.append(w2)

            # n_i calculated from estimated params (for identifiability test)
            x1_t, x2_t, _ = given_at_time(T_gen)
            y_pred_estimates.append((w1 * x1_t) * (x2_t - w2))

            # Verbose output
            if verbose:
                print("Time:", t)
                print("Initial guess:", init_guess)
                print("True w1:", true_w[T_gen][0])
                print("True w2:", true_w[T_gen][1])
                print("Estimated w1:", w1)
                print("Estimated w2:", result.x[1])
                print("x values at T_gen:", given_at_time(T_gen))
                print("Squared error:", result.fun)
                print("Mean node degree:", deg_lst[T_gen])
                print("\n")

            prev_w2 = w2 # Update prev_w2 for the next iteration

        w1_avg.append(w1_estimates)  # List of w1 estimates for this run
        w2_avg.append(w2_estimates)  # List of w2 estimates for this run
        y_pred_all_runs.append(y_pred_estimates)

        eps_w1 = temp  # Reset eps_w1 for the next run

    return w1_avg, w2_avg, y_pred_all_runs

# Split_point: None means no split, otherwise it is the time at which to split the optimization
def drive_optimizer(split_point=None):
    if split_point is None:
        w1_all_runs, w2_avg, y_pred_all_runs = optimize_segment()

        w1_run_avg = np.mean(w1_all_runs, axis=0)
        w2_run_avg = np.mean(w2_avg, axis=0)

        return w1_run_avg, w2_run_avg, w1_all_runs, y_pred_all_runs

    if split_point is not None:
        w1_all_runs1, w2_avg1, y_pred_runs1 = optimize_segment(start=0, end=split_point)
        w1_all_runs2, w2_avg2, y_pred_runs2 = optimize_segment(start=split_point, end=T)

        w1_avg1 = np.mean(w1_all_runs1, axis=0)
        w2_avg1 = np.mean(w2_avg1, axis=0)
        w1_avg2 = np.mean(w1_all_runs2, axis=0)
        w2_avg2 = np.mean(w2_avg2, axis=0)

        return w1_avg1, w2_avg1, w1_avg2, w2_avg2, w1_all_runs1, w1_all_runs2, y_pred_runs1, y_pred_runs2


#-------------
#
#  Identifiability analysis
#
#    Reduced model: y = w1 * x1 * x2, where w1 = <k> is the only unknown.
#        Treats r (recovered fraction) as known, so the (x2 - w2) term collapses.
#        x1 = beta * (n_r / gamma)
#        x2 = (1 - n_r / gamma - r)
#
#    Workflow:
#      1. Regress on <k> from known n_i, n_r (and known r).
#      2. Use estimated <k> + known n_r (+ known r) to predict n_i. Call this n_i_pred.
#      3. Use estimated <k> + known n_i (+ known r) to predict n_r. Call this n_r_pred.
#
#-------------

# Per-timestep components for the reduced (one-unknown) model.
#   x1_id = beta * (n_r / gamma)
#   x2_id = (1 - n_r / gamma - r)
#   y_id  = n_i
# All three are "known" in step 1.
def reduced_components_at(time):
    x1_id, _, y_id = given_at_time(time)  # x1_id = beta * (n_r/gamma); y_id = n_i
    n_r_ratio_over_gamma = _raw_new_r[time] / gamma
    r_known = true_w[time][1]
    x2_id = 1 - n_r_ratio_over_gamma - r_known
    return x1_id, x2_id, y_id

def loss_k_only(params, w1_run_avg, T_gen, eps_w1):
    w1 = params[0]
    x1_id, x2_id, y_id = reduced_components_at(T_gen)
    y_pred = w1 * x1_id * x2_id

    penalties = 0
    if w1 > binomial_bound or w1 < 0:
        penalties += 1000

    if w1_run_avg is not None:
        delta = abs(w1 - w1_run_avg)
        if delta > eps_w1:
            penalties += 100 * (delta - eps_w1) ** 2

    return ((y_pred - y_id) ** 2) + penalties

# Step 1: Regress on <k> alone, with known n_i, n_r, r.
def optimize_k_identifiability(start=0, end=T, bounds=[(0, None)],
                               eps_w1=None, num_runs=25):
    if bounds == [(0, None)]:
        bounds = [(0, binomial_bound)]
    if eps_w1 is None:
        eps_w1 = binomial_bound

    w1_all_runs = []
    for _ in range(num_runs):
        w1_estimates = []
        w1_run_avg = None
        temp = eps_w1

        for t in range(start, end):
            T_gen = t
            eps_w1 = temp * ((1 - t / T) ** 0.5)

            if w1_run_avg is None:
                init_guess = [random.uniform(1, binomial_bound)]
            else:
                init_guess = [w1_run_avg + random.uniform(-eps_w1, eps_w1)]

            result = minimize(
                lambda params: loss_k_only(params, w1_run_avg, T_gen, eps_w1=eps_w1),
                init_guess, method='L-BFGS-B', bounds=bounds
            )

            w1 = result.x[0]
            w1_estimates.append(w1)
            w1_run_avg = np.mean(w1_estimates)

            if verbose:
                print("[identifiability] Time:", t)
                print("[identifiability] True <k>:", true_w[T_gen][0])
                print("[identifiability] Estimated <k>:", w1)
                print("[identifiability] Squared error:", result.fun)
                print()

        w1_all_runs.append(w1_estimates)
        eps_w1 = temp

    return w1_all_runs

# Step 2: Predict n_i forward from estimated <k> and known n_r, r.
#   n_i_pred[t] = k_est[t] * x1_id[t] * x2_id[t]
def predict_n_i_from_k(k_est, start=0, end=T):
    n_i_pred = []
    for idx, t in enumerate(range(start, end)):
        x1_id, x2_id, _ = reduced_components_at(t)
        n_i_pred.append(k_est[idx] * x1_id * x2_id)
    return n_i_pred

# Step 3: Predict n_r given known n_i, r, and estimated <k>.
#   Solve for n_r in: n_i = beta * k_est * (1 - n_r/gamma - r) * (n_r/gamma)
#   Quadratic in n_r; solve numerically per timestep with a squared-residual minimize.
#   Bounds: n_r in [0, gamma] so that n_r/gamma in [0, 1].
def predict_n_r_from_k(k_est, start=0, end=T):
    n_r_pred = []
    for idx, t in enumerate(range(start, end)):
        _, _, n_i_known = given_at_time(t)
        r_known = true_w[t][1]
        k_t = k_est[idx]

        def residual(params):
            n_r_candidate = params[0]
            u = n_r_candidate / gamma
            y_pred = beta * k_t * (1 - u - r_known) * u
            return (y_pred - n_i_known) ** 2

        # Warm start from the known n_r so the optimizer has a good basin.
        warm_start = _raw_new_r[t]
        # Clip warm_start into bounds in case of noise.
        warm_start = min(max(warm_start, 0.0), gamma)

        result = minimize(residual, [warm_start], method='L-BFGS-B',
                          bounds=[(0.0, gamma)])
        n_r_pred.append(result.x[0])
    return n_r_pred

# Driver: returns averaged <k> estimates, n_i_pred, n_r_pred for a segment.
def run_identifiability(start=0, end=T, num_runs=25):
    k_all_runs = optimize_k_identifiability(start=start, end=end, num_runs=num_runs)
    k_avg = np.mean(k_all_runs, axis=0).tolist()
    n_i_pred = predict_n_i_from_k(k_avg, start=start, end=end)
    n_r_pred = predict_n_r_from_k(k_avg, start=start, end=end)
    return k_avg, n_i_pred, n_r_pred, k_all_runs

#-------------
#
#  Write data for plotting to file
#     Form: <label>:\n
#           x: <x_values>\n
#           y: <y_values>\n
#     where x_values and y_values are comma-separated lists of values
#
#-------------

# Save to write_file
# This is for single runs under a given SIR configuration
# Split: Tuple (split_point, half), where split_point is the time to split the optimization, and half is either 1 or 2
def save_xy_data(dynamic_deg=None, w1_avg=None, w2_avg=None, w1_all_runs=None, split=None, y_pred_all_runs=None,
                 k_id_avg=None, n_i_pred=None, n_r_pred=None):
    given_n_i = [given_at_time(t)[2] for t in range(len(true_dynamics))]
    given_n_r = [_raw_new_r[t] for t in range(len(true_dynamics))]

    # Compute y values
    w1_true_y = [true_w[t][0] for t in range(T)]
    w1_est_y = w1_avg
    w2_true_y = [true_w[t][1] for t in range(T)]
    w2_est_y = w2_avg
    sir_infections_y = [sum(1 for node in contact_graph.nodes() if true_dynamics[t][node] == 1) for t in range(len(true_dynamics))]

    # Newly recovered counts (raw counts, parallel to SIR Infections).
    newly_recovered_y = []
    for t in range(len(true_dynamics)):
        if t == 0:
            newly_recovered_y.append(sum(1 for node in contact_graph.nodes() if true_dynamics[0][node] == 2))
        else:
            newly_recovered_y.append(
                sum(1 for node in contact_graph.nodes()
                    if true_dynamics[t][node] == 2 and true_dynamics[t - 1][node] != 2)
            )

    # Bring informed_and_infected into local scope
    i_and_inf = deepcopy(informed_and_infected)
    i_and_inf = [len(i_and_inf[t]) for t in range(len(i_and_inf))]

    # Bring informed into local scope
    infm = deepcopy(informed)
    infm = [len(informed[t]) for t in range(len(informed))]

    # Round to 2 decimal places where appropriate
    w1_est_y = [round(y, 2) for y in w1_est_y]
    w2_est_y = [round(y, 2) for y in w2_est_y]

    # Identifiability outputs: round for consistency with other estimates.
    k_id_avg_y = [round(y, 2) for y in k_id_avg] if k_id_avg is not None else None
    n_i_pred_y = [round(y, 6) for y in n_i_pred] if n_i_pred is not None else None
    n_r_pred_y = [round(y, 6) for y in n_r_pred] if n_r_pred is not None else None

    x_ofs = 0

    # If there is a split point, adjust x_vals and y values accordingly
    if split is not None:
        sp, half = split
        if half == 1:
            x_ofs = 0  # Offset for generating x values for plotting
            sir_infections_y = sir_infections_y[:sp]
            newly_recovered_y = newly_recovered_y[:sp]
            dynamic_deg = dynamic_deg[:sp]
            w1_true_y = w1_true_y[:sp]
            w1_est_y = w1_est_y[:sp]
            w2_true_y = w2_true_y[:sp]
            w2_est_y = w2_est_y[:sp]
            i_and_inf = i_and_inf[:sp]
            given_n_i = given_n_i[:sp]
            given_n_r = given_n_r[:sp]
            infm = infm[:sp]
            # Save <k_0> runs
            w1_all_runs = [run for run in w1_all_runs if len(run) > 0]
            if y_pred_all_runs is not None:
                y_pred_all_runs = [run for run in y_pred_all_runs if len(run) > 0]
        if half == 2:
            x_ofs = sp  # Offset for generating x values for plotting
            sir_infections_y = sir_infections_y[sp:]
            newly_recovered_y = newly_recovered_y[sp:]
            dynamic_deg = dynamic_deg[sp:]
            w1_true_y = w1_true_y[sp:]
            w1_est_y = w1_est_y
            w2_true_y = w2_true_y[sp:]
            w2_est_y = w2_est_y
            i_and_inf = i_and_inf[sp:]
            given_n_i = given_n_i[sp:]
            given_n_r = given_n_r[sp:]
            infm = infm[sp:]
            # Save <k_q> runs
            w1_all_runs = [run for run in w1_all_runs if len(run) > 0]
            if y_pred_all_runs is not None:
                y_pred_all_runs = [run for run in y_pred_all_runs if len(run) > 0]

    y_model_vals = [round(y_model(t), 6) for t in range(x_ofs, x_ofs + len(w1_true_y))]

    with open(write_file, "a") as f:
        f.write("==New Sample==\n")

        f.write("Number of nodes: " + str(contact_graph.number_of_nodes()) + "\n\n")

        if isinstance(adherence, float):
            f.write("Adhering proportion: " + str(adherence) + "\n\n")
        # If only given adhering list, compute proportion
        else:
            # Round to nearest 0.01
            adhering_prop = round(len(adhering) / contact_graph.number_of_nodes(), 2)
            f.write("Adhering proportion: " + str(adhering_prop) + "\n\n")

        f.write("SIR Infections:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(sir_infections_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, sir_infections_y))}\n\n")

        f.write("Newly Recovered:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(newly_recovered_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, newly_recovered_y))}\n\n")

        f.write("Dynamic degree:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(dynamic_deg) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, dynamic_deg))}\n\n")

        f.write("w1 True (Mean Node Degree):\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(w1_true_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, w1_true_y))}\n\n")

        f.write("w1 Estimated:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(w1_est_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, w1_est_y))}\n\n")

        f.write("w1 all runs:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(w1_all_runs[0]) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, w1_all_runs))}\n\n")

        f.write("y_model values:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(y_model_vals) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, y_model_vals))}\n\n")

        if y_pred_all_runs is not None:
            f.write("y_pred all runs:\n")
            f.write(f"x: {','.join(map(str, range(x_ofs, len(y_pred_all_runs[0]) + x_ofs)))}\n")
            f.write(f"y: {','.join(map(str, y_pred_all_runs))}\n\n")

        f.write("w2 True (Recovered Fraction):\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(w2_true_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, w2_true_y))}\n\n")

        f.write("w2 Estimated:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(w2_est_y) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, w2_est_y))}\n\n")

        f.write("Informed and Infected:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(i_and_inf) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, i_and_inf[:len(i_and_inf)]))}\n\n")

        f.write("Informed:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs, len(infm) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, infm))}\n\n")

        # Note: n_i isn't defined for t=0 => we start x values from 1
        minimum_n_i_time = 0 if x_ofs != 0 else 1
        f.write("Given Newly Infected Ratio:\n")
        f.write(f"x: {','.join(map(str, range(x_ofs + minimum_n_i_time, len(given_n_i) + x_ofs)))}\n")
        f.write(f"y: {','.join(map(str, given_n_i[minimum_n_i_time:]))}\n\n")

        # Identifiability outputs.
        # k_id_avg / n_i_pred / n_r_pred are aligned to the current segment, so they share
        # the same x-axis offset and length as w1_true_y above.
        if k_id_avg_y is not None:
            f.write("k Identifiability Estimated:\n")
            f.write(f"x: {','.join(map(str, range(x_ofs, len(k_id_avg_y) + x_ofs)))}\n")
            f.write(f"y: {','.join(map(str, k_id_avg_y))}\n\n")

        if n_i_pred_y is not None:
            f.write("n_i Predicted (Identifiability):\n")
            f.write(f"x: {','.join(map(str, range(x_ofs, len(n_i_pred_y) + x_ofs)))}\n")
            f.write(f"y: {','.join(map(str, n_i_pred_y))}\n\n")

        if n_r_pred_y is not None:
            f.write("n_r Predicted (Identifiability):\n")
            f.write(f"x: {','.join(map(str, range(x_ofs, len(n_r_pred_y) + x_ofs)))}\n")
            f.write(f"y: {','.join(map(str, n_r_pred_y))}\n\n")


if split_point is None:
    w1_run_avg, w2_run_avg, w1_all_runs, y_pred_all_runs = drive_optimizer(split_point=None)
    # Identifiability analysis over the full window.
    k_id_avg, n_i_pred, n_r_pred, _k_id_all_runs = run_identifiability(start=0, end=T)
    save_xy_data(dynamic_deg=dynamic_deg, w1_avg=w1_run_avg, w2_avg=w2_run_avg,
                 w1_all_runs=w1_all_runs, y_pred_all_runs=y_pred_all_runs,
                 k_id_avg=k_id_avg, n_i_pred=n_i_pred, n_r_pred=n_r_pred)
else:
    w1_avg1, w2_avg1, w1_avg2, w2_avg2, w1_all_runs1, w1_all_runs2, y_pred_runs1, y_pred_runs2 = drive_optimizer(split_point=split_point)
    # Identifiability analysis per half so it aligns with the existing split outputs.
    k_id_avg1, n_i_pred1, n_r_pred1, _k_id_all_runs1 = run_identifiability(start=0, end=split_point)
    k_id_avg2, n_i_pred2, n_r_pred2, _k_id_all_runs2 = run_identifiability(start=split_point, end=T)

    save_xy_data(dynamic_deg=dynamic_deg, w1_avg=w1_avg1, w2_avg=w2_avg1,
                 w1_all_runs=w1_all_runs1, split=(split_point, 1), y_pred_all_runs=y_pred_runs1,
                 k_id_avg=k_id_avg1, n_i_pred=n_i_pred1, n_r_pred=n_r_pred1)
    save_xy_data(dynamic_deg=dynamic_deg, w1_avg=w1_avg2, w2_avg=w2_avg2,
                 w1_all_runs=w1_all_runs2, split=(split_point, 2), y_pred_all_runs=y_pred_runs2,
                 k_id_avg=k_id_avg2, n_i_pred=n_i_pred2, n_r_pred=n_r_pred2)

# Save daily infected and daily recovered counts to file
# Will be used in comparing ideal vs actual quarantine dynamics
def save_daily_infected_recovered():
    with open("experiment_data/infected_recovered.txt", "w") as f:
        f.write(f"Split point: {split_point}\n")
        f.write(f"Total nodes: {len(contact_graph.nodes())}\n")
        f.write("Day,Newly Infected,Newly Recovered\n")
        
        # Start from day 1 because day 0 has no "previous day" to compare against
        for day in range(1, T):
            newly_infected = sum(
                1
                for node in contact_graph.nodes()
                if true_dynamics[day][node] == 1 and true_dynamics[day - 1][node] != 1
            )
            newly_recovered = sum(
                1
                for node in contact_graph.nodes()
                if true_dynamics[day][node] == 2 and true_dynamics[day - 1][node] != 2
            )
            
            f.write(f"{day},{newly_infected},{newly_recovered}\n")

save_daily_infected_recovered()