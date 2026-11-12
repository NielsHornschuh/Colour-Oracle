"""Feedback-vangnet: een zachte willekeurige gok."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"random"}

import random

from colour_oracle.constants import N


class RandomStrategy:
    """Feedback-vangnet: een zachte, gewogen willekeurige gok om te blijven verkennen."""

    label = "Baseline Randomizer"

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def predict(self, order):
        # Eén willekeurige kleur krijgt 0.7 extra kans bovenop een kleine basiskans
        pick = self.rng.randrange(N)
        dist = [0.3 / N] * N
        dist[pick] += 0.7
        return dist

    def update(self, colour, pos=None, ai_guess=None, order=None):
        pass  # deze strategie leert niets
