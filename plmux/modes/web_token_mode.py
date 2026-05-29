"""Web token mode handler: manage web access tokens via overlay."""

from __future__ import annotations

from plmux.modes import AppContext


def handle_web_token_mode(key, ctx: AppContext) -> None:
    ch = str(key)
    name = key.name if hasattr(key, "name") else ""

    if name == "KEY_ESCAPE" or ch == "q":
        ctx.mode = "normal"
        ctx.web_token_last_generated = None
        ctx.web_token_last_mode = None
        ctx.dirty = True
        return

    from plmux.web.server import _web_server

    if _web_server is None:
        ctx.dirty = True
        return

    tm = _web_server.token_manager
    tokens = tm.list_tokens()
    n = len(tokens)

    ctx.web_token_cursor = max(0, min(ctx.web_token_cursor, n - 1)) if n else 0

    if name in ("KEY_UP",) or ch == "k":
        if n:
            ctx.web_token_cursor = max(0, ctx.web_token_cursor - 1)
        ctx.dirty = True
    elif name in ("KEY_DOWN",) or ch == "j":
        if n:
            ctx.web_token_cursor = min(n - 1, ctx.web_token_cursor + 1)
        ctx.dirty = True
    elif name == "KEY_HOME":
        ctx.web_token_cursor = 0
        ctx.dirty = True
    elif name == "KEY_END" or ch == "G":
        ctx.web_token_cursor = max(0, n - 1)
        ctx.dirty = True
    elif ch == "g":
        token = tm.generate(readonly=False)
        ctx.web_token_last_generated = token
        ctx.web_token_last_mode = "rw"
        ctx.web_token_cursor = 0
        ctx.dirty = True
    elif ch == "r":
        token = tm.generate(readonly=True)
        ctx.web_token_last_generated = token
        ctx.web_token_last_mode = "ro"
        ctx.web_token_cursor = 0
        ctx.dirty = True
    elif ch == "d":
        if n and 0 <= ctx.web_token_cursor < n:
            tm.revoke_at(ctx.web_token_cursor)
            new_tokens = tm.list_tokens()
            ctx.web_token_cursor = min(ctx.web_token_cursor, max(0, len(new_tokens) - 1))
            ctx.web_token_last_generated = None
            ctx.web_token_last_mode = None
        ctx.dirty = True
    elif ch == "y":
        if ctx.web_token_last_generated:
            from plmux.platform.clipboard import copy_to_clipboard
            copy_to_clipboard(ctx.web_token_last_generated)
        ctx.dirty = True
    else:
        ctx.dirty = True
