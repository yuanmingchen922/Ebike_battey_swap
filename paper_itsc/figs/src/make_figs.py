"""Figures of the ITSC siting paper (laptop only, no solver run).

Writes, next to the paper (``paper_itsc/figs/``):
  fig_map.{pdf,png}    Fig. 4  where the best one- and two-site layouts are, against the DOT pilot and a rule
  fig_onesite.{pdf,png} Fig. 5  the one-site answer is a corridor: 11 near-tie sites, with and without the
                               14-block approach limit (RESULTS_final.md sec. 1 and 6)
  fig_budget.{pdf,png}  Fig. 6  best layout found and lower bound per budget unit (RESULTS_final.md sec. 0-2)
  fig_costs.{pdf,png}  Fig. 7  daily cost of eight layouts, split into unserved-order penalty and other costs
  fig_framework.{pdf,png}      Fig. 1 preview, compiled from ``figs/fig_framework.tex`` (TikZ, the paper
                               \\input's the .tex itself; the PDF is a fallback)
  fig_map15.{pdf,png}  Fig. 4 (15-site study, replaces fig_map): only the 15 open sites, numbered as in the site
                       table, on a plain base map (land with the New Jersey shore, water, parks, OSM major streets, the
                       six bridges and tunnels the text names, restaurant density as a soft orange shading on
                       Manhattan; no neighbourhood names, no colour bar, no credit line: the caption names the shading
                       and the OSM credit, and credits the land and parks to the city's 2010 neighborhood tabulation
                       areas via the GeoDa Center); ``make_figs.py
                       map15`` draws it in two frames, fig_map15_northup (north-up, 3.5 in wide) and
                       fig_map15_rotated (street grid, 7.16 in wide), and copies MAP15_PREFERRED to fig_map15
                       (``fig_map15_plain``).  The former map (restaurant density, unchosen candidates, land beyond
                       reach, rider entry points, legend) is ``make_figs.py map15_detailed`` -> fig_map15_detailed
                       (``fig_map15``).  Both targets also write
  site_table.tex       its 15-row companion table (table*, full width) and
  site_table_compact.tex  the same rows in one column (table: No., site, area, swaps per evening, cost rise if
                       closed; R11: the sites within 1 km of an entry point in bold, no busy column); both carry
                       \\label{tab:sites15}, the paper inputs one of them.  Inputs:
                       ``figs/map15/layout.json`` and ``figs/map15/site_stats.csv``, copied from the R8 run of
                       record ``cloud_results/ebike_swap_sim/outputs/r8_k15_sp/`` (plan B: each site has its own
                       1.4 kW connection, the shared limit lifted; schema: ``LAYOUT15_SCHEMA`` /
                       ``SITE_STATS15_COLUMNS`` below and notes/siting15_design.md section 6.1).  The captions take
                       the power model from layout.json (``grid_kw``, ``site_kw``; ``power_clause15``).  Plan A's
                       inputs (r8_k15_n64, one 2 kW supply shared by all sites; its layout.json has no power fields)
                       are kept for the record in ``figs/map15_planA/`` (not rendered).
                       ``make_figs.py map15_demo`` renders a DEMO from a CSCD-15 rule layout with synthetic
                       statistics (inputs in ``figs/map15_demo/``, outputs ``fig_map15_demo`` and
                       ``site_table_demo*.tex``, so the demo never overwrites the real figure); the demo is
                       labelled DEMO in the legend, on the map and in the tables.
  fig_vk.{pdf,png}     15-site study, column width: daily cost (95 % CI) and share of orders served against the
                       number of open sites k = 1, 2, 5, 10, 15, 20, read from the run named in figs/map15/layout.json
                       (``run``, a folder of ``cloud_results/ebike_swap_sim/outputs/``; or ``vk --run NAME_OR_DIR``):
                       its final_summary.json (``vk``, ``in_sample``), else its RESULTS.md ("Final table").

Every number of the one-to-three-site figures (map, onesite, budget, costs) is copied by hand from
``ebike_swap_sim/outputs/r7_prod_final/RESULTS_final.md``; the section is cited next to each value.  The 15-site
figures (map15, vk) copy no number by hand: they read the run's own files (layout.json, site_stats.csv,
final_summary.json or RESULTS.md).
Map geometry: candidate coordinates from ``ebike_swap_sim/outputs/r7_prod_final/r7_siting/candidates.csv``
(the run's own candidate file, ids D01-D59), the single-site-feasible set from the ``feas_skip_list`` record of
``r7_siting/records.jsonl``, Manhattan outline from ``data/raw/nycnhood_acs.geojson``.

Colours (one scheme for every figure):
  blue  #2a78d6  layouts found by our method
  red   #d03b3b  DOT 2024 pilot pair
  dark grey #555555  rule layouts and role variants (alternatives)
  light grey #b4b4b4  context (candidate sites)
Blue and red pass the dataviz validator all-pairs (CVD dE 23.8, normal 31.6); shapes differ too
(star / circle = ours, square = pilot, triangle = rule), so the map also reads in greyscale.

Run:  python3 paper_itsc/figs/src/make_figs.py                 (all figures; map15 only if its inputs exist)
      python3 paper_itsc/figs/src/make_figs.py onesite budget  (only the named ones)
      python3 paper_itsc/figs/src/make_figs.py map15 [--layout L.json --stats S.csv]
      python3 paper_itsc/figs/src/make_figs.py map15_detailed  (the former map; only on request, like map15_demo)
      python3 paper_itsc/figs/src/make_figs.py map15_demo      (DEMO inputs + figure + tables, *_demo names)
      python3 paper_itsc/figs/src/make_figs.py vk [--run RUN]  (cost and served share against the number of sites;
                                                               RUN: a run name or folder, default the layout's run)
Streets on fig_map15: cached OpenStreetMap extract ``data/raw/osm_major_roads_manhattan.json``
(ODbL, (c) OpenStreetMap contributors; the caption must carry this credit, the map itself has no credit line since
2026-10-31); ``osm_fetch_streets()``
rebuilds the cache from the Overpass API when it is missing.  The New Jersey shore: cached OSM coastline
``data/raw/osm_coastline_manhattan.json`` (same licence and credit), rebuilt by ``osm_fetch_coast()``.
Land of Manhattan, Brooklyn and Queens and the parks on fig_map15: the 195 NTA polygons of
``data/raw/nycnhood_acs.geojson`` (the GeoDa Center's "NYC Neighborhoods ACS 2008-12", i.e. the city's 2010
neighborhood tabulation areas; data/MANIFEST.md section 2); the caption credits them in plain text (R11, 2026-10-31:
not the reference dcp2026acs, which is the 2020-24 ACS tables by 2020 NTA, a different data set).
Restaurant density on fig_map15: NYC DOHMH inspection records ``data/raw/dohmh_restaurants.csv`` (``DENS15``).
The project root (for the run records and the map outline) is two levels above ``paper_itsc``; set
``BSWAP_ROOT`` to override it when the script runs from a copy of the paper folder.
"""
from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.dirname(HERE)                                   # paper_itsc/figs
ROOT = os.environ.get("BSWAP_ROOT") or os.path.dirname(os.path.dirname(FIGS))   # OR Model-Battery Swap
RUN = os.path.join(ROOT, "ebike_swap_sim", "outputs", "r7_prod_final", "r7_siting")
NTA = os.path.join(ROOT, "data", "raw", "nycnhood_acs.geojson")

OURS, PILOT, ALT, CONTEXT = "#2a78d6", "#d03b3b", "#555555", "#b4b4b4"
OURS_L, PILOT_L, ALT_L = "#a9c8ef", "#efb1b1", "#c4c4c4"    # light tints for the "other costs" part
INK, INK2, LAND, EDGE = "#111111", "#555555", "#f1f1ef", "#a8a8a4"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "STIXGeneral"],
    "mathtext.fontset": "stix",
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.5,
    "savefig.dpi": 300,
})


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGS, f"{name}.{ext}"), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------------------------
# Map geometry: local metres, rotated so the avenues run left (south) to right (north)
# ---------------------------------------------------------------------------------------------------------------
LAT0, LON0 = 40.7580, -73.9855          # Times Square, only the origin of the local frame
GRID_DEG = 29.0                         # Manhattan street grid is about 29 degrees east of true north
_C, _S = math.cos(math.radians(90 - GRID_DEG)), math.sin(math.radians(90 - GRID_DEG))


def rot(lat, lon):
    """(lat, lon) -> (x, y) in km; x along the avenues (north is +x), y across (west / Hudson is +y)."""
    e = (lon - LON0) * 111.320 * math.cos(math.radians(LAT0))
    n = (lat - LAT0) * 110.540
    return e * _C + n * _S, -e * _S + n * _C


def manhattan_rings():
    """Manhattan NTA outer rings inside the study box (same filter as outputs/r7_siting/figs/siting_map.py)."""
    lat_min, lat_max, lon_min, lon_max = 40.698, 40.807, -74.020, -73.925      # data_nyc.MANHATTAN_BOX
    g = json.load(open(NTA, encoding="utf-8"))
    rings = []
    for f in g["features"]:
        if str(f["properties"].get("borocode", "")).strip() not in ("1", "1.0"):
            continue
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            ring = poly[0]
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            if max(lats) < lat_min or min(lats) > lat_max or max(lons) < lon_min or min(lons) > lon_max:
                continue
            if sum(lons) / len(lons) > -73.935:          # Randall's Island (outside the study area)
                continue
            r = [rot(p[1], p[0]) for p in ring]
            area = 0.5 * abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r))))
            if area < 0.03:                              # stray pier fragments and rocks, km^2
                continue
            rings.append(r)
    return rings


