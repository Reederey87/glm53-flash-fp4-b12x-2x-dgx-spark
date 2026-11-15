"""Native Flare API qualification; run in the pinned preparation uv environment."""
import argparse
import json
from pathlib import Path
import urllib.request


def post(base, body):
    request = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8001")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.base.rstrip("/")
    model = "nvidia/GLM-5.3-Flash-FP4-Local"
    results = []

    def check(name, function):
        try:
            detail = function()
            results.append({"name": name, "passed": True, "detail": detail})
        except Exception as error:
            results.append({"name": name, "passed": False, "error": repr(error)})
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results[-1]), flush=True)

    def body(messages, **options):
        return {"model": model, "messages": messages, "temperature": 1.0, "top_p": .95,
                "seed": 1234, "max_tokens": 1024, **options}

    def identity():
        with urllib.request.urlopen(base + "/v1/models", timeout=10) as response:
            models = json.load(response)["data"]
        entry = next(x for x in models if x["id"] == model)
        assert entry["max_model_len"] >= 1_000_000, entry
        return entry

    check("identity_and_context", identity)

    def reasoning():
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(args.snapshot), local_files_only=True, trust_remote_code=False)
        messages = [{"role": "user", "content": "Say hello."}]
        observations = {}
        for effort in (None, "low", "high", "max"):
            options = {} if effort is None else {"reasoning_effort": effort}
            rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **options)
            label = "Max" if effort is None else effort.capitalize()
            assert "Reasoning Effort: " + label in rendered
            expected = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, **options)
            response = post(base, body(messages, max_tokens=1, return_token_ids=True, **options))
            actual = response.get("prompt_token_ids")
            assert actual == expected, f"native prompt differs for {effort or 'omitted'}"
            observations[effort or "omitted"] = {"effort": label, "matched_tokens": len(actual)}
        return observations

    check("native_reasoning_template", reasoning)

    def tools():
        definition = {"type": "function", "function": {"name": "get_temperature", "description": "Read a city's temperature.",
                      "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"], "additionalProperties": False}}}
        messages = [{"role": "user", "content": "Use get_temperature to get the temperature in Oslo."}]
        response = post(base, body(messages, tools=[definition], tool_choice={"type": "function", "function": {"name": "get_temperature"}}))
        message = response["choices"][0]["message"]
        call = message["tool_calls"][0]
        assert call["function"]["name"] == "get_temperature"
        arguments = json.loads(call["function"]["arguments"])
        assert arguments["city"].lower() == "oslo"
        history = messages + [message, {"role": "tool", "tool_call_id": call["id"], "content": '{"temperature_c":12}'}]
        answer = post(base, body(history, tools=[definition], tool_choice="none"))
        assert answer["choices"][0]["message"].get("content")
        return {"function": call["function"]["name"], "arguments": arguments, "roundtrip": "passed"}

    check("tool_roundtrip", tools)

    def structured():
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
        response = post(base, body([{"role": "user", "content": "Return ok=true."}],
                                  response_format={"type": "json_schema", "json_schema": {"name": "status", "strict": True, "schema": schema}}))
        value = json.loads(response["choices"][0]["message"]["content"])
        assert value == {"ok": True}, value
        return value

    check("structured_output", structured)

    def prefix():
        messages = [{"role": "user", "content": "Remember this public test passage. " + "The harbor lantern glows at sunset. " * 180}]
        request = body(messages, max_tokens=8)
        first, repeated = post(base, request), post(base, request)
        first_usage, second_usage = first["usage"], repeated["usage"]
        assert second_usage["prompt_tokens_details"]["cached_tokens"] > 0
        assert second_usage["prompt_tokens"] == first_usage["prompt_tokens"]
        return {"first": first_usage, "repeated": second_usage}

    check("observed_prefix_reuse", prefix)

    def cancel():
        request = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body(
            [{"role": "user", "content": "Write a long Python sorting tutorial."}], stream=True, max_tokens=4096)).encode(),
            {"Content-Type": "application/json"})
        observed = False
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                if line.startswith(b"data:"):
                    observed = True
                    break
        assert observed
        following = post(base, body([{"role": "user", "content": "Say ready."}], max_tokens=128))
        assert following["usage"]["completion_tokens"] > 0
        return {"stream_closed": True, "subsequent_generation": "passed"}

    check("cancel_and_recover", cancel)
    return int(any(not item["passed"] for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
