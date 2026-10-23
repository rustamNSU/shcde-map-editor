"""Read-only pinned DLL evidence for the legacy wood-wall mapper."""
from pathlib import Path
import hashlib
import json
import re
import struct
import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/wood-wall-2026-10-23'
DLL = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Stronghold Crusader Definitive Edition\Stronghold Crusader Definitive Edition_Data\Plugins\x86_64\CrusaderDE.dll')
PINNED = 'fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2'

def main():
    raw=DLL.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==PINNED
    pe=pefile.PE(data=raw)
    base=pe.OPTIONAL_HEADER.ImageBase
    dis=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64); dis.detail=True
    pdata=[(e.struct.BeginAddress,e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION]
    def root(e):
        unwind=e.struct.UnwindData
        for _ in range(20):
            flags,_,count,_=pe.get_data(unwind,4)
            if not flags>>3&4:return e.struct.BeginAddress if unwind==e.struct.UnwindData else begin
            begin,_,unwind=struct.unpack('<3I',pe.get_data(unwind+4+((count+1)//2)*4,12))
        raise RuntimeError('unwind chain loop')
    grouped={}
    for e in pe.DIRECTORY_ENTRY_EXCEPTION:grouped.setdefault(root(e),[]).append((e.struct.BeginAddress,e.struct.EndAddress))
    OUT.mkdir(parents=True,exist_ok=True)
    pattern=re.compile(bytes.fromhex('41 FF 94 C6')+b'.{4}'+bytes.fromhex('4C 63 05'),re.S)
    hits=[]
    for s in pe.sections:
        if s.Characteristics&0x20000000:
            hits += [s.VirtualAddress+m.start() for m in pattern.finditer(s.get_data())]
    assert len(hits)==1, hits
    ins=next(dis.disasm(pe.get_data(hits[0],15),hits[0],count=1))
    table=ins.operands[0].mem.disp
    values=struct.unpack('<145Q',pe.get_data(table,145*8))
    result={'sha256':PINNED,'image_base':hex(base),'building_dispatch_call_rva':hex(hits[0]),
            'building_function_table_rva':hex(table),'entries':[],'functions':{}}
    targets={0xc77c0,0x6d580,0x7a3b0,0xc8cc0,0xcf640,0xc62f0,0x5b020}
    scans={'build_wall':'44 89 4C 24 ?? 44 89 44 24 ?? 89 54 24 ?? 48 89 4C 24 ?? 53 56 57',
           'ai_build_wall':'48 89 5C 24 ? 48 89 6C 24 ? 56 57 41 56 48 83 EC ? 0F B7 5C 24'}
    for name,pat in scans.items():
        rx=re.compile(b''.join(b'.' if '?' in x else re.escape(bytes([int(x,16)])) for x in pat.split()),re.S)
        matches=[s.VirtualAddress+m.start() for s in pe.sections if s.Characteristics&0x20000000 for m in rx.finditer(s.get_data())]
        assert len(matches)==1,(name,matches)
        result[name+'_rva']=hex(matches[0]); targets.add(matches[0])
    for i in (0,47,90,108,109,110,111,112,113,114,127,128):
        addr=values[i]-base if values[i] else None
        valid=addr is not None and 0<=addr<pe.OPTIONAL_HEADER.SizeOfImage
        result['entries'].append({'index':i,'pointer':hex(values[i]),'valid_image_pointer':valid,'update_rva':hex(addr) if valid else None,'bytes':pe.get_data(addr,32).hex() if valid else None})
        if valid:targets.add(addr)
    # Explicit additional target RVAs can be passed as hex arguments.
    import sys
    targets.update(int(x,16) for x in sys.argv[1:])
    requests=[]
    for rva in sorted(targets):
        contains=[(s,e) for s,e in pdata if s<=rva<e]
        ranges=next((v for v in grouped.values() if any(s<=rva<e for s,e in v)),None)
        if ranges is None:ranges=[(rva,rva+0x40)]
        if rva==0xc77c0:ranges=[(rva,0xc7a1e)]
        if rva in (0xace80,0xace90):ranges=[(rva,rva+3)]
        start=min(s for s,e in ranges); end=max(e for s,e in ranges)
        label=f'wood_native_{rva:x}'
        rows=[f'{i.address:08X} {i.bytes.hex(" "):<32} {i.mnemonic} {i.op_str}' for s,e in ranges for i in dis.disasm(pe.get_data(s,e-s),s)]
        (OUT/(label+'.capstone.asm')).write_text('\n'.join(rows)+'\n',encoding='utf8')
        result['functions'][hex(rva)]={'start':hex(start),'end':hex(end),'label':label}
        requests.append(f'{label}:{start:x}:'+','.join(f'{s:x}-{e:x}' for s,e in ranges))
    result['confirmed_wall_behavior']={'mapper46_height_delta':60,'mapper25_height_delta':90,
        'generic_wall_logic_bit':'0x100','mapper46_additional_logic_bit':'0x10000',
        'low_height_add_rva':'0x6F4A3','low_logic_or_rva':'0x6F721',
        'cost_selection_call_rva':'0x6F91E','cost_helper_rva':'0xC8CC0',
        'normal_cost_formula':'q = previous_remainder + 2*high_count + low_count; stone_cost = floor(q/4); next_remainder = q & 3',
        'resource_id':4,'resource_id_sdk_name':'STORED_STONE_BLOCKS',
        'resource_id_instruction_rva':'0xC8D44','remove_resource_call_rva':'0xC8D5F',
        'mode_limit':'normal resource-paying mode only; native globals bypass or specialize other game modes'}
    (OUT/'native_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    (ROOT/'research/wood_wall_native_requests.txt').write_text('\n'.join(requests)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
