"""
Drives adaptive_seed_selection.py and milp.py against the real-world rc_* network
pairs: capstone_proj_data/rc_weighted_contact_bin{i}.gml (i in 1..19) each paired
with the shared capstone_proj_data/rc_social_network.gml.

For each requested bin, calls into adaptive_seed_selection.initialize()/hill2() and
milp.initialize()/milp_seed_selection_stepwise() as library functions (both modules
already support this via their `network`/`social` arguments), and stores every
method's full return data -- cost curves, seed sets, infection/edge curves, etc. --
in a single pickle, keyed by bin index then by method label:

    { bin_i: {"Adaptive": {...}, "MILP": {...}}, ... }

That whole structure is saved to real_world_methods.pkl, and the "Adaptive"-only
slice of it is saved separately to adaptive_real_world.pkl.

adaptive_seed_selection.py and milp.py remain independently runnable
(`python adaptive_seed_selection.py` / `python milp.py`) via their own __main__
blocks, unchanged -- this driver only calls into them as a library.
"""
import argparse
import pickle

import adaptive_seed_selection
import milp

DATA_DIR = "capstone_proj_data"
SOCIAL_NETWORK_PATH = f"{DATA_DIR}/rc_social_network.gml"
CONTACT_NETWORK_TEMPLATE = DATA_DIR + "/rc_weighted_contact_bin{i}.gml"

OUTPUT_PATH = "real_world_methods.pkl"
ADAPTIVE_OUTPUT_PATH = "adaptive_real_world.pkl"

DEFAULT_BINS = list(range(12, 20))

# Set to False to skip milp.py entirely: only adaptive_real_world.pkl will be
# written (real_world_methods.pkl is skipped since it would have no MILP data).
RUN_MILP = False


def contact_network_path(bin_index):
    return CONTACT_NETWORK_TEMPLATE.format(i=bin_index)


def run_adaptive(bin_index):
    print(f"\n=== Adaptive (hill2): bin {bin_index} ===")
    adaptive_seed_selection.initialize(contact_network_path(bin_index), SOCIAL_NETWORK_PATH)

    (_, cost_curves, infection_curves, edge_term_curves, edge_curves,
     newly_counts, newly_frac, dynamics_list, tagged_contact,
     batch_seed_sets, alpha_w_curves, beta_w_curves) = adaptive_seed_selection.hill2()

    return {
        "cost_curves": cost_curves,
        "infection_term_curves": infection_curves,
        "edge_term_curves": edge_term_curves,
        "edge_curves": edge_curves,
        "newly_infected_counts": newly_counts,
        "newly_infected_frac": newly_frac,
        "dynamics_list": dynamics_list,
        "batch_seed_sets": batch_seed_sets,
        "alpha_w_curves": alpha_w_curves,
        "beta_w_curves": beta_w_curves,
        "social_network": adaptive_seed_selection.initial_social,
        "batch_interval": adaptive_seed_selection.batch_interval,
        "T": adaptive_seed_selection.T,
    }


def run_milp(bin_index):
    print(f"\n=== MILP (milp_seed_selection_stepwise): bin {bin_index} ===")
    milp.initialize(contact_network_path(bin_index), SOCIAL_NETWORK_PATH)

    (seed_sets, cost_curves, infection_curves, edge_term_curves, edge_curves,
     newly_counts, newly_frac, dynamics_list,
     alpha_w_curves, beta_w_curves) = milp.milp_seed_selection_stepwise()

    return {
        "seed_sets": seed_sets,
        "cost_curves": cost_curves,
        "infection_term_curves": infection_curves,
        "edge_term_curves": edge_term_curves,
        "edge_curves": edge_curves,
        "newly_infected_counts": newly_counts,
        "newly_infected_frac": newly_frac,
        "dynamics_list": dynamics_list,
        "alpha_w_curves": alpha_w_curves,
        "beta_w_curves": beta_w_curves,
        "batch_interval": milp.batch_interval,
        "T": milp.T,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run adaptive_seed_selection.py's hill2() and/or milp.py's "
                     "milp_seed_selection_stepwise() against the real-world "
                     "rc_weighted_contact_bin{i}.gml / rc_social_network.gml network pairs."
    )
    parser.add_argument("--bins", type=int, nargs="+", default=DEFAULT_BINS,
                         help=f"Contact network bin indices to run "
                              f"(default: {DEFAULT_BINS[0]}-{DEFAULT_BINS[-1]}).")
    parser.add_argument("--methods", choices=["adaptive", "milp", "both"], default="both",
                         help="Which method(s) to run for each bin (default: both).")
    parser.add_argument("--output", default=OUTPUT_PATH,
                         help=f"Path to write the combined, labeled results pickle "
                              f"(default: {OUTPUT_PATH}).")
    parser.add_argument("--adaptive-output", default=ADAPTIVE_OUTPUT_PATH,
                         help="Path to write just the Adaptive-method results pickle "
                              f"(default: {ADAPTIVE_OUTPUT_PATH}).")
    args = parser.parse_args()

    results = {}
    for bin_index in args.bins:
        methods = {}
        if args.methods in ("adaptive", "both"):
            methods["Adaptive"] = run_adaptive(bin_index)
        if RUN_MILP and args.methods in ("milp", "both"):
            methods["MILP"] = run_milp(bin_index)
        results[bin_index] = methods

    if RUN_MILP:
        with open(args.output, "wb") as f:
            pickle.dump({
                "bins": args.bins,
                "social_network_path": SOCIAL_NETWORK_PATH,
                "contact_network_template": CONTACT_NETWORK_TEMPLATE,
                "results": results,
            }, f)
        print(f"\nSaved combined results for bins {args.bins} to {args.output}")
    else:
        print(f"\nRUN_MILP is False; skipping {args.output}")

    adaptive_only = {bin_index: methods["Adaptive"]
                     for bin_index, methods in results.items() if "Adaptive" in methods}
    if adaptive_only:
        with open(args.adaptive_output, "wb") as f:
            pickle.dump({
                "bins": list(adaptive_only),
                "social_network_path": SOCIAL_NETWORK_PATH,
                "contact_network_template": CONTACT_NETWORK_TEMPLATE,
                "results": adaptive_only,
            }, f)
        print(f"Saved Adaptive-only results for bins {list(adaptive_only)} to {args.adaptive_output}")


if __name__ == "__main__":
    main()
