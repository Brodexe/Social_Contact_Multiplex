# Graph Report - Social_Contact_Multiplex  (2026-11-15)

## Corpus Check
- 53 files · ~508,080 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 632 nodes · 1482 edges · 36 communities (29 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 80 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f7a14a7e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- matplotlib_pyplot
- SIR.py
- core.py
- server.py
- MultiplexScene
- adaptive_seed_selection.py
- scene.js
- test_engine_equivalence.py
- SeedPolicyRun
- serena
- networks.py
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
- Workspace
- _normalized_layout
- networkx
- cost_curve_store.py
- stepOnce
- README.md
- numpy
- mean_field_approx.py
- visualize_adaptive.py
- hf_space/README.md
- extract_mfa.py
- find_seeds.py
- pickle

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

## Communities (36 total, 7 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 2 - "SIR.py"
Cohesion: 0.13
Nodes (11): break_quarantine(), competing_spread_step(), fj_belief_update(), misinfo_seed_set(), quarantine_edge_removal(), restore_edges(), set_info_label(), Simulate_SIR() (+3 more)

### Community 3 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 4 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (3): hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.10
Nodes (27): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_alone(), _core_alone_score(), core_over_btw(), _core_over_btw_score() (+19 more)

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "test_engine_equivalence.py"
Cohesion: 0.09
Nodes (17): build(), main(), Dataset, _draw_comparison(), truncate_files(), _check(), test_fj_q_r(), test_fj_q_true() (+9 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (18): MultiplexSIRS, BaselineRuns, CostModel, edge_key(), _RngStream, SeedPolicyRun, _run_pair(), _check_case() (+10 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 11 - "networks.py"
Cohesion: 0.10
Nodes (16): _bin_info(), build(), correlated_social(), describe(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw() (+8 more)

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "inspector.js"
Cohesion: 0.24
Nodes (12): esc(), fmtPct(), mean(), metricCell(), NetworkIndex, quarantineText(), renderGroupCard(), renderNodeCard() (+4 more)

### Community 16 - "restart"
Cohesion: 0.27
Nodes (17): activeSlot(), addSlot(), call(), clearSelection(), fillForm(), handleClick(), httpCall(), refreshPanel() (+9 more)

### Community 17 - "milp.py"
Cohesion: 0.22
Nodes (7): baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function(), initialize(), milp_seed_selection_stepwise(), no_quarantine_baseline_runs()

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "_static_payload"
Cohesion: 0.22
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), betweenness()

### Community 24 - "networkx"
Cohesion: 0.19
Nodes (11): khop_social(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), build_shared_network(), _current_params(), generate_global_betas() (+3 more)

### Community 25 - "cost_curve_store.py"
Cohesion: 0.15
Nodes (8): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), _draw_network()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 27 - "README.md"
Cohesion: 0.18
Nodes (11): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), greedy_for_ic(), greedy_for_ic_target(), greedy_for_lt(), IC() (+3 more)

### Community 28 - "numpy"
Cohesion: 0.22
Nodes (11): analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate(), mse_loss(), mse_slice() (+3 more)

### Community 29 - "mean_field_approx.py"
Cohesion: 0.24
Nodes (14): drive_optimizer(), given_at_time(), loss(), loss_k_only(), optimize_k_identifiability(), optimize_segment(), predict_n_i_from_k(), predict_n_r_from_k() (+6 more)

### Community 30 - "visualize_adaptive.py"
Cohesion: 0.21
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 32 - "extract_mfa.py"
Cohesion: 0.25
Nodes (5): parse_sample_data(), align_true_to_est(), mean_std(), plot_k_est(), plot_sensitivity_results()

### Community 33 - "find_seeds.py"
Cohesion: 0.39
Nodes (6): find_seed_set(), initialize_social_IM(), adherence_mode(), sensitivity_analysis(), simple_repeat(), yjmob_mode()

### Community 34 - "pickle"
Cohesion: 0.36
Nodes (6): delta_model(), _n_i_lookup(), plot_identifiability_results(), plot_model(), plot_optimizer_results(), pickle_load()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 179 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `SIR.py`, `Session`, `core.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `SeedPolicyRun` to `SIR.py`, `adaptive_seed_selection.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `SIR.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12923076923076923 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `scene.js`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Should `MultiplexScene` be split into smaller, more focused modules?**
  _Cohesion score 0.09468599033816426 - nodes in this community are weakly interconnected._