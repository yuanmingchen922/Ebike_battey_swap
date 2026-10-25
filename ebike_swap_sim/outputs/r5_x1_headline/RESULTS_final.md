# X1: Headline re-validation, round 5 (final report)

Source: `outputs/r5_x1_headline/` (`records.jsonl`, 640 records, last record per key (family, calib, seed, mult, targets, method); `per_instance.csv`, `stages.csv`, `shapley.csv`, `components.csv`, `metric_pack.csv`, `solver.csv`, `summary.json`; log `outputs/r5_lanes/r5_x1_headline.log`). Figures and tables were recomputed from the records by `figs/x1_final.py` (tables: `figs/x1_tables.py`) into `stages_final.csv`, `per_instance_final.csv`, `metric_pack_ci_final.csv` and `summary_final.json`. An independent recomputation of the headline from the raw records matches the script's per-instance values to 4e-15 percentage points.

## Summary

The round-3 coordination gains were 29.55 % (usd4h, n = 30) and 31.82 % (nyc4h, n = 10). Three corrections were applied: (a) eBaaS energy calibration, (b) a per-instance best-rule baseline (minimum over r2, r5_range and r5), and (c) like-for-like relaxed targets (rho = 0, R_end = 0) scored with the M1 end-state adjustment. After these, the headline is **27.17 % ± 5.96 on usd4h (n = 30, 30/30 positive)** and **27.37 % ± 7.11 on nyc4h (n = 10, 10/10 positive)**. That is 92 % and 86 % of the round-3 values. The total loss is 2.38 points on usd4h (paired 95 % CI ± 2.25) and 4.46 points on nyc4h (± 2.41). Under a Shapley split the attribution depends on the family and the demand level. On pooled usd4h the stronger baseline (b) accounts for most of the loss (-1.93 ± 0.76 of -2.38 points, 81 %), while the pooled calibration term (a = -0.41 ± 1.83, not distinguishable from zero) is a cancellation: calibration lowers the gap at x0.75 (-2.22) and x1 (-1.35) and raises it at x1.5 (+2.34 ± 1.24). On nyc4h, calibration and baseline contribute equally (-2.20 points each; paired a - b = 0.00 ± 1.97), and at usd4h x1 they are also about equal (-1.35 vs -1.51). The like-for-like targets and the end-state adjustment together move the gap by less than 0.1 point. Survival depends strongly on demand. At x0.75 only 64 % of the gain survives (9.78 % ± 2.88). At x1 91 % survives (28.28 % ± 7.36). At x1.5 the gain grows slightly to 43.45 % ± 5.86 (103 %). Lateness (50 %), response time (26-34 %) and unserved penalties (16-23 %) make up almost the whole saving. Electricity, travel and the end-state term together contribute under 1 %. Every ILP behind the headline is OPTIMAL (gap at most 9.6e-5) under the protocol settings: aggregated flow, Threads 3, Seed 0, TimeLimit 300 s. The nyc4h values are lower bounds, because PRUNING_NYC restricts only the ILP.

Notation: "± h" is the half-width of the exact Student-t 95 % confidence interval (t_{0.975, n-1} s / sqrt(n)); every group has n >= 10. Gap = 100 (baseline - ILP) / baseline per instance, then averaged. S0 = round 3 (legacy energy, r2 rule, written targets, raw total (26)); S1 = (a) eBaaS calibration; S2 = (b) + per-instance best rule; S3 = (c1) + relaxed targets (raw total); S4 = (c2) + end-state adjustment = round-5 headline. For the relaxed ILP, the better of the relaxed and the written optimum is used, chosen by the raw objective. In all 40 cells this was the relaxed solve.

## Coverage

