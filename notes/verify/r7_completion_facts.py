"""Completion runs of the one-to-three-site study (4-9 November 2026).

Re-derives, from the server records, every layout cost, extra-cost interval and proven range that the paper reports
for one to three budget units after the production run of 24 October 2026: 12 held-out evenings for every comparison
layout, the charging-only hubs within transfer range, the listed-site pair with four spares, the second three-site
layout, and a hub added to the best pair as a third unit.

usage (from the repository root):
    PYTHONPATH=ebike_swap_sim python3 notes/verify/r7_completion_facts.py \
        [records.jsonl] [cache_index.jsonl] > ebike_swap_sim/outputs/r7_completion/RESULTS_completion.md
defaults: ebike_swap_sim/outputs/r7_completion/records.jsonl and cache_index.jsonl.

How the numbers are read.
  In-sample (12 planning evenings, seeds 0-11): the last complete `price_open` record of a layout (set-up cost, the
  operating cost per evening, the open-sites lower bound, the solver status per evening).  An evening that was
  re-solved later with the same cache key and a lower cost replaces the first solve (the best pair's evenings 10-11).
  Held-out (seeds 100-111): the last `list_price` record with evaluator `out`; else the cache rows with seed >= 100.
  Intervals: paired, stratified 95 % intervals (`ebike_swap_sim.bilevel.stratified_ci`, Welch-Satterthwaite degrees
  of freedom), six strata (three demand levels x weekday / weekend, two evenings each), weights 5/42 per weekday
  evening and 2/42 per weekend evening.
  Proven range of a layout x' at budget m: [open-sites lower bound of x' - best cost found at m, cost of x' - lower
  bound at m]; the lower bound is 1,084.31 at one unit (open-sites riders) and 670.23 at two and three units.
"""
import collections
import json
import os
import sys

from ebike_swap_sim.bilevel import stratified_ci

