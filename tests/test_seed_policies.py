"""
Checks app.seeding against the research seed-selection code it ports.

  * SeedPolicyRun reproduces a reference loop written the way
    adaptive_seed_selection.degree_based_selection / random_seed_selection drive
    SIR.Simulate_SIR (one call per batch, or per tick without information spread),
    tick for tick under identical RNG seeds.
  * CostModel matches adaptive_seed_selection.global_cost_function.
  * Hill-climb keeps a swap whose batch cost did not rise; the MILP's seed term
    shrinks its seed set.

Run with `python -m pytest tests` or `python tests/test_seed_policies.py` from the repo root.
"""

import os
import random
import sys
from copy import deepcopy

import networkx as nx
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import network_setup  # noqa: E402
import SIR  # noqa: E402
from app import seeding  # noqa: E402

GAMMA, MU, INIT = 0.07, 0.05, 0.05
CASES = {
    "degree_lt":           dict(algorithm="degree", q="r", q_mech=("lt", 1), batch_interval=2, info_spread=True, T=12),
    "random_lt_q_true":    dict(algorithm="random", q=True, q_mech=("lt", 1), batch_interval=3, info_spread=True, T=12),
    "degree_no_spread":    dict(algorithm="degree", q="r", q_mech=("lt", 1), batch_interval=2, info_spread=False, T=8),
    "random_ic_per_tick":  dict(algorithm="random", q="r", q_mech=("ic", 0.05), batch_interval=1, info_spread=True, T=4),
}


def _setup(k_frac=0.75, rng_seed=7):
    shared = network_setup.load_shared_network()
    contact, social = shared["contact_network"], shared["social_network"]
    rng = random.Random(rng_seed)
    nodes = list(contact.nodes())
    init_state = {u: int(rng.random() < 0.08) for u in nodes}
    adhering = set(rng.sample(nodes, int(0.9 * len(nodes))))
    return contact, social, shared["global_betas"][0], init_state, adhering, int(k_frac * len(nodes))


def _reference(contact0, social0, beta, init_state, adhering, k, algorithm, q, q_mech,
               batch_interval, info_spread, T):
    """The research loop (adaptive_seed_selection.degree_based_selection et al.) for one simulation."""
    t_batch = batch_interval if info_spread else 0
    prev, live, states, seed_sets = init_state, None, [], []
    seed_set = None
    for t in range(T):
        if t % batch_interval == 0:
            if algorithm == "degree":
                G = nx.Graph()
                G.add_nodes_from(contact0.nodes())
                G.add_edges_from(e for e in contact0.edges() if live is None or seeding.edge_key(*e) in live)
                degree = dict(G.degree())
                seed_set = sorted(degree, key=lambda u: degree[u], reverse=True)[:k]
            else:
                seed_set = random.sample(list(contact0.nodes()), k)
            seed_sets.append(sorted(seed_set))
        if (t % batch_interval == 0) if info_spread else True:
            res = SIR.Simulate_SIR(deepcopy(contact0), deepcopy(social0), T=t_batch, beta=beta,
                                   gamma=GAMMA, mu=MU, init=INIT, q=q, q_mech=q_mech,
                                   adherence=set(adhering), begin_q=0, seeds=list(seed_set),
                                   initial_state_dict=prev)
            states += [dict(s) for s in res[4]]
            prev = res[4][-1]
            live = {seeding.edge_key(u, v) for u, v in res[0].edges()}
    return states, seed_sets


def _check_case(name, rng_seed=1234):
    case = dict(CASES[name])
    T = case.pop("T")
    contact, social, beta, init_state, adhering, k = _setup()

    random.seed(rng_seed)
    np.random.seed(rng_seed)
    ref_states, ref_seeds = _reference(contact, social, beta, init_state, adhering, k, T=T, **case)

    random.seed(rng_seed)
    np.random.seed(rng_seed)
    run = seeding.SeedPolicyRun(deepcopy(contact), deepcopy(social), beta=beta, gamma=GAMMA, mu=MU,
                                init=INIT, adherence=set(adhering), mc=1000, k=k,
                                initial_state_dict=init_state, baseline_runs=3, baseline_seed=0, **case)
    states, seeds = [], []
    for _ in range(T):
        run.step()
        states.append(dict(run.state))
        if run.new_batch:
            seeds.append(run.seeds)

    assert seeds == ref_seeds, f"{name}: seed sets diverge"
    for t, (a, b) in enumerate(zip(states, ref_states)):
        assert {u: int(s) for u, s in a.items()} == {u: int(s) for u, s in b.items()}, \
            f"{name}: state diverges at t={t}"


