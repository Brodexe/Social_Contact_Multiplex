"""
Step-at-a-time version of SIR.Simulate_SIR for the interactive app.

Simulate_SIR runs its whole time loop in one call, so it can't be paused,
stepped, or inspected between ticks. MultiplexSIRS holds that loop's state on
an object and advances it one tick per step() call. It deliberately reuses
SIR.py's own helpers (sirs_step, transition, update_N_P, quarantine_edge_removal,
restore_edges) and IM.py's diffusion functions, and replicates the loop body in
the same order -- including the order of every random draw -- so that with the
same RNG seeds it reproduces Simulate_SIR exactly. tests/test_engine_equivalence.py
checks this; if Simulate_SIR's loop changes, update step() to match.

Beyond what Simulate_SIR tracks, the stepper keeps display-only bookkeeping
(when each node was infected/informed, how many times it has been infected,
when its current quarantine began) that the UI shows in node pop-ups. None of
it feeds back into the dynamics.
"""

import math
import random
from copy import deepcopy

import networkx as nx
import numpy as np

import IM
import SIR
import correlated_graphs
import find_seeds


class MultiplexSIRS:
    # Arguments mirror SIR.Simulate_SIR. T may be None for an open-ended run; it only
    # matters to the dynamics when it is 0 or 1 (see Simulate_SIR's T_param handling).
    # mc is the Monte-Carlo count passed to IM.IC_prob_matrix (Simulate_SIR uses 1000).
    def __init__(self, contact_network, social_network, beta, gamma, mu, init,
                 q=False, q_mech=("ic", 0.02), adherence=None, begin_q=0, seeds=None,
                 initial_state_dict=None, T=None, mc=1000):
        if begin_q is None:
            begin_q = 0

        self.mech_type, self.mech_val = q_mech

        if social_network is None:
            social_network = correlated_graphs.create_social_graph(contact_network)[0]

        self.contact = contact_network
        self.social = social_network
        self.beta, self.gamma, self.mu = beta, gamma, mu
        self.begin_q = begin_q
        self.seeds = seeds
        self.mc = mc

        # Simulate_SIR: T == 0 => no information spread; T == 1 => spread on the seeding tick
        self.T_param = T

        n = len(contact_network.nodes())
        self.n = n
        self.N = n - 1
        self.P = n - self.N

        adhering = set()
        if isinstance(adherence, float) and 0 <= adherence <= 1:
            adhering = set(np.random.choice(contact_network.nodes(), size=int((adherence) * n), replace=False))
        elif isinstance(adherence, set):
            adhering = adherence
        self.adhering = adhering

        non_adhering = set(contact_network.nodes()) - adhering
        for node in non_adhering:
            nx.set_node_attributes(contact_network, {node: {'Adheres?': 'No'}})
            nx.set_node_attributes(social_network, {node: {'Adheres?': 'No'}})
        for node in adhering:
            nx.set_node_attributes(contact_network, {node: {'Adheres?': 'Yes'}})
            nx.set_node_attributes(social_network, {node: {'Adheres?': 'Yes'}})

        self.G_initial = deepcopy(contact_network)

        if initial_state_dict is not None:
            state = initial_state_dict.copy()
        elif isinstance(init, (list, set)):
            infected_nodes = set(init)
            state = {u: 1 if u in infected_nodes else 0 for u in range(n)}
        else:
            state = {u: np.random.choice(a=[1, 0], size=1, p=[init, 1 - init])[0]
                     for u in range(n)}
        self.state = state

        self.L = [0 for _ in range(self.N)] + [1 for _ in range(self.P)]

        self.fj_fixed_period = None
        if isinstance(q, int) and q > 1:
            self.d = [q for _ in range(n)]
            self.fj_fixed_period = q
            q = True
        elif q == "r":
            self.d = None
        elif q is True:
            samples_array = np.random.normal(loc=14, scale=2, size=n)
            self.d = [abs(round(x)) for x in samples_array]
        else:
            self.d = None
        self.q = q

        self.quarantine_statuses = [0 for _ in range(n)]
        for node in contact_network.nodes():
            nx.set_node_attributes(contact_network, {node: {'Informed?': 'Uninformed'}})
        for node in social_network.nodes():
            nx.set_node_attributes(social_network, {node: {'Informed?': 'Uninformed'}})

        self.already_quarantining = []

        self.fj_x = {node: 0.0 for node in contact_network.nodes()} if self.mech_type == "FJ" else None
        self.fj_s = None
        self.fj_removed_edges = set()
        self.fj_edge_restore_at = {}

        self.informed = set()
        self.previous_informed = set()
        self.initial_informed_lst = None

        self.t = 0  # number of completed steps

        # --- Display-only bookkeeping (never read by the dynamics) ---
        self.state_since = {u: 0 for u in range(n)}
        self.times_infected = {u: int(state[u] == 1) for u in range(n)}
        self.informed_at = {}
        self.quarantine_since = {}
        self.new_infected = []
        self.new_informed = []

    # Advance one tick. Body follows the `for t in range(T)` loop of SIR.Simulate_SIR.
    def step(self):
        t = self.t
        n = self.n
        contact_network, social_network = self.contact, self.social
        mech_type, mech_val = self.mech_type, self.mech_val
        q, begin_q = self.q, self.begin_q

        # ---- Social network changes ----
        if t < begin_q:
            pass
        elif t == begin_q:
            initial_informed_lst = []
            seeds = self.seeds
            if isinstance(seeds, set) or isinstance(seeds, list):
                initial_informed_lst = seeds
            elif isinstance(seeds, int) and seeds > 0:
                initial_informed_lst = find_seeds.find_seed_set(social_network, num_seeds=seeds, exponent=2)
            elif seeds is None or seeds == [] or seeds == 0:
                initial_informed_lst = []
            self.initial_informed_lst = initial_informed_lst

            self.informed = set(initial_informed_lst)
            for node in self.informed:
                nx.set_node_attributes(contact_network, {node: {'Informed?': 'Informed'}})
                nx.set_node_attributes(social_network, {node: {'Informed?': 'Informed'}})

            if mech_type == "FJ":
                self.fj_s = {node: (1.0 if node in self.informed else 0.0)
                             for node in social_network.nodes()}
                for node in social_network.nodes():
                    self.fj_x[node] = self.fj_s[node]

        if (t > begin_q) or (t == begin_q and self.T_param == 1):
            if self.initial_informed_lst != []:
                if mech_type == "ic":
                    ic_results = IM.IC_prob_matrix(social_network, S=list(self.informed), p=mech_val,
                                                   mc=self.mc, quarantining=self.quarantine_statuses)
                    new_informed_list = ic_results[1]
                elif mech_type == "lt":
                    lt_results = IM.lt_prob_matrix(social_network, threshold=mech_val, S=list(self.informed),
                                                   quarantining=self.quarantine_statuses)
                    new_informed_list = lt_results[1]
                elif mech_type == "FJ":
                    fj_s, fj_x = self.fj_s, self.fj_x
                    new_fj_x = {}
                    for node in social_network.nodes():
                        if fj_s[node] == 1.0:
                            new_fj_x[node] = 1.0
                        else:
                            neighbor_belief_sum = sum(fj_x[nb] for nb in social_network.neighbors(node))
                            deg = social_network.degree(node)
                            new_fj_x[node] = (fj_s[node] + neighbor_belief_sum) / (1 + deg)
                    self.fj_x = new_fj_x

                    kappa = mech_val
                    new_informed_list = [node for node in social_network.nodes()
                                         if node not in self.informed
                                         and random.random() < self.fj_x[node] ** kappa]

                assert len(self.informed) > 0, "Informed set is empty!"
                new_informed_list = set(new_informed_list)
                self.informed = self.informed.union(new_informed_list)
                for node in new_informed_list:
                    nx.set_node_attributes(contact_network, {node: {'Informed?': 'Informed'}})
                    nx.set_node_attributes(social_network, {node: {'Informed?': 'Informed'}})

        new_informed = self.informed - self.previous_informed
        self.previous_informed = self.informed.copy()

        # ---- Contact network changes ----
        P_prime, self.P, self.N = SIR.update_N_P(self.P, self.N, n)
        self.L = SIR.transition(self.L, P_prime)

        copy_state = deepcopy(self.state)
        state = self.state

        currently_infected = set([u for u in range(n) if state[u] == 1])
        trigger_nodes = currently_infected | set([u for u in new_informed if state[u] == 1])

        if mech_type == "FJ" and q is True and self.fj_x is not None:
            for (a, b) in [e for e, rt in self.fj_edge_restore_at.items() if t >= rt]:
                contact_network.add_edge(a, b)
                del self.fj_edge_restore_at[(a, b)]

        if q is not False:
            if mech_type == "FJ":
                if t > begin_q and self.fj_x is not None:
                    fj_x = self.fj_x
                    for (u, v) in list(contact_network.edges()):
                        if random.random() < 1.0 - math.exp(-(fj_x[u] + fj_x[v])):
                            contact_network.remove_edge(u, v)
                            e = (min(u, v), max(u, v))
                            if q == "r":
                                self.fj_removed_edges.add(e)
                            elif q is True:
                                period = self.fj_fixed_period if self.fj_fixed_period is not None \
                                    else abs(round(np.random.normal(loc=14, scale=2)))
                                self.fj_edge_restore_at[e] = t + period
            else:
                for u in trigger_nodes:
                    self.quarantine_statuses = SIR.quarantine_edge_removal(
                        contact_network, u, state, self.quarantine_statuses, self.already_quarantining)

        state = SIR.sirs_step(contact_network, state, self.L, self.beta, self.gamma, self.mu)
        self.state = state

        quarantine_statuses = self.quarantine_statuses
        d = self.d
        for u in range(n):
            is_informed = contact_network.nodes[u].get('Informed?') == 'Informed'

            if q is True and mech_type != "FJ":
                if is_informed and (1 <= quarantine_statuses[u] <= d[u]):
                    quarantine_statuses[u] += 1
                    if quarantine_statuses[u] >= d[u]:
                        quarantine_statuses[u] = 0
                        SIR.restore_edges(self.G_initial, contact_network, u,
                                          already_quarantining=self.already_quarantining)

            if q == "r" and state[u] == 2 and copy_state[u] != 2:
                quarantine_statuses[u] = 0
                if mech_type == "FJ":
                    for (a, b) in [e for e in self.fj_removed_edges if u in e]:
                        contact_network.add_edge(a, b)
                        self.fj_removed_edges.discard((a, b))
                else:
                    SIR.restore_edges(self.G_initial, contact_network, u,
                                      already_quarantining=self.already_quarantining)

        self.t = t + 1
        self._update_display_bookkeeping(copy_state, new_informed)

    def _update_display_bookkeeping(self, prev_state, new_informed):
        t = self.t
        self.new_infected = []
        for u in range(self.n):
            if self.state[u] != prev_state[u]:
                self.state_since[u] = t
                if self.state[u] == 1:
                    self.times_infected[u] += 1
                    self.new_infected.append(u)
            if self.quarantine_statuses[u] > 0:
                self.quarantine_since.setdefault(u, t)
            else:
                self.quarantine_since.pop(u, None)
        self.new_informed = sorted(int(u) for u in new_informed)
        for u in self.new_informed:
            self.informed_at.setdefault(u, t)
