Social Network Influence & Epidemic Simulation:

This project provides a framework for simulating, analyzing, and visualizing social network dynamics, information spread, and epidemic processes under varying conditions of quarantine, adherence, and network structure. It integrates graph generation, influence maximization, SIR-based epidemic modeling, and Mean Field Approximation (MFA) analyses.

Project Structure:
Core Simulation & Analysis (.py files in main folder)
Implements:
Directed and correlated graph construction.

Social network modeling and seed selection for influence maximization (IC and LT models).

SIR/SIRS epidemic simulations with quarantine and information spread.

MFA based parameter optimization

Tools for processing movement/contact networks (e.g., YJMob dataset).

Result Generation & Visualization (result_figures/):
Provides scripts to:
Parse simulation outputs into structured formats.

Estimate quarantine adherence and optimize network parameters.

Visualize infection, information, and adherence dynamics.

Explore sensitivity of MFA estimates to key simulation parameters.

Key Features:
Flexible graph and social network generation with controlled correlation and similarity.

Influence maximization under the Independent Cascade and Linear Threshold models.

Integration of quarantine and information propagation dynamics in epidemic simulations.

Mean Field Approximation framework for parameter inference and post-quarantine analysis.

Support for multiple datasets, including real-world movement/contact data (YJMob).

Dependencies:
numpy, scipy — Numerical operations and optimization.

networkx — Graph representation and manipulation.

matplotlib — Visualization of results and plots.

pickle — Serialization of simulation outputs.

py4cytoscape — Optional integration with Cytoscape for network visualization.

Usage:
Simulation: Run core scripts to generate networks, simulate SIR dynamics, and compute influence maximization metrics.

Pipelines: Run MFA several times to populate data files for analysis (mfa_drive_compute.py), with SIR/MFA data.

Analysis: Parse outputs using MFA tools (extract_mfa.py) and compute adherence, degree estimates, and loss metrics.

Visualization: Generate publication-quality plots of infection, informed populations, optimizer estimates, and sensitivity analyses.

This README covers purpose and functionality of main folder .py files.

correlated_graphs.py:
Implements several methods for generating and analyzing directed graphs with various correlation and similarity structures.

The core function, `create_correlated_digraph`, constructs a directed graph where edge existence correlates with an undirected base graph, allowing for controlled sparsity through a correlation factor.

Additionally, `create_w_k_hop_correlation` builds a graph based on Jaccard similarity between k-hop neighborhoods, providing insights into graph proximity and connectivity.

The `create_social_graph` function models a social network by utilizing Jaccard similarity and edge sampling based on ranked similarity, enabling the creation of directed social graphs with variable edge densities.





extract_loss_calc.py:
Loads a real-world social network, computes loss matrices for Independent Cascade (I.C.) and Linear Threshold (L.T.) diffusion models, and manages their storage and retrieval.

It parses a Facebook network dataset, relabels nodes for consistency, and generates multiple correlated networks for loss evaluation.

The resulting I.C. and L.T. loss matrices are written to a structured text file and can be safely re-parsed with validation checks.

For convenience, parsed matrices are simplified by retaining only their final rows, enabling easy comparison and downstream analysis.





find_seeds.py:
Provides a probabilistic method for selecting seed nodes in a social network, based on node degrees and a configurable exponent.

The function find_seed_set calculates the probability of each node being selected as a seed, ensuring a diverse and influential set of starting nodes.

The initialize_social_IM function initializes a social influence model (Independent Cascade or Linear Threshold) with a specified number of seeds and influence parameters, running simulations to determine the maximum influence spread.

This approach allows for flexible seed selection and influence maximization in social network models.





IM.py:
Models influence spread in social networks using the Independent Cascade (IC) and Linear Threshold (LT) diffusion models.

The IC_prob_matrix function simulates the probability of each node becoming informed based on multiple Monte Carlo simulations, while IC tracks the actual spread of influence.

The greedy function selects an optimal set of seed nodes to maximize influence spread using the IC model, while greedy_for_lt performs a similar task for the LT model by considering influence thresholds.

