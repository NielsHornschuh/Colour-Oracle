"""Het ensemble: alle strategieën stemmen mee, gewogen met een Hedge-achtige multiplicative weights update."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"math", "random"}

import math
import random

from colour_oracle.config import ACTIVE_STRATEGIES, ETA, FLOOR
from colour_oracle.constants import N
from colour_oracle.engine.helpers import argmax_random, normalize
from colour_oracle.engine.strategies import STRATEGY_CLASSES


def update_weights(weights, factors, floor):
    """Vermenigvuldig, normaliseer en zet daarna elk gewicht minimaal op `floor`.

    Gewichten op de ondergrens blijven er exact op staan. De massa die zij
    innemen komt uit de overige gewichten, die opnieuw geschaald worden. De lus
    herhaalt zich omdat het herschalen een ander gewicht onder de ondergrens
    kan duwen.
    """
    w = normalize([x * f for x, f in zip(weights, factors)])
    pinned = set()  # indices die op de ondergrens vastgezet zijn
    while True:
        fresh = [i for i, x in enumerate(w) if i not in pinned and x < floor]
        if not fresh:
            return w
        pinned.update(fresh)
        free_mass = 1.0 - floor * len(pinned)
        rest = sum(x for i, x in enumerate(w) if i not in pinned)
        w = [
            floor if i in pinned else x * free_mass / rest
            for i, x in enumerate(w)
        ]


class Ensemble:
    """Hedge-achtige multiplicative weights over de actieve strategieën."""

    def __init__(self, active=None, eta=ETA, floor=FLOOR, seed=None):
        self.active = tuple(active if active is not None else ACTIVE_STRATEGIES)
        self.eta = eta
        self.floor = floor
        self.seed = seed
        self.reset()

    def reset(self):
        self.rng = random.Random(self.seed)
        self.strategies = [STRATEGY_CLASSES[k](rng=self.rng) for k in self.active]
        # Iedere strategie begint met hetzelfde gewicht
        self.weights = [1.0 / len(self.strategies)] * len(self.strategies)
        self.order = list(range(N))
        self.picks = []     # de gok van elke strategie in de huidige ronde
        self.final = 0      # de uiteindelijke gok van de AI in de huidige ronde

    def begin_round(self, order):
        """order[positie] is de kleur die op die positie staat in deze ronde.

        De gok wordt hier vastgelegd, voordat de speler kiest.
        """
        self.order = list(order)
        dists = [s.predict(self.order) for s in self.strategies]
        # Elke strategie gokt de kleur met de hoogste kans
        self.picks = [argmax_random(d, self.rng) for d in dists]
        # De uiteindelijke gok volgt uit de met gewichten gemengde verdelingen
        mixed = [sum(w * d[c] for w, d in zip(self.weights, dists)) for c in range(N)]
        self.final = argmax_random(mixed, self.rng)

    def resolve(self, pos):
        """Leer van de keuze van de speler. Geeft True als de AI het goed had."""
        colour = self.order[pos]
        hit = self.final == colour
        # Strategieën die goed gokten groeien met e^eta, de rest krimpt met e^-eta
        factors = [
            math.exp(self.eta if pick == colour else -self.eta) for pick in self.picks
        ]
        self.weights = update_weights(self.weights, factors, self.floor)
        for strategy in self.strategies:
            strategy.update(colour, pos=pos, ai_guess=self.final, order=self.order)
        return hit
