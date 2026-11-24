# Graph Report - Social_Contact_Multiplex  (2026-11-24)

## Corpus Check
- 57 files · ~517,959 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 730 nodes · 1714 edges · 33 communities (24 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a62c83e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- random
- README.md
- networkx
- numpy
- MultiplexScene
- Correlate2.py
- scene.js
- drive_seed_selection.py
- SeedPolicyRun
- serena
- sbm_graph
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- adaptive_seed_selection.py
- core.py
- _Strategy
- LineChart
- server.py
- _normalized_layout
- networks.py
- _static_payload
- stepOnce
- Session
- Workspace
- sys
- hf_space/README.md
- BaselineRuns
- Correlate3.py

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
- `_reference()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `_check_case()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_hill_climb_accepts_non_worsening_swap()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_milp_seed_term_shrinks_seed_set()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (33 total, 9 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "random"
Cohesion: 0.06
Nodes (36): khop_social(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+28 more)

### Community 2 - "README.md"
Cohesion: 0.09
Nodes (32): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target() (+24 more)

### Community 3 - "networkx"
Cohesion: 0.19
Nodes (6): degree_correlation_over_time(), read_contact(), read_social(), create_correlated_digraph(), load_contact_bins(), parse()

### Community 4 - "numpy"
Cohesion: 0.06
Nodes (54): plot_five_conditions(), plot_correlation_bars(), _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff() (+46 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "Correlate2.py"
Cohesion: 0.25
Nodes (4): read_contact(), read_social(), simulate_temporal_multiplex(), sirs_step_temporal()

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.05
Nodes (31): run_methods(), plot_degree_correlation(), plot_new_infections(), _cascade_label(), clear_experiment_label(), clear_labels(), _expand_to_ticks(), _lighten() (+23 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.06
Nodes (19): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+11 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "inspector.js"
Cohesion: 0.26
Nodes (11): esc(), fmtPct(), mean(), metricCell(), NetworkIndex, quarantineText(), renderGroupCard(), renderNodeCard() (+3 more)

### Community 16 - "restart"
Cohesion: 0.27
Nodes (17): activeSlot(), addSlot(), call(), clearSelection(), fillForm(), handleClick(), httpCall(), refreshPanel() (+9 more)

### Community 17 - "adaptive_seed_selection.py"
Cohesion: 0.09
Nodes (27): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), given_at_time() (+19 more)

### Community 18 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.15
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 24 - "networks.py"
Cohesion: 0.13
Nodes (14): _bin_info(), build(), correlated_social(), describe(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw() (+6 more)

### Community 25 - "_static_payload"
Cohesion: 0.22
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), betweenness()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 30 - "sys"
Cohesion: 0.17
Nodes (7): build(), main(), _parse_experiment_args(), contact_network_path(), main(), run_adaptive(), run_milp()

### Community 37 - "Correlate3.py"
Cohesion: 0.14
Nodes (9): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping(), read_contact_time_zero(), read_social(), simulate_all_conditions(), simulate_one_condition() (+1 more)

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 222 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `random`, `core.py`, `README.md`, `Session`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `random`, `SeedPolicyRun`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `random` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.08599033816425121 - nodes in this community are weakly interconnected._