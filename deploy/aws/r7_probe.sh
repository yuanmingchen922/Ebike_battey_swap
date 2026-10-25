#!/usr/bin/env bash
# R7 siting probe, run ON THE INSTANCE, unattended (design notes/siting_scaleup_design.md 1.4, 3.1, 5.1):
#   step 1   reproduce the 15-candidate second-pass bounds, cache keys, demand hashes and template
#            arc counts through the new code (cache hits, masters only)
#   step 3   approach-radius effect on the 15-candidate family: terminal reachability of the 15
#            one-site layouts with / without the radius (library builds only), then 3 layouts x
#            3 scenarios, radius 14 vs none at equal effort (9 ILPs at max(300 s, cached limit),
#            warm-started, 4 workers x 3 threads), and the laptop-to-server factors (3 one-site
#            ScenarioLP barrier solves, 2 pass-2 ILPs re-solved with force=True at 300 s)
#   step 2   setup / sizes stage of r7_siting.py on manhattan_dot at N = 40 and N = all (59 with the
#            current DOT CSV): template arcs, LP columns / rows, z columns, RSS, superset LP time,
#            cold-barrier LP times per scenario (one-site, two-site, one-cell free, all-open free),
#            one exact pricing ILP at 300 s, and the terminal reachability of every one-site layout;
#            output dir outputs/r7_siting_probe/dot_N<N>_S<SCEN>; superset LP limit 600 s
#   summary  outputs/r7_siting_probe/probe_summary.json
# Thread budget: at most 12 solver threads at any time; memory guard: every step is killed when the
# step's process tree exceeds MAX_RSS_GB (default 58).
#
#   tmux new -d -s probe 'bash ~/battery_swap/deploy/aws/r7_probe.sh'        # all steps
#   bash ~/battery_swap/deploy/aws/r7_probe.sh 1 3                          # selected steps
#   SCEN=12 bash ~/battery_swap/deploy/aws/r7_probe.sh 2b                   # S = 12 instead of 6
# MAX_RSS_GB and SCEN are read once at start: give them per invocation, e.g.
#   tmux new -d -s probe2 'MAX_RSS_GB=100 SCEN=6 bash ~/battery_swap/deploy/aws/r7_probe.sh 3 2a; MAX_RSS_GB=100 SCEN=12 bash ~/battery_swap/deploy/aws/r7_probe.sh 2b sum'
ROOT="${AWS_REMOTE_ROOT:-$HOME/battery_swap}"
# shellcheck disable=SC1091
. "$ROOT/env.sh"                                   # venv, GRB_LICENSE_FILE, PYTHONPATH, cd ebike_swap_sim
set -uo pipefail                                   # after env.sh (it may read unset variables)
cd "$ROOT/ebike_swap_sim" || exit 1
export PYTHONPATH="${PYTHONPATH:-.}:."
P=outputs/r7_siting_probe
mkdir -p "$P"
LOG="$P/probe.log"
STEPS_FILE="$P/steps.jsonl"
MAX_RSS_GB="${MAX_RSS_GB:-58}"
SCEN="${SCEN:-6}"
export R7_SIZE_ALL_OPEN_MAX_SCEN="${R7_SIZE_ALL_OPEN_MAX_SCEN:-3}"   # all-open size LP on 3 LP scenarios (one wave)                                   # 6 = one seed per stratum (fits 60 GB at N = 59)
STEPS=("$@"); [ ${#STEPS[@]} -gt 0 ] || STEPS=(1 3 2a 2b sum)
DOT_CSV="$ROOT/data/raw/dot_candidate_sites.csv"
SYN_CSV="$ROOT/data/raw/dot_candidate_sites_SYNTHETIC.csv"
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

# run_guarded NAME CMD... : runs CMD in its own process group, samples the group's RSS every 10 s,
# kills it above MAX_RSS_GB, appends {"step", "rc", "wall_s", "peak_rss_gb", "killed"} to steps.jsonl
run_guarded() {
  local name="$1"; shift
  local t0 peak=0 killed=0 rss rc
  t0=$(date +%s)
  log "start $name: $*"
  setsid "$@" >>"$P/$name.log" 2>&1 &
  local pid=$!
  # setsid: the step is the leader of its own session (sid = pid), so the session's RSS is the step's
  while kill -0 "$pid" 2>/dev/null; do
    rss=$(ps -eo sid=,rss= 2>/dev/null | awk -v s="$pid" '$1 == s {t += $2} END {printf "%d", t / 1048576}')
    [ "${rss:-0}" -gt "$peak" ] && peak=$rss
    if [ "${rss:-0}" -ge "$MAX_RSS_GB" ]; then
      log "ABORT $name: process group RSS ${rss} GB >= ${MAX_RSS_GB} GB"
      pkill -TERM -s "$pid" 2>/dev/null; sleep 20; pkill -KILL -s "$pid" 2>/dev/null
      killed=1
    fi
    sleep 10
  done
  wait "$pid"; rc=$?
  log "end $name rc=$rc wall=$(( $(date +%s) - t0 )) s peak_rss=${peak} GB killed=$killed"
  printf '{"step": "%s", "rc": %d, "wall_s": %d, "peak_rss_gb": %d, "killed": %d, "finished": "%s"}\n' \
    "$name" "$rc" "$(( $(date +%s) - t0 ))" "$peak" "$killed" "$(date '+%F %T')" >>"$STEPS_FILE"
  return "$rc"
}

PY=python3
log "probe start on $(hostname): steps ${STEPS[*]}; nproc --all $(nproc --all); $(free -g | awk '/Mem:/ {print $2" GB RAM"}')"
[ -f outputs/r6_o2/manhattan_pass2/cuts.jsonl ] || { log "missing outputs/r6_o2/manhattan_pass2 (unzip r7_pass2.zip)"; }
# stale-code guard (adversarial review of 2026-10-21): the server copy must carry the start-state
# exemption, the hub-capable key component, the laptop-to-server LP factor and the all-scenario
# representative-layout check, else every step would measure other libraries
for mark in "reposition_radius_exempt_states:ebike_swap_sim/arcs.py" "roles_signature:ebike_swap_sim/benders.py" \
            "_lp_factor:experiments/r7_probe.py" "setup_stale:experiments/r7_probe.py" \
            "check_scenarios:experiments/r7_siting.py" "test_capped_lot_never_holds_a_hub_slot:tests/test_r7_siting.py"; do
  grep -q "${mark%%:*}" "${mark#*:}" 2>/dev/null || { log "STALE CODE: '${mark%%:*}' not in ${mark#*:}; sync the current tree first"; exit 2; }
done

for st in "${STEPS[@]}"; do
  case "$st" in
    1)
      rm -rf "$P/repro" "$P/repro_bound"; mkdir -p "$P/repro"
      cp -r outputs/r6_o2/manhattan_pass2/cache "$P/repro/cache"
      run_guarded step1_bound $PY experiments/r6_o2_siting.py --manhattan --bound-from-cuts --no-cover \
        --source-dir outputs/r6_o2/manhattan_pass2 --out-dir "$P/repro_bound" --master-threads 2 --max-threads 12
      run_guarded step1_repro $PY experiments/r7_probe.py repro --out "$P" --threads 3 --workers 4 --max-threads 12
      run_guarded step1_pytest env R7_REPRO=1 $PY -m pytest -q -p no:cacheprovider tests/test_r7_siting.py \
        -k "reproduced or lattice_fixture"
      ;;
    3)
      [ -f "$P/repro/cache/index.jsonl" ] || { mkdir -p "$P/repro"; cp -r outputs/r6_o2/manhattan_pass2/cache "$P/repro/cache"; }
      R5="--family r5_manhattan --menu full --scenarios 0 --seeds 0 1 2 --threads 3 --max-threads 12 --lp-workers 1 --lp-threads 1 --price-workers 4 --stage setup"
      # library-only reachability of the 15 one-site layouts, with and without the radius (no solve)
      run_guarded step3_feas_none $PY experiments/r7_probe.py feas --setup-dir "$P/feas_r5_none" --r7-args "$R5"
      run_guarded step3_feas_r14 $PY experiments/r7_probe.py feas --setup-dir "$P/feas_r5_r14" \
        --r7-args "$R5 --approach-radius 14"
      run_guarded step3_radius $PY experiments/r7_probe.py radius --out "$P" --radius 14 --threads 3 --workers 4 \
        --max-threads 12
      ;;
    2a|2b)
      CSV="$DOT_CSV"
      if [ ! -f "$CSV" ]; then
        log "DOT CSV absent: building the SYNTHETIC stand-in $SYN_CSV (results labelled synthetic)"
        $PY experiments/r7_probe.py synth --path "$SYN_CSV" --n 50 >>"$LOG" 2>&1
        CSV="$SYN_CSV"
      fi
      if [ "$st" = 2a ]; then N=40; RED="--reduced 40"; else N=all; RED=""; fi
      D="$P/dot_N${N}_S${SCEN}"
      [ "$CSV" = "$SYN_CSV" ] && D="${D}_SYNTHETIC"
      ARGS="--family manhattan_dot --dot-csv $CSV $RED --approach-radius 14 --scenarios $SCEN --threads 3 --lp-threads 3 --lp-workers 3 --master-threads 2 --price-workers 4 --max-threads 12 --time-limit 120 --max-rss-gb $((MAX_RSS_GB - 4))"
      # shellcheck disable=SC2086
      run_guarded "step${st}_setup" $PY experiments/r7_siting.py --stage setup --redo --out-dir "$D" $ARGS
      run_guarded "step${st}_price" $PY experiments/r7_probe.py price --setup-dir "$D" --r7-args "$ARGS --stage setup" \
        --time-limit 300 --threads 3 --workers 1
      # one scenario per demand level 32 / 40 / 48 orders (weekday): S = 6 -> 0 1 2, S = 12 -> 0 2 4
      if [ "$SCEN" = 12 ]; then FSC="0 2 4"; else FSC="0 1 2"; fi
      run_guarded "step${st}_feas" $PY experiments/r7_probe.py feas --setup-dir "$D" --r7-args "$ARGS --stage setup" \
        --scen "$FSC"
      ;;
    sum)
      $PY experiments/r7_probe.py summary --out "$P" >>"$LOG" 2>&1
      log "summary written: $P/probe_summary.json"
      ;;
    *) log "unknown step $st" ;;
  esac
done
log "probe done"
