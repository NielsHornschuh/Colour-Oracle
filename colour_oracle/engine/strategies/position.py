"""Statistisch: kans op dezelfde schermpositie."""

from colour_oracle.constants import N, UNIFORM
from colour_oracle.engine.helpers import to_colour_dist


class PositionStrategy:
    """Statistisch: hoe groot de kans is dat je weer op dezelfde schermpositie klikt.

    Houdt de herhaalkans bij na een reeks van 1, 2 of 3+ klikken op dezelfde
    plek, plus een afnemende voorkeur voor de andere posities. Het resultaat
    wordt via de huidige tegelvolgorde omgezet naar kleuren.
    """

    label = "Position Habit Tracker"

    def __init__(self, max_bucket=3, decay=0.9, rng=None):
        self.max_bucket = max_bucket
        self.decay = decay
        self.stats = {k: [1.0, 3.0] for k in range(1, max_bucket + 1)}
        self.prefs = [0.0] * N
        self.last_pos = None
        self.run = 0

    def predict(self, order):
        if self.last_pos is None:
            return list(UNIFORM)
        repeats, switches = self.stats[min(self.run, self.max_bucket)]
        r = repeats / (repeats + switches)
        others = [p for p in range(N) if p != self.last_pos]
        weights = [self.prefs[p] + 1.0 for p in others]
        total = sum(weights)
        pos_dist = [0.0] * N
        pos_dist[self.last_pos] = r
        for p, w in zip(others, weights):
            pos_dist[p] = (1.0 - r) * w / total
        return to_colour_dist(pos_dist, order)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        if self.last_pos is None:
            self.run = 1
        else:
            bucket = min(self.run, self.max_bucket)
            if pos == self.last_pos:
                self.stats[bucket][0] += 1
                self.run += 1
            else:
                self.stats[bucket][1] += 1
                self.run = 1
        self.prefs = [p * self.decay for p in self.prefs]
        self.prefs[pos] += 1.0
        self.last_pos = pos
