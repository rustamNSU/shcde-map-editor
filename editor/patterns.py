"""Material-independent binary masks, persisted under the user's Roaming folder."""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import numpy as np


@dataclass(frozen=True)
class Pattern:
    name: str
    cells: tuple
    tags: tuple = ()
    allow_empty: bool = field(default=False, compare=False, repr=False)

    def __post_init__(self):
        if not self.cells or not 1 <= len(self.cells) <= 120:
            raise ValueError('Mask height must be 1..120')
        width = len(self.cells[0])
        if not 1 <= width <= 120 or any(len(row) != width for row in self.cells):
            raise ValueError('Mask must be rectangular, at most 120x120')
        if any(v not in (0, 1) for row in self.cells for v in row) or (not self.allow_empty and not any(any(r) for r in self.cells)):
            raise ValueError('Mask needs at least one painted cell; values must be 0 or 1')
        if not isinstance(self.tags,(tuple,list)) or any(not isinstance(t,str) or not t.strip() or len(t)>40 for t in self.tags):
            raise ValueError('Tags must be nonempty strings of at most 40 characters')
        object.__setattr__(self,'tags',tuple(sorted(set(t.strip().casefold() for t in self.tags))))

    def transform(self, rotation=0, mirror=False, invert=False):
        if rotation not in (0, 90, 180, 270):
            raise ValueError('Rotation must be 0, 90, 180 or 270')
        mask = np.asarray(self.cells, dtype=np.uint8)
        if invert:
            mask=1-mask
        if mirror:
            mask = np.fliplr(mask)
        mask = np.rot90(mask, -(rotation//90))
        return Pattern(self.name, tuple(tuple(int(v) for v in row) for row in mask), self.tags, allow_empty=True)

    def indices(self, geometry, x, y):
        """x/y is the mask's upper-left cell in storage coordinates."""
        ids = []
        for dy, row in enumerate(self.cells):
            for dx, on in enumerate(row):
                if on:
                    try:
                        ids.append(geometry.index(x+dx, y+dy))
                    except ValueError:
                        pass
        return np.asarray(ids, dtype=np.int64)


class PatternLibrary:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(os.environ.get('APPDATA', str(Path.home()))) / 'SHCDEMapEditor/Patterns'

    def install_defaults(self, source=None):
        """Add bundled masks that are missing; never alter an existing user mask."""
        source = Path(source) if source is not None else Path(__file__).parent / 'assets/patterns'
        if not source.is_dir():
            raise FileNotFoundError('Bundled mask folder is missing: ' + str(source))
        defaults = sorted(source.glob('*.json'))
        if not defaults:
            raise FileNotFoundError('Bundled mask folder has no masks: ' + str(source))
        self.directory.mkdir(parents=True, exist_ok=True)
        added = 0
        for original in defaults:
            destination = self.directory / original.name
            if destination.exists():
                continue
            data = original.read_bytes()
            try:
                with destination.open('xb') as target:
                    target.write(data)
                added += 1
            except FileExistsError:
                # A second instance may have populated it since the check.
                continue
            except OSError:
                # A failed write must not leave a broken mask in the library.
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    pass
                raise
        return added

    @staticmethod
    def load(path):
        if Path(path).suffix.lower() == '.png':
            return PatternLibrary.load_image(path)
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
        if obj.get('version') != 1:
            raise ValueError('Unsupported pattern version')
        return Pattern(str(obj['name']), tuple(tuple(row) for row in obj['cells']), obj.get('tags',()))

    @staticmethod
    def load_image(path):
        """One PNG pixel per cell; light, opaque pixels paint, others skip."""
        from PIL import Image
        with Image.open(path) as image:
            if image.format != 'PNG':
                raise ValueError('Image masks must be PNG files')
            if not (1 <= image.width <= 120 and 1 <= image.height <= 120):
                raise ValueError('PNG masks must be 1..120 pixels per side; one pixel equals one map cell')
            rgba = image.convert('RGBA')
            light = np.asarray(rgba.convert('L')) >= 128
            opaque = np.asarray(rgba.getchannel('A')) >= 128
            cells = (light & opaque).astype(np.uint8)
        name = re.sub(r'[^\w -]', '_', Path(path).stem).strip()[:64] or 'Imported mask'
        return Pattern(name, tuple(tuple(int(v) for v in row) for row in cells))

    def save(self, pattern):
        if not re.fullmatch(r'[\w -]{1,64}', pattern.name) or pattern.name.strip() != pattern.name:
            raise ValueError('Use a name of 1..64 letters, digits, spaces, underscores or hyphens')
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (pattern.name + '.json')
        with path.open('x', encoding='utf-8') as f:
            json.dump({'version': 1, 'name': pattern.name, 'cells': pattern.cells, 'tags': pattern.tags}, f, indent=2)
        return path

    def set_tags(self, path, tags):
        path=Path(path).resolve()
        if path.parent!=self.directory.resolve() or path.suffix.lower()!='.json':
            raise ValueError('Select a mask in this library')
        pattern=self.load(path)
        updated=Pattern(pattern.name,pattern.cells,tags)
        obj=json.loads(path.read_text(encoding='utf-8'))
        obj['tags']=updated.tags
        temporary=path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(obj,indent=2),encoding='utf-8')
            temporary.replace(path)
        finally:
            if temporary.exists(): temporary.unlink()

    def replace(self, path, pattern):
        path=Path(path).resolve()
        if path.parent!=self.directory.resolve() or path.suffix.lower()!='.json':
            raise ValueError('Only masks in this library can be replaced')
        obj=json.loads(path.read_text(encoding='utf-8'))
        obj.update(version=1,name=pattern.name,cells=pattern.cells,tags=pattern.tags)
        temporary=path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(obj,indent=2),encoding='utf-8')
            temporary.replace(path)
        finally:
            if temporary.exists(): temporary.unlink()
        return path

    def list(self):
        return sorted(self.directory.glob('*.json')) if self.directory.exists() else []
