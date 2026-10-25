# R6 rolling -- foresight vs coordination under P 60, w 18, v 15

Rolling horizon W 24, k 6, lambda 10 min, aggregated windows, relaxed targets; offline reference and rules from the headline / psweep rows of the same instance (demand md5 checked). Per seed: headline = best_rule - offline, VoI = rolling - offline, VoC online = best_rule - rolling; mean +- exact t 95 %.

| case | metric | mean | ci95 | n |
|---|---|---|---|---|
| r5_stress4h | rolling_served_share | 0.817 | 0.088 | 5 |
| r5_stress4h | rolling_n_late_over_60min | 0 | 0 | 5 |
| r5_stress4h | headline_ea | 639.756 | 185.808 | 5 |
| r5_stress4h | value_of_information_ea | 300.777 | 148.465 | 5 |
| r5_stress4h | value_of_coordination_online_ea | 338.978 | 160.666 | 5 |
| r5_stress4h | share_surviving_online_ea | 0.526 | 0.183 | 5 |
| usd4h | rolling_served_share | 0.933 | 0.042 | 10 |
| usd4h | rolling_n_late_over_60min | 0 | 0 | 10 |
| usd4h | headline_ea | 237.092 | 64.313 | 10 |
| usd4h | value_of_information_ea | 137.095 | 55.607 | 10 |
| usd4h | value_of_coordination_online_ea | 99.998 | 68.870 | 10 |
| usd4h | share_surviving_online_ea | 0.289 | 0.480 | 10 |

## Anomalies

* none
