This README covers purpose and functionality of main folder .py files.

Files are grouped by area: graph/network generation utilities, influence
maximization, the core SIRS epidemic simulator, real-world dataset network
construction, the Mean Field Approximation (MFA) pipeline, and the
adaptive/MILP quarantine-seed-selection ("capstone") pipeline.

Several files reference other modules that no longer exist in the repo
(informingcontact.py, lt_ic_loss_function.py, milp_local.py, etc. have been
removed) or call functions with signatures that have since changed. Where a
file is currently broken because of this, it is called out explicitly below
rather than glossed over.


=====================================================
Graph & network generation utilities
=====================================================

correlated_graphs.py:
Implements methods for generating directed/undirected graphs correlated with
a base graph, used throughout the repo to build synthetic "social" layers on
top of "contact" layers.

`create_correlated_digraph(base_graph, correlation_factor, base_probability=0.01)`
builds a directed graph over `range(len(base_graph.nodes()))` where each
possible directed edge (i, j) is added with probability
`base_probability * (1 + correlation_factor)` if the undirected pair is an
edge in `base_graph`, else `base_probability * (1 - correlation_factor)`
(capped at 1.0). It indexes nodes by `range(num_nodes)`, so it assumes the
base graph's nodes are already labeled 0..n-1.

`create_w_k_hop_correlation(base_graph, k)` computes, for every node pair,
the Jaccard similarity of their k-hop ego-network node sets
(`nx.ego_graph(..., radius=k)`) and adds a directed edge i->j with
probability equal to that similarity. Returns `(correlated_graph, (x_vals,
y_vals))` for plotting similarity vs. edge-presence.

`create_social_graph(H, nE=None)` is the function actually used elsewhere in
the repo (yjmob_network_creation.py, mfa_drive_compute.py,
adaptive_seed_selection.py, milp.py) as the default social-graph generator
from a contact graph: it builds radius-2 ego networks for every node,
computes pairwise Jaccard similarity, ranks pairs by similarity, and samples
`nE` edges (default `2 * H.number_of_edges()`) with probability proportional
to `1/rank`, randomly assigning a direction to each sampled pair. Returns
`(G, sim)`.

Pure graph-generation utilities with no file I/O. Depends only on networkx,
numpy, random.


parse.py:
`parse(filename)` reads a whitespace-delimited edge-list text file (`i j`
integers per line) and builds an undirected `networkx.Graph` via
`G.add_edge(i, j)` for each line. Returns the graph. Used by
extract_loss_calc.py to load experiment_data/facebook_network0.txt.


network_setup.py:
Shared network/beta-generation module whose purpose (stated in its own
docstring) is to give adaptive_seed_selection.py and milp.py an identical
contact/social network and identical per-node transmission-rate ("beta")
assignments, so the two seed-selection approaches are actually compared on
the same input rather than on independently regenerated random networks.

Module-level config: `n=200`, `p=0.05` (Erdos-Renyi contact graph), `SEED=42`,
`HETEROGENEOUS_BETA=True`, `beta_L=0.05`, `beta_R=0.25`, `Gamma=2` (shape
parameter skewing the beta distribution toward `beta_R`), `num_simulations=10`.

`laplacian_smooth_beta(G, beta_low, beta_high, lam, alpha, seed)` generates a
spatially-smooth per-node beta assignment: draws Gaussian noise per node,
smooths it via `(I + alpha*L)^-1` (L = graph Laplacian) so adjacent nodes get
similar values, then rank-transforms the result to a `u**lam`-shaped
distribution over `[beta_low, beta_high]`.

`generate_global_betas(graph, num_sims, start_index)` returns `num_sims` beta
maps (or scalars if `HETEROGENEOUS_BETA=False`), deterministic given
`SEED + start_index + i`. `build_shared_network(num_sims)` builds the ER
contact graph (isolated nodes removed, relabeled to consecutive integers), a
social graph via `correlated_graphs.create_social_graph`, and the beta maps.

`load_shared_network(path="shared_network.pkl", min_simulations=None)` is the
entry point other scripts call: loads the pickle cache if present and its
stored params match the current module config; extends the cached beta-map
list in place if more simulations are requested than are cached; rebuilds
from scratch if parameters changed or the cache is missing/invalid; and
re-pickles to `path` whenever anything changed. Running the file directly
forces a full rebuild and overwrite of shared_network.pkl.

Reads/writes only shared_network.pkl (pickle, repo-root-relative by default).


=====================================================
Influence maximization & seed selection
=====================================================

IM.py:
Implements Independent Cascade (IC) and Linear Threshold (LT) influence
models and greedy seed-selection heuristics.

