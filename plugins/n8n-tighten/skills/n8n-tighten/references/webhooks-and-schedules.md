# Webhooks and schedules

The trigger is the most overlooked part of a workflow. Get it wrong and you'll spend weeks chasing ghosts.

## Webhook trigger

Webhooks listen on a URL and fire when called. Two URLs per webhook:

- **Test URL**: works only when the workflow editor is open with "Listen for Test Event" active. For development.
- **Production URL**: works when the workflow is activated. For production.

These are different URLs. Test events do not fire production handlers. The most common deployment bug is configuring an external service (Stripe, Shopify, Typeform) with the test URL and wondering why nothing fires after deployment.

### Webhook path

By default n8n generates a UUID. Replace it with something descriptive (`stripe-payment-success`) so URLs are readable in logs and easier to audit. Be aware:

- Paths must be unique across the entire n8n instance
- Two workflows with the same path silently collide; whichever activated last wins
- Audit periodically, orphaned paths from deleted workflows can cause confusion

### Response modes

Three options under `Respond` setting:

| Mode | When to use |
|------|-------------|
| `Immediately` | Fire-and-forget, return 200 the moment the webhook fires. Best for async work. |
| `When Last Node Finishes` | Synchronous, caller waits for the workflow to complete. Use for chat-style requests. |
| `Using Respond to Webhook node` | Custom response, explicit Respond to Webhook node decides status, headers, body. |

For external services with retry logic (Stripe, Shopify), use `Immediately` and process async. Holding the webhook open for 30+ seconds risks the caller timing out and retrying, which can double-process your event.

### Idempotency

External services retry. Your webhook will receive the same event multiple times. Either:

1. **Check upstream event ID**: Set node early in the flow that records `event_id` to a database, IF node checks for duplicates, skip if seen
2. **Make downstream operations idempotent**: `INSERT ... ON CONFLICT DO NOTHING`, upserts, etc.
3. **Both**: belt and suspenders, recommended for payment workflows

### Authentication

For webhooks called by external services that support signatures (Stripe, GitHub, Shopify, Slack), verify the signature in the first node after the webhook. Don't trust the payload until verified.

Pattern:
1. Webhook receives request
2. Code node: compute HMAC of body using shared secret, compare to `X-Signature` header
3. If mismatch: Stop And Error
4. Otherwise: continue with business logic

For webhooks you call from your own systems, use Header Auth or Basic Auth in the webhook node settings.

## Schedule (Cron) trigger

The Schedule trigger fires on a schedule. Modes:

- **Every X minutes/hours**: simple intervals
- **Cron expression**: complex schedules (`0 9 * * MON-FRI` = 9am weekdays)
- **Specific times**: pick weekdays + time

### Timezone

The Schedule trigger uses the **workflow's timezone**, set in `Workflow Settings → Timezone`. If you don't set this, it uses the n8n instance default, which may not be what you want.

Always set the timezone explicitly on schedule-driven workflows. "Send daily report at 9am" means different things in UTC vs. PST vs. local.

### Catch-up after downtime

If n8n is down at 9am and recovers at 9:15am, the 9am schedule did NOT fire. n8n does not catch up missed schedules by default. For workflows where missed runs matter (daily reports, billing cycles), add a self-healing pattern:

1. Schedule trigger fires
2. First node: check last successful run timestamp (from a database or workflow static data)
3. If last run was > expected interval ago, process the catch-up window
4. Update last-run timestamp on success

### Cron expression gotchas

- `0 0 * * *` = daily at midnight (in workflow timezone)
- `*/5 * * * *` = every 5 minutes
- Be careful with `0 0 * * 0` (Sunday in some contexts, varies by Cron flavor). n8n uses node-cron, week starts Sunday=0
- Don't run heavy workflows on the minute boundary (`0 * * * *`): that's when everyone schedules and your n8n queue piles up. Pick `7 * * * *` or similar.

## Manual / Form / Chat triggers

- **Manual**: useful for testing and ad-hoc runs. Don't ship critical work behind manual triggers.
- **Form**: n8n hosts a simple form, fires the workflow on submit. Good for internal tools.
- **Chat**: embeddable chat UI, fires on each message. Used with AI Agent nodes.

For all three, treat input as untrusted. Validate before doing anything destructive.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Configured Stripe with test URL → no events in production | Always use production URL after activation |
| Two workflows with same webhook path | Audit paths regularly; rename collisions |
| 30+ second webhook hold time → caller retries → double processing | Switch to `Immediately` response, process async |
| No signature verification on webhook from external service | Add HMAC check as first node post-webhook |
| Schedule running in wrong timezone → reports off by hours | Set Workflow Settings → Timezone explicitly |
| Missed runs after n8n downtime → silently skipped | Add catch-up logic for time-sensitive schedules |
| Webhook accessed at `$json.email` instead of `$json.body.email` | Remember webhook nesting (see expressions.md) |

## Audit checklist for triggers

- [ ] Webhook URLs in external services point to **production** URL, not test
- [ ] Webhook paths are descriptive and unique across the instance
- [ ] Webhooks from external services verify signatures
- [ ] Response mode matches the use case (async vs. sync)
- [ ] Idempotency handled for retryable webhooks (payments, orders)
- [ ] Schedule triggers have Workflow Timezone set explicitly
- [ ] Time-sensitive schedules have catch-up logic for missed runs
- [ ] Manual triggers are not load-bearing for production processes
