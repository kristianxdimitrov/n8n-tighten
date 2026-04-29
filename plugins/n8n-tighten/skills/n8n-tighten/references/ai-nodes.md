# AI and LLM nodes

n8n has dedicated nodes for OpenAI, Anthropic, Google, and a generic AI Agent node that supports multiple providers and tools. Choose nodes based on the use case, not what you used last time.

## Choosing a node

| Use case | Node |
|----------|------|
| One-shot prompt → completion | OpenAI / Anthropic chat node |
| Multi-turn conversation with memory | AI Agent + Memory node |
| LLM picks from tools/calls APIs | AI Agent + Tool nodes |
| Embeddings for vector search | Embeddings node + Vector Store node |
| Structured output (JSON) | OpenAI/Anthropic with response_format or Output Parser |

The AI Agent node is heavier-weight than a plain chat node. Don't reach for it when you just need "send prompt, get text back."

## Choosing a model

The default is rarely the right choice. Decision tree:

**Default first try:** small fast model (GPT-4o-mini, Claude Haiku, Gemini Flash). If output quality is acceptable, ship it, token cost is roughly 10x lower than frontier models.

**Upgrade when:** the small model fails on edge cases, you need long-context reasoning, or you need multimodal (vision/audio) and the small model doesn't support it.

**Frontier models** (GPT-4o, Claude Sonnet/Opus, Gemini Pro): use for complex reasoning, code generation, nuanced writing tasks, or when output quality directly impacts business metrics.

For high-volume background tasks (batch processing, classification, extraction), small models almost always win on cost-per-task.

## Prompt structure

Most LLM nodes have separate fields for system prompt and user prompt. Use them as designed:

- **System prompt**: role, output format, constraints, examples. Static across calls.
- **User prompt**: the variable input for this specific call.

Don't stuff everything into the user prompt with `{{ $json.description }}` interpolation, it makes prompts impossible to debug because the rendered prompt depends on runtime data.

Template:

```
System prompt:
You are [role]. Your task is to [outcome].

Output format:
[exact format spec, JSON schema, bullet structure, etc.]

Constraints:
- [constraint 1]
- [constraint 2]

Examples:
Input: [example input]
Output: [example output]

User prompt:
{{ $json.input_field }}
```

## Structured output

When the next node needs JSON, force JSON. Three options:

1. **Provider-native JSON mode** (OpenAI: `response_format: json_object`, Anthropic: tool use): most reliable
2. **Output Parser node**: parses LLM text response, can retry on parse failure
3. **Code node after the LLM**: `JSON.parse($json.output)` with try/catch

Don't trust freeform LLM output to be valid JSON without one of these. The model will helpfully add ```json fences or trailing commas at the worst possible moment.

## Token cost

Cost per call is dominated by:
1. Input token count (system + user prompt + any context)
2. Output token count (capped by max_tokens)
3. Model price tier

For batch workflows running 1000s of times per day, token cost can blow up fast. Cost-control patterns:

- Cache prompt prefixes when supported (OpenAI/Anthropic both offer prompt caching for repeated system prompts)
- Use the smallest model that meets quality bar, re-evaluate quarterly as new small models ship
- Cap `max_tokens` to the actual needed output length
- For classification, use logprobs/structured output instead of having the model write paragraphs explaining its choice

## AI Agent node specifics

The AI Agent node bundles: model + memory + tools + system prompt. It loops internally: model picks a tool, n8n runs the tool, result feeds back to the model, repeat until done.

Watch out:

- **Tool descriptions matter.** The model picks tools based on their `description` field. Vague descriptions = wrong tool choice. Write descriptions like you're explaining to a junior engineer who's never seen the API.
- **Memory eats tokens.** Conversation memory grows linearly. For long-running agents, use summarizing memory or truncate to last N turns.
- **Loop limits.** Set `Max Iterations` (default 10). Without it, a confused agent can spin forever and burn tokens.
- **Errors in tools propagate weirdly.** If a tool throws, the agent sees the error message as input and may try a different tool. Make tool errors actionable (e.g., "API returned 401: credential needs refresh") so the model can recover or escalate properly.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using GPT-4o for simple classification → 10x overspend | Switch to Haiku/Mini for high-volume tasks |
| Free-form output where downstream needs JSON → parse failures | Use JSON mode or Output Parser |
| Stuffing everything in user prompt → impossible to debug | Split system vs. user prompt |
| AI Agent with no Max Iterations cap → runaway loops | Set max iterations + add cost alerting |
| Not testing prompts on edge cases before deploying | Build a small eval set, run before each prompt change |

## Audit checklist for AI nodes

- [ ] Model choice justified, not "GPT-4 because that's what I always use"
- [ ] System prompt is static; user prompt holds the variable input
- [ ] Structured output uses JSON mode or a parser, not regex on freeform text
- [ ] `max_tokens` set to actual need, not 4096 default
- [ ] Agent nodes have `Max Iterations` capped
- [ ] Token cost has been ballparked for expected daily volume
