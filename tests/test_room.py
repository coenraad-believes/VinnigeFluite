import unittest

from game.room import Room, RoomError
from game.stats import STATS
from game.storage import load_cars

CARS = load_cars()


def open_room(*names):
    room = Room()
    room.open()
    return room, [room.join(n) for n in names]


def pick(room):
    top = CARS[room.game.players[room.game.current].pile[0]]
    return next(s.key for s in STATS if s.choosable(top))


class LobbyTests(unittest.TestCase):
    def test_join_and_leave(self):
        room, (a, b) = open_room("Anna", "Ben")
        self.assertEqual([s.naam for s in room.seats], ["Anna", "Ben"])
        self.assertEqual(room.seat_of(b), 1)
        room.leave(a)
        self.assertEqual(room.seat_of(b), 0)
        self.assertIsNone(room.seat_of(a))
        self.assertIsNone(room.seat_of(None))

    def test_join_rules(self):
        room, _ = open_room("Anna", "Ben", "Chris", "Dina")
        with self.assertRaises(RoomError):
            room.join("Eben")  # full
        room, _ = open_room("Anna")
        for naam in ("anna", "  "):
            with self.assertRaises(RoomError):
                room.join(naam)
        with self.assertRaises(RoomError):
            room.start(list(CARS), None)  # only one player
        room.join("Ben")
        room.start(list(CARS), 10)
        with self.assertRaises(RoomError):
            room.join("Laat")  # already started

    def test_changes_bump_version(self):
        room = Room()
        before = room.version
        room.open()
        room.join("Anna")
        self.assertEqual(room.version, before + 2)


class PlayTests(unittest.TestCase):
    def test_only_current_player_can_choose(self):
        room, tokens = open_room("Anna", "Ben")
        room.start(list(CARS), None)
        other = tokens[1 - room.game.current]
        room.choose(other, pick(room), CARS)
        self.assertEqual(room.phase, "kies")
        room.choose(tokens[room.game.current], pick(room), CARS)
        self.assertEqual(room.phase, "onthul")
        self.assertEqual(room.game.rounds, 1)

    def test_double_tap_next_round_counts_once(self):
        room, tokens = open_room("Anna", "Ben")
        room.start(list(CARS), None)
        room.choose(tokens[room.game.current], pick(room), CARS)
        seen = room.version
        room.next_round(seen)
        room.next_round(seen)  # the second phone tapped the same (now stale) button
        self.assertEqual(room.phase, "kies")
        self.assertEqual(room.version, seen + 1)

    def test_full_game_then_play_again(self):
        room, tokens = open_room("Anna", "Ben", "Pappa")
        room.start(list(CARS), 15)
        while room.phase != "einde":
            room.choose(tokens[room.game.current], pick(room), CARS)
            room.next_round(room.version)
        self.assertEqual(room.game.rounds, 15)
        self.assertEqual(room.game.total_cards(), len(CARS))
        room.play_again()
        self.assertEqual((room.phase, len(room.seats), room.game), ("lobby", 3, None))

    def test_snapshot_is_a_copy(self):
        room, _ = open_room("Anna", "Ben")
        room.start(list(CARS), None)
        snap = room.snapshot()
        snap.game.players[0].pile.clear()
        self.assertTrue(room.game.players[0].pile)


if __name__ == "__main__":
    unittest.main()
