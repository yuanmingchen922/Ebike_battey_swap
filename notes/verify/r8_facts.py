"""Re-derive the derived numbers of the R8 fifteen-site facts sheets.

    notes/r8_results_facts.md        plan B = r8_k15_sp  (each site its own 1.4 kW connection, shared limit lifted;
                                                          the result of record, author's decision 2026-10-30)
    notes/r8_results_facts_planA.md  plan A = r8_k15_n64 (all sites share one 2 kW supply, paper eq. (16))

Read-only: reads the downloaded run folders, the project's data files and the paper's own map helpers
(paper_itsc/figs/src/make_figs.py, imported, no figure or table is written). Laptop only, about 15 s.

    python3 -I notes/verify/r8_facts.py "$PWD"                      (plan B, from the project root)
    python3 -I notes/verify/r8_facts.py "$PWD" --run r8_k15_n64     (plan A)

--run is a folder name under cloud_results/ebike_swap_sim/outputs or a path (default r8_k15_sp = plan B).
--other is the run that section [M] compares with (default: the other plan; 'none' skips [M]).
The layout of the run is read from the run's own layout.json, with candidates_csv pointed at the run's local
candidates.csv (the copy in paper_itsc/figs/map15/ may hold another run).

Sections (labels used as sources in the facts sheets):
  [A] geography of the 15 sites with make_figs.site_rows15 (name, class, DOT, NTA, restaurants <= 1 km,
      nearest entry point), the NTA lookup without the Roosevelt-Island mask, restaurants by area
  [B] land beyond 14 blocks of every site, as fig_map15 computes it and with only the island masked
  [C] per-site statistics of the best layout from the cache (p-weighted, design weights), riders by entry point,
      check against the run's site_stats.csv
  [D] swap timing by hour and area, battery level at the swap (distribution and mean), riders who never swap
  [E] charging: the power settings of the run; where a shared supply can bind, charging steps per 5-min slot
      against its cap in every in-sample evening of the best layout; where it cannot, per-site charging
      (steps, kWh, slots with a charger running, slots with every charger running) and the network's total draw
  [F] site-number order: charging energy by the site's position in the id-sorted site list (all cached cells) only
      where a shared supply binds (the rule hands the shared supply out in facility order); in every run the
      per-site charging of the small layouts D07 + D45 and V(k=5)
  [G] orders rebuilt without the route library (cross-checked against the cached schedules): pickups and
      deliveries by area, served share by delivery area for the best and the rule layouts
  [H] paired stratified differences (bilevel.stratified_ci, the estimator of RESULTS.md)
  [I] site overlap across the searched layouts (4 restarts + k-median + free)
  [J] end-of-evening terminal rule (code family '(9)') reported for the rule schedules (cells of the 24 evenings of the
      final table; the exact check's own 16-rider evenings counted apart)
  [K] instance hours and USD from the cost.jsonl files of the 48-rider run and both plans
  [L] location hints for the grid-cell sites: nearest named major streets of the cached OSM extract
  [M] the same layouts under both power models (cells cached in both runs, paired by evening)
  [N] cost components of every layout of the final table (in-sample) and of each regret
  [O] riders who end the evening below the end-of-evening reserve (no terminal arc at an open site, family '(9)') for
      every layout of the final table, in-sample and held-out, from the cached schedules; riders who never swap; level
      at the swap; regrets against the best when each such rider costs P (one unserved order) or 2 P, and the penalty
      per rider at which a mean regret changes sign or its 95 % interval stops excluding zero
  [P] the exact check (validate.json, the validate rows of records.jsonl, the 16-rider cache cells): the rule-based
      lower level against the exact integer program, nine cells, the three 5-site layouts ranked under both
Cache cells: cells_of keeps the cells of the 24 evenings of the final table (matched by the demand md5 of the 15-site
cells): the exact check builds its own 16-rider evenings with the same seeds 0-2, read only in [J] and [P].
Areas: S14 = south of the 14th St guide line of fig_map15, 14-59 = between the 14th and 59th St guide lines,
N59 = north of the 59th St guide line (rotated along-avenue coordinate of make_figs.rot).
"""
import argparse
import collections
import csv
import json
import math
import os
import sys

OUTS = ("cloud_results", "ebike_swap_sim", "outputs")
PLAN_A, PLAN_B, RUN48_NAME = "r8_k15_n64", "r8_k15_sp", "r8_k15"
ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
ap.add_argument("root", nargs="?", default=os.getcwd(), help="project root (OR Model-Battery Swap)")
ap.add_argument("--run", default=PLAN_B, help="run folder (name under cloud_results/ebike_swap_sim/outputs, or a path)")
ap.add_argument("--other", default=None, help="run compared in [M] (default: the other plan; 'none' skips [M])")
ap.add_argument("--run48", default=RUN48_NAME, help="48-rider run (cost rows of [K])")
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)


def run_dir(name):
    return os.path.abspath(name) if os.path.isdir(name) else os.path.join(ROOT, *OUTS, name)


RUN = run_dir(ARGS.run)
RUN48 = run_dir(ARGS.run48)
_other = ARGS.other if ARGS.other is not None else {PLAN_A: PLAN_B, PLAN_B: PLAN_A}.get(os.path.basename(RUN))
OTHER = None if _other in (None, "none") else run_dir(_other)
sys.path.insert(0, os.path.join(ROOT, "paper_itsc", "figs", "src"))
sys.path.insert(0, os.path.join(ROOT, "ebike_swap_sim"))
import numpy as np                                    # noqa: E402
from matplotlib.path import Path                      # noqa: E402
import make_figs as MF                                # noqa: E402
from ebike_swap_sim import data_nyc as dn             # noqa: E402
from ebike_swap_sim import sites_nyc as S             # noqa: E402
from ebike_swap_sim import config as CFG              # noqa: E402
from ebike_swap_sim.bilevel import stratified_ci      # noqa: E402

FS = json.load(open(os.path.join(RUN, "final_summary.json")))
SS = json.load(open(os.path.join(RUN, "search_summary.json")))
BEST = FS["best"]["layout_key"]
DEP = {"[44, 56]": "Queensboro Br", "[48, 22]": "Williamsburg Br", "[44, 19]": "Manhattan Br",
       "[42, 14]": "Brooklyn Br", "[29, 46]": "Lincoln Tun", "[36, 21]": "Holland Tun"}
X14, _ = MF.rot(40.7359, -73.9934)
X59, _ = MF.rot(40.7644, -73.9737)
print(f"run {RUN}")


def area(x):
    return "S14" if x < X14 else ("14-59" if x < X59 else "N59")


def pw(held=False):
    return {d["seed"]: d["p"] for d in S.scenario_design(12, held_out=held)}


def load_index(run):
    return [json.loads(line) for line in open(os.path.join(run, "cache", "index.jsonl"))]


def main_md5(index):
    """seed -> demand md5 of the 24 evenings of the final table: only these evenings have 15-site cells (the exact
    check reuses seeds 0-2 for its own 16-rider evenings, with at most 5 sites)"""
    out = {}
    for r in index:
        if r.get("n_open") == 15 and r.get("policy", "baseline") == "baseline":
            out.setdefault(r["seed"], r["demand_md5"])
    return out


INDEX = load_index(RUN)
MAIN_MD5 = main_md5(INDEX)
_MD5_OF = {id(INDEX): MAIN_MD5}


def cells_of(key, held=False, index=None):
    lo, hi = (100, 112) if held else (0, 12)
    idx = INDEX if index is None else index
    md5 = _MD5_OF.get(id(idx))
    if md5 is None:
        md5 = _MD5_OF[id(idx)] = main_md5(idx)
    out = {}
    for r in idx:
        if (r["layout_key"] == key and lo <= r["seed"] < hi and r.get("policy", "baseline") == "baseline"
                and r.get("demand_md5") == md5.get(r["seed"])):
            out.setdefault(r["seed"], r)
    return out


def schedule(r, run=None):
    return json.load(open(os.path.join(run or RUN, "cache", "schedules", os.path.basename(r["schedule_path"]))))


def short(key):
    return "|".join(p.replace(":SC:B3:C2", "").replace(":SC:B", "(B").replace(":C2", ")") for p in key.split("|"))


# ---------------------------------------------------------------- [A]
lay = MF.load_layout15(os.path.join(RUN, "layout.json"))
lay["candidates_csv"] = os.path.join(RUN, "candidates.csv")          # the run's own file (layout.json may name a server path)
cands = MF.load_candidates15(lay["candidates_csv"])
polys = MF.nta_polygons()
rx, ry = MF.restaurants_xy()
depots = [(nm, *MF.rot(la, lo)) for nm, la, lo in MF.ENTRY_POINTS]
rows = MF.site_rows15(lay, cands, rx, ry, polys, depots)
allp = [(c, n, Path(ll)) for c, n, _r, ll, _roos in polys]
_pl = os.path.join(ROOT, "paper_itsc", "figs", "map15", "layout.json")
if os.path.exists(_pl):
    _pj = json.load(open(_pl))
    _same = sorted((s["id"], s["B"], s["C"]) for s in _pj["sites"]) == sorted((s["id"], s["B"], s["C"]) for s in lay["sites"])
    print(f"  paper_itsc/figs/map15/layout.json holds run {_pj.get('run')!r}; same sites and sizes as this run: {_same}")
