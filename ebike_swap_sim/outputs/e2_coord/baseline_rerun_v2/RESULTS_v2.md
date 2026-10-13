# E2 v2 -- fixed baseline re-run (ILP rows unchanged)

Same 15 saved instances (`instances/*.json`, |K| = 10, |I| in {22, 30, 45}, H = 24, L = 12, 3 co-located sites B_j = 4, C_j = 3, 12 hourly shuttles, seeds 0-4), same arc library (pruning tau_max 4, start_slack 6, reachable = True; n_arcs equal to the old `results.csv` on every instance: True). The ILP rows (`ilp` rho = 0.5, `ilp_rho0` rho = 0 with R_end = 1 kept) are re-used from `results.csv` (objective, constraints and arc defaults untouched by the baseline fixes); only the baseline side is re-run. Baseline variants: `baseline` (fixed policy: JIT dispatch F1 + dead-zone rule F2), `baseline_legacy` (old behaviour; reproduces the old `baseline` rows exactly on every instance: True), `baseline_reserve` (F3: end-reserve window and late-threshold window W = max sigma_j + 3 = 4 slots), `baseline_informed` (F6: stock-aware site choice + late-threshold window), `baseline_reorder` (REORDER_POINT transfers on the shuttles). `gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline, plan definition); `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP (baseline excess over the optimum).

## Headline

**ILP (rho = 0.5) vs the fixed baseline: 24.0 % (95 % CI +/- 8.7, n = 15)** of the baseline cost is saved by coordination (was 28.0 % +/- 7.2 against the old baseline; against `baseline_reserve` 23.6 %; with the rho = 0 ILP 24.0 %). Mean baseline cost 1166.2 -> 1150.2 (reserve 1142.3) against the ILP mean 773.0; mean unserved 6.27 -> 6.07 (ILP 2.67); mean bike km 107.7 -> 101.4; the fixed baseline is at most as expensive as the old one on 10 of 15 instances (the JIT rule changes the greedy assignment, so single instances swing both ways).

MIP start of the fixed baseline: accepted by the written model on 11 / 15 instances (old baseline: 11 / 15), by the rho = 0 model on 11 / 15 and under the fully relaxed end targets (rho = 0, R_end = 0) on 15 / 15 (Gurobi fix-and-solve certificate; the free ILP was not re-solved). `baseline` MIP start accepted (Gurobi fix-and-solve, all variables fixed, Threads 4, TimeLimit 120 s): written model 11/15, rho = 0 only 11/15, fully relaxed end targets (rho = 0, R_end = 0) 15/15; certificate agrees with `evaluate.check` on every run: True.

## Per instance: new baseline vs old baseline vs ILP

