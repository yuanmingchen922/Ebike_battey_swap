#!/usr/bin/env bash
# R8 fifteen-site study pre-flight check (notes/siting15_design.md sections 12-13), run ON THE
# INSTANCE after unpacking r8_code.zip and BEFORE 'run_lanes.sh start' of the k15 lanes:
#   1. STALE CODE markers: lane L1 (union bike-class arc library, bitmask reachability), lane L2
#      (family manhattan15, per-site metrics, force_k search, proxy screen, process-pool driver
#      experiments/r8_k15.py) and the fixer pass of 2026-10-28 must be present in the server tree;
#      one missing marker = exit 2.  Negative markers (critic C1 / C5): the R8 driver must not use
#      a thread pool and must never build the all-candidates template tier.
#   2. the k15 lane plan (outputs/cloud_lanes_k15/lanes.txt + lanes.json) is present, starts with
#      k15_instances, has the six lanes of the chain, every command runs experiments/r8_k15.py on
#      family manhattan15 with R7_BATCH=k15, 8 worker processes, --out-dir outputs/r8_k15 and no
#      --n-bikes / --n-orders / --ignore-gates (critic C4: n_bikes = 48 of the family gives the
#      orders); k15_search waits for k15_dryrun.
#   3. no other lane dispatcher is running (tmux session 'lanes_dispatch' is shared by every lane
#      plan; a running R7 dispatcher would swallow the k15 start); exit 3.
#   4. optional --smoke: the toy run of every stage (experiments/r8_k15.py --smoke --stage all, a
#      few seconds, 4 candidates, 2 worker processes) in a temporary directory, with <root>/env.sh
#      sourced when present (venv, PYTHONPATH, Gurobi licence); exit 4 when it fails.
# Steps 1-3 read files only: no solver, no instance build, no network.
#
#   bash ~/battery_swap/deploy/aws/r8_prod_check.sh --smoke          # on the server (all checks)
#   bash deploy/aws/r8_prod_check.sh --root . --no-dispatcher        # laptop: check a tree / an unzipped copy
#
# Exit codes: 0 ok, 2 stale code or bad lane plan, 3 a dispatcher is running, 4 smoke failed.
set -uo pipefail
ROOT="${AWS_REMOTE_ROOT:-$HOME/battery_swap}"
DISP=1
SMOKE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root) shift; ROOT="${1:-}" ;;
    --no-dispatcher) DISP=0 ;;
    --smoke) SMOKE=1 ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    *) echo "unknown option $1" >&2; exit 64 ;;
  esac
  shift
done
PKG="$ROOT/ebike_swap_sim"
[ -d "$PKG/ebike_swap_sim" ] || { echo "no package under $PKG (give --root PROJECT_ROOT)" >&2; exit 2; }

