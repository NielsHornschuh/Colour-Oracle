"""Statistisch: kleurherhalingen van 2 en 3 keuzes terug en koude kleuren."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"collections"}

from collections import deque

from colour_oracle.constants import N, UNIFORM
from colour_oracle.engine.helpers import normalize


class LagStrategy:
    """Statistisch: kleurherhalingen van 2 en 3 keuzes terug, en 'koude' kleuren."""

    label = "Gambler's Fallacy Balancer"
    LAGS = (2, 3)      # hoeveel keuzes terug er wordt gekeken
    WINDOW = 3         # aantal recente keuzes dat telt voor 'koud'

    def __init__(self, rng=None):
        self.history = deque(maxlen=self.WINDOW)
        self.lag_hits = {lag: 0 for lag in self.LAGS}
        self.lag_trials = {lag: 0 for lag in self.LAGS}
        self.cold_hits = 0.0           # hoe vaak een koude kleur gekozen werd
        self.cold_expected = 0.0       # hoe vaak dat bij puur toeval te verwachten was

    def _absent(self):
        # Kleuren die in het recente venster niet voorkwamen
        return [c for c in range(N) if c not in self.history]

    def predict(self, order):
        if len(self.history) < self.WINDOW:
            return list(UNIFORM)
        weights = [1.0] * N
        past = list(self.history)
        # Per lag: versterk of verzwak de kleur van die lag naar de gemeten herhaalkans
        for lag in self.LAGS:
            rate = (self.lag_hits[lag] + 1.0) / (self.lag_trials[lag] + 4.0)
            target = past[-lag]
            for c in range(N):
                weights[c] *= rate / 0.25 if c == target else (1.0 - rate) / 0.75
        # Daarna: geef koude kleuren meer of minder kans, naar de gemeten voorkeur
        absent = self._absent()
        a = len(absent)
        ratio = (self.cold_hits + 1.0) / (self.cold_expected + 1.0)
        mass = min(0.95, max(0.05, ratio * a / N))
        inside = mass / (a / N)
        outside = (1.0 - mass) / (1.0 - a / N)
        for c in range(N):
            weights[c] *= inside if c in absent else outside
        return normalize(weights)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        past = list(self.history)
        for lag in self.LAGS:
            if len(past) >= lag:
                self.lag_trials[lag] += 1
                if colour == past[-lag]:
                    self.lag_hits[lag] += 1
        if len(past) >= self.WINDOW:
            absent = self._absent()
            self.cold_expected += len(absent) / N
            if colour in absent:
                self.cold_hits += 1
        self.history.append(colour)
