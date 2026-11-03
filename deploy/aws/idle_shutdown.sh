#!/usr/bin/env bash
# Stop the instance (EBS kept) once nothing has run for IDLE_MAX minutes, to save budget.
# Started at boot by cron (@reboot nohup /home/ubuntu/idle_shutdown.sh); one copy only (flock).
# Busy = an experiment process, a running lane (tmux session lane_*), pytest or the r7 probe.
# A lane dispatcher on its own no longer counts as busy (fix of 2026-10-30: a dispatcher waiting
# behind a failed lane could keep an idle instance running).
IDLE_MAX=${IDLE_MAX:-60}
exec 9>/tmp/idle_shutdown.lock
flock -n 9 || exit 0
idle=0
while true; do
  if pgrep -f "experiments/" >/dev/null || tmux ls 2>/dev/null | grep -q '^lane_' \
     || pgrep -f "pytest" >/dev/null || pgrep -f "r7_probe" >/dev/null; then idle=0; else idle=$((idle+1)); fi
  echo "$(date -u +%FT%TZ) idle_minutes=$idle of $IDLE_MAX" > ~/idle_shutdown.state
  if [ $idle -ge $IDLE_MAX ]; then echo "$(date -u +%FT%TZ) shutting down (idle $IDLE_MAX min)" >> ~/idle_shutdown.log; sudo shutdown -h now; exit 0; fi
  sleep 60
done
