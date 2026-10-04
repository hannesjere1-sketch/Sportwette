#!/usr/bin/env bash
# Measure, evaluate and commit in a loop, so one workflow run covers hours.
#
# GitHub drops most runs of a frequent cron, so the schedule only has to start
# this loop now and then. The loop ticks every ten minutes (:05, :15, …):
#   * the first tick of each clock hour measures every card and re-runs the
#     analysis, as before;
#   * every tick re-measures the bargain candidates (fut/recheck.py) — dips are
#     often gone within the hour — and pushes new buys to the phone.
# Expects the fut-data worktree at $DATA.
set -u

DATA=${DATA:-_data}
DURATION=${DURATION:-20700} # 5 h 45 min, under the 6 h job limit
TICK=${TICK:-600}           # seconds between ticks
OFFSET=${OFFSET:-300}       # ticks at :05, :15, … — five minutes past each ten
end=$(( $(date +%s) + DURATION ))
ok=0
tried=0

snapped=""  # clock hour (UTC) of the last full measurement
if [ -f "$DATA/icons-prices.csv" ]; then
  snapped=$(tail -n 1 "$DATA/icons-prices.csv" | cut -c1-13)
fi

tick() {
  local hour
  hour=$(date -u +%Y-%m-%dT%H)
  if [ "$hour" != "$snapped" ]; then
    tried=$((tried + 1))
    snapped=$hour
    if python3 fut/collect.py "$DATA/icons-prices.csv"; then
      ok=$((ok + 1))
      python3 fut/analyze.py "$DATA/icons-prices.csv" --json "$DATA/icons-analysis.json" > "$DATA/bericht.txt" \
        || echo "Auswertung fehlgeschlagen"
    fi
  fi
  # A fresh worktree may have prices but no analysis yet: make one first.
  if [ ! -f "$DATA/icons-analysis.json" ] && [ -f "$DATA/icons-prices.csv" ]; then
    python3 fut/analyze.py "$DATA/icons-prices.csv" --json "$DATA/icons-analysis.json" > "$DATA/bericht.txt" \
      || echo "Auswertung fehlgeschlagen"
  fi
  if [ -f "$DATA/icons-analysis.json" ]; then
    python3 fut/recheck.py "$DATA/icons-analysis.json" "$DATA/icons-live.json" || echo "Nachmessen fehlgeschlagen"
  fi
  (
    cd "$DATA" || exit 1
    for f in icons-prices.csv icons-analysis.json bericht.txt icons-live.json; do
      [ -f "$f" ] && git add "$f"
    done
    git diff --cached --quiet && exit 0
    git commit -q -m "Icons/Heroes $(date -u +%Y-%m-%dT%H:%MZ)" && git push -q origin fut-data
  ) || echo "Sichern fehlgeschlagen"
}

tick
while :; do
  now=$(date +%s)
  next=$(( (now - OFFSET) / TICK * TICK + TICK + OFFSET ))
  [ "$next" -gt "$end" ] && break
  sleep $(( next - now ))
  tick
done

# A run whose every full measurement failed means the source is down or
# changed: go red so it gets noticed.
[ "$tried" -eq 0 ] || [ "$ok" -gt 0 ]
