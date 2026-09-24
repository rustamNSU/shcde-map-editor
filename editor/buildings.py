"""Reference-derived prefabs. All edits are atomic and available without Qt.

This is an experimental DE writer, not an implementation of the game's build
command. Unknown simulation state is preserved; populated buildings are refused.
"""
import json
import struct
from functools import lru_cache
from pathlib import Path
import numpy as np
from semantics import ENTITY_LAYOUTS, tile_index, tile_xy
from .services import EntityService

LAYOUTS={k:(v[0],v[1],v[2],v[4]) for k,v in ENTITY_LAYOUTS.items()}
LAYOUTS['gates']=(1031,516,0,8)
H=lambda b,o:struct.unpack_from('<H',b,o)[0]
I=lambda b,o:struct.unpack_from('<I',b,o)[0]

@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).parent/'assets/templates/buildings.json').read_text(encoding='utf-8'))['items']

def relocate(raw,fields,dx,dy):
    b=bytearray(raw)
    for f in fields:
        off=f['offset']
        if f['kind']=='tile':
            x,y=tile_xy(I(raw,off))
            struct.pack_into('<I',b,off,tile_index(x+dx,y+dy))
        else:
            x,y=struct.unpack_from(f['kind'],raw,off); scale=f['scale']
            struct.pack_into(f['kind'],b,off,x+dx*scale,y+dy*scale)
    return b


