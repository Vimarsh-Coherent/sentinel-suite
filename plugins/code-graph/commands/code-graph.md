---
description: Build/refresh the code knowledge graph and run an impact or architecture analysis.
argument-hint: "[build|impact <symbol/file>|arch|review|hubs]"
---

Use the bundled code-review-graph MCP tools to answer the user's request: `$ARGUMENTS`

- `build` (or empty): call `build_or_update_graph_tool`, then report graph stats via `list_graph_stats_tool`.
- `impact <target>`: call `get_impact_radius_tool` for the given symbol/file and summarise the blast radius.
- `arch`: call `get_architecture_overview_tool` and summarise the module/community map.
- `review`: call `detect_changes_tool` then `get_review_context_tool` and present a focused review.
- `hubs`: call `get_hub_nodes_tool` and `get_bridge_nodes_tool` and list architectural hotspots/chokepoints.

If the graph hasn't been built yet, run `build_or_update_graph_tool` first.
