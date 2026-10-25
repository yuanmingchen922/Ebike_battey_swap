# R6 fill, stage retries: what changed after the longer re-solves (final report)

Date: 2026-10-20. Stages headline, psweep (penalty sweep), vsweep (lateness sweep), fleet and levers of round 6
(`outputs/r6_penalty/<stage>/records.jsonl`) were re-solved where the ILP row was not OPTIMAL or had been cut short
by the laptop sleep (`experiments/r6_fill.py --retry-unsolved`; rule in `notes/DECISIONS.md`, "R6 fill-in script and
the retry rule"). The new rows carry `retry_of`, `retry_reason`, `retry_time_limit_s` and supersede the earlier row
of the same key (last row per key), except rows marked `retry_worse`, which are ignored. headline, psweep, vsweep
and fleet were retried on an x86-64 Linux server at 600 s; levers on the laptop at 1800 s. Prices: P 60 USD per
unserved order, w 18 USD/h from release, v 15 USD/h from the promise ("new prices"); legacy prices P 30 / v 36.

**Every number below was recomputed from the records** by `figs_retries/retries_analysis.py` (no solver run; it
writes `retries_rows.csv`, one per-instance CSV per stage and `retries_numbers.json`). "Before" = the records
without the retry rows, which is what the stage reports `RESULTS_final.md` and `R6_DIGEST.md` used; "after" = last
row per key with `retry_worse` rows ignored, which is what every `--analyse` now reads. Check of the method: the
"before" values reproduce the stage reports and the digest exactly (headline 38.42 ± 3.07 and 25.10 [20.15, 30.06];
psweep 39.70 ± 2.84 and 43.71 / 44.61; vsweep 24.14 ± 10.87 as solved and 31.65 best known; fleet K 8 / B 3
1477.9 [1307.6, 1648.1] and 214.4 / 89.4 / 17.1; levers 46.14 [42.47, 49.80], +228.53 [184.05, 273.00] and
−7.80 [−59.88, 44.28]; saving shares 19.0 / 16.4 / 64.4 %; service share 99.8 %).

Conventions as in the R6 reports: families usd4h, nyc4h, stress4h, stress4h-K8; rules r2, M2, M2+M3 and the best
rule (per-instance minimum of the end-adjusted total); ILP = relaxed-target aggregated ILP (Threads 3, Seed 0);
gap = 100 (best rule − ILP) / best rule per instance on end-adjusted totals, then averaged; exact Student-t 95 %
intervals over seeds, written `mean [lo, hi]` or `± half-width`; differences paired per seed. "Upper limit" = the
gap computed with the solver's lower bound in place of the incumbent (raw bound against the end-adjusted best
rule, so it is an upper limit of the true gap). MIP gaps are Gurobi's relative gaps in percent.

## Summary

- **55 ILP rows were re-solved; 10 are now optimal, 42 are still time-limited with smaller gaps, and 3 fleet
  re-solves ended worse and are ignored.** No retry row is sleep-truncated (runtime ≤ wall time on all server rows),
  every MIP start was accepted, and objective = evaluated cost and `check_ok` hold on all 55.