print(f"  layout.json: run {lay.get('run')!r}, n_bikes {lay.get('n_bikes')}, n_orders {lay.get('n_orders')}, "
      f"grid_kw {lay.get('grid_kw')}, site_kw {lay.get('site_kw')}, V {lay.get('V'):.1f}, served {lay.get('served_share'):.4f}")
print("[A] 15 sites south -> north (make_figs.site_rows15); restaurants in the box", len(rx))
for q in rows:
    r = cands[q["id"]]
    nta_all = [(c, n) for c, n, p in allp if p.contains_point((float(r["lon"]), float(r["lat"])))]
    print(f"  {q['no']:2d} {q['id']} {q['name']!r} class={q['klass']} DOT={q['dot']} map-NTA={q['nta_code'] or '?'} "
          f"{q['nta']} | NTA without mask={nta_all} | B:C {q['B']}:{q['C']} | rest<=1km {q['rest_1km']} "
          f"({q['rest_share'] * 100:.1f} %) | entry {q['entry']} {q['km_entry']:.2f} km | area {area(q['x'])}")
for nm, dx, dy in depots:
    near = min(((abs(q["x"] - dx) + abs(q["y"] - dy)), q["id"]) for q in rows)
    print(f"  entry {nm:17s} area {area(dx)}; nearest open site {near[1]} at {near[0]:.2f} km (grid)")
reg = dn.resolve_region("manhattan_s110")
cnt = {"box": collections.Counter(), "band": collections.Counter()}
with open(MF.DOHMH, encoding="utf-8") as fh:
    for rr in csv.DictReader(fh):
        if rr["r_boro"] != "Manhattan" or not rr["r_lat"] or not rr["r_lon"]:
            continue
        la, lo = float(rr["r_lat"]), float(rr["r_lon"])
        if MF.BOX[0] <= la <= MF.BOX[1] and MF.BOX[2] <= lo <= MF.BOX[3]:
            a = area(MF.rot(la, lo)[0])
            cnt["box"][a] += 1
            if reg.in_band(la, lo):
                cnt["band"][a] += 1
print("  restaurants by area:", {k: dict(v) for k, v in cnt.items()})
c18, c19 = cands["D18"], cands["D19"]
print(f"  Cooper Square pilot (D18) to PEC Site 38 (D19): straight line "
      f"{math.hypot(c18['x'] - c19['x'], c18['y'] - c19['y']):.2f} km, grid {abs(c18['x'] - c19['x']) + abs(c18['y'] - c19['y']):.2f} km")
print("  sites by area:", dict(collections.Counter(area(q["x"]) for q in rows)),
      "| DOT programme sites:", [q["id"] for q in rows if q["dot"]],
      "| classes:", dict(collections.Counter(q["klass"] for q in rows)))
for q in rows:                                         # every site within 1 km (grid) of an entry point
    near_e = [(nm, round(abs(q["x"] - dx) + abs(q["y"] - dy), 2)) for nm, dx, dy in depots if abs(q["x"] - dx) + abs(q["y"] - dy) <= 1.0]
    if near_e:
        print(f"  {q['id']} within 1 grid km of {near_e}")

# ---------------------------------------------------------------- [B]
x110, _ = MF.rot(40.7997, -73.9582)
xbat, _ = MF.rot(40.7003, -74.0170)
xl, yl = (xbat - 0.15, x110 + 0.05), (-3.35, 2.05)
gx = np.arange(xl[0] - 0.2, xl[1] + 0.2, 0.05)
gy = np.arange(yl[0] - 0.2, yl[1] + 0.2, 0.05)
GX, GY = np.meshgrid(gx, gy)
pts = np.c_[GX.ravel(), GY.ravel()]
land_map = np.zeros(GX.shape, dtype=bool)
land_fix = np.zeros(GX.shape, dtype=bool)
masked = []
for code, name, ring, ll, roos in polys:
    inside = Path(ring).contains_points(pts).reshape(GX.shape)
    island = roos and min(p[0] for p in ll) > -73.9625
    if roos:
        masked.append((code, name, "island" if island else "NOT the island"))
    if not roos:
        land_map |= inside
    if not island:
        land_fix |= inside
print("[B] polygons masked as Roosevelt Island by make_figs.nta_polygons:", masked)


def uncovered(ids, land):
    cov = np.zeros(GX.shape, dtype=bool)
    for i in ids:
        cov |= (np.abs(GX - cands[i]["x"]) + np.abs(GY - cands[i]["y"])) <= MF.ACCESS_KM
    return float(((~cov) & land).sum()) / float(land.sum()), cov


for name in ("best", "CSAV15", "kmedian15", "free", "dotfirst15", "CSCD15", "CSTC15", "V(k=1)", "prod_m1", "V(k=2)",
             "V(k=5)", "V(k=10)", "V(k=20)"):
    ids = [it[0] for it in FS["in_sample"][name]["layout"]]
    a, _ = uncovered(ids, land_map)
    b, _ = uncovered(ids, land_fix)
    print(f"  {name:10s} land beyond 14 blocks: map code {a * 100:5.2f} %   island-only mask {b * 100:5.2f} %")
for name in [n for n in FS["in_sample"] if n.startswith("restart:")]:
    a, _ = uncovered([it[0] for it in FS["in_sample"][name]["layout"]], land_map)
    print(f"  {name:20s} land beyond 14 blocks: map code {a * 100:5.2f} %")
nta_masks = [(n_, Path(r_).contains_points(pts).reshape(GX.shape)) for c_, n_, r_, ll_, roos_ in polys if not roos_]
for name in ("CSCD15", "CSTC15", "dotfirst15"):
    _, cv = uncovered([it[0] for it in FS["in_sample"][name]["layout"]], land_map)
    top = sorted(((int((m & ~cv).sum()), int(m.sum()), n_) for n_, m in nta_masks if (m & ~cv).any()), reverse=True)[:4]
    print(f"  {name}: land points beyond 14 blocks by NTA (uncovered / all)", [(n_, f"{u}/{t}") for u, t, n_ in top])
_, cov = uncovered([q["id"] for q in rows], land_map)
_unc = list(zip(GX[(~cov) & land_map], GY[(~cov) & land_map]))
if len(_unc) <= 12:
    for xx, yy in _unc:
        print("  best layout, uncovered land point (lat, lon):", [round(v, 5) for v in MF.unrot(xx, yy)])
else:
    top = sorted(((int((m & ~cov).sum()), int(m.sum()), n_) for n_, m in nta_masks if (m & ~cov).any()), reverse=True)[:5]
    print(f"  best layout: {len(_unc)} uncovered land points; by NTA (uncovered / all)", [(n_, f"{u}/{t}") for u, t, n_ in top],
          "; e.g. (lat, lon)", [[round(v, 5) for v in MF.unrot(xx, yy)] for xx, yy in _unc[:3]])
CLUSTERS = []                                         # uncovered land of the best layout, by NTA (for [L])
for n_, m in nta_masks:
    u = m & ~cov & land_map
    if u.any():
        lls = [MF.unrot(xx, yy) for xx, yy in zip(GX[u], GY[u])]
        mid = min(lls, key=lambda p_: (p_[0] - np.mean([q_[0] for q_ in lls])) ** 2 + (p_[1] - np.mean([q_[1] for q_ in lls])) ** 2)
        CLUSTERS.append((n_, int(u.sum()), mid))
        print(f"  best layout, uncovered land in {n_}: {int(u.sum())} points, lat {min(p_[0] for p_ in lls):.4f}-{max(p_[0] for p_ in lls):.4f}, "
              f"lon {min(p_[1] for p_ in lls):.4f} to {max(p_[1] for p_ in lls):.4f}")
dmin = np.full(GX.shape, np.inf)
for q in rows:
    dmin = np.minimum(dmin, np.abs(GX - q["x"]) + np.abs(GY - q["y"]))
dl = dmin[land_map]
print(f"  best layout: land points {int(land_map.sum())}, max grid km to the nearest site {dl.max():.2f}, "
      f"median {np.median(dl):.2f}, share within 1 km {np.mean(dl <= 1.0):.3f}")

# ---------------------------------------------------------------- [C]
P = pw()
cb = cells_of(BEST)
agg = collections.defaultdict(lambda: collections.defaultdict(float))
for seed, r in cb.items():
    for fid, st in r["per_site"].items():
        for k in ("swaps", "kwh_bought", "charge_steps", "charger_busy_share", "wait_min_mean", "stockout_slots"):
            agg[fid][k] += P[seed] * float(st[k])
        for d, n in st["rider_depots"].items():
            agg[fid]["from " + DEP[d]] += P[seed] * n
print(f"[C] best layout, in-sample cache ({len(cb)} evenings, design weights): per site")
for fid in sorted(agg):
    a = agg[fid]
    src = {k[5:]: round(v, 2) for k, v in sorted(a.items(), key=lambda kv: -kv[1]) if k.startswith("from ") and v > 0.004}
    print(f"  {fid} swaps {a['swaps']:.2f} kWh {a['kwh_bought']:.3f} steps {a['charge_steps']:.1f} busy {a['charger_busy_share']:.3f} "
          f"wait {a['wait_min_mean']:.1f} min stock-out {a['stockout_slots']:.1f}/48 riders by entry {src}")

