"""Exercise the actual portable EXE's new-size and valued-mask CLI paths."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from editor import MapReader, Pattern, PatternLibrary, EntityService
from editor.geometry import SUPPORTED_MAP_SIZES
from editor.navigation import calculate


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    exe=args.exe.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    mask=PatternLibrary(out).save(Pattern('Height proof',((1,1),(1,0)),
        heights=((0,64),(130,0))))
    recipe={'version':1,'operations':[
        {'op':'set_height','height':80,'rect':[370,370,6,6]},
        {'op':'paint','material':'oasis','rect':[370,370,6,6]},
        {'op':'paint','material':'river','rect':[385,385,3,15]},
        {'op':'stamp','pattern':mask.name,'x':390,'y':390},
        {'op':'place_building','building':'castle','x':400,'y':400,'owner':1},
        {'op':'place_building','building':'market','x':420,'y':420,'owner':1}]}
    path=out/'recipe.json';path.write_text(json.dumps(recipe),encoding='utf-8')
    results=[]
    for size in SUPPORTED_MAP_SIZES:
        report=out/('%s.json'%size);destination=out/('%s.map'%size)
        completed=subprocess.run([str(exe),'--cli','--report',str(report),'edit',
            '--size',str(size),'--recipe',str(path),'--output',str(destination)],
            timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        result=json.loads(report.read_text(encoding='utf-8'))
        if completed.returncode or not result['ok']:raise AssertionError(result)
        d=MapReader.open(destination);g=d.geometry
        assert d.size==size
        assert d.container.menu_metadata()['map_size']==size
        assert d.grid(3005)[g.index(370,370)]==80
        assert d.grid(3037)[g.index(370,370)]==16
        assert d.grid(3005)[g.index(385,385)]==0
        assert d.grid(3045)[g.index(385,385)]==8
        assert d.grid(3005)[g.index(390,390)]==0
        assert d.grid(3005)[g.index(391,390)]==64
        assert d.grid(3005)[g.index(390,391)]==130
        assert d.grid(3005)[g.index(391,391)]==8
        assert any(r['type']==41 for r in EntityService(d).records('buildings'))
        e,c,n=calculate(d)
        np.testing.assert_array_equal(e,d.grid(3030))
        np.testing.assert_array_equal(c,d.grid(3021))
        results.append(dict(size=size,ok=True,components=n))
        print('Portable size%s: passed'%size,flush=True)
    (out/'result.json').write_text(json.dumps(dict(ok=True,sizes=results),indent=2),encoding='utf-8')


if __name__=='__main__':main()
