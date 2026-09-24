"""Regression/evidence check for the user-supplied three-player editor resave."""
from pathlib import Path
import json
from maptool import MapFile,require
from research.analyze_references import objects,ENTITY_LAYOUTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/three-castle-resave'

def main():
    a=MapFile((ROOT/'output/three-castle-oasis-grid/etest_oasis_grid_3_castles_400.map').read_bytes())
    b=MapFile((OUT/'etest_oasis_grid_3_castles_400_r.map').read_bytes())
    before,after=a.menu_metadata(),b.menu_metadata()
    require(before['players_count']==2 and after['players_count']==3,'Player count evidence changed')
    require([(r['x'],r['y']) for r in after['start_markers'] if r['present']]==[(98,98),(156,18),(176,38)],'Unexpected markers')
    for sid in (3005,3045,3037,3008,1190,1191,1035):
        require(a.section(sid)['decoded']==b.section(sid)['decoded'],'Unexpected change to verified section')
    ba=objects(a,'buildings',ENTITY_LAYOUTS['buildings'])['records']
    bb=objects(b,'buildings',ENTITY_LAYOUTS['buildings'])['records']
    require(len(ba)==len(bb)==27,'Building count changed')
    for x,y in zip(ba,bb):
        for key in ('slot','type','owner','global_id','x','y','footprint_side','referenced_cells'):
            require(x[key]==y[key],'Core building state changed')
    # Check the empirical400-map projection on independent original examples.
    validated=[]
    paths=list((ROOT/'examples').glob('*.map'))+[
        ROOT/'output/references-2026-09-19/maps/ref_10_p1_or_red_castle_400.map',
        ROOT/'output/references-2026-09-19/maps/ref_10_p8_or_green_castle_400.map',
        ROOT/'output/height-castles-2026-09-19/ref_00_base_400_castles.map',
        OUT/'etest_oasis_grid_3_castles_400_r.map']
    for path in paths:
        m=MapFile(path.read_bytes());meta=m.menu_metadata()
        if m.version<200 or meta.get('map_size')!=400:continue
        keeps=[r for r in objects(m,'buildings',ENTITY_LAYOUTS['buildings'])['records'] if r['type']==41]
        require(meta['players_count']==len(keeps),'Menu count differs from keep count in control')
        for r in keeps:
            predicted=((r['x']-r['y']+197)//2,(r['x']+r['y']-598)//2)
            marker=meta['start_markers'][r['owner']-1]
            require(predicted==(marker['x'],marker['y']),'400-map marker formula mismatch')
        validated.append(dict(file=path.name,keeps=len(keeps)))
    result=dict(before=before,after=after,unchanged_core_buildings=27,
                unchanged_sections=[3005,3045,3037,3008,1190,1191,1035],
                preview_palette_changed_bytes=sum(x!=y for x,y in zip(a.preview[:512],b.preview[:512])),
                preview_changed_pixels=sum(x!=y for x,y in zip(a.preview[512:],b.preview[512:])),
                marker_formula_400_checks=validated,
                caution='Formula validated only on400-size DE maps with KeepTwo;500 differs.')
    (OUT/'menu_findings.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('PASS: menu metadata,27 buildings,7 unchanged sections,',sum(r['keeps'] for r in validated),'independent marker checks')

if __name__=='__main__':main()
