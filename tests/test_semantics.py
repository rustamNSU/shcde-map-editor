import io
from pathlib import Path
import struct
import unittest
import zipfile

from maptool import MapFile
from semantics import analyze, tile_index, tile_xy


class SemanticTests(unittest.TestCase):
    def test_all_storage_coordinates_are_bijective(self):
        for index in range(320800):
            self.assertEqual(tile_index(*tile_xy(index)), index)
        for point in ((0, 0), (799, 0), (400, 800), (400, -1)):
            with self.assertRaises(ValueError):
                tile_index(*point)

    def test_file_entities_independently_confirm_coordinates(self):
        for name, expected in [('3v3 Einstein SquaD.map', 73),
                               ('2v2 Einstein SquaD v2.0.map', 72),
                               ('001 3 green Fenrir - 6 wathcers.map', 56)]:
            with self.subTest(map=name):
                map_file = MapFile((Path('examples') / name).read_bytes())
                result = analyze(map_file)['entities']['buildings']
                self.assertEqual(result['active_count'], expected)
                self.assertEqual(result['coordinate_matches'], expected)
                self.assertEqual(result['distinct_referenced_slots'], expected)
                self.assertEqual(result['referenced_inactive_or_missing_slots'], [])
                self.assertTrue(all(r['referenced_tiles'] > 0 for r in result['records']))
                keeps = [r for r in result['records'] if r['type'] == 41]
                self.assertEqual(sorted(r['owner'] for r in keeps), list(range(1, 9)))

    def test_all_examples_rebuild_identically(self):
        examples = list(Path('examples').glob('*.map'))
        self.assertGreaterEqual(len(examples), 5)
        for path in examples:
            with self.subTest(map=path.name):
                data = path.read_bytes()
                parsed = MapFile(data)
                self.assertEqual(parsed.rebuild(), data)

    def test_preview_text_extension_preserved(self):
        data = Path('examples/2v2 Einstein SquaD v2.0.map').read_bytes()
        parsed = MapFile(data)
        self.assertEqual(len(parsed.preview_extra), 165)
        self.assertTrue(parsed.preview_extra.startswith(b'2v2 map, no wood.'))
        reparsed = MapFile(parsed.rebuild({1056: struct.pack('<I', 1182)}))
        self.assertEqual(parsed.preview_extra, reparsed.preview_extra)

    def test_se_style_appended_archive_survives_size_change(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('info.json', '{"name":"test"}')
        tail = archive.getvalue()
        parsed = MapFile(Path('examples/3v3 Einstein SquaD.map').read_bytes() + tail)
        payload = bytearray(parsed.section(3037)['decoded'])
        payload[150000:151024] = bytes(range(256)) * 4
        result = MapFile(parsed.rebuild({3037: bytes(payload)}))
        self.assertNotEqual(len(result.data), len(parsed.data))
        self.assertEqual(result.trailing, tail)
        with zipfile.ZipFile(io.BytesIO(result.trailing)) as stream:
            self.assertEqual(stream.read('info.json'), b'{"name":"test"}')


if __name__ == '__main__':
    unittest.main()
