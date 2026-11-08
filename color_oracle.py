"""Color Oracle: houd de nauwkeurigheid van de AI onder de drempel (WIN_THRESHOLD) gedurende 100 rondes.

Elke ronde staan de vier gekleurde tegels in willekeurige volgorde. De AI legt
een voorspelling vast, jij kiest een tegel, daarna wordt de gok van de AI
getoond en schudden de tegels opnieuw. Onder de motorkap weegt een ensemble van
heuristische voorspellers mee via een Hedge-achtige multiplicative weights update.

Dev screen: druk op Ctrl+Shift+D om het zijmenu te openen of te sluiten. Het
menu bevat twee schakelaars, beide uit bij de start: de strategiegewichten en
de voorspelling van de AI voor de keuze. Geen van beide verandert hoe de AI
voorspelt.

Starten:  python color_oracle.py
Nodig:    Python 3.9+ met Tkinter. Geen pakketten van derden.
"""

import math
import random
import tkinter as tk
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# Spelinstellingen
# ---------------------------------------------------------------------------
TOTAL_ROUNDS = 100       # vaste spellengte
WIN_THRESHOLD = 0.27     # de AI moet strikt onder deze nauwkeurigheid eindigen
REVEAL_MS = 750          # hoe lang de gok van de AI zichtbaar blijft na een keuze
SHUFFLE_MS = 250         # duur van de schudanimatie

# ---------------------------------------------------------------------------
# AI-instellingen
# ---------------------------------------------------------------------------
ETA = 0.35               # leersnelheid van de multiplicative weights update
FLOOR = 0.03             # kleinste aandeel dat een strategie mag houden

# Strategieën in het spel, in weergavevolgorde. Haal een sleutel weg om een
# strategie uit te zetten.
# Sleutels: colors, bias, random, streak, step, lag, reaction, position, pair
ACTIVE_STRATEGIES = (
    "colors", "bias", "random", "streak", "step", "lag", "reaction", "position", "pair",
)

# ---------------------------------------------------------------------------
# Constanten
# ---------------------------------------------------------------------------
COLORS = {
    "Red": "#ff4d5a",
    "Blue": "#3d8bff",
    "Green": "#2fd18b",
    "Yellow": "#ffc933",
}
NAMES = list(COLORS)
N = len(NAMES)
UNIFORM = [1.0 / N] * N  # gelijke kans voor elke kleur

# Maximaal aantal AI-treffers waarbij de AI nog strikt onder de drempel blijft.
# De 1e-9 voorkomt een afrondingsfout bij floats (bijvoorbeeld 0.27 * 100).
MAX_AI_HITS = math.ceil(WIN_THRESHOLD * TOTAL_ROUNDS - 1e-9) - 1

# Kleuren en lettertype van de interface
BG = "#0b0d14"
PANEL = "#141824"
PANEL2 = "#1d2333"
FG = "#f2f4fa"
MUTED = "#7f879d"
ACCENT = "#7c6cff"
GOLD = "#ffc933"
GOOD = "#2fd18b"
BAD = "#ff4d5a"
FONT = "Segoe UI"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
def normalize(values):
    """Schaal waarden zodat ze optellen tot 1. Bij een som van 0 volgt UNIFORM."""
    total = sum(values)
    if total <= 0:
        return list(UNIFORM)
    return [v / total for v in values]


def argmax_random(dist, rng):
    """Kies de index met de hoogste kans. Bij een gelijke stand beslist het lot."""
    best = max(dist)
    ties = [i for i, p in enumerate(dist) if abs(p - best) < 1e-9]
    return rng.choice(ties)


def to_color_dist(pos_dist, order):
    """Zet een verdeling over schermposities om in een verdeling over kleuren.

    order[positie] is de kleur die op die positie staat in de huidige ronde.
    """
    dist = [0.0] * N
    for pos, p in enumerate(pos_dist):
        dist[order[pos]] = p
    return dist


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

    def update(self, color, pos=None, ai_guess=None, order=None):
        past = list(self.history)
        # Registreer de gekozen kleur bij elke contextlengte
        for k in range(1, self.max_order + 1):
            if len(past) >= k:
                self.tables[k][tuple(past[-k:])][color] += 1
        self.history.append(color)


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

    def update(self, color, pos=None, ai_guess=None, order=None):
        self.scores = [s * self.decay for s in self.scores]
        self.scores[color] += 1.0
        if self.last is not None:
            self.transitions += 1
            if color == self.last:
                self.repeats += 1
        self.last = color


