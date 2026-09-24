"""Native Qt integration tests; preferences and generated files are isolated."""
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QPointF, QPoint, QEvent
from PySide6.QtGui import QWheelEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu
from editor import TemplateLibrary, Pattern, PatternLibrary
from editor.version import __version__
from editor.gui import EditorWindow, STYLE
from editor.settings import EditorSettings


class RefactorTests(unittest.TestCase):
    def test_version_in_title_and_help_about(self):
        w=self.window
        self.assertEqual(__version__,'0.2.0')
        self.assertIn(__version__,w.windowTitle())
        help_menu=next(menu for menu in w.menuBar().findChildren(QMenu)
                       if menu.title()=='Help')
        about=next(action for action in help_menu.actions() if action.text().startswith('About'))
        with patch('editor.gui.QMessageBox.information') as information:
            about.trigger()
        self.assertIn(f'Version {__version__}',information.call_args.args[2])

    def test_mask_filter_invert_and_tag_edit(self):
        w=self.window;p=w.brush_panel
        a=w.pattern_library.save(Pattern('A',((1,0),(1,1)),('letters',)))
        w.pattern_library.save(Pattern('Stone',((1,0),),('resources',)))
        w.pattern_library.save(Pattern('Old',((1,),)))
        w.set_mask(str(a));w.reload_patterns()
        p.tag_filter.setCurrentIndex(p.tag_filter.findData('letters'))
        visible=lambda:[p.gallery.item(i).text() for i in range(p.gallery.count()) if not p.gallery.item(i).isHidden()]
        self.assertEqual(visible(),['A'])
        p.invert.setChecked(True)
        self.assertEqual(w.canvas.pattern.cells,((0,1),(0,0)))
        self.assertEqual(PatternLibrary.load(a).cells,((1,0),(1,1)))
        with patch('editor.gui.QInputDialog.getText',return_value=('letters, symbols',True)):
            w.edit_mask_tags()
        self.assertEqual(PatternLibrary.load(a).tags,('letters','symbols'))
        self.assertNotEqual(p.tag_filter.findData('symbols'),-1)
        p.tag_filter.setCurrentIndex(p.tag_filter.findData('__untagged__'))
        self.assertEqual(visible(),['Old'])
        p.tag_filter.setCurrentIndex(p.tag_filter.findData(''))
        self.assertEqual(len(visible()),189)
        w.save_preferences()
        self.assertTrue(EditorSettings(w.settings.path).values['mask_invert'])

    def test_contextual_tool_groups_and_vegetation_location(self):
        w=self.window
        groups={'Height':w.height_group,'Variation':w.variation_group,
                'Vegetation':w.vegetation_group,'Paint':w.terrain_options_group,
                'Build':w.build_owner}
        for tool in ('Paint','Height','Variation','Vegetation','Build','Remove','Select','Inspect','Pan'):
            w.set_tool(tool)
            for owner,group in groups.items():
                self.assertEqual(not group.isHidden(),tool==owner,(tool,owner))
            brush=tool in ('Paint','Height','Variation','Vegetation')
            self.assertEqual(not w.brush_panel.isHidden(),brush)
            self.assertTrue(not w.symmetry_group.isHidden())
            self.assertEqual(w.symmetry_group.isEnabled(),brush)
        self.assertIs(w.height_group.parentWidget(),w.canvas)
        self.assertIs(w.variation_group.parentWidget(),w.canvas)
        self.assertIs(w.brush_overlay.parentWidget(),w.canvas)
        self.assertIs(w.vegetation_group.parentWidget(),w.brush_panel.parentWidget())
        self.assertIsNot(w.vegetation_group.parentWidget(),w.view_panel.parentWidget())
        w.set_tool('Height');w.height_control.spin.setValue(64)
        w.set_tool('Variation');w.variation_control.spin.setValue(987)
        w.set_tool('Vegetation');w.tree_choices.buttons['3'].click()
        self.assertEqual(w.tree_kind,'3')
        w.set_tool('Height');self.assertEqual(w.height_control.spin.value(),64)
        w.set_tool('Variation');self.assertEqual(w.variation_control.spin.value(),987)

    def test_variation_tool_and_uniform_resource_stamp(self):
        w=self.window
        w.tool_panel.choices.buttons['Variation'].click()
        self.assertEqual(w.state.tool,'Variation')
        self.assertEqual(w.canvas.layer,'noise')
        w.variation_control.spin.setValue(1234)
        path=w.pattern_library.save(Pattern('Variation mask',((1,0),(1,1))))
        w.set_mask(str(path))
        self.assertEqual(w.state.tool,'Variation')
        ids=w.canvas.pattern.indices(w.document.geometry,400,400)
        w.paint(ids)
        self.assertTrue(np.all(w.document.grid(3008)[ids]==1234))
        w.set_tool('Paint')
        w.palette.choices.buttons['iron'].click()
        w.uniform_variation.setChecked(True)
        w.variation_control.spin.setValue(0)
        before=w.document.edit_digest()
        w.paint(ids)
        self.assertTrue(np.all(w.document.grid(3008)[ids]==0))
        self.assertTrue(np.all(w.document.grid(3003)[ids]==0x88000))
        w.document.history.undo()
        self.assertEqual(w.document.edit_digest(),before)
        w.document.history.undo()

    def test_png_import_selects_mask_and_noise_view_is_read_only(self):
        from PIL import Image
        w=self.window
        path=self.path/'image.png'
        Image.new('L',(3,2),255).save(path)
        with patch('editor.gui.QFileDialog.getOpenFileName',return_value=(str(path),'')), patch('editor.gui.MaskEditor.exec',lambda dialog: (dialog.save(),dialog.result())[1]):
            w.import_mask()
        self.assertEqual(w.state.brush_shape,'mask')
        self.assertEqual(Path(w.state.mask_path).parent,w.pattern_library.directory)
        self.assertEqual(PatternLibrary.load(w.state.mask_path).cells,((1,1,1),(1,1,1)))
        before=w.document.edit_digest()
        w.tool_panel.choices.buttons['Variation'].click()
        self.assertEqual(w.canvas.layer,'noise')
        self.assertEqual(w.settings.values['view_layer'],'noise')
        self.assertFalse(w.view_panel.noise_legend.isHidden())
        self.assertEqual(w.document.edit_digest(),before)

    def test_selection_clipboard_shortcuts_and_placement(self):
        from editor import TerrainService
        w=self.window;g=w.document.geometry
        TerrainService(w.document).paint(g.rectangle(370,370,3,2),'oasis')
        w.set_tool('Select');w.canvas.selection=(370,370,3,2)
        self.app.setActiveWindow(w);w.canvas.setFocus();self.app.processEvents()
        QTest.keyClick(w.canvas,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(w.map_clipboard.width,3)
        w.state.brush_size=100;w.state.symmetry_horizontal=True
        QTest.keyClick(w.canvas,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(w.canvas.paste_size,(3,2))
        point=w.canvas.mapFromScene(QPointF(410.5,410.5))
        QTest.mouseClick(w.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point)
        self.assertIsNone(w.canvas.paste_size)
        self.assertTrue(np.all(w.document.grid(3037)[g.rectangle(410,410,3,2)]==16))
        w.undo()
        self.assertTrue(np.all(w.document.grid(3037)[g.rectangle(410,410,3,2)]==0))
        w.begin_paste();QTest.keyClick(w.canvas,Qt.Key.Key_Escape)
        self.assertIsNone(w.canvas.paste_size)

    def test_castle_hover_wall_area(self):
        from PySide6.QtGui import QImage,QPainter
        from PySide6.QtCore import QRectF
        from editor.render import PLAYER_COLORS
        w=self.window;c=w.canvas
        for size,radius in ((400,70),(500,80)):
            w.set_document(TemplateLibrary().create(size));w.set_tool('Build')
            c.building_key='castle';c.hover_cell=(390,390)
            w.set_building_owner(2);w.view_panel.players.setChecked(True);w.view_panel.opacity.setValue(30)
            def draw():
                image=QImage(800,800,QImage.Format.Format_ARGB32);image.fill(0)
                painter=QPainter(image);c.drawForeground(painter,QRectF(0,0,800,800));painter.end()
                return c.preview_image
            before=w.document.edit_digest();preview=draw()
            self.assertEqual(preview.pixelColor(393,397).getRgb(),(*PLAYER_COLORS[1],76))
            self.assertEqual(preview.pixelColor(393+radius,397).alpha(),76)
            self.assertEqual(preview.pixelColor(393+radius+1,397).alpha(),0)
            w.view_panel.players.setChecked(False)
            self.assertEqual(draw().pixelColor(393,397).alpha(),0)
            self.assertEqual(w.document.edit_digest(),before)

    def test_corner_controls_stay_fixed_during_pan_and_zoom(self):
        w=self.window;c=w.canvas
        w.set_tool('Height');self.app.processEvents()
        controls=(w.brush_overlay,w.height_group)
        before=[control.pos() for control in controls]
        c.scale(3,3)
        c.horizontalScrollBar().setValue(c.horizontalScrollBar().value()+120)
        c.verticalScrollBar().setValue(c.verticalScrollBar().value()+80)
        self.app.processEvents()
        self.assertEqual([control.pos() for control in controls],before)
        c.scale(.5,.5)
        c.horizontalScrollBar().setValue(c.horizontalScrollBar().value()-60)
        c.verticalScrollBar().setValue(c.verticalScrollBar().value()-40)
        self.app.processEvents()
        self.assertEqual([control.pos() for control in controls],before)

    def test_window_close_cancel_protects_committed_and_pending_changes(self):
        from PySide6.QtWidgets import QMessageBox
        from editor import TerrainService
        w=self.window
        for pending in (True,False):
            if pending:w.canvas.pending[w.document.geometry.index(400,400)]=True
            else:TerrainService(w.document).paint(w.document.geometry.brush(400,400,2),'oasis')
            with patch('editor.gui.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel) as warning:
                self.assertFalse(w.close());warning.assert_called_once()
                self.assertTrue(w.isVisible())
            w.canvas.pending.fill(False)

    def test_recent_isolation_clear_button_and_discard_without_export(self):
        from PySide6.QtWidgets import QDialog,QPushButton,QMessageBox
        from PySide6.QtGui import QCloseEvent
        from editor import TerrainService
        from editor.recent import RecentFiles
        w=self.window
        self.assertEqual(w.recent_files.path,self.path/'recent-files.json')
        self.assertEqual(w.pattern_library.directory,self.path/'Patterns')
        saved=self.path/'keep.map';saved.write_bytes(b'map must not be deleted')
        w.remember_file(saved)
        def interact(dialog):
            clear=next(b for b in dialog.findChildren(QPushButton) if b.text()=='Clear list')
            clear.click()
            self.assertFalse(clear.isEnabled())
            self.assertEqual(RecentFiles(w.recent_files.path).files,[])
            return QDialog.DialogCode.Rejected
        with patch.object(QDialog,'exec',interact):w.open_recent()
        self.assertEqual(saved.read_bytes(),b'map must not be deleted')
        recent_before=w.recent_files.path.read_bytes()
        TerrainService(w.document).paint(w.document.geometry.brush(400,400,2),'oasis')
        with patch('editor.gui.QMessageBox.question',return_value=QMessageBox.StandardButton.Discard), \
             patch('editor.gui.MapWriter.save_as') as save, \
             patch('editor.gui.MapWriter.serialize') as serialize, \
             patch.object(w,'remember_file') as remember:
            event=QCloseEvent();w.closeEvent(event)
            self.assertTrue(event.isAccepted())
            save.assert_not_called();serialize.assert_not_called();remember.assert_not_called()
        self.assertEqual(w.recent_files.path.read_bytes(),recent_before)

    def test_low_height_warning_is_independent_and_allows_zero(self):
        w=self.window
        w.height_control.minus.click()
        self.assertEqual(w.state.height,7)
        warning=w.height_warning
        self.assertEqual(warning.windowTitle(),'Low terrain height')
        self.assertIn('#ff6262',w.height_control.spin.styleSheet())
        warning.accept()
        w.height_control.spin.setValue(0)
        self.assertEqual(w.state.height,0)
        self.assertIsNone(w.height_warning)
        w.height_control.spin.setValue(8)
        self.assertEqual(w.height_control.spin.styleSheet(),'')
        w.height_control.slider.setValue(7)
        w.height_warning.checkBox().setChecked(True)
        w.height_warning.accept()
        settings=EditorSettings(w.settings.path)
        self.assertTrue(settings.values['hide_low_height_warning'])
        self.assertFalse(settings.values['hide_high_height_warning'])
        w.height_control.spin.setValue(8);w.height_control.spin.setValue(0)
        self.assertIsNone(w.height_warning)
        w.height_control.spin.setValue(131)
        self.assertEqual(w.height_warning.windowTitle(),'High terrain height')
        w.height_warning.accept()

    def test_high_height_warning_threshold_suppression_and_default(self):
        from editor.state import EditorState
        w=self.window
        self.assertEqual(w.height_control.spin.value(),8)
        w.height_control.spin.setValue(130)
        self.assertIsNone(w.height_warning)
        self.assertEqual(w.height_control.spin.styleSheet(),'')
        w.height_control.plus.click()
        warning=w.height_warning
        self.assertIsNotNone(warning)
        self.assertEqual(w.state.height,131)
        self.assertIn('#ff6262',w.height_control.spin.styleSheet())
        self.assertIn('#ff6262',w.height_control.slider.styleSheet())
        warning.accept()
        w.height_control.spin.setValue(200)
        self.assertIsNone(w.height_warning)
        w.height_control.spin.setValue(130)
        self.assertEqual(w.height_control.spin.styleSheet(),'')
        w.height_control.slider.setValue(255)
        w.height_warning.checkBox().setChecked(True)
        w.height_warning.accept()
        loaded=EditorSettings(w.settings.path)
        self.assertTrue(loaded.values['hide_high_height_warning'])
        self.assertEqual(EditorState.restore(dict(loaded.values,height=255)).height,8)
        w.height_control.spin.setValue(8);w.height_control.spin.setValue(255)
        self.assertIsNone(w.height_warning)
        self.assertEqual(w.state.height,255)
        self.assertIn('#ff6262',w.height_control.spin.styleSheet())

    def test_thin_tree_lines_mirror_at_all_grid_offsets(self):
        from editor import EntityService
        from editor.trees import TreeService
        w=self.window
        self.assertEqual(w.brush_panel.gallery.height(),200)
        w.choose_tree('2')
        for size in (400,500):
            w.set_document(TemplateLibrary().create(size))
            d=w.document;g=d.geometry
            for h,v in ((True,False),(False,True),(True,True)):
                w.symmetry_horizontal.setChecked(h);w.symmetry_vertical.setChecked(v)
                for offset in range(4):
                    for start,end in (((361,365+offset),(385,365+offset)),
                                      ((365+offset,361),(365+offset,385)),
                                      ((361,365+offset),(381,385+offset))):
                        ids=g.stroke_brush(start,end,1)
                        anchors=TreeService(d).anchors(ids)
                        self.assertGreater(len(anchors),1)
                        expected=g.symmetric_indices(anchors,h,v)
                        w.paint(ids)
                        positions={(r['x'],r['y']) for r in EntityService(d).records('vegetation')}
                        self.assertEqual(positions,set(zip(g.x[expected],g.y[expected])))
                        w.undo()
                        self.assertFalse(EntityService(d).records('vegetation'))

    def test_symmetry_brushes_history_and_preferences(self):
        from editor import EntityService
        from editor.state import EditorState
        w=self.window; d=w.document; g=d.geometry
        self.assertFalse(w.symmetry_horizontal.isChecked())
        self.assertFalse(w.symmetry_vertical.isChecked())
        w.symmetry_horizontal.setChecked(True);w.symmetry_vertical.setChecked(True)
        ids=g.brush(370,370,2)
        mirrored=w.canvas.symmetric_ids(ids)
        self.assertEqual(len(mirrored),16)
        before=d.edit_digest(); w.paint(ids)
        self.assertTrue(np.all(d.grid(3037)[mirrored]==16))
        self.assertEqual(len(d.history.commands),1)
        w.undo();self.assertEqual(d.edit_digest(),before)
        w.set_height(40);w.paint(ids)
        self.assertTrue(np.all(d.grid(3045)[mirrored]==40)); w.undo()
        w.choose_tree('2'); w.paint(g.brush(370,370,1))
        positions={(r['x'],r['y']) for r in EntityService(d).records('vegetation')}
        reflected=g.symmetric_indices(g.brush(370,370,1),True,True)
        self.assertEqual(positions,set(zip(g.x[reflected],g.y[reflected])))
        self.assertEqual(len(positions),4); w.undo()
        w.choose_tree('2');w.paint(g.brush(370,370,13))
        positions={(r['x'],r['y']) for r in EntityService(d).records('vegetation')}
        x0,y0,x1,y1=g.bounds
        self.assertTrue(positions)
        self.assertEqual(positions,{(x0+x1-1-x,y0+y1-1-y) for x,y in positions})
        w.undo()
        # A centerline stroke must not plant just one of two overlapping trees.
        w.paint(g.brush((x0+x1-1)//2,370,1))
        self.assertFalse(EntityService(d).records('vegetation'))
        w.save_preferences()
        state=EditorState.restore(EditorSettings(w.settings.path).values)
        self.assertTrue(state.symmetry_horizontal and state.symmetry_vertical)
        w.canvas.selection=(350,350,40,40);w.canvas.clip_selection=True
        clipped=w.canvas.symmetric_ids(g.brush(370,370,1))
        self.assertEqual(len(clipped),1)

    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        cls.app.setStyle('Fusion')
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)
        self.window=EditorWindow(startup=False,settings_path=self.path/'settings.json')
        self.window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.window.pattern_library=PatternLibrary(self.path/'Patterns')
        self.window.reload_patterns()
        self.window.show()
        self.window.set_document(TemplateLibrary().create(400))
        self.app.processEvents()

    def tearDown(self):
        self.window.document.saved_digest=self.window.document.edit_digest()
        self.window.close()
        self.folder.cleanup()

    def test_controls_sizes_masks_and_settings(self):
        w=self.window
        p=w.brush_panel
        p.size.setValue(1)
        self.assertFalse(p.minus.isEnabled())
        p.plus.click()
        self.assertEqual(w.state.brush_size,2)
        p.minus.click()
        self.assertEqual(w.state.brush_size,1)
        p.size.lineEdit().selectAll()
        QTest.keyClicks(p.size.lineEdit(),'250')
        QTest.keyClick(p.size.lineEdit(),Qt.Key.Key_Return)
        self.assertEqual(w.canvas.brush_size,250)
        self.assertEqual(p.slider.value(),250)
        p.size.lineEdit().selectAll()
        QTest.keyClicks(p.size.lineEdit(),'999')
        QTest.keyClick(p.size.lineEdit(),Qt.Key.Key_Return)
        self.assertEqual(w.state.brush_size,250)
        w.set_document(TemplateLibrary().create(500))
        w.set_size(500)
        self.assertEqual(p.size.value(),500)
        w.set_document(TemplateLibrary().create(400))
        self.assertEqual(w.state.brush_size,400)
        w.set_tool('Select')
        w.palette.choices.buttons['sand'].click()
        self.assertEqual((w.state.tool,w.state.material),('Select','sand'))
        w.palette.choices.buttons['iron'].click()
        self.assertEqual(w.state.material,'iron')
        w.palette.choices.buttons['stone'].click()
        self.assertEqual(w.state.material,'stone')
        path=w.pattern_library.save(Pattern('L',((1,0),(1,1))))
        w.reload_patterns()
        p.gallery.setCurrentRow(0)
        self.assertEqual(w.state.brush_shape,'mask')
        self.assertFalse(p.size_row.isEnabled())
        w.rotate_mask(90)
        self.assertEqual(w.canvas.pattern.cells,((1,1),(1,0)))
        w.save_preferences()
        prefs=EditorSettings(self.path/'settings.json').values
        self.assertEqual(prefs['rotation'],90)
        self.assertEqual(prefs['mask_path'],str(path))
        path.unlink()
        w.apply_state()
        self.assertEqual(w.state.brush_shape,'square')
        self.assertFalse(w.document.dirty)

    def test_selection_clipping_cancel_and_pan(self):
        w=self.window
        w.canvas.selection=(397,397,5,5)
        w.update_selection()
        w.clip_selection.setChecked(True)
        w.set_size(400)
        ids=w.canvas.ids_at(400,400)
        self.assertEqual(len(ids),25)
        w.paint(ids)
        self.assertEqual(w.document.history.cursor,1)
        w.undo()
        self.assertFalse(w.document.dirty)
        w.set_size(5)
        point=w.canvas.mapFromScene(QPointF(400.5,400.5))
        QTest.mousePress(w.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        self.assertTrue(w.canvas.pending.any())
        w.clear_selection()
        QTest.mouseRelease(w.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        self.assertFalse(w.document.dirty)
        self.assertFalse(w.canvas.pending.any())
        self.assertFalse(w.fill_button.isEnabled())

    def test_settings_reset_after_view_button_removal(self):
        from PySide6.QtWidgets import QDialog,QPushButton
        w=self.window
        w.set_tool('Height')
        w.view_panel.grid.setChecked(False)
        def reset(dialog):
            next(button for button in dialog.findChildren(QPushButton)
                 if button.text()=='Reset UI settings').click()
            return dialog.result()
        with patch.object(QDialog,'exec',reset):
            w.show_settings()
        self.assertEqual(w.state.tool,'Paint')
        self.assertEqual(w.canvas.layer,'surface')
        self.assertTrue(w.view_panel.grid.isChecked())

    def test_action_reference_and_tool_buttons(self):
        w=self.window
        for tool in ('Inspect','Select','Pan','Paint'):
            w.tool_panel.choices.buttons[tool].click()
            self.assertEqual(w.state.tool,tool)
            self.assertEqual(w.canvas.tool,tool)
        w.show_hotkeys()
        first=w.hotkeys_window
        w.show_hotkeys()
        self.assertIs(w.hotkeys_window,first)
        self.assertFalse(first.isModal())
        self.assertTrue(first.isVisible())
        from PySide6.QtWidgets import QTreeWidget
        tree=first.findChild(QTreeWidget)
        labels=[tree.topLevelItem(i).child(j).text(0)
                for i in range(tree.topLevelItemCount())
                for j in range(tree.topLevelItem(i).childCount())]
        for label in ('Copy selection','Paste selection',
                      'Place copied cells after Ctrl+V','Draw a selection with Select'):
            self.assertIn(label,labels)
        for name,key in [('Paint','B'),('Select','M'),('Inspect','I'),('Pan','H')]:
            self.assertEqual(w.tool_actions[name].shortcut().toString(),key)
            self.assertIn(key,w.tool_actions[name].toolTip())
        first.close()
        self.assertTrue(w.isVisible())
        w.activateWindow()
        w.canvas.setFocus()
        self.app.processEvents()
        QTest.keyClick(w.canvas,Qt.Key.Key_M)
        self.assertEqual(w.state.tool,'Select')
        w.brush_panel.size.setFocus()
        self.app.processEvents()
        QTest.keyClick(w.brush_panel.size,Qt.Key.Key_B)
        self.assertEqual(w.state.tool,'Select')
        w.canvas.setFocus()
        self.app.processEvents()
        QTest.keyClick(w.canvas,Qt.Key.Key_B)
        self.assertEqual(w.state.tool,'Paint')

    def test_batched_brush_matches_discrete_sweep(self):
        g=self.window.document.geometry
        for shape in ('square','circle'):
            for size in (1,2,5,101,400):
                for a,b in [((390,390),(405,397)),((405,397),(390,390)),((400,400),(400,400)),((400,210),(382,225))]:
                    steps=max(abs(b[0]-a[0]),abs(b[1]-a[1]),1)
                    ids=np.unique(np.concatenate([g.brush(round(a[0]+(b[0]-a[0])*t/steps),round(a[1]+(b[1]-a[1])*t/steps),size,shape) for t in range(steps+1)]))
                    np.testing.assert_array_equal(g.stroke_brush(a,b,size,shape),ids)

    def test_build_remove_and_palette(self):
        from editor import EntityService
        w=self.window
        item=next(w.building_list.item(i) for i in range(w.building_list.count())
                  if w.building_list.item(i).data(Qt.ItemDataRole.UserRole)=='quarry')
        w.choose_building(item)
        for owner in range(1,9):
            w.build_owner.buttons[owner].click()
            self.assertEqual(w.canvas.building_owner,owner)
            self.assertEqual(sum(b.isChecked() for b in w.build_owner.buttons.values()),1)
        w.build_owner.buttons[6].click()
        w.canvas.scale(5,5)
        w.canvas.centerOn(400,400)
        self.app.processEvents()
        pos=w.canvas.mapFromScene(QPointF(400.5,400.5))
        QTest.mouseClick(w.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        rows=EntityService(w.document).records('buildings')
        self.assertEqual({r['type'] for r in rows},{20,21})
        self.assertEqual({r['owner'] for r in rows},{6})
        w.tool_panel.choices.buttons['Remove'].click()
        QTest.mouseClick(w.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        self.assertFalse(EntityService(w.document).records('buildings'))
        w.undo()
        self.assertEqual(len(EntityService(w.document).records('buildings')),2)

    def test_cancel_and_cursor_zoom(self):
        w=self.window; c=w.canvas
        c.scale(3,3); c.centerOn(400,400)
        self.app.processEvents()
        pos=QPoint(c.viewport().width()//3,c.viewport().height()//3)
        for tool in ('Build','Remove','Paint','Select','Pan'):
            w.set_tool(tool)
            before=w.document.edit_digest()
            scroll=(c.horizontalScrollBar().value(),c.verticalScrollBar().value())
            QTest.mousePress(c.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,pos)
            QTest.mouseMove(c.viewport(),pos+QPoint(40,30))
            QTest.mouseRelease(c.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,pos+QPoint(40,30))
            self.assertEqual(w.state.tool,'Inspect')
            self.assertFalse(c.panning)
            self.assertEqual(scroll,(c.horizontalScrollBar().value(),c.verticalScrollBar().value()))
            QTest.mouseClick(c.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
            self.assertEqual(before,w.document.edit_digest())
        w.set_tool('Paint')
        QTest.mousePress(c.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        QTest.mouseClick(c.viewport(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,pos)
        QTest.mouseRelease(c.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        self.assertFalse(w.document.dirty)
        for amount in (120,120,-120,-120,-120,60,0,12000,12000,-12000,-12000,-12000,120):
            anchor=c.mapToScene(pos)
            event=QWheelEvent(QPointF(pos),QPointF(c.viewport().mapToGlobal(pos)),QPoint(),QPoint(0,amount),
                              Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
            QApplication.sendEvent(c.viewport(),event)
            self.app.processEvents()
            projected=c.mapFromScene(anchor)
            self.assertLessEqual(abs(projected.x()-pos.x()),1)
            self.assertLessEqual(abs(projected.y()-pos.y()),1)

    def test_save_as_preserves_dotted_names(self):
        from editor import MapReader
        w=self.window
        def run_now(message,function,done): done(function())
        for name,expected in [('3v3 Einstein v1.1','3v3 Einstein v1.1.map'),
                              ('another.v2.3.map','another.v2.3.map'),
                              ('CAPS.v1.MAP','CAPS.v1.MAP'),('plain','plain.map')]:
            path=self.path/name
            with patch('editor.gui.QFileDialog.getSaveFileName',return_value=(str(path),'Map (*.map)')), patch.object(w,'run_job',side_effect=run_now):
                w.save_as()
            saved=self.path/expected
            self.assertTrue(saved.is_file())
            from editor.preview import encode_preview
            reopened=MapReader.open(saved)
            self.assertEqual(reopened.container.preview,encode_preview(w.document))
            for section in w.document.container.sections:
                self.assertEqual(reopened.section(section['id'])['raw'],section['raw'])
            self.assertEqual(MapReader.open(saved).size,400)
            self.assertEqual(w.document.saved_path,saved.resolve())
        # Confirmation is applied after appending .map; Cancel preserves the file.
        from PySide6.QtWidgets import QMessageBox
        target=self.path/'3v3 Einstein v1.1.map'
        before=target.read_bytes()
        with patch('editor.gui.QFileDialog.getSaveFileName',return_value=(str(target.with_suffix('')),'')), \
             patch('editor.gui.QMessageBox.warning',return_value=QMessageBox.StandardButton.Cancel), \
             patch.object(w,'run_job') as job:
            w.save_as()
            job.assert_not_called()
        self.assertEqual(target.read_bytes(),before)

    def test_save_current_and_remember_dialog_folder(self):
        from PySide6.QtWidgets import QMessageBox
        from editor import MapReader,MapWriter,TerrainService
        w=self.window
        folder=self.path/'maps';folder.mkdir()
        target=folder/'current.map'
        MapWriter.save_as(w.document,target)
        w.set_document(MapReader.open(target))
        w.remember_file(target)
        self.assertEqual(EditorSettings(w.settings.path).values['last_map_directory'],str(folder.resolve()))
        with patch('editor.gui.QFileDialog.getOpenFileName',return_value=('','')) as dialog:
            w.open_map()
            self.assertEqual(dialog.call_args.args[2],str(folder.resolve()))
        with patch('editor.gui.QFileDialog.getSaveFileName',return_value=('','')) as dialog:
            w.save_as()
            self.assertEqual(Path(dialog.call_args.args[2]),target)
        TerrainService(w.document).paint(w.document.geometry.brush(400,400,2),'sand')
        def run_now(message,function,done): done(function())
        with patch('editor.gui.QMessageBox.warning',return_value=QMessageBox.StandardButton.Save) as warning, \
             patch('editor.gui.QFileDialog.getSaveFileName') as dialog, \
             patch.object(w,'run_job',side_effect=run_now):
            w.save_map()
            warning.assert_called_once();dialog.assert_not_called()
        self.assertFalse(w.document.dirty)
        self.assertEqual(list(folder.iterdir()),[target])
        self.assertEqual(MapReader.open(target).grid(3037)[w.document.geometry.index(400,400)],64)

    def test_height_sliders_and_ctrl_stroke(self):
        w=self.window; c=w.canvas
        w.view_panel.set_layer('height')
        self.assertEqual(w.state.tool,'Height')
        w.set_tool('Paint')
        self.assertEqual(c.layer,'surface')
        w.view_panel.opacity_control.slider.setValue(42)
        self.assertEqual(w.view_panel.opacity.value(),42)
        self.assertEqual(c.area_opacity,42)
        w.view_panel.opacity.setValue(17)
        self.assertEqual(w.view_panel.opacity_control.slider.value(),17)
        w.height_control.slider.setValue(255)
        self.assertEqual(w.state.tool,'Height')
        self.assertEqual(w.state.height,255)
        self.assertEqual(w.height_control.spin.value(),255)
        self.assertFalse(w.height_control.plus.isEnabled())
        if w.height_warning is not None: w.height_warning.accept()
        w.set_shape('square'); w.set_size(1); w.set_tool('Height')
        self.assertEqual(c.layer,'height')
        self.assertFalse(w.view_panel.height_legend.isHidden())
        c.scale(5,5); c.centerOn(410,410); self.app.processEvents()
        def stroke(start,points):
            p=c.mapFromScene(QPointF(start[0]+.5,start[1]+.5))
            QTest.mousePress(c.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier,p)
            for x,y in points:
                p=c.mapFromScene(QPointF(x+.5,y+.5))
                event=QMouseEvent(QEvent.Type.MouseMove,QPointF(p),QPointF(c.viewport().mapToGlobal(p)),
                    Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier)
                QApplication.sendEvent(c.viewport(),event)
            QTest.mouseRelease(c.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier,p)
        stroke((400,400),[(420,408),(408,422)])
        g=w.document.geometry
        changed=np.flatnonzero(w.document.grid(3005)==255)
        self.assertEqual(set(g.y[changed]),{400})
        self.assertEqual((g.x[changed].min(),g.x[changed].max()),(400,420))
        self.assertEqual(w.document.history.cursor,1)
        w.undo(); self.assertFalse(w.document.dirty)
        w.set_tool('Paint'); w.set_material('sand')
        stroke((400,400),[(405,420),(423,411)])
        painted=np.flatnonzero(w.document.grid(3037)==64)
        self.assertEqual(set(g.x[painted]),{400})
        self.assertEqual((g.y[painted].min(),g.y[painted].max()),(400,420))


if __name__=='__main__':
    unittest.main()
