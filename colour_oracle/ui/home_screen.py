"""Beginscherm: titel, doel van het spel, taalkeuze, een startknop en een verwijzing voor uitleg."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"math", "tkinter"}

import math
import tkinter as tk

from colour_oracle.config import CREATOR_NAME, TOTAL_ROUNDS, WIN_THRESHOLD
from colour_oracle.constants import COLOURS, N, NAMES
from colour_oracle.i18n import get_language, tr
from colour_oracle.ui.drawing import rounded_points
from colour_oracle.ui.theme import ACCENT, BG, FG, FONT, GOLD, MUTED, PANEL, PANEL2


class HomeScreen(tk.Frame):
    """Beginscherm: titel, doel van het spel, taalkeuze, een startknop en een verwijzing voor uitleg."""

    TILE = 74    # zijde van elk decoratief kleurvlak
    GAP = 16     # ruimte tussen de kleurvlakken

    def __init__(self, master, on_start, on_language):
        super().__init__(master, bg=BG)
        self.on_start = on_start
        self.on_language = on_language
        self.job = None          # lopende animatiestap
        self.tick = 0
        self.offsets = [0.0] * N  # huidige verticale afwijking per kleurvlak

        card = tk.Frame(self, bg=BG)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Vier kleurvlakken die zachtjes op en neer zweven
        width = N * self.TILE + (N - 1) * self.GAP
        self.canvas = tk.Canvas(
            card, width=width, height=self.TILE + 40, bg=BG, highlightthickness=0
        )
        self.canvas.pack(pady=(0, 6))
        self.tiles = []
        for i, name in enumerate(NAMES):
            x = i * (self.TILE + self.GAP)
            fill = COLOURS[name]
            self.tiles.append(self.canvas.create_polygon(
                rounded_points(x, 20, x + self.TILE, 20 + self.TILE, 18),
                smooth=True, fill=fill, outline=fill,
            ))

        # De titel: elke letter in een eigen kleur uit het kleurenpalet
        title = tk.Frame(card, bg=BG)
        title.pack()
        palette = list(COLOURS.values())
        shade = 0
        for char in "Colour Oracle":
            if char == " ":
                tk.Label(title, text=" ", bg=BG, font=(FONT, 40, "bold")).pack(side="left")
                continue
            tk.Label(
                title, text=char, bg=BG, fg=palette[shade % N], font=(FONT, 60, "bold")
            ).pack(side="left")
            shade += 1
        self.tagline = tk.Label(card, text="", bg=BG, fg=FG, font=(FONT, 18))
        self.tagline.pack(pady=(2, 0))

        # Kaart met het doel van het spel
        mission = tk.Frame(card, bg=PANEL)
        mission.pack(pady=(24, 0), fill="x")
        self.mission_title = tk.Label(
            mission, text="", bg=PANEL, fg=GOLD, font=(FONT, 10, "bold")
        )
        self.mission_title.pack(pady=(16, 6))
        self.mission_text = tk.Label(
            mission, text="", bg=PANEL, fg=FG, font=(FONT, 13), justify="center", padx=40,
        )
        self.mission_text.pack(pady=(0, 18))

        # Startknop met hover-effect
        self.button = tk.Label(
            card, text="", bg=ACCENT, fg="#ffffff", font=(FONT, 20, "bold"),
            padx=80, pady=14, cursor="hand2",
        )
        self.button.pack(pady=(26, 8))
        self.button.bind("<Button-1>", lambda e: self.on_start())
        self.button.bind("<Enter>", lambda e: self.button.config(bg="#9a8dff"))
        self.button.bind("<Leave>", lambda e: self.button.config(bg=ACCENT))
        self.enter_hint = tk.Label(card, text="", bg=BG, fg=MUTED, font=(FONT, 10))
        self.enter_hint.pack()

        # Verwijzing onderaan het scherm
        self.footer = tk.Label(self, text="", bg=BG, fg=MUTED, font=(FONT, 11))
        self.footer.place(relx=0.5, rely=1.0, y=-28, anchor="s")

        # Taalkeuze rechtsboven
        switch = tk.Frame(self, bg=BG)
        switch.place(relx=1.0, x=-24, y=20, anchor="ne")
        self.language_buttons = {}
        for code in ("nl", "en"):
            label = tk.Label(
                switch, text=code.upper(), font=(FONT, 11, "bold"), padx=12, pady=5,
                cursor="hand2",
            )
            label.pack(side="left", padx=2)
            label.bind("<Button-1>", lambda e, c=code: self.on_language(c))
            self.language_buttons[code] = label

        self.relabel()

    def relabel(self):
        # Zet alle teksten in de huidige taal en markeer de gekozen taal
        self.tagline.config(text=tr("tagline"))
        self.mission_title.config(text=tr("mission_title"))
        self.mission_text.config(
            text=tr("mission", pct=f"{WIN_THRESHOLD * 100:g}", rounds=TOTAL_ROUNDS)
        )
        self.button.config(text=tr("play"))
        self.enter_hint.config(text=tr("press_enter"))
        self.footer.config(text=tr("footer", name=CREATOR_NAME))
        for code, label in self.language_buttons.items():
            active = code == get_language()
            label.config(bg=ACCENT if active else PANEL2, fg="#ffffff" if active else MUTED)

    def start(self):
        # Start de zweefanimatie
        self.stop()
        self.tick = 0
        self._animate()

    def stop(self):
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None

    def _animate(self):
        # Elk kleurvlak zweeft met een eigen fase, zodat ze een golf vormen
        for i, item in enumerate(self.tiles):
            dy = math.sin(self.tick * 0.12 + i * 0.9) * 8
            self.canvas.move(item, 0, dy - self.offsets[i])
            self.offsets[i] = dy
        self.tick += 1
        self.job = self.after(33, self._animate)
