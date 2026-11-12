"""Het eindscherm met de uitslag van een spel."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"tkinter"}

import tkinter as tk

from colour_oracle.config import MAX_AI_HITS, TOTAL_ROUNDS, WIN_THRESHOLD
from colour_oracle.i18n import tr
from colour_oracle.ui.theme import ACCENT, BAD, BG, FG, FONT, GOOD, MUTED, PANEL


class GameOverOverlay(tk.Frame):
    """Scherm voor overwinning of nederlaag. Bedekt het hele venster."""

    def __init__(self, master, on_play_again, on_menu):
        super().__init__(master, bg=BG)
        card = tk.Frame(self, bg=PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center")
        self.title_label = tk.Label(card, text="", bg=PANEL, font=(FONT, 56, "bold"))
        self.title_label.pack(padx=70, pady=(34, 6))
        self.message = tk.Label(
            card, text="", bg=PANEL, fg=FG, font=(FONT, 16), wraplength=520
        )
        self.message.pack(padx=40)
        self.stats = tk.Label(card, text="", bg=PANEL, fg=MUTED, font=(FONT, 13))
        self.stats.pack(pady=(18, 2))
        self.note = tk.Label(
            card, text="", bg=PANEL, fg=MUTED, font=(FONT, 11), wraplength=520
        )
        self.note.pack(padx=40)
        self.play_button = tk.Label(
            card, text="", bg=ACCENT, fg="#ffffff", font=(FONT, 18, "bold"),
            padx=54, pady=14, cursor="hand2",
        )
        self.play_button.pack(pady=(26, 10))
        self.play_button.bind("<Button-1>", lambda e: on_play_again())
        self.play_button.bind("<Enter>", lambda e: self.play_button.config(bg="#9a8dff"))
        self.play_button.bind("<Leave>", lambda e: self.play_button.config(bg=ACCENT))
        # Terug naar het beginscherm
        self.menu_button = tk.Label(
            card, text="", bg=PANEL, fg=MUTED, font=(FONT, 11), cursor="hand2"
        )
        self.menu_button.pack(pady=(0, 30))
        self.menu_button.bind("<Button-1>", lambda e: on_menu())

    def relabel(self):
        # Zet de knoppen in de huidige taal. De rest wordt gevuld bij show().
        self.play_button.config(text=tr("play_again"))
        self.menu_button.config(text=tr("back_menu"))

    def show(self, hits, brain):
        """Vul het scherm met de uitslag van dit spel en toon het."""
        accuracy = hits / TOTAL_ROUNDS * 100
        if hits <= MAX_AI_HITS:
            self.title_label.config(text=tr("victory"), fg=GOOD)
            self.message.config(text=tr("win_msg"))
        else:
            self.title_label.config(text=tr("defeat"), fg=BAD)
            self.message.config(text=tr("lose_msg"))
        word = tr("word_one") if hits == 1 else tr("word_other")
        self.stats.config(
            text=tr("final_stats", pct=accuracy, hits=hits, word=word, rounds=TOTAL_ROUNDS)
        )
        note = tr("win_note", pct=f"{WIN_THRESHOLD * 100:g}", max=MAX_AI_HITS)
        if hits > MAX_AI_HITS:
            # Bij een nederlaag: noem de strategie met het hoogste gewicht
            weights = brain.weights
            top = max(range(len(weights)), key=lambda i: weights[i])
            note += tr("top_strategy", label=brain.strategies[top].label)
        self.note.config(text=note)
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.lift()

    def hide(self):
        self.place_forget()
