"""Same cases as the zone editor's check (frontend/src/utils/polygon.js)."""

from app.geometry import crossing_edges, segments_intersect

SQUARE = [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]
HOURGLASS = [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]


def test_simple_shapes_do_not_cross():
    assert crossing_edges(SQUARE) == set()
    assert crossing_edges([(0, 0), (1, 0), (0.5, 1)]) == set()
    assert crossing_edges([(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.5, 0.4), (0.1, 0.9)]) == set()


def test_hourglass_reports_the_crossing_edges():
    assert crossing_edges(HOURGLASS) == {1, 3}


def test_touching_a_non_adjacent_edge_counts():
    assert crossing_edges([(0, 0), (1, 0), (1, 1), (0.5, 0), (0, 1)])


def test_segments():
    assert segments_intersect((0, 0), (1, 1), (0, 1), (1, 0))
    assert segments_intersect((0, 0), (1, 0), (0.5, 0), (2, 0))
    assert not segments_intersect((0, 0), (1, 0), (0, 1), (1, 1))
