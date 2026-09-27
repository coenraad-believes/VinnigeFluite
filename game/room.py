"""One shared game for players on their own phones (no Streamlit here, so it is easy to test).

Every browser that opens the app is its own Streamlit session, so the game lives here, in one
Room object that all sessions share. Players join the lobby with a name and get a secret token
(kept in the page URL, so a phone that reloads is still the same player). Every change bumps
`version`, which tells the other phones to redraw.

Phases: "lobby" (players join) → "kies" (the current player picks a stat on their phone) →
"onthul" (everyone sees the cards) → "kies" … → "einde".
"""

from __future__ import annotations

import copy
import secrets
import threading
from dataclasses import dataclass, field

from game.engine import GameState, new_game, play_round

EMOJIS = ["🔴", "🔵", "🟢", "🟡"]
MAX_PLAYERS = 4


class RoomError(Exception):
    """A friendly (Afrikaans) message for the player."""


@dataclass
class Seat:
    naam: str
    token: str


@dataclass
class Snapshot:
    """A consistent copy of the room for drawing one screen."""
    phase: str | None
    version: int
    seats: list[Seat]
    game: GameState | None


@dataclass
class Room:
    phase: str | None = None  # None: no phone game open
    version: int = 0
    seats: list[Seat] = field(default_factory=list)  # seat index == player index in the game
    game: GameState | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(self.phase, self.version, copy.deepcopy(self.seats), copy.deepcopy(self.game))

    def seat_of(self, token: str | None) -> int | None:
        with self._lock:
            return self._seat_of(token)

    def _seat_of(self, token: str | None) -> int | None:
        return next((i for i, s in enumerate(self.seats) if token and s.token == token), None)

    def _changed(self) -> None:
        self.version += 1

    # ---------- lobby ----------

    def open(self) -> None:
        with self._lock:
            if self.phase is None:
                self.phase, self.seats, self.game = "lobby", [], None
                self._changed()

    def close(self) -> None:
        with self._lock:
            self.phase, self.seats, self.game = None, [], None
            self._changed()

    def join(self, naam: str) -> str:
        naam = naam.strip()
        with self._lock:
            if self.phase != "lobby":
                raise RoomError("Die spel het reeds begin.")
            if not naam:
                raise RoomError("Tik eers jou naam.")
            if len(self.seats) >= MAX_PLAYERS:
                raise RoomError(f"Daar is reeds {MAX_PLAYERS} spelers.")
            if any(s.naam.casefold() == naam.casefold() for s in self.seats):
                raise RoomError(f"Daar is reeds iemand met die naam {naam}.")
            token = secrets.token_urlsafe(8)
            self.seats.append(Seat(naam, token))
            self._changed()
            return token

    def leave(self, token: str) -> None:
        with self._lock:
            i = self._seat_of(token)
            if self.phase == "lobby" and i is not None:
                del self.seats[i]
                self._changed()

    def token_for(self, seat: int) -> str:
        """Lets a player whose phone lost its page take their seat back."""
        with self._lock:
            return self.seats[seat].token

    def start(self, card_ids: list[str], max_rounds: int | None) -> None:
        with self._lock:
            if self.phase != "lobby":
                return
            if len(self.seats) < 2:
                raise RoomError("Julle moet minstens 2 spelers wees.")
            players = [(s.naam, EMOJIS[i]) for i, s in enumerate(self.seats)]
            self.game = new_game(players, card_ids, max_rounds=max_rounds)
            self.phase = "kies"
            self._changed()

    # ---------- playing ----------

    def choose(self, token: str, stat_key: str, cars: dict[str, dict]) -> None:
        """The current player picks a stat. Taps from anyone else (or a stale screen) are ignored."""
        with self._lock:
            if self.phase != "kies" or self._seat_of(token) != self.game.current:
                return
            play_round(self.game, stat_key, cars)
            self.phase = "onthul"
            self._changed()

    def next_round(self, seen_version: int) -> None:
        """Anyone may move on from the reveal, but two quick taps only count once."""
        with self._lock:
            if self.phase != "onthul" or seen_version != self.version:
                return
            self.phase = "einde" if self.game.over else "kies"
            self._changed()

    def play_again(self) -> None:
        """Back to the lobby with the same players."""
        with self._lock:
            if self.phase == "einde":
                self.phase, self.game = "lobby", None
                self._changed()
