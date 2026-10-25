# X7 -- A7 RL comparator vs rule policies and the ILP (round 6: P 60, w 18, v 15 USD/h from b_i)

Families ['nyc4h_stress2', 'r5_stress4h'], test seeds `0:10`, training seeds `1000:1020`, PPO-clip 200000 steps per rider layer (r2, r5), ILP aggregated (O1), Threads 3, Seed 0, TimeLimit 300 s.

Headline = M1 relaxed control (rho = 0, R_end = 0); `total` = E2 (26), `end-adj` = (26) + C_end_adjust (M1); gap = 100 (policy - ilp_relaxed) / policy; differences are paired over seeds (end-adjusted, mean +- 95 % Student-t half-width). `best_rule` = per-seed minimum over rule_r2, rule_r5_range, rule_r5_transfer, rule_r5 (rule_r5_transfer only with services). `ilp_written` keeps (17)-(18); its `price_of_recovery` = ilp_written - ilp_relaxed.

## Training

| family | agent | status | steps | wall s | steps/s | return first 100 | last 100 |
|---|---|---|---|---|---|---|---|
| nyc4h_stress2 | ppo[r2] | TRAINED | 200704 | 544.0 | 369 | -123.98 | -114.71 |
| nyc4h_stress2 | ppo[r5] | TRAINED | 200704 | 488.7 | 411 | -132.14 | -99.97 |
| r5_stress4h | ppo[r2] | TRAINED | 200704 | 1602.7 | 125 | -180.31 | -197.42 |
| r5_stress4h | ppo[r5] | TRAINED | 200704 | 1412.9 | 142 | -183.22 | -191.29 |

## nyc4h_stress2

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 28.15 +- 4.72 | 28.10 +- 4.72 | - | 38.69 +- 65.81 |
| rule_r5_range | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | 31.26 +- 4.60 | 31.21 +- 4.60 | - | 87.65 +- 75.68 |
| rule_r5 | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | 31.26 +- 4.60 | 31.21 +- 4.60 | - | 87.65 +- 75.68 |
| rule_r5_selfish | 10 | 1063.03 +- 101.09 | 1063.35 +- 101.08 | 0.32 +- 0.08 | 0.839 +- 0.036 | 28.72 +- 4.33 | 28.68 +- 4.33 | - | 45.68 +- 61.61 |
| ilp_relaxed | 10 | 751.09 +- 38.84 | 751.81 +- 38.83 | 0.72 +- 0.08 | 0.933 +- 0.023 | - | - | - | -265.86 +- 55.42 |
| rl_ppo[r2] | 10 | 1054.88 +- 106.74 | 1055.24 +- 106.71 | 0.37 +- 0.07 | 0.844 +- 0.049 | 28.05 +- 4.73 | 28.01 +- 4.73 | -1.11 +- 4.09 | 37.57 +- 66.30 |
| replay[r2] | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 28.15 +- 4.72 | 28.10 +- 4.72 | 0.00 +- 0 | 38.69 +- 65.81 |
| heuristic_none[r2] | 10 | 1524.98 +- 65.92 | 1525.79 +- 65.88 | 0.81 +- 0.05 | 0.536 +- 0.025 | 50.75 +- 1.56 | 50.72 +- 1.56 | 469.43 +- 90.37 | 508.12 +- 55.97 |
| heuristic_asap[r2] | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | 28.15 +- 4.72 | 28.10 +- 4.72 | 0.00 +- 0 | 38.69 +- 65.81 |
| rl_ppo[r5] | 10 | 1109.13 +- 122.76 | 1109.45 +- 122.78 | 0.33 +- 0.07 | 0.808 +- 0.043 | 31.44 +- 4.77 | 31.39 +- 4.78 | 4.14 +- 8.76 | 91.79 +- 78.37 |
| replay[r5] | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | 31.26 +- 4.60 | 31.21 +- 4.60 | 0.00 +- 0 | 87.65 +- 75.68 |
| heuristic_none[r5] | 10 | 1690.37 +- 48.73 | 1691.01 +- 48.70 | 0.64 +- 0.05 | 0.400 +- 0.027 | 55.55 +- 2.11 | 55.53 +- 2.12 | 585.70 +- 98.32 | 673.34 +- 80.92 |
| heuristic_asap[r5] | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | 31.26 +- 4.60 | 31.21 +- 4.60 | 0.00 +- 0 | 87.65 +- 75.68 |
| best_rule | 10 | 1017.40 +- 80.67 | 1017.67 +- 80.65 | 0.27 +- 0.07 | 0.853 +- 0.028 | 25.80 +- 3.58 | 25.75 +- 3.58 | - | 0.00 +- 0 |

