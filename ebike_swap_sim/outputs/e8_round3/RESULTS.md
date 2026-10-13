# E8 round 3 -- provenance

Rows by method and source (round2 = reused rows of outputs/e8_nyc_fixed, seeds 0-2; round3 = seeds 3-9 solved here, Threads 3, Seed 0, TimeLimit 300 s):

| method | source | n |
|---|---|---|
| baseline | round2 | 6 |
| baseline | round3 | 14 |
| ilp | round2 | 6 |
| ilp | round3 | 14 |
| ilp_relaxed | round2 | 6 |
| ilp_relaxed | round3 | 14 |

# E8 -- NYC semi-real instance (DOHMH restaurants, ACS zone weights, real site coordinates on the synthetic grid)

## Summary (English rewrite of the script's original Chinese abstract)

This experiment compares the round-2 baseline policy, the E2 integer program (rho 0.5, R_end 1) and the relaxed-end-target ILP control on the R2.4 semi-real New York instance (Midtown/Chelsea/Flatiron study box; real DOHMH restaurants, ACS 2020-24 literature-formula zone weights and real candidate-site coordinates projected onto the synthetic 150 m grid) with 6 bikes, 36 orders, 17:00-21:00 (H = 48), usd_sunk USD costs and 10 random seeds. With the sites in the three busiest restaurant cells, the ILP's total-cost reduction relative to the baseline ((baseline - ILP) / baseline) averages 31.8 % (95 % t half-width 8.2, n = 10) and the relaxed control 31.9 %; the ILP reached a proven optimum in 20 / 20 solves (Threads 3, 300 s limit). Moving the three sites to the Citi-Bike-style grid-connected landmarks (8th Ave / W 34th St, Union Square, Grand Central) changes the mean baseline cost by -1.6 % and the ILP by 0.0 %, and the ILP's relative advantage there is 30.5 % (half-width 8.6), so siting affects both methods but does not change the conclusion. Compared with the synthetic usd4h family, the semi-real instance's cuisine shares are closer to the Kaggle target (L1 0.15 vs 0.28), customers fall in [11, 8, 9, 9, 9, 11, 9, 10, 10, 9] NTAs and orders are spread over about 32 restaurants (synthetic: only 8), but the mean restaurant-to-customer trip of 1.80 km is close to the synthetic 1.86 km. Geometry caveat: the road network is still the synthetic grid (rotated 29 degrees, 150 m blocks), elevation and traffic signals are synthetic, and all distances and energy use come from that synthetic geometry rather than from real roads.

## Setup

