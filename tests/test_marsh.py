import unittest
from pathlib import Path
import numpy as np
from editor import TemplateLibrary,TerrainService,MapReader,MapWriter
from editor.render import render_rgb
from maptool import MapFile


class MarshTests(unittest.TestCase):
    def test_reference_values_paint_undo_and_preservation(self):
        ref=MapReader.open(Path('output/references-2026-09-19/maps/ref_08_march_400.map'))
        marsh=np.flatnonzero(ref.grid(3003)==0x20008000)
        self.assertEqual(len(marsh),2589)
        for size in (400,500):
            d=TemplateLibrary().create(size)
            ids=d.geometry.brush(400,400,5)
            before=d.edit_digest()
            TerrainService(d).paint(ids,'marsh')
            for sid in (3003,3037,3005,3045,3006,3007,3009,3049):
                self.assertTrue(np.all(d.grid(sid)[ids]==ref.grid(sid)[marsh[0]]),sid)
            image=render_rgb(d,players=False)
            np.testing.assert_array_equal(image[400,400],[92,118,99])
            parsed=MapFile(MapWriter.serialize(d))
            for s in d.container.sections:
                if s['id']!=3003:self.assertEqual(s['raw'],parsed.section(s['id'])['raw'])
            d.history.undo();self.assertEqual(d.edit_digest(),before)
            d.history.redo();self.assertTrue(np.all(d.grid(3003)[ids]==0x20008000))
            TerrainService(d).paint(ids,'sand')
            self.assertTrue(np.all(d.grid(3003)[ids]==0x8000))
            self.assertTrue(np.all(d.grid(3037)[ids]==64))

    def test_resources_variation_and_protected_cells(self):
        d=TemplateLibrary().create(400);s=TerrainService(d)
        ids=d.geometry.brush(400,400,3)
        s.paint(ids,'iron');s.paint(ids,'marsh',variation=0)
        self.assertTrue(np.all(d.grid(3007)[ids]==16))
        self.assertTrue(np.all(d.grid(3008)[ids]==0))
        s.paint(ids,'stone');self.assertTrue(np.all(d.grid(3003)[ids]==0x28000))
        boundary=np.flatnonzero(~d.geometry.playable)[0]
        blocked=d.geometry.index(410,410)
        d.change(3012,[blocked],1,'occupied test cell')
        before=d.edit_digest()
        report=s.paint([boundary,blocked],'marsh')
        self.assertEqual(report['eligible_cells'],0)
        self.assertEqual(d.edit_digest(),before)