# change | marker (fixed string, grep -F) | file relative to the package root
MARKERS=(
  # L1 union (bike-class) arc library, critic C2
  "L1 union library|class UnionArcLibrary(ArcLibrary)|ebike_swap_sim/arcs.py"
  "L1 union library|def build_union_arcs|ebike_swap_sim/arcs.py"
  "L1 union library|def library_mode|ebike_swap_sim/arcs.py"
  "L1 union library|def delivery_need|ebike_swap_sim/arcs.py"
  "L1 union library|def _union_columns|ebike_swap_sim/arcs.py"
  "L1 bitmask reachability|def reach_sweep|ebike_swap_sim/arcs.py"
  "L1 bitmask reachability|def coreach_sweep|ebike_swap_sim/arcs.py"
  "L1 bitmask reachability|class _BitRank|ebike_swap_sim/arcs.py"
  "L1 aggregation fast path|def _init_union|ebike_swap_sim/aggregate.py"
  "L1 tests|def test_toy_views_reproduce_build_arcs|tests/test_union_arcs.py"
  "L1 tests|def test_ilp_values_identical_on_toy|tests/test_union_arcs.py"
  "L1 tests|def test_reduced6_manhattan_dot_8_riders_identical|tests/test_union_arcs.py"
  "L1 tests|def test_r5_manhattan_8_riders_identical|tests/test_union_arcs.py"
  # L2 family, metrics, exactly-k search
  "L2 family manhattan15|MANHATTAN15_FAMILY = \"manhattan15\"|ebike_swap_sim/sites_nyc.py"
  "L2 family manhattan15|\"n_bikes\": 48|ebike_swap_sim/sites_nyc.py"
  "L2 per-site metrics|def site_metrics|ebike_swap_sim/evaluate.py"
  "L2 per-site metrics|per_site|ebike_swap_sim/evaluate.py"
  "L2 service gate|SERVICE_GATE: Dict[str, float]|ebike_swap_sim/bilevel.py"
  "L2 service gate|def service_gate|ebike_swap_sim/bilevel.py"
  "L2 proxy screen|class ProxyScreen|ebike_swap_sim/bilevel.py"
  "L2 force_k|force_k: Optional[int] = None|ebike_swap_sim/bilevel.py"
  "L2 warm starts|def k_median_layout|ebike_swap_sim/bilevel.py"
  "L2 warm starts|def dot_first_layout|ebike_swap_sim/bilevel.py"
  "L2 warm starts|def top_sites|ebike_swap_sim/bilevel.py"
  "L2 external rows|def store_external_row|ebike_swap_sim/bilevel.py"
  "L2 unservable id index|_deliv|experiments/common.py"
  # L2 driver, critic C1 / C3 / C5 / C6
  "L2 driver C1 process pool|import multiprocessing as mp|experiments/r8_k15.py"
  "L2 driver C1 process pool|class WorkerPool|experiments/r8_k15.py"
  "L2 driver C3 saved instances|def stage_instances|experiments/r8_k15.py"
  "L2 driver gates|def stage_dryrun|experiments/r8_k15.py"
  "L2 driver gates|def gates_block|experiments/r8_k15.py"
  "L2 driver C6 ratio check|def stage_validate|experiments/r8_k15.py"
  "L2 driver search|def stage_search|experiments/r8_k15.py"
  "L2 driver final|def stage_final|experiments/r8_k15.py"
  "L2 driver report|def stage_report|experiments/r8_k15.py"
  "L2 driver lanes|def write_lanes|experiments/r8_k15.py"
  "L2 driver offline evaluator|class OfflineEvaluator|experiments/r8_k15.py"
  "L2 tests|def test_cli_smoke_all_stages_resume_and_contract|tests/test_r8_k15.py"
  "L2 tests|def test_force_k_is_exact_against_the_exhaustive_enumeration|tests/test_r8_k15.py"
  "L2 tests|def test_write_lanes_and_deploy_format|tests/test_r8_k15.py"
  # fixer pass after the two reviews (2026-10-28)
  "fixer a1 start prefetch|_prefetch(evaluator, [start])|ebike_swap_sim/bilevel.py"
  "fixer a1 start prefetch|search_blocked|experiments/r8_k15.py"
  "fixer dry-run references|dryrun_refs|experiments/r8_k15.py"
  "fixer V(k) gaps|vk_missing|experiments/r8_k15.py"
  "fixer instance loads|instance_load_s|experiments/r8_k15.py"
  "fixer tests|def test_restart_from_an_unpriced_start_is_ok_on_the_offline_evaluator|tests/test_r8_k15.py"
  "fixer tests|def test_site_metrics_rows_for_a_charge_only_hub|tests/test_r8_k15.py"
)
# change | forbidden marker (grep -F) | file: must NOT occur
NEGATIVE=(
  "C1 no thread pool|ThreadPoolExecutor|experiments/r8_k15.py"
  "C5 no all-candidates template|.template(|experiments/r8_k15.py"
  "C5 no all-candidates template|superset_bound|experiments/r8_k15.py"
  "C5 no all-candidates template|subset_library|experiments/r8_k15.py"
)

miss=0
for entry in "${MARKERS[@]}"; do
  IFS='|' read -r change mark rel <<<"$entry"
  if grep -qF -- "$mark" "$PKG/$rel" 2>/dev/null; then
    printf 'ok     [%s] %s in %s\n' "$change" "$mark" "$rel"
  else
    printf "STALE CODE: [%s] '%s' not in %s; unpack r8_code.zip first\n" "$change" "$mark" "$rel"
    miss=$((miss + 1))
  fi
