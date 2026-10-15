"""E9.6 access figures, regenerated from records.jsonl + candidates.csv (matplotlib Agg, no solver)."""
import csv
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

ROOT = "/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/e9_bilevel"
OUT = os.path.join(ROOT, "access")
REC = os.path.join(OUT, "records.jsonl")
LOG = os.path.join(ROOT, "logs", "access.log")

INK, INK2 = "#1f1f1f", "#5a5a5a"
COL = {"no_access": "#6b6b6b", "D8": "#c4542d", "D12": "#2d6fc4"}
ROLE_COL = {"S": "#e3a23c", "C": "#7a5bd1", "SC": "#2a9d5c"}

# ---------------------------------------------------------------- data
cands = {}
with open(os.path.join(ROOT, "candidates.csv")) as fh:
    for r in csv.DictReader(fh):
        cands[r["id"]] = r

plan = json.JSONDecoder().raw_decode(open(LOG).read())[0]
zones = plan["zones"]  # {"8": {zone: [locs]}, "12": {...}}
all_zones = sorted(zones["8"].keys())

steps, chosen, ll = [], [], []
cur = "no_access"
for line in open(REC):
    r = json.loads(line)
    if r["kind"] == "greedy_step":
        cur = r["access"]
        steps.append(r)
    elif r["kind"] == "layout_chosen":
        chosen.append(r)
    elif r["kind"] == "lower_level" and r.get("policy") == "ilp":
        r["_block"] = cur
        ll.append(r)

# per-layout V from the new ILP rows of each block (solve order)
def block_layouts(block):
    out, seen = [], {}
    for r in ll:
        if r["_block"] != block:
            continue
        k = r["layout_key"]
        if k not in seen:
            seen[k] = {"key": k, "tot": {}, "status": {}, "rt": 0.0, "served": {}}
            out.append(seen[k])
        seen[k]["tot"][r["seed"]] = r["total"]
        seen[k]["status"][r["seed"]] = r["status"]
        seen[k]["rt"] += r.get("runtime_s", 0.0)
        seen[k]["served"][r["seed"]] = (r.get("metrics") or {}).get("served_share")
    for d in out:
        d["V"] = sum(d["tot"].values()) / 3 if len(d["tot"]) == 3 and all(s == "OPTIMAL" for s in d["status"].values()) else None
        d["served_share"] = (sum(d["served"].values()) / len(d["served"])) if d["served"] and None not in d["served"].values() else None
    return out

def parse_key(key):
    items = []
    for part in key.split("|"):
        l, r, b, c = part.split(":")
        items.append((l, r, int(b[1:]), int(c[1:])))
    return items

def swap_locs(key):
    return [l for l, r, _b, _c in parse_key(key) if r in ("S", "SC")]

def covered(key, D):
    sl = set(swap_locs(key))
    return {z: any(l in sl for l in locs) for z, locs in zones[str(D)].items()}

# ---------------------------------------------------------------- geometry (lat/lon -> local metres, rotated grid)
LAT0 = sum(float(c["lat"]) for c in cands.values()) / len(cands)
LON0 = sum(float(c["lon"]) for c in cands.values()) / len(cands)
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(LAT0))
AZ = math.radians(29.0)  # avenue axis, degrees east of north (R2.4 grid)
BLOCK = 150.0

def xy(lat, lon):
    return ((float(lon) - LON0) * M_PER_DEG_LON, (float(lat) - LAT0) * M_PER_DEG_LAT)

def diamond(x, y, D):
    r = D * BLOCK
    ua = (math.sin(AZ) * r, math.cos(AZ) * r)      # along the avenues
    us = (math.cos(AZ) * r, -math.sin(AZ) * r)     # along the streets
    return [(x + ua[0], y + ua[1]), (x + us[0], y + us[1]), (x - ua[0], y - ua[1]), (x - us[0], y - us[1])]

