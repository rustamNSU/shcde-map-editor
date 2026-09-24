from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from editor import TemplateLibrary, TerrainService, MapReader, MapWriter


class OverwriteTests(unittest.TestCase):
    def test_atomic_replace_failure_and_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'existing.map'
            d=TemplateLibrary().create(400)
            MapWriter.save_as(d,path)
            before=path.read_bytes()
            TerrainService(d).paint(d.geometry.brush(400,400,3),'sand')
            with self.assertRaises(FileExistsError): MapWriter.save_as(d,path)
            with patch('editor.document.os.replace',side_effect=PermissionError('Locked')):
                with self.assertRaises(PermissionError): MapWriter.save_as(d,path,overwrite=True)
            self.assertEqual(path.read_bytes(),before)
            self.assertTrue(d.dirty)
            self.assertEqual(list(Path(tmp).iterdir()),[path])
            MapWriter.save_as(d,path,overwrite=True)
            self.assertFalse(d.dirty)
            self.assertEqual(MapReader.open(path).grid(3037)[d.geometry.index(400,400)],64)
            self.assertEqual(list(Path(tmp).iterdir()),[path])
