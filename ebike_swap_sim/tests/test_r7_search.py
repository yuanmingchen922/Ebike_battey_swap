"""R7 production drivers (``notes/siting_production_plan.md`` section 5 items 5-7): the comparison
filter of ``experiments/r7_siting.py``, the search driver ``experiments/r7_search.py`` (pair /
triple / hub-screen bounds valid against the exhaustive toy values, the budget-window rule, the
held-out feasibility check, list pricing, the no-radius evaluator), ``cost.jsonl``
(``experiments/r7_cost.py``) and the production lane plan.  Toy only, Threads 1."""
from __future__ import annotations

import json
import math
import os
import shlex
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


def _ctx(out, extra=()):
    args = RS.parse_args(["--smoke", "--budgets", "1", "2", "3", "--out-dir", str(out)] + list(extra))
    return R.Ctx(R.Run(args))


def _exhaustive(ctx, b):
    lays = BL.enumerate_layouts(ctx.candidates, ctx.enc.options, b, ctx.spec, range(1, ctx.m_of[b] + 1), s_needs_charge=True)
    return {l.key(): ctx.ev.value(l) for l in lays}


# ---------------------------------------------------------------------------
# item 5: comparison filter
# ---------------------------------------------------------------------------
def test_comparison_filter_and_time_limits(tmp_path):
    ctx = _ctx(tmp_path / "f")
    try:
        a = ctx.run.args
        f = R.comparison_filter(a, ctx)
        assert all(v is None for v in f.values()) and set(f) == set(R.COMPARISON_NAMES)        # default: every row
        a.comparison_rules = ["CSCD@1,2,3", "CSAV@2", "dot_all_pilot", "dot_pilot_proxy@2"]
        f = R.comparison_filter(a, ctx)
        assert f == {"CSCD": {1, 2, 3}, "CSAV": {2}, "dot_all_pilot": None, "dot_pilot_proxy": {2}}
        a.comparison_rules, a.comparison_budgets = ["CSTC", "transplant@1"], [2]
        f = R.comparison_filter(a, ctx)
        assert f == {"CSTC": {2}, "transplant": {1}}
        a.comparison_rules = None
        f = R.comparison_filter(a, ctx)
        assert f["CSCD"] == {2} and f["dot_all_pilot"] is None and f["transplant"] is None
        a.comparison_rules = ["nope"]
        with pytest.raises(SystemExit):
            R.comparison_filter(a, ctx)
        a.comparison_time_limits = None
        assert R.comparison_time_limits(a, ctx) == {}                    # toy: unchanged behaviour
        ctx.production = True
        assert R.comparison_time_limits(a, ctx) == {2: 600.0}            # manhattan_dot: m = 2 rows at 600 s
        a.comparison_time_limits = ["2:900", "3:450"]
        assert R.comparison_time_limits(a, ctx) == {2: 900.0, 3: 450.0}
        a.comparison_time_limits = ["none"]
        assert R.comparison_time_limits(a, ctx) == {}
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# item 7: cost.jsonl
# ---------------------------------------------------------------------------
def test_cost_log_rows_env_and_interval_union(tmp_path, monkeypatch):
    monkeypatch.setenv("R7_INSTANCE", "r7a.4xlarge")
    monkeypatch.setenv("R7_USD_PER_H", "1.2172")
    monkeypatch.setenv("R7_BATCH", "3")
    log = RC.CostLog(str(tmp_path), "rootlp", "r7_siting.py", argv=["--stage", "rootlp"])
    log.t0 -= 1800.0
    row = log.finish("ok")
    assert log.finish("ok") is None                                       # once per invocation
    assert row["instance"] == "r7a.4xlarge" and row["usd_per_h"] == 1.2172 and row["batch"] == "3"
    assert row["wall_h"] == pytest.approx(0.5, abs=1e-3) and row["usd"] == pytest.approx(0.5 * 1.2172, abs=2e-3)
    for k in ("stage", "start", "end", "wall_h", "instance", "usd_per_h", "usd"):
        assert k in row
    monkeypatch.delenv("R7_INSTANCE")
    monkeypatch.delenv("R7_USD_PER_H")
    assert RC.instance_price() == ("r7i.4xlarge", 1.0584)
    # two overlapping lanes of one batch (0-2 h and 1-3 h) and one of another batch
    p = tmp_path / "c2"
    p.mkdir()
    rows = [{"batch": "3", "stage": "a", "start_epoch": 0.0, "end_epoch": 7200.0, "wall_h": 2.0, "usd_per_h": 1.0, "usd": 2.0},
            {"batch": "3", "stage": "b", "start_epoch": 3600.0, "end_epoch": 10800.0, "wall_h": 2.0, "usd_per_h": 1.0, "usd": 2.0},
            {"batch": "4", "stage": "c", "start_epoch": 20000.0, "end_epoch": 23600.0, "wall_h": 1.0, "usd_per_h": 1.0, "usd": 1.0},
            {"batch": "4", "stage": "d", "start_epoch": 0.0, "end_epoch": 1.0, "wall_h": 0.0, "usd": 0.0, "dry_run": True}]
    (p / "cost.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    s = RC.summarise(str(p))
    assert s["batches"]["3"]["usd_sum"] == pytest.approx(4.0) and s["batches"]["3"]["instance_h"] == pytest.approx(3.0)
    assert s["batches"]["4"]["n"] == 1 and s["total"]["usd_instance"] == pytest.approx(4.0)
    assert any("| total |" in ln for ln in RC.summary_lines(str(p)))


# ---------------------------------------------------------------------------
# item 6: bounds of the search driver are valid (toy, exhaustive)
# ---------------------------------------------------------------------------
def test_set_bounds_valid_for_every_layout_and_window(tmp_path):
    """Every pair / triple bound of ``r7_search.set_bound`` (S_LP rule) is at most the exhaustive
    value of every layout with that open set (``bound_exact``, all sizes), and ``bound_window``
    is at most the value of every layout inside the set with investment in the window above the
    smaller budget; feasibility skip marks and the subset cuts never cut a finite layout."""
    out = tmp_path / "b"
    r = _run("r7_siting.py", ["--smoke", "--budgets", "1", "2", "3", "--stage", "setup,feas,m1", "--out-dir", str(out)])
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    ctx = _ctx(out)
    try:
        cert = ctx.certifier("relaxed", wall_h=1.0, label="t")
        ex = {}
        for b in ctx.budgets:
            ex.update(_exhaustive(ctx, b))
        locs = ctx.ids
        n_checked = 0
        for m in (2, 3):
            b = RS.budget_of(ctx, m)
            lo = RS.smaller_budget(ctx, b)
            sets = [frozenset(x) for x in __import__("itertools").combinations(locs, m)]
            for A in sets:
                rec = RS.set_bound(ctx, cert, A, b, ctx.S_LP, tag="t")
                for key, v in ex.items():
                    lay = BL.Layout.from_key(key)
                    inv = lay.investment(ctx.spec)
                    if inv > b + 1e-6 or not set(lay.locations()) <= A:
                        continue
                    if set(lay.locations()) == set(A) and rec["bound_exact"] is not None:
                        assert rec["bound_exact"] <= v + 1e-6, (A, key, rec["bound_exact"], v)
                        n_checked += 1
                    if inv > lo + 1e-6 and rec["bound_window"] is not None:
                        assert rec["bound_window"] <= v + 1e-6, (A, key, rec["bound_window"], v)
                        n_checked += 1
        assert n_checked > 20
        # the master never excludes a finite layout (terminal rows of the skip list, subset cuts)
        for key, v in ex.items():
            if math.isfinite(v):
                assert cert.master.envelope(BL.Layout.from_key(key)) <= v + 1e-6, key
        cert.close()
    finally:
        ctx.close()


def test_search_smoke_end_to_end_bounds_and_resume(tmp_path):
    """The production order on the toy (feas, rootlp, m1 -> calib, pairs, m3, roles -> filtered
    comparison, restricted -> oos with the held-out check -> noradius -> price-list -> report):
    every budget_result satisfies LB <= V* <= UB against the exhaustive optimum, the m = 1
    certificate survives the later stages, the comparison rows follow the filter, cost.jsonl has
    one row per invocation, and a second run resumes (stages skipped, no new solve)."""
    out = tmp_path / "s"
    base = ["--smoke", "--budgets", "1", "2", "3", "--out-dir", str(out)]
    steps = [("r7_siting.py", ["--stage", "setup,feas,rootlp,m1"]),
             ("r7_search.py", ["--stage", "calib,oos-feas,pairs,m3,roles"]),
             ("r7_siting.py", ["--stage", "comparison", "--comparison-rules", "CSCD@1,2,3", "CSAV@2", "dot_all_pilot",
                               "dot_pilot_proxy@2", "--comparison-time-limits", "2:60"]),
             ("r7_siting.py", ["--stage", "restricted"]),
             ("r7_search.py", ["--stage", "oos,noradius,report", "--oos-layouts", "best@m1", "best@m2", "CSCD@m2",
                               "dot_all_pilot", "T4:SC:B2:C1"]),
             ("r7_search.py", ["--stage", "price-list", "--evaluator", "out", "--layouts", "best@m2", "T1:SC:B1:C1|T2:SC:B1:C1"]),
             ("r7_siting.py", ["--stage", "analyse"])]
    for script, extra in steps:
        r = _run(script, base + extra, env={"R7_BATCH": "9"})
        assert r.returncode == 0, (script, extra, r.stdout[-3000:] + r.stderr[-3000:])
    recs = C.load_jsonl(str(out / "records.jsonl"))
    kinds = {x.get("kind") for x in recs}
    for k in ("calib", "pair_screen", "pair_summary", "m3_summary", "role_row", "hub_screen", "oos_feas", "oos_result",
              "noradius_result", "noradius_summary", "list_price", "baseline", "restricted_result"):
        assert k in kinds, k
    ctx = _ctx(out)
    try:
        for b in ctx.budgets:
            vstar = min(_exhaustive(ctx, b).values())
            for r in (x for x in recs if x.get("kind") == "budget_result" and float(x["budget"]) == b):
                assert r["LB"] is None or r["LB"] <= vstar + 1e-6, (b, r["stage"], r["LB"], vstar)
                assert r["UB"] is None or r["UB"] >= vstar - 1e-6
        last = R.last_results(recs)
        assert last[min(ctx.budgets)]["certified"]                      # the m = 1 certificate survives
        # pair screens: an excluded pair has no layout below UB_2 - tol
        b2 = RS.budget_of(ctx, 2)
        ex2 = _exhaustive(ctx, b2)
        summ = [x for x in recs if x.get("kind") == "pair_summary"][-1]
        for p in summ["pairs"]:
            if p["excluded"]:
                inside = [v for k, v in ex2.items() if set(BL.Layout.from_key(k).locations()) == set(p["atoms"])]
                assert all(v >= summ["UB"] - 1e-6 * max(1.0, abs(summ["UB"])) - 1e-9 for v in inside), p
        # held-out check: the T4 one-site layout is reported infeasible out of sample iff a bike lacks a terminal arc
        o = {x["layout_key"]: x for x in recs if x.get("kind") == "oos_result" and x.get("source") == "r7_search"}
        inf = any(BD.verify_terminal_infeasible(ctx.ev_out, BL.Layout.from_key("T4:SC:B2:C1"), s)
                  for s in range(ctx.ev_out.n_scenarios))
        assert (o["T4:SC:B2:C1"]["status"] == "INFEASIBLE_OUT_OF_SAMPLE") == inf
        assert all(x["status"] == "PRICED" for k, x in o.items() if k != "T4:SC:B2:C1")
    finally:
        ctx.close()
    rows = [x for x in recs if x.get("kind") == "baseline"]
    got = {(x["rule"], int(round(float(x["budget"]) / R.TOY_UNIT))) for x in rows}
    assert got == {("CSCD", 1), ("CSCD", 2), ("CSCD", 3), ("CSAV", 2), ("dot_pilot_proxy", 2)}
    assert all(x.get("time_limit") == 60.0 for x in rows if int(round(float(x["budget"]) / R.TOY_UNIT)) == 2)
    cost = RC.load(str(out))
    # one end row per billed invocation; the laptop analysis (last step) writes none (fixer pass)
    assert len(cost) == len(steps) - 1 and all(c["batch"] == "9" and c["status"] == "ok" for c in cost)
    assert len(RC.load(str(out), events=True)) == 2 * (len(steps) - 1) and not RC.unfinished(str(out))
    assert "Cost per batch" in (out / "RESULTS.md").read_text() and (out / "SEARCH.md").exists()
    # fixer pass: the pair search finds the m = 2 optimum (an SC + S layout of a screened pair) and the
    # restricted stage folds the incumbents back, so the last budget_result of m = 2 holds V*_2
    last = R.last_results(recs)
    assert last[b2]["UB"] == pytest.approx(min(ex2.values()), abs=1e-6)
    assert any(x.get("kind") == "pair_price" and (x.get("try") or 1) > 1 for x in recs)
    # analyse wrote the plan record / candidates.csv; the map reads the production records
    assert (out / "candidates.csv").exists() and "Certificate details" in (out / "RESULTS.md").read_text()
    m = subprocess.run([sys.executable, "outputs/r7_siting/figs/siting_map.py", "--out-dir", str(out), "--fig-dir",
                        str(tmp_path / "fig")], cwd=ROOT, capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, PYTHONPATH="."))
    assert m.returncode == 0, m.stderr[-2000:]
    ms = json.loads((tmp_path / "fig" / "map_summary.json").read_text())
    assert ms["panel2"].startswith("production") and "T4" in ms["terminal_infeasible"]
    # resume: the solved stages are skipped and nothing is solved again
    r = _run("r7_search.py", base + ["--stage", "pairs,m3,roles,oos,noradius"])
    assert r.returncode == 0 and r.stdout.count('"stage_skipped"') == 5, r.stdout[-2000:]
    r = _run("r7_search.py", base + ["--stage", "pairs,roles", "--redo"])
    assert r.returncode == 0, r.stderr[-2000:]
    new = C.load_jsonl(str(out / "records.jsonl"))[len(recs):]
    before = {x["layout_key"] for x in recs if x.get("kind") == "price" and x.get("status") in ("PRICED", "INFEASIBLE")}
    again = [x["layout_key"] for x in new if x.get("kind") == "price" and x.get("n_solves") and x["layout_key"] in before]
    assert not again, f"a --redo stage re-solved stored prices: {again}"
    solved = {(tuple(x["atoms"]), x["scenario"]) for x in recs if x.get("kind") == "subset_lp"}
    assert not [x for x in new if x.get("kind") == "subset_lp" and (tuple(x["atoms"]), x["scenario"]) in solved], \
        "a --redo stage re-solved a memoised subset LP"


