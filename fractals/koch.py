import numpy as np

_S3 = np.sqrt(3.0)


def _subdivide(p1, p2, depth):
    """Yield Koch curve points from p1 up to (not including) p2."""
    if depth == 0:
        yield p1
        return
    d = p2 - p1
    q = p1 + d / 3.0
    s = p1 + 2.0 * d / 3.0
    # Rotate d/3 by -60° (clockwise) to get the outward-pointing peak.
    # cos(-60°) = 0.5, sin(-60°) = -√3/2
    # new = (dx*0.5 + dy*√3/2,  -dx*√3/2 + dy*0.5)
    dx, dy = d[0] / 3.0, d[1] / 3.0
    r = q + np.array([dx * 0.5 + dy * _S3 / 2.0,
                      -dx * _S3 / 2.0 + dy * 0.5])
    yield from _subdivide(p1, q, depth - 1)
    yield from _subdivide(q, r, depth - 1)
    yield from _subdivide(r, s, depth - 1)
    yield from _subdivide(s, p2, depth - 1)


def generate_koch(depth=5):
    """Return a flat float32 array of Koch snowflake vertices for GL_LINE_LOOP."""
    # Equilateral triangle with circumradius 1, centered at origin
    p1 = np.array([-_S3 / 2.0, -0.5])
    p2 = np.array([ _S3 / 2.0, -0.5])
    p3 = np.array([0.0,          1.0])

    pts = (list(_subdivide(p1, p2, depth)) +
           list(_subdivide(p2, p3, depth)) +
           list(_subdivide(p3, p1, depth)))

    return np.array(pts, dtype="f4").flatten()
