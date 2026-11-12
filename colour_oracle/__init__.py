"""Colour Oracle: houd de nauwkeurigheid van de AI onder de drempel.

Indeling van het pakket:
  config.py     instellingen die je zelf aanpast
  constants.py  de vier kleuren en afgeleide waarden
  i18n.py       teksten in het Nederlands en Engels
  engine/       de AI: hulpfuncties, het ensemble en de negen strategieën
  ui/           alles wat je ziet: venster, tegels, panelen en schermen

Het pakket gebruikt `__lazy_modules__` (Python 3.15+): standaardmodules worden
dan pas geladen als ze nodig zijn. Eerdere versies van Python (3.9 tot 3.14)
negeren dit en laden ze zoals altijd.
"""