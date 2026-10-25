# R6 rolling horizon under the new prices: foresight vs online coordination, final report

Date: 2026-10-18. Stage `rolling` of `experiments/r6_penalty.py`. New prices: unserved penalty P = 60 USD, response
price w = 18 USD/h from release, lateness price v = 15 USD/h from the promise. Old prices (round 5): P = 30, w = 18,
v = 36. Everything else as in round 5 (`r5_x3_rolling`): rolling horizon W = 24 slots, commit k = 6 slots, lookahead
lambda = 10 min, 8 windows, aggregated window ILP, window TimeLimit 60 s, relaxed final targets, Gurobi Threads 3 /
Seed 0, eBaaS energy calibration.

All numbers below were recomputed from the records by `figs/make_rolling_final.py` (no solves; machine-readable output
in `figs/rolling_final_tables.json` and `figs/rolling_final_per_instance.csv`). Costs are end-adjusted
(`total + C_end_adjust`), USD per 4 h window, relaxed end targets. Best rule = per-instance minimum over r2, M2 and
M2+M3 of the end-adjusted cost. Intervals are exact Student-t 95 % CIs over seeds (n - 1 dof), written
`mean [lo, hi]`. Every difference is paired by seed. "+a/-b" counts seeds with a positive / negative difference.

Decomposition per instance (as in round 5):
`best rule - offline` (offline gap) = `(rolling - offline)` (foresight) + `(best rule - rolling)` (online coordination).
Share of the offline gap kept online = `(best rule - rolling) / (best rule - offline)`, reported as the mean of
per-seed ratios, the ratio of means and the median.

**Offline references.** usd4h: the relaxed offline ILP of `r6_penalty/headline` (usd4h x1, new prices; 10/10
OPTIMAL, MIP gap <= 8.8e-5, TimeLimit 300 s, MIP start = written-target optimum, accepted). The `psweep` P 60 copies
of these rows are identical. stress4h (code `r5_stress4h`): the relaxed offline ILP of `r6_penalty/psweep` (P 60,
v 15 cell; TimeLimit 300 s, not shortened by the wall budget, MIP start = M2 schedule, accepted): seeds 0 and 4
OPTIMAL, seeds 1, 2, 3 TIME_LIMIT. Rules come from the relaxed rule rows of the same stages. The demand hash is
identical across rolling, offline and rules on all 15 instances, and identical to the round-5 instances of the same
seeds. The round-5 comparison uses `outputs/r5_x3_rolling/records.jsonl` (rolling lambda 10, relaxed offline, rules),
which reproduces every round-5 number used here exactly.

## Problems and anomalies

1. **Terminal fallback (main caveat, unchanged from round 5).** In 12 of the 15 online runs (usd4h 8/10, stress4h
   4/5; round 5 at lambda 10: 13/15) all four windows that reach the horizon (t0 = 24, 30, 36, 42) were infeasible
   with the relaxed targets and were re-solved with a penalised dummy terminal arc. The stitched schedules then break
   the terminal certificate (9) for 1.20 [0.54, 1.86] bikes per run on usd4h (0-3) and 1.00 [0.12, 1.88] on stress4h
   (0-2). `C_dummy_terminal` is 0 in every record, so the evaluated cost does not price this. The offline ILP
   enforces (9); the best rule breaks (9) on 0/10 usd4h and 1/5 stress4h seeds (r2, seed 0). The online costs are
   therefore too favourable: foresight is understated and online coordination and the share kept online are
   overstated (upper bounds) by an amount this run cannot measure. The bias points the same way as the main result
   below (the share kept online falls), so it cannot explain that fall. The three runs without fallback (usd4h seeds
   1 and 4, stress4h seed 4) keep 0.74, 0.76 and 0.60 of the gap, in the upper half; with n = 3 this neither shows
   nor rules out a fallback bias.
2. **usd4h seed 0: rolling loses to the best rule.** Rolling costs 699.14 USD against 599.96 for r2 (-99.19 USD,
   -16.5 % of the best rule), so the share kept is -1.51. On this seed r2 serves all 36 orders and the offline gap is
   small (65.78 USD, 11.0 %); rolling drops 2 orders (+120 USD), which outweighs its lower response cost (-25.5 USD). In round 5 the same
   seed kept only 0.05. This one seed drives the usd4h mean of ratios (0.29) and its wide interval [-0.19, 0.77]. The
   ratio of means (0.42) and the median (0.54) are more robust summaries. Without seed 0 (post hoc, sensitivity only)
   the mean of ratios is 0.49 [0.30, 0.68] (n = 9; old prices 0.70 [0.55, 0.85]).
3. **Three of five stress4h offline references are TIME_LIMIT** (seeds 1, 2, 3; MIP gaps 1.12 %, 0.54 %, 0.46 %,
   i.e. 11.57, 5.51, 4.42 USD between incumbent and bound). In round 5 only seed 2 was (0.09 %). Foresight is then a
   difference with an upper bound. Using the Gurobi bound instead of the incumbent (raw-cost basis) moves the stress4h
   share kept from 0.527 to 0.523 and foresight from 300.7 to 305.0 USD, which does not change any conclusion. As a
   consistency check, the round-5 offline schedule priced at the new prices is never cheaper than the round-6 offline
   incumbent (difference 0.00 to 88.35 USD, all 15 instances >= 0).
