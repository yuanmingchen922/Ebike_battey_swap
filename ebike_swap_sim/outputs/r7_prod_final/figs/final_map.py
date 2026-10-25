"""Final map of the R7 Manhattan siting production run (laptop, records only, no solve).

Panel A: the whole study region (Manhattan south of 110th St). Panel B: zoom on Lower Manhattan
to Midtown East, where every chosen and rule site lies except CSAV's D58.

Shown: every candidate by class / DOT type (marker shape), the 23 one-site-feasible locations
(filled dark) against the 36 terminal-infeasible-alone ones (hollow grey; skip list of the feas
stage), the hub-capable set (violet edge), the best layout found per budget m = 1, 2, 3, the DOT
pilot sites, and the rule layouts priced in the comparison stage (CSCD m = 1, 2, 3, CSAV m = 2;
the DOT pilot proxy / all-pilot layout = the two in-region pilot sites).

Inputs: ``../r7_siting/{candidates.csv, map_data.csv, records.jsonl}`` (written by
``r7_siting.py --stage analyse``), the NTA polygons ``data/raw/nycnhood_acs.geojson``, the entry
points of ``data_nyc.MANHATTAN_ENTRY_POINTS``.  The m = 2 best layout is read from the last
``budget_result`` record (the improved in-sample value 716.85 of the oos re-solve does not change
the layout).  Writes ``fig_final_map.{png,pdf}`` next to this script.

Run: python3 outputs/r7_prod_final/figs/final_map.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(os.path.dirname(HERE), "r7_siting")
PKG = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))          # .../ebike_swap_sim (package root)
sys.path.insert(0, PKG)
NTA = os.path.join(os.path.dirname(PKG), "data", "raw", "nycnhood_acs.geojson")

BLUE, ORANGE, AQUA, RED, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#6250d6"
INK, MUTED, GRID = "#1f1f1f", "#9a9a9a", "#d6d6d6"
MARKERS = {"pilot": "o", "installed": "p", "shortlist": "s", "citibike_charging": "^", "depot": "h", "other": "X"}
LABELS = {"pilot": "DOT 2024 pilot hub", "installed": "installed cabinet", "shortlist": "DOT PEC preliminary site",
          "citibike_charging": "Citi Bike charging dock", "depot": "operator store / hub", "other": "other (planned)"}


def jl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def items(key):
    return [p.split(":")[0] for p in key.split("|")] if key else []


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from ebike_swap_sim import data_nyc as dn
    sys.path.insert(0, os.path.join(PKG, "outputs", "r7_siting", "figs"))
    from siting_map import nta_polygons

    cands = {r["id"]: r for r in csv.DictReader(open(os.path.join(RUN, "candidates.csv"), encoding="utf-8"))}
    for r in csv.DictReader(open(os.path.join(RUN, "map_data.csv"), encoding="utf-8")):
        cands.setdefault(r["id"], {}).update(r)
    recs = jl(os.path.join(RUN, "records.jsonl"))
    unit = 52150.0
    best = {}
    for r in recs:
        if r.get("kind") == "budget_result" and r.get("best_layout"):
            best[int(round(float(r["budget"]) / unit))] = r["best_layout"]
    rules = {}
    for r in recs:
        if r.get("kind") == "baseline" and r.get("layout_key"):
            rules[(r["rule"], int(round(float(r["budget"]) / unit)))] = r["layout_key"]
    infeasible = set()
    for r in recs:
        if r.get("kind") == "feas_skip_list":
            infeasible = set(r["locations"])
    feasible = sorted(c for c in cands if c not in infeasible)
    pilots = sorted(c for c, r in cands.items() if (r.get("dot_type") or "") == "pilot")

    def ll(cid):
        r = cands[cid]
        return float(r["lon"]), float(r["lat"])

    box = dn.MANHATTAN_BOX
    rings = nta_polygons(NTA, box.lat_min, box.lat_max, box.lon_min, box.lon_max)
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.5, 6.6), gridspec_kw={"width_ratios": [1.0, 1.25]})
    zoom = (-74.012, -73.958, 40.712, 40.768)                 # lon_min, lon_max, lat_min, lat_max
    lat_lims = {axA: (box.lat_min, 40.805), axB: (zoom[2], zoom[3])}
    lon_lims = {axA: (box.lon_min, -73.925), axB: (zoom[0], zoom[1])}
    for ax in (axA, axB):
        for ring in rings:
            ax.fill([p[0] for p in ring], [p[1] for p in ring], color="#f3f3f1", ec=GRID, lw=0.4, zorder=0)
        ax.set_xlim(*lon_lims[ax])
        ax.set_ylim(*lat_lims[ax])
        mid = 0.5 * sum(lat_lims[ax])
        ax.set_aspect(1.0 / math.cos(math.radians(mid)))
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_color(GRID)
    s_base = {axA: 26, axB: 60}
    for ax in (axA, axB):
        for cid, r in cands.items():
            lon, lat = ll(cid)
            mk = MARKERS.get(r.get("dot_type") or "", "o")
            if r.get("cls") == "lattice":
                mk = "o"
            feas = cid not in infeasible
            if r.get("cls") == "lattice":
                ax.scatter([lon], [lat], marker="o", s=s_base[ax], facecolors="white",
                           edgecolors=INK if feas else MUTED, linewidths=1.0 if feas else 0.6, linestyle="--", zorder=3)
                if feas:
                    ax.scatter([lon], [lat], marker=".", s=8, c=INK, zorder=3)
            else:
                ax.scatter([lon], [lat], marker=mk, s=s_base[ax], facecolors="#4a4a4a" if feas else "white",
                           edgecolors=INK if feas else MUTED, linewidths=0.6, zorder=3)
            if str(r.get("hub_capable", "")).strip().lower() in ("1", "true", "1.0"):
                ax.scatter([lon], [lat], marker=mk, s=s_base[ax] * 2.2, facecolors="none", edgecolors=VIOLET,
                           linewidths=0.9, zorder=2)
        for name, (lat, lon) in dn.MANHATTAN_ENTRY_POINTS.items():
            ax.scatter([lon], [lat], marker="*", s=s_base[ax] * 1.6, c="#5a5a5a", edgecolors="white", linewidths=0.4, zorder=4)
        # DOT pilot sites
        for cid in pilots:
            lon, lat = ll(cid)
            ax.scatter([lon], [lat], marker="o", s=s_base[ax] * 7, facecolors="none", edgecolors=RED, linewidths=1.3,
                       linestyle=(0, (2, 1.5)), zorder=5)
        # rule layouts
        cscd = set()
        for m in (1, 2, 3):
            cscd |= set(items(rules.get(("CSCD", m))))
        for cid in cscd:
            lon, lat = ll(cid)
            ax.scatter([lon], [lat], marker="s", s=s_base[ax] * 5, facecolors="none", edgecolors=ORANGE, linewidths=1.4, zorder=5)
        for cid in items(rules.get(("CSAV", 2))):
            lon, lat = ll(cid)
            ax.scatter([lon], [lat], marker="D", s=s_base[ax] * 4.5, facecolors="none", edgecolors=AQUA, linewidths=1.4, zorder=5)
        # best layouts per budget
        for m, key in sorted(best.items()):
            for cid in items(key):
                lon, lat = ll(cid)
                ax.scatter([lon], [lat], marker="o", s=s_base[ax] * (9 + 3 * m), facecolors="none", edgecolors=BLUE,
                           linewidths=2.0 if m == 1 else 1.4, linestyle="-" if m != 3 else (0, (3, 1.5)), zorder=6)
    # labels (zoom panel): one line per highlighted site, offset away from the marker
    roles = {}
    for m, key in sorted(best.items()):
        for p in key.split("|"):
            cid, role, b, c = p.split(":")
            roles.setdefault(cid, []).append(f"best m={m} {role}:{b}:{c}")
    for (rule, m), key in sorted(rules.items()):
        for cid in items(key):
            tag = "pilot pair" if rule.startswith("dot_") else f"{rule} m={m}"
            if tag not in roles.setdefault(cid, []):
                roles[cid].append(tag)
    offsets = {"D23": (10, 10), "D07": (-14, 12), "D45": (10, -2), "D18": (-16, -26), "D19": (10, -20), "D12": (-14, -18),
               "D30": (10, 6), "D58": (8, 6), "D24": (12, -12)}
    for cid, tags in roles.items():
        lon, lat = ll(cid)
        lab = f"{cid}: " + ", ".join(tags)
        for ax, inside in ((axB, zoom[0] <= lon <= zoom[1] and zoom[2] <= lat <= zoom[3]), (axA, cid == "D58")):
            if not inside:
                continue
            dx, dy = offsets.get(cid, (10, 8))
            ax.annotate(lab, (lon, lat), xytext=(dx, dy), textcoords="offset points", fontsize=6.6, color=INK,
                        ha="right" if dx < 0 else "left", zorder=8,
                        bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85),
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5))
    # zoom rectangle on panel A
    axA.plot([zoom[0], zoom[1], zoom[1], zoom[0], zoom[0]], [zoom[2], zoom[2], zoom[3], zoom[3], zoom[2]], color=MUTED,
             lw=0.8, ls="--", zorder=1)
    axA.set_title(f"A. Study region: {len(cands)} candidates, {len(feasible)} feasible as a single site", fontsize=9, color=INK)
    axB.set_title("B. Lower Manhattan to Midtown East (zoom)", fontsize=9, color=INK)
    types = sorted({(r.get("dot_type") or "") for r in cands.values() if r.get("cls") != "lattice"} - {""})
    h = [Line2D([], [], marker=MARKERS[t], color="#4a4a4a", mec=INK, lw=0, ms=6, label=LABELS[t]) for t in types]
    h += [Line2D([], [], marker="o", mfc="white", mec=INK, ls="none", ms=6, label="lattice cell (restaurant density)"),
          Line2D([], [], marker="s", mfc="#4a4a4a", mec=INK, ls="none", ms=6, label="filled: feasible as a single site (23)"),
          Line2D([], [], marker="s", mfc="white", mec=MUTED, ls="none", ms=6, label="hollow grey: terminal-infeasible alone (36)"),
          Line2D([], [], marker="o", mfc="none", mec=VIOLET, ls="none", ms=9, label="hub-capable (12)"),
          Line2D([], [], marker="*", color="#5a5a5a", ls="none", ms=9, label="entry point (bridge / tunnel)"),
          Line2D([], [], marker="o", mfc="none", mec=BLUE, mew=2.0, ls="none", ms=12, label="best layout found, m = 1 (D23)"),
          Line2D([], [], marker="o", mfc="none", mec=BLUE, mew=1.4, ls="none", ms=13,
                 label="best m = 2 (B3:C2) and m = 3 (B4:C2, dashed): D07 + D45"),
          Line2D([], [], marker="o", mfc="none", mec=RED, mew=1.3, ls="none", ms=12, label="DOT pilot site (= pilot proxy layout)"),
          Line2D([], [], marker="s", mfc="none", mec=ORANGE, mew=1.4, ls="none", ms=10, label="CSCD rule site (m = 1, 2, 3)"),
          Line2D([], [], marker="D", mfc="none", mec=AQUA, mew=1.4, ls="none", ms=9, label="CSAV rule site (m = 2)")]
    fig.legend(handles=h, loc="lower center", ncol=3, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.17, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(HERE, f"fig_final_map.{ext}"), dpi=300, bbox_inches="tight")
    print(json.dumps({"best": best, "rules": {f"{k[0]}@{k[1]}": v for k, v in rules.items()}, "feasible": feasible,
                      "pilots": pilots}))


if __name__ == "__main__":
    main()
