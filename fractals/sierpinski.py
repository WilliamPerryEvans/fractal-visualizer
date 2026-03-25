import numpy as np

_S3 = np.sqrt(3.0)


def generate_sierpinski(n_points=80_000):
    """
    Generate Sierpinski triangle points via the chaos game.
    Returns a flat float32 array for GL_POINTS rendering.
    """
    # Same triangle as Koch (circumradius 1, centered at origin)
    vertices = np.array([
        [0.0,          1.0],
        [-_S3 / 2.0,  -0.5],
        [ _S3 / 2.0,  -0.5],
    ], dtype="f4")

    rng = np.random.default_rng(42)
    choices = rng.integers(0, 3, n_points + 200)

    point = np.zeros(2, dtype="f4")
    points = np.empty((n_points, 2), dtype="f4")

    for i in range(n_points + 200):
        point = (point + vertices[choices[i]]) * 0.5
        if i >= 200:
            points[i - 200] = point

    return points.flatten()
