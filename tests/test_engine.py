import random
import unittest

from game.engine import GameState, Player, new_game, play_round
from game.stats import BY_KEY, STATS
from game.storage import load_cars

CARS = load_cars()


def car(cid, **stats):
    base = dict(id=cid, topspoed_kmh=200, nul_tot_100_s=6.0, kwartmyl_s=14.0, massa_kg=1300,
                jaar_begin=2000, jaar_einde=2004, enjin_cc=2000, krag_kw=150, wringkrag_nm=300)
    return base | stats


class DataTests(unittest.TestCase):
    def test_deck_has_80_unique_cards(self):
        self.assertEqual(len(CARS), 80)

    def test_fields_and_ranges(self):
        for c in CARS.values():
            with self.subTest(c["id"]):
                for key in ("naam", "maker", "land", "wiki_title", "foto_soek", "feit"):
                    self.assertTrue(c[key])
                self.assertTrue(100 <= c["topspoed_kmh"] <= 500)
                self.assertTrue(2.0 <= c["nul_tot_100_s"] <= 40)
                self.assertTrue(8.0 <= c["kwartmyl_s"] <= 26)
                self.assertTrue(600 <= c["massa_kg"] <= 3000)
                self.assertTrue(900 <= c["enjin_cc"] <= 8500)
                self.assertTrue(20 <= c["krag_kw"] <= 1200)
                self.assertTrue(80 <= c["wringkrag_nm"] <= 1700)
                self.assertTrue(1930 <= c["jaar_begin"] <= c["jaar_einde"] <= 2026)
                # a quarter mile takes longer than 0-100 km/h (except for the very slowest cars,
                # e.g. a Beetle 1200 finishes the quarter mile before it reaches 100 km/h)
                if c["nul_tot_100_s"] < 15:
                    self.assertGreater(c["kwartmyl_s"], c["nul_tot_100_s"])


class RuleTests(unittest.TestCase):
    def game(self, a, b, pot=None, current=0):
        return GameState(players=[Player("A", "🔴", a), Player("B", "🔵", b)], pot=pot or [], current=current)

    def test_direction_of_every_stat(self):
        fast = car("fast", topspoed_kmh=300, nul_tot_100_s=3.0, kwartmyl_s=11.0, massa_kg=1000,
                   jaar_begin=1990, jaar_einde=2020, enjin_cc=6000, krag_kw=400, wringkrag_nm=700)
        slow = car("slow")
        cars = {"fast": fast, "slow": slow}
        for stat in STATS:
            with self.subTest(stat.key):
                g = self.game(["slow", "x"], ["fast", "y"])
                cars |= {"x": car("x"), "y": car("y")}
                r = play_round(g, stat.key, cars)
                self.assertEqual(r.winner, 1)

    def test_years_is_span_inclusive(self):
        self.assertEqual(BY_KEY["jare"].value(car("c", jaar_begin=1998, jaar_einde=1998)), 1)
        self.assertEqual(BY_KEY["jare"].display(CARS["vw-beetle"]), "1938–2003 · 66 jaar")

    def test_chooser_keeps_turn_while_winning(self):
        cars = {"a1": car("a1", topspoed_kmh=300), "a2": car("a2", topspoed_kmh=300),
                "b1": car("b1"), "b2": car("b2")}
        g = self.game(["a1", "a2"], ["b1", "b2"])
        play_round(g, "topspoed_kmh", cars)
        self.assertEqual(g.current, 0)
        self.assertEqual(g.players[0].pile, ["a2", "a1", "b1"])

    def test_turn_passes_to_player_who_beat_chooser(self):
        cars = {"a1": car("a1"), "b1": car("b1", enjin_cc=5000), "c1": car("c1"),
                "a2": car("a2"), "b2": car("b2"), "c2": car("c2")}
        g = GameState(players=[Player("A", "", ["a1", "a2"]), Player("B", "", ["b1", "b2"]),
                               Player("C", "", ["c1", "c2"])])
        r = play_round(g, "enjin_cc", cars)
        self.assertEqual(r.winner, 1)
        self.assertEqual(g.current, 1)
        self.assertEqual(g.players[1].pile, ["b2", "a1", "b1", "c1"])

    def test_tie_goes_to_pot_then_next_winner_takes_it(self):
        cars = {"a1": car("a1"), "b1": car("b1"), "a2": car("a2", massa_kg=900), "b2": car("b2")}
        g = self.game(["a1", "a2"], ["b1", "b2"], pot=["extra"])
        r = play_round(g, "massa_kg", cars)
        self.assertIsNone(r.winner)
        self.assertEqual(g.pot, ["extra", "a1", "b1"])
        self.assertEqual(g.current, 0)
        r = play_round(g, "massa_kg", cars)
        self.assertEqual(r.winner, 0)
        self.assertEqual(r.pot_won, 3)
        self.assertEqual(g.pot, [])
        self.assertEqual(sorted(g.players[0].pile), ["a1", "a2", "b1", "b2", "extra"])
        self.assertTrue(g.over)
        self.assertEqual(g.winners(), [0])

    def test_eliminated_player_skipped_and_turn_moves_on_tie(self):
        cars = {k: car(k) for k in ["a1", "b1", "c1", "c2"]}
        g = GameState(players=[Player("A", "", ["a1"]), Player("B", "", ["b1"]), Player("C", "", ["c1", "c2"])])
        play_round(g, "enjin_cc", cars)  # three-way tie, A and B are out
        self.assertEqual(g.current, 2)
        self.assertTrue(g.over)

    def test_round_limit_most_cards_wins(self):
        cars = {k: car(k) for k in ["a1", "a2", "b1"]}
        cars["a1"]["topspoed_kmh"] = 999
        g = self.game(["a1", "a2"], ["b1"])
        g.players.append(Player("C", "", ["c1"]))
        cars["c1"] = car("c1")
        g.max_rounds = 1
        play_round(g, "topspoed_kmh", cars)
        self.assertTrue(g.over)
        self.assertEqual(g.winners(), [0])

    def test_deal_keeps_all_cards(self):
        for n in (2, 3, 4):
            g = new_game([(f"P{i}", "") for i in range(n)], list(CARS), rng=random.Random(n))
            self.assertEqual(g.total_cards(), 80)
            self.assertEqual({len(p.pile) for p in g.players}, {80 // n})
            self.assertEqual(len(g.pot), 80 % n)

    def test_full_games_finish_and_conserve_cards(self):
        for seed in range(20):
            rng = random.Random(seed)
            g = new_game([("A", ""), ("B", ""), ("C", ""), ("D", "")], list(CARS), rng=rng)
            while not g.over and g.rounds < 5000:
                play_round(g, rng.choice(STATS).key, CARS)
                self.assertEqual(g.total_cards(), 80)
                self.assertTrue(g.players[g.current].active or g.over)
            # an unlimited game can in theory loop forever; with random choices it ends
            self.assertTrue(g.over, f"seed {seed} did not finish")

    def test_save_roundtrip(self):
        g = new_game([("A", "🔴"), ("B", "🔵")], list(CARS), max_rounds=20, rng=random.Random(1))
        play_round(g, "enjin_cc", CARS)
        again = GameState.from_dict(g.to_dict())
        self.assertEqual(again, g)


if __name__ == "__main__":
    unittest.main()
