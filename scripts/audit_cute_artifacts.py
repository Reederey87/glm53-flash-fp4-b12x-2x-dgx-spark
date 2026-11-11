"""Bounded read-only inventory of canonical ELF64 AArch64 cache objects.

Requires a quiescent cache. File identity/metadata checks detect ordinary races,
not arbitrary concurrent writers. Never imports or loads cached code. Disk and
section sizes are NOT RAM. Unrecognized GPU symbols remain UNKNOWN, not zero.
"""
import argparse
import collections
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import time

SCHEMA = 'b12x._lib.compile_manifest.v3'
MAX_OBJECTS = 8192
MAX_OBJECT = 64 << 20
MAX_MANIFEST = 2 << 20
MAX_TABLE = 4 << 20
MAX_NOBITS = 256 << 20  # Declared bytes per object, never allocated by this tool.
LIMITS = dict(entries=65536, read_bytes=16 << 30, sections=1_000_000,
              symbols=16_000_000, nobits=8 << 30, row_bytes=32 << 20)
MAX_SECONDS = 300


class LimitExceeded(ValueError):
    pass


class Budget:
    def __init__(self):
        self.used = collections.Counter()
        self.deadline = time.monotonic() + MAX_SECONDS

    def charge(self, kind, amount):
        if time.monotonic() > self.deadline:
            raise LimitExceeded('audit time limit exceeded')
        if amount < 0 or self.used[kind] + amount > LIMITS[kind]:
            raise LimitExceeded('audit ' + kind + ' limit exceeded')
        self.used[kind] += amount


def signature(s):
    return s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns


@contextmanager
def checked_file(path, maximum, minimum=0):
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent_info = os.fstat(parent)
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, 'rb') as file:
            before = os.fstat(file.fileno())
            if not stat.S_ISREG(before.st_mode) or not minimum <= before.st_size <= maximum:
                raise ValueError('file type/size outside bounds')
            yield file, before.st_size
            after = os.fstat(file.fileno())
            named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            parent_after = path.parent.stat(follow_symlinks=False)
            if (signature(before) != signature(after) or signature(after) != signature(named)
                    or (parent_info.st_dev, parent_info.st_ino) != (parent_after.st_dev, parent_after.st_ino)):
                raise ValueError('file or parent changed during audit')
    finally:
        os.close(parent)


def read_region(file, offset, size, budget):
    budget.charge('read_bytes', size)
    file.seek(offset)
    data = file.read(size)
    if len(data) != size:
        raise ValueError('truncated region')
    return data


def digest_region(file, offset, size, budget):
    digest = hashlib.sha256()
    while size:
        count = min(size, 1 << 20)
        digest.update(read_region(file, offset, count, budget))
        offset += count
        size -= count
    return digest.hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('nonfinite JSON value')


