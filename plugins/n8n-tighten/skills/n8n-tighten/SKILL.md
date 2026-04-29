---
name: n8n-tighten
description: Audit and build production-grade n8n workflows. Use this skill whenever the user mentions n8n, asks about building, fixing, debugging, or reviewing an n8n workflow, shares a workflow JSON to inspect, or has the n8n MCP server connected and references workflows by name or ID. Triggers on phrases like "n8n workflow", "automation flow", "Zapier-like workflow in n8n", "my workflow keeps failing", "build me an n8n workflow that...", "review this n8n flow", "audit my workflows", "tighten this", "my n8n expression isn't working", "Split In Batches", "Error Trigger", or any reference to n8n nodes, expressions ({{ $json }}, {{ $node }}, {{ $items }}), webhooks, schedules, or Code/Function nodes. Also use when the user asks general questions about workflow architecture, error handling, retries, sub-workflows, or LLM/AI nodes inside an automation tool (n8n is the most likely target). Cover both new workflow construction and audits of existing ones, work via n8n MCP tools (n8n_get_workflow, n8n_validate_workflow, n8n_create_workflow, etc.) when available, and prefer guiding the user toward production-grade patterns (Error Trigger workflows, exponential backoff, modular sub-workflows, secure credential hygiene) over the quick-and-dirty approach.
license: MIT. See LICENSE file.
---

# n8n Tighten

Tighten loose n8n workflows and build new ones that ship tight from day one. The goal is workflows that don't silently fail, stay debuggable as they grow, and use credentials and expressions safely, the equivalent of going around with a wrench and making sure nothing's about to rattle off.

## How to use this skill

There are two modes. Identify which one the user wants before doing anything else.

**Audit mode**: the user has an existing workflow and wants it reviewed, debugged, or hardened. The workflow can come in via three paths:
- **n8n MCP tools** (preferred when available): fetch the workflow via `n8n_get_workflow` and run validators with `n8n_validate_workflow` before doing the human review
- **Pasted JSON**: the user dropped the workflow export into the chat
- **Description in plain English**: the user is describing what they built; ask follow-ups to fill in the gaps

Default behavior: run the audit checklist in `examples/audit-checklist.md`, surface issues by severity, and propose specific fixes with node-level diffs.

**Build mode**: the user wants a new workflow from a description. Default behavior: clarify the trigger and the success path, then sketch the node sequence before writing JSON. Always include error handling and credential hygiene from the start, not as an afterthought.

If the user's intent isn't clear, ask one question to disambiguate. Don't assume.

## Detecting available tools

Before asking the user for a workflow JSON, check whether n8n MCP tools are available in the current session. The relevant tool names start with `n8n_` or `mcp__*__n8n_*`: common ones are `n8n_get_workflow`, `n8n_list_workflows`, `n8n_validate_workflow`, `n8n_create_workflow`, `n8n_update_partial_workflow`, `n8n_autofix_workflow`.

- **If MCP tools are available:** use them. Don't ask the user to paste JSON when you can fetch it. If the user mentions a workflow by name or ID, call `n8n_list_workflows` or `n8n_get_workflow` directly.
- **If MCP tools are NOT available:** ask the user either to paste the workflow JSON (export via `workflow menu → Download` in n8n) or describe what they built. Mention the MCP option in passing, some users don't know it exists. Link to https://github.com/czlonkowski/n8n-mcp for setup.

When in doubt, try a tool call first. If it fails because the tool isn't available, fall back to asking for JSON.

## Reference files

Each file covers one topic. Load only what the current task needs, don't preemptively read everything.

| File | When to load |
|------|--------------|
| `references/error-handling.md` | User mentions failures, retries, alerting, "my workflow died last night", or you're hardening any production workflow |
| `references/loops.md` | User has more than ~50 items to process, mentions Split In Batches, batch processing, pagination, or sub-workflows |
| `references/ai-nodes.md` | User mentions LLM/AI/agent nodes, model selection, prompt templates, OpenAI/Anthropic nodes, or token cost concerns |
| `references/expressions.md` | User writes `{{ }}` expressions, asks about `$json`/`$node`/`$items`, or has "undefined" or paired-item resolution errors |
| `references/webhooks-and-schedules.md` | User has Webhook, Schedule, or Cron triggers; asks about timezones, webhook paths, or response modes |
| `references/credentials.md` | User asks about API keys, env vars, secrets, or you spot hardcoded credentials in an audit |

## Core principles

These apply to every workflow, audit or build. Internalize them before writing any nodes.

**1. Failures must be visible.** Every production workflow needs an Error Trigger workflow attached in Settings → Error Workflow. A workflow that fails silently for 11 days is worse than one that doesn't exist. Default the Error Trigger to send to Slack/Telegram/email with: workflow name, failed node, error message, execution URL.

**2. Modular over monolithic.** Aim for 5-10 nodes per workflow. Anything bigger gets broken into sub-workflows via Execute Sub-workflow. Big sprawling canvases are unmaintainable and undebuggable.

**3. Credentials live in the credential manager, never in expressions or hardcoded.** No `={{$env.API_KEY}}` in HTTP Request nodes: use n8n's credential system. See `references/credentials.md`.

**4. Naming is documentation.** Node names should describe what they do, not what they are. "Get Stripe customer by email" is better than "HTTP Request" or "HTTP Request1". Audit-mode rule: any node named "HTTP Request2" is a yellow flag.

