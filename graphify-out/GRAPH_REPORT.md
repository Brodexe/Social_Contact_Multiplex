# Graph Report - Social_Contact_Multiplex  (2026-11-25)

## Corpus Check
- 57 files · ~518,378 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 131 file(s) not represented in the graph (top: .gml 89, .pkl 14, .csv 9)

## Summary
- 755 nodes · 1773 edges · 35 communities (26 shown, 9 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 77 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce168b19`
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
- SIR.py
- seeding.py
- SeedPolicyRun
- serena
- sbm_graph
- CLAUDE.md
- SeedMetricChart
- test_engine_equivalence.py
- Project Config
- .step
- adaptive_seed_selection.py
- test_seed_policies.py
- _Strategy
- find_seeds.py
- server.py
- visualize_adaptive.py
- MultiplexSIRS
- networkx
- core.py
- _FixedBaselines
- random
- Session
- plot_identifiability.py
- hf_space/README.md
- BaselineRuns
- drive_seed_selection.py
- plot_joint_cost_elements
- os

## God Nodes (most connected - your core abstractions)
1. `MultiplexScene` - 28 edges
2. `SeedPolicyRun` - 25 edges
3. `MultiplexView` - 20 edges
4. `Simulate_SIR()` - 16 edges
5. `LineChart` - 15 edges
6. `restart()` - 14 edges
7. `_check()` - 14 edges
8. `hill2()` - 12 edges
9. `_static_payload()` - 12 edges
10. `MultiplexSIRS` - 12 edges

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

## Communities (35 total, 9 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.05
Nodes (72): el(), LineChart, niceStep(), esc(), fmtPct(), mean(), metricCell(), NetworkIndex (+64 more)

### Community 1 - "milp.py"
Cohesion: 0.09
Nodes (18): build(), main(), contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta() (+10 more)

### Community 2 - "README.md"
Cohesion: 0.14
Nodes (18): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), drive_optimizer(), given_at_time(), loss(), loss_k_only() (+10 more)

### Community 3 - "pandas"
Cohesion: 0.09
Nodes (11): degree_correlation_over_time(), plot_degree_correlation(), read_contact(), read_social(), plot_new_infections(), read_contact(), read_social(), simulate_temporal_multiplex() (+3 more)

### Community 4 - "matplotlib_pyplot"
Cohesion: 0.19
Nodes (18): compare_infections_adherence(), const_quarantines(), fj_quarantine(), informed_vs_noninformed(), jaccard_similarity(), misinformation_dynamics(), normal_dist_quarantines(), permanent_quarantine() (+10 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.08
Nodes (10): COLORS, hexToRgb(), SLOT_COLORS, SLOT_NAMES, STATE_COLORS, ARRANGEMENTS, ease(), LAYERS (+2 more)

### Community 6 - "numpy"
Cohesion: 0.12
Nodes (18): _draw_network(), analyze_file(), compute_adherence_bar_estimate(), estimate_a_then_f(), plot_adherence_bar_combined(), truncate_at_new_infection_cutoff(), two_stage_estimate(), mse_loss() (+10 more)

### Community 7 - "SIR.py"
Cohesion: 0.17
Nodes (11): break_quarantine(), competing_spread_step(), fj_belief_update(), misinfo_seed_set(), quarantine_edge_removal(), restore_edges(), set_info_label(), Simulate_SIR() (+3 more)

### Community 8 - "seeding.py"
Cohesion: 0.21
Nodes (7): greedy_for_ic(), greedy_for_ic_target(), greedy_for_lt(), IC(), IC_prob_matrix(), LT(), lt_prob_matrix()

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe, serena, start-mcp-server

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "test_engine_equivalence.py"
Cohesion: 0.26
Nodes (12): _check(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r(), test_ic_q_true(), test_lt_q_int(), test_misinfo_fj_takeover() (+4 more)

### Community 16 - ".step"
Cohesion: 0.27
Nodes (3): CostModel, edge_key(), test_cost_matches_research()

### Community 17 - "adaptive_seed_selection.py"
Cohesion: 0.08
Nodes (31): baseline_infections(), _bin_scores(), build_tagged_network(), centrality_bin_scores(), compute_beta_clustering(), compute_node_beta(), degree_based_selection(), format_rule_lines() (+23 more)

### Community 18 - "test_seed_policies.py"
Cohesion: 0.29
Nodes (9): _check_case(), _reference(), _setup(), test_degree_lt(), test_degree_no_spread(), test_hill_climb_accepts_non_worsening_swap(), test_milp_seed_term_shrinks_seed_set(), test_random_ic_per_tick() (+1 more)

### Community 19 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 20 - "find_seeds.py"
Cohesion: 0.39
Nodes (6): find_seed_set(), initialize_social_IM(), adherence_mode(), sensitivity_analysis(), simple_repeat(), yjmob_mode()

### Community 21 - "server.py"
Cohesion: 0.07
Nodes (12): _error(), handle(), _json_default(), options(), ScenarioConfig, Workspace, index(), options() (+4 more)

### Community 22 - "visualize_adaptive.py"
Cohesion: 0.18
Nodes (7): load_data(), _node_metrics_and_selection(), _plot_selected_seed_counts(), plot_selected_seed_counts_by_metric_bin(), plot_selected_seed_counts_for_real_world_bins(), plot_selected_seed_metric_heatmaps(), selection_frequency()

### Community 24 - "networkx"
Cohesion: 0.13
Nodes (15): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), NetworkMismatchError (+7 more)

### Community 25 - "core.py"
Cohesion: 0.16
Nodes (9): _cluster_layout(), _communities(), _fit_disc(), _grid_layout(), _normalized_layout(), _seed_metrics(), _static_payload(), describe() (+1 more)

### Community 27 - "random"
Cohesion: 0.31
Nodes (5): khop_social(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity()

### Community 29 - "plot_identifiability.py"
Cohesion: 0.15
Nodes (18): _aggregate(), _check_homogeneous(), delta_model(), _finish(), _groups(), _half(), _n_i_lookup(), _node_count() (+10 more)

### Community 33 - "drive_seed_selection.py"
Cohesion: 0.06
Nodes (29): _cascade_label(), clear_experiment_label(), clear_labels(), _condition_label(), _expand_to_ticks(), _lighten(), load_all(), _lookup() (+21 more)

### Community 34 - "plot_joint_cost_elements"
Cohesion: 0.33
Nodes (3): _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements()

### Community 37 - "os"
Cohesion: 0.13
Nodes (10): degree_preserving_rewire(), make_contact_layer_conditions(), make_correlated_social(), partial_rank_mapping(), plot_five_conditions(), simulate_all_conditions(), simulate_one_condition(), sirs_step() (+2 more)

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 232 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `BaselineRuns`, `README.md`, `seeding.py`, `.step`, `test_seed_policies.py`, `MultiplexSIRS`, `core.py`, `Session`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/AppData/Roaming/uv/tools/serena-agent/Scripts/python.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.052604698672114404 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `seeding.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `milp.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08771929824561403 - nodes in this community are weakly interconnected._
- **Why does `Workspace` connect `server.py` to `core.py`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.1402116402116402 - nodes in this community are weakly interconnected._