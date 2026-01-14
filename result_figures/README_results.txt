This README covers usage and functionality of result figure generating .py files.

analyze_quarantine_dynamics.py:
Analyzes post-quarantine network simulation data to estimate adherence and fit model parameters. It performs the following tasks:

Load Simulation Data:
Parses MFA simulation outputs and extracts relevant post-quarantine time series, including node degrees and informed/infected proportions.

Naive Adherence Estimation:
Computes a quick adherence estimate based on deviations in mean node degree.

Parameter Optimization:
Jointly optimizes a scale factor and adherence per run to best match the observed post-quarantine mean degree across simulations.

Dynamic Adherence Tracking:
Computes cumulative adherence estimates over time for each simulation run, capturing how estimates improve as more data becomes available.

Visualization:
Generates publication-quality plots:

True vs estimated mean post-quarantine node degree <k_q>

Cumulative adherence estimates with mean and standard deviation bands

Results Storage:
Saves all processed data, optimized parameters, and estimated time series to a pickle file for downstream analysis.

Output:
PDF plots of <k_q> comparison and cumulative adherence

Pickle file containing processed metrics, parameter estimates, and time series

Dependencies:
numpy, scipy, matplotlib, pickle, extract_mfa

Purpose:
Facilitates quantitative evaluation of quarantine effects and network adherence dynamics in simulation studies.





analyze_yjmob_quarantine.py:
Processes YJMob100k network simulations to estimate quarantine adherence based on Mean-Field Approximation (MFA) degree dynamics and the proportion of informed & infected individuals.

Overview:
Data Loading:
Loads five consecutive network samples (yjmob0_runs.txt to yjmob4_runs.txt) using extract_mfa.parse_sample_data.

Post-quarantine samples are identified (samples 2–4).

Time-Series Aggregation:
Combines infected & informed proportions and dynamic degree (⟨k_q⟩) across post-quarantine samples.

Computes mean and standard deviation across simulation runs.

Visualization:
Plots ⟨k_q⟩ and infected & informed fraction with mean ± 1 standard deviation bands.

Provides an MFA-based visualization of estimated vs true mean node degrees across pre- and post-quarantine intervals.

Quarantine Adherence Estimation:
Estimates adherence from MFA degrees using cumulative optimization over time.

Fits the scale factor S and adherence fraction per run to minimize MSE between estimated and true ⟨k_q⟩.

Computes per-time adherence estimates, mean, and standard deviation across runs.

Compares cumulative adherence to the true known adherence.

Output:
Saves results to a pickle file (cumulative_adherence_results.pkl) containing:

Pre-quarantine mean degree (k_0)

Split point for quarantine

Population size and number of simulations

Time series: i_prime_mean, inf_inf_runs, k_q_true_mean, k_q_true_runs

Cumulative adherence: cumulative_adh_runs, cumulative_adh_mean, cumulative_adh_std

Time indices (t_vals)

Key Features:
Supports multiple post-quarantine samples for robust estimation.

Generates publication-quality plots with mean and standard deviation bands.

Implements a cumulative MSE-based optimization for time-resolved adherence estimation.





extract_mfa.py:
Provides tools to parse output from mean_field_approx.py simulations into structured, analyzable Python objects. It converts text-based simulation results into a list of samples, each represented as a dictionary of datasets.

Overview:
Parses MFA simulation output files and returns a structured collection of samples.

Supported Dataset Keys:
SIR Infections

Dynamic degree

w1 True, w1 Estimated, w1 all runs

w2 True, w2 Estimated

Informed and Infected

Given Newly Infected Ratio

Informed

Data Structure:
Each sample contains:

Number of nodes

Adhering proportion

Time-series datasets with x (time points) and y (observables) values

Special Handling:
Converts np.float64 wrapped numbers into standard numeric values.

Handles nested lists for datasets like w1 all runs and Informed.

Maintains alignment of x-values and corresponding y-values.

File Format Requirements:
Each sample begins with a line ==New Sample==.

Datasets are identified by their names.

Time-series data lines start with x: and y: prefixes.

Error Handling:
Continues parsing even if some lines fail to convert.

Provides warnings for parsing issues without halting execution.

Use Cases:
Compute averages and standard deviations over simulation runs.

Analyze MFA degree estimates and infection dynamics.

Estimate quarantine adherence and other behavioral parameters from simulations.





plot_infected_informed.py:
Visualizes the infection and information spread dynamics in simulated populations under different quarantine adherence levels. It processes simulation outputs parsed via extract_mfa.py and produces publication-ready figures.

Purpose:
Display time evolution of Infected, Informed, and Informed & Infected fractions of a population.

Compare dynamics across different adherence levels to quarantine measures.

