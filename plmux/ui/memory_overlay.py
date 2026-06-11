"""Memory overlay: btop-style process memory display for plmux."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme


def _fmt_bytes(n: int) -> str:
    if n >= 1073741824:
        return f"{n / 1073741824:.1f}G"
    if n >= 1048576:
        return f"{n / 1048576:.1f}M"
    if n >= 1024:
        return f"{n / 1024:.0f}K"
    return f"{n}B"


def _gradient_bar(pct: float, width: int) -> Text:
    pct = max(0.0, min(pct, 100.0))
    result = Text()
    for i in range(width):
        pos = (i + 0.5) / width
        if pos * 100 > pct:
            result.append("░", style="bright_black")
        else:
            ratio = pos
            if ratio > 0.75:
                result.append("█", style="red")
            elif ratio > 0.50:
                result.append("█", style="yellow")
            elif ratio > 0.30:
                result.append("█", style="bright_green")
            else:
                result.append("█", style="green")
    return result


def build_memory_overlay(
    theme: Theme,
    *,
    data: dict,
    cursor: int,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    panel_w = min(terminal_width - 4, 100)
    inner_w = panel_w - 6
    max_h = min(terminal_height - 4, 32)

    accent = theme.pane_active_border
    panel_bg = theme.pane_inactive_border
    badge_bg = theme.status_background

    bar_w = max(10, min(16, (inner_w - 34) // 2))
    pct_w = 7
    rss_w = 8
    name_w = inner_w - bar_w - pct_w - rss_w - 3

    sys_mem = data.get("system", {})
    sys_total = sys_mem.get("total", 0)
    sys_used = sys_mem.get("used", 0)
    sys_pct = (sys_used / sys_total * 100) if sys_total > 0 else 0

    mem_label = Text.assemble((" MEM ", f"bold {accent}"))
    if sys_total > 0:
        used_str = _fmt_bytes(sys_used)
        total_str = _fmt_bytes(sys_total)
        sys_bar = _gradient_bar(sys_pct, bar_w)
        pct_color = "red" if sys_pct > 75 else ("yellow" if sys_pct > 50 else "green")
        sys_text = Text.assemble(
            mem_label,
            ("  ", ""),
            (f"{used_str} / {total_str} ", "bold"),
            sys_bar,
            (f"  {sys_pct:5.1f}%", f"bold {pct_color}"),
        )
    else:
        sys_text = mem_label

    body = Table.grid(padding=(0, 0))
    body.add_column(justify="left")

    line_idx = 0
    sessions = data.get("sessions", [])

    def _add_row(indent: int, name_part: Text, pct: float, rss: int) -> None:
        nonlocal line_idx
        sel = line_idx == cursor

        row = Text()
        col = 0

        row.append("  " * indent)
        col += 2 * indent

        if sel:
            row.append("▸ ", style=f"bold on {accent}")
            col += 2
            avail = name_w - col
            name_str = name_part.plain[:avail]
            row.append(name_str, style=f"bold on {accent}")
            col += len(name_str)
            pad = name_w - col
            if pad > 0:
                row.append(" " * pad, style=f"on {accent}")
        else:
            row.append("  ")
            col += 2
            avail = name_w - col
            name_str = name_part.plain[:avail]
            row.append_text(name_part)
            col += len(name_str)
            pad = name_w - col
            if pad > 0:
                row.append(" " * pad)

        row.append(" ")

        bar = _gradient_bar(pct, bar_w)
        row.append_text(bar)
        row.append(" ")

        pct_str = f"{pct:5.1f}%"
        ppad = pct_w - len(pct_str)
        if ppad > 0:
            row.append(" " * ppad)
        row.append(pct_str, style=f"bold on {accent}" if sel else "")
        row.append(" ")

        rss_str = f"{_fmt_bytes(rss):>8s}"
        rpad = rss_w - len(rss_str)
        if rpad > 0:
            row.append(" " * rpad)
        row.append(rss_str, style=f"on {accent}" if sel else "")

        body.add_row(row)
        line_idx += 1

    # plmux
    self_data = data.get("self", {})
    _add_row(0, Text("plmux", style="bold"), self_data.get("pct", 0.0), self_data.get("rss", 0))

    if not sessions:
        body.add_row(Text("  No session data", style="dim italic"))

    for sess in sessions:
        sname = sess.get("name", "?")
        _add_row(0, Text(sname, style="bold"), sess.get("total_pct", 0.0), sess.get("total_rss", 0))

        for win in sess.get("windows", []):
            wname = win.get("name", "?")
            _add_row(1, Text(wname, style="dim"), win.get("total_pct", 0.0), win.get("total_rss", 0))

            for pane in win.get("panes", []):
                pcmd = pane.get("cmd", "?")
                ppid = pane.get("pid", -1)
                pid_tag = f"({ppid})" if ppid > 0 else ""
                pane_label = Text.assemble(
                    (pcmd, ""),
                    (" ", ""),
                    (pid_tag, "dim"),
                )
                _add_row(2, pane_label, pane.get("pct", 0.0), pane.get("rss", 0))

    # footer
    legend = Text.assemble(
        (" █ ", "green"), ("<30%  ", "dim"),
        (" █ ", "bright_green"), ("30-50%  ", "dim"),
        (" █ ", "yellow"), ("50-75%  ", "dim"),
        (" █ ", "red"), (">75%", "dim"),
    )
    keys = Text.assemble(
        (" ↑↓/jk  ", f"bold {panel_bg} on {badge_bg}"),
        ("nav  ", "dim"),
        (" q/ESC ", f"bold {panel_bg} on {badge_bg}"),
        ("close", "dim"),
    )

    inner = Table.grid(padding=(0, 0))
    inner.add_column(justify="left")
    inner.add_row(sys_text)
    inner.add_row(Text("─" * inner_w, style=f"dim {accent}"))
    inner.add_row(body)
    inner.add_row(Text(""))
    inner.add_row(Text.assemble(legend, ("   ", ""), keys))

    return Panel(
        inner,
        title=" MEMORY ",
        title_align="left",
        border_style=accent,
        width=panel_w,
        height=max_h,
        style=f"on {panel_bg}",
        padding=(1, 2),
    )
