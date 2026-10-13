# E4u -- station sizing under USD (spares B_j, chargers C_j, power P_j), usd4h family: final report

## Summary (5 sentences)

1. On the usd4h instances (4-hour evening peak, 6 bikes / 36 orders, initial charge 30-60 %), when the ILP is free to choose the station sizes at usd_sunk USD prices it buys only 3-4 spare batteries and 2-3 chargers (the default configuration is 9 and 6), in every seed at least one site takes no charger, and the total-cost saving is only 1.3-1.6 $/window, because the holding costs of batteries and chargers are small to begin with (0.332 / 0.082 $/site/4 h).
2. The ILP cost is almost completely insensitive to B_j, C_j and P_j: the operating cost is already flat from 1 spare battery per site (600.0 -> 598.6 -> 598.3 $), the marginal value of one more battery is +0.47 $/window operating and +0.14 total for 1->2 (not significant) and negative afterwards; the operating marginal value of a charger is exactly 0 (the operating costs of the three seeds are identical at C_j = 1,2,3,4), and the power cap P_j does not bind either (the C_j = 1 solution is feasible at 1.4 kW, proving that the ILP curve is flat within the 0.06 $ solver tolerance).
3. The knee has moved to the baseline side: under the R2.3 rules, going from 1 to 2 batteries per site saves the baseline 48.5 $/battery/window (about 71,000 $/battery/year at 1460 windows/year), 2->3 saves 8.5 $, and afterwards ~ 0; in 2 seeds the baseline's service rate never reaches the ILP's level at the default size (0.806 vs 0.861 / 0.889) even with 6 batteries per site, and its total cost never reaches it in any of the 3 seeds.
4. At the default size (B 3, C 2, P 4 kW) the headline gap is 22.5 +/- 21.3 % (three seeds 16.1 / 32.2 / 19.1 %, ILP 637.9 vs baseline 832.2 $/window); the gap comes mainly from the baseline's lateness penalty (97 $), unserved orders (50 $) and response time (45.5 $), while electricity and riding distance contribute less than 2 $.
5. Compared with round 1 (toy units, 2 h, stressed state: the ILP had a clear knee at 2 batteries per site and the baseline needed >4 to catch up), under the round-2 USD pricing the ILP itself no longer has a knee and 1 battery is enough, whereas the baseline still needs 2-3 to be stable; note that the ILP's P sweep and the 12 off-line B x C cells were not solved because of the 58-minute wall-clock budget (the baseline side was completed with the policy on 2026-10-12), so for the ILP's off-line B x C cells these conclusions follow only from a monotonicity argument rather than from solves.

## Setup and data provenance

Family `usd4h` (DECISIONS R2.2: |K| = 6, |I| = 36, H = 48 slots of 5 min (17:00-21:00), L = 12, q0 ~ U{4..7} = 30-60 % of L, p_ch = 0.667 kW), 3 co-located sites (K_j = 8, Cbar_j = 6, M_j = 1, sigma_j = 1, R_end = 1, rho = 0.5, q_res = 1, grid group 8 kW / 6 kW 18-20 h), cost variant `usd_sunk` (R2.1: kappa 0.12 $/km, pi 0.32 $/kWh, P 30 $, w 18 $/h, v 36 $/h, F 12.03 $, bB 0.332 $, bC 0.082 $ per site per 4 h window). Baseline = round-2 rules (R2.3: stock-aware site choice, DEMAND_AWARE charging, JIT dispatch). Instances are byte-identical across methods and sizes (only B_j, C_j, P_kw change). Pruning: plan defaults + reachable (lossless on this family). Gurobi Threads 3, TimeLimit 300 s. Costs are USD per 4 h window; `total` is (26) including the setup constant (27) `F_j + bB B_j + bC C_j`; `operational` = total - C_setup. Headline gap = (baseline - ILP) / baseline. Marginal values = paired (within-seed) finite differences of cost per one unit added at one site (network change / 3 sites / step size), positive = adding the unit saves cost; annualised x 1460 (16 h / 4 h x 365, the task convention, i.e. every window priced like the dinner peak).

Records used:

- `results.csv`: 55 rows written by `experiments/e4u_sizing_usd.py` (29 ILP, 26 baseline; wall 57.6 min). No duplicate (seed, tag, method) rows were present (0 dropped). The script skipped 20 (seed, size) variants under its 58 min wall budget: the whole P sweep (8 ILP + 8 baseline runs), seed 2 of B3_C4_P4, and the 12 off-line B x C cells on seed 0; no ILP was solved for any of them.
- `results_baseline_fill.csv`: 47 baseline-only rows produced on 2026-10-12 by running the R2.3 policy (milliseconds each, same `sized_instance` / `pruning_for` / `run_baseline_case` path, written instances with rho = 0.5, `policy_reserve_source = R_end` on every row) on every skipped cell for seeds 0-2: P sweep (9), seed 2 B3_C4_P4 (1), the 12 off-line B x C cells x 3 seeds (36), plus one reproduction run of the stored seed 0 B3_C2_P4 baseline (identical: |diff| = 0.00 USD; excluded from the statistics). No ILP solve was run; the ILP P sweep is replaced by a certified bound (below), and the 12 off-line B x C ILP cells stay unsolved.
- The fairness fix F1 (relaxed-copy baseline reserve) does not touch this experiment: E4u never runs on a `relax_end_targets` copy (rho = 0.5, R_end = 1 on every row). The units fix (E8) is unrelated.

## Headline at the R2.2 default sizes (B_j = 3, C_j = 2, P_j = 4 kW; seeds 0-2, mean ± 95 % t-CI, n = 3)

| quantity | ILP (E2, rho = 0.5) | baseline (R2.3) | per seed (0 / 1 / 2) |
|---|---|---|---|
| total USD per 4 h window | 637.91 ± 55.26 | 832.16 ± 311.68 | ILP 615.15 / 659.60 / 638.98; baseline 733.10 / 973.24 / 790.12 |
| served share | 0.907 ± 0.144 | 0.861 ± 0.239 | ILP 0.972 / 0.861 / 0.889; baseline 0.972 / 0.806 / 0.806 |
| headline gap (baseline - ILP) / baseline | 22.5 ± 21.3 % | | 16.1 / 32.2 / 19.1 % |
| gap by component (USD) | lateness 97.0, unserved 50.0 (1.67 orders), response 45.5, C_travel 1.3, C_elec 0.4 | | |

## Sweep B: spares per site B_j (C_j = 2, P_j = 4 kW); mean over seeds 0-2 ± 95 % t-CI (n = 3)

**ILP**

| B_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 637.56 ± 52.05 | 599.98 ± 52.05 | 0.898 ± 0.105 | 3.67 ± 3.79 | 473.5 ± 57.0 | 4.0 ± 4.3 | 1.08 ± 0.38 | 7.33 ± 3.79 | 103.7 ± 60.9 | 4.0 ± 4.3 | 5.3 ± 7.6 | 0.211 ± 0.074 | 0.229 ± 0.449 | 3.00 ± 0.00 | 0.139 ± 1.136 | 0.471 ± 1.136 | 203 ± 1659 | - |
| 2 | 3 | 637.14 ± 55.15 | 598.56 ± 55.15 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.58 ± 0.59 | 7.00 ± 4.30 | 40.0 ± 41.3 | 0.3 ± 1.4 | 2.3 ± 6.3 | 0.113 ± 0.116 | 0.701 ± 0.287 | 3.00 ± 0.00 | -0.257 ± 0.038 | 0.075 ± 0.038 | -375 ± 55 | - |
| 3 | 3 | 637.91 ± 55.26 | 598.34 ± 55.26 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.41 ± 0.75 | 7.33 ± 5.74 | 26.7 ± 43.4 | 0.0 ± 0.0 | 4.7 ± 7.6 | 0.081 ± 0.147 | 0.806 ± 0.311 | 5.00 ± 0.00 | -0.249 ± 0.015 | 0.083 ± 0.015 | -364 ± 21 | - |
| 4 | 3 | 638.66 ± 55.31 | 598.09 ± 55.31 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.17 ± 0.71 | 7.33 ± 5.74 | 6.0 ± 25.8 | 0.0 ± 0.0 | 3.3 ± 3.8 | 0.032 ± 0.139 | 0.954 ± 0.199 | 6.00 ± 0.00 | -0.310 ± 0.093 | 0.022 ± 0.093 | -453 ± 136 | - |
| 6 | 3 | 640.52 ± 55.81 | 597.96 ± 55.81 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.04 ± 0.15 | 7.67 ± 5.17 | 0.0 ± 0.0 | 0.0 ± 0.0 | 7.3 ± 6.3 | 0.007 ± 0.030 | 1.000 ± 0.000 | 10.67 ± 3.79 | - | - | - | - |