| name | old_baseline | legacy_v2 | legacy==old | baseline_v2 | reserve | informed | reorder | ilp | ilp_status | ilp_rho0 | gap_v2_pct | gap_legacy_pct | gap_v2_rho0_pct | unserved_old/v2/ilp | km_old/v2 | jit | reach_ref | families_v2 | cert_written | cert_rho0 | cert_relaxed | cert_reserve_written | cert_reorder_written | old_start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e2-K10-I22-seed0 | 489.04 | 489.04 | True | 389.46 | 385.37 | 385.37 | 389.46 | 377.40 | OPTIMAL | 377.40 | 3.10 | 22.83 | 3.10 | 1/0/0 | 96.6/84.9 | 17 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I22-seed1 | 456.66 | 456.66 | True | 455.86 | 455.86 | 455.86 | 455.86 | 438.20 | OPTIMAL | 438.20 | 3.87 | 4.04 | 3.87 | 1/1/1 | 71.1/66.8 | 13 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I22-seed2 | 497.20 | 497.20 | True | 404 | 402.50 | 402.50 | 404 | 390.70 | OPTIMAL | 390.70 | 3.29 | 21.42 | 3.29 | 1/0/0 | 91.2/84.0 | 9 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I22-seed3 | 384.91 | 384.91 | True | 382.69 | 381.61 | 381.61 | 382.69 | 361.05 | OPTIMAL | 361.05 | 5.65 | 6.20 | 5.65 | 0/0/0 | 88.8/82.8 | 15 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I22-seed4 | 434.79 | 434.79 | True | 420.88 | 418.08 | 418.08 | 420.88 | 397.95 | OPTIMAL | 397.95 | 5.45 | 8.47 | 5.45 | 0/0/0 | 106.4/92.6 | 15 | 1 | {} | True | True | True | True | True | True |
| e2-K10-I30-seed0 | 968.86 | 968.86 | True | 872.92 | 869.58 | 869.58 | 872.92 | 485.05 | OPTIMAL | 485.05 | 44.43 | 49.94 | 44.43 | 5/4/0 | 117.8/104.2 | 16 | 0 | {} | True | True | True | True | True | False |
| e2-K10-I30-seed1 | 805.48 | 805.48 | True | 720.61 | 718.25 | 718.25 | 720.61 | 574 | OPTIMAL | 574 | 20.35 | 28.74 | 20.35 | 3/2/1 | 107.7/109.5 | 10 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I30-seed2 | 1073.48 | 1073.48 | True | 1062.81 | 1061.31 | 1061.31 | 1062.81 | 600.60 | OPTIMAL | 600.60 | 43.49 | 44.05 | 43.49 | 6/6/1 | 98.7/95.7 | 9 | 0 | {} | True | True | True | True | True | False |
| e2-K10-I30-seed3 | 593.18 | 593.18 | True | 683.49 | 680.49 | 680.49 | 683.49 | 484.60 | OPTIMAL | 484.60 | 29.10 | 18.31 | 29.10 | 0/1/0 | 119.8/111.6 | 10 | 0 | {"(17)": 1} | False | False | True | False | False | False |
| e2-K10-I30-seed4 | 779.42 | 779.42 | True | 592.99 | 586.18 | 586.18 | 592.99 | 529.70 | OPTIMAL | 529.70 | 10.67 | 32.04 | 10.67 | 2/0/0 | 123.8/116.5 | 12 | 0 | {"(17)": 1} | False | False | True | True | False | True |
| e2-K10-I45-seed0 | 2078.01 | 2078.01 | True | 2102.89 | 2102.89 | 2102.89 | 2102.89 | 1358.90 | OPTIMAL | 1358.90 | 35.38 | 34.61 | 35.38 | 14/14/7 | 120.5/123.4 | 9 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I45-seed1 | 2115.86 | 2115.86 | True | 2288.28 | 2200.70 | 2200.70 | 2288.28 | 1362.60 | OPTIMAL | 1362.60 | 40.45 | 35.60 | 40.45 | 14/16/7 | 114.8/113.0 | 8 | 0 | {} | True | True | True | True | True | True |
| e2-K10-I45-seed2 | 2270.37 | 2270.37 | True | 2212.63 | 2211.88 | 2211.88 | 2212.63 | 1553.55 | TIME_LIMIT | 1555.65 | 29.79 | 31.57 | 29.69 | 17/16/10 | 113.7/111.3 | 7 | 0 | {"(17)": 1} | False | False | True | True | False | True |
| e2-K10-I45-seed3 | 2119.44 | 2119.44 | True | 2190.16 | 2190.16 | 2190.16 | 2190.16 | 1184.90 | OPTIMAL | 1184.90 | 45.90 | 44.09 | 45.90 | 14/15/5 | 123.0/106.0 | 8 | 0 | {"(17)": 1, "(18)": 1} | False | False | True | True | False | False |
| e2-K10-I45-seed4 | 2425.69 | 2425.69 | True | 2472.61 | 2470.03 | 2470.03 | 2472.61 | 1496.45 | TIME_LIMIT | 1495 | 39.48 | 38.31 | 39.54 | 16/16/8 | 122.2/118.5 | 9 | 0 | {} | True | True | True | True | True | True |

`legacy_v2` = the fixed code run with `jit_dispatch = False, swap_on_reach_refusal = False` (must equal `old_baseline`); `unserved_old/v2/ilp` = unserved orders; `km_old/v2` = bike km (C_travel at kappa = 1); `jit` = just-in-time dispatches, `reach_ref` = reach-only refusals of the new rules; `cert_*` = Gurobi acceptance of the new baseline start (written model / (18) removed / (17)+(18) removed); `old_start_accepted` = acceptance of the old baseline in the original run.

## Headline gap per demand level: mean 100 (baseline - ILP) / baseline with 95 % t-CI over seeds

