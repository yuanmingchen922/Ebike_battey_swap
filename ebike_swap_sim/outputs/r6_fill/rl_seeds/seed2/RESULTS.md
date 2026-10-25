# X7 -- A7 RL comparator vs rule policies and the ILP (round 5)

Families ['nyc4h_stress2', 'r5_stress4h'], test seeds `0:10`, training seeds `1000:1020`, PPO-clip 200000 steps per rider layer (r2, r5), ILP aggregated (O1), Threads 3, Seed 0, TimeLimit 300 s.

Headline = M1 relaxed control (rho = 0, R_end = 0); `total` = E2 (26), `end-adj` = (26) + C_end_adjust (M1); gap = 100 (policy - ilp_relaxed) / policy; differences are paired over seeds (end-adjusted, mean +- 95 % Student-t half-width). `best_rule` = per-seed minimum over rule_r2, rule_r5_range, rule_r5_transfer, rule_r5 (rule_r5_transfer only with services). `ilp_written` keeps (17)-(18); its `price_of_recovery` = ilp_written - ilp_relaxed.

## Training

| family | agent | status | steps | wall s | steps/s | return first 100 | last 100 |
|---|---|---|---|---|---|---|---|
| nyc4h_stress2 | ppo[r2] | TRAINED | 200704 | 461.2 | 435 | -128.55 | -113.99 |
| nyc4h_stress2 | ppo[r5] | TRAINED | 200704 | 462.2 | 434 | -128.25 | -105.59 |
| r5_stress4h | ppo[r2] | TRAINED | 200704 | 1322.2 | 152 | -186.45 | -190.98 |
| r5_stress4h | ppo[r5] | TRAINED | 200704 | 1364.4 | 147 | -181.65 | -186.08 |

## nyc4h_stress2

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | - | - | - | 38.69 +- 65.81 |
| rule_r5_range | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | - | - | - | 87.65 +- 75.68 |
| rule_r5 | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | - | - | - | 87.65 +- 75.68 |
| rule_r5_selfish | 10 | 1063.03 +- 101.09 | 1063.35 +- 101.08 | 0.32 +- 0.08 | 0.839 +- 0.036 | - | - | - | 45.68 +- 61.61 |
| rl_ppo[r2] | 10 | 1065.19 +- 98.57 | 1065.58 +- 98.55 | 0.39 +- 0.09 | 0.836 +- 0.043 | - | - | 9.22 +- 13.97 | 47.91 +- 64.20 |
| replay[r2] | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | - | - | 0.00 +- 0 | 38.69 +- 65.81 |
| heuristic_none[r2] | 10 | 1524.98 +- 65.92 | 1525.79 +- 65.88 | 0.81 +- 0.05 | 0.536 +- 0.025 | - | - | 469.43 +- 90.37 | 508.12 +- 55.97 |
| heuristic_asap[r2] | 10 | 1056.07 +- 105.34 | 1056.36 +- 105.32 | 0.29 +- 0.08 | 0.842 +- 0.046 | - | - | 0.00 +- 0 | 38.69 +- 65.81 |
| rl_ppo[r5] | 10 | 1115.10 +- 122.01 | 1115.54 +- 121.96 | 0.44 +- 0.10 | 0.808 +- 0.043 | - | - | 10.23 +- 32.36 | 97.87 +- 75.00 |
| replay[r5] | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | - | - | 0.00 +- 0 | 87.65 +- 75.68 |
| heuristic_none[r5] | 10 | 1690.37 +- 48.73 | 1691.01 +- 48.70 | 0.64 +- 0.05 | 0.400 +- 0.027 | - | - | 585.70 +- 98.32 | 673.34 +- 80.92 |
| heuristic_asap[r5] | 10 | 1105.04 +- 118.11 | 1105.32 +- 118.11 | 0.27 +- 0.06 | 0.811 +- 0.042 | - | - | 0.00 +- 0 | 87.65 +- 75.68 |
| best_rule | 10 | 1017.40 +- 80.67 | 1017.67 +- 80.65 | 0.27 +- 0.07 | 0.853 +- 0.028 | - | - | - | 0.00 +- 0 |

