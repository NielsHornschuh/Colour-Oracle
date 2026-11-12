"""Feedback: toetst welke zichtbare terugkoppeling jouw gedrag verandert."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"math"}

import math

from colour_oracle.config import WIN_THRESHOLD
from colour_oracle.constants import N, UNIFORM
from colour_oracle.engine.helpers import normalize


class ReactionStrategy:
    """Feedback: toetst welke zichtbare terugkoppeling jouw gedrag verandert.

    Drie signalen worden los van elkaar gemeten:
      1. De getoonde nauwkeurigheid van de AI (groen onder de drempel, rood erboven).
      2. Of de AI de vorige ronde raak of mis gokte.
      3. Welke tegel tijdens het schudden het verst of het minst ver bewoog.
    Elk signaal krijgt een vertrouwen tussen 0 en 1 uit een z-toets. Een signaal
    zonder aantoonbare invloed krijgt vertrouwen 0 en telt dus niet mee.
    """

    label = "Dodge & Reaction Tracker"
    MIN_TRIALS = 5   # minimaal aantal waarnemingen per situatie voordat er getoetst wordt

    def __init__(self, rng=None):
        self.last = None            # laatst gekozen kleur
        self.ai_last = None         # laatste gok van de AI
        self.hit_last = None        # raakte de AI de vorige ronde
        self.prev_order = None      # tegelvolgorde van de vorige ronde
        self.n = 0                  # aantal gespeelde rondes
        self.ai_hits = 0            # aantal AI-treffers, voor de getoonde nauwkeurigheid
        # Per situatie: [keren dat je dezelfde kleur koos, aantal kansen]
        self.stay_by_status = {True: [0, 0], False: [0, 0]}   # True = groen
        self.stay_by_hit = {True: [0, 0], False: [0, 0]}      # True = AI had raak
        self.adopt = [0, 0]         # na een misser: de gok van de AI overgenomen
        # Beweging: hoe vaak je de grootste of kleinste verplaatser koos, en hoe vaak
        # dat bij puur toeval verwacht was (met de bijbehorende variantie)
        self.big = {"picked": 0.0, "expected": 0.0, "var": 0.0}
        self.small = {"picked": 0.0, "expected": 0.0, "var": 0.0}
        # Vertrouwen per signaal van de laatste voorspelling (bruikbaar voor het dev screen)
        self.trust = {"accuracy": 0.0, "ai_result": 0.0, "movement": 0.0}

    # ----- hulpfuncties ---------------------------------------------------
    def _green(self):
        # Zo ziet de speler de nauwkeurigheid: groen onder de drempel
        return self.n == 0 or self.ai_hits / self.n < WIN_THRESHOLD

    @staticmethod
    def _rate(pair):
        # Zachte schatting van een aandeel, met een kleine startwaarde
        return (pair[0] + 1.0) / (pair[1] + 4.0)

    TRUST_START = 1.0   # onder deze |z| is er geen aantoonbare invloed
    TRUST_FULL = 2.0    # vanaf deze |z| is het vertrouwen volledig

    @classmethod
    def _trust(cls, z):
        return min(1.0, max(0.0, (abs(z) - cls.TRUST_START) / (cls.TRUST_FULL - cls.TRUST_START)))

    def _z_diff(self, a, b):
        # Verschilt het aandeel van a = [successen, kansen] van dat van b?
        (xa, na), (xb, nb) = a, b
        if na < self.MIN_TRIALS or nb < self.MIN_TRIALS:
            return 0.0
        pooled = (xa + xb) / (na + nb)
        spread = math.sqrt(pooled * (1.0 - pooled) * (1.0 / na + 1.0 / nb))
        return 0.0 if spread == 0 else (xa / na - xb / nb) / spread

    def _z_adopt(self):
        # Wijkt het overnemen van de AI-gok af van de kans van 0.25?
        successes, trials = self.adopt
        if trials < self.MIN_TRIALS:
            return 0.0
        return (successes - 0.25 * trials) / math.sqrt(trials * 0.25 * 0.75)

    @staticmethod
    def _z_excess(group):
        # Wijkt het aantal gekozen verplaatsers af van wat toeval zou geven?
        if group["var"] <= 0:
            return 0.0
        return (group["picked"] - group["expected"]) / math.sqrt(group["var"])

    def _movers(self, order):
        # Grootste en kleinste verplaatsers sinds de vorige ronde, of None in ronde 1
        if self.prev_order is None:
            return None
        dist = [abs(order.index(c) - self.prev_order.index(c)) for c in range(N)]
        big = [c for c in range(N) if dist[c] == max(dist)]
        small = [c for c in range(N) if dist[c] == min(dist)]
        return big, small

    @staticmethod
    def _boost(weights, tiles, mass, trust):
        # De kans dat de keuze in `tiles` valt, is `mass`. Het effect schaalt met het vertrouwen.
        share = len(tiles) / N
        mass = min(0.98, max(0.02, mass))
        inside = mass / share
        outside = (1.0 - mass) / (1.0 - share)
        for c in range(N):
            weights[c] *= (inside if c in tiles else outside) ** trust

    # ----- voorspellen en leren -------------------------------------------
    def predict(self, order):
        if self.last is None:
            return list(UNIFORM)
        weights = [1.0] * N
        movers = self._movers(order)

        # Vertrouwen per signaal
        t_status = self._trust(
            self._z_diff(self.stay_by_status[True], self.stay_by_status[False])
        )
        t_stay = self._trust(self._z_diff(self.stay_by_hit[True], self.stay_by_hit[False]))
        t_adopt = self._trust(self._z_adopt())
        t_big = self._trust(self._z_excess(self.big))
        t_small = self._trust(self._z_excess(self.small))
        self.trust = {
            "accuracy": t_status,
            "ai_result": max(t_stay, t_adopt),
            "movement": max(t_big, t_small),
        }

        # 1. Getoonde nauwkeurigheid: blijf je bij je kleur in groen en wissel je in rood?
        self._boost(weights, [self.last], self._rate(self.stay_by_status[self._green()]), t_status)
        # 2. AI raak of mis: blijf je bij je kleur, of neem je de gok van de AI over?
        if self.hit_last is not None:
            self._boost(weights, [self.last], self._rate(self.stay_by_hit[self.hit_last]), t_stay)
        if self.hit_last is False and self.ai_last is not None:
            self._boost(weights, [self.ai_last], self._rate(self.adopt), t_adopt)
        # 3. Beweging: trekt de tegel die het verst (of het minst) bewoog je aan?
        if movers:
            for group, tiles, t in ((self.big, movers[0], t_big), (self.small, movers[1], t_small)):
                if len(tiles) < N:
                    ratio = (group["picked"] + 1.0) / (group["expected"] + 1.0)
                    self._boost(weights, tiles, ratio * len(tiles) / N, t)
        return normalize(weights)

    def update(self, colour, pos=None, ai_guess=None, order=None):
        green = self._green()   # de status op het moment van de keuze
        if self.last is not None and self.hit_last is not None:
            stay = int(colour == self.last)
            for pair in (self.stay_by_status[green], self.stay_by_hit[self.hit_last]):
                pair[1] += 1
                pair[0] += stay
            if not self.hit_last and self.ai_last is not None:
                self.adopt[1] += 1
                self.adopt[0] += int(colour == self.ai_last)
        movers = self._movers(order)
        if movers:
            for group, tiles in ((self.big, movers[0]), (self.small, movers[1])):
                if len(tiles) < N:
                    share = len(tiles) / N
                    group["picked"] += int(colour in tiles)
                    group["expected"] += share
                    group["var"] += share * (1.0 - share)
        self.n += 1
        self.ai_hits += int(ai_guess == colour)
        self.last = colour
        self.ai_last = ai_guess
        self.hit_last = (ai_guess == colour) if ai_guess is not None else None
        self.prev_order = list(order)
