"""Toy bilevel example of the ITSC siting paper (laptop only: Gurobi Threads 1, seconds).

Writes, next to the paper (``paper_itsc/figs/``):
  toy_table.tex        every admissible layout at one and two budget units, in two column groups by the number of
                       open sites: its exact cost and the lower bound the certificate assigns to it; the layouts the
                       loop costed in bold, the brute-force best at each budget starred (ties included)
  fig_toy.{pdf,png}    the two riders' optimal plan on the best one-unit layout, evening 1:
                       corner and charge against time, swaps and deliveries marked
  toy_example.json     every number used in the text (set-up, lower level, upper level, certificate)

The toy is ``sites_nyc.toy_base_instance`` with the four candidates of ``tests/test_r7_siting.py``
(``CANDS4``) and ``sites_nyc.TOY_SPEC``: a street of five corners 0..4 (0.5 km, one 5-minute slot and
one charge level per hop), two riders starting at corner 0 with 3 of 6 levels, four orders per
evening, two evenings (seeds 0 and 1, equal weight), 12 slots.  The menu is ONE option, a
swap-and-charge site with two spare batteries and one charger, whose investment (100 + 2*10 + 1*10
= 130) is exactly one budget unit, so budget m opens at most m sites.  Riders follow the
all-candidates convention (reposition toward any candidate); the open-sites values are computed
too and reported in the JSON.  End targets are relaxed (rho = R_end = 0) as in the paper.

Ground truth: every layout is solved exactly (MIPGap 0).  Certificate: ``benders.SitingCertifier``
(the paper's method: root bound, safe cuts, integer L-shaped cuts, master problem) on the same
evaluator; the script asserts that UB_m = LB_m = the exhaustive optimum at m = 1, 2.

The table and the figure are drawn from the JSON record only (``write_table``, ``draw_figure``): the full run writes
the JSON first and then draws from it, ``--redraw`` draws from the JSON on disk.

Run:  cd ebike_swap_sim && nice -n 15 python3 ../paper_itsc/figs/src/toy_example.py
      python3 paper_itsc/figs/src/toy_example.py --redraw
                                     (R11: toy_table.tex and fig_toy.{pdf,png} only, from figs/toy_example.json;
                                     no solve, no gurobipy, and the JSON is never rewritten)
Set ``BSWAP_ROOT`` when the script runs from a copy of the paper folder.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.dirname(HERE)                                                  # paper_itsc/figs
ROOT = os.environ.get("BSWAP_ROOT") or os.path.dirname(os.path.dirname(FIGS))  # OR Model-Battery Swap
SIM = os.path.join(ROOT, "ebike_swap_sim")
JSON_PATH = os.path.join(FIGS, "toy_example.json")
REDRAW = "--redraw" in sys.argv[1:]      # read before the solver imports: the redraw path needs no gurobipy

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.text  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

TOL = 1e-6
OURS, CONTEXT, INK, INK2 = "#2a78d6", "#b4b4b4", "#111111", "#555555"
OURS_DARK = "#1b4f8f"
# R11 (2026-10-31): axis titles 8 pt; ticks, legend and every label inside the plot FS = 7.5 pt (7.8 pt printed at
# \columnwidth; was 6 to 7 pt at 0.84\columnwidth, 5.4 pt printed)
FS = 7       # R16 (2026-11-09): drawn at the printed width (0.66 column) so all labels print at 7 pt or more
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "STIXGeneral"],
    "mathtext.fontset": "stix", "font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": FS,
    "ytick.labelsize": FS, "legend.fontsize": FS, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "savefig.dpi": 300,
})
COLUMN_BP = 252.0 * 72.0 / 72.27         # IEEEtran \columnwidth (21 pc) in PDF points: fig_toy's include width
NUM_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")


def _word(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else str(n)


# ----------------------------------------------------------------------------- (c) table, from the JSON record
def write_table(d):
    """``figs/toy_table.tex`` from the record ``d`` (the content of toy_example.json): the layouts in two column
    groups by the number of open sites (one site = one unit), exact cost and the certificate's lower bound; bold = the
    loop costed it (``priced == "PRICED"``), star = in the brute-force ties at some budget.  Asserts the caption's
    and the note's claims before writing them."""
    ul, cert = d["upper_level"], d["certificate"]
    best = {int(m): v for m, v in ul["best_exhaustive"].items()}          # JSON keys are strings
    ties = {k for v in best.values() for k in v["ties"]}
    n_costed = cert["n_layouts_costed"]

    def fmt(x):
        return "--" if x is None else f"{x:.2f}"

    groups, n_bold = {}, 0
    for lay in ul["layouts"]:
        sites, V, bound = lay["sites"], lay["V_all"], lay["bound"]
        n_open, name = len(sites), ", ".join(sites)
        rows = groups.setdefault(n_open, [])
        if V is None:                                                     # excluded by the feasibility rows
            rows.append(f"{name} & infeasible & --")
            continue
        star = "\\,$\\star$" if lay["key"] in ties else ""
        if lay["priced"] == "PRICED":
            n_bold += 1
            rows.append(f"\\textbf{{{name}}}{star} & \\textbf{{{fmt(V)}}} & \\textbf{{{fmt(bound)}}}")
        else:
            # the note's claim: the bound alone shows that a layout not costed cannot beat the best at its budget
            assert bound is not None and bound >= best[n_open]["V"] - TOL, (lay["key"], bound, best[n_open]["V"])
            rows.append(f"{name}{star} & {fmt(V)} & {fmt(bound)}")
    assert sorted(groups) == [1, 2], sorted(groups)
    assert n_bold == n_costed, (n_bold, n_costed)                          # bold = the layouts the loop costed
    for m in (1, 2):                                                       # the loop matches the brute-force best
        assert abs(cert["budgets"][str(m)]["UB"] - best[m]["V"]) <= TOL, (m, cert["budgets"][str(m)]["UB"], best[m])
    n_layouts = sum(len(v) for v in groups.values())                        # brute force solves every one of them
    n = max(len(v) for v in groups.values())
    left, right = (groups[g] + ["& &"] * (n - len(groups[g])) for g in (1, 2))
    rows_tex = [f"    {a} & {b} \\\\" for a, b in zip(left, right)]
    head = [f"\\multicolumn{{3}}{{@{{}}c}}{{{_word(1).capitalize()} site ({_word(1)} unit)}}",
            f"\\multicolumn{{3}}{{c@{{}}}}{{{_word(2).capitalize()} sites ({_word(2)} units)}}"]
    table = "\n".join([
        "% toy_table.tex -- written by figs/src/toy_example.py; do not edit by hand.",
        "% Every admissible layout of the toy at one and two budget units, in two column groups by the number of open",
        "% sites (one option per site: swap-and-charge, 2 spares, 1 charger = one unit).  Exact cost = the bilevel value",
        "% V(x) (set-up + mean operating cost over the two evenings).  Lower bound = the bound the certificate holds for",
        "% x (master rows, LP value or integer-program bound); -- for a layout excluded by the feasibility rows.",
        "% Bold = the certificate costed it (solved its lower-level programs); star = best at its budget by brute force",
        "% (ties included).  Every other feasible layout is pruned by its bound alone.",
        "\\begin{table}[t]",
        # R11 fix (2026-10-31): the caption says where the exact costs of every row come from (brute force), so that
        # "only the three in bold" does not read as a contradiction; the table spans the column (tabular*), so that
        # the note under it lines up with its rules
        f"  \\caption{{Toy example, upper level: brute force solves all {_word(n_layouts)} layouts; the loop "
        "(Algorithm~\\ref{alg:siting}) finds the same best ($\\star$) after solving only the "
        f"{_word(n_costed)} in bold}}\\label{{tab:toy}}",
        "  \\centering\\scriptsize",
        "  \\setlength{\\tabcolsep}{3pt}",
        "  \\begin{tabular*}{\\columnwidth}{@{\\extracolsep{\\fill}}lrr@{\\hspace{10pt}}lrr@{}}",
        "    \\toprule",
        f"    {head[0]} & {head[1]} \\\\",
        "    \\cmidrule(r){1-3}\\cmidrule(l){4-6}",
        "    Open sites & Exact cost & Lower bound & Open sites & Exact cost & Lower bound \\\\",
        "    \\midrule",
        *rows_tex,
        "    \\bottomrule",
        "  \\end{tabular*}\\par\\smallskip",
        "  {\\raggedright\\scriptsize Cost units per evening; a layout not in bold has a lower bound at or above the "
        "best cost at its budget, so the loop need not solve it.\\par}",
        "\\end{table}",
        "",
    ])
    with open(os.path.join(FIGS, "toy_table.tex"), "w", encoding="utf-8") as fh:
        fh.write(table)
    print(f"toy_table.tex: {n_layouts} layouts, {n_bold} costed (bold), {len(ties)} starred")