def hull(points):
    """Convex hull (monotone chain) of 2-D points."""
    pts = sorted(set(points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def rounded_hull(points, r):
    """Hull of discs of radius r around the points (a smooth shaded area)."""
    ring = []
    for x, y in points:
        for k in range(24):
            a = 2 * math.pi * k / 24
            ring.append((x + r * math.cos(a), y + r * math.sin(a)))
    return hull(ring)


def fig_map():
    cands = {r["id"]: r for r in csv.DictReader(open(os.path.join(RUN, "candidates.csv"), encoding="utf-8"))}
    assert len(cands) == 59, len(cands)                                              # RESULTS_final.md sec. 0

    def xy(cid):
        return rot(float(cands[cid]["lat"]), float(cands[cid]["lon"]))

    # RESULTS_final.md sec. 1, m = 1 near-ties: the 11 single sites within 3 % of the best (D23 ... D39),
    # E 13th St (D23) to E 54th St (D39), both sides of the island.
    near = ["D23", "D24", "D28", "D37", "D29", "D38", "D34", "D30", "D33", "D25", "D39"]
    best1 = "D23"                       # sec. 0: DOT PEC Site 34, 2nd Ave & E 13th St, 1,085.87, served 0.775
    best2 = ("D07", "D45")              # sec. 0: Greenwich Village grid cell + Citi Bike dock 3 Ave & E 62 St, 716.85
    alldot = ("D23", "D45")             # sec. 1 / sec. 4 DOT-only: 719.60, +2.75
    pilot = ("D12", "D18")              # sec. 4: DOT 2024 pilot pair, Essex Market + Cooper Sq, +134.42
    spread = ("D30", "D58")             # sec. 4: spread rule (CSAV), Midtown grid cell + W 106th St, +91.70

    rings = manhattan_rings()
    x110, _ = rot(40.7997, -73.9582)    # data_nyc.MANHATTAN_S110 north limit: W 110th St / Central Park West
    xbat, _ = rot(40.7003, -74.0170)    # The Battery
    x_lo, x_hi = xbat - 0.15, x110 + 0.05

    fig = plt.figure(figsize=(7.16, 2.05))
    ax = fig.add_axes([0.0, 0.0, 0.69, 1.0])
    lax = fig.add_axes([0.695, 0.0, 0.305, 1.0])
    lax.axis("off")
    for ring in rings:
        ax.add_patch(Polygon(ring, closed=True, fc=LAND, ec=EDGE, lw=0.9, zorder=0))
    for ring in rings:
        ax.add_patch(Polygon(ring, closed=True, fc=LAND, ec=LAND, lw=0.3, zorder=0.5))

    # Faint cross streets (streets run across the island, i.e. constant x), clipped to the island outline.
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    clip = PathPatch(Path.make_compound_path(*[Path(r + [r[0]], closed=True) for r in rings]),
                     fc="none", ec="none", transform=ax.transData)
    ax.add_patch(clip)
    streets = [("14th St", 40.7359, -73.9934), ("34th St", 40.7484, -73.9857), ("59th St", 40.7644, -73.9737),
               ("96th St", 40.7851, -73.9576)]                     # on 5th Ave
    for name, la, lo in streets:
        sx, _ = rot(la, lo)
        ln, = ax.plot([sx, sx], [-4.0, 2.5], color="#c9c9c4", lw=0.6, zorder=0.7)
        ln.set_clip_path(clip)
        ax.text(sx, -3.02, name, fontsize=7, color=INK2, ha="center", va="top", zorder=0.8)

    # One site: corridor of the 11 near-ties, each drawn as a small blue dot
    hx = rounded_hull([xy(c) for c in near], 0.28)
    ax.add_patch(Polygon(hx, closed=True, fc=OURS, alpha=0.13, ec="none", zorder=1))
    ax.add_patch(Polygon(hx, closed=True, fc="none", ec=OURS, lw=0.5, alpha=0.7, zorder=1))
    nx = [xy(c) for c in near if c != best1]
    ax.scatter([p[0] for p in nx], [p[1] for p in nx], s=7, c=OURS, alpha=0.75, lw=0, zorder=2)

    def pair(ids, color, marker, size, ls="-", lw=1.0, z=4):
        (x1, y1), (x2, y2) = xy(ids[0]), xy(ids[1])
        ax.plot([x1, x2], [y1, y2], ls=ls, color=color, lw=lw, zorder=z - 1, solid_capstyle="round")
        if marker:
            ax.scatter([x1, x2], [y1, y2], s=size, marker=marker, c=color, edgecolors="white",
                       linewidths=0.6, zorder=z)

    pair(spread, ALT, "^", 26)
    pair(pilot, PILOT, "s", 22)
    pair(alldot, OURS, None, 0, ls=(0, (3, 1.5)), lw=0.9)
    pair(best2, OURS, "o", 30, lw=1.5, z=5)
    bx, by = xy(best1)
    ax.scatter([bx], [by], s=120, marker="*", c=OURS, edgecolors="white", linewidths=0.6, zorder=6)

    halo = []                           # plain labels (no white halo); leaders keep them off the lines

    def note(cid, text, tx, ty, ha="center", va="center"):
        x, y = xy(cid)
        ax.annotate(text, (x, y), xytext=(tx, ty), ha=ha, va=va, fontsize=7.5, color=INK, path_effects=halo,
                    arrowprops=dict(arrowstyle="-", lw=0.4, color=INK2, shrinkA=1, shrinkB=3), zorder=7)

    note("D07", "Greenwich Village\n(grid cell)", -4.6, 1.3)
    note("D18", "Cooper Sq", -4.75, -0.95, ha="right")
    note("D12", "Essex Market", -4.95, -2.2, ha="right")
    note("D23", "DOT Site 34\n(2nd Ave & E 13th St)", -2.15, -2.45)
    note("D45", "3rd Ave & E 62nd St\n(Citi Bike dock)", 3.0, -2.45)
    note("D58", "DOT Site 16\n(W 106th St)", 4.6, 0.25, ha="right")

    ax0, ay0 = x_lo + 0.25, 1.0
    ux, uy = _S, _C
    ax.annotate("", xy=(ax0 + 0.6 * ux, ay0 + 0.6 * uy), xytext=(ax0, ay0),
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK2, mutation_scale=6))
    ax.text(ax0 + 0.8 * ux, ay0 + 0.8 * uy, "N", fontsize=7, color=INK2, ha="center", va="center")
    ax.plot([x_lo + 0.25, x_lo + 1.25], [-2.75, -2.75], color=INK2, lw=0.8)
    ax.text(x_lo + 0.75, -2.85, "1 km", fontsize=7, color=INK2, ha="center", va="top")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(-3.3, 2.0)
    ax.set_aspect("equal")
    ax.axis("off")

    h = [
        Line2D([], [], marker="*", ls="none", ms=9, mfc=OURS, mec="white", mew=0.5),
        (Patch(fc=matplotlib.colors.to_rgba(OURS, 0.13), ec=OURS, lw=0.5),
         Line2D([], [], marker="o", ls="none", ms=2.6, mfc=OURS, mec="none")),
        Line2D([], [], marker="o", ls="-", lw=1.5, ms=5, color=OURS, mec="white", mew=0.5),
        Line2D([], [], ls=(0, (3, 1.5)), lw=0.9, color=OURS),
        Line2D([], [], marker="^", ls="-", lw=1.0, ms=5, color=ALT, mec="white", mew=0.5),
        Line2D([], [], marker="s", ls="-", lw=1.0, ms=4.5, color=PILOT, mec="white", mew=0.5),
    ]
    lab = [
        "Best single site: DOT Site 34\n(PEC proposal), 1,086 USD/day",
        "11 single sites within 3 % of the best\n(13th to 54th St)",
        "Best pair: 717 USD/day (34 % less)",
        "All-DOT pair: +3 USD/day (a tie)",
        "Spread-rule pair: +92 USD/day",
        "DOT 2024 pilot pair:\n+134 USD/day",
    ]
    lax.legend(h, lab, loc="center left", bbox_to_anchor=(0.0, 0.5), frameon=False, handlelength=2.3,
               handletextpad=0.6, labelspacing=0.7, borderaxespad=0.0, fontsize=8)
    save(fig, "fig_map")


# ---------------------------------------------------------------------------------------------------------------
# Fig. 3: the one-site answer is a corridor (dot plot, with and without the 14-block approach limit)
# ---------------------------------------------------------------------------------------------------------------
def fig_onesite():
    # RESULTS_final.md sec. 1 (m = 1 near-ties, V_open with the 14-block limit, price_open @486-516) and
    # sec. 6 (no-radius re-pricing, noradius_result @993-1005). Labels: r7_siting/candidates.csv.
    # (label, V with limit, V without limit, without-value indicative?)
    rows = [
        ("DOT Site 34, 2nd Ave & E 13th St", 1085.87, 1078.16, False),      # D23
        ("Citi Bike dock, E 14th St & 1st Ave", 1087.74, 1078.32, False),   # D24
        ("Swobbee cabinet, 836 6th Ave", 1091.06, 1062.49, False),          # D28
        ("Citi Bike dock, 1st Ave & E 30th St", 1092.44, 1078.07, False),   # D37
        ("Swobbee cabinet, 124 W 31st St", 1095.90, 1062.87, False),        # D29
        ("Grid cell, Midtown East", 1097.95, 1071.30, False),               # D38
        ("Citi Bike dock, W 42nd St & 6th Ave", 1099.67, 1062.47, False),   # D34
        ("Grid cell, Midtown", 1102.40, 1069.16, False),                    # D30
        ("Zoomo store, 252 W 38th St", 1103.92, 1069.30, False),            # D33
        ("DOT Site 35, E 14th St & Ave A", 1105.78, 1092.78, False),        # D25
        ("DOT PEC site, E 54th St & 3rd Ave", 1109.86, 1086.43, True),          # D39 (* SKIPPED_BUDGET, indicative)
    ]
    assert rows[0][1] == min(r[1] for r in rows) and max(r[1] for r in rows) / rows[0][1] < 1.03
    NOLIM = "#6f6f6f"

    # Fixed axes box so the whole figure, row labels included, stays 3.45 in wide (column width, 7 pt text).
    fig = plt.figure(figsize=(3.45, 2.45))
    ax = fig.add_axes([0.445, 0.13, 0.545, 0.78])
    ys = list(range(len(rows)))
    ax.axvline(rows[0][1], color=OURS, lw=0.6, ls=(0, (3, 2)), alpha=0.8, zorder=1)
    for y, (lab, v_lim, v_no, ind) in zip(ys, rows):
        ax.plot([v_no, v_lim], [y, y], color="#c8c8c4", lw=1.0, zorder=2, solid_capstyle="butt")
        ax.scatter([v_no], [y], s=22, facecolors="white", edgecolors=NOLIM, linewidths=0.8, zorder=3,
                   linestyles=(0, (1.2, 0.9)) if ind else "solid")
        ax.scatter([v_lim], [y], s=24, c=OURS, edgecolors="white", linewidths=0.5, zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=7)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlim(1055, 1115)
    ax.set_xticks([1060, 1080, 1100])
    ax.set_xticklabels(["1,060", "1,080", "1,100"])
    ax.set_xlabel("Expected cost per day (USD)", fontsize=7.5, labelpad=2)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#888888")
    ax.tick_params(axis="x", length=2, color="#888888", pad=1.5, labelsize=7)
    ax.tick_params(axis="y", length=0, pad=3)
    ax.grid(axis="x", color="#ececea", lw=0.4, zorder=0)

    halo = []                           # plain text, no white halo
    ax.text(rows[0][1] + 0.8, -0.55, "best with limit", fontsize=7, color=OURS, ha="left", va="center",
            path_effects=halo, zorder=5)
    ax.text(1115, 1.6, "all 11 within\n3 % of the best", fontsize=7, color=INK, ha="right", va="center",
            linespacing=1.1, path_effects=halo, zorder=5)
    # the three Midtown sites that tie without the limit: D28 (row 2), D29 (row 4), D34 (row 6), at about 1,062.5
    bx = 1058.6
    ax.plot([bx, bx], [2, 6], color=INK2, lw=0.6, zorder=5, solid_capstyle="butt")
    for yy in (2, 4, 6):
        ax.plot([bx, 1061.2], [yy, yy], color=INK2, lw=0.6, zorder=5, solid_capstyle="butt")
    # the bracket spans only its own rows; the caption explains it (tie within 0.04 %, Site 34 then 8th)
    ax.text(1059.4, 3.0, "3-way tie", fontsize=7, color=INK2, ha="left", va="center", zorder=5)

    h = [Line2D([], [], marker="o", ls="none", ms=4.6, mfc=OURS, mec="white", mew=0.5),
         Line2D([], [], marker="o", ls="none", ms=4.4, mfc="white", mec=NOLIM, mew=0.8)]
    fig.legend(h, ["with the 14-block approach limit", "without the limit"], loc="upper left",
               bbox_to_anchor=(0.0, 1.0), ncol=2, frameon=False, handlelength=0.8, handletextpad=0.4, columnspacing=1.2, borderaxespad=0.1,
              fontsize=7)
    save(fig, "fig_onesite")


# ---------------------------------------------------------------------------------------------------------------
# Fig. 4: best layout found and lower bound per budget unit
# ---------------------------------------------------------------------------------------------------------------
def fig_budget():
    # RESULTS_final.md sec. 0 / 1: UB per m; sec. 2: open-sites certificate at m = 1 (V*_open in [1,084.31, 1,085.87],
    # 0.14 %); m = 2, 3: the master bound 670.23, also the open-sites bound (Section III-E: LB^open_m = LB_m for
    # m >= 2), so every gap drawn is an open-sites gap; sec. 1 m = 3: D07 + D23 + D45 = 718.80 (+8.82 +- 2.46),
    # B3 -> B4 at the two sites -6.87; sec. 0 / 7: served 0.775 -> 0.983, -34 %.  The all-candidates bound at one unit
    # (1,036.03, 4.59 %) and the spare move (-6.87) are in the text of VI-A / VI-B, not in the figure.
    # R11 (2026-10-31), readable at a glance: no legend (direct labels), the best layouts found joined by a thin blue
    # line, each bound a grey range line from the lower bound up to the dot with a dark cap at the bound (none at one
    # unit, where the 1.56 USD range hides under the dot), the gap printed beside each range, the third-site layout a
    # grey diamond (an alternative, not ours), integer labels as in fig_costs (display rounding only).
    ub = [1085.87, 716.85, 709.98]
    lb = [1084.31, 670.23, 670.23]      # 1 unit: open-sites certificate bound (sec. 2); 2, 3 units: master bound
    served = [0.775, 0.983, 0.985]
    third_site = 718.80
    gap = [f"{100 * (u - l) / u:.2f}" for u, l in zip(ub, lb)]           # (UB - LB) / UB, eq. certificate
    assert gap == ["0.14", "6.50", "5.60"], gap                           # the values the text quotes
    cut = round(100 * (ub[0] - ub[1]) / ub[0])
    assert cut == 34 and round(ub[1] - ub[2], 2) == 6.87

    def usd(v):                                                           # display rounding only
        return f"{v:,.0f}"

    fig, ax = plt.subplots(figsize=(3.6, 2.05))
    xs = [0, 1, 2]
    ax.plot(xs, ub, color=OURS, lw=0.8, zorder=3)                         # the best layouts found, joined
    for x, u, l in zip(xs, ub, lb):
        if u - l > 10.0:                  # a range shorter than the dot's radius (about 14 USD) would hide under it
            ax.plot([x, x], [l, u], color="#c4c4c4", lw=2.6, solid_capstyle="butt", zorder=1)
            ax.plot([x - 0.06, x + 0.06], [l, l], color=INK2, lw=0.8, zorder=2)
        ax.scatter([x], [u], s=34, c=OURS, edgecolors="white", linewidths=0.6, zorder=4)
    # direct labels: cost of each best layout found and its gap to the lower bound (each label at least 1.5 pt from
    # the blue line and the dots: ``chart_report``)
    ax.text(0.10, ub[0], usd(ub[0]), fontsize=7.5, ha="left", va="center", color=INK, zorder=5)
    ax.text(0.45, ub[0], f"gap {gap[0]} %", fontsize=7, ha="left", va="center", color=INK2, zorder=5)
    ax.text(0.90, ub[1], usd(ub[1]), fontsize=7.5, ha="right", va="center", color=INK, zorder=5)
    ax.text(1.09, 0.5 * (ub[1] + lb[1]) - 8, f"gap {gap[1]} %", fontsize=7, ha="left", va="center", color=INK2,
            zorder=5)
    ax.text(2.09, 0.5 * (ub[2] + lb[2]) - 8, f"gap {gap[2]} %", fontsize=7, ha="left", va="center", color=INK2,
            zorder=5)
    ax.text(2.10, ub[2] + 2, f"2 sites, 4 spares\neach: {usd(ub[2])}", fontsize=7.5, ha="left", va="bottom",
            color=INK, linespacing=1.1, zorder=5)
    # the third budget unit spent on a third site instead: a grey diamond left of the 3-unit column
    ax.scatter([1.8], [third_site], s=26, marker="D", facecolors="white", edgecolors=ALT, linewidths=0.9, zorder=4)
    ax.text(1.8, third_site + 22, f"3 sites:\n{usd(third_site)}", fontsize=7.5, ha="center", va="bottom", color=INK,
            linespacing=1.1, zorder=5)
    # the big step, beside the first segment
    ax.text(0.58, 0.5 * (ub[0] + ub[1]) + 25,
            f"cost \u2212{cut} %\nserved {100 * served[0]:.1f} % \u2192 {100 * served[1]:.1f} %", fontsize=7.5,
            ha="left", va="center", color=INK, linespacing=1.15, zorder=5)
    ax.set_xticks(xs)
    ax.set_xticklabels(["1 unit", "2 units", "3 units"])
    ax.set_xlim(-0.35, 2.75)
    ax.set_ylim(600, 1150)
    ax.set_yticks([700, 800, 900, 1000, 1100])
    ax.set_yticklabels(["700", "800", "900", "1,000", "1,100"])
    ax.set_ylabel("Daily cost (USD)", fontsize=7.5, labelpad=2)
    ax.set_xlabel("Budget (1 unit = 52,150 USD = one standard site)", fontsize=7.5, labelpad=2)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("bottom", "left"):
        ax.spines[sp].set_color("#888888")
    ax.tick_params(length=2, color="#888888", pad=1.5, labelsize=7)
    ax.grid(axis="y", color="#ececea", lw=0.4, zorder=0)
    chart_report(fig, ax, "fig_budget", 1.0)
    save(fig, "fig_budget")


# ---------------------------------------------------------------------------------------------------------------
# Fig. 5: daily cost split into unserved-order penalty and the rest, in three groups
# ---------------------------------------------------------------------------------------------------------------
def fig_costs():
    # RESULTS_final.md sec. 7 (served shares and cost drivers): V, unserved penalty, served share.
    # Role rows: sec. 3 (D24:S + D45:SC = 758.34; D07:S + D50:C = 1,445.77). Rule / pilot rows: sec. 4.
    groups = [
        ("Best layouts found", [
            ("1 unit: one site (DOT Site 34)", "ours", 1085.87, 568.57, 0.775),
            ("2 units: best pair", "ours", 716.85, 44.29, 0.983),
            ("3 units: best pair, 4 spares each", "ours", 709.98, 37.14, 0.985),
        ]),
        ("Two sites: rules and the DOT pilot", [
            ("Spread rule", "alt", 808.56, 144.29, 0.946),
            ("DOT 2024 pilot pair", "pilot", 851.27, 218.57, 0.916),
            ("Coverage rule", "alt", 858.33, 221.43, 0.914),
        ]),
        ("Two sites: swapping and charging apart", [
            ("Swap-only cabinet + full site", "alt", 758.34, 81.43, 0.969),
            ("Swap-only cabinet + hub", "alt", 1445.77, 1031.43, 0.580),
        ]),
    ]
    dark = {"ours": OURS, "pilot": PILOT, "alt": ALT}
    light = {"ours": OURS_L, "pilot": PILOT_L, "alt": ALT_L}

    # R9 review (2026-10-31): rows 0.95 apart (was 0.78), labels 0.25 above the bar centre with a thin white pad
    # (was 0.23, pad 0.3), groups 0.05 apart (was 0.25), figure 3.15 in high (was 2.95), so that a value label
    # ("717 (98.3 %)", "758 (96.9 %)") no longer runs into the next row's label and no label box cuts a bar.
    # R11 (2026-10-31), readable at a glance: the colour legend is gone (the group titles and row labels name every
    # bar; its dark swatch was the grey of the alternatives), the shade key is one line with neutral swatches, the row
    # names are Table IV's ("4 spares each", "+ full site", "+ hub"), the x title is "Daily cost (USD)" (the caption
    # says the brackets hold the share served), and the figure is 2.95 in high again: the shorter row names end before
    # the value labels above them (``chart_report`` checks it).  Values unchanged.
    step = 0.95
    fig, ax = plt.subplots(figsize=(3.5, 2.95))
    box = dict(fc="white", ec="none", pad=0.1)
    bh = 0.34
    y = 0.0
    for gi, (title, rows) in enumerate(groups):
        if gi:
            y -= 0.05
            ax.axhline(y + 0.45, color="#d8d8d4", lw=0.5, zorder=0)
        ax.text(0, y, title, fontsize=8, fontweight="bold", ha="left", va="center", color=INK)
        y -= 0.92
        for lab, kind, v, pen, srv in rows:
            other = v - pen
            ax.barh(y, other, height=bh, color=light[kind], edgecolor="white", lw=0.6, zorder=2)
            ax.barh(y, pen, left=other, height=bh, color=dark[kind], edgecolor="white", lw=0.6, zorder=2)
            ax.text(0, y + 0.25, lab, fontsize=7.5, ha="left", va="bottom", color=INK, bbox=box, zorder=4)
            ax.text(v + 15, y, f"{v:,.0f} ({srv * 100:.1f} %)", fontsize=7.5, ha="left", va="center",
                    color=INK, zorder=4)
            y -= step
    ax.set_xlim(0, 1750)
    ax.set_ylim(y + step - 0.43, 0.3)          # 0.43 below the last bar, as before
    ax.set_yticks([])
    ax.set_xticks([0, 500, 1000, 1500])
    ax.set_xticklabels(["0", "500", "1,000", "1,500"])
    ax.set_xlabel("Daily cost (USD)", labelpad=2, fontsize=7.5)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#888888")
    ax.tick_params(axis="x", length=2, color="#888888", pad=1.5, labelsize=7.5)
    ax.grid(axis="x", color="#ececea", lw=0.4, zorder=0)

    # shade key, one line: neutral swatches (the hue of a bar says whose layout it is, the shade which cost part); R11
    # fix: the entries say "lighter" and "darker", so the key reads for the blue and red bars too, not only the grey
    h1 = [Patch(fc="#cfcfcf", ec="none"), Patch(fc="#555555", ec="none")]
    ax.legend(h1, ["lighter: other costs", "darker: penalty for unserved orders"], loc="lower center",
              bbox_to_anchor=(0.5, 1.0),
              ncol=2, frameon=False, handlelength=1.2, handletextpad=0.4, columnspacing=1.2, borderaxespad=0.2,
              fontsize=7.5)
    chart_report(fig, ax, "fig_costs", 0.85)
    save(fig, "fig_costs")


def _pdf_size(fig):
    """Width and height (bp) of the PDF that ``save`` writes for ``fig``: an in-memory save with the same options (the
    tight box of the PDF renderer differs from the screen one by a point or two)."""
    import io
    import re
    buf = io.BytesIO()
    fig.savefig(buf, format="pdf", bbox_inches="tight", pad_inches=0.02)
    m = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", buf.getvalue())
    return float(m.group(1)), float(m.group(2))


def chart_report(fig, ax, name, include, clear=1.5):
    """R11 check of a chart before it is saved (fig_budget, fig_costs): its size, the printed scale at an include
    width of ``include`` x \\columnwidth (as in sections/06_results.tex), the smallest text printed, and every label
    problem on the drawn figure in page pt: two labels that overlap, a plotted line or a marker within ``clear`` pt
    of a label (half the line width added), a label over a bar.  Labels: the texts set with ``ax.text`` and the
    legend's; tick labels and axis titles are left to matplotlib.  Prints one line; returns the problems."""
    from matplotlib.text import Text
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    k = 72.0 / fig.dpi

    def box(a):
        e = a.get_window_extent(rend)
        return (e.x0 * k, e.y0 * k, e.x1 * k, e.y1 * k)

    texts = [t for t in ax.texts if t.get_visible() and t.get_text().strip()]
    if ax.get_legend() is not None:
        texts += list(ax.get_legend().get_texts())
    items = [(t.get_text().replace("\n", " "), box(t)) for t in texts]
    lines = []
    for ln in ax.lines:
        xy = ln.get_xydata()
        if ln.get_linestyle() not in ("None", "") and len(xy) >= 2:
            lines.append((ln.get_transform().transform(xy) * k, 0.5 * ln.get_linewidth()))
    marks = []
    for coll in ax.collections:
        offs, sizes = coll.get_offsets(), coll.get_sizes()
        if len(offs) and len(sizes):
            for j, c in enumerate(coll.get_offset_transform().transform(offs) * k):
                marks.append((c, 0.5 * math.sqrt(sizes[j % len(sizes)])))      # s = marker area in pt^2
    bars = [box(p) for p in ax.patches]
    problems = []
    for i, (na, ba) in enumerate(items):
        problems += [f"{na!r} overlaps {nb!r}" for nb, bb in items[i + 1:] if _box_overlap(ba, bb) > 0.05]
        if any(_seg_box_dist(p, q, ba) < clear + hw for P, hw in lines for p, q in zip(P[:-1], P[1:])):
            problems.append(f"a line runs into {na!r}")
        if any(_gap(ba, c) < r + clear for c, r in marks):
            problems.append(f"a marker sits on {na!r}")
        if any(_box_overlap(ba, b) > 0.05 for b in bars):
            problems.append(f"{na!r} cuts a bar")
    small = min(t.get_fontsize() for t in fig.findobj(lambda o: isinstance(o, Text))
                if t.get_visible() and t.get_text().strip())
    w_bp, h_bp = _pdf_size(fig)
    s = include * 252.0 * 72.0 / 72.27 / w_bp                            # \columnwidth = 21 pc = 252 pt
    print(f"{name}: {w_bp:.1f} x {h_bp:.1f} bp; at {include:g}\\columnwidth scale {s:.3f}, printed height "
          f"{h_bp * s:.0f} bp; smallest text {small:g} pt ({small * s:.2f} pt printed); label check: "
          + ("no overlap, no line or marker on a label, no label on a bar" if not problems else "; ".join(problems)))
    return problems


# ---------------------------------------------------------------------------------------------------------------
# Fig. 1 preview: compile the TikZ include in a standalone wrapper
# ---------------------------------------------------------------------------------------------------------------
def fig_framework():
    tex = os.path.join(FIGS, "fig_framework.tex")
    work = os.path.join(HERE, "_build")
    os.makedirs(work, exist_ok=True)
    wrapper = os.path.join(work, "framework_standalone.tex")
    with open(wrapper, "w", encoding="utf-8") as fh:
        fh.write("\\documentclass[10pt]{article}\n\\usepackage{newtxtext,newtxmath}\n\\usepackage{xcolor,tikz}\n"
                 "\\usetikzlibrary{arrows.meta,positioning,fit,calc,backgrounds,shapes.misc}\n"
                 "\\usepackage[active,tightpage]{preview}\\setlength\\PreviewBorder{1pt}\n"
                 "\\begin{document}\\begin{preview}\\begin{minipage}{252pt}\\centering\n"
                 f"\\input{{{tex}}}\n\\end{{minipage}}\\end{{preview}}\\end{{document}}\n")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "framework_standalone.tex"],
                   cwd=work, check=True, stdout=subprocess.DEVNULL)
    shutil.copy(os.path.join(work, "framework_standalone.pdf"), os.path.join(FIGS, "fig_framework.pdf"))
    subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", "-r300",
                    "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4",
                    "-sOutputFile=" + os.path.join(FIGS, "fig_framework.png"), os.path.join(FIGS, "fig_framework.pdf")],
                   check=True)


# ---------------------------------------------------------------------------------------------------------------
# Fig. 4 of the 15-site study (R8): the 15 open sites on the Manhattan map, plus the 15-row companion table
# ---------------------------------------------------------------------------------------------------------------
# Input contract (notes/siting15_design.md section 6.1).  The R8 driver writes both files next to its records;
# the paper build copies them to ``figs/map15/``.
#
# layout.json  (one object)
#   schema          "map15.layout/1"
#   label           str   legend title, e.g. "Best found, 15 sites" (DEMO inputs say so here)
#   demo            bool  true = synthetic numbers; the figure and the table are stamped DEMO
#   run, family, policy, variant, n_bikes, n_orders, n_scenarios   provenance (free, printed in the table note)
#   V, V_ci95       float, [lo, hi]   expected cost per day (USD) of the layout and its stratified 95 % CI
#   served_share    float             share of orders served (p-weighted mean over the scenarios)
#   investment_usd  float             capital of the layout (15 x 52,150 for 15 SC:B3:C2 units)
#   candidates_csv  str (optional)    path of the run's candidates.csv (default: the r7 production file);
#                                     a relative path is read against the project root (ROOT / BSWAP_ROOT)
#   depots          list (optional)   [{"name": str, "lat": float, "lon": float}] rider entry depots
#                                     (default: data_nyc.MANHATTAN_ENTRY_POINTS, six bridges / tunnels)
#   sites           list of 15        {"id": "D23", "role": "SC", "B": 3, "C": 2, "name": optional short name}
#                                     any order; the figure numbers them south -> north by the grid axis
# site_stats.csv   (one row per open site, header exactly these columns; blank = not measured -> "--")
#   id              candidate id, must match layout.sites
#   swaps_mean, swaps_lo, swaps_hi        swaps per evening at the site, p-weighted mean and stratified 95 % CI
#   orders_1km_served                     served orders whose restaurant lies within 1 km (grid distance)
#   orders_1km_total                      all orders with the restaurant within 1 km (served or not)
#   riders_distinct                       distinct riders that swapped at the site per evening (mean)
#   charger_busy_share                    share of 15-min slots with a charger in use (0..1)
#   idle_share                            share of 15-min slots with no swap and no charging (0..1)
#   kwh_bought                            kWh purchased at the site per evening (mean)
#   wait_min_mean                         mean wait before a swap, minutes
#   stockout_slots                        slots with no full battery on the shelf (mean per evening)
#   marginal_usd, marginal_lo, marginal_hi  cost change per day when the site is removed (remove-one pass),
#                                           positive = the site saves money; with its 95 % CI
#   n_scenarios                           scenarios behind the row (12 in the final table)
LAYOUT15_SCHEMA = "map15.layout/1"
SITE_STATS15_COLUMNS = ("id", "swaps_mean", "swaps_lo", "swaps_hi", "orders_1km_served", "orders_1km_total",
                        "riders_distinct", "charger_busy_share", "idle_share", "kwh_bought", "wait_min_mean",
                        "stockout_slots", "marginal_usd", "marginal_lo", "marginal_hi", "n_scenarios")

OSM = os.path.join(ROOT, "data", "raw", "osm_major_roads_manhattan.json")
OSM_COAST = os.path.join(ROOT, "data", "raw", "osm_coastline_manhattan.json")   # New Jersey shore of fig_map15
COAST_BOX = (40.68, 40.83, -74.10, -73.96)              # its Overpass box (lat_min, lat_max, lon_min, lon_max)
DOHMH = os.path.join(ROOT, "data", "raw", "dohmh_restaurants.csv")
MAP15_DIR = os.path.join(FIGS, "map15")                 # real inputs (from the R8 driver; plan B, r8_k15_sp)
RUNS15 = os.path.join(ROOT, "cloud_results", "ebike_swap_sim", "outputs")   # local copies of the R8 run folders
MAP15_DEMO_DIR = os.path.join(FIGS, "map15_demo")       # DEMO inputs (written by demo_map15)
BOX = (40.698, 40.807, -74.020, -73.925)                # data_nyc.MANHATTAN_BOX (lat_min, lat_max, lon_min, lon_max)
ROOSEVELT_LONLAT = (-73.9505, 40.7612)                  # mid Roosevelt Island; the NTA ring that holds it is masked
ACCESS_KM = 14 * 0.150                                  # 14 blocks of 150 m, grid (L1) distance
# data_nyc.MANHATTAN_ENTRY_POINTS, names for the map and the tables
ENTRY_POINTS = (("Queensboro Bridge", 40.7610, -73.9640), ("Williamsburg Bridge", 40.7184, -73.9860),
                ("Manhattan Bridge", 40.7170, -73.9960), ("Brooklyn Bridge", 40.7123, -74.0037),
                ("Lincoln Tunnel", 40.7585, -73.9955), ("Holland Tunnel", 40.7240, -74.0065))
CLASS_MARK = {"shortlist": "s", "pilot": "o", "installed": "p", "citibike_charging": "^", "depot": "h",
              "other": "X", "lattice": "D"}
CLASS_LABEL = {"shortlist": "DOT PEC proposed site", "pilot": "DOT 2024 pilot site", "installed": "installed cabinet",
               "citibike_charging": "Citi Bike charging dock", "depot": "operator depot", "other": "other planned site",
               "lattice": "grid cell, no address"}
CLASS_SHORT = {"shortlist": "PEC", "pilot": "pilot", "installed": "cabinet", "citibike_charging": "dock",
               "depot": "depot", "other": "other", "lattice": "grid"}
# ink area of each marker shape at the same matplotlib size ``s`` (unit box: square 1, circle pi/4, triangle 1/2, ...);
# fig_map15 scales ``s`` by MARK_AREA["o"] / MARK_AREA[shape] so that the ink, not the box, shows the swaps
MARK_AREA = {"o": 0.785, "s": 1.0, "D": 1.0, "p": 0.594, "^": 0.5, "h": 0.650, "X": 0.625}
NTA_SHORT = {"MN17": "Midtown", "MN13": "Chelsea-Flatiron", "MN23": "West Village", "MN24": "SoHo-TriBeCa",
             "MN22": "East Village", "MN27": "Chinatown", "MN25": "Lower Manhattan", "MN19": "East Midtown",
             "MN15": "Clinton", "MN12": "Upper West Side", "MN20": "Murray Hill", "MN40": "Upper East Side",
             "MN28": "Lower East Side", "MN21": "Gramercy", "MN31": "Lenox Hill", "MN32": "Yorkville",
             "MN14": "Lincoln Square", "MN50": "Stuyvesant Town", "MN09": "Morningside Hts", "MN33": "East Harlem S.",
             "MN11": "Central Harlem S.", "MN99": "park / cemetery"}
