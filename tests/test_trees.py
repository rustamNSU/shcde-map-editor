import unittest
import numpy as np
from editor import TemplateLibrary,MapDocument,MapWriter,MapValidator,EntityService
from editor.trees import TreeService,tree_catalog
from editor.buildings import BuildingService,H,catalog
from editor.services import HeightService

class TreeTests(unittest.TestCase):
    def test_catalog_place_remove_roundtrip(self):
        d=TemplateLibrary().create(400);s=TreeService(d)
        for n,k in enumerate(tree_catalog()):
            x,y=360+n*8,390
            self.assertEqual(s.paint(d.geometry.brush(x,y,1),k)['planted'],1)
        self.assertEqual(MapValidator.validate(d)['errors'],[])
        d=MapDocument(MapWriter.serialize(d)); s=TreeService(d)
        for n,k in enumerate(tree_catalog()):
            before=d.edit_digest(); s.remove(360+n*8,390);d.history.undo()
            self.assertEqual(before,d.edit_digest()); d.history.redo()
        self.assertFalse(EntityService(d).records('vegetation'))

    def test_brush_spacing_collision_undo(self):
        d=TemplateLibrary().create(500); s=TreeService(d); ids=d.geometry.brush(400,400,21)
        before=d.edit_digest();result=s.paint(ids,'2');self.assertGreater(result['planted'],10)
        after=d.edit_digest();self.assertEqual(s.paint(ids,'2')['planted'],0)
        self.assertEqual(d.edit_digest(),after); d.history.undo();self.assertEqual(d.edit_digest(),before)

    def test_castle_plateau(self):
        d=TemplateLibrary().create(400)
        HeightService(d).paint(d.geometry.rectangle(370,370,40,40),80)
        r=BuildingService(d).place('castle',380,380,3)
        templates=[v for v in catalog()['castle']['records'] if v['kind']=='buildings']
        for slot,template in zip(r['records']['buildings'],templates):
            self.assertEqual(H(d.section(4013)['decoded'],slot*812+0xec),H(bytes.fromhex(template['data']),0xec)+72)
        self.assertEqual(H(d.section(3015)['decoded'],r['records']['units'][0]*1168+0xba),80)
        self.assertEqual(MapValidator.validate(d)['errors'],[])
        BuildingService(d).remove(380,380)
        ids=d.geometry.rectangle(380,380,12,15)
        self.assertTrue(np.all(d.grid(3005)[ids]==80))

if __name__=='__main__':unittest.main()
