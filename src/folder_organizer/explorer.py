"""Open folders in the system file manager."""

import os
import subprocess
import sys


def open_folder(path: str) -> bool:
    """Open `path` in Explorer. Returns False if the folder doesn't exist."""
    if not os.path.isdir(path):
        return False
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - opening a user-chosen folder is the purpose of the app
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
    return True
