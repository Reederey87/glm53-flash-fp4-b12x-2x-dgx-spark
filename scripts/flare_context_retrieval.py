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

CHARS_PER_TOKEN = 3.9  # conservative English estimate; verified against usage

FILLER = (
    "Section {index}. The harbour records for period {index} list routine arrivals, "
    "departures, cargo manifests and weather observations taken at the quay. "
    "Nothing in this paragraph is a code or an instruction. "
)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build(target_tokens, depths, nonce):
    """Return (haystack, needles) with one code planted at each depth."""
    rng = random.Random(nonce)
    needles = []
    for position, depth in enumerate(depths):
        code = "".join(rng.choice("0123456789") for _ in range(12))
        needles.append({"section": 0, "depth": depth, "code": code})
    total_chars = int(target_tokens * CHARS_PER_TOKEN)
    # Size the section count from a measured paragraph, or the loop finishes
    # short of the target and silently understates the context.
    paragraph = len(FILLER.format(index=0))
    sections = max(8, int(total_chars / paragraph) + 2)
    for needle in needles:
        needle["section"] = min(sections - 1, max(0, int(needle["depth"] * sections)))
    ordered = {n["section"]: n for n in needles}
    parts, used = [], 0
    for index in range(sections):
        text = FILLER.format(index=index)
        if index in ordered:
            text += f"The access code for section {index} is {ordered[index]['code']}. "
        parts.append(text)
        used += len(text)
        if used >= total_chars:
            break
    return "".join(parts), needles


def request(base, body, timeout):
    payload = json.dumps(body).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", payload,
                                 {"Content-Type": "application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read())
    return data, time.monotonic() - started


def answer_text(data):
    choice = data["choices"][0]
    message = choice.get("message") or {}
    return (message.get("content") or "") + (message.get("reasoning") or "")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--model", default="nvidia/GLM-5.3-Flash-FP4-Local")
    parser.add_argument("--target-tokens", type=int, default=980000)
    parser.add_argument("--depths", default="0.05,0.25,0.5,0.75,0.95")
    parser.add_argument("--nonce", type=int, default=20261119)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    depths = [float(value) for value in args.depths.split(",")]
    haystack, needles = build(args.target_tokens, depths, args.nonce)
    results, first = [], True
    for needle in needles:
        body = {"model": args.model, "max_tokens": args.max_tokens, "temperature": 0,
                "messages": [{"role": "user", "content":
                              haystack + "\n\nQuestion: what is the access code for section "
                              f"{needle['section']}? Reply with only the code."}]}
        data, elapsed = request(args.base, body, args.timeout)
        usage = data.get("usage", {})
        text = answer_text(data)
        results.append({"section": needle["section"], "depth": needle["depth"],
                        "expected_sha256": digest(needle["code"]),
                        "found": needle["code"] in text,
                        "cold": first, "elapsed_s": round(elapsed, 3),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                        "response_sha256": digest(text)})
        first = False
        print(json.dumps(results[-1]), flush=True)

    passed = all(item["found"] for item in results)
    receipt = {"manifest": {"haystack_sha256": digest(haystack), "chars": len(haystack),
                            "target_tokens": args.target_tokens, "depths": depths,
                            "nonce": args.nonce, "max_tokens": args.max_tokens,
                            "method": "one haystack, one planted code per depth, "
                                      "first query cold and the rest prefix-cached"},
               "results": results,
               "prompt_tokens_observed": results[0]["prompt_tokens"],
               "passed": passed}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": passed, "found": sum(r["found"] for r in results),
                      "of": len(results), "prompt_tokens": results[0]["prompt_tokens"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
