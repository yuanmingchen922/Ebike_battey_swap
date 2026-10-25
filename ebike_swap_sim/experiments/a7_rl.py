"""Experiment A7 -- online learned comparator (``notes/reading_to_model.md`` item A7, the
IJCAI-25 Sec. 4.1 protocol without the Wasserstein penalty, i.e. plain PPO-clip).

A PPO policy (stable-baselines3) controls ONLY the station layer -- charging counts per site
(E2 (19)-(21)) and, where services exist, transfer loads per service ((10)-(11)) -- on top of the
event-driven rider policy of ``baseline.py`` (``ebike_swap_sim.rl_env.StationEnv``).  Reward =
negative incremental E2 cost ((26)-(32), ``evaluate.cost``) plus the M1 end-state adjustment at
the end of the window.  Episodes are one window of a generated instance: random TRAINING seeds
(default 1000-1063) and held-out TEST seeds (default 0-9, the seeds of the earlier rounds).

Sub-commands (outputs in ``outputs/a7_rl/<family>/``):

* ``train``    -- PPO-clip for ``--timesteps`` (default 200,000) env steps; saves
                  ``ppo_station.zip``, ``vecnormalize.pkl``, ``train_config.json``, ``monitor.csv``.
* ``evaluate`` -- on the test seeds: the full baseline policies (rider variant ``r2`` = DECISIONS
                  R2.3 and ``r5`` when ``baseline.BASELINE_VARIANTS`` defines it), the RL station
                  layer (deterministic), the in-environment replay of the baseline station rules
                  (parity check), the hand-written station heuristics ``none`` / ``asap``, and --
                  unless ``--no-ilp`` -- the E2 ILP (perfect information, Gurobi Threads 3,
                  ``--ilp-time-limit``).  Prints mean cost with 95 % seed confidence intervals
                  (Student t) and the paired difference to the ``r2`` baseline; writes
                  ``eval_records.jsonl``, ``eval_summary.csv`` and ``RESULTS_A7.md``.
* ``all``      -- ``train`` then ``evaluate`` (default).

Comparison metric: E2 total (26) and ``adjusted_total`` = E2 total + M1 end-state adjustment
(``rl_env.end_state_adjustment``), computed identically for every method on the relaxed-target
copy (``rho = R_end_j = 0``, the M1 headline control; ``--written-targets`` keeps (17)-(18)).
The ILP optimises E2 (26) only (no end-state term) and is the offline perfect-information
reference; on the semi-real families its value is an upper bound on the written optimum
(``PRUNING_NYC``).

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/a7_rl.py all --family nyc4h_stress2 --timesteps 200000
    python3 experiments/a7_rl.py train --timesteps 2000 --train-seeds 1000:1002 --tag smoke
    python3 experiments/a7_rl.py evaluate --test-seeds 0:10 --no-ilp
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from ebike_swap_sim import baseline as bl  # noqa: E402
from ebike_swap_sim.evaluate import check, cost, metrics  # noqa: E402
from ebike_swap_sim.or_instance import Instance  # noqa: E402
from ebike_swap_sim.rl_env import (EnvConfig, StationEnv, adjusted_cost,  # noqa: E402
                                   resolve_rider_variant, rider_params)
from experiments import common as C  # noqa: E402

THREADS = C.THREADS            # 3: Gurobi and torch
DEFAULT_FAMILY = "nyc4h_stress2"
DEFAULT_TRAIN_SEEDS = "1000:1064"
DEFAULT_TEST_SEEDS = "0:10"
OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "a7_rl")

#: PPO-clip hyper-parameters (IJCAI-25 Sec. 4.1 uses PPO variants with a clipped / penalised
#: surrogate; the Wasserstein penalty of W-PPO is dropped, A7 "Wasserstein-free").
PPO_DEFAULTS: Dict[str, Any] = {
    "learning_rate": 3e-4, "n_steps": 2048, "batch_size": 64, "n_epochs": 10,
    "gamma": 0.99, "gae_lambda": 0.95, "clip_range": 0.2, "ent_coef": 0.01,
    "vf_coef": 0.5, "max_grad_norm": 0.5, "net_arch": [64, 64],
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def parse_seeds(spec: str) -> List[int]:
    """``'a:b'`` -> ``range(a, b)``; ``'1,4,7'`` -> list; single int -> ``[n]``."""
    spec = str(spec).strip()
    if ":" in spec:
        a, b = spec.split(":", 1)
        return list(range(int(a), int(b)))
    return [int(s) for s in spec.split(",") if s.strip()]


def out_dir(family: str, tag: str = "") -> str:
    """``outputs/a7_rl/<family>[_<tag>]/`` (created)."""
    name = family + (f"_{tag}" if tag else "")
    return C.ensure_dir(os.path.join(OUT_ROOT, name))


def cached_factory(family: str, cache_dir: str, relax_targets: bool = True,
                   family_overrides: Optional[Dict[str, Any]] = None):
    """A7 instance factory ``seed -> (Instance, ArcLibrary)`` with a JSON cache of the generated
    instances (``Instance.save`` / ``Instance.load`` round-trip byte-identically, CONTRACT
    Section 4), so repeated training passes only rebuild the arc library (E2 (1)-(4), (9))."""
    os.makedirs(cache_dir, exist_ok=True)
    ov = dict(family_overrides or {})
    ov_key = "" if not ov else "_" + hashlib.md5(
        json.dumps(ov, sort_keys=True, default=str).encode()).hexdigest()[:8]

    def factory(seed: int):
        path = os.path.join(cache_dir, f"{family}{ov_key}_seed{int(seed)}.json")
        if os.path.exists(path):
            inst = Instance.load(path)
        else:
            inst = C.make_instance(family, int(seed), **ov)
            inst.save(path)
        if relax_targets:
            inst = C.relax_end_targets(inst)
        lib, _ = C.build_library(inst, C.pruning_for(inst))
        return inst, lib

    return factory


def mean_ci(values: Sequence[float], level: float = 0.95) -> Tuple[float, float, float]:
    """Mean and half-width of the Student-t confidence interval over seeds (``n - 1`` dof)."""
    v = np.asarray([x for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))],
                   dtype=float)
    if v.size == 0:
        return float("nan"), float("nan"), 0
    m = float(v.mean())
    if v.size < 2:
        return m, float("nan"), int(v.size)
    try:
        from scipy import stats
        tq = float(stats.t.ppf(0.5 + level / 2.0, v.size - 1))
    except ImportError:  # pragma: no cover
        tq = 1.96
    return m, tq * float(v.std(ddof=1)) / math.sqrt(v.size), int(v.size)


def available_rider_variants(names: Sequence[str] = ("r2", "r5")) -> List[str]:
    """The requested rider variants that ``baseline.BASELINE_VARIANTS`` defines (``r5`` is
    only present once the round-5 rider rules are merged into ``baseline.py``)."""
    out = []
    for n in names:
        try:
            resolve_rider_variant(n)
            out.append(n)
        except KeyError:
            print(f"[a7] rider variant {n!r} not defined in baseline.BASELINE_VARIANTS; skipped")
    return out


def _set_threads() -> None:
    try:
        import torch
        torch.set_num_threads(THREADS)
    except ImportError:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# training
# ---------------------------------------------------------------------------
def train(family: str = DEFAULT_FAMILY, train_seeds: Sequence[int] = tuple(range(1000, 1064)),
          timesteps: int = 200_000, seed: int = 0, tag: str = "", rider_variant: str = "r2",
          relax_targets: bool = True, episodes_per_instance: int = 8, cache_size: int = 4,
          reward_scale: float = 0.1, ppo: Optional[Dict[str, Any]] = None,
          family_overrides: Optional[Dict[str, Any]] = None, factory=None,
          verbose: int = 0, out: Optional[str] = None) -> Dict[str, Any]:
    """Train the A7 PPO-clip station policy and save it (``ppo_station.zip``).

    ``factory`` overrides the family factory (tests use the toy instance).  Returns the
    record written to ``train_config.json`` (paths, settings, wall time, last episode
    returns); ``out`` overrides the output directory."""
    from stable_baselines3 import PPO
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    _set_threads()
    od = C.ensure_dir(out) if out else out_dir(family, tag)
    hp = {**PPO_DEFAULTS, **(ppo or {})}
    net_arch = hp.pop("net_arch")
    if factory is None:
        factory = cached_factory(family, os.path.join(OUT_ROOT, "instances"), relax_targets, family_overrides)
    cfg = EnvConfig(rider_variant=rider_variant, seeds=tuple(int(s) for s in train_seeds),
                    episodes_per_instance=episodes_per_instance, cache_size=cache_size,
                    reward_scale=reward_scale, shuffle=True)
    monitor_path = os.path.join(od, "monitor.csv")

    def _make():
        return Monitor(StationEnv(factory=factory, config=cfg), filename=monitor_path)

    venv = VecNormalize(DummyVecEnv([_make]), norm_obs=False, norm_reward=True, gamma=hp["gamma"])
    venv.seed(seed)
    model = PPO("MlpPolicy", venv, seed=seed, device="cpu", verbose=verbose,
                policy_kwargs={"net_arch": list(net_arch)}, **hp)
    t0 = time.perf_counter()
    model.learn(total_timesteps=int(timesteps))
    wall = time.perf_counter() - t0
    model_path = os.path.join(od, "ppo_station.zip")
    model.save(model_path)
    venv.save(os.path.join(od, "vecnormalize.pkl"))
    rec = {
        "item": "A7", "family": family, "tag": tag, "timesteps": int(timesteps), "seed": seed,
        "train_seeds": [int(s) for s in train_seeds], "rider_variant": rider_variant,
        "relax_targets": relax_targets, "episodes_per_instance": episodes_per_instance,
        "reward_scale": reward_scale, "ppo": {**hp, "net_arch": list(net_arch)},
        "wall_s": wall, "model_path": model_path, "family_overrides": family_overrides or {},
        "action_space": str(venv.action_space), "obs_dim": int(venv.observation_space.shape[0]),
    }
    with open(os.path.join(od, "train_config.json"), "w") as fh:
        json.dump(C.jsonable(rec), fh, indent=2)
    print(f"[a7] trained {timesteps} steps in {wall:.1f} s -> {model_path}")
    return rec


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
def run_env_episode(env: StationEnv, seed: int, policy: str, model=None) -> Dict[str, Any]:
    """One test episode of the A7 environment on instance ``seed`` with ``policy`` in
    ``{'rl', 'replay', 'none', 'asap', 'demand_aware'}``; returns the schedule, the E2 cost
    (26)-(32), the M1-adjusted total, the episode return and the wall time."""
    env.cfg.station_policy = "baseline" if policy == "replay" else "agent"
    obs, _ = env.reset(options={"seed": seed})
    done, ret, t0 = False, 0.0, time.perf_counter()
    info: Dict[str, Any] = {}
    while not done:
        if policy == "rl":
            action, _ = model.predict(obs, deterministic=True)
        elif policy == "replay":
            action = env.action_space.sample() * 0
        else:
            action = env.heuristic_action(policy)
        obs, r, done, _, info = env.step(action)
        ret += r
    env.cfg.station_policy = "agent"
    return {"schedule": info["schedule"], "cost": info["cost"], "E2_total": info["episode_cost"],
            "end_adj": info["end_adj"], "adjusted_total": info["adjusted_total"], "return": ret,
            "runtime": time.perf_counter() - t0, "flags": info["flags"]}


def _row(method: str, seed: int, inst, lib, sched, e2: Dict[str, Any], runtime: float,
         extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    adj = adjusted_cost(inst, lib, sched)
    rep = check(inst, lib, sched)
    fams = {k: v["count"] for k, v in rep["families"].items()}
    m = metrics(inst, lib, sched)
    row = {"method": method, "seed": seed, "E2_total": e2["total"], "end_adj": adj["end_adj"],
           "adjusted_total": e2["total"] + adj["end_adj"], "C_elec": e2["C_elec"],
           "C_travel": e2["C_travel"], "C_orders": e2["C_orders"], "C_reb": e2["C_reb"],
           "unserved": e2["C_orders_parts"]["unserved"], "served_share": m["served_share"],
           "n_swaps": m["n_swaps"], "kwh_purchased": m["kwh_purchased"], "runtime": runtime,
           "families": fams, "ok_modulo_report_only": all(f in C.BASELINE_REPORT_ONLY for f in fams)}
    row.update(extra or {})
    return row


def evaluate_policy(family: str = DEFAULT_FAMILY, test_seeds: Sequence[int] = tuple(range(10)),
                    tag: str = "", model_path: Optional[str] = None, rider_variant: str = "r2",
                    relax_targets: bool = True, ilp: bool = True, ilp_time_limit: float = 120.0,
                    family_overrides: Optional[Dict[str, Any]] = None, factory=None,
                    heuristics: Sequence[str] = ("none", "asap"),
                    out: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate the saved A7 policy on held-out seeds against the baseline rider variants
    (``r2`` / ``r5``), the station heuristics and (optionally) the ILP; print and write
    mean costs with 95 % seed CIs and paired differences to the ``r2`` baseline; ``out``
    overrides the output directory."""
    from stable_baselines3 import PPO

    _set_threads()
    od = C.ensure_dir(out) if out else out_dir(family, tag)
    model_path = model_path or os.path.join(od, "ppo_station.zip")
    model = PPO.load(model_path, device="cpu")
    if factory is None:
        factory = cached_factory(family, os.path.join(OUT_ROOT, "instances"), relax_targets, family_overrides)
    env = StationEnv(factory=factory, config=EnvConfig(rider_variant=rider_variant,
                                                       seeds=tuple(int(s) for s in test_seeds),
                                                       cache_size=1, shuffle=False))
    have_ilp = False
    if ilp:
        import importlib.util          # only ilp.py imports gurobipy (CONTRACT section 0)
        have_ilp = importlib.util.find_spec("gurobipy") is not None
        if not have_ilp:
            print("[a7] gurobipy not available: ILP column skipped")
    rows: List[Dict[str, Any]] = []
    riders = available_rider_variants()
    for s in test_seeds:
        inst, lib = env._load(int(s))
        base_r2 = None
        for rv in riders:
            p = rider_params(inst, rv)
            t0 = time.perf_counter()
            sched, flags = bl.run_baseline(inst, lib, p)
            rt = time.perf_counter() - t0
            e2 = cost(inst, lib, sched)
            rows.append(_row(f"baseline_{rv}", s, inst, lib, sched, e2, rt))
            if rv == "r2":
                base_r2 = (sched, e2)
        for pol in ["rl", "replay", *heuristics]:
            ep = run_env_episode(env, int(s), pol, model)
            extra = {"return": ep["return"]}
            if pol == "replay" and base_r2 is not None and rider_variant == "r2":
                extra["parity_with_baseline_r2"] = abs(ep["E2_total"] - base_r2[1]["total"]) < 1e-6
            name = {"rl": f"rl_ppo[{rider_variant}]", "replay": f"replay[{rider_variant}]"}.get(
                pol, f"heuristic_{pol}[{rider_variant}]")
            rows.append(_row(name, s, inst, lib, ep["schedule"], ep["cost"], ep["runtime"], extra))
        if have_ilp:
            base = C.run_baseline_case(inst, lib)
            start, start_name = C.feasible_mip_start(inst, lib, base)
            rec = C.run_ilp_case(inst, lib, mip_start=start, time_limit=ilp_time_limit, threads=THREADS)
            if rec["schedule"] is not None:
                rows.append(_row("ilp", s, inst, lib, rec["schedule"], rec["cost"], rec["runtime"],
                                 {"status": rec["status"], "gap": rec["gap"], "mip_start": start_name}))
        print(f"[a7] seed {s}: " + ", ".join(f"{r['method']}={r['adjusted_total']:.2f}"
                                            for r in rows if r["seed"] == s))
    summary = summarise(rows)
    write_outputs(od, rows, summary, family, test_seeds, model_path, rider_variant, relax_targets,
                  have_ilp, ilp_time_limit)
    return {"rows": rows, "summary": summary}