# ---------------------------------------------------------------- figure 1: map
def draw_panel(ax, key, D, title, sub):
    for cid, c in cands.items():
        x, y = xy(c["lat"], c["lon"])
        mk = "s" if c["source"] == "zone" else ("D" if c["source"] == "landmark" else "o")
        ax.scatter([x], [y], s=46, marker=mk, facecolor="white", edgecolor=INK2, linewidths=0.9, zorder=5)
        ax.annotate(cid, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7.5, color=INK2, zorder=8)
    if key:
        for l, r, B, Cc in parse_key(key):
            x, y = xy(cands[l]["lat"], cands[l]["lon"])
            if r in ("S", "SC") and D:
                ax.add_patch(Polygon(diamond(x, y, D), closed=True, facecolor=ROLE_COL[r], alpha=0.10, edgecolor=ROLE_COL[r],
                                     linewidth=1.0, linestyle="--", zorder=3))
            ax.scatter([x], [y], s=150 + 55 * B, marker="*", facecolor=ROLE_COL[r], edgecolor=INK, linewidths=0.9, zorder=9)
            ax.annotate(f"{r} B{B} C{Cc}", (x, y), xytext=(6, -13), textcoords="offset points", fontsize=7.5,
                        color=ROLE_COL[r], fontweight="bold", zorder=10)
    ax.set_aspect("equal")
    ax.set_xlim(-2300, 1900)
    ax.set_ylim(-2200, 2400)
    ax.set_xticks([-2000, -1000, 0, 1000])
    ax.set_yticks([-2000, -1000, 0, 1000, 2000])
    ax.tick_params(labelsize=7, colors=INK2)
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.set_title(title + "\n" + sub, fontsize=8.5, color=INK, loc="left")

fig, axes = plt.subplots(1, 4, figsize=(16, 5.2))
draw_panel(axes[0], "L02:SC:B4:C2", None, "no_access, m = 2 and 3: L02:SC:B4:C2",
           "V 654.5, inv 52.6 k; covers 5/11 zones at D 8, 8/11 at D 12")
draw_panel(axes[1], "L02:SC:B4:C1|L05:SC:B1:C1", 8, "D = 8, m = 2: L02:SC:B4:C1 | L05:SC:B1:C1",
           "V 666.6, inv 103.1 k; 8/11 covered (not MN0202/0701/0801)")
draw_panel(axes[2], "L02:SC:B4:C2|L05:SC:B1:C1|L08:S:B1:C0", 8, "D = 8, m = 3: L02:SC:B4:C2 | L05:SC:B1:C1 | L08:S:B1:C0",
           "V 678.9, inv 153.9 k; 9/11 covered; repair cut by wall budget")
draw_panel(axes[3], "L02:SC:B4:C1|L05:SC:B1:C1", 12, "D = 12, m = 2 and 3: L02:SC:B4:C1 | L05:SC:B1:C1",
           "V 666.6, inv 103.1 k; 11/11 covered")
for ax in axes[1:]:
    ax.set_yticklabels([])
axes[0].set_ylabel("metres north of the candidate centroid", fontsize=8, color=INK2)
for ax in axes:
    ax.set_xlabel("metres east", fontsize=8, color=INK2)
h = [plt.Line2D([], [], marker="o", color="w", markerfacecolor="white", markeredgecolor=INK2, markersize=7, label="candidate: busiest restaurant cell"),
     plt.Line2D([], [], marker="D", color="w", markerfacecolor="white", markeredgecolor=INK2, markersize=6, label="candidate: landmark"),
     plt.Line2D([], [], marker="s", color="w", markerfacecolor="white", markeredgecolor=INK2, markersize=7, label="candidate: zone centre"),
     plt.Line2D([], [], marker="*", color="w", markerfacecolor=ROLE_COL["SC"], markeredgecolor=INK, markersize=13, label="open SC site (size ~ B)"),
     plt.Line2D([], [], marker="*", color="w", markerfacecolor=ROLE_COL["S"], markeredgecolor=INK, markersize=13, label="open S site"),
     Polygon([(0, 0)], facecolor="#2a9d5c", alpha=0.15, edgecolor="#2a9d5c", linestyle="--", label="D-block Manhattan reach of a swap site (grid rotated 29 deg)")]
