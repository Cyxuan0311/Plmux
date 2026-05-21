"""Tests for the EventBus system."""

from plmux.utils.event_bus import EventBus, get_event_bus, reset_event_bus


class TestEventBus:
    def setup_method(self):
        reset_event_bus()

    def teardown_method(self):
        reset_event_bus()

    def test_sync_emit_and_handler(self):
        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        bus.on("test.event", handler)
        bus.emit("test.event", data="hello")
        assert received == ["hello"]

    def test_multiple_handlers(self):
        bus = EventBus()
        received = []

        def h1(data):
            received.append(("h1", data))

        def h2(data):
            received.append(("h2", data))

        bus.on("test.event", h1)
        bus.on("test.event", h2)
        bus.emit("test.event", data=42)
        assert len(received) == 2

    def test_off_removes_handler(self):
        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        bus.on("test.event", handler)
        bus.off("test.event", handler)
        bus.emit("test.event", data="x")
        assert received == []

    def test_default_bus_singleton(self):
        reset_event_bus()
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_default_bus_emit(self):
        received = []

        def handler(prev_mode, new_mode):
            received.append((prev_mode, new_mode))

        bus = get_event_bus()
        bus.on("mode.changed", handler)
        bus.emit("mode.changed", prev_mode="normal", new_mode="prefix")
        assert received == [("normal", "prefix")]

    def test_handler_exception_does_not_crash(self):
        bus = EventBus()
        received = []

        def bad_handler(data):
            raise RuntimeError("boom")

        def good_handler(data):
            received.append(data)

        bus.on("test.event", bad_handler)
        bus.on("test.event", good_handler)
        bus.emit("test.event", data="ok")
        assert received == ["ok"]

    def test_clear_removes_all(self):
        bus = EventBus()
        received = []

        def handler(data):
            received.append(data)

        bus.on("test.event", handler)
        bus.clear()
        bus.emit("test.event", data="x")
        assert received == []