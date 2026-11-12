"""De vier kleuren van het spel en waarden die daaruit volgen."""


COLOURS = {
    "Red": "#ff4d5a",
    "Blue": "#3d8bff",
    "Green": "#2fd18b",
    "Yellow": "#ffc933",
}
NAMES = list(COLOURS)
N = len(NAMES)
UNIFORM = [1.0 / N] * N  # gelijke kans voor elke kleur
