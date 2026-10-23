"""Reproducible, read-only extraction of static reference prefabs for the editor."""
import json, struct, hashlib
from pathlib import Path
import numpy as np
from maptool import MapFile
from semantics import ENTITY_LAYOUTS, entity_report, tile_index, tile_xy
from editor.document import GRID_TYPES

ROOT=Path(__file__).resolve().parents[1]
MAPS=Path('C:/Users/rustam/AppData/LocalLow/Firefly Studios/Stronghold Crusader Definitive Edition/Maps')

def main():
    source=ROOT/'output/buildings-2026-09-20/ref_11_buidlings_400.map'
    source_bytes=source.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest()=='52514e52710005786836b1d1e323f5ff1a3013f05cfe1d6040b6a95d00b58d24'
    m=MapFile(source_bytes)
    g={sid:np.frombuffer(m.section(sid)['decoded'],dtype=dt) for sid,dt in GRID_TYPES.items()}
    buildings={r['slot']:r for r in entity_report(m,ENTITY_LAYOUTS['buildings'])['records']}
    catalog={}
    choices=[('hovel','Hovel',35,'Town'),('woodcutter','Woodcutter',28,'Resources'),
      ('quarry','Stone quarry + pile',29,'Resources'),('iron_mine','Iron mine',31,'Resources'),
      ('ox_tether','Ox tether',32,'Resources'),('hunter','Hunter’s post',19,'Food'),
      ('dairy_farm','Dairy farm',20,'Farms'),('apple_orchard','Apple orchard',21,'Farms'),
      ('wheat_farm','Wheat farm',22,'Farms'),('hops_farm','Hops farm',23,'Farms'),
      ('inn','Inn',68,'Town'),('granary','Granary',64,'Storage'),('armoury','Armoury',13,'Storage'),
      ('fletcher','Fletcher',59,'Workshops'),('poleturner','Poleturner',60,'Workshops'),
      ('blacksmith','Blacksmith',61,'Workshops'),('tanner','Tanner',62,'Workshops'),
      ('armourer','Armourer',63,'Workshops'),('bakery','Bakery',65,'Workshops'),
      ('mill','Mill',66,'Workshops'),('brewery','Brewery',67,'Workshops'),
      ('lookout_tower','Lookout tower',14,'Fortifications'),('perimeter_tower','Perimeter tower',15,'Fortifications'),
      ('defense_tower','Defense tower',16,'Fortifications'),('square_tower','Square tower',17,'Fortifications'),
      ('round_tower','Round tower',18,'Fortifications'),
      ('small_gate','Small gate',76,'Fortifications'),('large_gate','Large gate',80,'Fortifications'),
      ('small_gate_bridge','Small gate + drawbridge',77,'Fortifications'),
      ('large_gate_bridge','Large gate + drawbridge',80,'Fortifications'),
      ('stockpile','Stockpile (four sections)',24,'Storage'),
      ('pitch_rig','Pitch rig',33,'Resources'),('market','Market',34,'Town'),
      ('small_church','Small church',36,'Religion'),('church','Church',37,'Religion'),
      ('cathedral','Cathedral',38,'Religion'),('apothecary','Apothecary',39,'Town'),
      ('well','Well',40,'Town'),('water_pot','Water pot',41,'Town'),
      ('stone_barracks','Stone barracks + parade grounds',1,'Military'),
      ('mercenary_post','Mercenary post + parade grounds',5,'Military'),
      ('bedouin_stockade','Bedouin stockade + parade grounds',9,'Military'),
      ('engineers_guild','Engineers guild + parade ground',69,'Military'),
      ('stables','Stables',71,'Military'),
      ('tunnellers_guild','Tunnellers guild + parade ground',72,'Military'),
      ('oil_smelter','Oil smelter + parade ground',74,'Military'),
      ('dog_cage','War dog cage',79,'Fortifications'),('killing_pit','Killing pit',83,'Fortifications'),
      ('gallows','Gallows',42,'Bad things'),('cesspit','Cesspit',43,'Bad things'),
      ('stocks','Stocks',44,'Bad things'),('burning_stake','Burning stake',45,'Bad things'),
      ('dungeon','Dungeon',46,'Bad things'),('stretching_rack','Stretching rack',47,'Bad things'),
      ('gibbet','Gibbet',48,'Bad things'),('chopping_block','Chopping block',49,'Bad things'),
      ('dunking_stool','Dunking stool',50,'Bad things'),
      ('maypole','Maypole',51,'Good things'),('garden_3_a','Garden (3 × 3, A)',52,'Good things'),
      ('dancing_bear','Dancing bear',53,'Good things'),('garden_2','Garden (2 × 2)',54,'Good things'),
      ('garden_4','Garden (4 × 4)',55,'Good things'),('garden_3_b','Garden (3 × 3, B)',56,'Good things'),
      ('statue','Statue',57,'Good things'),('shrine','Shrine',58,'Good things')]
    groups={'quarry':[29,30], 'small_gate_bridge':[77,78], 'large_gate_bridge':[80,81],
            'stockpile':list(range(24,28)), 'stone_barracks':list(range(1,5)),
            'mercenary_post':list(range(5,9)), 'bedouin_stockade':list(range(9,13)),
            'engineers_guild':[69,70], 'tunnellers_guild':[72,73], 'oil_smelter':[74,75]}
    def fields(raw,kind):
        if kind=='buildings':
            pairs=[(0xe8,8),(0xee,1),(0xfe,1),(0x260,1)]
            tiles=[0x8c,0xc8,0xf4]+list(range(0x1c8,0x258,4))
        elif kind=='vegetation':
            pairs=[(0x5c,8),(0x62,1)]; tiles=[0x68]
        else:
            return json.loads((ROOT/'output/three-castle-oasis-grid/manifest.json').read_text())['unit_fields']
        result=[]
        for off,scale in pairs:
            x,y=struct.unpack_from('<HH',raw,off)
            if x and y and 0<x/scale<800 and 0<y/scale<800:
                result.append(dict(offset=off,kind='<HH',scale=scale))
        for off in tiles:
            v=struct.unpack_from('<I',raw,off)[0]
            if v and v<320800: result.append(dict(offset=off,kind='tile',scale=1))
        return result
    def prefab(key,label,slot,category,slots=None):
        row=buildings[slot]; slots=slots or [slot]
        x,y=row['x'],row['y']; ids=set(np.flatnonzero(np.isin(g[3012],slots)).tolist())
        if key in ('dairy_farm','apple_orchard','wheat_farm','hops_farm'):
            side=10 if key in ('dairy_farm','apple_orchard') else 9
            ids.update(tile_index(x+dx,y+dy) for dy in range(side) for dx in range(side))
        trees=sorted(set(int(v) for v in g[3004][list(ids)] if v))
        units=[]
        if key=='castle':
            # Only native structure references belong to this prefab. Empty
            # cells inside the enclosing rectangle remain usable by other tools.
            units=[r['slot'] for r in entity_report(m,ENTITY_LAYOUTS['units'])['records']
                   if r['type']==55 and abs(r['x']-x)<15 and abs(r['y']-y)<18]
            assert len(units)==1
            for u in units:
                rec=m.section(3015)['decoded'][u*1168:(u+1)*1168]
                assert struct.unpack_from('<H',rec,0x338)[0]==slot
                ids.add(struct.unpack_from('<I',rec,0xd4)[0])
        assert not(set(g[3012][list(ids)])-{0,*slots}),key
        assert not(set(g[3010][list(ids)])-{0,*units}),key
        ids=sorted(ids); cells=[[tile_xy(i)[0]-x,tile_xy(i)[1]-y] for i in ids]
        records=[]
        for kind,ss in [('buildings',slots),('vegetation',trees),('units',units)]:
            sid,stride,*_=ENTITY_LAYOUTS[kind]
            for s in ss:
                raw=m.section(sid)['decoded'][s*stride:(s+1)*stride]
                records.append(dict(kind=kind,slot=s,data=raw.hex(),fields=fields(raw,kind)))
                if kind=='buildings' and struct.unpack_from('<H',raw,0xd2)[0] in (45,46):
                    gate=struct.unpack_from('<H',raw,0x2d2)[0]
                    gr=m.section(1031)['decoded'][gate*516:(gate+1)*516]
                    assert struct.unpack_from('<I',gr,12)[0]==s
                    records.append(dict(kind='gates',slot=gate,data=gr.hex(),fields=[
                        dict(offset=o,kind='<II',scale=1) for o in (0x1c,0x28)]+[
                        dict(offset=o,kind='tile',scale=1) for o in (0x24,0x30)]))
        catalog[key]=dict(name=label,category=category,anchor=[x,y],type=row['type'],cells=cells,
             width=max(c[0] for c in cells)+1,height=max(c[1] for c in cells)+1,
             records=records,grids={str(sid):a[ids].tolist() for sid,a in g.items() if sid not in (3008,)})
    for key,label,slot,category in choices:
        prefab(key,label,slot,category,groups.get(key,[slot]))
    # Castle records must come from the isolated native reference, not a lord
    # that has been running alongside dozens of other entities in ref_11.
    castle_source=ROOT/'output/castle-audit-2026-09-20/ref_12_castle.map'
    castle_bytes=castle_source.read_bytes()
    assert hashlib.sha256(castle_bytes).hexdigest()=='d49bc802954bb0898064d24214b85491b0ad13028b9d1dd41c2a4baa7881cc6b'
    m=MapFile(castle_bytes)
    g={sid:np.frombuffer(m.section(sid)['decoded'],dtype=dt) for sid,dt in GRID_TYPES.items()}
    buildings={r['slot']:r for r in entity_report(m,ENTITY_LAYOUTS['buildings'])['records']}
    prefab('castle','Castle + campfire + stockpile',1,'Fortifications',list(range(1,10)))
    catalog['castle']['source']=castle_source.name
    catalog['castle']['source_sha256']=hashlib.sha256(castle_bytes).hexdigest()
    # Exact flat-ground wall/stair templates. Rotation is not inferred from sprite numbers.
    w=MapFile((MAPS/'ref_12_ladders_and_hills_400.map').read_bytes())
    for key,label,x,y,n in [('wall','High wall',392,521,1),('wall_stairs','High wall + stairs',392,521,6),('low_wall','Low wall',395,542,1)]:
        ids=[tile_index(x+dx,y) for dx in range(n)]
        catalog[key]=dict(name=label,category='Fortifications',type=0,anchor=[x,y],width=n,height=1,
          cells=[[dx,0] for dx in range(n)],records=[],grids={str(sid):np.frombuffer(w.section(sid)['decoded'],dtype=dt)[ids].tolist() for sid,dt in GRID_TYPES.items() if sid!=3008})
    result=dict(version=1,source=source.name,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),items=catalog)
    out=ROOT/'editor/assets/templates/buildings.json'
    out.write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print('Extracted',len(catalog),'prefabs to',out)
if __name__=='__main__': main()
