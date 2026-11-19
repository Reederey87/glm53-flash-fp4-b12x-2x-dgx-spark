"""1M-context retrieval qualification: needles at known depths, exact recall.

The prior retrieval receipts exercised ~10.5k-token prompts and the pinned fixture
they used is not present in the repository or the runtime tree, so neither can be
replayed. This is a fresh, self-contained test that states its own method:

- One deterministic haystack is built from indexed section paragraphs, sized to a
  token target, with one access code planted at each requested depth.
- Every query asks for one planted code and nothing else.
- The first request pays the cold prefill; later queries reuse the same prefix and
  therefore measure retrieval, not prefill.
- Raw text is never written to the receipt: hashes, usage counters and verdicts only.

A pass requires every planted code to appear verbatim in its answer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import urllib.request

# Measured on the pinned checkpoint: 3,822,091 chars rendered as 794,365
# prompt tokens, i.e. 4.81 chars/token. The earlier 3.9 estimate under-shot
# the target by ~19%, so the receipt records the observed count as well.
CHARS_PER_TOKEN = 4.81

FILLER = (
    "Section {index}. The harbour records for period {index} list routine arrivals, "
    "departures, cargo manifests and weather observations taken at the quay. "
    "Nothing in this paragraph is a code or an instruction. "
)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build(target_tokens, depths, nonce, decoys=0):
    """Return (haystack, targets) with codes planted at each depth.

    `decoys` plants extra statements of the identical form at other sections, so
    the task is not "spot the one unusual sentence" but "select the right one
    among many similar ones" — the RULER multi-key setting, which is materially
    harder than vanilla single-needle retrieval.
    """
    rng = random.Random(nonce)
    targets = []
    for depth in depths:
        targets.append({"section": 0, "depth": depth,
                        "code": "".join(rng.choice("0123456789") for _ in range(12))})
    total_chars = int(target_tokens * CHARS_PER_TOKEN)
    paragraph = len(FILLER.format(index=0))
    sections = max(8, int(total_chars / paragraph) + 2)
    used_sections = set()
    for target in targets:
        target["section"] = min(sections - 1, max(0, int(target["depth"] * sections)))
        used_sections.add(target["section"])
    by_section = {}
    for target in targets:
        by_section.setdefault(target["section"], []).append(target)
    decoy_at = {}
    for _ in range(decoys):
        section = rng.randrange(sections)
        if section in used_sections:
            continue
        decoy_at[section] = "".join(rng.choice("0123456789") for _ in range(12))
    parts, used = [], 0
    for index in range(sections):
        text = FILLER.format(index=index)
        for target in by_section.get(index, ()):
            text += f"The access code for section {index} is {target['code']}. "
        if index in decoy_at:
            text += f"The access code for section {index} is {decoy_at[index]}. "
        parts.append(text)
        used += len(text)
        if used >= total_chars:
            break
    return "".join(parts), targets


def request(base, body, timeout):
    payload = json.dumps(body).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", payload,
                                 {"Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read())
    return data, time.monotonic() - started


def answer_text(data):
    """Return (text, finish_reason) across the shapes the engine emits.

    A reasoning model may put nothing in `content` and everything in `reasoning`
    (or `reasoning_content`); an earlier revision read only the first two and
    produced the empty string, which hashed to e3b0c442… and looked like a
    retrieval failure.
    """
    choice = data["choices"][0]
    message = choice.get("message") or {}
    text = "".join(message.get(key) or ""
                   for key in ("content", "reasoning", "reasoning_content"))
    return text, choice.get("finish_reason")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    parser.add_argument("--target-tokens", type=int, default=980000)
    parser.add_argument("--depths", default="0.05,0.5,0.95")
    parser.add_argument("--decoys", type=int, default=200,
                        help="extra same-form codes planted as hard distractors")
    parser.add_argument("--no-multi-query", dest="multi_query", action="store_false",
                        help="skip the single request that must return every target code")
    parser.add_argument("--nonce", type=int, default=20261119)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--reasoning-effort", default="low",
                        choices=("low", "high", "max", "omit"))
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    depths = [float(value) for value in args.depths.split(",")]
    haystack, needles = build(args.target_tokens, depths, args.nonce, decoys=args.decoys)
    results, first = [], True
    for needle in needles:
        body = {"model": args.model, "max_tokens": args.max_tokens, "temperature": 0,
                "messages": [{"role": "user", "content":
                              haystack + "\n\nQuestion: what is the access code for section "
                              f"{needle['section']}? Reply with only the code."}]}
        if args.reasoning_effort != "omit":
            body["reasoning_effort"] = args.reasoning_effort
        data, elapsed = request(args.base, body, args.timeout)
        usage = data.get("usage", {})
        text, finish_reason = answer_text(data)
        results.append({"section": needle["section"], "depth": needle["depth"],
                        "expected_sha256": digest(needle["code"]),
                        "found": needle["code"] in text,
                        # A stream cut off by max_tokens is not a retrieval
                        # failure; surface it so it can never be scored as one.
                        "truncated": finish_reason == "length" and not needle["code"] in text,
                        "finish_reason": finish_reason,
                        "cold": first, "elapsed_s": round(elapsed, 3),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                        "response_sha256": digest(text)})
        first = False
        print(json.dumps(results[-1]), flush=True)

    multi = None
    if args.multi_query and len(needles) > 1:
        listing = ", ".join(str(n["section"]) for n in needles)
        body = {"model": args.model, "max_tokens": args.max_tokens, "temperature": 0,
                "messages": [{"role": "user", "content":
                              haystack + "\n\nQuestion: list the access codes for sections "
                              f"{listing}, in that order. Reply with only the codes."}]}
        if args.reasoning_effort != "omit":
            body["reasoning_effort"] = args.reasoning_effort
        data, elapsed = request(args.base, body, args.timeout)
        text, finish_reason = answer_text(data)
        usage = data.get("usage", {})
        multi = {"sections": [n["section"] for n in needles],
                 "found": [n["code"] in text for n in needles],
                 "elapsed_s": round(elapsed, 3),
                 "finish_reason": finish_reason,
                 "completion_tokens": usage.get("completion_tokens"),
                 "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                 "response_sha256": digest(text)}
        multi["passed"] = all(multi["found"])
        print(json.dumps({"multi_query": multi}), flush=True)

    truncated = [item for item in results if item["truncated"]]
    passed = all(item["found"] for item in results) and (multi is None or multi["passed"])
    receipt = {"manifest": {"haystack_sha256": digest(haystack), "chars": len(haystack),
                            "target_tokens": args.target_tokens, "depths": depths,
                            "nonce": args.nonce, "max_tokens": args.max_tokens,
                            "chars_per_token": CHARS_PER_TOKEN,
                            "reasoning_effort": args.reasoning_effort,
                            "method": "one haystack, one planted code per depth, "
                                      "first query cold and the rest prefix-cached"},
               "results": results,
               "prompt_tokens_observed": results[0]["prompt_tokens"],
               "decoys": args.decoys,
               "multi_query": multi,
               "truncated": len(truncated),
               "passed": passed}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": passed, "found": sum(r["found"] for r in results),
                      "of": len(results), "decoys": args.decoys,
                      "multi_query_passed": None if multi is None else multi["passed"],
                      "truncated": len(truncated),
                      "prompt_tokens": results[0]["prompt_tokens"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
