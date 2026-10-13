# E8 (final report) -- NYC semi-real instance: DOHMH restaurants, ACS literature zone weights, Midtown/Chelsea/Flatiron box

Authoritative inputs: `outputs/e8_nyc_fixed/{results.csv, per_instance.csv, siting.csv, rows.jsonl, demand_comparison.json, wall_time.json, run_stdout.log, instances/}` written by `experiments/e8_nyc_fixed.py` on 2026-10-12 17:43-17:52 (wall 9.4 min). `outputs/e8_nyc/` is the pre-fix profile run (ramp-interpolated release profile, units review F1) and is **superseded**; it is mentioned only in the anomalies. 18 records (6 instances x 3 methods), 18 unique (instance, method) keys, **0 duplicate rows dropped**. All statistics below were recomputed from `results.csv` / `per_instance.csv` and agree with the script's own `RESULTS.md`.

## Summary

On the semi-real NYC Midtown/Chelsea/Flatiron instance (real DOHMH restaurants, ACS 2020-24 literature-formula zone weights, three real candidate site coordinates projected onto the synthetic 150 m grid; 6 bikes, 36 orders, 17:00-21:00, usd_sunk USD costs, 3 seeds), the E2 integer program's total-cost reduction relative to the round-2 baseline ((baseline - ILP)/baseline) averages 36.5 % under the "busiest restaurant cell" siting (95 % t half-width 29.3, n = 3) and 34.3 % under the "grid landmark" siting (half-width 37.6); the fair control with relaxed end targets gives almost the same 36.5 % / 34.4 %, because the end targets (17)-(18) are worth only 0.21-0.23 $ in the optimal solutions. The composition of the gap is completely different from round 1: lateness cost accounts for 61 %, response time for 36 % and the unserved penalty for only 2.4 % (in round 1, 90 % came from the unserved penalty); both methods serve about 84-85 % of the orders (0-2 orders per seed are structurally unservable). Siting has almost no effect on the ILP (the changes of all three seeds are within +/-0.04 %), whereas the baseline cost varies from -9 % to +4 % with the siting, which shows that coordinated dispatching absorbs differences in site location while the nearest-rider rule cannot. On the solving side, PRUNING_NYC restricts the movement arcs to the 3 site nodes, each ILP has about 580,000 binary variables, and 12/12 solves were proven optimal at the root node (mean 41 s, max 60 s, time limit 300 s, no timeouts); but this pruning constrains only the ILP and not the baseline, so the ILP cost is an upper bound on the written model's optimum and the gap a lower bound on the coordination value. On the demand side, compared with the synthetic usd4h family the semi-real instance's cuisine shares are closer to the Kaggle target (L1 0.20 vs 0.31), the orders are spread over about 32 restaurants (synthetic: only 8) and 8-11 NTAs, and the mean restaurant-to-customer distance is similar (1.76 vs 1.77 km); but 26 % of the DOHMH restaurants in the study box are mapped to the non-sampleable "other" class, and the road network, elevation and traffic signals are still synthetic, with all distances and energy use coming from the synthetic grid rotated 29 degrees rather than from real roads.

## 1. Setup (as run)

