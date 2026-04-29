# n8n-tighten

A [Claude Skill](https://code.claude.com/docs/en/skills) and [Claude Code plugin](https://code.claude.com/docs/en/plugins) that tightens loose [n8n](https://n8n.io) workflows, and helps you build new ones that ship tight from day one.

When installed, Claude treats n8n questions as a structured engineering task, checking for silent failures, credential hygiene, modular architecture, and rate-limit safety before declaring a workflow "done." It works in two modes:

- **Tighten**: point Claude at an existing workflow (via the n8n MCP server, a pasted JSON export, or just a description) and get a severity-ranked list of loose ends with concrete fixes
- **Build**: describe what you want, get a workflow JSON with error handling, retries, and credential safety bolted on from the start, written directly into your n8n instance if MCP is connected, otherwise as importable JSON

## What it covers

- Three-layer error handling (node retries → workflow Error Trigger → centralized alerting)
- Loop architectures (Split In Batches, sub-workflows, pagination patterns)
- AI/LLM nodes (model selection, prompt structure, token cost, agent loop safety)
- Expression syntax (`$json`, `$node`, `$()`, paired items, webhook nesting gotchas)
- Webhook and schedule trigger patterns (idempotency, signature verification, timezone handling)
- Credential hygiene (credential manager vs. env vars, rotation, webhook auth)

Plus a standalone Python linter (`scripts/lint_workflow_json.py`) that statically checks exported workflow JSON for hardcoded secrets, missing retries, missing timezones, default node names, and other audit-checklist items. Slots into pre-commit or CI.

## Install

Pick whichever fits your environment.

### Claude Code (recommended): install as a plugin

In Claude Code, add this repo as a marketplace, then install the plugin:

```
/plugin marketplace add kristianxdimitrov/n8n-tighten
/plugin install n8n-tighten@n8n-tighten
```

The skill loads automatically when you ask Claude about n8n. Update later with:

```
/plugin marketplace update n8n-tighten
```

### Claude Code: install as a plain skill (no marketplace)

If you'd rather skip the plugin layer, drop just the skill folder into your skills directory:

```bash
git clone https://github.com/kristianxdimitrov/n8n-tighten.git
cp -r n8n-tighten/plugins/n8n-tighten/skills/n8n-tighten ~/.claude/skills/
```

### Claude.ai (Pro / Team / Enterprise)

Zip the inner skill folder and upload via Settings → Customize → Skills:

```bash
git clone https://github.com/kristianxdimitrov/n8n-tighten.git
cd n8n-tighten/plugins/n8n-tighten/skills
zip -r n8n-tighten.zip n8n-tighten/
```

Then in Claude.ai: `Customize → Skills → "+ Create skill"` and upload the zip.

## Connecting to your n8n instance

The skill works with three input paths, pick whichever matches your setup. The MCP path is the most powerful (Claude reads, audits, and writes workflows directly), but JSON paste and plain-English description both work fine without any extra setup.

### Option 1: n8n MCP server (recommended for active n8n users)

[`czlonkowski/n8n-mcp`](https://github.com/czlonkowski/n8n-mcp) is a Model Context Protocol server that exposes your n8n instance as a set of tools Claude can call. With it connected, Claude can list workflows, read their JSON, run n8n's own validators, apply diffs, and even create new workflows on your instance, no copy-paste required.

Quick setup (Claude Code):

```bash
claude mcp add n8n-mcp \
  -e MCP_MODE=stdio \
  -e LOG_LEVEL=error \
  -e DISABLE_CONSOLE_OUTPUT=true \
  -e N8N_API_URL=https://your-n8n-instance.com \
  -e N8N_API_KEY=your-api-key \
  -- npx n8n-mcp
```

Generate the API key in n8n under `Settings → API → Create an API Key`, and replace the URL with your instance address. Without API credentials, the server still works but only exposes documentation and validation tools. You'll need them to read or modify workflows. Full setup options (Claude Desktop, Docker, Railway, self-hosted) are in the [n8n-mcp Claude Code setup guide](https://github.com/czlonkowski/n8n-mcp/blob/main/docs/CLAUDE_CODE_SETUP.md).

Once connected, you can say things like:

- *"Tighten workflow `<workflow-id>`, check for silent failures and missing retries."*
- *"List all my active workflows that don't have an Error Trigger attached."*
- *"Update the Slack node in `<workflow-id>` to use exponential backoff instead of fixed retry."*
- *"Create a new workflow that watches my GitHub issues and posts a daily Slack digest."*

The skill will use the MCP tools (`n8n_get_workflow`, `n8n_validate_workflow`, `n8n_update_partial_workflow`, etc.) automatically. You don't have to name them.

> **Safety note from the n8n-mcp project:** never let Claude edit production workflows directly. Duplicate first, audit/edit on the copy, review the diff, then merge yourself.

### Option 2: paste workflow JSON

If you don't want to wire up MCP, just export the workflow from n8n (`workflow menu → Download`) and paste the JSON into chat. The skill runs the same audit checklist against the static JSON.

```
"Here's my workflow, tighten it:

[paste JSON]"
```

### Option 3: describe in plain English

For build-from-scratch tasks, you don't need any connection at all. Describe what you want and the skill produces an importable JSON (`workflow menu → Import from JSON`).

```
"Build me a workflow: webhook receives Stripe events, verify signature,
look up customer in Postgres, post to Slack on payment_failed."
```

## Use

Once installed, the skill triggers automatically when you ask Claude about n8n. Example prompts across all three input paths:

**With MCP connected:**
- *"Audit my active workflows and rank them by production-readiness."*
- *"Find every workflow on my instance with hardcoded API keys."*
- *"Add an Error Trigger to all my scheduled workflows."*

**With pasted JSON:**
- *"Here's my workflow JSON, audit it for production readiness."*
- *"This workflow scans 2TB on every run, fix it."*

**No connection (plain English):**
- *"Build me an n8n workflow that pulls new GitHub issues, classifies them with an LLM, and posts a daily digest to Slack."*
- *"My Split In Batches loop runs forever, what's wrong?"*
- *"How do I verify the Stripe signature on a webhook in n8n?"*

### Run the linter on exported workflows

For workflows tracked in version control, the bundled Python linter checks JSON files statically, no Claude required:

```bash
python plugins/n8n-tighten/scripts/lint_workflow_json.py path/to/workflow.json
```

Returns exit code 1 if it finds critical issues, drop it in pre-commit or CI to keep workflow JSON honest.

## Structure

```
n8n-tighten/                              ← repo root
├── .claude-plugin/
│   └── marketplace.json                       ← Claude Code marketplace catalog
├── plugins/
│   └── n8n-tighten/                      ← the plugin
│       ├── .claude-plugin/
│       │   └── plugin.json                    ← plugin manifest
│       ├── scripts/
│       │   └── lint_workflow_json.py          ← static linter (CI-friendly)
│       └── skills/
│           └── n8n-tighten/              ← the skill itself (drop-in for plain-skill install)
│               ├── SKILL.md                   ← entry point, dispatches to references
│               ├── references/
│               │   ├── error-handling.md
│               │   ├── loops.md
│               │   ├── ai-nodes.md
│               │   ├── expressions.md
│               │   ├── webhooks-and-schedules.md
│               │   └── credentials.md
│               └── examples/
│                   └── audit-checklist.md
├── LICENSE                                    ← MIT
└── README.md                                  ← this file
```

## Versioning and n8n compatibility

Patterns target **n8n v1.30+** (Community Edition and Cloud). Older versions may have minor expression syntax differences, `references/expressions.md` calls out known regressions. The skill prefers stable, current patterns over deprecated ones.

## Contributing

PRs welcome, especially for:
- New audit checks discovered in production
- Patterns for nodes/integrations not yet covered
- Fixes for n8n version-specific gotchas

Keep additions consistent with the structure: short SKILL.md, focused reference files, concrete checklists over vague guidance.

To bump versions on release: update `version` in both `.claude-plugin/marketplace.json` and `plugins/n8n-tighten/.claude-plugin/plugin.json`. Users won't get auto-updates unless this changes.

## License

MIT, see [LICENSE](LICENSE).

## Acknowledgments

Built on patterns from the n8n docs, the [n8n community forum](https://community.n8n.io), and lessons from running production n8n at scale. Inspired by the format of [Anthropic's example skills](https://github.com/anthropics/skills) and [@czlonkowski's n8n-skills repo](https://github.com/czlonkowski/n8n-skills).