Family `nyc4h` (`experiments/common.py`, builder `data_nyc.make_nyc_instance`): 6 bikes, 36 orders (1.5 orders per bike-hour), window 17:00-21:00 (H = 48 slots of 5 min), L = 12 levels of 50 Wh, costs `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30.0, w 18.0 $/h, v 36.0 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h site), q_res 1, rho 0.5, R_end 1. Three co-located sites (B 3, C 2, K 8, M 1, sigma 1, P 4 kW, group 8 kW / 6 kW 18-20 h). Study box lat 40.735-40.77, lon -74.005--73.965 (34 x 35 grid nodes of 150 m). Restaurants: 4607 usable DOHMH rows in the box mapped to the Kaggle cuisines (`data_nyc.CUISINE_MAP`), sampled by Kaggle share within 2.5 km of the customer with Zipf s = 1 ranks. **Zone weights: `acs_2020_24_literature`** (NTA2020; 15 NTAs intersect the box, 13 contain grid nodes; the literature formula on the ACS 2020-24 tables, no fallback). Seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; sitings `busiest` = the three busiest restaurant cells (sites [[13, 14], [17, 13], [17, 19]], lat/lon [[40.7513, -73.9922], [40.7475, -73.9869], [40.7545, -73.9817]]) and `grid` = 8th Ave / W 34th St, Union Square, Grand Central snapped to the grid (sites [[12, 15], [19, 4], [20, 19]]). Pruning `common.PRUNING_NYC` (moves only into the 3 site nodes, tau_max 4, start_slack 6, reachable pruning): 552,904 arcs on average. **This pruning restricts the ILP but not the policy** (fairness review F2): the baseline repositions only to swap sites and starts deliveries in place, so it loses nothing, whereas the ILP loses pre-positioning moves towards restaurants / customers (tau_max never binds on nyc4h: every customer -> restaurant pair is within 4 slots). The ILP totals below are therefore UPPER bounds on the written E2 optimum and the gaps LOWER bounds on the coordination value; no lossless probe exists for these targets yet (`--targets default` runs it). Release times follow the R2.2 block profile as a step function (`meta['hourly_profile_used']['kind']` = `block_step`, units review F1), the same object as the synthetic usd4h family. Restaurant supply: 26 % of the usable DOHMH rows in the box map to the unreachable `other` class (cafes, bakeries, desserts, juice; units review F3, declared assumption). Demand hash per (seed, siting): `demand_md5` column (orders, q0, H, L; identical across sitings by assertion). Methods: `baseline` (R2.3 defaults), `ilp` (written E2 model, baseline as verified MIP start via `common.feasible_mip_start`), `ilp_relaxed` (`common.relax_end_targets`: rho 0 and R_end 0 -- the fair control). Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 300 s. Wall time 25.3 min.

**Geometry caveat (R2.4):** Semi-real NYC instance: real DOHMH restaurants, real NTA zone weights and real candidate-site coordinates are projected onto the synthetic 150 m GridNetwork (local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, rotated by -29 deg to the Manhattan street-grid azimuth and snapped to 150 m blocks inside the study box); no real road network is used, and elevation and traffic signals remain synthetic.

## Headline

**Busiest-cell siting: ILP vs baseline gap = (baseline - ILP) / baseline = 31.8 % (95 % t-CI +/- 8.2, n = 10); relaxed-target ILP 31.9 % (+/- 8.2).** Grid-connected siting: 30.5 % (+/- 8.6) and 30.6 % (+/- 8.6). Mean totals (busiest): baseline 1013.7, ILP 669.9, relaxed 669.6 USD; served share 84 % vs 86 % vs 86 %. ILP solved to optimality in 20 of 20 runs (relaxed 20 of 20); MIP start accepted in 20 / 20 (variants injected: {'baseline_round1': 5, 'default': 15}) and 20 / 20 for the relaxed model; the baseline reports (18) in 4 and (17) in 2 of 20 runs.

## Per instance (both sitings): totals, both gap conventions, solver and start status

| siting | seed | n_arcs | baseline_total | baseline_unserved | baseline_km | baseline_swaps | baseline_families | ilp_total | ilp_status | ilp_gap | ilp_runtime_s | ilp_unserved | ilp_km | ilp_swaps | mip_start_variant | mip_start_accepted | relaxed_total | relaxed_status | relaxed_gap | relaxed_runtime_s | relaxed_unserved | relaxed_start_accepted | gap_vs_baseline_pct | gap_vs_ilp_pct | gap_relaxed_vs_baseline_pct | ilp_minus_relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | 0 | 729139 | 1374.68 | 5 | 119.25 | 9 | {"(18)": 1} | 706.08 | OPTIMAL | 0 | 60.03 | 6 | 90 | 6 | baseline_round1 | True | 705.87 | OPTIMAL | 0 | 55.46 | 6 | True | 48.64 | 94.69 | 48.65 | 0.21 |
| busiest | 1 | 530382 | 1043.48 | 6 | 110.85 | 6 | {} | 671.51 | OPTIMAL | 0 | 34.27 | 5 | 102.15 | 6 | default | True | 671.33 | OPTIMAL | 0 | 31.73 | 5 | True | 35.65 | 55.39 | 35.66 | 0.18 |
| busiest | 2 | 511370 | 882.69 | 6 | 106.35 | 8 | {"(17)": 1} | 661.16 | OPTIMAL | 0 | 36.66 | 5 | 90.90 | 6 | baseline_round1 | True | 660.91 | OPTIMAL | 0 | 36.32 | 5 | True | 25.10 | 33.51 | 25.13 | 0.25 |
| busiest | 3 | 452675 | 833.00 | 8 | 94.20 | 6 | {} | 675.21 | OPTIMAL | 0 | 51.53 | 5 | 95.10 | 6 | default | True | 674.95 | OPTIMAL | 0 | 44.11 | 5 | True | 18.94 | 23.37 | 18.97 | 0.27 |
| busiest | 4 | 506255 | 1089.28 | 7 | 116.40 | 6 | {} | 683.23 | OPTIMAL | 0 | 39.29 | 5 | 111.45 | 7 | default | True | 682.94 | OPTIMAL | 0 | 32.32 | 5 | True | 37.28 | 59.43 | 37.30 | 0.28 |
| busiest | 5 | 544674 | 889.26 | 4 | 111.90 | 8 | {"(17)": 1, "(18)": 1} | 657.34 | OPTIMAL | 0 | 49.25 | 4 | 94.20 | 8 | baseline_round1 | True | 656.87 | OPTIMAL | 0 | 44.58 | 4 | True | 26.08 | 35.28 | 26.13 | 0.46 |
| busiest | 6 | 523580 | 810.24 | 4 | 103.50 | 6 | {} | 646.19 | OPTIMAL | 0 | 34.84 | 5 | 91.05 | 6 | default | True | 645.96 | OPTIMAL | 0 | 37.19 | 5 | True | 20.25 | 25.39 | 20.28 | 0.23 |
| busiest | 7 | 530492 | 1080.27 | 8 | 103.80 | 6 | {} | 680.14 | OPTIMAL | 0 | 47.69 | 6 | 97.65 | 7 | default | True | 679.79 | OPTIMAL | 0 | 49.86 | 6 | True | 37.04 | 58.83 | 37.07 | 0.36 |
| busiest | 8 | 628238 | 1330.17 | 7 | 110.25 | 7 | {} | 673.92 | OPTIMAL | 0 | 64.05 | 7 | 84.45 | 6 | default | True | 673.70 | OPTIMAL | 0 | 64.39 | 7 | True | 49.34 | 97.38 | 49.35 | 0.21 |
| busiest | 9 | 609017 | 803.90 | 3 | 122.70 | 9 | {} | 643.75 | OPTIMAL | 0 | 59.99 | 3 | 94.50 | 7 | default | True | 643.41 | OPTIMAL | 0 | 53.04 | 3 | True | 19.92 | 24.88 | 19.96 | 0.34 |
| grid | 0 | 720006 | 1338.39 | 5 | 115.65 | 9 | {"(18)": 1} | 706.16 | OPTIMAL | 0 | 54.21 | 6 | 90.60 | 6 | baseline_round1 | True | 705.94 | OPTIMAL | 0 | 51.04 | 6 | True | 47.24 | 89.53 | 47.25 | 0.21 |
| grid | 1 | 525584 | 1085.71 | 7 | 112.65 | 7 | {} | 671.76 | OPTIMAL | 0 | 28.09 | 5 | 104.25 | 6 | default | True | 671.58 | OPTIMAL | 0 | 34.12 | 5 | True | 38.13 | 61.62 | 38.14 | 0.18 |
| grid | 2 | 490210 | 802.70 | 5 | 104.40 | 7 | {} | 661.01 | OPTIMAL | 0 | 35.67 | 5 | 88.80 | 7 | default | True | 660.73 | OPTIMAL | 0 | 29.66 | 5 | True | 17.65 | 21.44 | 17.69 | 0.28 |
| grid | 3 | 451186 | 827.79 | 7 | 99.60 | 6 | {} | 675.05 | OPTIMAL | 0 | 44.08 | 5 | 93.90 | 6 | default | True | 674.84 | OPTIMAL | 0 | 58.80 | 5 | True | 18.45 | 22.63 | 18.48 | 0.21 |
| grid | 4 | 497937 | 1009.01 | 6 | 123 | 6 | {} | 683.43 | OPTIMAL | 0 | 54.12 | 5 | 112.65 | 7 | default | True | 683.16 | OPTIMAL | 0 | 36.49 | 5 | True | 32.27 | 47.64 | 32.29 | 0.27 |
| grid | 5 | 532829 | 838.62 | 4 | 116.10 | 8 | {"(18)": 1} | 656.93 | OPTIMAL | 0 | 36.85 | 4 | 92.70 | 6 | baseline_round1 | True | 656.69 | OPTIMAL | 0 | 39.03 | 4 | True | 21.67 | 27.66 | 21.69 | 0.23 |
| grid | 6 | 537730 | 814.60 | 4 | 114.15 | 7 | {} | 646.57 | OPTIMAL | 0 | 38.31 | 5 | 93.45 | 7 | default | True | 646.28 | OPTIMAL | 0.00 | 40.60 | 5 | True | 20.63 | 25.99 | 20.66 | 0.28 |
| grid | 7 | 521696 | 1030.57 | 6 | 102.15 | 7 | {} | 680.04 | OPTIMAL | 0 | 44.86 | 6 | 96.75 | 7 | default | True | 679.68 | OPTIMAL | 0 | 45.97 | 6 | True | 34.01 | 51.55 | 34.05 | 0.36 |
| grid | 8 | 619426 | 1373.91 | 7 | 114.60 | 6 | {} | 674.21 | OPTIMAL | 0 | 59.03 | 7 | 86.85 | 6 | default | True | 673.99 | OPTIMAL | 0 | 57.54 | 7 | True | 50.93 | 103.78 | 50.94 | 0.21 |
| grid | 9 | 595659 | 850.14 | 2 | 135.60 | 8 | {} | 644.00 | OPTIMAL | 0 | 53.96 | 3 | 96.90 | 7 | default | True | 643.59 | OPTIMAL | 0 | 52.25 | 3 | True | 24.25 | 32.01 | 24.30 | 0.41 |

`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP; `gap_relaxed_vs_baseline_pct` uses the relaxed-target ILP (rho 0, R_end 0); `ilp_minus_relaxed` = price of the end targets (17)-(18) in the optimum; `baseline_families` = constraint families the policy *reports* (not enforced).

