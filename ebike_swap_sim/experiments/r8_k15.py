"""R8 fifteen-site study driver (``notes/siting15_design.md``, section 12 'Critic corrections' binding):
exactly ``k`` (15) battery-swap sites in Manhattan south of 110th St at a city-scale fleet (family
``manhattan15``: 48 riders, 8 per entry depot; 192 / 240 / 288 orders per evening at the three demand
levels, critic C4: the order count follows from ``n_bikes``), the rule-based rider module as the lower
level (``baseline.run_baseline`` variant r2, every schedule certified by ``evaluate.check``), the
exactly-k search of ``bilevel.greedy_local_search(force_k=...)`` with the library-free proxy screen
(``bilevel.ProxyScreen``), warm starts (CSCD-k, CSAV-k, k-median, DOT-first) and comparison rows, the
V(k) curve, the remove-one pass and the per-site statistics of the map (``paper_itsc/figs/src/
make_figs.py fig_map15``, input contract of design section 6.1).

Binding constraints of the critic that this driver implements:

* **C1** every lower-level cell runs in a ``multiprocessing`` PROCESS pool (never a thread pool: the
  rule follower is pure Python and holds the GIL).  Workers never receive an arc library: each
  worker loads the saved scenario instance from disk on first use (fork or spawn, no pickling of
  instances or libraries), builds the layout instance and its union library itself, runs the rule
  follower, certifies the schedule, measures the per-site statistics and returns one small dict
  plus the portable schedule; the parent stores the row under its own cache key
  (``LowerLevelEvaluator.store_external_row``; the worker's key must match).
* **C2** the union (bike-class) library of lane L1 (``library_mode = 'union'`` on every saved
  scenario instance; reachability = one bitmask sweep).
* **C3** the 12 in-sample + 12 held-out scenario instances are built ONCE (stage ``instances``, one
  process per scenario, resumable, route library included) and saved with ``Instance.save``.
* **C5** every cell is priced on the open-sites tier (``reposition='open_sites'``); the
  all-candidates template tier is never built.  Gates of the dry run: cell <= 45 s and worker RSS
  <= 4 GB per process, median open site >= 3 swaps per evening (else the ``escalate`` flag).
* **C6** the exact-ILP check (stage ``validate``, 16 riders / 80 orders / 5-site layouts) is reported
  as a rule / incumbent RATIO with the MIP gap of every cell, never as a rank statistic.

Stages (``--stage a,b`` or ``all``; every stage appends to ``records.jsonl`` and resumes from the
evaluator cache ``cache/index.jsonl`` + ``cache/schedules/``):

``instances``  build and save the in-sample and held-out scenario instances at ``n_bikes`` (48)
               into ``<out-dir>/instances/`` (``in_sNN.json`` / ``out_sNN.json`` + ``manifest.json``).
``dryrun``     one layout (CSCD-k) on every in-sample scenario with the gates -> ``dryrun.json``.
``validate``   optional: 16 riders / 80 orders / 5-site layouts (greedy-5, CSCD-5, CSAV-5) x 3
               scenarios, the exact aggregated ILP at 1,800 s / Threads 3 against the rule follower
               -> ``validate.json`` (ratio rows with gaps).
``search``     warm starts, forward selection from the m = 2 incumbent / the rule warm starts' best
               two sites / empty, swap local search at fixed k, size polish, the '15 units free'
               comparison, the V(k) path to ``--k-max`` -> ``search_summary.json``.
``final``      the best and comparison layouts on all in-sample and held-out scenarios, V(k) for
               ``--vk`` re-priced, the remove-one pass, per-site statistics -> ``layout.json`` +
               ``site_stats.csv`` (the ``fig_map15`` contract), ``final_summary.json``.
``report``     ``RESULTS.md`` with the tables the paper needs.

Modes: ``--smoke`` (the toy of ``r7_siting.py``: four candidates, k = 2, two scenarios, seconds),
``--dry-run`` (plans and counts only), ``--write-lanes`` (deploy-compatible lanes
``outputs/cloud_lanes_k15/lanes.txt``: instances -> dryrun -> validate -> search -> final -> report
for ``deploy/aws/run_lanes.sh``, thread budget 12, ``--max-rss-gb 110``).  Every invocation appends a
row to ``cost.jsonl`` (``experiments/r7_cost.py``; the laptop ``report`` stage is not billed).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r8_k15.py --smoke --stage all --out-dir outputs/r8_k15_smoke
    python3 experiments/r8_k15.py --stage instances --workers 8 --out-dir outputs/r8_k15
    python3 experiments/r8_k15.py --write-lanes

English only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import resource
import statistics
import sys
import time
import warnings
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import costs as cm  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim.or_instance import Instance  # noqa: E402
from experiments import common as C  # noqa: E402
from experiments import r7_cost as RC  # noqa: E402

INF = BL.INF
STAGES = ("instances", "dryrun", "validate", "search", "final", "report")
#: stages that run on every invocation (never skipped by a stage_done record)
ALWAYS_RUN = ("report",)
OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "r8_k15")
LANES_ROOT = os.path.join(C.OUTPUT_ROOT, "cloud_lanes_k15")
BUDGET_UNIT = 50_000.0 + 3 * 450.0 + 2 * 400.0          # one SC:B3:C2 unit, 52,150 USD (E9 convention)
UNIT_OPTION: Tuple[str, int, int] = ("SC", 3, 2)
TOY_OPTION: Tuple[str, int, int] = ("SC", 1, 1)
TOY_CANDIDATES = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))
TOY_MENU = {"SC": [(1, 1), (2, 1)]}
#: toy knobs of the smoke (``sites_nyc.toy_base_instance``): three riders at q0 = 5 of 6, eight orders, a
#: 2 h window, so that the rule follower serves orders and swaps at the open sites (layouts differ)
TOY_KW = {"q0": 5, "n_orders": 8, "H": 24}
TOY_BIKES = 3
#: gates of the dry run (design 12.1 C2 / C5 and 12.2)
GATES = {"cell_s": 45.0, "rss_gb": 4.0, "median_site_swaps": 3.0}
#: production incumbents of the r7 study (8 riders, exact follower), re-priced at the new fleet (12.2)
REF_LAYOUTS = {"prod_m1": "D23:SC:B3:C2", "prod_m2": "D07:SC:B3:C2|D45:SC:B3:C2"}
#: 1 km of grid distance in 150 m blocks (per-site 'orders within 1 km')
RADIUS_1KM_BLOCKS = 7
#: hours of the lane plan (design 12.4, r7i.4xlarge on-demand)
LANE_HOURS = {"instances": 0.7, "dryrun": 0.5, "validate": 1.5, "search": 2.2, "final": 1.0, "report": 0.1}
SCHEMA15 = "map15.layout/1"
SITE_STATS_COLUMNS = ("id", "swaps_mean", "swaps_lo", "swaps_hi", "orders_1km_served", "orders_1km_total",
                      "riders_distinct", "charger_busy_share", "idle_share", "kwh_bought", "wait_min_mean",
                      "stockout_slots", "marginal_usd", "marginal_lo", "marginal_hi", "n_scenarios")


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def rss_gb() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return ru / (1024.0 ** 3) if sys.platform == "darwin" else ru / (1024.0 ** 2)


def _md5(obj: Any) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _f(x: Any) -> Optional[float]:
    return None if x is None or x == INF else float(x)


def _write_json(path: str, obj: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(obj), fh, indent=1)
    os.replace(tmp, path)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


class Run:
    """Output directory, ``records.jsonl`` and the cache directory of one configuration."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        root = OUT_ROOT + "_smoke" if args.smoke else OUT_ROOT
        self.dir = C.ensure_dir(os.path.abspath(args.out_dir) if args.out_dir else root)
        self.records = os.path.join(self.dir, "records.jsonl")
        self.cache = os.path.join(self.dir, "cache")
        self.instance_dir = C.ensure_dir(os.path.join(self.dir, "instances"))
        self.stage = "-"
        self.config_md5: Optional[str] = None

    def emit(self, rec: Dict[str, Any], echo: bool = False) -> None:
        rec = {"stage": self.stage, **rec}
        if self.config_md5 is not None and "config_md5" not in rec:
            rec["config_md5"] = self.config_md5
        C.append_jsonl(self.records, C.jsonable(rec))
        if echo:
            keys = ("kind", "tag", "name", "layout_key", "V", "served_share", "status", "n_cells", "wall_s", "reason",
                    "escalate", "k", "start_status")
            print(json.dumps({k: C.jsonable(rec.get(k)) for k in keys if k in rec}), flush=True)

    def load(self) -> List[Dict[str, Any]]:
        return C.load_jsonl(self.records) if os.path.exists(self.records) else []

    def rss_guard(self, where: str, pool_gb: float = 0.0) -> bool:
        """``--max-rss-gb`` as a machine budget: the parent's RSS plus ``pool_gb``, the estimate of the
        worker processes (workers x the largest worker RSS of the last cell batch; R8 fix: the guard read
        the parent alone before)."""
        lim = self.args.max_rss_gb
        if lim is None:
            return True
        r = rss_gb()
        if r + float(pool_gb) > float(lim):
            self.emit({"kind": "aborted", "reason": f"RSS {r:.1f} GB parent + {pool_gb:.1f} GB workers (workers x last max worker RSS) "
                                                    f"> --max-rss-gb {lim} before {where}", "rss_gb": r, "pool_gb": float(pool_gb)}, echo=True)
            return False
        return True


def stage_done(records: Sequence[Dict[str, Any]], stage: str, md5: str) -> bool:
    return any(r.get("kind") == "stage_done" and r.get("stage") == stage and r.get("config_md5") == md5 for r in records)


# ---------------------------------------------------------------------------
# worker side (process pool, critic C1): instances from disk, single-scenario evaluators
# ---------------------------------------------------------------------------
_W: Dict[str, Any] = {"cfg": None, "ev": OrderedDict()}


class _SharedRoutes(dict):
    """Route library that ``copy.deepcopy`` shares instead of copying (routes are immutable data;
    ``layout_instance`` and ``relax_end_targets`` deep-copy the base instance per cell)."""

    def __deepcopy__(self, memo: Any) -> "_SharedRoutes":
        return self


def _worker_init(cfg: Dict[str, Any]) -> None:
    _W["cfg"] = cfg
    _W["ev"] = OrderedDict()
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[var] = str(max(1, int(cfg.get("threads", 1))))
    warnings.simplefilter("ignore")


def _instance_path(instance_dir: str, kind: str, s: int) -> str:
    return os.path.join(instance_dir, f"{kind}_s{int(s):02d}.json")


