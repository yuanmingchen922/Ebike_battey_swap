"""R8 fifteen-site study, lane L2 (``notes/siting15_design.md`` sections 3-6 as corrected in
section 12): the ``manhattan15`` family, ``evaluate.site_metrics``, the exactly-k search of
``bilevel.greedy_local_search(force_k=...)`` (exact against the exhaustive enumeration on the toy),
the library-free proxy screen and the k-median / DOT-first warm starts, external cache rows
(``LowerLevelEvaluator.store_external_row``), the driver ``experiments/r8_k15.py`` (toy smoke of
every stage, resume, dry run, the ``fig_map15`` input contract) and its lane writer.  Toy only,
Threads 1, seconds; the heavy probe of one real 48-rider cell runs only with ``R8_HEAVY=1``."""
from __future__ import annotations

import csv
import itertools
import json
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim import baseline as bl  # noqa: E402
from ebike_swap_sim import build_arcs  # noqa: E402
from ebike_swap_sim.evaluate import SITE_METRIC_KEYS, metric_pack, metrics, site_metrics  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r8_k15 as K  # noqa: E402

DEPLOY = os.path.join(os.path.dirname(ROOT), "deploy", "aws")
MAKE_FIGS = os.path.join(os.path.dirname(ROOT), "paper_itsc", "figs", "src", "make_figs.py")
HAS_GUROBI = True
try:
    import gurobipy  # noqa: F401
except ImportError:
    HAS_GUROBI = False


def _toy_scenarios(seeds=(0, 1), union=True):
    out = []
    for s in seeds:
        inst = S.toy_base_instance(s, candidates=K.TOY_CANDIDATES, n_bikes=K.TOY_BIKES, **K.TOY_KW)
        if union:
            inst.options["library_mode"] = "union"
        out.append(inst)
    return out


@pytest.fixture(scope="module")
def toy():
    scen = _toy_scenarios()
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, reposition="open_sites")
    return scen, ev


def _unit():
    return S.TOY_SPEC.Fhat + S.TOY_SPEC.bhat + S.TOY_SPEC.chat


def _exhaustive_k(ev, k):
    lays = BL.enumerate_layouts(ev.candidates, [K.TOY_OPTION], k * _unit(), S.TOY_SPEC, (k,))
    return {l.key(): ev.value(l, "baseline") for l in lays}


# ---------------------------------------------------------------------------
# family, per-site metrics
# ---------------------------------------------------------------------------
def test_manhattan15_family_registered():
    fam = S.MANHATTAN15_FAMILY
    assert fam == "manhattan15" and S.SITING_FAMILIES[fam]["n_bikes"] == 48
    assert S.SITING_FAMILIES[fam]["orders_per_bike_hour"] == 1.25          # 48 x 4 h x 1.25 = 240 orders (C4)
    assert S.family_spec_overrides(fam) == {"max_pair_km": 2.0} and S.SITING_POST[fam] == S.SITING_POST[S.MANHATTAN_DOT_FAMILY]
    assert S.SIZE_MENUS[fam] == S.SIZE_MENUS[S.MANHATTAN_DOT_FAMILY] and S.family_access_D(fam) == S.access_radius_blocks()
    # the older families are untouched
    assert S.SITING_FAMILIES[S.MANHATTAN_DOT_FAMILY]["n_bikes"] == 8 and S.FAMILY_SPEC_OVERRIDES[S.MANHATTAN_DOT_FAMILY] == {"max_pair_km": 2.0}
    for lv, n in zip(S.SCENARIO_LEVELS, (192, 240, 288)):
        assert round(48 * 4.0 * lv) == n