## Cost (26) and components (27)-(32): mean over seeds per siting and method (USD)

| siting | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 1013.70 | 39.57 | 0.79 | 13.19 | 174 | 578.85 | 207.30 | 0 |
| busiest | ilp | 669.85 | 39.57 | 0.26 | 11.42 | 153 | 459.60 | 6 | 0 |
| busiest | ilp_relaxed | 669.57 | 39.57 | 0 | 11.40 | 153 | 459.60 | 6 | 0 |
| grid | baseline | 997.14 | 39.57 | 0.72 | 13.65 | 159 | 583.20 | 201 | 0 |
| grid | ilp | 669.91 | 39.57 | 0.26 | 11.48 | 153 | 459.60 | 6 | 0 |
| grid | ilp_relaxed | 669.65 | 39.57 | 0 | 11.48 | 153 | 459.60 | 6 | 0 |

## Service / operations metrics: mean over seeds

| siting | method | served_share | n_unserved | mean_response_h | max_response_h | mean_lateness_h | n_late | bike_km | n_swaps | queue_wait_slots | kwh_purchased | peak_kw_sites | transfers_used | end_full_total | viol_17 | viol_18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 0.839 | 5.800 | 1.067 | 1.425 | 0.192 | 17.800 | 109.920 | 7.100 | 1 | 2.456 | 2.533 | 0 | 5.400 | 0.200 | 0.200 |
| busiest | ilp | 0.858 | 5.100 | 0.826 | 1.033 | 0.005 | 1.500 | 95.145 | 6.500 | 23.300 | 0.828 | 1.200 | 0 | 5 | 0 | 0 |
| busiest | ilp_relaxed | 0.858 | 5.100 | 0.826 | 1.033 | 0.005 | 1.500 | 95.025 | 7.600 | 25.600 | 0 | 0 | 0 | 1.400 | 0 | 0 |
| grid | baseline | 0.853 | 5.300 | 1.058 | 1.408 | 0.184 | 18.400 | 113.790 | 7.100 | 3.300 | 2.250 | 2.200 | 0 | 5.300 | 0 | 0.100 |
| grid | ilp | 0.858 | 5.100 | 0.826 | 1.033 | 0.005 | 1.500 | 95.685 | 6.500 | 21.500 | 0.817 | 1.467 | 0 | 5 | 0 | 0 |
| grid | ilp_relaxed | 0.858 | 5.100 | 0.826 | 1.033 | 0.005 | 1.500 | 95.655 | 7.100 | 15.600 | 0 | 0 | 0 | 1.900 | 0 | 0 |

