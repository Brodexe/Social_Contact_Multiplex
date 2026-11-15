# Graph Report - Social_Contact_Multiplex  (2026-11-12)

## Corpus Check
- 44 files · ~67,499 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 599 nodes · 1379 edges · 26 communities (21 shown, 5 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b69f5045`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- README.md
- core.py
- server.py
- MultiplexScene
- adaptive_seed_selection.py
- scene.js
- drive_seed_selection.py
- seeding.py
- serena
- networkx
- CLAUDE.md
- SeedMetricChart
- inspector.js
- Project Config
- restart
- milp.py
- Session
- SeedPolicyRun
- LineChart
- _static_payload
- Workspace
- _normalized_layout
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
- `_reference()` --calls--> `edge_key()`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `_check_case()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_hill_climb_accepts_non_worsening_swap()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `test_milp_seed_term_shrinks_seed_set()` --calls--> `SeedPolicyRun`  [EXTRACTED]
  tests/test_seed_policies.py → app/seeding.py
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py

## Import Cycles
- None detected.

## Communities (26 total, 5 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "numpy"
Cohesion: 0.07
Nodes (34): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), _draw_network() (+26 more)

### Community 2 - "README.md"
Cohesion: 0.06
Nodes (42): init(), parse_matrices(), simplify_matrices(), write_matrices_to_file(), find_seed_set(), initialize_social_IM(), greedy_for_ic(), greedy_for_ic_target() (+34 more)

### Community 3 - "core.py"
Cohesion: 0.24
Nodes (4): _error(), handle(), _json_default(), options()

### Community 4 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (5): positionNodeCard(), hexToRgb(), ease(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.11
Nodes (23): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_alone(), _core_alone_score(), core_over_btw(), _core_over_btw_score() (+15 more)

### Community 7 - "scene.js"
Cohesion: 0.29
Nodes (7): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.14
Nodes (5): build(), main(), Dataset, _draw_comparison(), truncate_files()

### Community 9 - "seeding.py"
Cohesion: 0.05
Nodes (13): BaselineRuns, betweenness(), CoreOverBetweenness, CostModel, DegreeBased, edge_key(), HillClimb, Milp (+5 more)

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "networkx"
Cohesion: 0.06
Nodes (35): _bin_info(), build(), correlated_social(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw(), khop_social() (+27 more)

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
Cohesion: 0.15
Nodes (11): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+3 more)

### Community 18 - "Session"
Cohesion: 0.20
Nodes (3): _network_key(), _seed_metrics(), Session

### Community 19 - "SeedPolicyRun"
Cohesion: 0.09
Nodes (15): MultiplexSIRS, SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true(), test_ic_no_q(), test_ic_q_r() (+7 more)

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "_static_payload"
Cohesion: 0.20
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), ScenarioConfig, _static_payload(), describe()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `networkx`, `seeding.py`, `Session`, `core.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `seeding.py` to `adaptive_seed_selection.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.06993006993006994 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `scene.js`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `README.md` be split into smaller, more focused modules?**
  _Cohesion score 0.05970149253731343 - nodes in this community are weakly interconnected._