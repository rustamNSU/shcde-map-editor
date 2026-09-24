"""Template-based experimental three-player map. Originals are never overwritten.

Coordinate fields are corroborated by TWO same-type castle complexes, not by
blindly treating every small integer as a coordinate. Game testing is still needed.
"""
from pathlib import Path
import json,struct
import numpy as np
from PIL import Image,ImageDraw
from maptool import MapFile,require,u32
from semantics import tile_index,tile_xy,entity_report,ENTITY_LAYOUTS
from research.analyze_references import grids,XY,objects,sha
from research.reference_findings import player_links

ROOT=Path(__file__).resolve().parents[1]
MAPS=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps')
OUT=ROOT/'output/three-castle-oasis-grid'
NAME='etest_oasis_grid_3_castles_400.map'
ANCHORS=[(403,534),(399,243)]
TARGETS=[(397,397),(375,260),(415,260)]

def getrec(m,sid,stride,slot):
    return bytes(m.section(sid)['decoded'][slot*stride:(slot+1)*stride])

def infer_positions(a,b):
    """Require exactly the same relative coordinate in two independent records."""
    found=[];used=set()
    for fmt,width,step,scale in [('<HH',4,2,1),('<HH',4,2,8),('<II',8,4,1),('<II',8,4,8)]:
        for off in range(0,len(a)-width+1,step):
            x,y=struct.unpack_from(fmt,a,off);xx,yy=struct.unpack_from(fmt,b,off)
            if (x,y)==(xx,yy):continue
            rel=(x-ANCHORS[0][0]*scale,y-ANCHORS[0][1]*scale)
            if rel!=(xx-ANCHORS[1][0]*scale,yy-ANCHORS[1][1]*scale):continue
            if not all(abs(v)<30*scale for v in rel):continue
            require(not any(i in used for i in range(off,off+width)),'Overlapping coordinate interpretations')
            found.append(dict(offset=off,kind=fmt,scale=scale));used.update(range(off,off+width))
    for off in range(0,len(a)-3,4):
        if any(i in used for i in range(off,off+4)):continue
        v,w=u32(a,off),u32(b,off)
        if not (v!=w and v<320800 and w<320800):continue
        x,y=tile_xy(v);xx,yy=tile_xy(w)
        rel=(x-ANCHORS[0][0],y-ANCHORS[0][1])
        if rel==(xx-ANCHORS[1][0],yy-ANCHORS[1][1]) and all(abs(n)<30 for n in rel):
            found.append(dict(offset=off,kind='tile',scale=1));used.update(range(off,off+4))
    return found,used

def relocate(record,positions,old,target):
    data=bytearray(record);dx,dy=target[0]-old[0],target[1]-old[1]
    for f in positions:
        off=f['offset']
        if f['kind']=='tile':
            x,y=tile_xy(u32(record,off));struct.pack_into('<I',data,off,tile_index(x+dx,y+dy))
        else:
            fmt=f['kind'];x,y=struct.unpack_from(fmt,record,off);s=f['scale']
            struct.pack_into(fmt,data,off,x+dx*s,y+dy*s)
    return data