tot_dep = collections.Counter()
for fid in agg:
    for k_, v_ in agg[fid].items():
        if k_.startswith("from "):
            tot_dep[k_[5:]] += v_
print("  riders who swapped (rider-site pairs) per evening, by entry point:", {k_: round(v_, 2) for k_, v_ in tot_dep.most_common()})
uni = FS["in_sample"]["best_locations"]["layout_key"]
d6 = S.scenario_design(6)
w6 = {seed: r_["p"] for seed, r_ in zip((0, 2, 4, 6, 8, 10), d6)}
sw6 = collections.Counter()
for r in INDEX:
    if r["layout_key"] == uni and r["seed"] in w6 and r.get("per_site"):
        w6_ = w6.pop(r["seed"])
        for fid, st in r["per_site"].items():
            sw6[fid] += w6_ * st["swaps"]
print("  best sites with 3 spares each, swaps per site on the 6 search evenings:", sorted((round(v_, 2), k_) for k_, v_ in sw6.items()))
sw12 = collections.Counter()
for seed, r in cells_of(uni).items():
    for fid, st in r["per_site"].items():
        sw12[fid] += P[seed] * st["swaps"]
print("  best sites with 3 spares each, swaps per site on the 12 in-sample evenings:", sorted((round(v_, 2), k_) for k_, v_ in sw12.items()))
_sst = {r_["id"]: r_ for r_ in csv.DictReader(open(os.path.join(RUN, "site_stats.csv"), encoding="utf-8"))}
_cmp = collections.defaultdict(float)
for fid, a in agg.items():
    s_ = _sst[fid.split(":")[0]]
    for k_cache, k_csv in (("swaps", "swaps_mean"), ("kwh_bought", "kwh_bought"), ("charger_busy_share", "charger_busy_share"),
                           ("wait_min_mean", "wait_min_mean"), ("stockout_slots", "stockout_slots")):
        _cmp[k_csv] = max(_cmp[k_csv], abs(a[k_cache] - float(s_[k_csv])))
print(f"  check against {os.path.basename(RUN)}/site_stats.csv ({len(_sst)} rows): max |cache - csv|",
      {k: round(v, 6) for k, v in _cmp.items()},
      "| totals: swaps", round(sum(float(s_["swaps_mean"]) for s_ in _sst.values()), 2),
      "kWh", round(sum(float(s_["kwh_bought"]) for s_ in _sst.values()), 3),
      "busy range", (round(min(float(s_["charger_busy_share"]) for s_ in _sst.values()), 3),
                     round(max(float(s_["charger_busy_share"]) for s_ in _sst.values()), 3)),
      "removal intervals that include zero", sorted(i for i, s_ in _sst.items() if float(s_["marginal_lo"]) <= 0.0))
_ar = collections.defaultdict(lambda: collections.defaultdict(float))
for q in rows:
    s_ = _sst[q["id"]]
    a_ = _ar[area(q["x"])]
    a_["sites"] += 1
    for k_ in ("swaps_mean", "kwh_bought", "marginal_usd"):
        a_[k_] += float(s_[k_])
print("  by area (sites, swaps, kWh, sum of removal values):",
      {k_: {kk: round(vv, 2) for kk, vv in v_.items()} for k_, v_ in sorted(_ar.items())})
_ent = sorted({min(((abs(q["x"] - dx) + abs(q["y"] - dy)), q["id"]) for q in rows)[1] for _nm, dx, dy in depots})
print(f"  the sites nearest to the six entry points {_ent}: swaps {sum(float(_sst[i]['swaps_mean']) for i in _ent):.2f}, "
      f"kWh {sum(float(_sst[i]['kwh_bought']) for i in _ent):.3f}, removal sum {sum(float(_sst[i]['marginal_usd']) for i in _ent):.1f}; "
      f"wait {min(float(_sst[i]['wait_min_mean']) for i in _ent):.1f}-{max(float(_sst[i]['wait_min_mean']) for i in _ent):.1f} min, "
      f"slots without a charged battery {min(float(_sst[i]['stockout_slots']) for i in _ent):.1f}-"
      f"{max(float(_sst[i]['stockout_slots']) for i in _ent):.1f}")

