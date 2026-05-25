"""Pet animation overlay: looping ASCII pet animation rendered inside a pane."""

from __future__ import annotations

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from plmux.ui.theme import Theme

_PETS: dict[str, list[list[str]]] = {
    "cat": [
        [
            "    /\\_/\\    ",
            "   ( o.o )   ",
            "    > ^ <    ",
            "   /|   |\\   ",
            "  (_|   |_)  ",
        ],
        [
            "    /\\_/\\    ",
            "   ( -.- )   ",
            "    > ~ <    ",
            "   /|   |\\   ",
            "  (_|   |_)  ",
        ],
        [
            "    /\\_/\\    ",
            "   ( o.o )   ",
            "    > v <    ",
            "   /|   |\\   ",
            "  (_|   |_)  ",
        ],
        [
            "    /\\_/\\    ",
            "   ( >.< )   ",
            "    >   <    ",
            "   /|   |\\   ",
            "  (_|   |_)  ",
        ],
    ],
    "dog": [
        [
            "   /\\__/\\   ",
            "  ( o  o )  ",
            "  (  ==  )  ",
            "   \\    /   ",
            "    ----    ",
            "   /|  |\\   ",
        ],
        [
            "   /\\__/\\   ",
            "  ( ^  ^ )  ",
            "  (  ==  )  ",
            "   \\    /   ",
            "    ----    ",
            "   /|  |\\   ",
        ],
        [
            "   /\\__/\\   ",
            "  ( o  o )  ",
            "  (  ==  )  ",
            "   \\    /   ",
            "    ----    ",
            "   /|  |\\   ",
        ],
        [
            "   /\\__/\\   ",
            "  ( -  - )  ",
            "  (  ~~  )  ",
            "   \\    /   ",
            "    ----    ",
            "   /|  |\\   ",
        ],
    ],
    "bunny": [
        [
            "   (\\(\\     ",
            "   (='.')    ",
            "   o_(\")_(\" ) ",
        ],
        [
            "   (\\(\\     ",
            "   (='.')    ",
            "   o_(\")_(\" ) ",
        ],
        [
            "   (\\(\\     ",
            "   (='o')    ",
            "   o_(\")_(\" ) ",
        ],
        [
            "   (\\(\\     ",
            "   (='.' )   ",
            "   o_(\")_(\" ) ",
        ],
    ],
    "fish": [
        [
            "  ><(((('>   ",
        ],
        [
            "  ><(((('>   ",
        ],
        [
            "  ><(((('>>  ",
        ],
        [
            "  ><(((('>   ",
        ],
    ],
    "penguin": [
        [
            "    (°v°)    ",
            "   (     )   ",
            "    \\   /    ",
            "     \\_/     ",
        ],
        [
            "    (°v°)    ",
            "   (     )   ",
            "    /   \\    ",
            "     \\_/     ",
        ],
        [
            "    (°v°)    ",
            "   (     )   ",
            "    \\   /    ",
            "     \\_/     ",
        ],
        [
            "    (°v°)    ",
            "   (     )   ",
            "    /   \\    ",
            "     \\_/     ",
        ],
    ],
    "owl": [
        [
            "   ,___,     ",
            "   (O,O)     ",
            "   (   )     ",
            '    "-"      ',
        ],
        [
            "   ,___,     ",
            "   (-,-)     ",
            "   (   )     ",
            '    "-"      ',
        ],
        [
            "   ,___,     ",
            "   (O,O)     ",
            "   (   )     ",
            '    "-"      ',
        ],
        [
            "   ,___,     ",
            "   (.,.)     ",
            "   (   )     ",
            '    "-"      ',
        ],
    ],
}

_PET_NAMES = list(_PETS.keys())

_STATUS_LINES: dict[str, list[str]] = {
    "cat": ["meow~", "purr...", "zzZ", "*stretches*", "mrrp?"],
    "dog": ["woof!", "*wags tail*", "zzZ", "*pants*", "arf!"],
    "bunny": ["*hops*", "*twitches nose*", "zzZ", "*nibbles*", "..."],
    "fish": ["blub blub", "*swims*", "...", "blub?", "*bubbles*"],
    "penguin": ["waddle waddle", "*slides*", "zzZ", "noot noot", "*flaps*"],
    "owl": ["hoo hoo", "*turns head*", "zzZ", "*stares*", "whoo?"],
}


def get_pet_names() -> list[str]:
    return list(_PET_NAMES)


def build_pet_overlay(
    theme: Theme,
    *,
    pane_rows: int,
    pane_cols: int,
    pet_type: str = "cat",
    frame: int = 0,
) -> Panel:
    fg = _extract_fg(theme.status_clock_style)
    bg = _extract_bg(theme.status_clock_style)
    border = theme.pane_active_border

    pet_frames = _PETS.get(pet_type, _PETS["cat"])
    current = pet_frames[frame % len(pet_frames)]

    status_lines = _STATUS_LINES.get(pet_type, _STATUS_LINES["cat"])
    status = status_lines[frame % len(status_lines)]

    pet_text = _render_pet(current, status, fg, bg, pane_rows, pane_cols)

    return Panel(
        Align.center(pet_text, vertical="middle"),
        title=f" {pet_type.upper()} ",
        title_align="center",
        border_style=border,
        padding=(0, 1),
        style=f"on {bg}" if bg else "",
    )


def _render_pet(frame_lines: list[str], status: str, fg: str, bg: str, max_rows: int, max_cols: int) -> Text:
    result = Text()

    top_pad = max(0, (max_rows - len(frame_lines) - 4) // 2)
    for _ in range(top_pad):
        result.append("\n")

    for line in frame_lines:
        padded = line.center(max_cols - 4) if max_cols > 4 else line
        result.append(padded + "\n", style=f"bold {fg}" if fg else "bold white")

    result.append("\n")
    status_centered = status.center(max_cols - 4) if max_cols > 4 else status
    result.append(status_centered, style=f"dim {fg}" if fg else "dim white")

    return result


def _extract_fg(style_str: str) -> str:
    parts = style_str.split()
    for i, p in enumerate(parts):
        if p == "on" and i > 0:
            return parts[i - 1]
    for p in parts:
        if p.startswith("#") or p in ("white", "black", "red", "green", "blue", "yellow", "cyan", "magenta"):
            return p
    return "white"


def _extract_bg(style_str: str) -> str:
    parts = style_str.split()
    for i, p in enumerate(parts):
        if p == "on" and i + 1 < len(parts):
            return parts[i + 1]
    return ""
