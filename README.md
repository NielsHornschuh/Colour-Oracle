# Color Oracle

Een spel waarin jij een AI probeert te slim af te zijn.

Elke ronde staan vier gekleurde tegels in willekeurige volgorde. De AI gokt welke tegel jij gaat kiezen, nog voordat jij kiest. Jij houdt de nauwkeurigheid van de AI onder de drempel gedurende 100 rondes om te winnen. Na elke ronde schudden de tegels.

Onder de motorkap staan negen strategieën die elk een eigen gok doen. Een Hedge-achtige multiplicative weights update geeft strategieën die goed gokken steeds meer gewicht. De gok van de AI is de gewogen uitkomst van al die stemmen.

## Starten in drie stappen

1. **Installeer Python 3.9 of nieuwer** via https://www.python.org/downloads/ (Ik raad aan de nieuwste versie te downloaden)
   - Windows: laat in het installatiescherm alles op de standaardinstelling staan. Tkinter zit er dan bij.
   - Mac: gebruik de installer van python.org. Die bevat Tkinter.
   - Linux (Ubuntu en Debian): voer `sudo apt install python3-tk` uit.
2. **Pak de zip uit** naar een map.
3. **Dubbelklik op de startbestanden voor jouw systeem:**
   - Windows: `Start-Windows.bat`
   - Mac: `Start-Mac.command` (de eerste keer: rechtermuisknop, dan Open)
   - Linux: `Start-Linux.sh`

Er zijn geen extra pakketten nodig.

## Starten vanuit de terminal

Open een terminal in de map en voer uit:

- Windows: `py color_oracle.py`
- Mac en Linux: `python3 color_oracle.py`

## Openen in een code-editor

Het is één bestand: `colour_oracle.py`.

- **PyCharm of VS Code:** kies Open Folder, open `colour_oracle.py` en druk op Run.
- **IDLE** (zit bij Python): open `colour_oracle.py` en druk op F5.

## Spelregels

- Klik op een tegel of druk op 1, 2, 3 of 4. De toetsen volgen de positie op het scherm (links → rechts), niet de kleur.
- De AI legt zijn gok vast voordat jij kiest. Daarna wordt de gok getoond.
- Je wint als de AI na 100 rondes strikt onder de drempel blijft.
- Zuiver toeval levert de AI gemiddeld 25% op. Wie patronen volgt, geeft de AI meer.

## De negen strategieën

Elke ronde doet elke strategie een eigen voorspelling in de vorm van een kans per kleur. De AI telt die kansen op, gewogen naar hoe vaak elke strategie tot nu toe goed zat, en kiest de kleur met de hoogste totaalkans. De volgorde hieronder is de volgorde in het dev screen.

1. **Markov Chain (1-Step / 2-Step)** (`colors`). Telt welke kleur volgde op jouw vorige één of twee kleuren, een N-gram. Heeft een lange context te weinig waarnemingen, dan valt de strategie terug op een kortere.
2. **Frequency & Recency Bias** (`bias`). Telt hoe vaak je elke kleur koos, waarbij recente keuzes zwaarder wegen, en meet hoe vaak je dezelfde kleur herhaalt.
3. **Baseline Randomizer** (`random`). Doet een zachte willekeurige gok. Dit is het vangnet: het voorkomt dat de AI vastloopt op een strategie die niet meer werkt, en haalt gemiddeld 25%.
4. **Anti-Streak Predictor** (`streak`). Meet hoe groot de kans is dat je dezelfde kleur nog eens kiest na een reeks van 1, 2 of 3 of meer keer, en voorspelt dan een herhaling of een wissel.
5. **Step Habit & Position Delta** (`step`). Een Markov chain op de sprongen tussen schermposities. Dit vangt een motorische gewoonte, zoals steeds één plek naar rechts klikken.
6. **Gambler's Fallacy Balancer** (`lag`). Kijkt naar de kleur van twee en drie keuzes terug en naar kleuren die je al even niet koos. Veel mensen denken dat een koude kleur aan de beurt is.
7. **Dodge & Reaction Tracker** (`reaction`). Toetst drie zichtbare signalen los van elkaar: de getoonde nauwkeurigheid van de AI (groen of rood), of de AI de vorige ronde raak gokte, en welke tegel tijdens het schudden het verst of het minst ver bewoog. Een z-toets bepaalt per signaal of het jouw gedrag aantoonbaar verandert. Een signaal zonder aantoonbare invloed telt niet mee.
8. **Position Habit Tracker** (`position`). Meet hoe groot de kans is dat je weer op dezelfde schermpositie klikt, na een reeks van 1, 2 of 3 of meer klikken, en onthoudt welke andere posities je liever hebt.
9. **Color-at-Position Tracker** (`pair`). Houdt per tegel bij hoe vaak een kleur op een bepaalde positie gekozen is ten opzichte van hoe vaak die daar stond. Zo vangt hij een voorkeur voor een bepaalde kleur op een bepaalde plek.

## Zelf aanpassen

Bovenaan `colour_oracle.py` staan de instellingen. Pas een waarde aan, sla op en start opnieuw.

| Instelling | Wat het doet |
| --- | --- |
| `TOTAL_ROUNDS` | Aantal rondes per spel |
| `WIN_THRESHOLD` | De drempel voor de AI, bijvoorbeeld 0.27 voor 27% |
| `ETA` | Hoe snel een strategie gewicht wint of verliest |
| `FLOOR` | Het kleinste gewicht dat een strategie houdt |
| `ACTIVE_STRATEGIES` | Welke strategieën meedoen. Haal een naam weg om hem uit te zetten |
| `CREATOR_NAME` | De naam op het beginscherm |
| `REVEAL_MS`, `SHUFFLE_MS` | Snelheid van de onthulling en de schudanimatie |

Wil je een eigen strategie toevoegen? Kopieer een bestaande klasse, zoals `PositionStrategy`, geef hem een nieuwe `label`, schrijf `predict` en `update` om en voeg hem toe aan `STRATEGY_CLASSES` en `ACTIVE_STRATEGIES`.

## Dev screen

Druk tijdens het spel op **Ctrl+Shift+D**. Er opent een paneel met de negen strategieën en hun gewichten, live bijgewerkt. Onder de Dodge & Reaction Tracker staan drie kleine balken met het vertrouwen per zichtbaar signaal: de nauwkeurigheid die je ziet, of de AI raak of mis gokte, en de beweging van de tegels. Groen betekent dat de AI denkt dat dit signaal jouw gedrag beïnvloedt. Een schakelaar toont de gok van de AI voordat je kiest. Niets in dit paneel verandert hoe de AI voorspelt.

## Problemen oplossen

| Melding of probleem | Oplossing |
| --- | --- |
| `No module named tkinter` | Installeer Python opnieuw via python.org, of op Linux `sudo apt install python3-tk` |
| Op Mac met Homebrew: Tkinter ontbreekt | Voer `brew install python-tk` uit, of gebruik de installer van python.org |
| Windows zegt dat Python niet gevonden is | Installeer Python opnieuw en vink Add python.exe to PATH aan |
| Mac blokkeert `Start-Mac.command` | Rechtermuisknop, dan Open, en bevestig |
| `.command` of `.sh` start niet | Voer in de map `chmod +x Start-Mac.command Start-Linux.sh` uit |

## Vragen

Wil je meer weten? Vraag het aan Niels.
