"""Round-3 experiment scripts (``experiments/e*_round3.py``) and the round-3 helpers of
``experiments/common.py``: zeta runs with the max-service explanation, reuse rules, wall
budget, and the ``--dry-run`` / ``--smoke`` modes of every script (run as subprocesses from
``ebike_swap_sim/`` with ``PYTHONPATH`` set, writing only into ``tmp_path``)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import build_arcs  # noqa: E402
from experiments import common as C  # noqa: E402

pytest.importorskip("gurobipy")

SCRIPTS = ["e2u_round3.py", "e3u_round3.py", "e4u_round3.py", "e8_round3.py"]


def _run(script: str, *args: str, timeout: float = 900.0) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=ROOT, MPLBACKEND="Agg")
    return subprocess.run([sys.executable, os.path.join(ROOT, "experiments", script), *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=timeout)


def test_round3_helper_rules():
    """Reuse rule (OPTIMAL or gap <= 1 %), implication rule and the wall budget."""
    assert C.reusable_ilp_row("OPTIMAL", 0.0) and C.reusable_ilp_row("TIME_LIMIT", 0.0004)
    assert not C.reusable_ilp_row("TIME_LIMIT", 0.02) and not C.reusable_ilp_row("TIME_LIMIT", None)
    assert not C.reusable_ilp_row("SKIPPED_BUDGET", float("nan"))
    assert C.zeta_implied_by_written("OPTIMAL", 0.95, 0.90)
    assert C.zeta_implied_by_written("TIME_LIMIT", 0.95, 0.90, written_gap=5e-5)
    assert not C.zeta_implied_by_written("TIME_LIMIT", 0.95, 0.90, written_gap=0.02)
    assert not C.zeta_implied_by_written("OPTIMAL", 0.85, 0.90)
    assert not C.zeta_implied_by_written("OPTIMAL", None, 0.90)
    b = C.WallBudget(1000.0, margin_s=90.0, min_solve_s=30.0)
    assert b.solve_limit(300.0) == pytest.approx(300.0)
    assert C.WallBudget(100.0, margin_s=90.0).solve_limit(300.0) is None
    assert C.WallBudget(200.0, margin_s=90.0).solve_limit(300.0) == pytest.approx(110.0, abs=1.0)
    assert C.ILP_PARAMS_R3 == {"Seed": 0} and C.ZETA_MAIN == 0.90 and C.ZETA_SENS == 0.85


def test_zeta_case_feasible_and_infeasible_on_toy():
    """(33) at zeta = 1 on the toy: feasible with transfers (U* = 0, cost 12.5); INFEASIBLE
    with ``no_transfers`` (the written no-transfers optimum 106 drops an order), and the
    record then carries the certified maximum feasible share."""
    inst = C.make_instance("toy")
    lib = build_arcs(inst)
    rec = C.run_zeta_case(inst, lib, 1.0, time_limit=60.0, threads=1)
    assert rec["status"] == "OPTIMAL" and rec["zeta_feasible"] is True and rec["max_service"] is None
    assert rec["obj"] == pytest.approx(12.5) and rec["metrics"]["n_unserved"] == 0
    assert rec["stats"]["switches"]["zeta"] == 1.0
    rec2 = C.run_zeta_case(inst, lib, 1.0, time_limit=60.0, threads=1, no_transfers=True)
    assert rec2["status"] in ("INFEASIBLE", "INF_OR_UNBD") and rec2["zeta_feasible"] is False
    ms = rec2["max_service"]
    assert ms["certified"] and ms["status"] == "OPTIMAL"
    assert ms["min_unserved"] >= 1 and ms["share_achievable"] < 1.0
    assert ms["share_upper_bound"] == pytest.approx(ms["share_achievable"])
    assert ms["n_orders"] == len(inst.orders)
    # the max-service solve alone, with a start that is not feasible for no_transfers (ignored)
    ms2 = C.max_service_share(inst, lib, time_limit=60.0, threads=1, no_transfers=True)
    assert ms2["min_unserved"] == ms["min_unserved"]


def test_jsonl_helpers(tmp_path):
    p = str(tmp_path / "r.jsonl")
    assert C.load_jsonl(p) == []
    C.append_jsonl(p, {"a": 1, "b": {"c": (1, 2)}, "d": None})
    C.append_jsonl(p, {"a": 2})
    rows = C.load_jsonl(p)
    assert [r["a"] for r in rows] == [1, 2] and rows[0]["b"] == {"c": [1, 2]} and "wall_clock" in rows[0]


@pytest.mark.parametrize("script", SCRIPTS)
def test_round3_dry_run(script, tmp_path):
    """``--dry-run`` prints the plan and the JSON summary, solves nothing, writes nothing."""
    out = str(tmp_path / "out")
    cp = _run(script, "--dry-run", "--out-dir", out, timeout=300.0)
    assert cp.returncode == 0, cp.stderr[-2000:]
    txt = cp.stdout
    assert "# plan" in txt
    summary = json.loads(txt[txt.index("{"):])
    assert summary["ilp_items"] > 0 and summary["out_dir"] == out
    assert summary.get("reused_round2_rows", summary.get("reused_round2_ilp_rows", 0)) > 0
    assert not os.path.exists(out)


@pytest.mark.parametrize("script, n_rows, ilp_method", [
    ("e2u_round3.py", 2, "ilp_zeta90"), ("e3u_round3.py", 3, "ilp"),
    ("e4u_round3.py", 2, "ILP"), ("e8_round3.py", 2, "ilp")])
def test_round3_smoke(script, n_rows, ilp_method, tmp_path):
    """``--smoke``: the cheapest cell with Threads 1 and TimeLimit 30 s; records.jsonl and
    results.csv are written, the ILP row has an incumbent (the accepted policy start)."""
    out = str(tmp_path / "smoke")
    cp = _run(script, "--smoke", "--out-dir", out, timeout=900.0)
    assert cp.returncode == 0, cp.stderr[-3000:]
    rows = C.load_jsonl(os.path.join(out, "records.jsonl"))
    assert len(rows) == n_rows
    assert os.path.exists(os.path.join(out, "results.csv"))
    ilp = [r for r in rows if r["method"] == ilp_method]
    assert len(ilp) == 1
    r = ilp[0]
    assert r["status"] in ("OPTIMAL", "TIME_LIMIT") and r["total"] is not None
    assert r.get("mip_start_accepted") is True
    assert float(r.get("time_limit_s") or r.get("time_limit_used_s") or 30.0) <= 30.0 + 1e-9
    lines = [ln for ln in cp.stdout.splitlines() if ln.startswith("{")]
    assert len(lines) == n_rows     # one printed line per completed run
