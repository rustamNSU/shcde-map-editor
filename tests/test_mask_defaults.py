import tempfile,unittest
from pathlib import Path
from editor.patterns import PatternLibrary,Pattern
from editor.gui import EditorWindow
from PySide6.QtWidgets import QApplication

class DefaultMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_bundled_masks_and_non_destructive_install(self):
        source=Path('editor/assets/patterns')
        originals=sorted(source.glob('*.json'))
        self.assertEqual(len(originals),186)
        self.assertEqual(len({path.name.casefold() for path in originals}),186)
        self.assertEqual({p.tags[0] for p in map(PatternLibrary.load, originals)},
                         {'pixel letters mono 11x8','pixel letters mono bold 11x8','perfect dos vga 437 13x9'})
        with tempfile.TemporaryDirectory() as temp:
            library=PatternLibrary(Path(temp)/'Patterns')
            self.assertEqual(library.install_defaults(),186)
            self.assertEqual(len(library.list()),186)
            chosen=library.directory/originals[0].name
            changed=chosen.read_bytes()+b'\n'
            chosen.write_bytes(changed)
            missing=library.directory/originals[1].name
            missing.unlink()
            extra=library.save(Pattern('My mask',((1,0),(0,1))))
            self.assertEqual(library.install_defaults(),1)
            self.assertEqual(chosen.read_bytes(),changed)
            self.assertEqual(missing.read_bytes(),originals[1].read_bytes())
            self.assertTrue(extra.exists())
            self.assertEqual(library.install_defaults(),0)

    def test_editor_startup_seeds_isolated_roaming_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'settings.json'
            window=EditorWindow(startup=False,settings_path=path)
            self.assertEqual(len(window.pattern_library.list()),186)
            self.assertEqual(window.brush_panel.gallery.count(),186)
            window.close()
            self.assertTrue(path.exists())

if __name__=='__main__':unittest.main()