best_rule picked: {"rule_r2": 7, "rule_r5_range": 3}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

## r5_stress4h

| method | n | total | end-adj | C_end_adjust | served | gap % (total) | gap % (end-adj) | diff vs own rule | diff vs best_rule |
|---|---|---|---|---|---|---|---|---|---|
| rule_r2 | 10 | 1688.25 +- 174.98 | 1689.63 +- 174.95 | 1.38 +- 0.10 | 0.742 +- 0.061 | - | - | - | 75.51 +- 80.19 |
| rule_r5_range | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | - | - | - | 40.19 +- 39.65 |
| rule_r5 | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | - | - | - | 40.19 +- 39.65 |
| rule_r5_selfish | 10 | 1633.83 +- 174.03 | 1635.25 +- 174.02 | 1.42 +- 0.09 | 0.758 +- 0.053 | - | - | - | 21.13 +- 62.76 |
| rl_ppo[r2] | 10 | 1730.17 +- 178.28 | 1731.66 +- 178.31 | 1.49 +- 0.09 | 0.706 +- 0.068 | - | - | 42.03 +- 32.46 | 117.54 +- 79.86 |
| replay[r2] | 10 | 1688.25 +- 174.98 | 1689.63 +- 174.95 | 1.38 +- 0.10 | 0.742 +- 0.061 | - | - | 0.00 +- 0 | 75.51 +- 80.19 |
| heuristic_none[r2] | 10 | 1808.22 +- 149.16 | 1810.15 +- 149.12 | 1.93 +- 0.08 | 0.652 +- 0.061 | - | - | 120.53 +- 62.66 | 196.03 +- 79.22 |
| heuristic_asap[r2] | 10 | 1676.40 +- 187.56 | 1677.60 +- 187.57 | 1.20 +- 0.13 | 0.748 +- 0.063 | - | - | -12.02 +- 18.11 | 63.48 +- 86.79 |
| rl_ppo[r5] | 10 | 1803.24 +- 111.40 | 1804.83 +- 111.30 | 1.60 +- 0.15 | 0.590 +- 0.050 | - | - | 150.52 +- 42.44 | 190.71 +- 75.01 |
| replay[r5] | 10 | 1653.15 +- 124.49 | 1654.31 +- 124.49 | 1.16 +- 0.10 | 0.733 +- 0.044 | - | - | 0.00 +- 0 | 40.19 +- 39.65 |
| heuristic_none[r5] | 10 | 1806.35 +- 114.53 | 1808.04 +- 114.49 | 1.69 +- 0.09 | 0.585 +- 0.055 | - | - | 153.73 +- 41.77 | 193.92 +- 73.65 |
| heuristic_asap[r5] | 10 | 1626.04 +- 119.76 | 1627.11 +- 119.76 | 1.07 +- 0.13 | 0.756 +- 0.037 | - | - | -27.20 +- 26.28 | 12.99 +- 44.65 |
| best_rule | 10 | 1612.87 +- 138.89 | 1614.12 +- 138.86 | 1.25 +- 0.12 | 0.758 +- 0.053 | - | - | - | 0.00 +- 0 |

best_rule picked: {"rule_r2": 4, "rule_r5_range": 6}.

Replay parity with the rule of the same rider layer: replay[r2] True, replay[r5] True.

Notes: the ILP has perfect information (offline reference); on nyc4h_stress2 its pruning (PRUNING_NYC, targets = facilities) binds only the ILP, so its optimum is an upper bound on the written optimum. The RL agent controls only the station layer (charging; transfers where services exist) on top of the named rider layer; `replay[r]` is the rule station layer inside the environment and must equal `rule_r`.
