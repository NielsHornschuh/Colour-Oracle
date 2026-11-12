"""Statistisch: kleurfrequentie met afnemend gewicht."""

from colour_oracle.constants import N
from colour_oracle.engine.helpers import normalize


class FrequencyStrategy:
    """Statistisch: kleurfrequentie met afnemend gewicht plus een correctie voor herhalen."""

    label = "Frequency & Recency Bias"

    def __init__(self, decay=0.85, rng=None):
        self.decay = decay                 # oudere keuzes tellen steeds minder mee
        self.scores = [0.0] * N
        self.last = None
        self.repeats = 0                   # hoe vaak dezelfde kleur twee keer achter elkaar
        self.transitions = 0               # aantal gemeten overgangen

    def predict(self, order):
        dist = normalize([s + 0.1 for s in self.scores])
        if self.last is not None:
            # Versterk of verzwak de laatst gekozen kleur naar de gemeten herhaalkans
            repeat_rate = (self.repeats + 1) / (self.transitions + N)
            dist[self.last] *= repeat_rate / (1.0 / N)
            dist = normalize(dist)
        return dist

    def update(self, colour, pos=None, ai_guess=None, order=None):
        self.scores = [s * self.decay for s in self.scores]
        self.scores[colour] += 1.0
        if self.last is not None:
            self.transitions += 1
            if colour == self.last:
                self.repeats += 1
        self.last = colour