# ----------------------------------------------------------------------------- (c) figure, from the JSON record
def draw_figure(d):
    """``figs/fig_toy.{pdf,png}`` from the record ``d``: the riders' plan of evening 1 on the best one-unit layout
    (``lower_level``).  R11 (2026-10-31): 3.5 x 2.3 in, included at \\columnwidth; the order release and due markers
    and their numbers are gone; one legend row of four entries.  R11 fix: the four "order k" labels are gone too (the
    text never cites an order number; "order 4" sat on the T4 guide line and "order 1"/"order 2" could be read as
    either rider's leg): the thick legs and the "carrying an order" key show that each rider delivers two orders."""
    st = d["setup"]
    H, L, q_res, corners = st["H"], st["L"], st["q_res"], st["corners"]
    cands = [(c["id"], c["corner"]) for c in st["candidates"]]
    low = d["lower_level"]
    open_sites = {part.split(":", 1)[0] for part in low["layout"].split("|")}
    open_corners = {node for cid, node in cands if cid in open_sites}
    riders0 = low["evenings"][0]["riders"]
    fig, (ax, axq) = plt.subplots(2, 1, figsize=(2.15, 1.245), sharex=True,
                                  gridspec_kw={"height_ratios": [2.3, 0.9], "hspace": 0.1})
    styles = [dict(color=OURS, ls="-"), dict(color=OURS_DARK, ls=(0, (3, 1.2)))]
    # context: candidate rows and the open site
    for cid, node in cands:
        if node in open_corners:
            ax.axhspan(node - 0.22, node + 0.22, color=OURS, alpha=0.13, lw=0, zorder=0)
            ax.text(H + 0.15, node, f"{cid} open", fontsize=FS, color=OURS, va="center", ha="left")
        else:
            ax.axhline(node, color=CONTEXT, lw=0.5, ls=":", zorder=0)
            ax.text(H + 0.15, node, cid, fontsize=FS, color=INK2, va="center", ha="left")
    for node in st["depots"]:
        ax.text(H + 0.15, node, "start", fontsize=FS, color=INK2, va="center", ha="left")
    # rider paths
    for rd, sty in zip(riders0, styles):
        for a in rd["arcs"]:
            if a["kind"] in ("wait", "move"):
                ax.plot([a["t0"], a["t1"]], [a["from"], a["to"]], lw=0.9, zorder=3, **sty)
            elif a["kind"] == "deliver":
                ta, tp = a["t_arrive_restaurant"], a["t_leave_restaurant"]
                ax.plot([a["t0"], ta], [a["from"], a["restaurant"]], lw=0.9, zorder=3, **sty)      # to the restaurant
                ax.plot([ta, tp], [a["restaurant"], a["restaurant"]], lw=0.9, zorder=3, **sty)     # wait + pickup
                ax.plot([tp, a["t1"]], [a["restaurant"], a["customer"]], lw=2.4, solid_capstyle="round", zorder=4,
                        **sty)
            elif a["kind"] == "swap":
                ax.plot([a["t0"], a["t1"]], [a["from"], a["to"]], lw=0.9, zorder=3, **sty)
                ax.plot([a["t0"]], [a["from"]], marker="D", ms=4, mfc="white", mec=sty["color"], mew=1.0, ls="",
                        zorder=5)
        # charge panel: linear within an arc, a jump at a swap
        a0 = rd["arcs"][0]
        xs, ys = [a0["t0"]], [a0["q0"]]
        for a in rd["arcs"]:
            if a["kind"] == "swap":
                xs += [a["t0"], a["t1"]]
                ys += [a["q0"], a["q1"]]
            else:
                xs.append(a["t1"])
                ys.append(a["q1"])
        axq.plot(xs, ys, lw=0.9, zorder=3, **sty)
        ax.plot([a0["t0"]], [a0["from"]], marker="o", ms=3, color=sty["color"], ls="", zorder=5)   # start
    ax.set_xlim(-0.3, H + 0.3)
    ax.set_ylim(min(corners) - 0.45, max(corners) + 0.6)
    ax.set_yticks(corners)
    ax.set_yticklabels([str(c) for c in corners])
    ax.set_ylabel("corner", labelpad=3)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
        axq.spines[sp].set_visible(False)
    axq.axhline(q_res, color=CONTEXT, lw=0.5, ls=":", zorder=0)
    axq.text(H + 0.15, q_res, "reserve", fontsize=FS, color=INK2, va="center", ha="left")
    axq.set_ylim(-0.3, L + 0.5)
    axq.set_yticks([0, L // 2, L])
    axq.set_ylabel("charge", labelpad=3)
    axq.set_xlabel(f"time slot $t$ ({st['slot_min']} min each)", labelpad=2)
    axq.set_xticks(range(0, H + 1, 2))
    handles = [Line2D([], [], color=styles[0]["color"], ls=styles[0]["ls"], lw=0.9, label="rider 1"),
               Line2D([], [], color=styles[1]["color"], ls=styles[1]["ls"], lw=0.9, label="rider 2"),
               Line2D([], [], color=OURS, lw=2.4, label="carrying an order"),
               Line2D([], [], marker="D", ms=4, mfc="white", mec=OURS, mew=1.0, ls="", label="swap")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, frameon=False, handlelength=1.6,
              columnspacing=0.9, handletextpad=0.4, borderaxespad=0.0, fontsize=FS)
    # checks on the drawn figure: the two y titles must not touch; the smallest text and its printed size
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    k = 72.0 / fig.dpi
    b_top, b_bot = ax.yaxis.label.get_window_extent(rend), axq.yaxis.label.get_window_extent(rend)
    gap = (b_top.y0 - b_bot.y1) * k
    assert gap > 0.0, f"fig_toy: the two y titles touch ({gap:.1f} pt)"
    small = min(t.get_fontsize() for t in fig.findobj(lambda o: isinstance(o, matplotlib.text.Text))
                if t.get_text().strip() and t.get_visible())
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGS, f"fig_toy.{ext}"), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    with open(os.path.join(FIGS, "fig_toy.pdf"), "rb") as fh:                   # the size as written
        m = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", fh.read())
    w_bp, h_bp = float(m.group(1)), float(m.group(2))
    s = 0.66 * COLUMN_BP / w_bp
    print(f"fig_toy: {w_bp:.1f} x {h_bp:.1f} bp; at \\columnwidth scale {s:.3f}, printed height {h_bp * s:.0f} bp; "
          f"smallest text {small:g} pt ({small * s:.2f} pt printed); y titles {gap:.1f} pt apart")


def redraw():
    """``--redraw``: toy_table.tex and fig_toy from figs/toy_example.json, which is read and never written."""
    with open(JSON_PATH, encoding="utf-8") as fh:
        d = json.load(fh)
    write_table(d)
    draw_figure(d)


if REDRAW:
    redraw()
    sys.exit(0)

# ----------------------------------------------------------------------------- full run: solver imports
sys.path.insert(0, SIM)
from ebike_swap_sim import benders as BD  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim.evaluate import cost as eval_cost  # noqa: E402
from experiments import common as C  # noqa: E402

# ----------------------------------------------------------------------------- set-up
CANDS4 = (("T1", 1), ("T2", 2), ("T3", 3), ("T4", 4))          # tests/test_r7_siting.py
SEEDS = (0, 1)                                                   # two demand evenings
MENU = {"SC": [(2, 1)]}                                          # one option: SC, B = 2, C = 1
FULL_MENU = {"S": [(1, 0), (2, 0)], "C": [(0, 1)], "SC": [(1, 1), (2, 1)]}   # the tests' menu, for counts only
PARAMS = {"Seed": 0, "MIPGap": 0.0}
SPEC = S.TOY_SPEC
UNIT = SPEC.Fhat + SPEC.bhat * 2 + SPEC.chat * 1                 # 130: one SC(2,1) site
BUDGETS = [UNIT, 2 * UNIT]


def r2(x):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), 2)


