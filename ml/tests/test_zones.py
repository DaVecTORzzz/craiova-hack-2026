from __future__ import annotations

import pytest

from safesight_ml.zones import RuleEngine, Zone, ZoneMembership, point_in_polygon, signed_distance

POLYGON = [(0.46, 0.16), (0.76, 0.16), (0.76, 0.68), (0.46, 0.68)]


def make_zone(**overrides):
    payload = {
        "id": "engine-left",
        "camera_id": "stand12",
        "name": "Motor stâng",
        "rule_type": "RESTRICTED",
        "active_when": "engine_on",
        "required_ppe": [],
        "severity": "CRITICAL",
        "debounce_s": 1.0,
        "escalate_after_s": 30,
        "notify_channel": "slack",
        "polygon": POLYGON,
        "reference_frame": None,
    }
    payload.update(overrides)
    return Zone(**payload)


def test_point_in_polygon():
    assert point_in_polygon((0.60, 0.60), POLYGON)
    assert not point_in_polygon((0.20, 0.60), POLYGON)
    assert not point_in_polygon((0.60, 0.90), POLYGON)


def test_zone_rejects_out_of_range_polygon():
    with pytest.raises(ValueError):
        make_zone(polygon=[(-0.1, 0.2), (0.8, 0.2), (0.8, 0.9)])


def test_rule_engine_rejects_min_window_larger_than_window():
    with pytest.raises(ValueError):
        RuleEngine(window_frames=5, min_window=6)


def test_zone_escalation_must_be_positive_or_null():
    with pytest.raises(ValueError):
        make_zone(escalate_after_s=0)


def test_engine_off_emits_nothing():
    engine = RuleEngine()
    zone = make_zone()
    for step in range(20):
        assert engine.observe(track_id=1, zone=zone, in_zone=True, now=step / 10, engine_on=False) is None


def test_debounce_emits_once():
    engine = RuleEngine()
    zone = make_zone(debounce_s=1.0)
    decisions = [
        engine.observe(track_id=1, zone=zone, in_zone=True, now=step / 10, engine_on=True)
        for step in range(11)
    ]
    assert all(decision is None for decision in decisions[:10])
    decision = decisions[10]
    assert decision is not None
    assert decision.seen == 11
    assert decision.window == 11
    assert decision.duration_s == pytest.approx(1.0)

    # The same presence must not produce a second event.
    assert engine.observe(track_id=1, zone=zone, in_zone=True, now=1.1, engine_on=True) is None


def test_reentry_after_cooldown_emits_again():
    engine = RuleEngine(cooldown_s=10.0)
    zone = make_zone(debounce_s=0.5)

    first = None
    for step in range(6):
        decision = engine.observe(track_id=1, zone=zone, in_zone=True, now=step / 10, engine_on=True)
        first = first or decision
    assert first is not None

    # Leave the zone; after the cooldown the state is reset.
    engine.observe(track_id=1, zone=zone, in_zone=False, now=1.0, engine_on=True)
    engine.observe(track_id=1, zone=zone, in_zone=False, now=11.1, engine_on=True)

    second = None
    for step in range(6):
        decision = engine.observe(track_id=1, zone=zone, in_zone=True, now=11.2 + step / 10, engine_on=True)
        second = second or decision
    assert second is not None


def test_temporal_confirmation_rejects_mostly_missing_track():
    engine = RuleEngine(min_window=5, seen_ratio=0.8, cooldown_s=100.0)
    zone = make_zone(debounce_s=0.1)

    # Only 2 of 8 observed frames confirm; no event.
    for step in range(8):
        in_zone = step in (0, 1)
        assert engine.observe(track_id=1, zone=zone, in_zone=in_zone, now=step / 10, engine_on=True) is None


def _membership_zone():
    return Zone(
        id="engine-left",
        camera_id="stand12",
        rule_type="RESTRICTED",
        severity="CRITICAL",
        polygon=[(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)],
    )


def _box(foot_y: float, height: float = 0.4) -> tuple[float, float, float, float]:
    """Person box centred at x=0.5 with the feet at ``foot_y``."""
    return (0.45, foot_y - height, 0.55, foot_y)


def test_signed_distance_is_positive_inside_and_uses_the_aspect():
    square = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
    assert signed_distance((0.5, 0.75), square) == pytest.approx(0.05)
    assert signed_distance((0.5, 0.85), square) == pytest.approx(-0.05)
    # On a 16:9 frame, 0.05 of the width is 0.089 frame heights.
    assert signed_distance((0.85, 0.5), square, aspect=16 / 9) == pytest.approx(-0.05 * 16 / 9)


def test_membership_needs_the_margin_to_enter_and_to_leave():
    zone = _membership_zone()
    member = ZoneMembership(margin=0.10)  # band = 0.10 * 0.4 = 0.04 frame heights

    def step(foot_y: float) -> bool:
        return member.update(track_id=1, bbox=_box(foot_y), zone=zone, now=0.0)

    assert step(0.79) is False  # 0.01 inside: on the edge, not in yet
    assert step(0.75) is True  # 0.05 inside: entered
    assert step(0.81) is True  # 0.01 outside: still in (inside the band)
    assert step(0.85) is False  # 0.05 outside: left
    assert member.transitions == 2


def test_zero_margin_is_the_bare_point_test():
    zone = _membership_zone()
    member = ZoneMembership(margin=0.0)
    assert member.update(track_id=1, bbox=_box(0.79), zone=zone, now=0.0) is True
    assert member.update(track_id=1, bbox=_box(0.81), zone=zone, now=0.0) is False


def test_box_cut_by_the_frame_bottom_keeps_the_last_state():
    zone = Zone(
        id="engine-left",
        camera_id="stand12",
        rule_type="RESTRICTED",
        severity="CRITICAL",
        polygon=[(0.2, 0.2), (0.8, 0.2), (0.8, 1.0), (0.2, 1.0)],
    )
    member = ZoneMembership()
    # Feet hidden below the frame: a new track does not enter on a guess...
    assert member.update(track_id=1, bbox=_box(0.995), zone=zone, now=0.0) is False
    # ...and a track already inside stays inside.
    assert member.update(track_id=2, bbox=_box(0.9), zone=zone, now=0.0) is True
    assert member.update(track_id=2, bbox=_box(0.995), zone=zone, now=0.1) is True


def test_membership_state_is_pruned():
    zone = _membership_zone()
    member = ZoneMembership(ttl_s=5.0)
    assert member.update(track_id=1, bbox=_box(0.75), zone=zone, now=0.0) is True
    member.prune(10.0)
    # Forgotten: the same track on the edge band starts again from "outside".
    assert member.update(track_id=1, bbox=_box(0.79), zone=zone, now=10.0) is False
