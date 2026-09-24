import hashlib
import json
from pathlib import Path
from .document import MapDocument


class TemplateLibrary:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(__file__).resolve().parent / 'assets/templates'

    def create(self, size):
        if size not in (400, 500):
            raise ValueError('Supported new-map sizes: 400, 500')
        info = json.loads((self.directory / 'manifest.json').read_text(encoding='utf-8'))[str(size)]
        raw = (self.directory / info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != info['sha256']:
            raise ValueError('Template integrity check failed')
        document = MapDocument(raw, template=True)
        if document.size != size:
            raise ValueError('Incorrect template size')
        return document