# ---------------------------------------------------------------- [D]
AREA = {q["id"]: area(q["x"]) for q in rows}
by_h = collections.defaultdict(float)
lev = collections.Counter()
never = first_h = 0.0
firsts = []
for seed, r in cb.items():
    s = schedule(r)
    for _b, arcs in s["x"].items():
        first = None
        for a in arcs:
            if a[0] == "swap":
                t = a[1][1]
                by_h[(t // 12, AREA[a[4].split(":")[0]])] += P[seed]
                lev[a[1][2]] += P[seed]
                first = t if first is None else first
        if first is None:
            never += P[seed]
        else:
            firsts.append((first, P[seed]))
            first_h += P[seed] * (first < 12)
tot = sum(by_h.values())
print(f"[D] swaps per evening {tot:.2f}")
for h in range(4):
    row = {a: round(by_h[(h, a)], 2) for a in ("S14", "14-59", "N59")}
    print(f"  {16 + h}:00-{17 + h}:00 {row} total {sum(row.values()):.2f}")
low = sum(v for q, v in lev.items() if q <= 6) / tot
print(f"  riders never swapping {never:.2f} of 64; first swap in the first hour {first_h:.2f}; mean first-swap minute "
      f"{5 * sum(t * p for t, p in firsts) / sum(p for _t, p in firsts):.0f}; swaps at <= 6 of 24 levels {low:.3f}; "
      f"mean level at the swap {sum(q * v for q, v in lev.items()) / tot:.2f} of 24; levels at the swap "
      f"{ {q: round(v, 2) for q, v in sorted(lev.items())} }")
print("  swaps per evening by area:", {a: round(sum(v for (h_, a_), v in by_h.items() if a_ == a), 2) for a in ("S14", "14-59", "N59")})

# ---------------------------------------------------------------- [E]
P_CH = float(CFG.energy_calibration("ebaas")["p_ch_kw"])           # kW of one charger (25 Wh per 5-min step at 90 %)


def _argv_value(run, flag):
    p = os.path.join(run, "cost.jsonl")
    if not os.path.exists(p):
        return None
    for line in open(p):
        argv = json.loads(line).get("argv") or []
        if flag in argv:
            return float(argv[argv.index(flag) + 1])
    return None


_fam = S.MANHATTAN15_PARAMS["facilities_spec"]
if lay.get("grid_kw") is not None:
    GRID_KW, GRID_SRC = float(lay["grid_kw"]), "layout.json grid_kw"
elif _argv_value(RUN, "--grid-kw") is not None:
    GRID_KW, GRID_SRC = _argv_value(RUN, "--grid-kw"), "cost.jsonl argv --grid-kw"
else:
    GRID_KW, GRID_SRC = float(_fam["grid_sites_kw"]), "family default (sites_nyc MANHATTAN15_PARAMS grid_sites_kw; no --grid-kw)"
SITE_KW = float(lay["site_kw"]) if lay.get("site_kw") is not None else float(_fam["P_kw"])
GROUP_STEPS = int(math.floor(GRID_KW / P_CH + 1e-9))               # chargers the shared supply runs at once
SITE_STEPS = int(math.floor(SITE_KW / P_CH + 1e-9))                # chargers one site's connection runs at once
CH = {f"{s_['id']}:SC": int(s_["C"]) for s_ in lay["sites"]}
n_ch = sum(CH.values())
CAN_BIND = GROUP_STEPS < n_ch
print(f"[E] power: shared supply {GRID_KW:g} kW ({GRID_SRC}) = {GROUP_STEPS} chargers at once; each site {SITE_KW:g} kW = "
      f"{SITE_STEPS} chargers (one charger {P_CH:.4f} kW); the best layout has {n_ch} chargers, at most {max(CH.values())} per site; "
      f"shared supply can bind: {CAN_BIND}; a site connection can bind: {SITE_STEPS < max(CH.values())}")
full_slots = []
site_e = collections.defaultdict(lambda: collections.defaultdict(float))
tot_kw = []
if CAN_BIND:
    print(f"  charging steps per 5-min slot ({GROUP_STEPS} steps = {GRID_KW:g} kW) in the best layout's in-sample evenings")
for seed, r in sorted(cb.items()):
    per_t = collections.Counter()
    per_jt = collections.Counter()
    for j, q, t, val in schedule(r)["c"]:
        per_t[int(t)] += int(val)
        per_jt[(j, int(t))] += int(val)
    full = sum(1 for t in range(48) if per_t.get(t, 0) >= GROUP_STEPS)
    full_slots.append(full)
    if CAN_BIND:
        print(f"  seed {seed}: max {max(per_t.values())} steps in a slot, slots at {GROUP_STEPS} steps {full}/48, "
              f"kWh {sum(per_t.values()) * 0.025 / 0.9:.3f}")
    else:
        print(f"  seed {seed}: all sites together: max {max(per_t.values())} chargers running in a slot "
              f"({max(per_t.values()) * P_CH:.2f} kW), mean {sum(per_t.values()) / 48:.1f} ({sum(per_t.values()) / 48 * P_CH:.2f} kW), "
              f"kWh {sum(per_t.values()) * 0.025 / 0.9:.3f}")
    tot_kw.append((P[seed], max(per_t.values()) * P_CH, sum(per_t.values()) / 48 * P_CH))
    for j in CH:
        ts = [per_jt.get((j, t), 0) for t in range(48)]
        e = site_e[j]
        e["steps"] += P[seed] * sum(ts)
        e["any"] += P[seed] * sum(1 for v in ts if v > 0)
        e["all"] += P[seed] * sum(1 for v in ts if v >= CH[j])
        e["max"] = max(e["max"], max(ts))
        e["first"] += P[seed] * next((t for t, v in enumerate(ts) if v > 0), 48)
        e["last"] += P[seed] * next((47 - t for t, v in enumerate(reversed(ts)) if v > 0), -1)
SHARED_BINDS = CAN_BIND and sum(full_slots) > 0
_sw = [agg[j]["swaps"] for j in sorted(agg)]
_kw = [agg[j]["kwh_bought"] for j in sorted(agg)]
print(f"  best layout: sites with any charging {sum(1 for v in _kw if v > 0)} of {len(_kw)}, with more than 0.1 kWh "
      f"{sum(1 for v in _kw if v > 0.1)}; correlation of kWh with swaps across the sites {np.corrcoef(_sw, _kw)[0, 1]:.3f}; "
      f"kWh of the first three sites by id {sum(_kw[:3]):.3f} of {sum(_kw):.3f}")
if not CAN_BIND:
    print(f"  shared supply cannot bind ({GROUP_STEPS} > {n_ch} chargers); per site (p-weighted over {len(cb)} evenings; "
          f"slots of 5 min, 48 per evening):")
    for j in sorted(site_e):
        e = site_e[j]
        print(f"    {j} chargers {CH[j]}: steps {e['steps']:.1f} = kWh {e['steps'] * 0.025 / 0.9:.3f}; slots with a charger running "
              f"{e['any']:.1f}, with all {CH[j]} running {e['all']:.1f}; most chargers in one slot {int(e['max'])}; "
              f"charger-slot use {e['steps'] / (CH[j] * 48):.2f}; first / last charging slot {e['first']:.1f} / {e['last']:.1f}")
    print(f"  sites that charge at all: {sum(1 for e in site_e.values() if e['steps'] > 0)} of {len(site_e)}; network draw (p-weighted): "
          f"peak {sum(p * a for p, a, _m in tot_kw):.2f} kW (max over evenings {max(a for _p, a, _m in tot_kw):.2f}), "
          f"evening mean {sum(p * m for p, _a, m in tot_kw):.2f} kW; total kWh "
          f"{sum(e['steps'] for e in site_e.values()) * 0.025 / 0.9:.3f}")

# ---------------------------------------------------------------- [F]
if SHARED_BINDS:
    print("[F] charging energy by position in the id-sorted site list, all cached cells with per-site rows")
    by_k = collections.defaultdict(list)
    for r in INDEX:
        if r.get("per_site"):
            by_k[r["n_open"]].append(r)
    for k in (5, 10, 15, 20):
        kw = collections.defaultdict(list)
        sh = []
        for r in by_k[k]:
            ids = sorted(r["per_site"])
            v = [r["per_site"][i]["kwh_bought"] for i in ids]
            for i, x in enumerate(v):
                kw[i + 1].append(x)
            if sum(v) > 0:
                sh.append(sum(v[:3]) / sum(v))
        print(f"  k={k}: {len(by_k[k])} cells, share of kWh at the first 3 ids {np.mean(sh):.3f} (min {min(sh):.3f}); "
              f"mean kWh by position {[round(float(np.mean(kw[i])), 2) for i in sorted(kw)]}")
else:
    print(f"[F] site-number order: not applicable in this run: no shared supply binds (cap {GROUP_STEPS} chargers at once, "
          f"slots at the cap {sum(full_slots)}), so the rule's facility order does not decide which site charges; "
          f"per-site charging of the small layouts:")
for key in ("D07:SC:B3:C2|D45:SC:B3:C2", FS["in_sample"]["V(k=5)"]["layout_key"]):
    a2 = collections.defaultdict(lambda: collections.defaultdict(float))
    for seed, r in cells_of(key).items():
        for fid, st in r["per_site"].items():
            a2[fid]["swaps"] += P[seed] * st["swaps"]
            a2[fid]["kwh"] += P[seed] * st["kwh_bought"]
            for d, n in st["rider_depots"].items():
                a2[fid][DEP[d]] += P[seed] * n
    print("  layout", key.replace(":SC:B3:C2", ""))
    for fid in sorted(a2):
        top = max(((v, d) for d, v in a2[fid].items() if d not in ("swaps", "kwh")))
        print(f"    {fid} swaps {a2[fid]['swaps']:.2f} kWh {a2[fid]['kwh']:.2f} main riders {top[1]} {top[0]:.2f}")

# ---------------------------------------------------------------- [G]


class _Captured(Exception):
    pass


CAP = {}


def _routes(net, nodes, phys):
    f = sys._getframe(1)
    CAP["orders"], CAP["box"] = list(f.f_locals["orders"]), f.f_locals["box"]
    raise _Captured()


dn.build_route_library = _routes                     # orders only: the route library is never built
cand_objs = [S.Candidate(id=r["id"], label=r["label"], source="dot", lat=float(r["lat"]), lon=float(r["lon"]),
                         node=(int(r["node_x"]), int(r["node_y"])), hub_capable=bool(int(r["hub_capable"] or 0)),
                         lattice_id=r["lattice_id"] or None, dot_type=r["dot_type"] or None, cls=r["cls"])
             for r in csv.DictReader(open(os.path.join(RUN, "candidates.csv"), encoding="utf-8"))]
deps = S.family_depots("manhattan15", cand_objs)
ORD = {}
N_BIKES = int(lay.get("n_bikes") or 64)
for sc in S.scenario_design(12):
    try:
        S.make_base_instance(sc["seed"], cand_objs, family="manhattan15", depots=deps, n_bikes=N_BIKES, **sc["overrides"])
    except _Captured:
        pass
    ORD[sc["seed"]] = (CAP["orders"], CAP["box"], sc["p"])


def node_area(box, v):
    return area(MF.rot(*box.node_latlon(v))[0])


ok = n = 0
pick = collections.Counter()
dele = collections.Counter()
for seed, (orders, box, p) in ORD.items():
    byid = {o.id: o for o in orders}
    for _b, arcs in schedule(cb[seed])["x"].items():
        for a in arcs:
            if a[0] == "deliver":
                n += 1
                ok += int(tuple(byid[a[3]].d) == tuple(a[2][0]))
    for o in orders:
        pick[node_area(box, o.o)] += p
        dele[node_area(box, o.d)] += p
print(f"[G] rebuilt orders: {ok}/{n} served deliveries of the cached best schedules match the rebuilt customer nodes")
T = sum(dele.values())
print("  expected orders per evening by pickup area", {k: round(v, 1) for k, v in pick.items()},
      {k: round(v / T, 3) for k, v in pick.items()})
print("  expected orders per evening by delivery area", {k: round(v, 1) for k, v in dele.items()},
      {k: round(v / T, 3) for k, v in dele.items()})
for name in ("best", "CSAV15", "kmedian15", "dotfirst15", "CSCD15", "CSTC15", "free", "best_locations"):
    cc = cells_of(FS["in_sample"][name]["layout_key"])
    ds = collections.Counter()
    for seed, (orders, box, p) in ORD.items():
        served = {a[3] for _b, arcs in schedule(cc[seed])["x"].items() for a in arcs if a[0] == "deliver"}
        for o in orders:
            if o.id in served:
                ds[node_area(box, o.d)] += p
    print(f"  {name:10s} served share by delivery area", {k: round(ds[k] / dele[k], 3) for k in ("S14", "14-59", "N59")})
# orders whose customer or restaurant lies beyond 14 blocks (grid) of every open site of a layout
for name in ("best", "CSAV15", "kmedian15", "CSCD15", "CSTC15", "dotfirst15"):
    lay_ids = [it[0] for it in FS["in_sample"][name]["layout"]]
    cc = cells_of(FS["in_sample"][name]["layout_key"])
    far_d = far_o = far_d_served = 0.0
    for seed, (orders, box, p) in ORD.items():
        served = {a[3] for _b, arcs in schedule(cc[seed])["x"].items() for a in arcs if a[0] == "deliver"}
        for o in orders:
            xd, yd = MF.rot(*box.node_latlon(o.d))
            xo, yo = MF.rot(*box.node_latlon(o.o))
            if min(abs(xd - cands[i]["x"]) + abs(yd - cands[i]["y"]) for i in lay_ids) > MF.ACCESS_KM:
                far_d += p
                far_d_served += p * (o.id in served)
            if min(abs(xo - cands[i]["x"]) + abs(yo - cands[i]["y"]) for i in lay_ids) > MF.ACCESS_KM:
                far_o += p
    print(f"  {name:10s} orders per evening with the customer beyond 14 blocks of every open site {far_d:.1f} "
          f"(served {far_d_served / far_d if far_d else float('nan'):.3f}); with the restaurant beyond {far_o:.1f}")

# ---------------------------------------------------------------- [H]
print("[H] paired stratified differences A - B (USD/day, half-width of the 95 % CI)")
RESTARTS = [n_ for n_ in FS["in_sample"] if n_.startswith("restart:")]
BEST_RESTART = "restart:" + SS["best_restart"]
EXTRA = ([("best", "best_locations"), ("V(k=20)", "best"), ("free", "CSAV15"), ("kmedian15", "free"),
          ("dotfirst15", "CSCD15"), ("CSTC15", "dotfirst15")]
         + [(n_, "best_locations") for n_ in RESTARTS if n_ != BEST_RESTART] + [(n_, "best") for n_ in RESTARTS if n_ != BEST_RESTART])
for kind, held in (("in_sample", False), ("held_out", True)):
    d = S.scenario_design(12, held_out=held)
    st, p = [r["stratum"] for r in d], [r["p"] for r in d]

    def tot_(nm):
        rr = FS[kind][nm]
        return [rr["C_setup"] + o for o in rr["opex"]]

    for a_, b_ in (("CSAV15", "best"), ("restart:CSCD_best2", "best_locations"), ("restart:CSCD_best2", "best"),
                   ("V(k=2)", "V(k=1)"), ("V(k=5)", "V(k=2)"), ("V(k=10)", "V(k=5)"), ("V(k=15)", "V(k=10)"),
                   ("V(k=20)", "V(k=15)"), ("prod_m1", "V(k=1)"), ("kmedian15", "CSAV15"), ("CSCD15", "dotfirst15"),
                   ("CSTC15", "CSCD15")):
        ci = stratified_ci([x - y for x, y in zip(tot_(a_), tot_(b_))], st, p)
        print(f"  {kind:9s} {a_:20s} - {b_:15s} {ci['mean']:9.1f} +- {ci['half']:6.1f}")
    print(f"  {kind:9s} additional pairs (best restart = {BEST_RESTART}):")
    for a_, b_ in EXTRA:
        ci = stratified_ci([x - y for x, y in zip(tot_(a_), tot_(b_))], st, p)
        print(f"  {kind:9s} {a_:20s} - {b_:15s} {ci['mean']:9.1f} +- {ci['half']:6.1f}")
    n_chk = n_bad = 0
    for nm in FS[kind]:
        if nm == "best":
            continue
        ci = stratified_ci([x - y for x, y in zip(tot_(nm), tot_("best"))], st, p)
        rg = FS["regret_in" if not held else "regret_out"].get(nm) or {}
        rci = rg.get("regret_ci") or {}
        if rg.get("regret") is None:
            continue
        n_chk += 1
        if abs(float(rg["regret"]) - ci["mean"]) > 0.05 or abs(float(rci.get("half") or 0.0) - float(ci["half"] or 0.0)) > 0.05:
            n_bad += 1
            print(f"  {kind:9s} MISMATCH {nm}: recomputed {ci['mean']:.2f} +- {ci['half']:.2f}, final_summary {rg['regret']:.2f} +- {rci.get('half')}")
    print(f"  {kind:9s} {n_chk} regrets against the best recomputed; {n_bad} differ from final_summary.json "
          f"regret_{'out' if held else 'in'} ('regret' and 'regret_ci.half', tolerance 0.05 USD; note: 'regret_ci.mean' "
          f"leaves out the set-up difference, so it differs for V(k), prod_m1/m2 and free, the half-width does not)")

# ---------------------------------------------------------------- [I]
names = ["restart:empty", "restart:CSCD_best2", "restart:m2_incumbent", "restart:CSAV_best2", "kmedian15", "free"]
names = [BEST_RESTART] + [n_ for n_ in names if n_ != BEST_RESTART]
sets = {nm: {it[0] for it in FS["in_sample"][nm]["layout"]} for nm in names}
cnt6 = collections.Counter(s for nm in names for s in sets[nm])
print("[I] best sites: in how many of the 6 searched layouts (4 restarts + k-median + free)",
      sorted((s, cnt6[s]) for s in sets[BEST_RESTART]))
for nm in names[1:]:
    print(f"  {nm}: {len(sets[nm] & sets[BEST_RESTART])} sites shared with the best")
print(f"  best restart {BEST_RESTART}; sites of the best in all six: {sorted(s for s in sets[BEST_RESTART] if cnt6[s] == 6)}, "
      f"in five: {sorted(s for s in sets[BEST_RESTART] if cnt6[s] == 5)}, only in the best: {sorted(s for s in sets[BEST_RESTART] if cnt6[s] == 1)}")
for nm in names:
    print(f"  {nm:22s} sites by area", dict(collections.Counter(area(cands[s]["x"]) for s in sets[nm])))
for nm in names[1:]:
    print(f"  {nm:22s} sites not in the best: {sorted(sets[nm] - sets[BEST_RESTART])}; best sites it lacks: "
          f"{sorted(sets[BEST_RESTART] - sets[nm])}")
print("  nearest open site (grid km) to each entry point, by layout:")
for nm in ["best"] + names + ["CSAV15", "CSCD15", "dotfirst15", "CSTC15"]:
    ids = [it[0] for it in FS["in_sample"][nm]["layout"]]
    near = [min((abs(cands[i]["x"] - dx) + abs(cands[i]["y"] - dy), i) for i in ids) for _en, dx, dy in depots]
    print(f"    {nm:22s} " + "; ".join(f"{en.split()[0]} {i} {d:.2f}" for (en, _dx, _dy), (d, i) in zip(depots, near))
          + f" | farthest {max(d for d, _i in near):.2f}")

# ---------------------------------------------------------------- [J]
fam = [(seed, (r.get("check_families") or {}).get("(9)", 0)) for seed, r in sorted(cb.items())]
allc = [r for r in INDEX if "check_families" in r and r.get("demand_md5") == MAIN_MD5.get(r["seed"])]
valc = [r for r in INDEX if "check_families" in r and r.get("demand_md5") != MAIN_MD5.get(r["seed"])]
print("[J] best layout, riders per evening reported under '(9)' (no end-of-evening terminal at an open site):", fam,
      "p-weighted mean", round(sum(P[s] * v for s, v in fam), 2))
print(f"  all checked cells of the 24 evenings: {sum(1 for r in allc if (r['check_families'] or {}).get('(9)'))} of {len(allc)} "
      f"with '(9)'; ok_modulo_report_only {collections.Counter(r.get('ok_modulo_report_only') for r in allc)}; rule cells "
      f"of the exact check's own evenings: {sum(1 for r in valc if (r['check_families'] or {}).get('(9)'))} of {len(valc)} "
      f"with '(9)'")
fam_out = [(seed, (r.get("check_families") or {}).get("(9)", 0)) for seed, r in sorted(cells_of(BEST, True).items())]
print(f"  best layout: in-sample evenings with at least one '(9)' rider {sum(1 for _s, v in fam if v)} of {len(fam)}; held-out "
      f"{fam_out}, {sum(1 for _s, v in fam_out if v)} of {len(fam_out)} with one, p-weighted mean "
      f"{sum(pw(True)[s] * v for s, v in fam_out):.2f}")
for nm in FS["in_sample"]:
    cc = cells_of(FS["in_sample"][nm]["layout_key"])
    if len(cc) == 12:
        print(f"    {nm:22s} '(9)' riders per evening (p-weighted, in-sample) "
              f"{sum(P[s] * (r.get('check_families') or {}).get('(9)', 0) for s, r in cc.items()):.2f}")
# where these riders are at 20:00: a rider without a 'term' arc in the cached schedule is a '(9)' rider (checked per evening)
Q_RES = int(CFG.energy_calibration("ebaas")["q_res"])
SITE_NODE = {(int(cands[s_["id"]]["node_x"]), int(cands[s_["id"]]["node_y"])): s_["id"] for s_ in lay["sites"]}
for tag, cc, ww in (("in-sample", cb, P), ("held-out", cells_of(BEST, True), pw(True))):
    n_r = n_site = n_match = 0
    lev_, site_, since_ = collections.Counter(), collections.Counter(), []
    for seed, r in sorted(cc.items()):
        s = schedule(r)
        no_term = [arcs for arcs in s["x"].values() if not any(a[0] == "term" for a in arcs)]
        n_match += int(len(no_term) == (r.get("check_families") or {}).get("(9)", 0))
        for arcs in no_term:
            node, t_end, q_end = tuple(arcs[-1][2][0]), arcs[-1][2][1], arcs[-1][2][2]
            n_r += 1
            lev_[q_end] += 1
            n_site += int(node in SITE_NODE)
            site_[SITE_NODE.get(node, "not at a site")] += ww[seed]
            t_arr = t_end
            for a in reversed(arcs):
                if a[0] != "wait":
                    break
                t_arr = a[1][1]
            since_.append((t_arr, ww[seed]))
    print(f"  {tag}: riders without a terminal arc {n_r} (rider-evenings, {len(cc)} evenings; count = '(9)' in {n_match} of {len(cc)}); "
          f"on an open site's node at 20:00: {n_site}; battery level at 20:00 {dict(sorted(lev_.items()))} of 24 (reserve {Q_RES}); "
          f"waiting there since slot {sum(t * p for t, p in since_) / max(sum(p for _t, p in since_), 1e-9):.1f} on average "
          f"(min {min((t for t, _p in since_), default=None)}, max {max((t for t, _p in since_), default=None)}); per evening by site "
          f"{ {k_: round(v_, 2) for k_, v_ in site_.most_common()} }")

# ---------------------------------------------------------------- [K]
print("[K] instance hours and USD (cost.jsonl 'end' rows; a 'start' row without an 'end' row = still running)")
T_h = T_u = 0.0
per_run = {}
for run in [RUN48] + [run_dir(x) for x in (PLAN_A, PLAN_B)]:
    p_ = os.path.join(run, "cost.jsonl")
    if not os.path.exists(p_):
        continue
    started, ended = {}, set()
    h_ = u_ = 0.0
    for line in open(p_):
        e = json.loads(line)
        if e["event"] == "start":
            started[(e["stage"], e["start"])] = e
        if e["event"] == "end":
            ended.add((e["stage"], e["start"]))
            h_ += e["wall_h"]
            u_ += e["usd"]
            print(f"  {os.path.basename(run):11s} {e['stage']:9s} {e['wall_h']:.4f} h {e['usd']:.4f} USD {e['status']}")
    for key_, e in started.items():
        if key_ not in ended:
            print(f"  {os.path.basename(run):11s} {e['stage']:9s} started {e['start']} on {e['instance']}: no 'end' row "
                  f"(running when downloaded; not in the totals)")
    per_run[os.path.basename(run)] = (h_, u_)
    T_h += h_
    T_u += u_
for nm_, (h_, u_) in per_run.items():
    print(f"  {nm_:11s} total {h_:.3f} h {u_:.3f} USD")
if RUN48_NAME in per_run and PLAN_A in per_run:
    print(f"  total {per_run[RUN48_NAME][0] + per_run[PLAN_A][0]:.3f} h "
          f"{per_run[RUN48_NAME][1] + per_run[PLAN_A][1]:.3f} USD (48-rider run + plan A, the plan A sheet's total); "
          f"all folders {T_h:.3f} h {T_u:.3f} USD")
print(f"  C(59,15) = {math.comb(59, 15):,}")
ss_ = SS
print(f"  search of this run: {ss_['n_cells']} lower-level evaluations, {ss_['proxy_calls']} proxy scores, wall {ss_['wall_s'] / 3600:.3f} h, "
      f"cell mean {ss_['cell_s_mean']:.2f} s, max {ss_['cell_s_max']:.2f} s, worker RSS max {ss_['worker_rss_gb_max']:.2f} GB; "
      f"final stage {FS.get('n_cells')} evaluations")

# ---------------------------------------------------------------- [L]
print("[L] nearest named major streets (data/raw/osm_major_roads_manhattan.json, metres) of the grid-cell sites")
osm = json.load(open(MF.OSM, encoding="utf-8"))


def _seg(p0, a, b):
    c = math.cos(math.radians(p0[0]))
    ax, ay = (a[1] - p0[1]) * 111320 * c, (a[0] - p0[0]) * 110540
    bx, by = (b[1] - p0[1]) * 111320 * c, (b[0] - p0[0]) * 110540
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L2))
    return math.hypot(ax + t * dx, ay + t * dy)


