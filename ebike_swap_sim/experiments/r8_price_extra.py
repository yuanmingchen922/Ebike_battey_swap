"""Price extra 15-site layouts on the planning and held-out evenings of an r8_k15 run (R14, 2026-11-06).

The size polish of ``r8_k15.py`` accepts the FIRST improving move of each round, so a priced candidate that was not
accepted can be cheaper on the six search evenings than the returned layout (run r8_k15_sp: polish_r4_2 at 8,333.5
against the returned 8,408.6).  This script costs such candidates on the 12 planning evenings and the 12 held-out
evenings, next to the run's best layout, with the run's own evaluators and cache (cells already priced are not
solved again).  Records ``price15`` rows tagged ``extra_in`` / ``extra_out`` in the run's records.jsonl.

usage: the r8_k15.py arguments of the run (same --out-dir etc.) plus  --extra NAME=LAYOUT_KEY [...]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experiments import r8_k15 as K  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--extra":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                n, _, k = argv[i].partition("=")
                extra.append((n, k))
                i += 1
            continue
        rest.append(argv[i])
        i += 1
    args = K.parse_args(rest + ["--stage", "final"])
    run = K.Run(args)
    try:
        ctx = K.Ctx(run)
        ctx.attach(("in", "out"))
        summ = json.load(open(os.path.join(run.dir, "search_summary.json"), encoding="utf-8"))
        named = [("best", BL.Layout.from_key(summ["best"]["layout_key"]))] + [(n, BL.Layout.from_key(k)) for n, k in extra]
        res_in = ctx.price(ctx.ev, named, tag="extra_in")
        res_out = ctx.price(ctx.ev_out, named, tag="extra_out") if ctx.ev_out is not None else {}
        strata = [ctx.stratum_of(ctx.ev, s) for s in range(ctx.ev.n_scenarios)]
        b = res_in["best"]
        out = {}
        for n, lay in named:
            r = res_in[n]
            row = {"layout_key": lay.key(), "V_in": r.get("V"), "served_in": r.get("served_share"), "complete_in": r.get("complete"),
                   "V_out": (res_out.get(n) or {}).get("V"), "served_out": (res_out.get(n) or {}).get("served_share")}
            if n != "best" and r.get("complete") and b.get("complete"):
                d = [float(x) - float(y) for x, y in zip(r["opex"], b["opex"])]
                ci = BL.stratified_ci(d, strata, ctx.ev.p)
                row["vs_best_in"] = {"mean": r["V"] - b["V"], "half": ci["half"], "df": ci["df"]}
                ro, bo = res_out.get(n) or {}, res_out.get("best") or {}
                if ro.get("complete") and bo.get("complete"):
                    so = [ctx.stratum_of(ctx.ev_out, s) for s in range(ctx.ev_out.n_scenarios)]
                    d = [float(x) - float(y) for x, y in zip(ro["opex"], bo["opex"])]
                    ci = BL.stratified_ci(d, so, ctx.ev_out.p)
                    row["vs_best_out"] = {"mean": ro["V"] - bo["V"], "half": ci["half"], "df": ci["df"]}
            out[n] = row
        run.emit({"kind": "extra_result", "layouts": out}, echo=True)
        print(json.dumps(out, indent=1))
        return out
    finally:
        K.close_pool()


if __name__ == "__main__":
    main()
