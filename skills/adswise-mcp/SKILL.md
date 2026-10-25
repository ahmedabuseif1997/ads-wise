---
name: adswise-mcp
description: Use the secured Ads-Wise developer MCP to inspect the live project, review development tasks, or update an explicitly authorized task. Applies to Ads-Wise operations, integration health, tenant isolation, and implementation coordination.
---

# AdsWise MCP

Use the configured `ads_wise` MCP server at `https://ads-wise.com/mcp/developer`.

## Workflow

1. Call `get_project_context` before making Ads-Wise decisions that depend on the live environment.
2. Call `list_development_tasks` when reviewing or continuing queued work.
3. Call `update_development_task` only when the user explicitly asks to change a task or its status.
4. Treat production changes, deployments, tenant pauses, and AI pauses as separate actions that still require the user's authorization.

## Invariants

- Never reveal, log, commit, or place the MCP bearer token in this skill.
- Keep tenant data isolated; never reuse one workspace's integration identifiers, tokens, analytics, or cached results for another workspace.
- Prefer read-only inspection before any live mutation.
- Report the exact task or environment affected after a write.
- If `ads_wise` is unavailable, report the connection failure rather than substituting guessed project state.

The local connection helper in `scripts/ads-wise-mcp-headers` reads the bearer token from macOS Keychain service `ads-wise-mcp-token`.

For the easiest first-time setup on macOS, run `scripts/connect.sh`; it asks for the token once and configures both Codex and Claude.
