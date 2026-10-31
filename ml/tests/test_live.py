from __future__ import annotations

import numpy as np

from safesight_ml.detector import Detection, FakeDetector
from safesight_ml.live import LiveFrameWriter
from safesight_ml.pipeline import Pipeline
from safesight_ml.run import main as run_main
from safesight_ml.zones import Zone

ZONE = Zone(
    id="engine-left",
    camera_id="stand12",
    name="Motor stâng",
    rule_type="RESTRICTED",
    active_when="engine_on",
    severity="CRITICAL",
    debounce_s=1.0,
    polygon=[(0.08, 0.30), (0.66, 0.30), (0.66, 0.90), (0.08, 0.90)],
)


class RecordingSink:
    def store_snapshot(self, event_id: str, frame: np.ndarray) -> str:
        return f"/snapshots/{event_id}.jpg"

    def emit(self, event) -> None:
        pass


class RecordingBlurrer:
    def __init__(self) -> None:
        self.calls = 0

    def blur(self, frame: np.ndarray, boxes=()) -> np.ndarray:
        self.calls += 1
        return frame


def test_live_writer_writes_latest_frame(tmp_path):
    writer = LiveFrameWriter(tmp_path, "stand12", interval_s=0)
    assert writer.due()
    assert writer.write(np.zeros((36, 64, 3), dtype=np.uint8))
    assert (tmp_path / "stand12.jpg").is_file()


def test_fake_cli_writes_live_frame(tmp_path):
    code = run_main(
        [
            "--fake",
            "--engine-on",
            "--dry-run",
            "--max-frames",
            "5",
            "--out",
            str(tmp_path / "out"),
            "--live-dir",
            str(tmp_path / "live"),
        ]
    )
    assert code == 0
    assert (tmp_path / "live" / "stand12.jpg").is_file()


def test_pipeline_writes_live_frame_and_reuses_blur(tmp_path):
    detections = [[Detection(track_id=1, bbox=(0.50, 0.20, 0.60, 0.60), confidence=0.91)]]
    blurrer = RecordingBlurrer()
    writer = LiveFrameWriter(tmp_path, "stand12", interval_s=0)
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(detections * 20),
        blurrer=blurrer,
        sink=RecordingSink(),
        engine_on=True,
        live_writer=writer,
    )
    for step in range(20):
        pipeline.process(np.zeros((360, 640, 3), dtype=np.uint8), now_s=step / 10)

    assert (tmp_path / "stand12.jpg").is_file()
    assert blurrer.calls >= 1


def test_live_writer_downscales_and_leaves_no_temp_file(tmp_path):
    import cv2

    writer = LiveFrameWriter(tmp_path, "stand12", interval_s=0, max_width=640)
    assert writer.write(np.zeros((2160, 3840, 3), dtype=np.uint8))
    image = cv2.imread(str(tmp_path / "stand12.jpg"))
    assert image.shape[:2] == (360, 640)
    assert [p.name for p in tmp_path.iterdir()] == ["stand12.jpg"]


def test_overlay_marks_person_in_active_zone_red():
    from safesight_ml.overlay import RED, GREEN, draw_overlay

    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    inside = Detection(track_id=1, bbox=(0.20, 0.40, 0.30, 0.80), confidence=0.9)
    outside = Detection(track_id=2, bbox=(0.80, 0.05, 0.90, 0.20), confidence=0.8)

    out = draw_overlay(frame, [ZONE], [inside, outside], {1}, engine_on=True)

    assert not np.array_equal(out, frame)
    assert np.array_equal(frame, np.zeros_like(frame))  # input untouched
    assert tuple(out[int(0.60 * 360), int(0.20 * 640)]) == RED  # left edge of box 1
    assert tuple(out[int(0.15 * 360), int(0.90 * 640) - 1]) == GREEN  # right edge of box 2


