#!/usr/bin/env python3
"""Check whether the API-Football plan in use returns goal minutes.

Spends three requests: the account status, one fixture lookup, and the goal
events for that fixture. Prints the shape of what comes back — never the key,
and never a full response body.

The analysis needs, for one match, the goals in order with a minute each. That
is what decides whether the opponent scored the FIRST goal of the match before
minute 35, which is the only case the strategy counts.
"""

import json
import os
import sys
import urllib.error
import urllib.request

HOST = "https://v3.football.api-sports.io"
# Bundesliga 2023/24, Bayern — a season and club the free plan is likely to hold.
LEAGUE, SEASON, TEAM = 78, 2023, 157


def call(path: str, key: str):
    req = urllib.request.Request(HOST + path, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def show_errors(payload) -> bool:
    """API-Football answers 200 with an errors object; surface it as a failure."""
    errors = payload.get("errors")
    if errors and errors != []:
        print(f"  Dienst meldet: {json.dumps(errors, ensure_ascii=False)[:300]}")
        return True
    return False


def main() -> int:
    key = os.environ.get("API_FOOTBALL_KEY", "").strip()
    if not key:
        print("API_FOOTBALL_KEY ist nicht gesetzt.", file=sys.stderr)
        return 1

    try:
        print("1) Kontostatus")
        status = call("/status", key)
        if show_errors(status):
            print("\nERGEBNIS: Schluessel wurde abgelehnt.")
            return 1
        resp = status.get("response") or {}
        sub = resp.get("subscription") or {}
        req = resp.get("requests") or {}
        print(f"   Tarif: {sub.get('plan')}   aktiv bis: {sub.get('end')}")
        print(f"   Anfragen heute: {req.get('current')} von {req.get('limit_day')}")

        print("\n2) Ein Spiel suchen (Bundesliga 2023/24, Bayern)")
        fixtures = call(f"/fixtures?league={LEAGUE}&season={SEASON}&team={TEAM}", key)
        if show_errors(fixtures):
            print("\nERGEBNIS: Spielliste nicht zugaenglich — vermutlich Saison ausserhalb des Tarifs.")
            return 1
        items = fixtures.get("response") or []
        print(f"   Spiele gefunden: {len(items)}")
        if not items:
            print("\nERGEBNIS: Keine Spiele — diese Saison deckt der Tarif nicht ab.")
            return 1

        finished = [f for f in items
                    if (f.get("fixture", {}).get("status", {}).get("short")) == "FT"]
        pick = (finished or items)[0]
        fid = pick["fixture"]["id"]
        goals = pick.get("goals") or {}
        print(f"   Gewaehlt: #{fid}  {pick['teams']['home']['name']} {goals.get('home')}"
              f":{goals.get('away')} {pick['teams']['away']['name']}"
              f"  ({pick['fixture']['date'][:10]})")

        print("\n3) Tor-Ereignisse zu diesem Spiel")
        events = call(f"/fixtures/events?fixture={fid}", key)
        if show_errors(events):
            print("\nERGEBNIS: Ereignisse nicht zugaenglich.")
            return 1
        all_events = events.get("response") or []
        goal_events = [e for e in all_events if (e.get("type") or "").lower() == "goal"]
        print(f"   Ereignisse gesamt: {len(all_events)}, davon Tore: {len(goal_events)}")

        with_minute = [e for e in goal_events
                       if isinstance((e.get("time") or {}).get("elapsed"), int)]
        print(f"   Tore mit Minutenangabe: {len(with_minute)}")

        for e in goal_events[:6]:
            t = e.get("time") or {}
            minute = t.get("elapsed")
            extra = t.get("extra")
            print(f"     Minute {minute}{'+' + str(extra) if extra else ''}"
                  f"  Team: {(e.get('team') or {}).get('name')}"
                  f"  Art: {e.get('detail')}")

        own = [e for e in goal_events if (e.get("detail") or "").lower() == "own goal"]
        print(f"   davon Eigentore in dieser Stichprobe: {len(own)}")
        if own:
            e = own[0]
            print(f"     Eigentor-Beispiel -> team im Datensatz: "
                  f"{(e.get('team') or {}).get('name')}")

        print()
        if goal_events and len(with_minute) == len(goal_events):
            print("ERGEBNIS: JA — Torminuten werden geliefert, Reihenfolge rekonstruierbar.")
            return 0
        if not goal_events:
            print("ERGEBNIS: UNKLAR — dieses Spiel hatte keine Tore. Bitte erneut laufen lassen.")
            return 1
        print("ERGEBNIS: NEIN — nicht alle Tore tragen eine Minute.")
        return 1

    except urllib.error.HTTPError as exc:
        print(f"Anfrage fehlgeschlagen mit HTTP {exc.code}.", file=sys.stderr)
        if exc.code in (401, 403):
            print("Der Schluessel wurde abgelehnt. Kommt er von RapidAPI statt von "
                  "api-sports.io? Dann braucht es einen anderen Host und Header.",
                  file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Dienst nicht erreichbar: {exc.reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