for q in rows:
    if q["klass"] != "lattice":
        continue
    r = cands[q["id"]]
    p0 = (float(r["lat"]), float(r["lon"]))
    best_d = {}
    for w in osm["ways"]:
        nm = w.get("name") or ""
        if nm and len(w["pts"]) > 1:
            d = min(_seg(p0, w["pts"][i], w["pts"][i + 1]) for i in range(len(w["pts"]) - 1))
            best_d[nm] = min(d, best_d.get(nm, 1e9))
    print(f"  {q['id']}: {[(n, round(d)) for n, d in sorted(best_d.items(), key=lambda kv: kv[1])[:4]]}")

for xx, yy in zip(GX[(~cov) & land_map][:2], GY[(~cov) & land_map][:2]):
    p0 = MF.unrot(xx, yy)
    best_d = {}
    for w in osm["ways"]:
        nm = w.get("name") or ""
        if nm and len(w["pts"]) > 1:
            d = min(_seg(p0, w["pts"][i], w["pts"][i + 1]) for i in range(len(w["pts"]) - 1))
            best_d[nm] = min(d, best_d.get(nm, 1e9))
    print(f"  uncovered point {[round(v, 5) for v in p0]}: {[(n, round(d)) for n, d in sorted(best_d.items(), key=lambda kv: kv[1])[:4]]}")