Support analysis of both grouped adherence levels and individual adherence scenarios.

Data Input:
Simulation outputs from MFA experiments, organized by adherence levels (e.g., 0.2, 0.4, …, 1.0).

Parsed using the extract_mfa parser.

Primary Functionality:
Grouped Adherence Plots:
Compares multiple adherence levels in a single figure.

Shows mean and variability (standard deviation) across simulation runs.

Uses distinct colors per adherence level and line styles per category (Infected, Informed, Informed & Infected).

Saves results to PDF and a serialized file for later analysis.

Single Adherence Plots:
Focuses on a single adherence scenario.

Displays mean dynamics with variability bands.

Produces clean figures suitable for presentations or publications.

Plotting Features:
Time-series alignment: Adjusts the x-axis based on simulation start times.

Error bands: Visualizes standard deviation across simulation runs.

Custom styling: Uses consistent colors, line styles, and figure sizes for publication-quality output.

Export: Figures saved as PDFs, and data optionally serialized for reproducibility.

Intended Use Cases:
Study how different levels of quarantine adherence influence epidemic progression.

Compare infection, awareness, and combined dynamics over time.

Generate visualizations for reports, papers, or presentations.

Dependencies:
matplotlib for plotting.

numpy for numerical operations.

pickle for saving structured output.

extract_mfa for parsing MFA simulation outputs.

Output Files:

Grouped adherence figure PDF.

Single adherence scenario figure PDF.

Optional serialized data file (.pkl) containing computed means and metadata for further analysis.





plot_informed.py:
Visualizes the time evolution of the informed fraction in a population during a simulation of epidemic and information spread. It produces publication-quality figures and saves processed data for further analysis.

Purpose:
Track how the fraction of informed individuals evolves over time.

Highlight the period before and after a key intervention or split point (e.g., quarantine start).

Provide both visual outputs and serialized data for reproducibility or downstream analysis.

Data Input:
Simulation outputs generated by MFA experiments, parsed using extract_mfa.

Focuses specifically on the Informed category from the dataset.

Primary Functionality:
Compute Statistics:
Aggregates all simulation runs for the informed population.

Calculates mean and standard deviation across runs.

Aligns time series so that the pre-intervention period is represented by zeros.

Visualization:
Plots the mean informed fraction over time with error bands representing variability across runs.

Clearly marks the split point (intervention start) to distinguish pre- and post-intervention dynamics.

Generates publication-ready figures in PDF format.

Data Serialization:
Saves the computed mean, standard deviation, and raw simulation runs to a .pkl file.

Includes metadata such as split point, total time points, and number of runs.

Enables later use without reprocessing raw simulation data.

Plotting Features:
Consistent figure styling (fonts, line widths, and figure size).

Shaded error bands to indicate variability across simulations.

Gridlines and labels for readability.

Intended Use Cases:
Analyze how quickly and extensively information spreads through the population.

Compare informed population dynamics across different scenarios or interventions.

Dependencies:
matplotlib for plotting.

numpy for numerical operations.

pickle for saving structured output.

extract_mfa for parsing MFA simulation outputs.

Output Files:

PDF figure showing the proportion of informed individuals over time.

Serialized results file (.pkl) containing full statistics and raw simulation data.





plot_optimizer.py:
Visualizes the estimates of mean node degrees obtained from optimization routines in MFA simulations, comparing them with ground truth values. It produces publication-quality figures and saves processed data for downstream analysis.

Purpose:
Evaluate how well the optimizer recovers mean node degrees from simulation data.

Compare estimates for pre-quarantine (⟨k₀⟩) and post-quarantine (⟨k_q⟩) periods.

Provide both visual outputs and serialized results for reproducibility.

Data Input:
MFA simulation outputs, parsed using extract_mfa.

Focuses on the w1 all runs dataset containing optimizer results and w1 True (Mean Node Degree) for ground truth.

Primary Functionality:
Select Samples:
Can plot pre-quarantine, post-quarantine, or all samples.

Handles multiple runs per sample, ensuring consistent time series lengths.

Compute Statistics:
Calculates mean and standard deviation of optimizer estimates across runs.

Aligns time series to facilitate comparison with ground truth.

Visualization:
Plots mean estimates over time with shaded error bands indicating variability.

Ground truth values are plotted as horizontal dashed lines.

Supports labeling by simulation parameter (e.g., varying infection rate β).

Generates publication-ready PDF figures.

Data Serialization:
Saves detailed results for each sample, including mean, standard deviation, and ground truth, in a .pkl file.

Enables later use without reprocessing raw simulation data.

Plotting Features:
Consistent figure styling (fonts, line widths, colors).