4. **The rolling policy does not always adapt well to the new prices.** All schedules are feasible for both price
   sets, so the round-5 online schedule can be priced at the new prices exactly (unserved = P x count, lateness = v x
   late hours). On average the round-6 rolling schedule is cheaper than the round-5 one priced at the new prices
   (usd4h 62.81 USD [-33.19, 158.80], 6/10 seeds; stress4h 88.14 USD [-23.11, 199.39], 5/5), but on usd4h seeds 0,
   3, 6 and 9 the round-5 online schedule would have been cheaper (by 1.64, 17.75, 165.77 and 35.68 USD). On seed 6
   the round-6 run drops 6 orders (5 flagged energy-refused) against 4 in round 5. The measured foresight is therefore
   partly a property of this myopic rolling policy, not only of missing information.
5. **Rolling barely charges.** Electricity is 0.01 USD (usd4h) and 0.24 USD (stress4h) per window for rolling
   against 0.68 / 1.18 USD for the best rule, with 5.4 / 7.0 swaps against 8.8 / 9.4 (best rule) and 8.3 / 10.0
   (offline). Most rolling drops are flagged energy-refused by the A3 proxy (an idle bike in place lacked the energy):
   2.0 of 2.4 per window on usd4h and 8.4 of 8.8 on stress4h, against 0.0 of 0.4 and 0.6 of 2.2 for the offline ILP.
   The end-of-window energy deficit is priced only through `C_end_adjust` (1.3-2.0 USD for every method).
6. **`check_ok` is False on all 15 rolling rows.** The stitched schedule is checked against (9) (item 1) and the
   written end targets (17)-(18), which the relaxed run does not impose (reported only). The hard families and
   identity (24) pass on every row (`hard_ok`, `identity_24_ok`). The same holds in round 5.
7. **The auto-generated `RESULTS.md` is numerically correct but incomplete.** Every number in it matches the
   recomputation (for example share kept 0.289 / 0.526, value of information 137.09 / 300.78 USD). Its column `ci95`
   is the half-width, and its anomaly list ("none") misses items 1-3 and 6.
8. **Rule schedules are identical in both rounds.** Pricing the round-5 r2, M2 and M2+M3 rows at the new prices
   reproduces the round-6 rows to 2e-13 USD (M2+M3 = M2 on these instances, which have no services). Changes in the
   best rule between rounds come only from the prices; the argmin changes on usd4h (r2 on 6 -> 8 seeds, M2 on 4 -> 2)
   and not on stress4h (r2 1, M2 4).
9. **Small n on stress4h.** With n = 5 the smallest attainable two-sided Wilcoxon p is 0.0625; the t-test p-values
   are reported for stress4h.
10. **Scope.** Round 6 re-ran lambda 10 with relaxed targets only. Lambda 0 / 20, the forecast battery plan and the
    written-target (price of recovery) runs of round 5 were not repeated, so the lookahead curve and the online price
    of recovery are not re-tested under the new prices. Round-5 records have no late-order counts; their lateness is
    reported in order-minutes (lateness USD / v x 60, exact under (31)).

## Coverage

| item | count / status |
|---|---|
| rolling records (`rolling/records.jsonl`) | 15 records, 15 keys (usd4h seeds 0-9, stress4h seeds 0-4), all `ROLLING`; 0 ERROR, 0 SKIPPED_BUDGET; no duplicate keys |
| windows | 8 per run, 120 in total, all OPTIMAL; max window MIP gap 9.8e-5; max window run time 42.9 s (limit 60 s) |
| fallback windows | 48 of 120 (4 per run in 12 runs; t0 = 24, 30, 36, 42) |
| prices in the rows | P 60, w 18, v 15 in every row; library price check on 105-144 delivery arcs per run |
| run time per rolling run | usd4h 45.3 s [40.8, 49.7]; stress4h 92.1 s [66.8, 117.3] |
| stage wall time | 969.6 s (16.2 min) of a 45 min budget |
| offline reference, usd4h | `headline`, 10/10 OPTIMAL (gap <= 8.8e-5, 25-145 s) |
| offline reference, stress4h | `psweep`, OPTIMAL 2 (seeds 0, 4; gap <= 3.9e-5), TIME_LIMIT 3 (seeds 1-3; gaps 1.12 / 0.54 / 0.46 %; 300 s, not budget-cut) |
| rules | r2, M2, M2+M3 relaxed rows: 30 (usd4h) + 15 (stress4h), all POLICY |
| round-5 counterpart | `r5_x3_rolling`: rolling lambda 10 relaxed 15 ROLLING; offline relaxed 14 OPTIMAL + 1 TIME_LIMIT (stress4h seed 2, 0.09 %); rules POLICY |
| skipped cells | none (lambda 0 / 20, forecast and written targets are not part of the R6 rolling stage) |

## Answer

### Summary

The offline gap does not change with the prices (usd4h 27.34 % [21.69, 32.99] vs 28.28 % under the old prices;
stress4h 40.00 % [34.56, 45.43] vs 39.96 %), but less of it survives online. At lambda 10 the rolling ILP keeps
0.42 of the gap on usd4h (ratio of means; mean of ratios 0.29 [-0.19, 0.77], median 0.54, n = 10) and 0.53 on
stress4h (mean of ratios 0.53 [0.34, 0.71], n = 5). Under the old prices it kept 0.73 and 0.79. The paired fall is
-0.25 [-0.35, -0.15] on stress4h (5/5 seeds, t p = 0.002) and -0.35 [-0.71, 0.02] on usd4h (8/10 seeds, t p = 0.058,
Wilcoxon p = 0.037). Foresight (rolling - offline) about doubles, from 8.33 % to 16.35 % [10.00, 22.69] of the
best-rule cost on usd4h and from 8.70 % to 18.88 % [11.36, 26.41] on stress4h. Online coordination (best rule -
rolling) falls from 19.94 % to 11.00 % [2.40, 19.59] and from 31.26 % to 21.11 % [13.00, 29.23]. Rolling still beats
the best rule on 14 of 15 instances (all but usd4h seed 0).

