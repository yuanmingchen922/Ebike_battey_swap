# E3u final report -- transfers and separation under USD costs, 4 h window (round 3: seeds 0-4, all cells solved)

## Summary

On the usd4h family (6 bikes, 36 orders, 4 h evening peak, 9 spares and 6 chargers in every layout) with five seeds per cell, the ILP's total cost is lowest in the co-located layout (638.2 +/- 28.7 USD per window under the written end targets, 95 % t-CI, n = 5) and separation costs 52.2 +/- 1.6 USD with one charging hub and 81.4 +/- 1.6 USD with two, of which 29.19 / 58.38 USD is the hub fixed cost F_hub and the rest (23.1 / 23.1 USD) is operations; with the end targets relaxed the operational part vanishes (29.3 +/- 0.2 / 58.5 +/- 0.2 USD, i.e. F_hub plus 0-0.4 USD). The value of transfers is 0.01 +/- 0.03 USD in the co-located layout, 8.6 +/- 10.1 USD (1 hub) and 8.6 +/- 10.1 USD (2 hubs) under the written targets, and 0.00 / 0.00 / 0.00 USD once rho and R_end are set to 0, which confirms on five seeds the round-2 reading that there is no within-horizon replenishment value in a 4 h window and that all of the transfer value is the recovery-target effect (one 22 USD shuttle with 2 batteries lifts the swap cap of 4 imposed by (17)-(18) and recovers 2-3 orders). Against the R2.3 policy with transfer rule NONE the ILP saves 21.3 +/- 11.3 % (a), 18.4 +/- 10.6 % (b) and 17.8 +/- 10.4 % (c) under the written targets and 21.4 +/- 11.3 / 21.2 +/- 10.2 / 20.5 +/- 10.0 % under the relaxed ones; the policy's REORDER_POINT rule is more expensive than NONE on every layout and every seed (+165 to +207 USD mean, CIs excluding 0) because its 5-14 shuttles at 20 USD never rescue more than one order. All 60 ILP cells are now solved (50 OPTIMAL at the root or within 9 nodes, 10 TIME_LIMIT), and the 600 s re-solves of the separated / written / transfers-free cells did not close their gaps: every one of the 10 runs stopped at 1.8-2.0 % after 63-143 nodes, the four round-2 incumbents improved by at most 0.32 USD, so the written transfer values stay lower bounds (upper bounds 22.2 +/- 9.8 / 22.2 +/- 9.6 USD). The baseline rows are the same schedule under both target settings (F1), every solved ILP run passes the independent checker and identity (24), the policy's own NONE schedule is rejected as a MIP start only in the written no-transfers models of the separated layouts (10/60, expected: it violates (17)-(18) there), and the script's automatic analysis step crashed on a NaN in the reused round-2 rows, so this report was built directly from records.jsonl.

## Setup and provenance

- Script `experiments/e3u_round3.py` (design, instance builder, record layout and MIP-start candidates imported from `experiments/e3u_transfers_usd_fixed.py`), run 2026-10-12 22:00 to 2026-10-13 00:29, 150.1 min wall, single process, Gurobi OutputFlag 0, Threads 3, Seed 0, TimeLimit 300 s (600 s for the separated / written / transfers-free cells), wall budget 240 min (not exhausted: 0 SKIPPED_BUDGET).
- Inputs of this report: `outputs/e3u_round3/records.jsonl` (106 records, 106 unique keys, 0 duplicates; last record per key kept), `results.csv`, `run_stdout.log`, `wall_time.json`, 30 saved instances `instances/{layout}_{targets}_seed{s}.json`; `outputs/e3u/relaxed_baseline_recomputed.csv` for the 14 policy cells not rebuilt in round 3 (see anomalies).
- Rows by method and source: ILP round2 (reused OPTIMAL rows) 17, ILP round3 43; policy round3 46, policy round2_recomputed 14. ILP statuses: {'OPTIMAL': 50, 'TIME_LIMIT': 10}.
- Family `usd4h` (R2.2): 6 bikes, 36 orders, H = 48 (Delta 5 min, 17:00-21:00), L = 12, initial bike levels 4-7 of 12; `usd_sunk` costs (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, f_e 20 $ per shuttle run, v_reb 1 $ per battery, F 12.03 / F_hub 29.19, bB 0.332, bC 0.082 per 4 h). Equal totals in every layout: sum B = 9 (3 per swap site, hubs 0), sum C = 6 (2 per co-located site; 6 at the single hub; 3 + 3 at two hubs), one grid group of 8 kW (6 kW 18-20 h). Shuttles every 6 slots from t = 2, U_e = 6. Written targets rho 0.5, R_end_j = 1 at swap sites; relaxed control rho 0, R_end 0. Pruning tau_max 4, start_slack 6, reachable pruning (lossless).
- Policy (baseline) = R2.3 rules: stock-aware nearest-feasible dispatch, threshold swapping, FCFS, DEMAND_AWARE charging at co-located sites and HIGH_FIRST / ASAP at charge-only hubs (`hub_charge_rule`, fairness F3), transfer rule NONE (default) or REORDER_POINT; on the relaxed copies the policy keeps the written R_end as its reserve (fairness F1), so the written and relaxed policy rows are the same schedule (asserted on all 60 rows, 0 mismatches).
- Gap definition everywhere: 100 (policy - ILP) / policy on the same instance and the same end-target setting; recomputed here from the merged policy table (the `gap_vs_baseline_*` columns of the reused round-2 relaxed co-located rows were computed against the pre-F1 policy and are not used).
- 95 % t-CI = t_{0.975, n-1} s / sqrt(n) over seeds (n = 5 everywhere; shown as mean +/- half-width).

## Headline numbers

- ILP total (USD per 4 h, transfers free): written (a) 638.2 +/- 28.7, (b) 690.5 +/- 29.0, (c) 719.7 +/- 29.0; relaxed 637.9 +/- 28.8 / 667.1 +/- 28.7 / 696.3 +/- 28.7. Round 2 (2 seeds): 637.4 / 689.8 / 719.1 written, 636.9 / 666.3 / 673.3 relaxed.
- Value of transfers (none - free): written (a) 0.01 +/- 0.03, (b) 8.6 +/- 10.1 [upper bound 22.2 +/- 9.8], (c) 8.6 +/- 10.1 [upper bound 22.2 +/- 9.6]; relaxed 0.00 +/- 0.00 / 0.00 +/- 0.00 / 0.00 +/- 0.03. Round 2: 0.03 / 6.59 / 12.60 written, 0 / 0 / 0.04 relaxed. Round 1 (toy units): 0 / 257 / 254.5.
- Cost of separation vs (a), transfers free: written 52.2 +/- 1.6 (b) / 81.4 +/- 1.6 (c), hub setup 29.19 / 58.38, operations 23.1 / 23.1; relaxed 29.3 +/- 0.2 / 58.5 +/- 0.2. Round 2: +52.4 / +81.7 written, +29.4 / +58.8 relaxed.
- Headline gap vs policy NONE, ILP transfers free: written 21.3 +/- 11.3 % (a), 18.4 +/- 10.6 % (b), 17.8 +/- 10.4 % (c); relaxed 21.4 +/- 11.3 / 21.2 +/- 10.2 / 20.5 +/- 10.0 %; vs REORDER_POINT (written) 37.4 +/- 7.3 / 32.0 +/- 5.6 / 31.1 +/- 5.5 %; ILP h = z = 0 vs NONE (written) 21.3 +/- 11.3 / 17.4 +/- 11.1 / 16.8 +/- 10.8 %. Round 2: 24.2 / 21.1 / 20.5 written, 24.2 / 23.9 / 15.8 relaxed.
- Policy (n = 5): NONE 822.9 +/- 155.6 (a), 856.2 +/- 148.6 (b), 885.4 +/- 148.6 (c); REORDER_POINT 1029.8 +/- 158.8 / 1021.3 +/- 123.4 / 1050.0 +/- 122.5; paired difference REORDER_POINT - NONE +206.9 +/- 75.4 / +165.1 +/- 46.9 / +164.6 +/- 47.2 USD. Round 2 (n = 3): NONE 832 / 864 / 893, REORDER_POINT 1038 / 1043 / 1072.
- Served share (written, transfers free): ILP 0.900 (a), 0.894 (b), 0.894 (c); ILP h = z = 0 0.900 / 0.822 / 0.822; policy NONE 0.856 / 0.850 / 0.850; attainable ceiling 0.972 on seeds 0, 1, 3, 4 and 1.0 on seed 2.
- Transfers: ILP uses 0 shuttles in (a) and in every relaxed run, exactly 1 shuttle with 2 batteries (C_reb 22 USD) in every written (b)/(c) run; policy REORDER_POINT 5-14 shuttles, 9-22 batteries, C_reb 109-302 USD.
- Stock-outs (slots with n_jLt = 0 summed over facilities): ILP written free 18.2 (a), 0 (b), 0 (c); relaxed 38.2 / 36.0 / 30.6; policy NONE 8.2 / 31.2 / 31.2.
- Grid: hub charging peak 1.33 kW in every written (b)/(c) free run, 0 kW in the hubs' no-transfer and relaxed runs; co-located sites at most 3.33 kW; limit 8 kW (6 kW in 18-20 h) never binds; electricity <= 0.82 USD per window.
- Solver: 60 ILP cells, OPTIMAL 50 (round 3: 33, mean 79 s, range 40-124 s; reused round 2: 17, mean 114 s), TIME_LIMIT 10 (all separated / written / transfers free, 600 s, gap 1.79-2.00 %, nodes 63-143), SKIPPED_BUDGET 0; binaries 1,033,046-1,392,552; MIP start accepted 50/60.

## Tables

### T1. ILP total cost (26), USD per 4 h window, by layout x transfer switch x end targets (mean +/- 95 % t-CI, n = 5; per-seed values seeds 0-4 in parentheses; status letters O = OPTIMAL, T = TIME_LIMIT at 600 s)