**baseline**

| B_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 1003.05 ± 440.56 | 965.47 ± 440.56 | 0.815 ± 0.242 | 6.67 ± 8.72 | 553.5 ± 197.9 | 199.0 ± 253.6 | 1.08 ± 0.31 | 7.33 ± 1.43 | 61.0 ± 17.4 | 18.3 ± 18.3 | 24.3 ± 29.8 | 0.212 ± 0.060 | 0.525 ± 0.129 | 1.33 ± 1.43 | 48.487 ± 77.574 | 48.819 ± 77.574 | 70791 ± 113258 | 35.1 ± 28.1 % |
| 2 | 3 | 857.59 ± 391.46 | 819.01 ± 391.46 | 0.870 ± 0.222 | 4.67 ± 7.99 | 543.0 ± 152.2 | 122.0 ± 200.0 | 1.17 ± 0.17 | 7.00 ± 0.00 | 21.7 ± 5.7 | 3.3 ± 14.3 | 4.0 ± 15.1 | 0.228 ± 0.033 | 0.829 ± 0.040 | 5.00 ± 0.00 | 8.477 ± 38.083 | 8.809 ± 38.083 | 12377 ± 55601 | 24.4 ± 26.6 % |
| 3 | 3 | 832.16 ± 311.68 | 792.59 ± 311.68 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.85 ± 0.24 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.166 ± 0.048 | 0.938 ± 0.079 | 5.33 ± 2.87 | -0.269 ± 0.073 | 0.063 ± 0.073 | -393 ± 107 | 22.5 ± 21.3 % |
| 4 | 3 | 832.96 ± 311.90 | 792.40 ± 311.90 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.63 ± 0.18 | 7.33 ± 1.43 | 1.7 ± 7.2 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.123 ± 0.036 | 0.986 ± 0.060 | 7.33 ± 2.87 | 2.441 ± 11.580 | 2.773 ± 11.580 | 3564 ± 16907 | 22.5 ± 21.3 % |
| 6 | 3 | 818.32 ± 244.78 | 775.76 ± 244.78 | 0.861 ± 0.239 | 5.00 ± 8.61 | 521.0 ± 143.6 | 92.0 ± 99.2 | 0.24 ± 0.38 | 7.00 ± 0.00 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.046 ± 0.073 | 1.000 ± 0.000 | 11.67 ± 2.87 | - | - | - | 21.2 ± 16.3 % |

## Sweep C: chargers per site C_j (B_j = 3, P_j = 4 kW)

ILP at C_j = 4 has seeds 0 and 1 only (seed 2 was skipped by the 58 min wall budget); its marginal value 3 -> 4 is the paired difference on seeds 0-1. The baseline at C_j = 4 has all three seeds (seed 2 baseline filled on 2026-10-12, `results_baseline_fill.csv`).

**ILP**

| C_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 637.66 ± 55.26 | 598.34 ± 55.26 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.41 ± 0.75 | 7.33 ± 5.74 | 27.3 ± 42.0 | 0.0 ± 0.0 | 5.7 ± 10.0 | 0.162 ± 0.294 | 0.799 ± 0.294 | 5.00 ± 0.00 | -0.082 ± 0.000 | 0.000 ± 0.000 | -120 ± 0 | - |
| 2 | 3 | 637.91 ± 55.26 | 598.34 ± 55.26 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.41 ± 0.75 | 7.33 ± 5.74 | 26.7 ± 43.4 | 0.0 ± 0.0 | 4.7 ± 7.6 | 0.081 ± 0.147 | 0.806 ± 0.311 | 5.00 ± 0.00 | -0.082 ± 0.000 | 0.000 ± 0.000 | -120 ± 0 | - |
| 3 | 3 | 638.15 ± 55.26 | 598.34 ± 55.26 | 0.907 ± 0.144 | 3.33 ± 5.17 | 481.5 ± 91.0 | 5.0 ± 8.6 | 0.41 ± 0.75 | 7.33 ± 5.74 | 27.0 ± 32.5 | 0.0 ± 0.0 | 4.7 ± 3.8 | 0.054 ± 0.098 | 0.803 ± 0.235 | 5.00 ± 0.00 | -0.091 (n=2) | -0.009 (n=2) | -133 (n=2) | - |
| 4 | 2 | 637.89 (n=2) | 597.83 (n=2) | 0.917 (n=2) | 3.00 (n=2) | 489.8 (n=2) | 6.0 (n=2) | 0.52 (n=2) | 8.00 (n=2) | 29.5 (n=2) | 0.0 (n=2) | 5.0 (n=2) | 0.051 (n=2) | 0.781 (n=2) | 5.00 (n=2) | - | - | - | - |

**baseline**

| C_j | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 831.65 ± 311.67 | 792.33 ± 311.67 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.59 ± 0.23 | 7.33 ± 1.43 | 10.7 ± 16.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.231 ± 0.089 | 0.910 ± 0.121 | 4.33 ± 2.87 | -0.167 ± 0.017 | -0.085 ± 0.017 | -244 ± 25 | 22.5 ± 21.3 % |
| 2 | 3 | 832.16 ± 311.68 | 792.59 ± 311.68 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.85 ± 0.24 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.166 ± 0.048 | 0.938 ± 0.079 | 5.33 ± 2.87 | -0.112 ± 0.039 | -0.030 ± 0.039 | -163 ± 57 | 22.5 ± 21.3 % |
| 3 | 3 | 832.49 ± 311.74 | 792.67 ± 311.74 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.94 ± 0.29 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.122 ± 0.038 | 0.938 ± 0.079 | 6.33 ± 2.87 | -0.082 ± 0.000 | -0.000 ± 0.000 | -120 ± 0 | 22.5 ± 21.3 % |
| 4 | 3 | 832.74 ± 311.74 | 792.67 ± 311.74 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.94 ± 0.29 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.091 ± 0.029 | 0.938 ± 0.079 | 6.33 ± 2.87 | - | - | - | 24.2 (n=2) % |

## Sweep P: site power limit P_j (B_j = 3, C_j = 4): baseline only, with an ILP sandwich bound

The ILP P sweep was never solved (all 8 (seed, P) ILP runs fell under the wall budget), so only the baseline rows exist (filled 2026-10-12). (20) allows floor(P_j / 0.667 kW) = 2 / 4 / 6 simultaneous chargers at 1.4 / 2.8 / 4.2 kW, so with C_j = 4 only P_j = 1.4 kW can bind; the P_j = 4.0 kW column is the stored C sweep cell B3_C4_P4 (floor(4.0 / 0.667) = 6 with the floor tolerance, i.e. identical to 4.2 kW).

**ILP**

| P_kw | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.4 | 0 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 2.8 | 0 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| 4 | 2 | 637.89 (n=2) | 597.83 (n=2) | 0.917 (n=2) | 3.00 (n=2) | 489.8 (n=2) | 6.0 (n=2) | 0.52 (n=2) | 8.00 (n=2) | 29.5 (n=2) | 0.0 (n=2) | 5.0 (n=2) | 0.051 (n=2) | 0.781 (n=2) | 5.00 (n=2) | - | - | - | - |
| 4.2 | 0 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |

**baseline**

