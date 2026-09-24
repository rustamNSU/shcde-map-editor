import unittest
import numpy as np
from editor import TemplateLibrary, TerrainService, MapWriter, MapReader
from editor.services import VariationService
from editor.cli import apply_recipe
from maptool import MapFile


class VariationTests(unittest.TestCase):
    def test_variation_roundtrip_preservation_boundary_undo(self):
        d=TemplateLibrary().create(400)
        before=d.edit_digest()
        ids=d.geometry.brush(400,400,5)
        boundary=np.flatnonzero(~d.geometry.playable)[:1]
        service=VariationService(d)
        report=service.paint(np.concatenate((ids,boundary)),65535)
        self.assertEqual(report['skipped_cells'],1)
        exported=MapFile(MapWriter.serialize(d))
        for section in d.container.sections:
            if section['id']!=3008:
                self.assertEqual(section['raw'],exported.section(section['id'])['raw'])
        actual=np.frombuffer(exported.section(3008)['decoded'],dtype='<u2')
        self.assertTrue(np.all(actual[ids]==65535))
        d.history.undo()
        self.assertEqual(d.edit_digest(),before)
        d.history.redo()
        self.assertTrue(np.all(d.grid(3008)[ids]==65535))
        for value in (-1,65536,True,1.5):
            with self.assertRaises(ValueError): service.paint(ids,value)

    def test_resource_repaint_and_uniform_variation_one_undo(self):
        d=TemplateLibrary().create(400)
        ids=d.geometry.brush(400,400,3)
        before=d.edit_digest()
        TerrainService(d).paint(ids,'stone',variation=1234)
        self.assertTrue(np.all(d.grid(3003)[ids]==0x28000))
        self.assertTrue(np.all(d.grid(3008)[ids]==1234))
        self.assertEqual(d.history.cursor,1)
        d.history.undo()
        self.assertEqual(d.edit_digest(),before)
        TerrainService(d).paint(ids,'iron')
        self.assertTrue(np.all(d.grid(3003)[ids]==0x88000))
        TerrainService(d).paint(ids,'earth')
        self.assertTrue(np.all(d.grid(3003)[ids]==0x8000))
        self.assertTrue(np.all(d.grid(3007)[ids]==16))

    def test_cli_variation(self):
        d=TemplateLibrary().create(500)
        apply_recipe(d,{'version':1,'operations':[
            {'op':'paint','material':'iron','variation':0,'rect':[400,400,2,2]},
            {'op':'set_variation','variation':32767,'rect':[400,400,1,1]}]})
        self.assertEqual(d.grid(3008)[d.geometry.index(400,400)],32767)
        self.assertEqual(d.grid(3008)[d.geometry.index(401,400)],0)