def test_site_metrics_rows_for_a_charge_only_hub(toy):
    """R8 reviewer: a charge-only hub (role C) is a row with swaps 0, so the kWh per site sums to the
    electricity of the schedule for every layout; under the exact ILP (which may charge at the hub) and
    under the r2 follower (which never does)."""
    scen, _ev = toy
    lay = BL.Layout.of([("T2", "SC", 1, 1), ("T4", "C", 0, 1)])
    inst = S.layout_instance(scen[0], lay, S.TOY_SPEC)
    lib = build_arcs(inst, strict=False, library_mode="union")
    scheds = [bl.run_baseline(inst, lib)[0]]
    if HAS_GUROBI:
        from ebike_swap_sim.ilp import solve
        s_ilp, st = solve(inst, lib, aggregate=True, threads=1, time_limit=60.0, params={"Seed": 0})
        assert st["status"] in ("OPTIMAL", "TIME_LIMIT") and s_ilp is not None
        scheds.append(s_ilp)
    for sched in scheds:
        sm = site_metrics(inst, lib, sched)
        m = metrics(inst, lib, sched)
        assert set(sm) == {"T2:SC", "T4:C"} and all(set(v) == set(SITE_METRIC_KEYS) for v in sm.values())
        hub = sm["T4:C"]
        assert hub["swaps"] == 0 and hub["riders_distinct"] == 0 and hub["wait_min_mean"] == 0.0 and hub["rider_depots"] == {}
        assert sum(v["swaps"] for v in sm.values()) == m["n_swaps"]
        assert sum(v["kwh_bought"] for v in sm.values()) == pytest.approx(m["kwh_purchased"])
        assert hub["kwh_bought"] == pytest.approx(hub["charge_steps"] * inst.disc.kwh_per_step)
        assert 0.0 <= hub["charger_busy_share"] <= 1.0


def test_site_metrics_match_the_schedule(toy):
    scen, _ev = toy
    lay = BL.Layout.of([("T2", "SC", 1, 1), ("T3", "SC", 1, 1)])
    inst = S.layout_instance(scen[0], lay, S.TOY_SPEC)
    lib = build_arcs(inst, strict=False)
    sched, flags = bl.run_baseline(inst, lib)
    sm = site_metrics(inst, lib, sched)
    assert set(sm) == {"T2:SC", "T3:SC"} and all(set(v) == set(SITE_METRIC_KEYS) for v in sm.values())
    m = metrics(inst, lib, sched)
    assert sum(v["swaps"] for v in sm.values()) == m["n_swaps"] == flags["n_swaps"] > 0
    for j, v in sm.items():
        assert v["swaps"] == m["swaps_per_facility"].get(j, 0)
        assert 0 <= v["riders_distinct"] <= min(v["swaps"], len(inst.bikes))
        assert 0.0 <= v["charger_busy_share"] <= 1.0 and 0.0 <= v["idle_share"] <= 1.0
        assert 0 <= v["orders_1km_served"] <= v["orders_1km_total"] <= len(inst.orders)
        assert v["kwh_bought"] == pytest.approx(v["charge_steps"] * inst.disc.kwh_per_step)
        assert v["stockout_slots"] == m["stockout_slots"][j]
        assert sum(v["rider_depots"].values()) == v["riders_distinct"]
    assert sum(v["kwh_bought"] for v in sm.values()) == pytest.approx(m["kwh_purchased"])
    # the pack carries the same table; the union library answers identically
    assert metric_pack(inst, lib, sched)["per_site"] == sm
    lib_u = build_arcs(inst, strict=False, library_mode="union")
    sched_u, _ = bl.run_baseline(inst, lib_u)
    assert site_metrics(inst, lib_u, sched_u) == sm
    # the unservable-order test reads the id index on both library kinds (value-identical)
    assert C.unservable_orders(inst, lib) == C.unservable_orders(inst, lib_u) == [o.id for o in inst.orders if not lib.delivery_arcs(o.id)]
    inst2 = S.layout_instance(scen[0], BL.Layout.of([("T1", "SC", 1, 1)]), S.TOY_SPEC)
    for mode in ({}, {"library_mode": "union"}):
        l2 = build_arcs(inst2, strict=False, reachable_pruning=True, tau_max=1, **mode)
        assert C.unservable_orders(inst2, l2) == [o.id for o in inst2.orders if not l2.delivery_arcs(o.id)]


# ---------------------------------------------------------------------------
# exactly-k search, proxy screen, warm starts
# ---------------------------------------------------------------------------
def test_service_gate_per_policy():
    assert BL.service_gate("ilp") == 0.5 and BL.service_gate("baseline") == 0.0 and BL.service_gate("selfish") == 0.0
    assert BL.service_gate("baseline", 0.3) == 0.3 and BL.SERVICE_GATE["ilp"] == 0.5


