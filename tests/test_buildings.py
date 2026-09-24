import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
from editor import TemplateLibrary,MapDocument,MapWriter,MapReader,EntityService,MapValidator
from editor.buildings import BuildingService,catalog,H,I
from editor.cli import apply_recipe
from research.reference_findings import player_links


class BuildingsTests(unittest.TestCase):
    def test_native_reference_castle_can_be_removed_and_replaced(self):
        path=Path(__file__).resolve().parents[1]/'output/castle-audit-2026-09-20/ref_12_castle.map'
        original=path.read_bytes(); d=MapDocument(original); b=BuildingService(d)
        before=d.edit_digest()
        self.assertEqual(b.remove(411,406)['removed'],10)
        d.history.undo(); self.assertEqual(d.edit_digest(),before)
        d.history.redo()
        made=b.place('castle',401,404,1)
        raw=d.section(4013)['decoded']; slot=made['records']['buildings'][0]
        self.assertEqual(I(raw,slot*812+0x2a8),I(raw,slot*812+0xd8))
        reopened=MapDocument(MapWriter.serialize(d))
        self.assertEqual(len(EntityService(reopened).records('units')),1)
        self.assertEqual(I(reopened.section(2022)['decoded'],0x583c+0x84),1)
        self.assertEqual(path.read_bytes(),original)

    def test_validator_detects_old_group_id_regression(self):
        d=TemplateLibrary().create(400); made=BuildingService(d).place('castle',390,390)
        self.assertEqual(MapValidator.validate(d)['errors'],[])
        raw=bytearray(d.section(4013)['decoded'])
        for slot in made['records']['buildings']:
            struct.pack_into('<I',raw,slot*812+0x2a8,4032)
        d.replace_section(4013,raw,'Simulate old writer bug')
        self.assertIn('Castle has stale building group IDs',MapValidator.validate(d)['errors'])
        self.assertIn('Castle has stale stockpile group IDs',MapValidator.validate(d)['errors'])

    def test_castle_replacement_initialization_and_dead_lord_cleanup(self):
        for size in (400,500):
            d=TemplateLibrary().create(size)
            for owner in (1,8):
                at=owner*0x583c
                player=bytearray(d.section(2022)['decoded'])
                struct.pack_into('<I',player,at+0x50c,12345)
                struct.pack_into('<I',player,at+0x84,7)
                d.replace_section(2022,player,'Existing player resources')
                for cycle in range(2):
                    b=BuildingService(d); before=d.edit_digest()
                    made=b.place('castle',390,390,owner)
                    building=d.section(4013)['decoded']
                    slots=made['records']['buildings']; roots=[I(building,slots[i]*812+0xd8) for i in (0,5)]
                    for i,slot in enumerate(slots):
                        self.assertEqual(I(building,slot*812+0x2a8),roots[i>=5])
                    unit_slot=made['records']['units'][0]
                    unit=d.section(3015)['decoded'][unit_slot*1168:(unit_slot+1)*1168]
                    self.assertEqual(struct.unpack_from('<HH',unit,0xc4),(393,392))
                    self.assertEqual(I(unit,0x3c8),150000)
                    self.assertEqual(I(unit,0x80),owner)
                    self.assertEqual(H(unit,0x338),slots[0])
                    player=d.section(2022)['decoded']
                    for off in (0xa4,0xcc,0x1e4,0x489c): self.assertEqual(I(player,at+off),1)
                    self.assertEqual(I(player,at+0x84),8)
                    self.assertEqual(I(player,at+0x50c),12345)
                    placed=d.edit_digest(); d.history.undo(); self.assertEqual(d.edit_digest(),before)
                    d.history.redo(); self.assertEqual(d.edit_digest(),placed)
                    d=MapDocument(MapWriter.serialize(d)); b=BuildingService(d)
                    # Removal through a stockpile child after export/reopen.
                    b.remove(400,392)
                    player=d.section(2022)['decoded']
                    for off in (0xa4,0xcc,0x1e4,0x489c,0x21f8,0x21fc): self.assertEqual(I(player,at+off),0)
                    self.assertEqual(I(player,at+0x84),7)
                    self.assertEqual(I(player,at+0x50c),12345)
                    self.assertFalse(any(d.section(3015)['decoded'][unit_slot*1168:(unit_slot+1)*1168]))
                    self.assertEqual(H(d.section(1190)['decoded'],owner*2),0)
                    self.assertEqual(I(d.section(1191)['decoded'],owner*4),0)
                made=b.place('castle',390,390,owner)
                slot=made['records']['units'][0]
                d.change(3015,[slot*1168+0x8c],3,'Simulate dead lord')
                b.remove(393,397)
                self.assertFalse(any(d.section(3015)['decoded'][slot*1168:(slot+1)*1168]))
                self.assertFalse(np.any(d.grid(3010)==slot))

    def test_catalog_roundtrip_both_sizes(self):
        for size in (400,500):
            d=TemplateLibrary().create(size); service=BuildingService(d)
            for n,(key,p) in enumerate(catalog().items()):
                x=330+(n%6)*22; y=330+(n//6)*24
                result=service.place(key,x,y,(n%8)+1)
                self.assertEqual(result['cells'],len(p['cells']))
                for kind,slots in result['records'].items():
                    if kind=='gates': continue
                    rows={r['slot']:r for r in EntityService(d).records(kind)}
                    self.assertTrue(all(rows[s]['coordinates_match'] for s in slots),key)
                if key=='castle':
                    owner=result['owner']; links=next(p for p in player_links(d) if p['player']==owner)
                    self.assertTrue(all(v['coordinate_match'] for v in links['links'].values()))
                    self.assertEqual(len(result['records']['buildings']),9)
                    self.assertEqual(len(result['records']['units']),1)
                if key=='apple_orchard': self.assertEqual(len(result['records']['vegetation']),8)
                if key=='quarry': self.assertEqual(len(result['records']['buildings']),2)
            report=MapValidator.validate(d)
            self.assertEqual(report['errors'],[])
            data=MapWriter.serialize(d); reopened=MapDocument(data)
            for sid,expected in d.replacements().items():
                self.assertEqual(reopened.section(sid)['decoded'],expected)
            self.assertEqual(reopened.container.menu_metadata()['players_count'],1)
            if size==400: self.assertEqual(sum(r['present'] for r in reopened.container.menu_metadata()['start_markers']),1)
            for s in d.container.sections:
                if s['id'] not in d.replacements(): self.assertEqual(s['raw'],reopened.container.section(s['id'])['raw'])

    def test_remove_groups_reopen_and_undo(self):
        for key in ('castle','quarry','apple_orchard','wheat_farm','small_gate_bridge','large_gate_bridge','granary'):
            d=TemplateLibrary().create(400); b=BuildingService(d)
            before=d.edit_digest(); b.place(key,390,390,3); placed=d.edit_digest()
            d.history.undo(); self.assertEqual(d.edit_digest(),before)
            d.history.redo(); self.assertEqual(d.edit_digest(),placed)
            # Resolve helper clicks from a fresh map, with no editor-only object metadata.
            d=MapDocument(MapWriter.serialize(d)); b=BuildingService(d)
            click={'castle':(400,392),'quarry':(397,392),'apple_orchard':(395,395),
                   'small_gate_bridge':(390,397),'large_gate_bridge':(399,392)}.get(key,(390,390))
            before=d.edit_digest(); self.assertGreater(b.remove(*click)['removed'],0)
            self.assertFalse(EntityService(d).records('buildings'),key)
            self.assertFalse(EntityService(d).records('vegetation'),key)
            self.assertFalse(EntityService(d).records('units'),key)
            self.assertFalse(np.any(d.grid(3012)),key)
            self.assertEqual(MapValidator.validate(d)['errors'],[])
            self.assertFalse(EntityService(MapDocument(MapWriter.serialize(d))).records('buildings'))
            d.history.undo(); self.assertEqual(d.edit_digest(),before)

    def test_refuse_collision_boundary_worker_and_atomic_recipe(self):
        d=TemplateLibrary().create(400); b=BuildingService(d)
        b.place('hovel',390,390); before=d.edit_digest()
        with self.assertRaises(ValueError): b.place('hovel',392,392)
        with self.assertRaises(ValueError): b.place('castle',1,1)
        with self.assertRaises(ValueError): b.place('hovel',400,400,9)
        self.assertEqual(before,d.edit_digest())
        with self.assertRaises(ValueError):
            apply_recipe(d,{'version':1,'operations':[
                {'op':'place_building','building':'quarry','x':410,'y':410},
                {'op':'place_building','building':'hovel','x':410,'y':410}]})
        self.assertEqual(before,d.edit_digest())
        row=EntityService(d).records('buildings')[0]
        at=row['slot']*812+0x19a; d.change(4013,[at],1,'Simulate worker')
        before=d.edit_digest()
        with self.assertRaisesRegex(ValueError,'workers'): b.remove(390,390)
        self.assertEqual(before,d.edit_digest())

    def test_gate_manager_links_and_castle_player_links(self):
        d=TemplateLibrary().create(400); b=BuildingService(d)
        for n,key in enumerate(('small_gate','large_gate','small_gate_bridge','large_gate_bridge')):
            result=b.place(key,350+n*20,390,4)
            self.assertEqual(len(result['records']['gates']),1)
            slot=result['records']['gates'][0]; gate=d.section(1031)['decoded'][slot*516:(slot+1)*516]
            record=d.section(4013)['decoded'][I(gate,12)*812:(I(gate,12)+1)*812]
            self.assertEqual(H(record,0x2d2),slot)
            self.assertEqual(I(gate,0x14),I(record,0xd8))
            self.assertEqual(I(gate,0x18),4)
        b.place('castle',390,430,8)
        with self.assertRaisesRegex(ValueError,'already'): b.place('castle',410,410,8)
        table=d.section(2022)['decoded']; off=8*0x583c
        self.assertEqual(struct.unpack_from('<2I',table,off+0x1d8),(393,438))
        self.assertEqual(I(table,off+0x21f8),H(d.section(1190)['decoded'],16))

if __name__=='__main__': unittest.main()