`viol_17` / `viol_18` = end-stock shortfalls reported by the baseline (0 for the ILP by construction); `transfers_used` is 0 everywhere (no services in the NYC family, E = {}).

## Solver statistics (mean / max over seeds)

| siting | method | n_arcs_mean | n_arcs_max | n_binaries_mean | n_binaries_max | n_rows_mean | n_rows_max | build_time_s_mean | build_time_s_max | runtime_s_mean | runtime_s_max | gap_mean | gap_max | node_count_mean | node_count_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | ilp | 556582.200 | 729139 | 556621.200 | 729178 | 52878 | 65707 | 2.277 | 3.042 | 47.761 | 64.055 | 0 | 0 | 1.400 | 5 |
| busiest | ilp_relaxed | 556582.200 | 729139 | 556621.200 | 729178 | 52878 | 65707 | 2.145 | 2.486 | 44.899 | 64.386 | 0 | 0 | 3 | 21 |
| grid | ilp | 549226.300 | 720006 | 549265.300 | 720045 | 51950.600 | 64778 | 2.281 | 2.783 | 44.917 | 59.029 | 0 | 0 | 1 | 1 |
| grid | ilp_relaxed | 549226.300 | 720006 | 549265.300 | 720045 | 51950.600 | 64778 | 2.267 | 2.971 | 44.550 | 58.798 | 0.000 | 0.000 | 1.200 | 3 |

