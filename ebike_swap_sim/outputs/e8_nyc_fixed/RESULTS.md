# E8 -- NYC semi-real instance (DOHMH restaurants, ACS zone weights, real site coordinates on the synthetic grid)

## Summary

This experiment compares the round-2 baseline policy, the E2 integer program (rho 0.5, R_end 1) and the ILP control with relaxed terminal targets on the R2.4 semi-real NYC instance (Midtown/Chelsea/Flatiron study box, real DOHMH restaurants, ACS 2020-24 literature-formula zone weights, real candidate site coordinates projected onto the synthetic 150 m grid) with 6 bikes, 36 orders, 17:00-21:00 (H = 48), usd_sunk USD costs and 3 random seeds. With the sites placed on the busiest restaurant cells, the ILP's total-cost reduction relative to the baseline ((baseline - ILP)/baseline) averages 36.5 % (95 % t half-width 29.3, n = 3); the relaxed control gives 36.5 %; the ILP reached optimality in 6/6 solves (Threads 3, time limit 300 s). Moving the three sites to Citi Bike-style 'grid' landmarks (8th Ave/W 34th, Union Sq, Grand Central) changes the mean baseline cost by -2.6 % and the ILP cost by 0.0 %, and the ILP's relative advantage is 34.3 % (half-width 37.6), i.e. siting affects both methods but does not change the conclusion. Compared with the synthetic usd4h family, the semi-real instance's cuisine shares are closer to the Kaggle target (L1 deviation 0.20 vs 0.31), customers fall in [11, 8, 9] NTAs and the restaurants are spread over about 32 establishments (the synthetic family has only 8), but the mean restaurant-to-customer distance 1.76 km is close to the synthetic family's 1.77 km. Geometry caveat: the road network is still the synthetic grid (rotated 29 degrees, 150 m blocks), elevation and traffic signals are synthetic values, and all distances / energy use come from that synthetic geometry rather than real roads.

## Setup

