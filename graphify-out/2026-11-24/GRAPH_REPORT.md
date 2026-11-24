# Graph Report - Social_Contact_Multiplex  (2026-11-24)

## Corpus Check
- 57 files · ~517,212 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 727 nodes · 1709 edges · 42 communities (28 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b0bc7495`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- milp.py
- README.md
- networkx
- numpy
- MultiplexScene
- simulate_temporal_multiplex
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
- browser_api.py
- random
- LineChart
- server.py
- ScenarioConfig
- degree_correlation_over_time
- networks.py
- core.py
- stepOnce
- create_correlated_digraph
- Session
- Workspace
- os
- hf_space/README.md
- BaselineRuns
- cost_curve_store.py
- load_contact_bins
- CostModel
- load_all
- Correlate3.py
- test_engine_equivalence.py
- test_seed_policies.py
- MultiplexSIRS
- plot_joint_cost_elements

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
- `khop_social()` --calls--> `create_social_graph()`  [EXTRACTED]
  app/networks.py → correlated_graphs.py
- `build()` --calls--> `laplacian_smooth_beta()`  [EXTRACTED]
  app/networks.py → network_setup.py
- `_reference()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_cost_matches_research()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `_check_case()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (42 total, 14 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "milp.py"
Cohesion: 0.12
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 2 - "README.md"
Cohesion: 0.11
Nodes (25): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), drive_optimizer(), given_at_time() (+17 more)

### Community 3 - "networkx"
Cohesion: 0.18
Nodes (5): read_contact(), read_social(), read_contact(), read_social(), parse()

### Community 4 - "numpy"
Cohesion: 0.06
Nodes (54): plot_five_conditions(), plot_correlation_bars(), _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff() (+46 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.14
Nodes (10): _comparison_curves(), Dataset, _draw_comparison(), _initialize_modules(), _measured_correlation(), _module_for(), _push(), run_correlation_experiment() (+2 more)

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
Cohesion: 0.10
Nodes (27): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), given_at_time() (+19 more)

### Community 18 - "browser_api.py"
Cohesion: 0.29
Nodes (3): _error(), handle(), _json_default()

### Community 19 - "random"
Cohesion: 0.06
Nodes (28): CoreOverBetweenness, DegreeBased, edge_key(), HillClimb, Milp, RandomSeeds, _Strategy, create_social_graph() (+20 more)

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 24 - "networks.py"
Cohesion: 0.13
Nodes (14): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social() (+6 more)

### Community 25 - "core.py"
Cohesion: 0.16
Nodes (9): _cluster_layout(), _communities(), _fit_disc(), _grid_layout(), _normalized_layout(), _seed_metrics(), _static_payload(), describe() (+1 more)

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 30 - "os"
Cohesion: 0.16
Nodes (5): plot_degree_correlation(), plot_new_infections(), build(), main(), _parse_experiment_args()

### Community 33 - "cost_curve_store.py"
Cohesion: 0.18
Nodes (8): _cascade_label(), _lighten(), _lookup(), plot_correlation_ablation(), plot_robustness_heatmaps(), cost_grid(), resolve_methods(), _total_cost()

### Community 35 - "CostModel"
Cohesion: 0.21
Nodes (3): CostModel, _FixedBaselines, test_cost_matches_research()

### Community 36 - "load_all"
Cohesion: 0.15
Nodes (7): clear_experiment_label(), clear_labels(), _expand_to_ticks(), load_all(), push_curve(), push_experiment_curve(), push_experiment_meta()

### Community 37 - "Correlate3.py"
Cohesion: 0.14
Nodes (9): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping(), read_contact_time_zero(), read_social(), simulate_all_conditions(), simulate_one_condition() (+1 more)

### Community 38 - "test_engine_equivalence.py"
Cohesion: 0.26
Nodes (12): _check(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r(), test_ic_q_true(), test_lt_q_int(), test_misinfo_fj_takeover() (+4 more)

### Community 39 - "test_seed_policies.py"
Cohesion: 0.29
Nodes (9): _check_case(), _reference(), _setup(), test_degree_lt(), test_degree_no_spread(), test_hill_climb_accepts_non_worsening_swap(), test_milp_seed_term_shrinks_seed_set(), test_random_ic_per_tick() (+1 more)

### Community 41 - "plot_joint_cost_elements"
Cohesion: 0.33
Nodes (3): _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 220 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `BaselineRuns`, `test_seed_policies.py`, `MultiplexSIRS`, `random`, `core.py`, `Session`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `random`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `milp.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1206896551724138 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.10810810810810811 - nodes in this community are weakly interconnected._