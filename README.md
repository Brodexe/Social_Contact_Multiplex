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