`IC_prob_matrix(g, S, p, mc=1000, quarantining=None)` runs `mc` Monte Carlo
trials of a single-hop activation attempt from seed set S (not a full
cascade), averages to a per-node marginal activation probability, and draws
one stochastic "final" informed set from those marginals. `p` may be a
scalar or an n x n array of edge-specific probabilities. Returns
`(quarantine_matrix, A_final)`. This is the function SIR.py calls in
production runs.

`IC(g, S, p, mc=1000)` runs the standard full multi-round IC cascade,
averaged over `mc` trials; `greedy_for_ic(g, k, p, mc, S=None)` greedily adds
k seeds maximizing `IC`-estimated spread. `lt_prob_matrix(g, S, threshold=1,
quarantining=None)` runs a single-pass LT activation (a node activates once
its count of already-active predecessors reaches `threshold`);
`greedy_for_lt(g, seed_candidates, k=3, threshold=1)` greedily selects up to
k seeds from a candidate pool; `LT(g, threshold, initial_active=None)` runs a
full iterative LT cascade to convergence. `greedy_for_ic_target(g, p, mc,
target, S_init=None)` greedily grows a seed set until a target spread is
reached rather than a fixed k.

Note: the `quarantining` parameter accepted by `IC_prob_matrix` and
`lt_prob_matrix` is not actually used to exclude quarantined nodes from
activating — in `lt_prob_matrix` the intended check is commented out, and in
`IC_prob_matrix` the parameter isn't referenced in the body at all. Despite
SIR.py passing quarantine status in, it currently has no effect on the IC/LT
spread calculations.


find_seeds.py:
`find_seed_set(social_graph, num_seeds, exponent=1)` computes a per-node
selection probability proportional to `degree^exponent` (with a small floor
to avoid zero-probability nodes), samples `num_seeds` nodes without
replacement, tags each with node attribute `is_seed='Seed'`, and returns the
list. Raises ValueError if fewer nodes have nonzero probability than
requested.

`initialize_social_IM(social_network, k=None, p=0.3, num_seeds=1,
lt_threshold=None)` draws a seed set via `find_seed_set`, then dispatches to
`IM.greedy_for_ic` (if `lt_threshold is None`) or `IM.greedy_for_lt`.

Note: this file's call `IM.greedy_for_ic(social_network, k, seeds, p)` is
positionally mismatched against IM.py's current signature
`greedy_for_ic(g, k, p, mc, S=None)` — the `p` parameter receives the
`seeds` list and `mc` receives the float `p`. Calling
`initialize_social_IM(..., lt_threshold=None)` (the default, IC branch) will
currently raise a TypeError. The LT branch (passing an `lt_threshold`) is
argument-order-correct and works.


=====================================================
Core epidemic simulation
=====================================================

SIR.py:
Implements an SIRS epidemic model coupled to a separate social-network layer
used to spread awareness of quarantine measures. No file I/O of its own.

`sirs_step(G, state, L, beta, gamma, mu)` performs one synchronous SIRS
update: infected nodes (state 1) infect susceptible neighbors (state 0) with
probability `beta` (scalar, or per-node array/dict for heterogeneous
transmission) provided the neighbor's `L` flag allows it; infected nodes
recover to state 2 with probability `gamma`; recovered nodes lose immunity
back to state 0 with probability `mu`.

`quarantine_edge_removal(g, node, states, quarantine_statuses,
already_quarantining)` cuts all of a node's edges once it is both informed
and adhering, and marks it quarantining. `restore_edges(g_init, g, node,
already_quarantining)` restores a node's original edges (excluding edges to
neighbors still quarantining) once its quarantine ends.

`Simulate_SIR(contact_network, social_network, T, beta, gamma, mu, init,
q=False, q_mech=("ic", 0.02), adherence=None, begin_q=0, seeds=None,
initial_state_dict=None)` is the main entry point.
  - `q` controls the quarantine mechanism: False (none); True (fixed-length
    or Normal(14, 2)-sampled duration, with edges restored once the period
    ends — pass an int > 1 to fix the duration); or "r" (edges removed on
    infection, restored immediately on recovery, no fixed duration).
  - `q_mech` is a (type, value) tuple selecting the information-spread
    model that drives who becomes "informed" and thus eligible to
    quarantine: `("ic", p)` Independent Cascade via `IM.IC_prob_matrix`,
    `("lt", threshold)` Linear Threshold via `IM.lt_prob_matrix`, or
    `("FJ", kappa)` Friedkin-Johnsen belief dynamics — beliefs evolve as
    `(s_i + sum of neighbor beliefs) / (1 + deg_i)` with seeds pinned at 1,
    a node becomes informed (absorbing) each step with probability
    `x_i**kappa`, and — uniquely for FJ — edge removal is partial and
    per-edge (`P(cut) = 1 - exp(-(x_i + x_j))`) rather than all-or-nothing
    per node.
  - `adherence` is a fraction in [0,1] or an explicit set of adhering
    nodes; `seeds` seeds the information cascade (explicit set, an int
    delegating to `find_seeds.find_seed_set`, or None/0 for no spread);
    `begin_q` delays the start of spread/quarantine; `initial_state_dict`
    lets a caller supply an explicit S/I/R assignment instead of sampling
    from `init`.
  - Returns an 11-tuple: `(contact_network, state_changes, infection_data,
    quarantine_prob_matrix, state_series, social_network, dynamic_degree,
    informed_infected_series, informed_series, adhering, all_edges)`.

