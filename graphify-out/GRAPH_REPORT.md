# Graph Report - Social_Contact_Multiplex  (2026-10-13)

## Corpus Check
- 44 files · ~58,031 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 486 nodes · 1077 edges · 16 communities (13 shown, 3 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 23 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7126b964`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- random
- test_seed_policies.py
- networkx
- MultiplexScene
- MILP Optimization Driver
- Adaptive Seed Selection
- Static Build & Deploy Scripts
- _Strategy
- serena
- Mean-Field Approximation
- CLAUDE.md
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
- `khop_social()` --calls--> `create_social_graph()`  [EXTRACTED]
  app/networks.py → correlated_graphs.py
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `Session` --uses--> `MultiplexSIRS`  [INFERRED]
  app/core.py → app/engine.py

## Import Cycles
- None detected.

## Communities (16 total, 3 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.05
Nodes (50): el(), LineChart, niceStep(), esc(), fmtPct(), mean(), metricCell(), NetworkIndex (+42 more)

### Community 1 - "numpy"
Cohesion: 0.06
Nodes (34): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), parse_matrices() (+26 more)

### Community 2 - "random"
Cohesion: 0.11
Nodes (22): create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target(), greedy_for_lt() (+14 more)

### Community 3 - "test_seed_policies.py"
Cohesion: 0.05
Nodes (26): MultiplexSIRS, BaselineRuns, CostModel, edge_key(), _RngStream, SeedPolicyRun, _check(), _run_pair() (+18 more)

### Community 4 - "networkx"
Cohesion: 0.05
Nodes (29): _error(), handle(), _json_default(), _network_key(), _normalized_layout(), options(), ScenarioConfig, _seed_metrics() (+21 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.14
Nodes (3): hexToRgb(), ease(), MultiplexScene

### Community 6 - "MILP Optimization Driver"
Cohesion: 0.11
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 7 - "Adaptive Seed Selection"
Cohesion: 0.15
Nodes (15): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_over_btw(), degree_based_selection(), given_at_time(), global_cost_function() (+7 more)

### Community 8 - "Static Build & Deploy Scripts"
Cohesion: 0.12
Nodes (6): build(), main(), Dataset, _draw_comparison(), _draw_network(), truncate_files()

### Community 9 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "Mean-Field Approximation"
Cohesion: 0.22
Nodes (13): drive_optimizer(), given_at_time(), loss(), loss_k_only(), optimize_k_identifiability(), optimize_segment(), predict_n_i_from_k(), predict_n_r_from_k() (+5 more)

### Community 13 - "Seed Metric Chart"
Cohesion: 0.38
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 148 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `test_seed_policies.py` to `random`, `networkx`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05213089802130898 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.0629399585921325 - nodes in this community are weakly interconnected._
- **Why does `HillClimb` connect `_Strategy` to `random`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `random` be split into smaller, more focused modules?**
  _Cohesion score 0.10512820512820513 - nodes in this community are weakly interconnected._