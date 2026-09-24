import json
from pathlib import Path
import tempfile
import unittest
from editor.recent import RecentFiles


class RecentFileTests(unittest.TestCase):
    def test_clear_persists_without_deleting_maps(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); saved=root/'keep.map';saved.write_bytes(b'untouched map')
            recent=RecentFiles(root/'recent.json');recent.remember(saved)
            recent.clear()
            self.assertEqual(RecentFiles(recent.path).files,[])
            self.assertEqual(saved.read_bytes(),b'untouched map')

    def test_limit_duplicates_order_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = RecentFiles(root/'recent-files.json')
            self.assertEqual(json.loads(history.path.read_text())['files'], [])
            for i in range(55):
                history.remember(root/('%s.map' % i))
            self.assertEqual(len(history.files),50)
            self.assertEqual(Path(history.files[-1]).name,'5.map')
            history.remember(root/'10.map')
            self.assertEqual(len(history.files),50)
            self.assertEqual(Path(history.files[0]).name,'10.map')
            self.assertEqual(RecentFiles(history.path).files,history.files)
            self.assertTrue(all(Path(p).is_absolute() for p in history.files))

    def test_invalid_file_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'recent-files.json'
            path.write_text('broken')
            history = RecentFiles(path)
            self.assertEqual(history.files,[])
            history.remember(Path(directory)/'saved.map')
            self.assertEqual(len(RecentFiles(path).files),1)