| Block | Rows (last per key) | Status |
|---|---|---|
| eBaaS ILP, written targets | 40 | 40 OPTIMAL (max MIP gap 9.6e-5; check_ok 40/40) |
| eBaaS ILP, relaxed targets | 40 | 40 OPTIMAL (max MIP gap 9.6e-5; check_ok 40/40) |
| eBaaS rule rows (r2, r5_range, r5 x 2 target copies) | 240 | 240 POLICY |
| Legacy ILP, written (copied round-3 rows, per-bike model) | 40 | 38 OPTIMAL, 2 TIME_LIMIT (usd4h seed 0 x1 gap 0.036 %; seed 7 x1.5 gap 0.114 %) |
| Legacy ILP, relaxed (copied round-3 rows) | 40 | 40 OPTIMAL |
| Legacy rule rows | 240 | 240 POLICY |
| SKIPPED_BUDGET / errors | 0 | none; duplicate keys 0; run wall time 73.7 min of a 150 min budget |

ILP settings on the eBaaS rows: aggregated flow (O1), Threads 3, Gurobi Seed 0, TimeLimit 300 s. Mean / max runtime was 37.5 / 111.9 s (usd4h relaxed), 71.2 / 211.8 s (usd4h written), 13.6 / 19.5 s (nyc4h relaxed) and 19.7 / 36.3 s (nyc4h written). The r5_transfer variant does not apply because no instance has services (n_services = 0). Orders are identical to the legacy instances in 40/40 cells, and the round-3 r2 baseline total is reproduced in 40/40 cells.

## Table 1. Survival path, gap (%) by stage (mean ± 95 % CI)

| Group | n | S0 round 3 | S1 (a) eBaaS | S2 (b) best rule | S3 (c1) relaxed | S4 (c2) headline | S4 min-max | S4 > 0 | S4 / S0 |
|---|---|---|---|---|---|---|---|---|---|
| usd4h (all) | 30 | 29.55 ± 5.61 | 28.91 ± 5.69 | 27.21 ± 5.96 | 27.25 ± 5.95 | 27.17 ± 5.96 | 5.3-54.4 | 30/30 | 0.92 |
| usd4h x0.75 | 10 | 15.36 ± 7.28 | 13.25 ± 4.10 | 9.83 ± 2.89 | 9.87 ± 2.88 | 9.78 ± 2.88 | 5.3-18.0 | 10/10 | 0.64 |
| usd4h x1 | 10 | 31.18 ± 9.05 | 29.08 ± 7.48 | 28.32 ± 7.35 | 28.37 ± 7.35 | 28.28 ± 7.36 | 12.9-43.8 | 10/10 | 0.91 |
| usd4h x1.5 | 10 | 42.11 ± 5.66 | 44.40 ± 5.88 | 43.47 ± 5.86 | 43.50 ± 5.86 | 43.45 ± 5.86 | 24.5-54.4 | 10/10 | 1.03 |
| nyc4h | 10 | 31.82 ± 8.19 | 29.45 ± 8.04 | 27.40 ± 7.10 | 27.46 ± 7.11 | 27.37 ± 7.11 | 17.9-44.2 | 10/10 | 0.86 |

The sequential stage steps for usd4h are S1 - S0 = -0.64, S2 - S1 = -1.70, S3 - S2 = +0.04 and S4 - S3 = -0.08 points. For nyc4h they are -2.37, -2.05, +0.05 and -0.09.

## Table 2. Shapley split of S0 -> S4 (exact 3-factor Shapley over (a), (b), (c1) on raw totals, plus the end-adjustment step)

| Group | n | S0 (%) | (a) calibration (pts) | (b) best rule (pts) | (c1) relaxed targets (pts) | (c2) end adjustment (pts) | S4 (%) | Survival S4/S0 | Paired S4 - S0 (pts, 95 % CI) | Instances with S4 < S0 |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 30 | 29.55 | -0.41 | -1.93 | +0.04 | -0.08 | 27.17 | 0.92 | -2.38 ± 2.25 | 15/30 |
| usd4h x0.75 | 10 | 15.36 | -2.22 | -3.31 | +0.04 | -0.09 | 9.78 | 0.64 | -5.58 ± 5.86 | 6/10 |
| usd4h x1 | 10 | 31.18 | -1.35 | -1.51 | +0.04 | -0.09 | 28.28 | 0.91 | -2.91 ± 3.20 | 7/10 |
| usd4h x1.5 | 10 | 42.11 | +2.34 | -0.98 | +0.03 | -0.05 | 43.45 | 1.03 | +1.33 ± 1.17 | 2/10 |
| nyc4h | 10 | 31.82 | -2.20 | -2.20 | +0.04 | -0.09 | 27.37 | 0.86 | -4.46 ± 2.41 | 9/10 |

