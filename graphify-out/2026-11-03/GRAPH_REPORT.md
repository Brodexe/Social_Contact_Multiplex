# Graph Report - Social_Contact_Multiplex  (2026-10-17)

## Corpus Check
- 44 files · ~66,996 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 596 nodes · 1360 edges · 32 communities (24 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `70caf47c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- README.md
- SIR.py
- server.py
- MultiplexScene
- adaptive_seed_selection.py
- scene.js
- drive_seed_selection.py
- _Strategy
- serena
- networkx
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- milp.py
- CostModel
- SeedPolicyRun
- LineChart
- core.py
- test_engine_equivalence.py
- test_seed_policies.py
- sbm_graph
- random
- stepOnce
- BaselineRuns
- network_setup.py
- MultiplexSIRS
- _RngStream
- hf_space/README.md

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

## Communities (32 total, 8 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "numpy"
Cohesion: 0.07
Nodes (32): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), compare_infections_adherence() (+24 more)

### Community 2 - "README.md"
Cohesion: 0.08
Nodes (32): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target() (+24 more)

### Community 3 - "SIR.py"
Cohesion: 0.17
Nodes (11): break_quarantine(), competing_spread_step(), fj_belief_update(), misinfo_seed_set(), quarantine_edge_removal(), restore_edges(), set_info_label(), Simulate_SIR() (+3 more)

### Community 4 - "server.py"
Cohesion: 0.06
Nodes (14): _error(), handle(), _json_default(), _network_key(), options(), ScenarioConfig, Session, Workspace (+6 more)

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (5): positionNodeCard(), hexToRgb(), ease(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.12
Nodes (21): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_alone(), _core_alone_score(), core_over_btw(), _core_over_btw_score() (+13 more)

### Community 7 - "scene.js"
Cohesion: 0.29
Nodes (7): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.13
Nodes (5): build(), main(), Dataset, _draw_comparison(), _draw_network()

### Community 9 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "networkx"
Cohesion: 0.15
Nodes (14): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), NetworkMismatchError (+6 more)

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
Cohesion: 0.16
Nodes (11): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+3 more)

### Community 18 - "CostModel"
Cohesion: 0.18
Nodes (4): CostModel, edge_key(), _FixedBaselines, test_cost_matches_research()

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "core.py"
Cohesion: 0.13
Nodes (9): _cluster_layout(), _communities(), _fit_disc(), _grid_layout(), _normalized_layout(), _seed_metrics(), _static_payload(), describe() (+1 more)

### Community 22 - "test_engine_equivalence.py"
Cohesion: 0.26
Nodes (12): _check(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r(), test_ic_q_true(), test_lt_q_int(), test_misinfo_fj_takeover() (+4 more)

### Community 23 - "test_seed_policies.py"
Cohesion: 0.29
Nodes (9): _check_case(), _reference(), _setup(), test_degree_lt(), test_degree_no_spread(), test_hill_climb_accepts_non_worsening_swap(), test_milp_seed_term_shrinks_seed_set(), test_random_ic_per_tick() (+1 more)

### Community 25 - "random"
Cohesion: 0.31
Nodes (5): khop_social(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

### Community 28 - "network_setup.py"
Cohesion: 0.39
Nodes (5): build_shared_network(), _current_params(), generate_global_betas(), laplacian_smooth_beta(), load_shared_network()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `README.md`, `server.py`, `CostModel`, `core.py`, `test_seed_policies.py`, `MultiplexSIRS`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `CostModel`, `core.py`, `_RngStream`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.07019230769230769 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `scene.js`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.08067375886524823 - nodes in this community are weakly interconnected._