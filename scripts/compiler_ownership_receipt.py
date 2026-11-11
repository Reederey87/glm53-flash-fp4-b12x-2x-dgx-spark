"""Verify complete, content-free compiler diagnostics; no serving verdict."""
import argparse
import json
from pathlib import Path
from host_ownership_receipt import validate as validate_memory


def one(log, marker):
    rows = [json.loads(line.split(marker, 1)[1]) for line in log.splitlines() if marker in line]
    if len(rows) != 1: raise ValueError('need exactly one ' + marker.strip())
    return rows[0]


def validate(log, worker, helper, metadata, pid, boundary='post-explicit-profile'):
    proof = validate_memory(log, worker, helper, pid, boundary)
    row = proof['record']
    if row['metadata_sha256'] != metadata or row['host']['MemAvailable'] < 4 * 1024**3 or type(row['result']) is not int or row['result'] <= 0:
        raise ValueError('compiler metadata/headroom/admission mismatch')
    objects = one(log, 'B12X_COMPILER_OBJECTS ')
    mappings = one(log, 'B12X_COMPILER_MAPS ')
    for extra in (objects, mappings):
        for key in ('version', 'boundary', 'pid', 'utc_ns', 'worker_sha256', 'helper_sha256', 'metadata_sha256'):
            if extra[key] != row[key]: raise ValueError('mixed compiler diagnostic receipts')
    summary = objects['objects']; maps = mappings['mappings']
    for key in ('scanned_objects', 'gc_objects_total', 'unique_payload_bytes', 'unique_payload_objects', 'visited_metadata_nodes', 'depth_omissions', 'uninspectable_targets'):
        if type(summary[key]) is not int or summary[key] < 0: raise ValueError('invalid compiler count')
    if summary['max_nodes'] != 100000 or summary['max_depth'] != 6 or summary['visited_metadata_nodes'] > 100000 or type(summary['truncated']) is not bool:
        raise ValueError('invalid compiler traversal bounds')
    if summary['max_gc_objects'] != 2000000 or summary['scanned_objects'] > 2000000 or summary['scanned_objects'] > summary['gc_objects_total']:
        raise ValueError('invalid GC scan bounds')
    if maps['max_maps'] != 16384 or not 0 < maps['maps'] <= 16384 or type(maps['truncated']) is not bool:
        raise ValueError('invalid mapping bounds')
    return dict(memory=proof, objects=summary, mappings=maps,
                complete_within_bounds=not summary['truncated'] and not maps['truncated'],
                serving_qualified=False, total_process_ownership_proven=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('log',type=Path)
    for name in ('worker','helper','metadata','boundary'): parser.add_argument('--'+name,required=True)
    parser.add_argument('--trace',type=Path,required=True); args=parser.parse_args()
    print(json.dumps(validate(args.log.read_text(),args.worker,args.helper,args.metadata,
                              json.loads(args.trace.read_text())['pid'],args.boundary),indent=2))
