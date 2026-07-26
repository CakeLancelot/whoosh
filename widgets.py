from PIL import ImageOps
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QTextEdit, QVBoxLayout, QWidget, QPushButton, QSlider, QHBoxLayout, \
    QFileDialog
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from unitypack.object import ObjectInfo

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
        audio_bytes = obj.contents.audio_data
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        temp_file = _write_temp_audio(audio_bytes)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(temp_file))

        self.audio_info_label = QLabel(f"{obj.contents._obj.get('m_Name', 'Name unknown')}\n"
                                       f"Format: {obj.contents._obj.get('m_Format', 'Unknown')} ({_get_audio_format_name(obj.contents._obj['m_Format'])})\n"
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

    def export_object(self):
        if self.unity_object.contents._obj['m_Format'] == 5:
            file_filter = "OGG Vorbis File (*.ogg)"
        else:
            file_filter = "Raw PCM Audio (*.raw)"
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Exported Object", filter=file_filter)
        if filepath is None or filepath == '':
            return

        with open(filepath, 'wb') as output:
            output.write(self.unity_object.contents.audio_data)

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

    def export_object(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Exported Object", filter="JSON File (*.json)")
        if filepath is None or filepath == '':
            return
        with open(filepath, 'w') as output:
            json.dump(self.unity_object.contents, output, indent=4, default=str)


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
        self.unity_object = obj
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

    def export_object(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Exported Object", filter="PNG Image (*.png)")
        if filepath is None or filepath == '':
            return

        with open(filepath, 'wb') as output:
            try:
                image = self.unity_object.contents.image
            except NotImplementedError:
                print("Texture format not implemented. Could not export.")
                return
            image = ImageOps.flip(image)
            image.save(output, format="png")
