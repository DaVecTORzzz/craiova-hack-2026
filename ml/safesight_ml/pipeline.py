"""Frame pipeline: detections -> zone rules -> blurred snapshot -> event."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np

from .detector import Detector
from .events import Confidence, EdgeEvent, EventContext, TemporalConfidence
from .live import LiveFrameWriter
from .overlay import draw_overlay, zone_active
from .privacy import Blurrer
from .sink import Sink
from .zones import RuleEngine, Zone, point_in_polygon

EVENT_TYPE_BY_RULE = {
    "RESTRICTED": "RESTRICTED_ZONE",
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
        live_writer: LiveFrameWriter | None = None,
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
        self.frame_index = 0

    def set_config(self, zones: list[Zone], engine_on: bool) -> None:
        self.zones = [zone for zone in zones if zone.camera_id == self.camera_id]
        self.engine_on = engine_on

    def process(self, frame: np.ndarray, now_s: float) -> list[EdgeEvent]:
        self.rules.prune(now_s)
        detections = self.detector.detect(frame, self.frame_index)
        boxes = [item.bbox for item in detections]
        inside = {
            item.track_id
            for item in detections
            for zone in self.zones
            if zone.rule_type in EVENT_TYPE_BY_RULE
            and zone_active(zone, self.engine_on)
            and point_in_polygon(item.foot_point, zone.polygon)
        }
        live_frame: np.ndarray | None = None

        def annotated() -> np.ndarray:
            # Blur first: the overlay must never hide or replace the privacy step.
            blurred = self.blurrer.blur(frame, boxes)
            return draw_overlay(blurred, self.zones, detections, inside, self.engine_on)

        if self.live_writer is not None and self.live_writer.due():
            live_frame = annotated()
            self.live_writer.write(live_frame)

        emitted: list[EdgeEvent] = []

        for detection in detections:
            foot = detection.foot_point
            for zone in self.zones:
                if zone.rule_type not in EVENT_TYPE_BY_RULE:
                    continue
                in_zone = point_in_polygon(foot, zone.polygon)
                decision = self.rules.observe(
                    track_id=detection.track_id,
                    zone=zone,
                    in_zone=in_zone,
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
                self.sink.emit(event)
                emitted.append(event)

        self.frame_index += 1
        return emitted
