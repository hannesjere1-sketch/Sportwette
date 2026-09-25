#!/usr/bin/env bash
# Collect, evaluate and commit in a loop, so one workflow run covers hours.
#
# GitHub drops most runs of a frequent cron (on the first day: 2 of 24 at
# */20), so the schedule only has to start this loop now and then; the loop
# keeps the 15-minute rhythm itself. Expects the fut-data worktree at $DATA.
set -u

DATA=${DATA:-_data}
INTERVAL=${INTERVAL:-900}   # seconds between collections
DURATION=${DURATION:-20700} # 5 h 45 min, under the 6 h job limit
end=$((SECONDS + DURATION))
ok=0

while :; do
  if python3 fut/collect.py "$DATA/fut-prices.csv"; then
    ok=$((ok + 1))
    python3 fut/analyze.py "$DATA/fut-prices.csv" --json "$DATA/fut-analysis.json" > "$DATA/bericht.txt" \
      || echo "Auswertung fehlgeschlagen"
    (
      cd "$DATA" &&
      git add fut-prices.csv fut-analysis.json bericht.txt &&
      git commit -q -m "FUT-Preise $(date -u +%Y-%m-%dT%H:%MZ)" &&
      git push -q origin fut-data
    ) || echo "Sichern fehlgeschlagen"
  fi
  [ $((SECONDS + INTERVAL)) -gt $end ] && break
  sleep "$INTERVAL"
done

# A run that never got a single price means the source is down or changed:
# go red so it gets noticed.
[ "$ok" -gt 0 ]
