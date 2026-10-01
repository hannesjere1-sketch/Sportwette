#!/usr/bin/env bash
# Collect, evaluate and commit once an hour, so one workflow run covers hours.
#
# GitHub drops most runs of a frequent cron, so the schedule only has to start
# this loop now and then; the loop itself takes a snapshot at five past every
# hour. Expects the fut-data worktree at $DATA.
set -u

DATA=${DATA:-_data}
DURATION=${DURATION:-20700} # 5 h 45 min, under the 6 h job limit
MINUTE=${MINUTE:-5}         # minute past the hour to take the snapshot at
end=$(( $(date +%s) + DURATION ))
ok=0
tried=0

snapped=""  # clock hour (UTC) of this run's last snapshot

snapshot() {
  tried=$((tried + 1))
  snapped=$(date -u +%Y-%m-%dT%H)
  if python3 fut/collect.py "$DATA/icons-prices.csv"; then
    ok=$((ok + 1))
    python3 fut/analyze.py "$DATA/icons-prices.csv" --json "$DATA/icons-analysis.json" > "$DATA/bericht.txt" \
      || echo "Auswertung fehlgeschlagen"
    (
      cd "$DATA" &&
      git add icons-prices.csv icons-analysis.json bericht.txt &&
      git commit -q -m "Icons/Heroes $(date -u +%Y-%m-%dT%H:%MZ)" &&
      git push -q origin fut-data
    ) || echo "Sichern fehlgeschlagen"
  fi
}

# One snapshot per clock hour: skip the start if this hour is already covered.
last_hour=""
if [ -f "$DATA/icons-prices.csv" ]; then
  last_hour=$(tail -n 1 "$DATA/icons-prices.csv" | cut -c1-13)
fi
snapped=$last_hour
[ "$last_hour" != "$(date -u +%Y-%m-%dT%H)" ] && snapshot

while :; do
  now=$(date +%s)
  next=$(( now / 3600 * 3600 + MINUTE * 60 ))
  [ "$next" -le "$now" ] && next=$(( next + 3600 ))
  # Started just before :05 and already snapped this hour: wait for the next.
  [ "$(date -u -d "@$next" +%Y-%m-%dT%H)" = "$snapped" ] && next=$(( next + 3600 ))
  [ "$next" -gt "$end" ] && break
  sleep $(( next - now ))
  snapshot
done

# A run whose every snapshot failed means the source is down or changed:
# go red so it gets noticed.
[ "$tried" -eq 0 ] || [ "$ok" -gt 0 ]