| item | value |
|---|---|
| family / builder | `nyc4h`, `data_nyc.make_nyc_instance` (DECISIONS R2.4) |
| size | 6 bikes, 36 orders (1.5 orders per bike-hour), window 17:00-21:00, H = 48 slots x 5 min, L = 12 levels (50 Wh) |
| costs | `usd_sunk` (R2.1): kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03, bB 0.332, bC 0.082 per 4 h site; q_res 1, rho 0.5, R_end 1 |
| sites | 3 co-located (B 3, C 2, K 8, M 1, sigma 1, P 4 kW; grid group 8 kW / 6 kW 18-20 h), no transfer services (E = {}) |
| siting `busiest` | three busiest DOHMH restaurant cells: grid nodes [13,14], [17,13], [17,19] = (40.7513, -73.9922), (40.7475, -73.9869), (40.7545, -73.9817) |
| siting `grid` | Citi Bike-style grid-connected landmarks snapped to the grid: 8th Ave / W 34th St [12,15], Union Square [19,4], Grand Central [20,19] |
| study box | lat 40.735-40.770, lon -74.005 to -73.965; 34 x 35 grid nodes of 150 m |
| restaurants | 4,607 usable DOHMH rows in the box; `CUISINE_MAP` -> 14 Kaggle classes + `other`; **26.1 % (1,201 rows) map to `other` and are never sampled** (`unmapped_share_in_box` = 0.2607 in every row) |
| zone weights | `acs_2020_24_literature` (NTA-2020; 15 NTAs intersect the box, 13 contain grid nodes; no GeoDa fallback) |
| release profile | R2.2 block profile as a step function (`hourly_profile_kind` = `block_step`, units fix F1), same object as the synthetic `usd4h` family |
| demand identity | `demand_md5` (orders, q0, H, L) asserted equal across the two sitings of a seed: seed 0 `7e2a8619...`, seed 1 `be2918de...`, seed 2 `0a7465f6...` |
| pruning | `common.PRUNING_NYC`: moves only into the 3 site nodes, tau_max 4, start_slack 6, lossless reachable pruning; 584,448 arcs on average (490 k - 729 k) |
| methods | `baseline` = R2.3 rules (stock-aware site choice, DEMAND_AWARE charging with reserve R_end_j, JIT dispatch, dead-zone rule; (9)/(17)/(18) reported not enforced); `ilp` = written E2 model (rho 0.5, R_end 1) with a verified baseline schedule as MIP start; `ilp_relaxed` = `common.relax_end_targets` (rho 0, R_end 0), the fair control |
| fairness fix F1 | the relaxed-copy baseline (only used as the MIP start of `ilp_relaxed`) ran with the written R_end as charging reserve: `baseline_relaxed_copy_differs` = False and `policy_reserve_source` = `written_R_end` in all 6 relaxed runs, so the `baseline` column is one policy throughout |
| solver | Gurobi 13, OutputFlag 0, Threads 3, TimeLimit 300 s per solve |

**Geometry caveat (R2.4).** Real restaurants, real NTA zone weights and real candidate-site coordinates are projected onto the synthetic 150 m GridNetwork (local equirectangular metres, 1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N, rotated by -29 deg to the Manhattan street-grid azimuth, snapped to 150 m blocks). No real road network is used; elevation and traffic signals are synthetic; every distance, travel time and energy figure comes from this synthetic geometry.

**Pruning caveat (fairness review F2).** `PRUNING_NYC` forbids repositioning moves to non-site nodes. The baseline never makes such moves (it repositions only to swap sites and starts deliveries in place), so it loses nothing; the ILP loses pre-positioning towards restaurants / customers. Every ILP total below is therefore an **upper bound on the written E2 optimum and every gap a lower bound on the coordination value**. The lossless probe (`--targets default`, multi-million-arc ILPs) has not been run.

## 2. Headline: ILP vs baseline vs relaxed control (mean over 3 seeds, 95 % t-CI, t_{0.975,2} = 4.303)

Gap definition: **gap = (baseline - ILP) / baseline** (headline); gap_vs_ilp = (baseline - ILP) / ILP (secondary).

| siting | gap written ILP, % | gap relaxed ILP, % | gap_vs_ilp, % | baseline total, USD | ILP total, USD | relaxed total, USD | ILP - relaxed, USD (price of (17)-(18)) |
|---|---|---|---|---|---|---|---|
| busiest | **36.5 +/- 29.3** | 36.5 +/- 29.3 | 61.2 +/- 77.0 | 1100.3 +/- 623.2 | 679.6 +/- 58.4 | 679.4 +/- 58.5 | 0.21 +/- 0.09 |
| grid | **34.3 +/- 37.6** | 34.4 +/- 37.6 | 57.5 +/- 85.0 | 1075.6 +/- 665.8 | 679.6 +/- 58.6 | 679.4 +/- 58.6 | 0.23 +/- 0.13 |
| both sitings pooled (n = 6, NOT independent: the two sitings of a seed share the demand) | 35.4 +/- 12.8 | 35.4 +/- 12.8 | - | 1087.9 | 679.6 | 679.4 | 0.22 |

Service and operations (mean over seeds; CI only where informative):