| layout | targets | transfers free | h = z = 0 | value of transfers (none - free) | status free / none |
|---|---|---|---|---|---|
| (a) co-located 3 sites | written | 638.22 +/- 28.69 [n=5] (615.15, 659.60, 638.98, 662.63, 614.76) | 638.24 +/- 28.67 [n=5] (615.20, 659.60, 638.98, 662.63, 614.78) | 0.01 +/- 0.03 [n=5] (0.05, 0.00, 0.00, 0.00, 0.02) | OOOOO / OOOOO |
| (a) co-located 3 sites | relaxed | 637.88 +/- 28.81 [n=5] (614.51, 659.37, 638.73, 662.31, 614.48) | 637.88 +/- 28.81 [n=5] (614.51, 659.37, 638.73, 662.31, 614.48) | 0.00 +/- 0.00 [n=5] (0.00, 0.00, 0.00, 0.00, 0.00) | OOOOO / OOOOO |
| (b) 3 swap sites + 1 hub | written | 690.47 +/- 28.99 [n=5] (668.46, 710.93, 690.37, 716.55, 666.04) | 699.12 +/- 29.66 [n=5] (681.06, 711.75, 689.81, 734.79, 678.19) | 8.65 +/- 10.12 [n=5] (12.60, 0.82, -0.56, 18.24, 12.15) | TTTTT / OOOOO |
| (b) 3 swap sites + 1 hub | relaxed | 667.14 +/- 28.69 [n=5] (644.08, 688.56, 667.92, 691.50, 643.67) | 667.14 +/- 28.69 [n=5] (644.08, 688.56, 667.92, 691.50, 643.67) | 0.00 +/- 0.00 [n=5] (0.00, 0.00, 0.00, 0.00, 0.00) | OOOOO / OOOOO |
| (c) 3 swap sites + 2 hubs | written | 719.66 +/- 28.99 [n=5] (697.65, 740.12, 719.56, 745.74, 695.23) | 728.30 +/- 29.63 [n=5] (710.25, 740.94, 719.00, 763.91, 707.38) | 8.63 +/- 10.10 [n=5] (12.60, 0.82, -0.56, 18.17, 12.15) | TTTTT / OOOOO |
| (c) 3 swap sites + 2 hubs | relaxed | 696.34 +/- 28.70 [n=5] (673.27, 717.75, 697.11, 720.73, 672.86) | 696.34 +/- 28.68 [n=5] (673.30, 717.75, 697.11, 720.69, 672.86) | 0.00 +/- 0.03 [n=5] (0.04, 0.00, 0.00, -0.04, 0.00) | OOOOO / OOOOO |

### T2. Value of transfers per layout and target setting (ILP cost with h = z = 0 minus ILP cost with transfers free; written separated values are lower bounds because the free runs stopped at TIME_LIMIT, the upper bound uses the free run's best bound)

| layout | targets | value (none - free), mean +/- CI | per seed | upper bound (none - free bound) | shuttles used (free) | batteries moved | C_reb (32) | served share free / none | n_swaps free / none |
|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | 0.01 +/- 0.03 [n=5] | 0.05, 0.00, 0.00, 0.00, 0.02 | 0.02 +/- 0.03 [n=5] | 0.0 | 0.0 | 0.0 | 0.900 / 0.900 | 7.0 / 7.2 |
| (a) co-located 3 sites | relaxed | 0.00 +/- 0.00 [n=5] | 0.00, 0.00, 0.00, 0.00, 0.00 | 0.00 +/- 0.01 [n=5] | 0.0 | 0.0 | 0.0 | 0.900 / 0.900 | 7.4 / 7.0 |
| (b) 3 swap sites + 1 hub | written | 8.65 +/- 10.12 [n=5] | 12.60, 0.82, -0.56, 18.24, 12.15 | 22.18 +/- 9.78 [n=5] | 1.0 | 2.0 | 22.0 | 0.894 / 0.822 | 6.0 / 4.0 |
| (b) 3 swap sites + 1 hub | relaxed | 0.00 +/- 0.00 [n=5] | 0.00, 0.00, 0.00, 0.00, 0.00 | 0.01 +/- 0.03 [n=5] | 0.0 | 0.0 | 0.0 | 0.900 / 0.900 | 6.8 / 7.0 |
| (c) 3 swap sites + 2 hubs | written | 8.63 +/- 10.10 [n=5] | 12.60, 0.82, -0.56, 18.17, 12.15 | 22.22 +/- 9.61 [n=5] | 1.0 | 2.0 | 22.0 | 0.894 / 0.822 | 6.0 / 4.0 |
| (c) 3 swap sites + 2 hubs | relaxed | 0.00 +/- 0.03 [n=5] | 0.04, 0.00, 0.00, -0.04, 0.00 | 0.02 +/- 0.05 [n=5] | 0.0 | 0.0 | 0.0 | 0.900 / 0.900 | 7.0 / 7.4 |

### T3. Cost of separation = ILP total(layout) - ILP total(co-located), same seed, switch and targets (USD per 4 h)

| layout | targets | switch | separation cost, mean +/- CI | per seed | hub setup F_hub | operational part (mean) |
|---|---|---|---|---|---|---|
| (b) 3 swap sites + 1 hub | written | transfers free | 52.25 +/- 1.58 [n=5] | 53.31, 51.33, 51.39, 53.92, 51.28 | 29.19 | 23.06 |
| (b) 3 swap sites + 1 hub | written | h = z = 0 (no transfers) | 60.88 +/- 11.38 [n=5] | 65.86, 52.15, 50.83, 72.16, 63.41 | 29.19 | 31.69 |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 29.27 +/- 0.21 [n=5] | 29.57, 29.19, 29.19, 29.19, 29.19 | 29.19 | 0.08 |
| (b) 3 swap sites + 1 hub | relaxed | h = z = 0 (no transfers) | 29.27 +/- 0.21 [n=5] | 29.57, 29.19, 29.19, 29.19, 29.19 | 29.19 | 0.08 |
| (c) 3 swap sites + 2 hubs | written | transfers free | 81.44 +/- 1.58 [n=5] | 82.50, 80.52, 80.58, 83.11, 80.47 | 58.38 | 23.06 |
| (c) 3 swap sites + 2 hubs | written | h = z = 0 (no transfers) | 90.06 +/- 11.35 [n=5] | 95.05, 81.34, 80.02, 101.28, 92.60 | 58.38 | 31.68 |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 58.46 +/- 0.21 [n=5] | 58.76, 58.38, 58.38, 58.42, 58.38 | 58.38 | 0.08 |
| (c) 3 swap sites + 2 hubs | relaxed | h = z = 0 (no transfers) | 58.46 +/- 0.23 [n=5] | 58.80, 58.38, 58.38, 58.38, 58.38 | 58.38 | 0.08 |

### T4. ILP operational metrics (means over seeds 0-4; CI where n = 5 and the quantity varies)

| layout | targets | switch | n | served share | n_unserved | C_reb | shuttles | batteries moved | n_swaps | stock-out slots | grid peak kW | end full (>= 4.5 written) | kWh bought | C_elec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | transfers free | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.0 | 18.2 +/- 14.9 [n=5] | 3.33 (max) / 1.87 (mean) | 5.0 | 1.16 | 0.37 |
| (a) co-located 3 sites | written | h = z = 0 (no transfers) | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.2 | 20.8 +/- 18.6 [n=5] | 2.67 (max) / 1.73 (mean) | 5.0 | 1.20 | 0.38 |
| (a) co-located 3 sites | relaxed | transfers free | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.4 | 38.2 +/- 13.8 [n=5] | 0.67 (max) / 0.13 (mean) | 1.8 | 0.08 | 0.02 |
| (a) co-located 3 sites | relaxed | h = z = 0 (no transfers) | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.0 | 39.4 +/- 21.0 [n=5] | 0.67 (max) / 0.13 (mean) | 2.2 | 0.08 | 0.02 |
| (b) 3 swap sites + 1 hub | written | transfers free | 5 | 0.894 +/- 0.045 [n=5] | 3.8 | 22.0 | 1.0 | 2.0 | 6.0 | 0.0 +/- 0.0 [n=5] | 1.33 (max) / 1.33 (mean) | 5.0 | 0.82 | 0.26 |
| (b) 3 swap sites + 1 hub | written | h = z = 0 (no transfers) | 5 | 0.822 +/- 0.039 [n=5] | 6.4 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 +/- 0.0 [n=5] | 0.00 (max) / 0.00 (mean) | 5.0 | 0.00 | 0.00 |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 6.8 | 36.0 +/- 20.5 [n=5] | 0.00 (max) / 0.00 (mean) | 2.2 | 0.00 | 0.00 |
| (b) 3 swap sites + 1 hub | relaxed | h = z = 0 (no transfers) | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.0 | 33.6 +/- 23.2 [n=5] | 0.00 (max) / 0.00 (mean) | 2.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | written | transfers free | 5 | 0.894 +/- 0.045 [n=5] | 3.8 | 22.0 | 1.0 | 2.0 | 6.0 | 0.0 +/- 0.0 [n=5] | 1.33 (max) / 1.33 (mean) | 5.0 | 0.82 | 0.26 |
| (c) 3 swap sites + 2 hubs | written | h = z = 0 (no transfers) | 5 | 0.822 +/- 0.039 [n=5] | 6.4 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 +/- 0.0 [n=5] | 0.00 (max) / 0.00 (mean) | 5.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.0 | 30.6 +/- 24.2 [n=5] | 0.00 (max) / 0.00 (mean) | 2.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | relaxed | h = z = 0 (no transfers) | 5 | 0.900 +/- 0.058 [n=5] | 3.6 | 0.0 | 0.0 | 0.0 | 7.4 | 43.2 +/- 15.2 [n=5] | 0.00 (max) / 0.00 (mean) | 1.6 | 0.00 | 0.00 |

### T5. Policy (R2.3 rules): NONE vs REORDER_POINT, mean over 5 seeds with 95 % t-CI (USD per 4 h; written and relaxed rows are the same schedule, so one table serves both target settings)