Depends on find_seeds.py, correlated_graphs.py, and IM.py.


SIR_examples.py:
Drives SIR.Simulate_SIR under different quarantine/adherence/seeding
configurations, aggregates over repeated trials, and produces
publication-styled matplotlib figures saved under result_figures/. Builds a
shared Erdos-Renyi contact network (n=200, p=0.05, seed=42) and a correlated
social network at import time.

Current top-level functions:
  - `informed_vs_noninformed(plot_data=False)` — q=True vs. q=False, 25
    trials; saves result_figures/informed_vs_noninformed.pdf.
  - `const_quarantines(plot_data=False)` — fixed 14-step quarantine
    (adherence=1.0) vs. none; saves result_figures/const_quarantines.pdf.
  - `normal_dist_quarantines(plot_data=False, num_trials=25)` — Normal(14,2)
    quarantine duration vs. none; saves
    result_figures/normal_dist_quarantines.pdf.
  - `jaccard_similarity(num_runs=20, bins=10, plot_data=False)` — reads
    experiment_data/Freeman3.gml, bins Jaccard similarity of correlated
    social graphs against empirical edge probability; saves
    result_figures/jaccard_similarity.pdf; returns (df, bin_means).
  - `random_vs_nonrandom_seeds(num_comparisons, plot_data=False)` — random
    vs. degree-weighted (find_seeds, exponent=20) seed selection across
    increasing seed-set sizes, q=100, adherence=1.0; saves
    result_figures/random_vs_nonrandom_seeds.pdf.
  - `compare_infections_adherence(adherence, plot_data=False)` — full vs.
    partial adherence under q="r". Currently broken: calls
    `SIR.Simulate_SIR(..., num_seeds=NUM_SEEDS, ...)`, but Simulate_SIR has
    no `num_seeds` parameter (the current parameter is `seeds`) — raises
    TypeError if invoked.
  - `r_quarantine(plot_data=False)` — quarantine-until-recovery (q="r") vs.
    none; saves result_figures/r_quarantine.pdf.
  - `permanent_quarantine(plot_data=False, num_trials=25)` — calls
    Simulate_SIR with `q=T`, where T is the module-level simulation length
    (100), not the literal boolean True; works because T > 1 is treated as
    a fixed quarantine duration equal to the whole run, but is fragile if T
    ever changes. Saves result_figures/permanent_quarantine.pdf.
  - `fj_quarantine(num_trials=25)` — Friedkin-Johnsen quarantine
    (q_mech=("FJ", 1.25), adherence=1.0); data-only helper (no plot of its
    own), consumed by plot_all_quarantine.
  - `plot_all_quarantine(num_trials=25)` — combines permanent_quarantine,
    normal_dist_quarantines, fj_quarantine, and the no-quarantine baseline
    into one comparison figure; saves
    result_figures/all_quarantine_strategies.pdf. This is the function
    actually invoked from __main__.
  - `rc()` — loads rc_contact_network_bin{1..19}.gml (relative path,
    inconsistent with the experiment_data/ or capstone_proj_data/ prefixes
    used elsewhere) and capstone_proj_data/rc_social_network.gml. Currently
    broken: calls `SIR.Simulate_SIR(..., lt_threshold=None, p=A_weighted)`,
    neither of which are parameters of the current Simulate_SIR — raises
    TypeError if invoked.
  - `plot_newly_infected()` — daily new-infection counts under q=False;
    saves result_figures/new_infections.pdf.
  - `plot_information_dynamics(plot_data=False)` — informed-node count over
    time with begin_q=30, q="r", adherence=1.0; saves
    result_figures/proportion_informed.pdf.
  - `run_simulations()` — orchestrates informed_vs_noninformed,
    const_quarantines, normal_dist_quarantines, r_quarantine,
    permanent_quarantine, random_vs_nonrandom_seeds(10),
    jaccard_similarity(20, 10); returns a 7-tuple.
  - `SIR_pickle_dump(filename='experiment_data/pickles.pkl')` — runs
    run_simulations() and pickles the results. Note: the saved dict labels
    `data[5]` (actually the random_vs_nonrandom_seeds result) as "Jaccard
    Similarity" — the real Jaccard result (data[6]) is never stored.
  - `pickle_load(filename='experiment_data/pickles.pkl')` — loads and
    prints that pickle file.

