"""Gemeinsame Helfer fuer die Rote-Karten-Studie.

Bewusst nur Standardbibliothek plus `requests` — in dieser Umgebung sind
pandas, numpy, scipy und BeautifulSoup nicht installiert.
"""

import csv
import math
import os
import re
import sys
import time

try:
    import requests
except ImportError:  # pragma: no cover - Hinweis statt Absturz
    requests = None


HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RESULTS_DIR = os.path.join(HERE, "results")


# ---------------------------------------------------------------- Logging ---

_ERRORS = []


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def warn(msg):
    """Fehler protokollieren statt abbrechen."""
    _ERRORS.append(msg)
    print("[%s] FEHLER: %s" % (time.strftime("%H:%M:%S"), msg),
          file=sys.stderr, flush=True)


def error_summary():
    if not _ERRORS:
        log("Keine Fehler.")
        return
    log("%d Fehler waehrend des Laufs:" % len(_ERRORS))
    for e in _ERRORS[:20]:
        log("  - %s" % e)
    if len(_ERRORS) > 20:
        log("  ... und %d weitere" % (len(_ERRORS) - 20))


# ------------------------------------------------------------------- HTTP ---

def new_session(headers=None):
    """Eine wiederverwendbare Verbindung mit festen Kopfzeilen.

    Wichtig gegenueber Cloudflare: eine Session behaelt die Cookies, die
    der Server beim ersten Aufruf setzt. Einzelne, voneinander unabhaengige
    Anfragen wirken dagegen wie ein Bot.
    """
    if requests is None:
        return None
    session = requests.Session()
    if headers:
        session.headers.update(headers)
    return session


# Welchen Browser curl_cffi nachbilden soll, wenn es installiert ist.
CURL_IMPERSONATE = "chrome"


def curl_cffi_version():
    """Version von curl_cffi — oder None, wenn es nicht installiert ist."""
    try:
        import curl_cffi
    except ImportError:
        return None
    return getattr(curl_cffi, "__version__", "unbekannt")


def browser_session(impersonate=CURL_IMPERSONATE):
    """Verbindung fuer Seiten, die Bots aussperren. Gibt (Session, Art).

    Cloudflare prueft nicht nur die Kopfzeilen, sondern auch den
    TLS-Fingerabdruck: die Reihenfolge der Cipher-Suites und
    Erweiterungen im Handshake. Python-requests hat da einen ganz
    eigenen, sofort erkennbaren Fingerabdruck — auch mit perfekten
    Browser-Kopfzeilen.

    curl_cffi bildet den Handshake echter Browser nach. Ist es
    installiert, nehmen wir es; sonst faellt alles auf requests
    zurueck und laeuft weiter, nur eben leichter erkennbar.
    """
    try:
        from curl_cffi import requests as curl_requests
    except ImportError:
        return new_session(), "requests"
    try:
        return curl_requests.Session(impersonate=impersonate), "curl_cffi"
    except Exception as exc:
        # Zum Beispiel ein Browsername, den diese Version nicht kennt.
        warn("curl_cffi vorhanden, aber nicht nutzbar (%s) — weiter mit "
             "requests." % exc)
        return new_session(), "requests"


def http_get(url, headers=None, timeout=30, session=None):
    """Ein GET-Aufruf. Gibt (status, text) zurueck, wirft nichts."""
    if requests is None:
        return 0, "requests ist nicht installiert (pip install requests)"
    verify = os.environ.get("SSL_CERT_FILE") or True
    try:
        caller = session or requests
        r = caller.get(url, headers=headers or {}, timeout=timeout,
                       verify=verify)
        return r.status_code, r.text
    except Exception as exc:  # Netzfehler duerfen den Lauf nicht killen
        return 0, str(exc)


def have_brotli():
    """Kann requests brotli-komprimierte Antworten auspacken?"""
    for name in ("brotli", "brotlicffi"):
        try:
            __import__(name)
            return True
        except ImportError:
            continue
    return False


def load_env(path=None):
    """Liest eine .env-Datei (KEY=VALUE pro Zeile) in os.environ."""
    path = path or os.path.join(HERE, ".env")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# ------------------------------------------------------------------- CSV ----

def read_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ------------------------------------------------------- Teamnamen-Abgleich --

