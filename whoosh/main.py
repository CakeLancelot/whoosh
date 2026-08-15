import os
import signal
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from whoosh.window import WhooshWindow


def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Dev: res/ lives in the project root, the parent of the whoosh package
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "res")
    return os.path.join(base_path, relative_path)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('WhooshIcon.ico')))
    window = WhooshWindow()
    window.app = app

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
