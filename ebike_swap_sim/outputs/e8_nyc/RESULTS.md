# E8 -- NYC semi-real instance (DOHMH restaurants, ACS zone weights, real site coordinates on the synthetic grid)

## Summary

This experiment compares the round-2 baseline policy, the E2 integer program (rho 0.5, R_end 1) and the ILP control with relaxed terminal targets on the R2.4 semi-real NYC instance (Midtown/Chelsea/Flatiron study box, real DOHMH restaurants, ACS 2020-24 literature-formula zone weights, real candidate site coordinates projected onto the synthetic 150 m grid) with 6 bikes, 36 orders, 17:00-21:00 (H = 48), usd_sunk USD costs and 3 random seeds. With the sites placed on the busiest restaurant cells, the ILP's total-cost reduction relative to the baseline ((baseline - ILP)/baseline) averages 27.3 % (95 % t half-width 29.4, n = 3); the relaxed control gives 27.3 %; the ILP reached optimality in 6/6 solves (Threads 3, time limit 300 s). Moving the three sites to Citi Bike-style 'grid' landmarks (8th Ave/W 34th, Union Sq, Grand Central) changes the mean baseline cost by -0.1 % and the ILP cost by 0.1 %, and the ILP's relative advantage is 26.5 % (half-width 37.1), i.e. siting affects both methods but does not change the conclusion. Compared with the synthetic usd4h family, the semi-real instance's cuisine shares are closer to the Kaggle target (L1 deviation 0.29 vs 0.31), customers fall in [9, 10, 9] NTAs and the restaurants are spread over about 32 establishments (the synthetic family has only 8), but the mean restaurant-to-customer distance 1.91 km is close to the synthetic family's 1.77 km. Geometry caveat: the road network is still the synthetic grid (rotated 29 degrees, 150 m blocks), elevation and traffic signals are synthetic values, and all distances / energy use come from that synthetic geometry rather than real roads.

## Setup

