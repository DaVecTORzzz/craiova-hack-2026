"""How many cores one edge process is allowed to use.

Every edge starts its own torch and OpenCV worker pools, each sized from the machine:
three cameras on a 16-core laptop queue up to 48 compute threads on 16 cores, and every
frame ends up slower than it would be alone. The budget is split per camera, keeping one
core for the API, the JPEG writes and the OS.

    uv run python -m safesight_ml.run --threads 5 ...
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2

TOPOLOGY = Path("/sys/devices/system/cpu")


def physical_cores() -> int:
    """Cores, not hardware threads: an inference split over 16 threads on 8 SMT cores is
    slower than the same work on 8 (measured on this laptop: 16.8 fps at 15 threads,
    20.1 at 8, 21.1 at 6)."""
    siblings = set()
    try:
        for path in TOPOLOGY.glob("cpu[0-9]*/topology/thread_siblings_list"):
            siblings.add(path.read_text().strip())
    except OSError:
        siblings = set()
    return len(siblings) or (os.cpu_count() or 1)


def per_camera(cameras: int, total: int | None = None) -> int:
    """Threads for one edge when ``cameras`` of them run at once, leaving one core for the
    API, the JPEG writes and the OS."""
    cores = total or physical_cores()
    return max(1, (cores - 1) // max(1, cameras))


def limit(threads: int) -> None:
    """Apply the budget to this process. ``0`` leaves everything at the default."""
    if threads <= 0:
        return
    cv2.setNumThreads(threads)
    try:
        import torch  # only present with the optional yolo extra
    except ImportError:
        return
    torch.set_num_threads(threads)
    # The tracker and the model runs share one pool; extra inter-op workers only add
    # contention when three edges already fight for the same cores.
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # Already started; nothing to set.
        pass
