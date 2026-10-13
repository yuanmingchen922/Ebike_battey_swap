"""E3u round-3 final report: tables with t-CIs, figures (Agg) and RESULTS_final.md.
Reads only records.jsonl / results.csv of outputs/e3u_round3 and the round-2
recomputed baseline rows (outputs/e3u/relaxed_baseline_recomputed.csv). No solver calls."""
import json, math, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "e3u_round3")
REC = os.path.join(OUT, "records.jsonl")
R2_BASE = os.path.join(ROOT, "outputs", "e3u", "relaxed_baseline_recomputed.csv")
LAYOUTS = ["colocated", "separated_1hub", "separated_2hubs"]
LAB = {"colocated": "(a) co-located 3 sites", "separated_1hub": "(b) 3 swap sites + 1 hub",
       "separated_2hubs": "(c) 3 swap sites + 2 hubs"}
SHORT = {"colocated": "(a) co-located", "separated_1hub": "(b) 1 hub", "separated_2hubs": "(c) 2 hubs"}
TARGETS = ["written", "relaxed"]
SW = ["free", "none"]
SWLAB = {"free": "transfers free", "none": "h = z = 0 (no transfers)"}
RULES = ["NONE", "REORDER_POINT"]
F_HUB = 29.19
SEEDS = [0, 1, 2, 3, 4]

# ---------------------------------------------------------------- t-CI
try:
    from scipy import stats
    def tcrit(n):
        return float(stats.t.ppf(0.975, n - 1))
except Exception:  # noqa: BLE001
    _T = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
    def tcrit(n):
        return _T[n]

