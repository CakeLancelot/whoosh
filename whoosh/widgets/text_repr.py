import json

from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from unitypack.object import ObjectInfo


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