| layout | rule | total | unserved (30) | response (31) | lateness (31) | C_reb (32) | C_elec (28) | served share | shuttles | batteries moved | stock-out slots | grid peak kW (max) | end full | (17)/(18) reported (written run) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | NONE | 822.90 +/- 155.61 [n=5] | 156.00 +/- 112.98 [n=5] | 518.40 +/- 53.93 [n=5] | 95.40 +/- 67.38 [n=5] | 0.00 +/- 0.00 [n=5] | 0.83 +/- 0.10 [n=5] | 0.856 +/- 0.105 [n=5] | 0.0 | 0.0 | 8.2 | 2.67 | 5.4 | s0:{}; s1:{"(18)": 1}; s2:{}; s3:{}; s4:{} |
| (a) co-located 3 sites | REORDER_POINT | 1029.75 +/- 158.78 [n=5] | 150.00 +/- 105.36 [n=5] | 519.30 +/- 51.54 [n=5] | 92.40 +/- 61.12 [n=5] | 215.00 +/- 63.28 [n=5] | 0.91 +/- 0.13 [n=5] | 0.861 +/- 0.098 [n=5] | 10.0 | 15.0 | 5.6 | 2.67 | 5.6 | s0:{}; s1:{"(18)": 1}; s2:{}; s3:{}; s4:{} |
| (b) 3 swap sites + 1 hub | NONE | 856.20 +/- 148.57 [n=5] | 162.00 +/- 107.32 [n=5] | 516.00 +/- 57.06 [n=5] | 96.60 +/- 66.66 [n=5] | 0.00 +/- 0.00 [n=5] | 0.00 +/- 0.00 [n=5] | 0.850 +/- 0.099 [n=5] | 0.0 | 0.0 | 31.2 | 0.00 | 1.8 | s0:{"(17)": 2, "(18)": 1}; s1:{"(17)": 2, "(18)": 1}; s2:{"(17)": 1, "(18)": 1}; s3:{"(17)": 2, "(18)": 1}; s4:{"(17)": 1, "(18)": 1} |
| (b) 3 swap sites + 1 hub | REORDER_POINT | 1021.29 +/- 123.42 [n=5] | 156.00 +/- 112.98 [n=5] | 519.00 +/- 55.20 [n=5] | 96.60 +/- 66.66 [n=5] | 167.00 +/- 49.07 [n=5] | 1.10 +/- 0.05 [n=5] | 0.856 +/- 0.105 [n=5] | 7.8 | 11.0 | 18.8 | 3.33 | 7.8 | s0:{}; s1:{}; s2:{}; s3:{"(17)": 1}; s4:{} |
| (c) 3 swap sites + 2 hubs | NONE | 885.39 +/- 148.57 [n=5] | 162.00 +/- 107.32 [n=5] | 516.00 +/- 57.06 [n=5] | 96.60 +/- 66.66 [n=5] | 0.00 +/- 0.00 [n=5] | 0.00 +/- 0.00 [n=5] | 0.850 +/- 0.099 [n=5] | 0.0 | 0.0 | 31.2 | 0.00 | 1.8 | s0:{"(17)": 2, "(18)": 1}; s1:{"(17)": 2, "(18)": 1}; s2:{"(17)": 1, "(18)": 1}; s3:{"(17)": 2, "(18)": 1}; s4:{"(17)": 1, "(18)": 1} |
| (c) 3 swap sites + 2 hubs | REORDER_POINT | 1050.02 +/- 122.55 [n=5] | 156.00 +/- 112.98 [n=5] | 519.00 +/- 55.20 [n=5] | 96.60 +/- 66.66 [n=5] | 166.60 +/- 49.33 [n=5] | 1.05 +/- 0.05 [n=5] | 0.856 +/- 0.105 [n=5] | 7.8 | 10.6 | 18.8 | 2.00 | 6.8 | s0:{}; s1:{}; s2:{}; s3:{"(17)": 1}; s4:{} |

Paired difference REORDER_POINT - NONE (same instance):

| layout | REORDER_POINT - NONE, mean +/- CI (USD) | per seed | unserved change (orders, per seed) |
|---|---|---|---|
| (a) co-located 3 sites | 206.85 +/- 75.41 [n=5] | 171.95, 143.35, 302.25, 222.48, 194.23 | [0, 0, 0, -1, 0] |
| (b) 3 swap sites + 1 hub | 165.09 +/- 46.92 [n=5] | 173.12, 152.05, 213.05, 110.03, 177.19 | [0, 0, 0, 0, -1] |
| (c) 3 swap sites + 2 hubs | 164.63 +/- 47.21 [n=5] | 173.12, 149.92, 213.05, 109.92, 177.14 | [0, 0, 0, 0, -1] |

### T6. Headline gap 100 (policy - ILP) / policy, by cell (mean +/- 95 % t-CI, n = 5)

| layout | targets | switch | n | vs NONE (default) | per seed | vs REORDER_POINT | vs best policy |
|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | transfers free | 5 | 21.3 +/- 11.3 [n=5] % | 16.1, 32.2, 19.1, 29.0, 10.3 | 37.4 +/- 7.3 [n=5] % | 21.3 +/- 11.3 [n=5] % |
| (a) co-located 3 sites | written | h = z = 0 (no transfers) | 5 | 21.3 +/- 11.3 [n=5] % | 16.1, 32.2, 19.1, 29.0, 10.3 | 37.4 +/- 7.3 [n=5] % | 21.3 +/- 11.3 [n=5] % |
| (a) co-located 3 sites | relaxed | transfers free | 5 | 21.4 +/- 11.3 [n=5] % | 16.2, 32.3, 19.2, 29.0, 10.3 | 37.5 +/- 7.3 [n=5] % | 21.4 +/- 11.3 [n=5] % |
| (a) co-located 3 sites | relaxed | h = z = 0 (no transfers) | 5 | 21.4 +/- 11.3 [n=5] % | 16.2, 32.3, 19.2, 29.0, 10.3 | 37.5 +/- 7.3 [n=5] % | 21.4 +/- 11.3 [n=5] % |
| (b) 3 swap sites + 1 hub | written | transfers free | 5 | 18.4 +/- 10.6 [n=5] % | 13.3, 29.0, 15.7, 25.5, 8.6 | 32.0 +/- 5.6 [n=5] % | 18.4 +/- 10.6 [n=5] % |
| (b) 3 swap sites + 1 hub | written | h = z = 0 (no transfers) | 5 | 17.4 +/- 11.1 [n=5] % | 11.6, 28.9, 15.7, 23.6, 6.9 | 31.2 +/- 6.3 [n=5] % | 17.4 +/- 11.1 [n=5] % |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 5 | 21.2 +/- 10.2 [n=5] % | 16.4, 31.3, 18.4, 28.1, 11.6 | 34.3 +/- 5.3 [n=5] % | 21.2 +/- 10.2 [n=5] % |
| (b) 3 swap sites + 1 hub | relaxed | h = z = 0 (no transfers) | 5 | 21.2 +/- 10.2 [n=5] % | 16.4, 31.3, 18.4, 28.1, 11.6 | 34.3 +/- 5.3 [n=5] % | 21.2 +/- 10.2 [n=5] % |
| (c) 3 swap sites + 2 hubs | written | transfers free | 5 | 17.8 +/- 10.4 [n=5] % | 12.8, 28.2, 15.1, 24.7, 8.2 | 31.1 +/- 5.5 [n=5] % | 17.8 +/- 10.4 [n=5] % |
| (c) 3 swap sites + 2 hubs | written | h = z = 0 (no transfers) | 5 | 16.8 +/- 10.8 [n=5] % | 11.2, 28.1, 15.2, 22.9, 6.6 | 30.3 +/- 6.2 [n=5] % | 16.8 +/- 10.8 [n=5] % |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 5 | 20.5 +/- 10.0 [n=5] % | 15.8, 30.4, 17.8, 27.2, 11.2 | 33.4 +/- 5.2 [n=5] % | 20.5 +/- 10.0 [n=5] % |
| (c) 3 swap sites + 2 hubs | relaxed | h = z = 0 (no transfers) | 5 | 20.5 +/- 10.0 [n=5] % | 15.8, 30.4, 17.8, 27.2, 11.2 | 33.4 +/- 5.2 [n=5] % | 20.5 +/- 10.0 [n=5] % |

### T7. Solver statistics

- Runs: 60 ILP cells (3 layouts x 2 targets x 2 switches x 5 seeds), all attempted; status OPTIMAL 50, TIME_LIMIT 10, SKIPPED_BUDGET 0, INFEASIBLE 0. Round 2: 17 OPTIMAL, 4 TIME_LIMIT, 15 SKIPPED_BUDGET.
- Binaries per layout (min / max / mean): (a) co-located 1,033,046 / 1,155,029 / 1,092,423; (b) 1 hub 1,033,047 / 1,270,583 / 1,182,762; (c) 2 hubs 1,258,383 / 1,392,552 / 1,322,469; rows 58,794-70,905.
- OPTIMAL runs: round 3 (33) mean 79 s, median 86 s, range 40-124 s, node count 1 on 32/33 (one run, (c) written h = z = 0 seed 1, needed 9 nodes); reused round-2 runs (17) mean 114 s, range 72-187 s, all at the root. Reported gap <= 1e-4 on every OPTIMAL run.
- TIME_LIMIT runs (10): all separated / written / transfers-free cells, 600 s each, gap 1.79-2.00 %, nodes 63-143; incumbents all use exactly 1 shuttle with 2 batteries.
- MIP-start acceptance (fix-and-solve certificate at build time): baseline:NONE accepted=True: 19; baseline:NONE(unverified) accepted=False: 10; baseline_reorder:REORDER_POINT accepted=True: 27; baseline_round1:NONE accepted=True: 1; baseline_round1:REORDER_POINT accepted=True: 3.
- Checks: evaluate.check ok 60/60, identity (24) ok 60/60, Gurobi objective == evaluate.cost 60/60, ILP total <= best policy total 60/60; policy rows: check modulo report-only families ok 60/60, identity (24) ok 60/60.
- Wall time: 150.1 min for 43 solves + 46 policy runs (plan: 15 fill, 24 extend, 4 resolve600; expected 119 min, worst case 265 min).

### T8. The 600 s re-solves and the other separated / written / transfers-free cells (did the gaps close?)