def site_of(fid):
    return S.split_facility_id(fid)[0] if fid else None


# ----------------------------------------------------------------------------- data
scen = [S.toy_base_instance(seed, candidates=CANDS4) for seed in SEEDS]
disc = scen[0].disc
setup_json = {
    "corners": list(scen[0].nodes), "hop_km": 0.5, "hop_slots": 1, "hop_levels": 1,
    "slot_min": round(disc.Delta_h * 60), "H": disc.H, "L": disc.L,
    "riders": [{"id": b.id, "start": b.v0, "q0": b.q0} for b in scen[0].bikes],
    "candidates": [{"id": cid, "corner": node} for cid, node in CANDS4],
    "depots": scen[0].meta["depots"],
    "evenings": [{"seed": seed, "weight": 1.0 / len(SEEDS),
                  "orders": [{"id": o.id, "restaurant": o.o, "customer": o.d, "release": o.r, "ready": o.a,
                              "due": o.b, "pickup_slots": o.hp, "dropoff_slots": o.hd} for o in inst.orders]}
                 for seed, inst in zip(SEEDS, scen)],
    "prices": {"unserved_P": scen[0].orders[0].P, "response_per_h": scen[0].orders[0].w,
               "lateness_per_h": scen[0].orders[0].v, "riding_per_km": scen[0].kappa,
               "electricity_per_kwh": scen[0].pi, "kwh_per_level": disc.eps_kwh, "transfer_trip_f": SPEC.f,
               "transfer_per_battery": SPEC.vreb},
    "site": {"role": "SC", "B": 2, "C": 1, "K": SPEC.K, "Cbar": SPEC.Cbar, "M": SPEC.M, "sigma": SPEC.sigma,
             "setup_per_day": SPEC.F + SPEC.bB * 2 + SPEC.bC * 1, "F": SPEC.F, "bB": SPEC.bB, "bC": SPEC.bC,
             "investment": UNIT, "Fhat": SPEC.Fhat, "bhat": SPEC.bhat, "chat": SPEC.chat},
    "budget_unit": UNIT, "q_res": scen[0].q_res, "end_targets": "relaxed (rho = R_end = 0)",
}

