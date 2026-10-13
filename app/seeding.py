"""
Batch seed-selection strategies for the interactive viewer, run one tick at a time.

Ports the strategies of adaptive_seed_selection.py (hill-climb, degree-based,
coreness-over-betweenness, random) and milp.py (step-wise MILP). Those scripts
re-select seeds every `batch_interval` ticks and, for each batch, call
SIR.Simulate_SIR afresh with that batch's seeds and the previous state
(initial_state_dict). Each call starts from the pristine contact network (any
quarantine cuts lifted, minus the MILP's chosen removals), informs exactly the
new seeds, and restarts the N/P transmission-blocking process. SeedPolicyRun
does the same with one app.engine.MultiplexSIRS per batch (one per tick when
information spread is off), so with matching RNG draws it reproduces the
research loops; tests/test_seed_policies.py checks this against a Simulate_SIR
reference loop.

Deliberate differences from the research scripts:
  * Hill-climb keeps the swap it is testing and accepts it when the batch cost
    does not rise, as its comments describe. (adaptive_seed_selection.hill2
    overwrites the candidate at the top of every tick, so it never accepts a
    swap, and its initial seed set has a binomial, not exactly K, size.)
  * Edge-removal cost uses each tick's own live edges. (Simulate_SIR returns
    live EdgeViews of one graph, so every tick in a research batch reports the
    end-of-batch edges.)
  * No random infections are injected (introduced_infections is (0, 1) there).

Cost of a batch window (global_cost_function in both scripts), each term capped at 1:
  infections  newly infected in the window / g, g = sum over the window of the
              per-tick max newly infected across no-quarantine baseline runs
  edges       removed edge cost in the window / (window length x total edge cost)
  seeds       seed-set size / n
The user picks which terms count. Hill-climb accepts swaps and the MILP weights
its objective using exactly those terms; the other strategies only report cost.
"""

import random
from contextlib import contextmanager
from copy import deepcopy

import networkx as nx
import numpy as np

import SIR
from app.engine import MultiplexSIRS

ALGORITHMS = {
    "hill": "Hill-climb",
    "degree": "Degree-based",
    "cob": "Coreness / betweenness",
    "random": "Random",
    "milp": "MILP",
}
COST_TERMS = ("infections", "edges", "seeds")
HILL_EWMA_ALPHA = 0.5
COB_EPS = 1e-9
MILP_TIME_LIMIT = 20  # seconds per solve; the best feasible solution so far is used if hit


def edge_key(u, v):
    return (u, v) if u <= v else (v, u)


def betweenness(G):
    # Exact betweenness is O(nm); sample sources on dense graphs (e.g. strongly
    # anti-correlated social layers) so building stays interactive.
    if G.number_of_edges() > 6000:
        return nx.betweenness_centrality(G, k=min(64, G.number_of_nodes()), seed=0)
    return nx.betweenness_centrality(G)


class _RngStream:
    """A private random / np.random state, swapped in around code that draws from the
    global RNGs (SIR.sirs_step does), so it never shifts the main run's draws."""

    def __init__(self, seed):
        self.py_state = random.Random(seed).getstate()
        self.np_state = np.random.RandomState(seed).get_state()

    @contextmanager
    def active(self):
        saved = random.getstate(), np.random.get_state()
        random.setstate(self.py_state)
        np.random.set_state(self.np_state)
        try:
            yield
        finally:
            self.py_state, self.np_state = random.getstate(), np.random.get_state()
            random.setstate(saved[0])
            np.random.set_state(saved[1])


# ---------------------------------------------------------------- cost ---

