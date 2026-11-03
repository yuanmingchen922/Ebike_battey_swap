"""Count the admissible Manhattan layouts per budget (Section V of the ITSC siting paper).

Numbers produced (paper lines: abstract, I-B Contributions, Section V "Upper level", Section VI opening):
  budget 1 unit :    236 admissible layouts (all one-site)
  budget 2 units:  97,040 (one-site + two-site)
  budget 3 units: 17,317,738 (one-, two- and three-site), printed as "17.3 million"

Inputs (nothing is typed by hand):
  * the size menu and the cost spec of the production run, read from the first ``plan`` record of
    ``ebike_swap_sim/outputs/r7_prod_final/r7_siting/records.jsonl``
    (menu S {2,3}; C {2,4}; SC {2,3,4} x {1,2}; Fhat 50,000, bhat 450, chat 400 USD);
  * the 59 candidate ids and their ``hub_capable`` flags from ``.../r7_siting/candidates.csv``
    (a hub may stand only at the 12 hub-capable sites);
  * one budget unit = 52,150 USD (one swap-and-charge site with three spares and two chargers).

A layout is admissible (rows (1)-(4) of the paper) when every open site has one menu option, the
investment is within the budget, at least one object can swap, and a swap-only cabinet is open only
together with a charge-capable object (``bilevel.enumerate_layouts(..., s_needs_charge=True)``).

Method: a dynamic programme over the 59 sites counts the layouts by (open sites, investment,
has-swap, has-charge, has-swap-only) in well under a second; for one and two units the count is
also checked against the explicit list of ``bilevel.enumerate_layouts`` (the routine the production
run used; its 236 one-site layouts are recorded in ``records.jsonl``).  Pass ``--enumerate-all`` to
list the three-unit layouts explicitly too (about two minutes and several GB on a laptop).

Writes ``paper_itsc/figs/layout_counts.json``.
Run:  cd ebike_swap_sim && nice -n 15 python3 ../paper_itsc/figs/src/layout_counts.py
Set ``BSWAP_ROOT`` when the script runs from a copy of the paper folder.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.dirname(HERE)                                                   # paper_itsc/figs
ROOT = os.environ.get("BSWAP_ROOT") or os.path.dirname(os.path.dirname(FIGS))  # OR Model-Battery Swap
SIM = os.path.join(ROOT, "ebike_swap_sim")
RUN = os.path.join(SIM, "outputs", "r7_prod_final", "r7_siting")
sys.path.insert(0, SIM)

from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402

UNIT = 52_150.0
BUDGETS = (1, 2, 3)
ROLE_SWAP = {"S": True, "SC": True, "C": False}
ROLE_CHARGE = {"S": False, "SC": True, "C": True}


def read_run():
    """Menu and spec of the production run, and the 59 candidates with their hub flags."""
    menu = spec = None
    with open(os.path.join(RUN, "records.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            if "menu" in r and "spec" in r:
                menu = {k: [tuple(v) for v in vs] for k, vs in r["menu"].items()}
                spec = S.SitingSpec.from_dict(r["spec"])
                break
    if menu is None:
        raise RuntimeError("no plan record with menu and spec in records.jsonl")
    cands = []
    with open(os.path.join(RUN, "candidates.csv")) as fh:
        for row in csv.DictReader(fh):
            cands.append(S.Candidate(id=row["id"], label=row["label"], source=row.get("cls", ""),
                                     lat=float(row["lat"]), lon=float(row["lon"]),
                                     node=(int(row["node_x"]), int(row["node_y"])),
                                     hub_capable=bool(int(row["hub_capable"]))))
    return menu, spec, cands


def options_per_site(menu, spec, cands):
    """``{site id: [(role, B, C), ...]}``: the menu, hubs only where ``hub_capable``."""
    grid = [o for o in BL.option_grid(menu, S.ROLES) if spec.valid_sizes(o[0], o[1], o[2])]
    return {c.id: [o for o in grid if o[0] != "C" or c.hub_capable] for c in cands}


def count_by_dp(opts, spec, budget):
    """Admissible layouts within ``budget`` by number of open sites, by a dynamic programme.

    State = (open sites, investment, has swap, has charge, has swap-only); one site at a time
    either stays closed or takes one of its options.  Investments are multiples of 50 USD, so the
    state space is tiny."""
    inv = {o: spec.Fhat + spec.bhat * o[1] + spec.chat * o[2] for os_ in opts.values() for o in os_}
    states = {(0, 0.0, False, False, False): 1}
    for site, os_ in opts.items():
        nxt = defaultdict(int)
        for (k, v, sw, ch, so), n in states.items():
            nxt[(k, v, sw, ch, so)] += n                       # site stays closed
            for o in os_:
                v2 = v + inv[o]
                if v2 > budget + 1e-9:
                    continue
                r = o[0]
                nxt[(k + 1, v2, sw or ROLE_SWAP[r], ch or ROLE_CHARGE[r], so or r == "S")] += n
        states = nxt
    out = defaultdict(int)
    for (k, v, sw, ch, so), n in states.items():
        if k == 0 or not sw or (so and not ch):             # rows (4): a swap object; S needs a charger
            continue
        out[k] += n
    return dict(sorted(out.items()))


def count_by_enumeration(opts, spec, cands, budget, k_max):
    """The explicit list of ``bilevel.enumerate_layouts`` (what the production run used)."""
    lays = BL.enumerate_layouts(cands, opts, budget, spec, range(1, k_max + 1), s_needs_charge=True)
    out = defaultdict(int)
    for lay in lays:
        out[lay.n_open] += 1
    return dict(sorted(out.items()))


def main(enumerate_all: bool = False) -> None:
    menu, spec, cands = read_run()
    assert len(cands) == 59, len(cands)
    n_hub = sum(1 for c in cands if c.hub_capable)
    opts = options_per_site(menu, spec, cands)
    result = {"unit_usd": UNIT, "n_candidates": len(cands), "n_hub_capable": n_hub,
              "menu": {k: [list(v) for v in vs] for k, vs in menu.items()},
              "investment": {"Fhat": spec.Fhat, "bhat": spec.bhat, "chat": spec.chat},
              "one_site_options_within_one_unit": sorted({o for os_ in opts.values() for o in os_
                                                          if spec.Fhat + spec.bhat * o[1] + spec.chat * o[2] <= UNIT}),
              "budgets": {}}
    for m in BUDGETS:
        t0 = time.time()
        by_k = count_by_dp(opts, spec, m * UNIT)
        rec = {"units": m, "budget_usd": m * UNIT, "by_open_sites": by_k, "total": sum(by_k.values()),
               "dp_seconds": round(time.time() - t0, 3)}
        if m <= 2 or enumerate_all:
            t0 = time.time()
            by_k_enum = count_by_enumeration(opts, spec, cands, m * UNIT, m)
            rec["by_open_sites_enumerated"] = by_k_enum
            rec["enumeration_seconds"] = round(time.time() - t0, 1)
            assert by_k_enum == by_k, (m, by_k_enum, by_k)
        result["budgets"][str(m)] = rec
        print(f"budget {m} unit(s): {rec['total']:,} admissible layouts  {by_k}")
    assert result["budgets"]["1"]["total"] == 236, "the production record says 236 one-site layouts"
    out = os.path.join(FIGS, "layout_counts.json")
    with open(out, "w") as fh:
        json.dump(result, fh, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main(enumerate_all="--enumerate-all" in sys.argv[1:])
