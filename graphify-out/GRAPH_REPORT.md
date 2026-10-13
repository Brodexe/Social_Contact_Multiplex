# Graph Report - Social_Contact_Multiplex  (2026-10-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 480 nodes · 1073 edges · 16 communities (13 shown, 3 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e29afbb8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Web UI Charts & Main
- Cost Curves & Plotting
- SIR Model & Network Generation
- Multiplex SIRS Engine & Tests
- App Server & Session API
- 3D Multiplex Scene
- MILP Optimization Driver
- Adaptive Seed Selection
- Static Build & Deploy Scripts
- Seed Selection Strategies
- Network Builders
- Mean-Field Approximation
- Baseline Runs & RNG
- Seed Metric Chart
- Project Config

## God Nodes (most connected - your core abstractions)
1. `MultiplexScene` - 31 edges
2. `SeedPolicyRun` - 18 edges
3. `LineChart` - 14 edges
4. `MultiplexSIRS` - 12 edges
5. `build()` - 12 edges
6. `Simulate_SIR()` - 12 edges
7. `restart()` - 11 edges
8. `create_social_graph()` - 11 edges
9. `stepOnce()` - 10 edges
10. `_check()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `build()` --calls--> `laplacian_smooth_beta()`  [EXTRACTED]
  app/networks.py → network_setup.py
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `Session` --uses--> `MultiplexSIRS`  [INFERRED]
  app/core.py → app/engine.py
- `_run_pair()` --calls--> `MultiplexSIRS`  [EXTRACTED]
  tests/test_engine_equivalence.py → app/engine.py

## Import Cycles
- None detected.

## Communities (16 total, 3 thin omitted)

### Community 0 - "Web UI Charts & Main"
Cohesion: 0.05
Nodes (49): el(), LineChart, niceStep(), esc(), fmtPct(), mean(), metricCell(), NetworkIndex (+41 more)

### Community 1 - "Cost Curves & Plotting"
Cohesion: 0.07
Nodes (31): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), compare_infections_adherence() (+23 more)

### Community 2 - "SIR Model & Network Generation"
Cohesion: 0.08
Nodes (30): khop_social(), betweenness(), CoreOverBetweenness, create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), parse_matrices() (+22 more)

### Community 3 - "Multiplex SIRS Engine & Tests"
Cohesion: 0.07
Nodes (24): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+16 more)

### Community 4 - "App Server & Session API"
Cohesion: 0.08
Nodes (16): _error(), handle(), _json_default(), _network_key(), _normalized_layout(), options(), ScenarioConfig, _seed_metrics() (+8 more)

### Community 5 - "3D Multiplex Scene"
Cohesion: 0.13
Nodes (4): positionNodeCard(), hexToRgb(), ease(), MultiplexScene

### Community 6 - "MILP Optimization Driver"
Cohesion: 0.11
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 7 - "Adaptive Seed Selection"
Cohesion: 0.15
Nodes (15): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_over_btw(), degree_based_selection(), given_at_time(), global_cost_function() (+7 more)

### Community 8 - "Static Build & Deploy Scripts"
Cohesion: 0.12
Nodes (6): build(), main(), Dataset, _draw_comparison(), _draw_network(), truncate_files()

### Community 9 - "Seed Selection Strategies"
Cohesion: 0.11
Nodes (5): DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "Network Builders"
Cohesion: 0.17
Nodes (9): build(), clustered_graph(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), NetworkMismatchError (+1 more)

### Community 11 - "Mean-Field Approximation"
Cohesion: 0.22
Nodes (13): drive_optimizer(), given_at_time(), loss(), loss_k_only(), optimize_k_identifiability(), optimize_segment(), predict_n_i_from_k(), predict_n_r_from_k() (+5 more)

### Community 13 - "Seed Metric Chart"
Cohesion: 0.38
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

## Knowledge Gaps
- **1 isolated node(s):** `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 143 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `Multiplex SIRS Engine & Tests` to `SIR Model & Network Generation`, `App Server & Session API`, `Baseline Runs & RNG`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `Social_Contact_Multiplex` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Web UI Charts & Main` be split into smaller, more focused modules?**
  _Cohesion score 0.0528169014084507 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `3D Multiplex Scene` to `Web UI Charts & Main`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `Cost Curves & Plotting` be split into smaller, more focused modules?**
  _Cohesion score 0.07093253968253968 - nodes in this community are weakly interconnected._
- **Why does `HillClimb` connect `Seed Selection Strategies` to `SIR Model & Network Generation`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `SIR Model & Network Generation` be split into smaller, more focused modules?**
  _Cohesion score 0.07662337662337662 - nodes in this community are weakly interconnected._