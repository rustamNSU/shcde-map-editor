import unittest
from pathlib import Path
from editor import MapReader
from editor.services import EntityService

class CastleOrientationReferenceTests(unittest.TestCase):
    def test_save_extension_roundtrip_and_distinct_door_layouts(self):
        p=Path('output/castle-orientation-2026-09-21/ref_from_save_castle_orientation.map')
        d=MapReader.open(p)
        self.assertEqual(d.container.save_extension['size'],591)
        self.assertEqual(d.container.rebuild(),p.read_bytes())
        rows=EntityService(d).records('buildings')
        for owner,delta in [(1,(3,7)),(2,(3,-1)),(3,(-1,3))]:
            keep=next(r for r in rows if r['owner']==owner and r['type']==41)
            door=next(r for r in rows if r['owner']==owner and r['type']==73)
            self.assertEqual((door['x']-keep['x'],door['y']-keep['y']),delta)
