from __future__ import annotations

import cv2
import pytest

from safesight_ml import threads


@pytest.mark.parametrize(
    ("cameras", "cores", "expected"),
    [
        (1, 8, 7),  # one camera keeps the machine, minus a core for the API
        (3, 8, 2),  # three edges of two threads fit in eight cores
        (4, 8, 1),
        (40, 8, 1),  # never zero, however many cameras are declared
        (3, 2, 1),
    ],
)
def test_the_cores_are_split_between_the_cameras(cameras, cores, expected):
    assert threads.per_camera(cameras, total=cores) == expected


def test_per_camera_uses_the_physical_cores_when_no_total_is_given():
    assert threads.physical_cores() <= (threads.os.cpu_count() or 1)
    assert threads.per_camera(1) == max(1, threads.physical_cores() - 1)


def test_limit_sets_the_thread_pool_and_zero_leaves_it_alone():
    before = cv2.getNumThreads()
    try:
        threads.limit(3)
        assert cv2.getNumThreads() == 3
        threads.limit(0)
        assert cv2.getNumThreads() == 3
    finally:
        cv2.setNumThreads(before)


def test_the_edge_parks_idle_openmp_workers():
    """Default libgomp behaviour spins a full core per pool thread; the edge turns it off
    before any numeric import, which is the only point where it can still take effect."""
    import os

    import safesight_ml.run  # noqa: F401  - the import is the thing under test

    assert os.environ.get("OMP_WAIT_POLICY") == "PASSIVE"