| layout | seed | round-2 incumbent (300 s) | round-2 gap | round-3 incumbent (600 s) | round-3 bound | round-3 gap | improvement (USD) | nodes | h = z = 0 optimum | value of transfers [lower, upper] |
|---|---|---|---|---|---|---|---|---|---|---|
| (b) 1 hub | 0 | 668.46 | 1.99 % | 668.46 | 655.23 | 1.98 % | 0.000 | 131 | 681.06 | [12.60, 25.83] |
| (b) 1 hub | 1 | 711.17 | 2.01 % | 710.93 | 696.89 | 1.97 % | 0.233 | 143 | 711.75 | [0.82, 14.86] |
| (b) 1 hub | 2 | - (not solved in round 2) | - | 690.37 | 676.67 | 1.98 % | - | 126 | 689.81 | [-0.56, 13.14] |
| (b) 1 hub | 3 | - (not solved in round 2) | - | 716.55 | 703.20 | 1.86 % | - | 93 | 734.79 | [18.24, 31.59] |
| (b) 1 hub | 4 | - (not solved in round 2) | - | 666.04 | 652.72 | 2.00 % | - | 136 | 678.19 | [12.15, 25.47] |
| (c) 2 hubs | 0 | 697.65 | 1.90 % | 697.65 | 684.42 | 1.90 % | 0.000 | 96 | 710.25 | [12.60, 25.83] |
| (c) 2 hubs | 1 | 740.45 | 1.94 % | 740.12 | 726.34 | 1.86 % | 0.324 | 88 | 740.94 | [0.82, 14.60] |
| (c) 2 hubs | 2 | - (not solved in round 2) | - | 719.56 | 705.27 | 1.99 % | - | 117 | 719.00 | [-0.56, 13.73] |
| (c) 2 hubs | 3 | - (not solved in round 2) | - | 745.74 | 732.39 | 1.79 % | - | 63 | 763.91 | [18.17, 31.52] |
| (c) 2 hubs | 4 | - (not solved in round 2) | - | 695.23 | 681.98 | 1.91 % | - | 69 | 707.38 | [12.15, 25.40] |

No: every cell stays at a 1.8-2.0 % gap; the incumbents of the 4 re-solved round-2 cells improved by 0.00 (seed 0, both layouts), 0.23 (b seed 1) and 0.32 USD (c seed 1), and the 6 new seeds show the same gap after 600 s as the round-2 cells after 300 s. The no-transfers optimum is feasible for the free model, so the true free optimum lies in [bound, min(incumbent, h = z = 0 optimum)] and the value of transfers in [max(0, lower), upper]; on seed 2 the free incumbent is 0.56 USD above the no-transfers optimum (lower bound -0.56 reads as 0).

### T9. Per-cell table (every ILP run; policy totals and gaps from the merged policy table)

