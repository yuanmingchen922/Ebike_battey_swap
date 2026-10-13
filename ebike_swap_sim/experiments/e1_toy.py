"""Experiment E1 -- reproduction of the documented toy results.

Cases (E2 ``notes/extracted/E2_Example.txt`` pp.10-15, ``Battery_Swap.pdf`` p.7):

1. toy ILP, written model                      -> J* = 12.5 = 4 + 0.1 + 0 + 6 + 2.4
2. toy ILP, ``rho = 0`` (drop (18))            -> 11.2
3. toy ILP, ``no_transfers`` (h = z = 0)       -> 106.0 (one order unserved)
4. toy ILP, lexicographic (min sum u, then J)  -> 12.5 with U* = 0
5. toy ILP, lexicographic + no_transfers       -> U* = 1, 106.0
6. baseline NONE on the toy                    -> 108.0 (order 3 unserved, (9)/(17)/(18) clean)
7. baseline REORDER_POINT on the toy           -> 14.5 (= 12.5 + two threshold-induced returns)
   (6-7 are run with the round-2 default rules of DECISIONS R2.3 -- stock-aware site
   choice, DEMAND_AWARE charging -- and repeated with the ``round1`` and ``legacy``
   variants of ``ebike_swap_sim.baseline.BASELINE_VARIANTS``; the old-vs-new table is
   written to RESULTS.md)
8. ILP with baseline REORDER_POINT / NONE as MIP start -> start accepted (fix-and-solve)?
9. Battery_Swap p.7 station: baseline reproduces the p.7 inventory table; ILP (rho = 0)
   optimum 0 with the baseline start verified at 0.1 (two charging steps); one bike with
   q_res = 2 and rho = 1 is forced to swap and recharge the returned battery (0.1)
10. identities: (24) battery conservation on every schedule, baseline online inventory
    == (13) recursion, Gurobi objective == ``evaluate.cost`` total

Outputs ``outputs/e1/results.csv``, ``outputs/e1/RESULTS.md`` (results table, p.15
and p.7 inventory tables, bike paths), ``outputs/e1/inventory_toy.png`` and
``outputs/e1/cost_components.png``.  Run from ``ebike_swap_sim/``::

    PYTHONPATH=. python3 experiments/e1_toy.py
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from experiments import common as C  # noqa: E402
from ebike_swap_sim import build_arcs  # noqa: E402
from ebike_swap_sim import baseline as bl  # noqa: E402

OUT_DIR = os.path.join(C.OUTPUT_ROOT, "e1")
TIME_LIMIT = 60.0

#: p.15 inventory table of the toy optimum: t -> ((n_A0, n_A1, n_A2), (n_C0, n_C1, n_C2)).
P15_TABLE = {0: ((0, 0, 0), (0, 0, 1)), 1: ((0, 0, 0), (0, 0, 1)), 2: ((0, 0, 0), (0, 0, 0)),
             3: ((0, 0, 1), (0, 0, 0)), 4: ((1, 0, 0), (0, 0, 0)), 5: ((0, 0, 0), (0, 0, 0)),
             6: ((0, 0, 0), (1, 0, 0)), 7: ((0, 0, 0), (0, 1, 0)), 8: ((0, 0, 0), (0, 0, 1))}
#: Battery_Swap p.7 table: t -> (n_J0, n_J1, n_J2).
P7_TABLE = {0: (0, 0, 1), 1: (1, 0, 0), 2: (0, 1, 0), 3: (0, 0, 1), 4: (1, 0, 0)}


def _row(case: str, method: str, switches: str, rec: Dict[str, Any], expected: Optional[float],
         extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Flat CSV row for one case from a :func:`common.run_ilp_case` /
    :func:`common.run_baseline_case` record."""
    c = rec.get("cost") or {}
    total = c.get("total")
    row: Dict[str, Any] = {
        "case": case, "method": method, "switches": switches,
        "status": rec.get("status", "-"),
        "total": total, "expected": expected,
        "match": None if expected is None or total is None else abs(total - expected) < 1e-6,
        **C.flatten_cost(c),
        "runtime_s": rec.get("runtime"),
        "check_ok": rec.get("ok"),
        "reported_families": json.dumps(rec.get("families", {})),
        "identity_24_ok": rec.get("identity_24_ok"),
        "n_unserved": (rec.get("metrics") or {}).get("n_unserved"),
    }
    if "stats" in rec and rec["stats"] is not None:
        st = rec["stats"]
        row["obj_eq_cost"] = (st.get("obj") is not None and total is not None
                              and abs(st["obj"] - total) <= 1e-6 * max(1.0, abs(total)))
        row["gap"] = st.get("gap")
        row["lex_min_unserved"] = st.get("lex_min_unserved")
    row.update(extra or {})
    return row


