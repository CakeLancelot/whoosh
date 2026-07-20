from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QTextEdit, QVBoxLayout, QWidget, QPushButton, QSlider, QHBoxLayout
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from unitypack.object import ObjectInfo

import os
import json
import tempfile

def _write_temp_audio(audio_data: bytes) -> str:
    """Write audio bytes to a temporary file and return the path."""
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(audio_data)
    tmp.close()
    return tmp.name

# TODO: Test if formats other than OGG work.
class AudioPlayerWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        audio_bytes = obj.contents._obj.get("audio data", b"")
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        temp_file = _write_temp_audio(audio_bytes)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(temp_file))

        self.audio_info_label = QLabel(f"{obj.contents._obj.get('m_Name', 'Name unknown')}\n"
                                       f"Format: {obj.contents._obj.get('m_Format', 'Unknown')}\n"
                                       f"Sample Rate: {obj.contents._obj.get('m_Frequency', 'Unknown')} Hz\n"
                                       f"Size: {obj.contents._obj.get('m_Size', 'Unknown')} bytes\n"
                                       f"Decompress on Load: {obj.contents._obj.get('m_DecompressOnLoad', 'Unknown')}")

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
        super().closeEvent(event)


class ObjectTextReprWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        if hasattr(obj.contents, "_obj"):
            text_edit.setPlainText(json.dumps(obj.contents._obj, indent=4, default=str))
        else:
            text_edit.setPlainText(json.dumps(obj.contents, indent=4, default=str))
        layout.addWidget(text_edit)


def PIL_to_qimage(pil_img):
    temp = pil_img.convert('RGBA')
    return QImage(
        temp.tobytes('raw', "RGBA"),
        temp.size[0],
        temp.size[1],
        QImage.Format.Format_RGBA8888
    )


class TextureViewWidget(QWidget):
    def __init__(self, obj: ObjectInfo, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        from PIL import ImageOps
        img = ImageOps.flip(obj.contents.image)
        q_img = PIL_to_qimage(img)
        pixmap = QPixmap.fromImage(q_img)
        label = QLabel()
        label.setPixmap(pixmap)
        scroll_area = QScrollArea()
        scroll_area.setWidget(label)
        layout.addWidget(scroll_area)