## Siting sensitivity: grid-connected variant minus busiest-cell siting (same orders, bikes' levels and ranks per seed)

| seed | baseline_busiest | baseline_grid | baseline_grid_minus_busiest | baseline_grid_minus_busiest_pct | ilp_busiest | ilp_grid | ilp_grid_minus_busiest | ilp_grid_minus_busiest_pct | ilp_relaxed_busiest | ilp_relaxed_grid | ilp_relaxed_grid_minus_busiest | ilp_relaxed_grid_minus_busiest_pct | gap_busiest_pct | gap_grid_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1374.68 | 1338.39 | -36.29 | -2.64 | 706.08 | 706.16 | 0.07 | 0.01 | 705.87 | 705.94 | 0.07 | 0.01 | 48.64 | 47.24 |
| 1 | 1043.48 | 1085.71 | 42.23 | 4.05 | 671.51 | 671.76 | 0.25 | 0.04 | 671.33 | 671.58 | 0.25 | 0.04 | 35.65 | 38.13 |
| 2 | 882.69 | 802.70 | -79.98 | -9.06 | 661.16 | 661.01 | -0.15 | -0.02 | 660.91 | 660.73 | -0.18 | -0.03 | 25.10 | 17.65 |
| 3 | 833.00 | 827.79 | -5.21 | -0.63 | 675.21 | 675.05 | -0.16 | -0.02 | 674.95 | 674.84 | -0.11 | -0.02 | 18.94 | 18.45 |
| 4 | 1089.28 | 1009.01 | -80.28 | -7.37 | 683.23 | 683.43 | 0.20 | 0.03 | 682.94 | 683.16 | 0.22 | 0.03 | 37.28 | 32.27 |
| 5 | 889.26 | 838.62 | -50.64 | -5.69 | 657.34 | 656.93 | -0.41 | -0.06 | 656.87 | 656.69 | -0.18 | -0.03 | 26.08 | 21.67 |
| 6 | 810.24 | 814.60 | 4.37 | 0.54 | 646.19 | 646.57 | 0.38 | 0.06 | 645.96 | 646.28 | 0.32 | 0.05 | 20.25 | 20.63 |
| 7 | 1080.27 | 1030.57 | -49.70 | -4.60 | 680.14 | 680.04 | -0.11 | -0.02 | 679.79 | 679.68 | -0.11 | -0.02 | 37.04 | 34.01 |
| 8 | 1330.17 | 1373.91 | 43.74 | 3.29 | 673.92 | 674.21 | 0.29 | 0.04 | 673.70 | 673.99 | 0.29 | 0.04 | 49.34 | 50.93 |
| 9 | 803.90 | 850.14 | 46.25 | 5.75 | 643.75 | 644.00 | 0.25 | 0.04 | 643.41 | 643.59 | 0.18 | 0.03 | 19.92 | 24.25 |

