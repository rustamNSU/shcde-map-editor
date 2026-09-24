"""Backend integration: byte preservation, history, boundaries and agent transactions."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from editor import (TemplateLibrary, MapReader, MapWriter, TerrainService, EntityService,
                    Pattern, PatternLibrary, MapValidator)
from editor.cli import apply_recipe, run
from maptool import MapFile


class EditorTests(unittest.TestCase):
    def test_opaque_player_lookup_is_preserved(self):
        from editor import MapDocument, BuildingService
        from editor.render import render_rgb
        template=TemplateLibrary().create(400)
        raw=bytearray(template.original_bytes)
        section=template.container.section(1190)
        self.assertTrue(section['compressed'])
        raw[section['offset']+12]=255  # Invalid blast literal-mode byte.
        d=MapDocument(raw)
        self.assertIsNone(d.section(1190)['decoded'])
        self.assertEqual(render_rgb(d).shape,(800,800,3))
        self.assertEqual(MapWriter.serialize(d),bytes(raw))
        before=d.edit_digest()
        BuildingService(d).place('castle',390,390,1)
        self.assertIsNotNone(MapFile(MapWriter.serialize(d)).section(1190)['decoded'])
        d.history.undo()
        self.assertEqual(d.edit_digest(),before)
        self.assertEqual(d.history.cursor,0)
        TerrainService(d).paint(d.geometry.brush(400,400,3),'oasis')
        exported=MapFile(MapWriter.serialize(d))
        self.assertEqual(exported.section(1190)['raw'],d.container.section(1190)['raw'])

    def test_templates_and_noop_exports_are_lossless(self):
        for size, expected in [(400,78804),(500,123504)]:
            d=TemplateLibrary().create(size)
            self.assertEqual(int(d.geometry.playable.sum()),expected)
            self.assertEqual(MapWriter.serialize(d),d.original_bytes)
            self.assertFalse(d.dirty)
            self.assertEqual(EntityService(d).records('units'),[])

    def test_stroke_history_and_unknown_sections(self):
        d=TemplateLibrary().create(400)
        with d.transaction('Two strokes'):
            TerrainService(d).paint(d.geometry.brush(400,400,9),'oasis')
            TerrainService(d).paint(d.geometry.brush(405,400,9),'sand')
        self.assertEqual(len(d.history.commands),1)
        self.assertTrue(d.dirty)
        exported=MapWriter.serialize(d)
        m=MapFile(exported)
        for section in d.container.sections:
            if section['id']!=3037:
                self.assertEqual(section['raw'],m.section(section['id'])['raw'])
        d.history.undo()
        self.assertFalse(d.dirty)
        self.assertEqual(MapWriter.serialize(d),d.original_bytes)
        d.history.redo()
        self.assertEqual(MapWriter.serialize(d),exported)

    def test_boundaries_and_object_cells_are_protected(self):
        d=TemplateLibrary().create(400)
        TerrainService(d).paint(np.arange(d.geometry.count),'oasis')
        orig=np.frombuffer(d.container.section(3037)['decoded'],dtype='u1')
        self.assertTrue(np.array_equal(d.grid(3037)[~d.geometry.playable],orig[~d.geometry.playable]))
        self.assertTrue(MapValidator.validate(d)['valid'])
        path=Path('output/leto-save-2026-09-19/snapshots/leto vs fbi 10.map')
        loaded=MapReader.open(path)
        occupied=[u for u in EntityService(loaded).records('units') if not u['anchor_reference']==u['slot']]
        self.assertTrue(occupied)
        ids=[u['tile_id'] for u in occupied]
        before=loaded.grid(3037)[ids].copy()
        TerrainService(loaded).paint(ids,'oasis')
        self.assertTrue(np.array_equal(before,loaded.grid(3037)[ids]))

    def test_failed_recipe_rolls_back_entire_batch(self):
        d=TemplateLibrary().create(400)
        recipe={'version':1,'operations':[{'op':'paint','material':'oasis','rect':[390,390,20,20]},
                                        {'op':'paint','material':'lava','rect':[395,395,2,2]}]}
        with self.assertRaises(ValueError):
            apply_recipe(d,recipe)
        self.assertEqual(MapWriter.serialize(d),d.original_bytes)
        self.assertEqual(d.history.cursor,0)

    def test_patterns_transform_persist_and_stamp(self):
        pattern=Pattern('Test mask',((1,0,0),(1,1,0)))
        self.assertEqual(pattern.transform(90).cells,((1,1),(1,0),(0,0)))
        with tempfile.TemporaryDirectory() as directory:
            lib=PatternLibrary(directory)
            path=lib.save(pattern)
            self.assertEqual(lib.load(path),pattern)
            with self.assertRaises(FileExistsError):
                lib.save(pattern)
            d=TemplateLibrary().create(500)
            result=TerrainService(d).paint(pattern.indices(d.geometry,400,400),'oasis')
            self.assertEqual(result['changed_field_values'],3)

    def test_resource_direct_paint_and_undo_all_linked_fields(self):
        d=TemplateLibrary().create(400)
        ids=d.geometry.brush(400,400,5)
        TerrainService(d).paint(ids,'iron')
        self.assertTrue(np.all(d.grid(3003)[ids]==0x88000))
        self.assertTrue(np.all(d.grid(3007)[ids]==2064))
        d.history.undo()
        self.assertEqual(MapWriter.serialize(d),d.original_bytes)

    def test_savepoint_branching_and_no_overwrite(self):
        d=TemplateLibrary().create(400)
        ids=d.geometry.brush(400,400,3)
        TerrainService(d).paint(ids,'oasis')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'new.map'
            MapWriter.save_as(d,path)
            self.assertFalse(d.dirty)
            with self.assertRaises(FileExistsError):
                MapWriter.save_as(d,path)
            d.history.undo()
            self.assertTrue(d.dirty)
            TerrainService(d).paint(ids,'sand')
            self.assertEqual(d.history.cursor,len(d.history.commands))
            self.assertTrue(d.dirty)

    def test_agent_dry_run_does_not_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            recipe=root/'recipe.json'
            recipe.write_text(json.dumps({'version':1,'operations':[{'op':'paint','material':'oasis','rect':[395,395,10,10]}]}))
            out=root/'not-written.map'
            report=root/'report.json'
            code=run(['--report',str(report),'edit','--size','500','--recipe',str(recipe),'--output',str(out),'--dry-run'])
            self.assertEqual(code,0)
            self.assertFalse(out.exists())
            self.assertEqual(json.loads(report.read_text())['validation']['changed_sections'],[3037])


if __name__=='__main__':
    unittest.main()