Uncertainty of the Shapley terms (digest correction, recomputed from `records.jsonl`; per-instance Shapley values, mean ± 95 % t half-width; instances with a negative contribution in brackets):

| Group | n | (a) calibration | (b) best rule | (a) - (b) paired |
|---|---|---|---|---|
| usd4h | 30 | -0.41 ± 1.83 (11/30) | -1.93 ± 0.76 (26/30) | +1.52 ± 1.68 |
| usd4h x0.75 | 10 | -2.22 ± 4.91 (4/10) | -3.31 ± 1.99 (10/10) | +1.09 ± 4.66 |
| usd4h x1 | 10 | -1.35 ± 2.70 (6/10) | -1.51 ± 0.93 (8/10) | +0.17 ± 2.47 |
| usd4h x1.5 | 10 | +2.34 ± 1.24 (1/10) | -0.98 ± 0.62 (8/10) | +3.31 ± 1.58 |
| nyc4h | 10 | -2.20 ± 1.90 (8/10) | -2.20 ± 1.09 (9/10) | +0.00 ± 1.97 |

The baseline step (b) is significantly negative in every group. The calibration step (a) is significant only at x1.5 (positive) and on nyc4h (negative); at x0.75 its point estimate is large but its interval includes zero.

## Table 3. Costs in USD per 4-h window (eBaaS, mean ± 95 % CI); price of recovery = written - relaxed ILP

| Group | n | Best rule, end-adj. (USD) | ILP relaxed, end-adj. (USD) | Saving (USD) | Price of recovery raw (USD) | Price of recovery end-adj. (USD) | C_end_adjust best rule (USD) | C_end_adjust ILP (USD) | Best rule picked (r5_range / r2) |
|---|---|---|---|---|---|---|---|---|---|
| usd4h (all) | 30 | 1031.39 ± 220.50 | 667.17 ± 90.56 | 364.22 ± 133.98 | 0.38 ± 0.08 | -0.04 ± 0.04 | 0.95 ± 0.07 | 1.39 ± 0.07 | 17 / 13 |
| usd4h x0.75 | 10 | 476.89 ± 25.40 | 429.15 ± 12.54 | 47.74 ± 16.92 | 0.20 ± 0.08 | -0.04 ± 0.07 | 0.83 ± 0.13 | 1.18 ± 0.10 | 7 / 3 |
| usd4h x1 | 10 | 830.91 ± 109.17 | 582.04 ± 18.40 | 248.87 ± 93.15 | 0.41 ± 0.10 | -0.03 ± 0.06 | 0.99 ± 0.12 | 1.45 ± 0.07 | 4 / 6 |
| usd4h x1.5 | 10 | 1786.38 ± 201.61 | 990.33 ± 27.77 | 796.06 ± 181.03 | 0.53 ± 0.16 | -0.06 ± 0.09 | 1.04 ± 0.08 | 1.55 ± 0.09 | 6 / 4 |
| nyc4h | 10 | 834.74 ± 101.69 | 593.77 ± 10.56 | 240.98 ± 95.41 | 0.45 ± 0.12 | -0.04 ± 0.04 | 0.90 ± 0.09 | 1.41 ± 0.11 | 6 / 4 |

## Table 4. Decomposition of the headline saving by cost component (best rule - ILP, USD per window, end-adjusted)

