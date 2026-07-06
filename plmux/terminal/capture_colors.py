"""Capture outer terminal colors at startup via OSC queries.

Note: termios/tty are Unix-only; imported lazily inside the function
so the module can be imported on Windows without error.
"""

from __future__ import annotations

import os
import select
import sys
import time


def _parse_osc_color_response(data: bytes) -> tuple[int, int, int] | None:
    """Parse OSC color response into (r,g,b).

    Handles formats:
      \x1b]12;rgb:RRRR/GGGG/BBBB\x07   (xterm query response)
      \x1b]12;#RRGGBB\x07               (hex format)
    """
    text = data.decode("utf-8", errors="replace")
    # Find the color value after ';'
    for sep in ("rgb:", "#"):
        idx = text.find(sep)
        if idx < 0:
            continue
        if sep == "rgb:":
            rest = text[idx + 4:]
            parts = rest.split("/")
            if len(parts) >= 3:
                try:
                    r = int(parts[0][:4], 16) >> 8
                    g = int(parts[1][:4], 16) >> 8
                    b = int(parts[2][:4], 16) >> 8
                    return (r, g, b)
                except ValueError:
                    return None
        else:  # '#RRGGBB'
            rest = text[idx + 1:].strip()
            if len(rest) >= 6:
                try:
                    r = int(rest[0:2], 16)
                    g = int(rest[2:4], 16)
                    b = int(rest[4:6], 16)
                    return (r, g, b)
                except ValueError:
                    return None
    return None


def capture_outer_cursor_color() -> tuple[int, int, int] | None:
    """Query the outer terminal for its cursor color via OSC 12 ; ?.

    Returns (r, g, b) or None if the query fails / times out.

    Must be called BEFORE blessed.Terminal() takes over the terminal.
    """
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        return None

    try:
        import termios
        import tty
    except ImportError:
        return None

    try:
        old = termios.tcgetattr(fd)
    except Exception:
        return None

    try:
        tty.setraw(fd)

        sys.stdout.buffer.write(b"\x1b]12;?\x07")
        sys.stdout.buffer.flush()

        response = b""
        deadline = time.monotonic() + 0.3

        while time.monotonic() < deadline:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                chunk = os.read(fd, 256)
                if not chunk:
                    break
                response += chunk
                if b"\x07" in response or b"\x1b\\" in response:
                    break

        return _parse_osc_color_response(response)

    finally:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, old)
        except Exception:
            pass
