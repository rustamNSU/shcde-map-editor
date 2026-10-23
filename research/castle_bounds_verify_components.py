"""Offline Unicorn checks of original E49D0 and DE6A0 instructions.

No game process or native game DLL loading. The original generic byte-fill
helper is implemented as an equivalent Unicorn-memory write to keep this
full-grid replay short; no component/edge decision is stubbed.
"""
from pathlib import Path
import sys
import json
import struct
from types import SimpleNamespace
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.append('C:/Program Files/Python39/Lib/site-packages')
sys.path.append(str(Path.home()/'AppData/Roaming/Python/Python39/site-packages'))
sys.path.insert(0,str(ROOT.parent/'shc-dashboard/artifacts/production-static'))
from verify_tile_height import HeightReplay,BASE,TM,FLAGS,EDGES
from replay_fletcher_native import STACK,RETURN
from unicorn.x86_const import (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,
                               UC_X86_REG_R9,UC_X86_REG_RSP,UC_X86_REG_RIP)
import editor.navigation as nav
from editor.geometry import MapGeometry
from semantics import ROW_COUNTS,ROW_STARTS

CONTEXT=BASE+0x60ad660
COMPONENTS=BASE+0x50ec690


class NavigationReplay(HeightReplay):
    def hook(self,uc,address,size,user_data):
        if address==BASE+0x7490:
            length=uc.reg_read(UC_X86_REG_RDX)
            value=uc.reg_read(UC_X86_REG_R8)&255
            target=uc.reg_read(UC_X86_REG_R9)
            uc.mem_write(target,bytes([value])*length)
            self.ret(0)
        elif address==BASE+0x1a64d0:
            self.ret(0)

    def function(self,rva,*args):
        sp=STACK+0x8000-8
        self.write(sp,RETURN,8)
        self.uc.reg_write(UC_X86_REG_RSP,sp)
        for reg,arg in zip((UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8,UC_X86_REG_R9),args):
            self.uc.reg_write(reg,int(arg))
        self.uc.emu_start(BASE+rva,RETURN,count=50000000)
        assert self.uc.reg_read(UC_X86_REG_RIP)==RETURN,hex(self.uc.reg_read(UC_X86_REG_RIP))


def initialize_geometry(r):
    g=MapGeometry
    for y in range(800):
        left=(800-ROW_COUNTS[y])//2
        start=int(ROW_STARTS[y])
        row=np.array([start-left,ROW_COUNTS[y],ROW_STARTS[y+1]],dtype='<i4')
        r.uc.mem_write(BASE+0x402ff2c+y*12,row.tobytes())
        if 0<y<799:
            i=int(g.index_grid[y,400])
            r.uc.mem_write(TM+y*32,(nav.neighbors()[i]-i).astype('<i4').tobytes())
    # No buildings or gates in this replay; C5040/C4BF0 execute their empty loops.
    r.write(BASE+0x64ccbb0+0x50,1,4)


