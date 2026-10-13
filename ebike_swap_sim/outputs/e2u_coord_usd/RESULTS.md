# E2u -- coordination value under USD costs, 4 h window (`usd4h`, round 2)

## Summary
This experiment compares the event-driven baseline policy with the E2 integer program on the round-2 `usd4h` family (6 bikes, 48 slots of 5 min, 3 co-located sites, B = 3, C = 2, USD costs `usd_sunk`) over 5 random seeds x 3 demand levels (x0.75 / x1 / x1.5, i.e. 27 / 36 / 54 orders).
The overall headline gap ((baseline - ILP) / baseline) is 21.9 % (+/- 7.4, n = 15); by demand level it is x0.75 6.9 % (+/- 4.9, n = 5), x1 21.3 % (+/- 11.3, n = 5), x1.5 37.3 % (+/- 10.8, n = 5); the ILP with relaxed end targets (rho = 0, R_end = 0) gives 19.0 % (+/- 7.3, n = 15), and the comparison against the round-1 rule baseline gives 23.4 % (+/- 7.0, n = 15).
The gap comes mainly from the unserved-order penalty (20 % share) and the response-time cost (25 %); the travel-cost share is 0 %, and the electricity and end-of-horizon inventory terms are negligible.
The 24 % of round 1 was obtained in toy units (P = 100, w = 12) with 10 bikes / a 2-hour window and the old baseline rules; under this round's USD pricing, P = 30 and w = 18 lower the relative weight of a single unserved order, and the R2.3 baseline (stock-aware site choice and demand-aware charging) is itself stronger; together these change the headline.
The cost-variant comparison (seeds 0-1) gives the drop rates of the ILP and the baseline under each variant: under `usd_A` (w = 40, where the response cost approaches P = 30) the ILP drop rate is clearly higher than under `usd_sunk`, while in toy units almost nothing is dropped, which shows that the R2.1 choice of `usd_sunk` as the default is necessary.

## Setup
Family `usd4h` (DECISIONS R2.2; sizes fixed in 'R2 implementation notes'): 6 bikes, H = 48 x 5 min (17:00-21:00), L = 12, 3 co-located fixed sites (B = 3, C = 2, K = 8, M = 1, sigma = 1, P_j = 4 kW), no transfer services (the family has |E| = 0, so C_reb = 0 and transfers = 0 by construction), Kaggle order attributes, q0 ~ U{4..7}. Demand x0.75 / x1 / x1.5 = 1.125 / 1.5 / 2.25 orders per bike-hour -> 27 / 36 / 54 orders; seeds [0, 1, 2, 3, 4]; 15 headline instances (saved as `instances/*.json`). Costs: `usd_sunk` (R2.1 default: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h) for the headline; `usd_A` (kappa 0.50, w 40, v 80) and `toy` (E2 p.14 units) re-price the identical instances of seeds [0, 1] (geometry asserted equal).
Arc library: plan pruning + lossless reachable pruning (`pruning_for(inst, reachable=True)`; 0.99 M / 1.15 M / 1.51 M arcs at the three demand levels). Methods: `baseline` = R2.3 rules (stock-aware site, DEMAND_AWARE charging, JIT dispatch, dead-zone rule), `baseline_round1` = round-1 rules after the reviewer fixes (nearest site, ASAP HIGH_FIRST), `ilp` = written model (rho = 0.5, R_end_j = 1), `ilp_relaxed` = `common.relax_end_targets` (rho = 0, R_end_j = 0), `ilp_lex` = lexicographic (min sum u_i, then (26)). Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 150 s per solve (100 s per lexicographic stage), MIP start = first clean policy schedule (`feasible_mip_start`). Gap = 100 (policy - ILP) / policy, mean over seeds with a 95 % t-CI. Total wall of the recorded phases: 112 min (two 3-thread processes, headline and variants, ran concurrently).

