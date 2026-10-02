#!/usr/bin/env python3
"""Re-measure the bargain candidates between the hourly runs and push new ones.

Dips are often gone within the hour, so the cards the last hourly analysis put
on its watch list (at least 8 % own dip) are fetched again every ten minutes.
Each fresh price is judged against the fair price and market move from that
analysis — the same rules as the hourly list — and the result is written to a
small JSON file the page reads alongside the hourly one:

    python3 fut/recheck.py icons-analysis.json icons-live.json
    python3 fut/recheck.py --test      # one test message on every channel

When a card turns into a buy, a push goes out on every channel configured
through environment variables (GitHub secrets — the repository is public):

  * ntfy:     NTFY_TOPIC, optionally NTFY_TOKEN. Without a token ntfy.sh limits
              messages per IP address, and runners share theirs; with a token
              (free account) the limit is per account instead.
  * Telegram: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

Without any, nothing is sent. The same card is pushed at most once every
NOTIFY_EVERY; a push that fails on every channel is retried next tick.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from analyze import EPS, MARKET_FALLING, MIN_NET_COINS, MIN_OWN_DIP, TAX  # noqa: E402
from collect import fetch, market_price  # noqa: E402

NOTIFY_EVERY = timedelta(hours=6)
PAGE = "https://hannesjere1-sketch.github.io/Sportwette/fut.html"
PAUSE = 0.4


def judge(card, price):
    """Status of a watched card at a fresh price, by the hourly list's rules."""
    fair, market = card["fair"], card.get("market")
    own = price / fair - 1 - (market or 0.0)
    net = round(fair * (1 - TAX) - price)
    if own > -MIN_OWN_DIP + EPS or net < MIN_NET_COINS:
        status = "vorbei"
    elif market is not None and market <= MARKET_FALLING:
        status = "markt-faellt"
    elif card.get("downtrend"):
        status = "abwaertstrend"
    else:
        status = "kaufen"
    return {"price": round(price), "ownDip": own, "netCoins": net, "status": status}


def coins(n):
    return f"{n:,}".replace(",", ".")


def message(card, live):
    """Title and plain-text body, short enough for a lock screen."""
    return (f"Schnäppchen: {card['name']}",
            f"Jetzt {coins(live['price'])} (eigener Dip {live['ownDip'] * 100:+.1f} %)\n"
            f"Max-Kaufpreis {coins(card['maxBuy'])}\n"
            f"Ziel (fair) {coins(card['fair'])}\n"
            f"Netto +{coins(live['netCoins'])} Coins")


def post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20):
        pass


def channels(env):
    """(name, send) for every configured channel; send(title, body) raises on failure."""
    out = []
    topic = env.get("NTFY_TOPIC", "").strip()
    if topic:
        token = env.get("NTFY_TOKEN", "").strip()
        auth = {"Authorization": f"Bearer {token}"} if token else {}
        # The JSON form, because umlauts in a title header are not reliable.
        out.append(("ntfy", lambda title, body: post_json(
            "https://ntfy.sh/", {"topic": topic, "title": title, "message": body,
                                 "tags": ["moneybag"], "priority": 4, "click": PAGE}, auth)))
    bot, chat = env.get("TELEGRAM_BOT_TOKEN", "").strip(), env.get("TELEGRAM_CHAT_ID", "").strip()
    if bot and chat:
        out.append(("Telegram", lambda title, body: post_json(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            {"chat_id": chat, "text": f"{title}\n{body}\n{PAGE}", "disable_web_page_preview": True})))
    return out


def push(card, live, chans, title=None, body=None):
    """Send on every channel; True if at least one got through."""
    if title is None:
        title, body = message(card, live)
    sent = False
    for name, send in chans:
        try:
            send(title, body)
            sent = True
            print(f"  Push über {name}: {card['name']}")
        except (urllib.error.URLError, TimeoutError) as e:
            # Only the channel name, the status and the service's own reason are
            # printed — never the URL, which for Telegram contains the token.
            reason = ""
            if isinstance(e, urllib.error.HTTPError):
                try:
                    reason = e.read().decode("utf-8", "replace")[:200]
                except OSError:
                    pass
            print(f"  Push über {name} fehlgeschlagen ({card['name']}): {getattr(e, 'code', type(e).__name__)} {reason}")
    return sent


def send_test(env):
    """Send one clearly marked test message; True if any channel took it."""
    chans = channels(env)
    if not chans:
        print("Kein Push-Kanal eingerichtet: Secret NTFY_TOPIC (oder TELEGRAM_BOT_TOKEN + "
              "TELEGRAM_CHAT_ID) fehlt oder ist leer.")
        return False
    print("Eingerichtete Kanäle:", ", ".join(name for name, _ in chans),
          "(ntfy mit Token)" if env.get("NTFY_TOKEN", "").strip() else "")
    card = {"name": "TEST – Push funktioniert", "fair": 163_000, "maxBuy": 151_000}
    live = {"price": 143_000, "ownDip": -0.117, "netCoins": 11_850}
    title, body = message(card, live)
    body = "Testnachricht aus GitHub Actions – kein echtes Schnäppchen.\n" + body
    return push({"name": card["name"]}, None, chans, title=title, body=body)


def main():
    if sys.argv[1:] == ["--test"]:
        sys.exit(0 if send_test(os.environ) else 1)
    if len(sys.argv) != 3:
        sys.exit("Aufruf: recheck.py <icons-analysis.json> <icons-live.json>")
    analysis_path, live_path = sys.argv[1:]
    with open(analysis_path, encoding="utf-8") as fh:
        watch = (json.load(fh).get("dips") or {}).get("watch") or []
    previous = {}
    if os.path.exists(live_path):
        with open(live_path, encoding="utf-8") as fh:
            previous = json.load(fh)
    notified = previous.get("notified", {})
    chans = channels(os.environ)
    now = datetime.now(timezone.utc)

    cards = {}
    for card in watch:
        try:
            price = market_price(fetch(card["id"]))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            print(f"  Fehler bei {card['name']}: {e}")
            price = None
        if price:
            live = judge(card, price)
            live["at"] = now.isoformat(timespec="seconds")
            cards[str(card["id"])] = live
            last = notified.get(str(card["id"]))
            due = not last or now - datetime.fromisoformat(last) >= NOTIFY_EVERY
            if live["status"] == "kaufen" and due:
                if not chans:
                    print(f"  Kein Push-Kanal eingerichtet – kein Push für {card['name']}")
                elif push(card, live, chans):
                    notified[str(card["id"])] = live["at"]
        time.sleep(PAUSE)

    # Forget notifications old enough to be sent again, so the file stays small.
    notified = {k: v for k, v in notified.items()
                if now - datetime.fromisoformat(v) < NOTIFY_EVERY}
    with open(live_path, "w", encoding="utf-8") as fh:
        json.dump({"checkedAt": now.isoformat(timespec="seconds"), "cards": cards,
                   "notified": notified}, fh, ensure_ascii=False, indent=1)
    buys = sum(c["status"] == "kaufen" for c in cards.values())
    print(f"{len(cards)}/{len(watch)} Kandidaten nachgemessen, {buys} weiterhin zum Kaufen ({now:%H:%M}Z).")


if __name__ == "__main__":
    main()
