"""R7 re-plan after batch 2 (``notes/siting_production_replan_m1.md`` with the critic corrections
K1-K7), drivers lane: changes 2, 3, 7, 8 and 9 on the toy at Threads 1.

* change 2 -- ``r7_search.py --stage price-list --tier open_sites`` (``price_open`` records, UB
  set, no new cut, a re-run makes 0 solves) with the list rule ``--layouts m1-lp-order`` and the
  extension ``--extend-below-ub on``; the M1 -> M4 resume (``--m1-pass2 off``);
* change 8 -- the analyse ``m1_dual_statement``: the open-sites certificate (tol 0, K2.2) equals
  the exhaustive open-sites enumeration at m = 1, the all-candidates pair holds V*_1;
* change 3 -- ``--stage import-records --from DIR``: the same UB and cache hits as a single-dir run;
* change 7 -- ``--price-tier open_sites`` for pairs, m3, roles, comparison, restricted, oos and
  noradius: open-sites values, pool signature unchanged, every budget_result valid, and the
  comparison regret interval ``[LB_rule - UB*, UB_rule - LB*]`` holds the exhaustive regret;
* change 5 plumbing -- the bound probe (``--cells``, ``--warm-tier``, ``--ilp-params``) and the
  M6 stage ``ub-check``;
* change 9 -- the post-batch-3 lane files ``lanes_r2.txt`` / ``lanes_r2_tier2.txt``.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r7_cost as RC  # noqa: E402
from experiments import r7_search as RS  # noqa: E402
from experiments import r7_siting as R  # noqa: E402

DEPLOY = os.path.join(os.path.dirname(ROOT), "deploy", "aws")


def _run(script, args, timeout=900, env=None):
    e = dict(os.environ, PYTHONPATH=".")
    e.update(env or {})
    return subprocess.run([sys.executable, f"experiments/{script}"] + args, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout, env=e)


def _ok(r, what=""):
    assert r.returncode == 0, (what, r.stdout[-3000:] + r.stderr[-3000:])
    return r


def _recs(out):
    return C.load_jsonl(str(out / "records.jsonl"))


def _ctx(out, budgets=("1", "2")):
    args = RS.parse_args(["--smoke", "--budgets", *budgets, "--out-dir", str(out)])
    return R.Ctx(R.Run(args))


def _exhaustive(ctx, b, ev=None):
    ev = ev or ctx.ev
    lays = BL.enumerate_layouts(ctx.candidates, ctx.enc.options, b, ctx.spec, range(1, ctx.m_of[b] + 1), s_needs_charge=True)
    return {l.key(): ev.value(l) for l in lays}


def _n_lines(path):
    return sum(1 for ln in open(path) if ln.strip()) if os.path.exists(path) else 0


# ---------------------------------------------------------------------------
# changes 2 and 8: open-sites list pricing, M1 -> M4 resume, dual statement
# ---------------------------------------------------------------------------
def test_price_list_open_tier_list_rule_resume_m4_and_dual_statement(tmp_path):
    out = tmp_path / "a"
    base = ["--smoke", "--budgets", "1", "2", "--out-dir", str(out)]
    _ok(_run("r7_siting.py", base + ["--stage", "m1"]), "m1")
    cuts0, idx0 = _n_lines(out / "cuts.jsonl"), _n_lines(out / "cache" / "index.jsonl")
    ctx = _ctx(out)
    try:
        order = RS.m1_lp_order(ctx, ctx.run.load())
        assert order == sorted(order) and len(order) >= 2
    finally:
        ctx.close()
    pl = base + ["--stage", "price-list", "--tier", "open_sites", "--layouts", RS.M1_LP_ORDER, "--lp-order-top", "1",
                 "--extend-below-ub", "on", "--verify-start", "unchecked", "--cover-rows", "off"]
    _ok(_run("r7_search.py", pl), "price-list open")
    recs = _recs(out)
    po = [r for r in recs if r.get("kind") == "price_open"]
    lp = [r for r in recs if r.get("kind") == "list_price"]
    assert po and lp and all(r.get("tier") == "open_sites" for r in lp)
    assert lp[0]["layout_key"] == order[0][1]                          # LP order first
    assert _n_lines(out / "cuts.jsonl") == cuts0                        # open-sites pricing adds no cut
    assert not [r for r in recs if r.get("kind") == "price" and r.get("tag") == "list"]
    ext = [r for r in recs if r.get("kind") == "price_list_extension"][-1]
    ub_open = min(float(r["V"]) for r in po if r.get("V") is not None)
    assert ext["UB_open"] == pytest.approx(ub_open)
    br = [r for r in recs if r.get("kind") == "budget_result" and r["stage"] == "search_price_list"]
    b1 = min(float(r["budget"]) for r in br)
    r1 = [r for r in br if float(r["budget"]) == b1][-1]
    assert r1["UB"] <= ub_open + 1e-9
    # resume: a re-run prices nothing (no new cache row, every listed layout resumed)
    idx1 = _n_lines(out / "cache" / "index.jsonl")
    assert idx1 > idx0
    _ok(_run("r7_search.py", pl), "price-list open again")
    new = _recs(out)[len(recs):]
    again = [r for r in new if r.get("kind") == "list_price"]
    assert again and all(r.get("resumed") for r in again)
    assert _n_lines(out / "cache" / "index.jsonl") == idx1
    # M4: m1 resume without pricing; the restored open-sites UB drives the prunes, 0 ILP solves
    n_before = len(_recs(out))
    _ok(_run("r7_siting.py", base + ["--stage", "m1", "--m1-pass2", "off", "--max-escalations", "0",
                                     "--verify-start", "unchecked"]), "m4")
    m4 = [r for r in _recs(out)[n_before:] if r.get("kind") == "budget_result"][-1]
    assert m4["counters"]["ilp_solves"] == 0
    # analyse: the dual statement (change 8)
    _ok(_run("r7_siting.py", base + ["--stage", "analyse"]), "analyse")
    d = [r for r in _recs(out) if r.get("kind") == "m1_dual_statement"][-1]
    ctx = _ctx(out)
    try:
        b1 = min(ctx.budgets)
        ex_all = _exhaustive(ctx, b1)
        ex_open = _exhaustive(ctx, b1, BD._tier_evaluator(ctx.ev, "open_sites"))
    finally:
        ctx.close()
    v_all, v_open = min(ex_all.values()), min(ex_open.values())
    al, op = d["all_candidates"], d["open_sites"]
    assert al["LB"] <= v_all + 1e-6 <= al["UB"] + 2e-6
    assert op["complete"], op
    assert op["UB"] == pytest.approx(v_open, abs=1e-6)                 # the open-sites certificate is exact
    assert op["LB"] <= v_open + 1e-6 and op["gap"] <= 1e-6
    # every layout whose open-sites value is below UB_open + something was priced or bounded
    assert all(x["lower"] < al["UB"] for x in al["not_excluded"])
    text = (out / "RESULTS.md").read_text()
    assert "m = 1 under both followers" in text and "Open-sites follower (tol 0)" in text


# ---------------------------------------------------------------------------
# change 3: import-records
# ---------------------------------------------------------------------------
def test_import_records_gives_the_single_dir_ub_and_cache_hits(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    base_a = ["--smoke", "--budgets", "1", "--out-dir", str(a)]
    _ok(_run("r7_siting.py", base_a + ["--stage", "m1"]), "m1")
    shutil.copytree(a, b)
    base_b = ["--smoke", "--budgets", "1", "--out-dir", str(b)]
    pl = ["--stage", "price-list", "--tier", "open_sites", "--layouts", RS.M1_LP_ORDER, "--lp-order-top", "3"]
    _ok(_run("r7_search.py", base_b + pl), "price-list in b")
    rb = [r for r in _recs(b) if r.get("kind") == "budget_result"][-1]
    n_a = len(_recs(a))
    r = _ok(_run("r7_search.py", base_a + ["--stage", "import-records", "--from", str(b)]), "import")
    imp = [x for x in _recs(a) if x.get("kind") == "import_result"][-1]
    assert imp["by_kind"].get("price_open", 0) >= 1 and imp["n_cache_rows"] >= 1 and imp["n_schedules"] >= 1
    added = _recs(a)[n_a:]
    assert {x.get("kind") for x in added} <= {"price_open", "price", "import_result", "stage_skipped"}
    assert not [x for x in added if x.get("kind") in ("budget_result", "final_bound", "stage_done")]     # K3.4
    # a second import appends nothing
    n_a2 = len(_recs(a))
    _ok(_run("r7_search.py", base_a + ["--stage", "import-records", "--from", str(b)]), "import again")
    imp2 = [x for x in _recs(a)[n_a2:] if x.get("kind") == "import_result"][-1]
    assert imp2["n_records"] == 0 and imp2["n_cache_rows"] == 0
    # the same list in a: every layout resumed (0 solves) and the same UB as in b
    n_a3 = len(_recs(a))
    idx = _n_lines(a / "cache" / "index.jsonl")
    _ok(_run("r7_search.py", base_a + pl), "price-list in a")
    new = _recs(a)[n_a3:]
    assert all(x.get("resumed") for x in new if x.get("kind") == "list_price")
    assert _n_lines(a / "cache" / "index.jsonl") == idx
    ra = [x for x in new if x.get("kind") == "budget_result"][-1]
    assert ra["UB"] == pytest.approx(rb["UB"]) and ra["best_layout"] == rb["best_layout"]
    # the imported schedules are readable from a's cache (warm starts / M6)
    ctx = _ctx(a, ("1",))
    try:
        key = ra["best_layout"]
        row, port = BD._tier_evaluator(ctx.ev, "open_sites").cached_schedule(BL.Layout.from_key(key), 0)
        assert row is not None and port is not None and str(a) in row["schedule_path"]
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# change 7: --price-tier open_sites in the search / comparison stages
# ---------------------------------------------------------------------------
def test_price_tier_open_sites_stages_valid_bounds_and_regret(tmp_path):
    out = tmp_path / "s"
    base = ["--smoke", "--budgets", "1", "2", "3", "--out-dir", str(out)]
    op = ["--price-tier", "open_sites", "--verify-start", "unchecked", "--time-limit-many-sites", "3:40"]
    _ok(_run("r7_siting.py", base + ["--stage", "setup,feas,rootlp,m1"]), "m1")
    ctx = _ctx(out, ("1", "2", "3"))
    sig0 = BD.pool_signature(ctx.ev)
    ctx.close()
    steps = [("r7_search.py", ["--stage", "price-list", "--tier", "open_sites", "--layouts", RS.M1_LP_ORDER,
                               "--lp-order-top", "2", "--extend-below-ub", "on"]),
             ("r7_search.py", ["--stage", "pairs,m3,roles"] + op),
             ("r7_siting.py", ["--stage", "comparison", "--comparison-rules", "CSCD@1,2,3", "CSAV@2", "dot_all_pilot",
                               "dot_pilot_proxy@2", "--comparison-time-limits", "2:60"] + op),
             ("r7_siting.py", ["--stage", "restricted"] + op),
             ("r7_search.py", ["--stage", "oos,noradius,report", "--oos-layouts", "best@m1", "best@m2", "CSCD@m2",
                               "T4:SC:B2:C1"] + op),
             ("r7_siting.py", ["--stage", "analyse"])]
    for script, extra in steps:
        _ok(_run(script, base + extra, env={"R7_BATCH": "4"}), (script, extra))
    recs = _recs(out)
    tags = {str(r.get("tag")).split(":")[0] for r in recs if r.get("kind") == "price_open"}
    assert {"list", "pair", "m3", "baseline"} <= tags, tags
    assert not [r for r in recs if r.get("kind") == "price" and str(r.get("tag")).split(":")[0] in
                ("pair", "m3", "role_S", "role_hub", "baseline", "restricted")]          # no all-candidates pricing
    assert all(r.get("tier") == "open_sites" for r in recs if r.get("kind") in ("pair_price", "m3_price", "role_price")
               and r.get("status") not in ("NO_ADMISSIBLE_LAYOUT",))
    assert any(r.get("kind") == "role_row" and r.get("follower") == "open_sites" for r in recs)
    oo = [r for r in recs if r.get("kind") == "oos_result" and r.get("source") == "r7_search"]
    nr = [r for r in recs if r.get("kind") == "noradius_result"]
    assert oo and all(r.get("tier") == "open_sites" for r in oo) and nr and all(r.get("tier") == "open_sites" for r in nr)
    ctx = _ctx(out, ("1", "2", "3"))
    try:
        assert BD.pool_signature(ctx.ev) == sig0                         # pool signature unchanged
        ex = {b: _exhaustive(ctx, b) for b in ctx.budgets}
        for r in (x for x in recs if x.get("kind") == "budget_result"):
            vstar = min(ex[float(r["budget"])].values())
            assert r["LB"] is None or r["LB"] <= vstar + 1e-6, (r["stage"], r["LB"], vstar)
            assert r["UB"] is None or r["UB"] >= vstar - 1e-6
        # comparison rows: V = V_open >= V_all(rule); LB_rule <= V_all(rule); the regret interval holds
        last = R.last_results(recs)
        rows = [x for x in recs if x.get("kind") == "baseline" and x.get("status") == "PRICED"]
        assert rows and all(x.get("tier") == "open_sites" for x in rows)
        for x in rows:
            b = float(x["budget"])
            lay = BL.Layout.from_key(x["layout_key"])
            v_rule = ctx.ev.value(lay)
            assert x["V"] >= v_rule - 1e-6
            assert x["LB_rule"] is None or x["LB_rule"] <= v_rule + 1e-6
            regret = v_rule - min(ex[b].values())
            lo = None if x["LB_rule"] is None else x["LB_rule"] - last[b]["UB"]
            hi = x["V"] - last[b]["LB"]
            assert (lo is None or lo <= regret + 1e-6) and regret <= hi + 1e-6, (x["rule"], b, lo, regret, hi)
        # --time-limit-many-sites 3:40: the three-site row is solved at 40 s
        three = [r for r in recs if r.get("kind") == "price_open" and BL.Layout.from_key(r["layout_key"]).n_open >= 3]
        assert three and all(all(float(c.get("time_limit") or 0) >= 40.0 for c in r["rows"]) for r in three)
    finally:
        ctx.close()
    text = (out / "RESULTS.md").read_text()
    assert "LB rule" in text and "T4b" in text and "UB tier" in text
    assert "both sides OPTIMAL" in (out / "SEARCH.md").read_text()
    cost = RC.load(str(out))
    assert cost and all(c["status"] == "ok" for c in cost)


# ---------------------------------------------------------------------------
# change 5 plumbing (M3 / M5 probe) and M6
# ---------------------------------------------------------------------------
def test_bound_probe_cells_warm_params_and_ub_check(tmp_path):
    out = tmp_path / "p"
    base = ["--smoke", "--budgets", "1", "--out-dir", str(out)]
    _ok(_run("r7_siting.py", base + ["--stage", "m1"]), "m1")
    # a two-site layout: the m = 1 smoke evaluates every one-site layout (acceptance), so only a
    # layout outside budget m = 1 has uncached all-candidates cells
    key = "T1:SC:B1:C1|T3:SC:B1:C1"
    ctx = _ctx(out, ("1",))
    try:
        assert all(ctx.ev.cache.get(ctx.ev.cache_key(BL.Layout.from_key(key), s, "ilp")) is None for s in range(2))
    finally:
        ctx.close()
    _ok(_run("r7_search.py", base + ["--stage", "price-list", "--tier", "open_sites", "--layouts", key]), "open")
    probe = base + ["--stage", "price-list", "--tier", "all_candidates", "--layouts", key, "--cells", f"{key}@1",
                    "--warm-tier", "open_sites", "--cover-rows", "off", "--verify-start", "unchecked"]
    n0 = len(_recs(out))
    _ok(_run("r7_search.py", probe), "probe a")
    new = _recs(out)[n0:]
    pr = [r for r in new if r.get("kind") == "price" and r.get("layout_key") == key][-1]
    assert pr["n_solves"] == 1 and pr["skipped_scenarios"] == [0] and pr["status"] == "UNRESOLVED"   # K3.1
    assert pr["warm_tier"] == "open_sites" and pr["strict_scenarios"]
    assert any(r.get("kind") == "ub_check_all_candidates" and r.get("source") == "pricing_warm_start" for r in new)
    lp = [r for r in new if r.get("kind") == "list_price"][-1]
    assert lp["n_solves"] == 1 and lp["skipped_scenarios"] == [0]
    # variant b: --ilp-params gives new rows (new cache key), again one solve
    n1 = len(_recs(out))
    _ok(_run("r7_search.py", probe + ["--ilp-params", "Method=2"]), "probe b")
    pr2 = [r for r in _recs(out)[n1:] if r.get("kind") == "price" and r.get("layout_key") == key][-1]
    assert pr2["n_solves"] == 1 and pr2["ilp_params"] == {"Method": 2}
    assert pr2["lower"] >= pr["lower"] - 1e-9                           # bounds only rise (max with the prior)
    # review: the probe_summary record of the second variant lists both variants (reporting only)
    ps = [r for r in _recs(out)[n1:] if r.get("kind") == "probe_summary"][-1]
    assert sorted(v["variant"] for v in ps["variants"]) == ["Method=2", "default"]
    assert {(c["variant"], c["scenario"]) for c in ps["cells"]} == {("default", 1), ("Method=2", 1)}
    assert ps["tier2"] is False and ps["verdict"]
    # M6: the open-sites schedules of the UB layout checked on the all-candidates library
    _ok(_run("r7_search.py", base + ["--stage", "ub-check", "--layouts", key, "--max-templates", "1"]), "ub-check")
    chk = [r for r in _recs(out) if r.get("kind") == "ub_check_all_candidates" and r.get("source") == "check"][-1]
    o = R.open_priced(_recs(out))[key]
    assert chk["ok"] and chk["V_checked"] == pytest.approx(o["V"]) and chk["same_value"]
    n2 = len(_recs(out))
    _ok(_run("r7_search.py", base + ["--stage", "ub-check", "--layouts", key]), "ub-check again")
    assert any(r.get("kind") == "ub_check_skipped" for r in _recs(out)[n2:])
    # the open tier refuses the probe switches (they are for the all-candidates bound probe)
    r = _run("r7_search.py", base + ["--stage", "price-list", "--tier", "open_sites", "--layouts", key, "--cells", f"{key}@1"])
    assert r.returncode != 0 and "--tier all_candidates" in (r.stdout + r.stderr)


# ---------------------------------------------------------------------------
# change 9: lanes_r2.txt / lanes_r2_tier2.txt
# ---------------------------------------------------------------------------
def _cmd_args(cmd):
    toks = shlex.split(cmd)
    env = {}
    while toks and "=" in toks[0] and not toks[0].startswith("-"):
        k, v = toks.pop(0).split("=", 1)
        env[k] = v
    assert toks[0] == "python3"
    return env, toks[1], toks[2:]


def test_r2_lanes_plan(tmp_path):
    d = tmp_path / "lanes"
    _ok(_run("r7_search.py", ["--write-lanes", "--lanes-plan", "r2", "--lanes-dir", str(d)]), "write")
    prod = [ln.split("\t")[0] for ln in open(os.path.join(RS.PROD_LANES_ROOT, "lanes.txt")) if ln.strip()
            and not ln.startswith("#")] if os.path.exists(os.path.join(RS.PROD_LANES_ROOT, "lanes.txt")) else []
    for fname, gate, prefix in (("lanes_r2.txt", "r2_gate", "r2_"), ("lanes_r2_tier2.txt", "r2t2_gate", "r2t2_")):
        rows = [ln.split("\t") for ln in (d / fname).read_text().splitlines() if ln and not ln.startswith("#")]
        meta = json.loads((d / fname.replace(".txt", ".json")).read_text())
        assert rows[0][0] == gate and rows[0][2] == "-"
        names = []
        for name, thr, after, cmd in rows:
            assert name.startswith(prefix) and name not in prod and name not in names
            for x in ([] if after == "-" else after.split(",")):
                assert x in names                                          # one chain inside the file
            names.append(name)
            env, script, args = _cmd_args(cmd)
            assert env["R7_INSTANCE"] == "r7i.4xlarge" and env["R7_USD_PER_H"] == "1.0584" and env["R7_BATCH"]
            assert 1 <= int(thr) <= 12
            if script == "experiments/r7_gate.py":
                assert args == ["--cost-dir", "outputs/r7_siting"]
                continue
            assert args[args.index("--tol-rel") + 1] == "0.01" and args[args.index("--max-rss-gb") + 1] == "110"
            assert args[args.index("--out-dir") + 1] == "outputs/r7_siting"
            assert "--verify-start" in args and args[args.index("--verify-start") + 1] == "unchecked" or "ub-check" in args
            mod = RS if script.endswith("r7_search.py") else R
            ns = mod.parse_args(args)
            assert ns.max_threads == int(thr), name
            st = ns.stage.split(",")
            if not all(s in (RS.POOL_FREE if mod is RS else R.POOL_FREE_STAGES) for s in st):
                assert ns.lp_workers * ns.lp_threads + ns.master_threads <= ns.max_threads
                assert ns.price_workers * ns.threads <= ns.max_threads
            if name.startswith("r2_b"):
                assert ns.price_tier == "open_sites" and ns.time_limit == 600.0 and ns.time_limit_many_sites == "5:900"
            assert ("--held-out" in args) == (name == "r2_b5_oos")
        assert meta["lanes"] and [x["name"] for x in meta["lanes"]] == names
    l1 = {r.split("\t")[0]: r.split("\t") for r in (d / "lanes_r2.txt").read_text().splitlines() if r and not r.startswith("#")}
    assert list(l1) == ["r2_gate", "r2_m1_ub", "r2_m4", "r2_m6", "r2_m3probe_a", "r2_m3probe_b", "r2_b4_pairs", "r2_b4_m3",
                        "r2_b4_roles", "r2_b5_comparison", "r2_b5_restricted", "r2_b5_oos", "r2_b6_noradius"]
    # review: M4 / M6 / batch 4 never wait for the M3 probes (a side branch after M6)
    assert {nm: l1[nm][2] for nm in ("r2_m4", "r2_m6", "r2_m3probe_a", "r2_m3probe_b", "r2_b4_pairs")} == \
        {"r2_m4": "r2_m1_ub", "r2_m6": "r2_m4", "r2_m3probe_a": "r2_m6", "r2_m3probe_b": "r2_m6", "r2_b4_pairs": "r2_m6"}
    # review: no template build where the stage only prices (m3, comparison); pairs / roles / restricted keep cover rows
    assert RS.parse_args(_cmd_args(l1["r2_b4_m3"][3])[2]).cover_rows == "off"
    assert R.parse_args(_cmd_args(l1["r2_b5_comparison"][3])[2]).cover_rows == "off"
    for nm in ("r2_b4_pairs", "r2_b4_roles"):
        assert RS.parse_args(_cmd_args(l1[nm][3])[2]).cover_rows == "on"
    assert R.parse_args(_cmd_args(l1["r2_b5_restricted"][3])[2]).cover_rows == "on"
    head = (d / "lanes_r2.txt").read_text()
    assert "ONLY AFTER the 12 b3_rootlp lanes are done" in head
    m1 = RS.parse_args(_cmd_args(l1["r2_m1_ub"][3])[2])
    assert (m1.tier, m1.layouts, m1.lp_order_below, m1.extend_below_ub, m1.cover_rows, m1.time_limit) == \
        ("open_sites", [RS.M1_LP_ORDER], 1075.0, "on", "off", 600.0)
    assert (m1.price_workers, m1.threads) == (4, 3)
    for nm, params in (("r2_m3probe_a", None), ("r2_m3probe_b", ["Method=2"])):
        p = RS.parse_args(_cmd_args(l1[nm][3])[2])
        assert (p.tier, p.cells, p.warm_tier, p.ilp_params, p.time_limit) == \
            ("all_candidates", ["D29:5", "D29:2"], "open_sites", params, 1200.0)
        assert (p.price_workers, p.threads, int(l1[nm][1])) == (2, 4, 8)          # K3.6: 2 x 4
    m4 = R.parse_args(_cmd_args(l1["r2_m4"][3])[2])
    assert (m4.stage, m4.m1_pass2, m4.max_escalations) == ("m1", "off", 0)
    m6 = RS.parse_args(_cmd_args(l1["r2_m6"][3])[2])
    assert (m6.stage, m6.layouts, m6.max_templates) == ("ub-check", ["best@m1"], 2)
    walls = {"r2_b4_pairs": 4, "r2_b4_m3": 1, "r2_b4_roles": 2.5, "r2_b5_oos": 1, "r2_b6_noradius": 2}
    for nm, w in walls.items():
        assert RS.parse_args(_cmd_args(l1[nm][3])[2]).wall == w
    assert R.parse_args(_cmd_args(l1["r2_b5_comparison"][3])[2]).wall_comparison == 2
    assert R.parse_args(_cmd_args(l1["r2_b5_restricted"][3])[2]).wall_restricted == 1
    meta = json.loads((d / "lanes_r2.json").read_text())
    b46 = sum(b["hours"] for b in meta["batches"] if b["batch"] in ("4", "5", "6"))
    assert b46 == pytest.approx(12.6, abs=0.05)        # re-plan section 3 + 3 x 0.3 h template set-up (review)
    assert meta["tier2_hours"] == pytest.approx(3.7, abs=0.05)            # K5 / K6
    # Tier 2 lanes: the better M3 variant through --ilp-params
    d2 = tmp_path / "lanes2"
    _ok(_run("r7_search.py", ["--write-lanes", "--lanes-plan", "r2", "--lanes-dir", str(d2), "--ilp-params", "Method=2"]))
    t2 = {r.split("\t")[0]: r.split("\t") for r in (d2 / "lanes_r2_tier2.txt").read_text().splitlines()
          if r and not r.startswith("#")}
    p = RS.parse_args(_cmd_args(t2["r2t2_m5"][3])[2])
    assert p.ilp_params == ["Method=2"] and p.cells == ["D29:0-5", "D28:0-5", "D34:0-5"] and len(p.layouts) == 3
    # the gate writes a cost row with --cost-dir
    from experiments import r7_gate as RG
    assert RG.check() == []
    assert RG.main(["--cost-dir", str(tmp_path / "c")]) == 0
    rows = RC.load(str(tmp_path / "c"))
    assert len(rows) == 1 and rows[0]["stage"] == "gate" and rows[0]["status"] == "ok"
    # the deploy dispatcher accepts both files (dry run)
    sh = os.path.join(DEPLOY, "run_lanes.sh")
    if os.path.exists(sh):
        for fname in ("lanes_r2.txt", "lanes_r2_tier2.txt"):
            p = subprocess.run(["bash", sh, "start", str(d / fname), "--max-threads", "12", "--dry-run"], capture_output=True,
                               text=True, env=dict(os.environ, LANES_DIR=str(tmp_path / "ld")), timeout=120)
            assert p.returncode == 0 and "dry run: nothing started" in p.stdout, p.stdout[-2000:] + p.stderr[-2000:]


# ---------------------------------------------------------------------------
# review fixes of the r2 code (labels, reporting, the no-radius evaluator)
# ---------------------------------------------------------------------------
def test_probe_summary_lift_and_verdict():
    qs = [100.0, 200.0, 300.0]
    def rows(b):          # bound incl. C_setup = 10
        return [{"scenario": s, "status": "TIME_LIMIT", "bound": b[s] + 10.0, "C_setup": 10.0, "time_limit": 1200.0,
                 "node_count": 5.0, "runtime_s": 1200.0} for s in (0, 2)]
    recs = [{"kind": "lp_location", "layout_key": "L1", "Qs": qs},
            {"kind": "price", "tier": "all_candidates", "layout_key": "L1", "scenarios": [0, 2], "strict_scenarios": True,
             "ilp_params": {}, "rows": rows({0: 100.5, 2: 301.5})},
            {"kind": "price", "tier": "all_candidates", "layout_key": "L1", "scenarios": [0, 2], "strict_scenarios": True,
             "ilp_params": {"Method": 2}, "rows": rows({0: 102.0, 2: 303.0})},
            {"kind": "price", "tier": "all_candidates", "layout_key": "L1", "rows": rows({0: 500.0, 2: 500.0})}]  # not a probe
    ps = RS.probe_summary(recs)
    by = {v["variant"]: v for v in ps["variants"]}
    assert by["default"]["mean_lift_pct"] == pytest.approx((0.5 + 0.5) / 2)
    assert by["Method=2"]["mean_lift_pct"] == pytest.approx((2.0 + 1.0) / 2)
    assert ps["best_variant"] == "Method=2" and ps["tier2"] and "--ilp-params Method=2" in ps["verdict"]
    ps2 = RS.probe_summary(recs[:2])
    assert not ps2["tier2"] and ps2["verdict"].startswith("skip Tier 2")
    # a bound below the LP never lowers the lift below 0 (the pricing keeps max(Qs, bound))
    low = [recs[0], dict(recs[1], rows=rows({0: 50.0, 2: 50.0}))]
    assert RS.probe_summary(low)["variants"][0]["mean_lift_pct"] == pytest.approx(0.0)
    assert RS.probe_summary([recs[0]]) is None


def test_n_priced_on_open_counts_priced_with_a_value_only():
    from types import SimpleNamespace as NS
    po = {"A": NS(status="PRICED", V=1.0), "B": NS(status="UNRESOLVED", V=None), "C": NS(status="INFEASIBLE", V=None),
          "D": NS(status="PRUNED_BY_BOUND", V=2.0)}
    assert BD.SitingCertifier._n_priced_on_open(NS(priced_open=po), ["A", "B", "C", "D", "E"]) == 1


def test_dual_statement_lb_unknown_names_no_layout():
    d = {"all_candidates": {"LB": 1.0, "UB": 2.0, "gap": 0.5, "LB_kind": "enumeration", "best_layout": "X", "UB_tier": "open_sites",
                            "n_locations_not_excluded": 0, "not_excluded": [], "n_unknown": 3},
         "open_sites": {"LB": None, "UB": 2.0, "gap": None, "best_layout": "X", "argmin": None, "complete": False,
                        "n_to_price": 0, "to_price": [], "n_unknown": 3, "ranking": []},
         "ub_check": None}
    text = "\n".join(R.dual_statement_lines(d))
    assert "LB unknown: 3 layouts without any bound" in text and "LB from" not in text


def test_noradius_evaluator_follows_verify_start(tmp_path):
    out = tmp_path / "nr"
    args = RS.parse_args(["--smoke", "--budgets", "1", "--out-dir", str(out), "--verify-start", "unchecked"])
    run = R.Run(args)
    ctx = R.Ctx(run)
    try:
        assert ctx.ev.verify_checked_starts is False
        ev = RS.noradius_evaluator(run, ctx)
        assert ev.verify_checked_starts is False
        assert BD._tier_evaluator(ev, "open_sites").verify_checked_starts is False
    finally:
        ctx.close()