for n_, cnt_, p0 in CLUSTERS:                          # one middle point of each uncovered cluster of the best layout
    best_d = {}
    for w in osm["ways"]:
        nm = w.get("name") or ""
        if nm and len(w["pts"]) > 1:
            d = min(_seg(p0, w["pts"][i], w["pts"][i + 1]) for i in range(len(w["pts"]) - 1))
            best_d[nm] = min(d, best_d.get(nm, 1e9))
    print(f"  uncovered cluster {n_} ({cnt_} points), middle point {[round(v, 5) for v in p0]}: "
          f"{[(n, round(d)) for n, d in sorted(best_d.items(), key=lambda kv: kv[1])[:4]]}")

# ---------------------------------------------------------------- [M]
if OTHER is None or not os.path.exists(os.path.join(OTHER, "cache", "index.jsonl")):
    print("[M] skipped (no other run)")
else:
    IDX2 = load_index(OTHER)
    d12 = S.scenario_design(12)
    st12, p12 = [r_["stratum"] for r_ in d12], [r_["p"] for r_ in d12]
    keys2 = {r_["layout_key"] for r_ in IDX2}
    names_here = collections.defaultdict(list)
    for nm, r_ in FS["in_sample"].items():
        names_here[r_["layout_key"]].append(nm)
    print(f"[M] the same layouts under both power models: this run {os.path.basename(RUN)} minus {os.path.basename(OTHER)}, "
          f"in-sample, paired by evening (layouts with all 12 evenings cached in both runs)")
    for key in sorted({r_["layout_key"] for r_ in INDEX} & keys2, key=lambda k_: (-len(k_.split("|")), k_)):
        c1, c2 = cells_of(key), cells_of(key, index=IDX2)
        if len(c1) < 12 or len(c2) < 12 or any(not c1[s_].get("feasible", True) or c1[s_].get("total") is None or
                                                 c2[s_].get("total") is None for s_ in range(12)):
            continue
        v1, v2 = [c1[s_]["total"] for s_ in range(12)], [c2[s_]["total"] for s_ in range(12)]
        ci = stratified_ci([a_ - b_ for a_, b_ in zip(v1, v2)], st12, p12)
        sv1 = sum(P[s_] * c1[s_]["metrics"]["served_share"] for s_ in range(12))
        sv2 = sum(P[s_] * c2[s_]["metrics"]["served_share"] for s_ in range(12))
        kw1 = sum(P[s_] * c1[s_]["metrics"]["kwh_purchased"] for s_ in range(12))
        kw2 = sum(P[s_] * c2[s_]["metrics"]["kwh_purchased"] for s_ in range(12))
        sw1 = sum(P[s_] * c1[s_]["metrics"]["n_swaps"] for s_ in range(12))
        sw2 = sum(P[s_] * c2[s_]["metrics"]["n_swaps"] for s_ in range(12))
        m1 = sum(P[s_] * v1[s_] for s_ in range(12))
        m2 = sum(P[s_] * v2[s_] for s_ in range(12))
        print(f"  {len(key.split('|')):2d} sites {names_here.get(key) or '-'} {short(key)[:70]}: V {m1:.1f} vs "
              f"{m2:.1f}, diff {ci['mean']:.1f} +- {ci['half']:.1f}; served {sv1:.3f} vs {sv2:.3f}; swaps {sw1:.1f} vs {sw2:.1f}; "
              f"kWh {kw1:.2f} vs {kw2:.2f}")
    # per site, by position in the id-sorted list (the rule's charging order): the coverage rule (the dry-run layout) and V(k=5)
    for nm in ("CSCD15", "V(k=5)"):
        key = FS["in_sample"][nm]["layout_key"]
        c1, c2 = cells_of(key), cells_of(key, index=IDX2)
        if len(c1) < 12 or len(c2) < 12:
            continue
        parts = []
        for pos, fid in enumerate(sorted(c1[0]["per_site"]), 1):
            s1 = sum(P[s_] * c1[s_]["per_site"][fid]["swaps"] for s_ in range(12))
            s2 = sum(P[s_] * c2[s_]["per_site"][fid]["swaps"] for s_ in range(12))
            k1 = sum(P[s_] * c1[s_]["per_site"][fid]["kwh_bought"] for s_ in range(12))
            k2 = sum(P[s_] * c2[s_]["per_site"][fid]["kwh_bought"] for s_ in range(12))
            parts.append(f"{pos}:{fid.split(':')[0]} {s1:.2f}/{k1:.2f} vs {s2:.2f}/{k2:.2f}")
        print(f"  {nm} per site (position in the id order: swaps/kWh this run vs other): " + "; ".join(parts))
    # 15-site layouts priced on the six search evenings in both runs: does the power model change their order?
    w6b = {seed: r_["p"] for seed, r_ in zip((0, 2, 4, 6, 8, 10), S.scenario_design(6))}

    def v6(index):
        out = collections.defaultdict(dict)
        for r_ in index:
            if r_["n_open"] == 15 and r_["seed"] in w6b and r_.get("total") is not None:
                out[r_["layout_key"]].setdefault(r_["seed"], r_["total"])
        return {k_: sum(w6b[s_] * v_ for s_, v_ in d_.items()) for k_, d_ in out.items() if len(d_) == 6}
    a6, b6 = v6(INDEX), v6(IDX2)
    both = sorted(set(a6) & set(b6))
    if len(both) >= 3:
        ra = {k_: i for i, k_ in enumerate(sorted(both, key=lambda k_: a6[k_]))}
        rb = {k_: i for i, k_ in enumerate(sorted(both, key=lambda k_: b6[k_]))}
        nn = len(both)
        rho = 1 - 6 * sum((ra[k_] - rb[k_]) ** 2 for k_ in both) / (nn * (nn * nn - 1))
        dif = [a6[k_] - b6[k_] for k_ in both]
        print(f"  15-site layouts priced on all 6 search evenings in both runs: {nn}; this minus other: mean {np.mean(dif):.1f}, "
              f"min {min(dif):.1f}, max {max(dif):.1f}; Spearman rank correlation of the two orders {rho:.3f}")
        print(f"    best of them in this run {short(min(both, key=lambda k_: a6[k_]))} ({min(a6[k_] for k_ in both):.1f}); "
              f"in the other {short(min(both, key=lambda k_: b6[k_]))} ({min(b6[k_] for k_ in both):.1f})")
    print(f"  15-site layouts priced on the 6 search evenings: this run {len(a6)}, other {len(b6)}; "
          f"this run's best locations {'in' if FS['in_sample']['best_locations']['layout_key'] in b6 else 'not in'} the other's cache; "
          f"the other's best locations {'in' if json.load(open(os.path.join(OTHER, 'final_summary.json')))['in_sample']['best_locations']['layout_key'] in a6 else 'not in'} this run's cache")

