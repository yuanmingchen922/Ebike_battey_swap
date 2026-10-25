# R6 rl_seeds -- PPO over three training seeds under P 60, w 18, v 15

Seed 0 = r6_penalty/rl; seeds 1 and 2 = this stage (same 200,000 steps, training seeds 1000-1019, test seeds 0-9, hyper-parameters a7_rl.PPO_DEFAULTS).  Reference rows (relaxed ILP 300 s, rules) from r6_penalty/rl.  Per PPO seed: mean over the test seeds (paired differences per test seed); across: mean +- exact t 95 % over the PPO seeds (n 3); pooled: over seeds x test seeds.

## Training

| ppo_seed | family | rider | status | timesteps_done | runtime_s | return_first100 | return_last100 | train_id |
|---|---|---|---|---|---|---|---|---|
| 0 | nyc4h_stress2 | r2 | TRAINED | 200704 | 543.95 | -123.98 | -114.71 | nyc4h_stress2_r2_20261018T115835 |
| 0 | nyc4h_stress2 | r5 | TRAINED | 200704 | 488.68 | -132.14 | -99.97 | nyc4h_stress2_r5_20261018T120705 |
| 0 | r5_stress4h | r2 | TRAINED | 200704 | 1602.74 | -180.31 | -197.42 | r5_stress4h_r2_20261018T134814 |
| 0 | r5_stress4h | r5 | TRAINED | 200704 | 1412.93 | -183.22 | -191.29 | r5_stress4h_r5_20261018T141308 |
| 1 | nyc4h_stress2 | r2 | TRAINED | 200704 | 464.57 | -131.10 | -100.80 | nyc4h_stress2_r2_20261019T133020 |
| 1 | nyc4h_stress2 | r5 | TRAINED | 200704 | 467.86 | -126.83 | -100.27 | nyc4h_stress2_r5_20261019T133826 |
| 1 | r5_stress4h | r2 | TRAINED | 200704 | 1611.84 | -189.08 | -188.25 | r5_stress4h_r2_20261019T140637 |
| 1 | r5_stress4h | r5 | TRAINED | 200704 | 1572.33 | -180.53 | -188.17 | r5_stress4h_r5_20261019T143404 |
| 2 | nyc4h_stress2 | r2 | TRAINED | 200704 | 461.19 | -128.55 | -113.99 | nyc4h_stress2_r2_20261019T144309 |
| 2 | nyc4h_stress2 | r5 | TRAINED | 200704 | 462.18 | -128.25 | -105.59 | nyc4h_stress2_r5_20261019T145109 |
| 2 | r5_stress4h | r2 | TRAINED | 200704 | 1322.20 | -186.45 | -190.98 | r5_stress4h_r2_20261019T151427 |
| 2 | r5_stress4h | r5 | TRAINED | 200704 | 1364.45 | -181.65 | -186.08 | r5_stress4h_r5_20261019T153824 |

## Across PPO seeds (n = number of PPO seeds with the cell)

| family | rider | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| nyc4h_stress2 | r2 | rl_ea | 1064.734 | 22.602 | 3 |
| nyc4h_stress2 | r2 | rl_minus_replay | 8.379 | 22.602 | 3 |
| nyc4h_stress2 | r2 | rl_minus_best_rule | 47.065 | 22.602 | 3 |
| nyc4h_stress2 | r2 | rl_minus_ilp | 312.925 | 22.602 | 3 |
| nyc4h_stress2 | r2 | gap_rl_vs_ilp_pct | 28.719 | 1.648 | 3 |
| nyc4h_stress2 | r5 | rl_ea | 1109.472 | 15.056 | 3 |
| nyc4h_stress2 | r5 | rl_minus_replay | 4.157 | 15.056 | 3 |
| nyc4h_stress2 | r5 | rl_minus_best_rule | 91.803 | 15.056 | 3 |
| nyc4h_stress2 | r5 | rl_minus_ilp | 357.663 | 15.056 | 3 |
| nyc4h_stress2 | r5 | gap_rl_vs_ilp_pct | 31.421 | 0.885 | 3 |
| r5_stress4h | r2 | rl_ea | 1752.495 | 93.547 | 3 |
| r5_stress4h | r2 | rl_minus_replay | 62.870 | 93.547 | 3 |
| r5_stress4h | r2 | rl_minus_best_rule | 138.375 | 93.547 | 3 |
| r5_stress4h | r2 | rl_minus_ilp | 782.976 | 93.547 | 3 |
| r5_stress4h | r2 | gap_rl_vs_ilp_pct | 44.305 | 3.498 | 3 |
| r5_stress4h | r5 | rl_ea | 1804.796 | 2.912 | 3 |
| r5_stress4h | r5 | rl_minus_replay | 150.486 | 2.912 | 3 |
| r5_stress4h | r5 | rl_minus_best_rule | 190.676 | 2.912 | 3 |
| r5_stress4h | r5 | rl_minus_ilp | 835.276 | 2.912 | 3 |
| r5_stress4h | r5 | gap_rl_vs_ilp_pct | 46.279 | 0.075 | 3 |

## Per PPO seed (means over test seeds)

