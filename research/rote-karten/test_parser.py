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


# --- Abrufmethode: curl_cffi oder requests -------------------------------
# Laeuft in beiden Faellen durch — curl_cffi ist optional.
_sess, _art = _c.browser_session()
assert _art in ("curl_cffi", "requests"), _art
assert _sess is not None

# Der wichtigste Punkt: mit curl_cffi setzen wir KEINEN eigenen
# User-Agent. impersonate liefert einen, der zum nachgebildeten
# TLS-Fingerabdruck passt; ein eigener wuerde ihm widersprechen — und
# genau dieser Widerspruch waere selbst ein Erkennungsmerkmal.
assert "User-Agent" not in f.CURL_EXTRA_HEADERS, f.CURL_EXTRA_HEADERS
assert "Accept-Language" in f.CURL_EXTRA_HEADERS

_f = f.FbrefFetcher(pause=f.DEFAULT_PAUSE["fbref"])
assert _f.transport == _art, (_f.transport, _art)
assert _f.pause == 6.0, "die 6-Sekunden-Pause darf nicht verlorengehen"
_ua_gesetzt = _f.session.headers.get("User-Agent")
if _art == "curl_cffi":
    assert _ua_gesetzt != f.BROWSER_HEADERS["User-Agent"]
else:
    assert _ua_gesetzt == f.BROWSER_HEADERS["User-Agent"]

# Offline baut gar keine Verbindung auf.
_fo = f.FbrefFetcher(pause=0, offline=True)
assert _fo.session is None and _fo.transport == "aus"

# Wird requests benutzt, muss die 403-Meldung auf curl_cffi hinweisen.
_alt = _c.http_get
try:
    _c.http_get = lambda url, headers=None, timeout=30, session=None: (403, "Just a moment...")
    _fr = f.FbrefFetcher(pause=0)
    _fr.transport = "requests"
    _fr.RETRY_WAITS = ()
    _fr._sleep = lambda: None
    try:
        _fr._fetch_url("https://fbref.com/x")
        raise AssertionError("haette scheitern muessen")
    except RuntimeError as exc:
        assert "curl_cffi" in str(exc), exc
    _fc = f.FbrefFetcher(pause=0)
    _fc.transport = "curl_cffi"
    _fc.RETRY_WAITS = ()
    _fc._sleep = lambda: None
    try:
        _fc._fetch_url("https://fbref.com/x")
        raise AssertionError("haette scheitern muessen")
    except RuntimeError as exc:
        # Schon aktiv — dann waere der Tipp nur Rauschen.
        assert "pip install curl_cffi" not in str(exc), exc
finally:
    _c.http_get = _alt

print("Abrufmethode ok: %s%s, Pause %.0f s"
      % (_art, " %s" % _c.curl_cffi_version() if _art == "curl_cffi" else "",
         _f.pause))


# --- ESPN ----------------------------------------------------------------
# Spielplan: zwei Haelften, weil ESPN hoechstens ein Jahr am Stueck nimmt
# (20230701-20240731 gibt HTTP 400, 20230701-20240630 geht).
_teile = f.EspnFetcher.schedule_parts("E0", "2324")
assert len(_teile) == 2, _teile
assert _teile[0][0] == "espn_schedule_E0_2324_1.json", _teile
assert "dates=20230701-20231231" in _teile[0][1], _teile
assert "dates=20240101-20240731" in _teile[1][1], _teile
assert f.espn_plays_cache_name("E0-2324-x") == "espn_plays_E0-2324-x.json"

# ESPN darf KEINEN Browser-User-Agent schicken: die Vorgelagerte
# antwortet darauf mit "Access Denied". Genau umgekehrt zu FBref.
_e = f.EspnFetcher(pause=0)
assert "User-Agent" not in _e.session.headers or \
    _e.session.headers.get("User-Agent") != f.BROWSER_HEADERS["User-Agent"], \
    "Browser-User-Agent bei ESPN fuehrt zu 403"

_plan = f.EspnFetcher._parse_schedule({"events": [{
    "id": 671031, "date": "2023-08-11T19:00Z",
    "competitions": [{"id": 671031, "competitors": [
        {"homeAway": "home", "team": {"id": 379, "displayName": "Burnley"}},
        {"homeAway": "away", "team": {"id": 382, "displayName": "Manchester City"}}]}]}]})
assert _plan["2023-08-11|Burnley|Manchester City"]["home_id"] == "379", _plan
print("ESPN-Spielplan ok")

def _play(**kw):
    basis = {"id": "1", "clock": {"displayValue": ""}, "addedClock": {"displayValue": ""},
             "homeScore": 0, "awayScore": 0, "redCard": False, "scoringPlay": False}
    basis.update(kw); return basis

_ref = lambda tid: {"$ref": "http://x/leagues/eng.1/seasons/2023/teams/%s?lang=en" % tid}
_karte = lambda: {"participants": [{"athlete": {"$ref": "http://x/athletes/1"}}]}
_roh = {"items": [
    _play(id="a", scoringPlay=True, clock={"displayValue": "4'"}, homeScore=0, awayScore=1, team=_ref(382)),
    _play(id="b", scoringPlay=True, clock={"displayValue": "36'"}, homeScore=0, awayScore=2, team=_ref(382)),
    _play(id="c", scoringPlay=True, clock={"displayValue": "75'"}, homeScore=0, awayScore=3, team=_ref(382)),
    _play(id="d", redCard=True, clock={"displayValue": "90'+4'"}, homeScore=0, awayScore=3,
          team=_ref(379), **_karte()),
    # Rot ohne Spieler: Trainerkarte oder Artefakt, zaehlt nicht als Unterzahl
    _play(id="e", redCard=True, clock={"displayValue": "43'"}, team=_ref(379), participants=None),
]}
_ev = f.EspnFetcher._parse_events(_roh, "379", "382")
assert len(_ev) == 4, _ev
_rot = [x for x in _ev if x["kind"] == "red"]
assert len(_rot) == 1 and _rot[0]["minute"] == 90 and _rot[0]["extra"] == 4, _rot
assert _rot[0]["side"] == "home", _rot
assert [(g["minute"], g["home_score"], g["away_score"])
        for g in _ev if g["kind"] == "goal"] == [(4,0,1),(36,0,2),(75,0,3)], _ev

_m = {"match_id": "espn-test", "league": "E0", "season": "2324", "date": "2023-08-11",
      "home_team": "Burnley", "away_team": "Manchester City", "fthg": "0", "ftag": "3"}
_zeilen, _p = f.rows_for_reds(_m, _ev, "espn")
assert _p is None and len(_zeilen) == 1
assert (_zeilen[0]["goals_for_at_red"], _zeilen[0]["goals_against_at_red"]) == (0, 3)
assert _zeilen[0]["score_check"] == "ok"
print("ESPN-Ereignisse ok (Gelb-Rot zaehlt, Karte ohne Spieler nicht)")

# Alle drei Quellen sind waehlbar, espn ist der Standard.
assert set(f.DEFAULT_PAUSE) == {"espn", "fbref", "api-football"}, f.DEFAULT_PAUSE
assert isinstance(f.build_fetcher("espn", 0, 0), f.EspnFetcher)
assert isinstance(f.build_fetcher("fbref", 0, 0), f.FbrefFetcher)
print("Drei Quellen waehlbar, FBref weiterhin vorhanden")


print("\nAlle Tests bestanden.")
