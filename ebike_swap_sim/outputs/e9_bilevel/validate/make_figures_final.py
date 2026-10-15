import json, csv, math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

ROOT = "/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel"
VAL = os.path.join(ROOT, "validate")
recs = [json.loads(l) for l in open(os.path.join(VAL, "records.jsonl"))]
cands = list(csv.DictReader(open(os.path.join(ROOT, "candidates.csv"))))
for c in cands:
    c["lat"] = float(c["lat"]); c["lon"] = float(c["lon"])

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e5e4df"
BLUE, ORANGE, AQUA, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#e34948"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})

layout_rows = [r for r in recs if r.get("kind") == "layout"]
ll = [r for r in recs if r.get("kind") == "lower_level"]
ilp = {(r["layout_key"], r["seed"]): r for r in ll if r["policy"] == "ilp"}
base = {(r["layout_key"], r["seed"]): r for r in ll if r["policy"] == "baseline"}
integ = next(r for r in recs if r.get("kind") == "integrated")
sb = next(r for r in recs if r.get("kind") == "superset_bound")
agree = next(r for r in recs if r.get("kind") == "agreement")
seeds = [0, 1]; p = 0.5

# ---- table of layouts with certified intervals -----------------------------
tab = []
for i, r in enumerate(layout_rows):
    k = r["layout_key"]
    bv = sum(base[(k, s)]["total"] for s in seeds) / 2
    lbs = []  # certified lower bound of V: mean of per-scenario Gurobi bounds (totals incl. C_setup), superset LB for unsolved scenarios
    for s in seeds:
        row = ilp.get((k, s))
        if row is not None:
            lbs.append(float(row["bound"]))
        else:
            lbs.append(r["C_setup"] + sb["bound"][s])
    V_lb = sum(lbs) / 2
    tab.append({"order": i + 1, "key": k, "status": r["status"], "V": r["V"], "V_lb": V_lb, "prune_bound": r["lower_bound"],
                "baseline_V": bv, "served": r["served_share"], "statuses": r["statuses"], "gaps": r["gaps"],
                "opex": r["opex"], "inv": r["investment"], "C_setup": r["C_setup"],
                "solve_s": [ilp[(k, s)]["runtime_s"] for s in seeds if (k, s) in ilp],
                "wall_clock": r["wall_clock"]})
for t in tab:
    print(json.dumps({kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in t.items()}))
best = min(t["V"] for t in tab if t["V"] is not None)
print("best", best, "integrated bound", integ["bound"], "gap", integ["gap"])
print("pruned margins:", [(t["key"], round(t["prune_bound"] - best, 3)) for t in tab if t["status"] == "PRUNED"])

# ---- figure 1: layouts -----------------------------------------------------
solved = sorted([t for t in tab if t["V"] is not None], key=lambda t: t["V"])
pruned = [t for t in tab if t["V"] is None]
order = solved + pruned
fig, ax = plt.subplots(figsize=(10.5, 4.8))
ys = list(range(len(order)))[::-1]
for y, t in zip(ys, order):
    B = int(t["key"].split(":")[2][1:])
    col = BLUE if B == 2 else AQUA
    if t["V"] is not None:
        ax.barh(y, t["V"], height=0.55, color=col, edgecolor="white", linewidth=1)
        ax.plot([t["V_lb"], t["V"]], [y, y], color=INK, linewidth=1.4, solid_capstyle="butt")
        ax.plot([t["V_lb"]], [y], marker="|", color=INK, markersize=9)
        tl = sum(1 for s in t["statuses"] if s == "TIME_LIMIT")
        lab = f"{t['V']:.1f}" + (f"  (certified >= {t['V_lb']:.1f}; {tl} of 2 solves at 300 s)" if tl else "  (both scenarios OPTIMAL)")
        ax.text(t["V"] + 1.5, y, lab, va="center", fontsize=8, color=INK)
    else:
        ax.barh(y, t["prune_bound"], height=0.55, facecolor="white", edgecolor=col, hatch="////", linewidth=1)
        ax.text(t["prune_bound"] + 1.5, y, f"PRUNED after seed 0: bound {t['prune_bound']:.1f} >= best {best:.1f}", va="center", fontsize=8, color=INK2)
ax.axvline(integ["bound"], color=ORANGE, linestyle="--", linewidth=1.2)
ax.text(integ["bound"] - 1.5, 2.5, f"integrated ILP\nbound {integ['bound']:.1f}", color=ORANGE, fontsize=8, ha="right", va="center")
ax.set_yticks(ys); ax.set_yticklabels([t["key"] for t in order], fontsize=9, color=INK)
ax.set_xlim(640, 840); ax.set_xlabel("V = allocated setup + expected operating cost, USD per 4 h window (seeds 0-1, p = 1/2); ILP values are upper bounds")
ax.xaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
ax.set_title("E9.1 validation, budget m = 1 (52,150 USD): the 8 admissible layouts on L01-L04", loc="left", color=INK, fontsize=10)
ax.legend(handles=[Patch(color=BLUE, label="SC with B = 2 spares"), Patch(color=AQUA, label="SC with B = 1 spare"),
                   Line2D([], [], color=INK, linewidth=1.4, label="certified interval [sum of Gurobi bounds, incumbent]"),
                   Patch(facecolor="white", edgecolor=INK2, hatch="////", label="pruned (scenario 1 not solved): bound only")],
          loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=7.5, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(VAL, "layouts_m1.png"), dpi=160, facecolor="white"); plt.close(fig)