# Short site names and neighborhoods for the tables, by candidate id of the 59-site file (r7_siting/candidates.csv =
# r8_k15_n64/candidates.csv = r8_k15_sp/candidates.csv, byte-identical, sha256 f489d22e...); the third field is the
# record tag that ends the candidate's label, checked before a name is used, so another candidate file falls back to
# short_site_name and the NTA name.  Areas are the
# common neighborhood names (the NTA polygon of each site was checked; NTA names such as "Clinton" or
# "SoHo-TriBeCa-Civic Center-Little Italy" read less well).
SITE15 = {
    'D01': ('Grid cell', 'Battery Park City', '[M01]'),
    'D02': ('Grid cell', 'Financial District', '[M02]'),
    'D03': ('PEC site, Water St & Gouverneur Ln', 'Financial District', '[D001]'),
    'D04': ('PEC site, Water St & John St', 'Financial District', '[D002]'),
    'D05': ('City Hall Park cabinet', 'Lower Manhattan', '[D004]'),
    'D06': ('PopWheels hub, Dominick St', 'Hudson Square', '[D012]'),
    'D07': ('Grid cell, 6th Ave & Bleecker St', 'Greenwich Village', '[M03]'),
    'D08': ('Two Bridges Tower cabinets', 'Lower East Side', '[D003]'),
    'D09': ('Grid cell, Bowery & Division St', 'Chinatown', '[M04]'),
    'D10': ('Grand St Citi Bike dock', 'Lower East Side', '[D005]'),
    'D11': ('Kenmare St Citi Bike dock', 'Little Italy', '[D007]'),
    'D12': ('Essex Market pilot site', 'Lower East Side', '[D006]'),
    'D13': ('JOCO hub, Bowery', 'Lower East Side', '[D009]'),
    'D14': ('DOT Site 39, 1st Ave & E 1st St', 'East Village', '[D010]'),
    'D15': ('Swobbee site, Charles St (planned)', 'West Village', '[D019]'),
    'D16': ('Whizz store, W 13th St', 'West Village', '[D020]'),
    'D17': ('Grid cell', 'Chelsea', '[M05]'),
    'D18': ('Cooper Square pilot site', 'East Village', '[D014]'),
    'D19': ('DOT Site 38, 1st Ave & E 5th St', 'East Village', '[D013]'),
    'D20': ('Movin store, Avenue B', 'East Village', '[D011]'),
    'D21': ('Avenue D Citi Bike dock', 'East Village', '[D008]'),
    'D22': ('Grid cell', 'East Village', '[M06]'),
    'D23': ('DOT Site 34, 2nd Ave & E 13th St', 'East Village', '[D018]'),
    'D24': ('E 14th St & 1st Ave Citi Bike dock', 'East Village', '[D017]'),
    'D25': ('DOT Site 35, E 14th St & Ave A', 'East Village', '[D016]'),
    'D26': ('E 14th St & Ave B Citi Bike dock', 'East Village', '[D015]'),
    'D27': ('Grid cell', 'Hudson Yards', '[M07]'),
    'D28': ('Swobbee cabinets, 836 6th Ave', 'NoMad', '[D022]'),
    'D29': ('Swobbee cabinets, W 31st St', 'Midtown', '[D023]'),
    'D30': ('Grid cell', 'Midtown', '[M08]'),
    'D31': ('W 35th St Citi Bike dock', 'Hudson Yards', '[D025]'),
    'D32': ('DOT Site 30, 10th Ave & W 38th St', 'Hudson Yards', '[D027]'),
    'D33': ('Zoomo store, W 38th St', 'Garment District', '[D024]'),
    'D34': ('Citi Bike dock, W 42nd St', 'Midtown', '[D026]'),
    'D35': ('DOT Site 29, 9th Ave & W 42nd St', "Hell's Kitchen", '[D029]'),
    'D36': ('DOT Site 23, 10th Ave & W 49th St', "Hell's Kitchen", '[D032]'),
    'D37': ('E 30th St Citi Bike dock', 'Kips Bay', '[D021]'),
    'D38': ('Grid cell, 3rd Ave & E 53rd St', 'Midtown East', '[M09]'),
    'D39': ('PEC site, 3rd Ave & E 54th St', 'Midtown East', '[D028]'),
    'D40': ('DOT Site 22, 9th Ave & W 55th St', "Hell's Kitchen", '[D033]'),
    'D41': ('Grid cell, 8th Ave & W 57th St', 'Midtown', '[M10]'),
    'D42': ('W 59th St Citi Bike dock', 'Lincoln Square', '[D036]'),
    'D43': ('W 66th St Citi Bike dock', 'Lincoln Square', '[D038]'),
    'D44': ('PEC site, 2nd Ave & E 57th St', 'Midtown East', '[D030]'),
    'D45': ('E 62nd St Citi Bike dock', 'Upper East Side', '[D031]'),
    'D46': ('DOT Site 21, 1st Ave & E 73rd St', 'Upper East Side', '[D035]'),
    'D47': ('E 72nd St Citi Bike dock', 'Upper East Side', '[D034]'),
    'D48': ('Grid cell, 2nd Ave & E 76th St', 'Upper East Side', '[M11]'),
    'D49': ('Grid cell, Amsterdam & W 80th St', 'Upper West Side', '[M12]'),
    'D50': ('Citi Bike dock, W 92nd St', 'Upper West Side', '[D043]'),
    'D51': ('De Hostos Houses charging pilot', 'Upper West Side', '[D044]'),
    'D52': ('PEC site, Columbus Ave & W 94th St', 'Upper West Side', '[D042]'),
    'D53': ('DOT Site 20, 2nd Ave & E 79th St', 'Upper East Side', '[D037]'),
    'D54': ('Grid cell', 'Upper East Side', '[M13]'),
    'D55': ('Citi Bike dock, E 95th St', 'Upper East Side', '[D039]'),
    'D56': ('PEC site, 1st Ave & E 99th St', 'East Harlem', '[D040]'),
    'D57': ('PEC site, 1st Ave & E 103rd St', 'East Harlem', '[D041]'),
    'D58': ('DOT Site 16, W 106th St', 'Upper West Side', '[D048]'),
    'D59': ('Grid cell', 'East Harlem', '[M15]'),
}

STREET, STREET_MAJOR, WATER = "#dcdbd6", "#cbcac4", "#ffffff"
# restaurant density: one warm hue, light -> mid (the dark end stays lighter than the blue markers, so the
# markers with their white rings read in greyscale too)
DENS_RAMP = ["#f4f3f0", "#f3e4ca", "#eccb95", "#dea75c", "#c8822f"]


def unrot(x, y):
    e = x * _C - y * _S
    n = x * _S + y * _C
    return LAT0 + n / 110.540, LON0 + e / (111.320 * math.cos(math.radians(LAT0)))


def osm_fetch_streets(path=OSM, timeout=120):
    """Rebuild the cached major-street extract from the Overpass API (only when the cache is missing).
    Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)."""
    import urllib.request
    import urllib.parse
    lat_min, lat_max, lon_min, lon_max = BOX
    q = (f"[out:json][timeout:{timeout}];way[highway~'^(motorway|trunk|primary|secondary|tertiary)$']"
         f"({lat_min},{lon_min},{lat_max},{lon_max});out geom;")
    req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "ebike-swap-siting-figure/0.1 (academic)"})
    with urllib.request.urlopen(req, timeout=timeout + 30) as r:
        j = json.load(r)
    ways = [{"id": w["id"], "highway": w.get("tags", {}).get("highway", ""), "name": w.get("tags", {}).get("name", ""),
             "pts": [[round(p["lat"], 5), round(p["lon"], 5)] for p in w["geometry"]]}
            for w in j["elements"] if w.get("type") == "way" and "geometry" in w]
    out = {"source": "OpenStreetMap via the Overpass API (https://overpass-api.de)",
           "licence": "ODbL 1.0; (c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright",
           "copyright_note": j.get("osm3s", {}).get("copyright", ""),
           "timestamp_osm_base": j.get("osm3s", {}).get("timestamp_osm_base", ""), "generator": j.get("generator", ""),
           "bbox": [lat_min, lon_min, lat_max, lon_max], "query": q,
           "fields": "ways: id, highway (OSM highway tag), name, pts = [[lat, lon], ...] rounded to 1e-5 deg",
           "n_ways": len(ways), "ways": ways}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    return out


def osm_fetch_coast(path=None, timeout=120, response=None):
    """Rebuild the cached coastline extract (OSM ``natural=coastline`` ways around Manhattan, both shores of the
    Hudson; fig_map15 draws the New Jersey shore from it) from the Overpass API, only when the cache is missing
    (``response``: an Overpass answer to the same query already at hand, read instead of asking again).
    Data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)."""
    import urllib.request
    import urllib.parse
    path = path or OSM_COAST
    lat_min, lat_max, lon_min, lon_max = COAST_BOX
    q = (f'[out:json][timeout:{timeout}];way["natural"="coastline"]'
         f'({lat_min},{lon_min},{lat_max},{lon_max});out geom;')
    if response is not None:
        j = response
    else:
        req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                     data=urllib.parse.urlencode({"data": q}).encode(),
                                     headers={"User-Agent": "ebike-swap-siting-figure/0.1 (academic)"})
        with urllib.request.urlopen(req, timeout=timeout + 30) as r:
            j = json.load(r)
    ways = [{"id": w["id"], "ends": [w["nodes"][0], w["nodes"][-1]],
             "pts": [[round(p["lat"], 5), round(p["lon"], 5)] for p in w["geometry"]]}
            for w in j["elements"] if w.get("type") == "way" and "geometry" in w and w.get("nodes")]
    out = {"source": "OpenStreetMap via the Overpass API (https://overpass-api.de)",
           "licence": "ODbL 1.0; (c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright",
           "copyright_note": j.get("osm3s", {}).get("copyright", ""),
           "timestamp_osm_base": j.get("osm3s", {}).get("timestamp_osm_base", ""), "generator": j.get("generator", ""),
           "bbox": [lat_min, lon_min, lat_max, lon_max], "query": q,
           "fields": "ways: id, ends = [first node id, last node id] (to join the ways), pts = [[lat, lon], ...] "
                     "rounded to 1e-5 deg (about 1 m); land lies to the left of each way (OSM coastline rule)",
           "n_ways": len(ways), "ways": ways}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    return out


def osm_streets():
    """Major streets of the cache as ``(highway, [(x, y), ...])`` in the rotated frame."""
    if not os.path.exists(OSM):
        osm_fetch_streets()
    j = json.load(open(OSM, encoding="utf-8"))
    assert "OpenStreetMap" in j.get("licence", ""), "street cache without its ODbL credit"
    return [(w["highway"], [rot(la, lo) for la, lo in w["pts"]]) for w in j["ways"]]


def nta_polygons():
    """Manhattan NTA rings in the study box: ``(code, name, ring_xy, ring_lonlat, roosevelt)``."""
    from matplotlib.path import Path
    lat_min, lat_max, lon_min, lon_max = BOX
    g = json.load(open(NTA, encoding="utf-8"))
    out = []
    for f in g["features"]:
        p = f["properties"]
        if str(p.get("borocode", "")).strip() not in ("1", "1.0"):
            continue
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            ring = poly[0]
            lons = [q[0] for q in ring]
            lats = [q[1] for q in ring]
            if max(lats) < lat_min or min(lats) > lat_max or max(lons) < lon_min or min(lons) > lon_max:
                continue
            clon = sum(lons) / len(lons)
            if clon > -73.935:                                   # Randall's Island
                continue
            r = [rot(q[1], q[0]) for q in ring]
            area = 0.5 * abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r))))
            if area < 0.03:
                continue
            # Roosevelt Island is one ring of MN31: test the ring itself (a centroid box, lon > -73.9585 and
            # 40.748 < lat < 40.778, also caught the Lenox Hill and Yorkville rings)
            roosevelt = Path([(q[0], q[1]) for q in ring]).contains_point(ROOSEVELT_LONLAT)
            out.append((p.get("ntacode") or "", p.get("ntaname") or "", r, [(q[0], q[1]) for q in ring], roosevelt))
    return out


def restaurants_xy():
    """DOHMH restaurants in the study box, rotated frame (km)."""
    xs, ys = [], []
    with open(DOHMH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["r_boro"] != "Manhattan" or not r["r_lat"] or not r["r_lon"]:
                continue
            la, lo = float(r["r_lat"]), float(r["r_lon"])
            if BOX[0] <= la <= BOX[1] and BOX[2] <= lo <= BOX[3]:
                x, y = rot(la, lo)
                xs.append(x)
                ys.append(y)
    import numpy as np
    return np.array(xs), np.array(ys)


def restaurants_latlon():
    """(lat, lon) arrays of every DOHMH restaurant in Manhattan, for the density shading of fig_map15 (the study box
    of ``restaurants_xy`` ends at about 116th Street, within smoothing reach of the map's edge); rows without a
    usable geocode (blank, or lat = lon = 0) are left out."""
    import numpy as np
    la, lo = [], []
    with open(DOHMH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["r_boro"] != "Manhattan" or not r["r_lat"] or not r["r_lon"]:
                continue
            a, b = float(r["r_lat"]), float(r["r_lon"])
            if 40.68 <= a <= 40.89 and -74.03 <= b <= -73.90:
                la.append(a)
                lo.append(b)
    return np.array(la), np.array(lo)


def restaurant_density15(proj, xl, yl, step=0.075, sigma=3.0, pad=1.0):
    """Restaurants per km^2 in ``proj`` coordinates, computed as for the former map (fig_map15_detailed): counts in
    square cells of ``step`` km over the frame grown by ``pad`` km on each side, smoothed by a Gaussian of ``sigma``
    cells.  Returns (x edges, y edges, density[y, x])."""
    import numpy as np
    from scipy.ndimage import gaussian_filter
    la, lo = restaurants_latlon()
    xy = np.array([proj(a, b) for a, b in zip(la, lo)])
    nx = int(math.ceil((xl[1] - xl[0] + 2 * pad) / step))
    ny = int(math.ceil((yl[1] - yl[0] + 2 * pad) / step))
    xe = xl[0] - pad + step * np.arange(nx + 1)
    ye = yl[0] - pad + step * np.arange(ny + 1)
    H, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[xe, ye])
    return xe, ye, (gaussian_filter(H, sigma) / (step * step)).T


def _root_path(path):
    """A relative path in layout.json is read against the project root (``ROOT``, or ``BSWAP_ROOT``)."""
    return path if not path or os.path.isabs(path) else os.path.join(ROOT, path)


def load_candidates15(path=None):
    path = _root_path(path) or os.path.join(RUN, "candidates.csv")
    cands = {r["id"]: dict(r) for r in csv.DictReader(open(path, encoding="utf-8"))}
    for r in cands.values():
        r["x"], r["y"] = rot(float(r["lat"]), float(r["lon"]))
        r["klass"] = "lattice" if r["cls"] == "lattice" else (r["dot_type"] or "other")
        r["dot_programme"] = r["klass"] in ("pilot", "shortlist")
    return cands


def short_site_name(r):
    """Short address of a candidate for the map table (``name`` in layout.json overrides it)."""
    lab = r["label"]
    if r["klass"] == "lattice":
        return f"grid cell {r['lattice_id']}"
    body = lab.split(":", 1)[1] if ":" in lab else lab
    body = body.strip()
    for stop in (" (", ", "):
        if stop in body:
            body = body.split(stop, 1)[0]
    body = body.replace(" at ", " & ").replace(" between ", " betw. ")
    head = lab.split(":", 1)[0]
    tag = ""
    if r["klass"] == "shortlist" and "Site" in head:
        tag = " (PEC " + head.split("Site", 1)[1].split()[0] + ")"
    return (body + tag).strip()


def load_layout15(path):
    lay = json.load(open(path, encoding="utf-8"))
    if lay.get("schema") != LAYOUT15_SCHEMA:
        raise ValueError(f"{path}: schema {lay.get('schema')!r}, expected {LAYOUT15_SCHEMA!r}")
    sites = lay.get("sites") or []
    for s in sites:
        for k in ("id", "role", "B", "C"):
            if k not in s:
                raise ValueError(f"{path}: site {s} lacks {k!r}")
    if len({s["id"] for s in sites}) != len(sites):
        raise ValueError(f"{path}: duplicate site ids")
    return lay


def load_site_stats15(path):
    stats = {}
    with open(path, encoding="utf-8") as fh:
        rd = csv.DictReader(fh)
        unknown = [c for c in (rd.fieldnames or []) if c not in SITE_STATS15_COLUMNS]
        if unknown:
            raise ValueError(f"{path}: unknown columns {unknown}; allowed: {SITE_STATS15_COLUMNS}")
        for r in rd:
            row = {}
            for k, v in r.items():
                if k == "id":
                    continue
                v = (v or "").strip()
                row[k] = None if v in ("", "nan", "None", "--") else float(v)
            stats[r["id"].strip()] = row
    return stats


def site_rows15(lay, cands, rx, ry, polys, depots):
    """The computable columns of the companion tables, one dict per site, numbered south -> north.  ``name``: the
    layout's own short name, else the curated one of ``SITE15``, else ``short_site_name``; ``area``: the curated
    neighborhood of ``SITE15``, else the short NTA name of the polygon that holds the site (``nta``)."""
    import numpy as np
    from matplotlib.path import Path
    paths = [(code, name, Path(ll)) for code, name, _r, ll, roos in polys if not roos]
    rows = []
    for s in lay["sites"]:
        r = cands[s["id"]]
        la, lo = float(r["lat"]), float(r["lon"])
        nta = next(((c, n) for c, n, p in paths if p.contains_point((lo, la))), ("", "?"))
        nta_short = NTA_SHORT.get(nta[0], nta[1].split("-")[0])
        known = SITE15.get(s["id"])
        if known and not r["label"].rstrip().endswith(known[2]):    # another candidate file: the id means another site
            known = None
        d = np.abs(rx - r["x"]) + np.abs(ry - r["y"])
        dep = min(((abs(r["x"] - dx) + abs(r["y"] - dy)), name) for name, dx, dy in depots)
        rows.append({"id": s["id"], "role": s["role"], "B": int(s["B"]), "C": int(s["C"]),
                     "name": s.get("name") or (known[0] if known else short_site_name(r)),
                     "area": known[1] if known else nta_short, "klass": r["klass"],
                     "dot": r["dot_programme"], "nta_code": nta[0], "nta": nta_short,
                     "rest_1km": int((d <= 1.0).sum()), "rest_share": float((d <= 1.0).sum()) / max(len(rx), 1),
                     "n_rest": int(len(rx)), "km_entry": dep[0], "entry": dep[1], "x": r["x"], "y": r["y"]})
    rows.sort(key=lambda q: (q["x"], q["y"]))
    for k, q in enumerate(rows, 1):
        q["no"] = k
    return rows


def _swap_size(sw):
    """Marker area (pt^2) from swaps per evening; None (not measured) = the 4-swap size, drawn hollow."""
    return 12.0 + 5.5 * (4.0 if sw is None else min(max(float(sw), 0.0), 12.0))


def _place_labels(rows, depots, xl, yl, km_per_pt=1.0 / 26.0, others=()):
    """Collision-aware label placement in map units (km).  Site numbers first (8 directions x 3 radii; the
    first radius needs no leader line), then the entry-point names (8 directions x 3 radii).  A candidate position
    is scored by its overlap with the markers (``others`` = the unchosen candidates, at half weight), the rings, the
    frame edge and the labels already placed; a number without a leader line that sits nearly as close to another
    site as to its own costs extra (it would read as that site's number), and so does a name nearly as close to
    another star or site as to its own star; a name nearer another star than its own costs much more (it would name
    the wrong star: in the plan B layout, site 2 lies 0.28 km from the Manhattan Bridge star and pushed that name
    next to the Brooklyn Bridge star); the cheapest wins, nearer positions preferred.  Returns ``(site_labels,
    depot_labels)`` with ``(x, y, leader)`` for the numbers and ``(x, y)`` for the names (both centred)."""
    obstacles = []                                                   # (xmin, xmax, ymin, ymax); sites first
    for q in rows:
        h = 0.26 if q["dot"] else 0.17
        obstacles.append((q["x"] - h, q["x"] + h, q["y"] - h, q["y"] + h))
    for _nm, dx, dy in depots:
        obstacles.append((dx - 0.13, dx + 0.13, dy - 0.13, dy + 0.13))
    minor = [(ox - 0.05, ox + 0.05, oy - 0.05, oy + 0.05) for ox, oy in others]
    placed = []

    def overlap(a, b):
        return max(0.0, min(a[1], b[1]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[2], b[2]))

    def cost(box, radius_rank, minor_w=0.5):
        c = (sum(overlap(box, o) for o in obstacles) + minor_w * sum(overlap(box, o) for o in minor)
             + 2.0 * sum(overlap(box, o) for o in placed))
        if box[0] < xl[0] + 0.1 or box[1] > xl[1] - 0.1 or box[2] < yl[0] + 0.35 or box[3] > yl[1] - 0.1:
            c += 1.0
        return c + 0.012 * radius_rank

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0), (0.71, 0.71), (-0.71, 0.71), (0.71, -0.71), (-0.71, -0.71)]
    order = sorted(range(len(rows)), key=lambda i: -sum(1 for j in range(len(rows)) if j != i and
                                                        abs(rows[i]["x"] - rows[j]["x"]) + abs(rows[i]["y"] - rows[j]["y"]) < 0.8))
    tmp = {}
    for i in order:
        q = rows[i]
        hw, hh = 5.0 * km_per_pt, 4.0 * km_per_pt                   # a bold two-digit 7 pt number
        close = any(abs(q["x"] - rows[j]["x"]) + abs(q["y"] - rows[j]["y"]) < 0.3 for j in range(len(rows)) if j != i)
        best = None
        for rk, r in enumerate((0.37 if not q["dot"] else 0.46, 0.62, 0.85)):
            if close and rk == 0:                                    # a close pair always gets leader lines
                continue
            for dx, dy in dirs:
                cx, cy = q["x"] + r * dx, q["y"] + r * dy
                box = (cx - hw, cx + hw, cy - hh, cy + hh)
                c = cost(box, rk)
                if rk == 0 and any(math.hypot(cx - rows[j]["x"], cy - rows[j]["y"]) < 1.8 * r
                                   for j in range(len(rows)) if j != i):
                    c += 0.03                                        # ambiguous without a leader line
                if rk > 0:                                           # a leader line must not cross another marker
                    for j, o in enumerate(obstacles):
                        if j == i:
                            continue
                        for t in (0.2, 0.35, 0.5, 0.65, 0.8):
                            px, py = q["x"] + t * r * dx, q["y"] + t * r * dy
                            if o[0] <= px <= o[1] and o[2] <= py <= o[3]:
                                c += 0.05
                                break
                if best is None or c < best[0] - 1e-12:
                    best = (c, cx, cy, rk > 0, box)
        placed.append(best[4])
        tmp[i] = (best[1], best[2], best[3])
    site_out = [tmp[i] for i in range(len(rows))]
    def gap(box, px, py):                                            # distance from a point to a label box
        return math.hypot(max(box[0] - px, 0.0, px - box[1]), max(box[2] - py, 0.0, py - box[3]))

    depot_out = []
    for di, (nm, dx, dy) in enumerate(depots):
        hw, hh = 0.5 * len(nm) * 3.3 * km_per_pt, 4.0 * km_per_pt     # 7 pt italic serif, about 3.3 pt per char
        best = None
        for rk, r in enumerate((0.22, 0.42, 0.62)):
            for ddx, ddy in dirs:
                cx, cy = dx + (r + hw) * ddx, dy + (r + hh) * ddy
                box = (cx - hw, cx + hw, cy - hh, cy + hh)
                c = cost(box, rk, minor_w=2.0)                       # candidate dots weigh more under a long name
                own = gap(box, dx, dy)
                near = [(ox, oy) for k, (_o, ox, oy) in enumerate(depots) if k != di] + [(q["x"], q["y"]) for q in rows]
                if any(gap(box, ox, oy) < own + 0.05 for ox, oy in near):
                    c += 0.05                                        # as near another star or site as its own star
                if any(gap(box, ox, oy) < own for ox, oy in near[:len(depots) - 1]):
                    c += 0.3                                         # nearer another star: would name the wrong one
                if best is None or c < best[0] - 1e-12:
                    best = (c, cx, cy, box)
        placed.append(best[3])
        depot_out.append((best[1], best[2]))
    return site_out, depot_out


def _share_pct(s):
    """A share as a short percentage for the legend: '14 %', '2.5 %', '0.04 %', '0 %'."""
    p = 100.0 * float(s)
    if p <= 0.0:
        return "0 %"
    if p < 0.005:
        return "<0.01 %"
    return f"{p:.0f} %" if p >= 9.5 else (f"{p:.1f} %" if p >= 0.95 else f"{p:.2f} %")


