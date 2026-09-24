import unittest
import numpy as np
from editor import TemplateLibrary

class SymmetryTests(unittest.TestCase):
    def test_axes_exact_cell_reflection_both_sizes(self):
        for size in (400,500):
            g=TemplateLibrary().create(size).geometry
            x0,y0,x1,y1=g.bounds; x,y=370,380
            original=g.brush(x,y,1)
            for h,v in ((False,False),(True,False),(False,True),(True,True)):
                ids=g.symmetric_indices(original,h,v)
                expected={(xx,yy) for xx in ([x,x0+x1-1-x] if v else [x])
                          for yy in ([y,y0+y1-1-y] if h else [y])}
                self.assertEqual(set(zip(g.x[ids],g.y[ids])),expected)
            # Asymmetric/even masks reflect actual occupied cells, not a recentered stamp.
            ids=g.rectangle(395,398,4,7)[::3]
            sym=g.symmetric_indices(ids,True,True)
            np.testing.assert_array_equal(sym,g.symmetric_indices(sym,True,True))
            self.assertTrue(np.all(g.playable[sym]))
            np.testing.assert_array_equal(g.symmetric_indices([],True,True),[])

if __name__=='__main__': unittest.main()
