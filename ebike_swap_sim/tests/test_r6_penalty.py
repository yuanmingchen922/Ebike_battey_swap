"""Round 6 experiment script ``experiments/r6_penalty.py``: stage plans (families, seeds, prices,
time limits as specified), the repriced round-5 builders, the reuse of identical headline cells,
the exact-t intervals and the paired comparisons of the analysis.  No solve beyond one tiny cell."""
from __future__ import annotations

import argparse
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip("gurobipy")
from ebike_swap_sim import costs as cm  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r6_penalty as R6  # noqa: E402


def test_plans_match_the_specification():
    h = R6.plan_grid("headline", smoke=False)
    assert len(h) == 40 and {c.pr["label"] for c in h} == {"P60_w18_v15"}
    assert sorted({(c.case, c.mult) for c in h}) == [("nyc4h", 1.0), ("usd4h", 0.75), ("usd4h", 1.0), ("usd4h", 1.5)]
    written = [c for c in h if "written" in c.ilp_targets]
    assert len(written) == 10 and all(c.case == "usd4h" and c.mult == 1.0 for c in written)
    assert all(c.tl == 300.0 and "relaxed" in c.ilp_targets for c in h)
    p = R6.plan_grid("psweep", smoke=False)
    assert len(p) == 100 and {c.pr["P"] for c in p} == {20.0, 30.0, 40.0, 60.0, 80.0}
    assert {c.pr["v"] for c in p} == {15.0} and {c.seed for c in p} == set(range(10))
    assert {c.case for c in p} == {"usd4h", "r5_stress4h"}
    reuse = [c for c in p if c.reuse]
    assert len(reuse) == 10 and all(c.case == "usd4h" and c.pr["P"] == 60.0 for c in reuse)
    assert p[-10:] == reuse                                     # copied cells come last
    v = R6.plan_grid("vsweep", smoke=False)
    assert len(v) == 50 and {c.pr["label"] for c in v} == {"P60_w18_v8", "P60_w18_v15", "P60_w18_v25",
                                                           "P60_w18_v36", "P30_w18_v36"}
    lv = R6.plan_levers_r6(R6.BASE, smoke=False, seeds=None)
    assert len(lv) == 15 and {c.cell for c in lv} == {"reference", "P0", "lockout0.25"}
    assert all(c.ilp_tl == 600.0 for c in lv) and {c.seed for c in lv} == set(range(5))
    fl = R6.plan_fleet_r6(R6.BASE, smoke=False, seeds=None)
    assert len(fl) == 48 and {c.seed for c in fl} == {0, 1, 2}
    assert {(c.info["K"], c.info["B_per_site"]) for c in fl} == {(k, b) for k in (4, 6, 8, 10) for b in (1, 2, 3, 4)}
    assert all(c.ilp_tl == (600.0 if c.info["K"] >= 8 else 300.0) for c in fl)
    assert R6.rolling_items(False, None).count(("usd4h", 9)) == 1 and len(R6.rolling_items(False, None)) == 15
    assert R6.network_seeds(False, None) == {"usd4h_ebaas": list(range(10)), "r5_stress4h": list(range(5))}


def test_repriced_builder_keeps_the_round5_instance():
    inst, pr = R6.build_case("usd4h", 0, 1.0, smoke=True)
    rp = R6.priced(inst, R6.BASE, "test")
    assert C.demand_md5(rp) == C.demand_md5(inst)
    assert cm.uniform_order_prices(rp) == {"P": 60.0, "w": 18.0, "v": 15.0}
    assert cm.uniform_order_prices(inst) == {"P": 30.0, "w": 18.0, "v": 36.0}
    lib, _ = C.build_library(rp, pr)
    assert cm.check_lib_prices(rp, lib)["ok"]


def test_mean_ci_is_exact_t():
    m, h, n = R6.mean_ci([1.0, 2.0, 3.0, None, float("nan")])
    assert (m, n) == (2.0, 3) and h == pytest.approx(4.302652729911275 / math.sqrt(3.0))
    assert math.isnan(R6.mean_ci([5.0])[1])


def test_paired_vs_ref_pairs_by_seed():
    import pandas as pd
    per = pd.DataFrame([
        {"case": "usd4h", "mult": 1.0, "pricing": "P60_w18_v15", "seed": s, "P": 60.0, "v": 15.0, "x": float(s)}
        for s in range(3)] + [
        {"case": "usd4h", "mult": 1.0, "pricing": "P20_w18_v15", "seed": s, "P": 20.0, "v": 15.0, "x": float(s) + 1.0}
        for s in (1, 2)])
    out = R6.paired_vs_ref(per, "P60_w18_v15", ["x"])
    assert len(out) == 1 and out.iloc[0].mean_diff == pytest.approx(1.0) and out.iloc[0].n_pairs == 2