done
for entry in "${NEGATIVE[@]}"; do
  IFS='|' read -r change mark rel <<<"$entry"
  if [ ! -f "$PKG/$rel" ]; then
    printf "STALE CODE: [%s] %s missing\n" "$change" "$rel"; miss=$((miss + 1))
  elif grep -qF -- "$mark" "$PKG/$rel"; then
    printf "FORBIDDEN: [%s] '%s' found in %s\n" "$change" "$mark" "$rel"; miss=$((miss + 1))
  else
    printf 'ok     [%s] no %s in %s\n' "$change" "$mark" "$rel"
  fi
done

LANES="$PKG/outputs/cloud_lanes_k15"
LF="$LANES/lanes.txt"
for f in lanes.txt lanes.json; do
  [ -s "$LANES/$f" ] || { echo "MISSING lane plan: $LANES/$f"; miss=$((miss + 1)); }
done
if [ -s "$LF" ]; then
  body() { grep -v '^#' "$LF" | grep -v '^[[:space:]]*$'; }
  names=$(body | cut -f1 | tr '\n' ' ')
  want="k15_instances k15_dryrun k15_validate k15_search k15_final k15_report "
  [ "$names" = "$want" ] || { echo "lanes.txt: lanes '$names', expected '$want'"; miss=$((miss + 1)); }
  after_search=$(body | awk -F'\t' '$1=="k15_search"{print $3}')
  [ "$after_search" = "k15_dryrun" ] || { echo "lanes.txt: k15_search waits for '$after_search', expected k15_dryrun"; miss=$((miss + 1)); }
  for need in 'experiments/r8_k15.py' '--family manhattan15' 'R7_BATCH=k15' '--out-dir outputs/r8_k15 ' '--workers 8' '--k 15'; do
    bad=$(body | grep -v -F -e "$need" | cut -f1 | tr '\n' ' ')
    [ -z "$bad" ] || { echo "lanes.txt: lanes without '$need': $bad"; miss=$((miss + 1)); }
  done
  for forbid in '--n-bikes' '--n-orders' '--ignore-gates' '--smoke' '--reduced'; do
    bad=$(body | grep -F -e "$forbid" | cut -f1 | tr '\n' ' ')
    [ -z "$bad" ] || { echo "lanes.txt: lanes with '$forbid': $bad"; miss=$((miss + 1)); }
  done
  grep -q '"name": "k15_instances"' "$LANES/lanes.json" 2>/dev/null || { echo "lanes.json: no k15_instances lane"; miss=$((miss + 1)); }
  echo "lane plan lanes.txt: $(body | wc -l | tr -d ' ') lanes ($names)"
fi
[ "$miss" -eq 0 ] || { echo "r8_prod_check: $miss problem(s); do not start the k15 lanes"; exit 2; }
echo "r8_prod_check: ${#MARKERS[@]} markers and ${#NEGATIVE[@]} negative markers ok under $PKG"

if [ "$DISP" = 1 ]; then
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t lanes_dispatch 2>/dev/null; then
    echo "dispatcher: tmux session 'lanes_dispatch' is running (another lane plan); let it finish or"
    echo "            'bash deploy/aws/run_lanes.sh stop all' (kills running lanes) before the k15 start"; exit 3
  fi
  echo "dispatcher: not running"
fi

if [ "$SMOKE" = 1 ]; then
  # shellcheck disable=SC1091
  [ -f "$ROOT/env.sh" ] && . "$ROOT/env.sh"
  TMPD="$(mktemp -d "${TMPDIR:-/tmp}/r8_smoke.XXXXXX")"
  t0=$(date +%s)
  if (cd "$PKG" && PYTHONPATH=. python3 experiments/r8_k15.py --smoke --stage all --workers 2 --out-dir "$TMPD/out") >"$TMPD/smoke.log" 2>&1; then
    echo "smoke: experiments/r8_k15.py --smoke --stage all ok in $(( $(date +%s) - t0 )) s (log $TMPD/smoke.log)"
  else
    echo "smoke: FAILED (last lines of $TMPD/smoke.log):"; tail -n 20 "$TMPD/smoke.log"; exit 4
  fi
fi
exit 0