# Kanonischer Name -> alle Schreibweisen, die uns begegnen koennen
# (football-data.co.uk, FBref, API-Football).
TEAM_ALIASES = {
    "Arsenal": ["arsenal"],
    "Aston Villa": ["aston villa", "villa"],
    "Bournemouth": ["bournemouth", "afc bournemouth"],
    "Brentford": ["brentford"],
    "Brighton": ["brighton", "brighton and hove albion",
                 "brighton & hove albion", "brighton hove albion"],
    "Burnley": ["burnley"],
    "Chelsea": ["chelsea"],
    "Crystal Palace": ["crystal palace"],
    "Everton": ["everton"],
    "Fulham": ["fulham"],
    "Ipswich": ["ipswich", "ipswich town"],
    "Leeds": ["leeds", "leeds united"],
    "Leicester": ["leicester", "leicester city"],
    "Liverpool": ["liverpool"],
    "Luton": ["luton", "luton town"],
    "Manchester City": ["man city", "manchester city"],
    "Manchester United": ["man united", "man utd", "manchester utd",
                          "manchester united"],
    "Newcastle": ["newcastle", "newcastle united", "newcastle utd"],
    # FBref schreibt auf der Spielplanseite nur "Nottingham".
    "Nottingham Forest": ["nott m forest", "nottm forest", "nott ham forest",
                          "nottingham forest", "nottingham"],
    "Sheffield United": ["sheffield united", "sheffield utd"],
    "Southampton": ["southampton"],
    "Sunderland": ["sunderland"],
    "Tottenham": ["tottenham", "tottenham hotspur", "spurs"],
    "West Ham": ["west ham", "west ham united", "west ham utd"],
    "Wolves": ["wolves", "wolverhampton", "wolverhampton wanderers"],
}

_SUFFIXES = (" fc", " afc", " cf", " sc", " ac", " bc")


def normalise_team(name):
    """Rohnamen auf eine vergleichbare Form bringen."""
    if not name:
        return ""
    s = name.strip().casefold()
    s = (s.replace("ä", "a").replace("ö", "o").replace("ü", "u")
           .replace("ß", "ss").replace("é", "e").replace("á", "a"))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    for suf in _SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    for pre in ("fc ", "afc ", "ac ", "as ", "ss ", "ssc ", "sc "):
        if s.startswith(pre):
            s = s[len(pre):].strip()
    s = re.sub(r"\butd\b", "united", s)
    return re.sub(r"\s+", " ", s)


_LOOKUP = {}
for _canon, _names in TEAM_ALIASES.items():
    for _n in _names:
        _LOOKUP[normalise_team(_n)] = _canon
    _LOOKUP[normalise_team(_canon)] = _canon


def canonical_team(name):
    """Kanonischer Name, wenn bekannt — sonst die normalisierte Form.

    Kein Abbruch bei unbekannten Vereinen: neue Ligen funktionieren
    weiter, sie werden dann eben ueber die normalisierte Form verglichen.
    """
    n = normalise_team(name)
    return _LOOKUP.get(n, n)


def same_team(a, b):
    return canonical_team(a) == canonical_team(b)


# ---------------------------------------------------------------- Statistik --

def wilson(successes, total, z=1.96):
    """95%-Konfidenzintervall nach Wilson. Nur math aus der Stdlib."""
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    margin = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
    return ((centre - margin) / denom, (centre + margin) / denom)


def fair_probs(odds_home, odds_draw, odds_away):
    """Buchmacher-Marge herausrechnen.

    1/Quote je Ausgang aufsummieren, dann jeden Wert durch die Summe teilen.
    Ergebnis: drei Wahrscheinlichkeiten, die sich exakt zu 1 addieren.
    """
    try:
        oh, od, oa = float(odds_home), float(odds_draw), float(odds_away)
    except (TypeError, ValueError):
        return None
    if min(oh, od, oa) <= 1.0:
        return None
    raw = (1.0 / oh, 1.0 / od, 1.0 / oa)
    total = sum(raw)
    if total <= 0:
        return None
    return tuple(x / total for x in raw)


# --------------------------------------------------------------- Gruppen -----

MINUTE_BUCKETS = [
    (0, 15, "0-15"),
    (16, 30, "16-30"),
    (31, 45, "31-45"),
    (46, 60, "46-60"),
    (61, 75, "61-75"),
    (76, 200, "76+"),
]

# Referenzminute je Bucket — gebraucht fuer die Vergleichsgruppe in 04.
BUCKET_REFERENCE_MINUTE = {
    "0-15": 8, "16-30": 23, "31-45": 38,
    "46-60": 53, "61-75": 68, "76+": 83,
}

MINUTE_ORDER = [b[2] for b in MINUTE_BUCKETS]
SCORE_ORDER = ["fuehrt", "unentschieden", "1 zurueck", "2+ zurueck"]
STRENGTH_ORDER = ["<1.50", "1.50-2.50", ">2.50"]
VENUE_ORDER = ["heim", "auswaerts"]


def minute_bucket(minute):
    for lo, hi, label in MINUTE_BUCKETS:
        if lo <= minute <= hi:
            return label
    return None


def score_state(goals_for, goals_against):
    diff = goals_for - goals_against
    if diff > 0:
        return "fuehrt"
    if diff == 0:
        return "unentschieden"
    if diff == -1:
        return "1 zurueck"
    return "2+ zurueck"


def strength_bucket(fair_odds):
    if fair_odds is None:
        return None
    if fair_odds < 1.50:
        return "<1.50"
    if fair_odds <= 2.50:
        return "1.50-2.50"
    return ">2.50"


def de(x, digits=1):
    """Zahl mit deutschem Komma."""
    return ("%.*f" % (digits, x)).replace(".", ",")