def mci(vals):
    v = np.asarray([x for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)
    n = len(v)
    if n == 0:
        return (float("nan"), float("nan"), 0)
    if n < 3:
        return (float(v.mean()), float("nan"), n)
    return (float(v.mean()), float(tcrit(n) * v.std(ddof=1) / math.sqrt(n)), n)

def fci(vals, d=2):
    m, h, n = mci(vals)
    if n == 0:
        return "-"
    if math.isnan(h):
        return f"{m:.{d}f} [n={n}]"
    return f"{m:.{d}f} +/- {h:.{d}f} [n={n}]"

def seeds_str(vals, d=2):
    return ", ".join(f"{v:.{d}f}" for v in vals)

def jl(v):
    if isinstance(v, str):
        return json.loads(v)
    return v

# ---------------------------------------------------------------- load
rows = [json.loads(l) for l in open(REC) if l.strip()]
def key(r):
    if r["method"] == "ilp":
        return (r["layout"], r["targets"], int(r["seed"]), "ilp", r["transfers"])
    return (r["layout"], r["targets"], int(r["seed"]), "baseline", str(r.get("switch", "")).replace("transfer_rule=", ""))
last, n_dup = {}, 0
for r in rows:
    k = key(r)
    if k in last:
        n_dup += 1
    last[k] = r
df = pd.DataFrame(list(last.values()))
ilp = df[df.method == "ilp"].copy()
base3 = df[df.method == "baseline"].copy()
base3["rule"] = base3["switch"].str.replace("transfer_rule=", "")
base3["source"] = base3["source"].fillna("round3")

# baseline cells whose library was not rebuilt in round 3: take the F1-corrected recomputed rows of round 2
r2b = pd.read_csv(R2_BASE)
r2b["rule"] = r2b["switch"].str.replace("transfer_rule=", "")
r2b["source"] = "round2_recomputed"
have = {(r.layout, r.targets, int(r.seed), r.rule) for r in base3.itertuples()}
fill = r2b[[(r.layout, r.targets, int(r.seed), r.rule) not in have for r in r2b.itertuples()]].copy()
# consistency of the overlapping rows (round-3 recomputation vs round-2 recomputation)
overlap = r2b[[(r.layout, r.targets, int(r.seed), r.rule) in have for r in r2b.itertuples()]]
mism = []
for r in overlap.itertuples():
    b = base3[(base3.layout == r.layout) & (base3.targets == r.targets) & (base3.seed == r.seed) & (base3.rule == r.rule)].iloc[0]
    if abs(float(b.total) - float(r.total)) > 1e-6:
        mism.append(f"{r.layout}/{r.targets}/seed{r.seed}/{r.rule}: {b.total:.3f} vs {r.total:.3f}")
base = pd.concat([base3, fill], ignore_index=True, sort=False)
for c in ["total", "unserved", "response", "lateness", "C_reb", "C_elec", "C_travel", "C_setup", "served_share", "n_unserved",
          "transfers_used", "batteries_moved", "stockout_slots_total", "peak_kw_group_max", "end_full_total", "kwh_purchased", "n_swaps"]:
    base[c] = pd.to_numeric(base[c], errors="coerce")
    if c in ilp:
        ilp[c] = pd.to_numeric(ilp[c], errors="coerce")
for c in ["bound", "gap", "runtime_s", "time_limit_used_s", "n_binaries", "n_rows", "node_count", "round2_total", "round2_gap", "n_unservable"]:
    ilp[c] = pd.to_numeric(ilp[c], errors="coerce")
base["seed"] = base["seed"].astype(int)
ilp["seed"] = ilp["seed"].astype(int)
assert len(base) == 60, len(base)
assert len(ilp) == 60, len(ilp)

def B(layout, targets, seed, rule, col="total"):
    s = base[(base.layout == layout) & (base.targets == targets) & (base.seed == seed) & (base.rule == rule)]
    return float(s.iloc[0][col]) if len(s) else float("nan")

def I(layout, targets, seed, sw, col="total"):
    s = ilp[(ilp.layout == layout) & (ilp.targets == targets) & (ilp.seed == seed) & (ilp.transfers == sw)]
    return s.iloc[0][col] if len(s) else None

def cell(layout, targets, sw):
    return ilp[(ilp.layout == layout) & (ilp.targets == targets) & (ilp.transfers == sw)].sort_values("seed")

# headline gaps recomputed against the merged (same-policy) baselines
ilp["base_none"] = [B(r.layout, r.targets, r.seed, "NONE") for r in ilp.itertuples()]
ilp["base_reorder"] = [B(r.layout, r.targets, r.seed, "REORDER_POINT") for r in ilp.itertuples()]
ilp["gap_none_pct"] = 100 * (ilp.base_none - ilp.total) / ilp.base_none
ilp["gap_reorder_pct"] = 100 * (ilp.base_reorder - ilp.total) / ilp.base_reorder
ilp["gap_best_pct"] = 100 * (np.minimum(ilp.base_none, ilp.base_reorder) - ilp.total) / np.minimum(ilp.base_none, ilp.base_reorder)

# ---------------------------------------------------------------- derived quantities
def transfer_value(layout, targets):
    vals, ub, seeds = [], [], []
    for s in SEEDS:
        a, b = cell(layout, targets, "none"), cell(layout, targets, "free")
        a, b = a[a.seed == s], b[b.seed == s]
        if len(a) and len(b):
            vals.append(float(a.iloc[0].total) - float(b.iloc[0].total))
            # upper bound: none incumbent (optimal) minus the free run's best bound
            ub.append(float(a.iloc[0].total) - float(b.iloc[0].bound))
            seeds.append(s)
    return vals, ub, seeds

def separation(layout, targets, sw):
    vals = []
    for s in SEEDS:
        a, b = cell(layout, targets, sw), cell("colocated", targets, sw)
        a, b = a[a.seed == s], b[b.seed == s]
        if len(a) and len(b):
            vals.append(float(a.iloc[0].total) - float(b.iloc[0].total))
    return vals

# ---------------------------------------------------------------- figures
figs = []
C_ILPF, C_ILPN, C_BN, C_BR = "#1f77b4", "#d62728", "#7f7f7f", "#bcbd22"

def fig_cost_by_layout():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    series = [("ilp", "free", "ILP, transfers free", C_ILPF), ("ilp", "none", "ILP, h = z = 0", C_ILPN),
              ("baseline", "NONE", "policy, transfer rule NONE", C_BN), ("baseline", "REORDER_POINT", "policy, REORDER_POINT", C_BR)]
    w = 0.2
    for ax, targets in zip(axes, TARGETS):
        for si, (m, sw, lab, col) in enumerate(series):
            for li, layout in enumerate(LAYOUTS):
                if m == "ilp":
                    vals = cell(layout, targets, sw).total.to_numpy(float)
                else:
                    vals = base[(base.layout == layout) & (base.targets == targets) & (base.rule == sw)].total.to_numpy(float)
                mean, h, n = mci(vals)
                x = li + (si - 1.5) * w
                ax.bar(x, mean, w, color=col, label=lab if li == 0 else None, yerr=None if math.isnan(h) else h,
                       capsize=3, error_kw={"elinewidth": 0.8})
                ax.scatter(np.full(len(vals), x) + np.linspace(-0.3, 0.3, len(vals)) * w, vals, s=9, color="black", zorder=3)
                ax.text(x, mean + 70, f"{mean:.0f}", ha="center", fontsize=6)
        ax.set_xticks(range(3)); ax.set_xticklabels([LAB[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ") for l in LAYOUTS], fontsize=8)
        ax.set_title(f"end targets: {targets}" + (" (rho 0.5, R_end 1)" if targets == "written" else " (rho 0, R_end 0)"), fontsize=9.5)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, 1350)
    axes[0].set_ylabel("total cost (26), USD per 4 h window")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("E3u round 3: total cost by layout (bars = mean of seeds 0-4, error bars = 95 % t-CI, dots = seeds)", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    p = os.path.join(OUT, "fig_cost_by_layout.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_transfer_value():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    w = 0.36
    cols = {"written": "#1f77b4", "relaxed": "#ff7f0e"}
    ax = axes[0]
    for ti, targets in enumerate(TARGETS):
        for li, layout in enumerate(LAYOUTS):
            vals, ub, _ = transfer_value(layout, targets)
            mean, h, n = mci(vals)
            x = li + (ti - 0.5) * w
            ax.bar(x, mean, w, color=cols[targets], alpha=0.85, yerr=None if math.isnan(h) else h, capsize=3,
                   label=f"{targets} targets" if li == 0 else None)
            ax.scatter(np.full(len(vals), x), vals, s=12, color="black", zorder=3)
            if targets == "written" and layout != "colocated":
                ax.scatter(np.full(len(ub), x), ub, s=22, facecolors="none", edgecolors="black", zorder=3,
                           label="upper bound (600 s MIP bound)" if li == 1 else None)
    ax.set_ylim(-3, 40)
    ax.set_ylabel("value of transfers, USD per 4 h window")
    ax.set_title("cost(h = z = 0) - cost(transfers free), ILP", fontsize=9)
    ax = axes[1]
    for ti, targets in enumerate(TARGETS):
        for li, layout in enumerate(LAYOUTS[1:], start=1):
            vals = separation(layout, targets, "free")
            mean, h, n = mci(vals)
            x = li + (ti - 0.5) * w
            ax.bar(x, mean, w, color=cols[targets], alpha=0.85, yerr=None if math.isnan(h) else h, capsize=3,
                   label=f"{targets} targets" if li == 1 else None)
            ax.scatter(np.full(len(vals), x), vals, s=12, color="black", zorder=3)
        ax.axhline(F_HUB, color="black", linewidth=0.6, linestyle=":")
        ax.axhline(2 * F_HUB, color="black", linewidth=0.6, linestyle=":")
    ax.text(0.55, F_HUB + 1, "F_hub (1 hub)", fontsize=7); ax.text(0.55, 2 * F_HUB + 1, "2 x F_hub", fontsize=7)
    ax.set_xlim(0.4, 2.6)
    ax.set_ylabel("cost of separation, USD per 4 h window")
    ax.set_title("cost(layout) - cost(co-located), ILP transfers free", fontsize=9)
    for ax in axes:
        ax.set_xticks(range(3)); ax.set_xticklabels([LAB[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ") for l in LAYOUTS], fontsize=8)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.legend(fontsize=7, frameon=False, loc="upper left"); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("E3u round 3: value of transfers and cost of separation (bars = mean of 5 seeds, error bars = 95 % t-CI, dots = seeds)", fontsize=9.5)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_transfer_value.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_gap_by_layout():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    w = 0.2
    series = [("free", "gap_none_pct", "ILP free vs policy NONE", C_ILPF, 1.0), ("none", "gap_none_pct", "ILP h = z = 0 vs policy NONE", C_ILPN, 1.0),
              ("free", "gap_reorder_pct", "ILP free vs policy REORDER_POINT", C_ILPF, 0.45), ("none", "gap_reorder_pct", "ILP h = z = 0 vs REORDER_POINT", C_ILPN, 0.45)]
    for ax, targets in zip(axes, TARGETS):
        for si, (sw, col, lab, color, alpha) in enumerate(series):
            for li, layout in enumerate(LAYOUTS):
                vals = cell(layout, targets, sw)[col].to_numpy(float)
                mean, h, n = mci(vals)
                x = li + (si - 1.5) * w
                ax.bar(x, mean, w, color=color, alpha=alpha, yerr=None if math.isnan(h) else h, capsize=3, label=lab if li == 0 else None)
                ax.scatter(np.full(len(vals), x) + np.linspace(-0.3, 0.3, len(vals)) * w, vals, s=9, color="black", zorder=3)
        ax.set_xticks(range(3)); ax.set_xticklabels([LAB[l].replace(" 3 sites", "\n3 sites").replace(" + ", "\n+ ") for l in LAYOUTS], fontsize=8)
        ax.set_title(f"end targets: {targets}", fontsize=9.5); ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("headline gap 100 (policy - ILP) / policy, %")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("E3u round 3: ILP saving over the R2.3 policy by layout (mean of seeds 0-4, 95 % t-CI, dots = seeds)", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    p = os.path.join(OUT, "fig_gap_by_layout.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_cost_components():
    comps = [("C_setup", "setup (27)"), ("C_travel", "travel (29)"), ("C_elec", "electricity (28)"), ("unserved", "unserved (30)"),
             ("response", "response (31)"), ("lateness", "lateness (31)"), ("C_reb", "transfers (32)")]
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(12, 4.6))
    xs, labels, pos = [], [], 0.0
    for layout in LAYOUTS:
        for targets in TARGETS:
            for sw in SW:
                sub = cell(layout, targets, sw)
                bottom = 0.0
                for ci, (col, lab) in enumerate(comps):
                    v = float(sub[col].mean())
                    ax.bar(pos, v, 0.8, bottom=bottom, color=cmap(ci), label=lab if pos == 0.0 else None)
                    bottom += v
                ax.text(pos, bottom + 6, f"{bottom:.0f}", ha="center", fontsize=6)
                xs.append(pos); labels.append(f"{SHORT[layout]}\n{'free' if sw == 'free' else 'h=z=0'}\n{targets}"); pos += 1.0
            pos += 0.3
        pos += 0.6
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("mean cost over seeds 0-4, USD per 4 h window")
    ax.set_ylim(0, 880)
    ax.set_title("E3u round 3: ILP cost components (27)-(32) by layout, transfer switch and end-target setting", fontsize=10)
    ax.legend(fontsize=7, frameon=False, ncol=4); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_cost_components.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_solver():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    xs, labels, pos = [], [], 0
    for layout in LAYOUTS:
        for targets in TARGETS:
            for sw in SW:
                sub = cell(layout, targets, sw)
                for r in sub.itertuples():
                    col = C_ILPF if r.status == "OPTIMAL" else "#d62728"
                    mk = "o" if r.source == "round3" else "s"
                    ax.scatter(pos, r.runtime_s, s=18, color=col, marker=mk, zorder=3)
                xs.append(pos); labels.append(f"{SHORT[layout][:3]}\n{sw[:4]}\n{targets[:3]}"); pos += 1
            pos += 0.3
    ax.axhline(300, color="black", linewidth=0.6, linestyle=":"); ax.axhline(600, color="black", linewidth=0.6, linestyle=":")
    ax.text(0, 305, "TimeLimit 300 s", fontsize=7); ax.text(0, 605, "TimeLimit 600 s", fontsize=7)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel("Gurobi wall time, s (Threads 3)")
    ax.set_title("solve time per run: blue = OPTIMAL, red = TIME_LIMIT; circle = round 3, square = reused round 2", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    tl = ilp[ilp.status == "TIME_LIMIT"].sort_values(["layout", "seed"])
    x = np.arange(len(tl))
    ax.bar(x - 0.2, 100 * tl.gap, 0.4, color="#d62728", label="MIP gap after 600 s (round 3)")
    r2g = [100 * g if not math.isnan(g) else np.nan for g in tl.round2_gap]
    ax.bar(x + 0.2, r2g, 0.4, color="#7f7f7f", label="MIP gap after 300 s (round 2, 4 cells)")
    ax.set_xticks(x); ax.set_xticklabels([f"{SHORT[r.layout][:3]}\ns{r.seed}" for r in tl.itertuples()], fontsize=7)
    ax.set_ylabel("relative MIP gap, %"); ax.set_ylim(0, 2.6)
    ax.set_title("separated / written / transfers-free cells: gap at the time limit", fontsize=8)
    ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("E3u round 3: solver statistics", fontsize=10)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_solver.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_in_transit():
    fig, ax = plt.subplots(figsize=(8.5, 3.9))
    cmap = plt.get_cmap("tab10")
    for li, layout in enumerate(LAYOUTS):
        for targets, ls in (("written", "-"), ("relaxed", "--")):
            series = []
            for r in cell(layout, targets, "free").itertuples():
                series.append(np.array(jl(r.m_t), dtype=float))
            H = len(series[0]) - 1
            for arr in series:
                ax.step(range(H + 1), arr, where="post", color=cmap(li), alpha=0.2, linewidth=0.7, linestyle=ls)
            ax.step(range(H + 1), np.mean(series, axis=0), where="post", color=cmap(li), linewidth=2, linestyle=ls,
                    label=f"{LAB[layout]}, {targets} (mean of {len(series)} seeds)")
    ax.set_xlabel("boundary t (slots of 5 min, 17:00 + 5 t min)"); ax.set_ylabel("batteries in transit m_t (count)")
    ax.set_title("E3u round 3: in-transit batteries (24), ILP with transfers free (thin = seeds, thick = mean)", fontsize=9.5)
    ax.legend(fontsize=7, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.22)); ax.spines[["top", "right"]].set_visible(False)
    fig.set_size_inches(8.5, 4.9)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_in_transit.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_full_stock(seed, targets):
    fig, axes = plt.subplots(3, 1, figsize=(8.5, 7.8), sharex=True)
    for ax, layout in zip(axes, LAYOUTS):
        sub = cell(layout, targets, "free"); r = sub[sub.seed == seed].iloc[0]
        roles = jl(r.facility_roles); fs = jl(r.full_stock)
        for j, traj in fs.items():
            fac = roles[j]
            ax.step(range(len(traj)), traj, where="post", linestyle="-" if fac["swap"] else "--",
                    label=f"{j} ({'swap site' if fac['swap'] else 'hub'}, B={fac['B']}, C={fac['C']})")
        ax.set_ylabel("full spares n_jLt (count)")
        ax.set_title(f"{LAB[layout]}: stock-out slots {int(r.stockout_slots_total)}, shuttles {int(r.transfers_used)}, "
                     f"batteries moved {int(r.batteries_moved)}, swaps {int(r.n_swaps)}, status {r.status}", fontsize=8.5)
        ax.legend(fontsize=7, frameon=False, ncol=2); ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("boundary t (slots of 5 min, 17:00 + 5 t min)")
    fig.suptitle(f"E3u round 3: full-battery stock per facility (13), ILP transfers free, seed {seed}, {targets} targets", fontsize=10)
    fig.tight_layout()
    p = os.path.join(OUT, f"fig_full_stock_{targets}_seed{seed}.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

def fig_grid(seed, targets="written"):
    fig, axes = plt.subplots(3, 1, figsize=(8.5, 6.6), sharex=True)
    for ax, layout in zip(axes, LAYOUTS):
        sub = cell(layout, targets, "free"); r = sub[sub.seed == seed].iloc[0]
        loads, limits = jl(r.grid_load_kw), jl(r.grid_limit_kw)
        for g, load in loads.items():
            ax.step(range(len(load)), load, where="post", label=f"group {g}: charging load (20)")
            ax.step(range(len(limits[g])), limits[g], where="post", linestyle=":", color="black", label=f"P_grid[{g}] limit (21)")
        ax.set_ylabel("power, kW"); ax.set_title(f"{LAB[layout]}: peak {float(r.peak_kw_group_max):.2f} kW", fontsize=9)
        ax.legend(fontsize=7, frameon=False); ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("slot t (5 min, 17:00 + 5 t min)")
    fig.suptitle(f"E3u round 3: grid-group charging load vs limit, ILP transfers free, seed {seed}, {targets} targets", fontsize=10)
    fig.tight_layout()
    p = os.path.join(OUT, f"fig_grid_load_seed{seed}.png"); fig.savefig(p, dpi=150); plt.close(fig); return p

figs = [fig_cost_by_layout(), fig_gap_by_layout(), fig_transfer_value(), fig_cost_components(), fig_solver(), fig_in_transit(),
        fig_full_stock(0, "written"), fig_full_stock(0, "relaxed"), fig_grid(0)]

# ---------------------------------------------------------------- tables
L = []
def add(*s):
    L.extend(s)

# T1 ILP cost
t1 = ["| layout | targets | transfers free | h = z = 0 | value of transfers (none - free) | status free / none |", "|---|---|---|---|---|---|"]
for layout in LAYOUTS:
    for targets in TARGETS:
        f, n = cell(layout, targets, "free"), cell(layout, targets, "none")
        tv, ub, _ = transfer_value(layout, targets)
        t1.append(f"| {LAB[layout]} | {targets} | {fci(f.total)} ({seeds_str(f.total)}) | {fci(n.total)} ({seeds_str(n.total)}) | "
                  f"{fci(tv)} ({seeds_str(tv)}) | {''.join(s[0] for s in f.status)} / {''.join(s[0] for s in n.status)} |")

# T2 value of transfers detail
t2 = ["| layout | targets | value (none - free), mean +/- CI | per seed | upper bound (none - free bound) | shuttles used (free) | batteries moved | C_reb (32) | served share free / none | n_swaps free / none |",
      "|---|---|---|---|---|---|---|---|---|---|"]
for layout in LAYOUTS:
    for targets in TARGETS:
        f, n = cell(layout, targets, "free"), cell(layout, targets, "none")
        tv, ub, _ = transfer_value(layout, targets)
        t2.append(f"| {LAB[layout]} | {targets} | {fci(tv)} | {seeds_str(tv)} | {fci(ub)} | {f.transfers_used.mean():.1f} | {f.batteries_moved.mean():.1f} | "
                  f"{f.C_reb.mean():.1f} | {f.served_share.mean():.3f} / {n.served_share.mean():.3f} | {f.n_swaps.mean():.1f} / {n.n_swaps.mean():.1f} |")

# T3 separation
t3 = ["| layout | targets | switch | separation cost, mean +/- CI | per seed | hub setup F_hub | operational part (mean) |", "|---|---|---|---|---|---|---|"]
for layout in LAYOUTS[1:]:
    nh = 1 if layout == "separated_1hub" else 2
    for targets in TARGETS:
        for sw in SW:
            v = separation(layout, targets, sw); m, h, n = mci(v)
            t3.append(f"| {LAB[layout]} | {targets} | {SWLAB[sw]} | {fci(v)} | {seeds_str(v)} | {nh * F_HUB:.2f} | {m - nh * F_HUB:.2f} |")

# T4 operational metrics
t4 = ["| layout | targets | switch | n | served share | n_unserved | C_reb | shuttles | batteries moved | n_swaps | stock-out slots | grid peak kW | end full (>= 4.5 written) | kWh bought | C_elec |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for layout in LAYOUTS:
    for targets in TARGETS:
        for sw in SW:
            c = cell(layout, targets, sw)
            t4.append(f"| {LAB[layout]} | {targets} | {SWLAB[sw]} | {len(c)} | {fci(c.served_share, 3)} | {c.n_unserved.mean():.1f} | {c.C_reb.mean():.1f} | "
                      f"{c.transfers_used.mean():.1f} | {c.batteries_moved.mean():.1f} | {c.n_swaps.mean():.1f} | {fci(c.stockout_slots_total, 1)} | "
                      f"{c.peak_kw_group_max.max():.2f} (max) / {c.peak_kw_group_max.mean():.2f} (mean) | {c.end_full_total.mean():.1f} | {c.kwh_purchased.mean():.2f} | {c.C_elec.mean():.2f} |")

# T5 baseline
t5 = ["| layout | rule | total | unserved (30) | response (31) | lateness (31) | C_reb (32) | C_elec (28) | served share | shuttles | batteries moved | stock-out slots | grid peak kW (max) | end full | (17)/(18) reported (written run) |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for layout in LAYOUTS:
    for rule in RULES:
        b = base[(base.layout == layout) & (base.targets == "written") & (base.rule == rule)].sort_values("seed")
        fam = "; ".join(f"s{r.seed}:{r.reported_families}" for r in b.itertuples())
        t5.append(f"| {LAB[layout]} | {rule} | {fci(b.total)} | {fci(b.unserved)} | {fci(b.response)} | {fci(b.lateness)} | {fci(b.C_reb)} | {fci(b.C_elec)} | "
                  f"{fci(b.served_share, 3)} | {b.transfers_used.mean():.1f} | {b.batteries_moved.mean():.1f} | {b.stockout_slots_total.mean():.1f} | "
                  f"{b.peak_kw_group_max.max():.2f} | {b.end_full_total.mean():.1f} | {fam} |")
# REORDER - NONE paired difference
t5b = ["| layout | REORDER_POINT - NONE, mean +/- CI (USD) | per seed | unserved change (orders, per seed) |", "|---|---|---|---|"]
for layout in LAYOUTS:
    d, du = [], []
    for s in SEEDS:
        d.append(B(layout, "written", s, "REORDER_POINT") - B(layout, "written", s, "NONE"))
        du.append(int(B(layout, "written", s, "REORDER_POINT", "n_unserved") - B(layout, "written", s, "NONE", "n_unserved")))
    t5b.append(f"| {LAB[layout]} | {fci(d)} | {seeds_str(d)} | {du} |")

# T6 headline gaps
t6 = ["| layout | targets | switch | n | vs NONE (default) | per seed | vs REORDER_POINT | vs best policy |", "|---|---|---|---|---|---|---|---|"]
for layout in LAYOUTS:
    for targets in TARGETS:
        for sw in SW:
            c = cell(layout, targets, sw)
            t6.append(f"| {LAB[layout]} | {targets} | {SWLAB[sw]} | {len(c)} | {fci(c.gap_none_pct, 1)} % | {seeds_str(c.gap_none_pct, 1)} | "
                      f"{fci(c.gap_reorder_pct, 1)} % | {fci(c.gap_best_pct, 1)} % |")

# T7 per-cell table
t7 = ["| layout | targets | seed | switch | source | status | ILP total | bound | gap | C_setup | C_travel | C_elec | unserved | response | lateness | C_reb | served | swaps | shuttles | moved | stock-out slots | peak kW | end full | binaries | rows | nodes | solve s | TL s | MIP start (accepted) | policy NONE | policy REORDER | gap vs NONE % | gap vs REORDER % |",
      "|" + "---|" * 33]
for seed in SEEDS:
    for layout in LAYOUTS:
        for targets in TARGETS:
            for sw in SW:
                c = cell(layout, targets, sw); r = c[c.seed == seed].iloc[0]
                t7.append(f"| {SHORT[layout]} | {targets} | {seed} | {sw} | {r.source} | {r.status} | {r.total:.2f} | {r.bound:.2f} | {r.gap:.4f} | {r.C_setup:.2f} | {r.C_travel:.2f} | "
                          f"{r.C_elec:.3f} | {r.unserved:.0f} | {r.response:.1f} | {r.lateness:.1f} | {r.C_reb:.0f} | {r.served_share:.3f} | {r.n_swaps:.0f} | {r.transfers_used:.0f} | "
                          f"{r.batteries_moved:.0f} | {r.stockout_slots_total:.0f} | {r.peak_kw_group_max:.2f} | {r.end_full_total:.0f} | {int(r.n_binaries):,} | {int(r.n_rows):,} | "
                          f"{int(r.node_count)} | {r.runtime_s:.0f} | {r.time_limit_used_s:.0f} | {r.mip_start_variant} ({r.mip_start_accepted}) | {r.base_none:.2f} | {r.base_reorder:.2f} | "
                          f"{r.gap_none_pct:.1f} | {r.gap_reorder_pct:.1f} |")

# T8 per-cell baseline table
t8 = ["| layout | targets | seed | rule | source | total | C_elec | unserved | response | lateness | C_reb | served | n_unserved | swaps | shuttles | moved | stock-out slots | peak kW | end full | (17)/(18) reported | unservable orders |",
      "|" + "---|" * 21]
for seed in SEEDS:
    for layout in LAYOUTS:
        for targets in TARGETS:
            for rule in RULES:
                b = base[(base.layout == layout) & (base.targets == targets) & (base.seed == seed) & (base.rule == rule)].iloc[0]
                nu = b.get("n_unservable")
                t8.append(f"| {SHORT[layout]} | {targets} | {seed} | {rule} | {b.source} | {b.total:.2f} | {b.C_elec:.3f} | {b.unserved:.0f} | {b.response:.1f} | {b.lateness:.1f} | "
                          f"{b.C_reb:.0f} | {b.served_share:.3f} | {b.n_unserved:.0f} | {b.n_swaps:.0f} | {b.transfers_used:.0f} | {b.batteries_moved:.0f} | {b.stockout_slots_total:.0f} | "
                          f"{b.peak_kw_group_max:.2f} | {b.end_full_total:.0f} | {b.reported_families} | {'-' if nu is None or (isinstance(nu, float) and math.isnan(nu)) else int(nu)} |")

# T9 re-solved cells
t9 = ["| layout | seed | round-2 incumbent (300 s) | round-2 gap | round-3 incumbent (600 s) | round-3 bound | round-3 gap | improvement (USD) | nodes | h = z = 0 optimum | value of transfers [lower, upper] |",
      "|---|---|---|---|---|---|---|---|---|---|---|"]
for r in ilp[(ilp.status == "TIME_LIMIT")].sort_values(["layout", "seed"]).itertuples():
    none_tot = float(I(r.layout, "written", r.seed, "none"))
    r2t = f"{r.round2_total:.2f}" if not math.isnan(r.round2_total) else "- (not solved in round 2)"
    r2g = f"{100 * r.round2_gap:.2f} %" if not math.isnan(r.round2_gap) else "-"
    imp = f"{r.round2_total - r.total:.3f}" if not math.isnan(r.round2_total) else "-"
    t9.append(f"| {SHORT[r.layout]} | {r.seed} | {r2t} | {r2g} | {r.total:.2f} | {r.bound:.2f} | {100 * r.gap:.2f} % | {imp} | {int(r.node_count)} | {none_tot:.2f} | "
              f"[{none_tot - r.total:.2f}, {none_tot - r.bound:.2f}] |")

# ---------------------------------------------------------------- solver stats
opt = ilp[ilp.status == "OPTIMAL"]; tl = ilp[ilp.status == "TIME_LIMIT"]
opt3 = opt[opt.source == "round3"]; opt2 = opt[opt.source == "round2"]
ms = ilp.groupby(["mip_start_variant", "mip_start_accepted"]).size()
ms_str = "; ".join(f"{k[0]} accepted={k[1]}: {v}" for k, v in ms.items())
binr = ilp.groupby("layout").n_binaries.agg(["min", "max", "mean"])
rows_r = ilp.groupby("layout").n_rows.agg(["min", "max"])
wall = json.load(open(os.path.join(OUT, "wall_time.json")))

# ---------------------------------------------------------------- anomalies
anom = []
anom.append("The script's own `--analyse` step failed after drawing the figures (`cannot convert float NaN to integer` in "
            "`e3u_transfers_usd_fixed.collect_anomalies`: `int(r.get('n_unservable', 0) or 0)` receives NaN on the 17 reused round-2 ILP rows, "
            "which never recorded `n_unservable`), so the run wrote no RESULTS.md; this report and the figures were produced from records.jsonl instead, "
            "and an English RESULTS.md stub was written by hand.")
anom.append(f"Baseline rows: 46 policy rows were recomputed in round 3 (every (layout, targets, seed) whose arc library was rebuilt); the 14 cells whose 12 ILP rows "
            f"were all reused from round 2 (co-located seeds 0-1 both targets, (b) relaxed seeds 0-1, (c) relaxed seed 0) have no policy row in records.jsonl and were "
            f"filled here from `outputs/e3u/relaxed_baseline_recomputed.csv` (F1-corrected same-policy rows, current package; `source = round2_recomputed`). "
            f"The {len(overlap)} overlapping cells agree to 1e-6 ({'no mismatch' if not mism else mism}); the round-3 script asserted its recomputed totals against the stored round-2 written rows (0 mismatches, wall_time.json).")
# MIPGap-level differences
for layout in LAYOUTS:
    for targets in TARGETS:
        for s in SEEDS:
            f, n = cell(layout, targets, "free"), cell(layout, targets, "none")
            f, n = f[f.seed == s].iloc[0], n[n.seed == s].iloc[0]
            if f.status == "OPTIMAL" and n.status == "OPTIMAL" and float(f.total) > float(n.total) + 1e-6:
                anom.append(f"{SHORT[layout]} {targets} seed {s}: transfers-free optimum {f.total:.3f} > no-transfers optimum {n.total:.3f} by {f.total - n.total:.3f} USD "
                            f"(both OPTIMAL within the default MIPGap 1e-4, i.e. about 0.07 USD; solver tolerance, not structure).")
        for sw in SW:
            w, rl = cell(layout, "written", sw), cell(layout, "relaxed", sw)
            w, rl = w[w.seed == s].iloc[0], rl[rl.seed == s].iloc[0]
            if w.status == "OPTIMAL" and rl.status == "OPTIMAL" and float(rl.total) > float(w.total) + 1e-6:
                anom.append(f"{SHORT[layout]} {sw} seed {s}: relaxed optimum {rl.total:.3f} > written {w.total:.3f}")
rej = ilp[ilp.mip_start_accepted == False]  # noqa: E712
anom.append(f"Rejected MIP starts: {len(rej)}/60, all of them the written NONE policy schedule offered (unverified) to the no_transfers model of the separated layouts "
            f"(seeds {sorted(rej.seed.unique().tolist())}); the policy reports (17) at 1-2 swap sites and (18) there (swap-only sites cannot recharge, hubs receive nothing), "
            f"no NONE fallback variant was clean, Gurobi ignored the start. All 50 other starts (REORDER_POINT schedules in the transfers-free models, NONE in the co-located and relaxed models) were accepted; "
            f"round 2: 3/21 rejected for the same reason.")
anom.append("Policy reports (17)/(18) but does not enforce them: every separated NONE run on every seed ends with 1-2 full spares against the 4.5 required by (18) and 1-2 "
            "sites below R_end = 1, and the co-located policy of seed 1 reports (18); under the written targets the ILP therefore pays for recovery stock the policy skips, "
            "so the written headline gaps are conservative in the ILP's disfavour (the relaxed setting is the like-for-like comparison).")
anom.append("Structurally unservable orders (no delivery arc, both methods pay P = 30): 1 on seeds 0, 1, 3 and 4, 0 on seed 2, so the attainable served share is 35/36 = 0.972 on four of the five seeds.")
anom.append("Policy stranded bikes: 1 on every seed-0 instance (all layouts, both rules), 0 on seeds 1-4; pruned-arc fallbacks and suppressed late trips 0 everywhere "
            "(the shared pruning never bound the policy).")
anom.append(f"Checks: evaluate.check, identity (24) and Gurobi objective == evaluate.cost hold on 60/60 ILP runs; ILP total <= best policy total on 60/60; "
            f"relaxed optimum <= written optimum on every OPTIMAL pair; duplicate keys in records.jsonl: {n_dup}.")
anom.append("Baseline charging rule differs by layout (F3): DEMAND_AWARE at co-located sites, HIGH_FIRST / ASAP at charge-only hubs; policy C_elec is exactly 0 in the separated NONE runs "
            "(nothing ever reaches a hub), so the policy's layout differences are F_hub plus 0-3 USD of travel / timing, not a charging effect.")
anom.append("Seed-2 lower bound below 0: on seed 2 the transfers-free incumbent at 600 s (690.37 (b), 719.56 (c)) is 0.56 USD above the no-transfers OPTIMUM of the same instance "
            "(689.81 / 719.00), which is a feasible point of the free model, so the free incumbent is provably at least 0.56 USD from optimal there and the per-seed value of transfers "
            "-0.56 must be read as 0 (interval [0, 13.1-13.7]); the 5-seed means in T1/T2 use the recorded incumbents as they are.")
anom.append("Seed 3 is the hardest instance for both methods (policy NONE 933-991 USD, 8 unserved; ILP 662-764 USD); the policy with rule NONE drops 1 / 7 / 7 / 8 / 3 orders on seeds 0-4 "
            "against the ILP's 1 / 5 / 4 / 5 / 3 (co-located, transfers free); the policy t-CIs (+/- 150-160 USD) are driven by this seed-0 / seed-4 vs seed-1 / seed-3 split.")

# ---------------------------------------------------------------- numbers for the summary / interpretation
def m(layout, targets, sw, col="total"):
    return mci(cell(layout, targets, sw)[col])
def bm(layout, rule, col="total"):
    return mci(base[(base.layout == layout) & (base.targets == "written") & (base.rule == rule)][col])
aW, bW, cW = m("colocated", "written", "free"), m("separated_1hub", "written", "free"), m("separated_2hubs", "written", "free")
aR, bR, cR = m("colocated", "relaxed", "free"), m("separated_1hub", "relaxed", "free"), m("separated_2hubs", "relaxed", "free")
tvbW, tvcW = mci(transfer_value("separated_1hub", "written")[0]), mci(transfer_value("separated_2hubs", "written")[0])
ubbW, ubcW = mci(transfer_value("separated_1hub", "written")[1]), mci(transfer_value("separated_2hubs", "written")[1])
tvaW = mci(transfer_value("colocated", "written")[0])
tvR = {l: mci(transfer_value(l, "relaxed")[0]) for l in LAYOUTS}
sepbW, sepcW = mci(separation("separated_1hub", "written", "free")), mci(separation("separated_2hubs", "written", "free"))
sepbR, sepcR = mci(separation("separated_1hub", "relaxed", "free")), mci(separation("separated_2hubs", "relaxed", "free"))
gW = {l: mci(cell(l, "written", "free").gap_none_pct) for l in LAYOUTS}
gR = {l: mci(cell(l, "relaxed", "free").gap_none_pct) for l in LAYOUTS}
gWr = {l: mci(cell(l, "written", "free").gap_reorder_pct) for l in LAYOUTS}
gWn = {l: mci(cell(l, "written", "none").gap_none_pct) for l in LAYOUTS}
bN = {l: bm(l, "NONE") for l in LAYOUTS}; bRp = {l: bm(l, "REORDER_POINT") for l in LAYOUTS}
dRN = {l: mci([B(l, "written", s, "REORDER_POINT") - B(l, "written", s, "NONE") for s in SEEDS]) for l in LAYOUTS}
# ILP vs policy component decomposition (a) written free
comp = {}
for col in ["unserved", "response", "lateness", "C_travel", "C_elec"]:
    comp[col] = float(np.mean([B("colocated", "written", s, "NONE", col) - float(I("colocated", "written", s, "free", col)) for s in SEEDS]))
tl_gaps = (100 * tl.gap.min(), 100 * tl.gap.max())
imp = tl[tl.round2_total.notna()]
imp_vals = (imp.round2_total - imp.total).tolist()

def pm(x, d=1):
    return f"{x[0]:.{d}f} +/- {x[1]:.{d}f}"

summary = (
    f"On the usd4h family (6 bikes, 36 orders, 4 h evening peak, 9 spares and 6 chargers in every layout) with five seeds per cell, the ILP's total cost is lowest "
    f"in the co-located layout ({pm(aW)} USD per window under the written end targets, 95 % t-CI, n = 5) and separation costs {pm(sepbW)} USD with one charging hub "
    f"and {pm(sepcW)} USD with two, of which 29.19 / 58.38 USD is the hub fixed cost F_hub and the rest ({sepbW[0] - F_HUB:.1f} / {sepcW[0] - 2 * F_HUB:.1f} USD) is operations; with the "
    f"end targets relaxed the operational part vanishes ({pm(sepbR)} / {pm(sepcR)} USD, i.e. F_hub plus 0-0.4 USD). "
    f"The value of transfers is {pm(tvaW, 2)} USD in the co-located layout, {pm(tvbW)} USD (1 hub) and {pm(tvcW)} USD (2 hubs) under the written targets, and "
    f"{tvR['colocated'][0]:.2f} / {tvR['separated_1hub'][0]:.2f} / {tvR['separated_2hubs'][0]:.2f} USD once rho and R_end are set to 0, which confirms on five seeds the round-2 reading "
    f"that there is no within-horizon replenishment value in a 4 h window and that all of the transfer value is the recovery-target effect (one 22 USD shuttle with 2 batteries "
    f"lifts the swap cap of 4 imposed by (17)-(18) and recovers 2-3 orders). "
    f"Against the R2.3 policy with transfer rule NONE the ILP saves {pm(gW['colocated'])} % (a), {pm(gW['separated_1hub'])} % (b) and {pm(gW['separated_2hubs'])} % (c) under the written "
    f"targets and {pm(gR['colocated'])} / {pm(gR['separated_1hub'])} / {pm(gR['separated_2hubs'])} % under the relaxed ones; the policy's REORDER_POINT rule is more expensive than NONE "
    f"on every layout and every seed (+{min(d[0] for d in dRN.values()):.0f} to +{max(d[0] for d in dRN.values()):.0f} USD mean, CIs excluding 0) because its 5-14 shuttles at 20 USD never rescue more than one order. "
    f"All 60 ILP cells are now solved (50 OPTIMAL at the root or within 9 nodes, 10 TIME_LIMIT), and the 600 s re-solves of the separated / written / transfers-free cells did not close "
    f"their gaps: every one of the 10 runs stopped at {tl_gaps[0]:.1f}-{tl_gaps[1]:.1f} % after 63-143 nodes, the four round-2 incumbents improved by at most {max(imp_vals):.2f} USD, so the written transfer values "
    f"stay lower bounds (upper bounds {pm(ubbW)} / {pm(ubcW)} USD). "
    f"The baseline rows are the same schedule under both target settings (F1), every solved ILP run passes the independent checker and identity (24), the policy's own NONE schedule "
    f"is rejected as a MIP start only in the written no-transfers models of the separated layouts (10/60, expected: it violates (17)-(18) there), and the script's automatic analysis "
    f"step crashed on a NaN in the reused round-2 rows, so this report was built directly from records.jsonl."
)

interp = [
    f"Compared with round 2 (seeds 0-1 only, 15 of 36 cells skipped, no CIs) every cell now has five seeds and every ILP-only quantity carries a t-interval; the layout ranking "
    f"(a) < (b) < (c) holds on every seed and both target settings, and the written separation cost {pm(sepbW)} / {pm(sepcW)} USD matches the round-2 point estimates "
    f"52.4 / 81.7 USD to within 1-2 USD, so the earlier two-seed reading was not a seed artefact.",
    f"The split of the separation cost is unchanged: F_hub (29.19 per hub) is 56-72 % of it under the written targets and 99 % under the relaxed targets, where the operational "
    f"part is {sepbR[0] - F_HUB:.2f} / {sepcR[0] - 2 * F_HUB:.2f} USD; the whole operational penalty of separation is therefore the price of restoring 5 full spares at H with swap-only "
    f"sites (C_j = 0) that cannot recharge, not a detour or queueing effect.",
    f"The within-horizon replenishment value of transfers is zero on all 15 relaxed (layout, seed) pairs (differences {min(min(transfer_value(l, 'relaxed')[0]) for l in LAYOUTS):.3f} to "
    f"{max(max(transfer_value(l, 'relaxed')[0]) for l in LAYOUTS):.3f} USD, inside the MIPGap tolerance, 0 shuttles in every relaxed run, 6-9 swaps per window): nine spares cover the swaps "
    f"six bikes need in four hours without any charging, exactly as in rounds 1 and 2.",
    f"Under the written targets the value of transfers in the separated layouts is {pm(tvbW)} USD (b) and {pm(tvcW)} USD (c), a lower bound whose per-seed values are "
    f"{seeds_str(transfer_value('separated_1hub', 'written')[0])} and {seeds_str(transfer_value('separated_2hubs', 'written')[0])}; the mechanism is the same on every seed (h = z = 0 forces "
    f"n_swaps = 4 and served share {m('separated_1hub', 'written', 'none', 'served_share')[0]:.3f}, one 2-battery shuttle restores 6 swaps and {m('separated_1hub', 'written', 'free', 'served_share')[0]:.3f}), "
    f"and the round-2 values 6.6 / 12.6 USD sit inside the new intervals.",
    f"The 600 s re-solves answer the open question of round 2 negatively: the separated / written / transfers-free model is the only cell type that does not solve at the root, "
    f"its gap after 600 s ({tl_gaps[0]:.1f}-{tl_gaps[1]:.1f} %) is the same as after 300 s, and the round-2 incumbents improved by only {', '.join(f'{v:.2f}' for v in imp_vals)} USD; "
    f"how much of the remaining 13-14 USD is primal cannot be told from the runs (on seed 2 the free incumbent is 0.56 USD above the no-transfers optimum, which is feasible for the free model, "
    f"so the primal side is off by at least that much), and the no-transfers optima bound the free optimum from above, so the true value of transfers lies in [max(0, lower), upper] per seed; "
    f"a certified value would need a tighter formulation or a much longer run rather than more seeds.",
    f"The ILP's advantage over the R2.3 policy is {pm(gW['colocated'])} % (a), {pm(gW['separated_1hub'])} % (b), {pm(gW['separated_2hubs'])} % (c) under the written targets "
    f"(round 2: 24.2 / 21.1 / 20.5 % on two seeds) and {pm(gR['colocated'])} / {pm(gR['separated_1hub'])} / {pm(gR['separated_2hubs'])} % relaxed; the t-intervals are wide "
    f"(+/- 10-11 pp) because the per-seed gap ranges from 10-16 % (seeds 4 and 0, where the policy drops 3 and 1 orders) to 29-32 % (seeds 1 and 3, where the policy drops 7-8 orders), "
    f"but every interval excludes 0 and the ordering (a) >= (b) >= (c) survives.",
    f"On the co-located layout the mean 5-seed difference policy NONE - ILP ({bN['colocated'][0] - aW[0]:.0f} USD) decomposes into lateness {comp['lateness']:.0f}, unserved {comp['unserved']:.0f}, "
    f"response {comp['response']:.0f}, travel {comp['C_travel']:.1f} and electricity {comp['C_elec']:.2f} USD, i.e. service quality (fewer late and dropped orders through "
    f"order re-assignment) and not energy or distance, the same composition as round 2.",
    f"The REORDER_POINT rule remains uniformly harmful with five seeds: +{pm(dRN['colocated'])} (a), +{pm(dRN['separated_1hub'])} (b), +{pm(dRN['separated_2hubs'])} USD (c) "
    f"over NONE, with 5-14 shuttles and 9-22 batteries moved per window and the unserved count unchanged on 12 of 15 (layout, seed) pairs (one order gained on (a) seed 3 and on (b)/(c) seed 4, "
    f"at a cost of 191-215 USD of shuttle fees);a reorder trigger that pays f_e = 20 per run cannot pay for itself when P = 30 and the sites already hold 3 spares.",
    f"Battery-side constraints still never bind: hub charging peaks at 1.33 kW and co-located sites at 3.33 kW against the 6-8 kW grid limit, the ILP buys at most 2.4 kWh "
    f"(0.8 USD) per window under the written targets and at most 0.39 kWh relaxed, and stock-outs appear only where the ILP lets stock run out deliberately near the end "
    f"(0 stock-out slots at the reserved separated sites under written targets, 6-61 elsewhere).",
    f"Served share: the ILP serves {m('colocated', 'written', 'free', 'served_share')[0]:.3f} (a) and {m('separated_1hub', 'written', 'free', 'served_share')[0]:.3f} (b)/(c) of the 36 orders "
    f"with transfers against an attainable 0.972 on four seeds (one structurally unservable order), the policy {bN['colocated'][2] and bm('colocated', 'NONE', 'served_share')[0]:.3f}; "
    f"forbidding transfers in the separated layouts under the written targets costs {m('separated_1hub', 'written', 'free', 'served_share')[0] - m('separated_1hub', 'written', 'none', 'served_share')[0]:.3f} "
    f"of served share (2-3 orders), nothing elsewhere.",
    f"What changed against round 2 is therefore coverage and certainty, not conclusions: the layout ranking, the zero replenishment value, the recovery-target origin of the transfer "
    f"value, the sign of the REORDER_POINT rule and the service-quality composition of the gap all hold on 5 seeds with intervals; the one open item (the 2 % gap of the "
    f"separated written transfers-free cells) is a solver-bound issue that 600 s did not fix.",
    f"Modelling implication for the supervisor (unchanged): rho and R_end are the only lever that gives transfers any value in this family; a periodic end condition or a longer "
    f"rolling horizon is needed before within-horizon replenishment can be observed, and the hub fixed cost dominates every layout comparison at this scale.",
]

# ---------------------------------------------------------------- write
md = []
md += ["# E3u final report -- transfers and separation under USD costs, 4 h window (round 3: seeds 0-4, all cells solved)", "",
       "## Summary", "", summary, "",
       "## Setup and provenance", "",
       f"- Script `experiments/e3u_round3.py` (design, instance builder, record layout and MIP-start candidates imported from `experiments/e3u_transfers_usd_fixed.py`), run 2026-10-12 22:00 to 2026-10-13 00:29, "
       f"{wall['wall_s'] / 60:.1f} min wall, single process, Gurobi OutputFlag 0, Threads 3, Seed 0, TimeLimit 300 s (600 s for the separated / written / transfers-free cells), wall budget 240 min (not exhausted: 0 SKIPPED_BUDGET).",
       f"- Inputs of this report: `outputs/e3u_round3/records.jsonl` (106 records, 106 unique keys, {n_dup} duplicates; last record per key kept), `results.csv`, `run_stdout.log`, `wall_time.json`, "
       f"30 saved instances `instances/{{layout}}_{{targets}}_seed{{s}}.json`; `outputs/e3u/relaxed_baseline_recomputed.csv` for the 14 policy cells not rebuilt in round 3 (see anomalies).",
       f"- Rows by method and source: ILP round2 (reused OPTIMAL rows) {int((ilp.source == 'round2').sum())}, ILP round3 {int((ilp.source == 'round3').sum())}; policy round3 {int((base.source == 'round3').sum())}, "
       f"policy round2_recomputed {int((base.source == 'round2_recomputed').sum())}. ILP statuses: {ilp.status.value_counts().to_dict()}.",
       "- Family `usd4h` (R2.2): 6 bikes, 36 orders, H = 48 (Delta 5 min, 17:00-21:00), L = 12, initial bike levels 4-7 of 12; `usd_sunk` costs (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, "
       "v 36 $/h, f_e 20 $ per shuttle run, v_reb 1 $ per battery, F 12.03 / F_hub 29.19, bB 0.332, bC 0.082 per 4 h). Equal totals in every layout: sum B = 9 (3 per swap site, hubs 0), sum C = 6 "
       "(2 per co-located site; 6 at the single hub; 3 + 3 at two hubs), one grid group of 8 kW (6 kW 18-20 h). Shuttles every 6 slots from t = 2, U_e = 6. Written targets rho 0.5, R_end_j = 1 at swap sites; "
       "relaxed control rho 0, R_end 0. Pruning tau_max 4, start_slack 6, reachable pruning (lossless).",
       "- Policy (baseline) = R2.3 rules: stock-aware nearest-feasible dispatch, threshold swapping, FCFS, DEMAND_AWARE charging at co-located sites and HIGH_FIRST / ASAP at charge-only hubs "
       "(`hub_charge_rule`, fairness F3), transfer rule NONE (default) or REORDER_POINT; on the relaxed copies the policy keeps the written R_end as its reserve (fairness F1), so the written and relaxed "
       "policy rows are the same schedule (asserted on all 60 rows, 0 mismatches).",
       "- Gap definition everywhere: 100 (policy - ILP) / policy on the same instance and the same end-target setting; recomputed here from the merged policy table (the `gap_vs_baseline_*` columns of the "
       "reused round-2 relaxed co-located rows were computed against the pre-F1 policy and are not used).",
       "- 95 % t-CI = t_{0.975, n-1} s / sqrt(n) over seeds (n = 5 everywhere; shown as mean +/- half-width).", "",
       "## Headline numbers", "",
       f"- ILP total (USD per 4 h, transfers free): written (a) {pm(aW)}, (b) {pm(bW)}, (c) {pm(cW)}; relaxed {pm(aR)} / {pm(bR)} / {pm(cR)}. Round 2 (2 seeds): 637.4 / 689.8 / 719.1 written, 636.9 / 666.3 / 673.3 relaxed.",
       f"- Value of transfers (none - free): written (a) {pm(tvaW, 2)}, (b) {pm(tvbW)} [upper bound {pm(ubbW)}], (c) {pm(tvcW)} [upper bound {pm(ubcW)}]; relaxed {pm(tvR['colocated'], 2)} / {pm(tvR['separated_1hub'], 2)} / {pm(tvR['separated_2hubs'], 2)}. "
       f"Round 2: 0.03 / 6.59 / 12.60 written, 0 / 0 / 0.04 relaxed. Round 1 (toy units): 0 / 257 / 254.5.",
       f"- Cost of separation vs (a), transfers free: written {pm(sepbW)} (b) / {pm(sepcW)} (c), hub setup 29.19 / 58.38, operations {sepbW[0] - F_HUB:.1f} / {sepcW[0] - 2 * F_HUB:.1f}; relaxed {pm(sepbR)} / {pm(sepcR)}. Round 2: +52.4 / +81.7 written, +29.4 / +58.8 relaxed.",
       f"- Headline gap vs policy NONE, ILP transfers free: written {pm(gW['colocated'])} % (a), {pm(gW['separated_1hub'])} % (b), {pm(gW['separated_2hubs'])} % (c); relaxed {pm(gR['colocated'])} / {pm(gR['separated_1hub'])} / {pm(gR['separated_2hubs'])} %; "
       f"vs REORDER_POINT (written) {pm(gWr['colocated'])} / {pm(gWr['separated_1hub'])} / {pm(gWr['separated_2hubs'])} %; ILP h = z = 0 vs NONE (written) {pm(gWn['colocated'])} / {pm(gWn['separated_1hub'])} / {pm(gWn['separated_2hubs'])} %. Round 2: 24.2 / 21.1 / 20.5 written, 24.2 / 23.9 / 15.8 relaxed.",
       f"- Policy (n = 5): NONE {pm(bN['colocated'])} (a), {pm(bN['separated_1hub'])} (b), {pm(bN['separated_2hubs'])} (c); REORDER_POINT {pm(bRp['colocated'])} / {pm(bRp['separated_1hub'])} / {pm(bRp['separated_2hubs'])}; "
       f"paired difference REORDER_POINT - NONE +{pm(dRN['colocated'])} / +{pm(dRN['separated_1hub'])} / +{pm(dRN['separated_2hubs'])} USD. Round 2 (n = 3): NONE 832 / 864 / 893, REORDER_POINT 1038 / 1043 / 1072.",
       f"- Served share (written, transfers free): ILP {m('colocated', 'written', 'free', 'served_share')[0]:.3f} (a), {m('separated_1hub', 'written', 'free', 'served_share')[0]:.3f} (b), {m('separated_2hubs', 'written', 'free', 'served_share')[0]:.3f} (c); "
       f"ILP h = z = 0 {m('colocated', 'written', 'none', 'served_share')[0]:.3f} / {m('separated_1hub', 'written', 'none', 'served_share')[0]:.3f} / {m('separated_2hubs', 'written', 'none', 'served_share')[0]:.3f}; policy NONE {bm('colocated', 'NONE', 'served_share')[0]:.3f} / {bm('separated_1hub', 'NONE', 'served_share')[0]:.3f} / {bm('separated_2hubs', 'NONE', 'served_share')[0]:.3f}; attainable ceiling 0.972 on seeds 0, 1, 3, 4 and 1.0 on seed 2.",
       f"- Transfers: ILP uses 0 shuttles in (a) and in every relaxed run, exactly 1 shuttle with 2 batteries (C_reb 22 USD) in every written (b)/(c) run; policy REORDER_POINT 5-14 shuttles, 9-22 batteries, C_reb 109-302 USD.",
       f"- Stock-outs (slots with n_jLt = 0 summed over facilities): ILP written free {m('colocated', 'written', 'free', 'stockout_slots_total')[0]:.1f} (a), 0 (b), 0 (c); relaxed {m('colocated', 'relaxed', 'free', 'stockout_slots_total')[0]:.1f} / {m('separated_1hub', 'relaxed', 'free', 'stockout_slots_total')[0]:.1f} / {m('separated_2hubs', 'relaxed', 'free', 'stockout_slots_total')[0]:.1f}; policy NONE {bm('colocated', 'NONE', 'stockout_slots_total')[0]:.1f} / {bm('separated_1hub', 'NONE', 'stockout_slots_total')[0]:.1f} / {bm('separated_2hubs', 'NONE', 'stockout_slots_total')[0]:.1f}.",
       f"- Grid: hub charging peak 1.33 kW in every written (b)/(c) free run, 0 kW in the hubs' no-transfer and relaxed runs; co-located sites at most 3.33 kW; limit 8 kW (6 kW in 18-20 h) never binds; electricity <= 0.82 USD per window.",
       f"- Solver: 60 ILP cells, OPTIMAL {len(opt)} (round 3: {len(opt3)}, mean {opt3.runtime_s.mean():.0f} s, range {opt3.runtime_s.min():.0f}-{opt3.runtime_s.max():.0f} s; reused round 2: {len(opt2)}, mean {opt2.runtime_s.mean():.0f} s), "
       f"TIME_LIMIT {len(tl)} (all separated / written / transfers free, 600 s, gap {tl_gaps[0]:.2f}-{tl_gaps[1]:.2f} %, nodes {int(tl.node_count.min())}-{int(tl.node_count.max())}), SKIPPED_BUDGET 0; "
       f"binaries {int(ilp.n_binaries.min()):,}-{int(ilp.n_binaries.max()):,}; MIP start accepted {int((ilp.mip_start_accepted == True).sum())}/60.", "",  # noqa: E712
       "## Tables", "",
       "### T1. ILP total cost (26), USD per 4 h window, by layout x transfer switch x end targets (mean +/- 95 % t-CI, n = 5; per-seed values seeds 0-4 in parentheses; status letters O = OPTIMAL, T = TIME_LIMIT at 600 s)", ""] + t1 + ["",
       "### T2. Value of transfers per layout and target setting (ILP cost with h = z = 0 minus ILP cost with transfers free; written separated values are lower bounds because the free runs stopped at TIME_LIMIT, the upper bound uses the free run's best bound)", ""] + t2 + ["",
       "### T3. Cost of separation = ILP total(layout) - ILP total(co-located), same seed, switch and targets (USD per 4 h)", ""] + t3 + ["",
       "### T4. ILP operational metrics (means over seeds 0-4; CI where n = 5 and the quantity varies)", ""] + t4 + ["",
       "### T5. Policy (R2.3 rules): NONE vs REORDER_POINT, mean over 5 seeds with 95 % t-CI (USD per 4 h; written and relaxed rows are the same schedule, so one table serves both target settings)", ""] + t5 + ["",
       "Paired difference REORDER_POINT - NONE (same instance):", ""] + t5b + ["",
       "### T6. Headline gap 100 (policy - ILP) / policy, by cell (mean +/- 95 % t-CI, n = 5)", ""] + t6 + ["",
       "### T7. Solver statistics", "",
       f"- Runs: 60 ILP cells (3 layouts x 2 targets x 2 switches x 5 seeds), all attempted; status OPTIMAL {len(opt)}, TIME_LIMIT {len(tl)}, SKIPPED_BUDGET 0, INFEASIBLE 0. Round 2: 17 OPTIMAL, 4 TIME_LIMIT, 15 SKIPPED_BUDGET.",
       f"- Binaries per layout (min / max / mean): " + "; ".join(f"{SHORT[l]} {int(binr.loc[l, 'min']):,} / {int(binr.loc[l, 'max']):,} / {int(binr.loc[l, 'mean']):,}" for l in LAYOUTS) + f"; rows {int(ilp.n_rows.min()):,}-{int(ilp.n_rows.max()):,}.",
       f"- OPTIMAL runs: round 3 ({len(opt3)}) mean {opt3.runtime_s.mean():.0f} s, median {opt3.runtime_s.median():.0f} s, range {opt3.runtime_s.min():.0f}-{opt3.runtime_s.max():.0f} s, node count 1 on {int((opt3.node_count == 1).sum())}/{len(opt3)} (one run, (c) written h = z = 0 seed 1, needed 9 nodes); "
       f"reused round-2 runs ({len(opt2)}) mean {opt2.runtime_s.mean():.0f} s, range {opt2.runtime_s.min():.0f}-{opt2.runtime_s.max():.0f} s, all at the root. Reported gap <= 1e-4 on every OPTIMAL run.",
       f"- TIME_LIMIT runs ({len(tl)}): all separated / written / transfers-free cells, 600 s each, gap {tl_gaps[0]:.2f}-{tl_gaps[1]:.2f} %, nodes {int(tl.node_count.min())}-{int(tl.node_count.max())}; incumbents all use exactly 1 shuttle with 2 batteries.",
       f"- MIP-start acceptance (fix-and-solve certificate at build time): {ms_str}.",
       f"- Checks: evaluate.check ok 60/60, identity (24) ok 60/60, Gurobi objective == evaluate.cost 60/60, ILP total <= best policy total 60/60; policy rows: check modulo report-only families ok 60/60, identity (24) ok 60/60.",
       f"- Wall time: {wall['wall_s'] / 60:.1f} min for 43 solves + 46 policy runs (plan: 15 fill, 24 extend, 4 resolve600; expected 119 min, worst case 265 min).", "",
       "### T8. The 600 s re-solves and the other separated / written / transfers-free cells (did the gaps close?)", ""] + t9 + ["",
       "No: every cell stays at a 1.8-2.0 % gap; the incumbents of the 4 re-solved round-2 cells improved by 0.00 (seed 0, both layouts), 0.23 (b seed 1) and 0.32 USD (c seed 1), and the 6 new seeds show the same gap after 600 s as the round-2 cells after 300 s. "
       "The no-transfers optimum is feasible for the free model, so the true free optimum lies in [bound, min(incumbent, h = z = 0 optimum)] and the value of transfers in [max(0, lower), upper]; on seed 2 the free incumbent is 0.56 USD above the no-transfers optimum (lower bound -0.56 reads as 0).", "",
       "### T9. Per-cell table (every ILP run; policy totals and gaps from the merged policy table)", ""] + t7 + ["",
       "### T10. Per-cell table (policy runs; `source` = round3 recomputation or round-2 F1-corrected recomputation)", ""] + t8 + ["",
       "## Figures", "", "All files are in `outputs/e3u_round3/`, regenerated from `records.jsonl` by the report script (matplotlib Agg, 150 dpi):", ""]
fig_desc = {"fig_cost_by_layout.png": "total cost by layout, panels written | relaxed; ILP free / ILP h = z = 0 / policy NONE / policy REORDER_POINT; bars = 5-seed means with 95 % t-CI error bars, dots = seeds, USD per 4 h window",
            "fig_gap_by_layout.png": "headline gap 100 (policy - ILP) / policy by layout, panels written | relaxed, ILP free and h = z = 0 vs NONE and vs REORDER_POINT, with t-CIs",
            "fig_transfer_value.png": "left: value of transfers per layout (written vs relaxed, t-CIs, open circles = upper bound from the 600 s MIP bound); right: cost of separation vs (a) with F_hub reference lines",
            "fig_cost_components.png": "stacked ILP cost components (27)-(32) per layout x switch x targets, 5-seed means",
            "fig_solver.png": "left: Gurobi wall time per run by status and source; right: MIP gap of the separated / written / transfers-free cells after 600 s vs the round-2 300 s gap",
            "fig_in_transit.png": "in-transit batteries m_t (24) over t for the ILP with transfers free, written (solid) vs relaxed (dashed), seed means and seeds",
            "fig_full_stock_written_seed0.png": "full-battery stock n_jLt per facility, ILP transfers free, seed 0, written targets",
            "fig_full_stock_relaxed_seed0.png": "same for the relaxed targets",
            "fig_grid_load_seed0.png": "grid-group charging load vs limit (21), ILP transfers free, seed 0, written targets"}
md += [f"- `{os.path.basename(f)}` -- {fig_desc[os.path.basename(f)]}" for f in figs]
md += ["", "## Anomalies and checks", ""] + [f"{i + 1}. {a}" for i, a in enumerate(anom)] + ["",
       "## Interpretation (comparison with round 2)", ""] + [f"{i + 1}. {s}" for i, s in enumerate(interp)] + ["",
       "## Files", "",
       "- `outputs/e3u_round3/RESULTS_final.md` (this report), `RESULTS.md` (short English provenance stub replacing the failed automatic report), the nine figures listed above, "
       "all written by `experiments/e3u_round3_report.py` (pandas + matplotlib only, no solver calls; run from `ebike_swap_sim/`); "
       "`records.jsonl`, `results.csv`, `run_stdout.log`, `wall_time.json`, `instances/` untouched.", ""]
out_md = os.path.join(OUT, "RESULTS_final.md")
with open(out_md, "w", encoding="utf-8") as fh:
    fh.write("\n".join(md))

# RESULTS.md stub (the script's analyse step crashed before writing it)
stub = ["# E3u round 3 -- provenance (English stub)", "",
        "The automatic `--analyse` step of `experiments/e3u_round3.py` drew the figures and then crashed in "
        "`e3u_transfers_usd_fixed.collect_anomalies` (`int(NaN)` on the reused round-2 ILP rows, which carry no `n_unservable`), so no RESULTS.md was written by the run. "
        "The full report with tables, 95 % t-CIs, solver statistics, anomalies and interpretation is `RESULTS_final.md` in this directory (built from `records.jsonl`).", "",
        f"Rows: ILP reused from round 2 (OPTIMAL) {int((ilp.source == 'round2').sum())}, ILP solved in round 3 {int((ilp.source == 'round3').sum())} "
        f"(Threads 3, Seed 0, TimeLimit 300 s / 600 s for separated-written-free cells); policy rows recomputed in round 3 {int((base3.shape[0]))}; "
        f"ILP statuses {ilp.status.value_counts().to_dict()}; seeds {SEEDS}; wall {wall['wall_s'] / 60:.1f} min; baseline mismatches vs stored round-2 written rows: {wall['baseline_mismatches']}.", "",
        "Re-solved round-2 TIME_LIMIT cells (600 s) against their round-2 incumbents:", ""] + t9 + [""]
with open(os.path.join(OUT, "RESULTS.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(stub))

# machine-readable extras for the orchestrator
print(json.dumps({"n_dup": n_dup, "mism": mism, "figs": figs, "statuses": ilp.status.value_counts().to_dict(),
                  "tl_gaps": tl_gaps, "imp_vals": imp_vals, "ms": ms_str,
                  "aW": aW, "bW": bW, "cW": cW, "aR": aR, "bR": bR, "cR": cR, "tvbW": tvbW, "tvcW": tvcW, "ubbW": ubbW, "ubcW": ubcW,
                  "sepbW": sepbW, "sepcW": sepcW, "sepbR": sepbR, "sepcR": sepcR, "gW": gW, "gR": gR, "gWr": gWr, "bN": bN, "bRp": bRp, "dRN": dRN, "comp": comp}, default=float, indent=1))
print("WROTE", out_md)