P12 = [5 / 42] * 6 + [2 / 42] * 6
STR12 = [s // 2 for s in range(12)]
LB = {1: 1084.31, 2: 670.23, 3: 670.23}
INFEASIBLE = set()     # layouts whose pricing stopped at an infeasible evening
KEY = collections.OrderedDict([
    ("DOT Site 34", "D23:SC:B3:C2"),
    ("Cooper Square (coverage rule, one site)", "D18:SC:B3:C2"),
    ("Citi Bike dock E 14th St & 1st Ave", "D24:SC:B3:C2"),
    ("Best pair (Greenwich Village cell + E 62nd St dock)", "D07:SC:B3:C2|D45:SC:B3:C2"),
    ("Listed-site pair (Site 34 + E 62nd St dock)", "D23:SC:B3:C2|D45:SC:B3:C2"),
    ("Cabinet at E 14th St dock + full site at E 62nd St dock", "D24:S:B3:C0|D45:SC:B3:C2"),
    ("Spread rule (two sites)", "D30:SC:B3:C2|D58:SC:B3:C2"),
    ("DOT 2024 pilot pair", "D12:SC:B3:C2|D18:SC:B3:C2"),
    ("Coverage rule (two sites)", "D18:SC:B3:C2|D19:SC:B3:C2"),
    ("Full site at the cell + hub W 13th St", "D07:SC:B3:C2|D16:C:B0:C4"),
    ("Full site at the cell + hub Bowery", "D07:SC:B3:C2|D13:C:B0:C4"),
    ("Full site at the cell + hub Kenmare St", "D07:SC:B3:C2|D11:C:B0:C4"),
    ("Cabinet at the cell + hub W 13th St", "D07:S:B3:C0|D16:C:B0:C4"),
    ("Cabinet at the cell + hub Bowery", "D07:S:B3:C0|D13:C:B0:C4"),
    ("Cabinet at the cell + hub Kenmare St", "D07:S:B3:C0|D11:C:B0:C4"),
    ("Cabinet at the cell + hub W 92nd St (out of range)", "D07:S:B3:C0|D50:C:B0:C4"),
    ("Cabinet at the cell + hub W 42nd St (out of range)", "D07:S:B3:C0|D34:C:B0:C4"),
    ("Cabinet at E 62nd St dock + hub E 72nd St", "D45:S:B3:C0|D47:C:B0:C4"),
    ("Full site at E 62nd St dock + hub E 72nd St", "D45:SC:B3:C2|D47:C:B0:C4"),
    ("Best pair, four spares each", "D07:SC:B4:C2|D45:SC:B4:C2"),
    ("Listed-site pair, four spares each", "D23:SC:B4:C2|D45:SC:B4:C2"),
    ("Best pair + Site 34", "D07:SC:B3:C2|D23:SC:B3:C2|D45:SC:B3:C2"),
    ("Best pair + E 14th St dock", "D07:SC:B3:C2|D24:SC:B3:C2|D45:SC:B3:C2"),
    ("Coverage rule (three sites)", "D18:SC:B3:C2|D19:SC:B3:C2|D23:SC:B3:C2"),
    ("Best pair + hub W 13th St (third unit)", "D07:SC:B3:C2|D16:C:B0:C4|D45:SC:B3:C2"),
    ("Best pair + hub Bowery (third unit)", "D07:SC:B3:C2|D13:C:B0:C4|D45:SC:B3:C2"),
    ("Best pair + hub Kenmare St (third unit)", "D07:SC:B3:C2|D11:C:B0:C4|D45:SC:B3:C2"),
    ("Best pair + hub E 72nd St (third unit)", "D07:SC:B3:C2|D45:SC:B3:C2|D47:C:B0:C4"),
])
S34, PAIR, LISTED = "DOT Site 34", "Best pair (Greenwich Village cell + E 62nd St dock)", "Listed-site pair (Site 34 + E 62nd St dock)"
PAIR4, LISTED4 = "Best pair, four spares each", "Listed-site pair, four spares each"
# (layout, reference, budget units of the proven range; None = no proven range for this comparison)
ROWS = [
    ("Cooper Square (coverage rule, one site)", S34, 1),
    ("Citi Bike dock E 14th St & 1st Ave", S34, 1),
    (S34, PAIR, 2),
    (LISTED, PAIR, 2),
    ("Cabinet at E 14th St dock + full site at E 62nd St dock", PAIR, 2),
    ("Spread rule (two sites)", PAIR, 2),
    ("DOT 2024 pilot pair", PAIR, 2),
    ("Coverage rule (two sites)", PAIR, 2),
    ("Full site at the cell + hub W 13th St", PAIR, 2),
    ("Full site at the cell + hub Bowery", PAIR, 2),
    ("Full site at the cell + hub Kenmare St", PAIR, 2),
    ("Cabinet at the cell + hub W 13th St", PAIR, 2),
    ("Cabinet at the cell + hub Bowery", PAIR, 2),
    ("Cabinet at the cell + hub Kenmare St", PAIR, 2),
    ("Cabinet at the cell + hub W 92nd St (out of range)", PAIR, 2),
    ("Cabinet at the cell + hub W 42nd St (out of range)", PAIR, 2),
    ("Cabinet at E 62nd St dock + hub E 72nd St", PAIR, 2),
    ("Full site at E 62nd St dock + hub E 72nd St", PAIR, 2),
    (PAIR4, PAIR, None),
    (LISTED4, LISTED, None),
    (LISTED4, PAIR4, 3),
    ("Best pair + Site 34", PAIR4, 3),
    ("Best pair + E 14th St dock", PAIR4, 3),
    ("Coverage rule (three sites)", PAIR4, 3),
    ("Best pair + hub W 13th St (third unit)", PAIR, None),
    ("Best pair + hub Bowery (third unit)", PAIR, None),
    ("Best pair + hub Kenmare St (third unit)", PAIR, None),
    ("Best pair + hub E 72nd St (third unit)", PAIR, None),
    ("Best pair + hub W 13th St (third unit)", PAIR4, 3),
    ("Best pair + hub Bowery (third unit)", PAIR4, 3),
    ("Best pair + hub Kenmare St (third unit)", PAIR4, 3),
    ("Best pair + hub E 72nd St (third unit)", PAIR4, 3),
]


def load(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def insample(recs, cache):
    """layout key (as a frozenset of its objects) -> last complete price_open record, re-solved evenings merged."""
    best = {}
    for row in cache:
        if row.get("total") is None:
            continue
        k = row.get("key")
        if k not in best or row["total"] < best[k]["total"]:
            best[k] = row
    out = {}
    for r in recs:
        if r.get("kind") != "price_open":
            continue
        ub = r.get("ub")
        if r.get("status") == "INFEASIBLE":
            INFEASIBLE.add(frozenset(r["layout_key"].split("|")))
            continue
        if not ub or len(ub) != 12 or any(v is None for v in ub):
            continue
        r = dict(r)
        rows = [dict(x) for x in (r.get("rows") or [])]
        if len(rows) == 12 and all(x.get("key") for x in rows):
            ub2, lower, reb, served = [], 0.0, 0.0, 0.0
            for x in rows:
                b = best.get(x["key"])
                if b is not None and b["total"] < (x.get("total") or float("inf")) - 1e-9:
                    x.update(status=b.get("status"), total=b["total"], opex=b["opex"], bound=b.get("bound"), gap=b.get("gap"))
                ub2.append(x["opex"])
                p = P12[int(x["scenario"])]
                lower += p * float(x.get("bound") if x.get("bound") is not None else x["total"])
                comp = (b or {}).get("components") or {}
                reb += p * float(comp.get("C_reb") or 0.0)
                share = ((b or {}).get("metrics") or {}).get("served_share")
                served = None if (served is None or share is None) else served + p * float(share)
            r["ub"], r["rows"] = ub2, rows
            r["V"] = r["setup"] + sum(p * u for p, u in zip(P12, ub2))
            r["lower_open"], r["transfer_cost"] = lower, reb
            if served is not None:      # weighted mean of the evenings' served shares, re-solved evenings included
                r["served_share"] = served
        out[frozenset(r["layout_key"].split("|"))] = r
    return out


def heldout(recs, cache):
    """layout key (frozenset) -> {seed: operating cost} for seeds 100-111."""
    out = {}
    for r in recs:
        if r.get("kind") == "list_price" and r.get("evaluator") == "out":
            op = r.get("opex") or []
            if len(op) == 12 and all(v is not None for v in op):
                out[frozenset(r["layout_key"].split("|"))] = {100 + i: v for i, v in enumerate(op)}
    best = collections.defaultdict(dict)
    for row in cache:
        if (row.get("seed") or 0) < 100 or row.get("total") is None or row.get("opex") is None:
            continue
        lk, sd = frozenset(row["layout_key"].split("|")), int(row["seed"])
        if sd not in best[lk] or row["total"] < best[lk][sd][0]:
            best[lk][sd] = (row["total"], row["opex"])
    for lk, d in best.items():
        if lk not in out:
            out[lk] = {sd: v[1] for sd, v in d.items()}
    return out


def paired(d):
    c = stratified_ci(d, STR12, P12)
    return c["mean"], c["half"]


def main(rec_path, cache_path):
    recs, cache = load(rec_path), load(cache_path)
    ins, ho = insample(recs, cache), heldout(recs, cache)
    fs = lambda name: frozenset(KEY[name].split("|"))
    print("# Completion runs of the one-to-three-site study (4-9 November 2026)\n")
    print("Written by `notes/verify/r7_completion_facts.py` from `records.jsonl` and `cache_index.jsonl` in this folder")
    print("(the server's `outputs/r7_siting/records.jsonl` and `cache/index.jsonl` after the last run). All values are USD")
    print("per day with the evening's set-up share, for open-sites riders. `RESULTS_final.md` of the production run")
    print("(`../r7_prod_final/`) has the same point values with the earlier, narrower intervals (6 degrees of freedom) and")
    print("held-out values for six weekday evenings only.\n")
    print("## Layouts\n")
    print("| Layout | Key | Cost | Set-up | Open-sites lower bound | Orders served | Evenings at the time limit | Transfer cost |")
    print("|---|---|---|---|---|---|---|---|")
    for name, k in KEY.items():
        r = ins.get(fs(name))
        if r is None:
            why = "infeasible (stopped at the first infeasible evening)" if fs(name) in INFEASIBLE else "not priced"
            print(f"| {name} | `{k}` | {why} | | | | | |")
            continue
        st = collections.Counter(x.get("status") for x in r.get("rows") or [])
        tl = st.get("TIME_LIMIT", 0)
        served = r.get("served_share")
        print(f"| {name} | `{k}` | {r['V']:,.2f} | {r['setup']:.2f} | {r['lower_open']:,.2f} | "
              f"{'' if served is None else format(100 * served, '.1f') + ' %'} | {tl} of 12 | {r.get('transfer_cost', 0.0):.2f} |")
    print("\nTransfer cost: weighted mean of the van-trip and per-battery charges; 0.00 means no battery moved between sites.\n")
    print("## Extra cost of a layout over its reference (mean and half-width of the paired 95 % interval)\n")
    print("| Layout | Reference | 12 planning evenings | 12 held-out evenings | Proven range |")
    print("|---|---|---|---|---|")
    for a, b, m in ROWS:
        ra, rb = ins.get(fs(a)), ins.get(fs(b))
        if ra is None or rb is None:
            print(f"| {a} | {b} | {'infeasible' if fs(a) in INFEASIBLE else 'not priced'} | | |")
            continue
        d = [ra["setup"] + u - (rb["setup"] + v) for u, v in zip(ra["ub"], rb["ub"])]
        mu, h = paired(d)
        cell_in = f"{mu:+.2f} ± {h:.2f}"
        ha, hb = ho.get(fs(a), {}), ho.get(fs(b), {})
        seeds = [s for s in range(100, 112) if s in ha and s in hb]
        if len(seeds) == 12:
            d = [ra["setup"] + ha[s] - (rb["setup"] + hb[s]) for s in seeds]
            mu, h = paired(d)
            cell_out = f"{mu:+.2f} ± {h:.2f}"
        else:
            cell_out = f"not complete ({len(seeds)} of 12)"
        rng = "" if m is None else f"[{ra['lower_open'] - rb['V']:.2f}, {ra['V'] - LB[m]:.2f}]"
        print(f"| {a} | {b} | {cell_in} | {cell_out} | {rng} |")
    print("\nThe proven range is given where the reference is the best layout found at that budget.")


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ebike_swap_sim", "outputs", "r7_completion")
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "records.jsonl"),
         sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "cache_index.jsonl"))