The admission effect of round 5 is gone. Under the new prices rolling serves as many orders as the best rule on usd4h
(93.3 % vs 92.5 %, paired +0.8 pp [-3.1, 4.8], n = 10, 5 up / 4 down / 1 tie, t p = 0.65) and more on stress4h
(81.7 % vs 75.4 %, +6.3 pp [0.8, 11.7], n = 5, 4 up / 0 down / 1 tie, t p = 0.034). Status: every rolling run is
ROLLING with all 8 windows OPTIMAL (window MIP gap <= 9.8e-5), with the unpriced terminal fallback in 4 of 8 windows on
8/10 usd4h and 4/5 stress4h seeds (anomaly 1); the rules are POLICY. Under the old prices the paired served-share
difference could not be told apart from zero: -6.4 pp [-13.0, 0.2] on usd4h (2 up / 7 down / 1 tie, t p = 0.057) and
-2.5 pp [-11.2, 6.2] on stress4h (2 up / 2 down / 1 tie, t p = 0.47, median 0; the mean comes almost entirely from
seed 0 at -14.6 pp), as round 5 itself reported (`r5_x3_rolling`, anomaly 6). The data therefore do not show a sign
reversal in served share. The robust change is within seed: the rule schedules are identical in both rounds, and
rolling's own served share rose by 7.8 pp [1.0, 14.6] on usd4h (7 up / 1 down / 2 ties, t p = 0.029) and by 8.8 pp
[4.5, 13.0] on stress4h (5/5 seeds, t p = 0.005), so its gap to the best rule rose by 7.2 pp [0.5, 14.0] and 8.8 pp
[4.5, 13.0] (T3). The unserved part of the online coordination value moved from negative point estimates whose
intervals include zero (-69.0 USD [-140.6, 2.6] and -36.0 USD [-160.7, 88.7]) to 18.0 USD [-68.0, 104.0] and 180.0 USD
[22.0, 338.0]; only the stress4h new-price value is clearly positive. Rolling now accepts moderate lateness: 92.5 [39.2, 145.8] and 146.0
[86.1, 205.9] order-minutes per window, against 9.5 and 9.0 before, with no order more than 60 min late (maximum 50
and 45 min). What remains is that rolling drops more orders than the offline ILP (5.6 pp and 13.7 pp), and these drops
are now most of the value of foresight.

### T1 Cost per method (USD per 4 h window, end-adjusted, relaxed targets; mean [95 % t-CI])

Absolute costs are not comparable between rounds (the prices differ); the shares in T2 are.

| quantity | usd4h old (n = 10) | usd4h new (n = 10) | stress4h old (n = 5) | stress4h new (n = 5) |
|---|---|---|---|---|
| best rule | 830.91 [721.74, 940.07] | 838.50 [753.33, 923.68] | 1387.36 [1173.65, 1601.07] | 1581.76 [1289.40, 1874.12] |
| rolling, lambda 10 | 648.64 [617.30, 679.97] | 738.51 [672.23, 804.78] | 944.07 [879.95, 1008.20] | 1242.78 [1015.28, 1470.29] |
| offline ILP | 582.05 [563.65, 600.45] | 601.41 [572.70, 630.13] | 826.10 [771.60, 880.60] | 942.01 [819.82, 1064.19] |

### T2 Decomposition of the offline gap (paired per seed)

| quantity | usd4h old (n = 10) | usd4h new (n = 10) | stress4h old (n = 5) | stress4h new (n = 5) |
|---|---|---|---|---|
| offline gap (best rule - offline), USD | 248.86 [155.71, 342.01] | 237.09 [172.78, 301.41] | 561.26 [388.10, 734.41] | 639.76 [453.95, 825.56] |
| offline gap, % of best rule | 28.28 [20.91, 35.64] | 27.34 [21.69, 32.99] | 39.96 [33.58, 46.35] | 40.00 [34.56, 45.43] |
| foresight (rolling - offline), USD | 66.59 [43.25, 89.92] | 137.09 [81.49, 192.70] | 117.97 [73.13, 162.82] | 300.78 [152.31, 449.24] |
| foresight, % of best rule | 8.33 [5.21, 11.46] | 16.35 [10.00, 22.69] | 8.70 [4.72, 12.69] | 18.88 [11.36, 26.41] |
| foresight, % of offline | 11.43 [7.49, 15.37] | 22.76 [13.63, 31.89] | 14.35 [8.71, 19.99] | 31.75 [18.15, 45.34] |
| online coordination (best rule - rolling), USD | 182.27 [80.50, 284.04] | 100.00 [31.13, 168.87] | 443.29 [250.53, 636.04] | 338.98 [178.31, 499.64] |
| online coordination, % of best rule | 19.94 [10.76, 29.12] | 11.00 [2.40, 19.59] | 31.26 [21.82, 40.70] | 21.11 [13.00, 29.23] |
| share of the gap kept online, mean of ratios | 0.64 [0.44, 0.83] | 0.29 [-0.19, 0.77] | 0.77 [0.64, 0.90] | 0.53 [0.34, 0.71] |
| share kept online, ratio of means | 0.732 | 0.422 | 0.790 | 0.530 |
| share kept online, median | 0.731 | 0.538 | 0.831 | 0.570 |
| foresight share of the gap, ratio of means | 0.268 | 0.578 | 0.210 | 0.470 |
| seeds with rolling < best rule | 10/10 | 9/10 | 5/5 | 5/5 |
| seeds with foresight > online coordination | 3/10 | 4/10 | 0/5 | 2/5 |

