# Reasoning default — max

## Contract

GLM-5.3-Flash's chat template writes the reasoning level as the **first system
token** of the prompt:

```jinja
{%- set effective_reasoning_effort = reasoning_effort
      if reasoning_effort is defined and reasoning_effort in ['low', 'high']
      else 'max' -%}
{%- if effective_reasoning_effort is not none -%}
<|system|>Reasoning Effort: {{ effective_reasoning_effort | capitalize }}
{%- endif -%}
```

Consequences, all of them load-bearing:

1. A request that **omits** `reasoning_effort` gets **Max**. That is the default
   this kit promises, and `DEFAULT_REASONING_EFFORT=max` in `.env` records it.
2. Only `low` and `high` are accepted spellings; `max`, `medium`, or any other
   value falls through to `max`. Passing `max` explicitly is therefore
   equivalent to omitting the field.
3. The level is a prompt token, not a sampling parameter. It is part of the
   prefix, so it participates in prefix caching exactly like any other token.

## How it is enforced

`scripts/verify_reasoning.py` runs inside the engine container against the
mounted checkpoint tokenizer and fails unless:

- the default render contains `Reasoning Effort: Max`,
- explicit `low` / `high` / `max` render their own level,
- the prompt still starts with `[gMASK]<sop>`.

`./launch.sh smoke` calls it; the gate in `docs/03-gate.md` makes it a hard
requirement. A future checkpoint that changes the default will fail the smoke
instead of silently serving a lower reasoning budget.

## Client side

- Omit `reasoning_effort` to use Max.
- `chat_template_kwargs: {"reasoning_effort": "low"|"high"}` narrows one request.
- Do not send `"medium"` and expect medium; it resolves to Max.
- The `glm45` reasoning parser splits the thinking from the answer. This vLLM
  build returns it as `message.reasoning` (clients that expect the OpenAI-style
  `reasoning_content` should read either key); `content` holds the answer.
- Proof that thinking is on: `usage.completion_tokens_details.reasoning_tokens`
  is non-zero. If a request is cut by `max_tokens` **before** the model closes
  its thinking block, the parser has no answer boundary and both fields can come
  back empty while the tokens are still counted as reasoning — give short
  requests enough budget (measured: 512 tokens answered 17×23 with 155
  reasoning tokens).

## Why not force it with an override

An override would make explicit `low`/`high` impossible and would duplicate a
172-line template that the checkpoint owns. The contract above is checked, not
rewritten: the kit asserts the default rather than re-implementing the prompt.
