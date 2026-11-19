# Graph Report - Social_Contact_Multiplex  (2026-11-18)

## Corpus Check
- 57 files · ~514,045 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 706 nodes · 1643 edges · 36 communities (30 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 76 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f050410f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- matplotlib_pyplot
- networkx
- browser_api.py
- server.py
- MultiplexScene
- drive_seed_selection.py
- scene.js
- cost_curve_store.py
- SeedPolicyRun
- serena
- numpy
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- adaptive_seed_selection.py
- Session
- _Strategy
- LineChart
- core.py
- test_engine_equivalence.py
- Correlate3.py
- networks.py
- pickle
- stepOnce
- visualize_adaptive.py
- os
- Workspace
- plot_correlation_ablation
- hf_space/README.md
- extract_mfa.py
- _seed_metrics
- _draw_comparison
- pandas

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
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `reset()` --uses--> `ScenarioConfig`  [INFERRED]
  app/server.py → app/core.py

## Import Cycles
- None detected.

## Communities (36 total, 6 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 2 - "networkx"
Cohesion: 0.05
Nodes (49): _cluster_layout(), init(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), load_contact_bins(), parse_matrices() (+41 more)

### Community 3 - "browser_api.py"
Cohesion: 0.29
Nodes (3): _error(), handle(), _json_default()

### Community 4 - "server.py"
Cohesion: 0.17
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (5): positionNodeCard(), hexToRgb(), ease(), MultiplexScene, MultiplexView

### Community 6 - "drive_seed_selection.py"
Cohesion: 0.19
Nodes (9): Dataset, _initialize_modules(), _measured_correlation(), _module_for(), _push(), run_correlation_experiment(), _run_cost_curves(), run_robustness_experiment() (+1 more)

### Community 7 - "scene.js"
Cohesion: 0.29
Nodes (7): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, LAYERS

### Community 8 - "cost_curve_store.py"
Cohesion: 0.13
Nodes (10): clear_experiment_label(), _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve() (+2 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (16): BaselineRuns, CostModel, edge_key(), _RngStream, SeedPolicyRun, _check_case(), _FixedBaselines, _reference() (+8 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 11 - "numpy"
Cohesion: 0.18
Nodes (12): _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate(), mse_loss() (+4 more)

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
Cohesion: 0.06
Nodes (31): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), given_at_time(), global_cost_function(), hill2(), initialize() (+23 more)

### Community 19 - "_Strategy"
Cohesion: 0.11
Nodes (5): DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "core.py"
Cohesion: 0.17
Nodes (8): _communities(), _fit_disc(), _grid_layout(), _normalized_layout(), options(), ScenarioConfig, _static_payload(), describe()

### Community 22 - "test_engine_equivalence.py"
Cohesion: 0.19
Nodes (14): MultiplexSIRS, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r(), test_ic_q_true() (+6 more)

### Community 23 - "Correlate3.py"
Cohesion: 0.13
Nodes (10): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping(), plot_five_conditions(), read_contact_time_zero(), read_social(), simulate_all_conditions() (+2 more)

### Community 24 - "networks.py"
Cohesion: 0.10
Nodes (16): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social() (+8 more)

### Community 25 - "pickle"
Cohesion: 0.23
Nodes (10): _aggregate(), delta_model(), _n_i_lookup(), _parities(), _plot_band(), plot_identifiability_results(), plot_model(), _series() (+2 more)

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 27 - "visualize_adaptive.py"
Cohesion: 0.21
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 28 - "os"
Cohesion: 0.22
Nodes (4): build(), main(), _parse_experiment_args(), truncate_files()

### Community 30 - "plot_correlation_ablation"
Cohesion: 0.18
Nodes (7): _cascade_label(), _lookup(), plot_correlation_ablation(), plot_robustness_heatmaps(), cost_grid(), resolve_methods(), _total_cost()

### Community 32 - "extract_mfa.py"
Cohesion: 0.25
Nodes (5): parse_sample_data(), align_true_to_est(), mean_std(), plot_k_est(), plot_sensitivity_results()

### Community 33 - "_seed_metrics"
Cohesion: 0.33
Nodes (3): _seed_metrics(), betweenness(), CoreOverBetweenness

### Community 37 - "pandas"
Cohesion: 0.09
Nodes (10): degree_correlation_over_time(), plot_degree_correlation(), read_contact(), read_social(), plot_new_infections(), read_contact(), read_social(), simulate_temporal_multiplex() (+2 more)

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 212 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `Session`, `networkx`, `core.py`, `test_engine_equivalence.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `SeedPolicyRun` to `networkx`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `networkx` be split into smaller, more focused modules?**
  _Cohesion score 0.052507836990595615 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `server.py`, `core.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `MultiplexScene` be split into smaller, more focused modules?**
  _Cohesion score 0.08865248226950355 - nodes in this community are weakly interconnected._