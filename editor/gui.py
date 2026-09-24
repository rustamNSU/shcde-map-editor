"""Qt desktop adapter. All document edits route through the shared backend."""
import math
import sys
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject, QRunnable, QThreadPool, QTimer, QEvent
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QAction, QKeySequence, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QDockWidget, QGroupBox, QFormLayout, QToolBar, QFileDialog, QMessageBox,
    QListWidget, QPlainTextEdit, QDialog, QLineEdit, QDialogButtonBox, QGridLayout,
    QInputDialog, QScrollArea, QLayout, QMenu)

from . import (MapReader, MapWriter, TemplateLibrary, TerrainService, EntityService,
               MapValidator, Pattern, PatternLibrary)
from .version import __version__
from .services import MATERIALS, HeightService, VariationService
from .render import render_rgb, PLAYER_COLORS, CASTLE_AREA_RADIUS
from .settings import EditorSettings
from .recent import RecentFiles
from .state import EditorState
from .mask_editor import MaskEditor
from .clipboard import MapClipboard
from .buildings import BuildingService, catalog
from .trees import TreeService, tree_catalog
from .panels import ToolPanel, OwnerPanel, SliderValue, BrushPanel, MaterialPalette, ViewPanel, InspectorPanel, HotkeysWindow, button

STYLE = '''
QMainWindow, QDialog { background:#171e23; color:#e0e5e7; }
QWidget#dockBody, QScrollArea { background:#171e23; }
QWidget { font-family:Segoe UI; font-size:12px; color:#dce2e4; }
QDockWidget { font-weight:600; }
QDockWidget::title { background:#253038; padding:10px; }
QToolBar { background:#202a31; border:0; padding:8px; spacing:8px; }
QToolButton, QPushButton { background:#2b363e; border:1px solid #3c4952; border-radius:5px; padding:8px 12px; }
QToolButton:hover, QPushButton:hover { background:#3b4952; }
QPushButton:checked { background:#355951; border-color:#85b5a2; }
QPushButton:disabled, QToolButton:disabled { color:#64727a; background:#242c32; }
QPushButton#primary { background:#426b5c; border:1px solid #719f89; }
QGroupBox { border:1px solid #35424b; border-radius:5px; margin-top:14px; padding:14px 8px 8px; }
QGroupBox::title { subcontrol-origin:margin; left:10px; color:#aab8c0; }
QComboBox, QSpinBox, QLineEdit { background:#192229; border:1px solid #41515b; border-radius:4px; padding:6px; }
QComboBox QAbstractItemView { background:#26323a; selection-background-color:#426b5c; }
QPlainTextEdit, QListWidget { background:#1b252c; border:1px solid #35424b; padding:5px; }
QListWidget::item:selected { background:#426b5c; }
QStatusBar { background:#202a31; color:#abbac4; }
QLabel#muted { color:#93a6b1; font-size:11px; }
QLabel#heading { font-size:17px; font-weight:600; color:#edf1ed; }
QCheckBox { padding:4px 0; }
QMenuBar { background:#202a31; }
QMenuBar::item:selected { background:#426b5c; }
QSlider::groove:horizontal { height:5px; background:#35424b; }
QSlider::handle:horizontal { background:#85b5a2; width:13px; margin:-5px 0; border-radius:3px; }
QTreeWidget { background:#1b252c; }
QHeaderView::section { background:#253038; color:#dce2e4; border:1px solid #35424b; padding:4px; }
QScrollBar:vertical { background:#202a31; width:10px; }
QScrollBar:horizontal { background:#202a31; height:10px; }
QScrollBar::handle { background:#4b5c65; min-height:20px; min-width:20px; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:#202a31; }
QMenu { background:#253038; border:1px solid #40505a; }
QMenu::item:selected { background:#426b5c; }
QToolTip { color:#eef2f4; background:#26353e; border:1px solid #61717b; }
'''


class JobSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = JobSignals()

    def run(self):
        try:
            self.signals.done.emit(self.function())
        except Exception as error:
            self.signals.failed.emit(str(error))


