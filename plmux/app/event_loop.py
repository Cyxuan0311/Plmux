"""Main asyncio event loop with Rich Live rendering — orchestration layer."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from datetime import datetime

from blessed import Terminal
from rich.console import Console, ConsoleDimensions
from rich.live import Live

from plmux.app.config_watcher import ConfigWatcher
from plmux.app.input_reader import InputReader
from plmux.app.persistence import persist_session
from plmux.app.remote import setup_remote_mode
from plmux.app.tickers import clock_ticker, memory_ticker, pet_ticker, status_refresh_ticker
from plmux.app.utils import parse_cmdline_trigger, parse_prefix_key, terminal_size, win_setup_timer
from plmux.config.loader import load_config
from plmux.daemon import ServerState, connect_and_receive
from plmux.debug_log import setup_debug_logging
from plmux.extensions.registry import (
    ExtensionContext,
    emit_hook,
    get_plugin_overlay,
    get_plugin_status_items,
    load_config_hooks,
    load_plugins,
    set_plugin_settings,
)
from plmux.modes import AppContext
from plmux.modes.dispatcher import dispatch_key
from plmux.state_bridge import build_detach_state, build_workspace_from_state
from plmux.terminal.capture_colors import capture_outer_cursor_color
from plmux.terminal.session import TerminalSession
from plmux.ui.geometry import remove_pane_collapse, reindex_after_remove
from plmux.ui.renderer import build_root
from plmux.ui.theme import load_theme
from plmux.workspace import TmuxServer, try_load_snapshot

_logger = logging.getLogger(__name__)


async def _init_app(
    config_path: str | None,
    debug: bool,
    attach_mode: bool,
    remote_mode: bool,
    target_session: str | None,
) -> tuple:
    cfg = load_config(config_path)
    theme = load_theme(cfg.theme)
    outer_color = capture_outer_cursor_color()
    term = Terminal(force_styling=True)
    console = Console(force_terminal=True)

    if sys.platform == "win32" or os.name == "nt":
        win_setup_timer()

    setup_debug_logging(debug)

    ctx = AppContext(
        ws=None,
        cfg=cfg,
        theme=theme,
        term=term,
        console=console,
        prefix_key=parse_prefix_key(cfg.keys.prefix),
        cmdline_trigger_type=parse_cmdline_trigger(cfg.keys.command_line)[0],
        cmdline_trigger_val=parse_cmdline_trigger(cfg.keys.command_line)[1],
        clock_str=datetime.now().strftime("%H:%M:%S"),
        outer_cursor_color=outer_color,
    )

    ipc_conn = None

    if remote_mode:
        ipc_conn = await setup_remote_mode(ctx, cfg, theme)
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

    if outer_color is not None:
        r, g, b = outer_color
        for sess in ctx.ws.sessions_list:
            for w in sess.windows:
                for pane in w.panes:
                    try:
                        pane.screen.set_cursor_color(r, g, b)
                    except Exception:
                        _logger.debug("set_cursor_color failed", exc_info=True)

    loop = asyncio.get_running_loop()

    ipc_recv_task = None
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
        _logger.debug("add_signal_handler not supported on this platform")
    except Exception:
        _logger.warning("add_signal_handler failed", exc_info=True)

    if not sig_handler_ok:
        def _sigint_fallback(_signum, _frame):
            ctx.sigint_flagged = True
        signal.signal(signal.SIGINT, _sigint_fallback)

    refresh = max(4, min(60, int(cfg.ui.refresh_hz)))
    frame_sleep = 1.0 / refresh

    clock_task = asyncio.create_task(clock_ticker(ctx))
    status_task = asyncio.create_task(status_refresh_ticker(ctx))
    pet_task = asyncio.create_task(pet_ticker(ctx))
    memory_task = asyncio.create_task(memory_ticker(ctx))

    config_watcher = ConfigWatcher(config_path)
    config_watcher.start(lambda: setattr(ctx, 'config_reload_pending', True))

    return cfg, ctx, ipc_conn, ipc_recv_task, frame_sleep, clock_task, status_task, pet_task, memory_task, config_watcher


async def _shutdown_app(
    ctx: AppContext,
    cfg,
    remote_mode: bool,
    ipc_conn,
    ipc_recv_task,
    clock_task,
    status_task,
    pet_task,
    memory_task,
) -> ServerState | None:
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
            _logger.debug("IPC detach send failed", exc_info=True)
        ipc_conn.close()

    for task in (clock_task, status_task, pet_task, memory_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        from plmux.web.server import stop_web_server
        await stop_web_server()
    except Exception:
        _logger.debug("web server stop failed on shutdown", exc_info=True)

    emit_hook("app_stopping", ExtensionContext())

    if remote_mode:
        ctx.ws.shutdown()
        return None
    if ctx.detach_requested:
        state = build_detach_state(ctx.ws, cfg)
        print("\r\n[detached (from session 0)]", flush=True)
        return state
    if ctx.hard_quit_requested:
        from plmux.session.store import resolve_state_path
        try:
            path = resolve_state_path(cfg)
            if path.is_file():
                path.unlink()
        except Exception:
            pass
        ctx.ws.shutdown()
        return None
    if cfg.session.auto_save:
        persist_session(ctx, cfg)
    ctx.ws.shutdown()
    return None


async def async_main(
    config_path: str | None,
    *,
    debug: bool = False,
    attach_mode: bool = False,
    remote_mode: bool = False,
    target_session: str | None = None,
) -> ServerState | None:
    cfg, ctx, ipc_conn, ipc_recv_task, frame_sleep, clock_task, status_task, pet_task, memory_task, config_watcher = await _init_app(
        config_path, debug, attach_mode, remote_mode, target_session,
    )

    web_task: asyncio.Task | None = None

    async def _start_web(port: int) -> None:
        try:
            from plmux.web.server import start_web_server
            web_cfg = ctx.ws.cfg.web
            await start_web_server(
                ctx.ws,
                host=web_cfg.host,
                port=port,
                tls_cert=web_cfg.tls_cert,
                tls_key=web_cfg.tls_key,
                auth_enabled=web_cfg.auth_enabled,
                config_tokens=web_cfg.tokens,
                config_readonly_tokens=web_cfg.readonly_tokens,
            )
            ctx.dirty = True
        except Exception:
            _logger.warning("web server start failed", exc_info=True)

    async def _maybe_start_web() -> None:
        nonlocal web_task
        if ctx._pending_web_port > 0:
            port = ctx._pending_web_port
            ctx._pending_web_port = 0
            await _start_web(port)
        if ctx._pending_web_stop:
            ctx._pending_web_stop = False
            try:
                from plmux.web.server import stop_web_server
                await stop_web_server()
                ctx.dirty = True
            except Exception:
                _logger.debug("web server stop failed", exc_info=True)
        if ctx._pending_web_restart:
            ctx._pending_web_restart = False
            web_cfg = ctx.ws.cfg.web
            await _start_web(web_cfg.port)

    with ctx.term.cbreak(), ctx.term.hidden_cursor():
        with Live(
            console=ctx.console,
            screen=cfg.ui.use_alternate_screen,
            auto_refresh=False,
        ) as live:
            try:
                from blessed.dec_modes import DecPrivateMode
                ctx.term._dec_mode_set_enabled(
                    DecPrivateMode.MOUSE_EXTENDED_SGR,
                    DecPrivateMode.MOUSE_REPORT_DRAG,
                )
            except Exception:
                _logger.debug("mouse mode setup fallback", exc_info=True)
                ctx.term.stream.write("\x1b[?1002h\x1b[?1006h")
                ctx.term.stream.flush()
                ctx.term._dec_mode_cache[1006] = 1
                ctx.term._dec_mode_cache[1002] = 1
            input_reader = InputReader(ctx.term)
            frame_count = 0
            plugins_loaded = False
            _last_resize_rows = 0
            _last_resize_cols = 0
            try:
                while ctx.running:
                    frame_start = time.monotonic()
                    frame_count += 1

                    if not plugins_loaded and frame_count >= 2:
                        plugins_loaded = True
                        load_config_hooks(cfg.hooks.hooks)
                        set_plugin_settings(cfg.extensions.plugin_settings)
                        load_plugins(cfg.extensions.enabled, cfg.extensions.search_paths)
                        emit_hook(
                            "app_started",
                            ExtensionContext(extra_config=dict(cfg.extra)),
                        )

                    tw, th = terminal_size(ctx.term)
                    ctx.console.size = ConsoleDimensions(width=tw, height=th)

                    inner_rows = max(cfg.ui.min_pane_rows, th - 2)
                    inner_cols = max(cfg.ui.min_pane_cols, tw)
                    ctx.content_rows = inner_rows
                    ctx.content_cols = inner_cols

                    if inner_rows != _last_resize_rows or inner_cols != _last_resize_cols:
                        _last_resize_rows = inner_rows
                        _last_resize_cols = inner_cols
                        ctx.dirty = True
                        if remote_mode and ipc_conn is not None:
                            try:
                                asyncio.ensure_future(ipc_conn.send_resize(inner_rows, inner_cols))
                            except Exception:
                                _logger.debug("IPC resize send failed", exc_info=True)

                    if not remote_mode:
                        TerminalSession.pump_all_sessions(ctx.ws.all_panes())
                        if ctx.dirty:
                            ctx.term.stream.flush()
                    else:
                        for sess in ctx.ws.sessions_list:
                            for w in sess.windows:
                                for s in w.panes:
                                    if s.is_remote and not s.closed:
                                        try:
                                            s._pump_queue()
                                        except Exception:
                                            _logger.debug("pump_queue failed for pane", exc_info=True)

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
                            ctx.prefix_key = parse_prefix_key(new_cfg.keys.prefix)
                            trig_type, trig_val = parse_cmdline_trigger(new_cfg.keys.command_line)
                            ctx.cmdline_trigger_type = trig_type
                            ctx.cmdline_trigger_val = trig_val
                            ctx.theme = load_theme(new_cfg.theme)
                            ctx.ws.theme = ctx.theme
                            new_enabled = set(new_cfg.extensions.enabled)
                            to_load = new_enabled - old_enabled
                            if to_load:
                                load_plugins(list(to_load), new_cfg.extensions.search_paths)
                        except Exception:
                            _logger.warning("config reload failed", exc_info=True)
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
                        _logger.debug("drain_web_keys failed", exc_info=True)

                    ctx.ws.web_mode = ctx.mode
                    ctx.ws.web_cmd_buffer = ctx.cmd_buffer
                    ctx.ws.clock_mode_pane = ctx.clock_mode_pane
                    ctx.ws.clock_str = ctx.clock_str

                    await _maybe_start_web()

                    try:
                        from plmux.web.server import notify_web_state_change
                        notify_web_state_change(ctx)
                    except Exception:
                        _logger.debug("notify_web_state_change failed", exc_info=True)

                    win = ctx.ws._window()
                    remain_on_exit = getattr(ctx.cfg.ui, "remain_on_exit", False)
                    dead_indices = [i for i, s in enumerate(win.panes) if s.closed and not s._dead]
                    if dead_indices:
                        if remain_on_exit:
                            for i in dead_indices:
                                win.panes[i]._dead = True
                            ctx.dirty = True
                        else:
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
                            dead = [i for i, s in enumerate(w.panes) if s.closed and not s._dead]
                            if remain_on_exit:
                                for di in dead:
                                    w.panes[di]._dead = True
                            else:
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

                    ctx.ws.sync_geometry(inner_rows, inner_cols)

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
                                copy_label = f"COPY \u2191{offset}/{sb_len}"
                            if ctx.copy_search_query:
                                n_matches = len(ctx.copy_search_matches)
                                copy_label += f" /{ctx.copy_search_query}({n_matches})"
                            if ctx.copy_search_active:
                                copy_label = f"SEARCH: {ctx.copy_search_query}_"
                            extra_items.append((copy_label, ctx.ws.theme.status_pane_style, "left"))
                        elif ctx.mode == "normal" and ctx.ws and ctx.ws.focus_pane is not None:
                            win_w = ctx.ws._window()
                            if win_w.focus_pane < len(win_w.panes):
                                fs = win_w.panes[win_w.focus_pane]
                                so = fs.scroll_offset
                                if so > 0:
                                    sb_len = fs.scrollback_len
                                    extra_items.append((f"\u2191{so}/{sb_len}", ctx.ws.theme.status_pane_style, "left"))
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
                            layout_list_tab=ctx.layout_list_tab,
                            layout_custom_cursor=ctx.layout_custom_cursor,
                            layout_builder=ctx.layout_builder,
                            custom_layouts=list(ctx.ws.cfg.custom_layouts),
                            current_panes=len(ctx.ws._window().panes),
                            clock_str=ctx.clock_str,
                            mode=ctx.mode.upper() if ctx.mode != "normal" else "NORMAL",
                            extra_items=extra_items,
                            completion_hints=ctx.completion_hints,
                            autosuggest_suggestion=ctx.autosuggest_suggestion,
                            memory_active=(ctx.mode == "memory"),
                            memory_cursor=ctx.memory_cursor,
                            plugin_overlay_name=ctx.mode if ctx.mode not in (
                                "normal", "prefix", "cmdline", "help", "esc_wait",
                                "copy", "theme_list", "session_list", "plugin_list",
                                "layout_list", "memory",
                            ) and get_plugin_overlay(ctx.mode) is not None else "",
                            plugin_state=ctx.plugin_state,
                            clock_mode_pane=ctx.clock_mode_pane,
                            pet_mode_pane=ctx.pet_mode_pane,
                            pet_type=ctx.pet_type,
                            pet_frame=ctx.pet_frame,
                            broadcast_enabled=ctx.broadcast_enabled,
                            display_panes_active=ctx.display_panes_active,
                            statusbar_style_active=(ctx.mode == "statusbar_style"),
                            statusbar_style_cursor=ctx.statusbar_style_cursor,
                            pane_border_style_active=(ctx.mode == "pane_border_style"),
                            pane_border_style_cursor=ctx.pane_border_style_cursor,
                            web_token_active=(ctx.mode == "web_token"),
                            web_token_cursor=ctx.web_token_cursor,
                            web_token_last_generated=ctx.web_token_last_generated,
                            web_token_last_mode=ctx.web_token_last_mode,
                        )
                        live.update(root)
                        live.refresh()
                        ctx.dirty = False

                    if ctx.display_panes_active and time.monotonic() > ctx.display_panes_until:
                        ctx.display_panes_active = False
                        ctx.dirty = True

                    elapsed = time.monotonic() - frame_start
                    poll_interval = min(frame_sleep, 0.004)
                    sleep_time = max(0.001, poll_interval - elapsed)
                    await asyncio.sleep(sleep_time)
            finally:
                try:
                    from blessed.dec_modes import DecPrivateMode
                    ctx.term._dec_mode_set_disabled(
                        DecPrivateMode.MOUSE_EXTENDED_SGR,
                        DecPrivateMode.MOUSE_REPORT_DRAG,
                    )
                except Exception:
                    _logger.debug("mouse mode disable fallback", exc_info=True)
                    ctx.term.stream.write("\x1b[?1002l\x1b[?1006l\x1b[?1000l")
                    ctx.term.stream.flush()
                    ctx.term._dec_mode_cache.pop(1006, None)
                    ctx.term._dec_mode_cache.pop(1002, None)
                input_reader.stop()
                config_watcher.stop()

    return await _shutdown_app(
        ctx, cfg, remote_mode, ipc_conn, ipc_recv_task,
        clock_task, status_task, pet_task, memory_task,
    )
