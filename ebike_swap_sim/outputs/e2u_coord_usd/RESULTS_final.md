# E2u -- coordination value under USD costs, 4 h window (`usd4h`, round 2): final report

Built from `records.jsonl` (111 rows, 111 unique (seed, demand, cost variant, method) keys, 0 duplicate rows dropped) on 2026-10-12 18:27; records last written 2026-10-12 18:18. The script-written `RESULTS.md`, `results.csv`, `improvement.csv`, `gap_decomposition.csv`, `variants.csv` and the four figures dated 16:48 were produced by an analyse pass when only one ILP row existed (stale); they were refreshed by re-running `--phase analyse` (reads `records.jsonl` only, no solves) at 18:21. No ILP was solved for this report; no file of the package was changed.

## Summary
This experiment compares the event-driven baseline policy with the E2 integer program on the round-2 `usd4h` family (6 bikes, 4 h = 48 slots of 5 min, 3 co-located sites B = 3 / C = 2, USD costs `usd_sunk`) over 5 random seeds x 3 demand levels (27 / 36 / 54 orders); all methods use the same instances and the same arc library.
The headline gap ((baseline - ILP) / baseline) is 21.9 % overall (95 % t confidence interval +/- 8.1, n = 15), by demand level x0.75 6.9 %, x1 21.3 %, x1.5 37.3 %; relative to the round-1 rule baseline it is 23.4 % (+/- 7.6), and the new R2.3 baseline rules are themselves only 1.8 % cheaper than the round-1 rules.
The composition of the gap is completely different from round 1: lateness cost accounts for 54 %, response-time cost for 25 %, the unserved penalty for 20 %, and travel plus electricity for less than 1 % combined, i.e. under USD pricing the ILP's advantage comes mainly from more punctual dispatching rather than from fewer dropped orders (in round 1, 90 % came from the P = 100 unserved penalty).
The control ILP with relaxed end targets gives 21.9 % (taking the better of written/relaxed as an upper bound; as recorded it is 19.0 %, because the relaxed solve of seed 1 x1.5 did not leave the MIP start within 150 s), which shows that (17)-(18) cost almost nothing on this family; the lexicographic (minimum unserved first) solution has its first stage proven optimal on only 5/15 instances, the rest being upper bounds under the 100 s limit.
The cost-unit sensitivity (seeds 0-1) confirms the R2.1 degeneracy argument: under `usd_A` (w = 40 $/h) the ILP drops 85 % of the orders (baseline 17 %), under `usd_sunk` 13 %, and in toy units 17 % (but 3 of the 6 toy ILP solves hit the time limit with gaps of 35-47 %, so their x1 / x1.5 results are unusable).

## Setup (as recorded in the rows)
Family `usd4h` (DECISIONS R2.2, sizes from the R2 implementation notes): 6 bikes, H = 48 x 5 min (17:00-21:00), L = 12, 3 co-located sites (B = 3, C = 2, K = 8, M = 1, sigma = 1, P_j = 4 kW), |E| = 0 transfer services (C_reb = 0 by construction), Kaggle prep / promise attributes, q0 ~ U{4..7}. Demand x0.75 / x1 / x1.5 = 27 / 36 / 54 orders; seeds 0-4 -> 15 headline instances (`instances/*.json`). Costs `usd_sunk` (kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03, bB 0.332, bC 0.082 $ per 4 h) for the headline; `usd_A` (kappa 0.50, w 40, v 80) and `toy` (E2 p.14 units) re-price the identical instances of seeds 0-1 (geometry asserted equal by the script). Arc library: plan pruning + lossless reachable pruning, 0.89-1.51 M arcs. Methods: `baseline` = R2.3 rules (stock-aware site, DEMAND_AWARE charging, JIT dispatch, dead-zone rule), `baseline_round1` = round-1 rules after the reviewer fixes (nearest site, ASAP HIGH_FIRST), `ilp` = written model (rho 0.5, R_end_j 1), `ilp_relaxed` = `relax_end_targets` copy (rho 0, R_end 0), `ilp_lex` = lexicographic (min sum u, then (26)). Gurobi, OutputFlag 0, Threads 3, TimeLimit 150 s per solve (100 s per lexicographic stage), MIP start = first clean policy schedule. Wall: headline phase 92.1 min, variants phase 20.1 min (two concurrent 3-thread processes).

Review-fix status relevant to this table (notes/workflow6_round2_review.json): fairness F1 (relaxed copy changed the DEMAND_AWARE reserve) does **not** affect any E2u row, because every `baseline` / `baseline_round1` row here was run on the written instance and the relaxed ILP is compared with those written rows; the relaxed-copy policy was used only to pick the `ilp_relaxed` MIP start (`pick_start`, label `default` in all 15 rows). Units F1 (NYC profile) concerns `nyc4h` only. The unservable-order count (fairness F5) is added below from the saved instances and the rebuilt library.

