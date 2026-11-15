# Graph Report - Social_Contact_Multiplex  (2026-11-10)

## Corpus Check
- 44 files · ~67,201 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .css 1)

## Summary
- 598 nodes · 1376 edges · 27 communities (20 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b69f5045`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.js
- numpy
- networkx
- core.py
- server.py
- MultiplexScene
- adaptive_seed_selection.py
- scene.js
- drive_seed_selection.py
- _Strategy
- serena
- networks.py
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
- BaselineRuns
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
- `_run_pair()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_engine_equivalence.py → network_setup.py
- `_setup()` --calls--> `load_shared_network()`  [EXTRACTED]
  tests/test_seed_policies.py → network_setup.py
- `reset()` --uses--> `ScenarioConfig`  [INFERRED]
  app/server.py → app/core.py

## Import Cycles
- None detected.

## Communities (27 total, 7 thin omitted)

### Community 0 - "main.js"
Cohesion: 0.08
Nodes (29): ALGO_HINTS, app, BASELINE_SERIES, baselineChart, chart, compact(), COST_HINTS, COST_SERIES (+21 more)

### Community 1 - "numpy"
Cohesion: 0.07
Nodes (33): _expand_to_ticks(), _lighten(), load_all(), _normalize_entry(), plot_joint_cost_comparison(), plot_joint_cost_elements(), push_curve(), _draw_network() (+25 more)

### Community 2 - "networkx"
Cohesion: 0.06
Nodes (47): init(), create_correlated_digraph(), create_social_graph(), create_w_k_hop_correlation(), jaccard_similarity(), parse_matrices(), simplify_matrices(), write_matrices_to_file() (+39 more)

### Community 3 - "core.py"
Cohesion: 0.21
Nodes (5): _error(), handle(), _json_default(), options(), ScenarioConfig

### Community 4 - "server.py"
Cohesion: 0.16
Nodes (6): index(), options(), remove(), reset(), _session(), step()

### Community 5 - "MultiplexScene"
Cohesion: 0.09
Nodes (4): positionNodeCard(), hexToRgb(), MultiplexScene, MultiplexView

### Community 6 - "adaptive_seed_selection.py"
Cohesion: 0.11
Nodes (23): baseline_infections(), build_tagged_network(), compute_beta_clustering(), compute_node_beta(), core_alone(), _core_alone_score(), core_over_btw(), _core_over_btw_score() (+15 more)

### Community 7 - "scene.js"
Cohesion: 0.25
Nodes (8): COLORS, SLOT_COLORS, SLOT_NAMES, STATE_COLORS, STATE_NAMES, ARRANGEMENTS, ease(), LAYERS

### Community 8 - "drive_seed_selection.py"
Cohesion: 0.13
Nodes (5): build(), main(), Dataset, _draw_comparison(), truncate_files()

### Community 9 - "_Strategy"
Cohesion: 0.10
Nodes (6): CoreOverBetweenness, DegreeBased, HillClimb, Milp, RandomSeeds, _Strategy

### Community 10 - "serena"
Cohesion: 0.50
Nodes (3): C:/Users/cates/.local/bin/serena.exe, serena, start-mcp-server

### Community 11 - "networks.py"
Cohesion: 0.10
Nodes (17): _bin_info(), build(), correlated_social(), describe(), er_graph(), _hs_bin_raw(), hs_info(), _hs_social_raw() (+9 more)

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
Cohesion: 0.11
Nodes (16): contact_network_path(), main(), run_adaptive(), run_milp(), baseline_infections(), compute_node_beta(), given_at_time(), global_cost_function() (+8 more)

### Community 19 - "SeedPolicyRun"
Cohesion: 0.05
Nodes (28): MultiplexSIRS, CostModel, edge_key(), SeedPolicyRun, _check(), _run_pair(), test_fj_q_r(), test_fj_q_true() (+20 more)

### Community 20 - "LineChart"
Cohesion: 0.24
Nodes (6): el(), LineChart, niceStep(), buildTiles(), seriesFor(), syncSeries()

### Community 21 - "_static_payload"
Cohesion: 0.22
Nodes (6): _cluster_layout(), _communities(), _grid_layout(), _seed_metrics(), _static_payload(), betweenness()

### Community 26 - "stepOnce"
Cohesion: 0.39
Nodes (7): collecting(), playLoop(), refreshPhaseBanner(), setPlaying(), sleep(), stepButton(), stepOnce()

## Knowledge Gaps
- **3 isolated node(s):** `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SeedPolicyRun` connect `SeedPolicyRun` to `networkx`, `BaselineRuns`, `Session`, `core.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **What connects `C:/Users/cates/.local/bin/serena.exe`, `start-mcp-server`, `Social_Contact_Multiplex` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08064516129032258 - nodes in this community are weakly interconnected._
- **Why does `BaselineRuns` connect `BaselineRuns` to `networkx`, `adaptive_seed_selection.py`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.07067307692307692 - nodes in this community are weakly interconnected._
- **Why does `MultiplexScene` connect `MultiplexScene` to `main.js`, `stepOnce`, `scene.js`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Should `networkx` be split into smaller, more focused modules?**
  _Cohesion score 0.05518207282913165 - nodes in this community are weakly interconnected._