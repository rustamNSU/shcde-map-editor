"""Persistent most-recent-first file paths, independent of GUI and map bytes."""
import json
import os
from pathlib import Path


class RecentFiles:
    limit = 50

    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('APPDATA', str(Path.home()))) / 'SHCDEMapEditor/recent-files.json'
        self.files = []
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version') == 1 and isinstance(data.get('files'), list):
                seen = set()
                for entry in data['files']:
                    if not isinstance(entry, str) or not entry.strip():
                        continue
                    normalized = str(Path(entry).resolve())
                    key = os.path.normcase(normalized)
                    if key not in seen:
                        self.files.append(normalized)
                        seen.add(key)
                    if len(self.files) == self.limit:
                        break
        except (OSError, ValueError, AttributeError):
            pass
        if not self.path.exists():
            self.save()

    def remember(self, path):
        normalized = str(Path(path).resolve())
        key = os.path.normcase(normalized)
        self.files = [normalized] + [p for p in self.files if os.path.normcase(p) != key]
        self.files = self.files[:self.limit]
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps({'version': 1, 'files': self.files}, indent=2), encoding='utf-8')
        temporary.replace(self.path)

    def clear(self):
        previous=self.files
        self.files=[]
        try:
            self.save()
        except OSError:
            self.files=previous
            raise
