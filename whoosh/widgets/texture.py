from PIL import ImageOps
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QBrush, QColor
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget, QFileDialog

from unitypack.object import ObjectInfo
from unitypack.engine.texture import TextureFormat


def PIL_to_qimage(pil_img) -> QImage:
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
