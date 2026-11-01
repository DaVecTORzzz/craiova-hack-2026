from __future__ import annotations

import numpy as np

from safesight_ml.ncnn_detector import LETTERBOX_FILL, decode, letterbox


def test_letterbox_pads_a_1080p_frame_and_keeps_the_aspect_ratio():
    frame = np.zeros((1080, 1920, 3), np.uint8)
    canvas, scale, left, top = letterbox(frame, 640)

    assert canvas.shape == (640, 640, 3)
    assert abs(scale - 640 / 1920) < 1e-6
    assert left == 0
    assert top == (640 - round(1080 * 640 / 1920)) // 2
    # The padding is the same grey ultralytics uses.
    assert tuple(canvas[0, 0]) == (LETTERBOX_FILL,) * 3


def _head(rows: list[list[float]]) -> np.ndarray:
    """(84, N) anchor-free head from a list of [cx, cy, w, h, class_0_score, ...]."""
    output = np.zeros((84, len(rows)), np.float32)
    for column, row in enumerate(rows):
        output[:4, column] = row[:4]
        for class_id, score in enumerate(row[4:]):
            output[4 + class_id, column] = score
    return output


def test_decode_maps_boxes_back_to_frame_pixels_and_keeps_people_only():
    # 1920x1080 in a 640 canvas: scale 1/3, 140 rows of padding top and bottom.
    output = _head(
        [
            [320, 320, 60, 90, 0.9],  # person in the middle of the canvas
            [320, 320, 60, 90, 0.0],  # same place, but the best class is not person
            [100, 100, 30, 30, 0.2],  # below the threshold
        ]
    )
    output[4 + 5, 1] = 0.9  # second anchor is a car

    boxes, scores = decode(output, scale=640 / 1920, left=0, top=140, frame_shape=(1080, 1920, 3))

    assert len(boxes) == 1
    assert scores[0] > 0.89
    # centre x: 320 / (1/3) = 960 ; centre y: (320 - 140) / (1/3) = 540
    assert abs((boxes[0][0] + boxes[0][2]) / 2 - 960) < 1.5
    assert abs((boxes[0][1] + boxes[0][3]) / 2 - 540) < 1.5
    assert abs((boxes[0][2] - boxes[0][0]) - 180) < 1.5  # 60 / (1/3)


def test_decode_returns_nothing_when_no_anchor_passes():
    output = _head([[320, 320, 60, 90, 0.1]])
    boxes, scores = decode(output, scale=1.0, left=0, top=0, frame_shape=(640, 640, 3))
    assert boxes.shape == (0, 4)
    assert scores.shape == (0,)


def test_decode_clips_boxes_to_the_frame():
    output = _head([[10, 10, 200, 200, 0.9]])
    boxes, _ = decode(output, scale=1.0, left=0, top=0, frame_shape=(640, 640, 3))
    assert boxes[0][0] >= 0 and boxes[0][1] >= 0
    assert boxes[0][2] <= 640 and boxes[0][3] <= 640
