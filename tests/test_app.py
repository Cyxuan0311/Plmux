
import plmux.app as app


def test_parse_prefix_key_defaults():
    assert app._parse_prefix_key(None) == chr(2)
    assert app._parse_prefix_key("ctrl+a") == chr(1)
    assert app._parse_prefix_key("^b") == chr(2)


def test_parse_cmdline_trigger_defaults():
    assert app._parse_cmdline_trigger(None) == ("char", ":")
    assert app._parse_cmdline_trigger(":") == ("char", ":")
    assert app._parse_cmdline_trigger("ctrl+shift+:") == ("chord", "ctrl+shift+;")


class DummyKey:
    def __init__(self, code):
        self.code = code


def test_match_chord_raw_int_code():
    k = DummyKey(59)
    # int path expects modifiers attr
    k.modifiers = 5
    assert app._match_chord_raw(k, "ctrl+shift+;") is True


def test_match_chord_raw_str_code():
    # string form: "\x1b[59;5u"
    k = DummyKey("\x1b[59;5u")
    assert app._match_chord_raw(k, "ctrl+shift+;") is True


def test_apply_tab_completion_single(monkeypatch):
    import plmux.modes.cmdline as cmdline_mod

    def fake_get_completions(buf):
        if buf.strip() == "":
            return ["attach", "ls"]
        if buf.strip() == "a":
            return ["attach"]
        return []

    monkeypatch.setattr(cmdline_mod, "get_completions", fake_get_completions)

    assert app._apply_tab_completion("") == ("", "attach  ls")
    assert app._apply_tab_completion("a") == ("attach ", "")
    assert app._apply_tab_completion("attach ") == ("attach ", "")
