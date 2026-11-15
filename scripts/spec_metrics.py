"""Normalize per-run speculative counters without inventing missing measurements."""

import math
import re

COUNTERS = {
    "vllm": {
        "accepted": "vllm:spec_decode_num_accepted_tokens_total",
        "draft_tokens": "vllm:spec_decode_num_draft_tokens_total",
        "drafts": "vllm:spec_decode_num_drafts_total",
    },
    "flare": {
        "accepted": "flare_accepted_draft_tokens_total",
        "draft_tokens": "flare_verification_draft_tokens_total",
        "drafts": "flare_draft_request_rounds_total",
        "rounds": "flare_verification_request_rounds_total",
    },
}
SAMPLE = re.compile(r'^([^\s{]+)(?:\{(?:[^"}]|"(?:\\.|[^"\\])*")*\})?\s+([^\s]+)(?:\s+\S+)?(?:\s+#.*)?$')


def parse_counters(text, engine):
    names = COUNTERS[engine]
    totals = {}
    for line in text.splitlines():
        match = SAMPLE.fullmatch(line.strip())
        if match is None or match[1] not in names.values():
            continue
        value = float(match[2])
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid counter {match[1]}: {value}")
        totals[match[1]] = totals.get(match[1], 0) + value
    missing = set(names.values()) - totals.keys()
    if missing:
        raise ValueError("missing counters: " + ", ".join(sorted(missing)))
    return totals


def counter_delta(before, after, engine):
    values = {key: after[name] - before[name] for key, name in COUNTERS[engine].items()}
    if any(value < 0 or not math.isfinite(value) for value in values.values()):
        raise ValueError("counters reset or became invalid during the measured run")
    if values["drafts"] <= 0 or values["draft_tokens"] <= 0:
        raise ValueError("speculative counters did not advance")
    if values["accepted"] > values["draft_tokens"]:
        raise ValueError("accepted drafts exceed proposed drafts")
    if "rounds" in values:
        if values["rounds"] < values["drafts"]:
            raise ValueError("draft-bearing rounds exceed total request rounds")
        values["zero_draft_rounds"] = values["rounds"] - values["drafts"]
    return values
