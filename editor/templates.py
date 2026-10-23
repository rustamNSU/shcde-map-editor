import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from maptool import MapFile
from .document import MapDocument
from .geometry import SUPPORTED_MAP_SIZES, empty_map_logic


@lru_cache(maxsize=8)
def _derive_empty(raw,size):
    """Retain an audited native empty template's opaque state and full noise."""
    m=MapFile(raw)
    grid=lambda sid,dtype:np.frombuffer(m.section(sid)['decoded'],dtype=dtype)
    # This is new-map construction only. Never erase an entity map or translate
    # unknown terrain/display values to make it resemble an empty template.
    if (any(np.any(grid(sid,'<u2')) for sid in (3004,3010,3012))
            or any(np.any(grid(sid,'u1')!=8) for sid in (3005,3045))
            or np.any(grid(3037,'u1'))):
        raise ValueError('Derived sizes require a known empty flat template')
    original_size=int.from_bytes(m.section(1050)['decoded'],'little')
    if not np.array_equal(grid(3003,'<u4'),empty_map_logic(original_size)):
        raise ValueError('The empty template has an unrecognized native boundary')
    old_playable=(grid(3003,'<u4')&0x30)==0
    if not np.array_equal(grid(3007,'<u2'),np.where(old_playable,16,0)):
        raise ValueError('The empty template has unrecognized ground display data')
    logic=empty_map_logic(size)
    replacements={1050:struct.pack('<I',size),3003:logic.tobytes(),
                  3007:np.where((logic&0x30)==0,16,0).astype('<u2').tobytes()}
    updated=bytearray(m.rebuild(replacements))
    # Header U4 stores the same native map size used by section1050. Prefix
    # length is unchanged by the section rebuild, so its verified offset holds.
    h=m.headers['u4']
    if h['size']<84: raise ValueError('Missing map-size menu metadata')
    struct.pack_into('<I',updated,h['offset']+4+80,size)
    d=MapDocument(bytes(updated),template=True)
    from .navigation import calculate
    edges,components,_=calculate(d)
    updated=d.container.rebuild({3030:edges.tobytes(),3021:components.tobytes()})
    final=MapDocument(updated,template=True)
    from .document import MapWriter
    header=MapWriter.header(final,refresh_preview=True)
    return header+updated[final.container.directory_offset:]


class TemplateLibrary:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(__file__).resolve().parent / 'assets/templates'

    def create(self, size):
        if type(size) is not int or size not in SUPPORTED_MAP_SIZES:
            raise ValueError('Supported new-map sizes: '+', '.join(map(str,SUPPORTED_MAP_SIZES)))
        manifest=json.loads((self.directory / 'manifest.json').read_text(encoding='utf-8'))
        info = manifest.get(str(size),manifest.get('500',manifest.get('400')))
        if info is None: raise ValueError('No audited native empty template is available')
        raw = (self.directory / info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != info['sha256']:
            raise ValueError('Template integrity check failed')
        if str(size) not in manifest: raw=_derive_empty(raw,size)
        document = MapDocument(raw, template=True)
        if document.size != size:
            raise ValueError('Incorrect template size')
        return document