def test_grid_smoke_cell_and_reuse(tmp_path):
    """One tiny headline cell (written + relaxed ILP), then a psweep reuse of it."""
    args = argparse.Namespace(smoke=True, out_root=str(tmp_path), seeds=[0], dry_run=False, threads=3,
                              budget_min=10.0)
    cell = R6.Cell("usd4h", R6.BASE, 0, 1.0, ("written", "relaxed"), ("written", "relaxed"), 30.0)
    hd = R6.stage_dir("headline", True, str(tmp_path))
    runner = R6.GridRunner("headline", hd, 3, C.WallBudget(600.0, margin_s=0.0, min_solve_s=1.0), True, str(tmp_path))
    runner.run([cell])
    ilp = [r for r in runner.done.values() if r["method"] == "ilp"]
    assert len(ilp) == 2 and all(r["obj_eq_eval"] for r in ilp) and all(r["P"] == 60.0 for r in ilp)
    assert all(r["status"] == "OPTIMAL" for r in ilp)
    reuse = R6.Cell("usd4h", R6.BASE, 0, 1.0, ("relaxed",), ("relaxed",), 30.0, reuse=("headline",))
    ps = R6.GridRunner("psweep", R6.stage_dir("psweep", True, str(tmp_path)), 3,
                       C.WallBudget(600.0, margin_s=0.0, min_solve_s=1.0), True, str(tmp_path))
    assert ps.try_reuse(reuse) and not ps.cell_todo(reuse)
    assert {r["reused_from"] for r in ps.done.values()} == {"headline"}
    per = R6.grid_per_instance(runner.done)
    assert len(per) == 1 and per.iloc[0].gap_best_ea_pct is not None
    assert per.iloc[0].price_of_recovery == pytest.approx(per.iloc[0].ilpw_total - per.iloc[0].ilp_total)
    assert os.path.exists(R6.analyse_grid("headline", hd))


def test_budget_cut_rows_are_not_done_and_not_reused(tmp_path):
    """A TIME_LIMIT row whose limit the wall budget cut short is re-solved and never copied."""
    assert R6.budget_cut({"status": "TIME_LIMIT", "time_limit_s": 100.0, "time_limit_requested_s": 300.0})
    assert R6.budget_cut({"status": "TIME_LIMIT", "budget_shortened": True})
    assert R6.budget_cut({"status": "TIME_LIMIT", "time_limit_s": 100.0}, 300.0)
    assert not R6.budget_cut({"status": "OPTIMAL", "time_limit_s": 100.0, "time_limit_requested_s": 300.0})
    assert not R6.budget_cut({"status": "TIME_LIMIT", "time_limit_s": 300.0, "time_limit_requested_s": 300.0})
    assert not R6.budget_cut({"status": "POLICY"}, 300.0)
    assert R6.budget_cut({"status": "TIME_LIMIT", "time_limit": 50.0, "time_limit_requested": 120.0},
                         300.0, used_key="time_limit", req_key="time_limit_requested")
    lab = R6.BASE["label"]
    hd = R6.stage_dir("headline", True, str(tmp_path))
    C.ensure_dir(hd)
    base = {"family": "usd4h", "calib": lab, "seed": 0, "mult": 1.0, "targets": "relaxed"}
    rows = [{**base, "method": r, "status": "POLICY", "total": 1.0} for r in R6.RULES]
    rows.append({**base, "method": "ilp", "status": "TIME_LIMIT", "mip_gap": 0.2, "total": 1.0,
                 "time_limit_s": 40.0, "time_limit_requested_s": 300.0, "budget_shortened": True})
    for r in rows:
        C.append_jsonl(os.path.join(hd, R6.RECORDS), r)
    bud = C.WallBudget(600.0, margin_s=0.0, min_solve_s=1.0)
    h = R6.GridRunner("headline", hd, 3, bud, True, str(tmp_path))
    key = R6.grid_key("usd4h", lab, 0, 1.0, "relaxed", "ilp")
    assert not h.is_done(key)
    assert h.is_done(R6.grid_key("usd4h", lab, 0, 1.0, "relaxed", "r2"))
    cell = R6.Cell("usd4h", R6.BASE, 0, 1.0, ("relaxed",), ("relaxed",), 300.0, reuse=("headline",))
    assert h.cell_todo(cell)
    ps = R6.GridRunner("psweep", R6.stage_dir("psweep", True, str(tmp_path)), 3, bud, True, str(tmp_path))
    assert not ps.try_reuse(cell) and not ps.done


def test_grid_stops_building_cells_after_the_budget(tmp_path):
    bud = C.WallBudget(0.0, margin_s=0.0, min_solve_s=1.0)
    g = R6.GridRunner("psweep", R6.stage_dir("psweep", True, str(tmp_path)), 3, bud, True, str(tmp_path))
    g.run_cell = lambda cell: (_ for _ in ()).throw(AssertionError("cell built after the budget"))  # type: ignore
    cell = R6.Cell("r5_stress4h", R6.pricing(20.0, 15.0), 0, 1.0, ("relaxed",), ("relaxed",), 30.0)
    g.run([cell])
    rows = list(g.done.values())
    assert len(rows) == 1 and rows[0]["status"] == C.SKIPPED_BUDGET and rows[0]["method"] == "ilp"


