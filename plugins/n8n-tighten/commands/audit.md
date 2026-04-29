---
description: Audit an n8n workflow for production readiness with severity-ranked findings
argument-hint: [workflow-id-or-paste-json-after]
---

Run a production-readiness audit on the n8n workflow specified after this command.

The argument may be one of:
- An n8n workflow ID (use the n8n MCP tools to fetch it via `n8n_get_workflow`)
- The literal word "all" or "active" (use `n8n_list_workflows` and audit each)
- Empty (ask the user to either paste a workflow JSON or describe the workflow)
- Inline JSON pasted after the command

Argument provided: $ARGUMENTS

Follow the audit workflow defined in the n8n-tighten skill:

1. Get the workflow into context (MCP, JSON paste, or description)
2. Run `n8n_validate_workflow` first if MCP is available
3. Walk through `examples/audit-checklist.md` in order
4. Report findings grouped by severity (Critical, High, Medium, Low) with concrete fixes
5. Lead with a one-paragraph verdict before listing findings
6. End with a recommended fix order

Be opinionated. Catch the stuff that breaks at 2am: silent failures (no Error Trigger), hardcoded credentials, missing retries on rate-limited APIs, schedule triggers without timezones, webhook signatures missing on destructive endpoints. Don't bury a credential leak under nine style nits.
