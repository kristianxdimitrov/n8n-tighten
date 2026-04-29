---
description: Build a new production-grade n8n workflow from a description
argument-hint: [description-of-workflow-to-build]
---

Build a new n8n workflow according to this description: $ARGUMENTS

Follow the build workflow defined in the n8n-tighten skill:

1. **Clarify the trigger** if not obvious from the description. Webhook? Schedule? Manual? Form? Each has different concerns.
2. **Map the happy path** as 5-10 plain-English steps before writing any JSON. If you can't fit it in 10 steps, propose splitting into two workflows.
3. **Identify failure modes** for each step: transient (retry), permanent (route to error branch), fatal (stop and alert).
4. **Choose nodes** preferring dedicated nodes over generic HTTP Request when both exist. With MCP available, use `search_nodes` to discover relevant nodes and `get_node` to verify current parameters.
5. **Write the workflow.**
   - With MCP: use `n8n_create_workflow` to write directly to the user's instance. Validate with `n8n_validate_workflow` after creation. Return the workflow ID and link, not the JSON.
   - Without MCP: output JSON in a code block. The user imports via `workflow menu → Import from JSON`.
6. **Wire the Error Trigger.** Always. With MCP, this can be a separate `n8n_create_workflow` call for the Error Handler workflow.

If the description is empty or too vague, ask one focused clarifying question before proceeding. Don't guess critical details like which trigger fires the workflow.

Always include error handling, retries, and credential hygiene from step one. Never produce a workflow with hardcoded API keys or no Error Trigger.
