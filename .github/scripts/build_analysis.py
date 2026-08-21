#!/usr/bin/env python3
"""Measure one question: after conceding the opening goal early, does the team win?

The trigger, precisely:
  * a tracked club concedes the FIRST goal of the match
  * that goal falls before minute 35
  * the club has not scored at that point — which the first-goal rule guarantees,
    so 1:1 or 2:1 can never qualify
  * one trigger per match at most, and it is the opening goal by definition
  * own goals count as ordinary goals, credited to the side they benefit
  * a hit is a win; a draw and a defeat are both misses

Everything comes from API-Football. Its fixture list already carries the
half-time score, so the run needs no second service — and no matching of club
names across two services, which is where quiet errors would creep in.

The key is read from API_FOOTBALL_KEY and sent as a header. It is never
printed, never written to an output file, and never reaches the page.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HOST = "https://v3.football.api-sports.io"
STATE_PATH = os.path.join("data", "analysis-state.json")
OUT_PATH = os.path.join("public", "analysis.json")

# Requests to spend per run, leaving headroom under the daily allowance of 100.
BUDGET = 95
# The free plan also caps requests per minute; this spacing stays well under it.
PAUSE = 7

LEAGUES = {78: "Bundesliga", 39: "Premier League", 140: "La Liga",
           135: "Serie A", 61: "Ligue 1"}
# API-Football numbers a season by its opening year: 2023 means 2023/24.
SEASONS = [2021, 2022, 2023, 2024, 2025]

TRIGGER_BEFORE_MINUTE = 35

# Exact spellings rather than substrings: "Marseille Consolat" is a different
# club from Marseille, and "Real Madrid Castilla" from Real Madrid. Both
# services' spellings are listed so the table survives a change of source.
TEAM_ALIASES = {
    "FC Bayern München": ["bayern munich", "bayern münchen", "fc bayern münchen",
                          "fc bayern munich"],
    "Borussia Dortmund": ["borussia dortmund", "bv borussia 09 dortmund"],
    "Arsenal": ["arsenal", "arsenal fc"],
    "Liverpool FC": ["liverpool", "liverpool fc"],
    "Manchester City": ["manchester city", "manchester city fc"],
    "FC Barcelona": ["barcelona", "fc barcelona"],
    "Real Madrid": ["real madrid", "real madrid cf"],
    "AC Milan": ["ac milan", "milan"],
    "Inter": ["inter", "internazionale", "inter milan", "fc internazionale milano"],
    "SSC Napoli": ["napoli", "ssc napoli"],
    "Paris Saint-Germain": ["paris saint germain", "paris saint-germain",
                            "paris saint-germain fc", "psg"],
    "Olympique de Marseille": ["marseille", "olympique marseille",
                               "olympique de marseille"],
}

LOOKUP = {alias: canon for canon, names in TEAM_ALIASES.items() for alias in names}


def canonical(name):
    """Map an API club name onto the app's spelling, or None if untracked."""
    if not name:
        return None
    return LOOKUP.get(name.casefold().strip())


class Budget:
    """Counts requests so a run can stop cleanly instead of being cut off."""

    def __init__(self, limit):
        self.left = limit
        self.used = 0

    def take(self):
        if self.left <= 0:
            return False
        self.left -= 1
        self.used += 1
        return True


