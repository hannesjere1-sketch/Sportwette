"""Tests for fetch_futalert.py with made-up answers; no network, no real prices.

    python3 -m unittest fut/test_fetch_futalert.py
"""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import fetch_futalert as ff  # noqa: E402

CARD = {"karte": "Testspieler", "promo": "TOTW 2", "gold_id": 1, "futalert_id": 99,
        "release": "2026-09-23T17:00:00Z", "aus_packs": "2026-09-30T17:00:00Z"}
START = datetime(2026, 9, 18, 17, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 17, tzinfo=timezone.utc)
AFTER_END = END + timedelta(hours=1)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_for(text, calls):
    def opener(req, timeout=None):
        calls.append(json.loads(req.data))
        return FakeResponse(text.encode())
    return opener


def failing(code, calls):
    def opener(req, timeout=None):
        calls.append(1)
        raise urllib.error.HTTPError(req.full_url, code, "x", {}, None)
    return opener


def movements(*items):
    return json.dumps({"CardMovements": [
        {"CurrentPricePS4": p, "CurrentPriceXBox": 1, "CurrentPricePC": 0, "LastUpdatedDate": t}
        for t, p in items], "Status": {"StatusType": "Ok"}})


class Window(unittest.TestCase):
    def test_five_days_before_to_seven_after(self):
        self.assertEqual(ff.window(CARD), (START, END))

    def test_selection_skips_totw1_and_cards_without_ids(self):
        cards = [CARD, dict(CARD, promo="TOTW 1"), dict(CARD, futalert_id=None), dict(CARD, gold_id=None),
                 dict(CARD, promo="DFG Team 2")]
        self.assertEqual([c["promo"] for c in ff.selected(cards)], ["TOTW 2", "DFG Team 2"])


class Fetch(unittest.TestCase):
    def test_one_request_for_the_window_ps_only_inside_window(self):
        calls = []
        text = movements(("2026-09-18T16:31:00", 500),      # before the window
                         ("2026-09-18T17:31:00.123", 100),
                         ("2026-09-19T01:31:00", 0),          # no PS price
                         ("2026-09-30T17:31:00", 700))        # after the window
        pts = ff.fetch(CARD, opener_for(text, calls))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["PlayerId"], 99)
        self.assertEqual(calls[0]["StartDate"], "2026-09-18T17:00:00")
        self.assertEqual(calls[0]["EndDate"], "2026-09-30T17:00:00")
        self.assertTrue(calls[0]["IsHourly"])
        self.assertEqual(pts, [(datetime(2026, 9, 18, 17, 31, tzinfo=timezone.utc), 100)])

    def test_stops_on_403_429_other_http_and_cloudflare(self):
        for code in (403, 429, 500):
            with self.assertRaises(ff.Stop) as cm:
                ff.fetch(CARD, failing(code, []))
            self.assertIn(str(code), str(cm.exception))
        with self.assertRaises(ff.Stop):
            ff.fetch(CARD, opener_for("<html><title>Just a moment...</title></html>", []))
        with self.assertRaises(ff.Stop):
            ff.fetch(CARD, opener_for("kein json", []))


class Blocks(unittest.TestCase):
    def test_four_hour_blocks_median_empty_left_out(self):
        pts = [(START + timedelta(minutes=31), 100), (START + timedelta(hours=1, minutes=31), 300),
               (START + timedelta(hours=2, minutes=31), 200), (START + timedelta(hours=9), 50)]
        self.assertEqual(ff.blocks(pts, START, END),
                         [(START, 200), (START + timedelta(hours=8), 50)])

    def test_six_blocks_per_day(self):
        pts = [(START + timedelta(hours=h), 10) for h in range(24)]
        self.assertEqual(len(ff.blocks(pts, START, END)), 6)


class Run(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.log = []

    def run_ff(self, cards, opener, now=AFTER_END):
        sleeps = []
        code = ff.run(self.dir, cards, now, opener=opener, sleep=sleeps.append, out=self.log.append)
        return code, sleeps

    def test_cache_means_never_asking_twice_and_csv_written(self):
        calls = []
        op = opener_for(movements(("2026-09-20T10:31:00", 1000), ("2026-09-20T11:31:00", 1200)), calls)
        b = dict(CARD, karte="Zweiter", futalert_id=7)
        code, sleeps = self.run_ff([CARD, b], op)
        self.assertEqual((code, len(calls), len(sleeps)), (0, 2, 1))
        self.assertTrue(all(8 <= s <= 15 for s in sleeps))
        code, sleeps = self.run_ff([CARD, b], op)
        self.assertEqual((len(calls), len(sleeps)), (2, 0))  # all from cache
        with open(os.path.join(self.dir, ff.CSV_NAME), encoding="utf-8") as fh:
            rows = fh.read().splitlines()
        self.assertEqual(rows[0], "karte,promo,timestamp,preis,plattform,quelle")
        self.assertEqual(rows[1], "Testspieler,TOTW 2,2026-09-20T09:00:00Z,1100,ps,futalert-4h")
        self.assertEqual(len(rows), 3)

    def test_open_window_is_not_fetched(self):
        calls = []
        code, _ = self.run_ff([CARD], opener_for(movements(), calls), now=END - timedelta(hours=1))
        self.assertEqual((code, calls), (0, []))
        self.assertTrue(any("wartet" in line for line in self.log))

    def test_stop_ends_run_keeps_progress_and_resumes(self):
        cards = [dict(CARD, karte="A", futalert_id=1), dict(CARD, karte="B", futalert_id=2),
                 dict(CARD, karte="C", futalert_id=3)]
        calls = []
        ok = opener_for(movements(("2026-09-20T10:31:00", 1000)), calls)

        def second_fails(req, timeout=None):
            if len(calls) == 1:
                calls.append("403")
                raise urllib.error.HTTPError(req.full_url, 403, "x", {}, None)
            return ok(req, timeout)

        code, _ = self.run_ff(cards, second_fails)
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 2)  # A fetched, B refused, C never asked
        self.assertTrue(any("ABBRUCH" in line for line in self.log))
        calls.clear()
        code, _ = self.run_ff(cards, ok)
        self.assertEqual((code, len(calls)), (0, 2))  # only B and C

    def test_plan_makes_no_request(self):
        calls = []
        ff.run(self.dir, [CARD], AFTER_END, plan_only=True, opener=opener_for(movements(), calls),
               out=self.log.append)
        self.assertEqual(calls, [])
        self.assertTrue(any("Abfragen" in line for line in self.log))


if __name__ == "__main__":
    unittest.main()
