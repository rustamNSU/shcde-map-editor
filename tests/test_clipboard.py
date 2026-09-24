import unittest
import numpy as np
from editor import TemplateLibrary,TerrainService
from editor.clipboard import MapClipboard

class ClipboardTests(unittest.TestCase):
 def test_layers_exact_values_undo_snapshot_and_scope(self):
  for layer,fields in [('surface',(3037,3008,3003,3007)),('height',(3005,3045)),('noise',(3008,))]:
   d=TemplateLibrary().create(400);g=d.geometry;source=g.rectangle(370,370,3,2);target=g.rectangle(410,410,3,2)
   if layer=='surface':
    for i,material in zip(source,['earth','oasis','sand','stone','iron','marsh']):TerrainService(d).paint([i],material)
    d.change(3008,source,[1,2,3,400,500,65535],'source')
   elif layer=='height':
    for sid in fields:d.change(sid,source,[8,9,12,40,60,130],'source')
   else:d.change(3008,source,[0,1,256,4096,32000,65535],'source')
   clip=MapClipboard.copy(d,(370,370,3,2),layer)
   expected={sid:d.grid(sid)[source].copy() for sid in fields}
   d.change(fields[0],source,0,'source changed after copy')
   before={sid:d.grid(sid).copy() for sid in d._grids};commands=len(d.history.commands)
   clip.paste(d,410,410)
   self.assertEqual(len(d.history.commands),commands+1)
   for sid in fields:np.testing.assert_array_equal(d.grid(sid)[target],expected[sid])
   for sid,values in before.items():
    if sid not in fields:np.testing.assert_array_equal(d.grid(sid),values)
   d.history.undo()
   for sid,values in before.items():np.testing.assert_array_equal(d.grid(sid),values)
 def test_protected_and_boundary_cells(self):
  d=TemplateLibrary().create(500);g=d.geometry
  TerrainService(d).paint(g.rectangle(380,380,3,2),'oasis')
  clip=MapClipboard.copy(d,(380,380,3,2),'surface')
  protected=g.index(410,410);d.change(3012,[protected],1,'occupied')
  result=clip.paste(d,410,410);self.assertEqual(result['eligible_cells'],5)
  self.assertEqual(d.grid(3037)[protected],0)
  self.assertEqual(clip.paste(d,-800,-800)['eligible_cells'],0)
if __name__=='__main__':unittest.main()
