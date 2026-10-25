# R6 rolling_ext -- lookahead 0 / 20 min and the bootstrap-forecast battery plan under P 60, w 18, v 15

W 24, k 6, window TimeLimit 60 s, aggregated windows, relaxed final targets; forecast = BootstrapForecast(pool all), 1 scenario, lambda 10.  Lambda 10 from r6_penalty/rolling; offline relaxed ILP and the rules from headline / psweep (same instances).  Per seed: VoI = rolling - offline, VoC online = best rule - rolling, share surviving = VoC online / headline; differences to lambda 10 paired per seed; mean +- exact t 95 %.

| case | metric | mean | ci95 | n |
|---|---|---|---|---|
| r5_stress4h | voc_online_lam0_ea | 97.079 | 140.525 | 5 |
| r5_stress4h | share_surviving_lam0_ea | 0.121 | 0.244 | 5 |
| r5_stress4h | diff_lam0_minus_lam10_ea | 241.900 | 54.245 | 5 |
| r5_stress4h | voc_online_lam10_ea | 338.978 | 160.666 | 5 |
| r5_stress4h | share_surviving_lam10_ea | 0.526 | 0.182 | 5 |
| r5_stress4h | voc_online_lam20_ea | 236.955 | 320.369 | 5 |
| r5_stress4h | share_surviving_lam20_ea | 0.293 | 0.555 | 5 |
| r5_stress4h | diff_lam20_minus_lam10_ea | 102.023 | 204.148 | 5 |
| r5_stress4h | voc_online_forecast10_ea | 297.432 | 80.924 | 5 |
| r5_stress4h | share_surviving_forecast10_ea | 0.480 | 0.147 | 5 |
| r5_stress4h | diff_forecast10_minus_lam10_ea | 41.546 | 140.524 | 5 |
| r5_stress4h | lam0_served_share | 0.708 | 0.082 | 5 |
| r5_stress4h | lam10_served_share | 0.817 | 0.088 | 5 |
| r5_stress4h | lam20_served_share | 0.767 | 0.069 | 5 |
| r5_stress4h | forecast10_served_share | 0.800 | 0.108 | 5 |
| usd4h | voc_online_lam0_ea | -33.150 | 83.817 | 10 |
| usd4h | share_surviving_lam0_ea | -0.326 | 0.537 | 10 |
| usd4h | diff_lam0_minus_lam10_ea | 133.148 | 61.553 | 10 |
| usd4h | voc_online_lam10_ea | 99.998 | 68.870 | 10 |
| usd4h | share_surviving_lam10_ea | 0.289 | 0.480 | 10 |
| usd4h | voc_online_lam20_ea | 100.196 | 105.450 | 10 |
| usd4h | share_surviving_lam20_ea | 0.354 | 0.416 | 10 |
| usd4h | diff_lam20_minus_lam10_ea | -0.198 | 84.633 | 10 |
| usd4h | voc_online_forecast10_ea | 102.994 | 104.945 | 10 |
| usd4h | share_surviving_forecast10_ea | 0.109 | 0.933 | 10 |
| usd4h | diff_forecast10_minus_lam10_ea | -2.996 | 72.299 | 10 |
| usd4h | lam0_served_share | 0.867 | 0.062 | 10 |
| usd4h | lam10_served_share | 0.933 | 0.042 | 10 |
| usd4h | lam20_served_share | 0.939 | 0.061 | 10 |
| usd4h | forecast10_served_share | 0.942 | 0.045 | 10 |

## Anomalies

* none

Files: records.jsonl, results.csv, per_instance.csv, summary.csv.
