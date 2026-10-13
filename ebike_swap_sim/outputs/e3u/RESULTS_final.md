# E3u final report -- transfers and separation under USD costs, 4 h window (round 2, corrected)

## Summary

On the usd4h family under USD costs and the 4-hour evening peak (6 bikes / 36 orders / 3 spare batteries per site), the ILP's total cost is still lowest in the co-located layout (about 637 $); the separated layouts cost 52 $ more (1 charging hub) and 82 $ more (2 hubs), of which 29 / 58 $ is hub fixed cost and about 23 $ is the operating penalty (one shuttle run at 22 $ plus response time). The value of transfers is 0 in the co-located layout and 0.6-12.6 $ per window in the separated layouts under the end targets as written in the document (an order of magnitude smaller than the roughly 255 toy units of round 1, because the unserved penalty fell from 100 to 30), and once the end targets (17)(18) are relaxed the value of transfers drops to 0 in every layout, which shows that there is still no "within-window restocking" value in the 4-hour window; all the remaining value comes from the recovery target "keep 5 full batteries at the end", which squeezes the number of possible swaps in the separated layouts down to 4. Compared with the round-2 baseline policy, the ILP saves 24 % (co-located), 21 % (1 hub) and 20 % (2 hubs) under the written targets and 24 / 24 / 16 % with the targets relaxed, lower than round 1's 48 / 37 / 36 %, with the gap coming mainly from unserved and late orders rather than from energy; the baseline's REORDER_POINT transfer rule is 143-302 $ more expensive than no transfers in every layout and every seed, because the 20 $ fixed fee per shuttle run does not buy the service of a single order. Following fairness fix F1, this report recomputed all "relaxed-target" baseline rows with the current package (in the old file those rows used a different policy with reserve 0; only the 6 rows of the co-located layout were affected, REORDER_POINT by at most 61 $); after the recomputation the baseline is identical under both target settings, 18/18 fixed-solve certificates are feasible, and the old rows are kept in the appendix column relaxed_baseline_prefix_policy. Caveats: 15 of the 36 ILP solves were skipped because of the 57-minute wall-clock budget (seed 2 is entirely missing), 4 written-target free-transfer solves of the separated layouts hit the 300 s limit (gap about 2 %), so the ILP cells have only 1-2 seeds and no confidence intervals, and the value of transfers under the written targets is only a lower bound (upper bound 15-26 $).

## Setup and provenance

- Experiment script `experiments/e3u_transfers_usd.py` (run 2026-10-12, 56.4 min single process, Threads 3, TimeLimit 300 s, wall budget 57 min); the review-fixed copy `experiments/e3u_transfers_usd_fixed.py` was NOT re-run (its fixes are declaration / fairness fixes that this report applies to the saved rows instead).
- Inputs: `outputs/e3u/results.csv` (72 rows, no duplicate (instance, method, variant) keys: 0 rows dropped), `run.log`, `wall_time.json`, 18 saved instances `instances/{layout}_{targets}_seed{s}.json`.
- Family `usd4h` (R2.2): 6 bikes, 36 orders, H = 48 (Delta 5 min, 17:00-21:00), L = 12, `usd_sunk` costs (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, f_e 20 $ per shuttle, v_reb 1 $ per battery, F 12.03 / F_hub 29.19, bB 0.332, bC 0.082 per 4 h). Equal totals in every layout: sum B = 9 (3 per swap site, hubs 0), sum C = 6, grid group 8 kW (6 kW 18-20 h). Shuttles every 6 slots from t = 2, U_e = 6. Written targets rho 0.5, R_end_j = 1 at swap sites; relaxed control rho 0, R_end 0 for every layout and both switches. Pruning tau_max 4, start_slack 6, reachable pruning (lossless per r2_size_probe).
- **Fairness fix F1 applied to the saved rows (review `notes/workflow6_round2_review.json`).** The 18 `relaxed` baseline rows in `results.csv` were produced before the fix, with the DEMAND_AWARE charging reserve read from the relaxed copy (reserve 0), i.e. a different policy from the written rows. For this report every relaxed copy was rebuilt from the saved written instance with the current `common.relax_end_targets` (byte-identical to the saved relaxed JSON apart from meta, asserted 9/9), and the policy was re-run with `common.run_baseline_case` (current package, `policy_reserve_source = written_R_end`), both transfer rules, 36 baseline runs in 33 s (`relaxed_baseline_recomputed.csv`). The current package reproduces all 18 written rows exactly, and every recomputed relaxed row equals its written counterpart exactly (same schedule). Only the 6 co-located relaxed rows differ from the pre-fix values (NONE by 0.23-0.27 USD, REORDER_POINT by 3.5-61.2 USD, appendix A1); the separated layouts never differed because the hubs charge HIGH_FIRST and the reserve only enters DEMAND_AWARE at charge-capable swap sites. `gap_vs_baseline_*` of the 9 relaxed ILP rows were recomputed against the recomputed baselines (T5, T6). No ILP was re-solved.
- Same-policy certificates: the recomputed relaxed schedules were injected as fixed MIP starts into the relaxed E2 models (Threads 2, every variable fixed; NONE -> no_transfers model, REORDER_POINT -> transfers-free model): 18/18 feasible, fixed-solve objective == `evaluate.cost` (`relaxed_start_certificates.csv`, 3.1 s build + 1.4 s per certificate).
- Baseline charging rule per layout (fairness F3, declared here): co-located sites DEMAND_AWARE (R2.3); charge-only hubs HIGH_FIRST / ASAP (`hub_charge_rule`, DECISIONS R2 implementation notes) because the literal hub forecast is 0. The ILP-only quantities (value of transfers, cost of separation) are unaffected; baseline-vs-baseline layout readings mix the layout with this rule difference.
- Headline gap definition everywhere: 100 (baseline - ILP) / baseline, same instance and same end-target setting; the baseline is the R2.3 policy with transfer_rule NONE (default) or REORDER_POINT.

