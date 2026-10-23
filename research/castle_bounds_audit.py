"""Read the pinned installed DLL and export castle/range evidence; never execute it."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import capstone
import pefile


PINNED_SHA256='fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2'
DEFAULT_DLL=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Stronghold Crusader Definitive Edition\Stronghold Crusader Definitive Edition_Data\Plugins\x86_64\CrusaderDE.dll')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll',type=Path,default=DEFAULT_DLL)
    parser.add_argument('--output',type=Path,default=Path('output/castle-bounds-2026-10-23'))
    args=parser.parse_args()
    digest=hashlib.sha256(args.dll.read_bytes()).hexdigest()
    if digest!=PINNED_SHA256:
        raise ValueError('DLL differs from the analyzed version; research must be revalidated')
    pe=pefile.PE(str(args.dll))
    dis=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
    ranges={'radius_table':(0x6af00,0x6af5e),'range_check':(0xeef90,0xef0cd),
            'distance':(0x79c0,0x7a1a),'placement_range_cases':(0x780d0,0x78586),
            'beach_neighbor_guard':(0x64a50,0x64b47),'keep_center':(0xd0630,0xd0960)}
    args.output.mkdir(parents=True,exist_ok=True)
    for name,(start,end) in ranges.items():
        rows=[f'{i.address:08X} {i.mnemonic} {i.op_str}'
              for i in dis.disasm(pe.get_data(start,end-start),start)]
        (args.output/(name+'.capstone.asm')).write_text('\n'.join(rows)+'\n',encoding='utf-8')
    counts=struct.unpack('<10i',pe.get_data(0x2d1c38,40))
    camp_offsets=[struct.unpack('<2i',pe.get_data(0x2d3210+i*8,8)) for i in range(20)]
    evidence={'dll_sha256':digest,'image_base':hex(pe.OPTIONAL_HEADER.ImageBase),
              'preset_sizes':[160,200,300,400,500,600,700,800],
              'radius_by_size':{160:45,200:50,300:60,400:70,500:80,600:90,700:100,800:100},
              'nonpreset_default_radius':70,'brush_count_table_rva':'0x2D1C38',
              'brush_counts':counts,'camp_offset_table_rva':'0x2D3210',
              'camp_offsets':camp_offsets,
              'native_flag_with_unverified_menu_name_rva':'0x8574B90',
              'clear_radius_normal':6,'clear_radius_surface_mask_0x90_nonzero':2}
    (args.output/'castle_bounds_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sha256':digest,'output':str(args.output),'functions':len(ranges)}))


if __name__=='__main__':
    main()