class BaselineRuns:
    """No-quarantine reference runs (adaptive_seed_selection.baseline_infections), whose
    per-tick max newly infected normalizes the infection term. Each tick there is a
    one-step Simulate_SIR(q=False) call, i.e. a fresh N/P process and one sirs_step,
    done here directly since nothing else in that call touches the dynamics. The app
    has no fixed horizon, so runs are extended on demand."""

    def __init__(self, contact, beta, gamma, mu, init, runs, seed):
        self.G, self.beta, self.gamma, self.mu = contact, beta, gamma, mu
        self.n = contact.number_of_nodes()
        self.rng = _RngStream(seed)
        with self.rng.active():
            # make_initial_state
            self.states = [{u: (1 if random.random() < init else 0) for u in contact.nodes()}
                           for _ in range(runs)]
        self.max_new = []  # tick -> max over runs of newly infected

    def _extend(self, t_max):
        n = self.n
        with self.rng.active():
            while len(self.max_new) <= t_max:
                t = len(self.max_new)
                best = 0
                for r, prev in enumerate(self.states):
                    L = [0] * (n - 1) + [1]
                    P_prime, _, _ = SIR.update_N_P(1, n - 1, n)
                    L = SIR.transition(L, P_prime)
                    state = SIR.sirs_step(self.G, prev, L, self.beta, self.gamma, self.mu)
                    self.states[r] = state
                    new = sum(1 for u in state if state[u] == 1 and (t == 0 or prev[u] != 1))
                    best = max(best, new)
                self.max_new.append(best)

    def g(self, t0, t1):
        """Sum over ticks t0..t1 of the max newly infected across runs."""
        self._extend(t1)
        return sum(self.max_new[t0:t1 + 1])


