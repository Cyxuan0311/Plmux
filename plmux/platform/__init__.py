"""Platform abstraction: PTY factory, shell detection, clipboard."""

from plmux.platform.pty_factory import spawn_pty as spawn_pty, _WindowsPtyProcess as _WindowsPtyProcess
from plmux.platform.pty_handle import PtyHandle as PtyHandle
from plmux.platform.shell import default_shell_argv as default_shell_argv, resolve_shell_argv as resolve_shell_argv, ensure_interactive_shell as ensure_interactive_shell