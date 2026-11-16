"""Qualification-only same-selection reference, following pinned MLA tests."""
from dataclasses import fields, replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import torch


def install_observer(layer, storage):
    indexer = layer.attention.indexer
    original = indexer.forward

    def observed(*args, **kwargs):
        selection, scratch = original(*args, **kwargs)
        for field in fields(storage):
            getattr(storage, field.name).copy_(getattr(scratch, field.name))
        return selection, scratch

    indexer.forward = observed


def matched_reference(layer, storage, metadata, forward, persistent, initial,
                      output, stages, expected_output, expected_stages,
                      repetitions, receipt):
    path = Path(os.environ["FLARE_PINNED_SOURCE"]) / "tests/recipes/test_glm53_mla_cuda.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "2d22226f190e272b565f585561d7ee4c5dac88c35ee352dc258eb0ec9083fca0"
    spec = importlib.util.spec_from_file_location("pinned_mla_selection_reference", path)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    native = replace(storage, **{f.name: getattr(storage, f.name).clone() for f in fields(storage)})
    saved = {"output": output.clone(), **{k: v.clone() for k, v in stages.items()}}
    saved_state = {k: v.clone() for k, v in persistent.items()}
    indexer = layer.attention.indexer
    original = indexer.forward
    comparisons = []

    def same_selection(*args, **kwargs):
        selection, scratch = original(*args, **kwargs)
        # Exact operands first; valid cutoff ties do not license different scores.
        for name in ("query_fp8", "weights", "pool_lengths", "page_table", "selected_lengths"):
            a, b = getattr(scratch, name), getattr(native, name)
            if a.dtype == torch.float8_e4m3fn:
                a, b = a.view(torch.uint8), b.view(torch.uint8)
            torch.testing.assert_close(a, b, rtol=0, atol=0, msg=name)
        reference.assert_selection(native.pools, scratch.pools, indexer, scratch)
        comparisons.append({"same_order": bool(torch.equal(native.pools, scratch.pools)),
                            "same_set": bool(torch.equal(native.pools.sort().values,
                                                         scratch.pools.sort().values))})
        # Recompute the physical mapping independently from native selected pools.
        scratch.pools.copy_(native.pools)
        if indexer.logical:
            from ignition.recipes.glm53.dcp import expand_tokens
            expand_tokens(scratch.pools, metadata.positions, scratch.physical, scratch.selected_lengths)
        else:
            from b12x.attention import sparse_mla
            sparse_mla.expand_pooled_topk_to_physical_slots(scratch.pools, metadata.positions,
                metadata.requests, metadata.block_table, scratch.physical, scratch.selected_lengths,
                **indexer.expand_options, plan=indexer.expand_plan)
        torch.testing.assert_close(scratch.physical, native.physical, rtol=0, atol=0)
        torch.testing.assert_close(scratch.selected_lengths, native.selected_lengths, rtol=0, atol=0)
        return (scratch.physical, scratch.selected_lengths, selection[2]), scratch

    def error(a, b):
        diff = (a.float() - b.float()).abs()
        return {"exact": bool(torch.equal(a, b)), "max_abs": float(diff.max()),
                "different": int(diff.count_nonzero())}

    try:
        indexer.forward = same_selection
        for key, value in persistent.items():
            value.copy_(initial[key])
        for _ in range(repetitions):
            forward()
        torch.cuda.synchronize(output.device)
        for key, value in persistent.items():
            torch.testing.assert_close(value, saved_state[key], rtol=0, atol=0)
        matched_output = output.clone()
        matched_stages = {k: v.clone() for k, v in stages.items()}
        row = {"repetitions": repetitions, "selection_comparisons": comparisons,
               "uncorrected": {k: error(saved[k], v) for k, v in expected_stages.items()},
               "matched": {k: error(saved[k], v) for k, v in matched_stages.items()},
               "original_output": error(saved["output"], expected_output),
               "matched_output": error(saved["output"], matched_output),
               "scope": "same-selection reference; original exact stages/output bounds remain"}
        with Path(receipt).open("a") as out:
            out.write(json.dumps(row, allow_nan=False) + "\n")
        return matched_output, matched_stages
    finally:
        indexer.forward = original
        output.copy_(saved["output"])
        for key, value in stages.items():
            value.copy_(saved[key])
        for key, value in persistent.items():
            value.copy_(saved_state[key])
        for field in fields(storage):
            getattr(storage, field.name).copy_(getattr(native, field.name))
        torch.cuda.synchronize(output.device)