# ---------------------------------------------------------------- [N]
print("[N] cost components, in-sample, USD per evening (orders = unserved / 60)")
cols = ("C_setup", "C_elec", "C_travel", "unserved", "response", "lateness", "total")
for nm, r_ in FS["in_sample"].items():
    c_ = r_["components"]
    print(f"  {nm:22s} " + " ".join(f"{k} {c_[k]:9.1f}" for k in cols) + f" | unserved orders {c_['unserved'] / 60:.1f} | "
          f"order cost share {(c_['unserved'] + c_['response'] + c_['lateness']) / c_['total']:.3f} | served {r_['served_share']:.3f} "
          f"| swaps {r_['n_swaps_mean']:.1f} | kWh {r_['kwh_mean']:.2f}")
cb_ = FS["in_sample"]["best"]["components"]
for nm, r_ in FS["in_sample"].items():
    if nm == "best" or r_["n_open"] != 15:
        continue
    c_ = r_["components"]
    dd = {k: c_[k] - cb_[k] for k in cols}
    print(f"  regret {nm:22s} {dd['total']:8.1f} = unserved {dd['unserved']:8.1f} + response {dd['response']:8.1f} + lateness "
          f"{dd['lateness']:7.1f} + travel {dd['C_travel']:6.1f} + electricity {dd['C_elec']:5.1f} + set-up {dd['C_setup']:5.1f}")

# ---------------------------------------------------------------- [O]
# Riders who end the evening below the end-of-evening reserve: no terminal arc at an open site (code family '(9)'),
# counted from the cached schedules and checked against each cell's check_families; riders who never swap; battery
# level at the swap. Then the regret against the best when each such rider is charged pen USD per evening (P = the
# price of one unserved order, and 2 P), paired by evening with bilevel.stratified_ci (the estimator of RESULTS.md).
# The penalty is added to the same schedules (the riders do not act differently): an ex-post charge, not a re-run.
def end_state(r_):
    """one cell: '(9)' riders, where they stand at 20:00 and their level, never-swapping riders, levels at the swaps"""
    s_ = schedule(r_)
    ids_ = {it[0] for it in r_["layout"]}
    node_ = {(int(cands[i]["node_x"]), int(cands[i]["node_y"])) for i in ids_}
    o_ = {"n9": 0, "no_term": 0, "bad_term": 0, "at_site": 0, "lev": collections.Counter(), "never": 0, "sw_n": 0,
          "sw_q": 0, "sw_low": 0, "n_bikes": len(s_["x"]), "fam9": (r_.get("check_families") or {}).get("(9)", 0)}
    for arcs in s_["x"].values():
        terms = [a for a in arcs if a[0] == "term"]
        if not any(a[4] is not None and a[4].split(":")[0] in ids_ for a in terms):
            o_["n9"] += 1
            if terms:
                o_["bad_term"] += 1                  # a terminal arc at a closed site or a dummy one (none expected)
            else:
                o_["no_term"] += 1
                o_["at_site"] += int(tuple(arcs[-1][2][0]) in node_)
                o_["lev"][arcs[-1][2][2]] += 1
        sw = [a[1][2] for a in arcs if a[0] == "swap"]
        o_["never"] += int(not sw)
        o_["sw_n"] += len(sw)
        o_["sw_q"] += sum(sw)
        o_["sw_low"] += sum(1 for q in sw if q <= 6)
    return o_


def _sig(c_):
    return c_["half"] is not None and abs(c_["mean"]) > c_["half"]


def pen_points(dtot, dn9, st_, p_, pmax=10000.0):
    """penalty per rider at which the mean regret changes sign, and at which its 95 % interval stops (or starts)
    excluding zero. The mean is linear in pen and the half-width convex, so an interval that excludes zero at pen = 0
    stops doing so at one penalty at most (bisection); one that includes zero is scanned in steps of 1 USD."""
    def ci(pen):
        return stratified_ci([t + pen * n for t, n in zip(dtot, dn9)], st_, p_)
    c0 = ci(0.0)
    dbar = sum(p * x for p, x in zip(p_, dn9))
    flip = (-c0["mean"] / dbar) if c0["mean"] * dbar < 0 else None
    if _sig(c0):
        sgn = 1.0 if c0["mean"] > 0 else -1.0

        def f(pen):
            c_ = ci(pen)
            return sgn * c_["mean"] - c_["half"]
        lo, hi = 0.0, 1.0
        while f(hi) > 0 and hi < pmax:
            lo, hi = hi, 2.0 * hi
        if f(hi) > 0:
            return dbar, flip, "stays significant", None
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
        return dbar, flip, "stops being significant at", hi
    for pen in range(1, int(pmax) + 1):
        if _sig(ci(float(pen))):
            return dbar, flip, "becomes significant at", float(pen)
    return dbar, flip, "never significant", None


_cu = list(cells_of(BEST).values())
P_ORDER = sum(r_["components"]["unserved"] for r_ in _cu) / max(sum(r_["metrics"]["n_unserved"] for r_ in _cu), 1)
PENS = (0.0, P_ORDER, 2.0 * P_ORDER)
print(f"[O] end-of-evening riders below the reserve (no terminal arc at an open site, '(9)'), riders who never swap, "
      f"battery level at the swap, and regrets with a penalty per such rider; P = {P_ORDER:.2f} USD per unserved order "
      f"(components.unserved / metrics.n_unserved of the best layout's cells); reserve {Q_RES} of 24 levels")
