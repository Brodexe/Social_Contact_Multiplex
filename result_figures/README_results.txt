This README covers usage and functionality of result-figure-generating .py
files in this folder. All of these scripts parse text/pickle output produced
by mean_field_approx.py (via extract_mfa.py) or by the analyze_* scripts in
this same folder, and save PDF figures (plus, for most, a companion .pkl of
the processed data) for downstream reporting.


extract_mfa.py:
Parses the text files written by mean_field_approx.py's `save_xy_data` into
a list of samples, each a dict of named datasets. `parse_sample_data(filename)`
splits the file on "==New Sample==" markers; within each sample it reads
"Number of nodes" and "Adhering proportion" scalars, and any of the following
dataset blocks (each a `x:`/`y:` pair of lines): SIR Infections, Dynamic
degree, w1 True (Mean Node Degree), w1 Estimated, w1 all runs, w2 True, w2
Estimated, Informed and Infected, Given Newly Infected Ratio, Informed,
y_true values, y_model values, y_pred all runs, Newly Recovered, k
Identifiability Estimated, n_i Predicted (Identifiability), n_r Predicted
(Identifiability). `w1 all runs`/`y_pred all runs` y-lines (nested lists,
possibly containing `np.float64(...)` wrapper text) and `Informed` y-lines
(nested lists) get special parsing via `ast.literal_eval` after stripping the
numpy wrapper; everything else parses as a flat float list, or as a nested
list if the line starts with `[`. Parsing failures are logged and degrade to
an empty list rather than aborting the whole file. Used by every other
script in this folder.


analyze_yjmob_quarantine.py:
Estimates quarantine adherence on the YJMob100k dataset from MFA-estimated
degree dynamics and the informed-and-infected fraction, and produces the two
headline YJMob figures.

Loads five consecutive interval samples (yjmob0_runs.txt through
yjmob4_runs.txt via extract_mfa) plus a sixth, yjmob5_runs.txt, which holds
the full-period (pre+post-quarantine combined) optimization produced by
mean_field_approx.py's yjmob-mode file_index==5 path. Samples 2-4 are treated
as post-quarantine; their "Informed and Infected" (normalized by population)
and "Dynamic degree" series are concatenated across samples, run-by-run, into
one continuous per-run time series (`inf_inf_runs`, `k_q_runs`), and their
mean/std across runs are computed.

`plot_mfa_estimated_degree()` builds YJMOB_k_est.pdf: it plots the true
piecewise mean degree and the MFA-estimated mean degree (with +/-1 std band)
for each of the 5 individual intervals, laid out on one shared time axis by
accumulating each interval's duration (pre-quarantine intervals in orange,
post-quarantine in red), then overlays the yjmob5_runs.txt full-period fit
(pre in green, post in purple) for comparison against the interval-by-interval
approach.

