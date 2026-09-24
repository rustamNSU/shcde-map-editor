"""Read-only castle-layout evidence from the user's populated save reference."""
import hashlib,json,struct
from pathlib import Path
from editor import MapReader
from editor.services import EntityService

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps/ref_from_save_castle_orientation.map')
OUT=ROOT/'output/castle-orientation-2026-09-21'

def main():
    data=SOURCE.read_bytes();digest=hashlib.sha256(data).hexdigest()
    OUT.mkdir(parents=True,exist_ok=True);snapshot=OUT/SOURCE.name
    if snapshot.exists():assert snapshot.read_bytes()==data
    else:snapshot.write_bytes(data)
    d=MapReader.open(snapshot);assert d.container.rebuild()==data
    rows=EntityService(d).records('buildings');raw=d.section(4013)['decoded']
    report=dict(source=str(SOURCE),sha256=digest,save_extension_size=d.container.save_extension['size'],castles=[])
    for keep in (r for r in rows if 40<=r['type']<=44):
        x,y=keep['x'],keep['y'];owner=keep['owner'];group=[]
        for r in rows:
            off=r['slot']*812
            root=struct.unpack_from('<I',raw,off+0x2a8)[0]
            # Initial nearby stockpile group; later player buildings excluded.
            if root==keep['global_id'] or (r['type']==10 and r['owner']==owner and abs(r['x']-x)<15 and abs(r['y']-y)<15):
                group.append(dict(slot=r['slot'],type=r['type'],relative=[r['x']-x,r['y']-y],
                    group_root=root,access_relative=[v-base for v,base in zip(struct.unpack_from('<HH',raw,off+0xfe),(x,y))]))
        report['castles'].append(dict(owner=owner,keep_type=keep['type'],origin=[x,y],parts=group))
    assert SOURCE.read_bytes()==data
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
