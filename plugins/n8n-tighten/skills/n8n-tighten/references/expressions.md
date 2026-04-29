# Expression syntax and data flow

n8n expressions are JavaScript inside `{{ }}`. They're evaluated at runtime against the current item's data and the workflow's execution context.

## The basics

| Syntax | Meaning |
|--------|---------|
| `{{ $json.field }}` | Field on current item |
| `{{ $json["field with spaces"] }}` | Bracket notation for awkward field names |
| `{{ $('Node Name').item.json.field }}` | Field from another node, current item |
| `{{ $('Node Name').first().json.field }}` | First item from another node |
| `{{ $('Node Name').all() }}` | All items from another node (array) |
| `{{ $node["Node Name"].json.field }}` | Older syntax, still works, but `$()` is preferred |
| `{{ $now }}` | Luxon DateTime, current time |
| `{{ $env.VAR_NAME }}` | Environment variable |
| `{{ $items() }}` | All items entering the current node |
| `{{ $itemIndex }}` | Index of current item |
| `{{ $execution.id }}` | Current execution ID |
| `{{ $workflow.id }}` | Current workflow ID |

## The most common mistake: webhook data

Webhook nodes wrap incoming data, payload is at `$json.body`, not `$json`.

```
❌ {{ $json.email }}              // undefined
✅ {{ $json.body.email }}          // works
```

The full webhook structure:
```json
{
  "headers": { ... },
  "params": { ... },     // URL path params
  "query": { ... },      // querystring
  "body": { ... }        // POST/PUT body, your actual payload
}
```

When debugging "why is my expression undefined," check whether the source is a webhook and whether you've remembered the `.body` prefix.

## `$node[]` vs `$()`: they're not identical

Both reference data from previous nodes. Differences:

- `$node["Name"]`, older syntax, still supported, returns full node output structure
- `$('Name').item`, newer syntax, returns single paired item (recommended for most cases)
- `$('Name').first()`, explicitly first item
- `$('Name').all()`, explicit array of all items
- `$('Name').itemMatching(idx)`, item at specific index

The expression builder generates `$()` syntax by default. Stick with it unless you hit a known regression.

**Known regression:** in some versions, `$('NodeName').item` fails downstream of a Merge node when the data came from inputs 2+. If you see `"Can't determine which item to use"`, switch to `$('NodeName').first()` or `$node["NodeName"].json` as a workaround.

## Data flow: items, not records

n8n's atomic unit is the **item**, not the record. An item is `{ json: {...}, binary: {...}, pairedItem: {...} }`.

When a node receives 100 items, downstream nodes run 100 times, once per item. Most nodes operate per-item automatically; you rarely need to think about the array.

When you DO need the full array (e.g., "send the entire list to one Slack message"):

```javascript
// Code node, collapse all items into one
const allItems = $input.all();
const summary = allItems.map(i => i.json.title).join('\n');
return [{ json: { summary } }];
```

Returning `[{ json: { ... } }]` (one-element array) collapses 100 items into 1 downstream.

## Paired items

When a node produces output, n8n tracks which input item produced which output item via `pairedItem`. This is what makes `$('UpstreamNode').item` work. n8n traces back through the paired item chain.

The chain breaks when:
- A Code node returns items without preserving `pairedItem`
- A Merge node combines streams in modes that don't preserve pairing
- An aggregation collapses many items to one

When pairing breaks, `$('Name').item` errors out with "Can't determine which item to use." Fixes:

1. Use `$('Name').first()` if you want the first item explicitly
2. Use `$('Name').itemMatching($itemIndex)` if pairing is sequential
3. In a Code node, preserve `pairedItem`:
   ```javascript
   return $input.all().map((item, i) => ({
     json: { ... transformed ... },
     pairedItem: { item: i }
   }));
   ```

## Common syntax errors

| Wrong | Right | Why |
|-------|-------|-----|
| `$json.field` | `{{ $json.field }}` | Missing braces, treated as literal text |
| `{$json.field}` | `{{ $json.field }}` | Single brace, invalid |
| `{{{ $json.field }}}` | `{{ $json.field }}` | Triple brace, invalid |
| `{{ $json.field name }}` | `{{ $json["field name"] }}` | Bracket notation for spaces |
| `{{ $node[http request] }}` | `{{ $node["HTTP Request"] }}` | Quotes around node name; case-sensitive |
| `{{ $env.API_KEY }}` in HTTP creds | Use credential manager | Don't put secrets in expressions |

## Date/time with Luxon

`$now`, `$today`, and `DateTime` are Luxon objects, not vanilla JS Dates. Use Luxon syntax:

```javascript
{{ $now.toFormat('yyyy-MM-dd') }}              // 2026-04-29
{{ $now.toISO() }}                              // 2026-04-29T15:30:00.000+02:00
{{ $now.minus({ days: 7 }).toISO() }}           // a week ago
{{ $now.setZone('America/New_York').hour }}     // hour in NYC
{{ DateTime.fromISO($json.created_at).toFormat('LLL d') }}  // parse ISO string
```

Cheat sheet for format tokens: https://moment.github.io/luxon/#/formatting?id=table-of-tokens

## Defensive expressions

When data might be missing, use optional chaining and nullish coalescing:

```javascript
{{ $json.user?.email ?? 'unknown@example.com' }}
{{ $json.items?.[0]?.id }}
{{ ($json.amount ?? 0) * 1.2 }}
```

Don't rely on `||` for defaults when 0, false, or '' are valid values: use `??` instead.

## Audit checklist for expressions

- [ ] All expressions wrapped in `{{ }}`
- [ ] Webhook payloads accessed via `.body`, not root
- [ ] Node references use exact case-matched names with quotes
- [ ] Optional chaining used where data may be missing
- [ ] No secrets/API keys in expressions (use credential manager)
- [ ] Luxon syntax for date math, not raw `new Date()`
- [ ] No double-loops (don't iterate items that n8n is already iterating)