Online coordination is significant on both families under the new prices (usd4h t p = 0.010, Wilcoxon p = 0.020,
9/10 seeds; stress4h t p = 0.004, 5/5 seeds).

### T3 Change from old to new prices on the same instances (new - old, paired by seed)

| quantity | usd4h (n = 10) | stress4h (n = 5) |
|---|---|---|
| offline gap, pp of best rule | -0.93 [-5.79, 3.92]; +5/-5; t p = 0.674 | 0.03 [-3.65, 3.72]; +2/-3; t p = 0.981 |
| foresight, pp of best rule | 8.02 [0.90, 15.13]; +8/-2; t p = 0.031, W p = 0.027 | 10.18 [4.85, 15.51]; +5/-0; t p = 0.006 |
| online coordination, pp of best rule | -8.95 [-17.72, -0.18]; +2/-8; t p = 0.046, W p = 0.049 | -10.15 [-14.60, -5.69]; +0/-5; t p = 0.003 |
| share kept online (mean of ratios) | -0.347 [-0.709, 0.015]; +2/-8; t p = 0.058, W p = 0.037 | -0.248 [-0.346, -0.149]; +0/-5; t p = 0.002 |
| served share, rolling, pp | 7.8 [1.0, 14.6]; +7/-1; t p = 0.029 | 8.8 [4.5, 13.0]; +5/-0; t p = 0.005 |
| served share, offline, pp | 3.6 [1.1, 6.1]; +7/-0; t p = 0.009 | 7.9 [5.8, 10.1]; +5/-0; t p = 0.001 |
| served share, best rule, pp | 0.6 [-0.7, 1.8]; +1/-0 (argmin switch, seed 2) | 0.0 (identical) |
| served gap rolling - best rule, pp | 7.2 [0.5, 14.0]; +7/-1; t p = 0.039 | 8.8 [4.5, 13.0]; +5/-0; t p = 0.005 |
| unserved orders per window, rolling | -2.80 [-5.25, -0.35]; +1/-7; t p = 0.029 | -4.20 [-6.24, -2.16]; +0/-5; t p = 0.005 |
| lateness, rolling, order-min per window | 83.0 [29.3, 136.7]; +9/-1; t p = 0.007 | 137.0 [82.4, 191.6]; +5/-0; t p = 0.002 |

### T4 Service and lateness (mean [95 % t-CI] per 4 h window)

| quantity | usd4h old | usd4h new | stress4h old | stress4h new |
|---|---|---|---|---|
| served share, best rule, % | 91.9 [88.3, 95.6] | 92.5 [89.4, 95.6] | 75.4 [64.8, 86.0] | 75.4 [64.8, 86.0] |
| served share, rolling, % | 85.6 [80.0, 91.2] | 93.3 [89.1, 97.5] | 72.9 [66.9, 79.0] | 81.7 [72.8, 90.5] |
| served share, offline, % | 95.3 [92.6, 97.9] | 98.9 [97.9, 99.9] | 87.5 [82.3, 92.7] | 95.4 [90.8, 100.0] |
| rolling - best rule, pp (paired) | -6.4 [-13.0, 0.2]; +2/-7, 1 tie; t p = 0.057 | 0.8 [-3.1, 4.8]; +5/-4, 1 tie; t p = 0.65 | -2.5 [-11.2, 6.2]; +2/-2, 1 tie; t p = 0.47 | 6.3 [0.8, 11.7]; +4/-0, 1 tie; t p = 0.034 |
| offline - rolling, pp (paired) | 9.7 [5.6, 13.8] | 5.6 [2.1, 9.1] | 14.6 [9.7, 19.4] | 13.7 [7.5, 20.0] |
| unserved orders: best rule / rolling / offline | 2.9 / 5.2 / 1.7 | 2.7 / 2.4 / 0.4 | 11.8 / 13.0 / 6.0 | 11.8 / 8.8 / 2.2 |
| lateness, best rule, order-min | 209.5 [98.9, 320.1] | 215.0 [107.8, 322.2] | 456.0 [277.8, 634.2] | 456.0 [277.8, 634.2] |
| lateness, rolling, order-min | 9.5 [3.8, 15.2] | 92.5 [39.2, 145.8] | 9.0 [0.9, 17.1] | 146.0 [86.1, 205.9] |
| lateness, offline, order-min | 3.0 [0.5, 5.5] | 33.0 [6.5, 59.5] | 2.0 [-1.4, 5.4] | 151.0 [89.2, 212.8] |
| mean lateness per served order, rolling, min | 0.31 [0.11, 0.50] | 2.72 [1.20, 4.24] | 0.26 [0.02, 0.51] | 3.78 [2.14, 5.41] |
| orders > 30 min late: best rule / rolling | n/a | 1.2 / 0.6 | n/a | 5.0 / 0.8 |
| orders > 60 min late: best rule / rolling / offline | n/a | 0 / 0 / 0 | n/a | 0.2 / 0 / 0 |
| max lateness over seeds: best rule / rolling / offline, min | n/a | 40 / 50 / 35 | n/a | 65 / 45 / 45 |
| energy-refused unserved orders (proxy): best rule / rolling / offline | 0.3 / 4.7 / 0.4 | 0.1 / 2.0 / 0.0 | 7.6 / 12.8 / 4.4 | 7.6 / 8.4 / 0.6 |
| swaps: best rule / rolling / offline | 9.2 / 5.7 / 8.3 | 8.8 / 5.4 / 8.3 | 9.4 / 5.6 / 9.6 | 9.4 / 7.0 / 10.0 |

