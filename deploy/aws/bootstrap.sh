#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu Server 24.04 LTS (x86_64) EC2 instance, run ON the instance
# after sync_up.sh and upload_licence.sh:
#
#   ssh -i ~/.ssh/battery-swap.pem ubuntu@<host> 'bash ~/battery_swap/deploy/aws/bootstrap.sh'
#
# Steps (each prints a line starting with "==>"; the summary at the end lists OK / FAIL):
#   1. apt packages: python3.12 + venv, pip, tmux, rsync, htop, git, build tools for pip
#   2. venv at <root>/venv, pip install -r deploy/aws/requirements.txt (CPU torch)
#   3. <root>/env.sh with GRB_LICENSE_FILE, PYTHONPATH=. and the venv activation
#   4. licence check: gurobipy creates and solves a 1-variable model under GRB_LICENSE_FILE
#      (Gurobi's own output is discarded, so nothing of the licence is printed)
#   5. toy invariant: the aggregated toy ILP optimum equals 12.5 (pytest + a direct check)
#   6. one tiny smoke stage: r6_penalty psweep --smoke at Threads 1 (about 30-60 s) into
#      <root>/scratch/smoke (not into outputs/)
#   7. rewrite_paths.py: cached schedule paths recorded on the laptop get the server prefix
#
# The script is idempotent: re-running it reuses the venv and repeats pip / the checks, so
# run it again after a lost ssh connection or an apt lock timeout.
#
# Options:
#   --skip-apt       do not run apt (already installed)
#   --checks-only    only steps 3-7 (venv must exist); used after re-uploading a licence
#   --run-tests      also run the whole pytest suite (about 390 tests, several minutes)
#   --no-smoke       skip step 6
#   --root DIR       project root (default: the folder two levels above this script)
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
SKIP_APT=0; CHECKS_ONLY=0; RUN_TESTS=0; SMOKE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-apt) SKIP_APT=1 ;;
    --checks-only) CHECKS_ONLY=1 ;;
    --run-tests) RUN_TESTS=1 ;;
    --no-smoke) SMOKE=0 ;;
    --root) shift; ROOT="$(cd "$1" && pwd)" ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
PKG="$ROOT/ebike_swap_sim"
VENV="$ROOT/venv"
LIC="${GRB_LICENSE_FILE:-$HOME/gurobi/gurobi.lic}"
RESULTS=()
step() { echo; echo "==> $*"; }
ok() { RESULTS+=("OK   $*"); echo "OK: $*"; }
fail() { RESULTS+=("FAIL $*"); echo "FAIL: $*" >&2; }

[ -d "$PKG/ebike_swap_sim" ] || { echo "package not found at $PKG; run sync_up.sh first" >&2; exit 1; }

# ---------------------------------------------------------------- 1. apt
if [ "$CHECKS_ONLY" = 0 ] && [ "$SKIP_APT" = 0 ]; then
  step "apt packages"
  export DEBIAN_FRONTEND=noninteractive
  # A freshly booted instance runs unattended-upgrades / apt-daily for a few minutes and holds
  # the dpkg lock; DPkg::Lock::Timeout makes apt wait (up to 10 min) instead of failing at once.
  APT=(sudo apt-get -o DPkg::Lock::Timeout=600 -y -q)
  "${APT[@]}" update
  if "${APT[@]}" install python3.12 python3.12-venv python3-pip tmux rsync htop git curl \
       build-essential python3.12-dev; then
    ok "apt packages installed"
  else
    fail "apt install (check the network / the security group outbound rule)"
    echo "apt failed; nothing else can work without python3.12-venv. If the instance was booted" >&2
    echo "less than ~5 minutes ago, wait two minutes and re-run bootstrap.sh (it is safe to repeat)." >&2
    exit 1
  fi
fi

# ---------------------------------------------------------------- 2. venv + pip
if [ "$CHECKS_ONLY" = 0 ]; then
  step "virtual environment $VENV"
  PY=python3.12; command -v python3.12 >/dev/null 2>&1 || PY=python3
  if [ ! -x "$VENV/bin/python" ]; then
    "$PY" -m venv "$VENV" || { fail "venv creation"; exit 1; }
  fi
  "$VENV/bin/python" -m pip install --upgrade -q pip wheel
  if "$VENV/bin/python" -m pip install -q -r "$HERE/requirements.txt"; then
    ok "pip install -r requirements.txt ($("$VENV/bin/python" --version 2>&1))"
  else
    fail "pip install -r requirements.txt"
  fi
fi
[ -x "$VENV/bin/python" ] || { echo "venv missing at $VENV (run without --checks-only)" >&2; exit 1; }

# ---------------------------------------------------------------- 3. env.sh
step "writing $ROOT/env.sh"
cat > "$ROOT/env.sh" <<EOF
# Source this before running anything:  . $ROOT/env.sh
export GRB_LICENSE_FILE="$LIC"
export PYTHONPATH=.
# Keep BLAS / torch from grabbing every core; the lanes override these per lane.
export OMP_NUM_THREADS="\${OMP_NUM_THREADS:-3}" MKL_NUM_THREADS="\${MKL_NUM_THREADS:-3}" OPENBLAS_NUM_THREADS="\${OPENBLAS_NUM_THREADS:-3}"
export MPLBACKEND=Agg
. "$VENV/bin/activate"
cd "$PKG"
EOF
ok "env.sh written (GRB_LICENSE_FILE=$LIC)"
# shellcheck disable=SC1090,SC1091  # env.sh is written just above
. "$ROOT/env.sh"
cd "$PKG" || exit 1

