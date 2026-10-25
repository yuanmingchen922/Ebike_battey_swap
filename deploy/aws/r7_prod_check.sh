#!/usr/bin/env bash
# R7 production pre-flight check (notes/siting_production_plan.md section 5 item 10), run ON THE
# INSTANCE after unpacking r7_code.zip (or sync_up.sh) and BEFORE 'run_lanes.sh start':
#   1. STALE CODE markers: every production change 1-7 of plan section 5 (plus the fixer pass of
#      2026-10-21) and every re-plan change 1-9 (notes/siting_production_replan_m1.md, 2026-10-23)
#      must be present in the server tree; one missing marker = exit 2.
#   2. the production lane plans (outputs/cloud_lanes_siting_prod/lanes.txt, lanes_r2.txt,
#      lanes_r2_tier2.txt + their .json) are present and each starts with its gate lane
#      (b0_gate / r2_gate / r2t2_gate: experiments/r7_gate.py, the same check from Python); the
#      r2 lanes run at --tol-rel 0.01 with --verify-start unchecked, batches 4-6 on open_sites,
#      and no r2 lane name repeats a lanes.txt name (the status files share LANES_DIR).
#   3. probe precondition: no tmux session 'probe' and probe.log ends with 'probe done'
#      (the 110 GB guard is per process; batch 1 must not run beside the step-2b probe); exit 3.
# It reads files only: no solver, no instance build, no network.
#
# This is a separate script on purpose: deploy/aws/r7_probe.sh is left byte-identical, because the
# step-2b probe is executing it on the server and bash reads a running script lazily.
#
#   bash ~/battery_swap/deploy/aws/r7_prod_check.sh                  # on the server (all checks)
#   bash deploy/aws/r7_prod_check.sh --root . --no-probe             # laptop: check a tree / an unzipped copy
#
# Exit codes: 0 ok, 2 stale code or missing lane plan, 3 probe still running / not finished.
set -uo pipefail
ROOT="${AWS_REMOTE_ROOT:-$HOME/battery_swap}"
PROBE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --root) shift; ROOT="${1:-}" ;;
    --no-probe) PROBE=0 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown option $1" >&2; exit 64 ;;
  esac
  shift
done
PKG="$ROOT/ebike_swap_sim"
[ -d "$PKG/ebike_swap_sim" ] || { echo "no package under $PKG (give --root PROJECT_ROOT)" >&2; exit 2; }

