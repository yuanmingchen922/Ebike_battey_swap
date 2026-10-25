# shellcheck shell=bash
# shellcheck disable=SC2034  # the variables below are used by the scripts that source this file
# Shared helpers for the deploy/aws scripts.  Sourced, never executed.
#
# Loads deploy/aws/aws_env.sh (copied from aws_env.example.sh, git-ignored) or the same
# variables from the environment, validates them and builds the ssh / rsync option arrays.
# Nothing here prints the key, the licence or any file content: only paths and host names.

AWS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The project root ("OR Model-Battery Swap"): the folder that holds ebike_swap_sim/, data/,
# notes/data/ and deploy/aws/.  The remote layout mirrors it under AWS_REMOTE_ROOT.
LOCAL_ROOT="$(cd "$AWS_SCRIPT_DIR/../.." && pwd)"

die() { echo "error: $*" >&2; exit 1; }
info() { echo "[$(date +%H:%M:%S)] $*"; }

# load_env: source aws_env.sh when present, apply defaults, check the required variables.
# Pass "no-host" to skip the host / key checks (for local-only runs such as --to DIR).
load_env() {
  local mode="${1:-full}"
  if [ -f "$AWS_SCRIPT_DIR/aws_env.sh" ]; then
    # shellcheck disable=SC1091
    . "$AWS_SCRIPT_DIR/aws_env.sh"
    local eperm
    eperm="$(stat -f '%Lp' "$AWS_SCRIPT_DIR/aws_env.sh" 2>/dev/null || stat -c '%a' "$AWS_SCRIPT_DIR/aws_env.sh" 2>/dev/null || echo '')"
    case "$eperm" in
      400|600) ;;
      *) echo "warning: aws_env.sh has mode ${eperm:-?}; run: chmod 600 \"$AWS_SCRIPT_DIR/aws_env.sh\"" >&2 ;;
    esac
  fi
  : "${AWS_USER:=ubuntu}"
  : "${AWS_REGION:=us-east-2}"
  : "${AWS_REMOTE_ROOT:=/home/ubuntu/battery_swap}"
  : "${AWS_SSH_PORT:=22}"
  [ "$mode" = "no-host" ] && return 0
  [ -n "${AWS_HOST:-}" ] || die "AWS_HOST is not set (copy aws_env.example.sh to aws_env.sh and fill it in)"
  [ -n "${AWS_KEY:-}" ] || die "AWS_KEY (path of the .pem key) is not set"
  AWS_KEY="${AWS_KEY/#\~/$HOME}"
  [ -f "$AWS_KEY" ] || die "key file not found: $AWS_KEY"
  # The key must be private to the owner or ssh refuses it.
  local perm
  perm="$(stat -f '%Lp' "$AWS_KEY" 2>/dev/null || stat -c '%a' "$AWS_KEY" 2>/dev/null || echo '')"
  case "$perm" in
    400|600) ;;
    *) echo "warning: $AWS_KEY has mode ${perm:-?}; run: chmod 400 \"$AWS_KEY\"" >&2 ;;
  esac
  SSH_OPTS=(-i "$AWS_KEY" -p "$AWS_SSH_PORT"
            -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=60 -o ServerAliveCountMax=5)
  SCP_OPTS=(-i "$AWS_KEY" -P "$AWS_SSH_PORT" -o StrictHostKeyChecking=accept-new)
  REMOTE="$AWS_USER@$AWS_HOST"
  # rsync's -e argument (one string).
  RSYNC_SSH="ssh -i '$AWS_KEY' -p $AWS_SSH_PORT -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=60"
}

# shellcheck disable=SC2029  # the command string is built on the client on purpose
remote_sh() { ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"; }

# pick_rsync: prefer a modern rsync (Homebrew) over macOS openrsync; both work with the
# options used here (-azR --partial --delete --exclude --dry-run --stats).
pick_rsync() {
  if [ -x /opt/homebrew/bin/rsync ]; then echo /opt/homebrew/bin/rsync
  elif [ -x /usr/local/bin/rsync ]; then echo /usr/local/bin/rsync
  else command -v rsync || die "rsync not found"; fi
}

# Files that must never leave the laptop or never be synced in either direction.
# Used by sync_up.sh and sync_down.sh in addition to their own lists.
COMMON_EXCLUDES=(
  --exclude '.git/' --exclude '.gitignore'
  --exclude '__pycache__/' --exclude '*.pyc' --exclude '.pytest_cache/' --exclude '.ipynb_checkpoints/'
  --exclude '*.lic' --exclude 'gurobi.lic*' --exclude 'aws_env.sh' --exclude '*.pem' --exclude '.ssh/'
  --exclude '*.pdf' --exclude '*.zip'
  --exclude '.DS_Store' --exclude '*.swp' --exclude '*~' --exclude '*.bak' --exclude '*.tmp'
  --exclude '*_zh.md'
  --exclude '*.nohup.out' --exclude '*.pid'
  --exclude '*_smoke/' --exclude 'scratch/' --exclude 'venv/' --exclude '.venv/'
)
