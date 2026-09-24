"""Integration checks against the locally extracted research fixture."""
import struct
import unittest
from pathlib import Path

from maptool import MapFile, decode, encode


class MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = Path('output/einstein/original.map').read_bytes()
        cls.map = MapFile(cls.original)

    def test_lossless_roundtrip(self):
        self.assertEqual(self.map.rebuild(), self.original)
        self.assertEqual([s['id'] for s in self.map.sections if s['error']], [1190])

    def test_compressed_patch_moves_offsets_and_preserves_other_blocks(self):
        sid = 3037
        payload = bytearray(self.map.section(sid)['decoded'])
        # Deliberately nontrivial edit exercises changed compressed lengths.
        payload[150000:151024] = bytes(range(256)) * 4
        patched = MapFile(self.map.rebuild({sid: bytes(payload)}))
        self.assertEqual(patched.section(sid)['decoded'], payload)
        self.assertNotEqual(patched.section(sid)['stored_size'], self.map.section(sid)['stored_size'])
        for section in self.map.sections:
            if section['id'] != sid:
                self.assertEqual(section['raw'], patched.section(section['id'])['raw'])
        restored = MapFile(patched.rebuild({sid: self.map.section(sid)['decoded']}))
        self.assertEqual(restored.section(sid)['decoded'], self.map.section(sid)['decoded'])

    def test_uncompressed_patch(self):
        value = struct.pack('<I', 1182)
        patched = MapFile(self.map.rebuild({1056: value}))
        self.assertEqual(patched.section(1056)['decoded'], value)
        self.assertEqual(len(patched.data), len(self.original))

    def test_reject_unsafe_replacements(self):
        for replacement in ({999999: b''}, {3037: b''}, {1190: bytes(18)}):
            with self.assertRaises(ValueError):
                self.map.rebuild(replacement)

    def test_crc_and_truncation(self):
        block = bytearray(encode(b'test payload' * 100))
        block[8] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC32'):
            decode(block)
        with self.assertRaises(ValueError):
            MapFile(self.original[:-1])


if __name__ == '__main__':
    unittest.main()