def power_clause15(lay, n):
    """Caption clause on the charging power, read from layout.json: ``grid_kw`` = the supply shared by all sites
    ((21), P_grid of the sites group), ``site_kw`` = each site's own connection ((20), P_j).  When ``grid_kw`` is at
    least n x ``site_kw`` (n = open sites, 15 here) the shared limit cannot bind and the clause says each site has its
    own connection; otherwise it says all sites share one supply.  A layout without both fields (plan A's file in
    figs/map15_planA/, the DEMO) gets no clause (fig_map15 warns): the power model is never assumed."""
    g, s = lay.get("grid_kw"), lay.get("site_kw")
    if g is None or s is None:
        return ""
    g, s = float(g), float(s)
    if g >= n * s - 1e-9:
        return f"each site has its own {s:g}~\\textup{{kW}} connection"
    return f"all sites share one {g:g}~\\textup{{kW}} supply"


def fig_map15(layout_json=None, site_stats_csv=None, name="fig_map15", table_name="site_table"):
    """The 15-site map (figure*, 7.16 x 2.12 in) and its companion tables ``figs/<table_name>.tex`` (table*, full
    width) and ``figs/<table_name>_compact.tex`` (table, one column); both tables carry ``\\label{tab:sites15}``."""
    import numpy as np
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.legend_handler import HandlerTuple
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    from scipy.ndimage import gaussian_filter

    layout_json = layout_json or os.path.join(MAP15_DIR, "layout.json")
    site_stats_csv = site_stats_csv or os.path.join(MAP15_DIR, "site_stats.csv")
    lay = load_layout15(layout_json)
    stats = load_site_stats15(site_stats_csv) if os.path.exists(site_stats_csv) else {}
    cands = load_candidates15(lay.get("candidates_csv"))
    missing = [s["id"] for s in lay["sites"] if s["id"] not in cands]
    if missing:
        raise ValueError(f"layout sites not in candidates.csv: {missing}")
    depots = [(d["name"], *rot(float(d["lat"]), float(d["lon"]))) for d in lay["depots"]] if lay.get("depots") \
        else [(nm, *rot(la, lo)) for nm, la, lo in ENTRY_POINTS]
    polys = nta_polygons()
    rings = [r for _c, _n, r, _ll, _roos in polys]
    rx, ry = restaurants_xy()
    streets = osm_streets()
    rows = site_rows15(lay, cands, rx, ry, polys, depots)
    n = len(rows)
    demo = bool(lay.get("demo"))

    x110, _ = rot(40.7997, -73.9582)
    xbat, _ = rot(40.7003, -74.0170)
    xl, yl = (xbat - 0.15, x110 + 0.05), (-3.35, 2.05)
    yv = (-3.30, 1.74)          # shown range: the drawn content only (density grid and label placement keep ``yl``;
                                # the old 2.05 top left a 0.4 in white band above the island)

    fig = plt.figure(figsize=(7.16, 2.12))
    ax = fig.add_axes([0.0, 0.0, 0.70, 1.0])
    lax = fig.add_axes([0.705, 0.0, 0.295, 1.0])     # as tall as the map: the legend at its top, the credit below
    lax.axis("off")
    ax.set_facecolor(WATER)
    clip = PathPatch(Path.make_compound_path(*[Path(r + [r[0]], closed=True) for r in rings]), fc="none", ec="none",
                     transform=ax.transData)
    ax.add_patch(clip)
    for ring in rings:
        ax.add_patch(Polygon(ring, closed=True, fc=LAND, ec=EDGE, lw=0.7, zorder=0))

    # (2) restaurant density: 75 m bins, Gaussian 225 m, per km^2, clipped to land
    step = 0.075
    xe = np.arange(xl[0], xl[1] + step, step)
    ye = np.arange(yl[0], yl[1] + step, step)
    H, _, _ = np.histogram2d(rx, ry, bins=[xe, ye])
    Hs = gaussian_filter(H, 3.0) / (step * step)
    cmap = LinearSegmentedColormap.from_list("dens", DENS_RAMP)
    pm = ax.pcolormesh(xe, ye, Hs.T, cmap=cmap, vmin=0, vmax=np.percentile(Hs, 99.5), shading="flat", zorder=0.4,
                       rasterized=True)
    pm.set_clip_path(clip)

    # (3) OSM major streets, two weights, plus the dashed cross-street guides
    minor = [pts for hw, pts in streets if hw in ("secondary", "tertiary")]
    major = [pts for hw, pts in streets if hw not in ("secondary", "tertiary")]
    for segs, col, lw, z in ((minor, STREET, 0.35, 0.6), (major, STREET_MAJOR, 0.55, 0.65)):
        lc = LineCollection(segs, colors=col, linewidths=lw, zorder=z, capstyle="round")
        lc.set_clip_path(clip)
        ax.add_collection(lc)
        lc.set_clip_box(ax.bbox)    # also clip to the map frame: the land (and so the streets) goes on north of
                                    # 110th St, and without a clip box the PDF drew those streets under the legend
    for sname, la, lo in (("14th St", 40.7359, -73.9934), ("34th St", 40.7484, -73.9857), ("59th St", 40.7644, -73.9737),
                          ("96th St", 40.7851, -73.9576)):
        sx, _ = rot(la, lo)
        ln, = ax.plot([sx, sx], [-4.0, 2.5], color="#9a9994", lw=0.5, ls=(0, (2, 2)), zorder=0.8)
        ln.set_clip_path(clip)
        ax.text(sx, -3.06, sname, fontsize=7, color=INK2, ha="center", va="top", zorder=0.9)

    # (4) land beyond 14 blocks of every open site (hatched); Roosevelt Island is not part of the band
    gx = np.arange(xl[0] - 0.2, xl[1] + 0.2, 0.05)
    gy = np.arange(yl[0] - 0.2, yl[1] + 0.2, 0.05)
    X, Y = np.meshgrid(gx, gy)
    covered = np.zeros(X.shape, dtype=bool)
    for q in rows:
        covered |= (np.abs(X - q["x"]) + np.abs(Y - q["y"])) <= ACCESS_KM
    land = np.zeros(X.shape, dtype=bool)
    pts = np.c_[X.ravel(), Y.ravel()]
    for _c, _n, ring, _ll, roos in polys:
        if not roos:
            land |= Path(ring).contains_points(pts).reshape(X.shape)
    uncovered_share = float(((~covered) & land).sum()) / max(land.sum(), 1)
    if uncovered_share > 0:                                  # (no contour at all when every point is within reach)
        Z = np.where(land, (~covered).astype(float), np.nan)
        plt.rcParams["hatch.linewidth"] = 0.4
        cf = ax.contourf(gx, gy, Z, levels=[0.5, 1.5], colors=["none"], hatches=["////"], zorder=1.4)
        for c in getattr(cf, "collections", [cf]):
            c.set_edgecolor(OURS)
            c.set_linewidth(0)
        ax.contour(gx, gy, Z, levels=[0.5], colors=[OURS], linewidths=0.6, linestyles="--", zorder=1.5)

    # (5) unchosen candidates, rider entry points (stars above the DOT rings, below the site markers)
    chosen = {q["id"] for q in rows}
    others = [c for c in cands if c not in chosen]
    ax.scatter([cands[c]["x"] for c in others], [cands[c]["y"] for c in others], s=5, c=CONTEXT, lw=0, zorder=2)
    halo = [pe.withStroke(linewidth=1.8, foreground="white")]
    # map labels say "Br." so the three bridge names fit at the southern tip; the tables keep the full names
    depots_map = [(nm.replace(" Bridge", " Br."), dx, dy) for nm, dx, dy in depots]
    site_lab, depot_lab = _place_labels(rows, depots_map, xl, yl, others=[(cands[c]["x"], cands[c]["y"]) for c in others])
    for (nm, dx, dy), (lx, ly) in zip(depots_map, depot_lab):
        ax.scatter([dx], [dy], marker="*", s=42, c=INK2, edgecolors="white", linewidths=0.5, zorder=4.6)
        ax.text(lx, ly, nm, fontsize=7, color=INK2, ha="center", va="center", style="italic", path_effects=halo,
                zorder=6.5)

    # (6) the sites: shape = class, ink area = swaps per evening (MARK_AREA evens out the shapes), red ring = DOT
    # programme, number south -> north
    for q, (lx, ly, leader) in zip(rows, site_lab):
        st = stats.get(q["id"], {})
        sw = st.get("swaps_mean")
        size = _swap_size(sw)
        mk = CLASS_MARK[q["klass"]]
        s_mk = size * MARK_AREA["o"] / MARK_AREA[mk]
        if q["dot"]:
            ax.scatter([q["x"]], [q["y"]], marker="o", s=size * 3.4, facecolors="none", edgecolors="white", linewidths=2.0,
                       zorder=4.4)
            ax.scatter([q["x"]], [q["y"]], marker="o", s=size * 3.4, facecolors="none", edgecolors=PILOT, linewidths=0.9,
                       zorder=4.5)
        if sw is None:
            ax.scatter([q["x"]], [q["y"]], marker=mk, s=s_mk, facecolors="white", edgecolors=OURS, linewidths=1.0, zorder=5)
        else:
            ax.scatter([q["x"]], [q["y"]], marker=mk, s=s_mk, c=OURS, edgecolors="white", linewidths=0.9, zorder=5)
        arrow = dict(arrowstyle="-", lw=0.5, color=INK2, shrinkA=4.5, shrinkB=(7 if q["dot"] else 4.5)) if leader else None
        ax.annotate(str(q["no"]), (q["x"], q["y"]), xytext=(lx, ly), textcoords="data", ha="center", va="center",
                    fontsize=7, fontweight="bold", color=INK, path_effects=halo, zorder=7, arrowprops=arrow)

    # (7) north arrow, scale bar, credit, DEMO stamp
    ax0, ay0 = xl[0] + 0.25, 1.0
    ax.annotate("", xy=(ax0 + 0.6 * _S, ay0 + 0.6 * _C), xytext=(ax0, ay0),
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK2, mutation_scale=6))
    ax.text(ax0 + 0.8 * _S, ay0 + 0.8 * _C, "N", fontsize=7, color=INK2, ha="center", va="center")
    ax.plot([xl[0] + 0.25, xl[0] + 1.25], [-2.75, -2.75], color=INK2, lw=0.8)
    ax.text(xl[0] + 0.75, -2.85, "1 km", fontsize=7, color=INK2, ha="center", va="top")
    lax.text(0.0, 0.0, "streets \u00a9 OpenStreetMap contributors (ODbL)", fontsize=7, color=INK2, ha="left",
             va="bottom", transform=lax.transAxes)
    if demo:
        ax.text(0.5 * (xl[0] + xl[1]), yl[1] - 0.05, "DEMO: synthetic site statistics, not a run result",
                fontsize=7.5, color=PILOT, ha="center", va="top", fontweight="bold", zorder=9)
    ax.set_xlim(*xl)
    ax.set_ylim(*yv)
    ax.set_aspect("equal")
    ax.axis("off")

    # legend: classes present with their counts (fixed order), DOT ring, size key, land beyond reach, entry points,
    # other candidates, density; the title carries the layout's cost and served share
    count = {k: sum(1 for q in rows if q["klass"] == k) for k in CLASS_MARK}
    classes = [k for k in CLASS_MARK if count[k]]
    h = [Line2D([], [], marker=CLASS_MARK[k], ls="none", ms=5.5, mfc=OURS, mec="white", mew=0.5) for k in classes]
    lab = [f"{CLASS_LABEL[k]} ({count[k]})" for k in classes]
    h.append(Line2D([], [], marker="o", ls="none", ms=9, mfc="none", mec=PILOT, mew=0.9))
    lab.append(f"DOT pilot or PEC site ({sum(1 for q in rows if q['dot'])} of {n})")
    h.append(tuple(Line2D([], [], marker="o", ls="none", ms=math.sqrt(_swap_size(s)), mfc=OURS, mec="white", mew=0.5)
                   for s in (2, 5, 8)))
    lab.append("marker size: 2 / 5 / 8 swaps per evening")
    h += [Patch(fc="none", ec=OURS, hatch="////", lw=0.6, ls="--"),
          Line2D([], [], marker="*", ls="none", ms=7, mfc=INK2, mec="white", mew=0.4),
          Line2D([], [], marker="o", ls="none", ms=2.4, mfc=CONTEXT, mec="none"),
          Patch(fc=DENS_RAMP[3], ec="none")]
    lab += [f"land beyond 14 blocks of all sites ({_share_pct(uncovered_share)})",
            "rider entry point (bridge or tunnel portal)", f"other candidate site ({len(others)}, not chosen)",
            "restaurant density (darker = more)"]
    title = lay.get("label") or f"{n} sites"
    if lay.get("V") is not None:
        title += f"\n{float(lay['V']):,.0f} USD/day"
        if lay.get("served_share") is not None:
            title += f", {float(lay['served_share']) * 100:.1f} % of orders served"
    title += f"\nnumbered 1\u2013{n} from south to north"
    if demo:
        title = "DEMO — " + title
    lax.legend(h, lab, loc="upper left", bbox_to_anchor=(0.0, 1.0), frameon=False, handlelength=2.2, handletextpad=0.6,
               labelspacing=0.42, borderaxespad=0.0, fontsize=7, title=title, title_fontsize=7.5, alignment="left",
               handler_map={tuple: HandlerTuple(ndivide=None, pad=0.6)})
    save(fig, name)
    site_table15(lay, rows, stats, table_name)
    site_table15_compact(lay, rows, stats, f"{table_name}_compact")
    power = power_clause15(lay, n)
    if not power:
        print(f"warning: {layout_json} has no grid_kw / site_kw; the table captions leave the power model out")
    print(f"{name}: {n} sites, {_share_pct(uncovered_share)} of the land beyond 14 blocks of every site; power: "
          f"{power or 'not given'}; tables figs/{table_name}.tex, figs/{table_name}_compact.tex")
    return rows


def _tex(s):
    """Escape the LaTeX specials that can occur in a site name."""
    for a, b in (("&", "\\&"), ("%", "\\%"), ("#", "\\#"), ("_", "\\_"), ("$", "\\$")):
        s = s.replace(a, b)
    return s


def _num(v, nd=0):
    """A table number: thousands separators, a math minus sign, '--' when not measured."""
    if v is None:
        return "--"
    s = f"{v:,.{nd}f}"
    return "$-$" + s[1:] if s.startswith("-") else s


def _pm(mean, lo, hi, nd=0):
    """'mean +- half-width' of the 95 % CI [lo, hi]; the half-width is left out when it rounds to zero."""
    s = _num(mean, nd)
    if mean is not None and lo is not None and hi is not None and round(0.5 * (hi - lo), nd) > 0:
        s += f"\\,$\\pm$\\,{_num(0.5 * (hi - lo), nd)}"
    return s


def _hdr(*lines, align="c"):
    """A header cell of one or more short lines (a nested tabular, bottom-aligned)."""
    if len(lines) == 1:
        return lines[0]
    return f"\\begin{{tabular}}[b]{{@{{}}{align}@{{}}}}" + "\\\\".join(lines) + "\\end{tabular}"


