# Architecture

## Data path

```
checkpoint (42 files, ~165 GiB/replica, same bytes on both nodes)
        │  --load-format b12x  (io_uring bounce reads on GB10)
        ▼
rank 0 head  ── vLLM TP2 ──┐   attention  B12X (fp8_ds_mla KV, block 256)
rank 1 worker ─────────────┘   MoE        b12x (W4A16 A4 prefill on)
                               linear     b12x per-quant kernels
                               collectives RoCEnante (≤2 MB AR, ≤16 MB AG)
                               draft      MTP-5, humming MoE + B12X attention
        │
        ▼
127.0.0.1:8000  ── tailscale_proxy.py ──► 100.125.23.98:8000
```

Both ranks run the same image and the same checkpoint snapshot; only
`--node-rank` and `--headless` differ. The worker is dispatched over the QSFP
rail by the head (`ssh nvidia@192.168.177.11`), so the head is the only node an
operator needs to touch.

## Why these components

- **vLLM** is the only engine in this workspace that already serves this
  checkpoint end to end on GB10 with a 2.3M-token FP8 pool. It owns the
  scheduler, prefix cache, chunked prefill, OpenAI surface, reasoning/tool
  parsers.
- **FlashInfer `b12x`** is the kernel layer: NVFP4/MXFP8 GEMM, fused MoE,
  sparse/compressed MLA, the `--load-format b12x` loader, and the RoCEnante
  collectives. The image vendors it under
  `/usr/local/lib/python3.12/dist-packages/flashinfer/experimental/b12x`.
- **Flare** is qualified but not deployed (see `01-qualification.md`). It would
  replace the vLLM runtime with a prepared Rust package: smaller request path and
  a larger native KV cache (a community guide reports 3.4–4.8M tokens), but a
  multi-hour ~178 GB preparation and lower prefill in its published numbers.

## Image

`vllm-node-b12x` is built from `eugr/spark-vllm-docker` with `--exp-b12x`,
which builds FlashInfer from `local-inference-lab/flashinfer@main` for
`sm_121a` instead of installing the standalone `b12x` wheel. The deployed
digest is pinned in `receipts/expected-image-digest.txt`; `preflight.sh` and
`qualify.sh` fail when the local tag drifts from it.

The build lane is deliberately **not** part of a serving window:

```bash
# on the head, with both nodes idle and >=100 GiB free
git clone https://github.com/eugr/spark-vllm-docker && cd spark-vllm-docker
./build-and-copy.sh --cleanup -c --copy-parallel --exp-b12x
```

That build is the path to a newer FlashInfer than the image carries
(`91271757`, 2026-10-15 vs `361e45fad`, 2026-11-01 — 140 commits). It is a
separate, pre-registered window: the Python adapter surface in the vLLM fork
must match the newer kernel package, and a failed build must not cost the
serving window.

## Files and state

| Path | Purpose |
|---|---|
| `/home/nvidia/b12x` | runtime tree (this kit), no build artifacts |
| `/home/nvidia/.cache/huggingface` | checkpoint snapshot, mounted into the container |
| `/home/nvidia/.cache/{vllm,flashinfer,b12x,triton,tilelang}` | JIT/compile caches, mounted |
| `/home/nvidia/b12x/local/` | logs, watchdog state, image digest receipt |
| `/home/nvidia/glm53-fp4-local` | deposed kit, kept intact as rollback |
