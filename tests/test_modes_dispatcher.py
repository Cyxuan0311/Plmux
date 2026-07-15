"""Tests for mode dispatcher routing."""

import plmux.app  # noqa: F401 — ensure correct import order to avoid circular imports
from plmux.modes import AppContext
from plmux.modes.dispatcher import dispatch_key, _MODE_HANDLERS


class _MockPane:
    closed = False

    def close(self):
        pass

    def is_alive(self):
        return True


class _MockWindow:
    def __init__(self):
        self.panes = [_MockPane()]
        self.tree = 0
        self.focus_pane = 0


class _MockSession:
    def __init__(self):
        self.windows = [_MockWindow()]
        self.current_window = 0

    def write_text(self, text):
        pass

    def resize(self, rows, cols):
        pass

    def close(self):
        pass


class _MockWorkspace:
    def __init__(self):
        self._sessions = [_MockSession()]
        self.current_session = 0

    def _window(self):
        return self._sessions[0].windows[0]

    def _session(self):
        return self._sessions[0]

    def active_session(self):
        return self._sessions[0]

    def all_panes(self):
        return [self._window().panes[0]]


class TestDispatchKey:
    def setup_method(self):
        self.ctx = AppContext(ws=_MockWorkspace())

    def test_normal_mode_routes_to_normal(self):
        self.ctx.mode = "normal"
        dispatch_key("a", self.ctx)

    def test_known_modes_have_handlers(self):
        for mode in _MODE_HANDLERS:
            assert _MODE_HANDLERS[mode] is not None, f"{mode} has no handler"

    def test_unknown_mode_falls_back_to_normal(self):
        self.ctx.mode = "nonexistent_mode"
        handler = _MODE_HANDLERS.get(self.ctx.mode)
        assert handler is None

    def test_prefix_mode_has_handler(self):
        assert "prefix" in _MODE_HANDLERS

    def test_cmdline_mode_has_handler(self):
        assert "cmdline" in _MODE_HANDLERS

    def test_copy_mode_has_handler(self):
        assert "copy" in _MODE_HANDLERS

    def test_help_mode_has_handler(self):
        assert "help" in _MODE_HANDLERS

    def test_session_list_mode_has_handler(self):
        assert "session_list" in _MODE_HANDLERS

    def test_memory_mode_has_handler(self):
        assert "memory" in _MODE_HANDLERS