def test_pipeline_snapshot_is_annotated_after_blur():
    detections = [[Detection(track_id=1, bbox=(0.20, 0.40, 0.30, 0.80), confidence=0.91)]]

    class FrameSink(RecordingSink):
        frames: list[np.ndarray] = []

        def store_snapshot(self, event_id, frame):
            self.frames.append(frame)
            return super().store_snapshot(event_id, frame)

    sink = FrameSink()
    blurrer = RecordingBlurrer()
    pipeline = Pipeline(
        camera_id="stand12",
        zones=[ZONE],
        detector=FakeDetector(detections * 20),
        blurrer=blurrer,
        sink=sink,
        engine_on=True,
    )
    blank = np.zeros((360, 640, 3), dtype=np.uint8)
    for step in range(20):
        pipeline.process(blank, now_s=step / 10)

    assert len(sink.frames) == 1
    assert blurrer.calls == 1
    assert sink.frames[0].any()


def test_fake_cli_writes_annotated_video(tmp_path):
    import cv2

    video = tmp_path / "annotated.mp4"
    code = run_main(
        ["--fake", "--engine-on", "--dry-run", "--max-frames", "30", "--out", str(tmp_path / "out"), "--annotated-video", str(video)]
    )
    assert code == 0
    capture = cv2.VideoCapture(str(video))
    assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 30
    capture.release()


def test_hivis_ratio_separates_vest_from_dark_jacket():
    from safesight_ml.ppe import HIVIS_MIN, VestTracker, hivis_ratio

    frame = np.full((360, 640, 3), 60, dtype=np.uint8)
    frame[100:300, 100:200] = (0, 120, 255)  # fluorescent orange (BGR) person
    vest_box = (100 / 640, 80 / 360, 200 / 640, 320 / 360)
    dark_box = (400 / 640, 80 / 360, 500 / 640, 320 / 360)

    assert hivis_ratio(frame, vest_box) > HIVIS_MIN
    assert hivis_ratio(frame, dark_box) < HIVIS_MIN
    assert hivis_ratio(frame, (0.5, 0.5, 0.5, 0.5)) is None

    tracker = VestTracker(alpha=0.5)
    tracker.update(1, 1.0)
    assert tracker.score(1) == 1.0
    tracker.update(1, 0.0)
    assert tracker.score(1) == 0.5
    tracker.update(1, None)
    assert tracker.score(1) == 0.5


def test_async_live_writer_blurs_a_frame_with_faces_found_after_it(tmp_path):
    import threading
    import time

    from safesight_ml.live import AsyncLiveWriter

    gate = threading.Event()

    class SlowFaces:
        """A face appears in frame 2; YuNet only sees it there, after frame 1 was submitted."""

        def detect_faces(self, frame):
            gate.wait(2)
            return [(40, 40, 20, 20)] if frame[0, 0, 0] == 2 else []

    rendered = []

    def render_for(frame):
        def render(blurrer):
            out = blurrer.blur(frame, [])
            rendered.append((int(frame[0, 0, 0]), out))
            return out

        return render

    writer = AsyncLiveWriter(LiveFrameWriter(tmp_path, "stand12"), faces=SlowFaces(), max_fps=1000)
    frames = []
    for value in (1, 2):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        frame[0, 0] = value
        frame[40:60, 40:60] = 255  # the "face" square, sharp edges
        frames.append(frame)
        writer.submit(frame, render_for(frame))
    time.sleep(0.2)
    assert rendered == []  # held until a YuNet pass after it has finished
    gate.set()
    deadline = time.time() + 3
    while len(rendered) < 1 and time.time() < deadline:
        time.sleep(0.02)
    writer.close()

    assert rendered, "no live frame written"
    value, out = rendered[0]
    # Frame 1 had no face of its own pass; it is blurred with the face found in frame 2.
    assert value == 1
    assert out[40:60, 40:60].mean() < 128 < frames[0][40:60, 40:60].mean()