## Headline numbers

- ILP total (USD per 4 h, mean of seeds 0-1), transfers free, written targets: (a) co-located 637.37, (b) 1 hub 689.81, (c) 2 hubs 719.05; relaxed targets 636.94 / 666.32 / 673.27 (seed 0 only for (c)).
- Value of transfers = ILP cost(h = z = 0) - ILP cost(transfers free): written (a) 0.03, (b) 6.59 (seeds 12.60, 0.58), (c) 12.60 (seed 0); relaxed (a) 0.00, (b) 0.00, (c) 0.04. The written separated values are lower bounds because the free runs stopped at TIME_LIMIT (gap 1.9-2.0 %); upper bounds from the 300 s bounds: (b) 25.9 / 14.9, (c) 25.8 USD. Round 1 (toy units, 2 h): 0 / 257 / 254.5, entirely a recovery-target effect.
- Cost of separation vs (a), transfers free: written +52.44 (b) / +81.68 (c), of which hub setup F_hub 29.19 / 58.38 and operations 23.3 / 23.3; relaxed +29.38 / +58.76, i.e. hub setup plus 0.2-0.4 USD. Round 1: +55.4 / +97.9 toy units (40 / 80 setup + 15 / 18 operations).
- Headline gap (baseline NONE - ILP)/baseline, ILP transfers free: written 24.2 % (a), 21.1 % (b), 20.5 % (c); relaxed 24.2 / 23.9 / 15.8 %; vs REORDER_POINT 36.5 / 33.8 / 32.8 % (written). Round 1: 48 / 37 / 36 % vs NONE.
- Baseline (n = 3, 95 % t-CI): NONE 832 +/- 312 (a), 864 +/- 303 (b), 893 +/- 303 (c); REORDER_POINT 1038 +/- 288, 1043 +/- 262, 1072 +/- 259; REORDER_POINT is worse than NONE on every layout and seed (+143 to +302 USD) with identical unserved counts.
- Served share: ILP 0.917 (a, both targets), 0.903 (b written free) vs 0.833 (b written h = z = 0), 0.917 (b relaxed); baseline 0.861 everywhere (1 / 7 / 7 unserved on seeds 0 / 1 / 2). One order per seed-0 and seed-1 instance is structurally unservable (no delivery arc; both methods pay P), so the attainable ceiling is 35/36 = 0.972.
- Transfers used by the ILP: 0 in (a) and under every relaxed run; exactly 1 shuttle with 2 batteries (C_reb 22) in (b)/(c) under the written targets. Baseline REORDER_POINT: 7-14 shuttles, 9-22 batteries.
- Grid: peak charging load 1.33 kW at the hubs (written free), at most 3.33 kW at co-located sites, against 8 / 6 kW; electricity <= 0.82 USD per window; under the relaxed targets the ILP buys 0-0.39 kWh.
- Solver: 36 ILP runs planned, 17 OPTIMAL (72-187 s, root node), 4 TIME_LIMIT (300 s, gap 1.9-2.0 %), 15 SKIPPED_BUDGET; 1.11-1.39 M binaries, 62-71 k rows; MIP start accepted on 18/21 solved runs.

## Tables

### T1. ILP total cost (26), USD per 4 h window, by layout x transfer switch x end targets

Mean over the seeds that were solved (n in brackets; seeds 0-1 only, seed 2 was skipped by the wall budget), per-seed values in parentheses; no t-CI because n <= 2 for every ILP cell. `status` = Gurobi status of the runs (O = OPTIMAL, T = TIME_LIMIT, 2 % gap).

| layout | targets | transfers free | h = z = 0 (no transfers) | value of transfers (none - free) | status free / none |
|---|---|---|---|---|---|
| (a) co-located 3 sites | written | 637.37 [n=2] (615.15, 659.60) | 637.40 [n=2] (615.20, 659.60) | 0.03 (0.05, 0.00) | OO/OO |
| (a) co-located 3 sites | relaxed | 636.94 [n=2] (614.51, 659.37) | 636.94 [n=2] (614.51, 659.37) | 0.00 (0.00, 0.00) | OO/OO |
| (b) 3 swap sites + 1 hub | written | 689.81 [n=2] (668.46, 711.17) | 696.40 [n=2] (681.06, 711.75) | 6.59 (12.60, 0.58) | TT/OO |
| (b) 3 swap sites + 1 hub | relaxed | 666.32 [n=2] (644.08, 688.56) | 666.32 [n=2] (644.08, 688.56) | 0.00 (0.00, 0.00) | OO/OO |
| (c) 3 swap sites + 2 hubs | written | 719.05 [n=2] (697.65, 740.45) | 710.25 [n=1] (710.25) | 12.60 (12.60) | TT/O |
| (c) 3 swap sites + 2 hubs | relaxed | 673.27 [n=1] (673.27) | 673.30 [n=1] (673.30) | 0.04 (0.04) | O/O |

### T2. Cost of separation = ILP total(layout) - ILP total(co-located), same seed, same switch, same targets (USD per 4 h)

| layout | targets | switch | separation cost mean (per seed) | of which hub setup F_hub (27) | operational part |
|---|---|---|---|---|---|
| (b) 3 swap sites + 1 hub | written | transfers free | 52.44 (53.31, 51.57) | 29.19 | 23.25 |
| (b) 3 swap sites + 1 hub | written | no_transfers | 59.00 (65.86, 52.15) | 29.19 | 29.81 |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 29.38 (29.57, 29.19) | 29.19 | 0.19 |
| (b) 3 swap sites + 1 hub | relaxed | no_transfers | 29.38 (29.57, 29.19) | 29.19 | 0.19 |
| (c) 3 swap sites + 2 hubs | written | transfers free | 81.68 (82.50, 80.85) | 58.38 | 23.30 |
| (c) 3 swap sites + 2 hubs | written | no_transfers | 95.05 (95.05) | 58.38 | 36.67 |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 58.76 (58.76) | 58.38 | 0.38 |
| (c) 3 swap sites + 2 hubs | relaxed | no_transfers | 58.80 (58.80) | 58.38 | 0.42 |