@pytest.mark.parametrize("k", [1, 2, 3])
def test_force_k_is_exact_against_the_exhaustive_enumeration(toy, k):
    _scen, ev = toy
    vals = _exhaustive_k(ev, k)
    best_v = min(vals.values())
    g = BL.greedy_local_search(ev, ev.candidates, k * _unit(), size_menu={"SC": [(1, 1)]}, roles=("SC",), screen=False,
                               moves=("add", "drop", "swap"), max_passes=5, min_served_share=None, policy="baseline", force_k=k)
    r = g["per_budget"][k * _unit()]
    assert r["status"] == "OK" and r["layout"].n_open == k and r["value"] == pytest.approx(best_v, abs=1e-6)
    assert g["force_k"] == k and g["min_served_share"] == 0.0
    assert set(g["path_k"]) == set(range(1, k + 1)) and g["path_k"][k][1] >= r["value"] - 1e-9
    # add / drop are disabled at fixed k: every priced layout of the local search has k sites
    for h in r["history"]:
        if h.get("layout_key"):
            assert BL.Layout.from_key(h["layout_key"]).n_open == k
    # the forward path never stops early: every accepted step has one more site
    acc = [h for h in g["history"] if h["step"] == "forward_accept"]
    assert [h["k"] for h in acc] == list(range(2, k + 1)) if k > 1 else acc == []


def test_force_k_accepts_a_rising_V_to_reach_k(toy):
    """The toy's V(k) falls, so build a case where it must rise: a start layout that is the best
    2-site layout and force_k = 3 with every third site making V worse is impossible to assert
    generally; instead check the mechanism on the recorded path: V(k) is the accepted (lowest V)
    addition of each step even when it is above V(k - 1)."""
    _scen, ev = toy
    g = BL.greedy_local_search(ev, ev.candidates, 4 * _unit(), size_menu={"SC": [(1, 1)]}, roles=("SC",), screen=False,
                               moves=("swap",), max_passes=1, min_served_share=None, policy="baseline", force_k=4, local_search=False)
    r = g["per_budget"][4 * _unit()]
    assert r["layout"] is not None and r["layout"].n_open == 4
    for kk in range(2, 5):
        step = [h for h in g["history"] if h["step"] == "forward_candidate" and BL.Layout.from_key(h["layout_key"]).n_open == kk
                and h["usable"]]
        assert g["path_k"][kk][1] == pytest.approx(min(h["V"] for h in step))


def test_proxy_screen_kmedian_and_warm_starts(toy):
    scen, ev = toy
    px = BL.ProxyScreen(ev.candidates, scen, ev.p, S.TOY_SPEC)
    assert px.D.shape == (sum(len(i.orders) for i in scen), 4) and px.w.sum() == pytest.approx(sum(ev.p[s] * sum(o.P for o in i.orders) for s, i in enumerate(scen)))
    one = BL.Layout.of([("T2", "SC", 1, 1)])
    two = one.add(("T3", "SC", 1, 1))
    assert px.demand_cost(["T2", "T3"]) <= px.demand_cost(["T2"]) and px.score(BL.Layout()) == BL.INF
    assert px.score(two) == pytest.approx(px.demand_cost(["T2", "T3"]) + two.allocated_cost(S.TOY_SPEC))
    assert px.score(BL.Layout.of([("T2", "C", 0, 1)])) == BL.INF          # a hub is not swap-capable
    ranked = px.rank([one, two], 1)
    assert len(ranked) == 1 and ranked[0][1].key() == two.key()
    # k-median = the exact minimum of the proxy demand cost over every k-subset (MIP or greedy)
    for k in (1, 2, 3):
        lay, info = BL.k_median_layout(px, k, K.TOY_OPTION, time_limit=10.0)
        assert lay.n_open == k and info["method"] in ("mip", "greedy")
        best = min(px.demand_cost(sub) for sub in itertools.combinations(px.ids, k))
        if info["method"] == "mip":
            assert px.demand_cost(lay.locations()) == pytest.approx(best, abs=1e-6)
        else:
            assert px.demand_cost(lay.locations()) >= best - 1e-9
    # the proxy-screened exactly-k search with the study's screen parameters (3 priced per step, swaps to
    # the 3 nearest + 5 proxy-best closed candidates) still reaches the exhaustive optimum on the toy
    for k in (1, 2, 3):
        vals = _exhaustive_k(ev, k)
        g = BL.greedy_local_search(ev, ev.candidates, k * _unit(), size_menu={"SC": [(1, 1)]}, roles=("SC",), screen=px, k_screen=3,
                                   moves=("swap",), max_passes=5, min_served_share=None, policy="baseline", force_k=k,
                                   swap_neighbourhood={"nearest": 3, "proxy_best": 5})
        r = g["per_budget"][k * _unit()]
        assert r["value"] == pytest.approx(min(vals.values()), abs=1e-6), (k, r["layout"].key())
        priced = {h["layout_key"] for h in g["history"] if h["step"] in ("singleton", "forward_candidate")}
        assert len(priced) <= 3 * k                                               # the screen prices at most k_screen per step
    # restricted swap neighbourhood: an open site moves only to its nearest closed candidate or the proxy-best one
    lay3 = BL.Layout.of([("T1", "SC", 1, 1), ("T4", "SC", 1, 1)])
    g = BL.greedy_local_search(ev, ev.candidates, 2 * _unit(), size_menu={"SC": [(1, 1)]}, roles=("SC",), screen=px, k_screen=10,
                               moves=("swap",), max_passes=1, min_served_share=None, policy="baseline", force_k=2, start=lay3,
                               swap_neighbourhood={"nearest": 1, "proxy_best": 0})
    tried = [h["layout_key"] for h in g["per_budget"][2 * _unit()]["history"] if h["step"].startswith("ls_pass")]
    assert tried and set(tried) <= {"T2:SC:B1:C1|T4:SC:B1:C1", "T1:SC:B1:C1|T3:SC:B1:C1"}
    # warm starts: DOT-first needs programme sites; top_sites keeps the best two by weight
    dw = BL.demand_weights(ev.candidates, scen, 1, ev.p)
    assert BL.dot_first_layout(ev.candidates, 2, dw, K.TOY_OPTION) is None
    cands = [S.Candidate.from_record(c.to_record()) for c in ev.candidates]
    cands[3].dot_type = "pilot"
    df = BL.dot_first_layout(cands, 2, dw, K.TOY_OPTION)
    assert df.n_open == 2 and "T4" in df.locations()
    assert BL.top_sites(BL.Layout.from_key("T1:SC:B1:C1|T2:SC:B1:C1|T3:SC:B1:C1"), dw, 2).n_open == 2
    # the old budget mode is untouched by the new arguments (defaults): same call as before
    g0 = BL.greedy_local_search(ev, ev.candidates, 2 * _unit(), size_menu={"SC": [(1, 1)]}, roles=("SC",), screen=False,
                                policy="baseline")
    assert g0["force_k"] is None and g0["min_served_share"] == 0.5


