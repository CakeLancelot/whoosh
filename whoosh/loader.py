import re

from PySide6.QtCore import QThread, Signal


def extract_shader_name(script: str) -> str:
    try:
        return re.findall('"([^"]*)"', script)[0]
    except IndexError:
        return ""


class AssetLoaderThread(QThread):
    """Worker thread for building the tree model without blocking the UI."""
    row_ready = Signal(str, str, str)
    warning = Signal(str, str)
    error = Signal(str, str)
    finished_loading = Signal()

    def __init__(self, asset):
        super().__init__()
        self.asset = asset

    def run(self):
        ignored_assets = set()
        try:
            for index, obj in self.asset.objects.items():
                try:
                    name = ""
                    contents = obj._read()
                    if hasattr(contents, "name") and contents.name not in (None, ""):
                        name = contents.name
                    elif obj.class_id == 48 and hasattr(contents, "script"):
                        name = extract_shader_name(contents.script)
                    elif hasattr(contents, "_obj") and "m_Name" in contents._obj.keys():
                        name = contents._obj["m_Name"]
                    elif hasattr(contents, "keys") and "m_Name" in contents.keys():
                        name = contents["m_Name"]
                    self.row_ready.emit(str(index), str(name), str(obj.type))
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
                        self.warning.emit("Missing asset", message)
                    else:
                        self.error.emit("Error", f"Failed to load the specified asset (during object reading)\n\n{str(err)[:500]}")
        except Exception as err:
            self.error.emit("Error", f"Failed to load the specified asset file (during object enumeration)\n\n{str(err)[:500]}")
        finally:
            self.finished_loading.emit()
