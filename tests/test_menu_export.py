"""Regressions for broken500 exports, native marker retention, and thumbnails."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from editor import MapReader,MapWriter,TemplateLibrary,BuildingService
from editor.preview import render_preview
from editor.menu import castle_markers,project_keep
from editor.services import EntityService
from maptool import MapFile

ROOT=Path(__file__).resolve().parents[1]
ADA=ROOT/'output/ada-resave-2026-09-20'


class MenuExportTests(unittest.TestCase):
    def test_repair_ada_on_explicit_save_without_edits(self):
        d=MapReader.open(ADA/'2v2 Ada_gui.map')
        native=MapReader.open(ADA/'2v2 Ada.map')
        self.assertEqual(MapWriter.serialize(d),d.original_bytes)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixed.map'
            MapWriter.save_as(d,path)
            fixed=MapFile(path.read_bytes())
        self.assertEqual(fixed.menu_metadata(),native.container.menu_metadata())
        for s in d.container.sections:
            self.assertEqual(fixed.section(s['id'])['raw'],s['raw'])
        self.assertEqual(fixed.description,d.container.description)
        self.assertEqual(fixed.trailing,d.container.trailing)
        self.assertEqual(fixed.preview_extra,d.container.preview_extra)
        self.assertFalse(d.dirty)
        image=np.asarray(render_preview(d))
        ys,xs=np.where(np.any(image!=0,axis=2))
        self.assertEqual((xs.min(),ys.min(),xs.max(),ys.max()),(18,17,183,182))
        self.assertEqual(castle_markers(d),{1:(40,126),2:(73,159),3:(130,36),4:(163,69)})

    def test_native_markers_preserved_and_projection_tolerance(self):
        for path in (ADA/'2v2 Ada.map',ROOT/'examples/3v3 Einstein SquaD.map'):
            d=MapReader.open(path)
            before=d.container.menu_metadata()
            fixed=MapFile(MapWriter.serialize(d,refresh_preview=True))
            self.assertEqual(before,fixed.menu_metadata())
            for r in EntityService(d).records('buildings'):
                if r['type']!=41 or not 1<=r['owner']<=8:continue
                marker=before['start_markers'][r['owner']-1]
                xy=project_keep(d.size,r['x'],r['y'])
                self.assertLessEqual(abs(xy[0]-marker['x']),1)
                self.assertEqual(xy[1],marker['y'])

    def test_new_500_castles_remove_and_undo_markers(self):
        d=TemplateLibrary().create(500)
        service=BuildingService(d)
        service.place('castle',347,527,1)
        service.place('castle',446,258,4)
        meta=MapFile(MapWriter.serialize(d)).menu_metadata()
        self.assertEqual(meta['players_count'],2)
        self.assertEqual((meta['start_markers'][3]['x'],meta['start_markers'][3]['y']),(163,69))
        service.remove(347,527)
        meta=MapFile(MapWriter.serialize(d)).menu_metadata()
        self.assertEqual(meta['players_count'],1)
        self.assertFalse(meta['start_markers'][0]['present'])
        d.history.undo()
        self.assertEqual(MapFile(MapWriter.serialize(d)).menu_metadata()['players_count'],2)
