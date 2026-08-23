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

# --- Echter FBref-Spielbericht -------------------------------------------
# Burnley vs. Manchester City, 11.08.2023, von Hand gespeichert.
# Haelt fest, was am echten HTML anders ist als erwartet: FBref schreibt
# die Minute mit &rsquor; und dem typografischen Apostroph U+2019.
SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "data", "sample", "sample.html")
if os.path.isfile(SAMPLE):
    import common
    raw = open(SAMPLE, encoding="utf-8", errors="replace").read()
    real = f.FbrefFetcher._parse_events(raw)
    goals = [e for e in real if e["kind"] == "goal"]
    reds = [e for e in real if e["kind"] == "red"]
    assert len(goals) == 3 and len(reds) == 1, real
    assert [(g["minute"], g["home_score"], g["away_score"]) for g in goals] == \
        [(4, 0, 1), (36, 0, 2), (75, 0, 3)], goals
    assert reds[0]["minute"] == 90 and reds[0]["extra"] == 4, reds
    assert reds[0]["side"] == "home", reds       # Burnley ist Heimteam

    real_match = {"match_id": "E0-2324-2023-08-11-burnley-man-city",
                  "league": "E0", "season": "2324", "date": "2023-08-11",
                  "home_team": "Burnley", "away_team": "Manchester City",
                  "fthg": "0", "ftag": "3"}
    rr, prob = f.rows_for_reds(real_match, real, "fbref")
    assert prob is None and len(rr) == 1, (prob, rr)
    r = rr[0]
    assert r["red_team"] == "Burnley" and r["opponent_team"] == "Manchester City"
    assert (r["red_minute"], r["red_extra"]) == (90, 4), r
    assert (r["goals_for_at_red"], r["goals_against_at_red"]) == (0, 3), r
    assert r["score_check"] == "ok", r
    print("Echter FBref-Spielbericht ok: %s, Minute 90+4, Stand 0:3"
          % r["red_team"])
else:
    print("Hinweis: data/sample/sample.html fehlt — echter Bericht nicht geprueft.")

# --- Echte FBref-Spielplanseite ------------------------------------------
# Premier League 2023/24, von Hand gespeichert. Haelt fest, dass FBref auf
# dieser Seite Kurzformen benutzt ("Nottingham" statt "Nottingham Forest")
# und dass Kopf- und Trennzeilen nicht als Spiele durchrutschen.
SCHEDULE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "sample", "sample_schedule.html")
if os.path.isfile(SCHEDULE):
    import common
    raw_s = open(SCHEDULE, encoding="utf-8", errors="replace").read()
    table = f.FbrefFetcher._parse_schedule(raw_s)
    assert len(table) == 380, "erwartet 380 Spiele, gefunden %d" % len(table)

    # Jedes Spiel aus Phase 1 muss einen Spielbericht finden — sonst passen
    # die Teamnamen der beiden Quellen nicht zusammen.
    fixtures = common.read_csv(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "matches_all.csv"))
    if fixtures:
        missing = [m for m in fixtures
                   if "%s|%s|%s" % (m["date"], m["home_team"],
                                    m["away_team"]) not in table]
        assert not missing, "kein Spielbericht fuer %d Spiele, z. B. %s" % (
            len(missing), missing[0]["match_id"])
        print("Spielplan: alle %d Spiele aus Phase 1 zugeordnet" % len(fixtures))

    # Stichproben: normale Schreibweise und FBref-Kurzform.
    assert table["2023-08-11|Burnley|Manchester City"] == \
        "/en/matches/3a6836b4/Burnley-Manchester-City-August-11-2023-Premier-League"
    assert "2023-08-12|Arsenal|Nottingham Forest" in table, "Kurzform nicht erkannt"
    assert all(k.split("|")[0][:2] == "20" for k in table), \
        "Zeile ohne echtes Datum in der Tabelle"
    print("Echte FBref-Spielplanseite ok: %d Spiele" % len(table))
else:
    print("Hinweis: data/sample/sample_schedule.html fehlt — Spielplan nicht geprueft.")


# --- Browser-Kopfzeilen, Cache-Namen, Wiederholversuche ------------------
for _h in ("User-Agent", "Accept", "Accept-Language", "Accept-Encoding"):
    assert _h in f.BROWSER_HEADERS, "Kopfzeile fehlt: %s" % _h
assert "Chrome/" in f.BROWSER_HEADERS["User-Agent"]
assert "Windows NT" in f.BROWSER_HEADERS["User-Agent"]
# "br" darf nur drinstehen, wenn requests es auch auspacken kann —
# sonst kaeme unlesbarer Zeichensalat zurueck.
import common as _c
assert ("br" in f.BROWSER_HEADERS["Accept-Encoding"]) == _c.have_brotli()
print("Browser-Kopfzeilen ok (Accept-Encoding: %s)"
      % f.BROWSER_HEADERS["Accept-Encoding"])

assert f.schedule_cache_name("E0", "2324") == "schedule_E0_2324.html"
assert f.match_cache_name("E0-2324-2023-08-11-burnley-man-city") == \
    "match_E0-2324-2023-08-11-burnley-man-city.html"
print("Cache-Dateinamen ok")

# Ohne Netz und ohne Datei: klare Meldung mit Dateiname UND Adresse.
_offline = f.FbrefFetcher(pause=0, offline=True)
assert _offline.session is None, "im Offline-Modus darf es keine Verbindung geben"
try:
    _offline._html("match_gibtsnicht.html", "https://fbref.com/en/matches/x")
    raise AssertionError("haette scheitern muessen")
except RuntimeError as exc:
    assert "match_gibtsnicht.html" in str(exc) and "fbref.com" in str(exc), exc
print("Offline-Meldung nennt Dateiname und Adresse")

# Wiederholversuche: 403, dann 403, dann 200 -> Erfolg beim dritten Versuch.
_calls = {"n": 0}
def _flaky(url, headers=None, timeout=30, session=None):
    _calls["n"] += 1
    return (200, "<html>ok</html>") if _calls["n"] == 3 else (403, "Just a moment...")
_real_get = _c.http_get
try:
    _c.http_get = _flaky
    _r = f.FbrefFetcher(pause=0)
    _r.RETRY_WAITS = (0, 0)
    _r._sleep = lambda: None          # Wartezeiten fuer den Test aus
    assert _r._fetch_url("https://fbref.com/x") == "<html>ok</html>"
    assert _calls["n"] == 3, _calls

    # Dreimal 403 -> Aufgabe, aber mit brauchbarer Meldung.
    _c.http_get = lambda url, headers=None, timeout=30, session=None: (403, "Just a moment...")
    _r2 = f.FbrefFetcher(pause=0)
    _r2.RETRY_WAITS = (0, 0)
    _r2._sleep = lambda: None
    try:
        _r2._fetch_url("https://fbref.com/x")
        raise AssertionError("haette scheitern muessen")
    except RuntimeError as exc:
        assert "403" in str(exc) and "--from-cache" in str(exc), exc
finally:
    _c.http_get = _real_get
print("Wiederholversuche ok (2 Wiederholungen, dann klare Meldung)")


print("\nAlle Tests bestanden.")
