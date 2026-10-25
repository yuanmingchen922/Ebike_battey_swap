#!/usr/bin/env bash
# Pull the results from the instance with rsync over ssh (compressed, resumable).
#
#   deploy/aws/sync_down.sh [--dry-run] [--in-place] [--with-instances] [--path REL ...] [--from DIR]
#
# Default destination: <project root>/cloud_results/  (LOCAL_RESULTS_DIR in aws_env.sh), a
# mirror of the remote tree.  The laptop may still be appending to its own
# ebike_swap_sim/outputs/*/records.jsonl, so the download never touches them unless you say
#   --in-place        write straight into the local ebike_swap_sim/outputs/ (use when no local
#                     experiment is running; server files replace local files of the same name)
#   --with-instances  include outputs/*/instances/ (large, regenerable)
#   --path REL        extra remote path relative to AWS_REMOTE_ROOT (repeatable), e.g.
#                     --path ebike_swap_sim/outputs/r6_penalty_smoke
#   --from DIR        local test source instead of the instance (no ssh)
#
# What comes back by default (all under ebike_swap_sim/outputs/):
#   r6_penalty/  r6_fill/  r6_o2/  r7_siting/  cloud_lanes/ cloud_lanes_siting/ (lane status + logs)  R6_DIGEST.md
#   including the PDF figures under */figs/ (the only PDFs the scripts ever transfer; every
#   other *.pdf stays excluded by COMMON_EXCLUDES).
# Never: *.lic, venv/, __pycache__, *_smoke/ folders, instance dumps (without --with-instances).
set -euo pipefail
# shellcheck disable=SC1091
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"

DRY=0; INPLACE=0; INSTANCES=0; FROM=""; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --in-place) INPLACE=1 ;;
    --with-instances) INSTANCES=1 ;;
    --path) shift; [ -n "${1:-}" ] || die "--path needs a value"; EXTRA+=("./${1#./}") ;;
    --from) shift; FROM="${1:-}"; [ -n "$FROM" ] || die "--from needs a directory" ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
  shift
done

RSYNC="$(pick_rsync)"
PATHS=(
  ./ebike_swap_sim/outputs/r6_penalty
  ./ebike_swap_sim/outputs/r6_fill
  ./ebike_swap_sim/outputs/r6_o2
  ./ebike_swap_sim/outputs/r7_siting
  ./ebike_swap_sim/outputs/cloud_lanes
  ./ebike_swap_sim/outputs/cloud_lanes_siting
  ./ebike_swap_sim/outputs/cloud_lanes_siting_prod
  ./ebike_swap_sim/outputs/R6_DIGEST.md
)
PATHS+=("${EXTRA[@]+"${EXTRA[@]}"}")

if [ -n "$FROM" ]; then
  load_env no-host
  SRC_PREFIX="$FROM/"
  SSH_ARGS=()
else
  load_env
  SRC_PREFIX="$REMOTE:$AWS_REMOTE_ROOT/"
  SSH_ARGS=(-e "$RSYNC_SSH")
fi
: "${LOCAL_RESULTS_DIR:=cloud_results}"
if [ "$INPLACE" = 1 ]; then
  DEST="$LOCAL_ROOT/"
else
  DEST="$LOCAL_ROOT/$LOCAL_RESULTS_DIR/"
fi
[ "$DRY" = 1 ] || mkdir -p "$DEST"

OPTS=(-azR --partial --human-readable --stats)
[ "$DRY" = 1 ] && OPTS+=(--dry-run -v)
# rsync applies the first matching rule: the include for figure PDFs must come before the
# common "*.pdf" exclude (the figures are regenerable, but the lanes write them and they are small).
INCL=(--include 'figs/*.pdf')
EXCL=(--exclude 'venv/' --exclude '*.lic' --exclude 'models/*.tmp')
[ "$INSTANCES" = 1 ] || EXCL+=(--exclude 'instances/')

# One rsync call with several sources; with -R each source keeps its path after the "./".
SRCS=()
for p in "${PATHS[@]}"; do SRCS+=("$SRC_PREFIX$p"); done
if [ -n "$FROM" ]; then
  # Local source: rsync wants the "./" anchor inside the path, so run from the source dir.
  cd "$FROM"
  SRCS=("${PATHS[@]}")
fi
info "results <- ${SRC_PREFIX} -> $DEST"
# rsync returns 23 when some of the listed remote paths do not exist yet (e.g. cloud_lanes
# before the first lane); that is not an error here.
set +e
# ${SSH_ARGS[@]+...}: an empty array is "unbound" under set -u in bash 3.2 (macOS)
"$RSYNC" "${OPTS[@]}" ${SSH_ARGS[@]+"${SSH_ARGS[@]}"} "${INCL[@]}" "${COMMON_EXCLUDES[@]}" "${EXCL[@]}" "${SRCS[@]}" "$DEST"
rc=$?
set -e
case "$rc" in
  0) ;;
  23|24) echo "note: rsync reported partial transfer (code $rc): some listed paths do not exist on the source yet" >&2 ;;
  *) die "rsync failed with code $rc" ;;
esac
if [ "$DRY" = 1 ]; then
  info "dry run only; nothing was written"
elif [ "$INPLACE" = 0 ]; then
  cat <<EOF
done.  The server tree is mirrored under $DEST
Compare with the local outputs before copying, e.g.
    diff <(wc -l < "$DEST/ebike_swap_sim/outputs/r6_penalty/levers/records.jsonl") \\
         <(wc -l < "$LOCAL_ROOT/ebike_swap_sim/outputs/r6_penalty/levers/records.jsonl")
and when the laptop is idle, re-run with --in-place to write into ebike_swap_sim/outputs/.
EOF
fi