class BuildingService:
    def __init__(self,document):
        self.document=document

    def footprint(self,key,x,y):
        p=catalog()[key]
        if type(x) is not int or type(y) is not int:
            raise ValueError('Building coordinates must be integers')
        return np.array([tile_index(x+dx,y+dy) for dx,dy in p['cells']],dtype=np.int64)

    def check_placement(self,key,x,y,owner=1):
        d=self.document
        if key not in catalog(): raise ValueError('Unknown building: '+str(key))
        if type(owner) is not int or not 1<=owner<=8: raise ValueError('Player must be 1..8')
        if d.size not in (400,500): raise ValueError('Building tools require a 400 or 500 map')
        ids=self.footprint(key,x,y)
        if not np.all(d.geometry.playable[ids]): raise ValueError('The complete building must fit inside the map')
        if any(np.any(d.grid(sid)[ids]) for sid in (3012,3010,3004)):
            raise ValueError('The footprint overlaps a building, unit or vegetation')
        occupied=set(ids.tolist())
        if any(r['tile_id'] in occupied for r in EntityService(d).records('units')):
            raise ValueError('A unit occupies the footprint')
        if not np.all(np.isin(d.grid(3003)[ids],[0x8000,0x28000,0x88000])):
            raise ValueError('Placement currently needs clear, flat land')
        base=int(d.grid(3045)[ids[0]])
        if not np.all((d.grid(3005)[ids]==base)&(d.grid(3045)[ids]==base)) or (key!='castle' and base!=8):
            raise ValueError('Castle needs one flat plateau; other reference buildings require ground height 8')
        if key=='castle' and any(not 0<=v+base-8<=255 for v in catalog()[key]['grids']['3005']):
            raise ValueError('Castle elevation exceeds the height range')
        if key=='castle' and any(40<=r['type']<=44 and r['owner']==owner for r in EntityService(d).records('buildings')):
            raise ValueError('This player already has a castle')
        return ids

    def _allocate(self,kind,count):
        sid,stride,_,_=LAYOUTS[kind]
        if not count: return []
        if self.document.section(sid)['decoded'] is None:
            raise ValueError('Cannot edit %s: section %s could not be decoded and is preserved unchanged' % (kind,sid))
        b=self.document.grid(sid).reshape(-1,stride)
        # Never recycle a dead simulation record with unknown outstanding links.
        slots=np.flatnonzero(~np.any(b,axis=1)); slots=slots[slots!=0]
        if len(slots)<count: raise ValueError('No clean free '+kind+' slots remain')
        return [int(v) for v in slots[:count]]

    def place(self,key,x,y,owner=1):
        d=self.document; ids=self.check_placement(key,x,y,owner); p=catalog()[key]
        label='Place '+p['name']; dx=x-p['anchor'][0]; dy=y-p['anchor'][1]
        elevation=int(d.grid(3045)[ids[0]])-8 if key=='castle' else 0
        remap={kind:{} for kind in LAYOUTS}; blobs={}; gidmap={}
        nextgid=I(d.section(1035)['decoded'],0)
        livegids=[r['global_id'] for k in ENTITY_LAYOUTS for r in EntityService(d).records(k)]
        nextgid=max([nextgid]+[v+1 for v in livegids])
        for kind in LAYOUTS:
            source=[r for r in p['records'] if r['kind']==kind]
            for r,slot in zip(source,self._allocate(kind,len(source))):
                remap[kind][r['slot']]=slot
                raw=bytes.fromhex(r['data']); gidmap[I(raw,LAYOUTS[kind][3])]=nextgid; nextgid+=1
        # Allocate fresh IDs for isolated path regions; retain ordinary ground region 1.
        regions={v for v in p['grids']['3021'] if v>1}
        firstregion=int(d.grid(3021).max())+1
        if firstregion+len(regions)>65535: raise ValueError('Path region capacity exceeded')
        regionmap={v:firstregion+i for i,v in enumerate(sorted(regions))}
        made=[]
        for r in p['records']:
            kind=r['kind']; sid,stride,_,go=LAYOUTS[kind]
            raw=bytes.fromhex(r['data']); rec=relocate(raw,r['fields'],dx,dy)
            if elevation and kind in ('buildings','units'):
                off=0xec if kind=='buildings' else 0xba
                struct.pack_into('<H',rec,off,H(raw,off)+elevation)
            struct.pack_into('<I',rec,go,gidmap[I(raw,go)])
            if kind=='buildings':
                struct.pack_into('<H',rec,0xd6,owner); struct.pack_into('<I',rec,8,owner)
                if key=='castle':
                    # Native group-root ID: keep/door/camp point to the keep;
                    # all four stockpile pieces point to the first pile.
                    struct.pack_into('<I',rec,0x2a8,gidmap[I(raw,0x2a8)])
                link=H(raw,0x192)
                if link:
                    if link not in remap['buildings']: raise ValueError('Template has an external building link')
                    struct.pack_into('<H',rec,0x192,remap['buildings'][link])
                gate=H(raw,0x2d2)
                if gate: struct.pack_into('<H',rec,0x2d2,remap['gates'][gate])
            elif kind=='units':
                for off in (0x10,0x80): struct.pack_into('<I',rec,off,owner)
                rec[0x96]=owner
                struct.pack_into('<H',rec,0x338,remap['buildings'][H(raw,0x338)])
            elif kind=='gates':
                struct.pack_into('<I',rec,12,remap['buildings'][I(raw,12)])
                struct.pack_into('<I',rec,0x14,gidmap[I(raw,0x14)])
                struct.pack_into('<I',rec,0x18,owner)
                for off in (0x34,0x38,0x1e8):
                    struct.pack_into('<I',rec,off,regionmap.get(I(raw,off),I(raw,off)))
            slot=remap[kind][r['slot']]
            if sid not in blobs: blobs[sid]=bytearray(d.section(sid)['decoded'])
            blobs[sid][slot*stride:(slot+1)*stride]=rec
            made.append((kind,slot,rec))
        with d.transaction(label):
            for sid,values in p['grids'].items():
                sid=int(sid); values=np.array(values,dtype=d.grid(sid).dtype)
                if elevation and sid in (3005,3045): values=(values.astype(np.int16)+elevation).astype(values.dtype)
                if sid in (3012,3010,3004):
                    kind={3012:'buildings',3010:'units',3004:'vegetation'}[sid]
                    values=np.array([remap[kind].get(int(v),0) for v in values],dtype=values.dtype)
                elif sid==3043: values[:]=owner-1
                elif sid==3021: values=np.array([regionmap.get(int(v),int(v)) for v in values],dtype=values.dtype)
                d.change(sid,ids,values,label)
            for sid,data in blobs.items(): d.replace_section(sid,data,label)
            d.replace_section(1035,struct.pack('<I',nextgid),label)
            self._player_links(owner,made,False,label)
        return {'building':key,'owner':owner,'x':x,'y':y,'cells':len(ids),
                'records':{k:list(v.values()) for k,v in remap.items()},'experimental':True}

    def _player_links(self,owner,records,remove,label):
        d=self.document
        required=[2022]+([1190,1191] if any(k=='units' for k,s,r in records) else [])
        if 1190 in required and d.section(1190)['decoded'] is None:
            # Reconstruct the nine-slot lord lookup from independent player/unit
            # records. Removed units are available in this transaction's records.
            players=d.section(2022)['decoded']; gids=d.section(1191)['decoded']
            if players is None or gids is None:
                raise ValueError('Cannot rebuild lord lookup: player data is unreadable')
            deleted={s:r for k,s,r in records if k=='units'}
            units=d.section(3015)['decoded']; slots=[]
            for player in range(9):
                slot=I(players,player*0x583c+0x21f8)
                gid=I(players,player*0x583c+0x21fc)
                if gid!=I(gids,player*4): raise ValueError('Conflicting player/lord IDs; cannot rebuild lookup')
                if slot:
                    rec=deleted.get(slot,units[slot*1168:(slot+1)*1168])
                    if (len(rec)!=1168 or (H(rec,0x8c) in (0,3) and slot not in deleted)
                            or H(rec,0x8e)!=55 or I(rec,0x80)!=player or I(rec,0x98)!=gid):
                        raise ValueError('Conflicting lord records; cannot rebuild lookup')
                elif gid: raise ValueError('Missing lord slot; cannot rebuild lookup')
                slots.append(slot)
            if len(set(s for s in slots if s))!=len([s for s in slots if s]):
                raise ValueError('Duplicate lord slots; cannot rebuild lookup')
            d.recover_section(1190,struct.pack('<9H',*slots))
        for sid in required:
            if d.section(sid)['decoded'] is None:
                raise ValueError('Cannot update player links: section %s could not be decoded and is preserved unchanged' % sid)
        b=bytearray(d.section(2022)['decoded']); at=owner*0x583c
        castle=any(k=='buildings' and H(r,0xd2)==41 for k,s,r in records)
        # Links contain ACCESS coordinates (not footprint origins).
        for kind,slot,rec in records:
            if kind=='buildings':
                t=H(rec,0xd2); off={41:0x94,10:0xbc,19:0xe4,11:0x10c,55:0x1d4}.get(t)
                if off is not None:
                    old=I(b,at+off)
                    if remove and old==slot:
                        b[at+off:at+off+16]=bytes(16)
                        if castle and t in (41,10,55): struct.pack_into('<I',b,at+off+16,0)
                    elif not remove and (not old or t in (41,55)):
                        xx,yy=struct.unpack_from('<HH',rec,0xfe)
                        if t==55: xx,yy=H(rec,0xee)+3,H(rec,0xf0)
                        struct.pack_into('<4I',b,at+off,slot,xx,yy,tile_index(xx,yy))
                        if castle and t in (41,10,55): struct.pack_into('<I',b,at+off+16,1)
                space=H(rec,0x196)
                if space: struct.pack_into('<I',b,at+0x74,max(0,I(b,at+0x74)+(-space if remove else space)))
            elif kind=='units':
                gid=I(rec,0x98)
                struct.pack_into('<II',b,at+0x21f8,0 if remove else slot,0 if remove else gid)
                for sid,fmt,value in ((1190,'<H',slot),(1191,'<I',gid)):
                    table=bytearray(d.section(sid)['decoded'])
                    struct.pack_into(fmt,table,owner*struct.calcsize(fmt),0 if remove else value)
                    d.replace_section(sid,table,label)
        if castle:
            # These values are corroborated by native P1/P8 castles and the
            # user-validated three-castle map. Do not reset resources or copy an
            # entire player record over existing state. 0x489c's name is unknown.
            count=sum(k=='units' and H(r,0x8e)==55 and H(r,0x8c) not in (0,3)
                      for k,s,r in records)
            struct.pack_into('<I',b,at+0x84,max(0,I(b,at+0x84)+(-count if remove else count)))
            struct.pack_into('<I',b,at+0x489c,0 if remove else 1)
        d.replace_section(2022,b,label)
        if remove:
            # Keep first-storage links valid when another storage building survives.
            b=bytearray(d.section(2022)['decoded'])
            for t,off in ((10,0xbc),(19,0xe4),(11,0x10c)):
                if I(b,at+off): continue
                row=next((r for r in EntityService(d).records('buildings') if r['owner']==owner and r['type']==t),None)
                if row:
                    raw=d.section(4013)['decoded']; rr=raw[row['slot']*812:(row['slot']+1)*812]
                    xx,yy=H(rr,0xfe),H(rr,0x100)
                    struct.pack_into('<4I',b,at+off,row['slot'],xx,yy,tile_index(xx,yy))
                    if castle and t==10: struct.pack_into('<I',b,at+off+16,1)
            d.replace_section(2022,b,label)

    def group_at(self,x,y):
        """Resolve a clicked child to its complete supported prefab."""
        d=self.document; index=tile_index(x,y); slot=int(d.grid(3012)[index])
        rows=EntityService(d).records('buildings'); byslot={r['slot']:r for r in rows}
        row=byslot.get(slot)
        if not row:
            # Orchard gaps and fields still belong to the farmhouse.
            row=next((r for r in rows if r['type'] in (30,31,32,33) and r['x']<=x<r['x']+(10 if r['type'] in (32,33) else 9)
                      and r['y']<=y<r['y']+(10 if r['type'] in (32,33) else 9)),None)
        if not row: return None
        if row['type'] in (71,72,73,55):
            raw=d.section(4013)['decoded']; parent=H(raw,row['slot']*812+0x192); row=byslot.get(parent,row)
        if row['type']==21:
            raw=d.section(4013)['decoded']
            row=next((r for r in rows if r['type']==20 and H(raw,r['slot']*812+0x192)==row['slot']),row)
        if row['type']==10:
            row=next((r for r in rows if r['type']==41 and r['owner']==row['owner'] and
                      (row['x']-r['x'],row['y']-r['y']) in ((7,2),(10,2),(7,5),(10,5))),row)
        if row['type']==49:
            row=next((r for r in rows if r['owner']==row['owner'] and
                      ((r['type']==46 and (row['x'],row['y'])==(r['x'],r['y']+5)) or
                       (r['type']==45 and (row['x'],row['y'])==(r['x']+7,r['y']+1)))),row)
        options=[(key,p) for key,p in catalog().items() if p['type']==row['type']]
        options.sort(key=lambda item:len(item[1]['records']),reverse=True)
        for key,p in options:
            dx=row['x']-p['anchor'][0]; dy=row['y']-p['anchor'][1]; matched=[]
            for rr in p['records']:
                if rr['kind']!='buildings': continue
                raw=bytes.fromhex(rr['data']); xx,yy=H(raw,0xee)+dx,H(raw,0xf0)+dy
                candidate=next((r for r in rows if r['x']==xx and r['y']==yy and r['type']==H(raw,0xd2) and r['owner']==row['owner']),None)
                if not candidate: break
                matched.append(candidate)
            else: return key,row,matched
        raise ValueError('This building layout has no complete reference template yet')

    def remove(self,x,y):
        d=self.document; group=self.group_at(x,y); label='Remove building'
        if not group:
            i=tile_index(x,y)
            if not (int(d.grid(3003)[i])&0x100): return {'removed':0}
            if not d.geometry.playable[i] or d.grid(3045)[i]!=8:
                raise ValueError('Only flat-ground walls can be removed currently')
            ids=np.array([i]); records=[]; owner=1
        else:
            key,root,rows=group; owner=root['owner']; p=catalog()[key]
            ids=self.footprint(key,root['x'],root['y']); records=[]
            slots={r['slot'] for r in rows}
            if set(map(int,d.grid(3012)[ids]))-{0,*slots}: raise ValueError('Another building overlaps this group')
            raw=d.section(4013)['decoded']
            for row in rows:
                slot=row['slot']; rec=raw[slot*812:(slot+1)*812]
                if H(rec,0x19a) or any(rec[0x19e:0x1a8]):
                    raise ValueError('This building has assigned workers; removal of active simulation links is not supported yet')
                if any(rec[0x120:0x188]):
                    raise ValueError('This building contains goods; live resource-accounting removal is not supported yet')
                records.append(('buildings',slot,rec))
                gate=H(rec,0x2d2)
                if gate:
                    gr=d.section(1031)['decoded'][gate*516:(gate+1)*516]
                    if I(gr,12)!=slot: raise ValueError('Inconsistent gate manager link')
                    records.append(('gates',gate,gr))
            if key=='apple_orchard':
                for slot in set(map(int,d.grid(3004)[ids]))-{0}:
                    rec=d.section(1014)['decoded'][slot*156:(slot+1)*156]
                    if H(rec,0x46)!=15: raise ValueError('Unrelated vegetation inside orchard')
                    records.append(('vegetation',slot,rec))
            if key=='castle':
                # Include a dead lord as well. Active-only entity enumeration
                # used to leave its record behind when replacing a castle.
                units=d.section(3015)['decoded']
                for slot in range(1,len(units)//1168):
                    rec=units[slot*1168:(slot+1)*1168]
                    if H(rec,0x8e)==55 and I(rec,0x80)==owner and H(rec,0x338)==root['slot']:
                        records.append(('units',slot,rec))
                players=d.section(2022)['decoded']; at=owner*0x583c
                lordslot=I(players,at+0x21f8)
                if lordslot and lordslot not in {s for k,s,r in records if k=='units'}:
                    raise ValueError('The player lord does not link to this castle; removal would leave inconsistent player data')
            unit_slots={s for k,s,r in records if k=='units'}
            if any(r['tile_id'] in set(ids.tolist()) and r['slot'] not in unit_slots for r in EntityService(d).records('units')):
                raise ValueError('Move units out of the footprint before removing this building')
        with d.transaction(label):
            # Preserve mineral deposits and ground textures; clear the complete structural footprint.
            resource=d.grid(3003)[ids]&0xa0000
            ground_height=d.grid(3045)[ids].copy()
            for sid,value in ((3003,resource|0x8000),(3005,ground_height),(3006,0),
                              (3007,np.where(resource,2064,16)),(3009,0),(3012,0),(3043,0),
                              (3049,0),(3030,255),(3021,1),(3020,0),(3026,0),(3118,0),
                              (3028,0),(3029,0),(3101,0),(3103,0),(3104,0)):
                d.change(sid,ids,value,label)
            for kind,slot,rec in records:
                sid,stride,_,_=LAYOUTS[kind]
                start=slot*stride
                d.change(sid,np.arange(start,start+stride),0,label)
                if kind in ('vegetation','units'):
                    grid=3004 if kind=='vegetation' else 3010
                    d.change(grid,np.flatnonzero(d.grid(grid)==slot),0,label)
            self._player_links(owner,records,True,label)
        return {'removed':len(records) or len(ids),'experimental':True}
