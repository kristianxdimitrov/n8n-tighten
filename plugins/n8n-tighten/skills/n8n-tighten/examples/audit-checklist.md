# Audit checklist

Walk this checklist top to bottom when auditing an n8n workflow. Group findings by severity in the final report.

## Critical: fix before production

These cause silent failures, data corruption, or credential leaks.

- [ ] **Error Workflow attached.** Workflow Settings → Error Workflow set to a real error handler. (See `references/error-handling.md`.)
- [ ] **No hardcoded credentials.** No API keys in node params, Code nodes, headers, URLs, or `$env`. (See `references/credentials.md`.)
- [ ] **Webhook signature verification.** External webhooks (Stripe, GitHub, Shopify) verify HMAC before processing.
- [ ] **Idempotency on retryable webhooks.** Payment/order webhooks check for duplicate event IDs.
- [ ] **No `console.log` of credentials.** Code nodes don't log secrets.
- [ ] **Production webhook URLs configured upstream.** External services point to production URL, not test.
- [ ] **Pagination loops have hard caps.** Recursive sub-workflows or Split In Batches loops can't run forever.
- [ ] **Workflow timezone set explicitly** for any schedule-triggered workflow.

## High: fix soon

Workflow technically works but is fragile, expensive, or hard to debug.

- [ ] **Retry On Fail enabled** on every external API call.
- [ ] **Exponential backoff** for rate-limited APIs (not n8n's fixed-interval retry).
- [ ] **Continue On Fail** used deliberately, not by default.
- [ ] **Max Iterations cap** on AI Agent nodes.
- [ ] **`max_tokens` set** on LLM nodes (not left at default 4096).
- [ ] **Model choice justified**: small models for high-volume, frontier models only where quality matters.
- [ ] **Structured output** enforced via JSON mode or Output Parser, not freeform parsing.
- [ ] **Webhook validation step** right after the trigger checks required fields exist.
- [ ] **Catch-up logic** on time-sensitive scheduled workflows (daily reports, billing).
- [ ] **No nested loops** (Split In Batches inside Split In Batches).
- [ ] **Webhook response mode** matches use case (async vs. sync, not 30+ second holds).

## Medium: refactor when you next touch this

Style and maintainability issues that compound over time.

- [ ] **Node names describe intent.** No "HTTP Request2" or "Code1".
- [ ] **Workflow has < 10 nodes.** Larger flows extracted into sub-workflows.
- [ ] **Repeated logic extracted** into reusable sub-workflows.
- [ ] **System prompts vs. user prompts split** correctly on LLM nodes.
- [ ] **Webhook paths descriptive** (`stripe-payment-success` not UUID).
- [ ] **Defensive expressions** (`?.`, `??`) where data may be missing.
- [ ] **Luxon syntax** for date math, not raw `new Date()`.
- [ ] **Predefined nodes preferred** over generic HTTP Request when both exist (Slack, Stripe, Postgres).
- [ ] **No double-loops** over n8n's automatic per-item iteration.

## Low: nice-to-haves

- [ ] **Notes added** to workflow describing purpose and owner.
- [ ] **Credentials named clearly** (`Stripe: Production` not `Stripe1`).
- [ ] **Schedules avoid the minute boundary** (`7 * * * *` not `0 * * * *`).
- [ ] **Workflow tagged** for searchability.
- [ ] **Static configuration** moved to env vars or a Config node at the top.

## Reporting format

When you've completed the checklist, structure findings like this:

```
## Verdict
[One paragraph: ship-ready, ship-after-fixes, or rebuild]

## Critical (N findings)
1. **[Issue title]**
   - Where: [Node name + parameter, or quoted code/expression]
   - Problem: [One-sentence explanation]
   - Fix: [Concrete proposed change]

## High (N findings)
[same structure]

## Medium / Low (N findings)
[same structure, can be more terse]

## Recommended fix order
1. [Most critical fix]
2. [Next]
3. [...]
```

Always lead with the verdict so the user knows whether to keep reading. Then put the most critical issues first, don't bury a credential leak under nine style nits.

## When to use the n8n MCP tools

When the n8n MCP server is connected (tool names start with `n8n_`), prefer the tool path over manual JSON inspection, validators catch structural issues programmatically and you can act on findings without copy-paste loops.

**Recommended audit sequence with MCP:**

1. **Get the workflow.** `n8n_get_workflow` with the workflow ID. If the user said "audit my workflows" without specifying which: `n8n_list_workflows` first, then audit each (or ask which subset, active only, scheduled only, etc.).

2. **Run the structural validator.** `n8n_validate_workflow` returns expression format errors, connection structure issues, wrong node typeVersions, missing webhook paths. These map directly to **Critical** and **High** findings, surface them first.

3. **Preview programmatic fixes.** `n8n_autofix_workflow` with `applyFixes: false` (preview mode) shows what could be auto-fixed for: expression format, typeVersion correction, error output config, missing webhook paths, connection structure. Don't apply silently, show the user the preview, get confirmation.

4. **Run the human review** against the audit checklist above. This catches what validators don't: naming, modularity, business-logic correctness, prompt structure, security posture, model choice, idempotency.

5. **Apply fixes only with confirmation.** If the user wants fixes applied:
   - Small, surgical edits → `n8n_update_partial_workflow` with explicit operations (`patchNodeField`, `updateNode`, `addConnection`, `updateSettings`)
   - Large rewrites → propose creating a new workflow with `n8n_create_workflow` rather than overwriting, so the user has a rollback
   - Never use `n8n_update_full_workflow` on a production workflow without an explicit "yes, replace it entirely"

**Things to know about the MCP tools:**

- `n8n_create_workflow` always creates **inactive** workflows. Tell the user they need to activate it manually after review.
- The `n8n_audit_instance` tool runs n8n's built-in security audit + a deeper instance scan. Worth running once during initial onboarding to surface instance-level issues (default credentials, missing TLS, etc.), separate concern from per-workflow audits.
- If a tool call fails with an auth/credentials error, the n8n API key is missing or expired. The MCP server still works for documentation/validation tools without API credentials, but you can't read or modify workflows. Tell the user to set `N8N_API_KEY` in their MCP config.
- Don't trust default parameter values when reading nodes. `get_node` with `mode='full'` shows what's actually configured; defaults can hide misconfiguration.
