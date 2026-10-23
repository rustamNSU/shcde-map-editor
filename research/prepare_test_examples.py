"""Restore missing, hash-pinned local test copies; never change source maps.

The original examples are private research inputs, not release assets. Supply
their directory explicitly; existing destination files must be byte-identical.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = {
    '3v3 Einstein SquaD.map': '8762bd1d32ac6e6665f9ac5122149de979503568fc6ebfe3c41cb8604b8fdec3',
    '2v2 Einstein SquaD v2.0.map': '6c197ee48e3374134439ef9f3cd4536cbe09e5d9a6ea74d711a02a0f67cfb8bf',
    '001 3 green Fenrir - 6 wathcers.map': '2291f860ca42b405cad7ea7e66fef8e50d3b07cafe176368ecb48623d3fcb70d',
    '1x1 - sword no lions.map': '7b4bda25adc9f1e8fdcc02d3984fdb6b8125e05b9bda95678ea99060699d9a77',
    '3v3 Einstein v1.1.map': '54ad84015e8d767338d8007285f94d2240984eec4dd24a7c27479f6ad5493d38',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    destination = ROOT/'examples'
    pending = []
    for name, expected in EXAMPLES.items():
        source, target = args.source/name, destination/name
        data = source.read_bytes()
        if digest(data) != expected:
            raise ValueError('Source differs from pinned test fixture: ' + str(source))
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Existing fixture differs; refusing replacement: ' + str(target))
        pending.append((source, target, data, expected))
    destination.mkdir(exist_ok=True)
    provenance = []
    for source, target, data, expected in pending:
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(data)
        if digest(target.read_bytes()) != expected or digest(source.read_bytes()) != expected:
            raise ValueError('Fixture/source changed during preparation')
        provenance.append(dict(source=str(source.resolve()), copy=str(target.resolve()), sha256=expected))
    output = ROOT/'output/test-fixture-provenance.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print('Five test fixtures available; pinned hashes verified; source maps unchanged.')


if __name__ == '__main__':
    main()
