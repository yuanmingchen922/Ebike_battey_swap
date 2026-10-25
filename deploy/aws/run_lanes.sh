#!/usr/bin/env bash
# Start, watch and stop experiment lanes in tmux on the instance, with thread accounting.
#
#   run_lanes.sh start  LANES_FILE [--max-threads N] [--only a,b] [--dry-run]
#   run_lanes.sh status [LANES_FILE]
#   run_lanes.sh stop   <lane-name|all>
#   run_lanes.sh logs   <lane-name> [N]          last N lines (default 40) of the lane's log
#   run_lanes.sh dispatch LANES_FILE --max-threads N   (internal: the queue loop)
#
# Lanes file (written by make_cloud_lanes.py; TAB-separated, "#" lines ignored):
#   name <TAB> threads <TAB> after <TAB> command
#   "after" is "-" or a comma-separated list of lane names that must have finished (rc=0) first.
#   The command runs in bash from the package root with the venv and GRB_LICENSE_FILE of
#   <root>/env.sh; several commands may be joined with ";" or "&&".
#
# Thread accounting: the dispatcher keeps the sum of "threads" of the running lanes at or below
# --max-threads.  Default: 1.5 solver threads per PHYSICAL core, capped at nproc - 1 (EC2 vCPUs
# are hyperthreads, two per core; Gurobi gains little from them and a lane sharing a core hits its
# time limits more often).  On r7i.8xlarge (32 vCPU = 16 cores) that is 24: eight lanes at
# Threads 3, or four beside the 11-thread siting lane.  --max-threads 31 uses every hyperthread
# (ten lanes); --max-threads 16 keeps one thread per core.  Each lane also gets OMP_NUM_THREADS
# etc. set to its count.
#
# Files (LANES_DIR = <package>/outputs/cloud_lanes): lane_<name>.sh (wrapper), lane_<name>.status
# (START / EXIT rc / lane DONE lines with UTC times), lane_<name>.log (stdout+stderr of the
# command), dispatcher.log.  A tmux session per lane is named lane_<name>; the queue loop runs
# in the tmux session "lanes_dispatch".
#
# Lane states: queued, running, done (last "lane DONE" line has rc=0), failed (rc != 0: the
# dispatcher does not retry it and holds back the lanes that depend on it), on hold (stopped with
# "stop"), released, interrupted (was running when the machine stopped).  An explicit "start"
# releases held and failed lanes so that they run again; it may be run while a dispatcher is
# active (it then only releases, the running dispatcher picks the lanes up).
#
# Resume after a reboot or a spot interruption: run "start" again with the same lanes file.
# Done lanes are skipped; interrupted lanes are restarted (every experiment resumes from its
# records.jsonl, so only the solve in flight is repeated).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PKG="$ROOT/ebike_swap_sim"
LANES_DIR="${LANES_DIR:-$PKG/outputs/cloud_lanes}"
# A relative LANES_DIR is taken from the directory the command is run in and made absolute here:
# the dispatcher and the lane wrappers run with their working directory at $PKG (review of
# 2026-10-21: a relative path put the status files elsewhere, and status / stop / release broke).
case "$LANES_DIR" in /*) ;; *) LANES_DIR="$(pwd)/$LANES_DIR" ;; esac
ENV_SH="$ROOT/env.sh"
POLL="${LANES_POLL:-30}"   # seconds between dispatcher passes

die() { echo "error: $*" >&2; exit 1; }
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
ncpu() { nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4; }
# Physical cores: lscpu on Linux, sysctl on macOS, else half the logical CPUs.
nphys() {
  local n=""
  if command -v lscpu >/dev/null 2>&1; then
    n="$(lscpu -p=CORE 2>/dev/null | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
  fi
  case "$n" in ''|0|*[!0-9]*) n="$(sysctl -n hw.physicalcpu 2>/dev/null || echo '')" ;; esac
  case "$n" in ''|0|*[!0-9]*) n=$(( $(ncpu) / 2 )) ;; esac
  [ "$n" -ge 1 ] || n=1
  echo "$n"
}
# Default --max-threads: 1.5 x physical cores, never above nproc - 1, never below 1.
default_max() {
  local m cap
  m=$(( $(nphys) * 3 / 2 )); cap=$(( $(ncpu) - 1 ))
  [ "$m" -le "$cap" ] || m="$cap"
  [ "$m" -ge 1 ] || m=1
  echo "$m"
}
have_tmux() { command -v tmux >/dev/null 2>&1; }
session_alive() { have_tmux && tmux has-session -t "lane_$1" 2>/dev/null; }
status_file() { echo "$LANES_DIR/lane_$1.status"; }
lane_started() { [ -f "$(status_file "$1")" ]; }
# done: the LAST "lane DONE" line has rc=0 (a crashed lane -- OOM, Gurobi error, bad command --
# writes rc != 0 and must not count as done, or its dependents would run on incomplete records).
lane_done() { local st; st="$(status_file "$1")"; [ -f "$st" ] && grep '^lane DONE' "$st" | tail -1 | grep -q ' rc=0 '; }
# failed: the lane's last status line is a non-zero "lane DONE" (nothing released it since).
lane_failed() { local st; st="$(status_file "$1")"; [ -f "$st" ] && tail -1 "$st" | grep -qE '^lane DONE rc=[1-9]'; }
lane_rc() { grep '^lane DONE' "$(status_file "$1")" 2>/dev/null | tail -1 | sed -n 's/^lane DONE rc=\([0-9]*\).*/\1/p'; }
# A lane stopped with "run_lanes.sh stop" stays on hold (the dispatcher does not restart it)
# until the next explicit "run_lanes.sh start".
lane_held() { local st; st="$(status_file "$1")"; [ -f "$st" ] && tail -1 "$st" | grep -q "^STOPPED"; }
lane_released() { local st; st="$(status_file "$1")"; [ -f "$st" ] && tail -1 "$st" | grep -q "^RELEASED"; }

