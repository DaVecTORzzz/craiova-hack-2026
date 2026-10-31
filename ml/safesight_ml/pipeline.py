"""Frame pipeline: detections -> zone rules -> blurred snapshot -> event."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import numpy as np

from .align import ZoneAligner
from .detector import Detector
from .events import Confidence, EdgeEvent, EventContext, TemporalConfidence
from .live import AnnotatedVideoWriter, AsyncLiveWriter, LiveFrameWriter, shrink_to_width
from .overlay import draw_alert, draw_overlay, zone_active
from .ppe import VestTracker, vest_sample
from .privacy import Blurrer
from .sink import Sink
from .zones import RuleEngine, Zone, ZoneMembership

EVENT_TYPE_BY_RULE = {
    "RESTRICTED": "RESTRICTED_ZONE",
    "PPE_REQUIRED": "NO_PPE",
}
ALERT_BANNER_S = 2.0

# Zone rule -> the vest state that counts as a violation. Only hi-vis is checked today:
# there is no detector for hard hats or ear defenders, so a zone that requires them
# raises nothing for them. They are also never treated as satisfied.
PPE_VIOLATION_STATE = {"hi_vis_vest": "no_vest"}


def triggers_event(zone: Zone, vest_state: str | None) -> bool:
    """Does this zone raise an event for a person in the given PPE state?

    ``RESTRICTED`` fires for anyone inside. ``PPE_REQUIRED`` fires only when a
    required item is provably missing, so an ``unknown`` vest state is silent:
    a low colour score on a small or partly hidden person is not a violation.
    Any other rule type is silent by default — mapped or not, it must not start
    raising person-in-zone events just because the type exists.
    """
    if zone.rule_type == "RESTRICTED":
        return True
    if zone.rule_type != "PPE_REQUIRED":
        return False
    return any(
        item in zone.required_ppe and vest_state == violation
        for item, violation in PPE_VIOLATION_STATE.items()
    )


class StageTimer:
    """Wall-clock seconds and call count per pipeline stage, for metrics.json."""

    def __init__(self) -> None:
        self.total_s: dict[str, float] = {}
        self.calls: dict[str, int] = {}
        self._lock = threading.Lock()

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            self.add(name, time.perf_counter() - started)

    def add(self, name: str, seconds: float) -> None:
        with self._lock:  # the live writer thread times its blur too
            self.total_s[name] = self.total_s.get(name, 0.0) + seconds
            self.calls[name] = self.calls.get(name, 0) + 1

    def summary(self) -> dict[str, dict[str, float]]:
        return {
            name: {
                "calls": self.calls[name],
                "total_s": round(total, 3),
                "mean_ms": round(1000 * total / self.calls[name], 2),
            }
            for name, total in self.total_s.items()
        }


class Pipeline:
    def __init__(
        self,
        *,
        camera_id: str,
        zones: list[Zone],
        detector: Detector,
        blurrer: Blurrer,
        sink: Sink,
        engine_on: bool,
        start_epoch: float | None = None,
        rules: RuleEngine | None = None,
        clock: Callable[[], float] | None = None,
        live_writer: LiveFrameWriter | AsyncLiveWriter | None = None,
        video_writer: AnnotatedVideoWriter | None = None,
        aligner: ZoneAligner | None = None,
        membership: ZoneMembership | None = None,
    ) -> None:
        self.camera_id = camera_id
        self.zones = [zone for zone in zones if zone.camera_id == camera_id]
        self.detector = detector
        self.blurrer = blurrer
        self.sink = sink
        self.engine_on = engine_on
        self.start_epoch = start_epoch if start_epoch is not None else time.time()
        self.rules = rules or RuleEngine()
        self.clock = clock
        self.live_writer = live_writer
        self.video_writer = video_writer
        self.aligner = aligner
        self.membership = membership or ZoneMembership()
        self.timer = StageTimer()
        self.frame_index = 0
        self._alert: tuple[str, float] | None = None
        # False while a looped clip replays a pass too soon after the last alert: the
        # live view keeps updating, but no new event is raised.
        self.emit_events = True
        self.vests = VestTracker()

    def set_config(self, zones: list[Zone], engine_on: bool) -> None:
        self.zones = [zone for zone in zones if zone.camera_id == self.camera_id]
        self.engine_on = engine_on

    def process(self, frame: np.ndarray, now_s: float) -> list[EdgeEvent]:
        self.rules.prune(now_s)
        self.membership.prune(now_s)
        self.vests.prune(now_s)
        with self.timer.stage("detect"):
            detections = self.detector.detect(frame, self.frame_index)
        boxes = [item.bbox for item in detections]
        zones: list[Zone] | None = self.zones
        if self.aligner is not None:
            with self.timer.stage("align"):
                self.aligner.update(frame)
            zones = self.aligner.zones(self.zones)
        # None: the camera view could not be matched to the reference, so no zone is trusted.
        zones_known = zones is not None
        zones = zones or []
        height, width = frame.shape[:2]
        # Updated every frame, also while events are muted, so the state never goes stale.
        in_zone = {
            (item.track_id, zone.id): self.membership.update(
                track_id=item.track_id, bbox=item.bbox, zone=zone, now=now_s, aspect=width / height
            )
            for item in detections
            for zone in zones
            if zone.rule_type in EVENT_TYPE_BY_RULE
        }
        # Colour is read from the raw frame, before blur; it never leaves this process.
        vest = {
            item.track_id: self.vests.update(
                item.track_id,
                vest_sample(frame, item.bbox),
                item.confidence,
                now_s,
                person_px=(item.bbox[3] - item.bbox[1]) * frame.shape[0],
            )
            for item in detections
        }
        # Highlighted, not just present: a compliant person in a PPE zone is left alone,
        # otherwise the operator sees red boxes and no incident to go with them.
        inside = {
            item.track_id
            for item in detections
            for zone in zones
            if zone_active(zone, self.engine_on)
            and in_zone.get((item.track_id, zone.id), False)
            and triggers_event(zone, vest.get(item.track_id))
        }
        live_frame: np.ndarray | None = None

        engine_on = self.engine_on

        def annotated(blurrer: Blurrer | None = None, max_width: int = 0) -> np.ndarray:
            # Blur first: the overlay must never hide or replace the privacy step.
            # Faces are searched on the full frame: downscaling first loses small faces
            # (cam01: 15 -> 7 YuNet hits at 1280 px), so it is not a free speed-up.
            with self.timer.stage("blur"):
                blurred = (blurrer or self.blurrer).blur(frame, boxes)
            # The overlay is drawn after the shrink: half the pixels, and it scales with width.
            blurred = shrink_to_width(blurred, max_width)
            with self.timer.stage("overlay"):
                return draw_overlay(blurred, zones, detections, inside, engine_on, vest, zones_known)

        if isinstance(self.live_writer, AsyncLiveWriter):
            # Rendered on the writer's thread; detection does not wait for the blur.
            # The writer blurs with YuNet passes around this frame; snapshots and the MP4
            # always use a fresh full pass of ``self.blurrer``.
            live_width = self.live_writer.writer.max_width
            self.live_writer.submit(frame, lambda blurrer: annotated(blurrer, live_width))
        elif self.live_writer is not None and self.live_writer.due():
            live_frame = annotated()  # full size: the snapshot and the MP4 reuse it
            with self.timer.stage("live_write"):
                self.live_writer.write(live_frame)

        emitted: list[EdgeEvent] = []

        for detection in detections if self.emit_events else ():
            for zone in zones:
                if zone.rule_type not in EVENT_TYPE_BY_RULE:
                    continue
                decision = self.rules.observe(
                    track_id=detection.track_id,
                    zone=zone,
                    # A PPE zone only counts while the requirement is actually broken:
                    # a person who puts the vest on stops accumulating, and one who takes
                    # it off starts fresh after the cooldown.
                    in_zone=in_zone[(detection.track_id, zone.id)]
                    and triggers_event(zone, vest.get(detection.track_id)),
                    now=now_s,
                    engine_on=self.engine_on,
                )
                if decision is None:
                    continue

                event_epoch = self.clock() if self.clock is not None else self.start_epoch + now_s
                detected_at = datetime.fromtimestamp(event_epoch, tz=UTC)
                event_id = f"evt_{self.camera_id}_{int(event_epoch * 1000)}_{detection.track_id}"

                if live_frame is None:
                    live_frame = annotated()
                with self.timer.stage("snapshot"):
                    snapshot_url = self.sink.store_snapshot(event_id, live_frame)

                event = EdgeEvent(
                    event_id=event_id,
                    type=EVENT_TYPE_BY_RULE[zone.rule_type],  # type: ignore[arg-type]
                    severity=zone.severity,
                    camera_id=self.camera_id,
                    zone_id=zone.id,
                    track_id=detection.track_id,
                    confidence=Confidence(
                        detector=detection.confidence,
                        temporal=TemporalConfidence(
                            seen=decision.seen,
                            window=decision.window,
                        ),
                    ),
                    duration_s=round(decision.duration_s, 3),
                    context=EventContext(engine_on=self.engine_on),
                    snapshot_url=snapshot_url,
                    model=self.detector.model_name,
                    detected_at=detected_at,
                )
                with self.timer.stage("emit"):
                    self.sink.emit(event)
                emitted.append(event)

        if self.video_writer is not None:
            out = live_frame if live_frame is not None else annotated()
            if emitted:
                last = emitted[-1]
                self._alert = (f"ALERTA {last.type} | {last.zone_id} | persoana #{last.track_id}", now_s)
            if self._alert is not None and now_s - self._alert[1] <= ALERT_BANNER_S:
                out = draw_alert(out, self._alert[0])
            with self.timer.stage("video_write"):
                self.video_writer.write(out)

        self.frame_index += 1
        return emitted