### T3. ILP operational metrics (seed means over solved seeds)

| layout | targets | switch | n | served share | n_unserved | C_reb | transfers used | batteries moved | n_swaps | stock-out slots (sum over facilities) | hub / site grid peak kW (limit 8, 6 in 18-20 h) | end full total (>= 4.5 under written) | kWh purchased | C_elec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | transfers free | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 8.0 | 26.5 | 2.33 | 5.0 | 1.56 | 0.50 |
| (a) co-located 3 sites | written | no_transfers | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 8.5 | 31.5 | 2.00 | 5.0 | 1.64 | 0.52 |
| (a) co-located 3 sites | relaxed | transfers free | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 8.5 | 48.0 | 0.33 | 1.0 | 0.19 | 0.06 |
| (a) co-located 3 sites | relaxed | no_transfers | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 8.0 | 48.0 | 0.33 | 1.5 | 0.19 | 0.06 |
| (b) 3 swap sites + 1 hub | written | transfers free | 2 | 0.903 | 3.5 | 22.0 | 1.0 | 2.0 | 6.0 | 0.0 | 1.33 | 5.0 | 0.89 | 0.28 |
| (b) 3 swap sites + 1 hub | written | no_transfers | 2 | 0.833 | 6.0 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 | 0.00 | 5.0 | 0.00 | 0.00 |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 7.5 | 41.0 | 0.00 | 1.5 | 0.00 | 0.00 |
| (b) 3 swap sites + 1 hub | relaxed | no_transfers | 2 | 0.917 | 3.0 | 0.0 | 0.0 | 0.0 | 8.0 | 53.0 | 0.00 | 1.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | written | transfers free | 2 | 0.903 | 3.5 | 22.0 | 1.0 | 2.0 | 6.0 | 0.0 | 1.33 | 5.0 | 0.86 | 0.28 |
| (c) 3 swap sites + 2 hubs | written | no_transfers | 1 | 0.861 | 5.0 | 0.0 | 0.0 | 0.0 | 4.0 | 0.0 | 0.00 | 5.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 1 | 0.972 | 1.0 | 0.0 | 0.0 | 0.0 | 9.0 | 58.0 | 0.00 | 0.0 | 0.00 | 0.00 |
| (c) 3 swap sites + 2 hubs | relaxed | no_transfers | 1 | 0.972 | 1.0 | 0.0 | 0.0 | 0.0 | 9.0 | 56.0 | 0.00 | 0.0 | 0.00 | 0.00 |

### T4. Baseline policy (R2.3 rules): NONE vs REORDER_POINT, mean over 3 seeds with 95 % t-CI (USD per 4 h)

The recomputed relaxed-copy rows are identical to the written rows (same policy, written reserve), so one table serves both target settings. `families` = (17)/(18) reported by the written run (not enforced; off under the relaxed targets).

| layout | rule | total | unserved (P) | response | lateness | C_reb | C_elec | served share | transfers used | batteries moved | stock-out slots | grid peak kW | end full | (17)/(18) reported (seeds) | charge rule |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | NONE | 832.16 +/- 311.68 | 150.00 +/- 258.16 | 527.00 +/- 146.81 | 102.00 +/- 142.18 | 0.00 +/- 0.00 | 0.85 +/- 0.24 | 0.861 | 0.0 | 0.0 | 7.7 | 2.22 | 5.3 | s0:{}; s1:{"(18)": 1}; s2:{} | sites DEMAND_AWARE |
| (a) co-located 3 sites | REORDER_POINT | 1038.00 +/- 287.62 | 150.00 +/- 258.16 | 521.00 +/- 143.56 | 92.00 +/- 99.24 | 222.00 +/- 173.89 | 0.91 +/- 0.33 | 0.861 | 10.3 | 15.3 | 4.3 | 2.00 | 5.3 | s0:{}; s1:{"(18)": 1}; s2:{} | sites DEMAND_AWARE |
| (b) 3 swap sites + 1 hub | NONE | 863.69 +/- 302.84 | 150.00 +/- 258.16 | 528.00 +/- 150.02 | 104.00 +/- 138.49 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0.861 | 0.0 | 0.0 | 30.7 | 0.00 | 1.7 | s0:{"(17)": 2, "(18)": 1}; s1:{"(17)": 2, "(18)": 1}; s2:{"(17)": 1, "(18)": 1} | hubs HIGH_FIRST (ASAP) |
| (b) 3 swap sites + 1 hub | REORDER_POINT | 1043.10 +/- 261.81 | 150.00 +/- 258.16 | 528.00 +/- 150.02 | 104.00 +/- 138.49 | 178.33 +/- 76.98 | 1.10 +/- 0.14 | 0.861 | 8.3 | 11.7 | 20.3 | 2.89 | 7.7 | s0:{}; s1:{}; s2:{} | hubs HIGH_FIRST (ASAP) |
| (c) 3 swap sites + 2 hubs | NONE | 892.88 +/- 302.84 | 150.00 +/- 258.16 | 528.00 +/- 150.02 | 104.00 +/- 138.49 | 0.00 +/- 0.00 | 0.00 +/- 0.00 | 0.861 | 0.0 | 0.0 | 30.7 | 0.00 | 1.7 | s0:{"(17)": 2, "(18)": 1}; s1:{"(17)": 2, "(18)": 1}; s2:{"(17)": 1, "(18)": 1} | hubs HIGH_FIRST (ASAP) |
| (c) 3 swap sites + 2 hubs | REORDER_POINT | 1071.58 +/- 259.05 | 150.00 +/- 258.16 | 528.00 +/- 150.02 | 104.00 +/- 138.49 | 177.67 +/- 79.19 | 1.05 +/- 0.14 | 0.861 | 8.3 | 11.0 | 20.3 | 2.00 | 7.0 | s0:{}; s1:{}; s2:{} | hubs HIGH_FIRST (ASAP) |

