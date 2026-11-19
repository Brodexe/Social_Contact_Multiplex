# Graph Report - Social_Contact_Multiplex  (2026-11-18)

## Corpus Check
- 57 files · ~515,258 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 714 nodes · 1671 edges · 34 communities (26 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 80 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f050410f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- README.md
- core.py
- server.py
- MultiplexScene
- adaptive_seed_selection.py
- scene.js
- cost_curve_store.py
- SeedPolicyRun
- serena
- find_seeds.py
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- milp.py
- Session
- _Strategy
- LineChart
- _static_payload
- SIR.py
- partial_rank_mapping
- networks.py
- simulate_all_conditions
- stepOnce
- simulate_temporal_multiplex
- Workspace
- random
- hf_space/README.md
- BaselineRuns
- networkx
- _normalized_layout

## God Nodes (most connected - your core abstractions)
1. `MultiplexScene` - 28 edges
2. `SeedPolicyRun` - 25 edges
3. `MultiplexView` - 20 edges
4. `Simulate_SIR()` - 16 edges
5. `LineChart` - 15 edges
6. `restart()` - 14 edges
7. `_check()` - 14 edges
8. `_static_payload()` - 12 edges
9. `MultiplexSIRS` - 12 edges
10. `refreshPanel()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `build()` --calls--> `laplacian_smooth_beta()`  [EXTRACTED]
  app/networks.py → network_setup.py
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `reset()` --uses--> `ScenarioConfig`  [INFERRED]
  app/server.py → app/core.py
- `_static_payload()` --calls--> `describe()`  [EXTRACTED]
  app/core.py → app/networks.py

## Import Cycles
- None detected.

## Communities (34 total, 8 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "numpy"
Cohesion: 0.06
Nodes (50): degree_correlation_over_time(), plot_degree_correlation(), plot_new_infections(), plot_five_conditions(), load_contact_bins(), plot_correlation_bars(), _draw_network(), analyze_file() (+42 more)

### Community 2 - "README.md"
Cohesion: 0.07
Nodes (33): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), greedy_for_ic(), greedy_for_ic_target(), greedy_for_lt(), IC() (+25 more)

### Community 3 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 4 - "server.py"
Cohesion: 0.15
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (5): positionNodeCard(), hexToRgb(), ease(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.07
Nodes (33): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_alone(), _core_alone_score(), core_over_btw(), _core_over_btw_score() (+25 more)

### Community 7 - "scene.js"
Cohesion: 0.29
Nodes (7): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, LAYERS

### Community 8 - "cost_curve_store.py"
Cohesion: 0.07
Nodes (21): _cascade_label(), clear_experiment_label(), _expand_to_ticks(), _lighten(), load_all(), _lookup(), _normalize_entry(), plot_correlation_ablation() (+13 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (28): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+20 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 11 - "find_seeds.py"
Cohesion: 0.39
Nodes (6): find_seed_set(), initialize_social_IM(), adherence_mode(), sensitivity_analysis(), simple_repeat(), yjmob_mode()

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "inspector.js"
Cohesion: 0.26
Nodes (11): esc(), fmtPct(), mean(), metricCell(), NetworkIndex, quarantineText(), renderGroupCard(), renderNodeCard() (+3 more)

### Community 16 - "restart"
Cohesion: 0.27
Nodes (17): activeSlot(), addSlot(), call(), clearSelection(), fillForm(), handleClick(), httpCall(), refreshPanel() (+9 more)

### Community 17 - "milp.py"
Cohesion: 0.12
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "_static_payload"
Cohesion: 0.22
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), betweenness()

### Community 22 - "SIR.py"
Cohesion: 0.17
Nodes (11): break_quarantine(), competing_spread_step(), fj_belief_update(), misinfo_seed_set(), quarantine_edge_removal(), restore_edges(), set_info_label(), Simulate_SIR() (+3 more)

### Community 23 - "partial_rank_mapping"
Cohesion: 0.25
Nodes (4): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping()

### Community 24 - "networks.py"
Cohesion: 0.10
Nodes (16): _bin_info(), build(), correlated_social(), describe(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw() (+8 more)

### Community 25 - "simulate_all_conditions"
Cohesion: 0.33
Nodes (3): simulate_all_conditions(), simulate_one_condition(), sirs_step()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 30 - "random"
Cohesion: 0.20
Nodes (5): khop_social(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity()

### Community 37 - "networkx"
Cohesion: 0.17
Nodes (7): read_contact(), read_social(), read_contact(), read_social(), read_contact_time_zero(), read_social(), parse()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 212 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `BaselineRuns`, `Session`, `core.py`, `random`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `random`, `adaptive_seed_selection.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.05822784810126582 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.07294117647058823 - nodes in this community are weakly interconnected._