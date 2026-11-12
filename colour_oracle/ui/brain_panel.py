"""Live gewichten van de strategieën, getekend als balken."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"tkinter"}

import tkinter as tk

from colour_oracle.ui.theme import ACCENT, FG, FONT, GOLD, GOOD, MUTED, PANEL, PANEL2


class BrainPanel(tk.Canvas):
    """Live gewichten van de strategieën. Label en percentage boven, de balk eronder.

    De lange strategienamen hebben de volle paneelbreedte nodig, daarom heeft
    elke rij twee regels in plaats van een labelkolom naast de balk. Onder één
    gekozen rij staan kleine extra balken, zoals de drie vertrouwenswaarden van
    de Dodge & Reaction Tracker. Die extra rijen hebben een vaste hoogte, dus
    het paneel verandert nooit van grootte.
    """

    W = 330
    ROW = 44
    SUB = 20      # hoogte van een kleine extra balk
    PAD = 14

    def __init__(self, master, rows, sub_rows=0):
        super().__init__(
            master, width=self.W, height=self.PAD + rows * self.ROW + sub_rows * self.SUB + (6 if sub_rows else 0),
            bg=PANEL, highlightthickness=0,
        )

    def render(self, items, subs=(), sub_after=None):
        """items is een lijst van (label, gewicht). De hoogste krijgt een gouden balk.

        Subs is een lijst van (label, waarde van 0 tot 1). Die staan onder rij sub_after.
        """
        self.delete("all")
        top = max(w for _, w in items)
        lead = top - min(w for _, w in items) > 0.005  # alleen markeren bij een duidelijk verschil
        scale = max(top, 0.2)                          # de balken schalen mee met het hoogste gewicht
        bar_left, bar_right = self.PAD, self.W - self.PAD
        bar_width = bar_right - bar_left
        y = 10
        for i, (label, weight) in enumerate(items):
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
            y += self.ROW
            if i == sub_after:
                for sub_label, value in subs:
                    self._draw_sub(y, sub_label, value)
                    y += self.SUB
                y += 6   # een kleine ruimte voor de volgende rij

    def _draw_sub(self, y, label, value):
        # Eén kleine balk. Groen betekent: dit signaal heeft aantoonbare invloed op de speler.
        left = self.PAD + 14
        bar_left, bar_right = left + 112, self.W - self.PAD - 40
        self.create_text(left, y + 6, text=label, anchor="w", fill=MUTED, font=(FONT, 9))
        self.create_rectangle(bar_left, y + 2, bar_right, y + 10, fill=PANEL2, outline="")
        if value > 0:
            self.create_rectangle(
                bar_left, y + 2, bar_left + (bar_right - bar_left) * value, y + 10,
                fill=GOOD if value >= 0.5 else ACCENT, outline="",
            )
        self.create_text(
            self.W - self.PAD, y + 6, text=f"{value * 100:.0f}%", anchor="e", fill=MUTED,
            font=(FONT, 9),
        )
