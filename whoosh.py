from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTreeView, QFrame,
    QFileDialog, QMessageBox, QTextEdit, QLabel, QHeaderView,
    QMenuBar, QMenu, QAbstractItemView, QVBoxLayout, QScrollArea
)
from PySide6.QtCore import Qt, QStandardPaths, QByteArray
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem, QKeySequence, QImage, QPixmap
import json
import os
import re
import unitypack
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment

import sys

def PIL_to_qimage(pil_img):
    temp = pil_img.convert('RGBA')
    return QImage(
        temp.tobytes('raw', "RGBA"),
        temp.size[0],
        temp.size[1],
        QImage.Format.Format_RGBA8888
    )

class WhooshWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.current_asset = None
        self.current_env = None

        self.setWindowTitle("whoosh")
        self.resize(640, 480)

        self._setup_menu()
        self._setup_ui()

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_asset)
        file_menu.addAction(open_action)

        set_env_action = QAction("Set Unity&Evironment...", self)
        set_env_action.triggered.connect(self.set_env)
        file_menu.addAction(set_env_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Left frame with tree view
        left_frame = QFrame()
        self.tree_view = QTreeView()
        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.tree_model = QStandardItemModel(0, 3)
        self.tree_model.setHorizontalHeaderLabels(["Index", "Name", "Type"])
        self.tree_view.setModel(self.tree_model)

        self.tree_view.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree_view.header().setDefaultSectionSize(100)
        self.tree_view.header().resizeSection(0, 50)
        self.tree_view.header().resizeSection(1, 150)

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.tree_view)

        # Right frame for details
        self.right_frame = QFrame()
        self.right_layout = QVBoxLayout(self.right_frame)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        splitter.addWidget(left_frame)
        splitter.addWidget(self.right_frame)

        splitter.setSizes([300, 340])

        self.tree_view.clicked.connect(self.select_object)

    def open_asset(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Asset File")
        if not filepath:
            return

        self.current_file = open(filepath, 'rb')

        compressed_suffixes = ('.unity3d', '.resourceFile', '.assetbundle')
        if self.current_file.name.endswith(compressed_suffixes):
            self.current_asset = unitypack.load(self.current_file).assets[0]
        else:
            if self.current_env is not None:
                self.current_asset = Asset.from_file(self.current_file, UnityEnvironment(self.current_env))
            else:
                self.current_asset = Asset.from_file(self.current_file)

        self.setWindowTitle(f"{os.path.basename(self.current_asset.name)} - whoosh")

        self.tree_model.removeRows(0, self.tree_model.rowCount())

        ignored_assets = set()
        for index, obj in self.current_asset.objects.items():
            try:
                name = ""
                if hasattr(obj.contents, "name"):
                    name = obj.contents.name
                index_item = QStandardItem(str(index))
                name_item = QStandardItem(str(name))
                type_item = QStandardItem(str(obj.type))
                self.tree_model.appendRow([index_item, name_item, type_item])
            except KeyError as err:
                if "No such asset:" in err.args[0]:
                    missing_asset = re.search(r"'([^']*)'", err.args[0]).group(1)
                    if missing_asset in ignored_assets:
                        continue
                    else:
                        ignored_assets.add(missing_asset)
                    message = (f"This asset depends on the file \"{missing_asset}\", but it was not found.\n\n"
                               "You may need to copy the missing file into the same directory, "
                               "or set your UnityEnvironment under the \"File\" menu.\n"
                               "The file can still be read, but certain objects will be "
                               "excluded from the list until the issue is corrected.")
                    QMessageBox.critical(self, "Missing asset", message)
                else:
                    raise

    def set_env(self):
        self.current_env = QFileDialog.getExistingDirectory(self, "Select UnityEnvironment Directory")

    def select_object(self, index):
        if not index.isValid():
            return

        # Clear right frame
        while self.right_layout.count():
            child = self.right_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        row = index.row()
        index_str = self.tree_model.item(row, 0).text()

        if not index_str:
            return

        obj = self.current_asset.objects[int(index_str)]

        if obj.class_id == 28:
            # Display image
            from PIL import ImageOps
            img = ImageOps.flip(obj.contents.image)
            q_img = PIL_to_qimage(img)
            pixmap = QPixmap.fromImage(q_img)
            label = QLabel()
            label.setPixmap(pixmap)
            scroll_area = QScrollArea()
            scroll_area.setWidget(label)
            self.right_layout.addWidget(scroll_area)
        else:
            # Display JSON
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            if hasattr(obj.contents, "_obj"):
                text_edit.setPlainText(json.dumps(obj.contents._obj, indent=4, default=str))
            else:
                text_edit.setPlainText(json.dumps(obj.contents, indent=4, default=str))
            self.right_layout.addWidget(text_edit)


def main():
    app = QApplication(sys.argv)
    window = WhooshWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