def parse_manifest(data):
    try:
        m = json.loads(data, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except RecursionError as error:
        raise ValueError('manifest nesting exceeds bound') from error
    pending, nodes = [(m, 0)], 0
    while pending:
        value, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 50000:
            raise ValueError('manifest structure exceeds bound')
        if type(value) in (dict, list):
            children = value.values() if type(value) is dict else value
            if nodes + len(pending) + len(children) > 50000:
                raise ValueError('manifest structure exceeds bound')
            pending.extend((child, depth + 1) for child in children)
    if type(m) is not dict or m.get('schema') != SCHEMA:
        raise ValueError('requires exact v3 manifest object')
    for name, maximum in (('cache_key', 64), ('object_sha256', 64),
                          ('cache_format', 256), ('package_fingerprint', 1024)):
        if type(m.get(name)) is not str or not 0 < len(m[name]) <= maximum:
            raise ValueError('invalid manifest field: ' + name)
    if (type(m.get('object_bytes')) is not int
            or not re.fullmatch('[0-9a-f]{64}', m['cache_key'])
            or not re.fullmatch('[0-9a-f]{64}', m['object_sha256'])
            or type(m.get('toolchain')) not in (list, dict)):
        raise ValueError('invalid manifest key/digest/size/toolchain')
    toolchain = json.dumps(m['toolchain'], sort_keys=True, allow_nan=False).encode()
    if len(toolchain) > 32768:
        raise ValueError('toolchain exceeds retention bound')
    return m, hashlib.sha256(toolchain).hexdigest()


def strings(file, section, budget):
    if section[1] != 3 or not 0 < section[5] <= MAX_TABLE:
        raise ValueError('invalid string table')
    table = read_region(file, section[4], section[5], budget)
    if table[0] or table[-1]:
        raise ValueError('string table must begin/end with NUL')
    return table


def parse_elf(file, size, key, budget):
    header = read_region(file, 0, 64, budget)
    if header[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('requires ELF64 little-endian version1')
    kind, machine, version, entry, phoff, shoff, _, ehsize, phsize, phcount, shsize, count, names = struct.unpack('<HHIQQQIHHHHHH', header[16:])
    if (kind, machine, version, ehsize, shsize) != (1, 183, 1, 64, 64):
        raise ValueError('requires AArch64 ET_REL ELF64 header')
    if entry or phoff or phsize or phcount:
        raise ValueError('program headers/entry unsupported in this ET_REL audit')
    if not 0 < count <= 4096 or names >= count or shoff < 64 or shoff % 8 or shoff + count * 64 > size:
        raise ValueError('invalid/unsupported section table')
    budget.charge('sections', count)
    sections = list(struct.iter_unpack('<IIQQQQIIQQ', read_region(file, shoff, count * 64, budget)))
    if any(sections[0]):
        raise ValueError('nonzero null section/extended indexing unsupported')
    ranges, totals, nobits = [(0, 64), (shoff, shoff + count * 64)], collections.Counter(), 0
    for _, typ, flags, _, offset, length, _, _, align, entsize in sections:
        if typ == 0:  # Remaining fields of inactive sections are undefined.
            continue
        if flags & 0x800 or typ in (11, 18):
            raise ValueError('compressed/dynamic/extended-index sections unsupported')
        if align and align & (align - 1) or entsize and length % entsize:
            raise ValueError('invalid section alignment/entry size')
        if typ == 8:
            nobits += length
            if nobits > MAX_NOBITS:
                raise ValueError('declared NOBITS exceeds per-object bound')
        else:
            if offset + length > size or length and align and offset % align:
                raise ValueError('section range/alignment outside file')
            if length:
                ranges.append((offset, offset + length))
        if flags & 2:
            group = 'nobits' if typ == 8 else ('executable' if flags & 4 else ('writable' if flags & 1 else 'readonly'))
            totals['alloc_' + group] += length
        else:
            totals['nonalloc_nobits' if typ == 8 else 'nonalloc'] += length
    budget.charge('nobits', nobits)
    ranges.sort()
    if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError('overlapping sections or header tables')
    if names:
        table = strings(file, sections[names], budget)
        if any(s[1] and s[0] >= len(table) for s in sections):
            raise ValueError('invalid section name offset')
    elif any(s[1] and s[0] for s in sections):
        raise ValueError('section names without string table')
    symtabs = [s for s in sections if s[1] == 2]
    if len(symtabs) > 1:
        raise ValueError('multiple symbol tables unsupported')
    payload = None
    expected = ('b12x_cute_' + key + '_cubin').encode() + b'\0'
    for section in symtabs:
        _, _, _, _, offset, length, link, info, _, entrysize = section
        if entrysize != 24 or not 24 <= length <= MAX_TABLE or length % 24 or not 0 < link < count or not 1 <= info <= length // 24:
            raise ValueError('invalid/oversized symbol table')
        budget.charge('symbols', length // 24)
        table = strings(file, sections[link], budget)
        raw = read_region(file, offset, length, budget)
        if any(raw[:24]):
            raise ValueError('invalid null symbol')
        for index, (name, symbol_info, _, section_index, value, symbol_size) in enumerate(struct.iter_unpack('<IBBHQQ', raw)):
            if index % 1024 == 0:
                budget.charge('symbols', 0)
            if name >= len(table):
                raise ValueError('invalid symbol string offset')
            if section_index >= count and section_index not in (0xfff1, 0xfff2):
                raise ValueError('invalid/unsupported symbol section index')
            if (symbol_info >> 4 == 0) != (index < info):
                raise ValueError('invalid local/global symbol ordering')
            # Final NUL above guarantees termination; compare a bounded prefix.
            if not table.startswith(expected, name):
                continue
            if symbol_info != 0x11 or not 0 < section_index < count or not symbol_size:
                raise ValueError('GPU symbol must be a defined GLOBAL OBJECT')
            owner = sections[section_index]
            if owner[1] != 1 or not owner[2] & 2 or value + symbol_size > owner[5]:
                raise ValueError('GPU payload outside allocated PROGBITS')
            if payload is not None:
                raise ValueError('duplicate GPU payload symbol')
            payload = dict(bytes=symbol_size, sha256=digest_region(file, owner[4] + value, symbol_size, budget))
    return dict(totals), payload


def inventory(path, budget=None):
    budget = budget if budget is not None else Budget()
    key = path.stem
    if path.suffix != '.o' or not re.fullmatch('[0-9a-f]{64}', key) or path.parent.name != key[:2]:
        raise ValueError('noncanonical object path')
    with checked_file(path.with_suffix('.json'), MAX_MANIFEST, 2) as (mf, msize):
        data = read_region(mf, 0, msize, budget)
        manifest, toolchain_sha = parse_manifest(data)
        with checked_file(path, MAX_OBJECT, 64) as (file, size):
            sha = digest_region(file, 0, size, budget)
            if manifest['cache_key'] != key or manifest['object_bytes'] != size or manifest['object_sha256'] != sha:
                raise ValueError('manifest key/size/digest mismatch')
            sections, payload = parse_elf(file, size, key, budget)
    row = dict(key=key, object_bytes=size, object_sha256=sha, schema=SCHEMA,
               cache_format=manifest['cache_format'], toolchain=manifest['toolchain'],
               toolchain_sha256=toolchain_sha, package_fingerprint=manifest['package_fingerprint'],
               manifest_sha256=hashlib.sha256(data).hexdigest(), sections=sections,
               gpu_payload=payload, gpu_payload_status='identified-export-symbol' if payload else 'UNKNOWN')
    budget.charge('row_bytes', len(json.dumps(row, sort_keys=True).encode()) + 2)
    return row


def discover(root, budget):
    paths, snapshots = [], {}
    def entries(directory):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            snapshots[directory] = signature(os.fstat(fd))
            with os.scandir(fd) as iterator:
                for entry in iterator:
                    budget.charge('entries', 1)
                    yield entry.name, entry.stat(follow_symlinks=False)
        finally:
            os.close(fd)
    for name, info in entries(root):
        shard = root / name
        if stat.S_ISLNK(info.st_mode):
            raise ValueError('symlink entry in cache root')
        if not stat.S_ISDIR(info.st_mode):
            if name.endswith('.o'):
                raise ValueError('object outside canonical shard')
            continue
        for leaf, info in entries(shard):
            if not leaf.endswith('.o'):
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('object is not a regular non-symlink file')
            if len(paths) >= MAX_OBJECTS:
                raise LimitExceeded('object count exceeds audit bound')
            paths.append(shard / leaf)
    return sorted(paths), snapshots


def summarize(rows, errors):
    totals, unique = collections.Counter(), collections.Counter()
    objects, payloads, identified = set(), {}, 0
    for row in rows:
        totals['object_bytes'] += row['object_bytes']
        totals.update(row['sections'])
        if row['object_sha256'] not in objects:
            objects.add(row['object_sha256'])
            unique['object_bytes'] += row['object_bytes']
            unique.update(row['sections'])
        if row['gpu_payload'] is not None:
            identified += 1
            payload = row['gpu_payload']
            totals['gpu_payload_subset_bytes'] += payload['bytes']
            payloads[(payload['sha256'], payload['bytes'])] = payload['bytes']
    return dict(version=2, scope='all-disk-objects-not-live-owners',
                accounting='file bytes and declared sections, not RAM; GPU bytes are a subset',
                complete=not errors, scan_complete=not errors, empty_cache=not rows and not errors,
                objects=len(rows), distinct_object_digests=len(objects), objects_with_gpu_symbol=identified,
                gpu_payload_coverage=dict(complete=not errors and bool(rows) and identified == len(rows),
                                          identified=identified, unknown=len(rows) - identified),
                totals_basis='per-path-disk-section-descriptors', totals=dict(totals),
                unique_object_totals=dict(unique),
                unique_gpu_payload_totals=dict(payloads=len(payloads), known_subset_bytes=sum(payloads.values())),
                errors=errors, artifacts=rows)


def scan(root):
    budget, rows, errors = Budget(), [], []
    try:
        paths, snapshots = discover(root, budget)
        for path in paths:
            try:
                rows.append(inventory(path, budget))
            except LimitExceeded:
                raise
            except (OSError, ValueError, struct.error) as error:
                errors.append(dict(key=path.stem[:64], error=str(error)[:512]))
        for directory, before in snapshots.items():
            if signature(directory.stat(follow_symlinks=False)) != before:
                raise ValueError('cache directory changed during audit')
    except (OSError, ValueError, struct.error) as error:
        errors.append(dict(key=None, error=str(error)[:512]))
    report = summarize(rows, errors)
    report['work'] = dict(budget.used)
    report['limits'] = dict(LIMITS, objects=MAX_OBJECTS, seconds=MAX_SECONDS,
                            object_bytes=MAX_OBJECT, manifest_bytes=MAX_MANIFEST,
                            nobits_per_object=MAX_NOBITS)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    report = scan(parser.parse_args().root)
    print(json.dumps(report, sort_keys=True))
    return not report['scan_complete']


if __name__ == '__main__':
    raise SystemExit(main())