- **The sleep-truncated cells are repaired and equal the "best-known" values the reports had substituted.** Lateness
  sweep v 36 seeds 5 and 6 are now OPTIMAL at 645.02 and 626.90 USD, exactly the v 25 optimum repriced at v 36 that
  the vsweep report used; the v 36 gap 31.65 ± 6.56 % is now a solved value (10/10 optimal), not a lower bound.
  Penalty sweep usd4h P 80 seed 0 is OPTIMAL at 532.60 USD (the report's corrected value); stress4h P 40 seed 9 is
  OPTIMAL at 847.54 USD.
- **Headline numbers barely move.** usd4h x1.5: 38.42 → **38.44 ± 3.07 % [35.37, 41.51]** (8 optimal + 2
  time-limited at 600 s, MIP gaps 0.87 and 0.90 %; upper limit 38.63); pooled usd4h: 25.10 → **25.11 %
  [20.15, 30.07]** (n 30, 28 optimal); saving 363.17 → 363.32 USD. The paired change against the legacy prices at
  x1.5 is −5.00 ± 3.09 points (p 0.005, 9/10 seeds lower), pooled −2.05 ± 2.00 (p 0.044).
- **Penalty sweep: the stress4h curve is unchanged within 0.1 point up to P 60 and the P 80 point rises from the
  recorded 43.71 to 44.50 ± 3.03 %** (best-known 44.69 ± 3.15, upper limit 45.43). Three P 80 incumbents (seeds 3,
  6, 7) are still 9-16 USD above the repriced P 60 schedule, so P 80 still needs the best-known convention; the
  largest remaining MIP gap fell from 11.63 to 3.38 %. stress4h P 60 (the digest's n = 10 stress4h gap):
  39.70 → 39.73 ± 2.84 %, 5 optimal + 5 time-limited (≤ 0.87 %).
- **Fleet: no design conclusion changes.** Cost-minimal designs (ILP K 8 / B 3, 1477.9 USD, 99.3 % served; rule
  K 8 / B 4), the per-seed argmins, the 9.4 % [6.5, 12.2] design saving and the bike values 4→6 214.1
  [193.7, 234.4], 6→8 89.4 [0.3, 178.5], 8→10 17.1 [−13.2, 47.5] USD are the same to within 0.4 USD. The K 10 /
  B 1 seed-2 cell (991 s sleep-affected run) is now OPTIMAL. The K 10 / B 2 seed-2 cell with the 100.5 % MIP gap was
  not re-solved (plain 600 s limit) and remains excluded by the nesting argument.
- **Levers: the reference incumbents improved by up to 102.7 USD and the lock-out paradox is gone.** Reference gap
  46.14 → **47.59 % [42.16, 53.03]** (1 optimal + 4 time-limited at 1800 s, MIP gaps 0.75-2.87 %; upper limit 48.26).
  No on-site charging costs the ILP **+262.96 USD [216.81, 309.11]** (was +228.53), at least 207.7 USD on every seed
  by the bounds; the demand-charge break-even rises to **≥ 24,900 USD per kW-month** (was ≥ 20,400). The lock-out of
  two spares now costs the ILP **+9.78 USD [−4.88, 24.43]**, positive on 5/5 seeds (was −7.80, negative on 4/5);
  on seed 4 both solves are optimal and the change is exactly +2.52 USD. No lock-out incumbent is below its
  reference any more (three were).
- **Still open:** 42 time-limited rows (headline 2, psweep 19, fleet 12 + 4 never retried, levers 9), all with
  MIP gaps ≤ 3.4 % except fleet K 10 / B 2 seed 2 (100.5 %). The rolling-horizon analysis and the stress fill stage
  were produced before the retried psweep rows were synced (one stress4h P 60 reference row improved by 2.71 USD);
  the effect on the rolling numbers is below 0.001 of the share kept (Section 1, item 9).

---

## 1. Problems and anomalies

1. **Three fleet re-solves ended with a worse incumbent and are ignored (`retry_worse`).** K 4 / B 1 seed 1
   (−3.27 USD; MIP gap 1.56 → 1.53 %), K 6 / B 1 seed 1 (−9.27 USD; 1.54 → 2.40 %) and K 6 / B 3 seed 1 (−1.11 USD;
   0.63 → 0.74 %). All three started from a rule schedule or the previous spare level's incumbent (the rows solved
   before the incumbent-saving change had no saved incumbent) and ran 600 s on the server; the 300 s laptop rows
   remain the rows of these keys, with their 300 s bounds. The retries' own bounds were weaker too, so nothing is
   gained from them. These cells keep their earlier MIP gaps (1.56, 1.54, 0.63 %).
2. **42 of the 55 re-solved rows are still time-limited.** Largest remaining gaps: penalty sweep stress4h P 80
   seed 6 3.38 % (seeds 2-7: 1.7-3.4 %), levers lock-out seed 2 3.26 % and reference seed 2 2.87 %, fleet
   K 4 / B 1 seed 0 1.04 % (the kept 300 s rows of item 1 up to 1.56 %), headline x1.5 seeds 0 and 8 0.87 / 0.90 %.
   Every stage result below states which cells these are.
3. **Four fleet rows were never re-solved** (plain 600 s TIME_LIMIT rows are only re-solved above their own limit,
   and the default retry limit was 600 s): K 8 / B 1 seed 1 (1.34 %), K 8 / B 1 seed 2 (0.62 %), K 8 / B 2 seed 2
   (0.31 %) and **K 10 / B 2 seed 2 (100.5 %)**. The last is the only incumbent in the five stages known to be far
   from optimal: it is 65.7 USD above the K 8 / B 2 seed-2 incumbent, which a 10-bike schedule can copy. It still
   needs `--time-limit 1800` (about 9 h for the 20 rows that would be selected) or a warm start from the K 8 / B 2
   schedule.
4. **Repriced schedules still beat the recorded incumbent in four stress4h cells of the penalty sweep** (seven
   before): P 30 seed 5 by 0.12 USD, and P 80 seeds 3, 6, 7 by 11.2, 9.2 and 15.9 USD (the P 60 schedule repriced to
   P 80; before the retry the largest such margin was 117.5 USD on seed 3). The P 80 column therefore still has a
   recorded and a best-known value (44.50 vs 44.69 %). On usd4h no recorded cell is beaten any more. The only
   OPTIMAL cell beaten by a repriced schedule on the raw objective is stress4h P 40 seed 9, by 0.047 USD, within the
   1e-4 relative MIP tolerance (0.085 USD).
5. **The retry's bound is weaker than the first solve's in 15 rows** (headline x1.5 seed 0; psweep stress4h P 30
   seed 2, P 40 seed 7, P 60 seed 1, P 80 seeds 2, 3, 7; fleet K 4 / B 1-3 seed 0, K 6 / B 1 seeds 0-1, K 6 / B 2-3
   seed 1; levers reference seed 3). Because the model is identical (`n_vars`, `n_binaries`, `n_rows`, `n_arcs` equal
   on 55/55 retry rows; demand and order hashes equal), the valid lower bound of a cell is the larger of the two,
   but the stage analyses read only the last row's bound. Their upper limits are therefore slightly conservative:
   the x1.5 upper limit is 38.63 with the retry bounds and 38.62 with the best bounds; fleet K 4 / B 1 seed 0 shows
   a MIP gap of 1.04 % at an unchanged incumbent where 0.88 % is proven.
6. **Content keys drifted on the server.** All 16 fleet retry rows carry `key_md5_rebuilt` (the instance rebuilt on
   x86-64 hashes differently); they were matched by (cell, seed, target), the demand / order hashes and the model
   dimensions agree with the replaced rows on 16/16, and the rows keep the recorded key, so they supersede the old
   rows correctly. The grid stages key by labels (no drift). The levers retry ran on the laptop (no drift). The 16
   orphan case notes left by the failed first server attempt were pruned to `fleet/cases_orphans.jsonl` and do not
   hide any cell (48 cases, 48 ILP rows).
7. **One runtime overshoot:** levers no-on-site-charging seed 2 ran 1810.6 s against 1800 s (Gurobi's limit check
   between nodes). No consequence. No retry row is sleep-truncated: on the 28 grid retry rows Gurobi's runtime is
   below the measured wall time (difference −7.9 to −9.5 s; the limit was 600 s), and the X5 rows ran at or below
   their limit.
8. **Wall clocks of the retry rows run from 2026-10-19 16:31 to 2026-10-20 02:41** as recorded; the server rows
   carry the server's clock, the levers rows the laptop's, so the range mixes two clocks.
9. **Downstream joins were produced before the server rows were synced** (the four server stages' `records.jsonl`
   have mtime 23:52:18 on 2026-10-19; `rolling/RESULTS.md` 23:50:49; `r6_fill/stress/RESULTS.md` 23:41:55).
   - Rolling horizon: its stress4h offline reference for seed 1 is the psweep P 60 row, now 1031.31 instead of
     1034.02 USD (end-adjusted); seeds 2 and 3 did not change. Recomputed from `rolling/per_instance.csv`, the share
     of the gap kept online on stress4h is 0.526 ± 0.182 instead of 0.526 ± 0.183 (ratio of means 0.5294 vs
     0.5299), foresight 301.3 instead of 300.8 USD. `r6_penalty.py --stage rolling --analyse` should still be re-run
     so that the files agree with the records; no conclusion changes.
   - Stress fill stage: its price of recovery on stress4h 6 bikes takes the relaxed reference from its own solve on
     seeds 0-2 (seed 1: 1033.05 USD, TIME_LIMIT) and from psweep on seeds 3-4 (unchanged by the retry). The retried
     psweep seed-1 incumbent (1031.31) is 1.74 USD better than the stress stage's own; with the best known relaxed
     value the seed-1 price of recovery would read 4.23 instead of 2.49 USD. For the stress report writer.
   - levers_ext joins the retried reference rows (1037.94 / 1386.87 / 1215.46 / 1419.99 / 1322.79 USD raw in
     `levers_ext/cases_wide_joined.csv`), so it is consistent with this report. Its "reused: true" lines for
     `lockout0.1` seeds 0-4 are legitimate: each shares its content key with `lockout0.05` of the same seed (both
     shares round to one locked battery), so one solve serves both labels.
10. **The auto-generated `RESULTS.md` files after the retry are numerically right** (their key tables, the levers
    effects and the fleet designs match this recomputation to rounding) but fleet and levers still print
    "Anomalies: none", which misses items 1-5, and the psweep key table shows the recorded P 80 value (44.50) without
    the best-known one.

## 2. Coverage

**Retried rows** (`retries_rows.csv`; one row per re-solved ILP, matched to the row it replaces by `retry_of`).

| stage | rows retried | reason | limit before → retry | machine | now optimal | still time-limited | worse (ignored) | max MIP gap after (%) | total incumbent improvement (USD) |
|---|---|---|---|---|---|---|---|---|---|
| headline | 3 (usd4h x1.5 seeds 0, 5, 8) | not optimal | 300 → 600 s | server | 1 (seed 5) | 2 | 0 | 0.90 | 4.7 |
| psweep | 23 (stress4h P 30: 3, P 40: 5, P 60: 6, P 80: 8; usd4h P 80: 1) | 21 not optimal, 2 sleep-truncated | 300 → 600 s | server | 4 | 19 | 0 | 3.38 | 238.5 |
| vsweep | 2 (usd4h P 60 / v 36 seeds 5, 6) | sleep-truncated | 300 → 600 s | server | 2 | 0 | 0 | - | 778.5 |
| fleet | 16 (K 4 seeds 0-1: 8; K 6 seeds 0-2: 7; K 10 / B 1 seed 2) | 15 not optimal, 1 sleep-truncated | 300 (K 4, 6) / 600 (K 10) → 600 s | server | 1 (K 10 / B 1 seed 2) | 12 | 3 | 1.04 (kept rows 1.56) | 29.1 |
| levers | 11 (reference and lock-out seeds 0-4; no on-site charging seed 2) | not optimal | 600 → 1800 s | laptop | 2 (reference and lock-out, seed 4) | 9 | 0 | 3.26 | 262.7 |
| all | 55 | 50 / 5 | | | 10 | 42 | 3 | | 1313.5 |

Checks on the 55 retry rows: same key as the replaced row 55/55 (fleet by (cell, seed, target) with
`key_md5_rebuilt`, item 6); model dimensions equal 55/55; demand and order hashes equal 55/55; MIP start accepted
55/55 (grid stages: the saved incumbent `prior_incumbent`; fleet: a rule or the previous spare level's incumbent;
levers: the lock-out incumbent with transfers stripped seeds the reference, the rules seed the lock-out);
`obj_eq_eval` and `check_ok` true 55/55; `retry_worse` 3/55; no ERROR or SKIPPED_BUDGET rows added.

**ILP status after the retry, per stage** (relaxed targets unless stated):

| stage | ILP rows | optimal | time-limited (cells; MIP gap %) |
|---|---|---|---|
| headline | 40 relaxed + 10 written | 38 + 10 | usd4h x1.5 seeds 0 (0.87), 8 (0.90) at 600 s |
| psweep usd4h | 50 | 50 | - |
| psweep stress4h | 50 | 31 (P 20: 10, P 30: 7, P 40: 7, P 60: 5, P 80: 2) | P 30 seeds 2, 5, 6 (≤ 0.58); P 40 seeds 2, 6, 7 (≤ 0.40); P 60 seeds 1, 2, 3, 5, 6 (≤ 0.87); P 80 seeds 1-3, 5-9 (0.51-3.38) |
| vsweep | 50 | 50 | - |
| fleet | 48 | 29 | 19: K 4 seeds 0-1 all B (0.33-1.56); K 6 / B 1 seeds 0-2, B 2 seeds 1-2, B 3 seeds 1-2 (0.35-1.54); K 8 / B 1 seeds 1-2, B 2 seed 2 (0.31-1.34, not retried); K 10 / B 2 seed 2 (100.5, not retried) |
| levers | 15 | 6 | reference seeds 0-3 (1.50, 0.75, 2.87, 1.00); lock-out seeds 0-3 (2.20, 2.23, 3.26, 1.05); no on-site charging seed 2 (0.32) |

Nothing else changed: rule rows, instances, prices and the network, rolling and rl stages are untouched.

## 3. What changed, stage by stage

### 3.1 Headline (usd4h x1.5; the pooled usd4h gap)

Per-cell change (end-adjusted ILP cost and gap; seeds 1-4, 6, 7, 9 were optimal before and are unchanged):

| seed | before: status, MIP gap, ILP (USD), gap (%) | after: status, MIP gap, ILP (USD), gap (%) |
|---|---|---|
| 0 | TIME_LIMIT 1.07 %, 1091.37, 37.13 | TIME_LIMIT 0.87 %, 1088.71, 37.28 |
| 5 | TIME_LIMIT 0.33 %, 1302.78, 40.65 | **OPTIMAL** (150 s), 1300.87, 40.74 |
| 8 | TIME_LIMIT 0.91 %, 1324.35, 41.14 | TIME_LIMIT 0.90 %, 1324.28, 41.14 |

Group values (n = 10 per group, 30 pooled):

| quantity | before (R6 reports) | after the retry |
|---|---|---|
| gap usd4h x1.5 | 38.42 ± 3.07 [35.35, 41.49]; 7 OPT + 3 TL (≤ 1.07 %) | **38.44 ± 3.07 [35.37, 41.51]**; 8 OPT + 2 TL (≤ 0.90 %) |
| upper limit from the bound, x1.5 | 38.63 ± 3.09 | 38.63 ± 3.09 (38.62 with the best bound of each cell) |
| saving usd4h x1.5 (USD) | 805.74 ± 112.16 | 806.21 ± 112.03 |
| x1.5 gap, new − legacy prices (paired) | −5.03 ± 3.08, p 0.005, 9/10 lower | **−5.00 ± 3.09**, p 0.005, 9/10 lower; saving +10.15 ± 72.96 (p 0.76) |
| gap usd4h pooled | 25.10 ± 4.96 [20.15, 30.06]; 27 OPT + 3 TL | **25.11 ± 4.96 [20.15, 30.07]**; 28 OPT + 2 TL |
| upper limit, pooled | 25.32 | 25.32 |
| saving usd4h pooled (USD) | 363.17 [234.98, 491.35] | **363.32 [235.07, 491.57]** |
| pooled gap, new − legacy (paired) | −2.06 ± 2.00, p 0.044, 21/30 lower | −2.05 ± 2.00, p 0.044, 21/30 lower; saving −0.90 ± 27.48 |
| saving shares, pooled: lateness / response / unserved | 19.0 / 16.4 / 64.4 % | **19.1 / 16.8 / 63.9 %** (travel 0.14, electricity 0.17, end adjustment −0.13) |
| service share of the pooled saving | 99.8 % | 99.8 % (99.82) |
| ILP late orders per window, pooled / x1.5 | 4.07 ± 1.48 / 8.40 ± 2.19 | **3.90 ± 1.36** / 7.90 ± 1.80 (best rule 13.77 / 24.20, unchanged) |
| served share, ILP − best rule, pooled | +0.081 ± 0.027 | +0.081 ± 0.026 |
| detour per swap saved, pooled (km) | 0.357 ± 0.129 | 0.379 ± 0.125 |
| ILP end adjustment larger by, pooled (USD) | 0.461 ± 0.069 | 0.464 ± 0.070 |
| electricity saving, pooled (USD) | 0.616 ± 0.049 | 0.616 ± 0.049 |
| ILPs of the headline solved to optimality | 47 / 50 | **48 / 50** |
| x1.5 relaxed ILP runtime, mean / max (s) | 215.5 / 300 | 260.5 / 600 |
| minimum instance gap usd4h / x1.5 | 4.92 (x0.75) / 28.26 | unchanged |

usd4h x0.75, x1 and nyc4h are untouched (all optimal before). The best-rule identity does not change (r2 on 8 of
the x1.5 seeds, M2 on 2).

### 3.2 Penalty sweep (stress4h P 30-80, usd4h P 80)

Recorded = the incumbent of the row; best-known = the cheapest of the seed's five ILP schedules repriced at P
(exact: same instance and model at every P); upper limit = gap against the best bound at any P' ≤ P. n = 10 per row.

| family, P | before: recorded / best-known; OPT / TL (max MIP gap) | after: recorded / best-known / upper limit; OPT / TL (max MIP gap) | cells still beaten by a repriced schedule |
|---|---|---|---|
| stress4h P 20 | 33.21 ± 2.48; 10 / 0 | unchanged | 0 |
| stress4h P 30 | 33.64 ± 2.22; 7 / 3 (0.58) | 33.64 ± 2.22 / 33.64 / 33.86; 7 / 3 (0.58) | seed 5 by 0.12 USD |
| stress4h P 40 | 35.14 ± 2.17 / 35.15; 5 / 5 (0.75) | **35.21 ± 2.19 [33.02, 37.41]** / 35.21 / 35.42; 7 / 3 (0.40) | 0 |
| stress4h P 60 | 39.70 ± 2.84; 4 / 6 (1.12) | **39.73 ± 2.84 [36.89, 42.57]** / 39.73 / 39.98; 5 / 5 (0.87) | 0 |
| stress4h P 80 | 43.71 ± 2.65 / 44.61 ± 3.15; 2 / 8 (11.63) | **44.50 ± 3.03 [41.47, 47.53]** / **44.69 ± 3.15 [41.53, 47.84]** / 45.43 ± 3.20; 2 / 8 (3.38) | seeds 3, 6, 7 by 11.2 / 9.2 / 15.9 USD |
| usd4h P 80 | 29.56 ± 8.72 (one sleep cell at 0 %) / 30.66 ± 6.73; 9 / 1 (94.3) | **30.66 ± 6.73 [23.93, 37.39]** / 30.66 / 30.83; 10 / 0 (0.01) | 0 |
| usd4h P 20-60 | 22.29 / 22.48 / 23.79 / 27.34; all OPT | unchanged | 0 |

Per-cell changes among the 23 retried rows: 17 incumbents improved by 0.12-106.3 USD (largest stress4h P 80 seed 3,
1116.37 → 1010.00 USD end-adjusted, cell gap 44.23 → 49.54 %; seed 2 +35.8 USD, 45.35 → 47.10 %), 6 kept the same
incumbent with a smaller MIP gap. The stress4h P 80 seed-3 incumbent now drops one order (it dropped three before,
two at P 60), so the earlier inconsistency with monotonicity in P is gone.

Paired differences to P 60 and consecutive steps on stress4h (points; recorded, with best-known in brackets where
different):

| contrast | before | after |
|---|---|---|
| P 20 − P 60 | −6.49 ± 3.08 | −6.52 ± 3.07 |
| P 30 − P 60 | −6.06 ± 2.37 | −6.09 ± 2.36 |
| P 40 − P 60 | −4.56 ± 1.50 | −4.52 ± 1.46 (0/10 seeds higher) |
| P 80 − P 60 | +4.01 ± 1.50 (best-known +4.91 ± 0.71) | **+4.77 ± 0.74** (best-known +4.96 ± 0.70); 10/10 seeds higher |
| step 30 → 40 | +1.50 ± 0.89 | +1.57 ± 0.92 |
| step 40 → 60 | +4.56 ± 1.50 | +4.52 ± 1.46 |
| step 60 → 80 | +4.01 ± 1.50 | +4.77 ± 0.74 |
| usd4h step 60 → 80 | +2.22 ± 3.61 (best-known +3.31 ± 1.66) | **+3.31 ± 1.66** recorded |
| ILP end-adjusted cost at P 80 − at P 60, stress4h (USD) | +65.6 ± 36.3 | +50.3 ± 24.5 |
| ILP served share at P 80 − at P 60, stress4h | +0.015 ± 0.016 | +0.021 ± 0.012 |

The statements of the psweep report stand: the mean gap rises at every step from P 40 on (significant), the 20 → 30
step is flat, and per seed the gap falls at least once on usd4h seeds 5-8 and stress4h seeds 5 and 8 (unchanged).
The P 80 recorded value now lies within 0.2 points of the best-known one instead of 0.9.

### 3.3 Lateness sweep (usd4h, P 60, v 36)

| quantity | before (as solved / best-known) | after |
|---|---|---|
| v 36 ILP status | 8 OPT + 2 TL (seeds 5, 6: the rule MIP start, sleep-truncated) | **10 OPT** (seeds 5 and 6 solved in 108 and 176 s; max MIP gap 9e-5) |
| v 36 gap | 24.14 ± 10.87 as solved / 31.65 ± 6.56 best-known (lower bound) | **31.65 ± 6.56 [25.09, 38.22]**, 10/10 positive, min-max 12.9-42.6 |
| seeds 5 / 6 cell gap | 0.00 / 0.00 (as solved); 32.47 / 42.63 (best-known) | 32.47 / 42.63 |
| v 36 ILP end-adjusted cost; saving (USD) | 689.5 ± 133.5; 224.1 ± 116.3 as solved | 611.7 ± 35.5; 301.8 ± 90.3 |
| v 36 − v 15 (paired) | +4.31 ± 1.53 best-known | **+4.31 ± 1.53** (p 1e-4), 10/10 seeds |
| v 36 − v 25 | +2.18 ± 0.78 best-known | +2.18 ± 0.78 |
| slope, points per 10 USD/h | 2.09 ± 0.75 best-known (as solved −0.44 ± 3.55) | **2.09 ± 0.75**, monotone on 10/10 seeds |
| v effect / P effect of the old-to-new price change (Shapley) | −5.05 ± 1.86 / +4.12 ± 3.51 | −5.05 ± 1.87 / +4.12 ± 3.51 |
| v 36 ILP late orders; late hours per window | 2.8; 0.42 h (best-known) | 2.8 ± 1.7; 0.42 ± 0.29 h |

The solved v 36 optima equal the v 25 optimum repriced at v 36 on 8 of 10 seeds (difference 0.00 USD, seeds 5 and 6
included) and are 2.73 and 3.45 USD below it on seeds 7 and 8 (solved before), so the report's "best-known"
substitution for seeds 5 and 6 was exact. The bridge (P 30, v 36: 28.28 ± 7.36 %) and v 8 / v 15 / v 25 are untouched.

### 3.4 Fleet grid (stress4h, 48 orders, 0.6 kWh; K 4-10 x B 1-4; seeds 0-2)

Cells whose row changed (ILP system cost = end-adjusted total + K x 88.94 USD; seed means, n = 3):

| cell | ILP system cost before → after (USD) | statuses, MIP gaps (%) before → after | per-seed incumbent change (USD) |
|---|---|---|---|
| K 4 / B 1 | 1740.0 → 1740.0 | TL 0.88, TL 1.56, OPT → TL 1.04, TL 1.56 (kept), OPT | 0 (s0), worse retry ignored (s1) |
| K 4 / B 2 | 1729.7 → 1729.0 | TL 0.81, TL 1.21, OPT → TL 0.86, TL 0.90, OPT | 0, −2.23 |
| K 4 / B 3 | 1729.7 → 1729.0 | TL 0.72, TL 1.00, OPT → TL 0.76, TL 0.50, OPT | 0, −2.07 |
| K 4 / B 4 | 1730.7 → 1730.0 | TL 0.79, TL 0.97, OPT → TL 0.62, TL 0.33, OPT | 0, −2.04 |
| K 6 / B 1 | 1516.0 → 1514.2 | TL 1.30, 1.54, 1.21 → TL 0.87, 1.54 (kept), 0.76 | −4.25, worse ignored, −1.03 |
| K 6 / B 2 | 1480.6 → 1478.5 | OPT, TL 0.94, TL 1.14 → OPT, TL 0.81, TL 0.54 | 0, −1.52, −5.07 |
| K 6 / B 3 | 1478.8 → 1478.8 | OPT, TL 0.63, TL 0.64 → OPT, TL 0.63 (kept), TL 0.35 | 0, worse ignored, 0 |
| K 10 / B 1 | 1664.1 → 1660.5 | OPT, OPT, TL 2.31 (991 s run) → **3 OPT** | 0, 0, −10.84 |

Design conclusions, before → after:

| quantity | before | after |
|---|---|---|
| ILP seed-mean cost-minimal design | K 8 / B 3, 1477.9 [1307.6, 1648.1], served 99.3 % [96.3, 102.3], 3/3 OPT; not certified | **unchanged** |
| ILP per-seed argmin | K 6 / B 2 (1321.5), K 8 / B 2 (1535.8), K 8 / B 3 (1494.2), all OPT, served 100 / 97.9 / 100 % | unchanged |
| cells within 3 USD of the minimum | K 8 / B 3 1477.9, K 8 / B 2 1478.1, K 8 / B 4 1478.6, K 6 / B 3 1478.8, K 6 / B 4 1479.7, K 6 / B 2 1480.6 | same six; K 6 / B 2 now 1478.5 (third) |
| competitors whose mean bound (raw basis) is below the K 8 / B 3 mean 1475.4 | K 6 / B 2 1471.5, K 6 / B 3 1472.0, K 8 / B 2 1475.2 (+ K 10 / B 2, nesting) | K 6 / B 2 1471.8, K 6 / B 3 1473.0, K 8 / B 2 1475.2 (+ K 10 / B 2) |
| certified statement | 6-8 bikes with 2-3 spares per site | **unchanged** |
| per-seed certificate margin of every K 4 cell (raw) | ≥ 240.8 USD | ≥ 240.2 USD with the retry bounds (≥ 240.8 with the best bound per cell) |
| K 4 − K 8 (best spare level per seed; USD / served points) | +252.1 [61.3, 442.8]; −25.0 [−35.4, −14.6] | +251.4 [61.0, 441.8]; −25.0 |
| K 6 − K 8 | +1.4 [−176.4, 179.2] | +1.1 [−176.0, 178.3] |
| K 10 − K 8 | +143.6 [83.2, 204.0] | unchanged |
| bike 4 → 6 at B 3 (USD per bike; bound range of the mean) | 214.4 [195.3, 233.5]; [210.9, 216.9]; pays on 3/3 | **214.1 [193.7, 234.4]**; [211.7, 216.1]; pays on 3/3; 4/6 solves TL (0.33-1.04 %) |
| bike 6 → 8 at B 3 | 89.4 [0.3, 178.5]; [87.3, 89.4]; pays on 2/3 | **89.4 [0.3, 178.5]**; [87.8, 89.4]; 2/6 TL (0.35, 0.63 %) |
| bike 8 → 10 at B 3 | 17.1 [−13.2, 47.5]; 6/6 OPT | unchanged |
| spare 1 → 2 at K 6 / 2 → 3 at K 6 / 3 → 4 at K 6 | 11.8 [−14.0, 37.6] / 0.62 [−1.59, 2.83] / −0.31 | 11.9 [−16.8, 40.7] / **−0.11 [−0.86, 0.64]** / −0.31 |
| spare values at K 8 (1 → 2, 2 → 3, 3 → 4) | 22.9, 0.08, −0.25 | unchanged (K 8 not retried) |
| spare 3 → 4 at K 4 | −0.33 [−0.38, −0.29]; not certified on seeds 0-1 (bounds allow +2.9 / +4.3) | −0.33 [−0.34, −0.33]; still not certified (mean bound range [−2.13, 1.06]) |
| rule − ILP at each policy's own per-seed design | 150.1 [90.0, 210.2] USD, 9.4 % [6.5, 12.2], equal service on every seed | **unchanged** |
| gap at K 4 / B 1; K 4 / B 2-4 | 37.9 [23.5, 52.3]; 32.3-32.5 | 37.9; 32.4-32.5 |
| gap pooled by spare level B 1 / B 2 / B 3 / B 4 (n 12) | 48.5 / 32.4 / 24.9 / 22.0 | 48.6 / 32.5 / 24.9 / 22.0 |
| K 10 / B 2 seed 2 | TL 100.5 %, incumbent 65.7 USD above K 8 / B 2 | **unchanged (not re-solved)** |

The third spare at 6 bikes was worth 0.62 USD before and is now −0.11 USD: the retry removed the only positive
third-spare values at K 6 (seeds 1-2, which were within the MIP gaps). The fleet report's statement "a third spare
adds at most 1.5 USD on any seed" now reads "at most 0.9 USD (K 8 seed 2)".

### 3.5 Station levers (stress4h-K8, seeds 0-4)

Per-lever values (ILP end-adjusted, USD per window; raw-total brackets for the effects):

| lever | before: ILP cost; status (MIP gaps %); gap; upper limit | after: ILP cost; status (MIP gaps %); gap; upper limit |
|---|---|---|
| reference | 1313.6 [1155.2, 1471.9]; 0 OPT + 5 TL (6.87, 0.83, 10.48, 1.36, 0.85); 46.14 [42.47, 49.80]; 48.31 | **1278.7 [1086.9, 1470.5]**; 1 OPT + 4 TL (1.50, 0.75, 2.87, 1.00, 0); **47.59 [42.16, 53.03]**; 48.26 |
| no on-site charging | 1542.1; 4 OPT + 1 TL (seed 2: 0.72); 41.85 [37.85, 45.86]; 41.98 | 1541.7; 4 OPT + 1 TL (seed 2: 0.32); 41.87 [37.86, 45.88]; 41.95 |
| lock-out of 2 spares | 1305.8; 0 OPT + 5 TL (5.24, 3.64, 5.62, 1.23, 0.39); 47.69 [43.43, 51.94]; 49.35 | **1288.5**; 1 OPT + 4 TL (2.20, 2.23, 3.26, 1.05, 0); 48.39 [43.34, 53.44]; 49.30 |

Reference incumbents per seed, before → after (end-adjusted): 1099.06 → 1040.18, 1388.98 → 1388.97,
1320.27 → 1217.50, 1427.43 → 1422.01, 1332.07 → 1324.93 (optimal at 1288 s). The reference gap per seed is now
53.5 / 45.3 / 51.0 / 44.6 / 43.6 %. The ILP served share at the reference is 0.925 [0.877, 0.973] (was 0.919); the
best rule (r2 on 15/15 cells) is unchanged at 2435.1 USD and 0.653 served.

| effect (lever − reference, paired, n = 5) | before | after |
|---|---|---|
| no on-site charging, ILP (USD) | +228.53 [184.05, 273.00]; 5/5 > 0; proven bracket lower end ≥ 169.6 per seed | **+262.96 [216.81, 309.11]**; 5/5 > 0; per seed 301.4, 208.0, 281.4, 280.5, 243.4; brackets [301.3, 316.8], [207.7, 218.1], [276.3, 316.1], [280.1, 294.3], [243.2, 243.2]; **lower end ≥ 207.7 on every seed** |
| no on-site charging, best rule (USD) | +213.51 [123.95, 303.07], 5/5 > 0 | unchanged |
| no on-site charging, ILP − rule change | +15.0 [−62.1, 92.2] | +49.4 [−48.1, 147.0] |
| no on-site charging, gap change (points) | −4.28 [−5.84, −2.73], 5/5 < 0 | **−5.72 [−8.44, −3.01]**, 5/5 < 0 |
| no on-site charging, ILP / rule served share (points) | −9.7 [−12.2, −7.2] / −13.8 [−16.3, −11.2] | −10.3 [−12.5, −8.1] / −13.8 |
| demand-charge break-even (USD per kW-month, min over seeds; incumbents) | ≥ 21,700 (≥ 20,400 with the P 0 bound) | **≥ 24,900** (per seed 36,200 / 24,900 / 33,700 / 33,600 / 29,200; the same with the bound, the seed-1 P 0 solve is optimal) |
| lock-out of 2 spares, ILP (USD) | −7.80 [−59.88, 44.28]; 1/5 > 0; lock-out incumbent below the reference on seeds 0, 2, 4 by 15.8 / 66.7 / 4.7 | **+9.78 [−4.88, 24.43]**; **5/5 > 0**; per seed 8.89, 30.31, 5.29, 2.42, 1.99; no lock-out incumbent below its reference |
| lock-out, proven range of the true change per seed (restriction: ≥ 0) | [0, 59.5], [0, 62.4], [0, 71.4], [0, 19.6], [0, 6.6] | [0, 25.3], [0, 41.3], [0, 40.7], [0, 17.1], **exactly 2.52 (both solves optimal)** |
| lock-out, best rule (USD) | +60.11 [−95.75, 215.97] (seed 1: +284.23) | unchanged |
| lock-out, gap change (points) | +1.55 [−0.40, 3.50], 5/5 > 0 | +0.80 [−1.74, 3.34], 2/5 > 0 |
| reference gap with min(reference, lock-out) incumbent (raw) | ≥ 46.91 [42.54, 51.28] | 47.65 [42.20, 53.09] (= the reference's own value) |

## 4. Comparison with the legacy prices on the same instances

Only the new-price side changed; the legacy side is the round-5 record (headline `r5_x1_headline`, fleet and
levers `r5_x5_stress`; vsweep bridge P 30 / v 36 for the lateness sweep). Values before the retry in parentheses.

| quantity | legacy prices (P 30, v 36) | new prices, after the retry | new − legacy (paired) |
|---|---|---|---|
| headline gap usd4h x1.5 (n 10) | 43.45 ± 5.86 (10 OPT) | 38.44 ± 3.07 (8 OPT + 2 TL ≤ 0.90 %) | **−5.00 ± 3.09** (−5.03), p 0.005, 9/10 lower; saving +10.2 ± 73.0 USD |
| headline gap usd4h pooled (n 30) | 27.17 ± 5.96 | 25.11 ± 4.96 | −2.05 ± 2.00 (−2.06), p 0.044; saving −0.9 ± 27.5 USD |
| headline gap usd4h x0.75, x1, nyc4h | 9.78, 28.28, 27.37 | 9.56, 27.34, 27.88 | −0.23 ± 2.55, −0.93 ± 4.86, +0.51 ± 5.05 (unchanged) |
| lateness sweep: gap at P 60 / v 36 vs the bridge P 30 / v 36 (n 10) | 28.28 ± 7.36 (10 OPT) | 31.65 ± 6.56 (now 10 OPT) | P effect at v 36 +3.38 ± 3.70; v effect at P 30 −5.80 ± 2.23; Shapley −5.05 ± 1.87 (v) / +4.12 ± 3.51 (P) (unchanged) |
| penalty sweep, stress4h at P 60 vs legacy (n 10; legacy 5 OPT at 300 s + 5 TL at 120 s) | 41.38 ± 2.71 | 39.73 ± 2.84 (39.70) | −1.65 ± 2.75 (−1.68 ± 2.76 before) |
| penalty sweep, stress4h at P 80 vs legacy (best-known) | 41.38 ± 2.71 | 44.69 ± 3.15 (44.61) | +3.30 ± 3.37 (+3.23 ± 3.36 before) |
| fleet: ILP served share on the 24 shared instances (seeds 0-1, K 4-8, 0.6 kWh; legacy 23 OPT + 1 TL) | 0.65-0.97 by cell | +4.95 ± 1.21 [3.74, 6.16] points above legacy (was +4.9 [3.7, 6.2]); by fleet size +6.5 / +6.3 / +2.1 | - |
| fleet: cross-pricing check on the 24 shared instances | legacy schedule repriced to the new prices | never below the new incumbent (0/24; mean advantage of the own-price schedule 44.7 [34.0, 55.4] USD); new schedule repriced to the legacy prices never below the legacy optimum (0/24; 54.9 [37.4, 72.3]) | - |
| fleet: ILP seed-mean argmin on the shared seeds, K ≤ 8 | K 4 / B 2, 1310.1 USD, served 69.8 % | K 6 / B 2, 1443.0 USD, served 95.8 % (was K 6 / B 3, 1443.1; K 6 / B 3 is 0.1 USD behind; both time-limited on seed 1) | - |
| levers: ILP change without on-site charging, seeds 0-2 (legacy 300 s) | +79.45 [19.20, 139.70] | **+263.62 [141.48, 385.77]** (210.42) | **+184.18 [122.28, 246.07]** (+130.98) |
| levers: gap at the reference, seeds 0-2 | 45.89 [44.28, 47.50] (1 OPT + 2 TL 1.20 / 1.37 %) | 49.94 [39.57, 60.31] (47.68) | +4.05 [−6.83, 14.93] (+1.79) |
| levers: gap at the reference, seeds 0-4 (legacy = round-5 core at 600 s: 2 OPT + 3 TL ≤ 1.25 %) | 45.51 [40.76, 50.26] | 47.59 [42.16, 53.03] (46.14) | +2.08 [−4.54, 8.70] (+0.62) |
| levers: gap without on-site charging, seeds 0-2 | 34.90 [31.26, 38.54] | 43.60 [36.43, 50.77] (43.57) | +8.70 (+8.67) |
| levers: gap change without on-site charging, seeds 0-2 (points) | −10.99 [−14.50, −7.48] | −6.34 [−12.09, −0.59] (−4.11) | +4.65 (+6.88) |
| levers: gap with the lock-out, seeds 0-2 | 45.15 [43.32, 46.98] | 51.21 [46.98, 55.43] (50.07) | +6.06 [2.09, 10.02] (+4.92) |
| levers: ILP change with the lock-out, seeds 0-2 | −2.60 [−10.62, 5.42] (TL 0.14-0.82 %) | +14.83 [−18.77, 48.43] (−11.17) | not a clean contrast (MIP gaps 2.2-3.3 % on the new side) |

Rule rows are identical in both rounds on every shared instance (the rules do not read the prices on these
families), so every legacy-vs-new contrast above is a pure price effect on the ILP side plus the new incumbents.

## 5. Interpretation

**Shown by the records**

- The retries change no conclusion of the R6 digest. Every headline number moves by less than its rounding
  (x1.5 gap +0.02 points, pooled gap +0.01, saving +0.15 USD), the penalty and lateness curves keep their shape and
  significance, the fleet designs, certificates and marginal values are the same to within 0.4 USD, and the levers
  effects keep their sign and significance.
- The three cells the digest reported with substitutes (vsweep v 36 seeds 5-6, psweep usd4h P 80 seed 0) are now
  solved and equal the substitutes exactly, which validates the repricing argument used there.
- The levers stage is where the retries matter. The reference incumbents were up to 10.5 % above their bounds at
  600 s; at 1800 s they are within 0.75-2.87 %, the reference gap rises from 46.1 to 47.6 % (upper limit 48.3 % in
  both cases, so the true value sits in a narrower band), the no-on-site-charging effect rises from +228.5 to
  +263.0 USD with a proven floor of 207.7 USD on every seed, and the lock-out of two spares is now a small positive
  cost on every seed (certified +2.52 USD on seed 4), consistent with it being a restriction. The demand-charge
  break-even rises accordingly to about 24,900 USD per kW-month.
- The penalty sweep's P 80 point on stress4h is the only sweep value that moves visibly (+0.8 points recorded),
  because its incumbents were the worst converged; the recorded and best-known values now differ by 0.2 points.
- The fleet retries sharpen certificates slightly (K 6 / B 2 and K 6 / B 3 mean bounds 1471.8 / 1473.0 against
  the K 8 / B 3 mean 1475.4) but do not close them; "6-8 bikes with 2-3 spares per site" remains the certified
  statement, and the third spare at 6 bikes is now worth nothing (−0.11 [−0.86, 0.64] USD).

**Suggested, not shown**

- The remaining time-limited cells (MIP gaps ≤ 3.4 % apart from K 10 / B 2 seed 2) would probably move the
  stress4h P 80 gap and the levers reference gap by a fraction of a point each; the upper limits (45.43 % and
  48.26 %) bound how far.
- The three fleet re-solves that ended worse suggest that a 600 s solve from a rule start on the server is not
  reliably better than a 300 s solve on the laptop; a warm start from the saved incumbent (now written for every
  cell) should be used for any further retry.
- The K 10 / B 2 seed-2 cell will not improve without a warm start from the K 8 / B 2 schedule or a much longer
  limit; the nesting argument that excludes it from the design conclusions does not depend on the solver.

## 6. Figures (`figs_retries/`, PDF and 300-dpi PNG, Okabe-Ito colours; script `retries_analysis.py`)

- `fig_retry_overview`: (a) MIP gap before vs after for the 55 re-solved rows by stage (filled = optimal after the
  retry, hollow = still time-limited, crosses = worse incumbent, ignored); (b) improvement of the incumbent per row
  (symlog axis), with the largest improvements listed.
- `fig_retry_price_curves`: (a) gap vs P on stress4h and usd4h, recorded values before (hollow) and after (filled)
  the retry with 95 % intervals and the upper limit from the bound; (b) gap vs v on usd4h at P 60, as solved before
  (hollow; the contaminated v 36 point) and after the retry, with the best-known value used before and the legacy
  bridge.
- `fig_retry_levers_fleet`: (a) station levers per seed: ILP incumbent before (hollow) and after (filled; circle =
  optimal) with the proven lower bound; (b) fleet grid: value of an added bike at 3 spares per site before and after,
  with per-seed values and the range allowed by the bounds.

## 7. Manuscript items replaced (`manuscript/PENDING_R6.md`)

- **Item 16** ("Cells of the calibrated-price runs cut short by a machine sleep or by the time limit and reported
  with best-known repriced schedules or bound-based limits"). New statement, per cell:
  - usd4h x1.5 seeds 0, 5, 8: re-solved at 600 s; seed 5 optimal, seeds 0 and 8 time-limited with MIP gaps 0.87 and
    0.90 %. Gap 38.44 ± 3.07 % (upper limit 38.63); pooled usd4h 25.11 % [20.15, 30.07], 28 of 30 optimal. The
    footnotes "MIP gaps at most 1.07 %" become "at most 0.90 % at 600 s".
  - levers reference: re-solved at 1800 s; 1 of 5 optimal, MIP gaps 0.75-2.87 %; no incumbent is provably
    sub-optimal any more (no lock-out incumbent lies below its reference). Gap 47.59 % [42.16, 53.03], upper limit
    48.26 %; no on-site charging +262.96 USD [216.81, 309.11] (≥ 207.7 USD per seed by the bounds); lock-out of two
    spares +9.78 USD [−4.88, 24.43], non-negative on every seed, exactly +2.52 USD on seed 4.
  - fleet 10 bikes / 1 spare seed 2: re-solved, optimal (837.06 USD; the "991 s run used" note is void). fleet 10
    bikes / 2 spares seed 2: **not re-solved** (100.5 % MIP gap stands; still excluded by the nesting argument).
  - lateness sweep v 36 seeds 5 and 6: solved to optimality; the best-known schedules were the optima. The v 36 value
    31.65 ± 6.56 % is a solved value, not a lower bound; "two seeds use the best known schedule" is dropped.
  - penalty sweep usd4h P 80 seed 0: optimal (532.60 USD), gap 30.66 ± 6.73 % recorded. stress4h P 30 (one cell):
    seed 5 is still 0.12 USD above the repriced P 40 schedule (immaterial). P 40 seed 9: optimal. P 80 seeds 2, 3, 6,
    7: re-solved at 600 s (MIP gaps 1.66, 2.33, 3.38, 3.22 %); seeds 3, 6, 7 remain 9-16 USD above the repriced P 60
    schedule, so P 80 is still reported as recorded 44.50 ± 3.03 % and best-known 44.69 ± 3.15 % (upper limit 45.43).
  - stress4h six-bike cells: psweep P 60 now 5 of 10 optimal (was 4 of 10), MIP gaps ≤ 0.87 %; gap 39.73 ± 2.84 %.
    (The network-stage "2 of 5" cells were not part of the retry.)
- **Item 9**, the clause "the unresolved lock-out of two spares also needs a warm-started reference solve": done.
  The reference was warm-started from the lock-out incumbent with transfers stripped (`mip_start_variant`
  `ilp:lockout0.25|no_transfers`) at 1800 s; the result is the lock-out statement under item 16 above. The levers
  "chargers twice as fast", "second swap position" and "lock-out of one spare" belong to the levers_ext report,
  which already joins these retried reference rows.
- **Item 20** (calibrated-price values to re-derive before the final build), the headline-dependent entries,
  re-derived from the post-retry records: service share of the pooled saving 99.8 % (99.82); late orders per window
  usd4h pooled best rule → ILP 13.8 → **3.9** (was 4.1), nyc4h 14.9 → 4.4 (unchanged); paired served-share advantage
  +0.081 / +0.072 (unchanged); detours **0.38** / 0.40 km (was 0.36 / 0.40); end-adjustment differences 0.46 / 0.58
  USD (unchanged); saving shares usd4h lateness / response / unserved **19.1 / 16.8 / 63.9 %** (was 19.0 / 16.4 /
  64.4), nyc4h 17.5 / 18.4 / 63.8 (unchanged). The no-wait shares and the M4-minus-best-rule values were not
  recomputed here (the latter come from the rl records, which the retries do not touch).
- Digest section 7 rows that change: 1 (25.11 %, 28 OPT + 2 TL), 4 (38.44 %, ≤ 38.63), 9 (39.73 %, 5 OPT + 5 TL
  ≤ 0.87 %), 10 (47.59 % [42.16, 53.03], ≤ 48.26; 1 OPT + 4 TL at 1800 s), 19 (363.32 USD), 20 (19.1 / 16.8 / 63.9),
  25 (usd4h 13.8 → 3.9), 27 (0.38 / 0.40 km), 30 (48 / 50), 31 (largest excess against the bound: headline 0.19,
  psweep P 60 0.25 and P 80 0.93, levers 0.67 points), 60 (6 → 8 bikes: 40.1 → 47.6 %), 65 (K 8 served 0.925 vs
  0.653), 70 (214.1 / 89.4 / 17.1), 73 (+262.96 [216.81, 309.11], ≥ 207.7 per seed; reference 1/5 OPT), 74
  (≥ about 24,900), 75 (lock-out of 2 spares +9.78 [−4.88, 24.43], true value in [0, 17-41] per seed, 2.52 on
  seed 4). Rows 62, 63, 67-69, 71, 72 are unchanged. Items 5-8 and 10 of PENDING_R6.md are covered by the other fill
  stages, not by this report.

## Appendix A. The 55 re-solved rows

Improvement = previous total − new total (raw objective, USD). "kept" = `retry_worse`, previous row remains.

| stage | cell | seed | reason | before: status, MIP gap % | after: status, MIP gap %, runtime s | improvement | MIP start |
|---|---|---|---|---|---|---|---|
| headline | usd4h x1.5 | 0 | not optimal | TL 1.07 | TL 0.87, 600 | 2.71 | saved incumbent |
| headline | usd4h x1.5 | 5 | not optimal | TL 0.33 | OPT, 150 | 1.96 | saved incumbent |
| headline | usd4h x1.5 | 8 | not optimal | TL 0.91 | TL 0.90, 600 | 0.07 | saved incumbent |
| psweep | stress4h P 30 | 2 | not optimal | TL 0.58 | TL 0.58, 600 | 0.25 | saved incumbent |
| psweep | stress4h P 30 | 5 | not optimal | TL 0.28 | TL 0.25, 600 | 0 | saved incumbent |
| psweep | stress4h P 30 | 6 | not optimal | TL 0.33 | TL 0.18, 600 | 0.12 | saved incumbent |
| psweep | stress4h P 40 | 2 | not optimal | TL 0.70 | TL 0.38, 600 | 2.79 | saved incumbent |
| psweep | stress4h P 40 | 3 | not optimal | TL 0.57 | OPT, 297 | 1.40 | saved incumbent |
| psweep | stress4h P 40 | 6 | not optimal | TL 0.48 | TL 0.32, 600 | 1.21 | saved incumbent |
| psweep | stress4h P 40 | 7 | not optimal | TL 0.75 | TL 0.40, 600 | 3.09 | saved incumbent |
| psweep | stress4h P 40 | 9 | sleep-truncated (1093 s vs 167 s wall) | TL 0.27 | OPT, 155 | 1.47 | saved incumbent |
| psweep | stress4h P 60 | 1 | not optimal | TL 1.12 | TL 0.87, 600 | 2.57 | saved incumbent |
| psweep | stress4h P 60 | 2 | not optimal | TL 0.54 | TL 0.40, 600 | 0 | saved incumbent |
| psweep | stress4h P 60 | 3 | not optimal | TL 0.46 | TL 0.14, 600 | 0 | saved incumbent |
| psweep | stress4h P 60 | 5 | not optimal | TL 0.52 | TL 0.39, 600 | 0.51 | saved incumbent |
| psweep | stress4h P 60 | 6 | not optimal | TL 0.66 | TL 0.41, 600 | 0 | saved incumbent |
| psweep | stress4h P 60 | 9 | not optimal | TL 0.16 | OPT, 104 | 1.37 | saved incumbent |
| psweep | stress4h P 80 | 1 | not optimal | TL 0.78 | TL 0.67, 601 | 0 | saved incumbent |
| psweep | stress4h P 80 | 2 | not optimal | TL 4.71 | TL 1.66, 600 | 35.84 | saved incumbent |
| psweep | stress4h P 80 | 3 | not optimal | TL 11.63 | TL 2.33, 602 | 106.28 | saved incumbent |
| psweep | stress4h P 80 | 5 | not optimal | TL 2.99 | TL 2.90, 600 | 0 | saved incumbent |
| psweep | stress4h P 80 | 6 | not optimal | TL 3.76 | TL 3.38, 600 | 4.39 | saved incumbent |
| psweep | stress4h P 80 | 7 | not optimal | TL 3.79 | TL 3.22, 600 | 6.11 | saved incumbent |
| psweep | stress4h P 80 | 8 | not optimal | TL 0.83 | TL 0.51, 600 | 3.48 | saved incumbent |
| psweep | stress4h P 80 | 9 | not optimal | TL 0.84 | TL 0.58, 600 | 1.09 | saved incumbent |
| psweep | usd4h P 80 | 0 | sleep-truncated (459 s vs 44 s wall) | TL 94.28 | OPT, 33 | 66.54 | saved incumbent |
| vsweep | usd4h P 60 / v 36 | 5 | sleep-truncated (949 s vs 22 s wall) | TL 90.06 | OPT, 108 | 311.55 | saved incumbent |
| vsweep | usd4h P 60 / v 36 | 6 | sleep-truncated (460 s vs 44 s wall) | TL 90.95 | OPT, 176 | 466.97 | saved incumbent |
| fleet | K 4 / B 1 | 0 | not optimal | TL 0.88 | TL 1.04, 600 | 0 | rule M2 |
| fleet | K 4 / B 2 | 0 | not optimal | TL 0.81 | TL 0.86, 600 | 0 | K 4 / B 1 incumbent |
| fleet | K 4 / B 3 | 0 | not optimal | TL 0.72 | TL 0.76, 600 | 0 | K 4 / B 2 incumbent |
| fleet | K 4 / B 4 | 0 | not optimal | TL 0.79 | TL 0.62, 600 | 0 | K 4 / B 3 incumbent |
| fleet | K 6 / B 1 | 0 | not optimal | TL 1.30 | TL 0.87, 600 | 4.25 | rule M2 |
| fleet | K 4 / B 1 | 1 | not optimal | TL 1.56 | TL 1.53, 600, **kept** | −3.27 | rule r2 |
| fleet | K 4 / B 2 | 1 | not optimal | TL 1.21 | TL 0.90, 600 | 2.23 | K 4 / B 1 incumbent |
| fleet | K 4 / B 3 | 1 | not optimal | TL 1.00 | TL 0.50, 600 | 2.07 | K 4 / B 2 incumbent |
| fleet | K 4 / B 4 | 1 | not optimal | TL 0.97 | TL 0.33, 600 | 2.04 | K 4 / B 3 incumbent |
| fleet | K 6 / B 1 | 1 | not optimal | TL 1.54 | TL 2.40, 600, **kept** | −9.27 | rule M2 |
| fleet | K 6 / B 2 | 1 | not optimal | TL 0.94 | TL 0.81, 600 | 1.52 | K 6 / B 1 incumbent |
| fleet | K 6 / B 3 | 1 | not optimal | TL 0.63 | TL 0.74, 600, **kept** | −1.11 | K 6 / B 2 incumbent |
| fleet | K 10 / B 1 | 2 | sleep-truncated (991 s at a 600 s limit) | TL 2.31 | OPT, 565 | 10.84 | rule M2 |
| fleet | K 6 / B 1 | 2 | not optimal | TL 1.21 | TL 0.76, 600 | 1.03 | rule M2 |
| fleet | K 6 / B 2 | 2 | not optimal | TL 1.14 | TL 0.54, 600 | 5.07 | K 6 / B 1 incumbent |
| fleet | K 6 / B 3 | 2 | not optimal | TL 0.64 | TL 0.35, 600 | 0 | K 6 / B 2 incumbent |
| levers | lock-out of 2 spares | 0 | not optimal | TL 5.24 | TL 2.20, 1800 | 33.39 | rule M2 |
| levers | reference | 0 | not optimal | TL 6.87 | TL 1.50, 1800 | 58.96 | lock-out incumbent, transfers stripped |
| levers | lock-out of 2 spares | 1 | not optimal | TL 3.64 | TL 2.23, 1800 | 19.93 | rule r2 |
| levers | reference | 1 | not optimal | TL 0.83 | TL 0.75, 1800 | 0 | lock-out incumbent, transfers stripped |
| levers | lock-out of 2 spares | 2 | not optimal | TL 5.62 | TL 3.26, 1800 | 30.24 | rule r2 |
| levers | no on-site charging | 2 | not optimal | TL 0.72 | TL 0.32, 1811 | 2.07 | rule M2 |
| levers | reference | 2 | not optimal | TL 10.48 | TL 2.87, 1800 | 102.74 | lock-out incumbent, transfers stripped |
| levers | lock-out of 2 spares | 3 | not optimal | TL 1.23 | TL 1.05, 1800 | 2.68 | rule r2 |
| levers | reference | 3 | not optimal | TL 1.36 | TL 1.00, 1800 | 5.45 | lock-out incumbent, transfers stripped |
| levers | lock-out of 2 spares | 4 | not optimal | TL 0.39 | OPT, 1659 | 0 | rule r2 |
| levers | reference | 4 | not optimal | TL 0.85 | OPT, 1288 | 7.21 | lock-out incumbent, transfers stripped |

Reproduce: `python3 outputs/r6_fill/figs_retries/retries_analysis.py` (reads the records only; a few seconds).