| Component | usd4h saving (USD, n = 30) | share | nyc4h saving (USD, n = 10) | share |
|---|---|---|---|---|
| Unserved penalty | 83.00 ± 37.75 | 22.8 % | 39.00 ± 32.07 | 16.2 % |
| Response time | 96.15 ± 36.90 | 26.4 % | 82.65 ± 52.40 | 34.3 % |
| Lateness | 183.80 ± 75.04 | 50.5 % | 118.20 ± 67.87 | 49.1 % |
| Travel | 1.05 ± 0.40 | 0.3 % | 0.98 ± 0.71 | 0.4 % |
| Electricity | 0.66 ± 0.05 | 0.2 % | 0.65 ± 0.11 | 0.3 % |
| End-state adjustment | -0.44 ± 0.07 | -0.1 % | -0.50 ± 0.09 | -0.2 % |
| Setup | 0.00 ± 0.00 | 0.0 % | 0.00 ± 0.00 | 0.0 % |
| Rebalancing | 0.00 ± 0.00 | 0.0 % | 0.00 ± 0.00 | 0.0 % |
| Total, end-adjusted | 364.22 ± 133.98 | 100.0 % | 240.98 ± 95.41 | 100.0 % |

## Table 5. A3 metric pack, best rule vs ILP with relaxed targets (eBaaS; mean ± 95 % CI; paired ILP - rule difference)

| Metric (unit) | usd4h best rule | usd4h ILP | usd4h ILP - rule | nyc4h best rule | nyc4h ILP | nyc4h ILP - rule |
|---|---|---|---|---|---|---|
| Served share (-) | 0.85 ± 0.05 | 0.91 ± 0.03 | +0.06 ± 0.02 | 0.91 ± 0.03 | 0.94 ± 0.01 | +0.04 ± 0.03 |
| Unserved orders (count) | 7.23 ± 3.04 | 4.47 ± 1.93 | -2.77 ± 1.26 | 3.40 ± 1.08 | 2.10 ± 0.53 | -1.30 ± 1.07 |
| Late orders (count) | 13.30 ± 3.62 | 0.40 ± 0.21 | -12.90 ± 3.61 | 14.70 ± 4.86 | 0.80 ± 0.45 | -13.90 ± 5.03 |
| Bike km (km) | 119.44 ± 7.07 | 110.69 ± 6.63 | -8.76 ± 3.34 | 119.56 ± 8.13 | 111.42 ± 5.90 | -8.14 ± 5.93 |
| Swaps (count) | 9.47 ± 0.59 | 8.10 ± 0.77 | -1.37 ± 0.71 | 8.80 ± 1.16 | 8.30 ± 0.76 | -0.50 ± 1.23 |
| BSR (-) | 0.92 ± 0.04 | 0.74 ± 0.07 | -0.18 ± 0.09 | 0.86 ± 0.07 | 0.53 ± 0.13 | -0.32 ± 0.11 |
| Min SBUR (-) | 0.62 ± 0.13 | 0.60 ± 0.11 | -0.02 ± 0.13 | 0.73 ± 0.19 | 0.77 ± 0.16 | +0.03 ± 0.18 |
| Mean SBUR (-) | 1.05 ± 0.07 | 0.90 ± 0.09 | -0.15 ± 0.08 | 0.98 ± 0.13 | 0.92 ± 0.08 | -0.06 ± 0.14 |
| Outage rate (-) | 0.09 ± 0.05 | 0.35 ± 0.09 | +0.26 ± 0.09 | 0.02 ± 0.04 | 0.32 ± 0.14 | +0.30 ± 0.15 |
| Energy-refused orders (count) | 0.77 ± 1.12 | 0.33 ± 0.27 | -0.43 ± 1.18 | 0.00 ± 0.00 | 0.10 ± 0.23 | +0.10 ± 0.23 |
| Station time (min per swap) | 6.05 ± 0.95 | 7.72 ± 0.94 | +1.67 ± 1.47 | 10.37 ± 2.92 | 23.19 ± 10.03 | +12.82 ± 9.75 |
| Wait before swap (min per swap) | 1.05 ± 0.95 | 2.72 ± 0.94 | +1.67 ± 1.47 | 5.37 ± 2.92 | 18.19 ± 10.03 | +12.82 ± 9.75 |
| Detour (km per swap) | 1.08 ± 0.13 | 0.69 ± 0.09 | -0.39 ± 0.13 | 1.10 ± 0.14 | 0.68 ± 0.19 | -0.42 ± 0.18 |
| Empty km per bike-hour (km/h) | 0.47 ± 0.07 | 0.72 ± 0.08 | +0.26 ± 0.09 | 0.46 ± 0.08 | 0.36 ± 0.05 | -0.10 ± 0.08 |
| Empty km share (-) | 0.09 ± 0.01 | 0.16 ± 0.02 | +0.07 ± 0.02 | 0.09 ± 0.01 | 0.08 ± 0.01 | -0.01 ± 0.01 |
| Network peak (kW) | 1.58 ± 0.11 | 0.20 ± 0.12 | -1.38 ± 0.14 | 1.50 ± 0.17 | 0.07 ± 0.10 | -1.43 ± 0.23 |
| Energy bought (kWh) | 2.29 ± 0.16 | 0.24 ± 0.16 | -2.05 ± 0.15 | 2.10 ± 0.32 | 0.06 ± 0.10 | -2.04 ± 0.35 |
| C_end_adjust (USD) | 0.95 ± 0.07 | 1.39 ± 0.07 | +0.44 ± 0.07 | 0.90 ± 0.09 | 1.41 ± 0.11 | +0.50 ± 0.09 |

