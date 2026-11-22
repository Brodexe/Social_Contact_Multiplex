# Graph Report - Social_Contact_Multiplex  (2026-11-22)

## Corpus Check
- 57 files · ~517,022 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 725 nodes · 1691 edges · 38 communities (31 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c9d8cb6f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- matplotlib_pyplot
- README.md
- sbm_graph
- numpy
- MultiplexScene
- visualize_adaptive.py
- scene.js
- drive_seed_selection.py
- SeedPolicyRun
- serena
- pickle
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- adaptive_seed_selection.py
- core.py
- seeding.py
- LineChart
- server.py
- os
- random
- networks.py
- _static_payload
- stepOnce
- extract_mfa.py
- Session
- Workspace
- milp.py
- hf_space/README.md
- Correlate2.py
- plot_joint_cost_elements
- _normalized_layout
- network_setup.py
- networkx
- Correlate3.py

## God Nodes (most connected - your core abstractions)
1. `MultiplexScene` - 28 edges
2. `SeedPolicyRun` - 25 edges
3. `MultiplexView` - 20 edges
4. `Simulate_SIR()` - 16 edges
5. `LineChart` - 15 edges
6. `restart()` - 14 edges
7. `_check()` - 14 edges
8. `MultiplexSIRS` - 12 edges
9. `refreshPanel()` - 12 edges
10. `_static_payload()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `test_cost_matches_research()` --calls--> `CostModel`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `build()` --calls--> `laplacian_smooth_beta()`  [EXTRACTED]
  app/networks.py → network_setup.py
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `_reference()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (38 total, 7 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 2 - "README.md"
Cohesion: 0.06
Nodes (42): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target() (+34 more)

### Community 4 - "numpy"
Cohesion: 0.17
Nodes (13): plot_five_conditions(), _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate() (+5 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "visualize_adaptive.py"
Cohesion: 0.19
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.06
Nodes (25): _cascade_label(), clear_experiment_label(), _expand_to_ticks(), _lighten(), load_all(), _lookup(), plot_correlation_ablation(), plot_robustness_heatmaps() (+17 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.06
Nodes (25): MultiplexSIRS, SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r() (+17 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 11 - "pickle"
Cohesion: 0.23
Nodes (10): _aggregate(), delta_model(), _n_i_lookup(), _parities(), _plot_band(), plot_identifiability_results(), plot_model(), _series() (+2 more)

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
Nodes (26): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), given_at_time() (+18 more)

### Community 18 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 19 - "seeding.py"
Cohesion: 0.05
Nodes (10): BaselineRuns, CoreOverBetweenness, CostModel, DegreeBased, edge_key(), HillClimb, Milp, RandomSeeds (+2 more)

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 22 - "os"
Cohesion: 0.14
Nodes (9): build(), main(), load_contact_bins(), plot_correlation_bars(), contact_network_path(), main(), run_adaptive(), run_milp() (+1 more)

### Community 23 - "random"
Cohesion: 0.18
Nodes (7): khop_social(), make_correlated_social(), partial_rank_mapping(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity()

### Community 24 - "networks.py"
Cohesion: 0.13
Nodes (13): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), NetworkMismatchError (+5 more)

### Community 25 - "_static_payload"
Cohesion: 0.20
Nodes (7): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), describe(), betweenness()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 27 - "extract_mfa.py"
Cohesion: 0.25
Nodes (5): parse_sample_data(), align_true_to_est(), mean_std(), plot_k_est(), plot_sensitivity_results()

### Community 30 - "milp.py"
Cohesion: 0.22
Nodes (7): baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function(), initialize(), milp_seed_selection_stepwise(), no_quarantine_baseline_runs()

### Community 32 - "Correlate2.py"
Cohesion: 0.33
Nodes (3): plot_new_infections(), simulate_temporal_multiplex(), sirs_step_temporal()

### Community 33 - "plot_joint_cost_elements"
Cohesion: 0.33
Nodes (3): _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements()

### Community 36 - "network_setup.py"
Cohesion: 0.39
Nodes (5): build_shared_network(), _current_params(), generate_global_betas(), laplacian_smooth_beta(), load_shared_network()

### Community 37 - "networkx"
Cohesion: 0.12
Nodes (9): degree_correlation_over_time(), plot_degree_correlation(), read_contact(), read_social(), read_contact(), read_social(), read_contact_time_zero(), parse() (+1 more)

### Community 40 - "Correlate3.py"
Cohesion: 0.21
Nodes (6): degree_preserving_rewire(), make_contact_layer_conditions(), read_social(), simulate_all_conditions(), simulate_one_condition(), sirs_step()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 220 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `core.py`, `seeding.py`, `Session`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.06201923076923077 - nodes in this community are weakly interconnected._
- **Should `MultiplexScene` be split into smaller, more focused modules?**
  _Cohesion score 0.09158186864014801 - nodes in this community are weakly interconnected._
- **Should `drive_seed_selection.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061683599419448475 - nodes in this community are weakly interconnected._