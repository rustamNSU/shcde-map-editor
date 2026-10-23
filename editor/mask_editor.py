"""Pixel-mask editor. Edits stay in memory until Save or Save As succeeds."""
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt,QRect,QTimer
from PySide6.QtGui import QImage,QPainter,QColor,QPen,QPixmap
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,
    QLabel,QLineEdit,QSpinBox,QPushButton,QScrollArea,QDialogButtonBox,QMessageBox,QSlider,
    QComboBox,QCheckBox)
from .patterns import Pattern,PatternLibrary,ImageImportSettings,MAX_PATTERN_SIZE


class MaskCanvas(QWidget):
    def __init__(self, pattern):
        super().__init__()
        self.cells=np.zeros((MAX_PATTERN_SIZE,MAX_PATTERN_SIZE),dtype=np.uint8)
        self.heights=np.zeros_like(self.cells)
        source=np.asarray(pattern.cells,dtype=np.uint8)
        self.rows,self.columns=source.shape
        self.cells[:self.rows,:self.columns]=source
        self.is_height=pattern.is_height
        self.height_range=pattern.height_range
        if pattern.is_height:self.heights[:self.rows,:self.columns]=np.asarray(pattern.heights,dtype=np.uint8)
        self.selected_height=pattern.height_range[0] if pattern.is_height else 8
        self.pixel_size=16
        self.paint_value=None
        self.resize_grid(self.columns,self.rows)

    def resize_grid(self, columns, rows):
        self.columns=columns;self.rows=rows
        self.setFixedSize(columns*self.pixel_size+1,rows*self.pixel_size+1)
        self.update()

    def paintEvent(self, event):
        painter=QPainter(self)
        rgb=np.zeros((self.rows,self.columns,3),dtype=np.uint8)
        rgb[:]=(28,37,43)
        active=self.cells[:self.rows,:self.columns]!=0
        if self.is_height:
            lo,hi=self.height_range
            levels=((self.heights[:self.rows,:self.columns].astype(np.float32)-lo)*255/max(1,hi-lo)).clip(0,255).astype(np.uint8)
            rgb[active]=np.repeat(levels[...,None],3,axis=2)[active]
        else:rgb[active]=(160,205,183)
        image=QImage(rgb.data,self.columns,self.rows,rgb.strides[0],QImage.Format.Format_RGB888).copy()
        painter.drawImage(QRect(0,0,self.columns*self.pixel_size,self.rows*self.pixel_size),image)
        if self.pixel_size<4:return
        painter.setPen(QPen(QColor('#52616b'),1))
        for x in range(self.columns+1): painter.drawLine(x*self.pixel_size,0,x*self.pixel_size,self.height())
        for y in range(self.rows+1): painter.drawLine(0,y*self.pixel_size,self.width(),y*self.pixel_size)

    def cell_at(self,event):
        return int(event.position().x())//self.pixel_size,int(event.position().y())//self.pixel_size

    def mousePressEvent(self,event):
        if event.button() not in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton):return
        x,y=self.cell_at(event)
        if 0<=x<self.columns and 0<=y<self.rows:
            if self.is_height:
                self.paint_value=0 if event.button()==Qt.MouseButton.RightButton else 1
                self.cells[y,x]=self.paint_value
                if self.paint_value:self.heights[y,x]=self.selected_height
            elif event.button()==Qt.MouseButton.LeftButton:
                self.paint_value=1-int(self.cells[y,x]);self.cells[y,x]=self.paint_value
            self.update()

    def mouseMoveEvent(self,event):
        if self.paint_value is None or not event.buttons()&(Qt.MouseButton.LeftButton|Qt.MouseButton.RightButton):return
        x,y=self.cell_at(event)
        if 0<=x<self.columns and 0<=y<self.rows:
            self.cells[y,x]=self.paint_value
            if self.is_height and self.paint_value:self.heights[y,x]=self.selected_height
            self.update()

    def mouseReleaseEvent(self,event): self.paint_value=None