**5. Validate inputs at the edge.** Webhook and Trigger nodes receive untrusted data. Right after the trigger, add a validation step (Code node or IF node) that checks required fields exist and have the right shape. Route invalid inputs to an error branch, not to the happy path.

**6. Expressions are JavaScript.** `{{ }}` is a JS sandbox. Treat it as code: avoid side effects, don't mutate external state, use Set or Code nodes when logic gets non-trivial.

## Audit workflow

When asked to audit, run through `examples/audit-checklist.md` in order. The checklist groups issues by severity:

- **Critical**: workflow will fail silently, leak credentials, or corrupt data
- **High**: workflow works but is fragile, expensive, or hard to debug
- **Medium**: style/maintainability issues that compound over time
- **Low**: nits

**Step 1, Get the workflow into context.**
- With MCP: call `n8n_get_workflow` with the workflow ID or name. If the user didn't specify which one, list with `n8n_list_workflows` and ask which to audit (or audit several if the user says "all of them" or "active ones").
- Without MCP: work from the pasted JSON or the user's description.

**Step 2, Run programmatic checks first.**
- With MCP: call `n8n_validate_workflow` to surface structural issues (bad expressions, wrong typeVersions, missing webhook paths, malformed connections). Then optionally call `n8n_autofix_workflow` in preview mode (`applyFixes: false`) to see what could be auto-fixed. Don't apply autofixes silently, show the user the diff and let them approve.
- Without MCP: skim the JSON for the obvious stuff before doing the human review.

**Step 3, Human review.** Walk through the audit checklist. Look for what validators miss: naming, modularity, business-logic correctness, prompt structure, model choice, security posture.

**Step 4, Report findings** grouped by severity. For each finding: quote the offending node/expression, explain the problem in one sentence, propose the fix as a concrete diff or replacement.

**Step 5, Optionally apply fixes (MCP only).** If the user wants the fixes applied, use `n8n_update_partial_workflow` with explicit operations (`patchNodeField`, `updateNode`, `addConnection`, etc.): don't `n8n_update_full_workflow` unless the workflow is small. Always confirm before writing to a production workflow. If unsure whether the workflow is production, assume yes and ask.

## Build workflow

When asked to build, follow this order:

1. **Clarify the trigger.** Webhook? Schedule? Manual? Form? Chat? Each has different concerns, see `references/webhooks-and-schedules.md`.
2. **Map the happy path.** List the 5-10 steps as plain English first. If you can't fit it in 10 steps, it's two workflows.
3. **Identify the failure modes.** For each step, ask: what happens if this fails? Transient (retry) vs. permanent (route to error branch) vs. fatal (stop and alert).
4. **Choose nodes.** Prefer dedicated nodes (Slack, Stripe, Postgres) over generic HTTP Request when both exist. They handle auth, pagination, and errors better. With MCP available, use `search_nodes` to discover relevant nodes and `get_node` to check current parameters before writing them in.
5. **Write the workflow.**
   - With MCP: use `n8n_create_workflow` to write directly to the user's instance. Validate with `n8n_validate_workflow` after creation. Return the workflow ID and link, not the JSON.
   - Without MCP: output the JSON in a code block. The user imports via `workflow menu → Import from JSON`.
6. **Wire the Error Trigger.** Always. Even for "I'll just test it locally" workflows, habits compound. With MCP, this can be a separate `n8n_create_workflow` call for the Error Handler workflow itself.

## Output format

**When proposing a workflow (without MCP):**
- Lead with a one-paragraph summary of what it does and which trigger fires it
- Then a node-by-node breakdown in a table or numbered list
- Then the JSON (in a code block, importable)
- Then a "deploy checklist", credentials to create, env vars to set, Error Trigger workflow to attach

**When creating a workflow via MCP:**
- Lead with the same one-paragraph summary
- Confirm what was created: workflow name, ID, and a direct link if available (`https://<n8n-host>/workflow/<id>`)
- List what still needs human action: credentials to bind, env vars to set, Error Trigger workflow to attach in Workflow Settings
- Note that the workflow was created **inactive** by default (n8n MCP creates inactive workflows). The user has to activate it explicitly after reviewing.

**When auditing:**
- Lead with a one-paragraph verdict ("ship it after fixing 2 critical issues" / "rebuild, fundamental architecture problem")
- Then findings grouped by severity, each with quote → problem → fix
- Then a recommended next-step ordering
- If MCP fixes are possible and the user wants them applied, propose the operations as a list (`patchNodeField`, `addConnection`, etc.) and confirm before calling `n8n_update_partial_workflow`

## Versions and breaking changes

n8n ships fast. Some expression syntax has changed across versions, `$node["Name"]` and `$('Name')` behave subtly differently and `$('Name').item` has had regressions in Merge node contexts. When in doubt about a version-specific behavior, say so rather than guessing. The `references/expressions.md` file calls out the known footguns.

## What this skill is not

- Not a replacement for reading the n8n docs. Point users to https://docs.n8n.io for canonical reference.
- Not a security audit tool. It catches obvious credential leaks; it doesn't substitute for proper threat modeling.
- Not opinionated about hosting (Cloud vs. self-hosted vs. embedded), patterns here work on all three.