The rule schedules are identical in both rounds; the usd4h best-rule changes (lateness 209.5 -> 215.0, served share
+0.6 pp) come only from the argmin switch on seeds 0, 2, 4 (M2 -> r2) and 9 (r2 -> M2). Round-5 records carry no late-order counts (n/a).

### T5 Where the online advantage and the foresight value come from (USD per window, paired components)

| component | usd4h old | usd4h new | stress4h old | stress4h new |
|---|---|---|---|---|
| coordination: unserved (best rule - rolling) | -69.00 [-140.57, 2.57] | 18.00 [-67.96, 103.96] | -36.00 [-160.66, 88.66] | 180.00 [21.96, 338.04] |
| coordination: response | 127.95 [64.01, 191.89] | 49.35 [15.01, 83.69] | 207.00 [138.78, 275.22] | 78.60 [17.71, 139.49] |
| coordination: lateness | 120.00 [53.23, 186.77] | 30.62 [13.24, 48.01] | 268.20 [163.78, 372.62] | 77.50 [36.04, 118.96] |
| coordination: other (set-up, travel, electricity, rebalancing, end adjustment) | 3.32 [1.80, 4.84] | 2.02 [0.48, 3.57] | 4.09 [2.71, 5.47] | 2.88 [1.80, 3.95] |
| foresight: unserved (rolling - offline) | 105.00 [60.61, 149.39] | 120.00 [44.29, 195.71] | 210.00 [140.31, 279.69] | 396.00 [216.58, 575.42] |
| foresight: response | -40.35 [-65.16, -15.54] | 3.45 [-25.00, 31.90] | -92.70 [-123.23, -62.17] | -90.00 [-127.04, -52.96] |
| foresight: lateness | 3.90 [-0.02, 7.82] | 14.88 [6.54, 23.21] | 4.20 [-0.80, 9.20] | -1.25 [-13.67, 11.17] |
| foresight: other | -1.96 [-2.71, -1.21] | -1.23 [-1.93, -0.53] | -3.53 [-4.90, -2.16] | -3.97 [-6.32, -1.62] |

Under the new prices the unserved component is 0.88 of foresight on usd4h (120.0 of 137.1 USD) and more than all of
it on stress4h (396.0 of 300.8 USD, partly offset by -90.0 USD of response: the offline ILP serves more orders, some
with longer responses).

## Comparison with round 5 (old prices) on the same instances

Same 15 instances (demand hash identical), same rolling protocol, same rules (identical schedules), offline ILP
re-solved at the new prices.

| quantity | usd4h old -> new | stress4h old -> new |
|---|---|---|
| offline gap, % of best rule | 28.28 -> 27.34 (no change) | 39.96 -> 40.00 (no change) |
| foresight, % of best rule | 8.33 -> 16.35 (+8.02 [0.90, 15.13]) | 8.70 -> 18.88 (+10.18 [4.85, 15.51]) |
| online coordination, % of best rule | 19.94 -> 11.00 (-8.95 [-17.72, -0.18]) | 31.26 -> 21.11 (-10.15 [-14.60, -5.69]) |
| share kept online, ratio of means | 0.73 -> 0.42 | 0.79 -> 0.53 |
| share kept online, mean of ratios | 0.64 -> 0.29 (-0.35 [-0.71, 0.02]) | 0.77 -> 0.53 (-0.25 [-0.35, -0.15]) |
| served share, rolling - best rule, pp (paired) | -6.4 [-13.0, 0.2] (not significant) -> +0.8 [-3.1, 4.8] (not significant); change +7.2 [0.5, 14.0] | -2.5 [-11.2, 6.2] (not significant) -> +6.3 [0.8, 11.7]; change +8.8 [4.5, 13.0] |
| served share, rolling, pp (new - old) | +7.8 [1.0, 14.6], +7/-1 | +8.8 [4.5, 13.0], +5/-0 |
| lateness, rolling, order-min | 9.5 -> 92.5 | 9.0 -> 146.0 |
| unserved part of online coordination, USD | -69.0 [-140.6, 2.6] -> +18.0 [-68.0, 104.0] | -36.0 [-160.7, 88.7] -> +180.0 [22.0, 338.0] |
| runs with terminal fallback | 8/10 -> 8/10 | 5/5 -> 4/5 |

Round-5 artefact (e) (part of the rolling-horizon gain was order admission) is resolved in the sense that the online
policy no longer wins by dropping orders that the rules serve. The round-5 served-share deficit itself was not
significant (round 5, anomaly 6); what changed significantly between the price sets is that rolling serves more orders
on the same seeds while the rule schedules stay the same. The round-5 statement "between about two thirds and
four fifths of the offline gap is still there online" does not hold under the new prices; about one half does (0.42
and 0.53 as ratio of means).

## Interpretation

