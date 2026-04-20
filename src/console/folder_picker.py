import os
import tkinter as tk
from tkinter import filedialog


def pick_folder() -> str | None:
    """Pop up a GUI folder picker dialog and return the selected path"""
    root = tk.Tk()
    root.withdraw()

    initial_dir = os.getcwd()
    if os.name == "nt":
        initial_dir = os.path.dirname(os.getcwd())

    folder_selected = filedialog.askdirectory(
        title="Select Workspace Folder",
        initialdir=initial_dir,
    )

    root.destroy()
    return folder_selected if folder_selected else None
