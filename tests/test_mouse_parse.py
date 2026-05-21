from plmux.app import _parse_mouse_event


def test_parse_sgr_press_and_release():
    # SGR press: \x1b[<0;12;5M  (button 0 at x=12 y=5)
    seq = "\x1b[<0;12;5M"
    me = _parse_mouse_event(seq)
    assert me is not None
    assert me["x"] == 11
    assert me["y"] == 4
    assert me["button"] == 0
    assert me["type"] == "M"


def test_parse_legacy_click():
    # legacy sequence: \x1b[M cb cx cy
    seq = "\x1b[M" + chr(32 + 0) + chr(32 + 10) + chr(32 + 6)
    me = _parse_mouse_event(seq)
    assert me is not None
    assert me["x"] == 9
    assert me["y"] == 5