# parse_lanes FILE -> fills arrays L_NAME L_THREADS L_AFTER L_CMD
parse_lanes() {
  local f="$1" line name threads after cmd
  [ -f "$f" ] || die "lanes file not found: $f"
  L_NAME=(); L_THREADS=(); L_AFTER=(); L_CMD=()
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    IFS=$'\t' read -r name threads after cmd <<<"$line"
    [ -n "$name" ] && [ -n "$threads" ] && [ -n "$cmd" ] || die "bad lane line (need name<TAB>threads<TAB>after<TAB>command): $line"
    case "$threads" in ''|*[!0-9]*) die "threads must be an integer in lane $name" ;; esac
    case "$name" in *[!A-Za-z0-9_.-]*) die "lane name may only contain letters, digits, _ . - : $name" ;; esac
    L_NAME+=("$name"); L_THREADS+=("$threads"); L_AFTER+=("${after:--}"); L_CMD+=("$cmd")
  done < "$f"
  [ "${#L_NAME[@]}" -gt 0 ] || die "no lanes in $f"
}

# deps_done INDEX -> 0 when every lane in "after" finished with rc=0
deps_done() {
  local after="${L_AFTER[$1]}" d deps
  [ "$after" = "-" ] && return 0
  IFS=',' read -ra deps <<<"$after"
  for d in "${deps[@]}"; do lane_done "$d" || return 1; done
  return 0
}
# deps_failed INDEX -> 0 when a lane in "after" is in the failed state (so this lane is blocked)
deps_failed() {
  local after="${L_AFTER[$1]}" d deps
  [ "$after" = "-" ] && return 1
  IFS=',' read -ra deps <<<"$after"
  for d in "${deps[@]}"; do lane_failed "$d" && return 0; done
  return 1
}

running_threads() {
  local i total=0
  for i in "${!L_NAME[@]}"; do session_alive "${L_NAME[$i]}" && total=$((total + L_THREADS[i])); done
  echo "$total"
}