def summarise(rows: List[Dict[str, Any]], ref: str = "baseline_r2") -> List[Dict[str, Any]]:
    """Per method: mean E2 total and M1-adjusted total with 95 % seed CIs, and the paired
    difference ``method - ref`` (adjusted) with its CI (seeds where both exist)."""
    methods = list(dict.fromkeys(r["method"] for r in rows))
    by = {(r["method"], r["seed"]): r for r in rows}
    out = []
    for m in methods:
        rs = [r for r in rows if r["method"] == m]
        e2, e2h, n = mean_ci([r["E2_total"] for r in rs])
        adj, adjh, _ = mean_ci([r["adjusted_total"] for r in rs])
        diffs = [r["adjusted_total"] - by[(ref, r["seed"])]["adjusted_total"]
                 for r in rs if (ref, r["seed"]) in by]
        d, dh, nd = mean_ci(diffs)
        out.append({"method": m, "n_seeds": n, "E2_mean": e2, "E2_ci95": e2h,
                    "adjusted_mean": adj, "adjusted_ci95": adjh,
                    f"diff_vs_{ref}_mean": d, f"diff_vs_{ref}_ci95": dh, "n_paired": nd,
                    "served_share_mean": float(np.mean([r["served_share"] for r in rs])),
                    "all_ok_modulo_report_only": all(r["ok_modulo_report_only"] for r in rs)})
    return out