# ---------------------------------------------------------------- 4. licence
step "Gurobi licence check (GRB_LICENSE_FILE=$LIC)"
if [ ! -f "$LIC" ]; then
  fail "licence file not found at $LIC (run deploy/aws/upload_licence.sh from the laptop)"
else
  # The Python below silences Gurobi at the file-descriptor level before importing it, so the
  # WLS banner (licence id, registered user) never reaches the terminal or a log.
  if python - <<'PY'
import os, sys
saved_out, saved_err = os.dup(1), os.dup(2)
devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(devnull, 1); os.dup2(devnull, 2)
status = None
try:
    import gurobipy as gp
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model(env=env)
    x = m.addVar(ub=1.0, obj=1.0)
    m.ModelSense = gp.GRB.MAXIMIZE
    m.optimize()
    status = "ok" if (m.Status == gp.GRB.OPTIMAL and abs(x.X - 1.0) < 1e-9) else "solve returned status %s" % m.Status
    m.dispose(); env.dispose()
    ver = ".".join(str(v) for v in gp.gurobi.version())
except Exception as exc:  # noqa: BLE001
    status = "gurobipy could not start: %s (error code %s)" % (type(exc).__name__, getattr(exc, "errno", "?"))
    ver = "?"
finally:
    os.dup2(saved_out, 1); os.dup2(saved_err, 2)
if status == "ok":
    print("gurobipy %s created and solved a model under GRB_LICENSE_FILE" % ver)
    sys.exit(0)
print(status)
sys.exit(1)
PY
  then ok "Gurobi licence works"
  else fail "Gurobi licence (WLS needs outbound HTTPS to Gurobi's servers; check the file path and the security group)"
  fi
fi

# ---------------------------------------------------------------- 5. toy invariant 12.5
step "toy invariant: aggregated toy ILP optimum == 12.5"
if python -m pytest "tests/test_aggregate.py::test_toy_12_5_11_2_106_aggregated" -q -p no:cacheprovider >/dev/null 2>&1 \
   && python - <<'PY'
from ebike_swap_sim import toy_instance, build_arcs
from ebike_swap_sim.ilp import solve
inst = toy_instance(); lib = build_arcs(inst)
_, st = solve(inst, lib, aggregate=True, threads=1, time_limit=60.0)
assert st["status"] == "OPTIMAL" and abs(st["obj"] - 12.5) < 1e-6, st
print("toy ILP optimum %.3f (OPTIMAL)" % st["obj"])
PY
then ok "toy ILP optimum 12.5"
else fail "toy ILP optimum 12.5 (see: python -m pytest tests/test_aggregate.py -q)"
fi

# ---------------------------------------------------------------- 5b. full suite (optional)
if [ "$RUN_TESTS" = 1 ]; then
  step "full pytest suite"
  if python -m pytest -q -p no:cacheprovider 2>&1 | tail -3; then ok "pytest suite"; else fail "pytest suite"; fi
fi

# ---------------------------------------------------------------- 6. smoke stage
if [ "$SMOKE" = 1 ]; then
  step "smoke stage: r6_penalty psweep --smoke --threads 1 -> $ROOT/scratch/smoke"
  mkdir -p "$ROOT/scratch"
  if OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python experiments/r6_penalty.py --stage psweep --smoke --threads 1 \
       --out-root "$ROOT/scratch/smoke" > "$ROOT/scratch/smoke_psweep.log" 2>&1 \
     && [ -f "$ROOT/scratch/smoke/psweep/RESULTS.md" ]; then
    ok "smoke stage finished ($(tail -1 "$ROOT/scratch/smoke/psweep/wall_time.json" 2>/dev/null | tr -d '\n' | cut -c1-80))"
  else
    fail "smoke stage (log: $ROOT/scratch/smoke_psweep.log)"
  fi
fi

# ---------------------------------------------------------------- 7. cached paths
step "rewrite laptop paths in cached schedule indexes"
if python "$HERE/rewrite_paths.py" --root "$ROOT" --apply; then ok "rewrite_paths"; else fail "rewrite_paths"; fi

# ---------------------------------------------------------------- summary
echo
NCPU="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo '?')"
RAM="$(free -g 2>/dev/null | awk '/Mem:/{print $2}')"; [ -n "$RAM" ] || RAM="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))"
echo "==> machine: $NCPU vCPU, $RAM GB RAM, $(df -h "$ROOT" | awk 'NR==2{print $4}') free on $(df -h "$ROOT" | awk 'NR==2{print $1}')"
echo "==> summary"
rc=0
for r in "${RESULTS[@]}"; do echo "   $r"; case "$r" in FAIL*) rc=1 ;; esac; done
cat <<EOF

Next:
    . $ROOT/env.sh
    python $HERE/make_cloud_lanes.py            # writes outputs/cloud_lanes/lanes.txt
    bash $HERE/run_lanes.sh start outputs/cloud_lanes/lanes.txt --dry-run   # plan + thread budget
    bash $HERE/run_lanes.sh start outputs/cloud_lanes/lanes.txt             # --max-threads N to change
    bash $HERE/run_lanes.sh status
EOF
exit $rc