Family `nyc4h` (`experiments/common.py`, builder `data_nyc.make_nyc_instance`): 6 bikes, 36 orders (1.5 orders per bike-hour), window 17:00-21:00 (H = 48 slots of 5 min), L = 12 levels of 50 Wh, costs `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30.0, w 18.0 $/h, v 36.0 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h site), q_res 1, rho 0.5, R_end 1. Three co-located sites (B 3, C 2, K 8, M 1, sigma 1, P 4 kW, group 8 kW / 6 kW 18-20 h). Study box lat 40.735-40.77, lon -74.005--73.965 (34 x 35 grid nodes of 150 m). Restaurants: 4607 usable DOHMH rows in the box mapped to the Kaggle cuisines (`data_nyc.CUISINE_MAP`), sampled by Kaggle share within 2.5 km of the customer with Zipf s = 1 ranks. **Zone weights: `acs_2020_24_literature`** (NTA2020; 15 NTAs intersect the box, 13 contain grid nodes; the literature formula on the ACS 2020-24 tables, no fallback). Seeds [0, 1, 2]; sitings `busiest` = the three busiest restaurant cells (sites [[13, 14], [17, 13], [17, 19]], lat/lon [[40.7513, -73.9922], [40.7475, -73.9869], [40.7545, -73.9817]]) and `grid` = 8th Ave / W 34th St, Union Square, Grand Central snapped to the grid (sites [[12, 15], [19, 4], [20, 19]]). Pruning `common.PRUNING_NYC` (moves only into the 3 site nodes, tau_max 4, start_slack 6, reachable pruning): 584,448 arcs on average. **This pruning restricts the ILP but not the policy** (fairness review F2): the baseline repositions only to swap sites and starts deliveries in place, so it loses nothing, whereas the ILP loses pre-positioning moves towards restaurants / customers (tau_max never binds on nyc4h: every customer -> restaurant pair is within 4 slots). The ILP totals below are therefore UPPER bounds on the written E2 optimum and the gaps LOWER bounds on the coordination value; no lossless probe exists for these targets yet (`--targets default` runs it). Release times follow the R2.2 block profile as a step function (`meta['hourly_profile_used']['kind']` = `block_step`, units review F1), the same object as the synthetic usd4h family. Restaurant supply: 26 % of the usable DOHMH rows in the box map to the unreachable `other` class (cafes, bakeries, desserts, juice; units review F3, declared assumption). Demand hash per (seed, siting): `demand_md5` column (orders, q0, H, L; identical across sitings by assertion). Methods: `baseline` (R2.3 defaults), `ilp` (written E2 model, baseline as verified MIP start via `common.feasible_mip_start`), `ilp_relaxed` (`common.relax_end_targets`: rho 0 and R_end 0 -- the fair control). Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 300 s. Wall time 9.4 min.

**Geometry caveat (R2.4):** Semi-real NYC instance: real DOHMH restaurants, real NTA zone weights and real candidate-site coordinates are projected onto the synthetic 150 m GridNetwork (local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, rotated by -29 deg to the Manhattan street-grid azimuth and snapped to 150 m blocks inside the study box); no real road network is used, and elevation and traffic signals remain synthetic.

## Headline

**Busiest-cell siting: ILP vs baseline gap = (baseline - ILP) / baseline = 36.5 % (95 % t-CI +/- 29.3, n = 3); relaxed-target ILP 36.5 % (+/- 29.3).** Grid-connected siting: 34.3 % (+/- 37.6) and 34.4 % (+/- 37.6). Mean totals (busiest): baseline 1100.3, ILP 679.6, relaxed 679.4 USD; served share 84 % vs 85 % vs 85 %. ILP solved to optimality in 6 of 6 runs (relaxed 6 of 6); MIP start accepted in 6 / 6 (variants injected: {'baseline_round1': 3, 'default': 3}) and 6 / 6 for the relaxed model; the baseline reports (18) in 2 and (17) in 1 of 6 runs.

## Per instance (both sitings): totals, both gap conventions, solver and start status

| siting | seed | n_arcs | baseline_total | baseline_unserved | baseline_km | baseline_swaps | baseline_families | ilp_total | ilp_status | ilp_gap | ilp_runtime_s | ilp_unserved | ilp_km | ilp_swaps | mip_start_variant | mip_start_accepted | relaxed_total | relaxed_status | relaxed_gap | relaxed_runtime_s | relaxed_unserved | relaxed_start_accepted | gap_vs_baseline_pct | gap_vs_ilp_pct | gap_relaxed_vs_baseline_pct | ilp_minus_relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | 0 | 729139 | 1374.68 | 5 | 119.25 | 9 | {"(18)": 1} | 706.08 | OPTIMAL | 0 | 60.03 | 6 | 90 | 6 | baseline_round1 | True | 705.87 | OPTIMAL | 0 | 55.46 | 6 | True | 48.64 | 94.69 | 48.65 | 0.21 |
| busiest | 1 | 530382 | 1043.48 | 6 | 110.85 | 6 | {} | 671.51 | OPTIMAL | 0 | 34.27 | 5 | 102.15 | 6 | default | True | 671.33 | OPTIMAL | 0 | 31.73 | 5 | True | 35.65 | 55.39 | 35.66 | 0.18 |
| busiest | 2 | 511370 | 882.69 | 6 | 106.35 | 8 | {"(17)": 1} | 661.16 | OPTIMAL | 0 | 36.66 | 5 | 90.90 | 6 | baseline_round1 | True | 660.91 | OPTIMAL | 0 | 36.32 | 5 | True | 25.10 | 33.51 | 25.13 | 0.25 |
| grid | 0 | 720006 | 1338.39 | 5 | 115.65 | 9 | {"(18)": 1} | 706.16 | OPTIMAL | 0 | 54.21 | 6 | 90.60 | 6 | baseline_round1 | True | 705.94 | OPTIMAL | 0 | 51.04 | 6 | True | 47.24 | 89.53 | 47.25 | 0.21 |
| grid | 1 | 525584 | 1085.71 | 7 | 112.65 | 7 | {} | 671.76 | OPTIMAL | 0 | 28.09 | 5 | 104.25 | 6 | default | True | 671.58 | OPTIMAL | 0 | 34.12 | 5 | True | 38.13 | 61.62 | 38.14 | 0.18 |
| grid | 2 | 490210 | 802.70 | 5 | 104.40 | 7 | {} | 661.01 | OPTIMAL | 0 | 35.67 | 5 | 88.80 | 7 | default | True | 660.73 | OPTIMAL | 0 | 29.66 | 5 | True | 17.65 | 21.44 | 17.69 | 0.28 |

`gap_vs_baseline_pct` = 100 (baseline - ILP) / baseline (headline), `gap_vs_ilp_pct` = 100 (baseline - ILP) / ILP; `gap_relaxed_vs_baseline_pct` uses the relaxed-target ILP (rho 0, R_end 0); `ilp_minus_relaxed` = price of the end targets (17)-(18) in the optimum; `baseline_families` = constraint families the policy *reports* (not enforced).

## Cost (26) and components (27)-(32): mean over seeds per siting and method (USD)

| siting | method | total | C_setup | C_elec | C_travel | unserved | response | lateness | C_reb |
|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 1100.28 | 39.57 | 0.75 | 13.46 | 170 | 612.50 | 264 | 0 |
| busiest | ilp | 679.58 | 39.57 | 0.19 | 11.32 | 160 | 462.50 | 6 | 0 |
| busiest | ilp_relaxed | 679.37 | 39.57 | 0 | 11.30 | 160 | 462.50 | 6 | 0 |
| grid | baseline | 1075.60 | 39.57 | 0.72 | 13.31 | 170 | 604 | 248 | 0 |
| grid | ilp | 679.64 | 39.57 | 0.23 | 11.35 | 160 | 462.50 | 6 | 0 |
| grid | ilp_relaxed | 679.42 | 39.57 | 0 | 11.35 | 160 | 462.50 | 6 | 0 |

## Service / operations metrics: mean over seeds

| siting | method | served_share | n_unserved | mean_response_h | max_response_h | mean_lateness_h | n_late | bike_km | n_swaps | queue_wait_slots | kwh_purchased | peak_kw_sites | transfers_used | end_full_total | viol_17 | viol_18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 0.843 | 5.667 | 1.120 | 1.500 | 0.240 | 19.667 | 112.150 | 7.667 | 3 | 2.352 | 2 | 0 | 4.667 | 0.333 | 0.500 |
| busiest | ilp | 0.852 | 5.333 | 0.838 | 1.056 | 0.006 | 1.667 | 94.350 | 6 | 17 | 0.593 | 1.111 | 0 | 5 | 0 | 0 |
| busiest | ilp_relaxed | 0.852 | 5.333 | 0.838 | 1.056 | 0.006 | 1.667 | 94.150 | 8 | 15 | 0 | 0 | 0 | 1 | 0 | 0 |
| grid | baseline | 0.843 | 5.667 | 1.106 | 1.472 | 0.227 | 18.333 | 110.900 | 7.667 | 5.667 | 2.259 | 1.556 | 0 | 4.667 | 0 | 0.167 |
| grid | ilp | 0.852 | 5.333 | 0.838 | 1.056 | 0.006 | 1.667 | 94.550 | 6.333 | 11.333 | 0.704 | 1.333 | 0 | 5 | 0 | 0 |
| grid | ilp_relaxed | 0.852 | 5.333 | 0.838 | 1.056 | 0.006 | 1.667 | 94.550 | 7.333 | 12 | 0 | 0 | 0 | 1.667 | 0 | 0 |

`viol_17` / `viol_18` = end-stock shortfalls reported by the baseline (0 for the ILP by construction); `transfers_used` is 0 everywhere (no services in the NYC family, E = {}).

## Solver statistics (mean / max over seeds)

| siting | method | n_arcs_mean | n_arcs_max | n_binaries_mean | n_binaries_max | n_rows_mean | n_rows_max | build_time_s_mean | build_time_s_max | runtime_s_mean | runtime_s_max | gap_mean | gap_max | node_count_mean | node_count_max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | ilp | 590297 | 729139 | 590336 | 729178 | 55450.333 | 65707 | 2.164 | 2.839 | 43.654 | 60.028 | 0 | 0 | 1 | 1 |
| busiest | ilp_relaxed | 590297 | 729139 | 590336 | 729178 | 55450.333 | 65707 | 2.219 | 2.486 | 41.168 | 55.457 | 0 | 0 | 1 | 1 |
| grid | ilp | 578600 | 720006 | 578639 | 720045 | 54151.333 | 64778 | 2.058 | 2.783 | 39.325 | 54.211 | 0 | 0 | 1 | 1 |
| grid | ilp_relaxed | 578600 | 720006 | 578639 | 720045 | 54151.333 | 64778 | 2.027 | 2.580 | 38.271 | 51.036 | 0 | 0 | 1 | 1 |

## Siting sensitivity: grid-connected variant minus busiest-cell siting (same orders, bikes' levels and ranks per seed)

| seed | baseline_busiest | baseline_grid | baseline_grid_minus_busiest | baseline_grid_minus_busiest_pct | ilp_busiest | ilp_grid | ilp_grid_minus_busiest | ilp_grid_minus_busiest_pct | ilp_relaxed_busiest | ilp_relaxed_grid | ilp_relaxed_grid_minus_busiest | ilp_relaxed_grid_minus_busiest_pct | gap_busiest_pct | gap_grid_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1374.68 | 1338.39 | -36.29 | -2.64 | 706.08 | 706.16 | 0.07 | 0.01 | 705.87 | 705.94 | 0.07 | 0.01 | 48.64 | 47.24 |
| 1 | 1043.48 | 1085.71 | 42.23 | 4.05 | 671.51 | 671.76 | 0.25 | 0.04 | 671.33 | 671.58 | 0.25 | 0.04 | 35.65 | 38.13 |
| 2 | 882.69 | 802.70 | -79.98 | -9.06 | 661.16 | 661.01 | -0.15 | -0.02 | 660.91 | 660.73 | -0.18 | -0.03 | 25.10 | 17.65 |

## Demand pattern: NYC semi-real vs synthetic `usd4h` (same seeds)

| descriptor | NYC semi-real | synthetic usd4h |
|---|---|---|
| orders pooled | 108 | 108 |
| restaurants available | 4607 (DOHMH rows in box) | 8 (synthetic) |
| distinct restaurants hit per seed | [32, 32, 33] | [8, 8, 8] |
| top-10 restaurants' share of orders per seed | [0.39, 0.39, 0.36] | [1.0, 1.0, 1.0] |
| top-3 restaurants' share per seed | [0.19, 0.19, 0.17] | [0.64, 0.61, 0.58] |
| customer zones hit per seed | [11, 8, 9] (NTA-2020) | [13, 13, 14] (synthetic zones of 16) |
| mean restaurant -> customer route (km) per seed | [1.79, 1.79, 1.7] | [1.67, 1.9, 1.74] |
| max route (km) per seed | [3.3, 3.3, 3.3] | [4.2, 4.05, 3.45] |
| mean prep (min) per seed | [29.6, 29.9, 29.7] | [29.3, 29.9, 28.6] |
| promise after ready (slots) | 5 | 5 |
| L1 distance of cuisine shares to Kaggle target | 0.199 | 0.313 |
| zone weights | acs_2020_24_literature | synthetic Dirichlet demographics |


Cuisine shares (pooled over seeds):

| cuisine | kaggle_share | nyc_share | synthetic_share |
|---|---|---|---|
| American | 0.308 | 0.315 | 0.296 |
| Japanese | 0.248 | 0.231 | 0.315 |
| Italian | 0.157 | 0.213 | 0.241 |
| Chinese | 0.113 | 0.074 | 0.102 |
| Mexican | 0.041 | 0.037 | 0.046 |
| Indian | 0.038 | 0.046 | 0 |
| Middle Eastern | 0.026 | 0.028 | 0 |
| Mediterranean | 0.024 | 0 | 0 |
| Thai | 0.010 | 0.009 | 0 |
| French | 0.009 | 0 | 0 |
| Southern | 0.009 | 0.028 | 0 |
| Korean | 0.007 | 0.009 | 0 |
| Spanish | 0.006 | 0 | 0 |
| Vietnamese | 0.004 | 0.009 | 0 |

NYC customer zone shares (sampling law = ACS zone-weight mass of the grid nodes in the box; realised = orders):

| zone | name | sampling_law_share | realised_share |
|---|---|---|---|
| MN0603 | Murray Hill-Kips Bay | 0.203 | 0.120 |
| MN0402 | Hell's Kitchen | 0.200 | 0.176 |
| MN0401 | Chelsea-Hudson Yards | 0.178 | 0.231 |
| MN0501 | Midtown South-Flatiron-Union Square | 0.099 | 0.139 |
| MN0604 | East Midtown-Turtle Bay | 0.098 | 0.111 |
| MN0502 | Midtown-Times Square | 0.069 | 0.046 |
| MN0602 | Gramercy | 0.066 | 0.074 |
| MN0802 | Upper East Side-Carnegie Hill | 0.034 | 0.037 |
| MN0203 | West Village | 0.020 | 0 |
| MN0701 | Upper West Side-Lincoln Square | 0.013 | 0.037 |
| MN0601 | Stuyvesant Town-Peter Cooper Village | 0.009 | 0 |
| MN0202 | Greenwich Village | 0.008 | 0.019 |
| MN0801 | Upper East Side-Lenox Hill-Roosevelt Island | 0.005 | 0.009 |

NYC restaurant top-10 (pooled over seeds; name (cuisine): orders): SKY PAVILION (Chinese) 3; YAKINIKU FUTAGO (Japanese) 3; HERALD SQUARE CAFE (American) 3; RESTAURANT 555 (Italian) 2; PANDA EXPRESS (Chinese) 2; YAMA (Japanese) 2; TEPPEN RAMEN (Japanese) 2; ELEMENT HOTEL TIME SQUARE (American) 2; HOLIDAY INN EXPRESS NYC TIMES SQUARE (American) 1; IKAZAYA FUTAGO (Japanese) 1.

Synthetic restaurant top-10 (node (cuisine): orders): (7, 14) (Italian) 11; (12, 4) (Japanese) 10; (13, 1) (Italian) 9; (7, 0) (American) 8; (11, 12) (Japanese) 7; (2, 4) (Italian) 6; (6, 0) (Chinese) 5; (7, 13) (Japanese) 5; (12, 14) (American) 5; (11, 17) (Japanese) 5.

## Interpretation

On the semi-real Midtown instance the coordinated ILP lowers the baseline's cost by 36.5 % (+/- 29.3) with the written end targets and by 36.5 % (+/- 29.3) under the fair relaxed control, so the advantage seen on the synthetic usd4h family (seed 0: 615 vs 733 USD, 16 %; seed 1: 660 vs 973, 32 %, `outputs/r2_probe/`) survives real restaurant and customer geography of the same size. The gap is made of unserved orders (10 USD of the 420.7 USD mean difference at the busiest siting), response (150), lateness (258) and travel (2.1); electricity (0.56) is negligible at pi = 0.32 $/kWh and there are no transfers (E = {}). The baseline serves 84 % of the orders against 85 % for the ILP, with mean response 1.12 h vs 0.84 h and 112.1 vs 94.3 km; with P = 30.0 USD and w = 18.0 $/h a dropped order costs about as much as 1.7 h of waiting, so the ILP trades response time for coverage. Swaps: baseline 7.7 vs ILP 6.0 per run with 2.35 vs 0.59 kWh purchased; the ILP meets (17)-(18) at a price of 0.21 USD on average (written minus relaxed optimum), while the baseline ends with (18) violated in 2 of 6 runs (DEMAND_AWARE charging covers only the per-site reserve (17), DECISIONS R2 notes). Siting matters for both methods: moving the three sites to the grid-connected landmarks changes the baseline by -2.6 % and the ILP by 0.0 % on average (per seed ILP: [0.0, 0.0, -0.0] %), and the ILP's relative advantage is 34.3 % there (+/- 37.6); Union Square sits on the southern edge of the box, so bikes starting there ride farther to the Midtown demand mass, which the ILP absorbs better than the nearest-rider policy only when a dropped order is at stake. Demand realism: the realised cuisine mix of the NYC instances is within L1 = 0.20 of the Kaggle order shares (synthetic 0.31, where only 8 restaurants exist and some cuisines have none), the customers fall in [11, 8, 9] NTAs with the top three zones (MN0603, MN0402, MN0401: 20 %, 20 %, 18 % of the sampling mass) receiving 53 % of the orders (L1 realised-vs-law 0.32 over 13 zones at 36 orders per seed), and orders spread over about 32 distinct restaurants per seed (top-10 share 0.38) against 8 fixed synthetic restaurants (top-10 share 1.0). Trip geometry is similar in both families (mean restaurant -> customer route 1.76 vs 1.77 km) because both live on the same 150 m grid with the same speed / energy physics; the semi-real instance only changes *where* the mass sits (Chelsea / Hudson Yards / Midtown South NTAs) and how concentrated the restaurants are. Solver: 584,448 arcs under PRUNING_NYC (versus 1.9 M for usd4h at the same size) because moves are allowed only into the three site nodes; the ILPs solved in 41 s on average (max 60 s), 12 of 12 runs proven optimal within 300 s at Threads 3. Caveats: synthetic road geometry (rotated grid, synthetic elevation and signals, one shortest grid route per pair), 3 seeds (CIs are wide), 6 bikes / 36 orders (the R2.2 nominal 10 / 60 was not solved here), and the baseline's (17)/(18) violations are reported, not priced -- the relaxed control is the fair comparison. PRUNING_NYC binds only the ILP (no repositioning to non-site nodes), so every ILP total is an upper bound on the written optimum and every gap a lower bound on the coordination value (fairness review F2); the `other` cuisine class (26 % of the box's restaurants) is unreachable by construction (units review F3).

## Anomalies and notes

- The default baseline schedule violated (18) and a fallback variant was injected as start on nyc4h-busiest-seed0 (baseline_round1), nyc4h-grid-seed0 (baseline_round1), nyc4h-busiest-seed2 (baseline_round1) (baseline columns still describe the default policy).
- Structurally unservable orders (no delivery arc; both methods pay P, raw drop rates inflated identically): nyc4h-busiest-seed1 (1), nyc4h-grid-seed1 (1), nyc4h-busiest-seed2 (2), nyc4h-grid-seed2 (2); `served_share_servable` is the share relative to the servable orders (fairness review F5).
- Sites are placed by node, several facilities could share a node if two sitings coincided (they do not here); the grid-connected coordinates are my choice of three well-known landmarks, not Citi Bike station records.
- `data_nyc.make_nyc_instance` draws the bikes' start nodes round robin over the sites, so the two sitings of a seed differ only in the site nodes and the bikes' starting positions; orders, prep times, restaurant ranks and q0 are identical.

## Figures

- `map_seed0.png`
- `cost_components.png`
- `gap_by_seed.png`
- `demand_comparison.png`

Files: `results.csv` (one row per instance x method), `per_instance.csv`, `siting.csv`, `demand_comparison.json`, `instances/*.json` (byte-identical inputs of every method), `wall_time.json`; all in `outputs/e8_nyc/`.
