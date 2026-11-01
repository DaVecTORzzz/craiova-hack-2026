from __future__ import annotations

import numpy as np

from safesight_ml.suggest import cluster_points, equipment_polygon, hull_polygon


def test_clusters_separate_two_groups_of_people_and_ignore_a_walker():
    left = np.random.default_rng(1).normal(loc=[0.2, 0.8], scale=0.01, size=(30, 2))
    right = np.random.default_rng(2).normal(loc=[0.7, 0.6], scale=0.01, size=(30, 2))
    walker = np.array([[0.45, 0.1], [0.46, 0.11]])

    groups = cluster_points(np.vstack([left, right, walker]), radius=0.05, minimum=10)

    assert len(groups) == 2
    assert sorted(len(group) for group in groups) == [30, 30]


def test_the_hull_contains_the_points_and_stays_inside_the_frame():
    square = np.array([[0.3, 0.3], [0.6, 0.3], [0.6, 0.5], [0.3, 0.5]])
    polygon = hull_polygon(square, margin=0.02)

    assert len(polygon) == 4
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    assert min(xs) < 0.3 and max(xs) > 0.6  # crescut, nu doar lipit de puncte
    assert 0.0 <= min(xs) and max(xs) <= 1.0
    assert 0.0 <= min(ys) and max(ys) <= 1.0


def test_the_hull_is_clipped_at_the_frame_edge():
    hugging_the_corner = np.array([[0.0, 0.0], [0.2, 0.0], [0.0, 0.2]])
    polygon = hull_polygon(hugging_the_corner, margin=0.1)
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in polygon)


def test_equipment_box_is_extended_sideways_and_down_to_the_ground():
    # motor mic, sus în cadru: zona trebuie să coboare sub el, unde stă lumea
    polygon = equipment_polygon((0.20, 0.40, 0.30, 0.50), (1080, 1920), side_pad=0.25, ground_drop=1.2)

    left, top, right, bottom = polygon[0][0], polygon[0][1], polygon[1][0], polygon[2][1]
    assert left < 0.20 and right > 0.30  # lățit
    assert top == 0.40  # nu urcă peste echipament
    assert abs(bottom - (0.50 + 0.10 * 1.2)) < 1e-6  # coboară 1,2 înălțimi


def test_equipment_zone_never_leaves_the_frame():
    polygon = equipment_polygon((0.01, 0.80, 0.10, 0.95), (1080, 1920), side_pad=0.5, ground_drop=2.0)
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in polygon)
