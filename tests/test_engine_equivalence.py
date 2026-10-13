"""
Checks that app.engine.MultiplexSIRS reproduces SIR.Simulate_SIR exactly.

Both are run from identical RNG seeds on copies of the shared network; the
per-step SIRS states, informed sets, and mean contact degree (i.e. quarantine
edge cuts/restores), plus the final contact network edges, must all match. Run
with `python -m pytest tests` or `python tests/test_engine_equivalence.py` from
the repo root.
"""

import os
import random
import sys
from copy import deepcopy

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import network_setup  # noqa: E402
import SIR  # noqa: E402
from app.engine import MultiplexSIRS  # noqa: E402

CASES = {
    "ic_q_r":        dict(q="r", q_mech=("ic", 0.05), adherence=1.0, seeds=5, begin_q=0, T=20),
    "ic_q_true":     dict(q=True, q_mech=("ic", 0.05), adherence=0.7, seeds=5, begin_q=3, T=20),
    "lt_q_int":      dict(q=6, q_mech=("lt", 1), adherence=0.8, seeds=4, begin_q=0, T=20),
    "ic_no_q":       dict(q=False, q_mech=("ic", 0.05), adherence=1.0, seeds=3, begin_q=0, T=15),
    "fj_q_true":     dict(q=True, q_mech=("FJ", 1.25), adherence=1.0, seeds=5, begin_q=0, T=20),
    "fj_q_r":        dict(q="r", q_mech=("FJ", 1.25), adherence=0.9, seeds=5, begin_q=0, T=20),
    "single_tick":   dict(q="r", q_mech=("ic", 0.05), adherence=1.0, seeds=[0, 5, 9], begin_q=0, T=1),
    # Competing misinformation (non-adherers are misinformation seeds too)
    "mis_ic_takeover": dict(q="r", q_mech=("ic", 0.05), adherence=0.85, seeds=5, begin_q=0, T=20,
                            misinfo=True, misinfo_seeds=4, misinfo_mode="takeover", misinfo_val=0.08),
    "mis_ic_collide":  dict(q=True, q_mech=("ic", 0.05), adherence=0.9, seeds=5, begin_q=2, T=20,
                            misinfo=True, misinfo_seeds=3, misinfo_mode="collide"),
    "mis_lt_takeover": dict(q=6, q_mech=("lt", 1), adherence=0.9, seeds=4, begin_q=0, T=20,
                            misinfo=True, misinfo_seeds=2, misinfo_mode="takeover"),
    "mis_fj_takeover": dict(q="r", q_mech=("FJ", 1.25), adherence=0.9, seeds=5, begin_q=0, T=20,
                            misinfo=True, misinfo_seeds=3, misinfo_mode="takeover"),
}


def _run_pair(case, rng_seed=1234):
    shared = network_setup.load_shared_network()
    beta = shared["global_betas"][0]
    params = dict(beta=beta, gamma=0.07, mu=0.05, init=0.08, **case)

    random.seed(rng_seed)
    np.random.seed(rng_seed)
    ref = SIR.Simulate_SIR(deepcopy(shared["contact_network"]), deepcopy(shared["social_network"]), **params)

    random.seed(rng_seed)
    np.random.seed(rng_seed)
    T = params.pop("T")
    sim = MultiplexSIRS(deepcopy(shared["contact_network"]), deepcopy(shared["social_network"]), T=T, **params)
    states, informed, misinformed, mean_degree = [], [], [], []
    for _ in range(T if T > 0 else 1):
        sim.step()
        states.append(dict(sim.state))
        informed.append(set(int(u) for u in sim.informed))
        misinformed.append(set(int(u) for u in sim.misinformed))
        mean_degree.append(np.mean([deg for _, deg in sim.contact.degree()]))

    return ref, (states, informed, misinformed, mean_degree, sim.contact)


def _check(name):
    ref, (states, informed, misinformed, mean_degree, contact) = _run_pair(CASES[name])
    ref_contact, ref_states, ref_degree, ref_informed, ref_mis = ref[0], ref[4], ref[6], ref[8], ref[11]
    assert len(ref_states) == len(states), name
    for t, (a, b) in enumerate(zip(ref_states, states)):
        assert a == b, f"{name}: SIRS state differs at step {t}"
    for t, (a, b) in enumerate(zip(ref_informed, informed)):
        assert set(int(u) for u in a) == b, f"{name}: informed set differs at step {t}"
    for t, (a, b) in enumerate(zip(ref_mis, misinformed)):
        assert set(int(u) for u in a) == b, f"{name}: misinformed set differs at step {t}"
    # Simulate_SIR's dynamic_degree is the mean contact degree after each step's cuts/restores
    assert np.allclose(ref_degree, mean_degree), f"{name}: contact edge counts differ"
    assert set(map(frozenset, ref_contact.edges())) == set(map(frozenset, contact.edges())), \
        f"{name}: final contact edges differ"


def test_ic_q_r():
    _check("ic_q_r")


def test_ic_q_true():
    _check("ic_q_true")


def test_lt_q_int():
    _check("lt_q_int")


def test_ic_no_q():
    _check("ic_no_q")


def test_fj_q_true():
    _check("fj_q_true")


def test_fj_q_r():
    _check("fj_q_r")


def test_single_tick():
    _check("single_tick")


def test_misinfo_ic_takeover():
    _check("mis_ic_takeover")


def test_misinfo_ic_collide():
    _check("mis_ic_collide")


def test_misinfo_lt_takeover():
    _check("mis_lt_takeover")


def test_misinfo_fj_takeover():
    _check("mis_fj_takeover")


if __name__ == "__main__":
    for case_name in CASES:
        _check(case_name)
        print(f"ok  {case_name}")