EOUT = {}
for kind, held in (("in_sample", False), ("held_out", True)):
    d_ = S.scenario_design(12, held_out=held)
    st_, p_, seeds_ = [x["stratum"] for x in d_], [x["p"] for x in d_], [x["seed"] for x in d_]
    print(f"  {kind}, per layout, p-weighted per evening: '(9)' riders [cache count; evenings where the two agree; range; "
          f"terminal arcs at a closed site or dummy; of the rider-evenings, at an open site's node at 20:00; level at 20:00]"
          f" | never swap | swaps | mean level at the swap (share at <= 6 levels) | max |final_summary - cache| total")
    for nm in FS[kind]:
        cc = cells_of(FS[kind][nm]["layout_key"], held)
        if any(s not in cc for s in seeds_):
            print(f"    {nm:22s} cells missing: {[s for s in seeds_ if s not in cc]}")
            continue
        es = [end_state(cc[s]) for s in seeds_]
        tot = [FS[kind][nm]["C_setup"] + o for o in FS[kind][nm]["opex"]]
        EOUT[(kind, nm)] = {"n9": [e["n9"] for e in es], "tot": tot}

        def w(f):
            return sum(p * f(e) for p, e in zip(p_, es))
        lev = collections.Counter()
        for p, e in zip(p_, es):
            for q, c in e["lev"].items():
                lev[q] += p * c
        n9s = [e["n9"] for e in es]
        sw_n = w(lambda e: e["sw_n"])
        print(f"    {nm:22s} '(9)' {w(lambda e: e['n9']):5.2f} [{w(lambda e: e['fam9']):5.2f}; "
              f"{sum(1 for e in es if e['n9'] == e['fam9'])}/12; {min(n9s)}-{max(n9s)}; {sum(e['bad_term'] for e in es)}; "
              f"{sum(e['at_site'] for e in es)}/{sum(e['no_term'] for e in es)}; "
              f"{ {q: round(v, 2) for q, v in sorted(lev.items())} }] | never {w(lambda e: e['never']):5.2f} of "
              f"{es[0]['n_bikes']} | swaps {sw_n:5.1f} | level at the swap {w(lambda e: e['sw_q']) / sw_n:5.2f} "
              f"({w(lambda e: e['sw_low']) / sw_n:.3f}) | {max(abs(t - cc[s]['total']) for t, s in zip(tot, seeds_)):.1e}")
    print(f"  {kind}: regret against the best with pen USD per '(9)' rider (paired, stratified_ci); '(9)' difference "
          f"per evening; penalty per rider at which the mean regret changes sign; what its 95 % interval does")
    b_ = EOUT[(kind, "best")]
    order = {pen: [] for pen in PENS}
    status = {pen: {} for pen in PENS}
    for nm in FS[kind]:
        if nm == "best" or (kind, nm) not in EOUT:
            continue
        a_ = EOUT[(kind, nm)]
        dn9 = [x - y for x, y in zip(a_["n9"], b_["n9"])]
        dtot = [x - y for x, y in zip(a_["tot"], b_["tot"])]
        parts = []
        for pen in PENS:
            c_ = stratified_ci([t + pen * n for t, n in zip(dtot, dn9)], st_, p_)
            parts.append(f"{pen:5.1f}: {c_['mean']:8.1f} +- {c_['half']:6.1f}")
            status[pen][nm] = (c_["mean"] > 0, _sig(c_))
            if FS[kind][nm]["n_open"] == 15:
                order[pen].append((c_["mean"], nm))
        dbar, flip, what, at = pen_points(dtot, dn9, st_, p_)
        print(f"    {nm:22s} " + "; ".join(parts) + f" | '(9)' {dbar:+5.2f} | sign changes at "
              f"{'%.0f' % flip if flip is not None else 'no penalty'} | {what}{' %.0f' % at if at is not None else ''}")
    for pen in PENS:
        print(f"  {kind}: 15-site layouts by mean regret at pen {pen:.0f}: " + " < ".join(nm for _m, nm in sorted(order[pen])))
    for a_nm, b_nm in (("kmedian15", "free"), ("CSAV15", "free"), ("CSTC15", "dotfirst15"), ("CSCD15", "dotfirst15"),
                       ("CSTC15", "CSCD15"), ("restart:m2_incumbent", "restart:CSAV_best2")):      # pairs inside a group
        if (kind, a_nm) in EOUT and (kind, b_nm) in EOUT:
            A_, B_ = EOUT[(kind, a_nm)], EOUT[(kind, b_nm)]
            parts = []
            for pen in PENS:
                c_ = stratified_ci([x - y + pen * (u - v) for x, y, u, v in zip(A_["tot"], B_["tot"], A_["n9"], B_["n9"])], st_, p_)
                parts.append(f"{pen:5.1f}: {c_['mean']:7.1f} +- {c_['half']:6.1f}")
            print(f"  {kind}: {a_nm} - {b_nm} with the same charge on both: " + "; ".join(parts))
    for pen in PENS[1:]:
        ch = [nm for nm in status[0.0] if status[pen][nm] != status[0.0][nm]]
        print(f"  {kind}: at pen {pen:.0f}, comparisons whose sign or significance differs from pen 0: "
              + (", ".join(f"{nm} {status[0.0][nm]} -> {status[pen][nm]} (positive, significant)" for nm in ch) or "none"))

# ---------------------------------------------------------------- [P]
VP = os.path.join(RUN, "validate.json")
if not os.path.exists(VP):
    print("[P] exact check: no validate.json in this run")
else:
    import hashlib
    VJ = json.load(open(VP))
    _md5v = hashlib.md5(open(VP, "rb").read()).hexdigest()
    _vrec = [json.loads(line) for line in open(os.path.join(RUN, "records.jsonl"))]
    _vrec = [r_ for r_ in _vrec if r_.get("stage") == "validate"]
    _same = [nm_ for nm_ in (RUN48_NAME, PLAN_A, PLAN_B) if os.path.abspath(run_dir(nm_)) != os.path.abspath(RUN)
             and os.path.exists(os.path.join(run_dir(nm_), "validate.json"))
             and hashlib.md5(open(os.path.join(run_dir(nm_), "validate.json"), "rb").read()).hexdigest() == _md5v]
    print(f"[P] exact check (validate.json md5 {_md5v[:10]}, "
          f"{'a byte-identical copy of the validate.json of ' + ', '.join(_same) if _same else 'not a copy of another run'}; "
          f"validate rows in this run's records.jsonl {len(_vrec)}): {VJ['n_bikes']} riders, k = {VJ['k']}, "
          f"{VJ['time_limit']:g} s and {VJ['threads']} threads per solve; {VJ['n_cells']} cells, {VJ['n_optimal']} OPTIMAL; "
          f"ratio rule / exact median {VJ['ratio_median']:.3f} (min {VJ['ratio_min']:.3f}, max {VJ['ratio_max']:.3f}); "
          f"gap median {VJ['gap_median']:.1e}, max {VJ['gap_max']:.1e}")
    for row in VJ["rows"]:
        print(f"  {row['name']:8s} evening {row['scenario']} (seed {row['seed']}): rule {row['rule_total']:7.1f} exact "
              f"{row['ilp_incumbent']:7.1f} bound {row['ilp_bound']:7.1f} gap {row['ilp_gap']:.1e} {row['ilp_status']} ratio "
              f"{row['ratio_rule_over_incumbent']:.3f} | served rule {row['rule_served']:.4f} exact {row['ilp_served']:.4f} | "
              f"solve {row['ilp_runtime_s']:.0f} s, {row['n_arcs'] / 1e6:.2f} M arcs, {row['n_binaries']:,} binaries, "
              f"start {row['mip_start']}")
    lays = list(dict.fromkeys(r_["name"] for r_ in VJ["rows"]))
    key_of = {r_["name"]: r_["layout_key"] for r_ in VJ["rows"]}
    ev_ = sorted({r_["scenario"] for r_ in VJ["rows"]})
    val = {(r_["name"], r_["scenario"]): r_ for r_ in VJ["rows"]}
    for lab, fld, vals in (("rule", "rule_total", "rule_values"), ("exact", "ilp_incumbent", "ilp_values")):
        mean_ = {n_: sum(val[(n_, s_)][fld] for s_ in ev_) / len(ev_) for n_ in lays}
        rk = sorted(lays, key=lambda n_: mean_[n_])
        print(f"  {lab:5s}: mean of the {len(ev_)} evenings " + ", ".join(f"{n_} {mean_[n_]:.1f}" for n_ in lays)
              + f" (validate.json {vals}: " + ", ".join(f"{n_} {VJ[vals][n_]:.1f}" for n_ in lays)
              + f"); order {' < '.join(rk)}; above the first: " + ", ".join(f"{n_} +{mean_[n_] - mean_[rk[0]]:.1f}" for n_ in rk[1:])
              + "; order per evening: " + "; ".join(f"{s_}: {' < '.join(sorted(lays, key=lambda n_: val[(n_, s_)][fld]))}" for s_ in ev_))
    for n_ in lays:
        print(f"  {n_:8s} {key_of[n_].replace(':SC:B3:C2', '')}: served rule "
              f"{sum(val[(n_, s_)]['rule_served'] for s_ in ev_) / len(ev_):.4f}, exact "
              f"{sum(val[(n_, s_)]['ilp_served'] for s_ in ev_) / len(ev_):.4f} (mean of the evenings)")
    for rec in _vrec:
        if rec.get("kind") == "price15":
            c_ = rec["components"]
            print(f"  records {rec['tag']:13s} {rec['name']:8s} V {rec['V']:7.1f} served {rec['served_share']:.4f} swaps "
                  f"{rec['n_swaps_mean']:5.2f} kWh {rec['kwh_mean']:5.2f} | unserved {c_['unserved']:6.1f} "
                  f"({c_['unserved'] / P_ORDER:.2f} orders) response {c_['response']:6.1f} lateness {c_['lateness']:5.1f} travel "
                  f"{c_['C_travel']:4.1f} electricity {c_['C_elec']:4.2f} set-up {c_['C_setup']:5.2f}")
        elif rec.get("kind") == "validate_plan":
            print(f"  records validate_plan: greedy source {rec.get('greedy_source')!r}, {rec.get('n_scenarios')} evenings, "
                  f"{rec.get('n_bikes')} riders, workers {rec.get('workers')}")
    _vmd5 = {r_["demand_md5"] for r_ in INDEX if r_.get("policy") == "ilp"}
    _vc = [r_ for r_ in INDEX if r_.get("demand_md5") in _vmd5]
    for n_ in lays:
        for pol in ("baseline", "ilp"):
            cc = sorted((r_ for r_ in _vc if r_["layout_key"] == key_of[n_] and r_.get("policy") == pol), key=lambda r_: r_["seed"])
            if cc:
                print(f"  cache {n_:8s} {pol:8s} " + "; ".join(
                    f"seed {r_['seed']}: '(9)' {(r_.get('check_families') or {}).get('(9)', 0)} (families {r_.get('check_families')}, "
                    f"check_ok {r_.get('check_ok')}), unserved {r_['metrics']['n_unserved']} (unservable {r_.get('n_unservable')}), "
                    f"swaps {r_['metrics']['n_swaps']}" for r_ in cc))
    _vr = [r_ for r_ in _vc if r_.get("policy", "baseline") == "baseline"]
    print(f"  rule cells on the {VJ['n_bikes']}-rider evenings (search at that fleet + the three layouts): {len(_vr)}; with a "
          f"'(9)' rider {sum(1 for r_ in _vr if (r_.get('check_families') or {}).get('(9)'))} "
          f"({[(r_['layout_key'].replace(':SC:B3:C2', ''), r_['seed']) for r_ in _vr if (r_.get('check_families') or {}).get('(9)')]})")
