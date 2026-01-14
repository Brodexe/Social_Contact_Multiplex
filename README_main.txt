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