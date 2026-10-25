# O2 Manhattan: first pass (2026-10-18/19), what it certifies, and the second pass

Code: `ebike_swap_sim/ebike_swap_sim/benders.py`, `ebike_swap_sim/experiments/r6_o2_siting.py`.
Design: `notes/o2_siting_bound_design.md`; conventions: `notes/DECISIONS.md` (O2 conventions, O2 second pass).
Diagnosis source: `notes/workflow27_o2_diagnose.json` (two independent agents; condensed below).
First-pass folder (READ-ONLY from now on): `ebike_swap_sim/outputs/r6_o2/manhattan/` (`records.jsonl`, `cuts.jsonl`,
`cache/`), log `outputs/r6_o2/manhattan.log`.

## 1. What the first pass did

Command: `--manhattan --threads 3 --lp-threads 3 --lp-workers 3 --master-threads 2 --wall-relaxed 9 --wall-written 10
--reserve-min 60` (new prices P 60 / w 18 / v 15; 15 candidates, seeds 0-2, 8 bikes, family menu, budgets m = 1-4 x 52,150 USD).

* Superset LP bound `L = [633.85, 593.83, 722.39]` (770 s); three scenario LPs of 1.09-1.12 M columns / 179 k rows.
* Warm start (rule layouts, present-day proxy, round-5 layouts) priced; fixed-layout LP-gap gate: median 2.7 % (relaxed),
  4.5 % (written) -> both targets chose "certify the smallest budget by enumeration".
* The enumeration LP pass hit the wall at layout 47-52 of 90 in both targets (relaxed after 8 h, written after 9 h).
  The master was never solved (`master_solves 0`), every `budget_result` row has `LB None`, `gap inf`, `certified false`.
* Best layouts found: m = 1 `M09:SC:B3:C2` (relaxed V 1052.995; written best `M08:SC:B3:C2` V 1132.39),
  m = 2-4 `M08:SC:B3:C2|M09:SC:B3:C2` (relaxed 700.113, written 706.26; written m = 3-4 `M08|M09|M12` 703.61).
  These are also the CSCD / CSTC rule layouts at m = 2.

## 2. Diagnosis (verified; details in workflow27_o2_diagnose.json)

1. **LP re-solves 15-60x slower than a cold solve.** `ScenarioLP.solve` used barrier (Method 2) only for the first
   solve (all three LPs solved cold in about 16 s, in parallel) and warm-started dual simplex (Method 1) for every re-solve:
   160-1,360 s per layout (median 380 s relaxed, 265 s written). The RHS of the 135 fixing rows changes to a different
   open site, so the retained basis is far from optimal; simplex is single-threaded; `LPWarmStart 2` was never set, so
   Gurobi 13 solved the ORIGINAL, unpresolved model from the stale basis; and the machine paged (swap 8.5 of 9.2 GB).
2. **No pruning before the LP pass.** `certify_by_enumeration` solved the LPs of all 90 layouts before any prune;
   `master.envelope(l)` from the cuts already in the pool would have resolved the far one-site layouts without a solve
   (87 of 90 one-site layouts are resolved by 52 LPs through the size transfer at the same site); the layout order
   interleaved locations (worst case for a basis warm start).
3. **LB raised only at the end of the enumeration;** `lp_phase` / `screen` / `integer_phase` / `_explore` all return on
   `wall_out`; `finish()` never solved the master and never folded the superset bound in -> `LB None`.
4. **Resume impossible as written:** `finished_targets()` skipped any target with a `target_done` record of the same
   `config_md5`; `lp_memo` / `lp_pruned` were not persisted; the pool reader was strict.
5. **Cut validity (all stored kinds reusable):** `lp` cuts are safe Lagrangian cuts (valid for every first-stage value,
   any solver accuracy; audits `Qt - Qs <= 6e-8`); `lshaped` (`LBIP` from the all-candidates pricing ObjBound, `L` the
   superset bound) and `lifted` cuts are valid at every admissible integer point under their own target; relaxed cuts
   are valid for the written problem, never the reverse (`Cut.applies_to`).