def _and(items):
    items = [str(i) for i in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _table_head(lay, table_name, rows):
    """Provenance comments of a companion table (not printed)."""
    lines = [f"% {table_name}.tex -- written by figs/src/make_figs.py (fig_map15); do not edit by hand.",
             f"% layout: {lay.get('label', '')}; run {lay.get('run', '?')}, family {lay.get('family', '?')}, policy "
             f"{lay.get('policy', '?')} / {lay.get('variant', '?')}, {lay.get('n_bikes', '?')} riders, "
             f"{lay.get('n_orders', '?')} orders, {lay.get('n_scenarios', '?')} scenarios.",
             "% candidate ids, row 1 to " + str(len(rows)) + ": " + " ".join(q["id"] for q in rows)]
    if lay.get("demo"):
        lines.append("% DEMO: the run columns are synthetic numbers; replace by the driver's site_stats.csv.")
    return lines


def _evenings(lay):
    """Caption sentence on what the run columns average over (from the layout's provenance fields)."""
    ns, nb = lay.get("n_scenarios"), lay.get("n_bikes")
    return f"Means over the {ns} evenings with {nb} riders. " if ns and nb else ""


def _equipment(rows):
    """The common charger count when every site swaps and charges with the same number of chargers (the captions
    then say so), else ``None`` (the tables show role and size per site)."""
    roles = {q["role"] for q in rows}
    chargers = {q["C"] for q in rows}
    if roles != {"SC"} or len(chargers) != 1:
        return None
    return chargers.pop()


def site_table15(lay, rows, stats, table_name="site_table"):
    """``figs/<table_name>.tex``: the full companion table (table*, one row per site, south -> north)."""
    n = len(rows)
    lines = _table_head(lay, table_name, rows)
    equip = _equipment(rows)
    size_col = equip is None                                           # mixed roles / chargers: show role and size
    power = power_clause15(lay, n)                                     # from layout.json grid_kw / site_kw
    cap = (f"The {n} open sites of Fig.~\\ref{{fig:map15}}, numbered from south to north"
           + (f"; each site swaps and charges and has {equip} chargers" if equip else "") + ". " + _evenings(lay)
           + "Restaurants and orders: those within 1~km of the site along the street grid. Entry point: the nearest "
           "of the six entry points (bridges and tunnel portals) where riders start. Chargers busy: share of the evening with a charger in "
           f"use{'; ' + power if power else ''}. Cost rise: increase in the daily cost if only "
           "this site is closed. $\\pm$: half-width of the 95\\pct{} CI.")
    if lay.get("demo"):
        cap = "DEMO (synthetic statistics). " + cap
    head = ["No.", "Site", "Area",
            _hdr("Role,", "spares:chargers") if size_col else _hdr("Spare", "batteries"),
            _hdr("Restaurants", "within 1~km"), _hdr("Nearest entry", "point, km", align="l"),
            _hdr("Swaps per", "evening"), _hdr("Chargers", "busy (\\%)"), _hdr("kWh per", "evening"),
            _hdr("Orders", "served/all"), _hdr("Cost rise", "if removed", "(USD/day)")]
    lines += ["\\begin{table*}[t]", f"  \\caption{{{cap}}}\\label{{tab:sites15}}", "  \\centering\\scriptsize",
              "  \\setlength{\\tabcolsep}{3pt}",
              "  \\begin{tabular}{@{}rll" + ("l" if size_col else "r") + "rlrrrrr@{}}", "    \\toprule",
              "    " + " & ".join(head) + " \\\\", "    \\midrule"]
    for q in rows:
        st = stats.get(q["id"], {})
        busy = st.get("charger_busy_share")
        size = f"{q['role']}, {q['B']}:{q['C']}" if size_col else f"{q['B']}"
        cells = [str(q["no"]), _tex(q["name"]), _tex(q["area"]), size, f"{q['rest_1km']:,}",
                 f"{_tex(q['entry'])}, {q['km_entry']:.1f}",
                 _pm(st.get("swaps_mean"), st.get("swaps_lo"), st.get("swaps_hi"), 1),
                 _num(None if busy is None else 100.0 * busy), _num(st.get("kwh_bought"), 2),
                 f"{_num(st.get('orders_1km_served'))}/{_num(st.get('orders_1km_total'))}",
                 _pm(st.get("marginal_usd"), st.get("marginal_lo"), st.get("marginal_hi"))]
        lines.append("    " + " & ".join(cells) + f" \\\\  % {q['id']}")
    lines += ["    \\bottomrule", "  \\end{tabular}", "\\end{table*}", ""]
    with open(os.path.join(FIGS, f"{table_name}.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


ENTRY_NEAR15_KM = 1.0     # compact site table (R11): a site this near a rider entry point (grid km) is set in bold
NUM_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def _word(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else str(n)


def _entry_claim15(lay, rows, stats):
    """The takeaway of the compact site table (R11), checked before it is written: the sites within
    ``ENTRY_NEAR15_KM`` of a rider entry point, one per entry point, swap the most and cost the most to close (each
    minimum above the other sites' maximum, also on the table's rounded numbers).  Returns (those rows, None) when it
    holds, else (those rows, why not)."""
    n_entry = len(lay["depots"]) if lay.get("depots") else len(ENTRY_POINTS)      # as fig_map15 / fig_map15_plain
    near = [q for q in rows if q["km_entry"] <= ENTRY_NEAR15_KM]
    far = [q for q in rows if q["km_entry"] > ENTRY_NEAR15_KM]
    entries = {q["entry"] for q in near}
    if len(near) != n_entry or len(entries) != n_entry:
        return near, (f"{len(near)} sites within {ENTRY_NEAR15_KM:g} km of {len(entries)} of the {n_entry} entry "
                      "points")
    if not far:
        return near, "no other site to compare with"
    for key, nd, what in (("swaps_mean", 1, "swaps per evening"), ("marginal_usd", 0, "cost rise if closed")):
        a = [stats.get(q["id"], {}).get(key) for q in near]
        b = [stats.get(q["id"], {}).get(key) for q in far]
        if None in a or None in b:
            return near, f"{what} not measured at every site"
        lo, hi = min(a), max(b)
        if not (lo > hi and float(f"{lo:.{nd}f}") > float(f"{hi:.{nd}f}")):
            return near, f"{what}: at least {lo:.{nd}f} near an entry point, at most {hi:.{nd}f} elsewhere"
    return near, None


def site_table15_compact(lay, rows, stats, table_name="site_table_compact"):
    """``figs/<table_name>.tex``: the same sites in one column (table): No., site, area, swaps per evening, cost rise
    if the site alone is closed (USD/day, +- half-width of the 95 % CI).  Spares and chargers go to the note under the
    table (a column only when they are not uniform enough to say in one sentence).
    R11 (2026-10-31), readable at a glance: the caption leads with the takeaway, checked on the numbers first
    (``_entry_claim15``): the sites within 1 km of a rider entry point (No. and Site in bold) swap the most and on
    average cost the most to close (R11 fix: "on average").  If the check fails the caption is neutral, nothing is
    bold and a warning is printed.  The key moves
    to a note under the table; the busy column is gone (the text never cites it and it repeats the swap ranking; the
    full table site_table.tex keeps it)."""
    from collections import Counter
    n = len(rows)
    lines = _table_head(lay, table_name, rows)
    equip = _equipment(rows)
    size_col = equip is None
    if size_col:
        sizes = ""
    else:
        base = Counter(q["B"] for q in rows).most_common(1)[0][0]
        ex = {}
        for q in rows:
            if q["B"] != base:
                ex.setdefault(q["B"], []).append(q["no"])
        sizes = f"Each site swaps and charges, with {equip} chargers and {base} spare batteries"
        if ex:
            sizes += " (" + "; ".join(f"{b} at site{'s' if len(nos) > 1 else ''} {_and(nos)}"
                                      for b, nos in sorted(ex.items(), reverse=True)) + ")"
        sizes += ". "
    # short caption (one column): the takeaway; the power model and the rider count are stated in the text (Section
    # V-A), the full table* caption keeps them
    ns = lay.get("n_scenarios")
    near, why = _entry_claim15(lay, rows, stats)
    bold = set() if why else {q["no"] for q in near}
    cap = f"The {n} open sites of Fig.~\\ref{{fig:map15}}, south to north"
    if why:
        print(f"warning: {table_name}.tex: neutral caption, nothing in bold ({why})")
    else:
        # R11 fix: "on average" (the cost rise of the weakest bold site and of the strongest other one, 628 and 617,
        # have overlapping intervals; the claim holds for the means); no commas around it: the comma's depth in the
        # caption's last line pushed the last text line of page 9's right column to page 10 (underfull column)
        cap += (f" (bold: within {ENTRY_NEAR15_KM:g}~km of an entry point; these swap the most and, on average, cost the most to close)")
    if lay.get("demo"):
        cap = "DEMO (synthetic statistics). " + cap
    note = (sizes + (f"Means over the {ns} planning evenings, weighted as in Section~\\ref{{sec:model:upper}}; " if ns else "")
            + "cost rise if closed = daily cost increase if only this site closes ($\\pm$ 95\\pct{} CI half-width).")
    # three-line headers keep the two number columns as narrow as their numbers (with two lines the table was 2.4 pt
    # wider than the column)
    head = ["No.", "Site", "Area"] + ([_hdr("Role,", "size")] if size_col else []) + \
           [_hdr("Swaps", "per", "evening"), _hdr("Cost rise", "if closed", "(USD/day)")]
    lines += ["\\begin{table}[t]", f"  \\caption{{{cap}}}\\label{{tab:sites15}}", "  \\centering\\scriptsize",
              "  \\setlength{\\tabcolsep}{2pt}",
              "  \\begin{tabular}{@{}rll" + ("l" if size_col else "") + "rr@{}}", "    \\toprule",
              "    " + " & ".join(head) + " \\\\", "    \\midrule"]
    for q in rows:
        st = stats.get(q["id"], {})
        no, name = str(q["no"]), _tex(q["name"])
        if q["no"] in bold:                                              # the numbers stay regular
            no, name = f"\\textbf{{{no}}}", f"\\textbf{{{name}}}"
        cells = [no, name, _tex(q["area"])]
        if size_col:
            cells.append(f"{q['role']}, {q['B']}:{q['C']}")
        cells += [_num(st.get("swaps_mean"), 1),
                  _pm(st.get("marginal_usd"), st.get("marginal_lo"), st.get("marginal_hi"))]
        lines.append("    " + " & ".join(cells) + f" \\\\  % {q['id']}")
    lines += ["    \\bottomrule", "  \\end{tabular}\\par\\smallskip", f"  {{\\raggedright\\scriptsize {note}\\par}}",
              "\\end{table}", ""]
    with open(os.path.join(FIGS, f"{table_name}.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"{table_name}.tex: {n} sites, " + (f"sites {_and(sorted(bold))} in bold" if bold else "none in bold"))


def demo_map15(rule="CSCD", seed=0, out_dir=None, name="fig_map15_demo", table_name="site_table_demo"):
    """DEMO inputs: a ``rule``-15 layout (bilevel.rule_layout, every site SC:B3:C2; CSCD weights = restaurants within
    14 blocks as a stand-in for the scenario demand) and synthetic site statistics, written to ``figs/map15_demo/``
    and rendered as fig_map15_demo / site_table_demo*.tex with the DEMO stamp (never over the real figure)."""
    import random
    import sys
    import numpy as np
    sys.path.insert(0, os.path.join(ROOT, "ebike_swap_sim"))
    from ebike_swap_sim import sites_nyc as SN           # noqa: E402
    from ebike_swap_sim import bilevel as BL             # noqa: E402
    cands = load_candidates15()
    rx, ry = restaurants_xy()
    objs = [SN.Candidate(id=r["id"], label=r["label"], source="dot", lat=float(r["lat"]), lon=float(r["lon"]),
                         node=(int(r["node_x"]), int(r["node_y"])), hub_capable=bool(int(r["hub_capable"] or 0)),
                         lattice_id=r["lattice_id"] or None, dot_type=r["dot_type"] or None, cls=r["cls"])
            for r in cands.values()]
    weights = {r["id"]: float(((np.abs(rx - r["x"]) + np.abs(ry - r["y"])) <= ACCESS_KM).sum()) for r in cands.values()}
    spec = SN.DEFAULT_SPEC
    unit = spec.Fhat + 3 * spec.bhat + 2 * spec.chat                      # one SC:B3:C2 site = 52,150 USD
    lay_obj = BL.rule_layout(rule, objs, 15 * unit, spec, weights=weights, role="SC", base_size=(3, 2), k=15)
    items = SN.layout_items(lay_obj)
    assert len(items) == 15, items
    rng = random.Random(seed)
    sites, stats_rows = [], []
    for cid, role, B, C in items:
        r = cands[cid]
        n1 = float(((np.abs(rx - r["x"]) + np.abs(ry - r["y"])) <= 1.0).sum())
        sw = max(0.6, min(9.0, 0.9 + 6.5 * n1 / 1500.0 + rng.gauss(0, 0.8)))
        half = 0.12 * sw + 0.3
        kwh = sw * 0.55 * (1 + rng.gauss(0, 0.1))
        sites.append({"id": cid, "role": role, "B": int(B), "C": int(C)})
        stats_rows.append({"id": cid, "swaps_mean": round(sw, 2), "swaps_lo": round(sw - half, 2),
                           "swaps_hi": round(sw + half, 2), "orders_1km_served": round(2.3 * sw + rng.gauss(0, 1.5), 1),
                           "orders_1km_total": round(2.9 * sw + 2, 1), "riders_distinct": round(1.4 * sw, 1),
                           "charger_busy_share": round(min(0.95, sw / 7.4 * 0.9), 3),
                           "idle_share": round(max(0.0, 1 - sw / 7.4), 3), "kwh_bought": round(kwh, 2),
                           "wait_min_mean": round(max(0.0, rng.gauss(2.5, 1.0)), 1), "stockout_slots": round(max(0.0, rng.gauss(0.4, 0.4)), 1),
                           "marginal_usd": round(8 * sw + rng.gauss(20, 12), 1), "marginal_lo": None, "marginal_hi": None,
                           "n_scenarios": 12})
    for s in stats_rows:
        s["marginal_lo"] = round(s["marginal_usd"] - 15, 1)
        s["marginal_hi"] = round(s["marginal_usd"] + 15, 1)
    total_sw = sum(s["swaps_mean"] for s in stats_rows)
    lay = {"schema": LAYOUT15_SCHEMA, "label": f"{rule}-15 rule layout", "demo": True, "run": "demo", "family": "manhattan15",
           "policy": "baseline", "variant": "r2", "n_bikes": 48, "n_orders": 240, "n_scenarios": 12,
           "V": 1234.5, "V_ci95": [1180.0, 1289.0], "served_share": 0.93, "investment_usd": 15 * unit,
           "note": f"DEMO: synthetic statistics ({total_sw:.0f} swaps per evening in all); not a run result",
           "sites": sites}
    out_dir = out_dir or MAP15_DEMO_DIR
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "layout.json"), "w", encoding="utf-8") as fh:
        json.dump(lay, fh, indent=1)
    with open(os.path.join(out_dir, "site_stats.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SITE_STATS15_COLUMNS))
        w.writeheader()
        for s in stats_rows:
            w.writerow(s)
    return fig_map15(os.path.join(out_dir, "layout.json"), os.path.join(out_dir, "site_stats.csv"), name=name,
                     table_name=table_name)


def fig_map15_detailed(layout_json=None, site_stats_csv=None):
    """The former 15-site map (restaurant density, unchosen candidates, land beyond reach, entry points, legend) as
    ``fig_map15_detailed``; it writes the same two site tables as ``fig_map15_plain``."""
    return fig_map15(layout_json, site_stats_csv, name="fig_map15_detailed")


# ---------------------------------------------------------------------------------------------------------------
# Fig. 4 of the 15-site study, plain map (2026-10-30): the 15 open sites only, numbered as in tab:sites15, on a base map
# ---------------------------------------------------------------------------------------------------------------
# ``make_figs.py map15`` draws two frames: north-up at column width (fig_map15_northup, 3.5 in wide) and the
# street-grid frame of the former figure at full width (fig_map15_rotated, 7.16 in wide, with a north arrow).  It
# copies MAP15_PREFERRED to fig_map15 and writes the two site tables exactly as fig_map15 does.
# Base map, all vector: land of the five boroughs (NTA polygons of data/raw/nycnhood_acs.geojson; the Manhattan
# polygon MN99 gives the parks: Central Park, Battery Park, Randall's and Governors Islands), the New Jersey shore from
# the cached OSM coastline (``nj_land15``, data/raw/osm_coastline_manhattan.json), the OSM major streets on Manhattan
# only, the East River bridges over the water, the Holland and Lincoln tunnels as dashes over the Hudson.  On
# Manhattan's land, under the parks and streets, a soft orange shading shows the restaurant density (``DENS15``,
# 2026-10-31).  No colour bar and no credit line on the map: the caption says what the shading is, carries the
# OpenStreetMap credit (streets, bridges, tunnels, the New Jersey shore) and credits the other land and the parks to the
# city's 2010 neighborhood tabulation areas via the GeoDa Center (R11, 2026-10-31).
# Text sizes (R11, 2026-10-31): at least 7.1 pt (scale bar, north arrow, bridge, tunnel and park names; 7.08 pt printed
# at the 0.997 include scale of \textwidth), site names and badge numbers 7.5 pt; ``check_overlaps15`` flags any text
# under 7 pt.
# Labels: rivers, park and the three other land areas (``nudge_label15``; in the street-grid frame BROOKLYN stays
# level with QUEENS, ``ALIGN15``), each bridge and tunnel name beside its own line (``place_crossing_label15``), then
# the 15 sites (name next to the badge, or at the end of a leader line where sites are close; ``place_site_labels15``).
# Badges (R11 fix, 2026-10-31): the sites within 1 km of a rider entry point, one per entry point, have a dark blue
# badge (``PLAIN15["site_entry"]``, the dark blue of Fig. 3), the others the blue of our layouts; the caption names
# them ("dark badges").  Colour only: same size and place, so the label placement is unchanged.
# No neighbourhood names: the table's Area column gives them.
# ``check_overlaps15`` and ``check_crossings15`` measure every label on the drawn figure and report any problem.
MAP15_PREFERRED = "rotated"     # the full-width frame: a larger scale, every name sits next to its badge
MAP15_FONT = "Arial Narrow"     # map labels (TrueType, embedded as Type 42); falls back to DejaVu Sans if missing
PLAIN15 = {"water": "#e3e9ef", "land": "#f5f6f8", "boro": "#edf0f3", "park": "#e4e8ec", "park_edge": "#d3d9df",
           "coast": "#c5cdd5", "casing": "#f5f6f8", "road": "#ffffff", "hw_casing": "#dfe3e7", "hw": "#ffffff",
           "tunnel": "#8a95a0", "site": OURS, "site_entry": "#1b4f8f", "ink": "#1c1c1c", "water_ink": "#8696a6",
           "bridge_ink": "#6c7278", "park_ink": "#7b848c", "boro_ink": "#aab1b8", "leader": "#555555",
           "furniture": "#444444", "frame": "#a3a9af"}
# R12e (2026-11-04): one blue-grey family (water, land, boroughs, park) with white streets; badges keep the two blues.
# lightness L* (greyscale): water 82.6 < park 87.5 < other boroughs 91.0 < Manhattan 95.9; badges 50.4
# Restaurant density shading: the computation of the former map (fig_map15_detailed: DOHMH restaurants, ``step`` =
# 75 m cells, Gaussian of ``sigma`` = 3 cells = 225 m, per km^2; every Manhattan restaurant, cells over the frame grown
# by ``pad`` km), shown as one warm hue (``color``) whose opacity rises smoothly with the density: none up to the
# ``lo`` quantile of the density over Manhattan's land in the frame (the quietest third of the island keeps the land
# colour), ``alpha`` from the ``hi`` quantile up, a smoothstep in between (no visible edge where the shading starts).
# Composited on the land it runs from L* 95.9 to #efc4a4 (L* 82, chroma 24), far lighter than the badges (L* 50.4),
# so the badges stay apart from it in greyscale.  The densest blocks are about as light as the rivers (L* 82.6) in
# greyscale; the white streets and the shoreline still mark them as land.  ``alpha`` 0.45 and 0.40 were tried
# (2026-10-31) and not kept: in greyscale the shading stays as grey as the rivers (L* 83.5, 84.8), in colour the
# secondary hot spots (Chinatown, Lower East Side, Greenwich Village) fade.
DENS15 = dict(color="#6f9bd1", alpha=0.38, lo=0.35, hi=0.985, step=0.075, sigma=3.0, pad=1.0)  # R12e: blue tint
BRIDGES15 = ("Brooklyn Bridge", "Williamsburg Bridge", "Ed Koch Queensboro Bridge Upper Level",
             "Ed Koch Queensboro Bridge Lower Level", "Ed Koch Queensboro Bridge Lower Roadway",
             "Queensboro Bridge (Upper Level)", "Queensboro Bridge (Lower Level)", "Roosevelt Island Bridge",
             "Robert F. Kennedy Bridge", "Canal Street", "Canal Street (lower level)", "Flatbush Avenue Extension",
             "Flatbush Avenue Extension (lower level)")   # OSM names the Manhattan Bridge roadways by their streets
TUNNELS15 = ("Holland Tunnel", "Lincoln Tunnel")
# the six crossings the text names: label -> the OSM names of its roadways (BRIDGES15, TUNNELS15)
CROSSINGS15 = {"Brooklyn Bridge": ("Brooklyn Bridge",),
               "Manhattan Bridge": ("Canal Street", "Canal Street (lower level)", "Flatbush Avenue Extension",
                                    "Flatbush Avenue Extension (lower level)"),
               "Williamsburg Bridge": ("Williamsburg Bridge",),
               "Queensboro Bridge": ("Ed Koch Queensboro Bridge Upper Level", "Ed Koch Queensboro Bridge Lower Level",
                                     "Ed Koch Queensboro Bridge Lower Roadway", "Queensboro Bridge (Upper Level)",
                                     "Queensboro Bridge (Lower Level)"),
               "Holland Tunnel": ("Holland Tunnel",), "Lincoln Tunnel": ("Lincoln Tunnel",)}
# frames: projection ("en" = north-up, "rot" = street grid), limits in km, width in inches (height follows); label
# sizes (site names and badge numbers, badge diameter, bridge and tunnel names, pt); map furniture in page pt from
# the bottom-left corner: scale bar (left end of the bar), north arrow (tail; street-grid frame only)
FRAMES15 = {"northup": dict(proj="en", xl=(-3.40, 4.45), yl=(-6.78, 4.95), width=3.5, site_font=7.5, badge=11.5,
                            crossing_font=7.1, scale=(203.0, 22.0), arrow=None),
            "rotated": dict(proj="rot", xl=(-7.55, 5.30), yl=(-3.32, 1.70), width=7.16, site_font=7.5, badge=11.5,
                            crossing_font=7.1, scale=(6.0, 150.0), arrow=(64.0, 146.0))}
# hand nudges of a bridge or tunnel name after ``place_crossing_label15``: (dx, dy) in page pt, per frame.  R11
# (2026-10-31): at 7.1 pt (was 7.0) the Manhattan Bridge name of the street-grid frame is 1 pt longer and came 9.4 pt
# from the Williamsburg Bridge (at least CROSS_CLEAR15 = 10 pt); 1 pt to the left its right end is where it was
# (10.4 pt) and it stays beside the end of its own line (``check_crossings15`` measures the drawn name)
CROSS_NUDGE15 = {"rotated": {"Manhattan Bridge": (-1.0, 0.0)}, "northup": {}}
# geographic labels (orientation only): (text, lat, lon, kind, rotation on the page in degrees).  For a river, the
# park or a land area the anchor is where the search for a clear spot starts; a bridge or tunnel name is set beside
# its own line (the anchor only breaks ties).  kind: park, water, boro (land beyond Manhattan), bridge (bridges and
# tunnels)
PLACES15 = {
    "rotated": [
        ("Central Park", 40.7815, -73.9664, "park", 0),
        ("Hudson River", 40.7437, -74.0152, "water", 0), ("East River", 40.7399, -73.9647, "water", 0),
        ("BROOKLYN", 40.6928, -73.9928, "boro", 0), ("QUEENS", 40.7695, -73.9344, "boro", 0),
        ("NEW JERSEY", 40.7124, -74.0390, "boro", 0),
        ("Brooklyn Bridge", 40.7040, -73.9975, "bridge", 0), ("Manhattan Bridge", 40.7062, -73.9895, "bridge", 0),
        ("Williamsburg Bridge", 40.7135, -73.9725, "bridge", 0), ("Queensboro Bridge", 40.7570, -73.9530, "bridge", 0),
        ("Holland Tunnel", 40.7260, -74.0200, "bridge", 0), ("Lincoln Tunnel", 40.7650, -74.0100, "bridge", 0),
    ],
    "northup": [
        ("Central Park", 40.7815, -73.9671, "park", 61),
        ("Hudson River", 40.7381, -74.0205, "water", 70), ("East River", 40.7399, -73.9636, "water", 68),
        ("BROOKLYN", 40.7019, -73.9547, "boro", 0), ("QUEENS", 40.7453, -73.9428, "boro", 0),
        ("NEW JERSEY", 40.7900, -74.0170, "boro", 62),
        ("Brooklyn Bridge", 40.7040, -73.9975, "bridge", 0), ("Manhattan Bridge", 40.7062, -73.9895, "bridge", 0),
        ("Williamsburg Bridge", 40.7135, -73.9725, "bridge", 0), ("Queensboro Bridge", 40.7570, -73.9530, "bridge", 0),
        ("Holland Tunnel", 40.7260, -74.0200, "bridge", 0), ("Lincoln Tunnel", 40.7650, -74.0100, "bridge", 0),
    ],
}
GEO_STYLE15 = {"water": dict(size=7.4, style="italic", color=PLAIN15["water_ink"], track=0.18, radius=60.0),
               "bridge": dict(size=7.1, style="italic", color=PLAIN15["bridge_ink"], track=0.0, radius=16.0),
               "boro": dict(size=7.4, style="normal", color=PLAIN15["boro_ink"], track=0.35, radius=60.0),
               "park": dict(size=7.1, style="italic", color=PLAIN15["park_ink"], track=0.12, radius=16.0)}
# names kept level with another name of the same kind, per frame: {name: partner}.  The partner is placed first; the
# name then takes its height and the search moves it sideways only (``nudge_label15(dy_fixed=...)``).  Street-grid
# frame: BROOKLYN and QUEENS share one baseline above the bottom edge (2026-10-31, after the credit line left the
# lower-left corner).
ALIGN15 = {"rotated": {"BROOKLYN": "QUEENS"}, "northup": {}}


def en15(lat, lon):
    """(lat, lon) -> (east, north) in km around Times Square: the north-up frame (``rot`` is the street-grid one)."""
    return (lon - LON0) * 111.320 * math.cos(math.radians(LAT0)), (lat - LAT0) * 110.540


def map15_label(name):
    """Short map name of a site-table name: 'Grid cell, Bowery & Division St' -> 'Bowery & Division St',
    'DOT Site 34, 2nd Ave & E 13th St' -> 'DOT Site 34', 'Swobbee cabinets, 836 6th Ave' -> 'Swobbee cabinets';
    Citi Bike docks keep their street, names without a comma stay as they are."""
    if name.startswith("Grid cell, "):
        return name[len("Grid cell, "):]
    if name.startswith("Citi Bike dock") or "," not in name:
        return name
    return name.split(",")[0]


def _rdp(pts, tol):
    """Ramer-Douglas-Peucker simplification of a polyline or closed ring (list of (x, y)); ``tol`` in its units."""
    import numpy as np
    a = np.asarray(pts, dtype=float)
    n = len(a)
    if n < 4:
        return [tuple(p) for p in a]
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        p, sub = a[i], a[i + 1:j]
        vx, vy = a[j] - p
        L = math.hypot(vx, vy)
        d = (np.hypot(sub[:, 0] - p[0], sub[:, 1] - p[1]) if L == 0
             else np.abs(vx * (sub[:, 1] - p[1]) - vy * (sub[:, 0] - p[0])) / L)
        m = int(np.argmax(d))
        if d[m] > tol:
            keep[i + 1 + m] = True
            stack += [(i, i + 1 + m), (i + 1 + m, j)]
    return [tuple(p) for p in a[keep]]


def _rings_path(rings):
    """One compound path from an outer ring and its holes (holes reversed, so the non-zero fill leaves them out)."""
    from matplotlib.path import Path

    def signed(r):
        return 0.5 * sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))
    verts, codes = [], []
    for k, r in enumerate(rings):
        if (signed(r) > 0) != (k == 0):
            r = r[::-1]
        verts += list(r) + [r[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 1) + [Path.CLOSEPOLY]
    return Path(verts, codes)


def nyc_land15(proj, box=(40.64, 40.86, -74.10, -73.84), tol=0.004):
    """Land of the five boroughs near Manhattan as paths in ``proj`` coordinates: ``(manhattan, parks, other)``.
    Parks: the parts of MN99 of 0.05 km^2 or more (Central Park, Battery Park, Randall's and Governors Islands); the
    smaller MN99 parts are piers on the Brooklyn shore and are drawn with the other boroughs.  Rings are simplified
    to ``tol`` km (4 m, a sixth of a point at the wide frame's scale)."""
    g = json.load(open(NTA, encoding="utf-8"))
    man, parks, other = [], [], []
    for f in g["features"]:
        p = f["properties"]
        geom = f["geometry"]
        for poly in ([geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]):
            lons = [q[0] for q in poly[0]]
            lats = [q[1] for q in poly[0]]
            if max(lats) < box[0] or min(lats) > box[1] or max(lons) < box[2] or min(lons) > box[3]:
                continue
            rings = [[proj(q[1], q[0]) for q in r] for r in poly]
            r0 = rings[0]
            area = 0.5 * abs(sum(r0[i][0] * r0[i - 1][1] - r0[i - 1][0] * r0[i][1] for i in range(len(r0))))
            path = _rings_path([_rdp(rg, tol) for rg in rings])
            if p.get("ntacode") == "MN99":
                (parks if area >= 0.05 else other).append(path)
            elif str(p.get("borocode", "")).strip() in ("1", "1.0"):
                man.append(path)
            else:
                other.append(path)
    return man, parks, other


def _join_coast(ways):
    """Join coastline ways ``(first node, last node, pts)`` end to start: the open chains and the closed rings."""
    by_first = {}
    for w in ways:
        by_first.setdefault(w[0], []).append(w)
    lasts = {w[1] for w in ways}
    used, chains, rings = set(), [], []
    heads = [w for w in ways if w[0] not in lasts or w[0] == w[1]]
    for w0 in heads + list(ways):                 # heads first; what is left after them lies on closed loops
        if id(w0) in used:
            continue
        pts, w = [], w0
        while w is not None and id(w) not in used:
            used.add(id(w))
            pts += w[2] if not pts else w[2][1:]
            nxt = [v for v in by_first.get(w[1], []) if id(v) not in used]
            w = nxt[0] if nxt else None
        (rings if len(pts) > 3 and pts[0] == pts[-1] else chains).append(pts)
    return chains, rings


def _clip_polyline(pts, box):
    """The pieces of a polyline inside the box (x0, y0, x1, y1), each from where it enters to where it leaves
    (Liang-Barsky clipping of every segment)."""
    x0, y0, x1, y1 = box
    pieces, cur = [], None
    for p, q in zip(pts[:-1], pts[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        t0, t1, out = 0.0, 1.0, False
        for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
            if pp == 0:
                out = out or qq < 0
            elif pp < 0:
                t0 = max(t0, qq / pp)
            else:
                t1 = min(t1, qq / pp)
        if out or t0 > t1:
            if cur:
                pieces.append(cur)
            cur = None
            continue
        a, b = (p[0] + t0 * dx, p[1] + t0 * dy), (p[0] + t1 * dx, p[1] + t1 * dy)
        if cur is None:
            cur = [a]
        cur.append(b)
        if t1 < 1.0:
            pieces.append(cur)
            cur = None
    if cur:
        pieces.append(cur)
    return pieces


def _perim(pt, box):
    """Position of a point of the box's edge along it, counter-clockwise from the bottom-left corner."""
    x0, y0, x1, y1 = box
    W, H = x1 - x0, y1 - y0
    e = 1e-9 * (W + H)
    x, y = pt
    if abs(y - y0) < e:
        return x - x0
    if abs(x - x1) < e:
        return W + (y - y0)
    if abs(y - y1) < e:
        return W + H + (x1 - x)
    return 2 * W + H + (y1 - y)


def _land_on_box(chains, rings, box):
    """Land polygons inside the box from coastline chains (land on the left of each chain): every piece of a chain in
    the box is closed along the box edge, counter-clockwise, to the next piece (osmcoastline's rule).  Closed rings
    inside the box are kept as they are.  Returns (polygons, open ends): an open end is a chain that stops inside the
    box (a gap in the data), left out."""
    x0, y0, x1, y1 = box
    W, H = x1 - x0, y1 - y0
    P = 2 * (W + H)
    corners = [(0.0, (x0, y0)), (W, (x1, y0)), (W + H, (x1, y1)), (2 * W + H, (x0, y1))]

    def on_edge(pt):
        e = 1e-9 * (W + H)
        return min(abs(pt[0] - x0), abs(pt[0] - x1), abs(pt[1] - y0), abs(pt[1] - y1)) < e

    def inside(pt):
        return x0 < pt[0] < x1 and y0 < pt[1] < y1

    pieces, polys, open_ends = [], [], 0
    for ring in rings:
        if all(inside(p) for p in ring):
            polys.append(list(ring))
            continue
        k = next(i for i, p in enumerate(ring) if not inside(p))         # open the ring outside the box
        chains = list(chains) + [ring[k:] + ring[1:k + 1]]
    for ch in chains:
        for pc in _clip_polyline(ch, box):
            if on_edge(pc[0]) and on_edge(pc[-1]) and len(pc) >= 2:
                pieces.append(pc)
            else:
                open_ends += 1
    used = set()
    for k0 in range(len(pieces)):
        if k0 in used:
            continue
        ring, k = [], k0
        while True:
            used.add(k)
            ring += pieces[k]
            t_out = _perim(pieces[k][-1], box)
            nxt = min(range(len(pieces)), key=lambda j: (_perim(pieces[j][0], box) - t_out) % P)
            d = (_perim(pieces[nxt][0], box) - t_out) % P
            ring += [c for t, c in sorted(corners, key=lambda tc: (tc[0] - t_out) % P) if 0 < (t - t_out) % P < d]
            if nxt == k0 or nxt in used:
                break
            k = nxt
        polys.append(ring)
    return polys, open_ends


def nj_land15(proj, xl, yl, margin=0.3, far_km=0.4):
    """The New Jersey shore (land west of the Hudson) as paths in ``proj`` coordinates, cut to the frame grown by
    ``margin`` km: the coastline ways of the OSM cache (``OSM_COAST``) whose nodes lie, at the median, more than
    ``far_km`` from any vertex of the NYC neighbourhood polygons (the NYC shores come from that file), joined, cut and
    closed along the frame.  Returns (paths, number of open chain ends in the frame, which should be 0)."""
    import numpy as np
    from matplotlib.path import Path
    from scipy.spatial import cKDTree
    if not os.path.exists(OSM_COAST):
        osm_fetch_coast()
    j = json.load(open(OSM_COAST, encoding="utf-8"))
    assert "OpenStreetMap" in j.get("licence", ""), "coastline cache without its ODbL credit"
    g = json.load(open(NTA, encoding="utf-8"))
    nyc = [en15(q[1], q[0]) for f in g["features"]
           for poly in ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon"
                        else f["geometry"]["coordinates"]) for r in poly for q in r]
    tree = cKDTree(np.asarray(nyc))
    ways = []
    for w in j["ways"]:
        d, _ = tree.query(np.asarray([en15(la, lo) for la, lo in w["pts"]]))
        if float(np.median(d)) > far_km:
            ways.append((w["ends"][0], w["ends"][1], [proj(la, lo) for la, lo in w["pts"]]))
    chains, rings = _join_coast(ways)
    box = (xl[0] - margin, yl[0] - margin, xl[1] + margin, yl[1] + margin)
    polys, open_ends = _land_on_box(chains, rings, box)
    paths = []
    for pg in polys:
        pg = _rdp(pg + [pg[0]], 0.004)
        paths.append(Path(pg[:-1] + [pg[0]], [Path.MOVETO] + [Path.LINETO] * (len(pg) - 2) + [Path.CLOSEPOLY]))
    return paths, open_ends


def _class_raster(layers, xl, yl, nx, ny):
    """Rasterise paths (no antialiasing) into an (ny, nx) array of class ids, row 0 at the top; ``layers`` =
    [(class id, paths), ...] drawn in order over class 0 (water)."""
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import PathPatch
    fig = Figure(figsize=(nx / 100.0, ny / 100.0), dpi=100)
    canvas = FigureCanvasAgg(fig)
    fig.patch.set_facecolor((0, 0, 0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.axis("off")
    for val, paths in layers:
        for pth in paths:
            ax.add_patch(PathPatch(pth, fc=(val / 255.0,) * 3, ec="none", antialiased=False))
    canvas.draw()
    return np.asarray(canvas.buffer_rgba())[:ny, :nx, 0].astype(int)


def _halo_text(ax, x, y, s, lw=2.0, **kw):
    """Text with a white halo, drawn as a separate stroke underneath so that the text itself stays real (embedded,
    searchable) text; returns the text artist."""
    z = kw.pop("zorder", 6)
    ax.text(x, y, s, zorder=z - 0.01, path_effects=[pe.Stroke(linewidth=lw, foreground="white")],
            **{**kw, "color": "white"})
    return ax.text(x, y, s, zorder=z, **kw)


def _tracked_text(ax, x, y, s, prop, track=0.15, rotation=0.0, color="k", zorder=6, halo=0.0):
    """Letter-spaced text (``track`` em between characters) centred on the data point (x, y), placed character by
    character (kerning is lost, which spaced capitals do not need); returns the character artists."""
    from matplotlib.textpath import TextToPath
    from matplotlib.transforms import ScaledTranslation
    t2p = TextToPath()
    size = prop.get_size_in_points()
    adv = [t2p.get_text_width_height_descent(c, prop, ismath=False)[0] if c != " " else 0.28 * size for c in s]
    gap = track * size
    a = math.radians(rotation)
    _w, h, d = t2p.get_text_width_height_descent("H", prop, ismath=False)
    out, pos = [], -0.5 * (sum(adv) + gap * (len(s) - 1))
    for c, w in zip(s, adv):
        if c != " ":
            dx = pos * math.cos(a) + 0.5 * (h - d) * math.sin(a)
            dy = pos * math.sin(a) - 0.5 * (h - d) * math.cos(a)
            kw = dict(fontproperties=prop, rotation=rotation, rotation_mode="anchor", ha="left", va="baseline",
                      transform=ax.transData + ScaledTranslation(dx / 72.0, dy / 72.0, ax.figure.dpi_scale_trans))
            if halo:
                ax.text(x, y, c, color="white", zorder=zorder - 0.01,
                        path_effects=[pe.Stroke(linewidth=halo, foreground="white")], **kw)
            out.append(ax.text(x, y, c, color=color, zorder=zorder, **kw))
        pos += w + gap
    return out


def _box_overlap(a, b):
    """Overlap area of two boxes (x0, y0, x1, y1)."""
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _seg_cross(p1, p2, p3, p4):
    """Whether the segments p1p2 and p3p4 cross."""
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (o(p3, p4, p1) > 0) != (o(p3, p4, p2) > 0) and (o(p1, p2, p3) > 0) != (o(p1, p2, p4) > 0)


def _seg_box(p, q, b, pad=0.0):
    """Whether the segment pq meets the box b grown by ``pad`` (25 points along the segment)."""
    for k in range(25):
        t = k / 24.0
        x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
        if b[0] - pad <= x <= b[2] + pad and b[1] - pad <= y <= b[3] + pad:
            return True
    return False


def _seg_point_dist(p, q, c):
    vx, vy = q[0] - p[0], q[1] - p[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((c[0] - p[0]) * vx + (c[1] - p[1]) * vy) / L2))
    return math.hypot(p[0] + t * vx - c[0], p[1] + t * vy - c[1])


def _gap(b, pt):
    """Distance from a point to a box (0 inside)."""
    return math.hypot(max(b[0] - pt[0], 0.0, pt[0] - b[2]), max(b[1] - pt[1], 0.0, pt[1] - b[3]))


def _seg_box_hit(p, q, b):
    """Whether the segment pq meets the box b (exact)."""
    if max(p[0], q[0]) < b[0] or min(p[0], q[0]) > b[2] or max(p[1], q[1]) < b[1] or min(p[1], q[1]) > b[3]:
        return False
    if b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] or b[0] <= q[0] <= b[2] and b[1] <= q[1] <= b[3]:
        return True
    c = ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))
    return any(_seg_cross(p, q, c[k], c[(k + 1) % 4]) for k in range(4))


def _seg_box_dist(p, q, b):
    """Distance from the segment pq to the box b (0 when they meet)."""
    if _seg_box_hit(p, q, b):
        return 0.0
    return min(_gap(b, p), _gap(b, q),
               *(_seg_point_dist(p, q, c) for c in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3]))))


def _segs_box_dist(segs, b, cap=99.0):
    """Distance from a set of segments to the box b (``cap`` when none is nearer)."""
    d = cap
    for p, q in segs:
        if (min(p[0], q[0]) - b[2] > d or b[0] - max(p[0], q[0]) > d or min(p[1], q[1]) - b[3] > d
                or b[1] - max(p[1], q[1]) > d):
            continue
        d = min(d, _seg_box_dist(p, q, b))
    return d


CROSS_NEAR15, CROSS_CLEAR15 = 4.0, 10.0     # a bridge or tunnel name: within 4 pt of its line, 10 pt from any other


def place_crossing_label15(size, own, others, anchor, Wpt, Hpt, ground, hard, soft=(), step=1.5):
    """A box (page pt) for the name of a bridge or tunnel, set beside its own line: boxes of ``size`` (w, h) placed
    1.5 or 3 pt from points of the own line (``own``: segments, every ``step`` pt along them) that lie over water or
    land beyond Manhattan, on eight sides.  Cost: the box farther than CROSS_NEAR15 from its own line or on it, nearer
    than CROSS_CLEAR15 to another crossing (``others``), off the page, on a ``hard`` box (other labels, badges, map
    furniture) or on the same row as one less than 12 pt away (all but forbidden); its share over Manhattan and on the
    ``soft`` boxes (the room next to each badge); the distance to ``anchor`` (ties only).  Returns
    (box, cost, distance to the own line, distance to the nearest other crossing)."""
    w, h = size
    inner = (3.0, 3.0, Wpt - 3.0, Hpt - 3.0)
    seeds = []
    for p, q in own:
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        for k in range(int(L // step) + 1):
            t = k * step / L if L > 0 else 0.0
            s = (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
            if ground.at(s) in (0, 1):
                seeds.append(s)
    best = None
    for sx, sy in seeds:
        for g in (1.5, 3.0):
            for b in ((sx + g, sy - h / 2, sx + g + w, sy + h / 2), (sx - g - w, sy - h / 2, sx - g, sy + h / 2),
                      (sx - w / 2, sy + g, sx + w / 2, sy + g + h), (sx - w / 2, sy - g - h, sx + w / 2, sy - g),
                      (sx + g, sy + g, sx + g + w, sy + g + h), (sx + g, sy - g - h, sx + g + w, sy - g),
                      (sx - g - w, sy + g, sx - g, sy + g + h), (sx - g - w, sy - g - h, sx - g, sy - g)):
                c = 100.0 * (w * h - _box_overlap(b, inner))
                bp = (b[0] - 4.0, b[1] - 1.5, b[2] + 4.0, b[3] + 1.5)
                c += 100.0 * sum(_box_overlap(bp, o) for o in hard) + 1.5 * sum(_box_overlap(bp, o) for o in soft)
                c += 20.0 * sum(1 for o in hard if min(b[3], o[3]) > max(b[1], o[1])
                                and max(o[0] - b[2], b[0] - o[2]) < 12.0)
                if best is not None and c >= best[1]:
                    continue
                d_own = _segs_box_dist(own, b)
                if d_own > CROSS_NEAR15:
                    c += 500.0 + 50.0 * (d_own - CROSS_NEAR15)
                elif d_own < 0.6:
                    c += 300.0
                d_oth = _segs_box_dist(others, b)
                if d_oth < CROSS_CLEAR15:
                    c += 500.0 + 50.0 * (CROSS_CLEAR15 - d_oth)
                sh = ground.shares(b)
                c += 30.0 * (sh[2] + sh[3]) + 0.02 * math.hypot(0.5 * (b[0] + b[2]) - anchor[0],
                                                               0.5 * (b[1] + b[3]) - anchor[1])
                if best is None or c < best[1] - 1e-9:
                    best = (b, c, d_own, d_oth)
    return best


class _Ground15:
    """What lies under a box on the page (pt): the share of each class of the 1-pt raster (0 water, 1 other borough
    or New Jersey, 2 Manhattan, 3 park), from summed-area tables; ``at`` gives the class under one point."""

    def __init__(self, cls_page):
        import numpy as np
        self.cls = cls_page[::-1]                                        # row 0 = page bottom
        self.h, self.w = cls_page.shape
        self.sat = {k: np.pad((self.cls == k).astype(float).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
                    for k in range(4)}

    def at(self, pt):
        x, y = int(math.floor(pt[0])), int(math.floor(pt[1]))
        return int(self.cls[y, x]) if 0 <= x < self.w and 0 <= y < self.h else -1

    def shares(self, b):
        x0, y0 = int(max(0, min(self.w, math.floor(b[0])))), int(max(0, min(self.h, math.floor(b[1]))))
        x1, y1 = int(max(0, min(self.w, math.ceil(b[2])))), int(max(0, min(self.h, math.ceil(b[3]))))
        n = max(1, (x1 - x0) * (y1 - y0))
        return {k: (S[y1, x1] - S[y0, x1] - S[y1, x0] + S[y0, x0]) / n for k, S in self.sat.items()}


def place_site_labels15(P, sizes, Wpt, Hpt, r, ground, obstacles, max_lead=94, lines=(), rows=()):
    """A position for each site name (page pt).  P: badge centres; sizes: (w, h) of each name box; r: badge radius.
    Candidates: next to the badge (right, left, above, below, then the four corners) or at the end of a leader line
    (24 directions x 9 lengths, 17-94 pt; dearer than any free spot next to the badge).  Cost: overlaps with other
    names, badges, ``obstacles`` and the page edge (all but forbidden); leader lines that cross a name, an obstacle,
    a badge or another leader (forbidden); each bridge or tunnel line (``lines``: one list of segments per crossing)
    that the name or its leader crosses (avoided where a free spot exists); a name on the same row as a bridge or
    tunnel name (``rows``) less than 15 pt from it (it would read as one line); the share of the box over Manhattan's
    streets (names prefer water, parks and the other boroughs, the free space); the leader's length; a name less
    than 6 pt nearer its own badge than another badge (it could be read as that site's).  Greedy start, most crowded
    site first, then best-response rounds until nothing moves.  Returns per site (box, leader or None, cost)."""
    n = len(P)
    cands = []
    for i, (px, py) in enumerate(P):
        w, h = sizes[i]
        g = 1.4
        rr = 0.7071 * (r + g)                 # a diagonal box keeps its corner r + g from the badge centre
        c = [((x0, y0, x0 + w, y0 + h), None, pen) for (x0, y0), pen in (
            ((px + r + g, py - h / 2), 0.0), ((px - r - g - w, py - h / 2), 3.0),
            ((px - w / 2, py + r + g), 8.0), ((px - w / 2, py - r - g - h), 8.0),
            ((px + rr, py + rr), 10.0), ((px + rr, py - rr - h), 10.0),
            ((px - rr - w, py + rr), 12.0), ((px - rr - w, py - rr - h), 12.0))]
        for d in (17, 23, 30, 38, 47, 57, 68, 80, 94):
            if d > max_lead:
                continue
            for k in range(24):
                ux, uy = math.cos(2 * math.pi * k / 24), math.sin(2 * math.pi * k / 24)
                qx, qy = px + d * ux, py + d * uy
                if ux >= 0.35:
                    b = (qx + 1.0, qy - h / 2, qx + 1.0 + w, qy + h / 2)
                elif ux <= -0.35:
                    b = (qx - 1.0 - w, qy - h / 2, qx - 1.0, qy + h / 2)
                elif uy > 0:
                    b = (qx - w / 2, qy + 1.0, qx + w / 2, qy + 1.0 + h)
                else:
                    b = (qx - w / 2, qy - 1.0 - h, qx + w / 2, qy - 1.0)
                c.append((b, ((px + (r + 0.6) * ux, py + (r + 0.6) * uy), (qx, qy)), 24.0 + 0.6 * d))
        cands.append(c)
    inner = (2.0, 2.0, Wpt - 2.0, Hpt - 2.0)

    def cost(i, cand, cur):
        b, lead, c = cand
        c += 100.0 * ((b[2] - b[0]) * (b[3] - b[1]) - _box_overlap(b, inner))
        bp = (b[0] - 4.0, b[1] - 1.0, b[2] + 4.0, b[3] + 1.0)   # 4 pt beside other text: two names on one
        for j in range(n):                                        # line would read as one
            c += 400.0 * max(0.0, r + 1.0 - _gap(b, P[j]))         # badges are discs: keep 1 pt clear of each
            if j == i or cur[j] is None:
                continue
            bj, lj, _ = cur[j]
            c += 100.0 * _box_overlap(bp, bj)
            if lj is not None and _seg_box(lj[0], lj[1], b, pad=0.8):
                c += 1000.0
            if lead is not None and (_seg_box(lead[0], lead[1], bj, pad=0.8)
                                     or (lj is not None and _seg_cross(lead[0], lead[1], lj[0], lj[1]))):
                c += 1000.0
        for o in obstacles:
            c += 100.0 * _box_overlap(bp, o)
            if lead is not None and _seg_box(lead[0], lead[1], o, pad=0.5):
                c += 1000.0
        if lead is not None and any(j != i and _seg_point_dist(lead[0], lead[1], P[j]) < r + 1.2 for j in range(n)):
            c += 1000.0
        bl = (b[0] - 0.5, b[1] - 0.5, b[2] + 0.5, b[3] + 0.5)
        for segs in lines:
            if any(_seg_box_hit(p, q, bl) for p, q in segs):
                c += 40.0
            if lead is not None and any(_seg_cross(lead[0], lead[1], p, q) for p, q in segs):
                c += 40.0
        for o in rows:
            if min(b[3], o[3]) > max(b[1], o[1]) and max(o[0] - b[2], b[0] - o[2]) < 15.0:
                c += 200.0
        sh = ground.shares(b)
        c += 26.0 * sh[2] + 6.0 * sh[3] + 4.0 * sh[1]
        own = _gap(b, P[i]) if lead is None else _gap(b, lead[1])
        c += 50.0 * sum(1 for j in range(n) if j != i and _gap(b, P[j]) < own + 6.0)
        return c

    crowd = [sum(1 for j in range(n) if j != i and math.hypot(P[i][0] - P[j][0], P[i][1] - P[j][1]) < 60)
             for i in range(n)]
    order = sorted(range(n), key=lambda i: -crowd[i])
    cur = [None] * n
    for i in order:
        cur[i] = min(cands[i], key=lambda cd: cost(i, cd, cur))
    for _round in range(40):
        moved = 0
        for i in order:
            best = min(cands[i], key=lambda cd: cost(i, cd, cur))
            if cost(i, best, cur) < cost(i, cur[i], cur) - 1e-9:
                cur[i], moved = best, moved + 1
        if not moved:
            break
    return [(cur[i][0], cur[i][1], cost(i, cur[i], cur)) for i in range(n)]


def nudge_label15(box0, kind, Wpt, Hpt, ground, hard, soft=(), segments=(), radius=20.0, step=2.0, dy_fixed=None):
    """Shift a geographic label (its box at the anchor, page pt) to the cheapest spot within ``radius``: on the page,
    off the ``hard`` boxes and the ``segments`` (leader lines), on its own kind of ground (a river on blue water, a
    land area on its land, the park on the park, a bridge or tunnel off Manhattan), clear of the ``soft`` boxes (the
    room next to each badge) and close to the anchor.  With ``dy_fixed`` (pt) the label keeps that vertical shift and
    only sideways shifts within ``radius`` are tried (a name kept level with another, ``ALIGN15``).  Returns (dx, dy,
    cost); a cost of 100 or more means no clean spot."""
    import numpy as np
    allowed = {"water": (0,), "boro": (1,), "park": (3,), "bridge": (0, 1)}[kind]
    wrong = 30.0 if kind == "bridge" else 60.0
    inner = (3.0, 3.0, Wpt - 3.0, Hpt - 3.0)
    best = None
    steps = np.arange(-radius, radius + 1e-9, step)
    for dy in (steps if dy_fixed is None else (dy_fixed,)):
        for dx in steps:
            if dx * dx + (dy * dy if dy_fixed is None else 0.0) > radius * radius + 1e-9:
                continue
            b = (box0[0] + dx, box0[1] + dy, box0[2] + dx, box0[3] + dy)
            c = 100.0 * ((b[2] - b[0]) * (b[3] - b[1]) - _box_overlap(b, inner))
            bp = (b[0] - 4.0, b[1] - 1.5, b[2] + 4.0, b[3] + 1.5)
            c += 100.0 * sum(_box_overlap(bp, o) for o in hard) + 1.5 * sum(_box_overlap(bp, o) for o in soft)
            c += 20.0 * sum(1 for o in hard if min(b[3], o[3]) > max(b[1], o[1])          # on the same line as
                            and max(o[0] - b[2], b[0] - o[2]) < 12.0)                   # other text, 12 pt away
            c += 1000.0 * sum(1 for p, q in segments if _seg_box(p, q, b, pad=1.0))
            sh = ground.shares(b)
            c += wrong * (1.0 - sum(sh[k] for k in allowed)) + 0.5 * math.hypot(dx, dy)
            if best is None or c < best[2] - 1e-9:
                best = (dx, dy, c)
    return best


def _scale_bar15(ax, x0, y0, s_pt, font, km=1.0, zorder=7):
    """A two-part scale bar of ``km`` with its left end at the data point (x0, y0); returns the artists."""
    from matplotlib.patches import Rectangle
    h, col = 2.2 / s_pt, PLAIN15["furniture"]
    arts = [ax.add_patch(Rectangle((x0, y0), 0.5 * km, h, fc=col, ec=col, lw=0.5, zorder=zorder)),
            ax.add_patch(Rectangle((x0 + 0.5 * km, y0), 0.5 * km, h, fc="white", ec=col, lw=0.5, zorder=zorder))]
    for v, s in ((0.0, "0"), (0.5 * km, f"{0.5 * km:g}"), (km, f"{km:g} km")):
        arts.append(_halo_text(ax, x0 + v, y0 - 1.6 / s_pt, s, lw=1.6, fontproperties=font, color=col, ha="center",
                               va="top", zorder=zorder))
    return arts


def _north_arrow15(ax, x0, y0, s_pt, angle_deg, font, length=18.0, zorder=7):
    """North arrow from the data point (x0, y0), pointing ``angle_deg`` from the page's x axis; returns the artists."""
    a = math.radians(angle_deg)
    x1, y1 = x0 + length / s_pt * math.cos(a), y0 + length / s_pt * math.sin(a)
    col = PLAIN15["furniture"]
    return [ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=zorder,
                        arrowprops=dict(arrowstyle="-|>,head_length=0.5,head_width=0.22", lw=0.8, color=col,
                                        shrinkA=0, shrinkB=0)),
            ax.text(x1 + 4.5 / s_pt * math.cos(a), y1 + 4.5 / s_pt * math.sin(a), "N", fontproperties=font,
                    color=col, ha="center", va="center", zorder=zorder)]


MIN_TEXT15 = 7.0     # pt on the figure; R11 (2026-10-31): was 6.5 (the scale bar printed at 6.58 pt)


def check_overlaps15(fig, names, badges, r, leaders, geo, furniture):
    """Measure the drawn labels (page pt) and list every problem: two labels that overlap, a label on a badge, a leader
    line through a label other than its own, a label off the page, a text under ``MIN_TEXT15`` = 7 pt.  ``names``:
    site name artists; ``badges``: badge centres; ``leaders``: (site index, segment); ``geo``: (text, artists),
    measured character by character for spaced labels (a slanted label's box would be mostly empty); ``furniture``:
    artists of the scale bar and north arrow (not checked against each other)."""
    renderer = fig.canvas.get_renderer()
    k = 72.0 / fig.dpi
    Wpt, Hpt = fig.get_figwidth() * 72.0, fig.get_figheight() * 72.0

    def box(a):
        e = a.get_window_extent(renderer)
        return (e.x0 * k, e.y0 * k, e.x1 * k, e.y1 * k)

    items = [(f"site {i + 1} name", box(t), ("site", i)) for i, t in enumerate(names)]   # (name, box, owner)
    items += [(f"label {txt!r}".replace("\\n", " "), box(a), ("geo", g)) for g, (txt, arts) in enumerate(geo)
              for a in arts]
    items += [("map furniture", box(a), ("furniture", 0)) for a in furniture]
    problems = []
    for a in range(len(items)):
        na, ba, oa = items[a]
        if ba[0] < 0 or ba[1] < 0 or ba[2] > Wpt or ba[3] > Hpt:
            problems.append(f"{na} leaves the page")
        for b in range(a + 1, len(items)):
            nb, bb, ob = items[b]
            if oa != ob and _box_overlap(ba, bb) > 0.05:
                problems.append(f"{na} overlaps {nb}")
        for j, c in enumerate(badges):
            if _gap(ba, c) < r - 0.05:
                problems.append(f"{na} covers badge {j + 1}")
        for i, (p, q) in leaders:
            if oa != ("site", i) and _seg_box(p, q, ba):
                problems.append(f"leader of site {i + 1} crosses {na}")
    for t in fig.findobj(lambda o: hasattr(o, "get_fontsize") and hasattr(o, "get_text")):
        if t.get_text().strip() and t.get_fontsize() < MIN_TEXT15:
            problems.append(f"text {t.get_text()!r} is {t.get_fontsize():.2f} pt")
    return sorted(set(problems), key=problems.index)


def check_crossings15(fig, crossing, cross, others_of):
    """Measure each drawn bridge or tunnel name (page pt): its distance to its own line and to the nearest other
    crossing.  ``crossing``: (text, artists); ``cross``: text -> own segments; ``others_of``: text -> the other
    crossings' segments.  Returns (problems, one line per name)."""
    renderer = fig.canvas.get_renderer()
    k = 72.0 / fig.dpi
    problems, lines = [], []
    for text, arts in crossing:
        e = [a.get_window_extent(renderer) for a in arts]
        b = (min(q.x0 for q in e) * k, min(q.y0 for q in e) * k, max(q.x1 for q in e) * k, max(q.y1 for q in e) * k)
        d_own, d_oth = _segs_box_dist(cross[text], b), _segs_box_dist(others_of[text], b)
        lines.append(f"{text}: {d_own:.1f} pt from its line, {d_oth:.1f} pt from the nearest other crossing")
        if d_own > CROSS_NEAR15 + 0.05:
            problems.append(f"{text} is {d_own:.1f} pt from its own line (at most {CROSS_NEAR15:g})")
        if d_oth < CROSS_CLEAR15 - 0.05:
            problems.append(f"{text} is {d_oth:.1f} pt from another crossing (at least {CROSS_CLEAR15:g})")
    return problems, lines


def fig_map15_plain_variant(rows, variant, name=None, demo=False, dark=()):
    """Draw one frame of the plain 15-site map (``variant`` in FRAMES15) to ``figs/<name>.{pdf,png}``; ``rows`` from
    site_rows15 (numbered south -> north as in the site table); ``dark``: the site numbers drawn with a dark badge
    (``entry_badges15``; R11 fix).  Returns (width, height in inches, problems found, notes: where each bridge and
    tunnel name sits, which site names touch a bridge or tunnel line)."""
    import numpy as np
    from matplotlib import font_manager
    from matplotlib.collections import LineCollection
    from matplotlib.colors import ListedColormap, to_rgb
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import PathPatch, Rectangle
    from matplotlib.path import Path
    from matplotlib.transforms import Bbox

    fr = FRAMES15[variant]
    proj = en15 if fr["proj"] == "en" else rot
    xl, yl, W = fr["xl"], fr["yl"], fr["width"]
    H = W * (yl[1] - yl[0]) / (xl[1] - xl[0])
    s_pt = W * 72.0 / (xl[1] - xl[0])                   # pt per km
    Wpt, Hpt = W * 72.0, H * 72.0
    try:
        font_manager.findfont(FontProperties(family=MAP15_FONT), fallback_to_default=False)
        family = MAP15_FONT
    except ValueError:
        family = "DejaVu Sans"
        print(f"warning: font {MAP15_FONT!r} not found; the map labels use {family}")
    man, parks, other = nyc_land15(proj)
    nj, open_ends = nj_land15(proj, xl, yl)
    j = json.load(open(OSM, encoding="utf-8"))
    assert "OpenStreetMap" in j.get("licence", ""), "street cache without its ODbL credit"
    ways = [(w["highway"], w["name"], [proj(la, lo) for la, lo in w["pts"]]) for w in j["ways"]]

    def to_pt(x, y):
        return (x - xl[0]) * s_pt, (y - yl[0]) * s_pt

    def to_km(X, Y):
        return xl[0] + X / s_pt, yl[0] + Y / s_pt

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((xl[0], yl[0]), xl[1] - xl[0], yl[1] - yl[0], fc=PLAIN15["water"], ec="none", zorder=0))

    # (1) class raster, one cell per pt, over the frame padded by 2 km (the street filter looks just past the frame)
    cell = 1.0 / s_pt
    npad, nx, ny = int(round(2.0 / cell)), int(round(Wpt)), int(round(Hpt))
    cls = _class_raster([(1, other + nj), (2, man), (3, parks)], (xl[0] - npad * cell, xl[0] + (nx + npad) * cell),
                        (yl[0] - npad * cell, yl[0] + (ny + npad) * cell), nx + 2 * npad, ny + 2 * npad)
    ground = _Ground15(cls[npad:npad + ny, npad:npad + nx].copy())

    # only what reaches into the frame is drawn (the PDF keeps what a clip path hides): land polygons within 0.5 km,
    # streets with a point on Manhattan's land inside the frame (none of New Jersey, Brooklyn or Queens), simplified
    # to 4 m like the land
    fb = Bbox([[xl[0] - 0.5, yl[0] - 0.5], [xl[1] + 0.5, yl[1] + 0.5]])
    man, parks, other = ([p for p in ps if p.get_extents().overlaps(fb)] for ps in (man, parks, other))

    def on_manhattan(x, y):                     # raster row 0 is its top edge, yl[0] + (ny + npad) cells
        if not (xl[0] - 0.2 <= x <= xl[1] + 0.2 and yl[0] - 0.2 <= y <= yl[1] + 0.2):
            return False
        return cls[int((yl[0] + (ny + npad) * cell - y) / cell), int((x - xl[0]) / cell) + npad] in (2, 3)

    ways = [(hw, nm, _rdp(pts, 0.004)) for hw, nm, pts in ways
            if (nm in BRIDGES15 or nm in TUNNELS15) and any(fb.contains(x, y) for x, y in pts)
            or any(on_manhattan(x, y) for x, y in pts)]

    # (2) land: the coast stroke under the fills (only its outer half shows), the fills with a seam-hiding edge
    for pth in other + nj + man + parks:
        ax.add_patch(PathPatch(pth, fc=PLAIN15["coast"], ec=PLAIN15["coast"], lw=0.6, zorder=1))
    for paths, fc, ec, lw, z in ((other + nj, PLAIN15["boro"], PLAIN15["boro"], 0.35, 1.1),
                                 (man, PLAIN15["land"], PLAIN15["land"], 0.35, 1.2),
                                 (parks, PLAIN15["park"], PLAIN15["park_edge"], 0.3, 1.3)):
        for pth in paths:
            ax.add_patch(PathPatch(pth, fc=fc, ec=ec, lw=lw, zorder=z))

    # (2b) restaurant density (DENS15) over Manhattan's land fill, under the parks and streets.  Clip: the
    # neighbourhood rings unsimplified (their shared edges coincide; the 4 m simplified rings leave hairline gaps that
    # would show as light lines through the shading), without Roosevelt Island (it would only catch the smoothing
    # tail of the Upper East Side across the river).  The 75 m cells are resampled bicubically at the output
    # resolution, so the shading has no steps; the colour map holds one colour and the opacity ramp, so the PDF
    # stores a one-colour image and its soft mask.
    roos = proj(ROOSEVELT_LONLAT[1], ROOSEVELT_LONLAT[0])
    man_exact = [p for p in nyc_land15(proj, tol=0.0)[0] if p.get_extents().overlaps(fb) and not p.contains_point(roos)]
    dclip = PathPatch(Path.make_compound_path(*man_exact), fc="none", ec="none", transform=ax.transData)
    ax.add_patch(dclip)
    xe, ye, dens = restaurant_density15(proj, xl, yl, DENS15["step"], DENS15["sigma"], DENS15["pad"])
    XC, YC = np.meshgrid(0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:]))
    cells = np.c_[XC.ravel(), YC.ravel()]
    on_land = (cells[:, 0] > xl[0]) & (cells[:, 0] < xl[1]) & (cells[:, 1] > yl[0]) & (cells[:, 1] < yl[1])
    on_land &= np.any([p.contains_points(cells) for p in man_exact], axis=0)
    d_lo, d_hi = np.quantile(dens.ravel()[on_land], [DENS15["lo"], DENS15["hi"]])
    lut = np.linspace(0.0, 1.0, 256)
    shade = ListedColormap(np.c_[np.tile(to_rgb(DENS15["color"]), (256, 1)),
                                 DENS15["alpha"] * lut * lut * (3.0 - 2.0 * lut)])
    im = ax.imshow(dens, extent=(xe[0], xe[-1], ye[0], ye[-1]), origin="lower", cmap=shade, vmin=d_lo, vmax=d_hi,
                   interpolation="bicubic", interpolation_stage="data", zorder=1.25)
    im.set_clip_path(dclip)
    ax.set_xlim(*xl)                            # imshow may reset the limits and the aspect
    ax.set_ylim(*yl)
    ax.set_aspect("equal")

    # (3) streets on Manhattan only (clipped to its land), bridges over the water, tunnels as dashes over the water
    # (drawn under the land, so they show where they pass under the river)
    clip = PathPatch(Path.make_compound_path(*man, *parks), fc="none", ec="none", transform=ax.transData)
    ax.add_patch(clip)
    land = man + parks + other

    def over_water(p0, p1):
        return any(not any(lp.contains_point((p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]))) for lp in land)
                   for t in (0.2, 0.35, 0.5, 0.65, 0.8))

    bridges, tunnels, tunnel_lines = {}, {}, []           # OSM name -> segments (km); tunnel polylines
    for hw, nm, pts in ways:
        if nm in BRIDGES15:
            bridges.setdefault(nm, []).extend((p0, p1) for p0, p1 in zip(pts[:-1], pts[1:])
                                              if not nm.startswith(("Canal", "Flatbush")) or over_water(p0, p1))
        elif nm in TUNNELS15:
            tunnels.setdefault(nm, []).extend(zip(pts[:-1], pts[1:]))
            tunnel_lines.append(pts)
    kw = s_pt / 39.6                                    # line widths follow the scale (39.6 pt/km in the wide frame)

    def of_class(*tags):
        return [p for hw, nm, p in ways if hw in tags]
    layers = [(of_class("secondary", "tertiary"), PLAIN15["casing"], 0.85, PLAIN15["road"], 0.45),
              (of_class("primary"), PLAIN15["casing"], 1.15, PLAIN15["road"], 0.70),
              (of_class("motorway", "trunk"), PLAIN15["hw_casing"], 1.55, PLAIN15["hw"], 1.0)]   # casing, fill (pt)
    for li, (segs, cc, cw, fc, fw) in enumerate(layers):         # all casings first, then all fills
        lc = LineCollection(segs, colors=cc, linewidths=cw * kw, zorder=2.0 + 0.01 * li, capstyle="round",
                            joinstyle="round")
        lc.set_clip_path(clip)
        ax.add_collection(lc)
    for li, (segs, cc, cw, fc, fw) in enumerate(layers):
        lc = LineCollection(segs, colors=fc, linewidths=fw * kw, zorder=2.05 + 0.01 * li, capstyle="round",
                            joinstyle="round")
        lc.set_clip_path(clip)
        ax.add_collection(lc)
    bridge_segs = [s for v in bridges.values() for s in v]
    ax.add_collection(LineCollection(bridge_segs, colors=PLAIN15["hw_casing"], linewidths=1.55 * kw, zorder=2.2,
                                     capstyle="butt"))
    ax.add_collection(LineCollection(bridge_segs, colors=PLAIN15["hw"], linewidths=1.0 * kw, zorder=2.21,
                                     capstyle="butt"))
    ax.add_collection(LineCollection(tunnel_lines, colors=PLAIN15["tunnel"], linewidths=0.8,
                                     linestyles=(0, (2.0, 1.4)), zorder=0.5))

    # the crossings on the page (pt), as the reader sees them: a bridge everywhere, a tunnel over the water only
    def seg_pt(s):
        return to_pt(*s[0]), to_pt(*s[1])

    def over_water_pt(s):
        return ground.at((0.5 * (s[0][0] + s[1][0]), 0.5 * (s[0][1] + s[1][1]))) == 0

    cross = {}
    for label, osm_names in CROSSINGS15.items():
        cross[label] = [s for nm in osm_names for s in map(seg_pt, bridges.get(nm, []))]
        cross[label] += [s for nm in osm_names for s in map(seg_pt, tunnels.get(nm, [])) if over_water_pt(s)]
    labelled = {nm for v in CROSSINGS15.values() for nm in v}
    unlabelled = {nm: [seg_pt(s) for s in v] for nm, v in bridges.items() if nm not in labelled}
    others_of = {t: [s for k, v in cross.items() if k != t for s in v] + [s for v in unlabelled.values() for s in v]
                 for t in cross}

    # (4) text measurement on the page (pt)
    site_font, badge = fr["site_font"], fr["badge"]
    font = FontProperties(family=family, size=site_font)
    fontb = FontProperties(family=family, size=site_font, weight="bold")
    font_small = FontProperties(family=family, size=7.1)       # scale bar, "N"; R11: was 6.6 (6.58 pt printed)
    renderer = fig.canvas.get_renderer()
    k_pt = 72.0 / fig.dpi

    def extent(arts):
        e = [t.get_window_extent(renderer) for t in arts]
        return (min(b.x0 for b in e) * k_pt, min(b.y0 for b in e) * k_pt, max(b.x1 for b in e) * k_pt,
                max(b.y1 for b in e) * k_pt)

    P = [to_pt(*proj(*unrot(q["x"], q["y"]))) for q in rows]      # badge centres (rows hold the grid frame)
    r = 0.5 * badge + 0.45
    badge_boxes = [(x - r, y - r, x + r, y + r) for x, y in P]
    badge_room = [(x - r - 9, y - r - 3, x + r + 9, y + r + 3) for x, y in P]

    # (5) map furniture on open water or plain land: scale bar, north arrow (street-grid frame only); no credit line
    # (the caption carries the OpenStreetMap credit and credits the land and parks to the city's 2010 neighborhood
    # tabulation areas via the GeoDa Center)
    furn = _scale_bar15(ax, *to_km(*fr["scale"]), s_pt, font_small)
    if fr["proj"] == "rot" and fr.get("arrow"):
        furn += _north_arrow15(ax, *to_km(*fr["arrow"]), s_pt, GRID_DEG, font_small, length=18.0)
    if demo:
        furn.append(ax.text(*to_km(0.5 * Wpt, 6.0), "DEMO: synthetic site statistics, not a run result",
                            fontproperties=fontb, color=PILOT, ha="center", va="bottom", zorder=9))
    fig.canvas.draw()
    furn = [a for a in furn if hasattr(a, "get_window_extent")]
    furn_boxes = [extent([a]) for a in furn]

    # (6) geographic labels: each bridge and tunnel name beside its own line, then rivers, park and land areas
    def draw_geo(text, x, y, kind, rotn):
        st = GEO_STYLE15[kind]
        size = fr["crossing_font"] if kind == "bridge" else st["size"]
        prop = FontProperties(family=family, size=size, style=st["style"])
        lines = text.split("\n")
        halo = 1.6 if kind == "bridge" else 0.0
        arts = []
        for li, line in enumerate(lines):
            yy = y + (0.5 * (len(lines) - 1) - li) * size * 1.08 / s_pt
            if st["track"] > 0:
                arts += _tracked_text(ax, x, yy, line, prop, track=st["track"], rotation=rotn, color=st["color"],
                                      halo=halo)
            else:
                kwt = dict(fontproperties=prop, color=st["color"], rotation=rotn, ha="center", va="center",
                           rotation_mode="anchor", zorder=6)
                arts.append(_halo_text(ax, x, yy, line, lw=halo, **kwt) if halo else ax.text(x, yy, line, **kwt))
        return arts

    geo, crossing, notes = [], [], []

    def geo_boxes():                            # one box per character of a spaced label: a slanted label (the
        return [extent([t]) for g in geo for t in g[1]]   # rivers and the park in the north-up frame) stays thin

    def measure(text, kind, rotn):
        n0 = len(ax.texts)
        b0 = extent(draw_geo(text, *to_km(0.5 * Wpt, 0.5 * Hpt), kind, rotn))
        for t in ax.texts[n0:]:
            t.remove()
        return b0

    for text, la, lo, kind, rotn in PLACES15[variant]:
        if kind != "bridge":
            continue
        b0 = measure(text, kind, rotn)
        res = place_crossing_label15((b0[2] - b0[0], b0[3] - b0[1]), cross[text], others_of[text],
                                     to_pt(*proj(la, lo)), Wpt, Hpt, ground, badge_boxes + furn_boxes + geo_boxes(),
                                     badge_room)
        if res is None:
            notes.append(f"left out {text!r} (its line is not on the page)")
            continue
        dx, dy = CROSS_NUDGE15.get(variant, {}).get(text, (0.0, 0.0))      # hand nudge (page pt), usually none
        b = (res[0][0] + dx, res[0][1] + dy, res[0][2] + dx, res[0][3] + dy)
        arts = draw_geo(text, *to_km(0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3])), kind, rotn)
        geo.append((text, arts))
        crossing.append((text, arts))
    align = ALIGN15.get(variant, {})
    label_y = {}                                # final height (km) of each river, park and land-area name
    for text, la, lo, kind, rotn in sorted(PLACES15[variant], key=lambda p: p[0] in align):   # partners first
        if kind == "bridge":
            continue
        x, y = proj(la, lo)
        n0 = len(ax.texts)
        b0 = extent(draw_geo(text, x, y, kind, rotn))
        for t in ax.texts[n0:]:
            t.remove()
        hard, radius, c = badge_boxes + furn_boxes + geo_boxes(), GEO_STYLE15[kind]["radius"], 100.0
        if align.get(text) in label_y:          # level with its partner: same kind, so the same baseline
            dx, dy, c = nudge_label15(b0, kind, Wpt, Hpt, ground, hard, badge_room, radius=radius,
                                      dy_fixed=(label_y[align[text]] - y) * s_pt)
            if c >= 100.0:
                notes.append(f"{text!r} not level with {align[text]!r} (no clear spot at that height)")
        if c >= 100.0:
            dx, dy, c = nudge_label15(b0, kind, Wpt, Hpt, ground, hard, badge_room, radius=radius)
        if c >= 100.0:
            notes.append(f"left out {text!r} (no clear spot within {radius:g} pt)")
            continue
        geo.append((text, draw_geo(text, x + dx / s_pt, y + dy / s_pt, kind, rotn)))
        label_y[text] = y + dy / s_pt
    crossing_boxes = [extent(arts) for text, arts in crossing]

    # (7) the sites: badge, number, name (next to the badge or at the end of a leader line)
    names = [map15_label(q["name"]) for q in rows]
    sizes = []
    for nm in names:
        t = ax.text(0, 0, nm, fontproperties=font)
        e = extent([t])
        t.remove()
        sizes.append((e[2] - e[0] + 1.0, e[3] - e[1]))
    line_groups = list(cross.values()) + list(unlabelled.values())
    placed = place_site_labels15(P, sizes, Wpt, Hpt, r, ground, furn_boxes + geo_boxes(), lines=line_groups,
                                 rows=crossing_boxes)
    leaders = [(i, lead) for i, (b, lead, c) in enumerate(placed) if lead is not None]
    name_artists = []
    for q, (px, py), nm, (b, lead, c) in zip(rows, P, names, placed):
        x, y = to_km(px, py)
        ax.scatter([x], [y], s=badge ** 2, c=PLAIN15["site_entry" if q["no"] in dark else "site"],
                   edgecolors="white", linewidths=0.9, zorder=8,
                   path_effects=[pe.SimplePatchShadow(offset=(0.5, -0.6), shadow_rgbFace="#000000", alpha=0.28),
                                 pe.Normal()])
        ax.annotate(str(q["no"]), (x, y), xytext=(0, -0.36 * site_font), textcoords="offset points", ha="center",
                    va="baseline", fontproperties=fontb, color="white", zorder=8.1)
        if lead is not None:
            (x0, y0), (x1, y1) = to_km(*lead[0]), to_km(*lead[1])
            ax.plot([x0, x1], [y0, y1], color=PLAIN15["leader"], lw=0.5, zorder=7, solid_capstyle="round",
                    path_effects=[pe.withStroke(linewidth=1.5, foreground="white")])
        name_artists.append(_halo_text(ax, *to_km(0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3])), nm, lw=2.0,
                                       fontproperties=font, color=PLAIN15["ink"], ha="center", va="center", zorder=9))

    # (8) a thin frame line just inside the page edge
    e = 0.2 / s_pt
    ax.add_patch(Rectangle((xl[0] + e, yl[0] + e), xl[1] - xl[0] - 2 * e, yl[1] - yl[0] - 2 * e, fc="none",
                           ec=PLAIN15["frame"], lw=0.4, zorder=10, clip_on=False))
    fig.canvas.draw()
    problems = check_overlaps15(fig, name_artists, P, r, leaders, geo, furn) + notes
    if open_ends:
        problems.append(f"New Jersey shore: {open_ends} coastline pieces stop inside the frame (data gap)")
    cross_problems, info = check_crossings15(fig, crossing, cross, others_of)
    problems += cross_problems
    for i, t in enumerate(name_artists):
        b = extent([t])
        hit = [k for k, v in cross.items() if any(_seg_box_hit(p, q, b) for p, q in v)]
        if placed[i][1] is not None:
            hit += [k for k, v in cross.items() if any(_seg_cross(placed[i][1][0], placed[i][1][1], p, q)
                                                       for p, q in v) and k not in hit]
        if hit:
            info.append(f"site {i + 1} name or leader crosses the {', the '.join(hit)} line")
    name = name or f"fig_map15_{variant}"
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGS, f"{name}.{ext}"), dpi=300)
    plt.close(fig)
    return W, H, problems, info