| layout | targets | seed | switch | source | status | ILP total | bound | gap | C_setup | C_travel | C_elec | unserved | response | lateness | C_reb | served | swaps | shuttles | moved | stock-out slots | peak kW | end full | binaries | rows | nodes | solve s | TL s | MIP start (accepted) | policy NONE | policy REORDER | gap vs NONE % | gap vs REORDER % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located | written | 0 | free | round2 | OPTIMAL | 615.15 | 615.15 | 0.0000 | 39.57 | 12.31 | 0.764 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 17 | 3.33 | 5 | 1,155,029 | 63,316 | 1 | 173 | 300 | baseline_reorder:REORDER_POINT (True) | 733.10 | 905.04 | 16.1 | 32.0 |
| (a) co-located | written | 0 | none | round2 | OPTIMAL | 615.20 | 615.14 | 0.0001 | 39.57 | 12.31 | 0.818 | 30 | 523.5 | 9.0 | 0 | 0.972 | 11 | 0 | 0 | 21 | 2.67 | 5 | 1,155,029 | 63,316 | 1 | 165 | 300 | baseline:NONE (True) | 733.10 | 905.04 | 16.1 | 32.0 |
| (a) co-located | relaxed | 0 | free | round2 | OPTIMAL | 614.51 | 614.51 | 0.0000 | 39.57 | 12.31 | 0.124 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 54 | 0.67 | 0 | 1,155,029 | 63,316 | 1 | 119 | 300 | baseline_reorder:REORDER_POINT (True) | 733.10 | 905.04 | 16.2 | 32.1 |
| (a) co-located | relaxed | 0 | none | round2 | OPTIMAL | 614.51 | 614.51 | 0.0000 | 39.57 | 12.31 | 0.124 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 61 | 0.67 | 0 | 1,155,029 | 63,316 | 1 | 112 | 300 | baseline:NONE (True) | 733.10 | 905.04 | 16.2 | 32.1 |
| (b) 1 hub | written | 0 | free | round3 | TIME_LIMIT | 668.46 | 655.23 | 0.0198 | 68.76 | 11.99 | 0.213 | 60 | 499.5 | 6.0 | 22 | 0.944 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,270,583 | 66,149 | 131 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 770.83 | 943.95 | 13.3 | 29.2 |
| (b) 1 hub | written | 0 | none | round2 | OPTIMAL | 681.06 | 681.06 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 448.5 | 3.0 | 0 | 0.861 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,270,583 | 66,149 | 1 | 122 | 300 | baseline:NONE(unverified) (False) | 770.83 | 943.95 | 11.6 | 27.9 |
| (b) 1 hub | relaxed | 0 | free | round2 | OPTIMAL | 644.08 | 644.02 | 0.0001 | 68.76 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 59 | 0.00 | 0 | 1,270,583 | 66,149 | 1 | 187 | 300 | baseline_reorder:REORDER_POINT (True) | 770.83 | 943.95 | 16.4 | 31.8 |
| (b) 1 hub | relaxed | 0 | none | round2 | OPTIMAL | 644.08 | 644.02 | 0.0001 | 68.76 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 60 | 0.00 | 0 | 1,270,583 | 66,149 | 1 | 121 | 300 | baseline:NONE (True) | 770.83 | 943.95 | 16.4 | 31.8 |
| (c) 2 hubs | written | 0 | free | round3 | TIME_LIMIT | 697.65 | 684.42 | 0.0190 | 97.95 | 11.99 | 0.213 | 60 | 499.5 | 6.0 | 22 | 0.944 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,392,552 | 70,905 | 96 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 800.02 | 973.14 | 12.8 | 28.3 |
| (c) 2 hubs | written | 0 | none | round2 | OPTIMAL | 710.25 | 710.21 | 0.0001 | 97.95 | 10.80 | 0.000 | 150 | 448.5 | 3.0 | 0 | 0.861 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,392,552 | 70,905 | 1 | 86 | 300 | baseline:NONE(unverified) (False) | 800.02 | 973.14 | 11.2 | 27.0 |
| (c) 2 hubs | relaxed | 0 | free | round2 | OPTIMAL | 673.27 | 673.22 | 0.0001 | 97.95 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 58 | 0.00 | 0 | 1,392,552 | 70,905 | 1 | 118 | 300 | baseline_reorder:REORDER_POINT (True) | 800.02 | 973.14 | 15.8 | 30.8 |
| (c) 2 hubs | relaxed | 0 | none | round2 | OPTIMAL | 673.30 | 673.25 | 0.0001 | 97.95 | 12.85 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 56 | 0.00 | 0 | 1,392,552 | 70,905 | 1 | 89 | 300 | baseline:NONE (True) | 800.02 | 973.14 | 15.8 | 30.8 |
| (a) co-located | written | 1 | free | round2 | OPTIMAL | 659.60 | 659.60 | 0.0000 | 39.57 | 10.80 | 0.231 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 36 | 1.33 | 5 | 1,106,236 | 62,446 | 1 | 94 | 300 | baseline_round1:REORDER_POINT (True) | 973.24 | 1116.60 | 32.2 | 40.9 |
| (a) co-located | written | 1 | none | round2 | OPTIMAL | 659.60 | 659.60 | 0.0000 | 39.57 | 10.80 | 0.231 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 42 | 1.33 | 5 | 1,106,236 | 62,446 | 1 | 86 | 300 | baseline_round1:NONE (True) | 973.24 | 1116.60 | 32.2 | 40.9 |
| (a) co-located | relaxed | 1 | free | round2 | OPTIMAL | 659.37 | 659.37 | 0.0000 | 39.57 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 7 | 0 | 0 | 42 | 0.00 | 2 | 1,106,236 | 62,446 | 1 | 88 | 300 | baseline_reorder:REORDER_POINT (True) | 973.24 | 1116.60 | 32.3 | 40.9 |
| (a) co-located | relaxed | 1 | none | round2 | OPTIMAL | 659.37 | 659.37 | 0.0000 | 39.57 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 35 | 0.00 | 3 | 1,106,236 | 62,446 | 1 | 95 | 300 | baseline:NONE (True) | 973.24 | 1116.60 | 32.3 | 40.9 |
| (b) 1 hub | written | 1 | free | round3 | TIME_LIMIT | 710.93 | 696.89 | 0.0197 | 68.76 | 10.87 | 0.302 | 150 | 456.0 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,219,763 | 65,322 | 143 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 1001.74 | 1153.79 | 29.0 | 38.4 |
| (b) 1 hub | written | 1 | none | round2 | OPTIMAL | 711.75 | 711.75 | 0.0000 | 68.76 | 9.99 | 0.000 | 210 | 423.0 | 0.0 | 0 | 0.806 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,219,763 | 65,322 | 1 | 115 | 300 | baseline:NONE(unverified) (False) | 1001.74 | 1153.79 | 28.9 | 38.3 |
| (b) 1 hub | relaxed | 1 | free | round2 | OPTIMAL | 688.56 | 688.56 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,219,763 | 65,322 | 1 | 102 | 300 | baseline_reorder:REORDER_POINT (True) | 1001.74 | 1153.79 | 31.3 | 40.3 |
| (b) 1 hub | relaxed | 1 | none | round2 | OPTIMAL | 688.56 | 688.56 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 7 | 0 | 0 | 46 | 0.00 | 2 | 1,219,763 | 65,322 | 1 | 72 | 300 | baseline:NONE (True) | 1001.74 | 1153.79 | 31.3 | 40.3 |
| (c) 2 hubs | written | 1 | free | round3 | TIME_LIMIT | 740.12 | 726.34 | 0.0186 | 97.95 | 10.87 | 0.302 | 150 | 456.0 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,337,408 | 70,012 | 88 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 1030.93 | 1180.86 | 28.2 | 37.3 |
| (c) 2 hubs | written | 1 | none | round3 | OPTIMAL | 740.94 | 740.94 | 0.0000 | 97.95 | 9.99 | 0.000 | 210 | 423.0 | 0.0 | 0 | 0.806 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,337,408 | 70,012 | 9 | 98 | 300 | baseline:NONE(unverified) (False) | 1030.93 | 1180.86 | 28.1 | 37.3 |
| (c) 2 hubs | relaxed | 1 | free | round3 | OPTIMAL | 717.75 | 717.75 | 0.0000 | 97.95 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,337,408 | 70,012 | 1 | 96 | 300 | baseline_reorder:REORDER_POINT (True) | 1030.93 | 1180.86 | 30.4 | 39.2 |
| (c) 2 hubs | relaxed | 1 | none | round3 | OPTIMAL | 717.75 | 717.75 | 0.0000 | 97.95 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 47 | 0.00 | 3 | 1,337,408 | 70,012 | 1 | 76 | 300 | baseline:NONE (True) | 1030.93 | 1180.86 | 30.4 | 39.2 |
| (a) co-located | written | 2 | free | round3 | OPTIMAL | 638.98 | 638.98 | 0.0000 | 39.57 | 11.16 | 0.249 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 23 | 1.33 | 5 | 1,044,991 | 60,216 | 1 | 93 | 300 | baseline_reorder:REORDER_POINT (True) | 790.12 | 1092.37 | 19.1 | 41.5 |
| (a) co-located | written | 2 | none | round3 | OPTIMAL | 638.98 | 638.98 | 0.0000 | 39.57 | 11.16 | 0.249 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 23 | 1.33 | 5 | 1,044,991 | 60,216 | 1 | 92 | 300 | baseline:NONE (True) | 790.12 | 1092.37 | 19.1 | 41.5 |
| (a) co-located | relaxed | 2 | free | round3 | OPTIMAL | 638.73 | 638.73 | 0.0000 | 39.57 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 40 | 0.00 | 3 | 1,044,991 | 60,216 | 1 | 86 | 300 | baseline_reorder:REORDER_POINT (True) | 790.12 | 1092.37 | 19.2 | 41.5 |
| (a) co-located | relaxed | 2 | none | round3 | OPTIMAL | 638.73 | 638.73 | 0.0000 | 39.57 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 39 | 0.00 | 3 | 1,044,991 | 60,216 | 1 | 90 | 300 | baseline:NONE (True) | 790.12 | 1092.37 | 19.2 | 41.5 |
| (b) 1 hub | written | 2 | free | round3 | TIME_LIMIT | 690.37 | 676.67 | 0.0198 | 68.76 | 11.34 | 0.267 | 120 | 465.0 | 3.0 | 22 | 0.889 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,154,084 | 63,039 | 126 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 818.50 | 1031.55 | 15.7 | 33.1 |
| (b) 1 hub | written | 2 | none | round3 | OPTIMAL | 689.81 | 689.81 | 0.0000 | 68.76 | 10.55 | 0.000 | 180 | 430.5 | 0.0 | 0 | 0.833 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,154,084 | 63,039 | 1 | 53 | 300 | baseline:NONE(unverified) (False) | 818.50 | 1031.55 | 15.7 | 33.1 |
| (b) 1 hub | relaxed | 2 | free | round3 | OPTIMAL | 667.92 | 667.92 | 0.0000 | 68.76 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,154,084 | 63,039 | 1 | 89 | 300 | baseline_reorder:REORDER_POINT (True) | 818.50 | 1031.55 | 18.4 | 35.3 |
| (b) 1 hub | relaxed | 2 | none | round3 | OPTIMAL | 667.92 | 667.92 | 0.0000 | 68.76 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,154,084 | 63,039 | 1 | 48 | 300 | baseline:NONE (True) | 818.50 | 1031.55 | 18.4 | 35.3 |
| (c) 2 hubs | written | 2 | free | round3 | TIME_LIMIT | 719.56 | 705.27 | 0.0199 | 97.95 | 11.34 | 0.267 | 120 | 465.0 | 3.0 | 22 | 0.889 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,268,793 | 67,766 | 117 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 847.69 | 1060.74 | 15.1 | 32.2 |
| (c) 2 hubs | written | 2 | none | round3 | OPTIMAL | 719.00 | 719.00 | 0.0000 | 97.95 | 10.55 | 0.000 | 180 | 430.5 | 0.0 | 0 | 0.833 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,268,793 | 67,766 | 1 | 48 | 300 | baseline:NONE(unverified) (False) | 847.69 | 1060.74 | 15.2 | 32.2 |
| (c) 2 hubs | relaxed | 2 | free | round3 | OPTIMAL | 697.11 | 697.11 | 0.0000 | 97.95 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 40 | 0.00 | 3 | 1,268,793 | 67,766 | 1 | 103 | 300 | baseline_reorder:REORDER_POINT (True) | 847.69 | 1060.74 | 17.8 | 34.3 |
| (c) 2 hubs | relaxed | 2 | none | round3 | OPTIMAL | 697.11 | 697.11 | 0.0000 | 97.95 | 11.16 | 0.000 | 120 | 465.0 | 3.0 | 0 | 0.889 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,268,793 | 67,766 | 1 | 46 | 300 | baseline:NONE (True) | 847.69 | 1060.74 | 17.8 | 34.3 |
| (a) co-located | written | 3 | free | round3 | OPTIMAL | 662.63 | 662.63 | 0.0000 | 39.57 | 12.24 | 0.320 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 6 | 2.00 | 5 | 1,122,816 | 63,061 | 1 | 85 | 300 | baseline_reorder:REORDER_POINT (True) | 932.91 | 1155.39 | 29.0 | 42.6 |
| (a) co-located | written | 3 | none | round3 | OPTIMAL | 662.63 | 662.63 | 0.0000 | 39.57 | 12.24 | 0.320 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 18 | 1.33 | 5 | 1,122,816 | 63,061 | 1 | 78 | 300 | baseline:NONE (True) | 932.91 | 1155.39 | 29.0 | 42.6 |
| (a) co-located | relaxed | 3 | free | round3 | OPTIMAL | 662.31 | 662.29 | 0.0000 | 39.57 | 12.24 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 28 | 0.00 | 2 | 1,122,816 | 63,061 | 1 | 100 | 300 | baseline_reorder:REORDER_POINT (True) | 932.91 | 1155.39 | 29.0 | 42.7 |
| (a) co-located | relaxed | 3 | none | round3 | OPTIMAL | 662.31 | 662.29 | 0.0000 | 39.57 | 12.24 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 15 | 0.00 | 2 | 1,122,816 | 63,061 | 1 | 100 | 300 | baseline:NONE (True) | 932.91 | 1155.39 | 29.0 | 42.7 |
| (b) 1 hub | written | 3 | free | round3 | TIME_LIMIT | 716.55 | 703.20 | 0.0186 | 68.76 | 12.02 | 0.267 | 150 | 460.5 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,236,334 | 65,912 | 93 | 600 | 600 | baseline_round1:REORDER_POINT (True) | 961.42 | 1071.45 | 25.5 | 33.1 |
| (b) 1 hub | written | 3 | none | round3 | OPTIMAL | 734.79 | 734.72 | 0.0001 | 68.76 | 10.53 | 0.000 | 240 | 415.5 | 0.0 | 0 | 0.778 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,236,334 | 65,912 | 1 | 84 | 300 | baseline:NONE(unverified) (False) | 961.42 | 1071.45 | 23.6 | 31.4 |
| (b) 1 hub | relaxed | 3 | free | round3 | OPTIMAL | 691.50 | 691.48 | 0.0000 | 68.76 | 12.24 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 27 | 0.00 | 2 | 1,236,334 | 65,912 | 1 | 97 | 300 | baseline_reorder:REORDER_POINT (True) | 961.42 | 1071.45 | 28.1 | 35.5 |
| (b) 1 hub | relaxed | 3 | none | round3 | OPTIMAL | 691.50 | 691.48 | 0.0000 | 68.76 | 12.24 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 15 | 0.00 | 2 | 1,236,334 | 65,912 | 1 | 76 | 300 | baseline:NONE (True) | 961.42 | 1071.45 | 28.1 | 35.5 |
| (c) 2 hubs | written | 3 | free | round3 | TIME_LIMIT | 745.74 | 732.39 | 0.0179 | 97.95 | 12.02 | 0.267 | 150 | 460.5 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,355,213 | 70,692 | 63 | 600 | 600 | baseline_round1:REORDER_POINT (True) | 990.61 | 1100.54 | 24.7 | 32.2 |
| (c) 2 hubs | written | 3 | none | round3 | OPTIMAL | 763.91 | 763.91 | 0.0000 | 97.95 | 10.46 | 0.000 | 240 | 415.5 | 0.0 | 0 | 0.778 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,355,213 | 70,692 | 1 | 90 | 300 | baseline:NONE(unverified) (False) | 990.61 | 1100.54 | 22.9 | 30.6 |
| (c) 2 hubs | relaxed | 3 | free | round3 | OPTIMAL | 720.73 | 720.67 | 0.0001 | 97.95 | 12.28 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 7 | 0 | 0 | 6 | 0.00 | 2 | 1,355,213 | 70,692 | 1 | 124 | 300 | baseline_reorder:REORDER_POINT (True) | 990.61 | 1100.54 | 27.2 | 34.5 |
| (c) 2 hubs | relaxed | 3 | none | round3 | OPTIMAL | 720.69 | 720.67 | 0.0000 | 97.95 | 12.24 | 0.000 | 150 | 460.5 | 0.0 | 0 | 0.861 | 9 | 0 | 0 | 47 | 0.00 | 0 | 1,355,213 | 70,692 | 1 | 80 | 300 | baseline:NONE (True) | 990.61 | 1100.54 | 27.2 | 34.5 |
| (a) co-located | written | 4 | free | round3 | OPTIMAL | 614.76 | 614.75 | 0.0000 | 39.57 | 10.91 | 0.284 | 90 | 474.0 | 0.0 | 0 | 0.917 | 6 | 0 | 0 | 9 | 1.33 | 5 | 1,033,046 | 59,153 | 1 | 102 | 300 | baseline_reorder:REORDER_POINT (True) | 685.14 | 879.37 | 10.3 | 30.1 |
| (a) co-located | written | 4 | none | round3 | OPTIMAL | 614.78 | 614.75 | 0.0000 | 39.57 | 10.91 | 0.302 | 90 | 474.0 | 0.0 | 0 | 0.917 | 6 | 0 | 0 | 0 | 2.00 | 5 | 1,033,046 | 59,153 | 1 | 86 | 300 | baseline:NONE (True) | 685.14 | 879.37 | 10.3 | 30.1 |
| (a) co-located | relaxed | 4 | free | round3 | OPTIMAL | 614.48 | 614.48 | 0.0000 | 39.57 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 7 | 0 | 0 | 27 | 0.00 | 2 | 1,033,046 | 59,153 | 1 | 75 | 300 | baseline_reorder:REORDER_POINT (True) | 685.14 | 879.37 | 10.3 | 30.1 |
| (a) co-located | relaxed | 4 | none | round3 | OPTIMAL | 614.48 | 614.48 | 0.0000 | 39.57 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 6 | 0 | 0 | 47 | 0.00 | 3 | 1,033,046 | 59,153 | 1 | 86 | 300 | baseline:NONE (True) | 685.14 | 879.37 | 10.3 | 30.1 |
| (b) 1 hub | written | 4 | free | round3 | TIME_LIMIT | 666.04 | 652.72 | 0.0200 | 68.76 | 11.02 | 0.267 | 90 | 474.0 | 0.0 | 22 | 0.917 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,033,047 | 58,794 | 136 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 728.50 | 905.69 | 8.6 | 26.5 |
| (b) 1 hub | written | 4 | none | round3 | OPTIMAL | 678.19 | 678.19 | 0.0000 | 68.76 | 9.43 | 0.000 | 180 | 420.0 | 0.0 | 0 | 0.833 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,033,047 | 58,794 | 1 | 40 | 300 | baseline:NONE(unverified) (False) | 728.50 | 905.69 | 6.9 | 25.1 |
| (b) 1 hub | relaxed | 4 | free | round3 | OPTIMAL | 643.67 | 643.67 | 0.0000 | 68.76 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 6 | 0 | 0 | 48 | 0.00 | 3 | 1,033,047 | 58,794 | 1 | 71 | 300 | baseline_reorder:REORDER_POINT (True) | 728.50 | 905.69 | 11.6 | 28.9 |
| (b) 1 hub | relaxed | 4 | none | round3 | OPTIMAL | 643.67 | 643.67 | 0.0000 | 68.76 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 6 | 0 | 0 | 24 | 0.00 | 3 | 1,033,047 | 58,794 | 1 | 41 | 300 | baseline:NONE (True) | 728.50 | 905.69 | 11.6 | 28.9 |
| (c) 2 hubs | written | 4 | free | round3 | TIME_LIMIT | 695.23 | 681.98 | 0.0191 | 97.95 | 11.02 | 0.267 | 90 | 474.0 | 0.0 | 22 | 0.917 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,258,383 | 66,841 | 69 | 600 | 600 | baseline_reorder:REORDER_POINT (True) | 757.69 | 934.82 | 8.2 | 25.6 |
| (c) 2 hubs | written | 4 | none | round3 | OPTIMAL | 707.38 | 707.38 | 0.0000 | 97.95 | 9.43 | 0.000 | 180 | 420.0 | 0.0 | 0 | 0.833 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,258,383 | 66,841 | 1 | 51 | 300 | baseline:NONE(unverified) (False) | 757.69 | 934.82 | 6.6 | 24.3 |
| (c) 2 hubs | relaxed | 4 | free | round3 | OPTIMAL | 672.86 | 672.86 | 0.0000 | 97.95 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 7 | 0 | 0 | 26 | 0.00 | 2 | 1,258,383 | 66,841 | 1 | 88 | 300 | baseline_reorder:REORDER_POINT (True) | 757.69 | 934.82 | 11.2 | 28.0 |
| (c) 2 hubs | relaxed | 4 | none | round3 | OPTIMAL | 672.86 | 672.86 | 0.0000 | 97.95 | 10.91 | 0.000 | 90 | 474.0 | 0.0 | 0 | 0.917 | 7 | 0 | 0 | 43 | 0.00 | 2 | 1,258,383 | 66,841 | 1 | 48 | 300 | baseline:NONE (True) | 757.69 | 934.82 | 11.2 | 28.0 |