### T5. Headline gap 100 (baseline - ILP) / baseline, corrected (relaxed ILP vs the same-policy baseline)

Mean over solved seeds (per-seed in parentheses). `old` = the value in results.csv / RESULTS.md, computed against the pre-fix relaxed baseline rows (reserve-0 policy); identical for the written rows.

| layout | targets | switch | n | vs NONE (default) | old | vs REORDER_POINT | old | vs best baseline |
|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | transfers free | 2 | 24.2 % (16.1, 32.2) | 24.2 % | 36.5 % (32.0, 40.9) | 36.5 % | 24.2 % |
| (a) co-located 3 sites | written | no_transfers | 2 | 24.2 % (16.1, 32.2) | 24.2 % | 36.5 % (32.0, 40.9) | 36.5 % | 24.2 % |
| (a) co-located 3 sites | relaxed | transfers free | 2 | 24.2 % (16.2, 32.3) | 24.2 % | 36.5 % (32.1, 40.9) | 33.1 % | 24.2 % |
| (a) co-located 3 sites | relaxed | no_transfers | 2 | 24.2 % (16.2, 32.3) | 24.2 % | 36.5 % (32.1, 40.9) | 33.1 % | 24.2 % |
| (b) 3 swap sites + 1 hub | written | transfers free | 2 | 21.1 % (13.3, 29.0) | 21.1 % | 33.8 % (29.2, 38.4) | 33.8 % | 21.1 % |
| (b) 3 swap sites + 1 hub | written | no_transfers | 2 | 20.3 % (11.6, 28.9) | 20.3 % | 33.1 % (27.9, 38.3) | 33.1 % | 20.3 % |
| (b) 3 swap sites + 1 hub | relaxed | transfers free | 2 | 23.9 % (16.4, 31.3) | 23.9 % | 36.0 % (31.8, 40.3) | 36.0 % | 23.9 % |
| (b) 3 swap sites + 1 hub | relaxed | no_transfers | 2 | 23.9 % (16.4, 31.3) | 23.9 % | 36.0 % (31.8, 40.3) | 36.0 % | 23.9 % |
| (c) 3 swap sites + 2 hubs | written | transfers free | 2 | 20.5 % (12.8, 28.2) | 20.5 % | 32.8 % (28.3, 37.3) | 32.8 % | 20.5 % |
| (c) 3 swap sites + 2 hubs | written | no_transfers | 1 | 11.2 % (11.2) | 11.2 % | 27.0 % (27.0) | 27.0 % | 11.2 % |
| (c) 3 swap sites + 2 hubs | relaxed | transfers free | 1 | 15.8 % (15.8) | 15.8 % | 30.8 % (30.8) | 30.8 % | 15.8 % |
| (c) 3 swap sites + 2 hubs | relaxed | no_transfers | 1 | 15.8 % (15.8) | 15.8 % | 30.8 % (30.8) | 30.8 % | 15.8 % |

### T6. Per-instance table (every ILP run, corrected baselines)

