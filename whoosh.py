from widgets import AudioPlayerWidget, ObjectTextReprWidget, TextureViewWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTreeView, QFrame,
    QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView, QVBoxLayout
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem, QKeySequence, QDesktopServices, QIcon
import os
import re
import unitypack
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment

import signal
import sys


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath("./res")
    return os.path.join(base_path, relative_path)

class WhooshWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.current_asset = None
        self.current_env = None
        self.export_function = None

        self.setWindowTitle("whoosh")
        self.resize(640, 480)

        self._setup_menu()
        self._setup_ui()
        self._setup_drag_and_drop()

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_asset)
        file_menu.addAction(open_action)

        set_env_action = QAction("Set Unity&Environment...", self)
        set_env_action.triggered.connect(self.set_env)
        file_menu.addAction(set_env_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        object_menu = menu_bar.addMenu("&Object")

        self.replace_action = QAction("Replace...", self)
        self.replace_action.triggered.connect(self.export_object)
        self.replace_action.setEnabled(False)
        object_menu.addAction(self.replace_action)

        self.export_action = QAction("Export...", self)
        self.export_action.triggered.connect(self.export_object)
        self.export_action.setEnabled(False)
        object_menu.addAction(self.export_action)

        help_menu = menu_bar.addMenu("&Help")

        repo_action = QAction("GitHub Page", self)
        repo_action.triggered.connect(self.open_repo)
        help_menu.addAction(repo_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

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
        #self.tree_view.setSortingEnabled(True)

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

        self.tree_view.selectionModel().selectionChanged.connect(self.select_object)

    def _setup_drag_and_drop(self):
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        filepath = urls[0].toLocalFile()
        
        if os.path.isfile(filepath):
            self._load_asset_file(filepath)

    def open_asset(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Asset File")
        if not filepath:
            return
        self._load_asset_file(filepath)

    def _load_asset_file(self, filepath: str):
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
        try:
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
                        QMessageBox.critical(self, "Error", f"Failed to load the specified asset file\n\n{str(err)[:500]}")
        except Exception as err:
            QMessageBox.critical(self, "Error", f"Failed to load the specified asset file\n\n{str(err)[:500]}")

    def set_env(self):
        self.current_env = QFileDialog.getExistingDirectory(self, "Select UnityEnvironment Directory")

    def select_object(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes:
            return
        index = indexes[0]

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
            widget_to_add = TextureViewWidget(obj)
        elif obj.class_id == 83:
            widget_to_add = AudioPlayerWidget(obj)
        else:
            widget_to_add = ObjectTextReprWidget(obj)

        self.right_layout.addWidget(widget_to_add)

        if hasattr(widget_to_add, "export_object") and callable(widget_to_add.export_object):
            self.export_function = widget_to_add.export_object
            self.export_action.setEnabled(True)
        else:
            self.export_action.setEnabled(False)

    def export_object(self):
        if self.export_function is not None:
            self.export_function()

    def open_repo(self):
        QDesktopServices.openUrl(QUrl("https://github.com/cakeLancelot/whoosh"))

    def about(self):
        QMessageBox.about(self, "About whoosh", "whoosh v0.1\n\n"
                                                "The alpha asset viewer for Unity 2.x - 3.x files.\n"
                                                "Built with PySide6 and UnityPackFF.\n\n")

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('WhooshIcon.ico')))
    window = WhooshWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
