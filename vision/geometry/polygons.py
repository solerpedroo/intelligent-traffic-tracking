"""Simple normalized polygons; winding independent, boundary inclusive."""

from vision.geometry import cross, subtract

EPS = 1e-10


def on_segment(point, a, b):
    return abs(cross(subtract(b, a), subtract(point, a))) <= EPS and (
        min(a[0], b[0]) - EPS <= point[0] <= max(a[0], b[0]) + EPS
        and min(a[1], b[1]) - EPS <= point[1] <= max(a[1], b[1]) + EPS
    )


def intersects(a, b, c, d):
    values = (
        cross(subtract(b, a), subtract(c, a)),
        cross(subtract(b, a), subtract(d, a)),
        cross(subtract(d, c), subtract(a, c)),
        cross(subtract(d, c), subtract(b, c)),
    )
    if any(on_segment(p, x, y) for p, x, y in ((a, c, d), (b, c, d), (c, a, b), (d, a, b))):
        return True
    return values[0] * values[1] < 0 and values[2] * values[3] < 0


def validate_polygon(vertices):
    if len(set(vertices)) != len(vertices):
        raise ValueError("Polygon vertices must be unique; do not repeat the closing vertex")
    n = len(vertices)
    area = sum(cross(vertices[i], vertices[(i + 1) % n]) for i in range(n)) / 2
    if abs(area) <= 1e-10:
        raise ValueError("Polygon must have nonzero area")
    for i in range(n):
        a, b, c = vertices[i], vertices[(i + 1) % n], vertices[(i + 2) % n]
        incoming, outgoing = subtract(b, a), subtract(c, b)
        if abs(cross(incoming, outgoing)) <= EPS and (
            incoming[0] * outgoing[0] + incoming[1] * outgoing[1] < 0
        ):
            raise ValueError("Polygon edges must not backtrack")
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if intersects(a, b, vertices[j], vertices[(j + 1) % n]):
                raise ValueError("Polygon must be simple, without touching or crossing edges")


def contains(vertices, point):
    inside = False
    for i, a in enumerate(vertices):
        b = vertices[(i + 1) % len(vertices)]
        if on_segment(point, a, b):
            return True
        if (a[1] > point[1]) != (b[1] > point[1]):
            intersection_x = a[0] + (point[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if point[0] < intersection_x:
                inside = not inside
    return inside