| comparison | demand_mult | n | gap_vs_baseline_mean_pct | ci95_pct | lo_pct | hi_pct | abs_gain_mean | gap_ex_setup_mean_pct | gap_ex_setup_ci95_pct | baseline_mean | ilp_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP (rho=0.5) vs baseline | 0.75 | 5 | 4.27 | 1.49 | 2.78 | 5.77 | 17.52 | 5.93 | 2.12 | 410.58 | 393.06 |
| ILP (rho=0.5) vs baseline | 1 | 5 | 29.61 | 18.17 | 11.44 | 47.78 | 251.77 | 34.43 | 20.00 | 786.56 | 534.79 |
| ILP (rho=0.5) vs baseline | 1.50 | 5 | 38.20 | 7.47 | 30.73 | 45.67 | 862.04 | 40.24 | 7.85 | 2253.32 | 1391.28 |
| ILP (rho=0.5) vs baseline | all | 15 | 24.03 | 8.68 | 15.35 | 32.71 | 377.11 | 26.87 | 9.15 | 1150.15 | 773.04 |
| ILP (rho=0) vs baseline | 0.75 | 5 | 4.27 | 1.49 | 2.78 | 5.77 | 17.52 | 5.93 | 2.12 | 410.58 | 393.06 |
| ILP (rho=0) vs baseline | 1 | 5 | 29.61 | 18.17 | 11.44 | 47.78 | 251.77 | 34.43 | 20.00 | 786.56 | 534.79 |
| ILP (rho=0) vs baseline | 1.50 | 5 | 38.19 | 7.51 | 30.68 | 45.70 | 861.91 | 40.23 | 7.89 | 2253.32 | 1391.41 |
| ILP (rho=0) vs baseline | all | 15 | 24.02 | 8.68 | 15.34 | 32.71 | 377.07 | 26.86 | 9.15 | 1150.15 | 773.09 |
| ILP (rho=0.5) vs baseline_legacy | 0.75 | 5 | 12.59 | 10.99 | 1.60 | 23.59 | 59.46 | 16.65 | 14.04 | 452.52 | 393.06 |
| ILP (rho=0.5) vs baseline_legacy | 1 | 5 | 34.61 | 15.59 | 19.02 | 50.21 | 309.29 | 39.91 | 16.55 | 844.08 | 534.79 |
| ILP (rho=0.5) vs baseline_legacy | 1.50 | 5 | 36.84 | 5.86 | 30.98 | 42.69 | 810.59 | 38.86 | 6.20 | 2201.87 | 1391.28 |
| ILP (rho=0.5) vs baseline_legacy | all | 15 | 28.01 | 7.19 | 20.82 | 35.21 | 393.12 | 31.80 | 7.47 | 1166.16 | 773.04 |
| ILP (rho=0.5) vs baseline_reserve | 0.75 | 5 | 3.82 | 1.68 | 2.14 | 5.49 | 15.62 | 5.30 | 2.36 | 408.68 | 393.06 |
| ILP (rho=0.5) vs baseline_reserve | 1 | 5 | 29.23 | 18.56 | 10.67 | 47.78 | 248.37 | 33.99 | 20.48 | 783.16 | 534.79 |
| ILP (rho=0.5) vs baseline_reserve | 1.50 | 5 | 37.71 | 7.31 | 30.40 | 45.02 | 843.85 | 39.74 | 7.69 | 2235.13 | 1391.28 |
| ILP (rho=0.5) vs baseline_reserve | all | 15 | 23.58 | 8.71 | 14.87 | 32.30 | 369.28 | 26.34 | 9.23 | 1142.33 | 773.04 |
| ILP (rho=0.5) vs baseline_informed | 0.75 | 5 | 3.82 | 1.68 | 2.14 | 5.49 | 15.62 | 5.30 | 2.36 | 408.68 | 393.06 |
| ILP (rho=0.5) vs baseline_informed | 1 | 5 | 29.23 | 18.56 | 10.67 | 47.78 | 248.37 | 33.99 | 20.48 | 783.16 | 534.79 |
| ILP (rho=0.5) vs baseline_informed | 1.50 | 5 | 37.71 | 7.31 | 30.40 | 45.02 | 843.85 | 39.74 | 7.69 | 2235.13 | 1391.28 |
| ILP (rho=0.5) vs baseline_informed | all | 15 | 23.58 | 8.71 | 14.87 | 32.30 | 369.28 | 26.34 | 9.23 | 1142.33 | 773.04 |
| ILP (rho=0.5) vs baseline_reorder | 0.75 | 5 | 4.27 | 1.49 | 2.78 | 5.77 | 17.52 | 5.93 | 2.12 | 410.58 | 393.06 |
| ILP (rho=0.5) vs baseline_reorder | 1 | 5 | 29.61 | 18.17 | 11.44 | 47.78 | 251.77 | 34.43 | 20.00 | 786.56 | 534.79 |
| ILP (rho=0.5) vs baseline_reorder | 1.50 | 5 | 38.20 | 7.47 | 30.73 | 45.67 | 862.04 | 40.24 | 7.85 | 2253.32 | 1391.28 |
| ILP (rho=0.5) vs baseline_reorder | all | 15 | 24.03 | 8.68 | 15.35 | 32.71 | 377.11 | 26.87 | 9.15 | 1150.15 | 773.04 |

