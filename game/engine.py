"""Pure game logic for Vinnige Fluite (no Streamlit here, so it is easy to test).

Rules:
- The deck is shuffled and dealt round-robin; leftover cards start in the pot.
- The player whose turn it is picks a stat from their top card. Every other active
  player's top card is compared on that stat.
- The single best card wins all compared cards plus the pot (to the bottom of the pile).
  If the chooser wins, it stays their turn; otherwise the turn passes to the winner.
- On a tie the cards go into the pot and the chooser keeps the turn.
- Players with no cards left are out. The game ends when one player is left, or when
  the round limit (if any) is reached — then the player with the most cards wins.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from game.stats import BY_KEY


@dataclass
class Player:
    naam: str
    emoji: str
    pile: list[str] = field(default_factory=list)  # index 0 is the top card

    @property
    def active(self) -> bool:
        return bool(self.pile)


@dataclass
class RoundResult:
    chooser: int
    stat: str
    played: dict[int, str]  # player index -> card id
    values: dict[int, float]
    winner: int | None  # None means a tie (cards went to the pot)
    pot_won: int = 0  # how many pot cards the winner collected


@dataclass
class GameState:
    players: list[Player]
    current: int = 0
    pot: list[str] = field(default_factory=list)
    rounds: int = 0
    max_rounds: int | None = None
    last: RoundResult | None = None

    def active_players(self) -> list[int]:
        return [i for i, p in enumerate(self.players) if p.active]

    @property
    def over(self) -> bool:
        if len(self.active_players()) <= 1:
            return True
        return self.max_rounds is not None and self.rounds >= self.max_rounds

    def winners(self) -> list[int]:
        """Players with the most cards (more than one means a shared win)."""
        most = max(len(p.pile) for p in self.players)
        if most == 0:
            return []
        return [i for i, p in enumerate(self.players) if len(p.pile) == most]

    def total_cards(self) -> int:
        return len(self.pot) + sum(len(p.pile) for p in self.players)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.last:  # JSON keys must be strings
            d["last"]["played"] = {str(k): v for k, v in self.last.played.items()}
            d["last"]["values"] = {str(k): v for k, v in self.last.values.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> GameState:
        last = d.get("last")
        if last:
            last = RoundResult(**{**last,
                                  "played": {int(k): v for k, v in last["played"].items()},
                                  "values": {int(k): v for k, v in last["values"].items()}})
        return cls(players=[Player(**p) for p in d["players"]], current=d["current"], pot=d["pot"],
                   rounds=d["rounds"], max_rounds=d["max_rounds"], last=last)


def new_game(players: list[tuple[str, str]], card_ids: list[str], max_rounds: int | None = None,
             rng: random.Random | None = None) -> GameState:
    if not 2 <= len(players) <= 4:
        raise ValueError("2 tot 4 spelers")
    rng = rng or random.Random()
    deck = list(card_ids)
    rng.shuffle(deck)
    n = len(players)
    per_player = len(deck) // n
    state = GameState(players=[Player(naam, emoji) for naam, emoji in players], max_rounds=max_rounds)
    for i in range(per_player * n):
        state.players[i % n].pile.append(deck[i])
    state.pot = deck[per_player * n:]
    return state


def play_round(state: GameState, stat_key: str, cars: dict[str, dict]) -> RoundResult:
    if state.over:
        raise RuntimeError("Die spel is klaar")
    stat = BY_KEY[stat_key]
    chooser = state.current
    order = [chooser] + [i for i in state.active_players() if i != chooser]
    played = {i: state.players[i].pile.pop(0) for i in order}
    values = {i: stat.value(cars[c]) for i, c in played.items()}

    best = max(values.values()) if stat.higher_wins else min(values.values())
    top = [i for i, v in values.items() if v == best]
    if len(top) == 1:
        winner = top[0]
        pot_won = len(state.pot)
        state.players[winner].pile.extend(list(played.values()) + state.pot)
        state.pot = []
        state.current = winner
    else:
        winner, pot_won = None, 0
        state.pot.extend(played.values())
        if not state.players[chooser].active:  # chooser played their last card in a tie
            state.current = _next_active(state, chooser)

    state.rounds += 1
    state.last = RoundResult(chooser, stat_key, played, values, winner, pot_won)
    return state.last


def _next_active(state: GameState, start: int) -> int:
    n = len(state.players)
    for step in range(1, n + 1):
        i = (start + step) % n
        if state.players[i].active:
            return i
    return start