6. Minor: `lp_workers x lp_threads` reserved 9 cores for single-threaded simplex; the `lp_layout` record dropped
   `runtime_s` / `iterations`; the target switch cost one slow warm solve.

## 3. What the first pass certifies now (bound from the stored pool, no new solve)

`--bound-from-cuts` on the first-pass pool (read-only; 262 cuts apply to relaxed, 489 to written; cover row included,
which changes nothing here; niced, Threads 1; `outputs/r6_o2/manhattan_bound/BOUND.md`, 2026-10-19 11:00, written
target provisional because its `budget_result` rows did not exist yet):

| target | m | LB | bound kind | UB (best priced) | UB layout | gap % |
|---|---|---|---|---|---|---|
| relaxed | 1 | 1,037.83 | enumeration floor (= master) | 1,052.995 | M09:SC:B3:C2 | 1.44 |
| relaxed | 2-4 | 674.83 | master (= trivial) | 700.113 | M08:SC:B3:C2 + M09:SC:B3:C2 | 3.61 |
| written | 1 | 1,037.83 | enumeration floor (= master) | 1,132.39 | M08:SC:B3:C2 | 8.35 |
| written | 2 | 674.83 | master (= trivial) | 706.26 | M08:SC:B3:C2 + M09:SC:B3:C2 | 4.45 |
| written | 3-4 | 674.83 | master (= trivial) | 703.61 | M08 + M09 + M12 (SC:B3:C2) | 4.09 |

Open layouts at m = 1 (envelope below `UB - tol`, `tol = max(0.25 % UB, 1 USD)`):

* relaxed: `M06:SC:B3:C2` (envelope 1037.8, no LP yet), `M09:SC:B3:C2` (priced 1046.2, open ILP gap in scenario 0:
  bound 972.8 vs incumbent 993.1 at 300 s), `M03:SC:B3:C2` (1049.5, no LP yet). `M05` (1067.8) and `M08` (1070.1) are
  resolved (`UB - tol = 1050.36`).
* written: `M06` (1037.8), `M03` (1050.2), `M05` (1067.8), `M07` (1098.6) unpriced; `M09` (1100.6) and `M08` (1122.6,
  the incumbent) priced with open ILP gaps (`UB - tol = 1129.56`).

