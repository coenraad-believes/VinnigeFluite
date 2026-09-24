"""Local-first persistence: the running game lives in data/savegame.json."""

import json
from pathlib import Path

from game.engine import GameState

ROOT = Path(__file__).resolve().parent.parent
SAVE = ROOT / "data" / "savegame.json"


def load_cars() -> dict[str, dict]:
    cars = json.loads((ROOT / "data" / "cars.json").read_text(encoding="utf-8"))
    return {c["id"]: c for c in cars}


def load_credits() -> dict[str, dict]:
    path = ROOT / "data" / "credits.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_game(state: GameState, screen: str) -> None:
    tmp = SAVE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"screen": screen, "state": state.to_dict()}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(SAVE)


def load_game() -> tuple[GameState, str] | None:
    try:
        d = json.loads(SAVE.read_text(encoding="utf-8"))
        return GameState.from_dict(d["state"]), d["screen"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def clear_game() -> None:
    SAVE.unlink(missing_ok=True)
