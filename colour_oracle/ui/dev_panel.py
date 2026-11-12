"""Het dev screen: strategieën met gewichten en een schakelaar voor de AI-voorspelling."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"tkinter"}

import tkinter as tk

from colour_oracle.engine.strategies.reaction import ReactionStrategy
from colour_oracle.i18n import tr
from colour_oracle.ui.brain_panel import BrainPanel
from colour_oracle.ui.theme import BG, FG, FONT, GOOD, MUTED, PANEL, PANEL2


class DevPanel(tk.Frame):
    """Zwevend dev screen rechtsboven op het hoofdvenster.

    Het paneel wordt met place() over het spel gelegd, dus de rest verschuift niet.
    Het toont altijd de strategieën met hun gewichten en heeft één schakelaar voor
    de voorspelling van de AI voor de keuze. Niets hier verandert hoe de AI voorspelt.
    """

    def __init__(self, master, brain, on_prediction_toggle):
        super().__init__(master, bg=PANEL, padx=16, pady=14)
        self.brain = brain
        self.on_prediction_toggle = on_prediction_toggle
        self.is_open = False          # staat het paneel open
        self.show_prediction = False  # schakelaar: AI-voorspelling tonen voor de keuze

        self.title_label = tk.Label(self, text="", bg=PANEL, fg=FG, font=(FONT, 12, "bold"))
        self.title_label.pack(anchor="w")
        # Vaste hoogte van twee regels, zodat het paneel in elke taal even groot blijft
        self.note = tk.Label(
            self, text="", bg=PANEL, fg=MUTED, font=(FONT, 9), wraplength=BrainPanel.W,
            justify="left", anchor="nw", height=2,
        )
        self.note.pack(anchor="w", fill="x", pady=(0, 10))
        self.prediction_name, self.prediction_state = self._toggle(
            "", self._toggle_prediction
        )
        # De strategieën en gewichten staan er altijd, dus het paneel heeft een vaste grootte
        self.weights_label = tk.Label(self, text="", bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.weights_label.pack(anchor="w", pady=(10, 8))
        sub_rows = 3 if "reaction" in brain.active else 0   # de drie vertrouwensbalken
        self.brain_panel = BrainPanel(self, len(brain.strategies), sub_rows)
        self.brain_panel.pack()

    def _toggle(self, text, command):
        # Een klikbare rij met een AAN/UIT-label. Geeft het naamlabel en het statuslabel terug.
        row = tk.Frame(self, bg=PANEL2, cursor="hand2")
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
        return name, state

    def _paint_toggle(self):
        # Kleur en tekst van het statuslabel volgen de stand van de schakelaar
        on = self.show_prediction
        self.prediction_state.config(
            text=tr("on") if on else tr("off"), bg=GOOD if on else BG,
            fg="#10131c" if on else MUTED,
        )

    def _toggle_prediction(self):
        self.show_prediction = not self.show_prediction
        self._paint_toggle()
        self.on_prediction_toggle()

    def relabel(self):
        # Zet alle teksten in de huidige taal
        self.title_label.config(text=tr("dev_title"))
        self.note.config(text=tr("dev_note"))
        self.prediction_name.config(text=tr("dev_prediction"))
        self.weights_label.config(text=tr("dev_weights"))
        self._paint_toggle()

    def toggle(self):
        # Ctrl+Shift+D opent of sluit het zijmenu
        self.is_open = not self.is_open
        if self.is_open:
            self.place(relx=1.0, x=-16, y=16, anchor="ne")
            self.lift()
            self._render()
        else:
            self.place_forget()

    def refresh(self):
        # Werk de balken bij, maar alleen als het paneel open staat
        if self.is_open:
            self._render()

    def raise_if_open(self):
        # Het paneel blijft bereikbaar boven het beginscherm en het eindscherm
        if self.is_open:
            self.lift()

    def _render(self):
        items = [(s.label, w) for s, w in zip(self.brain.strategies, self.brain.weights)]
        # Onder de Dodge & Reaction Tracker staat het vertrouwen per zichtbaar signaal
        subs, after = (), None
        for i, strategy in enumerate(self.brain.strategies):
            if isinstance(strategy, ReactionStrategy):
                trust = strategy.trust
                subs = [
                    (tr("trust_accuracy"), trust["accuracy"]),
                    (tr("trust_ai"), trust["ai_result"]),
                    (tr("trust_move"), trust["movement"]),
                ]
                after = i
        self.brain_panel.render(items, subs, after)