# the paper's evaluator: all-candidates riders, relaxed end targets, exact lower-level solves
ev_all = BL.LowerLevelEvaluator(scen, SPEC, time_limit=60.0, threads=1, params=PARAMS, aggregate=True,
                                reposition="all_candidates").derive(relaxed_targets=True)
ev_open = BL.LowerLevelEvaluator(scen, SPEC, time_limit=60.0, threads=1, params=PARAMS, aggregate=True,
                                 reposition="open_sites").derive(relaxed_targets=True)
enc = BD.MenuEncoding([c.id for c in ev_all.candidates], MENU, S.ROLES, SPEC)

# ----------------------------------------------------------------------------- (b) upper level, ground truth
t0 = time.perf_counter()
layouts = BL.enumerate_layouts(ev_all.candidates, enc.options, BUDGETS[-1], SPEC, (1, 2), s_needs_charge=True)
truth = {}
for lay in layouts:
    e = ev_all.evaluate(lay, "ilp")
    eo = ev_open.evaluate(lay, "ilp")
    truth[lay.key()] = {"layout": lay, "units": int(round(lay.investment(SPEC) / UNIT)), "sites": list(lay.locations()),
                        "setup": e["C_setup"], "V_all": e["V"], "opex_all": e["opex"], "statuses": e["statuses"],
                        "V_open": eo["V"], "opex_open": eo["opex"],
                        "served_share": e.get("served_share")}
