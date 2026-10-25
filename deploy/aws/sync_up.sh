#!/usr/bin/env bash
# Push the code, the data and the resumable outputs to the instance with rsync over ssh
# (compressed, resumable: --partial keeps half-transferred files, a second run only sends
# what changed).
#
#   deploy/aws/sync_up.sh [--dry-run] [--code-only | --outputs-only] [--with-instances]
#                         [--delete] [--to DIR]
#
#   --dry-run         list what would be transferred, send nothing
#   --code-only       package, experiments, tests, data, notes/data, deploy/aws (no outputs)
#   --outputs-only    only the resumable outputs listed below
#   --with-instances  also the per-run instance dumps (outputs/*/instances/, about 90 MB,
#                     regenerated from the seeds by the experiments; not needed)
#   --delete          remove remote files that no longer exist locally (inside the synced
#                     folders only; never used on outputs the server may be writing)
#   --to DIR          local test target instead of the instance (no ssh), e.g. a scratch folder
#
# What goes up (paths relative to the project root; the remote layout mirrors them under
# AWS_REMOTE_ROOT because the code locates data/ and notes/data/ relative to the package):
#   ebike_swap_sim/ebike_swap_sim  ebike_swap_sim/experiments  ebike_swap_sim/tests
#   ebike_swap_sim/pytest.ini README.md CONTRACT.md
#   data/                          (23 MB; raw CSV / GeoJSON / ACS xlsx; the .zip is skipped)
#   food_order.csv                 (124 KB)
#   notes/data/                    (72 KB: cost_calibration_usd.json, kaggle_calibration.json,
#                                   zone_weights_manhattan.csv; nothing else of notes/)
#   deploy/aws/                    (scripts; aws_env.sh and *.lic are excluded)
#   ebike_swap_sim/outputs/R5_DIGEST.md, R6_DIGEST.md
#   ebike_swap_sim/outputs/r6_penalty/   records, schedules, tables (the retries and the joins)
#   ebike_swap_sim/outputs/r6_fill/      records and tables of the finished stages
#   ebike_swap_sim/outputs/r6_o2/        records, cuts.jsonl, cache (compliance and the siting passes)
#   ebike_swap_sim/outputs/r5_x6_manhattan/chosen_layout.json
#   ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt, lanes.json   (R7 production lane plan only;
#                                         never the lane status files the server writes there)
# Never: .git, __pycache__, PDFs, the manuscript / paper / reading folders, notes/ except
# notes/data, *_smoke outputs, *.lic, aws_env.sh, *.pem, *.pid, *.nohup.out, *_zh.md.
set -euo pipefail
# shellcheck disable=SC1091
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

DRY=0; CODE=1; OUTPUTS=1; INSTANCES=0; DELETE=0; TO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --code-only) OUTPUTS=0 ;;
    --outputs-only) CODE=0 ;;
    --with-instances) INSTANCES=1 ;;
    --delete) DELETE=1 ;;
    --to) shift; TO="${1:-}"; [ -n "$TO" ] || die "--to needs a directory" ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

RSYNC="$(pick_rsync)"
if [ -n "$TO" ]; then
  load_env no-host
  mkdir -p "$TO"
  DEST="$TO/"
  SSH_ARGS=()
else
  load_env
  DEST="$REMOTE:$AWS_REMOTE_ROOT/"
  SSH_ARGS=(-e "$RSYNC_SSH")
  info "creating $AWS_REMOTE_ROOT on $REMOTE"
  remote_sh "mkdir -p '$AWS_REMOTE_ROOT'"
fi

# -a archive, -z compress, -R keep the path relative to the "./" anchor, --partial resume.
OPTS=(-azR --partial --human-readable --stats)
[ "$DRY" = 1 ] && OPTS+=(--dry-run -v)
[ "$DELETE" = 1 ] && OPTS+=(--delete)

CODE_PATHS=(
  ./ebike_swap_sim/ebike_swap_sim
  ./ebike_swap_sim/experiments
  ./ebike_swap_sim/tests
  ./ebike_swap_sim/pytest.ini
  ./ebike_swap_sim/README.md
  ./ebike_swap_sim/CONTRACT.md
  ./data
  ./food_order.csv
  ./notes/data
  ./deploy/aws
)
OUTPUT_PATHS=(
  ./ebike_swap_sim/outputs/R5_DIGEST.md
  ./ebike_swap_sim/outputs/R6_DIGEST.md
  ./ebike_swap_sim/outputs/r6_penalty
  ./ebike_swap_sim/outputs/r6_fill
  ./ebike_swap_sim/outputs/r6_o2
  ./ebike_swap_sim/outputs/r5_x6_manhattan/chosen_layout.json
  ./ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt
  ./ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.json
)
OUTPUT_EXCLUDES=(--exclude '*_lanes/' --exclude 'figs/*.pdf' --exclude 'lane_*.status' --exclude 'cloud_lanes/')
[ "$INSTANCES" = 1 ] || OUTPUT_EXCLUDES+=(--exclude 'instances/')

cd "$LOCAL_ROOT"
missing=0
for p in "${CODE_PATHS[@]}" "${OUTPUT_PATHS[@]}"; do
  [ -e "$p" ] || { echo "warning: $p does not exist locally, skipped" >&2; missing=1; }
done
# select_existing PATH... -> the array "paths" (bash 3.2 compatible: macOS has no mapfile)
select_existing() { paths=(); local p; for p in "$@"; do [ -e "$p" ] && paths+=("$p"); done; }

if [ "$CODE" = 1 ]; then
  info "code + data -> $DEST"
  select_existing "${CODE_PATHS[@]}"
  # ${arr[@]+"${arr[@]}"}: an empty array is "unbound" under set -u in bash 3.2 (macOS)
  "$RSYNC" "${OPTS[@]}" ${SSH_ARGS[@]+"${SSH_ARGS[@]}"} "${COMMON_EXCLUDES[@]}" \
    --exclude 'deploy/aws/lanes*.txt' --exclude 'outputs/' \
    ${paths[@]+"${paths[@]}"} "$DEST"
fi
if [ "$OUTPUTS" = 1 ]; then
  info "resumable outputs -> $DEST"
  select_existing "${OUTPUT_PATHS[@]}"
  # No --delete on outputs: the server appends to records.jsonl while the lanes run.
  OPTS_OUT=(); for o in "${OPTS[@]}"; do [ "$o" = "--delete" ] || OPTS_OUT+=("$o"); done
  "$RSYNC" "${OPTS_OUT[@]}" ${SSH_ARGS[@]+"${SSH_ARGS[@]}"} "${COMMON_EXCLUDES[@]}" "${OUTPUT_EXCLUDES[@]}" \
    ${paths[@]+"${paths[@]}"} "$DEST"
fi
[ "$missing" = 0 ] || echo "note: some listed paths were missing locally (see warnings above)" >&2
if [ "$DRY" = 1 ]; then
  info "dry run only; nothing was sent"
elif [ -z "$TO" ]; then
  cat <<EOF
done.  Next steps (first time only):
    deploy/aws/upload_licence.sh
    ssh ${SSH_OPTS[*]} $REMOTE 'bash $AWS_REMOTE_ROOT/deploy/aws/bootstrap.sh'
EOF
fi
