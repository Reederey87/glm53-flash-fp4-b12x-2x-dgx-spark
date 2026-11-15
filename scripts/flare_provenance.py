"""Local export provenance; supplemental evidence, not signed core metadata."""
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_plan(recipe, plan):
    expected = {'repository': recipe['model'], 'revision': recipe['checkpoint_revision'],
                'tensor_parallel': 2, 'max_concurrency': recipe['concurrency'],
                'prefill_chunk': recipe['prefill_chunk'], 'context_parallel': False,
                'language_model_only': True,
                'native_dense_activations': recipe.get('native_dense_activations', False)}
    for key, value in expected.items():
        if type(plan.get(key)) is not type(value) or plan[key] != value:
            raise ValueError(f'resolved plan {key} differs from recipe')
    speculation = plan.get('speculation') or {}
    if speculation.get('draft_tokens') != recipe['mtp_drafts'] or speculation.get('adaptive') is not False:
        raise ValueError('resolved speculation differs from recipe')


def export_receipt(recipe, command, log, previous_primaries):
    """Called only after successful export; bind its resolved plan to a new core."""
    plans, entries = [], []
    for line in Path(log).read_text().splitlines():
        if line.startswith('{"plan":'):
            plans.append(json.loads(line)['plan'])
        if line.startswith('Exported cache entry: '):
            entries.append(line.removeprefix('Exported cache entry: '))
    if len(plans) != 1 or len(entries) != 1:
        raise ValueError('export must report exactly one resolved plan and cache entry')
    native = recipe.get('native_dense_activations', False)
    if plans[0].get('native_dense_activations') is not native:
        raise ValueError('resolved native activation option differs from recipe')
    verify_plan(recipe, plans[0])
    if ('--native-dense-activations' in command) != native:
        raise ValueError('export argv differs from resolved activation option')
    root = Path(recipe['runtime_root']).resolve()
    primary = (Path(entries[0]) / 'model.safetensors').resolve()
    if not primary.is_relative_to(root / 'cores') or primary in previous_primaries:
        raise ValueError('export must publish a new primary inside the candidate cache')
    return {'schema': 1, 'evidence': 'successful local export; unsigned supplemental provenance',
            'core_primary': str(primary), 'core_primary_sha256': sha256(primary),
            'plan': plans[0], 'argv': command, 'log_sha256': sha256(log),
            'flare_revision': recipe['flare_revision'],
            'checkpoint_revision': recipe['checkpoint_revision']}


def verify_export_receipt(recipe, state):
    """Require separately accepted provenance for the requested activation arm."""
    root = Path(recipe['runtime_root']).resolve()
    path = Path(state.get('export_receipt', '')).resolve()
    if not path.is_relative_to(root / 'local'):
        raise ValueError('accepted export provenance is missing or outside candidate local directory')
    if sha256(path) != state.get('export_receipt_sha256'):
        raise ValueError('export provenance changed after acceptance')
    receipt = json.loads(path.read_text())
    if receipt.get('schema') != 1:
        raise ValueError('unsupported export provenance schema')
    for key in ('core_primary', 'core_primary_sha256'):
        if receipt.get(key) != state[key]:
            raise ValueError('export provenance belongs to a different core')
    for key in ('flare_revision', 'checkpoint_revision'):
        if receipt.get(key) != recipe[key]:
            raise ValueError('export provenance source pin differs from recipe')
    native = recipe.get('native_dense_activations', False)
    if receipt.get('plan', {}).get('native_dense_activations') is not native:
        raise ValueError('accepted core activation option differs from recipe')
    verify_plan(recipe, receipt['plan'])
    if ('--native-dense-activations' in receipt.get('argv', [])) != native:
        raise ValueError('accepted export argv differs from activation option')