| layout | targets | seed | switch | status | ILP total | bound | gap | C_setup | C_travel | C_elec | unserved | response | lateness | C_reb | served | swaps | transfers | moved | stock-out slots | peak kW | end full | binaries | rows | solve s | MIP start (accepted) | baseline NONE | baseline REORDER | gap vs NONE % | gap vs REORDER % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) co-located | written | 0 | transfers free | OPTIMAL | 615.15 | 615.15 | 0.0000 | 39.57 | 12.31 | 0.764 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 17 | 3.33 | 5 | 1,155,029 | 63,316 | 173 | baseline_reorder:REORDER_POINT (True) | 733.10 | 905.04 | 16.1 | 32.0 |
| (a) co-located | written | 0 | no_transfers | OPTIMAL | 615.20 | 615.14 | 0.0001 | 39.57 | 12.31 | 0.818 | 30 | 523.5 | 9.0 | 0 | 0.972 | 11 | 0 | 0 | 21 | 2.67 | 5 | 1,155,029 | 63,316 | 165 | baseline:NONE (True) | 733.10 | 905.04 | 16.1 | 32.0 |
| (a) co-located | relaxed | 0 | transfers free | OPTIMAL | 614.51 | 614.51 | 0.0000 | 39.57 | 12.31 | 0.124 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 54 | 0.67 | 0 | 1,155,029 | 63,316 | 119 | baseline_reorder:REORDER_POINT (True) | 733.10 | 905.04 | 16.2 | 32.1 |
| (a) co-located | relaxed | 0 | no_transfers | OPTIMAL | 614.51 | 614.51 | 0.0000 | 39.57 | 12.31 | 0.124 | 30 | 523.5 | 9.0 | 0 | 0.972 | 10 | 0 | 0 | 61 | 0.67 | 0 | 1,155,029 | 63,316 | 112 | baseline:NONE (True) | 733.10 | 905.04 | 16.2 | 32.1 |
| (b) 1 hub | written | 0 | transfers free | TIME_LIMIT | 668.46 | 655.13 | 0.0199 | 68.76 | 11.99 | 0.213 | 60 | 499.5 | 6.0 | 22 | 0.944 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,270,583 | 66,149 | 300 | baseline_reorder:REORDER_POINT (True) | 770.83 | 943.95 | 13.3 | 29.2 |
| (b) 1 hub | written | 0 | no_transfers | OPTIMAL | 681.06 | 681.06 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 448.5 | 3.0 | 0 | 0.861 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,270,583 | 66,149 | 122 | baseline:NONE(unverified) (False) | 770.83 | 943.95 | 11.6 | 27.9 |
| (b) 1 hub | relaxed | 0 | transfers free | OPTIMAL | 644.08 | 644.02 | 0.0001 | 68.76 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 59 | 0.00 | 0 | 1,270,583 | 66,149 | 187 | baseline_reorder:REORDER_POINT (True) | 770.83 | 943.95 | 16.4 | 31.8 |
| (b) 1 hub | relaxed | 0 | no_transfers | OPTIMAL | 644.08 | 644.02 | 0.0001 | 68.76 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 60 | 0.00 | 0 | 1,270,583 | 66,149 | 121 | baseline:NONE (True) | 770.83 | 943.95 | 16.4 | 31.8 |
| (c) 2 hubs | written | 0 | transfers free | TIME_LIMIT | 697.65 | 684.42 | 0.0190 | 97.95 | 11.99 | 0.213 | 60 | 499.5 | 6.0 | 22 | 0.944 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,392,552 | 70,905 | 300 | baseline_reorder:REORDER_POINT (True) | 800.02 | 973.14 | 12.8 | 28.3 |
| (c) 2 hubs | written | 0 | no_transfers | OPTIMAL | 710.25 | 710.21 | 0.0001 | 97.95 | 10.80 | 0.000 | 150 | 448.5 | 3.0 | 0 | 0.861 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,392,552 | 70,905 | 86 | baseline:NONE(unverified) (False) | 800.02 | 973.14 | 11.2 | 27.0 |
| (c) 2 hubs | relaxed | 0 | transfers free | OPTIMAL | 673.27 | 673.22 | 0.0001 | 97.95 | 12.82 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 58 | 0.00 | 0 | 1,392,552 | 70,905 | 118 | baseline_reorder:REORDER_POINT (True) | 800.02 | 973.14 | 15.8 | 30.8 |
| (c) 2 hubs | relaxed | 0 | no_transfers | OPTIMAL | 673.30 | 673.25 | 0.0001 | 97.95 | 12.85 | 0.000 | 30 | 523.5 | 9.0 | 0 | 0.972 | 9 | 0 | 0 | 56 | 0.00 | 0 | 1,392,552 | 70,905 | 89 | baseline:NONE (True) | 800.02 | 973.14 | 15.8 | 30.8 |
| (a) co-located | written | 1 | transfers free | OPTIMAL | 659.60 | 659.60 | 0.0000 | 39.57 | 10.80 | 0.231 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 36 | 1.33 | 5 | 1,106,236 | 62,446 | 94 | baseline_round1:REORDER_POINT (True) | 973.24 | 1116.60 | 32.2 | 40.9 |
| (a) co-located | written | 1 | no_transfers | OPTIMAL | 659.60 | 659.60 | 0.0000 | 39.57 | 10.80 | 0.231 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 42 | 1.33 | 5 | 1,106,236 | 62,446 | 86 | baseline_round1:NONE (True) | 973.24 | 1116.60 | 32.2 | 40.9 |
| (a) co-located | relaxed | 1 | transfers free | OPTIMAL | 659.37 | 659.37 | 0.0000 | 39.57 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 7 | 0 | 0 | 42 | 0.00 | 2 | 1,106,236 | 62,446 | 88 | baseline_reorder:REORDER_POINT (True) | 973.24 | 1116.60 | 32.3 | 40.9 |
| (a) co-located | relaxed | 1 | no_transfers | OPTIMAL | 659.37 | 659.37 | 0.0000 | 39.57 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 35 | 0.00 | 3 | 1,106,236 | 62,446 | 95 | baseline:NONE (True) | 973.24 | 1116.60 | 32.3 | 40.9 |
| (b) 1 hub | written | 1 | transfers free | TIME_LIMIT | 711.17 | 696.89 | 0.0201 | 68.76 | 11.05 | 0.356 | 150 | 456.0 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,219,763 | 65,322 | 300 | baseline_reorder:REORDER_POINT (True) | 1001.74 | 1153.79 | 29.0 | 38.4 |
| (b) 1 hub | written | 1 | no_transfers | OPTIMAL | 711.75 | 711.75 | 0.0000 | 68.76 | 9.99 | 0.000 | 210 | 423.0 | 0.0 | 0 | 0.806 | 4 | 0 | 0 | 0 | 0.00 | 5 | 1,219,763 | 65,322 | 115 | baseline:NONE(unverified) (False) | 1001.74 | 1153.79 | 28.9 | 38.3 |
| (b) 1 hub | relaxed | 1 | transfers free | OPTIMAL | 688.56 | 688.56 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 6 | 0 | 0 | 23 | 0.00 | 3 | 1,219,763 | 65,322 | 102 | baseline_reorder:REORDER_POINT (True) | 1001.74 | 1153.79 | 31.3 | 40.3 |
| (b) 1 hub | relaxed | 1 | no_transfers | OPTIMAL | 688.56 | 688.56 | 0.0000 | 68.76 | 10.80 | 0.000 | 150 | 456.0 | 3.0 | 0 | 0.861 | 7 | 0 | 0 | 46 | 0.00 | 2 | 1,219,763 | 65,322 | 72 | baseline:NONE (True) | 1001.74 | 1153.79 | 31.3 | 40.3 |
| (c) 2 hubs | written | 1 | transfers free | TIME_LIMIT | 740.45 | 726.08 | 0.0194 | 97.95 | 11.16 | 0.338 | 150 | 456.0 | 3.0 | 22 | 0.861 | 6 | 1 | 2 | 0 | 1.33 | 5 | 1,337,408 | 70,012 | 300 | baseline_reorder:REORDER_POINT (True) | 1030.93 | 1180.86 | 28.2 | 37.3 |
| (c) 2 hubs | written | 1 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 1030.93 | 1180.86 | - | - |
| (c) 2 hubs | relaxed | 1 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 1030.93 | 1180.86 | - | - |
| (c) 2 hubs | relaxed | 1 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 1030.93 | 1180.86 | - | - |
| (a) co-located | written | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 790.12 | 1092.37 | - | - |
| (a) co-located | written | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 790.12 | 1092.37 | - | - |
| (a) co-located | relaxed | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 790.12 | 1092.37 | - | - |
| (a) co-located | relaxed | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 790.12 | 1092.37 | - | - |
| (b) 1 hub | written | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 818.50 | 1031.55 | - | - |
| (b) 1 hub | written | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 818.50 | 1031.55 | - | - |
| (b) 1 hub | relaxed | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 818.50 | 1031.55 | - | - |
| (b) 1 hub | relaxed | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 818.50 | 1031.55 | - | - |
| (c) 2 hubs | written | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 847.69 | 1060.74 | - | - |
| (c) 2 hubs | written | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 847.69 | 1060.74 | - | - |
| (c) 2 hubs | relaxed | 2 | transfers free | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 847.69 | 1060.74 | - | - |
| (c) 2 hubs | relaxed | 2 | no_transfers | SKIPPED_BUDGET | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | 847.69 | 1060.74 | - | - |

