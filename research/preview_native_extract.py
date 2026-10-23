"""File-only extraction of pinned native radar tables and targeted code xrefs.

Run with a Python containing pefile/capstone. No game execution or map writes.
"""
import hashlib
import json
from pathlib import Path
import struct
import capstone
from capstone.x86 import X86_OP_MEM, X86_OP_IMM, X86_REG_RIP
import pefile

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT.parent / 'shc-dashboard/artifacts/ballista-cow-static/CrusaderDE.snapshot.dll'
OUT = ROOT / 'output/preview-native-2026-10-23'
SHA = 'fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2'


def main():
    data = DLL.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA
    pe = pefile.PE(data=data)
    base = pe.OPTIONAL_HEADER.ImageBase
    OUT.mkdir(parents=True, exist_ok=True)
    tables = []
    for rva, count, condition in [
        (0x312690,8,'Luminescence multipliers; index byte & 0xFE; skip shading for byte=2'),
        (0x3126B0,1,'PitchTrap plus MiscDisplayGrid bit 0x2000 override'),
        (0x3126B4,1,'Neutral/special-unit colour'),
        (0x3126B8,8,'Logic & 1 (Sea), random & 7'),
        (0x3126D8,4,'Logic & 0x100000 (River), random & 3'),
        (0x3126E8,8,'Logic & 0x200000 (Ford), random & 7'),
        (0x312708,4,'Logic & 0x40000000 (Moat), random & 3; late override'),
        (0x312718,8,'Logic & 0x20000 (HasStone), random & 7'),
        (0x312738,4,'Logic & 0x80 (ImpassableEdge), random & 3'),
        (0x312748,4,'Logic & 0x40000 (Unknown18), random & 3'),
        (0x312768,4,'Surface & 0x20 (BeachOrWaves), random & 3'),
        (0x312778,4,'Logic & 0x80000 (HasIron), random & 3'),
        (0x312788,4,'Logic & 0xA0000000 (Swamp/Pitch), random & 3'),
        (0x312798,8,'Ordinary ground height <=16, random & 7'),
        (0x3127B8,8,'Surface &2 or Logic &8, random &7'),
        (0x3127D8,4,'Logic &0x3000 (Tree/TreeProximity), random &3; late override'),
        (0x3127E8,4,'Surface &0x40 or ordinary ground height>16, random &3'),
        (0x3127F8,4,'Surface &1 and Logic &0x8000, random &3'),
        (0x312808,4,'Surface &0x80 and Logic &0x8000, random &3'),
        (0x312818,4,'Surface &0x10 and Logic &0x8000, random &3'),
        (0x312880,36,'Owner colours; colour-owner remap at0x2C3CE0; 4 variants each'),
    ]:
        values=list(struct.unpack('<'+'I'*count,pe.get_data(rva,count*4)))
        tables.append(dict(rva=hex(rva),count=count,condition=condition,
            values=[hex(v) for v in values],rgb=[[(v>>16)&255,(v>>8)&255,v&255] for v in values]))
    overrides=list(struct.iter_unpack('<II',pe.get_data(0x312910,8*8)))
    doc=dict(dll_path=str(DLL),sha256=SHA,tables=tables,
        overrides=[dict(mask=hex(a),color=hex(b)) for a,b in overrides],
        projection_parameters=dict(
            columns='native alternating-width diamond scan, clipped before destination mapping',
            row_stride='lookup cursor alternates400/401; loop column count is runtime W/W+1 from0x3A11E68; lookup starts0x322+8 per rotation',
            destination='x=trunc(2*(column-trunc(margin/2)+xdelta)/step)+xoffset; y=row/step-margin+ydelta+yoffset',
            rows={
                '160':dict(step=1,margin=320,xdelta=0,ydelta=0,xoffset=20,yoffset=20,xlimit=80,ylimit=160),
                '200':dict(step=1,margin=300,xdelta=0,ydelta=0,xoffset=0,yoffset=0,xlimit=100,ylimit=200),
                '300':dict(step=2,margin=125,xdelta=-50,ydelta=0,xoffset=12,yoffset=25,xlimit=170,ylimit=150),
                '400':dict(step=2,margin=200,xdelta=0,ydelta=100,xoffset=0,yoffset=0,xlimit=200,ylimit=200),
                '500':dict(step=3,margin=33,xdelta=-32,ydelta=0,xoffset=0,yoffset=0,xlimit=300,ylimit=200),
                '600':dict(step=3,margin=100,xdelta=0,ydelta=66,xoffset=0,yoffset=0,xlimit=300,ylimit=200),
                '700':dict(step=4,margin=0,xdelta=2,ydelta=0,xoffset=0,yoffset=0,xlimit=400,ylimit=200),
                '800':dict(step=4,margin=0,xdelta=0,ydelta=0,xoffset=0,yoffset=0,xlimit=400,ylimit=200),
            }))
    (OUT/'tables-and-projection.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
    targets={0x3a11e68,0x3b4ace4,0x4ec82b0,0xf4df0}
    md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True;md.skipdata=True
    funcs=[(e.struct.BeginAddress,e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION]
    lines=[]
    for sec in pe.sections:
        if not sec.Characteristics&0x20000000:continue
        for ins in md.disasm(sec.get_data(),base+sec.VirtualAddress):
            if ins.id==0:continue
            matched=set()
            for op in ins.operands:
                if op.type==X86_OP_MEM:
                    target=ins.address+ins.size+op.mem.disp-base if op.mem.base==X86_REG_RIP else op.mem.disp
                    if target in targets:matched.add(target)
                if op.type==X86_OP_IMM and op.imm-base in targets:matched.add(op.imm-base)
            if matched:
                rva=ins.address-base
                envelope=next((f for f in funcs if f[0]<=rva<f[1]),None)
                lines.append(dict(rva=hex(rva),instruction=ins.mnemonic+' '+ins.op_str,
                    target=[hex(v) for v in matched],unwind_chunk=[hex(v) for v in envelope] if envelope else None))
    (OUT/'targeted-xrefs.json').write_text(json.dumps(lines,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tables=len(tables),xrefs=len(lines),output=str(OUT))))


if __name__=='__main__':main()
