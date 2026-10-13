# E2 v2 -- coordinated ILP vs the *fixed* event-driven baseline (baseline side re-run only)

Byte-identical instances `instances/*.json` of the v1 run (10 bikes, |I| in {22, 30, 45}, H = 24, L = 12, 3 co-located fixed sites, 12 hourly site <-> site shuttles, seeds [0, 1, 2, 3, 4]); arc libraries rebuilt with the v1 pruning (`pruning_for(inst, reachable=True)`), arc counts reproduced in 15/15 instances. **The ILP rows (`ilp` at rho = 0.5, `ilp_rho0` at rho = 0) are the unchanged v1 rows of `results.csv`; the free ILP was not re-solved.** The pre-fix policy (`baseline_legacy`: `jit_dispatch = False`, `swap_on_reach_refusal = False`) reproduces the v1 `baseline` cost exactly in 15/15 instances. MIP-start certificates: fix-and-solve (`ILPModel.verify_mip_start`, Threads 4, TimeLimit 120 s, OutputFlag 0) under the written model and under `relax_end_targets` (rho = 0 and R_end_j = 0). Wall time 8.0 min.

Headline gap definition: `gap_vs_baseline_pct = 100 (baseline - ILP) / baseline` (`common.gap_definitions`); `gap_vs_ilp_pct = 100 (baseline - ILP) / ILP` is in the CSV. `gap_rho0_*` compares with `ilp_rho0` (rho = 0 only; the ILP with R_end = 0 as well was never solved, so the gap against the fully relaxed ILP is >= the rho = 0 gap).

## Headline

- Fixed baseline vs ILP (rho = 0): mean gap **24.0 % (95 % CI +/- 8.7, n = 15)**; vs ILP (rho = 0.5, written model): 24.0 % (+/- 8.7). By demand (rho = 0): x0.75: 4.3 +/- 1.5 %, x1: 29.6 +/- 18.2 %, x1.5: 38.2 +/- 7.5 %.
- v1 (legacy) baseline vs ILP (rho = 0): 28.0 % (+/- 7.2); the fix moves the mean baseline cost from 1166.2 to 1150.2 (-1.4 %), cheaper in 10 and dearer in 5 of 15 instances (greedy policy: a better first leg does not imply a better schedule).
- `baseline_reserve` (end windows W = max sigma + 3): 1142.3 mean cost, gap 23.6 % (+/- 8.7).
- MIP start of the fixed baseline accepted under the written model in 11/15 instances (legacy: 11/15; v1 run: 11/15) and under the fully relaxed end targets in 15/15; `baseline_reserve`: 14/15 written, 15/15 relaxed. Rejections under the relaxed targets can only come from (9) (terminal certificate), since every other family holds by construction.

## Per-instance comparison (fixed baseline `baseline` vs v1 baseline vs unchanged ILP rows)

