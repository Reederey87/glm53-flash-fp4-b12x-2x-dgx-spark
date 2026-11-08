# DeepSeek Harness throughput — 2026-11-08

**Observation:** 45 tok/s reported by the DeepSeek Harness UI while driving this
deployment (`nvidia/GLM-5.3-Flash-FP4-Local`, 1M context, MTP-5, reasoning
default Max).

## What the server measured at the same time

vLLM logs a 10-second `Avg generation throughput` window. Over the harness
session on this boot (`docker logs --since 3h vllm_node`, 104 windows):

| statistic | tok/s |
|---|---:|
| min | 0.0 (idle windows) |
| p50 | 29.0 |
| p90 | 35.1 |
| **max** | **46.5** |

Peak window, verbatim:

```
INFO 11-08 15:52:51 [loggers.py:315] Engine 000: Avg prompt throughput: 0.0 tokens/s,
Avg generation throughput: 46.5 tokens/s, Running: 1 reqs, Waiting: 0 reqs,
GPU KV cache usage: 6.8%, Prefix cache hit rate: 73.7%
```

## How to read it

- The 45 tok/s is an **interactive client rate**, consistent with the server's
  peak 10-second window (46.5 tok/s), not with its median (29.0). Short agent
  turns and UI smoothing bias the visible number toward the fast windows.
- It includes reasoning tokens: the template defaults to `Reasoning Effort: Max`,
  so a turn that thinks produces tokens that the UI may or may not count as
  output.
- Prefix cache was warm (73.7–80.2%), which is the normal agent-loop case.
- It is **not** comparable to the controlled matrix in
  `receipts/speed-*.json`, which uses cache-cold unique prompts, a fixed
  200-token budget, and no concurrent traffic: c1 27.80 tok/s, c8 58.64 tok/s
  aggregate. Use that matrix for adoption/revert decisions; use this number as
  the interactive experience it is.

Reproduce the distribution on the head:

```bash
docker logs --since 3h vllm_node 2>&1 \
  | grep -o 'Avg generation throughput: [0-9.]*' | cut -d' ' -f4 \
  | python3 -c 'import sys; v=sorted(map(float,sys.stdin)); n=len(v);
print(f"n={n} p50={v[n//2]} p90={v[int(n*.9)]} max={v[-1]}")'
```