def test_restart_from_an_unpriced_start_is_ok_on_the_offline_evaluator(toy, tmp_path):
    """R8 reviewer (major): the start layout of a restart was priced without a prefetch, which on the
    driver's OfflineEvaluator is an ERROR row (the cell is never solved in the parent), so every restart
    from a layout silently fell back to the singleton search from empty.  Now the start is prefetched."""
    scen, ev_real = toy
    off = K.OfflineEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, reposition="open_sites", cache_dir=str(tmp_path / "c"))
    n_pricer = {"calls": 0}

    def pricer(lays):                      # the pool stand-in: single-scenario rows stored through store_external_row
        n_pricer["calls"] += 1
        for lay, s in off.missing_cells(lays):
            ev1 = BL.LowerLevelEvaluator([scen[s]], S.TOY_SPEC, probabilities=[1.0], time_limit=30.0, threads=1, reposition="open_sites")
            row = ev1.evaluate_scenario(lay, 0, "baseline")
            off.store_external_row(lay, s, "baseline", row, row.pop("_portable", None))
    off.pricer = pricer
    start = BL.Layout.of([("T1", "SC", 1, 1), ("T4", "SC", 1, 1)])
    assert off.missing_cells([start])                                   # not priced before the search
    g = BL.greedy_local_search(off, ev_real.candidates, 2 * _unit(), start=start, force_k=2, size_menu={"SC": [(1, 1)]},
                               roles=("SC",), k_screen=2, max_passes=1, moves=("swap",), local_search=True,
                               min_served_share=None, policy="baseline")
    first = g["history"][0]
    assert first["step"] == "start" and first["layout_key"] == start.key() and first["status"] == "OK", first
    assert g["class_counts"].get("ERROR", 0) == 0 and n_pricer["calls"] >= 1
    r = g["per_budget"][2 * _unit()]
    assert r["layout"] is not None and r["layout"].n_open == 2 and r["value"] <= ev_real.value(start, "baseline") + 1e-9