### T7. Solver statistics (Gurobi, Threads 3, TimeLimit 300 s, OutputFlag 0; reachable pruning, tau_max 4, start_slack 6)

- Runs: 36 ILP runs planned (3 layouts x 2 targets x 2 switches x 3 seeds); status counts: OPTIMAL 17, TIME_LIMIT 4, SKIPPED_BUDGET 15 (57 min wall budget exhausted after seed 1 / layout (c) written-free).
- Binaries: 1,106,236 - 1,392,552 (co-located 1,130,632, 1 hub 1,245,173, 2 hubs 1,381,523); rows 62,446 - 70,905; arc library build 2.8 s (max 6.6); model build 5.2 s.
- OPTIMAL runs (17): solve time mean 114 s, range 72 - 187 s, reported gap 0 (<= 1e-4 MIPGap), node count 1 on every optimal run (solved at the root).
- TIME_LIMIT runs (4): all four are the separated layouts under the written targets with transfers free (seeds 0-1); incumbents at 300 s with gap 1.9-2.0 % (bounds: 1 hub 655.13 / 696.89, 2 hubs 684.43 / 726.08).
- Checks: evaluate.check ok on 21/21 solved runs, identity (24) ok 21/21, Gurobi objective == evaluate.cost on 21/21.
- MIP-start acceptance (fix-and-solve certificate at build time): baseline:NONE accepted=True: 6; baseline:NONE(unverified) accepted=False: 3; baseline_reorder:REORDER_POINT accepted=True: 10; baseline_round1:NONE accepted=True: 1; baseline_round1:REORDER_POINT accepted=True: 1. The three rejected starts are the written NONE schedule of the separated layouts in the no_transfers model, which reports (17) x2 + (18) (hubs charge nothing they never receive); no NONE fallback variant passed check there, so the unverified default was offered and Gurobi ignored it.
- Same-policy relaxed-copy certificates run for this report (Threads 2, every variable fixed to the policy schedule): 18/18 feasible (NONE start in the no_transfers model, REORDER_POINT start in the transfers-free model, 9 instances each), fixed-solve objective == evaluate.cost in 18/18, 3.1 s build + 1.4 s certificate each.

### A1. Appendix: relaxed-copy baseline rows, pre-fix policy (results.csv) vs recomputed same policy

| layout | seed | rule | relaxed_baseline_prefix_policy (reserve 0, results.csv) | recomputed (written reserve, this report) | written row | difference (prefix - recomputed) | prefix C_elec / end full | recomputed C_elec / end full |
|---|---|---|---|---|---|---|---|---|
| (a) co-located | 0 | NONE | 732.849 | 733.098 | 733.098 | -0.249 | 0.711 / 5 | 0.960 / 6 |
| (a) co-located | 0 | REORDER_POINT | 860.742 | 905.045 | 905.045 | -44.302 | 0.604 / 4 | 0.907 / 6 |
| (a) co-located | 1 | NONE | 972.978 | 973.244 | 973.244 | -0.267 | 0.516 / 3 | 0.782 / 4 |
| (a) co-located | 1 | REORDER_POINT | 1055.383 | 1116.596 | 1116.596 | -61.213 | 0.569 / 4 | 0.782 / 4 |
| (a) co-located | 2 | NONE | 789.893 | 790.124 | 790.124 | -0.231 | 0.569 / 5 | 0.800 / 6 |
| (a) co-located | 2 | REORDER_POINT | 1088.857 | 1092.373 | 1092.373 | -3.516 | 0.533 / 5 | 1.049 / 6 |
| (b) 1 hub | 0 | NONE | 770.832 | 770.832 | 770.832 | +0.000 | 0.000 / 2 | 0.000 / 2 |
| (b) 1 hub | 0 | REORDER_POINT | 943.952 | 943.952 | 943.952 | +0.000 | 1.120 / 8 | 1.120 / 8 |
| (b) 1 hub | 1 | NONE | 1001.742 | 1001.742 | 1001.742 | +0.000 | 0.000 / 1 | 0.000 / 1 |
| (b) 1 hub | 1 | REORDER_POINT | 1153.790 | 1153.790 | 1153.790 | +0.000 | 1.138 / 7 | 1.138 / 7 |
| (b) 1 hub | 2 | NONE | 818.496 | 818.496 | 818.496 | +0.000 | 0.000 / 2 | 0.000 / 2 |
| (b) 1 hub | 2 | REORDER_POINT | 1031.545 | 1031.545 | 1031.545 | +0.000 | 1.031 / 8 | 1.031 / 8 |
| (c) 2 hubs | 0 | NONE | 800.022 | 800.022 | 800.022 | +0.000 | 0.000 / 2 | 0.000 / 2 |
| (c) 2 hubs | 0 | REORDER_POINT | 973.142 | 973.142 | 973.142 | +0.000 | 1.120 / 8 | 1.120 / 8 |
| (c) 2 hubs | 1 | NONE | 1030.932 | 1030.932 | 1030.932 | +0.000 | 0.000 / 1 | 0.000 / 1 |
| (c) 2 hubs | 1 | REORDER_POINT | 1180.855 | 1180.855 | 1180.855 | +0.000 | 1.013 / 5 | 1.013 / 5 |
| (c) 2 hubs | 2 | NONE | 847.686 | 847.686 | 847.686 | +0.000 | 0.000 / 2 | 0.000 / 2 |
| (c) 2 hubs | 2 | REORDER_POINT | 1060.735 | 1060.735 | 1060.735 | +0.000 | 1.031 / 8 | 1.031 / 8 |

