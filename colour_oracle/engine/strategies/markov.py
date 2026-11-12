"""Structureel: N-gram overgangen op kleuren."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"collections"}

from collections import defaultdict, deque

from colour_oracle.constants import N, UNIFORM
from colour_oracle.engine.helpers import normalize


class MarkovStrategy:
    """Structureel: N-gram overgangen op kleuren, met terugval op kortere contexten."""

    label = "Markov Chain (1-Step / 2-Step)"

    def __init__(self, max_order=2, rng=None):
        self.max_order = max_order
        # Laatste gekozen kleuren, maximaal max_order stuks
        self.history = deque(maxlen=max_order)
        # tables[k][context] = telling van de kleur die volgde op die context
        self.tables = {k: defaultdict(lambda: [0] * N) for k in range(1, max_order + 1)}

    def predict(self, order):
        # Begin bij de langste context en val terug op een kortere als er te
        # weinig waarnemingen zijn (minder dan 2).
        for k in range(min(self.max_order, len(self.history)), 0, -1):
            counts = self.tables[k].get(tuple(list(self.history)[-k:]))
            if counts and sum(counts) >= 2:
                # +0.5 is een zachte startwaarde zodat geen enkele kleur op 0 staat
                return normalize([c + 0.5 for c in counts])
        return list(UNIFORM)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        past = list(self.history)
        # Registreer de gekozen kleur bij elke contextlengte
        for k in range(1, self.max_order + 1):
            if len(past) >= k:
                self.tables[k][tuple(past[-k:])][colour] += 1
        self.history.append(colour)