**Shown by these records.**

- The repricing leaves the offline gap unchanged (27 % and 40 % of the best-rule cost) but moves part of it from
  online coordination to foresight. At lambda 10 the rolling ILP keeps about half of the gap (ratio of means 0.42 on
  usd4h and 0.53 on stress4h), against about three quarters under the old prices. The fall is clear on stress4h (5/5
  seeds) and on usd4h in the ratio of means and the median; the usd4h mean of ratios is dominated by seed 0 and its
  interval includes zero.
- Online coordination is still worth 11.0 % [2.4, 19.6] (usd4h) and 21.1 % [13.0, 29.2] (stress4h) of the best-rule
  cost, and rolling beats the best rule on 14 of 15 instances. As in round 5, coordination is worth more on the
  energy-stressed family.
- The admission effect is gone: rolling serves as many orders as the best rule (usd4h, +0.8 pp [-3.1, 4.8]) or more
  (stress4h, +6.3 pp [0.8, 11.7], 4 up / 0 down / 1 tie). This is not a reversal of a significant old-price deficit
  (old prices -6.4 pp [-13.0, 0.2] and -2.5 pp [-11.2, 6.2]); it is a rise in rolling's own served share on the same
  seeds (+7.8 and +8.8 pp) with unchanged rule schedules. The online advantage now comes from response (49 / 79 USD), lateness (31 / 78 USD) and, on stress4h, fewer drops
  (180 USD). Rolling now accepts moderate lateness (no order more than 60 min late) instead of dropping orders.
- Foresight under the new prices consists mainly of orders that the rolling ILP drops and the offline ILP serves
  (2.0 more per window on usd4h, 6.6 more on stress4h).

**Suggested, not shown.**

- Under the old prices a myopic planner could correct missing foresight cheaply by dropping a late order for 30 USD;
  round 5 then counted that saving as coordination. At P 60 this recourse is expensive, so the cost of not knowing the
  future shows up as foresight. The records are consistent with this (the unserved coordination components move from
  negative point estimates with intervals including zero to non-negative ones, clearly positive on stress4h, T5), but
  no run isolates the mechanism.
- The extra drops look energy-related: most rolling drops are flagged energy-refused (2.0 of 2.4 and 8.4 of 8.8), and
  rolling swaps less than the offline ILP (5.4 vs 8.3 and 7.0 vs 10.0) and almost never charges. A planner without
  foresight seems to under-provision battery energy for later orders. A terminal energy reserve or a battery plan
  might recover part of the foresight value; the forecast battery plan of round 5 added nothing under the old prices
  and was not re-tested here.
- The true share kept online is probably lower than reported, because the unpriced terminal fallback (12/15 runs)
  makes the online costs too favourable. Part of the measured foresight reflects the rolling heuristic rather than
  missing information (anomaly 4), so a better online policy could keep more of the gap.

For the manuscript: under the calibrated prices, say that about half of the offline coordination gap survives online
at lambda 10 (not two thirds to four fifths), that the remainder is mostly orders the online planner cannot serve
for lack of energy foresight, and that the online advantage over the rules no longer depends on dropping orders. The
terminal-fallback caveat still applies, and the lookahead curve has not been re-run at the new prices.

## Figures

All under `rolling/figs/`, made by `make_rolling_final.py` (records only), PDF and 300-dpi PNG, colour-blind-safe
blue/orange palette, old prices also hatched or drawn with a different marker.

- `fig_rolling_decomposition.pdf` / `.png` (7.2 x 2.75 in). Suggested caption: *Offline gap (best rule - offline
  ILP), foresight (rolling - offline) and online coordination (best rule - rolling) as a share of the best-rule cost,
  end-adjusted, relaxed end targets, rolling horizon with 10 min lookahead. Hatched: old prices (P 30 USD, v 36
  USD/h); solid: new prices (P 60 USD, v 15 USD/h); same instances. Bars: means; error bars: exact 95 % t-CIs over
  seeds; dots: seeds. (a) usd4h, 10 seeds; (b) stress4h, 5 seeds. In 12 of 15 new-price runs the last windows use an
  unpriced terminal fallback, so foresight is understated and online coordination overstated.*
- `fig_rolling_service_lateness.pdf` / `.png` (7.2 x 4.4 in). Suggested caption: *Orders served (a, b) and total
  lateness past the promise in order-minutes per 4 h window (c, d) for the best rule, the rolling horizon (10 min
  lookahead) and the offline ILP, under old (circles) and new (squares) prices. Markers: means with exact 95 %
  t-CIs; grey dots: seeds. Under the new prices the rolling horizon serves as many orders as the best rule (usd4h)
  or more (stress4h) and accepts moderate lateness instead of dropping orders. Paired by seed, rolling - best rule is
  +0.8 pp [-3.1, 4.8] (usd4h, n = 10) and +6.3 pp [0.8, 11.7] (stress4h, n = 5) under the new prices and -6.4 pp
  [-13.0, 0.2] and -2.5 pp [-11.2, 6.2] under the old prices (neither different from zero); the rule markers are the
  same schedules in both rounds.* (Caption text only; the figure itself shows unpaired means and is unchanged.)
- `fig_rolling_share_kept.pdf` / `.png` (7.2 x 2.6 in). Suggested caption: *Share of the offline gap kept online,
  (best rule - rolling) / (best rule - offline), per seed under old and new prices (grey lines pair the same
  instance). Diamonds: mean of per-seed ratios with exact 95 % t-CI; orange bars: ratio of means. The usd4h mean of
  ratios is pulled down by seed 0, where the rolling horizon loses to the best rule.*