def test_store_external_row_matches_the_single_scenario_key(toy, tmp_path):
    scen, _ev = toy
    cache = str(tmp_path / "cache")
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, reposition="open_sites", cache_dir=cache)
    lay = BL.Layout.of([("T2", "SC", 1, 1), ("T3", "SC", 1, 1)])
    # a worker's single-scenario evaluator of scenario 1 computes the SAME key as the parent for s = 1
    ev1 = BL.LowerLevelEvaluator([scen[1]], S.TOY_SPEC, probabilities=[1.0], time_limit=30.0, threads=1, reposition="open_sites")
    assert ev1.cache_key(lay, 0, "baseline") == ev.cache_key(lay, 1, "baseline")
    row = ev1.evaluate_scenario(lay, 0, "baseline")
    port = row.pop("_portable")
    stored = ev.store_external_row(lay, 1, "baseline", row, port)
    assert stored["scenario"] == 1 and stored["p"] == ev.p[1] and os.path.exists(stored["schedule_path"])
    hit = ev.evaluate_scenario(lay, 1, "baseline")
    assert hit["cache_hit"] and hit["total"] == pytest.approx(row["total"]) and ev.n_baseline_runs == 0
    assert BL.materialise_schedule(ev.load_portable(hit), *ev.layout_pair(lay, 1)) is not None
    with pytest.raises(ValueError):
        ev.store_external_row(lay, 0, "baseline", {**row}, port)          # the row's key belongs to scenario 1
    err = ev.store_external_row(lay.drop("T3"), 0, "baseline", {"status": BL.ERROR, "error": "x"}, None)
    assert err["status"] == BL.ERROR and err["key"] not in ev.cache and ev.n_errors == 1


# ---------------------------------------------------------------------------
# the driver: toy smoke of every stage, resume, dry run, lanes
# ---------------------------------------------------------------------------
def _run(args, timeout=600, env=None):
    e = dict(os.environ, PYTHONPATH=".")
    e.update(env or {})
    return subprocess.run([sys.executable, "experiments/r8_k15.py"] + args, cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout, env=e)


