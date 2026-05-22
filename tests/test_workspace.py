from plmux.config.schema import PlmuxConfig
from plmux.ui.theme import Theme


class DummySession:
    def __init__(self, rows, cols, shell=None, env=None, on_update=None):
        self.rows = rows
        self.cols = cols
        self.argv = ["/bin/sh"]
        self.proc = type("P", (), {"pid": 12345})()
        self._closed = False

    def close(self):
        self._closed = True

    def resize(self, rows, cols):
        self.rows = rows
        self.cols = cols


def make_workspace(monkeypatch):
    # Replace TerminalSession with DummySession to avoid spawning PTYs
    import plmux.workspace as workspace
    monkeypatch.setattr(workspace, "TerminalSession", DummySession)
    cfg = PlmuxConfig()
    theme = Theme()
    return workspace.PaneWorkspace(cfg, theme)


def test_split_and_focus(monkeypatch):
    ws = make_workspace(monkeypatch)
    initial_count = len(ws.sessions)
    ws.split("row")
    assert len(ws.sessions) == initial_count + 1
    assert ws.focus_pane == len(ws.sessions) - 1


def test_new_and_close_window(monkeypatch):
    ws = make_workspace(monkeypatch)
    ws.new_window()
    assert len(ws.windows) >= 2
    cur = ws.current_window
    assert ws.close_window() is True
    assert ws.current_window != cur or len(ws.windows) == 1


def test_focus_next_prev(monkeypatch):
    ws = make_workspace(monkeypatch)
    # create few panes
    ws.split("row")
    ws.split("row")
    order = [i for i in range(len(ws.sessions))]
    ws.focus_pane = order[0]
    ws.focus_next()
    assert ws.focus_pane in order
    ws.focus_prev()
    assert ws.focus_pane in order


def test_cycle_layout_builders(monkeypatch):
    ws = make_workspace(monkeypatch)
    # add panes so layout functions have >1 pane
    ws.split("row")
    ws.split("row")
    ws.cycle_layout()
    assert ws.tree is not None
