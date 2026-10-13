# E1 -- toy reproduction (E2 pp.10-15, Battery_Swap p.7)

Toy instance: {'bikes': 2, 'orders': 3, 'nodes': 3, 'routes': 6, 'facilities': 2, 'swap_sites': 1, 'charge_sites': 1, 'services': 2, 'H': 8, 'L': 2, 'Delta_h': 0.08333333333333333, 'eps_kwh': 0.02, 'p_ch_kw': 0.3}; arc library {'wait': 144, 'move': 156, 'deliver': 124, 'swap': 32, 'term': 14, 'total': 470} built in 0.000 s.

## Results

| case | method | switches | status | total | expected | match | C_travel | C_elec | unserved | response | lateness | C_reb | runtime_s | check_ok | reported_families | identity_24_ok | obj_eq_cost | mip_start_accepted | lex_min_unserved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| toy | ILP | written model | OPTIMAL | 12.500 | 12.500 | True | 4 | 0.100 | 0 | 6 | 0 | 2.400 | 0.003 | True | {} | True | True | - | - |
| toy | ILP | rho=0 | OPTIMAL | 11.200 | 11.200 | True | 4 | 0 | 0 | 6 | 0 | 1.200 | 0.002 | True | {} | True | True | - | - |
| toy | ILP | no_transfers | OPTIMAL | 106 | 106 | True | 2 | 0 | 100 | 4 | 0 | 0 | 0.001 | True | {} | True | True | - | - |
| toy | ILP | lexicographic | OPTIMAL | 12.500 | 12.500 | True | 4 | 0.100 | 0 | 6 | 0 | 2.400 | 0.005 | True | {} | True | True | - | 0 |
| toy | ILP | lexicographic+no_transfers | OPTIMAL | 106 | 106 | True | 2 | 0 | 100 | 4 | 0 | 0 | 0.002 | True | {} | True | True | - | 1 |
| toy | baseline | transfer_rule=NONE | - | 108 | 108 | True | 4 | 0 | 100 | 4 | 0 | 0 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | transfer_rule=REORDER_POINT | - | 14.500 | 14.500 | True | 6 | 0.100 | 0 | 6 | 0 | 2.400 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=default, transfer_rule=NONE | - | 108 | 108 | True | 4 | 0 | 100 | 4 | 0 | 0 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=default, transfer_rule=REORDER_POINT | - | 14.500 | 14.500 | True | 6 | 0.100 | 0 | 6 | 0 | 2.400 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=round1, transfer_rule=NONE | - | 108 | 108 | True | 4 | 0 | 100 | 4 | 0 | 0 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=round1, transfer_rule=REORDER_POINT | - | 14.500 | 14.500 | True | 6 | 0.100 | 0 | 6 | 0 | 2.400 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=legacy, transfer_rule=NONE | - | 108 | 108 | True | 4 | 0 | 100 | 4 | 0 | 0 | 0.000 | True | {} | True | - | - | - |
| toy | baseline | variant=legacy, transfer_rule=REORDER_POINT | - | 14.500 | 14.500 | True | 6 | 0.100 | 0 | 6 | 0 | 2.400 | 0.000 | True | {} | True | - | - | - |
| toy | ILP | MIP start = baseline REORDER_POINT | OPTIMAL | 12.500 | 12.500 | True | 4 | 0.100 | 0 | 6 | 0 | 2.400 | 0.002 | True | {} | True | True | True | - |
| toy | ILP | MIP start = baseline NONE | OPTIMAL | 12.500 | 12.500 | True | 4 | 0.100 | 0 | 6 | 0 | 2.400 | 0.002 | True | {} | True | True | True | - |
| toy | ILP | no_transfers, MIP start = baseline NONE | OPTIMAL | 106 | 106 | True | 2 | 0 | 100 | 4 | 0 | 0 | 0.001 | True | {} | True | True | True | - |
| p7 | baseline | default | - | 0.100 | 0.100 | True | 0 | 0.100 | 0 | 0 | 0 | 0 | 0.000 | True | {} | True | - | - | - |
| p7 | ILP | rho=0, MIP start = baseline | OPTIMAL | 0 | 0 | True | 0 | 0 | 0 | 0 | 0 | 0 | 0.001 | True | {} | True | True | True | - |
| p7 | ILP | rho=1, q_res=2, one bike | OPTIMAL | 0.100 | 0.100 | True | 0 | 0.100 | 0 | 0 | 0 | 0 | 0.000 | True | {} | True | True | - | - |

`match` compares `total` with the documented value; `reported_families` lists the constraint families `evaluate.check` reports (the baseline may report (9), (17), (18) without being wrong); `obj_eq_cost` is Gurobi objective == `evaluate.cost` total; `mip_start_accepted` is certified by the fix-and-solve verification of `ilp.set_mip_start`.