The legacy-calibration metric pack and the per-variant rows (r2, r5_range, r5, written ILP) are in `metric_pack.csv`.

## Figures (`figs/`, PDF vector + PNG 300 dpi)

* `x1_survival_waterfall.{pdf,png}` (7.2 in): a waterfall from the round-3 gap through the Shapley steps (a), (b), (c1), (c2) to the round-5 headline. Panel (a) is usd4h (n = 30) and panel (b) is nyc4h (n = 10). The end bars show the mean with 95 % t-CI.
* `x1_gap_by_demand.{pdf,png}` (3.5 in): round-3 gap vs round-5 headline gap by demand multiplier (usd4h x0.75 / x1 / x1.5; nyc4h x1), as mean ± 95 % t-CI with per-instance points.
* `x1_component_decomposition.{pdf,png}` (3.5 in): headline saving by cost component, mean ± 95 % t-CI.
* `x1_metric_pack.{pdf,png}` (7.2 in): served share, BSR, mean SBUR, station time, outage rate, empty km per bike-hour, network peak kW and energy bought, best rule vs ILP.

## Anomalies and caveats

1. **The ILP outage rate is higher than the rule's** (usd4h 0.35 vs 0.09; nyc4h 0.32 vs 0.02). It comes mainly from the reserve-breach flag (a path visits q < q_res). In E2, constraint (9) imposes q_res only on the terminal certificate, so the ILP can legitimately discharge below the reserve in the middle of the horizon. Of the 82 outage flags on the chosen ILP rows, at most 11 can come from energy refusal, and none from stranding. Before the manuscript reports "outage" for the ILP, the metric needs to be redefined or split into its parts.
2. **ILP station time is longer on nyc4h** (23.2 vs 10.4 min per swap; the wait component is 18.2 vs 5.4 min). The metric counts idle wait slots before a swap as station time. The ILP uses the station as a free parking buffer, so this mostly measures deliberate waiting, not rider inconvenience. On usd4h the difference is +1.7 ± 1.5 min.
3. **With relaxed targets the ILP buys almost no energy** (0.24 / 0.06 kWh vs 2.29 / 2.10 kWh for the rule; peak 0.20 / 0.07 kW vs 1.58 / 1.50 kW). This is mostly recharging deferred past the window, which R_end = 0 allows, not lower energy use: the ILP leaves a larger end deficit, with C_end_adjust 1.39 / 1.41 vs 0.95 / 0.90 USD, so about two thirds (usd4h, +0.44 of -0.66 USD) to three quarters (nyc4h, +0.50 of -0.65 USD) of its electricity saving reappears in the end-state term. The lower in-window peak load is therefore not a grid benefit of coordination and should not be reported as one. The raw price of recovery is 0.38 / 0.45 USD, but end-adjusted it is -0.04 USD in both families. The end-adjusted relaxed optimum is therefore slightly worse than the written one, because the relaxed ILP minimises the raw objective (26), not the adjusted one. The effect is under 0.1 point of gap.
4. **Step (c1) is an ILP-only effect.** Rule totals are identical for the written and relaxed target copies in 240/240 pairs, so the like-for-like correction cannot lower the baseline.
5. **r5 and r5_range give identical results** in every cell (no services, so r5 reduces to r5_range). The best rule is r5_range in 23 cells and r2 in 17, with the written target copy picked in every case (ties).
6. **The S0 (legacy) and S1-S4 ILPs use different formulations**: per-bike round-3 rows vs the aggregated flow. Both are optimal, but per DECISIONS.md the O1 equivalence was checked only on the toy and three E2u optima. Step (a) therefore mixes the energy calibration with the formulation change. Since both are optimal, the difference should come from the calibration alone.
7. **Survival is heterogeneous across instances.** The headline gap is below the round-3 gap in 15/30 usd4h cells and 9/10 nyc4h cells. At x1.5 the calibration raises the gap (+2.34 points), so overall survival above 90 % on usd4h partly reflects cancellation across demand levels.

