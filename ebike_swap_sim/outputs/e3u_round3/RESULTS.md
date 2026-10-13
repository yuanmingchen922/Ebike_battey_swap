# E3u round 3 -- provenance (English stub)

The automatic `--analyse` step of `experiments/e3u_round3.py` drew the figures and then crashed in `e3u_transfers_usd_fixed.collect_anomalies` (`int(NaN)` on the reused round-2 ILP rows, which carry no `n_unservable`), so no RESULTS.md was written by the run. The full report with tables, 95 % t-CIs, solver statistics, anomalies and interpretation is `RESULTS_final.md` in this directory (built from `records.jsonl`).

Rows: ILP reused from round 2 (OPTIMAL) 17, ILP solved in round 3 43 (Threads 3, Seed 0, TimeLimit 300 s / 600 s for separated-written-free cells); policy rows recomputed in round 3 46; ILP statuses {'OPTIMAL': 50, 'TIME_LIMIT': 10}; seeds [0, 1, 2, 3, 4]; wall 150.1 min; baseline mismatches vs stored round-2 written rows: [].

Re-solved round-2 TIME_LIMIT cells (600 s) against their round-2 incumbents:

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
