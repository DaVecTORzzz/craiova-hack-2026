from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from safesight_ml import privacy_audit


def _write_image(path: Path, value: int) -> None:
    image = np.full((32, 32, 3), value, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def test_iter_images_filters_suffixes(tmp_path):
    _write_image(tmp_path / "a.jpg", 10)
    _write_image(tmp_path / "b.png", 20)
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    paths = privacy_audit.iter_images(tmp_path)

    assert {path.name for path in paths} == {"a.jpg", "b.png"}


def test_scan_images_flags_only_images_with_faces(tmp_path):
    images = [
        (tmp_path / "clean.jpg", np.zeros((10, 10, 3), dtype=np.uint8)),
        (tmp_path / "face.jpg", np.ones((10, 10, 3), dtype=np.uint8)),
    ]

    findings = privacy_audit.scan_images(images, lambda image: [(1, 2, 3, 4)] if image.mean() else [])

    assert [finding.path for finding in findings] == [str(tmp_path / "face.jpg")]
    assert findings[0].faces == 1


def test_main_reports_clean_and_flagged_directories(tmp_path, monkeypatch, capsys):
    class FakeBlurrer:
        def __init__(self, *_args, **_kwargs):
            pass

        def detect_faces(self, image):
            return [(1, 1, 2, 2)] if image.mean() > 100 else []

    monkeypatch.setattr(privacy_audit, "FaceBlurrer", FakeBlurrer)

    clean = tmp_path / "clean"
    clean.mkdir()
    _write_image(clean / "clean.jpg", 10)
    assert privacy_audit.main(["--dir", str(clean)]) == 0
    assert "OK: 1 image(s), 0 faces detected" in capsys.readouterr().out

    flagged = tmp_path / "flagged"
    flagged.mkdir()
    _write_image(flagged / "face.jpg", 240)
    assert privacy_audit.main(["--dir", str(flagged), "--json"]) == 1
    assert '"faces": 1' in capsys.readouterr().out


def test_main_returns_error_for_missing_or_empty_directories(tmp_path, capsys):
    assert privacy_audit.main(["--dir", str(tmp_path / "missing")]) == 2
    assert "not found" in capsys.readouterr().out

    empty = tmp_path / "empty"
    empty.mkdir()
    assert privacy_audit.main(["--dir", str(empty)]) == 2
    assert "no images found" in capsys.readouterr().out

def test_main_returns_error_for_unreadable_image(tmp_path, monkeypatch, capsys):
    class FakeBlurrer:
        def __init__(self, *_args, **_kwargs):
            pass

        def detect_faces(self, _image):
            return []

    monkeypatch.setattr(privacy_audit, "FaceBlurrer", FakeBlurrer)
    (tmp_path / "broken.jpg").write_bytes(b"not a jpeg")

    assert privacy_audit.main(["--dir", str(tmp_path)]) == 2
    assert "unreadable image" in capsys.readouterr().out