## Cost (26) and components (27)-(32): seed means per demand level

| demand_mult | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb | n_unserved | n_swaps | bike_km | jit_dispatches | reach_refusals |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 | 0.20 | 3.60 | 82.20 | 13.80 | 0.20 |
| 0.75 | baseline_legacy | 452.52 | 114 | 2.31 | 90.81 | 60 | 175 | 10.40 | 0 | 0.60 | 4.40 | 90.81 | 0 | 1.20 |
| 0.75 | baseline_reserve | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 | 0.20 | 2.40 | 80.55 | 13.80 | 0.20 |
| 0.75 | baseline_informed | 408.68 | 114 | 1.73 | 80.55 | 20 | 181.60 | 10.80 | 0 | 0.20 | 2.40 | 80.55 | 13.80 | 0.20 |
| 0.75 | baseline_reorder | 410.58 | 114 | 1.98 | 82.20 | 20 | 181.60 | 10.80 | 0 | 0.20 | 3.60 | 82.20 | 13.80 | 0.20 |
| 0.75 | baseline_old (results.csv) | 452.52 | - | - | 90.81 | - | - | - | - | 0.60 | - | - | - | - |
| 0.75 | ilp (rho=0.5) | 393.06 | - | - | - | - | - | - | - | 0.20 | - | - | - | - |
| 0.75 | ilp_rho0 | 393.06 | - | - | - | - | - | - | - | - | - | - | - | - |
| 1 | baseline | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 | 2.60 | 5.80 | 107.52 | 11.40 | 0 |
| 1 | baseline_legacy | 844.08 | 114 | 3.33 | 113.55 | 320 | 244 | 49.20 | 0 | 3.20 | 5.80 | 113.55 | 0 | 0.20 |
| 1 | baseline_reserve | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 | 2.60 | 4.20 | 104.94 | 11.40 | 0.80 |
| 1 | baseline_informed | 783.16 | 114 | 2.82 | 104.94 | 260 | 253 | 48.40 | 0 | 2.60 | 4.20 | 104.94 | 11.40 | 0.80 |
| 1 | baseline_reorder | 786.56 | 114 | 3.04 | 107.52 | 260 | 253.20 | 48.80 | 0 | 2.60 | 5.80 | 107.52 | 11.40 | 0 |
| 1 | baseline_old (results.csv) | 844.08 | - | - | 113.55 | - | - | - | - | 3.20 | - | - | - | - |
| 1 | ilp (rho=0.5) | 534.79 | - | - | - | - | - | - | - | 0.40 | - | - | - | - |
| 1 | ilp_rho0 | 534.79 | - | - | - | - | - | - | - | - | - | - | - | - |
| 1.50 | baseline | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 | 15.40 | 5.20 | 114.45 | 8.20 | 0 |
| 1.50 | baseline_legacy | 2201.87 | 114 | 3.24 | 118.83 | 1500 | 325 | 140.80 | 0 | 15 | 5.40 | 118.83 | 0 | 0 |
| 1.50 | baseline_reserve | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 | 15.20 | 3.40 | 113.40 | 8.20 | 0.40 |
| 1.50 | baseline_informed | 2235.13 | 114 | 2.33 | 113.40 | 1520 | 333.80 | 151.60 | 0 | 15.20 | 3.60 | 113.40 | 8.20 | 0.40 |
| 1.50 | baseline_reorder | 2253.32 | 114 | 2.47 | 114.45 | 1540 | 331.60 | 150.80 | 0 | 15.40 | 5.20 | 114.45 | 8.20 | 0 |
| 1.50 | baseline_old (results.csv) | 2201.87 | - | - | 118.83 | - | - | - | - | 15 | - | - | - | - |
| 1.50 | ilp (rho=0.5) | 1391.28 | - | - | - | - | - | - | - | 7.40 | - | - | - | - |
| 1.50 | ilp_rho0 | 1391.41 | - | - | - | - | - | - | - | - | - | - | - | - |