### T10. Per-cell table (policy runs; `source` = round3 recomputation or round-2 F1-corrected recomputation)

| layout | targets | seed | rule | source | total | C_elec | unserved | response | lateness | C_reb | served | n_unserved | swaps | shuttles | moved | stock-out slots | peak kW | end full | (17)/(18) reported | unservable orders |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located | written | 0 | NONE | round2_recomputed | 733.10 | 0.960 | 30 | 577.5 | 72.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 12 | 2.67 | 6 | {} | 1 |
| (a) co-located | written | 0 | REORDER_POINT | round2_recomputed | 905.04 | 0.907 | 30 | 577.5 | 72.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 3 | 2.67 | 6 | {} | 1 |
| (a) co-located | relaxed | 0 | NONE | round2_recomputed | 733.10 | 0.960 | 30 | 577.5 | 72.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 12 | 2.67 | 6 | {} | 1 |
| (a) co-located | relaxed | 0 | REORDER_POINT | round2_recomputed | 905.04 | 0.907 | 30 | 577.5 | 72.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 3 | 2.67 | 6 | {} | 1 |
| (b) 1 hub | written | 0 | NONE | round3 | 770.83 | 0.000 | 30 | 580.5 | 78.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 44 | 0.00 | 2 | {"(17)": 2, "(18)": 1} | 1 |
| (b) 1 hub | written | 0 | REORDER_POINT | round3 | 943.95 | 1.120 | 30 | 580.5 | 78.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 36 | 3.33 | 8 | {} | 1 |
| (b) 1 hub | relaxed | 0 | NONE | round2_recomputed | 770.83 | 0.000 | 30 | 580.5 | 78.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 44 | 0.00 | 2 | {} | 1 |
| (b) 1 hub | relaxed | 0 | REORDER_POINT | round2_recomputed | 943.95 | 1.120 | 30 | 580.5 | 78.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 36 | 3.33 | 8 | {} | 1 |
| (c) 2 hubs | written | 0 | NONE | round3 | 800.02 | 0.000 | 30 | 580.5 | 78.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 44 | 0.00 | 2 | {"(17)": 2, "(18)": 1} | 1 |
| (c) 2 hubs | written | 0 | REORDER_POINT | round3 | 973.14 | 1.120 | 30 | 580.5 | 78.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 36 | 2.00 | 8 | {} | 1 |
| (c) 2 hubs | relaxed | 0 | NONE | round2_recomputed | 800.02 | 0.000 | 30 | 580.5 | 78.0 | 0 | 0.972 | 1 | 7 | 0 | 0 | 44 | 0.00 | 2 | {} | 1 |
| (c) 2 hubs | relaxed | 0 | REORDER_POINT | round2_recomputed | 973.14 | 1.120 | 30 | 580.5 | 78.0 | 172 | 0.972 | 1 | 7 | 8 | 12 | 36 | 2.00 | 8 | {} | 1 |
| (a) co-located | written | 1 | NONE | round2_recomputed | 973.24 | 0.782 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 7 | 2.67 | 4 | {"(18)": 1} | 1 |
| (a) co-located | written | 1 | REORDER_POINT | round2_recomputed | 1116.60 | 0.782 | 210 | 523.5 | 138.0 | 192 | 0.806 | 7 | 7 | 9 | 12 | 7 | 2.00 | 4 | {"(18)": 1} | 1 |
| (a) co-located | relaxed | 1 | NONE | round2_recomputed | 973.24 | 0.782 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 7 | 2.67 | 4 | {} | 1 |
| (a) co-located | relaxed | 1 | REORDER_POINT | round2_recomputed | 1116.60 | 0.782 | 210 | 523.5 | 138.0 | 192 | 0.806 | 7 | 7 | 9 | 12 | 7 | 2.00 | 4 | {} | 1 |
| (b) 1 hub | written | 1 | NONE | round3 | 1001.74 | 0.000 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 25 | 0.00 | 1 | {"(17)": 2, "(18)": 1} | 1 |
| (b) 1 hub | written | 1 | REORDER_POINT | round3 | 1153.79 | 1.138 | 210 | 541.5 | 168.0 | 151 | 0.806 | 7 | 8 | 7 | 11 | 20 | 3.33 | 7 | {} | 1 |
| (b) 1 hub | relaxed | 1 | NONE | round2_recomputed | 1001.74 | 0.000 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 25 | 0.00 | 1 | {} | 1 |
| (b) 1 hub | relaxed | 1 | REORDER_POINT | round2_recomputed | 1153.79 | 1.138 | 210 | 541.5 | 168.0 | 151 | 0.806 | 7 | 8 | 7 | 11 | 20 | 3.33 | 7 | {} | 1 |
| (c) 2 hubs | written | 1 | NONE | round3 | 1030.93 | 0.000 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 25 | 0.00 | 1 | {"(17)": 2, "(18)": 1} | 1 |
| (c) 2 hubs | written | 1 | REORDER_POINT | round3 | 1180.86 | 1.013 | 210 | 541.5 | 168.0 | 149 | 0.806 | 7 | 8 | 7 | 9 | 20 | 2.00 | 5 | {} | 1 |
| (c) 2 hubs | relaxed | 1 | NONE | round3 | 1030.93 | 0.000 | 210 | 541.5 | 168.0 | 0 | 0.806 | 7 | 8 | 0 | 0 | 25 | 0.00 | 1 | {} | 1 |
| (c) 2 hubs | relaxed | 1 | REORDER_POINT | round3 | 1180.86 | 1.013 | 210 | 541.5 | 168.0 | 149 | 0.806 | 7 | 8 | 7 | 9 | 20 | 2.00 | 5 | {} | 1 |
| (a) co-located | written | 2 | NONE | round3 | 790.12 | 0.800 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 4 | 1.33 | 6 | {} | 0 |
| (a) co-located | written | 2 | REORDER_POINT | round3 | 1092.37 | 1.049 | 210 | 462.0 | 66.0 | 302 | 0.806 | 7 | 7 | 14 | 22 | 3 | 1.33 | 6 | {} | 0 |
| (a) co-located | relaxed | 2 | NONE | round3 | 790.12 | 0.800 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 4 | 1.33 | 6 | {} | 0 |
| (a) co-located | relaxed | 2 | REORDER_POINT | round3 | 1092.37 | 1.049 | 210 | 462.0 | 66.0 | 302 | 0.806 | 7 | 7 | 14 | 22 | 3 | 1.33 | 6 | {} | 0 |
| (b) 1 hub | written | 2 | NONE | round3 | 818.50 | 0.000 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 23 | 0.00 | 2 | {"(17)": 1, "(18)": 1} | 0 |
| (b) 1 hub | written | 2 | REORDER_POINT | round3 | 1031.55 | 1.031 | 210 | 462.0 | 66.0 | 212 | 0.806 | 7 | 7 | 10 | 12 | 5 | 2.00 | 8 | {} | 0 |
| (b) 1 hub | relaxed | 2 | NONE | round3 | 818.50 | 0.000 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 23 | 0.00 | 2 | {} | 0 |
| (b) 1 hub | relaxed | 2 | REORDER_POINT | round3 | 1031.55 | 1.031 | 210 | 462.0 | 66.0 | 212 | 0.806 | 7 | 7 | 10 | 12 | 5 | 2.00 | 8 | {} | 0 |
| (c) 2 hubs | written | 2 | NONE | round3 | 847.69 | 0.000 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 23 | 0.00 | 2 | {"(17)": 1, "(18)": 1} | 0 |
| (c) 2 hubs | written | 2 | REORDER_POINT | round3 | 1060.74 | 1.031 | 210 | 462.0 | 66.0 | 212 | 0.806 | 7 | 7 | 10 | 12 | 5 | 2.00 | 8 | {} | 0 |
| (c) 2 hubs | relaxed | 2 | NONE | round3 | 847.69 | 0.000 | 210 | 462.0 | 66.0 | 0 | 0.806 | 7 | 7 | 0 | 0 | 23 | 0.00 | 2 | {} | 0 |
| (c) 2 hubs | relaxed | 2 | REORDER_POINT | round3 | 1060.74 | 1.031 | 210 | 462.0 | 66.0 | 212 | 0.806 | 7 | 7 | 10 | 12 | 5 | 2.00 | 8 | {} | 0 |
| (a) co-located | written | 3 | NONE | round3 | 932.91 | 0.853 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 14 | 2.00 | 6 | {} | 1 |
| (a) co-located | written | 3 | REORDER_POINT | round3 | 1155.39 | 0.853 | 210 | 526.5 | 150.0 | 215 | 0.806 | 7 | 7 | 10 | 15 | 9 | 2.00 | 6 | {} | 1 |
| (a) co-located | relaxed | 3 | NONE | round3 | 932.91 | 0.853 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 14 | 2.00 | 6 | {} | 1 |
| (a) co-located | relaxed | 3 | REORDER_POINT | round3 | 1155.39 | 0.853 | 210 | 526.5 | 150.0 | 215 | 0.806 | 7 | 7 | 10 | 15 | 9 | 2.00 | 6 | {} | 1 |
| (b) 1 hub | written | 3 | NONE | round3 | 961.42 | 0.000 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 41 | 0.00 | 2 | {"(17)": 2, "(18)": 1} | 1 |
| (b) 1 hub | written | 3 | REORDER_POINT | round3 | 1071.45 | 1.120 | 240 | 504.0 | 135.0 | 109 | 0.778 | 8 | 7 | 5 | 9 | 23 | 3.33 | 8 | {"(17)": 1} | 1 |
| (b) 1 hub | relaxed | 3 | NONE | round3 | 961.42 | 0.000 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 41 | 0.00 | 2 | {} | 1 |
| (b) 1 hub | relaxed | 3 | REORDER_POINT | round3 | 1071.45 | 1.120 | 240 | 504.0 | 135.0 | 109 | 0.778 | 8 | 7 | 5 | 9 | 23 | 3.33 | 8 | {} | 1 |
| (c) 2 hubs | written | 3 | NONE | round3 | 990.61 | 0.000 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 41 | 0.00 | 2 | {"(17)": 2, "(18)": 1} | 1 |
| (c) 2 hubs | written | 3 | REORDER_POINT | round3 | 1100.54 | 1.013 | 240 | 504.0 | 135.0 | 109 | 0.778 | 8 | 7 | 5 | 9 | 23 | 2.00 | 6 | {"(17)": 1} | 1 |
| (c) 2 hubs | relaxed | 3 | NONE | round3 | 990.61 | 0.000 | 240 | 504.0 | 135.0 | 0 | 0.778 | 8 | 7 | 0 | 0 | 41 | 0.00 | 2 | {} | 1 |
| (c) 2 hubs | relaxed | 3 | REORDER_POINT | round3 | 1100.54 | 1.013 | 240 | 504.0 | 135.0 | 109 | 0.778 | 8 | 7 | 5 | 9 | 23 | 2.00 | 6 | {} | 1 |
| (a) co-located | written | 4 | NONE | round3 | 685.14 | 0.747 | 90 | 507.0 | 36.0 | 0 | 0.917 | 3 | 7 | 0 | 0 | 4 | 2.00 | 5 | {} | 1 |
| (a) co-located | written | 4 | REORDER_POINT | round3 | 879.37 | 0.978 | 90 | 507.0 | 36.0 | 194 | 0.917 | 3 | 7 | 9 | 14 | 6 | 2.67 | 6 | {} | 1 |
| (a) co-located | relaxed | 4 | NONE | round3 | 685.14 | 0.747 | 90 | 507.0 | 36.0 | 0 | 0.917 | 3 | 7 | 0 | 0 | 4 | 2.00 | 5 | {} | 1 |
| (a) co-located | relaxed | 4 | REORDER_POINT | round3 | 879.37 | 0.978 | 90 | 507.0 | 36.0 | 194 | 0.917 | 3 | 7 | 9 | 14 | 6 | 2.67 | 6 | {} | 1 |
| (b) 1 hub | written | 4 | NONE | round3 | 728.50 | 0.000 | 120 | 492.0 | 36.0 | 0 | 0.889 | 4 | 7 | 0 | 0 | 23 | 0.00 | 2 | {"(17)": 1, "(18)": 1} | 1 |
| (b) 1 hub | written | 4 | REORDER_POINT | round3 | 905.69 | 1.102 | 90 | 507.0 | 36.0 | 191 | 0.917 | 3 | 7 | 9 | 11 | 10 | 3.33 | 8 | {} | 1 |
| (b) 1 hub | relaxed | 4 | NONE | round3 | 728.50 | 0.000 | 120 | 492.0 | 36.0 | 0 | 0.889 | 4 | 7 | 0 | 0 | 23 | 0.00 | 2 | {} | 1 |
| (b) 1 hub | relaxed | 4 | REORDER_POINT | round3 | 905.69 | 1.102 | 90 | 507.0 | 36.0 | 191 | 0.917 | 3 | 7 | 9 | 11 | 10 | 3.33 | 8 | {} | 1 |
| (c) 2 hubs | written | 4 | NONE | round3 | 757.69 | 0.000 | 120 | 492.0 | 36.0 | 0 | 0.889 | 4 | 7 | 0 | 0 | 23 | 0.00 | 2 | {"(17)": 1, "(18)": 1} | 1 |
| (c) 2 hubs | written | 4 | REORDER_POINT | round3 | 934.82 | 1.049 | 90 | 507.0 | 36.0 | 191 | 0.917 | 3 | 7 | 9 | 11 | 10 | 2.00 | 7 | {} | 1 |
| (c) 2 hubs | relaxed | 4 | NONE | round3 | 757.69 | 0.000 | 120 | 492.0 | 36.0 | 0 | 0.889 | 4 | 7 | 0 | 0 | 23 | 0.00 | 2 | {} | 1 |
| (c) 2 hubs | relaxed | 4 | REORDER_POINT | round3 | 934.82 | 1.049 | 90 | 507.0 | 36.0 | 191 | 0.917 | 3 | 7 | 9 | 11 | 10 | 2.00 | 7 | {} | 1 |