# change | marker (fixed string, grep -F) | file relative to the package root
MARKERS=(
  "1 root bound|def stage_rootlp|experiments/r7_siting.py"
  "1 root bound|def merge_root|experiments/r7_siting.py"
  "1 root bound|def root_order|experiments/r7_siting.py"
  "1 root bound|--root-import|experiments/r7_siting.py"
  "1 root bound|rootlp_incomplete|experiments/r7_siting.py"
  "2 memory lifecycle|class ScenarioLPSet|ebike_swap_sim/benders.py"
  "2 memory lifecycle|def release_library|ebike_swap_sim/benders.py"
  "2 memory lifecycle|release_lps|ebike_swap_sim/benders.py"
  "2 memory lifecycle|def evict_template|ebike_swap_sim/bilevel.py"
  "2 memory lifecycle|max_templates|ebike_swap_sim/bilevel.py"
  "3 batched escalation|def _escalate_batch|ebike_swap_sim/benders.py"
  "3 batched escalation|escalate_batch_max|ebike_swap_sim/benders.py"
  "4 feasibility skip list|def stage_feas|experiments/r7_siting.py"
  "4 feasibility skip list|def mark_terminal_infeasible|ebike_swap_sim/benders.py"
  "4 feasibility skip list|def verify_terminal_infeasible|ebike_swap_sim/benders.py"
  "4 feasibility skip list|def feasibility_signature|ebike_swap_sim/benders.py"
  "4 feasibility skip list|skip_locations|ebike_swap_sim/benders.py"
  "5 comparison filter|def comparison_filter|experiments/r7_siting.py"
  "5 comparison filter|--comparison-time-limits|experiments/r7_siting.py"
  "5 comparison filter|def restore_prior_lb|experiments/r7_siting.py"
  "6 search driver|def stage_calib|experiments/r7_search.py"
  "6 search driver|def set_bound|experiments/r7_search.py"
  "6 search driver|def stage_pairs|experiments/r7_search.py"
  "6 search driver|def pair_next_layout|experiments/r7_search.py"
  "6 search driver|def stage_m3|experiments/r7_search.py"
  "6 search driver|def stage_roles|experiments/r7_search.py"
  "6 search driver|def stage_oos_feas|experiments/r7_search.py"
  "6 search driver|def stage_oos|experiments/r7_search.py"
  "6 search driver|def stage_noradius|experiments/r7_search.py"
  "6 search driver|def stage_price_list|experiments/r7_search.py"
  "6 search driver|def write_prod_lanes|experiments/r7_search.py"
  "6 search driver|def m1_warm_layouts|experiments/r7_siting.py"
  "7 cost per batch|class CostLog|experiments/r7_cost.py"
  "7 cost per batch|def install_signal_handlers|experiments/r7_cost.py"
  "7 cost per batch|def summarise|experiments/r7_cost.py"
  "fixer|def instance_md5|experiments/r7_siting.py"
  "fixer|def instance_plan|experiments/r7_siting.py"
  "10 gate|def check|experiments/r7_gate.py"
  "tests|def test_cli_feas_rootlp_stages_merge_and_stage_lanes|tests/test_r7_siting.py"
  "tests|def test_warm_start_releases_lps_before_pricing|tests/test_r7_siting.py"
  "tests|def test_production_lanes_plan|tests/test_r7_search.py"
  "tests|def test_rootlp_lane_fails_without_a_value|tests/test_r7_search.py"
  # R7 re-plan after batch 2 (notes/siting_production_replan_m1.md changes 1-9 with the critic K1-K7)
  "r2-1 restore price_open|def _restore_open|ebike_swap_sim/benders.py"
  "r2-1 restore price_open|lower_open|ebike_swap_sim/benders.py"
  "r2-1 restore price_open|best_tier|ebike_swap_sim/benders.py"
  "r2-2 price-list tier|M1_LP_ORDER|experiments/r7_search.py"
  "r2-2 price-list tier|--extend-below-ub|experiments/r7_search.py"
  "r2-2 price-list tier|def m1_lp_order|experiments/r7_search.py"
  "r2-3 import-records|def stage_import_records|experiments/r7_search.py"
  "r2-4 warm from open_sites|def _warm_pick|ebike_swap_sim/benders.py"
  "r2-4 warm from open_sites|def ub_check_all_candidates|ebike_swap_sim/benders.py"
  "r2-5 m1 pass2 off / cells / params|price_pass|ebike_swap_sim/benders.py"
  "r2-5 m1 pass2 off / cells / params|def parse_cells|ebike_swap_sim/benders.py"
  "r2-5 m1 pass2 off / cells / params|def parse_ilp_params|ebike_swap_sim/benders.py"
  "r2-5 m1 pass2 off / cells / params|strict_scenarios|ebike_swap_sim/benders.py"
  "r2-5 m1 pass2 off / cells / params|--m1-pass2|experiments/r7_siting.py"
  "r2-6 verify start|verify_checked_starts|ebike_swap_sim/bilevel.py"
  "r2-6 verify start|--verify-start|experiments/r7_siting.py"
  "r2-7 price tier|--price-tier|experiments/r7_siting.py"
  "r2-7 price tier|def all_candidates_lower|experiments/r7_siting.py"
  "r2-7 price tier|def tier_kw|experiments/r7_search.py"
  "r2-7 price tier|--time-limit-many-sites|experiments/r7_siting.py"
  "r2-8 analyse dual statement|def m1_dual_statement|experiments/r7_siting.py"
  "r2-8 analyse dual statement|def m1_lower_table|experiments/r7_siting.py"
  "r2-9 lanes|def write_r2_lanes|experiments/r7_search.py"
  "r2-9 lanes|def stage_ub_check|experiments/r7_search.py"
  "r2-9 lanes|--cost-dir|experiments/r7_gate.py"
  "r2 tests|def test_restore_reads_price_open_into_priced_open_and_ub_only|tests/test_r7_replan.py"
  "r2 tests|def test_r2_lanes_plan|tests/test_r7_replan_drivers.py"
)

miss=0
for entry in "${MARKERS[@]}"; do
  IFS='|' read -r change mark rel <<<"$entry"
  if grep -qF -- "$mark" "$PKG/$rel" 2>/dev/null; then
    printf 'ok     [%s] %s in %s\n' "$change" "$mark" "$rel"
  else
    printf "STALE CODE: [%s] '%s' not in %s; sync the current tree first\n" "$change" "$mark" "$rel"
    miss=$((miss + 1))
  fi