## Demand pattern: NYC semi-real vs synthetic `usd4h` (same seeds)

| descriptor | NYC semi-real | synthetic usd4h |
|---|---|---|
| orders pooled | 360 | 360 |
| restaurants available | 4607 (DOHMH rows in box) | 8 (synthetic) |
| distinct restaurants hit per seed | [32, 32, 33, 34, 32, 32, 32, 32, 34, 32] | [8, 8, 8, 8, 7, 8, 7, 8, 8, 7] |
| top-10 restaurants' share of orders per seed | [0.39, 0.39, 0.36, 0.33, 0.39, 0.39, 0.39, 0.39, 0.33, 0.39] | [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] |
| top-3 restaurants' share per seed | [0.19, 0.19, 0.17, 0.14, 0.17, 0.19, 0.17, 0.19, 0.14, 0.17] | [0.64, 0.61, 0.58, 0.67, 0.69, 0.56, 0.64, 0.64, 0.61, 0.64] |
| customer zones hit per seed | [11, 8, 9, 9, 9, 11, 9, 10, 10, 9] (NTA-2020) | [13, 13, 14, 12, 12, 13, 14, 14, 14, 14] (synthetic zones of 16) |
| mean restaurant -> customer route (km) per seed | [1.79, 1.79, 1.7, 1.79, 2.1, 1.76, 1.73, 1.74, 1.94, 1.7] | [1.67, 1.9, 1.74, 2.02, 1.66, 1.89, 1.95, 1.82, 2.0, 1.98] |
| max route (km) per seed | [3.3, 3.3, 3.3, 3.3, 3.3, 3.3, 3.15, 3.45, 3.3, 3.45] | [4.2, 4.05, 3.45, 4.35, 3.9, 4.2, 4.2, 4.2, 3.6, 4.95] |
| mean prep (min) per seed | [29.6, 29.9, 29.7, 29.4, 29.4, 29.2, 28.1, 28.9, 27.2, 30.3] | [29.3, 29.9, 28.6, 29.0, 28.9, 29.3, 28.5, 30.6, 30.1, 29.3] |
| promise after ready (slots) | 5 | 5 |
| L1 distance of cuisine shares to Kaggle target | 0.149 | 0.277 |
| zone weights | acs_2020_24_literature | synthetic Dirichlet demographics |


Cuisine shares (pooled over seeds):

| cuisine | kaggle_share | nyc_share | synthetic_share |
|---|---|---|---|
| American | 0.308 | 0.311 | 0.369 |
| Japanese | 0.248 | 0.225 | 0.292 |
| Italian | 0.157 | 0.192 | 0.189 |
| Chinese | 0.113 | 0.092 | 0.114 |
| Mexican | 0.041 | 0.047 | 0.036 |
| Indian | 0.038 | 0.053 | 0 |
| Middle Eastern | 0.026 | 0.036 | 0 |
| Mediterranean | 0.024 | 0.017 | 0 |
| Thai | 0.010 | 0.003 | 0 |
| French | 0.009 | 0.003 | 0 |
| Southern | 0.009 | 0.014 | 0 |
| Korean | 0.007 | 0.006 | 0 |
| Spanish | 0.006 | 0 | 0 |
| Vietnamese | 0.004 | 0.003 | 0 |

NYC customer zone shares (sampling law = ACS zone-weight mass of the grid nodes in the box; realised = orders):

