#!/usr/bin/env python3
"""
Static linter for exported n8n workflow JSON.

Catches a handful of common production-readiness issues without needing
the n8n MCP server or a live n8n instance. Use it as a pre-commit hook
or CI step on workflow JSON files in version control.

Usage:
    python lint_workflow_json.py path/to/workflow.json
    python lint_workflow_json.py path/to/workflows/*.json
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

# Regex for things that look like API keys / tokens hardcoded in fields
SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style API key"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "Anthropic API key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub personal access token"),
    (r"xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+", "Slack bot token"),
    (r"AIza[A-Za-z0-9_-]{30,}", "Google API key"),
    (r"AKIA[A-Z0-9]{16}", "AWS access key ID"),
]


class Finding:
    SEVERITIES = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def __init__(self, severity: str, node: str, message: str):
        self.severity = severity
        self.node = node
        self.message = message

    def __repr__(self):
        return f"[{self.severity.upper()}] ({self.node}) {self.message}"

    def sort_key(self):
        return (self.SEVERITIES.get(self.severity, 99), self.node)


def walk_strings(obj: Any, path: str = ""):
    """Yield (path, string_value) for every string in a nested structure."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")


def lint_workflow(workflow: dict) -> list[Finding]:
    findings: list[Finding] = []
    nodes = workflow.get("nodes", [])
    settings = workflow.get("settings", {})

    # --- Critical checks -------------------------------------------------

    # 1. Hardcoded secrets in any node parameter
    for node in nodes:
        node_name = node.get("name", "<unnamed>")
        for path, val in walk_strings(node.get("parameters", {})):
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, val):
                    findings.append(Finding(
                        "critical",
                        node_name,
                        f"Hardcoded {label} found at parameters.{path}. Move to credential manager.",
                    ))

    # 2. Webhook nodes accepting destructive operations without auth
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.webhook":
            params = node.get("parameters", {})
            if params.get("authentication") in (None, "none", ""):
                findings.append(Finding(
                    "high",
                    node.get("name", "<unnamed>"),
                    "Webhook has no authentication configured. Add Header Auth, Basic Auth, or signature verification.",
                ))

    # 3. Schedule trigger without timezone set on workflow
    has_schedule_trigger = any(
        n.get("type") in (
            "n8n-nodes-base.scheduleTrigger",
            "n8n-nodes-base.cron",
        )
        for n in nodes
    )
    if has_schedule_trigger and not settings.get("timezone"):
        findings.append(Finding(
            "high",
            "<workflow settings>",
            "Schedule trigger present but workflow timezone not set. Set in Workflow Settings → Timezone.",
        ))

    # --- High checks -----------------------------------------------------

    # 4. HTTP Request nodes without retry on fail
    for node in nodes:
        if node.get("type") == "n8n-nodes-base.httpRequest":
            if not node.get("retryOnFail"):
                findings.append(Finding(
                    "high",
                    node.get("name", "<unnamed>"),
                    "HTTP Request node has no retry on fail. Enable in node Settings.",
                ))

    # --- Medium checks ---------------------------------------------------

    # 5. Nodes with default-style names ("HTTP Request", "HTTP Request1", "Code", "Code1", etc.)
    default_name_pattern = re.compile(
        r"^(HTTP Request|Code|Function|Set|IF|Webhook|Schedule Trigger)\d*$"
    )
    for node in nodes:
        name = node.get("name", "")
        if default_name_pattern.match(name):
            findings.append(Finding(
                "medium",
                name,
                f"Node has a default-style name. Rename to describe what it does.",
            ))

    # 6. Workflow has > 15 nodes (extract sub-workflows)
    if len(nodes) > 15:
        findings.append(Finding(
            "medium",
            "<workflow>",
            f"Workflow has {len(nodes)} nodes. Consider extracting sub-workflows (target: under 10 per workflow).",
        ))

    # --- Low checks ------------------------------------------------------

    # 7. Schedule on the minute boundary
    for node in nodes:
        if node.get("type") in (
            "n8n-nodes-base.scheduleTrigger",
            "n8n-nodes-base.cron",
        ):
            for path, val in walk_strings(node.get("parameters", {})):
                if isinstance(val, str) and re.match(r"^0\s+\*\s+\*\s+\*\s+\*$", val):
                    findings.append(Finding(
                        "low",
                        node.get("name", "<unnamed>"),
                        "Schedule fires on the minute boundary (`0 * * * *`). Consider offsetting (e.g., `7 * * * *`) to spread load.",
                    ))

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python lint_workflow_json.py <workflow.json> [more.json ...]")
        sys.exit(1)

    total_findings = 0
    exit_code = 0

    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"⚠ {path}: not found", file=sys.stderr)
            exit_code = 2
            continue

        try:
            workflow = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            print(f"⚠ {path}: invalid JSON ({e})", file=sys.stderr)
            exit_code = 2
            continue

        findings = lint_workflow(workflow)
        findings.sort(key=lambda f: f.sort_key())

        print(f"\n=== {path} ===")
        if not findings:
            print("  ✓ no issues found")
            continue

        for f in findings:
            print(f"  {f}")

        total_findings += len(findings)
        # Critical findings cause non-zero exit (good for CI)
        if any(f.severity == "critical" for f in findings):
            exit_code = 1

    print(f"\nTotal findings: {total_findings}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