# shellcheck disable=SC2016  # the single-quoted lines are written into the wrapper verbatim
write_wrapper() {  # write_wrapper INDEX
  local i="$1" name="${L_NAME[$1]}" threads="${L_THREADS[$1]}" cmd="${L_CMD[$1]}" w
  w="$LANES_DIR/lane_$name.sh"
  {
    echo '#!/usr/bin/env bash'
    echo "# lane $name (threads $threads), written by run_lanes.sh at $(now)"
    echo 'set -u'
    echo "ST=\"$LANES_DIR/lane_$name.status\""
    echo "LOG=\"$LANES_DIR/lane_$name.log\""
    echo "if [ -f \"$ENV_SH\" ]; then . \"$ENV_SH\"; fi"
    echo "cd \"$PKG\" || exit 1"
    echo 'export PYTHONPATH=.'
    echo "export OMP_NUM_THREADS=$threads MKL_NUM_THREADS=$threads OPENBLAS_NUM_THREADS=$threads"
    echo 'echo "lane start $(date -u +%Y-%m-%dT%H:%M:%SZ) pid $$ host $(hostname)" >> "$ST"'
    echo "echo \"$name START \$(date -u +%Y-%m-%dT%H:%M:%SZ)\" >> \"\$ST\""
    echo "bash -c $(printf '%q' "$cmd") >> \"\$LOG\" 2>&1"
    echo 'rc=$?'
    echo "echo \"$name EXIT \$rc \$(date -u +%Y-%m-%dT%H:%M:%SZ)\" >> \"\$ST\""
    echo 'echo "lane DONE rc=$rc $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ST"'
  } > "$w"
  chmod +x "$w"
  echo "$w"
}

start_lane() {  # start_lane INDEX
  local i="$1" name="${L_NAME[$1]}" w
  w="$(write_wrapper "$i")"
  if lane_started "$name"; then echo "RESTART $(now)" >> "$(status_file "$name")"; fi
  tmux new-session -d -s "lane_$name" -c "$PKG" "bash '$w'"
  echo "$(now) started lane $name (threads ${L_THREADS[$i]})" | tee -a "$LANES_DIR/dispatcher.log"
}

# release_lanes -> appends RELEASED to every held or failed lane of the parsed file; prints the count
release_lanes() {
  local i name n=0
  for i in "${!L_NAME[@]}"; do
    name="${L_NAME[$i]}"
    if lane_held "$name"; then
      echo "RELEASED by run_lanes.sh start $(now) (was on hold)" >> "$(status_file "$name")"; n=$((n + 1))
    elif lane_failed "$name"; then
      echo "RELEASED by run_lanes.sh start $(now) (was failed rc=$(lane_rc "$name"))" >> "$(status_file "$name")"; n=$((n + 1))
    fi
  done
  echo "$n"
}

cmd_dispatch() {
  local f="$1" max="$2" i name free pending nfail=0 nblocked=0
  parse_lanes "$f"
  echo "$(now) dispatcher start: ${#L_NAME[@]} lanes, max threads $max, $(ncpu) vCPU / $(nphys) cores" >> "$LANES_DIR/dispatcher.log"
  while :; do
    pending=0
    for i in "${!L_NAME[@]}"; do
      name="${L_NAME[$i]}"
      lane_done "$name" && continue
      lane_held "$name" && continue
      lane_failed "$name" && continue       # not retried in a loop; "start" releases it
      deps_failed "$i" && continue          # blocked behind a failed lane
      pending=1
      session_alive "$name" && continue
      deps_done "$i" || continue
      free=$(( max - $(running_threads) ))
      [ "${L_THREADS[$i]}" -le "$free" ] || continue
      start_lane "$i"
    done
    [ "$pending" = 1 ] || break
    sleep "$POLL"
  done
  for i in "${!L_NAME[@]}"; do
    name="${L_NAME[$i]}"
    if lane_failed "$name"; then
      nfail=$((nfail + 1))
      echo "$(now) lane $name FAILED rc=$(lane_rc "$name") (log: $LANES_DIR/lane_$name.log)" >> "$LANES_DIR/dispatcher.log"
    elif deps_failed "$i" && ! lane_done "$name"; then
      nblocked=$((nblocked + 1))
      echo "$(now) lane $name not started: depends on a failed lane (${L_AFTER[$i]})" >> "$LANES_DIR/dispatcher.log"
    fi
  done
  if [ "$nfail" = 0 ]; then
    echo "$(now) dispatcher done: every lane finished" >> "$LANES_DIR/dispatcher.log"
  else
    echo "$(now) dispatcher done: $nfail lane(s) failed, $nblocked blocked behind them; inspect the logs, fix, then run_lanes.sh start again" >> "$LANES_DIR/dispatcher.log"
  fi
}

