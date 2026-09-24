"""In-memory document, explicit byte patches, transactional undo and lossless IO."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
import tempfile
import struct
from pathlib import Path
import numpy as np
from maptool import MapFile, u32
from .geometry import MapGeometry

GRID_TYPES = {3003: '<u4', 3037: 'u1', 3005: 'u1', 3045: 'u1',
              3004: '<u2', 3010: '<u2', 3012: '<u2', 3007: '<u2', 3008: '<u2'}
GRID_TYPES.update({3043:'u1',3006:'u1',3009:'<u2',3030:'u1',3020:'u1',
                   3026:'<u2',3118:'u1',3021:'<u2',3049:'u1',3028:'u1',
                   3029:'u1',3101:'u1',3103:'u1',3104:'u1'})
ENTITY_SECTIONS = (4013, 3015, 1014, 2022, 1035, 1190, 1191, 1031)


@dataclass
class RecoveredSection:
    section: int
    data: bytes


@dataclass
class Patch:
    section: int
    indices: np.ndarray
    before: np.ndarray
    after: np.ndarray


@dataclass
class EditCommand:
    label: str
    patches: list


class CommandHistory:
    def __init__(self, document):
        self.document = document
        self.commands = []
        self.cursor = 0

    def push(self, command):
        if not command.patches:
            return
        del self.commands[self.cursor:]
        self.commands.append(command)
        self.cursor += 1

    def undo(self):
        if self.document._transaction is not None:
            raise ValueError('Finish the current edit first')
        if self.cursor:
            self.cursor -= 1
            for patch in reversed(self.commands[self.cursor].patches):
                self.document._apply(patch, False)

    def redo(self):
        if self.document._transaction is not None:
            raise ValueError('Finish the current edit first')
        if self.cursor < len(self.commands):
            for patch in self.commands[self.cursor].patches:
                self.document._apply(patch, True)
            self.cursor += 1


class MapDocument:
    def __init__(self, source_bytes, source_path=None, template=False):
        self.original_bytes = bytes(source_bytes)
        self.container = MapFile(self.original_bytes)
        self.source_path = Path(source_path).resolve() if source_path else None
        self.is_template = template
        self.size = u32(self.container.section(1050)['decoded'])
        if self.container.version < 200 or self.container.capacity != 200:
            raise ValueError('The GUI/backend currently supports DE layouts only')
        self._grids = {}
        for sid, dtype in GRID_TYPES.items():
            data = self.container.section(sid)['decoded']
            if data is None:
                raise ValueError('Required grid %s is opaque' % sid)
            grid = np.frombuffer(data, dtype=dtype).copy()
            if len(grid) != MapGeometry.count:
                raise ValueError('Unexpected grid size: %s' % sid)
            self._grids[sid] = grid
        self.geometry = MapGeometry(self._grids[3003], self.size)
        for sid in ENTITY_SECTIONS:
            data=self.container.section(sid)['decoded']
            # Optional metadata can remain opaque. Preserve its stored bytes and
            # refuse only operations that depend on decoding that section.
            if data is not None:
                self._grids[sid] = np.frombuffer(data, dtype='u1').copy()
        self.history = CommandHistory(self)
        self._transaction = None
        self.revision = 0
        self.saved_digest = self.edit_digest()
        self.saved_path = None

    def grid(self, sid):
        """Read-only array view; all edits must go through commands."""
        view = self._grids[sid].view()
        view.flags.writeable = False
        return view

    def section(self, sid):
        """Current decoded section, compatible with the semantic reader."""
        if sid in self._grids:
            return dict(self.container.section(sid), decoded=self._grids[sid].tobytes())
        return self.container.section(sid)

    def replace_section(self, sid, data, label):
        if sid not in self._grids or len(data) != self._grids[sid].nbytes:
            raise ValueError('Unsupported section or changed section length')
        values = np.frombuffer(data, dtype=self._grids[sid].dtype)
        ids = np.flatnonzero(values != self._grids[sid])
        return self.change(sid, ids, values[ids], label)

    def replacements(self):
        return {sid: array.tobytes() for sid, array in self._grids.items()
                if array.tobytes() != self.container.section(sid)['decoded']}

    def edit_digest(self):
        h = hashlib.sha256()
        for sid in sorted(self._grids):
            h.update(self._grids[sid].tobytes())
        return h.hexdigest()

    @property
    def dirty(self):
        return self.edit_digest() != self.saved_digest

    def _apply(self, patch, forward):
        if isinstance(patch,RecoveredSection):
            if forward: self._grids[patch.section]=np.frombuffer(patch.data,dtype='u1').copy()
            else: self._grids.pop(patch.section,None)
            self.revision+=1
            return
        self._grids[patch.section][patch.indices] = patch.after if forward else patch.before
        self.revision += 1

    def recover_section(self,sid,data):
        if self._transaction is None: raise ValueError('Recovery requires a transaction')
        section=self.container.section(sid)
        if sid in self._grids or section['decoded'] is not None or len(data)!=section['size']:
            raise ValueError('Invalid section recovery')
        patch=RecoveredSection(sid,bytes(data))
        self._apply(patch,True)
        self._transaction.patches.append(patch)

    def change(self, sid, indices, values, label):
        if sid not in self._grids:
            raise ValueError('No supported editing operation for this section')
        indices = np.asarray(indices, dtype=np.int64)
        if len(np.unique(indices)) != len(indices):
            raise ValueError('Duplicate patch indices')
        if np.any(indices < 0) or np.any(indices >= len(self._grids[sid])):
            raise ValueError('Invalid tile index')
        arr = self._grids[sid]
        after = np.broadcast_to(np.asarray(values, dtype=arr.dtype), (len(indices),)).copy()
        changed = arr[indices] != after
        patch = Patch(sid, indices[changed], arr[indices[changed]].copy(), after[changed])
        if not len(patch.indices):
            return 0
        self._apply(patch, True)
        if self._transaction is not None:
            self._transaction.patches.append(patch)
        else:
            self.history.push(EditCommand(label, [patch]))
        return len(patch.indices)

    @contextmanager
    def transaction(self, label):
        if self._transaction is not None:
            yield
            return
        command = EditCommand(label, [])
        self._transaction = command
        try:
            yield
        except BaseException:
            for patch in reversed(command.patches):
                self._apply(patch, False)
            raise
        else:
            self.history.push(command)
        finally:
            self._transaction = None


class MapReader:
    @staticmethod
    def open(path):
        path = Path(path)
        return MapDocument(path.read_bytes(), path)


class MapWriter:
    @staticmethod
    def header(document, refresh_preview=None):
        from .services import EntityService
        from semantics import entity_report, ENTITY_LAYOUTS
        d=document
        header=bytearray(d.original_bytes[:d.container.directory_offset])
        before=[r for r in entity_report(d.container,ENTITY_LAYOUTS['buildings'])['records'] if 40<=r['type']<=44]
        after=[r for r in EntityService(d).records('buildings') if 40<=r['type']<=44]
        signature=lambda rows:sorted((r['owner'],r['type'],r['x'],r['y']) for r in rows)
        if refresh_preview is None: refresh_preview=bool(d.replacements())
        if d.size in (400,500) and (refresh_preview or signature(before)!=signature(after)):
            from .menu import castle_markers
            markers=castle_markers(d)
            struct.pack_into('<I',header,d.container.headers['u2']['offset']+4+24,len(markers))
            off=d.container.headers['u4']['offset']+4+16
            header[off:off+64]=bytes([255])*64
            for owner,xy in markers.items():
                struct.pack_into('<II',header,off+(owner-1)*8,*xy)
        if refresh_preview:
            from .preview import encode_preview
            from maptool import encode
            block=encode(encode_preview(d))+d.container.preview_extra
            end=8+struct.unpack_from('<I',header,4)[0]
            header=header[:4]+struct.pack('<I',len(block))+block+header[end:]
        return bytes(header)

    @staticmethod
    def serialize(document, refresh_preview=None):
        from .services import MapValidator
        report = MapValidator.validate(document)
        if report['errors']:
            raise ValueError('; '.join(report['errors']))
        replacements = document.replacements()
        recovered={sid for sid in replacements if document.container.section(sid)['decoded'] is None}
        if recovered-{1190}: raise ValueError('Unsupported section recovery')
        data = document.container.rebuild(replacements,recovered_sections=recovered)
        expected_header=MapWriter.header(document,refresh_preview)
        data=expected_header+data[document.container.directory_offset:]
        check = MapFile(data)
        for section in document.container.sections:
            sid = section['id']
            if sid in replacements:
                if check.section(sid)['decoded'] != replacements[sid]:
                    raise ValueError('Edited-section readback failed')
            elif check.section(sid)['raw'] != section['raw']:
                raise ValueError('Unrelated section changed')
        if check.trailing != document.container.trailing:
            raise ValueError('Trailing data changed')
        if data[:check.directory_offset] != expected_header:
            raise ValueError('Header changed unexpectedly')
        return data

    @staticmethod
    def save_as(document, path, overwrite=False):
        path = Path(path).resolve()
        if path.suffix.lower() != '.map':
            raise ValueError('Export destination must end in .map')
        if path.exists() and not overwrite:
            raise FileExistsError('Destination exists; explicit overwrite authorization is required')
        # Explicit exports refresh even a previously exported map whose thumbnail
        # is stale. Low-level no-op serialization stays byte-for-byte lossless.
        data = MapWriter.serialize(document,refresh_preview=True)
        if overwrite:
            # Validate on the same volume before atomically replacing the target.
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+path.name+'.', suffix='.tmp', delete=False) as stream:
                    temporary=Path(stream.name)
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if temporary.read_bytes()!=data:
                    raise IOError('Written map readback failed')
                os.replace(temporary,path)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        else:
            # Exclusive create protects against a destination appearing during validation.
            with path.open('xb') as stream:
                stream.write(data)
            if path.read_bytes() != data:
                raise IOError('Written map readback failed')
        document.saved_digest = document.edit_digest()
        document.saved_path = path
        return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
