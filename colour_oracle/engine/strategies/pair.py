"""Structureel: hoe vaak elke kleur op elke positie gekozen wordt."""

from colour_oracle.constants import N
from colour_oracle.engine.helpers import normalize, to_colour_dist


class PairStrategy:
    """Structureel: hoe vaak elke kleur gekozen wordt als die op een bepaalde plek staat.

    Voor elke tegel op het scherm weet het model hoe vaak precies dat paar van
    positie en kleur getoond is en hoe vaak het gekozen is.
    """

    label = "Colour-at-Position Tracker"

    def __init__(self, rng=None):
        self.chosen = [[0] * N for _ in range(N)]   # chosen[positie][kleur]
        self.shown = [[0] * N for _ in range(N)]    # shown[positie][kleur]

    def predict(self, order):
        # Keuzekans per tegel: aantal keer gekozen gedeeld door aantal keer getoond
        scores = [
            (self.chosen[p][order[p]] + 1.0) / (self.shown[p][order[p]] + 4.0)
            for p in range(N)
        ]
        return to_colour_dist(normalize(scores), order)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        for p in range(N):
            self.shown[p][order[p]] += 1
        self.chosen[pos][order[pos]] += 1
