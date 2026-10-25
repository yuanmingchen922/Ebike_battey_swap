# R6 compliance -- M4 compliance sweep, selfish equilibrium and rule r2 on Manhattan under P 60, w 18, v 15

Repriced r5_manhattan scenarios (3 seeds, written targets, aggregated ILP, Threads 3, Seed 0, TimeLimit 300 s / 600 s with a charge-only hub).  V = allocated set-up + mean scenario OPEX.  Compliance: share psi of the riders follows the ILP plan (station layer = plan), the others follow follower E (r5_selfish); 3 draws of the compliant set per psi; V per draw, then mean +- exact t 95 % over draws.  psi = 1 reproduces the ILP value.

## Layout values under the followers

| layout_key | layout_label | policy | status | V | served_share | statuses | gaps | n_solves | o2_UB | o2_certified |
|---|---|---|---|---|---|---|---|---|---|---|
| M04:SC:B2:C2|M09:SC:B4:C2 | o2_best_m2 | baseline | OK | 1148.45 | 0.82 | ["POLICY", "POLICY", "POLICY"] | [null, null, null] | 0 | 699.96 | False |
| M04:SC:B2:C2|M09:SC:B4:C2 | o2_best_m2 | ilp | OK | 699.96 | 0.98 | ["OPTIMAL", "OPTIMAL", "OPTIMAL"] | [0.0, 0.0, 0.0] | 0 | 699.96 | False |
| M04:SC:B2:C2|M09:SC:B4:C2 | o2_best_m2 | selfish | OK | 1168.58 | 0.81 | ["POLICY", "POLICY", "POLICY"] | [null, null, null] | 0 | 699.96 | False |
| M06:SC:B4:C2|M12:S:B3:C0 | r5_chosen | baseline | OK | 1238.55 | 0.75 | ["POLICY", "POLICY", "POLICY"] | [null, null, null] | 3 | - | - |
| M06:SC:B4:C2|M12:S:B3:C0 | r5_chosen | ilp | OK | 802.43 | 0.96 | ["TIME_LIMIT", "TIME_LIMIT", "TIME_LIMIT"] | [0.06441953469117083, 0.0849444439231272, 0.02876113062110014] | 0 | - | - |
| M06:SC:B4:C2|M12:S:B3:C0 | r5_chosen | selfish | OK | 1248.87 | 0.76 | ["POLICY", "POLICY", "POLICY"] | [null, null, null] | 3 | - | - |

## Compliance curve (mean +- t 95 % over draws)

| layout_key | alpha_c | metric | mean | ci95 | n |
|---|---|---|---|---|---|
| M04:SC:B2:C2|M09:SC:B4:C2 | 0 | V | 1491.148 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0 | served_share | 0.667 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0 | gap_vs_selfish_pct | -27.603 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0 | share_of_selfish_gap_recovered | -0.688 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.250 | V | 1307.198 | 151.807 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.250 | served_share | 0.753 | 0.067 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.250 | gap_vs_selfish_pct | -11.862 | 12.991 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.250 | share_of_selfish_gap_recovered | -0.296 | 0.324 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.500 | V | 1100.129 | 130.776 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.500 | served_share | 0.822 | 0.043 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.500 | gap_vs_selfish_pct | 5.858 | 11.191 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.500 | share_of_selfish_gap_recovered | 0.146 | 0.279 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.750 | V | 902.199 | 122.619 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.750 | served_share | 0.897 | 0.067 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.750 | gap_vs_selfish_pct | 22.795 | 10.493 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 0.750 | share_of_selfish_gap_recovered | 0.568 | 0.262 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 1 | V | 699.957 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 1 | served_share | 0.983 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 1 | gap_vs_selfish_pct | 40.102 | 0 | 3 |
| M04:SC:B2:C2|M09:SC:B4:C2 | 1 | share_of_selfish_gap_recovered | 1 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0 | V | 1474.924 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0 | served_share | 0.650 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0 | gap_vs_selfish_pct | -18.101 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0 | share_of_selfish_gap_recovered | -0.506 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.250 | V | 1251.262 | 304.316 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.250 | served_share | 0.758 | 0.115 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.250 | gap_vs_selfish_pct | -0.192 | 24.367 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.250 | share_of_selfish_gap_recovered | -0.005 | 0.682 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.500 | V | 1050.359 | 84.823 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.500 | served_share | 0.836 | 0.073 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.500 | gap_vs_selfish_pct | 15.895 | 6.792 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.500 | share_of_selfish_gap_recovered | 0.445 | 0.190 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.750 | V | 937.087 | 113.514 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.750 | served_share | 0.903 | 0.084 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.750 | gap_vs_selfish_pct | 24.965 | 9.089 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 0.750 | share_of_selfish_gap_recovered | 0.698 | 0.254 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 1 | V | 802.426 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 1 | served_share | 0.958 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 1 | gap_vs_selfish_pct | 35.748 | 0 | 3 |
| M06:SC:B4:C2|M12:S:B3:C0 | 1 | share_of_selfish_gap_recovered | 1 | 0 | 3 |

## Anomalies

* none

Files: records.jsonl, results.csv, per_draw.csv, summary.csv, layout_values.csv, cache/.