## Gap decomposition baseline_v2 - ILP (rho = 0.5) by component

| demand_mult | baseline_total | ilp_total | gap_total | d_C_setup | d_C_elec | d_C_travel | d_unserved | d_response | d_lateness | d_C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct | gap_vs_baseline_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 410.58 | 393.06 | 17.52 | 0 | 1.98 | 11.34 | 0 | 4.20 | 0 | 0 | 0 | 23.98 | 0 | 64.73 | 11.29 | 4.27 |
| x1 | 786.56 | 534.79 | 251.77 | 0 | 3.04 | 8.13 | 220 | -1 | 21.60 | 0 | 87.38 | -0.40 | 8.58 | 3.23 | 1.21 | 32.01 |
| x1.5 | 2253.32 | 1391.28 | 862.04 | 0 | 2.47 | -4.23 | 800 | -15.80 | 79.60 | 0 | 92.80 | -1.83 | 9.23 | -0.49 | 0.29 | 38.26 |
| all | 1150.15 | 773.04 | 377.11 | 0 | 2.50 | 5.08 | 340 | -4.20 | 33.73 | 0 | 90.16 | -1.11 | 8.95 | 1.35 | 0.66 | 32.79 |

Same against the rho = 0 ILP:

| demand_mult | baseline_total | ilp_total | gap_total | d_C_setup | d_C_elec | d_C_travel | d_unserved | d_response | d_lateness | d_C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct | gap_vs_baseline_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 410.58 | 393.06 | 17.52 | 0 | 1.98 | 11.34 | 0 | 3.80 | 0.40 | 0 | 0 | 21.69 | 2.28 | 64.73 | 11.29 | 4.27 |
| x1 | 786.56 | 534.79 | 251.77 | 0 | 3.04 | 8.13 | 220 | -1 | 21.60 | 0 | 87.38 | -0.40 | 8.58 | 3.23 | 1.21 | 32.01 |
| x1.5 | 2253.32 | 1391.41 | 861.91 | 0 | 2.47 | -5.16 | 800 | -15.80 | 80.40 | 0 | 92.82 | -1.83 | 9.33 | -0.60 | 0.29 | 38.25 |
| all | 1150.15 | 773.09 | 377.07 | 0 | 2.50 | 4.77 | 340 | -4.33 | 34.13 | 0 | 90.17 | -1.15 | 9.05 | 1.27 | 0.66 | 32.78 |

Old behaviour (baseline_legacy) - ILP (rho = 0.5), for reference:

| demand_mult | baseline_total | ilp_total | gap_total | d_C_setup | d_C_elec | d_C_travel | d_unserved | d_response | d_lateness | d_C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct | gap_vs_baseline_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | 452.52 | 393.06 | 59.46 | 0 | 2.31 | 19.95 | 40 | -2.40 | -0.40 | 0 | 67.27 | -4.04 | -0.67 | 33.55 | 3.89 | 13.14 |
| x1 | 844.08 | 534.79 | 309.29 | 0 | 3.33 | 14.16 | 280 | -10.20 | 22 | 0 | 90.53 | -3.30 | 7.11 | 4.58 | 1.08 | 36.64 |
| x1.5 | 2201.87 | 1391.28 | 810.59 | 0 | 3.24 | 0.15 | 760 | -22.40 | 69.60 | 0 | 93.76 | -2.76 | 8.59 | 0.02 | 0.40 | 36.81 |
| all | 1166.16 | 773.04 | 393.12 | 0 | 2.96 | 11.42 | 360 | -11.67 | 30.40 | 0 | 91.58 | -2.97 | 7.73 | 2.90 | 0.75 | 33.71 |

