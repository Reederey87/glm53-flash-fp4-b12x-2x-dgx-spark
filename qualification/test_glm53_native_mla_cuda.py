"""Exact pinned MLA replay assertions with the deployed dense activation option.

This tests one TP2 shard on one GPU, not two-host collectives or model accuracy.
The upstream body, sparse tie checks and zero-tolerance comparisons stay intact.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("FLARE_RUN_CUDA_TESTS") != "1",
                               reason="requires an explicitly assigned CUDA device")


@pytest.fixture(scope="module")
def upstream_mla():
    root = Path(os.environ["FLARE_PINNED_SOURCE"])
    path = root / "tests/recipes/test_glm53_mla_cuda.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "2d22226f190e272b565f585561d7ee4c5dac88c35ee352dc258eb0ec9083fca0")
    spec = importlib.util.spec_from_file_location("pinned_glm_mla_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tp2_weights(upstream_mla):
    return upstream_mla.model_weights.__wrapped__(SimpleNamespace(param=2))


@pytest.mark.parametrize("mode,rows,overlap", [
    ("decode", 1, True), ("decode", 2, True),
    ("decode", 1, False), ("decode", 2, False),
    ("prefill", 65, True), ("prefill", 4096, True),
])
def test_native_dense_mla_replay(upstream_mla, tp2_weights, monkeypatch,
                                 mode, rows, overlap, record_property):
    import torch
    torch.manual_seed(531)
    original = upstream_mla.RecordedPreparationSession
    sessions = []

    def session(**kwargs):
        assert "native_dense_activations" not in kwargs
        result = original(**kwargs, native_dense_activations=True)
        assert result.native_dense_activations is True
        sessions.append(result)
        return result

    monkeypatch.setattr(upstream_mla, "RecordedPreparationSession", session)
    upstream_mla.test_glm_mla_checkpoint_native_replay(
        tp2_weights, mode, rows, overlap)
    assert len(sessions) == 1
    record_property("native_dense_activations", True)
    record_property("tp_shard", "rank1/world2; one GPU operator replay")