cmd_start() {
  local f="" max="" only="" dry=0 i name
  while [ $# -gt 0 ]; do
    case "$1" in
      --max-threads) shift; max="${1:-}" ;;
      --only) shift; only="${1:-}" ;;
      --dry-run) dry=1 ;;
      -*) die "unknown option $1" ;;
      *) f="$1" ;;
    esac
    shift
  done
  [ -n "$f" ] || die "usage: run_lanes.sh start LANES_FILE [--max-threads N] [--only a,b] [--dry-run]"
  [ -f "$f" ] || die "lanes file not found: $f"
  # Absolute path: the dispatcher runs in its own tmux session whose working directory may differ.
  f="$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"
  parse_lanes "$f"
  [ -n "$max" ] || max=$(default_max)
  case "$max" in ''|*[!0-9]*) die "--max-threads needs an integer" ;; esac
  [ "$max" -ge 1 ] || max=1
  if [ -n "$only" ]; then
    local keep=() kn kt ka kc sel want
    for i in "${!L_NAME[@]}"; do
      sel=0; IFS=',' read -ra want <<<"$only"
      for kn in "${want[@]}"; do [ "$kn" = "${L_NAME[$i]}" ] && sel=1; done
      [ "$sel" = 1 ] && keep+=("$i")
    done
    [ "${#keep[@]}" -gt 0 ] || die "--only matched no lane"
    kn=(); kt=(); ka=(); kc=()
    for i in "${keep[@]}"; do kn+=("${L_NAME[$i]}"); kt+=("${L_THREADS[$i]}"); ka+=("${L_AFTER[$i]}"); kc+=("${L_CMD[$i]}"); done
    L_NAME=("${kn[@]}"); L_THREADS=("${kt[@]}"); L_AFTER=("${ka[@]}"); L_CMD=("${kc[@]}")
    f="$LANES_DIR/lanes_selected.txt"
    mkdir -p "$LANES_DIR"
    { echo "# selection written by run_lanes.sh --only $only at $(now)"
      for i in "${!L_NAME[@]}"; do printf '%s\t%s\t%s\t%s\n' "${L_NAME[$i]}" "${L_THREADS[$i]}" "${L_AFTER[$i]}" "${L_CMD[$i]}"; done; } > "$f"
  fi
  local total=0 maxlane=0 ndone=0 nfail=0
  for i in "${!L_NAME[@]}"; do
    total=$((total + L_THREADS[i])); [ "${L_THREADS[$i]}" -gt "$maxlane" ] && maxlane="${L_THREADS[$i]}"
    lane_done "${L_NAME[$i]}" && ndone=$((ndone + 1))
    lane_failed "${L_NAME[$i]}" && nfail=$((nfail + 1))
  done
  echo "lanes file : $f"
  echo "lanes      : ${#L_NAME[@]} ($ndone already done, $nfail failed), threads if all ran at once: $total"
  echo "machine    : $(ncpu) vCPU = $(nphys) physical cores; max concurrent threads: $max (about $((max / 3)) lanes at Threads 3; default $(default_max) = 1.5 x cores, --max-threads to change)"
  [ "$maxlane" -le "$max" ] || die "lane with $maxlane threads exceeds --max-threads $max"
  echo
  printf '%-28s %7s %-22s %s\n' "lane" "threads" "after" "state"
  local free="$max" plan
  for i in "${!L_NAME[@]}"; do
    name="${L_NAME[$i]}"
    if lane_done "$name"; then plan="done"
    elif session_alive "$name"; then plan="running"
    elif lane_failed "$name"; then plan="failed (rc=$(lane_rc "$name")); start re-runs it"
    elif lane_held "$name"; then plan="on hold; start releases it"
    elif deps_failed "$i"; then plan="blocked (failed: ${L_AFTER[$i]})"
    elif ! deps_done "$i"; then plan="queued (waits for ${L_AFTER[$i]})"
    elif [ "${L_THREADS[$i]}" -le "$free" ]; then plan="starts now"; free=$((free - L_THREADS[i]))
    else plan="queued (threads)"; fi
    printf '%-28s %7s %-22s %s\n' "$name" "${L_THREADS[$i]}" "${L_AFTER[$i]}" "$plan"
  done
  if [ "$dry" = 1 ]; then echo; echo "dry run: nothing started"; return 0; fi
  if [ "$ndone" = "${#L_NAME[@]}" ]; then echo; echo "every lane is already done; nothing to start"; return 0; fi
  have_tmux || die "tmux not found (sudo apt-get install tmux)"
  mkdir -p "$LANES_DIR"
  # An explicit start releases the lanes that "stop" put on hold and the lanes that failed.
  local nrel
  nrel="$(release_lanes)"
  [ "$nrel" = 0 ] || echo "released $nrel held / failed lane(s); they run again from their records"
  [ -f "$ENV_SH" ] || echo "warning: $ENV_SH not found; lanes run with the current environment (run bootstrap.sh first)" >&2
  if tmux has-session -t lanes_dispatch 2>/dev/null; then
    echo
    if [ "$nrel" = 0 ]; then
      echo "a dispatcher is already running (tmux session lanes_dispatch) and no lane needed releasing; nothing to do."
      echo "to change the lanes file or --max-threads: run_lanes.sh stop all, then start again."
    else
      echo "a dispatcher is already running (tmux session lanes_dispatch); it picks the released lanes up within $POLL s."
      [ -z "$only" ] || echo "note: lanes selected with --only must also be in the file the running dispatcher reads."
    fi
    return 0
  fi
  echo "$(now) start requested: file $f, max threads $max" >> "$LANES_DIR/dispatcher.log"
  # LANES_DIR is passed explicitly: a tmux server that is already running (e.g. the probe's) does
  # not hand this shell's environment to a new session
  tmux new-session -d -s lanes_dispatch -c "$PKG" "LANES_DIR='$LANES_DIR' bash '$HERE/run_lanes.sh' dispatch '$f' --max-threads $max"
  sleep 2
  if ! tmux has-session -t lanes_dispatch 2>/dev/null; then
    echo "error: the dispatcher exited at once; last lines of $LANES_DIR/dispatcher.log:" >&2
    tail -n 5 "$LANES_DIR/dispatcher.log" >&2
    return 1
  fi
  echo
  echo "dispatcher started in tmux session lanes_dispatch; lanes start within $POLL s as threads allow."
  echo "watch:  bash $HERE/run_lanes.sh status $f      attach: tmux attach -t lane_<name>  (detach: Ctrl-b d)"
}

