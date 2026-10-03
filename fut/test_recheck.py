"""Checks the ten-minute recheck: its verdicts and when it pushes.

Run with:  python3 -m unittest fut/test_recheck.py
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))
import recheck  # noqa: E402

CARD = {"id": 7, "name": "Steve McManaman (2)", "kind": "Hero", "fair": 163_000,
        "maxBuy": 151_000, "market": -0.006, "downtrend": False}


class RecheckTest(unittest.TestCase):
    def test_verdicts(self):
        self.assertEqual(recheck.judge(CARD, 143_000)["status"], "kaufen")
        self.assertEqual(recheck.judge(CARD, 152_000)["status"], "vorbei")   # dip gone
        self.assertEqual(recheck.judge(dict(CARD, market=-0.05), 125_000)["status"], "markt-faellt")
        self.assertEqual(recheck.judge(dict(CARD, downtrend=True), 143_000)["status"], "abwaertstrend")
        live = recheck.judge(CARD, 143_000)
        self.assertEqual(live["netCoins"], 11_850)

    def test_message(self):
        title, body = recheck.message(CARD, recheck.judge(CARD, 143_000))
        self.assertEqual(title, "Schnäppchen: Steve McManaman (2)")
        self.assertIn("Jetzt 143.000", body)
        self.assertIn("Max-Kaufpreis 151.000", body)
        self.assertIn("Ziel (fair) 163.000", body)
        self.assertIn("Netto +11.850 Coins", body)

    def run_main(self, folder, price, sent, fail=False, env=None):
        def send(title, body):
            if fail:
                raise recheck.urllib.error.URLError("down")
            sent.append(title)
        analysis = os.path.join(folder, "a.json")
        with open(analysis, "w") as fh:
            json.dump({"dips": {"watch": [CARD]}}, fh)
        live = os.path.join(folder, "live.json")
        with mock.patch.object(recheck, "fetch", return_value={"priceInfo": {"source": "market", "displayPrice": price}}), \
             mock.patch.object(recheck, "channels", return_value=[("test", send)]), \
             mock.patch.object(recheck, "PAUSE", 0), \
             mock.patch.object(recheck, "PAUSE_FILE", os.path.join(folder, "kein-pause-file")), \
             mock.patch.object(sys, "argv", ["recheck.py", analysis, live]), \
             mock.patch.dict(os.environ, env or {}, clear=False):
            recheck.main()
        with open(live) as fh:
            return json.load(fh)

    def test_pushes_once_per_card(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            first = self.run_main(d, 143_000, sent)
            self.assertEqual(first["cards"]["7"]["status"], "kaufen")
            self.run_main(d, 141_000, sent)   # ten minutes later, still a buy
        self.assertEqual(sent, ["Schnäppchen: Steve McManaman (2)"])

    def test_failed_push_is_retried(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            self.run_main(d, 143_000, sent, fail=True)
            self.run_main(d, 143_000, sent)
        self.assertEqual(len(sent), 1)

    def test_gone_dip_is_reported_not_pushed(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            live = self.run_main(d, 152_000, sent)
        self.assertEqual(sent, [])
        self.assertEqual(live["cards"]["7"]["status"], "vorbei")
        self.assertEqual(live["cards"]["7"]["price"], 152_000)

    def test_no_channel_without_secrets(self):
        self.assertEqual(recheck.channels({}), [])
        self.assertEqual([n for n, _ in recheck.channels({"NTFY_TOPIC": "x", "TELEGRAM_BOT_TOKEN": "t",
                                                          "TELEGRAM_CHAT_ID": "1"})], ["ntfy", "Telegram"])

    def test_test_message(self):
        sent = []
        with mock.patch.object(recheck, "channels", return_value=[("test", lambda t, b: sent.append((t, b)))]):
            self.assertTrue(recheck.send_test({}))
        self.assertTrue(sent[0][0].startswith("Schnäppchen: TEST"))
        self.assertIn("kein echtes Schnäppchen", sent[0][1])
        self.assertFalse(recheck.send_test({}))   # no channel configured

    def test_max_buy_is_always_a_buy(self):
        # Paying exactly the max buy price must never come out as "vorbei", for
        # cheap and dear cards, flat and slightly falling markets.
        from analyze import max_buy
        for fair in range(25_000, 500_001, 7_500):
            for market in (None, 0.0, -0.006, -0.02, 0.015):
                card = {"fair": fair, "market": market, "downtrend": False}
                limit = max_buy(fair, market)
                self.assertEqual(recheck.judge(card, limit)["status"], "kaufen",
                                 f"fair {fair}, market {market}, max buy {limit}")

    def test_push_limit(self):
        self.assertEqual(recheck.push_limit({}), 250_000)
        self.assertEqual(recheck.push_limit({"PUSH_MAX_PRICE": "150000"}), 150_000)
        self.assertEqual(recheck.push_limit({"PUSH_MAX_PRICE": "150.000"}), 150_000)
        self.assertEqual(recheck.push_limit({"PUSH_MAX_PRICE": ""}), 250_000)
        self.assertEqual(recheck.push_limit({"PUSH_MAX_PRICE": "viel"}), 250_000)

    def test_no_push_over_the_price_cap(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            live = self.run_main(d, 143_000, sent, env={"PUSH_MAX_PRICE": "100000"})
            self.assertEqual(live["cards"]["7"]["status"], "kaufen")   # still listed
            self.assertEqual(sent, [])
            self.assertEqual(live["notified"], {})
            # Cap raised: the same card is pushed at the next tick.
            self.run_main(d, 143_000, sent, env={"PUSH_MAX_PRICE": "250000"})
        self.assertEqual(len(sent), 1)

    def test_paused_sends_nothing_and_resumes(self):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            live = self.run_main(d, 143_000, sent, env={"PUSH_PAUSED": "ja"})
            self.assertEqual(live["cards"]["7"]["status"], "kaufen")  # still measured
            self.assertEqual(sent, [])
            self.assertEqual(live["notified"], {})
            self.run_main(d, 143_000, sent, env={"PUSH_PAUSED": ""})  # resumed
        self.assertEqual(len(sent), 1)
        with tempfile.NamedTemporaryFile() as f, mock.patch.object(recheck, "PAUSE_FILE", f.name):
            self.assertTrue(recheck.push_paused({}))
        with mock.patch.object(recheck, "PAUSE_FILE", "/nonexistent/push-paused"):
            self.assertFalse(recheck.push_paused({"PUSH_PAUSED": "false"}))
            self.assertTrue(recheck.push_paused({"PUSH_PAUSED": "1"}))


if __name__ == "__main__":
    unittest.main()