## Headline
**ILP (written model) vs the R2.3 baseline: 21.9 % (+/- 7.4, n = 15)** -- by demand x0.75 6.9 % (+/- 4.9, n = 5), x1 21.3 % (+/- 11.3, n = 5), x1.5 37.3 % (+/- 10.8, n = 5). Relaxed control (rho = 0, R_end = 0): 19.0 % (+/- 7.3, n = 15). Lexicographic: 14.9 % (+/- 7.3, n = 15). Against the round-1 rules baseline: 23.4 % (+/- 7.0, n = 15) (x0.75 10.4 % (+/- 4.0, n = 5), x1 22.5 % (+/- 13.4, n = 5), x1.5 37.3 % (+/- 10.8, n = 5)). Mean totals: baseline 1022.3 USD, ILP 726.5 USD per instance; excluding the constant setup term (27) the operating gap is 22.7 % (+/- 7.5). Round 1 (toy units, 10 bikes, H 24, baseline v2 = today's round-1 rules): 24.0 % (+/- 8.7).

## Gap per comparison and demand level (mean over seeds, 95 % t-CI)
| comparison | cost_variant | demand_mult | n | gap_mean_pct | gap_ci95_pct | gap_lo_pct | gap_hi_pct | abs_gain_mean | gap_ex_setup_mean_pct | gap_vs_ilp_mean_pct | policy_total_mean | ilp_total_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ILP written vs baseline R2.3 [headline] | usd_sunk | 0.75 | 5 | 6.91 | 4.87 | 2.04 | 11.78 | 35.88 | 7.48 | 7.58 | 502.74 | 466.86 |
| ILP written vs baseline R2.3 [headline] | usd_sunk | 1 | 5 | 21.33 | 11.31 | 10.02 | 32.64 | 184.63 | 22.37 | 28.51 | 822.90 | 638.27 |
| ILP written vs baseline R2.3 [headline] | usd_sunk | 1.50 | 5 | 37.35 | 10.79 | 26.55 | 48.14 | 667.04 | 38.21 | 61.78 | 1741.29 | 1074.26 |
| ILP written vs baseline R2.3 [headline] | usd_sunk | all | 15 | 21.86 | 7.43 | 14.44 | 29.29 | 295.85 | 22.69 | 32.62 | 1022.31 | 726.46 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | usd_sunk | 0.75 | 5 | 6.94 | 4.87 | 2.06 | 11.81 | 36.02 | 7.51 | 7.61 | 502.74 | 466.72 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | usd_sunk | 1 | 5 | 21.38 | 11.29 | 10.09 | 32.67 | 185.02 | 22.42 | 28.59 | 822.90 | 637.88 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | usd_sunk | 1.50 | 5 | 28.62 | 22.16 | 6.46 | 50.78 | 492.57 | 29.30 | 46.28 | 1741.29 | 1248.72 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 | usd_sunk | all | 15 | 18.98 | 7.27 | 11.71 | 26.24 | 237.87 | 19.75 | 27.49 | 1022.31 | 784.44 |
| ILP lexicographic vs baseline R2.3 | usd_sunk | 0.75 | 5 | 6.71 | 4.66 | 2.06 | 11.37 | 34.81 | 7.27 | 7.34 | 502.74 | 467.93 |
| ILP lexicographic vs baseline R2.3 | usd_sunk | 1 | 5 | 17.13 | 15.46 | 1.67 | 32.59 | 151.88 | 17.95 | 22.86 | 822.90 | 671.03 |
| ILP lexicographic vs baseline R2.3 | usd_sunk | 1.50 | 5 | 20.88 | 25.55 | -4.67 | 46.43 | 365.39 | 21.37 | 33.66 | 1741.29 | 1375.90 |
| ILP lexicographic vs baseline R2.3 | usd_sunk | all | 15 | 14.91 | 7.29 | 7.61 | 22.20 | 184.03 | 15.53 | 21.28 | 1022.31 | 838.29 |
| ILP written vs baseline round-1 rules | usd_sunk | 0.75 | 5 | 10.36 | 4.02 | 6.34 | 14.39 | 54.41 | 11.21 | 11.68 | 521.27 | 466.86 |
| ILP written vs baseline round-1 rules | usd_sunk | 1 | 5 | 22.51 | 13.44 | 9.07 | 35.96 | 202.40 | 23.58 | 31.21 | 840.67 | 638.27 |
| ILP written vs baseline round-1 rules | usd_sunk | 1.50 | 5 | 37.35 | 10.82 | 26.53 | 48.17 | 667.19 | 38.21 | 61.79 | 1741.45 | 1074.26 |
| ILP written vs baseline round-1 rules | usd_sunk | all | 15 | 23.41 | 6.95 | 16.46 | 30.36 | 308.00 | 24.33 | 34.89 | 1034.46 | 726.46 |
| ILP relaxed vs baseline round-1 rules | usd_sunk | 0.75 | 5 | 10.39 | 4.02 | 6.37 | 14.41 | 54.55 | 11.24 | 11.71 | 521.27 | 466.72 |
| ILP relaxed vs baseline round-1 rules | usd_sunk | 1 | 5 | 22.56 | 13.42 | 9.15 | 35.98 | 202.79 | 23.63 | 31.29 | 840.67 | 637.88 |
| ILP relaxed vs baseline round-1 rules | usd_sunk | 1.50 | 5 | 28.62 | 22.16 | 6.46 | 50.79 | 492.73 | 29.31 | 46.29 | 1741.45 | 1248.72 |
| ILP relaxed vs baseline round-1 rules | usd_sunk | all | 15 | 20.53 | 6.96 | 13.57 | 27.48 | 250.02 | 21.39 | 29.76 | 1034.46 | 784.44 |
| baseline R2.3 vs baseline round-1 rules | usd_sunk | 0.75 | 5 | 3.59 | 6.09 | -2.50 | 9.68 | 18.52 | 3.89 | 3.94 | 521.27 | 502.74 |
| baseline R2.3 vs baseline round-1 rules | usd_sunk | 1 | 5 | 1.73 | 3.88 | -2.16 | 5.61 | 17.77 | 1.80 | 1.84 | 840.67 | 822.90 |
| baseline R2.3 vs baseline round-1 rules | usd_sunk | 1.50 | 5 | 0.01 | 0.04 | -0.04 | 0.05 | 0.16 | 0.01 | 0.01 | 1741.45 | 1741.29 |
| baseline R2.3 vs baseline round-1 rules | usd_sunk | all | 15 | 1.77 | 1.75 | 0.02 | 3.53 | 12.15 | 1.90 | 1.93 | 1034.46 | 1022.31 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | 0.75 | 2 | 17.78 | 53.40 | -35.62 | 71.18 | 184.58 | 18.49 | 21.94 | 1022.49 | 837.91 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | 1 | 2 | 35.44 | 70.18 | -34.75 | 105.62 | 620.18 | 36.26 | 56.03 | 1725.57 | 1105.38 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | 1.50 | 2 | 50.45 | 56.44 | -5.99 | 106.89 | 1693.90 | 51.06 | 103.46 | 3328.87 | 1634.97 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | all | 6 | 34.56 | 16.30 | 18.26 | 50.86 | 832.89 | 35.27 | 60.48 | 2025.64 | 1192.75 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 0.75 | 2 | 22.45 | 5.47 | 16.98 | 27.92 | 242.52 | 23.30 | 28.95 | 1080.43 | 837.91 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 1 | 2 | 37.36 | 94.38 | -57.02 | 131.73 | 685.49 | 38.19 | 61.91 | 1790.88 | 1105.38 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 1.50 | 2 | 50.46 | 56.41 | -5.95 | 106.87 | 1694.23 | 51.07 | 103.49 | 3329.21 | 1634.97 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | all | 6 | 36.75 | 14.36 | 22.40 | 51.11 | 874.08 | 37.52 | 64.78 | 2066.84 | 1192.75 |
| ILP written vs baseline R2.3 (toy) | toy | 0.75 | 2 | 16.79 | 157.54 | -140.75 | 174.33 | 109.67 | 19.82 | 22.91 | 603.37 | 493.70 |
| ILP written vs baseline R2.3 (toy) | toy | 1 | 2 | 1.18 | 130.48 | -129.29 | 131.66 | -20.33 | 1.71 | 2.30 | 1067.69 | 1088.02 |
| ILP written vs baseline R2.3 (toy) | toy | 1.50 | 2 | 2.22 | 27.58 | -25.36 | 29.80 | 58.80 | 2.30 | 2.32 | 2927.88 | 2869.08 |
| ILP written vs baseline R2.3 (toy) | toy | all | 6 | 6.73 | 13.54 | -6.81 | 20.27 | 49.38 | 7.94 | 9.18 | 1532.98 | 1483.60 |
| ILP written vs baseline round-1 rules (toy units) | toy | 0.75 | 2 | 19.80 | 123.72 | -103.92 | 143.53 | 128.25 | 23.41 | 26.56 | 621.94 | 493.70 |
| ILP written vs baseline round-1 rules (toy units) | toy | 1 | 2 | 5.84 | 74.16 | -68.33 | 80.00 | 43.71 | 6.73 | 6.61 | 1131.73 | 1088.02 |
| ILP written vs baseline round-1 rules (toy units) | toy | 1.50 | 2 | 2.29 | 27.89 | -25.60 | 30.18 | 60.91 | 2.38 | 2.40 | 2929.99 | 2869.08 |
| ILP written vs baseline round-1 rules (toy units) | toy | all | 6 | 9.31 | 11.60 | -2.29 | 20.91 | 77.62 | 10.84 | 11.85 | 1561.22 | 1483.60 |
| ILP written vs baseline round-1 rules (usd_sunk, variant seeds) | usd_sunk | 0.75 | 2 | 12.87 | 7.94 | 4.94 | 20.81 | 67.51 | 13.92 | 14.78 | 524.97 | 457.46 |
| ILP written vs baseline round-1 rules (usd_sunk, variant seeds) | usd_sunk | 1 | 2 | 26.61 | 133.67 | -107.06 | 160.29 | 253.84 | 27.80 | 39.13 | 891.32 | 637.48 |
| ILP written vs baseline round-1 rules (usd_sunk, variant seeds) | usd_sunk | 1.50 | 2 | 41.18 | 32.70 | 8.48 | 73.88 | 754.34 | 42.10 | 70.33 | 1820.77 | 1066.43 |
| ILP written vs baseline round-1 rules (usd_sunk, variant seeds) | usd_sunk | all | 6 | 26.89 | 15.11 | 11.77 | 42.00 | 358.56 | 27.94 | 41.41 | 1079.02 | 720.46 |
| ILP written vs baseline R2.3 (usd_sunk, variant seeds) | usd_sunk | 0.75 | 2 | 7.91 | 54.06 | -46.15 | 61.97 | 41.02 | 8.56 | 8.82 | 498.48 | 457.46 |
| ILP written vs baseline R2.3 (usd_sunk, variant seeds) | usd_sunk | 1 | 2 | 24.14 | 102.71 | -78.56 | 126.85 | 215.69 | 25.28 | 33.34 | 853.17 | 637.48 |
| ILP written vs baseline R2.3 (usd_sunk, variant seeds) | usd_sunk | 1.50 | 2 | 41.17 | 32.76 | 8.41 | 73.92 | 754.00 | 42.08 | 70.30 | 1820.43 | 1066.43 |
| ILP written vs baseline R2.3 (usd_sunk, variant seeds) | usd_sunk | all | 6 | 24.41 | 16.84 | 7.57 | 41.24 | 336.90 | 25.31 | 37.49 | 1057.36 | 720.46 |

`gap_mean_pct` = 100 (policy - ILP) / policy (headline convention); `gap_vs_ilp_mean_pct` = 100 (policy - ILP) / ILP; `gap_ex_setup` divides by the policy cost minus C_setup (27). ILP totals are incumbents: at a TIME_LIMIT status they are upper bounds on the optimum, so the gap is a lower bound.

## Gap decomposition (policy - ILP per component, USD per instance, and share of the total gap)
### headline: baseline vs ilp (usd_sunk)
| demand_mult | n | total_gap | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8 | 5 | 35.9 | 0 | 0.6 | 1.1 | 6 | 10.8 | 17.4 | 0 | 16.7 | 30.1 | 48.5 | 3.0 | 1.7 |
| 1 | 5 | 184.6 | 0 | 0.5 | 1.2 | 48 | 42.6 | 92.4 | 0 | 26.0 | 23.1 | 50.0 | 0.6 | 0.3 |
| 1.5 | 5 | 667.0 | 0 | 0.3 | 2.0 | 126 | 166.2 | 372.6 | 0 | 18.9 | 24.9 | 55.9 | 0.3 | 0.0 |
| all | 15 | 295.9 | 0 | 0.4 | 1.4 | 60 | 73.2 | 160.8 | 0 | 20.3 | 24.7 | 54.4 | 0.5 | 0.2 |

### relaxed: baseline vs ilp_relaxed (usd_sunk)
| demand_mult | n | total_gap | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8 | 5 | 36.0 | 0 | 0.7 | 1.1 | 6 | 10.8 | 17.4 | 0 | 16.7 | 30.0 | 48.3 | 3.0 | 2.1 |
| 1 | 5 | 185.0 | 0 | 0.8 | 1.2 | 48 | 42.6 | 92.4 | 0 | 25.9 | 23.0 | 49.9 | 0.7 | 0.4 |
| 1.5 | 5 | 492.6 | 0 | 0.6 | 1.5 | 102 | 120.3 | 268.2 | 0 | 20.7 | 24.4 | 54.4 | 0.3 | 0.1 |
| all | 15 | 237.9 | 0 | 0.7 | 1.3 | 52 | 57.9 | 126 | 0 | 21.9 | 24.3 | 53.0 | 0.5 | 0.3 |

### round1 rules: baseline_round1 vs ilp (usd_sunk)
| demand_mult | n | total_gap | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb | unserved_share_pct | response_share_pct | lateness_share_pct | C_travel_share_pct | C_elec_share_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8 | 5 | 54.4 | 0 | 1.0 | 0.9 | 6 | 18.9 | 27.6 | 0 | 11.0 | 34.7 | 50.7 | 1.7 | 1.8 |
| 1 | 5 | 202.4 | 0 | 0.8 | 0.9 | 48 | 48.3 | 104.4 | 0 | 23.7 | 23.9 | 51.6 | 0.5 | 0.4 |
| 1.5 | 5 | 667.2 | 0 | 0.6 | 1.8 | 138 | 157.8 | 369 | 0 | 20.7 | 23.7 | 55.3 | 0.3 | 0.1 |
| all | 15 | 308.0 | 0 | 0.8 | 1.2 | 64 | 75 | 167 | 0 | 20.8 | 24.4 | 54.2 | 0.4 | 0.3 |

## Cost (26) and components (27)-(32): mean over seeds per demand level and method (usd_sunk)
| demand_mult | method | n | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.75 | baseline | 5 | 502.74 | 39.57 | 0.74 | 10.63 | 42 | 390 | 19.80 | 0 |
| 0.75 | baseline_round1 | 5 | 521.27 | 39.57 | 1.10 | 10.49 | 42 | 398.10 | 30 | 0 |
| 0.75 | ilp | 5 | 466.86 | 39.57 | 0.12 | 9.57 | 36 | 379.20 | 2.40 | 0 |
| 0.75 | ilp_relaxed | 5 | 466.72 | 39.57 | 0.00 | 9.55 | 36 | 379.20 | 2.40 | 0 |
| 0.75 | ilp_lex | 5 | 467.93 | 39.57 | 0.13 | 9.73 | 30 | 384.30 | 4.20 | 0 |
| 1 | baseline | 5 | 822.90 | 39.57 | 0.83 | 12.70 | 156 | 518.40 | 95.40 | 0 |
| 1 | baseline_round1 | 5 | 840.67 | 39.57 | 1.14 | 12.46 | 156 | 524.10 | 107.40 | 0 |
| 1 | ilp | 5 | 638.27 | 39.57 | 0.37 | 11.53 | 108 | 475.80 | 3 | 0 |
| 1 | ilp_relaxed | 5 | 637.88 | 39.57 | 0.02 | 11.48 | 108 | 475.80 | 3 | 0 |
| 1 | ilp_lex | 5 | 671.03 | 39.57 | 0.42 | 11.84 | 96 | 499.80 | 23.40 | 0 |
| 1.50 | baseline | 5 | 1741.29 | 39.57 | 0.86 | 14.86 | 576 | 736.80 | 373.20 | 0 |
| 1.50 | baseline_round1 | 5 | 1741.45 | 39.57 | 1.24 | 14.64 | 588 | 728.40 | 369.60 | 0 |
| 1.50 | ilp | 5 | 1074.26 | 39.57 | 0.60 | 12.88 | 450 | 570.60 | 0.60 | 0 |
| 1.50 | ilp_relaxed | 5 | 1248.72 | 39.57 | 0.30 | 13.35 | 474 | 616.50 | 105 | 0 |
| 1.50 | ilp_lex | 5 | 1375.90 | 39.57 | 0.79 | 13.75 | 510 | 641.40 | 170.40 | 0 |

## Service, response, lateness, distance, swaps, energy, transfers (mean over seeds, usd_sunk)
| demand_mult | method | served_share | n_unserved | mean_response_h | mean_lateness_h | n_late | bike_km | n_swaps | kwh_purchased | peak_kw_group | transfers_used | stockout_slots | end_full_total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.750 | baseline | 0.948 | 1.400 | 0.847 | 0.022 | 3.600 | 88.590 | 6.200 | 2.322 | 2.533 | 0 | 5.200 | 6.200 |
| 0.750 | baseline_round1 | 0.948 | 1.400 | 0.864 | 0.033 | 5 | 87.450 | 6.400 | 3.444 | 2.267 | 0 | 7.800 | 8.400 |
| 0.750 | ilp | 0.956 | 1.200 | 0.817 | 0.003 | 0.600 | 79.740 | 5 | 0.378 | 0.667 | 0 | 4 | 5 |
| 0.750 | ilp_relaxed | 0.956 | 1.200 | 0.817 | 0.003 | 0.600 | 79.560 | 6.600 | 0.011 | 0.133 | 0 | 20.600 | 2.400 |
| 0.750 | ilp_lex | 0.963 | 1 | 0.821 | 0.005 | 1.200 | 81.090 | 5 | 0.411 | 0.533 | 0 | 0 | 5 |
| 1 | baseline | 0.856 | 5.200 | 0.939 | 0.089 | 10.800 | 105.870 | 7.200 | 2.589 | 2.133 | 0 | 8.200 | 5.400 |
| 1 | baseline_round1 | 0.856 | 5.200 | 0.950 | 0.101 | 11 | 103.800 | 7 | 3.578 | 2.133 | 0 | 6 | 7.800 |
| 1 | ilp | 0.900 | 3.600 | 0.816 | 0.002 | 1 | 96.120 | 7 | 1.144 | 1.733 | 0 | 25.400 | 5 |
| 1 | ilp_relaxed | 0.900 | 3.600 | 0.816 | 0.002 | 1 | 95.700 | 7.400 | 0.078 | 0.133 | 0 | 40 | 1.800 |
| 1 | ilp_lex | 0.911 | 3.200 | 0.845 | 0.019 | 4.600 | 98.670 | 6.400 | 1.300 | 1.600 | 0 | 16.800 | 5.200 |
| 1.500 | baseline | 0.644 | 19.200 | 1.181 | 0.302 | 23 | 123.810 | 8.200 | 2.700 | 2.533 | 0 | 7.400 | 4.600 |
| 1.500 | baseline_round1 | 0.637 | 19.600 | 1.178 | 0.300 | 22.800 | 121.980 | 8.400 | 3.878 | 2.800 | 0 | 5.800 | 6.800 |
| 1.500 | ilp | 0.722 | 15 | 0.813 | 0.000 | 0.200 | 107.340 | 8 | 1.889 | 1.467 | 0 | 26.800 | 5 |
| 1.500 | ilp_relaxed | 0.707 | 15.800 | 0.911 | 0.088 | 5.200 | 111.240 | 8.400 | 0.944 | 1.067 | 0 | 30.200 | 2.400 |
| 1.500 | ilp_lex | 0.685 | 17 | 0.975 | 0.137 | 10.200 | 114.570 | 8.200 | 2.456 | 2 | 0 | 24.200 | 5.400 |

`end_full_total` = full batteries in stock at H (sum over sites; (18) requires >= rho sum B = 4.5 -> 5); `stockout_slots` = slots with no full battery at a swap site; `peak_kw_group` = max grid-group load.

## Drop rate by cost variant (share of orders unserved, mean over the seeds run)
| cost_variant | method | 0.75 | 1.0 | 1.5 |
|---|---|---|---|---|
| toy | baseline | 5.6 | 11.1 | 35.2 |
| toy | baseline_round1 | 5.6 | 12.5 | 35.2 |
| toy | ilp | 1.9 | 12.5 | 35.2 |
| usd_A | baseline | 5.6 | 11.1 | 35.2 |
| usd_A | baseline_round1 | 5.6 | 12.5 | 35.2 |
| usd_A | ilp | 85.2 | 86.1 | 83.3 |
| usd_sunk | baseline | 5.2 | 14.4 | 35.6 |
| usd_sunk | baseline_round1 | 5.2 | 14.4 | 36.3 |
| usd_sunk | ilp | 4.4 | 10 | 27.8 |

Coefficients per variant (USD; toy in E2 p.14 units):
| cost_variant | coef_kappa | coef_pi | coef_P | coef_w | coef_v | coef_F | coef_bB | coef_bC |
|---|---|---|---|---|---|---|---|---|
| toy | 1 | 2 | 100 | 12 | 24 | 20 | 3 | 2 |
| usd_A | 0.500 | 0.320 | 30 | 40 | 80 | 12.030 | 0.332 | 0.082 |
| usd_sunk | 0.120 | 0.320 | 30 | 18 | 36 | 12.030 | 0.332 | 0.082 |

Gap of the written ILP over both baselines under each extra variant (same seeds as the variant run):
| comparison | cost_variant | demand_mult | n | gap_mean_pct | gap_ci95_pct | policy_total_mean | ilp_total_mean |
|---|---|---|---|---|---|---|---|
| ILP written vs baseline R2.3 (usd_A) | usd_A | 0.75 | 2 | 17.78 | 53.40 | 1022.49 | 837.91 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | 1 | 2 | 35.44 | 70.18 | 1725.57 | 1105.38 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | 1.50 | 2 | 50.45 | 56.44 | 3328.87 | 1634.97 |
| ILP written vs baseline R2.3 (usd_A) | usd_A | all | 6 | 34.56 | 16.30 | 2025.64 | 1192.75 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 0.75 | 2 | 22.45 | 5.47 | 1080.43 | 837.91 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 1 | 2 | 37.36 | 94.38 | 1790.88 | 1105.38 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | 1.50 | 2 | 50.46 | 56.41 | 3329.21 | 1634.97 |
| ILP written vs baseline round-1 rules (usd_A) | usd_A | all | 6 | 36.75 | 14.36 | 2066.84 | 1192.75 |
| ILP written vs baseline R2.3 (toy) | toy | 0.75 | 2 | 16.79 | 157.54 | 603.37 | 493.70 |
| ILP written vs baseline R2.3 (toy) | toy | 1 | 2 | 1.18 | 130.48 | 1067.69 | 1088.02 |
| ILP written vs baseline R2.3 (toy) | toy | 1.50 | 2 | 2.22 | 27.58 | 2927.88 | 2869.08 |
| ILP written vs baseline R2.3 (toy) | toy | all | 6 | 6.73 | 13.54 | 1532.98 | 1483.60 |
| ILP written vs baseline round-1 rules (toy units) | toy | 0.75 | 2 | 19.80 | 123.72 | 621.94 | 493.70 |
| ILP written vs baseline round-1 rules (toy units) | toy | 1 | 2 | 5.84 | 74.16 | 1131.73 | 1088.02 |
| ILP written vs baseline round-1 rules (toy units) | toy | 1.50 | 2 | 2.29 | 27.89 | 2929.99 | 2869.08 |
| ILP written vs baseline round-1 rules (toy units) | toy | all | 6 | 9.31 | 11.60 | 1561.22 | 1483.60 |

## Lexicographic (service-first) vs the written model, usd_sunk
| name | U_star | lex_certified | ilp_unserved | lex_total | ilp_total | service_premium_pct |
|---|---|---|---|---|---|---|
| usd4h-K6-I27-seed0-x0.75 | 1 | True | 1 | 443.90 | 443.90 | 0 |
| usd4h-K6-I27-seed1-x0.75 | 2 | False | 1 | 471.02 | 471.02 | 0 |
| usd4h-K6-I27-seed2-x0.75 | 1 | False | 0 | 462.85 | 462.87 | -0.00 |
| usd4h-K6-I27-seed3-x0.75 | 2 | True | 3 | 502.70 | 497.32 | 1.08 |
| usd4h-K6-I27-seed4-x0.75 | 1 | True | 1 | 459.18 | 459.18 | 0 |
| usd4h-K6-I36-seed0-x1 | 1 | True | 1 | 733.10 | 615.36 | 19.13 |
| usd4h-K6-I36-seed1-x1 | 8 | False | 5 | 659.60 | 659.60 | 0 |
| usd4h-K6-I36-seed2-x1 | 7 | False | 4 | 638.98 | 638.98 | 0 |
| usd4h-K6-I36-seed3-x1 | 3 | True | 5 | 708.67 | 662.63 | 6.95 |
| usd4h-K6-I36-seed4-x1 | 3 | False | 3 | 614.78 | 614.78 | 0 |
| usd4h-K6-I54-seed0-x1.5 | 17 | False | 11 | 1642.66 | 1008.52 | 62.88 |
| usd4h-K6-I54-seed1-x1.5 | 21 | False | 17 | 1998.44 | 1124.33 | 77.74 |
| usd4h-K6-I54-seed2-x1.5 | 20 | False | 15 | 1061.64 | 1061.64 | 0 |
| usd4h-K6-I54-seed3-x1.5 | 20 | False | 17 | 1114.70 | 1114.70 | 0 |
| usd4h-K6-I54-seed4-x1.5 | 20 | False | 15 | 1062.08 | 1062.08 | 0 |

`U_star` = min sum u_i of stage 1 (`lex_certified` = stage 1 proved optimal); `service_premium_pct` = extra cost of serving U* orders instead of the cost-optimal number, relative to the written optimum.

## Solver statistics (per cost variant, method, demand level)
| cost_variant | method | demand_mult | n | optimal | time_limit | gap_mean | gap_max | runtime_mean | runtime_max | build_mean | binaries_mean | rows_mean | start_accepted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| toy | ilp | 0.750 | 2 | 2 | 0 | 0 | 0 | 80.798 | 93.852 | 4.760 | 960286 | 59518.500 | 2 |
| toy | ilp | 1 | 2 | 1 | 1 | 0.236 | 0.473 | 127.814 | 150.112 | 4.805 | 1130585.500 | 62693 | 2 |
| toy | ilp | 1.500 | 2 | 0 | 2 | 0.363 | 0.371 | 150.096 | 150.123 | 8.377 | 1488540 | 68280 | 2 |
| usd_A | ilp | 0.750 | 2 | 2 | 0 | 0 | 0 | 25.635 | 38.060 | 5.246 | 960286 | 59518.500 | 2 |
| usd_A | ilp | 1 | 2 | 2 | 0 | 0 | 0 | 41.525 | 65.044 | 5.143 | 1130585.500 | 62693 | 2 |
| usd_A | ilp | 1.500 | 2 | 2 | 0 | 0 | 0 | 86.002 | 133.545 | 8.152 | 1488540 | 68280 | 2 |
| usd_sunk | ilp | 0.750 | 5 | 5 | 0 | 0.000 | 0.000 | 81.117 | 95.658 | 4.034 | 942466.600 | 58945.600 | 5 |
| usd_sunk | ilp | 1 | 5 | 4 | 1 | 0.000 | 0.000 | 89.459 | 150.057 | 4.105 | 1092376.400 | 61449.600 | 5 |
| usd_sunk | ilp | 1.500 | 5 | 5 | 0 | 0.000 | 0.000 | 110.677 | 137.957 | 4.742 | 1454023.400 | 67292.400 | 5 |
| usd_sunk | ilp_lex | 0.750 | 5 | 5 | 0 | 0.000 | 0.000 | 110.056 | 176.539 | 3.625 | 942466.600 | 58946.600 | 5 |
| usd_sunk | ilp_lex | 1 | 5 | 4 | 1 | 0.032 | 0.161 | 163.213 | 185.294 | 4.092 | 1092376.400 | 61450.600 | 5 |
| usd_sunk | ilp_lex | 1.500 | 5 | 3 | 2 | 0.165 | 0.437 | 191.998 | 200.636 | 5.216 | 1454023.400 | 67293.400 | 5 |
| usd_sunk | ilp_relaxed | 0.750 | 5 | 5 | 0 | 0.000 | 0.000 | 85.563 | 114.850 | 3.415 | 942466.600 | 58945.600 | 5 |
| usd_sunk | ilp_relaxed | 1 | 5 | 5 | 0 | 0.000 | 0.000 | 85.031 | 125.535 | 3.855 | 1092376.400 | 61449.600 | 5 |
| usd_sunk | ilp_relaxed | 1.500 | 5 | 4 | 1 | 0.088 | 0.438 | 106.213 | 150.205 | 5.449 | 1454023.400 | 67292.400 | 5 |

MIP start used (headline ILPs): ilp/baseline_round1: 4, ilp/default: 11, ilp_lex/baseline_round1: 4, ilp_lex/default: 11, ilp_relaxed/default: 15

## Baseline report-only violations ((9), (17), (18) are reported, not enforced)
| cost_variant | method | demand_mult | n | viol_17 | viol_18 | viol_9 | shortfall_18_mean |
|---|---|---|---|---|---|---|---|
| toy | baseline | 0.75 | 2 | 0 | 0 | 0 | 0 |
| toy | baseline | 1 | 2 | 0 | 1 | 0 | 0.25 |
| toy | baseline | 1.50 | 2 | 1 | 1 | 0 | 0.75 |
| toy | baseline_round1 | 0.75 | 2 | 0 | 0 | 0 | 0 |
| toy | baseline_round1 | 1 | 2 | 0 | 0 | 0 | 0 |
| toy | baseline_round1 | 1.50 | 2 | 0 | 0 | 0 | 0 |
| usd_A | baseline | 0.75 | 2 | 0 | 0 | 0 | 0 |
| usd_A | baseline | 1 | 2 | 0 | 1 | 0 | 0.25 |
| usd_A | baseline | 1.50 | 2 | 1 | 1 | 0 | 0.75 |
| usd_A | baseline_round1 | 0.75 | 2 | 0 | 0 | 0 | 0 |
| usd_A | baseline_round1 | 1 | 2 | 0 | 0 | 0 | 0 |
| usd_A | baseline_round1 | 1.50 | 2 | 0 | 0 | 0 | 0 |
| usd_sunk | baseline | 0.75 | 5 | 0 | 0 | 0 | 0 |
| usd_sunk | baseline | 1 | 5 | 0 | 1 | 0 | 0.10 |
| usd_sunk | baseline | 1.50 | 5 | 1 | 3 | 0 | 0.50 |
| usd_sunk | baseline_round1 | 0.75 | 5 | 0 | 0 | 0 | 0 |
| usd_sunk | baseline_round1 | 1 | 5 | 0 | 0 | 0 | 0 |
| usd_sunk | baseline_round1 | 1.50 | 5 | 0 | 0 | 0 | 0 |

## Figures
- `gap_by_demand.png`: headline gap per comparison and demand level (mean, 95 % CI) with the round-1 reference
- `cost_components.png`: stacked mean cost components (27)-(32) per method and demand level (usd_sunk)
- `gap_decomposition.png`: gap decomposition policy - ILP per component (usd_sunk, written model)
- `drop_rate_by_variant.png`: drop rate by cost variant (ILP and policy)

## Interpretation
1. Under USD costs with sunk rider labour the coordinated plan saves 21.9 % (+/- 7.4) of the R2.3 policy's cost on average, rising from 6.9 % at demand x0.75 to 37.3 % at x1.5: coordination pays when bikes and spare batteries are scarce.
2. The gap is 20 % unserved-order penalties and 25 % response-time cost; travel contributes 0 % and electricity / end-stock terms are negligible, so the ILP's advantage is capacity allocation (which orders to serve and when to swap), not routing.
3. Served share rises from 81.6 % (policy) to 85.9 % (ILP) with mean response 59 vs 49 min; the ILP uses 6.7 swaps and 1.14 kWh per instance against 7.2 and 2.54 kWh for the policy.
4. Dropping the end-of-horizon targets ((17)-(18), rho = 0 and R_end = 0) changes the gap to 19.0 % (+/- 7.3): the written model meets the targets at a measurable cost on this family, so the headline is not an artefact of asymmetric constraints.
5. The comparison policy matters: against the round-1 rules the same ILP gains 23.4 % (+/- 7.0); the R2.3 rules (stock-aware site choice, demand-aware charging) lower the policy's own cost by 1.8 % (+/- 1.8), which is one part of the move away from round 1's 24 %.
6. The unit system is the other part: on the variant seeds the toy-priced instances give 9.3 % (+/- 11.6) against the round-1 rules versus 26.9 % in usd_sunk, because P = 100 with w = 12 makes every dropped order worth ~8 response-hours whereas P = 30 with w = 18 makes it worth under 2.
7. The remaining difference to round 1 is the instance family (6 bikes / 4 h / no shuttles / Kaggle prep and promise times vs 10 bikes / 2 h / 12 shuttles / synthetic attributes), which this run does not isolate.
8. Cost variants and drop rates: the ILP drops 14.1 % of orders under usd_sunk, 84.9 % under usd_A and 16.5 % under toy (policy: 18.4 / 17.3 / 17.3 %); usd_A prices response at 40 $/h so a typical order's unavoidable waiting (~45 min) costs ~30 $ = P and the optimiser is indifferent between serving and dropping -- the R2.1 degeneracy argument is confirmed quantitatively (gap vs the R2.3 policy under usd_A: 34.6 %).
9. Service-first (lexicographic) plans serve on average -1.87 more orders than the cost-optimal plan at a cost premium of 11.2 %; stage 1 was certified optimal in 5 of 15 instances.
10. All ILP schedules passed `evaluate.check` with zero violations and identity (24); the policy schedules violate only the report-only families (17)/(18) when they do (counts in the table above).

## Anomalies and limitations
- 8 ILP solve(s) hit the time limit (max MIP gap 47.30 %): usd4h-K6-I36-seed1-x1/ilp/toy (47.30 %), usd4h-K6-I54-seed0-x1.5/ilp/toy (37.07 %), usd4h-K6-I54-seed1-x1.5/ilp/toy (35.50 %), usd4h-K6-I36-seed0-x1/ilp/usd_sunk (0.04 %), usd4h-K6-I36-seed0-x1/ilp_lex/usd_sunk (16.09 %), usd4h-K6-I54-seed0-x1.5/ilp_lex/usd_sunk (38.60 %), usd4h-K6-I54-seed1-x1.5/ilp_lex/usd_sunk (43.74 %), usd4h-K6-I54-seed1-x1.5/ilp_relaxed/usd_sunk (43.76 %). Their totals are incumbents (upper bounds), so the corresponding gaps are lower bounds.
- Lexicographic stage 1 was not certified optimal in 10 instance(s); U* there is the incumbent count (upper bound).
- 12 ILP solve(s) used a fallback policy schedule as MIP start because the R2.3 default violated (18): baseline_round1.
- Some ILP-vs-policy CIs include 0: ILP lexicographic vs baseline R2.3 x1.5; ILP written vs baseline R2.3 (usd_A) x0.75; ILP written vs baseline R2.3 (usd_A) x1.0; ILP written vs baseline R2.3 (usd_A) x1.5; ILP written vs baseline round-1 rules (usd_A) x1.0; ILP written vs baseline round-1 rules (usd_A) x1.5; ILP written vs baseline R2.3 (toy) x0.75; ILP written vs baseline R2.3 (toy) x1.0; ILP written vs baseline R2.3 (toy) x1.5; ILP written vs baseline round-1 rules (toy units) x0.75; ILP written vs baseline round-1 rules (toy units) x1.0; ILP written vs baseline round-1 rules (toy units) x1.5; ILP written vs baseline round-1 rules (usd_sunk, variant seeds) x1.0; ILP written vs baseline R2.3 (usd_sunk, variant seeds) x0.75; ILP written vs baseline R2.3 (usd_sunk, variant seeds) x1.0
- ILP incumbent costlier than the R2.3 policy (time limit before the start was improved, or the lexicographic service constraint): usd4h-K6-I36-seed1-x1/ilp, usd4h-K6-I54-seed0-x1.5/ilp_lex
- The usd4h family has no transfer services (|E| = 0): C_reb = 0 and transfers = 0 for every method, so the transfer dimension of E2 is not exercised here (it was in round 1 with 12 shuttles).
- Lexicographic solves use two Gurobi stages with their own TimeLimit each, so one `ilp_lex` row may take up to 2 x 100 s.
- The headline and variant phases ran as two concurrent 3-thread processes while a size-probe from the integrate step was still running (3 more threads); wall times are therefore slightly pessimistic.
