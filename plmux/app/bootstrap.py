"""Application bootstrap: CLI parsing, config loading, and entry point."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys

from plmux import __version__
from plmux.cli.commands import cmd_list_sessions, cmd_list_windows, cmd_kill_server, new_session, rename_window, rename_session
from plmux.daemon import is_server_alive, run_server, is_windows, kill_server
from plmux.daemon.server import run_daemon_from_config
from plmux.state_bridge import serve_mode, spawn_server_subprocess


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="plmux",
        description="Lightweight tmux-like PTY multiplexer",
        epilog=(
            "Examples:\n"
            "  plmux                  Start a new session\n"
            "  plmux ls               List active sessions\n"
            "  plmux attach           Attach to an existing session\n"
            "  plmux kill-server      Kill the running daemon\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", title="commands", metavar="COMMAND")

    sub.add_parser("ls", aliases=["list-sessions"], help="List active sessions")
    ls_p = sub.add_parser("lsw", aliases=["list-windows"], help="List windows")
    ls_p.add_argument("-p", "--panes", action="store_true", help="Also list panes in each window")
    attach_p = sub.add_parser("attach", aliases=["a"], help="Attach to an existing session")
    attach_p.add_argument("session", nargs="?", default=None, help="Pane index to focus (optional)")
    sub.add_parser("kill-server", help="Kill the running plmux daemon")
    new_sess_p = sub.add_parser("new-session", help="Create a new detached plmux session")
    new_sess_p.add_argument("-s", "--session-name", default=None, help="Name for the new session")
    rn_win_p = sub.add_parser("rename-window", help="Set a name for a window in saved session")
    rn_win_p.add_argument("index", type=int, help="Window index")
    rn_win_p.add_argument("name", help="New window name")
    rn_sess_p = sub.add_parser("rename-session", help="Set a name for the saved session")
    rn_sess_p.add_argument("name", help="New session name")
    sub.add_parser("swap-pane", help="Swap two pane indices in saved session")

    p.add_argument("--config", "-c", default=None, help="Path to config.json")
    p.add_argument("--debug", "-d", action="store_true", default=False, help="Enable debug logging to plmux_debug.log")
    p.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--serve", default=None, help=argparse.SUPPRESS)
    p.add_argument("--daemon", action="store_true", default=False, help=argparse.SUPPRESS)
    return p


def _ensure_server_running(cfg_path: str | None) -> None:
    """Start the daemon server if not already running."""
    if is_server_alive():
        return

    from plmux.config.loader import load_config
    from plmux.workspace import try_load_snapshot

    cfg = load_config(cfg_path)
    snap = try_load_snapshot(cfg) if cfg.session.auto_save else None

    if hasattr(os, "fork"):
        pid = os.fork()
        if pid == 0:
            os.setsid()
            devnull = os.open(os.devnull, os.O_RDWR)
            log_fd = os.open(os.path.expanduser("~/.config/plmux/daemon.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            os.dup2(devnull, 0)
            os.dup2(devnull, 1)
            os.dup2(log_fd, 2)
            if devnull > 2:
                os.close(devnull)
            if log_fd > 2:
                os.close(log_fd)
            asyncio.run(run_daemon_from_config(cfg, restore=snap))
            os._exit(0)
        else:
            import time as _time
            for _ in range(100):
                if is_server_alive():
                    return
                _time.sleep(0.05)
    elif is_windows():
        cmd = [sys.executable, "-m", "plmux", "--daemon"]
        if cfg_path:
            cmd.extend(["--config", cfg_path])
        log_dir = os.path.expanduser("~/.config/plmux")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "daemon.log")
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": open(log_path, "w"),
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        }
        try:
            subprocess.Popen(cmd, **kwargs)
        except Exception:
            pass
        finally:
            try:
                kwargs["stderr"].close()
            except Exception:
                pass
        import time as _time
        for _ in range(100):
            if is_server_alive():
                return
            _time.sleep(0.05)
    else:
        asyncio.run(run_daemon_from_config(cfg, restore=snap))


def run(argv: list[str] | None = None) -> None:
    from plmux.app.event_loop import async_main

    argv = argv if argv is not None else sys.argv[1:]
    p = build_arg_parser()
    ns = p.parse_args(argv)

    if ns.serve:
        serve_mode(ns.serve)
        return

    if ns.daemon:
        from plmux.config.loader import load_config
        from plmux.workspace import try_load_snapshot
        cfg = load_config(ns.config)
        snap = try_load_snapshot(cfg) if cfg.session.auto_save else None
        asyncio.run(run_daemon_from_config(cfg, restore=snap))
        return

    if ns.command in ("ls", "list-sessions"):
        cmd_list_sessions()
        return

    if ns.command in ("lsw", "list-windows"):
        cmd_list_windows(panes=getattr(ns, "panes", False))
        return

    if ns.command == "kill-server":
        cmd_kill_server()
        return

    if ns.command == "new-session":
        session_name = getattr(ns, "session_name", None)
        new_session(session_name=session_name)
        return

    if ns.command == "rename-window":
        rename_window(ns.index, ns.name)
        return

    if ns.command == "rename-session":
        rename_session(ns.name)
        return

    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    attach_mode = ns.command in ("attach", "a")
    target_session = getattr(ns, "session", None)

    use_remote = is_server_alive() or attach_mode

    if is_windows() and not use_remote:
        use_remote = True

    if use_remote:
        _ensure_server_running(ns.config)
        try:
            asyncio.run(async_main(ns.config, debug=ns.debug, remote_mode=True, target_session=target_session))
        except (ConnectionRefusedError, FileNotFoundError, ConnectionError) as e:
            print(f"Error: Could not connect to plmux server: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            detach_state = asyncio.run(async_main(ns.config, debug=ns.debug, attach_mode=False, target_session=target_session))
            if detach_state is not None:
                if hasattr(os, "fork"):
                    pid = os.fork()
                    if pid == 0:
                        os.setsid()
                        devnull = os.open(os.devnull, os.O_RDWR)
                        log_fd = os.open(os.path.expanduser("~/.config/plmux/daemon.log"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        os.dup2(devnull, 0)
                        os.dup2(devnull, 1)
                        os.dup2(log_fd, 2)
                        if devnull > 2:
                            os.close(devnull)
                        if log_fd > 2:
                            os.close(log_fd)
                        asyncio.run(run_server(detach_state))
                        os._exit(0)
                elif is_windows():
                    spawn_server_subprocess(detach_state)
                    import time as _time
                    for _ in range(50):
                        if is_server_alive():
                            break
                        _time.sleep(0.1)
                else:
                    asyncio.run(run_server(detach_state))
        except KeyboardInterrupt:
            pass
        except (ConnectionRefusedError, FileNotFoundError, ConnectionError) as e:
            print(f"Error: Could not connect to plmux server: {e}", file=sys.stderr)
            sys.exit(1)
