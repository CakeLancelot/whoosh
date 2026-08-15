from PySide6.QtWidgets import QTreeView, QHeaderView, QVBoxLayout, QWidget
from PySide6.QtGui import QStandardItemModel, QStandardItem

from unitypack.object import ObjectInfo


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
