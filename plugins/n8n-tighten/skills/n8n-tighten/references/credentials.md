# Credentials and environment variables

The single biggest security mistake in n8n workflows is putting secrets in the wrong place. Get this right and most other security worries become smaller.

## The credential manager

n8n has a dedicated credential system (`Credentials` in the left sidebar). Every node that needs auth supports loading from credentials. Use it for:

- API keys
- OAuth tokens
- Database passwords
- SMTP passwords
- Any secret your workflow needs

Credentials are encrypted at rest with the n8n encryption key (set via `N8N_ENCRYPTION_KEY` env var). They're scoped per-credential. You can grant a workflow access to one credential without exposing others.

### Why not env vars for secrets

n8n supports `$env.MY_SECRET` in expressions. **Don't use this for secrets.** Reasons:

1. Env vars in expressions show up in execution logs
2. They show up in workflow exports (sharing a workflow shares your secrets)
3. They show up in error messages when something fails
4. They bypass n8n's credential rotation and audit features

Use `$env` for **non-secret config**: feature flags, environment names, log levels. Use the credential manager for anything sensitive.

### What hardcoded credentials look like

These are red flags during an audit:

```
❌ HTTP Request → Authentication: None → Headers → Authorization: Bearer sk-abc123...
❌ Code node: const apiKey = "sk-abc123...";
❌ Set node: api_key = sk-abc123...
❌ HTTP Request → URL: https://api.service.com?api_key=abc123
```

What it should look like:

```
✅ HTTP Request → Authentication: Generic Credential Type → Header Auth → (select credential)
✅ HTTP Request → Authentication: Predefined Credential Type → OpenAI account → (select credential)
✅ Code node uses a Credential field if the API needs it
```

## Environment variables (for non-secrets)

`$env.VAR_NAME` accesses environment variables set in the n8n process.

Good uses:
- `$env.ENVIRONMENT` → "production" / "staging", for routing logic
- `$env.SLACK_CHANNEL_ALERTS` → channel name (not the webhook URL, that goes in credentials)
- `$env.FEATURE_FLAG_NEW_FLOW` → toggling experimental code paths
- `$env.SUPPORT_EMAIL` → ops contact

Set them via:
- Docker: `-e VAR_NAME=value` or in `docker-compose.yml`
- n8n Cloud: Settings → Environment Variables (Enterprise)
- Self-hosted: shell env or `.env` file loaded by your process manager

## Credential scoping (Enterprise)

If you're on n8n Enterprise / Cloud Pro, credentials support **sharing controls**:

- Per-credential access by user/role
- Per-project credential scoping
- Credential ownership tracking

Audit principle: production credentials should only be accessible to workflows that need them. The intern's test workflow does not need the production Stripe key.

## Rotation

Plan for credential rotation from day one. When you rotate:

1. Create new credential in n8n (don't edit the existing one)
2. Update workflows to point to the new credential, usually one-by-one to validate
3. Keep old credential active until all workflows are switched
4. Revoke old credential at the source (Stripe dashboard, etc.)
5. Delete old credential from n8n

Don't edit a credential's value in place. If a workflow breaks during rotation, you need a way to revert.

## Webhook authentication

Webhook nodes support inbound auth (verifying the caller is authorized):

- **Header Auth**: caller must include a specific header value
- **Basic Auth**: username/password
- **JWT**: verifies a JWT signature

Use these when external services call your n8n webhook. Don't make webhooks publicly callable without auth unless the workflow is designed to handle untrusted input (e.g., a public form intake that does heavy validation downstream).

## Code node and credential access

The Code node can access credentials via `this.getCredentials("credentialName")` (in n8n internal API). For most cases, prefer using a dedicated node. It's harder to leak credentials accidentally from a Code node into logs.

If you must call an authed API from a Code node:

```javascript
const creds = await this.getCredentials('myApi');
const response = await this.helpers.httpRequest({
  method: 'GET',
  url: `https://api.example.com/data`,
  headers: { 'Authorization': `Bearer ${creds.token}` }
});
return [{ json: response }];
```

Never `console.log` credentials. Code node logs go to execution data and can be exported.

## Workflow exports

When you export a workflow as JSON (for sharing, version control, backup), n8n strips credential **values** but keeps **references** by ID. So a shared workflow JSON file is safe to commit to a public repo IF:

- All credentials are managed via the credential manager (not hardcoded)
- No `$env` references with secret-looking values
- No secrets in Code node source code

Always re-scan workflow exports before publishing or committing.

## The n8n API key (MCP and external integrations)

When you use the n8n MCP server or any external tool that talks to your n8n instance, you generate an n8n API key under `Settings → API → Create an API Key`. This is itself a credential that protects your entire instance. Anyone with it can read, modify, and delete workflows.

Treat the n8n API key the same as any other production secret:

- Store it in your shell environment, MCP config, or secrets manager, never commit it to git
- Scope it down: if your version of n8n supports per-API-key permissions, give the MCP read-only access for audit-only workflows; only grant write access when you're actively building
- Rotate it on a schedule, and immediately if a developer leaves the team
- Use a separate API key for dev/staging vs. production, don't share keys across environments
- Audit `~/.claude.json` (Claude Code config) for committed API keys before pushing dotfiles to a public repo

## Common mistakes

| Mistake | Fix |
|---------|-----|
| API key hardcoded in HTTP Request header | Move to credential manager |
| API key in `$env.API_KEY` | Move to credential manager |
| Same credential used by 50 workflows, no rotation plan | Document credentials, set quarterly rotation |
| Secrets in Code node source | Use `getCredentials()` or a dedicated node |
| Webhook with no auth, accepting destructive operations | Add Header Auth or signature verification |
| Workflow JSON committed with hardcoded creds | Audit before committing; use credential refs only |
| `console.log` of credential value during debugging | Never. Even temporarily. |

## Audit checklist for credentials

- [ ] Zero hardcoded API keys in node parameters or Code nodes
- [ ] Zero `$env.SECRET_NAME` references for secrets, only for non-secret config
- [ ] All authed nodes use the credential manager
- [ ] Webhooks accepting destructive operations have authentication
- [ ] `N8N_ENCRYPTION_KEY` is set (otherwise credentials are not encrypted at rest)
- [ ] Credentials have descriptive names, `Stripe: Production` not `Stripe1`
- [ ] No credentials shared between dev/staging/production environments
- [ ] n8n API key (used by MCP/external tools) is scoped, rotated, and not committed to git
