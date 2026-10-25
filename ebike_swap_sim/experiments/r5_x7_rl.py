"""Round 5, experiment X7 -- the A7 RL comparator against the rule policies and the ILP
(``notes/reading_to_model.md`` item A7; IJCAI-25 Sec. 4.1 protocol, plain PPO-clip).

Families (byte-identical instances for every method; demand md5 asserted per (family, seed)):

* ``nyc4h_stress2`` (semi-real, as built: 6 bikes / 36 orders / H 48, 3 sites B 1 / C 1);
* ``r5_stress4h``   (round-5 main family: 6 bikes / 48 orders / H 48 / L 24, 3 sites B 2 / C 1).

Methods per (family, test seed 0-9), all on the M1 relaxed control (``rho = R_end_j = 0``,
``common.relax_end_targets`` = the ``rho0_R0`` cell of ``common.boundary_grid``) unless stated:

* rule policies (``common.run_baseline_case``, written DEMAND_AWARE reserve kept on the copy):
  ``rule_r2`` (DECISIONS R2.3), ``rule_r5_range`` (M2), ``rule_r5_transfer`` (M3, only when the
  instance has services), ``rule_r5`` (M2 + M3), and ``rule_r5_selfish`` (M4, informational, not in
  ``best_rule``); the derived row ``best_rule`` = per-instance minimum over r2, r5_range,
  r5_transfer (when services exist) and r5 of ``total_end_adjusted`` (the conservative comparison);
* the A7 PPO-clip station agent (``rl_env.StationEnv``) trained for ``--timesteps`` (200 k) on
  the training seeds 1000-1019 for EACH rider layer ``r2`` and ``r5`` (``rl_ppo[r2]``,
  ``rl_ppo[r5]``), evaluated deterministically; with it the in-environment replay of the rule
  station layer (``replay[rider]``, parity check against ``rule_<rider>``) and the station
  heuristics ``heuristic_none[rider]`` / ``heuristic_asap[rider]``;
* ``ilp_relaxed``: the E2 ILP on the relaxed copy, aggregated flow (O1, ``aggregate=True``),
  Gurobi Threads 3, Seed 0, TimeLimit ``--ilp-time-limit`` (120 s), MIP start = the cheapest
  rule schedule without violated families (else ``common.feasible_mip_start``);
* ``ilp_written``: the same ILP with the written targets (17)-(18) (``rho = 0.5``, ``R_end = 1``),
  run LAST (lowest priority); ``price_of_recovery = ilp_written - ilp_relaxed``.  The rule and RL
  schedules do not depend on the targets (the policies enforce neither (17) nor (18)), so their
  rows serve both comparisons.

Headline (relaxed control): ``gap_ilp_pct = 100 (policy - ILP) / policy`` on the E2 total (26)
and ``gap_ilp_end_adj_pct`` on ``total_end_adjusted`` = (26) + ``C_end_adjust`` (M1), reported for
every policy row; RL vs rule as paired differences with 95 % Student-t CIs over seeds.  Every row
carries the (26)-(32) components, ``C_end_adjust``, the A3 metric pack (``common.flatten_r5`` ->
``r5_*`` columns), the violated families and ``demand_md5``.

Protocol: append-only ``records.jsonl`` (resume by key ``(kind, family, seed, method)``),
``results.csv`` refreshed after every run (raw rows + derived ``best_rule`` + gaps),
``summary.csv`` / ``RESULTS.md`` at the end (or ``--analyse``), ``run_stdout.log`` (one line per
run), ``wall_time.json``; ``common.WallBudget`` (default 240 min): an ILP gets
``min(TimeLimit, remaining - margin)`` or is recorded as ``SKIPPED_BUDGET``; PPO training stops
early (``TRUNCATED_BUDGET``, model saved, re-trained on resume) when the remaining budget falls
below the reserve kept for the later phases.  Order of work: per family (rules, ILP relaxed,
train + evaluate r2, train + evaluate r5), then ILP written for both families.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/r5_x7_rl.py --dry-run          # plan + expected wall time, nothing solved
    python3 experiments/r5_x7_rl.py --smoke --out /tmp/x7_smoke   # 2 k steps, seed 0, TL 30 s
    python3 experiments/r5_x7_rl.py                    # full run (resumable)
    python3 experiments/r5_x7_rl.py --analyse          # tables only
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance, cost, metrics  # noqa: E402
from ebike_swap_sim.evaluate import check  # noqa: E402
from experiments import a7_rl as A7  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "r5_x7_rl")
RECORDS = "records.jsonl"
FAMILIES: Tuple[str, ...] = ("nyc4h_stress2", "r5_stress4h")
RIDERS: Tuple[str, ...] = ("r2", "r5")
#: rule variants -> ``common.BASELINE_VARIANTS`` key; ``r5_transfer`` only with services
RULES: Dict[str, str] = {"r2": "baseline", "r5_range": "baseline_r5_range",
                         "r5_transfer": "baseline_r5_transfer", "r5": "baseline_r5",
                         "r5_selfish": "baseline_r5_selfish"}
BEST_RULE_OVER: Tuple[str, ...] = ("r2", "r5_range", "r5_transfer", "r5")
TRAIN_SEEDS = "1000:1020"
TEST_SEEDS = "0:10"
TIMESTEPS = 200_000
PPO_SEED = 0
ILP_TIME_LIMIT = 120.0
WALL_BUDGET_MIN = 240.0
HEURISTICS: Tuple[str, ...] = ("none", "asap")
#: training-env instance handling (a7_rl defaults are 8 / 4): rebuilding the arc library
#: (3 s on r5_stress4h, 2.4 M arcs, about 0.45 GB) dominates the training wall time, so 8 of
#: the 20 training instances are kept in memory and each is used for 16 consecutive episodes
EPISODES_PER_INSTANCE = 16
CACHE_SIZE = 8
#: expected wall seconds per item (calibrated by the smoke run / R5 probe; for --dry-run)
EXPECT_S: Dict[str, Dict[str, float]] = {
    # calibrated 2026-10-17 (smoke + probes, Threads 3): relaxed aggregated ILP OPTIMAL in 3 s
    # (nyc4h_stress2) / 57 s (r5_stress4h); PPO training 270 / 130 steps/s over the first 20 k steps
    # (instance generation included), faster once the training instances are cached
    "nyc4h_stress2": {"ilp_relaxed": 6.0, "ilp_written": 6.0, "train_steps_per_s": 330.0, "instance": 3.0},
    "r5_stress4h": {"ilp_relaxed": 70.0, "ilp_written": 80.0, "train_steps_per_s": 170.0, "instance": 5.0},
    "_default": {"ilp_relaxed": 90.0, "ilp_written": 100.0, "train_steps_per_s": 150.0, "instance": 5.0},
}
EXPECT_RULE_S = 2.0      # all rule variants of one seed
EXPECT_RL_EVAL_S = 3.0   # the four episodes of one seed and rider


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def key_of(r: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (str(r["kind"]), str(r["family"]), str(r["seed"]), str(r["method"]))


def last_per_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for r in rows:
        out[key_of(r)] = r
    return out


class Ctx:
    """Run context: output paths, records, wall budget, settings."""

    def __init__(self, a: argparse.Namespace) -> None:
        self.a = a
        mk = (lambda p: p) if a.dry_run else C.ensure_dir     # --dry-run creates nothing
        self.out = mk(a.out)
        self.records_path = os.path.join(self.out, RECORDS)
        self.log_path = os.path.join(self.out, "run_stdout.log")
        self.inst_dir = mk(os.path.join(self.out, "instances"))
        self.model_root = mk(os.path.join(self.out, "models"))
        self.rows: List[Dict[str, Any]] = C.load_jsonl(self.records_path)
        self.done = last_per_key(self.rows)
        self.budget = C.WallBudget(a.wall_budget_min * 60.0, margin_s=60.0, min_solve_s=20.0)
        self.md5: Dict[Tuple[str, int], str] = {}
        for r in self.rows:
            if r.get("demand_md5") and str(r.get("seed")).lstrip("-").isdigit():
                self.md5.setdefault((r["family"], int(r["seed"])), r["demand_md5"])
        self.t_start = time.strftime("%Y-%m-%d %H:%M:%S")

    def log(self, msg: str) -> None:
        line = f"[x7 {self.budget.elapsed() / 60.0:6.1f} min] {msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def add(self, row: Dict[str, Any]) -> None:
        row = dict(row)
        row.setdefault("smoke", bool(self.a.smoke))
        C.append_jsonl(self.records_path, row)
        row["wall_clock"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.rows.append(C.jsonable(row))
        self.done[key_of(row)] = self.rows[-1]
        write_results(self)

    def check_md5(self, family: str, seed: int, inst: Instance) -> str:
        md5 = C.demand_md5(inst)
        prev = self.md5.setdefault((family, int(seed)), md5)
        assert prev == md5, f"demand md5 changed for {family} seed {seed}: {prev} vs {md5}"
        return md5


# ---------------------------------------------------------------------------
# instances
# ---------------------------------------------------------------------------
def load_written(family: str, seed: int, cache_dir: str) -> Instance:
    """Written-target instance of ``family`` / ``seed`` with a JSON cache (``Instance.save`` /
    ``load`` round-trip byte-identically); same file naming as ``a7_rl.cached_factory``."""
    path = os.path.join(cache_dir, f"{family}_seed{int(seed)}.json")
    if os.path.exists(path):
        return Instance.load(path)
    inst = C.make_instance(family, int(seed))
    inst.save(path)
    return inst


def load_case(family: str, seed: int, cache_dir: str, relaxed: bool = True):
    """``(instance, library)``: the relaxed copy (M1 headline control) or the written instance,
    library with ``common.pruning_for`` (the family's ILP pruning)."""
    inst = load_written(family, seed, cache_dir)
    if relaxed:
        inst = C.relax_end_targets(inst)
    lib, _ = C.build_library(inst, C.pruning_for(inst))
    return inst, lib


def make_factory(family: str, cache_dir: str):
    def factory(seed: int):
        return load_case(family, int(seed), cache_dir, relaxed=True)
    factory.family = family  # type: ignore[attr-defined]
    return factory


# ---------------------------------------------------------------------------
# rows
# ---------------------------------------------------------------------------
def schedule_row(kind: str, family: str, seed: int, method: str, inst, lib, sched,
                 runtime: float, md5: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Flat record of one schedule: (26)-(32) + C_end_adjust (evaluate.cost), A7 adjusted
    total (rl_env convention), A3 metric pack, violated families, served share."""
    from ebike_swap_sim.rl_env import adjusted_cost
    c = cost(inst, lib, sched)
    rep = check(inst, lib, sched)
    fams = C.family_counts(rep)
    met = metrics(inst, lib, sched)
    row: Dict[str, Any] = {
        "kind": kind, "family": family, "seed": int(seed), "method": method,
        "boundary_variant": inst.meta.get("boundary_variant", "written"),
        "status": "POLICY" if kind != "ilp" else None,
        "demand_md5": md5, "n_bikes": len(inst.bikes), "n_orders": len(inst.orders),
        "n_services": len(inst.services), "n_arcs": len(lib),
        **C.flatten_cost(c),
        "a7_end_adj": adjusted_cost(inst, lib, sched)["end_adj"],
        "families": fams, "ok": rep["ok"],
        "ok_modulo_report_only": all(f in C.BASELINE_REPORT_ONLY for f in fams),
        "served_share": met["served_share"], "n_served": met["n_served"], "n_swaps": met["n_swaps"],
        "kwh_purchased": met["kwh_purchased"], "runtime_s": float(runtime),
        **C.flatten_r5(met),
    }
    row["a7_adjusted_total"] = row["total"] + row["a7_end_adj"]
    row.update(extra or {})
    return row


def _maxrss_gb() -> float:
    """Peak resident memory of this process in GB (macOS reports bytes, Linux KiB)."""
    import resource
    v = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return v / 1e9 if sys.platform == "darwin" else v / 1e6


def skipped_row(kind: str, family: str, seed: Any, method: str, status: str, **extra: Any) -> Dict[str, Any]:
    return {"kind": kind, "family": family, "seed": seed, "method": method, "status": status, **extra}


def fmt_line(r: Dict[str, Any]) -> str:
    tot, adj = r.get("total"), r.get("total_end_adjusted")
    s = f"{r['family']} seed {r['seed']} {r['method']}: status {r.get('status')}"
    if tot is not None:
        s += f", total {tot:.2f}, end-adjusted {adj:.2f}, served {r.get('served_share', float('nan')):.3f}"
    if r.get("gap") is not None:
        s += f", MIP gap {100 * float(r['gap']):.2f} %"
    if r.get("runtime_s") is not None:
        s += f", {float(r['runtime_s']):.1f} s"
    return s


# ---------------------------------------------------------------------------
# phases
# ---------------------------------------------------------------------------
def rule_names(inst: Instance) -> List[str]:
    return [n for n in RULES if n != "r5_transfer" or len(inst.services) > 0]


def _rule_done(ctx: Ctx, family: str, seed: int, name: str) -> bool:
    return ("rule", family, str(seed), f"rule_{name}") in ctx.done


def _ilp_done(ctx: Ctx, family: str, seed: int, method: str) -> bool:
    r = ctx.done.get(("ilp", family, str(seed), method))
    return r is not None and r.get("status") not in (C.SKIPPED_BUDGET, "ERROR")


def phase_rules_and_ilp(ctx: Ctx, family: str, seeds: Sequence[int]) -> None:
    """Rule rows and the relaxed ILP per test seed (one instance / library per seed)."""
    a = ctx.a
    for s in seeds:
        need_ilp = not a.no_ilp and not _ilp_done(ctx, family, s, "ilp_relaxed")
        rules_done = (all(_rule_done(ctx, family, s, n) for n in RULES if n != "r5_transfer")
                      and (_rule_done(ctx, family, s, "r5_transfer") or not _needs_transfer_rule(ctx, family, s)))
        if rules_done and not need_ilp:
            continue
        inst, lib = load_case(family, s, ctx.inst_dir, relaxed=True)
        md5 = ctx.check_md5(family, s, inst)
        rule_recs: Dict[str, Any] = {}
        for name in rule_names(inst):
            vkey = RULES[name]
            try:
                rec = C.run_baseline_case(inst, lib, C.baseline_variant_params(vkey, inst), label=vkey)
            except Exception as exc:  # noqa: BLE001 - record and continue
                if not _rule_done(ctx, family, s, name):
                    ctx.add(skipped_row("rule", family, s, f"rule_{name}", "ERROR", error=f"{type(exc).__name__}: {exc}"))
                    ctx.log(f"{family} seed {s} rule_{name}: ERROR {exc}")
                continue
            rule_recs[name] = rec
            if not _rule_done(ctx, family, s, name):
                row = schedule_row("rule", family, s, f"rule_{name}", inst, lib, rec["schedule"], rec["runtime"], md5,
                                   {"rule_variant": vkey, "policy_reserve_source": rec["policy_reserve_source"],
                                    "pruning_flags": rec["pruning_flags"]})
                ctx.add(row)
                ctx.log(fmt_line(row))
        if need_ilp:
            run_ilp(ctx, family, s, inst, lib, md5, "ilp_relaxed", rule_recs)
        del inst, lib


def _needs_transfer_rule(ctx: Ctx, family: str, seed: int) -> bool:
    """True when a stored rule row says the instance has services (r5_transfer applies)."""
    r = ctx.done.get(("rule", family, str(seed), "rule_r2"))
    return bool(r and int(r.get("n_services") or 0) > 0)


def pick_mip_start(inst, lib, rule_recs: Dict[str, Any]):
    """Cheapest (E2 total) rule schedule with no violated family on ``inst``; else
    ``common.feasible_mip_start`` from the r2 rule record."""
    clean = [(rec["cost"]["total"], name, rec) for name, rec in rule_recs.items() if not rec["families"]]
    if clean:
        clean.sort(key=lambda x: x[0])
        return clean[0][2]["schedule"], f"rule_{clean[0][1]}"
    base = rule_recs.get("r2") or C.run_baseline_case(inst, lib)
    sched, name = C.feasible_mip_start(inst, lib, base)
    return sched, name


def run_ilp(ctx: Ctx, family: str, seed: int, inst, lib, md5: str, method: str,
            rule_recs: Optional[Dict[str, Any]] = None) -> None:
    a = ctx.a
    tl = ctx.budget.solve_limit(a.ilp_time_limit)
    if tl is None:
        row = skipped_row("ilp", family, seed, method, C.SKIPPED_BUDGET, demand_md5=md5)
        ctx.add(row)
        ctx.log(fmt_line(row))
        return
    if rule_recs is None:
        rule_recs = {}
        for name in ("r2", "r5"):
            try:
                rule_recs[name] = C.run_baseline_case(inst, lib, C.baseline_variant_params(RULES[name], inst))
            except Exception:  # noqa: BLE001
                pass
    start, start_name = pick_mip_start(inst, lib, rule_recs)
    try:
        rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=tl, threads=C.THREADS, label=method,
                             params=dict(C.ILP_PARAMS_R3), **C.R5_ILP_KWARGS)
    except Exception as exc:  # noqa: BLE001 - record and continue
        row = skipped_row("ilp", family, seed, method, "ERROR", error=f"{type(exc).__name__}: {exc}",
                          demand_md5=md5, time_limit=tl)
        ctx.add(row)
        ctx.log(fmt_line(row) + f" ({exc})")
        return
    extra = {"status": rec["status"], "obj": rec["obj"], "bound": rec["bound"], "gap": rec["gap"],
             "time_limit": tl, "time_limit_requested": a.ilp_time_limit, "threads": C.THREADS,
             "gurobi_seed": C.ILP_PARAMS_R3.get("Seed"), "aggregate": True,
             "build_time_s": rec["build_time"], "n_vars": rec["n_vars"], "n_binaries": rec["n_binaries"],
             "mip_start": start_name, "mip_start_accepted": rec["mip_start_accepted"]}
    if rec["schedule"] is None:
        row = skipped_row("ilp", family, seed, method, rec["status"], demand_md5=md5,
                          runtime_s=rec["runtime"], **{k: v for k, v in extra.items() if k != "status"})
    else:
        row = schedule_row("ilp", family, seed, method, inst, lib, rec["schedule"], rec["runtime"], md5, extra)
    ctx.add(row)
    ctx.log(fmt_line(row))


def model_dir(ctx: Ctx, family: str, rider: str) -> str:
    return C.ensure_dir(os.path.join(ctx.model_root, f"{family}_{rider}"))


def train_done(ctx: Ctx, family: str, rider: str) -> Optional[Dict[str, Any]]:
    r = ctx.done.get(("train", family, "train", f"ppo[{rider}]"))
    if r and r.get("status") == "TRAINED" and os.path.exists(r.get("model_path", "")):
        return r
    return None


def train_policy(ctx: Ctx, family: str, rider: str, reserve_s: float) -> Optional[Dict[str, Any]]:
    """PPO-clip training of the A7 station agent (``a7_rl.PPO_DEFAULTS``, torch Threads 3,
    seed ``PPO_SEED``) with a wall-budget stop; appends the ``train`` record."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from ebike_swap_sim.rl_env import EnvConfig, StationEnv

    a = ctx.a
    method = f"ppo[{rider}]"
    if ctx.budget.remaining() - reserve_s < a.min_train_min * 60.0:
        row = skipped_row("train", family, "train", method, C.SKIPPED_BUDGET, rider_variant=rider)
        ctx.add(row)
        ctx.log(f"{family} train {method}: SKIPPED_BUDGET")
        return None
    A7._set_threads()
    od = model_dir(ctx, family, rider)
    hp = {**A7.PPO_DEFAULTS}
    net_arch = hp.pop("net_arch")
    train_seeds = A7.parse_seeds(a.train_seeds)
    cfg = EnvConfig(rider_variant=rider, seeds=tuple(train_seeds), episodes_per_instance=a.episodes_per_instance,
                    cache_size=a.cache_size,
                    reward_scale=0.1, shuffle=True)
    monitor_path = os.path.join(od, "monitor.csv")
    factory = make_factory(family, ctx.inst_dir)

    def _make():
        return Monitor(StationEnv(factory=factory, config=cfg), filename=monitor_path)

    budget = ctx.budget

    class _BudgetStop(BaseCallback):
        def _on_step(self) -> bool:
            return budget.remaining() > reserve_s

    venv = VecNormalize(DummyVecEnv([_make]), norm_obs=False, norm_reward=True, gamma=hp["gamma"])
    venv.seed(PPO_SEED)
    model = PPO("MlpPolicy", venv, seed=PPO_SEED, device="cpu", verbose=0,
                policy_kwargs={"net_arch": list(net_arch)}, **hp)
    t0 = time.perf_counter()
    model.learn(total_timesteps=int(a.timesteps), callback=_BudgetStop())
    wall = time.perf_counter() - t0
    done_steps = int(model.num_timesteps)
    model_path = os.path.join(od, "ppo_station.zip")
    model.save(model_path)
    venv.save(os.path.join(od, "vecnormalize.pkl"))
    ep = pd.read_csv(monitor_path, skiprows=1) if os.path.exists(monitor_path) else pd.DataFrame()
    status = "TRAINED" if done_steps >= int(a.timesteps) else "TRUNCATED_BUDGET"
    train_id = f"{family}_{rider}_{time.strftime('%Y%m%dT%H%M%S')}"
    row = {"kind": "train", "family": family, "seed": "train", "method": method, "status": status,
           "rider_variant": rider, "train_id": train_id, "timesteps_target": int(a.timesteps),
           "timesteps_done": done_steps, "train_seeds": train_seeds, "ppo_seed": PPO_SEED,
           "ppo": {**hp, "net_arch": list(net_arch)}, "episodes_per_instance": a.episodes_per_instance, "cache_size": a.cache_size,
           "reward_scale": 0.1, "relax_targets": True, "torch_threads": C.THREADS,
           "runtime_s": wall, "steps_per_s": done_steps / max(wall, 1e-9), "model_path": model_path,
           "n_episodes": int(len(ep)),
           "return_first100": float(ep["r"].head(100).mean()) if len(ep) else None,
           "return_last100": float(ep["r"].tail(100).mean()) if len(ep) else None,
           "action_space": str(venv.action_space), "obs_dim": int(venv.observation_space.shape[0]),
           "maxrss_gb": _maxrss_gb()}
    venv.close()
    ctx.add(row)
    ctx.log(f"{family} train {method}: {status}, {done_steps} steps in {wall:.1f} s "
            f"({row['steps_per_s']:.0f} steps/s), return first/last 100 episodes "
            f"{row['return_first100']} / {row['return_last100']}")
    return row


def evaluate_rl(ctx: Ctx, family: str, rider: str, train_row: Dict[str, Any], seeds: Sequence[int]) -> None:
    """Deterministic RL episodes + replay + heuristics per test seed (same cached instance)."""
    from stable_baselines3 import PPO
    from ebike_swap_sim.rl_env import EnvConfig, StationEnv

    A7._set_threads()
    tid = train_row["train_id"]

    def todo(s: int, m: str) -> bool:
        r = ctx.done.get(("rl", family, str(s), m))
        return r is None or r.get("train_id") != tid

    methods = {"rl": f"rl_ppo[{rider}]", "replay": f"replay[{rider}]",
               **{h: f"heuristic_{h}[{rider}]" for h in HEURISTICS}}
    seeds_todo = [s for s in seeds if any(todo(s, m) for m in methods.values())]
    if not seeds_todo:
        return
    model = PPO.load(train_row["model_path"], device="cpu")
    env = StationEnv(factory=make_factory(family, ctx.inst_dir),
                     config=EnvConfig(rider_variant=rider, seeds=tuple(seeds_todo), cache_size=1, shuffle=False))
    for s in seeds_todo:
        inst, lib = env._load(int(s))  # noqa: SLF001 - the episode instance itself
        md5 = ctx.check_md5(family, s, inst)
        rule = ctx.done.get(("rule", family, str(s), f"rule_{rider}"))
        for pol, m in methods.items():
            if not todo(s, m):
                continue
            ep = A7.run_env_episode(env, int(s), pol, model)
            assert env.inst is inst, "episode instance differs from the evaluated one"
            extra = {"rider_variant": rider, "station_policy": pol, "train_id": tid,
                     "model_timesteps": train_row["timesteps_done"], "train_status": train_row["status"],
                     "episode_return": ep["return"]}
            row = schedule_row("rl", family, s, m, inst, lib, ep["schedule"], ep["runtime"], md5, extra)
            if pol == "replay" and rule and rule.get("total") is not None:
                row["parity_with_rule"] = abs(row["total"] - float(rule["total"])) < 1e-6
            ctx.add(row)
            ctx.log(fmt_line(row) + (f", parity {row['parity_with_rule']}" if "parity_with_rule" in row else ""))
    del env, model


def phase_written(ctx: Ctx, family: str, seeds: Sequence[int]) -> None:
    for s in seeds:
        if _ilp_done(ctx, family, s, "ilp_written"):
            continue
        inst, lib = load_case(family, s, ctx.inst_dir, relaxed=False)
        md5 = ctx.check_md5(family, s, inst)
        run_ilp(ctx, family, s, inst, lib, md5, "ilp_written")
        del inst, lib


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------
GAP_REF = "ilp_relaxed"


def derived_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Last row per key + derived ``best_rule`` rows + headline gaps to ``ilp_relaxed`` and the
    price of recovery on ``ilp_written`` rows."""
    last = list(last_per_key([r for r in rows if r.get("kind") != "train"]).values())
    by = {(r["family"], str(r["seed"]), r["method"]): r for r in last}
    out = [dict(r) for r in last]
    fam_seeds = sorted({(r["family"], str(r["seed"])) for r in last})
    for fam, s in fam_seeds:
        cands = [by[(fam, s, f"rule_{n}")] for n in BEST_RULE_OVER
                 if (fam, s, f"rule_{n}") in by and by[(fam, s, f"rule_{n}")].get("total_end_adjusted") is not None]
        if cands:
            b = min(cands, key=lambda r: float(r["total_end_adjusted"]))
            br = dict(b)
            br.update(kind="best_rule", method="best_rule", best_rule_variant=b["method"],
                      best_rule_candidates=[c["method"] for c in cands])
            out.append(br)
    by = {(r["family"], str(r["seed"]), r["method"]): r for r in out}
    for r in out:
        ref = by.get((r["family"], str(r["seed"]), GAP_REF))
        r["gap_ilp_pct"] = r["gap_ilp_end_adj_pct"] = None
        if ref is None or ref.get("total") is None or r.get("total") is None or r["method"] in (GAP_REF, "ilp_written"):
            continue
        for col, key in (("total", "gap_ilp_pct"), ("total_end_adjusted", "gap_ilp_end_adj_pct")):
            p, q = float(r[col]), float(ref[col])
            r[key] = None if abs(p) < 1e-12 else 100.0 * (p - q) / abs(p)
    for r in out:
        if r["method"] == "ilp_written" and r.get("total") is not None:
            ref = by.get((r["family"], str(r["seed"]), GAP_REF))
            if ref is not None and ref.get("total") is not None:
                r["price_of_recovery"] = float(r["total"]) - float(ref["total"])
                r["price_of_recovery_end_adj"] = float(r["total_end_adjusted"]) - float(ref["total_end_adjusted"])
                r["price_of_recovery_certified"] = all(
                    x.get("status") == "OPTIMAL" or C.reusable_ilp_row(x.get("status"), x.get("gap"), tol=1e-4)
                    for x in (r, ref))
    return out


def write_results(ctx: Ctx) -> None:
    rows = derived_rows(ctx.rows)
    rows.extend(r for r in last_per_key(ctx.rows).values() if r.get("kind") == "train")
    C.write_csv(rows, os.path.join(ctx.out, "results.csv"))


def summarise(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per (family, method): means with 95 % CIs, headline gaps, and paired differences of the
    RL agent to its own rider rule and to best_rule (end-adjusted totals)."""
    d = [r for r in derived_rows(rows) if r.get("total") is not None]
    out: List[Dict[str, Any]] = []
    for fam in sorted({r["family"] for r in d}):
        dr = [r for r in d if r["family"] == fam]
        by = {(str(r["seed"]), r["method"]): r for r in dr}
        for m in list(dict.fromkeys(r["method"] for r in dr)):
            rs = [r for r in dr if r["method"] == m]
            rec: Dict[str, Any] = {"family": fam, "method": m}
            for col in ("total", "total_end_adjusted", "C_end_adjust", "served_share", "gap_ilp_pct",
                        "gap_ilp_end_adj_pct", "price_of_recovery", "price_of_recovery_end_adj", "runtime_s"):
                vals = [float(r[col]) for r in rs if r.get(col) is not None]
                mu, hw, n = A7.mean_ci(vals)
                rec[f"{col}_mean"], rec[f"{col}_ci95"] = mu, hw
                if col == "total":
                    rec["n_seeds"] = n
            refs = [("best_rule", "best_rule")]
            if m.startswith("rl_ppo[") or m.startswith("replay[") or m.startswith("heuristic_"):
                rider = m[m.index("[") + 1:-1]
                refs.insert(0, ("own_rule", f"rule_{rider}"))
            for lab, ref in refs:
                diffs = [float(r["total_end_adjusted"]) - float(by[(str(r["seed"]), ref)]["total_end_adjusted"])
                         for r in rs if (str(r["seed"]), ref) in by]
                mu, hw, n = A7.mean_ci(diffs)
                rec[f"diff_vs_{lab}_end_adj_mean"], rec[f"diff_vs_{lab}_end_adj_ci95"] = mu, hw
                rec[f"diff_vs_{lab}_n"] = n
            if m == "best_rule":
                rec["best_rule_variants"] = json.dumps(
                    {v: sum(1 for r in rs if r.get("best_rule_variant") == v)
                     for v in sorted({r.get("best_rule_variant") for r in rs})})
            if m == "ilp_written":
                rec["price_of_recovery_n_certified"] = sum(1 for r in rs if r.get("price_of_recovery_certified"))
            if m.startswith("ilp"):
                rec["n_optimal"] = sum(1 for r in rs if r.get("status") == "OPTIMAL")
                gaps = [float(r["gap"]) for r in rs if r.get("gap") is not None]
                rec["max_mip_gap"] = max(gaps) if gaps else None
            if m.startswith("replay["):
                rec["parity_all"] = all(bool(r.get("parity_with_rule")) for r in rs)
            rec["all_ok_modulo_report_only"] = all(bool(r.get("ok_modulo_report_only")) for r in rs)
            rec["md5_unique_per_seed"] = all(
                len({x.get("demand_md5") for x in dr if str(x["seed"]) == str(r["seed"])}) == 1 for r in rs)
            out.append(rec)
    return out


def write_report(ctx: Ctx) -> None:
    summ = summarise(ctx.rows)
    C.write_csv(summ, os.path.join(ctx.out, "summary.csv"))
    trains = [r for r in last_per_key(ctx.rows).values() if r.get("kind") == "train"]
    a = ctx.a
    lines = ["# X7 -- A7 RL comparator vs rule policies and the ILP (round 5)", "",
             f"Families {list(a.families)}, test seeds `{a.test_seeds}`, training seeds `{a.train_seeds}`, "
             f"PPO-clip {a.timesteps} steps per rider layer ({', '.join(a.riders)}), ILP aggregated (O1), "
             f"Threads {C.THREADS}, Seed 0, TimeLimit {a.ilp_time_limit:g} s.", "",
             "Headline = M1 relaxed control (rho = 0, R_end = 0); `total` = E2 (26), `end-adj` = (26) + "
             "C_end_adjust (M1); gap = 100 (policy - ilp_relaxed) / policy; differences are paired over seeds "
             "(end-adjusted, mean +- 95 % Student-t half-width). `best_rule` = per-seed minimum over "
             f"{', '.join('rule_' + n for n in BEST_RULE_OVER)} (rule_r5_transfer only with services). "
             "`ilp_written` keeps (17)-(18); its `price_of_recovery` = ilp_written - ilp_relaxed.", ""]
    if trains:
        lines += ["## Training", "", "| family | agent | status | steps | wall s | steps/s | return first 100 | last 100 |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in trains:
            lines.append(f"| {r['family']} | {r['method']} | {r.get('status')} | {r.get('timesteps_done', '-')} | "
                         f"{C.fmt(r.get('runtime_s'), 1)} | {C.fmt(r.get('steps_per_s'), 0)} | "
                         f"{C.fmt(r.get('return_first100'), 2)} | {C.fmt(r.get('return_last100'), 2)} |")
        lines.append("")
    for fam in sorted({s["family"] for s in summ}):
        lines += [f"## {fam}", "",
                  "| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | "
                  "diff vs own rule | diff vs best_rule |", "|---|---|---|---|---|---|---|---|---|---|"]

        def pm(s, col, d=2):
            mu, hw = s.get(f"{col}_mean"), s.get(f"{col}_ci95")
            if mu is None or (isinstance(mu, float) and math.isnan(mu)):
                return "-"
            return f"{mu:.{d}f} +- {C.fmt(hw, d)}"

        for s in [x for x in summ if x["family"] == fam]:
            lines.append(f"| {s['method']} | {s['n_seeds']} | {pm(s, 'total')} | {pm(s, 'total_end_adjusted')} | "
                         f"{pm(s, 'C_end_adjust')} | {pm(s, 'served_share', 3)} | {pm(s, 'gap_ilp_pct')} | "
                         f"{pm(s, 'gap_ilp_end_adj_pct')} | {pm(s, 'diff_vs_own_rule_end_adj')} | "
                         f"{pm(s, 'diff_vs_best_rule_end_adj')} |")
        extra = [x for x in summ if x["family"] == fam]
        por = [x for x in extra if x["method"] == "ilp_written"]
        if por:
            lines += ["", f"Price of recovery (ilp_written - ilp_relaxed): total {pm(por[0], 'price_of_recovery')}, "
                          f"end-adjusted {pm(por[0], 'price_of_recovery_end_adj')} (both ILPs certified optimal on "
                          f"{por[0].get('price_of_recovery_n_certified')} of {por[0]['n_seeds']} seeds)."]
        for x in extra:
            if x["method"].startswith("ilp"):
                lines += ["", f"{x['method']}: OPTIMAL on {x.get('n_optimal')} of {x['n_seeds']} seeds, "
                              f"max MIP gap {C.fmt(x.get('max_mip_gap'), 4)}."]
        br = [x for x in extra if x["method"] == "best_rule"]
        if br:
            lines += ["", f"best_rule picked: {br[0].get('best_rule_variants')}."]
        par = [x for x in extra if x["method"].startswith("replay[")]
        if par:
            lines += ["", "Replay parity with the rule of the same rider layer: "
                      + ", ".join(f"{x['method']} {x.get('parity_all')}" for x in par) + "."]
        lines.append("")
    skipped = [r for r in last_per_key(ctx.rows).values() if r.get("status") in (C.SKIPPED_BUDGET, "ERROR")]
    if skipped:
        lines += ["## Skipped / failed", ""] + [f"- {r['family']} {r['seed']} {r['method']}: {r['status']} "
                                                f"{r.get('error', '')}" for r in skipped] + [""]
    lines += ["Notes: the ILP has perfect information (offline reference); on nyc4h_stress2 its pruning "
              "(PRUNING_NYC, targets = facilities) binds only the ILP, so its optimum is an upper bound on the "
              "written optimum. The RL agent controls only the station layer (charging; transfers where services "
              "exist) on top of the named rider layer; `replay[r]` is the rule station layer inside the "
              "environment and must equal `rule_r`."]
    with open(os.path.join(ctx.out, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# plan / main
# ---------------------------------------------------------------------------
def build_plan(ctx: Ctx) -> List[Tuple[str, str, Any, str]]:
    a = ctx.a
    seeds = A7.parse_seeds(a.test_seeds)
    plan: List[Tuple[str, str, Any, str]] = []
    for fam in a.families:
        for s in seeds:
            for n in RULES:
                if n == "r5_transfer":
                    continue        # added at run time when the instance has services
                if not _rule_done(ctx, fam, s, n):
                    plan.append(("rules", fam, s, f"rule_{n}"))
            if not a.no_ilp and not _ilp_done(ctx, fam, s, "ilp_relaxed"):
                plan.append(("ilp_relaxed", fam, s, "ilp_relaxed"))
        for rider in a.riders:
            tr = train_done(ctx, fam, rider)
            if tr is None:
                plan.append(("train", fam, "train", f"ppo[{rider}]"))
            for s in seeds:
                r = ctx.done.get(("rl", fam, str(s), f"rl_ppo[{rider}]"))
                if tr is None or r is None or r.get("train_id") != tr["train_id"]:
                    plan.append(("rl_eval", fam, s, f"rl+replay+heuristics[{rider}]"))
    if not a.no_ilp and not a.no_written:
        for fam in a.families:
            for s in seeds:
                if not _ilp_done(ctx, fam, s, "ilp_written"):
                    plan.append(("ilp_written", fam, s, "ilp_written"))
    return plan


def plan_minutes(plan: Sequence[Tuple[str, str, Any, str]], a: argparse.Namespace) -> Dict[str, Any]:
    """Expected and worst-case wall minutes of the remaining plan (worst: every ILP at its
    TimeLimit, training at 60 % of the calibrated speed)."""
    per: Dict[str, int] = {}
    exp = worst = 0.0
    for ph, fam, _s, _m in plan:
        per[ph] = per.get(ph, 0) + 1
        e = EXPECT_S.get(fam, EXPECT_S["_default"])
        if ph == "rules":
            exp += EXPECT_RULE_S / len(RULES)
            worst += EXPECT_RULE_S / len(RULES)
        elif ph in ("ilp_relaxed", "ilp_written"):
            exp += min(e[ph], a.ilp_time_limit) + 2 * e["instance"]
            worst += a.ilp_time_limit + 30.0 + 2 * e["instance"]
        elif ph == "train":
            t = a.timesteps / e["train_steps_per_s"]
            exp += t + 30.0
            worst += t / 0.6 + 30.0
        elif ph == "rl_eval":
            exp += EXPECT_RL_EVAL_S + e["instance"]
            worst += 2 * (EXPECT_RL_EVAL_S + e["instance"])
    return {"items": len(plan), "per_phase": per, "expected_wall_min": round(exp / 60.0, 1),
            "worst_wall_min": round(worst / 60.0, 1), "wall_budget_min": a.wall_budget_min}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--families", nargs="+", default=list(FAMILIES))
    ap.add_argument("--riders", nargs="+", default=list(RIDERS))
    ap.add_argument("--train-seeds", default=TRAIN_SEEDS)
    ap.add_argument("--test-seeds", default=TEST_SEEDS)
    ap.add_argument("--timesteps", type=int, default=TIMESTEPS)
    ap.add_argument("--ilp-time-limit", type=float, default=ILP_TIME_LIMIT)
    ap.add_argument("--wall-budget-min", type=float, default=WALL_BUDGET_MIN)
    ap.add_argument("--min-train-min", type=float, default=3.0,
                    help="do not start a training with less than this many minutes available")
    ap.add_argument("--episodes-per-instance", type=int, default=EPISODES_PER_INSTANCE,
                    help="consecutive training episodes per instance (amortises the library build)")
    ap.add_argument("--cache-size", type=int, default=CACHE_SIZE, help="training instances kept in memory")
    ap.add_argument("--no-ilp", action="store_true")
    ap.add_argument("--no-written", action="store_true", help="skip the written-target ILP phase")
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="2048 PPO steps on seeds 1000-1001, test seed 0, ILP TimeLimit 30 s (use --out)")
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args(argv)
    if a.smoke:
        a.timesteps = min(a.timesteps, 2048)
        a.train_seeds = "1000:1002"
        a.test_seeds = "0:1"
        a.ilp_time_limit = min(a.ilp_time_limit, 30.0)
        a.wall_budget_min = min(a.wall_budget_min, 30.0)
        a.min_train_min = 0.5
        if os.path.abspath(a.out) == os.path.abspath(OUT_DIR):
            a.out = os.path.join(OUT_DIR, "_smoke")
    for f in a.families:
        if f not in C.FAMILIES:
            ap.error(f"unknown family {f!r}")
    return a


def main(argv: Optional[Sequence[str]] = None) -> None:
    a = parse_args(argv)
    ctx = Ctx(a)
    if a.analyse:
        write_results(ctx)
        write_report(ctx)
        return
    plan = build_plan(ctx)
    pm = plan_minutes(plan, a)
    if a.dry_run:
        import importlib.util
        print(json.dumps({"out": ctx.out, "families": a.families, "riders": a.riders, "train_seeds": a.train_seeds,
                          "test_seeds": a.test_seeds, "timesteps": a.timesteps, "ilp_time_limit": a.ilp_time_limit,
                          "threads": C.THREADS, "gurobi_params": C.ILP_PARAMS_R3, "ilp_kwargs": C.R5_ILP_KWARGS,
                          "existing_records": len(ctx.rows),
                          "gurobipy": importlib.util.find_spec("gurobipy") is not None,
                          "stable_baselines3": importlib.util.find_spec("stable_baselines3") is not None,
                          **pm}, indent=2))
        for item in plan:
            print("  ", item)
        return
    ctx.log(f"start: {pm}")
    seeds = A7.parse_seeds(a.test_seeds)
    for fi, fam in enumerate(a.families):
        phase_rules_and_ilp(ctx, fam, seeds)
        for ri, rider in enumerate(a.riders):
            tr = train_done(ctx, fam, rider)
            if tr is None:
                # reserve kept for the higher-priority work after this training: its evaluation (2 min),
                # later trainings at their minimum and the relaxed ILPs of later families (the
                # lower-priority written ILPs are not reserved)
                later = a.families[fi + 1:]
                n_later_train = (len(a.riders) - ri - 1) + len(later) * len(a.riders)
                n_later_ilp = 0 if a.no_ilp else sum(1 for f in later for s in seeds
                                                     if not _ilp_done(ctx, f, s, "ilp_relaxed"))
                reserve = (120.0 + n_later_train * a.min_train_min * 60.0
                           + n_later_ilp * (a.ilp_time_limit + 15.0))
                tr = train_policy(ctx, fam, rider, reserve)
            if tr is None:
                continue
            evaluate_rl(ctx, fam, rider, tr, seeds)
    if not a.no_ilp and not a.no_written:
        for fam in a.families:
            phase_written(ctx, fam, seeds)
    write_results(ctx)
    write_report(ctx)
    with open(os.path.join(ctx.out, "wall_time.json"), "w") as fh:
        json.dump({"start": ctx.t_start, "end": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "wall_min": ctx.budget.elapsed() / 60.0, "budget_min": a.wall_budget_min,
                   "plan": pm}, fh, indent=2)
    ctx.log(f"done in {ctx.budget.elapsed() / 60.0:.1f} min")


if __name__ == "__main__":
    main()