def entry_badges15(lay, rows):
    """R11 fix (2026-10-31): the site numbers whose map badge is dark (``PLAIN15["site_entry"]``): the sites within
    ``ENTRY_NEAR15_KM`` grid km of a rider entry point, when they are exactly one per entry point (the geometric part of
    ``_entry_claim15``, the rule that sets them in bold in the compact site table).  Else an empty set and a warning,
    since the caption names the dark badges."""
    n_entry = len(lay["depots"]) if lay.get("depots") else len(ENTRY_POINTS)
    near = [q for q in rows if q["km_entry"] <= ENTRY_NEAR15_KM]
    if len(near) != n_entry or len({q["entry"] for q in near}) != n_entry:
        print(f"warning: fig_map15: every badge alike ({len(near)} sites within {ENTRY_NEAR15_KM:g} km of "
              f"{len({q['entry'] for q in near})} of the {n_entry} entry points); the caption's dark badges do not hold")
        return set()
    print(f"fig_map15: dark badges (within {ENTRY_NEAR15_KM:g} km of an entry point, one per entry point): sites "
          + ", ".join(str(q["no"]) for q in near))
    return {q["no"] for q in near}


def fig_map15_plain(layout_json=None, site_stats_csv=None):
    """``make_figs.py map15``: the plain 15-site map in both frames (fig_map15_northup, fig_map15_rotated), the
    preferred one copied to fig_map15 (the paper's Fig. 4), and the two site tables, written exactly as fig_map15
    writes them (same rows, same numbering)."""
    layout_json = layout_json or os.path.join(MAP15_DIR, "layout.json")
    site_stats_csv = site_stats_csv or os.path.join(MAP15_DIR, "site_stats.csv")
    lay = load_layout15(layout_json)
    stats = load_site_stats15(site_stats_csv) if os.path.exists(site_stats_csv) else {}
    cands = load_candidates15(lay.get("candidates_csv"))
    missing = [s["id"] for s in lay["sites"] if s["id"] not in cands]
    if missing:
        raise ValueError(f"layout sites not in candidates.csv: {missing}")
    depots = [(d["name"], *rot(float(d["lat"]), float(d["lon"]))) for d in lay["depots"]] if lay.get("depots") \
        else [(nm, *rot(la, lo)) for nm, la, lo in ENTRY_POINTS]
    polys = nta_polygons()
    rx, ry = restaurants_xy()
    rows = site_rows15(lay, cands, rx, ry, polys, depots)
    # R11 fix (2026-10-31): the caption's lead claim (a site within 1 km of each entry point) is shown on the map by a
    # darker badge for those sites, the same rule that sets them in bold in the compact site table; only when the
    # sites near an entry point are one per entry point (else every badge stays alike and a warning is printed)
    dark = entry_badges15(lay, rows)
    for variant in FRAMES15:
        W, H, problems, info = fig_map15_plain_variant(rows, variant, demo=bool(lay.get("demo")), dark=dark)
        print(f"fig_map15_{variant}: {W:.2f} x {H:.2f} in; label check: "
              + (f"no overlap, nothing off the page, every text >= {MIN_TEXT15:g} pt, every bridge and tunnel name within "
                 f"{CROSS_NEAR15:g} pt of its line and {CROSS_CLEAR15:g} pt from the others" if not problems
                 else "; ".join(problems)))
        for line in info:
            print("   ", line)
    for ext in ("pdf", "png"):
        shutil.copyfile(os.path.join(FIGS, f"fig_map15_{MAP15_PREFERRED}.{ext}"),
                        os.path.join(FIGS, f"fig_map15.{ext}"))
    site_table15(lay, rows, stats, "site_table")
    site_table15_compact(lay, rows, stats, "site_table_compact")
    print(f"fig_map15 = fig_map15_{MAP15_PREFERRED}; {len(rows)} sites; tables figs/site_table.tex, "
          f"figs/site_table_compact.tex")
    return rows


