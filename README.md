# 🏎️ Vinnige Fluite 💨

'n Afrikaanse Top Trumps-kaartspel vir kinders: 120 regte karre, 2 tot 4 spelers op een skerm.
Alles loop plaaslik op jou rekenaar, en jy het geen internet nodig om te speel nie.

*An Afrikaans car Top Trumps game for kids. It has 120 real cars and lets 2–4 players take turns on one screen. It runs locally and offline.*

## Hoe om te begin / Getting started

Jy het [uv](https://docs.astral.sh/uv/) nodig. *Requires uv.* Installeer dit so: *Install it like this:*

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# of met Homebrew / or with Homebrew
brew install uv
```

Maak dan 'n nuwe terminaal oop, en laai die speletjie af en begin dit: *Then open a new terminal, download the game and start it:*

```bash
git clone https://github.com/coenraad-believes/VinnigeFluite.git
cd VinnigeFluite
uv python install 3.12
uv sync
uv run streamlit run app.py        # maak http://localhost:8501 oop
```

Die foto's is reeds afgelaai. Om hulle weer af te laai (jy het internet nodig): *Photos are already downloaded. To re-fetch them (needs internet):*

```bash
uv run python scripts/fetch_images.py              # net ontbrekende foto's
uv run python scripts/fetch_images.py bmw-m3-e30   # net een kar weer
```

Om 'n spesifieke foto vas te pen, voeg `"foto": "File:....jpg"` (die Commons-lêernaam) by daardie kar in `data/cars.json` en laai hom weer af. *To pin a specific photo, add `"foto": "File:....jpg"` to that car in `data/cars.json` and re-fetch.*

## Reëls

- Die 120 kaarte word geskommel en uitgedeel.
- Wie se beurt dit is, kies iets van hul boonste kaart. Almal se boonste kaarte word vergelyk.
- **Hoër wen:** Topspoed, Krag (kW), Wringkrag (Nm), Produksiejare (hoeveel jaar lank gebou), Enjingrootte.
  **Laer wen:** 0–100 km/h, Kwartmyl, Massa.
- As jy wen, is dit weer jou beurt. As iemand jou klop, is dit hulle beurt.
- Gelykop: die kaarte gaan in die pot, en die volgende wenner kry alles.
- Wie al die kaarte het, of die meeste as die rondtes op is, wen.

## Projek

| Pad | Wat |
|---|---|
| `app.py` | Streamlit-skerms |
| `game/engine.py` | spelreëls (suiwer Python, getoets) |
| `game/stats.py` | die ses eienskappe en watter kant wen |
| `game/render.py` | kaart-HTML/CSS |
| `game/storage.py` | laai kaarte, stoor die spel in `data/savegame.json` |
| `data/cars.json` | die 120 kaarte |
| `data/credits.json` | fotograaf en lisensie vir elke foto |
| `scripts/fetch_images.py` | laai foto's van Wikimedia Commons af |

Toetse / tests: `uv run python -m unittest discover tests`

## Bronne

Die syfers is feite uit publieke bronne (vervaardigers, Wikipedia, motortydskrifte) en is benaderd. Die foto's kom van Wikimedia Commons onder vrye lisensies (CC BY, CC BY-SA, CC0 of publieke domein). Elke kaart en die "Oor die kaarte"-skerm noem die fotograaf.
