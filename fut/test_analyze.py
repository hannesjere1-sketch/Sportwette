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


if __name__ == "__main__":
    unittest.main()
