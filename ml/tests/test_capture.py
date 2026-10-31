from __future__ import annotations

import threading

import numpy as np

from safesight_ml.capture import LatestFrameReader, is_live_source


class GatedCapture:
    """Delivers frame i only after the test releases it; then reports end of stream."""

    def __init__(self, count: int) -> None:
        self.count = count
        self.index = 0
        self.gate = threading.Semaphore(0)
        self.delivered = threading.Semaphore(0)
        self.released = False

    def read(self):
        self.gate.acquire()
        if self.index >= self.count:
            return False, None
        frame = np.full((2, 2, 3), self.index, dtype=np.uint8)
        self.index += 1
        self.delivered.release()
        return True, frame

    def release(self) -> None:
        self.released = True


def _deliver(capture: GatedCapture, n: int) -> None:
    for _ in range(n):
        capture.gate.release()
        assert capture.delivered.acquire(timeout=2)


def test_reader_returns_newest_frame_and_counts_dropped():
    capture = GatedCapture(5)
    reader = LatestFrameReader(capture)

    _deliver(capture, 3)
    ok, frame, seq = reader.read(timeout_s=2)
    assert ok and seq == 2 and frame[0, 0, 0] == 2
    assert reader.dropped == 2

    _deliver(capture, 1)
    ok, frame, seq = reader.read(timeout_s=2)
    assert ok and seq == 3 and frame[0, 0, 0] == 3
    assert reader.dropped == 2

    capture.gate.release()  # frame 4
    capture.gate.release()  # end of stream
    ok, frame, seq = reader.read(timeout_s=2)
    assert ok and seq == 4
    ok, frame, _ = reader.read(timeout_s=2)
    assert not ok and frame is None

    reader.release()
    assert capture.released


def test_reader_does_not_return_the_same_frame_twice():
    capture = GatedCapture(2)
    reader = LatestFrameReader(capture)
    _deliver(capture, 1)
    assert reader.read(timeout_s=2)[0]
    ok, _, _ = reader.read(timeout_s=0.05)
    assert not ok
    capture.gate.release()
    capture.gate.release()
    reader.release()


def test_live_sources_are_streams_not_files():
    assert is_live_source("rtsp://127.0.0.1:8554/stand12")
    assert is_live_source("HTTP://cam.local/stream")
    assert not is_live_source("../data/videos/clip.mp4")


def test_webcam_sources_are_live_and_parse_the_device_index():
    from safesight_ml.capture import webcam_index

    assert webcam_index("webcam") == 0
    assert webcam_index("webcam:2") == 2
    assert webcam_index("WEBCAM:1") == 1
    assert webcam_index("webcam:x") is None
    assert webcam_index("clip.mp4") is None
    assert is_live_source("webcam:0")
    assert not is_live_source("webcam.mp4")
