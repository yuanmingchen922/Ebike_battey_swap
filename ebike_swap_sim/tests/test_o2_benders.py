"""Plan item O2 (``notes/o2_siting_bound_design.md`` section 7.1): the Benders siting bound on toy
instances only (Threads 1, seconds).  ``ebike_swap_sim/benders.py``, the evaluator extensions of
``bilevel.py`` (``best_bd_stop``, ``time_limit``, callable greedy screen) and ``ilp.py``
(``keep_rows``, ``ObjBound`` without incumbent)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip("gurobipy")

from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import ilp  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from experiments import common as C  # noqa: E402

CANDS3 = (("T1", 1), ("T2", 2), ("T3", 3))
MENU = {"S": [(1, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
BUDGETS = [130.0, 260.0]
PARAMS = {"Seed": 0, "MIPGap": 0.0}


def _scenarios():
    return [S.toy_base_instance(0, candidates=CANDS3), S.toy_base_instance(1, candidates=CANDS3)]


@pytest.fixture(scope="module")
def ev():
    return BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True)


@pytest.fixture(scope="module")
def ev_rel(ev):
    return ev.derive(relaxed_targets=True)


@pytest.fixture(scope="module")
def enc(ev):
    return BD.MenuEncoding([c.id for c in ev.candidates], MENU, S.ROLES, S.TOY_SPEC)


@pytest.fixture(scope="module")
def lps(ev):
    out = [BD.ScenarioLP(ev, s, threads=1) for s in range(ev.n_scenarios)]
    yield out
    for lp in out:
        lp.dispose()


@pytest.fixture(scope="module")
def layouts(ev, enc):
    return BL.enumerate_layouts(ev.candidates, enc.options, max(BUDGETS), S.TOY_SPEC, (1, 2), s_needs_charge=True)


@pytest.fixture(scope="module")
def exhaustive(ev, ev_rel, enc):
    """Exact optimum per (target, budget) by pricing every admissible layout."""
    out = {}
    for tgt, e in (("written", ev), ("relaxed", ev_rel)):
        for b in BUDGETS:
            lays = BL.enumerate_layouts(ev.candidates, enc.options, b, S.TOY_SPEC, (1, 2), s_needs_charge=True)
            out[(tgt, b)] = min((e.value(l), l.key()) for l in lays)
    return out


# ---------------------------------------------------------------------------
# ilp.py: keep_rows and ObjBound without incumbent
# ---------------------------------------------------------------------------
def test_keep_rows_default_path_unchanged(ev):
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    inst, lib = ev.layout_pair(lay, 0)
    a = ilp.build_model(inst, lib, threads=1, time_limit=10)
    assert a.keep_rows is False and a.rows == {}
    import gurobipy as gp
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model(env=env)
    t_inst, t_lib = ev.template(0)
    fv = tuple({f.id: m.addVar(lb=-gp.GRB.INFINITY) for f in t_inst.facilities} for _ in range(3))
    sub = ilp.build_submodel(t_inst, t_lib, m, facility_vars=fv, aggregate=True, keep_rows=True)
    assert sum(len(v) for v in sub.rows.values()) == sum(sub.n_rows.values())
    assert set(sub.rows) == set(sub.n_rows)
    m.dispose()
    env.dispose()


def test_bound_kept_without_incumbent_and_best_bd_stop_row(ev):
    lay = BL.Layout.from_key("T2:SC:B2:C1")
    key = ev.cache_key(lay, 0, "ilp")
    row = ev.evaluate_scenario(lay, 0, "ilp", best_bd_stop=-1e6, force=True)
    assert row["best_bd_stop"] == -1e6
    assert row["gurobi_status"] == "USER_OBJ_LIMIT"
    assert row["bound"] is not None and row["bound"] >= -1e6
    assert row["key"] == key                                   # BestBdStop is not part of the key
    assert not ev._reusable(row, 30.0)                         # a stopped solve is never 'completed'
    full = ev.evaluate_scenario(lay, 0, "ilp", force=True)
    assert full["status"] == "OPTIMAL" and full.get("best_bd_stop") is None
    # row semantics (C3): bound and total include C_setup
    assert full["C_setup"] == pytest.approx(lay.allocated_cost(S.TOY_SPEC))
    assert full["bound"] - full["C_setup"] <= full["opex"] + 1e-6


# ---------------------------------------------------------------------------
# scenario LP: dual identities, safe cuts, cut validity
# ---------------------------------------------------------------------------
def test_dual_identities_and_safe_value(lps, enc, layouts):
    for lay in layouts[:12]:
        for lp in lps:
            r = lp.solve(enc.x_of_layout(lay), audit=True)
            assert r.status == "OPTIMAL"
            assert r.audit["max_copy_rc"] <= 1e-6
            assert r.audit["max_beta_vs_fix_pi"] <= 1e-6
            assert -1e-6 <= r.Qt - r.Qs <= 1e-6


def _random_hull_points(enc, layouts, n, rng):
    """Random points of the menu hull: convex combinations of admissible layouts."""
    W = np.array([enc.w_of(l) for l in layouts])
    pts = []
    for _ in range(n):
        lam = rng.dirichlet(np.ones(len(layouts)) * 0.3)
        pts.append(lam @ W)
    return pts


def test_cut_validity_random_first_stage_values(lps, enc, layouts):
    """Every stored LP cut, evaluated at a random first-stage value (integer or fractional), is at
    most the LP recourse at that value (no tolerance beyond 1e-6), under both targets."""
    rng = np.random.default_rng(7)
    for relaxed in (False, True):
        for lp in lps:
            lp.set_target(relaxed)
        cuts = {s: [] for s in range(len(lps))}
        gen = [enc.x_of_layout(l) for l in layouts[::3]] + [enc.x_of(w) for w in _random_hull_points(enc, layouts, 6, rng)]
        for x in gen:
            for s, lp in enumerate(lps):
                r = lp.solve(x)
                cuts[s].append((r.c0, r.beta))
        tests = [enc.x_of(w) for w in _random_hull_points(enc, layouts, 10, rng)] + \
                [enc.x_of_layout(l) for l in layouts[1::4]]
        n = 0
        for x in tests:
            for s, lp in enumerate(lps):
                r = lp.solve(x)
                assert r.status == "OPTIMAL"                       # complete recourse (C2)
                for c0, beta in cuts[s]:
                    val = c0 + sum(b * BD._x_component(x, k) for k, b in beta.items())
                    assert val <= r.Qt + 1e-6 * max(1.0, abs(r.Qt))
                    n += 1
        assert n > 100
    for lp in lps:
        lp.set_target(False)


def test_safe_cut_valid_under_perturbed_duals(lps, enc, layouts):
    """Weak duality does not need optimal duals (C1): noisy multipliers still give valid cuts."""
    rng = np.random.default_rng(3)
    lp = lps[0]
    lp.solve(enc.x_of_layout(layouts[0]))
    pi = np.asarray(lp.model.getAttr("Pi", lp.constrs), dtype=float)
    noisy = pi + rng.normal(0.0, 1e-3, size=pi.shape)
    c0, beta = lp.cut_from_pi(noisy)
    for lay in layouts[::5]:
        x = enc.x_of_layout(lay)
        r = lp.solve(x)
        assert c0 + float(beta @ lp.x_vector(x)) <= r.Qt + 1e-6 * max(1.0, abs(r.Qt))


def test_template_lp_equals_layout_lp_and_bounds_the_ilp(ev, ev_rel, lps, enc, layouts):
    """At integer layouts: template LP (no elastic activity) = LP of the layout instance (C12),
    Q_LP <= Q_IP, and relaxed <= written."""
    import gurobipy as gp
    for lay in layouts[::4]:
        x = enc.x_of_layout(lay)
        for s, lp in enumerate(lps):
            r_w = lp.solve(x)
            lp.set_target(True)
            r_r = lp.solve(x)
            lp.set_target(False)
            assert r_r.Qt <= r_w.Qt + 1e-6
            row = ev.evaluate_scenario(lay, s, "ilp")
            if row["status"] == "OPTIMAL":
                assert r_w.artificial <= 1e-9
                assert r_w.Qs <= row["opex"] + 1e-6
                inst, lib = ev.layout_pair(lay, s)
                mdl = ilp.build_model(inst, lib, threads=1, time_limit=10, aggregate=True)
                rel = mdl.model.relax()                     # y, B, C fixed by bounds: C_setup is a constant
                rel.Params.OutputFlag = 0
                rel.optimize()
                assert rel.Status == gp.GRB.OPTIMAL
                assert rel.ObjVal - _setup_const(mdl) == pytest.approx(r_w.Qt, abs=1e-6)
                rel.dispose()
            rrow = ev_rel.evaluate_scenario(lay, s, "ilp")
            if rrow["status"] == "OPTIMAL":
                assert r_r.Qs <= rrow["opex"] + 1e-6


def _setup_const(mdl):
    """C_setup of a layout model (y, B, C fixed): a constant to subtract from the relaxed objective."""
    return sum(f.F * f.y + f.bB * f.B + f.bC * f.C for f in mdl.inst.facilities)


# ---------------------------------------------------------------------------
# certifier: exactness, nested budgets, infeasibility handling
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("target", ["written", "relaxed"])
def test_benders_matches_exhaustive(ev, ev_rel, lps, exhaustive, target):
    e = ev if target == "written" else ev_rel
    recs = []
    cert = BD.SitingCertifier(e, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    res = cert.run(warm_layouts=[])
    for b in BUDGETS:
        v_opt, key = exhaustive[(target, b)]
        r = res[b]
        assert isinstance(r["LB"], float) and r["LB"] <= v_opt + 1e-6          # valid lower bound
        assert r["UB"] == pytest.approx(v_opt, abs=1e-6)                        # exact incumbent
        assert e.value(BL.Layout.from_key(r["best_layout"])) == pytest.approx(v_opt, abs=1e-6)
        assert r["certified"] and r["gap"] <= 1e-6
        assert r["coverage"]["checked"] and r["coverage"]["n_open"] == 0
    # far fewer exact pricings than layouts
    assert cert.counters["priced"] + cert.counters["pruned_by_bound"] + cert.counters["infeasible"] < 30
    # every theta cut is below the exact value at every priced layout (integer validity)
    for key, pr in cert.priced.items():
        if pr.status != "PRICED" or not cert.enc.contains(pr.layout):
            continue
        w = cert.enc.w_of(pr.layout)
        floor = cert.master.theta_floor(w)
        for s in range(cert.S):
            assert floor[s] <= pr.ub[s] + 1e-6
    cert.close()


def test_pruning_test_uses_the_budget_of_the_layout(ev, lps, exhaustive):
    """C5: an incumbent at the largest budget must not stop the pricing of a layout that is
    optimal at a smaller budget."""
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6)
    cert.UB[260.0] = 1.0           # artificial (too good) incumbent at m = 2
    cert.best[260.0] = None
    res = cert.run(warm_layouts=[], screen=False)
    v_opt, _key = exhaustive[("written", 130.0)]
    assert res[130.0]["UB"] == pytest.approx(v_opt, abs=1e-6)
    assert res[130.0]["LB"] <= v_opt + 1e-6
    cert.close()


def test_infeasible_layouts_get_combinatorial_cuts(ev, ev_rel, lps, enc, layouts):
    pool = BD.CutPool(None, BD.pool_signature(ev))
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, pool=pool, tol_rel=1e-9, tol_abs=1e-6)
    inf = []
    for lay in layouts:
        if lay.n_open != 1:
            continue
        pr = cert.price(lay, full=True)
        if pr.status == "INFEASIBLE":
            inf.append((lay, pr.infeasible))
            assert cert.master.envelope(lay) == BL.INF          # excluded from the master
    assert inf, "the toy needs at least one infeasible singleton"
    kinds = {c.kind for c in pool.cuts}
    assert "nogood" in kinds or "terminal" in kinds
    for c in pool.cuts:
        if c.kind == "nogood":
            assert c.target == "written"
            assert c.applies_to("written") and not c.applies_to("relaxed")
    cert.close()
    # one-way import (C16)
    rel = BD.Cut(kind="nogood", target="relaxed", what="T1:SC:B1:C1")
    assert rel.applies_to("written") and rel.applies_to("relaxed")
    wr = BD.Cut(kind="lp", target="written", scenario=0)
    assert not wr.applies_to("relaxed")


def test_master_respects_budget_and_access_rows(ev, enc):
    access = {"z1": ["T3"]}
    covers = BD.cover_sets(ev, enc.objects)
    m = BD.Master(enc, ev.p, [0.0] * ev.n_scenarios, s_needs_charge=True, access=access, covers=covers, threads=1)
    for b in (130.0, 200.0, 260.0):
        r = m.solve(b)
        lay = r["layout"]
        assert lay.investment(S.TOY_SPEC) <= b + 1e-6
        assert BL.layout_covers(lay, access)
        assert S.layout_admissible(lay, s_needs_charge=True)
        assert m.rows_ok(lay)
        lp = m.solve(b, relax=True)
        assert float(enc.inv @ lp["w"]) <= b + 1e-6
        assert sum(lp["w"][i] for i in enc.swap_idx if enc.loc[i] == "T3") >= 1 - 1e-6
    assert m.solve(50.0)["status"] == "INFEASIBLE"                       # below one site
    # an S-only layout violates s_needs_charge in the master
    assert not m.rows_ok(BL.Layout.from_key("T3:S:B1:C0"))
    m.dispose()


def test_cache_keys_and_pool_signature_depend_on_prices():
    scen = _scenarios()
    rep = [cm.reprice_orders(i, P=60.0, w=18.0, v=15.0, source="test") for i in scen]
    e0 = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, threads=1, aggregate=True)
    e1 = BL.LowerLevelEvaluator(rep, S.TOY_SPEC, threads=1, aggregate=True)
    lay = BL.Layout.from_key("T2:SC:B1:C1")
    assert e0.cache_key(lay, 0, "ilp") != e1.cache_key(lay, 0, "ilp")
    assert BD.pool_signature(e0) != BD.pool_signature(e1)
    assert BD.pool_signature(e0) == BD.pool_signature(BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, threads=1,
                                                                             aggregate=True))
    assert BD.pool_signature(e0, M_el=1e4) != BD.pool_signature(e0, M_el=1e5)
    # the target is in the evaluator key (the pool tags each cut instead)
    assert e0.cache_key(lay, 0, "ilp") != e0.derive(relaxed_targets=True).cache_key(lay, 0, "ilp")
    # unrepriced instances keep their earlier key component (None)
    assert cm.pricing_cache_component(scen[0]) is None and cm.pricing_cache_component(rep[0]) is not None


def test_cut_pool_signature_resume_and_dedupe(tmp_path, ev):
    path = str(tmp_path / "cuts.jsonl")
    sig = BD.pool_signature(ev)
    p1 = BD.CutPool(path, sig)
    c = BD.Cut(kind="lp", target="relaxed", scenario=0, c0=1.5, beta={"y|T1:SC": -2.0})
    assert p1.add(c) and not p1.add(BD.Cut.from_json(c.to_json()))
    p2 = BD.CutPool(path, sig)
    assert len(p2.cuts) == 1 and p2.cuts[0].beta == {"y|T1:SC": -2.0}
    p3 = BD.CutPool(path, "other")
    assert p3.cuts == [] and any(f.startswith("cuts.jsonl.stale") for f in os.listdir(tmp_path))


def test_relax_and_round_and_lp_screen(ev, lps):
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6)
    cert.lp_phase()
    for b in BUDGETS:
        assert cert.LB_LP[b] is not None and cert.x_star[b] is not None
        x = cert.enc.x_of(cert.x_star[b])
        usage = {}
        for s, r in enumerate(cert.lp_at_x(x, "test")):
            for f, u in r.usage.items():
                for k, v in u.items():
                    usage.setdefault(f, {})[k] = usage.setdefault(f, {}).get(k, 0.0) + ev.p[s] * v
        lays = BD.relax_and_round(cert.enc, cert.x_star[b], usage, b, cert.in_master)
        assert lays
        for l in lays:
            assert l.investment(S.TOY_SPEC) <= b + 1e-6 and cert.in_master(l)
    screen = BD.LPScreen(cert)
    g = BL.greedy_local_search(ev, ev.candidates, 260.0, size_menu=MENU, budget_levels=BUDGETS, screen=screen,
                               k_screen=2, s_needs_charge=True, max_passes=1)
    assert g["per_budget"][260.0]["layout"] is not None
    cert.close()


def test_smoke_cli(tmp_path):
    env = dict(os.environ, PYTHONPATH=ROOT)
    out = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r6_o2_siting.py"), "--smoke",
                          "--out-root", str(tmp_path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    assert out.returncode == 0, out.stderr[-3000:]
    recs = C.load_jsonl(str(tmp_path / "smoke" / "records.jsonl"))
    acc = [r for r in recs if r.get("kind") == "acceptance"]
    assert len(acc) == 4 and all(r["ok"] for r in acc)
    assert os.path.exists(tmp_path / "smoke" / "RESULTS.md")
    kinds = [r.get("kind") for r in recs]
    assert kinds.count("gate") == 2 and kinds.count("target_done") == 2
    assert {r["policy"] for r in recs if r.get("kind") == "cross_follower"} == {"baseline", "selfish"}
    # comparison layouts are priced before the per-budget results of their target (Table 1 is final)
    for tgt in ("relaxed", "written"):
        idx = [(i, r["kind"]) for i, r in enumerate(recs) if r.get("target") == tgt]
        assert max(i for i, k in idx if k == "baseline") < min(i for i, k in idx if k == "budget_result")
    # resume: finished targets are skipped
    again = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r6_o2_siting.py"), "--smoke",
                            "--out-root", str(tmp_path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    assert again.returncode == 0, again.stderr[-3000:]
    recs2 = C.load_jsonl(str(tmp_path / "smoke" / "records.jsonl"))
    assert [r.get("kind") for r in recs2[len(recs):]].count("target_skipped") == 2
    an = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r6_o2_siting.py"), "--smoke", "--analyse",
                         "--out-root", str(tmp_path)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert an.returncode == 0, an.stderr[-3000:]
    assert "Table 1" in open(tmp_path / "smoke" / "RESULTS.md", encoding="utf-8").read()
    json.dumps(acc)
    # every budget_result has a finite LB with a bound kind, and a final_bound record precedes it
    br = [r for r in recs if r.get("kind") == "budget_result"]
    assert len(br) == 4 and all(isinstance(r["LB"], float) and r.get("LB_kind") for r in br)
    assert kinds.count("final_bound") == 4
    # second-pass plumbing: --bound-from-cuts and --resume-open read the finished stage READ-ONLY
    src = tmp_path / "smoke"
    before = {p.name: p.stat().st_size for p in src.iterdir() if p.is_file()}
    bfc = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r6_o2_siting.py"), "--smoke", "--bound-from-cuts",
                         "--source-dir", str(src), "--out-dir", str(tmp_path / "smoke_bound")], cwd=ROOT, env=env,
                        capture_output=True, text=True, timeout=600)
    assert bfc.returncode == 0, bfc.stderr[-3000:]
    rows = C.load_jsonl(str(tmp_path / "smoke_bound" / "bound_from_cuts.jsonl"))
    assert len(rows) == 4 and os.path.exists(tmp_path / "smoke_bound" / "BOUND.md")
    stored = {(r["target"], float(r["budget"])): r for r in br}
    for r in rows:
        s_ = stored[(r["target"], float(r["budget"]))]
        assert r["LB"] == pytest.approx(s_["LB"], abs=1e-5) and r["UB"] == pytest.approx(s_["UB"], abs=1e-6)
        assert r["n_cover_rows"] >= 1 and r["master_status"] == "OPTIMAL"
    res = subprocess.run([sys.executable, os.path.join(ROOT, "experiments", "r6_o2_siting.py"), "--smoke", "--resume-open",
                          "--source-dir", str(src), "--out-dir", str(tmp_path / "smoke2")], cwd=ROOT, env=env,
                         capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, res.stderr[-3000:]
    recs3 = C.load_jsonl(str(tmp_path / "smoke2" / "records.jsonl"))
    k3 = [r.get("kind") for r in recs3[len(recs2):]]            # rows appended after the copied source records
    assert k3.count("seeded_from") == 1 and k3.count("target_skipped") == 2     # every budget certified: nothing to do
    assert len(recs3) >= len(recs2) + 3
    seeded = [r for r in recs3 if r.get("kind") == "seeded_from"][0]
    assert seeded["copied"] and seeded["cache_rows"] > 0 and seeded["cuts"] > 0
    assert os.path.exists(tmp_path / "smoke2" / "cache" / "index.jsonl")
    for row in C.load_jsonl(str(tmp_path / "smoke2" / "cache" / "index.jsonl")):
        if row.get("schedule_path"):
            assert row["schedule_path"].startswith(str(tmp_path / "smoke2")) and os.path.exists(row["schedule_path"])
    assert {p.name: p.stat().st_size for p in src.iterdir() if p.is_file()} == before      # the source was not written
    with pytest.raises(SystemExit):
        R_main = __import__("experiments.r6_o2_siting", fromlist=["main"]).main
        R_main(["--smoke", "--resume-open", "--source-dir", str(src), "--out-dir", str(src)])


def test_bound_stopped_pricing_is_a_valid_lower_bound(ev, tmp_path):
    """4.2: with an incumbent below the layout's value, BestBdStop prunes the layout; the recorded
    scenario bounds stay below the exact OPEX (C3: bound - C_setup)."""
    e = BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                               cache_dir=str(tmp_path / "cache"))
    lay = BL.Layout.from_key("T1:SC:B1:C1")
    exact = [ev.evaluate_scenario(lay, s, "ilp")["opex"] for s in range(2)]
    v = lay.allocated_cost(S.TOY_SPEC) + sum(p * o for p, o in zip(ev.p, exact))
    res = BD.price_layout(e, lay, [0.0, 0.0], ub_ref=v - 50.0, tol=1e-6)
    assert res.status == "PRUNED_BY_BOUND"
    assert res.setup + sum(p * l for p, l in zip(e.p, res.lb)) >= v - 50.0 - 1e-6
    for s in range(2):
        assert res.lb[s] <= exact[s] + 1e-6
    # a later full pricing re-solves the stopped rows and returns the exact value
    full = BD.price_layout(e, lay, [0.0, 0.0], ub_ref=BL.INF, tol=1e-6, full=True)
    assert full.status == "PRICED" and full.V == pytest.approx(v, abs=1e-6)


def test_escalation_reprices_open_gaps(ev, lps):
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6)
    lay = BL.Layout.from_key("T2:SC:B2:C1")
    cert.lp_at(lay)
    pr = cert.price(lay, full=True)
    assert pr.status == "PRICED"
    pr.lb[0] = pr.ub[0] - 5.0                     # pretend a TIME_LIMIT gap in scenario 0
    assert cert.escalate(lay)                      # re-priced (cached OPTIMAL rows close the gap)
    assert cert.priced[lay.key()].lb[0] == pytest.approx(pr.ub[0], abs=1e-6)
    assert not cert.escalate(lay)                  # nothing left to improve
    cert.close()


# ---------------------------------------------------------------------------
# review round 1 (fixer): reuse rules, escalation, exploration, coverage, shared LPs,
# R_end > 0, extensive LP (C15), per-bike LP (C12), algorithm (A), default path (7.1 i)
# ---------------------------------------------------------------------------
import dataclasses  # noqa: E402
import math  # noqa: E402

SPEC_R = dataclasses.replace(S.TOY_SPEC, R_end_S=1, R_end_SC=1)       # (17) binds under written targets
#: B at both bounds (0 and K = 2), C-only hubs with B = 2, SC with C = 0, all three roles
MENU_R = {"S": [(0, 0), (1, 0), (2, 0)], "C": [(0, 1), (2, 1)], "SC": [(0, 1), (1, 1), (2, 1), (2, 0)]}
#: box menu (every role's sizes a product of ranges): algorithm (A) with size_bounds is the extensive form (C11)
MENU_BOX = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}
BOX_BOUNDS = {"S": (1, 2, 0, 0), "C": (0, 0, 1, 1), "SC": (1, 2, 1, 1)}


def _scen_r():
    return [S.toy_base_instance(s, candidates=CANDS3, n_bikes=2, q0=3) for s in (0, 1)]


@pytest.fixture(scope="module")
def rend():
    """R_end = 1 toy: exact OPEX of every admissible layout under both targets (ground truth)."""
    ev_w = BL.LowerLevelEvaluator(_scen_r(), SPEC_R, time_limit=60.0, threads=1, params=PARAMS, aggregate=True)
    ev_r = ev_w.derive(relaxed_targets=True)
    enc = BD.MenuEncoding([c.id for c in ev_w.candidates], MENU_R, S.ROLES, SPEC_R)
    lays = BL.enumerate_layouts(ev_w.candidates, enc.options, max(BUDGETS), SPEC_R, (1, 2), s_needs_charge=True)
    exact = {}
    for tgt, e in (("written", ev_w), ("relaxed", ev_r)):
        for l in lays:
            rows = [e.evaluate_scenario(l, s, "ilp") for s in range(2)]
            assert all(r["status"] in ("OPTIMAL", BL.INFEASIBLE_ILP, BL.INFEASIBLE_TERMINAL) for r in rows)
            exact[(tgt, l.key())] = [r["opex"] if r.get("feasible") else None for r in rows]

    def V(tgt, l):
        o = exact[(tgt, l.key())]
        return math.inf if any(v is None for v in o) else l.allocated_cost(SPEC_R) + sum(p * v for p, v in zip(ev_w.p, o))

    opt = {(t, b): min((V(t, l), l.key()) for l in lays if l.investment(SPEC_R) <= b + 1e-9)
           for t in ("written", "relaxed") for b in BUDGETS}
    return {"ev": ev_w, "ev_r": ev_r, "enc": enc, "lays": lays, "exact": exact, "V": V, "opt": opt}


def test_reuse_rules_for_best_bd_stop_rows(ev):
    """A row actually stopped by BestBdStop is never a completed solve, whatever its gap; a row
    whose BestBdStop never fired follows the ordinary TIME_LIMIT rule."""
    assert not ev._reusable({"status": "USER_OBJ_LIMIT", "gap": 0.004, "best_bd_stop": 100.0, "time_limit": 30.0,
                             "total": 101.0}, 30.0)
    assert not ev._reusable({"status": BL.NO_INCUMBENT, "gurobi_status": "USER_OBJ_LIMIT", "gap": None,
                             "best_bd_stop": 100.0, "time_limit": 30.0, "total": None}, 30.0)
    assert ev._reusable({"status": "TIME_LIMIT", "gurobi_status": "TIME_LIMIT", "gap": 0.05, "best_bd_stop": 100.0,
                         "time_limit": 300.0, "total": 101.0}, 300.0)
    assert not ev._reusable({"status": "TIME_LIMIT", "gap": 0.05, "best_bd_stop": 100.0, "time_limit": 30.0,
                             "total": 101.0}, 300.0)
    assert ev._reusable({"status": "TIME_LIMIT", "gap": 0.004, "best_bd_stop": 100.0, "time_limit": 30.0,
                         "total": 101.0}, 300.0)
    # price_layout: an unfired-BestBdStop TIME_LIMIT row is reused, a fired one is re-solved
    e = BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True)
    lay = BL.Layout.from_key("T2:SC:B2:C1")
    for s in range(2):
        row = e.evaluate_scenario(lay, s, "ilp")
        assert row["status"] == "OPTIMAL"
        e.cache[row["key"]] = dict(row, status="TIME_LIMIT", gurobi_status="TIME_LIMIT", gap=0.05,
                                   bound=row["bound"] - 3.0, best_bd_stop=1e9, time_limit=30.0)
    r1 = BD.price_layout(e, lay, [0.0, 0.0], ub_ref=BL.INF, tol=1e-6, full=True)
    assert r1.n_solves == 0 and all(r["cache_hit"] for r in r1.rows) and r1.status == "PRICED"
    key0 = e.cache_key(lay, 0, "ilp")
    e.cache[key0] = dict(e.cache[key0], status="USER_OBJ_LIMIT", gurobi_status="USER_OBJ_LIMIT", gap=0.004)
    r2 = BD.price_layout(e, lay, [0.0, 0.0], ub_ref=BL.INF, tol=1e-6, full=True)
    assert r2.n_solves == 1 and r2.rows[0]["status"] == "OPTIMAL"


def test_escalation_one_scenario_and_no_wasted_level(ev, lps):
    lay = BL.Layout.from_key("T2:SC:B2:C1")
    # cap equal to the base limit: every level has the same time limit -> nothing to escalate
    c0 = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, escalate_cap_s=30.0)
    c0.lp_at(lay)
    pr = c0.price(lay, full=True)
    pr.lb[0] = pr.ub[0] - 5.0
    assert not c0.escalate(lay) and c0.counters["escalations"] == 0
    c0.close()
    recs = []
    c1 = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    c1.lp_at(lay)
    pr = c1.price(lay, full=True)
    pr.lb[1] = pr.ub[1] - 5.0                    # scenario 1 is the open one
    assert c1.escalate(lay)
    esc = [r for r in recs if r["kind"] == "escalate"]
    assert len(esc) == 1 and esc[0]["scenario"] == 1 and esc[0]["time_limit"] == pytest.approx(90.0)
    last = [r for r in recs if r["kind"] == "price"][-1]
    assert last["rows"][0]["cache_hit"]          # the other scenario is not re-solved
    assert c1.escalation_time_limit(lay, 2) == pytest.approx(270.0)
    c1.close()


def test_coverage_counts_open_priced_layouts_and_ignores_empty_access_zones(ev, lps):
    access = {"z_empty": [], "z1": ["T3"]}
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, access=access)
    assert cert.master.access_empty == ["z_empty"]
    n_ref = len(BL.enumerate_layouts(ev.candidates, cert.enc.options, 130.0, S.TOY_SPEC, (1,), s_needs_charge=True,
                                     access={"z1": ["T3"]}))
    assert n_ref > 0 and len(cert.menu_layouts(130.0)) == n_ref
    lay = BL.Layout.from_key("T3:SC:B1:C1")
    cert.UB[130.0] = 1e4
    cert.priced[lay.key()] = BD.PriceResult(layout=lay, status="PRICED", setup=lay.allocated_cost(S.TOY_SPEC),
                                            lb=[0.0, 0.0], ub=[1e4, 1e4], V=1e4, lb_p=[0.0, 0.0])
    cov = cert.coverage(130.0)
    assert cov["checked"] and cov["n_layouts"] == n_ref
    assert cov["n_open_priced"] == 1 and lay.key() in cov["open"]
    assert cov["n_open"] == cov["n_open_priced"] + cov["n_open_unpriced"]
    cert.close()


def test_shared_lps_follow_the_certifier_target(rend):
    """CLI order (relaxed, then written on the same LPs and pool) with R_end = 1; afterwards the
    relaxed certifier is used again: its LPs are switched back and its cuts stay valid for the
    relaxed problem.  Every theta cut is checked at EVERY feasible layout against the exact OPEX."""
    ev_w, ev_r, enc, lays, exact, opt = (rend[k] for k in ("ev", "ev_r", "enc", "lays", "exact", "opt"))
    lps_ = [BD.ScenarioLP(ev_w, s, threads=1) for s in range(2)]
    pool = BD.CutPool(None, BD.pool_signature(ev_w))
    L = ev_w.superset_bound(method="lp")
    certs = {}
    for tgt, e in (("relaxed", ev_r), ("written", ev_w)):
        cert = BD.SitingCertifier(e, BUDGETS, MENU_R, S.ROLES, lps=lps_, pool=pool, L=L, tol_rel=1e-9, tol_abs=1e-6)
        res = cert.run(warm_layouts=[])
        for b in BUDGETS:
            v_opt = opt[(tgt, b)][0]
            assert isinstance(res[b]["LB"], float) and res[b]["LB"] <= v_opt + 1e-6
            assert res[b]["UB"] == pytest.approx(v_opt, abs=1e-6) and res[b]["certified"]
            assert res[b]["coverage"]["checked"] and res[b]["coverage"]["n_open"] == 0
        certs[tgt] = cert
    n_before = len(pool.cuts)
    crel = certs["relaxed"]
    for l in lays[::23]:
        crel.lp_memo.pop(l.key(), None)
        crel.lp_at(l)
    new = pool.cuts[n_before:]
    assert new and all(c.target == "relaxed" for c in new if c.kind == "lp")
    assert all(lp.relaxed for lp in lps_)
    for tgt, cert in certs.items():
        for l in lays:
            o = exact[(tgt, l.key())]
            if any(v is None for v in o):
                continue
            w = enc.w_of(l)
            assert cert.master.rows_ok(l, w), l.key()            # no feasible layout is excluded
            fl = cert.master.theta_floor(w)
            for s in range(2):
                assert fl[s] <= o[s] + 1e-6 * max(1.0, abs(o[s])), (tgt, l.key(), s)
    for c in certs.values():
        c.close()
    for lp in lps_:
        lp.dispose()


def test_search_covers_the_menu_when_pricing_gaps_stay_open(rend):
    """Node-limited pricing (every ILP row keeps an open gap, escalation cannot close it): the
    exploration master keeps pricing new layouts instead of stalling on one; LB stays valid."""
    params = {"Seed": 0, "MIPGap": 0.0, "NodeLimit": 0, "Heuristics": 0, "Cuts": 0, "Presolve": 0}
    ev = BL.LowerLevelEvaluator(_scen_r(), SPEC_R, time_limit=60.0, threads=1, params=params,
                                aggregate=True).derive(relaxed_targets=True)
    recs = []
    cert = BD.SitingCertifier(ev, [130.0], MENU_R, S.ROLES, tol_rel=1e-9, tol_abs=1e-6, max_escalations=1,
                              on_record=recs.append)
    res = cert.run(warm_layouts=[])[130.0]
    v_opt = rend["opt"][("relaxed", 130.0)][0]
    assert isinstance(res["LB"], float) and res["LB"] <= v_opt + 1e-6
    assert res["UB"] is not None and res["UB"] >= v_opt - 1e-6
    cov = res["coverage"]
    assert cov["checked"] and cov["n_open_unpriced"] == 0           # every layout priced, pruned or excluded
    assert cert.counters["explore_proposals"] > 0
    assert res["close_reason"] == "gap" or res["close_reason"].startswith("open pricing gaps only")
    for l in cert.menu_layouts(130.0):
        k = l.key()
        assert k in cert.priced or k in cert.lp_pruned or cert.master.envelope(l) >= res["UB"] - 1e-6
    cert.close()


def test_enumeration_certifies_a_budget(ev, lps, exhaustive):
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6)
    rec = cert.certify_by_enumeration(130.0)
    v_opt = exhaustive[("written", 130.0)][0]
    assert rec["done"] and rec["LB_enum"] <= v_opt + 1e-6
    assert cert.UB[130.0] == pytest.approx(v_opt, abs=1e-6)
    assert cert.closed[130.0] == "gap" and cert.LB[130.0] <= v_opt + 1e-6
    res = cert.finish()
    assert res[130.0]["certified"] and res[130.0]["coverage"]["n_open"] == 0
    cert.close()


def _extensive_lp(lps_, enc, master, p, budget):
    """LP relaxation of the extensive form: the structural rows of a master WITHOUT cuts over w in [0, 1] and one
    copy of every scenario LP (same artificial and slack columns), copies linked to x(w)."""
    import gurobipy as gp
    import scipy.sparse as sp
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model(env=env)
    m.Params.Threads = 1
    w = m.addMVar(enc.n, lb=0.0, ub=1.0)
    mm = master.model
    mm.update()
    Am = mm.getA().tocsr()[:, :enc.n]
    rhs = np.array(mm.getAttr("RHS", mm.getConstrs()), dtype=float)
    rhs[master.budget_row.index] = budget
    m.addMConstr(Am, w, np.array(mm.getAttr("Sense", mm.getConstrs())), rhs)
    obj = enc.setup @ w
    for s, lp in enumerate(lps_):
        A = lp._matrix()
        keep = np.setdiff1d(np.arange(A.shape[0]), lp.fix_rows)
        lb = np.where(np.isfinite(lp.lb), lp.lb, -gp.GRB.INFINITY)
        ub = np.where(np.isfinite(lp.ub), lp.ub, gp.GRB.INFINITY)
        x = m.addMVar(A.shape[1], lb=lb, ub=ub)
        sense = np.where(lp.le, "<", np.where(lp.ge, ">", "="))
        m.addMConstr(sp.csr_matrix(A[keep]), x, sense[keep], lp.b[keep])
        for k, col in zip(lp.copy_keys, lp.copy_idx):
            m.addConstr(x[int(col)] - enc.lp_coeffs({k: 1.0}) @ w == 0.0)
        obj = obj + p[s] * (lp.q @ x)
    m.setObjective(obj, gp.GRB.MINIMIZE)
    m.optimize()
    assert m.Status == gp.GRB.OPTIMAL
    val = float(m.ObjVal)
    m.dispose()
    env.dispose()
    return val


@pytest.mark.parametrize("target", ["written", "relaxed"])
def test_lp_phase_equals_extensive_lp(ev, ev_rel, lps, target):
    """7.1 (f), C15: without the superset rows (L = 0) the converged LP-phase bound equals the LP
    relaxation of the extensive form with the same elastic columns."""
    e = ev if target == "written" else ev_rel
    cert = BD.SitingCertifier(e, BUDGETS, MENU, S.ROLES, lps=lps, L=[0.0, 0.0], tol_rel=1e-9, tol_abs=1e-6,
                              lp_phase_iters=2000, lp_stall_iters=10_000)
    cert.lp_phase()
    fresh = BD.Master(cert.enc, ev.p, [0.0, 0.0], s_needs_charge=True, covers=cert.covers, threads=1)   # no cut rows
    for b in BUDGETS:
        ext = _extensive_lp(lps, cert.enc, fresh, ev.p, b)
        assert cert.LB_LP[b] <= ext + 1e-6 * max(1.0, abs(ext))
        assert cert.LB_LP[b] == pytest.approx(ext, abs=1e-5 * max(1.0, abs(ext)))
    fresh.dispose()
    cert.close()
    for lp in lps:
        lp.set_target(False)


def test_template_lp_equals_per_bike_layout_lp(rend):
    """7.1 (c), C12 for per-bike pricing (Midtown): at integer layouts the aggregated template LP
    equals the LP relaxation of the PER-BIKE layout model, under both targets, and is below the
    per-bike ILP OPEX."""
    import gurobipy as gp
    ev_pb = BL.LowerLevelEvaluator(_scen_r(), SPEC_R, time_limit=60.0, threads=1, params=PARAMS, aggregate=False)
    lps_ = [BD.ScenarioLP(ev_pb, s, threads=1) for s in range(2)]
    enc = rend["enc"]
    n = 0
    for relaxed in (False, True):
        e = ev_pb.derive(relaxed_targets=True) if relaxed else ev_pb
        for lp in lps_:
            lp.set_target(relaxed)
        for lay in rend["lays"][::11]:
            for s, lp in enumerate(lps_):
                r = lp.solve(enc.x_of_layout(lay))
                row = e.evaluate_scenario(lay, s, "ilp")
                if row["status"] != "OPTIMAL":
                    continue
                assert r.artificial <= 1e-9 and r.slack <= 1e-9
                assert r.Qs <= row["opex"] + 1e-6
                inst, lib = e.layout_pair(lay, s)
                mdl = ilp.build_model(inst, lib, threads=1, time_limit=10)          # per-bike (default path)
                rel = mdl.model.relax()
                rel.Params.OutputFlag = 0
                rel.optimize()
                assert rel.Status == gp.GRB.OPTIMAL
                assert rel.ObjVal - _setup_const(mdl) == pytest.approx(r.Qt, abs=1e-6)
                rel.dispose()
                n += 1
    assert n >= 10
    for lp in lps_:
        lp.dispose()


def test_benders_matches_integrated_stochastic_ilp_on_a_box_menu(ev):
    """7.1 (e): on a box menu algorithm (A) is the extensive form (C11); both optima agree."""
    cert = BD.SitingCertifier(ev, BUDGETS, MENU_BOX, S.ROLES, tol_rel=1e-9, tol_abs=1e-6)
    res = cert.run(warm_layouts=[])
    for b in BUDGETS:
        ig = BL.integrated_stochastic_ilp(ev, ev.candidates, b, time_limit=120.0, threads=1, size_bounds=BOX_BOUNDS,
                                          s_needs_charge=True, params={"MIPGap": 0.0})
        assert ig["status"] == "OPTIMAL"
        assert res[b]["UB"] == pytest.approx(ig["obj"], abs=1e-6)
        assert res[b]["LB"] <= ig["obj"] + 1e-6 and res[b]["certified"]
    cert.close()


def test_default_per_bike_path_toy_optima():
    """7.1 (i): the default (per-bike, keep_rows=False) model still gives 12.5 / 11.2 / 106."""
    from ebike_swap_sim import build_arcs, toy_instance
    inst = toy_instance()
    lib = build_arcs(inst)
    _s, st = ilp.solve(inst, lib, threads=1, time_limit=60.0)
    assert st["status"] == "OPTIMAL" and st["obj"] == pytest.approx(12.5)
    inst0 = toy_instance()
    inst0.rho = 0.0
    _s0, st0 = ilp.solve(inst0, build_arcs(inst0), threads=1, time_limit=60.0)
    assert st0["obj"] == pytest.approx(11.2)
    _sn, st_n = ilp.solve(inst, lib, threads=1, time_limit=60.0, no_transfers=True)
    assert st_n["obj"] == pytest.approx(106.0)


def test_gate_acts_after_warm_start_and_thread_guard(ev, lps, exhaustive):
    """Design section 8 step 3: a median LP gap > 2 % triggers the enumeration of the smallest
    budget (auto) or stops the run (abort); the CLI rejects more than 12 threads in total."""
    import argparse
    from experiments import r6_o2_siting as R

    class _Run:
        def __init__(self):
            self.recs = []

        def emit(self, rec, echo=False):
            self.recs.append(rec)

    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6)
    cert.lp_gap_cells = lambda: [0.05, 0.06, 0.07]
    run = _Run()
    g = R.gate_after_warm(run, cert, argparse.Namespace(gate="auto"), BUDGETS, 130.0)
    assert g["action"].startswith("certify")
    en = [r for r in run.recs if r["kind"] == "gate_enumeration"]
    assert en and en[0]["done"] and en[0]["LB_enum"] <= exhaustive[("written", 130.0)][0] + 1e-6
    assert cert.closed[130.0] == "gap"
    with pytest.raises(SystemExit):
        R.gate_after_warm(_Run(), cert, argparse.Namespace(gate="abort"), BUDGETS, 130.0)
    cert.close()
    with pytest.raises(SystemExit):
        R.main(["--manhattan", "--dry-run", "--lp-workers", "4", "--lp-threads", "3", "--master-threads", "2"])


# ---------------------------------------------------------------------------
# second pass (notes/o2_manhattan_first_pass.md): LP methods, envelope pruning, guaranteed bound,
# bound from the stored pool, resume, one-way cut import
# ---------------------------------------------------------------------------
import math  # noqa: E402

_T2 = "T2:SC:B1:C1"
_T2B = "T2:SC:B2:C1"


def test_lp_methods_agree_and_records_carry_method_runtime(ev, enc, lps, layouts):
    """The cold barrier (default), the warm dual simplex and the concurrent re-solve give the same
    safe value Qs within 1e-6 (the cut is valid for any optimal duals); every LPResult and
    lp_layout record carries the method, runtime and iteration count."""
    for lp in lps:
        lp.set_target(False)
    dual = BD.ScenarioLP(ev, 0, threads=1, method="dual")
    conc = BD.ScenarioLP(ev, 0, threads=1, method="concurrent")
    try:
        for i, lay in enumerate(layouts[:6]):
            x = enc.x_of_layout(lay)
            a, b = lps[0].solve(x), dual.solve(x)
            assert a.status == b.status == "OPTIMAL"
            assert abs(a.Qs - b.Qs) <= 1e-6 * max(1.0, abs(a.Qs))
            assert a.method.startswith("barrier-cold")
            assert b.method == ("method2-cold" if i == 0 else "dual-warm")
            assert a.runtime_s >= 0.0 and a.iterations >= 0.0 and b.iterations >= 0.0
            if i < 2:
                c = conc.solve(x)
                assert c.status == "OPTIMAL" and abs(a.Qs - c.Qs) <= 1e-6 * max(1.0, abs(a.Qs))
                assert c.method.startswith("concurrent")
        assert dual.n_solves == 6
    finally:
        dual.dispose()
        conc.dispose()
    with pytest.raises(ValueError):
        BD.ScenarioLP(ev, 0, threads=1, method="simplexx")
    recs = []
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    cert.lp_at(BL.Layout.from_key(_T2))
    r = [x for x in recs if x["kind"] == "lp_layout"][0]
    assert len(r["runtime_s"]) == 2 and len(r["iterations"]) == 2 and all(m.startswith("barrier") for m in r["method"])
    cert.close()


@pytest.mark.parametrize("phase", ["enumeration", "lp_phase", "integer_phase"])
def test_lb_is_never_none_when_the_wall_hits(ev, lps, exhaustive, phase):
    """Whatever phase the wall stops, finish() ends with a bound-only master solve over the full
    pool and every budget_result has a finite, valid LB (at least the superset trivial bound)."""
    recs = []
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    cert.warm_start([BL.Layout.from_key(_T2)])
    calls = {"n": 0}

    def wall_out():
        calls["n"] += 1
        return calls["n"] > 2 if phase == "enumeration" else True

    cert.wall_out = wall_out
    if phase == "enumeration":
        e = cert.certify_by_enumeration(130.0)
        assert not e["done"] and e["reason"] == "wall" and math.isfinite(e["LB_floor"])
        assert cert.LB[130.0] >= e["LB_floor"] - 1e-9
    elif phase == "lp_phase":
        cert.lp_phase()
        assert cert.counters["master_solves"] == 0
    else:
        cert.integer_phase()
        assert all(v == "wall" for v in cert.closed.values())
    res = cert.finish()
    sup = BD.superset_trivial_bound(cert.enc, cert.p, cert.L)
    for b in BUDGETS:
        lb = res[b]["LB"]
        assert isinstance(lb, float) and math.isfinite(lb)
        assert sup - 1e-9 <= lb <= exhaustive[("written", b)][0] + 1e-6
        kind = res[b]["LB_kind"]
        assert kind is not None and (kind in ("master", "superset", "enumeration", "lp_phase") or kind.startswith("nested:"))
        assert res[b]["close_reason"] in ("wall", "gap", "not searched")
        assert res[b]["LB_parts"]["master_status"] in ("OPTIMAL", "TIME_LIMIT", "INFEASIBLE")
    fb = [r for r in recs if r["kind"] == "final_bound"]
    assert len(fb) == len(BUDGETS)
    assert cert.counters["master_solves"] >= len(BUDGETS)
    cert.close()


def test_envelope_pruning_is_safe_and_location_major(ev, lps, layouts):
    """The LP-free envelope prune never removes a layout whose exact V is below UB - tol
    (envelope <= v_LP <= V); the enumeration order keeps every site set contiguous."""
    recs = []
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    cert.warm_start([BL.Layout.from_key(_T2B), BL.Layout.from_key("T1:SC:B1:C1|T2:S:B1:C0")])
    e1 = cert.certify_by_enumeration(130.0)
    e2 = cert.certify_by_enumeration(260.0)
    assert e1["done"] and e2["done"] and e1["prune"]
    env_pruned = [r for r in recs if r["kind"] == "lp_pruned" and r.get("by") == "envelope"]
    assert env_pruned, "the toy enumeration prunes some layouts without an LP"
    assert cert.counters["envelope_pruned"] == len(env_pruned)
    assert e1["n_envelope_pruned"] + e2["n_envelope_pruned"] == len(env_pruned)
    for r in env_pruned:
        lay = BL.Layout.from_key(r["layout_key"])
        v = ev.value(lay)
        ubr = max(cert.UB[b] for b in cert.fits(lay))
        assert v >= ubr - cert.tol(ubr) - 1e-6
        assert r["envelope"] <= v + 1e-6
    rng = np.random.default_rng(3)
    for i in rng.choice(len(layouts), size=min(15, len(layouts)), replace=False):
        assert cert.master.envelope(layouts[i]) <= ev.value(layouts[i]) + 1e-6
    order = cert._enum_order(cert.menu_layouts(260.0))
    groups = []
    for l, _env in order:
        g = tuple(l.locations())
        if not groups or groups[-1] != g:
            groups.append(g)
    assert len(groups) == len(set(groups))
    for b in BUDGETS:
        assert cert.closed[b] == "gap"
    cert.close()


def test_bound_from_cuts_equals_the_certifier_lb(ev, lps, tmp_path, exhaustive):
    """After a full toy run (file pool, records) the CLI's bound from the stored pool equals the
    certifier's LB per budget (same masters, cover rows, superset bound, enumeration floor and
    nested propagation); without the cover rows it is at most that and at least the trivial
    bound."""
    from experiments import r6_o2_siting as R
    pool_path = str(tmp_path / "cuts.jsonl")
    pool = BD.CutPool(pool_path, BD.pool_signature(ev))
    recs = []
    cert = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, pool=pool, tol_rel=1e-9, tol_abs=1e-6,
                              on_record=recs.append)
    cert.warm_start([BL.Layout.from_key(_T2)])
    cert.certify_by_enumeration(130.0)
    res = cert.run(warm_layouts=[])
    cfg = {"menu": MENU, "roles": S.ROLES, "budgets": BUDGETS}
    rows = R.bound_from_pool(ev, cfg, pool_path, recs, ["written"], cert.L, with_cover=True, top=3, threads=1)
    by_b = {r["budget"]: r for r in rows}
    for b in BUDGETS:
        assert by_b[b]["LB"] == pytest.approx(res[b]["LB"], abs=1e-5)
        assert by_b[b]["UB"] == pytest.approx(res[b]["UB"], abs=1e-6)
        assert by_b[b]["LB"] <= exhaustive[("written", b)][0] + 1e-6
        assert by_b[b]["ranked"] and by_b[b]["n_cover_rows"] >= 1
    assert by_b[130.0]["enumeration"] is not None and by_b[260.0]["enumeration"] is None
    sup = BD.superset_trivial_bound(cert.enc, cert.p, cert.L)
    rows2 = R.bound_from_pool(ev, cfg, pool_path, recs, ["written"], cert.L, with_cover=False, top=None, threads=1)
    for r in rows2:
        assert sup - 1e-9 <= r["LB"] <= res[r["budget"]]["LB"] + 1e-5
    cert.close()


def test_resume_open_continues_a_wall_stopped_run(ev, lps, tmp_path, exhaustive):
    """A run stopped by the wall is resumed from the pool and the records: every LP solve,
    pricing and LP prune of the first run is restored (none solved again) and the resumed run
    certifies both budgets."""
    cache = str(tmp_path / "cache")
    pool_path = str(tmp_path / "cuts.jsonl")
    e1 = BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=cache)
    recs = []
    c1 = BD.SitingCertifier(e1, BUDGETS, MENU, S.ROLES, lps=lps, pool=BD.CutPool(pool_path, BD.pool_signature(e1)),
                            tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    c1.warm_start([BL.Layout.from_key(_T2), BL.Layout.from_key(_T2B)])
    calls = {"n": 0}

    def wall_out():
        calls["n"] += 1
        return calls["n"] > 3

    c1.wall_out = wall_out
    c1.integer_phase()
    r1 = c1.finish()
    assert all(isinstance(r1[b]["LB"], float) for b in BUDGETS)
    priced1, lp1, pruned1 = set(c1.priced), set(c1.lp_memo), set(c1.lp_pruned)
    assert priced1 and lp1
    c1.close()
    e2 = BL.LowerLevelEvaluator(_scenarios(), S.TOY_SPEC, time_limit=30.0, threads=1, params=PARAMS, aggregate=True,
                                cache_dir=cache)
    recs2 = []
    c2 = BD.SitingCertifier(e2, BUDGETS, MENU, S.ROLES, lps=lps, pool=BD.CutPool(pool_path, BD.pool_signature(e2)),
                            tol_rel=1e-9, tol_abs=1e-6, on_record=recs2.append)
    st = c2.restore(recs)
    assert st["priced"] == len(priced1) and st["lp_layouts"] == len(lp1) and st["lp_pruned"] == len(pruned1 - priced1)
    assert set(c2.priced) == priced1 and set(c2.lp_memo) == lp1
    for key in lp1:
        for s in range(c1.S):
            assert c2.lp_memo[key][s].Qs == pytest.approx(c1.lp_memo[key][s].Qs, abs=1e-9)
    for b in BUDGETS:
        assert c2.UB[b] == pytest.approx(c1.UB[b], abs=1e-9)
    res = c2.run(warm_layouts=[BL.Layout.from_key(_T2), BL.Layout.from_key(_T2B)])
    for b in BUDGETS:
        assert res[b]["certified"] and res[b]["UB"] == pytest.approx(exhaustive[("written", b)][0], abs=1e-6)
        assert res[b]["restored"] == st
    assert not ({r["layout_key"] for r in recs2 if r["kind"] == "lp_layout"} & lp1)
    assert all(r["n_solves"] == 0 for r in recs2 if r["kind"] == "price" and r["layout_key"] in priced1)
    c2.close()


def test_written_cuts_never_enter_a_relaxed_master(ev, ev_rel, lps, tmp_path):
    """One-way import (C16) in every master built from a stored pool: the relaxed master holds
    relaxed / both cuts only, the written master both targets."""
    from experiments import r6_o2_siting as R
    pool_path = str(tmp_path / "cuts.jsonl")
    pool = BD.CutPool(pool_path, BD.pool_signature(ev))
    cw = BD.SitingCertifier(ev, BUDGETS, MENU, S.ROLES, lps=lps, pool=pool, tol_rel=1e-9, tol_abs=1e-6)
    cw.warm_start([BL.Layout.from_key(_T2)])
    cw.close()
    assert pool.cuts and all(c.target in ("written", "both") for c in pool.cuts)
    n_rel_before = len(pool.for_target("relaxed"))
    cr = BD.SitingCertifier(ev_rel, BUDGETS, MENU, S.ROLES, lps=lps, pool=pool, tol_rel=1e-9, tol_abs=1e-6)
    assert cr.n_pool_loaded == n_rel_before == cr.master.n_cuts < len(pool.cuts)   # no written cut loaded
    cr.warm_start([BL.Layout.from_key(_T2B)])
    assert all(c.target != "written" for c in pool.for_target("relaxed"))
    assert {c.target for c in pool.cuts} >= {"written", "relaxed"}
    cfg = {"menu": MENU, "roles": S.ROLES, "budgets": BUDGETS}
    rows = R.bound_from_pool(ev_rel, cfg, pool_path, [], ["relaxed", "written"], cr.L, with_cover=False, top=None, threads=1)
    for r in rows:
        kinds = r["n_cuts_by_kind"]
        if r["target"] == "relaxed":
            assert kinds and not any(k.endswith(":written") for k in kinds)
        else:
            assert any(k.endswith(":relaxed") for k in kinds) and any(k.endswith(":written") for k in kinds)
        assert r["UB"] is None and math.isfinite(r["LB"])
    with pytest.raises(ValueError):
        BD.CutPool(pool_path, "other-signature", read_only=True)
    cr.close()
    for lp in lps:
        lp.set_target(False)


# ---------------------------------------------------------------------------
# review round 3 (fixer): escalation on the enumeration path, resume-open configuration check,
# master-infeasible budgets
# ---------------------------------------------------------------------------
def test_enumeration_escalates_open_pricing_gaps(tmp_path):
    """Pricings stopped at a tiny TIME_LIMIT leave open gaps.  The enumeration path escalates
    them itself (pass 3) instead of closing the budget as 'enumerated (open pricing gaps)' --
    which the integer phase would then skip -- and certifies once a level solves the rows
    exactly.  LB stays a valid lower bound throughout."""
    scen = [S.toy_base_instance(s, candidates=CANDS3, n_orders=8, n_bikes=3) for s in (0, 1)]
    params = {"Seed": 0, "MIPGap": 0.0, "Heuristics": 0.0}
    exact = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=60.0, threads=1, params=PARAMS, aggregate=True)
    enc = BD.MenuEncoding([c.id for c in exact.candidates], MENU, S.ROLES, S.TOY_SPEC)
    lays = BL.enumerate_layouts(exact.candidates, enc.options, 130.0, S.TOY_SPEC, (1,), s_needs_charge=True)
    v_opt = min(exact.value(l) for l in lays)
    found = False
    for i, tl in enumerate((0.004, 0.006, 0.008)):
        ev_ = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=tl, threads=1, params=params, aggregate=True,
                                     cache_dir=str(tmp_path / f"cache_{i}"))
        lps_ = [BD.ScenarioLP(ev_, s, threads=1) for s in range(2)]
        recs = []
        cert = BD.SitingCertifier(ev_, [130.0], MENU, S.ROLES, lps=lps_, on_record=recs.append, max_escalations=2,
                                  escalate_factor=100.0, escalate_cap_s=30.0, tol_rel=1e-9, tol_abs=1e-6)
        cert.warm_start([BL.Layout.from_key(_T2), BL.Layout.from_key(_T2B)])
        e = cert.certify_by_enumeration(130.0)
        res = cert.finish()[130.0]
        cert.close()
        for lp in lps_:
            lp.dispose()
        assert e["done"] and isinstance(res["LB"], float) and res["LB"] <= v_opt + 1e-6
        assert res["UB"] is not None and res["UB"] >= v_opt - 1e-6
        if e["n_open_before_escalation"] == 0:
            continue                            # every row solved exactly within tl: nothing to escalate
        found = True
        assert e["n_escalations"] > 0 and cert.counters["escalations"] == e["n_escalations"]
        esc = [r for r in recs if r["kind"] == "escalate"]
        assert len(esc) == e["n_escalations"] and all(r["layout_key"] in cert.priced for r in esc)
        # the 30 s level solves the toy rows exactly: the budget is certified by the enumeration itself
        assert e["close_reason"] == "gap" and e["n_open_priced"] == 0 and res["certified"]
        assert res["UB"] == pytest.approx(v_opt, abs=1e-6) and res["LB"] >= v_opt - 1e-6
        break
    assert found, "no time limit left an open pricing gap on this machine"


def test_resume_open_skips_only_certified_rows_of_the_same_core_configuration(tmp_path):
    """``--resume-open``: a ``target_done`` row is skipped only when every requested budget is
    certified AND the budget-free configuration hash matches; a certified row of another
    configuration is run again and a ``target_not_skipped`` record says so."""
    import argparse

    from experiments import r6_o2_siting as R
    run = R.Run("smoke", argparse.Namespace(out_root=str(tmp_path), out_dir=None, source_dir=None))
    ok = {"130.0": {"certified": True}, "260.0": {"certified": True}}
    run.emit({"kind": "target_done", "target": "relaxed", "config_md5": "x1", "config_md5_core": "coreA", "results": ok})
    run.emit({"kind": "target_done", "target": "written", "config_md5": "x2", "config_md5_core": "coreB", "results": ok})
    done = R.finished_targets(run, "x1", resume_open=True, budgets=[130.0, 260.0], md5_core="coreA")
    assert set(done) == {"relaxed"}
    ns = [r for r in C.load_jsonl(run.records) if r.get("kind") == "target_not_skipped"]
    assert len(ns) == 1 and ns[0]["target"] == "written" and ns[0]["stored_config_md5_core"] == "coreB"
    assert R.finished_targets(run, "x1", resume_open=True, budgets=[130.0, 390.0], md5_core="coreA") == {}
    assert set(R.finished_targets(run, "x1", resume_open=True, budgets=[130.0], md5_core="coreB")) == {"written"}
    assert set(R.finished_targets(run, "x2")) == {"written"}           # without --resume-open: the full hash
    # a row without the core hash (first pass) is never skipped under --resume-open
    run.emit({"kind": "target_done", "target": "relaxed", "config_md5": "x1", "results": ok})
    assert R.finished_targets(run, "x1", resume_open=True, budgets=[130.0], md5_core="coreA") == {}


def test_master_infeasible_budget_is_reported_as_no_admissible_layout(ev, lps, tmp_path):
    """A budget below the cheapest admissible option: the master is infeasible (``LB = inf``).
    The row reports ``LB None``, ``close_reason`` NO_ADMISSIBLE and is certified only because no
    feasible layout exists either (``UB None``); the other budget is unaffected; the CLI bound
    from the pool reports the same."""
    from experiments import r6_o2_siting as R
    pool_path = str(tmp_path / "cuts.jsonl")
    recs = []
    cert = BD.SitingCertifier(ev, [65.0, 130.0], MENU, S.ROLES, lps=lps, pool=BD.CutPool(pool_path, BD.pool_signature(ev)),
                              tol_rel=1e-9, tol_abs=1e-6, on_record=recs.append)
    assert cert.enc.inv.min() > 65.0 and cert.menu_layouts(65.0) == []
    res = cert.run(warm_layouts=[BL.Layout.from_key(_T2)])
    r65, r130 = res[65.0], res[130.0]
    assert r65["LB"] is None and r65["UB"] is None and r65["gap"] is None
    assert r65["certified"] and r65["close_reason"] == BD.NO_ADMISSIBLE
    assert isinstance(r130["LB"], float) and r130["certified"] and r130["close_reason"] == "gap"
    assert r130["LB"] <= r130["UB"] + 1e-9
    fb = {r["budget"]: r for r in recs if r["kind"] == "final_bound"}
    assert fb[65.0]["LB"] is None and fb[65.0]["LB_infinite"] == BD.NO_ADMISSIBLE and fb[130.0]["LB"] == r130["LB"]
    json.dumps(C.jsonable(res))
    rows = R.bound_from_pool(ev, {"menu": MENU, "roles": S.ROLES, "budgets": [65.0, 130.0]}, pool_path, recs, ["written"],
                             cert.L, with_cover=False, top=None, threads=1)
    by_b = {r["budget"]: r for r in rows}
    assert by_b[65.0]["LB"] is None and by_b[65.0]["LB_kind"] == BD.NO_ADMISSIBLE and by_b[65.0]["gap"] is None
    assert math.isfinite(by_b[130.0]["LB"]) and by_b[130.0]["LB"] <= r130["UB"] + 1e-9
    cert.close()