t_truth = time.perf_counter() - t0
best = {}
for m, b in enumerate(BUDGETS, start=1):
    feas = [(v["V_all"], k) for k, v in truth.items() if v["units"] <= m and v["V_all"] not in (None, BL.INF)]
    v_star, k_star = min(feas)
    ties = sorted(k for v, k in feas if abs(v - v_star) <= TOL)
    best[m] = {"V": v_star, "layout": k_star, "ties": ties, "n_admissible": sum(1 for v in truth.values() if v["units"] <= m),
               "n_feasible": len(feas)}

# ----------------------------------------------------------------------------- (b) certificate
records = []
t0 = time.perf_counter()
cert = BD.SitingCertifier(ev_all, BUDGETS, MENU, S.ROLES, s_needs_charge=True, tol_rel=1e-9, tol_abs=TOL,
                          lp_threads=1, master_threads=1, on_record=records.append)
# one-site feasibility screen (Algorithm 1, step m = 1): a site some rider cannot reach is dropped
# without any solve, and the master gets its terminal row
screen = {}
for loc, _node in CANDS4:
    for s in range(ev_all.n_scenarios):
        stuck = BD.verify_terminal_infeasible(ev_all, BL.Layout.of([(loc, "SC", 2, 1)]), s)
        if stuck:
            screen[loc] = {"evening": SEEDS[s], "riders_stuck": stuck}
            cert.mark_terminal_infeasible(loc, s, role="SC", bikes=stuck, source="toy_example")
            break