class MaskEditor(QDialog):
    def __init__(self,parent,library,pattern,path=None):
        super().__init__(parent)
        self.library=library;self.path=Path(path) if path else None;self.saved_path=None
        self.setWindowTitle('Edit mask — '+pattern.name)
        self.resize(760,650)
        layout=QVBoxLayout(self)
        self.instructions=QLabel();self.instructions.setWordWrap(True);layout.addWidget(self.instructions)
        form=QFormLayout();self.name=QLineEdit(pattern.name);self.tags=QLineEdit(', '.join(pattern.tags))
        self.name.setReadOnly(self.path is not None)
        self.tags.setPlaceholderText('letters, symbols')
        form.addRow('Name',self.name);form.addRow('Tags',self.tags);layout.addLayout(form)
        self.canvas=MaskCanvas(pattern)
        mode_row=QHBoxLayout();self.mode=QComboBox()
        self.mode.addItem('Binary shape','binary');self.mode.addItem('Height values','height')
        self.mode.setCurrentIndex(1 if pattern.is_height else 0)
        mode_row.addWidget(QLabel('Mask type'));mode_row.addWidget(self.mode)
        self.minimum=QSpinBox();self.maximum=QSpinBox();self.height_value=QSpinBox()
        for spin in (self.minimum,self.maximum,self.height_value):spin.setRange(0,255)
        self.minimum.setValue(pattern.height_range[0]);self.maximum.setValue(pattern.height_range[1])
        self.height_value.setValue(self.canvas.selected_height)
        for label,widget in (('Min',self.minimum),('Max',self.maximum),('Paint height',self.height_value)):
            mode_row.addWidget(QLabel(label));mode_row.addWidget(widget)
        layout.addLayout(mode_row)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.minimum.valueChanged.connect(self.change_height_range);self.maximum.valueChanged.connect(self.change_height_range)
        self.height_value.valueChanged.connect(lambda value:setattr(self.canvas,'selected_height',value))
        self.change_mode()
        row=QHBoxLayout();self.columns=QSpinBox();self.rows=QSpinBox()
        for spin,value in ((self.columns,self.canvas.columns),(self.rows,self.canvas.rows)):
            spin.setRange(1,MAX_PATTERN_SIZE);spin.setValue(value);spin.setKeyboardTracking(False)
        row.addWidget(QLabel('Columns'));row.addWidget(self.columns)
        row.addWidget(QLabel('Rows'));row.addWidget(self.rows)
        for label,spin in (('+ Column',self.columns),('+ Row',self.rows)):
            button=QPushButton(label);button.clicked.connect(lambda checked=False,s=spin:s.setValue(s.value()+1));row.addWidget(button)
        invert=QPushButton('Invert');invert.clicked.connect(self.invert);row.addWidget(invert)
        layout.addLayout(row)
        for spin in (self.columns,self.rows):spin.valueChanged.connect(self.resize_canvas)
        zoom_row=QHBoxLayout();zoom_row.addWidget(QLabel('Zoom'))
        self.zoom=QSpinBox();self.zoom.setRange(6,400);self.zoom.setSuffix('%');self.zoom.setValue(100)
        self.zoom.setSingleStep(25);self.zoom.setToolTip('Magnify pixels without changing mask dimensions')
        minus=QPushButton('−');plus=QPushButton('+');fit=QPushButton('Fit mask')
        minus.clicked.connect(lambda:self.zoom.setValue(self.zoom.value()-25))
        plus.clicked.connect(lambda:self.zoom.setValue(self.zoom.value()+25))
        slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(6,400);slider.setValue(100)
        slider.valueChanged.connect(self.zoom.setValue);self.zoom.valueChanged.connect(slider.setValue)
        self.zoom.valueChanged.connect(self.set_zoom)
        for widget in (minus,self.zoom,plus,slider,fit):zoom_row.addWidget(widget)
        layout.addLayout(zoom_row)
        self.scroll=QScrollArea();self.scroll.setWidget(self.canvas);layout.addWidget(self.scroll,1)
        fit.clicked.connect(self.fit_mask)
        layout.addWidget(QLabel('1–%d rows and columns. Save uses the app mask folder; Save As keeps the original.' % MAX_PATTERN_SIZE))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject)
        save_as=buttons.addButton('Save As…',QDialogButtonBox.ButtonRole.ActionRole);save_as.clicked.connect(self.save_as)
        layout.addWidget(buttons)
        self.initial_state=self.edit_state()

    def change_mode(self):
        height=self.mode.currentData()=='height'
        if height and not self.canvas.is_height and not np.any(self.canvas.heights):
            self.canvas.heights.fill(self.height_value.value())
        self.canvas.is_height=height
        for widget in (self.minimum,self.maximum,self.height_value):widget.setEnabled(height)
        self.instructions.setText('Height mask: left click/drag paints the selected height; right click/drag makes a hole. Black can be height zero; holes leave the map unchanged.' if height else 'Click to toggle a pixel; drag to paint or erase. Increase rows/columns to expand the canvas.')
        self.change_height_range()

    def change_height_range(self):
        lo,hi=self.minimum.value(),self.maximum.value()
        if lo>hi:
            if self.sender() is self.maximum:self.minimum.setValue(hi);lo=hi
            else:self.maximum.setValue(lo);hi=lo
        self.canvas.height_range=(lo,hi)
        np.clip(self.canvas.heights,lo,hi,out=self.canvas.heights)
        self.height_value.setRange(lo,hi)
        self.canvas.selected_height=self.height_value.value();self.canvas.update()

    def edit_state(self):
        return (self.name.text(),self.tags.text(),self.columns.value(),self.rows.value(),
                self.canvas.cells[:self.rows.value(),:self.columns.value()].tobytes(),
                self.canvas.is_height,self.canvas.height_range,
                self.canvas.heights[:self.rows.value(),:self.columns.value()].tobytes() if self.canvas.is_height else b'')

    def reject(self):
        if self.edit_state()!=self.initial_state:
            answer=QMessageBox.question(self,'Unsaved mask changes','Discard unsaved mask changes?',
                QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer!=QMessageBox.StandardButton.Discard:return
        super().reject()

    def set_zoom(self,value):
        self.canvas.pixel_size=max(1,round(16*value/100))
        self.resize_canvas()

    def fit_mask(self):
        viewport=self.scroll.viewport()
        pixels=min((viewport.width()-2)//self.columns.value(),(viewport.height()-2)//self.rows.value())
        self.zoom.setValue(max(6,min(400,int(pixels*100/16))))

    def resize_canvas(self):self.canvas.resize_grid(self.columns.value(),self.rows.value())

    def invert(self):
        if self.canvas.is_height:
            area=self.canvas.heights[:self.rows.value(),:self.columns.value()]
            area[:]=sum(self.canvas.height_range)-area.astype(np.int16)
        else:
            area=self.canvas.cells[:self.rows.value(),:self.columns.value()]
            area[:]=1-area
        self.canvas.update()

    def pattern(self,name,tags):
        cells=self.canvas.cells[:self.rows.value(),:self.columns.value()]
        heights=self.canvas.heights[:self.rows.value(),:self.columns.value()]
        return Pattern(name.strip(),tuple(tuple(int(v) for v in row) for row in cells),
                       tuple(t.strip() for t in tags.split(',') if t.strip()),
                       heights=tuple(tuple(int(v) for v in row) for row in heights) if self.canvas.is_height else (),
                       height_range=self.canvas.height_range)

    def save(self):
        try:
            pattern=self.pattern(self.name.text(),self.tags.text())
            self.saved_path=self.library.replace(self.path,pattern) if self.path else self.library.save(pattern)
        except (OSError,ValueError,KeyError,TypeError) as error:
            QMessageBox.warning(self,'Could not save mask',str(error));return
        self.accept()

    def save_as(self):
        dialog=QDialog(self);dialog.setWindowTitle('Save mask as');layout=QFormLayout(dialog)
        name=QLineEdit(self.name.text()+' copy');tags=QLineEdit(self.tags.text())
        layout.addRow('New name',name);layout.addRow('Tags',tags)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:self.saved_path=self.library.save(self.pattern(name.text(),tags.text()))
        except (OSError,ValueError,KeyError,TypeError) as error:
            QMessageBox.warning(self,'Could not save mask',str(error));return
        self.accept()


class ImageMaskImportDialog(QDialog):
    """Preview image-to-mask conversion; accepts without writing a library file.

    After acceptance, ``pattern`` and ``settings`` hold the converted Pattern
    and ImageImportSettings. The caller can persist settings.to_dict() and open
    MaskEditor to name/edit/save the result.
    """
    def __init__(self,parent,path,settings=None):
        super().__init__(parent)
        self.path=Path(path);self.pattern=None
        self.settings=ImageImportSettings.for_image(path) if settings is None else ImageImportSettings.from_dict(settings)
        from PIL import Image,ImageOps
        with Image.open(path) as source:
            oriented=ImageOps.exif_transpose(source)
            source_width,source_height=oriented.size;source_format=source.format or self.path.suffix.lstrip('.').upper()
        self.setWindowTitle('Import image mask — '+self.path.name);self.resize(650,740)
        layout=QVBoxLayout(self)
        info=QLabel('%s · %d × %d source pixels\nChoose output cells and conversion. The original image stays unchanged.' % (source_format,source_width,source_height));info.setWordWrap(True);layout.addWidget(info)
        dimensions=QHBoxLayout();self.width_cells=QSpinBox();self.height_cells=QSpinBox()
        for spin,value in ((self.width_cells,self.settings.width),(self.height_cells,self.settings.height)):
            spin.setRange(1,MAX_PATTERN_SIZE);spin.setValue(value);spin.setKeyboardTracking(False)
        dimensions.addWidget(QLabel('Output width'));dimensions.addWidget(self.width_cells)
        dimensions.addWidget(QLabel('Height'));dimensions.addWidget(self.height_cells)
        dimensions.addWidget(QLabel('cells'));layout.addLayout(dimensions)
        form=QFormLayout();self.mode=QComboBox()
        self.mode.addItem('Binary shape (brightness threshold)','binary');self.mode.addItem('Height values (grayscale)','height')
        self.mode.setCurrentIndex(self.mode.findData(self.settings.mode));form.addRow('Convert to',self.mode)
        self.fit=QComboBox()
        self.fit.addItem('Fit whole image, transparent margins','contain');self.fit.addItem('Fill output, crop edges','cover');self.fit.addItem('Stretch to output dimensions','stretch')
        self.fit.setCurrentIndex(self.fit.findData(self.settings.fit));form.addRow('Image fit',self.fit)
        self.threshold=QSpinBox();self.threshold.setRange(0,255);self.threshold.setValue(self.settings.threshold)
        self.threshold.setToolTip('Binary masks paint pixels whose brightness reaches this threshold.')
        form.addRow('Brightness threshold',self.threshold)
        self.alpha_threshold=QSpinBox();self.alpha_threshold.setRange(0,255);self.alpha_threshold.setValue(self.settings.alpha_threshold)
        self.alpha_threshold.setToolTip('Transparent pixels leave the map unchanged. Fully transparent pixels are always skipped.')
        form.addRow('Minimum opacity',self.alpha_threshold)
        height_row=QHBoxLayout();self.minimum=QSpinBox();self.maximum=QSpinBox()
        for spin,value in ((self.minimum,self.settings.min_height),(self.maximum,self.settings.max_height)):
            spin.setRange(0,255);spin.setValue(value)
        height_row.addWidget(QLabel('Black →'));height_row.addWidget(self.minimum)
        height_row.addWidget(QLabel('White →'));height_row.addWidget(self.maximum)
        form.addRow('Map height range',height_row)
        self.invert=QCheckBox('Invert brightness before conversion');self.invert.setChecked(self.settings.invert)
        self.normalize=QCheckBox('Expand visible brightness to full contrast');self.normalize.setChecked(self.settings.normalize)
        form.addRow(self.normalize);form.addRow(self.invert);layout.addLayout(form)
        self.preview=QLabel();self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.preview.setMinimumHeight(160)
        layout.addWidget(self.preview,1)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        explanation=QLabel('Color images use luminance. Smaller outputs average source pixels; larger outputs use smooth interpolation. Height masks store actual values, including zero; transparency makes holes.');explanation.setWordWrap(True);layout.addWidget(explanation)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Continue')
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject);layout.addWidget(self.buttons)
        self.preview_timer=QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self.refresh_preview)
        for spin in (self.width_cells,self.height_cells,self.threshold,self.alpha_threshold,self.minimum,self.maximum):
            spin.valueChanged.connect(self.schedule_preview)
        for combo in (self.mode,self.fit):combo.currentIndexChanged.connect(self.schedule_preview)
        self.invert.toggled.connect(self.schedule_preview)
        self.normalize.toggled.connect(self.schedule_preview)
        self.refresh_preview()

    def current_settings(self):
        return ImageImportSettings(width=self.width_cells.value(),height=self.height_cells.value(),
            mode=self.mode.currentData(),threshold=self.threshold.value(),alpha_threshold=self.alpha_threshold.value(),
            invert=self.invert.isChecked(),normalize=self.normalize.isChecked(),min_height=self.minimum.value(),max_height=self.maximum.value(),fit=self.fit.currentData())

    def schedule_preview(self,*args):
        self.preview_timer.start()

    def refresh_preview(self):
        height=self.mode.currentData()=='height'
        self.threshold.setEnabled(not height);self.minimum.setEnabled(height);self.maximum.setEnabled(height)
        try:
            options=self.current_settings();pattern=PatternLibrary.load_image(self.path,options)
            cells=np.asarray(pattern.cells,dtype=np.uint8);active=cells!=0
            yy,xx=np.indices(cells.shape)
            checker=np.where((xx//8+yy//8)%2,50,70).astype(np.uint8)
            rgb=np.repeat(checker[...,None],3,axis=2)
            if pattern.is_height:
                values=np.asarray(pattern.heights,dtype=np.float32)
                lo,hi=pattern.height_range;levels=((values-lo)*255/max(1,hi-lo)).astype(np.uint8)
                rgb[active]=np.repeat(levels[...,None],3,axis=2)[active]
            else:rgb[active]=(160,205,183)
            image=QImage(rgb.data,rgb.shape[1],rgb.shape[0],rgb.strides[0],QImage.Format.Format_RGB888).copy()
            pixmap=QPixmap.fromImage(image).scaled(570,270,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation)
            self.preview.setPixmap(pixmap)
            count=int(active.sum())
            self.summary.setStyleSheet('')
            self.summary.setText('%d × %d cells · %s · %d painted / %d skipped%s' %
                (options.width,options.height,'Height mask' if height else 'Binary mask',count,int(active.size-count),
                 (' · heights %d–%d' % pattern.height_range) if height else ''))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            self.settings=options;self.pattern=pattern
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.pattern=None;self.preview.clear();self.summary.setStyleSheet('color:#e89786')
            self.summary.setText(str(error));self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def accept(self):
        self.preview_timer.stop();self.refresh_preview()
        if self.pattern is not None:super().accept()
