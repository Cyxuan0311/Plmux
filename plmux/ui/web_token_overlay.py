"""Web token management overlay: generate, revoke, copy tokens."""

from __future__ import annotations

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from plmux.ui.theme import Theme


def build_web_token_overlay(
    theme: Theme,
    *,
    tokens: list[dict[str, str]] | None = None,
    last_generated: str | None = None,
    last_generated_mode: str | None = None,
    cursor: int = 0,
    server_running: bool = True,
    terminal_width: int,
    terminal_height: int,
) -> Panel:
    if tokens is None:
        tokens = []

    cursor = max(0, min(cursor, max(len(tokens) - 1, 0))) if tokens else 0

    table = Table(
        show_header=True,
        box=box.SIMPLE,
        border_style="dim #665c54",
        header_style="bold #fabd2f",
        pad_edge=False,
    )
    table.add_column("", width=3)
    table.add_column("Prefix", style="bold #83a598", width=10)
    table.add_column("Hash", width=16)
    table.add_column("Mode", width=12)

    if not server_running:
        table.add_row("", Text("Web server not running", style="bold #f92672"), "", "", style="dim white")
        table.add_row("", Text("Start with :web first", style="dim #ebdbb2"), "", "", style="dim white")
    elif not tokens:
        table.add_row("", "(no tokens)", "", "", style="dim white")
    else:
        for i, t in enumerate(tokens):
            if i == cursor:
                marker = "\u25B6"
                row_style = "bold white"
            else:
                marker = " "
                row_style = "dim white"

            mode_text = t.get("mode", "")
            if mode_text == "read-write":
                mode_style = "bold #85c751"
            else:
                mode_style = "bold #fe8019"

            table.add_row(
                Text(marker, style=row_style),
                Text(t.get("prefix", "") + "...", style=row_style),
                Text(t.get("hash", ""), style="dim #665c54"),
                Text(mode_text, style=mode_style),
            )

    info_text = Text()
    if last_generated:
        mode_label = "read-only" if last_generated_mode == "ro" else "read-write"
        info_text.append("  New token: ", style="bold #fabd2f")
        info_text.append(last_generated, style="bold #83a598")
        info_text.append(f"  ({mode_label})", style="dim #ebdbb2")

    footer = Text()
    if server_running:
        footer.append(" g ", style="bold black on #85c751")
        footer.append(" gen RW  ", style="dim")
        footer.append(" r ", style="bold black on #fe8019")
        footer.append(" gen RO  ", style="dim")
        footer.append(" d ", style="bold black on #f92672")
        footer.append(" revoke  ", style="dim")
        footer.append(" y ", style="bold black on #83a598")
        footer.append(" copy  ", style="dim")
        footer.append(" \u2191\u2193 ", style="bold black on #85c751")
        footer.append(" nav  ", style="dim")
    footer.append(" Esc ", style="bold black on #85c751")
    footer.append(" close", style="dim")

    inner = Table.grid(padding=(0, 1))
    inner.add_row(table)
    if info_text:
        inner.add_row("")
        inner.add_row(info_text)
    inner.add_row("")
    inner.add_row(footer)

    max_w = min(terminal_width - 4, 72)
    max_h = min(terminal_height - 4, 26)

    return Panel(
        inner,
        title=" WEB TOKENS ",
        title_align="left",
        border_style=theme.pane_active_border,
        box=box.HEAVY,
        width=max_w,
        height=max_h,
        style=f"on {theme.status_background}",
        padding=(1, 2),
    )


def get_token_at(tokens: list[dict[str, str]], cursor: int) -> dict[str, str] | None:
    if not tokens or cursor < 0 or cursor >= len(tokens):
        return None
    return tokens[cursor]