class RandomStrategy:
    """Feedback-vangnet: een zachte, gewogen willekeurige gok om te blijven verkennen."""

    label = "Baseline Randomizer"

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def predict(self, order):
        # Eén willekeurige kleur krijgt 0.7 extra kans bovenop een kleine basiskans
        pick = self.rng.randrange(N)
        dist = [0.3 / N] * N
        dist[pick] += 0.7
        return dist

    def update(self, color, pos=None, ai_guess=None, order=None):
        pass  # deze strategie leert niets


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
        for color, w in zip(others, weights):
            dist[color] = (1.0 - r) * w / total
        return dist

    def update(self, color, pos=None, ai_guess=None, order=None):
        if self.last is None:
            self.run = 1
        else:
            bucket = min(self.run, self.max_bucket)
            if color == self.last:
                self.stats[bucket][0] += 1
                self.run += 1
            else:
                self.stats[bucket][1] += 1
                self.run = 1
        self.prefs = [p * self.decay for p in self.prefs]
        self.prefs[color] += 1.0
        self.last = color


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
                return to_color_dist(pos_dist, order)
        return list(UNIFORM)

    def update(self, color, pos=None, ai_guess=None, order=None):
        if self.last_pos is not None:
            delta = (pos - self.last_pos) % N   # sprong rond het scherm, modulo N
            for k in range(0, self.max_order + 1):
                if len(self.deltas) >= k:
                    self.tables[k][self._context(k)][delta] += 1
            self.deltas.append(delta)
        self.last_pos = pos


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

    def update(self, color, pos=None, ai_guess=None, order=None):
        past = list(self.history)
        for lag in self.LAGS:
            if len(past) >= lag:
                self.lag_trials[lag] += 1
                if color == past[-lag]:
                    self.lag_hits[lag] += 1
        if len(past) >= self.WINDOW:
            absent = self._absent()
            self.cold_expected += len(absent) / N
            if color in absent:
                self.cold_hits += 1
        self.history.append(color)


class ReactionStrategy:
    """Feedback: hoe jij reageert nadat de AI raak of mis gokte."""

    label = "Dodge & Reaction Tracker"

    def __init__(self, rng=None):
        self.last = None               # laatst gekozen kleur
        self.ai_last = None            # laatste gok van de AI
        self.hit_last = None           # raakte de AI de vorige ronde
        # rep[raak] = [herhalingen, kansen] van jouw laatste kleur na een raak of mis
        self.rep = {True: [0, 0], False: [0, 0]}
        # adopt = [keren dat je de gok van de AI overnam, kansen] na een misser
        self.adopt = [0, 0]

    @staticmethod
    def _rate(pair):
        return (pair[0] + 1.0) / (pair[1] + 4.0)

    def predict(self, order):
        if self.last is None or self.ai_last is None:
            return list(UNIFORM)
        r = self._rate(self.rep[self.hit_last])
        if self.hit_last:
            # Na een raak: herhaal je je kleur, of wissel je naar iets anders
            dist = [(1.0 - r) / (N - 1)] * N
            dist[self.last] = r
            return dist
        # Na een misser: herhaal je je kleur, neem je de gok van de AI over, of iets anders
        a = self._rate(self.adopt)
        if r + a > 0.98:
            scale = 0.98 / (r + a)
            r, a = r * scale, a * scale
        rest = (1.0 - r - a) / (N - 2)
        dist = [rest] * N
        dist[self.last] = r
        dist[self.ai_last] = a
        return dist

    def update(self, color, pos=None, ai_guess=None, order=None):
        if self.last is not None and self.ai_last is not None:
            pair = self.rep[self.hit_last]
            pair[1] += 1
            if color == self.last:
                pair[0] += 1
            if not self.hit_last:
                self.adopt[1] += 1
                if color == self.ai_last:
                    self.adopt[0] += 1
        self.last = color
        self.ai_last = ai_guess
        self.hit_last = (ai_guess == color) if ai_guess is not None else None


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
        return to_color_dist(pos_dist, order)

    def update(self, color, pos=None, ai_guess=None, order=None):
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