# ---------------------------------------------------------------------------------------------------------------
# 15-site study: daily cost and share of orders served against the number of open sites (two small panels)
# ---------------------------------------------------------------------------------------------------------------
def run_dir15(run):
    """The folder of an R8 run: ``run`` as a path (absolute, or relative to the project root or the working folder),
    else a run name under ``RUNS15`` (cloud_results/ebike_swap_sim/outputs/)."""
    tries = [run] if os.path.isabs(run) else [os.path.join(ROOT, run), os.path.abspath(run), os.path.join(RUNS15, run)]
    for d in tries:
        if os.path.isdir(d):
            return d
    raise FileNotFoundError(f"run {run!r}: no folder at {', '.join(tries)}")


def _results_md_final(path):
    """The rows of the "## Final table" of an R8 RESULTS.md: name -> {k, V, lo, hi, served, layout_key=None}, values
    as printed (USD to 0.1, served share to 0.001)."""
    rows, on = {}, False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## "):
                on = line.startswith("## Final table")
            elif on and line.startswith("| ") and not line.startswith("| layout"):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                lo, hi = (float(x) for x in c[3].strip("[]").split(","))
                rows[c[0]] = {"k": int(c[1]), "V": float(c[2]), "lo": lo, "hi": hi, "served": float(c[4]),
                              "layout_key": None}
    return rows


