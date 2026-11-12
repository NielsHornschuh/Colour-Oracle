"""Instellingen die je zelf kunt aanpassen. Pas een waarde aan, sla op en start opnieuw."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"math"}

import math


# ---------------------------------------------------------------------------
# Spelinstellingen
# ---------------------------------------------------------------------------
TOTAL_ROUNDS = 100       # vaste spellengte
WIN_THRESHOLD = 0.27     # de AI moet strikt onder deze nauwkeurigheid eindigen
REVEAL_MS = 750          # hoe lang de gok van de AI zichtbaar blijft na een keuze
SHUFFLE_MS = 250         # duur van de schudanimatie
CREATOR_NAME = "Niels"   # naam op het beginscherm, voor vragen en uitleg

# ---------------------------------------------------------------------------
# AI-instellingen
# ---------------------------------------------------------------------------
ETA = 0.35               # leersnelheid van de multiplicative weights update
FLOOR = 0.03             # kleinste aandeel dat een strategie mag houden

# Strategieën in het spel, in weergavevolgorde. Haal een sleutel weg om een
# strategie uit te zetten.
# Sleutels: colours, bias, random, streak, step, lag, reaction, position, pair
ACTIVE_STRATEGIES = (
    "colours", "bias", "random", "streak", "step", "lag", "reaction", "position", "pair",
)

# ---------------------------------------------------------------------------
# Taal
# ---------------------------------------------------------------------------
DEFAULT_LANGUAGE = "nl"   # taal bij het opstarten: "nl" of "en"

# Maximaal aantal AI-treffers waarbij de AI nog strikt onder de drempel blijft.
# De 1e-9 voorkomt een afrondingsfout bij floats (bijvoorbeeld 0.27 * 100).
MAX_AI_HITS = math.ceil(WIN_THRESHOLD * TOTAL_ROUNDS - 1e-9) - 1
