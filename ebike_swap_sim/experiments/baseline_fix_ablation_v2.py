"""Ablation of the two baseline policy fixes (F1 just-in-time dispatch, F2 dead-zone
swap rule) on the E4 ``B`` sweep (``C_j = 3``, ``P_j = 4`` kW), both regimes.

Variants of :class:`ebike_swap_sim.baseline.BaselineParams`: ``legacy`` (old behaviour),
``jit_only``, ``deadzone_only``, ``v2`` (both fixes, the default), and the two
``*_no_reach_guard`` controls (``require_post_delivery_reach = False``).  Instances are
regenerated as in ``e4_sizing`` (``common.make_instance('large', seed)``, stressed regime
``init_frac = (0.25, 0.5)``); one arc library per seed (the arcs do not depend on
``B_j``).  Costs: ``evaluate.cost`` (26)-(32).  Writes ``outputs/e4_sizing/ablation_fixes_v2.csv``
(the table is embedded into ``RESULTS_v2.md`` by ``baseline_rerun_v2.py --report-only``).

Run from ``ebike_swap_sim/``::  PYTHONPATH=. python3 experiments/baseline_fix_ablation_v2.py
"""
import sys, os, json, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from experiments import common as C
from experiments import e4_sizing as E4
from experiments import baseline_rerun_v2 as V

VARS = {"legacy": {"jit_dispatch": False, "swap_on_reach_refusal": False},
        "jit_only": {"swap_on_reach_refusal": False},
        "deadzone_only": {"jit_dispatch": False},
        "v2": {},
        "v2_no_reach_guard": {"require_post_delivery_reach": False},
        "legacy_no_reach_guard": {"jit_dispatch": False, "swap_on_reach_refusal": False, "require_post_delivery_reach": False}}
rows = []
for regime, init in (("main", None), ("stressed_lowq0", (0.25, 0.5))):
    for seed in (0, 1, 2):
        ov = {"demand_spec": {"init_frac": init}} if init else {}
        base = C.make_instance("large", seed=seed, **ov)
        work = copy.deepcopy(base)
        lib = None
        for B in E4.B_SWEEP:
            V._apply_sizes(work, B, E4.BASE_C, E4.BASE_P, f"B{B}")
            if lib is None:
                lib, _ = C.build_library(work, C.pruning_for(work))
            for name, p in VARS.items():
                r = C.run_baseline_case(work, lib, p, label=name)
                fl, m = r["flags"], r["metrics"]
                rr = fl.get("reach_refusals") or {}
                rows.append({"regime": regime, "seed": seed, "B_j": B, "variant": name, "total": r["cost"]["total"],
                             "n_unserved": m["n_unserved"], "n_swaps": m["n_swaps"], "bike_km": m["bike_km"],
                             "lateness": r["cost"]["C_orders_parts"]["lateness"], "response": r["cost"]["C_orders_parts"]["response"],
                             "jit": fl.get("jit_dispatches", 0), "reach_refusals": rr.get("count", 0),
                             "reach_to_swap": V._count(rr.get("bikes_sent_to_swap", 0)),
                             "stockout_slots": sum(m["stockout_slots"].values()), "stranded": len(fl["stranded_bikes"]),
                             "families": json.dumps(r["families"], sort_keys=True)})
df = pd.DataFrame(rows)
df.to_csv(os.path.join(V.OUT_E4, "ablation_fixes_v2.csv"), index=False)
pd.set_option("display.width", 250)
print(df.groupby(["regime", "B_j", "variant"])[["total", "n_unserved", "n_swaps", "bike_km", "lateness", "jit", "reach_refusals", "reach_to_swap", "stockout_slots", "stranded"]].mean().round(2).to_string())
