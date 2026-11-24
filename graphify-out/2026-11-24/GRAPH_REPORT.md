# Graph Report - Social_Contact_Multiplex  (2026-11-24)

## Corpus Check
- 57 files · ~517,789 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 728 nodes · 1707 edges · 33 communities (26 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2a62c83e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- matplotlib_pyplot
- README.md
- extract_mfa.py
- numpy
- MultiplexScene
- visualize_adaptive.py
- scene.js
- cost_curve_store.py
- SeedPolicyRun
- serena
- plot_identifiability.py
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
- partial_rank_mapping
- _normalized_layout
- networkx
- _static_payload
- stepOnce
- Session
- Workspace
- milp.py
- hf_space/README.md
- BaselineRuns
- os

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
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `reset()` --uses--> `ScenarioConfig`  [INFERRED]
  app/server.py → app/core.py
- `Session` --uses--> `MultiplexSIRS`  [INFERRED]
  app/core.py → app/engine.py
- `Session` --uses--> `SeedPolicyRun`  [INFERRED]
  app/core.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (33 total, 7 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 2 - "README.md"
Cohesion: 0.08
Nodes (35): init(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target(), greedy_for_lt(), IC(), IC_prob_matrix() (+27 more)

### Community 3 - "extract_mfa.py"
Cohesion: 0.25
Nodes (5): parse_sample_data(), align_true_to_est(), mean_std(), plot_k_est(), plot_sensitivity_results()

### Community 4 - "numpy"
Cohesion: 0.15
Nodes (15): _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate(), mse_loss() (+7 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "visualize_adaptive.py"
Cohesion: 0.21
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "cost_curve_store.py"
Cohesion: 0.09
Nodes (17): _cascade_label(), clear_experiment_label(), _expand_to_ticks(), _lighten(), load_all(), _lookup(), _normalize_entry(), plot_correlation_ablation() (+9 more)

### Community 9 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (28): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+20 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 11 - "plot_identifiability.py"
Cohesion: 0.35
Nodes (7): _aggregate(), delta_model(), _n_i_lookup(), _parities(), _plot_band(), plot_model(), _series()

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
Nodes (38): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), given_at_time() (+30 more)

### Community 18 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 19 - "_Strategy"
Cohesion: 0.11
Nodes (5): DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.14
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 22 - "partial_rank_mapping"
Cohesion: 0.25
Nodes (4): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping()

### Community 24 - "networkx"
Cohesion: 0.06
Nodes (34): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social() (+26 more)

### Community 25 - "_static_payload"
Cohesion: 0.15
Nodes (8): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), describe(), betweenness(), CoreOverBetweenness

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 30 - "milp.py"
Cohesion: 0.10
Nodes (14): build(), main(), _parse_experiment_args(), contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections() (+6 more)

### Community 37 - "os"
Cohesion: 0.08
Nodes (17): degree_correlation_over_time(), plot_degree_correlation(), read_contact(), read_social(), plot_new_infections(), read_contact(), read_social(), simulate_temporal_multiplex() (+9 more)

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 221 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `core.py`, `README.md`, `Session`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `SeedPolicyRun`, `README.md`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.07539450613676213 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `MultiplexScene` be split into smaller, more focused modules?**
  _Cohesion score 0.09158186864014801 - nodes in this community are weakly interconnected._