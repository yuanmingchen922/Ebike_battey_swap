# E2 smoke -- synthetic families, baseline vs ILP

Seed 0; pruning {'tau_max': 4, 'start_slack': 6, 'reachable': False} (reposition targets = restaurants + facilities + depots); Gurobi Threads 4, TimeLimit 300 s, OutputFlag 0.

| family | n_bikes | n_orders | H | L | n_arcs | build_time_s | ilp_build_time_s | ilp_binaries | ilp_rows | ilp_status | ilp_obj | ilp_bound | ilp_gap | ilp_runtime_s | baseline_total | baseline_runtime_s | baseline_families | baseline_unserved | ilp_unserved_n | baseline_gap_pct | mip_start_accepted | mip_start_verified_status | ilp_ok | baseline_identity_24_ok | ilp_identity_24_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| small | 4 | 12 | 24 | 8 | 279408 | 0.2393 | 0.6728 | 279423 | 23276 | OPTIMAL | 287 | 287 | 0 | 2.2141 | 483.3667 | 0.0008 | {} | 200 | 0 | 68.4204 | True | OPTIMAL | True | True | True |
| medium | 8 | 24 | 24 | 8 | 740736 | 0.7965 | 1.5982 | 740763 | 44904 | OPTIMAL | 399.1500 | 399.1500 | 0 | 5.7639 | 716.6833 | 0.0011 | {"(18)": 1} | 300 | 0 | 79.5524 | False | INFEASIBLE | True | True | True |
| large | 10 | 30 | 24 | 12 | 1491030 | 1.6555 | 3.4870 | 1491063 | 80306 | OPTIMAL | 485.0500 | 485.0500 | 0 | 14.8579 | 968.8611 | 0.0016 | {"(18)": 1} | 500 | 0 | 99.7446 | False | INFEASIBLE | True | True | True |

`baseline_gap_pct` = (baseline - ILP) / ILP in %; `baseline_families` are the constraint families the policy reports (only (9), (17), (18) are allowed, they are reported, not enforced); `mip_start_accepted` is the fix-and-solve certificate of the baseline start (False when the baseline violates (18), i.e. ends with fewer full spares than rho * sum B).
