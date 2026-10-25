# E9 M4 -- compliance sweep (share of riders following the coordinator)

Family `r5_manhattan` (8 bikes); candidates `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/candidates.csv`; cache `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/r5_x6_manhattan/cache`; reposition targets `open_sites`; min served share 0.5; swap-only sites need a C / SC object: True; wall 0.2 min; Threads 3; TimeLimit 300 s (hubs 600 s, integrated 600 s); Gurobi Seed 0.

Every ILP total on the semi-real family is an upper bound on the written optimum (moves only into candidate / depot nodes, E8 convention); the R2.4 geometry caveat applies (real restaurants, zone weights and candidate coordinates on a synthetic 150 m grid; elevation and signals synthetic).

## Protocol

Layout M06:SC:B4:C2|M12:S:B3:C0 (cli); plan = the cached lower-level ILP schedule per scenario; non-compliant riders follow the r5_selfish rule; draws [0, 1, 2]; seeds [0, 1, 2].

## V against compliance

| alpha_c | V | served_share | mean_defected | complete |
|---|---|---|---|---|
| 0 | 1165.023 | 0.625 | 0 | True |
| 0.250 | 1081.071 | 0.722 | 0.556 | True |
| 0.500 | 998.626 | 0.767 | 0.444 | True |
| 0.750 | 849.093 | 0.817 | 0 | True |
| 1 | 703.115 | 0.858 | 0 | True |

## Per scenario and draw

| scenario | alpha_c | draw | status | opex | ilp_opex | served_share | n_compliant | n_defected | check_ok |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | OK | 1067.446 | 675.012 | 0.625 | 0 | 0 | False |
| 0 | 0 | 1 | OK | 1067.446 | 675.012 | 0.625 | 0 | 0 | False |
| 0 | 0 | 2 | OK | 1067.446 | 675.012 | 0.625 | 0 | 0 | False |
| 0 | 0.250 | 0 | OK | 1117.672 | 675.012 | 0.700 | 2 | 1 | False |
| 0 | 0.250 | 1 | OK | 835.192 | 675.012 | 0.700 | 2 | 0 | False |
| 0 | 0.250 | 2 | OK | 984.682 | 675.012 | 0.750 | 2 | 1 | False |
| 0 | 0.500 | 0 | OK | 981.646 | 675.012 | 0.775 | 4 | 1 | False |
| 0 | 0.500 | 1 | OK | 771.871 | 675.012 | 0.800 | 4 | 0 | False |
| 0 | 0.500 | 2 | OK | 989.227 | 675.012 | 0.775 | 4 | 0 | False |
| 0 | 0.750 | 0 | OK | 782.581 | 675.012 | 0.750 | 6 | 0 | False |
| 0 | 0.750 | 1 | OK | 735.420 | 675.012 | 0.925 | 6 | 0 | False |
| 0 | 0.750 | 2 | OK | 772.944 | 675.012 | 0.800 | 6 | 0 | False |
| 0 | 1 | 0 | OK | 675.012 | 675.012 | 0.875 | 8 | 0 | True |
| 0 | 1 | 1 | OK | 675.012 | 675.012 | 0.875 | 8 | 0 | True |
| 0 | 1 | 2 | OK | 675.012 | 675.012 | 0.875 | 8 | 0 | True |
| 1 | 0 | 0 | OK | 1024.257 | 648.030 | 0.625 | 0 | 0 | False |
| 1 | 0 | 1 | OK | 1024.257 | 648.030 | 0.625 | 0 | 0 | False |
| 1 | 0 | 2 | OK | 1024.257 | 648.030 | 0.625 | 0 | 0 | False |
| 1 | 0.250 | 0 | OK | 1036.429 | 648.030 | 0.725 | 2 | 1 | False |
| 1 | 0.250 | 1 | OK | 1216.407 | 648.030 | 0.650 | 2 | 0 | False |
| 1 | 0.250 | 2 | OK | 847.321 | 648.030 | 0.800 | 2 | 0 | False |
| 1 | 0.500 | 0 | OK | 946.327 | 648.030 | 0.800 | 4 | 1 | False |
| 1 | 0.500 | 1 | OK | 991.741 | 648.030 | 0.775 | 4 | 0 | False |
| 1 | 0.500 | 2 | OK | 1008.367 | 648.030 | 0.725 | 4 | 1 | False |
| 1 | 0.750 | 0 | OK | 776.905 | 648.030 | 0.750 | 6 | 0 | False |
| 1 | 0.750 | 1 | OK | 837.750 | 648.030 | 0.825 | 6 | 0 | False |
| 1 | 0.750 | 2 | OK | 741.601 | 648.030 | 0.875 | 6 | 0 | False |
| 1 | 1 | 0 | OK | 648.030 | 648.030 | 0.900 | 8 | 0 | True |
| 1 | 1 | 1 | OK | 648.030 | 648.030 | 0.900 | 8 | 0 | True |
| 1 | 1 | 2 | OK | 648.030 | 648.030 | 0.900 | 8 | 0 | True |
| 2 | 0 | 0 | OK | 1323.722 | 706.657 | 0.625 | 0 | 0 | False |
| 2 | 0 | 1 | OK | 1323.722 | 706.657 | 0.625 | 0 | 0 | False |
| 2 | 0 | 2 | OK | 1323.722 | 706.657 | 0.625 | 0 | 0 | False |
| 2 | 0.250 | 0 | OK | 1094.948 | 706.657 | 0.700 | 2 | 1 | False |
| 2 | 0.250 | 1 | OK | 1176.448 | 706.657 | 0.775 | 2 | 0 | False |
| 2 | 0.250 | 2 | OK | 1181.606 | 706.657 | 0.700 | 2 | 1 | False |
| 2 | 0.500 | 0 | OK | 1022.636 | 706.657 | 0.700 | 4 | 1 | False |
| 2 | 0.500 | 1 | OK | 1098.940 | 706.657 | 0.750 | 4 | 0 | False |
| 2 | 0.500 | 2 | OK | 937.948 | 706.657 | 0.800 | 4 | 0 | False |
| 2 | 0.750 | 0 | OK | 860.114 | 706.657 | 0.750 | 6 | 0 | False |
| 2 | 0.750 | 1 | OK | 979.981 | 706.657 | 0.825 | 6 | 0 | False |
| 2 | 0.750 | 2 | OK | 915.608 | 706.657 | 0.850 | 6 | 0 | False |
| 2 | 1 | 0 | OK | 706.657 | 706.657 | 0.800 | 8 | 0 | True |
| 2 | 1 | 1 | OK | 706.657 | 706.657 | 0.800 | 8 | 0 | True |
| 2 | 1 | 2 | OK | 706.657 | 706.657 | 0.800 | 8 | 0 | True |

## Solver statistics

{"n_solves": 0, "n_cache_hits": 3, "n_baseline_runs": 0, "n_errors": 0, "solver_time_s": 0.0, "library_time_s": 10.987238666042686, "n_cached_rows": 1152, "reposition": "open_sites", "aggregate": true, "variant": {}}

## Figures

* `compliance.png`