## Interpretation

The round-3 headline largely survives all three fairness corrections. Coordination still lowers the end-adjusted cost by 27.2 % on the synthetic usd4h family and by at least 27.4 % on the NYC-calibrated nyc4h family. Every instance stays positive, and every ILP is proved optimal. The reduction from about 30 % is significant but modest: -2.4 ± 2.2 points on usd4h and -4.5 ± 2.4 on nyc4h. On pooled usd4h most of it (-1.93 ± 0.76 points) comes from replacing the round-2 rule with a per-instance best of the operator-grade rules, whose range-aware swap trigger (r5_range) wins in 23 of 40 cells; the pooled calibration term (-0.41 ± 1.83) is a cancellation across demand levels. On nyc4h and at usd4h x1 the calibration and the stronger baseline contribute about equally (nyc4h -2.20 / -2.20 points). The calibration lowers the gap at x0.75 and x1 (point estimates -2.2 and -1.4 points, intervals include zero) and raises it at x1.5 (+2.3 ± 1.2 points), because cheaper energy per km leaves the rule's congestion-driven losses unchanged. The boundary-condition corrections are numerically negligible (under 0.1 point). With a 4-h window and a 0.6 kWh pack, end-state energy is worth about 1 USD against savings of hundreds of USD. The manuscript can therefore use the relaxed, end-adjusted gap as the headline with no material change to the conclusion. The saving is almost entirely service quality: late orders fall from about 13-15 to under 1 per window, and the served share rises by 4-6 points. Electricity and travel savings are well under 1 % of the total. This supports framing the value as coordinated dispatch and swap timing, not energy arbitrage. The metric pack shows the mechanism: the ILP takes shorter detours per swap in both families (-0.39 ± 0.13 and -0.42 ± 0.18 km) and rides fewer bike-km, but it swaps significantly less often only on usd4h (-1.37 ± 0.71 swaps; nyc4h -0.50 ± 1.23, not significant). Its much lower in-window peak load (1.4 kW less) and energy purchase are mostly recharging deferred past the window under R_end = 0, as the larger end deficit shows (anomaly 3), so they are not a grid benefit. It accepts more waiting at stations and a lower BSR, deliberately parking bikes near stations; empty km per bike-hour rises on usd4h (+0.26 ± 0.09) but falls on nyc4h (-0.10 ± 0.08). Outage and station-time metrics read against the ILP only because of how they are defined (anomalies 1-2), so they should be redefined or reported with their components. The demand gradient (10 % at x0.75, 28 % at x1, 43 % at x1.5) is the most robust finding to report: coordination is worth most when the network is congested.

## Appendix A. Per-instance values (eBaaS headline cells; S0 from the matching legacy cell)