def write_outputs(od: str, rows, summary, family, test_seeds, model_path, rider_variant,
                  relax_targets, have_ilp, ilp_time_limit) -> None:
    """``eval_records.jsonl``, ``eval_summary.csv`` and ``RESULTS_A7.md`` in ``od``; prints the table."""
    with open(os.path.join(od, "eval_records.jsonl"), "w") as fh:
        for r in rows:
            fh.write(json.dumps(C.jsonable(r)) + "\n")
    C.write_csv(summary, os.path.join(od, "eval_summary.csv"))
    ref = "baseline_r2"
    lines = [
        "# A7 -- RL station-layer comparator (PPO-clip)", "",
        f"Family `{family}`, test seeds {list(test_seeds)}, model `{os.path.relpath(model_path, C._ROOT)}`, "
        f"rider layer `{rider_variant}`, targets {'relaxed (rho = R_end = 0, M1 headline)' if relax_targets else 'written'}; "
        f"ILP {'included (TimeLimit %g s, Threads %d)' % (ilp_time_limit, THREADS) if have_ilp else 'not run'}.", "",
        "Costs: E2 total (26) and adjusted = E2 total + M1 end-state adjustment; mean +- 95 % "
        "Student-t half-width over seeds; paired difference to the full R2.3 baseline policy.", "",
        "| method | n | E2 total | adjusted | diff vs baseline_r2 | served share | ok (mod. 9/17/18) |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(f"| {s['method']} | {s['n_seeds']} | {s['E2_mean']:.2f} +- {s['E2_ci95']:.2f} | "
                     f"{s['adjusted_mean']:.2f} +- {s['adjusted_ci95']:.2f} | "
                     f"{s[f'diff_vs_{ref}_mean']:+.2f} +- {s[f'diff_vs_{ref}_ci95']:.2f} | "
                     f"{s['served_share_mean']:.3f} | {s['all_ok_modulo_report_only']} |")
    lines += ["", "Notes: the ILP has perfect information and optimises (26) without the end-state "
              "term; on semi-real families it is an upper bound on the written optimum (PRUNING_NYC). "
              "`replay` is the baseline station rule executed inside the environment (parity check: "
              "it must equal `baseline_r2`)."]
    with open(os.path.join(od, "RESULTS_A7.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", nargs="?", default="all", choices=("train", "evaluate", "all"))
    ap.add_argument("--family", default=DEFAULT_FAMILY)
    ap.add_argument("--family-overrides", default="{}", help="JSON dict of make_instance overrides")
    ap.add_argument("--train-seeds", default=DEFAULT_TRAIN_SEEDS)
    ap.add_argument("--test-seeds", default=DEFAULT_TEST_SEEDS)
    ap.add_argument("--timesteps", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=0, help="PPO / torch seed")
    ap.add_argument("--tag", default="")
    ap.add_argument("--rider-variant", default="r2")
    ap.add_argument("--written-targets", action="store_true", help="keep (17)-(18) (default: relaxed, M1)")
    ap.add_argument("--episodes-per-instance", type=int, default=8)
    ap.add_argument("--cache-size", type=int, default=4)
    ap.add_argument("--reward-scale", type=float, default=0.1)
    ap.add_argument("--ppo", default="{}", help="JSON dict of PPO hyper-parameter overrides")
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-ilp", action="store_true")
    ap.add_argument("--ilp-time-limit", type=float, default=120.0)
    ap.add_argument("--verbose", type=int, default=0)
    a = ap.parse_args(argv)
    ov = json.loads(a.family_overrides)
    relax = not a.written_targets
    if a.command in ("train", "all"):
        train(a.family, parse_seeds(a.train_seeds), a.timesteps, a.seed, a.tag, a.rider_variant,
              relax, a.episodes_per_instance, a.cache_size, a.reward_scale, json.loads(a.ppo), ov,
              verbose=a.verbose)
    if a.command in ("evaluate", "all"):
        evaluate_policy(a.family, parse_seeds(a.test_seeds), a.tag, a.model, a.rider_variant, relax,
                        not a.no_ilp, a.ilp_time_limit, ov)


if __name__ == "__main__":
    main()