def test_search_dry_run_and_skips(tmp_path):
    out = tmp_path / "d"
    r = _run("r7_search.py", ["--smoke", "--dry-run", "--stage", "calib,oos-feas,pairs,m3,roles,oos,noradius,report",
                              "--out-dir", str(out)])
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    recs = C.load_jsonl(str(out / "records.jsonl"))
    assert not [x for x in recs if x.get("kind") in ("price", "subset_lp", "lp_layout")]
    assert any(x.get("kind") == "pairs_plan" for x in recs)
    m3 = [x for x in recs if x.get("stage") == "search_m3"]
    assert m3 and m3[0]["kind"] == "stage_skipped"                       # smoke default budgets 1 2: no m = 3
    r = _run("r7_search.py", ["--smoke", "--stage", "bogus", "--out-dir", str(out)])
    assert r.returncode != 0 and "unknown stage" in r.stderr


def test_noradius_evaluator_differs_only_by_the_radius(tmp_path):
    ctx = _ctx(tmp_path / "n", ["--approach-radius", "3"])
    try:
        run = ctx.run
        ev = RS.noradius_evaluator(run, ctx)
        sig_r, sig_n = ctx.ev.pruning_signature(0), ev.pruning_signature(0)
        assert "reposition_target_radius" in sig_r and "reposition_target_radius" not in sig_n
        assert {k: v for k, v in sig_r.items() if not k.startswith("reposition_")} == \
            {k: v for k, v in sig_n.items() if not k.startswith("reposition_")}
        lay = BL.Layout.from_key("T2:SC:B2:C1")
        assert ev.cache_key(lay, 0, "ilp") != ctx.ev.cache_key(lay, 0, "ilp")
        assert ev.seeds == ctx.ev.seeds and ev.demand_md5 == ctx.ev.demand_md5 and ev.p == ctx.ev.p
        assert ev.time_limit == ctx.ev.time_limit and ev.threads == ctx.ev.threads
        # the radius only removes arcs: every no-radius library holds the radius library
        _i, lib_r = ctx.ev.template(0)
        _j, lib_n = ev.template(0)
        assert len(lib_n) >= len(lib_r)
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# production lanes (plan 2.1 / 2.2, r7i.4xlarge, 12 threads, --max-rss-gb 110)
# ---------------------------------------------------------------------------
def _cmd_args(cmd):
    toks = shlex.split(cmd)
    while toks and "=" in toks[0] and not toks[0].startswith("-"):
        toks.pop(0)
    assert toks[0] == "python3"
    return toks[1], toks[2:]


