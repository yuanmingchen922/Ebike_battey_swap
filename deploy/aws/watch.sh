#!/usr/bin/env bash
# Watch the experiments on the AWS instance from the laptop (read-only).
#   bash deploy/aws/watch.sh          # dashboard, refreshed every 30 s (Ctrl-C to stop watching; the run continues)
#   bash deploy/aws/watch.sh once     # one snapshot
#   bash deploy/aws/watch.sh log      # follow the probe log live (Ctrl-C to stop following)
#   bash deploy/aws/watch.sh lane NAME  # follow one production lane's log live, e.g. b2_m1
#   bash deploy/aws/watch.sh shell    # log in to the instance
# Connection settings come from deploy/aws/aws_env.sh (AWS_HOST changes after every stop/start).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
. "$HERE/aws_env.sh"
SSH=(ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 -i "$AWS_KEY" "${AWS_USER:-ubuntu}@$AWS_HOST")
P=battery_swap/ebike_swap_sim/outputs/r7_siting_probe
snapshot() {
  "${SSH[@]}" "
    echo \"== \$(date -u '+%F %T') UTC  (New York \$(TZ=America/New_York date '+%H:%M'))\"
    echo '== running sessions:'; tmux ls 2>/dev/null || echo '   (none)'
    echo '== load and memory:'; uptime | sed 's/^/   /'; free -g | awk 'NR==2{printf \"   memory used %s of %s GB\n\", \$3, \$2}'
    echo '== idle watchdog:'; sed 's/^/   /' ~/idle_shutdown.state
    echo '== experiment processes (elapsed, memory GB, command):'
    ps -eo etime=,rss=,args= | grep -E 'experiments/' | grep -v grep | awk '{printf \"   %s  %5.1f GB  \", \$1, \$2/1048576; for(i=3;i<=NF && i<=7;i++) printf \"%s \", \$i; print \"\"}'
    if [ -f battery_swap/ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt ] && tmux has-session -t lanes_dispatch 2>/dev/null || [ -d battery_swap/ebike_swap_sim/outputs/r7_siting ]; then
      echo '== production lanes:'
      cd battery_swap && LANES_DIR=\$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod bash deploy/aws/run_lanes.sh status ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt 2>/dev/null | grep -v -E ' queued ' | cut -c1-120 | sed 's/^/   /'
      echo '== cost so far (cost.jsonl):'
      ( . env.sh >/dev/null 2>&1; python3 experiments/r7_cost.py outputs/r7_siting 2>/dev/null | tail -4 | sed 's/^/   /' )
    else
      echo '== last steps of the probe log:'; grep -E 'start|end|ABORT|STALE|probe done' $P/probe.log 2>/dev/null | tail -6 | cut -c1-150 | sed 's/^/   /'
    fi
  "
}
case "${1:-dash}" in
  once)  snapshot ;;
  log)   "${SSH[@]}" "tail -n 30 -f $P/probe.log" ;;
  shell) exec "${SSH[@]}" ;;
  lane)  "${SSH[@]}" "tail -n 30 -f battery_swap/ebike_swap_sim/outputs/cloud_lanes_siting_prod/lane_${2:?lane name}.log" ;;
  dash)  while true; do clear; snapshot || echo "cannot reach $AWS_HOST (stopped, or the IP changed)"; sleep 30; done ;;
  *)     echo "usage: $0 [dash|once|log|lane NAME|shell]"; exit 2 ;;
esac