class CostModel:
    def __init__(self, contact, terms, batch_interval, baselines):
        self.terms = tuple(terms)
        self.batch_interval = batch_interval
        self.baselines = baselines
        self.n = contact.number_of_nodes()
        self.edge_weight = {edge_key(u, v): d.get("weight", 1) for u, v, d in contact.edges(data=True)}
        self.edge_cost_bound = sum(self.edge_weight.values())  # every edge lost in one tick

    def removed_cost(self, live):
        """Cost of the contact edges missing from `live` (a set of edge_key tuples)."""
        return sum(w for e, w in self.edge_weight.items() if e not in live)

    def window_start(self, t_cur):
        # With per-tick reselection there is no batch to window against: use all history
        return 0 if self.batch_interval == 1 else (t_cur // self.batch_interval) * self.batch_interval

    def weights(self, t0, t1):
        """(alpha_w, beta_w) normalizing the infection and edge terms over ticks t0..t1."""
        g = self.baselines.g(t0, t1)
        h = (t1 - t0 + 1) * self.edge_cost_bound
        return (1 / g if g > 0 else 1.0), (1 / h if h > 0 else 1.0)

    def evaluate(self, t_cur, newly_infected, removed_costs, seed_count):
        """Cost of the window ending at tick t_cur; newly_infected and removed_costs are per tick."""
        ws = self.window_start(t_cur)
        infected = sum(newly_infected[ws:t_cur + 1])
        removed = sum(removed_costs[ws:t_cur + 1])
        alpha_w, beta_w = self.weights(ws, t_cur)
        terms = {
            "infections": min(alpha_w * infected, 1.0),
            "edges": min(beta_w * removed, 1.0),
            "seeds": min(seed_count / self.n, 1.0) if self.n else 0.0,
        }
        return {
            "cost": sum(terms[k] for k in self.terms),
            "terms": terms,
            "raw": {"infections": int(infected), "edges": float(removed), "seeds": int(seed_count)},
        }


# ----------------------------------------------------------- strategies ---
# select(run) -> (seeds, removed_edges) at each batch start; observe(cost) at each batch end.

class _Strategy:
    def __init__(self, run):
        self.run = run

    def observe(self, cost):
        pass

    def _current_graph(self):
        """The contact network as of the last tick (initial network before any)."""
        run = self.run
        G = nx.Graph()
        G.add_nodes_from(run.G0.nodes())
        for u, v, data in run.G0.edges(data=True):
            if run.live_edges is None or edge_key(u, v) in run.live_edges:
                G.add_edge(u, v, **data)
        return G


class RandomSeeds(_Strategy):
    def select(self, run):
        return random.sample(list(run.G0.nodes()), run.k), set()


class DegreeBased(_Strategy):
    """Top K by degree in the current (quarantine-pruned) contact network."""

    def select(self, run):
        degree = dict(self._current_graph().degree())
        return sorted(degree, key=lambda u: degree[u], reverse=True)[:run.k], set()


class CoreOverBetweenness(_Strategy):
    """Top K by (coreness / max coreness) / (betweenness / max betweenness) in the
    current contact network; COB_EPS keeps zero-betweenness nodes finite."""

    def select(self, run):
        G = self._current_graph()
        G.remove_edges_from(list(nx.selfloop_edges(G)))
        core = nx.core_number(G)
        btw = betweenness(G)
        max_core = max(core.values()) or 1
        max_btw = max(btw.values()) or 1
        score = {u: (core[u] / max_core) / (btw[u] / max_btw + COB_EPS) for u in G.nodes()}
        return sorted(score, key=lambda u: score[u], reverse=True)[:run.k], set()


class HillClimb(_Strategy):
    """Stochastic hill-climb (adaptive_seed_selection.hill2): each batch tests the
    accepted seed set with one swap, keeping it if the batch cost did not rise."""

    def __init__(self, run):
        super().__init__(run)
        self.nodes = list(run.G0.nodes())
        self.utilities = {u: random.uniform(0, 1) for u in self.nodes}
        self.accepted = set(random.sample(self.nodes, run.k))
        self.candidate = set(self.accepted)
        self.last_cost = None

    def select(self, run):
        return sorted(self.candidate), set()

    def observe(self, cost):
        cost = cost["cost"]
        delta = (self.last_cost - cost) if self.last_cost is not None else 0.0
        for u in self.nodes:
            self.utilities[u] = HILL_EWMA_ALPHA * delta + (1 - HILL_EWMA_ALPHA) * self.utilities[u]
        if self.last_cost is not None and cost <= self.last_cost:
            self.accepted = self.candidate
        self.candidate = self._propose()
        self.last_cost = cost

    def _propose(self):
        """One swap: add a random non-seed (dropping a seed chosen by softmax of -utility)
        or drop a random seed (adding a random non-seed), whichever the first node in a
        shuffled order calls for."""
        order = list(self.nodes)
        random.shuffle(order)
        S = self.accepted
        candidate = set(S)
        for u in order:
            if u not in S:
                active = [j for j in self.nodes if j in S]
                if not active:
                    continue
                weights = np.array([np.exp(-self.utilities[j]) for j in active])
                drop = active[np.random.choice(len(active), p=weights / weights.sum())]
                candidate.discard(drop)
                candidate.add(u)
                break
            non_seeds = [j for j in self.nodes if j not in S]
            if not non_seeds:
                continue
            candidate.discard(u)
            candidate.add(random.choice(non_seeds))
            break
        return candidate


class Milp(_Strategy):
    """milp.milp_seed_selection_stepwise: each batch, jointly choose seeds x_v and live
    edges y_e minimizing  seeds: gamma_w * sum x  +  edges: beta_w * sum w_e (1 - y_e)
    +  infections: alpha_w * sum z_e, where z_e = y_e (1 - x_u)(1 - x_v) (edge live with
    no seeded endpoint) proxies exposure, subject to sum x <= K. alpha_w and beta_w
    normalize over the window the batch will cover, as the cost function does."""

    def __init__(self, run):
        super().__init__(run)
        from scipy.optimize import Bounds, LinearConstraint
        from scipy.sparse import csr_matrix, lil_matrix

        G = run.G0
        self.nodes = list(G.nodes())
        self.edges = list(G.edges())
        N, E = len(self.nodes), len(self.edges)
        idx = {v: i for i, v in enumerate(self.nodes)}
        self.N, self.E = N, E
        self.edge_weights = np.array([G[u][v].get("weight", 1) for u, v in self.edges], dtype=float)

        # Variables [x_0..x_{N-1}, y_0..y_{E-1}, z_0..z_{E-1}]; z_e linearized by 4 rows per edge
        n_vars, n_con = N + 2 * E, 1 + 4 * E
        A = lil_matrix((n_con, n_vars))
        lb = np.full(n_con, -np.inf)
        ub = np.full(n_con, np.inf)
        A[0, :N] = 1.0
        ub[0] = run.k
        for i, (u, v) in enumerate(self.edges):
            ui, vi, yi, zi, r = idx[u], idx[v], N + i, N + E + i, 1 + 4 * i
            A[r, zi] = 1; A[r, ui] = 1; ub[r] = 1                                       # z <= 1 - x_u
            A[r + 1, zi] = 1; A[r + 1, vi] = 1; ub[r + 1] = 1                           # z <= 1 - x_v
            A[r + 2, zi] = 1; A[r + 2, yi] = -1; ub[r + 2] = 0                          # z <= y
            A[r + 3, zi] = 1; A[r + 3, yi] = -1; A[r + 3, ui] = 1; A[r + 3, vi] = 1; lb[r + 3] = 0  # z >= y - x_u - x_v
        self.constraints = [LinearConstraint(csr_matrix(A), lb, ub)]
        self.bounds = Bounds(lb=np.zeros(n_vars), ub=np.ones(n_vars))
        self.integrality = np.ones(n_vars)

    def select(self, run):
        from scipy.optimize import milp

        t, bi = run.t, run.batch_interval
        t0, t1 = (0, t) if bi == 1 else (t, t + bi - 1)
        alpha_w, beta_w = run.cost_model.weights(t0, t1)
        terms = run.cost_model.terms
        N, E = self.N, self.E
        c = np.zeros(N + 2 * E)
        if "seeds" in terms:
            c[:N] = 1.0 / N
        if "edges" in terms:
            c[N:N + E] = -beta_w * self.edge_weights
        if "infections" in terms:
            c[N + E:] = alpha_w

        res = milp(c=c, bounds=self.bounds, constraints=self.constraints,
                   integrality=self.integrality, options={"time_limit": MILP_TIME_LIMIT})
        if res.x is None:
            return [], set()
        x = np.round(res.x[:N]).astype(int)
        y = np.round(res.x[N:N + E]).astype(int)
        return ([self.nodes[i] for i in range(N) if x[i] == 1],
                {self.edges[i] for i in range(E) if y[i] == 0})


STRATEGIES = {"hill": HillClimb, "degree": DegreeBased, "cob": CoreOverBetweenness,
              "random": RandomSeeds, "milp": Milp}


# ------------------------------------------------------------------ run ---

class SeedPolicyRun:
    """Drop-in for MultiplexSIRS in app.core.Session: same step() and the attributes
    Session.snapshot() reads, with seeds chosen by a strategy every batch."""

    def __init__(self, contact_network, social_network, beta, gamma, mu, init,
                 q=False, q_mech=("ic", 0.02), adherence=None, mc=1000,
                 algorithm="degree", k=None, batch_interval=2, info_spread=True,
                 cost_terms=("infections", "edges"), baseline_runs=10, baseline_seed=None,
                 initial_state_dict=None):
        n = contact_network.number_of_nodes()
        self.n = n
        self.G0 = contact_network
        self.social0 = social_network
        self.beta, self.gamma, self.mu, self.init = beta, gamma, mu, init
        self.q, self.q_mech, self.mc = q, q_mech, mc
        self.algorithm = algorithm
        self.k = int(0.75 * n) if k is None else int(k)
        if not 0 <= self.k <= n:
            raise ValueError(f"Seeds per batch K must be between 0 and the network's {n} nodes")
        self.batch_interval = int(batch_interval)
        self.info_spread = info_spread

        # Same draws, in the same order, as MultiplexSIRS: adherence, then initial infections
        if isinstance(adherence, float) and 0 <= adherence <= 1:
            self.adhering = set(np.random.choice(list(contact_network.nodes()),
                                                 size=int(adherence * n), replace=False))
        elif isinstance(adherence, set):
            self.adhering = set(adherence)
        else:
            self.adhering = set()
        if initial_state_dict is not None:
            state = dict(initial_state_dict)
        else:
            state = {u: np.random.choice(a=[1, 0], size=1, p=[init, 1 - init])[0] for u in range(n)}
        self.state = {u: int(s) for u, s in state.items()}

        baselines = BaselineRuns(contact_network, beta, gamma, mu, init, baseline_runs, baseline_seed)
        self.cost_model = CostModel(contact_network, cost_terms, self.batch_interval, baselines)

        self.t = 0
        self.sim = None            # MultiplexSIRS for the current batch (or tick)
        self.live_edges = None     # edge_key set after the last tick
        self.newly_infected = []   # per tick, as adaptive_seed_selection.given_at_time counts it
        self.removed_costs = []    # per tick
        self.costs = []            # one per completed batch
        self.batch = 0             # index of the batch being shown (1-based once running)
        self.seeds = []            # seeds of the batch being shown (before t=1: the first batch's)
        self.removed = set()       # MILP edge removals of that batch
        self.new_batch = False     # a batch started on the last step
        self.new_cost = None       # cost evaluated on the last step

        # Display-only bookkeeping, carried across the per-batch simulations
        self.state_since = {u: 0 for u in range(n)}
        self.times_infected = {u: int(self.state[u] == 1) for u in range(n)}
        self.informed_at = {}
        self.quarantine_since = {}
        self.new_infected = []
        self.new_informed = []
        self._prev_informed = set()

        self.strategy = STRATEGIES[algorithm](self)
        self._pending = self.strategy.select(self)
        self.seeds = sorted(int(u) for u in self._pending[0])

    # Attributes Session.snapshot() reads from the live simulation
    @property
    def informed(self):
        return self.sim.informed if self.sim is not None else set()

    @property
    def contact(self):
        return self.sim.contact if self.sim is not None else self.G0

    @property
    def d(self):
        return self.sim.d if self.sim is not None else None

    @property
    def fj_x(self):
        if self.sim is not None:
            return self.sim.fj_x
        return {u: 0.0 for u in range(self.n)} if self.q_mech[0] == "FJ" else None

    def step(self):
        t, bi = self.t, self.batch_interval
        self.new_batch = t % bi == 0
        if self.new_batch:
            seeds, self.removed = self._pending
            self.seeds = sorted(int(u) for u in seeds)
            self.batch += 1
        if self.new_batch or not self.info_spread:
            contact = deepcopy(self.G0)
            contact.remove_edges_from(self.removed)
            self.sim = MultiplexSIRS(
                contact, deepcopy(self.social0), beta=self.beta, gamma=self.gamma, mu=self.mu,
                init=self.init, q=self.q, q_mech=self.q_mech, adherence=set(self.adhering),
                begin_q=0, seeds=list(self.seeds), initial_state_dict=self.state,
                T=bi if self.info_spread else 0, mc=self.mc)

        prev = self.state
        self.sim.step()
        self.state = {u: int(s) for u, s in self.sim.state.items()}
        self.t = t + 1

        self.newly_infected.append(sum(1 for u in range(self.n)
                                       if self.state[u] == 1 and (t == 0 or prev[u] != 1)))
        self.live_edges = {edge_key(u, v) for u, v in self.sim.contact.edges()}
        self.removed_costs.append(self.cost_model.removed_cost(self.live_edges))
        self._update_display_bookkeeping(prev)

        self.new_cost = None
        if self.t % bi == 0:
            cost = self.cost_model.evaluate(t, self.newly_infected, self.removed_costs, len(self.seeds))
            cost["t"] = self.t
            self.costs.append(cost)
            self.new_cost = cost
            self.strategy.observe(cost)
            self._pending = self.strategy.select(self)

    def _update_display_bookkeeping(self, prev):
        t = self.t
        self.new_infected = []
        statuses = self.sim.quarantine_statuses
        for u in range(self.n):
            if self.state[u] != prev[u]:
                self.state_since[u] = t
                if self.state[u] == 1:
                    self.times_infected[u] += 1
                    self.new_infected.append(u)
            if statuses[u] > 0:
                self.quarantine_since.setdefault(u, t)
            else:
                self.quarantine_since.pop(u, None)
        informed = set(int(u) for u in self.sim.informed)
        self.new_informed = sorted(informed - self._prev_informed)
        self._prev_informed = informed
        self.informed_at = {u: self.informed_at.get(u, t) for u in informed}

    def static_info(self):
        return {
            "algorithm": self.algorithm,
            "label": ALGORITHMS[self.algorithm],
            "k": self.k,
            "batch_interval": self.batch_interval,
            "info_spread": self.info_spread,
            "terms": list(self.cost_model.terms),
        }

    def snapshot_info(self):
        return {
            "batch": self.batch,
            "new_batch": self.new_batch,
            "cost": self.new_cost,
            "milp_removed": len(self.removed),
        }
