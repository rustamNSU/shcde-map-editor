import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QDialog,QLineEdit,QMessageBox
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from editor.patterns import Pattern,PatternLibrary
from editor.mask_editor import MaskEditor

class MaskEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_edit_resize_invert_save_and_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            library=PatternLibrary(tmp);path=library.save(Pattern('Original',((1,0),(0,1)),('old',)))
            dialog=MaskEditor(None,library,library.load(path),path)
            QTest.mouseClick(dialog.canvas,Qt.MouseButton.LeftButton,pos=QPoint(24,8))
            self.assertEqual(dialog.canvas.cells[0,1],1)
            dialog.columns.setValue(120);dialog.rows.setValue(120)
            self.assertEqual(dialog.canvas.cells[119,119],0)
            dialog.invert();self.assertEqual(dialog.canvas.cells[119,119],1)
            dialog.tags.setText('Letters, New');dialog.save()
            self.assertEqual(dialog.result(),QDialog.DialogCode.Accepted)
            saved=library.load(path);self.assertEqual(len(saved.cells),120);self.assertEqual(saved.tags,('letters','new'))
            original=path.read_bytes()
            copy=MaskEditor(None,library,saved,path);copy.invert()
            def accept_name(d):
                fields=d.findChildren(QLineEdit);fields[0].setText('Copy');fields[1].setText('symbols')
                return QDialog.DialogCode.Accepted
            with patch('editor.mask_editor.QDialog.exec',accept_name):copy.save_as()
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(library.load(copy.saved_path).tags,('symbols',))
            self.assertEqual(copy.result(),QDialog.DialogCode.Accepted)
    def test_zoom_fit_and_pixel_hit_testing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pattern=Pattern('Large',tuple(tuple(int(x==y) for x in range(120)) for y in range(120)))
            dialog=MaskEditor(None,PatternLibrary(tmp),pattern)
            dialog.show();self.app.processEvents();dialog.fit_mask();self.app.processEvents()
            self.assertLessEqual(dialog.canvas.height(),dialog.scroll.viewport().height())
            self.assertLessEqual(dialog.canvas.width(),dialog.scroll.viewport().width())
            dialog.zoom.setValue(200)
            self.assertEqual(dialog.canvas.pixel_size,32)
            QTest.mouseClick(dialog.canvas,Qt.MouseButton.LeftButton,pos=QPoint(48,16))
            self.assertEqual(dialog.canvas.cells[0,1],1)
            self.assertEqual(dialog.rows.value(),120)
            with patch('editor.mask_editor.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):dialog.reject()

    def test_close_warns_and_cancel_keeps_mask_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            library=PatternLibrary(tmp);path=library.save(Pattern('Mask',((1,0),)))
            original=path.read_bytes()
            dialog=MaskEditor(None,library,library.load(path),path)
            dialog.show();self.app.processEvents();dialog.invert()
            with patch('editor.mask_editor.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel) as warning:
                self.assertFalse(dialog.close());warning.assert_called_once()
                self.assertTrue(dialog.isVisible())
            with patch('editor.mask_editor.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard):
                self.assertTrue(dialog.close())
            self.assertEqual(path.read_bytes(),original)

    def test_cancel_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            library=PatternLibrary(Path(tmp)/'masks');dialog=MaskEditor(None,library,Pattern('Imported',((1,),)))
            dialog.reject();self.assertFalse(library.directory.exists())
    def test_dimensions_reject_above_limit(self):
        with self.assertRaises(ValueError):Pattern('Too wide',(tuple([1]*121),))

if __name__=='__main__':unittest.main()