fig.legend(handles=h, loc="lower center", ncol=3, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, 0.0))
fig.suptitle("E9.6 access row [U4]: chosen layouts on the 12 Midtown candidates (lat/lon of candidates.csv projected to metres; R2.4 synthetic-grid caveat)",
             fontsize=10, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.14, 1, 0.95))
fig.savefig(os.path.join(OUT, "access_map.png"), dpi=150, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- figure 2: V bars with setup / opex split, investment
by = {(r["access"], int(r["budget_m"])): r for r in chosen}
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.6, 1]})
variants = ["no_access", "D8", "D12"]
labels = {"no_access": "no access row", "D8": "D = 8 blocks", "D12": "D = 12 blocks"}
w = 0.26
base = {2: by[("no_access", 2)]["V"], 3: by[("no_access", 3)]["V"]}
for i, v in enumerate(variants):
    xs = [m + (i - 1) * w for m in (2, 3)]
    opex = [by[(v, m)]["opex_mean"] for m in (2, 3)]
    setup = [by[(v, m)]["C_setup"] for m in (2, 3)]
    ax1.bar(xs, opex, w, color=COL[v], alpha=0.55, edgecolor=INK, linewidth=0.5, label=f"{labels[v]}: expected opex")
    ax1.bar(xs, setup, w, bottom=opex, color=COL[v], alpha=1.0, edgecolor=INK, linewidth=0.5, hatch="///" , label=f"{labels[v]}: allocated setup C_setup")
    for x, m in zip(xs, (2, 3)):
        V = by[(v, m)]["V"]
        d = V - base[m]
        txt = f"{V:.1f}" + ("" if v == "no_access" else f"\n({d:+.1f})")
        ax1.text(x, V + 0.6, txt, ha="center", va="bottom", fontsize=7.5, color=INK)
ax1.set_ylim(600, 722)
ax1.set_xticks([2, 3])
ax1.set_xticklabels(["m = 2 (104,300 USD)", "m = 3 (156,450 USD)"])
ax1.set_ylabel("V = C_setup + expected OPEX (USD per 4 h window)")
ax1.set_title("V with / without the access row (delta vs no_access in brackets)", fontsize=9.5, loc="left")
ax1.legend(fontsize=6.8, frameon=False, ncol=3, loc="upper left")
ax1.grid(axis="y", alpha=0.3)
for i, v in enumerate(variants):
    xs = [m + (i - 1) * w for m in (2, 3)]
    inv = [by[(v, m)]["investment"] / 1000 for m in (2, 3)]
    ax2.bar(xs, inv, w, color=COL[v], edgecolor=INK, linewidth=0.5, label=labels[v])
    for x, iv, m in zip(xs, inv, (2, 3)):
        ax2.text(x, iv + 1.5, f"{iv:.1f}k\n{by[(v, m)]['n_open']} site" + ("s" if by[(v, m)]["n_open"] > 1 else ""), ha="center", va="bottom", fontsize=7, color=INK)