def test_paired_vs_ref_drops_incomparable_ilp_pairs():
    import pandas as pd
    ref = R6.BASE["label"]
    per = pd.DataFrame([
        {"case": "usd4h", "mult": 1.0, "pricing": ref, "seed": 0, "P": 60.0, "v": 15.0, "ilp_total": 10.0,
         "best_total": 20.0, "ilp_status": "TIME_LIMIT", "ilp_mip_start_variant": "ilp_written"},
        {"case": "usd4h", "mult": 1.0, "pricing": ref, "seed": 1, "P": 60.0, "v": 15.0, "ilp_total": 10.0,
         "best_total": 20.0, "ilp_status": "OPTIMAL", "ilp_mip_start_variant": "ilp_written"},
        {"case": "usd4h", "mult": 1.0, "pricing": "P20_w18_v15", "seed": 0, "P": 20.0, "v": 15.0, "ilp_total": 8.0,
         "best_total": 18.0, "ilp_status": "OPTIMAL", "ilp_mip_start_variant": "r5@relaxed"},
        {"case": "usd4h", "mult": 1.0, "pricing": "P20_w18_v15", "seed": 1, "P": 20.0, "v": 15.0, "ilp_total": 7.0,
         "best_total": 18.0, "ilp_status": "OPTIMAL", "ilp_mip_start_variant": "r5@relaxed"}])
    out = R6.paired_vs_ref(per, ref, ["ilp_total", "best_total"]).set_index("metric")
    assert out.at["ilp_total", "n_pairs"] == 1 and out.at["ilp_total", "n_excluded_start"] == 1
    assert out.at["ilp_total", "mean_diff"] == pytest.approx(-3.0)
    assert out.at["best_total", "n_pairs"] == 2


def test_wide_r6_takes_best_rule_metrics_from_the_end_adjusted_argmin(tmp_path):
    d = str(tmp_path)
    C.append_jsonl(os.path.join(d, "cases.jsonl"), {"sub": "fleet", "cell": "K4_B1", "seed": 0, "target": "relaxed",
                                                    "key_md5": "k", "ilp_method": None})
    base = {"key_md5": "k", "status": "OK"}
    C.append_jsonl(os.path.join(d, R6.RECORDS), {**base, "method": "baseline_r2", "rule": "r2", "total": 10.0,
                                                 "total_end_adjusted": 15.0, "served_share": 0.5,
                                                 "n_late_over_60min": 3})
    C.append_jsonl(os.path.join(d, R6.RECORDS), {**base, "method": "baseline_r5", "rule": "r5", "total": 11.0,
                                                 "total_end_adjusted": 12.0, "served_share": 0.9,
                                                 "n_late_over_60min": 1})
    C.append_jsonl(os.path.join(d, R6.RECORDS), {**base, "method": "best_rule", "rule": "r2", "total": 10.0,
                                                 "total_end_adjusted": 15.0, "served_share": 0.5,
                                                 "n_late_over_60min": 3, "best_rule_end_adjusted_rule": "r5",
                                                 "best_rule_total_end_adjusted_min": 12.0})
    w = R6.wide_r6(d).iloc[0]
    assert w.best_rule_rule == "r5" and w.best_rule_rule_raw == "r2"
    assert w.best_rule_served_share == 0.9 and w.best_rule_n_late_over_60min == 1
    assert w.best_rule_total_end_adjusted == 12.0 == w.best_rule_total_end_adjusted_min


def test_rl_rows_carry_pricing_and_lateness_and_resume_rule():
    X7 = R6._install_rl_loader(R6.BASE)
    X7b = R6._install_rl_loader(R6.BASE)                       # idempotent
    assert X7b.schedule_row is X7.schedule_row
    assert X7.skipped_row("ilp", "f", 0, "ilp_relaxed", "ERROR")["P"] == 60.0

    class Ctx:
        a = argparse.Namespace(ilp_time_limit=300.0)
        done = {("ilp", "f", "0", "ilp_relaxed"): {"status": "TIME_LIMIT", "time_limit": 120.0,
                                                   "time_limit_requested": 120.0},
                ("ilp", "f", "1", "ilp_relaxed"): {"status": "OPTIMAL", "time_limit": 120.0,
                                                   "time_limit_requested": 120.0},
                ("ilp", "f", "2", "ilp_relaxed"): {"status": "TIME_LIMIT", "time_limit": 300.0,
                                                   "time_limit_requested": 300.0}}
    assert not X7._ilp_done(Ctx, "f", 0, "ilp_relaxed")
    assert X7._ilp_done(Ctx, "f", 1, "ilp_relaxed") and X7._ilp_done(Ctx, "f", 2, "ilp_relaxed")
    inst, pr = R6.build_case("usd4h", 0, 1.0, smoke=True)
    inst = R6.priced(inst, R6.BASE, "test")
    lib, _ = C.build_library(inst, pr)
    rec = C.run_baseline_case(inst, lib)
    row = X7.schedule_row("rule", "usd4h", 0, "rule_r2", inst, lib, rec["schedule"], 0.0, C.demand_md5(inst))
    assert {"n_late", "n_late_over_60min", "mean_lateness_min", "P", "w", "v", "pricing"} <= set(row)
    assert row["v"] == 15.0