def read_run15(run_dir):
    """In-sample results of an R8 run for fig_vk: ``(rows, curve, source)``.  ``rows``: final-table name ("best",
    "prod_m1", "V(k=1)", ...) -> {k (open sites), V, lo, hi (stratified 95 % CI), served, layout_key}; ``curve``: the
    V(k) rows sorted by k.  Source: the run's final_summary.json (full precision: ``in_sample`` and the ``vk`` list),
    else its RESULTS.md ("Final table", as printed).  When both exist they must agree to the printed precision, so a
    stale copy of either file stops the figure."""
    fs, md = os.path.join(run_dir, "final_summary.json"), os.path.join(run_dir, "RESULTS.md")
    if os.path.exists(fs):
        j = json.load(open(fs, encoding="utf-8"))
        rows = {name: {"k": int(e["n_open"]), "V": float(e["V"]), "lo": float(e["V_ci95"][0]),
                       "hi": float(e["V_ci95"][1]), "served": float(e["served_share"]),
                       "layout_key": e.get("layout_key")} for name, e in j["in_sample"].items()}
        curve = [{"k": int(e["k"]), "V": float(e["V"]), "lo": float(e["V_ci95"][0]), "hi": float(e["V_ci95"][1]),
                  "served": float(e["served_share"]), "layout_key": e.get("layout_key")} for e in j["vk"]]
        for r in curve:                                  # the vk list repeats the final-table rows "V(k=...)"
            q = rows.get(f"V(k={r['k']})")
            if q is not None and (abs(q["V"] - r["V"]) > 1e-6 or abs(q["served"] - r["served"]) > 1e-9):
                raise ValueError(f"{fs}: vk row k = {r['k']} differs from in_sample 'V(k={r['k']})'")
        source = fs
        if os.path.exists(md):
            for name, r in _results_md_final(md).items():
                q = rows.get(name)
                if q is None or q["k"] != r["k"] or any(abs(q[f] - r[f]) > 0.051 for f in ("V", "lo", "hi")) \
                        or abs(q["served"] - r["served"]) > 0.00051:
                    raise ValueError(f"{run_dir}: final_summary.json and RESULTS.md disagree on {name!r}: {q} vs {r}")
    elif os.path.exists(md):
        rows = _results_md_final(md)
        curve = [dict(r) for name, r in rows.items() if name.startswith("V(k=")]
        source = md
    else:
        raise FileNotFoundError(f"{run_dir}: neither final_summary.json nor RESULTS.md")
    curve.sort(key=lambda r: r["k"])
    return rows, curve, source


def _vk_site_label(layout_key, cands):
    """Short label of a one-site layout key for fig_vk: "Site 34" for a numbered DOT PEC site, "Midtown grid cell"
    for a grid cell, else the curated short name (``SITE15``, checked against the candidate file as in site_rows15);
    None for a layout of several sites or an unknown one."""
    if not layout_key or "|" in layout_key:
        return None
    cid = layout_key.split(":", 1)[0]
    r = cands.get(cid)
    if r is None:
        return cid
    known = SITE15.get(cid)
    if known and r["label"].rstrip().endswith(known[2]):
        if known[0] == "Grid cell":
            return f"{known[1]} grid cell"
        name = known[0]
    else:
        name = short_site_name(r)
    if "Site " in name:
        num = name.split("Site ", 1)[1].split()[0].rstrip(",")
        if num.isdigit():
            return f"Site {num}"
    return name.split(",")[0]


def fig_vk(run=None, layout_json=None):
    """Column-width figure (about 3.4 x 1.6 in): left, the expected cost per day with its 95 % CI; right, the share
    of orders served; both against the number of open sites k = 1, 2, 5, 10, 15, 20 (one measure per panel, no
    second y axis, both axes from zero).  Dots: best layout found with k sites, every site one standard unit; star:
    the 15-site layout of fig_map15, whose spare batteries were tuned afterwards.  The values come from the run named
    in ``layout_json`` (default figs/map15/layout.json, field ``run``) or from ``run`` (a run name under RUNS15 or a
    folder); nothing is typed in here (``read_run15``)."""
    layout_json = layout_json or os.path.join(MAP15_DIR, "layout.json")
    lay = load_layout15(layout_json) if os.path.exists(layout_json) else {}
    run = run or lay.get("run")
    if not run:
        raise ValueError(f"fig_vk: no run given and no 'run' in {layout_json}")
    run_dir = run_dir15(run)
    rows, curve, source = read_run15(run_dir)
    # Sources (all in ``source``: the run's final_summary.json, else its RESULTS.md; USD per day = per evening, mean
    # over the in-sample scenarios with the stratified 95 % CI; served = share of orders served):
    # dots k = 2, 5, 10, 15, 20: final_summary.json "vk" (= RESULTS.md section "V(k) curve" and final-table rows
    #   "V(k=...)"), the greedy path re-priced, every site SC:B3:C2 (one standard unit, 52,150 USD);
    # dot k = 1: the cheaper of row "V(k=1)" (greedy singleton; D30, a Midtown grid cell, in R8) and row "prod_m1"
    #   (best single site of the one-to-three-site study; D23 = DOT PEC Site 34);
    # star: row "best", the map's layout after the size polish (spares tuned), drawn apart at its own k.
    one = min((r for r in (rows.get("V(k=1)"), rows.get("prod_m1")) if r is not None), key=lambda r: r["V"])
    if curve[0]["k"] == 1:
        curve[0] = one
    best = rows["best"]
    if lay.get("V") is not None and lay.get("run") == os.path.basename(os.path.normpath(run_dir)) \
            and abs(float(lay["V"]) - best["V"]) > 0.051:
        raise ValueError(f"fig_vk: the star of run {run} ({best['V']:.1f}) is not the map's layout ({lay['V']:.1f})")
    cands_csv = os.path.join(run_dir, "candidates.csv")
    cands = load_candidates15(cands_csv if os.path.exists(cands_csv) else lay.get("candidates_csv"))
    one_lab = _vk_site_label(one["layout_key"], cands) if curve[0]["k"] == 1 else None
    ks = [r["k"] for r in curve]
    v = [r["V"] for r in curve]
    lo = [r["lo"] for r in curve]
    hi = [r["hi"] for r in curve]
    served = [r["served"] for r in curve]
    bk, bv, bserved = best["k"], best["V"], best["served"]
    assert all(a < b < c for a, b, c in zip(lo, v, hi)), "fig_vk: a CI that does not hold its value"
    if v != sorted(v, reverse=True) or served != sorted(served) or (bk in ks and bv >= v[ks.index(bk)]):
        print("warning: fig_vk: cost not falling or served share not rising with k, or the star not below its k")

    fig = plt.figure(figsize=(3.4, 1.6))
    axc = fig.add_axes([0.100, 0.19, 0.3975, 0.70])
    axs = fig.add_axes([0.5875, 0.19, 0.3975, 0.70])
    for ax, title in ((axc, "Cost per day (USD)"), (axs, "Orders served (%)")):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("bottom", "left"):
            ax.spines[sp].set_color("#888888")
        ax.tick_params(length=2, color="#888888", pad=1.5, labelsize=7)
        ax.grid(axis="y", color="#ececea", lw=0.4, zorder=0)
        ax.set_xlim(-0.2, 21.5)
        ax.set_xticks([1, 5, 10, 15, 20])
        ax.set_xticks([2], minor=True)
        ax.tick_params(axis="x", which="minor", length=1.5, color="#888888")
        ax.set_xlabel("Number of open sites", fontsize=7.5, labelpad=1.5)
        ax.text(0.0, 1.06, title, transform=ax.transAxes, fontsize=7.5, color=INK, ha="left", va="bottom")

    # left: cost per day, the 95 % CI as a light bar behind each dot
    axc.vlines(ks, lo, hi, colors=OURS_L, lw=2.4, zorder=2)
    axc.plot(ks, v, color=OURS, lw=0.9, zorder=3, solid_capstyle="round")
    axc.scatter(ks, v, s=16, c=OURS, edgecolors="white", linewidths=0.5, zorder=4)
    axc.scatter([bk], [bv], s=58, marker="*", c=OURS, edgecolors="white", linewidths=0.5, zorder=5)
    axc.set_ylim(0, 20000)
    axc.set_yticks([0, 5000, 10000, 15000, 20000])
    axc.set_yticklabels(["0", "5,000", "10,000", "15,000", "20,000"])
    axc.text(ks[0] + 0.9, v[0] + 350, f"{one_lab}: {v[0]:,.0f}" if one_lab else f"{v[0]:,.0f}", fontsize=7, color=INK2,
             ha="left", va="bottom")
    axc.text(ks[-1], lo[-1] - 450, f"{v[-1]:,.0f}", fontsize=7, color=INK2, ha="center", va="top")
    axc.annotate(f"best found: {bv:,.0f}\n(spares tuned)", (bk, bv), xytext=(7.4, 5600), fontsize=7, color=INK2,
                 ha="center", va="center", linespacing=1.05,
                 arrowprops=dict(arrowstyle="-", lw=0.45, color=INK2, shrinkA=2, shrinkB=3.5, relpos=(0.75, 1.0)))

    # right: share of orders served
    pct = [100 * s for s in served]
    axs.plot(ks, pct, color=OURS, lw=0.9, zorder=3, solid_capstyle="round")
    axs.scatter(ks, pct, s=16, c=OURS, edgecolors="white", linewidths=0.5, zorder=4)
    axs.scatter([bk], [100 * bserved], s=58, marker="*", c=OURS, edgecolors="white", linewidths=0.5, zorder=5)
    axs.set_ylim(0, 100)
    axs.set_yticks([0, 25, 50, 75, 100])
    axs.text(bk, 100 * bserved + 7, f"{100 * bserved:.1f}", fontsize=7, color=INK2, ha="center", va="bottom")
    axs.text(ks[-1], pct[-1] - 6, f"{pct[-1]:.1f}", fontsize=7, color=INK2, ha="center", va="top")
    save(fig, "fig_vk")
    print(f"fig_vk: run {os.path.basename(os.path.normpath(run_dir))} ({os.path.basename(source)}): "
          + ", ".join(f"k={k} {x:,.1f} ({100 * p:.1f} %)" for k, x, p in zip(ks, v, served))
          + f"; k=1 = {one_lab or ks[0]}; star k={bk} {bv:,.1f} ({100 * bserved:.1f} %)")



def fig_map15_numbers(layout_json=None, site_stats_csv=None, name="fig_map15_numbers"):
    """``make_figs.py map15_numbers`` (R16, 2026-11-09): the north-up frame of the plain 15-site map drawn at its
    printed width in the 8-page paper (0.68 column = 171 pt) with the badge numbers only, so that every label prints at
    7 pt or more.  The site names are in the compact site table, which uses the same numbers.  Same sites, numbering,
    dark badges and geography as ``fig_map15_northup``; the scale bar is labelled at 0 and 1 km only (the 0.5 km label
    does not fit at this scale).  Writes ``figs/<name>.{pdf,png}`` and nothing else."""
    import copy
    global map15_label, place_site_labels15, _scale_bar15
    layout_json = layout_json or os.path.join(MAP15_DIR, "layout.json")
    lay = load_layout15(layout_json)
    cands = load_candidates15(lay.get("candidates_csv"))
    depots = [(d["name"], *rot(float(d["lat"]), float(d["lon"]))) for d in lay["depots"]] if lay.get("depots") \
        else [(nm, *rot(la, lo)) for nm, la, lo in ENTRY_POINTS]
    rx, ry = restaurants_xy()
    rows = site_rows15(lay, cands, rx, ry, nta_polygons(), depots)
    dark = entry_badges15(lay, rows)

    def bar_two_labels(ax, x0, y0, s_pt, font, km=1.0, zorder=7):
        from matplotlib.patches import Rectangle
        h, col = 2.2 / s_pt, PLAIN15["furniture"]
        arts = [ax.add_patch(Rectangle((x0, y0), 0.5 * km, h, fc=col, ec=col, lw=0.5, zorder=zorder)),
                ax.add_patch(Rectangle((x0 + 0.5 * km, y0), 0.5 * km, h, fc="white", ec=col, lw=0.5, zorder=zorder))]
        for v, txt in ((0.0, "0"), (km, f"{km:g} km")):
            arts.append(_halo_text(ax, x0 + v, y0 - 1.6 / s_pt, txt, lw=1.6, fontproperties=font, color=col,
                                   ha="center", va="top", zorder=zorder))
        return arts

    keep = (copy.deepcopy(FRAMES15["northup"]), map15_label, place_site_labels15, _scale_bar15)
    try:
        FRAMES15["northup"].update(width=171.36 / 72.0, scale=(138.0, 15.0))
        _scale_bar15 = bar_two_labels
        map15_label = lambda n: ""
        place_site_labels15 = lambda P, sizes, *a, **k: [((x, y, x, y), None, 0.0) for x, y in P]
        W, H, problems, info = fig_map15_plain_variant(rows, "northup", name=name, demo=bool(lay.get("demo")), dark=dark)
    finally:
        FRAMES15["northup"], map15_label, place_site_labels15, _scale_bar15 = keep
    problems = [q for q in problems if not (q.startswith("site ") and "name covers badge" in q)]
    print(f"{name}: {W * 72:.1f} x {H * 72:.1f} pt; label check: " + ("; ".join(problems) if problems else "clean"))
    for line in info:
        print("   ", line)
    return rows

FIGURES = {"map": fig_map, "onesite": fig_onesite, "budget": fig_budget, "costs": fig_costs,
           "framework": fig_framework, "map15": fig_map15_plain, "map15_detailed": fig_map15_detailed,
           "map15_numbers": fig_map15_numbers, "map15_demo": demo_map15, "vk": fig_vk}
ON_REQUEST = ("map15_demo", "map15_detailed", "map15_numbers")        # not drawn by a run without names

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    kw = {}
    for flag, key in (("--layout", "layout_json"), ("--stats", "site_stats_csv"), ("--run", "run")):
        if flag in args:
            i = args.index(flag)
            kw[key] = args[i + 1]
            del args[i:i + 2]
    takes = {"map15": ("layout_json", "site_stats_csv"), "map15_detailed": ("layout_json", "site_stats_csv"),
             "map15_numbers": ("layout_json", "site_stats_csv"),
             "vk": ("layout_json", "run")}                                                  # options per figure
    names = args or [n for n in FIGURES if n not in ON_REQUEST]
    unknown = [n for n in names if n not in FIGURES]
    if unknown:
        print(f"unknown figure(s) {unknown}; usage: make_figs.py [name ...] [--layout layout.json --stats site_stats.csv] "
              f"[--run RUN]; names: {', '.join(FIGURES)}")
        sys.exit(2)
    for name in names:
        if name in takes and not args and not kw and not os.path.exists(os.path.join(MAP15_DIR, "layout.json")):
            print(f"{name}: no figs/map15/layout.json yet (R8 driver output); run `make_figs.py map15_demo` for the demo")
            continue
        FIGURES[name](**{k: v for k, v in kw.items() if k in takes.get(name, ())})