def test_cli_smoke_all_stages_resume_and_contract(tmp_path):
    out = tmp_path / "smoke"
    t0 = time.perf_counter()
    r = _run(["--smoke", "--stage", "all", "--out-dir", str(out)])
    wall = time.perf_counter() - t0
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert wall < 120.0
    for f in ("records.jsonl", "cost.jsonl", "dryrun.json", "search_summary.json", "final_summary.json", "layout.json",
              "site_stats.csv", "RESULTS.md", "candidates.csv", "wall_time.json"):
        assert (out / f).exists(), f
    # C3: the scenario instances are saved once (JSON by Instance.save + a pickle twin), union mode on
    inst_dir = out / "instances"
    names = sorted(p.name for p in inst_dir.glob("*.json"))
    assert names == ["in_s00.json", "in_s01.json", "manifest.json", "out_s00.json", "out_s01.json", "val_s00.json", "val_s01.json"]
    d = json.loads((inst_dir / "in_s00.json").read_text())
    assert d["options"]["library_mode"] == "union" and d["routes"] and d["meta"]["r8"]["kind"] == "in"
    man = json.loads((inst_dir / "manifest.json").read_text())
    assert set(man["files"]) == {n for n in names if n != "manifest.json"}
    recs = C.load_jsonl(str(out / "records.jsonl"))
    kinds = {x.get("kind") for x in recs}
    for k in ("instances_plan", "instance_built", "dryrun", "search_plan", "restart_result", "free_result", "search_result",
              "final_plan", "final_result", "price15", "cell_batch", "stage_done", "kmedian"):
        assert k in kinds, k
    assert {x["stage"] for x in recs if x.get("kind") == "stage_done"} >= {"instances", "dryrun", "search", "final"}
    # every cell went through the pool (worker pid, wall and RSS on the cached rows), never the parent
    rows = C.load_jsonl(str(out / "cache" / "index.jsonl"))
    assert rows and all(r.get("cell_wall_s") is not None and r.get("worker_rss_gb") is not None for r in rows)
    assert all(r["policy"] in ("baseline", "ilp") and r["reposition"] == "open_sites" for r in rows)
    assert all(r.get("per_site") for r in rows if r["policy"] == "baseline" and r.get("feasible"))
    # gates of the dry run
    dr = json.loads((out / "dryrun.json").read_text())
    assert set(dr["gates"]) == {"cell_s", "rss_gb", "median_site_swaps"} and dr["gates"]["cell_s"]["ok"] and dr["gates"]["rss_gb"]["ok"]
    assert len(dr["cell_wall_s"]) == 2 and isinstance(dr["escalate"], bool)
    # the search: exactly k sites, the warm starts and the V(k) path to k_max
    ss = json.loads((out / "search_summary.json").read_text())
    assert ss["k"] == 2 and BL.Layout.from_key(ss["best"]["layout_key"]).n_open == 2
    assert set(ss["warm"]) == {"CSCD2", "CSTC2", "CSAV2", "kmedian2", "dotfirst2"} and ss["warm"]["dotfirst2"]["layout_key"] is None
    assert {"m2_incumbent", "CSCD_best2", "CSAV_best2", "empty"} <= set(ss["restarts"])
    # every restart that starts from a layout priced it through the pool: the start step is OK, never ERROR
    for n, rr in ss["restarts"].items():                 # 'empty' records its best singleton as the start
        assert rr["start_status"] == "OK", (n, rr)
    starts = [x for x in recs if x.get("kind") == "search_step" and x.get("step") == "start" and x.get("restart") != "empty"]
    assert starts and all(x["status"] == "OK" for x in starts)
    assert ss["vk_missing"] == []
    assert set(dr["reference_layouts"]) == {"toy_m1", "toy_m2", "toy_m2:T1", "toy_m2:T4"}
    assert all(v["status"] == "OK" and v["V"] is not None for v in dr["reference_layouts"].values())
    # one in-memory cache for the three evaluators: no key is priced twice within the process
    keys = [r["key"] for r in rows]
    assert len(keys) == len(set(keys)), f"{len(keys) - len(set(keys))} duplicated cache rows"
    assert set(ss["vk_layouts"]) == {"1", "2", "3"} and all(v for v in ss["vk_layouts"].values())
    assert BL.Layout.from_key(ss["vk_layouts"]["3"]).n_open == 3 and ss["free"]["status"] == "OK"
    # exactness on the toy: the best found equals the exhaustive optimum at k = 2 under the rule follower
    scen = _toy_scenarios()
    ev = BL.LowerLevelEvaluator(scen, S.TOY_SPEC, time_limit=30.0, threads=1, reposition="open_sites")
    assert ss["best"]["V"] == pytest.approx(min(_exhaustive_k(ev, 2).values()), abs=1e-6)
    # the final table: in-sample + held-out, V(k), remove-one, regret with paired CIs
    fs = json.loads((out / "final_summary.json").read_text())
    assert fs["best"]["complete"] and fs["best_out"]["complete"] and fs["best"]["V"] == pytest.approx(ss["best"]["V"])
    assert {r["k"] for r in fs["vk"]} == {1, 2, 3} and all(r["V"] is not None for r in fs["vk"])
    assert len(fs["remove_one"]) == 2 and all(v["complete"] for v in fs["remove_one"].values())
    assert fs["regret_in"]["best"]["regret"] == 0.0 and all("regret_ci" in v for v in fs["regret_in"].values())
    assert fs["best"]["V_ci95"] is not None and fs["best"]["ci"]["df"] == 1
    for l, t in fs["site_table"].items():
        assert t["marginal_usd"] == pytest.approx(fs["remove_one"][f"remove:{l}"]["V"] - fs["best"]["V"])
        assert t["n_scenarios"] == 2 and t["swaps_mean"] >= 0
    # the fig_map15 input contract (design 6.1)
    lj = json.loads((out / "layout.json").read_text())
    assert lj["schema"] == "map15.layout/1" and lj["demo"] is False and lj["policy"] == "baseline" and lj["variant"] == "r2"
    assert len(lj["sites"]) == 2 and all(set(s) == {"id", "role", "B", "C"} for s in lj["sites"])
    assert lj["n_bikes"] == K.TOY_BIKES and lj["n_orders"] == 8 and lj["n_scenarios"] == 2 and lj["V"] == pytest.approx(fs["best"]["V"])
    assert lj["investment_usd"] == pytest.approx(2 * _unit()) and os.path.exists(lj["candidates_csv"])
    with open(out / "site_stats.csv", encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        assert tuple(rd.fieldnames) == K.SITE_STATS_COLUMNS
        stats = list(rd)
    assert [s["id"] for s in stats] == [s["id"] for s in lj["sites"]]
    assert all(float(s["swaps_mean"]) >= 0 and s["n_scenarios"] == "2" for s in stats)
    if os.path.exists(MAKE_FIGS):
        txt = open(MAKE_FIGS, encoding="utf-8").read()
        for col in K.SITE_STATS_COLUMNS:
            assert f'"{col}"' in txt                                    # every column is in the L3 contract
        assert '"map15.layout/1"' in txt
    # the ILP check (C6): ratio rows with gaps, never a rank statistic
    if HAS_GUROBI:
        v = json.loads((out / "validate.json").read_text())
        assert v["n_cells"] == 4 and v["ratio_median"] is not None and "rank" not in v["statement"].split("no ")[0]
        for row in v["rows"]:
            assert row["ilp_gap"] is not None and row["ratio_rule_over_incumbent"] is not None
            if str(row["ilp_status"]) == "OPTIMAL":
                assert row["ratio_rule_over_incumbent"] >= 1.0 - 1e-9
        assert "greedy2" in v["rule_values"] and len(v["rule_values"]) >= 2        # layouts deduplicated by key
    res = (out / "RESULTS.md").read_text()
    for head in ("## Dry run (gates)", "## Search", "## Final table", "## V(k) curve", "## Per-site statistics"):
        assert head in res
    # resume: a second invocation skips every finished stage and re-writes the report only
    n_rows = len(rows)
    r2 = _run(["--smoke", "--stage", "all", "--out-dir", str(out)])
    assert r2.returncode == 0, r2.stderr[-2000:]
    assert r2.stdout.count("stage_skipped") >= 4 and len(C.load_jsonl(str(out / "cache" / "index.jsonl"))) == n_rows
    # the final stage alone on the cache: no new cell, identical values
    r3 = _run(["--smoke", "--stage", "final", "--redo", "--out-dir", str(out)])
    assert r3.returncode == 0, r3.stderr[-2000:]
    assert len(C.load_jsonl(str(out / "cache" / "index.jsonl"))) == n_rows
    assert json.loads((out / "final_summary.json").read_text())["best"]["V"] == pytest.approx(fs["best"]["V"])
    # dry run: plans only, no cell
    r4 = _run(["--smoke", "--stage", "dryrun,search,final", "--dry-run", "--out-dir", str(tmp_path / "dry")])
    assert r4.returncode != 0 and "instances" in (r4.stdout + r4.stderr)          # needs the instances first
    r5 = _run(["--smoke", "--stage", "instances", "--out-dir", str(tmp_path / "dry")])
    r6 = _run(["--smoke", "--stage", "dryrun,search,final", "--dry-run", "--out-dir", str(tmp_path / "dry")])
    assert r5.returncode == 0 and r6.returncode == 0, r6.stderr[-2000:]
    assert not (tmp_path / "dry" / "cache" / "index.jsonl").exists()
    cost = C.load_jsonl(str(out / "cost.jsonl"))
    assert cost and all(c["script"] == "r8_k15.py" for c in cost) and all("report" not in c["stage"] or "," in c["stage"] for c in cost)


def test_write_lanes_and_deploy_format(tmp_path):
    lanes_dir = tmp_path / "lanes"
    r = _run(["--write-lanes", "--lanes-dir", str(lanes_dir)])
    assert r.returncode == 0, r.stderr[-2000:]
    txt = (lanes_dir / "lanes.txt").read_text()
    rows = [ln.split("\t") for ln in txt.splitlines() if ln and not ln.startswith("#")]
    meta = json.loads((lanes_dir / "lanes.json").read_text())
    names = [r[0] for r in rows]
    assert names == ["k15_instances", "k15_dryrun", "k15_validate", "k15_search", "k15_final", "k15_report"]
    # chain: search depends on dryrun only (the optional ILP check must not block the study), the rest is a line
    assert [r[2] for r in rows] == ["-", "k15_instances", "k15_dryrun", "k15_dryrun", "k15_search", "k15_final"]
    assert meta["usable_threads"] == 12 and meta["max_rss_gb"] == 110.0
    for name, thr, after, cmd in rows:
        assert thr.isdigit() and 1 <= int(thr) <= 12 and len(name) <= 40
        assert "r8_k15.py" in cmd and "--max-rss-gb 110" in cmd and "R7_BATCH=k15" in cmd and "--family manhattan15" in cmd
        toks = cmd.split()
        stage = toks[toks.index("--stage") + 1]
        assert stage == name.split("_", 1)[1]
        mx = int(toks[toks.index("--max-threads") + 1])
        assert mx == int(thr)
        if stage in ("instances", "dryrun", "search", "final"):
            assert int(toks[toks.index("--workers") + 1]) == int(thr) == 8
        if stage == "validate":
            vw, vt = int(toks[toks.index("--validate-workers") + 1]), int(toks[toks.index("--validate-threads") + 1])
            assert vw * vt == int(thr) == 12
    assert "critic C1" in txt and "escalate" in txt and "--max-rss-gb guards the parent RSS plus workers" in txt
    sh = os.path.join(DEPLOY, "run_lanes.sh")
    if os.path.exists(sh):
        p = subprocess.run(["bash", sh, "start", str(lanes_dir / "lanes.txt"), "--max-threads", "12", "--dry-run"],
                           capture_output=True, text=True, env=dict(os.environ, LANES_DIR=str(tmp_path / "ld")), timeout=120)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
        assert "dry run: nothing started" in p.stdout and "k15_instances" in p.stdout
    # the thread check of main: a pool stage with more workers than the budget is refused
    r2 = _run(["--smoke", "--stage", "dryrun", "--workers", "2", "--max-threads", "1", "--out-dir", str(tmp_path / "x")])
    assert r2.returncode != 0 and "exceed" in (r2.stdout + r2.stderr)


@pytest.mark.skipif(os.environ.get("R8_HEAVY") != "1", reason="set R8_HEAVY=1: one manhattan15 scenario at 48 riders (minutes)")
def test_heavy_one_real_cell_at_48_riders(tmp_path):
    """Builds in-sample scenario 0 of ``manhattan15`` (48 riders, 192 orders at level 1.0) through the
    instance worker, then prices CSCD-15 on it through the cell worker; logs the timings to
    ``outputs/r8_k15_probe/one_cell.json`` and checks the dry-run gates on this one cell."""
    args = K.parse_args(["--out-dir", str(tmp_path / "probe"), "--workers", "1"])
    run = K.Run(args)
    ctx = K.Ctx(run)
    job = [j for j in K.instance_jobs(ctx, ("in",)) if j["s"] == 0][0]
    res = K._instance_job(job)
    assert res["n_bikes"] == 48 and res["n_orders"] == 192
    ctx.attach(("in",)) if False else None
    scen = [K._load_instance(res["path"], light=True)]
    spec = S.spec_from_instance(scen[0], **S.family_spec_overrides(ctx.family))
    weights = BL.demand_weights(ctx.cands, scen, ctx.D, [1.0])
    lay = BL.rule_layout("CSCD", ctx.cands, 15 * BL.Layout.of([(ctx.ids[0],) + K.UNIT_OPTION]).investment(spec), spec, weights,
                         role="SC", base_size=(3, 2), k=15, max_B=3, max_C=2)
    cfg = {"instance_dir": run.instance_dir, "spec": spec.to_dict(), "pruning": ctx.pruning, "params": dict(C.ILP_PARAMS_R3),
           "threads": 1, "time_limit": 300.0, "aggregate": False, "relaxed_targets": True, "keep": 1, "radius_blocks": 7}
    K._worker_init(cfg)
    cell = K._cell_job({"layout": lay.key(), "kind": "in", "s": 0, "policy": "baseline", "site_metrics": True})
    row = cell["row"]
    rec = {"instance_build_s": res["build_s"], "n_nodes": res["n_nodes"], "n_routes": res["n_routes"], "size_mb": res["size_mb"],
           "cell_wall_s": cell["cell_wall_s"], "worker_rss_gb": cell["worker_rss_gb"], "n_arcs": row.get("n_arcs"),
           "runtime_s": row.get("runtime_s"), "total": row.get("total"), "served": (row.get("metrics") or {}).get("served_share"),
           "n_swaps": (row.get("metrics") or {}).get("n_swaps"), "swaps_per_site": {k: v["swaps"] for k, v in (row.get("per_site") or {}).items()},
           "status": row.get("status"), "error": row.get("error")}
    os.makedirs(os.path.join(ROOT, "outputs", "r8_k15_probe"), exist_ok=True)
    with open(os.path.join(ROOT, "outputs", "r8_k15_probe", "one_cell.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)
    assert row["status"] == "POLICY", rec
    assert cell["cell_wall_s"] <= K.GATES["cell_s"] and cell["worker_rss_gb"] <= K.GATES["rss_gb"]   # laptop: 3 s, 1.1 GB
