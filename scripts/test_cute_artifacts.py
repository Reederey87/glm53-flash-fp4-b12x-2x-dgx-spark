"""Offline synthetic ELF/manifest regressions; no native code loading."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit_cute_artifacts as audit

KEY = 'a' * 64
OTHER = 'b' * 64


def section(typ=0, flags=0, offset=0, size=0, link=0, info=0, entsize=0):
    return (0, typ, flags, 0, offset, size, link, info, 1 if typ else 0, entsize)


def elf(key=KEY, *, symbol=None, symbol_info=0x11, duplicate=False, extra=None):
    name = ('b12x_cute_' + key + '_cubin').encode() if symbol is None else symbol
    strings = b'\0' + name + b'\0'
    dataoff, stroff = 384, 400
    symoff = stroff + len(strings)
    entry = struct.pack('<IBBHQQ', 1, symbol_info, 0, 1, 0, 16)
    symbols = bytes(24) + entry * (2 if duplicate else 1)
    entries = [section(), section(1, 2, dataoff, 16), section(3, 0, stroff, len(strings)),
               section(2, 0, symoff, len(symbols), 2, len(symbols)//24 if symbol_info >> 4 == 0 else 1, 24),
               extra or section()]
    header = b'\x7fELF\x02\x01\x01' + bytes(9) + struct.pack('<HHIQQQIHHHHHH', 1, 183, 1, 0, 0, 64, 0, 64, 0, 0, 64, 5, 0)
    return header + b''.join(struct.pack('<IIQQQQIIQQ', *s) for s in entries) + b'x'*16 + strings + symbols


def change_section(data, index, field, value):
    result = bytearray(data)
    offset = 64 + index * 64
    fields = list(struct.unpack('<IIQQQQIIQQ', result[offset:offset+64]))
    fields[field] = value
    struct.pack_into('<IIQQQQIIQQ', result, offset, *fields)
    return bytes(result)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def store(self, data=None, key=KEY, **changes):
        data = elf(key) if data is None else data
        path = self.root / key[:2] / (key + '.o')
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        manifest = dict(schema=audit.SCHEMA, cache_key=key, object_bytes=len(data),
                        object_sha256=hashlib.sha256(data).hexdigest(),
                        cache_format='b12x_cute_compile_cache_v4',
                        package_fingerprint='pinned-package', toolchain=['cuda', {'version': '13'}])
        manifest.update(changes)
        path.with_suffix('.json').write_text(json.dumps(manifest))
        return path

    def test_valid_accounting_and_provenance(self):
        path = self.store()
        row = audit.inventory(path)
        self.assertEqual(row['sections']['alloc_readonly'], 16)
        self.assertEqual(row['gpu_payload']['bytes'], 16)
        self.assertEqual(row['gpu_payload']['sha256'], hashlib.sha256(b'x'*16).hexdigest())
        self.assertEqual(row['toolchain'], ['cuda', {'version': '13'}])
        self.assertEqual(row['toolchain_sha256'], hashlib.sha256(json.dumps(row['toolchain'], sort_keys=True).encode()).hexdigest())
        self.assertEqual(row['manifest_sha256'], hashlib.sha256(path.with_suffix('.json').read_bytes()).hexdigest())
        report = audit.scan(self.root)
        self.assertTrue(report['scan_complete'])
        self.assertTrue(report['gpu_payload_coverage']['complete'])
        self.assertEqual(report['totals']['gpu_payload_subset_bytes'], 16)
        self.assertEqual(report['totals']['alloc_readonly'], 16)  # Never add the subset twice.

    def test_actual_style_local_kernels_binary_is_unknown(self):
        self.store(elf(symbol=b'kernels_binary', symbol_info=1))
        report = audit.scan(self.root)
        self.assertTrue(report['scan_complete'])
        self.assertEqual(report['artifacts'][0]['gpu_payload_status'], 'UNKNOWN')
        self.assertIsNone(report['artifacts'][0]['gpu_payload'])
        self.assertEqual(report['gpu_payload_coverage'], dict(complete=False, identified=0, unknown=1))
        self.assertNotIn('gpu_payload_subset_bytes', report['totals'])

    def test_missing_symbol_table_is_unknown(self):
        data = change_section(elf(), 3, 1, 0)
        row = audit.inventory(self.store(data))
        self.assertIsNone(row['gpu_payload'])

    def test_overlap_and_header_intersections_rejected(self):
        for extra in (section(1, 2, 384, 16), section(1, 2, 0, 16), section(1, 2, 100, 16)):
            with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, 'overlapping'):
                audit.inventory(self.store(elf(extra=extra)))

    def test_bad_header_and_null_section(self):
        for offset, fmt, value in ((52, '<H', 0), (40, '<Q', 0), (56, '<H', 1), (60, '<H', 0)):
            data = bytearray(elf()); struct.pack_into(fmt, data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                audit.inventory(self.store(bytes(data)))
        with self.assertRaisesRegex(ValueError, 'null section'):
            audit.inventory(self.store(change_section(elf(), 0, 5, 123)))

    def test_inactive_section_fields_are_not_counted(self):
        row = audit.inventory(self.store(elf(extra=section(0, 2, 0, 2**63))))
        self.assertEqual(row['sections']['alloc_readonly'], 16)

    def test_nobits_bounded_and_separate_from_file_bytes(self):
        row = audit.inventory(self.store(elf(extra=section(8, 3, 2**60, 4096))))
        self.assertEqual(row['sections']['alloc_nobits'], 4096)
        self.assertLess(row['object_bytes'], 4096)
        with self.assertRaisesRegex(ValueError, 'NOBITS'):
            audit.inventory(self.store(elf(extra=section(8, 3, 0, audit.MAX_NOBITS+1))))

    def test_compressed_and_bad_section_ranges(self):
        for field, value in ((2, 2 | 0x800), (4, 2**40), (5, 2**40), (8, 3)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.inventory(self.store(change_section(elf(), 1, field, value)))

    def test_wrong_gpu_symbol_type_binding_and_duplicate(self):
        for data in (elf(symbol_info=0x12), elf(symbol_info=1), elf(duplicate=True)):
            with self.subTest(data=data[-24:]), self.assertRaises(ValueError):
                audit.inventory(self.store(data))

    def test_payload_symbol_bounds_and_indices(self):
        for offset, fmt, value in ((6, '<H', 0), (6, '<H', 0xffff), (8, '<Q', 15), (16, '<Q', 0)):
            data = bytearray(elf()); struct.pack_into(fmt, data, len(data)-24+offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                audit.inventory(self.store(bytes(data)))

    def test_string_table_and_symbol_table_validation(self):
        data = elf()
        str_end = 400 + len(b'\0b12x_cute_' + KEY.encode() + b'_cubin\0')
        bad_string = data[:str_end-1] + b'x' + data[str_end:]
        for bad in (bad_string, change_section(data, 3, 9, 8), change_section(data, 3, 6, 1)):
            with self.subTest(bad=bad[-24:]), self.assertRaises(ValueError):
                audit.inventory(self.store(bad))
        bad = bytearray(data); struct.pack_into('<I', bad, len(bad)-24, 2**32-1)
        with self.assertRaisesRegex(ValueError, 'string offset'):
            audit.inventory(self.store(bytes(bad)))

    def test_manifest_schema_types_and_integrity(self):
        for changes in (dict(schema='v3'), dict(object_bytes=True), dict(object_sha256='b'*64),
                        dict(cache_key=OTHER), dict(toolchain=None), dict(package_fingerprint=42)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                audit.inventory(self.store(**changes))

    def test_malformed_manifests_are_per_artifact_errors(self):
        path = self.store()
        for raw in ('[]', 'null', '{"schema":1,"schema":2}', '{', '['*1100+'0'+']'*1100,
                    '{"nested":'+'['*33+'0'+']'*33+'}', '{"x":NaN}'):
            path.with_suffix('.json').write_text(raw)
            with self.subTest(raw=raw[:40]):
                report = audit.scan(self.root)
                self.assertFalse(report['scan_complete'])
                self.assertEqual(len(report['errors']), 1)

    def test_manifest_and_object_size_bounds(self):
        path = self.store()
        with patch.object(audit, 'MAX_MANIFEST', 16), self.assertRaisesRegex(ValueError, 'bounds'):
            audit.inventory(path)
        with patch.object(audit, 'MAX_OBJECT', 64), self.assertRaisesRegex(ValueError, 'bounds'):
            audit.inventory(path)

    def test_missing_file_and_empty_root_are_distinct(self):
        for root in (self.root/'absent', self.store()):
            self.assertFalse(audit.scan(root)['scan_complete'])
        empty = self.root/'empty'; empty.mkdir()
        report = audit.scan(empty)
        self.assertTrue(report['scan_complete'])
        self.assertTrue(report['empty_cache'])
        self.assertFalse(report['gpu_payload_coverage']['complete'])

    def test_symlink_and_fifo_rejected_without_blocking(self):
        path = self.store(); manifest = path.with_suffix('.json')
        backup = self.root/'manifest'; manifest.rename(backup); manifest.symlink_to(backup)
        self.assertFalse(audit.scan(self.root)['scan_complete'])
        manifest.unlink(); os.mkfifo(manifest)
        self.assertFalse(audit.scan(self.root)['scan_complete'])
        manifest.unlink(); backup.rename(manifest)
        target = self.root/'target'; path.rename(target); path.symlink_to(target)
        self.assertFalse(audit.scan(self.root)['scan_complete'])
        path.unlink(); target.rename(path)
        shard = path.parent; moved = self.root/'moved'; shard.rename(moved); shard.symlink_to(moved)
        self.assertFalse(audit.scan(self.root)['scan_complete'])

    def test_changes_during_parse_are_rejected(self):
        path = self.store()
        original = audit.parse_elf
        def mutate(*args):
            result = original(*args)
            with path.open('ab') as file: file.write(b'x')
            return result
        with patch.object(audit, 'parse_elf', side_effect=mutate), self.assertRaisesRegex(ValueError, 'changed'):
            audit.inventory(path)

    def test_replacement_and_directory_changes_rejected(self):
        path = self.store(); original = audit.parse_elf
        def replace(*args):
            result = original(*args)
            other = path.with_suffix('.replacement'); other.write_bytes(path.read_bytes()); other.replace(path)
            return result
        with patch.object(audit, 'parse_elf', side_effect=replace), self.assertRaisesRegex(ValueError, 'changed'):
            audit.inventory(path)
        original_inventory = audit.inventory
        def add_file(*args):
            row = original_inventory(*args)
            (path.parent/'new-file').write_text('changed')
            return row
        with patch.object(audit, 'inventory', side_effect=add_file):
            self.assertFalse(audit.scan(self.root)['scan_complete'])

    def test_enumeration_errors_not_silent(self):
        with patch.object(audit.os, 'scandir', side_effect=PermissionError('denied')):
            self.assertFalse(audit.scan(self.root)['scan_complete'])

    def test_aggregate_limits_stop_with_incomplete_report(self):
        self.store()
        for field in ('entries', 'read_bytes', 'sections', 'symbols', 'row_bytes'):
            with self.subTest(field=field), patch.dict(audit.LIMITS, {field: 0}):
                report = audit.scan(self.root)
                self.assertFalse(report['scan_complete'])
                self.assertIn('limit', report['errors'][-1]['error'])
        with patch.object(audit, 'MAX_OBJECTS', 0):
            self.assertFalse(audit.scan(self.root)['scan_complete'])
        with patch.object(audit, 'MAX_SECONDS', -1):
            self.assertFalse(audit.scan(self.root)['scan_complete'])
        self.store(elf(extra=section(8, 3, 0, 1)))
        with patch.dict(audit.LIMITS, {'nobits': 0}):
            self.assertFalse(audit.scan(self.root)['scan_complete'])

    def test_dedup_object_and_payload_totals(self):
        first = audit.inventory(self.store())
        duplicate = audit.inventory(self.store(elf(), key=OTHER))  # Same content, different key: unknown symbol.
        report = audit.summarize([first, duplicate], [])
        self.assertEqual(report['distinct_object_digests'], 1)
        self.assertEqual(report['totals']['object_bytes'], first['object_bytes']*2)
        self.assertEqual(report['unique_object_totals']['object_bytes'], first['object_bytes'])
        second = audit.inventory(self.store(key=OTHER))  # Different object/prefix, identical payload bytes.
        report = audit.summarize([first, second], [])
        self.assertEqual(report['distinct_object_digests'], 2)
        self.assertEqual(report['totals']['gpu_payload_subset_bytes'], 32)
        self.assertEqual(report['unique_gpu_payload_totals'], dict(payloads=1, known_subset_bytes=16))

    def test_mixed_errors_preserve_valid_rows(self):
        self.store(); bad = self.store(key=OTHER); bad.with_suffix('.json').write_text('[]')
        report = audit.scan(self.root)
        self.assertFalse(report['scan_complete'])
        self.assertEqual(report['objects'], 1)
        self.assertFalse(report['gpu_payload_coverage']['complete'])

    def test_cli_missing_root_is_nonzero_json(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['audit', str(self.root/'absent')]), contextlib.redirect_stdout(output):
            self.assertTrue(audit.main())
        self.assertFalse(json.loads(output.getvalue())['scan_complete'])


if __name__ == '__main__':
    unittest.main()
