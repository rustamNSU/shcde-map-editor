"""Execute pinned native height helpers in Unicorn against synthetic cells.

No native DLL loading, game process access, or source game/map writes.
The existing replay maps PE instructions into Unicorn, with synthetic zeroed
unit/building state. These helpers require no substituted decision routines.
"""
from pathlib import Path
import json
from research.verify_navigation_port import HeightReplay, BASE, TM, FLAGS, HEIGHT
from replay_fletcher_native import BM, UM, U, SHA256
from unicorn.x86_const import UC_X86_REG_RAX

OUT=Path(__file__).resolve().parents[1]/'output/wall-height-2026-10-23'
TILE=1000
BASE_HEIGHT=BASE+0x4e2b870
STRUCTURE=BASE+0x4b6aa50


def main():
    r=HeightReplay()
    cases=[('keep41',41,0x10000000,8,92),
           ('lookout_tower74',74,0x10000000,8,296),
           ('perimeter_tower75',75,0x10000000,8,148),
           ('defensive_turret76',76,0x10000000,8,180),
           ('square_tower77',77,0x10000000,8,192),
           ('round_tower78',78,0x10000000,8,192),
           ('small_gate46',46,0x100,98,128),
           ('high_wall',0,0x100,98,0),
           ('low_wall',0,0x10100,68,0),
           ('crenellated_wall',0,0x300,106,0),
           ('crenellated_high_component',0,0x400300,106,0),
           ('crenellated_low_wall',0,0x10300,76,0)]
    rows=[]
    for name,typ,flags,current,expected_offset in cases:
        r.uc.mem_write(U,b'\x00'*0x490)
        r.uc.mem_write(BM+0x32c,b'\x00'*0x32c)
        r.write(BASE+0x9302c4,1,4)
        r.write(U+0x414,0,2)
        r.write(FLAGS+TILE*4,flags,4)
        r.write(HEIGHT+TILE,current,1)
        r.write(BASE_HEIGHT+TILE,8,1)
        r.write(STRUCTURE+TILE*2,1 if typ else 0,2)
        r.write(BM+0x32c+0x12e,typ,2)
        r.write(BM+0x32c+0x148,8,2)
        r.write(U+0xd0,TILE,4)
        r.write(U+0xb6,current,2)
        r.write(U+0xb8,0,2)
        r.function(0xc07c0,BM,1)
        offset=r.uc.reg_read(UC_X86_REG_RAX)&0xffffffff
        assert offset==expected_offset,(name,offset,expected_offset)
        r.function(0x6b910,TM,TILE)
        effective=r.uc.reg_read(UC_X86_REG_RAX)&0xffffffff
        expected_effective=8+offset if typ in (45,46) else current+offset
        assert effective==expected_effective,(name,effective,expected_effective)
        r.function(0x184fd0,UM,1)
        unit_base=r.read(U+0xb6,2,True)
        unit_offset=r.read(U+0xb8,2,True)
        expected_unit_offset=(offset if flags&0x10000000 else 40 if typ and flags&0x100 else 0)
        assert unit_offset==expected_unit_offset,(name,unit_offset,expected_unit_offset)
        assert unit_base==(8 if flags&0x10000000 else current),(name,unit_base)
        r.function(0x6b530,TM,TILE,0)
        obstacle_raw=r.uc.reg_read(UC_X86_REG_RAX)&0xffffffff
        obstacle=obstacle_raw if obstacle_raw<0x80000000 else (~obstacle_raw)&0xffffffff
        rows.append(dict(name=name,building_type=typ,logic=hex(flags),base_grid=8,current_grid=current,
                         c07c0_offset=offset,surface_6b910=effective,unit_b6=unit_base,
                         unit_b8=unit_offset,unit_z_sum=unit_base+unit_offset,
                         barrier_6b530_magnitude=obstacle,barrier_6b530_signed_raw=hex(obstacle_raw)))
    result=dict(dll_sha256=SHA256,file_only=True,cases=rows,
                scope='Original C07C0, 6B910, 184FD0, 6B530 instructions; synthetic normal-state units; no height/decision helper stubbed',
                limitations='Not a live game test. Unit state flags are zero, unit type is0, no carried extra elevation. 6B530 sign encodes additional behavior; magnitude is reported separately.')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'native-height-replay.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