Adherence estimation: `k_0` is the average of the last pre-quarantine mean
degree from the first two interval samples. For each run, a cumulative
optimization (`mse_slice`, L-BFGS-B) fits scale factor S and adherence
jointly against `k_q_est = k_0 * (1 - S * adherence * i_prime)` using only
the data available up to time t, for every t from 1 to 45 days
post-quarantine — this produces a time-resolved adherence estimate per run,
averaged across runs into `adh_mean`/`adh_std`. `plot_mfa_estimated_degree()`
runs first and is followed by the cumulative-adherence plot
(YJMOB_adherence.pdf), which shows the estimated adherence curve with a
+/-1 std band against a horizontal line for the true adhering proportion
(pulled from the dataset's "Adhering proportion" field).

Saves result_figures/cumulative_adherence_results.pkl with k_0, split_point,
adhering_proportion, population, num_simulations, and time_after_q; the full
time-series fields (i_prime_mean, k_q_true_mean/runs, cumulative_adh_*,
t_vals) are present in the code as commented-out dict entries and are not
currently written to the pickle.


analyze_quarantine_dynamics.py:
Runs the same style of two-stage adherence/scale-factor fit as
analyze_yjmob_quarantine.py, but on synthetic data across three true
adherence levels (experiment_data/a_0.2, a_0.4, a_0.6) instead of the YJMob
dataset, and adds a degeneracy-aware two-stage estimator plus a
runs-truncation step to keep only the well-behaved part of each trajectory.

Every sample is first truncated to its first 70 timesteps ("for faster
testing", per an in-file comment). For each adherence level, `k_0`/`k_q` come
from the pre-/post-quarantine samples' true mean degree, and
"Informed and Infected"/"Dynamic degree" series across all post-quarantine
(odd-indexed) samples become per-run i_prime/k_q series, same as in
analyze_yjmob_quarantine.py.

`two_stage_estimate(i_prime_series, k_q_series, k_0)` addresses the fact
that jointly fitting scale factor f and adherence a is not identifiable
(only their product f*a enters the k_q model): stage 1 fits adherence alone
on days where informed-and-infected is low (a fixed f=2.0 plugged in as a
proxy for "low infection overall"); stage 2 then fits f alone, with
adherence fixed at its stage-1 value, on the remaining days. This is used
for the per-level "true vs. estimated <k_q>" comparison figures
(kq_true_vs_estimated_a{level}.pdf) and the cumulative-adherence-over-time
comparison (adherence_comparison.pdf).

`estimate_a_then_f(i_prime_run, k_q_run, k_0, anchor_idx=1)` is a different,
non-iterative estimator used only for the summary bar chart: near the very
start of quarantining, f is known exactly (=2, an initial-condition
property), so anchoring there lets p = f*a be solved as a single variable
and divided by the known f to recover adherence directly, without needing
the low-infection-day heuristic. `truncate_at_new_infection_cutoff` keeps
only the window from quarantine start through the first day the newly-
infected ratio drops below 0.01 (after which the k_q signal is dominated by
noise); `compute_adherence_bar_estimate` drops any run whose surviving
window is shorter than 5 timesteps, and truncates survivors to exactly 5 so
they can be averaged consistently. `plot_adherence_bar_combined` renders
these per-level mean estimates as a grouped bar chart (target vs. observed
adherence) into f_degeneration_combined.pdf.

Outputs per adherence level: result_figures/kq_true_vs_estimated_a{level}.pdf
and result_figures/analyze_quarantine_dynamics_data_a{level}.pkl. Combined
outputs: result_figures/f_degeneration_combined.pdf and
result_figures/adherence_comparison.pdf.


noisy_k_est.py:
Compares MFA-estimated mean degree against ground truth under three levels
each of Gaussian and Poisson measurement noise, using a fixed 6-run-per-noise
-type data generation protocol documented at the top of the file (each run
appends a pre-/post-quarantine sample pair to experiment_data/mfa_xy_data.txt,
with `clear=True` only on the very first run so all runs share the same
underlying network).

Loads all 12 samples from experiment_data/mfa_xy_data.txt via extract_mfa;
samples 0-5 are the 3 Gaussian noise levels (sigma, sigma/2, sigma/3, as
pre/post-quarantine pairs), samples 6-11 the 3 Poisson levels (scale 1/9,
1/4, 1). `plot_k_est(noise_groups, title, out_path)` plots the shared true
<k> curve once (all noise levels share the same underlying network) plus
each noise level's estimated <k> (with +/-1 std band) in a distinct color,
split at the quarantine boundary. Produces
result_figures/noisy_k_est.pdf (Gaussian) and
result_figures/noisy_k_est_poisson.pdf (Poisson).


plot_optimizer.py:
`plot_optimizer_results(samples, even_or_odd)` visualizes the raw
optimizer-run estimates (`w1 all runs`) from mean_field_approx.py, rather
than a pre-computed mean: for each sample matching the `even_or_odd` filter
(0 = pre-quarantine/even-indexed samples only, 1 = post-quarantine/odd-indexed
only, 2 = all), it pads all runs in that sample to a common length, plots the
mean +/-1 std across runs, and — only for the third sample (i == 2) — overlays
the true mean degree as a horizontal reference line, labeling each sample's
curve by an inferred beta value (`0.15 - 0.015 * i`, i.e. assuming the
samples correspond to a beta sweep). Saves
result_figures/optimizer_results.pdf and
result_figures/plot_optimizer_data.pkl. Run directly (`__main__`), it loads
experiment_data/mfa_xy_data.txt and calls `plot_optimizer_results(samples,
even_or_odd=2)`.


plot_split_optimization.py:
Compares MFA-estimated vs. true mean degree for one pre-quarantine sample and
one post-quarantine sample (samples[0] and samples[1] of
experiment_data/mfa_xy_data.txt), aligning the true series to the estimated
series' timestamps via `np.isin`. Plots both true curves (solid black) and
both estimated curves (dashed, distinct colors) with +/-1 std bands from
`w1 all runs`, with a vertical line marking the quarantine boundary. Saves
result_figures/mfa_degree_estimates.pdf and
result_figures/mfa_degree_estimates_data.pkl (the raw per-run data is present
in the code as commented-out dict entries and not currently written).


sensitivity_analysis.py:
`plot_sensitivity_results(file_path, parameter_name, value_range)` plots, for
each sample in a sensitivity-sweep data file, the mean +/-1 std of the
`w1 all runs` estimator trajectories against a horizontal true-<k_0> reference
line, one curve per sample labeled by its corresponding value in
`value_range`. Called three times against the sweep files produced by
mfa_drive_compute.py's `sensitivity_analysis()`:
experiment_data/sensitivity_num_seeds.txt (seed counts [5, 10, 15]),
sensitivity_init.txt (initial-infected proportions [0.025, 0.05, 0.10]), and
sensitivity_density.txt (network densities [0.03, 0.04, 0.05]). Saves
result_figures/sensitivity_{parameter_name}.pdf per sweep.


plot_identifiability.py:
Visualizes the identifiability analysis mean_field_approx.py runs alongside
its main MFA fit (see mean_field_approx.py's identifiability mode in
README_main.txt). Two independent plotting functions, both parameterized by
`even_or_odd` (0 = pre-quarantine/even samples, 1 = post-quarantine/odd
samples, 2 = all, with a vertical line marking the boundary between the two
halves when applicable):

`plot_model(samples, even_or_odd=2)` compares the true newly-infected ratio
("Given Newly Infected Ratio") against the estimator's predicted newly
-infected ratio (mean +/-1 std of "y_pred all runs", padded to a common
length across runs). Saves result_figures/identifiability_results.pdf and
result_figures/plot_identifiability_data.pkl.

`plot_identifiability_results(samples, even_or_odd=2)` compares true vs.
predicted n_i (newly infected ratio, from "Given Newly Infected Ratio" vs.
"n_i Predicted (Identifiability)") and true vs. predicted n_r (newly
recovered ratio — true value is "Newly Recovered" raw counts divided by
node count, since that dataset stores counts rather than a ratio; predicted
value is "n_r Predicted (Identifiability)" directly). Node count is pulled
from the first sample's "Number of nodes" field, falling back to 200 if
missing. Saves result_figures/identifiability_n_i_n_r.pdf and
result_figures/plot_identifiability_n_i_n_r_data.pkl.

Run directly (`__main__`), it loads experiment_data/mfa_xy_data.txt and
calls `plot_identifiability_results(samples, even_or_odd=2)` only —
`plot_model` is defined but not invoked from `__main__`.
