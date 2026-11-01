from __future__ import annotations

import pytest

from safesight_ml.run import frames_to_skip


@pytest.mark.parametrize(
    ("lag", "fps", "expected"),
    [
        (0.0, 30, 0),  # la timp
        (-0.2, 30, 0),  # înainte de timp: doar dormim
        (0.033, 30, 0),  # sub un cadru: nu merită sărit
        (0.05, 30, 1),
        (0.10, 30, 3),
        (1.0, 30, 30),
        (0.5, 0, 0),  # fps invalid nu aruncă
    ],
)
def test_frames_to_skip_catches_up_without_going_negative(lag, fps, expected):
    assert frames_to_skip(lag, fps) == expected
