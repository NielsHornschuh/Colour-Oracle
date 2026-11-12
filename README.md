# Colour Oracle

Een spel waarin jij een AI probeert te slim af te zijn.

Elke ronde staan vier gekleurde tegels in willekeurige volgorde. De AI legt
vooraf vast welke kleur jij gaat kiezen. Jij houdt de nauwkeurigheid van de AI
onder de drempel gedurende 100 rondes om te winnen. Na elke ronde schudden de
tegels.

De AI combineert negen strategieën met een Hedge-achtige *multiplicative
weights update*. Strategieën die goed voorspellen krijgen meer gewicht;
strategieën die minder goed werken krijgen minder gewicht.

## Benodigdheden

- Python 3.9 of nieuwer
- Tkinter

Er zijn geen externe Python-pakketten nodig. Tkinter wordt meestal automatisch
meegeleverd met Python:

- **Windows:** installeer Python via [python.org](https://www.python.org/downloads/)
  en laat Tkinter en de standaardopties geselecteerd.
- **macOS:** gebruik bij voorkeur de installer van python.org.
- **Linux (Ubuntu/Debian):** installeer Tkinter met `sudo apt install python3-tk`.

## Starten

Open een terminal in de projectmap en voer uit:

```text
python main.py
```

Op macOS en Linux kan ook `python3 main.py` nodig zijn. In PyCharm of VS Code
kun je `main.py` openen en uitvoeren. De applicatie opent een Tkinter-venster.

## Spelregels

- Klik op een tegel of druk op `1`, `2`, `3` of `4`.
- De toetsen volgen de schermpositie van links naar rechts, niet de kleur.
- De AI maakt haar voorspelling voordat jij kiest.
- Na je keuze wordt de voorspelling getoond en leert de AI van het resultaat.
- Je wint als de AI na 100 rondes strikt onder **27%** nauwkeurigheid blijft.
- Bij vier even waarschijnlijke kleuren is de gemiddelde basisnauwkeurigheid 25%.
  Voorspelbare patronen maken het voor de AI makkelijker.

Op het beginscherm kun je rechtsboven wisselen tussen Nederlands en Engels.
De standaardtaal is Nederlands.

## Projectstructuur

```text
main.py
colour_oracle/
├── config.py                 # spel- en AI-instellingen
├── constants.py              # kleuren en gedeelde constanten
├── i18n.py                   # Nederlandse en Engelse teksten
├── engine/
│   ├── ensemble.py           # combinatie en gewichten van strategieën
│   ├── helpers.py            # gedeelde AI-hulpfuncties
│   └── strategies/           # afzonderlijke voorspellers
└── ui/                       # Tkinter-schermen, tegels en panelen
```

De AI-logica, gebruikersinterface en configuratie zijn van elkaar gescheiden.
Daardoor kun je een strategie of een UI-onderdeel aanpassen zonder alles in
één bestand te wijzigen.

## De negen strategieën

De strategieën worden in deze volgorde geladen:

1. **Markov Chain (1-Step / 2-Step)** (`colours`) — voorspelt op basis van de
   vorige één of twee gekozen kleuren.
2. **Frequency & Recency Bias** (`bias`) — combineert keuze-frequentie met
   extra gewicht voor recente keuzes.
3. **Baseline Randomizer** (`random`) — een zachte willekeurige basisvoorspeller.
4. **Anti-Streak Predictor** (`streak`) — herkent reeksen en voorspelt een
   herhaling of wissel.
5. **Step Habit & Position Delta** (`step`) — leert patronen in sprongen tussen
   schermposities.
6. **Gambler's Fallacy Balancer** (`lag`) — gebruikt oudere keuzes en kleuren
   die al een tijd niet gekozen zijn.
7. **Dodge & Reaction Tracker** (`reaction`) — meet reacties op de getoonde
   nauwkeurigheid, een AI-treffer of -misser en tegelbeweging.
8. **Position Habit Tracker** (`position`) — volgt voorkeuren voor
   schermposities en herhalingen.
9. **Colour-at-Position Tracker** (`pair`) — volgt kleurvoorkeuren per positie.

Elke strategie voorspelt een kansverdeling. Het ensemble mengt die
verdelingen met de actuele strategiegewichten en kiest daaruit de
AI-voorspelling.

## Instellingen aanpassen

Pas de waarden bovenaan `colour_oracle/config.py` aan en start het spel daarna
opnieuw.

| Instelling | Betekenis |
| --- | --- |
| `TOTAL_ROUNDS` | Aantal rondes per spel |
| `WIN_THRESHOLD` | Maximale AI-nauwkeurigheid; de AI moet hier strikt onder blijven |
| `ETA` | Leersnelheid van de multiplicative weights update |
| `FLOOR` | Minimumgewicht voor elke actieve strategie |
| `ACTIVE_STRATEGIES` | Strategieën die aan het ensemble deelnemen |
| `CREATOR_NAME` | Naam op het beginscherm |
| `REVEAL_MS` | Tijd dat de voorspelling na een keuze zichtbaar blijft |
| `SHUFFLE_MS` | Duur van de schudanimatie |
| `DEFAULT_LANGUAGE` | Starttaal: `nl` of `en` |

Een strategie uitschakelen kan door haar sleutel uit `ACTIVE_STRATEGIES` te
halen. Voeg een nieuwe strategie toe als klasse in
`colour_oracle/engine/strategies/`, registreer haar in `strategies/__init__.py`
en voeg haar sleutel toe aan `ACTIVE_STRATEGIES`.

## Dev screen

Druk tijdens het spel op **Ctrl+Shift+D** om het dev screen te openen. Het
toont de live gewichten van alle strategieën. Als `reaction` actief is, worden
ook de drie vertrouwenswaarden van de zichtbare signalen getoond.

Met de schakelaar **Show AI prediction before pick** kun je de voorspelling
vooraf zichtbaar maken. Dit is bedoeld voor demonstraties: het dev screen
verandert de werking van de AI niet.

## Problemen oplossen

| Probleem | Oplossing |
| --- | --- |
| `No module named tkinter` | Installeer Tkinter; op Ubuntu/Debian: `sudo apt install python3-tk` |
| Windows vindt Python niet | Installeer Python opnieuw en vink **Add python.exe to PATH** aan |
| Het venster verschijnt niet | Controleer of `python main.py` vanuit de projectmap wordt uitgevoerd |

## Vragen

Wil je meer weten over de werking? Vraag het aan Niels.