## Headline
**ILP (written model) vs the R2.3 baseline: 21.9 % (+/- 8.1, n = 15)** -- x0.75 6.9 % (+/- 4.9, n = 5), x1 21.3 % (+/- 11.3, n = 5), x1.5 37.3 % (+/- 10.8, n = 5). Against the round-1 rules baseline: 23.4 % (+/- 7.6, n = 15). Relaxed control (rho 0, R_end 0): 19.0 % (+/- 8.0, n = 15) as recorded, 21.9 % (+/- 8.1, n = 15) with the best-known relaxed value (the written solution is feasible for the relaxed instance, so min(written, relaxed) is a valid upper bound). Lexicographic: 14.9 % (+/- 8.0, n = 15). R2.3 rules vs round-1 rules (policy only): 1.8 % (+/- 1.9, n = 15). Mean totals: baseline 1022.3 USD, ILP 726.5 USD per instance. Round 1 (toy units, 10 bikes, H 24, 12 shuttles, baseline v2 = today's round-1 rules): 24.0 % (+/- 8.7; x0.75 4.3, x1 29.6, x1.5 38.2).

## Gap per comparison and demand level (mean over seeds, 95 % t-CI; gap = 100 (policy - ILP) / policy)
| comparison | demand | n | gap mean % | CI95 +/- | lo | hi | abs gain USD | CI95 | policy mean USD | ILP mean USD |
|---|---|---|---|---|---|---|---|---|---|---|
| ILP written vs baseline R2.3 [headline] | x0.75 | 5 | 6.91 | 4.87 | 2.0 | 11.8 | 35.9 | 28.2 | 502.7 | 466.9 |
| ILP written vs baseline R2.3 [headline] | x1 | 5 | 21.33 | 11.31 | 10.0 | 32.6 | 184.6 | 128.2 | 822.9 | 638.3 |
| ILP written vs baseline R2.3 [headline] | x1.5 | 5 | 37.35 | 10.80 | 26.5 | 48.1 | 667.0 | 281.8 | 1741.3 | 1074.3 |
| ILP written vs baseline R2.3 [headline] | all | 15 | 21.86 | 8.13 | 13.7 | 30.0 | 295.9 | 171.3 | 1022.3 | 726.5 |
| ILP written vs baseline round-1 rules | x0.75 | 5 | 10.36 | 4.03 | 6.3 | 14.4 | 54.4 | 22.0 | 521.3 | 466.9 |
| ILP written vs baseline round-1 rules | x1 | 5 | 22.51 | 13.44 | 9.1 | 36.0 | 202.4 | 162.4 | 840.7 | 638.3 |
| ILP written vs baseline round-1 rules | x1.5 | 5 | 37.35 | 10.82 | 26.5 | 48.2 | 667.2 | 282.3 | 1741.4 | 1074.3 |
| ILP written vs baseline round-1 rules | all | 15 | 23.41 | 7.61 | 15.8 | 31.0 | 308.0 | 168.7 | 1034.5 | 726.5 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x0.75 | 5 | 6.94 | 4.88 | 2.1 | 11.8 | 36.0 | 28.2 | 502.7 | 466.7 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x1 | 5 | 21.38 | 11.29 | 10.1 | 32.7 | 185.0 | 128.1 | 822.9 | 637.9 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | x1.5 | 5 | 28.62 | 22.16 | 6.5 | 50.8 | 492.6 | 418.9 | 1741.3 | 1248.7 |
| ILP relaxed (rho 0, R_end 0) vs baseline R2.3 [as recorded] | all | 15 | 18.98 | 7.95 | 11.0 | 26.9 | 237.9 | 151.1 | 1022.3 | 784.4 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x0.75 | 5 | 6.94 | 4.87 | 2.1 | 11.8 | 36.0 | 28.2 | 502.7 | 466.7 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x1 | 5 | 21.38 | 11.29 | 10.1 | 32.7 | 185.0 | 128.1 | 822.9 | 637.9 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | x1.5 | 5 | 37.37 | 10.78 | 26.6 | 48.2 | 667.4 | 281.6 | 1741.3 | 1073.9 |
| ILP relaxed vs baseline R2.3 [best known: min(written, relaxed)] | all | 15 | 21.90 | 8.12 | 13.8 | 30.0 | 296.1 | 171.3 | 1022.3 | 726.2 |
| ILP lexicographic vs baseline R2.3 | x0.75 | 5 | 6.71 | 4.66 | 2.1 | 11.4 | 34.8 | 26.9 | 502.7 | 467.9 |
| ILP lexicographic vs baseline R2.3 | x1 | 5 | 17.13 | 15.46 | 1.7 | 32.6 | 151.9 | 153.5 | 822.9 | 671.0 |
| ILP lexicographic vs baseline R2.3 | x1.5 | 5 | 20.88 | 25.55 | -4.7 | 46.4 | 365.4 | 479.8 | 1741.3 | 1375.9 |
| ILP lexicographic vs baseline R2.3 | all | 15 | 14.91 | 7.98 | 6.9 | 22.9 | 184.0 | 143.6 | 1022.3 | 838.3 |
| baseline R2.3 vs baseline round-1 rules (policy-only) | x0.75 | 5 | 3.59 | 6.10 | -2.5 | 9.7 | 18.5 | 31.4 | 521.3 | 502.7 |
| baseline R2.3 vs baseline round-1 rules (policy-only) | x1 | 5 | 1.73 | 3.88 | -2.2 | 5.6 | 17.8 | 40.9 | 840.7 | 822.9 |
| baseline R2.3 vs baseline round-1 rules (policy-only) | x1.5 | 5 | 0.01 | 0.04 | -0.0 | 0.0 | 0.2 | 0.6 | 1741.4 | 1741.3 |
| baseline R2.3 vs baseline round-1 rules (policy-only) | all | 15 | 1.77 | 1.92 | -0.1 | 3.7 | 12.1 | 13.2 | 1034.5 | 1022.3 |

ILP totals are incumbents; at TIME_LIMIT they are upper bounds on the optimum and the gap is a lower bound. CI only when n >= 3. CIs here use the exact Student-t quantile (t(14) = 2.145 for the pooled rows); the script's `improvement.csv` / `gap_by_demand.png` use 1.96 for n > 11, so their pooled half-widths are ~9 % narrower (e.g. +/- 7.4 instead of +/- 8.1 for the headline); means are identical.

## Gap decomposition (mean policy - ILP per component, USD per instance, share of the total gap in brackets)
| comparison | demand | n | total gap | unserved | response | lateness | C_travel | C_elec | C_setup | C_reb |
|---|---|---|---|---|---|---|---|---|---|---|
| headline: baseline R2.3 - ILP written | x0.75 | 5 | 35.9 | 6.0 (17 %) | 10.8 (30 %) | 17.4 (48 %) | 1.1 (3 %) | 0.6 (2 %) | 0.0 (0 %) | 0.0 (0 %) |
| headline: baseline R2.3 - ILP written | x1 | 5 | 184.6 | 48.0 (26 %) | 42.6 (23 %) | 92.4 (50 %) | 1.2 (1 %) | 0.5 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| headline: baseline R2.3 - ILP written | x1.5 | 5 | 667.0 | 126.0 (19 %) | 166.2 (25 %) | 372.6 (56 %) | 2.0 (0 %) | 0.3 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| headline: baseline R2.3 - ILP written | all | 15 | 295.9 | 60.0 (20 %) | 73.2 (25 %) | 160.8 (54 %) | 1.4 (0 %) | 0.4 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| round-1 rules: baseline round-1 - ILP written | x0.75 | 5 | 54.4 | 6.0 (11 %) | 18.9 (35 %) | 27.6 (51 %) | 0.9 (2 %) | 1.0 (2 %) | 0.0 (0 %) | 0.0 (0 %) |
| round-1 rules: baseline round-1 - ILP written | x1 | 5 | 202.4 | 48.0 (24 %) | 48.3 (24 %) | 104.4 (52 %) | 0.9 (0 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| round-1 rules: baseline round-1 - ILP written | x1.5 | 5 | 667.2 | 138.0 (21 %) | 157.8 (24 %) | 369.0 (55 %) | 1.8 (0 %) | 0.6 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| round-1 rules: baseline round-1 - ILP written | all | 15 | 308.0 | 64.0 (21 %) | 75.0 (24 %) | 167.0 (54 %) | 1.2 (0 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| relaxed: baseline R2.3 - ILP relaxed (as recorded) | x0.75 | 5 | 36.0 | 6.0 (17 %) | 10.8 (30 %) | 17.4 (48 %) | 1.1 (3 %) | 0.7 (2 %) | 0.0 (0 %) | 0.0 (0 %) |
| relaxed: baseline R2.3 - ILP relaxed (as recorded) | x1 | 5 | 185.0 | 48.0 (26 %) | 42.6 (23 %) | 92.4 (50 %) | 1.2 (1 %) | 0.8 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| relaxed: baseline R2.3 - ILP relaxed (as recorded) | x1.5 | 5 | 492.6 | 102.0 (21 %) | 120.3 (24 %) | 268.2 (54 %) | 1.5 (0 %) | 0.6 (0 %) | 0.0 (0 %) | 0.0 (0 %) |
| relaxed: baseline R2.3 - ILP relaxed (as recorded) | all | 15 | 237.9 | 52.0 (22 %) | 57.9 (24 %) | 126.0 (53 %) | 1.3 (1 %) | 0.7 (0 %) | 0.0 (0 %) | 0.0 (0 %) |

## Service, response, lateness, distance, swaps, energy by method and demand (usd_sunk, mean over seeds)
| demand | method | n | total USD | served % | served % of servable | unserved | drop % | mean response min | mean lateness min | n_late | bike km | swaps | kWh bought | end full | stockout slots |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x0.75 | baseline | 5 | 502.7 | 94.8 | 97.8 | 1.40 | 5.2 | 50.8 | 1.30 | 3.6 | 88.6 | 6.2 | 2.32 | 6.2 | 5.2 |
| x0.75 | baseline_round1 | 5 | 521.3 | 94.8 | 97.8 | 1.40 | 5.2 | 51.9 | 1.96 | 5.0 | 87.5 | 6.4 | 3.44 | 8.4 | 7.8 |
| x0.75 | ilp | 5 | 466.9 | 95.6 | 98.5 | 1.20 | 4.4 | 49.0 | 0.15 | 0.6 | 79.7 | 5.0 | 0.38 | 5.0 | 4.0 |
| x0.75 | ilp_relaxed | 5 | 466.7 | 95.6 | 98.5 | 1.20 | 4.4 | 49.0 | 0.15 | 0.6 | 79.6 | 6.6 | 0.01 | 2.4 | 20.6 |
| x0.75 | ilp_lex | 5 | 467.9 | 96.3 | 99.3 | 1.00 | 3.7 | 49.3 | 0.27 | 1.2 | 81.1 | 5.0 | 0.41 | 5.0 | 0.0 |
| x1 | baseline | 5 | 822.9 | 85.6 | 87.5 | 5.20 | 14.4 | 56.3 | 5.35 | 10.8 | 105.9 | 7.2 | 2.59 | 5.4 | 8.2 |
| x1 | baseline_round1 | 5 | 840.7 | 85.6 | 87.5 | 5.20 | 14.4 | 57.0 | 6.07 | 11.0 | 103.8 | 7.0 | 3.58 | 7.8 | 6.0 |
| x1 | ilp | 5 | 638.3 | 90.0 | 92.1 | 3.60 | 10.0 | 48.9 | 0.15 | 1.0 | 96.1 | 7.0 | 1.14 | 5.0 | 25.4 |
| x1 | ilp_relaxed | 5 | 637.9 | 90.0 | 92.1 | 3.60 | 10.0 | 48.9 | 0.15 | 1.0 | 95.7 | 7.4 | 0.08 | 1.8 | 40.0 |
| x1 | ilp_lex | 5 | 671.0 | 91.1 | 93.2 | 3.20 | 8.9 | 50.7 | 1.14 | 4.6 | 98.7 | 6.4 | 1.30 | 5.2 | 16.8 |
| x1.5 | baseline | 5 | 1741.3 | 64.4 | 66.2 | 19.20 | 35.6 | 70.8 | 18.11 | 23.0 | 123.8 | 8.2 | 2.70 | 4.6 | 7.4 |
| x1.5 | baseline_round1 | 5 | 1741.4 | 63.7 | 65.4 | 19.60 | 36.3 | 70.7 | 18.01 | 22.8 | 122.0 | 8.4 | 3.88 | 6.8 | 5.8 |
| x1.5 | ilp | 5 | 1074.3 | 72.2 | 74.2 | 15.00 | 27.8 | 48.8 | 0.03 | 0.2 | 107.3 | 8.0 | 1.89 | 5.0 | 26.8 |
| x1.5 | ilp_relaxed | 5 | 1248.7 | 70.7 | 72.6 | 15.80 | 29.3 | 54.7 | 5.30 | 5.2 | 111.2 | 8.4 | 0.94 | 2.4 | 30.2 |
| x1.5 | ilp_lex | 5 | 1375.9 | 68.5 | 70.4 | 17.00 | 31.5 | 58.5 | 8.24 | 10.2 | 114.6 | 8.2 | 2.46 | 5.4 | 24.2 |
| all | baseline | 15 | 1022.3 | 81.6 | 83.8 | 8.60 | 18.4 | 59.3 | 8.25 | 12.5 | 106.1 | 7.2 | 2.54 | 5.4 | 6.9 |
| all | baseline_round1 | 15 | 1034.5 | 81.4 | 83.6 | 8.73 | 18.6 | 59.8 | 8.68 | 12.9 | 104.4 | 7.3 | 3.63 | 7.7 | 6.5 |
| all | ilp | 15 | 726.5 | 85.9 | 88.2 | 6.60 | 14.1 | 48.9 | 0.11 | 0.6 | 94.4 | 6.7 | 1.14 | 5.0 | 18.7 |
| all | ilp_relaxed | 15 | 784.4 | 85.4 | 87.7 | 6.87 | 14.6 | 50.9 | 1.87 | 2.3 | 95.5 | 7.5 | 0.34 | 2.2 | 30.3 |
| all | ilp_lex | 15 | 838.3 | 85.3 | 87.6 | 7.07 | 14.7 | 52.8 | 3.22 | 5.3 | 98.1 | 6.5 | 1.39 | 5.2 | 13.7 |

`served % of servable` excludes the structurally unservable orders (no delivery arc: release + prep + ride > H), counted per instance from the saved instances: 15 of 585 orders over the 15 instances (0-2 per instance; both methods pay P for them). `end full` = full batteries in stock at H ((18) needs >= 5 of 9); `stockout slots` = slots with no full battery at a swap site.

## Drop rate by cost variant (R2.1 degeneracy table; seeds 0-1, byte-identical instances re-priced)
| cost variant | method | rows | x0.75 drop % (unserved/orders) | x1 | x1.5 | mean drop % | ILP TIME_LIMIT |
|---|---|---|---|---|---|---|---|
| usd_sunk | baseline | 6 | 5.6 (3/54) | 11.1 (8/72) | 35.2 (38/108) | 17.3 | - |
| usd_sunk | baseline_round1 | 6 | 5.6 (3/54) | 12.5 (9/72) | 35.2 (38/108) | 17.7 | - |
| usd_sunk | ilp | 6 | 3.7 (2/54) | 8.3 (6/72) | 25.9 (28/108) | 12.7 | 1 of 6 |
| usd_A | baseline | 6 | 5.6 (3/54) | 11.1 (8/72) | 35.2 (38/108) | 17.3 | - |
| usd_A | baseline_round1 | 6 | 5.6 (3/54) | 12.5 (9/72) | 35.2 (38/108) | 17.7 | - |
| usd_A | ilp | 6 | 85.2 (46/54) | 86.1 (62/72) | 83.3 (90/108) | 84.9 | 0 of 6 |
| toy | baseline | 6 | 5.6 (3/54) | 11.1 (8/72) | 35.2 (38/108) | 17.3 | - |
| toy | baseline_round1 | 6 | 5.6 (3/54) | 12.5 (9/72) | 35.2 (38/108) | 17.7 | - |
| toy | ilp | 6 | 1.9 (1/54) | 12.5 (9/72) | 35.2 (38/108) | 16.5 | 3 of 6 |

Coefficients per variant (toy in E2 p.14 units):
| cost variant | kappa | pi | P | w | v | F | bB | bC |
|---|---|---|---|---|---|---|---|---|
| toy | 1.0 | 2.0 | 100.0 | 12.0 | 24.0 | 20.0 | 3.0 | 2.0 |
| usd_A | 0.5 | 0.32 | 30.0 | 40.0 | 80.0 | 12.03 | 0.332 | 0.082 |
| usd_sunk | 0.12 | 0.32 | 30.0 | 18.0 | 36.0 | 12.03 | 0.332 | 0.082 |

Gap of the written ILP over both baselines under each variant (same seeds 0-1; n = 2 per level so no CI; per-seed gaps listed):
| cost variant | policy | demand | n | gap mean % | CI95 | policy mean | ILP mean | per-seed gaps % |
|---|---|---|---|---|---|---|---|---|
| usd_sunk | baseline | x0.75 | 2 | 7.9 | - | 498.5 | 457.5 | 3.7; 12.2 |
| usd_sunk | baseline | x1 | 2 | 24.1 | - | 853.2 | 637.5 | 16.1; 32.2 |
| usd_sunk | baseline | x1.5 | 2 | 41.2 | - | 1820.4 | 1066.4 | 38.6; 43.7 |
| usd_sunk | baseline | all | 6 | 24.4 | 16.8 | 1057.4 | 720.5 | 3.7; 16.1; 38.6; 12.2; 32.2; 43.7 |
| usd_sunk | baseline_round1 | x0.75 | 2 | 12.9 | - | 525.0 | 457.5 | 13.5; 12.2 |
| usd_sunk | baseline_round1 | x1 | 2 | 26.6 | - | 891.3 | 637.5 | 16.1; 37.1 |
| usd_sunk | baseline_round1 | x1.5 | 2 | 41.2 | - | 1820.8 | 1066.4 | 38.6; 43.8 |
| usd_sunk | baseline_round1 | all | 6 | 26.9 | 15.1 | 1079.0 | 720.5 | 13.5; 16.1; 38.6; 12.2; 37.1; 43.8 |
| usd_A | baseline | x0.75 | 2 | 17.8 | - | 1022.5 | 837.9 | 13.6; 22.0 |
| usd_A | baseline | x1 | 2 | 35.4 | - | 1725.6 | 1105.4 | 29.9; 41.0 |
| usd_A | baseline | x1.5 | 2 | 50.5 | - | 3328.9 | 1635.0 | 46.0; 54.9 |
| usd_A | baseline | all | 6 | 34.6 | 16.3 | 2025.6 | 1192.8 | 13.6; 29.9; 46.0; 22.0; 41.0; 54.9 |
| usd_A | baseline_round1 | x0.75 | 2 | 22.5 | - | 1080.4 | 837.9 | 22.9; 22.0 |
| usd_A | baseline_round1 | x1 | 2 | 37.4 | - | 1790.9 | 1105.4 | 29.9; 44.8 |
| usd_A | baseline_round1 | x1.5 | 2 | 50.5 | - | 3329.2 | 1635.0 | 46.0; 54.9 |
| usd_A | baseline_round1 | all | 6 | 36.8 | 14.4 | 2066.8 | 1192.8 | 22.9; 29.9; 46.0; 22.0; 44.8; 54.9 |
| toy | baseline | x0.75 | 2 | 16.8 | - | 603.4 | 493.7 | 4.4; 29.2 |
| toy | baseline | x1 | 2 | 1.2 | - | 1067.7 | 1088.0 | 11.5; -9.1 |
| toy | baseline | x1.5 | 2 | 2.2 | - | 2927.9 | 2869.1 | 4.4; 0.0 |
| toy | baseline | all | 6 | 6.7 | 13.5 | 1533.0 | 1483.6 | 4.4; 11.5; 4.4; 29.2; -9.1; 0.0 |
| toy | baseline_round1 | x0.75 | 2 | 19.8 | - | 621.9 | 493.7 | 10.1; 29.5 |
| toy | baseline_round1 | x1 | 2 | 5.8 | - | 1131.7 | 1088.0 | 11.7; 0.0 |
| toy | baseline_round1 | x1.5 | 2 | 2.3 | - | 2930.0 | 2869.1 | 4.5; 0.1 |
| toy | baseline_round1 | all | 6 | 9.3 | 11.6 | 1561.2 | 1483.6 | 10.1; 11.7; 4.5; 29.5; 0.0; 0.1 |

## Lexicographic (service-first) vs the written model, usd_sunk
| instance | status | stage-1 certified | stage-1 status | stage-1 s | U* (min unserved) | stage-1 bound | lex unserved | ILP unserved | lex total | ILP total | service premium % | stage-2 MIP gap % | gap vs baseline % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h-K6-I27-seed0-x0.75 | OPTIMAL | yes | OPTIMAL | 8 | 1 | - | 1 | 1 | 443.9 | 443.9 | 0.0 | 0.00 | 3.7 |
| usd4h-K6-I27-seed1-x0.75 | OPTIMAL | no | TIME_LIMIT | 100 | 2 | 0 | 1 | 1 | 471.0 | 471.0 | 0.0 | 0.00 | 12.2 |
| usd4h-K6-I27-seed2-x0.75 | OPTIMAL | no | TIME_LIMIT | 100 | 1 | 0 | 0 | 0 | 462.8 | 462.9 | -0.0 | 0.00 | 3.8 |
| usd4h-K6-I27-seed3-x0.75 | OPTIMAL | yes | OPTIMAL | 7 | 2 | - | 2 | 3 | 502.7 | 497.3 | 1.1 | 0.01 | 9.0 |
| usd4h-K6-I27-seed4-x0.75 | OPTIMAL | yes | OPTIMAL | 5 | 1 | - | 1 | 1 | 459.2 | 459.2 | 0.0 | 0.00 | 5.0 |
| usd4h-K6-I36-seed0-x1 | TIME_LIMIT | yes | OPTIMAL | 9 | 1 | - | 1 | 1 | 733.1 | 615.4 | 19.1 | 16.09 | 0.0 |
| usd4h-K6-I36-seed1-x1 | OPTIMAL | no | TIME_LIMIT | 100 | 8 | 2 | 5 | 5 | 659.6 | 659.6 | 0.0 | 0.00 | 32.2 |
| usd4h-K6-I36-seed2-x1 | OPTIMAL | no | TIME_LIMIT | 100 | 7 | 3 | 4 | 4 | 639.0 | 639.0 | 0.0 | 0.00 | 19.1 |
| usd4h-K6-I36-seed3-x1 | OPTIMAL | yes | OPTIMAL | 100 | 3 | - | 3 | 5 | 708.7 | 662.6 | 6.9 | 0.00 | 24.0 |
| usd4h-K6-I36-seed4-x1 | OPTIMAL | no | TIME_LIMIT | 100 | 3 | 2 | 3 | 3 | 614.8 | 614.8 | 0.0 | 0.00 | 10.3 |
| usd4h-K6-I54-seed0-x1.5 | TIME_LIMIT | no | TIME_LIMIT | 100 | 17 | 9 | 17 | 11 | 1642.7 | 1008.5 | 62.9 | 38.60 | -0.0 |
| usd4h-K6-I54-seed1-x1.5 | TIME_LIMIT | no | TIME_LIMIT | 100 | 21 | 13 | 21 | 17 | 1998.4 | 1124.3 | 77.7 | 43.74 | 0.0 |
| usd4h-K6-I54-seed2-x1.5 | OPTIMAL | no | TIME_LIMIT | 100 | 20 | 13 | 15 | 15 | 1061.6 | 1061.6 | 0.0 | 0.00 | 22.4 |
| usd4h-K6-I54-seed3-x1.5 | OPTIMAL | no | TIME_LIMIT | 100 | 20 | 14 | 17 | 17 | 1114.7 | 1114.7 | 0.0 | 0.00 | 43.1 |
| usd4h-K6-I54-seed4-x1.5 | OPTIMAL | no | TIME_LIMIT | 100 | 20 | 12 | 15 | 15 | 1062.1 | 1062.1 | 0.0 | 0.01 | 38.9 |

`U*` is the stage-1 incumbent (= minimum number of unserved orders only when certified); `stage-1 bound` is the stage-1 lower bound at the 100 s limit; `service premium` = 100 (lex total - written total) / written total. When stage 1 is uncertified, stage 2 only imposes sum u <= incumbent, so the lex row is at best the written optimum restricted to <= U* drops.

## Per instance (usd_sunk): total USD [unserved], policy report-only violations, TL = TIME_LIMIT with MIP gap
| instance | |I| | unservable | baseline R2.3 | baseline round-1 | ILP written | ILP relaxed | ILP lex | gap vs R2.3 % | gap vs round-1 % | MIP start | ILP s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h-K6-I27-seed0-x0.75 | 27 | 1 | 460.7 [1] | 513.2 [1] | 443.9 [1] | 443.9 [1] | 443.9 [1] | 3.7 | 13.5 | default | 96 |
| usd4h-K6-I27-seed1-x0.75 | 27 | 0 | 536.2 [2] | 536.8 [2] | 471.0 [1] | 470.9 [1] | 471.0 [1] | 12.2 | 12.2 | default | 86 |
| usd4h-K6-I27-seed2-x0.75 | 27 | 0 | 480.9 [1] | 519.9 [1] | 462.9 [0] | 462.6 [0] | 462.8 [0] | 3.8 | 11.0 | default | 86 |
| usd4h-K6-I27-seed3-x0.75 | 27 | 2 | 552.7 [2] | 552.8 [2] | 497.3 [3] | 497.1 [3] | 502.7 [2] | 10.0 | 10.0 | default | 71 |
| usd4h-K6-I27-seed4-x0.75 | 27 | 1 | 483.2 [1] | 483.6 [1] | 459.2 [1] | 459.1 [1] | 459.2 [1] | 5.0 | 5.1 | default | 67 |
| usd4h-K6-I36-seed0-x1 | 36 | 1 | 733.1 [1] | 733.4 [1] | 615.4 [1] (TL 0.04 %) | 614.5 [1] | 733.1 [1] (TL 16.09 %) | 16.1 | 16.1 | default | 150 |
| usd4h-K6-I36-seed1-x1 | 36 | 1 | 973.2 [7] (18) | 1049.2 [8] | 659.6 [5] | 659.4 [5] | 659.6 [5] | 32.2 | 37.1 | baseline_round1 | 86 |
| usd4h-K6-I36-seed2-x1 | 36 | 0 | 790.1 [7] | 790.4 [7] | 639.0 [4] | 638.7 [4] | 639.0 [4] | 19.1 | 19.2 | default | 70 |
| usd4h-K6-I36-seed3-x1 | 36 | 1 | 932.9 [8] | 944.7 [7] | 662.6 [5] | 662.3 [5] | 708.7 [3] | 29.0 | 29.9 | default | 73 |
| usd4h-K6-I36-seed4-x1 | 36 | 1 | 685.1 [3] | 685.6 [3] | 614.8 [3] | 614.5 [3] | 614.8 [3] | 10.3 | 10.3 | default | 67 |
| usd4h-K6-I54-seed0-x1.5 | 54 | 1 | 1642.2 [17] (17) (18) | 1642.7 [17] | 1008.5 [11] | 1007.9 [11] | 1642.7 [17] (TL 38.60 %) | 38.6 | 38.6 | baseline_round1 | 137 |
| usd4h-K6-I54-seed1-x1.5 | 54 | 1 | 1998.6 [21] | 1998.9 [21] | 1124.3 [17] | 1998.4 [21] (TL 43.76 %) | 1998.4 [21] (TL 43.74 %) | 43.7 | 43.8 | default | 138 |
| usd4h-K6-I54-seed2-x1.5 | 54 | 2 | 1367.6 [18] (18) | 1366.8 [20] | 1061.6 [15] | 1061.1 [15] | 1061.6 [15] | 22.4 | 22.3 | baseline_round1 | 88 |
| usd4h-K6-I54-seed3-x1.5 | 54 | 1 | 1959.0 [20] | 1959.5 [20] | 1114.7 [17] | 1114.3 [17] | 1114.7 [17] | 43.1 | 43.1 | default | 93 |
| usd4h-K6-I54-seed4-x1.5 | 54 | 2 | 1739.0 [20] (18) | 1739.4 [20] | 1062.1 [15] | 1061.9 [15] | 1062.1 [15] | 38.9 | 38.9 | baseline_round1 | 98 |

## Solver statistics
| method | solves | OPTIMAL | TIME_LIMIT | mean gap % | max gap % | mean s | total min | binaries min (M) | binaries max (M) | MIP start accepted |
|---|---|---|---|---|---|---|---|---|---|---|
| ilp | 27 | 23 | 4 | 4.441 | 47.30 | 90 | 40.5 | 0.89 | 1.51 | 27 |
| ilp_lex | 15 | 12 | 3 | 6.564 | 43.74 | 155 | 38.8 | 0.89 | 1.51 | 15 |
| ilp_relaxed | 15 | 14 | 1 | 2.919 | 43.76 | 92 | 23.1 | 0.89 | 1.51 | 15 |

| cost variant | method | demand | n | OPTIMAL | TIME_LIMIT | mean gap % | max gap % | mean s | max s | build s | binaries (M) | rows (k) | nodes | start accepted | fallback start |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| toy | ilp | x0.75 | 2 | 2 | 0 | 0.000 | 0.00 | 81 | 94 | 4.8 | 0.96 | 59.5 | 1 | 2 | 0 |
| toy | ilp | x1 | 2 | 1 | 1 | 23.648 | 47.30 | 128 | 150 | 4.8 | 1.13 | 62.7 | 1 | 2 | 1 |
| toy | ilp | x1.5 | 2 | 0 | 2 | 36.283 | 37.07 | 150 | 150 | 8.4 | 1.49 | 68.3 | 1 | 2 | 1 |
| usd_A | ilp | x0.75 | 2 | 2 | 0 | 0.000 | 0.00 | 26 | 38 | 5.2 | 0.96 | 59.5 | 1 | 2 | 0 |
| usd_A | ilp | x1 | 2 | 2 | 0 | 0.000 | 0.00 | 42 | 65 | 5.1 | 1.13 | 62.7 | 1 | 2 | 1 |
| usd_A | ilp | x1.5 | 2 | 2 | 0 | 0.000 | 0.00 | 86 | 134 | 8.2 | 1.49 | 68.3 | 1 | 2 | 1 |
| usd_sunk | ilp | x0.75 | 5 | 5 | 0 | 0.001 | 0.00 | 81 | 96 | 4.0 | 0.94 | 58.9 | 1 | 5 | 0 |
| usd_sunk | ilp | x1 | 5 | 4 | 1 | 0.008 | 0.04 | 89 | 150 | 4.1 | 1.09 | 61.4 | 1 | 5 | 1 |
| usd_sunk | ilp | x1.5 | 5 | 5 | 0 | 0.002 | 0.01 | 111 | 138 | 4.7 | 1.45 | 67.3 | 1 | 5 | 3 |
| usd_sunk | ilp_lex | x0.75 | 5 | 5 | 0 | 0.002 | 0.01 | 110 | 177 | 3.6 | 0.94 | 58.9 | 1 | 5 | 0 |
| usd_sunk | ilp_lex | x1 | 5 | 4 | 1 | 3.219 | 16.09 | 163 | 185 | 4.1 | 1.09 | 61.5 | 1 | 5 | 1 |
| usd_sunk | ilp_lex | x1.5 | 5 | 3 | 2 | 16.471 | 43.74 | 192 | 201 | 5.2 | 1.45 | 67.3 | 1 | 5 | 3 |
| usd_sunk | ilp_relaxed | x0.75 | 5 | 5 | 0 | 0.002 | 0.00 | 86 | 115 | 3.4 | 0.94 | 58.9 | 1 | 5 | 0 |
| usd_sunk | ilp_relaxed | x1 | 5 | 5 | 0 | 0.001 | 0.00 | 85 | 126 | 3.9 | 1.09 | 61.4 | 1 | 5 | 0 |
| usd_sunk | ilp_relaxed | x1.5 | 5 | 4 | 1 | 8.754 | 43.76 | 106 | 150 | 5.4 | 1.45 | 67.3 | 1 | 5 | 0 |

MIP start injected (first clean policy schedule; `baseline_round1` when the R2.3 default violated (18)):
| cost variant | method | start | n |
|---|---|---|---|
| toy | ilp | baseline_round1 | 2 |
| toy | ilp | default | 4 |
| usd_A | ilp | baseline_round1 | 2 |
| usd_A | ilp | default | 4 |
| usd_sunk | ilp | baseline_round1 | 4 |
| usd_sunk | ilp | default | 11 |
| usd_sunk | ilp_lex | baseline_round1 | 4 |
| usd_sunk | ilp_lex | default | 11 |
| usd_sunk | ilp_relaxed | default | 15 |

### TIME_LIMIT rows
| instance | variant | method | incumbent | bound | MIP gap % | s | unserved | baseline R2.3 | gap vs baseline % | start | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h-K6-I36-seed0-x1 | usd_sunk | ilp | 615.4 | 615.1 | 0.04 | 150 | 1 | 733.1 | 16.1 | default | incumbent improved over the start |
| usd4h-K6-I36-seed0-x1 | usd_sunk | ilp_lex | 733.1 | 615.1 | 16.09 | 109 | 1 | 733.1 | 0.0 | default | incumbent = MIP start (no improvement) |
| usd4h-K6-I54-seed0-x1.5 | toy | ilp | 2529.5 | 1591.9 | 37.07 | 150 | 17 | 2645.6 | 4.4 | baseline_round1 | incumbent improved over the start |
| usd4h-K6-I36-seed1-x1 | toy | ilp | 1514.7 | 798.3 | 47.30 | 150 | 8 | 1388.5 | -9.1 | baseline_round1 | incumbent = MIP start (no improvement) |
| usd4h-K6-I54-seed0-x1.5 | usd_sunk | ilp_lex | 1642.7 | 1008.5 | 38.60 | 201 | 17 | 1642.2 | -0.0 | baseline_round1 | incumbent = MIP start (no improvement) |
| usd4h-K6-I54-seed1-x1.5 | toy | ilp | 3208.7 | 2069.6 | 35.50 | 150 | 21 | 3210.2 | 0.0 | default | incumbent improved over the start |
| usd4h-K6-I54-seed1-x1.5 | usd_sunk | ilp_lex | 1998.4 | 1124.3 | 43.74 | 200 | 21 | 1998.6 | 0.0 | default | incumbent improved over the start |
| usd4h-K6-I54-seed1-x1.5 | usd_sunk | ilp_relaxed | 1998.4 | 1123.9 | 43.76 | 150 | 21 | 1998.6 | 0.0 | default | incumbent improved over the start |

## Baseline report-only violations ((9), (17), (18) reported, not enforced)
| cost variant | method | rows | (17) | (18) | (9) | instances |
|---|---|---|---|---|---|---|
| toy | baseline | 6 | 1 | 2 | 0 | usd4h-K6-I36-seed1-x1, usd4h-K6-I54-seed0-x1.5 |
| toy | baseline_round1 | 6 | 0 | 0 | 0 |  |
| usd_A | baseline | 6 | 1 | 2 | 0 | usd4h-K6-I36-seed1-x1, usd4h-K6-I54-seed0-x1.5 |
| usd_A | baseline_round1 | 6 | 0 | 0 | 0 |  |
| usd_sunk | baseline | 15 | 1 | 4 | 0 | usd4h-K6-I36-seed1-x1, usd4h-K6-I54-seed0-x1.5, usd4h-K6-I54-seed2-x1.5, usd4h-K6-I54-seed4-x1.5 |
| usd_sunk | baseline_round1 | 15 | 0 | 0 | 0 |  |

## Figures (verified present; regenerated 18:21 from the complete records)
- `gap_by_demand.png`: present, 2026-10-12 18:21 -- headline gap per comparison and demand level (mean, 95 % t-CI) with the round-1 reference line
- `cost_components.png`: present, 2026-10-12 18:21 -- stacked mean cost components (27)-(32) per method and demand level, USD
- `drop_rate_by_variant.png`: present, 2026-10-12 18:21 -- share of orders dropped by the ILP and by the R2.3 policy under usd_sunk / usd_A / toy (seeds 0-1)
- `gap_decomposition.png`: present, 2026-10-12 18:21 -- baseline R2.3 minus ILP written per component

## Anomalies and limitations
- 8 of 57 ILP solves hit the time limit (table above). Four of them never left the MIP start: `ilp_lex` seed 0 x1 (incumbent = R2.3 schedule, 733.1) and seed 0 x1.5 (= round-1 schedule, 1642.7), and `ilp_lex` + `ilp_relaxed` seed 1 x1.5 (1998.4, 0.18 USD below the start). Their gaps vs the policy are ~0 and drag the lexicographic and relaxed means at x1.5 down (lex x1.5 CI includes 0; relaxed x1.5 28.6 % as recorded vs 37.4 % best known). The written-model TIME_LIMIT in usd_sunk (seed 0 x1) is at MIP gap 0.04 % and is effectively optimal.
- Lexicographic stage 1 (min sum u) was certified in only 5 of 15 instances at the 100 s stage limit; the stage-1 bounds are weak (e.g. 9 vs incumbent 17 at seed 0 x1.5), so the 'service-first' rows measure the written optimum under sum u <= incumbent, not a true lexicographic optimum. Where certified (seeds 0, 3, 4 at x0.75, seed 3 at x1) the service premium is 0-7 % for 0-2 extra orders served.
- The `toy` variant ILP hit the limit in 3 of 6 solves with gaps 35-47 % (seed 0 x1.5, seed 1 x1, seed 1 x1.5; the seed 1 x1 incumbent is the round-1 start, costlier than the R2.3 policy), so the toy-unit gap at x1 / x1.5 (1-6 %) is not comparable with round 1; only x0.75 (17-20 %) is informative.
- `usd_A`: the ILP drops 83-86 % of orders (policy 6-35 %) and its 'gap' of 35 % is therefore a degenerate comparison (serving costs more than P); confirms R2.1.
- The R2.3 default policy reported (18) in 4 and (17) in 1 of 15 usd_sunk rows (DEMAND_AWARE reserve covers (17) only), so the `baseline_round1` schedule was injected as MIP start in those ILPs; the baseline column still reports the policy under test. Its total is conservative for the headline (the policy saves electricity by not meeting (18)).
- At x1.5 the two policies are almost identical (0.01 % apart) and the R2.3 rules save only 1.8 % overall: on this family (3 spares per site, 6 bikes) the stock-aware site choice and demand-aware charging rarely change a decision.
- Structurally unservable orders: 15 over the 15 instances (0-2 each, always the last-released ids); both methods pay P = 30 for them and they inflate every drop rate identically.
- |E| = 0: the transfer dimension of E2 is not exercised (C_reb = 0). Grid groups never bind (peak <= 2.7 kW). The ILP buys 0.4-1.9 kWh per instance (ending with exactly the 5 full batteries (18) needs; the relaxed ILP 0.0-0.9 kWh and 2 full batteries), the policy 2.3-2.7 kWh; electricity is < 1.3 USD per instance either way.
- Every ILP row reports node_count = 1: all solves (optimal or not) ended at the root node (presolve, cuts and heuristics), so the time limit is spent in the root and the stage-1 lexicographic bounds are root LP bounds.
- MIP-start acceptance: every one of the 57 ILP rows records `mip_start_accepted = True` (fix-and-solve certificate from the run itself); no extra certificate was solved for this report.
- The headline and variant phases ran concurrently with other 3-thread jobs; runtimes are pessimistic, and a 150 s limit at x1.5 (1.4-1.5 M binaries) is tight (4 of 5 written solves optimal in 88-138 s).

## Interpretation
1. Under USD costs with sunk rider labour the coordinated E2 plan saves 21.9 % (+/- 8.1) of the R2.3 policy's cost on the usd4h family, rising from 6.9 % at demand x0.75 to 21.3 % at x1 and 37.3 % at x1.5, i.e. the same monotone shape as round 1 (4.3 / 29.6 / 38.2 %) and a pooled value (21.9 vs 24.0 %) that is statistically indistinguishable from it despite the move from toy to USD units, from 10 to 6 bikes and from 2 to 4 h.
2. What the gap is made of has changed completely: in round 1 90 % of the baseline-minus-ILP difference was the P = 100 drop penalty, whereas here lateness (v = 36 $/h) carries 54 %, response time (w = 18 $/h) 25 % and unserved orders only 20 %; travel and electricity together are under 1 %.
3. The ILP's advantage is therefore timing rather than volume: served share is 81.6 % (policy) vs 85.9 % (ILP) pooled, but the policy delivers 12.5 late orders per instance (8.3 min mean lateness) against 0.6 (0.1 min) for the ILP, with mean response 59 vs 49 min.
4. Battery logistics is again not where the money is: the ILP uses 6.7 swaps and 1.14 kWh per instance against 7.2 swaps and 2.54 kWh for the policy, travel differs by 1-2 USD, and the ILP even tolerates more empty-stock slots (19 vs 7 per instance) because it times its swaps around the stock it knows it will have, ending with exactly the 5 full batteries that (18) requires; the 4 h window with 3 spares per site is tight enough to be felt but not to cost money at 0.32 $/kWh.
5. The end-of-horizon targets cost almost nothing: the relaxed control gives 21.9 % (best known) vs 21.9 % written, a difference of a few USD per instance (the ILP meets (18) by simply not swapping more than it needs), so the headline is not an artefact of asymmetric constraints.
6. The comparison policy matters less than in round 1: the R2.3 rules lower the policy's own cost by only 1.8 % (+/- 1.9), so the ILP gains 23.4 % against the round-1 rules vs 21.9 % against R2.3; the stock-aware / demand-aware rules bite at x0.75 (3.6 %) and vanish at x1.5 (0.0 %).
7. The unit system drives the drop rate, not the gap shape: with `usd_sunk` the ILP drops 4-26 % of orders (policy 6-35 %), with `usd_A` (w = 40 $/h) it drops 83-86 % because the unavoidable prep + ride wait of a typical order costs more than P = 30, and with toy units it drops 2-35 % on the solves that finished; the R2.1 choice of `usd_sunk` is confirmed as necessary.
8. Compared with round 1 the pooled headline is unchanged in size but should be read differently: a 22 % saving of a ~1000 USD evening (about 300 USD per 6-bike shift, 650 USD at x1.5) is now mostly on-time delivery value to customers (w, v), with the operator-side components (travel, electricity, setup) essentially identical between the two methods.
9. Service-first planning is cheap where it could be certified (0-7 % premium for 0-2 extra orders at x0.75 / seed 3 x1), but the 100 s stage limit left 10 of 15 stage-1 solves uncertified; a longer stage-1 limit (or the service-rate constraint (33)) is needed before the lexicographic numbers can be quoted.
10. Solver side: 0.89-1.51 M binaries, 56-69 k rows; 23 of 27 written-model solves are OPTIMAL (mean 93 s), the four TIME_LIMIT written solves are at gap < 0.04 % (usd_sunk) or in the toy variant; the x1.5 instances are at the edge of the 150 s budget and would need ~300 s for the lexicographic and relaxed variants.