| siting | method | served share | served share of servable orders | n_unserved | mean response, h | n_late (of 36) | mean lateness, h | bike km | swaps | kWh purchased | end full batteries (of 9) | (17) viol. | (18) viol. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 0.843 +/- 0.040 | 0.867 | 5.67 | 1.12 +/- 0.40 | 19.7 | 0.240 | 112.2 | 7.67 | 2.35 | 4.67 | 1 of 3 runs | 2 of 3 runs |
| busiest | ilp | 0.852 +/- 0.040 | 0.877 | 5.33 | 0.84 +/- 0.03 | 1.7 | 0.006 | 94.4 | 6.00 | 0.59 | 5.00 | 0 | 0 |
| busiest | ilp_relaxed | 0.852 | 0.877 | 5.33 | 0.84 | 1.7 | 0.006 | 94.2 | 8.00 | 0.00 | 1.00 | n/a | n/a |
| grid | baseline | 0.843 +/- 0.080 | 0.867 | 5.67 | 1.11 +/- 0.42 | 18.3 | 0.227 | 110.9 | 7.67 | 2.26 | 4.67 | 0 | 1 of 3 runs |
| grid | ilp | 0.852 +/- 0.040 | 0.877 | 5.33 | 0.84 +/- 0.03 | 1.7 | 0.006 | 94.6 | 6.33 | 0.70 | 5.00 | 0 | 0 |
| grid | ilp_relaxed | 0.852 | 0.877 | 5.33 | 0.84 | 1.7 | 0.006 | 94.6 | 7.33 | 0.00 | 1.67 | n/a | n/a |

`served share of servable orders` for the ILP rows is computed here as n_served / (36 - n_unservable) (the script leaves that column empty for ILP rows; see anomalies). Structurally unservable orders (no delivery arc; both methods pay P): seed 0 none, seed 1 one, seed 2 two.

## 3. Per-instance table

| siting | seed | arcs | baseline USD | base. unserved | base. km | base. swaps | base. reports | ILP USD | status | MIP gap | time, s | ILP unserved | ILP km | ILP swaps | MIP-start variant | relaxed USD | status | time, s | gap written, % | gap relaxed, % | gap_vs_ilp, % | ILP - relaxed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | 0 | 729,139 | 1374.68 | 5 | 119.3 | 9 | (18) | 706.08 | OPTIMAL | 0 | 60.0 | 6 | 90.0 | 6 | baseline_round1 | 705.87 | OPTIMAL | 55.5 | 48.64 | 48.65 | 94.69 | 0.21 |
| busiest | 1 | 530,382 | 1043.48 | 6 | 110.9 | 6 | - | 671.51 | OPTIMAL | 0 | 34.3 | 5 | 102.2 | 6 | default | 671.33 | OPTIMAL | 31.7 | 35.65 | 35.66 | 55.39 | 0.18 |
| busiest | 2 | 511,370 | 882.69 | 6 | 106.4 | 8 | (17) | 661.16 | OPTIMAL | 0 | 36.7 | 5 | 90.9 | 6 | baseline_round1 | 660.91 | OPTIMAL | 36.3 | 25.10 | 25.13 | 33.51 | 0.25 |
| grid | 0 | 720,006 | 1338.39 | 5 | 115.7 | 9 | (18) | 706.16 | OPTIMAL | 0 | 54.2 | 6 | 90.6 | 6 | baseline_round1 | 705.94 | OPTIMAL | 51.0 | 47.24 | 47.25 | 89.53 | 0.21 |
| grid | 1 | 525,584 | 1085.71 | 7 | 112.7 | 7 | - | 671.76 | OPTIMAL | 0 | 28.1 | 5 | 104.3 | 6 | default | 671.58 | OPTIMAL | 34.1 | 38.13 | 38.14 | 61.62 | 0.18 |
| grid | 2 | 490,210 | 802.70 | 5 | 104.4 | 7 | - | 661.01 | OPTIMAL | 0 | 35.7 | 5 | 88.8 | 7 | default | 660.73 | OPTIMAL | 29.7 | 17.65 | 17.69 | 21.44 | 0.28 |

`base. reports` = constraint families the baseline reports violated (not enforced). The baseline policy itself runs in 3.8-4.9 ms per instance.

## 4. Cost components (26)-(32), mean over seeds, USD

