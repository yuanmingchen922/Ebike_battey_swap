"""R7 re-plan after batch 2 (``notes/siting_production_replan_m1.md``, core lane: changes 1, 4, 5, 6
with the critic corrections K2 / K3).  Toy tests at Threads 1:

* change 1 -- ``restore`` reads ``price_open`` records into ``priced_open`` and ``UB`` only (never
  ``priced``, cuts or the floor);
* change 4 -- all-candidates pricing warm-started from the open-sites schedules
  (``warm_tier='open_sites'``) and the ``ub_check_all_candidates`` record / check;
* change 5 -- ``certify_by_enumeration(price_pass=False)`` (``--m1-pass2 off``), the strict cell
  filter of K3.1 (``n_solves == len(cells)``) and ``ilp_params`` in the cache key;
* change 6 -- ``verify_checked_starts=False`` gives identical totals and keys.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402

CANDS4 = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))
MENU = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
PARAMS = {"Seed": 0, "MIPGap": 0.0}
UNIT = 130.0


def _toy_ev(cache_dir=None, relaxed=True):
    scen = [S.toy_base_instance(0, candidates=CANDS4), S.toy_base_instance(1, candidates=CANDS4)]
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=(None if cache_dir is None else str(cache_dir)))
    return ev.derive(relaxed_targets=True) if relaxed else ev


def _cert(ev, pool, records, budgets=(UNIT,), **kw):
    kw.setdefault("price_workers", 2)
    return BD.SitingCertifier(ev, list(budgets), MENU, S.ROLES, s_needs_charge=True, pool=pool, tol_rel=1e-9,
                              tol_abs=1e-6, lp_threads=1, master_threads=1, on_record=records.append, **kw)


def _m1_layouts(ev):
    enc = BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, S.TOY_SPEC)
    return BL.enumerate_layouts(ev.candidates, enc.options, UNIT, S.TOY_SPEC, (1,), s_needs_charge=True)


def _best_open(ev, tmp_path):
    """The m = 1 layout with the lowest open-sites value (exhaustive on the toy)."""
    ev_o = ev.derive(reposition="open_sites")
    best = None
    for l in _m1_layouts(ev):
        v = ev_o.evaluate(l, "ilp")["V"]
        if v is not None and v != BL.INF and (best is None or v < best[0]):
            best = (v, l)
    return best


# ---------------------------------------------------------------------------
# change 1: restore of price_open
# ---------------------------------------------------------------------------
def test_restore_reads_price_open_into_priced_open_and_ub_only(tmp_path):
    ev = _toy_ev(tmp_path / "cache")
    pool = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
    rec = []
    c0 = _cert(ev, pool, rec)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    c0.lp_at(lay)                                   # an LP of the layout in the pool (restorable)
    base_records = list(rec)
    r_open = c0.price(lay, tier="open_sites", tag="ub")
    assert r_open.V is not None and rec[-1]["kind"] == "price_open"
    assert "lb_open" in rec[-1] and len(rec[-1]["lb_open"]) == ev.n_scenarios
    # a worse second open record of the same layout must not override the better one
    worse = dict(rec[-1], V=r_open.V + 50.0)
    c0.close()
    n_pool = len(pool.cuts)

    def fresh(records):
        p = BD.CutPool(str(tmp_path / "cuts.jsonl"), BD.pool_signature(ev))
        c = _cert(ev, p, [])
        c.restore(records)
        return c, p

    cb, pb = fresh(base_records)
    ca, pa = fresh(rec + [worse])
    assert cb.UB[UNIT] == float("inf") and not cb.priced_open
    assert ca.UB[UNIT] == pytest.approx(r_open.V) and ca.best[UNIT].key() == lay.key()
    assert lay.key() in ca.priced_open and ca.priced_open[lay.key()].tier == "open_sites"
    assert lay.key() not in ca.priced and not ca.priced and ca.restored.get("priced_open") == 1
    assert len(pa.cuts) == len(pb.cuts) == n_pool                   # no cut from the open pricing
    assert set(ca.lp_memo) == set(cb.lp_memo) == {lay.key()}
    lays = _m1_layouts(ev)
    fa = BD.enumeration_floor(ca.master, lays, ca._known_v_lp(), ca._known_priced())
    fb = BD.enumeration_floor(cb.master, lays, cb._known_v_lp(), cb._known_priced())
    assert fa == fb                                                  # the floor ignores the open value
    r = ca.result(UNIT)
    assert r["best_tier"] == "open_sites" and r["best_lb"] is None and r["UB"] == pytest.approx(r_open.V)
    # records of the other target are ignored
    cw, _pw = fresh([dict(x, target="written") for x in rec])
    assert cw.UB[UNIT] == float("inf") and not cw.priced_open
    for c in (ca, cb, cw):
        c.close()


# ---------------------------------------------------------------------------
# change 4: warm all-candidates from open_sites, ub_check_all_candidates
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("workers", [1, 2])
def test_warm_tier_open_sites_valid_and_cuts_identical_to_cold(tmp_path, workers):
    lay = BL.Layout.from_key("T1:SC:B2:C1")
    ev_w = _toy_ev(tmp_path / f"warm{workers}")
    pool_w = BD.CutPool(None, BD.pool_signature(ev_w))
    rec_w = []
    cw = _cert(ev_w, pool_w, rec_w, price_workers=workers)
    ro = cw.price(lay, tier="open_sites", tag="ub")
    assert ro.status == "PRICED"
    rw = cw.price(lay, full=True, tag="probe", warm_tier="open_sites")
    ev_c = _toy_ev(tmp_path / f"cold{workers}")
    pool_c = BD.CutPool(None, BD.pool_signature(ev_c))
    cc = _cert(ev_c, pool_c, [], price_workers=workers)
    rc = cc.price(lay, full=True, tag="probe")
    assert rw.status == rc.status == "PRICED" and rw.V == pytest.approx(rc.V)
    assert rw.lb == pytest.approx(rc.lb) and rw.ub == pytest.approx(rc.ub)
    for s in range(ev_w.n_scenarios):                               # all-candidates <= open_sites per cell
        assert rw.ub[s] <= ro.ub[s] + 1e-6
    sig = lambda pool: sorted((c.kind, c.scenario, c.what, round(c.LBIP or 0.0, 6)) for c in pool.cuts if c.kind in ("lshaped", "lifted"))
    assert sig(pool_w) == sig(pool_c)                                # cuts identical to a cold run
    price_rec = [r for r in rec_w if r.get("kind") == "price"][-1]
    assert price_rec["warm_tier"] == "open_sites"
    for row in rw.rows:
        assert row["warm_source"] == "open_sites" and row["warm_check_ok"] is True and row["warm_materialised"] is True
        if row["mip_start_variant"] == "warm_parent":
            assert row["mip_start_obj"] == pytest.approx(row["warm_obj"])
        else:                                                        # the rule start was at least as good
            assert row["mip_start_obj"] <= row["warm_obj"] + 1e-6
    chk = [r for r in rec_w if r.get("kind") == "ub_check_all_candidates"]
    assert chk and chk[-1]["ok"] and chk[-1]["n_cells"] == ev_w.n_scenarios
    # M6: the standalone check of the open-sites schedules on the all-candidates library
    m6 = cw.ub_check_all_candidates(lay)
    assert m6["ok"] and m6["V_checked"] == pytest.approx(ro.V) and m6["V_open"] == pytest.approx(ro.V)
    assert all(c["check_ok"] and c["same_cost"] for c in m6["cells"])
    cw.close()
    cc.close()


def test_warm_parent_is_used_when_better_than_the_rule_start(tmp_path, monkeypatch):
    """The open-sites schedule is taken as the MIP start when it is cheaper than the rule start
    (forced here by a rule start of no value: ``feasible_mip_start`` returns nothing)."""
    lay = BL.Layout.from_key("T1:SC:B2:C1")
    ev = _toy_ev(tmp_path / "c")
    cert = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), [], price_workers=1)
    cert.price(lay, tier="open_sites", tag="ub")
    monkeypatch.setattr(ev._C, "feasible_mip_start", lambda inst, lib, base, *a, **k: (None, "none"))
    r = cert.price(lay, full=True, tag="probe", warm_tier="open_sites")
    assert r.status == "PRICED" and all(row["mip_start_variant"] == "warm_parent" for row in r.rows)
    cert.close()


def test_warm_tier_absent_schedule_and_default_unchanged(tmp_path):
    """Without an open-sites row the solve runs as before (rule start), the row says so; without
    ``warm_tier`` the rows carry none of the new fields (older families unchanged)."""
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    ev = _toy_ev(tmp_path / "c")
    rec = []
    cert = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec, price_workers=1)
    r = cert.price(lay, full=True, tag="probe", warm_tier="open_sites")
    assert all(row["warm_source"] == "open_sites" and row["warm_available"] is False for row in r.rows)
    assert all("warm_check_ok" not in row for row in r.rows)
    ev2 = _toy_ev(tmp_path / "d")
    rec2 = []
    c2 = _cert(ev2, BD.CutPool(None, BD.pool_signature(ev2)), rec2, price_workers=1)
    r2 = c2.price(lay, full=True, tag="probe")
    assert all(set(row) == set(BD._ROW_KEYS) for row in r2.rows)
    pr = [x for x in rec2 if x.get("kind") == "price"][-1]
    assert "warm_tier" not in pr and "strict_scenarios" not in pr
    assert not any(x.get("kind") == "ub_check_all_candidates" for x in rec2)
    cert.close()
    c2.close()


# ---------------------------------------------------------------------------
# change 5: strict cells (K3.1), ilp_params in the key, price_pass=False
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("workers", [1, 2])
def test_strict_cells_solve_only_the_filtered_cells(tmp_path, workers):
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    ev = _toy_ev(tmp_path / f"s{workers}")
    lb0 = [1.0, 2.0]
    r = BD.price_layout(ev, lay, lb0, float("inf"), 0.0, full=True, scenarios=[1], workers=workers,
                        strict_scenarios=True)
    assert r.n_solves == 1 and r.skipped == [0] and r.status == "UNRESOLVED" and r.V is None
    assert r.lb[0] == lb0[0] and r.ub[0] is None and r.ub[1] is not None
    assert [row["scenario"] for row in r.rows] == [1]
    # the old behaviour (non-strict): the uncached cell outside the filter is solved anyway
    ev2 = _toy_ev(tmp_path / f"n{workers}")
    r2 = BD.price_layout(ev2, lay, lb0, float("inf"), 0.0, full=True, scenarios=[1], workers=workers)
    assert r2.n_solves == 2 and r2.status == "PRICED" and not r2.skipped
    # a cached cell outside the filter is reused (no solve) in both modes
    r3 = BD.price_layout(ev2, lay, lb0, float("inf"), 0.0, full=True, scenarios=[1], workers=workers,
                         strict_scenarios=True)
    assert r3.n_solves == 0 and r3.status == "PRICED" and r3.V == pytest.approx(r2.V)


def test_strict_cells_through_the_certifier_keep_a_valid_floor(tmp_path):
    ev = _toy_ev(tmp_path / "c")
    rec = []
    cert = _cert(ev, BD.CutPool(None, BD.pool_signature(ev)), rec)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    exact = _toy_ev().evaluate(lay, "ilp")
    lp = cert.lp_lb(lay)
    r = cert.price(lay, full=True, scenarios=[0], strict_scenarios=True, tag="probe")
    assert r.n_solves == 1 and r.status == "UNRESOLVED" and r.lb[1] == pytest.approx(lp[1])
    assert cert.priced[lay.key()].lower <= exact["V"] + 1e-6               # a valid lower value
    pr = [x for x in rec if x.get("kind") == "price"][-1]
    assert pr["strict_scenarios"] and pr["skipped_scenarios"] == [1] and pr["scenarios"] == [0]
    cert.close()


def test_parse_cells_and_ilp_params():
    c = BD.parse_cells(["D29:5", "D29:2", "D28:0-2,D34:SC:B3:C2@1+3"])
    assert c == {"D29": {2, 5}, "D28": {0, 1, 2}, "D34:SC:B3:C2": {1, 3}}
    assert BD.cells_for_layout(c, BL.Layout.from_key("D29:SC:B3:C2")) == [2, 5]
    assert BD.cells_for_layout(c, BL.Layout.from_key("D34:SC:B3:C2")) == [1, 3]
    assert BD.cells_for_layout(c, BL.Layout.from_key("D07:SC:B3:C2")) == []
    assert BD.cells_for_layout(None, BL.Layout.from_key("D07:SC:B3:C2")) is None
    assert BD.parse_ilp_params(["Method=2", "MIPFocus=3,Heuristics=0.2", "NodeMethod=1"]) == \
        {"Method": 2, "MIPFocus": 3, "Heuristics": 0.2, "NodeMethod": 1}
    with pytest.raises(ValueError):
        BD.parse_ilp_params(["Threads=4"])
    with pytest.raises(ValueError):
        BD.parse_cells(["D29"])


def test_ilp_params_enter_the_cache_key_only_of_their_rows(tmp_path):
    ev = _toy_ev(tmp_path / "c")
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    k0 = ev.cache_key(lay, 0, "ilp")
    sib = ev.derive(params={"Method": 2})
    assert sib.params == {**ev.params, "Method": 2} and ev.params == {"Seed": 0, **PARAMS}
    assert sib.cache_key(lay, 0, "ilp") != k0 and ev.cache_key(lay, 0, "ilp") == k0
    r0 = BD.price_layout(ev, lay, [0.0, 0.0], float("inf"), 0.0, full=True)
    r1 = BD.price_layout(ev, lay, [0.0, 0.0], float("inf"), 0.0, full=True, ilp_params={"Method": 2})
    assert r0.n_solves == 2 and r1.n_solves == 2                      # new rows by design
    assert r1.V == pytest.approx(r0.V)
    keys1 = {row["key"] for row in r1.rows}
    assert keys1.isdisjoint({row["key"] for row in r0.rows})
    assert all(ev.cache[k]["params"].get("Method") == 2 for k in keys1)
    r2 = BD.price_layout(ev, lay, [0.0, 0.0], float("inf"), 0.0, full=True, ilp_params={"Method": 2})
    assert r2.n_solves == 0                                          # cached under the params key


def test_derive_does_not_inherit_tier_siblings(tmp_path):
    ev = _toy_ev(tmp_path / "c")
    sib = BD._tier_evaluator(ev, "open_sites")
    w = ev.derive(relaxed_targets=False)
    assert getattr(w, "_open_sites_sibling", None) is None
    sib_w = BD._tier_evaluator(w, "open_sites")
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    assert sib_w is not sib and sib_w.relaxed_targets is False and sib.relaxed_targets is True
    assert sib_w.cache_key(lay, 0, "ilp") != sib.cache_key(lay, 0, "ilp")


def test_m1_pass2_off_prices_nothing_and_keeps_the_floor(tmp_path):
    """M4 analogue on the toy: run 1 = enumeration without pricing under a weak UB (an
    all-candidates pricing of a poor layout, as batch 2's D30); run 2 = a new certifier restored
    from the records plus an open-sites pricing of the best layout (change 1): 0 ILP and 0 LP
    solves, the UB is the open-sites value, every layout is pruned or still listed as unpriced,
    and the floor is the floor of run 1."""
    ev = _toy_ev(tmp_path / "cache")
    cuts = str(tmp_path / "cuts.jsonl")
    lays = _m1_layouts(ev)
    rec1 = []
    c1 = _cert(ev, BD.CutPool(cuts, BD.pool_signature(ev)), rec1)
    vals = {l.key(): _toy_ev().evaluate(l, "ilp")["V"] for l in lays}
    finite = {k: v for k, v in vals.items() if v is not None and v != BL.INF}
    worst = max(finite, key=finite.get)
    c1.price(BL.Layout.from_key(worst), full=True, tag="weak_ub")
    e1 = c1.certify_by_enumeration(UNIT, force_lp_per_location=True, price_pass=False)
    assert e1["done"] and e1["n_priced"] == 0 and c1.counters["escalations"] == 0
    floor1 = c1.enum_floor(UNIT)[0]
    n_ilp1 = c1.counters["ilp_solves"]
    c1.close()
    # the open-sites UB pass (M1), written to the same records
    v_open, best = _best_open(ev, tmp_path)
    c_ub = _cert(ev, BD.CutPool(cuts, BD.pool_signature(ev)), rec1)
    c_ub.price(best, tier="open_sites", tag="ub")
    c_ub.close()
    # M4: resume, no pricing
    rec2 = []
    c2 = _cert(ev, BD.CutPool(cuts, BD.pool_signature(ev)), rec2)
    c2.restore(rec1)
    assert c2.UB[UNIT] == pytest.approx(min(v_open, finite[worst]))
    e2 = c2.certify_by_enumeration(UNIT, force_lp_per_location=True, price_pass=False)
    assert c2.counters["ilp_solves"] == 0 and c2.counters["lp_solves"] == 0 and e2["n_priced"] == 0
    assert e2["price_pass"] is False and e2["n_escalations"] == 0
    floor2 = c2.enum_floor(UNIT)[0]
    assert floor2 == pytest.approx(floor1) and floor2 <= min(finite.values()) + 1e-6
    thr = c2.UB[UNIT] - c2.tol(c2.UB[UNIT])
    unpriced = {u["layout_key"] for u in e2["unpriced"]}
    for l in lays:
        k = l.key()
        if k in c2.priced or k in c2.lp_pruned or c2.master.envelope(l) == BL.INF:
            continue
        assert k in unpriced and c2.v_lp(l) < thr                    # listed exactly when not prunable
    assert all(u["v_LP"] < thr for u in e2["unpriced"])
    res = c2.finish(final_master_s=10.0)[UNIT]
    assert res["LB"] <= min(finite.values()) + 1e-6 and res["UB"] == pytest.approx(c2.UB[UNIT])
    if unpriced:
        assert "m1-pass2 off" in res["close_reason"]
    assert n_ilp1 > 0
    c2.close()


def _run(args, timeout=900):
    return subprocess.run([sys.executable, "experiments/r7_siting.py"] + args, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout)


def test_cli_m1_pass2_off_resumes_past_stage_done(tmp_path):
    out = str(tmp_path / "o")
    r = _run(["--smoke", "--stage", "m1", "--budgets", "1", "--out-dir", out])
    assert r.returncode == 0, r.stderr[-3000:]
    r = _run(["--smoke", "--stage", "m1", "--budgets", "1", "--out-dir", out])
    assert r.returncode == 0 and "stage_skipped" in r.stdout
    r = _run(["--smoke", "--stage", "m1", "--budgets", "1", "--out-dir", out, "--m1-pass2", "off",
              "--verify-start", "unchecked"])
    assert r.returncode == 0, r.stderr[-3000:]
    recs = [json.loads(x) for x in open(os.path.join(out, "records.jsonl")) if x.strip()]
    last_done = [x for x in recs if x.get("kind") == "stage_done" and x.get("stage") == "m1"][-1]
    assert last_done.get("m1_pass2") == "off"
    assert any(x.get("kind") == "m1_warm_skipped" for x in recs)
    br = [x for x in recs if x.get("kind") == "budget_result"]
    assert br[-1]["counters"]["ilp_solves"] == 0 and br[-1]["UB"] == pytest.approx(br[0]["UB"])
    assert br[-1]["LB"] >= br[0]["LB"] - 1e-6 or br[-1]["certified"]


# ---------------------------------------------------------------------------
# change 6: verify_start off for check-clean starts
# ---------------------------------------------------------------------------
def test_verify_checked_starts_off_gives_identical_totals_and_keys(tmp_path):
    lays = [BL.Layout.from_key("T1:SC:B2:C1|T3:S:B1:C0"), BL.Layout.from_key("T2:SC:B1:C1")]
    ev_a = _toy_ev(tmp_path / "a")
    ev_b = _toy_ev(tmp_path / "b")
    ev_b.verify_checked_starts = False
    n_skipped = 0
    for lay in lays:
        for s in range(ev_a.n_scenarios):
            ra = ev_a.evaluate_scenario(lay, s, "ilp")
            rb = ev_b.evaluate_scenario(lay, s, "ilp")
            assert ra["key"] == rb["key"] and ra["status"] == rb["status"]
            assert ra["total"] == pytest.approx(rb["total"], abs=1e-9)
            assert "verify_start" not in ra
            n_skipped += int(rb.get("verify_start") is False)
    assert n_skipped > 0
    # the open-sites sibling follows its evaluator's setting (synchronised on every use)
    assert BD._tier_evaluator(ev_b, "open_sites").verify_checked_starts is False
    assert BD._tier_evaluator(ev_a, "open_sites").verify_checked_starts is True
