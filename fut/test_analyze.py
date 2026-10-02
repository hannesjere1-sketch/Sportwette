"""Checks the analysis against synthetic prices whose truth is known.

Run with:  python3 -m unittest fut/test_analyze.py
"""

import math
import os
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import analyze  # noqa: E402


def synthetic(days=21, cards=8, daily=0.0, weekly=0.0, noise=0.005, trend=0.0, seed=1):
    """Hourly prices: level × daily wave (low 05:00, high 17:00) × a weekly
    pattern (Thursday 10:00 dip, Saturday 20:00 spike) × noise."""
    rnd = random.Random(seed)
    start = datetime(2026, 10, 5, tzinfo=analyze.TZ)  # a Monday
    rows = []
    for c in range(cards):
        level = rnd.uniform(50_000, 450_000)
        kind = "Icon" if c % 2 else "Hero"
        for step in range(days * 24):
            local = start + timedelta(hours=step)
            level *= 1 + trend / 24
            wave = 1 - daily * math.cos((local.hour - 5) / 24 * 2 * math.pi)
            week = 1.0
            if local.weekday() == 3 and 8 <= local.hour <= 12:
                week -= weekly
            if local.weekday() == 5 and 19 <= local.hour <= 21:
                week += weekly
            price = level * wave * week * math.exp(rnd.gauss(0, noise))
            rows.append((local.astimezone(timezone.utc), str(c), f"Karte {c}", kind, price))
    return rows


class AnalyzeTest(unittest.TestCase):
    def test_finds_the_cheap_and_dear_hours(self):
        res = analyze.run(synthetic(daily=0.04))
        prof = res["all"]["hourProfile"]
        self.assertIn(min(prof, key=prof.get), (4, 5, 6))
        self.assertIn(max(prof, key=prof.get), (16, 17, 18))
        self.assertAlmostEqual(prof[17] / prof[5] - 1, 0.083, delta=0.015)

    def test_finds_the_weekly_flip(self):
        res = analyze.run(synthetic(weekly=0.08))
        top = res["all"]["flips"][0]
        self.assertEqual(top["buyDay"], 3)
        self.assertIn(top["buyHour"], range(8, 13))
        self.assertEqual(top["sellDay"], 5)
        self.assertIn(top["sellHour"], range(19, 22))
        self.assertGreater(top["gain"], 0.12)

    def test_walk_forward_profits_from_a_real_pattern(self):
        w = analyze.run(synthetic(daily=0.04))["all"]["walkForward"]
        self.assertGreater(w["trades"], 50)
        self.assertGreater(w["avgGain"], 0.05)
        self.assertGreater(w["avgGainLow"], 0)

    def test_noise_shows_no_honest_gain(self):
        w = analyze.run(synthetic(noise=0.03))["all"]["walkForward"]
        self.assertLess(w["avgGainLow"], 0.0)
        self.assertLess(abs(w["avgGain"]), 0.02)

    def test_trend_does_not_fake_an_hour_pattern(self):
        # A card rising 1 % a day all along: no hour should look special.
        prof = analyze.run(synthetic(trend=0.01))["all"]["hourProfile"]
        self.assertLess(max(prof.values()) / min(prof.values()) - 1, 0.01)

    def test_price_cap(self):
        rows = synthetic(cards=4)
        rows += [(t, "pricey", "Teuer", "Icon", 900_000) for t, *_ in rows[:300]]
        res = analyze.run(rows)
        self.assertNotIn("pricey", {c["id"] for c in res["cards"]})

    def test_kinds_reported_separately(self):
        res = analyze.run(synthetic(daily=0.04))
        self.assertEqual(set(res["byKind"]), {"Icon", "Hero"})
        self.assertEqual(res["byKind"]["Icon"]["cards"], 4)

    def test_night_outliers_do_not_fake_a_spread(self):
        rows = synthetic(cards=4, days=7)
        # One overpriced listing at 03:00 every night for card 0.
        rows = [(t, c, n, k, p * 2.2 if c == "0" and t.astimezone(analyze.TZ).hour == 3 else p)
                for t, c, n, k, p in rows]
        res = analyze.run(rows)
        card = next(c for c in res["cards"] if c["id"] == "0")
        self.assertLess(card["spread"], 0.05)
        self.assertLess(card["high7"], card["low7"] * 1.2)

    def test_no_card_hours_before_two_days(self):
        res = analyze.run(synthetic(cards=4, days=1, daily=0.04))
        self.assertTrue(all("spread" not in c for c in res["cards"]))

    def test_dip_is_bought_and_sold_on_recovery(self):
        rows = synthetic(cards=4, days=3, noise=0.002)
        # Card 1 drops 12 % for three hours on day 2, then recovers.
        dip_start = rows[0][0] + timedelta(hours=40)
        rows = [(t, c, n, k, p * 0.88 if c == "1" and dip_start <= t < dip_start + timedelta(hours=3) else p)
                for t, c, n, k, p in rows]
        res = analyze.run(rows)
        lv = res["dips"]["levels"]["0.08"]
        self.assertEqual(lv["trades"], 1)
        self.assertEqual(lv["hitRate"], 1.0)
        self.assertAlmostEqual(lv["avgGain"], 0.136, delta=0.02)
        trade = res["dips"]["recent"][0]
        self.assertEqual(trade["card"], "1")
        self.assertEqual(datetime.fromisoformat(trade["buyAt"]), dip_start.astimezone(analyze.TZ))

    def test_current_dip_is_signalled(self):
        rows = synthetic(cards=4, days=2, noise=0.002)
        last = max(t for t, *_ in rows)
        rows = [(t, c, n, k, p * 0.9 if c == "2" and t == last else p) for t, c, n, k, p in rows]
        sig = analyze.run(rows)["dips"]["signals"]
        self.assertEqual([s["id"] for s in sig], ["2"])
        self.assertAlmostEqual(sig[0]["discount"], -0.1, delta=0.01)

    def test_quiet_market_has_no_dips(self):
        res = analyze.run(synthetic(cards=6, days=4, noise=0.002))
        self.assertEqual(res["dips"]["levels"]["0.08"]["trades"], 0)
        self.assertEqual(res["dips"]["signals"], [])


if __name__ == "__main__":
    unittest.main()