Family `nyc4h` (`experiments/common.py`, builder `data_nyc.make_nyc_instance`): 6 bikes, 36 orders (1.5 orders per bike-hour), window 17:00-21:00 (H = 48 slots of 5 min), L = 12 levels of 50 Wh, costs `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30.0, w 18.0 $/h, v 36.0 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h site), q_res 1, rho 0.5, R_end 1. Three co-located sites (B 3, C 2, K 8, M 1, sigma 1, P 4 kW, group 8 kW / 6 kW 18-20 h). Study box lat 40.735-40.77, lon -74.005--73.965 (34 x 35 grid nodes of 150 m). Restaurants: 4607 usable DOHMH rows in the box mapped to the Kaggle cuisines (`data_nyc.CUISINE_MAP`), sampled by Kaggle share within 2.5 km of the customer with Zipf s = 1 ranks. **Zone weights: `acs_2020_24_literature`** (NTA2020; 15 NTAs intersect the box, 13 contain grid nodes; the literature formula on the ACS 2020-24 tables, no fallback). Seeds [0, 1, 2]; sitings `busiest` = the three busiest restaurant cells (sites [[13, 14], [17, 13], [17, 19]], lat/lon [[40.7513, -73.9922], [40.7475, -73.9869], [40.7545, -73.9817]]) and `grid` = 8th Ave / W 34th St, Union Square, Grand Central snapped to the grid (sites [[12, 15], [19, 4], [20, 19]]). Pruning `common.PRUNING_NYC` (moves only into the 3 site nodes, tau_max 4, start_slack 6, reachable pruning): 654,181 arcs on average. Methods: `baseline` (R2.3 defaults), `ilp` (written E2 model, baseline as verified MIP start via `common.feasible_mip_start`), `ilp_relaxed` (`common.relax_end_targets`: rho 0 and R_end 0 -- the fair control). Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 300 s. Wall time 18.9 min.

**Geometry caveat (R2.4):** Semi-real NYC instance: real DOHMH restaurants, real NTA zone weights and real candidate-site coordinates are projected onto the synthetic 150 m GridNetwork (local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, rotated by -29 deg to the Manhattan street-grid azimuth and snapped to 150 m blocks inside the study box); no real road network is used, and elevation and traffic signals remain synthetic.

## Headline

**Busiest-cell siting: ILP vs baseline gap = (baseline - ILP) / baseline = 27.3 % (95 % t-CI +/- 29.4, n = 3); relaxed-target ILP 27.3 % (+/- 29.4).** Grid-connected siting: 26.5 % (+/- 37.1) and 26.5 % (+/- 37.2). Mean totals (busiest): baseline 901.3, ILP 644.3, relaxed 643.9 USD; served share 94 % vs 91 % vs 91 %. ILP solved to optimality in 6 of 6 runs (relaxed 6 of 6); MIP start accepted in 6 / 6 (variants injected: {'baseline_round1': 4, 'default': 1, 'baseline_reserve': 1}) and 6 / 6 for the relaxed model; the baseline reports (18) in 5 and (17) in 3 of 6 runs.

## Per instance (both sitings): totals, both gap conventions, solver and start status

| siting | seed | n_arcs | baseline_total | baseline_unserved | baseline_km | baseline_swaps | baseline_families | ilp_total | ilp_status | ilp_gap | ilp_runtime_s | ilp_unserved | ilp_km | ilp_swaps | mip_start_variant | mip_start_accepted | relaxed_total | relaxed_status | relaxed_gap | relaxed_runtime_s | relaxed_unserved | relaxed_start_accepted | gap_vs_baseline_pct | gap_vs_ilp_pct | gap_relaxed_vs_baseline_pct | ilp_minus_relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | 0 | 747798 | 1051.42 | 1 | 124.65 | 9 | {"(18)": 1} | 630.31 | OPTIMAL | 0.00 | 118.37 | 2 | 104.10 | 10 | baseline_round1 | True | 629.65 | OPTIMAL | 0 | 92.93 | 2 | True | 40.05 | 66.81 | 40.11 | 0.66 |
| busiest | 1 | 668274 | 761.74 | 1 | 123.15 | 9 | {"(17)": 1, "(18)": 1} | 634.29 | OPTIMAL | 0 | 76.94 | 3 | 104.25 | 6 | baseline_round1 | True | 634.08 | OPTIMAL | 0 | 70.04 | 3 | True | 16.73 | 20.09 | 16.76 | 0.21 |
| busiest | 2 | 571533 | 890.84 | 5 | 137.70 | 9 | {"(18)": 1} | 668.22 | OPTIMAL | 0 | 77.72 | 5 | 99.30 | 6 | baseline_round1 | True | 667.95 | OPTIMAL | 0.00 | 59.09 | 5 | True | 24.99 | 33.32 | 25.02 | 0.27 |
| grid | 0 | 728867 | 1121.96 | 1 | 137.10 | 8 | {} | 631.17 | OPTIMAL | 0.00 | 120.26 | 2 | 109.95 | 11 | default | True | 630.46 | OPTIMAL | 0.00 | 88.80 | 2 | True | 43.74 | 77.76 | 43.81 | 0.71 |
| grid | 1 | 649741 | 777.96 | 1 | 131.70 | 9 | {"(17)": 1, "(18)": 1} | 634.73 | OPTIMAL | 0 | 98.73 | 3 | 107.70 | 6 | baseline_round1 | True | 634.48 | OPTIMAL | 0 | 77.35 | 3 | True | 18.41 | 22.57 | 18.44 | 0.25 |
| grid | 2 | 558873 | 808.90 | 3 | 140.10 | 10 | {"(17)": 1, "(18)": 1} | 668.67 | OPTIMAL | 0 | 63.20 | 5 | 103.20 | 6 | baseline_reserve | True | 668.35 | OPTIMAL | 0 | 62.84 | 5 | True | 17.34 | 20.97 | 17.38 | 0.32 |

`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP; `gap_relaxed_vs_baseline_pct` uses the relaxed-target ILP (rho 0, R_end 0); `ilp_minus_relaxed` = price of the end targets (17)-(18) in the optimum; `baseline_families` = constraint families the policy *reports* (not enforced).

## Cost (26) and components (27)-(32): mean over seeds per siting and method (USD)

| siting | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 901.33 | 39.57 | 0.84 | 15.42 | 70 | 609.50 | 166 | 0 |
| busiest | ilp | 644.27 | 39.57 | 0.40 | 12.31 | 100 | 489 | 3 | 0 |
| busiest | ilp_relaxed | 643.89 | 39.57 | 0.03 | 12.29 | 100 | 489 | 3 | 0 |
| grid | baseline | 902.94 | 39.57 | 1.01 | 16.36 | 50 | 622 | 174 | 0 |
| grid | ilp | 644.85 | 39.57 | 0.45 | 12.83 | 100 | 489 | 3 | 0 |
| grid | ilp_relaxed | 644.43 | 39.57 | 0.08 | 12.78 | 100 | 489 | 3 | 0 |

## Service / operations metrics: mean over seeds

