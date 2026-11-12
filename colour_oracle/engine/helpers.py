"""Kleine hulpfuncties voor kansen en tegelvolgordes."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"random"}

import random

from colour_oracle.constants import N, UNIFORM


def normalize(values):
    """Schaal waarden zodat ze optellen tot 1. Bij een som van 0 volgt UNIFORM."""
    total = sum(values)
    if total <= 0:
        return list(UNIFORM)
    return [v / total for v in values]


def argmax_random(dist, rng):
    """Kies de index met de hoogste kans. Bij een gelijke stand beslist het lot."""
    best = max(dist)
    ties = [i for i, p in enumerate(dist) if abs(p - best) < 1e-9]
    return rng.choice(ties)


def to_colour_dist(pos_dist, order):
    """Zet een verdeling over schermposities om in een verdeling over kleuren.

    Order[positie] is de kleur die op die positie staat in de huidige ronde.
    """
    dist = [0.0] * N
    for pos, p in enumerate(pos_dist):
        dist[order[pos]] = p
    return dist


def random_order(previous=None):
    """Geef een willekeurige tegelvolgorde die verschilt van de vorige."""
    order = list(range(N))
    while True:
        random.shuffle(order)
        if order != previous:
            return order
