import unittest
import numpy as np
from editor import TemplateLibrary, HeightService, MapWriter, MapDocument, BuildingService
from editor.render import render_rgb, HEIGHT_COLORS
from editor.cli import apply_recipe


class HeightTests(unittest.TestCase):
    def test_limits_protection_history_and_export(self):
        d=TemplateLibrary().create(400); g=d.geometry
        BuildingService(d).place('hovel',400,400)
        occupied=g.index(400,400); boundary=int(np.flatnonzero(~g.playable)[0])
        free=g.index(390,390); before=d.edit_digest()
        result=HeightService(d).paint([occupied,boundary,free],255)
        self.assertEqual(result['eligible_cells'],1)
        self.assertEqual(result['skipped_cells'],2)
        self.assertEqual(d.grid(3005)[free],255)
        self.assertEqual(d.grid(3045)[free],255)
        np.testing.assert_array_equal(render_rgb(d,'height')[390,390],HEIGHT_COLORS[255])
        after=d.edit_digest(); d.history.undo(); self.assertEqual(d.edit_digest(),before)
        d.history.redo(); self.assertEqual(d.edit_digest(),after)
        self.assertEqual(MapDocument(MapWriter.serialize(d)).grid(3005)[free],255)
        HeightService(d).paint([free],0)
        np.testing.assert_array_equal(render_rgb(d,'height')[390,390],HEIGHT_COLORS[0])
        for bad in (-1,256,1.5,True):
            with self.assertRaises(ValueError): HeightService(d).paint([free],bad)

    def test_recipe_and_height_only_preservation(self):
        d=TemplateLibrary().create(500)
        apply_recipe(d,{'version':1,'operations':[{'op':'set_height','height':128,'rect':[390,390,10,10]}]})
        self.assertEqual(set(d.replacements()),{3005,3045})
        exported=MapDocument(MapWriter.serialize(d))
        for s in d.container.sections:
            if s['id'] not in (3005,3045):
                self.assertEqual(s['raw'],exported.container.section(s['id'])['raw'])
        self.assertTrue(np.all(exported.grid(3005)[d.geometry.rectangle(390,390,10,10)]==128))

if __name__=='__main__': unittest.main()