def test_production_lanes_plan(tmp_path):
    lanes_dir = tmp_path / "prod"
    r = _run("r7_search.py", ["--write-lanes", "--lanes-dir", str(lanes_dir)])
    assert r.returncode == 0, r.stderr[-2000:]
    rows = [ln.split("\t") for ln in (lanes_dir / "lanes.txt").read_text().splitlines() if ln and not ln.startswith("#")]
    meta = json.loads((lanes_dir / "lanes.json").read_text())
    assert [b["batch"] for b in meta["batches"]] == [1, 2, 3, 4, 5, 6]
    assert meta["total_usd"] == pytest.approx(52.8, abs=0.2)          # plan 2.2: 49.9-50.0 h = 52.8 USD
    names = []
    batch_of = {}
    for name, thr, after, cmd in rows:
        assert len(cmd) and thr.isdigit() and 1 <= int(thr) <= 12
        for a in ([] if after == "-" else after.split(",")):
            assert a in names, (name, a)                                 # dependencies come first
            assert batch_of[a] <= int(cmd.split("R7_BATCH=")[1].split()[0])
        b = int(cmd.split("R7_BATCH=")[1].split()[0])
        batch_of[name] = b
        names.append(name)
        assert "R7_INSTANCE=r7i.4xlarge" in cmd and "R7_USD_PER_H=1.0584" in cmd
        script, args = _cmd_args(cmd)
        if name == "b0_gate":                                             # fixer pass: STALE CODE gate first
            assert script == "experiments/r7_gate.py" and not names[:-1] and thr == "1"
            continue
        # fixer pass: the held-out instances are built only by the two lanes that use them
        assert ("--held-out" in args) == (name in ("b1_oos_feas", "b5_oos")), name
        assert "--max-rss-gb" in args and args[args.index("--max-rss-gb") + 1] == "110"
        assert args[args.index("--approach-radius") + 1] == "14" and args[args.index("--scenarios") + 1] == "12"
        assert args[args.index("--tol-rel") + 1] == "0.01"
        mod = RS if script.endswith("r7_search.py") else R
        ns = mod.parse_args(args)                                         # every flag exists
        st = ns.stage.split(",")
        assert ns.max_threads == int(thr), (name, ns.max_threads, thr)
        pool_free = all(s in (R.POOL_FREE_STAGES if mod is R else RS.POOL_FREE) for s in st)
        if pool_free:
            assert ns.lp_threads <= ns.max_threads
        else:
            assert ns.lp_workers * ns.lp_threads + ns.master_threads <= ns.max_threads
            assert ns.price_workers * ns.threads <= ns.max_threads
    assert [batch_of[n] for n in names] == sorted(batch_of[n] for n in names)
    roots = [r for r in rows if r[0].startswith("b3_rootlp")]
    assert len(roots) == 12 and sum(1 for r in roots if r[2] == "b2_m1") == 3   # at most 3 all-open LPs at once
    assert sum(int(r[1]) for r in roots[:3]) <= 12
    assert "--root-import" in roots[0][3] and all("--root-import" not in r[3] for r in roots[1:])
    cmp_ = [r for r in rows if r[0] == "b5_comparison"][0][3]
    assert "--comparison-rules CSCD@1,2,3 CSAV@2 dot_all_pilot dot_pilot_proxy@2" in cmp_ and "2:600" in cmp_
    pairs = [r for r in rows if r[0] == "b4_pairs"][0][3]
    assert "|" not in pairs and "D30+D38" in pairs
    assert [r for r in rows if r[0] == "b1_calib"][0][2] == "b0_gate"
    head = (lanes_dir / "lanes.txt").read_text()
    assert "LANES_DIR=$PWD/ebike_swap_sim/" in head and "probe done" in head
    from experiments import r7_gate as RG
    assert RG.check() == [] and RG.main([]) == 0
    assert RG.check(markers=[("def no_such_marker", "experiments/r7_gate.py")])
    # the deploy dispatcher accepts the file (dry run: nothing started)
    sh = os.path.join(DEPLOY, "run_lanes.sh")
    if os.path.exists(sh):
        p = subprocess.run(["bash", sh, "start", str(lanes_dir / "lanes.txt"), "--max-threads", "12", "--dry-run"],
                           capture_output=True, text=True, env=dict(os.environ, LANES_DIR=str(tmp_path / "ld")), timeout=120)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
        assert "dry run: nothing started" in p.stdout and "b1_calib" in p.stdout


