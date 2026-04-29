---
description: Run the static linter on an exported n8n workflow JSON file
argument-hint: [path/to/workflow.json]
allowed-tools: Bash
---

Run the n8n-tighten static linter on the workflow JSON file at: $ARGUMENTS

Execute this command:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/lint_workflow_json.py" "$ARGUMENTS"
```

The linter checks for:
- **Critical:** hardcoded API keys (OpenAI, Anthropic, GitHub, Slack, Google, AWS patterns)
- **High:** webhooks without authentication, HTTP nodes without retry on fail, schedule triggers with no workflow timezone set
- **Medium:** default-style node names ("HTTP Request2"), workflows with more than 15 nodes that should be split
- **Low:** schedule triggers firing on the minute boundary

After the linter runs, summarize the findings for the user grouped by severity. If the linter returned exit code 1, surface that critical issues block CI. Suggest concrete fixes for each finding rather than restating the linter's terse output.

If `$ARGUMENTS` is empty or the file path doesn't exist, ask the user for a valid path before running anything.