| name | demand_mult | seed | v1_baseline_total | total | delta_vs_v1_baseline | ilp_total | ilp_rho0_total | v1_gap_rho0_vs_baseline_pct | gap_rho0_vs_baseline_pct | gap_vs_baseline_pct | v1_baseline_unserved_n | n_unserved | ilp_rho0_unserved_n | jit_dispatches | reach_refusals | reach_bikes_sent_to_swap | viol_17 | viol_18 | start_written_accepted | start_relaxed_accepted | v1_mip_start_accepted_rho05 | v1_mip_start_accepted_rho0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2-K10-I22-seed0 | 0.75 | 0 | 489.04 | 389.46 | -99.59 | 377.40 | 377.40 | 22.83 | 3.10 | 3.10 | 1 | 0 | 0 | 17 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I22-seed1 | 0.75 | 1 | 456.66 | 455.86 | -0.79 | 438.20 | 438.20 | 4.04 | 3.87 | 3.87 | 1 | 1 | 1 | 13 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I22-seed2 | 0.75 | 2 | 497.20 | 404 | -93.20 | 390.70 | 390.70 | 21.42 | 3.29 | 3.29 | 1 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I22-seed3 | 0.75 | 3 | 384.91 | 382.69 | -2.22 | 361.05 | 361.05 | 6.20 | 5.65 | 5.65 | 0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I22-seed4 | 0.75 | 4 | 434.79 | 420.88 | -13.91 | 397.95 | 397.95 | 8.47 | 5.45 | 5.45 | 0 | 0 | 0 | 15 | 1 | 1 | 0 | 0 | True | True | True | True |
| e2-K10-I30-seed0 | 1 | 0 | 968.86 | 872.92 | -95.94 | 485.05 | 485.05 | 49.94 | 44.43 | 44.43 | 5 | 4 | 0 | 16 | 0 | 0 | 0 | 0 | True | True | False | True |
| e2-K10-I30-seed1 | 1 | 1 | 805.48 | 720.61 | -84.87 | 574 | 574 | 28.74 | 20.35 | 20.35 | 3 | 2 | 1 | 10 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I30-seed2 | 1 | 2 | 1073.48 | 1062.81 | -10.67 | 600.60 | 600.60 | 44.05 | 43.49 | 43.49 | 6 | 6 | 1 | 9 | 0 | 0 | 0 | 0 | True | True | False | False |
| e2-K10-I30-seed3 | 1 | 3 | 593.18 | 683.49 | 90.31 | 484.60 | 484.60 | 18.31 | 29.10 | 29.10 | 0 | 1 | 0 | 10 | 0 | 0 | 1 | 0 | False | True | False | False |
| e2-K10-I30-seed4 | 1 | 4 | 779.42 | 592.99 | -186.42 | 529.70 | 529.70 | 32.04 | 10.67 | 10.67 | 2 | 0 | 0 | 12 | 0 | 0 | 1 | 0 | False | True | True | True |
| e2-K10-I45-seed0 | 1.50 | 0 | 2078.01 | 2102.89 | 24.89 | 1358.90 | 1358.90 | 34.61 | 35.38 | 35.38 | 14 | 14 | 7 | 9 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I45-seed1 | 1.50 | 1 | 2115.86 | 2288.28 | 172.42 | 1362.60 | 1362.60 | 35.60 | 40.45 | 40.45 | 14 | 16 | 7 | 8 | 0 | 0 | 0 | 0 | True | True | True | True |
| e2-K10-I45-seed2 | 1.50 | 2 | 2270.37 | 2212.63 | -57.73 | 1553.55 | 1555.65 | 31.48 | 29.69 | 29.79 | 17 | 16 | 10 | 7 | 0 | 0 | 1 | 0 | False | True | True | True |
| e2-K10-I45-seed3 | 1.50 | 3 | 2119.44 | 2190.16 | 70.72 | 1184.90 | 1184.90 | 44.09 | 45.90 | 45.90 | 14 | 15 | 5 | 8 | 0 | 0 | 1 | 1 | False | True | False | True |
| e2-K10-I45-seed4 | 1.50 | 4 | 2425.69 | 2472.61 | 46.92 | 1496.45 | 1495 | 38.37 | 39.54 | 39.48 | 16 | 16 | 8 | 9 | 0 | 0 | 0 | 0 | True | True | True | True |

`total` = fixed baseline cost (26); `v1_baseline_total` = legacy; `v1_gap_rho0_*` / `gap_rho0_*` = headline gap of the legacy / fixed baseline against `ilp_rho0`; `gap_vs_baseline_pct` = fixed baseline against the written-model ILP; `start_*_accepted` = fix-and-solve certificate of the fixed baseline (written model / rho = 0 & R_end = 0); `v1_mip_start_accepted_*` = certificate of the legacy start in the v1 run.

## Variant means per demand level (gap mean and 95 % t-CI over seeds, flags, acceptance counts)

