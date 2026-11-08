# Runbook

## Start / stop

```bash
# production (owns the memory gate + health gate)
systemctl --user start vllm-b12x.service
systemctl --user stop  vllm-b12x.service

# direct (development only; the gate still runs in preflight)
./launch.sh up
./launch.sh down
./launch.sh restart
```

`up` dispatches the worker first, then the head, and returns once the launcher
has handed off. The unit's `ExecStartPost` holds it in `activating` until
`/health` is 200 (900 s budget).

## Status and evidence

```bash
./launch.sh status     # containers, /health, model id, KV pool
./launch.sh smoke      # functional acceptance
./launch.sh speed      # 8k..128k prefill, decode c1..8, acceptance
./launch.sh qualify    # pinned bytes vs live bytes -> receipts/
./launch.sh logs       # head;  ./launch.sh logs worker
```

The first line of the boot log that matters is:

```
GPU KV cache size: 2,350,210 tokens
```

Anything materially below that means the KV pin, the block size, or the model
length changed.

## Failure modes seen on this pair

| Symptom | Cause | Action |
|---|---|---|
| Unit fails immediately, `MemAvailable <100GiB` | previous rank still holds the pool | `./launch.sh down`, wait for `MemAvailable` to recover, start again |
| Container exits with `NV_ERR_NO_MEMORY` | GB10 page-cache/driver allocation refusal | stop, `sync`, drop caches is **not** enough — restart the worker rank first, then head |
| `/health` fine, requests stall | one rank is loading/compiling | check `docker logs` on the worker; a cold boot takes ~4–6 min |
| `health=000` for one tick | long prefill | watchdog waits one tick before healing; do not restart manually |
| KV pool smaller than 2.3M | `max_model_len` or `kv_cache_bytes` edited | compare `./launch.sh render` with the recipe |

## Memory discipline

- 121 GiB unified per node; the 1M arm leaves 3–5 GiB available. Do not build,
  download, or co-locate another model while it runs.
- The unit gates on **MemAvailable** (not MemFree) on both nodes.
- `vm.min_free_kbytes=1048576` on both nodes or neither.

## Rollback

The deposed kit is intact at `/home/nvidia/glm53-fp4-local` with its own image,
`.env`, and unit:

```bash
systemctl --user stop vllm-b12x.service
systemctl --user start vllm-glm53fp4.service
```

Re-enable its watchdog timer only after stopping the b12x one; two watchdogs
would fight over the same container name.

## Watchdog

`vllm-b12x-watchdog.timer` runs every minute. It ignores a unit that is
disabled, inactive, or activating; waits one tick when both ranks are up but
health is down; heals `failed` units; and caps itself at 3 heals per 6 h. The
cap exists so a broken boot cannot thrash GB10 memory.

## Endpoint exposure

The server binds `127.0.0.1:8000` only. `vllm-b12x-tailscale.service` runs
`scripts/tailscale_proxy.py`, which binds the host's Tailscale IPv4 and forwards
to loopback. Tailscale is the network boundary; the API has no auth.