# ---------------------------------------------------------------------------
# fixer pass (reviews of 2026-10-21)
# ---------------------------------------------------------------------------
def _cost_child(d, sig):
    code = ("import sys, time\n"
            f"sys.path.insert(0, {ROOT!r})\n"
            "from experiments import r7_cost as RC\n"
            f"log = RC.CostLog({str(d)!r}, 'm1', 'x.py', argv=[])\n"
            "log.install_signal_handlers()\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n")
    p = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True,
                         env=dict(os.environ, R7_BATCH="2"))
    assert p.stdout.readline().strip() == "ready"
    p.send_signal(sig)
    rc = p.wait(timeout=30)
    p.stdout.close()
    return rc


def test_cost_rows_on_sigterm_sighup_and_hard_kill(tmp_path):
    """A lane stopped by run_lanes.sh (SIGTERM) or tmux kill-session (SIGHUP) writes its end row
    (status killed: ...) and exits 128 + signum at once; a SIGKILL leaves a start row that
    summarise counts as unfinished."""
    import signal
    for sig, name in ((signal.SIGTERM, "SIGTERM"), (signal.SIGHUP, "SIGHUP")):
        d = tmp_path / name
        d.mkdir()
        assert _cost_child(d, sig) == 128 + int(sig)
        rows = RC.load(str(d))
        assert len(rows) == 1 and rows[0]["status"] == f"killed: {name}" and rows[0]["batch"] == "2"
        assert RC.summarise(str(d))["batches"]["2"]["failed"] == 1
    d = tmp_path / "kill"
    d.mkdir()
    assert _cost_child(d, signal.SIGKILL) == -int(signal.SIGKILL)
    assert RC.load(str(d)) == [] and len(RC.unfinished(str(d))) == 1
    s = RC.summarise(str(d))
    assert s["n_unfinished"] == 1 and s["batches"]["2"]["unfinished"] == 1
    assert any("start row but no end row" in ln for ln in RC.summary_lines(str(d)))


