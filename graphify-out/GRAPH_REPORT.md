# Graph Report - Social_Contact_Multiplex  (2026-11-22)

## Corpus Check
- 57 files · ~517,714 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 728 nodes · 1701 edges · 37 communities (26 shown, 11 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b32f60f4`
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
- test_engine_equivalence.py
- CostModel
- networks.py
- _static_payload
- stepOnce
- test_seed_policies.py
- Session
- Workspace
- milp.py
- hf_space/README.md
- BaselineRuns
- MultiplexSIRS
- _RngStream
- _draw_network
- networkx

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
- `_check_case()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_hill_climb_accepts_non_worsening_swap()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py

## Import Cycles
- None detected.

## Communities (37 total, 11 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 2 - "README.md"
Cohesion: 0.05
Nodes (47): init(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), parse_matrices(), simplify_matrices(), write_matrices_to_file() (+39 more)

### Community 4 - "numpy"
Cohesion: 0.10
Nodes (21): correlated_social(), degree_correlation_over_time(), plot_five_conditions(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff() (+13 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "visualize_adaptive.py"
Cohesion: 0.19
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "cost_curve_store.py"
Cohesion: 0.09
Nodes (18): _cascade_label(), clear_experiment_label(), _expand_to_ticks(), _lighten(), load_all(), _lookup(), _normalize_entry(), plot_correlation_ablation() (+10 more)

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
Cohesion: 0.17
Nodes (5): _error(), handle(), _json_default(), _fit_disc(), _normalized_layout()

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (7): betweenness(), CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "server.py"
Cohesion: 0.14
Nodes (8): options(), ScenarioConfig, index(), options(), remove(), reset(), _session(), step()

### Community 22 - "test_engine_equivalence.py"
Cohesion: 0.10
Nodes (18): build(), main(), load_contact_bins(), plot_correlation_bars(), _parse_experiment_args(), truncate_files(), _check(), test_fj_q_r() (+10 more)

### Community 23 - "CostModel"
Cohesion: 0.20
Nodes (4): CostModel, edge_key(), _FixedBaselines, test_cost_matches_research()

### Community 24 - "networks.py"
Cohesion: 0.15
Nodes (13): _bin_info(), build(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social(), NetworkMismatchError (+5 more)

### Community 25 - "_static_payload"
Cohesion: 0.20
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), describe()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 27 - "test_seed_policies.py"
Cohesion: 0.29
Nodes (9): _check_case(), _reference(), _setup(), test_degree_lt(), test_degree_no_spread(), test_hill_climb_accepts_non_worsening_swap(), test_milp_seed_term_shrinks_seed_set(), test_random_ic_per_tick() (+1 more)

### Community 30 - "milp.py"
Cohesion: 0.12
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 37 - "networkx"
Cohesion: 0.08
Nodes (17): plot_degree_correlation(), read_contact(), read_social(), plot_new_infections(), read_contact(), read_social(), simulate_temporal_multiplex(), sirs_step_temporal() (+9 more)

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 221 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `MultiplexSIRS`, `README.md`, `core.py`, `test_seed_policies.py`, `Session`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `SeedPolicyRun`, `README.md`, `_RngStream`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.05401234567901234 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `Workspace` to `core.py`, `server.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.0990990990990991 - nodes in this community are weakly interconnected._