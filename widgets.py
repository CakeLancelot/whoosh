from PIL import ImageOps
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter, QBrush, QColor
from PySide6.QtWidgets import (
    QLabel, QScrollArea, QTextEdit, QVBoxLayout, QWidget, QPushButton, QSlider, QHBoxLayout,
    QFileDialog, QTreeView, QHeaderView, QToolBar,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from unitypack.object import ObjectInfo
from unitypack.engine.texture import TextureFormat

import os
import json
import tempfile

def _get_audio_format_name(value: int) -> str:
    # The formats built into UPFF are too new
    match value:
        case 1: return "PCM8 Mono"
        case 2: return "PCM8 Stereo"
        case 3: return "PCM16 Mono"
        case 4: return "PCM16 Stereo"
        case 5: return "OGG Vorbis"
        case _: return "Undocumented - please report"


def _write_temp_audio(audio_data: bytes) -> str:
    """Write audio bytes to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(audio_data)
        return tmp.name

# TODO: Test if formats other than OGG work.
class AudioPlayerWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        self.unity_object = obj
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        temp_file = _write_temp_audio(self.unity_object.contents.audio_data)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(temp_file))

        self.audio_info_label = QLabel(f"{self.unity_object.contents._obj.get('m_Name', 'Name unknown')}\n"
                                       f"Format: {self.unity_object.contents._obj.get('m_Format', 'Unknown')} ({_get_audio_format_name(self.unity_object.contents._obj['m_Format'])})\n"
                                       f"Sample Rate: {self.unity_object.contents._obj.get('m_Frequency', 'Unknown')} Hz\n"
                                       f"Size: {self.unity_object.contents._obj.get('m_Size', 'Unknown')} bytes\n"
                                       f"Decompress on Load: {self.unity_object.contents._obj.get('m_DecompressOnLoad', 'Unknown')}")

        # Progress slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.slider.sliderMoved.connect(self._on_slider_moved)

        # Control buttons
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._toggle_play_pause)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.player.stop)
        btn_layout.addWidget(self.play_btn)
        btn_layout.addWidget(self.stop_btn)

        # Time labels
        time_layout = QHBoxLayout()
        self.pos_label = QLabel("00:00")
        self.dur_label = QLabel("00:00")
        time_layout.addWidget(self.pos_label)
        time_layout.addStretch()
        time_layout.addWidget(self.dur_label)

        layout.addWidget(self.audio_info_label)
        layout.addLayout(btn_layout)
        layout.addWidget(self.slider)
        layout.addStretch()
        layout.addLayout(time_layout)

        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def _format_time(self, ms: int) -> str:
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def _on_position_changed(self, pos: int):
        self.slider.setValue(pos)
        self.pos_label.setText(self._format_time(pos))

    def _on_duration_changed(self, dur: int):
        self.slider.setRange(0, dur)
        self.dur_label.setText(self._format_time(dur))

    def _on_slider_moved(self, val: int):
        self.player.setPosition(val)

    def _toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶ Play")
        else:
            self.player.play()
            self.play_btn.setText("⏸ Pause")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_btn.setText("▶ Play")

    def closeEvent(self, event):
        self.player.stop()
        # Clean up temp file
        source = self.player.source().toLocalFile()
        if source and os.path.exists(source):
            os.remove(source)
        self.unity_object = None
        super().closeEvent(event)

    def export_object(self) -> bool:
        if self.unity_object.contents._obj['m_Format'] == 5:
            file_filter = "OGG Vorbis File (*.ogg)"
        else:
            file_filter = "Raw PCM Audio (*.raw)"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Exported Object", filter=file_filter)
        if filepath is None or filepath == '':
            return False

        with open(filepath, 'wb') as output:
            output.write(self.unity_object.contents.audio_data)
        return True

class ObjectTextReprWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        self.unity_object = obj
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        if hasattr(obj.contents, "_obj"):
            text_edit.setPlainText(json.dumps(obj.contents._obj, indent=4, default=str))
        else:
            text_edit.setPlainText(json.dumps(obj.contents, indent=4, default=str))
        layout.addWidget(text_edit)

    def closeEvent(self, event):
            self.unity_object = None
            super().closeEvent(event)

class ObjectDictTreeWidget(QWidget):
    """Displays the object's dictionary as a collapsible tree view."""

    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        self.unity_object = obj
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree_view = QTreeView()
        self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Key", "Value"])

        if hasattr(obj.contents, "_obj"):
            data = obj.contents._obj
        else:
            data = obj.contents

        ObjectDictTreeWidget._populate_model(model, data)
        self.tree_view.setModel(model)
        #self.tree_view.expandAll()

        layout.addWidget(self.tree_view)

    def closeEvent(self, event):
        self.unity_object = None
        super().closeEvent(event)

    @staticmethod
    def _populate_model(model: QStandardItemModel, data, parent: QStandardItem | None = None):
        """Recursively populate a QStandardItemModel from a dict/list structure."""
        if isinstance(data, dict):
            for key, value in data.items():
                key_item = QStandardItem(str(key))
                if isinstance(value, dict):
                    val_item = QStandardItem("[nested dict]")
                    ObjectDictTreeWidget._populate_model(model, value, key_item)
                elif isinstance(value, list):
                    val_item = QStandardItem(f"[list: {len(value)} items]")
                    ObjectDictTreeWidget._populate_model(model, value, key_item)
                else:
                    val_item = QStandardItem(ObjectDictTreeWidget._format_value(value))
                if parent is None:
                    model.appendRow([key_item, val_item])
                else:
                    parent.appendRow([key_item, val_item])
        elif isinstance(data, list):
            for idx, value in enumerate(data):
                key_item = QStandardItem(f"[{idx}]")
                if isinstance(value, (dict, list)):
                    val_item = QStandardItem(
                        f"[nested {'dict' if isinstance(value, dict) else 'list'}]"
                    )
                    ObjectDictTreeWidget._populate_model(model, value, key_item)
                else:
                    val_item = QStandardItem(ObjectDictTreeWidget._format_value(value))
                if parent is None:
                    model.appendRow([key_item, val_item])
                else:
                    parent.appendRow([key_item, val_item])
        else:
            val_item = QStandardItem(ObjectDictTreeWidget._format_value(data))
            if parent is None:
                model.appendRow([QStandardItem("<root>"), val_item])
            else:
                parent.appendRow([QStandardItem("<root>"), val_item])

    @staticmethod
    def _format_value(value) -> str:
        """Format a scalar value for display."""
        if value is None:
            return "<None>"
        if isinstance(value, bool):
            return str(value)
        return str(value)

class GenericObjectView(QWidget):
    """A widget that displays an object with a toolbar to switch between Text and Tree views."""
    
    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        self.unity_object = obj

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Toolbar for switching views
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        self.action_tree = QAction("Tree", self)
        self.action_tree.setToolTip("View as tree structure")
        self.action_tree.triggered.connect(self._show_tree_view)

        self.action_text = QAction("Text", self)
        self.action_text.setToolTip("View as text representation")
        self.action_text.triggered.connect(self._show_text_view)

        self.toolbar.addWidget(QLabel("View as: "))
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_tree)
        self.toolbar.addAction(self.action_text)

        self.current_widget = None

        layout.addWidget(self.toolbar)

        # Default to tree view
        self._show_tree_view()

    def _switch_widget(self, new_widget: QWidget):
        if self.current_widget is not None:
            # Remove the current widget from the layout
            index = self.layout().indexOf(self.current_widget)
            if index != -1:
                self.layout().removeWidget(self.current_widget)
                self.current_widget.hide()

        self.current_widget = new_widget
        self.layout().addWidget(new_widget)
        new_widget.show()

    def _show_text_view(self):
        self._switch_widget(ObjectTextReprWidget(self.unity_object))
        self.action_text.setEnabled(False)
        self.action_tree.setEnabled(True)

    def _show_tree_view(self):
        self._switch_widget(ObjectDictTreeWidget(self.unity_object))
        self.action_text.setEnabled(True)
        self.action_tree.setEnabled(False)

    def export_object(self) -> bool:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Exported Object", filter="JSON File (*.json)"
        )
        if filepath is None or filepath == "":
            return False
        with open(filepath, "w") as output:
            if hasattr(self.unity_object.contents, "_obj"):
                json.dump(self.unity_object.contents._obj, output, indent=4, default=str)
            else:
                json.dump(self.unity_object.contents, output, indent=4, default=str)
        return True

    def closeEvent(self, event):
        self.unity_object = None
        super().closeEvent(event)

