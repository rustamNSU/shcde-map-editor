"""Read-only audit of the user's height map and native editor resave."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from maptool import MapFile,encode
from semantics import ENTITY_LAYOUTS,entity_report
from editor.document import GRID_TYPES

ROOT=Path(__file__).resolve().parents[1]
MAPS=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps')
OUT=ROOT/'output/ada-resave-2026-09-20'

def main():
    OUT.mkdir(exist_ok=True,parents=True); maps=[]; hashes={}
    for name in ('2v2 Ada_gui.map','2v2 Ada.map'):
        data=(MAPS/name).read_bytes();target=OUT/name
        if target.exists(): assert target.read_bytes()==data,'Snapshot would overwrite different bytes'
        else: target.write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest();m=MapFile(data);maps.append(m)
        colors=[(((v>>10)&31)*255//31,((v>>5)&31)*255//31,(v&31)*255//31) for (v,) in struct.iter_unpack('<H',m.preview[:512])]
        pixels=np.array(colors,dtype='uint8')[np.frombuffer(m.preview[512:],dtype='uint8')].reshape(200,200,3)
        Image.fromarray(pixels).resize((800,800),Image.Resampling.NEAREST).save(OUT/(name+'.preview.png'))
    a,b=maps; changes=[]
    for s in a.sections:
        t=b.section(s['id']); aa=s['decoded'];bb=t['decoded']
        if aa==bb: continue
        row=dict(section=s['id'],size_before=s['size'],size_after=t['size'],changed_bytes=sum(x!=y for x,y in zip(aa,bb)) if aa is not None and bb is not None else None)
        if aa is not None and bb is not None:
            if s['id'] in GRID_TYPES:
                x=np.frombuffer(aa,GRID_TYPES[s['id']]);y=np.frombuffer(bb,GRID_TYPES[s['id']]);mask=x!=y
                pairs,counts=np.unique(np.stack((x[mask],y[mask]),axis=1),axis=0,return_counts=True)
                row.update(changed_cells=int(mask.sum()),transitions=sorted([[int(x),int(y),int(c)] for (x,y),c in zip(pairs,counts)],key=lambda r:-r[2])[:30])
            elif len(aa)<=128:row.update(before_hex=aa.hex(),after_hex=bb.hex())
        changes.append(row)
    report=dict(hashes=hashes,menu_before=a.menu_metadata(),menu_after=b.menu_metadata(),
        headers={k:dict(before=v['hex'],after=b.headers[k]['hex']) for k,v in a.headers.items() if v['hex']!=b.headers[k]['hex']},
        preview=dict(decoded_sizes=[len(a.preview),len(b.preview)],palette_changed_bytes=sum(x!=y for x,y in zip(a.preview[:512],b.preview[:512])),indices_changed=sum(x!=y for x,y in zip(a.preview[512:],b.preview[512:])),extra_unchanged=a.preview_extra==b.preview_extra),
        description_unchanged=a.description==b.description,trailing_unchanged=a.trailing==b.trailing,
        sections=changes,entities={k:dict(before=entity_report(a,l)['records'],after=entity_report(b,l)['records']) for k,l in ENTITY_LAYOUTS.items()})
    report['entity_word_diffs']={}
    for kind,sid,stride in [('units',3015,1168),('buildings',4013,812)]:
        aa=a.section(sid)['decoded'];bb=b.section(sid)['decoded'];slots=[]
        for slot in range(len(aa)//stride):
            x=aa[slot*stride:(slot+1)*stride];y=bb[slot*stride:(slot+1)*stride]
            if x!=y:
                slots.append(dict(slot=slot,words=[dict(offset=hex(off),before=int.from_bytes(x[off:off+4],'little'),after=int.from_bytes(y[off:off+4],'little')) for off in range(0,stride,4) if x[off:off+4]!=y[off:off+4]]))
        report['entity_word_diffs'][kind]=slots
    report['lord_health']={name:[dict(slot=r['slot'],hp=struct.unpack_from('<I',m.section(3015)['decoded'],r['slot']*1168+0x3c8)[0]) for r in entity_report(m,ENTITY_LAYOUTS['units'])['records']] for name,m in [('gui',a),('native',b)]}
    empty=MapFile((ROOT/('editor/assets/templates/empty-%s.map' % a.menu_metadata()['map_size'])).read_bytes())
    report['preview']['before_identical_to_empty_template']=a.preview==empty.preview
    report['unchanged_sections']=[s['id'] for s in a.sections if s['decoded']==b.section(s['id'])['decoded']]
    report['player_word_diffs']={str(owner):[
        dict(offset=hex(off),before=struct.unpack_from('<I',a.section(2022)['decoded'],owner*0x583c+off)[0],
             after=struct.unpack_from('<I',b.section(2022)['decoded'],owner*0x583c+off)[0])
        for off in range(0,0x583c,4) if a.section(2022)['decoded'][owner*0x583c+off:owner*0x583c+off+4]!=b.section(2022)['decoded'][owner*0x583c+off:owner*0x583c+off+4]] for owner in range(9)}
    # Container-only experiment in memory, not a new map. Shows the preview is
    # independently replaceable without importing the resave's terrain changes.
    block=encode(b.preview)+a.preview_extra
    patched=MapFile(a.data[:4]+struct.pack('<I',len(block))+block+a.data[8+struct.unpack_from('<I',a.data,4)[0]:])
    assert patched.preview==b.preview
    assert patched.menu_metadata()==a.menu_metadata()
    assert all(patched.section(s['id'])['raw']==s['raw'] for s in a.sections)
    report['preview']['memory_only_replacement_preserves_all_section_bytes']=True
    for name,data in hashes.items(): assert hashlib.sha256((MAPS/name).read_bytes()).hexdigest()==data
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2))
    print('Report:', OUT/'comparison.json')
    print('Menu:', report['menu_before'], report['menu_after'])
    print('Changes:', [(r['section'],r['changed_bytes']) for r in changes])

if __name__=='__main__':main()