| variant | demand_mult | n | baseline_total_mean | ilp_rho05_total_mean | ilp_rho0_total_mean | gap_rho0_mean_pct | gap_rho0_ci95_pct | gap_rho05_mean_pct | gap_rho05_ci95_pct | abs_gain_rho0_mean | unserved_mean | bike_km_mean | swaps_mean | jit_mean | reach_refusals_mean | late_suppressed_mean | viol_17_runs | viol_18_runs | start_written_accepted | start_relaxed_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.75 | 5 | 410.58 | 393.06 | 393.06 | 4.27 | 1.49 | 4.27 | 1.49 | 17.52 | 0.20 | 82.20 | 3.60 | 13.80 | 0.20 | 0 | 0 | 0 | 5 | 5 |
| baseline | 1 | 5 | 786.56 | 534.79 | 534.79 | 29.61 | 18.17 | 29.61 | 18.17 | 251.77 | 2.60 | 107.52 | 5.80 | 11.40 | 0 | 0 | 2 | 0 | 3 | 5 |
| baseline | 1.50 | 5 | 2253.32 | 1391.28 | 1391.41 | 38.19 | 7.51 | 38.20 | 7.47 | 861.91 | 15.40 | 114.45 | 5.20 | 8.20 | 0 | 0 | 2 | 1 | 3 | 5 |
| baseline | all | 15 | 1150.15 | 773.04 | 773.09 | 24.02 | 8.68 | 24.03 | 8.68 | 377.07 | 6.07 | 101.39 | 4.87 | 11.13 | 0.07 | 0 | 4 | 1 | 11 | 15 |
| baseline_legacy | 0.75 | 5 | 452.52 | 393.06 | 393.06 | 12.59 | 10.99 | 12.59 | 10.99 | 59.46 | 0.60 | 90.81 | 4.40 | 0 | 1.20 | 0 | 0 | 0 | 5 | 5 |
| baseline_legacy | 1 | 5 | 844.08 | 534.79 | 534.79 | 34.61 | 15.59 | 34.61 | 15.59 | 309.29 | 3.20 | 113.55 | 5.80 | 0 | 0.20 | 0 | 2 | 2 | 2 | 5 |
| baseline_legacy | 1.50 | 5 | 2201.87 | 1391.28 | 1391.41 | 36.83 | 5.90 | 36.84 | 5.86 | 810.46 | 15 | 118.83 | 5.40 | 0 | 0 | 0 | 0 | 1 | 4 | 5 |
| baseline_legacy | all | 15 | 1166.16 | 773.04 | 773.09 | 28.01 | 7.20 | 28.01 | 7.19 | 393.07 | 6.27 | 107.73 | 5.20 | 0 | 0.47 | 0 | 2 | 3 | 11 | 15 |
| baseline_reserve | 0.75 | 5 | 408.68 | 393.06 | 393.06 | 3.82 | 1.68 | 3.82 | 1.68 | 15.62 | 0.20 | 80.55 | 2.40 | 13.80 | 0.20 | 4.80 | 0 | 0 | 5 | 5 |
| baseline_reserve | 1 | 5 | 783.16 | 534.79 | 534.79 | 29.23 | 18.56 | 29.23 | 18.56 | 248.37 | 2.60 | 104.94 | 4.20 | 11.40 | 0.80 | 7.20 | 1 | 0 | 4 | 5 |
| baseline_reserve | 1.50 | 5 | 2235.13 | 1391.28 | 1391.41 | 37.70 | 7.36 | 37.71 | 7.31 | 843.72 | 15.20 | 113.40 | 3.40 | 8.20 | 0.40 | 4 | 0 | 0 | 5 | 5 |
| baseline_reserve | all | 15 | 1142.33 | 773.04 | 773.09 | 23.58 | 8.71 | 23.58 | 8.71 | 369.24 | 6 | 99.63 | 3.33 | 11.13 | 0.47 | 5.33 | 1 | 0 | 14 | 15 |
| baseline_informed | 0.75 | 5 | 408.68 | 393.06 | 393.06 | 3.82 | 1.68 | 3.82 | 1.68 | 15.62 | 0.20 | 80.55 | 2.40 | 13.80 | 0.20 | 4.80 | 0 | 0 | 5 | 5 |
| baseline_informed | 1 | 5 | 783.16 | 534.79 | 534.79 | 29.23 | 18.56 | 29.23 | 18.56 | 248.37 | 2.60 | 104.94 | 4.20 | 11.40 | 0.80 | 7.20 | 1 | 0 | 4 | 5 |
| baseline_informed | 1.50 | 5 | 2235.13 | 1391.28 | 1391.41 | 37.70 | 7.36 | 37.71 | 7.31 | 843.72 | 15.20 | 113.40 | 3.60 | 8.20 | 0.40 | 4 | 1 | 1 | 4 | 5 |
| baseline_informed | all | 15 | 1142.33 | 773.04 | 773.09 | 23.58 | 8.71 | 23.58 | 8.71 | 369.24 | 6 | 99.63 | 3.40 | 11.13 | 0.47 | 5.33 | 2 | 1 | 13 | 15 |
| baseline_reorder | 0.75 | 5 | 410.58 | 393.06 | 393.06 | 4.27 | 1.49 | 4.27 | 1.49 | 17.52 | 0.20 | 82.20 | 3.60 | 13.80 | 0.20 | 0 | 0 | 0 | 5 | 5 |
| baseline_reorder | 1 | 5 | 786.56 | 534.79 | 534.79 | 29.61 | 18.17 | 29.61 | 18.17 | 251.77 | 2.60 | 107.52 | 5.80 | 11.40 | 0 | 0 | 2 | 0 | 3 | 5 |
| baseline_reorder | 1.50 | 5 | 2253.32 | 1391.28 | 1391.41 | 38.19 | 7.51 | 38.20 | 7.47 | 861.91 | 15.40 | 114.45 | 5.20 | 8.20 | 0 | 0 | 2 | 1 | 3 | 5 |
| baseline_reorder | all | 15 | 1150.15 | 773.04 | 773.09 | 24.02 | 8.68 | 24.03 | 8.68 | 377.07 | 6.07 | 101.39 | 4.87 | 11.13 | 0.07 | 0 | 4 | 1 | 11 | 15 |

## Cost (26) and components (27)-(32): mean over seeds per demand level and method

