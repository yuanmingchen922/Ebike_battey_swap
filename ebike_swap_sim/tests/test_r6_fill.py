"""Round-6 fill-in script ``experiments/r6_fill.py``: retry selection on synthetic records
(status, sleep guard, last row per key wins), the stage plans of the specification (seeds,
limits, cells), the compliance layout parsing from a synthetic O2 ``records.jsonl``, the lane
writer, the ILP objective == ``evaluate.cost`` identity on a repriced toy instance, and -- when
the machine has memory for them (1.5 GB of free swap, or ``R6_FILL_SMOKE=1``) -- one tiny cell
per new stage end to end with ``--smoke``.  Threads 1 everywhere."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip("gurobipy")
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import toy_instance  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r5_x5_stress as X5  # noqa: E402
from experiments import r6_fill as F  # noqa: E402
from experiments import r6_penalty as R6  # noqa: E402

LAB = R6.BASE["label"]


def _swap_free_gb() -> float:
    try:
        out = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=10).stdout
        free = out.split("free =")[1].split("M")[0].strip()
        return float(free) / 1024.0
    except Exception:  # noqa: BLE001
        return 99.0


def _smoke_ok() -> bool:
    return os.environ.get("R6_FILL_SMOKE") == "1" or _swap_free_gb() >= 1.5


needs_memory = pytest.mark.skipif(not _smoke_ok(), reason="reduced-instance solver smoke: less than 1.5 GB of swap free "
                                                           "(set R6_FILL_SMOKE=1 to force)")


def _grid_row(seed: int, status: str, runtime: float, wall: float, limit: float = 300.0, targets: str = "relaxed",
              method: str = "ilp", **extra):
    return {"family": "usd4h", "calib": LAB, "seed": seed, "mult": 1.0, "targets": targets, "method": method,
            "status": status, "runtime_s": runtime, "wall_s": wall, "time_limit_s": limit, "time_limit_requested_s": limit,
            "mip_gap": 0.01 if status != "OPTIMAL" else 0.0, "total": 100.0, "P": 60.0, "w": 18.0, "v": 15.0, **extra}


# ---------------------------------------------------------------------------
# retry selection
# ---------------------------------------------------------------------------
def test_sleep_guard_and_retry_reason():
    assert F.retry_reason(_grid_row(0, "OPTIMAL", 22.0, 25.0)) is None
    assert F.retry_reason(_grid_row(0, "TIME_LIMIT", 300.03, 306.2)) == "not_optimal"           # a plain time limit
    assert F.retry_reason(_grid_row(0, "TIME_LIMIT", 459.5, 44.2)) == "sleep_truncated"          # runtime > wall + 10
    assert F.retry_reason(_grid_row(0, "TIME_LIMIT", 1092.7, 167.5)) == "sleep_truncated"        # wall < limit
    assert F.retry_reason(_grid_row(0, "TIME_LIMIT", 300.0, 305.0, limit=300.0)) == "not_optimal"
    assert F.retry_reason(_grid_row(0, "POLICY", 0.1, 0.1, method="r2")) is None
    assert F.retry_reason({"family": "usd4h", "method": "cell_error", "status": "ERROR"}) is None
    assert F.retry_reason(_grid_row(0, C.SKIPPED_BUDGET, 0.0, 0.0)) == "not_optimal"
    # X5 layout (no wall_s): runtime beyond the limit is the sleep signature
    x5 = {"key_md5": "k", "method": "ILP_tl600", "status": "TIME_LIMIT", "runtime_s": 991.5, "time_limit": 600.0, "gap": 0.02}
    assert F.retry_reason(x5) == "sleep_truncated"
    assert F.retry_reason({**x5, "runtime_s": 604.1, "gap": 1.005}) == "not_optimal"
    assert F.retry_reason({**x5, "status": "OPTIMAL", "runtime_s": 51.0}) is None
    assert not F.sleep_truncated(_grid_row(0, "OPTIMAL", 459.5, 44.2))                           # OPTIMAL is never truncated
    t = F.ilp_timing({"runtime_s": 1.0, "time_limit_used_s": 20.0})
    assert t == {"runtime": 1.0, "wall": None, "limit": 20.0}


def test_grid_retry_selection_last_row_per_key_wins(tmp_path):
    p = os.path.join(str(tmp_path), "records.jsonl")
    rows = [_grid_row(0, "TIME_LIMIT", 300.0, 305.0), _grid_row(0, "OPTIMAL", 120.0, 125.0),       # seed 0: fixed later
            _grid_row(1, "OPTIMAL", 120.0, 125.0), _grid_row(1, "TIME_LIMIT", 300.0, 305.0),       # seed 1: last is TL
            _grid_row(2, "TIME_LIMIT", 459.5, 44.2),                                                 # seed 2: sleep
            _grid_row(3, "OPTIMAL", 10.0, 12.0, targets="written"), _grid_row(3, "TIME_LIMIT", 300.0, 305.0),
            _grid_row(4, "POLICY", 0.1, 0.1, method="r2"),
            {"family": "usd4h", "calib": LAB, "seed": 5, "mult": 1.0, "targets": "*", "method": "cell_error", "status": "ERROR"}]
    for r in rows:
        C.append_jsonl(p, r)
    sel = F.select_grid_retries(p)
    keys = {k[2:] for k in sel}
    assert keys == {(1, 1.0, "relaxed", "ilp"), (2, 1.0, "relaxed", "ilp"), (3, 1.0, "relaxed", "ilp")}
    assert sel[("usd4h", LAB, 2, 1.0, "relaxed", "ilp")][2] == "sleep_truncated"
    assert sel[("usd4h", LAB, 1, 1.0, "relaxed", "ilp")][0] == 3                                     # record index of the last row
    cells = F.plan_grid_retries("headline", sel, 600.0)
    assert sorted((c.seed, c.ilp_targets, c.tl) for c in cells) == [(1, ("relaxed",), 600.0), (2, ("relaxed",), 600.0),
                                                                     (3, ("relaxed",), 600.0)]
    assert all(c.pr["label"] == LAB and c.case == "usd4h" for c in cells)
    # one cell with both targets unsolved -> one Cell with both targets
    C.append_jsonl(p, _grid_row(3, "TIME_LIMIT", 300.0, 305.0, targets="written"))
    cells = F.plan_grid_retries("headline", F.select_grid_retries(p), 600.0)
    assert [c.ilp_targets for c in cells if c.seed == 3] == [("written", "relaxed")]


def test_stress_retry_selection_takes_the_last_done_row(tmp_path):
    p = os.path.join(str(tmp_path), "records.jsonl")
    base = {"cell": "K10_B1_pack0.6", "seed": 2, "method": "ILP_tl600", "time_limit": 600.0}
    C.append_jsonl(p, {**base, "key_md5": "a", "status": "TIME_LIMIT", "runtime_s": 991.5, "gap": 0.02})
    C.append_jsonl(p, {**base, "key_md5": "a", "status": C.SKIPPED_BUDGET})                        # not done: the TL row stays
    C.append_jsonl(p, {**base, "key_md5": "b", "status": "TIME_LIMIT", "runtime_s": 600.0, "gap": 0.01})
    C.append_jsonl(p, {**base, "key_md5": "b", "status": "OPTIMAL", "runtime_s": 50.0, "gap": 0.0, "retry_of": 2})
    C.append_jsonl(p, {**base, "key_md5": "c", "method": "baseline_r2", "status": "OK"})
    sel = F.select_stress_retries(p)
    assert set(sel) == {("a", "ILP_tl600")} and sel[("a", "ILP_tl600")][2] == "sleep_truncated"
    cols = F.retry_cols(0, {**base, "status": "TIME_LIMIT", "runtime_s": 991.5, "gap": 0.02, "total": 700.0}, "sleep_truncated", 600.0)
    assert cols["retry_of_status"] == "TIME_LIMIT" and cols["retry_of_mip_gap"] == 0.02 and cols["retry_n"] == 1
    assert cols["retry_of_total"] == 700.0 and cols["retry_time_limit_s"] == 600.0


def test_retry_plan_defaults_and_dry_run(tmp_path, capsys):
    assert F.RETRY_TL == {"headline": 600.0, "psweep": 600.0, "vsweep": 600.0, "fleet": 600.0, "levers": 1800.0}
    root = str(tmp_path)
    hd = R6.stage_dir("headline", False, root)
    C.ensure_dir(hd)
    for r in (_grid_row(0, "TIME_LIMIT", 300.0, 305.0), _grid_row(1, "OPTIMAL", 10.0, 12.0)):
        C.append_jsonl(os.path.join(hd, R6.RECORDS), r)
    F.main(["--retry-unsolved", "--stage", "headline", "--dry-run", "--out-root", root])
    out = json.loads(capsys.readouterr().out)
    assert out["n_retries"] == 1 and out["time_limit_s"] == 600.0 and out["items"][0]["reason"] == "not_optimal"
    F.main(["--retry-unsolved", "--stage", "headline", "--dry-run", "--out-root", root, "--time-limit", "900"])
    assert json.loads(capsys.readouterr().out)["time_limit_s"] == 900.0
    with pytest.raises(SystemExit):
        F.main(["--retry-unsolved", "--stage", "stress", "--dry-run"])          # not a retry stage


def test_stress_retry_cases_keep_the_method_name_and_order_lockout_first(tmp_path):
    """The X5 retry re-solves under the ORIGINAL method name (the row key) at the new limit; the
    lock-out cells of the levers stage come before the reference (start pool)."""
    d = str(tmp_path)
    for cell, key in (("reference", "kref"), ("lockout0.25", "klock"), ("P0", "kp0")):
        C.append_jsonl(os.path.join(d, "cases.jsonl"), {"sub": "levers", "cell": cell, "seed": 1, "target": X5.RELAXED,
                                                        "key_md5": key, "ilp_method": "ILP_tl600", "phase": "x"})
        C.append_jsonl(os.path.join(d, R6.RECORDS), {"key_md5": key, "cell": cell, "seed": 1, "method": "ILP_tl600",
                                                     "status": "TIME_LIMIT", "runtime_s": 600.1, "time_limit": 600.0, "gap": 0.05})
    C.append_jsonl(os.path.join(d, R6.RECORDS), {"key_md5": "kp0", "cell": "P0", "seed": 1, "method": "ILP_tl600",
                                                 "status": "OPTIMAL", "runtime_s": 100.0, "time_limit": 600.0, "gap": 0.0})
    sel = F.select_stress_retries(os.path.join(d, R6.RECORDS))
    assert set(sel) == {("kref", "ILP_tl600"), ("klock", "ILP_tl600")}
    cases = F._stress_cases_for_retry("levers", sel, d, 1800.0, smoke=False)
    assert [c.cell for c in cases] == ["lockout0.25", "reference"] and all(c.ilp_tl == 1800.0 and c.seed == 1 for c in cases)
    assert all(c.n_bikes == 8 and c.target == X5.RELAXED for c in cases)


def test_retry_stress_runner_forces_only_the_ilp_row(tmp_path):
    """On a smoke-size levers case (instance generation only, no library, no solve): the runner's
    todo is exactly the forced ILP method, ``ilp_method`` is overridden to that name, other
    cases are untouched."""
    d = str(tmp_path)
    case = [c for c in R6.plan_levers_r6(R6.BASE, True, None) if c.cell == "reference"][0]
    w = case.builder()
    t = X5.target_copy(w, case.target)
    key = X5.content_key(t, C.pruning_for(t))
    assert cm.uniform_order_prices(t) == {"P": 60.0, "w": 18.0, "v": 15.0}
    prev = {"key_md5": key, "cell": "reference", "seed": 0, "method": "ILP_tl20", "status": "TIME_LIMIT", "runtime_s": 20.1,
            "time_limit": 20.0, "gap": 0.1, "total": 50.0}
    C.append_jsonl(os.path.join(d, R6.RECORDS), prev)
    if not hasattr(X5, "_r6_orig_ilp_method"):
        X5._r6_orig_ilp_method = X5.ilp_method
    runner = F.RetryStressRunner(d, "levers", R6.BASE, 1, {(key, "ILP_tl20"): (0, prev, "not_optimal")}, 40.0)
    _w, _t, k2, _pr, todo = runner.case_status(case)
    assert k2 == key and todo == ["ILP_tl20"] and runner.current_method(40.0) == "ILP_tl20"
    other = [c for c in R6.plan_levers_r6(R6.BASE, True, None) if c.cell == "P0"][0]
    _w, _t, k3, _pr, todo = runner.case_status(other)
    assert k3 != key and todo == [] and runner.current_method(40.0) == "ILP_tl40"
    assert not os.path.exists(os.path.join(d, "schedules", f"{key}_ILP_tl20.json"))


def test_stress_retry_forces_a_time_limit_row_within_the_reuse_gap(tmp_path):
    """A TIME_LIMIT row with a MIP gap of 0.5 % counts as done for the stage resume
    (``r5_x5_stress._is_done``) and as reusable (``common.reusable_ilp_row``), yet it is NOT
    OPTIMAL: the retry selection forces it (reason not_optimal) at a limit above its own, and
    skips it as a blind re-run at its own limit; a sleep-truncated row is forced at any limit."""
    p = os.path.join(str(tmp_path), "records.jsonl")
    base = {"cell": "K4_B1_pack0.6", "seed": 0, "method": "ILP_tl300", "time_limit": 300.0, "target": X5.RELAXED}
    tl_row = {**base, "key_md5": "g", "status": "TIME_LIMIT", "runtime_s": 300.0, "gap": 0.005, "total": 1217.0}
    slept = {**base, "key_md5": "s", "method": "ILP_tl600", "time_limit": 600.0, "status": "TIME_LIMIT", "runtime_s": 991.5,
             "gap": 0.023, "total": 847.9}
    for r in (tl_row, slept, {**base, "key_md5": "o", "status": "OPTIMAL", "runtime_s": 50.0, "gap": 0.0}):
        C.append_jsonl(p, r)
    assert X5._is_done(tl_row) and C.reusable_ilp_row(tl_row["status"], tl_row["gap"])
    sel = F.select_stress_retries(p)
    assert set(sel) == {("g", "ILP_tl300"), ("s", "ILP_tl600")}
    assert sel[("g", "ILP_tl300")][2] == "not_optimal" and sel[("s", "ILP_tl600")][2] == "sleep_truncated"
    run, skip = F.stress_retry_selection(p, 600.0)
    assert set(run) == {("g", "ILP_tl300"), ("s", "ILP_tl600")} and not skip
    run, skip = F.stress_retry_selection(p, 300.0)              # the 300 s row at 300 s: a blind re-run
    assert set(run) == {("s", "ILP_tl600")} and set(skip) == {("g", "ILP_tl300")}
    # the four plain 600 s TIME_LIMIT rows of fleet: skipped at the default 600 s, included at 1800 s
    plain600 = {**base, "key_md5": "q", "method": "ILP_tl600", "time_limit": 600.0, "status": "TIME_LIMIT", "runtime_s": 600.0,
                "gap": 0.006, "total": 943.8}
    C.append_jsonl(p, plain600)
    assert ("q", "ILP_tl600") in F.stress_retry_selection(p, 600.0)[1]
    assert ("q", "ILP_tl600") in F.stress_retry_selection(p, 1800.0)[0]
    assert F.case_id_of(tl_row) == ("K4_B1_pack0.6", 0, X5.RELAXED)


def _stub_ilp(status: str = "OPTIMAL", gap: float = 0.0):
    """``common.run_ilp_case`` replacement: returns the MIP start it was given as the solution
    (evaluated with the real check / cost / metrics), no Gurobi."""
    calls = []

    def run(inst, lib, mip_start=None, time_limit=None, threads=None, label="ilp", **kw):
        assert mip_start is not None, "the retry runner offers the rule schedules as start candidates"
        calls.append({"time_limit": time_limit, "threads": threads, "label": label})
        rep = C.check(inst, lib, mip_start)
        cst = C.cost(inst, lib, mip_start)
        return {"label": label, "schedule": mip_start, "stats": {"switches": {"aggregate": True}, "n_agg_arcs": 0},
                "status": status, "obj": cst["total"], "bound": cst["total"] * (1 - gap), "gap": gap, "runtime": 0.01,
                "build_time": 0.0, "n_binaries": 0, "n_vars": 0, "n_rows": 0, "mip_start_accepted": True,
                "mip_start_info": {"verified_status": "ok"}, "cost": cst, "check": rep, "families": C.family_counts(rep),
                "ok": rep["ok"], "identity_24_ok": rep.get("identity_24_ok"), "metrics": C.metrics(inst, lib, mip_start)}
    run.calls = calls
    return run


def _retry_case(case: X5.Case, tl: float) -> X5.Case:
    return X5.Case(case.sub, case.cell, case.seed, case.target, case.build_id, case.builder, float(tl), case.lp, case.phase,
                   dict(case.info), case.n_bikes, case.H)


def test_retry_stress_runner_resolves_a_forced_row_with_a_stubbed_solver(tmp_path, monkeypatch, capsys):
    """Regression for the server fleet retry that reported every forced case ``reused``: the
    recorded ``key_md5`` of the forced row differs from the content key of the rebuilt instance
    (the records were written on another machine).  The row -- TIME_LIMIT at a 0.5 % gap, i.e.
    done and reusable -- must still be re-solved at the new limit under its method name, the new
    row must keep the recorded key (it supersedes the old one) and carry ``key_md5_rebuilt``, and
    no ``cases.jsonl`` note may be added.  A forced row whose rebuilt instance really differs
    (``orders_md5``) is skipped as RETRY_SKIPPED, nothing emitted.  Smoke-size levers instances
    (4 bikes, 2 h), library and rules real, the solver stubbed, Threads 1."""
    d = str(tmp_path)
    plan = R6.plan_levers_r6(R6.BASE, True, None)
    ref = [c for c in plan if c.cell == "reference"][0]
    p0 = [c for c in plan if c.cell == "P0"][0]
    w = ref.builder()
    t = X5.target_copy(w, ref.target)
    key = X5.content_key(t, C.pruning_for(t))
    recorded = "0123456789abcdef0123456789abcdef"                  # != key: the drifted recording
    prev = {"sub": "levers", "key_md5": recorded, "cell": "reference", "seed": 0, "target": ref.target, "method": "ILP_tl20",
            "status": "TIME_LIMIT", "runtime_s": 20.1, "time_limit": 20.0, "gap": 0.005, "total": 1.0e9,
            "orders_md5": X5.orders_md5(t), "demand_md5": C.demand_md5(t), "n_bikes": len(t.bikes), "n_orders": len(t.orders),
            "H": t.H, "L": t.L}
    other = {**prev, "key_md5": "fedcba9876543210fedcba9876543210", "cell": "P0", "orders_md5": "not-the-same-orders"}
    C.append_jsonl(os.path.join(d, R6.RECORDS), prev)
    C.append_jsonl(os.path.join(d, R6.RECORDS), other)
    for r in (prev, other):
        C.append_jsonl(os.path.join(d, "cases.jsonl"), {"sub": "levers", "cell": r["cell"], "seed": 0, "target": ref.target,
                                                        "key_md5": r["key_md5"], "ilp_method": "ILP_tl20", "phase": "x"})
    assert X5._is_done(prev) and C.reusable_ilp_row(prev["status"], prev["gap"])
    sel, skip = F.stress_retry_selection(os.path.join(d, R6.RECORDS), 40.0)
    assert set(sel) == {(recorded, "ILP_tl20"), (other["key_md5"], "ILP_tl20")} and not skip
    stub = _stub_ilp()
    monkeypatch.setattr(C, "run_ilp_case", stub)
    monkeypatch.setattr(X5, "sched_cols", R6._sched_cols_r6)
    runner = F.RetryStressRunner(d, "levers", R6.BASE, 1, sel, 40.0)
    with F.ilp_method_override(runner):
        runner.run_plan("levers", [_retry_case(ref, 40.0), _retry_case(p0, 40.0)], 600.0)
    out = capsys.readouterr().out
    assert '"reused"' not in out and '"ilp_status": "OPTIMAL"' in out and "content key drifted" in out
    assert "RETRY_SKIPPED" in out and "orders_md5" in out
    assert stub.calls == [{"time_limit": 40.0, "threads": 1, "label": "ILP_tl20"}]       # one solve, at the new limit
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    assert len(rows) == 3, [r.get("method") for r in rows]                              # exactly one row appended
    new = rows[-1]
    assert new["method"] == "ILP_tl20" and new["key_md5"] == recorded and new["key_md5_rebuilt"] == key
    assert new["retry_of"] == 0 and new["retry_reason"] == "not_optimal" and new["retry_time_limit_s"] == 40.0
    assert new["time_limit"] == 40.0 and new["status"] == "OPTIMAL" and new["source"] == "r6_fill_retry"
    assert new["retry_worse"] is False and new["retry_of_mip_gap"] == 0.005 and new["obj_eq_eval"] is True
    assert R6.last_done_rows(os.path.join(d, R6.RECORDS))[(recorded, "ILP_tl20")]["retry_of"] == 0
    assert len(C.load_jsonl(os.path.join(d, "cases.jsonl"))) == 2                        # no note added
    assert runner.n_drift == 1 and not runner.force.get((recorded, "ILP_tl20")) and len(runner.skipped_mismatch) == 1
    assert runner.skipped_mismatch[0]["cell"] == "P0" and (other["key_md5"], "ILP_tl20") in runner.force
    assert os.path.exists(os.path.join(d, "schedules", f"{recorded}_ILP_tl20.json"))      # incumbent under the recorded key
    t2 = F.retries_table("levers", d)
    assert len(t2) == 1 and t2.iloc[0]["new_status"] == "OPTIMAL" and t2.iloc[0]["prev_mip_gap"] == 0.005
    # the same forced row matched by its content key (no drift) carries no key_md5_rebuilt
    d2 = str(tmp_path / "exact")
    prev2 = {**prev, "key_md5": key}
    C.append_jsonl(os.path.join(d2, R6.RECORDS), prev2)
    runner2 = F.RetryStressRunner(d2, "levers", R6.BASE, 1, {(key, "ILP_tl20"): (0, prev2, "not_optimal")}, 40.0)
    with F.ilp_method_override(runner2):
        runner2.run_plan("levers", [_retry_case(ref, 40.0)], 600.0)
    rows2 = C.load_jsonl(os.path.join(d2, R6.RECORDS))
    assert len(rows2) == 2 and rows2[-1]["key_md5"] == key and "key_md5_rebuilt" not in rows2[-1] and runner2.n_drift == 0


def test_prune_orphan_case_notes(tmp_path):
    """A note whose key has no row while another note of the same cell has rows (left by the
    failed retry: it noted the cell under the drifted key) is moved to cases_orphans.jsonl; a
    cell whose only note has no rows yet (a stage still running) is kept."""
    d = str(tmp_path)
    rec = os.path.join(d, R6.RECORDS)
    C.append_jsonl(rec, {"key_md5": "good", "cell": "K4_B1_pack0.6", "seed": 0, "target": X5.RELAXED, "method": "ILP_tl300", "status": "TIME_LIMIT"})
    note = {"sub": "fleet", "cell": "K4_B1_pack0.6", "seed": 0, "target": X5.RELAXED, "phase": "ilp"}
    C.append_jsonl(os.path.join(d, "cases.jsonl"), {**note, "key_md5": "good", "ilp_method": "ILP_tl300"})
    C.append_jsonl(os.path.join(d, "cases.jsonl"), {**note, "key_md5": "drifted", "ilp_method": "ILP_tl600"})
    C.append_jsonl(os.path.join(d, "cases.jsonl"), {**note, "cell": "K6_B1_pack0.6", "key_md5": "pending", "ilp_method": "ILP_tl300"})
    assert R6.wide_r6(d).iloc[0]["key_md5"] == "drifted"                 # the orphan hides the cell's rows
    dry = F.prune_orphan_case_notes(d, dry_run=True)
    assert [o["key_md5"] for o in dry] == ["drifted"] and len(C.load_jsonl(os.path.join(d, "cases.jsonl"))) == 3
    gone = F.prune_orphan_case_notes(d)
    assert [o["key_md5"] for o in gone] == ["drifted"]
    left = C.load_jsonl(os.path.join(d, "cases.jsonl"))
    assert [n["key_md5"] for n in left] == ["good", "pending"]
    assert C.load_jsonl(os.path.join(d, "cases_orphans.jsonl"))[0]["key_md5"] == "drifted"
    assert R6.wide_r6(d).set_index("cell").loc["K4_B1_pack0.6", "key_md5"] == "good"
    assert F.prune_orphan_case_notes(d) == []


def _x5_case(cell: str, seed: int, target: str, tl, lp: bool, phase: str) -> X5.Case:
    return X5.Case("stress", cell, seed, target, f"b:{cell}:{seed}", lambda: None, tl, lp, phase, {"K": 6}, 6, 48)


def test_stress_runner_note_case_is_phase_aware_and_wide_r6_reads_the_ilp_row(tmp_path):
    """An LP-only note and a later ILP note of the same (sub, cell, seed, target, key) both land in
    cases.jsonl (X5's dedup hid the second); wide_r6 takes the row naming the ILP method."""
    d = str(tmp_path)
    runner = R6.StressRunner(d, "stress", R6.BASE, 1)
    lp_only = _x5_case("r5_stress4h_K6", 0, X5.RELAXED, None, True, "lp_only")
    with_ilp = _x5_case("r5_stress4h_K6", 0, X5.RELAXED, 300.0, True, "boundary")
    runner.note_case(lp_only, "k")
    runner.note_case(lp_only, "k")                     # a repeat without an ILP is still deduplicated
    runner.note_case(with_ilp, "k")
    runner.note_case(with_ilp, "k")
    notes = C.load_jsonl(os.path.join(d, "cases.jsonl"))
    assert [(n["phase"], n["ilp_method"]) for n in notes] == [("lp_only", None), ("boundary", "ILP_tl300")]
    base = {"key_md5": "k", "status": "OK", "rule": "r2", "total": 10.0, "total_end_adjusted": 11.0}
    for m in ("baseline_r2", "baseline_r5", "best_rule"):
        C.append_jsonl(os.path.join(d, R6.RECORDS), {**base, "method": m})
    C.append_jsonl(os.path.join(d, R6.RECORDS), {"key_md5": "k", "method": "ILP_tl300", "status": "TIME_LIMIT", "total": 9.0,
                                                 "total_end_adjusted": 9.5, "gap": 0.01, "time_limit": 300.0})
    w = R6.wide_r6(d)
    assert len(w) == 1 and w.iloc[0]["ilp_method"] == "ILP_tl300" and w.iloc[0]["ilp_total"] == 9.0
    # a fresh runner on the same directory knows the ILP note and does not note the cell again
    runner2 = R6.StressRunner(d, "stress", R6.BASE, 1)
    runner2.note_case(with_ilp, "k")
    runner2.note_case(lp_only, "k")
    assert len(C.load_jsonl(os.path.join(d, "cases.jsonl"))) == 2


def test_retry_worse_rows_are_ignored_and_blind_reruns_are_skipped(tmp_path):
    p = os.path.join(str(tmp_path), "records.jsonl")
    base = {"cell": "K8_B1_pack0.6", "seed": 1, "method": "ILP_tl600", "time_limit": 600.0}
    C.append_jsonl(p, {**base, "key_md5": "a", "status": "TIME_LIMIT", "runtime_s": 600.1, "gap": 0.013, "total": 870.0})
    C.append_jsonl(p, {**base, "key_md5": "a", "status": "TIME_LIMIT", "runtime_s": 600.0, "gap": 0.02, "total": 875.0,
                       "retry_of": 0, "retry_worse": True})                                          # worse re-solve: ignored
    C.append_jsonl(p, {**base, "key_md5": "b", "status": "TIME_LIMIT", "runtime_s": 991.5, "gap": 0.02, "total": 848.0})  # sleep
    C.append_jsonl(p, {**base, "key_md5": "c", "status": C.SKIPPED_BUDGET})
    rows = R6.last_done_rows(p)
    assert rows[("a", "ILP_tl600")]["total"] == 870.0 and "retry_worse" not in rows[("a", "ILP_tl600")]
    sel = F.select_stress_retries(p)
    assert set(sel) == {("a", "ILP_tl600"), ("b", "ILP_tl600"), ("c", "ILP_tl600")} and sel[("a", "ILP_tl600")][0] == 0
    run, skip = F.stress_retry_selection(p, 600.0)
    assert set(skip) == {("a", "ILP_tl600")} and set(run) == {("b", "ILP_tl600"), ("c", "ILP_tl600")}   # a: blind re-run at 600 s
    run, skip = F.stress_retry_selection(p, 1200.0)
    assert not skip and len(run) == 3
    assert F.blind_rerun(sel[("a", "ILP_tl600")][1], "not_optimal", 600.0)
    assert not F.blind_rerun(sel[("b", "ILP_tl600")][1], "sleep_truncated", 600.0)
    assert not F.blind_rerun({"status": C.SKIPPED_BUDGET, "time_limit": 600.0}, "not_optimal", 600.0)


def test_retry_stress_runner_marks_a_worse_resolve_and_keeps_its_incumbent_file(tmp_path):
    d = str(tmp_path)
    prev = {"key_md5": "k", "cell": "reference", "seed": 0, "method": "ILP_tl600", "status": "TIME_LIMIT", "runtime_s": 600.1,
            "time_limit": 600.0, "gap": 0.1, "total": 1000.0}
    C.append_jsonl(os.path.join(d, R6.RECORDS), prev)
    runner = F.RetryStressRunner(d, "levers", R6.BASE, 1, {("k", "ILP_tl600"): (0, prev, "not_optimal")}, 1800.0)
    runner._cur, runner._key = ("ILP_tl600", (0, prev, "not_optimal")), "k"
    runner.emit("levers", {"key_md5": "k", "cell": "reference", "seed": 0, "method": "ILP_tl600", "status": "TIME_LIMIT",
                           "runtime_s": 1800.0, "time_limit": 1800.0, "gap": 0.12, "total": 1010.0})
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    assert rows[-1]["retry_worse"] is True and rows[-1]["retry_of"] == 0 and runner._last_ilp_row is None
    assert R6.last_done_rows(os.path.join(d, R6.RECORDS))[("k", "ILP_tl600")]["total"] == 1000.0
    # the previous row (index 0, 600 s) stays the candidate: skipped at 600 s (blind), re-solved at a larger limit
    sel = F.select_stress_retries(os.path.join(d, R6.RECORDS))
    assert runner.n_worse == 1 and set(sel) == {("k", "ILP_tl600")} and sel[("k", "ILP_tl600")][0] == 0
    assert not F.stress_retry_selection(os.path.join(d, R6.RECORDS), 600.0)[0]
    assert F.stress_retry_selection(os.path.join(d, R6.RECORDS), 1800.0)[1] == {}
    t = F.retries_table("levers", d)
    assert len(t) == 1 and bool(t.iloc[0]["retry_worse"]) and t.iloc[0]["improved_usd"] == -10.0
    # ...and a better re-solve replaces the row and keeps its incumbent
    runner._cur = ("ILP_tl600", (0, prev, "not_optimal"))
    runner.emit("levers", {"key_md5": "k", "cell": "reference", "seed": 0, "method": "ILP_tl600", "status": "TIME_LIMIT",
                           "runtime_s": 1800.0, "time_limit": 1800.0, "gap": 0.05, "total": 990.0})
    assert runner._last_ilp_row == ("k", "ILP_tl600")
    assert R6.last_done_rows(os.path.join(d, R6.RECORDS))[("k", "ILP_tl600")]["total"] == 990.0


def test_no_transfer_variants_and_saved_incumbent_round_trip(tmp_path):
    from ebike_swap_sim import Schedule
    with_t = Schedule(x={"b1": [1, 2]}, u={"o1": 1}, c={("j", 0, 3): 1}, h={"svc": 1}, z={("svc", 0): 1})
    without = Schedule(x={"b1": [1, 2]}, u={"o1": 1}, c={("j", 0, 3): 1}, h={}, z={})
    v = R6.no_transfer_variants([("ilp:lockout0.25:rho0_R0", with_t), ("rule:r2@reference:rho0_R0", without),
                                 ("ilp:lockout0.1:rho0_R0|no_transfers", without)])
    assert [lab for lab, _s in v] == ["ilp:lockout0.25:rho0_R0|no_transfers"]
    assert v[0][1].h == {} and v[0][1].z == {} and v[0][1].x == {"b1": [1, 2]} and v[0][1].u == {"o1": 1}
    assert with_t.h == {"svc": 1}                                                          # the original is untouched
    d = str(tmp_path)
    with open(R6.incumbent_path(d, "k", "ILP_tl600"), "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(X5.portable(without).to_dict()), fh)
    s = R6.load_incumbent(d, "k", "ILP_tl600")
    assert s is not None and dict(s.u) == {"o1": 1} and R6.load_incumbent(d, "k", "ILP_tl300") is None
    assert os.path.basename(R6.incumbent_path(d, "k", "ILP_tl600")) == "k_ILP_tl600.json"


def test_load_jsonl_lenient_skips_a_half_written_last_line(tmp_path, capsys):
    from experiments import r6_o2_siting as O2
    p = os.path.join(str(tmp_path), "records.jsonl")
    C.append_jsonl(p, {"kind": "budget_result", "target": "written", "budget": 2 * O2.BUDGET_UNIT, "best_layout": "M03:SC:B3:C2"})
    with open(p, "a", encoding="utf-8") as fh:
        fh.write('{"kind": "budget_result", "target": "written", "bud')
    with pytest.raises(ValueError):
        C.load_jsonl(p)
    assert len(F.load_jsonl_lenient(p)) == 1 and "does not parse" in capsys.readouterr().out
    assert F.o2_best_layout(p)["best_layout"] == "M03:SC:B3:C2"


# ---------------------------------------------------------------------------
# stage plans
# ---------------------------------------------------------------------------
def test_stress_plan_matches_the_specification():
    plan = F.plan_stress_r6(R6.BASE, smoke=False)
    by = {}
    for c in plan:
        by.setdefault((c.cell, c.target, c.ilp_tl, c.lp), set()).add(c.seed)
    assert by[("r5_stress4h_k10_K10", X5.RELAXED, 600.0, True)] == set(range(5))
    assert by[("r5_stress8h_K6", X5.RELAXED, 600.0, True)] == {0, 1, 2}
    assert by[("r5_stress4h_K6", "written", 300.0, True)] == set(range(5))
    # the boundary reference rho0_R0 (= the relaxed K6 cell) is ONE case per seed carrying the LP of
    # the shadow-price block and the 300 s ILP: X5.Runner.note_case dedups on (sub, cell, seed,
    # target, key), so a separate LP-only note of the same cell hid the ILP row from the analysis
    assert by[("r5_stress4h_K6", X5.RELAXED, 300.0, True)] == {0, 1, 2}
    assert by[("r5_stress4h_K6", X5.RELAXED, None, True)] == {3, 4}                      # LP-only relaxed on the other seeds
    assert by[("r5_stress4h_k8_K8", X5.RELAXED, None, True)] == set(range(5))            # and at 8 bikes
    labels = {c.target for c in plan if c.phase == "boundary"}
    assert labels == set(X5.boundary_specs()) and C.PERIODIC_LABEL in labels and len(labels) == 9
    assert all(c.ilp_tl == 300.0 and c.lp == (c.target == X5.RELAXED) and c.seed in (0, 1, 2)
               for c in plan if c.phase == "boundary")
    assert [c.target for c in plan if c.phase == "boundary"][:3] == [X5.RELAXED] * 3        # reference first (start pool)
    tags = [(c.cell, c.seed, c.target) for c in plan]
    assert len(tags) == len(set(tags))                                                    # no case is noted twice
    assert [c.H for c in plan if c.cell == "r5_stress8h_K6"] == [96, 96, 96]
    assert len(plan) == 2 + 5 + 5 + 27 + 5 + 3
    assert [c.cell for c in plan[:7]] == ["r5_stress4h_K6"] * 2 + ["r5_stress4h_k8_K8"] * 5   # cheap LP-only cells first
    sub = F.plan_stress_r6(R6.BASE, smoke=False, seeds=[0, 1])
    assert {c.seed for c in sub} == {0, 1}
    sm = F.plan_stress_r6(R6.BASE, smoke=True)
    assert len(sm) == 2 and {c.target for c in sm} == {X5.RELAXED, "written"} and all(c.ilp_tl == F.SMOKE_TL for c in sm)


def test_pack_levers_ext_rolling_ext_transfers_and_rl_plans():
    pack = F.plan_pack_r6(R6.BASE, smoke=False)
    assert len(pack) == 144 and all(c.ilp_tl is None and not c.lp for c in pack)
    assert {(c.info["K"], c.info["B_per_site"], c.info["pack_kwh"]) for c in pack} == \
        {(k, b, p) for k in (4, 6, 8, 10) for b in (1, 2, 3, 4) for p in (0.5, 0.75, 1.0)}
    assert {c.seed for c in pack} == {0, 1, 2}
    lv = F.plan_levers_ext_r6(R6.BASE, smoke=False)
    assert len(lv) == 20 and {c.cell for c in lv} == {"eps50", "M2", "lockout0.05", "lockout0.1"}
    assert all(c.ilp_tl == 600.0 and c.target == X5.RELAXED and c.n_bikes == 8 for c in lv) and {c.seed for c in lv} == set(range(5))
    assert all(c.info["lockout_n_target"] == 1 for c in lv if c.cell.startswith("lockout"))
    items = F.rolling_ext_items(False, None)
    assert len(items) == 45 and {(p, lam) for _c, _s, p, lam in items} == {("rolling", 0.0), ("rolling", 20.0), ("forecast", 10.0)}
    assert {(c, s) for c, s, _p, _l in items} == {("usd4h", s) for s in range(10)} | {("r5_stress4h", s) for s in range(5)}
    assert F.rolling_ext_items(True, None) == [("usd4h", 0, "rolling", 0.0), ("usd4h", 0, "forecast", 10.0)]
    d = F.transfers_design(False, None)
    assert d == {"seeds": [0, 1, 2, 3, 4], "layouts": ["colocated", "separated_1hub", "separated_2hubs"],
                 "targets": ["relaxed", "written"], "timetables": ["r3", "cyclic"], "switches": ["none", "free"], "tl": 300.0}
    assert F.transfers_design(True, None)["tl"] == F.SMOKE_TL
    a = argparse.Namespace(smoke=False, dry_run=False, seeds=None, budget_min=270.0, ppo_seeds=[1, 2])
    argv = F.rl_seed_argv(a, "/tmp/x")
    assert "--no-ilp" in argv and "--no-written" in argv and argv[argv.index("--ilp-time-limit") + 1] == "300.0"
    assert F.PPO_SEEDS == (1, 2) and set(F.EST_MIN) == set(F.NEW_STAGES) == set(F.WALL_BUDGET_MIN)


# ---------------------------------------------------------------------------
# compliance layout parsing
# ---------------------------------------------------------------------------
def test_compliance_layout_parsing_from_synthetic_o2_records(tmp_path, capsys):
    from experiments import r6_o2_siting as O2
    p = os.path.join(str(tmp_path), "records.jsonl")
    unit = O2.BUDGET_UNIT
    with pytest.raises(FileNotFoundError):
        F.o2_best_layout(p)
    C.append_jsonl(p, {"kind": "budget_result", "target": "relaxed", "budget": 2 * unit, "best_layout": "M01:SC:B2:C1", "certified": True})
    C.append_jsonl(p, {"kind": "budget_result", "target": "written", "budget": 1 * unit, "best_layout": "M02:SC:B2:C1", "certified": True})
    with pytest.raises(LookupError):
        F.o2_best_layout(p)
    C.append_jsonl(p, {"kind": "budget_result", "target": "written", "budget": 2 * unit, "best_layout": "M03:SC:B3:C2", "UB": 700.0,
                       "LB": 699.0, "gap": 0.001, "certified": False})
    C.append_jsonl(p, {"kind": "budget_result", "target": "written", "budget": 2 * unit, "best_layout": "M04:SC:B3:C2|M09:S:B2:C0",
                       "UB": 690.0, "LB": 689.5, "gap": 0.0007, "certified": True})
    r = F.o2_best_layout(p)
    assert r["best_layout"] == "M04:SC:B3:C2|M09:S:B2:C0" and r["certified"] is True        # last row wins
    args = argparse.Namespace(smoke=False, layout_key=None, o2_records=p)
    lays = F.compliance_layouts(args)
    assert [l["label"] for l in lays] == ["o2_best_m2", "r5_chosen"] and lays[1]["layout_key"] == F.R5_LAYOUT
    assert lays[0]["o2_UB"] == 690.0
    lays = F.compliance_layouts(argparse.Namespace(smoke=False, layout_key=F.R5_LAYOUT, o2_records=p))
    assert len(lays) == 1 and lays[0]["source"] == "cli --layout-key"
    F.main(["--check-o2", "--o2-records", p])
    assert json.loads(capsys.readouterr().out)["best_layout"].startswith("M04")
    with pytest.raises(SystemExit) as ex:
        F.main(["--check-o2", "--o2-records", os.path.join(str(tmp_path), "absent.jsonl")])
    assert ex.value.code == 1
    # the stage itself fails clearly without the file / without the written m=2 row
    with pytest.raises(SystemExit, match="O2 Manhattan records not found"):
        F.main(["--stage", "compliance", "--o2-records", os.path.join(str(tmp_path), "absent2.jsonl"), "--out-root", str(tmp_path)])
    nomatch = os.path.join(str(tmp_path), "nomatch.jsonl")
    C.append_jsonl(nomatch, {"kind": "budget_result", "target": "written", "budget": 1 * unit, "best_layout": "M02:SC:B2:C1"})
    with pytest.raises(SystemExit, match="budget_result"):
        F.main(["--stage", "compliance", "--o2-records", nomatch, "--out-root", str(tmp_path)])
    capsys.readouterr()
    F.main(["--stage", "compliance", "--dry-run", "--o2-records", p, "--out-root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["layout_error"] is None and out["layouts"][0]["layout_key"].startswith("M04") and out["psi"] == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_seed_cache_copies_only_the_requested_layouts(tmp_path):
    src = os.path.join(str(tmp_path), "src")
    dst = os.path.join(str(tmp_path), "dst")
    C.ensure_dir(os.path.join(src, "schedules"))
    sp = os.path.join(src, "schedules", "k1.json")
    with open(sp, "w") as fh:
        json.dump({"x": 1}, fh)
    C.append_jsonl(os.path.join(src, "index.jsonl"), {"key": "k1", "layout_key": "A", "schedule_path": sp})
    C.append_jsonl(os.path.join(src, "index.jsonl"), {"key": "k2", "layout_key": "B"})
    assert F.seed_cache(src, dst, ["A"]) == 1
    rows = C.load_jsonl(os.path.join(dst, "index.jsonl"))
    assert len(rows) == 1 and rows[0]["schedule_path"].startswith(dst) and os.path.exists(rows[0]["schedule_path"])
    assert F.seed_cache(src, dst, ["A"]) == 0                                               # idempotent
    assert len(C.load_jsonl(os.path.join(src, "index.jsonl"))) == 2                          # the source is untouched


# ---------------------------------------------------------------------------
# lanes
# ---------------------------------------------------------------------------
def test_lane_writer(tmp_path, monkeypatch):
    # hermetic: the retry counts come from the round-6 digest, not from the live r6 records (once
    # the retries have run, the records hold far fewer unsolved cells and the balance of the
    # original plan no longer applies; R7 fixer pass, review minor item)
    monkeypatch.setattr(F, "RECORDS", "__absent_records_for_the_lane_test__.jsonl")
    launch = F.write_lanes(str(tmp_path))
    assert sorted(os.listdir(str(tmp_path))) == ["lane_1.sh", "lane_2.sh", "lane_3.sh", "lane_4.sh", "launch.json"]
    lanes = {l["lane"]: l for l in launch["lanes"]}
    names = {k: [c["name"] for c in l["commands"]] for k, l in lanes.items()}
    assert names["lane_4"] == ["r6_rl_seeds", "r6_analyse_lane_4"]                            # rl_seeds alone
    assert names["lane_3"][-2:] == ["r6_compliance", "r6_analyse_lane_3"]                     # compliance last
    all_names = sum(names.values(), [])
    for st in F.NEW_STAGES:
        assert f"r6_{st}" in all_names
    for st in F.RETRY_STAGES:
        assert f"r6_retry_{st}" in all_names
    s3 = open(os.path.join(str(tmp_path), "lane_3.sh")).read()
    assert s3.index("wait_for_o2\n") < s3.index("run r6_compliance") and "caffeinate -i" in s3 and "--check-o2" in s3
    # bounded wait: on a timeout compliance runs on the round-5 layout only, so the lane's analyse still runs
    assert f"-ge {F.O2_WAIT_MAX_POLLS}" in s3 and "return 1" in s3 and f"--layout-key '{F.R5_LAYOUT}'" in s3
    assert s3.count("run r6_compliance") == 2 and s3.index("if [ $? -eq 0 ]") < s3.index("run r6_compliance")
    # every lane's final analyse re-runs the r6_penalty rolling analysis (joins the retried headline / psweep rows)
    assert "experiments/r6_penalty.py --stage rolling --analyse" in F.ANALYSE_ALL
    for k in (1, 2, 3, 4):
        sk = open(os.path.join(str(tmp_path), f"lane_{k}.sh")).read()
        assert "r6_penalty.py --stage rolling --analyse" in sk and sk.rstrip().endswith('>> "$ST"')
    assert launch["status"].startswith("not started") and all(l["pid"] is None for l in launch["lanes"])
    mins = [l["expected_wall_min"] for l in launch["lanes"]]
    assert max(mins[:3]) - min(mins[:3]) < 90                                                  # balanced solver lanes


# ---------------------------------------------------------------------------
# objective identity on a repriced toy instance (Threads 1)
# ---------------------------------------------------------------------------
def test_ilp_objective_equals_evaluator_cost_on_a_repriced_toy():
    inst = cm.reprice_orders(toy_instance(), P=60.0, w=18.0, v=15.0, source="test")
    assert cm.uniform_order_prices(inst) == {"P": 60.0, "w": 18.0, "v": 15.0}
    lib, _ = C.build_library(inst, None)
    assert cm.check_lib_prices(inst, lib)["ok"]
    rec = C.run_ilp_case(inst, lib, threads=1, time_limit=30.0, params=dict(C.ILP_PARAMS_R3), aggregate=True)
    assert rec["status"] == "OPTIMAL" and rec["cost"] is not None
    assert abs(rec["obj"] - rec["cost"]["total"]) <= 1e-6 * max(1.0, abs(rec["obj"]))
    assert R6.obj_check_cols(rec)["obj_eq_eval"] is True


# ---------------------------------------------------------------------------
# end to end: compliance on the toy siting instances (Threads 1, seconds)
# ---------------------------------------------------------------------------
def test_compliance_smoke_on_toy_layouts(tmp_path):
    root = str(tmp_path)
    F.main(["--stage", "compliance", "--smoke", "--out-root", root, "--threads", "1", "--psi", "0", "1"])
    d = F.stage_dir("compliance", True, root)
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    price = {(r["layout_key"], r["policy"]): r for r in rows if r.get("kind") == "price"}
    assert {k[1] for k in price} == {"ilp", "selfish", "baseline"} and len({k[0] for k in price}) == 2
    assert all(r["P"] == 60.0 and r["v"] == 15.0 for r in price.values())
    comp = [r for r in rows if r.get("kind") == "compliance" and r.get("status") == "OK"]
    assert {float(r["alpha_c"]) for r in comp} == {0.0, 1.0} and {r["draw"] for r in comp} == {0, 1}
    summ = [r for r in rows if r.get("kind") == "compliance_summary" and r.get("complete")]
    v1 = {r["layout_key"]: r["V"] for r in summ if float(r["alpha_c"]) == 1.0}
    for key, v in v1.items():                                   # psi = 1 with the plan station layer = the ILP value
        assert v == pytest.approx(price[(key, "ilp")]["V"], abs=1e-6)
    assert os.path.exists(os.path.join(d, "RESULTS.md")) and os.path.exists(os.path.join(d, "per_draw.csv"))
    # resume: nothing is solved again
    n = len(rows)
    F.main(["--stage", "compliance", "--smoke", "--out-root", root, "--threads", "1", "--psi", "0", "1"])
    rows2 = C.load_jsonl(os.path.join(d, R6.RECORDS))
    assert len([r for r in rows2 if r.get("kind") in ("price", "compliance")]) == len([r for r in rows if r.get("kind") in ("price", "compliance")])
    assert len(rows2) == n + 1                                   # only the plan row


# ---------------------------------------------------------------------------
# reduced-instance smokes (memory permitting)
# ---------------------------------------------------------------------------
@needs_memory
def test_retry_grid_smoke_appends_a_marked_row(tmp_path):
    """A solved tiny headline cell, its ILP row re-labelled as sleep-truncated, then the retry:
    a new row under the same key (last wins) with retry_of and the previous status."""
    root = str(tmp_path)
    hd = R6.stage_dir("headline", True, root)
    runner = R6.GridRunner("headline", hd, 1, C.WallBudget(600.0, margin_s=0.0, min_solve_s=1.0), True, root)
    runner.run([R6.Cell("usd4h", R6.BASE, 0, 1.0, ("relaxed",), ("relaxed",), 30.0)])
    key = R6.grid_key("usd4h", LAB, 0, 1.0, "relaxed", "ilp")
    row = dict(runner.done[key])
    assert row["status"] == "OPTIMAL"
    fake = {**row, "status": "TIME_LIMIT", "runtime_s": row["wall_s"] + 50.0, "mip_gap": 0.5}
    C.append_jsonl(os.path.join(hd, R6.RECORDS), fake)
    sel = F.select_grid_retries(os.path.join(hd, R6.RECORDS))
    assert set(sel) == {key} and sel[key][2] == "sleep_truncated"
    F.main(["--retry-unsolved", "--stage", "headline", "--smoke", "--out-root", root, "--threads", "1", "--time-limit", "30"])
    rows = C.load_jsonl(os.path.join(hd, R6.RECORDS))
    last = [r for r in rows if r["method"] == "ilp"][-1]
    assert last["status"] == "OPTIMAL" and last["retry_of"] == len(rows) - 2 and last["retry_of_status"] == "TIME_LIMIT"
    assert last["retry_reason"] == "sleep_truncated" and last["retry_time_limit_s"] == 30.0 and last["obj_eq_eval"]
    assert last["mip_start_variant"] in ("prior_incumbent", "r2@relaxed", "r5_range@relaxed", "r5@relaxed")
    assert not F.select_grid_retries(os.path.join(hd, R6.RECORDS))
    assert os.path.exists(os.path.join(hd, "retries.csv"))        # the retry run ends with analyse_retry
    os.remove(os.path.join(hd, "retries.csv"))
    t = F.retries_table("headline", hd)                             # pure: nothing written
    assert len(t) == 1 and t.iloc[0].new_status == "OPTIMAL" and os.path.exists(os.path.join(hd, "retries.csv")) is False
    F.main(["--retry-unsolved", "--stage", "headline", "--smoke", "--out-root", root, "--analyse"])
    assert os.path.exists(os.path.join(hd, "retries.csv")) and len(pd.read_csv(os.path.join(hd, "retries.csv"))) == 1


@needs_memory
def test_stress_smoke_cell(tmp_path):
    root = str(tmp_path)
    F.main(["--stage", "stress", "--smoke", "--out-root", root, "--threads", "1"])
    d = F.stage_dir("stress", True, root)
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    ilp = [r for r in rows if r["method"].startswith("ILP_tl")]
    assert len(ilp) == 2 and all(r["obj_eq_eval"] and r["P"] == 60.0 for r in ilp)
    assert [r for r in rows if r["method"] == "LP"] and os.path.exists(os.path.join(d, "price_of_recovery.csv"))
    assert os.path.exists(os.path.join(d, "RESULTS.md"))


@needs_memory
def test_rolling_ext_smoke_cell(tmp_path):
    root = str(tmp_path)
    F.main(["--stage", "rolling_ext", "--smoke", "--out-root", root, "--threads", "1"])
    d = F.stage_dir("rolling_ext", True, root)
    rows = [r for r in C.load_jsonl(os.path.join(d, R6.RECORDS)) if r["status"] == "ROLLING"]
    assert {(r["policy"], r["lookahead_min"]) for r in rows} == {("rolling", 0.0), ("forecast", 10.0)}
    assert all(r["P"] == 60.0 and "n_late_over_60min" in r for r in rows)
    assert os.path.exists(os.path.join(d, "per_instance.csv"))


@needs_memory
def test_pack_and_levers_ext_smoke_cells(tmp_path):
    root = str(tmp_path)
    F.main(["--stage", "pack", "--smoke", "--out-root", root, "--threads", "1"])
    rows = C.load_jsonl(os.path.join(F.stage_dir("pack", True, root), R6.RECORDS))
    assert {r["method"] for r in rows} == {"baseline_r2", "baseline_r5_range", "baseline_r5", "best_rule"}
    assert all(r["P"] == 60.0 for r in rows)
    F.main(["--stage", "levers_ext", "--smoke", "--out-root", root, "--threads", "1"])
    rows = C.load_jsonl(os.path.join(F.stage_dir("levers_ext", True, root), R6.RECORDS))
    ilp = [r for r in rows if r["method"].startswith("ILP_tl")]
    assert len(ilp) == 1 and ilp[0]["cell"] == "eps50" and ilp[0]["obj_eq_eval"] and ilp[0]["eps_wh"] == 50.0


@needs_memory
def test_transfers_smoke_cells(tmp_path):
    root = str(tmp_path)
    F.main(["--stage", "transfers", "--smoke", "--out-root", root, "--threads", "1"])
    d = F.stage_dir("transfers", True, root)
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    ilp = [r for r in rows if r["method"] == "ilp"]
    assert {r["variant"] for r in ilp} == {"none", "free"} and all(r["P"] == 60.0 and "wall_s" in r for r in ilp)
    assert all(r.get("obj_eq_eval") for r in ilp if r.get("obj") is not None)
    assert {r["variant"] for r in rows if r["method"] == "baseline"} >= {"r2", "r5_transfer", "r5"}
    assert os.path.exists(os.path.join(d, "RESULTS.md")) and os.path.exists(os.path.join(d, "paired.csv"))


@needs_memory
def test_rl_seeds_smoke(tmp_path):
    pytest.importorskip("stable_baselines3")
    root = str(tmp_path)
    F.main(["--stage", "rl_seeds", "--smoke", "--out-root", root, "--ppo-seeds", "1"])
    d = F.stage_dir("rl_seeds", True, root)
    rows = C.load_jsonl(os.path.join(d, R6.RECORDS))
    assert all(r["ppo_seed"] == 1 for r in rows) and any(r["kind"] == "train" for r in rows)
    assert os.path.exists(os.path.join(d, "seed1", "models")) and os.path.exists(os.path.join(d, "RESULTS.md"))
