"""Main asyncio event loop with Rich Live rendering."""

from __future__ import annotations

import asyncio
import os
import queue
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Callable

from blessed import Terminal
from rich.console import Console, ConsoleDimensions
from rich.live import Live

from plmux.config.loader import load_config
from plmux.daemon import ServerState
from plmux.debug_log import setup_debug_logging
from plmux.extensions.registry import ExtensionContext, emit_hook, load_plugins, get_plugin_status_items, get_plugin_overlay, load_config_hooks
from plmux.modes import AppContext
from plmux.modes.dispatcher import dispatch_key
from plmux.session.store import save_session
from plmux.state_bridge import (
    build_detach_state,
    build_workspace_from_state,
)
from plmux.daemon import connect_and_receive
from plmux.terminal.session import TerminalSession
from plmux.ui.renderer import build_root
from plmux.ui.geometry import remove_pane_collapse, reindex_after_remove
from plmux.ui.theme import load_theme
from plmux.workspace import Session, TmuxServer, Window, try_load_snapshot


def _terminal_size(term: Terminal) -> tuple[int, int]:
    import shutil
    tw, th = term.width, term.height
    if tw is None or th is None:
        try:
            sz = shutil.get_terminal_size()
            tw, th = sz.columns, sz.lines
        except OSError:
            tw, th = 80, 24
    return tw, th


def _parse_prefix_key(spec: str) -> str:
    s = (spec or "ctrl+b").lower().strip()
    if s in ("ctrl+b", "c-b", "^b"):
        return chr(2)
    if s in ("ctrl+a", "c-a", "^a"):
        return chr(1)
    return chr(2)


def _parse_cmdline_trigger(spec: str) -> tuple[str, str]:
    s = (spec or ":").strip()
    low = s.lower()
    if low in ("ctrl+shift+:", "c-s-:", "ctrl+shift+;", "c-s-;"):
        return ("chord", "ctrl+shift+;")
    return ("char", s[:1])


def _match_chord_raw(key, chord_name: str) -> bool:
    if chord_name != "ctrl+shift+;":
        return False
    code = getattr(key, "code", None)
    if not code:
        return False
    if isinstance(code, int):
        return code == 59 and getattr(key, "modifiers", 0) & 5 == 5
    if isinstance(code, str):
        import re
        m = re.match(r"\x1b\[(\d+);(\d+)u", code)
        if m:
            cp = int(m.group(1))
            mod = int(m.group(2))
            return cp == 59 and mod in (5, 6)
    return False


class _InputReader:
    """Background thread that reads keyboard input into a queue.

    Decouples input reading from the main event loop so that PTY output
    can be pumped and rendered without waiting for the next keypress.
    """

    def __init__(self, term: Terminal) -> None:
        self._term = term
        self._queue: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, name="plmux-input-reader", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        from plmux.app.mouse_handler import SGR_MOUSE_RE, make_mouse_keystroke
        is_win = sys.platform == "win32" or os.name == "nt"
        while not self._stop.is_set():
            try:
                if is_win:
                    key = self._term.inkey(timeout=0.002)
                    if key:
                        raw = str(key)
                        if raw.startswith("\x1b[<"):
                            m = SGR_MOUSE_RE.match(raw)
                            if m:
                                key = make_mouse_keystroke(raw, m)
                        self._queue.put(key)
                else:
                    key = self._term.inkey(timeout=0.016)
                    if key:
                        raw = str(key)
                        if raw.startswith("\x1b[<"):
                            m = SGR_MOUSE_RE.match(raw)
                            if m:
                                key = make_mouse_keystroke(raw, m)
                        self._queue.put(key)
            except Exception:
                self._stop.wait(0.005)

    def get_all(self) -> list:
        keys = []
        while True:
            try:
                keys.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return keys

    def stop(self) -> None:
        self._stop.set()


def _win_setup_timer() -> None:
    try:
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass


