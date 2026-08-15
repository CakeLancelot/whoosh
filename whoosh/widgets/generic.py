import json

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QToolBar, QVBoxLayout, QWidget, QFileDialog

from unitypack.object import ObjectInfo

from whoosh.widgets.text_repr import ObjectTextReprWidget
from whoosh.widgets.dict_tree import ObjectDictTreeWidget


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