| siting | method | total | C_setup (27) | C_elec (28) | C_travel (29) | unserved P u (30) | response (31) | lateness (31) | C_reb (32) |
|---|---|---|---|---|---|---|---|---|---|
| busiest | baseline | 1100.28 | 39.57 | 0.75 | 13.46 | 170.0 | 612.5 | 264.0 | 0 |
| busiest | ilp | 679.58 | 39.57 | 0.19 | 11.32 | 160.0 | 462.5 | 6.0 | 0 |
| busiest | ilp_relaxed | 679.37 | 39.57 | 0.00 | 11.30 | 160.0 | 462.5 | 6.0 | 0 |
| grid | baseline | 1075.60 | 39.57 | 0.72 | 13.31 | 170.0 | 604.0 | 248.0 | 0 |
| grid | ilp | 679.64 | 39.57 | 0.23 | 11.35 | 160.0 | 462.5 | 6.0 | 0 |
| grid | ilp_relaxed | 679.42 | 39.57 | 0.00 | 11.35 | 160.0 | 462.5 | 6.0 | 0 |

Gap decomposition (baseline - ILP, mean over seeds):

| siting | total gap, USD | lateness | response | unserved | travel | electricity |
|---|---|---|---|---|---|---|
| busiest | 420.7 | 258.0 (61.3 %) | 150.0 (35.7 %) | 10.0 (2.4 %) | 2.1 (0.5 %) | 0.6 (0.1 %) |
| grid | 396.0 | 242.0 (61.1 %) | 141.5 (35.7 %) | 10.0 (2.5 %) | 2.0 (0.5 %) | 0.5 (0.1 %) |

## 5. Siting sensitivity (grid-connected minus busiest, same demand per seed)

| seed | baseline busiest | baseline grid | delta, USD | delta, % | ILP busiest | ILP grid | delta, USD | delta, % | relaxed delta, % | gap busiest, % | gap grid, % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 1374.68 | 1338.39 | -36.29 | -2.64 | 706.08 | 706.16 | +0.07 | +0.01 | +0.01 | 48.64 | 47.24 |
| 1 | 1043.48 | 1085.71 | +42.23 | +4.05 | 671.51 | 671.76 | +0.25 | +0.04 | +0.04 | 35.65 | 38.13 |
| 2 | 882.69 | 802.70 | -79.98 | -9.06 | 661.16 | 661.01 | -0.15 | -0.02 | -0.03 | 25.10 | 17.65 |
| mean | 1100.28 | 1075.60 | -24.68 | -2.55 | 679.58 | 679.64 | +0.06 | +0.01 | +0.01 | 36.46 | 34.34 |

The ILP optimum is insensitive to the siting (|delta| <= 0.25 USD, <= 0.04 %); the baseline moves by -9 % to +4 % with no consistent sign. The two sitings differ only in the site nodes and the bikes' start nodes (round robin over the sites); orders, prep times, restaurant ranks and q0 are identical (hash-asserted).

## 6. Demand comparison with the synthetic `usd4h` family (same seeds, 108 pooled orders each)

| descriptor | NYC semi-real (`nyc4h`) | synthetic `usd4h` |
|---|---|---|
| restaurants available | 4,607 DOHMH rows in the box (3,406 samplable after the `other` exclusion) | 8 synthetic |
| distinct restaurants hit per seed | 32, 32, 33 | 8, 8, 8 |
| top-10 restaurants' share of orders | 0.39, 0.39, 0.36 | 1.00, 1.00, 1.00 |
| top-3 restaurants' share | 0.19, 0.19, 0.17 | 0.64, 0.61, 0.58 |
| customer zones hit per seed | 11, 8, 9 (of 13 NTA-2020 with grid nodes) | 13, 13, 14 (of 16 synthetic zones) |
| mean restaurant -> customer route, km | 1.79, 1.79, 1.70 (mean 1.76) | 1.67, 1.90, 1.74 (mean 1.77) |
| max route, km | 3.3, 3.3, 3.3 | 4.2, 4.05, 3.45 |
| mean prep, min | 29.6, 29.9, 29.7 | 29.3, 29.9, 28.6 |
| promise after ready | 5 slots (25 min) | 5 slots |
| L1 distance of realised cuisine shares to the Kaggle target | **0.199** | 0.313 |
| zone weights | ACS 2020-24 literature formula | synthetic Dirichlet demographics |