**m >= 2 is the trivial bound.** 674.83 = mean superset LP bound 650.02 + cheapest two-site setup 24.81: `theta_s = L_s`
in every scenario. The stored LP cuts carry `beta_y` of about -1.6e4 on every closed site (duals of the `M_el = 1e4`
elastic columns), so a cut binds only at layouts with the same open sites; nothing in the pool says anything about
two-site layouts other than the 14 warm-start layouts. The master's minimisers at m >= 2 are pairs of far `B1` sites
(e.g. `M01:S:B1:C0|M13:SC:B1:C1`). A Benders loop seeded with this pool therefore raises the m >= 2 bound only to the
two-stage LP bound of the LP phase (unknown; between 674.8 and the incumbent's `v_LP` of about 693.8) and will not close
the 3.6 % gap: with 17,340 admissible layouts at m = 2 each proposal costs 3 LPs + a pricing and its cut resolves
essentially that layout only (design section 8 step 3 predicted this for a fixed-layout LP gap above 2 %).

## 4. What changed in the code (second-pass support)

* `ScenarioLP(method=...)`, CLI `--lp-method`: `barrier` (default; Method 2 + crossover with `LPWarmStart 0`, i.e. presolve
  and barrier run on every solve: Gurobi would otherwise skip the barrier and only run crossover from the stale basis),
  `dual` (old protocol with `LPWarmStart 2`), `concurrent` (Method 3). `LPResult.method` / `runtime_s` / `iterations`
  are stored in every `lp_layout` record. Cut construction unchanged (safe cut of C1 from the optimal duals of any method);
  toy test: barrier, dual and concurrent agree on `Qs` within 1e-6. Defaults: `--lp-workers 3 --lp-threads 3
  --master-threads 2` (11 of 12 cores; barrier scales with threads).
* `certify_by_enumeration(b, limit, prune=True)`: location-major, envelope-ascending order; **envelope prune before the LP**
  (`lp_pruned` record with `by = envelope`, counter `envelope_pruned`); prune again (envelope and `v_LP`) before every
  pricing; the enumeration floor `min_l max(envelope, v_LP, lower)` over the complete layout list is raised into `LB`
  also when the wall stops the enumeration (`enumerate` record with `done false`, `LB_floor`).
* **Escalation on the enumeration path (review round 3, major):** `certify_by_enumeration` pass 3 escalates the priced
  layouts whose best known lower value `max(envelope, v_LP, lower)` is still below `UB - tol` (`escalate()`, one scenario
  per call, lowest layout first, the open set recomputed after every call) until the budget closes, every level is
  used up, or the wall. Before, the budget closed as `enumerated (open pricing gaps)` and the integer phase skipped it,
  so the step-1 command (`--certify-budgets 1 --no-lp-phase --no-screen`) could never run the escalation of
  `M09:SC:B3:C2` scenario 0 that the relaxed m = 1 certificate needs. `enumerate` records carry `n_escalations`,
  `n_open_before_escalation`, `n_open_priced`, `open_priced`; the close reason names the open count when gaps remain.
* `LB = inf` (master infeasible: no admissible layout within the budget, e.g. a budget below the cheapest option) is
  reported as `LB None` with `close_reason = master infeasible (no admissible layout)`, certified only when no feasible
  layout was priced either (`UB None`; a finite `UB` is flagged inconsistent); a finite `LB` above `UB` (tolerances) is
  clamped to `UB` in the row (`LB_raw`). `--bound-from-cuts` reports the same for such a budget.
* `--resume-open` skips a `target_done` row only when every requested budget is certified AND the budget-free
  configuration hash `config_md5_core` (prices, menu, roles, spec, tolerances, access rows, escalations, gate; stored
  in `plan` and `target_done`) matches; otherwise a `target_not_skipped` record is written and the target runs again.
  First-pass rows have no core hash and are never skipped under `--resume-open`.
* **Guaranteed bound:** `SitingCertifier.finish()` always ends with `final_bound()`: one bound-only master solve per budget
  over the full pool (cover rows, `--final-master-s 120`, `ObjBound` valid at `TIME_LIMIT`), `LB = max(LB so far, master
  ObjBound, superset trivial bound, enumeration floor)`, nested over budgets; `final_bound` records; `budget_result`
  carries `LB_kind` (`master`, `enumeration`, `lp_phase`, `superset`, `nested:<kind>`) and `LB_parts`. `LB` is never
  `None`. `lp_phase` / `screen` skip budgets already closed.
* Resume: `--source-dir` (first pass, READ-ONLY; records, pool and cache copied once into `--out-dir`, cached rows'
  `schedule_path` rewritten to the copy), `--resume-open` (`target_done` rows count only when every requested budget is
  certified; `SitingCertifier.restore()` rebuilds `lp_memo` from the pool's `lp` cuts with `meta.tag = layout`, `priced`
  from the `price` records, `lp_pruned` from the `lp_pruned` records, `UB` / `best` from the restored incumbents),
  `--certify-budgets m ...`, `--skip-enumeration`, `--enum-limit`, lenient JSON-lines readers.
* `--bound-from-cuts` (`benders.pool_bound`, CLI `bound_from_pool`): masters per target and budget from a stored pool,
  `BOUND.md` + `bound_from_cuts.jsonl` in `--out-dir`; `--no-cover` skips the templates (5.0 GB peak with them on
  Manhattan, 0.19 GB without; same numbers here). Toy test: equals the certifier's `LB` after a full run.
* Tests (`tests/test_o2_benders.py`, toy, Threads 1): LP methods agree; LB finite when the wall hits in the enumeration /
  LP phase / integer phase; envelope pruning never prunes a layout with `V < UB - tol` and `envelope <= V` at random
  layouts; bound-from-cuts equals the certifier's LB; `restore` + resume certifies without re-solving anything of the first
  run; written cuts never enter a relaxed master; CLI plumbing of `--resume-open` / `--bound-from-cuts` on the smoke stage.

## 5. Second pass: commands and expected wall time

Prerequisites: the first pass has exited (`ps aux | grep r6_o2_siting`), no other lane runs, and the machine is no
longer paging: `sysctl vm.swapusage` shows at most a few GB used (not the 6-8.5 GB of the first pass) and
`memory_pressure` reports a normal level. **Every unit cost and hour estimate below presupposes no paging**: after the
first pass had exited, with swap still at about 8 GB used, a step-1 `--dry-run` (evaluator build, no solve) took 34 min
wall for 98 s of CPU (4 % CPU), so quit the other memory consumers (or reboot) before step 1. Run from
`ebike_swap_sim/` with `PYTHONPATH=.`; everything goes to a NEW folder `outputs/r6_o2/manhattan_pass2/` (the
first-pass folder is read once and never written).

Unit costs with the fast LP solves: a layout's three LPs about 20-30 s (three workers x three threads, cold barrier about
16 s plus post-processing); a pricing about 6 min per layout (3 scenarios x <= 300 s; 600 s per scenario with a
charge-only hub); an escalation 900 s then 1,800 s for one scenario; a master solve < 1 s.

