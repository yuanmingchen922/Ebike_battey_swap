# E2 (v2) -- fixed event-driven baseline vs the stored coordinated ILP

Re-evaluation of `RESULTS.md` after the baseline fixes (reviewer F1 just-in-time dispatch, F2 dead-zone swap after a reach refusal, F3/F6 RESERVE and informed variants, F4 explicit gap conventions). The 15 instances are the stored `instances/*.json` (10 bikes, |I| in {22, 30, 45}, H = 24 x 5 min, L = 12, 3 co-located fixed sites, 12 site <-> site shuttles, seeds [0, 1, 2, 3, 4]), each verified byte-identical to the generator output; the arc library is rebuilt with the same pruning (reposition targets = restaurants + facilities + depots, tau_max = 4, start_slack = 6, reachable = True) and its size equals the stored `n_arcs` in every instance. **Only the baseline side was re-run**; the `ilp` (rho = 0.5, R_end = 1) and `ilp_rho0` (rho = 0, R_end = 1) rows are taken unchanged from `results.csv` (Gurobi 13, TimeLimit 240 s; 4 of 30 solves at x1.5 ended at the limit with gap <= 2.1 %). The legacy flags (`jit_dispatch = False`, `swap_on_reach_refusal = False`) reproduce the stored `baseline` rows exactly (asserted on total, travel, unserved, swaps, (17)/(18) shortfalls in all 15 instances), so the old and new baselines are compared on the same schedules. MIP-start acceptance is certified with the fix-and-solve solve (x, u, c, h, z, n fixed; OutputFlag 0, Threads 4, TimeLimit 120 s) under the written model and under the fully relaxed end targets (`common.relax_end_targets`: rho = 0 AND R_end_j = 0); the free ILP was not re-solved. Wall time 6.2 min.

## Headline

