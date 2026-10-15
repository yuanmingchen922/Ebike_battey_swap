"""Experiment E9 -- bi-level siting of swapping / charging stations on the energy-stressed
semi-real family ``nyc4h_stress2`` (``notes/bilevel_siting_design.md`` section 6; the relaunch
family of DECISIONS "E9 relaunch decisions": 6 bikes / 36 orders / ``q0 ~ U{3..6}``; the first
attempt's ``nyc4h_stress`` stays selectable with ``--family nyc4h_stress``).

Upper level: the planner's layout (open candidates, role S / C / SC, spares B_j, chargers C_j)
under the investment budget (33a); lower level: the written E2 operations ILP with the
facilities fixed, one solve per demand scenario (seed).  Sub-commands (one output directory
``outputs/e9_bilevel/<sub>/`` each, with ``records.jsonl`` appended per run, ``results.csv``
refreshed, figures and a ``RESULTS.md``; the lower-level cache ``outputs/e9_bilevel/cache/`` is
shared by every sub-command so a layout priced once is never solved again):

* ``--validate`` (E9.1): integrated stochastic ILP (A) vs exhaustive bi-level enumeration (B)
  on a small candidate set (default L01-L04, 2 scenarios, 6 bikes, budget m = 1); the optimal
  values must coincide where (A) closes its gap and (B) has full coverage.
* ``--sweep`` (E9.2): greedy + local search (C) per budget ``m = 1..4`` (``Budget_m = m x 52,150
  USD``) on 12 candidates, seeds 0-2, 8 bikes; one integrated run (A) per budget warm-started
  from (C) for the bound; Pareto curve, maps, chosen sites.
* ``--roles`` (E9.3): (C) at ``m = 2, 3`` with the role sets {SC}, {S, SC}, {S, C, SC}.
* ``--deck`` (E9.4): the proposal deck's spin-and-adjust planner (D) vs (C) and the (A) bound.
* ``--cross`` (E9.5): every chosen layout under the lower-level ILP and the R2.3 baseline policy
  on seeds 0-4 (3 in-sample + 2 out-of-sample), regret matrices, relaxed-target control.
* ``--access`` (E9.6): (C) with the planner-only access row [U4] for ``D in {8, 12}`` blocks.

Conventions of the relaunch: the greedy starts from the best singleton by V (per-role baseline
screen), discards moves whose lower level is infeasible or serves < ``--min-served`` (0.5),
reports ``wall budget exhausted`` / ``no feasible layout`` with the status counts of the priced
layouts, records lower-level exceptions as ``ERROR`` rows, treats the access row [U4] as a repair
+ report rule (uncovered zones are listed, never enforced on the search); swap-only sites are
admissible only next to a C / SC object; the search sub-commands price layouts with reposition
targets = open sites + depots (``--reposition open_sites``, E8 convention) while ``--validate``
keeps the all-candidates template so that (A) and (B) price the same arcs.

Modes: ``--dry-run`` prints the plan (no Gurobi); ``--smoke`` runs the sub-command on the toy
siting instances (seconds) into ``outputs/e9_bilevel_smoke/``; ``--wall-budget`` seconds per
run (``SKIPPED_BUDGET`` recorded, resume by re-running).  Gurobi: ``OutputFlag 0``, ``Threads 3``,
``Seed 0``, ``TimeLimit 300 s`` per lower-level solve (600 s with charge-only hubs), 600 s for
the integrated model.  Every ILP total on the semi-real family is an upper bound on the
written optimum (``PRUNING_NYC`` moves only to candidate / depot nodes) and the geometry caveat
of R2.4 applies (synthetic grid, elevation, signals).  English only.

Run from ``ebike_swap_sim/`` with ``PYTHONPATH=.``::

    python3 experiments/e9_bilevel_siting.py --validate --dry-run
    python3 experiments/e9_bilevel_siting.py --validate --smoke
    python3 experiments/e9_bilevel_siting.py --validate
    python3 experiments/e9_bilevel_siting.py --sweep --wall-budget 36000
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ebike_swap_sim import Instance  # noqa: E402
from ebike_swap_sim import sites_nyc as S  # noqa: E402
from ebike_swap_sim import bilevel as BL  # noqa: E402
from experiments import common as C  # noqa: E402

OUT_ROOT = os.path.join(C.OUTPUT_ROOT, "e9_bilevel")
SUBS = ("validate", "sweep", "roles", "deck", "cross", "access")
TIME_LIMIT = 300.0
TIME_LIMIT_HUB = 600.0
INTEGRATED_TIME_LIMIT = 600.0
BUDGET_UNIT = 50_000.0 + 3 * 450.0 + 2 * 400.0          # 52,150 USD = Fhat + 3 bhat + 2 chat
SEARCH_SEEDS = [0, 1, 2]
EVAL_SEEDS = [0, 1, 2, 3, 4]
ROLE_SETS = {"SC_only": ("SC",), "S_SC": ("S", "SC"), "S_C_SC": ("S", "C", "SC")}
DEFAULT_FAMILY = S.STRESS2_FAMILY
MIN_SERVED_SHARE = 0.5
S_NEEDS_CHARGE = True            # DECISIONS "E9 relaunch decisions": swap-only sites only next to a C / SC object
ACCESS_D = [8, 12]
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ROLE_COLOUR = {"S": "#2a78d6", "C": "#eb6834", "SC": "#1baf7a"}
INK, INK2 = "#0b0b0b", "#52514e"
GEOMETRY_NOTE = ("Every ILP total on the semi-real family is an upper bound on the written optimum "
                 "(moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies "
                 "(real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; "
                 "elevation and signals synthetic).")


# ---------------------------------------------------------------------------
# study object
# ---------------------------------------------------------------------------
class Study:
    """Candidates, scenarios, spec, evaluator and output directory of one sub-command."""

    def __init__(self, sub: str, args: argparse.Namespace) -> None:
        self.sub = sub
        self.args = args
        self.smoke = bool(args.smoke)
        root = args.out_root or (OUT_ROOT + "_smoke" if self.smoke else OUT_ROOT)
        self.root = C.ensure_dir(root)
        self.out_dir = C.ensure_dir(os.path.join(root, sub))
        self.cache_dir = os.path.join(root, "cache")
        self.records_path = os.path.join(self.out_dir, "records.jsonl")
        self.wall = C.WallBudget(float(args.wall_budget), margin_s=60.0, min_solve_s=30.0)
        self.threads = int(args.threads)
        self.time_limit = float(args.time_limit)
        self.time_limit_hub = float(args.time_limit_hub)
        self.integrated_time_limit = float(args.integrated_time_limit)
        self.min_served = float(args.min_served)
        self.s_needs_charge = bool(S_NEEDS_CHARGE and not args.allow_s_only)
        self.access_mode = str(args.access_mode)
        # reposition targets: the search sub-commands price per-layout libraries (open sites + depots,
        # E8 convention); --validate keeps the all-candidates template so that (A) and (B) share it
        self.reposition = "all_candidates" if sub == "validate" else str(args.reposition)
        self.t0 = time.perf_counter()
        if self.smoke:
            self.family = "toy_siting"
            self.candidates = S.candidates_from_records(S.toy_base_instance(0).meta["candidates"])
            self.spec = S.TOY_SPEC
            self.budget_unit = 130.0
            self.size_menu = {"S": [(0, 0), (1, 0), (2, 0)], "C": [(0, 1), (1, 1), (2, 1)],
                              "SC": [(B, Cc) for B in (0, 1, 2) for Cc in (0, 1)]}
            self.validation_grid = BL.option_grid(self.size_menu)
            self.validation_bounds = None
            self.n_bikes = 2
            self.time_limit = min(self.time_limit, 30.0)
            self.integrated_time_limit = min(self.integrated_time_limit, 60.0)
        else:
            self.family = str(args.family)
            if self.family not in S.SITING_FAMILIES:
                raise SystemExit(f"--family must be one of {sorted(S.SITING_FAMILIES)}")
            self.candidates = S.candidate_sites()
            self.spec = S.DEFAULT_SPEC
            self.budget_unit = BUDGET_UNIT
            self.size_menu = S.SIZE_MENUS[self.family]
            self.validation_grid = list(BL.VALIDATION_GRID)
            self.validation_bounds = {"S": (1, 2, 0, 0), "SC": (1, 2, 1, 1)}
            self.n_bikes = int(args.bikes) if args.bikes else int(S.SITING_FAMILIES[self.family]["n_bikes"])
        with open(os.path.join(self.root, "candidates.json"), "w", encoding="utf-8") as fh:
            json.dump(S.candidates_to_records(self.candidates), fh, indent=1)
        pd.DataFrame(S.candidates_to_records(self.candidates)).to_csv(os.path.join(self.root, "candidates.csv"), index=False)
        self._scen: Dict[Tuple[int, int], Instance] = {}

    # -- scenarios ----------------------------------------------------------
    def scenario(self, seed: int, n_bikes: Optional[int] = None, candidates: Optional[Sequence[S.Candidate]] = None
                 ) -> Instance:
        """Base instance of ``seed`` (cached per seed, bike count and candidate subset); the
        candidate subset only changes the node set / reposition targets, never the demand."""
        nb = int(n_bikes or self.n_bikes)
        cands = list(candidates or self.candidates)
        key = (int(seed), nb, tuple(c.id for c in cands))
        if key not in self._scen:
            if self.smoke:
                self._scen[key] = S.toy_base_instance(int(seed), n_bikes=nb)
            else:
                depots = [c.node for c in self.candidates[:3]]      # always the three nyc4h busiest cells
                self._scen[key] = S.make_base_instance(int(seed), cands, family=self.family, depots=depots, n_bikes=nb)
                if self.spec is S.DEFAULT_SPEC:
                    self.spec = S.spec_from_instance(self._scen[key])
        return self._scen[key]

    def evaluator(self, seeds: Sequence[int], n_bikes: Optional[int] = None, relaxed: bool = False,
                  candidates: Optional[Sequence[S.Candidate]] = None) -> BL.LowerLevelEvaluator:
        scen = [self.scenario(s, n_bikes, candidates) for s in seeds]
        return BL.LowerLevelEvaluator(scen, self.spec, time_limit=self.time_limit, time_limit_hub=self.time_limit_hub,
                                      threads=self.threads, params=dict(C.ILP_PARAMS_R3), cache_dir=self.cache_dir,
                                      relaxed_targets=relaxed, wall=self.wall, verbose=True, reposition=self.reposition)

    def greedy_kwargs(self) -> Dict[str, Any]:
        """Relaunch conventions shared by every greedy call."""
        return {"k_screen": int(self.args.k_screen), "screen": not self.smoke, "min_served_share": self.min_served,
                "s_needs_charge": self.s_needs_charge, "access_mode": self.access_mode}

    def plan_common(self) -> Dict[str, Any]:
        return {"family": self.family, "reposition": self.reposition, "min_served_share": self.min_served,
                "s_needs_charge": self.s_needs_charge, "access_mode": self.access_mode, "n_bikes": self.n_bikes}

    def budget(self, m: Optional[float]) -> Optional[float]:
        return None if m is None else float(m) * self.budget_unit

    # -- records ----------------------------------------------------------------
    def emit(self, row: Dict[str, Any]) -> None:
        row = dict(row)
        row.setdefault("sub", self.sub)
        row.setdefault("family", self.family)
        row.setdefault("smoke", self.smoke)
        row.setdefault("source", "e9")
        C.append_jsonl(self.records_path, C.jsonable(row))
        keys = ("kind", "method", "budget_m", "layout_key", "status", "V", "served_share", "investment", "gap", "runtime_s", "error")
        print(json.dumps({k: C.jsonable(row.get(k)) for k in keys if k in row}), flush=True)

    def emit_cache_rows(self, ev: BL.LowerLevelEvaluator) -> None:
        """Copy the lower-level rows solved by this run into the sub-command's records."""
        for r in ev.new_rows:
            self.emit({"kind": "lower_level", **{k: v for k, v in r.items() if not k.startswith("_")}})
        ev.new_rows.clear()

    def refresh_csv(self) -> pd.DataFrame:
        rows = C.load_jsonl(self.records_path)
        df = C.records_to_frame(rows) if rows else pd.DataFrame()
        df.to_csv(os.path.join(self.out_dir, "results.csv"), index=False)
        return df

    def done(self, kind: str, **match: Any) -> Optional[Dict[str, Any]]:
        """Last record of ``kind`` matching ``match`` (resume)."""
        found = None
        for r in C.load_jsonl(self.records_path):
            if r.get("kind") == kind and all(r.get(k) == v for k, v in match.items()):
                found = r
        return found

    def elapsed_min(self) -> float:
        return (time.perf_counter() - self.t0) / 60.0


