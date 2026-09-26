"""Checks the analysis against synthetic prices whose truth is known.

Run with:  python3 -m unittest fut/test_analyze.py
"""

import argparse
import json
import math
import os
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import analyze  # noqa: E402


def args(**kw):
    base = dict(window=14, min_days=3, min_hours=12, min_edge=0.01, slippage=0.01,
                events="", min_events=1)
    base.update(kw)
    return argparse.Namespace(**base)


def synthetic(amplitude, days=28, players=6, noise=0.01, seed=1, drop=0.0):
    """Hourly prices: random-walk trend × daily wave (low 07:00, high 19:00 Berlin) × noise.

    With drop > 0, every Thursday 09:00 a reward drop cuts prices by that share,
    bottoming out after 3 hours and recovering fully a day later."""
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
            if drop:
                since = None
                for back in range(0, 49):
                    t = local - timedelta(hours=back)
                    if t.weekday() == 3 and t.hour == 9:
                        since = back
                        break
                if since is not None and since <= 27:
                    depth = since / 3 if since <= 3 else max(0.0, 1 - (since - 3) / 24)
                    price *= 1 - drop * depth
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

    def test_reliability_verdicts(self):
        early = analyze.run(synthetic(amplitude=0.06, days=3), args())["reliability"]
        self.assertEqual(early["verdict"], "sammeln")
        strong = analyze.run(synthetic(amplitude=0.06), args())["reliability"]
        self.assertEqual(strong["verdict"], "profitabel")
        # Real but smaller than the tax: the hours are right, the money is not.
        weak = analyze.run(synthetic(amplitude=0.015, noise=0.005), args())["reliability"]
        self.assertEqual(weak["verdict"], "muster")
        noise = analyze.run(synthetic(amplitude=0.0, noise=0.03), args())["reliability"]
        self.assertIn(noise["verdict"], ("kein-muster", "sammeln"))

    def test_reward_drop_is_measured_and_traded(self):
        ev = [{"key": "rivals", "name": "Rivals", "weekday": 3, "hour": 9}]
        path = os.path.join(os.path.dirname(__file__), "_test_events.json")
        with open(path, "w") as fh:
            json.dump(ev, fh)
        try:
            res = analyze.run(synthetic(amplitude=0.0, noise=0.005, drop=0.08, days=35),
                              args(events=path))
        finally:
            os.remove(path)
        e = res["events"][0]
        self.assertGreaterEqual(e["measured"], 4)
        self.assertEqual(e["troughOffset"], 3)
        self.assertAlmostEqual(e["troughChange"], -0.08, delta=0.01)
        # Trough to recovery is ~8.7 %: enough to clear tax and undercut.
        self.assertGreater(e["backtest"]["trades"], 0)
        self.assertGreater(e["backtest"]["avgReturn"], 0)

    def test_daily_strategy_skips_reward_days(self):
        ev = [{"key": "rivals", "name": "Rivals", "weekday": 3, "hour": 9}]
        path = os.path.join(os.path.dirname(__file__), "_test_events.json")
        with open(path, "w") as fh:
            json.dump(ev, fh)
        try:
            res = analyze.run(synthetic(amplitude=0.06, drop=0.08), args(events=path))
        finally:
            os.remove(path)
        days = {t["day"] for p in res["players"] for t in p["trades"]}
        self.assertTrue(days)
        self.assertFalse(any(datetime.fromisoformat(d).weekday() == 3 for d in days))


if __name__ == "__main__":
    unittest.main()
