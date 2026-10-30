from __future__ import annotations

import numpy as np
import pytest

from safetarmac_ml.privacy import FaceBlurrer, NoopBlurrer, PrivacyError


def test_face_blurrer_fails_closed_when_model_is_missing(tmp_path):
    with pytest.raises(PrivacyError):
        FaceBlurrer(tmp_path / "missing.onnx")


def test_noop_blurrer_is_only_a_passthrough():
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    assert NoopBlurrer().blur(frame) is frame