res = cert.run()
t_cert = time.perf_counter() - t0
root_bound = list(cert.L)
cert_json = {}
for m, b in enumerate(BUDGETS, start=1):
    r = res[b]
    cert_json[m] = {"UB": r["UB"], "LB": r["LB"], "gap": r["gap"], "certified": bool(r["certified"]),
                    "best_layout": r["best_layout"], "LB_kind": r["LB_kind"], "LB_root_trivial": r["LB_superset"],
                    "LB_LP_phase": r["LB_LP"]}
    assert r["certified"], (m, r)
    assert abs(r["UB"] - best[m]["V"]) <= 1e-6, (m, r["UB"], best[m]["V"])
    assert r["LB"] >= best[m]["V"] - 1e-6, (m, r["LB"], best[m]["V"])
counters = dict(cert.counters)
n_priced_layouts = len([k for k, pr in cert.priced.items() if pr.n_solves > 0 or pr.status == "PRICED"])
# per-layout bound known to the certificate: max(master rows at x, LP value, pricing bound); inf if excluded
per_layout = {}
for lay in layouts:
    k = lay.key()
    pr = cert.priced.get(k)
    ok = cert.master.rows_ok(lay)
    env = cert.master.envelope(lay) if ok else BL.INF
    vlp = cert.v_lp(lay) if k in cert.lp_memo else None
    lo = env
    if vlp is not None:
        lo = max(lo, vlp)
    if pr is not None and pr.status == "INFEASIBLE":
        lo = BL.INF
    elif pr is not None:
        lo = max(lo, pr.lower)
    per_layout[k] = {"rows_ok": bool(ok), "envelope": None if env == BL.INF else env, "v_LP": vlp,
                     "priced": None if pr is None else pr.status, "bound": lo}
    V = truth[k]["V_all"]
    if V not in (None, BL.INF):
        assert lo <= V + 1e-6, (k, lo, V)
# pair screen (eq. pairscreen): regional LP per pair of sites, one LP per evening
pairs = {}
ub2, tol2 = cert.UB[BUDGETS[1]], cert.tol(cert.UB[BUDGETS[1]])
for lay in layouts:
    if lay.n_open != 2:
        continue
    atoms = list(lay.locations())
    lba = cert.subset_bound(atoms)
    setup_min = BD.setup_min(enc, 2, atoms, s_needs_charge=True)
    lb_pair = setup_min + sum(p * x for p, x in zip(cert.p, lba))
    pairs[lay.key()] = {"sites": atoms, "LB_pair": lb_pair, "LB_pair_scenarios": lba, "setup_min": setup_min,
                        "cannot_beat_UB2": bool(lb_pair >= ub2 - tol2 - 1e-9), "V_exact": truth[lay.key()]["V_all"]}
    assert lb_pair <= truth[lay.key()]["V_all"] + 1e-6
cert.close()

# how the search space grows with the menu (counts only, no solve)
counts = {}
for name, menu in (("one_option", MENU), ("tests_menu", FULL_MENU)):
    enc_m = BD.MenuEncoding([c.id for c in ev_all.candidates], menu, S.ROLES, SPEC)
    counts[name] = {m: len(BL.enumerate_layouts(ev_all.candidates, enc_m.options, m * UNIT, SPEC, tuple(range(1, m + 1)),
                                                 s_needs_charge=True)) for m in (1, 2, 3)}