| Family | Seed | Mult | S0 (%) | S1 (%) | S2 (%) | S3 (%) | S4 (%) | Best rule | Best rule end-adj. (USD) | ILP relaxed end-adj. (USD) | Price of recovery end-adj. (USD) | Round-3 ILP status (gap) | Round-5 ILP status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 0 | 0.75 | 3.65 | 7.81 | 6.45 | 6.45 | 6.33 | r5_range | 430.93 | 403.67 | +0.000 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 1 | 0.75 | 12.16 | 13.01 | 13.01 | 13.03 | 12.93 | r2 | 483.06 | 420.58 | -0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 2 | 0.75 | 3.75 | 9.75 | 5.30 | 5.36 | 5.29 | r5_range | 449.49 | 425.73 | +0.028 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 3 | 0.75 | 10.02 | 8.35 | 7.12 | 7.16 | 7.06 | r5_range | 475.00 | 441.48 | -0.052 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 4 | 0.75 | 4.96 | 10.34 | 8.34 | 8.39 | 8.29 | r5_range | 447.25 | 410.17 | -0.107 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 5 | 0.75 | 28.92 | 23.78 | 18.06 | 18.08 | 17.96 | r5_range | 561.29 | 460.46 | -0.292 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 6 | 0.75 | 27.47 | 15.62 | 6.87 | 6.91 | 6.86 | r5_range | 469.07 | 436.87 | +0.062 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 7 | 0.75 | 17.12 | 8.20 | 8.20 | 8.28 | 8.18 | r2 | 487.92 | 448.01 | +0.029 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 8 | 0.75 | 28.64 | 13.51 | 13.51 | 13.56 | 13.47 | r2 | 492.33 | 426.00 | -0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 9 | 0.75 | 16.88 | 22.17 | 11.43 | 11.47 | 11.43 | r5_range | 472.55 | 418.52 | -0.045 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 0 | 1 | 16.06 | 13.10 | 12.98 | 13.02 | 12.88 | r5_range | 613.10 | 534.16 | -0.231 | TIME_LIMIT (0.036 %) | OPTIMAL / OPTIMAL |
| usd4h | 1 | 1 | 32.23 | 29.77 | 29.77 | 29.80 | 29.71 | r2 | 830.79 | 583.98 | +0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 2 | 1 | 19.13 | 21.77 | 20.02 | 20.06 | 19.99 | r5_range | 730.17 | 584.22 | +0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 3 | 1 | 28.97 | 31.84 | 31.84 | 31.89 | 31.79 | r2 | 857.43 | 584.84 | +0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 4 | 1 | 10.27 | 14.18 | 14.02 | 14.08 | 13.98 | r5_range | 636.52 | 547.56 | +0.037 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 5 | 1 | 41.15 | 37.60 | 32.00 | 32.05 | 31.97 | r5_range | 867.66 | 590.25 | -0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 6 | 1 | 48.28 | 41.41 | 41.41 | 41.47 | 41.39 | r2 | 1005.12 | 589.14 | -0.044 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 7 | 1 | 35.78 | 27.86 | 27.86 | 27.91 | 27.84 | r2 | 829.88 | 598.82 | -0.062 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 8 | 1 | 45.19 | 43.85 | 43.85 | 43.91 | 43.83 | r2 | 1116.81 | 627.33 | +0.028 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 9 | 1 | 34.80 | 29.43 | 29.43 | 29.51 | 29.39 | r2 | 821.58 | 580.07 | +0.000 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 0 | 1.5 | 38.59 | 39.24 | 37.83 | 37.86 | 37.79 | r5_range | 1455.86 | 905.68 | -0.144 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 1 | 1.5 | 43.74 | 44.41 | 44.41 | 44.43 | 44.38 | r2 | 1819.62 | 1012.01 | -0.018 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 2 | 1.5 | 22.37 | 24.54 | 24.54 | 24.57 | 24.53 | r2 | 1285.96 | 970.55 | -0.018 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 3 | 1.5 | 43.10 | 48.79 | 46.20 | 46.23 | 46.17 | r5_range | 1866.18 | 1004.53 | -0.081 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 4 | 1.5 | 38.93 | 42.14 | 40.14 | 40.17 | 40.11 | r5_range | 1607.69 | 962.84 | +0.018 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 5 | 1.5 | 45.74 | 48.51 | 47.67 | 47.73 | 47.66 | r5_range | 1927.95 | 1009.16 | +0.199 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 6 | 1.5 | 51.82 | 54.44 | 54.44 | 54.46 | 54.42 | r2 | 2216.48 | 1010.23 | -0.028 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 7 | 1.5 | 46.11 | 47.98 | 47.98 | 48.01 | 47.96 | r2 | 1992.07 | 1036.63 | -0.009 | TIME_LIMIT (0.114 %) | OPTIMAL / OPTIMAL |
| usd4h | 8 | 1.5 | 46.62 | 50.09 | 49.35 | 49.37 | 49.32 | r5_range | 2021.14 | 1024.33 | -0.223 | OPTIMAL | OPTIMAL / OPTIMAL |
| usd4h | 9 | 1.5 | 44.10 | 43.85 | 42.15 | 42.16 | 42.11 | r5_range | 1670.85 | 967.29 | -0.268 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 0 | 1 | 48.64 | 47.69 | 44.21 | 44.27 | 44.19 | r5_range | 1100.54 | 614.18 | +0.036 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 1 | 1 | 35.65 | 31.18 | 27.27 | 27.31 | 27.21 | r5_range | 833.58 | 606.78 | -0.161 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 2 | 1 | 25.10 | 17.93 | 17.93 | 17.99 | 17.90 | r2 | 715.80 | 587.71 | -0.062 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 3 | 1 | 18.94 | 22.62 | 19.49 | 19.52 | 19.44 | r5_range | 758.01 | 610.65 | +0.000 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 4 | 1 | 37.28 | 35.40 | 32.88 | 32.96 | 32.85 | r5_range | 899.73 | 604.21 | -0.036 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 5 | 1 | 26.08 | 26.65 | 23.70 | 23.76 | 23.67 | r5_range | 753.94 | 575.47 | -0.097 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 6 | 1 | 20.25 | 17.91 | 17.91 | 17.97 | 17.88 | r2 | 702.24 | 576.70 | -0.009 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 7 | 1 | 37.04 | 27.50 | 27.50 | 27.58 | 27.47 | r2 | 799.09 | 579.61 | -0.018 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 8 | 1 | 49.34 | 48.01 | 43.49 | 43.52 | 43.44 | r5_range | 1058.06 | 598.41 | +0.000 | OPTIMAL | OPTIMAL / OPTIMAL |
| nyc4h | 9 | 1 | 19.92 | 19.64 | 19.64 | 19.69 | 19.61 | r2 | 726.43 | 583.95 | -0.045 | OPTIMAL | OPTIMAL / OPTIMAL |

