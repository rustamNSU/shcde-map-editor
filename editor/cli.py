"""JSON command interface, suitable for agents and reproducible map recipes."""
import argparse
import json
from pathlib import Path
import sys
from . import MapReader, MapWriter, TemplateLibrary, TerrainService, EntityService, MapValidator, PatternLibrary
from .geometry import SUPPORTED_MAP_SIZES


def apply_recipe(document, recipe, directory=Path('.')):
    if recipe.get('version') != 1:
        raise ValueError('Recipe version must be 1')
    if set(recipe) - {'version', 'operations'}:
        raise ValueError('Unknown recipe keys')
    operations = recipe.get('operations', [])
    if not isinstance(operations, list):
        raise ValueError('operations must be a list')
    results = []
    with document.transaction('Apply recipe'):
        for op in operations:
            kind = op.get('op')
            if kind in ('plant_trees','remove_tree'):
                from .trees import TreeService
                service=TreeService(document)
                if kind=='remove_tree':
                    if set(op)-{'op','x','y'}: raise ValueError('Unknown tree removal keys')
                    results.append(service.remove(op['x'],op['y']))
                else:
                    if set(op)-{'op','type','brush'}: raise ValueError('Unknown tree placement keys')
                    brush=op['brush']; ids=document.geometry.brush(brush['x'],brush['y'],brush['size'],brush.get('shape','square'))
                    results.append(service.paint(ids,str(op['type'])))
                continue
            if kind in ('set_height','set_variation'):
                from .services import HeightService, VariationService
                field='height' if kind=='set_height' else 'variation'
                if set(op)-{'op',field,'rect','brush'} or ('rect' in op)==('brush' in op):
                    raise ValueError(kind+' needs '+field+' and exactly one rect or brush')
                if 'rect' in op: ids=document.geometry.rectangle(*op['rect'])
                else:
                    brush=op['brush']
                    ids=document.geometry.brush(brush['x'],brush['y'],brush['size'],brush.get('shape','square'))
                service=HeightService(document) if kind=='set_height' else VariationService(document)
                results.append(service.paint(ids,op[field]))
                continue
            if kind in ('place_building','remove_building'):
                from .buildings import BuildingService
                allowed={'op','x','y'} | ({'building','owner'} if kind=='place_building' else set())
                if set(op)-allowed: raise ValueError('Unknown building operation keys')
                service=BuildingService(document)
                results.append(service.place(op['building'],op['x'],op['y'],op.get('owner',1)) if kind=='place_building'
                               else service.remove(op['x'],op['y']))
                continue
            common = {'op', 'material', 'experimental_resources', 'variation'}
            permitted = {'paint': {'rect', 'brush'}, 'stamp': {'pattern', 'x', 'y', 'rotation', 'mirror', 'invert'}}
            if kind not in permitted or set(op) - common - permitted[kind]:
                raise ValueError('Unknown operation or keys: ' + str(kind))
            if kind == 'paint':
                if ('rect' in op) == ('brush' in op):
                    raise ValueError('Paint needs exactly one of rect or brush')
                if 'rect' in op:
                    ids = document.geometry.rectangle(*op['rect'])
                else:
                    brush = op['brush']
                    ids = document.geometry.brush(brush['x'], brush['y'], brush['size'], brush.get('shape', 'square'))
            else:
                pattern = PatternLibrary.load(directory / op['pattern']).transform(op.get('rotation', 0), op.get('mirror', False), op.get('invert',False))
                if pattern.is_height:
                    if 'material' in op or 'variation' in op:
                        raise ValueError('A height mask stamps its stored elevations; omit material and variation')
                    from .services import HeightService
                    ids,values=pattern.height_samples(document.geometry,op['x'],op['y'])
                    results.append(HeightService(document).paint_values(ids,values))
                    continue
                ids = pattern.indices(document.geometry, op['x'], op['y'])
            if not isinstance(op.get('experimental_resources', False), bool):
                raise ValueError('experimental_resources must be a boolean')
            results.append(TerrainService(document).paint(ids, op['material'], op.get('experimental_resources', False), variation=op.get('variation')))
    return results


def run(argv):
    parser = argparse.ArgumentParser(prog='SHCDEMapEditor --cli')
    parser.add_argument('--report', type=Path, help='Write JSON result (required for windowed exe output)')
    sub = parser.add_subparsers(dest='command', required=True)
    inspect_p = sub.add_parser('inspect')
    inspect_p.add_argument('input', type=Path)
    inspect_p.add_argument('--cell', nargs=2, type=int)
    validate_p = sub.add_parser('validate')
    validate_p.add_argument('input', type=Path)
    edit = sub.add_parser('edit')
    source = edit.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path)
    source.add_argument('--size', type=int, choices=SUPPORTED_MAP_SIZES)
    edit.add_argument('--recipe', type=Path)
    edit.add_argument('--output', type=Path)
    edit.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'edit':
            if not args.dry_run and not args.output:
                raise ValueError('Specify --output or --dry-run')
            d = MapReader.open(args.input) if args.input else TemplateLibrary().create(args.size)
            results = apply_recipe(d, json.loads(args.recipe.read_text(encoding='utf-8')), args.recipe.parent) if args.recipe else []
            report = {'ok': True, 'operations': results, 'validation': MapValidator.validate(d), 'dry_run': args.dry_run}
            if not args.dry_run:
                report['export'] = MapWriter.save_as(d, args.output)
        else:
            d = MapReader.open(args.input)
            report = {'ok': True, 'validation': MapValidator.validate(d)}
            if args.command == 'inspect':
                report.update(size=d.size, version=d.container.version, menu=d.container.menu_metadata(),
                              entity_record_counts={kind: len(EntityService(d).records(kind)) for kind in ('buildings', 'units', 'vegetation')})
                if args.cell:
                    report['cell'] = TerrainService(d).inspect(*args.cell)
                    report['objects'] = EntityService(d).at(*args.cell)
    except Exception as error:
        report = {'ok': False, 'error': str(error), 'error_type': type(error).__name__}
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        # Reports never overwrite existing files, including accidental input paths.
        with args.report.open('x', encoding='utf-8') as stream:
            stream.write(text)
    if sys.stdout is not None:
        print(text)
    return 0 if report['ok'] and report.get('validation', {}).get('valid', True) else 1