def test_cost_total_leaves_out_unbatched_rows(tmp_path):
    rows = [{"batch": "3", "stage": "a", "start_epoch": 0.0, "end_epoch": 3600.0, "wall_h": 1.0, "usd_per_h": 1.0, "usd": 1.0},
            {"batch": None, "stage": "analyse", "start_epoch": 0.0, "end_epoch": 3600.0, "wall_h": 1.0, "usd_per_h": 1.0,
             "usd": 1.0}]
    (tmp_path / "cost.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    s = RC.summarise(str(tmp_path))
    assert s["total"]["usd_sum"] == pytest.approx(1.0) and not s["batches"]["None"]["in_total"]
    assert any("not in total" in ln for ln in RC.summary_lines(str(tmp_path)))
    log = RC.CostLog(str(tmp_path / "x"), "analyse", "r7_siting.py", enabled=False)
    assert log.finish("ok") is None and not (tmp_path / "x" / "cost.jsonl").exists()


def test_records_of_another_instance_are_invisible(tmp_path):
    """Every record carries the instance md5; Run.load (and so the restored LBs, prices and
    incumbents) ignores the records of another instance written into the same out-dir."""
    ctx = _ctx(tmp_path / "i")
    try:
        run = ctx.run
        b = min(ctx.budgets)
        run.emit({"kind": "budget_result", "target": "relaxed", "budget": b, "LB": 1e9, "UB": 1e9, "instance_md5": "foreign"})
        run.emit({"kind": "budget_result", "target": "relaxed", "budget": b, "LB": 1.0, "UB": 2.0})
        recs = run.load()
        assert all(r.get("instance_md5") == ctx.instance_md5() for r in recs) and len(recs) == 1
        assert R.last_results(recs)[b]["LB"] == 1.0
        cert = ctx.certifier("relaxed", wall_h=1.0, label="t")
        assert R.restore_prior_lb(cert, run.load())[b] == 1.0
        cert.close()
        assert ctx.instance_md5() != ctx.config_md5()                       # budgets left out
    finally:
        ctx.close()


def test_max_escalations_default_per_family():
    assert RS.parse_args(["--smoke"]).max_escalations == 2
    assert RS.parse_args(["--family", "r5_manhattan"]).max_escalations == 2
    assert RS.parse_args(["--family", "manhattan_dot"]).max_escalations == 3
    assert RS.parse_args(["--smoke", "--max-escalations", "4"]).max_escalations == 4


def test_rootlp_lane_fails_without_a_value(tmp_path):
    """A rootlp lane that delivers no value (here the RSS guard trips) exits 3 without stage_done,
    so the dispatcher marks it failed and it can be re-run."""
    out = tmp_path / "r"
    r = _run("r7_siting.py", ["--smoke", "--stage", "rootlp", "--max-rss-gb", "0.0001", "--out-dir", str(out)])
    assert r.returncode == 3, r.stdout[-2000:] + r.stderr[-2000:]
    recs = C.load_jsonl(str(out / "records.jsonl"))
    assert any(x.get("kind") == "rootlp_incomplete" for x in recs)
    assert not any(x.get("kind") == "stage_done" and x.get("stage") == "rootlp" for x in recs)
    assert RC.load(str(out))[-1]["status"] == "error: SystemExit"