| siting | method | served_share | n_unserved | mean_response_h | max_response_h | mean_lateness_h | n_late | bike_km | n_swaps | queue_wait_slots | kwh_purchased | peak_kw_sites | transfers_used | end_full_total | viol_17 | viol_18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 0.935 | 2.333 | 1.005 | 1.361 | 0.136 | 17.333 | 128.500 | 9 | 0 | 2.630 | 2.667 | 0 | 3.333 | 0.333 | 1.167 |
| busiest | ilp | 0.907 | 3.333 | 0.832 | 1.056 | 0.003 | 1 | 102.550 | 7.333 | 13 | 1.241 | 1.333 | 0 | 5 | 0 | 0 |
| busiest | ilp_relaxed | 0.907 | 3.333 | 0.832 | 1.056 | 0.003 | 1 | 102.450 | 8.333 | 26.667 | 0.093 | 0.222 | 0 | 1 | 0 | 0 |
| grid | baseline | 0.954 | 1.667 | 1.005 | 1.306 | 0.140 | 19 | 136.300 | 9 | 4.333 | 3.167 | 2.667 | 0 | 4.333 | 0.667 | 0.333 |
| grid | ilp | 0.907 | 3.333 | 0.832 | 1.056 | 0.003 | 1 | 106.950 | 7.667 | 18.667 | 1.407 | 1.333 | 0 | 5 | 0 | 0 |
| grid | ilp_relaxed | 0.907 | 3.333 | 0.832 | 1.056 | 0.003 | 1 | 106.500 | 8.333 | 21.333 | 0.241 | 0.444 | 0 | 1.333 | 0 | 0 |

`viol_17` / `viol_18` = end-stock shortfalls reported by the baseline (0 for the ILP by construction); `transfers_used` is 0 everywhere (no services in the NYC family, E = {}).

## Solver statistics (mean / max over seeds)

| siting | method | n_arcs_mean | n_arcs_max | n_binaries_mean | n_binaries_max | n_rows_mean | n_rows_max | build_time_s_mean | build_time_s_max | runtime_s_mean | runtime_s_max | gap_mean | gap_max | node_count_mean | node_count_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | ilp | 662535 | 747798 | 662574 | 747837 | 62973.333 | 68390 | 3.466 | 3.641 | 91.009 | 118.372 | 0.000 | 0.000 | 1 | 1 |
| busiest | ilp_relaxed | 662535 | 747798 | 662574 | 747837 | 62973.333 | 68390 | 3.519 | 4.196 | 74.022 | 92.935 | 0.000 | 0.000 | 1 | 1 |
| grid | ilp | 645827 | 728867 | 645866 | 728906 | 61524.333 | 66912 | 4.238 | 5.247 | 94.063 | 120.261 | 0.000 | 0.000 | 1 | 1 |
| grid | ilp_relaxed | 645827 | 728867 | 645866 | 728906 | 61524.333 | 66912 | 4.291 | 6.944 | 76.333 | 88.804 | 0.000 | 0.000 | 1 | 1 |

## Siting sensitivity: grid-connected variant minus busiest-cell siting (same orders, bikes' levels and ranks per seed)

| seed | baseline_busiest | baseline_grid | baseline_grid_minus_busiest | baseline_grid_minus_busiest_pct | ilp_busiest | ilp_grid | ilp_grid_minus_busiest | ilp_grid_minus_busiest_pct | ilp_relaxed_busiest | ilp_relaxed_grid | ilp_relaxed_grid_minus_busiest | ilp_relaxed_grid_minus_busiest_pct | gap_busiest_pct | gap_grid_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1051.42 | 1121.96 | 70.55 | 6.71 | 630.31 | 631.17 | 0.86 | 0.14 | 629.65 | 630.46 | 0.81 | 0.13 | 40.05 | 43.74 |
| 1 | 761.74 | 777.96 | 16.22 | 2.13 | 634.29 | 634.73 | 0.43 | 0.07 | 634.08 | 634.48 | 0.40 | 0.06 | 16.73 | 18.41 |
| 2 | 890.84 | 808.90 | -81.95 | -9.20 | 668.22 | 668.67 | 0.45 | 0.07 | 667.95 | 668.35 | 0.40 | 0.06 | 24.99 | 17.34 |

## Demand pattern: NYC semi-real vs synthetic `usd4h` (same seeds)