def layout_row(study: Study, ev: BL.LowerLevelEvaluator, lay: Optional[BL.Layout], kind: str, method: str,
               m: float, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"kind": kind, "method": method, "budget_m": m, "budget": study.budget(m),
                           "seeds": list(ev.seeds), "n_bikes": len(ev.scenarios[0].bikes),
                           "time_limit": ev.time_limit, "threads": ev.threads, "wall_min": study.elapsed_min()}
    if lay is None:
        row.update(layout_key=None, layout=None, status="NONE", V=None, served_share=None)
    else:
        row.update(layout_key=lay.key(), layout=lay.to_json(), n_open=lay.n_open, investment=lay.investment(ev.spec),
                   C_setup=lay.allocated_cost(ev.spec), n_S=lay.n_role("S"), n_C=lay.n_role("C"),
                   n_SC=lay.n_role("SC"), total_B=lay.total_B(), total_C=lay.total_C())
    row.update(extra or {})
    return row


def eval_cols(ev_out: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    cols = {f"{prefix}status": ev_out["status"], f"{prefix}V": (None if ev_out["V"] in (None, BL.INF) else ev_out["V"]),
            f"{prefix}feasible": ev_out["feasible"], f"{prefix}opex_mean": ev_out["opex_mean"],
            f"{prefix}opex": ev_out["opex"], f"{prefix}statuses": ev_out["statuses"], f"{prefix}gaps": ev_out["gaps"],
            f"{prefix}n_solves": ev_out["n_solves"], f"{prefix}n_cache_hits": ev_out["n_cache_hits"]}
    for k in ("served_share", "n_late", "kwh_purchased", "transfers_used", "stockout_slots"):
        if k in ev_out:
            cols[f"{prefix}{k}"] = ev_out[k]
    if ev_out["rows"]:
        comps = [r.get("components") for r in ev_out["rows"] if r.get("components")]
        if comps:
            for c in ("C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"):
                cols[f"{prefix}{c}"] = sum(x.get(c, 0.0) for x in comps) / len(comps)
    return cols


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def plot_map(study: Study, base: Instance, layouts: Dict[str, Optional[BL.Layout]], path: str, title: str) -> Optional[str]:
    """Candidates (ids), depots, DOHMH restaurants, instance customers and the chosen sites of
    one or more layouts (coloured by role, sized by B_j) in the rotated local frame of the box."""
    if "box" not in base.meta:
        return None
    from ebike_swap_sim import data_nyc as dn
    box = dn.StudyBox(**{k: base.meta["box"][k] for k in ("lat_min", "lat_max", "lon_min", "lon_max", "block_m", "azimuth_deg")})
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    ax.set_facecolor("#fcfcfb")
    try:
        rest = dn.restaurants_in_box(box)
        ax.scatter(rest["x"], rest["y"], s=3, color="#b5b3ab", alpha=0.5, linewidths=0, zorder=2, label=f"DOHMH restaurants ({len(rest)})")
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"restaurants not drawn: {exc}")
    corners = [(box.lat_min, box.lon_min), (box.lat_min, box.lon_max), (box.lat_max, box.lon_max), (box.lat_max, box.lon_min)]
    cp = [box.project(*c) for c in corners] + [box.project(*corners[0])]
    ax.plot([p[0] for p in cp], [p[1] for p in cp], color=INK2, linewidth=1.0, linestyle="--", zorder=3)
    cx = [box.node_xy(tuple(c))[0] for c in base.meta.get("customers", [])]
    cy = [box.node_xy(tuple(c))[1] for c in base.meta.get("customers", [])]
    ax.scatter(cx, cy, s=22, marker="^", facecolor="white", edgecolor=INK, linewidths=0.7, zorder=4, label=f"customers of seed {base.meta.get('seed')} ({len(cx)})")
    rx = [box.node_xy(tuple(r[0]))[0] for r in base.meta.get("restaurants", [])]
    ry = [box.node_xy(tuple(r[0]))[1] for r in base.meta.get("restaurants", [])]
    ax.scatter(rx, ry, s=40, marker="s", facecolor="none", edgecolor=INK, linewidths=0.8, zorder=4, label=f"restaurants used ({len(rx)})")
    for c in study.candidates:
        x, y = box.node_xy(c.node)
        ax.scatter([x], [y], s=70, marker="o", facecolor="white", edgecolor=INK2, linewidths=1.0, zorder=6)
        ax.annotate(c.id, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8, color=INK2, zorder=8)
    dx = [box.node_xy(tuple(d))[0] for d in base.meta.get("depots", [])]
    dy = [box.node_xy(tuple(d))[1] for d in base.meta.get("depots", [])]
    ax.scatter(dx, dy, s=120, marker="D", facecolor="none", edgecolor="#4a3aa7", linewidths=1.4, zorder=7, label="depots (bikes start)")
    markers = ["*", "P", "X", "h", "v"]
    for i, (name, lay) in enumerate(layouts.items()):
        if lay is None:
            continue
        for l, r, B, Cc in lay.open:
            node = next(c.node for c in study.candidates if c.id == l)
            x, y = box.node_xy(node)
            ax.scatter([x], [y], s=160 + 60 * B, marker=markers[i % len(markers)], facecolor=ROLE_COLOUR[r], edgecolor=INK,
                       linewidths=1.0, alpha=0.85, zorder=9 + i)
            ax.annotate(f"{r} B{B} C{Cc}", (x, y), xytext=(6, -12 - 9 * i), textcoords="offset points", fontsize=7,
                        color=ROLE_COLOUR[r], zorder=12)
        ax.scatter([], [], s=120, marker=markers[i % len(markers)], facecolor="#cccccc", edgecolor=INK, label=f"{name}: {lay.key()}")
    for r, col in ROLE_COLOUR.items():
        ax.scatter([], [], s=80, marker="o", facecolor=col, edgecolor=INK, label=f"role {r}")
    ax.set_xlim(-100, box.grid_nx * box.block_m + 100)
    ax.set_ylim(-100, box.grid_ny * box.block_m + 100)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m), frame rotated 29 deg (R2.4 projection)", fontsize=8, color=INK2)
    ax.set_ylabel("y (m) along the avenues", fontsize=8, color=INK2)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.set_title(title + "\n" + "candidates = circles with ids; chosen sites coloured by role, sized by B_j; synthetic grid (R2.4 caveat)",
                 fontsize=9, color=INK, loc="left")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_pareto(rows: Sequence[Dict[str, Any]], path: str, title: str = "Investment vs expected operating cost") -> str:
    fig, ax = plt.subplots(figsize=(7, 4.2))
    by_method: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        if r.get("V") is None or r.get("investment") is None:
            continue
        by_method.setdefault(str(r["method"]), []).append(r)
    for i, (mth, rs) in enumerate(sorted(by_method.items())):
        rs = sorted(rs, key=lambda r: r["investment"])
        ax.plot([r["investment"] / 1000 for r in rs], [r.get("opex_mean", r["V"] - r.get("C_setup", 0.0)) for r in rs],
                marker="o", color=PALETTE[i % len(PALETTE)], label=mth)
        for r in rs:
            ax.annotate(f"m={r.get('budget_m')}", (r["investment"] / 1000, r.get("opex_mean", r["V"] - r.get("C_setup", 0.0))),
                        xytext=(4, 4), textcoords="offset points", fontsize=7, color=INK2)
    bounds = [r for r in rows if r.get("bound") is not None and r.get("method") == "integrated"]
    if bounds:
        bounds = sorted(bounds, key=lambda r: r["budget"])
        ax.plot([r["budget"] / 1000 for r in bounds], [r["bound"] - (r.get("C_setup") or 0.0) for r in bounds],
                linestyle="--", color=INK2, label="integrated bound (minus C_setup)")
    ax.set_xlabel("investment inv(lambda), thousand USD")
    ax.set_ylabel("expected operating cost sum_s p_s OPEX_s (USD per window)")
    ax.set_title(title, fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_bars(groups: Dict[str, Dict[str, Optional[float]]], path: str, ylabel: str, title: str) -> str:
    """Grouped bars: ``groups[x_label][series] = value``."""
    xs = list(groups.keys())
    series = sorted({s for g in groups.values() for s in g})
    fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(xs) * len(series)), 4.2))
    width = 0.8 / max(1, len(series))
    for i, s in enumerate(series):
        vals = [groups[x].get(s) for x in xs]
        ax.bar([j + i * width for j in range(len(xs))], [v if v is not None else 0.0 for v in vals], width,
               color=PALETTE[i % len(PALETTE)], label=s)
        for j, v in enumerate(vals):
            if v is not None:
                ax.text(j + i * width, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks([j + 0.4 - width / 2 for j in range(len(xs))])
    ax.set_xticklabels(xs, fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_heat(matrix: pd.DataFrame, path: str, title: str) -> str:
    fig, ax = plt.subplots(figsize=(max(5, 0.9 * len(matrix.columns) + 3), max(3, 0.5 * len(matrix) + 1.5)))
    data = matrix.values.astype(float)
    im = ax.imshow(data, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, fontsize=8, rotation=20, ha="right")
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=7)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not math.isnan(data[i, j]):
                ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", fontsize=7, color=INK)
    fig.colorbar(im, ax=ax, fraction=0.03)
    ax.set_title(title, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# RESULTS.md helpers
# ---------------------------------------------------------------------------
def write_md(study: Study, title: str, sections: Sequence[Tuple[str, str]], figures: Sequence[str]) -> str:
    lines = [f"# {title}", "", f"Family `{study.family}` ({study.n_bikes} bikes); candidates `{study.root}/candidates.csv`; cache "
             f"`{study.cache_dir}`; reposition targets `{study.reposition}`; min served share {study.min_served:g}; "
             f"swap-only sites need a C / SC object: {study.s_needs_charge}; wall {study.elapsed_min():.1f} min; "
             f"Threads {study.threads}; TimeLimit {study.time_limit:.0f} s (hubs {study.time_limit_hub:.0f} s, integrated "
             f"{study.integrated_time_limit:.0f} s); Gurobi Seed 0.", "", GEOMETRY_NOTE, ""]
    for head, body in sections:
        lines += [f"## {head}", "", body, ""]
    if figures:
        lines += ["## Figures", ""] + [f"* `{os.path.relpath(f, study.out_dir)}`" for f in figures if f] + [""]
    path = os.path.join(study.out_dir, "RESULTS.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def _cell(v: Any) -> Any:
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return "inf" if math.isinf(v) else None
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(C.jsonable(v))
    return v


def table(rows: Sequence[Dict[str, Any]], cols: Sequence[str], digits: int = 3) -> str:
    if not rows:
        return "(no rows)"
    df = pd.DataFrame([{c: _cell(r.get(c)) for c in cols} for r in rows])
    return C.markdown_table(df, cols, digits)


def _fmt_layout(lay: Optional[BL.Layout]) -> str:
    return "-" if lay is None else lay.key()


def _greedy_cols(res: Dict[str, Any]) -> Dict[str, Any]:
    """Status columns of one ``greedy_local_search`` per-budget result."""
    return {"status": res["status"], "search_complete": res.get("search_complete"), "reasons": res.get("reasons"),
            "uncovered_zones": res.get("uncovered_zones"), "access_repaired": res.get("access_repaired"),
            "greedy_served_share": res.get("served_share"), "history_len": len(res.get("history") or [])}


# ---------------------------------------------------------------------------
# E9.1 validate
# ---------------------------------------------------------------------------
def run_validate(study: Study) -> Dict[str, Any]:
    a = study.args
    n_c = int(a.n_candidates) if a.n_candidates else (2 if study.smoke else 4)
    cands = study.candidates[:n_c]
    seeds = [int(s) for s in (a.seeds or ([0, 1] if not study.smoke else [0, 1]))]
    n_bikes = int(a.bikes) if a.bikes else (2 if study.smoke else 6)
    budgets = [float(m) for m in (a.budgets or [1])] if not study.smoke else [1.0, 2.0]
    grid = list(study.validation_grid)
    roles = ("S", "SC") if not study.smoke else ROLES_ALL
    size_bounds = study.validation_bounds
    max_hubs = None
    if a.with_hub and not study.smoke:
        grid = grid + [("C", 0, 1)]
        roles = ("S", "C", "SC")
        size_bounds = {**size_bounds, "C": (0, 0, 1, 1)}
        max_hubs = 1
    plan = {"sub": "validate", **study.plan_common(), "n_candidates": len(cands), "candidates": [c.id for c in cands],
            "seeds": seeds, "n_bikes": n_bikes, "budgets_m": budgets, "grid": grid, "roles": list(roles),
            "size_bounds": size_bounds, "max_hubs": max_hubs}
    caps = None if max_hubs is None else {"C": max_hubs}
    for m in budgets:
        lays = BL.enumerate_layouts(cands, grid, study.budget(m), study.spec, range(1, int(m) + 1), max_role_count=caps,
                                    s_needs_charge=study.s_needs_charge)
        plan[f"layouts_m{m:g}"] = len(lays)
    plan["worst_case_lower_level_solves"] = sum(plan[f"layouts_m{m:g}"] for m in budgets) * len(seeds)
    print(json.dumps(plan, indent=1, default=str), flush=True)
    if a.dry_run:
        return plan
    # the validation scenarios carry only the validation candidates (smaller template libraries:
    # reposition targets = these candidates + depots); (A) and (B) share the same per-layout
    # libraries (sub-libraries of the all-candidates template, reposition = 'all_candidates')
    ev = study.evaluator(seeds, n_bikes, candidates=cands)
    bound = ev.superset_bound(time_limit=study.time_limit)
    study.emit({"kind": "superset_bound", "bound": bound, "rows": ev.bound_rows, "seeds": seeds})
    agreement: Dict[str, Any] = {"plan": plan, "budgets": []}
    figures: List[str] = []
    sections: List[Tuple[str, str]] = []
    for m in budgets:
        budget = study.budget(m)
        prev = study.done("exhaustive", budget_m=m)
        if prev and prev.get("coverage", {}).get("full_coverage"):
            print(f"# exhaustive m={m:g} already complete; re-priced from the cache", flush=True)
        ex = BL.exhaustive(ev, cands, grid, budget, range(1, int(m) + 1), bound=bound, screen=True, max_role_count=caps,
                           s_needs_charge=study.s_needs_charge,
                           on_row=lambda r, m=m: study.emit({"kind": "layout", "method": "exhaustive", "budget_m": m, **r}))
        study.emit_cache_rows(ev)
        ex_row = layout_row(study, ev, ex["best_layout"], "exhaustive", "exhaustive", m,
                            {"V": ex["best_value"], "coverage": ex["coverage"], "evaluator": ex["evaluator"],
                             "n_layouts": ex["coverage"]["n_layouts"], "status": "OK"})
        study.emit(ex_row)
        tl = study.wall.solve_limit(study.integrated_time_limit)
        if tl is None:
            ig_row = layout_row(study, ev, None, "integrated", "integrated", m, {"status": C.SKIPPED_BUDGET})
            study.emit(ig_row)
            ig = None
        else:
            ig = BL.integrated_stochastic_ilp(ev, cands, budget, roles=roles, size_bounds=size_bounds, time_limit=tl,
                                              threads=study.threads, params=dict(C.ILP_PARAMS_R3),
                                              mip_start_layout=ex["best_layout"], certify=True, max_role_count=caps,
                                              s_needs_charge=study.s_needs_charge)
            ig_row = layout_row(study, ev, ig["layout"], "integrated", "integrated", m,
                                {k: ig[k] for k in ("status", "obj", "bound", "gap", "runtime_s", "build_s", "n_vars",
                                                   "n_binaries", "n_rows", "V_model", "V_certified", "certified_ok",
                                                   "mip_start", "expected_served_share", "sol_count", "node_count")})
            ig_row["V"] = ig["obj"]
            ig_row["per_scenario"] = [{k: v for k, v in r.items() if k != "components"} for r in ig["per_scenario"]]
            study.emit(ig_row)
        study.emit_cache_rows(ev)
        # agreement ------------------------------------------------------------
        rec: Dict[str, Any] = {"budget_m": m, "budget": budget, "exhaustive_V": ex["best_value"],
                               "exhaustive_layout": _fmt_layout(ex["best_layout"]), "coverage": ex["coverage"],
                               "integrated_status": None if ig is None else ig["status"],
                               "integrated_obj": None if ig is None else ig["obj"],
                               "integrated_bound": None if ig is None else ig["bound"],
                               "integrated_gap": None if ig is None else ig["gap"],
                               "integrated_layout": None if ig is None else ig["layout_key"],
                               "integrated_V_certified": None if ig is None else ig["V_certified"]}
        if ig is not None and ig["obj"] is not None and ex["best_value"] is not None:
            gapA = float(ig["gap"] or 0.0)
            # tolerance: 1e-6 plus the MIP gaps of (A) and of the lower-level solves behind (B)'s optimum
            best_rows = next((r for r in ex["rows"] if r.get("is_best")), None)
            gapB = sum(ev.p[i] * abs(float(g or 0.0)) * abs(float(o or 0.0))
                       for i, (g, o) in enumerate(zip((best_rows or {}).get("gaps") or [], (best_rows or {}).get("opex") or [])))
            tol = 1e-6 * max(1.0, abs(ig["obj"])) + gapA * abs(ig["obj"]) + gapB
            diff = ig["obj"] - ex["best_value"]
            rec.update(diff=diff, tolerance=tol, exact=(gapA == 0.0 and gapB == 0.0 and ex["coverage"]["full_coverage"]),
                       agree=(abs(diff) <= tol) or (ig["bound"] is not None and ig["bound"] - tol <= ex["best_value"] <= ig["obj"] + tol),
                       integrated_le_exhaustive=(ig["obj"] <= ex["best_value"] + tol),
                       exhaustive_within_bounds=(ig["bound"] is not None and ig["bound"] - tol <= ex["best_value"] <= ig["obj"] + tol),
                       same_layout=(ig["layout_key"] == _fmt_layout(ex["best_layout"])),
                       integrated_layout_V_by_evaluator=ev.value(ig["layout"]) if ig["layout"] is not None else None)
        else:
            rec.update(agree=False, exact=False, diff=None, tolerance=None)
        agreement["budgets"].append(rec)
        study.emit({"kind": "agreement", "budget_m": m, **rec})
        rows_sorted = sorted([r for r in ex["rows"]], key=lambda r: (r.get("V") is None, r.get("V") or 0.0))
        for r in rows_sorted:
            rt = [row.get("runtime_s") for row in ev.cache.values()
                  if row.get("layout_key") == r["layout_key"] and row.get("policy") == "ilp"
                  and row.get("seed") in ev.seeds and row.get("reposition") == ev.reposition]
            r["solve_s"] = [round(float(x), 1) for x in rt if x is not None]
        sections.append((f"Budget m = {m:g} ({budget:,.0f} USD): all enumerated layouts (B)",
                         table(rows_sorted, ["layout_key", "investment", "C_setup", "status", "V", "lower_bound", "statuses", "gaps",
                                             "served_share", "solve_s", "error"])))
        sections.append((f"Budget m = {m:g}: agreement (A) vs (B)",
                         table([rec], ["exhaustive_V", "exhaustive_layout", "integrated_obj", "integrated_bound", "integrated_gap",
                                       "integrated_layout", "integrated_V_certified", "diff", "tolerance", "exact", "agree",
                                       "same_layout"], 6)
                         + "\n\n" + f"Coverage: {json.dumps(ex['coverage'])}"))
        if not study.smoke:
            base = study.scenario(seeds[0], n_bikes)
            fig = plot_map(study, base, {"exhaustive": ex["best_layout"], "integrated": None if ig is None else ig["layout"]},
                           os.path.join(study.out_dir, f"map_budget_{m:g}.png"), f"E9.1 validation, budget m = {m:g}")
            if fig:
                figures.append(fig)
    with open(os.path.join(study.out_dir, "agreement.json"), "w", encoding="utf-8") as fh:
        json.dump(C.jsonable(agreement), fh, indent=1)
    study.refresh_csv()
    ilp_rows = [r for r in ev.cache.values() if r.get("policy") == "ilp" and r.get("runtime_s") is not None
                and r.get("seed") in ev.seeds and r.get("reposition") == ev.reposition and r.get("family") == ev.family]
    rts = sorted(float(r["runtime_s"]) for r in ilp_rows)
    solve_stats = {"n": len(rts), "mean_s": (sum(rts) / len(rts)) if rts else None, "max_s": (rts[-1] if rts else None),
                   "median_s": (rts[len(rts) // 2] if rts else None), "n_time_limit": sum(1 for r in ilp_rows if r.get("status") == "TIME_LIMIT")}
    agreement["solve_stats"] = solve_stats
    sections.append(("Lower-level solve times (cached ILP rows of this family / candidate set)", json.dumps(solve_stats)))
    sections.insert(0, ("Protocol", f"Candidates {[c.id for c in cands]}; scenarios seeds {seeds} (p = 1/{len(seeds)}); "
                                    f"{n_bikes} bikes; option grid {grid}; roles {list(roles)}; swap-only sites need a C / SC "
                                    f"object: {study.s_needs_charge}; superset bound per scenario "
                                    f"{[round(b, 3) for b in bound]} (ObjBound of the all-open relaxed-target model); "
                                    f"(B) with scenario-by-scenario pruning and baseline-value ordering, (A) warm-started from (B)'s optimum. "
                                    f"Agreement rule: |V_A - V_B| <= 1e-6 + gap_A |V_A| + sum_s p_s gap_s |OPEX_s| (exact when all gaps are 0 "
                                    f"and (B) has full coverage), otherwise V_B within [bound_A, incumbent_A]."))
    sections.append(("Solver statistics", json.dumps(ev.stats())))
    write_md(study, "E9.1 -- integrated stochastic ILP (A) vs exhaustive bi-level enumeration (B)", sections, figures)
    print(json.dumps(C.jsonable(agreement["budgets"]), indent=1), flush=True)
    return agreement


ROLES_ALL = S.ROLES


# ---------------------------------------------------------------------------
# E9.2 sweep
# ---------------------------------------------------------------------------
def run_sweep(study: Study, role_set: Tuple[str, ...] = ("S", "C", "SC"), tag: str = "sweep",
              budgets: Optional[Sequence[float]] = None, access: Optional[Dict[str, List[str]]] = None,
              integrated: bool = True, zeta_exp: Optional[float] = None) -> Dict[str, Any]:
    a = study.args
    seeds = [int(s) for s in (a.seeds or SEARCH_SEEDS)] if not study.smoke else [0, 1]
    budgets = [float(m) for m in (budgets or a.budgets or [1, 2, 3, 4])] if not study.smoke else [1.0, 2.0]
    menu = {r: study.size_menu[r] for r in role_set if r in study.size_menu}
    plan = {"sub": tag, **study.plan_common(), "seeds": seeds, "budgets_m": budgets, "roles": list(role_set), "size_menu": menu,
            "n_candidates": len(study.candidates), "k_screen": int(a.k_screen), "access_zones": None if access is None else len(access),
            "moves_per_step_max": len(study.candidates) * sum(len(v) for v in menu.values())}
    print(json.dumps(plan, indent=1, default=str), flush=True)
    if a.dry_run:
        return plan
    ev = study.evaluator(seeds)
    levels = [study.budget(m) for m in budgets]
    g = BL.greedy_local_search(ev, study.candidates, max(levels), size_menu=menu, roles=role_set, budget_levels=levels,
                               access=access, **study.greedy_kwargs(),
                               on_step=lambda r: study.emit({"kind": "greedy_step", "role_set": "+".join(role_set), **r}))
    study.emit_cache_rows(ev)
    study.emit({"kind": "greedy_summary", "role_set": "+".join(role_set), "class_counts": g["class_counts"],
                "wall_exhausted": g["wall_exhausted"], "best_singleton": g["best_singleton"], "frontier": g["frontier"]})
    results: Dict[float, Dict[str, Any]] = {}
    rows_md: List[Dict[str, Any]] = []
    figures: List[str] = []
    for m, b in zip(budgets, levels):
        res = g["per_budget"][b]
        lay = res["layout"]
        row = layout_row(study, ev, lay, "layout_chosen", "greedy_ls", m, {"role_set": "+".join(role_set), **_greedy_cols(res)})
        if lay is not None:
            evo = ev.evaluate(lay)
            row.update(eval_cols(evo))
            row["V"] = evo["V"]
            row["history_len"] = len(res["history"])
            if not study.smoke:
                row["zone_distance"] = BL.zone_site_distances(lay, study.candidates, ev.scenarios)
        study.emit(row)
        results[m] = {"greedy": row}
        rows_md.append(row)
        if integrated:
            tl = study.wall.solve_limit(study.integrated_time_limit)
            prev = study.done("layout_chosen", method="integrated", budget_m=m, role_set="+".join(role_set))
            if prev and C.reusable_ilp_row(prev.get("status"), prev.get("gap")):
                print(f"# integrated m={m:g} reused ({prev['status']}, gap {prev.get('gap')})", flush=True)
                results[m]["integrated"] = prev
                rows_md.append(prev)
                continue
            if tl is None:
                irow = layout_row(study, ev, None, "layout_chosen", "integrated", m, {"status": C.SKIPPED_BUDGET, "role_set": "+".join(role_set)})
            else:
                ig = BL.integrated_stochastic_ilp(ev, study.candidates, b, roles=role_set, time_limit=tl, threads=study.threads,
                                                  params=dict(C.ILP_PARAMS_R3), mip_start_layout=lay, certify=True,
                                                  access=access, zeta_exp=zeta_exp, s_needs_charge=study.s_needs_charge)
                irow = layout_row(study, ev, ig["layout"], "layout_chosen", "integrated", m,
                                  {k: ig[k] for k in ("status", "obj", "bound", "gap", "runtime_s", "build_s", "n_vars", "n_binaries",
                                                     "n_rows", "V_model", "V_certified", "certified_ok", "mip_start",
                                                     "expected_served_share")})
                irow["V"] = ig["obj"]
                irow["role_set"] = "+".join(role_set)
                if ig["layout"] is not None:
                    irow.update(eval_cols(ev.evaluate(ig["layout"]), "ll_"))
            study.emit(irow)
            study.emit_cache_rows(ev)
            results[m]["integrated"] = irow
            rows_md.append(irow)
    study.refresh_csv()
    # figures / tables ----------------------------------------------------------
    pareto_rows = [r for r in rows_md if r.get("V") is not None]
    figures.append(plot_pareto(pareto_rows, os.path.join(study.out_dir, "pareto.png"), f"E9 {tag}: investment vs expected OPEX"))
    pd.DataFrame([{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in rows_md]).to_csv(
        os.path.join(study.out_dir, "pareto.csv"), index=False)
    if not study.smoke:
        base = study.scenario(seeds[0])
        for m in budgets:
            lays = {k: (BL.Layout.from_json(v["layout"]) if v.get("layout") else None) for k, v in results[m].items()}
            fig = plot_map(study, base, lays, os.path.join(study.out_dir, f"map_budget_{m:g}.png"), f"E9 {tag}: budget m = {m:g}")
            if fig:
                figures.append(fig)
    sections = [("Chosen layouts per budget", table(rows_md, ["budget_m", "method", "layout_key", "investment", "C_setup", "status",
                                                              "V", "opex_mean", "served_share", "n_late", "kwh_purchased", "transfers_used",
                                                              "gap", "bound", "search_complete", "reasons"])),
                ("Greedy frontier", json.dumps(g["frontier"]) + f"\n\nbest singleton: {g['best_singleton']}\n\n"
                 f"priced layouts by status: {json.dumps(g['class_counts'])}; wall exhausted: {g['wall_exhausted']}"),
                ("Solver statistics", json.dumps(ev.stats()))]
    write_md(study, f"E9 {tag} -- greedy + local search per budget" + (" with the integrated bound" if integrated else ""), sections, figures)
    return {"results": results, "greedy": g}


# ---------------------------------------------------------------------------
# E9.3 roles
# ---------------------------------------------------------------------------
def run_roles(study: Study) -> Dict[str, Any]:
    a = study.args
    budgets = [float(m) for m in (a.budgets or [2, 3])] if not study.smoke else [1.0, 2.0]
    seeds = [int(s) for s in (a.seeds or SEARCH_SEEDS)] if not study.smoke else [0, 1]
    plan = {"sub": "roles", **study.plan_common(), "role_sets": ROLE_SETS, "budgets_m": budgets, "seeds": seeds}
    print(json.dumps(plan, indent=1), flush=True)
    if a.dry_run:
        return plan
    ev = study.evaluator(seeds)
    rows: List[Dict[str, Any]] = []
    for name, roles in ROLE_SETS.items():
        menu = {r: study.size_menu[r] for r in roles}
        levels = [study.budget(m) for m in budgets]
        g = BL.greedy_local_search(ev, study.candidates, max(levels), size_menu=menu, roles=roles, budget_levels=levels,
                                   **study.greedy_kwargs(),
                                   on_step=lambda r, name=name: study.emit({"kind": "greedy_step", "role_set": name, **r}))
        study.emit_cache_rows(ev)
        study.emit({"kind": "greedy_summary", "role_set": name, "class_counts": g["class_counts"],
                    "wall_exhausted": g["wall_exhausted"], "best_singleton": g["best_singleton"], "frontier": g["frontier"]})
        for m, b in zip(budgets, levels):
            res = g["per_budget"][b]
            lay = res["layout"]
            row = layout_row(study, ev, lay, "layout_chosen", f"greedy_ls[{name}]", m, {"role_set": name, **_greedy_cols(res)})
            if lay is not None:
                evo = ev.evaluate(lay)
                row.update(eval_cols(evo))
                row["V"] = evo["V"]
            study.emit(row)
            rows.append(row)
    study.refresh_csv()
    groups: Dict[str, Dict[str, Optional[float]]] = {}
    comp_groups: Dict[str, Dict[str, Optional[float]]] = {}
    for r in rows:
        groups.setdefault(f"m={r['budget_m']:g}", {})[r["role_set"]] = r.get("V")
        for c in ("C_elec", "C_travel", "unserved", "response", "lateness", "C_reb"):
            comp_groups.setdefault(f"m={r['budget_m']:g} {r['role_set']}", {})[c] = r.get(c)
    figures = [plot_bars(groups, os.path.join(study.out_dir, "roles.png"), "V (USD per window)", "E9.3 role sets: V per budget"),
               plot_bars(comp_groups, os.path.join(study.out_dir, "roles_components.png"), "USD per window",
                         "E9.3 mean cost components (28)-(32) per role set")]
    sections = [("Role sets per budget", table(rows, ["budget_m", "role_set", "layout_key", "n_S", "n_C", "n_SC", "investment", "V",
                                                      "opex_mean", "transfers_used", "C_reb", "served_share", "status",
                                                      "search_complete", "reasons"])),
                ("Solver statistics", json.dumps(ev.stats()))]
    write_md(study, "E9.3 -- role separation: co-located only vs hubs allowed vs no hubs", sections, figures)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# E9.4 deck
# ---------------------------------------------------------------------------
def _chosen_layouts(study: Study, subs: Sequence[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sub in subs:
        path = os.path.join(study.root, sub, "records.jsonl")
        last: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for r in C.load_jsonl(path):
            if r.get("kind") in ("layout_chosen", "exhaustive", "integrated") and r.get("layout"):
                last[(sub, r.get("method"), r.get("budget_m"), r.get("role_set"))] = r
        out.extend(last.values())
    return out


def run_deck(study: Study) -> Dict[str, Any]:
    a = study.args
    budgets = [float(m) for m in (a.budgets or [1, 2, 3, 4])] if not study.smoke else [1.0, 2.0]
    seeds = [int(s) for s in (a.seeds or SEARCH_SEEDS)] if not study.smoke else [0, 1]
    plan = {"sub": "deck", **study.plan_common(), "budgets_m": budgets, "seeds": seeds, "iterations": int(a.iterations)}
    print(json.dumps(plan, indent=1), flush=True)
    if a.dry_run:
        return plan
    ev = study.evaluator(seeds)
    rows: List[Dict[str, Any]] = []
    for m in budgets:
        d = BL.deck_heuristic(ev, study.candidates, study.budget(m), iterations=int(a.iterations))
        lay = d["layout"]
        row = layout_row(study, ev, lay, "layout_chosen", "deck", m, {"status": d["status"], "k": d["k"], "log": d["log"]})
        if lay is not None:
            cr = BL.cross_evaluate(ev, lay)
            row.update(eval_cols(cr["ilp"]))
            row["V"] = cr["ilp"]["V"]
            row.update(eval_cols(cr["baseline"], "baseline_"))
            row["gap_vs_baseline_pct"] = cr["gap_vs_baseline_pct"]
        study.emit(row)
        study.emit_cache_rows(ev)
        rows.append(row)
    study.refresh_csv()
    others = _chosen_layouts(study, ["sweep"])
    groups: Dict[str, Dict[str, Optional[float]]] = {}
    overlap_rows: List[Dict[str, Any]] = []
    for r in rows:
        key = f"m={r['budget_m']:g}"
        groups.setdefault(key, {})["deck (ILP-priced)"] = r.get("V")
        groups[key]["deck (baseline-priced)"] = r.get("baseline_V")
        for o in others:
            if o.get("budget_m") == r["budget_m"] and o.get("V") is not None:
                groups[key][str(o["method"])] = o["V"]
                if o.get("bound") is not None:
                    groups[key]["integrated bound"] = o["bound"]
                lay_o = BL.Layout.from_json(o["layout"])
                lay_d = BL.Layout.from_json(r["layout"]) if r.get("layout") else None
                if lay_d is not None:
                    overlap_rows.append({"budget_m": r["budget_m"], "other": o["method"], "deck": lay_d.key(), "other_layout": lay_o.key(),
                                         "shared_locations": len(set(lay_d.locations()) & set(lay_o.locations())),
                                         "regret_usd": (r["V"] - o["V"]) if r.get("V") is not None else None,
                                         "regret_pct": (100.0 * (r["V"] - o["V"]) / o["V"]) if r.get("V") is not None and o["V"] else None})
    figures = [plot_bars(groups, os.path.join(study.out_dir, "deck_vs_bilevel.png"), "V (USD per window)",
                         "E9.4 deck heuristic vs greedy+LS vs integrated per budget")]
    sections = [("Deck heuristic per budget", table(rows, ["budget_m", "k", "layout_key", "investment", "V", "baseline_V", "gap_vs_baseline_pct",
                                                           "served_share", "status"])),
                ("Overlap and regret vs the bi-level layouts (from --sweep records, if present)",
                 table(overlap_rows, ["budget_m", "other", "deck", "other_layout", "shared_locations", "regret_usd", "regret_pct"])),
                ("Solver statistics", json.dumps(ev.stats()))]
    write_md(study, "E9.4 -- the proposal deck's spin-and-adjust planner vs the bi-level optimum", sections, figures)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# E9.5 cross
# ---------------------------------------------------------------------------
def run_cross(study: Study) -> Dict[str, Any]:
    a = study.args
    seeds = [int(s) for s in (a.seeds or EVAL_SEEDS)] if not study.smoke else [0, 1, 2]
    in_sample = [s for s in seeds if s in SEARCH_SEEDS] if not study.smoke else [0, 1]
    chosen = _chosen_layouts(study, ["sweep", "deck", "roles", "validate"])
    if a.layouts:
        chosen += [{"method": "cli", "budget_m": None, "layout": BL.Layout.from_key(k).to_json(), "role_set": None} for k in a.layouts]
    if not chosen and study.smoke:
        chosen = [{"method": "smoke", "budget_m": 2.0, "layout": [["T1", "SC", 2, 1], ["T2", "S", 2, 0]], "role_set": None},
                  {"method": "smoke", "budget_m": 1.0, "layout": [["T2", "SC", 2, 1]], "role_set": None}]
    uniq: Dict[str, Dict[str, Any]] = {}
    for r in chosen:
        lay = BL.Layout.from_json(r["layout"])
        uniq.setdefault(lay.key(), {"layout": lay, "sources": []})["sources"].append(f"{r.get('method')}@m{r.get('budget_m')}")
    plan = {"sub": "cross", **study.plan_common(), "seeds": seeds, "in_sample": in_sample, "n_layouts": len(uniq),
            "layouts": {k: v["sources"] for k, v in uniq.items()}}
    print(json.dumps(plan, indent=1), flush=True)
    if a.dry_run:
        return plan
    if not uniq:
        print("# no chosen layouts found (run --sweep / --deck first)", flush=True)
        write_md(study, "E9.5 -- cross-evaluation", [("Status", "no chosen layouts found")], [])
        study.refresh_csv()
        return plan
    ev = study.evaluator(seeds)
    ev_rel = study.evaluator(seeds, relaxed=True)
    rows: List[Dict[str, Any]] = []
    for key, rec in uniq.items():
        lay = rec["layout"]
        cr = BL.cross_evaluate(ev, lay)
        row = layout_row(study, ev, lay, "cross", "cross", None, {"sources": rec["sources"]})
        row.update(eval_cols(cr["ilp"], "ilp_"))
        row.update(eval_cols(cr["baseline"], "baseline_"))
        row["V"] = cr["ilp"]["V"]
        row["gap_vs_baseline_pct"] = cr["gap_vs_baseline_pct"]
        ins = [i for i, s in enumerate(seeds) if s in in_sample]
        outs = [i for i, s in enumerate(seeds) if s not in in_sample]
        if ins and outs and cr["ilp"]["complete"]:
            op = cr["ilp"]["opex"]
            row["ilp_opex_in_sample"] = sum(op[i] for i in ins) / len(ins)
            row["ilp_opex_out_of_sample"] = sum(op[i] for i in outs) / len(outs)
            row["in_out_gap"] = row["ilp_opex_out_of_sample"] - row["ilp_opex_in_sample"]
        rel = ev_rel.evaluate(lay)
        row.update(eval_cols(rel, "ilp_relaxed_"))
        study.emit(row)
        study.emit_cache_rows(ev)
        study.emit_cache_rows(ev_rel)
        rows.append(row)
    study.refresh_csv()
    vi = [r["ilp_V"] for r in rows if r.get("ilp_V") is not None]
    vb = [r["baseline_V"] for r in rows if r.get("baseline_V") is not None]
    for r in rows:
        r["regret_ilp"] = None if r.get("ilp_V") is None or not vi else r["ilp_V"] - min(vi)
        r["regret_baseline"] = None if r.get("baseline_V") is None or not vb else r["baseline_V"] - min(vb)
    mat = pd.DataFrame({"ILP": [r.get("ilp_V") for r in rows], "baseline": [r.get("baseline_V") for r in rows],
                        "ILP relaxed targets": [r.get("ilp_relaxed_V") for r in rows]},
                       index=[r["layout_key"] for r in rows]).astype(float)
    mat.to_csv(os.path.join(study.out_dir, "cross_eval.csv"))
    figures = [plot_heat(mat, os.path.join(study.out_dir, "cross_eval.png"), "E9.5 V(layout) under each operating policy")]
    sections = [("Layout x policy", table(rows, ["layout_key", "sources", "investment", "ilp_V", "baseline_V", "ilp_relaxed_V",
                                                 "gap_vs_baseline_pct", "regret_ilp", "regret_baseline", "ilp_served_share",
                                                 "baseline_served_share", "ilp_opex_in_sample", "ilp_opex_out_of_sample", "in_out_gap"])),
                ("Solver statistics", json.dumps({"written": ev.stats(), "relaxed": ev_rel.stats()}))]
    write_md(study, "E9.5 -- cross-evaluation of the chosen layouts under the ILP and the baseline policy", sections, figures)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# E9.6 access
# ---------------------------------------------------------------------------
def run_access(study: Study) -> Dict[str, Any]:
    a = study.args
    budgets = [float(m) for m in (a.budgets or [2, 3])] if not study.smoke else [1.0, 2.0]
    seeds = [int(s) for s in (a.seeds or SEARCH_SEEDS)] if not study.smoke else [0, 1]
    Ds = [int(d) for d in (a.access_d or ACCESS_D)] if not study.smoke else [1]
    scen = [study.scenario(s) for s in seeds]
    if study.smoke:
        for inst in scen:
            inst.meta["orders"] = [{"id": o.id, "zone_code": "Z1" if o.d <= 2 else "Z2"} for o in inst.orders]
    sets = {D: BL.access_sets(study.candidates, scen, D) for D in Ds}
    plan = {"sub": "access", **study.plan_common(), "budgets_m": budgets, "seeds": seeds, "D_blocks": Ds,
            "zones": {D: {z: locs for z, locs in s_.items()} for D, s_ in sets.items()}, "zeta": a.zeta}
    print(json.dumps(plan, indent=1), flush=True)
    if a.dry_run:
        return plan
    ev = study.evaluator(seeds)
    rows: List[Dict[str, Any]] = []
    variants: List[Tuple[str, Optional[Dict[str, List[str]]]]] = [("no_access", None)] + [(f"D{D}", sets[D]) for D in Ds]
    for name, acc in variants:
        levels = [study.budget(m) for m in budgets]
        uncoverable = [] if acc is None else [z for z, locs in acc.items() if not locs]
        g = BL.greedy_local_search(ev, study.candidates, max(levels), size_menu=study.size_menu, roles=S.ROLES,
                                   budget_levels=levels, access=acc, **study.greedy_kwargs(),
                                   on_step=lambda r, name=name: study.emit({"kind": "greedy_step", "access": name, **r}))
        study.emit_cache_rows(ev)
        study.emit({"kind": "greedy_summary", "access": name, "class_counts": g["class_counts"],
                    "wall_exhausted": g["wall_exhausted"], "best_singleton": g["best_singleton"], "frontier": g["frontier"]})
        for m, b in zip(budgets, levels):
            res = g["per_budget"][b]
            lay = res["layout"]
            row = layout_row(study, ev, lay, "layout_chosen", f"greedy_ls[{name}]", m,
                             {"access": name, "uncoverable_zones": uncoverable, **_greedy_cols(res)})
            if lay is not None:
                evo = ev.evaluate(lay)
                row.update(eval_cols(evo))
                row["V"] = evo["V"]
                dist = BL.zone_site_distances(lay, study.candidates, scen)
                row["zone_mean_blocks"] = dist["mean_blocks"]
                row["zone_max_blocks"] = dist["max_blocks"]
                row["zones_covered"] = {D: sum(1 for locs in sets[D].values() if any(l in lay.locations() and S.ROLE_SWAP[lay.role(l)] for l in locs))
                                        for D in Ds}
            study.emit(row)
            rows.append(row)
        if a.zeta is not None and acc is not None:
            for m, b in zip(budgets, levels):
                tl = study.wall.solve_limit(study.integrated_time_limit)
                if tl is None:
                    study.emit(layout_row(study, ev, None, "layout_chosen", f"integrated[{name},zeta{a.zeta}]", m, {"status": C.SKIPPED_BUDGET}))
                    continue
                ig = BL.integrated_stochastic_ilp(ev, study.candidates, b, roles=S.ROLES, time_limit=tl, threads=study.threads,
                                                  params=dict(C.ILP_PARAMS_R3), access=acc, zeta_exp=float(a.zeta),
                                                  mip_start_layout=g["per_budget"][b]["layout"], certify=True,
                                                  s_needs_charge=study.s_needs_charge)
                irow = layout_row(study, ev, ig["layout"], "layout_chosen", f"integrated[{name},zeta{a.zeta}]", m,
                                  {k: ig[k] for k in ("status", "obj", "bound", "gap", "runtime_s", "expected_served_share", "V_certified")})
                irow["V"] = ig["obj"]
                irow["access"] = name
                irow["note"] = "optimistic bi-level: [U5] on the follower's u; a planner-only row"
                study.emit(irow)
                study.emit_cache_rows(ev)
                rows.append(irow)
    study.refresh_csv()
    groups: Dict[str, Dict[str, Optional[float]]] = {}
    for r in rows:
        groups.setdefault(f"m={r['budget_m']:g}", {})[str(r["method"])] = r.get("V")
    figures = [plot_bars(groups, os.path.join(study.out_dir, "access.png"), "V (USD per window)", "E9.6 V with / without the access row [U4]")]
    sections = [("Access row per budget", table(rows, ["budget_m", "method", "layout_key", "investment", "V", "opex_mean", "served_share",
                                                       "zone_mean_blocks", "zone_max_blocks", "zones_covered", "uncovered_zones",
                                                       "access_repaired", "uncoverable_zones", "status", "search_complete", "reasons"])),
                ("Access sets", "\n".join(f"* D = {D}: " + json.dumps(s_) for D, s_ in sets.items())),
                ("Solver statistics", json.dumps(ev.stats()))]
    write_md(study, "E9.6 -- the planner-only access row [U4]: what it costs the operator", sections, figures)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for sub in SUBS:
        ap.add_argument(f"--{sub}", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="toy siting instances, seconds")
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--threads", type=int, default=C.THREADS)
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    ap.add_argument("--time-limit-hub", type=float, default=TIME_LIMIT_HUB)
    ap.add_argument("--integrated-time-limit", type=float, default=INTEGRATED_TIME_LIMIT)
    ap.add_argument("--wall-budget", type=float, default=8 * 3600.0, help="seconds")
    ap.add_argument("--seeds", nargs="*", type=int, default=None)
    ap.add_argument("--budgets", nargs="*", type=float, default=None, help="budget multipliers m")
    ap.add_argument("--bikes", type=int, default=None)
    ap.add_argument("--n-candidates", type=int, default=None, help="validate: first n candidates")
    ap.add_argument("--with-hub", action="store_true", help="validate: add the C role (C = 1)")
    ap.add_argument("--k-screen", type=int, default=5)
    ap.add_argument("--iterations", type=int, default=3, help="deck heuristic iterations")
    ap.add_argument("--access-d", nargs="*", type=int, default=None)
    ap.add_argument("--zeta", type=float, default=None, help="access: expected service share [U5] for the integrated run")
    ap.add_argument("--layouts", nargs="*", default=None, help="cross: extra layout keys")
    ap.add_argument("--family", default=DEFAULT_FAMILY, help=f"siting family, one of {sorted(S.SITING_FAMILIES)}")
    ap.add_argument("--min-served", type=float, default=MIN_SERVED_SHARE,
                    help="greedy: moves whose expected served share is below this are discarded")
    ap.add_argument("--allow-s-only", action="store_true", help="lift the rule 'swap-only sites only next to a C / SC object'")
    ap.add_argument("--reposition", default="open_sites", choices=list(S.REPOSITION_MODES),
                    help="reposition targets of the search sub-commands (validate always uses all_candidates)")
    ap.add_argument("--access-mode", default="repair", choices=["repair", "report", "enforce"],
                    help="access: how the greedy treats the planner-only row [U4]")
    args = ap.parse_args(argv)
    if args.threads > 3:
        raise SystemExit("round-3 rule: Threads <= 3")
    chosen = [sub for sub in SUBS if getattr(args, sub)]
    if not chosen:
        raise SystemExit("choose one of " + ", ".join(f"--{s}" for s in SUBS))
    warnings.simplefilter("ignore")
    out: Dict[str, Any] = {}
    for sub in chosen:
        study = Study(sub, args)
        fn = {"validate": run_validate, "sweep": run_sweep, "roles": run_roles, "deck": run_deck, "cross": run_cross,
              "access": run_access}[sub]
        out[sub] = fn(study)
        if not args.dry_run:
            with open(os.path.join(study.out_dir, "wall_time.json"), "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"wall_s": time.perf_counter() - study.t0, "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
                                     "args": vars(args)}) + "\n")
            print(f"# {sub} finished in {study.elapsed_min():.1f} min -> {study.out_dir}", flush=True)
    return out


if __name__ == "__main__":
    main()
