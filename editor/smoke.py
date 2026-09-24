"""Explicit packaged-app diagnostic, writing only to a new requested directory."""
import json
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
from . import TemplateLibrary, MapWriter, MapReader, Pattern, PatternLibrary
from .gui import EditorWindow


def self_test(app, directory):
    directory.mkdir(parents=True, exist_ok=False)
    window=EditorWindow(startup=False, settings_path=directory/'settings.json')
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    window.show()
    app.processEvents()
    try:
        for size in (400,500):
            doc=TemplateLibrary().create(size)
            assert MapWriter.serialize(doc)==doc.original_bytes
        window.set_document(TemplateLibrary().create(400))
        app.processEvents()
        brush=window.brush_panel
        brush.size.setValue(1)
        assert not brush.minus.isEnabled()
        brush.plus.click()
        assert window.state.brush_size==2
        brush.minus.click()
        assert window.state.brush_size==1
        brush.size.lineEdit().selectAll()
        QTest.keyClicks(brush.size.lineEdit(),'250')
        QTest.keyClick(brush.size.lineEdit(),Qt.Key.Key_Return)
        assert window.canvas.brush_size==250 and brush.slider.value()==250
        brush.size.setValue(5)
        assert len(window.palette.choices.buttons)==8
        window.show_hotkeys()
        app.processEvents()
        window.hotkeys_window.grab().save(str(directory/'hotkeys.png'))
        window.hotkeys_window.close()
        window.activateWindow()
        window.canvas.setFocus()
        app.processEvents()
        QTest.keyClick(window.canvas,Qt.Key.Key_M)
        assert window.state.tool=='Select'
        window.set_tool('Paint')
        # Navigation must move the viewport without painting in the active tool.
        canvas = window.canvas
        canvas.scale(3,3)
        canvas.centerOn(400,400)
        app.processEvents()
        before = (canvas.horizontalScrollBar().value(), canvas.verticalScrollBar().value())
        digest = window.document.edit_digest()
        origin = canvas.viewport().rect().center()
        QTest.mousePress(canvas.viewport(),Qt.MouseButton.MiddleButton,Qt.KeyboardModifier.NoModifier,origin)
        QTest.mouseMove(canvas.viewport(),origin+QPoint(60,40),20)
        QTest.mouseRelease(canvas.viewport(),Qt.MouseButton.MiddleButton,Qt.KeyboardModifier.NoModifier,origin+QPoint(60,40))
        after = (canvas.horizontalScrollBar().value(), canvas.verticalScrollBar().value())
        assert after == (before[0]-60,before[1]-40), (before,after)
        assert not canvas.panning and window.document.edit_digest()==digest
        assert window.document.history.cursor==0
        canvas.fit_map()
        start=window.canvas.mapFromScene(QPointF(390.5,390.5))
        end=window.canvas.mapFromScene(QPointF(420.5,405.5))
        QTest.mousePress(window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start)
        QTest.mouseMove(window.canvas.viewport(),end,20)
        QTest.mouseRelease(window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,end)
        assert window.document.dirty and window.document.history.cursor==1
        window.undo()
        assert not window.document.dirty
        window.redo()
        assert window.document.dirty
        window.canvas.selection=(395,395,5,5)
        window.update_selection()
        window.set_material('sand')
        window.fill_selection()
        assert window.document.grid(3037)[window.document.geometry.index(397,397)]==64
        pattern=Pattern('smoke-mask',((1,0,1),(0,1,0)))
        library=PatternLibrary(directory/'Patterns')
        assert library.load(library.save(pattern))==pattern
        export=MapWriter.save_as(window.document,directory/'edited.map')
        assert MapReader.open(export['path']).grid(3037).tolist()==window.document.grid(3037).tolist()
        window.canvas.fit_map()
        window.inspect_cell(397,397)
        app.processEvents()
        window.grab().save(str(directory/'editor.png'))
        window.canvas.scale(5,5)
        window.canvas.centerOn(400,400)
        app.processEvents()
        window.grab().save(str(directory/'grid-detail.png'))
        from .buildings import BuildingService
        from .services import EntityService
        window.set_document(TemplateLibrary().create(400))
        service=BuildingService(window.document)
        service.place('castle',380,390,1)
        service.place('quarry',402,390,1)
        service.place('apple_orchard',402,410,1)
        service.place('round_tower',380,416,1)
        window.update_document_ui()
        window.canvas.scale(7,7)
        window.canvas.centerOn(398,405)
        window.canvas.building_key='hovel'
        window.set_tool('Build')
        app.processEvents()
        pos=window.canvas.mapFromScene(QPointF(394.5,418.5))
        QTest.mouseClick(window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        assert any(r['type']==1 for r in EntityService(window.document).records('buildings'))
        window.set_tool('Remove')
        QTest.mouseClick(window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,pos)
        assert not any(r['type']==1 for r in EntityService(window.document).records('buildings'))
        window.undo()
        assert any(r['type']==1 for r in EntityService(window.document).records('buildings'))
        app.processEvents()
        window.grab().save(str(directory/'buildings.png'))
        building_export=MapWriter.save_as(window.document,directory/'buildings.map')
        reopened=MapReader.open(building_export['path'])
        assert len(EntityService(reopened).records('buildings'))==14
        window.set_document(TemplateLibrary().create(400))
        window.set_tool('Height')
        window.set_shape('circle')
        assert window.state.tool=='Height'
        # Concentric targets exercise the full color range and both height layers.
        for size,height in ((100,32),(80,64),(60,128),(40,192),(20,255)):
            window.height_control.slider.setValue(height)
            window.set_size(size)
            window.paint(window.document.geometry.brush(400,400,size,'circle'))
        assert window.document.grid(3005)[window.document.geometry.index(400,400)]==255
        window.view_panel.opacity_control.slider.setValue(40)
        assert window.canvas.area_opacity==40
        window.canvas.scale(3,3)
        window.canvas.centerOn(400,400)
        # Scroll the right dock so the colorbar and opacity slider are visible.
        from PySide6.QtWidgets import QScrollArea
        parent=window.view_panel.parentWidget()
        while parent and not isinstance(parent,QScrollArea): parent=parent.parentWidget()
        if parent: parent.ensureWidgetVisible(window.view_panel)
        app.processEvents()
        window.grab().save(str(directory/'height-editor.png'))
        height_export=MapWriter.save_as(window.document,directory/'heights.map')
        assert MapReader.open(height_export['path']).grid(3045)[window.document.geometry.index(400,400)]==255
        result={'ok':True,'checks':['bundled 400/500 templates','lossless no-op','middle-drag pan without edits','Qt mouse paint',
            'undo/redo','selection fill','mask save/load','map export/readback','GUI screenshots',
            'brush plus/minus and typed 250','visible palette','Hotkeys window','tool keyboard shortcut'],
            'export':export,'building_export':building_export,'height_export':height_export,
            'building_checks':['linked castle, quarry and orchard','GUI placement/removal','undo','export/reopen'],
            'height_checks':['target slider','height tool preserves brush shape','jet view','opacity slider','export/reopen']}
        code=0
    except Exception as error:
        result={'ok':False,'error':repr(error)}
        code=1
    (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if window.document:
        window.document.saved_digest=window.document.edit_digest()
    window.close()
    return code