| P_kw | n | total USD/4 h | operational USD | served share | n unserved | response USD | lateness USD | C_elec USD | swaps | stock-out site-slots | stock-out+queue slots | swap-wait bike-slots | charger util | idle-full share | end full (18) lhs | marg. total / unit / window | marg. oper. / unit / window | marg. total / unit / year | headline gap |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.4 | 3 | 832.65 ± 311.68 | 792.59 ± 311.68 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.85 ± 0.24 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.083 ± 0.024 | 0.938 ± 0.079 | 5.33 ± 2.87 | -0.021 ± 0.028 | -0.021 ± 0.028 | -31 ± 41 | - |
| 2.8 | 3 | 832.74 ± 311.74 | 792.67 ± 311.74 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.94 ± 0.29 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.091 ± 0.029 | 0.938 ± 0.079 | 6.33 ± 2.87 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0 ± 0 | - |
| 4 | 3 | 832.74 ± 311.74 | 792.67 ± 311.74 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.94 ± 0.29 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.091 ± 0.029 | 0.938 ± 0.079 | 6.33 ± 2.87 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0 ± 0 | 24.2 (n=2) % |
| 4.2 | 3 | 832.74 ± 311.74 | 792.67 ± 311.74 | 0.861 ± 0.239 | 5.00 ± 8.61 | 527.0 ± 146.8 | 102.0 ± 142.2 | 0.94 ± 0.29 | 7.33 ± 1.43 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.091 ± 0.029 | 0.938 ± 0.079 | 6.33 ± 2.87 | - | - | - | - |

ILP bound at P_j = 1.4 kW (no solve): the C_j = 1 optimum uses at most one charger per site in any slot ((14)/(20) with C_j = 1), so it is feasible at (B 3, C 4, P 1.4) where two are allowed; hence opt_oper(P 1.4) <= oper(B3_C1_P4), and opt_oper(P 1.4) >= oper(B3_C4_P4) because lowering P_j only removes solutions. Per seed (operational USD):

| seed | lower bound = oper(B3_C4_P4) | upper bound = oper(B3_C1_P4) | width |
|---|---|---|---|
| 0 | 575.630 | 575.576 | -0.053 |
| 1 | 620.031 | 620.031 | 0.000 |
| 2 | - (no C 4 run) | 599.409 | - |

The ILP cost-vs-P curve is therefore flat to within 0.05 USD per window (seed 0; exactly flat on seed 1), i.e. the marginal value of a kW for the ILP is 0 (|value| < 0.05 / 3 / 1.4 = 0.012 USD per kW per window) at these sizes.

## What the coordinator buys: B_j, C_j free at usd_sunk prices (y_j = 1 fixed)

