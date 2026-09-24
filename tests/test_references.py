"""Regression cases that previously failed with runtime-derived file offsets."""
from pathlib import Path
import unittest

from maptool import MapFile
from semantics import entity_report, ENTITY_LAYOUTS
from research.reference_findings import player_links

ROOT = Path(__file__).resolve().parents[1] / 'output/references-2026-09-19/maps'


class ReferenceTests(unittest.TestCase):
    def test_three_trees_link_back_to_their_saved_tile(self):
        fixtures = [('palm', 2, 402, 401), ('coconut_palm', 3, 401, 400),
                    ('olivee_tree', 1, 400, 400)]
        for name, typ, x, y in fixtures:
            with self.subTest(tree=name):
                m = MapFile((ROOT / ('ref_09_vege_%s_400.map' % name)).read_bytes())
                r = entity_report(m, ENTITY_LAYOUTS['vegetation'])
                self.assertEqual(r['active_count'], 1)
                self.assertEqual(r['coordinate_matches'], 1)
                self.assertEqual(r['referenced_inactive_or_missing_slots'], [])
                tree = r['records'][0]
                self.assertEqual((tree['slot'],tree['type'],tree['x'],tree['y']), (1,typ,x,y))
                self.assertEqual(tree['anchor_reference'], tree['slot'])

    def test_lord_reserved_slot_is_not_an_additional_unit(self):
        for name, player in [('p1_or_red', 1), ('p8_or_green', 8)]:
            with self.subTest(player=player):
                m=MapFile((ROOT/('ref_10_%s_castle_400.map'%name)).read_bytes())
                units=entity_report(m,ENTITY_LAYOUTS['units'])
                self.assertEqual(units['active_count'],1)
                self.assertEqual(units['records'][0]['slot'],1)
                self.assertEqual(units['records'][0]['type'],55)
                self.assertEqual(units['records'][0]['anchor_reference'],1)
                self.assertEqual(units['coordinate_matches'],1)
                links=player_links(m)
                self.assertEqual(len(links),1)
                self.assertEqual(links[0]['player'],player)
                self.assertEqual(links[0]['links']['keep']['slot'],1)
                self.assertEqual(links[0]['links']['first_stockpile']['slot'],6)
                self.assertEqual(links[0]['links']['campground_candidate']['slot'],5)

    def test_de_description_is_in_preview_extension(self):
        before=MapFile((ROOT/'ref_03_hill_400.map').read_bytes())
        after=MapFile((ROOT/'ref_03_hill_map_description_400.map').read_bytes())
        self.assertEqual(before.description,after.description)
        # The editor rewrites unused palette bytes 424..426 during this save;
        # visible pixels and actual tile sections are unchanged.
        self.assertEqual(before.preview[512:],after.preview[512:])
        for sid in (3003,3037,3005,3045):
            self.assertEqual(before.section(sid)['decoded'],after.section(sid)['decoded'])
        self.assertEqual(after.preview_text_bytes,b'abcdefgh & 1234567890')
        self.assertIsNone(before.preview_text_bytes)

    def test_old_einstein_unit_references_are_now_resolved(self):
        m=MapFile(Path('examples/3v3 Einstein SquaD.map').read_bytes())
        units=entity_report(m,ENTITY_LAYOUTS['units'])
        self.assertEqual(units['active_count'],8)
        self.assertEqual(units['coordinate_matches'],8)
        self.assertEqual(units['referenced_inactive_or_missing_slots'],[])


if __name__=='__main__':
    unittest.main()
