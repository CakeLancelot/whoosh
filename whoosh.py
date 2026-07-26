from widgets import AudioPlayerWidget, GenericObjectView, TextureViewWidget
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTreeView, QFrame,
    QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView, QVBoxLayout, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt, QUrl, QSortFilterProxyModel
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem, QKeySequence, QDesktopServices, QIcon
import os
import re
import unitypack
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment

import signal
import sys

def extract_shader_name(script: str) -> str:
    try:
        return re.findall('"([^"]*)"', script)[0]
    except IndexError:
        return ""

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
        self.current_asset_dirty = False
        self.current_env = None
        self.export_function = None

        self.setWindowTitle("whoosh")
        self.resize(800, 600)

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

        self.save_action = QAction("&Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_asset)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("&Save as...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self.save_asset_as)
        self.save_as_action.setEnabled(False)
        file_menu.addAction(self.save_as_action)

        file_menu.addSeparator()

        set_env_action = QAction("Set Unity&Environment...", self)
        set_env_action.triggered.connect(self.set_env)
        file_menu.addAction(set_env_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        asset_menu = menu_bar.addMenu("&Asset")

        self.properties_action = QAction("&Properties", self)
        self.properties_action.triggered.connect(self.show_asset_properties)
        self.properties_action.setEnabled(False)
        asset_menu.addAction(self.properties_action)

        self.references_action = QAction("&References", self)
        self.references_action.triggered.connect(self.show_asset_references)
        self.references_action.setEnabled(False)
        asset_menu.addAction(self.references_action)

        object_menu = menu_bar.addMenu("&Object")

        self.replace_action = QAction("Replace...", self)
        self.replace_action.triggered.connect(self.replace_object)
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

        # Proxy model for filtering by name
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.tree_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(1)  # Filter by Name column
        self.tree_view.setModel(self.proxy_model)

        self.tree_view.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree_view.header().setDefaultSectionSize(100)
        self.tree_view.header().resizeSection(0, 65)
        self.tree_view.header().resizeSection(1, 175)
        #self.tree_view.setSortingEnabled(True)

        # Search line edit
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.textChanged.connect(self.proxy_model.setFilterFixedString)

        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search_edit)
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

    def save_asset(self):
        if self.current_asset is None or not self.current_asset_dirty:
            return
        pass

    def save_asset_as(self):
        pass

    def show_asset_properties(self):
        if self.current_asset is None:
            return

        properties = {
            "Name": self.current_asset.name,
            "Types": "\n".join(f"{type_id}: {obj}" for type_id, obj in self.current_asset.types.items()),
            "Long object IDs": self.current_asset.long_object_ids,
            "Objects Count": len(self.current_asset.objects),
        }

        properties_str = "\n\n".join(f"{key}: {value}" for key, value in properties.items())
        self.display_in_right_frame(properties_str)

    def show_asset_references(self):
        if self.current_asset is None:
            return

        references_str = "\n".join(f"{i}: {str(ref)}" for i, ref in enumerate(self.current_asset.asset_refs))
        self.display_in_right_frame(references_str)

    def _load_asset_file(self, filepath: str):
        self.tree_view.clearSelection()
        self.clear_right_frame()
        self.current_file = open(filepath, 'rb')

        compressed_suffixes = ('.unity3d', '.resourceFile', '.assetbundle')
        if self.current_file.name.endswith(compressed_suffixes):
            self.current_asset = unitypack.load(self.current_file).assets[0]
        else:
            if self.current_env is not None:
                self.current_asset = Asset.from_file(self.current_file, UnityEnvironment(self.current_env))
            else:
                self.current_asset = Asset.from_file(self.current_file)

        self.tree_model.removeRows(0, self.tree_model.rowCount())
        self.search_edit.clear()

        ignored_assets = set()
        try:
            for index, obj in self.current_asset.objects.items():
                try:
                    name = ""
                    if hasattr(obj._read(), "name") and obj._read().name not in (None, ""):
                        name = obj._read().name
                    elif obj.class_id == 48 and hasattr(obj._read(), "script"):
                        name = extract_shader_name(obj._read().script)
                    elif hasattr(obj._read(), "_obj") and "m_Name" in obj._read()._obj.keys():
                        name = obj._read()._obj["m_Name"]
                    elif hasattr(obj._read(), "keys") and "m_Name" in obj._read().keys():
                        name = obj._read()["m_Name"]
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

        self.setWindowTitle(f"{os.path.basename(self.current_asset.name)} - whoosh")
        self.properties_action.setEnabled(True)
        self.references_action.setEnabled(True)

    def set_env(self):
        self.current_env = QFileDialog.getExistingDirectory(self, "Select UnityEnvironment Directory")

    def select_object(self, selected, _):
        indexes = selected.indexes()
        if not indexes:
            return
        index = indexes[0]

        self.clear_right_frame()

        # Map proxy index back to source model index
        source_index = self.proxy_model.mapToSource(index)
        index_str = self.tree_model.item(source_index.row(), 0).text()

        if not index_str:
            return

        obj = self.current_asset.objects[int(index_str)]

        if obj.class_id == 28:
            widget_to_add = TextureViewWidget(obj)
        elif obj.class_id == 83:
            widget_to_add = AudioPlayerWidget(obj)
        else:
            widget_to_add = GenericObjectView(obj)

        self.right_layout.addWidget(widget_to_add)

        if hasattr(widget_to_add, "export_object") and callable(widget_to_add.export_object):
            self.export_function = widget_to_add.export_object
            self.export_action.setEnabled(True)
        else:
            self.export_action.setEnabled(False)

    def display_in_right_frame(self, string: str):
        self.tree_view.clearSelection()

        self.export_action.setEnabled(False)
        self.replace_action.setEnabled(False)

        self.clear_right_frame()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(string)
        self.right_layout.addWidget(text_edit)

    def export_object(self):
        if self.export_function is not None:
            result = self.export_function()

    def replace_object(self):
        pass

    def clear_right_frame(self):
        while self.right_layout.count():
            child = self.right_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

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

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.isfile(filepath):
            window._load_asset_file(filepath)
        else:
            QMessageBox.critical(window, "Error", f"File not found: {filepath}")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
