# 67 — Reaching the serving model over Tailscale (client troubleshooting)

Verified **2026-11-20** against the live head. Everything below was read from the
cluster, not remembered; where a value varies per boot it is marked.

## What the cluster side looks like (confirmed)

| Item | Value |
| --- | --- |
| Tailnet IPv4 (head) | **`100.125.23.98`** |
| MagicDNS name | **`spark-a183.tail0c5008.ts.net`** |
| `tailscaled` on head | active, version **1.104.7** |
| Tailnet account | `reederey@` (personal tailnet, suffix `tail0c5008.ts.net`) |
| Proxy unit | `b12x-flare-tailscale.service` (systemd **user** unit, runs as `nvidia`) |
| Proxy listener | **`100.125.23.98:8000`** → forward to `127.0.0.1:8001` |
| Model listener | `127.0.0.1:8001` only — **not** reachable off-host without the proxy |
| API | OpenAI-compatible, **no API key** (access is bounded by the tailnet or SSH) |
| Model id | `nvidia/GLM-5.3-Flash-FP4-Local` |
| Context | `max_model_len` = **1,048,576** (advertised; retrieval qualified to 979,581) |
| Slots | 4 concurrent requests |
| KV pool | ~2.31–2.39 M tokens, **varies per boot** |

Cluster-side sanity check, which must pass *before* blaming the client:

```bash
# on the head, as nvidia
systemctl --user is-active b12x-flare-tailscale.service      # want: active
systemctl --user is-active b12x-flare-production.service     # want: active
ss -tlnp | grep -E ':8000|:8001'                             # 8000 on 100.125.23.98, 8001 on 127.0.0.1
curl -s -o /dev/null -w '%{http_code}\n' http://100.125.23.98:8000/health   # want: 200
curl -s http://100.125.23.98:8000/v1/models | head -c 200
```

If `/health` through `100.125.23.98:8000` is **200 on the host** but unreachable
from the Mac, the fault is client-side or tailnet-side — not the model.

## What the client MacBook needs

1. **The same tailnet account.** Tailscale is per-tailnet; a personal account and
   a work account are separate networks and cannot see each other without node
   sharing. Confirm on the Mac: `tailscale status` must list `spark-a183`.
2. **A client that actually routes `100.64.0.0/10`.** Two very different builds:
   - **Standalone/Homebrew/CLI build** creates a TUN interface and routes `100.x`
     normally. Raw `curl` works.
   - **Mac App Store build** runs in **userspace networking** mode: there is *no*
     route for `100.125.0.0/10`, and raw sockets go to the LAN gateway instead.
     This is the single most common cause of "ping works, curl doesn't".

   Decisive check on the Mac:

   ```bash
   route -n get 100.125.23.98 | grep -E 'gateway|interface'
   ```

   - `interface: utun*` → TUN mode, raw sockets will work.
   - `gateway: <your LAN router>, interface: en0/en1` → **userspace mode**; raw
     `curl` cannot work no matter what, and you need one of:
     - `tailscale serve`/`tailscale` HTTP proxy on the Mac, or
     - the SSH forward (below), or
     - the standalone build instead of the App Store build.

3. **Client timeouts sized for prefill.** A ~1M-token prompt takes **~520 s** to
   prefill (measured). Default 60 s HTTP timeouts will fail with a read timeout
   that looks like a network fault. Use `--max-time 900` for long prompts, or
   stream.

## Diagnostic ladder (run in order, stop at the first failure)

```bash
# 1. Is the Mac on the tailnet, and does it see the head?
tailscale status | grep spark-a183

# 2. Does the tailnet IP answer at all (ICMP)?
ping -c 3 100.125.23.98

# 3. Is port 8000 reachable? (TCP, no HTTP)
nc -vz 100.125.23.98 8000

# 4. Does the proxy answer HTTP?
curl -sS -m 10 -o /dev/null -w '%{http_code}\n' http://100.125.23.98:8000/health

# 5. Does model discovery work?
curl -sS -m 10 http://100.125.23.98:8000/v1/models | head -c 300

# 6. A real completion
curl -sS -m 120 http://100.125.23.98:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"nvidia/GLM-5.3-Flash-FP4-Local","messages":[{"role":"user","content":"Say ready."}],"max_tokens":32}'
```