# ----------------------------------------------------------------------------- (a) lower level on the best one-unit layout
lay1 = BL.Layout.from_key(best[1]["layout"])
lower = {"layout": lay1.key(), "evenings": []}
for s in range(len(scen)):
    inst, lib = ev_all.layout_pair(lay1, s)
    rec = C.run_ilp_case(inst, lib, time_limit=60.0, threads=1, label="toy", params=PARAMS, fixed_facilities=True,
                         aggregate=True)
    sched = rec["schedule"]
    assert sched is not None and rec["status"] == "OPTIMAL", rec["status"]
    cst = eval_cost(inst, lib, sched)
    assert abs(cst["total"] - truth[lay1.key()]["setup"] - truth[lay1.key()]["opex_all"][s]) <= 1e-6
    riders = []
    for k in sorted(sched.x):
        arcs = []
        for a in sched.path(k, lib):
            if a.kind == "term":
                continue
            d = {"kind": a.kind, "from": a.src[0], "t0": a.src[1], "q0": a.src[2], "to": a.dst[0], "t1": a.dst[1],
                 "q1": a.dst[2], "km": a.d_km}
            if a.kind == "deliver":
                o = inst.order(a.order)
                t_arr = a.src[1] + inst.tau(a.src[0], o.o) if a.src[0] != o.o else a.src[1]
                t_pick = max(t_arr, o.a) + o.hp          # leaves the restaurant
                d.update(order=o.id, restaurant=o.o, customer=o.d, t_arrive_restaurant=t_arr, t_leave_restaurant=t_pick,
                         due=o.b, late_slots=max(0, a.dst[1] - o.b), response_slots=a.dst[1] - o.r)
            if a.kind == "swap":
                d.update(site=site_of(a.fac))
            arcs.append(d)
        riders.append({"rider": k, "arcs": arcs, "n_swaps": sum(1 for a in arcs if a["kind"] == "swap"),
                       "km": sum(a["km"] for a in arcs), "end_level": arcs[-1]["q1"] if arcs else None})
    unserved = sorted(i for i, v in sched.u.items() if v)
    charge_steps = sum(v for (j, q, t), v in sched.c.items() if v)
    lower["evenings"].append({
        "seed": SEEDS[s], "riders": riders, "unserved_orders": unserved, "charge_steps": charge_steps,
        "transfers_used": sum(1 for v in sched.h.values() if v),
        "cost": {"setup": cst["C_setup"], "electricity": cst["C_elec"], "riding": cst["C_travel"],
                 "orders": cst["C_orders"], "orders_unserved": cst["C_orders_parts"]["unserved"],
                 "orders_response": cst["C_orders_parts"]["response"], "orders_lateness": cst["C_orders_parts"]["lateness"],
                 "transfers": cst["C_reb"], "opex": cst["total"] - cst["C_setup"], "total": cst["total"]},
        "ilp": {"status": rec["status"], "runtime_s": rec["runtime"], "n_binaries": rec["n_binaries"], "n_rows": rec["n_rows"],
                "n_arcs": len(lib)},
    })

n_feas = sum(1 for v in truth.values() if v["V_all"] not in (None, BL.INF))

# ----------------------------------------------------------------------------- (d) JSON
out = {
    "setup": setup_json,
    "lower_level": lower,
    "upper_level": {
        "menu": {"SC": [[2, 1]]}, "budgets": BUDGETS, "n_layouts": len(layouts), "n_feasible": n_feas,
        "layouts": [{"key": k, "sites": v["sites"], "units": v["units"], "setup": v["setup"], "V_all": r2(v["V_all"]),
                     "opex_all": [r2(x) for x in v["opex_all"]], "V_open": r2(v["V_open"]),
                     "opex_open": [r2(x) for x in v["opex_open"]], "statuses": v["statuses"],
                     "served_share": v["served_share"], **{kk: (r2(vv) if isinstance(vv, float) else vv)
                                                            for kk, vv in per_layout[k].items()}}
                    for k, v in truth.items()],
        "best_exhaustive": best, "same_cost_both_conventions": all(
            (v["V_all"] == v["V_open"]) or (v["V_all"] in (None, BL.INF) and v["V_open"] in (None, BL.INF))
            or abs(v["V_all"] - v["V_open"]) <= 1e-6 for v in truth.values()),
        "layout_counts_by_menu": counts,
    },
    "certificate": {"budgets": cert_json, "root_bound_per_evening": root_bound, "counters": counters,
                    "one_site_screen": screen,
                    "n_layouts_costed": n_priced_layouts, "n_layout_lps": len(cert.lp_memo),
                    "pair_screen": pairs, "records_by_kind": {}},
    "timing_s": {"exhaustive_10_layouts_two_conventions": round(t_truth, 2), "certificate": round(t_cert, 2)},
    "files": ["figs/toy_table.tex", "figs/fig_toy.pdf", "figs/fig_toy.png", "figs/toy_example.json"],
}
for r in records:
    out["certificate"]["records_by_kind"][r["kind"]] = out["certificate"]["records_by_kind"].get(r["kind"], 0) + 1
txt = json.dumps(out, indent=1, default=lambda x: (None if isinstance(x, float) and not math.isfinite(x) else str(x)))
with open(JSON_PATH, "w", encoding="utf-8") as fh:
    fh.write(txt)

# ----------------------------------------------------------------------------- (c) table and figure, from the record
rec_json = json.loads(txt)
write_table(rec_json)
draw_figure(rec_json)
print(txt)