def test_degree_lt():
    _check_case("degree_lt")


def test_random_lt_q_true():
    _check_case("random_lt_q_true")


def test_degree_no_spread():
    _check_case("degree_no_spread")


def test_random_ic_per_tick():
    _check_case("random_ic_per_tick")


class _FixedBaselines:
    def __init__(self, runs):
        self.runs = runs

    def g(self, t0, t1):
        return sum(max(run[t] for run in self.runs) for t in range(t0, t1 + 1))


def test_cost_matches_research():
    import adaptive_seed_selection as research

    rng = random.Random(3)
    G = nx.gnp_random_graph(40, 0.15, seed=3)
    for u, v in G.edges():
        G[u][v]["weight"] = rng.choice([1, 1, 2, 0.5])
    edges = list(G.edges())
    T = 11
    baseline = [[rng.randint(0, 6) for _ in range(T)] for _ in range(4)]
    newly = [rng.randint(0, 5) for _ in range(T)]
    live = [[e for e in edges if rng.random() < 0.7] for _ in range(T)]

    for batch_interval in (1, 2, 5):
        research.initial_contact, research.n = G, G.number_of_nodes()
        research.baseline_runs, research.batch_interval = baseline, batch_interval
        model = seeding.CostModel(G, ("infections", "edges"), batch_interval, _FixedBaselines(baseline))
        removed = [model.removed_cost({seeding.edge_key(*e) for e in lv}) for lv in live]
        for t_cur in range(T):
            expected, _ = research.global_cost_function(newly, live, 30, t_cur)
            got = model.evaluate(t_cur, newly, removed, 30)
            assert abs(got["cost"] - expected) < 1e-12, (batch_interval, t_cur, got["cost"], expected)
            assert got["terms"]["seeds"] == 30 / G.number_of_nodes()


def test_hill_climb_accepts_non_worsening_swap():
    contact, social, beta, init_state, adhering, k = _setup()
    run = seeding.SeedPolicyRun(deepcopy(contact), deepcopy(social), beta=beta, gamma=GAMMA, mu=MU,
                                init=INIT, adherence=set(adhering), algorithm="hill", k=k,
                                initial_state_dict=init_state, baseline_runs=1, baseline_seed=0)
    hill = run.strategy
    first = set(hill.accepted)
    hill.observe({"cost": 1.0})               # first batch: nothing to compare, propose a swap
    candidate = set(hill.candidate)
    assert len(candidate) == k and len(candidate ^ first) == 2
    hill.observe({"cost": 1.2})               # worse: keep the accepted set
    assert hill.accepted == first
    candidate = set(hill.candidate)
    hill.observe({"cost": 0.9})               # better: take the swap
    assert hill.accepted == candidate


def test_milp_seed_term_shrinks_seed_set():
    contact, social, beta, init_state, adhering, k = _setup()
    sizes = {}
    for terms in (("infections", "edges"), ("infections", "edges", "seeds")):
        run = seeding.SeedPolicyRun(deepcopy(contact), deepcopy(social), beta=beta, gamma=GAMMA, mu=MU,
                                    init=INIT, adherence=set(adhering), algorithm="milp", k=k,
                                    cost_terms=terms, initial_state_dict=init_state,
                                    baseline_runs=3, baseline_seed=0)
        sizes[len(terms)] = len(run.seeds)
        assert len(run.seeds) <= k
    assert sizes[3] < sizes[2], sizes


if __name__ == "__main__":
    for name in CASES:
        _check_case(name)
        print(f"ok  {name}")
    test_cost_matches_research()
    print("ok  cost function")
    test_hill_climb_accepts_non_worsening_swap()
    print("ok  hill-climb")
    test_milp_seed_term_shrinks_seed_set()
    print("ok  milp seed term")