class MapCanvas(QGraphicsView):
    hovered = Signal(int, int)
    clicked = Signal(int, int)
    cancel_requested = Signal()
    paint_requested = Signal(object)
    selection_changed = Signal(object)
    paste_requested = Signal(int,int)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor('#151c21'))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.document = None
        self.pixmap = None
        self.tool = 'Inspect'
        self.building_key = 'castle'
        self.building_owner = 1
        self.brush_size = 5
        self.brush_shape = 'square'
        self.pattern = None
        self.paste_size = None
        self.selection = None
        self.hover_cell = None
        self.drag_origin = None
        self.drag_last = None
        self.constraint_origin = None
        self.constraint_axis = None
        self.pending = np.zeros(320800,dtype=bool)
        self.clip_selection = False
        self.preview_image = None
        self.panning = False
        self.pan_button = None
        self.show_grid = True
        self.layer = 'surface'
        self.show_objects = True
        self.show_players = True
        self.area_opacity = 25
        self.symmetry_horizontal=False
        self.symmetry_vertical=False
        self.setMinimumSize(420, 350)

    def set_document(self, document):
        self.document = document
        self.scene().clear()
        self.pixmap = None
        self.selection = self.hover_cell = None
        self.cancel_gesture()
        self.refresh()
        self.fit_map()

    def refresh(self):
        if self.document is None:
            return
        rgb = render_rgb(self.document, self.layer, self.show_objects, self.show_players, self.area_opacity)
        image = QImage(rgb.data, 800, 800, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        if self.pixmap is None:
            self.pixmap = self.scene().addPixmap(QPixmap.fromImage(image))
            # Allow cursor-anchored zoom even when the map is smaller than the viewport.
            self.scene().setSceneRect(-10000, -10000, 20800, 20800)
        else:
            self.pixmap.setPixmap(QPixmap.fromImage(image))
        self.viewport().update()

    def fit_map(self):
        if self.document:
            x0, y0, x1, y1 = self.document.geometry.bounds
            self.fitInView(QRectF(x0-12,y0-12,x1-x0+24,y1-y0+24), Qt.AspectRatioMode.KeepAspectRatio)

    def cell_at(self, point):
        p = self.mapToScene(point)
        return math.floor(p.x()), math.floor(p.y())

    def invalidate_preview(self):
        self.preview_image=None

    def cancel_gesture(self):
        self.paste_size=None
        self.pending.fill(False)
        self.drag_origin=self.drag_last=None
        self.constraint_origin=self.constraint_axis=None
        self.panning=False
        self.pan_button=None
        self.unsetCursor()
        self.invalidate_preview()
        self.viewport().update()

    def clip_ids(self, ids):
        return self.document.geometry.clip_indices(ids,self.selection if self.clip_selection else None)

    def ids_at(self, x, y):
        if self.pattern is not None:
            ids=self.pattern.indices(self.document.geometry, x-len(self.pattern.cells[0])//2,
                                        y-len(self.pattern.cells)//2)
        else:
            ids=self.document.geometry.brush(x,y,self.brush_size,self.brush_shape)
        return self.clip_ids(ids)

    def symmetric_ids(self,ids):
        return self.clip_ids(self.document.geometry.symmetric_indices(
            ids,self.symmetry_horizontal,self.symmetry_vertical))

    def mousePressEvent(self, event):
        if not self.document:
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.cancel_gesture()
            self.cancel_requested.emit()
            event.accept()
            return
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self.tool == 'Pan'):
            self.cancel_gesture()
            self.panning = True
            self.pan_button = event.button()
            self.pan_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self.invalidate_preview()
            x,y = self.cell_at(event.position().toPoint())
            if self.paste_size:
                self.paste_requested.emit(x,y)
                event.accept()
                return
            self.clicked.emit(x,y)
            self.drag_origin = self.drag_last = (x,y)
            self.constraint_origin=(x,y) if event.modifiers() & Qt.KeyboardModifier.ControlModifier else None
            self.constraint_axis=None
            if self.tool in ('Paint','Height','Variation','Vegetation'):
                self.pending.fill(False)
                self.pending[self.ids_at(x,y)] = True
            elif self.tool == 'Select':
                self.selection = (x,y,1,1)
            self.viewport().update()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.document:
            return
        if self.panning:
            delta = event.position().toPoint()-self.pan_position
            self.pan_position = event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-delta.y())
            return
        x,y = self.cell_at(event.position().toPoint())
        self.hover_cell = (x,y)
        self.invalidate_preview()
        self.hovered.emit(x,y)
        if self.drag_origin and event.buttons() & Qt.MouseButton.LeftButton:
            if self.tool in ('Paint','Height','Variation','Vegetation') and self.pattern is None:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if self.constraint_origin is None:
                        self.constraint_origin=self.drag_last
                    ox,oy=self.constraint_origin
                    if self.constraint_axis is None and (x,y)!=(ox,oy):
                        self.constraint_axis='x' if abs(x-ox)>=abs(y-oy) else 'y'
                    if self.constraint_axis=='x': y=oy
                    elif self.constraint_axis=='y': x=ox
                    self.hover_cell=(x,y)
                else:
                    self.constraint_origin=self.constraint_axis=None
                ids=self.document.geometry.stroke_brush(self.drag_last,(x,y),self.brush_size,self.brush_shape)
                self.pending[self.clip_ids(ids)]=True
                self.drag_last=(x,y)
            elif self.tool == 'Select':
                ox,oy = self.drag_origin
                self.selection = (min(ox,x), min(oy,y), min(800,abs(x-ox)+1), min(800,abs(y-oy)+1))
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        if self.panning:
            if event.button() != self.pan_button:
                return
            self.panning = False
            self.pan_button = None
            self.unsetCursor()
            return
        if event.button() == Qt.MouseButton.LeftButton and self.drag_origin is not None:
            if self.pending.any():
                self.paint_requested.emit(np.flatnonzero(self.pending))
            self.pending.fill(False)
            self.invalidate_preview()
            if self.tool == 'Select' and self.selection:
                self.selection_changed.emit(self.selection)
            self.drag_origin = self.drag_last = None
            self.constraint_origin=self.constraint_axis=None
            self.viewport().update()

    def wheelEvent(self, event):
        delta=event.angleDelta().y()
        if not self.document or not delta:
            event.accept()
            return
        position=event.position().toPoint()
        before=self.mapToScene(position)
        current=self.transform().m11()
        target=max(.3,min(50,current*1.2**max(-20,min(20,delta/120))))
        self.scale(target/current,target/current)
        after=self.mapToScene(position)
        correction=after-before
        self.translate(correction.x(),correction.y())
        self.hover_cell=self.cell_at(position)
        self.invalidate_preview()
        self.viewport().update()
        event.accept()

    def drawForeground(self, painter, rect):
        if not self.document:
            return
        scale = self.transform().m11()
        if self.show_grid and scale >= 6:
            painter.setPen(QPen(QColor(35,42,45,110), 0))
            for x in range(max(0,int(rect.left())),min(800,int(rect.right())+1)+1):
                painter.drawLine(QPointF(x,max(0,rect.top())),QPointF(x,min(800,rect.bottom())))
            for y in range(max(0,int(rect.top())),min(800,int(rect.bottom())+1)+1):
                painter.drawLine(QPointF(max(0,rect.left()),y),QPointF(min(800,rect.right()),y))
        if self.paste_size and self.hover_cell:
            painter.setPen(QPen(QColor('#8fd3cf'),0))
            painter.setBrush(QColor(110,205,204,35))
            painter.drawRect(QRectF(*self.hover_cell,*self.paste_size))
            return
        # Center guides are always visible; symmetry toggles only affect edits.
        x0,y0,x1,y1=self.document.geometry.bounds
        painter.setPen(QPen(QColor(110,205,204,180),0,Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(x0,(y0+y1)/2),QPointF(x1,(y0+y1)/2))
        painter.drawLine(QPointF((x0+x1)/2,y0),QPointF((x0+x1)/2,y1))
        painter.setPen(QPen(QColor('#8fd3cf'),0))
        if self.selection:
            painter.setBrush(QColor(110,205,204,30))
            painter.drawRect(QRectF(*self.selection))
        if self.preview_image is None:
            ids=np.flatnonzero(self.pending)
            if not len(ids) and self.hover_cell and self.tool in ('Paint','Height','Variation','Vegetation'):
                ids=self.ids_at(*self.hover_cell)
            if self.tool in ('Paint','Height','Variation','Vegetation'): ids=self.symmetric_ids(ids)
            rgba=np.zeros((800,800,4),dtype=np.uint8)
            if (self.tool=='Build' and self.building_key=='castle' and self.hover_cell
                    and self.show_players and self.layer=='surface'):
                x,y=self.hover_cell
                radius=CASTLE_AREA_RADIUS[self.document.size]
                # Keep anchor -> middle of the three-cell doorway between keep/camp.
                cx,cy=x+3,y+7
                g=self.document.geometry
                area=g.rectangle(cx-radius,cy-radius,2*radius+1,2*radius+1)
                area=area[g.playable[area]]
                rgba[g.y[area],g.x[area]]=(*PLAYER_COLORS[self.building_owner-1],
                                           round(max(0,min(100,self.area_opacity))*255/100))
            if len(ids):
                g=self.document.geometry
                ids=ids[g.playable[ids]]
                rgba[g.y[ids],g.x[ids]]=(181,219,180,90)
            self.preview_image=QImage(rgba.data,800,800,rgba.strides[0],QImage.Format.Format_RGBA8888).copy()
        painter.drawImage(QPointF(0,0),self.preview_image)
        if self.hover_cell:
            if self.tool in ('Build','Remove'):
                try:
                    service=BuildingService(self.document)
                    x,y=self.hover_cell
                    if self.tool=='Build':
                        ids=service.footprint(self.building_key,x,y)
                        try:
                            service.check_placement(self.building_key,x,y,self.building_owner)
                            color=QColor(115,220,150,90)
                        except ValueError:
                            color=QColor(230,85,85,100)
                    else:
                        group=service.group_at(x,y)
                        ids=service.footprint(group[0],group[1]['x'],group[1]['y']) if group else [self.document.geometry.index(x,y)]
                        color=QColor(230,85,85,100)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(color)
                    g=self.document.geometry
                    for i in ids:
                        painter.drawRect(QRectF(int(g.x[i]),int(g.y[i]),1,1))
                except (ValueError,KeyError):
                    pass
            painter.setPen(QPen(QColor('#f3cf82'),0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(*self.hover_cell,1,1))


class EditorWindow(QMainWindow):
    def __init__(self, startup=True, settings_path=None):
        super().__init__()
        self.resize(1440,940)
        self.setMinimumSize(1000,700)
        self.setWindowTitle(f'SHC DE Map Editor {__version__}')
        self.document = None
        self.map_clipboard = None
        self.busy = False
        self.jobs = set()
        self.settings = EditorSettings(settings_path)
        # One configuration root for all persisted UI data, including tests.
        self.pattern_library = PatternLibrary(self.settings.path.parent/'Patterns')
        self.pattern_library.install_defaults()
        self.state = EditorState.restore(self.settings.values)
        self.action_entries = []
        self.hotkeys_window = None
        self.height_warning = None
        self.preference_timer = QTimer(self)
        self.preference_timer.setSingleShot(True)
        self.preference_timer.timeout.connect(self.save_preferences)
        self.recent_files = RecentFiles(self.settings.path.with_name('recent-files.json'))
        self.canvas = MapCanvas()
        self.canvas.area_opacity = self.settings.values['castle_area_opacity']
        self.canvas.show_players = self.settings.values['show_castle_areas']
        self.map_column=QWidget()
        self.map_layout=QVBoxLayout(self.map_column)
        self.map_layout.setContentsMargins(0,0,0,0)
        self.map_layout.setSpacing(0)
        self.map_layout.addWidget(self.canvas,1)
        self.setCentralWidget(self.map_column)
        self.canvas.hovered.connect(self.hover)
        self.canvas.clicked.connect(self.inspect_cell)
        self.canvas.cancel_requested.connect(self.cancel_active_tool)
        self.canvas.paint_requested.connect(self.paint)
        self.canvas.selection_changed.connect(self.update_selection)
        self.canvas.paste_requested.connect(self.paste_at)
        self.build_toolbar()
        self.build_left()
        self.build_right()
        self.build_canvas_controls()
        self.reload_patterns()
        self.apply_state(save=False)
        self.change_layers()
        self.update_selection()
        self.statusBar().showMessage('Ready · Middle-drag to pan · Right-click cancels · Wheel zooms at cursor')
        if startup:
            QTimer.singleShot(0, lambda: self.new_map(400))

    def action(self, label, handler, shortcut=None, group='File', tip=None, canvas_only=False):
        action = QAction(label,self)
        action.triggered.connect(lambda checked=False: handler())
        if shortcut:
            if isinstance(shortcut,QKeySequence.StandardKey):
                action.setShortcuts(shortcut)
            else:
                action.setShortcut(shortcut)
        if canvas_only:
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.canvas.addAction(action)
        else:
            self.addAction(action)
        keys=', '.join(k.toString(QKeySequence.SequenceFormat.NativeText) for k in action.shortcuts())
        action.setToolTip((tip or label)+(' ('+keys+')' if keys else ''))
        self.action_entries.append((group,action,'Map canvas focus' if canvas_only else 'Editor window'))
        return action

    def build_toolbar(self):
        bar = QToolBar('Document')
        bar.setMovable(False)
        self.addToolBar(bar)
        menus={name:self.menuBar().addMenu(name) for name in ('File','Edit','View','Help')}
        def add(label, handler, shortcut=None, group='File', tip=None, toolbar=True, canvas=False):
            action=self.action(label,handler,shortcut,group,tip,canvas)
            menus[group].addAction(action)
            if toolbar:
                bar.addAction(action)
            return action
        add('New 400',lambda:self.new_map(400),QKeySequence.StandardKey.New,tip='Create a new 400 map from the empty template')
        add('New 500',lambda:self.new_map(500),tip='Create a new 500 map from the empty template')
        add('Open…',self.open_map,QKeySequence.StandardKey.Open,tip='Open a map or save file')
        add('Recent maps…',self.open_recent,tip='Reopen one of the last 50 opened or saved maps')
        bar.addSeparator()
        self.undo_action=add('Undo',self.undo,QKeySequence.StandardKey.Undo,'Edit',canvas=True)
        self.redo_action=add('Redo',self.redo,QKeySequence.StandardKey.Redo,'Edit',canvas=True)
        add('Fit map',self.canvas.fit_map,'F','View',canvas=True)
        add('Validate',self.validate,group='File',tip='Check structural validity and export limitations')
        add('Save',self.save_map,QKeySequence.StandardKey.Save,tip='Save to the current map; confirm before replacing an existing file')
        add('Save As…',self.save_as,QKeySequence.StandardKey.SaveAs,tip='Choose a map filename; confirm before replacing an existing file')
        add('Settings',self.show_settings,group='View',tip='Display preferences and reset editor controls')
        add('Hotkeys',self.show_hotkeys,group='Help',toolbar=False)
        add('About SHC DE Map Editor…',self.about,group='Help',toolbar=False)
        self.tool_actions={}
        for name,key,description in [('Variation','N','Paint a fixed texture variation value; Ctrl constrains direction'),('Vegetation','T','Plant the selected tree with the brush; four-cell spacing'),('Paint','B','Paint terrain; hold Ctrl for horizontal/vertical strokes'),('Height','E','Set terrain height with the brush; Ctrl constrains direction'),('Build','G','Place the selected building at its top-left cell'),('Remove','D','Remove a complete building group or one wall cell'),('Select','M','Drag a rectangular selection'),('Inspect','I','Inspect cell and entity data'),('Pan','H','Drag with the left button to move the view')]:
            action=self.action(name,lambda n=name:self.set_tool(n),key,'Tools',description,True)
            menus['Edit'].addAction(action)
            self.tool_actions[name]=action
        self.tool_panel=ToolPanel(self.tool_actions)
        self.tool_panel.setObjectName('dockBody')
        self.tools_bar=QScrollArea()
        self.tools_bar.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tools_bar.setWidgetResizable(True)
        self.tools_bar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tools_bar.setWidget(self.tool_panel)
        self.tools_bar.setFixedHeight(self.tool_panel.sizeHint().height()+24)
        self.map_layout.insertWidget(0,self.tools_bar)
        for label,handler,key,tip in (
                ('Copy selection',self.copy_selection,QKeySequence.StandardKey.Copy,'Copy selected cells from the current Surface, Height or Variation layer'),
                ('Paste selection',self.begin_paste,QKeySequence.StandardKey.Paste,'Place copied cells at their original size; click the top-left destination, Esc cancels')):
            menus['Edit'].addAction(self.action(label,handler,key,'Edit',tip,True))
        clear=self.action('Clear selection / cancel stroke',self.clear_selection,'Esc','Edit','Cancel an unfinished stroke or clear the selection',True)
        menus['Edit'].addAction(clear)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

    def dock(self, title, side):
        dock = QDockWidget(title,self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        body = QWidget()
        body.setObjectName('dockBody')
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12,12,12,12)
        layout.setSpacing(10)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(body)
        dock.setWidget(scroll)
        dock.setMinimumWidth(235)
        dock.setMaximumWidth(300)
        self.addDockWidget(side,dock)
        return layout

    def group(self, title, layout):
        box = QGroupBox(title)
        content = QVBoxLayout(box)
        content.setSpacing(7)
        layout.addWidget(box)
        return content

    def muted(self, text, layout):
        label = QLabel(text)
        label.setObjectName('muted')
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def build_left(self):
        layout=self.dock('Tools & brushes',Qt.DockWidgetArea.LeftDockWidgetArea)
        self.doc_label=QLabel('Opening template…')
        self.doc_label.setObjectName('heading')
        layout.addWidget(self.doc_label)
        self.build_owner=OwnerPanel()
        self.build_owner.valueChanged.connect(self.set_building_owner)
        layout.addWidget(self.build_owner)
        self.brush_panel=BrushPanel()
        self.brush_panel.shape_changed.connect(self.set_shape)
        self.brush_panel.size_changed.connect(self.set_size)
        self.brush_panel.mask_changed.connect(self.set_mask)
        self.brush_panel.rotate_requested.connect(self.rotate_mask)
        self.brush_panel.mirror_changed.connect(self.mirror_mask)
        self.brush_panel.invert_changed.connect(self.invert_mask)
        self.brush_panel.tag_changed.connect(self.set_mask_tag)
        self.brush_panel.gallery.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.brush_panel.gallery.customContextMenuRequested.connect(self.mask_context_menu)
        self.brush_panel.library_operations.addWidget(button('Edit','Edit selected mask pixels and dimensions',self.edit_mask))
        self.brush_panel.library_operations.addWidget(button('Edit tags','Assign comma-separated tags to the selected mask',self.edit_mask_tags))
        self.brush_panel.library_operations.addWidget(button('Masks folder','Open the mask library folder',self.open_masks_folder))
        for label,tip,handler in [('Create','Create a custom mask',self.create_mask),('Import','Import JSON or PNG mask: white paints; black/transparent skips. One pixel per cell, maximum 120 × 120.',self.import_mask)]:
            self.brush_panel.operations.addWidget(button(label,tip,handler))
        trees=self.group('Vegetation',layout)
        self.vegetation_group=trees.parentWidget()
        from .panels import Choices
        self.tree_kind='2'
        self.tree_choices=Choices([(k,p['name'],'Plant '+p['name']+' (T). Brush spaces trees four cells apart. Remove (D) deletes a tree.') for k,p in tree_catalog().items()])
        self.tree_choices.select('2')
        self.tree_choices.changed.connect(self.choose_tree)
        trees.addWidget(self.tree_choices)
        heightbox=self.group('Terrain height',layout)
        self.height_group=heightbox.parentWidget()
        self.height_control=SliderValue(0,255,self.state.height,tip='Target height 0–255; default 8. Values below 8 or above 130 are experimental and shown in red.')
        self.height_control.spin.valueChanged.connect(self.set_height)
        heightbox.addWidget(self.height_control)
        self.muted('Height (E): paint target elevation.\nSteep edges need in-game testing.',heightbox)
        variationbox=self.group('Texture variation / noise',layout)
        self.variation_group=variationbox.parentWidget()
        self.variation_control=SliderValue(0,65535,self.state.variation,
            tip='Fixed texture variation value. The same value produces repeatable variation; this is not terrain height.')
        self.variation_control.spin.valueChanged.connect(self.set_variation)
        variationbox.addWidget(self.variation_control)
        terrain_options=self.group('Terrain painting',layout)
        self.terrain_options_group=terrain_options.parentWidget()
        self.uniform_variation=QCheckBox('Apply fixed texture variation')
        self.uniform_variation.setToolTip('Stamp the selected variation along with terrain, including PNG masks. Undo restores both together.')
        self.uniform_variation.setChecked(self.state.uniform_variation)
        self.uniform_variation.toggled.connect(lambda on:self.set_uniform_variation(on))
        terrain_options.addWidget(self.uniform_variation)
        self.variation_hint=self.muted('',terrain_options)
        layout.insertWidget(1,self.brush_panel)
        self.brush_panel.setTitle('Masks')
        selection=self.group('Selection',layout)
        self.selection_group=selection.parentWidget()
        self.selection_label=QLabel('No selection')
        selection.addWidget(self.selection_label)
        self.fill_button=button('Fill selection','Fill the selected rectangle with the current terrain',self.fill_selection)
        selection.addWidget(self.fill_button)
        row=QHBoxLayout()
        self.clear_button=button('Clear','Clear selection (Esc on canvas)',self.clear_selection)
        self.capture_button=button('Save mask','Capture non-earth cells in selection; maximum 120 × 120',self.capture_mask)
        row.addWidget(self.clear_button)
        row.addWidget(self.capture_button)
        selection.addLayout(row)
        self.clip_selection=QCheckBox('Paint inside selection')
        self.clip_selection.setToolTip('Restrict brush strokes and mask stamps to the selected rectangle')
        self.clip_selection.toggled.connect(self.set_selection_clip)
        selection.addWidget(self.clip_selection)
        layout.addStretch()
        self.history_list=QListWidget()
        self.history_list.setMaximumHeight(65)
        self.history_list.setToolTip('Undoable edits; use Undo / Redo to step through them')
        layout.addWidget(self.history_list)

    def build_right(self):
        layout=self.dock('Terrain & view',Qt.DockWidgetArea.RightDockWidgetArea)
        self.view_panel=ViewPanel(self.settings.values)
        self.view_panel.changed.connect(self.change_layers)
        layout.addWidget(self.view_panel)
        symmetry=self.group('Symmetrical painting',self.view_panel.layout())
        self.symmetry_group=symmetry.parentWidget()
        self.symmetry_horizontal=QCheckBox('Horizontal axis · top / bottom')
        self.symmetry_vertical=QCheckBox('Vertical axis · left / right')
        for control in (self.symmetry_horizontal,self.symmetry_vertical):
            control.setToolTip('Mirror terrain, height and tree brushes across the map center. Both axes give four quarters. Buildings and Remove are unchanged. Selection clipping and protected cells still apply.')
            control.toggled.connect(self.set_symmetry)
            symmetry.addWidget(control)
        self.palette=MaterialPalette()
        self.palette.changed.connect(self.set_material)
        layout.addWidget(self.palette)
        buildings=self.group('Buildings',layout)
        self.buildings_group=buildings.parentWidget()
        self.building_list=QListWidget()
        self.building_list.setMinimumHeight(240)
        self.building_list.setMaximumHeight(310)
        self.building_list.setToolTip('Click a building, then click the map. Green preview fits; red means occupied or outside the map. G: Build; D: Remove.')
        for key,p in sorted(catalog().items(),key=lambda item:(item[1]['category'],item[1]['name'])):
            from PySide6.QtWidgets import QListWidgetItem
            item=QListWidgetItem('%s  ·  %s × %s' % (p['name'],p['width'],p['height']))
            item.setData(Qt.ItemDataRole.UserRole,key)
            item.setToolTip('%s — %s\nIncludes all linked parts. Anchor: top-left. Reference orientation.\nExperimental export: verify in the game.' % (p['category'],p['name']))
            self.building_list.addItem(item)
            if key=='castle': self.building_list.setCurrentItem(item)
        self.building_list.itemClicked.connect(self.choose_building)
        buildings.addWidget(self.building_list)
        self.muted('Reference orientations · experimental export\nCastles include campfire, stockpile and lord.',buildings)
        self.overview=QLabel()
        self.overview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overview.setFixedHeight(110)
        self.overview.setToolTip('Map overview; gold marks the playable boundary')
        layout.addWidget(self.overview)
        self.inspector=InspectorPanel()
        layout.addWidget(self.inspector)
        layout.addStretch()

    def build_canvas_controls(self):
        viewport=self.canvas.viewport()
        self.brush_overlay=QGroupBox('Brush',self.canvas)
        box=QVBoxLayout(self.brush_overlay)
        for control in (self.brush_panel.shapes,self.brush_panel.size_row,
                        self.brush_panel.slider,self.brush_panel.dimensions):
            box.addWidget(control)
        for panel in (self.height_group,self.variation_group):
            panel.parentWidget().layout().removeWidget(panel)
            panel.setParent(self.canvas)
        for panel in (self.brush_overlay,self.height_group,self.variation_group):
            panel.setStyleSheet('QGroupBox { background:#202a31; }')
            panel.setFixedWidth(250)
        viewport.installEventFilter(self)
        self.position_canvas_controls()

    def position_canvas_controls(self):
        if not hasattr(self,'brush_overlay'):return
        viewport=self.canvas.viewport();margin=14
        origin=viewport.pos()
        self.brush_overlay.adjustSize()
        self.brush_overlay.move(origin.x()+margin,origin.y()+margin)
        for panel in (self.height_group,self.variation_group):
            panel.adjustSize()
            top=margin
            if viewport.width()<528 and self.brush_overlay.isVisible():
                top=margin*2+self.brush_overlay.height()
            panel.move(origin.x()+max(margin,viewport.width()-panel.width()-margin),origin.y()+top)
            panel.raise_()
        self.brush_overlay.raise_()

    def eventFilter(self,watched,event):
        if watched is self.canvas.viewport() and event.type()==QEvent.Type.Resize:
            self.position_canvas_controls()
        return super().eventFilter(watched,event)

    def set_tool(self, value):
        self.canvas.cancel_gesture()
        self.state.tool=value
        self.apply_state()
        if value=='Variation': self.view_panel.set_layer('noise')
        elif value=='Height': self.view_panel.set_layer('height')
        elif value in ('Paint','Vegetation','Build'): self.view_panel.set_layer('surface')
        self.canvas.setFocus()

    def set_height(self,value):
        crossed=self.state.height<=130<value
        crossed_low=self.state.height>=8>value
        activate=value!=self.state.height
        self.state.height=value
        self.height_control.spin.setStyleSheet('QSpinBox { color:#ff6262; font-weight:600; }' if value<8 or value>130 else '')
        self.height_control.slider.setStyleSheet('QSlider::handle:horizontal { background:#ff6262; } QSlider::sub-page:horizontal { background:#c74444; }' if value<8 or value>130 else '')
        if activate: self.set_tool('Height')
        if self.state.tool=='Height' and hasattr(self,'fill_button'):
            self.fill_button.setText('Fill height: %s' % value)
        self.preference_timer.start(250)
        if crossed and not self.settings.values['hide_high_height_warning']:
            self.show_height_warning()
        elif crossed_low and not self.settings.values['hide_low_height_warning']:
            self.show_height_warning(low=True)

    def show_height_warning(self,low=False):
        if self.height_warning is not None: return
        title='Low terrain height' if low else 'High terrain height'
        message=('Ordinary ground starts at height 8. The game editor does not normally allow painting below 8. '
                 'Special terrain may use lower values, but ordinary ground at this height is unverified.\n\n'
                 'You can still use values down to 0. The selected value is kept.' if low else
                 'Heights above 130 have caused glitches in the game.\n\n'
                 'You can still use values up to 255. The selected value is kept.')
        dialog=QMessageBox(QMessageBox.Icon.Warning,title,message,
            QMessageBox.StandardButton.Ok,self)
        checkbox=QCheckBox("Don't show this warning again")
        dialog.setCheckBox(checkbox)
        self.height_warning=dialog
        def finished(_):
            self.settings.values['hide_low_height_warning' if low else 'hide_high_height_warning']=checkbox.isChecked()
            self.save_preferences()
            self.height_warning=None
            dialog.deleteLater()
        dialog.finished.connect(finished)
        self.height_control.slider.setSliderDown(False)
        dialog.open()

    def choose_tree(self,key):
        self.tree_kind=key
        self.set_tool('Vegetation')

    def set_building_owner(self,value):
        self.canvas.building_owner=value
        self.canvas.invalidate_preview()
        self.canvas.viewport().update()

    def choose_building(self,item):
        self.canvas.building_key=item.data(Qt.ItemDataRole.UserRole)
        self.set_tool('Build')

    def cancel_active_tool(self):
        self.clear_selection()
        self.set_tool('Inspect')
        self.building_list.clearSelection()
        self.statusBar().showMessage('Tool cancelled · Select a tool or building to continue')

    def set_shape(self, value):
        if value=='mask' and not self.state.mask_path:
            if self.brush_panel.gallery.count():
                self.set_mask(self.brush_panel.gallery.item(0).data(Qt.ItemDataRole.UserRole))
                return
            self.statusBar().showMessage('Create or import a mask first.')
            self.brush_panel.shapes.select(self.state.brush_shape)
            return
        self.state.brush_shape=value
        self.set_tool(self.state.tool if self.state.tool in ('Height','Variation','Vegetation') else 'Paint')

    def set_variation(self, value):
        self.state.variation=value
        self.apply_state()

    def set_uniform_variation(self, enabled):
        self.state.uniform_variation=enabled
        self.preference_timer.start(250)

    def set_size(self, value):
        self.state.brush_size=value
        self.apply_state()

    def set_material(self, value):
        self.state.material=value
        self.apply_state()
        self.canvas.setFocus()

    def set_mask(self, path):
        self.state.mask_path=path
        self.state.brush_shape='mask'
        self.set_tool(self.state.tool if self.state.tool in ('Height','Variation','Vegetation') else 'Paint')

    def rotate_mask(self, delta):
        self.state.rotation=(self.state.rotation+delta)%360
        self.apply_state()

    def mirror_mask(self, on):
        self.state.mirror=on
        self.apply_state()

    def invert_mask(self, on):
        self.canvas.cancel_gesture()
        self.state.mask_invert=on
        self.apply_state()

    def set_mask_tag(self, tag):
        self.state.mask_tag=tag
        self.preference_timer.start(250)

    def open_masks_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        try:
            self.pattern_library.directory.mkdir(parents=True,exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.pattern_library.directory.resolve()))):
                self.error('Could not open masks folder: '+str(self.pattern_library.directory))
        except OSError as error: self.error(str(error))

    def edit_mask_tags(self):
        item=self.brush_panel.gallery.currentItem()
        if item is None or item.isHidden():
            self.error('Select a visible mask to edit its tags.')
            return
        path=item.data(Qt.ItemDataRole.UserRole)
        try:
            pattern=PatternLibrary.load(path)
            text,ok=QInputDialog.getText(self,'Mask tags','Tags separated by commas (for example: letters, symbols):',text=', '.join(pattern.tags))
            if ok:
                self.pattern_library.set_tags(path,tuple(t.strip() for t in text.split(',') if t.strip()))
                self.reload_patterns()
        except (OSError,ValueError,KeyError,TypeError) as error: self.error(str(error))

    def set_symmetry(self):
        self.canvas.cancel_gesture()
        self.state.symmetry_horizontal=self.symmetry_horizontal.isChecked()
        self.state.symmetry_vertical=self.symmetry_vertical.isChecked()
        self.apply_state()

    def apply_state(self, save=True):
        maximum=self.document.geometry.max_brush_size if self.document else 500
        self.state.brush_size=min(maximum,max(1,self.state.brush_size))
        pattern=None
        if self.state.brush_shape=='mask':
            try:
                pattern=PatternLibrary.load(self.state.mask_path).transform(self.state.rotation,self.state.mirror,self.state.mask_invert)
            except (OSError,ValueError,KeyError,TypeError):
                self.state.brush_shape='square'
                self.state.mask_path=''
        self.canvas.tool=self.state.tool
        self.canvas.brush_size=self.state.brush_size
        self.canvas.brush_shape=self.state.brush_shape if pattern is None else 'square'
        self.canvas.pattern=pattern
        for axis in ('horizontal','vertical'):
            name='symmetry_'+axis; value=getattr(self.state,name)
            setattr(self.canvas,name,value)
            control=getattr(self,name)
            control.blockSignals(True); control.setChecked(value); control.blockSignals(False)
        self.canvas.invalidate_preview()
        self.tool_panel.choices.select(self.state.tool)
        self.brush_panel.sync(self.state,maximum,pattern)
        self.height_control.spin.setValue(self.state.height)
        self.palette.choices.select(self.state.material)
        self.variation_control.spin.blockSignals(True)
        self.variation_control.spin.setValue(self.state.variation)
        self.variation_control.slider.setValue(self.state.variation)
        self.variation_control.spin.blockSignals(False)
        self.uniform_variation.setChecked(self.state.uniform_variation)
        self.fill_button.setText('Fill variation: %s' % self.state.variation if self.state.tool=='Variation' else 'Fill height: %s' % self.state.height if self.state.tool=='Height' else 'Fill with '+self.state.material.replace('_',' '))
        self.sync_tool_panels()
        self.canvas.viewport().update()
        if save:
            self.preference_timer.start(250)

    def sync_tool_panels(self):
        tool=self.state.tool
        brush=tool in ('Paint','Height','Variation','Vegetation')
        self.height_group.setVisible(tool=='Height')
        self.variation_group.setVisible(tool=='Variation')
        self.vegetation_group.setVisible(tool=='Vegetation')
        self.terrain_options_group.setVisible(tool=='Paint')
        self.variation_hint.setText('Value: %s. Change it with Variation (N).' % self.state.variation)
        self.build_owner.setVisible(tool=='Build')
        self.buildings_group.setVisible(tool=='Build')
        self.palette.setVisible(tool=='Paint')
        self.brush_panel.setVisible(brush)
        self.brush_overlay.setVisible(brush)
        self.symmetry_group.setEnabled(brush)
        self.selection_group.setVisible(brush or tool=='Select')
        self.position_canvas_controls()

    def update_selection(self, selection=None):
        selection=self.canvas.selection
        self.selection_label.setText('%s × %s cells' % (selection[2],selection[3]) if selection else 'No selection')
        for w in (self.fill_button,self.clear_button,self.capture_button,self.clip_selection):
            w.setEnabled(selection is not None)
        self.capture_button.setEnabled(selection is not None and max(selection[2:])<=120)
        self.selection_label.setToolTip('Select a rectangle to enable Fill, Clear and Save mask. Masks must be at most 120 × 120 cells.')

    def set_selection_clip(self, on):
        self.canvas.clip_selection=on
        self.canvas.invalidate_preview()
        self.canvas.viewport().update()

    def copy_selection(self):
        if not self.document or not self.canvas.selection:
            self.statusBar().showMessage('Select a rectangle with Select (M), then press Ctrl+C.')
            return
        try:
            self.map_clipboard=MapClipboard.copy(self.document,self.canvas.selection,self.canvas.layer)
            clip=self.map_clipboard
            self.statusBar().showMessage('Copied %s: %s × %s cells. Ctrl+V, then click the top-left destination.' % (clip.layer,clip.width,clip.height))
        except ValueError as error:self.error(str(error))

    def begin_paste(self):
        if not self.document or self.map_clipboard is None:
            self.statusBar().showMessage('Copy a map selection first (Ctrl+C).')
            return
        self.canvas.cancel_gesture()
        self.canvas.paste_size=(self.map_clipboard.width,self.map_clipboard.height)
        self.canvas.setFocus();self.canvas.viewport().update()
        self.statusBar().showMessage('Paste %s: click the top-left destination. Esc or right-click cancels.' % self.map_clipboard.layer)

    def paste_at(self,x,y):
        if not self.map_clipboard:return
        try:
            report=self.map_clipboard.paste(self.document,x,y)
            self.canvas.cancel_gesture()
            self.update_document_ui()
            self.statusBar().showMessage('Pasted %s cells; %s outside/protected cells skipped.' % (report['eligible_cells'],report['skipped_cells']))
        except ValueError as error:self.error(str(error))

    def clear_selection(self):
        self.canvas.cancel_gesture()
        self.canvas.selection=None
        self.canvas.invalidate_preview()
        self.update_selection()
        self.canvas.viewport().update()

    def save_preferences(self):
        self.settings.values.update(self.state.preferences())
        try:
            self.settings.save()
        except OSError as error:
            self.statusBar().showMessage('Could not save preferences: '+str(error))

    def show_hotkeys(self):
        if self.hotkeys_window is None:
            self.hotkeys_window=HotkeysWindow(self,self.action_entries)
        self.hotkeys_window.show()
        self.hotkeys_window.raise_()
        self.hotkeys_window.activateWindow()

    def show_settings(self):
        dialog=QDialog(self)
        dialog.setWindowTitle('Settings')
        layout=QVBoxLayout(dialog)
        note=QLabel('Brush and view preferences are saved automatically.\nCastle opacity is in the right View panel.\n\n'+str(self.settings.path))
        note.setWordWrap(True)
        layout.addWidget(note)
        reset=button('Reset UI settings','Restore brush and display defaults; keep maps, masks and recent files')
        height_warning=QCheckBox('Warn when terrain height exceeds 130')
        height_warning.setChecked(not self.settings.values['hide_high_height_warning'])
        height_warning.toggled.connect(lambda on:(self.settings.values.update(hide_high_height_warning=not on),self.save_preferences()))
        layout.addWidget(height_warning)
        low_warning=QCheckBox('Warn when terrain height is below 8')
        low_warning.setChecked(not self.settings.values['hide_low_height_warning'])
        low_warning.toggled.connect(lambda on:(self.settings.values.update(hide_low_height_warning=not on),self.save_preferences()))
        layout.addWidget(low_warning)
        def restore():
            self.state=EditorState()
            v=self.view_panel
            v.layer='surface'
            for w in (v.grid,v.objects,v.players):
                w.setChecked(True)
            v.opacity.setValue(25)
            self.clear_selection()
            self.clip_selection.setChecked(False)
            self.apply_state()
            self.change_layers()
            self.save_preferences()
            dialog.accept()
        reset.clicked.connect(restore)
        layout.addWidget(reset)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def run_job(self, message, function, done):
        self.busy = True
        self.setEnabled(False)
        self.statusBar().showMessage(message)
        job=Job(function)
        self.jobs.add(job)
        def finish(result=None, error=None):
            self.jobs.discard(job)
            self.busy=False
            self.setEnabled(True)
            if error:
                self.error(error)
            else:
                done(result)
        job.signals.done.connect(lambda result: finish(result))
        job.signals.failed.connect(lambda error: finish(error=error))
        QThreadPool.globalInstance().start(job)

    def can_discard(self):
        if self.busy:
            return False
        if self.document and (self.document.dirty or self.canvas.pending.any()):
            answer=QMessageBox.question(self,'Unsaved changes','Discard unsaved changes?',
                QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            return answer == QMessageBox.StandardButton.Discard
        return True

    def new_map(self, size):
        if self.can_discard():
            self.run_job('Loading %s template…' % size,lambda: TemplateLibrary().create(size),self.set_document)

    def open_map(self):
        if not self.can_discard():
            return
        path,_=QFileDialog.getOpenFileName(self,'Open map or save',self.map_directory(),'Game maps and saves (*.map *.msv)')
        if path:
            self.open_path(path, discard_checked=True)

    def remember_file(self, path):
        self.settings.values['last_map_directory']=str(Path(path).resolve().parent)
        self.save_preferences()
        try:
            self.recent_files.remember(path)
        except OSError as error:
            self.error('Map operation succeeded, but recent files could not be saved: '+str(error))

    def open_path(self, path, discard_checked=False):
        if not discard_checked and not self.can_discard():
            return
        if not Path(path).is_file():
            self.error('Map no longer exists at this path:\n'+str(path))
            return
        def opened(document):
            self.set_document(document)
            self.remember_file(path)
        self.run_job('Opening map…',lambda: MapReader.open(path),opened)

    def open_recent(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Recent maps')
        dialog.resize(800,450)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Last 50 maps · newest first · select a path to reopen'))
        entries = QListWidget()
        for path in self.recent_files.files:
            entries.addItem(path)
            entries.item(entries.count()-1).setToolTip(path)
        layout.addWidget(entries)
        empty=QLabel('No recent maps yet. Open or save a map to add it here.')
        empty.setVisible(not bool(entries.count()))
        layout.addWidget(empty)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel)
        clear=buttons.addButton('Clear list',QDialogButtonBox.ButtonRole.ActionRole)
        clear.setToolTip('Clear recent-file history only. Your map files are not deleted.')
        clear.setEnabled(bool(entries.count()))
        def clear_history():
            try:
                self.recent_files.clear()
            except OSError as error:
                self.error('Could not clear recent files: '+str(error))
                return
            entries.clear();empty.show();clear.setEnabled(False)
            buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(False)
        clear.clicked.connect(clear_history)
        buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(bool(entries.count()))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        entries.itemDoubleClicked.connect(lambda item: dialog.accept())
        layout.addWidget(buttons)
        if entries.count():
            entries.setCurrentRow(0)
        if dialog.exec()==QDialog.DialogCode.Accepted and entries.currentItem():
            self.open_path(entries.currentItem().text())

    def set_document(self, document):
        self.document=document
        self.canvas.set_document(document)
        self.apply_state()
        self.update_selection()
        self.update_document_ui()
        self.statusBar().showMessage('Ready · Size %s · Middle-drag to pan · Right-click cancels · Wheel zooms at cursor' % document.size)

    def update_document_ui(self):
        if not self.document:
            return
        d=self.document
        name=d.saved_path.name if d.saved_path else (d.source_path.name if d.source_path else 'Untitled')
        self.doc_label.setText('Map size %s%s' % (d.size,' •' if d.dirty else ''))
        self.setWindowTitle('SHC DE Map Editor %s · %s%s' % (__version__,name,' · Unsaved' if d.dirty else ''))
        self.undo_action.setEnabled(d.history.cursor>0)
        self.redo_action.setEnabled(d.history.cursor<len(d.history.commands))
        self.history_list.clear()
        for i,cmd in enumerate(d.history.commands):
            self.history_list.addItem(('✓ ' if i<d.history.cursor else '↶ ')+cmd.label)
        self.canvas.refresh()
        if self.canvas.pixmap:
            x0,y0,x1,y1=d.geometry.bounds
            pix=self.canvas.pixmap.pixmap().copy(x0,y0,x1-x0,y1-y0)
            self.overview.setPixmap(pix.scaled(160,105,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation))

    def paint(self, ids):
        if not self.document:
            return
        if not len(ids):
            self.statusBar().showMessage('This mask has no painted cells at this position.')
            return
        try:
            if self.state.tool=='Vegetation':
                service=TreeService(self.document)
                # Space the original anchors first; otherwise a mirrored anchor
                # can disappear because its coordinate is no longer divisible by4.
                anchors=self.canvas.symmetric_ids(service.anchors(ids))
                if (self.state.symmetry_horizontal or self.state.symmetry_vertical) and len(tree_catalog()[self.tree_kind]['cells'])>1:
                    # Opposite anchors can meet one cell apart at the centerline.
                    # Skip both overlapping footprints instead of planting only
                    # whichever side happened to be processed first.
                    g=self.document.geometry
                    points=set(zip(g.x[anchors],g.y[anchors]))
                    anchors=np.array([i for i in anchors if not any(
                        (int(g.x[i])+dx,int(g.y[i])+dy) in points
                        for dy in range(-2,3) for dx in range(-2,3) if dx or dy)],dtype=np.int64)
                report=service.paint(anchors,self.tree_kind,scatter=False)
                self.update_document_ui()
                self.statusBar().showMessage('Planted %s trees/shrubs; occupied or unsuitable cells skipped' % report['planted'])
                return
            ids=self.canvas.symmetric_ids(ids)
            report=(VariationService(self.document).paint(ids,self.state.variation) if self.state.tool=='Variation'
                    else HeightService(self.document).paint(ids,self.state.height) if self.state.tool=='Height'
                    else TerrainService(self.document).paint(ids,self.state.material,variation=self.state.variation if self.state.uniform_variation else None))
            if not report['eligible_cells']:
                self.error('No editable cells in this stroke. Buildings, units, vegetation, water and map borders are protected.')
                return
            self.update_document_ui()
            self.statusBar().showMessage('Paint: %s eligible cells · %s protected/skipped · %s changed values' %
                (report['eligible_cells'],report['skipped_cells'],report['changed_field_values']))
        except Exception as error:
            self.error(str(error))

    def fill_selection(self):
        if self.document and self.canvas.selection:
            self.paint(self.document.geometry.rectangle(*self.canvas.selection))

    def undo(self):
        if self.document:
            self.document.history.undo()
            self.update_document_ui()

    def redo(self):
        if self.document:
            self.document.history.redo()
            self.update_document_ui()

    def hover(self,x,y):
        if self.document:
            try:
                row=TerrainService(self.document).inspect(x,y)
                if self.state.tool in ('Build','Remove'):
                    detail=catalog()[self.canvas.building_key]['name'] if self.state.tool=='Build' else 'Click a building group or wall cell'
                    self.statusBar().showMessage('X %s  Y %s · %s · %s · Player %s' % (x,y,self.state.tool,detail,self.build_owner.value()))
                    return
                self.statusBar().showMessage('X %s  Y %s · %s%% · %s / %s / %s %s · %s' %
                    (x,y,round(self.canvas.transform().m11()*100),self.state.tool,
                     self.state.material.replace('_',' '),self.state.brush_shape,self.state.brush_size,
                     'Playable' if row['playable'] else 'Outside boundary'))
            except ValueError:
                self.statusBar().showMessage('Outside storage diamond')

    def inspect_cell(self,x,y):
        if not self.document:
            return
        if self.state.tool in ('Build','Remove'):
            try:
                service=BuildingService(self.document)
                if self.state.tool=='Build':
                    service.place(self.canvas.building_key,x,y,self.build_owner.value())
                    message='Placed '+catalog()[self.canvas.building_key]['name']
                else:
                    from semantics import tile_index
                    result=(TreeService(self.document).remove(x,y) if self.document.grid(3004)[tile_index(x,y)] else service.remove(x,y))
                    message='Removed %s linked records / wall cells' % result['removed']
                self.update_document_ui()
                self.statusBar().showMessage(message)
            except (ValueError,KeyError) as error:
                self.error(str(error))
            return
        try:
            row=TerrainService(self.document).inspect(x,y)
            lines=['CELL  %s, %s' % (x,y), '', 'Playable: '+str(row['playable']),
                   'Surface: '+str(row['surface']), 'Height: '+str(row['height']),
                   'Variation: '+str(row['texture_noise']),
                   'Base height: '+str(row['base_height']), 'Logic: '+row['logic']]
            for obj in EntityService(self.document).at(x,y):
                lines += ['',obj['kind'].upper(),'Type: '+str(obj['type']), 'Slot: '+str(obj['slot']),
                          'Owner: '+str(obj.get('owner','—'))]
                if 'type_name' in obj: lines.append('Name: '+obj['type_name'])
                if 'hp_candidate' in obj:
                    lines.append('HP candidate: '+str(obj['hp_candidate']))
            self.inspector.setPlainText('\n'.join(lines))
        except ValueError:
            self.inspector.setPlainText('Outside storage diamond')

    def change_layers(self,*args):
        v=self.view_panel
        if self.canvas.layer!=v.layer:
            if v.layer=='noise':
                self.state.tool='Variation'
                self.canvas.cancel_gesture()
                self.apply_state()
            elif v.layer=='height':
                self.state.tool='Height'
                self.canvas.cancel_gesture()
                self.apply_state()
            elif self.state.tool in ('Height','Variation'):
                self.state.tool='Paint'
                self.canvas.cancel_gesture()
                self.apply_state()
        v.height_legend.setVisible(v.layer=='height')
        v.noise_legend.setVisible(v.layer=='noise')
        self.canvas.layer=v.layer
        self.canvas.show_grid=v.grid.isChecked()
        self.canvas.show_objects=v.objects.isChecked()
        self.canvas.show_players=v.players.isChecked()
        self.canvas.area_opacity=v.opacity.value()
        self.canvas.invalidate_preview()
        self.settings.values.update(castle_area_opacity=self.canvas.area_opacity,
            show_castle_areas=self.canvas.show_players,show_grid=self.canvas.show_grid,
            show_objects=self.canvas.show_objects,view_layer=self.canvas.layer)
        self.preference_timer.start(250)
        self.update_document_ui()

    def validate(self):
        if self.document:
            report=MapValidator.validate(self.document)
            QMessageBox.information(self,'Validation', '\n'.join(['Structural checks: '+('passed' if report['valid'] else 'failed'),
                'Changed sections: '+str(report['changed_sections'])]+report['errors']+report['warnings']))

    def map_directory(self):
        saved=self.settings.values.get('last_map_directory','')
        if isinstance(saved,str) and saved and Path(saved).is_dir():
            return saved
        for recent in self.recent_files.files:
            if Path(recent).parent.is_dir():
                return str(Path(recent).parent)
        return ''

    def save_map(self):
        if not self.document or self.busy:
            return
        path=self.document.saved_path
        if path is None and not self.document.is_template:
            path=self.document.source_path
        if path is None or path.suffix.lower()!='.map':
            self.save_as()
            return
        self.save_to_path(path)

    def save_to_path(self, path):
        path=Path(path).resolve()
        overwrite=path.exists()
        if overwrite:
            answer=QMessageBox.warning(self,'Replace existing map?',
                'Replace this file with your current map?\n\n'+str(path)+'\n\nThe previous contents will be replaced.',
                QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Save:
                return
        def saved(report):
            self.update_document_ui()
            self.statusBar().showMessage('Saved and readback verified: '+report['path'])
            self.remember_file(report['path'])
        self.run_job('Validating and writing map…',lambda: MapWriter.save_as(self.document,path,overwrite=overwrite),saved)

    def save_as(self):
        if not self.document or self.busy:
            return
        current=self.document.saved_path or self.document.source_path
        name=current.with_suffix('.map').name if current and not self.document.is_template else 'untitled-%s.map' % self.document.size
        if self.document.saved_path: name=self.document.saved_path.name
        initial=str(Path(self.map_directory())/name)
        path,_=QFileDialog.getSaveFileName(self,'Save map as',initial,'Map (*.map)',options=QFileDialog.Option.DontConfirmOverwrite)
        if path:
            # A version suffix such as .1 belongs to the user's filename.
            # Native dialogs do not always append the selected file extension.
            if not path.lower().endswith('.map'):
                path += '.map'
            self.save_to_path(path)

    def reload_patterns(self):
        self.brush_panel.load_masks(self.pattern_library,self.state.mask_path,self.state.mask_tag)
        self.apply_state()

    def mask_context_menu(self, position):
        gallery=self.brush_panel.gallery
        item=gallery.itemAt(position)
        if item is None:return
        gallery.setCurrentItem(item)
        menu=QMenu(self)
        menu.addAction('Edit tags...',self.edit_mask_tags)
        menu.addAction('Edit mask...',self.edit_mask)
        menu.exec(gallery.viewport().mapToGlobal(position))

    def run_mask_editor(self, pattern, path=None):
        dialog=MaskEditor(self,self.pattern_library,pattern,path)
        if dialog.exec()==QDialog.DialogCode.Accepted and dialog.saved_path:
            self.state.mask_path=str(dialog.saved_path)
            self.state.brush_shape='mask'
            self.state.mask_tag=''
            self.reload_patterns()

    def edit_mask(self):
        item=self.brush_panel.gallery.currentItem()
        if item is None or item.isHidden():
            self.error('Select a visible mask to edit.')
            return
        path=item.data(Qt.ItemDataRole.UserRole)
        try:self.run_mask_editor(PatternLibrary.load(path),path)
        except (OSError,ValueError,KeyError,TypeError) as error:self.error(str(error))

    def create_mask(self):
        cells=tuple(tuple(int((x-5)**2+(y-5)**2<=16) for x in range(11)) for y in range(11))
        self.run_mask_editor(Pattern('New mask',cells))

    def capture_mask(self):
        if not self.document or not self.canvas.selection:
            self.error('Select a rectangle first. Painted or resource cells become the mask; earth stays transparent.')
            return
        x,y,w,h=self.canvas.selection
        if w>120 or h>120:
            self.error('Masks may be at most 120 × 120 cells')
            return
        name,ok=QInputDialog.getText(self,'Save selection mask','Pattern name')
        if not ok:
            return
        try:
            cells=[]
            for dy in range(h):
                row=[]
                for dx in range(w):
                    try:
                        i=self.document.geometry.index(x+dx,y+dy)
                        on=self.document.geometry.playable[i] and (self.document.grid(3037)[i]!=0 or self.document.grid(3003)[i] in (0x28000,0x88000,0x20008000))
                    except ValueError:
                        on=False
                    row.append(int(on))
                cells.append(tuple(row))
            saved=self.pattern_library.save(Pattern(name,tuple(cells)))
            self.state.mask_path=str(saved)
            self.state.brush_shape='mask'
            self.state.mask_tag=''
            self.reload_patterns()
        except Exception as error:
            self.error(str(error))

    def import_mask(self):
        path,_=QFileDialog.getOpenFileName(self,'Import mask','','Masks (*.json *.png);;PNG image (*.png);;JSON mask (*.json)')
        if path:
            try:
                self.run_mask_editor(PatternLibrary.load(path))
            except Exception as error:
                self.error(str(error))

    def error(self,message):
        self.statusBar().showMessage(message)
        QMessageBox.warning(self,'Map editor',message)

    def about(self):
        QMessageBox.information(self,f'About SHC DE Map Editor',
            f'Version {__version__}\n\n400 / 500 templates · In-memory edits · Undo / redo · Mask library\n\n'
            'Terrain, height, building and tree editing. Fresh schematic export previews. Castle areas are 141 cells wide on size 400 and 161 on size 500. Native preview artwork and 3D are not implemented.\n\n'
            'Mask folder: '+str(self.pattern_library.directory))

    def closeEvent(self,event):
        if self.can_discard():
            self.preference_timer.stop()
            self.save_preferences()
            if self.hotkeys_window:
                self.hotkeys_window.close()
            event.accept()
        else:
            event.ignore()


def run():
    app=QApplication(sys.argv)
    app.setApplicationName('SHC DE Map Editor')
    app.setApplicationVersion(__version__)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets/app-icon.ico')))
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    if '--self-test' in sys.argv:
        from .smoke import self_test
        index=sys.argv.index('--self-test')
        return self_test(app, Path(sys.argv[index+1]))
    window=EditorWindow()
    window.show()
    return app.exec()