```
cd "/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim"

# 0. bound of the first pass once more (adds the written budget_result rows); no solve; 1 min, 0.2 GB
PYTHONPATH=. nice -n 15 python3 experiments/r6_o2_siting.py --manhattan --bound-from-cuts --no-cover \
  --source-dir outputs/r6_o2/manhattan --out-dir outputs/r6_o2/manhattan_bound \
  --master-threads 1 --threads 1 --lp-threads 1 --lp-workers 1

# 1. m = 1 certification by pruned enumeration, relaxed then written (resumes: no first-pass LP or ILP is solved again)
PYTHONPATH=. nice -n 10 python3 experiments/r6_o2_siting.py --manhattan \
  --source-dir outputs/r6_o2/manhattan --out-dir outputs/r6_o2/manhattan_pass2 --resume-open \
  --budgets 1 --certify-budgets 1 --gate report --no-lp-phase --no-screen \
  --lp-method barrier --lp-workers 3 --lp-threads 3 --threads 3 --master-threads 2 \
  --wall-relaxed 3 --wall-written 4 --reserve-min 20 2>&1 | tee -a outputs/r6_o2/manhattan_pass2.log

# 2. m = 2-4: Benders phases seeded with the pool (bound only; no certificate expected, see section 3)
PYTHONPATH=. nice -n 10 python3 experiments/r6_o2_siting.py --manhattan \
  --source-dir outputs/r6_o2/manhattan --out-dir outputs/r6_o2/manhattan_pass2 --resume-open \
  --budgets 2 3 4 --skip-enumeration --gate report \
  --lp-method barrier --lp-workers 3 --lp-threads 3 --threads 3 --master-threads 2 \
  --wall-relaxed 4 --wall-written 4 --reserve-min 30 2>&1 | tee -a outputs/r6_o2/manhattan_pass2.log

# 3. tables: bound from the second-pass pool and the RESULTS.md of the second pass
PYTHONPATH=. nice -n 15 python3 experiments/r6_o2_siting.py --manhattan --bound-from-cuts --no-cover \
  --source-dir outputs/r6_o2/manhattan_pass2 --out-dir outputs/r6_o2/manhattan_pass2_bound \
  --master-threads 1 --threads 1 --lp-threads 1 --lp-workers 1
PYTHONPATH=. python3 experiments/r6_o2_siting.py --manhattan --analyse --out-dir outputs/r6_o2/manhattan_pass2
```

Expected times (walls above are upper limits; the run exits when the budgets are certified):