## Failure modes, by symptom

| Symptom | Most likely cause | Check / fix |
| --- | --- | --- |
| `tailscale status` lists nothing / "Logged out" | Not signed in, or wrong account | `tailscale up`; sign into the `reederey@` tailnet |
| Mac sees other peers but not `spark-a183` | Different tailnet, or node sharing not granted | Compare tailnet suffixes (`tail0c5008.ts.net`); share the node from the admin console |
| `ping` OK, `curl` hangs, `nc` fails | **Userspace client** (see above) | `route -n get` test; use SSH forward or standalone build |
| `ping` OK, `nc` says closed, host-side 200 | Proxy unit down on the head | `systemctl --user start b12x-flare-tailscale.service` on the head |
| `nc` OK, `/health` 000, token requests fail | Model unit down (startup gate) | `systemctl --user status b12x-flare-production.service`; the watchdog recovers a running-but-unhealthy owner, and a failed startup retries twice |
| Works, then stops after a reboot | The proxy used to die with a failed model start (fixed 2026-11-18, PR #8) | Confirm the proxy unit is active; the watchdog now ensures it |
| `401`/`403` from the API | Client sending an `Authorization` header expecting auth | No key is required; use `local` if a client demands a non-empty value |
| Read timeout after ~60 s on a long prompt | Client timeout too short for ~520 s prefill | Raise to ≥ 900 s; prefer streaming |
| First token arrives, then stalls | Client disconnected mid-generation | Server cancels on disconnect; retry |
| `Connection refused` immediately | Nothing listening on 8000 | Host-side `ss -tlnp` as above |
| MagicDNS name does not resolve | MagicDNS disabled on the tailnet | Use the IP `100.125.23.98`; DNS is a convenience only |

## Fallback that always works: SSH forward

Independent of tailnet mode, and the method this workspace documents:

```bash
ssh -N -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
    -L 127.0.0.1:18001:127.0.0.1:8001 nvidia@spark-a183.local
# then point the client at http://127.0.0.1:18001/v1
```

Requires an SSH key that `spark-a183.local` accepts (this workspace uses the
NVIDIA Sync key). The forward targets **8001**, the model port, not the proxy.

## API details a client needs

- **Base URL:** `http://100.125.23.98:8000/v1` (or `http://127.0.0.1:18001/v1` via the forward)
- **Model id:** `nvidia/GLM-5.3-Flash-FP4-Local`
- **Auth:** none. Send no `Authorization`, or `Bearer local` if a client insists.
- **Reasoning:** omitting `reasoning_effort` selects the checkpoint default **Max**;
  `low` and `high` are supported. Max reasoning can consume hundreds of tokens
  before any answer, so budget `max_tokens` accordingly.
- **Sampling:** temperature is clamped to the advertised range (**0.95–1.0**);
  `temperature: 0` does **not** mean greedy. `top_p` default 0.95. Inspect
  `/v1/models` → `flare.sampling_ranges` for the live contract.
- **Streaming:** supported; recommended for anything expected to take minutes.
- **Cost of long context:** a ~980k-token prompt repays a **~520 s prefill on every
  turn** — measured `cached_tokens` was 0–9, i.e. the prefix is not retained at that
  size. See [66-context-retrieval-1m.md](66-context-retrieval-1m.md). For an agent
  workflow, treat 1M context as batch, not interactive.

## One-command health probe for the client

```bash
HOST=100.125.23.98
echo "route:  $(route -n get $HOST 2>/dev/null | awk '/interface/{print $2}')"
echo "ping:   $(ping -c1 -W2 $HOST >/dev/null 2>&1 && echo ok || echo FAIL)"
echo "tcp:    $(nc -z -w3 $HOST 8000 >/dev/null 2>&1 && echo ok || echo FAIL)"
echo "health: $(curl -s -m 10 -o /dev/null -w '%{http_code}' http://$HOST:8000/health)"
echo "models: $(curl -s -m 10 http://$HOST:8000/v1/models | head -c 60)"
```

Interpretation: `route` shows the interface the OS will use — `utun*` is fine,
`en0/en1` means userspace mode and an SSH forward is the answer.