| descriptor | NYC semi-real | synthetic usd4h |
|---|---|---|
| orders pooled | 108 | 108 |
| restaurants available | 4607 (DOHMH rows in box) | 8 (synthetic) |
| distinct restaurants hit per seed | [32, 32, 33] | [8, 8, 8] |
| top-10 restaurants' share of orders per seed | [0.39, 0.39, 0.36] | [1.0, 1.0, 1.0] |
| top-3 restaurants' share per seed | [0.19, 0.19, 0.17] | [0.64, 0.61, 0.58] |
| customer zones hit per seed | [9, 10, 9] (NTA-2020) | [13, 13, 14] (synthetic zones of 16) |
| mean restaurant -> customer route (km) per seed | [1.76, 1.95, 2.03] | [1.67, 1.9, 1.74] |
| max route (km) per seed | [3.15, 3.3, 3.6] | [4.2, 4.05, 3.45] |
| mean prep (min) per seed | [28.1, 29.3, 29.3] | [29.3, 29.9, 28.6] |
| promise after ready (slots) | 5 | 5 |
| L1 distance of cuisine shares to Kaggle target | 0.288 | 0.313 |
| zone weights | acs_2020_24_literature | synthetic Dirichlet demographics |


Cuisine shares (pooled over seeds):

| cuisine | kaggle_share | nyc_share | synthetic_share |
|---|---|---|---|
| American | 0.308 | 0.278 | 0.296 |
| Japanese | 0.248 | 0.213 | 0.315 |
| Italian | 0.157 | 0.194 | 0.241 |
| Chinese | 0.113 | 0.167 | 0.102 |
| Mexican | 0.041 | 0.009 | 0.046 |
| Indian | 0.038 | 0.074 | 0 |
| Middle Eastern | 0.026 | 0.019 | 0 |
| Mediterranean | 0.024 | 0.009 | 0 |
| Thai | 0.010 | 0 | 0 |
| French | 0.009 | 0 | 0 |
| Southern | 0.009 | 0.019 | 0 |
| Korean | 0.007 | 0.009 | 0 |
| Spanish | 0.006 | 0 | 0 |
| Vietnamese | 0.004 | 0.009 | 0 |

NYC customer zone shares (sampling law = ACS zone-weight mass of the grid nodes in the box; realised = orders):

| zone | name | sampling_law_share | realised_share |
|---|---|---|---|
| MN0603 | Murray Hill-Kips Bay | 0.203 | 0.120 |
| MN0402 | Hell's Kitchen | 0.200 | 0.194 |
| MN0401 | Chelsea-Hudson Yards | 0.178 | 0.259 |
| MN0501 | Midtown South-Flatiron-Union Square | 0.099 | 0.102 |
| MN0604 | East Midtown-Turtle Bay | 0.098 | 0.111 |
| MN0502 | Midtown-Times Square | 0.069 | 0.065 |
| MN0602 | Gramercy | 0.066 | 0.065 |
| MN0802 | Upper East Side-Carnegie Hill | 0.034 | 0.028 |
| MN0203 | West Village | 0.020 | 0.009 |
| MN0701 | Upper West Side-Lincoln Square | 0.013 | 0.028 |
| MN0601 | Stuyvesant Town-Peter Cooper Village | 0.009 | 0 |
| MN0202 | Greenwich Village | 0.008 | 0.019 |
| MN0801 | Upper East Side-Lenox Hill-Roosevelt Island | 0.005 | 0 |

NYC restaurant top-10 (pooled over seeds; name (cuisine): orders): YAKINIKU FUTAGO (Japanese) 3; HERALD SQUARE CAFE (American) 3; NYC PIZZERIA (Italian) 2; VIRGIN HOTEL - 38TH FLOOR EVENT SPACE (American) 2; MALA PANDA (Chinese) 2; CHEF GUO (Chinese) 2; KOI (Japanese) 2; DIM SUM PALACE (Chinese) 2; TEMPURA MATSUI (Japanese) 2; HOT DOG CONCESSION (American) 1.

Synthetic restaurant top-10 (node (cuisine): orders): (7, 14) (Italian) 11; (12, 4) (Japanese) 10; (13, 1) (Italian) 9; (7, 0) (American) 8; (11, 12) (Japanese) 7; (2, 4) (Italian) 6; (6, 0) (Chinese) 5; (7, 13) (Japanese) 5; (12, 14) (American) 5; (11, 17) (Japanese) 5.

## Interpretation

