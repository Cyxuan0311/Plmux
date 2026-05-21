"""Cross-platform clipboard operations."""

from __future__ import annotations

import os
import sys


def copy_to_clipboard(text: str) -> None:
    try:
        import pyperclip
        pyperclip.copy(text)
        return
    except Exception:
        pass

    try:
        if sys.platform == "darwin":
            p = os.popen("pbcopy", "w")
            p.write(text)
            p.close()
            return
        if sys.platform == "win32" or os.name == "nt":
            p = os.popen("clip", "w")
            p.write(text)
            p.close()
            return
        p = os.popen("xclip -selection clipboard -i", "w")
        p.write(text)
        p.close()
    except Exception:
        pass