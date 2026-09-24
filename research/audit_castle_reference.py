"""Read-only reference audit; snapshot and reproduce current castle writer output."""
from pathlib import Path
import hashlib,json,struct
import numpy as np
from maptool import MapFile
from semantics import ENTITY_LAYOUTS,entity_report
from editor import TemplateLibrary,BuildingService,MapWriter

ROOT=Path(__file__).resolve().parents[1]
MAPS=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps')
OUT=ROOT/'output/castle-audit-2026-09-20'

def words(a,b):
    return [dict(offset=hex(i),reference=int.from_bytes(a[i:i+4],'little'),generated=int.from_bytes(b[i:i+4],'little'))
            for i in range(0,min(len(a),len(b)),4) if a[i:i+4]!=b[i:i+4]]

def diff(a,b):
    rows=[]
    for s in a.sections:
        t=b.section(s['id']);aa=s['decoded'];bb=t['decoded']
        if aa==bb: continue
        row=dict(section=s['id'],size=s['size'],changed_bytes=sum(x!=y for x,y in zip(aa,bb)) if aa is not None and bb is not None else None)
        if aa is not None and len(aa)<=128: row.update(before=aa.hex(),after=bb.hex())
        rows.append(row)
    return rows

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    path=MAPS/'ref_12_castle.map';raw=path.read_bytes();ref=MapFile(raw)
    size=ref.menu_metadata()['map_size']; d=TemplateLibrary().create(size)
    keep=next(r for r in entity_report(ref,ENTITY_LAYOUTS['buildings'])['records'] if r['type']==41)
    result=BuildingService(d).place('castle',keep['x'],keep['y'],1)
    generated=MapWriter.serialize(d); gen=MapFile(generated)
    for name,data in [('ref_12_castle.map',raw),('empty.map',d.original_bytes),('generated-current.map',generated)]:
        dest=OUT/name
        if dest.exists(): assert dest.read_bytes()==data,'Audit output already exists with different bytes'
        else: dest.write_bytes(data)
    er={name:{kind:entity_report(m,layout)['records'] for kind,layout in ENTITY_LAYOUTS.items()}
        for name,m in [('reference',ref),('generated',gen),('empty',d.container)]}
    report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),size=size,anchor=[keep['x'],keep['y']],
        empty_to_reference=diff(d.container,ref),empty_to_generated=diff(d.container,gen),
        reference_to_generated=diff(ref,gen),entities=er,
        lord_word_diffs=words(ref.section(3015)['decoded'][1168:2336],gen.section(3015)['decoded'][1168:2336]),
        player1_word_diffs=words(ref.section(2022)['decoded'][0x583c:2*0x583c],gen.section(2022)['decoded'][0x583c:2*0x583c]),
        building_word_diffs={str(slot):words(ref.section(4013)['decoded'][slot*812:(slot+1)*812],gen.section(4013)['decoded'][slot*812:(slot+1)*812]) for slot in range(1,10)})
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert path.read_bytes()==raw
    print('source',report['source_sha256'])
    print('empty -> ref',[(r['section'],r['changed_bytes']) for r in report['empty_to_reference']])
    print('empty -> generated',[(r['section'],r['changed_bytes']) for r in report['empty_to_generated']])
    print('lord differences',report['lord_word_diffs'])
    print('player1 differences',report['player1_word_diffs'])

if __name__=='__main__':main()
