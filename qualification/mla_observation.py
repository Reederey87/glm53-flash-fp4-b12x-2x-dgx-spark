# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Qualification-only observation of the actual MLA attention return.

Copied from pinned Flare5a4e867 PreparedGlmMLA.forward. The only semantic
addition binds the already-computed attended tensor into the diagnostic return.
No serving source, arithmetic, kernel choice or comparison tolerance changes.
"""
from dataclasses import replace
from ignition.recipes.glm53.mla import MLAScratch, rms_norm

def observed_forward(self, source, metadata):
    s = MLAScratch.allocate(source.shape[0], self.heads, self.blocks, self.mode, self.device,
        context_ranks=self.context_ranks, remote=self.remote)
    p = self.projections
    projected = p["qkv_a_proj"](source)
    s.projected_input.copy_(projected)
    rms_norm(s.query_input, self.module.q_a_layernorm.weight, s.query_residual,
        self.module.q_a_layernorm.variance_epsilon, round_before_weight=True)
    chain = self.query_chain
    chain_pending = None
    if chain is not None:
        chain_pending = chain.start(s.query_residual, s.query, s.absorbed_query, s.gathered)
        query = s.query
    else:
        query = p["q_b_proj"](s.query_residual).view(source.shape[0], self.heads, 256)
        if self.context is None:
            absorbed_query = self.query_absorption(query.transpose(0, 1)).transpose(0, 1)
            s.absorbed_query.copy_(absorbed_query)
    rms_norm(s.latent_input, self.module.kv_a_layernorm.weight, s.latent,
        self.module.kv_a_layernorm.variance_epsilon, round_before_weight=True)
    self.writer(s.latent, metadata.token_slots)
    selection, index_scratch = self.indexer.forward(source, s.query_residual,
        s.projected_input[:, 2048:2176], s.projected_input[:, 2176:2208], metadata, s.index)
    physical, selected_lengths, page_table = selection
    s = replace(s, index=index_scratch, query=query)
    chain_result = chain.finish(chain_pending, physical) if chain is not None else None
    if self.context is None:
        s.visible.copy_(metadata.positions + 1)
        if self.sm103_prefill:
            end = metadata.positions.max().reshape(1) + 1
            attended = self.attention(chain_result if chain_result is not None else s.absorbed_query,
                metadata.positions, selected_lengths, page_table[0], end, cache=self.cache)
        else:
            attended = self.attention(chain_result if chain_result is not None else s.absorbed_query,
                physical, s.visible, selected_lengths, cache=self.cache)
        s = replace(s, attended=attended)
        expanded = self.value_expansion(attended.transpose(0, 1)).transpose(0, 1)
        s.expanded.copy_(expanded)
    elif self.mode == "prefill":
        self.attend_gathered_context(s, metadata, query, physical, selected_lengths)
    else:
        s.visible.copy_(self.context.shards.local_tokens(metadata.positions + 1))
        for start, end, absorb, gather, attention, combine, expand in self.slices:
            count = end - start
            absorbed = s.absorbed_query[start:end] if chain is not None else absorb(query[start:end].transpose(0, 1)).transpose(0, 1)
            gathered = (chain_result[start:end] if chain is not None else
                        gather(absorbed.view(count, -1)).view(count, self.heads * self.context_ranks, 512))
            # The head exchange uses its own channel, so it reads the partial output and LSE in place.
            partial, lse = attention(gathered, physical[start:end], s.visible[start:end],
                selected_lengths[start:end], cache=self.cache)
            attended = combine(partial, lse)
            expanded = expand(attended.transpose(0, 1)).transpose(0, 1)
            s.expanded[start:end].copy_(expanded)
    output = p["o_proj"](s.expanded.view(source.shape[0], -1))
    return output, replace(s, output=output)
