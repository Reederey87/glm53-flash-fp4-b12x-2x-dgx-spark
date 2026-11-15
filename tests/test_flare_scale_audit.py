from pathlib import Path
import sys
import struct
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flare_scale_audit import e4m3, scale_boundary


class ScaleBoundaryTests(unittest.TestCase):
    def histogram(self, entries):
        result = [0] * 256
        for code, count in entries.items():
            result[code] = count
        return result

    def test_known_e4m3_boundaries_and_invalid_scales(self):
        for code, value in ((0, 0), (128, 0), (1, 1 / 512), (7, 7 / 512), (8, 1 / 64), (126, 448)):
            self.assertEqual(e4m3(code), value)
        for code in (127, 129, 255, -1, 256):
            with self.assertRaises(ValueError):
                e4m3(code)

    def test_full_layer_maximum_can_change_subset_conclusion(self):
        subset = scale_boundary(self.histogram({1: 10, 8: 1}))
        self.assertEqual(subset['nonzero_scales_below_packed_boundary'], 0)
        full = scale_boundary(self.histogram({1: 10, 8: 1, 126: 1}))
        self.assertEqual(full['full_layer_lifting_factor'], 1)
        self.assertEqual(full['nonzero_scales_below_packed_boundary'], 10)
        self.assertEqual(full['below_boundary_byte_counts'], {'1': 10})

    def test_zero_scales_and_missing_or_invalid_evidence(self):
        result = scale_boundary(self.histogram({0: 100}))
        self.assertEqual(result['zero_scale_count'], 100)
        self.assertEqual(result['nonzero_scales_below_packed_boundary'], 0)
        for histogram in ([0] * 256, [1] * 255, self.histogram({127: 1}), self.histogram({1: -1})):
            with self.assertRaises(ValueError):
                scale_boundary(histogram)

    def test_boundary_matches_independent_half_bit_encoding(self):
        for factor in (1, 2, 4, 8):
            for code in range(127):
                value = e4m3(code)
                if value * factor > 448:
                    continue
                lifted = value * factor * 128
                encoded_value = 0 if lifted < 2 else lifted
                half_bits = struct.unpack('<H', struct.pack('<e', encoded_value))[0]
                packed_byte = ((half_bits << 1) >> 8) & 255
                restored = struct.unpack('<e', struct.pack('<H', packed_byte << 7))[0] / (128 * factor)
                expected = 0 if 0 < value * factor < 1 / 64 else value
                self.assertEqual(restored, expected)


if __name__ == '__main__':
    unittest.main()