| family | rider | ppo_seed | metric | mean | ci95 | n |
|---|---|---|---|---|---|---|
| nyc4h_stress2 | r2 | 0 | rl_ea | 1055.242 | 106.713 | 10 |
| nyc4h_stress2 | r2 | 0 | rl_minus_replay | -1.113 | 4.092 | 10 |
| nyc4h_stress2 | r2 | 0 | rl_minus_best_rule | 37.573 | 66.302 | 10 |
| nyc4h_stress2 | r2 | 0 | gap_rl_vs_ilp_pct | 28.006 | 4.727 | 10 |
| nyc4h_stress2 | r2 | 1 | rl_ea | 1073.379 | 94.935 | 10 |
| nyc4h_stress2 | r2 | 1 | rl_minus_replay | 17.024 | 33.660 | 10 |
| nyc4h_stress2 | r2 | 1 | rl_minus_best_rule | 55.710 | 68.693 | 10 |
| nyc4h_stress2 | r2 | 1 | gap_rl_vs_ilp_pct | 29.318 | 5.156 | 10 |
| nyc4h_stress2 | r2 | 2 | rl_ea | 1065.580 | 98.546 | 10 |
| nyc4h_stress2 | r2 | 2 | rl_minus_replay | 9.225 | 13.973 | 10 |
| nyc4h_stress2 | r2 | 2 | rl_minus_best_rule | 47.911 | 64.197 | 10 |
| nyc4h_stress2 | r2 | 2 | gap_rl_vs_ilp_pct | 28.833 | 4.560 | 10 |
| nyc4h_stress2 | r5 | 0 | rl_ea | 1109.454 | 122.777 | 10 |
| nyc4h_stress2 | r5 | 0 | rl_minus_replay | 4.139 | 8.757 | 10 |
| nyc4h_stress2 | r5 | 0 | rl_minus_best_rule | 91.785 | 78.371 | 10 |
| nyc4h_stress2 | r5 | 0 | gap_rl_vs_ilp_pct | 31.394 | 4.776 | 10 |
| nyc4h_stress2 | r5 | 1 | rl_ea | 1103.420 | 117.687 | 10 |
| nyc4h_stress2 | r5 | 1 | rl_minus_replay | -1.895 | 18.053 | 10 |
| nyc4h_stress2 | r5 | 1 | rl_minus_best_rule | 85.751 | 75.736 | 10 |
| nyc4h_stress2 | r5 | 1 | gap_rl_vs_ilp_pct | 31.079 | 4.783 | 10 |
| nyc4h_stress2 | r5 | 2 | rl_ea | 1115.542 | 121.960 | 10 |
| nyc4h_stress2 | r5 | 2 | rl_minus_replay | 10.227 | 32.358 | 10 |
| nyc4h_stress2 | r5 | 2 | rl_minus_best_rule | 97.873 | 75.002 | 10 |
| nyc4h_stress2 | r5 | 2 | gap_rl_vs_ilp_pct | 31.790 | 4.722 | 10 |
| r5_stress4h | r2 | 0 | rl_ea | 1729.864 | 174.692 | 10 |
| r5_stress4h | r2 | 0 | rl_minus_replay | 40.238 | 27.482 | 10 |
| r5_stress4h | r2 | 0 | rl_minus_best_rule | 115.743 | 76.704 | 10 |
| r5_stress4h | r2 | 0 | gap_rl_vs_ilp_pct | 43.471 | 3.815 | 10 |
| r5_stress4h | r2 | 1 | rl_ea | 1795.967 | 133.999 | 10 |
| r5_stress4h | r2 | 1 | rl_minus_replay | 106.341 | 59.117 | 10 |
| r5_stress4h | r2 | 1 | rl_minus_best_rule | 181.846 | 68.937 | 10 |
| r5_stress4h | r2 | 1 | gap_rl_vs_ilp_pct | 45.931 | 2.596 | 10 |
| r5_stress4h | r2 | 2 | rl_ea | 1731.656 | 178.305 | 10 |
| r5_stress4h | r2 | 2 | rl_minus_replay | 42.030 | 32.458 | 10 |
| r5_stress4h | r2 | 2 | rl_minus_best_rule | 117.536 | 79.857 | 10 |
| r5_stress4h | r2 | 2 | gap_rl_vs_ilp_pct | 43.513 | 3.801 | 10 |
| r5_stress4h | r5 | 0 | rl_ea | 1803.605 | 111.975 | 10 |
| r5_stress4h | r5 | 0 | rl_minus_replay | 149.295 | 43.243 | 10 |
| r5_stress4h | r5 | 0 | rl_minus_best_rule | 189.485 | 75.855 | 10 |
| r5_stress4h | r5 | 0 | gap_rl_vs_ilp_pct | 46.248 | 2.490 | 10 |
| r5_stress4h | r5 | 1 | rl_ea | 1805.949 | 112.141 | 10 |
| r5_stress4h | r5 | 1 | rl_minus_replay | 151.639 | 41.802 | 10 |
| r5_stress4h | r5 | 1 | rl_minus_best_rule | 191.828 | 72.584 | 10 |
| r5_stress4h | r5 | 1 | gap_rl_vs_ilp_pct | 46.308 | 2.593 | 10 |
| r5_stress4h | r5 | 2 | rl_ea | 1804.834 | 111.300 | 10 |
| r5_stress4h | r5 | 2 | rl_minus_replay | 150.524 | 42.441 | 10 |
| r5_stress4h | r5 | 2 | rl_minus_best_rule | 190.714 | 75.011 | 10 |
| r5_stress4h | r5 | 2 | gap_rl_vs_ilp_pct | 46.282 | 2.535 | 10 |

Files: records.jsonl (seeds 1-2, with ppo_seed), seed<k>/ (X7 folders), per_test_seed.csv, training.csv, summary_by_ppo_seed.csv, summary_across_ppo_seeds.csv, summary_pooled.csv.