def call(path, key, budget):
    if not budget.take():
        raise BudgetSpent()
    if budget.used > 1:
        time.sleep(PAUSE)
    req = urllib.request.Request(HOST + path, headers={"x-apisports-key": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    errors = payload.get("errors")
    if errors and errors != []:
        raise ApiRefused(json.dumps(errors, ensure_ascii=False)[:200])
    return payload


class BudgetSpent(Exception):
    pass


class ApiRefused(Exception):
    pass


# ---------------------------------------------------------------- trigger rule

def goal_side(event, home_id):
    """Which side a goal counts for. An own goal counts for the other side."""
    team_id = (event.get("team") or {}).get("id")
    scored_by_home = team_id == home_id
    if (event.get("detail") or "").casefold() == "own goal":
        scored_by_home = not scored_by_home
    return "home" if scored_by_home else "away"


# API-Football files a MISSED penalty as type "Goal" with detail "Missed
# Penalty". Counting those breaks the rebuilt score, so only the details that
# actually put the ball in the net are kept.
SCORING_DETAILS = {"normal goal", "own goal", "penalty"}


def ordered_goals(events, home_id):
    goals = []
    for e in events:
        if (e.get("type") or "").casefold() != "goal":
            continue
        if (e.get("detail") or "").casefold() not in SCORING_DETAILS:
            continue
        t = e.get("time") or {}
        minute = t.get("elapsed")
        if not isinstance(minute, int):
            continue
        goals.append({"minute": minute,
                      "extra": t.get("extra") or 0,
                      "side": goal_side(e, home_id)})
    goals.sort(key=lambda g: (g["minute"], g["extra"]))
    return goals


def evaluate(meta, events):
    """Return (case, skip_reason). A case is None when the match never triggered."""
    goals = ordered_goals(events, meta["homeId"])

    # Reconstructing the score and comparing it with the final score catches a
    # mis-credited own goal or a gap in the event list, instead of letting a
    # wrong trigger through unnoticed.
    rebuilt_home = sum(1 for g in goals if g["side"] == "home")
    rebuilt_away = len(goals) - rebuilt_home
    if (rebuilt_home, rebuilt_away) != (meta["ftHome"], meta["ftAway"]):
        return None, (f"Ereignisse ergeben {rebuilt_home}:{rebuilt_away}, "
                      f"Endstand ist {meta['ftHome']}:{meta['ftAway']}")

    if not goals:
        return None, None

    first = goals[0]
    if first["side"] == meta["side"]:
        return None, None            # our team scored first — never a trigger
    if first["minute"] >= TRIGGER_BEFORE_MINUTE:
        return None, None            # conceded too late

    mine = meta["ftHome"] if meta["side"] == "home" else meta["ftAway"]
    theirs = meta["ftAway"] if meta["side"] == "home" else meta["ftHome"]

    return {
        "fixture": meta["fixture"],
        "date": meta["date"],
        "league": meta["league"],
        "home": meta["home"],
        "away": meta["away"],
        "team": meta["team"],
        "venue": "H" if meta["side"] == "home" else "A",
        "minute": first["minute"],
        "ftHome": meta["ftHome"],
        "ftAway": meta["ftAway"],
        "hit": mine > theirs,
    }, None


# ------------------------------------------------------------------ state file

def blank_state():
    return {"version": 1, "seasons": {"available": [], "unavailable": []},
            "listsFetched": [], "candidates": {}, "cases": {}, "skipped": {},
            # Fixture ids already looked at. The current season is re-fetched on
            # every run, so counting without this would inflate the total.
            "seen": [], "scanned": 0, "updatedAt": None}


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as handle:
            state = json.load(handle)
        if state.get("version") == 1:
            return state
    except (OSError, ValueError):
        pass
    return blank_state()


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


# ------------------------------------------------------------- fixture listing

def collect_fixtures(state, key, budget):
    """Fetch each league-season list once, recording the matches worth checking."""
    for season in SEASONS:
        if season in state["seasons"]["unavailable"]:
            continue
        for league_id, league_name in LEAGUES.items():
            tag = f"{league_id}-{season}"
            # The current season keeps gaining matches, so its list is refreshed.
            if tag in state["listsFetched"] and season != SEASONS[-1]:
                continue
            try:
                data = call(f"/fixtures?league={league_id}&season={season}", key, budget)
            except ApiRefused as exc:
                print(f"  {league_name} {season}: abgelehnt ({exc})")
                if season not in state["seasons"]["unavailable"]:
                    state["seasons"]["unavailable"].append(season)
                break

            items = data.get("response") or []
            if not items:
                print(f"  {league_name} {season}: keine Spiele — Saison nicht abgedeckt")
                if season not in state["seasons"]["unavailable"]:
                    state["seasons"]["unavailable"].append(season)
                break

            added = note_candidates(state, items, league_name)
            if tag not in state["listsFetched"]:
                state["listsFetched"].append(tag)
            if season not in state["seasons"]["available"]:
                state["seasons"]["available"].append(season)
            print(f"  {league_name} {season}: {len(items)} Spiele, {added} neue Kandidaten")


def note_candidates(state, items, league_name):
    """Keep matches where a tracked club conceded in the first half."""
    added = 0
    seen = set(state.setdefault("seen", []))
    for item in items:
        fixture = item.get("fixture") or {}
        if (fixture.get("status") or {}).get("short") != "FT":
            continue
        teams = item.get("teams") or {}
        score = item.get("score") or {}
        half = score.get("halftime") or {}
        full = score.get("fulltime") or {}
        if half.get("home") is None or full.get("home") is None:
            continue

        home_name = (teams.get("home") or {}).get("name")
        away_name = (teams.get("away") or {}).get("name")
        home, away = canonical(home_name), canonical(away_name)
        if not home and not away:
            continue

        fid = str(fixture.get("id"))
        if fid not in seen:
            seen.add(fid)
            state["scanned"] += 1

        for side, mine in (("home", home), ("away", away)):
            if not mine:
                continue
            conceded_first_half = half["away"] if side == "home" else half["home"]
            # No goal against before the break rules out a trigger before
            # minute 35, so the match needs no event lookup at all.
            if not conceded_first_half:
                continue

            keyed = f"{fid}:{side}"
            if keyed in state["candidates"] or keyed in state["cases"] or keyed in state["skipped"]:
                continue
            state["candidates"][keyed] = {
                "fixture": int(fid),
                "side": side,
                "team": mine,
                "date": (fixture.get("date") or "")[:10],
                "league": league_name,
                "home": home or home_name,
                "away": away or away_name,
                "homeId": (teams.get("home") or {}).get("id"),
                "ftHome": full["home"],
                "ftAway": full["away"],
            }
            added += 1

    state["seen"] = sorted(seen)
    return added


# ------------------------------------------------------------------ evaluation

def evaluate_pending(state, key, budget):
    """Spend the remaining budget on event lookups, newest matches first."""
    pending = sorted(state["candidates"].items(),
                     key=lambda kv: kv[1]["date"], reverse=True)
    # One fixture can hold two candidates (both clubs tracked); one lookup serves both.
    cache = {}
    done = 0
    for keyed, meta in pending:
        fid = meta["fixture"]
        try:
            if fid not in cache:
                cache[fid] = (call(f"/fixtures/events?fixture={fid}", key, budget)
                              .get("response") or [])
        except BudgetSpent:
            break
        except ApiRefused as exc:
            state["skipped"][keyed] = f"abgelehnt: {exc}"
            state["candidates"].pop(keyed, None)
            continue

        case, reason = evaluate(meta, cache[fid])
        if reason:
            state["skipped"][keyed] = reason
        else:
            state["cases"][keyed] = case          # None means "no trigger"
        state["candidates"].pop(keyed, None)
        done += 1
    return done


# ---------------------------------------------------------------------- output

def bucket(minute):
    if minute <= 10:
        return "Minute 1–10"
    if minute <= 20:
        return "Minute 11–20"
    return "Minute 21–34"


def summarise(rows):
    total = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    return {"cases": total, "hits": hits, "misses": total - hits,
            "hitRate": round(hits / total * 100, 1) if total else 0.0}


def group(rows, key):
    out = {}
    for row in rows:
        name = key(row)
        entry = out.setdefault(name, {"label": name, "cases": 0, "hits": 0})
        entry["cases"] += 1
        entry["hits"] += 1 if row["hit"] else 0
    for entry in out.values():
        entry["hitRate"] = round(entry["hits"] / entry["cases"] * 100, 1)
    return list(out.values())


def write_output(state):
    rows = [c for c in state["cases"].values() if c]
    rows.sort(key=lambda r: r["date"], reverse=True)

    minute_rows = group(rows, lambda r: bucket(r["minute"]))
    order = {"Minute 1–10": 0, "Minute 11–20": 1, "Minute 21–34": 2}
    minute_rows.sort(key=lambda r: order.get(r["label"], 9))

    checked = len(state["cases"]) + len(state["skipped"])
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0)
                       .isoformat().replace("+00:00", "Z"),
        "seasons": sorted(state["seasons"]["available"]),
        "progress": {
            "checked": checked,
            "total": checked + len(state["candidates"]),
            "pending": len(state["candidates"]),
            "matchesScanned": state["scanned"],
            "skipped": len(state["skipped"]),
        },
        "summary": summarise(rows),
        "byTeam": sorted(group(rows, lambda r: r["team"]),
                         key=lambda r: -r["cases"]),
        "byMinute": minute_rows,
        "byVenue": group(rows, lambda r: "Heim" if r["venue"] == "H" else "Auswärts"),
        "cases": rows,
    }
    save_json(OUT_PATH, payload)
    return payload


