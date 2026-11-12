"""Het hoofdvenster: bouwt het scherm op en regelt het verloop van het spel."""

# Lazy import (Python 3.15+), zie colour_oracle/__init__.py
__lazy_modules__ = {"tkinter"}

import tkinter as tk

from colour_oracle.config import MAX_AI_HITS, REVEAL_MS, TOTAL_ROUNDS, WIN_THRESHOLD
from colour_oracle.constants import COLOURS, N, NAMES
from colour_oracle.engine.ensemble import Ensemble
from colour_oracle.engine.helpers import random_order
from colour_oracle.i18n import colour_name, set_language, tr
from colour_oracle.ui.dev_panel import DevPanel
from colour_oracle.ui.game_over import GameOverOverlay
from colour_oracle.ui.home_screen import HomeScreen
from colour_oracle.ui.theme import ACCENT, BAD, BG, FG, FONT, GOOD, MUTED, PANEL, PANEL2
from colour_oracle.ui.tile_board import TileBoard


class App(tk.Tk):
    """Het hoofdvenster: bouwt het scherm op en regelt het verloop van het spel."""

    def __init__(self):
        super().__init__()
        self.title("Colour Oracle")
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

        self._build()
        # Het beginscherm en het eindscherm bedekken het hele venster
        self.home = HomeScreen(self, self.start_game, self.set_language)
        self.game_over = GameOverOverlay(self, on_play_again=self.new_game, on_menu=self.show_home)
        # Toetsen 1 tot 4 kiezen een schermpositie
        for i in range(N):
            self.bind(str(i + 1), lambda e, i=i: self.pick_position(i))
        self.bind("<Control-Shift-D>", self._toggle_dev)
        self.bind("<Control-Shift-d>", self._toggle_dev)
        self.bind("<Return>", self._restart_key)
        self.bind("<space>", self._restart_key)
        self._apply_language()
        self.show_home()

    # ----- indeling -------------------------------------------------------
    def _stat(self, parent, column):
        # Eén statistiekvak met titel, waarde en onderschrift. De grid met
        # uniform kolommen houdt alle vakken even breed en even hoog.
        box = tk.Frame(parent, bg=PANEL)
        box.grid(row=0, column=column, sticky="nsew", padx=6)
        title = tk.Label(box, text="", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold"))
        title.pack(pady=(10, 0))
        value = tk.Label(box, text="", bg=PANEL, fg=FG, font=(FONT, 24, "bold"))
        value.pack()
        caption = tk.Label(box, text="", bg=PANEL, fg=MUTED, font=(FONT, 9))
        caption.pack(pady=(0, 10))
        return title, value, caption

    def _build(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        # Het dev screen zweeft over het venster en wordt pas getoond na Ctrl+Shift+D
        self.dev_panel = DevPanel(self, self.brain, self._on_prediction_toggle)

        tk.Label(
            left, text="Colour Oracle", bg=BG, fg=FG, font=(FONT, 30, "bold")
        ).pack()
        self.subtitle = tk.Label(left, text="", bg=BG, fg=MUTED, font=(FONT, 11))
        self.subtitle.pack(pady=(0, 12))

        # Drie statistiekvakken: voortgang, nauwkeurigheid en treffers
        stats = tk.Frame(left, bg=BG)
        stats.pack(fill="x")
        for column in range(3):
            stats.columnconfigure(column, weight=1, uniform="stat")
        self.round_title, self.round_value, self.round_caption = self._stat(stats, 0)
        self.acc_title, self.acc_value, self.acc_caption = self._stat(stats, 1)
        self.hits_title, self.hits_value, self.hits_caption = self._stat(stats, 2)

        # Voortgangsbalk, tekent zichzelf opnieuw bij elke formaatwijziging
        self.progress = tk.Canvas(left, height=10, bg=BG, highlightthickness=0)
        self.progress.pack(fill="x", padx=6, pady=(10, 8))
        self.progress.bind("<Configure>", lambda e: self._draw_progress())

        # Kaart met de voorspelling van de AI
        card = tk.Frame(left, bg=PANEL)
        card.pack(fill="x", padx=6, pady=4)
        self.prediction_title = tk.Label(
            card, text="", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")
        )
        self.prediction_title.pack(pady=(10, 4))
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

        self.board = TileBoard(left, self.pick_colour)
        self.board.pack(pady=(10, 0))
        self.hint_label = tk.Label(left, text="", bg=BG, fg=MUTED, font=(FONT, 10))
        self.hint_label.pack()

        self.restart_button = restart = tk.Label(
            left, text="", bg=PANEL2, fg=MUTED, font=(FONT, 10, "bold"),
            padx=16, pady=6, cursor="hand2",
        )
        restart.pack(side="bottom", pady=(8, 0))
        restart.bind("<Button-1>", lambda e: self.new_game())

    # ----- taal -----------------------------------------------------------
    def set_language(self, code):
        # Wissel de taal en werk alle zichtbare teksten bij
        set_language(code)
        self._apply_language()

    def _apply_language(self):
        # Vaste teksten
        self.subtitle.config(
            text=tr("subtitle", pct=f"{WIN_THRESHOLD * 100:g}", rounds=TOTAL_ROUNDS)
        )
        self.round_title.config(text=tr("progress"))
        self.acc_title.config(text=tr("ai_accuracy"))
        self.hits_title.config(text=tr("ai_hits"))
        self.prediction_title.config(text=tr("ai_prediction"))
        self.hint_label.config(text=tr("hint"))
        self.restart_button.config(text=tr("restart"))
        self.dev_panel.relabel()
        self.game_over.relabel()
        self.board.relabel()
        self.home.relabel()
        # Teksten die van de spelstand afhangen
        if self.phase in ("locked", "home", "waiting", "shuffling"):
            self._seal_card()
        self._refresh()

    # ----- dev screen -----------------------------------------------------
    def _toggle_dev(self, event=None):
        # Ctrl+Shift+D opent of sluit het zijmenu
        self.dev_panel.toggle()

    def _on_prediction_toggle(self):
        # Tijdens het wachten op een keuze werkt de kaart direct bij
        if self.phase in ("waiting", "shuffling"):
            self._seal_card()

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
        # Enter of spatie start een nieuw spel op het eindscherm en op het beginscherm
        if self.phase == "over":
            self.new_game()
        elif self.phase == "home":
            self.start_game()

    def show_home(self):
        # Toon het beginscherm. Het spel staat vergrendeld tot de speler start.
        self._cancel_jobs()
        self.game_over.hide()
        self.phase = "home"
        self.board.locked = True
        self.home.place(x=0, y=0, relwidth=1, relheight=1)
        self.home.lift()
        self.home.start()
        self.dev_panel.raise_if_open()

    def start_game(self):
        self.home.stop()
        self.home.place_forget()
        self.new_game()

    def new_game(self):
        self._cancel_jobs()
        self.game_over.hide()
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

    def pick_colour(self, colour):
        # Een klik op een tegel wordt omgezet naar de schermpositie van die kleur
        self.pick_position(self.order.index(colour))

    def pick_position(self, pos):
        if self.phase != "waiting":
            return
        self.phase = "reveal"
        self.board.locked = True
        colour = self.order[pos]
        predicted = self.brain.final   # de gok stond al vast voor deze keuze
        hit = self.brain.resolve(pos)  # pas nu leert de AI van de keuze
        self.rounds += 1
        self.hits += int(hit)
        self.board.highlight(colour, predicted)
        self.chip.config(text="", bg=COLOURS[NAMES[predicted]])
        self.card_text.config(
            text=tr(
                "ai_predicted", colour=colour_name(predicted),
                result=tr("hit") if hit else tr("miss"),
            ),
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
        self.game_over.show(self.hits, self.brain)
        self.dev_panel.raise_if_open()

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
        if self.dev_panel.show_prediction:
            predicted = self.brain.final
            self.chip.config(text="", bg=COLOURS[NAMES[predicted]])
            self.card_text.config(text=tr("locked_in", colour=colour_name(predicted)), fg=FG)
            return
        self.chip.config(text="?", bg=PANEL2)
        self.card_text.config(text=tr("sealed"), fg=FG)

    def _refresh(self):
        # Rondeteller: tijdens het wachten en schudden telt de lopende ronde mee
        current = min(self.rounds + (1 if self.phase in ("waiting", "shuffling") else 0),
                      TOTAL_ROUNDS)
        current = max(current, 1)
        self.round_value.config(text=tr("round_value", n=current, total=TOTAL_ROUNDS))
        left = TOTAL_ROUNDS - self.rounds
        self.round_caption.config(
            text=tr("left_one" if left == 1 else "left_other", n=left)
        )
        # Nauwkeurigheid: groen onder de drempel, rood erboven
        if self.rounds:
            accuracy = self.hits / self.rounds * 100
            under = self.hits / self.rounds < WIN_THRESHOLD
            self.acc_value.config(text=f"{accuracy:.1f}%", fg=GOOD if under else BAD)
        else:
            self.acc_value.config(text="--", fg=FG)
        self.acc_caption.config(text=tr("must_finish", pct=f"{WIN_THRESHOLD * 100:g}"))
        # Zodra de treffers boven het maximum uitkomen, staat de nederlaag vast
        self.hits_value.config(text=str(self.hits), fg=BAD if self.hits > MAX_AI_HITS else FG)
        self.hits_caption.config(
            text=tr("defeat_locked") if self.hits > MAX_AI_HITS else tr("limit", n=MAX_AI_HITS),
            fg=BAD if self.hits > MAX_AI_HITS else MUTED,
        )
        self._draw_progress()
        self.dev_panel.refresh()
