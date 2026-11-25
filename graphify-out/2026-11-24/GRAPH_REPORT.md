# Graph Report - Social_Contact_Multiplex  (2026-11-24)

## Corpus Check
- 57 files · ~517,376 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 732 nodes · 1718 edges · 40 communities (32 shown, 8 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e94cac17`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- milp.py
- README.md
- pandas
- matplotlib_pyplot
- MultiplexScene
- numpy
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
- visualize_adaptive.py
- extract_mfa.py
- networks.py
- _static_payload
- stepOnce
- networkx
- Session
- plot_identifiability.py
- build
- hf_space/README.md
- BaselineRuns
- cost_curve_store.py
- plot_joint_cost_elements
- _normalized_layout
- pickle
- Correlate3.py
- os
- _draw_comparison

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
- `Session` --uses--> `MultiplexSIRS`  [INFERRED]
  app/core.py → app/engine.py

## Import Cycles
- None detected.

## Communities (40 total, 8 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "milp.py"
Cohesion: 0.12
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 2 - "README.md"
Cohesion: 0.06
Nodes (47): khop_social(), init(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), parse_matrices(), simplify_matrices(), write_matrices_to_file() (+39 more)

### Community 3 - "pandas"
Cohesion: 0.09
Nodes (10): degree_correlation_over_time(), plot_degree_correlation(), read_contact(), read_social(), plot_new_infections(), read_contact(), read_social(), simulate_temporal_multiplex() (+2 more)

### Community 4 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "numpy"
Cohesion: 0.18
Nodes (12): _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate(), mse_loss() (+4 more)

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.16
Nodes (10): _comparison_curves(), Dataset, _initialize_modules(), _measured_correlation(), _module_for(), _push(), run_correlation_experiment(), run_robustness_experiment() (+2 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (28): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+20 more)

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
Nodes (28): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), given_at_time() (+20 more)

### Community 18 - "core.py"
Cohesion: 0.19
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.10
Nodes (7): Workspace, index(), options(), remove(), reset(), _session(), step()

### Community 22 - "visualize_adaptive.py"
Cohesion: 0.21
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 23 - "extract_mfa.py"
Cohesion: 0.21
Nodes (6): parse_sample_data(), align_true_to_est(), mean_std(), plot_k_est(), plot_optimizer_results(), plot_sensitivity_results()

### Community 24 - "networks.py"
Cohesion: 0.23
Nodes (8): _bin_info(), _hs_bin_raw(), hs_info(), _hs_social_raw(), _rc_bin_raw(), rc_info(), _rc_social_raw(), rc_tie_type()

### Community 25 - "_static_payload"
Cohesion: 0.25
Nodes (6): _communities(), _grid_layout(), _seed_metrics(), _static_payload(), describe(), betweenness()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 27 - "networkx"
Cohesion: 0.25
Nodes (4): _cluster_layout(), create_correlated_digraph(), load_contact_bins(), parse()

### Community 29 - "plot_identifiability.py"
Cohesion: 0.30
Nodes (8): _aggregate(), delta_model(), _n_i_lookup(), _parities(), _plot_band(), plot_identifiability_results(), plot_model(), _series()

### Community 30 - "build"
Cohesion: 0.25
Nodes (5): build(), correlated_social(), er_graph(), NetworkMismatchError, _relabel()

### Community 33 - "cost_curve_store.py"
Cohesion: 0.17
Nodes (9): _cascade_label(), _condition_label(), _lighten(), _lookup(), plot_correlation_ablation(), plot_robustness_heatmaps(), cost_grid(), resolve_methods() (+1 more)

### Community 34 - "plot_joint_cost_elements"
Cohesion: 0.33
Nodes (3): _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements()

### Community 36 - "pickle"
Cohesion: 0.16
Nodes (8): clear_experiment_label(), clear_labels(), _expand_to_ticks(), load_all(), push_curve(), push_experiment_curve(), push_experiment_meta(), pickle_load()

### Community 37 - "Correlate3.py"
Cohesion: 0.13
Nodes (10): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping(), plot_five_conditions(), read_contact_time_zero(), read_social(), simulate_all_conditions() (+2 more)

### Community 38 - "os"
Cohesion: 0.23
Nodes (3): build(), main(), _parse_experiment_args()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 222 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `BaselineRuns`, `core.py`, `README.md`, `Session`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `README.md`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `milp.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1206896551724138 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `server.py` to `core.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.05647517039922103 - nodes in this community are weakly interconnected._