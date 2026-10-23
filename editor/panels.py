"""Reusable Qt panels; no binary map editing lives here."""
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QColor, QImage, QKeySequence, QValidator, QPainter
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QButtonGroup, QLabel, QSpinBox, QSlider, QListWidget,
    QListWidgetItem, QListView, QCheckBox, QGroupBox, QPlainTextEdit,
    QDialog, QDialogButtonBox, QTreeWidget, QTreeWidgetItem, QToolTip, QComboBox)
from .services import MATERIALS
from .patterns import PatternLibrary
from .render import PLAYER_COLORS, HEIGHT_COLORS


def button(text, tip, callback=None):
    widget=QPushButton(text)
    widget.setToolTip(tip)
    if callback:
        widget.clicked.connect(callback)
    return widget


class Choices(QWidget):
    changed = Signal(str)

    def __init__(self, choices, columns=2):
        super().__init__()
        layout=QGridLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(5)
        self.buttons={}
        self.group=QButtonGroup(self)
        for i,(key,label,tip) in enumerate(choices):
            b=button(label,tip)
            b.setCheckable(True)
            self.group.addButton(b)
            self.buttons[key]=b
            layout.addWidget(b,i//columns,i%columns)
            b.clicked.connect(lambda checked=False,k=key: self.changed.emit(k))

    def select(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)


class SliderValue(QWidget):
    """Shared numeric input with slider and one-unit step buttons."""
    def __init__(self,minimum,maximum,value,suffix='',tip=''):
        super().__init__()
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        row=QHBoxLayout()
        self.minus=button('−','Decrease by one')
        self.plus=button('+','Increase by one')
        self.minus.setFixedWidth(34); self.plus.setFixedWidth(34)
        self.spin=QSpinBox(); self.spin.setRange(minimum,maximum); self.spin.setSuffix(suffix)
        self.spin.setValue(value); self.spin.setToolTip(tip)
        self.slider=QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum,maximum); self.slider.setValue(value)
        self.slider.setToolTip(tip)
        self.minus.clicked.connect(lambda:self.spin.setValue(self.spin.value()-1))
        self.plus.clicked.connect(lambda:self.spin.setValue(self.spin.value()+1))
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        def update_buttons():
            self.minus.setEnabled(self.spin.value()>minimum)
            self.plus.setEnabled(self.spin.value()<maximum)
        self.spin.valueChanged.connect(update_buttons); update_buttons()
        for w in (self.minus,self.spin,self.plus): row.addWidget(w)
        layout.addLayout(row); layout.addWidget(self.slider)


