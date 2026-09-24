"""Paint a five-cell-pitch oasis grid on a supplied castle layout, preserving entities."""
import argparse
import json
from pathlib import Path
import numpy as np
from maptool import MapFile, require, u32
from research.analyze_references import grids, XY, objects, ENTITY_LAYOUTS, sha

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('destination',type=Path)
    p.add_argument('archive',type=Path)
    args=p.parse_args()
    require(not args.destination.exists(),'Destination exists')
    raw=args.source.read_bytes();m=MapFile(raw);g=grids(m)
    require(u32(m.section(1050)['decoded'])==400,'Expected map size400')
    buildings=objects(m,'buildings',ENTITY_LAYOUTS['buildings'])['records']
    keeps=[r for r in buildings if r['type'] in range(40,45) and r['state']==2]
    require(sorted(r['owner'] for r in keeps)==[1,2,3],'Need supplied P1/P2/P3 castle layout')
    inside=(g[3003]&0x30)==0
    # Preserve footprint cells: no terrain repaint under existing structures.
    ground=inside & (g[3003]==0x8000) & (g[3012]==0) & (g[3004]==0)
    require(np.all(g[3037][ground]==0),'Source has other painted surfaces')
    line=((XY[:,0]%5)==0)|((XY[:,1]%5)==0)
    target=ground&line
    surface=g[3037].copy();surface[target]=16
    result=m.rebuild({3037:surface.tobytes()});check=MapFile(result)
    require(all(s['error'] is None for s in check.sections),'Invalid output')
    for s in m.sections:
        if s['id']!=3037:require(check.section(s['id'])['raw']==s['raw'],'Unrelated data modified')
    require(check.section(3037)['decoded']==surface.tobytes(),'Incorrect grid')
    require(result[:m.directory_offset]==raw[:m.directory_offset] and check.trailing==m.trailing,'Metadata modified')
    args.archive.mkdir(parents=True,exist_ok=True)
    require(not (args.archive/args.destination.name).exists(),'Archive output exists')
    for dest,data in [(args.archive/args.source.name,raw),(args.archive/args.destination.name,result),(args.destination,result)]:
        with dest.open('xb') as f:f.write(data)
        require(dest.read_bytes()==data,'Disk mismatch')
    require(args.source.read_bytes()==raw,'Source modified')
    report=dict(source=str(args.source),destination=str(args.destination),source_sha256=sha(raw),
                output_sha256=sha(result),pitch=5,earth_interior=[4,4],line_width=1,
                oasis_cells=int(target.sum()),changed_section=3037,keeps=keeps,
                note='Castle footprints excluded; partial cells at map boundary. Game validation pending.')
    (args.archive/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='keeps'},indent=2))

if __name__=='__main__':main()
