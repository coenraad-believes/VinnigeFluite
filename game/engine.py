"""Pure game logic for Vinnige Fluite (no Streamlit here, so it is easy to test).

Rules:
- The deck is shuffled and dealt round-robin; leftover cards start in the pot.
- The player whose turn it is picks a stat from their top card. Every other active
  player's top card is compared on that stat.
- The single best card wins all compared cards plus the pot (to the bottom of the pile).
  If the chooser wins, it stays their turn; otherwise the turn passes to the winner.
- On a tie the cards go into the pot, and only the tied players play the next round (an
  "afspeel"), again and again until one of them wins it and takes the pot. The chooser keeps
  the turn if they are in the tie; otherwise the next tied player chooses.
- Players with no cards left are out. The game ends when one player is left, or when
  the round limit (if any) is reached — then the player with the most cards wins.

Gedokterde spel: a player called "Pappa" or "Mamma" can't win. Before the cards are compared,
the hidden top cards (everyone's except the chooser's, which the chooser has already seen) are
quietly swapped for another card from that same player's own pile, so that a kid wins the round.
Swaps only happen when needed, pick randomly among the cards that work, and never use a card
from the last two rounds, so it doesn't look suspicious. The winner screen reveals it afterwards.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from game.stats import BY_KEY, Stat

RIGGED_NAMES = {"pappa", "mamma"}
RECENT_ROUNDS = 2  # cards from this many previous rounds are never swapped in


@dataclass
class Player:
    naam: str
    emoji: str
    pile: list[str] = field(default_factory=list)  # index 0 is the top card

    @property
    def active(self) -> bool:
        return bool(self.pile)

    @property
    def rigged(self) -> bool:
        """Pappa and Mamma can't win."""
        return self.naam.strip().casefold() in RIGGED_NAMES


@dataclass
class RoundResult:
    chooser: int
    stat: str
    played: dict[int, str]  # player index -> card id
    values: dict[int, float]
    winner: int | None  # None means a tie (cards went to the pot)
    pot_won: int = 0  # how many pot cards the winner collected
    tie_off: bool = False  # only the players from a previous tie played this round


@dataclass
class GameState:
    players: list[Player]
    current: int = 0
    pot: list[str] = field(default_factory=list)
    rounds: int = 0
    max_rounds: int | None = None
    last: RoundResult | None = None
    recent: list[list[str]] = field(default_factory=list)  # cards played in the last few rounds
    swaps: int = 0  # how many times a card was quietly swapped
    tied: list[int] = field(default_factory=list)  # players in an afspeel after a tie (empty: everyone plays)

    @property
    def rigged(self) -> bool:
        """True when the game is being doctored: a Pappa/Mamma plays against at least one kid."""
        return any(p.rigged for p in self.players) and not all(p.rigged for p in self.players)

    def active_players(self) -> list[int]:
        return [i for i, p in enumerate(self.players) if p.active]

    def contenders(self) -> list[int]:
        """Who plays the next round: the tied players during an afspeel, otherwise everyone."""
        return [i for i in self.tied if self.players[i].active] or self.active_players()

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
                   rounds=d["rounds"], max_rounds=d["max_rounds"], last=last,
                   recent=d.get("recent", []), swaps=d.get("swaps", 0), tied=d.get("tied", []))


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


def play_round(state: GameState, stat_key: str, cars: dict[str, dict],
               rng: random.Random | None = None) -> RoundResult:
    if state.over:
        raise RuntimeError("Die spel is klaar")
    stat = BY_KEY[stat_key]
    chooser = state.current
    tie_off = bool(state.tied)
    order = [chooser] + [i for i in state.contenders() if i != chooser]
    if state.rigged:
        _doctor(state, stat, cars, order, rng or random.Random())
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
        state.tied = []
    else:
        winner, pot_won = None, 0
        state.pot.extend(played.values())
        tied = [i for i in top if state.players[i].active]
        # An afspeel needs two players with cards. In a doctored game, Pappa and Mamma never
        # play one on their own, or one of them would win the pot.
        if len(tied) < 2 or (state.rigged and all(state.players[i].rigged for i in tied)):
            tied = []
        state.tied = tied
        if tied and chooser not in tied:
            state.current = _next_active(state, chooser, among=tied)
        elif not state.players[chooser].active:  # chooser played their last card in a tie
            state.current = _next_active(state, chooser)

    state.rounds += 1
    state.recent = (state.recent + [list(played.values())])[-RECENT_ROUNDS:]
    state.last = RoundResult(chooser, stat_key, played, values, winner, pot_won, tie_off)
    return state.last


def _next_active(state: GameState, start: int, among: list[int] | None = None) -> int:
    n = len(state.players)
    for step in range(1, n + 1):
        i = (start + step) % n
        if state.players[i].active and (among is None or i in among):
            return i
    return start


def _beats(stat: Stat, a: float, b: float) -> bool:
    return a > b if stat.higher_wins else a < b


def _doctor(state: GameState, stat: Stat, cars: dict[str, dict], order: list[int], rng: random.Random) -> None:
    """Quietly swap hidden top cards so that a kid (not Pappa/Mamma) wins this round.

    The chooser's top card is never touched, because the chooser has already seen it. Every
    other player's top card is still face down, so it can be exchanged for another card from
    that player's own pile (the old top card simply stays in the pile, one place lower).
    """
    chooser = order[0]
    kids = [i for i in order if not state.players[i].rigged]
    parents = [i for i in order if state.players[i].rigged]
    if not kids or not parents:
        return
    recent = {c for rnd in state.recent for c in rnd}

    def val(cid: str) -> float:
        return stat.value(cars[cid])

    def top(i: int) -> float:
        return val(state.players[i].pile[0])

    def swap_to_top(i: int, ok) -> bool:
        """Move a random card from player i's pile that satisfies ok(value) to the top."""
        pile = state.players[i].pile
        options = [n for n, cid in enumerate(pile) if n > 0 and cid not in recent and ok(val(cid))]
        if not options:
            return False
        n = rng.choice(options)
        pile.insert(0, pile.pop(n))
        state.swaps += 1
        return True

    def best(values):
        values = list(values)
        return max(values) if stat.higher_wins else min(values)

    # 1. Make sure some kid holds a card that beats the chooser's card if a parent chose, or at
    #    least the kids' best card when a kid chose. Only hidden (non-chooser) kid cards can change.
    target = best(top(i) for i in kids)
    if chooser in parents and not _beats(stat, target, top(chooser)):
        needed = top(chooser)
        helpers = [i for i in kids if i != chooser]
        rng.shuffle(helpers)
        for i in helpers:
            if swap_to_top(i, lambda v: _beats(stat, v, needed)):
                break
        target = best(top(i) for i in kids)

    # 2. Every other parent must end up with a card that loses to the kids' best card.
    for i in parents:
        if i == chooser or _beats(stat, target, top(i)):
            continue
        if not swap_to_top(i, lambda v: _beats(stat, target, v)):
            # No losing card in that parent's pile: give a kid an even stronger card instead.
            helpers = [k for k in kids if k != chooser]
            rng.shuffle(helpers)
            current = top(i)
            for k in helpers:
                if swap_to_top(k, lambda v: _beats(stat, v, current)):
                    target = best(top(j) for j in kids)
                    break