def PIL_to_qimage(pil_img):
    temp = pil_img.convert('RGBA')
    return QImage(
        temp.tobytes('raw', "RGBA"),
        temp.size[0],
        temp.size[1],
        QImage.Format.Format_RGBA8888
    )

def create_checkerboard_pixmap(image_pixmap: QPixmap, tile_size: int = 10) -> QPixmap:
    """Create a pixmap with a checkerboard background and the image composited on top."""
    combined = QPixmap(image_pixmap.size())
    painter = QPainter(combined)
    white = QColor(255, 255, 255)
    gray = QColor(192, 192, 192)
    for y in range(0, combined.height(), tile_size):
        for x in range(0, combined.width(), tile_size):
            row = y // tile_size
            col = x // tile_size
            color = white if (row + col) % 2 == 0 else gray
            painter.fillRect(x, y, tile_size, tile_size, QBrush(color))
    painter.drawPixmap(0, 0, image_pixmap)
    painter.end()
    return combined

class TextureViewWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        self.unity_object = obj
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        from PIL import ImageOps
        img = ImageOps.flip(obj.contents.image)
        q_img = PIL_to_qimage(img)
        pixmap = QPixmap.fromImage(q_img)
        checkerboard_pixmap = create_checkerboard_pixmap(pixmap)
        label = QLabel()
        label.setPixmap(checkerboard_pixmap)
        scroll_area = QScrollArea()
        scroll_area.setWidget(label)
        layout.addWidget(scroll_area)
        status_bar = QLabel(
            f"{obj.contents.width}x{obj.contents.height}px "
            f"{TextureFormat(obj.contents.format).name} "
            f"{obj.contents._obj['m_CompleteImageSize']} bytes"
        )
        status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_bar)

    def closeEvent(self, event):
        self.unity_object = None
        super().closeEvent(event)

    def export_object(self) -> bool:
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Exported Object", filter="PNG Image (*.png)")
        if filepath is None or filepath == '':
            return False

        with open(filepath, 'wb') as output:
            try:
                image = self.unity_object.contents.image
            except NotImplementedError:
                print("Texture format not implemented. Could not export.")
                return False
            image = ImageOps.flip(image)
            image.save(output, format="png")
        return True