def _load_instance(path: str, light: bool = False) -> Instance:
    """The saved scenario instance (``Instance.save`` JSON, critic C3).  ``light`` strips the
    routes (parent: keys and the cache only).  A worker prefers the pickle twin written next to
    the JSON by the ``instances`` stage (same object, loads in a fraction of the JSON parse)."""
    pkl = path[:-5] + ".pkl" if path.endswith(".json") else path + ".pkl"
    if not light and os.path.exists(pkl) and os.path.getmtime(pkl) >= os.path.getmtime(path):
        import pickle
        with open(pkl, "rb") as fh:
            inst = pickle.load(fh)
        inst.routes = _SharedRoutes(inst.routes)
        return inst
    with open(path, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    if light:
        d["routes"] = []
    inst = Instance.from_dict(d)
    if not light:
        inst.routes = _SharedRoutes(inst.routes)
    return inst


def _worker_evaluator(kind: str, s: int) -> BL.LowerLevelEvaluator:
    """Single-scenario evaluator of ``(kind, s)`` in this worker (LRU of ``cfg['keep']`` scenarios)."""
    cfg = _W["cfg"]
    key = (kind, int(s))
    evs: "OrderedDict" = _W["ev"]
    if key in evs:
        evs.move_to_end(key)
        return evs[key]
    t0 = time.perf_counter()
    inst = _load_instance(_instance_path(cfg["instance_dir"], kind, s))
    _W["load_s"] = _W.get("load_s", 0.0) + (time.perf_counter() - t0)     # reported per cell (R8 fix)
    spec = S.SitingSpec.from_dict(cfg["spec"])
    ev = BL.LowerLevelEvaluator([inst], spec, probabilities=[1.0], time_limit=float(cfg["time_limit"]),
                                threads=int(cfg["threads"]), params=dict(cfg["params"]), cache_dir=None,
                                relaxed_targets=bool(cfg["relaxed_targets"]), pruning=dict(cfg["pruning"]),
                                reposition="open_sites", aggregate=bool(cfg["aggregate"]), keep_libraries=1, verbose=False)
    ev.verify_checked_starts = bool(cfg.get("verify_checked_starts", True))
    evs[key] = ev
    while len(evs) > max(1, int(cfg.get("keep", 2))):
        evs.popitem(last=False)
    return ev


def _cell_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """One lower-level cell ``(layout, kind, s, policy)`` in a worker process: the row of
    ``LowerLevelEvaluator.evaluate_scenario`` on the single-scenario evaluator, the portable
    schedule, the per-site statistics (``evaluate.site_metrics``) and the worker's wall / RSS."""
    from ebike_swap_sim.evaluate import site_metrics
    t0 = time.perf_counter()
    _W["load_s"] = 0.0
    kind, s, policy = job["kind"], int(job["s"]), job.get("policy", "baseline")
    lay = BL.Layout.from_key(job["layout"])
    out: Dict[str, Any] = {"job": job, "row": None, "portable": None}
    try:
        ev = _worker_evaluator(kind, s)
        row = ev.evaluate_scenario(lay, 0, policy, time_limit=job.get("time_limit"))
        port = row.pop("_portable", None)
        if port is None and row.get("feasible"):
            port = ev.load_portable(row)
        if job.get("site_metrics", True) and row.get("feasible") and port is not None:
            inst_l, lib = ev.layout_pair(lay, 0)
            sched = BL.materialise_schedule(port, inst_l, lib)
            if sched is not None:
                row["per_site"] = {str(j): v for j, v in site_metrics(inst_l, lib, sched,
                                                                      radius_blocks=int(_W["cfg"].get("radius_blocks", RADIUS_1KM_BLOCKS))).items()}
        row = {k: v for k, v in row.items() if not k.startswith("_")}
        if "traceback" in row:
            row["traceback"] = str(row["traceback"])[-1500:]
        out["row"], out["portable"] = row, port
        # free the layout library (1.5-2 GB at 15 open sites) before the next cell
        ev._pairs.clear()
        ev._pair_order.clear()
    except Exception as exc:  # noqa: BLE001 -- reported as an ERROR row, never silent
        out["row"] = {"status": BL.ERROR, "feasible": None, "total": None, "opex": None, "layout_key": lay.key(),
                      "policy": policy, "error": f"{type(exc).__name__}: {exc}"}
    out["cell_wall_s"] = time.perf_counter() - t0
    out["instance_load_s"] = float(_W.get("load_s", 0.0))      # inside cell_wall_s (the gate sees it)
    out["worker_rss_gb"] = rss_gb()
    out["worker_pid"] = os.getpid()
    return out


def _instance_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Build and save one scenario instance (stage ``instances``; critic C3)."""
    t0 = time.perf_counter()
    path = job["path"]
    if job.get("smoke"):
        inst = S.toy_base_instance(int(job["seed"]), candidates=tuple(tuple(x) for x in job["toy_candidates"]),
                                   **job.get("toy_kw", {}))
    else:
        cands = S.candidates_from_records(job["candidates"])
        depots = S.family_depots(job["family"], cands)
        base = S.make_base_instance(int(job["seed"]), cands, family=job["family"], depots=depots,
                                    n_bikes=int(job["n_bikes"]), **job.get("overrides", {}))
        pr = cm.R6_PRICING
        inst = cm.reprice_orders(base, P=pr["P"], w=pr["w"], v=pr["v"], source=f"experiments/r8_k15.py; {pr['source']}")
        if C.demand_md5(inst) != C.demand_md5(base):
            raise AssertionError("repricing changed the demand side")
    inst.options["library_mode"] = str(job.get("library_mode", "union"))
    inst.meta["r8"] = {"kind": job["kind"], "scenario": int(job["s"]), "design": job.get("design"), "n_bikes": len(inst.bikes),
                       "n_orders": len(inst.orders), "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    inst.save(path)
    import pickle
    with open(path[:-5] + ".pkl", "wb") as fh:
        pickle.dump(inst, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return {"job": {k: v for k, v in job.items() if k != "candidates"}, "path": path, "build_s": time.perf_counter() - t0,
            "n_nodes": len(inst.nodes), "n_routes": len(inst.routes), "n_orders": len(inst.orders), "n_bikes": len(inst.bikes),
            "size_mb": os.path.getsize(path) / 2 ** 20, "worker_rss_gb": rss_gb(), "demand_md5": C.demand_md5(inst)}


class WorkerPool:
    """One PROCESS pool per worker configuration (critic C1), kept open across batches so that the
    workers keep their loaded scenario instances; ``multiprocessing`` context ``start_method``
    (``fork`` where available; the workers load everything from disk, so ``spawn`` works too).
    ``workers <= 1`` runs the jobs in this process with the same worker initialiser (the toy,
    debugging)."""

    def __init__(self, start_method: str = "fork") -> None:
        self.start_method = start_method
        self._pool: Any = None
        self._sig: Optional[str] = None
        self._workers = 0

    def _open(self, cfg: Dict[str, Any], workers: int) -> Any:
        sig = _md5({"cfg": cfg, "workers": int(workers)})
        if self._pool is not None and self._sig == sig:
            return self._pool
        self.close()
        methods = mp.get_all_start_methods()
        method = self.start_method if self.start_method in methods else ("fork" if "fork" in methods else "spawn")
        if sys.platform == "darwin" and method == "fork":
            os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
        ctx = mp.get_context(method)
        self._pool = ctx.Pool(processes=int(workers), initializer=_worker_init, initargs=(cfg,))
        self._sig, self._workers = sig, int(workers)
        return self._pool

    def run(self, cfg: Dict[str, Any], jobs: Sequence[Dict[str, Any]], fn: Callable[[Dict[str, Any]], Dict[str, Any]],
            workers: int, on_result: Optional[Callable[[Dict[str, Any]], None]] = None, chunksize: int = 1) -> List[Dict[str, Any]]:
        jobs = list(jobs)
        out: List[Dict[str, Any]] = []
        if not jobs:
            return out
        if int(workers) <= 1:
            _worker_init(cfg)
            for j in jobs:
                r = fn(j)
                out.append(r)
                if on_result is not None:
                    on_result(r)
            _W["ev"].clear()
            return out
        pool = self._open(cfg, workers)
        for r in pool.imap_unordered(fn, jobs, chunksize=max(1, int(chunksize))):
            out.append(r)
            if on_result is not None:
                on_result(r)
        return out

    def close(self) -> None:
        if self._pool is not None:
            try:
                self._pool.close()
                self._pool.join()
            except Exception:  # noqa: BLE001
                self._pool.terminate()
            self._pool = None
            self._sig = None


_POOL: Optional[WorkerPool] = None


def run_pool(cfg: Dict[str, Any], jobs: Sequence[Dict[str, Any]], fn: Callable[[Dict[str, Any]], Dict[str, Any]],
             workers: int, start_method: str = "fork", on_result: Optional[Callable[[Dict[str, Any]], None]] = None,
             chunksize: int = 1) -> List[Dict[str, Any]]:
    """Run ``fn`` over ``jobs`` in the process-wide :class:`WorkerPool` (opened on first use, kept
    across batches, closed by :func:`close_pool`).  Results arrive in completion order; ``chunksize``
    consecutive jobs go to one worker (scenario-major batches keep the worker's loaded instance)."""
    global _POOL
    if _POOL is None or _POOL.start_method != start_method:
        if _POOL is not None:
            _POOL.close()
        _POOL = WorkerPool(start_method)
    return _POOL.run(cfg, jobs, fn, workers, on_result, chunksize=chunksize)


def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        _POOL.close()
        _POOL = None


# ---------------------------------------------------------------------------
# parent side: offline evaluators (keys and cache only; every solve happens in the pool)
# ---------------------------------------------------------------------------
class OfflineEvaluator(BL.LowerLevelEvaluator):
    """``LowerLevelEvaluator`` on LIGHT scenario instances (routes stripped: keys, probabilities
    and the cache only).  A cell that is not in the cache is never solved here (critic C5: no
    library in the parent): ``prefetch(layouts)`` sends the missing cells to the process pool
    through ``pricer`` and stores the rows; a cell still missing afterwards becomes an
    :data:`bilevel.ERROR` row."""

    pricer: Optional[Callable[[Sequence[BL.Layout]], None]] = None
    kind: str = "in"
    policy_default: str = "baseline"

    def _solve_scenario(self, layout: BL.Layout, s: int, policy: str, key: str, tl: float, warm: Any,
                        best_bd_stop: Any = None, warm_source: Any = None) -> Dict[str, Any]:
        raise RuntimeError("offline evaluator: the cell was not priced by the process pool (prefetch missing)")

    def missing_cells(self, layouts: Sequence[BL.Layout], scenarios: Optional[Sequence[int]] = None,
                      policy: Optional[str] = None, time_limit: Optional[float] = None) -> List[Tuple[BL.Layout, int]]:
        pol = policy or self.policy_default
        idx = list(range(self.n_scenarios)) if scenarios is None else [int(s) for s in scenarios]
        out: List[Tuple[BL.Layout, int]] = []
        seen = set()
        for lay in layouts:
            if lay.key() in seen:
                continue
            seen.add(lay.key())
            for s in idx:
                row = self.cache.get(self.cache_key(lay, s, pol))
                tl = self._time_limit_for(lay) if time_limit is None else float(time_limit)
                if row is None or not self._reusable(row, tl):
                    out.append((lay, s))
        return out

    def prefetch(self, layouts: Sequence[BL.Layout]) -> None:
        if self.pricer is not None:
            self.pricer(list(layouts))


def light_instances(instance_dir: str, kind: str, n: int) -> List[Instance]:
    out = []
    for s in range(int(n)):
        path = _instance_path(instance_dir, kind, s)
        if not os.path.exists(path):
            raise SystemExit(f"scenario instance {path} is missing: run --stage instances first")
        out.append(_load_instance(path, light=True))
    return out


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
class Ctx:
    """Candidates, scenario designs, spec, unit option, the offline evaluators (search subset,
    in-sample, held-out) and the worker configuration of one run."""

    def __init__(self, run: Run, need: Sequence[str] = ()) -> None:
        a = run.args
        self.run = run
        self.smoke = bool(a.smoke)
        self.k = int(a.k)
        self.k_max = max(self.k, int(a.k_max))
        self.vk = sorted({int(x) for x in a.vk} | {self.k})
        if self.smoke:
            self.family = "toy_siting"
            self.option = TOY_OPTION
            self.menu = dict(TOY_MENU)
            # one stratum with two seeds (toy): the stratified CI then has one degree of freedom
            self.design = [{"seed": s, "stratum": 1, "day_type": "weekday", "level": 1.0, "p": 0.5,
                            "seed_in_stratum": s, "overrides": {}} for s in (0, 1)]
            self.held = [{"seed": 100 + s, "stratum": 1, "day_type": "weekday", "level": 1.0, "p": 0.5,
                          "seed_in_stratum": s, "overrides": {}} for s in (0, 1)]
            self.val_design = [{"seed": s, "stratum": 1, "day_type": "weekday", "level": 1.0, "p": 0.5,
                                "seed_in_stratum": s, "overrides": {}} for s in (0, 1)]
            toy0 = S.toy_base_instance(0, candidates=TOY_CANDIDATES, **TOY_KW)
            self.cands = S.candidates_from_records(toy0.meta["candidates"])
            self.dropped, self.info = [], {}
            self.spec = S.TOY_SPEC
            self.n_bikes, self.n_bikes_val = TOY_BIKES, TOY_BIKES
            self.D = 1
            self.pruning: Dict[str, Any] = {}
            self.S_search = [0, 1]
            # a two-site start so the smoke exercises the m2-incumbent restart (an unpriced start
            # was an ERROR row before the R8 fix) and the reference-layout probe of the dry run
            self.start_key = a.start_layout if a.start_layout != REF_LAYOUTS["prod_m2"] else "T1:SC:B1:C1|T4:SC:B1:C1"
            self.ref_layouts: Dict[str, str] = {"toy_m1": "T3:SC:B1:C1", "toy_m2": "T1:SC:B1:C1|T4:SC:B1:C1"}
        else:
            self.family = a.family
            self.option = UNIT_OPTION
            self.cands, self.dropped, self.info = S.dot_candidates(a.dot_csv or S.DOT_CSV_DEFAULT, merge_m=a.merge_m, cap=a.cap)
            if a.reduced:
                self.cands = self.cands[:int(a.reduced)]
            if not self.cands:
                raise SystemExit("no candidates (DOT CSV absent?)")
            self.menu = dict(S.SIZE_MENUS[self.family])
            self.design = S.scenario_design(a.scenarios)
            self.held = S.scenario_design(a.scenarios, held_out=True)
            self.val_design = [{"seed": s, "stratum": 1, "day_type": "weekday", "level": 1.25, "p": 1.0 / a.validate_scenarios,
                                "seed_in_stratum": i, "overrides": {"orders_per_bike_hour": 1.25}}
                               for i, s in enumerate(range(int(a.validate_scenarios)))]
            self.spec = None          # from the saved instances (spec_from_instance), see below
            self.n_bikes = int(S.SITING_FAMILIES[self.family]["n_bikes"]) if a.n_bikes is None else int(a.n_bikes)
            self.n_bikes_val = int(a.validate_bikes)
            self.D = S.access_radius_blocks()
            self.pruning = {} if a.approach_radius is None else {"approach_radius_blocks": int(a.approach_radius)}
            self.S_search = S.lp_scenario_subset(self.design)
            self.start_key = a.start_layout
            self.ref_layouts = dict(REF_LAYOUTS)
        self.ids = [c.id for c in self.cands]
        self.p = [float(d["p"]) for d in self.design]
        self.p_out = [float(d["p"]) for d in self.held]
        self.unit = BL.Layout.of([(self.ids[0],) + self.option]).investment(self.spec) if self.spec is not None else None
        self.scen: List[Instance] = []
        self.scen_out: List[Instance] = []
        self.ev: Optional[OfflineEvaluator] = None
        self.ev_search: Optional[OfflineEvaluator] = None
        self.ev_out: Optional[OfflineEvaluator] = None
        self.proxy: Optional[BL.ProxyScreen] = None
        self.weights: Dict[str, float] = {}
        self.n_cells = 0
        self.n_cells_solved = 0
        self.cell_walls: List[float] = []
        self.worker_rss: List[float] = []
        self.last_worker_rss_max = 0.0
        if need:
            self.attach(need)

    # ------------------------------------------------------------------ scenarios
    def attach(self, need: Sequence[str]) -> None:
        """Load the light instances of ``need`` (``'in'`` / ``'out'``) and build the evaluators."""
        a = self.run.args
        if "in" in need and not self.scen:
            self.scen = light_instances(self.run.instance_dir, "in", len(self.design))
            if self.spec is None:
                ov = S.family_spec_overrides(self.family)
                if a.grid_kw is not None:
                    # plan B (2026-10-30): the shared supply group of all sites (constraint (21)) gets this cap;
                    # a large value removes the shared feeder, each site keeps its own P_kw limit
                    ov["grid_kw"] = float(a.grid_kw)
                self.spec = S.spec_from_instance(self.scen[0], **ov)
                self.unit = BL.Layout.of([(self.ids[0],) + self.option]).investment(self.spec)
            self.ev = self._evaluator(self.scen, self.p, "in")
            sub = [self.scen[s] for s in self.S_search]
            p_sub = [self.p[s] for s in self.S_search]
            tot = sum(p_sub)
            self.ev_search = self._evaluator(sub, [x / tot for x in p_sub], "in", scenario_ids=list(self.S_search))
            self.ev_search.cache = self.ev.cache          # one in-memory cache (R8 fix: no cell priced twice in a process)
            self.proxy = BL.ProxyScreen(self.cands, sub, self.ev_search.p, self.spec)
            self.weights = BL.demand_weights(self.cands, sub, self.D, self.ev_search.p)
        if "out" in need and not self.scen_out and self.held:
            self.scen_out = light_instances(self.run.instance_dir, "out", len(self.held))
            self.ev_out = self._evaluator(self.scen_out, self.p_out, "out")
            if self.ev is not None:
                self.ev_out.cache = self.ev.cache          # keys differ by seed / demand hash, so sharing is safe
        self.run.config_md5 = self.config_md5()
        _ = a

    def _evaluator(self, scen: Sequence[Instance], p: Sequence[float], kind: str,
                   scenario_ids: Optional[List[int]] = None) -> OfflineEvaluator:
        a = self.run.args
        ev = OfflineEvaluator(scen, self.spec, probabilities=list(p), time_limit=float(a.time_limit), threads=1,
                              params=dict(C.ILP_PARAMS_R3), cache_dir=self.run.cache, relaxed_targets=True,
                              pruning=dict(self.pruning), reposition="open_sites", aggregate=True, verbose=False)
        # aggregate=True: the ILP cells of the validate stage are keyed as the aggregated formulation (the
        # workers solve them so); rule-follower keys do not carry the formulation
        ev.kind = kind
        ev.scenario_ids = list(range(len(scen))) if scenario_ids is None else list(scenario_ids)
        ev.pricer = lambda lays, _ev=ev: self.price_cells(_ev, lays)
        return ev

    def worker_cfg(self, policy: str = "baseline") -> Dict[str, Any]:
        a = self.run.args
        ilp = policy == "ilp"
        return {"instance_dir": self.run.instance_dir, "spec": self.spec.to_dict(), "pruning": dict(self.pruning),
                "params": dict(C.ILP_PARAMS_R3), "threads": int(a.validate_threads if ilp else 1),
                "time_limit": float(a.validate_time_limit if ilp else a.time_limit), "aggregate": bool(ilp),
                "relaxed_targets": True, "keep": int(a.worker_keep), "radius_blocks": RADIUS_1KM_BLOCKS,
                "verify_checked_starts": not bool(a.validate_skip_verify)}

    def config_md5(self) -> str:
        parts = {"family": self.family, "k": self.k, "option": list(self.option), "candidates": self.ids,
                 "design": [{k: v for k, v in d.items()} for d in self.design],
                 "held": [{k: v for k, v in d.items()} for d in self.held], "n_bikes": self.n_bikes,
                 "spec": None if self.spec is None else self.spec.to_dict(), "pruning": self.pruning,
                 "S_search": self.S_search, "menu": {k: [list(x) for x in v] for k, v in self.menu.items()}}
        if self.ev is not None:
            parts["demand_md5"] = self.ev.demand_md5
        return _md5(parts)

    # ------------------------------------------------------------------ pricing
    def price_cells(self, ev: OfflineEvaluator, layouts: Sequence[BL.Layout], scenarios: Optional[Sequence[int]] = None,
                    policy: Optional[str] = None, time_limit: Optional[float] = None, tag: str = "") -> Dict[str, int]:
        """Price the cells of ``layouts`` that are not in ``ev``'s cache in the process pool and
        store the rows (critic C1).  ``scenarios`` are indices of ``ev``."""
        a = self.run.args
        pol = policy or ev.policy_default
        missing = ev.missing_cells(layouts, scenarios, pol, time_limit)
        stats = {"cells": 0, "solved": 0, "errors": 0, "cache_hits": 0}
        if not missing:
            return stats
        if a.dry_run:
            self.n_cells += len(missing)
            return {**stats, "cells": len(missing)}
        workers = int(a.validate_workers if pol == "ilp" else a.workers)
        if not self.run.rss_guard(f"pricing {len(missing)} cells", pool_gb=workers * float(self.last_worker_rss_max)):
            raise SystemExit("RSS guard")
        # scenario-major order with a chunk of consecutive jobs per worker, so a worker's LRU of loaded
        # instances (--worker-keep) is hit by the next job (R8 fix; layout-major order reloaded the
        # pickled instance on most cells)
        missing.sort(key=lambda t: (int(t[1]), t[0].key()))
        jobs = [{"layout": lay.key(), "kind": ev.kind, "s": int(ev.scenario_ids[s]), "policy": pol,
                 "time_limit": time_limit, "site_metrics": True, "_s_local": int(s)} for lay, s in missing]
        n_lay = len({l.key() for l, _s in missing})
        chunk = max(1, min(n_lay, len(jobs) // (4 * max(1, workers)), 8))
        t0 = time.perf_counter()
        loads: List[float] = []

        def on_result(res: Dict[str, Any]) -> None:
            job, row = res["job"], res["row"]
            lay = BL.Layout.from_key(job["layout"])
            s_local = int(job["_s_local"])
            row = dict(row)
            row["cell_wall_s"] = res["cell_wall_s"]
            row["instance_load_s"] = res.get("instance_load_s")
            row["worker_rss_gb"] = res["worker_rss_gb"]
            loads.append(float(res.get("instance_load_s") or 0.0))
            self.cell_walls.append(float(res["cell_wall_s"]))
            self.worker_rss.append(float(res["worker_rss_gb"]))
            stats["cells"] += 1
            if row.get("status") == BL.ERROR:
                stats["errors"] += 1
                self.run.emit({"kind": "cell_error", "tag": tag, "layout_key": lay.key(), "scenario": job["s"], "scenario_kind": job["kind"],
                               "error": row.get("error"), "traceback": row.get("traceback")}, echo=True)
            else:
                stats["solved"] += 1
            ev.store_external_row(lay, s_local, pol, row, res.get("portable"))

        run_pool(self.worker_cfg(pol), jobs, _cell_job, workers, start_method=a.start_method, on_result=on_result, chunksize=chunk)
        self.n_cells += stats["cells"]
        self.n_cells_solved += stats["solved"]
        if stats["cells"]:
            self.last_worker_rss_max = max(self.worker_rss[-stats["cells"]:], default=0.0)
        self.run.emit({"kind": "cell_batch", "tag": tag, "policy": pol, "scenario_kind": ev.kind, "n_cells": stats["cells"],
                       "n_layouts": n_lay, "errors": stats["errors"], "workers": workers, "chunksize": chunk,
                       "instance_load_s_sum": sum(loads), "instance_loads": sum(1 for x in loads if x > 0),
                       "wall_s": time.perf_counter() - t0, "cell_s_max": max(self.cell_walls[-stats["cells"]:], default=None),
                       "cell_s_mean": (sum(self.cell_walls[-stats["cells"]:]) / stats["cells"]) if stats["cells"] else None,
                       "worker_rss_gb_max": max(self.worker_rss[-stats["cells"]:], default=None), "parent_rss_gb": rss_gb()},
                      echo=True)
        return stats

    def price(self, ev: OfflineEvaluator, named: Sequence[Tuple[str, BL.Layout]], tag: str,
              scenarios: Optional[Sequence[int]] = None, policy: Optional[str] = None,
              time_limit: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Full value of every named layout on ``ev`` (all its scenarios or ``scenarios``), the
        missing cells priced in one pool batch; emits one ``price15`` record per layout."""
        pol = policy or ev.policy_default
        lays = [l for _n, l in named if l is not None]
        self.price_cells(ev, lays, scenarios, pol, time_limit, tag=tag)
        out: Dict[str, Dict[str, Any]] = {}
        if self.run.args.dry_run:
            return out
        for name, lay in named:
            if lay is None:
                out[name] = {"name": name, "layout_key": None, "status": "NONE", "V": None}
                continue
            e = ev.evaluate(lay, pol, scenarios=scenarios)
            rec = self.summary_of(ev, lay, e, scenarios)
            rec.update(name=name, tag=tag, kind="price15", scenario_kind=ev.kind, policy=pol)
            self.run.emit(rec, echo=True)
            out[name] = rec
        return out

    def summary_of(self, ev: OfflineEvaluator, lay: BL.Layout, e: Dict[str, Any],
                   scenarios: Optional[Sequence[int]] = None) -> Dict[str, Any]:
        idx = list(range(ev.n_scenarios)) if scenarios is None else list(scenarios)
        rows = e["rows"]
        opex = [r.get("opex") for r in rows]
        complete = e["status"] == "OK" and len(rows) == len(idx) and all(o is not None for o in opex)
        rec: Dict[str, Any] = {"layout_key": lay.key(), "layout": lay.to_json(), "n_open": lay.n_open, "k": lay.n_open,
                               "status": e["status"], "V": _f(e["V"]), "C_setup": e["C_setup"], "investment": e["investment"],
                               "served_share": e.get("served_share"), "opex": opex, "statuses": e["statuses"],
                               "scenarios": [int(ev.scenario_ids[s]) for s in idx[:len(rows)]], "complete": complete,
                               "n_cache_hits": e["n_cache_hits"], "error": e.get("error")}
        if complete:
            strata = [self.stratum_of(ev, s) for s in idx]
            ci = BL.stratified_ci([float(o) for o in opex], strata, [ev.p[s] for s in idx])
            rec["V_ci95"] = (None if ci["half"] is None else [rec["V"] - ci["half"], rec["V"] + ci["half"]])
            rec["ci"] = ci
            met = [r.get("metrics") or {} for r in rows]
            rec["n_swaps_mean"] = sum(ev.p[s] * float(m.get("n_swaps", 0)) for s, m in zip(idx, met)) / sum(ev.p[s] for s in idx)
            rec["kwh_mean"] = sum(ev.p[s] * float(m.get("kwh_purchased", 0)) for s, m in zip(idx, met)) / sum(ev.p[s] for s in idx)
            rec["components"] = self._mean_components(ev, rows, idx)
        return rec

    def stratum_of(self, ev: OfflineEvaluator, s: int) -> Any:
        design = self.held if ev.kind == "out" else self.design
        return design[int(ev.scenario_ids[s])].get("stratum", s)

    @staticmethod
    def _mean_components(ev: OfflineEvaluator, rows: Sequence[Dict[str, Any]], idx: Sequence[int]) -> Dict[str, float]:
        tot = sum(ev.p[s] for s in idx)
        out: Dict[str, float] = {}
        for s, r in zip(idx, rows):
            for k, v in (r.get("components") or {}).items():
                if isinstance(v, (int, float)):
                    out[k] = out.get(k, 0.0) + ev.p[s] * float(v) / tot
        return out

    # ------------------------------------------------------------------ per-site statistics
    def per_site_table(self, ev: OfflineEvaluator, lay: BL.Layout, scenarios: Optional[Sequence[int]] = None
                       ) -> Dict[str, Dict[str, Any]]:
        """p-weighted per-site statistics of ``lay`` over the scenarios (from the cached rows'
        ``per_site`` entries), with the stratified CI of the swaps per evening."""
        idx = list(range(ev.n_scenarios)) if scenarios is None else list(scenarios)
        rows = [ev.cache.get(ev.cache_key(lay, s, ev.policy_default)) for s in idx]
        if any(r is None or not r.get("per_site") for r in rows):
            return {}
        ptot = sum(ev.p[s] for s in idx)
        out: Dict[str, Dict[str, Any]] = {}
        for l, r, _B, _C in lay.open:
            if not S.ROLE_SWAP[r]:
                continue
            fid = S.facility_id(l, r)
            per = [row["per_site"].get(fid) or {} for row in rows]
            sw = [float(x.get("swaps", 0)) for x in per]
            ci = BL.stratified_ci(sw, [self.stratum_of(ev, s) for s in idx], [ev.p[s] for s in idx])
            mean = lambda key: sum(ev.p[s] * float(x.get(key, 0) or 0) for s, x in zip(idx, per)) / ptot  # noqa: E731
            m = mean("swaps")
            out[l] = {"id": l, "facility": fid, "swaps_mean": m,
                      "swaps_lo": (None if ci["half"] is None else m - ci["half"]),
                      "swaps_hi": (None if ci["half"] is None else m + ci["half"]),
                      "orders_1km_served": mean("orders_1km_served"), "orders_1km_total": mean("orders_1km_total"),
                      "riders_distinct": mean("riders_distinct"), "charger_busy_share": mean("charger_busy_share"),
                      "idle_share": mean("idle_share"), "kwh_bought": mean("kwh_bought"), "wait_min_mean": mean("wait_min_mean"),
                      "stockout_slots": mean("stockout_slots"), "n_scenarios": len(idx), "swaps_per_scenario": sw}
        return out


# ---------------------------------------------------------------------------
# layouts of the study
# ---------------------------------------------------------------------------
def unit_layout(ctx: Ctx, locs: Iterable[str]) -> BL.Layout:
    r, B, Cc = ctx.option
    return BL.Layout.of([(l, r, B, Cc) for l in locs])


def rule_layouts(ctx: Ctx, k: int) -> Dict[str, Optional[BL.Layout]]:
    """CSCD-k, CSTC-k (inverse-distance access), CSAV-k, k-median-k and DOT-first-k, all at the unit
    option (exactly ``k`` units: no budget remainder, so no extra sizes)."""
    assert ctx.ev_search is not None and ctx.proxy is not None
    sp = ctx.spec
    b = k * ctx.unit
    r, B, Cc = ctx.option
    out: Dict[str, Optional[BL.Layout]] = {}
    out["CSCD"] = BL.rule_layout("CSCD", ctx.cands, b, sp, ctx.weights, role=r, base_size=(B, Cc), k=k, max_B=B, max_C=Cc)
    aw = BL.access_weights(ctx.cands, ctx.ev_search.scenarios, ctx.ev_search.p)
    out["CSTC"] = BL.rule_layout("CSTC", ctx.cands, b, sp, aw, role=r, base_size=(B, Cc), k=k, max_B=B, max_C=Cc)
    out["CSAV"] = BL.rule_layout("CSAV", ctx.cands, b, sp, role=r, base_size=(B, Cc), k=k, max_B=B, max_C=Cc)
    km, info = BL.k_median_layout(ctx.proxy, k, ctx.option, time_limit=float(ctx.run.args.kmedian_time_limit))
    out["kmedian"] = km
    ctx.run.emit({"kind": "kmedian", "k": k, "layout_key": None if km is None else km.key(), **info})
    out["dotfirst"] = BL.dot_first_layout(ctx.cands, k, ctx.weights, ctx.option)
    return out


def ref_layout(ctx: Ctx, key: Optional[str]) -> Optional[BL.Layout]:
    """A production layout key re-expressed at the unit option; ``None`` when a location is unknown."""
    if not key:
        return None
    try:
        lay = BL.Layout.from_key(key)
    except Exception:  # noqa: BLE001
        return None
    if any(l not in ctx.ids for l in lay.locations()):
        return None
    return unit_layout(ctx, lay.locations())


# ---------------------------------------------------------------------------
# stage: instances (critic C3)
# ---------------------------------------------------------------------------
def instance_jobs(ctx: Ctx, kinds: Sequence[str] = ("in", "out")) -> List[Dict[str, Any]]:
    a = ctx.run.args
    jobs: List[Dict[str, Any]] = []
    recs = S.candidates_to_records(ctx.cands)
    for kind in kinds:
        design = {"in": ctx.design, "out": ctx.held, "val": ctx.val_design}[kind]
        nb = ctx.n_bikes_val if kind == "val" else ctx.n_bikes
        for s, d in enumerate(design):
            job = {"kind": kind, "s": s, "seed": int(d["seed"]), "overrides": dict(d.get("overrides", {})), "n_bikes": nb,
                   "family": ctx.family, "smoke": ctx.smoke, "path": _instance_path(ctx.run.instance_dir, kind, s),
                   "design": {k: v for k, v in d.items() if k != "overrides"}, "library_mode": "union",
                   "toy_candidates": [list(x) for x in TOY_CANDIDATES], "toy_kw": ({**TOY_KW, "n_bikes": nb} if ctx.smoke else {})}
            job["signature"] = _md5({k: v for k, v in job.items() if k not in ("path",)} | {"candidates": ctx.ids,
                                                                                            "pricing": cm.R6_PRICING if not ctx.smoke else "toy"})
            job["candidates"] = recs
            jobs.append(job)
    _ = a
    return jobs


def manifest_path(ctx: Ctx) -> str:
    return os.path.join(ctx.run.instance_dir, "manifest.json")


def load_manifest(ctx: Ctx) -> Dict[str, Any]:
    p = manifest_path(ctx)
    return _read_json(p) if os.path.exists(p) else {"files": {}}


def stage_instances(run: Run, ctx: Ctx, kinds: Sequence[str] = ("in", "out")) -> Dict[str, Any]:
    a = run.args
    jobs = instance_jobs(ctx, kinds)
    man = load_manifest(ctx)
    todo = []
    for j in jobs:
        have = man["files"].get(os.path.basename(j["path"]))
        if have and have.get("signature") == j["signature"] and os.path.exists(j["path"]) and not a.redo:
            continue
        todo.append(j)
    plan = {"kind": "instances_plan", "n_scenarios": len(jobs), "n_to_build": len(todo), "kinds": list(kinds),
            "n_bikes": ctx.n_bikes, "n_bikes_val": ctx.n_bikes_val, "workers": a.workers,
            "paths": [os.path.basename(j["path"]) for j in jobs]}
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    t0 = time.perf_counter()

    def on_result(res: Dict[str, Any]) -> None:
        j = res["job"]
        man["files"][os.path.basename(res["path"])] = {"signature": j["signature"], "kind": j["kind"], "s": j["s"], "seed": j["seed"],
                                                      "n_bikes": res["n_bikes"], "n_orders": res["n_orders"], "n_nodes": res["n_nodes"],
                                                      "n_routes": res["n_routes"], "build_s": res["build_s"], "size_mb": res["size_mb"],
                                                      "demand_md5": res["demand_md5"], "worker_rss_gb": res["worker_rss_gb"]}
        _write_json(manifest_path(ctx), man)
        run.emit({"kind": "instance_built", "file": os.path.basename(res["path"]), "build_s": res["build_s"], "n_nodes": res["n_nodes"],
                  "n_routes": res["n_routes"], "n_orders": res["n_orders"], "n_bikes": res["n_bikes"], "size_mb": res["size_mb"],
                  "worker_rss_gb": res["worker_rss_gb"]}, echo=False)
        print(json.dumps({"built": os.path.basename(res["path"]), "build_s": round(res["build_s"], 1), "n_nodes": res["n_nodes"],
                          "n_routes": res["n_routes"], "n_orders": res["n_orders"]}), flush=True)
    run_pool({"threads": 1}, todo, _instance_job, int(a.workers), start_method=a.start_method, on_result=on_result)
    out = {"n_built": len(todo), "wall_s": time.perf_counter() - t0, "manifest": man}
    if kinds == ("in", "out") or set(kinds) >= {"in", "out"}:
        run.emit({"kind": "stage_done", "stage": "instances", "n_built": len(todo), "wall_s": out["wall_s"]}, echo=True)
    return out


# ---------------------------------------------------------------------------
# stage: dry run with the gates
# ---------------------------------------------------------------------------
def stage_dryrun(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    ctx.attach(("in",))
    assert ctx.ev is not None
    lay = ref_layout(ctx, a.dryrun_layout) if a.dryrun_layout else None
    if lay is None:
        lay = rule_layouts(ctx, ctx.k)["CSCD"]
    if lay is None:
        raise SystemExit("dryrun: no layout")
    ctx.cell_walls, ctx.worker_rss = [], []
    res = ctx.price(ctx.ev, [("dryrun", lay)], tag="dryrun")
    if a.dry_run:
        plan = {"kind": "dryrun_plan", "layout_key": lay.key(), "n_cells": ctx.n_cells}
        run.emit(plan, echo=True)
        return plan
    rec = res["dryrun"]
    # reference layouts at this fleet (reviewer): the production m = 1 / m = 2 layouts, the singletons of
    # the pair and the search start, priced on every in-sample scenario in one batch; their statuses say
    # whether V(1), V(2) and the m2 restart exist at 48 riders before the search is paid for
    refs: Dict[str, BL.Layout] = {}
    for n, key in list(ctx.ref_layouts.items()) + ([("start", ctx.start_key)] if ctx.start_key else []):
        l = ref_layout(ctx, key)
        if l is not None and l.key() not in {x.key() for x in refs.values()}:
            refs[n] = l
            if l.n_open > 1:
                for loc in l.locations():
                    single = unit_layout(ctx, [loc])
                    if single.key() not in {x.key() for x in refs.values()}:
                        refs[f"{n}:{loc}"] = single
    ref_res = ctx.price(ctx.ev, list(refs.items()), tag="dryrun_refs") if refs else {}
    ref_rows = {n: {"layout_key": refs[n].key(), "V": r.get("V"), "status": r.get("status"), "served_share": r.get("served_share"),
                    "statuses": r.get("statuses")} for n, r in ref_res.items()}
    for n, r in ref_rows.items():
        run.emit({"kind": "dryrun_ref", "name": n, **r}, echo=True)
    table = ctx.per_site_table(ctx.ev, lay)
    swaps = sorted(v["swaps_mean"] for v in table.values())
    med = statistics.median(swaps) if swaps else 0.0
    cells = [ctx.ev.cache.get(ctx.ev.cache_key(lay, s, "baseline")) or {} for s in range(ctx.ev.n_scenarios)]
    walls = [float(r.get("cell_wall_s") or 0.0) for r in cells]
    rss = [float(r.get("worker_rss_gb") or 0.0) for r in cells]
    gates = {"cell_s": {"max": max(walls, default=0.0), "limit": GATES["cell_s"], "ok": max(walls, default=0.0) <= GATES["cell_s"]},
             "rss_gb": {"max": max(rss, default=0.0), "limit": GATES["rss_gb"], "ok": max(rss, default=0.0) <= GATES["rss_gb"]},
             "median_site_swaps": {"value": med, "limit": GATES["median_site_swaps"], "ok": med >= GATES["median_site_swaps"]}}
    escalate = not all(g["ok"] for g in gates.values())
    out = {"kind": "dryrun", "layout_key": lay.key(), "V": rec.get("V"), "served_share": rec.get("served_share"),
           "n_scenarios": ctx.ev.n_scenarios, "cell_wall_s": walls, "worker_rss_gb": rss, "swaps_per_site": {l: v["swaps_mean"] for l, v in table.items()},
           "median_site_swaps": med, "gates": gates, "escalate": escalate, "cached_cells": sum(1 for r in cells if r.get("cell_wall_s") is None),
           "reference_layouts": ref_rows, "instance_load_s": [r.get("instance_load_s") for r in cells],
           "n_arcs": [r.get("n_arcs") for r in cells], "runtime_s": [r.get("runtime_s") for r in cells],
           "recommendation": ("go: 48 riders / 240 orders" if not escalate else
                              "escalate: 64 riders / 320 orders with pickup-radius pruning (design 12.2), or the cell/RSS budget"),
           "smoke": ctx.smoke}
    _write_json(os.path.join(run.dir, "dryrun.json"), out)
    run.emit({**out, "kind": "dryrun"}, echo=True)
    run.emit({"kind": "stage_done", "stage": "dryrun", "escalate": escalate}, echo=True)
    return out


def gates_block(run: Run, ctx: Ctx) -> Optional[str]:
    """Reason the search must not start (a failed dry-run gate), ``None`` when it may."""
    if run.args.ignore_gates or ctx.smoke:
        return None
    p = os.path.join(run.dir, "dryrun.json")
    if not os.path.exists(p):
        return "dryrun.json is missing: run --stage dryrun first (or --ignore-gates)"
    d = _read_json(p)
    if d.get("escalate"):
        bad = [k for k, g in d.get("gates", {}).items() if not g.get("ok")]
        return f"dry-run gates failed ({', '.join(bad)}): {d.get('recommendation')} (or --ignore-gates)"
    return None


# ---------------------------------------------------------------------------
# stage: validate (critic C6: ratio with gaps)
# ---------------------------------------------------------------------------
def stage_validate(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    try:
        import gurobipy  # noqa: F401
    except ImportError:
        rec = {"kind": "validate", "status": "skipped", "reason": "gurobipy not available"}
        run.emit(rec, echo=True)
        return rec
    stage_instances(run, ctx, kinds=("val",))
    ctx.attach(("in",))
    kv = int(a.validate_k)
    scen_val = light_instances(run.instance_dir, "val", len(ctx.val_design))
    p_val = [float(d["p"]) for d in ctx.val_design]
    tot = sum(p_val)
    ev_val = ctx._evaluator(scen_val, [x / tot for x in p_val], "val")
    if ctx.ev is not None:
        ev_val.cache = ctx.ev.cache           # one in-memory cache per process (keys differ where the scenarios do)
    ev_val.design = ctx.val_design
    ctx.held_val = ctx.val_design
    # layouts: the greedy best at k_v under the rule follower AT THE VALIDATION FLEET (forward selection
    # from the m = 2 incumbent with the proxy screen on the validation scenarios), CSCD-kv, CSAV-kv
    rules = rule_layouts(ctx, kv)
    named: List[Tuple[str, BL.Layout]] = []
    greedy, greedy_src = None, "none"
    if not a.dry_run:
        proxy_v = BL.ProxyScreen(ctx.cands, scen_val, ev_val.p, ctx.spec)
        kw = {**search_kwargs(ctx), "screen": proxy_v, "max_passes": 2}
        g = BL.greedy_local_search(ev_val, ctx.cands, kv * ctx.unit, start=ref_layout(ctx, ctx.start_key), force_k=kv,
                                   on_step=lambda rec: run.emit({"kind": "search_step", "restart": "validate_greedy", **rec}), **kw)
        rv = g["per_budget"][kv * ctx.unit]
        greedy = rv.get("layout")
        greedy_src = "greedy at the validation fleet (rule follower, proxy screen)"
    if greedy is None:
        greedy = rules["kmedian"]
        greedy_src = "kmedian (greedy did not reach k)"
    named.append((f"greedy{kv}", greedy))
    named.append((f"CSCD{kv}", rules["CSCD"]))
    named.append((f"CSAV{kv}", rules["CSAV"]))
    named = [(n, l) for n, l in named if l is not None]
    seen = set()
    uniq: List[Tuple[str, BL.Layout]] = []
    for n, l in named:
        if l.key() not in seen:
            seen.add(l.key())
            uniq.append((n, l))
    plan = {"kind": "validate_plan", "layouts": [(n, l.key()) for n, l in uniq], "n_scenarios": len(scen_val),
            "n_bikes": ctx.n_bikes_val, "time_limit": a.validate_time_limit, "threads": a.validate_threads,
            "workers": a.validate_workers, "greedy_source": greedy_src}
    run.emit(plan, echo=True)
    if a.dry_run:
        return plan
    rule = ctx.price(ev_val, uniq, tag="validate_rule", policy="baseline")
    ilp = ctx.price(ev_val, uniq, tag="validate_ilp", policy="ilp", time_limit=float(a.validate_time_limit))
    rows: List[Dict[str, Any]] = []
    for n, l in uniq:
        for s in range(ev_val.n_scenarios):
            rr = ev_val.cache.get(ev_val.cache_key(l, s, "baseline")) or {}
            ri = ev_val.cache.get(ev_val.cache_key(l, s, "ilp")) or {}
            v_rule, v_ilp = rr.get("total"), ri.get("total")
            rows.append({"name": n, "layout_key": l.key(), "scenario": s, "seed": ev_val.seeds[s], "rule_total": v_rule,
                         "ilp_incumbent": v_ilp, "ilp_bound": ri.get("bound"), "ilp_gap": ri.get("gap"), "ilp_status": ri.get("gurobi_status") or ri.get("status"),
                         "ilp_runtime_s": ri.get("runtime_s"), "ratio_rule_over_incumbent": (None if not v_rule or not v_ilp else v_rule / v_ilp),
                         "ratio_rule_over_bound": (None if not v_rule or not ri.get("bound") else v_rule / float(ri["bound"])),
                         "rule_served": (rr.get("metrics") or {}).get("served_share"), "ilp_served": (ri.get("metrics") or {}).get("served_share"),
                         "mip_start": ri.get("mip_start_variant"), "n_arcs": ri.get("n_arcs"), "n_binaries": ri.get("n_binaries")})
    ratios = [r["ratio_rule_over_incumbent"] for r in rows if r["ratio_rule_over_incumbent"] is not None]
    gaps = [r["ilp_gap"] for r in rows if r["ilp_gap"] is not None]
    out = {"kind": "validate", "rows": rows, "n_cells": len(rows), "ratio_median": (statistics.median(ratios) if ratios else None),
           "ratio_min": (min(ratios) if ratios else None), "ratio_max": (max(ratios) if ratios else None),
           "gap_median": (statistics.median(gaps) if gaps else None), "gap_max": (max(gaps) if gaps else None),
           "n_optimal": sum(1 for r in rows if str(r["ilp_status"]) == "OPTIMAL"), "time_limit": a.validate_time_limit,
           "threads": a.validate_threads, "n_bikes": ctx.n_bikes_val, "k": kv,
           "statement": "rule / incumbent ratio with the MIP gap of every cell; no rank statistic (critic C6)",
           "rule_values": {n: r.get("V") for n, r in rule.items()}, "ilp_values": {n: r.get("V") for n, r in ilp.items()}}
    _write_json(os.path.join(run.dir, "validate.json"), out)
    run.emit({k: v for k, v in out.items() if k != "rows"}, echo=True)
    run.emit({"kind": "stage_done", "stage": "validate"}, echo=True)
    return out


# ---------------------------------------------------------------------------
# stage: search
# ---------------------------------------------------------------------------
def search_kwargs(ctx: Ctx) -> Dict[str, Any]:
    a = ctx.run.args
    return dict(size_menu={ctx.option[0]: [(ctx.option[1], ctx.option[2])]}, roles=(ctx.option[0],), k_screen=int(a.k_screen),
                max_passes=int(a.max_passes), moves=("swap",), screen=ctx.proxy, local_search=True, min_served_share=None,
                policy="baseline", swap_neighbourhood={"nearest": int(a.swap_nearest), "proxy_best": int(a.swap_proxy_best)})


def polish_sizes(run: Run, ctx: Ctx, best: BL.Layout, v_best: float) -> Tuple[BL.Layout, float, List[Dict[str, Any]]]:
    """Size polish at fixed locations and fixed investment: (i) D'Hondt sizes by the swaps per site
    within the family menu, (ii) one-for-one transfers of a spare / a charger from the least to the
    most used sites (ranked by the swap difference, ``--k-screen`` priced per round, first
    improvement, up to ``--polish-rounds`` rounds)."""
    a = run.args
    assert ctx.ev_search is not None
    ev = ctx.ev_search
    role = ctx.option[0]
    menu = [(B, Cc) for (B, Cc) in ctx.menu.get(role, [(ctx.option[1], ctx.option[2])])]
    Bs = sorted({B for B, _ in menu})
    Cs = sorted({Cc for _, Cc in menu})
    log: List[Dict[str, Any]] = []
    cur, v_cur = best, v_best
    totB, totC = best.total_B(), best.total_C()

    def swaps_of(lay: BL.Layout) -> Dict[str, float]:
        t = ctx.per_site_table(ev, lay)
        return {l: float(v["swaps_mean"]) for l, v in t.items()}

    def valid(lay: BL.Layout) -> bool:
        return (lay.total_B() == totB and lay.total_C() == totC and all((B, Cc) in menu for _l, _r, B, Cc in lay.open))

    # (i) D'Hondt
    sw = swaps_of(cur)
    if not sw:
        log.append({"step": "dhondt", "skipped": "no per-site table for the best layout (an ERROR or INFEASIBLE cell)"})
    if sw and (len(Bs) > 1 or len(Cs) > 1):
        size = {l: [min(Bs), min(Cs)] for l in cur.locations()}
        for pos, cap, total in ((0, max(Bs), totB), (1, max(Cs), totC)):
            left = total - sum(v[pos] for v in size.values())
            while left > 0:
                open_ = [l for l in size if size[l][pos] < cap]
                if not open_:
                    break
                bestl = max(open_, key=lambda l: (sw.get(l, 0.0) / (size[l][pos] - min((Bs, Cs)[pos]) + 1), -cur.locations().index(l)))
                size[bestl][pos] += 1
                left -= 1
        dh = BL.Layout.of([(l, role, size[l][0], size[l][1]) for l in cur.locations()])
        if valid(dh) and dh.key() != cur.key():
            r = ctx.price(ev, [("polish_dhondt", dh)], tag="polish")["polish_dhondt"]
            log.append({"step": "dhondt", "layout_key": dh.key(), "V": r.get("V"), "status": r.get("status")})
            if r.get("V") is not None and r["V"] < v_cur - 1e-6:
                cur, v_cur = dh, float(r["V"])
    # (ii) transfers
    for rnd in range(int(a.polish_rounds)):
        sw = swaps_of(cur)
        moves: List[Tuple[float, BL.Layout, str]] = []
        for it_i in cur.open:
            for it_j in cur.open:
                if it_i[0] == it_j[0]:
                    continue
                li, _ri, Bi, Ci = it_i
                lj, _rj, Bj, Cj = it_j
                for kind2, (Bi2, Ci2, Bj2, Cj2) in (("spare", (Bi - 1, Ci, Bj + 1, Cj)), ("charger", (Bi, Ci - 1, Bj, Cj + 1))):
                    if (Bi2, Ci2) not in menu or (Bj2, Cj2) not in menu:
                        continue
                    lay2 = cur.replace(li, (li, role, Bi2, Ci2)).replace(lj, (lj, role, Bj2, Cj2))
                    moves.append((sw.get(lj, 0.0) - sw.get(li, 0.0), lay2, f"{kind2} {li}->{lj}"))
        if not moves:
            break
        moves.sort(key=lambda t: (-t[0], t[1].key()))
        top = moves[:max(1, int(a.k_screen))]
        res = ctx.price(ev, [(f"polish_r{rnd}_{i}", l) for i, (_g, l, _d) in enumerate(top)], tag="polish")
        improved = False
        for i, (_g, l, d) in enumerate(top):
            r = res[f"polish_r{rnd}_{i}"]
            log.append({"step": f"transfer_round{rnd}", "move": d, "layout_key": l.key(), "V": r.get("V"), "status": r.get("status")})
            if r.get("V") is not None and r["V"] < v_cur - 1e-6:
                cur, v_cur = l, float(r["V"])
                improved = True
                break
        if not improved:
            break
    return cur, v_cur, log


def stage_search(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    ctx.attach(("in",))
    assert ctx.ev_search is not None and ctx.proxy is not None
    block = gates_block(run, ctx)
    if block:
        run.emit({"kind": "search_blocked", "reason": block}, echo=True)
        raise SystemExit(block)
    ev = ctx.ev_search
    k = ctx.k
    unit = ctx.unit
    t_stage = time.perf_counter()
    S.write_candidate_tables(ctx.cands, ctx.dropped, run.dir)
    run.emit({"kind": "search_plan", "k": k, "k_max": ctx.k_max, "unit": unit, "option": list(ctx.option), "S_search": ctx.S_search,
              "n_candidates": len(ctx.ids), "k_screen": a.k_screen, "max_passes": a.max_passes,
              "swap_neighbourhood": {"nearest": a.swap_nearest, "proxy_best": a.swap_proxy_best}, "workers": a.workers,
              "gate": BL.service_gate("baseline"), "demand_D_blocks": ctx.D}, echo=True)
    # 0. warm starts and comparison layouts
    rules = rule_layouts(ctx, k)
    warm = ctx.price(ev, [(f"{n}{k}", l) for n, l in rules.items()], tag="warm")
    # 1. restarts of the forward selection
    start_m2 = ref_layout(ctx, ctx.start_key)
    restarts: List[Tuple[str, Optional[BL.Layout]]] = []
    if start_m2 is not None:
        restarts.append(("m2_incumbent", start_m2))
    for n in ("CSCD", "CSAV"):
        lay = rules.get(n)
        if lay is not None and lay.n_open >= 2:
            restarts.append((f"{n}_best2", BL.top_sites(lay, ctx.weights, 2)))
    restarts.append(("empty", None))
    # the start layouts in one pool batch (R8 fix: an unpriced start was an ERROR row on the offline
    # evaluator and the restart silently fell back to the singleton search from empty)
    ctx.price(ev, [(n, l) for n, l in restarts if l is not None], tag="starts")
    kw = search_kwargs(ctx)
    results: Dict[str, Dict[str, Any]] = {}
    hist_n = 0
    for name, start in restarts:
        if a.dry_run:
            continue
        t0 = time.perf_counter()
        g = BL.greedy_local_search(ev, ctx.cands, k * unit, start=start, force_k=k,
                                   on_step=lambda rec, _n=name: run.emit({"kind": "search_step", "restart": _n, **rec}), **kw)
        r = g["per_budget"][k * unit]
        start_status = next((h.get("status") for h in g["history"] if h.get("step") == "start"), None)
        results[name] = {"start": None if start is None else start.key(), "start_status": start_status,
                         "layout_key": None if r["layout"] is None else r["layout"].key(),
                         "V": r.get("value"), "status": r["status"], "served_share": r.get("served_share"),
                         "path_k": {int(kk): list(v) for kk, v in g["path_k"].items()}, "class_counts": g["class_counts"],
                         "best_singleton": g["best_singleton"], "wall_s": time.perf_counter() - t0,
                         "n_history": len(g["history"]) + len(r.get("history", []))}
        hist_n += results[name]["n_history"]
        run.emit({"kind": "restart_result", "name": name, **{kk: v for kk, v in results[name].items() if kk != "path_k"}}, echo=True)
        if start is not None and start_status == BL.ERROR:
            reason = f"restart {name}: the start layout {start.key()} is an ERROR row (pricing failed); refusing to continue from empty"
            run.emit({"kind": "search_blocked", "reason": reason}, echo=True)
            raise SystemExit(reason)
    if a.dry_run:
        plan = {"kind": "search_dry_run", "warm": list(rules), "restarts": [n for n, _ in restarts], "n_cells_planned": ctx.n_cells}
        run.emit(plan, echo=True)
        return plan
    ok = {n: r for n, r in results.items() if r["layout_key"] is not None and r["V"] is not None}
    if not ok:
        raise SystemExit("no restart reached k sites")
    best_name = min(ok, key=lambda n: (ok[n]["V"], ok[n]["layout_key"]))
    best = BL.Layout.from_key(ok[best_name]["layout_key"])
    v_best = float(ok[best_name]["V"])
    # include the warm starts in the 'best found' comparison (a rule layout may win)
    for n, w in warm.items():
        if w.get("V") is not None and w["V"] < v_best - 1e-6:
            best_name, best, v_best = f"warm:{n}", BL.Layout.from_key(w["layout_key"]), float(w["V"])
    # 2. size polish at the best locations
    polished, v_pol, plog = polish_sizes(run, ctx, best, v_best)
    # 3. 'k units free': the budget reading of the same search (no force_k)
    free_start = start_m2 if start_m2 is not None else None
    g_free = BL.greedy_local_search(ev, ctx.cands, k * unit, start=free_start, force_k=None,
                                    on_step=lambda rec: run.emit({"kind": "search_step", "restart": "free", **rec}),
                                    **{**kw, "size_menu": ctx.menu, "moves": ("add", "drop", "swap", "size")})
    rf = g_free["per_budget"][k * unit]
    free = {"layout_key": None if rf["layout"] is None else rf["layout"].key(), "V": rf.get("value"), "status": rf["status"],
            "n_open": None if rf["layout"] is None else rf["layout"].n_open, "served_share": rf.get("served_share")}
    run.emit({"kind": "free_result", **free}, echo=True)
    # 4. V(k) path beyond k from the best found locations (no local search)
    ext = {}
    if ctx.k_max > k:
        g_ext = BL.greedy_local_search(ev, ctx.cands, ctx.k_max * unit, start=best, force_k=ctx.k_max,
                                       on_step=lambda rec: run.emit({"kind": "search_step", "restart": "extend", **rec}),
                                       **{**kw, "local_search": False})
        ext = {int(kk): list(v) for kk, v in g_ext["path_k"].items()}
    # V(k) layouts: k < k_main from the main path (m2 incumbent restart, else the first restart that has the point),
    # k = 1 from the best singleton of the 'empty' restart, k > k from the extension
    main = "m2_incumbent" if "m2_incumbent" in ok else best_name if best_name in ok else next(iter(ok))
    vk_layouts: Dict[int, Optional[str]] = {}
    for kk in range(1, ctx.k_max + 1):
        key = None
        for src in ([main] + [n for n in ok if n != main]):
            pk = ok[src]["path_k"]
            if kk in pk:
                key = pk[kk][0]
                break
        if key is None and kk == 1 and ok.get("empty", {}).get("best_singleton"):
            key = ok["empty"]["best_singleton"][0]
        if key is None and kk in ext:
            key = ext[kk][0]
        if kk == k:
            key = best.key()
        vk_layouts[kk] = key
    vk_missing = [kk for kk, v in vk_layouts.items() if v is None]
    if vk_missing:
        run.emit({"kind": "vk_missing", "k": vk_missing, "reason": "no restart produced a usable layout at these k "
                  "(every candidate layout INFEASIBLE or ERROR at this fleet); the V(k) rows stay absent from the final table"}, echo=True)
    summary = {"k": k, "k_max": ctx.k_max, "unit": unit, "option": list(ctx.option), "S_search": ctx.S_search, "vk_missing": vk_missing,
               "warm": {n: {"layout_key": w.get("layout_key"), "V": w.get("V"), "served_share": w.get("served_share")} for n, w in warm.items()},
               "restarts": results, "best_restart": best_name, "best_locations": {"layout_key": best.key(), "V": v_best},
               "best": {"layout_key": polished.key(), "V": v_pol}, "polish_log": plog, "free": free, "extension_path": ext,
               "vk_layouts": {str(kk): v for kk, v in vk_layouts.items()}, "n_cells": ctx.n_cells, "n_cells_solved": ctx.n_cells_solved,
               "proxy_calls": ctx.proxy.n_calls, "wall_s": time.perf_counter() - t_stage, "config_md5": run.config_md5,
               "cell_s_mean": (sum(ctx.cell_walls) / len(ctx.cell_walls)) if ctx.cell_walls else None,
               "cell_s_max": max(ctx.cell_walls, default=None), "worker_rss_gb_max": max(ctx.worker_rss, default=None)}
    _write_json(os.path.join(run.dir, "search_summary.json"), summary)
    run.emit({"kind": "search_result", "best_restart": best_name, "layout_key": polished.key(), "V": v_pol, "V_locations": v_best,
              "n_cells": ctx.n_cells, "wall_s": summary["wall_s"]}, echo=True)
    run.emit({"kind": "stage_done", "stage": "search"}, echo=True)
    return summary


# ---------------------------------------------------------------------------
# stage: final (in-sample + held-out, V(k), remove-one, per-site statistics, map contract)
# ---------------------------------------------------------------------------
def stage_final(run: Run, ctx: Ctx) -> Dict[str, Any]:
    a = run.args
    ctx.attach(("in", "out"))
    assert ctx.ev is not None
    summ_path = os.path.join(run.dir, "search_summary.json")
    if not os.path.exists(summ_path):
        if a.dry_run:                       # plan with the rule layouts as stand-ins for the search result
            rules = rule_layouts(ctx, ctx.k)
            n_lay = sum(1 for l in rules.values() if l is not None) + len(ctx.vk) + len(ctx.ref_layouts) + 2
            n_out = 0 if not ctx.held else len(ctx.held)
            plan = {"kind": "final_plan", "dry_run": True, "note": "search_summary.json missing: counts from the rule layouts",
                    "n_layouts": n_lay, "n_remove_one": ctx.k, "n_in": len(ctx.design), "n_out": n_out,
                    "n_cells_planned": n_lay * (len(ctx.design) + n_out) + ctx.k * len(ctx.design)}
            run.emit(plan, echo=True)
            return plan
        raise SystemExit("search_summary.json is missing: run --stage search first")
    summ = _read_json(summ_path)
    named: List[Tuple[str, BL.Layout]] = []

    def add(name: str, key: Optional[str]) -> None:
        if key and all(n != name for n, _ in named):
            try:
                named.append((name, BL.Layout.from_key(key)))
            except Exception:  # noqa: BLE001
                pass
    add("best", summ["best"]["layout_key"])
    add("best_locations", summ["best_locations"]["layout_key"])
    for n, r in summ["restarts"].items():
        add(f"restart:{n}", r.get("layout_key"))
    for n, w in summ["warm"].items():
        add(n, w.get("layout_key"))
    add("free", summ["free"].get("layout_key"))
    for kk in ctx.vk:
        add(f"V(k={kk})", summ["vk_layouts"].get(str(kk)))
    for n, key in ctx.ref_layouts.items():
        lay = ref_layout(ctx, key)
        if lay is not None:
            add(n, lay.key())
    best = BL.Layout.from_key(summ["best"]["layout_key"])
    remove = [(f"remove:{l}", best.drop(l)) for l in best.locations() if best.n_open > 1]
    plan = {"kind": "final_plan", "layouts": [(n, l.key()) for n, l in named], "n_remove_one": len(remove),
            "n_in": ctx.ev.n_scenarios, "n_out": (0 if ctx.ev_out is None else ctx.ev_out.n_scenarios)}
    run.emit(plan, echo=True)
    t0 = time.perf_counter()
    res_in = ctx.price(ctx.ev, named, tag="final_in")
    res_out = ctx.price(ctx.ev_out, named, tag="final_out") if ctx.ev_out is not None else {}
    res_rm = ctx.price(ctx.ev, remove, tag="remove_one")
    if a.dry_run:
        plan["n_cells_planned"] = ctx.n_cells
        return plan
    # paired regret against the best (in-sample and held-out)
    def paired(res: Dict[str, Dict[str, Any]], ev: OfflineEvaluator) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        b = res.get("best")
        if not b or not b.get("complete"):
            return out
        strata = [ctx.stratum_of(ev, s) for s in range(ev.n_scenarios)]
        for n, r in res.items():
            if not r.get("complete"):
                continue
            d = [float(x) - float(y) for x, y in zip(r["opex"], b["opex"])]
            ci = BL.stratified_ci(d, strata, ev.p)
            out[n] = {"regret": r["V"] - b["V"], "regret_ci": ci, "regret_pct": (100.0 * (r["V"] - b["V"]) / b["V"]) if b["V"] else None}
        return out
    regret_in = paired(res_in, ctx.ev)
    regret_out = paired(res_out, ctx.ev_out) if ctx.ev_out is not None else {}
    # per-site statistics and the remove-one marginal values
    table = ctx.per_site_table(ctx.ev, best)
    b_in = res_in["best"]
    strata = [ctx.stratum_of(ctx.ev, s) for s in range(ctx.ev.n_scenarios)]
    for l in best.locations():
        r = res_rm.get(f"remove:{l}")
        if r and r.get("complete") and b_in.get("complete") and l in table:
            d = [float(x) - float(y) for x, y in zip(r["opex"], b_in["opex"])]   # opex without the site - opex with it
            ci = BL.stratified_ci(d, strata, ctx.ev.p)
            marg = float(r["V"]) - float(b_in["V"])                               # positive = the site saves money
            table[l]["marginal_usd"] = marg
            table[l]["marginal_lo"] = None if ci["half"] is None else marg - ci["half"]
            table[l]["marginal_hi"] = None if ci["half"] is None else marg + ci["half"]
            table[l]["V_without"] = r["V"]
    # V(k) curve
    vk = []
    for kk in ctx.vk:
        r = res_in.get(f"V(k={kk})")
        if r:
            vk.append({"k": kk, "layout_key": r["layout_key"], "V": r.get("V"), "V_ci95": r.get("V_ci95"), "served_share": r.get("served_share"),
                       "V_out": (res_out.get(f"V(k={kk})") or {}).get("V"), "n_open": r.get("n_open")})
    # the map contract (design 6.1)
    layout_json = {"schema": SCHEMA15, "label": f"Best found, {best.n_open} sites", "demo": False, "run": os.path.basename(run.dir),
                   "family": ctx.family, "policy": "baseline", "variant": "r2", "n_bikes": ctx.n_bikes,
                   "grid_kw": float(ctx.spec.grid_kw), "site_kw": float(ctx.spec.P_kw),
                   "n_orders": int(round(sum(p * len(i.orders) for p, i in zip(ctx.p, ctx.scen)))),
                   "n_scenarios": ctx.ev.n_scenarios, "V": b_in.get("V"), "V_ci95": b_in.get("V_ci95"),
                   "served_share": b_in.get("served_share"), "investment_usd": best.investment(ctx.spec),
                   "candidates_csv": os.path.join(run.dir, "candidates.csv"),
                   "sites": [{"id": l, "role": r, "B": int(B), "C": int(Cc)} for l, r, B, Cc in best.open],
                   "V_out": (res_out.get("best") or {}).get("V"), "V_out_ci95": (res_out.get("best") or {}).get("V_ci95"),
                   "search": {"best_restart": summ.get("best_restart"), "S_search": summ.get("S_search"), "V_search": summ["best"]["V"]}}
    if not os.path.exists(layout_json["candidates_csv"]):
        S.write_candidate_tables(ctx.cands, ctx.dropped, run.dir)
    _write_json(os.path.join(run.dir, "layout.json"), layout_json)
    with open(os.path.join(run.dir, "site_stats.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SITE_STATS_COLUMNS))
        w.writeheader()
        for l, _r, _B, _C in best.open:
            t = table.get(l, {})
            row = {c: t.get(c) for c in SITE_STATS_COLUMNS}
            row["id"] = l
            row["n_scenarios"] = t.get("n_scenarios", ctx.ev.n_scenarios)
            w.writerow({c: ("" if v is None else (f"{v:.4f}" if isinstance(v, float) else v)) for c, v in row.items()})
    final = {"kind": "final", "best": b_in, "best_out": res_out.get("best"), "in_sample": res_in, "held_out": res_out,
             "remove_one": res_rm, "regret_in": regret_in, "regret_out": regret_out, "site_table": table, "vk": vk,
             "layout_json": layout_json, "n_cells": ctx.n_cells, "wall_s": time.perf_counter() - t0,
             "cell_s_mean": (sum(ctx.cell_walls) / len(ctx.cell_walls)) if ctx.cell_walls else None,
             "cell_s_max": max(ctx.cell_walls, default=None), "worker_rss_gb_max": max(ctx.worker_rss, default=None)}
    _write_json(os.path.join(run.dir, "final_summary.json"), final)
    run.emit({"kind": "final_result", "layout_key": best.key(), "V": b_in.get("V"), "V_out": layout_json["V_out"],
              "served_share": b_in.get("served_share"), "n_cells": ctx.n_cells, "wall_s": final["wall_s"]}, echo=True)
    run.emit({"kind": "stage_done", "stage": "final"}, echo=True)
    return final


# ---------------------------------------------------------------------------
# stage: report
# ---------------------------------------------------------------------------
def _fmt(x: Any, nd: int = 1) -> str:
    if x is None:
        return "--"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def _ci(rec: Dict[str, Any], key: str = "V_ci95", nd: int = 1) -> str:
    ci = rec.get(key)
    if not ci:
        return "--"
    return f"[{ci[0]:.{nd}f}, {ci[1]:.{nd}f}]"


def stage_report(run: Run, ctx: Ctx) -> str:
    a = run.args
    lines: List[str] = [f"# R8 fifteen-site study -- {os.path.basename(run.dir)}", "",
                        f"Family `{ctx.family}`, k = {ctx.k}, unit option {ctx.option}, lower level = rule-based rider module "
                        f"(`baseline.run_baseline` variant r2, every schedule certified by `evaluate.check`), open-sites tier, union "
                        f"arc library; search on scenarios {ctx.S_search}, final table on {len(ctx.design)} in-sample + {len(ctx.held)} "
                        f"held-out scenarios.  Values are USD per evening (window-allocated set-up + operating cost).  The best layout is "
                        f"'best found under the rule follower' (no certificate; design section 5).  Power: shared supply group "
                        f"of all sites capped at {ctx.spec.grid_kw:g} kW, each site at {ctx.spec.P_kw:g} kW.", ""]
    dry = os.path.join(run.dir, "dryrun.json")
    if os.path.exists(dry):
        d = _read_json(dry)
        lines += ["## Dry run (gates)", "", "| gate | value | limit | ok |", "|---|---|---|---|"]
        for name, g in d["gates"].items():
            lines.append(f"| {name} | {_fmt(g.get('max', g.get('value')), 2)} | {g['limit']} | {'yes' if g['ok'] else 'NO'} |")
        lines += ["", f"Layout {d['layout_key']}: V = {_fmt(d.get('V'))}, served {_fmt(d.get('served_share'), 3)}; "
                      f"median site swaps {_fmt(d.get('median_site_swaps'), 2)}; escalate = {d['escalate']} ({d['recommendation']}).", ""]
    val = os.path.join(run.dir, "validate.json")
    if os.path.exists(val):
        v = _read_json(val)
        lines += [f"## Rule follower against the exact aggregated ILP ({v.get('n_bikes')} riders, k = {v.get('k')}, "
                  f"{v.get('time_limit')} s, Threads {v.get('threads')})", "",
                  "Ratio = rule total / ILP incumbent total of the same cell with the cell's MIP gap (critic C6: no rank statistic).", "",
                  "| layout | scenario | rule | ILP incumbent | bound | gap | status | ratio |", "|---|---|---|---|---|---|---|---|"]
        for r in v["rows"]:
            lines.append(f"| {r['name']} | {r['scenario']} | {_fmt(r['rule_total'])} | {_fmt(r['ilp_incumbent'])} | {_fmt(r['ilp_bound'])} | "
                         f"{_fmt(r['ilp_gap'], 3)} | {r['ilp_status']} | {_fmt(r['ratio_rule_over_incumbent'], 3)} |")
        lines += ["", f"Ratio median {_fmt(v.get('ratio_median'), 3)} (min {_fmt(v.get('ratio_min'), 3)}, max {_fmt(v.get('ratio_max'), 3)}); "
                      f"gap median {_fmt(v.get('gap_median'), 3)}, max {_fmt(v.get('gap_max'), 3)}; {v.get('n_optimal')} of {v.get('n_cells')} cells OPTIMAL.", ""]
    summ_p = os.path.join(run.dir, "search_summary.json")
    if os.path.exists(summ_p):
        s = _read_json(summ_p)
        lines += ["## Search (6-scenario subset)", "", "| restart | start | result | V | status |", "|---|---|---|---|---|"]
        for n, r in s["restarts"].items():
            lines.append(f"| {n} | {r.get('start') or 'empty'} | {r.get('layout_key')} | {_fmt(r.get('V'))} | {r.get('status')} |")
        lines += ["", f"Best restart: {s['best_restart']}; best locations V = {_fmt(s['best_locations']['V'])}; after the size polish V = "
                      f"{_fmt(s['best']['V'])} ({s['best']['layout_key']}).  '{ctx.k} units free' (budget reading): "
                      f"{s['free'].get('layout_key')} with {s['free'].get('n_open')} sites, V = {_fmt(s['free'].get('V'))}.  "
                      f"{s['n_cells']} lower-level cells ({s['n_cells_solved']} solved), {s['proxy_calls']} proxy evaluations, "
                      f"wall {_fmt(s.get('wall_s'))} s; cell mean {_fmt(s.get('cell_s_mean'), 2)} s, max {_fmt(s.get('cell_s_max'), 2)} s, "
                      f"worker RSS max {_fmt(s.get('worker_rss_gb_max'), 2)} GB.", ""]
    fin_p = os.path.join(run.dir, "final_summary.json")
    if os.path.exists(fin_p):
        f = _read_json(fin_p)
        lines += ["## Final table (in-sample, stratified 95 % CI; held-out; regret against the best, paired stratified CI)", "",
                  "| layout | sites | V in | CI | served | V out | regret in | regret CI | regret out |", "|---|---|---|---|---|---|---|---|---|"]
        for n, r in f["in_sample"].items():
            ro = f["held_out"].get(n) or {}
            rg = f["regret_in"].get(n) or {}
            rgo = f["regret_out"].get(n) or {}
            ci = rg.get("regret_ci") or {}
            half = ci.get("half")
            lines.append(f"| {n} | {r.get('n_open')} | {_fmt(r.get('V'))} | {_ci(r)} | {_fmt(r.get('served_share'), 3)} | {_fmt(ro.get('V'))} | "
                         f"{_fmt(rg.get('regret'))} | {'--' if half is None else f'+-{half:.1f}'} | {_fmt(rgo.get('regret'))} |")
        lines += ["", "## V(k) curve (greedy path, re-priced on the in-sample scenarios)", "", "| k | layout | V in | CI | V out | served |",
                  "|---|---|---|---|---|---|"]
        for r in f["vk"]:
            lines.append(f"| {r['k']} | {r['layout_key']} | {_fmt(r.get('V'))} | {_ci(r)} | {_fmt(r.get('V_out'))} | {_fmt(r.get('served_share'), 3)} |")
        lines += ["", "## Per-site statistics of the best layout (p-weighted over the in-sample scenarios; removal = V without the site - V with it)", "",
                  "| site | swaps | CI | orders <= 1 km served / total | riders | busy | idle | kWh | wait min | stock-out slots | removal USD | CI |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for l, t in f["site_table"].items():
            lines.append(f"| {l} | {_fmt(t.get('swaps_mean'), 2)} | [{_fmt(t.get('swaps_lo'), 2)}, {_fmt(t.get('swaps_hi'), 2)}] | "
                         f"{_fmt(t.get('orders_1km_served'))} / {_fmt(t.get('orders_1km_total'))} | {_fmt(t.get('riders_distinct'))} | "
                         f"{_fmt(t.get('charger_busy_share'), 2)} | {_fmt(t.get('idle_share'), 2)} | {_fmt(t.get('kwh_bought'), 2)} | "
                         f"{_fmt(t.get('wait_min_mean'))} | {_fmt(t.get('stockout_slots'))} | {_fmt(t.get('marginal_usd'))} | "
                         f"[{_fmt(t.get('marginal_lo'))}, {_fmt(t.get('marginal_hi'))}] |")
        lj = f["layout_json"]
        lines += ["", f"Map inputs: `layout.json` (schema {lj['schema']}, V = {_fmt(lj.get('V'))}, served {_fmt(lj.get('served_share'), 3)}, "
                      f"investment {lj['investment_usd']:.0f} USD) and `site_stats.csv` in `{run.dir}` -> copy to `paper_itsc/figs/map15/` "
                      f"and run `make_figs.py map15`.", ""]
    cost = RC.summary_lines(os.path.join(run.dir, RC.COST_FILE))
    if cost:
        lines += cost
    txt = "\n".join(lines) + "\n"
    with open(os.path.join(run.dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write(txt)
    print(f"wrote {os.path.join(run.dir, 'RESULTS.md')}")
    _ = a
    return txt


# ---------------------------------------------------------------------------
# lanes (deploy/aws/run_lanes.sh format)
# ---------------------------------------------------------------------------
def write_lanes(args: argparse.Namespace) -> str:
    """Deploy-compatible lanes ``instances -> dryrun -> validate -> search -> final -> report`` for
    the r7i.4xlarge (dispatcher budget ``--max-threads`` 12, ``--max-rss-gb`` 110); every command
    carries ``R7_BATCH=k15`` and the instance price for ``cost.jsonl``."""
    usable = int(args.max_threads) if args.max_threads is not None else 12
    rss = args.max_rss_gb if args.max_rss_gb is not None else 110.0
    out_dir = args.out_dir or "outputs/r8_k15"
    inst, usd = args.instance, float(args.usd_per_h)
    W = max(1, min(int(args.workers), usable))
    VW, VT = int(args.validate_workers), int(args.validate_threads)
    while VW * VT > usable and VW > 1:
        VW -= 1
    tail = (f" --out-dir {out_dir} --family {args.family} --scenarios {int(args.scenarios)} --k {int(args.k)} --k-max {int(args.k_max)}"
            f" --max-rss-gb {rss:g}" + (f" --approach-radius {int(args.approach_radius)}" if args.approach_radius is not None else "")
            + (f" --dot-csv {args.dot_csv}" if args.dot_csv else "") + (f" --start-layout '{args.start_layout}'" if args.start_layout else "")
            + f" --vk {' '.join(str(int(x)) for x in args.vk)}")
    env = f"R7_BATCH=k15 R7_INSTANCE={inst} R7_USD_PER_H={usd:g} "
    lanes: List[Dict[str, Any]] = []

    def add(name: str, threads: int, after: str, stage: str, extra: str = "") -> None:
        cmd = env + f"python3 experiments/r8_k15.py --stage {stage} --workers {W} --max-threads {max(threads, 1)}{extra}{tail}"
        lanes.append({"name": name, "threads": int(threads), "after": after, "stage": stage, "command": cmd,
                      "hours": LANE_HOURS[stage], "usd": round(LANE_HOURS[stage] * usd, 2)})
    add("k15_instances", W, "-", "instances")
    add("k15_dryrun", W, "k15_instances", "dryrun")
    add("k15_validate", VW * VT, "k15_dryrun", "validate", f" --validate-workers {VW} --validate-threads {VT}")
    add("k15_search", W, "k15_dryrun", "search")            # validate is optional: its failure must not block the study
    add("k15_final", W, "k15_search", "final")
    add("k15_report", 1, "k15_final", "report")
    lanes_dir = os.path.abspath(args.lanes_dir) if args.lanes_dir else LANES_ROOT
    os.makedirs(lanes_dir, exist_ok=True)
    rel = os.path.relpath(lanes_dir, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tot_h = sum(l["hours"] for l in lanes)
    head = ["# R8 fifteen-site study lanes for deploy/aws/run_lanes.sh -- written by experiments/r8_k15.py --write-lanes",
            f"# plan: notes/siting15_design.md section 12.4; instance {inst} at {usd:g} USD/h, dispatcher budget {usable} threads, "
            f"--max-rss-gb {rss:g}; {W} worker PROCESSES per rule-follower stage (critic C1), {VW} x {VT} threads for the ILP check (C6)",
            f"# start on the server (project root, after deploy/aws/sync_up.sh): LANES_DIR=$PWD/ebike_swap_sim/{rel} "
            f"bash deploy/aws/run_lanes.sh start ebike_swap_sim/{rel}/lanes.txt --max-threads {usable}",
            "# chain: instances -> dryrun -> {validate, search} -> final -> report; search waits for dryrun only (the optional ILP "
            "check cannot block the study; the thread budget still serialises it behind validate); every command appends to "
            f"{out_dir}/cost.jsonl (R7_BATCH=k15); re-run 'run_lanes.sh start' after a stop: every stage resumes from cache/",
            "# --max-rss-gb guards the parent RSS plus workers x the largest worker RSS of the previous cell batch (first batch: parent only);"
            " the dry run gates every worker at 4 GB",
            "# gates: k15_search refuses to start when dryrun.json says escalate (then 64 riders / 320 orders, design 12.2)",
            "# format: name <TAB> threads <TAB> after <TAB> command (bash, from the package root)",
            f"# total about {tot_h:.1f} h = {tot_h * usd:.1f} USD before the 30 % contingency (design 12.4: about 7 h = 7.5 USD)"]
    lines = list(head)
    for l in lanes:
        lines.append(f"# {l['name']}: stage {l['stage']}, about {l['hours']} h = {l['usd']} USD")
        lines.append("\t".join([l["name"], str(l["threads"]), l["after"], l["command"]]))
    path = os.path.join(lanes_dir, "lanes.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(lanes_dir, "lanes.json"), "w", encoding="utf-8") as fh:
        json.dump({"lanes": lanes, "instance": inst, "usd_per_h": usd, "usable_threads": usable, "max_rss_gb": rss, "out_dir": out_dir,
                   "workers": W, "validate_workers": VW, "validate_threads": VT, "total_hours": tot_h, "total_usd": round(tot_h * usd, 2)},
                  fh, indent=1)
    print(f"wrote {path} ({len(lanes)} lanes, about {tot_h:.1f} h = {tot_h * usd:.1f} USD)")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage", default="all", help="comma-separated stages or 'all': " + ", ".join(STAGES))
    ap.add_argument("--smoke", action="store_true", help="toy instance (four candidates, k = 2), seconds")
    ap.add_argument("--dry-run", action="store_true", help="plans and cell counts only, no solve")
    ap.add_argument("--redo", action="store_true", help="re-run stages that have a stage_done record")
    ap.add_argument("--family", default=S.MANHATTAN15_FAMILY, choices=[S.MANHATTAN15_FAMILY, S.MANHATTAN_DOT_FAMILY])
    ap.add_argument("--dot-csv", default=None)
    ap.add_argument("--merge-m", type=float, default=80.0)
    ap.add_argument("--cap", type=int, default=60)
    ap.add_argument("--reduced", type=int, default=None, help="use only the first N candidates (probes)")
    ap.add_argument("--scenarios", type=int, default=12, help="stratified design size (6, 10, 12, 15)")
    ap.add_argument("--n-bikes", type=int, default=None, help="override the family fleet (default: the family's n_bikes)")
    ap.add_argument("--approach-radius", type=int, default=14, help="moves into candidates only from within N blocks (-1 = off)")
    ap.add_argument("--k", type=int, default=15, help="exactly this many open sites")
    ap.add_argument("--k-max", type=int, default=20, help="V(k) path continued to this k")
    ap.add_argument("--vk", nargs="*", type=int, default=[1, 2, 5, 10, 15, 20], help="k values of the V(k) table")
    ap.add_argument("--start-layout", default=REF_LAYOUTS["prod_m2"], help="m = 2 incumbent (layout key) of the forward selection")
    ap.add_argument("--k-screen", type=int, default=3, help="layouts priced per step after the proxy screen")
    ap.add_argument("--max-passes", type=int, default=5, help="local search passes at fixed k")
    ap.add_argument("--swap-nearest", type=int, default=3)
    ap.add_argument("--swap-proxy-best", type=int, default=5)
    ap.add_argument("--polish-rounds", type=int, default=3)
    ap.add_argument("--kmedian-time-limit", type=float, default=60.0)
    ap.add_argument("--dryrun-layout", default=None, help="layout key of the dry run (default CSCD-k)")
    ap.add_argument("--ignore-gates", action="store_true", help="run the search although a dry-run gate failed")
    ap.add_argument("--grid-kw", type=float, default=None,
                    help="cap of the shared supply group of all sites in kW (default: the family value, 2 kW for manhattan15); a large value such as 1000 removes the shared feeder and leaves every site its own P_kw limit")
    ap.add_argument("--validate-k", type=int, default=5)
    ap.add_argument("--validate-bikes", type=int, default=16)
    ap.add_argument("--validate-scenarios", type=int, default=3)
    ap.add_argument("--validate-time-limit", type=float, default=1800.0)
    ap.add_argument("--validate-threads", type=int, default=3)
    ap.add_argument("--validate-workers", type=int, default=4)
    ap.add_argument("--validate-skip-verify", action="store_true", help="skip Gurobi's fix-and-solve check of a clean rule start")
    ap.add_argument("--time-limit", type=float, default=300.0, help="(unused by the rule follower; the evaluator protocol)")
    ap.add_argument("--workers", type=int, default=8, help="worker PROCESSES of the pool (critic C1)")
    ap.add_argument("--start-method", choices=["fork", "spawn", "forkserver"], default="fork")
    ap.add_argument("--worker-keep", type=int, default=2, help="scenario instances a worker keeps loaded (LRU)")
    ap.add_argument("--max-threads", type=int, default=None, help="thread budget of this process (lanes)")
    ap.add_argument("--max-rss-gb", type=float, default=None, help="abort before a batch when the parent RSS plus workers x the last batch's largest worker RSS exceeds it")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--write-lanes", action="store_true")
    ap.add_argument("--lanes-dir", default=None)
    ap.add_argument("--instance", default=RC.DEFAULT_INSTANCE, help="--write-lanes: instance type for cost.jsonl")
    ap.add_argument("--usd-per-h", type=float, default=RC.DEFAULT_USD_PER_H, help="--write-lanes: price for cost.jsonl")
    return ap


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    args = build_parser().parse_args(argv)
    if args.approach_radius is not None and int(args.approach_radius) < 0:
        args.approach_radius = None
    if args.smoke:
        args.k = 2 if args.k == 15 else args.k
        args.k_max = 3 if args.k_max == 20 else args.k_max
        args.vk = [1, 2, 3] if args.vk == [1, 2, 5, 10, 15, 20] else args.vk
        args.workers = min(int(args.workers), 2)
        args.validate_k = min(int(args.validate_k), 2)
        args.validate_bikes = TOY_BIKES
        args.validate_scenarios = 2
        args.validate_time_limit = min(float(args.validate_time_limit), 30.0)
        args.validate_threads = 1
        args.validate_workers = min(int(args.validate_workers), 2)
        args.kmedian_time_limit = min(float(args.kmedian_time_limit), 10.0)
        args.approach_radius = None
    return args


def main(argv: Optional[List[str]] = None) -> Any:
    args = parse_args(argv)
    if args.write_lanes:
        return write_lanes(args)
    stages = list(STAGES) if args.stage == "all" else [s.strip() for s in args.stage.split(",") if s.strip()]
    for st in stages:
        if st not in STAGES:
            raise SystemExit(f"unknown stage {st!r}; choose from {STAGES}")
    if args.max_threads is not None:
        pool_stage = any(st in ("instances", "dryrun", "search", "final") for st in stages)
        need = max(([int(args.workers)] if pool_stage else []) +
                   ([int(args.validate_workers) * int(args.validate_threads)] if "validate" in stages else []) + [0])
        if need > int(args.max_threads):
            raise SystemExit(f"workers ({need}) exceed --max-threads {args.max_threads}")
    warnings.simplefilter("ignore")
    run = Run(args)
    cost = RC.CostLog(run.dir, ",".join(stages), "r8_k15.py", dry_run=bool(args.dry_run), argv=argv,
                      enabled=not all(st in ("report",) for st in stages))
    cost.install_signal_handlers()
    status = "error"
    try:
        ctx = Ctx(run)
        out: Dict[str, Any] = {}
        for st in stages:
            run.stage = st
            if st == "instances":
                ctx.run.config_md5 = ctx.config_md5()
            else:
                ctx.attach(("in",))
            md5 = run.config_md5
            if st not in ALWAYS_RUN and not args.dry_run and not args.redo and stage_done(run.load(), st, md5):
                run.emit({"kind": "stage_skipped", "stage": st, "reason": "stage_done record with the same configuration"}, echo=True)
                continue
            t0 = time.perf_counter()
            fn = {"instances": stage_instances, "dryrun": stage_dryrun, "validate": stage_validate, "search": stage_search,
                  "final": stage_final, "report": stage_report}[st]
            out[st] = fn(run, ctx)
            if not args.dry_run:
                with open(os.path.join(run.dir, "wall_time.json"), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"stage": st, "wall_s": time.perf_counter() - t0, "rss_gb": rss_gb(),
                                         "n_cells": ctx.n_cells, "finished": time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
        status = "ok"
        return out
    except BaseException as exc:  # noqa: BLE001 -- recorded in cost.jsonl, then re-raised
        status = f"error: {type(exc).__name__}"
        raise
    finally:
        close_pool()
        cost.finish(status)


if __name__ == "__main__":
    main()