| zone | name | sampling_law_share | realised_share |
|---|---|---|---|
| MN0603 | Murray Hill-Kips Bay | 0.203 | 0.175 |
| MN0402 | Hell's Kitchen | 0.200 | 0.186 |
| MN0401 | Chelsea-Hudson Yards | 0.178 | 0.181 |
| MN0501 | Midtown South-Flatiron-Union Square | 0.099 | 0.119 |
| MN0604 | East Midtown-Turtle Bay | 0.098 | 0.119 |
| MN0502 | Midtown-Times Square | 0.069 | 0.042 |
| MN0602 | Gramercy | 0.066 | 0.075 |
| MN0802 | Upper East Side-Carnegie Hill | 0.034 | 0.036 |
| MN0203 | West Village | 0.020 | 0.022 |
| MN0701 | Upper West Side-Lincoln Square | 0.013 | 0.022 |
| MN0601 | Stuyvesant Town-Peter Cooper Village | 0.009 | 0.006 |
| MN0202 | Greenwich Village | 0.008 | 0.008 |
| MN0801 | Upper East Side-Lenox Hill-Roosevelt Island | 0.005 | 0.008 |

NYC restaurant top-10 (pooled over seeds; name (cuisine): orders): WASABI SUSHI BENTO (Japanese) 5; RESTAURANT ASSOCIATES @ AMAZON JFK24 (American) 4; SKY PAVILION (Chinese) 3; YAKINIKU FUTAGO (Japanese) 3; HERALD SQUARE CAFE (American) 3; SOPHRA GRILL (Middle Eastern) 3; BROOKLYN DINER (American) 3; RESTAURANT 555 (Italian) 2; PANDA EXPRESS (Chinese) 2; YAMA (Japanese) 2.

Synthetic restaurant top-10 (node (cuisine): orders): (6, 12) (American) 12; (7, 14) (Italian) 11; (12, 4) (Japanese) 10; (9, 14) (Italian) 10; (10, 10) (American) 10; (10, 18) (American) 10; (13, 1) (Italian) 9; (6, 9) (Japanese) 9; (7, 11) (Japanese) 9; (7, 0) (American) 8.

## Interpretation

On the semi-real Midtown instance the coordinated ILP lowers the baseline's cost by 31.8 % (+/- 8.2) with the written end targets and by 31.9 % (+/- 8.2) under the fair relaxed control, so the advantage seen on the synthetic usd4h family (seed 0: 615 vs 733 USD, 16 %; seed 1: 660 vs 973, 32 %, `outputs/r2_probe/`) survives real restaurant and customer geography of the same size. The gap is made of unserved orders (21 USD of the 343.8 USD mean difference at the busiest siting), response (119.2), lateness (201.3) and travel (1.8); electricity (0.52) is negligible at pi = 0.32 $/kWh and there are no transfers (E = {}). The baseline serves 84 % of the orders against 86 % for the ILP, with mean response 1.07 h vs 0.83 h and 109.9 vs 95.1 km; with P = 30.0 USD and w = 18.0 $/h a dropped order costs about as much as 1.7 h of waiting, so the ILP trades response time for coverage. Swaps: baseline 7.1 vs ILP 6.5 per run with 2.46 vs 0.83 kWh purchased; the ILP meets (17)-(18) at a price of 0.28 USD on average (written minus relaxed optimum), while the baseline ends with (18) violated in 4 of 20 runs (DEMAND_AWARE charging covers only the per-site reserve (17), DECISIONS R2 notes). Siting matters for both methods: moving the three sites to the grid-connected landmarks changes the baseline by -1.6 % and the ILP by 0.0 % on average (per seed ILP: [0.0, 0.0, -0.0, -0.0, 0.0, -0.1, 0.1, -0.0, 0.0, 0.0] %), and the ILP's relative advantage is 30.5 % there (+/- 8.6); Union Square sits on the southern edge of the box, so bikes starting there ride farther to the Midtown demand mass, which the ILP absorbs better than the nearest-rider policy only when a dropped order is at stake. Demand realism: the realised cuisine mix of the NYC instances is within L1 = 0.15 of the Kaggle order shares (synthetic 0.28, where only 8 restaurants exist and some cuisines have none), the customers fall in [11, 8, 9, 9, 9, 11, 9, 10, 10, 9] NTAs with the top three zones (MN0603, MN0402, MN0401: 20 %, 20 %, 18 % of the sampling mass) receiving 54 % of the orders (L1 realised-vs-law 0.14 over 13 zones at 36 orders per seed), and orders spread over about 32 distinct restaurants per seed (top-10 share 0.38) against 8 fixed synthetic restaurants (top-10 share 1.0). Trip geometry is similar in both families (mean restaurant -> customer route 1.80 vs 1.86 km) because both live on the same 150 m grid with the same speed / energy physics; the semi-real instance only changes *where* the mass sits (Chelsea / Hudson Yards / Midtown South NTAs) and how concentrated the restaurants are. Solver: 552,904 arcs under PRUNING_NYC (versus 1.9 M for usd4h at the same size) because moves are allowed only into the three site nodes; the ILPs solved in 46 s on average (max 64 s), 40 of 40 runs proven optimal within 300 s at Threads 3. Caveats: synthetic road geometry (rotated grid, synthetic elevation and signals, one shortest grid route per pair), 10 seeds (CIs now +/- 8-9 points; the template text of round 2 said 3 seeds), 6 bikes / 36 orders (the R2.2 nominal 10 / 60 was not solved here), and the baseline's (17)/(18) violations are reported, not priced -- the relaxed control is the fair comparison. PRUNING_NYC binds only the ILP (no repositioning to non-site nodes), so every ILP total is an upper bound on the written optimum and every gap a lower bound on the coordination value (fairness review F2); the `other` cuisine class (26 % of the box's restaurants) is unreachable by construction (units review F3).

