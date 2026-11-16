"""Measure the registered cold-discovery mechanism, not overall performance."""
import json
from pathlib import Path
import sys

from analyze_workload_trace import analyze
import flare_mixed_compare


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def arm(directory, label):
    _, requests, _ = flare_mixed_compare.load(directory / f'{label}-mixed.jsonl', 'latency')
    lengths = [128, *(r['prompt_tokens'] for r in requests.values())]
    warm_lengths = []
    warm_wall = 0.
    if label == '1-latency':
        warm = load(directory / f'{label}-warmup.jsonl')
        assert warm[-1] == {'complete': True, 'requests': 14, 'repetitions': 2}
        stages = warm[1:-1]
        assert [(r['repetition'], r['stage']) for r in stages] == [(a, b) for a in range(2) for b in range(3)]
        for stage in stages:
            warm_lengths.extend(r['prompt_tokens'] for r in stage['requests'])
            warm_wall += stage['wall_s']
        assert warm_lengths == [32768, 1024, 1024, 1024, 1024, 1024, 1024] * 2
        lengths += warm_lengths
    rows = load(directory / f'{label}-trace.jsonl')
    result = analyze(rows, lengths)
    ordered = sorted(result['histories'], key=lambda r: r['first_prefill_selected_ns'])
    if warm_lengths:
        assert [r['prompt_tokens'] for r in ordered[:14]] == warm_lengths
        assert ordered[14]['prompt_tokens'] == 128
    short = next(r for r in ordered if r['prompt_tokens'] == 4096)
    final_prefill = max((r for r in short['events'] if r['kind'] == 'Prefill'), key=lambda r: r['fence'])
    snapshot = next(r for r in short['events'] if r['kind'] == 'Snapshot' and r['fence'] > final_prefill['fence'])
    graphs = {r['graph']: r for r in rows[0]['graphs']}
    intervening = [r for r in rows if r['event'] == 'completion' and final_prefill['fence'] < r['fence'] < snapshot['fence']]
    discovery = [r for r in intervening if r['timing_origin'] == 'Discovery' and graphs[r['graph']]['kind'] == 'Prefill']
    observation = {'label': label, 'native_histories': result['native_histories'],
        'completions': result['completions'], 'warmup_wall_s': warm_wall,
        'first_4k_terminal_tail_s': (snapshot['at_ns'] - final_prefill['at_ns']) / 1e9,
        'intervening_discovery_prefills': len(discovery),
        'intervening_graphs': [{**r, 'graph_descriptor': graphs[r['graph']]} for r in intervening],
        'scope': 'native unique first 4k cohort request; no HTTP ID or performance verdict'}
    (directory / f'{label}-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    (directory / f'{label}-warmup-mechanism.json').write_text(json.dumps(observation, indent=2) + '\n')
    print(json.dumps({k: v for k, v in observation.items() if k != 'intervening_graphs'}), flush=True)


def compare(directory):
    baseline, candidate = [json.loads((directory / f'{label}-warmup-mechanism.json').read_text())
                           for label in ('0-latency', '1-latency')]
    passed = (baseline['intervening_discovery_prefills'] > 0
        and candidate['intervening_discovery_prefills'] == 0
        and candidate['first_4k_terminal_tail_s'] <= baseline['first_4k_terminal_tail_s'] * .5
        and 0 < candidate['warmup_wall_s'] <= 300)
    result = {'baseline': baseline, 'candidate': candidate, 'mechanism_gate_passed': passed,
              'scope': 'one fresh start per arm, traced; startup mechanism only, no adoption or performance pass'}
    (directory / 'warmup-mechanism-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    (directory / 'diagnosis-complete.txt').write_text('Both traced arms complete; mechanism result retained.\n')
    if passed:
        (directory / 'warmup-mechanism-gate-passed.txt').write_text('Cold-discovery mechanism gate only; full performance and adoption gates remain.\n')
    print(json.dumps({'mechanism_gate_passed': passed, 'scope': result['scope']}), flush=True)


if __name__ == '__main__':
    directory, label = Path(sys.argv[1]), sys.argv[2]
    compare(directory) if label == 'compare' else arm(directory, label)
