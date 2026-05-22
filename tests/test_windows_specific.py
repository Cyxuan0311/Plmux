import sys
import types
import time

import plmux.app as app
from plmux.config.loader import default_user_config_dir


def test_win_setup_timer_no_error(monkeypatch):
    fake_ctypes = types.SimpleNamespace()
    fake_winmm = types.SimpleNamespace(timeBeginPeriod=lambda x: 0)
    fake_ctypes.windll = types.SimpleNamespace(winmm=fake_winmm)
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    app._win_setup_timer()


def test_input_reader_get_all(monkeypatch):
    class DummyTerm:
        def inkey(self):
            return "X"

    reader = app._InputReader(DummyTerm())
    try:
        time.sleep(0.05)
        keys = reader.get_all()
        assert isinstance(keys, list)
    finally:
        reader.stop()


def test_input_reader_stop():
    class DummyTerm:
        def inkey(self):
            return None

    reader = app._InputReader(DummyTerm())
    reader.stop()
    assert reader._stop.is_set()


def test_default_user_config_dir_windows(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # Avoid changing global sys.platform/os.name (breaks pytest). Patch only the loader module.
    import plmux.config.loader as loader
    monkeypatch.setattr(loader.sys, "platform", "win32", raising=False)
    monkeypatch.setattr(loader.os, "name", "nt", raising=False)
    def test_default_user_config_dir_nonwindows(tmp_path, monkeypatch):
        # Ensure default_user_config_dir returns a valid path on this platform
        p = default_user_config_dir()
        assert p.name == "plmux"
