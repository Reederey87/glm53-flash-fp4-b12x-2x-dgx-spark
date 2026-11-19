# 66 — 1M-context retrieval qualification

**Date:** 2026-11-19 · **Engine:** native Flare production (`b12x-flare-production.service`)
**Host:** kernel `7.0.0-1025-nvidia`, driver `580.178.04`, ConnectX-7 `28.50.1002`

## Why this exists

The README advertises a **1,048,576-token** context. The only retained retrieval
evidence used prompts of **~10,466 tokens**, and the fixture those receipts pin
(`5a255503…`) is present in neither the repository nor the runtime tree, so it
cannot be replayed. The claim had never been exercised anywhere near its limit.

## Method

`scripts/flare_context_retrieval.py` — self-contained, states its own method:

- One deterministic haystack sized to a token target; **979,581 prompt tokens**
  observed in `usage` (target 980,000; 4,712,926 characters at the measured 4.81
  chars/token).
- **200 decoy codes** of the identical form planted at other sections, so the task
  is selecting the right code among look-alikes rather than spotting the one
  unusual sentence (RULER multi-key setting).
- Three target codes at **5% / 50% / 95%** depth, one query each, then **one
  multi-query** that must return all three.
- `reasoning_effort=low`, `temperature=0`, `max_tokens=1024`, `finish_reason`
  recorded so a truncated stream can never be scored as a retrieval failure.
- Raw text is never written out: hashes, usage counters and verdicts only.

Receipt: `receipts/context-retrieval-1m-20261119.json`.

## Result — passes

| Query | Depth | Section | Found | Finish | Elapsed | Cached tokens |
| --- | --- | --- | --- | --- | ---: | ---: |
| single | 5% | 1214 | **yes** | stop | 518.8 s | 0 |
| single | 50% | 12149 | **yes** | stop | 529.7 s | 0 |
| single | 95% | 23084 | **yes** | stop | 524.9 s | 9 |
| multi (all 3) | — | — | **yes, 3/3** | stop | 521.1 s | 9 |

No truncation, no empty answers, and the answer to the multi-query was 65
completion tokens — it returned the codes without eliding any.

Retrieval therefore holds at **979,581 tokens** at the start, middle and end of the
context, with 200 look-alike distractors, for a single needle and for three at
once. This matches published findings that single-needle retrieval at 1M is
largely solved for current models, and that the harder discriminators are
multi-hop and aggregation.

## The operational finding: no prefix reuse at 1M

`cached_tokens` was **0, 0, 9, 9**. The 980k prefix is not retained, so **every
turn repays a full ~520-second prefill** (~1,888 tok/s). For an agent session that
re-sends a long conversation each turn, that is the dominant cost, not decode.

The likely mechanism is retention capacity rather than the pool: the engine reports
**183–184 shared snapshot slots**, and a 980k-token prefix spans ~3,830 pages, far
more than the slot count. Worth confirming against the pinned source, and worth a
separate exploration of `--prefix-cache-*` / disk retention if long-context agent
traffic is a real use case.

## Limits of this result

- **979,581 of 1,048,576 tokens** (93%). A full-window probe was not run: it costs
  another ~9 minutes per query and the pool must hold the prefix.
- One haystack, one nonce, one repetition per depth. This is a qualification
  smoke, not a benchmark: no confidence interval, and RULER-style aggregation and
  multi-hop tasks were not attempted.
- Synthetic filler. Real documents contain passages that look relevant, which is
  harder than look-alike codes.
- A pass here does **not** establish that 1M context is usable for reasoning, only
  that verbatim retrieval survives the window.