def main():
    dest=MAPS/NAME
    require(not dest.exists() and not (OUT/NAME).exists(),'Destination already exists')
    source=MAPS/'ref_00_base_400_castles.map';empty=MAPS/'ref_00_base_400.map'
    raw=source.read_bytes();emptyraw=empty.read_bytes();m=MapFile(raw);e=MapFile(emptyraw)
    orig=grids(m);flat=grids(e);g={sid:a.copy() for sid,a in orig.items()}
    records=objects(m,'buildings',ENTITY_LAYOUTS['buildings'])['records']
    require(len(records)==18,'Expected exactly two nine-part complexes')
    require([r['type'] for r in records[:9]]==[r['type'] for r in records[9:]],'Different templates')
    unitrecords=objects(m,'units',ENTITY_LAYOUTS['units'])['records'];require(len(unitrecords)==2,'Expected two lords')
    # These fields were already allocated by the supplied source's editing history.
    require(u32(m.section(1047)['decoded'])>=27,'Source building high-water template insufficient')
    for s in range(19,28):require(not any(getrec(m,4013,812,s)),'New building slot not empty')
    require(not any(getrec(m,3015,1168,3)),'Third unit slot not empty')
    audit={'building_fields':[], 'targets':TARGETS}
    # Move all local grid state using copied patches. Randomness stays at its
    # destination;3036 is unidentified global-pattern data and is not translated.
    transfer=[sid for sid in orig if sid not in (3008,3036)]
    def patch(anchor):
        return np.array([tile_index(anchor[0]+dx,anchor[1]+dy) for dy in range(-10,25) for dx in range(-10,25)])
    srcpatch=[patch(a) for a in ANCHORS]
    for ids in srcpatch:
        for sid in transfer:g[sid][ids]=flat[sid][ids]
    targetpatch=[patch(a) for a in TARGETS]
    require(len(set(np.concatenate(targetpatch).tolist()))==sum(map(len,targetpatch)),'Target complexes overlap')
    for p,ids in enumerate(targetpatch,1):
        require(np.all((flat[3003][ids]&0x30)==0),'Castle patch outside playable area')
        srcidx=0 if p==1 else 1
        for sid in transfer:g[sid][ids]=orig[sid][srcpatch[srcidx]]
        if p==3:
            for sid,offset in [(3012,9),(3010,1)]:
                values=g[sid][ids].copy();values[values!=0]+=offset;g[sid][ids]=values
            values=g[3043][ids].copy();values[values==1]=2;g[3043][ids]=values
    building=bytearray(m.section(4013)['decoded']);units=bytearray(m.section(3015)['decoded']);players=bytearray(m.section(2022)['decoded'])
    nextgid=u32(m.section(1035)['decoded']);require(nextgid==max([r['global_id'] for r in records+unitrecords])+1,'Global ID counter mismatch')
    idmap={records[9+i]['global_id']:nextgid+i for i in range(9)}
    idmap[unitrecords[1]['global_id']]=nextgid+9
    for part in range(9):
        a,b=getrec(m,4013,812,part+1),getrec(m,4013,812,part+10)
        fields,used=infer_positions(a,b)
        require(any(f['offset']==0xee for f in fields) and any(f['offset']==0xf4 for f in fields),'Primary building coords not detected')
        audit['building_fields'].append(dict(part=part,fields=fields))
        for p in (1,2,3):
            oldidx=0 if p==1 else 1;template=a if p==1 else b
            rec=relocate(template,fields,ANCHORS[oldidx],TARGETS[p-1]);slot=(p-1)*9+part+1
            if p==3:
                struct.pack_into('<H',rec,0xd6,3);struct.pack_into('<I',rec,8,3)
                for off in range(0,812-3,4):
                    if not any(i in used for i in range(off,off+4)) and u32(template,off) in idmap:
                        struct.pack_into('<I',rec,off,idmap[u32(template,off)])
                for off in range(0,811,2):
                    if any(i in used for i in range(off,off+2)):continue
                    va,vb=struct.unpack_from('<H',a,off)[0],struct.unpack_from('<H',b,off)[0]
                    if 1<=va<=9 and vb==va+9:struct.pack_into('<H',rec,off,vb+9)
            building[slot*812:(slot+1)*812]=rec
    a,b=getrec(m,3015,1168,1),getrec(m,3015,1168,2);fields,used=infer_positions(a,b);audit['unit_fields']=fields
    require({0xc4,0xd4,0xb6}.issubset({f['offset'] for f in fields}),'Missing unit coordinates')
    for p in (1,2,3):
        oldidx=0 if p==1 else 1;template=a if p==1 else b
        rec=relocate(template,fields,ANCHORS[oldidx],TARGETS[p-1])
        if p==3:
            for off in (0x10,0x80):struct.pack_into('<I',rec,off,3)
            rec[0x96]=3
            for off in range(0,1165,4):
                if not any(i in used for i in range(off,off+4)) and u32(template,off) in idmap:struct.pack_into('<I',rec,off,idmap[u32(template,off)])
            require(struct.unpack_from('<H',rec,0x338)[0]==10,'Unexpected linked keep')
            struct.pack_into('<H',rec,0x338,19)
        units[p*1168:(p+1)*1168]=rec
    stride=0x583c;a,b=getrec(m,2022,stride,1),getrec(m,2022,stride,2);fields,used=infer_positions(a,b);audit['player_fields']=fields
    for p in (1,2,3):
        oldidx=0 if p==1 else 1;template=a if p==1 else b
        rec=relocate(template,fields,ANCHORS[oldidx],TARGETS[p-1])
        if p==3:
            for off in (0x94,0xbc,0x1d4):struct.pack_into('<I',rec,off,u32(template,off)+9)
            struct.pack_into('<I',rec,0x21f8,3);struct.pack_into('<I',rec,0x21fc,nextgid+9)
        players[p*stride:(p+1)*stride]=rec
    lordslots=bytearray(m.section(1190)['decoded']);lordgids=bytearray(m.section(1191)['decoded'])
    require(struct.unpack_from('<H',lordslots,4)[0]==2 and u32(lordgids,8)==unitrecords[1]['global_id'],'Unexpected lord lookup format')
    struct.pack_into('<H',lordslots,6,3);struct.pack_into('<I',lordgids,12,nextgid+9)
    # Texture-only grid. Preserve the complete occupied footprint and castle
    # approach state, but remove decorative earth-stones on unoccupied land.
    inside=(g[3003]&0x30)==0;ground=inside&(g[3003]==0x8000)&(g[3012]==0)
    line=(XY[:,0]%5==0)|(XY[:,1]%5==0)
    g[3037][ground]=0;g[3037][ground&line]=16
    repl={sid:a.tobytes() for sid,a in g.items() if a.tobytes()!=m.section(sid)['decoded']}
    repl.update({4013:bytes(building),3015:bytes(units),2022:bytes(players),1190:bytes(lordslots),1191:bytes(lordgids),1035:struct.pack('<I',nextgid+10)})
    result=m.rebuild(repl);check=MapFile(result)
    require(all(s['error'] is None for s in check.sections),'Decode error')
    er={k:entity_report(check,v) for k,v in ENTITY_LAYOUTS.items()}
    require(er['buildings']['active_count']==27 and er['units']['active_count']==3,'Wrong entity count')
    for k in ('buildings','units'):
        require(not er[k]['referenced_inactive_or_missing_slots'],'Dangling references')
        require(er[k]['active_count']==er[k]['coordinate_matches'],'Bad entity coords')
    br=objects(check,'buildings',ENTITY_LAYOUTS['buildings'])['records']
    for p in (1,2,3):
        rs=[r for r in br if r['owner']==p];require(len(rs)==9,'Wrong building ownership')
        require(sum(r['referenced_cells'] for r in rs)==117,'Wrong footprint total')
        for r in rs:require(r['referenced_cells']==r['footprint_side']**2,'Footprint mismatch')
    links=player_links(check);require([p['player'] for p in links]==[1,2,3],'Wrong player list')
    for player in links:
        for link in player['links'].values():require(link['coordinate_match'],'Bad player coordinate')
    gids=[r['global_id'] for r in br]+[r['global_id'] for r in objects(check,'units',ENTITY_LAYOUTS['units'])['records']]
    require(len(set(gids))==30,'Duplicate global IDs')
    for s in m.sections:
        if s['id'] not in repl:require(s['raw']==check.section(s['id'])['raw'],'Unrelated section modified')
    require(source.read_bytes()==raw and empty.read_bytes()==emptyraw,'Source modified')
    OUT.mkdir(parents=True,exist_ok=True)
    # Review image uses schematic colors, not game texture assets.
    im=Image.new('RGB',(800,800),'#1f2229');pix=im.load()
    for i,(x,y) in enumerate(XY):
        if not inside[i]:continue
        c=(180,156,108)
        if g[3037][i]&16:c=(45,145,65)
        if g[3012][i]:c=[(230,70,70),(70,100,240),(240,190,60)][(int(g[3012][i])-1)//9]
        pix[int(x),int(y)]=c
    draw=ImageDraw.Draw(im)
    for p,(x,y) in enumerate(TARGETS,1):draw.text((x-8,y-18),f'P{p}',fill='white')
    im.save(OUT/'layout.png')
    audit.update(source_sha256=sha(raw),output_sha256=sha(result),output=str(dest),changed_sections=sorted(repl),players=links,
                 entities=er,global_id_next=nextgid+10,validation='Static checks passed; game load not yet tested',oasis_cells=int(np.count_nonzero(g[3037]&16)))
    (OUT/'manifest.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    for path,data in [(OUT/source.name,raw),(OUT/NAME,result),(dest,result)]:
        with path.open('xb') as f:f.write(data)
        require(path.read_bytes()==data,'Disk mismatch')
    print(json.dumps({k:audit[k] for k in ('output','changed_sections','validation','oasis_cells')},indent=2))

if __name__=='__main__':main()
