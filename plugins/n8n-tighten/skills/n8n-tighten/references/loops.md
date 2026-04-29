# Loops and modular architecture

n8n's data model is item-based, most nodes process arrays of items in parallel. You don't need an explicit loop for "do this thing to every item." You need an explicit loop when you want batching, rate limiting, or per-item recursion.

## When you need an explicit loop

| Scenario | Solution |
|----------|----------|
| Process 1000 records but the API limits 10/second | `Split In Batches` with delay |
| API returns paginated results, fetch all pages | `Split In Batches` or recursive sub-workflow with `nextPageToken` |
| Need to retry per-item with custom backoff | Loop over items in a Code node |
| Workflow has > 10 nodes and is getting unwieldy | Extract sub-workflows via `Execute Sub-workflow` |

## When you do NOT need an explicit loop

If you have 100 items coming out of an HTTP Request and want to send each one to Slack, **you don't need a loop**. The Slack node will run once per item automatically. Adding `Split In Batches` here just slows things down.

This is the most common loop mistake, building Split In Batches around something n8n is already doing for you.

## Split In Batches

The standard batching pattern. Used when you need to:

- Throttle to N requests per second
- Process in chunks of N at a time
- Show progress (each batch = one execution log entry)

Setup:
1. `Split In Batches` node, Batch Size = 10 (or whatever fits your rate limit)
2. Process each batch (HTTP Request, etc.)
3. Wait node (e.g., 1 second) if needed
4. Loop back to Split In Batches

The "loop back" is done by connecting the last node in the batch processing chain back to the Split In Batches node. Split In Batches has two outputs: "loop" (more batches to do) and "done" (finished).

Critical: connect to **input 1** when looping back, not creating a new connection. The node tracks position internally.

## Sub-workflows (Execute Sub-workflow)

Once a workflow exceeds ~10 nodes, extract logical chunks into sub-workflows. Benefits:

- Each sub-workflow gets its own execution log → easier debugging
- Sub-workflows are reusable across parent workflows
- Each sub-workflow has its own Error Trigger (granular alerting)
- Smaller workflows = faster to load in the editor

When to extract:
- Repeated logic that appears in 2+ workflows → extract to shared sub-workflow
- A "step" that's conceptually one operation but takes 5+ nodes (e.g., "enrich lead" might be 6 nodes wrapping CRM + email validator + scoring)
- Anything you'd want to test in isolation

How to extract:
1. Create new workflow with `Execute Workflow Trigger` as the first node (it accepts input from the parent)
2. Move the nodes from the parent
3. Last node in the sub-workflow returns data via standard output
4. In parent, replace the moved nodes with `Execute Sub-workflow` node, point at the new workflow ID

Data passing: input items to the sub-workflow are accessed via `$json` like any other node. Output items become available to the next node in the parent workflow.

## Pagination loop pattern

Common API pattern: response includes a `nextPageToken` (or `cursor`, `next_url`, etc.) that you use to fetch the next page until null.

Cleanest implementation: recursive sub-workflow.

```
[Parent]
  HTTP Request (page 1) → Set (collect results) → Execute Sub-workflow (if nextPageToken)

[Sub-workflow: "Fetch more pages"]
  Execute Workflow Trigger → HTTP Request (using passed token) →
    IF (more pages?) → Execute Sub-workflow (recursive) → Merge → return all items
                    → return current page only
```

Alternative: Split In Batches over a synthetic counter, with a fixed max iteration cap as a safety net. Less elegant but harder to runaway-recurse.

## Anti-patterns

**Loop inside a loop inside a loop.** If you have nested Split In Batches, you almost certainly want a sub-workflow. Three levels of nesting is unreadable.

**No exit condition.** Pagination loops without a hard maximum iteration count can run forever if the API misbehaves. Always cap (e.g., max 100 pages).

**Loop over items the parent workflow already iterates.** Mentioned above. If a node receives 100 items, downstream nodes already run 100 times. Don't double-loop.

**Mutating workflow-global state from inside a loop.** n8n loops don't share state cleanly. Use a Set node before the loop to seed an accumulator, pass it through each iteration, return it at the end.

## Audit checklist for loops

- [ ] Every Split In Batches has an exit condition (loop terminates)
- [ ] Pagination loops have a max-page cap
- [ ] Workflows over 10 nodes have sub-workflows extracted
- [ ] No accidental "loop on top of n8n's automatic per-item processing"
- [ ] Wait nodes inside loops respect API rate limits (not just `Wait 1 second` cargo-culted)