On the semi-real Midtown instance the coordinated ILP lowers the baseline's cost by 27.3 % (+/- 29.4) with the written end targets and by 27.3 % (+/- 29.4) under the fair relaxed control, so the advantage seen on the synthetic usd4h family (seed 0: 615 vs 733 USD, 16 %; seed 1: 660 vs 973, 32 %, `outputs/r2_probe/`) survives real restaurant and customer geography of the same size. The gap is made of unserved orders (-30 USD of the 257.1 USD mean difference at the busiest siting), response (120.5), lateness (163) and travel (3.1); electricity (0.44) is negligible at pi = 0.32 $/kWh and there are no transfers (E = {}). The baseline serves 94 % of the orders against 91 % for the ILP, with mean response 1.01 h vs 0.83 h and 128.5 vs 102.6 km; with P = 30.0 USD and w = 18.0 $/h a dropped order costs about as much as 1.7 h of waiting, so the ILP trades response time for coverage. Swaps: baseline 9.0 vs ILP 7.3 per run with 2.63 vs 1.24 kWh purchased; the ILP meets (17)-(18) at a price of 0.38 USD on average (written minus relaxed optimum), while the baseline ends with (18) violated in 5 of 6 runs (DEMAND_AWARE charging covers only the per-site reserve (17), DECISIONS R2 notes). Siting matters for both methods: moving the three sites to the grid-connected landmarks changes the baseline by -0.1 % and the ILP by 0.1 % on average (per seed ILP: [0.1, 0.1, 0.1] %), and the ILP's relative advantage is 26.5 % there (+/- 37.1); Union Square sits on the southern edge of the box, so bikes starting there ride farther to the Midtown demand mass, which the ILP absorbs better than the nearest-rider policy only when a dropped order is at stake. Demand realism: the realised cuisine mix of the NYC instances is within L1 = 0.29 of the Kaggle order shares (synthetic 0.31, where only 8 restaurants exist and some cuisines have none), the customers fall in [9, 10, 9] NTAs with the top three zones (MN0603, MN0402, MN0401: 20 %, 20 %, 18 % of the sampling mass) receiving 57 % of the orders (L1 realised-vs-law 0.25 over 13 zones at 36 orders per seed), and orders spread over about 32 distinct restaurants per seed (top-10 share 0.38) against 8 fixed synthetic restaurants (top-10 share 1.0). Trip geometry is similar in both families (mean restaurant -> customer route 1.91 vs 1.77 km) because both live on the same 150 m grid with the same speed / energy physics; the semi-real instance only changes *where* the mass sits (Chelsea / Hudson Yards / Midtown South NTAs) and how concentrated the restaurants are. Solver: 654,181 arcs under PRUNING_NYC (versus 1.9 M for usd4h at the same size) because moves are allowed only into the three site nodes; the ILPs solved in 93 s on average (max 120 s), 12 of 12 runs proven optimal within 300 s at Threads 3. Caveats: synthetic road geometry (rotated grid, synthetic elevation and signals, one shortest grid route per pair), 3 seeds (CIs are wide), 6 bikes / 36 orders (the R2.2 nominal 10 / 60 was not solved here), and the baseline's (17)/(18) violations are reported, not priced -- the relaxed control is the fair comparison.

## Anomalies and notes

- The default baseline schedule violated (18) and a fallback variant was injected as start on nyc4h-busiest-seed0 (baseline_round1), nyc4h-busiest-seed1 (baseline_round1), nyc4h-grid-seed1 (baseline_round1), nyc4h-busiest-seed2 (baseline_round1), nyc4h-grid-seed2 (baseline_reserve) (baseline columns still describe the default policy).
- The baseline policy depends on R_end_j through the DEMAND_AWARE reserve (R2.3: reserve = R_end_j y_j), so its schedule on the relaxed copy (R_end 0) differs from the written one on nyc4h-busiest-seed0 (1051.10 vs written baseline), nyc4h-grid-seed0 (1121.56 vs written baseline), nyc4h-busiest-seed1 (761.51 vs written baseline), nyc4h-grid-seed1 (777.41 vs written baseline), nyc4h-busiest-seed2 (890.52 vs written baseline), nyc4h-grid-seed2 (808.59 vs written baseline); the relaxed-copy schedule is only the MIP start of `ilp_relaxed`, all baseline columns are the written-instance policy.
- Sites are placed by node, several facilities could share a node if two sitings coincided (they do not here); the grid-connected coordinates are my choice of three well-known landmarks, not Citi Bike station records.
- `data_nyc.make_nyc_instance` draws the bikes' start nodes round robin over the sites, so the two sitings of a seed differ only in the site nodes and the bikes' starting positions; orders, prep times, restaurant ranks and q0 are identical.

## Figures

- `map_seed0.png`
- `cost_components.png`
- `gap_by_seed.png`
- `demand_comparison.png`

Files: `results.csv` (one row per instance x method), `per_instance.csv`, `siting.csv`, `demand_comparison.json`, `instances/*.json` (byte-identical inputs of every method), `wall_time.json`; all in `outputs/e8_nyc/`.
