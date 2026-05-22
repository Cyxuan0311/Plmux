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
from pathlib import Path

from blessed import Terminal
from rich.console import Console, ConsoleDimensions
from rich.live import Live

from plmux.config.loader import load_config
from plmux.daemon import ServerState
from plmux.debug_log import PerfTimer, get_frame_profiler, setup_debug_logging
from plmux.terminal._c_extension import _fastscreen
from plmux.extensions.registry import ExtensionContext, emit_hook, load_plugins, get_plugin_status_items, get_plugin_overlay
from plmux.modes import AppContext
from plmux.modes.dispatcher import dispatch_key
from plmux.session.store import save_session
from plmux.state_bridge import (
    build_detach_state,
    build_workspace_from_state,
)
from plmux.daemon import connect_and_receive
from plmux.terminal.session import TerminalSession, report_session_stats, reset_session_stats
from plmux.ui.renderer import build_root
from plmux.ui.theme import load_theme
from plmux.workspace import PaneWorkspace, try_load_snapshot


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
                    import msvcrt
                    if msvcrt.kbhit():
                        key = self._term.inkey()
                        if key:
                            self._queue.put(key)
                        continue
                    self._stop.wait(0.002)
                else:
                    key = self._term.inkey(timeout=0.016)
                    if key:
                        if str(key).startswith("\x1b[<"):
                            m = SGR_MOUSE_RE.match(str(key))
                            if m:
                                key = make_mouse_keystroke(str(key), m)
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
    target_session: str | None = None,
) -> ServerState | None:
    cfg = load_config(config_path)
    theme = load_theme(cfg.theme)
    term = Terminal(force_styling=True)
    console = Console(force_terminal=True)

    if sys.platform == "win32" or os.name == "nt":
        _win_setup_timer()

    setup_debug_logging(debug)

    if debug:
        _fastscreen.enable_debug(str(Path.cwd() / "plmux_cdebug.log"))

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

    async def status_refresh_ticker() -> None:
        while ctx.running:
            await asyncio.sleep(2)
            try:
                pane_cwd = ""
                if ctx.ws and ctx.ws.sessions:
                    fp = ctx.ws.focus_pane
                    if 0 <= fp < len(ctx.ws.sessions):
                        s = ctx.ws.sessions[fp]
                        if sys.platform != "win32" and os.name != "nt":
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

    if attach_mode:
        state, fds = await connect_and_receive()
        ctx.ws = build_workspace_from_state(state, cfg, theme, ctx.mark_dirty, target_session)
    else:
        snap = try_load_snapshot(cfg) if cfg.session.auto_save else None
        ctx.ws = await asyncio.to_thread(
            PaneWorkspace, cfg, theme, on_dirty=ctx.mark_dirty, restore=snap
        )
        if snap is not None:
            emit_hook("session_loaded", ExtensionContext(hook_name="session_loaded"))

    loop = asyncio.get_running_loop()

    def _handle_sigint() -> None:
        ctx.dirty = True
        ctx.sigint_flagged = True
        if ctx.ws.sessions:
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
        buffer_dumps: dict[str, str] = {}
        for i, s in enumerate(ctx.ws.sessions):
            try:
                buffer_dumps[str(i)] = s.dump_buffer()
            except Exception:
                pass
        save_session(
            cfg,
            tree=ctx.ws.tree,
            focus_pane=ctx.ws.focus_pane,
            shell=cfg.shell,
            cwd=os.getcwd(),
            extra_meta={"argv0": sys.argv[0], "theme": ctx.ws.theme.name},
            buffer_dumps=buffer_dumps,
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
            profiler = get_frame_profiler(slow_threshold_ms=16.0, exclude_from_slow={"input"})
            try:
                while ctx.running:
                    frame_count += 1

                    if not plugins_loaded and frame_count >= 2:
                        plugins_loaded = True
                        load_plugins(cfg.extensions.enabled, cfg.extensions.search_paths)
                        emit_hook(
                            "app_started",
                            ExtensionContext(extra_config=dict(cfg.extra)),
                        )
                    frame_timer = PerfTimer()
                    frame_start = time.monotonic()

                    tw, th = _terminal_size(term)
                    console.size = ConsoleDimensions(width=tw, height=th)

                    inner_rows = max(cfg.ui.min_pane_rows, th - 2)
                    inner_cols = max(cfg.ui.min_pane_cols, tw)
                    ctx.ws.sync_geometry(inner_rows, inner_cols)

                    t_pty = PerfTimer()
                    TerminalSession.pump_all_sessions(ctx.ws.sessions)
                    pty_ms = t_pty.elapsed_ms()

                    keys = input_reader.get_all()
                    input_ms = frame_timer.elapsed_ms()

                    if ctx.sigint_flagged:
                        ctx.sigint_flagged = False
                        if ctx.ws.sessions:
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
                                fs = ctx.ws.sessions[ctx.ws.focus_pane]
                                if fs.scroll_offset > 0:
                                    fs.scroll_offset = 0
                                    ctx.dirty = True
                            dispatch_key(key, ctx)
                        TerminalSession.pump_all_sessions(ctx.ws.sessions)

                    try:
                        from plmux.web.server import drain_web_keys
                        web_keys = drain_web_keys()
                        for wk in web_keys:
                            dispatch_key(wk, ctx)
                            TerminalSession.pump_all_sessions(ctx.ws.sessions)
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

                    dead_indices = [i for i, s in enumerate(ctx.ws.sessions) if s.closed]
                    if dead_indices:
                        for i in sorted(dead_indices, reverse=True):
                            if not ctx.ws.remove_pane(i):
                                ctx.running = False
                        ctx.dirty = True
                        if ctx.running and not ctx.ws.sessions:
                            ctx.running = False
                        if not ctx.running:
                            continue

                    render_ms = 0.0
                    if ctx.dirty or keys:
                        t_render = PerfTimer()
                        extra_items = []
                        if ctx.broadcast_enabled:
                            extra_items.append(("BCAST", ctx.ws.theme.status_pane_style, "left"))
                        if getattr(ctx.ws, "zoom_pane", None) is not None:
                            extra_items.append(("ZOOM", ctx.ws.theme.status_win_style, "left"))
                        if ctx.mode == "copy":
                            s_copy = ctx.ws.active_session() if ctx.copy_pane is None else ctx.ws.sessions[ctx.copy_pane]
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
                            fs = ctx.ws.sessions[ctx.ws.focus_pane]
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
                            theme_list_active=(ctx.mode == "theme_list"),
                            theme_list_cursor=ctx.theme_list_cursor,
                            theme_search_query=ctx.theme_search_query,
                            session_list_active=(ctx.mode == "session_list"),
                            session_list_cursor=ctx.session_list_cursor,
                            plugin_list_active=(ctx.mode == "plugin_list"),
                            plugin_list_cursor=ctx.plugin_list_cursor,
                            plugin_search_paths=list(cfg.extensions.search_paths),
                            plugin_enabled_names=list(cfg.extensions.enabled),
                            layout_list_active=(ctx.mode == "layout_list"),
                            layout_list_cursor=ctx.layout_list_cursor,
                            current_panes=len(ctx.ws.sessions),
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
                        )
                        live.update(root)
                        ctx.dirty = False
                        render_ms = t_render.elapsed_ms()

                    frame_timer.elapsed_ms()
                    profiler.end_frame({
                        "input": input_ms,
                        "pty": pty_ms,
                        "render": render_ms,
                    })

                    if frame_count % 60 == 0:
                        report_session_stats()
                        reset_session_stats()

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

    clock_task.cancel()
    status_task.cancel()
    try:
        await clock_task
    except asyncio.CancelledError:
        pass
    try:
        await status_task
    except asyncio.CancelledError:
        pass

    try:
        from plmux.web.server import stop_web_server
        await stop_web_server()
    except Exception:
        pass

    emit_hook("app_stopping", ExtensionContext())

    if debug:
        _fastscreen.disable_debug()

    if ctx.detach_requested:
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
