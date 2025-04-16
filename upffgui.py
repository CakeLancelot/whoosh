import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from PIL import ImageTk, ImageOps
import json
import os
import re
import unitypack
from unitypack.asset import Asset
from unitypack.environment import UnityEnvironment

current_file = None
current_asset = None
current_env = None

def open_asset(root, tree_view):
    global current_file
    global current_asset
    global current_env
    filepath = filedialog.askopenfilename()
    if filepath == "":
        return

    current_file = open(filepath, 'rb')

    compressed_suffixes = ('.unity3d', '.resourceFile', '.assetbundle')
    if current_file.name.endswith(compressed_suffixes):
        current_asset = unitypack.load(current_file).assets[0]
    else:
        if current_env is not None:
            current_asset = Asset.from_file(current_file, UnityEnvironment(current_env))
        else:
            current_asset = Asset.from_file(current_file)

    root.title(f"{os.path.basename(current_asset.name)} - UnityPackFF GUI")
    tree_view.delete(*tree_view.get_children())

    ignored_assets = set()
    for index, obj in current_asset.objects.items():
        try:
            name = ""
            if hasattr(obj.contents, "name"):
                name = obj.contents.name
            tree_view.insert("", "end", text=index, values=(index, name, obj.type))
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
                tk.messagebox.showerror("Missing asset", message)
            else:
                raise


def set_env():
    global current_env
    current_env = filedialog.askdirectory()

def select_object(event, tree_view, right_frame):
    global current_asset
    for child in right_frame.winfo_children():
        child.destroy()

    item = tree_view.item(tree_view.focus())
    if item['text'] == '':
        return
    obj = current_asset.objects[item['text']]

    if (obj.class_id == 28):
        canvas = tk.Canvas(right_frame, width=obj.contents.width, height=obj.contents.height)
        canvas.image =  ImageTk.PhotoImage(ImageOps.flip(obj.contents.image))
        canvas.pack(fill=tk.BOTH)
        canvas.create_image(obj.contents.width / 2, obj.contents.height / 2, image=canvas.image)
    else:
        text = scrolledtext.ScrolledText(right_frame)
        if hasattr(obj.contents, "_obj"):
            text.insert(tk.END, json.dumps(obj.contents._obj, indent=4, default=str))
        else:
            text.insert(tk.END, json.dumps(obj.contents, indent=4, default=str))
        text.config(state=tk.DISABLED)
        text.pack(expand=True, fill=tk.BOTH)


def main():
    root = tk.Tk()
    root.title("UnityPackFF GUI")
    root.geometry("640x480")

    paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    left_frame = ttk.Frame(paned_window, width=100)
    paned_window.add(left_frame, weight=1)

    tree_view = ttk.Treeview(left_frame, selectmode=tk.BROWSE)
    tree_view["columns"] = ("1", "2", "3")
    tree_view['show'] = 'headings'
    tree_view.heading("1", text="Index")
    tree_view.column("1", minwidth=0, width=50)
    tree_view.heading("2", text="Name")
    tree_view.column("2", minwidth=0, width=100)
    tree_view.heading("3", text="Type")
    tree_view.column("3", minwidth=0, width=100)
    tree_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb = ttk.Scrollbar(left_frame, orient="vertical", command=tree_view.yview)
    vsb.pack(side='right', fill='y')
    tree_view.configure(yscrollcommand=vsb.set)

    right_frame = ttk.Frame(paned_window)
    paned_window.add(right_frame, weight=8)

    tree_view.bind("<<TreeviewSelect>>", lambda event: select_object(event, tree_view, right_frame))

    menu_bar = tk.Menu(root)
    file_menu = tk.Menu(menu_bar, tearoff=False)
    menu_bar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Open...", command=lambda: open_asset(root, tree_view), accelerator="Ctrl+O")
    file_menu.add_command(label="Set UnityEnvironment...", command=lambda: set_env())
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit, accelerator="Ctrl+Q")

    root.bind_all("<Control-q>", lambda event: root.quit())
    root.bind_all("<Control-o>", lambda event: open_asset(root, tree_view))
    root.config(menu=menu_bar)
    root.mainloop()


if __name__ == "__main__":
    main()
