# E8 round 3 (final report) -- NYC semi-real Midtown instance, seeds 0-9, sitings busiest / grid, methods baseline / ILP / relaxed ILP

Authoritative inputs: `outputs/e8_round3/{records.jsonl, results.csv, per_instance.csv, siting.csv, demand_comparison.json, wall_time.json, run_stdout.log, instances/}` written by `experiments/e8_round3.py` on 2026-10-12 21:59-22:25 (wall 25.3 min for the 14 new instances), which imports the design of `experiments/e8_nyc_fixed.py`. `records.jsonl` holds 60 records with 60 unique (siting, seed, method) keys (0 duplicates; the LAST record per key is used): 18 rows reused from round 2 (`source = round2`, seeds 0-2, byte-equal totals to `outputs/e8_nyc_fixed/rows.jsonl`, verified) and 42 rows solved in round 3 (`source = round3`, seeds 3-9). Every statistic below was recomputed from `records.jsonl` and agrees with the script's own `RESULTS.md` (whose Chinese abstract has been rewritten in English in place). Gap definition throughout: **gap = (baseline - ILP) / baseline**. 95 % confidence intervals are Student-t over seeds (t_{0.975,9} = 2.262 for n = 10). `outputs/e8_nyc/` (pre-fix ramp profile) remains superseded and is not used.

## Summary

On the semi-real NYC Midtown/Chelsea/Flatiron instance (real DOHMH restaurants, ACS 2020-24 literature-formula zone weights and three real candidate-site coordinates projected onto the synthetic 150 m grid; 6 bikes, 36 orders, 17:00-21:00, `usd_sunk` costs), the E2 integer program lowers the round-2 baseline policy's total cost by **31.8 +/- 8.2 %** (n = 10 seeds) with the sites in the three busiest restaurant cells and by **30.5 +/- 8.6 %** with the sites at the grid-connected landmarks (8th Ave/W 34th, Union Square, Grand Central), and the fair relaxed-end-target control reproduces these figures to within 0.03 points (31.9 % / 30.6 %) because the end targets (17)-(18) cost only 0.28-0.26 USD in the optimum. With 10 seeds the confidence half-widths shrink from 29-38 points (round 2, n = 3) to 8-9 points, the gap is positive on 20 of 20 instances (range 17.7-50.9 %), and the round-2 point estimates (36.5 % / 34.3 %) sit inside the new intervals, the seven new seeds alone averaging 29.8 % / 28.9 %. The saving (343.8 USD per 4 h window at the busiest siting) is 59 % lateness, 35 % response time and 6 % unserved-order penalty: the ILP serves 85.8 % of the orders with a mean response of 0.83 h and 1.5 late deliveries per run, against 83.9 %, 1.07 h and 17.8 late deliveries for the nearest-rider policy, while riding 13 % fewer kilometres. Siting moves the ILP optimum by at most 0.41 USD (0.06 %) on any seed (coefficient of variation of the ILP total across seeds 2.8 %), whereas the baseline moves by -9.1 % to +5.8 % with no consistent sign (mean -1.6 +/- 3.6 %), so coordinated scheduling absorbs where the stations are and the myopic policy does not. All 40 ILP solves were proven optimal (0 TIME_LIMIT, 0 SKIPPED_BUDGET; mean 45.5 s, max 64.4 s at Threads 3, 553 k binaries on average), but because `PRUNING_NYC` restricts repositioning for the ILP only, every ILP total is an upper bound on the written E2 optimum and every gap a lower bound on the coordination value; the demand side is more realistic than the synthetic family (cuisine L1 0.15 vs 0.28 to the Kaggle shares, about 32 restaurants per seed instead of 8, 8-11 NTAs), yet trip geometry (1.80 vs 1.86 km) is the same because the road network, elevation and signals are still synthetic.

## 1. Setup (as run)

| item | value |
|---|---|
| family / builder | `nyc4h`, `data_nyc.make_nyc_instance` (DECISIONS R2.4), sitings from `e8_nyc_fixed.make_instance` |
| size | 6 bikes, 36 orders (1.5 orders per bike-hour), window 17:00-21:00, H = 48 slots x 5 min, L = 12 levels (50 Wh) |
| costs | `usd_sunk` (R2.1): kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h site; q_res 1, rho 0.5, R_end 1 |
| sites | 3 co-located (B 3, C 2, K 8, M 1, sigma 1, P 4 kW; grid group 8 kW / 6 kW 18-20 h), no transfer services (E = {}) |
| siting `busiest` | three busiest DOHMH restaurant cells, grid nodes [13,14], [17,13], [17,19] = (40.7513, -73.9922), (40.7475, -73.9869), (40.7545, -73.9817) |
| siting `grid` | grid-connected landmarks snapped to the grid: 8th Ave / W 34th St [12,15], Union Square [19,4], Grand Central [20,19] |
| seeds | 0-9; seeds 0-2 reused from round 2 (`outputs/e8_nyc_fixed/rows.jsonl`, all ILP rows OPTIMAL, reuse rule `common.reusable_ilp_row`), seeds 3-9 solved in round 3 |
| demand identity | `demand_md5` (orders, q0, H, L) asserted equal across the two sitings of every seed: all 10 seeds pass; the two sitings of a seed differ only in the site nodes and the bikes' start nodes (round robin over the sites) |
| pruning | `common.PRUNING_NYC` (`pruning_targets = facilities`): moves only into the 3 site nodes, tau_max 4, start_slack 6, lossless reachable pruning |
| methods | `baseline` = R2.3 rules (stock-aware site choice, DEMAND_AWARE charging with reserve R_end_j, JIT dispatch, dead-zone rule; (9)/(17)/(18) reported, not enforced); `ilp` = written E2 model (rho 0.5, R_end 1) with a verified baseline schedule as MIP start (`common.feasible_mip_start`); `ilp_relaxed` = `common.relax_end_targets` (rho 0, R_end 0), the fair control |
| fairness fix F1 | relaxed-copy baseline (only the MIP start of `ilp_relaxed`) ran with the written R_end as charging reserve: `baseline_relaxed_copy_differs` = False in 20 / 20 runs, `policy_reserve_source` = `written_R_end` in 20 / 20 |
| solver | Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 300 s, Seed 0 (`common.ILP_PARAMS_R3`) for the round-3 rows; the reused round-2 rows were solved with Threads 3, TimeLimit 300 s (Gurobi default seed, which is also 0) |
| wall budget | 2 h; used 25.3 min for 14 instances x 3 methods (42 rows), 0 rows SKIPPED_BUDGET |