`__main__` currently only calls `plot_all_quarantine(num_trials=5)`; other
invocations, including calls to functions named `FJ()` and `compare_FJ_IC()`
that no longer exist in this file, are commented out as stale scaffolding.


=====================================================
Real-world dataset network construction
=====================================================

yjmob_network_creation.py:
Builds per-time-interval contact networks and one directed social network
from a sampled YJMob100k-style movement CSV, with optional Cytoscape export.

Reads experiment_data/yjmob_1000_sample.csv (user_id, day, time, x, y).
`SAMPLE_SIZES = (100, 250, 500, 1000)` with `SAMPLE_SIZE_IDX` (hardcoded)
selecting how many distinct users (seeded with `random.seed(42)`) to keep.
Records are bucketed into 15-minute intervals. Within each interval, two
users "collide" (an edge) if their coordinates match exactly at the same
timestep or across a 1-step window; one undirected contact_network is built
per interval from collision pairs (edges are unweighted — collision counts
are tallied but not used to threshold or weight edges).

The social network is built once, from the first interval's contact network,
via `correlated_graphs.create_social_graph`, and reused for every interval
(this differs from an earlier percentile-based collision-count filtering
approach). All contact networks and the social network are unioned onto a
consistent node set and relabeled to consecutive integers. Writes
experiment_data/yjmob_{sample_size}_contact{interval}.gml and
experiment_data/yjmob_{sample_size}_social.gml (the latter rewritten
identically each interval). If `ping_cytoscape` (hardcoded True) is set, also
pushes each interval to a running Cytoscape instance via py4cytoscape.

No `__main__` guard — the entire script runs at import time.


high_school_network_creation.py:
One-shot script building a high-school social network and 19 time-binned
contact networks from interaction-survey data, with optional Cytoscape push.

Reads capstone_proj_data/high_school_social.csv (space-delimited, columns
u/v) into an undirected social graph, and capstone_proj_data/HS_data.csv
(space-delimited, columns t/u/v — a preprocessed version of the raw
High-School_data_2013.csv dataset) into 19 equal-width time bins via
`pd.cut`, building one contact graph per bin (isolated nodes removed). Every
node gets a `name` attribute set to its stringified id (needed for GML
round-tripping / Cytoscape display).

Writes capstone_proj_data/high_school_social.gml and capstone_proj_data/
high_school_contact_bin{1..19}.gml — these exact filenames are read back by
drive_seed_selection.py. If `ping_cytoscape` (hardcoded True) is set, also
pushes the networks to a running Cytoscape instance; there is no try/except
around the py4cytoscape calls, so this will fail/hang without Cytoscape
running.


rc_creation_simple.py:
One-shot script (no functions, executes top to bottom) building a "simple"
residential-college-style social and contact network from two raw CSVs.
Node universe is hardcoded as `ALL_NODES = set(range(1, 85))` (84 people).

Social network: reads capstone_proj_data/RelationshipsFromSurveys.csv, and
for each undirected pair builds one edge with one attribute per survey date
(`s_YYYYMMDD`), valued as the comma-joined set of relationship types reported
that date. No edge weights or time-binning (contrast with
mit_rc_network_creation.py below, hence "simple").

Contact network: reads capstone_proj_data/Proximity.csv, canonicalizes each
proximity ping into an undirected pair, and sets a boolean edge attribute per
unique raw timestamp (`c_YYYYMMDD_HHMMSS`) on that pair's single edge.

Writes capstone_proj_data/rc_social_simple.gml and
capstone_proj_data/rc_contact_simple.gml, and prints diagnostic summaries to
stdout. No other script in the repo currently reads these two output files.


mit_rc_network_creation.py:
One-shot script (no functions, no __main__ guard) that builds the "rc_*" GML
files used throughout the rest of the repo, from the MIT Reality Commons
"Social Evolution" dataset ("RC" = Reality Commons, a dorm-based
mobile-sensing study — not "residential college").

Social network: reads capstone_proj_data/RelationshipsFromSurveys.csv.
Relationship types are mapped to hardcoded weights (CloseFriend: 0.09,
SocializeTwicePerWeek: 0.07, PoliticalDiscussant: 0.05,
FacebookAllTaggedPhotos: 0.03, BlogLivejournalTwitter: 0.01 — no cited
derivation). Builds a directed graph with edges deliberately reversed
(nominee -> nominator); when a pair reports multiple relationship types, the
edge keeps the maximum weight (not the sum), on the reasoning that a
"CloseFriend" relationship is already explicit and strong. Node set is forced
to exactly {1..84}. Writes capstone_proj_data/rc_social_network.gml.