class OwnerPanel(QGroupBox):
    valueChanged = Signal(int)

    def __init__(self):
        super().__init__('Building owner')
        layout=QVBoxLayout(self)
        grid=QGridLayout()
        grid.setSpacing(6)
        self.buttons={}
        self.group=QButtonGroup(self)
        self.group.setExclusive(True)
        names=('Red','Orange','Yellow','Blue','Black','Purple','Sky blue','Green')
        for owner,(rgb,name) in enumerate(zip(PLAYER_COLORS,names),1):
            color=QColor(*rgb).name()
            foreground='#171e23' if owner in (2,3,7) else '#ffffff'
            b=button('P%s' % owner,'Player %s — %s. Set owner for new buildings and walls.' % (owner,name))
            b.setAccessibleName('Player %s, %s' % (owner,name))
            b.setCheckable(True)
            b.setMinimumHeight(36)
            b.setStyleSheet('QPushButton { background:%s; color:%s; border:2px solid #35424b; '
                            'border-radius:5px; padding:6px 2px; font-weight:600; } '
                            'QPushButton:hover { border-color:#aab7bd; } '
                            'QPushButton:checked { border-color:#ffffff; } '
                            'QPushButton:focus { border-style:dotted; }' % (color,foreground))
            self.group.addButton(b,owner)
            self.buttons[owner]=b
            grid.addWidget(b,(owner-1)//4,(owner-1)%4)
        self.buttons[1].setChecked(True)
        self.group.idClicked.connect(self.valueChanged.emit)
        layout.addLayout(grid)
        note=QLabel('Owner for new buildings')
        note.setObjectName('muted')
        layout.addWidget(note)

    def value(self):
        return self.group.checkedId()


class ToolPanel(QWidget):
    def __init__(self, actions):
        super().__init__()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.choices=Choices([(name,name,actions[name].toolTip()) for name in ('Paint','Height','Variation','Vegetation','Build','Remove','Select','Inspect','Pan')],columns=9)
        for name,b in self.choices.buttons.items():
            pix=QPixmap(20,20)
            pix.fill(Qt.GlobalColor.transparent)
            painter=QPainter(pix)
            painter.setPen(QColor('#b9d7cc'))
            if name=='Select':
                painter.drawRect(3,3,14,14)
            elif name=='Paint':
                painter.drawLine(4,16,16,4)
                painter.drawLine(3,17,7,16)
            elif name=='Pan':
                painter.drawLine(2,10,18,10)
                painter.drawLine(10,2,10,18)
                painter.drawLine(2,10,5,7)
                painter.drawLine(18,10,15,13)
            else:
                painter.drawEllipse(3,3,11,11)
                painter.drawLine(13,13,18,18)
            painter.end()
            b.setIcon(QIcon(pix))
            b.clicked.connect(actions[name].trigger)
        layout.addWidget(self.choices)


class CellSizeSpinBox(QSpinBox):
    def validate(self, text, position):
        raw=text.removesuffix(self.suffix()).strip()
        if not raw or raw.isdecimal():
            state=QValidator.State.Acceptable if raw and self.minimum()<=int(raw)<=self.maximum() else QValidator.State.Intermediate
            return state,text,position
        return QValidator.State.Invalid,text,position

    def fixup(self, text):
        QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()),
                         'Enter a whole number from 1 to %s cells.' % self.maximum(),self)
        return str(self.value())+self.suffix()