## Digest corrections (2026-10-18)

Applied after the two-refuter verification pass; numbers recomputed from the records (no solves). Items marked "one verifier" are qualifiers added where only one verifier objected.

- C2 (Shapley attribution): both verifiers refuted the blanket statement that the stronger baseline (b) is the main source of the loss and that calibration matters mainly at low demand. Recomputed per-instance Shapley values from `records.jsonl` (identical point values): usd4h a = -0.41 +/- 1.83, b = -1.93 +/- 0.76; nyc4h a = -2.20 +/- 1.90, b = -2.20 +/- 1.09 (a - b = 0.00 +/- 1.97); usd4h x1 a = -1.35 +/- 2.70, b = -1.51 +/- 0.93; x0.75 a = -2.22 +/- 4.91; x1.5 a = +2.34 +/- 1.24. Summary, a new uncertainty table under Table 2 and the Interpretation were rewritten accordingly.
- C6 (metric pack): both verifiers refuted the unqualified 'the ILP swaps less ... far lower grid load'. The swap reduction is significant only on usd4h (nyc4h -0.50 +/- 1.23); the lower in-window energy purchase and peak load are mostly deferred recharging under R_end = 0 (C_end_adjust +0.44 / +0.50 USD against an electricity saving of 0.66 / 0.65 USD). Anomaly 3 and the Interpretation were rewritten.
