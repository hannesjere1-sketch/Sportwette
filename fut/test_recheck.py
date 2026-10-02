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

    def run_main(self, folder, price, sent, fail=False):
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
             mock.patch.object(sys, "argv", ["recheck.py", analysis, live]):
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


if __name__ == "__main__":
    unittest.main()
