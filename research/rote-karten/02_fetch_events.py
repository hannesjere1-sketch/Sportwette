#!/usr/bin/env python3
"""Phase 2 — Rote-Karten-Minute, betroffenes Team und Spielstand holen.

Der Abruf steckt hinter EINER Schnittstelle mit ZWEI Implementierungen:

  (a) fbref          Spielberichte von fbref.com auslesen (Standard)
  (b) api-football   v3.football.api-sports.io, Key aus .env

Auswahl per Kommandozeile:  --source fbref | api-football

Der Fortschritt landet in data/events_progress_<set>.json. Ein Neustart
macht dort weiter, wo der letzte Lauf aufgehoert hat — bereits geholte
Spiele werden nicht noch einmal abgefragt.

Ausgabe:
  --set reds      (Standard)  data/red_card_events.csv
  --set baseline              data/baseline_events.csv   (fuer Phase 4)
"""

import argparse
import html as html_module
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import log, warn

# ------------------------------------------------------------- Einstellungen -

FBREF_COMPS = {
    "E0": (9, "Premier-League"),
    "D1": (20, "Bundesliga"),
    "SP1": (12, "La-Liga"),
    "I1": (11, "Serie-A"),
    "F1": (13, "Ligue-1"),
}

API_LEAGUE_IDS = {"E0": 39, "D1": 78, "SP1": 140, "I1": 135, "F1": 61}

API_HOST = "https://v3.football.api-sports.io"

# Sekunden zwischen zwei Anfragen. 6 s bei FBref ist bewusst grosszuegig:
# die Seite ist kostenlos, und wer zu schnell klopft, fliegt raus.
DEFAULT_PAUSE = {"fbref": 6.0, "api-football": 7.0}

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


# ==================================================== Schnittstelle ==========

class Fetcher:
    """Gemeinsame Schnittstelle. Beide Implementierungen liefern dasselbe.

    fetch(match) -> Liste von Ereignissen, je Ereignis ein dict:
        {"minute": int, "extra": int, "kind": "goal"|"red",
         "side": "home"|"away", "home_score": int|None, "away_score": int|None}
    Bei Fehlern: Exception werfen. Der Aufrufer loggt und macht weiter.
    """

    name = "abstract"

    def fetch(self, match):
        raise NotImplementedError

    def budget_left(self):
        return True


def season_years(season):
    """'2324' -> (2023, '2023-2024')"""
    start = 2000 + int(season[:2])
    return start, "%d-%d" % (start, start + 1)


# ==================================================== (a) FBref ==============

TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WS_RE = re.compile(r"\s+")


def strip_tags(raw):
    """HTML-Schnipsel in reinen Text.

    html.unescape kennt die komplette HTML5-Entity-Tabelle. Das ist hier
    wichtig: FBref schreibt die Spielminute mit &rsquor; (nicht &rsquo;),
    und eine handgepflegte Ersetzungsliste uebersieht so etwas.
    """
    text = TAG_RE.sub(" ", raw)
    text = html_module.unescape(text)
    return WS_RE.sub(" ", text).strip()