Cuisine mix (pooled over seeds; Kaggle target / NYC realised / synthetic realised): American 0.308 / 0.315 / 0.296; Japanese 0.248 / 0.231 / 0.315; Italian 0.157 / 0.213 / 0.241; Chinese 0.113 / 0.074 / 0.102; Mexican 0.041 / 0.037 / 0.046; Indian 0.038 / 0.046 / 0; Middle Eastern 0.026 / 0.028 / 0; Mediterranean 0.024 / 0 / 0; Thai 0.010 / 0.009 / 0; French 0.009 / 0 / 0; Southern 0.009 / 0.028 / 0; Korean 0.007 / 0.009 / 0; Spanish 0.006 / 0 / 0; Vietnamese 0.004 / 0.009 / 0. The synthetic family has restaurants in only 5 cuisines, so 9 classes are structurally absent there; the NYC box covers all 14 (Mediterranean, French and Spanish simply did not come up in 108 draws).

Customer zone shares (sampling law = ACS zone-weight mass of the grid nodes / realised over 108 orders): MN0603 Murray Hill-Kips Bay 0.203 / 0.120; MN0402 Hell's Kitchen 0.200 / 0.176; MN0401 Chelsea-Hudson Yards 0.178 / 0.231; MN0501 Midtown South-Flatiron-Union Sq 0.099 / 0.139; MN0604 East Midtown-Turtle Bay 0.098 / 0.111; MN0502 Midtown-Times Square 0.069 / 0.046; MN0602 Gramercy 0.066 / 0.074; MN0802 UES-Carnegie Hill 0.034 / 0.037; MN0203 West Village 0.020 / 0; MN0701 UWS-Lincoln Sq 0.013 / 0.037; MN0601 Stuy Town 0.009 / 0; MN0202 Greenwich Village 0.008 / 0.019; MN0801 UES-Lenox Hill 0.005 / 0.009 (L1 realised vs law 0.32 at 36 orders per seed; the top three zones hold 58 % of the mass and received 53 % of the orders).

NYC restaurant top-10 (pooled; orders): SKY PAVILION (Chinese) 3, YAKINIKU FUTAGO (Japanese) 3, HERALD SQUARE CAFE (American) 3, RESTAURANT 555 (Italian) 2, PANDA EXPRESS (Chinese) 2, YAMA (Japanese) 2, TEPPEN RAMEN (Japanese) 2, ELEMENT HOTEL TIME SQUARE (American) 2, HOLIDAY INN EXPRESS NYC TIMES SQUARE (American) 1, IKAZAYA FUTAGO (Japanese) 1. Synthetic top-10: node (7,14) Italian 11, (12,4) Japanese 10, (13,1) Italian 9, (7,0) American 8, (11,12) Japanese 7, (2,4) Italian 6, (6,0) Chinese 5, (7,13) Japanese 5, (12,14) American 5, (11,17) Japanese 5.

Unreachable supply: 1,201 of the 4,607 box restaurants (26.1 %) are mapped to `other` (Coffee/Tea 460, Bakery 113, 'Other' 111, Donuts 76, Juice 71, Asian/Asian Fusion 70, Frozen Desserts 46, Latin American 40, ...) and can never be sampled; citywide the share is 32.5 % (units review F3, declared assumption; `cuisine_map_overrides` with `CUISINE_MAP_CAFES_AS_AMERICAN` lowers it to 8.9 % but was not run).

## 7. Solver statistics

| siting | method | arcs (mean / max) | binaries (mean / max) | rows (mean / max) | library build, s | model build, s | runtime, s (mean / max) | MIP gap (max) | B&B nodes | status | MIP start accepted | start variant |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest | ilp | 590,297 / 729,139 | 590,336 / 729,178 | 55,450 / 65,707 | 1.3 | 2.16 | 43.7 / 60.0 | 0.0 | 1 | 3 x OPTIMAL | 3 / 3 | baseline_round1 x2, default x1 |
| busiest | ilp_relaxed | 590,297 / 729,139 | 590,336 / 729,178 | 55,450 / 65,707 | 1.3 | 2.22 | 41.2 / 55.5 | 0.0 | 1 | 3 x OPTIMAL | 3 / 3 | default x3 |
| grid | ilp | 578,600 / 720,006 | 578,639 / 720,045 | 54,151 / 64,778 | 1.4 | 2.06 | 39.3 / 54.2 | 0.0 | 1 | 3 x OPTIMAL | 3 / 3 | baseline_round1 x1, default x2 |
| grid | ilp_relaxed | 578,600 / 720,006 | 578,639 / 720,045 | 54,151 / 64,778 | 1.4 | 2.03 | 38.3 / 51.0 | 0.0 | 1 | 3 x OPTIMAL | 3 / 3 | default x3 |