## Anomalies and notes

- The default baseline schedule violated (18) and a fallback variant was injected as start on nyc4h-busiest-seed0 (baseline_round1), nyc4h-grid-seed0 (baseline_round1), nyc4h-busiest-seed2 (baseline_round1), nyc4h-busiest-seed5 (baseline_round1), nyc4h-grid-seed5 (baseline_round1) (baseline columns still describe the default policy).
- Structurally unservable orders (no delivery arc; both methods pay P, raw drop rates inflated identically): nyc4h-busiest-seed1 (1), nyc4h-grid-seed1 (1), nyc4h-busiest-seed2 (2), nyc4h-grid-seed2 (2), nyc4h-busiest-seed3 (1), nyc4h-grid-seed3 (1), nyc4h-busiest-seed4 (3), nyc4h-grid-seed4 (3), nyc4h-busiest-seed5 (1), nyc4h-grid-seed5 (1), nyc4h-busiest-seed6 (1), nyc4h-grid-seed6 (1), nyc4h-busiest-seed7 (3), nyc4h-grid-seed7 (3), nyc4h-busiest-seed8 (1), nyc4h-grid-seed8 (1); `served_share_servable` is the share relative to the servable orders (fairness review F5).
- Baseline bikes stranded (no feasible reposition / terminal) on nyc4h-grid-seed3 (1), nyc4h-busiest-seed5 (2), nyc4h-grid-seed5 (1), nyc4h-busiest-seed6 (1).
- Sites are placed by node, several facilities could share a node if two sitings coincided (they do not here); the grid-connected coordinates are my choice of three well-known landmarks, not Citi Bike station records.
- `data_nyc.make_nyc_instance` draws the bikes' start nodes round robin over the sites, so the two sitings of a seed differ only in the site nodes and the bikes' starting positions; orders, prep times, restaurant ranks and q0 are identical.

## Figures

- `map_seed0.png`
- `cost_components.png`
- `gap_by_seed.png`
- `demand_comparison.png`

Files: `results.csv` (one row per instance x method), `per_instance.csv`, `siting.csv`, `demand_comparison.json`, `instances/*.json` (byte-identical inputs of every method), `wall_time.json`; all in `outputs/e8_round3/` (the script's template printed the stale path `outputs/e8_nyc/`).
