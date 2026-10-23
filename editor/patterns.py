"""Material-independent binary/height masks and read-only image conversion."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import re
import numpy as np

MAX_PATTERN_SIZE = 800


@dataclass(frozen=True)
class ImageImportSettings:
    width: int = 120
    height: int = 120
    mode: str = 'binary'
    threshold: int = 128
    alpha_threshold: int = 128
    invert: bool = False
    normalize: bool = False
    min_height: int = 8
    max_height: int = 130
    fit: str = 'contain'

    def __post_init__(self):
        for name in ('width', 'height'):
            if type(getattr(self, name)) is not int or not 1 <= getattr(self, name) <= MAX_PATTERN_SIZE:
                raise ValueError('Output width and height must be 1..%d cells' % MAX_PATTERN_SIZE)
        if self.mode not in ('binary', 'height'):
            raise ValueError('Image conversion mode must be binary or height')
        if self.fit not in ('contain', 'cover', 'stretch'):
            raise ValueError('Image fit must be contain, cover or stretch')
        for name in ('threshold', 'alpha_threshold', 'min_height', 'max_height'):
            if type(getattr(self, name)) is not int or not 0 <= getattr(self, name) <= 255:
                raise ValueError(name.replace('_', ' ').capitalize() + ' must be 0..255')
        if self.min_height > self.max_height:
            raise ValueError('Minimum height must not exceed maximum height')
        if type(self.invert) is not bool or type(self.normalize) is not bool:
            raise ValueError('Invert and normalize must be true or false')

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        if isinstance(values, cls):
            return values
        names = cls.__dataclass_fields__
        return cls(**{k: v for k, v in dict(values or {}).items() if k in names})

    @classmethod
    def for_image(cls, path):
        from PIL import Image, ImageOps
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            scale = min(1, 120 / max(image.size))
            return cls(width=max(1, round(image.width * scale)),
                       height=max(1, round(image.height * scale)))


@dataclass(frozen=True)
class Pattern:
    name: str
    cells: tuple
    tags: tuple = ()
    allow_empty: bool = field(default=False, compare=False, repr=False)
    heights: tuple = ()
    height_range: tuple = (0, 255)

    def __post_init__(self):
        if not self.cells or not 1 <= len(self.cells) <= MAX_PATTERN_SIZE:
            raise ValueError('Mask height must be 1..%d' % MAX_PATTERN_SIZE)
        width = len(self.cells[0])
        if not 1 <= width <= MAX_PATTERN_SIZE or any(len(row) != width for row in self.cells):
            raise ValueError('Mask must be rectangular, at most %dx%d' % (MAX_PATTERN_SIZE, MAX_PATTERN_SIZE))
        if any(v not in (0, 1) for row in self.cells for v in row) or (not self.allow_empty and not any(any(r) for r in self.cells)):
            raise ValueError('Mask needs at least one painted cell; values must be 0 or 1')
        if not isinstance(self.tags,(tuple,list)) or any(not isinstance(t,str) or not t.strip() or len(t)>40 for t in self.tags):
            raise ValueError('Tags must be nonempty strings of at most 40 characters')
        if (len(self.height_range) != 2 or any(type(v) is not int for v in self.height_range)
                or not 0 <= self.height_range[0] <= self.height_range[1] <= 255):
            raise ValueError('Height mask range must be minimum/maximum from 0..255')
        if self.heights:
            if len(self.heights) != len(self.cells) or any(len(row) != width for row in self.heights):
                raise ValueError('Height values must match the mask dimensions')
            lo, hi = self.height_range
            if any(type(v) is not int or not lo <= v <= hi for row in self.heights for v in row):
                raise ValueError('Height values must be whole numbers within the mask height range')
        object.__setattr__(self,'tags',tuple(sorted(set(t.strip().casefold() for t in self.tags))))
        object.__setattr__(self,'height_range',tuple(self.height_range) if self.heights else (0, 255))

    @property
    def is_height(self):
        return bool(self.heights)

    def transform(self, rotation=0, mirror=False, invert=False):
        if rotation not in (0, 90, 180, 270):
            raise ValueError('Rotation must be 0, 90, 180 or 270')
        mask = np.asarray(self.cells, dtype=np.uint8)
        heights = np.asarray(self.heights, dtype=np.uint8) if self.is_height else None
        if invert and heights is not None:
            heights = (sum(self.height_range) - heights.astype(np.int16)).astype(np.uint8)
        elif invert:
            mask=1-mask
        if mirror:
            mask = np.fliplr(mask)
            if heights is not None: heights = np.fliplr(heights)
        mask = np.rot90(mask, -(rotation//90))
        if heights is not None: heights = np.rot90(heights, -(rotation//90))
        return Pattern(self.name, tuple(tuple(int(v) for v in row) for row in mask), self.tags, allow_empty=True,
                       heights=tuple(tuple(int(v) for v in row) for row in heights) if heights is not None else (),
                       height_range=self.height_range)

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

    def height_samples(self, geometry, x, y):
        """Return corresponding cell IDs/heights, skipping holes and storage edges."""
        if not self.is_height:
            raise ValueError('This mask contains a binary shape, not height values')
        ids, values = [], []
        for dy, row in enumerate(self.cells):
            for dx, on in enumerate(row):
                if not on: continue
                try:
                    index = geometry.index(x + dx, y + dy)
                except ValueError:
                    continue
                ids.append(index); values.append(self.heights[dy][dx])
        return np.asarray(ids, dtype=np.int64), np.asarray(values, dtype=np.uint8)


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
        if Path(path).suffix.lower() != '.json':
            return PatternLibrary.load_image(path)
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
        if obj.get('version') not in (1, 2):
            raise ValueError('Unsupported pattern version')
        if obj.get('version') == 2 and obj.get('kind') != 'height':
            raise ValueError('Unsupported pattern kind')
        if obj.get('version') == 2 and not obj.get('heights'):
            raise ValueError('Height masks require a height-value matrix')
        return Pattern(str(obj['name']), tuple(tuple(row) for row in obj['cells']), obj.get('tags',()),
                       heights=tuple(tuple(row) for row in obj['heights']) if obj['version'] == 2 else (),
                       height_range=tuple(obj.get('height_range', (0, 255))))

    @staticmethod
    def load_image(path, settings=None):
        """Convert any Pillow-supported image; dimensions describe output map cells.

        Area averaging is used when shrinking and Lanczos when enlarging. Source
        EXIF orientation is honored. Contain preserves the whole image with
        transparent padding; cover crops; stretch uses independent axis scales.
        """
        from PIL import Image, ImageOps
        options = ImageImportSettings.for_image(path) if settings is None else ImageImportSettings.from_dict(settings)
        with Image.open(path) as image:
            oriented = ImageOps.exif_transpose(image)
            # Preserve high-bit grayscale gradients instead of Pillow's direct
            # I;16 -> RGBA conversion, which clips most values to white.
            if oriented.mode.startswith('I;16') or oriented.mode in ('I', 'F'):
                values = np.asarray(oriented, dtype=np.float64)
                finite = np.isfinite(values)
                lo, hi = (float(values[finite].min()), float(values[finite].max())) if finite.any() else (0, 0)
                if oriented.mode.startswith('I;16') or (oriented.mode == 'I' and 255 < hi <= 65535 and lo >= 0):
                    levels = values * (255 / 65535)
                elif oriented.mode == 'F' and 0 <= lo <= hi <= 1:
                    levels = values * 255
                elif 0 <= lo <= hi <= 255:
                    levels = values
                else:
                    levels = (values - lo) * (255 / max(1e-20, hi - lo))
                levels = np.nan_to_num(levels, nan=0, posinf=255, neginf=0).clip(0, 255).round().astype(np.uint8)
                rgba = Image.fromarray(levels).convert('RGBA')
            else:
                rgba = oriented.convert('RGBA')
            size = (options.width, options.height)
            downscale = rgba.width > options.width or rgba.height > options.height
            resampling = Image.Resampling.BOX if downscale else Image.Resampling.LANCZOS
            if options.fit == 'stretch':
                rgba = rgba.resize(size, resampling)
            elif options.fit == 'cover':
                rgba = ImageOps.fit(rgba, size, method=resampling)
            else:
                contained = ImageOps.contain(rgba, size, method=resampling)
                rgba = Image.new('RGBA', size, (0, 0, 0, 0))
                rgba.paste(contained, ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2))
            luminance = np.asarray(rgba.convert('L'), dtype=np.uint16)
            opaque = (np.asarray(rgba.getchannel('A')) >= options.alpha_threshold) & (np.asarray(rgba.getchannel('A')) > 0)
            if options.normalize and opaque.any():
                lo, hi = int(luminance[opaque].min()), int(luminance[opaque].max())
                if hi > lo:
                    luminance = ((luminance.astype(np.int32) - lo) * 255 / (hi - lo)).round().clip(0, 255).astype(np.uint16)
            if options.invert: luminance = 255 - luminance
            heights = ()
            if options.mode == 'height':
                cells = opaque.astype(np.uint8)
                values = options.min_height + (luminance * (options.max_height - options.min_height) + 127) // 255
                heights = tuple(tuple(int(v) for v in row) for row in values)
            else:
                cells = ((luminance >= options.threshold) & opaque).astype(np.uint8)
        name = re.sub(r'[^\w -]', '_', Path(path).stem).strip()[:64] or 'Imported mask'
        return Pattern(name, tuple(tuple(int(v) for v in row) for row in cells), heights=heights,
                       height_range=(options.min_height, options.max_height) if heights else (0, 255))

    @staticmethod
    def _payload(pattern):
        obj = {'version': 2 if pattern.is_height else 1, 'name': pattern.name,
               'cells': pattern.cells, 'tags': pattern.tags}
        if pattern.is_height:
            obj.update(kind='height', heights=pattern.heights, height_range=pattern.height_range)
        return obj

    def save(self, pattern):
        if not re.fullmatch(r'[\w -]{1,64}', pattern.name) or pattern.name.strip() != pattern.name:
            raise ValueError('Use a name of 1..64 letters, digits, spaces, underscores or hyphens')
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (pattern.name + '.json')
        with path.open('x', encoding='utf-8') as f:
            json.dump(self._payload(pattern), f, indent=2)
        return path

    def set_tags(self, path, tags):
        path=Path(path).resolve()
        if path.parent!=self.directory.resolve() or path.suffix.lower()!='.json':
            raise ValueError('Select a mask in this library')
        pattern=self.load(path)
        updated=Pattern(pattern.name,pattern.cells,tags,heights=pattern.heights,height_range=pattern.height_range)
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
        for key in ('kind', 'heights', 'height_range'): obj.pop(key, None)
        obj.update(self._payload(pattern))
        temporary=path.with_suffix('.json.tmp')
        try:
            temporary.write_text(json.dumps(obj,indent=2),encoding='utf-8')
            temporary.replace(path)
        finally:
            if temporary.exists(): temporary.unlink()
        return path

    def list(self):
        return sorted(self.directory.glob('*.json')) if self.directory.exists() else []
