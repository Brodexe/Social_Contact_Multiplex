# Use this file to run the mean field approximation several times
import subprocess
import sys
import find_seeds
import networkx as nx
import correlated_graphs

repeat = 1  # Number of times to run the MFA

# Run mean field approximation with varying adherence levels
def adherence_mode():
    write_to = ("experiment_data/a_0.2", "experiment_data/a_0.4", "experiment_data/a_0.6", 
                "experiment_data/a_0.8", "experiment_data/a_0.9", "experiment_data/a_1.0")
    adherence_level = (0.2, 0.4, 0.6, 0.8, 0.9, 1.0)

    # Clear previous data files
    for file in write_to:
        open(file, "w").close()

    # Iteratively run MFA for each adherence level
    for i in range(len(write_to)):
        for _ in range(repeat):
            subprocess.run([sys.executable, "mean_field_approx.py", write_to[i], str(adherence_level[i]),
                            "adherence mode"])

def simple_repeat():
    for _ in range(repeat):
        subprocess.run([sys.executable, "mean_field_approx.py"])

def yjmob_mode():
    files_to_clear = ["experiment_data/yjmob0_runs.txt", "experiment_data/yjmob1_runs.txt",
                      "experiment_data/yjmob2_runs.txt", "experiment_data/yjmob3_runs.txt",
                      "experiment_data/yjmob4_runs.txt", "experiment_data/yjmob5_runs.txt"
                      ]
    
    for file in files_to_clear:
        open(file, "w").close()

    for _ in range(repeat):
        # File index: correspond to different time intervals in YJMob dataset
        for file_index in range(6):
            subprocess.run([sys.executable, "mean_field_approx.py", 
                            str(file_index), "yjmob mode"])
            
# Quantities under consideration for sensitivity analysis:
# number of seeds, initial infected proportion, density of the network
# System argument has following structure:
# mean_field_approx.py <num_seeds> <init> <write_file>
# Network is automatically read by mean_field_approx.py. Not provided as argument
def sensitivity_analysis():
    files_to_clear = ["experiment_data/sensitivity_num_seeds.txt",
                      "experiment_data/sensitivity_init.txt",
                      "experiment_data/sensitivity_density.txt"
                      ]
    
    for file in files_to_clear:
        open(file, "w").close()

    n = 200
    p = 0.05
    
    # Generate and write default networks to be read later
    contact_network = nx.erdos_renyi_graph(n, p)
    num_contact_edges = len(contact_network.edges())
    default_seeds = find_seeds.find_seed_set(contact_network, num_seeds=10, exponent=2)
    default_seed_arg = str(list(map(int, default_seeds)))
    default_init_arg = "0.05"
    default_social = correlated_graphs.create_social_graph(contact_network, nE=2*num_contact_edges)[0]

    # Default contact
    nx.write_gml(contact_network, "experiment_data/mfa_contact.gml")
    # Use default social network. Write it to file for MFA to read
    nx.write_gml(default_social, "experiment_data/mfa_social.gml")

    # First, vary number of seeds
    # Append new seeds to existing set to reduce variability
    seeds = find_seeds.find_seed_set(contact_network, num_seeds=5, exponent=2)
    num_comparisons = 3
    for i in range(num_comparisons):
        # Add 5 more unique seeds in each comparison
        while len(seeds) < 5 * (i + 1):
            new_seed = find_seeds.find_seed_set(contact_network, num_seeds=1, exponent=2)
            if new_seed[0] not in seeds:
                seeds += new_seed
        seed_arg = str(list(map(int, seeds)))
        for _ in range(repeat):
            subprocess.run([sys.executable, "mean_field_approx.py", 
                            str(seed_arg), default_init_arg, 
                            "experiment_data/sensitivity_num_seeds.txt",
                            "sensitivity analysis mode",
                            ])
    
    # Vary initial infected
    init_list = [0.025, 0.05, 0.10]
    for init in init_list:
        for _ in range(repeat):
            subprocess.run([sys.executable, "mean_field_approx.py", 
                            str(default_seed_arg), str(init), 
                            "experiment_data/sensitivity_init.txt",
                            "sensitivity analysis mode",
                            ])
    
    # Finally, vary density of the contact network
    density_list = [0.03, 0.04, 0.05]
    for density in density_list:
        contact_network = nx.erdos_renyi_graph(n=n, p=density)
        # Generate new contact network with given density
        # Overwrite existing contact network file
        nx.write_gml(contact_network, "experiment_data/mfa_contact.gml") 

        for _ in range(repeat):
            subprocess.run([sys.executable, "mean_field_approx.py", 
                            str(default_seed_arg), default_init_arg, 
                            "experiment_data/sensitivity_density.txt",
                            "sensitivity analysis mode",
                            ])

# adherence_mode: Run MFA with different adherence levels
# simple_repeat: Run MFA several times with same configuration
# yjmob_mode: Run MFA on YJMob dataset
# sensitivity_analysis: Run MFA for sensitivity analysis on parameters

if __name__ == "__main__":
    # adherence_mode()
    # yjmob_mode()
    sensitivity_analysis()
    # simple_repeat()