Both models allow for quarantine handling, ensuring nodes in quarantine are not activated, and the influence of a node is based on its neighbors' status.





informingcontact.py:
Simulates and visualizes the spread of influence in social and contact networks, using both the Independent Cascade (IC) and Linear Threshold (LT) models.

It generates a contact network from a file, correlates it with a social network, and simulates the SIR epidemic model on the social graph. The resulting social network is used for Influence Maximization (IM) to identify seed nodes, with the goal of reducing the spread of infection by removing edges from the contact network.

Supports integration with Cytoscape via py4cytoscape for visualization and can save networks to GML files or display them inline using matplotlib.

It also compares the influence spread of the greedy IM algorithm with a random seed selection approach, plotting edge removal efficiency as a function of k, the number of seed nodes chosen.





lt_ic_loss_function.py:
Calculates the loss between observed and inferred quarantine data for the Independent Cascade (I.C.) and Linear Threshold (L.T.) models, and evaluates the effect of varying thresholds on the loss.

It generates subgraphs from a social network using random walks and computes the loss of L.T. with respect to I.C. using the mean squared error (MSE) metric. The script includes functionalities for random node removal, edge existence probability.

It also supports generating multiple networks to observe the impact on loss and visualizes the results as a 3D bar graph comparing losses across networks. Additionally, it provides the ability to plot loss comparisons with varying thresholds.





mean_field_approx.py:
Simulates an SIR model on a contact network, optimizing the parameters (mean node degree and recovered fraction) using mean-field approximation.

It supports multiple modes (standard, adherence, YJMOB, sensitivity analysis) and saves simulation results, including newly infected and recovered counts, to a file.

The optimization uses L-BFGS-B to minimize error between predicted and true dynamics.





mfa_drive_compute.py:
Runs the Mean Field Approximation (MFA) multiple times with varying parameters to explore different scenarios.

adherence_mode: Runs MFA for different adherence levels (0.2, 0.4, 0.6, 0.8, 0.9, 1.0) and saves results.

simple_repeat: Runs MFA several times with the same configuration.

yjmob_mode: Runs MFA on the YJMob dataset for different time intervals.

sensitivity_analysis: Runs MFA while varying the number of seeds, initial infected proportion, and network density.

Iterates multiple times to gather sufficient data.





parse.py:
Defines a function to parse an edge list from a text file and create a NetworkX graph.

parse: Reads a file with edge pairs, adds edges to a graph, and determines the minimum node index.

G.add_edge(i, j): Adds an edge between nodes i and j for each line in the file.

It returns the constructed graph. If parse_example is set to True, you can test the function by passing a file containing edge data.





SIR_examples.py:
Simulates and visualizes various SIR (Susceptible-Infected-Recovered) models with different quarantine strategies and conditions.

informed_vs_noninformed: Compares infection rates with and without quarantine.

const_quarantines: Simulates infection spread with a constant quarantine duration and compares with no quarantine.

normal_dist_quarantines: Tests the effect of Gaussian quarantine on infection spread.

jaccard_similarity: Calculates and visualizes the Jaccard similarity between social and contact networks.

random_vs_nonrandom_seeds: Compares infection rates using random vs. degree-based non-random seed selection.

compare_infections_adherence: Compares the effect of full vs. partial adherence on infection rates.

r_quarantine: Simulates quarantine measures that last until recovery.

permanent_quarantine: Tests permanent quarantine strategies on infection dynamics.

plot_all_quarantine: Plots results for all quarantine strategies to compare their effects.

run_simulations: Runs all the above simulations.

SIR_pickle_dump: Saves the simulation results and model parameters into a pickle file.

pickle_load: Loads and prints the saved simulation data.

The main function executes the simulations and saves results for further analysis. The visualizations include infection curves for different strategies, all saved as PDF figures for publication.





SIR.py:
Simulation of an SIR (Susceptible, Infected, Recovered) model with additional features, including quarantine measures, information spread, and social network dynamics. 

Main Features::
SIRS Model with State Transitions:
The sirs_step function handles the transition of nodes through the SIR states, considering infection spread (via the beta parameter), recovery (via the gamma parameter), and immunity loss (via the mu parameter).

