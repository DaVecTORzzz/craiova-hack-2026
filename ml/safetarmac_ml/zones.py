"""Zone geometry and the rule engine for the first vertical slice."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Point = tuple[float, float]
RuleType = Literal["RESTRICTED", "PPE_REQUIRED", "FOD_WATCH", "NO_SMOKING", "CROWD_WATCH"]
ActiveWhen = Literal["always", "engine_on"]


class Zone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    name: str = ""
    rule_type: RuleType
    active_when: ActiveWhen = "always"
    required_ppe: list[str] = Field(default_factory=list)
    severity: Literal["CRITICAL", "WARNING"]
    debounce_s: float = Field(default=1.0, ge=0.0)
    escalate_after_s: int | None = Field(default=30, ge=0)
    notify_channel: str = "slack"
    polygon: list[Point] = Field(min_length=3)
    reference_frame: str | None = None

    @field_validator("polygon")
    @classmethod
    def _normalized_polygon(cls, value: list[Point]) -> list[Point]:
        for x, y in value:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("polygon points must be normalized to 0..1")
        return value


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    """Ray casting on normalized coordinates."""
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_cross:
                inside = not inside
    return inside


@dataclass
class _RuleState:
    first_seen: float
    last_seen: float
    seen: deque[bool] = field(default_factory=lambda: deque(maxlen=15))
    emitted: bool = False
    left_at: float | None = None


@dataclass(frozen=True)
class RuleDecision:
    seen: int
    window: int
    duration_s: float


class RuleEngine:
    """One event per presence, with debounce, temporal confidence and cooldown."""

    def __init__(
        self,
        *,
        window_frames: int = 15,
        min_window: int = 5,
        seen_ratio: float = 0.8,
        cooldown_s: float = 10.0,
    ) -> None:
        if window_frames < 1:
            raise ValueError("window_frames must be >= 1")
        if min_window < 1 or min_window > window_frames:
            raise ValueError("min_window must be between 1 and window_frames")
        if not 0.0 <= seen_ratio <= 1.0:
            raise ValueError("seen_ratio must be between 0 and 1")
        self.window_frames = window_frames
        self.min_window = min_window
        self.seen_ratio = seen_ratio
        self.cooldown_s = cooldown_s
        self._states: dict[tuple[int, str], _RuleState] = {}

    def observe(
        self,
        *,
        track_id: int,
        zone: Zone,
        in_zone: bool,
        now: float,
        engine_on: bool,
    ) -> RuleDecision | None:
        """Update the rule state for one track/zone pair at one frame."""
        key = (track_id, zone.id)
        active = zone.active_when == "always" or engine_on

        if not active:
            self._states.pop(key, None)
            return None

        state = self._states.get(key)

        if not in_zone:
            if state is None:
                return None
            state.last_seen = now
            state.seen.append(False)
            if state.left_at is None:
                state.left_at = now
            if now - state.left_at >= self.cooldown_s:
                del self._states[key]
            return None

        if state is None:
            state = _RuleState(
                first_seen=now,
                last_seen=now,
                seen=deque([True], maxlen=self.window_frames),
            )
            self._states[key] = state
        else:
            state.last_seen = now
            state.left_at = None
            state.seen.append(True)

        if state.emitted:
            return None

        window = len(state.seen)
        seen = sum(state.seen)
        duration = now - state.first_seen
        confirmed = window >= self.min_window and seen / window >= self.seen_ratio
        if duration < zone.debounce_s or not confirmed:
            return None

        state.emitted = True
        return RuleDecision(seen=seen, window=window, duration_s=duration)

    def reset(self) -> None:
        self._states.clear()