def main():
    r=NavigationReplay()
    initialize_geometry(r)
    g=MapGeometry
    n=g.count
    logic=np.full(n,0x10,dtype=np.uint32)
    height=np.full(n,80,dtype=np.uint8)
    damage=np.zeros(n,dtype=np.int8)
    slots=np.zeros(n,dtype=np.uint16)
    types=np.zeros(n,dtype=np.int16)
    tree_pass=np.zeros(n,dtype=np.uint8)
    probes={}
    # Five separated islands exercise seed eligibility for ordinary/raised
    # ground, sea, river and ford. Heights affect edges, not component seeds.
    for k,(name,flag,h) in enumerate((('land',0x8000,8),('sea',1,0),
            ('river',0x100000,0),('ford',0x200000,0),('high_plateau',0x8000,130))):
        ids=g.index_grid[380:388,300+k*30:308+k*30].ravel()
        logic[ids]=flag
        height[ids]=h
        probes[name]=int(ids[0])
    edges=np.zeros(n,dtype=np.uint8)
    port=np.zeros(n,dtype=np.uint16)
    nav._native()(n,*(a.ctypes.data for a in (logic,height,damage,slots,types,tree_pass,
                  nav.neighbors(),edges,port)),1)
    r.uc.mem_write(FLAGS,logic.tobytes())
    r.uc.mem_write(EDGES,edges.tobytes())
    r.function(0xe49d0,CONTEXT,1)
    actual=np.frombuffer(r.uc.mem_read(COMPONENTS,n*2),dtype='<u2').copy()
    mismatches=np.flatnonzero(actual!=port)
    component_result={'cells':n,'mismatch_count':len(mismatches),
        'first_mismatches':[dict(tile=int(i),native=int(actual[i]),port=int(port[i])) for i in mismatches[:8]],
        'probe_labels':{name:dict(native=int(actual[i]),port=int(port[i])) for name,i in probes.items()},
        'scope':'full scan with separated land/sea/river/ford/high plateau islands; no buildings or vegetation'}

    # Direct DE6A0 checks isolate reciprocal-edge writes independently from
    # D86F0's corner queue construction. Neighbor obstacles and borders vary.
    rng=np.random.default_rng(2026102302)
    centers=g.index_grid[300:500:10,300:500:10].ravel()
    logic=np.full(n,0x8000,dtype=np.uint32)
    touched=np.unique(np.concatenate((centers,nav.neighbors()[centers].ravel())))
    touched=touched[touched>=0]
    logic[touched]=rng.choice(np.array([0,0x8000,1,0x10,0x20,0x80,0x100,0x400,
        0x100000,0x200000,0x20008000,0x28000,0x88000],dtype=np.uint32),len(touched))
    expected=rng.integers(0,256,n,dtype=np.uint8)
    r.uc.mem_write(FLAGS,logic.tobytes())
    r.uc.mem_write(EDGES,expected.tobytes())
    for i in centers:
        mask=int(expected[i])
        for direction,j in enumerate(nav.neighbors()[i]):
            if j<0 or int(logic[j])&0x30 or int(logic[j])&0x4a5014b1:
                continue
            opposite=1<<((direction+4)%8)
            expected[j]=(int(expected[j])|opposite) if mask&(1<<direction) else (int(expected[j])&~opposite)
        r.function(0xde6a0,CONTEXT,int(i),int(g.y[i]))
    actual_edges=np.frombuffer(r.uc.mem_read(EDGES,n),dtype=np.uint8)
    edge_mismatches=np.flatnonzero(actual_edges!=expected)
    cleanup_result={'source_cells':len(centers),'compared_cells':n,'mismatch_count':len(edge_mismatches),
        'first_mismatches':[dict(tile=int(i),native=int(actual_edges[i]),port=int(expected[i]))
                            for i in edge_mismatches[:8]],
        'scope':'random initial edge bytes and mixed flags; no tree pass-through branch'}

    gate_mismatches=[]
    rng=np.random.default_rng(2026102303)
    for case in range(80):
        raw=bytearray(812)
        orientation=80 if case&1 else 0
        state=2 if case&2 else 0
        side=5 if case&4 else 7
        x=y=400
        struct.pack_into('<hh',raw,0xee,x,y)
        struct.pack_into('<i',raw,0xf8,side)
        struct.pack_into('<h',raw,0x102,orientation)
        raw[0x2a2]=state
        gate=np.frombuffer(raw,dtype=np.uint8).copy()
        logic=np.full(n,0x8000,dtype=np.uint32)
        base=np.full(n,80,dtype=np.uint8)
        current=base.copy()
        if orientation==80:
            endpoints=[(x-1,y+side//2),(x,y+side//2),(x+side,y+side//2),(x+side-1,y+side//2)]
        else:
            endpoints=[(x+side//2,y-1),(x+side//2,y),(x+side//2,y+side),(x+side//2,y+side-1)]
        indices=np.array([g.index_grid[yy,xx] for xx,yy in endpoints])
        logic[indices]=rng.choice(np.array([0,0x8000,1,0x80,0x400],dtype=np.uint32),4)
        base[indices]=rng.choice(np.array([63,64,80,96,97],dtype=np.uint8),4)
        current[indices]=rng.choice(np.array([63,64,80,96,97],dtype=np.uint8),4)
        initial=rng.integers(0,256,n,dtype=np.uint8)
        expected=initial.copy()
        fake=SimpleNamespace(geometry=g,grid=lambda sid:{3003:logic,3045:base,3005:current}[sid])
        nav._gate_edges(fake,expected,[gate],tree_pass,closed=False)
        r.uc.mem_write(BASE+0x64ccbb0+0x5c+812,bytes(raw))
        r.uc.mem_write(FLAGS,logic.tobytes())
        r.uc.mem_write(BASE+0x4e2b870,base.tobytes())
        r.uc.mem_write(BASE+0x4ddd350,current.tobytes())
        r.uc.mem_write(EDGES,initial.tobytes())
        r.function(0xd8ce0,CONTEXT,1)
        actual_gate=np.frombuffer(r.uc.mem_read(EDGES,n),dtype=np.uint8)
        bad=np.flatnonzero(actual_gate!=expected)
        if len(bad):
            gate_mismatches.append(dict(case=case,orientation=orientation,state=state,
                cells=[dict(tile=int(i),native=int(actual_gate[i]),port=int(expected[i])) for i in bad[:8]]))
    gate_result={'cases':80,'mismatch_count':len(gate_mismatches),
                 'first_mismatches':gate_mismatches[:8],
                 'scope':'both gate orientations, sizes5/7, open/closed, unequal current/base heights and obstacle flags; no tree exception'}
    result={'dll_sha256':'fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2',
            'offline_only':True,'E49D0':component_result,'DE6A0':cleanup_result,'D8CE0':gate_result}
    out=ROOT/'output/navigation-update-2026-10-23/component-native-comparison.json'
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    if len(mismatches) or len(edge_mismatches) or gate_mismatches:
        raise SystemExit(1)


if __name__=='__main__':
    main()