Quarantine Mechanism:
quarantine_edge_removal quarantines nodes based on certain conditions, removing edges to prevent further spread. It checks if a node is "informed" and "adhering" to quarantine measures before quarantining it.

The restore_edges function restores previously removed edges when the quarantine ends, ensuring a proper simulation of the dynamics.

Node State and Information Spread:
The simulation includes the spread of information about quarantining measures through a social network (social_network), using either Independent Cascade (IC) or Linear Threshold (LT) models.

Initially uninformed nodes can become "informed" during the simulation (at the begin_q time). Once informed, they may follow quarantine measures if adhering to them.

Dynamic Quarantine and Social Network:
The simulation adjusts quarantine statuses dynamically, with users possibly remaining in quarantine for a fixed or variable period. The state of the network (edges, nodes) can change depending on which nodes are quarantining and whether information about quarantining spreads.

Infection Dynamics:
Infection spread is managed using sirs_step, where infected nodes try to infect susceptible neighbors with a probability determined by beta.

Additionally, nodes have a recovery probability (gamma) and possibly lose immunity (mu).

Simulation Data Collection:
During the simulation, the model keeps track of various metrics, including:

Infection count over time (Inf list).

Quarantine status for each node (all_quaratines).

The degree distribution (dynamic_degree), tracking changes in node connectivity.

Quarantine Duration and Edge Restoration:
For nodes that are quarantining, the length of their quarantine period is either fixed (q is an integer) or variable (using a normal distribution). The edges are restored after the quarantine period ends (in q=True or "r" mode).

Key Simulation Steps:
Initialize the social network and set the initial node states.

Propagate infections using the sirs_step method, which incorporates the likelihood of infection spread, recovery, and immunity loss.

Model the quarantine process with dynamic updates:
Edge removals when nodes are quarantined.

Edge restorations either at the end of a fixed quarantine period or immediately upon recovery.

Information spread is modeled via the find_seeds method for determining initial informed nodes, which then spreads through the social network via either the Independent Cascade (IC) or Linear Threshold (LT) model.

Track key metrics for each time step:
Infection dynamics (Inf list).

The state of quarantining (all_quaratines).

The number of informed individuals and quarantined individuals at each time step.

Node degrees, to assess how quarantine and network changes affect the structure over time.





yjmob_network_creation.py:
Processes movement data, computes contact networks, and generates social networks based on user interactions.

Main Steps and Features:
Data Parsing and Preparation:
The code starts by reading movement data from a CSV file (yjmob_sample.csv).

It processes the data into time intervals and stores it in the day_data_initial and day_data_final dictionaries.

day_data_initial: Stores user data grouped by time intervals (15-minute intervals).

day_data_final: Transforms the initial data into a dictionary where each interval has users with their time and location data.

Collisions Detection (for Contact Networks):
A collision occurs when two users are in the same location within a 2-time unit window (checking current and next time point).

The distance between users is computed using the Cartesian distance formula.

If two users’ coordinates match (within the defined time window), a collision is counted, and the pair is stored as an edge in a graph.

Creating Contact Networks:
For each time interval, the collision data is used to create an undirected contact network (contact_network), where nodes represent users and edges represent interactions (collisions).

The contact network for each interval is stored in contact_networks.

Social Network Creation:
A social network is built from the global collision frequency.

The 75th percentile of the collision count is calculated and used to filter out edges (i.e., only keep edges with a collision count greater than or equal to the 75th percentile).

The social network is directed (social_network), and this directed graph is then relabeled for consistency.

Ensuring Consistency Across Networks:
The union of all nodes across all time intervals is computed to ensure that all contact and social networks have the same set of nodes.

The user IDs are relabeled to consecutive integers for consistency across all networks (this is important when integrating these networks with external tools like Cytoscape).

Relabeling and Exporting Networks:
For each interval, the contact and social networks are saved in .gml format using nx.write_gml.

Cytoscape Integration: If ping_cytoscape is set to True, the social network is converted to an undirected graph and relabeled to avoid node overlaps. This union of the contact and social networks is sent to Cytoscape using py4cytoscape's create_network_from_networkx function.

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