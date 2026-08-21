#!/usr/bin/env python3
"""Fetch the next fortnight of fixtures for the tracked clubs.

Reads the token from the FOOTBALL_DATA_TOKEN environment variable and sends it
as the X-Auth-Token header. The token is never printed, never written to the
output file, and never reaches the published page — the page only ever reads
the JSON this script produces.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.football-data.org/v4/matches"
DAYS = 14

# Free-tier competitions. Frauen-Bundesliga is not among them, which is why
# Bayern (F) stays a manual entry in the app.
COMPETITIONS = {
    "BL1": "Bundesliga",
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
}

# The API spells clubs its own way; the app has one canonical spelling per club
# and matches fixtures to teams by that string. Order matters: "Internazionale"
# must be tested before "Milan", or Inter would be filed under AC Milan.
TEAM_RULES = [
    ("Inter", lambda n: "internazionale" in n or n.strip() == "inter"),
    ("AC Milan", lambda n: "milan" in n and "internazionale" not in n),
    ("FC Bayern München", lambda n: "bayern" in n and "münchen" in n or n.startswith("fc bayern")),
    ("Borussia Dortmund", lambda n: "dortmund" in n),
    ("Arsenal", lambda n: "arsenal" in n),
    ("Liverpool FC", lambda n: "liverpool" in n),
    ("Manchester City", lambda n: "manchester city" in n),
    ("FC Barcelona", lambda n: "barcelona" in n),
    ("Real Madrid", lambda n: "real madrid" in n),
    ("SSC Napoli", lambda n: "napoli" in n),
    ("Paris Saint-Germain", lambda n: "paris saint-germain" in n or n.strip() == "psg"),
    ("Olympique de Marseille", lambda n: "marseille" in n),
]


def canonical(name: str):
    """Map an API club name onto the app's spelling, or None if untracked."""
    if not name:
        return None
    low = name.casefold()
    for canon, matches in TEAM_RULES:
        if matches(low):
            return canon
    return None


def request(url: str, token: str):
    req = urllib.request.Request(url, headers={"X-Auth-Token": token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# /v4/matches refuses a range longer than this ("Specified period must not
# exceed 10 days"), so a fortnight has to be asked for in two windows.
MAX_WINDOW = 10


def windows(start, end):
    """Split [start, end] into spans of at most MAX_WINDOW days."""
    spans = []
    cursor = start
    while cursor < end:
        stop = min(cursor + timedelta(days=MAX_WINDOW), end)
        spans.append((cursor, stop))
        cursor = stop
    return spans


def fetch(token: str, start, end):
    """One request per window, all five competitions at once.

    A fortnight needs two requests; the free tier allows ten per minute, so
    a short pause between them keeps a wide margin.
    """
    codes = ",".join(COMPETITIONS)
    by_id = {}
    for i, (span_from, span_to) in enumerate(windows(start, end)):
        if i:
            time.sleep(7)
        url = (f"{API}?competitions={codes}"
               f"&dateFrom={span_from.isoformat()}&dateTo={span_to.isoformat()}")
        for match in request(url, token).get("matches", []):
            # Windows share a boundary day, so the same match can arrive twice.
            by_id[match.get("id") or id(match)] = match
    return list(by_id.values())


def main() -> int:
    token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
    if not token:
        print("FOOTBALL_DATA_TOKEN is not set — refusing to run.", file=sys.stderr)
        print("Add it under Settings -> Secrets and variables -> Actions.", file=sys.stderr)
        return 1

    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=DAYS)
    date_from = today.isoformat()
    date_to = end.isoformat()

    try:
        raw = fetch(token, today, end)
    except urllib.error.HTTPError as exc:
        # Never echo the response body blindly; print only the status.
        print(f"Request failed with HTTP {exc.code}.", file=sys.stderr)
        if exc.code in (401, 403):
            print("The token was rejected. Check the FOOTBALL_DATA_TOKEN secret.", file=sys.stderr)
        elif exc.code == 429:
            print("Rate limit hit. The job will try again on the next run.", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Could not reach the service: {exc.reason}", file=sys.stderr)
        return 1

    out = []
    for match in raw:
        home = canonical((match.get("homeTeam") or {}).get("name"))
        away = canonical((match.get("awayTeam") or {}).get("name"))
        if not home and not away:
            continue  # neither side is a club we follow

        competition = (match.get("competition") or {}).get("code")
        kickoff = match.get("utcDate")
        if not kickoff:
            continue

        out.append({
            "kickoff": kickoff,
            "league": COMPETITIONS.get(competition, competition or ""),
            # Keep the real opponent name for the side we do not track.
            "home": home or (match.get("homeTeam") or {}).get("name", ""),
            "away": away or (match.get("awayTeam") or {}).get("name", ""),
        })

    out.sort(key=lambda m: m["kickoff"])

    if not out:
        print("No fixtures for the tracked clubs in this window — keeping the previous file.")
        return 0

    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "dateFrom": date_from,
        "dateTo": date_to,
        "matches": out,
    }

    target = os.path.join("public", "fixtures.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Wrote {len(out)} fixtures for {date_from} to {date_to}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
