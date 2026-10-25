# X7 -- A7 RL comparator vs rule policies and the ILP (round 5)

Families ['nyc4h_stress2', 'r5_stress4h'], test seeds `0:10`, training seeds `1000:1020`, PPO-clip 200000 steps per rider layer (r2, r5), ILP aggregated (O1), Threads 3, Seed 0, TimeLimit 120 s.

Headline = M1 relaxed control (rho = 0, R_end = 0); `total` = E2 (26), `end-adj` = (26) + C_end_adjust (M1); gap = 100 (policy - ilp_relaxed) / policy; differences are paired over seeds (end-adjusted, mean +- 95 % Student-t half-width). `best_rule` = per-seed minimum over rule_r2, rule_r5_range, rule_r5_transfer, rule_r5 (rule_r5_transfer only with services). `ilp_written` keeps (17)-(18); its `price_of_recovery` = ilp_written - ilp_relaxed.

## Training

| family | agent | status | steps | wall s | steps/s | return first 100 | last 100 |
|---|---|---|---|---|---|---|---|
| nyc4h_stress2 | ppo[r2] | TRAINED | 200704 | 489.2 | 410 | -112.37 | -106.57 |
| nyc4h_stress2 | ppo[r5] | TRAINED | 200704 | 464.6 | 432 | -117.00 | -89.48 |
| r5_stress4h | ppo[r2] | TRAINED | 200704 | 1624.8 | 124 | -142.80 | -158.47 |
| r5_stress4h | ppo[r5] | TRAINED | 200704 | 1561.6 | 129 | -127.70 | -128.05 |

## nyc4h_stress2

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1003.02 +- 134.33 | 1003.31 +- 134.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 31.74 +- 7.20 | 31.68 +- 7.21 | - | 38.94 +- 64.10 |
| rule_r5_range | 10 | 1018.82 +- 151.36 | 1019.09 +- 151.37 | 0.27 +- 0.06 | 0.811 +- 0.042 | 32.31 +- 8.29 | 32.26 +- 8.30 | - | 54.72 +- 54.58 |
| rule_r5 | 10 | 1018.82 +- 151.36 | 1019.09 +- 151.37 | 0.27 +- 0.06 | 0.811 +- 0.042 | 32.31 +- 8.29 | 32.26 +- 8.30 | - | 54.72 +- 54.58 |
| rule_r5_selfish | 10 | 1009.08 +- 135.60 | 1009.40 +- 135.59 | 0.32 +- 0.08 | 0.839 +- 0.036 | 32.10 +- 7.35 | 32.05 +- 7.36 | - | 45.03 +- 62.65 |
| ilp_relaxed | 10 | 667.83 +- 13.33 | 668.54 +- 13.31 | 0.71 +- 0.05 | 0.858 +- 0.022 | - | - | - | -295.83 +- 121.27 |
| rl_ppo[r2] | 10 | 1024.92 +- 121.32 | 1025.38 +- 121.30 | 0.46 +- 0.06 | 0.806 +- 0.074 | 33.55 +- 6.26 | 33.51 +- 6.26 | 22.07 +- 25.89 | 61.01 +- 65.38 |
| replay[r2] | 10 | 1003.02 +- 134.33 | 1003.31 +- 134.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 31.74 +- 7.20 | 31.68 +- 7.21 | 0.00 +- 0 | 38.94 +- 64.10 |
| heuristic_none[r2] | 10 | 1133.00 +- 73.75 | 1133.81 +- 73.72 | 0.81 +- 0.05 | 0.536 +- 0.025 | 40.71 +- 3.16 | 40.69 +- 3.16 | 130.51 +- 81.56 | 169.44 +- 86.60 |
| heuristic_asap[r2] | 10 | 1003.02 +- 134.33 | 1003.31 +- 134.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 31.74 +- 7.20 | 31.68 +- 7.21 | 0.00 +- 0 | 38.94 +- 64.10 |
| rl_ppo[r5] | 10 | 1010.24 +- 149.27 | 1010.71 +- 149.28 | 0.47 +- 0.05 | 0.756 +- 0.060 | 31.81 +- 8.11 | 31.77 +- 8.12 | -8.38 +- 18.87 | 46.34 +- 47.92 |
| replay[r5] | 10 | 1018.82 +- 151.36 | 1019.09 +- 151.37 | 0.27 +- 0.06 | 0.811 +- 0.042 | 32.31 +- 8.29 | 32.26 +- 8.30 | 0.00 +- 0 | 54.72 +- 54.58 |
| heuristic_none[r5] | 10 | 1119.37 +- 49.58 | 1120.01 +- 49.56 | 0.64 +- 0.05 | 0.400 +- 0.027 | 40.18 +- 2.30 | 40.15 +- 2.30 | 100.92 +- 133.39 | 155.64 +- 115.06 |
| heuristic_asap[r5] | 10 | 1018.82 +- 151.36 | 1019.09 +- 151.37 | 0.27 +- 0.06 | 0.811 +- 0.042 | 32.31 +- 8.29 | 32.26 +- 8.30 | 0.00 +- 0 | 54.72 +- 54.58 |
| ilp_written | 10 | 668.67 +- 13.47 | 668.87 +- 13.48 | 0.20 +- 0.04 | 0.856 +- 0.024 | - | - | - | -295.50 +- 121.29 |
| best_rule | 10 | 964.10 +- 130.65 | 964.37 +- 130.65 | 0.27 +- 0.07 | 0.853 +- 0.028 | 29.02 +- 7.26 | 28.97 +- 7.27 | - | 0.00 +- 0 |