## Inventory table of the toy optimum (E2 p.15)

Reproduces the documented table: **True**.

| t | n[A][0] | n[A][1] | n[A][2] | n[C][0] | n[C][1] | n[C][2] | m_t |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| 2 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| 3 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| 6 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| 7 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 8 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

Bike paths of the optimum:

- bike 1: deliver order 2: ('A', 0, 2) -> ('B', 2, 1); wait: ('B', 2, 1) -> ('B', 3, 1); wait: ('B', 3, 1) -> ('B', 4, 1); wait: ('B', 4, 1) -> ('B', 5, 1); wait: ('B', 5, 1) -> ('B', 6, 1); wait: ('B', 6, 1) -> ('B', 7, 1); wait: ('B', 7, 1) -> ('B', 8, 1); term fac A: ('B', 8, 1) -> sink
- bike 2: deliver order 1: ('A', 0, 2) -> ('B', 2, 1); move: ('B', 2, 1) -> ('A', 3, 0); swap fac A: ('A', 3, 0) -> ('A', 4, 2); deliver order 3: ('A', 4, 2) -> ('B', 6, 1); wait: ('B', 6, 1) -> ('B', 7, 1); wait: ('B', 7, 1) -> ('B', 8, 1); term fac A: ('B', 8, 1) -> sink

Transfers: h = {1: 1, 2: 1}, z = {"(1, 2)": 1, "(2, 0)": 1}, charging c = {"('C', 0, 6)": 1, "('C', 1, 7)": 1}.

## Baseline rules: round 1 vs round 2 (DECISIONS R2.3)

Cases 6-7 use the round-2 defaults of `BaselineParams` (`stock_aware_site=True`, `charge_rule='DEMAND_AWARE'` with lead = lookback = 12, charge-only hubs under `hub_charge_rule='HIGH_FIRST'`). `round1` = nearest site regardless of stock + ASAP HIGH_FIRST charging (the round-1 policy after the reviewer fixes); `legacy` = round1 without JIT dispatch and dead-zone rule. On the toy the three variants coincide in cost: A is the only swap site (stock-aware choice can only fall back to it) and the hub C follows HIGH_FIRST, so DEMAND_AWARE changes nothing. The literal R2.3 reading at the hub (`hub_charge_rule='DEMAND_AWARE'`) would give 14.4 with a reported (18) shortfall of 1 (see `tests/test_baseline.py`).

| variant | transfer_rule | total | C_travel | C_elec | unserved | response | C_reb | n_swaps | charge_steps | stock_aware_reroutes | stock_aware_fallbacks | charge_rule_effective | reported_families | ok_modulo_report_only | identity_24_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| default | NONE | 108 | 4 | 0 | 100 | 4 | 0 | 0 | 0 | 0 | 4 | {"C": "HIGH_FIRST"} | {} | True | True |
| default | REORDER_POINT | 14.500 | 6 | 0.100 | 0 | 6 | 2.400 | 1 | 2 | 0 | 4 | {"C": "HIGH_FIRST"} | {} | True | True |
| round1 | NONE | 108 | 4 | 0 | 100 | 4 | 0 | 0 | 0 | 0 | 0 | {"C": "HIGH_FIRST"} | {} | True | True |
| round1 | REORDER_POINT | 14.500 | 6 | 0.100 | 0 | 6 | 2.400 | 1 | 2 | 0 | 0 | {"C": "HIGH_FIRST"} | {} | True | True |
| legacy | NONE | 108 | 4 | 0 | 100 | 4 | 0 | 0 | 0 | 0 | 0 | {"C": "HIGH_FIRST"} | {} | True | True |
| legacy | REORDER_POINT | 14.500 | 6 | 0.100 | 0 | 6 | 2.400 | 1 | 2 | 0 | 0 | {"C": "HIGH_FIRST"} | {} | True | True |

## Battery_Swap p.7 inventory table (baseline policy)

Reproduces the documented table: **True**.

| t | n[J][0] | n[J][1] | n[J][2] | m_t |
|---|---|---|---|---|
| 0 | 0 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 | 0 |
| 2 | 0 | 1 | 0 | 0 |
| 3 | 0 | 0 | 1 | 0 |
| 4 | 1 | 0 | 0 | 0 |

## Identities

- (24) battery conservation holds on every schedule: True
- baseline online inventory == (13) recursion: NONE True, REORDER_POINT True, p7 True
- Gurobi objective == evaluate.cost total on every ILP run: True
- lexicographic: U* = 0 (written model), 1 (no_transfers)

## Figures

- `inventory_toy.png`: stock trajectories of the toy optimum
- `cost_components.png`: cost components per toy case
