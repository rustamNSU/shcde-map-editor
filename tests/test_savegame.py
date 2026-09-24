"""Regression coverage for the observed DE save prefix and dynamic records."""
import struct
import unittest
from pathlib import Path

from research.analyze_savegame import inspect
from maptool import MapFile

FIXTURES = Path(__file__).resolve().parents[1] / 'output/leto-save-2026-09-19/snapshots'


class SavegameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (FIXTURES / 'leto vs fbi 10.map').read_bytes()
        cls.parsed = MapFile(cls.raw)

    def test_real_save_and_renamed_map_rebuild_identically(self):
        self.assertEqual(self.raw, (FIXTURES / 'leto vs fbi 10 .msv').read_bytes())
        for path in FIXTURES.glob('*.msv'):
            with self.subTest(save=path.name):
                raw = path.read_bytes()
                parsed = MapFile(raw)
                self.assertEqual(parsed.rebuild(), raw)
                self.assertEqual(parsed.save_extension['size'], 97)
                self.assertEqual(parsed.count, 175)
                self.assertTrue(all(s['error'] is None for s in parsed.sections))

    def test_section_edit_preserves_save_prefix_and_other_blocks(self):
        payload = bytearray(self.parsed.section(3037)['decoded'])
        payload[150000:151024] = bytes(range(256)) * 4
        modified = MapFile(self.parsed.rebuild({3037: bytes(payload)}))
        self.assertEqual(modified.save_extension, self.parsed.save_extension)
        self.assertEqual(modified.data[:modified.directory_offset],
                         self.raw[:self.parsed.directory_offset])
        self.assertEqual(modified.section(3037)['decoded'], payload)
        self.assertNotEqual(modified.section(3037)['stored_size'],
                            self.parsed.section(3037)['stored_size'])
        for section in self.parsed.sections:
            if section['id'] != 3037:
                self.assertEqual(section['raw'], modified.section(section['id'])['raw'])

    def test_invalid_save_extension_does_not_trigger_directory_scanning(self):
        invalid = bytearray(self.raw)
        struct.pack_into('<I', invalid, self.parsed.save_extension['offset'], 96)
        with self.assertRaises(ValueError):
            MapFile(invalid)
        with self.assertRaises(ValueError):
            MapFile(self.raw[:self.parsed.directory_offset + 16])

    def test_workers_and_storage_totals_cross_validate_dynamic_records(self):
        report, units, links, resources = inspect(self.parsed, {})
        self.assertEqual(report['entity_counts']['units'], 1460)
        self.assertEqual(report['entity_counts']['buildings'], 638)
        self.assertEqual(report['unit_coordinate_checks']['current_matches'], 1460)
        self.assertEqual(len(links), 237)
        self.assertTrue(all(w['reciprocal_slot'] and w['reciprocal_gid'] and w['same_owner']
                            for w in links))
        self.assertTrue(all(r['equal'] for r in resources if r['good'] not in ('null', 'gold')))
        # Candidate target fields have genuine exceptions: don't invent a rule
        # that every cached position must be a synchronized coordinate triple.
        self.assertEqual(report['unit_coordinate_checks']['target_candidate_matches'], 1433)
        self.assertEqual(len(units), 1460)


if __name__ == '__main__':
    unittest.main()
