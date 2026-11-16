# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unchanged PreparedMTP arithmetic prefix, with diagnostic stage returns."""
import torch
from flashinfer.triton.norm import rms_norm

def feedback(self, metadata):
    w, m = (self.weights.tensors, metadata)
    embedded = self.embedding(token_ids=m.token_ids, num_rows=m.num_tokens)
    embedded = embedded.masked_fill((m.indexed.positions == 0)[:, None], 0)
    joined = torch.empty((embedded.shape[0], 8192), dtype=embedded.dtype, device=embedded.device)
    rms_norm(embedded, w['enorm'], joined[:, :4096], self.eps, round_before_weight=True)
    rms_norm(m.hidden, w['hnorm'], joined[:, 4096:], self.eps, round_before_weight=True)
    residual = self.projection(joined)
    normalized = torch.empty_like(residual)
    rms_norm(residual, w['input_layernorm'], normalized, self.eps, round_before_weight=True)
    return (embedded, joined, residual, normalized)