ilp_relaxed: OPTIMAL on 10 of 10 seeds, max MIP gap 0.0001.

best_rule picked: {"rule_r2": 7, "rule_r5_range": 3}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

## r5_stress4h

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1688.25 +- 174.98 | 1689.63 +- 174.95 | 1.38 +- 0.10 | 0.742 +- 0.061 | 42.22 +- 3.52 | 42.16 +- 3.52 | - | 75.51 +- 80.19 |
| rule_r5_range | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.39 +- 2.41 | 41.31 +- 2.42 | - | 40.19 +- 39.65 |
| rule_r5 | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.39 +- 2.41 | 41.31 +- 2.42 | - | 40.19 +- 39.65 |
| rule_r5_selfish | 10 | 1633.83 +- 174.03 | 1635.25 +- 174.02 | 1.42 +- 0.09 | 0.758 +- 0.053 | 40.22 +- 3.99 | 40.15 +- 4.00 | - | 21.13 +- 62.76 |
| ilp_relaxed | 10 | 967.65 +- 75.63 | 969.52 +- 75.57 | 1.87 +- 0.12 | 0.944 +- 0.029 | - | - | - | -644.60 +- 85.12 |
| rl_ppo[r2] | 10 | 1728.32 +- 174.73 | 1729.86 +- 174.69 | 1.54 +- 0.11 | 0.706 +- 0.064 | 43.53 +- 3.81 | 43.47 +- 3.81 | 40.24 +- 27.48 | 115.74 +- 76.70 |
| replay[r2] | 10 | 1688.25 +- 174.98 | 1689.63 +- 174.95 | 1.38 +- 0.10 | 0.742 +- 0.061 | 42.22 +- 3.52 | 42.16 +- 3.52 | 0.00 +- 0 | 75.51 +- 80.19 |
| heuristic_none[r2] | 10 | 1808.22 +- 149.16 | 1810.15 +- 149.12 | 1.93 +- 0.08 | 0.652 +- 0.061 | 46.32 +- 2.87 | 46.28 +- 2.87 | 120.53 +- 62.66 | 196.03 +- 79.22 |
| heuristic_asap[r2] | 10 | 1676.40 +- 187.56 | 1677.60 +- 187.57 | 1.20 +- 0.13 | 0.748 +- 0.063 | 41.62 +- 4.20 | 41.55 +- 4.21 | -12.02 +- 18.11 | 63.48 +- 86.79 |
| rl_ppo[r5] | 10 | 1802.20 +- 112.06 | 1803.61 +- 111.98 | 1.41 +- 0.13 | 0.590 +- 0.052 | 46.31 +- 2.49 | 46.25 +- 2.49 | 149.30 +- 43.24 | 189.48 +- 75.85 |
| replay[r5] | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | 41.39 +- 2.41 | 41.31 +- 2.42 | 0.00 +- 0 | 40.19 +- 39.65 |
| heuristic_none[r5] | 10 | 1806.35 +- 114.53 | 1808.04 +- 114.49 | 1.69 +- 0.09 | 0.585 +- 0.055 | 46.42 +- 2.55 | 46.37 +- 2.54 | 153.73 +- 41.77 | 193.92 +- 73.65 |
| heuristic_asap[r5] | 10 | 1626.04 +- 119.76 | 1627.11 +- 119.76 | 1.07 +- 0.13 | 0.756 +- 0.037 | 40.42 +- 2.38 | 40.34 +- 2.39 | -27.20 +- 26.28 | 12.99 +- 44.65 |
| best_rule | 10 | 1612.87 +- 138.89 | 1614.12 +- 138.86 | 1.25 +- 0.12 | 0.758 +- 0.053 | 39.78 +- 2.83 | 39.71 +- 2.84 | - | 0.00 +- 0 |

ilp_relaxed: OPTIMAL on 5 of 10 seeds, max MIP gap 0.0112.

best_rule picked: {"rule_r2": 4, "rule_r5_range": 6}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

Notes: the ILP has perfect information (offline reference); on nyc4h_stress2 its pruning (PRUNING_NYC, targets = facilities) binds only the ILP, so its optimum is an upper bound on the written optimum. The RL agent controls only the station layer (charging; transfers where services exist) on top of the named rider layer; `replay[r]` is the rule station layer inside the environment and must equal `rule_r`.

