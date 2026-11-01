// Polygon geometry for the zone editor. Points are { x, y } normalized 0-1.
// The backend runs the same crossing check (backend/app/geometry.py) and rejects a
// self-crossing polygon with 422, so the editor blocks Save before that happens.

const EPS = 1e-9;

function orient(a, b, c) {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

function onSegment(a, b, p) {
  return (
    Math.min(a.x, b.x) - EPS <= p.x && p.x <= Math.max(a.x, b.x) + EPS &&
    Math.min(a.y, b.y) - EPS <= p.y && p.y <= Math.max(a.y, b.y) + EPS
  );
}

/** Do segments p1-p2 and p3-p4 share any point (crossing, touching or overlapping)? */
export function segmentsIntersect(p1, p2, p3, p4) {
  const d1 = orient(p3, p4, p1);
  const d2 = orient(p3, p4, p2);
  const d3 = orient(p1, p2, p3);
  const d4 = orient(p1, p2, p4);
  if (((d1 > EPS && d2 < -EPS) || (d1 < -EPS && d2 > EPS)) && ((d3 > EPS && d4 < -EPS) || (d3 < -EPS && d4 > EPS))) {
    return true;
  }
  return (
    (Math.abs(d1) <= EPS && onSegment(p3, p4, p1)) ||
    (Math.abs(d2) <= EPS && onSegment(p3, p4, p2)) ||
    (Math.abs(d3) <= EPS && onSegment(p1, p2, p3)) ||
    (Math.abs(d4) <= EPS && onSegment(p1, p2, p4))
  );
}

/**
 * Indices of the edges that cross another, non-adjacent edge. Edge i joins point i to
 * point i + 1; with `closed`, the last edge joins the last point back to the first.
 */
export function crossingEdges(points, closed = true) {
  const n = points.length;
  const count = closed ? n : n - 1;
  const crossing = new Set();
  if (n < 4) return crossing;
  for (let i = 0; i < count; i += 1) {
    for (let j = i + 1; j < count; j += 1) {
      const adjacent = j === i + 1 || (closed && i === 0 && j === n - 1);
      if (adjacent) continue;
      if (segmentsIntersect(points[i], points[(i + 1) % n], points[j], points[(j + 1) % n])) {
        crossing.add(i);
        crossing.add(j);
      }
    }
  }
  return crossing;
}

/**
 * The same points ordered by angle around their centroid. Untangles any convex shape and
 * most simple ones; a strongly concave outline can still come out wrong, so it is a button.
 */
export function orderAroundCentroid(points) {
  const cx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const cy = points.reduce((sum, p) => sum + p.y, 0) / points.length;
  return [...points].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));
}
