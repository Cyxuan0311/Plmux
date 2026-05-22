"""Tests for PerfStats and FrameProfiler in debug_log."""

from plmux.debug_log import PerfStats, PerfTimer, FrameProfiler


class TestPerfStats:
    def test_record_and_report(self):
        s = PerfStats("test")
        s.record(1.0)
        s.record(2.0)
        s.record(3.0)
        s.report(interval_s=0.0)
        assert s._count == 3
        assert s._min_ms == 1.0
        assert s._max_ms == 3.0
        assert abs(s._total_ms - 6.0) < 0.001

    def test_reset(self):
        s = PerfStats("test")
        s.record(1.0)
        s.record(2.0)
        s.reset()
        assert s._count == 0
        assert s._min_ms == float("inf")
        assert s._max_ms == 0.0
        assert s._total_ms == 0.0

    def test_empty_no_crash(self):
        s = PerfStats("test")
        s.report(interval_s=0.0)


class TestFrameProfiler:
    def test_end_frame_records_phases(self):
        fp = FrameProfiler(slow_threshold_ms=100.0)
        fp.end_frame({"input": 5.0, "pty": 3.0, "render": 2.0})
        assert fp._frame_count == 1
        assert fp.phase("input")._count == 1
        assert fp.phase("pty")._count == 1
        assert fp.phase("render")._count == 1

    def test_slow_frame_detection(self):
        fp = FrameProfiler(slow_threshold_ms=10.0)
        fp.end_frame({"input": 5.0, "pty": 6.0, "render": 3.0})


class TestPerfTimer:
    def test_elapsed_ms(self):
        t = PerfTimer()
        ms = t.elapsed_ms()
        assert ms >= 0

    def test_elapsed_us(self):
        t = PerfTimer()
        us = t.elapsed_us()
        assert us >= 0

    def test_reset(self):
        t = PerfTimer()
        t.reset()
        ms = t.elapsed_ms()
        assert ms >= 0
        assert ms < 1000