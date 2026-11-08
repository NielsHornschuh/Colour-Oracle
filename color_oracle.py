"""Color Oracle: keep the AI's prediction accuracy under 25% for 25 rounds.

Each round the four colored tiles sit in a random order. The AI locks in a
prediction, you pick a tile, the AI's guess is revealed, and the tiles shuffle.
Underneath, an ensemble of heuristic predictors is weighted with a Hedge style
multiplicative weights update.

Run:   python color_oracle.py
Needs: Python 3.9+ with Tkinter. No third party packages.
"""

import math
import random
import tkinter as tk
from collections import defaultdict, deque

# ---------------------------------------------------------------------------
# Game settings
# ---------------------------------------------------------------------------
TOTAL_ROUNDS = 100        # fixed game length
WIN_THRESHOLD = 0.25     # the AI must finish strictly below this accuracy
REVEAL_MS = 750         # how long the AI's guess stays visible after a pick
SHUFFLE_MS = 250         # length of the shuffle animation

# ---------------------------------------------------------------------------
# AI settings
# ---------------------------------------------------------------------------
ETA = 0.35               # learning rate of the multiplicative weights update
FLOOR = 0.03             # smallest share a strategy is allowed to keep

# Strategies in play, in display order. Remove a key to switch a strategy off.
# Keys: colors, bias, random, streak, step, lag, reaction, position, pair
# Tested slightly stronger set for 25 rounds:
#   ("colors", "bias", "step", "position", "pair", "reaction")
ACTIVE_STRATEGIES = (
    "colors", "bias", "random", "streak", "step", "lag", "reaction", "position", "pair",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLORS = {
    "Red": "#ff4d5a",
    "Blue": "#3d8bff",
    "Green": "#2fd18b",
    "Yellow": "#ffc933",
}
NAMES = list(COLORS)
N = len(NAMES)
UNIFORM = [1.0 / N] * N

# Most AI hits allowed while still staying strictly below the threshold.
MAX_AI_HITS = math.ceil(WIN_THRESHOLD * TOTAL_ROUNDS - 1e-9) - 1

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
    total = sum(values)
    if total <= 0:
        return list(UNIFORM)
    return [v / total for v in values]


def argmax_random(dist, rng):
    best = max(dist)
    ties = [i for i, p in enumerate(dist) if abs(p - best) < 1e-9]
    return rng.choice(ties)


def to_color_dist(pos_dist, order):
    """Turn a distribution over screen positions into one over colors."""
    dist = [0.0] * N
    for pos, p in enumerate(pos_dist):
        dist[order[pos]] = p
    return dist


class MarkovStrategy:
    """Color chains: N-gram transitions on colors, backing off to shorter contexts."""

    label = "Color chains"

    def __init__(self, max_order=2, rng=None):
        self.max_order = max_order
        self.history = deque(maxlen=max_order)
        self.tables = {k: defaultdict(lambda: [0] * N) for k in range(1, max_order + 1)}

    def predict(self, order):
        for k in range(min(self.max_order, len(self.history)), 0, -1):
            counts = self.tables[k].get(tuple(list(self.history)[-k:]))
            if counts and sum(counts) >= 2:
                return normalize([c + 0.5 for c in counts])
        return list(UNIFORM)

    def update(self, color, pos=None, ai_guess=None, order=None):
        past = list(self.history)
        for k in range(1, self.max_order + 1):
            if len(past) >= k:
                self.tables[k][tuple(past[-k:])][color] += 1
        self.history.append(color)


class FrequencyStrategy:
    """Color bias: decayed color frequency plus a color repeat adjustment."""

    label = "Color bias"

    def __init__(self, decay=0.85, rng=None):
        self.decay = decay
        self.scores = [0.0] * N
        self.last = None
        self.repeats = 0
        self.transitions = 0

    def predict(self, order):
        dist = normalize([s + 0.1 for s in self.scores])
        if self.last is not None:
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
    """Random baseline: a soft weighted random guess for exploration."""

    label = "Random baseline"

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def predict(self, order):
        pick = self.rng.randrange(N)
        dist = [0.3 / N] * N
        dist[pick] += 0.7
        return dist

    def update(self, color, pos=None, ai_guess=None, order=None):
        pass


class StreakStrategy:
    """Streak breaker: chance of repeating the same color after a run of 1, 2, 3+."""

    label = "Streak breaker"

    def __init__(self, max_bucket=3, decay=0.97, rng=None):
        self.max_bucket = max_bucket
        self.decay = decay
        self.stats = {k: [1.0, 3.0] for k in range(1, max_bucket + 1)}
        self.prefs = [0.0] * N
        self.last = None
        self.run = 0

    def predict(self, order):
        if self.last is None:
            return list(UNIFORM)
        repeats, switches = self.stats[min(self.run, self.max_bucket)]
        r = repeats / (repeats + switches)
        others = [c for c in range(N) if c != self.last]
        weights = [self.prefs[c] + 1.0 for c in others]
        total = sum(weights)
        dist = [0.0] * N
        dist[self.last] = r
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
    """Step habit: Markov chain on screen position deltas (a motor habit)."""

    label = "Step habit"

    def __init__(self, max_order=2, rng=None):
        self.max_order = max_order
        self.deltas = deque(maxlen=max_order)
        self.tables = {k: defaultdict(lambda: [0] * N) for k in range(0, max_order + 1)}
        self.last_pos = None

    def _context(self, k):
        return () if k == 0 else tuple(list(self.deltas)[-k:])

    def predict(self, order):
        if self.last_pos is None:
            return list(UNIFORM)
        for k in range(min(self.max_order, len(self.deltas)), -1, -1):
            counts = self.tables[k].get(self._context(k))
            if counts and sum(counts) >= 2:
                delta_dist = normalize([c + 0.5 for c in counts])
                pos_dist = [0.0] * N
                for delta, p in enumerate(delta_dist):
                    pos_dist[(self.last_pos + delta) % N] = p
                return to_color_dist(pos_dist, order)
        return list(UNIFORM)

    def update(self, color, pos=None, ai_guess=None, order=None):
        if self.last_pos is not None:
            delta = (pos - self.last_pos) % N
            for k in range(0, self.max_order + 1):
                if len(self.deltas) >= k:
                    self.tables[k][self._context(k)][delta] += 1
            self.deltas.append(delta)
        self.last_pos = pos


class LagStrategy:
    """Lag and coverage: color repeats from 2 and 3 picks back, and cold colors."""

    label = "Lag and coverage"
    LAGS = (2, 3)
    WINDOW = 3

    def __init__(self, rng=None):
        self.history = deque(maxlen=self.WINDOW)
        self.lag_hits = {lag: 0 for lag in self.LAGS}
        self.lag_trials = {lag: 0 for lag in self.LAGS}
        self.cold_hits = 0.0
        self.cold_expected = 0.0

    def _absent(self):
        return [c for c in range(N) if c not in self.history]

    def predict(self, order):
        if len(self.history) < self.WINDOW:
            return list(UNIFORM)
        weights = [1.0] * N
        past = list(self.history)
        for lag in self.LAGS:
            rate = (self.lag_hits[lag] + 1.0) / (self.lag_trials[lag] + 4.0)
            target = past[-lag]
            for c in range(N):
                weights[c] *= rate / 0.25 if c == target else (1.0 - rate) / 0.75
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
    """Reaction to AI: how you respond after the AI hits or misses."""

    label = "Reaction to AI"

    def __init__(self, rng=None):
        self.last = None
        self.ai_last = None
        self.hit_last = None
        self.rep = {True: [0, 0], False: [0, 0]}
        self.adopt = [0, 0]

    @staticmethod
    def _rate(pair):
        return (pair[0] + 1.0) / (pair[1] + 4.0)

    def predict(self, order):
        if self.last is None or self.ai_last is None:
            return list(UNIFORM)
        r = self._rate(self.rep[self.hit_last])
        if self.hit_last:
            dist = [(1.0 - r) / (N - 1)] * N
            dist[self.last] = r
            return dist
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
    """Position habit: how likely you are to click the same screen spot again.

    Tracks the chance of repeating the same position after a run of 1, 2 or 3+
    clicks on it, and a decayed preference for the other positions. The result
    is mapped to colors through the current tile order.
    """

    label = "Position habit"

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
    """Color at position: how often each color is chosen when shown at each spot.

    For every tile on screen the model knows how often that exact pair of
    position and color was shown and how often it was chosen.
    """

    label = "Color at position"

    def __init__(self, rng=None):
        self.chosen = [[0] * N for _ in range(N)]
        self.shown = [[0] * N for _ in range(N)]

    def predict(self, order):
        scores = [
            (self.chosen[p][order[p]] + 1.0) / (self.shown[p][order[p]] + 4.0)
            for p in range(N)
        ]
        return to_color_dist(normalize(scores), order)

    def update(self, color, pos=None, ai_guess=None, order=None):
        for p in range(N):
            self.shown[p][order[p]] += 1
        self.chosen[pos][order[pos]] += 1


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
    scaled = normalize([w * f for w, f in zip(weights, factors)])
    return normalize([max(w, floor) for w in scaled])


class Ensemble:
    """Hedge style multiplicative weights over the active strategies."""

    def __init__(self, active=None, eta=ETA, floor=FLOOR, seed=None):
        self.active = tuple(active if active is not None else ACTIVE_STRATEGIES)
        self.eta = eta
        self.floor = floor
        self.seed = seed
        self.reset()

    def reset(self):
        self.rng = random.Random(self.seed)
        self.strategies = [STRATEGY_CLASSES[k](rng=self.rng) for k in self.active]
        self.weights = [1.0 / len(self.strategies)] * len(self.strategies)
        self.order = list(range(N))
        self.picks = []
        self.final = 0

    def begin_round(self, order):
        """order[position] is the color shown at that position this round."""
        self.order = list(order)
        dists = [s.predict(self.order) for s in self.strategies]
        self.picks = [argmax_random(d, self.rng) for d in dists]
        mixed = [sum(w * d[c] for w, d in zip(self.weights, dists)) for c in range(N)]
        self.final = argmax_random(mixed, self.rng)

    def resolve(self, pos):
        """Learn from the player's pick. Returns True when the AI guessed it."""
        color = self.order[pos]
        hit = self.final == color
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
    return [
        x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
        x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r,
        x1, y1 + r, x1, y1,
    ]


def random_order(previous=None):
    order = list(range(N))
    while True:
        random.shuffle(order)
        if order != previous:
            return order


class TileBoard(tk.Canvas):
    """The four colored tiles. Tiles slide to new positions when shuffled."""

    W, H = 680, 250
    TILE_W, TILE_H, GAP, TOP = 142, 150, 20, 42

    def __init__(self, master, on_click):
        super().__init__(master, width=self.W, height=self.H, bg=BG, highlightthickness=0)
        self.on_click = on_click
        self.locked = True
        self.job = None
        self.left = (self.W - (N * self.TILE_W + (N - 1) * self.GAP)) / 2
        self.pos_x = {}
        self.pos_y = {c: 0.0 for c in range(N)}
        self.rects = {}
        self.badges = {}
        for pos in range(N):
            cx = self.slot_x(pos) + self.TILE_W / 2
            self.create_text(
                cx, self.TOP + self.TILE_H + 28, text=str(pos + 1), fill=MUTED,
                font=(FONT, 14, "bold"),
            )
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
            self.badges[color] = self.create_text(
                x + self.TILE_W / 2, self.TOP - 18, text="", fill=FG,
                font=(FONT, 11, "bold"), tags=(tag,), state="hidden",
            )
            self.pos_x[color] = x
            self.tag_bind(tag, "<Button-1>", lambda e, c=color: self._click(c))
            self.tag_bind(tag, "<Enter>", lambda e, c=color: self._hover(c, True))
            self.tag_bind(tag, "<Leave>", lambda e, c=color: self._hover(c, False))

    def slot_x(self, pos):
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
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None

    def set_order(self, order, animate=False, on_done=None):
        """order[position] is the color shown there."""
        self.cancel()
        targets = {color: self.slot_x(pos) for pos, color in enumerate(order)}
        starts = dict(self.pos_x)
        steps = max(2, SHUFFLE_MS // 16) if animate else 1

        def frame(i):
            t = i / steps
            ease = t * t * (3 - 2 * t)
            for c in range(N):
                nx = starts[c] + (targets[c] - starts[c]) * ease
                ny = ((-1) ** c) * 26 * math.sin(math.pi * t) if animate else 0.0
                self.move(f"t{c}", nx - self.pos_x[c], ny - self.pos_y[c])
                self.pos_x[c], self.pos_y[c] = nx, ny
            if i < steps:
                self.job = self.after(16, lambda: frame(i + 1))
            else:
                self.job = None
                for c in range(N):
                    self.move(f"t{c}", targets[c] - self.pos_x[c], -self.pos_y[c])
                    self.pos_x[c], self.pos_y[c] = targets[c], 0.0
                if on_done:
                    on_done()

        frame(1)

    def highlight(self, picked, predicted):
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
    """Live strategy weights, drawn as bars."""

    W = 330
    ROW = 34

    def __init__(self, master, rows):
        super().__init__(
            master, width=self.W, height=14 + rows * self.ROW, bg=PANEL, highlightthickness=0
        )

    def render(self, items):
        self.delete("all")
        top = max(w for _, w in items)
        lead = top - min(w for _, w in items) > 0.005
        scale = max(top, 0.2)
        for i, (label, weight) in enumerate(items):
            y = 10 + i * self.ROW
            is_top = lead and weight == top
            self.create_text(
                14, y + 11, text=label, anchor="w", fill=FG if is_top else MUTED,
                font=(FONT, 10, "bold" if is_top else "normal"),
            )
            self.create_rectangle(160, y + 4, 276, y + 18, fill=PANEL2, outline="")
            self.create_rectangle(
                160, y + 4, 160 + 116 * weight / scale, y + 18,
                fill=GOLD if is_top else ACCENT, outline="",
            )
            self.create_text(
                self.W - 12, y + 11, text=f"{weight * 100:.0f}%", anchor="e", fill=FG,
                font=(FONT, 10, "bold"),
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
        self.phase = "locked"
        self.rounds = 0
        self.hits = 0
        self.jobs = []

        self._build()
        self._build_overlay()
        for i in range(N):
            self.bind(str(i + 1), lambda e, i=i: self.pick_position(i))
        self.bind("<Return>", self._restart_key)
        self.bind("<space>", self._restart_key)
        self.new_game()

    # ----- layout ---------------------------------------------------------
    def _stat(self, parent, title):
        box = tk.Frame(parent, bg=PANEL)
        box.pack(side="left", expand=True, fill="both", padx=6)
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
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="y", padx=(24, 0))

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

        stats = tk.Frame(left, bg=BG)
        stats.pack(fill="x")
        self.round_value, self.round_caption = self._stat(stats, "PROGRESS")
        self.acc_value, self.acc_caption = self._stat(stats, "AI ACCURACY")
        self.hits_value, self.hits_caption = self._stat(stats, "AI HITS")
        self.round_value.config(font=(FONT, 20, "bold"))

        self.progress = tk.Canvas(left, height=10, bg=BG, highlightthickness=0)
        self.progress.pack(fill="x", padx=6, pady=(10, 8))
        self.progress.bind("<Configure>", lambda e: self._draw_progress())

        card = tk.Frame(left, bg=PANEL)
        card.pack(fill="x", padx=6, pady=4)
        tk.Label(card, text="AI PREDICTION", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(
            pady=(10, 4)
        )
        row = tk.Frame(card, bg=PANEL)
        row.pack(pady=(0, 12))
        self.chip = tk.Label(
            row, text="?", width=4, height=2, bg=PANEL2, fg=FG, font=(FONT, 14, "bold")
        )
        self.chip.pack(side="left", padx=(0, 14))
        self.card_text = tk.Label(
            row, text="", bg=PANEL, fg=FG, font=(FONT, 15, "bold"), width=34, anchor="w"
        )
        self.card_text.pack(side="left")

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

        tk.Label(
            right, text="HOW THE AI THINKS", bg=BG, fg=FG, font=(FONT, 12, "bold")
        ).pack(anchor="w")
        tk.Label(
            right, text="Live strategy weights", bg=BG, fg=MUTED, font=(FONT, 9)
        ).pack(anchor="w", pady=(0, 8))
        self.brain_panel = BrainPanel(right, len(self.brain.strategies))
        self.brain_panel.pack()

    def _build_overlay(self):
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

    # ----- game flow ------------------------------------------------------
    def _after(self, ms, fn):
        self.jobs.append(self.after(ms, fn))

    def _cancel_jobs(self):
        for job in self.jobs:
            self.after_cancel(job)
        self.jobs = []
        self.board.cancel()

    def _restart_key(self, event=None):
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
        self.brain.begin_round(self.order)
        self.phase = "waiting"
        self.board.locked = False
        self._seal_card()
        self._refresh()

    def pick_color(self, color):
        self.pick_position(self.order.index(color))

    def pick_position(self, pos):
        if self.phase != "waiting":
            return
        self.phase = "reveal"
        self.board.locked = True
        color = self.order[pos]
        predicted = self.brain.final
        hit = self.brain.resolve(pos)
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
        self.brain.begin_round(self.order)
        self._seal_card()
        self.board.set_order(self.order, animate=True, on_done=self._ready)

    def _ready(self):
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
            weights = self.brain.weights
            top = max(range(len(weights)), key=lambda i: weights[i])
            note += f" Its most trusted strategy at the end: {self.brain.strategies[top].label}."
        self.over_note.config(text=note)
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self.overlay.lift()

    # ----- display --------------------------------------------------------
    def _draw_progress(self):
        self.progress.delete("all")
        width = self.progress.winfo_width()
        self.progress.create_rectangle(0, 0, width, 10, fill=PANEL2, outline="")
        self.progress.create_rectangle(
            0, 0, width * self.rounds / TOTAL_ROUNDS, 10, fill=ACCENT, outline=""
        )

    def _seal_card(self):
        self.chip.config(text="?", bg=PANEL2)
        self.card_text.config(text="Locked in. Make your move.", fg=FG)

    def _refresh(self):
        current = min(self.rounds + (1 if self.phase in ("waiting", "shuffling") else 0),
                      TOTAL_ROUNDS)
        current = max(current, 1)
        self.round_value.config(text=f"Round {current} / {TOTAL_ROUNDS}")
        left = TOTAL_ROUNDS - self.rounds
        self.round_caption.config(text=f"{left} round{'s' if left != 1 else ''} left")
        if self.rounds:
            accuracy = self.hits / self.rounds * 100
            under = self.hits / self.rounds < WIN_THRESHOLD
            self.acc_value.config(text=f"{accuracy:.1f}%", fg=GOOD if under else BAD)
        else:
            self.acc_value.config(text="--", fg=FG)
        self.acc_caption.config(text=f"must finish under {WIN_THRESHOLD * 100:g}%")
        self.hits_value.config(text=str(self.hits), fg=BAD if self.hits > MAX_AI_HITS else FG)
        self.hits_caption.config(
            text="defeat locked in" if self.hits > MAX_AI_HITS else f"limit {MAX_AI_HITS}",
            fg=BAD if self.hits > MAX_AI_HITS else MUTED,
        )
        self._draw_progress()
        self.brain_panel.render(
            [(s.label, w) for s, w in zip(self.brain.strategies, self.brain.weights)]
        )


if __name__ == "__main__":
    App().mainloop()