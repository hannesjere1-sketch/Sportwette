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


def steady(cards, others=0, start=datetime(2026, 10, 5, tzinfo=timezone.utc)):
    """Rows for cards given as hourly price lists (all ending at the same hour),
    plus `others` flat cards so the market has enough members."""
    length = max(len(v) for v in cards.values())
    cards = dict(cards, **{f"flat{k}": [300_000] * length for k in range(others)})
    rows = []
    for pid, prices in cards.items():
        offset = length - len(prices)
        for k, p in enumerate(prices):
            rows.append((start + timedelta(hours=offset + k), pid, pid, "Icon", float(p)))
    return rows


def assessment(prices):
    """The assessment of the last of an hourly price list."""
    points = [(datetime(2026, 10, 5, tzinfo=timezone.utc) + timedelta(hours=k), float(p))
              for k, p in enumerate(prices)]
    return analyze.assess(points, [t for t, _ in points], len(points) - 1)


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

    # ---- bargain list -------------------------------------------------------

    def test_dip_is_bought_and_sold_on_recovery(self):
        rows = synthetic(cards=6, days=3, noise=0.002)
        # Card 1 drops 12 % for three hours on day 2, then recovers.
        dip_start = rows[0][0] + timedelta(hours=40)
        rows = [(t, c, n, k, p * 0.88 if c == "1" and dip_start <= t < dip_start + timedelta(hours=3) else p)
                for t, c, n, k, p in rows]
        lv = analyze.run(rows)["dips"]["levels"]["0.10"]
        self.assertEqual(lv["trades"], 1)
        self.assertEqual(lv["hitRate"], 1.0)
        self.assertAlmostEqual(lv["avgGain"], 0.136, delta=0.02)
        self.assertAlmostEqual(lv["avgNet"], 0.95 / 0.88 - 1, delta=0.02)

    def test_spike_does_not_lift_the_fair_price(self):
        # Ledley King: 395k for two days, 14 h at 544k, now 370k. Against the
        # last 24 h median that looked like -19 %; it is only ~6 % under fair.
        prices = [395_000] * 50 + [544_000] * 14 + [380_000] * 5 + [370_000]
        res = analyze.run(steady({"king": prices}, others=6))
        self.assertNotIn("king", [s["id"] for s in res["dips"]["signals"]])
        a = assessment(prices)
        self.assertAlmostEqual(a["fair"], 395_000, delta=8_000)

    def test_back_to_pre_spike_level_is_no_bargain(self):
        # A spike that fills most of the history: against the median it would
        # look like the normal level, and the return to it like a 15 % dip.
        prices = [300_000] * 30 + [450_000] * 45 + [382_000]
        a = assessment(prices)
        self.assertAlmostEqual(a["fair"], 300_000, delta=1)
        self.assertEqual(a["preSpike"], 300_000)
        self.assertTrue(a["backAfterSpike"])
        res = analyze.run(steady({"long": prices}, others=6))
        self.assertNotIn("long", [s["id"] for s in res["dips"]["signals"]])

    def test_short_history_spike(self):
        # The real Ledley King (2) curve: half of the history is the spike.
        prices = [395, 395, 391, 420, 449, 544, 535, 540, 530, 512, 529, 530, 510, 505,
                  479, 425, 459, 461, 470, 405, 385, 370, 365, 392, 389, 368, 371]
        a = assessment([p * 1000 for p in prices])
        self.assertGreater(a["discount"], -0.08)
        self.assertEqual(a["preSpike"], 395_000)

    def test_falling_card_is_flagged_as_downtrend(self):
        prices = [200_000] * 60 + [200_000 * 0.975 ** k for k in range(1, 7)]
        res = analyze.run(steady({"slide": prices}, others=6))
        sig = {s["id"]: s for s in res["dips"]["signals"]}
        self.assertEqual(sig["slide"]["status"], "abwaertstrend")
        self.assertEqual(sig["slide"]["falls"], 6)

    def test_calm_card_ranks_before_wild_one(self):
        calm = [200_000] * 60 + [170_000]
        # Wild card: deeper dip (-18 % vs -15 %), but it swings ±8 % every hour.
        wild = [200_000 * (1.08 if k % 2 else 0.92) for k in range(60)] + [150_000]
        res = analyze.run(steady({"calm": calm, "wild": wild}, others=6))
        sig = [s for s in res["dips"]["signals"] if s["id"] in ("calm", "wild")]
        self.assertEqual([s["id"] for s in sig], ["calm", "wild"])
        self.assertLess(sig[0]["vol"], 0.01)
        self.assertGreater(sig[1]["vol"], 0.05)

    def test_market_wide_drop_is_no_bargain(self):
        # Every card 12 % down at once: no card has a dip of its own.
        cards = {f"c{k}": [200_000] * 60 + [176_000] for k in range(8)}
        self.assertEqual(analyze.run(steady(cards))["dips"]["signals"], [])

    def test_own_dip_in_falling_market_is_not_a_buy(self):
        cards = {f"c{k}": [200_000] * 60 + [192_000] for k in range(8)}  # market -4 %
        cards["deep"] = [200_000] * 60 + [164_000]                      # -18 %, own -14 %
        sig = analyze.run(steady(cards))["dips"]["signals"]
        self.assertEqual([(s["id"], s["status"]) for s in sig], [("deep", "markt-faellt")])
        self.assertAlmostEqual(sig[0]["ownDip"], -0.14, delta=0.01)

    def test_own_dip_in_steady_market_is_a_buy(self):
        sig = analyze.run(steady({"dip": [200_000] * 60 + [174_000]}, others=6))["dips"]["signals"]
        self.assertEqual([(s["id"], s["status"]) for s in sig], [("dip", "kaufen")])
        self.assertEqual(sig[0]["netCoins"], round(200_000 * 0.95 - 174_000))
        self.assertEqual(len(sig[0]["spark"]), analyze.SPARK_HOURS)

    def test_small_net_profit_is_not_listed(self):
        # 15 % under 20k fair is only 2,000 coins after tax.
        sig = analyze.run(steady({"cheap": [20_000] * 60 + [17_000]}, others=6))["dips"]["signals"]
        self.assertEqual(sig, [])

    def test_max_buy_is_a_valid_bid(self):
        # Net rule is the lower limit for cheap cards …
        self.assertEqual(analyze.max_buy(20_000), 16_000)    # 16,000 net vs 18,000 dip
        self.assertEqual(analyze.max_buy(9_000), 5_500)      # 5,550 → 100 steps
        # … the 10 % dip rule for dearer ones.
        self.assertEqual(analyze.max_buy(163_000), 146_000)  # 146,700 dip vs 151,850 net
        self.assertEqual(analyze.max_buy(67_000), 60_000)    # 60,300 dip vs 60,650 net
        # A falling market lowers the dip limit further.
        self.assertEqual(analyze.max_buy(200_000, -0.02), 176_000)
        sig = analyze.run(steady({"dip": [200_000] * 60 + [174_000]}, others=6))["dips"]["signals"]
        self.assertEqual(sig[0]["maxBuy"], 180_000)

    def test_mario_gomez_max_buy_matches_status(self):
        # The bug report: max buy 99,500 (net rule only), live 99,000, yet "Dip
        # vorbei" because the own dip was only -9.8 %. Fair ~108,000, market -0.6 %.
        fair, market = 108_000, -0.006
        self.assertEqual(analyze.max_buy(fair), 97_000)          # 97,200 dip vs 99,600 net
        self.assertEqual(analyze.max_buy(fair, market), 96_500)  # 96,552 with the market
        own = 99_000 / fair - 1 - market
        self.assertGreater(own, -analyze.MIN_OWN_DIP)  # 99,000 is no buy …
        self.assertGreater(99_000, analyze.max_buy(fair, market))  # … and over max buy

    def test_watch_list_starts_at_eight_percent(self):
        cards = {"nine": [200_000] * 60 + [182_000], "five": [200_000] * 60 + [190_000]}
        watch = analyze.run(steady(cards, others=6))["dips"]["watch"]
        self.assertEqual([w["id"] for w in watch], ["nine"])
        self.assertEqual(watch[0]["fair"], 200_000)
        self.assertEqual(watch[0]["maxBuy"], 180_000)


if __name__ == "__main__":
    unittest.main()