class PairStrategy:
    """Structureel: hoe vaak elke kleur gekozen wordt als die op een bepaalde plek staat.

    Voor elke tegel op het scherm weet het model hoe vaak precies dat paar van
    positie en kleur getoond is en hoe vaak het gekozen is.
    """

    label = "Cyclic Loop & Pair Detector"

    def __init__(self, rng=None):
        self.chosen = [[0] * N for _ in range(N)]   # chosen[positie][kleur]
        self.shown = [[0] * N for _ in range(N)]    # shown[positie][kleur]

    def predict(self, order):
        # Keuzekans per tegel: aantal keer gekozen gedeeld door aantal keer getoond
        scores = [
            (self.chosen[p][order[p]] + 1.0) / (self.shown[p][order[p]] + 4.0)
            for p in range(N)
        ]
        return to_color_dist(normalize(scores), order)

    def update(self, color, pos=None, ai_guess=None, order=None):
        for p in range(N):
            self.shown[p][order[p]] += 1
        self.chosen[pos][order[pos]] += 1


# Koppelt elke sleutel uit ACTIVE_STRATEGIES aan zijn klasse
STRATEGY_CLASSES = {
    "colors": MarkovStrategy,
    "bias": FrequencyStrategy,
    "random": RandomStrategy,
    "streak": StreakStrategy,
    "step": StepStrategy,
    "lag": LagStrategy,
    "reaction": ReactionStrategy,
    "position": PositionStrategy,
    "pair": PairStrategy,
}


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
        color = self.order[pos]
        hit = self.final == color
        # Strategieën die goed gokten groeien met e^eta, de rest krimpt met e^-eta
        factors = [
            math.exp(self.eta if pick == color else -self.eta) for pick in self.picks
        ]
        self.weights = update_weights(self.weights, factors, self.floor)
        for strategy in self.strategies:
            strategy.update(color, pos=pos, ai_guess=self.final, order=self.order)
        return hit


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
def rounded_points(x1, y1, x2, y2, r):
    """Punten voor een rechthoek met afgeronde hoeken, bedoeld voor smooth=True."""
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r,
        x1, y1 + r, x1, y1,
    ]


def random_order(previous=None):
    """Geef een willekeurige tegelvolgorde die verschilt van de vorige."""
    order = list(range(N))
    while True:
        random.shuffle(order)
        if order != previous:
            return order


