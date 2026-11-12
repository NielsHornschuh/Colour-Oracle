"""Structureel: Markov chain op verschillen tussen schermposities."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"collections"}

from collections import defaultdict, deque

from colour_oracle.constants import N, UNIFORM
from colour_oracle.engine.helpers import normalize, to_colour_dist


class StepStrategy:
    """Structureel: Markov chain op verschillen tussen schermposities (een motorische gewoonte)."""

    label = "Step Habit & Position Delta"

    def __init__(self, max_order=2, rng=None):
        self.max_order = max_order
        self.deltas = deque(maxlen=max_order)   # laatste positiesprongen
        # tables[k][context] = telling van de sprong die volgde op die context
        self.tables = {k: defaultdict(lambda: [0] * N) for k in range(0, max_order + 1)}
        self.last_pos = None

    def _context(self, k):
        # k = 0 is de algemene verdeling van sprongen, zonder context
        return () if k == 0 else tuple(list(self.deltas)[-k:])

    def predict(self, order):
        if self.last_pos is None:
            return list(UNIFORM)
        # Langste context eerst, daarna terugval naar kortere contexten
        for k in range(min(self.max_order, len(self.deltas)), -1, -1):
            counts = self.tables[k].get(self._context(k))
            if counts and sum(counts) >= 2:
                delta_dist = normalize([c + 0.5 for c in counts])
                pos_dist = [0.0] * N
                # Een sprong van delta vanaf de laatste positie geeft de nieuwe positie
                for delta, p in enumerate(delta_dist):
                    pos_dist[(self.last_pos + delta) % N] = p
                return to_colour_dist(pos_dist, order)
        return list(UNIFORM)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        if self.last_pos is not None:
            delta = (pos - self.last_pos) % N   # sprong rond het scherm, modulo N
            for k in range(0, self.max_order + 1):
                if len(self.deltas) >= k:
                    self.tables[k][self._context(k)][delta] += 1
            self.deltas.append(delta)
        self.last_pos = pos
