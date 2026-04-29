# Error handling and retries

n8n's error model is layered. Use all three layers; skipping any one creates blind spots.

## The three layers

**Layer 1: Node-level retry (transient failures)**

Every node has a Settings tab with `Retry On Fail`. Enable it for any node that calls an external API. Defaults that work:

- Max Tries: 3
- Wait Between Tries: 1000ms (or longer for known rate-limited APIs)

Built-in retry uses fixed wait times. For rate-limited APIs (DataForSEO, OpenAI, Anthropic, Google APIs), fixed retries can hammer the API and make the rate limit worse. Use exponential backoff instead, wrap the call in a Code node that doubles the wait between attempts:

```javascript
// Code node: exponential backoff
const maxTries = 3;
const baseDelay = 1000;
let lastError;

for (let attempt = 0; attempt < maxTries; attempt++) {
  try {
    const response = await this.helpers.httpRequest({
      method: 'GET',
      url: $input.first().json.url,
      json: true,
    });
    return [{ json: response }];
  } catch (error) {
    lastError = error;
    if (attempt < maxTries - 1) {
      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
throw lastError;
```

**Layer 2: Continue On Fail (handled failures)**

For nodes where you want to keep going even if one item fails (e.g., processing 100 emails, one bounces), enable `Continue On Fail` in node settings. The failed item gets routed to the error output (right side of the node, when `Settings → On Error → Continue Error Output` is set in v1.40+).

This is different from retry. Retry says "try again." Continue On Fail says "give up on this one and keep moving."

Common pattern: HTTP Request → Continue On Fail → IF (check `$json.error`) → branches for success vs. failure.

**Layer 3: Error Trigger workflow (catch-all)**

Every production workflow needs a separate Error Trigger workflow attached in `Workflow Settings → Error Workflow`.

Steps to set up:
1. Create new workflow named e.g. `Error Handler: Slack`
2. First node: `Error Trigger`
3. Second node: Set node that builds a clean alert payload (see template below)
4. Third node: Slack/Telegram/Email/Discord, whatever your team watches
5. Save and activate
6. In every other workflow: Settings → Error Workflow → select this one

Set node template:

```
workflow: {{ $json.workflow.name }}
failed_node: {{ $json.execution.lastNodeExecuted }}
error: {{ $json.execution.error.message }}
url: {{ $json.execution.url }}
mode: {{ $json.execution.mode }}
```

The execution URL is the most important field, it lets you click straight to the failure.

## What the Error Trigger receives

```json
{
  "workflow": { "id": "abc", "name": "My Workflow" },
  "execution": {
    "id": "123",
    "url": "https://your-n8n/workflow/abc/executions/123",
    "lastNodeExecuted": "HTTP Request",
    "error": { "message": "...", "stack": "..." },
    "mode": "trigger" | "manual" | "webhook"
  },
  "trigger": { ... }  // only present if the trigger itself failed
}
```

If the error originates in the trigger node (webhook never received, schedule misfired), `execution.id` and `execution.url` won't be present: the workflow never started. Handle this case: check `$json.execution?.url` before referencing it.

## Stop And Error node

When you want to deliberately fail a workflow (e.g., validation failed, business logic rejected the input), use the `Stop And Error` node. It fails the execution, which triggers the Error Workflow. Don't throw raw `Error()` from a Code node when you mean "stop the workflow". Stop And Error is clearer and surfaces a custom message.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Error Trigger workflow not attached → silent failures | Attach in Workflow Settings, even for "test" workflows |
| Same retry settings on every node regardless of upstream rate limit | Tune per-node based on the API |
| `Continue On Fail` everywhere → errors get swallowed | Use it deliberately, with an explicit error branch |
| Generic alert "workflow failed" → can't debug without logging in | Include execution URL in every alert |
| Testing the Error Trigger via manual run | Error Triggers only fire on automatic executions; test by deliberately breaking a node and triggering the parent workflow |

## Audit checklist for error handling

- [ ] Error Workflow is set in Workflow Settings
- [ ] Error Workflow includes execution URL in its alert
- [ ] All HTTP Request / API nodes have `Retry On Fail` enabled
- [ ] Rate-limited APIs use exponential backoff, not fixed retry
- [ ] Critical decision points use `Stop And Error`, not silent skips
- [ ] Webhook triggers validate input shape before business logic