| seed | sweep | method | status | total | oper. | C_setup | served | n_unserved | response | lateness | C_elec | swaps | chosen B | chosen C | sum B | sum C | chg util | idle-full | end full | gap | runtime s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | free | ILP | OPTIMAL | 613.83 | 576.17 | 37.66 | 0.972 | 1 | 523.5 | 9.0 | 1.17 | 9 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.46 | 0.47 | 3 | 0.00008 | 190.9 |
| 0 | free_fixed | ILP | OPTIMAL | 613.83 | 576.17 | 37.66 | 0.972 | 1 | 523.5 | 9.0 | 1.17 | 9 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.46 | 0.47 | 3 | 0.00003 | 65.3 |
| 0 | free_fixed | baseline | - | 790.37 | 752.71 | 37.66 | 0.972 | 1 | 600.0 | 108.0 | 1.08 | 8 | {"S1": 2, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 1} | 4 | 3 | 0.42 | 0.58 | 1 | - | 0.0 |
| 1 | free | ILP | OPTIMAL | 657.99 | 620.74 | 37.25 | 0.861 | 5 | 456.0 | 3.0 | 0.94 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.55 | 0.41 | 3 | 0.00007 | 129.8 |
| 1 | free_fixed | ILP | OPTIMAL | 657.99 | 620.74 | 37.25 | 0.861 | 5 | 456.0 | 3.0 | 0.94 | 6 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.55 | 0.41 | 3 | 0.00000 | 69.9 |
| 1 | free_fixed | baseline | - | 1175.98 | 1138.73 | 37.25 | 0.722 | 10 | 547.5 | 279.0 | 0.75 | 7 | {"S1": 1, "S2": 1, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 3 | 2 | 0.44 | 0.48 | 0 | - | 0.0 |
| 2 | free | ILP | OPTIMAL | 637.63 | 600.05 | 37.58 | 0.889 | 4 | 465.0 | 3.0 | 0.85 | 6 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.50 | 0.53 | 3 | 0.00002 | 169.6 |
| 2 | free_fixed | ILP | OPTIMAL | 637.63 | 600.05 | 37.58 | 0.889 | 4 | 465.0 | 3.0 | 0.85 | 6 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.50 | 0.53 | 3 | 0.00004 | 50.2 |
| 2 | free_fixed | baseline | - | 908.86 | 871.28 | 37.58 | 0.722 | 10 | 448.5 | 111.0 | 0.78 | 7 | {"S1": 1, "S2": 2, "S3": 1} | {"S1": 1, "S2": 1, "S3": 0} | 4 | 2 | 0.46 | 0.48 | 1 | - | 0.0 |

| seed | ILP free total | ILP at default B3/C2 | saving of free sizing | units removed vs default | baseline at free sizes | baseline at default | gap at free sizes | baseline served at free sizes | ILP served |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 613.83 | 615.15 | 1.32 | 5 batteries, 3 chargers | 790.37 | 733.10 | 22.3 % | 0.972 | 0.972 |
| 1 | 657.99 | 659.60 | 1.61 | 6 batteries, 4 chargers | 1175.98 | 973.24 | 44.0 % | 0.722 | 0.861 |
| 2 | 637.63 | 638.98 | 1.35 | 5 batteries, 4 chargers | 908.86 | 790.12 | 29.8 % | 0.722 | 0.889 |

## Spares the baseline needs to match the ILP service level (B sweep, C_j = 2, P_j = 4 kW)

| seed | ILP served @B3 | ILP total @B3 | ILP mean resp. h @B3 | baseline served @B3 | baseline served @B6 | baseline total @B6 | B_j to match ILP served | B_j to match served + response | B_j to match ILP total | B_j to match ILP@B1 served |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.972 | 615.15 | 0.831 | 0.972 | 0.972 | 735.30 | 2 | unreachable (> 6) | unreachable (> 6) | 2 |
| 1 | 0.861 | 659.60 | 0.817 | 0.806 | 0.806 | 927.21 | unreachable (> 6) | unreachable (> 6) | unreachable (> 6) | unreachable (> 6) |
| 2 | 0.889 | 638.98 | 0.807 | 0.806 | 0.806 | 792.44 | unreachable (> 6) | unreachable (> 6) | unreachable (> 6) | unreachable (> 6) |

## Gap decomposition: baseline - ILP by cost component (seed means over common seeds; gap in % of baseline)

| sweep | size | n | baseline total | ILP total | gap | gap % | gap unserved | gap response | gap lateness | gap C_travel | gap C_elec | base n_unserved | ILP n_unserved | base n_late | ILP n_late |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 1 | 3 | 1003.05 | 637.56 | 365.49 | 36.4 | 90.00 | 80.00 | 195.00 | 0.49 | 0.01 | 6.67 | 3.67 | 15.00 | 1.33 |
| B | 2 | 3 | 857.59 | 637.14 | 220.45 | 25.7 | 40.00 | 61.50 | 117.00 | 1.36 | 0.59 | 4.67 | 3.33 | 13.33 | 1.67 |
| B | 3 | 3 | 832.16 | 637.91 | 194.25 | 23.3 | 50.00 | 45.50 | 97.00 | 1.31 | 0.43 | 5.00 | 3.33 | 11.67 | 1.67 |
| B | 4 | 3 | 832.96 | 638.66 | 194.31 | 23.3 | 50.00 | 45.50 | 97.00 | 1.34 | 0.46 | 5.00 | 3.33 | 11.67 | 1.67 |
| B | 6 | 3 | 818.32 | 640.52 | 177.80 | 21.7 | 50.00 | 39.50 | 87.00 | 1.10 | 0.20 | 5.00 | 3.33 | 11.67 | 1.67 |
| C | 1 | 3 | 831.65 | 637.66 | 193.99 | 23.3 | 50.00 | 45.50 | 97.00 | 1.31 | 0.18 | 5.00 | 3.33 | 11.67 | 1.67 |
| C | 2 | 3 | 832.16 | 637.91 | 194.25 | 23.3 | 50.00 | 45.50 | 97.00 | 1.31 | 0.43 | 5.00 | 3.33 | 11.67 | 1.67 |
| C | 3 | 3 | 832.49 | 638.15 | 194.34 | 23.3 | 50.00 | 45.50 | 97.00 | 1.31 | 0.52 | 5.00 | 3.33 | 11.67 | 1.67 |
| C | 4 | 2 | 853.78 | 637.89 | 215.89 | 25.3 | 30.00 | 69.75 | 114.00 | 1.67 | 0.46 | 4.00 | 3.00 | 14.50 | 2.00 |

## B x C grid at P_j = 4 kW (seed means; n in brackets)

**ILP: total USD per window (served share)**

| B_j \ C_j | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 1 | - (not run) | 637.6 (0.898) [n=3] | - (not run) | - (not run) |
| 2 | - (not run) | 637.1 (0.907) [n=3] | - (not run) | - (not run) |
| 3 | 637.7 (0.907) [n=3] | 637.9 (0.907) [n=3] | 638.2 (0.907) [n=3] | 637.9 (0.917) [n=2] |
| 4 | - (not run) | 638.7 (0.907) [n=3] | - (not run) | - (not run) |
| 6 | - (not run) | 640.5 (0.907) [n=3] | - (not run) | - (not run) |

**baseline: total USD per window (served share)**

| B_j \ C_j | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 1 | 1002.8 (0.815) [n=3] | 1003.0 (0.815) [n=3] | 1003.3 (0.815) [n=3] | 1003.5 (0.815) [n=3] |
| 2 | 857.0 (0.870) [n=3] | 857.6 (0.870) [n=3] | 857.8 (0.870) [n=3] | 858.1 (0.870) [n=3] |
| 3 | 831.7 (0.861) [n=3] | 832.2 (0.861) [n=3] | 832.5 (0.861) [n=3] | 832.7 (0.861) [n=3] |
| 4 | 832.6 (0.861) [n=3] | 833.0 (0.861) [n=3] | 833.3 (0.861) [n=3] | 833.6 (0.861) [n=3] |
| 6 | 818.0 (0.861) [n=3] | 818.3 (0.861) [n=3] | 818.6 (0.861) [n=3] | 818.9 (0.861) [n=3] |

## Stock-out and queue diagnostics at the default sizes (B 3, C 2, P 4 kW) and at B_j = 1

| size | method | n | stock-out site-slots | stock-out with bike queued | swap-wait bike-slots | desk occupancy | charger util | idle-full share | peak kW (group) | swaps | kWh bought | end full |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B3_C2 | ILP | 3 | 26.7 ± 43.4 | 0.0 ± 0.0 | 4.7 ± 7.6 | 0.051 ± 0.040 | 0.081 ± 0.147 | 0.806 ± 0.311 | 1.78 ± 1.91 | 7.33 ± 5.74 | 1.30 ± 2.35 | 5.00 ± 0.00 |
| B3_C2 | baseline | 3 | 7.7 ± 10.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.051 ± 0.010 | 0.166 ± 0.048 | 0.938 ± 0.079 | 2.22 ± 1.91 | 7.33 ± 1.43 | 2.65 ± 0.76 | 5.33 ± 2.87 |
| B1_C2 | ILP | 3 | 103.7 ± 60.9 | 4.0 ± 4.3 | 5.3 ± 7.6 | 0.051 ± 0.026 | 0.211 ± 0.074 | 0.229 ± 0.449 | 1.78 ± 0.96 | 7.33 ± 3.79 | 3.37 ± 1.19 | 3.00 ± 0.00 |
| B1_C2 | baseline | 3 | 61.0 ± 17.4 | 18.3 ± 18.3 | 24.3 ± 29.8 | 0.051 ± 0.010 | 0.212 ± 0.060 | 0.525 ± 0.129 | 2.00 ± 0.00 | 7.33 ± 1.43 | 3.39 ± 0.97 | 1.33 ± 1.43 |
| B6_C2 | ILP | 3 | 0.0 ± 0.0 | 0.0 ± 0.0 | 7.3 ± 6.3 | 0.053 ± 0.036 | 0.007 ± 0.030 | 1.000 ± 0.000 | 0.22 ± 0.96 | 7.67 ± 5.17 | 0.11 ± 0.48 | 10.67 ± 3.79 |
| B6_C2 | baseline | 3 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.3 ± 1.4 | 0.049 ± 0.000 | 0.046 ± 0.073 | 1.000 ± 0.000 | 0.89 ± 0.96 | 7.00 ± 0.00 | 0.74 ± 1.17 | 11.67 ± 2.87 |

## Per-instance table (every row of results.csv plus the baseline fill rows)

| seed | sweep | tag | method | status | total | oper. | served | n_unserved | response | lateness | C_elec | swaps | stock-out slots | swap-wait | end full | reported families | MIP gap | runtime s | MIP start | source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | B | B1_C2_P4 | ILP | TIME_LIMIT | 616.42 | 578.84 | 0.944 | 2 | 499.5 | 6.0 | 1.244 | 9 | 128 | 2 | 3 | {} | 0.00295 | 300.1 | default | results.csv |
| 0 | B | B1_C2_P4 | baseline | - | 1010.56 | 972.98 | 0.917 | 3 | 636.0 | 234.0 | 1.084 | 7 | 61 | 25 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | results.csv |
| 0 | B | B2_C2_P4 | ILP | OPTIMAL | 614.42 | 575.85 | 0.972 | 1 | 523.5 | 9.0 | 0.853 | 9 | 21 | 2 | 3 | {} | 0.00000 | 159.0 | default | results.csv |
| 0 | B | B2_C2_P4 | baseline | - | 767.46 | 728.89 | 0.972 | 1 | 591.0 | 93.0 | 1.244 | 7 | 23 | 0 | 5 | {} | - | 0.0 | - | results.csv |
| 0 | B | B3_C2_P4 | ILP | OPTIMAL | 615.15 | 575.58 | 0.972 | 1 | 523.5 | 9.0 | 0.764 | 10 | 12 | 8 | 5 | {} | 0.00001 | 173.6 | default | results.csv |
| 0 | B | B3_C2_P4 | baseline | - | 733.10 | 693.53 | 0.972 | 1 | 577.5 | 72.0 | 0.960 | 7 | 12 | 0 | 6 | {} | - | 0.0 | - | results.csv |
| 0 | B | B4_C2_P4 | ILP | OPTIMAL | 615.88 | 575.31 | 0.972 | 1 | 523.5 | 9.0 | 0.498 | 10 | 18 | 3 | 6 | {} | 0.00006 | 146.7 | default | results.csv |
| 0 | B | B4_C2_P4 | baseline | - | 733.85 | 693.28 | 0.972 | 1 | 577.5 | 72.0 | 0.711 | 7 | 0 | 0 | 8 | {} | - | 0.0 | - | results.csv |
| 0 | B | B6_C2_P4 | ILP | OPTIMAL | 617.48 | 574.92 | 0.972 | 1 | 523.5 | 9.0 | 0.107 | 10 | 0 | 5 | 9 | {} | 0.00000 | 122.9 | default | results.csv |
| 0 | B | B6_C2_P4 | baseline | - | 735.30 | 692.75 | 0.972 | 1 | 577.5 | 72.0 | 0.178 | 7 | 0 | 0 | 11 | {} | - | 0.0 | - | results.csv |
| 0 | C | B3_C1_P4 | ILP | OPTIMAL | 614.90 | 575.58 | 0.972 | 1 | 523.5 | 9.0 | 0.764 | 10 | 13 | 10 | 5 | {} | 0.00000 | 112.2 | default | results.csv |
| 0 | C | B3_C1_P4 | baseline | - | 732.59 | 693.26 | 0.972 | 1 | 577.5 | 72.0 | 0.693 | 7 | 18 | 0 | 5 | {} | - | 0.0 | - | results.csv |
| 0 | C | B3_C3_P4 | ILP | OPTIMAL | 615.39 | 575.58 | 0.972 | 1 | 523.5 | 9.0 | 0.764 | 10 | 18 | 5 | 5 | {} | 0.00000 | 119.2 | default | results.csv |
| 0 | C | B3_C3_P4 | baseline | - | 733.45 | 693.63 | 0.972 | 1 | 577.5 | 72.0 | 1.067 | 7 | 12 | 0 | 7 | {} | - | 0.0 | - | results.csv |
| 0 | C | B3_C4_P4 | ILP | OPTIMAL | 615.69 | 575.63 | 0.972 | 1 | 523.5 | 9.0 | 0.818 | 10 | 20 | 6 | 5 | {} | 0.00010 | 117.8 | default | results.csv |
| 0 | C | B3_C4_P4 | baseline | - | 733.70 | 693.63 | 0.972 | 1 | 577.5 | 72.0 | 1.067 | 7 | 12 | 0 | 7 | {} | - | 0.0 | - | results.csv |
| 0 | P | B3_C4_P1.4 | baseline | - | 733.59 | 693.53 | 0.972 | 1 | 577.5 | 72.0 | 0.960 | 7 | 12 | 0 | 6 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | P | B3_C4_P2.8 | baseline | - | 733.70 | 693.63 | 0.972 | 1 | 577.5 | 72.0 | 1.067 | 7 | 12 | 0 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | P | B3_C4_P4.2 | baseline | - | 733.70 | 693.63 | 0.972 | 1 | 577.5 | 72.0 | 1.067 | 7 | 12 | 0 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | free | free | ILP | OPTIMAL | 613.83 | 576.17 | 0.972 | 1 | 523.5 | 9.0 | 1.173 | 9 | 68 | 3 | 3 | {} | 0.00008 | 190.9 | - | results.csv |
| 0 | free_fixed | free_fixed | ILP | OPTIMAL | 613.83 | 576.17 | 0.972 | 1 | 523.5 | 9.0 | 1.173 | 9 | 68 | 2 | 3 | {} | 0.00003 | 65.3 | chain:free | results.csv |
| 0 | free_fixed | free_fixed | baseline | - | 790.37 | 752.71 | 0.972 | 1 | 600.0 | 108.0 | 1.084 | 8 | 54 | 6 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | results.csv |
| 0 | heat | B1_C1_P4 | baseline | - | 1010.31 | 972.98 | 0.917 | 3 | 636.0 | 234.0 | 1.084 | 7 | 61 | 25 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B1_C3_P4 | baseline | - | 1010.81 | 972.98 | 0.917 | 3 | 636.0 | 234.0 | 1.084 | 7 | 61 | 25 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B1_C4_P4 | baseline | - | 1011.05 | 972.98 | 0.917 | 3 | 636.0 | 234.0 | 1.084 | 7 | 61 | 25 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B2_C1_P4 | baseline | - | 766.84 | 728.52 | 0.972 | 1 | 591.0 | 93.0 | 0.871 | 7 | 29 | 0 | 3 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B2_C3_P4 | baseline | - | 767.71 | 728.89 | 0.972 | 1 | 591.0 | 93.0 | 1.244 | 7 | 23 | 0 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B2_C4_P4 | baseline | - | 767.95 | 728.89 | 0.972 | 1 | 591.0 | 93.0 | 1.244 | 7 | 23 | 0 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B4_C1_P4 | baseline | - | 733.47 | 693.15 | 0.972 | 1 | 577.5 | 72.0 | 0.587 | 7 | 0 | 0 | 8 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B4_C3_P4 | baseline | - | 734.22 | 693.40 | 0.972 | 1 | 577.5 | 72.0 | 0.836 | 7 | 0 | 0 | 8 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B4_C4_P4 | baseline | - | 734.46 | 693.40 | 0.972 | 1 | 577.5 | 72.0 | 0.836 | 7 | 0 | 0 | 8 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B6_C1_P4 | baseline | - | 735.06 | 692.75 | 0.972 | 1 | 577.5 | 72.0 | 0.178 | 7 | 0 | 0 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B6_C3_P4 | baseline | - | 735.55 | 692.75 | 0.972 | 1 | 577.5 | 72.0 | 0.178 | 7 | 0 | 0 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 0 | heat | B6_C4_P4 | baseline | - | 735.80 | 692.75 | 0.972 | 1 | 577.5 | 72.0 | 0.178 | 7 | 0 | 0 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | B | B1_C2_P4 | ILP | OPTIMAL | 658.32 | 620.74 | 0.861 | 5 | 456.0 | 3.0 | 0.942 | 6 | 79 | 8 | 3 | {} | 0.00000 | 93.0 | baseline_reserve | results.csv |
| 1 | B | B1_C2_P4 | baseline | - | 1176.52 | 1138.94 | 0.722 | 10 | 547.5 | 279.0 | 0.960 | 7 | 54 | 36 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | results.csv |
| 1 | B | B2_C2_P4 | ILP | OPTIMAL | 658.78 | 620.21 | 0.861 | 5 | 456.0 | 3.0 | 0.409 | 6 | 52 | 0 | 3 | {} | 0.00000 | 86.7 | default | results.csv |
| 1 | B | B2_C2_P4 | baseline | - | 1039.55 | 1000.97 | 0.806 | 7 | 564.0 | 213.0 | 1.120 | 7 | 19 | 11 | 5 | {} | - | 0.0 | - | results.csv |
| 1 | B | B3_C2_P4 | ILP | OPTIMAL | 659.60 | 620.03 | 0.861 | 5 | 456.0 | 3.0 | 0.231 | 6 | 46 | 4 | 5 | {} | 0.00000 | 79.5 | baseline_round1 | results.csv |
| 1 | B | B3_C2_P4 | baseline | - | 973.24 | 933.67 | 0.806 | 7 | 541.5 | 168.0 | 0.782 | 8 | 7 | 0 | 4 | {"(18)": 1} | - | 0.0 | - | results.csv |
| 1 | B | B4_C2_P4 | ILP | OPTIMAL | 660.37 | 619.80 | 0.861 | 5 | 456.0 | 3.0 | 0.000 | 6 | 0 | 2 | 6 | {} | 0.00000 | 80.7 | default | results.csv |
| 1 | B | B4_C2_P4 | baseline | - | 974.15 | 933.59 | 0.806 | 7 | 541.5 | 168.0 | 0.604 | 8 | 5 | 0 | 6 | {} | - | 0.0 | - | results.csv |
| 1 | B | B6_C2_P4 | ILP | OPTIMAL | 662.36 | 619.80 | 0.861 | 5 | 456.0 | 3.0 | 0.000 | 7 | 0 | 7 | 11 | {} | 0.00000 | 95.8 | default | results.csv |
| 1 | B | B6_C2_P4 | baseline | - | 927.21 | 884.65 | 0.806 | 7 | 523.5 | 138.0 | 0.409 | 7 | 0 | 0 | 13 | {} | - | 0.0 | - | results.csv |
| 1 | C | B3_C1_P4 | ILP | OPTIMAL | 659.36 | 620.03 | 0.861 | 5 | 456.0 | 3.0 | 0.231 | 6 | 46 | 2 | 5 | {} | 0.00000 | 99.4 | baseline_reserve | results.csv |
| 1 | C | B3_C1_P4 | baseline | - | 972.73 | 933.41 | 0.806 | 7 | 541.5 | 168.0 | 0.516 | 8 | 8 | 0 | 3 | {"(17)": 1, "(18)": 1} | - | 0.0 | - | results.csv |
| 1 | C | B3_C3_P4 | ILP | OPTIMAL | 659.85 | 620.03 | 0.861 | 5 | 456.0 | 3.0 | 0.231 | 6 | 42 | 3 | 5 | {} | 0.00000 | 79.6 | default | results.csv |
| 1 | C | B3_C3_P4 | baseline | - | 973.61 | 933.80 | 0.806 | 7 | 541.5 | 168.0 | 0.907 | 8 | 7 | 0 | 5 | {} | - | 0.0 | - | results.csv |
| 1 | C | B3_C4_P4 | ILP | OPTIMAL | 660.09 | 620.03 | 0.861 | 5 | 456.0 | 3.0 | 0.231 | 6 | 39 | 4 | 5 | {} | 0.00000 | 86.5 | default | results.csv |
| 1 | C | B3_C4_P4 | baseline | - | 973.86 | 933.80 | 0.806 | 7 | 541.5 | 168.0 | 0.907 | 8 | 7 | 0 | 5 | {} | - | 0.0 | - | results.csv |
| 1 | P | B3_C4_P1.4 | baseline | - | 973.74 | 933.67 | 0.806 | 7 | 541.5 | 168.0 | 0.782 | 8 | 7 | 0 | 4 | {"(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | P | B3_C4_P2.8 | baseline | - | 973.86 | 933.80 | 0.806 | 7 | 541.5 | 168.0 | 0.907 | 8 | 7 | 0 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | P | B3_C4_P4.2 | baseline | - | 973.86 | 933.80 | 0.806 | 7 | 541.5 | 168.0 | 0.907 | 8 | 7 | 0 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | free | free | ILP | OPTIMAL | 657.99 | 620.74 | 0.861 | 5 | 456.0 | 3.0 | 0.942 | 6 | 79 | 3 | 3 | {} | 0.00007 | 129.8 | - | results.csv |
| 1 | free_fixed | free_fixed | ILP | OPTIMAL | 657.99 | 620.74 | 0.861 | 5 | 456.0 | 3.0 | 0.942 | 6 | 79 | 3 | 3 | {} | 0.00000 | 69.9 | chain:free | results.csv |
| 1 | free_fixed | free_fixed | baseline | - | 1175.98 | 1138.73 | 0.722 | 10 | 547.5 | 279.0 | 0.747 | 7 | 68 | 36 | 0 | {"(17)": 3, "(18)": 1} | - | 0.0 | - | results.csv |
| 1 | heat | B1_C1_P4 | baseline | - | 1176.28 | 1138.94 | 0.722 | 10 | 547.5 | 279.0 | 0.960 | 7 | 54 | 36 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B1_C3_P4 | baseline | - | 1176.77 | 1138.94 | 0.722 | 10 | 547.5 | 279.0 | 0.960 | 7 | 54 | 36 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B1_C4_P4 | baseline | - | 1177.01 | 1138.94 | 0.722 | 10 | 547.5 | 279.0 | 0.960 | 7 | 54 | 36 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B2_C1_P4 | baseline | - | 1038.98 | 1000.65 | 0.806 | 7 | 564.0 | 213.0 | 0.800 | 7 | 29 | 11 | 3 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B2_C3_P4 | baseline | - | 1039.79 | 1000.97 | 0.806 | 7 | 564.0 | 213.0 | 1.120 | 7 | 19 | 11 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B2_C4_P4 | baseline | - | 1040.04 | 1000.97 | 0.806 | 7 | 564.0 | 213.0 | 1.120 | 7 | 19 | 11 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B4_C1_P4 | baseline | - | 973.75 | 933.43 | 0.806 | 7 | 541.5 | 168.0 | 0.444 | 8 | 6 | 0 | 5 | {"(17)": 1, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B4_C3_P4 | baseline | - | 974.52 | 933.71 | 0.806 | 7 | 541.5 | 168.0 | 0.729 | 8 | 5 | 0 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B4_C4_P4 | baseline | - | 974.86 | 933.80 | 0.806 | 7 | 541.5 | 168.0 | 0.818 | 8 | 5 | 0 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B6_C1_P4 | baseline | - | 926.80 | 884.49 | 0.806 | 7 | 523.5 | 138.0 | 0.249 | 7 | 0 | 0 | 12 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B6_C3_P4 | baseline | - | 927.60 | 884.80 | 0.806 | 7 | 523.5 | 138.0 | 0.551 | 7 | 0 | 0 | 13 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 1 | heat | B6_C4_P4 | baseline | - | 927.92 | 884.87 | 0.806 | 7 | 523.5 | 138.0 | 0.622 | 7 | 0 | 0 | 13 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | B | B1_C2_P4 | ILP | OPTIMAL | 637.93 | 600.35 | 0.889 | 4 | 465.0 | 3.0 | 1.049 | 7 | 104 | 6 | 3 | {} | 0.00005 | 80.5 | baseline_reserve | results.csv |
| 2 | B | B1_C2_P4 | baseline | - | 822.06 | 784.48 | 0.806 | 7 | 477.0 | 84.0 | 1.209 | 8 | 68 | 12 | 2 | {"(17)": 1} | - | 0.0 | - | results.csv |
| 2 | B | B2_C2_P4 | ILP | OPTIMAL | 638.21 | 599.64 | 0.889 | 4 | 465.0 | 3.0 | 0.480 | 6 | 47 | 5 | 3 | {} | 0.00000 | 71.6 | default | results.csv |
| 2 | B | B2_C2_P4 | baseline | - | 765.75 | 727.18 | 0.833 | 6 | 474.0 | 60.0 | 1.138 | 7 | 23 | 1 | 5 | {} | - | 0.0 | - | results.csv |
| 2 | B | B3_C2_P4 | ILP | OPTIMAL | 638.98 | 599.41 | 0.889 | 4 | 465.0 | 3.0 | 0.249 | 6 | 22 | 2 | 5 | {} | 0.00000 | 77.3 | default | results.csv |
| 2 | B | B3_C2_P4 | baseline | - | 790.12 | 750.55 | 0.806 | 7 | 462.0 | 66.0 | 0.800 | 7 | 4 | 1 | 6 | {} | - | 0.0 | - | results.csv |
| 2 | B | B4_C2_P4 | ILP | OPTIMAL | 639.73 | 599.16 | 0.889 | 4 | 465.0 | 3.0 | 0.000 | 6 | 0 | 5 | 6 | {} | 0.00000 | 79.8 | default | results.csv |
| 2 | B | B4_C2_P4 | baseline | - | 790.89 | 750.32 | 0.806 | 7 | 462.0 | 66.0 | 0.569 | 7 | 0 | 1 | 8 | {} | - | 0.0 | - | results.csv |
| 2 | B | B6_C2_P4 | ILP | OPTIMAL | 641.72 | 599.16 | 0.889 | 4 | 465.0 | 3.0 | 0.000 | 6 | 0 | 10 | 12 | {} | 0.00000 | 89.6 | default | results.csv |
| 2 | B | B6_C2_P4 | baseline | - | 792.44 | 749.88 | 0.806 | 7 | 462.0 | 66.0 | 0.124 | 7 | 0 | 1 | 11 | {} | - | 0.0 | - | results.csv |
| 2 | C | B3_C1_P4 | ILP | OPTIMAL | 638.73 | 599.41 | 0.889 | 4 | 465.0 | 3.0 | 0.249 | 6 | 23 | 5 | 5 | {} | 0.00000 | 75.2 | default | results.csv |
| 2 | C | B3_C1_P4 | baseline | - | 789.65 | 750.32 | 0.806 | 7 | 462.0 | 66.0 | 0.569 | 7 | 6 | 1 | 5 | {} | - | 0.0 | - | results.csv |
| 2 | C | B3_C3_P4 | ILP | OPTIMAL | 639.22 | 599.41 | 0.889 | 4 | 465.0 | 3.0 | 0.249 | 6 | 21 | 6 | 5 | {} | 0.00000 | 74.0 | default | results.csv |
| 2 | C | B3_C3_P4 | baseline | - | 790.41 | 750.59 | 0.806 | 7 | 462.0 | 66.0 | 0.836 | 7 | 4 | 1 | 7 | {} | - | 0.0 | - | results.csv |
| 2 | C | B3_C4_P4 | baseline | - | 790.65 | 750.59 | 0.806 | 7 | 462.0 | 66.0 | 0.836 | 7 | 4 | 1 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | P | B3_C4_P1.4 | baseline | - | 790.62 | 750.55 | 0.806 | 7 | 462.0 | 66.0 | 0.800 | 7 | 4 | 1 | 6 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | P | B3_C4_P2.8 | baseline | - | 790.65 | 750.59 | 0.806 | 7 | 462.0 | 66.0 | 0.836 | 7 | 4 | 1 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | P | B3_C4_P4.2 | baseline | - | 790.65 | 750.59 | 0.806 | 7 | 462.0 | 66.0 | 0.836 | 7 | 4 | 1 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | free | free | ILP | OPTIMAL | 637.63 | 600.05 | 0.889 | 4 | 465.0 | 3.0 | 0.853 | 6 | 62 | 6 | 3 | {} | 0.00002 | 169.6 | - | results.csv |
| 2 | free_fixed | free_fixed | ILP | OPTIMAL | 637.63 | 600.05 | 0.889 | 4 | 465.0 | 3.0 | 0.853 | 6 | 62 | 6 | 3 | {} | 0.00004 | 50.2 | chain:free | results.csv |
| 2 | free_fixed | free_fixed | baseline | - | 908.86 | 871.28 | 0.722 | 10 | 448.5 | 111.0 | 0.782 | 7 | 69 | 1 | 1 | {"(17)": 2, "(18)": 1} | - | 0.0 | - | results.csv |
| 2 | heat | B1_C1_P4 | baseline | - | 821.82 | 784.48 | 0.806 | 7 | 477.0 | 84.0 | 1.209 | 8 | 68 | 12 | 2 | {"(17)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B1_C3_P4 | baseline | - | 822.31 | 784.48 | 0.806 | 7 | 477.0 | 84.0 | 1.209 | 8 | 68 | 12 | 2 | {"(17)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B1_C4_P4 | baseline | - | 822.55 | 784.48 | 0.806 | 7 | 477.0 | 84.0 | 1.209 | 8 | 68 | 12 | 2 | {"(17)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B2_C1_P4 | baseline | - | 765.17 | 726.84 | 0.833 | 6 | 474.0 | 60.0 | 0.800 | 7 | 28 | 1 | 2 | {"(17)": 1, "(18)": 1} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B2_C3_P4 | baseline | - | 766.00 | 727.18 | 0.833 | 6 | 474.0 | 60.0 | 1.138 | 7 | 23 | 1 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B2_C4_P4 | baseline | - | 766.25 | 727.18 | 0.833 | 6 | 474.0 | 60.0 | 1.138 | 7 | 23 | 1 | 5 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B4_C1_P4 | baseline | - | 790.54 | 750.22 | 0.806 | 7 | 462.0 | 66.0 | 0.462 | 7 | 0 | 1 | 7 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B4_C3_P4 | baseline | - | 791.21 | 750.39 | 0.806 | 7 | 462.0 | 66.0 | 0.640 | 7 | 0 | 1 | 8 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B4_C4_P4 | baseline | - | 791.45 | 750.39 | 0.806 | 7 | 462.0 | 66.0 | 0.640 | 7 | 0 | 1 | 8 | {} | - | 0.2 | - | baseline_fill_2026-10-12 |
| 2 | heat | B6_C1_P4 | baseline | - | 792.19 | 749.88 | 0.806 | 7 | 462.0 | 66.0 | 0.124 | 7 | 0 | 1 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B6_C3_P4 | baseline | - | 792.68 | 749.88 | 0.806 | 7 | 462.0 | 66.0 | 0.124 | 7 | 0 | 1 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |
| 2 | heat | B6_C4_P4 | baseline | - | 792.93 | 749.88 | 0.806 | 7 | 462.0 | 66.0 | 0.124 | 7 | 0 | 1 | 11 | {} | - | 0.0 | - | baseline_fill_2026-10-12 |

## Solver statistics

- ILP runs: 29 (29 stored; none re-solved here); statuses {'OPTIMAL': 28, 'TIME_LIMIT': 1}; TIME_LIMIT count 1 (seed 0 B1_C2_P4, 300.1 s, MIP gap 0.29 %); binaries 1,044,945-1,154,981 (arcs 1,044,906-1,154,942, rows 60,032-63,124); solve time mean 109.5 s, median 89.6 s, max 300.1 s; MIP gap max 0.0029, mean 0.00012; arc build mean 2.24 s; model build mean 4.33 s; evaluate.check passes on all: True; identity (24): True; MIP start accepted 25 of 26 runs with a start (rejected: seed 0 B1_C2_P4 default start); start variants {'default': 19, nan: 3, 'chain:free': 3, 'baseline_reserve': 3, 'baseline_round1': 1}; Gurobi Threads 3, TimeLimit 300 s, wall 57.6 min, 20 (seed, size) variants skipped by the 58 min wall budget.
- baseline runs: 72 (26 stored + 46 filled 2026-10-12 with the same R2.3 policy and library; reproduction check of stored seed 0 B3_C2_P4: |diff| = 0.00e+00 USD); runtime < 10 ms each; identity (24) holds on all: True; report-only families observed: ['{"(17)": 1, "(18)": 1}', '{"(17)": 1}', '{"(17)": 2, "(18)": 1}', '{"(17)": 3, "(18)": 1}', '{"(18)": 1}', '{}']; ILP <= baseline on every (seed, size) with both rows: True (violations []).

## Figures (regenerated 2026-10-12 from the CSVs with matplotlib Agg)

- `cost_vs_B.png` -- (a) total cost vs B_j with min-max band over seeds, (b) served share, (c) empty-stock site-slots; ILP and baseline, 3 seeds per point.
- `cost_vs_C.png` -- same panels vs C_j; ILP at C_j = 4 is seeds 0-1 only (annotated n = 2), baseline C_j = 4 has 3 seeds after the fill.
- `cost_vs_P.png` -- baseline only (filled rows) plus the certified flat ILP bound (dashed) and the stored ILP cell at 4 kW (n = 2); the ILP P sweep was not solved.
- `heatmap_BxC.png` -- B x C grid at P_j = 4 kW: ILP on the two sweep lines only (8 cells), baseline on all 20 cells (3 seeds each); cells show mean total cost, served share and n.

The previous versions of `cost_vs_C.png` / `heatmap_BxC.png` / `RESULTS.md` (17:44 run) showed a jump of the baseline at C_j = 4 (853.8 USD, 0.889 served) and of the ILP served share (0.917); both were seed-set artefacts (C_j = 4 had seeds 0-1 only) and are gone once seed 2 is filled (baseline 832.74) or the n = 2 is annotated (ILP).

## Anomalies

1. **Wall budget cut 20 of 49 planned ILP variants**: the P sweep was never solved, the B x C grid has ILP values only on the two sweep lines, and C_j = 4 has ILP seeds 0-1 only. Baseline cells were completed with the policy on 2026-10-12 (no solver); ILP conclusions for P_j rest on the sandwich bound above, and for the off-line B x C cells on monotonicity (the ILP operational cost is exactly independent of C_j on the B_j = 3 line, so the same is expected on the other rows, but it was not solved).
2. **Seed-set artefact in the 17:44 outputs**: the baseline "jump" at C_j = 4 (853.8 vs 832.2) and the ILP served share 0.917 at C_j = 4 were caused by seed 2 missing from that cell; the seed-2 baseline fill gives 790.65 (flat line, 832.74 mean). The original figures/RESULTS.md must not be quoted for C_j = 4.
3. **One TIME_LIMIT**: seed 0 B1_C2_P4 ILP stopped at 300.1 s with MIP gap 0.29 % (<= 1.8 USD) after its default MIP start was rejected (the R2.3 schedule violated a report-only family and no clean fallback was found: `mip_start_accepted = False`); this is the only ILP row with total above the B_j = 2 row of the same seed by more than the setup difference (616.42 vs 614.42, setup difference 1.00), so part of the 1.0 USD operational excess at B_j = 1 may be solver slack.
4. **ILP marginal values are negative beyond one spare per site** (-0.26, -0.25, -0.31 USD per battery per window at 2 -> 3, 3 -> 4, 4 -> 6, CI excludes 0) because the holding cost bB = 0.332 is paid for batteries that are never used (idle-full share 0.70 -> 1.00); only 1 -> 2 is positive (+0.14 ± 1.14, not significant). The ILP's cost-minimising size on the sweep is B_j = 2 (637.14) but within 0.4 USD of B_j = 1.
5. **Non-monotone baseline in B_j**: 3 -> 4 spares costs the baseline 0.27 USD per battery per window (slightly more electricity, same service), while 4 -> 6 saves 2.44 per battery (lateness 102 -> 92): the DEMAND_AWARE / stock-aware rules react discontinuously to stock levels. Seed variance is large (baseline total CI ± 312 USD; seed 1 carries 279 USD of lateness at B_j = 1), so the baseline marginal values carry wide CIs (48.5 ± 77.6 at 1 -> 2).
6. **Chargers are worthless for both methods**: the ILP operational cost is identical to 1e-9 for C_j = 1, 2, 3 on all seeds (the seed 0 C_j = 4 run is 0.053 USD above its C_j = 1 value, inside the 1e-4 relative MIP tolerance of 0.06 USD); the baseline's operational marginal value is -0.085 / -0.030 / 0.000 per charger (more chargers -> more electricity bought for batteries that are not swapped). Total cost rises by bC = 0.082 per charger per site for the ILP exactly.
7. **A tighter power cap slightly helps the baseline**: at P_j = 1.4 kW the baseline buys less electricity (C_elec 0.85 vs 0.94) at unchanged service (-0.021 USD per kW per window), but on seed 1 it then ends the window violating the report-only network target (18) (end full 4 < 0.5 x 9); peak group power never exceeds 3.33 kW (ILP) / 3.33 kW (baseline) against the 6-8 kW group limit (21), which therefore never binds.
8. **Baseline at the ILP-chosen lean sizes collapses**: with 3-4 batteries and 2-3 chargers in the network the baseline serves 0.722 on seeds 1-2 (total 1176 / 909 USD, gap 44.0 / 29.8 %), far worse than at the default sizes (973 / 790): the ILP's sizing is only cheap under coordinated operation.
9. **Unserved orders include structurally unservable ones** (review F5: usd4h seed 0 order 35 has no delivery arc), and under usd_sunk the ILP itself drops 4-5 orders on seeds 1-2 because P = 30 USD is below the waiting cost of late orders; the service-level comparison is therefore between two cost-optimal drop policies, not against 100 % service.
10. **Pruned-arc fallbacks in the baseline** (review F4): every seed-0 fill row (13 of 47, including the reproduction run) records exactly 1 pruned-arc fallback -- the known seed-0 bike stranded at slot 47 with no feasible reposition arc (review F4, usd4h seed 0); seeds 1-2 record 0. The stored rows do not export this count, and the fallback does not change the seed-0 cost (reproduction 733.098 = stored).
11. **Annualised figures** (x 1460) assume every 4 h window of a 16 h day all year looks like the dinner peak; they are an upper-bound convention from the task, not a forecast.

## Interpretation (with round-1 comparison)

1. Under USD prices and a 4 h window, the coordinator buys very little station: the free-size ILP keeps 3-4 spare batteries and 2-3 chargers in the whole network (vs 9 and 6 at the R2.2 default), leaves at least one site without a charger in every seed, and saves only 1.3-1.6 USD per window by doing so, because bB = 0.332 and bC = 0.082 per site per window are tiny next to the order-side costs (response 456-524 USD, unserved 30-150 USD).
2. The ILP's cost is flat in every sizing dimension: operational cost 600.0 / 598.6 / 598.3 / 598.1 / 598.0 USD at B_j = 1 / 2 / 3 / 4 / 6, identical across C_j = 1-4, and certified flat in P_j down to 1.4 kW; stock-outs fall from 104 to 0 empty site-slots as B_j grows but never cost an order because the ILP routes bikes to the site that has stock when it needs it.
3. In round 1 (toy units, 2 h, stressed q0 3-6/12) the ILP had a clear knee at two spares per site (operational 644 -> 458 toy units, 61.9 per battery) and the free-size run bought 5-7 batteries; in round 2 that knee has disappeared for the ILP (one spare per site already suffices) and moved to the baseline, which gains 48.5 USD per battery per window (about 70,800 USD per battery-year at 1460 windows) from the first extra spare and 8.5 USD from the second, then nothing.
4. "Chargers worthless" survives the change of units and rules exactly as in round 1: for the ILP the marginal operational value of a charger is 0.000 on all seeds and the total rises by bC per charger; for the R2.3 baseline it is slightly negative (-0.03 to -0.08 USD per charger per window), whereas the round-1 ASAP baseline still wanted a second charger (7.6 toy units); the demand-aware charging rule has removed that need.
5. The site power limit (20) and the grid group limit (21) never bind on this family (peak group draw <= 3.33 kW against 6-8 kW; at most 2 simultaneous chargers per site are ever useful), so the marginal value of a kW is 0 for the ILP and -0.02 USD per kW per window for the baseline, which simply wastes less electricity when capped.
6. The headline gap at the default sizes is 22.5 ± 21.3 % (16.1 / 32.2 / 19.1 % per seed, 194 USD per window) and is dominated by the baseline's lateness (97 USD), dropped orders (50 USD, 1.67 orders) and response time (45.5 USD); travel and electricity contribute under 2 USD, as in round 1 where the gap was almost entirely unserved orders at P = 100.
7. The gap shrinks with spares (36.4 % at B_j = 1 -> 21.7 % at B_j = 6) only because the baseline improves; the value of coordination is therefore largest exactly where stations are lean, which is where the ILP would size them.
8. The baseline cannot buy its way to the ILP's service level: on seeds 1 and 2 it serves 0.806 at every B_j in {1, ..., 6} against 0.861 / 0.889 for the ILP at B_j = 3 (it does not even reach the ILP's B_j = 1 level), and on no seed does it reach the ILP's total cost at any B_j <= 6 (best 735 / 927 / 792 vs 615 / 660 / 639); round 1 had the same qualitative result (baseline needed B_j = 4 to approach the ILP at B_j = 2 in cost, service unreachable).
9. Seed heterogeneity is the main statistical caveat: with n = 3 the baseline's CIs span ± 312 USD because seed 1 (0.722-0.806 served, 279 USD lateness at B_j = 1) is much harder than seed 0 (0.972 served); the ILP's CIs (± 55 USD) are narrower, and every paired difference used for the marginal values is computed within seed.
10. For the paper, the sizing message is therefore: under realistic USD coefficients station capital is not the lever, coordination is -- one spare per site and one charger (or none) per site are enough for a coordinated fleet, while an uncoordinated fleet needs two to three spares per site and still serves 5-8 percentage points fewer orders; the remaining gaps in the evidence are the unsolved ILP P sweep and off-line B x C cells (a 60-90 min re-run at Threads 3 would close them).

## Files

- `RESULTS_final.md` (this file), `results.csv` (stored, unchanged), `results_baseline_fill.csv` (new baseline-only rows), `_tables_final.md` / `_summary_final.json` (intermediate tables and numbers), `cost_vs_B.png`, `cost_vs_C.png`, `cost_vs_P.png`, `heatmap_BxC.png` (regenerated). The original `RESULTS.md`, `summary_*.csv`, `spares_to_match.csv`, `gap_decomposition.csv` from the 17:44 run are kept as written by the script; where they disagree with this file (C_j = 4 cells) this file is authoritative.