## Figures

All files are in `outputs/e3u/`; every figure referenced here exists (verified by listing).

- `fig_cost_by_layout.png` -- REGENERATED for this report (Agg): total cost by layout, two panels (written | relaxed), ILP free / ILP h = z = 0 / policy NONE / policy REORDER_POINT, bars = seed means with value labels, dots = seeds; the baseline bars use the recomputed same-policy rows. The original had a clipped y-axis label and plotted only the written baselines.
- `fig_gap_by_layout.png` -- NEW: corrected headline gap vs the NONE policy by layout, panels written | relaxed, ILP free vs h = z = 0.
- `fig_transfer_value.png` -- REGENERATED: left = value of transfers per layout (written vs relaxed) with open circles marking the upper bound implied by the TIME_LIMIT bound of the free run; right = cost of separation vs (a). Data unchanged (ILP-only).
- `fig_cost_components.png` (ILP cost components (27)-(32) per cell), `fig_in_transit.png` (m_t over t), `fig_full_stock_written_seed0.png`, `fig_full_stock_relaxed_seed0.png` (n_jLt per facility), `fig_grid_load_seed0.png` (charging load vs limit) -- EXISTING, drawn from ILP rows only (unaffected by the F1 correction), inspected: labelled axes with units, consistent with results.csv.

## Anomalies and checks

1. **Pre-fix relaxed baseline rows (F1).** 6 of the 18 relaxed baseline rows in `results.csv` (all co-located) are a reserve-0 policy; the pre-fix REORDER_POINT rows were 3.5-61.2 USD cheaper than the same policy with the written reserve (fewer charge steps, lower end stock). Consequence in the original RESULTS.md: the relaxed-target gap vs REORDER_POINT for (a) read 33.1 % instead of 36.5 %; gaps vs NONE moved by <= 0.03 pp. All corrected in T5/T6; old values kept in A1.
2. **`n_seeds` in the original RESULTS.md summary table counts SKIPPED_BUDGET rows** (shows 3 for every ILP cell); the solved counts are 2 (seeds 0-1) for most cells and 1 for (c) written h = z = 0 and both (c) relaxed cells. The `_fixed` script has the same `summary_table` and would reproduce this.
3. **Coverage.** 15 of 36 ILP runs were skipped by the 57 min wall budget: all 12 seed-2 runs and 3 of 4 (c) seed-1 runs. Every ILP cell therefore has n <= 2 and no CI can be given; the baseline CIs (n = 3) are wide (+/- 260-312 USD) because seed 1 and seed 2 drop 7 orders against 1 on seed 0.
4. **TIME_LIMIT.** The 4 separated-layout written-target transfers-free runs stopped at 300 s with gap 1.9-2.0 % (node counts 1-8). Their incumbents still use exactly one shuttle; the value of transfers under written targets is a lower bound (true value in [12.6, 25.9] on (b)/(c) seed 0, [0.6, 14.9] on (b) seed 1) and the written separation costs are upper bounds.
5. **MIPGap-level differences.** Differences of <= 0.07 USD between runs (default relative MIPGap 1e-4 on ~650 USD) are solver tolerance, not structure: (a) written seed 0 reports no_transfers 615.20 > transfers-free 615.15 although the free solution moves no battery; (c) relaxed seed 0 673.30 vs 673.27. The "value of transfers" of 0.03-0.05 USD in (a) and (c)-relaxed is therefore 0.
6. **Rejected MIP starts (expected).** 3/21: the written NONE policy schedule of the separated layouts reports (17) x2 + (18) (swap-only sites cannot recharge and hubs receive nothing), no NONE fallback variant was clean, so an unverified start was offered and ignored. All 18 REORDER_POINT / co-located starts and all 18 same-policy relaxed certificates were accepted.
7. **Policy reports (17)/(18) but does not enforce them**: every separated NONE run and co-located seed 1 end below the written targets, so under the written setting the baseline is compared with an ILP that pays for the recovery stock the policy skips; the written headline gaps are conservative in the ILP's disfavour. Under the relaxed setting both sides face the same constraints (the clean comparison).
8. **Mixed charging rules across layouts (F3)**: baseline C_elec is 0 in the separated NONE runs (nothing reaches the hubs) and 0.8-1.1 USD elsewhere; the baseline layout differences (832 -> 864 -> 893) are F_hub (29.19 per hub) plus 0.5-2.5 USD of travel/lateness, not a charging effect.
9. **Structurally unservable orders (F5)**: 1 order on every seed-0 and seed-1 instance (release + prep + handling beyond H), 0 on seed 2; both methods pay P = 30 for it, which dilutes every relative gap identically.
10. **Baseline stranded bikes**: the policy reports 1 stranded bike (no feasible repositioning at the end of the horizon, certified by a terminal arc) on every seed-0 instance (all three layouts, both transfer rules) and on no seed-1 / seed-2 instance; pruned-arc fallbacks 0 and suppressed late trips 0 everywhere, so the shared pruning did not bind the policy.
11. **Monotonicity checks pass**: relaxed optimum <= written optimum and transfers-free <= no-transfers on every solved pair (within MIPGap); evaluate.check, identity (24) and objective == cost hold on 21/21 solved ILP runs and 36/36 policy runs.

