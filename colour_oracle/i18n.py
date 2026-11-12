"""Alle zichtbare teksten in het Nederlands en het Engels, en de taalkeuze."""

from colour_oracle.config import DEFAULT_LANGUAGE
from colour_oracle.constants import NAMES


# Huidige taal. Lees die altijd met get_language() en niet met een directe import
# van LANG: een import kopieert de waarde en ziet een taalwissel niet.
LANG = DEFAULT_LANGUAGE

# Alle zichtbare teksten staan hier, per taal. Met {naam} worden waarden ingevuld.
TEXT = {
    "en": {
        "subtitle": "Keep the AI under {pct}% accuracy for {rounds} rounds. Tiles shuffle after every round.",
        "progress": "PROGRESS", "ai_accuracy": "AI ACCURACY", "ai_hits": "AI HITS",
        "round_value": "Round {n} / {total}",
        "left_one": "{n} round left", "left_other": "{n} rounds left",
        "must_finish": "must finish under {pct}%",
        "limit": "limit {n}", "defeat_locked": "defeat locked in",
        "ai_prediction": "AI PREDICTION",
        "sealed": "Locked in. Make your move.",
        "locked_in": "AI has locked in {colour}.",
        "ai_predicted": "AI predicted {colour}.  {result}",
        "hit": "HIT", "miss": "MISS",
        "you_ai": "YOU + AI", "you": "YOU", "ai": "AI",
        "hint": "Click a tile or press 1 to 4. Keys follow the screen position.",
        "restart": "Restart",
        "victory": "VICTORY!", "defeat": "DEFEAT!",
        "win_msg": "You successfully outsmarted the AI's pattern recognition.",
        "lose_msg": "The AI figured out your patterns.",
        "final_stats": "Final AI accuracy: {pct:.1f}%   ({hits} {word} in {rounds} rounds)",
        "word_one": "hit", "word_other": "hits",
        "win_note": "To win, the AI had to stay under {pct}% ({max} hits or fewer).",
        "top_strategy": " Its most trusted strategy at the end: {label}.",
        "play_again": "PLAY AGAIN", "back_menu": "Back to menu",
        "tagline": "Can you outsmart the AI?",
        "mission_title": "YOUR MISSION",
        "mission": "The AI tries to guess which tile you will pick, before you pick it.\nKeep its accuracy under {pct}% for {rounds} rounds.\nThe tiles shuffle after every round. Be unpredictable.",
        "play": "PLAY", "press_enter": "or press Enter",
        "footer": "Want to know more? Ask {name} for an explanation.",
        "dev_title": "DEV SCREEN",
        "dev_note": "Showcase only. Nothing here changes how the AI predicts.",
        "dev_prediction": "Show AI prediction before pick",
        "dev_weights": "Live strategy weights",
        "on": "ON", "off": "OFF",
        "trust_accuracy": "Accuracy readout", "trust_ai": "AI hit or miss", "trust_move": "Tile movement",
        "colour_Red": "Red", "colour_Blue": "Blue", "colour_Green": "Green", "colour_Yellow": "Yellow",
    },
    "nl": {
        "subtitle": "Houd de AI onder {pct}% nauwkeurigheid gedurende {rounds} rondes. De tegels schudden na elke ronde.",
        "progress": "VOORTGANG", "ai_accuracy": "AI-NAUWKEURIGHEID", "ai_hits": "AI-TREFFERS",
        "round_value": "Ronde {n} / {total}",
        "left_one": "nog {n} ronde", "left_other": "nog {n} rondes",
        "must_finish": "moet onder {pct}% eindigen",
        "limit": "limiet {n}", "defeat_locked": "verlies staat vast",
        "ai_prediction": "AI-VOORSPELLING",
        "sealed": "Vastgelegd. Doe je zet.",
        "locked_in": "De AI heeft {colour} vastgelegd.",
        "ai_predicted": "De AI voorspelde {colour}.  {result}",
        "hit": "RAAK", "miss": "MIS",
        "you_ai": "JIJ + AI", "you": "JIJ", "ai": "AI",
        "hint": "Klik op een tegel of druk op 1 tot 4. De toetsen volgen de positie op het scherm.",
        "restart": "Opnieuw",
        "victory": "GEWONNEN!", "defeat": "VERLOREN!",
        "win_msg": "Je bent de patroonherkenning van de AI te slim af geweest.",
        "lose_msg": "De AI heeft je patronen doorzien.",
        "final_stats": "Eindnauwkeurigheid AI: {pct:.1f}%   ({hits} {word} in {rounds} rondes)",
        "word_one": "treffer", "word_other": "treffers",
        "win_note": "Om te winnen moest de AI onder de {pct}% blijven (maximaal {max} treffers).",
        "top_strategy": " Meest vertrouwde strategie aan het eind: {label}.",
        "play_again": "OPNIEUW SPELEN", "back_menu": "Terug naar het menu",
        "tagline": "Kun jij de AI te slim af zijn?",
        "mission_title": "JOUW MISSIE",
        "mission": "De AI probeert te raden welke tegel jij kiest, nog voordat jij kiest.\nHoud de nauwkeurigheid onder de {pct}% gedurende {rounds} rondes.\nDe tegels schudden na elke ronde. Wees onvoorspelbaar.",
        "play": "SPELEN", "press_enter": "of druk op Enter",
        "footer": "Wil je meer weten? Vraag het aan {name}.",
        "dev_title": "DEV-SCHERM",
        "dev_note": "Alleen voor de showcase. Niets hier verandert hoe de AI voorspelt.",
        "dev_prediction": "Toon AI-voorspelling voor de keuze",
        "dev_weights": "Live strategiegewichten",
        "on": "AAN", "off": "UIT",
        "trust_accuracy": "Nauwkeurigheid", "trust_ai": "AI raak of mis", "trust_move": "Tegelbeweging",
        "colour_Red": "Rood", "colour_Blue": "Blauw", "colour_Green": "Groen", "colour_Yellow": "Geel",
    },
}


def set_language(code):
    """Wissel de taal van alle teksten. Onbekende codes worden genegeerd."""
    global LANG
    if code in TEXT:
        LANG = code


def get_language():
    """Geef de code van de huidige taal terug, "nl" of "en"."""
    return LANG


def tr(key, **values):
    """Geef de tekst bij `key` in de huidige taal, met de waarden ingevuld."""
    return TEXT[LANG][key].format(**values)


def colour_name(colour):
    """Naam van een kleur (index) in de huidige taal."""
    return tr("colour_" + NAMES[colour])
