"""Extract pinned native starting-gold tables without executing the game DLL."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import pefile


PINNED_SHA256 = "fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2"
DEFAULT_DLL = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Stronghold Crusader Definitive Edition"
    r"\Stronghold Crusader Definitive Edition_Data\Plugins\x86_64\CrusaderDE.dll"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, default=DEFAULT_DLL)
    parser.add_argument("--output", type=Path,
                        default=Path("output/gold-startup-2026-10-23/native_gold_evidence.json"))
    args = parser.parse_args()
    digest = hashlib.sha256(args.dll.read_bytes()).hexdigest()
    if digest != PINNED_SHA256:
        raise ValueError("DLL differs from the pinned research version")
    pe = pefile.PE(str(args.dll))
    rows = []
    for goods_level in range(1, 5):
        rows.append({
            "starting_goods_level": goods_level,
            "fairness_1_to_5_human_ai_pairs": [
                list(struct.unpack("<2i", pe.get_data(
                    0x2D4DA0 + ((goods_level - 1) * 5 + fairness - 1) * 8, 8)))
                for fairness in range(1, 6)
            ],
        })
    evidence = {
        "dll_sha256": digest,
        "image_base": hex(pe.OPTIONAL_HEADER.ImageBase),
        "starting_gold_pair_table_rva": "0x2D4DA0",
        "starting_gold_pairs": rows,
        "section2022_source_rva": "0x379ADD0",
        "player_record_stride": "0x583C",
        "total_gold_record_offset": "0x50C",
        "incoming_gold_record_offset": "0x4A8",
        "new_match_totals_clear": [
            {"player": player,
             "cleared_span_rva_inclusive": [
                 hex(0x379ADD0 + player * 0x583C + 0x4D0),
                 hex(0x379ADD0 + player * 0x583C + 0x533)],
             "gold_rva": hex(0x379ADD0 + player * 0x583C + 0x50C)}
            for player in range(1, 9)
        ],
        "reviewed_instruction_locations": {
            "multiplayer_save_early_branch": "0x95540..0x955D5",
            "totals_clear_including_gold": "0x957D4..0x9592F",
            "incoming_gold_from_default_goods": "0xD1392..0xD1398",
            "incoming_gold_fairness_override": "0xD14A3..0xD1552",
        },
        "scope": "File-only data extraction plus separately reviewed Ghidra instructions; no live-game test",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sha256": digest, "output": str(args.output), "goods_levels": len(rows)}))


if __name__ == "__main__":
    main()