Totals: 12 ILP solves, 12 OPTIMAL, **0 TIME_LIMIT**, every solve closed at the root node (node_count 1) with the baseline MIP start; mean 584,488 binaries (490 k - 729 k), mean runtime 40.6 s (max 60.0 s) at Threads 3 against the 300 s limit; baseline 3.8-4.9 ms per instance; whole experiment 9.4 min wall. For scale, the synthetic `usd4h` family at the same size has 1.9 M arcs under the plan pruning (`PRUNING_NYC` cuts the NYC family to 0.58 M by allowing moves only into the 3 site nodes).

## 8. Figures (all verified present in `outputs/e8_nyc_fixed/`, written 17:52 together with `results.csv`; none regenerated)

- `map_seed0.png` -- nyc4h-busiest-seed0: 150 m grid nodes in the rotated frame (axes in metres, azimuth stated), DOHMH restaurants coloured by Kaggle cuisine (American 1846, Italian 412, Japanese 247, Chinese 152, Mexican 140, Korean 136, Mediterranean 115, other cuisines 1559), ACS zone-weight density heat (colour bar, per km^2, clipped to the box) with NTA labels, the 32 restaurants and 36 customers of the seed, the `busiest` sites (stars S1-S3) and the `grid` sites (crosses, labelled), and the six ILP bike paths with q0. Renders as required.
- `cost_components.png` -- stacked components (27)-(32) per method and siting, y axis "mean cost over 3 seeds (USD, usd_sunk)", totals annotated.
- `gap_by_seed.png` -- headline gap per seed (dots) and mean with 95 % t-CI (bars) for written and relaxed ILP, both sitings, y axis "gap = 100 (baseline - ILP) / baseline, %".
- `demand_comparison.png` -- cuisine shares (Kaggle target vs NYC realised vs synthetic realised, %) and NTA customer shares (sampling law vs realised, %).

## 9. Anomalies and notes

1. `outputs/e8_nyc/` (pre-fix) is superseded: its nyc4h instances were generated with the hour-top interpolated (ramp) release profile (units review F1), which also changed the rejection-sampled orders, destinations and q0; its headline was 27.3 % +/- 29.4 (busiest) / 26.5 % +/- 37.1 (grid) with baseline 901 vs ILP 644 USD and served shares 94 % vs 91 %. Not comparable instance by instance; do not cite.
2. MIP-start fallback: the default R2.3 baseline schedule violated (18) on busiest-seed0, grid-seed0 and busiest-seed2 and the `baseline_round1` schedule was injected instead (all accepted and verified OPTIMAL as fixed starts); the `baseline` rows still report the default policy.
3. The baseline reports (18) violated in 3 of 6 runs (end-stock shortfall 1.5, 0.5 batteries) and (17) in 1 of 6; both are reported, not priced, which makes the written-ILP gap conservative. The relaxed control confirms this: it moves the gap by at most 0.04 points.
4. The ILP drops MORE orders than the baseline on seed 0 (6 vs 5, both sitings) and fewer on seeds 1-2; it trades one dropped order (P = 30) for response and lateness savings. Mean served share 85.2 % vs 84.3 %.
5. `served_share_servable` is populated only for the baseline rows in `results.csv` (empty for `ilp` / `ilp_relaxed`); the ILP values in section 2 were derived from n_served and n_unservable.
6. `queue_wait_slots` is larger for the ILP (11-17 mean) than for the baseline (3-6): the ILP parks bikes at sites between jobs and those waiting arcs are counted by the metric; it is not a swap queue (sigma 1, swaps 6-8 per run).
7. The relaxed ILP buys no electricity at all (kWh 0, end full batteries 1-1.7 of 9, 38-41 stock-out slots), i.e. without end targets the 9 spare batteries alone cover the 4 h window; the written ILP charges 0.59-0.70 kWh to meet (17)-(18) at a cost of 0.21-0.23 USD.
8. `RESULTS.md` written by the script ends with "all in `outputs/e8_nyc/`" (stale string at `experiments/e8_nyc_fixed.py` line 1046); the files are in `outputs/e8_nyc_fixed/`. Cosmetic; package left untouched (read-only brief).
9. With n = 3 the 95 % t half-widths (29-38 points) are wider than the means; the pooled n = 6 CI (+/- 12.8) is optimistic because the two sitings share the demand of each seed. Seed 0 dominates (gap 48 %) because its baseline accumulates 447 USD of lateness.
10. `map_seed0.png` legend shows "other cuisines (1559)": this is the 1,201 unmapped `other` rows plus the 358 restaurants in the eight mapped-but-unlisted small classes; not an inconsistency with the 26.1 % share.