## Appendix A1: per instance, new prices (end-adjusted USD; "kept old" = the same seed under the old prices)

| family | seed | best rule (name) | offline (status, MIP gap) | rolling | gap % | foresight % | coordination % | kept | kept old | served best rule / rolling / offline (%) | unserved B / R / O | lateness B / R / O (order-min) | fallback windows new / old | (9) bikes, rolling |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 0 | 599.96 (r2) | 534.18 (OPTIMAL, 0.00 %) | 699.14 | 10.96 | 27.50 | -16.53 | -1.508 | 0.049 | 100.0 / 94.4 / 100.0 | 0 / 2 / 0 | 40 / 65 / 0 | 4 / 4 | 2 |
| usd4h | 1 | 886.04 (r2) | 592.47 (OPTIMAL, 0.01 %) | 667.49 | 33.13 | 8.47 | 24.67 | 0.744 | 0.759 | 88.9 / 97.2 / 100.0 | 4 / 1 / 0 | 185 / 55 / 30 | 0 / 4 | 0 |
| usd4h | 2 | 824.24 (r2) | 618.13 (OPTIMAL, 0.00 %) | 781.29 | 25.01 | 19.80 | 5.21 | 0.208 | 0.350 | 88.9 / 86.1 / 97.2 | 4 / 5 / 1 | 120 / 5 / 25 | 4 / 4 | 1 |
| usd4h | 3 | 902.18 (r2) | 614.48 (OPTIMAL, 0.00 %) | 845.57 | 31.89 | 25.61 | 6.27 | 0.197 | 0.769 | 88.9 / 86.1 / 97.2 | 4 / 5 / 1 | 215 / 85 / 10 | 4 / 4 | 1 |
| usd4h | 4 | 716.97 (r2) | 545.80 (OPTIMAL, 0.00 %) | 587.71 | 23.87 | 5.85 | 18.03 | 0.755 | 0.702 | 91.7 / 97.2 / 100.0 | 3 / 1 / 0 | 30 / 0 / 5 | 0 / 0 | 0 |
| usd4h | 5 | 875.41 (M2) | 634.99 (OPTIMAL, 0.00 %) | 729.31 | 27.46 | 10.77 | 16.69 | 0.608 | 0.652 | 91.7 / 97.2 / 97.2 | 3 / 1 / 1 | 235 / 155 / 45 | 4 / 4 | 1 |
| usd4h | 6 | 956.87 (r2) | 617.76 (OPTIMAL, 0.01 %) | 907.80 | 35.44 | 30.31 | 5.13 | 0.145 | 0.913 | 91.7 / 83.3 / 97.2 | 3 / 6 / 1 | 395 / 100 / 30 | 4 / 4 | 3 |
| usd4h | 7 | 749.38 (r2) | 610.67 (OPTIMAL, 0.00 %) | 676.03 | 18.51 | 8.72 | 9.79 | 0.529 | 0.438 | 100.0 / 100.0 / 100.0 | 0 / 0 / 0 | 230 / 140 / 55 | 4 / 4 | 1 |
| usd4h | 8 | 994.81 (r2) | 667.31 (OPTIMAL, 0.00 %) | 776.07 | 32.92 | 10.93 | 21.99 | 0.668 | 0.922 | 94.4 / 97.2 / 100.0 | 2 / 1 / 0 | 520 / 250 / 125 | 4 / 4 | 2 |
| usd4h | 9 | 879.18 (M2) | 578.31 (OPTIMAL, 0.00 %) | 714.64 | 34.22 | 15.51 | 18.71 | 0.547 | 0.810 | 88.9 / 94.4 / 100.0 | 4 / 2 / 0 | 180 / 70 / 5 | 4 / 0 | 1 |
| stress4h | 0 | 1183.98 (r2) | 787.82 (OPTIMAL, 0.00 %) | 1005.22 | 33.46 | 18.36 | 15.10 | 0.451 | 0.640 | 89.6 / 89.6 / 100.0 | 5 / 5 / 0 | 290 / 70 / 85 | 4 / 4 | 1 |
| stress4h | 1 | 1684.78 (M2) | 1034.02 (TIME_LIMIT, 1.12 %) | 1231.16 | 38.63 | 11.70 | 26.92 | 0.697 | 0.865 | 72.9 / 83.3 / 91.7 | 13 / 8 / 4 | 535 / 190 / 165 | 4 / 4 | 1 |
| stress4h | 2 | 1730.79 (M2) | 1015.58 (TIME_LIMIT, 0.54 %) | 1505.73 | 41.32 | 28.32 | 13.00 | 0.315 | 0.682 | 66.7 / 70.8 / 91.7 | 16 / 14 / 4 | 390 / 160 / 115 | 4 / 4 | 2 |
| stress4h | 3 | 1754.85 (M2) | 958.82 (TIME_LIMIT, 0.46 %) | 1301.02 | 45.36 | 19.50 | 25.86 | 0.570 | 0.851 | 72.9 / 79.2 / 95.8 | 13 / 10 / 2 | 660 / 130 / 185 | 4 / 4 | 1 |
| stress4h | 4 | 1554.41 (M2) | 913.79 (OPTIMAL, 0.00 %) | 1170.79 | 41.21 | 16.53 | 24.68 | 0.599 | 0.831 | 75.0 / 85.4 / 97.9 | 12 / 7 / 1 | 405 / 180 / 205 | 0 / 4 | 0 |