cmd_status() {
  local f="${1:-}" i name st last state
  [ -n "$f" ] || f="$LANES_DIR/lanes.txt"
  [ -f "$f" ] || { find "$LANES_DIR" -maxdepth 1 -name 'lane_*.status' 2>/dev/null | sed 's/.*lane_//; s/\.status$//' | sort | while read -r name; do
      echo "$name: $(tail -1 "$LANES_DIR/lane_$name.status")"; done; return 0; }
  parse_lanes "$f"
  echo "dispatcher: $(tmux has-session -t lanes_dispatch 2>/dev/null && echo running || echo not running)   running threads: $(running_threads)/$(ncpu) vCPU ($(nphys) cores)   $(now)"
  printf '%-28s %7s %-16s %s\n' "lane" "threads" "state" "last status line"
  for i in "${!L_NAME[@]}"; do
    name="${L_NAME[$i]}"; st="$(status_file "$name")"
    if lane_done "$name"; then state="done"
    elif session_alive "$name"; then state="running"
    elif lane_failed "$name"; then state="failed (rc=$(lane_rc "$name"))"
    elif lane_held "$name"; then state="on hold"
    elif lane_released "$name"; then state="released"
    elif deps_failed "$i"; then state="blocked"
    elif [ -f "$st" ]; then state="interrupted"
    else state="queued"; fi
    last=""; [ -f "$st" ] && last="$(tail -1 "$st")"
    printf '%-28s %7s %-16s %s\n' "$name" "${L_THREADS[$i]}" "$state" "$last"
  done
}