## Figures

- `cost_components_v2.png`
- `improvement_vs_demand_v2.png`

## Anomalies

- none

## Interpretation

1. **Byte-identity holds.** The 15 saved instances give the old `n_arcs` on every instance and `baseline_legacy` reproduces the old `baseline` rows to 1e-6 everywhere; the ILP rows (`ilp`, `ilp_rho0`) are re-used unchanged, so the only moving part is the policy.
2. **Headline: the coordinator saves 24.0 % (95 % CI +/- 8.7, n = 15) of the fixed baseline's cost, against 28.0 % (+/- 7.2) of the old one.** By demand: x0.75 4.3 % (+/- 1.5; was 12.6 %), x1 29.6 % (+/- 18.2; was 34.6 %), x1.5 38.2 % (+/- 7.5; was 36.8 %). With the rho = 0 ILP the numbers are the same to 0.1 point. The mean baseline cost moves 1166.2 -> 1150.2 (-1.4 %), unserved 6.27 -> 6.07, bike km 107.7 -> 101.4 (-5.9 %), swaps 5.2 -> 4.9; the fixed baseline is cheaper on 10 of 15 instances, and the swings are large in both directions (I30-seed4 779.4 -> 593.0, I30-seed0 968.9 -> 872.9, I22-seed0 489.0 -> 389.5; but I30-seed3 593.2 -> 683.5 and I45-seed1 2115.9 -> 2288.3). The gain concentrates at low demand (x0.75: 452.5 -> 410.6, the JIT rule picks the nearer idle bike for 9-17 orders per run and the old policy's one unserved order disappears on 2 of the 3 seeds that had one), while at x1.5 the fixed baseline is slightly worse (2201.9 -> 2253.3, 15.4 vs 15.0 unserved): when every bike is busy, committing the nearest bike early to an order whose food is not ready loses more than the shorter first leg gains (see the E4 ablation).
3. **Variants.** `baseline_reserve` and `baseline_informed` coincide (1142.3; the end-reserve window never binds and the stock-aware site choice never reroutes a bike; the only active ingredient is the late-threshold window, 5.3 suppressed late swap trips per run, which saves 7.8 on average and makes the start acceptable to the written model on 14 / 15 instances instead of 11 / 15). `baseline_reorder` equals `baseline` on every instance: the REORDER_POINT rule never ships a battery on these instances (site stock of 4 full spares is never at or below s_j = 1 at a shuttle departure), so transfers do not exist in the E2 baselines even when enabled; the E2 shuttles matter only to the ILP, which also does not use them (0 transfers in every ILP row).
4. **MIP start.** The fixed baseline start is accepted by the written model on 11 / 15 instances (the same count as the old baseline, but a different set: I30-seed0 and I30-seed2 are newly accepted, I30-seed4 and I45-seed2 newly rejected; the four rejections I30-seed3 / I30-seed4 / I45-seed2 / I45-seed3 are all by (17), one site ending without its R_end = 1 full spare, plus (18) on I45-seed3); removing (18) alone does not help (11 / 15), and under the fully relaxed end targets (rho = 0, R_end = 0) all 15 starts are accepted (Gurobi fix-and-solve, 4 s build + 3.5 s solve per instance, objective equal to `evaluate.cost`). The old `ilp_rho0` rows kept R_end = 1, which is why the rho = 0 comparison was never fully "fair"; a rho = 0 and R_end = 0 ILP was not solved (out of scope: no free ILP re-solve).
5. **Gap decomposition is unchanged in character**: of the 377 units mean gap, 340 are unserved orders (3.4 more orders served by the ILP at P_i = 100), lateness +33.7, travel +5.1, electricity +2.5, response -4.2 (the baseline serves fewer orders); at x0.75 the gap (17.5) is travel (11.3) and response, at x1 / x1.5 it is 87 / 93 % unserved orders. The ILP side of E2 (two TIME_LIMIT solves at x1.5 with gap <= 1 %) is as before.