Price of recovery (ilp_written - ilp_relaxed): total 0.84 +- 0.54, end-adjusted 0.33 +- 0.54 (both ILPs certified optimal on 10 of 10 seeds).

ilp_relaxed: OPTIMAL on 10 of 10 seeds, max MIP gap 0.

ilp_written: OPTIMAL on 10 of 10 seeds, max MIP gap 0.0001.

best_rule picked: {"rule_r2": 7, "rule_r5_range": 3}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

## r5_stress4h

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1525.37 +- 137.90 | 1526.75 +- 137.87 | 1.38 +- 0.10 | 0.742 +- 0.061 | 44.39 +- 3.61 | 44.32 +- 3.62 | - | 85.67 +- 61.63 |
| rule_r5_range | 10 | 1445.38 +- 96.47 | 1446.54 +- 96.48 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.64 +- 2.39 | 41.56 +- 2.40 | - | 5.45 +- 8.23 |
| rule_r5 | 10 | 1445.38 +- 96.47 | 1446.54 +- 96.48 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.64 +- 2.39 | 41.56 +- 2.40 | - | 5.45 +- 8.23 |
| rule_r5_selfish | 10 | 1482.36 +- 147.96 | 1483.77 +- 147.93 | 1.42 +- 0.09 | 0.758 +- 0.053 | 42.57 +- 4.58 | 42.50 +- 4.58 | - | 42.69 +- 71.70 |
| ilp_relaxed | 10 | 839.79 +- 31.20 | 841.63 +- 31.16 | 1.83 +- 0.06 | 0.854 +- 0.038 | - | - | - | -599.46 +- 74.98 |
| rl_ppo[r2] | 10 | 1475.10 +- 84.31 | 1476.98 +- 84.30 | 1.88 +- 0.08 | 0.652 +- 0.061 | 42.90 +- 2.15 | 42.85 +- 2.15 | -49.77 +- 61.42 | 35.90 +- 55.52 |
| replay[r2] | 10 | 1525.37 +- 137.90 | 1526.75 +- 137.87 | 1.38 +- 0.10 | 0.742 +- 0.061 | 44.39 +- 3.61 | 44.32 +- 3.62 | 0.00 +- 0 | 85.67 +- 61.63 |
| heuristic_none[r2] | 10 | 1475.05 +- 84.32 | 1476.98 +- 84.30 | 1.93 +- 0.08 | 0.652 +- 0.061 | 42.90 +- 2.15 | 42.85 +- 2.15 | -49.77 +- 61.42 | 35.90 +- 55.52 |
| heuristic_asap[r2] | 10 | 1523.57 +- 150.16 | 1524.78 +- 150.18 | 1.20 +- 0.13 | 0.748 +- 0.063 | 44.14 +- 4.42 | 44.06 +- 4.43 | -1.97 +- 19.36 | 83.70 +- 69.99 |
| rl_ppo[r5] | 10 | 1289.78 +- 65.32 | 1291.40 +- 65.33 | 1.62 +- 0.11 | 0.585 +- 0.055 | 34.75 +- 2.33 | 34.69 +- 2.33 | -155.14 +- 52.90 | -149.69 +- 58.13 |
| replay[r5] | 10 | 1445.38 +- 96.47 | 1446.54 +- 96.48 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.64 +- 2.39 | 41.56 +- 2.40 | 0.00 +- 0 | 5.45 +- 8.23 |
| heuristic_none[r5] | 10 | 1289.67 +- 65.27 | 1291.36 +- 65.29 | 1.69 +- 0.09 | 0.585 +- 0.055 | 34.74 +- 2.33 | 34.68 +- 2.33 | -155.17 +- 52.91 | -149.72 +- 58.14 |
| heuristic_asap[r5] | 10 | 1464.21 +- 107.22 | 1465.28 +- 107.22 | 1.07 +- 0.13 | 0.756 +- 0.037 | 42.32 +- 2.66 | 42.24 +- 2.67 | 18.75 +- 21.84 | 24.20 +- 20.09 |
| ilp_written | 10 | 845.20 +- 32.20 | 846.36 +- 32.19 | 1.16 +- 0.07 | 0.844 +- 0.039 | - | - | - | -594.72 +- 75.74 |
| best_rule | 10 | 1439.89 +- 100.85 | 1441.08 +- 100.82 | 1.19 +- 0.11 | 0.746 +- 0.055 | 41.38 +- 2.61 | 41.30 +- 2.61 | - | 0.00 +- 0 |

Price of recovery (ilp_written - ilp_relaxed): total 5.41 +- 4.97, end-adjusted 4.74 +- 4.98 (both ILPs certified optimal on 1 of 10 seeds).

ilp_relaxed: OPTIMAL on 3 of 10 seeds, max MIP gap 0.0164.

ilp_written: OPTIMAL on 1 of 10 seeds, max MIP gap 0.0252.

best_rule picked: {"rule_r2": 2, "rule_r5_range": 8}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

Notes: the ILP has perfect information (offline reference); on nyc4h_stress2 its pruning (PRUNING_NYC, targets = facilities) binds only the ILP, so its optimum is an upper bound on the written optimum. The RL agent controls only the station layer (charging; transfers where services exist) on top of the named rider layer; `replay[r]` is the rule station layer inside the environment and must equal `rule_r`.