cmd_stop() {
  local target="${1:-}" name pid
  [ -n "$target" ] || die "usage: run_lanes.sh stop <lane-name|all>"
  have_tmux || die "tmux not found"
  if [ "$target" = all ]; then
    tmux kill-session -t lanes_dispatch 2>/dev/null && echo "dispatcher stopped"
    tmux list-sessions -F '#S' 2>/dev/null | grep '^lane_' | sed 's/^lane_//' | while read -r name; do cmd_stop "$name"; done
    return 0
  fi
  name="$target"
  local killed=0
  if [ -f "$(status_file "$name")" ]; then
    pid="$(grep -o 'pid [0-9]*' "$(status_file "$name")" | tail -1 | awk '{print $2}')"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      # Terminate the whole tree under the lane shell (python, gurobi workers), children first.
      kill_tree "$pid"
      killed=1
    fi
  fi
  if tmux kill-session -t "lane_$name" 2>/dev/null; then killed=1; fi
  if [ "$killed" = 1 ]; then
    sleep 1   # let the wrapper write its last lines first, so STOPPED stays the last one
    echo "STOPPED by run_lanes.sh $(now)" >> "$(status_file "$name")"
    echo "lane $name stopped (it resumes from its records on the next start)"
  else
    echo "lane $name was not running"
  fi
}

# kill_tree PID: SIGTERM to every descendant of PID (deepest first), then to PID itself.
kill_tree() {
  local p="$1" c
  for c in $(pgrep -P "$p" 2>/dev/null); do kill_tree "$c"; done
  kill -TERM "$p" 2>/dev/null
}

cmd_logs() {
  local name="${1:-}" n="${2:-40}"
  [ -n "$name" ] || die "usage: run_lanes.sh logs <lane-name> [N]"
  [ -f "$LANES_DIR/lane_$name.log" ] || die "no log for lane $name"
  tail -n "$n" "$LANES_DIR/lane_$name.log"
}

case "${1:-}" in
  start) shift; cmd_start "$@" ;;
  status) shift; cmd_status "$@" ;;
  stop) shift; cmd_stop "$@" ;;
  logs) shift; cmd_logs "$@" ;;
  dispatch) shift; f="${1:-}"; shift; max=""; while [ $# -gt 0 ]; do case "$1" in --max-threads) shift; max="${1:-}" ;; esac; shift; done
            [ -n "$max" ] || max=$(default_max); mkdir -p "$LANES_DIR"
            # errors of the queue loop (e.g. a missing lanes file) go to dispatcher.log as well
            cmd_dispatch "$f" "$max" 2>> "$LANES_DIR/dispatcher.log" ;;
  -h|--help|'') sed -n '2,38p' "$0" ;;
  *) die "unknown command $1" ;;
esac
