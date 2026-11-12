"""Statistisch: kans op dezelfde kleur na een reeks."""

from colour_oracle.constants import N, UNIFORM


class StreakStrategy:
    """Statistisch: kans op dezelfde kleur na een reeks van 1, 2 of 3+ keer."""

    label = "Anti-Streak Predictor"

    def __init__(self, max_bucket=3, decay=0.97, rng=None):
        self.max_bucket = max_bucket
        self.decay = decay
        # stats[reekslengte] = [aantal herhalingen, aantal wissels], met een lichte startwaarde
        self.stats = {k: [1.0, 3.0] for k in range(1, max_bucket + 1)}
        self.prefs = [0.0] * N             # voorkeur voor de overige kleuren
        self.last = None
        self.run = 0                       # lengte van de huidige reeks

    def predict(self, order):
        if self.last is None:
            return list(UNIFORM)
        repeats, switches = self.stats[min(self.run, self.max_bucket)]
        r = repeats / (repeats + switches)  # kans op herhalen bij deze reekslengte
        others = [c for c in range(N) if c != self.last]
        weights = [self.prefs[c] + 1.0 for c in others]
        total = sum(weights)
        dist = [0.0] * N
        dist[self.last] = r
        # De resterende kans (1 - r) wordt verdeeld over de andere kleuren
        for colour, w in zip(others, weights):
            dist[colour] = (1.0 - r) * w / total
        return dist

    def update(self, colour, pos=None, ai_guess=None, order=None):
        if self.last is None:
            self.run = 1
        else:
            bucket = min(self.run, self.max_bucket)
            if colour == self.last:
                self.stats[bucket][0] += 1
                self.run += 1
            else:
                self.stats[bucket][1] += 1
                self.run = 1
        self.prefs = [p * self.decay for p in self.prefs]
        self.prefs[colour] += 1.0
        self.last = colour