class FbrefFetcher(Fetcher):
    """Spielberichte von fbref.com auslesen.

    Achtung: FBref sitzt hinter Cloudflare. Aus manchen Umgebungen kommt
    HTTP 403 zurueck (siehe README). Dann bitte --source api-football
    nehmen oder das Skript vom eigenen Rechner aus starten.
    """

    name = "fbref"
    BASE = "https://fbref.com"

    def __init__(self, pause=3.0, cache_path=None):
        # Auch mit --pause 0 wird nie schneller als alle 3 s angefragt.
        self.pause = max(3.0, float(pause))
        self.cache_path = cache_path or os.path.join(
            common.DATA_DIR, "fbref_schedule_cache.json")
        self.schedules = self._load_cache()
        self._schedule_failed = {}   # Liga/Saison -> Fehlermeldung
        self._last_request = 0.0

    # ---- Hoeflichkeit ----------------------------------------------------
    def _sleep(self):
        """Warten, bis seit dem ENDE der letzten Anfrage genug Zeit ist."""
        wait = self.pause - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)

    def _get(self, url):
        self._sleep()
        status, text = common.http_get(url, headers={"User-Agent": USER_AGENT})
        # Uhr erst jetzt stellen: die Pause zaehlt ab dem Ende der Anfrage,
        # sonst frisst eine langsame Antwort die Wartezeit auf.
        self._last_request = time.time()
        if status != 200:
            hint = ""
            if status == 403 or "Just a moment" in text[:2000]:
                hint = (" — FBref blockt den Zugriff (Cloudflare). "
                        "Bitte --source api-football verwenden.")
            raise RuntimeError("FBref HTTP %s fuer %s%s" % (status, url, hint))
        return text

    # ---- Spielplan -> Links auf die Spielberichte ------------------------
    def _load_cache(self):
        try:
            with open(self.cache_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_cache(self):
        try:
            common.write_text(self.cache_path,
                              json.dumps(self.schedules, indent=1))
        except Exception as exc:
            warn("FBref-Cache nicht schreibbar: %s" % exc)

    def _schedule(self, league, season):
        key = "%s-%s" % (league, season)
        if key in self.schedules:
            return self.schedules[key]
        if key in self._schedule_failed:
            # Einmal gescheitert reicht — nicht fuer jedes Spiel neu anklopfen.
            raise RuntimeError(self._schedule_failed[key])
        if league not in FBREF_COMPS:
            raise RuntimeError("Liga %s bei FBref nicht hinterlegt" % league)
        comp_id, comp_slug = FBREF_COMPS[league]
        _, slug = season_years(season)
        url = ("%s/en/comps/%d/%s/schedule/%s-%s-Scores-and-Fixtures"
               % (self.BASE, comp_id, slug, slug, comp_slug))
        log("  FBref-Spielplan holen: %s" % url)
        try:
            html = self._get(url)
            table = self._parse_schedule(html)
        except Exception as exc:
            self._schedule_failed[key] = str(exc)
            raise
        if not table:
            self._schedule_failed[key] = "FBref-Spielplan %s leer/unlesbar" % key
            raise RuntimeError(self._schedule_failed[key])
        self.schedules[key] = table
        self._save_cache()
        return table

    @staticmethod
    def _cell(row_html, stat):
        m = re.search(r'data-stat="%s"[^>]*>(.*?)</t[dh]>' % stat, row_html,
                      re.S)
        return m.group(1) if m else ""

    @classmethod
    def _parse_schedule(cls, html):
        """Aus der Spielplan-Tabelle: Datum + Teams -> Link zum Bericht."""
        table = {}
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
            if 'data-stat="match_report"' not in row:
                continue
            date = strip_tags(cls._cell(row, "date"))
            home = strip_tags(cls._cell(row, "home_team"))
            away = strip_tags(cls._cell(row, "away_team"))
            link = re.search(r'data-stat="match_report".*?href="([^"]+)"',
                             row, re.S)
            # Die Kopfzeile der Tabelle enthaelt ebenfalls eine Zelle
            # data-stat="match_report" und wuerde sonst als Spiel
            # "Home gegen Away" mitgezaehlt. Ein echtes Datum gibt es
            # dort nicht — daran erkennen wir sie.
            if not DATE_RE.match(date or ""):
                continue
            if not (home and away and link):
                continue
            key = "%s|%s|%s" % (date, common.canonical_team(home),
                                common.canonical_team(away))
            table[key] = link.group(1)
        return table

    # ---- Spielbericht ----------------------------------------------------
    def fetch(self, match):
        table = self._schedule(match["league"], match["season"])
        key = "%s|%s|%s" % (match["date"], match["home_team"],
                            match["away_team"])
        href = table.get(key)
        if not href:
            # Datum kann um einen Tag abweichen (Zeitzone der Quelle).
            for delta in ("-1", "+1"):
                alt = shift_date(match["date"], int(delta))
                href = table.get("%s|%s|%s" % (alt, match["home_team"],
                                               match["away_team"]))
                if href:
                    break
        if not href:
            raise RuntimeError("Kein FBref-Spielbericht gefunden fuer %s"
                               % key)
        html = self._get(self.BASE + href if href.startswith("/") else href)
        return self._parse_events(html)

    @staticmethod
    def _parse_events(html):
        start = html.find('id="events_wrap"')
        if start < 0:
            raise RuntimeError("FBref: Ereignisblock nicht gefunden")
        section = html[start:]
        end = section.find('id="team_stats')
        if end > 0:
            section = section[:end]

        events = []
        chunks = re.split(r'<div class="event ([ab])"', section)
        # chunks[0] ist der Text vor dem ersten Ereignis
        for i in range(1, len(chunks) - 1, 2):
            side = "home" if chunks[i] == "a" else "away"
            block = chunks[i + 1]
            icons = re.findall(r'class="event_icon ([a-z_]+)"', block)
            kind = None
            for icon in icons:
                if icon in ("goal", "penalty_goal", "own_goal"):
                    kind = "goal"
                    break
                if icon in ("red_card", "yellow_red_card"):
                    kind = "red"
                    break
            if kind is None:
                continue  # Wechsel, Gelbe Karte usw. interessieren uns nicht

            text = strip_tags(block)
            # 4' oder 90+4' — das Zeichen dahinter ist bei FBref das
            # typografische Apostroph, nicht das gerade ASCII-Zeichen.
            mm = re.search(r"(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*['\u2019\u2032]",
                           text)
            if not mm:
                continue
            minute = int(mm.group(1))
            extra = int(mm.group(2) or 0)

            home_score = away_score = None
            if kind == "goal":
                # FBref schreibt den laufenden Spielstand ans Tor. Den nehmen
                # wir direkt — damit ist auch bei Eigentoren egal, auf welcher
                # Seite FBref sie einsortiert.
                sm = re.search(r"(\d{1,2})\s*:\s*(\d{1,2})", text)
                if sm:
                    home_score, away_score = int(sm.group(1)), int(sm.group(2))
            events.append({"minute": minute, "extra": extra, "kind": kind,
                           "side": side, "home_score": home_score,
                           "away_score": away_score})
        if not events:
            raise RuntimeError("FBref: keine verwertbaren Ereignisse")
        return events


def shift_date(iso, days):
    import datetime
    try:
        d = datetime.date.fromisoformat(iso) + datetime.timedelta(days=days)
        return d.isoformat()
    except Exception:
        return iso


# ==================================================== (b) API-Football ======

# API-Football meldet verschossene Elfmeter als type "Goal" mit
# detail "Missed Penalty" — die duerfen nicht als Tor zaehlen.
SCORING_DETAILS = {"normal goal", "own goal", "penalty"}
RED_DETAILS = {"red card", "second yellow card"}


class ApiFootballFetcher(Fetcher):

    name = "api-football"

    def __init__(self, pause=7.0, budget=95):
        common.load_env()
        self.key = os.environ.get("API_FOOTBALL_KEY", "").strip()
        if not self.key:
            raise RuntimeError(
                "API_FOOTBALL_KEY fehlt. Lege research/rote-karten/.env an "
                "mit der Zeile:  API_FOOTBALL_KEY=dein_key")
        self.pause = float(pause)
        self.budget = int(budget)
        self.used = 0
        self._last_request = 0.0
        self._fixtures = {}

    def budget_left(self):
        return self.used < self.budget

    def _call(self, path, params):
        if not self.budget_left():
            raise RuntimeError("Tagesbudget von %d Anfragen erreicht"
                               % self.budget)
        wait = self.pause - (time.time() - self._last_request)
        if wait > 0:
            time.sleep(wait)

        query = "&".join("%s=%s" % (k, v) for k, v in sorted(params.items()))
        url = "%s%s?%s" % (API_HOST, path, query)
        # Der Key steht ausschliesslich im Header, nie in der URL.
        status, text = common.http_get(url, headers={"x-apisports-key": self.key})
        self._last_request = time.time()   # Pause zaehlt ab dem Ende
        self.used += 1
        if status != 200:
            raise RuntimeError("API-Football HTTP %s (%s)" % (status, text[:160]))
        try:
            payload = json.loads(text)
        except Exception as exc:
            raise RuntimeError("API-Football: Antwort kein JSON (%s)" % exc)
        errors = payload.get("errors")
        if errors and not isinstance(errors, list):
            raise RuntimeError("API-Football meldet: %s" % errors)
        return payload.get("response") or []

    # ---- Spielplan der Liga einmal holen und zwischenspeichern -----------
    def _fixture_index(self, league, season):
        key = "%s-%s" % (league, season)
        if key in self._fixtures:
            return self._fixtures[key]
        path = os.path.join(common.DATA_DIR, "api_fixtures_%s.json" % key)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                index = json.load(fh)
            self._fixtures[key] = index
            return index
        except Exception:
            pass
        if league not in API_LEAGUE_IDS:
            raise RuntimeError("Liga %s bei API-Football nicht hinterlegt"
                               % league)
        year, _ = season_years(season)
        log("  API-Football-Spielplan holen (1 Anfrage): %s" % key)
        rows = self._call("/fixtures", {"league": API_LEAGUE_IDS[league],
                                        "season": year})
        index = {}
        for row in rows:
            try:
                fixture = row["fixture"]
                teams = row["teams"]
                date = (fixture.get("date") or "")[:10]
                k = "%s|%s|%s" % (date,
                                  common.canonical_team(teams["home"]["name"]),
                                  common.canonical_team(teams["away"]["name"]))
                index[k] = {"id": fixture["id"],
                            "home_id": teams["home"]["id"],
                            "away_id": teams["away"]["id"]}
            except Exception as exc:
                warn("API-Football: Spielplanzeile uebersprungen (%s)" % exc)
        common.write_text(path, json.dumps(index, indent=1))
        self._fixtures[key] = index
        return index

    def fetch(self, match):
        index = self._fixture_index(match["league"], match["season"])
        key = "%s|%s|%s" % (match["date"], match["home_team"],
                            match["away_team"])
        entry = index.get(key)
        if not entry:
            for delta in (-1, 1):
                entry = index.get("%s|%s|%s" % (shift_date(match["date"], delta),
                                                match["home_team"],
                                                match["away_team"]))
                if entry:
                    break
        if not entry:
            raise RuntimeError("Kein API-Football-Spiel gefunden fuer %s" % key)

        rows = self._call("/fixtures/events", {"fixture": entry["id"]})
        return self._parse_events(rows, entry["home_id"])

    @staticmethod
    def _parse_events(rows, home_id):
        events = []
        for row in rows:
            try:
                etype = (row.get("type") or "").casefold()
                detail = (row.get("detail") or "").casefold()
                team_id = (row.get("team") or {}).get("id")
                elapsed = (row.get("time") or {}).get("elapsed")
                extra = (row.get("time") or {}).get("extra") or 0
                if elapsed is None:
                    continue
                is_home = team_id == home_id
                if etype == "goal" and detail in SCORING_DETAILS:
                    if detail == "own goal":
                        is_home = not is_home  # zaehlt fuer den Gegner
                    kind = "goal"
                elif etype == "card" and detail in RED_DETAILS:
                    kind = "red"
                else:
                    continue
                events.append({"minute": int(elapsed), "extra": int(extra),
                               "kind": kind,
                               "side": "home" if is_home else "away",
                               "home_score": None, "away_score": None})
            except Exception as exc:
                warn("API-Football: Ereignis uebersprungen (%s)" % exc)
        if not events:
            raise RuntimeError("API-Football: keine verwertbaren Ereignisse")
        return events


# ==================================================== Auswertung ============

def sort_key(ev):
    return (ev["minute"], ev.get("extra") or 0, 0 if ev["kind"] == "goal" else 1)


def with_running_score(events):
    """Jedem Tor den Spielstand NACH dem Tor zuordnen.

    Wenn die Quelle den Stand mitliefert (FBref), wird der genommen,
    sonst wird gezaehlt.
    """
    out = sorted(events, key=sort_key)
    h = a = 0
    for ev in out:
        if ev["kind"] != "goal":
            continue
        if ev["home_score"] is not None and ev["away_score"] is not None:
            h, a = ev["home_score"], ev["away_score"]
        else:
            if ev["side"] == "home":
                h += 1
            else:
                a += 1
            ev["home_score"], ev["away_score"] = h, a
    return out


def score_before(events, minute, extra=0):
    """Spielstand exakt in dem Moment, in dem das Ereignis faellt."""
    h = a = 0
    for ev in events:
        if ev["kind"] != "goal":
            continue
        if sort_key(ev) > (minute, extra, 1):
            break
        h, a = ev["home_score"], ev["away_score"]
    return h, a


# ==================================================== Ablauf ================

def load_progress(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_progress(path, progress):
    common.write_text(path, json.dumps(progress, indent=1))


def build_fetcher(source, pause, budget):
    if source == "fbref":
        return FbrefFetcher(pause=pause)
    if source == "api-football":
        return ApiFootballFetcher(pause=pause, budget=budget)
    raise RuntimeError("Unbekannte Quelle: %s" % source)


RED_FIELDS = [
    "match_id", "league", "season", "date", "home_team", "away_team",
    "red_minute", "red_extra", "red_side", "red_team", "opponent_team",
    "goals_for_at_red", "goals_against_at_red",
    "is_first_red", "own_reds_before", "opp_reds_before",
    "final_home_goals", "final_away_goals", "score_check", "source",
]

BASE_FIELDS = ["match_id", "league", "season", "date",
               "minute", "extra", "home_score", "away_score", "source"]


def rows_for_reds(match, events, source):
    events = with_running_score(events)
    rows = []
    reds = [e for e in events if e["kind"] == "red"]
    if not reds:
        return rows, "keine Rote Karte in den Ereignissen"

    # Selbstpruefung: nachgezaehlter Endstand gegen den gemeldeten Endstand.
    fh = int(match["fthg"] or 0)
    fa = int(match["ftag"] or 0)
    goals = [e for e in events if e["kind"] == "goal"]
    if goals:
        last = goals[-1]
        check = "ok" if (last["home_score"], last["away_score"]) == (fh, fa) \
            else "abweichung"
    else:
        check = "ok" if (fh, fa) == (0, 0) else "abweichung"

    home_reds = away_reds = 0
    for i, red in enumerate(sorted(reds, key=sort_key)):
        h, a = score_before(events, red["minute"], red.get("extra") or 0)
        if red["side"] == "home":
            team, opp = match["home_team"], match["away_team"]
            gf, ga = h, a
            own_before, opp_before = home_reds, away_reds
        else:
            team, opp = match["away_team"], match["home_team"]
            gf, ga = a, h
            own_before, opp_before = away_reds, home_reds
        rows.append({
            "match_id": match["match_id"], "league": match["league"],
            "season": match["season"], "date": match["date"],
            "home_team": match["home_team"], "away_team": match["away_team"],
            "red_minute": red["minute"], "red_extra": red.get("extra") or 0,
            "red_side": red["side"], "red_team": team, "opponent_team": opp,
            "goals_for_at_red": gf, "goals_against_at_red": ga,
            "is_first_red": 1 if i == 0 else 0,
            "own_reds_before": own_before, "opp_reds_before": opp_before,
            "final_home_goals": fh, "final_away_goals": fa,
            "score_check": check, "source": source,
        })
        if red["side"] == "home":
            home_reds += 1
        else:
            away_reds += 1
    return rows, None


def rows_for_baseline(match, events, source):
    events = with_running_score(events)
    rows = []
    for ev in events:
        if ev["kind"] != "goal":
            continue
        rows.append({
            "match_id": match["match_id"], "league": match["league"],
            "season": match["season"], "date": match["date"],
            "minute": ev["minute"], "extra": ev.get("extra") or 0,
            "home_score": ev["home_score"], "away_score": ev["away_score"],
            "source": source,
        })
    return rows, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["fbref", "api-football"],
                    default="fbref", help="Datenquelle (Standard: fbref)")
    ap.add_argument("--set", dest="dataset", choices=["reds", "baseline"],
                    default="reds",
                    help="reds = Spiele mit Roter Karte, "
                         "baseline = Spiele ohne (fuer Phase 4)")
    ap.add_argument("--limit", type=int, default=0,
                    help="hoechstens so viele Spiele in diesem Lauf")
    ap.add_argument("--pause", type=float, default=None,
                    help="Sekunden Pause zwischen Anfragen")
    ap.add_argument("--budget", type=int, default=95,
                    help="max. API-Anfragen (nur api-football)")
    ap.add_argument("--retry-errors", action="store_true",
                    help="frueher fehlgeschlagene Spiele erneut versuchen")
    args = ap.parse_args()

    pause = args.pause if args.pause is not None else DEFAULT_PAUSE[args.source]

    if args.dataset == "reds":
        src_csv = os.path.join(common.DATA_DIR, "matches_with_reds.csv")
        out_csv = os.path.join(common.DATA_DIR, "red_card_events.csv")
        fields, builder = RED_FIELDS, rows_for_reds
    else:
        src_csv = os.path.join(common.DATA_DIR, "matches_all.csv")
        out_csv = os.path.join(common.DATA_DIR, "baseline_events.csv")
        fields, builder = BASE_FIELDS, rows_for_baseline

    matches = common.read_csv(src_csv)
    if not matches:
        warn("%s fehlt oder ist leer — bitte zuerst 01_fetch_matches.py laufen "
             "lassen." % os.path.basename(src_csv))
        return 1
    if args.dataset == "baseline":
        matches = [m for m in matches
                   if int(m.get("hr") or 0) == 0 and int(m.get("ar") or 0) == 0]

    progress_path = os.path.join(common.DATA_DIR,
                                 "events_progress_%s.json" % args.dataset)
    progress = load_progress(progress_path)
    log("Fortschritt: %d Spiele bereits abgefragt." % len(progress))

    todo = []
    for m in matches:
        entry = progress.get(m["match_id"])
        if entry and entry.get("status") == "ok":
            continue
        if entry and entry.get("status") == "error" and not args.retry_errors:
            continue
        todo.append(m)
    if args.limit:
        todo = todo[: args.limit]
    log("Offen in diesem Lauf: %d von %d Spielen." % (len(todo), len(matches)))

    try:
        fetcher = build_fetcher(args.source, pause, args.budget)
    except Exception as exc:
        warn(str(exc))
        return 1
    log("Quelle: %s, Pause %.1f s" % (fetcher.name, pause))

    done = failed = 0
    in_a_row = 0
    for i, match in enumerate(todo, start=1):
        if not fetcher.budget_left():
            log("Budget aufgebraucht — Rest beim naechsten Lauf.")
            break
        try:
            events = fetcher.fetch(match)
            progress[match["match_id"]] = {
                "status": "ok", "source": fetcher.name,
                "events": events, "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            done += 1
            in_a_row = 0
        except Exception as exc:
            # Ein kaputtes Spiel darf den Lauf nicht killen.
            warn("%s: %s" % (match["match_id"], exc))
            progress[match["match_id"]] = {
                "status": "error", "source": fetcher.name, "error": str(exc),
                "fetched_at": time.strftime("%Y-%m-%d %H:%M"),
            }
            failed += 1
            in_a_row += 1
            if in_a_row >= 5:
                # Einzelne kaputte Spiele ueberspringen wir — aber wenn nichts
                # mehr geht (Quelle blockt, Netz weg), hat Weiterlaufen keinen
                # Sinn. Der Fortschritt bleibt erhalten.
                log("Abbruch: 5 Fehler in Folge. Fortschritt ist gesichert, "
                    "spaeter mit --retry-errors erneut versuchen.")
                save_progress(progress_path, progress)
                break
        # Nach JEDEM Spiel sichern. Wer den Lauf abbricht oder wem der
        # Rechner abstuerzt, verliert hoechstens dieses eine Spiel.
        save_progress(progress_path, progress)
        if i % 5 == 0 or i == len(todo):
            log("  %d/%d abgefragt (%d ok, %d Fehler)"
                % (i, len(todo), done, failed))
    save_progress(progress_path, progress)

    # ---- Ausgabe aus dem gesamten Fortschritt neu aufbauen ---------------
    by_id = {m["match_id"]: m for m in matches}
    out_rows = []
    for match_id, entry in progress.items():
        if entry.get("status") != "ok" or match_id not in by_id:
            continue
        try:
            rows, problem = builder(by_id[match_id], entry["events"],
                                    entry.get("source", "?"))
            if problem:
                warn("%s: %s" % (match_id, problem))
            out_rows.extend(rows)
        except Exception as exc:
            warn("%s: Auswertung fehlgeschlagen (%s)" % (match_id, exc))

    out_rows.sort(key=lambda r: (r["date"], r["match_id"]))
    common.write_csv(out_csv, out_rows, fields)
    log("Geschrieben: %s (%d Zeilen)"
        % (os.path.relpath(out_csv, common.HERE), len(out_rows)))
    if args.dataset == "reds":
        bad = sum(1 for r in out_rows if r["score_check"] != "ok")
        if bad:
            log("Hinweis: %d Zeilen mit Spielstand-Abweichung "
                "(werden in Phase 3 aussortiert)." % bad)
    common.error_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