Gridlines, legends, and labels for clarity.

Distinguishes pre- and post-quarantine estimates visually.

Intended Use Cases:
Assess optimizer performance in recovering network structure from MFA simulations.

Compare estimates under different simulation parameters (e.g., varying infection rates).

Produce reproducible figures for reports, publications, or presentations.

Dependencies:
matplotlib for plotting.

numpy for numerical operations.

pickle for saving structured results.

extract_mfa for parsing MFA simulation outputs.

Output Files:
PDF figure showing optimizer estimates with variability bands.

Serialized results file (.pkl) containing full statistics and raw run data.





plot_split_optimization.py:
Visualizes the estimated mean node degree (⟨k⟩) from MFA simulations, comparing the optimizer’s estimates with the ground truth for pre- and post-quarantine periods. It also saves the processed data for further analysis.

Purpose:
Show how the mean field approximation (MFA) estimates the average node degree over time.

Highlight the effect of quarantine on network connectivity.

Include variability across multiple optimizer runs using standard deviation bands.

Data Input:
MFA simulation outputs parsed using extract_mfa.parse_sample_data.

Requires w1 Estimated, w1 True (Mean Node Degree), and w1 all runs datasets for pre- and post-quarantine samples.

Primary Steps:
Align Ground Truth to Estimated Values:

Only consider true values corresponding to time points where estimates exist.

Compute Mean and Standard Deviation:

For all optimizer runs (w1 all runs), calculate mean and standard deviation to visualize uncertainty.

Plotting:
Pre- and post-quarantine estimates are plotted in distinct colors with dashed lines.

Ground truth values are plotted as solid black lines.

Standard deviation bands are shaded for visual clarity.

Quarantine onset is indicated with a vertical dashed line.

Data Serialization:
Saves processed data, including aligned true values, estimates, mean/std bands, and all run data, in a .pkl file.

Enables reproducibility and further analysis without reprocessing raw MFA outputs.

Plot Features:
Publication-quality figure with large fonts, gridlines, and labeled axes.

Clearly distinguishes pre-quarantine vs post-quarantine dynamics.

Highlights variability across optimizer runs.

Dependencies:
matplotlib for plotting.

numpy for numerical operations.

pickle for data serialization.

extract_mfa for parsing MFA simulation outputs.

Output Files:
result_figures/mfa_degree_estimates.pdf — Figure showing estimated vs true mean node degree.

result_figures/mfa_degree_estimates_data.pkl — Pickled dictionary containing all processed data and statistics.





sensitivity_analysis.py:
Generates plots from sensitivity analysis experiments conducted using the MFA (Mean Field Approximation) framework. It visualizes how estimates of the initial mean node degree (⟨k₀⟩) respond to changes in key simulation parameters.

Purpose:
Explore the effect of varying parameters on the optimizer’s estimates of the mean node degree.

Compare estimated ⟨k₀⟩ with the true network mean degree.

Include standard deviation bands across multiple optimizer runs for uncertainty quantification.

Parameters Analyzed:
Number of Seeds — initial informed individuals in the simulation.

Init - proportion of initially infected individuals

Social Network Density — fraction of possible edges present in the network.

Data Input:
MFA output files parsed using extract_mfa.parse_sample_data.

Requires w1 all runs and w1 True (Mean Node Degree) datasets.

Processing Steps:
Normalize Run Lengths:
All optimizer runs are padded to the maximum run length to allow proper averaging.

Compute Mean and Standard Deviation:
For each parameter value, calculate mean and std across runs.

Plotting:
Plot mean estimate over time with shaded std bands.

Horizontal line for the true mean node degree.

Label each curve with the corresponding parameter value.

Save Plot:
Exported as a publication-ready PDF with consistent figure size for Overleaf.

Plot Features:
Time series of estimated ⟨k₀⟩ for multiple parameter values.

Shaded bands representing variability across optimizer runs.

True reference line for direct comparison.

Gridlines, legends, and axis labels optimized for clarity.

Dependencies:
matplotlib for plotting.

numpy for numerical operations.

extract_mfa for parsing MFA simulation outputs.

Output Files:
result_figures/sensitivity_<parameter>.pdf — PDF plots for each parameter analyzed, e.g.:

sensitivity_Number of Seeds.pdf

sensitivity_Init.pdf

sensitivity_Social Network Density.pdf

Usage Example:

The script automatically generates plots for:

Number of seeds: [5, 10, 15]

Initial infected proportions: [0.05, 0.10, 0.15]

Network densities computed from edge counts [1000, 1500, 2000]

Each curve represents the mean estimate of ⟨k₀⟩ for a given parameter value, with standard deviation bands showing uncertainty.