## 10. Interpretation

On the semi-real Midtown instance the coordinated E2 ILP cuts the round-2 baseline's cost by 36.5 % (+/- 29.3, n = 3) at the busiest-cell siting and 34.3 % (+/- 37.6) at the grid-connected siting, and the fair relaxed control (rho 0, R_end 0) gives the same numbers to within 0.04 points, so none of the advantage is manufactured by the end-of-window targets (their price in the optimum is 0.21-0.23 USD). Because `PRUNING_NYC` restricts only the ILP, these are lower bounds on the coordination value under the written model. The magnitude is in line with the synthetic `usd4h` family of the same size under the same round-2 rules (seeds 0-1 in `outputs/r2_probe/`: 16.1 % and 32.2 %) and with round 1's 24.0 % +/- 8.7 (toy units, 10 bikes, 2 h, `baseline_round1` rules), but its composition is entirely different: in round 1 90 % of the gap was unserved-order penalty at P = 100, whereas here 61 % is lateness, 36 % response time and only 2.4 % unserved orders, because at P = 30 and w = 18 $/h a dropped order is worth about 1.7 h of customer waiting and both methods drop 5-6 of 36 orders (0-2 of them structurally unservable). The ILP's lever is therefore sequencing, not coverage: it serves 85 % of the orders with a mean response of 0.84 h and 1.7 late deliveries per run, against 84 %, 1.12 h and 19 late deliveries for the nearest-rider FIFO policy, while riding 16 % fewer kilometres (94 vs 112 km) and buying a quarter of the electricity (0.6 vs 2.3 kWh). Unlike round 1, charging now occurs in both methods and the baseline's DEMAND_AWARE rule leaves end-stock targets unmet in 4 of 6 runs, but with 9 spare batteries for 6 bikes over 4 h the battery side is still not binding (the relaxed ILP never charges), so E8 again says nothing about station queues or grid limits. Siting is a strong test of robustness: moving the three sites to 8th Ave/W 34th, Union Square and Grand Central changes the ILP optimum by at most 0.25 USD (0.04 %) on every seed, whereas the baseline moves by -9 % to +4 % depending on the seed, i.e. the coordinated schedule absorbs where the sites are and the myopic policy does not. The demand side is more realistic than the synthetic family in the ways R2.4 intended -- cuisine mix within L1 0.20 of the Kaggle shares (0.31 synthetic), about 32 distinct restaurants per seed instead of 8 (top-10 share 0.38 vs 1.0), customers spread over 8-11 NTAs with Chelsea/Hudson Yards, Hell's Kitchen and Murray Hill/Kips Bay carrying half of the mass -- yet trip geometry is almost identical (mean restaurant -> customer route 1.76 vs 1.77 km) because both families live on the same 150 m grid with the same speed and energy physics; the semi-real instance changes where the demand sits, not how far bikes ride. Three caveats bound the claim: the geometry is synthetic (rotated grid, synthetic elevation and signals, one shortest grid route per pair), 26 % of the box's restaurants (cafes, bakeries, desserts, juice, Asian fusion, Latin American) are unreachable by the cuisine mapping, and with 3 seeds the confidence intervals are wider than the means, so the result should be read as "the ILP advantage survives real restaurant and customer geography" rather than as a precise percentage. Computationally the NYC family is the cheapest of round 2: 0.58 M binaries per ILP, all 12 solves optimal at the root node in 28-60 s, so more seeds and the lossless `--targets default` probe are affordable follow-ups.
