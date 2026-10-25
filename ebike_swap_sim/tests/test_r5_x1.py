"""X1 headline re-validation script (``experiments/r5_x1_headline.py``): plan / resume rules,
best-rule and best-known-relaxed selection, the Shapley decomposition and ``--dry-run``
(subprocess, writes nothing).  No Gurobi solve is run here."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from experiments import common as C  # noqa: E402
from experiments import r5_x1_headline as X1  # noqa: E402


def _row(fam, cal, seed, mult, tg, m, total, ea=None, **kw):
    r = {"family": fam, "calib": cal, "seed": seed, "mult": mult, "targets": tg, "method": m,
         "status": kw.pop("status", "POLICY" if m != "ilp" else "OPTIMAL"), "total": total,
         "total_end_adjusted": (None if total is None else total + 1.0) if ea is None else ea, "C_end_adjust": 1.0, "demand_md5": "x"}
    r.update(kw)
    return r


def test_plan_and_resume_rules():
    plan = X1.build_plan({}, ["usd4h", "nyc4h"], [0, 1], [0.75, 1.0, 1.5])
    # legacy rule groups first (8 cells), then per ebaas cell: rules + ilp written + ilp relaxed
    assert [it for it in plan if it[1] == "legacy"] == plan[:8]
    assert sum(1 for it in plan if it[5] == "ilp") == 16
    assert {it[4] for it in plan if it[5] == "ilp"} == {"written", "relaxed"}
    assert X1.cells_for(["usd4h", "nyc4h"], [0], [0.75, 1.0])[-1] == ("nyc4h", 0, 1.0)
    done = {}
    for tg in X1.TARGETS:
        for r in X1.CORE_RULES:
            row = _row("nyc4h", "ebaas", 0, 1.0, tg, r, 10.0)
            done[X1.key_of(row)] = row
    row = _row("nyc4h", "ebaas", 0, 1.0, "written", "ilp", 5.0, status="TIME_LIMIT", mip_gap=0.05)
    done[X1.key_of(row)] = row
    row = _row("nyc4h", "ebaas", 0, 1.0, "relaxed", "ilp", None, status=C.SKIPPED_BUDGET)
    done[X1.key_of(row)] = row
    plan = X1.build_plan(done, ["nyc4h"], [0], [1.0], legacy=False)
    assert plan == [("nyc4h", "ebaas", 0, 1.0, "relaxed", "ilp")]
    plan = X1.build_plan(done, ["nyc4h"], [0], [1.0], legacy=False, retry_unsolved=True)
    assert ("nyc4h", "ebaas", 0, 1.0, "written", "ilp") in plan
    assert X1.group_plan(X1.build_plan({}, ["nyc4h"], [0], [1.0], legacy=False))[0][4] == [
        ("*", "rules"), ("written", "ilp"), ("relaxed", "ilp")]


def test_per_instance_best_rule_and_best_known_relaxed():
    rows = [
        _row("usd4h", "ebaas", 0, 1.0, "written", "r2", 100.0, 101.0),
        _row("usd4h", "ebaas", 0, 1.0, "written", "r5_range", 90.0, 95.0),
        _row("usd4h", "ebaas", 0, 1.0, "written", "r5", 92.0, 93.0),
        _row("usd4h", "ebaas", 0, 1.0, "relaxed", "r2", 100.0, 101.0),
        _row("usd4h", "ebaas", 0, 1.0, "relaxed", "r5_range", 90.0, 95.0),
        _row("usd4h", "ebaas", 0, 1.0, "relaxed", "r5", 91.0, 92.0),
        _row("usd4h", "ebaas", 0, 1.0, "written", "ilp", 60.0, 61.0),
        # relaxed solve stopped above the written optimum -> best known relaxed = written row
        _row("usd4h", "ebaas", 0, 1.0, "relaxed", "ilp", 62.0, 62.5, status="TIME_LIMIT", mip_gap=0.1),
    ]
    per = X1.per_instance(X1.last_per_key(rows))
    r = per.iloc[0]
    assert r.best_rule_w == "r5_range" and r.B_best_w == 90.0
    assert r.best_rule_rel_ea == "r5@relaxed" and r.B_best_rel_ea == 92.0
    assert r.I_rel_from == "written" and r.I_rel == 60.0 and r.I_rel_ea == 61.0
    assert r.g_w_r2 == pytest.approx(40.0) and r.g_w_best == pytest.approx(100 * 30 / 90)
    assert r.g_rel_best_ea == pytest.approx(100 * (92 - 61) / 92)
    bad = rows + [dict(_row("usd4h", "ebaas", 0, 1.0, "written", "r5_transfer", 1.0), demand_md5="y")]
    with pytest.raises(RuntimeError):
        X1.per_instance(X1.last_per_key(bad))


def test_shapley_additive():
    v = {(a, b, c): 30.0 - 5 * a - 3 * b - 1 * c - 2 * a * b for a in (0, 1) for b in (0, 1) for c in (0, 1)}
    phi = X1.shapley(v, 3)
    assert sum(phi) == pytest.approx(v[(1, 1, 1)] - v[(0, 0, 0)])
    assert phi == pytest.approx([-6.0, -4.0, -1.0])
    assert X1.gap_pct(200.0, 150.0) == pytest.approx(25.0) and X1.gap_pct(None, 1.0) is None


def test_dry_run_subprocess(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT, MPLBACKEND="Agg")
    out = tmp_path / "x1"
    res = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r5_x1_headline.py"), "--dry-run",
                          "--out-dir", str(out)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stderr
    js = json.loads(res.stdout[res.stdout.index("{"):])
    assert js["ilp_items"] == 80 and js["cells"] == 80 and js["threads"] == 3 and js["time_limit"] == 300.0
    assert js["aggregate"] == {"aggregate": True} and js["gurobi_params"] == {"Seed": 0}
    assert not out.exists()