**Baseline v2 vs `ilp_rho0` (headline gap = (baseline - ILP) / baseline): 24.0 % (95 % t-CI +/- 8.7, n = 15)**, by demand x0.75: 4.3 +/- 1.5 %, x1: 29.6 +/- 18.2 %, x1.5: 38.2 +/- 7.5 %; vs the written model (`ilp`, rho = 0.5): 24.0 % (+/- 8.7). The legacy baseline gave 28.0 % (+/- 7.2) and 28.0 % respectively, i.e. the fixes close 4.0 points of the reported gap. Excluding the constant setup term (27) the operational-cost reduction is 26.9 % (+/- 9.2). The fixed policy lowers the baseline's own cost by 4.1 % on average (+/- 5.5; 10 instances better, 5 worse, 0 unchanged), saves 6.3 km of bike travel per instance (+/- 2.9; 113.5 -> 107.5 km at base demand) and 0.20 unserved orders (+/- 0.51); 42 % of the new baseline's dispatches are just-in-time starts (the nearest idle bike was blocked only by the dominance rule; under the old rule each such case went either to a farther bike or to the same bike one or more boundaries later, so this is an upper bound on the reviewer's 23 % 'farther bike' share). The gap is still dominated by unserved orders (90 % of the baseline-minus-ILP difference; x0.75 0 %, x1 87 %, x1.5 93 %).
 MIP start: the new default schedule is accepted under the written model in 11 of 15 instances (it violates (18) in 1 and (17) in 4; legacy: 3 / 2) and under the fully relaxed end targets in 15 of 15; the RESERVE variant is accepted in 14 / 15 (written) and 15 / 15 (relaxed) and costs -0.6 % relative to the default (negative = cheaper).


## Relative improvement over the baseline variants (mean over seeds, 95 % t-CI)

| comparison | demand_mult | n_seeds | rel_impr_mean_pct | rel_impr_ci95_pct | rel_impr_lo_pct | rel_impr_hi_pct | abs_gain_mean | rel_impr_ex_setup_mean_pct | rel_impr_ex_setup_ci95_pct |
|---|---|---|---|---|---|---|---|---|---|
| ILP (rho=0.5) vs baseline v2 | 0.75 | 5 | 4.27 | 1.49 | 2.78 | 5.77 | 17.52 | 5.93 | 2.12 |
| ILP (rho=0.5) vs baseline v2 | 1 | 5 | 29.61 | 18.17 | 11.44 | 47.78 | 251.77 | 34.43 | 20.00 |
| ILP (rho=0.5) vs baseline v2 | 1.50 | 5 | 38.20 | 7.47 | 30.73 | 45.67 | 862.04 | 40.24 | 7.85 |
| ILP (rho=0.5) vs baseline v2 | all | 15 | 24.03 | 8.68 | 15.35 | 32.71 | 377.11 | 26.87 | 9.15 |
| ILP (rho=0) vs baseline v2 [headline] | 0.75 | 5 | 4.27 | 1.49 | 2.78 | 5.77 | 17.52 | 5.93 | 2.12 |
| ILP (rho=0) vs baseline v2 [headline] | 1 | 5 | 29.61 | 18.17 | 11.44 | 47.78 | 251.77 | 34.43 | 20.00 |
| ILP (rho=0) vs baseline v2 [headline] | 1.50 | 5 | 38.19 | 7.51 | 30.68 | 45.70 | 861.91 | 40.23 | 7.89 |
| ILP (rho=0) vs baseline v2 [headline] | all | 15 | 24.02 | 8.68 | 15.34 | 32.71 | 377.07 | 26.86 | 9.15 |
| ILP (rho=0.5) vs baseline legacy | 0.75 | 5 | 12.59 | 10.99 | 1.60 | 23.59 | 59.46 | 16.65 | 14.04 |
| ILP (rho=0.5) vs baseline legacy | 1 | 5 | 34.61 | 15.59 | 19.02 | 50.21 | 309.29 | 39.91 | 16.55 |
| ILP (rho=0.5) vs baseline legacy | 1.50 | 5 | 36.84 | 5.86 | 30.98 | 42.69 | 810.59 | 38.86 | 6.20 |
| ILP (rho=0.5) vs baseline legacy | all | 15 | 28.01 | 7.19 | 20.82 | 35.21 | 393.12 | 31.80 | 7.47 |
| ILP (rho=0) vs baseline legacy | 0.75 | 5 | 12.59 | 10.99 | 1.60 | 23.59 | 59.46 | 16.65 | 14.04 |
| ILP (rho=0) vs baseline legacy | 1 | 5 | 34.61 | 15.59 | 19.02 | 50.21 | 309.29 | 39.91 | 16.55 |
| ILP (rho=0) vs baseline legacy | 1.50 | 5 | 36.83 | 5.90 | 30.93 | 42.73 | 810.46 | 38.85 | 6.24 |
| ILP (rho=0) vs baseline legacy | all | 15 | 28.01 | 7.20 | 20.82 | 35.21 | 393.07 | 31.80 | 7.47 |
| ILP (rho=0.5) vs baseline RESERVE | 0.75 | 5 | 3.82 | 1.68 | 2.14 | 5.49 | 15.62 | 5.30 | 2.36 |
| ILP (rho=0.5) vs baseline RESERVE | 1 | 5 | 29.23 | 18.56 | 10.67 | 47.78 | 248.37 | 33.99 | 20.48 |
| ILP (rho=0.5) vs baseline RESERVE | 1.50 | 5 | 37.71 | 7.31 | 30.40 | 45.02 | 843.85 | 39.74 | 7.69 |
| ILP (rho=0.5) vs baseline RESERVE | all | 15 | 23.58 | 8.71 | 14.87 | 32.30 | 369.28 | 26.34 | 9.23 |
| ILP (rho=0) vs baseline RESERVE | 0.75 | 5 | 3.82 | 1.68 | 2.14 | 5.49 | 15.62 | 5.30 | 2.36 |
| ILP (rho=0) vs baseline RESERVE | 1 | 5 | 29.23 | 18.56 | 10.67 | 47.78 | 248.37 | 33.99 | 20.48 |
| ILP (rho=0) vs baseline RESERVE | 1.50 | 5 | 37.70 | 7.36 | 30.35 | 45.06 | 843.72 | 39.73 | 7.73 |
| ILP (rho=0) vs baseline RESERVE | all | 15 | 23.58 | 8.71 | 14.87 | 32.30 | 369.24 | 26.34 | 9.23 |
| baseline v2 vs baseline legacy | 0.75 | 5 | 8.61 | 12.50 | -3.89 | 21.12 | 41.94 | 11.25 | 16.22 |
| baseline v2 vs baseline legacy | 1 | 5 | 6.03 | 17.91 | -11.88 | 23.93 | 57.52 | 6.76 | 21.41 |
| baseline v2 vs baseline legacy | 1.50 | 5 | -2.41 | 4.81 | -7.22 | 2.39 | -51.44 | -2.55 | 5.08 |
| baseline v2 vs baseline legacy | all | 15 | 4.07 | 5.46 | -1.39 | 9.54 | 16.01 | 5.15 | 6.67 |
| baseline RESERVE vs baseline v2 | 0.75 | 5 | 0.47 | 0.50 | -0.02 | 0.97 | 1.89 | 0.66 | 0.70 |
| baseline RESERVE vs baseline v2 | 1 | 5 | 0.49 | 0.48 | 0.01 | 0.97 | 3.40 | 0.59 | 0.60 |
| baseline RESERVE vs baseline v2 | 1.50 | 5 | 0.79 | 2.11 | -1.31 | 2.90 | 18.18 | 0.83 | 2.22 |
| baseline RESERVE vs baseline v2 | all | 15 | 0.58 | 0.49 | 0.10 | 1.07 | 7.83 | 0.70 | 0.53 |
| baseline informed vs baseline v2 | 0.75 | 5 | 0.47 | 0.50 | -0.02 | 0.97 | 1.89 | 0.66 | 0.70 |
| baseline informed vs baseline v2 | 1 | 5 | 0.49 | 0.48 | 0.01 | 0.97 | 3.40 | 0.59 | 0.60 |
| baseline informed vs baseline v2 | 1.50 | 5 | 0.79 | 2.11 | -1.31 | 2.90 | 18.18 | 0.83 | 2.22 |
| baseline informed vs baseline v2 | all | 15 | 0.58 | 0.49 | 0.10 | 1.07 | 7.83 | 0.70 | 0.53 |
| baseline REORDER_POINT vs baseline v2 | 0.75 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline REORDER_POINT vs baseline v2 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline REORDER_POINT vs baseline v2 | 1.50 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline REORDER_POINT vs baseline v2 | all | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone vs baseline v2 | 0.75 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone vs baseline v2 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone vs baseline v2 | 1.50 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| baseline zone vs baseline v2 | all | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

`rel_impr` = (cost_A - cost_B) / cost_A in % for the pair 'B vs A' (`common.gap_definitions` `gap_vs_baseline_pct`, the headline convention); `rel_impr_ex_setup` divides by cost_A minus the constant setup term (27) (C_setup = 114); negative = B is worse than A. The ILP rows are the stored solutions; `ilp_rho0` kept R_end_j = 1, so against the fully relaxed ILP the improvement is at least the value shown.

## Legacy vs fixed baseline (legacy minus new, mean over seeds, 95 % t-CI)

| demand_mult | n | legacy_total_mean | new_total_mean | cost_saving_mean | cost_saving_ci95 | cost_saving_pct_mean | cost_saving_pct_ci95 | km_saved_mean | km_saved_ci95 | unserved_reduction_mean | unserved_reduction_ci95 | swaps_change_mean | new_better_n | new_worse_n | jit_dispatches_mean | jit_share_of_dispatches_pct | reach_refusals_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.75 | 5 | 452.52 | 410.58 | 41.94 | 62.10 | 8.61 | 12.50 | 8.61 | 4.94 | 0.40 | 0.68 | -0.80 | 5 | 0 | 13.80 | 63.30 | 0.20 |
| 1 | 5 | 844.08 | 786.56 | 57.52 | 128.55 | 6.03 | 17.91 | 6.03 | 7.15 | 0.60 | 1.42 | 0 | 4 | 1 | 11.40 | 41.61 | 0 |
| 1.50 | 5 | 2201.87 | 2253.32 | -51.44 | 103.22 | -2.41 | 4.81 | 4.38 | 9.28 | -0.40 | 1.42 | -0.20 | 1 | 4 | 8.20 | 27.70 | 0 |
| all | 15 | 1166.16 | 1150.15 | 16.01 | 45.92 | 4.07 | 5.46 | 6.34 | 2.92 | 0.20 | 0.51 | -0.33 | 10 | 5 | 11.13 | 42.39 | 0.07 |

`jit_share_of_dispatches_pct` = just-in-time dispatches / served orders of the new policy (dispatches in which the nearest idle bike was blocked only by the ILP's dominance rule and now waits and starts at a_i - tau_r); `reach_refusals_mean` = reach-only refusals per run (the dead-zone rule sends such bikes to swap).

## Per instance: legacy / new / RESERVE baseline, stored ILPs, both gap conventions, MIP-start certificates

| name | legacy_total | new_total | reserve_total | legacy_km | new_km | legacy_unserved | new_unserved | legacy_swaps | new_swaps | new_jit_dispatches | new_reach_refusals | ilp_total | ilp_rho0_total | gap_vs_baseline_pct_rho0 | gap_vs_ilp_pct_rho0 | legacy_gap_vs_baseline_pct_rho0 | new_families | new_start_written | new_start_relaxed | reserve_families | reserve_start_written | reserve_start_relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2-K10-I22-seed0 | 489.0 | 389.5 | 385.4 | 96.6 | 84.9 | 1 | 0 | 4 | 4 | 17 | 0 | 377.4 | 377.4 | 3.1 | 3.2 | 22.8 | {} | True | True | {} | True | True |
| e2-K10-I22-seed1 | 456.7 | 455.9 | 455.9 | 71.1 | 66.8 | 1 | 1 | 4 | 3 | 13 | 0 | 438.2 | 438.2 | 3.9 | 4.0 | 4.0 | {} | True | True | {} | True | True |
| e2-K10-I22-seed2 | 497.2 | 404 | 402.5 | 91.2 | 84 | 1 | 0 | 2 | 1 | 9 | 0 | 390.7 | 390.7 | 3.3 | 3.4 | 21.4 | {} | True | True | {} | True | True |
| e2-K10-I22-seed3 | 384.9 | 382.7 | 381.6 | 88.8 | 82.8 | 0 | 0 | 5 | 4 | 15 | 0 | 361.1 | 361.1 | 5.7 | 6.0 | 6.2 | {} | True | True | {} | True | True |
| e2-K10-I22-seed4 | 434.8 | 420.9 | 418.1 | 106.4 | 92.6 | 0 | 0 | 7 | 6 | 15 | 1 | 398.0 | 398.0 | 5.4 | 5.8 | 8.5 | {} | True | True | {} | True | True |
| e2-K10-I30-seed0 | 968.9 | 872.9 | 869.6 | 117.7 | 104.2 | 5 | 4 | 8 | 8 | 16 | 0 | 485.0 | 485.0 | 44.4 | 80.0 | 49.9 | {} | True | True | {} | True | True |
| e2-K10-I30-seed1 | 805.5 | 720.6 | 718.2 | 107.7 | 109.5 | 3 | 2 | 5 | 5 | 10 | 0 | 574 | 574 | 20.3 | 25.5 | 28.7 | {} | True | True | {} | True | True |
| e2-K10-I30-seed2 | 1073.5 | 1062.8 | 1061.3 | 98.7 | 95.7 | 6 | 6 | 4 | 4 | 9 | 0 | 600.6 | 600.6 | 43.5 | 77.0 | 44.1 | {} | True | True | {} | True | True |
| e2-K10-I30-seed3 | 593.2 | 683.5 | 680.5 | 119.8 | 111.6 | 0 | 1 | 7 | 6 | 10 | 0 | 484.6 | 484.6 | 29.1 | 41.0 | 18.3 | {"(17)": 1} | False | True | {"(17)": 1} | False | True |
| e2-K10-I30-seed4 | 779.4 | 593.0 | 586.2 | 123.8 | 116.5 | 2 | 0 | 5 | 6 | 12 | 0 | 529.7 | 529.7 | 10.7 | 11.9 | 32.0 | {"(17)": 1} | False | True | {} | True | True |
| e2-K10-I45-seed0 | 2078.0 | 2102.9 | 2102.9 | 120.4 | 123.4 | 14 | 14 | 4 | 3 | 9 | 0 | 1358.9 | 1358.9 | 35.4 | 54.7 | 34.6 | {} | True | True | {} | True | True |
| e2-K10-I45-seed1 | 2115.9 | 2288.3 | 2200.7 | 114.8 | 113.0 | 14 | 16 | 4 | 5 | 8 | 0 | 1362.6 | 1362.6 | 40.5 | 67.9 | 35.6 | {} | True | True | {} | True | True |
| e2-K10-I45-seed2 | 2270.4 | 2212.6 | 2211.9 | 113.7 | 111.3 | 17 | 16 | 6 | 5 | 7 | 0 | 1553.5 | 1555.7 | 29.7 | 42.2 | 31.5 | {"(17)": 1} | False | True | {} | True | True |
| e2-K10-I45-seed3 | 2119.4 | 2190.2 | 2190.2 | 123 | 106.0 | 14 | 15 | 7 | 7 | 8 | 0 | 1184.9 | 1184.9 | 45.9 | 84.8 | 44.1 | {"(17)": 1, "(18)": 1} | False | True | {} | True | True |
| e2-K10-I45-seed4 | 2425.7 | 2472.6 | 2470.0 | 122.2 | 118.5 | 16 | 16 | 6 | 6 | 9 | 0 | 1496.5 | 1495 | 39.5 | 65.4 | 38.4 | {} | True | True | {} | True | True |

`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP (baseline excess over the optimum); `*_start_written` / `*_start_relaxed` = fix-and-solve certificate of the schedule as MIP start under the written model / under rho = 0 and R_end = 0.

## Cost (26) and components (27)-(32): mean over seeds per demand level and method

| demand_mult | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 |
| 0.75 | baseline_legacy | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 |
| 0.75 | baseline_reserve | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 |
| 0.75 | baseline_informed | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 |
| 0.75 | baseline_reorder | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 |
| 0.75 | baseline_zone | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 |
| 0.75 | ilp | 393.06 | 114 | 0 | 70.86 | 20 | 177.40 | 10.80 | 0 |
| 0.75 | ilp_rho0 | 393.06 | 114 | 0 | 70.86 | 20 | 177.80 | 10.40 | 0 |
| 1 | baseline | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 |
| 1 | baseline_legacy | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 |
| 1 | baseline_reserve | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 |
| 1 | baseline_informed | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 |
| 1 | baseline_reorder | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 |
| 1 | baseline_zone | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 |
| 1 | ilp | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 |
| 1 | ilp_rho0 | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 |
| 1.50 | baseline | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 |
| 1.50 | baseline_legacy | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 |
| 1.50 | baseline_reserve | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 |
| 1.50 | baseline_informed | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 |
| 1.50 | baseline_reorder | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 |
| 1.50 | baseline_zone | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 |
| 1.50 | ilp | 1391.28 | 114 | 0 | 118.68 | 740 | 347.40 | 71.20 | 0 |
| 1.50 | ilp_rho0 | 1391.41 | 114 | 0 | 119.61 | 740 | 347.40 | 70.40 | 0 |

## Service / operations metrics: mean over seeds

| demand_mult | method | served_share | mean_response_h | mean_lateness_h | max_lateness_h | n_late | bike_km | n_swaps | queue_wait_slots | kwh_purchased | transfers_used | end_full_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.750 | baseline | 0.991 | 0.694 | 0.021 | 0.150 | 3.800 | 82.200 | 3.600 | 0 | 0.989 | 0 | 9 |
| 0.750 | baseline_legacy | 0.973 | 0.681 | 0.020 | 0.150 | 3.600 | 90.810 | 4.400 | 0 | 1.156 | 0 | 8.400 |
| 0.750 | baseline_reserve | 0.991 | 0.694 | 0.021 | 0.150 | 3.800 | 80.550 | 2.400 | 0 | 0.867 | 0 | 10.200 |
| 0.750 | baseline_informed | 0.991 | 0.694 | 0.021 | 0.150 | 3.800 | 80.550 | 2.400 | 0 | 0.867 | 0 | 10.200 |
| 0.750 | baseline_reorder | 0.991 | 0.694 | 0.021 | 0.150 | 3.800 | 82.200 | 3.600 | 0 | 0.989 | 0 | 9 |
| 0.750 | baseline_zone | 0.991 | 0.694 | 0.021 | 0.150 | 3.800 | 82.200 | 3.600 | 0 | 0.989 | 0 | 9 |
| 0.750 | ilp | 0.991 | 0.678 | 0.021 | 0.150 | 3.800 | 70.860 | 2.200 | 1.600 | 0 | 0 | 9.800 |
| 0.750 | ilp_rho0 | 0.991 | 0.679 | 0.020 | 0.150 | 3.600 | 70.860 | 2 | 0.200 | 0 | 0 | 10 |
| 1 | baseline | 0.913 | 0.768 | 0.073 | 0.333 | 12.600 | 107.520 | 5.800 | 1 | 1.522 | 0 | 7 |
| 1 | baseline_legacy | 0.893 | 0.756 | 0.076 | 0.367 | 10.600 | 113.550 | 5.800 | 0.600 | 1.667 | 0 | 7.200 |
| 1 | baseline_reserve | 0.913 | 0.767 | 0.072 | 0.333 | 12.400 | 104.940 | 4.200 | 0.800 | 1.411 | 0 | 8.600 |
| 1 | baseline_informed | 0.913 | 0.767 | 0.072 | 0.333 | 12.400 | 104.940 | 4.200 | 0.800 | 1.411 | 0 | 8.600 |
| 1 | baseline_reorder | 0.913 | 0.768 | 0.073 | 0.333 | 12.600 | 107.520 | 5.800 | 1 | 1.522 | 0 | 7 |
| 1 | baseline_zone | 0.913 | 0.768 | 0.073 | 0.333 | 12.600 | 107.520 | 5.800 | 1 | 1.522 | 0 | 7 |
| 1 | ilp | 0.987 | 0.716 | 0.038 | 0.300 | 7.200 | 99.390 | 3.800 | 2.600 | 0 | 0 | 8.200 |
| 1 | ilp_rho0 | 0.987 | 0.716 | 0.038 | 0.317 | 7.200 | 99.390 | 3.600 | 2.200 | 0 | 0 | 8.400 |
| 1.500 | baseline | 0.658 | 0.934 | 0.213 | 0.533 | 20.400 | 114.450 | 5.200 | 1 | 1.233 | 0 | 7.200 |
| 1.500 | baseline_legacy | 0.667 | 0.902 | 0.195 | 0.533 | 20.200 | 118.830 | 5.400 | 0.200 | 1.622 | 0 | 7 |
| 1.500 | baseline_reserve | 0.662 | 0.934 | 0.213 | 0.533 | 20.600 | 113.400 | 3.400 | 0.800 | 1.167 | 0 | 9 |
| 1.500 | baseline_informed | 0.662 | 0.934 | 0.213 | 0.533 | 20.600 | 113.400 | 3.600 | 1 | 1.167 | 0 | 8.800 |
| 1.500 | baseline_reorder | 0.658 | 0.934 | 0.213 | 0.533 | 20.400 | 114.450 | 5.200 | 1 | 1.233 | 0 | 7.200 |
| 1.500 | baseline_zone | 0.658 | 0.934 | 0.213 | 0.533 | 20.400 | 114.450 | 5.200 | 1 | 1.233 | 0 | 7.200 |
| 1.500 | ilp | 0.836 | 0.769 | 0.078 | 0.500 | 15.200 | 118.680 | 3.400 | 1 | 0 | 0 | 8.600 |
| 1.500 | ilp_rho0 | 0.836 | 0.769 | 0.077 | 0.483 | 16 | 119.610 | 3.800 | 0.600 | 0 | 0 | 8.200 |

## Policy flags of the baseline variants: mean over seeds

| demand_mult | method | jit_dispatches | reach_refusals | reach_sent_to_swap | late_trips_suppressed | stock_aware_reroutes | n_transfers_used | viol_17 | viol_18 |
|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 13.80 | 0.20 | 0.20 | 0 | 0 | 0 | 0 | 0 |
| 0.75 | baseline_legacy | 0 | 1.20 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0.75 | baseline_reserve | 13.80 | 0.20 | 0.20 | 4.80 | 0 | 0 | 0 | 0 |
| 0.75 | baseline_informed | 13.80 | 0.20 | 0.20 | 4.80 | 0 | 0 | 0 | 0 |
| 0.75 | baseline_reorder | 13.80 | 0.20 | 0.20 | 0 | 0 | 0 | 0 | 0 |
| 0.75 | baseline_zone | 13.80 | 0.20 | 0.20 | 0 | 0 | 0 | 0 | 0 |
| 1 | baseline | 11.40 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0 |
| 1 | baseline_legacy | 0 | 0.20 | 0 | 0 | 0 | 0 | 0.40 | 0.40 |
| 1 | baseline_reserve | 11.40 | 0.80 | 0 | 7.20 | 0 | 0 | 0.20 | 0 |
| 1 | baseline_informed | 11.40 | 0.80 | 0 | 7.20 | 0 | 0 | 0.20 | 0 |
| 1 | baseline_reorder | 11.40 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0 |
| 1 | baseline_zone | 11.40 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0 |
| 1.50 | baseline | 8.20 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0.20 |
| 1.50 | baseline_legacy | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.20 |
| 1.50 | baseline_reserve | 8.20 | 0.40 | 0 | 4 | 0 | 0 | 0 | 0 |
| 1.50 | baseline_informed | 8.20 | 0.40 | 0 | 4 | 0 | 0 | 0.20 | 0.20 |
| 1.50 | baseline_reorder | 8.20 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0.20 |
| 1.50 | baseline_zone | 8.20 | 0 | 0 | 0 | 0 | 0 | 0.40 | 0.20 |

`viol_17` = summed local end-stock shortfall (17), `viol_18` = global shortfall (18) (both reported, not enforced, by the policy); `late_trips_suppressed` and `stock_aware_reroutes` are the informed / RESERVE rules.

## Gap decomposition (baseline v2 - ILP) by component

rho = 0 pair (`ilp_rho0`):

| demand_mult | total_gap | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 17.5 | 2.0 | 11.3 | 0 | 3.8 | 0.4 | 0 | 0 | 21.7 | 2.3 | 64.7 |
| x1 | 251.8 | 3.0 | 8.1 | 220 | -1 | 21.6 | 0 | 87.4 | -0.4 | 8.6 | 3.2 |
| x1.5 | 861.9 | 2.5 | -5.2 | 800 | -15.8 | 80.4 | 0 | 92.8 | -1.8 | 9.3 | -0.6 |
| all | 377.1 | 2.5 | 4.8 | 340 | -4.3 | 34.1 | 0 | 90.2 | -1.1 | 9.1 | 1.3 |

Written model (`ilp`, rho = 0.5):

| demand_mult | total_gap | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 17.5 | 2.0 | 11.3 | 0 | 4.2 | 0 | 0 | 0 | 24.0 | 0 | 64.7 |
| x1 | 251.8 | 3.0 | 8.1 | 220 | -1 | 21.6 | 0 | 87.4 | -0.4 | 8.6 | 3.2 |
| x1.5 | 862.0 | 2.5 | -4.2 | 800 | -15.8 | 79.6 | 0 | 92.8 | -1.8 | 9.2 | -0.5 |
| all | 377.1 | 2.5 | 5.1 | 340 | -4.2 | 33.7 | 0 | 90.2 | -1.1 | 8.9 | 1.3 |

## MIP-start certificates (fix-and-solve, Threads 4, TimeLimit 120 s)

| method | model | n | accepted | check_ok | seconds_mean | seconds_max |
|---|---|---|---|---|---|---|
| baseline | relaxed | 15 | 15 | 15 | 2.29 | 2.71 |
| baseline | written | 15 | 11 | 11 | 2.31 | 2.91 |
| baseline_legacy | relaxed | 15 | 15 | 15 | 2.33 | 2.89 |
| baseline_legacy | written | 15 | 11 | 11 | 2.36 | 2.91 |
| baseline_reserve | relaxed | 15 | 15 | 15 | 2.30 | 2.81 |
| baseline_reserve | written | 15 | 14 | 14 | 2.31 | 2.91 |

Rejected starts: e2-K10-I30-seed0/baseline_legacy/written (INFEASIBLE, families {"(18)": 1}); e2-K10-I30-seed2/baseline_legacy/written (INFEASIBLE, families {"(17)": 1}); e2-K10-I30-seed3/baseline/written (INFEASIBLE, families {"(17)": 1}); e2-K10-I30-seed3/baseline_reserve/written (INFEASIBLE, families {"(17)": 1}); e2-K10-I30-seed3/baseline_legacy/written (INFEASIBLE, families {"(17)": 1, "(18)": 1}); e2-K10-I30-seed4/baseline/written (INFEASIBLE, families {"(17)": 1}); e2-K10-I45-seed2/baseline/written (INFEASIBLE, families {"(17)": 1}); e2-K10-I45-seed3/baseline/written (INFEASIBLE, families {"(17)": 1, "(18)": 1}); e2-K10-I45-seed3/baseline_legacy/written (INFEASIBLE, families {"(18)": 1}).

`evaluate.check` (zero violations) and the Gurobi certificate agree on every schedule.

## Interpretation

The fixed baseline is a stronger opponent: its mean cost falls from 1166.2 to 1150.2 (4.1 %), travel from 107.7 to 101.4 km and unserved orders from 6.27 to 6.07 per instance, so the ILP's headline advantage shrinks from 28.0 % to 24.0 % (rho = 0 pair) and from 28.0 % to 24.0 % (written model), with CI half-widths of 8.7 points. By demand level the ILP's gain over the new baseline is x0.75 4.3 %, x1 29.6 %, x1.5 38.2 % (legacy: 12.6 / 34.6 / 36.8 %): the JIT rule matters most where bikes are plentiful relative to orders and the prep time a_i - r_i is the binding delay; at x1.5 nearly every idle bike is dispatched anyway and the gap is set by how many orders fit into the horizon. The composition of the gap is unchanged in kind: 90 % of the baseline-minus-ILP difference is the P_i = 100 penalty (served share 91 % vs 99 % at base demand, 66 % vs 84 % at x1.5); travel is now 108 km vs 99 km for the ILP at base demand (legacy 114 km), i.e. the 'farther bike' inefficiency the reviewer measured is gone from the baseline; the remaining travel gap (11 km at x0.75 with an identical served share) is what coordinated assignment, swap placement and repositioning buy beyond nearest-bike dispatch, and at x1.5 it reverses because the ILP serves 18 points more of the orders; mean response per served order is 0.77 h (legacy 0.76, ILP 0.72), mean lateness 0.073 h (ILP 0.038). Swaps per run: baseline v2 4.9 (legacy 5.2, RESERVE 3.3, ILP 3.1); the RESERVE variant suppresses 5.3 late swap trips per run and changes the cost by -0.6 % relative to the default (negative = cheaper), while leaving (17) violated in 1 and (18) in 0 of 15 runs (default: 4 / 1; legacy: 2 / 3). REORDER_POINT transfers and zone dispatch change the default by -0.00 % and -0.00 % (12 spares for 10 bikes in a 2 h window leave the reorder rule nothing to ship; the nearest-by-tau rule already picks the same-zone bike), and the informed variant by -0.58 %. What does not change: the ILP rows, the toy and p.7 reproductions, and the conclusion that on this 2-hour / 12-spare family the gain sits in dispatch rather than in battery logistics (the stored fixed-dispatch ILPs recovered < 2 % of the legacy gap; they were not re-solved against the new baseline, see Anomalies). Caveat: toy unit system (P_i = 100 dominates), so the comparison is essentially one of service levels.

## Anomalies and notes

- The fixed policy is more expensive than the legacy one on e2-K10-I30-seed3 (593.2 -> 683.5), e2-K10-I45-seed0 (2078.0 -> 2102.9), e2-K10-I45-seed1 (2115.9 -> 2288.3), e2-K10-I45-seed3 (2119.4 -> 2190.2), e2-K10-I45-seed4 (2425.7 -> 2472.6): a greedy policy is not monotone in its rules (serving an extra order early changes which bikes are idle later); the reviewer predicted these swings.
- New default schedule rejected as MIP start under the written model in 4 instances (e2-K10-I30-seed3, e2-K10-I30-seed4, e2-K10-I45-seed2, e2-K10-I45-seed3): end-target families {"(17)": 1}, {"(17)": 1}, {"(17)": 1}, {"(17)": 1, "(18)": 1}; reported, not enforced (DECISIONS.md). Under the fully relaxed end targets it is accepted in 15 of 15.
- RESERVE schedule rejected under the written model in 1 instances (e2-K10-I30-seed3; families {"(17)": 1}). The reserve guard (`end_reserve_window = W = max sigma + 3 = 4 slots here, sigma_j = 1`) only refuses swaps inside the last W slots; a swap at t < H - W may still take the last full battery (on e2-K10-I30-seed3 site S1 goes 1 -> 0 at t = 18, window starts at t = 20) and a returned q = 1-2 battery needs L - q = 10-11 charging slots, so (17) cannot be restored by H. A window covering the charging lead time (about L - q_thr slots) or a stock-aware guard 'n_jLt - 1 >= R_end_j unless a charge completes by H' would be needed for a guaranteed (17)-feasible start; this is a limitation of the F3 variant in baseline.py / common.BASELINE_VARIANTS, not changed here.
- `ilp_rho0` was solved with rho = 0 but R_end_j = 1 (E2 run), not with the fully relaxed end targets of `common.relax_end_targets`; its objective bounds the fully relaxed optimum from above, so the headline improvement is a lower bound on the fair-control improvement (in E2 the ILP met (17) at zero measurable cost).
- `ilp_fixed_arcs` / `ilp_fixed_assign` fix the *legacy* baseline's dispatch; the chained dispatch decomposition of RESULTS.md is therefore not recomputed for the new baseline (requires new ILP solves).
- Stored ILP runs not proven optimal: e2-K10-I45-seed2/ilp (TIME_LIMIT, gap 0.0198), e2-K10-I45-seed2-rho0/ilp_rho0 (TIME_LIMIT, gap 0.0212), e2-K10-I45-seed4/ilp (TIME_LIMIT, gap 0.0151), e2-K10-I45-seed4-rho0/ilp_rho0 (TIME_LIMIT, gap 0.0138)
- `baseline_informed` coincides with `baseline_reserve` in 15 of 15 runs and `baseline_reserve` with the default in 3: with M_j = 1, sigma_j = 1 and three stocked sites the stock-aware re-routing never fires and the two variants differ only through the (17) reserve guard.

## Figures

- `improvement_vs_demand_v2.png`: relative improvement over the baseline variants vs demand multiplier (mean, 95 % CI).
- `gap_decomposition_v2.png`: baseline v2 minus ILP (rho = 0) by cost component.
- `cost_components_v2.png`: stacked cost components, fixed vs legacy vs RESERVE baseline vs stored ILPs.

Files: `results_v2.csv` (new baseline rows, `source = rerun_v2`, plus the unchanged ILP rows, `source = results.csv`), `improvement_v2.csv`, `legacy_vs_new_v2.csv`, `per_instance_v2.csv`, `gap_decomposition_v2_rho0.csv`, `gap_decomposition_v2_rho05.csv`, `mip_start_v2.csv`, all in `outputs/e2_coord_v2/`. The E2 inputs in `outputs/e2_coord/` (`RESULTS.md`, `results.csv`, `instances/`, figures) are untouched.
