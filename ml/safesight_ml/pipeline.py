"""Frame pipeline: detections -> zone rules -> blurred snapshot -> event."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import numpy as np

from .detector import Detector
from .events import Confidence, EdgeEvent, EventContext, TemporalConfidence
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
    ) -> None:
        self.camera_id = camera_id
        self.zones = [zone for zone in zones if zone.camera_id == camera_id]
        self.detector = detector
        self.blurrer = blurrer
        self.sink = sink
        self.engine_on = engine_on
        self.start_epoch = start_epoch if start_epoch is not None else time.time()
        self.rules = rules or RuleEngine()
        self.frame_index = 0

    def process(self, frame: np.ndarray, now_s: float) -> list[EdgeEvent]:
        detections = self.detector.detect(frame, self.frame_index)
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

                event_epoch = self.start_epoch + now_s
                detected_at = datetime.fromtimestamp(event_epoch, tz=UTC)
                event_id = f"evt_{self.camera_id}_{int(event_epoch * 1000)}_{detection.track_id}"

                blurred = self.blurrer.blur(frame)
                snapshot_url = self.sink.store_snapshot(event_id, blurred)

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
