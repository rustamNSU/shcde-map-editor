import json,tempfile,unittest
from pathlib import Path
from editor import Pattern,PatternLibrary


class MaskTagTests(unittest.TestCase):
    def test_tags_old_masks_and_non_destructive_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib=PatternLibrary(tmp)
            path=lib.save(Pattern('A',((1,0),(0,1))))
            obj=json.loads(path.read_text());obj.pop('tags');obj['custom']='preserve'
            path.write_text(json.dumps(obj))
            self.assertEqual(lib.load(path).tags,())
            lib.set_tags(path,('Letters',' symbols ','letters'))
            self.assertEqual(lib.load(path).tags,('letters','symbols'))
            self.assertEqual(lib.load(path).cells,((1,0),(0,1)))
            self.assertEqual(json.loads(path.read_text())['custom'],'preserve')
            self.assertEqual(len(list(Path(tmp).iterdir())),1)

    def test_invert_transform_and_solid_mask(self):
        p=Pattern('L',((1,0,0),(1,1,0)),('letters',))
        self.assertEqual(p.transform(invert=True).cells,((0,1,1),(0,0,1)))
        self.assertEqual(p.transform(90,True,True).cells,((1,1),(0,1),(0,0)))
        self.assertEqual(p.transform(invert=True).tags,p.tags)
        self.assertEqual(p.cells,((1,0,0),(1,1,0)))
        self.assertEqual(Pattern('solid',((1,1),)).transform(invert=True).cells,((0,0),))
