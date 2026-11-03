# Graph Report - Social_Contact_Multiplex  (2026-10-13)

## Corpus Check
- 44 files · ~66,816 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 590 nodes · 1348 edges · 27 communities (21 shown, 6 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 71 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `01d86bb8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- README.md
- random
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
- browser_api.py
- test_engine_equivalence.py
- SeedPolicyRun
- LineChart
- core.py
- Session
- seeding.py
- sbm_graph
- stepOnce
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

## Communities (27 total, 6 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "numpy"
Cohesion: 0.07
Nodes (31): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), compare_infections_adherence() (+23 more)

### Community 2 - "README.md"
Cohesion: 0.09
Nodes (31): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target() (+23 more)

### Community 3 - "random"
Cohesion: 0.09
Nodes (24): create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), break_quarantine(), competing_spread_step(), fj_belief_update(), misinfo_seed_set() (+16 more)

### Community 4 - "server.py"
Cohesion: 0.11
Nodes (7): Workspace, index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (5): positionNodeCard(), hexToRgb(), ease(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.07
Nodes (32): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_over_btw(), degree_based_selection(), given_at_time(), global_cost_function() (+24 more)

### Community 7 - "scene.js"
Cohesion: 0.29
Nodes (7): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.12
Nodes (6): build(), main(), Dataset, _draw_comparison(), _draw_network(), truncate_files()

### Community 9 - "_Strategy"
Cohesion: 0.11
Nodes (5): DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "networkx"
Cohesion: 0.14
Nodes (15): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social() (+7 more)

### Community 13 - "SeedMetricChart"
Cohesion: 0.35
Nodes (5): barPath(), binCounts(), el(), METRICS, SeedMetricChart

### Community 14 - "inspector.js"
Cohesion: 0.26
Nodes (11): esc(), fmtPct(), mean(), metricCell(), NetworkIndex, quarantineText(), renderGroupCard(), renderNodeCard() (+3 more)

### Community 16 - "restart"
Cohesion: 0.27
Nodes (17): activeSlot(), addSlot(), call(), clearSelection(), fillForm(), handleClick(), httpCall(), refreshPanel() (+9 more)

### Community 17 - "browser_api.py"
Cohesion: 0.33
Nodes (3): _error(), handle(), _json_default()

### Community 18 - "test_engine_equivalence.py"
Cohesion: 0.10
Nodes (18): MultiplexSIRS, CostModel, edge_key(), _check(), _run_pair(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q() (+10 more)

### Community 19 - "SeedPolicyRun"
Cohesion: 0.08
Nodes (3): BaselineRuns, _RngStream, SeedPolicyRun

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "core.py"
Cohesion: 0.13
Nodes (11): _cluster_layout(), _communities(), _fit_disc(), _grid_layout(), _normalized_layout(), options(), ScenarioConfig, _seed_metrics() (+3 more)

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `random`, `test_engine_equivalence.py`, `core.py`, `Session`, `seeding.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `SeedPolicyRun` to `seeding.py`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.0701484895033282 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `scene.js`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.08888888888888889 - nodes in this community are weakly interconnected._