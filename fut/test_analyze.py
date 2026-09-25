"""Checks the analysis against synthetic prices whose truth is known.

Run with:  python3 -m unittest fut/test_analyze.py
"""

import argparse
import math
import os
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import analyze  # noqa: E402


def args(**kw):
    base = dict(window=14, min_days=3, min_hours=12, min_edge=0.01, slippage=0.01)
    base.update(kw)
    return argparse.Namespace(**base)


def synthetic(amplitude, days=28, players=6, noise=0.01, seed=1):
    """Hourly prices: random-walk trend × daily wave (low 07:00, high 19:00 Berlin) × noise."""
    rnd = random.Random(seed)
    start = datetime(2026, 10, 1, tzinfo=analyze.TZ)
    rows = []
    for p in range(players):
        level = rnd.uniform(5_000, 80_000)
        for step in range(days * 24):
            local = start + timedelta(hours=step)
            level *= math.exp(rnd.gauss(0, 0.004))
            wave = 1 - amplitude * math.cos((local.hour - 7) / 24 * 2 * math.pi)
            price = level * wave * math.exp(rnd.gauss(0, noise))
            rows.append((local.astimezone(timezone.utc), str(p), f"Spieler {p}", price))
    return rows


class AnalyzeTest(unittest.TestCase):
    def test_finds_the_daily_pattern_and_profits(self):
        res = analyze.run(synthetic(amplitude=0.06), args())
        prof = res["marketProfile"]
        self.assertIn(min(prof, key=prof.get), (6, 7, 8))
        self.assertIn(max(prof, key=prof.get), (18, 19, 20))
        self.assertGreater(res["overall"]["trades"], 50)
        self.assertGreater(res["overall"]["avgReturn"], 0)

    def test_small_pattern_does_not_beat_the_tax(self):
        # A 2 % swing each way is real but smaller than the 5 % tax: no trades
        # should be taken, and certainly no fake profit reported.
        res = analyze.run(synthetic(amplitude=0.01), args())
        self.assertEqual(res["overall"]["trades"], 0)

    def test_pure_noise_is_not_traded_profitably(self):
        res = analyze.run(synthetic(amplitude=0.0, noise=0.03), args(min_edge=0.0))
        o = res["overall"]
        if o["trades"]:
            self.assertLess(o["avgReturn"], 0)

    def test_no_lookahead(self):
        # Prices on the traded day must not influence that day's chosen hours:
        # corrupting the last day changes its outcome, never its hours.
        rows = synthetic(amplitude=0.06, days=10, players=1)
        last = max(r[0] for r in rows).astimezone(analyze.TZ).date()
        grid, _ = analyze.hourly_grid(rows)
        before = {t["day"]: (t["buyHour"], t["sellHour"])
                  for t in analyze.backtest_player(grid["0"], args())}
        for h in grid["0"][last]:
            grid["0"][last][h] *= 1 + (0.3 if h == 3 else 0)
        after = {t["day"]: (t["buyHour"], t["sellHour"])
                 for t in analyze.backtest_player(grid["0"], args())}
        self.assertEqual(before.get(last.isoformat()), after.get(last.isoformat()))


if __name__ == "__main__":
    unittest.main()
