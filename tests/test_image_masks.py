"""PNG mask semantics and read-only noise rendering."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from editor import PatternLibrary, TemplateLibrary
from editor.render import render_rgb


class ImageMaskTests(unittest.TestCase):
    def test_pixels_alpha_orientation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'patch.v1.PNG'
            pixels=np.array([[(255,255,255,255),(0,0,0,255),(255,255,255,0)],
                             [(128,128,128,255),(127,127,127,255),(255,255,255,127)]],dtype=np.uint8)
            Image.fromarray(pixels).save(path)
            pattern=PatternLibrary.load(path)
            self.assertEqual(pattern.cells,((1,0,0),(1,0,0)))
            library=PatternLibrary(Path(tmp)/'library')
            self.assertEqual(PatternLibrary.load(library.save(pattern)),pattern)
            self.assertEqual(pattern.transform(90).cells,((1,1),(0,0),(0,0)))

    def test_empty_and_oversized_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'mask.png'
            for size,color in [((121,1),255),((2,2),0)]:
                Image.new('L',size,color).save(path)
                with self.assertRaises(ValueError): PatternLibrary.load(path)

    def test_noise_fixed_range_and_no_mutation(self):
        d=TemplateLibrary().create(400)
        ids=np.flatnonzero(d.geometry.playable)[1000:1003]
        d.change(3008,ids,np.array([0,32768,65535],dtype=np.uint16),'Test noise')
        before=d.edit_digest()
        rgb=render_rgb(d,'noise')
        np.testing.assert_array_equal(rgb[d.geometry.y[ids],d.geometry.x[ids]],
                                      [[0,0,0],[127,127,127],[255,255,255]])
        self.assertEqual(before,d.edit_digest())


if __name__=='__main__': unittest.main()
