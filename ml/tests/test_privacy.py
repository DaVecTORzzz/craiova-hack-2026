from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from safesight_ml.privacy import FaceBlurrer, NoopBlurrer, PrivacyError


def test_face_blurrer_fails_closed_when_model_is_missing(tmp_path):
    with pytest.raises(PrivacyError):
        FaceBlurrer(tmp_path / "missing.onnx")


MODEL = Path(__file__).resolve().parents[1] / "models" / "face_detection_yunet_2023mar.onnx"
needs_model = pytest.mark.skipif(not MODEL.is_file(), reason="face model not downloaded")


@needs_model
def test_face_blurrer_returns_nothing_on_an_empty_frame():
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    assert FaceBlurrer(MODEL).detect_faces(frame) == []


@needs_model
@pytest.mark.parametrize("shape", [(97, 133, 3), (1080, 1920, 3), (721, 1279, 3)])
def test_face_blurrer_handles_frames_whose_sides_are_not_multiples_of_32(shape):
    """The graph pads to a multiple of 32 on both sides; a 133 px wide frame used to line up
    with the cells of a wider grid and return boxes outside the picture."""
    frame = np.zeros(shape, dtype=np.uint8)
    assert FaceBlurrer(MODEL).detect_faces(frame) == []


@needs_model
def test_face_blurrer_blurs_a_face_it_finds():
    """End to end: a real face from the fixture clip is found and the region is flattened."""
    import cv2

    clip = Path(__file__).resolve().parents[2] / "data" / "videos"
    video = clip / "2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4"
    if not video.is_file():
        pytest.skip("demo clip not available")
    capture = cv2.VideoCapture(str(video))
    frame = None
    for _ in range(40):
        ok, current = capture.read()
        if ok:
            frame = current
    capture.release()

    blurrer = FaceBlurrer(MODEL)
    faces = blurrer.detect_faces(frame)
    assert faces, "YuNet found no face in a frame that is known to contain one"

    blurred = blurrer.blur(frame)
    x, y, w, h = faces[0]
    detail = lambda image: cv2.Laplacian(  # noqa: E731
        cv2.cvtColor(image[y : y + h, x : x + w], cv2.COLOR_BGR2GRAY), cv2.CV_64F
    ).var()
    assert detail(blurred) < detail(frame)


def test_noop_blurrer_is_only_a_passthrough():
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    assert NoopBlurrer().blur(frame) is frame


def test_strong_blur_removes_at_least_as_much_detail_as_gaussian_sigma_25():
    import cv2
    import numpy as np

    from safesight_ml.privacy import _strong_blur

    rng = np.random.default_rng(3)
    roi = rng.integers(0, 255, (240, 200, 3), dtype=np.uint8)  # worst case: all fine detail

    def detail(image):
        return cv2.Laplacian(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()

    assert _strong_blur(roi).shape == roi.shape
    assert detail(_strong_blur(roi)) <= detail(cv2.GaussianBlur(roi, (0, 0), sigmaX=25)) * 1.1
