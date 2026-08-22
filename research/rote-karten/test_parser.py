#!/usr/bin/env python3
"""Selbsttest ohne Netz: prueft beide Parser und die Auswertungslogik.

    python3 test_parser.py

Braucht keine Internetverbindung und keinen API-Key.
"""

import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
f = importlib.import_module("02_fetch_events")

# --- FBref-Spielbericht: kuenstliches HTML im echten Aufbau ---------------
html = """
<div id="events_wrap"><div class="event_header">...</div>
<div class="event a">
 <div>12&rsquo;&nbsp;&middot;&nbsp;1&nbsp;<small>:</small>&nbsp;0</div>
 <div class="event_icon goal"></div><div>Foden</div>
</div>
<div class="event b">
 <div>29&rsquo;&nbsp;&middot;&nbsp;1&nbsp;<small>:</small>&nbsp;1</div>
 <div class="event_icon own_goal"></div><div>Dias</div>
</div>
<div class="event b">
 <div>41&rsquo;</div>
 <div class="event_icon yellow_red_card"></div><div>Rice</div>
</div>
<div class="event a">
 <div>45+2&rsquo;&nbsp;&middot;&nbsp;2&nbsp;<small>:</small>&nbsp;1</div>
 <div class="event_icon penalty_goal"></div><div>Haaland</div>
</div>
<div class="event a">
 <div>73&rsquo;</div><div class="event_icon yellow_card"></div><div>Rodri</div>
</div>
<div id="team_stats">...</div>
"""
ev = f.FbrefFetcher._parse_events(html)
assert len(ev) == 4, ev
assert ev[0] == {"minute":12,"extra":0,"kind":"goal","side":"home","home_score":1,"away_score":0}, ev[0]
assert ev[2]["kind"] == "red" and ev[2]["side"] == "away" and ev[2]["minute"] == 41, ev[2]
assert ev[3]["minute"] == 45 and ev[3]["extra"] == 2, ev[3]
print("FBref-Parser ok:", ev)

# --- Spielplan-Tabelle ----------------------------------------------------
sched = """<tr><td data-stat="date"><a href="/x">2023-08-11</a></td>
<td data-stat="home_team"><a href="/y">Burnley</a></td>
<td data-stat="away_team"><a href="/z">Manchester City</a></td>
<td data-stat="match_report"><a href="/en/matches/abc123/Burnley-Man-City">Match Report</a></td></tr>"""
tbl = f.FbrefFetcher._parse_schedule(sched)
assert tbl == {"2023-08-11|Burnley|Manchester City": "/en/matches/abc123/Burnley-Man-City"}, tbl
print("Spielplan-Parser ok")

# --- API-Football-Ereignisse ---------------------------------------------
rows = [
 {"type":"Goal","detail":"Normal Goal","team":{"id":50},"time":{"elapsed":12,"extra":None}},
 {"type":"Goal","detail":"Missed Penalty","team":{"id":50},"time":{"elapsed":20,"extra":None}},
 {"type":"Goal","detail":"Own Goal","team":{"id":50},"time":{"elapsed":29,"extra":None}},
 {"type":"Card","detail":"Second Yellow card","team":{"id":42},"time":{"elapsed":41,"extra":None}},
 {"type":"Card","detail":"Yellow Card","team":{"id":50},"time":{"elapsed":44,"extra":None}},
 {"type":"Goal","detail":"Penalty","team":{"id":50},"time":{"elapsed":45,"extra":2}},
]
ev2 = f.ApiFootballFetcher._parse_events(rows, home_id=50)
assert len(ev2) == 4, ev2
assert ev2[1]["side"] == "away", ev2[1]   # Eigentor zaehlt fuer den Gegner
assert ev2[2]["kind"] == "red" and ev2[2]["side"] == "away"
print("API-Parser ok (verschossener Elfer ignoriert, Eigentor gedreht)")

# --- Spielstand + Zeilenbau ----------------------------------------------
match = {"match_id":"m1","league":"E0","season":"2324","date":"2023-08-11",
         "home_team":"Manchester City","away_team":"Arsenal","fthg":"2","ftag":"1"}
rows, problem = f.rows_for_reds(match, f.with_running_score(ev2), "api-football")
assert problem is None, problem
assert len(rows) == 1
r = rows[0]
assert r["red_team"] == "Arsenal" and r["red_minute"] == 41
assert (r["goals_for_at_red"], r["goals_against_at_red"]) == (1, 1), r
assert r["score_check"] == "ok", r
assert r["is_first_red"] == 1
print("Zeilenbau ok:", r["red_team"], r["red_minute"], r["goals_for_at_red"], ":", r["goals_against_at_red"], r["score_check"])

# --- Selbstpruefung schlaegt an, wenn der Endstand nicht passt ------------
bad = dict(match); bad["fthg"] = "5"
rows_bad, _ = f.rows_for_reds(bad, f.with_running_score(ev2), "x")
assert rows_bad[0]["score_check"] == "abweichung"
print("Selbstpruefung ok")

# --- Baseline-Zeilen ------------------------------------------------------
brows, _ = f.rows_for_baseline(match, f.with_running_score(ev2), "x")
assert [ (b["minute"], b["home_score"], b["away_score"]) for b in brows ] == [(12,1,0),(29,1,1),(45,2,1)], brows
print("Baseline-Zeilen ok")
print("\nAlle Tests bestanden.")