class _ConfigWatcher:
    def __init__(self, config_path: str | None) -> None:
        from plmux.config.loader import _resolve_user_config_path
        self._path = _resolve_user_config_path(config_path)
        self._mtime: float = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._update_mtime()

    def _update_mtime(self) -> None:
        try:
            self._mtime = os.path.getmtime(self._path)
        except OSError:
            pass

    def start(self, callback: object) -> None:
        def _watch() -> None:
            while not self._stop.is_set():
                self._stop.wait(2.0)
                if self._stop.is_set():
                    break
                try:
                    current = os.path.getmtime(self._path)
                    if current > self._mtime:
                        self._mtime = current
                        callback()
                except OSError:
                    pass

        self._thread = threading.Thread(target=_watch, name="plmux-config-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


async def async_main(
    config_path: str | None,
    *,
    debug: bool = False,
    attach_mode: bool = False,
    remote_mode: bool = False,
    target_session: str | None = None,
) -> ServerState | None:
    cfg = load_config(config_path)
    theme = load_theme(cfg.theme)
    term = Terminal(force_styling=True)
    console = Console(force_terminal=True)

    if sys.platform == "win32" or os.name == "nt":
        _win_setup_timer()

    setup_debug_logging(debug)

    ctx = AppContext(
        ws=None,
        cfg=cfg,
        theme=theme,
        term=term,
        console=console,
        prefix_key=_parse_prefix_key(cfg.keys.prefix),
        cmdline_trigger_type=_parse_cmdline_trigger(cfg.keys.command_line)[0],
        cmdline_trigger_val=_parse_cmdline_trigger(cfg.keys.command_line)[1],
        clock_str=datetime.now().strftime("%H:%M:%S"),
    )

    async def clock_ticker() -> None:
        while ctx.running:
            await asyncio.sleep(1)
            new_time = datetime.now().strftime("%H:%M:%S")
            if new_time != ctx.clock_str:
                ctx.clock_str = new_time
                ctx.dirty = True

    async def pet_ticker() -> None:
        while ctx.running:
            await asyncio.sleep(0.8)
            if ctx.pet_mode_pane is not None:
                ctx.pet_frame += 1
                ctx.dirty = True

    async def status_refresh_ticker() -> None:
        while ctx.running:
            await asyncio.sleep(2)
            try:
                pane_cwd = ""
                if ctx.ws and ctx.ws._window().panes:
                    win = ctx.ws._window()
                    fp = win.focus_pane
                    if 0 <= fp < len(win.panes):
                        s = win.panes[fp]
                        if sys.platform != "win32" and os.name != "nt" and s.proc is not None:
                            try:
                                pane_cwd = os.readlink(f"/proc/{s.proc.pid}/cwd")
                            except OSError:
                                pass
                        if not pane_cwd:
                            try:
                                pane_cwd = os.getcwd()
                            except OSError:
                                pass
                await asyncio.to_thread(
                    emit_hook,
                    "status_refresh",
                    ExtensionContext(hook_name="status_refresh", cwd=pane_cwd),
                )
                ctx.dirty = True
            except Exception:
                pass

    ipc_conn = None

    if remote_mode:
        from plmux.daemon.client import attach_to_server
        from plmux.platform.shell import resolve_shell_argv
        from plmux.session.models import tree_from_json
        from plmux.ui.geometry import count_panes

        ipc_conn, init_data = await attach_to_server()
        ctx.ws = TmuxServer(cfg, theme, on_dirty=ctx.mark_dirty)
        ctx.ws.sessions_list.clear()
        ctx.ws.current_session = init_data.get("current_session", 0)

        def _get_focus_pane_idx() -> int:
            gi = 0
            for si, sess in enumerate(ctx.ws.sessions_list):
                for w in sess.windows:
                    for pi, s in enumerate(w.panes):
                        if si == ctx.ws.current_session and w is ctx.ws._session().windows[sess.current_window] and pi == w.focus_pane:
                            return gi
                        gi += 1
            return 0

        def _make_on_write() -> Callable:
            def on_write(data: bytes) -> None:
                idx = _get_focus_pane_idx()
                asyncio.ensure_future(ipc_conn.send_key(idx, data))
            return on_write

        def _make_remote_session(rows, cols, *, shell=None, env=None):
            return TerminalSession.create_remote(
                rows=rows, cols=cols, argv=resolve_shell_argv(cfg.shell),
                on_update=ctx.mark_dirty,
                on_write=_make_on_write(),
            )

        ctx.ws._make_session = _make_remote_session

        for sd in init_data.get("sessions_data", []):
            sess = Session(cfg, theme, ctx.mark_dirty, ctx.ws._make_session, name=sd.get("name", ""))
            sess.current_window = sd.get("current_window", 0)
            sess.windows.clear()
            for w_data in sd.get("windows", []):
                w_tree = tree_from_json(w_data.get("tree", 0))
                n_panes = count_panes(w_tree)
                w_panes = []
                for _ in range(n_panes):
                    w_panes.append(TerminalSession.create_remote(
                        rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                        on_update=ctx.mark_dirty,
                        on_write=_make_on_write(),
                    ))
                sess.windows.append(Window(
                    tree=w_tree,
                    focus_pane=max(0, min(w_data.get("focus_pane", 0), n_panes - 1)),
                    panes=w_panes,
                ))
            if not sess.windows:
                pane = TerminalSession.create_remote(
                    rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                    on_update=ctx.mark_dirty,
                    on_write=_make_on_write(),
                )
                sess.windows.append(Window(tree=0, focus_pane=0, panes=[pane]))
            ctx.ws.sessions_list.append(sess)

        ctx.ws.current_session = min(ctx.ws.current_session, max(0, len(ctx.ws.sessions_list) - 1))

        for sess in ctx.ws.sessions_list:
            sess._make_session = ctx.ws._make_session

        def _send_remote_command(cmd: dict) -> None:
            try:
                asyncio.ensure_future(ipc_conn.send_command(cmd))
            except Exception:
                pass

        ctx.send_remote_command = _send_remote_command

        buffer_dumps = init_data.get("buffer_dumps", {})
        global_idx = 0
        for sess in ctx.ws.sessions_list:
            for w in sess.windows:
                for s in w.panes:
                    buf = buffer_dumps.get(str(global_idx))
                    if buf:
                        try:
                            s.restore_buffer(buf)
                        except Exception:
                            pass
                    global_idx += 1

        def _on_pane_output(pane_idx: int, data: bytes) -> None:
            pane = None
            gi = 0
            for sess in ctx.ws.sessions_list:
                for w in sess.windows:
                    for s in w.panes:
                        if gi == pane_idx:
                            pane = s
                        gi += 1
            if pane and not pane.closed:
                pane.feed_remote(data)
                ctx.dirty = True

        def _on_state_update(state: dict) -> None:
            sessions_data = state.get("sessions_data", [])
            new_sessions_count = len(sessions_data)

            while len(ctx.ws.sessions_list) > new_sessions_count:
                old = ctx.ws.sessions_list.pop()
                old.shutdown()

            for si, sd in enumerate(sessions_data):
                if si < len(ctx.ws.sessions_list):
                    sess = ctx.ws.sessions_list[si]
                    sess.name = sd.get("name", sess.name)
                    sess.current_window = sd.get("current_window", 0)
                    new_windows_data = sd.get("windows", [])
                    while len(sess.windows) > len(new_windows_data):
                        w = sess.windows.pop()
                        for s in w.panes:
                            s.close()
                    for wi, w_data in enumerate(new_windows_data):
                        w_tree = tree_from_json(w_data.get("tree", 0))
                        n_panes = count_panes(w_tree)
                        if wi < len(sess.windows):
                            w = sess.windows[wi]
                            w.tree = w_tree
                            w.focus_pane = w_data.get("focus_pane", 0)
                            while len(w.panes) > n_panes:
                                old_pane = w.panes.pop()
                                old_pane.close()
                            while len(w.panes) < n_panes:
                                w.panes.append(TerminalSession.create_remote(
                                    rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                                    on_update=ctx.mark_dirty,
                                    on_write=_make_on_write(),
                                ))
                        else:
                            w_panes = []
                            for _ in range(n_panes):
                                w_panes.append(TerminalSession.create_remote(
                                    rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                                    on_update=ctx.mark_dirty,
                                    on_write=_make_on_write(),
                                ))
                            sess.windows.append(Window(
                                tree=w_tree,
                                focus_pane=max(0, min(w_data.get("focus_pane", 0), max(0, n_panes - 1))),
                                panes=w_panes,
                            ))
                else:
                    new_sess = Session(cfg, theme, ctx.mark_dirty, ctx.ws._make_session, name=sd.get("name", ""))
                    new_sess.current_window = sd.get("current_window", 0)
                    for w_data in sd.get("windows", []):
                        w_tree = tree_from_json(w_data.get("tree", 0))
                        n_panes = count_panes(w_tree)
                        w_panes = []
                        for _ in range(n_panes):
                            w_panes.append(TerminalSession.create_remote(
                                rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                                on_update=ctx.mark_dirty,
                                on_write=_make_on_write(),
                            ))
                        new_sess.windows.append(Window(
                            tree=w_tree,
                            focus_pane=max(0, min(w_data.get("focus_pane", 0), max(0, n_panes - 1))),
                            panes=w_panes,
                        ))
                    if not new_sess.windows:
                        pane = TerminalSession.create_remote(
                            rows=24, cols=80, argv=resolve_shell_argv(cfg.shell),
                            on_update=ctx.mark_dirty,
                            on_write=_make_on_write(),
                        )
                        new_sess.windows.append(Window(tree=0, focus_pane=0, panes=[pane]))
                    new_sess._make_session = ctx.ws._make_session
                    ctx.ws.sessions_list.append(new_sess)

            ctx.ws.current_session = state.get("current_session", ctx.ws.current_session)
            ctx.dirty = True

        def _on_pane_closed(pane_idx: int) -> None:
            gi = 0
            for sess in ctx.ws.sessions_list:
                for w in sess.windows:
                    for i, s in enumerate(w.panes):
                        if gi == pane_idx:
                            s._closed = True
                            ctx.dirty = True
                        gi += 1

        ipc_conn._on_pane_output = _on_pane_output
        ipc_conn._on_state_update = _on_state_update
        ipc_conn._on_pane_closed = _on_pane_closed

    elif attach_mode:
        state, fds = await connect_and_receive()
        ctx.ws = build_workspace_from_state(state, cfg, theme, ctx.mark_dirty, target_session)
    else:
        snap = try_load_snapshot(cfg) if cfg.session.auto_save else None
        ctx.ws = await asyncio.to_thread(
            TmuxServer, cfg, theme, on_dirty=ctx.mark_dirty, restore=snap
        )
        if snap is not None:
            emit_hook("session_loaded", ExtensionContext(hook_name="session_loaded"))

    loop = asyncio.get_running_loop()

    ipc_recv_task: asyncio.Task | None = None
    if remote_mode and ipc_conn is not None:
        async def _ipc_recv_loop() -> None:
            try:
                await ipc_conn.recv_loop()
            except (ConnectionResetError, BrokenPipeError, OSError):
                pass
            finally:
                ctx.running = False
        ipc_recv_task = asyncio.create_task(_ipc_recv_loop())

    def _handle_sigint() -> None:
        ctx.dirty = True
        ctx.sigint_flagged = True
        if not remote_mode and ctx.ws._window().panes:
            s = ctx.ws.active_session()
            s.write_text("\x03")
            try:
                if sys.platform == "win32" or os.name == "nt":
                    import ctypes
                    ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, s.proc.pid)
                else:
                    os.kill(s.proc.pid, signal.SIGINT)
            except OSError:
                pass
        elif remote_mode and ipc_conn:
            asyncio.ensure_future(ipc_conn.send_key(0, b"\x03"))

    sig_handler_ok = False
    try:
        loop.add_signal_handler(signal.SIGINT, _handle_sigint)
        sig_handler_ok = True
    except NotImplementedError:
        pass
    except Exception:
        pass

    if not sig_handler_ok:
        def _sigint_fallback(_signum, _frame):
            ctx.sigint_flagged = True
        signal.signal(signal.SIGINT, _sigint_fallback)

    refresh = max(4, min(60, int(cfg.ui.refresh_hz)))
    frame_sleep = 1.0 / refresh

    clock_task = asyncio.create_task(clock_ticker())
    status_task = asyncio.create_task(status_refresh_ticker())
    pet_task = asyncio.create_task(pet_ticker())

    config_watcher = _ConfigWatcher(config_path)
    config_watcher.start(lambda: setattr(ctx, 'config_reload_pending', True))

    web_task: asyncio.Task | None = None

    async def _maybe_start_web() -> None:
        nonlocal web_task
        if ctx._pending_web_port > 0:
            port = ctx._pending_web_port
            ctx._pending_web_port = 0
            try:
                from plmux.web.server import start_web_server
                await start_web_server(ctx.ws, port=port)
                ctx.dirty = True
            except Exception:
                pass
        if ctx._pending_web_stop:
            ctx._pending_web_stop = False
            try:
                from plmux.web.server import stop_web_server
                await stop_web_server()
                ctx.dirty = True
            except Exception:
                pass

    def persist() -> None:
        from plmux.session.models import tree_to_json
        buffer_dumps: dict[str, str] = {}
        sessions_data: list[dict] = []
        global_idx = 0
        for sess in ctx.ws.sessions_list:
            pane_offset = global_idx
            for w in sess.windows:
                for s in w.panes:
                    try:
                        buffer_dumps[str(global_idx)] = s.dump_buffer()
                    except Exception:
                        pass
                    global_idx += 1
            windows_data = []
            for w in sess.windows:
                windows_data.append({
                    "tree": tree_to_json(w.tree),
                    "focus_pane": w.focus_pane,
                })
            sessions_data.append({
                "name": sess.name,
                "windows": windows_data,
                "current_window": sess.current_window,
                "pane_offset": pane_offset,
                "pane_count": global_idx - pane_offset,
            })
        # cur_sess = ctx.ws._session()
        save_session(
            cfg,
            tree=ctx.ws.tree,
            focus_pane=ctx.ws.focus_pane,
            shell=cfg.shell,
            cwd=os.getcwd(),
            extra_meta={"argv0": sys.argv[0], "theme": ctx.ws.theme.name},
            buffer_dumps=buffer_dumps,
            sessions_data=sessions_data,
            current_session=ctx.ws.current_session,
        )
        emit_hook("session_saved", ExtensionContext(hook_name="session_saved"))

    with term.cbreak(), term.hidden_cursor():
        with Live(
            console=console,
            screen=cfg.ui.use_alternate_screen,
            refresh_per_second=refresh,
        ) as live:
            try:
                from blessed.dec_modes import DecPrivateMode
                term._dec_mode_set_enabled(
                    DecPrivateMode.MOUSE_EXTENDED_SGR,
                    DecPrivateMode.MOUSE_REPORT_DRAG,
                )
            except Exception:
                term.stream.write("\x1b[?1002h\x1b[?1006h")
                term.stream.flush()
                term._dec_mode_cache[1006] = 1
                term._dec_mode_cache[1002] = 1
            input_reader = _InputReader(term)
            frame_count = 0
            plugins_loaded = False
            _last_resize_rows = 0
            _last_resize_cols = 0
            try:
                while ctx.running:
                    frame_count += 1
                    frame_start = time.monotonic()

                    if not plugins_loaded and frame_count >= 2:
                        plugins_loaded = True
                        load_config_hooks(cfg.hooks.hooks)
                        load_plugins(cfg.extensions.enabled, cfg.extensions.search_paths)
                        emit_hook(
                            "app_started",
                            ExtensionContext(extra_config=dict(cfg.extra)),
                        )

                    tw, th = _terminal_size(term)
                    console.size = ConsoleDimensions(width=tw, height=th)

                    inner_rows = max(cfg.ui.min_pane_rows, th - 2)
                    inner_cols = max(cfg.ui.min_pane_cols, tw)
                    ctx.content_rows = inner_rows
                    ctx.content_cols = inner_cols
                    ctx.ws.sync_geometry(inner_rows, inner_cols)

                    if remote_mode and ipc_conn is not None:
                        if inner_rows != _last_resize_rows or inner_cols != _last_resize_cols:
                            _last_resize_rows = inner_rows
                            _last_resize_cols = inner_cols
                            try:
                                asyncio.ensure_future(ipc_conn.send_resize(inner_rows, inner_cols))
                            except Exception:
                                pass

                    if not remote_mode:
                        TerminalSession.pump_all_sessions(ctx.ws.all_panes())
                    else:
                        for sess in ctx.ws.sessions_list:
                            for w in sess.windows:
                                for s in w.panes:
                                    if s.is_remote and not s.closed:
                                        try:
                                            s._pump_queue()
                                        except Exception:
                                            pass

                    keys = input_reader.get_all()

                    if ctx.sigint_flagged:
                        ctx.sigint_flagged = False
                        if remote_mode and ipc_conn:
                            asyncio.ensure_future(ipc_conn.send_key(0, b"\x03"))
                        elif ctx.ws._window().panes:
                            s = ctx.ws.active_session()
                            s.write_text("\x03")
                            try:
                                if sys.platform == "win32" or os.name == "nt":
                                    import ctypes
                                    ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, s.proc.pid)
                                else:
                                    os.kill(s.proc.pid, signal.SIGINT)
                            except OSError:
                                pass
                        ctx.dirty = True

                    if ctx.config_reload_pending:
                        ctx.config_reload_pending = False
                        try:
                            new_cfg = load_config(config_path)
                            old_enabled = set(ctx.cfg.extensions.enabled)
                            ctx.cfg = new_cfg
                            ctx.prefix_key = _parse_prefix_key(new_cfg.keys.prefix)
                            trig_type, trig_val = _parse_cmdline_trigger(new_cfg.keys.command_line)
                            ctx.cmdline_trigger_type = trig_type
                            ctx.cmdline_trigger_val = trig_val
                            ctx.theme = load_theme(new_cfg.theme)
                            ctx.ws.theme = ctx.theme
                            new_enabled = set(new_cfg.extensions.enabled)
                            to_load = new_enabled - old_enabled
                            if to_load:
                                load_plugins(list(to_load), new_cfg.extensions.search_paths)
                        except Exception:
                            pass
                        ctx.dirty = True

                    for key in keys:
                        from plmux.app.mouse_handler import handle_mouse_event
                        mouse_handled = handle_mouse_event(key, ctx, ctx.ws, inner_rows, inner_cols)
                        if not mouse_handled:
                            if ctx.mode == "normal" and ctx.ws and ctx.ws.focus_pane is not None:
                                win = ctx.ws._window()
                                if win.focus_pane < len(win.panes):
                                    fs = win.panes[win.focus_pane]
                                    if fs.scroll_offset > 0:
                                        fs.scroll_offset = 0
                                        ctx.dirty = True
                            dispatch_key(key, ctx)
                        if not remote_mode:
                            TerminalSession.pump_all_sessions(ctx.ws.all_panes())

                    try:
                        from plmux.web.server import drain_web_keys
                        web_keys = drain_web_keys()
                        for wk in web_keys:
                            dispatch_key(wk, ctx)
                            if not remote_mode:
                                TerminalSession.pump_all_sessions(ctx.ws.all_panes())
                        if web_keys:
                            ctx.dirty = True
                    except Exception:
                        pass

                    ctx.ws.web_mode = ctx.mode
                    ctx.ws.web_cmd_buffer = ctx.cmd_buffer

                    await _maybe_start_web()

                    try:
                        from plmux.web.server import notify_web_state_change
                        notify_web_state_change(ctx)
                    except Exception:
                        pass

                    win = ctx.ws._window()
                    dead_indices = [i for i, s in enumerate(win.panes) if s.closed]
                    if dead_indices:
                        for i in sorted(dead_indices, reverse=True):
                            if not ctx.ws.remove_pane(i):
                                ctx.hard_quit_requested = True
                                ctx.running = False
                        ctx.dirty = True
                        if ctx.running and not win.panes:
                            ctx.hard_quit_requested = True
                            ctx.running = False
                        if not ctx.running:
                            continue

                    for si, sess in enumerate(ctx.ws.sessions_list):
                        if si == ctx.ws.current_session:
                            continue
                        for w in sess.windows:
                            dead = [i for i, s in enumerate(w.panes) if s.closed]
                            for di in sorted(dead, reverse=True):
                                if di < len(w.panes):
                                    w.panes[di].close()
                                    del w.panes[di]
                                    new_tree = remove_pane_collapse(w.tree, di)
                                    if new_tree is None:
                                        w.tree = 0
                                    else:
                                        w.tree = reindex_after_remove(new_tree, di)
                            if not w.panes:
                                w.tree = 0
                                w.focus_pane = 0

                    if ctx.dirty or keys:
                        extra_items = []
                        if ctx.broadcast_enabled:
                            extra_items.append(("SYNC", ctx.ws.theme.status_pane_style, "left"))
                        if getattr(ctx.ws, "zoom_pane", None) is not None:
                            extra_items.append(("ZOOM", ctx.ws.theme.status_win_style, "left"))
                        if ctx.mode == "copy":
                            s_copy = ctx.ws.active_session() if ctx.copy_pane is None else ctx.ws._window().panes[ctx.copy_pane]
                            sb_len = s_copy.scrollback_len
                            offset = ctx.copy_scroll_offset
                            copy_label = "COPY"
                            if sb_len > 0 and offset > 0:
                                copy_label = f"COPY ↑{offset}/{sb_len}"
                            if ctx.copy_search_query:
                                n_matches = len(ctx.copy_search_matches)
                                copy_label += f" /{ctx.copy_search_query}({n_matches})"
                            if ctx.copy_search_active:
                                copy_label = f"SEARCH: {ctx.copy_search_query}_"
                            extra_items.append((copy_label, ctx.ws.theme.status_pane_style, "left"))
                        elif ctx.mode == "normal" and ctx.ws and ctx.ws.focus_pane is not None:
                            win = ctx.ws._window()
                            if win.focus_pane < len(win.panes):
                                fs = win.panes[win.focus_pane]
                                so = fs.scroll_offset
                                if so > 0:
                                    sb_len = fs.scrollback_len
                                    extra_items.append((f"↑{so}/{sb_len}", ctx.ws.theme.status_pane_style, "left"))
                        extra_items.extend(get_plugin_status_items())
                        root = await asyncio.to_thread(
                            build_root,
                            ctx.ws,
                            status_position=cfg.ui.status_position,
                            cmdline_active=(ctx.mode == "cmdline"),
                            cmd_buffer=ctx.cmd_buffer,
                            platform_name=os.name,
                            terminal_width=tw,
                            terminal_height=th,
                            help_active=(ctx.mode == "help"),
                            help_tab=ctx.help_tab,
                            help_scroll_offset=ctx.help_scroll_offset,
                            theme_list_active=(ctx.mode == "theme_list"),
                            theme_list_cursor=ctx.theme_list_cursor,
                            theme_search_query=ctx.theme_search_query,
                            session_list_active=(ctx.mode == "session_list"),
                            session_list_cursor=ctx.session_list_cursor,
                            session_list_tab=ctx.session_list_tab,
                            plugin_list_active=(ctx.mode == "plugin_list"),
                            plugin_list_cursor=ctx.plugin_list_cursor,
                            plugin_search_paths=list(cfg.extensions.search_paths),
                            plugin_enabled_names=list(cfg.extensions.enabled),
                            layout_list_active=(ctx.mode == "layout_list"),
                            layout_list_cursor=ctx.layout_list_cursor,
                            current_panes=len(ctx.ws._window().panes),
                            clock_str=ctx.clock_str,
                            mode=ctx.mode.upper() if ctx.mode != "normal" else "NORMAL",
                            extra_items=extra_items,
                            completion_hints=ctx.completion_hints,
                            plugin_overlay_name=ctx.mode if ctx.mode not in (
                                "normal", "prefix", "cmdline", "help", "esc_wait",
                                "copy", "theme_list", "session_list", "plugin_list",
                                "layout_list",
                            ) and get_plugin_overlay(ctx.mode) is not None else "",
                            plugin_state=ctx.plugin_state,
                            clock_mode_pane=ctx.clock_mode_pane,
                            pet_mode_pane=ctx.pet_mode_pane,
                            pet_type=ctx.pet_type,
                            pet_frame=ctx.pet_frame,
                        )
                        live.update(root)
                        ctx.dirty = False

                    elapsed = time.monotonic() - frame_start
                    poll_interval = min(frame_sleep, 0.004)
                    sleep_time = max(0.001, poll_interval - elapsed)
                    await asyncio.sleep(sleep_time)
            finally:
                try:
                    from blessed.dec_modes import DecPrivateMode
                    term._dec_mode_set_disabled(
                        DecPrivateMode.MOUSE_EXTENDED_SGR,
                        DecPrivateMode.MOUSE_REPORT_DRAG,
                    )
                except Exception:
                    term.stream.write("\x1b[?1002l\x1b[?1006l\x1b[?1000l")
                    term.stream.flush()
                    term._dec_mode_cache.pop(1006, None)
                    term._dec_mode_cache.pop(1002, None)
                input_reader.stop()
                config_watcher.stop()

    if ipc_recv_task is not None:
        ipc_recv_task.cancel()
        try:
            await ipc_recv_task
        except asyncio.CancelledError:
            pass

    if remote_mode and ipc_conn is not None:
        try:
            await ipc_conn.send_detach()
        except Exception:
            pass
        ipc_conn.close()

    clock_task.cancel()
    status_task.cancel()
    pet_task.cancel()
    try:
        await clock_task
    except asyncio.CancelledError:
        pass
    try:
        await status_task
    except asyncio.CancelledError:
        pass
    try:
        await pet_task
    except asyncio.CancelledError:
        pass

    try:
        from plmux.web.server import stop_web_server
        await stop_web_server()
    except Exception:
        pass

    emit_hook("app_stopping", ExtensionContext())

    if remote_mode:
        ctx.ws.shutdown()
        return None
    elif ctx.detach_requested:
        state = build_detach_state(ctx.ws, cfg)
        print("\r\n[detached (from session 0)]", flush=True)
        return state
    elif ctx.hard_quit_requested:
        from plmux.session.store import resolve_state_path
        try:
            path = resolve_state_path(cfg)
            if path.is_file():
                path.unlink()
        except Exception:
            pass
        ctx.ws.shutdown()
        return None
    else:
        if cfg.session.auto_save:
            persist()
        ctx.ws.shutdown()
        return None