class BrushPanel(QGroupBox):
    shape_changed=Signal(str)
    size_changed=Signal(int)
    mask_changed=Signal(str)
    rotate_requested=Signal(int)
    mirror_changed=Signal(bool)
    invert_changed=Signal(bool)
    tag_changed=Signal(str)

    def __init__(self):
        super().__init__('Brush')
        layout=QVBoxLayout(self)
        self.shapes=Choices([('square','Square','Square footprint in map cells'),
                             ('circle','Circle','Circular footprint in map cells'),
                             ('mask','Mask','Stamp a saved mask at its original dimensions')],3)
        layout.addWidget(self.shapes)
        self.shapes.changed.connect(self.shape_changed)
        self.size_row=QWidget()
        row=QHBoxLayout(self.size_row)
        row.setContentsMargins(0,0,0,0)
        self.minus=button('−','Decrease brush size by exactly one cell')
        self.plus=button('+','Increase brush size by exactly one cell')
        self.minus.setFixedWidth(36)
        self.plus.setFixedWidth(36)
        self.size=CellSizeSpinBox()
        self.size.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.size.setRange(1,500)
        self.size.setSuffix(' cells')
        self.size.setKeyboardTracking(False)
        row.addWidget(self.minus)
        row.addWidget(self.size,1)
        row.addWidget(self.plus)
        layout.addWidget(self.size_row)
        self.slider=QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1,500)
        self.slider.setToolTip('Brush size in cells; type an exact large size above')
        layout.addWidget(self.slider)
        self.dimensions=QLabel()
        self.dimensions.setObjectName('muted')
        layout.addWidget(self.dimensions)
        self.minus.clicked.connect(lambda: self.size.setValue(self.size.value()-1))
        self.plus.clicked.connect(lambda: self.size.setValue(self.size.value()+1))
        self.size.valueChanged.connect(self._size_changed)
        self.slider.valueChanged.connect(self.size.setValue)
        self.tag_filter=QComboBox()
        self.tag_filter.addItem('All','')
        self.tag_filter.setToolTip('Filter masks by tag; All shows the complete library')
        self.tag_filter.currentIndexChanged.connect(self.filter_masks)
        layout.addWidget(self.tag_filter)
        self.gallery=QListWidget()
        self.gallery.setViewMode(QListView.ViewMode.IconMode)
        self.gallery.setResizeMode(QListView.ResizeMode.Adjust)
        self.gallery.setMovement(QListView.Movement.Static)
        self.gallery.setIconSize(QSize(42,42))
        self.gallery.setGridSize(QSize(94,70))
        self.gallery.setFixedHeight(200)
        self.gallery.setToolTip('Select a mask thumbnail to paint with it; masks keep their own cell dimensions')
        self.gallery.currentItemChanged.connect(lambda item,old: self.mask_changed.emit(item.data(Qt.ItemDataRole.UserRole)) if item else None)
        self.gallery.itemClicked.connect(lambda item: self.mask_changed.emit(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.gallery)
        self.empty=QLabel('No masks yet — create or import one.')
        self.empty.setObjectName('muted')
        layout.addWidget(self.empty)
        row=QHBoxLayout()
        self.rotate_left=button('↶','Rotate the mask 90° counterclockwise',lambda: self.rotate_requested.emit(-90))
        self.rotate_right=button('↷','Rotate the mask 90° clockwise',lambda: self.rotate_requested.emit(90))
        self.angle=QLabel('0°')
        self.mirror=QCheckBox('Mirror')
        self.mirror.setToolTip('Mirror the mask before applying its rotation')
        self.mirror.toggled.connect(self.mirror_changed)
        for w in (self.rotate_left,self.angle,self.rotate_right,self.mirror):
            row.addWidget(w)
        layout.addLayout(row)
        self.invert=QCheckBox('Invert mask')
        self.invert.setToolTip('Binary: swap painted/empty cells. Height: reverse elevation within its range. Saved mask stays unchanged.')
        self.invert.toggled.connect(self.invert_changed)
        layout.addWidget(self.invert)
        self.operations=QHBoxLayout()
        layout.addLayout(self.operations)
        self.library_operations=QHBoxLayout()
        layout.addLayout(self.library_operations)

    def _size_changed(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.minus.setEnabled(value>1)
        self.plus.setEnabled(value<self.size.maximum())
        self.size_changed.emit(value)

    def sync(self, state, maximum, pattern):
        self.shapes.select(state.brush_shape)
        self.size.blockSignals(True)
        self.slider.blockSignals(True)
        self.size.setMaximum(maximum)
        self.slider.setMaximum(maximum)
        self.size.setValue(state.brush_size)
        self.slider.setValue(state.brush_size)
        self.size.blockSignals(False)
        self.slider.blockSignals(False)
        mask=state.brush_shape=='mask'
        self.size_row.setEnabled(not mask)
        self.slider.setEnabled(not mask)
        self.size_row.setToolTip('Masks have fixed dimensions; select Square or Circle to resize' if mask else 'Size: 1–%s cells. Type a value or use − / +.' % maximum)
        self.size.setToolTip(self.size_row.toolTip())
        self.minus.setEnabled(not mask and state.brush_size>1)
        self.plus.setEnabled(not mask and state.brush_size<maximum)
        self.dimensions.setText(('%s · %s × %s cells' % (pattern.name,len(pattern.cells[0]),len(pattern.cells))) if pattern else ('Size range: 1–%s cells' % maximum))
        self.dimensions.setWordWrap(True)
        if pattern and pattern.is_height:
            self.dimensions.setText(self.dimensions.text()+'\nHeight values %s–%s' % pattern.height_range)
        self.angle.setText('%s°' % state.rotation)
        self.mirror.blockSignals(True)
        self.mirror.setChecked(state.mirror)
        self.mirror.blockSignals(False)
        self.invert.blockSignals(True)
        self.invert.setChecked(state.mask_invert)
        self.invert.blockSignals(False)
        for w in (self.rotate_left,self.rotate_right,self.mirror,self.invert):
            w.setEnabled(mask and pattern is not None)

    def filter_masks(self, *args):
        tag=self.tag_filter.currentData() or ''
        shown=0
        for i in range(self.gallery.count()):
            item=self.gallery.item(i)
            tags=item.data(Qt.ItemDataRole.UserRole+1) or []
            visible=not tag or (not tags if tag=='__untagged__' else tag in tags)
            item.setHidden(not visible)
            shown+=int(visible)
        self.gallery.setVisible(shown>0)
        self.empty.setText('No masks for this tag.' if tag else 'No masks yet — create or import one.')
        self.empty.setVisible(shown==0)
        self.tag_changed.emit(tag)

    def load_masks(self, library, selected, tag=''):
        self.gallery.blockSignals(True)
        self.gallery.clear()
        tags=set()
        for path in library.list():
            try:
                pattern=PatternLibrary.load(path)
                cells=np.asarray(pattern.cells,dtype=np.uint8)
                rgb=np.zeros((*cells.shape,4),dtype=np.uint8)
                rgb[cells!=0]=(160,205,183,255)
                if pattern.is_height:
                    rgb[cells!=0,:3]=HEIGHT_COLORS[np.asarray(pattern.heights,dtype=np.uint8)[cells!=0]]
                image=QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format.Format_RGBA8888).copy()
                pix=QPixmap.fromImage(image).scaled(42,42,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation)
                item=QListWidgetItem(QIcon(pix),pattern.name)
                item.setData(Qt.ItemDataRole.UserRole,str(path))
                item.setData(Qt.ItemDataRole.UserRole+1,list(pattern.tags))
                tags.update(pattern.tags)
                item.setToolTip('%s · %s × %s cells · %s\nTags: %s\n%s' % (pattern.name,cells.shape[1],cells.shape[0],
                    'height values %s–%s' % pattern.height_range if pattern.is_height else 'binary coverage',
                    ', '.join(pattern.tags) or 'Untagged',path))
                self.gallery.addItem(item)
                if str(path)==selected:
                    self.gallery.setCurrentItem(item)
            except (OSError,ValueError,KeyError,TypeError):
                continue
        self.empty.setVisible(self.gallery.count()==0)
        self.gallery.setVisible(self.gallery.count()>0)
        self.gallery.blockSignals(False)
        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem('All','')
        self.tag_filter.addItem('Untagged','__untagged__')
        for value in sorted(tags): self.tag_filter.addItem(value,value)
        self.tag_filter.setCurrentIndex(max(0,self.tag_filter.findData(tag)))
        self.tag_filter.blockSignals(False)
        self.filter_masks()


class MaterialPalette(QGroupBox):
    changed=Signal(str)

    def __init__(self):
        super().__init__('Terrain palette')
        layout=QVBoxLayout(self)
        self.choices=Choices([(name,name.replace('_',' ').title(),
            ('Paint '+name.replace('_',' '))) for name in MATERIALS])
        for name,b in self.choices.buttons.items():
            pix=QPixmap(22,22)
            pix.fill(QColor(MATERIALS[name][1]))
            b.setIcon(QIcon(pix))
            b.setIconSize(QSize(22,22))
            b.setMinimumHeight(40)
        self.choices.changed.connect(self.changed)
        layout.addWidget(self.choices)
        self.choices.buttons['marsh'].setToolTip('Paint marsh: passable ground that cannot be built on. Paint another terrain over it to remove it.')


class ViewPanel(QGroupBox):
    changed=Signal()

    def __init__(self, values):
        super().__init__('View & symmetry')
        layout=QVBoxLayout(self)
        self.layer=values.get('view_layer','surface')
        if self.layer not in ('surface','height','noise'):
            self.layer='surface'
        self.height_legend=QWidget()
        legend=QVBoxLayout(self.height_legend); legend.setContentsMargins(0,0,0,0)
        gradient=QLabel()
        rgb=np.repeat(HEIGHT_COLORS[None,:,:],12,axis=0).copy()
        gradient.setPixmap(QPixmap.fromImage(QImage(rgb.data,256,12,rgb.strides[0],QImage.Format.Format_RGB888).copy()))
        gradient.setScaledContents(True); gradient.setFixedHeight(12)
        legend.addWidget(gradient)
        ticks=QHBoxLayout()
        for i,value in enumerate((0,64,128,192,255)):
            if i: ticks.addStretch()
            ticks.addWidget(QLabel(str(value)))
        legend.addLayout(ticks)
        layout.addWidget(self.height_legend)
        self.height_legend.setVisible(self.layer=='height')
        self.noise_legend=QLabel('Variation: black 0 → white 65535\nUse Variation (N) to paint values')
        self.noise_legend.setWordWrap(True)
        layout.addWidget(self.noise_legend)
        self.noise_legend.setVisible(self.layer=='noise')
        self.grid=QCheckBox('Cell grid')
        self.objects=QCheckBox('Objects and units')
        self.players=QCheckBox('Castle areas')
        self.terrain_rewrite=QCheckBox('Castle terrain clearing')
        for w,key,tip in [(self.grid,'show_grid','Show cell grid when zoomed in'),
                          (self.objects,'show_objects','Show schematic objects and unit records'),
                          (self.players,'show_castle_areas','Native construction radius around each keep, selected by map size'),
                          (self.terrain_rewrite,'show_terrain_rewrite','Amber: terrain the game may repaint around keep/campfire at startup. This overlay does not edit terrain.')]:
            w.setChecked(values.get(key,True) is True)
            w.setToolTip(tip)
            w.toggled.connect(self.changed)
            layout.addWidget(w)
        self.opacity_control=SliderValue(0,100,values['castle_area_opacity'],'%',
            'Castle area overlay opacity; height view retains accurate colors')
        self.opacity=self.opacity_control.spin
        layout.addWidget(QLabel('Castle area opacity'))
        self.opacity.setSuffix('%')
        self.opacity.setValue(values['castle_area_opacity'])
        self.opacity.setToolTip('Transparency of castle area overlays; solid castle footprints retain their player color')
        self.opacity.valueChanged.connect(self.changed)
        layout.addWidget(self.opacity_control)

    def set_layer(self, value):
        self.layer=value
        self.height_legend.setVisible(value=='height')
        self.noise_legend.setVisible(value=='noise')
        self.changed.emit()


class InspectorPanel(QGroupBox):
    def __init__(self):
        super().__init__('Inspector')
        layout=QVBoxLayout(self)
        self.summary=QLabel('Click a cell to inspect it.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.details=QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(120)
        self.details.hide()
        self.toggle=button('Details','Show or hide raw cell and entity fields')
        self.toggle.setCheckable(True)
        self.toggle.toggled.connect(self.details.setVisible)
        layout.addWidget(self.toggle)
        layout.addWidget(self.details)

    def setPlainText(self, text):
        self.details.setPlainText(text)
        lines=text.splitlines()
        self.summary.setText('\n'.join([lines[0]]+[line for line in lines if line.startswith(('Height:', 'Playable:'))]))


class HotkeysWindow(QDialog):
    def __init__(self, parent, entries):
        super().__init__(parent)
        self.setWindowTitle('Hotkeys')
        self.resize(690,540)
        self.setModal(False)
        layout=QVBoxLayout(self)
        tree=QTreeWidget()
        tree.setHeaderLabels(['Action','Shortcut','Context'])
        groups={}
        for group,action,context in entries:
            keys=', '.join(k.toString(QKeySequence.SequenceFormat.NativeText) for k in action.shortcuts())
            if not keys:
                continue
            if group not in groups:
                groups[group]=QTreeWidgetItem(tree,[group])
            QTreeWidgetItem(groups[group],[action.text(),keys,context])
        mouse=QTreeWidgetItem(tree,['Mouse controls'])
        for label,key in [('Pan the map','Middle drag'),
                          ('Pan with the Pan tool','Left drag'),
                          ('Zoom at cursor','Mouse wheel'),
                          ('Use the active brush or tool','Left click / drag'),
                          ('Draw a selection with Select','Left drag'),
                          ('Place copied cells after Ctrl+V','Left click at top-left destination'),
                          ('Constrain regular brush stroke to one axis','Ctrl + left drag'),
                          ('Cancel active tool or paste placement','Right click')]:
            QTreeWidgetItem(mouse,[label,key,'Map canvas'])
        tree.expandAll()
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        layout.addWidget(tree)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
