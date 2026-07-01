# Attribution & Licensing

**Sentinel Suite** is a unified brand for an integrated toolkit. Several of its
modules are **powered by third-party open-source projects**, bundled here under
`vendor/` with their original licenses and authorship intact. "Sentinel Suite" is
the name of the integrated product — it is **not** a claim of authorship over
the upstream projects below.

## Powered-by (bundled upstream projects)

| Sentinel Suite module | Path | Upstream project | License | Author |
|---------------------|------|------------------|---------|--------|
| Sentinel Suite Skills | `vendor/ecc/` | [ecc](https://github.com/affaan-m/ecc) | MIT | Affaan Mustafa |
| Sentinel Suite Graph | `vendor/code-review-graph/` | [code-review-graph](https://github.com/tirth8205/code-review-graph) | MIT | Tirth Patel |
| Sentinel Suite Orchestrator | `vendor/octogent/` | [Octogent](https://github.com/hesamsheikh/octogent) | MIT | Hesam Sheikh |

Each vendored directory retains its own `LICENSE`. They were cloned with
`git clone --depth 1`; consult each upstream repo for full history and the
current version.

### Modifications to vendored code

- `vendor/ecc/.claude-plugin/plugin.json` — the plugin `name` and `description`
  fields were changed to present it as "sentinel-skills" within the Sentinel
  Suite marketplace. All upstream authorship, the homepage, the repository URL,
  and the MIT license are preserved. No other vendored files were modified.

## Original Sentinel Suite code (MIT, © micoherent7)

- `plugins/undercover/` — **Sentinel Suite Guard**. An original, clean-room
  re-creation of the *behaviour* of Claude Code's documented "Undercover Mode",
  generalised into a secrets/sensitive-info guardrail.
- `plugins/code-graph/` — glue (skill/command/MCP config) for Sentinel Suite Graph.
- `plugins/orchestrator/` — glue (skill/command/launcher) for Sentinel Suite
  Orchestrator.
- `mcp-server/` — **Sentinel Suite MCP**, the unified server.
- `mcp-server/src/sentinel_suite_mcp/orchestrator.py` + `orchestrator_server.py` —
  **Sentinel Suite Orchestrator**, an original **pure-Python re-implementation of
  Octogent's core** (tentacles + sessions + local dashboard). It was written from
  Octogent's public behaviour/concepts; no upstream TypeScript was copied.
  `vendor/octogent/` remains bundled for reference and keeps its own MIT license.
- `.claude-plugin/marketplace.json` — the Sentinel Suite marketplace manifest.

## Intent

This is a personal learning + productivity toolkit. Sentinel Suite Guard scrubs
your *own outgoing* commit/PR text; it is not for evading review or hiding
wrongdoing.