| demand_mult | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb | n_unserved |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 | 0.20 |
| 0.75 | baseline_legacy | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 | 0.60 |
| 0.75 | baseline_reserve | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 | 0.20 |
| 0.75 | baseline_informed | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 | 0.20 |
| 0.75 | baseline_reorder | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 | 0.20 |
| 0.75 | ilp | 393.06 | 114 | 0 | 70.86 | 20 | 177.40 | 10.80 | 0 | 0.20 |
| 0.75 | ilp_rho0 | 393.06 | 114 | 0 | 70.86 | 20 | 177.80 | 10.40 | 0 | 0.20 |
| 1 | baseline | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 | 2.60 |
| 1 | baseline_legacy | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 | 3.20 |
| 1 | baseline_reserve | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 | 2.60 |
| 1 | baseline_informed | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 | 2.60 |
| 1 | baseline_reorder | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 | 2.60 |
| 1 | ilp | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 | 0.40 |
| 1 | ilp_rho0 | 534.79 | 114 | 0 | 99.39 | 40 | 254.20 | 27.20 | 0 | 0.40 |
| 1.50 | baseline | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 | 15.40 |
| 1.50 | baseline_legacy | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 | 15 |
| 1.50 | baseline_reserve | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 | 15.20 |
| 1.50 | baseline_informed | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 | 15.20 |
| 1.50 | baseline_reorder | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 | 15.40 |
| 1.50 | ilp | 1391.28 | 114 | 0 | 118.68 | 740 | 347.40 | 71.20 | 0 | 7.40 |
| 1.50 | ilp_rho0 | 1391.41 | 114 | 0 | 119.61 | 740 | 347.40 | 70.40 | 0 | 7.40 |

## Gap decomposition (fixed baseline - ILP at rho = 0) by component

| demand_mult | total_gap | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 17.5 | 2.0 | 11.3 | 0 | 3.8 | 0.4 | 0 | 0 | 21.7 | 2.3 | 64.7 |
| x1 | 251.8 | 3.0 | 8.1 | 220 | -1 | 21.6 | 0 | 87.4 | -0.4 | 8.6 | 3.2 |
| x1.5 | 861.9 | 2.5 | -5.2 | 800 | -15.8 | 80.4 | 0 | 92.8 | -1.8 | 9.3 | -0.6 |
| all | 377.1 | 2.5 | 4.8 | 340 | -4.3 | 34.1 | 0 | 90.2 | -1.1 | 9.1 | 1.3 |

## Interpretation

The fix changes the baseline, not the conclusion: the fixed policy costs 1150.2 on average against 1166.2 for the v1 policy, so the coordination gap moves from 28.0 % to 24.0 % (rho = 0; 24.0 % against the written model). The CI half-width (8.7 points) is of the same order as in v1, so the headline is robust to the dispatch bug. Mechanics of the fix: 11.1 just-in-time dispatches and 0.1 reach-only refusals per run (0.1 bikes sent to swap by the dead-zone rule); travel falls from 107.7 to 101.4 km per run and unserved orders from 6.27 to 6.07, but the greedy policy is not monotone in its inputs: 5 instances get dearer because a nearer bike taken now is missing later. The gap stays dominated by the P_i = 100 penalty (90 % of the fixed-baseline-minus-ILP difference is unserved orders); the travel component of the gap is now 4.8 units (the ILP still travels less), i.e. the F1 bug explained part, not all, of the v1 travel difference. MIP-start acceptance: the fixed baseline is a feasible point of the written model in 11/15 runs and of the fully relaxed model in 15/15; the remaining rejections are the report-only end targets (17)/(18) (4 runs with a local shortfall, 1 with a global one) -- `baseline_reserve` is accepted in 14/15 runs under the written model and is the variant to use as a warm start when (17)/(18) are kept. The `ilp_fixed_arcs` / `ilp_fixed_assign` rows of v1 are tied to the *legacy* baseline's delivery arcs and are not re-used here; the dispatch-vs-logistics decomposition would need those two ILPs re-solved with the fixed baseline's arcs.

## Anomalies / checks

- v1 ILP rows not proven optimal (inherited): e2-K10-I45-seed2/ilp (TIME_LIMIT, gap 0.0198255608123331), e2-K10-I45-seed2/ilp_rho0 (TIME_LIMIT, gap 0.0212129977822775), e2-K10-I45-seed4/ilp (TIME_LIMIT, gap 0.0150838465850661), e2-K10-I45-seed4/ilp_rho0 (TIME_LIMIT, gap 0.0137531024162717)

## Figures

- `cost_components_v2.png`
- `improvement_vs_demand_v2.png`
- `gap_decomposition_rho0_v2.png`

Files: `results_v2.csv` (baseline variant rows + the unchanged v1 ILP rows, column `source`), `wall_time_v2.json`. v1 files (`RESULTS.md`, `results.csv`, figures without suffix) are untouched.
