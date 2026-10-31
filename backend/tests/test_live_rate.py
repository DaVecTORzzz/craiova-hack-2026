"""The live rate is measured from the frames that actually reached the backend."""

from __future__ import annotations

import time

from app.services.live_rate import LiveRate


def test_no_frames_means_unknown_not_zero():
    """A camera nobody watches renders nothing; reporting 0 fps would look like a fault."""
    rate = LiveRate()
    assert rate.fps("stand12") is None
    assert rate.snapshot() == {}


def test_counts_only_new_frames():
    rate = LiveRate(window_s=5.0)
    for version in range(5):
        rate.observe("stand12", version)
    first = rate.fps("stand12")
    assert first is not None

    # same mtime again: the poll saw no new frame, so the rate must not change
    for _ in range(10):
        rate.observe("stand12", 4)
    assert rate.fps("stand12") == first


def test_a_stalled_edge_stops_reporting():
    rate = LiveRate(window_s=0.2)
    rate.observe("stand12", 1)
    time.sleep(0.01)
    rate.observe("stand12", 2)
    assert rate.fps("stand12") is not None

    time.sleep(0.25)  # nothing new arrives
    assert rate.fps("stand12") is None


def test_missing_file_is_ignored():
    rate = LiveRate()
    assert rate.observe("stand12", None) is None
    assert rate.snapshot() == {}


def test_snapshot_lists_only_cameras_with_a_rate():
    rate = LiveRate()
    rate.observe("stand12", 1)
    time.sleep(0.01)
    rate.observe("stand12", 2)
    rate.observe("taxiway-b", None)
    assert set(rate.snapshot()) == {"stand12"}
