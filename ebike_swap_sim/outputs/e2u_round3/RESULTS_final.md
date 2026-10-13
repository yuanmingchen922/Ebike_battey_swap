# E2u final report -- coordination value under USD costs, 4 h window (round 3: seeds 0-9, service-share constraint (33))

Built from `outputs/e2u_round3/records.jsonl` (150 records, 150 unique (instance, method) keys, 0 duplicates; the LAST record per key is used) on 2026-10-13 after the run finished at 02:22 (263.2 min wall of a 300 min budget). No solver was run for this report: every number below is recomputed from the records with exact Student-t quantiles (the script's `improvement.csv` / `RESULTS.md` use 1.96 for n > 11, so their pooled half-widths are about 4 % narrower: +/- 5.38 instead of +/- 5.61 for the headline; means are identical). The four figures `gap_by_demand.png`, `zeta_premium.png`, `cost_components.png` and `drop_rates.png` were regenerated here with matplotlib (Agg). The script-written `RESULTS.md` is in English and was left as written.

## Summary

On the round-2 `usd4h` family (6 bikes, 4 h = 48 slots of 5 min, 3 co-located sites with B = 3 spares and C = 2 chargers each, `usd_sunk` prices) extended from 5 to 10 seeds, the E2 integer program is cheaper than the R2.3 rule baseline on all 30 instances and the headline gap ((baseline - ILP) / baseline) is **29.6 % +/- 5.6 (95 % t-CI, n = 30)**: 15.4 % +/- 7.3 at x0.75 (27 orders), 31.2 % +/- 9.1 at x1 (36 orders) and 42.1 % +/- 5.7 at x1.5 (54 orders), n = 10 each. The five new seeds alone give 37.2 % +/- 6.2, significantly above the round-2 value of 21.9 % +/- 8.1 (seeds 0-4, reproduced exactly from the reused rows; Welch p = 0.004), because their baseline runs are 28 % more expensive (1311 vs 1022 USD) while the ILP optimum moves by 5 % (765 vs 727 USD): the value of coordination is the lateness and response cost the myopic policy incurs on bad demand draws (gap vs baseline lateness cost r = 0.91 over 30 instances), and the composition is unchanged (lateness 59 %, response 32 %, unserved orders 8 %, travel plus electricity under 1 %).

The round-3 decision R3.1 replaces the uncertifiable lexicographic variant of round 2 by the hard service-share constraint (33) `sum_i (1 - u_i) >= zeta |I|`. At the main setting zeta = 0.90 the constraint is feasible on all 20 instances with 27 or 36 orders and costs **0.9 USD +/- 1.4 (0.2 %) per instance at x0.75** (binding on 3 of 10 seeds, where it converts one 30 USD drop into a served order for 0.5-5.3 USD) and **37.4 USD +/- 38.2 (5.5 %) at x1** (binding on 8 of 10 seeds, range 1.4-175.9 USD; the served share rises from 0.875 to 0.922, i.e. 1.7 more orders per instance, at a net 22 USD per rescued order on top of the 30 USD penalty avoided). Against the baseline the zeta-0.90 ILP still saves 15.2 % +/- 7.3 (x0.75), 27.8 % +/- 8.7 (x1) and 21.5 % +/- 5.9 pooled over the 20 feasible instances (the unconstrained ILP saves 23.3 % +/- 6.5 on the same 20), while serving more orders than the baseline at x1 (0.922 vs 0.872) and about as many at x0.75 (0.956 vs 0.967). The sensitivity setting zeta = 0.85 never binds at x0.75 (10/10 cells implied by the written optimum, premium 0) and binds on 2 of 10 seeds at x1 (premium 8.0 USD +/- 17.3, 1.1 %; 40 USD on the two binding seeds), giving 23.0 % +/- 6.3 against the baseline on the same 20 instances.

At x1.5 (54 orders) both zeta levels are **infeasible on all 10 seeds**: the maximum served share any schedule can reach under the E2 constraints is 0.74-0.80 where certified (6 seeds, `min sum u` solved to optimality) and at most 0.76-0.83 by the Gurobi bound on the four seeds where the max-service solve timed out, in every case below the 46 of 54 orders (0.85) that the weaker constraint requires. The script marks 6 of these cells per zeta as proven infeasible (2 by Gurobi's INFEASIBLE status, 4 by the certified maximum share) and 4 as undecided (TIME_LIMIT without an incumbent), but the recorded dual bounds (at least 9, 13, 11 and 12 unserved orders for seeds 0, 1, 5, 6 vs the 8 allowed) prove infeasibility there too. With 6 bikes in 4 h, 54 orders exceed the fleet's capacity: the cost-optimal ILP drops 16.3 (30 %) and the baseline 20.2 (37 %); a 90 % service guarantee at this demand would need more bikes, not a different schedule.

The relaxed-target control (rho 0, R_end 0) is now solved to optimality on all 30 instances and reproduces the written result to 0.03 points (29.6 % +/- 5.6): the end targets (17)-(18) cost 0.34 USD per instance on average (at most 0.86 USD), so none of the coordination value comes from end-of-window stock. Solver: 91 ILP work items plus 44 reused round-2 rows; written ILP 28/30 OPTIMAL (2 TIME_LIMIT with MIP gap 0.04 % and 0.11 %), relaxed 30/30 OPTIMAL, zeta-0.90 19 OPTIMAL / 9 TIME_LIMIT / 2 INFEASIBLE, zeta-0.85 20 OPTIMAL / 6 TIME_LIMIT / 4 INFEASIBLE, 0 SKIPPED_BUDGET; 25 of the 60 zeta cells were settled without a solve (`implied_by_written` 8 + 17; `implied_by_max_service` 2). Every solved schedule passes the independent checker and identity (24).

## Setup and provenance

- Script `experiments/e2u_round3.py` (design, instance builder and record layout from round 2), run 2026-10-12 21:59 to 2026-10-13 02:22 in one process, Gurobi OutputFlag 0, Threads 3, Seed 0, TimeLimit 300 s per solve (also for the `min sum u` max-service solve), wall budget 300 min (263.2 min used, nothing skipped). The E3u / E4u / E8 round-3 scripts ran concurrently on the same machine for part of the window, so solve times are not a clean benchmark.
- Inputs of this report: `records.jsonl` (150 records), `results.csv`, `run_stdout.log`, `wall_time.json`, `zeta_feasibility.csv`, `improvement.csv`, 30 saved instances `instances/usd4h-K6-I{27,36,54}-seed{0..9}-x{0.75,1,1.5}.json`; the round-2 report `outputs/e2u_coord_usd/RESULTS_final.md` for the comparison.
- Family `usd4h` (R2.2): 6 bikes, H = 48 (Delta 5 min, 17:00-21:00), L = 12, 3 co-located sites (B = 3, C = 2, K = 8, M = 1, sigma = 1, P_j = 4 kW), no transfer services, q0 ~ U{4..7}, Kaggle prep / promise attributes; demand x0.75 / x1 / x1.5 = 27 / 36 / 54 orders; seeds 0-9, byte-identical instances per (seed, demand) across methods. Costs `usd_sunk` (R2.1): kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03, bB 0.332, bC 0.082 $ per site per 4 h. Arc library: plan pruning + lossless reachable pruning, 0.89-1.58 M binaries, 57-69 k rows.
- Methods: `baseline` = R2.3 rules (stock-aware nearest-feasible dispatch, DEMAND_AWARE charging, JIT dispatch, dead-zone rule; 4 ms per instance); `ilp` = written model (rho 0.5, R_end_j 1); `ilp_zeta90` / `ilp_zeta85` = written model plus (33) at zeta 0.90 / 0.85 (`ilp.build_model(zeta=...)` via `experiments.common.run_zeta_case`); `ilp_relaxed` = `relax_end_targets` copy (rho 0, R_end 0). MIP start = first clean policy schedule (`feasible_mip_start`); for the zeta models the written schedule when it satisfies (33), else the policy schedule when it does, else none (`none(start violates zeta)` on 29 cells).
- Reuse: the LAST round-2 record per key was copied (`source = round2`, `solve_mode = reused`) for all 15 round-2 baseline rows and for round-2 ILP rows that were OPTIMAL or had MIP gap <= 1 % (14 written + 1 TIME_LIMIT at 0.04 % + 14 relaxed = 29 rows); the round-2 relaxed cell seed 1 x1.5 (TIME_LIMIT 43.8 %, stuck at the MIP start) was re-solved (now OPTIMAL 1123.9). Seeds 5-9 and all zeta cells are round-3 solves. Reused rows carry no `n_vars` / `threads` columns.
- `solve_mode` values: `solved` (Gurobi run in round 3), `reused` (round-2 row), `implied_by_written` (certified written optimum already serves >= zeta |I| orders, so the zeta-constrained optimum equals it; 0 s), `implied_by_max_service` (certified maximum share from the zeta-0.90 run of the same instance lies below zeta, so the cell is INFEASIBLE without a solve; 0 s).
- Gap definition: 100 (baseline - ILP) / baseline on the same instance; ILP totals at TIME_LIMIT are incumbents (upper bounds), so those gaps are lower bounds. 95 % t-CI = t_{0.975, n-1} s / sqrt(n) over seeds; shown as mean +/- half-width.
- Baseline rows report (17) violated on 5 and (18) on 6 of the 30 runs (report-only, not priced; `ok_modulo_report_only` True on all 30), so the written-ILP gap is conservative on those instances; the relaxed control moves it by <= 0.1 points.

## Headline gap per comparison and demand level (mean over seeds, 95 % t-CI)

| comparison | demand | n | gap mean % | CI95 +/- | lo | hi | abs gain USD | CI95 | baseline mean USD | ILP mean USD | per-seed gaps % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP written (rho 0.5, R_end 1) vs baseline R2.3 [headline] | x0.75 | 10 | 15.36 | 7.28 | 8.1 | 22.6 | 97.3 | 54.5 | 577.4 | 480.1 | 3.7; 12.2; 3.8; 10.0; 5.0; 28.9; 27.5; 17.1; 28.6; 16.9 |
| ILP written (rho 0.5, R_end 1) vs baseline R2.3 [headline] | x1 | 10 | 31.18 | 9.05 | 22.1 | 40.2 | 333.9 | 136.7 | 992.5 | 658.6 | 16.1; 32.2; 19.1; 29.0; 10.3; 41.1; 48.3; 35.8; 45.2; 34.8 |
| ILP written (rho 0.5, R_end 1) vs baseline R2.3 [headline] | x1.5 | 10 | 42.11 | 5.66 | 36.5 | 47.8 | 831.8 | 176.4 | 1930.3 | 1098.4 | 38.6; 43.7; 22.4; 43.1; 38.9; 45.7; 51.8; 46.1; 46.6; 44.1 |
| ILP written (rho 0.5, R_end 1) vs baseline R2.3 [headline] | all | 30 | 29.55 | 5.61 | 23.9 | 35.2 | 421.0 | 134.1 | 1166.7 | 745.7 | 3.7; 12.2; 3.8; 10.0; 5.0; 28.9; 27.5; 17.1; 28.6; 16.9; 16.1; 32.2; 19.1; 29.0; 10.3; 41.1; 48.3; 35.8; 45.2; 34.8; 38.6; 43.7; 22.4; 43.1; 38.9; 45.7; 51.8; 46.1; 46.6; 44.1 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | x0.75 | 10 | 15.20 | 7.26 | 7.9 | 22.5 | 96.4 | 54.4 | 577.4 | 481.0 | 3.7; 12.2; 3.8; 9.0; 5.0; 28.9; 27.4; 17.1; 28.1; 16.9 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | x1 | 10 | 27.76 | 8.66 | 19.1 | 36.4 | 296.6 | 123.3 | 992.5 | 696.0 | 16.1; 29.3; 10.9; 24.0; 10.3; 39.7; 45.5; 35.3; 31.8; 34.7 |
| ILP + (33) zeta 0.90 vs baseline R2.3 | x1.5 | 0 | - | - | - | - | - | - | - | - | infeasible on all 10 seeds |
| ILP + (33) zeta 0.90 vs baseline R2.3 | all | 20 | 21.48 | 5.91 | 15.6 | 27.4 | 196.5 | 77.4 | 785.0 | 588.5 | 3.7; 12.2; 3.8; 9.0; 5.0; 28.9; 27.4; 17.1; 28.1; 16.9; 16.1; 29.3; 10.9; 24.0; 10.3; 39.7; 45.5; 35.3; 31.8; 34.7 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | x0.75 | 10 | 15.36 | 7.28 | 8.1 | 22.6 | 97.3 | 54.5 | 577.4 | 480.1 | 3.7; 12.2; 3.8; 10.0; 5.0; 28.9; 27.5; 17.1; 28.6; 16.9 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | x1 | 10 | 30.58 | 8.59 | 22.0 | 39.2 | 326.0 | 128.8 | 992.5 | 666.6 | 16.1; 32.2; 19.1; 29.0; 10.3; 41.1; 48.0; 35.8; 39.3; 34.8 |
| ILP + (33) zeta 0.85 vs baseline R2.3 | x1.5 | 0 | - | - | - | - | - | - | - | - | infeasible on all 10 seeds |
| ILP + (33) zeta 0.85 vs baseline R2.3 | all | 20 | 22.97 | 6.25 | 16.7 | 29.2 | 211.6 | 83.6 | 785.0 | 573.3 | 3.7; 12.2; 3.8; 10.0; 5.0; 28.9; 27.5; 17.1; 28.6; 16.9; 16.1; 32.2; 19.1; 29.0; 10.3; 41.1; 48.0; 35.8; 39.3; 34.8 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x0.75 | 10 | 15.39 | 7.28 | 8.1 | 22.7 | 97.5 | 54.6 | 577.4 | 479.9 | 3.6; 12.2; 3.8; 10.1; 5.0; 28.9; 27.5; 17.2; 28.7; 16.9 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x1 | 10 | 31.22 | 9.03 | 22.2 | 40.3 | 334.3 | 136.6 | 992.5 | 658.2 | 16.2; 32.3; 19.2; 29.0; 10.3; 41.2; 48.3; 35.8; 45.2; 34.8 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x1.5 | 10 | 42.14 | 5.66 | 36.5 | 47.8 | 832.3 | 176.4 | 1930.3 | 1098.0 | 38.6; 43.8; 22.4; 43.1; 38.9; 45.8; 51.8; 46.1; 46.6; 44.1 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | all | 30 | 29.58 | 5.61 | 24.0 | 35.2 | 421.4 | 134.1 | 1166.7 | 745.4 | 3.6; 12.2; 3.8; 10.1; 5.0; 28.9; 27.5; 17.2; 28.7; 16.9; 16.2; 32.3; 19.2; 29.0; 10.3; 41.2; 48.3; 35.8; 45.2; 34.8; 38.6; 43.8; 22.4; 43.1; 38.9; 45.8; 51.8; 46.1; 46.6; 44.1 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x0.75 | 10 | 15.39 | 7.28 | 8.1 | 22.7 | 97.5 | 54.6 | 577.4 | 479.9 | 3.7; 12.2; 3.8; 10.1; 5.0; 28.9; 27.5; 17.2; 28.7; 16.9 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x1 | 10 | 31.22 | 9.03 | 22.2 | 40.3 | 334.3 | 136.6 | 992.5 | 658.2 | 16.2; 32.3; 19.2; 29.0; 10.3; 41.2; 48.3; 35.8; 45.2; 34.8 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x1.5 | 10 | 42.14 | 5.66 | 36.5 | 47.8 | 832.3 | 176.4 | 1930.3 | 1098.0 | 38.6; 43.8; 22.4; 43.1; 38.9; 45.8; 51.8; 46.1; 46.6; 44.1 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | all | 30 | 29.58 | 5.61 | 24.0 | 35.2 | 421.4 | 134.1 | 1166.7 | 745.4 | 3.7; 12.2; 3.8; 10.1; 5.0; 28.9; 27.5; 17.2; 28.7; 16.9; 16.2; 32.3; 19.2; 29.0; 10.3; 41.2; 48.3; 35.8; 45.2; 34.8; 38.6; 43.8; 22.4; 43.1; 38.9; 45.8; 51.8; 46.1; 46.6; 44.1 |

Seed subsets of the headline comparison (written ILP vs baseline R2.3):

| seeds | demand | n | gap mean % | CI95 +/- | baseline mean USD | ILP mean USD |
|---|---|---|---|---|---|---|
| seeds0-4 | x0.75 | 5 | 6.91 | 4.87 | 502.7 | 466.9 |
| seeds0-4 | x1 | 5 | 21.33 | 11.31 | 822.9 | 638.3 |
| seeds0-4 | x1.5 | 5 | 37.35 | 10.80 | 1741.3 | 1074.3 |
| seeds0-4 | all | 15 | 21.86 | 8.13 | 1022.3 | 726.5 |
| seeds5-9 | x0.75 | 5 | 23.81 | 7.75 | 652.1 | 493.3 |
| seeds5-9 | x1 | 5 | 41.04 | 7.25 | 1162.2 | 678.9 |
| seeds5-9 | x1.5 | 5 | 46.88 | 3.62 | 2119.3 | 1122.6 |
| seeds5-9 | all | 15 | 37.24 | 6.22 | 1311.2 | 765.0 |

Round 2 (seeds 0-4, n = 15) reported 21.86 % +/- 8.13 with x0.75 6.9 / x1 21.3 / x1.5 37.3; the same rows give the same numbers here. The ten new instances of seeds 5-9 have gaps of 16.9-51.8 % (mean 37.2 % +/- 6.2); a Welch test against seeds 0-4 gives p = 0.004, the difference being driven by the baseline (seeds 5-9: 652 / 1162 / 2119 USD vs 503 / 823 / 1741 USD on seeds 0-4) rather than by the ILP (493 / 679 / 1123 vs 467 / 638 / 1074). Across the 30 instances the gap tracks the baseline's lateness cost (r = 0.91) and the baseline total (r = 0.86), and the absolute saving tracks the baseline's lateness cost at r = 0.99; the ILP total has a coefficient of variation of 4-5 % per demand level (444-511 / 615-719 / 1009-1160 USD) against 15-22 % for the baseline (461-719 / 685-1311 / 1368-2325 USD).

## Service-share constraint (33): feasibility, premium and served shares

Premium = total(zeta run) - total(written ILP) on the same instance (a certified premium of exactly 0 where the cell is `implied_by_written`); "binding" = premium > 0. Required served = ceil(zeta |I|).

| zeta | demand | instances | feasible | infeasible (proven) | undecided by the script | implied by the written optimum | binding (premium > 0) | premium vs written USD | premium % | premium on binding instances USD | gap vs baseline % | written gap on the same instances % | served share zeta / written / baseline | unserved zeta / written / baseline | required served |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.90 | x0.75 | 10 | 10 | 0 | 0 | 7 | 3 | 0.94 +/- 1.36 | 0.19 +/- 0.27 | 3.12 +/- 6.07 (n = 3) | 15.20 +/- 7.26 | 15.36 +/- 7.28 | 0.956 / 0.944 / 0.967 | 1.20 / 1.50 / 0.90 | [25] |
| 0.90 | x1 | 10 | 10 | 0 | 0 | 1 | 8 | 37.38 +/- 38.23 | 5.46 +/- 5.36 | 46.76 +/- 47.07 (n = 8) | 27.76 +/- 8.66 | 31.18 +/- 9.05 | 0.922 / 0.875 / 0.872 | 2.80 / 4.50 / 4.60 | [33] |
| 0.90 | x1.5 | 10 | 0 | 6 | 4 | 0 | - | - | - | - | - | - | - | - | [49] |
| 0.90 | all | 30 | 20 | 6 | 4 | 8 | 11 | 19.16 +/- 19.32 | 2.82 +/- 2.73 | 34.86 +/- 34.49 (n = 11) | 21.48 +/- 5.91 | 23.27 +/- 6.46 | 0.939 / 0.910 / 0.919 | 2.00 / 3.00 / 2.75 | [25, 33, 49] |
| 0.85 | x0.75 | 10 | 10 | 0 | 0 | 10 | 0 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | - (n = 0) | 15.36 +/- 7.28 | 15.36 +/- 7.28 | 0.944 / 0.944 / 0.967 | 1.50 / 1.50 / 0.90 | [23] |
| 0.85 | x1 | 10 | 10 | 0 | 0 | 7 | 2 | 7.99 +/- 17.34 | 1.11 +/- 2.41 | 40.08 (n = 2) | 30.58 +/- 8.59 | 31.18 +/- 9.05 | 0.886 / 0.875 / 0.872 | 4.10 / 4.50 / 4.60 | [31] |
| 0.85 | x1.5 | 10 | 0 | 6 | 4 | 0 | - | - | - | - | - | - | - | - | [46] |
| 0.85 | all | 30 | 20 | 6 | 4 | 17 | 2 | 4.00 +/- 8.04 | 0.56 +/- 1.12 | 40.08 (n = 2) | 22.97 +/- 6.25 | 23.27 +/- 6.46 | 0.915 / 0.910 / 0.919 | 2.80 / 3.00 / 2.75 | [23, 31, 46] |

Reading: at x0.75 the written optimum already serves >= 25 of 27 orders on 7 seeds; on seeds 3, 6 and 8 it drops 3 orders and zeta 0.90 forces a third order back in for 5.3, 0.5 and 3.5 USD. At x1 the written optimum serves 33 of 36 on only 2 seeds (0 and 4); on the other 8 the constraint lifts the served count from 31-28 to 33 for 1.4-175.9 USD (median 32.7 USD), with the two worst seeds (2: 64.7 USD; 8: 175.9 USD) being the instances where the written optimum drops 4 and 8 orders. zeta 0.85 (31 of 36) binds only on seeds 6 and 8 (3.2 and 76.9 USD). Seed 0 x1 shows a premium of -0.2 USD on both zeta rows: the reused round-2 written row is a TIME_LIMIT incumbent (615.36, gap 0.04 %) while the zeta solves, which are restrictions of the same model, closed at 615.15; the written optimum is therefore at most 615.15 and the true premium is 0.

The zeta-constrained schedules buy service with waiting, not with distance or energy: at x1 the zeta-0.90 ILP keeps 5.7 late deliveries per instance against 1.2 for the written ILP (lateness 37.8 vs 3.9 USD) and 16.5 for the baseline, rides 103 vs 94 km and swaps 7.9 vs 7.0 times; electricity stays under 0.6 USD.

### x1.5 (54 orders): why both zeta levels are infeasible on every seed

| seed | unservable orders | zeta 0.90 status / solve_mode / zeta_feasible / s | zeta 0.85 status / solve_mode / zeta_feasible / s | max-service solve status / s | min unserved incumbent / Gurobi bound | max share reached | upper bound on max share | certified | ILP written served [unserved] | baseline served [unserved] |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / 300 | 17 / 9 | 0.685 | 0.833 | no | 0.796 [11] | 0.685 [17] |
| 1 | 1 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / 300 | 14 / 13 | 0.741 | 0.759 | no | 0.685 [17] | 0.611 [21] |
| 2 | 2 | INFEASIBLE / solved / infeasible / 214 | INFEASIBLE / solved / infeasible / 248 | TIME_LIMIT / 300 | 20 / 13 | 0.630 | 0.759 | no | 0.722 [15] | 0.667 [18] |
| 3 | 1 | TIME_LIMIT / solved / infeasible / 300 | INFEASIBLE / implied_by_max_service / infeasible / 0 | OPTIMAL / 189 | 14 / 14 | 0.741 | 0.741 | yes | 0.685 [17] | 0.630 [20] |
| 4 | 2 | TIME_LIMIT / solved / infeasible / 300 | INFEASIBLE / implied_by_max_service / infeasible / 0 | OPTIMAL / 141 | 12 / 12 | 0.778 | 0.778 | yes | 0.722 [15] | 0.630 [20] |
| 5 | 1 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / 300 | 16 / 11 | 0.704 | 0.796 | no | 0.704 [16] | 0.630 [20] |
| 6 | 1 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / solved / undecided / 300 | TIME_LIMIT / 300 | 17 / 12 | 0.685 | 0.778 | no | 0.685 [17] | 0.611 [21] |
| 7 | 3 | TIME_LIMIT / solved / infeasible / 300 | TIME_LIMIT / solved / infeasible / 300 | OPTIMAL / 144 | 14 / 14 | 0.741 | 0.741 | yes | 0.648 [19] | 0.574 [23] |
| 8 | 3 | INFEASIBLE / solved / infeasible / 175 | INFEASIBLE / solved / infeasible / 209 | OPTIMAL / 185 | 11 / 11 | 0.796 | 0.796 | yes | 0.630 [20] | 0.611 [21] |
| 9 | 0 | TIME_LIMIT / solved / infeasible / 300 | TIME_LIMIT / solved / infeasible / 300 | OPTIMAL / 129 | 13 / 13 | 0.759 | 0.759 | yes | 0.704 [16] | 0.611 [21] |

`max share reached` is the share of the best `min sum u` incumbent (a lower bound on the maximum feasible share), `upper bound` = 1 - ceil(Gurobi bound) / 54 (a valid upper bound on it); the two coincide when the max-service solve closed (certified). zeta 0.90 requires 49 served (at most 5 unserved) and zeta 0.85 requires 46 (at most 8 unserved); every upper bound is at most 0.833 (at least 9 unserved), so no seed can satisfy either constraint. The script's own `zeta_feasible` flag is False only where Gurobi returned INFEASIBLE (seeds 2 and 8) or the maximum share is certified (seeds 3, 4, 7, 9) and None (undecided) on seeds 0, 1, 5, 6; the dual bounds recorded for those four cells settle them as infeasible as well. `unservable orders` = orders with no delivery arc (release + prep + ride > H), 15 of 540 at this level, which both methods pay P for. The max-service model keeps the written end targets (17)-(18), so the bound is for the written constraint set; on this family the targets cost under 1 USD in the cost optimum and are unlikely to cap service, but this was not re-solved with rho = R_end = 0.

## Gap decomposition (mean baseline - ILP per component, USD per instance, share of the total gap)

| comparison | demand | n | total gap USD | unserved (30) | response (31) | lateness (31) | travel (27) | electricity (28) | setup (29) | transfers (32) |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline R2.3 - ILP written | x0.75 | 10 | 97.3 | -18.0 (-18 %) | 51.5 (53 %) | 61.2 (63 %) | 2.1 (2 %) | 0.6 (1 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP written | x1 | 10 | 333.9 | 3.0 (1 %) | 125.0 (37 %) | 203.1 (61 %) | 2.4 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP written | x1.5 | 10 | 831.8 | 117.0 (14 %) | 229.9 (28 %) | 482.4 (58 %) | 2.2 (0 %) | 0.3 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP written | all | 30 | 421.0 | 34.0 (8 %) | 135.4 (32 %) | 248.9 (59 %) | 2.2 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.90 | x0.75 | 10 | 96.4 | -9.0 (-9 %) | 44.1 (46 %) | 58.8 (61 %) | 1.9 (2 %) | 0.6 (1 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.90 | x1 | 10 | 296.6 | 54.0 (18 %) | 71.7 (24 %) | 169.2 (57 %) | 1.3 (0 %) | 0.4 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.90 | all | 20 | 196.5 | 22.5 (11 %) | 57.9 (29 %) | 114.0 (58 %) | 1.6 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.85 | x0.75 | 10 | 97.3 | -18.0 (-18 %) | 51.5 (53 %) | 61.2 (63 %) | 2.1 (2 %) | 0.6 (1 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.85 | x1 | 10 | 326.0 | 15.0 (5 %) | 113.2 (35 %) | 195.0 (60 %) | 2.2 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP + (33) zeta 0.85 | all | 20 | 211.6 | -1.5 (-1 %) | 82.3 (39 %) | 128.1 (61 %) | 2.2 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP relaxed targets | x0.75 | 10 | 97.5 | -18.0 (-18 %) | 51.5 (53 %) | 61.2 (63 %) | 2.1 (2 %) | 0.8 (1 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP relaxed targets | x1 | 10 | 334.3 | 3.0 (1 %) | 125.0 (37 %) | 203.1 (61 %) | 2.4 (1 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP relaxed targets | x1.5 | 10 | 832.3 | 117.0 (14 %) | 229.9 (28 %) | 482.4 (58 %) | 2.2 (0 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| baseline R2.3 - ILP relaxed targets | all | 30 | 421.4 | 34.0 (8 %) | 135.4 (32 %) | 248.9 (59 %) | 2.2 (1 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |

The negative unserved term at x0.75 means the ILP drops more orders than the baseline (1.5 vs 0.9 per instance: with P = 30 USD a drop is cheaper than a late delivery) and more than pays for it with response and lateness; the ILP drops more orders than the baseline on 8 of 30 instances, fewer on 16, the same on 6. Lateness and response time make up 91 % of the pooled gap (round 2: 79 %), travel and electricity under 1 %, setup and transfers are identical by construction.

## Service, drop rates, response, lateness, distance, energy by method and demand (mean over seeds)

| demand | method | n | total USD (95 % t-CI) | served share | unserved per instance | drop % (unserved / orders) | mean response min | mean lateness min | late deliveries | bike km | swaps | kWh bought | end full (of 9) | stock-out slots |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | baseline (R2.3 rules) | 10 | 577.4 +/- 68.4 | 0.967 +/- 0.020 | 0.90 | 3.3 (9/270) | 55.2 | 4.18 | 7.7 | 96.8 | 6.6 | 2.41 | 5.9 | 5.1 |
| x0.75 | ILP written | 10 | 480.1 +/- 15.8 | 0.944 +/- 0.031 | 1.50 | 5.6 (15/270) | 49.8 | 0.31 | 1.4 | 79.7 | 5.3 | 0.53 | 5.0 | 7.9 |
| x0.75 | ILP + (33) zeta 0.90 | 10 | 481.0 +/- 16.5 | 0.956 +/- 0.021 | 1.20 | 4.4 (12/270) | 50.2 | 0.47 | 2.2 | 81.2 | 5.3 | 0.52 | 5.0 | 10.2 |
| x0.75 | ILP + (33) zeta 0.85 | 10 | 480.1 +/- 15.8 | 0.944 +/- 0.031 | 1.50 | 5.6 (15/270) | 49.8 | 0.31 | 1.4 | 79.7 | 5.3 | 0.53 | 5.0 | 7.9 |
| x0.75 | ILP relaxed targets | 10 | 479.9 +/- 15.8 | 0.944 +/- 0.031 | 1.50 | 5.6 (15/270) | 49.8 | 0.31 | 1.4 | 79.6 | 6.6 | 0.01 | 2.4 | 19.3 |
| x1 | baseline (R2.3 rules) | 10 | 992.5 +/- 156.4 | 0.872 +/- 0.046 | 4.60 | 12.8 (46/360) | 63.0 | 10.99 | 16.5 | 114.2 | 7.6 | 2.68 | 5.2 | 5.8 |
| x1 | ILP written | 10 | 658.6 +/- 22.4 | 0.875 +/- 0.037 | 4.50 | 12.5 (45/360) | 49.6 | 0.20 | 1.2 | 94.1 | 7.0 | 1.17 | 5.0 | 20.7 |
| x1 | ILP + (33) zeta 0.90 | 10 | 696.0 +/- 56.0 | 0.922 +/- 0.013 | 2.80 | 7.8 (28/360) | 52.4 | 1.91 | 5.7 | 103.3 | 7.9 | 1.58 | 5.0 | 19.9 |
| x1 | ILP + (33) zeta 0.85 | 10 | 666.6 +/- 36.6 | 0.886 +/- 0.026 | 4.10 | 11.4 (41/360) | 50.2 | 0.64 | 2.1 | 95.5 | 7.2 | 1.24 | 5.0 | 20.9 |
| x1 | ILP relaxed targets | 10 | 658.2 +/- 22.5 | 0.875 +/- 0.037 | 4.50 | 12.5 (45/360) | 49.6 | 0.20 | 1.2 | 93.9 | 7.4 | 0.12 | 1.9 | 35.4 |
| x1.5 | baseline (R2.3 rules) | 10 | 1930.3 +/- 200.9 | 0.626 +/- 0.022 | 20.20 | 37.4 (202/540) | 77.7 | 24.21 | 24.4 | 125.7 | 8.4 | 2.91 | 4.6 | 9.4 |
| x1.5 | ILP written | 10 | 1098.4 +/- 33.1 | 0.698 +/- 0.032 | 16.30 | 30.2 (163/540) | 49.0 | 0.10 | 0.7 | 107.0 | 8.4 | 2.09 | 5.0 | 22.7 |
| x1.5 | ILP + (33) zeta 0.90 | 0 | infeasible on all 10 seeds | - | - | - | - | - | - | - | - | - | - | - |
| x1.5 | ILP + (33) zeta 0.85 | 0 | infeasible on all 10 seeds | - | - | - | - | - | - | - | - | - | - | - |
| x1.5 | ILP relaxed targets | 10 | 1098.0 +/- 33.1 | 0.698 +/- 0.032 | 16.30 | 30.2 (163/540) | 49.0 | 0.10 | 0.7 | 107.5 | 8.8 | 0.39 | 1.3 | 22.6 |
| all | baseline (R2.3 rules) | 30 | 1166.7 +/- 228.2 | 0.822 +/- 0.057 | 8.57 | 22.0 (257/1170) | 65.3 | 13.13 | 16.2 | 112.2 | 7.5 | 2.67 | 5.2 | 6.8 |
| all | ILP written | 30 | 745.7 +/- 99.5 | 0.839 +/- 0.043 | 7.43 | 19.1 (223/1170) | 49.5 | 0.20 | 1.1 | 93.6 | 6.9 | 1.26 | 5.0 | 17.1 |
| all | ILP + (33) zeta 0.90 | 20 | 588.5 +/- 57.9 | 0.939 +/- 0.014 | 2.00 | 6.3 (40/630) | 51.3 | 1.19 | 4.0 | 92.3 | 6.6 | 1.05 | 5.0 | 15.1 |
| all | ILP + (33) zeta 0.85 | 20 | 573.3 +/- 48.2 | 0.915 +/- 0.023 | 2.80 | 8.9 (56/630) | 50.0 | 0.47 | 1.8 | 87.6 | 6.2 | 0.89 | 5.0 | 14.4 |
| all | ILP relaxed targets | 30 | 745.4 +/- 99.4 | 0.839 +/- 0.043 | 7.43 | 19.1 (223/1170) | 49.5 | 0.20 | 1.1 | 93.7 | 7.6 | 0.17 | 1.9 | 25.8 |

Drop rate = unserved / orders summed over the seeds of the level. Structurally unservable orders (no delivery arc) are known for seeds 0-4 from the round-2 report (x0.75: 1, 0, 0, 2, 1; x1: 1, 1, 0, 1, 1) and for all x1.5 seeds from the max-service solves (1, 1, 2, 1, 2, 1, 1, 3, 3, 0); they are counted as unserved for every method. `end full` = full batteries in stock at H ((18) needs >= 5 of 9); the relaxed ILP leaves 1.3-2.4 and buys 0.01-0.39 kWh, the written ILP exactly 5.0 and 0.5-2.1 kWh.

## Relaxed-target control

The relaxed ILP (rho 0, R_end 0) is OPTIMAL on all 30 instances (round 2: 14/15, the seed-1 x1.5 cell having stopped at its MIP start). Its gap is 29.58 % +/- 5.61 vs 29.55 % +/- 5.61 for the written model; the written-minus-relaxed difference is 0.34 USD per instance on average (mean 0.17 / 0.36 / 0.48 USD at x0.75 / x1 / x1.5, maximum 0.86; one instance, seed 0 x0.75, reads -0.02 USD, inside the MIP tolerance of the two OPTIMAL rows), i.e. the price of the end targets (17)-(18) is the 0.5-2.1 kWh of charging needed to end with 5 full batteries. The "best known" row (min(written, relaxed), a valid upper bound because the written solution is feasible for the relaxed model) equals the relaxed row everywhere.

## Solver statistics

| method | demand | cells | OPTIMAL | TIME_LIMIT | INFEASIBLE | SKIPPED_BUDGET | solve_mode (solved / reused / implied_by_written / implied_by_max_service) | source round2 / round3 | max MIP gap % | mean s (solved cells) | max s | binaries (M) | MIP start |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ilp | x0.75 | 10 | 10 | 0 | 0 | 0 | 5 / 5 / 0 / 0 | 5 / 5 | 0.006 | 107 | 199 | 0.89-1.05 | default|True 10 |
| ilp | x1 | 10 | 9 | 1 | 0 | 0 | 5 / 5 / 0 / 0 | 5 / 5 | 0.036 | 108 | 183 | 1.03-1.28 | default|True 7; baseline_round1|True 3 |
| ilp | x1.5 | 10 | 9 | 1 | 0 | 0 | 5 / 5 / 0 / 0 | 5 / 5 | 0.114 | 212 | 300 | 1.35-1.58 | baseline_round1|True 4; default|True 4; default|False 1; baseline_reserve|True 1 |
| ilp | all | 30 | 28 | 2 | 0 | 0 | 15 / 15 / 0 / 0 | 15 / 15 | 0.114 | 143 | 300 | 0.89-1.58 | default|True 21; baseline_round1|True 7; default|False 1; baseline_reserve|True 1 |
| ilp_zeta90 | x0.75 | 10 | 10 | 0 | 0 | 0 | 3 / 0 / 7 / 0 | 0 / 10 | 0.004 | 78 | 95 | 0.89-1.05 | written_optimum|- 7; default|True 1; none(start violates zeta)|- 2 |
| ilp_zeta90 | x1 | 10 | 9 | 1 | 0 | 0 | 9 / 0 / 1 / 0 | 0 / 10 | 0.015 | 128 | 300 | 1.03-1.28 | default|True 1; none(start violates zeta)|- 8; written_optimum|- 1 |
| ilp_zeta90 | x1.5 | 10 | 0 | 8 | 2 | 0 | 10 / 0 / 0 / 0 | 0 / 10 | - | 279 | 300 | 1.35-1.58 | none(start violates zeta)|- 10 |
| ilp_zeta90 | all | 30 | 19 | 9 | 2 | 0 | 22 / 0 / 8 / 0 | 0 / 30 | 0.015 | 190 | 300 | 0.89-1.58 | written_optimum|- 8; default|True 2; none(start violates zeta)|- 20 |
| ilp_zeta85 | x0.75 | 10 | 10 | 0 | 0 | 0 | 0 / 0 / 10 / 0 | 0 / 10 | 0.006 | - | 0 | 0.89-1.05 | written_optimum|- 10 |
| ilp_zeta85 | x1 | 10 | 10 | 0 | 0 | 0 | 3 / 0 / 7 / 0 | 0 / 10 | 0.004 | 123 | 143 | 1.03-1.28 | default|True 2; written_optimum|- 7; none(start violates zeta)|- 1 |
| ilp_zeta85 | x1.5 | 10 | 0 | 6 | 4 | 0 | 8 / 0 / 0 / 2 | 0 / 10 | - | 282 | 300 | 1.35-1.58 | none(start violates zeta)|- 8; -|- 2 |
| ilp_zeta85 | all | 30 | 20 | 6 | 4 | 0 | 11 / 0 / 17 / 2 | 0 / 30 | 0.006 | 239 | 300 | 0.89-1.58 | written_optimum|- 17; default|True 2; none(start violates zeta)|- 9; -|- 2 |
| ilp_relaxed | x0.75 | 10 | 10 | 0 | 0 | 0 | 5 / 5 / 0 / 0 | 5 / 5 | 0.010 | 109 | 219 | 0.89-1.05 | default|True 5; written_ilp|True 5 |
| ilp_relaxed | x1 | 10 | 10 | 0 | 0 | 0 | 5 / 5 / 0 / 0 | 5 / 5 | 0.008 | 96 | 126 | 1.03-1.28 | default|True 5; written_ilp|True 5 |
| ilp_relaxed | x1.5 | 10 | 10 | 0 | 0 | 0 | 6 / 4 / 0 / 0 | 4 / 6 | 0.009 | 157 | 212 | 1.35-1.58 | default|True 5; written_ilp|True 5 |
| ilp_relaxed | all | 30 | 30 | 0 | 0 | 0 | 16 / 14 / 0 / 0 | 14 / 16 | 0.010 | 123 | 219 | 0.89-1.58 | default|True 15; written_ilp|True 15 |

- Written ILP: 15 solves in round 3 (seeds 5-9) with 14 OPTIMAL and 1 TIME_LIMIT (seed 7 x1.5, gap 0.11 %, 781 nodes); 15 reused round-2 rows with 14 OPTIMAL and 1 TIME_LIMIT (seed 0 x1, 150 s limit of round 2, gap 0.04 %). 26 of 30 closed at the root node. MIP start accepted on 29/30 (one default start rejected at x1.5, the solve still closed at OPTIMAL).
- zeta 0.90: 22 solves, 3.9 + 19.3 + 46.5 min of Gurobi time per level; the only feasible TIME_LIMIT cell is seed 6 x1 (714.29, gap 0.015 %, 788 nodes). The 10 x1.5 solves took 175-300 s each (2 INFEASIBLE in 175-214 s, 8 at the limit) and each was followed by a max-service solve of 129-300 s (6 closed).
- zeta 0.85: 11 solves (3 at x1, 8 at x1.5), 17 cells implied by the written optimum, 2 implied by the certified maximum share.
- Relaxed ILP: 16 solves, all OPTIMAL, 96-157 s mean per level; MIP start = written ILP schedule on the 15 round-3 cells (all accepted).
- Counts over all 120 ILP cells: OPTIMAL 97, TIME_LIMIT 17 (2 written with gap <= 0.11 %, 1 zeta-0.90 feasible with gap 0.015 %, 14 zeta cells at x1.5 without an incumbent), INFEASIBLE 6, SKIPPED_BUDGET 0. Round-3 Gurobi time: 64 solved cells, 181.9 min, plus 18 max-service solves (one per x1.5 zeta cell that was not implied), 70.9 min; 252.8 of the 263.2 min wall.

## Per instance (USD per 4 h window; [n] = unserved orders; TL = TIME_LIMIT with MIP gap)

| instance | orders | baseline [unserved] | ILP written [unserved] | ILP zeta 0.90 [unserved] | ILP zeta 0.85 [unserved] | ILP relaxed [unserved] | gap written % | gap zeta 0.90 % | gap zeta 0.85 % | premium 0.90 USD | premium 0.85 USD | ILP source / status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h-K6-I27-seed0-x0.75 | 27 | 460.7 [1] | 443.9 [1] | 443.9 [1] (implied) | 443.9 [1] (implied) | 443.9 [1] | 3.7 | 3.7 | 3.7 | 0.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I27-seed1-x0.75 | 27 | 536.2 [2] | 471.0 [1] | 471.0 [1] (implied) | 471.0 [1] (implied) | 470.9 [1] | 12.2 | 12.2 | 12.2 | 0.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I27-seed2-x0.75 | 27 | 480.9 [1] | 462.9 [0] | 462.9 [0] (implied) | 462.9 [0] (implied) | 462.6 [0] | 3.8 | 3.8 | 3.8 | 0.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I27-seed3-x0.75 | 27 | 552.7 [2] | 497.3 [3] | 502.7 [2] | 497.3 [3] (implied) | 497.1 [3] | 10.0 | 9.0 | 10.0 | 5.3 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I27-seed4-x0.75 | 27 | 483.2 [1] | 459.2 [1] | 459.2 [1] (implied) | 459.2 [1] (implied) | 459.1 [1] | 5.0 | 5.0 | 5.0 | 0.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I27-seed5-x0.75 | 27 | 718.5 [0] | 510.7 [2] | 510.7 [2] (implied) | 510.7 [2] (implied) | 510.6 [2] | 28.9 | 28.9 | 28.9 | 0.0 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I27-seed6-x0.75 | 27 | 691.1 [1] | 501.2 [3] | 501.7 [2] | 501.2 [3] (implied) | 501.1 [3] | 27.5 | 27.4 | 27.5 | 0.5 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I27-seed7-x0.75 | 27 | 589.3 [0] | 488.4 [1] | 488.4 [1] (implied) | 488.4 [1] (implied) | 488.2 [1] | 17.1 | 17.1 | 17.1 | 0.0 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I27-seed8-x0.75 | 27 | 699.6 [1] | 499.2 [3] | 502.7 [2] | 499.2 [3] (implied) | 498.9 [3] | 28.6 | 28.1 | 28.6 | 3.5 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I27-seed9-x0.75 | 27 | 562.0 [0] | 467.1 [0] | 467.1 [0] (implied) | 467.1 [0] (implied) | 466.9 [0] | 16.9 | 16.9 | 16.9 | 0.0 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I36-seed0-x1 | 36 | 733.1 [1] | 615.4 [1] (TL 0.04 %) | 615.1 [1] | 615.1 [1] | 614.5 [1] | 16.1 | 16.1 | 16.1 | -0.2 | -0.2 | round2 / TIME_LIMIT |
| usd4h-K6-I36-seed1-x1 | 36 | 973.2 [7] | 659.6 [5] | 688.3 [3] | 659.6 [5] (implied) | 659.4 [5] | 32.2 | 29.3 | 32.2 | 28.7 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I36-seed2-x1 | 36 | 790.1 [7] | 639.0 [4] | 703.7 [3] | 639.0 [4] (implied) | 638.7 [4] | 19.1 | 10.9 | 19.1 | 64.7 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I36-seed3-x1 | 36 | 932.9 [8] | 662.6 [5] | 708.7 [3] | 662.6 [5] (implied) | 662.3 [5] | 29.0 | 24.0 | 29.0 | 46.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I36-seed4-x1 | 36 | 685.1 [3] | 614.8 [3] | 614.8 [3] (implied) | 614.8 [3] (implied) | 614.5 [3] | 10.3 | 10.3 | 10.3 | 0.0 | 0.0 | round2 / OPTIMAL |
| usd4h-K6-I36-seed5-x1 | 36 | 1116.4 [3] | 657.0 [4] | 673.2 [3] | 657.0 [4] (implied) | 656.6 [4] | 41.1 | 39.7 | 41.1 | 16.1 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I36-seed6-x1 | 36 | 1310.3 [6] | 677.7 [6] | 714.3 [3] (TL 0.01 %) | 681.0 [5] | 677.5 [6] | 48.3 | 45.5 | 48.0 | 36.6 | 3.2 | round3 / OPTIMAL |
| usd4h-K6-I36-seed7-x1 | 36 | 1065.9 [3] | 684.6 [5] | 689.2 [3] | 684.6 [5] (implied) | 684.0 [5] | 35.8 | 35.3 | 35.8 | 4.7 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I36-seed8-x1 | 36 | 1311.3 [3] | 718.7 [8] | 894.6 [3] | 795.6 [5] | 718.5 [8] | 45.2 | 31.8 | 39.3 | 175.9 | 76.9 | round3 / OPTIMAL |
| usd4h-K6-I36-seed9-x1 | 36 | 1007.0 [5] | 656.5 [4] | 657.9 [3] | 656.5 [4] (implied) | 656.3 [4] | 34.8 | 34.7 | 34.8 | 1.4 | 0.0 | round3 / OPTIMAL |
| usd4h-K6-I54-seed0-x1.5 | 54 | 1642.2 [17] | 1008.5 [11] | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1007.9 [11] | 38.6 | - | - | - | - | round2 / OPTIMAL |
| usd4h-K6-I54-seed1-x1.5 | 54 | 1998.6 [21] | 1124.3 [17] | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1123.9 [17] | 43.7 | - | - | - | - | round2 / OPTIMAL |
| usd4h-K6-I54-seed2-x1.5 | 54 | 1367.6 [18] | 1061.6 [15] | INFEASIBLE (solved) | INFEASIBLE (solved) | 1061.1 [15] | 22.4 | - | - | - | - | round2 / OPTIMAL |
| usd4h-K6-I54-seed3-x1.5 | 54 | 1959.0 [20] | 1114.7 [17] | TIME_LIMIT (solved) | INFEASIBLE (by max share) | 1114.3 [17] | 43.1 | - | - | - | - | round2 / OPTIMAL |
| usd4h-K6-I54-seed4-x1.5 | 54 | 1739.0 [20] | 1062.1 [15] | TIME_LIMIT (solved) | INFEASIBLE (by max share) | 1061.9 [15] | 38.9 | - | - | - | - | round2 / OPTIMAL |
| usd4h-K6-I54-seed5-x1.5 | 54 | 2029.6 [20] | 1101.2 [16] | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1100.5 [16] | 45.7 | - | - | - | - | round3 / OPTIMAL |
| usd4h-K6-I54-seed6-x1.5 | 54 | 2325.0 [21] | 1120.3 [17] | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1119.9 [17] | 51.8 | - | - | - | - | round3 / OPTIMAL |
| usd4h-K6-I54-seed7-x1.5 | 54 | 2137.6 [23] | 1152.0 [19] (TL 0.11 %) | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1151.5 [19] | 46.1 | - | - | - | - | round3 / TIME_LIMIT |
| usd4h-K6-I54-seed8-x1.5 | 54 | 2173.4 [21] | 1160.2 [20] | INFEASIBLE (solved) | INFEASIBLE (solved) | 1159.6 [20] | 46.6 | - | - | - | - | round3 / OPTIMAL |
| usd4h-K6-I54-seed9-x1.5 | 54 | 1930.7 [21] | 1079.3 [16] | TIME_LIMIT (solved) | TIME_LIMIT (solved) | 1079.0 [16] | 44.1 | - | - | - | - | round3 / OPTIMAL |

## Comparison with round 2

| quantity | round 2 (seeds 0-4) | round 3 (seeds 0-9) |
|---|---|---|
| headline gap, written ILP vs baseline R2.3 | 21.9 % +/- 8.1 (n = 15) | 29.6 % +/- 5.6 (n = 30); seeds 0-4 unchanged 21.9 +/- 8.1, seeds 5-9 37.2 +/- 6.2 |
| by demand level | 6.9 / 21.3 / 37.3 % (n = 5) | 15.4 +/- 7.3 / 31.2 +/- 9.1 / 42.1 +/- 5.7 % (n = 10) |
| mean totals baseline / ILP | 1022.3 / 726.5 USD | 1166.7 / 745.7 USD |
| decomposition (lateness / response / unserved) | 54 / 25 / 20 % | 59 / 32 / 8 % |
| relaxed control | 19.0 % as recorded, 21.9 % best known (1 TIME_LIMIT at the MIP start) | 29.6 % +/- 5.6, all 30 OPTIMAL; end targets worth 0.34 USD per instance |
| service-first variant | lexicographic: 14.9 % +/- 8.0, stage 1 certified on 5/15 only (not citable) | zeta 0.90: feasible on 20/30, 21.5 % +/- 5.9 on those, premium 0.9 USD (x0.75) / 37.4 USD (x1); zeta 0.85: 23.0 % +/- 6.3, premium 0 / 8.0 USD; infeasible on all x1.5 instances (max share 0.74-0.83) |
| written ILP solver status | 23/27 OPTIMAL incl. variants, 150 s limit | 28/30 OPTIMAL, 2 TIME_LIMIT with gap <= 0.11 %, 300 s limit |
| wall | 92 + 20 min | 263 min (300 min budget) |

The lexicographic column of round 2 is superseded: where it was certified (x0.75 seeds 0, 3, 4; x1 seeds 0, 3) its minimum-unserved solution coincides with or is dominated by the zeta-0.90 cell (seed 3 x0.75: lex 502.7 with 2 unserved = zeta-0.90 502.7; seed 3 x1: lex 708.7 with 3 unserved = zeta-0.90 708.7), and the uncertified x1.5 stage-1 incumbents (17-21 unserved) are now explained by the certified maximum shares (11-14 unserved at best).

## Figures

- `gap_by_demand.png` -- headline gap per demand level for the written ILP, the two zeta settings and the relaxed control: 10-seed means with 95 % t-CI bars and seed dots; the x1.5 zeta cells are marked infeasible 10/10.
- `zeta_premium.png` -- left: premium of zeta 0.90 and 0.85 over the written optimum per seed at x0.75 and x1 (USD per 4 h); right: served share per instance for baseline / written / zeta 0.85 / zeta 0.90 against the required shares.
- `cost_components.png` -- stacked mean cost components (unserved, response, lateness, travel, electricity, setup) per method and demand level.
- `drop_rates.png` -- left: drop rate (% of orders) per method and demand level with seed dots; right: for the ten x1.5 seeds the maximum feasible served share (incumbent bar, Gurobi upper bound tick, certified or bound) against the zeta lines, with the written ILP and baseline shares.

## Anomalies and caveats

1. Seed 0 x1: the reused round-2 written row is a TIME_LIMIT incumbent (615.36, gap 0.04 %) and both zeta cells, solved in round 3 as restrictions of the same model, closed 0.22 USD below it (615.15). The written row is 0.04 % suboptimal; the recorded premium of -0.2 USD reads as 0, and the headline gap on this instance (16.1 %) is a lower bound by 0.03 points.
2. x1.5 zeta cells: 4 of 10 per zeta level are recorded as `zeta_feasible = None` (undecided) because the max-service solve timed out at 300 s, although its dual bound (at least 9-13 unserved) already excludes both zeta levels. The feasibility counts above treat them as infeasible by bound; the script's CSV does not.
3. The zeta-0.90 / 0.85 solves at x1.5 ran without a MIP start (neither the written nor the policy schedule satisfies (33) there) and never found an incumbent: 14 of the 18 ran to the 300 s limit and 4 ended INFEASIBLE in 175-248 s, each followed by a max-service solve of 129-300 s, so 18 of the 20 x1.5 zeta cells cost 300-600 s for a result that the bound of one max-service solve per instance settles. A cheaper design would run `min sum u` first and skip the zeta solves whose target exceeds the bound (as `implied_by_max_service` already does for the second zeta level).
4. Seeds 5-9 are markedly worse for the baseline than seeds 0-4 at every demand level (baseline +30 % / +41 % / +22 %), which raises the pooled gap from 21.9 to 29.6 %; the round-2 numbers are reproduced exactly, so this is sampling, not a code change, but it means the round-2 CI (+/- 8.1) was optimistic about the between-seed spread of the baseline.
5. The ILP drops more orders than the baseline on 8 of 30 instances (x0.75 seeds 3, 5, 6, 7, 8; x1 seeds 5, 7, 8), by 1-5 orders, because at P = 30 USD a drop is cheaper than serving late; the service-share results quantify what it costs to forbid this (0.5-5.3 USD at x0.75, up to 176 USD at x1).
6. Baseline runs violate the report-only end targets (17) on 5 and (18) on 6 of 30 instances (check_ok False on 9 rows, `ok_modulo_report_only` True on all); not priced, so the gap is conservative there.
7. Solve times were measured while the E3u / E4u / E8 round-3 scripts ran concurrently on the same machine; the written-ILP round-3 mean of 143 s (round 2: 90 s at a 150 s limit) is not a clean benchmark.
8. Reused round-2 rows lack `n_vars` / `threads` and were solved with TimeLimit 150 s; the only round-2 TIME_LIMIT row that passes the reuse rule (gap <= 1 %) is the seed 0 x1 written cell (0.04 %, see 1).
9. The max-service bound and the `implied_by_max_service` cells are for the written constraint set (rho 0.5, R_end 1); the relaxed-target maximum share was not solved, so the statement "no schedule can serve 85 %" is for the written model (the end targets cost under 1 USD in the cost optimum on this family, so a relaxed bound is unlikely to differ by more than one order).

## Interpretation

Round 3 settles the two open questions of round 2 for E2u. First, the coordination value is robust to the seed sample: on 10 seeds the written ILP saves 29.6 % +/- 5.6 of the baseline's USD cost over the 4 h window (15 / 31 / 42 % at x0.75 / x1 / x1.5) and is cheaper on every one of the 30 instances, with the gap rising with demand because the rule baseline's lateness explodes while the ILP's total is almost deterministic (CV 3-5 %). Second, the service level can now be imposed cleanly: at zeta = 0.90 the constraint is free at x0.75 (0.2 %), costs 5.5 % at x1 (37 USD, i.e. about 22 USD net per rescued order, with the service share rising from 0.875 to 0.922 and the saving against the baseline staying at 27.8 %), and is infeasible at x1.5 because 54 orders in 4 h exceed what 6 bikes can deliver under any schedule (maximum feasible share 0.74-0.83). At zeta = 0.85 the constraint is essentially free (binding on 2 of 20 feasible instances). The relaxed-target control confirms on 30 solved-to-optimality instances that the end targets (17)-(18) are worth 0.3 USD per instance, so the advantage is sequencing and dispatching, not stock management or energy; the composition (59 % lateness, 32 % response, 8 % unserved) is the same as in round 2 and in E8. For the paper: the headline is 29.6 % +/- 5.6 (n = 30); the service-share result gives a clean two-line statement (90 % service is attainable at x0.75 and x1 for 0.2 % and 5.5 % of the optimal cost, and not attainable at x1.5 with 6 bikes), and the lexicographic variant should not be cited. What remains open is a fleet-size sweep at x1.5 (how many bikes make 90 % feasible, and at what cost) and the relaxed-target maximum share, both cheap to add.