# ---- figure 2: map ---------------------------------------------------------
val_ids = ["L01", "L02", "L03", "L04"]; depots = ["L01", "L02", "L03"]
chosen = {"L02": ("SC", 2, 1)}
best_by_loc = {}
for t in solved:
    loc = t["key"].split(":")[0]
    if loc not in best_by_loc or t["V"] < best_by_loc[loc]["V"]:
        best_by_loc[loc] = t
fig, ax = plt.subplots(figsize=(7.4, 7.0))
lat0 = sum(c["lat"] for c in cands) / len(cands)
ax.set_aspect(1 / math.cos(math.radians(lat0)))
for c in cands:
    inval = c["id"] in val_ids
    ax.scatter(c["lon"], c["lat"], s=110 if inval else 60, marker="o", facecolor=(AQUA if inval else "white"),
               edgecolor=INK if inval else INK2, linewidths=1.0, zorder=5, alpha=0.95)
    ax.annotate(c["id"], (c["lon"], c["lat"]), xytext=(7, 5), textcoords="offset points", fontsize=8, color=INK if inval else INK2, zorder=8)
    if inval:
        bt = best_by_loc.get(c["id"])
        off = {"L01": (8, -16), "L02": (12, -4), "L03": (-138, 9), "L04": (10, -4)}[c["id"]]
        ax.annotate(f"best {bt['key'].split(':',1)[1]}: V {bt['V']:.1f}", (c["lon"], c["lat"]), xytext=off, textcoords="offset points", fontsize=7, color=INK, zorder=8)
    if c["id"] in depots:
        ax.scatter(c["lon"], c["lat"], s=330, marker="D", facecolor="none", edgecolor=VIOLET, linewidths=1.3, zorder=6)
    if c["id"] in chosen:
        r, B, Cc = chosen[c["id"]]
        ax.scatter(c["lon"], c["lat"], s=520, marker="*", facecolor=ORANGE, edgecolor=INK, linewidths=0.9, zorder=9)
ax.set_xlim(-74.003, -73.966); ax.set_xlabel("longitude (WGS84)"); ax.set_ylabel("latitude (WGS84)")
ax.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
ax.set_title("E9.1 validation, budget m = 1: candidates and the chosen site\n"
             "star = L02:SC:B2:C1, chosen by both the exhaustive enumeration\nand the integrated ILP (V 676.2 USD per window)",
             loc="left", fontsize=9, color=INK)
ax.legend(handles=[Line2D([], [], marker="o", color="w", markerfacecolor=AQUA, markeredgecolor=INK, markersize=9, label="validation candidate (L01-L04)"),
                   Line2D([], [], marker="o", color="w", markerfacecolor="white", markeredgecolor=INK2, markersize=7, label="other candidate (not in E9.1)"),
                   Line2D([], [], marker="D", color="w", markerfacecolor="none", markeredgecolor=VIOLET, markersize=10, label="depot (bikes start)"),
                   Line2D([], [], marker="*", color="w", markerfacecolor=ORANGE, markeredgecolor=INK, markersize=15, label="chosen: co-located SC, 2 spares, 1 charger")],
          loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=7.5, frameon=False)
fig.text(0.01, 0.005, "Coordinates from candidates.csv; the instance itself runs on a synthetic 150 m grid rotated 29 deg (R2.4 geometry caveat).", fontsize=7, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(VAL, "map_validate_m1.png"), dpi=160, facecolor="white"); plt.close(fig)

# ---- figure 3: solve times -------------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 3.9))
keys = [t["key"] for t in order]
x = list(range(len(keys)))
for i, k in enumerate(keys):
    for s, dx in zip(seeds, (-0.18, 0.18)):
        row = ilp.get((k, s))
        if row is None:
            ax.scatter(i + dx, 5, marker="x", color=INK2, s=40, zorder=5)
            ax.text(i + dx, 7, "not\nsolved", ha="center", fontsize=6.5, color=INK2)
            continue
        tl = row["status"] == "TIME_LIMIT"
        ax.bar(i + dx, row["runtime_s"], width=0.32, color=(RED if tl else BLUE), edgecolor="white")
        if tl:
            ax.text(i + dx, 150, f"gap {100*row['gap']:.1f} %", ha="center", va="center", fontsize=6.5, color="white", rotation=90)
        else:
            ax.text(i + dx, row["runtime_s"] + 6, "OPT", ha="center", fontsize=6.5, color=INK)
ax.axhline(300, color=INK2, linestyle="--", linewidth=1); ax.text(len(keys) - 0.5, 306, "TimeLimit 300 s", ha="right", fontsize=7.5, color=INK2)
ax.set_xticks(x); ax.set_xticklabels(keys, fontsize=8, rotation=20, ha="right")
ax.set_ylabel("Gurobi runtime, s (Threads 3, Seed 0)"); ax.set_ylim(0, 335)
ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
ax.set_title("Lower-level ILP solve times per layout (left bar seed 0, right bar seed 1); 0.58-0.79 M arcs each", loc="left", fontsize=10, color=INK)
ax.legend(handles=[Patch(color=BLUE, label="OPTIMAL"), Patch(color=RED, label="TIME_LIMIT (incumbent kept, MIP gap shown)")], loc="upper center", bbox_to_anchor=(0.5, -0.3), ncol=2, fontsize=7.5, frameon=False)
fig.tight_layout(); fig.savefig(os.path.join(VAL, "solve_times_m1.png"), dpi=160, facecolor="white"); plt.close(fig)
print("figures written")