## Figures

All files are in `outputs/e3u_round3/`, regenerated from `records.jsonl` by the report script (matplotlib Agg, 150 dpi):

- `fig_cost_by_layout.png` -- total cost by layout, panels written | relaxed; ILP free / ILP h = z = 0 / policy NONE / policy REORDER_POINT; bars = 5-seed means with 95 % t-CI error bars, dots = seeds, USD per 4 h window
- `fig_gap_by_layout.png` -- headline gap 100 (policy - ILP) / policy by layout, panels written | relaxed, ILP free and h = z = 0 vs NONE and vs REORDER_POINT, with t-CIs
- `fig_transfer_value.png` -- left: value of transfers per layout (written vs relaxed, t-CIs, open circles = upper bound from the 600 s MIP bound); right: cost of separation vs (a) with F_hub reference lines
- `fig_cost_components.png` -- stacked ILP cost components (27)-(32) per layout x switch x targets, 5-seed means
- `fig_solver.png` -- left: Gurobi wall time per run by status and source; right: MIP gap of the separated / written / transfers-free cells after 600 s vs the round-2 300 s gap
- `fig_in_transit.png` -- in-transit batteries m_t (24) over t for the ILP with transfers free, written (solid) vs relaxed (dashed), seed means and seeds
- `fig_full_stock_written_seed0.png` -- full-battery stock n_jLt per facility, ILP transfers free, seed 0, written targets
- `fig_full_stock_relaxed_seed0.png` -- same for the relaxed targets
- `fig_grid_load_seed0.png` -- grid-group charging load vs limit (21), ILP transfers free, seed 0, written targets

