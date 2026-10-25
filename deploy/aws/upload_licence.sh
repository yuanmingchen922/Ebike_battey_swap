#!/usr/bin/env bash
# Copy the Gurobi WLS licence file to the instance as ~/gurobi/gurobi.lic (mode 600).
#
#   deploy/aws/upload_licence.sh [PATH_OF_LICENCE_FILE]
#
# The path defaults to GRB_LICENSE_LOCAL from aws_env.sh.  The file is transferred with scp
# over the ssh key; its content is never read, printed or stored by this script, and
# sync_up.sh excludes *.lic so the licence can never travel with the code.  Nothing is
# committed: *.lic is in .gitignore.
set -euo pipefail
# shellcheck disable=SC1091
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_env

LIC="${1:-${GRB_LICENSE_LOCAL:-}}"
[ -n "$LIC" ] || die "no licence path: pass it as the first argument or set GRB_LICENSE_LOCAL in aws_env.sh"
LIC="${LIC/#\~/$HOME}"
[ -f "$LIC" ] || die "licence file not found at the given path: $LIC"
[ -s "$LIC" ] || die "licence file is empty: $LIC"
case "$LIC" in
  *.lic) ;;
  *) echo "warning: the file does not end in .lic; uploading it anyway as gurobi.lic" >&2 ;;
esac

info "creating ~/gurobi on $REMOTE"
# shellcheck disable=SC2016  # $HOME must expand on the server
remote_sh 'mkdir -p "$HOME/gurobi" && chmod 700 "$HOME/gurobi"'

info "uploading the licence file (size $(wc -c < "$LIC" | tr -d ' ') bytes) to ~/gurobi/gurobi.lic"
scp -q "${SCP_OPTS[@]}" "$LIC" "$REMOTE:gurobi/gurobi.lic"
# shellcheck disable=SC2016
remote_sh 'chmod 600 "$HOME/gurobi/gurobi.lic" && test -s "$HOME/gurobi/gurobi.lic" && ls -l "$HOME/gurobi/gurobi.lic"'

cat <<EOF
done.  On the instance the licence is used through
    export GRB_LICENSE_FILE=\$HOME/gurobi/gurobi.lic
which bootstrap.sh writes into $AWS_REMOTE_ROOT/env.sh.  Verify with
    ssh ${SSH_OPTS[*]} $REMOTE 'bash $AWS_REMOTE_ROOT/deploy/aws/bootstrap.sh --checks-only'
EOF
