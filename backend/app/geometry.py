"""Polygon checks for zones. Points are (x, y) normalized 0-1.

The zone editor runs the same check (frontend/src/utils/polygon.js) and blocks Save, so
a self-crossing zone only reaches this from the API or the editor's JSON field.
"""

from __future__ import annotations

from collections.abc import Sequence

Point = tuple[float, float]

EPS = 1e-9


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    return (
        min(a[0], b[0]) - EPS <= p[0] <= max(a[0], b[0]) + EPS
        and min(a[1], b[1]) - EPS <= p[1] <= max(a[1], b[1]) + EPS
    )


def segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """Do segments p1-p2 and p3-p4 share any point (crossing, touching or overlapping)?"""
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    if ((d1 > EPS and d2 < -EPS) or (d1 < -EPS and d2 > EPS)) and (
        (d3 > EPS and d4 < -EPS) or (d3 < -EPS and d4 > EPS)
    ):
        return True
    return (
        (abs(d1) <= EPS and _on_segment(p3, p4, p1))
        or (abs(d2) <= EPS and _on_segment(p3, p4, p2))
        or (abs(d3) <= EPS and _on_segment(p1, p2, p3))
        or (abs(d4) <= EPS and _on_segment(p1, p2, p4))
    )


def crossing_edges(polygon: Sequence[Point]) -> set[int]:
    """Indices of the edges of the closed polygon that meet a non-adjacent edge.

    Edge i joins point i to point i + 1; the last edge joins the last point to the first.
    """
    n = len(polygon)
    crossing: set[int] = set()
    if n < 4:
        return crossing
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if segments_intersect(polygon[i], polygon[(i + 1) % n], polygon[j], polygon[(j + 1) % n]):
                crossing.update((i, j))
    return crossing