## Anomalies and checks

1. The script's own `--analyse` step failed after drawing the figures (`cannot convert float NaN to integer` in `e3u_transfers_usd_fixed.collect_anomalies`: `int(r.get('n_unservable', 0) or 0)` receives NaN on the 17 reused round-2 ILP rows, which never recorded `n_unservable`), so the run wrote no RESULTS.md; this report and the figures were produced from records.jsonl instead, and an English RESULTS.md stub was written by hand.
2. Baseline rows: 46 policy rows were recomputed in round 3 (every (layout, targets, seed) whose arc library was rebuilt); the 14 cells whose 12 ILP rows were all reused from round 2 (co-located seeds 0-1 both targets, (b) relaxed seeds 0-1, (c) relaxed seed 0) have no policy row in records.jsonl and were filled here from `outputs/e3u/relaxed_baseline_recomputed.csv` (F1-corrected same-policy rows, current package; `source = round2_recomputed`). The 22 overlapping cells agree to 1e-6 (no mismatch); the round-3 script asserted its recomputed totals against the stored round-2 written rows (0 mismatches, wall_time.json).
3. (c) 2 hubs relaxed seed 3: transfers-free optimum 720.726 > no-transfers optimum 720.690 by 0.036 USD (both OPTIMAL within the default MIPGap 1e-4, i.e. about 0.07 USD; solver tolerance, not structure).
4. Rejected MIP starts: 10/60, all of them the written NONE policy schedule offered (unverified) to the no_transfers model of the separated layouts (seeds [0, 1, 2, 3, 4]); the policy reports (17) at 1-2 swap sites and (18) there (swap-only sites cannot recharge, hubs receive nothing), no NONE fallback variant was clean, Gurobi ignored the start. All 50 other starts (REORDER_POINT schedules in the transfers-free models, NONE in the co-located and relaxed models) were accepted; round 2: 3/21 rejected for the same reason.
5. Policy reports (17)/(18) but does not enforce them: every separated NONE run on every seed ends with 1-2 full spares against the 4.5 required by (18) and 1-2 sites below R_end = 1, and the co-located policy of seed 1 reports (18); under the written targets the ILP therefore pays for recovery stock the policy skips, so the written headline gaps are conservative in the ILP's disfavour (the relaxed setting is the like-for-like comparison).
6. Structurally unservable orders (no delivery arc, both methods pay P = 30): 1 on seeds 0, 1, 3 and 4, 0 on seed 2, so the attainable served share is 35/36 = 0.972 on four of the five seeds.
7. Policy stranded bikes: 1 on every seed-0 instance (all layouts, both rules), 0 on seeds 1-4; pruned-arc fallbacks and suppressed late trips 0 everywhere (the shared pruning never bound the policy).
8. Checks: evaluate.check, identity (24) and Gurobi objective == evaluate.cost hold on 60/60 ILP runs; ILP total <= best policy total on 60/60; relaxed optimum <= written optimum on every OPTIMAL pair; duplicate keys in records.jsonl: 0.
9. Baseline charging rule differs by layout (F3): DEMAND_AWARE at co-located sites, HIGH_FIRST / ASAP at charge-only hubs; policy C_elec is exactly 0 in the separated NONE runs (nothing ever reaches a hub), so the policy's layout differences are F_hub plus 0-3 USD of travel / timing, not a charging effect.
10. Seed-2 lower bound below 0: on seed 2 the transfers-free incumbent at 600 s (690.37 (b), 719.56 (c)) is 0.56 USD above the no-transfers OPTIMUM of the same instance (689.81 / 719.00), which is a feasible point of the free model, so the free incumbent is provably at least 0.56 USD from optimal there and the per-seed value of transfers -0.56 must be read as 0 (interval [0, 13.1-13.7]); the 5-seed means in T1/T2 use the recorded incumbents as they are.
11. Seed 3 is the hardest instance for both methods (policy NONE 933-991 USD, 8 unserved; ILP 662-764 USD); the policy with rule NONE drops 1 / 7 / 7 / 8 / 3 orders on seeds 0-4 against the ILP's 1 / 5 / 4 / 5 / 3 (co-located, transfers free); the policy t-CIs (+/- 150-160 USD) are driven by this seed-0 / seed-4 vs seed-1 / seed-3 split.

## Interpretation (comparison with round 2)

1. Compared with round 2 (seeds 0-1 only, 15 of 36 cells skipped, no CIs) every cell now has five seeds and every ILP-only quantity carries a t-interval; the layout ranking (a) < (b) < (c) holds on every seed and both target settings, and the written separation cost 52.2 +/- 1.6 / 81.4 +/- 1.6 USD matches the round-2 point estimates 52.4 / 81.7 USD to within 1-2 USD, so the earlier two-seed reading was not a seed artefact.
2. The split of the separation cost is unchanged: F_hub (29.19 per hub) is 56-72 % of it under the written targets and 99 % under the relaxed targets, where the operational part is 0.08 / 0.08 USD; the whole operational penalty of separation is therefore the price of restoring 5 full spares at H with swap-only sites (C_j = 0) that cannot recharge, not a detour or queueing effect.
3. The within-horizon replenishment value of transfers is zero on all 15 relaxed (layout, seed) pairs (differences -0.036 to 0.036 USD, inside the MIPGap tolerance, 0 shuttles in every relaxed run, 6-9 swaps per window): nine spares cover the swaps six bikes need in four hours without any charging, exactly as in rounds 1 and 2.
4. Under the written targets the value of transfers in the separated layouts is 8.6 +/- 10.1 USD (b) and 8.6 +/- 10.1 USD (c), a lower bound whose per-seed values are 12.60, 0.82, -0.56, 18.24, 12.15 and 12.60, 0.82, -0.56, 18.17, 12.15; the mechanism is the same on every seed (h = z = 0 forces n_swaps = 4 and served share 0.822, one 2-battery shuttle restores 6 swaps and 0.894), and the round-2 values 6.6 / 12.6 USD sit inside the new intervals.
5. The 600 s re-solves answer the open question of round 2 negatively: the separated / written / transfers-free model is the only cell type that does not solve at the root, its gap after 600 s (1.8-2.0 %) is the same as after 300 s, and the round-2 incumbents improved by only 0.00, 0.00, 0.23, 0.32 USD; how much of the remaining 13-14 USD is primal cannot be told from the runs (on seed 2 the free incumbent is 0.56 USD above the no-transfers optimum, which is feasible for the free model, so the primal side is off by at least that much), and the no-transfers optima bound the free optimum from above, so the true value of transfers lies in [max(0, lower), upper] per seed; a certified value would need a tighter formulation or a much longer run rather than more seeds.
6. The ILP's advantage over the R2.3 policy is 21.3 +/- 11.3 % (a), 18.4 +/- 10.6 % (b), 17.8 +/- 10.4 % (c) under the written targets (round 2: 24.2 / 21.1 / 20.5 % on two seeds) and 21.4 +/- 11.3 / 21.2 +/- 10.2 / 20.5 +/- 10.0 % relaxed; the t-intervals are wide (+/- 10-11 pp) because the per-seed gap ranges from 10-16 % (seeds 4 and 0, where the policy drops 3 and 1 orders) to 29-32 % (seeds 1 and 3, where the policy drops 7-8 orders), but every interval excludes 0 and the ordering (a) >= (b) >= (c) survives.
7. On the co-located layout the mean 5-seed difference policy NONE - ILP (185 USD) decomposes into lateness 92, unserved 48, response 43, travel 1.2 and electricity 0.46 USD, i.e. service quality (fewer late and dropped orders through order re-assignment) and not energy or distance, the same composition as round 2.
8. The REORDER_POINT rule remains uniformly harmful with five seeds: +206.9 +/- 75.4 (a), +165.1 +/- 46.9 (b), +164.6 +/- 47.2 USD (c) over NONE, with 5-14 shuttles and 9-22 batteries moved per window and the unserved count unchanged on 12 of 15 (layout, seed) pairs (one order gained on (a) seed 3 and on (b)/(c) seed 4, at a cost of 191-215 USD of shuttle fees);a reorder trigger that pays f_e = 20 per run cannot pay for itself when P = 30 and the sites already hold 3 spares.
9. Battery-side constraints still never bind: hub charging peaks at 1.33 kW and co-located sites at 3.33 kW against the 6-8 kW grid limit, the ILP buys at most 2.4 kWh (0.8 USD) per window under the written targets and at most 0.39 kWh relaxed, and stock-outs appear only where the ILP lets stock run out deliberately near the end (0 stock-out slots at the reserved separated sites under written targets, 6-61 elsewhere).
10. Served share: the ILP serves 0.900 (a) and 0.894 (b)/(c) of the 36 orders with transfers against an attainable 0.972 on four seeds (one structurally unservable order), the policy 0.856; forbidding transfers in the separated layouts under the written targets costs 0.072 of served share (2-3 orders), nothing elsewhere.
11. What changed against round 2 is therefore coverage and certainty, not conclusions: the layout ranking, the zero replenishment value, the recovery-target origin of the transfer value, the sign of the REORDER_POINT rule and the service-quality composition of the gap all hold on 5 seeds with intervals; the one open item (the 2 % gap of the separated written transfers-free cells) is a solver-bound issue that 600 s did not fix.
12. Modelling implication for the supervisor (unchanged): rho and R_end are the only lever that gives transfers any value in this family; a periodic end condition or a longer rolling horizon is needed before within-horizon replenishment can be observed, and the hub fixed cost dominates every layout comparison at this scale.

## Files

- `outputs/e3u_round3/RESULTS_final.md` (this report), `RESULTS.md` (short English provenance stub replacing the failed automatic report), the nine figures listed above, all written by `experiments/e3u_round3_report.py` (pandas + matplotlib only, no solver calls; run from `ebike_swap_sim/`); `records.jsonl`, `results.csv`, `run_stdout.log`, `wall_time.json`, `instances/` untouched.