* Step 1, relaxed m = 1: envelope pass over the 90 layouts in seconds (first-pass LP values and pricings restored);
  LP + pricing of `M06:SC:B3:C2` and `M03:SC:B3:C2` (2 x (0.5 + 6-15) min), escalation of `M09:SC:B3:C2` scenario 0
  (15 + 30 min) and, if `M06` / `M03` end with open gaps, their escalations: **about 1-1.5 h**, worst case 2.5 h.
  The escalations run inside the enumeration (pass 3; `enumerate` record `n_escalations`): the floor is capped by
  `M09`'s priced lower 1046.21 against the required `UB - tol = 1050.36`, so without them step 1 would end
  `enumerated (open pricing gaps)` at about 0.6 % (unless pricing `M06` / `M03` lowers `UB` by >= 4 USD).
  Comparison layouts at m = 1 are cache hits. Result: a certified relaxed m = 1 (gap <= 0.25 %) or a bound with the
  escalations used up and at most 2-3 priced layouts with open ILP gaps (`close_reason` says how many).
* Step 1, written m = 1: four unpriced open layouts (`M06`, `M03`, `M05`, `M07`; the first written pricing of `M06`
  will probably lower `UB` and resolve `M07` / `M05` without pricing) plus escalations of `M09` and `M08`:
  **about 2-3 h**. The written LP after the target switch now costs one cold solve (no stale basis).
* Step 2, per target: LP phase <= 80 rounds x 3 budgets x 30 s = <= 2 h (stalls earlier in practice, 30-60 min);
  screen <= 9 pricings = <= 1.5 h; integer phase until the wall, each proposal 0.5 min LP + 6-15 min pricing, i.e. about
  15-25 two-site layouts per target. **4 h per target as given**, LB rises from 674.8 to the LP-phase bound `LB_LP`
  (a few USD at most, so m >= 2 stays uncertified; the honest statement for the paper is the regret interval with
  this bound).
* Step 3: 1-2 min.

Total: about 10-12 h on the machine alone (steps 1 and 2 of both targets); step 1 alone (the m = 1 certificates)
about 4 h. If only one night is available, run step 1 and then step 2 with `--wall-relaxed 2 --wall-written 2`.

Single-command variant (same result, one process for everything; the m = 1 enumeration first, then the Benders
phases for m = 2-4 within each target's wall): `--budgets 1 2 3 4 --certify-budgets 1 --gate report --wall-relaxed 6
--wall-written 6 --reserve-min 30` with the same `--source-dir` / `--out-dir` / `--resume-open` / `--lp-*` flags.

## 6. How the compliance experiment reads the chosen layout

`experiments/r6_fill.py --stage compliance` calls `o2_best_layout(records_path, target='written', m=2)`: the LAST
`budget_result` row with `target = written` and `budget = 2 x 52,150` in the given records file, field `best_layout`.
The second pass appends its rows after the copied first-pass rows, so point it at the second-pass folder:

```
PYTHONPATH=. python3 experiments/r6_fill.py --stage compliance \
  --o2-records outputs/r6_o2/manhattan_pass2/records.jsonl --o2-cache outputs/r6_o2/manhattan_pass2/cache
```

(`--check-o2` with the same `--o2-records` exits 0 once that row exists; `seed_cache` copies the rows of the chosen
layout from `--o2-cache` into the compliance cache.) Until step 2 has run, the last written m = 2 row in that file is
the first pass's (`M08:SC:B3:C2|M09:SC:B3:C2`, `LB None`): a valid incumbent, not a certified optimum; the row's
`certified` / `LB_kind` fields say which it is. `--layout-key` overrides.

## 7. Caveats

* Certificates hold for seeds 0-2 under the all-candidates library convention and the recalibrated prices; every ILP
  value is an upper bound on the unpruned optimum (PRUNING_NYC).
* `LB` in a `budget_result` is now always finite; `LB_kind = superset` means nothing beyond the trivial bound was
  learnt (not the case anywhere above: m = 1 has the enumeration floor, m >= 2 the master over the structural rows).
* The with-cover `--bound-from-cuts` builds the three all-candidates templates (5 GB peak on this machine); use
  `--no-cover` while anything else runs (the single cover row did not change any bound here).
