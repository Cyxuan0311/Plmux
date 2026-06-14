"""Status bar gradient effect: apply smooth background color gradient to status bar."""

from __future__ import annotations

from rich.color import Color
from rich.style import Style
from rich.text import Text

from plmux.ui.gradient import hsl_gradient, try_parse_hex
from plmux.ui.theme import Theme


def _style_to_bgcolor(style: Style) -> str | None:
    if style.bgcolor and style.bgcolor.triplet:
        c = style.bgcolor.triplet
        return f"#{c.red:02x}{c.green:02x}{c.blue:02x}"
    return None


def apply_status_bar_gradient(text: Text, theme: Theme) -> None:
    base = try_parse_hex(theme.status_background)
    if not base:
        base = try_parse_hex("#85c751")
    if not base:
        return

    total_len = len(text.plain)
    if total_len == 0:
        return

    spans = list(text.spans)
    if not spans:
        return

    gradient_colors = hsl_gradient(
        base, 128,
        hue_range=120,
        sat_boost=1.15,
        light_start_offset=0.35,
        light_end_offset=-0.15,
    )

    new_text = Text()
    for span in spans:
        seg = text.plain[span.start:span.end]
        raw_style = span.style
        if isinstance(raw_style, str):
            try:
                raw_style = Style.parse(raw_style)
            except Exception:
                new_text.append(seg, style=span.style)
                continue

        mid = (span.start + span.end) / 2.0
        t = mid / max(1, total_len)
        color_idx = min(int(t * 127), 127)
        gradient_color = gradient_colors[color_idx]

        orig_bg = _style_to_bgcolor(raw_style)
        if not orig_bg:
            new_text.append(seg, style=raw_style)
            continue

        new_style = Style(
            color=raw_style.color,
            bgcolor=Color.parse(gradient_color),
            bold=raw_style.bold,
            dim=raw_style.dim,
            italic=raw_style.italic,
            underline=raw_style.underline,
            strike=raw_style.strike,
            reverse=raw_style.reverse,
        )
        new_text.append(seg, style=new_style)

    text._text = new_text._text
    text.spans = new_text.spans