class TileBoard(tk.Canvas):
    """De vier gekleurde tegels. Bij het schudden schuiven de tegels naar hun nieuwe plek."""

    W, H = 680, 250
    TILE_W, TILE_H, GAP, TOP = 142, 150, 20, 42

    def __init__(self, master, on_click):
        super().__init__(master, width=self.W, height=self.H, bg=BG, highlightthickness=0)
        self.on_click = on_click
        self.locked = True       # klikken is pas toegestaan als het bord ontgrendeld is
        self.job = None          # lopende animatiestap
        self.left = (self.W - (N * self.TILE_W + (N - 1) * self.GAP)) / 2
        self.pos_x = {}          # huidige x van elke tegel (per kleur)
        self.pos_y = {c: 0.0 for c in range(N)}
        self.rects = {}
        self.badges = {}
        # Cijfers 1 tot 4 onder de vaste posities
        for pos in range(N):
            cx = self.slot_x(pos) + self.TILE_W / 2
            self.create_text(
                cx, self.TOP + self.TILE_H + 28, text=str(pos + 1), fill=MUTED,
                font=(FONT, 14, "bold"),
            )
        # Elke tegel krijgt een eigen tag, zodat alle onderdelen samen bewegen
        for color in range(N):
            x = self.slot_x(color)
            tag = f"t{color}"
            fill = COLORS[NAMES[color]]
            self.rects[color] = self.create_polygon(
                rounded_points(x, self.TOP, x + self.TILE_W, self.TOP + self.TILE_H, 24),
                smooth=True, fill=fill, outline=fill, width=4, tags=(tag,),
            )
            self.create_text(
                x + self.TILE_W / 2, self.TOP + self.TILE_H / 2, text=NAMES[color],
                fill="#10131c", font=(FONT, 17, "bold"), tags=(tag,),
            )
            # Label boven de tegel (YOU, AI of YOU + AI), eerst verborgen
            self.badges[color] = self.create_text(
                x + self.TILE_W / 2, self.TOP - 18, text="", fill=FG,
                font=(FONT, 11, "bold"), tags=(tag,), state="hidden",
            )
            self.pos_x[color] = x
            self.tag_bind(tag, "<Button-1>", lambda e, c=color: self._click(c))
            self.tag_bind(tag, "<Enter>", lambda e, c=color: self._hover(c, True))
            self.tag_bind(tag, "<Leave>", lambda e, c=color: self._hover(c, False))

    def slot_x(self, pos):
        # x-coördinaat van de linkerrand van een positie
        return self.left + pos * (self.TILE_W + self.GAP)

    def _click(self, color):
        if not self.locked:
            self.on_click(color)

    def _hover(self, color, inside):
        if self.locked:
            return
        self.itemconfig(
            self.rects[color], outline="#ffffff" if inside else COLORS[NAMES[color]]
        )
        self.config(cursor="hand2" if inside else "")

    def cancel(self):
        # Stop een lopende animatie
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None

    def set_order(self, order, animate=False, on_done=None):
        """order[positie] is de kleur die daar staat."""
        self.cancel()
        targets = {color: self.slot_x(pos) for pos, color in enumerate(order)}
        starts = dict(self.pos_x)
        steps = max(2, SHUFFLE_MS // 16) if animate else 1  # ongeveer 60 beelden per seconde

        def frame(i):
            t = i / steps
            ease = t * t * (3 - 2 * t)  # smoothstep: zacht starten en afremmen
            for c in range(N):
                nx = starts[c] + (targets[c] - starts[c]) * ease
                # Tegels golven om en om omhoog en omlaag tijdens het schuiven
                ny = ((-1) ** c) * 26 * math.sin(math.pi * t) if animate else 0.0
                self.move(f"t{c}", nx - self.pos_x[c], ny - self.pos_y[c])
                self.pos_x[c], self.pos_y[c] = nx, ny
            if i < steps:
                self.job = self.after(16, lambda: frame(i + 1))
            else:
                self.job = None
                # Zet elke tegel exact op de doelplek, tegen afrondingsverschillen
                for c in range(N):
                    self.move(f"t{c}", targets[c] - self.pos_x[c], -self.pos_y[c])
                    self.pos_x[c], self.pos_y[c] = targets[c], 0.0
                if on_done:
                    on_done()

        frame(1)

    def highlight(self, picked, predicted):
        # Wis eerst de vorige markeringen
        for c in range(N):
            self.itemconfig(self.rects[c], outline=COLORS[NAMES[c]], width=4, dash="")
            self.itemconfig(self.badges[c], text="", state="hidden")
        if picked == predicted:
            self.itemconfig(self.rects[picked], outline="#ffffff", width=6)
            self.itemconfig(self.badges[picked], text="YOU + AI", fill=BAD, state="normal")
            return
        self.itemconfig(self.rects[picked], outline="#ffffff", width=6)
        self.itemconfig(self.badges[picked], text="YOU", fill=FG, state="normal")
        self.itemconfig(self.rects[predicted], outline="#ffffff", width=4, dash=(8, 6))
        self.itemconfig(self.badges[predicted], text="AI", fill=ACCENT, state="normal")

    def clear_highlight(self):
        for c in range(N):
            self.itemconfig(self.rects[c], outline=COLORS[NAMES[c]], width=4, dash="")
            self.itemconfig(self.badges[c], text="", state="hidden")


class BrainPanel(tk.Canvas):
    """Live gewichten van de strategieën. Label en percentage boven, de balk eronder.

    De lange strategienamen hebben de volle paneelbreedte nodig, daarom heeft
    elke rij twee regels in plaats van een labelkolom naast de balk.
    """

    W = 330
    ROW = 44
    PAD = 14

    def __init__(self, master, rows):
        super().__init__(
            master, width=self.W, height=self.PAD + rows * self.ROW, bg=PANEL,
            highlightthickness=0,
        )

    def render(self, items):
        """items is een lijst van (label, gewicht). De hoogste krijgt een gouden balk."""
        self.delete("all")
        top = max(w for _, w in items)
        lead = top - min(w for _, w in items) > 0.005  # alleen markeren bij een duidelijk verschil
        scale = max(top, 0.2)                          # de balken schalen mee met het hoogste gewicht
        bar_left, bar_right = self.PAD, self.W - self.PAD
        bar_width = bar_right - bar_left
        for i, (label, weight) in enumerate(items):
            y = 10 + i * self.ROW
            is_top = lead and weight == top
            self.create_text(
                self.PAD, y + 8, text=label, anchor="w", fill=FG if is_top else MUTED,
                font=(FONT, 10, "bold" if is_top else "normal"),
            )
            self.create_text(
                bar_right, y + 8, text=f"{weight * 100:.0f}%", anchor="e", fill=FG,
                font=(FONT, 10, "bold"),
            )
            self.create_rectangle(bar_left, y + 22, bar_right, y + 32, fill=PANEL2, outline="")
            self.create_rectangle(
                bar_left, y + 22, bar_left + bar_width * weight / scale, y + 32,
                fill=GOLD if is_top else ACCENT, outline="",
            )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Color Oracle")
        self.configure(bg=BG)
        self.geometry("1120x740")
        self.minsize(1040, 700)

        self.brain = Ensemble()
        self.order = list(range(N))
        # Fases: locked, waiting (wacht op keuze), reveal, shuffling, over
        self.phase = "locked"
        self.rounds = 0
        self.hits = 0
        self.jobs = []              # geplande after-taken, zodat ze te annuleren zijn
        self.dev_open = False       # staat het dev screen open
        self.show_weights = False   # schakelaar: strategiegewichten tonen
        self.show_prediction = False  # schakelaar: AI-voorspelling tonen voor de keuze

        self._build()
        self._build_overlay()
        # Toetsen 1 tot 4 kiezen een schermpositie
        for i in range(N):
            self.bind(str(i + 1), lambda e, i=i: self.pick_position(i))
        self.bind("<Control-Shift-D>", self._toggle_dev)
        self.bind("<Control-Shift-d>", self._toggle_dev)
        self.bind("<Return>", self._restart_key)
        self.bind("<space>", self._restart_key)
        self.new_game()

    # ----- indeling -------------------------------------------------------
    def _stat(self, parent, title, column):
        # Eén statistiekvak met titel, waarde en onderschrift. Het grid met
        # uniform kolommen houdt alle vakken even breed en even hoog.
        box = tk.Frame(parent, bg=PANEL)
        box.grid(row=0, column=column, sticky="nsew", padx=6)
        tk.Label(box, text=title, bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(
            pady=(10, 0)
        )
        value = tk.Label(box, text="", bg=PANEL, fg=FG, font=(FONT, 24, "bold"))
        value.pack()
        caption = tk.Label(box, text="", bg=PANEL, fg=MUTED, font=(FONT, 9))
        caption.pack(pady=(0, 10))
        return value, caption

    def _build(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        # Het dev screen is een zwevend paneel rechtsboven op het hoofdvenster.
        # Het wordt met place() over het spel gelegd, dus de rest verschuift niet.
        self.dev_frame = tk.Frame(self, bg=PANEL, padx=16, pady=14)

        tk.Label(
            left, text="Color Oracle", bg=BG, fg=FG, font=(FONT, 30, "bold")
        ).pack()
        tk.Label(
            left,
            text=(
                f"Keep the AI under {WIN_THRESHOLD * 100:g}% accuracy for {TOTAL_ROUNDS} "
                "rounds. Tiles shuffle after every round."
            ),
            bg=BG, fg=MUTED, font=(FONT, 11),
        ).pack(pady=(0, 12))

        # Drie statistiekvakken: voortgang, nauwkeurigheid en treffers
        stats = tk.Frame(left, bg=BG)
        stats.pack(fill="x")
        for column in range(3):
            stats.columnconfigure(column, weight=1, uniform="stat")
        self.round_value, self.round_caption = self._stat(stats, "PROGRESS", 0)
        self.acc_value, self.acc_caption = self._stat(stats, "AI ACCURACY", 1)
        self.hits_value, self.hits_caption = self._stat(stats, "AI HITS", 2)

        # Voortgangsbalk, tekent zichzelf opnieuw bij elke formaatwijziging
        self.progress = tk.Canvas(left, height=10, bg=BG, highlightthickness=0)
        self.progress.pack(fill="x", padx=6, pady=(10, 8))
        self.progress.bind("<Configure>", lambda e: self._draw_progress())

        # Kaart met de voorspelling van de AI
        card = tk.Frame(left, bg=PANEL)
        card.pack(fill="x", padx=6, pady=4)
        tk.Label(card, text="AI PREDICTION", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(
            pady=(10, 4)
        )
        # Het kleurvlak staat boven de tekst en beide staan in het midden. Zo
        # blijft de plek gelijk, ook als de tekst van lengte wisselt.
        self.chip = tk.Label(
            card, text="?", width=4, height=2, bg=PANEL2, fg=FG, font=(FONT, 14, "bold")
        )
        self.chip.pack(pady=(0, 8))
        self.card_text = tk.Label(
            card, text="", bg=PANEL, fg=FG, font=(FONT, 15, "bold"), width=34, anchor="center"
        )
        self.card_text.pack(pady=(0, 12))

        self.board = TileBoard(left, self.pick_color)
        self.board.pack(pady=(10, 0))
        tk.Label(
            left,
            text="Click a tile or press 1 to 4. Keys follow the screen position.",
            bg=BG, fg=MUTED, font=(FONT, 10),
        ).pack()

        restart = tk.Label(
            left, text="Restart", bg=PANEL2, fg=MUTED, font=(FONT, 10, "bold"),
            padx=16, pady=6, cursor="hand2",
        )
        restart.pack(side="bottom", pady=(8, 0))
        restart.bind("<Button-1>", lambda e: self.new_game())

        # Inhoud van het dev screen: uitleg, twee schakelaars en het gewichtenpaneel
        dev = self.dev_frame
        tk.Label(dev, text="DEV SCREEN", bg=PANEL, fg=FG, font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Label(
            dev, text="Showcase only. Nothing here changes how the AI predicts.",
            bg=PANEL, fg=MUTED, font=(FONT, 9), wraplength=BrainPanel.W, justify="left",
        ).pack(anchor="w", pady=(0, 10))
        self.weights_toggle = self._toggle(dev, "Show strategy weights", self._toggle_weights)
        self.prediction_toggle = self._toggle(
            dev, "Show AI prediction before pick", self._toggle_prediction
        )
        # De houder met de balken verschijnt alleen als de schakelaar aan staat
        self.brain_holder = tk.Frame(dev, bg=PANEL)
        tk.Label(
            self.brain_holder, text="Live strategy weights", bg=PANEL, fg=MUTED, font=(FONT, 9)
        ).pack(anchor="w", pady=(10, 8))
        self.brain_panel = BrainPanel(self.brain_holder, len(self.brain.strategies))
        self.brain_panel.pack()

    def _toggle(self, parent, text, command):
        # Een klikbare rij met een AAN/UIT-label. Geeft het statuslabel terug.
        row = tk.Frame(parent, bg=PANEL2, cursor="hand2")
        row.pack(fill="x", pady=3)
        name = tk.Label(
            row, text=text, bg=PANEL2, fg=FG, font=(FONT, 10), anchor="w", padx=12, pady=8
        )
        name.pack(side="left", fill="x", expand=True)
        state = tk.Label(
            row, text="OFF", bg=BG, fg=MUTED, font=(FONT, 9, "bold"), width=5, pady=3
        )
        state.pack(side="right", padx=10)
        for widget in (row, name, state):
            widget.bind("<Button-1>", lambda e: command())
        return state

    @staticmethod
    def _paint_toggle(state, on):
        # Kleur en tekst van het statuslabel volgen de stand van de schakelaar
        state.config(
            text="ON" if on else "OFF", bg=GOOD if on else BG,
            fg="#10131c" if on else MUTED,
        )

    def _build_overlay(self):
        # Scherm voor overwinning of nederlaag, bedekt het hele venster
        self.overlay = tk.Frame(self, bg=BG)
        card = tk.Frame(self.overlay, bg=PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.over_title = tk.Label(card, text="", bg=PANEL, font=(FONT, 56, "bold"))
        self.over_title.pack(padx=70, pady=(34, 6))
        self.over_message = tk.Label(
            card, text="", bg=PANEL, fg=FG, font=(FONT, 16), wraplength=520
        )
        self.over_message.pack(padx=40)
        self.over_stats = tk.Label(card, text="", bg=PANEL, fg=MUTED, font=(FONT, 13))
        self.over_stats.pack(pady=(18, 2))
        self.over_note = tk.Label(
            card, text="", bg=PANEL, fg=MUTED, font=(FONT, 11), wraplength=520
        )
        self.over_note.pack(padx=40)
        self.play_button = tk.Label(
            card, text="PLAY AGAIN", bg=ACCENT, fg="#ffffff", font=(FONT, 18, "bold"),
            padx=54, pady=14, cursor="hand2",
        )
        self.play_button.pack(pady=(26, 36))
        self.play_button.bind("<Button-1>", lambda e: self.new_game())
        self.play_button.bind("<Enter>", lambda e: self.play_button.config(bg="#9a8dff"))
        self.play_button.bind("<Leave>", lambda e: self.play_button.config(bg=ACCENT))

    # ----- dev screen -----------------------------------------------------
    def _toggle_dev(self, event=None):
        # Ctrl+Shift+D opent of sluit het zijmenu
        self.dev_open = not self.dev_open
        if self.dev_open:
            self.dev_frame.place(relx=1.0, x=-16, y=16, anchor="ne")
            self.dev_frame.lift()
        else:
            self.dev_frame.place_forget()

    def _toggle_weights(self):
        self.show_weights = not self.show_weights
        self._paint_toggle(self.weights_toggle, self.show_weights)
        if self.show_weights:
            self.brain_holder.pack(anchor="w")
            self._render_brain()
        else:
            self.brain_holder.pack_forget()

    def _toggle_prediction(self):
        self.show_prediction = not self.show_prediction
        self._paint_toggle(self.prediction_toggle, self.show_prediction)
        # Tijdens het wachten op een keuze werkt de kaart direct bij
        if self.phase in ("waiting", "shuffling"):
            self._seal_card()

    def _render_brain(self):
        self.brain_panel.render(
            [(s.label, w) for s, w in zip(self.brain.strategies, self.brain.weights)]
        )

    # ----- spelverloop ----------------------------------------------------
    def _after(self, ms, fn):
        # Plan een taak en onthoud die, zodat een nieuw spel hem kan annuleren
        self.jobs.append(self.after(ms, fn))

    def _cancel_jobs(self):
        for job in self.jobs:
            self.after_cancel(job)
        self.jobs = []
        self.board.cancel()

    def _restart_key(self, event=None):
        # Enter of spatie start alleen een nieuw spel op het eindscherm
        if self.phase == "over":
            self.new_game()

    def new_game(self):
        self._cancel_jobs()
        self.overlay.place_forget()
        self.brain.reset()
        self.rounds = 0
        self.hits = 0
        self.order = random_order()
        self.board.clear_highlight()
        self.board.set_order(self.order, animate=False)
        # De AI legt de gok vast voordat de speler iets kiest
        self.brain.begin_round(self.order)
        self.phase = "waiting"
        self.board.locked = False
        self._seal_card()
        self._refresh()

    def pick_color(self, color):
        # Een klik op een tegel wordt omgezet naar de schermpositie van die kleur
        self.pick_position(self.order.index(color))

    def pick_position(self, pos):
        if self.phase != "waiting":
            return
        self.phase = "reveal"
        self.board.locked = True
        color = self.order[pos]
        predicted = self.brain.final   # de gok stond al vast voor deze keuze
        hit = self.brain.resolve(pos)  # pas nu leert de AI van de keuze
        self.rounds += 1
        self.hits += int(hit)
        self.board.highlight(color, predicted)
        self.chip.config(text="", bg=COLORS[NAMES[predicted]])
        self.card_text.config(
            text=f"AI predicted {NAMES[predicted]}.  {'HIT' if hit else 'MISS'}",
            fg=BAD if hit else GOOD,
        )
        self._refresh()
        self._after(REVEAL_MS, self._next_round)

    def _next_round(self):
        self.board.clear_highlight()
        if self.rounds >= TOTAL_ROUNDS:
            self._game_over()
            return
        self.order = random_order(self.order)
        self.phase = "shuffling"
        # De nieuwe gok wordt vastgelegd terwijl de tegels nog schuiven
        self.brain.begin_round(self.order)
        self._seal_card()
        self.board.set_order(self.order, animate=True, on_done=self._ready)

    def _ready(self):
        # De animatie is klaar: de speler mag weer kiezen
        self.phase = "waiting"
        self.board.locked = False
        self._refresh()

    def _game_over(self):
        self.phase = "over"
        self.board.locked = True
        accuracy = self.hits / TOTAL_ROUNDS * 100
        if self.hits <= MAX_AI_HITS:
            self.over_title.config(text="VICTORY!", fg=GOOD)
            self.over_message.config(
                text="You successfully outsmarted the AI's pattern recognition."
            )
        else:
            self.over_title.config(text="DEFEAT!", fg=BAD)
            self.over_message.config(text="The AI figured out your patterns.")
        plural = "hit" if self.hits == 1 else "hits"
        self.over_stats.config(
            text=f"Final AI accuracy: {accuracy:.1f}%   ({self.hits} {plural} in {TOTAL_ROUNDS} rounds)"
        )
        note = (
            f"To win, the AI had to stay under {WIN_THRESHOLD * 100:g}% "
            f"({MAX_AI_HITS} hits or fewer)."
        )
        if self.hits > MAX_AI_HITS:
            # Bij een nederlaag: noem de strategie met het hoogste gewicht
            weights = self.brain.weights
            top = max(range(len(weights)), key=lambda i: weights[i])
            note += f" Its most trusted strategy at the end: {self.brain.strategies[top].label}."
        self.over_note.config(text=note)
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.overlay.lift()
        if self.dev_open:
            self.dev_frame.lift()  # het dev screen blijft bereikbaar op het eindscherm

    # ----- weergave -------------------------------------------------------
    def _draw_progress(self):
        self.progress.delete("all")
        width = self.progress.winfo_width()
        self.progress.create_rectangle(0, 0, width, 10, fill=PANEL2, outline="")
        self.progress.create_rectangle(
            0, 0, width * self.rounds / TOTAL_ROUNDS, 10, fill=ACCENT, outline=""
        )

    def _seal_card(self):
        # Toont de vastgelegde gok alleen als het dev screen dat aanzet.
        # Anders blijft de kaart verzegeld met een vraagteken.
        if self.show_prediction:
            predicted = self.brain.final
            self.chip.config(text="", bg=COLORS[NAMES[predicted]])
            self.card_text.config(text=f"AI has locked in {NAMES[predicted]}.", fg=FG)
            return
        self.chip.config(text="?", bg=PANEL2)
        self.card_text.config(text="Locked in. Make your move.", fg=FG)

    def _refresh(self):
        # Rondeteller: tijdens het wachten en schudden telt de lopende ronde mee
        current = min(self.rounds + (1 if self.phase in ("waiting", "shuffling") else 0),
                      TOTAL_ROUNDS)
        current = max(current, 1)
        self.round_value.config(text=f"Round {current} / {TOTAL_ROUNDS}")
        left = TOTAL_ROUNDS - self.rounds
        self.round_caption.config(text=f"{left} round{'s' if left != 1 else ''} left")
        # Nauwkeurigheid: groen onder de drempel, rood erboven
        if self.rounds:
            accuracy = self.hits / self.rounds * 100
            under = self.hits / self.rounds < WIN_THRESHOLD
            self.acc_value.config(text=f"{accuracy:.1f}%", fg=GOOD if under else BAD)
        else:
            self.acc_value.config(text="--", fg=FG)
        self.acc_caption.config(text=f"must finish under {WIN_THRESHOLD * 100:g}%")
        # Zodra de treffers boven het maximum uitkomen, staat de nederlaag vast
        self.hits_value.config(text=str(self.hits), fg=BAD if self.hits > MAX_AI_HITS else FG)
        self.hits_caption.config(
            text="defeat locked in" if self.hits > MAX_AI_HITS else f"limit {MAX_AI_HITS}",
            fg=BAD if self.hits > MAX_AI_HITS else MUTED,
        )
        self._draw_progress()
        if self.show_weights:
            self._render_brain()


if __name__ == "__main__":
    App().mainloop()