done

LANES="$PKG/outputs/cloud_lanes_siting_prod"
for f in lanes.txt lanes.json lanes_r2.txt lanes_r2.json lanes_r2_tier2.txt lanes_r2_tier2.json; do
  [ -s "$LANES/$f" ] || { echo "MISSING lane plan: $LANES/$f"; miss=$((miss + 1)); }
done
# lane file | expected first lane (the gate)
for spec in "lanes.txt|b0_gate" "lanes_r2.txt|r2_gate" "lanes_r2_tier2.txt|r2t2_gate"; do
  IFS='|' read -r lf gate <<<"$spec"
  [ -s "$LANES/$lf" ] || continue
  first=$(grep -v '^#' "$LANES/$lf" | grep -v '^[[:space:]]*$' | head -n 1 | cut -f1)
  [ "$first" = "$gate" ] || { echo "lane plan $lf: first lane is '$first', expected $gate"; miss=$((miss + 1)); }
  echo "lane plan $lf: $(grep -v '^#' "$LANES/$lf" | grep -vc '^[[:space:]]*$') lanes, first '$first'"
done
# re-plan lanes: every pricing lane at --tol-rel 0.01 with --verify-start unchecked; batches 4-6 on open_sites;
# r2 lane names never collide with lanes.txt (status files share LANES_DIR)
if [ -s "$LANES/lanes_r2.txt" ]; then
  bad=$(grep -v '^#' "$LANES/lanes_r2.txt" | grep -v '^[[:space:]]*$' | grep -v 'r7_gate.py' | grep -v -e '--tol-rel 0.01' | cut -f1)
  [ -z "$bad" ] || { echo "lanes_r2.txt: lanes without --tol-rel 0.01: $bad"; miss=$((miss + 1)); }
  bad=$(grep -v '^#' "$LANES/lanes_r2.txt" | grep -v '^[[:space:]]*$' | grep -e '--stage price-list\|--stage pairs\|--stage m3\|--stage roles\|--stage comparison\|--stage restricted\|--stage oos\|--stage noradius\|--stage m1' | grep -v -e '--verify-start unchecked' | cut -f1)
  [ -z "$bad" ] || { echo "lanes_r2.txt: pricing lanes without --verify-start unchecked: $bad"; miss=$((miss + 1)); }
  bad=$(grep -v '^#' "$LANES/lanes_r2.txt" | grep -v '^[[:space:]]*$' | grep '^r2_b[456]_' | grep -v -e '--price-tier open_sites' | cut -f1)
  [ -z "$bad" ] || { echo "lanes_r2.txt: batch 4-6 lanes without --price-tier open_sites: $bad"; miss=$((miss + 1)); }
  if [ -s "$LANES/lanes.txt" ]; then
    dup=$(comm -12 <(grep -v '^#' "$LANES/lanes.txt" | cut -f1 | sort -u) <(grep -v '^#' "$LANES/lanes_r2.txt" "$LANES/lanes_r2_tier2.txt" 2>/dev/null | cut -f1 | sed 's/^[^:]*://' | sort -u) | grep -v '^$')
    [ -z "$dup" ] || { echo "lane names shared by lanes.txt and the r2 files: $dup"; miss=$((miss + 1)); }
  fi
fi
[ "$miss" -eq 0 ] || { echo "r7_prod_check: $miss problem(s); do not start the production lanes"; exit 2; }
echo "r7_prod_check: ${#MARKERS[@]} markers found under $PKG"

if [ "$PROBE" = 1 ]; then
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t probe 2>/dev/null; then
    echo "probe: tmux session 'probe' is still running; wait for it (or stop it by hand) before batch 1"; exit 3
  fi
  PLOG="$PKG/outputs/r7_siting_probe/probe.log"
  if [ -f "$PLOG" ] && ! tail -n 1 "$PLOG" | grep -q 'probe done'; then
    echo "probe: $PLOG does not end with 'probe done' (last line: $(tail -n 1 "$PLOG" | cut -c1-120))"
    echo "       if the probe was stopped by hand, re-run with --no-probe"; exit 3
  fi
  echo "probe: not running"
fi
exit 0
