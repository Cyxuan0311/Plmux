"""Tests for command-line mode tab completion."""

from plmux.modes.cmdline import _apply_tab_completion


class TestTabCompletion:
    def test_no_completion_list_returns_empty(self):
        buf, hints, lst, idx = _apply_tab_completion("split", None, -1)
        assert isinstance(buf, str)
        assert isinstance(hints, str)
        assert isinstance(lst, list)

    def test_empty_cmd_buffer(self):
        buf, hints, lst, idx = _apply_tab_completion("", None, -1)
        assert isinstance(buf, str)

    def test_single_completion_cycles_properly(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "split", ["split-window"], 0,
        )
        assert "split-window" in buf
        assert idx == 0

    def test_multiple_completions_cycle(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "s", ["split-window", "swap-pane"], 0,
        )
        assert idx == 1

    def test_completion_cycles_back_to_start(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "s", ["a", "b"], 1,
        )
        assert idx == 0

    def test_completion_with_multiple_parts(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "split-window -h 10", ["10", "20"], -1,
        )
        assert buf.endswith(" ")

    def test_empty_completion_list(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "split", [], 0,
        )
        assert lst == []
        assert idx == -1

    def test_single_item_completion(self):
        buf, hints, lst, idx = _apply_tab_completion(
            "split", ["split-window"], -1,
        )
        assert lst == ["split-window"]
        assert idx == 0