def table_matches(df, expected: Dict[int, Any], facilities: List[str], L: int) -> bool:
    """Compare an :func:`common.inventory_table` frame with a documented table."""
    for t, rows in expected.items():
        if len(facilities) == 1:
            rows = (rows,)
        for j, want in zip(facilities, rows):
            got = tuple(int(df.loc[df["t"] == t, f"n[{j}][{q}]"].iloc[0]) for q in range(L + 1))
            if got != tuple(want):
                return False
    return True


def main(out_dir: str = OUT_DIR) -> List[Dict[str, Any]]:
    """Run E1 and write ``results.csv`` / ``RESULTS.md`` / figures to ``out_dir``."""
    C.ensure_dir(out_dir)
    rows: List[Dict[str, Any]] = []
    md: List[str] = ["# E1 -- toy reproduction (E2 pp.10-15, Battery_Swap p.7)", ""]

    inst = C.make_instance("toy")
    lib, t_build = C.build_library(inst, {})
    md.append(f"Toy instance: {inst.summary()}; arc library {lib.counts()} built in {t_build:.3f} s.")
    md.append("")

    # --- 1-5: ILP variants ------------------------------------------------
    ilp_default = C.run_ilp_case(inst, lib, time_limit=TIME_LIMIT, label="ilp")
    rows.append(_row("toy", "ILP", "written model", ilp_default, 12.5))
    inst_rho0 = _with(inst, rho=0.0)
    rows.append(_row("toy", "ILP", "rho=0", C.run_ilp_case(
        inst_rho0, build_arcs(inst_rho0), time_limit=TIME_LIMIT), 11.2))
    rows.append(_row("toy", "ILP", "no_transfers", C.run_ilp_case(
        inst, lib, time_limit=TIME_LIMIT, no_transfers=True), 106.0))
    lex = C.run_ilp_case(inst, lib, time_limit=TIME_LIMIT, lexicographic=True)
    rows.append(_row("toy", "ILP", "lexicographic", lex, 12.5))
    lex_nt = C.run_ilp_case(inst, lib, time_limit=TIME_LIMIT, lexicographic=True, no_transfers=True)
    rows.append(_row("toy", "ILP", "lexicographic+no_transfers", lex_nt, 106.0))

    # --- 6-7: baselines ---------------------------------------------------
    b_none = C.run_baseline_case(inst, lib, {"transfer_rule": "NONE"}, label="baseline NONE")
    rows.append(_row("toy", "baseline", "transfer_rule=NONE", b_none, 108.0,
                     {"baseline_flags": json.dumps({k: b_none["flags"][k] for k in
                                                    ("queued_at_H", "wait_slots_in_queue", "end_shortfalls",
                                                     "terminal_violations", "inventory_consistent")},
                                                   default=str)}))
    b_rp = C.run_baseline_case(inst, lib, {"transfer_rule": "REORDER_POINT"}, label="baseline REORDER_POINT")
    rows.append(_row("toy", "baseline", "transfer_rule=REORDER_POINT", b_rp, 14.5,
                     {"baseline_flags": json.dumps({k: b_rp["flags"][k] for k in
                                                    ("queued_at_H", "wait_slots_in_queue", "end_shortfalls",
                                                     "terminal_violations", "inventory_consistent")},
                                                   default=str)}))

    # --- 6b: old (round-1) vs new (round-2) baseline rules -------------------
    variant_rows: List[Dict[str, Any]] = []
    for variant in ("default", "round1", "legacy"):
        for rule in ("NONE", "REORDER_POINT"):
            params = bl.baseline_variant_params(variant, transfer_rule=rule)
            rec = C.run_baseline_case(inst, lib, params, label=f"baseline {variant} {rule}")
            variant_rows.append({
                "variant": variant, "transfer_rule": rule, "total": rec["cost"]["total"],
                "C_travel": rec["cost"]["C_travel"], "C_elec": rec["cost"]["C_elec"],
                "unserved": rec["cost"]["C_orders_parts"]["unserved"],
                "response": rec["cost"]["C_orders_parts"]["response"], "C_reb": rec["cost"]["C_reb"],
                "n_swaps": rec["flags"]["n_swaps"], "charge_steps": sum(rec["schedule"].c.values()),
                "stock_aware_reroutes": rec["flags"].get("stock_aware_reroutes"),
                "stock_aware_fallbacks": rec["flags"].get("stock_aware_fallbacks"),
                "charge_rule_effective": json.dumps(rec["flags"].get("charge_rule_effective"), default=str),
                "reported_families": json.dumps(rec["families"]),
                "ok_modulo_report_only": rec["ok_modulo_report_only"],
                "identity_24_ok": rec["identity_24_ok"],
            })
            rows.append(_row("toy", "baseline", f"variant={variant}, transfer_rule={rule}", rec,
                             {"NONE": 108.0, "REORDER_POINT": 14.5}[rule]))

    # --- 8: baselines as MIP starts ----------------------------------------
    ilp_rp_start = C.run_ilp_case(inst, lib, mip_start=b_rp["schedule"], time_limit=TIME_LIMIT)
    rows.append(_row("toy", "ILP", "MIP start = baseline REORDER_POINT", ilp_rp_start, 12.5,
                     {"mip_start_accepted": ilp_rp_start["mip_start_accepted"],
                      "mip_start_obj": ilp_rp_start["mip_start_info"]["start_obj"],
                      "mip_start_verified_status": ilp_rp_start["mip_start_info"]["verified_status"]}))
    ilp_none_start = C.run_ilp_case(inst, lib, mip_start=b_none["schedule"], time_limit=TIME_LIMIT)
    rows.append(_row("toy", "ILP", "MIP start = baseline NONE", ilp_none_start, 12.5,
                     {"mip_start_accepted": ilp_none_start["mip_start_accepted"],
                      "mip_start_obj": ilp_none_start["mip_start_info"]["start_obj"],
                      "mip_start_verified_status": ilp_none_start["mip_start_info"]["verified_status"]}))
    ilp_none_start_nt = C.run_ilp_case(inst, lib, mip_start=b_none["schedule"], time_limit=TIME_LIMIT,
                                       no_transfers=True)
    rows.append(_row("toy", "ILP", "no_transfers, MIP start = baseline NONE", ilp_none_start_nt, 106.0,
                     {"mip_start_accepted": ilp_none_start_nt["mip_start_accepted"],
                      "mip_start_obj": ilp_none_start_nt["mip_start_info"]["start_obj"],
                      "mip_start_verified_status": ilp_none_start_nt["mip_start_info"]["verified_status"]}))

    # --- 9: Battery_Swap p.7 ------------------------------------------------
    p7 = C.make_instance("p7")
    lib7, _ = C.build_library(p7, {})
    b7 = C.run_baseline_case(p7, lib7, None, label="baseline p7")
    df7 = C.inventory_table(p7, lib7, b7["schedule"])
    p7_ok = table_matches(df7, P7_TABLE, ["J"], p7.L)
    rows.append(_row("p7", "baseline", "default", b7, 0.1, {"p7_table_reproduced": p7_ok}))
    ilp7 = C.run_ilp_case(p7, lib7, mip_start=b7["schedule"], time_limit=TIME_LIMIT)
    rows.append(_row("p7", "ILP", "rho=0, MIP start = baseline", ilp7, 0.0,
                     {"mip_start_accepted": ilp7["mip_start_accepted"],
                      "mip_start_obj": ilp7["mip_start_info"]["start_obj"],
                      "mip_start_verified_status": ilp7["mip_start_info"]["verified_status"]}))
    p7b = C.make_instance("p7")
    p7b.rho = 1.0
    p7b.q_res = 2
    p7b.bikes = p7b.bikes[:1]
    p7b.reindex()
    ilp7b = C.run_ilp_case(p7b, build_arcs(p7b), time_limit=TIME_LIMIT)
    # one bike must leave full (q_res = 2 -> swap) and rho = 1 forces the returned
    # empty battery to be recharged to full: two charging steps = 0.1
    rows.append(_row("p7", "ILP", "rho=1, q_res=2, one bike", ilp7b, 0.1,
                     {"n_swaps": (ilp7b["metrics"] or {}).get("n_swaps")}))

    # --- tables, figures ------------------------------------------------------
    df = C.write_csv(rows, os.path.join(out_dir, "results.csv"))
    cols = ["case", "method", "switches", "status", "total", "expected", "match", "C_travel", "C_elec",
            "unserved", "response", "lateness", "C_reb", "runtime_s", "check_ok", "reported_families",
            "identity_24_ok", "obj_eq_cost", "mip_start_accepted", "lex_min_unserved"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    md.append("## Results")
    md.append("")
    md.append(C.markdown_table(df, cols))
    md.append("")
    md.append("`match` compares `total` with the documented value; `reported_families` lists the "
              "constraint families `evaluate.check` reports (the baseline may report (9), (17), (18) "
              "without being wrong); `obj_eq_cost` is Gurobi objective == `evaluate.cost` total; "
              "`mip_start_accepted` is certified by the fix-and-solve verification of `ilp.set_mip_start`.")
    md.append("")

    inv = C.inventory_table(inst, lib, ilp_default["schedule"])
    p15_ok = table_matches(inv, P15_TABLE, ["A", "C"], inst.L)
    md.append("## Inventory table of the toy optimum (E2 p.15)")
    md.append("")
    md.append(f"Reproduces the documented table: **{p15_ok}**.")
    md.append("")
    md.append(C.markdown_table(inv))
    md.append("")
    md.append("Bike paths of the optimum:")
    md.append("")
    for k in [b.id for b in inst.bikes]:
        md.append(f"- bike {k}: " + "; ".join(C.path_description(inst, lib, ilp_default["schedule"], k)))
    md.append("")
    md.append(f"Transfers: h = {ilp_default['schedule'].h}, z = {_jsonable(ilp_default['schedule'].z)}, "
              f"charging c = {_jsonable(ilp_default['schedule'].c)}.")
    md.append("")

    md.append("## Baseline rules: round 1 vs round 2 (DECISIONS R2.3)")
    md.append("")
    md.append("Cases 6-7 use the round-2 defaults of `BaselineParams` (`stock_aware_site=True`, "
              "`charge_rule='DEMAND_AWARE'` with lead = lookback = 12, charge-only hubs under "
              "`hub_charge_rule='HIGH_FIRST'`). `round1` = nearest site regardless of stock + ASAP "
              "HIGH_FIRST charging (the round-1 policy after the reviewer fixes); `legacy` = round1 "
              "without JIT dispatch and dead-zone rule. On the toy the three variants coincide in cost: "
              "A is the only swap site (stock-aware choice can only fall back to it) and the hub C "
              "follows HIGH_FIRST, so DEMAND_AWARE changes nothing. The literal R2.3 reading at the hub "
              "(`hub_charge_rule='DEMAND_AWARE'`) would give 14.4 with a reported (18) shortfall of 1 "
              "(see `tests/test_baseline.py`).")
    md.append("")
    vdf = pd.DataFrame(variant_rows)
    md.append(C.markdown_table(vdf, list(vdf.columns)))
    md.append("")
    md.append("## Battery_Swap p.7 inventory table (baseline policy)")
    md.append("")
    md.append(f"Reproduces the documented table: **{p7_ok}**.")
    md.append("")
    md.append(C.markdown_table(df7))
    md.append("")

    md.append("## Identities")
    md.append("")
    md.append(f"- (24) battery conservation holds on every schedule: {all(bool(r['identity_24_ok']) for r in rows if r['identity_24_ok'] is not None)}")
    md.append(f"- baseline online inventory == (13) recursion: NONE {b_none['flags']['inventory_consistent']}, "
              f"REORDER_POINT {b_rp['flags']['inventory_consistent']}, p7 {b7['flags']['inventory_consistent']}")
    md.append(f"- Gurobi objective == evaluate.cost total on every ILP run: {all(r.get('obj_eq_cost') for r in rows if r['method'] == 'ILP')}")
    md.append(f"- lexicographic: U* = {lex['lex_min_unserved']} (written model), "
              f"{lex_nt['lex_min_unserved']} (no_transfers)")
    md.append("")

    fig1 = C.plot_inventory(inst, lib, ilp_default["schedule"], os.path.join(out_dir, "inventory_toy.png"),
                            title="Toy optimum: stock n_jqt (p.15)")
    comp_recs = []
    for r in rows:
        if r["case"] == "toy" and r["total"] is not None:
            comp_recs.append({"label": f"{r['method']} {r['switches']}", **{f"x_{k}": r.get(k) for k in
                              ("C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "C_reb")}})
    fig2 = C.plot_cost_components(comp_recs, os.path.join(out_dir, "cost_components.png"), prefixes=("x_",),
                                  title="Toy: cost components per case")
    md.append("## Figures")
    md.append("")
    md.append(f"- `{os.path.basename(fig1)}`: stock trajectories of the toy optimum")
    md.append(f"- `{os.path.basename(fig2)}`: cost components per toy case")
    md.append("")
    with open(os.path.join(out_dir, "RESULTS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    for r in rows:
        print(f"{r['case']:>4} {r['method']:>8} {r['switches']:<40} total={C.fmt(r['total'])} "
              f"expected={C.fmt(r['expected'])} match={r['match']} check={r['check_ok']} fams={r['reported_families']}")
    print("p.15 table reproduced:", p15_ok, "| p.7 table reproduced:", p7_ok)
    return rows


def _with(inst, **changes):
    """Copy of the toy with scalar fields changed (rho, q_res, ...)."""
    import copy
    new = copy.deepcopy(inst)
    for k, v in changes.items():
        setattr(new, k, v)
    return new


def _jsonable(d: Dict[Any, Any]) -> str:
    return json.dumps({str(k): v for k, v in d.items()}, default=str)


if __name__ == "__main__":
    main()
