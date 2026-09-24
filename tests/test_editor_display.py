import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from editor import TemplateLibrary
from editor.render import render_rgb, PLAYER_COLORS, castle_parts
from editor.settings import EditorSettings


class DisplayTests(unittest.TestCase):
    def test_castle_footprint_and_area(self):
        d = TemplateLibrary().create(400)
        # Same five-part layout observed in the castle reference, moved to center.
        parts = [dict(type=t,x=x,y=y,owner=1) for t,x,y in
                 [(41,397,393),(71,399,400),(73,400,400),(72,401,400),(55,397,401),(10,404,395)]]
        d._entity_cache = {'buildings':parts,'units':[],'vegetation':[]}
        d._entity_cache_revision=d.revision
        self.assertEqual(next(castle_parts(d))[2], (400,400))
        base = render_rgb(d, objects=False, players=False)
        color = np.array(PLAYER_COLORS[0])
        self.assertEqual(int(np.all(base==color,axis=2).sum()),101)
        self.assertFalse(np.all(base[395,404]==color))  # stockpile is not castle
        tinted = render_rgb(d,objects=False,players=True,area_opacity=25)
        changed = np.any(tinted!=base,axis=2)
        self.assertEqual(int(changed.sum()),141*141-101)
        ys,xs = np.where(changed)
        self.assertEqual((xs.min(),xs.max(),ys.min(),ys.max()),(330,470,330,470))
        np.testing.assert_array_equal(tinted[330,330],np.rint(base[330,330]*.75+color*.25))
        np.testing.assert_array_equal(render_rgb(d,objects=False,area_opacity=0),base)
        d=TemplateLibrary().create(500)
        d._entity_cache = {'buildings':parts,'units':[],'vegetation':[]}
        d._entity_cache_revision=d.revision
        base500=render_rgb(d,objects=False,players=False)
        tinted500=render_rgb(d,objects=False,area_opacity=25)
        changed500=np.any(tinted500!=base500,axis=2)
        self.assertEqual(int(changed500.sum()),161*161-101)
        ys,xs=np.where(changed500)
        self.assertEqual((xs.min(),xs.max(),ys.min(),ys.max()),(320,480,320,480))
        np.testing.assert_array_equal(tinted500[320,320],np.rint(base500[320,320]*.75+color*.25))
        self.assertFalse(changed500[319,400])
        self.assertFalse(changed500[481,400])
        self.assertFalse(d.dirty)

    def test_settings_first_run_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'Roaming/settings.json'
            settings = EditorSettings(path)
            self.assertTrue(path.exists())
            self.assertEqual(settings.values['castle_area_opacity'],25)
            settings.values['castle_area_opacity']=12
            settings.save()
            self.assertEqual(EditorSettings(path).values['castle_area_opacity'],12)
            path.write_text(json.dumps({'castle_area_opacity':-1}))
            self.assertEqual(EditorSettings(path).values['castle_area_opacity'],25)
