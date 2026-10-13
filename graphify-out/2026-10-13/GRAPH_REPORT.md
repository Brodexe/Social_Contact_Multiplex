# Graph Report - Social_Contact_Multiplex  (2026-10-13)

## Corpus Check
- 44 files · ~63,221 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 568 nodes · 1304 edges · 32 communities (22 shown, 10 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `01d86bb8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- networkx
- test_seed_policies.py
- server.py
- MultiplexScene
- milp.py
- Adaptive Seed Selection
- drive_seed_selection.py
- _Strategy
- serena
- networks.py
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- core.py
- CostModel
- SeedPolicyRun
- LineChart
- _static_payload
- Session
- BaselineRuns
- test_engine_equivalence.py
- Workspace
- stepOnce
- MultiplexSIRS
- _RngStream
- NetworkIndex
- _normalized_layout
- hf_space/README.md

## God Nodes (most connected - your core abstractions)
1. `MultiplexScene` - 27 edges
2. `SeedPolicyRun` - 22 edges
3. `MultiplexView` - 20 edges
4. `LineChart` - 14 edges
5. `restart()` - 14 edges
6. `Simulate_SIR()` - 12 edges
7. `_static_payload()` - 12 edges
8. `MultiplexSIRS` - 12 edges
9. `create_social_graph()` - 12 edges
10. `refreshPanel()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `khop_social()` --calls--> `create_social_graph()`  [EXTRACTED]
  app/networks.py → correlated_graphs.py
- `build()` --calls--> `laplacian_smooth_beta()`  [EXTRACTED]
  app/networks.py → network_setup.py
- `_reference()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `_check_case()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_hill_climb_accepts_non_worsening_swap()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (32 total, 10 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.09
Nodes (25): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, COST_HINTS, COST_SERIES, esc() (+17 more)

### Community 1 - "numpy"
Cohesion: 0.07
Nodes (31): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), compare_infections_adherence() (+23 more)

### Community 2 - "networkx"
Cohesion: 0.07
Nodes (42): init(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), parse_matrices(), simplify_matrices(), write_matrices_to_file() (+34 more)

### Community 3 - "test_seed_policies.py"
Cohesion: 0.29
Nodes (9): _check_case(), _reference(), _setup(), test_degree_lt(), test_degree_no_spread(), test_hill_climb_accepts_non_worsening_swap(), test_milp_seed_term_shrinks_seed_set(), test_random_ic_per_tick() (+1 more)

### Community 4 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "milp.py"
Cohesion: 0.11
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 7 - "Adaptive Seed Selection"
Cohesion: 0.15
Nodes (15): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_over_btw(), degree_based_selection(), given_at_time(), global_cost_function() (+7 more)

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.12
Nodes (6): build(), main(), Dataset, _draw_comparison(), _draw_network(), truncate_files()

### Community 9 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "networks.py"
Cohesion: 0.10
Nodes (17): _bin_info(), build(), correlated_social(), describe(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw() (+9 more)

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "inspector.js"
Cohesion: 0.15
Nodes (18): esc(), fmtPct(), mean(), metricCell(), quarantineText(), renderGroupCard(), renderNodeCard(), tieTable() (+10 more)

### Community 16 - "restart"
Cohesion: 0.27
Nodes (17): activeSlot(), addSlot(), call(), clearSelection(), fillForm(), handleClick(), httpCall(), refreshPanel() (+9 more)

### Community 17 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 18 - "CostModel"
Cohesion: 0.20
Nodes (4): CostModel, edge_key(), _FixedBaselines, test_cost_matches_research()

### Community 20 - "LineChart"
Cohesion: 0.32
Nodes (3): el(), LineChart, niceStep()

### Community 21 - "_static_payload"
Cohesion: 0.22
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), betweenness()

### Community 24 - "test_engine_equivalence.py"
Cohesion: 0.36
Nodes (8): _check(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r(), test_ic_q_true(), test_lt_q_int(), test_single_tick()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 29 - "NetworkIndex"
Cohesion: 0.40
Nodes (4): NetworkIndex, compact(), newSlotState(), recordSnapshot()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 168 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `networkx`, `test_seed_policies.py`, `core.py`, `Session`, `MultiplexSIRS`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08620689655172414 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `networkx`, `SeedPolicyRun`, `_RngStream`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.07093253968253968 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `inspector.js`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `networkx` be split into smaller, more focused modules?**
  _Cohesion score 0.06516105146242132 - nodes in this community are weakly interconnected._