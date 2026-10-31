"""Keep zone polygons on the ground when the camera pans, tilts or zooms.

Zones are drawn once on a reference frame. Every few frames the current frame is
matched to the reference (ORB + RANSAC homography) and the polygons are mapped into
the current view. If the match fails, the zones are "unknown" for that frame and no
zone rule fires: a wrong polygon is worse than none.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .zones import Zone

WORK_WIDTH = 640
MIN_INLIERS = 40
# A fixed apron camera never scales the scene by more than this between frames.
MAX_SCALE_CHANGE = 4.0


def load_reference(path: str | Path) -> np.ndarray:
    """First frame of a video, or an image file."""
    path = Path(path)
    image = cv2.imread(str(path)) if path.suffix.lower() in {".jpg", ".jpeg", ".png"} else None
    if image is None:
        capture = cv2.VideoCapture(str(path))
        ok, image = capture.read()
        capture.release()
        if not ok:
            raise OSError(f"could not read a reference frame from {path}")
    return image


class ZoneAligner:
    def __init__(self, reference: np.ndarray, *, every_n: int = 5, min_inliers: int = MIN_INLIERS) -> None:
        if every_n < 1:
            raise ValueError("every_n must be >= 1")
        self.every_n = every_n
        self.min_inliers = min_inliers
        self._orb = cv2.ORB_create(1500)
        self._matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self._ref = self._features(reference)
        self._ref_size = reference.shape[1], reference.shape[0]
        # Normalized current-frame coords -> normalized reference coords, and its inverse.
        self._to_ref: np.ndarray | None = np.eye(3)
        self._last: tuple[np.ndarray, np.ndarray | None] | None = None
        self._calls = 0
        self.lost_updates = 0

    def _features(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
        height, width = frame.shape[:2]
        scale = WORK_WIDTH / width
        small = cv2.resize(frame, (WORK_WIDTH, max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self._orb.detectAndCompute(gray, None)
        # Normalized 0..1 coordinates, so reference and stream may differ in resolution.
        points = np.float32([kp.pt for kp in keypoints]).reshape(-1, 2) / np.float32([small.shape[1], small.shape[0]])
        return points, descriptors

    def _match(self, ref, cur) -> np.ndarray | None:
        (ref_pts, ref_desc), (cur_pts, cur_desc) = ref, cur
        if ref_desc is None or cur_desc is None or len(ref_desc) < 2 or len(cur_desc) < 2:
            return None
        good = [
            pair[0]
            for pair in self._matcher.knnMatch(cur_desc, ref_desc, k=2)
            if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance
        ]
        if len(good) < self.min_inliers:
            return None
        src = cur_pts[[m.queryIdx for m in good]]
        dst = ref_pts[[m.trainIdx for m in good]]
        # 4 px at the 640 px working width.
        homography, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0 / WORK_WIDTH)
        if homography is None or mask is None or int(mask.sum()) < self.min_inliers:
            return None
        return homography if _plausible(homography) else None

    def update(self, frame: np.ndarray) -> bool:
        """Re-estimate the camera motion every ``every_n`` calls. Returns False if lost."""
        self._calls += 1
        if (self._calls - 1) % self.every_n:
            return self._to_ref is not None
        current = self._features(frame)
        to_ref = self._match(self._ref, current)
        if to_ref is None and self._last is not None and self._to_ref is not None:
            # Large pan/zoom: chain through the last frame that matched.
            step = self._match(self._last, current)
            to_ref = self._to_ref @ step if step is not None else None
            if to_ref is not None and not _plausible(to_ref):
                to_ref = None
        if to_ref is None:
            self._to_ref = None
            self.lost_updates += 1
            return False
        self._to_ref = to_ref
        self._last = current
        return True

    def zones(self, zones: list[Zone]) -> list[Zone] | None:
        """Zones in the current view, or None when the view is not aligned."""
        if self._to_ref is None:
            return None
        to_current = np.linalg.inv(self._to_ref)
        aligned = []
        for zone in zones:
            points = np.float32(zone.polygon).reshape(-1, 1, 2)
            mapped = cv2.perspectiveTransform(points, to_current).reshape(-1, 2)
            # Not re-validated: a mapped corner may sit just outside the frame.
            aligned.append(zone.model_copy(update={"polygon": [(float(x), float(y)) for x, y in mapped]}))
        return aligned


def _plausible(homography: np.ndarray) -> bool:
    if not np.all(np.isfinite(homography)) or abs(homography[2, 2]) < 1e-9:
        return False
    h = homography / homography[2, 2]
    det = float(np.linalg.det(h[:2, :2]))
    if not 1.0 / MAX_SCALE_CHANGE**2 <= det <= MAX_SCALE_CHANGE**2:
        return False
    # Strong perspective terms mean a degenerate fit, not a camera move.
    return float(np.abs(h[2, :2]).max()) < 2.0