**Geometry caveat (R2.4).** Real restaurants, real NTA zone weights and real candidate-site coordinates are projected onto the synthetic 150 m GridNetwork (local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, rotated by -29 deg to the Manhattan street-grid azimuth, snapped to 150 m blocks). No real road network is used; elevation and traffic signals are synthetic; every distance, travel time and energy figure comes from this synthetic geometry.

**Pruning caveat (fairness review F2).** `PRUNING_NYC` forbids repositioning moves to non-site nodes. The baseline never makes such moves (it repositions only to swap sites and starts deliveries in place), so it loses nothing; the ILP loses pre-positioning towards restaurants / customers (tau_max 4 never binds on nyc4h). Every ILP total below is therefore an **upper bound on the written E2 optimum and every gap a lower bound on the coordination value**. The lossless probe (`e8_nyc_fixed.py --targets default`, multi-million-arc ILPs) has still not been run.

## 2. Headline: ILP vs baseline vs relaxed control (mean over 10 seeds, 95 % t-CI, t_{0.975,9} = 2.262)

| siting | gap written ILP, % | gap relaxed ILP, % | gap_vs_ilp = (baseline - ILP)/ILP, % | baseline total, USD | ILP total, USD | relaxed total, USD | saving baseline - ILP, USD | ILP - relaxed, USD (price of (17)-(18)) | gap range over seeds, % | median gap, % |
|---|---|---|---|---|---|---|---|---|---|---|
| busiest | **31.8 +/- 8.2** | 31.9 +/- 8.2 | 50.8 +/- 19.8 | 1013.7 +/- 149.3 | 669.9 +/- 13.3 | 669.6 +/- 13.3 | 343.8 +/- 138.8 | 0.28 +/- 0.06 | 18.9 - 49.3 | 30.9 |
| grid | **30.5 +/- 8.6** | 30.6 +/- 8.6 | 48.4 +/- 20.7 | 997.1 +/- 153.4 | 669.9 +/- 13.3 | 669.6 +/- 13.3 | 327.2 +/- 144.2 | 0.26 +/- 0.05 | 17.7 - 50.9 | 28.3 |
| per-seed mean of the two sitings (n = 10, independent) | 31.2 +/- 8.3 | - | - | - | - | - | - | - | - | - |
| both sitings pooled (n = 20, NOT independent: sitings share each seed's demand) | 31.2 +/- 5.4 | 31.2 +/- 5.3 | - | - | - | - | - | - | - | - |

Round-2 comparison on the same definition: seeds 0-2 only give 36.5 +/- 29.3 % (busiest) and 34.3 +/- 37.6 % (grid) (t_{0.975,2} = 4.303, identical to the round-2 report); the seven new seeds 3-9 alone give 29.8 +/- 10.7 % and 28.9 +/- 10.5 %. The gap is positive on 20 / 20 instances.

### 2a. Service and operations (mean over 10 seeds, 95 % t-CI)

| siting | method | served share | served share of servable orders | n_unserved (of 36) | mean response, h | max response, h | n_late (of 36) | mean lateness, h | bike km | swaps | kWh purchased | end full batteries (of 9) | stock-out slots | (17) reported violated | (18) reported violated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 0.839 +/- 0.035 | 0.870 +/- 0.028 | 5.80 +/- 1.25 | 1.067 +/- 0.092 | 1.43 | 17.8 +/- 3.2 | 0.192 | 109.9 +/- 6.0 | 7.1 +/- 0.9 | 2.46 +/- 0.31 | 5.4 | 4.9 | 2 of 10 runs | 2 of 10 runs |
| busiest | ilp | 0.858 +/- 0.022 | 0.891 +/- 0.026 | 5.10 +/- 0.79 | 0.826 +/- 0.015 | 1.03 | 1.5 +/- 0.8 | 0.005 | 95.1 +/- 5.3 | 6.5 +/- 0.5 | 0.83 +/- 0.21 | 5.0 | 9.3 | 0 (enforced) | 0 (enforced) |
| busiest | ilp_relaxed | 0.858 +/- 0.022 | 0.891 +/- 0.026 | 5.10 +/- 0.79 | 0.826 +/- 0.015 | 1.03 | 1.5 +/- 0.8 | 0.005 | 95.0 +/- 5.4 | 7.6 +/- 0.5 | 0.00 +/- 0.00 | 1.4 | 31.1 | 0 (enforced) | n/a (relaxed) |
| grid | baseline | 0.853 +/- 0.033 | 0.885 +/- 0.031 | 5.30 +/- 1.17 | 1.058 +/- 0.094 | 1.41 | 18.4 +/- 3.2 | 0.184 | 113.8 +/- 7.5 | 7.1 +/- 0.7 | 2.25 +/- 0.26 | 5.3 | 8.3 | 0 of 10 runs | 2 of 10 runs |
| grid | ilp | 0.858 +/- 0.022 | 0.891 +/- 0.026 | 5.10 +/- 0.79 | 0.826 +/- 0.015 | 1.03 | 1.5 +/- 0.8 | 0.005 | 95.7 +/- 5.5 | 6.5 +/- 0.4 | 0.82 +/- 0.13 | 5.0 | 12.4 | 0 (enforced) | 0 (enforced) |
| grid | ilp_relaxed | 0.858 +/- 0.022 | 0.891 +/- 0.026 | 5.10 +/- 0.79 | 0.826 +/- 0.015 | 1.03 | 1.5 +/- 0.8 | 0.005 | 95.7 +/- 5.6 | 7.1 +/- 0.4 | 0.00 +/- 0.00 | 1.9 | 22.7 | 0 (enforced) | n/a (relaxed) |

`served share of servable orders` for the ILP rows is computed here as n_served / (36 - n_unservable) (the script leaves that column empty for ILP rows). Structurally unservable orders (no delivery arc; both methods pay P) per seed 0-9: 0, 1, 2, 1, 3, 1, 1, 3, 1, 0 (mean 1.3; identical for both sitings). The baseline policy runs in 4.7 ms per instance (max 7.3 ms).

## 3. Per-cell table (one row per siting x seed; all 20 ILP and 20 relaxed solves OPTIMAL)

| siting | seed | source | arcs | baseline USD | base. unserved | base. km | base. swaps | base. late | base. reports | ILP USD | status | MIP gap | time, s | nodes | ILP unserved | ILP km | ILP swaps | ILP late | MIP-start variant | relaxed USD | status | time, s | gap written, % | gap relaxed, % | gap_vs_ilp, % | ILP - relaxed, USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | 0 | round2 | 729,139 | 1374.68 | 5 | 119.2 | 9 | 25 | (18) | 706.08 | OPTIMAL | 0.0e+00 | 60.0 | 1 | 6 | 90.0 | 6 | 4 | baseline_round1 | 705.87 | OPTIMAL | 55.5 | 48.64 | 48.65 | 94.69 | 0.21 |
| busiest | 1 | round2 | 530,382 | 1043.48 | 6 | 110.8 | 6 | 17 | - | 671.51 | OPTIMAL | 0.0e+00 | 34.3 | 1 | 5 | 102.1 | 6 | 1 | default | 671.33 | OPTIMAL | 31.7 | 35.65 | 35.66 | 55.39 | 0.18 |
| busiest | 2 | round2 | 511,370 | 882.69 | 6 | 106.4 | 8 | 17 | (17) | 661.16 | OPTIMAL | 0.0e+00 | 36.7 | 1 | 5 | 90.9 | 6 | 0 | baseline_round1 | 660.91 | OPTIMAL | 36.3 | 25.10 | 25.13 | 33.51 | 0.25 |
| busiest | 3 | round3 | 452,675 | 833.00 | 8 | 94.2 | 6 | 12 | - | 675.21 | OPTIMAL | 0.0e+00 | 51.5 | 1 | 5 | 95.1 | 6 | 1 | default | 674.95 | OPTIMAL | 44.1 | 18.94 | 18.97 | 23.37 | 0.27 |
| busiest | 4 | round3 | 506,255 | 1089.28 | 7 | 116.4 | 6 | 20 | - | 683.23 | OPTIMAL | 0.0e+00 | 39.3 | 1 | 5 | 111.4 | 7 | 3 | default | 682.94 | OPTIMAL | 32.3 | 37.28 | 37.30 | 59.43 | 0.28 |
| busiest | 5 | round3 | 544,674 | 889.26 | 4 | 111.9 | 8 | 18 | (17), (18) | 657.34 | OPTIMAL | 0.0e+00 | 49.3 | 1 | 4 | 94.2 | 8 | 1 | baseline_round1 | 656.87 | OPTIMAL | 44.6 | 26.08 | 26.13 | 35.28 | 0.46 |
| busiest | 6 | round3 | 523,580 | 810.24 | 4 | 103.5 | 6 | 13 | - | 646.19 | OPTIMAL | 0.0e+00 | 34.8 | 1 | 5 | 91.0 | 6 | 1 | default | 645.96 | OPTIMAL | 37.2 | 20.25 | 20.28 | 25.39 | 0.23 |
| busiest | 7 | round3 | 530,492 | 1080.27 | 8 | 103.8 | 6 | 21 | - | 680.14 | OPTIMAL | 0.0e+00 | 47.7 | 5 | 6 | 97.7 | 7 | 1 | default | 679.79 | OPTIMAL | 49.9 | 37.04 | 37.07 | 58.83 | 0.36 |
| busiest | 8 | round3 | 628,238 | 1330.17 | 7 | 110.2 | 7 | 23 | - | 673.92 | OPTIMAL | 0.0e+00 | 64.1 | 1 | 7 | 84.4 | 6 | 1 | default | 673.70 | OPTIMAL | 64.4 | 49.34 | 49.35 | 97.38 | 0.21 |
| busiest | 9 | round3 | 609,017 | 803.90 | 3 | 122.7 | 9 | 12 | - | 643.75 | OPTIMAL | 0.0e+00 | 60.0 | 1 | 3 | 94.5 | 7 | 2 | default | 643.41 | OPTIMAL | 53.0 | 19.92 | 19.96 | 24.88 | 0.34 |
| grid | 0 | round2 | 720,006 | 1338.39 | 5 | 115.7 | 9 | 25 | (18) | 706.16 | OPTIMAL | 0.0e+00 | 54.2 | 1 | 6 | 90.6 | 6 | 4 | baseline_round1 | 705.94 | OPTIMAL | 51.0 | 47.24 | 47.25 | 89.53 | 0.21 |
| grid | 1 | round2 | 525,584 | 1085.71 | 7 | 112.6 | 7 | 17 | - | 671.76 | OPTIMAL | 0.0e+00 | 28.1 | 1 | 5 | 104.2 | 6 | 1 | default | 671.58 | OPTIMAL | 34.1 | 38.13 | 38.14 | 61.62 | 0.18 |
| grid | 2 | round2 | 490,210 | 802.70 | 5 | 104.4 | 7 | 13 | - | 661.01 | OPTIMAL | 0.0e+00 | 35.7 | 1 | 5 | 88.8 | 7 | 0 | default | 660.73 | OPTIMAL | 29.7 | 17.65 | 17.69 | 21.44 | 0.28 |
| grid | 3 | round3 | 451,186 | 827.79 | 7 | 99.6 | 6 | 13 | - | 675.05 | OPTIMAL | 0.0e+00 | 44.1 | 1 | 5 | 93.9 | 6 | 1 | default | 674.84 | OPTIMAL | 58.8 | 18.45 | 18.48 | 22.63 | 0.21 |
| grid | 4 | round3 | 497,937 | 1009.01 | 6 | 123.0 | 6 | 23 | - | 683.43 | OPTIMAL | 0.0e+00 | 54.1 | 1 | 5 | 112.6 | 7 | 3 | default | 683.16 | OPTIMAL | 36.5 | 32.27 | 32.29 | 47.64 | 0.27 |
| grid | 5 | round3 | 532,829 | 838.62 | 4 | 116.1 | 8 | 16 | (18) | 656.93 | OPTIMAL | 0.0e+00 | 36.8 | 1 | 4 | 92.7 | 6 | 1 | baseline_round1 | 656.69 | OPTIMAL | 39.0 | 21.67 | 21.69 | 27.66 | 0.23 |
| grid | 6 | round3 | 537,730 | 814.60 | 4 | 114.2 | 7 | 14 | - | 646.57 | OPTIMAL | 0.0e+00 | 38.3 | 1 | 5 | 93.4 | 7 | 1 | default | 646.28 | OPTIMAL | 40.6 | 20.63 | 20.66 | 25.99 | 0.28 |
| grid | 7 | round3 | 521,696 | 1030.57 | 6 | 102.1 | 7 | 21 | - | 680.04 | OPTIMAL | 0.0e+00 | 44.9 | 1 | 6 | 96.8 | 7 | 1 | default | 679.68 | OPTIMAL | 46.0 | 34.01 | 34.05 | 51.55 | 0.36 |
| grid | 8 | round3 | 619,426 | 1373.91 | 7 | 114.6 | 6 | 23 | - | 674.21 | OPTIMAL | 0.0e+00 | 59.0 | 1 | 7 | 86.9 | 6 | 1 | default | 673.99 | OPTIMAL | 57.5 | 50.93 | 50.94 | 103.78 | 0.21 |
| grid | 9 | round3 | 595,659 | 850.14 | 2 | 135.6 | 8 | 19 | - | 644.00 | OPTIMAL | 0.0e+00 | 54.0 | 1 | 3 | 96.9 | 7 | 2 | default | 643.59 | OPTIMAL | 52.3 | 24.25 | 24.30 | 32.01 | 0.41 |

`base. reports` = constraint families the baseline reports violated (not enforced, not priced). `source` = round2 for the reused seeds 0-2, round3 for seeds 3-9.

## 4. Cost components (26)-(32), mean over 10 seeds, USD (95 % t-CI on the total)

| siting | method | total | C_setup (27) | C_elec (28) | C_travel (29) | unserved P u (30) | response w (31) | lateness v (31) | C_reb (32) |
|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 1013.7 +/- 149.3 | 39.57 | 0.79 | 13.19 | 174.0 +/- 37.6 | 578.9 +/- 49.0 | 207.3 +/- 95.0 | 0 |
| busiest | ilp | 669.9 +/- 13.3 | 39.57 | 0.26 | 11.42 | 153.0 +/- 23.6 | 459.6 +/- 16.1 | 6.0 +/- 3.5 | 0 |
| busiest | ilp_relaxed | 669.6 +/- 13.3 | 39.57 | 0.00 | 11.40 | 153.0 +/- 23.6 | 459.6 +/- 16.1 | 6.0 +/- 3.5 | 0 |
| grid | baseline | 997.1 +/- 153.4 | 39.57 | 0.72 | 13.65 | 159.0 +/- 35.1 | 583.2 +/- 47.2 | 201.0 +/- 97.2 | 0 |
| grid | ilp | 669.9 +/- 13.3 | 39.57 | 0.26 | 11.48 | 153.0 +/- 23.6 | 459.6 +/- 16.1 | 6.0 +/- 3.5 | 0 |
| grid | ilp_relaxed | 669.6 +/- 13.3 | 39.57 | 0.00 | 11.48 | 153.0 +/- 23.6 | 459.6 +/- 16.1 | 6.0 +/- 3.5 | 0 |

Gap decomposition (baseline - written ILP, mean over 10 seeds):

| siting | total gap, USD | lateness | response | unserved | travel | electricity | setup / transfers |
|---|---|---|---|---|---|---|---|
| busiest | 343.8 | 201.3 (58.5 %) | 119.2 (34.7 %) | 21.0 (6.1 %) | 1.8 (0.5 %) | 0.52 (0.15 %) | 0 |
| grid | 327.2 | 195.0 (59.6 %) | 123.6 (37.8 %) | 6.0 (1.8 %) | 2.2 (0.7 %) | 0.46 (0.14 %) | 0 |

The gap is driven by the baseline's lateness: across the 20 instances the per-instance gap correlates with the baseline's lateness cost at r = 0.98 (and with the baseline total at r = 0.99), while the ILP total is nearly constant (coefficient of variation 2.8 % vs 21 % for the baseline). Seeds 0 and 8 (gap 47-51 %) are the instances where the nearest-rider policy accumulates 400-500 USD of lateness.

## 5. Siting sensitivity (grid-connected minus busiest, same demand per seed; ILP vs baseline)

| seed | baseline busiest | baseline grid | delta, USD | delta, % | ILP busiest | ILP grid | delta, USD | delta, % | relaxed delta, % | gap busiest, % | gap grid, % | gap grid - busiest, points |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1374.68 | 1338.39 | -36.29 | -2.64 | 706.08 | 706.16 | +0.07 | +0.010 | +0.010 | 48.64 | 47.24 | -1.40 |
| 1 | 1043.48 | 1085.71 | +42.23 | +4.05 | 671.51 | 671.76 | +0.25 | +0.038 | +0.038 | 35.65 | 38.13 | +2.48 |
| 2 | 882.69 | 802.70 | -79.98 | -9.06 | 661.16 | 661.01 | -0.15 | -0.022 | -0.027 | 25.10 | 17.65 | -7.45 |
| 3 | 833.00 | 827.79 | -5.21 | -0.63 | 675.21 | 675.05 | -0.16 | -0.024 | -0.016 | 18.94 | 18.45 | -0.49 |
| 4 | 1089.28 | 1009.01 | -80.28 | -7.37 | 683.23 | 683.43 | +0.20 | +0.029 | +0.032 | 37.28 | 32.27 | -5.01 |
| 5 | 889.26 | 838.62 | -50.64 | -5.69 | 657.34 | 656.93 | -0.41 | -0.063 | -0.027 | 26.08 | 21.67 | -4.41 |
| 6 | 810.24 | 814.60 | +4.37 | +0.54 | 646.19 | 646.57 | +0.38 | +0.058 | +0.050 | 20.25 | 20.63 | +0.38 |
| 7 | 1080.27 | 1030.57 | -49.70 | -4.60 | 680.14 | 680.04 | -0.11 | -0.016 | -0.016 | 37.04 | 34.01 | -3.03 |
| 8 | 1330.17 | 1373.91 | +43.74 | +3.29 | 673.92 | 674.21 | +0.29 | +0.043 | +0.043 | 49.34 | 50.93 | +1.59 |
| 9 | 803.90 | 850.14 | +46.25 | +5.75 | 643.75 | 644.00 | +0.25 | +0.039 | +0.028 | 19.92 | 24.25 | +4.33 |
| mean +/- 95 % CI (n = 10) | 1013.7 | 997.1 | -16.6 +/- 35.6 | -1.64 +/- 3.63 | 669.9 | 669.9 | 0.06 +/- 0.18 | 0.009 +/- 0.028 | - | 31.8 | 30.5 | -1.3 +/- 2.6 |

The ILP optimum is insensitive to the siting: |delta| <= 0.41 USD (<= 0.063 %) on every seed, mean 0.009 +/- 0.028 % (the CI contains 0). The baseline moves by -9.1 % to +5.8 % (6 of 10 seeds cheaper at the grid siting; mean -1.6 +/- 3.6 %, CI contains 0), so the grid-connected siting is neither systematically better nor worse for the policy, it is simply less predictable. The headline gap difference between sitings (-1.3 +/- 2.6 points) is not significant.

## 6. Demand realism: NYC semi-real `nyc4h` vs the synthetic `usd4h` family (same 10 seeds, 360 pooled orders each; from `demand_comparison.json`)

| descriptor | NYC semi-real (`nyc4h`) | synthetic `usd4h` |
|---|---|---|
| restaurants available | 4,607 DOHMH rows in the box (26.1 % mapped to the non-samplable `other` class) | 8 synthetic |
| distinct restaurants hit per seed | 32, 32, 33, 34, 32, 32, 32, 32, 34, 32 (mean 32.5) | 8, 8, 8, 8, 7, 8, 7, 8, 8, 7 |
| top-10 restaurants' share of orders | 0.33 - 0.39 (mean 0.38) | 1.00 |
| top-3 restaurants' share | 0.14 - 0.19 (mean 0.17) | 0.56 - 0.69 (mean 0.63) |
| customer zones hit per seed | 11, 8, 9, 9, 9, 11, 9, 10, 10, 9 (of 13 NTA-2020 with grid nodes) | 12 - 14 (of 16 synthetic zones) |
| mean restaurant -> customer route, km | 1.70 - 2.10 (mean 1.80) | 1.66 - 2.02 (mean 1.86) |
| max route, km | 3.15 - 3.45 | 3.45 - 4.95 |
| mean prep, min | 27.2 - 30.3 (mean 29.2) | 28.5 - 30.6 (mean 29.3) |
| promise after ready | 5 slots (25 min) | 5 slots |
| L1 distance of realised cuisine shares to the Kaggle target | **0.149** | 0.277 |
| zone weights | ACS 2020-24 literature formula | synthetic Dirichlet demographics |

Cuisine mix (pooled over 10 seeds; Kaggle target / NYC realised / synthetic realised): American 0.308 / 0.311 / 0.369; Japanese 0.248 / 0.225 / 0.292; Italian 0.157 / 0.192 / 0.189; Chinese 0.113 / 0.092 / 0.114; Mexican 0.041 / 0.047 / 0.036; Indian 0.038 / 0.053 / 0; Middle Eastern 0.026 / 0.036 / 0; Mediterranean 0.024 / 0.017 / 0; Thai 0.010 / 0.003 / 0; French 0.009 / 0.003 / 0; Southern 0.009 / 0.014 / 0; Korean 0.007 / 0.006 / 0; Spanish 0.006 / 0 / 0; Vietnamese 0.004 / 0.003 / 0. The synthetic family has restaurants in only 5 cuisines; with 360 draws the NYC instance now hits 13 of the 14 classes (round 2, 108 draws: 11).

Customer zone shares (sampling law = ACS zone-weight mass of the grid nodes / realised over 360 orders): MN0603 Murray Hill-Kips Bay 0.203 / 0.175; MN0402 Hell's Kitchen 0.200 / 0.186; MN0401 Chelsea-Hudson Yards 0.178 / 0.181; MN0501 Midtown South-Flatiron-Union Sq 0.099 / 0.119; MN0604 East Midtown-Turtle Bay 0.098 / 0.119; MN0502 Midtown-Times Square 0.069 / 0.042; MN0602 Gramercy 0.066 / 0.075; MN0802 UES-Carnegie Hill 0.034 / 0.036; MN0203 West Village 0.020 / 0.022; MN0701 UWS-Lincoln Sq 0.013 / 0.022; MN0601 Stuy Town 0.009 / 0.006; MN0202 Greenwich Village 0.008 / 0.008; MN0801 UES-Lenox Hill 0.005 / 0.008 (L1 realised vs law 0.14 at 360 orders, down from 0.32 at 108 orders in round 2; the top three zones hold 58 % of the mass and received 54 % of the orders).

NYC restaurant top-10 (pooled; orders): WASABI SUSHI BENTO (Japanese) 5, RESTAURANT ASSOCIATES @ AMAZON JFK24 (American) 4, SKY PAVILION (Chinese) 3, YAKINIKU FUTAGO (Japanese) 3, HERALD SQUARE CAFE (American) 3, SOPHRA GRILL (Middle Eastern) 3, BROOKLYN DINER (American) 3, RESTAURANT 555 (Italian) 2, PANDA EXPRESS (Chinese) 2, YAMA (Japanese) 2 -- i.e. no restaurant receives more than 1.4 % of the 360 orders, against 12 orders (3.3 %) for the busiest synthetic node.

## 7. Solver statistics

| siting | method | n | arcs (mean / min / max) | binaries (mean / min / max) | rows (mean / max) | library build, s | model build, s | runtime, s (mean +/- CI / min / max) | MIP gap (max) | B&B nodes (mean / max) | status | MIP start accepted | start variant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | ilp | 10 | 556,582 / 452,675 / 729,139 | 556,621 / 452,714 / 729,178 | 52,878 / 65,707 | 1.44 | 2.28 | 47.8 +/- 8.0 / 34.3 / 64.1 | 0.0e+00 | 1.4 / 5 | 10 x OPTIMAL | 10 / 10 | baseline_round1 x3, default x7 |
| busiest | ilp_relaxed | 10 | 556,582 / 452,675 / 729,139 | 556,621 / 452,714 / 729,178 | 52,878 / 65,707 | 1.44 | 2.14 | 44.9 +/- 7.7 / 31.7 / 64.4 | 0.0e+00 | 3.0 / 21 | 10 x OPTIMAL | 10 / 10 | default x10 |
| grid | ilp | 10 | 549,226 / 451,186 / 720,006 | 549,265 / 451,225 / 720,045 | 51,951 / 64,778 | 1.45 | 2.28 | 44.9 +/- 7.3 / 28.1 / 59.0 | 0.0e+00 | 1.0 / 1 | 10 x OPTIMAL | 10 / 10 | baseline_round1 x2, default x8 |
| grid | ilp_relaxed | 10 | 549,226 / 451,186 / 720,006 | 549,265 / 451,225 / 720,045 | 51,951 / 64,778 | 1.45 | 2.27 | 44.5 +/- 7.2 / 29.7 / 58.8 | 5.6e-05 | 1.2 / 3 | 10 x OPTIMAL | 10 / 10 | default x10 |

Totals: **40 ILP solves, 40 OPTIMAL, 0 TIME_LIMIT, 0 SKIPPED_BUDGET** (and 20 baseline policy rows, status POLICY); mean 552,943 binaries (451,225 - 729,178), mean runtime 45.5 +/- 3.2 s (min 28.1, max 64.4 s; sum 30.4 min of solver time) against the 300 s limit at Threads 3; largest MIP gap 5.6e-05 (grid seed 6, relaxed; within tolerance); 37 of 40 solves closed at the root node with the baseline MIP start (max 21 nodes, busiest seed 7 relaxed); MIP start accepted in 40 / 40. Round-3 solves (seeds 3-9) took 47.6 +/- 3.4 s (max 64.4) against 40.6 +/- 7.1 s for the reused round-2 solves. Whole round-3 run: 25.3 min wall for 14 instances (2 h budget), all rows recorded. For scale, the synthetic `usd4h` family at the same size has 1.9 M arcs under the plan pruning; `PRUNING_NYC` cuts the NYC family to 0.55 M by allowing moves only into the 3 site nodes.

## 8. Figures (in `outputs/e8_round3/`)

- `map_seed0.png` -- kept from the script run (2026-10-12 22:25): nyc4h-busiest-seed0 in the rotated 150 m grid frame (axes in metres), DOHMH restaurants coloured by Kaggle cuisine, ACS zone-weight density with NTA labels, the seed's 32 restaurants and 36 customers, the `busiest` sites (stars) and `grid` sites (crosses), and the six ILP bike paths with q0 (round-2 ILP schedule, identical row).
- `gap_by_seed.png` -- **regenerated from `records.jsonl` for 10 seeds** (matplotlib Agg): headline gap per seed (dots, seed labels) with the mean (bar) and 95 % t-CI (whisker) for the written and relaxed ILP under both sitings; y axis `cost gap = 100 (baseline - ILP) / baseline [%]`.
- `cost_components.png` -- **regenerated for 10 seeds**: stacked mean components (27)-(32) per method and siting, y axis `mean cost over 10 seeds [USD, usd_sunk]`, totals annotated with the 95 % t-CI whisker beside each bar.
- `demand_comparison.png` -- kept from the script run (already built on the 10-seed `demand_comparison.json`): cuisine shares (Kaggle target vs NYC realised vs synthetic realised, %) and NTA customer shares (sampling law vs realised, %).

## 9. Anomalies and notes

1. **Provenance mix.** 18 of 60 rows (seeds 0-2) are copied from round 2 (`source = round2`); their totals equal `outputs/e8_nyc_fixed/rows.jsonl` exactly. The round-2 rows lack the `time_limit_used_s` / `threads` / `wall_s` / `n_vars` / `node_count` columns in their original form only where the column did not exist then (node counts are present for all 40 ILP rows); the Gurobi `Seed 0` parameter was set explicitly only for the round-3 rows (Gurobi's default seed is also 0).
2. **MIP-start fallback** (default R2.3 baseline schedule violated (18); `baseline_round1` injected instead) on 5 of 20 written-ILP solves: busiest/0, busiest/2, busiest/5, grid/0, grid/5. All accepted and verified OPTIMAL as fixed starts; the `baseline` rows still report the default policy.
3. **Baseline end-stock reports.** The baseline reports (18) violated in 4 of 20 runs (busiest 0, busiest 5, grid 0, grid 5) and (17) in 2 of 20 (busiest 2, busiest 5); `check_ok` is False for these 5 baseline rows. Reported, not priced, which makes the written-ILP gap conservative; the relaxed control moves the gap by at most 0.05 points.
4. **Coverage trade.** The ILP drops MORE orders than the baseline on 5 instances (busiest/0, busiest/6, grid/0, grid/6, grid/9; one order each), fewer on 8 and the same number on 7: it trades a dropped order (P = 30 USD) for response and lateness savings. Mean served share 85.8 % vs 83.9 % (busiest) / 85.3 % (grid).
5. **Stranded baseline bikes** (no feasible reposition / terminal under the policy) on 4 runs: busiest seed 5 (2 bikes), busiest seed 6 (1), grid seed 3 (1), grid seed 5 (1). The policy's cost is still priced with (9) reported; these runs are not outliers in the gap (20-26 %).
6. `served_share_servable` is populated only for the baseline rows in `results.csv` (empty for `ilp` / `ilp_relaxed`); the ILP values in section 2a were derived from `n_served` and `n_unservable` (fairness review F5 note carried over from round 2).
7. `queue_wait_slots` is larger for the ILP (mean 23.3 busiest / 21.5 grid, up to 59) than for the baseline (1.0 / 3.3): the ILP parks bikes at sites between jobs and those waiting arcs are counted by the metric; it is not a swap queue (sigma 1, 6-8 swaps per run).
8. **The relaxed ILP buys no electricity in 20 / 20 runs** (end full batteries 1-3 of 9, 31.1 / 22.7 stock-out slots on average): without end targets the 9 spare batteries alone cover the 4 h window; the written ILP charges 0.83 / 0.82 kWh to meet (17)-(18) at 0.28 / 0.26 USD. The battery side is still not binding.
9. The largest MIP gap recorded is 5.6e-5 (grid seed 6, relaxed) with status OPTIMAL (within Gurobi's MIPGap tolerance); all other solves report gap 0.
10. **Script report cosmetics, fixed in the rewritten `RESULTS.md`:** the abstract was in Chinese (rewritten in English); the interpretation's caveat list still said '3 seeds (CIs are wide)' although n = 10 (template text in `e8_nyc_fixed.write_results_md`); the closing line said 'all in `outputs/e8_nyc/`' (stale string at `experiments/e8_nyc_fixed.py` line 1046) although the files are in `outputs/e8_round3/`. The package itself was left untouched (read-only brief; E2u running in the background).
11. With n = 10 the half-widths (8.2 / 8.6 points) are about a quarter of the means; the seed-0 and seed-8 instances (gap 47-51 %) and seeds 2, 3, 6, 9 (18-25 %) span the range, so the spread is genuine demand variation (baseline lateness 15-450 USD), not solver noise (ILP totals vary by only 2.8 %).
12. `map_seed0.png` and `demand_comparison.png` were not regenerated (kept as written by the script at 22:25; the map needs the arc library of seed 0 and the demand figure already covers 10 seeds); `gap_by_seed.png` and `cost_components.png` were overwritten by the regenerated versions.

## 10. Interpretation (round 3 vs round 2)

Extending E8 from 3 to 10 seeds does not move the conclusion but makes it quotable: the headline gap is 31.8 +/- 8.2 % at the busiest-cell siting and 30.5 +/- 8.6 % at the grid-connected siting (round 2: 36.5 +/- 29.3 and 34.3 +/- 37.6), the half-width has fallen from larger-than-the-mean to about a quarter of it, the round-2 point estimates lie inside the new intervals, and the seven new seeds alone average 29.8 % / 28.9 %, so the first three seeds were on the optimistic side of a distribution that spans 18-51 %. The relaxed control gives 31.9 % / 30.6 %, within 0.03 points of the written model on every siting, confirming for all 10 seeds what round 2 showed for 3: none of the advantage is manufactured by the end-of-window targets, whose price in the optimum is 0.28-0.26 USD. The composition of the gap is unchanged from round 2 and still the opposite of round 1: lateness 59 %, response 35 %, unserved orders 6 % at the busiest siting (round 2: 61 / 36 / 2.4 %), because at P = 30 USD and w = 18 $/h both methods drop 5-6 of 36 orders and the ILP's lever is sequencing rather than coverage. The ILP keeps 1.5 late deliveries per run against 17.8 (busiest) / 18.4 (grid) for the nearest-rider FIFO policy, responds in 0.83 h instead of 1.07 h, rides 95 instead of 110 km, and buys a third of the electricity (0.83 vs 2.46 kWh), all with non-overlapping confidence intervals. The siting result is now statistically clean: the ILP optimum changes by at most 0.41 USD (0.063 %) on any seed, while the baseline swings between -9.1 % and +5.8 % with a mean of -1.6 +/- 3.6 % whose interval contains zero -- the coordinated schedule absorbs where the stations are, the myopic policy is merely less predictable, and the headline gap difference between sitings (-1.3 +/- 2.6 points) is not significant. The ILP total is remarkably stable across seeds (coefficient of variation 2.8 %, 644-706 USD) while the baseline varies by 21 % (804-1375 USD) and the per-instance gap tracks the baseline's lateness at r = 0.98: the value of coordination on this instance is essentially the lateness the greedy policy incurs on bad demand draws. Charging is still not binding: the relaxed ILP never buys a kWh in 20 runs and the written ILP charges only to satisfy (17)-(18), so with 9 spare batteries for 6 bikes over 4 h E8 continues to say nothing about station queues, charging slots or grid limits, exactly as in round 2. The demand side has improved in the ways R2.4 intended and the larger sample sharpens the picture: cuisine shares are within L1 0.15 of the Kaggle target (synthetic 0.28; round 2 at 108 orders: 0.20 vs 0.31), 13 of 14 cuisine classes and all 13 NTAs with grid nodes are hit, the realised zone shares are within L1 0.14 of the ACS sampling law (0.32 at 108 orders), and orders spread over about 32 restaurants per seed with a top-10 share of 0.38 against 1.0 for the 8 synthetic restaurants. Trip geometry is still the same in both families (mean restaurant -> customer route 1.80 vs 1.86 km) because both live on the same rotated 150 m grid with the same speed and energy physics; the semi-real instance changes where the demand sits, not how far bikes ride. Computationally the family remains the cheapest of the programme: 553 k binaries per ILP, 40 / 40 solves optimal in 28-64 s with 37 of them closed at the root node, 25 min of wall time for the 7 new seeds, so the result is limited by the model's realism and not by the solver. Three caveats bound the claim as before: the geometry is synthetic (rotated grid, synthetic elevation and signals, one shortest grid route per pair), 26 % of the box's restaurants are unreachable by the cuisine mapping, and `PRUNING_NYC` restricts only the ILP, so each ILP total is an upper bound on the written optimum and each gap a lower bound on the coordination value -- the lossless `--targets default` probe is the one follow-up that would turn the lower bound into an exact value, and at 10 seeds it is the only thing missing from a citable E8 result.