ax2.axhline(104.3, color=INK2, linestyle=":", linewidth=0.8)
ax2.axhline(156.45, color=INK2, linestyle=":", linewidth=0.8)
ax2.text(1.58, 106, "budget m=2", fontsize=6.5, color=INK2, ha="left")
ax2.text(1.58, 158.2, "budget m=3", fontsize=6.5, color=INK2, ha="left")
ax2.set_xticks([2, 3])
ax2.set_xticklabels(["m = 2", "m = 3"])
ax2.set_ylim(0, 185)
ax2.set_ylabel("investment inv(lambda), thousand USD")
ax2.set_title("Investment of the chosen layout", fontsize=9.5, loc="left")
ax2.legend(fontsize=7, frameon=False)
ax2.grid(axis="y", alpha=0.3)
fig.suptitle("E9.6: the planner-only access row costs the operator ~12.1 USD per window per extra site (allocated setup); opex barely moves",
             fontsize=9.5, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(os.path.join(OUT, "access.png"), dpi=150, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- figure 3: coverage and distance
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
rows3 = [("no_access", 2), ("D8", 2), ("D8", 3), ("D12", 2), ("D12", 3)]
names = ["no_access\nm=2,3", "D=8\nm=2", "D=8\nm=3", "D=12\nm=2", "D=12\nm=3"]
x = list(range(len(rows3)))
cov8 = [by[k]["zones_covered"]["8"] for k in rows3]
cov12 = [by[k]["zones_covered"]["12"] for k in rows3]
ax1.bar([i - 0.18 for i in x], cov8, 0.36, color=COL["D8"], edgecolor=INK, linewidth=0.5, label="zones with a swap site within 8 blocks")
ax1.bar([i + 0.18 for i in x], cov12, 0.36, color=COL["D12"], edgecolor=INK, linewidth=0.5, label="zones with a swap site within 12 blocks")
for i in x:
    ax1.text(i - 0.18, cov8[i] + 0.15, str(cov8[i]), ha="center", fontsize=8)
    ax1.text(i + 0.18, cov12[i] + 0.15, str(cov12[i]), ha="center", fontsize=8)
ax1.axhline(11, color=INK2, linestyle=":", linewidth=0.8)
ax1.text(len(x) - 0.55, 12.0, "11 demand zones; MN0801 is beyond 8 blocks of every candidate", fontsize=6.5, color=INK2, ha="right")
ax1.set_xticks(x)
ax1.set_xticklabels(names, fontsize=8)
ax1.set_ylim(0, 13)
ax1.set_ylabel("NTA demand zones covered (of 11)")
ax1.set_title("Zone coverage of the chosen layouts", fontsize=9.5, loc="left")
ax1.legend(fontsize=7, frameon=False, loc="lower right")
ax1.grid(axis="y", alpha=0.3)
mean_b = [by[k]["zone_mean_blocks"] for k in rows3]
max_b = [by[k]["zone_max_blocks"] for k in rows3]
ax2.plot(x, mean_b, marker="o", color=INK, label="mean over customer nodes (108 orders, seeds 0-2)")
ax2.plot(x, max_b, marker="s", color=COL["D8"], label="max over customer nodes")
for i in x:
    ax2.text(i, mean_b[i] + 0.4, f"{mean_b[i]:.1f}", ha="center", fontsize=7.5)
    ax2.text(i, max_b[i] + 0.4, f"{max_b[i]:.0f}", ha="center", fontsize=7.5, color=COL["D8"])
ax2.axhline(8, color=COL["D8"], linestyle="--", linewidth=0.7, alpha=0.6)
ax2.axhline(12, color=COL["D12"], linestyle="--", linewidth=0.7, alpha=0.6)
ax2.text(0.35, 7.0, "D = 8 (1.2 km)", fontsize=6.5, color=COL["D8"], ha="left")
ax2.text(0.35, 12.3, "D = 12 (1.8 km)", fontsize=6.5, color=COL["D12"], ha="left")
ax2.set_xticks(x)
ax2.set_xticklabels(names, fontsize=8)
ax2.set_ylim(0, 25)
ax2.set_ylabel("blocks (150 m) to the nearest open swap site")
ax2.set_title("Customer-to-site distance", fontsize=9.5, loc="left")
ax2.legend(fontsize=7, frameon=False, loc="upper right")
ax2.grid(alpha=0.3)
fig.suptitle("E9.6: coverage and distance; the second site (L05) cuts the mean distance from 11.6 to 8.5 blocks, the third (L08) to 7.4",
             fontsize=9.5, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(os.path.join(OUT, "access_coverage.png"), dpi=150, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- figure 4: search trace per variant
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
stage_col = {"singleton": "#8a8a8a", "forward_candidate": "#c4542d", "ls": "#2a9d5c", "repair": "#2d6fc4", "ls_covering": "#7a5bd1"}
for ax, v in zip(axes, variants):
    seq = []
    for s in steps:
        if s["access"] != v or s["step"] not in ("singleton", "forward_candidate"):
            continue
        seq.append((s["step"], s["layout_key"], s["V"]))
    # local search / repair: new ILP solves of this block, in solve order; D12 had none (all cache hits)
    for d in block_layouts(v):
        if any(d["key"] == k for _st, k, _V in seq):
            continue
        n_open = len(parse_key(d["key"]))
        if v == "no_access":
            st = "ls"
        elif n_open == 3 or (n_open == 2 and d["key"].startswith("L02:SC:B4:C2|")):
            st = "repair"
        else:
            st = "ls_covering"
        seq.append((st, d["key"], d["V"]))
    xs = list(range(len(seq)))
    for i, (st, k, V) in enumerate(seq):
        if V is None:
            ax.scatter([i], [700], marker="x", color="red", s=40, zorder=5)
            ax.annotate("TIME_LIMIT /\nwall budget", (i, 700), xytext=(-40, 4), textcoords="offset points", fontsize=6.5, color="red")
            continue
        ax.scatter([i], [V], color=stage_col[st], s=28, edgecolor=INK, linewidths=0.4, zorder=4)
    chosen_v = {m: by[(v, m)]["V"] for m in (2, 3)}
    ax.axhline(chosen_v[2], color=COL[v], linestyle="-", linewidth=1.0, label=f"chosen m=2: {chosen_v[2]:.1f}")
    if abs(chosen_v[3] - chosen_v[2]) > 1e-6:
        ax.axhline(chosen_v[3], color=COL[v], linestyle="--", linewidth=1.0, label=f"chosen m=3: {chosen_v[3]:.1f}")
    ax.axhline(654.525, color=INK2, linestyle=":", linewidth=0.8, label="no_access optimum 654.5")
    ax.set_title(f"{labels[v]}: {len(seq)} layouts newly solved" + ("" if v != "D12" else "; LS / repair all cache hits"),
                 fontsize=8.5, loc="left")
    ax.set_xlabel("pricing order (singletons, forward adds, then local search / repair)", fontsize=8)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.set_ylim(648, 705)
axes[0].set_ylabel("V of the priced layout (USD per window)")
h = [plt.Line2D([], [], marker="o", color="w", markerfacecolor=c, markeredgecolor=INK, markersize=7, label=n) for n, c in
     [("singleton (start stage)", stage_col["singleton"]), ("forward addition (all rejected: V rises)", stage_col["forward_candidate"]),
      ("local search move", stage_col["ls"]), ("access repair candidate", stage_col["repair"]), ("covering local search", stage_col["ls_covering"])]]
fig.legend(handles=h, loc="lower center", ncol=5, fontsize=7.5, frameon=False, bbox_to_anchor=(0.5, -0.01))
fig.suptitle("E9.6 greedy + local search trace: one site is optimal for the operator; every second site costs ~12 USD per window; the access repair adds L05 (and L08 at D 8, m 3)",
             fontsize=9.5, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.06, 1, 0.94))
fig.savefig(os.path.join(OUT, "access_search.png"), dpi=150, facecolor="white")
plt.close(fig)

# ---------------------------------------------------------------- print tables for the markdown
print("== coverage per zone per layout")
for name, key, D in [("no_access D8", "L02:SC:B4:C2", 8), ("no_access D12", "L02:SC:B4:C2", 12),
                     ("D8 m=2", "L02:SC:B4:C1|L05:SC:B1:C1", 8), ("D8 m=3", "L02:SC:B4:C2|L05:SC:B1:C1|L08:S:B1:C0", 8),
                     ("D12 m=2,3", "L02:SC:B4:C1|L05:SC:B1:C1", 12)]:
    c = covered(key, D)
    print(name, "covered", sorted(z for z, ok in c.items() if ok), "uncovered", sorted(z for z, ok in c.items() if not ok))
print("== block layouts")
for v in variants:
    print("--", v)
    for d in block_layouts(v):
        print(d["key"], d["V"], d["served_share"], round(d["rt"], 1), d["status"])
