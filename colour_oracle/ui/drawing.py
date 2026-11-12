"""Tekenhulp voor de interface."""


def rounded_points(x1, y1, x2, y2, r):
    """Punten voor een rechthoek met afgeronde hoeken, bedoeld voor smooth=True."""
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r,
        x1, y1 + r, x1, y1,
    ]