Column key: gap % = 100 (best rule - offline) / best rule; foresight % and coordination % are shares of the best-rule
cost; kept = (best rule - rolling) / (best rule - offline); B / R / O = best rule / rolling / offline; fallback
windows = windows re-solved with the dummy terminal arc (of 8); (9) bikes = bikes without a terminal certificate in
the stitched rolling schedule (unpriced).

## Appendix A2: checks run on the records

- Cost identities on every rolling row: `total = C_setup + C_elec + C_travel + C_orders + C_reb` and
  `total_end_adjusted = total + C_end_adjust` (differences 0); `unserved = 60 x n_unserved`.
- Rule schedules: round-5 rows priced at the new prices equal the round-6 rows (max |difference| 2.3e-13 USD).
- Offline: the round-5 offline schedule priced at the new prices is >= the round-6 offline incumbent on all 15
  instances (raw ILP objective).
- Round-5 values used here reproduce `r5_x3_rolling/RESULTS_final.md` (for example 648.64 / 944.07 USD rolling,
  share kept 0.64 / 0.77 and 0.732 / 0.790).
- Auto-generated `RESULTS.md` / `summary.csv` / `per_instance.csv`: all reported means and half-widths agree with the
  recomputation.

## Verification corrections (R6)

Recomputed from the records by `figs/verify_c3_served_share.py` (records only, no solves). Sources: rolling rows
`rolling/records.jsonl`; new-price rules `headline/records.jsonl` (usd4h) and `psweep/records.jsonl` (stress4h, calib
P60_w18_v15, relaxed, mult 1); old prices `r5_x3_rolling/records.jsonl` (rolling relaxed lambda 10, baseline_r2 /
r5_range / r5). Best rule = per-seed argmin of end-adjusted cost. The demand hash matches across all four sources on
every seed. Status: rolling ROLLING, 8/8 windows OPTIMAL on every run in both rounds (window MIP gap <= 9.8e-5),
terminal fallback in 4 of 8 windows on stress4h seeds 0-3 (new) and 0-4 (old), usd4h 8/10 in both rounds; rules POLICY.

**C3.** Claim: "On stress4h under the new prices, rolling serves 6.3 pp [0.8, 11.7] more orders than the best rule
(4 seeds up, 0 down); under the old prices it served 2.5 pp fewer."

- Verdicts: refuter 1 refuted, refuter 2 refuted. Corrector: refuted; both refuters are right.
- Recomputed (stress4h, n = 5, seeds 0-4). New prices, rolling - best rule per seed: 0.00, +10.42, +4.17, +6.25,
  +10.42 pp; mean +6.25 [0.76, 11.74], t p = 0.034, 4 up / 0 down / 1 tie; 81.7 % vs 75.4 %. Old prices: -14.58,
  +2.08, -2.08, 0.00, +2.08 pp; mean -2.50 [-11.16, 6.16], t p = 0.47, 2 up / 2 down / 1 tie, median 0. Best rule
  (r2 on seed 0, M2 = M2+M3 on seeds 1-4) and its served shares are identical in both rounds. Change new - old in
  rolling - best rule = change in rolling's own served share: +8.75 [4.50, 13.00], t p = 0.005, 5/5 seeds.
- Why refuted: every number reproduces, but the old-price clause gave a non-significant mean (CI spans zero, seeds
  split 2/2, carried by seed 0 at -14.6 pp) without its interval next to a significant new-price value, which reads as
  a sign reversal the data do not support. Round 5 had itself called this difference not significant. The claim also
  omitted n, the tie and the solve status.
- Same issue in the same sentence for usd4h (not separately refuted, corrected for consistency): old prices -6.4 pp
  [-13.0, 0.2], t p = 0.057, 2 up / 7 down / 1 tie; new prices +0.8 pp [-3.1, 4.8], t p = 0.65, 5 up / 4 down / 1 tie
  (the claim's "5 up / 4 down" omitted the tie on seed 7). Rolling's own served share rose by 7.8 pp [1.0, 14.6]
  (+7/-1, 2 ties).
- What changed: (1) Summary, admission paragraph: added n, ties, t p and solve status; replaced "Under the old prices
  it served fewer (-6.4 pp and -2.5 pp)" by the old-price CIs and seed counts, stated that they do not differ from
  zero, and named the within-seed rise of rolling's served share (+7.8 / +8.8 pp; gap to the best rule +7.2 / +8.8 pp)
  as the robust change. The adjacent unserved-component sentence ("turned from negative ... to non-negative") now
  gives the old-price CIs (-69.0 [-140.6, 2.6], -36.0 [-160.7, 88.7] USD), which include zero. (2) T4: seed counts,
  ties and t p added to the paired served-share row. (3) Comparison table: CIs and "not significant" markers on the
  served-share and unserved-component rows, plus a row for the change in rolling's own served share. (4) Text after the
  comparison table and the third "Shown by these records" bullet: no reversal claimed; the change is a rise in rolling's
  served share on the same seeds. (5) "Suggested, not shown": "the unserved components flip sign" replaced by the
  qualified statement. (6) Caption of `fig_rolling_service_lateness`: paired differences with CIs added. The figure
  itself (unpaired means and CIs per method) is correct and was not regenerated. No other table entry, figure or
  conclusion changes; the new-price result (+6.3 pp [0.8, 11.7] on stress4h) stands.
