---
name: code-graph
description: Token-efficient code intelligence over a structural knowledge graph (powered by the code-review-graph MCP server). Use for "impact radius", "what does this change affect", "blast radius", "architecture overview", "find hubs/bridges", "review context", "semantic code search", or before reviewing a PR. Builds a Tree-sitter→SQLite graph and answers structural questions cheaply.
---

# Code Graph (powered by code-review-graph)

This skill drives the bundled **code-review-graph** MCP server — a local-first
engine that parses a repo with Tree-sitter into a SQLite knowledge graph
(functions/classes as nodes; calls/imports/inheritance/tests as edges) and
answers "what is affected by this change?" with ~80x fewer tokens than reading
the whole codebase.

## Setup (once per repo)

1. Ensure the MCP server is connected (this plugin ships `.mcp.json`, which runs
   `uvx code-review-graph serve`). Vendored source lives in
   `${CLAUDE_PLUGIN_ROOT}/../../vendor/code-review-graph` for offline/learning.
2. Build/refresh the graph: call `build_or_update_graph_tool` (incremental,
   usually <2s after the first build).

## Common workflows (call these MCP tools)

| Goal | Tool |
|------|------|
| Build / incrementally update the graph | `build_or_update_graph_tool` |
| What does changing X affect? (blast radius) | `get_impact_radius_tool` |
| Risk-scored summary of current changes | `detect_changes_tool` |
| Token-optimized review context for a PR | `get_review_context_tool` |
| Callers / callees / tests / imports of a symbol | `query_graph_tool` |
| Meaning-based search for code entities | `semantic_search_nodes_tool` |
| High-level architecture map (communities) | `get_architecture_overview_tool` |
| Most-connected hotspots | `get_hub_nodes_tool` |
| Chokepoints between modules | `get_bridge_nodes_tool` |
| Untested hotspots / weaknesses | `get_knowledge_gaps_tool` |
| Auto-suggested review questions | `get_suggested_questions_tool` |
| List indexed repos / graph stats | `list_repos_tool`, `list_graph_stats_tool` |

## Typical sequence for a code review

1. `build_or_update_graph_tool` — make sure the graph is current.
2. `detect_changes_tool` — get risk-scored impact of the diff.
3. `get_review_context_tool` — pull the minimal relevant context.
4. `get_impact_radius_tool` on any high-risk node to see what else it touches.
5. Review using only that focused context (not the whole repo).

Prefer these tools over reading entire files when a question is structural
("who calls this?", "what breaks if I change this?", "where are the hubs?").
