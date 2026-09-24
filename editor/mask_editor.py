"""Pixel-mask editor. Edits stay in memory until Save or Save As succeeds."""
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt,QRect
from PySide6.QtGui import QImage,QPainter,QColor,QPen
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,
    QLabel,QLineEdit,QSpinBox,QPushButton,QScrollArea,QDialogButtonBox,QMessageBox,QSlider)
from .patterns import Pattern


class MaskCanvas(QWidget):
    def __init__(self, pattern):
        super().__init__()
        self.cells=np.zeros((120,120),dtype=np.uint8)
        source=np.asarray(pattern.cells,dtype=np.uint8)
        self.rows,self.columns=source.shape
        self.cells[:self.rows,:self.columns]=source
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
        rgb[:]=(28,37,43);rgb[self.cells[:self.rows,:self.columns]!=0]=(160,205,183)
        image=QImage(rgb.data,self.columns,self.rows,rgb.strides[0],QImage.Format.Format_RGB888).copy()
        painter.drawImage(QRect(0,0,self.columns*self.pixel_size,self.rows*self.pixel_size),image)
        if self.pixel_size<4:return
        painter.setPen(QPen(QColor('#52616b'),1))
        for x in range(self.columns+1): painter.drawLine(x*self.pixel_size,0,x*self.pixel_size,self.height())
        for y in range(self.rows+1): painter.drawLine(0,y*self.pixel_size,self.width(),y*self.pixel_size)

    def cell_at(self,event):
        return int(event.position().x())//self.pixel_size,int(event.position().y())//self.pixel_size

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        x,y=self.cell_at(event)
        if 0<=x<self.columns and 0<=y<self.rows:
            self.paint_value=1-int(self.cells[y,x]);self.cells[y,x]=self.paint_value;self.update()

    def mouseMoveEvent(self,event):
        if self.paint_value is None or not event.buttons()&Qt.MouseButton.LeftButton:return
        x,y=self.cell_at(event)
        if 0<=x<self.columns and 0<=y<self.rows:
            self.cells[y,x]=self.paint_value;self.update()

    def mouseReleaseEvent(self,event): self.paint_value=None


class MaskEditor(QDialog):
    def __init__(self,parent,library,pattern,path=None):
        super().__init__(parent)
        self.library=library;self.path=Path(path) if path else None;self.saved_path=None
        self.setWindowTitle('Edit mask — '+pattern.name)
        self.resize(760,650)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('Click to toggle a pixel; drag to paint or erase. Increase rows/columns to expand the canvas.'))
        form=QFormLayout();self.name=QLineEdit(pattern.name);self.tags=QLineEdit(', '.join(pattern.tags))
        self.name.setReadOnly(self.path is not None)
        self.tags.setPlaceholderText('letters, symbols')
        form.addRow('Name',self.name);form.addRow('Tags',self.tags);layout.addLayout(form)
        self.canvas=MaskCanvas(pattern)
        row=QHBoxLayout();self.columns=QSpinBox();self.rows=QSpinBox()
        for spin,value in ((self.columns,self.canvas.columns),(self.rows,self.canvas.rows)):
            spin.setRange(1,120);spin.setValue(value);spin.setKeyboardTracking(False)
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
        layout.addWidget(QLabel('1–120 rows and columns. Save uses the app mask folder; Save As keeps the original.'))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject)
        save_as=buttons.addButton('Save As…',QDialogButtonBox.ButtonRole.ActionRole);save_as.clicked.connect(self.save_as)
        layout.addWidget(buttons)
        self.initial_state=self.edit_state()

    def edit_state(self):
        return (self.name.text(),self.tags.text(),self.columns.value(),self.rows.value(),
                self.canvas.cells[:self.rows.value(),:self.columns.value()].tobytes())

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
        area=self.canvas.cells[:self.rows.value(),:self.columns.value()]
        area[:]=1-area;self.canvas.update()

    def pattern(self,name,tags):
        cells=self.canvas.cells[:self.rows.value(),:self.columns.value()]
        return Pattern(name.strip(),tuple(tuple(int(v) for v in row) for row in cells),
                       tuple(t.strip() for t in tags.split(',') if t.strip()))

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
