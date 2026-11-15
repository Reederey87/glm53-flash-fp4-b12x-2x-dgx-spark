"""Observe a failed KDA case after measuring its original acceptance result.

These eager clones can alter timing. They diagnose stages, never replace the
unmodified graph result or qualify an engine change. No tensor data is emitted.
"""

import torch


def diagnose(operators, sources, metas, records, state, chain, initial_r, initial_c, width):
    from ignition.recipes.glm53 import kda

    observed = {"plain": {}, "verify": {}}
    phase = "plain"

    def save(name, value):
        observed[phase].setdefault(name, []).append(value.detach().clone())

    original_record = kda._record
    original_decode = kda.kda_decode_out
    original_projections = {n: operators[n].projections["input_proj"] for n in (1, width)}

    class InputProjection:
        def __init__(self, original):
            self.original = original

        def __call__(self, value):
            result = self.original(value)
            save("input_projection", result)
            return result

    def inputs(values):
        for name, value in zip(("convolution", "forget_gate", "beta", "output_gate"), values, strict=True):
            save(name, value)

    def recording(reads, recurrent, output, *args):
        inputs(reads[:4])
        result = original_record(reads, recurrent, output, *args)
        save("gated_recurrence", output)
        return result

    def decoding(*args):
        inputs(args[:4])
        result = original_decode(*args)
        save("gated_recurrence", args[13])
        return result

    try:
        for n, original in original_projections.items():
            operators[n].projections["input_proj"] = InputProjection(original)
        kda._record, kda.kda_decode_out = recording, decoding
        state.recurrent.copy_(initial_r)
        state.convolution.zero_()
        for i in range(width):
            sources[1].copy_(chain[i:i + 1])
            save("output", operators[1](sources[1], metas[1]))
        phase = "verify"
        state.recurrent.copy_(initial_r)
        state.convolution.zero_()
        sources[width].copy_(chain[:width])
        save("output", operators[width](sources[width], metas[width], records=records.layer(0)))
        torch.cuda.synchronize()
    finally:
        kda._record, kda.kda_decode_out = original_record, original_decode
        for n, original in original_projections.items():
            operators[n].projections["input_proj"] = original
        state.recurrent.copy_(initial_r)
        state.convolution.copy_(initial_c)

    result = {"scope": "post-measurement eager diagnostics; timing may differ", "stages": {}}
    expected_names = {"input_projection", "convolution", "forget_gate", "beta",
                      "output_gate", "gated_recurrence", "output"}
    if any(set(observed[p]) != expected_names for p in observed):
        raise RuntimeError("KDA diagnostic hooks did not observe all stages")
    for name in sorted(expected_names):
        plain = torch.cat(observed["plain"][name]).float()
        verified = torch.cat(observed["verify"][name]).float()
        if plain.shape != verified.shape:
            raise RuntimeError(f"KDA diagnostic shape differs for {name}")
        finite = bool(torch.isfinite(plain).all() and torch.isfinite(verified).all())
        norm = plain.norm().item()
        result["stages"][name] = {
            "shape": list(plain.shape), "finite": finite,
            "relative_l2": (verified - plain).norm().item() / norm if finite and norm else None,
            "max_abs": (verified - plain).abs().max().item() if finite else None,
        }
    return result
