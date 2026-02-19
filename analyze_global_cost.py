import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import networkx as nx

# File form (.txt):
# Seed set: <tuple of node indices>, cost: <float>
read_file = "hon_experiment_data/seed_costs.txt"
def extract_average_costs():
    runs_dict = {}
    with open(read_file, 'r') as f:
        for line in f:
            if line.startswith("Seed set:"):
                parts = line.split(", cost: ")
                seed_set_str = parts[0].replace("Seed set: ", "").strip()
                cost_str = parts[1].strip()

                # Convert seed set string to tuple of integers
                seed_set = tuple(int(x) for x in seed_set_str.strip("()").split(",") if x)
                cost = float(cost_str)

                if seed_set not in runs_dict:
                    runs_dict[seed_set] = []
                runs_dict[seed_set].append(cost)
    return runs_dict

runs_dict = extract_average_costs()

# Average cost for each seed set across all runs
average_costs = {seed_set: np.mean(costs) for seed_set, costs in runs_dict.items()}

# Generate all combinations of seeds sets:
# All sizes, all nodes considered
all_nodes = list(contact_network.nodes())
all_seed_sets = []
# Practical constraint on how many seeds to consider
for size in range(1, int((n + 1) / 4)):
    seed_set_of_size = np.random.choice(all_nodes, size=size, replace=False)
    all_seed_sets.append(seed_set_of_size)

# See if submodularity is satisfied: adding a seed should not increase marginal gain
submodular_violations = 0
for seed_set in all_seed_sets:
    seed_set = list(seed_set)
    for node in all_nodes:
        if node not in seed_set:
            smaller_set = seed_set
            larger_set = seed_set + [node]

            cost_smaller = average_costs.get(tuple(smaller_set), None)
            cost_larger = average_costs.get(tuple(larger_set), None)

            if cost_smaller is not None and cost_larger is not None:
                marginal_gain_smaller = cost_smaller - average_costs.get(tuple(smaller_set + [n]), 0) if len(smaller_set) + 1 <= len(all_nodes) else 0
                marginal_gain_larger = cost_larger - average_costs.get(tuple(larger_set + [n]), 0) if len(larger_set) + 1 <= len(all_nodes) else 0

                if marginal_gain_smaller < marginal_gain_larger:
                    submodular_violations += 1

print("Number of submodularity violations:", submodular_violations)

# See if monotonocity is satisfied: each added seed should not increase cost
# Probably not satisfied since we have multiple competing terms in the cost function
monotonicity_violations = 0
for seed_set in all_seed_sets:
    seed_set = list(seed_set)
    for node in all_nodes:
        if node not in seed_set:
            smaller_set = seed_set
            larger_set = seed_set + [node]

            cost_smaller = average_costs.get(tuple(smaller_set), None)
            cost_larger = average_costs.get(tuple(larger_set), None)

            if cost_smaller is not None and cost_larger is not None:
                if cost_larger > cost_smaller:
                    monotonicity_violations += 1
print("Number of monotonicity violations:", monotonicity_violations)