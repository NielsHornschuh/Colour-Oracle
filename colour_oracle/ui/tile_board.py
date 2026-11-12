"""De vier gekleurde tegels. Bij het schudden schuiven de tegels naar hun nieuwe plek."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"math", "tkinter"}

import math
import tkinter as tk

from colour_oracle.config import SHUFFLE_MS
from colour_oracle.constants import COLOURS, N, NAMES
from colour_oracle.i18n import colour_name, tr
from colour_oracle.ui.drawing import rounded_points
from colour_oracle.ui.theme import ACCENT, BAD, BG, FG, FONT, MUTED


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
        self.names = {}          # tekst met de kleurnaam op elke tegel
        # Cijfers 1 tot 4 onder de vaste posities
        for pos in range(N):
            cx = self.slot_x(pos) + self.TILE_W / 2
            self.create_text(
                cx, self.TOP + self.TILE_H + 28, text=str(pos + 1), fill=MUTED,
                font=(FONT, 14, "bold"),
            )
        # Elke tegel krijgt een eigen tag, zodat alle onderdelen samen bewegen
        for colour in range(N):
            x = self.slot_x(colour)
            tag = f"t{colour}"
            fill = COLOURS[NAMES[colour]]
            self.rects[colour] = self.create_polygon(
                rounded_points(x, self.TOP, x + self.TILE_W, self.TOP + self.TILE_H, 24),
                smooth=True, fill=fill, outline=fill, width=4, tags=(tag,),
            )
            self.names[colour] = self.create_text(
                x + self.TILE_W / 2, self.TOP + self.TILE_H / 2, text=colour_name(colour),
                fill="#10131c", font=(FONT, 17, "bold"), tags=(tag,),
            )
            # Label boven de tegel (YOU, AI of YOU + AI), eerst verborgen
            self.badges[colour] = self.create_text(
                x + self.TILE_W / 2, self.TOP - 18, text="", fill=FG,
                font=(FONT, 11, "bold"), tags=(tag,), state="hidden",
            )
            self.pos_x[colour] = x
            self.tag_bind(tag, "<Button-1>", lambda e, c=colour: self._click(c))
            self.tag_bind(tag, "<Enter>", lambda e, c=colour: self._hover(c, True))
            self.tag_bind(tag, "<Leave>", lambda e, c=colour: self._hover(c, False))

    def relabel(self):
        # Pas de kleurnamen aan na een taalwissel
        for colour in range(N):
            self.itemconfig(self.names[colour], text=colour_name(colour))

    def slot_x(self, pos):
        # x-coördinaat van de linkerrand van een positie
        return self.left + pos * (self.TILE_W + self.GAP)

    def _click(self, colour):
        if not self.locked:
            self.on_click(colour)

    def _hover(self, colour, inside):
        if self.locked:
            return
        self.itemconfig(
            self.rects[colour], outline="#ffffff" if inside else COLOURS[NAMES[colour]]
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
        targets = {colour: self.slot_x(pos) for pos, colour in enumerate(order)}
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
            self.itemconfig(self.rects[c], outline=COLOURS[NAMES[c]], width=4, dash="")
            self.itemconfig(self.badges[c], text="", state="hidden")
        if picked == predicted:
            self.itemconfig(self.rects[picked], outline="#ffffff", width=6)
            self.itemconfig(self.badges[picked], text=tr("you_ai"), fill=BAD, state="normal")
            return
        self.itemconfig(self.rects[picked], outline="#ffffff", width=6)
        self.itemconfig(self.badges[picked], text=tr("you"), fill=FG, state="normal")
        self.itemconfig(self.rects[predicted], outline="#ffffff", width=4, dash=(8, 6))
        self.itemconfig(self.badges[predicted], text=tr("ai"), fill=ACCENT, state="normal")

    def clear_highlight(self):
        for c in range(N):
            self.itemconfig(self.rects[c], outline=COLOURS[NAMES[c]], width=4, dash="")
            self.itemconfig(self.badges[c], text="", state="hidden")
