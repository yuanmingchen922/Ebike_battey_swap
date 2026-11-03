#!/usr/bin/env bash
# Server-side watcher for the R8 fifteen-site chain (author's decision, 2026-10-28):
# when the 48-rider dry run fails only its swap gate (median open site below 3 swaps per evening),
# start the same study at 64 riders / 320 orders automatically, after the k15 dispatcher has finished
# (the optional 16-rider ILP check still runs; k15_search refuses; k15_final / k15_report stay blocked).
# A failed cost gate (cell time, worker memory) or a failed lane stops the watcher: the author decides.
#
#   tmux new-session -d -s r8_escalate "bash ~/battery_swap/deploy/aws/r8_escalate.sh"
#   log: ~/r8_escalate.log
set -uo pipefail
ROOT="$HOME/battery_swap"
PKG="$ROOT/ebike_swap_sim"
L15="$PKG/outputs/cloud_lanes_k15"
L64="$PKG/outputs/cloud_lanes_k15n64"
DRY="$PKG/outputs/r8_k15/dryrun.json"
LOG="$HOME/r8_escalate.log"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
last_done() { grep '^lane DONE' "$1" 2>/dev/null | tail -1; }

log "watcher start (pid $$)"
while :; do
  l="$(last_done "$L15/lane_k15_dryrun.status")"
  [ -n "$l" ] && break
  li="$(last_done "$L15/lane_k15_instances.status")"
  if [ -n "$li" ] && ! echo "$li" | grep -q ' rc=0 '; then log "k15_instances failed ($li); watcher stops"; exit 2; fi
  sleep 60
done
if ! echo "$l" | grep -q ' rc=0 '; then log "k15_dryrun failed ($l); watcher stops"; exit 2; fi
esc="$(python3 -c "import json; print(int(bool(json.load(open('$DRY'))['escalate'])))")"
bad="$(python3 -c "import json; d = json.load(open('$DRY')); print(','.join(k for k, g in d['gates'].items() if not g['ok']))")"
med="$(python3 -c "import json; print(json.load(open('$DRY')).get('median_site_swaps'))")"
log "k15 dry run: escalate=$esc failed gates=[$bad] median site swaps=$med"
if [ "$esc" = 0 ]; then log "no escalation: the 48-rider chain continues"; exit 0; fi
if [ "$bad" != "median_site_swaps" ]; then log "a cost gate failed ($bad): no automatic escalation, the author decides"; exit 3; fi
log "escalating to 64 riders / 320 orders once the k15 dispatcher has finished"
while tmux has-session -t lanes_dispatch 2>/dev/null; do sleep 60; done
log "k15 dispatcher finished; starting the 64-rider chain"
cd "$ROOT" || exit 1
LANES_DIR="$L64" bash "$ROOT/deploy/aws/run_lanes.sh" start "$L64/lanes.txt" --max-threads 12 >> "$LOG" 2>&1
log "64-rider chain start returned rc=$?"
