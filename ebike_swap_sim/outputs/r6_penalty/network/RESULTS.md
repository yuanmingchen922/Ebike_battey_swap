# R6 network -- value of the swap network vs coordination (P 60, w 18, v 15)

2 x 2 per seed (home charging vs network) x (policy vs relaxed aggregated ILP), as r5_x4_network phase a; VoN = home - network, VoC = policy - ILP; Shapley shares; mean +- exact t 95 % over seeds (paired per seed).

## best_rule vs relaxed ILP, end-adjusted totals (USD per window)

| case | policy | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| r5_stress4h | best_rule | H_policy | 2354.24 | 92.51 | 5 |
| r5_stress4h | best_rule | H_ilp | 1693.08 | 92.43 | 5 |
| r5_stress4h | best_rule | N_policy | 1581.76 | 292.36 | 5 |
| r5_stress4h | best_rule | N_ilp | 942.01 | 122.18 | 5 |
| r5_stress4h | best_rule | VoN_policy | 772.48 | 291.37 | 5 |
| r5_stress4h | best_rule | VoN_ilp | 751.07 | 59.78 | 5 |
| r5_stress4h | best_rule | VoC_network | 639.76 | 185.81 | 5 |
| r5_stress4h | best_rule | VoC_home | 661.17 | 154.75 | 5 |
| r5_stress4h | best_rule | VoN_policy_pct | 32.80 | 12.35 | 5 |
| r5_stress4h | best_rule | VoN_ilp_pct | 44.46 | 4.92 | 5 |
| r5_stress4h | best_rule | VoC_network_pct | 40.00 | 5.43 | 5 |
| r5_stress4h | best_rule | VoC_home_pct | 27.99 | 5.79 | 5 |
| r5_stress4h | best_rule | total_effect | 1412.24 | 148.42 | 5 |
| r5_stress4h | best_rule | interaction | -21.41 | 271.70 | 5 |
| r5_stress4h | best_rule | shapley_network | 761.78 | 160.57 | 5 |
| r5_stress4h | best_rule | shapley_coordination | 650.46 | 103.84 | 5 |
| usd4h_ebaas | best_rule | H_policy | 1674.34 | 42.79 | 10 |
| usd4h_ebaas | best_rule | H_ilp | 1015.27 | 60.75 | 10 |
| usd4h_ebaas | best_rule | N_policy | 838.50 | 85.18 | 10 |
| usd4h_ebaas | best_rule | N_ilp | 601.42 | 28.72 | 10 |
| usd4h_ebaas | best_rule | VoN_policy | 835.84 | 84.57 | 10 |
| usd4h_ebaas | best_rule | VoN_ilp | 413.85 | 46.57 | 10 |
| usd4h_ebaas | best_rule | VoC_network | 237.08 | 64.31 | 10 |
| usd4h_ebaas | best_rule | VoC_home | 659.07 | 59.04 | 10 |
| usd4h_ebaas | best_rule | VoN_policy_pct | 49.93 | 4.96 | 10 |
| usd4h_ebaas | best_rule | VoN_ilp_pct | 40.58 | 2.84 | 10 |
| usd4h_ebaas | best_rule | VoC_network_pct | 27.34 | 5.65 | 10 |
| usd4h_ebaas | best_rule | VoC_home_pct | 39.36 | 3.35 | 10 |
| usd4h_ebaas | best_rule | total_effect | 1072.92 | 39.67 | 10 |
| usd4h_ebaas | best_rule | interaction | -421.99 | 102.16 | 10 |
| usd4h_ebaas | best_rule | shapley_network | 624.85 | 45.29 | 10 |
| usd4h_ebaas | best_rule | shapley_coordination | 448.08 | 34.67 | 10 |

## Lateness per policy (seed means; lateness.csv has the t 95 % half-widths)

| case | infra | method | n_late | n_late_over_30min | n_late_over_60min | mean_lateness_min | max_lateness_min | served_share |
|---|---|---|---|---|---|---|---|---|
| r5_stress4h | home | ilp_relaxed | 11.20 | 0.20 | 0 | 5.17 | 29 | 0.59 |
| r5_stress4h | home | r2 | 11.60 | 9.80 | 0.60 | 27.49 | 63 | 0.38 |
| r5_stress4h | home | r5 | 14.20 | 13.80 | 0.40 | 37.75 | 62 | 0.40 |
| r5_stress4h | home | r5_range | 14.20 | 13.80 | 0.40 | 37.75 | 62 | 0.40 |
| r5_stress4h | network | ilp_relaxed | 10.80 | 1 | 0 | 3.30 | 35 | 0.95 |
| r5_stress4h | network | r2 | 22 | 6.20 | 0.20 | 15.43 | 50 | 0.74 |
| r5_stress4h | network | r5 | 20.60 | 5 | 0.20 | 12.87 | 52 | 0.74 |
| r5_stress4h | network | r5_range | 20.60 | 5 | 0.20 | 12.87 | 52 | 0.74 |
| usd4h_ebaas | home | ilp_relaxed | 7.30 | 0.70 | 0 | 3.44 | 26 | 0.74 |
| usd4h_ebaas | home | r2 | 4.60 | 3.50 | 0.20 | 13.93 | 49.50 | 0.36 |
| usd4h_ebaas | home | r5 | 8 | 5.90 | 0.20 | 22.53 | 57 | 0.38 |
| usd4h_ebaas | home | r5_range | 8 | 5.90 | 0.20 | 22.53 | 57 | 0.38 |
| usd4h_ebaas | network | ilp_relaxed | 3.10 | 0.20 | 0 | 0.93 | 13.50 | 0.99 |
| usd4h_ebaas | network | r2 | 14.10 | 1.20 | 0 | 6.72 | 28.50 | 0.93 |
| usd4h_ebaas | network | r5 | 13.80 | 0.90 | 0 | 6.78 | 27 | 0.91 |
| usd4h_ebaas | network | r5_range | 13.80 | 0.90 | 0 | 6.78 | 27 | 0.91 |

## Anomalies

* none

Files: records.jsonl, results.csv, decomposition.csv, summary.csv (long: case, basis = total or total_end_adjusted, policy, metric = quantity of the X4 decomposition, mean, ci95, n), ebaas_metrics.csv, lateness.csv.