Contact networks: reads capstone_proj_data/Proximity.csv, bins timestamps
into 30-day windows (the origin of the "bin1..bin19" naming used across the
repo). For each proximity record, treats its reported `prob2` value as a
Bernoulli success probability and stochastically samples (unseeded — not
reproducible run to run) whether the contact "really" occurred. Produces:
  - capstone_proj_data/rc_contact_network_bin{1..N}.gml — one unweighted
    graph per bin, all 84 nodes present (including isolates).
  - capstone_proj_data/rc_contact_unified_all_bins.gml — one graph with a
    boolean `contact_bin_{i}` attribute per edge per bin plus a
    `total_realized_contacts` sum.
  - capstone_proj_data/rc_weighted_contact_bin{1..N}.gml — ground-truth
    edges are those realized in bin i, but each edge's weight is the
    fraction of the *other* bins (leave-one-out) that also contain that
    edge. This is the specific file family read by milp.py,
    drive_seed_selection.py, and dual_optimization_driver.py.

Note: the Bernoulli realization step is not seeded, so re-running this script
regenerates different rc_contact_network_bin*.gml / rc_weighted_contact_bin*
.gml files each time, even though every downstream script treats them as
fixed inputs. Also pushes all networks to Cytoscape via py4cytoscape
(requires a running local instance).


=====================================================
Mean Field Approximation (MFA) pipeline
=====================================================

mean_field_approx.py:
Core MFA simulation/optimization engine: simulates an SIRS model on a
contact network and fits a reduced mean-field model to the resulting
infection/recovery dynamics, writing results in the text format that
result_figures/extract_mfa.py parses. Mode is selected via the last CLI
argument (`sys.argv[-1]`); other positional args vary per mode (no argparse —
fragile to a wrong argument count).

  - Standard mode (no mode string): hardcoded defaults (n=200 ER contact
    graph p=0.05, T=100, beta=0.15, gamma=0.07, mu=0.05, init=0.1,
    adherence=0.6, split_point=30). Loads experiment_data/mfa_contact.gml /
    mfa_social.gml, generating them via `nx.erdos_renyi_graph` +
    `correlated_graphs.create_social_graph` if missing; picks 10 seeds via
    `find_seeds.find_seed_set` (exponent=2); writes to
    experiment_data/mfa_xy_data.txt.
  - "adherence mode": argv = [write_file, adherence] — used to sweep
    adherence levels.
  - "yjmob mode": argv = [file_index, yjmob_size]. Loads
    experiment_data/yjmob_{yjmob_size}_contact{idx}.gml /
    ..._social.gml, T=15, no split point. Intervals 0-4 are simulated
    individually, each continuing epidemic state from the previous interval
    via experiment_data/mfa_initial_state.pkl, and their per-interval
    dynamics are cached in a shelve database
    (experiment_data/yjmob_dynamics_shelve, key "Interval {i}"). Intervals
    0-1 use adherence=0 (pre-quarantine); interval 2 uses adherence=0.6 and
    fixes the adhering node set, which intervals >=3 reuse. file_index==5
    reads all 5 cached intervals back out of the shelve, concatenates them
    into one 75-step combined series, sets split_point=30, and reruns the
    full pre/post-quarantine optimization over the combined series — this
    is what produces the "full-period" yjmob5_runs.txt fit used by
    result_figures/analyze_yjmob_quarantine.py. Output:
    experiment_data/yjmob{file_index}_runs.txt.
  - "sensitivity analysis mode": argv = [seeds_literal, init, write_file]
    (seeds parsed via ast.literal_eval); pre-quarantine only, no split.

Optional noise injection (module-level `noisy_data`, `noise_type`
"gaussian"/"poisson", `gaussian_noise_scale`, `poisson_noise_scale`) perturbs
the per-timestep newly-infected/newly-recovered ratios once, before any
optimization, so the same noisy series is used throughout a run.

