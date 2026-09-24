import struct,tempfile,unittest
from pathlib import Path
import numpy as np
from editor import TemplateLibrary,MapReader,MapDocument,MapWriter,BuildingService,TerrainService
from editor.preview import encode_preview,render_preview
from maptool import MapFile

class PreviewTests(unittest.TestCase):
    def test_changed_map_palette_castles_and_undo_both_sizes(self):
        for size in (400,500):
            d=TemplateLibrary().create(size)
            original=d.original_bytes;blank=encode_preview(d)
            TerrainService(d).paint(d.geometry.rectangle(360,360,25,25),'oasis')
            BuildingService(d).place('castle',400,410,1)
            preview=encode_preview(d)
            self.assertEqual(len(preview),40512)
            self.assertNotEqual(preview,blank)
            palette=np.frombuffer(preview[:512],dtype='<u2')
            self.assertTrue(np.all(palette<32768))
            image=np.asarray(render_preview(d))
            self.assertTrue(np.any(np.all(image==[223,59,48],axis=2)))
            parsed=MapFile(MapWriter.serialize(d))
            self.assertEqual(parsed.preview,preview)
            self.assertEqual(parsed.rebuild(),parsed.data)
            for s in d.container.sections:
                if s['id'] not in d.replacements():self.assertEqual(parsed.section(s['id'])['raw'],s['raw'])
            d.history.undo();d.history.undo()
            self.assertEqual(MapWriter.serialize(d),original)

    def test_explicit_save_refreshes_stale_preview_only(self):
        d=MapReader.open(Path('output/height-resave-2026-09-20/etest_height_00.map'))
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'fresh.map';MapWriter.save_as(d,out);m=MapFile(out.read_bytes())
            self.assertNotEqual(m.preview,d.container.preview)
            self.assertEqual(m.menu_metadata(),d.container.menu_metadata())
            for name in d.container.headers:self.assertEqual(m.headers[name]['hex'],d.container.headers[name]['hex'])
            for s in d.container.sections:self.assertEqual(m.section(s['id'])['raw'],s['raw'])
            self.assertFalse(d.dirty)

    def test_description_extension_save_prefix_and_tail_preserved(self):
        for path in [Path('examples/2v2 Einstein SquaD v2.0.map'),
                     Path('output/leto-save-2026-09-19/snapshots/leto vs fbi 10.map')]:
            d=MapDocument(path.read_bytes()+b'preview-test-trailing-data')
            before=d.container
            m=MapFile(MapWriter.serialize(d,refresh_preview=True))
            self.assertEqual(m.preview_extra,before.preview_extra)
            self.assertEqual(m.description,before.description)
            self.assertEqual(m.trailing,before.trailing)
            self.assertEqual(m.save_extension['hex'] if m.save_extension else None,
                             before.save_extension['hex'] if before.save_extension else None)
            for s in before.sections:self.assertEqual(m.section(s['id'])['raw'],s['raw'])

if __name__=='__main__':unittest.main()