## Lateness (seed means; lateness.csv has the t 95 % half-widths)

| family | method | n | n_late | n_late_over_30min | n_late_over_60min | mean_lateness_min | max_lateness_min | served_share |
|---|---|---|---|---|---|---|---|---|
| nyc4h_stress2 | best_rule | 10 | 16.60 | 1.80 | 0 | 9.76 | 30.50 | 0.85 |
| nyc4h_stress2 | heuristic_asap[r2] | 10 | 17.40 | 2.40 | 0 | 11.13 | 33 | 0.84 |
| nyc4h_stress2 | heuristic_asap[r5] | 10 | 16.90 | 2.50 | 0 | 11.67 | 34 | 0.81 |
| nyc4h_stress2 | heuristic_none[r2] | 10 | 10.10 | 4.50 | 0.10 | 16.31 | 55 | 0.54 |
| nyc4h_stress2 | heuristic_none[r5] | 10 | 7.90 | 3.20 | 0.20 | 15.37 | 52 | 0.40 |
| nyc4h_stress2 | ilp_relaxed | 10 | 7.90 | 0.10 | 0 | 2.45 | 22 | 0.93 |
| nyc4h_stress2 | replay[r2] | 10 | 17.40 | 2.40 | 0 | 11.13 | 33 | 0.84 |
| nyc4h_stress2 | replay[r5] | 10 | 16.90 | 2.50 | 0 | 11.67 | 34 | 0.81 |
| nyc4h_stress2 | rl_ppo[r2] | 10 | 17.60 | 2.50 | 0 | 11.29 | 33.50 | 0.84 |
| nyc4h_stress2 | rl_ppo[r5] | 10 | 16.80 | 2.50 | 0 | 11.76 | 34 | 0.81 |
| nyc4h_stress2 | rule_r2 | 10 | 17.40 | 2.40 | 0 | 11.13 | 33 | 0.84 |
| nyc4h_stress2 | rule_r5 | 10 | 16.90 | 2.50 | 0 | 11.67 | 34 | 0.81 |
| nyc4h_stress2 | rule_r5_range | 10 | 16.90 | 2.50 | 0 | 11.67 | 34 | 0.81 |
| nyc4h_stress2 | rule_r5_selfish | 10 | 17.60 | 2.60 | 0 | 11.40 | 33 | 0.84 |
| r5_stress4h | best_rule | 10 | 21.80 | 6.70 | 0.10 | 14.63 | 51 | 0.76 |
| r5_stress4h | heuristic_asap[r2] | 10 | 22.90 | 7.50 | 0.30 | 17.24 | 52 | 0.75 |
| r5_stress4h | heuristic_asap[r5] | 10 | 21.60 | 7.30 | 0.30 | 15.06 | 54.50 | 0.76 |
| r5_stress4h | heuristic_none[r2] | 10 | 19.30 | 5.80 | 0 | 15.76 | 51.50 | 0.65 |
| r5_stress4h | heuristic_none[r5] | 10 | 13.60 | 1.60 | 0 | 8.20 | 37 | 0.59 |
| r5_stress4h | ilp_relaxed | 10 | 10.90 | 1.10 | 0 | 3.47 | 37.50 | 0.94 |
| r5_stress4h | replay[r2] | 10 | 23 | 7.60 | 0.20 | 17.24 | 52.50 | 0.74 |
| r5_stress4h | replay[r5] | 10 | 20.60 | 6.70 | 0.20 | 14.50 | 53 | 0.73 |
| r5_stress4h | rl_ppo[r2] | 10 | 21.30 | 6.80 | 0 | 16.28 | 49.50 | 0.71 |
| r5_stress4h | rl_ppo[r5] | 10 | 13.80 | 1.70 | 0 | 8.44 | 39.50 | 0.59 |
| r5_stress4h | rule_r2 | 10 | 23 | 7.60 | 0.20 | 17.24 | 52.50 | 0.74 |
| r5_stress4h | rule_r5 | 10 | 20.60 | 6.70 | 0.20 | 14.50 | 53 | 0.73 |
| r5_stress4h | rule_r5_range | 10 | 20.60 | 6.70 | 0.20 | 14.50 | 53 | 0.73 |
| r5_stress4h | rule_r5_selfish | 10 | 22.50 | 6.70 | 0.20 | 15.87 | 52.50 | 0.76 |