def main():
    key = os.environ.get("API_FOOTBALL_KEY", "").strip()
    if not key:
        print("API_FOOTBALL_KEY ist nicht gesetzt.", file=sys.stderr)
        return 1

    state = load_state()
    budget = Budget(BUDGET)

    print("Spiellisten:")
    try:
        collect_fixtures(state, key, budget)
    except BudgetSpent:
        print("  Budget während der Spiellisten aufgebraucht.")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Abbruch: {exc}", file=sys.stderr)

    seen = set()
    for bucket_ in (state["candidates"], state["cases"]):
        for entry in bucket_.values():
            if entry:
                seen.add(entry["team"])
    missing = sorted(set(TEAM_ALIASES) - seen)
    if missing and state["scanned"]:
        print("  Ohne einen einzigen Fall — Schreibweise pruefen: " + ", ".join(missing))

    print(f"\nTor-Abfragen (Budget übrig: {budget.left}):")
    try:
        done = evaluate_pending(state, key, budget)
        print(f"  {done} Spiele ausgewertet")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"  Abbruch nach {budget.used} Anfragen: {exc}", file=sys.stderr)

    state["updatedAt"] = datetime.now(timezone.utc).replace(microsecond=0) \
                                 .isoformat().replace("+00:00", "Z")
    save_json(STATE_PATH, state)
    payload = write_output(state)

    if state["skipped"]:
        kinds = {}
        for reason in state["skipped"].values():
            head = reason.split(",")[0] if "Ereignisse ergeben" in reason else reason
            kind = "Ereignisse passen nicht zum Endstand" if "Endstand" in reason else head
            kinds[kind] = kinds.get(kind, 0) + 1
        print("\nUebersprungen:")
        for kind, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"  {n}x {kind}")

    p, s = payload["progress"], payload["summary"]
    print(f"\nStand: {p['checked']} von {p['total']} geprüft, "
          f"{p['pending']} offen, {p['skipped']} übersprungen")
    print(f"Treffer: {s['hits']} von {s['cases']} Fällen ({s['hitRate']} %)")
    print(f"Anfragen verbraucht: {budget.used}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
