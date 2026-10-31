from __future__ import annotations

import numpy as np
import pytest

from safesight_ml.privacy import FaceBlurrer, NoopBlurrer, PrivacyError


def test_face_blurrer_fails_closed_when_model_is_missing(tmp_path):
    with pytest.raises(PrivacyError):
        FaceBlurrer(tmp_path / "missing.onnx")


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