## Interpretation (with round-1 comparison)

1. At equal totals (9 spares, 6 chargers, one 8/6 kW grid group) co-location remains the cheapest layout on every solved seed, as in round 1, but the price of separation is now mostly the hub's fixed cost: +52 USD (b) and +82 USD (c) per 4 h window under the written targets, of which 29 / 58 USD is F_hub and about 23 USD is operations (one 22 USD shuttle plus the response-time cost of the longer swap detours), and under the relaxed targets the operational part collapses to 0.2-0.4 USD (round 1: 15-18 of 55-98 toy units).
2. The round-1 finding survives the move to USD costs, a 4 h window and 3 spares per site: the within-horizon replenishment value of transfers is zero in every layout (relaxed targets: 0.00 / 0.00 / 0.04 USD, all ILP runs with 0 shuttles and 7.5-9 swaps), because nine spares cover the 6-9 swaps the fleet needs in four hours even without any charging.
3. Whatever value transfers have under the written targets is again the recovery-target mechanism: with C_j = 0 at the swap sites and no transfers, (17) + (18) require 5 of the 9 spares to be full at H, which caps the fleet at 4 swaps (n_swaps = 4 on every written h = z = 0 separated run) and costs 2-3 extra dropped orders; one shuttle moving 2 batteries (C_reb 22 USD) recovers 1-3 of them, worth 0.6-12.6 USD net (lower bound; <= 26 USD from the 2 % bounds).
4. In USD the size of that effect is an order of magnitude smaller than round 1's ~255 toy units because P fell from 100 to 30 and the shuttle fee rose from 5 to 20: an extra served order is now worth 30 USD minus its response cost (18 $/h), so the ILP recovers only the orders a single shuttle can enable and otherwise prefers to drop them.
5. The ILP's advantage over the R2.3 policy is 24 % (a), 21 % (b) and 20 % (c) under the written targets and 24 / 24 / 16 % under the relaxed ones (round 1: 48 / 37 / 36 % with P = 100); on (a) the 195 USD mean difference is lateness 96 + unserved 60 + response 37 + travel 1 + electricity 0.3, so the gap is service quality (fewer late and dropped orders), not energy or distance, consistent with round 1 where 90 % of the gap was the drop penalty.
6. The relaxed-target control is now a clean comparison: after the F1 correction the policy's schedule is identical under both settings, its start is accepted by every relaxed model (18/18 certificates), and the written-vs-relaxed difference of the ILP (0.2-23 USD, largest in the separated layouts) measures exactly the price of the recovery targets; the correction itself changed only the co-located REORDER_POINT rows, shifting the relaxed gap vs REORDER_POINT on (a) from 33.1 % to 36.5 %.
7. The REORDER_POINT baseline rule is uniformly harmful under USD costs (+143 to +302 USD on every layout and seed, 7-14 shuttles with f_e = 20 each, zero change in unserved orders), whereas in round 1 it reduced the separated-layout cost by 115-220 toy units: a reorder-point trigger that was cheap at f_e = 5 and P = 100 is not worth running when a shuttle costs most of an order's penalty and the sites already hold 3 spares.
8. Battery-side constraints still do not bind: hub charging peaks at 1.33 kW and co-located sites at 3.33 kW against 6-8 kW, electricity is below 1 USD per window, the relaxed ILP buys at most 0.39 kWh, and stock-outs occur only where the ILP deliberately lets stock run to zero near the end (41-61 stock-out slots under relaxed targets, 0 at the reserved separated sites under written ones), so, as in round 1 and E4, the charging / grid / transfer machinery is correct but idle at this size.
9. Compared with round 1 the layout ranking, the zero replenishment value and the "transfers only serve the end targets" conclusion are unchanged; what changed is the scale of every monetary effect (gaps roughly halved, transfer value down 20x, separation penalty dominated by F_hub) and the sign of the REORDER_POINT baseline rule.
10. The main limitations are coverage and certification: seed 2 has no ILP solution at all, (c) has one seed for three of its four cells, the four written transfers-free separated runs are 2 % incumbents, and the baseline t-CIs span 260-312 USD because seed 0 drops 1 order and seeds 1-2 drop 7; a complete 3-seed run with a larger wall budget (or 8 h sensitivity) is needed before any of the per-layout differences can be given a confidence interval.
11. Modelling implication for the supervisor (as in round 1): rho and R_end are the only lever that gives transfers any value in this family; a periodic end condition (end stock >= initial stock) or a longer / rolling horizon is needed to observe genuine within-horizon replenishment.

## Files

- `outputs/e3u/RESULTS_final.md` (this report), `outputs/e3u/relaxed_baseline_recomputed.csv` (36 policy runs: written and relaxed copies, both rules, current package), `outputs/e3u/relaxed_start_certificates.csv` (18 fix-and-solve certificates), regenerated `fig_cost_by_layout.png`, `fig_transfer_value.png`, new `fig_gap_by_layout.png`; original `results.csv`, `RESULTS.md`, `run.log`, `wall_time.json`, `instances/` untouched.