Math: the standard model fits `n_i(t) = w1 * x1(t) * (x2(t) - w2)`, where
`x1 = beta * (n_r/gamma)`, `x2 = 1 - n_r/gamma`, `w1` is mean node degree
<k>, and `w2` is recovered fraction r. `optimize_segment` runs 25 independent
L-BFGS-B optimizations per segment, stepping through time with a
warm-started running average and previous-step value used as soft-penalty
anchors (the allowed drift `eps_w1` decays as `(1 - t/T)**0.5` to tighten
convergence over time); w1 is capped at a binomial upper bound
`n*p + sqrt(n*p*(1-p))`. When a split point is set, the pre- and
post-quarantine halves are each fit independently (this produces the "w1
True/Estimated" pre- vs. post- pairs consumed downstream). A separate,
always-on identifiability pass (`run_identifiability`) fits a reduced
one-parameter model where the recovered fraction is treated as known rather
than fit, then (1) regresses <k> alone from known n_i/n_r/r
(`optimize_k_identifiability`), (2) forward-predicts n_i from that <k>
(`predict_n_i_from_k`), and (3) numerically inverts the relation per-timestep
to back out n_r from the estimated <k> and known n_i/r
(`predict_n_r_from_k`) — testing whether <k> alone is enough to recover both
infection and recovery flows.

Output format (`save_xy_data`): appends one "==New Sample==" block per call
to the target file, each with "Number of nodes", "Adhering proportion", then
labeled x/y sections — SIR Infections, Newly Recovered, Dynamic degree, w1
True (Mean Node Degree), w1 Estimated, w1 all runs (all 25 raw run
trajectories), y_model values, y_pred all runs, w2 True (Recovered
Fraction), w2 Estimated, Informed and Infected, Informed, Given Newly
Infected Ratio, k Identifiability Estimated, n_i Predicted
(Identifiability), n_r Predicted (Identifiability). Separately,
`save_daily_infected_recovered()` (called unconditionally at the end of
every run) writes experiment_data/infected_recovered.txt as a
Day/Newly Infected/Newly Recovered table.

Depends on find_seeds.py and correlated_graphs.py.


mfa_drive_compute.py:
Driver that repeatedly shells out to `mean_field_approx.py` (via
`subprocess.run`) with different arguments to sweep parameters, 10 repeats
per configuration.

  - `adherence_mode()` — clears experiment_data/a_0.2, a_0.4, a_0.6, then
    runs mean_field_approx.py in "adherence mode" for adherence levels 0.2,
    0.4, 0.6 (3 levels, not the 6 an earlier version swept).
  - `simple_repeat()` — runs mean_field_approx.py with no extra arguments,
    repeated.
  - `yjmob_mode(size)` — size must be one of {100, 250, 500, 1000}. Clears
    experiment_data/yjmob{0..5}_runs.txt, then for each repeat and each of
    the 6 yjmob file indices, runs mean_field_approx.py in "yjmob mode".
  - `sensitivity_analysis()` — builds a default ER contact network (n=200,
    p=0.05) and social network, writing experiment_data/mfa_contact.gml /
    mfa_social.gml for mean_field_approx.py to read; sweeps (a) number of
    seeds (grown in batches of 5 up to 15 via find_seeds.find_seed_set,
    exponent=2) into experiment_data/sensitivity_num_seeds.txt, (b) initial
    infected proportion [0.025, 0.05, 0.10] into sensitivity_init.txt, and
    (c) network density [0.03, 0.04, 0.05] (regenerating the contact graph
    each time) into sensitivity_density.txt.

`__main__` builds an argparse parser with a `--yjmob-size` option, but the
parsed value is currently unused — the code calls `yjmob_mode(size=250)`
hardcoded regardless of the flag. `adherence_mode()`, `sensitivity_analysis()`,
and `simple_repeat()` are present in the file but commented out, so as
currently checked in, running this script only executes `yjmob_mode(size=250)`.


extract_loss_calc.py:
Loads the Facebook ego-network dataset (experiment_data/facebook_network0.txt,
via parse.py), computes/stores Independent Cascade and Linear Threshold loss
matrices across several correlated networks, and provides a re-parser.
`write_matrices_to_file` / `parse_matrices` serialize and reload
experiment_data/loss_matrices.txt with per-line column-count validation.
`simplify_matrices` reduces every matrix to only its final row.

Note: this file is currently non-runnable — its first import,
`import lt_ic_loss_function as lc`, refers to a module that no longer exists
anywhere in the repo. Any use of this script requires either restoring that
module or reworking the loss-matrix computation it depends on.


=====================================================
Adaptive & MILP quarantine-seed-selection ("capstone") pipeline
=====================================================

This group of files compares strategies for choosing which nodes to
quarantine over time on a real or synthetic contact network, under a shared
per-timestep cost model that trades off epidemic spread against the cost of
edges removed by quarantine.

adaptive_seed_selection.py:
Runs an SIRS-with-quarantine simulation (SIR.Simulate_SIR) and compares
three strategies for re-selecting which nodes to quarantine every
`batch_interval` (2) of `T` (100) steps: an adaptive stochastic hill-climber
(`hill2`), a degree-based heuristic (`degree_based_selection`), and a random
baseline (`random_seed_selection`), plus a no-quarantine reference
(`no_quarantine_baseline_runs`). All three selection strategies choose
`K = int(3/4 * n)` nodes per round — i.e. quarantining roughly 75% of the
population at a time, not a small classic-influence-maximization seed set.

`initialize(network=None, social=None)` must be called first. With both
args None it loads the network shared with milp.py via
`network_setup.load_shared_network`; given a GML path (optionally with a
real social-network GML too) it loads and relabels those onto one shared
integer id space instead.

`global_cost_function(newly_infected, live_edges, seed_set_size, t_cur)`
scores a batch window as the sum of two capped, normalized terms: newly
infected count (normalized against the worst-case no-quarantine baseline)
and cumulative edge-removal cost (normalized against a static worst-case
bound — every edge lost every step — rather than a full-quarantine
simulated counterfactual, because aggressive quarantine can suppress spread
so effectively that it produces *less* cumulative edge loss than a realistic
policy, which would make that counterfactual an unsound bound).

`hill2()` initializes a random K-node seed set and per-node scalar
"utilities" ~ U(0,1); at each batch boundary it updates every node's utility
with an EWMA of the cost delta, then attempts exactly one add/drop swap per
batch (softmax-weighted by utility) and accepts it if the resulting cost is
no worse than the previous batch's. Across 10 simulation runs it keeps the
most common resulting seed set, and records the full per-run per-batch seed
history (`all_batch_seed_sets`) — this is what visualize_adaptive.py
consumes. Returns a 12-tuple: (most_common_seed_set, all_cost_curves,
all_infection_term_curves, all_edge_term_curves, all_edge_curves,
all_newly_infected_counts, all_newly_infected_frac, all_state_vectors,
tagged, all_batch_seed_sets, all_alpha_w_curves, all_beta_w_curves).
`degree_based_selection()` and `random_seed_selection()` return an analogous
11-tuple (no `all_batch_seed_sets`, plus `all_full_dynamics` in its place).

`__main__` runs all three methods against the synthetic shared network,
pickles hill2's per-batch seed sets and the social network to
adaptive_seed_data.pkl (read by visualize_adaptive.py), and pushes each
method's cost/infection/edge curves into cost_curve_store.py under labels
"Degree-Based", "Random Seeds", "Adaptive" for later joint comparison plots.

Depends on SIR.py, correlated_graphs.py, cost_curve_store.py,
network_setup.py.


visualize_adaptive.py:
Post-processing/visualization only (no simulation) for hill2's results,
examining which nodes get selected as quarantine seeds relative to their
network centrality (degree, k-core coreness, betweenness — computed on the
undirected social network).

Reads adaptive_seed_data.pkl (produced by adaptive_seed_selection.py's
__main__) for a single-network run, or adaptive_real_world.pkl (produced by
dual_optimization_driver.py sweeping the rc_weighted_contact_bin{i}.gml
files) for a multi-bin sweep.

`plot_selected_seed_counts_by_metric_bin` bins nodes by each raw metric
value and counts how many selected seeds fall in each bin, as a 3-panel bar
chart with a KDE density overlay of the network-wide distribution; writes
capstone_result_figures/adaptive_selected_seed_counts_by_metric_bin.pdf.
`plot_selected_seed_counts_for_real_world_bins` repeats this per real-world
bin, writing capstone_result_figures/
adaptive_selected_seed_counts_real_world_bin{i}.pdf per bin.
`plot_selected_seed_metric_heatmaps` condenses all real-world bins into one
figure: 3 heatmaps (degree/coreness/betweenness) with network bin index on
the x-axis, metric-value bin on the y-axis, and column-normalized selection
fraction as color; writes
capstone_result_figures/adaptive_selected_seed_metric_heatmaps.pdf.

The `__main__` mode (single-network vs. real-world sweep) is chosen by a
hardcoded `SELECTED_MODE` constant, not a CLI flag.

Note: "selected" here is a boolean (selected at least once across all
runs/batches) — the underlying per-node selection *frequency* is computed
but discarded, so these plots show which nodes were ever picked, not how
often.


milp.py:
An alternative to adaptive_seed_selection.py's heuristic hill-climb:
formulates quarantine-seed and edge-removal selection jointly as a
Mixed-Integer Linear Program, re-solved every `batch_interval` (5) steps via
`scipy.optimize.milp`. Because the true SIR dynamics are nonlinear and can't
be expressed inside a MILP, exposure is approximated by a linearized
auxiliary binary `z_e = y_e * (1 - x_u) * (1 - x_v)` ("edge e is live and
neither endpoint is quarantined"), encoded with the standard 4-constraint AND
linearization per edge; the sum of z_e over a batch window stands in for
actual epidemic exposure in the objective.

`initialize(network=None, social=None)` mirrors adaptive_seed_selection.py's
version (same shared-network loading via network_setup, same real-GML
loading/relabeling path) and additionally runs `num_simulations`
no-quarantine baseline trajectories via `baseline_infections` up front, used
only as a normalization bound for the cost function.

`global_cost_function(newly_infected, live_edges, t_cur)` uses the same
two-term capped/normalized cost as adaptive_seed_selection.py (infection
term bounded by the worst-case no-quarantine baseline, edge term bounded by
a static worst-case bound for the same reason described there).

`milp_seed_selection_stepwise()` builds the MILP constraint matrix once
(`sum(x) <= K` where `K = int(3/4 * n)`, matching adaptive_seed_selection.py's
budget, plus 4 linearization rows per edge), then for each simulation run
re-solves the MILP at every batch boundary with an objective that rewards
keeping edges live (weighted by the edge-cost normalization) and penalizes
the exposure proxy z_e (weighted by the infection-cost normalization);
selected nodes/edges are held fixed until the next batch, and
SIR.Simulate_SIR is called per batch with those seeds and `q="r"`. Returns a
10-tuple: (winner_sets, all_cost_curves, all_infection_term_curves,
all_edge_term_curves, all_edge_curves, all_newly_infected_counts,
all_newly_infected_frac, all_full_dynamics, all_alpha_w_curves,
all_beta_w_curves).

`__main__` runs against the synthetic shared network and pushes results into
cost_curve_store.py under the "MILP" label — milp.py does not write any
figure directly itself. Depends on correlated_graphs.py, network_setup.py,
SIR.py, cost_curve_store.py.


dual_optimization_driver.py:
Orchestrates both adaptive_seed_selection.py's `hill2()` and milp.py's
`milp_seed_selection_stepwise()` (as library calls, not subprocesses) against
the real-world rc_weighted_contact_bin{i}.gml family, for a configurable list
of bins (`--bins`, default 12-19) and method selection (`--methods
{adaptive,milp,both}`, default both).

Note: a module-level `RUN_MILP = False` kill-switch currently disables the
MILP path regardless of `--methods`, and also skips writing the combined
real_world_methods.pkl output entirely — only adaptive_real_world.pkl (the
file visualize_adaptive.py's real-world mode reads) gets written by default,
despite the docstring describing a combined-output default.

Writes real_world_methods.pkl (only if RUN_MILP is True) and
adaptive_real_world.pkl (whenever adaptive results exist), both to the
current working directory. Produces no plots itself.


cost_curve_store.py:
Shared storage + comparison-plotting module that decouples
adaptive_seed_selection.py, milp.py (and a since-removed milp_local.py
variant, per METHOD_STYLE's remaining "MILP-Local" entry) from each other:
each script independently computes its own cost curves and calls
`push_curve(label, cost_curves, infection_curves=None, edge_curves=None,
alpha_curves=None, beta_curves=None, batch_interval=1, T=None,
path="cost_curves_data.pkl")` to merge its results into one shared pickle,
so the scripts can be run separately, in any order/subset, and compared
later in one figure.

`_expand_to_ticks` repeats each method's once-per-batch cost value across
the ticks its batch covers, so methods using different `batch_interval`
values still align on one shared per-tick x-axis when compared.
`plot_joint_cost_comparison()` plots mean +/- std cost over time for every
method present in the store, writing
capstone_result_figures/joint_cost_comparison.pdf. `plot_joint_cost_elements()`
decomposes each method's total cost into its two capped, normalized
components (infection term, edge term) for methods that have both
populated, writing
capstone_result_figures/joint_cost_elements_comparison.pdf.

`__main__` just calls both plotting functions against whatever is currently
in cost_curves_data.pkl — meant to be run manually after one or more of
milp.py / adaptive_seed_selection.py have already populated the store.


drive_seed_selection.py:
A standalone comparison/visualization driver for adaptive_seed_selection.py
only (does not call milp.py or cost_curve_store.py). For each bin in a
configurable range, runs hill2, degree_based_selection, and
random_seed_selection against either the "rc" or "high_school" dataset
(`DATASET` enum, hardcoded), and renders a combined figure: a network-topology
panel (Kamada-Kawai layout, node color/size by degree) plus a triple-axis
comparison panel (edge-fraction, newly-infected-fraction, and cost curves
with std bands). Saves capstone_result_figures/dual_bin{bin_idx}.pdf per bin.

Note: this script is currently broken. It unpacks each
adaptive_seed_selection.py call into only 6 variables (e.g.
`_, hill_cc, hill_ec, hill_nc, hill_nf, hill_dyn = asm.hill2()`), but
hill2()/degree_based_selection()/random_seed_selection() currently return
12-, 11-, and 11-tuples respectively — this unpacking raises
`ValueError: too many values to unpack` on the very first call in the loop.
The existing dual_bin10.pdf-dual_bin19.pdf files in capstone_result_figures/
appear to be outputs from an earlier version of adaptive_seed_selection.py
with shorter return signatures. Also note: unlike milp.py and
dual_optimization_driver.py, this script's `initialize()` call only passes a
contact-network path (no real social-network GML), so it always synthesizes
its social network via correlated_graphs.create_social_graph rather than
using the real rc_social_network.gml.
