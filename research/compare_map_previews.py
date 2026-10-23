"""Compare a saved native radar thumbnail with the current offline renderer.

Read-only inputs; write only PNG/JSON evidence into an explicitly named folder.
Run from the repository root with .venv/Scripts/python -m research.compare_map_previews.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from editor.document import MapReader
from editor.preview import encode_preview


def decode_preview(data):
    if len(data) != 40512:
        raise ValueError('Expected 512-byte palette plus 200x200 indices')
    palette = np.frombuffer(data[:512], dtype='<u2').astype(np.uint32)
    rgb = np.column_stack(((palette >> 10) & 31, (palette >> 5) & 31, palette & 31))
    # Native F6FB0 expands 5-bit channels with <<3, not full-range rescaling.
    # Keep stored row order for both images; Unity's texture buffer is flipped.
    rgb = (rgb << 3).astype(np.uint8)
    indices = np.frombuffer(data[512:], dtype=np.uint8).reshape(200, 200)
    return Image.fromarray(rgb[indices])


def compare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or source in output.parents:
        raise ValueError('Output must be separate from source map')
    source_bytes = source.read_bytes()
    digest = hashlib.sha256(source_bytes).hexdigest()
    document = MapReader.open(source)
    native = document.container.preview
    generated = encode_preview(document)
    native_image = decode_preview(native)
    generated_image = decode_preview(generated)
    output.mkdir(parents=True, exist_ok=True)
    native_image.save(output / 'native.png')
    generated_image.save(output / 'current-editor.png')
    sheet = Image.new('RGB', (1248, 666), '#202124')
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 23)
    except OSError:
        font = ImageFont.load_default()
    for index, (label, image) in enumerate((
        ('Built-in game editor: stored thumbnail', native_image),
        ('Our editor: regenerated from the same map', generated_image),
    )):
        x = 16 + index * 616
        draw.text((x, 14), label, fill='white', font=font)
        sheet.paste(image.resize((600, 600), Image.Resampling.NEAREST), (x, 50))
    sheet.save(output / 'comparison.png')
    a, b = np.asarray(native_image), np.asarray(generated_image)
    result = {
        'source': str(source), 'source_sha256': digest, 'map_size': document.size,
        'decoded_thumbnail_bytes': len(native),
        'format': 'DCL-compressed RGB555 palette (256 uint16) + 200x200 uint8 indices',
        'inspection_decode': 'Native channel expansion (5-bit <<3), stored raster row order for both images',
        'native_palette_indices_used': len(set(native[512:])),
        'current_palette_indices_used': len(set(generated[512:])),
        'pixels_with_different_rgb': int(np.any(a != b, axis=2).sum()),
        'comparison_scope': 'Same saved map; no source edits. Current schematic renderer only.',
        'source_unchanged': hashlib.sha256(source.read_bytes()).hexdigest() == digest,
    }
    if not result['source_unchanged']:
        raise RuntimeError('Input map changed during comparison')
    (output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.source, args.output), indent=2))


if __name__ == '__main__':
    main()
