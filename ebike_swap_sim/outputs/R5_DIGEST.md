# Round 5 digest: answers to the manuscript research questions

Date: 2026-10-18. Inputs: the seven round-5 final reports (X1-X7), their records, and a two-refuter verification
pass on 42 claims. Where both refuters refuted a claim, the numbers were recomputed from the records (no solves) and
the corresponding `RESULTS_final.md` was corrected. Each corrected report ends with a "Digest corrections" section;
pre-edit copies are in the session scratchpad. All nine round-5 commands exited 0 (logs in `outputs/r5_lanes/`).

Conventions (all experiments): aggregated E2 ILP (O1), Gurobi Threads 3, Seed 0. Gap = 100 (baseline - ILP) /
baseline per instance, then averaged. Baseline `best_rule` = per-instance minimum over r2, r5_range, r5 (and
r5_transfer where services exist). Headline = like-for-like relaxed end targets (rho = 0, R_end = 0) scored on the
end-adjusted cost (`total + C_end_adjust`) unless stated. Written M1 targets give the price of recovery. Intervals
are exact Student-t 95 % CIs over seeds or scenarios, written as `[lo, hi]` or `± half-width`. The last record per
key is used everywhere; no experiment has duplicate keys.

Report paths (all under `ebike_swap_sim/outputs/`):

| id | experiment | report |
|---|---|---|
| X1 | headline re-validation | `r5_x1_headline/RESULTS_final.md` |
| X2 | transfers, hub separation | `r5_x2_transfers/RESULTS_final.md` |
| X3 | rolling horizon, foresight vs coordination | `r5_x3_rolling/RESULTS_final.md` |
| X4 | value of the swap network vs home charging | `r5_x4_network/RESULTS_final.md` |
| X5 | stressed family, boundary grid, fleet sweep, levers | `r5_x5_stress/RESULTS_final.md` |
| X6 | Manhattan-wide siting, compliance | `r5_x6_manhattan/RESULTS_final.md` |
| X7 | RL comparator | `r5_x7_rl/RESULTS_final.md` |

## Coverage

| id | records / keys | ILP status | skipped / errors |
|---|---|---|---|
| X1 | 640 / 640 | eBaaS ILP 80/80 OPTIMAL (max gap 9.6e-5); legacy rows (copied round 3) written 38 OPT + 2 TL (0.036 %, 0.114 %), relaxed 40 OPT | 0 / 0 |
| X2 | 390 / 390 | 79 OPT, 11 TL (all written, transfers-free, separated; 10 r3 at 0.92-2.28 %, 1 cyclic at 0.47 %); all relaxed OPT | 0 / 0 |
| X3 | 210 / 210 | relaxed phase complete: offline usd 10/10 OPT, r5 4 OPT + 1 TL (0.09 %); written partial (usd 5 OPT; r5 1 OPT + 4 TL at 0.30-2.52 %) | 56 SKIPPED_BUDGET (phases B/C, by design) / 0 |
| X4 | 180 / 180 | 42 OPT, 3 TL (r5 network written, 0.30-0.79 %); all relaxed headline OPT; 15 home written rows implied by construction | 0 / 0 |
| X5 | 241 cases | core 9 OPT / 16 TL (0.17-3.23 %); boundary 11 OPT / 10 TL / 1 TL without incumbent; fleet 23 OPT / 1 TL; levers 8 OPT / 13 TL (0.14-1.37 %); all 80 incumbents pass check | 5 boundary SKIPPED_BUDGET / 0 |
| X6 | 6 stages | written 66 unique (47 OPT, 18 TL, 1 INFEASIBLE_ILP); relaxed 21 (20 OPT, 1 TL); TL gaps 0.39-2.75 %; selfish equilibria 82/84 converged (2 hit the 10-iteration cap) | 14 SKIPPED_BUDGET stage rows; 4 of 6 stages truncated / 0 |
| X7 | 284 / 284 | nyc4h_stress2 relaxed and written 10/10 OPT; r5_stress4h relaxed 3 OPT + 7 TL (0.13-1.64 %), written 1 OPT + 9 TL (0.35-2.52 %); 4/4 PPO trainings complete | 0 / 0 |

## Verification outcome

41 claims were checked by two refuters each. 21 survived both. 14 were refuted by both refuters and corrected in the
reports: X1 C2, C6; X3 C2, C3, C6; X4 C4; X5 C3, C4, C6; X6 C3, C4, C5; X7 C2, C5. Three of these also needed an
extra recomputation that settled the refuters' disagreement: the X1 per-instance Shapley CIs, the X7 instance-adjusted
training trend (instance order reconstructed from the seeded draw; it matches the second refuter exactly), and the X6
selfish-equilibrium convergence count. 6 claims were refuted by one refuter only (X3 C1, C5; X4 C3; X5 C1, C2; X6 C2). For
these, qualifiers were added where cheap (X3 C5, X5 C1); the rest are carried as caveats below. One factual error
not raised as a claim was also fixed: X6 said all selfish equilibria converged, but 2 did not.

---

## RQ1. Value of coordination (ILP vs the conservative best rule)

**Answer.** Coordination cuts the end-adjusted window cost by about 27 % on the base families. This survives all
three round-5 fairness corrections, holds on every instance, and every ILP is proved optimal. The gain rises steeply
with congestion and battery stress, to 40-48 % on the stressed family, and it carries over to a Manhattan-wide
instance (32-34 %). Almost all of the saving is service quality (lateness, response, unserved orders), not energy.

| family (source) | n | gap vs best_rule, relaxed, end-adjusted | ILP status |
|---|---|---|---|
| usd4h, pooled x0.75/x1/x1.5 (X1) | 30 | **27.17 % ± 5.96** (30/30 > 0; min 5.29 %) | 30/30 OPT |
| usd4h x0.75 / x1 / x1.5 (X1) | 10 each | 9.78 ± 2.88 / 28.28 ± 7.36 / 43.45 ± 5.86 % | OPT |
| nyc4h (X1; lower bound, PRUNING_NYC) | 10 | **≥ 27.37 % ± 7.11** (10/10 > 0) | OPT |
| E3u layouts, usd4h seeds 0-4 (X2) | 15 | 20.98 % [16.59, 25.36] | OPT |
| r5_stress4h, 6 bikes / 48 orders (X5 core) | 5 | 40.05 % [33.68, 46.41] (end-adj. 39.96) | 5 OPT |
| r5_stress4h, 8 bikes / 64 orders (X5) | 5 | 45.58 % [40.83, 50.32] (vs bound 45.85) | 2 OPT / 3 TL ≤ 1.25 % |
| r5_stress4h, 10 bikes / 80 orders (X5) | 5 | 46.99 % [43.09, 50.88] (vs bound 47.76) | 5 TL ≤ 1.93 % |
| r5_stress8h, 6 bikes / 96 orders (X5) | 3 | 47.96 % [13.66, 82.26] (seeds 32.2 / 53.6 / 58.0) | 3 TL ≤ 1.49 % |
| r5_stress4h, seeds 0-9 (X7, 120 s limit) | 10 | 41.30 % ± 2.61 (41.61 ± 2.76 vs bound) | 3 OPT / 7 TL |
| nyc4h_stress2 (X7; lower bound, pruning) | 10 | 28.97 % ± 7.27 | 10 OPT |
| Manhattan, bi-level layout (X6) | 3 scen. | 31.8 % [23.1, 40.5] | OPT |
| Manhattan, 7 layouts pooled (X6) | 21 cells | 34.3 % [30.7, 37.8] (scenario-clustered [20.8, 47.7], n = 3) | 20 OPT / 1 TL |

Note: X1 usd4h x1, X3 usd4h_ebaas and the X4 network cell use the same 10 instances (28.28 % end-adjusted, 28.37 %
raw). They are one result, not three.

Survival of the round-3 gain (X1, Table 1-2 and the corrected Shapley table):
- usd4h: 29.55 % ± 5.61 → 27.17 % ± 5.96 (survival 0.92); paired S4 - S0 = -2.38 ± 2.25 pts (15/30 instances lower).
- nyc4h: 31.82 % ± 8.19 → 27.37 % ± 7.11 (survival 0.86); paired -4.46 ± 2.41 pts (9/10 lower).
- Shapley (per-instance, ± 95 % t), usd4h: calibration a = -0.41 ± 1.83, best-rule baseline b = -1.93 ± 0.76,
  relaxed targets c1 = +0.04 ± 0.01, end adjustment c2 = -0.08 ± 0.01.
  nyc4h: a = -2.20 ± 1.90, b = -2.20 ± 1.09 (a - b = 0.00 ± 1.97), c1 = +0.04, c2 = -0.09.
  **Corrected:** b dominates only on pooled usd4h (81 % of the loss). On nyc4h, and at usd4h x1 (a -1.35 vs b -1.51),
  the two contribute about equally. The small pooled a is a cancellation: x0.75 -2.22 ± 4.91, x1 -1.35 ± 2.70,
  x1.5 +2.34 ± 1.24.
- By demand: survival 0.64 (x0.75; paired -5.58 ± 5.86), 0.91 (x1; -2.91 ± 3.20), 1.03 (x1.5; +1.33 ± 1.17).
- The best rule is r5_range in 23/40 cells and r2 in 17/40. r5 = r5_range everywhere (no services).

Where the saving comes from (X1 Table 4, best rule - ILP, USD per 4-h window):
- usd4h: 364.22 ± 133.98 in total. Lateness 183.80 ± 75.04 (50.5 %), response 96.15 ± 36.90 (26.4 %), unserved
  83.00 ± 37.75 (22.8 %), travel 1.05 (0.3 %), electricity 0.66 (0.2 %), end adjustment -0.44.
- nyc4h: 240.98 ± 95.41. Lateness 49.1 %, response 34.3 %, unserved 16.2 %.
- Service terms are at least 93 % of the saving on every instance.
- Late orders: 13.30 → 0.40 (usd4h) and 14.70 → 0.80 (nyc4h). Served share +0.06 ± 0.02 and +0.04 ± 0.03.

Mechanism (X1 metric pack; **corrected**):
- The ILP takes shorter detours per swap: -0.39 ± 0.13 km (usd4h) and -0.42 ± 0.18 km (nyc4h).
- It swaps significantly less only on usd4h: -1.37 ± 0.71 swaps (nyc4h -0.50 ± 1.23, not significant).
- Its lower in-window energy purchase (-2.05 kWh) and peak load (-1.38 kW) are mostly recharging deferred past the
  window, which R_end = 0 allows. C_end_adjust rises by +0.44 / +0.50 USD against an electricity saving of
  0.66 / 0.65 USD, so this must not be reported as a grid benefit.
- It accepts a lower BSR (0.92 → 0.74; 0.86 → 0.53) and longer station waits (nyc4h 10.4 → 23.2 min per swap, mostly
  deliberate parking).

Sources: X1 report Tables 1-5 and corrected Shapley table; `r5_x1_headline/per_instance_final.csv`,
`stages_final.csv`, `metric_pack_ci_final.csv`; X5 report §1; X6 Table 3; X7 Table 1.

## RQ2. Foresight vs coordination (X3)

**Answer.** The offline headline is mostly coordination, not perfect foresight. A rolling-horizon ILP that sees
orders 10 min before release and re-plans every 30 min keeps 64 % (usd4h_ebaas) to 77 % (r5_stress4h) of the
best-rule-to-offline gap, and it is cheaper than the best rule on all 15 instances. Two things make these shares
upper bounds: the online runs use an unpriced terminal fallback, and part of the online gain is order admission.

Cost per 4-h window (relaxed, end-adjusted, USD):

| method | usd4h_ebaas (n = 10) | r5_stress4h, 6 bikes (n = 5) |
|---|---|---|
| best rule | 830.91 [721.74, 940.07] | 1387.36 [1173.65, 1601.07] |
| rolling, lambda 0 / 10 / 20 | 689.95 / 648.64 / 620.10 | 1027.95 / 944.07 / 948.44 |
| rolling + forecast battery plan, lambda 10 | 641.88 | 934.37 |
| offline ILP | 582.05 [563.65, 600.45] | 826.10 [771.60, 880.60] |

Decomposition at lambda 10 (headline gap = foresight + online coordination):
- Offline gap: 28.28 % [20.91, 35.64] (usd) and 39.96 % [33.58, 46.35] (r5).
- Online coordination (best rule - rolling): 182.27 USD [80.50, 284.04] = 19.94 % [10.76, 29.12] of the best rule
  (usd); 443.29 USD [250.53, 636.04] = 31.26 % [21.82, 40.70] (r5).
- Foresight (rolling - offline): 66.59 USD [43.25, 89.92] = 8.33 % [5.21, 11.46] of the best rule (usd);
  117.97 USD [73.13, 162.82] = 8.70 % [4.72, 12.69] (r5).
- Share of the gap kept online (mean of per-seed ratios): 0.64 [0.44, 0.83] (usd) and 0.77 [0.64, 0.90] (r5).
  Ratio of means: 0.73 and 0.79.
  **Qualifier (one refuter):** on usd4h the CI reaches below one half, 3/10 seeds keep less than half, and seed 0
  keeps 0.05.
- **Corrected:** foresight share of the gap = 0.36 [0.17, 0.56] (usd) and 0.23 [0.10, 0.36] (r5), mean of ratios.
  Ratio of means 0.27 and 0.21. Foresight is clearly the minor part on r5 (5/5 seeds) but only borderline on usd,
  where it exceeds coordination on 3/10 seeds.
- At lambda 0, foresight is 13.34 % (usd) and 14.66 % (r5) of the best rule. On usd it then equals online
  coordination (14.93 %; foresight share 0.57 [0.29, 0.85]).

Lookahead (**corrected**):
- lambda 0 → 10 helps on both families: usd 41.31 [22.62, 60.00], 9/10 seeds, p = 0.0007; r5 83.87 [48.77, 118.98],
  5/5 seeds, p = 0.003.
- lambda 10 → 20 is marginal on usd: 28.54 [2.17, 54.90], 7/10 seeds, t p = 0.04, Wilcoxon p = 0.06.
- On r5 no further gain is detected: -4.36 [-59.58, 50.85], 3/5 seeds improve. With n = 5 this neither shows nor
  rules out a plateau.
- Per-seed curves are monotone on only 6/10 (usd) and 3/5 (r5) seeds.
- The forecast battery plan has no detectable value: rolling - forecast = 6.75 USD [-8.32, 21.83] (usd) and
  9.71 USD [-8.95, 28.36] (r5). The test is underpowered; savings up to about 3 % are not excluded.

Admission effect (qualified):
- Rolling avoids almost all lateness: 5.7 vs 125.7 USD (paired 120.0 [53.2, 186.8], 10/10 seeds) and 5.4 vs
  273.6 USD (268.2 [163.8, 372.6], 5/5 seeds).
- Its lower served share is not significant per seed: usd 0.856 vs 0.919, paired 0.064 [-0.002, 0.130], p = 0.057;
  r5 0.729 vs 0.754, p = 0.47.

Price of recovery (**corrected**):
- Offline usd4h_ebaas, resolved (all OPTIMAL): -0.03 USD [-0.18, 0.12] end-adjusted and +0.29 [0.17, 0.40] on the
  objective.
- Offline r5_stress4h: 6.73 USD [-3.87, 17.33], within the MIP gaps.
- Online: not measured. The terminal fallback was used in 47/60 relaxed online runs (28/40 usd, 19/20 r5), so the
  written targets are not enforced there.

Source: X3 report T1-T5, `r5_x3_rolling/per_instance.csv`, `figs/x3_final_tables.json`.

## RQ3. When do batteries and stations bind?

**Answer.** At usd4h scale with B = 3 spares per site, the battery side does not bind within a 4-h window. The
relaxed ILP buys 0 kWh and moves 0 batteries in all 45 X2 solves. The battery side binds on the stressed family, and
more so as fleet and demand grow together. Coordination is worth most where fleet, demand and battery scarcity are
all highest, and coordination substitutes for battery hardware.

Evidence:
- Demand gradient (X1, usd4h): the gap is 9.78 / 28.28 / 43.45 % at x0.75 / x1 / x1.5.
- Stressed family (X5): the gap is 40.05 → 45.58 → 46.99 % at 6 → 8 → 10 bikes. 6 vs 10 bikes: Welch p = 0.04.
  8 vs 10: p = 0.54. Orders scale at 8 per bike, so fleet size and demand are confounded.
- LP operating value of one more spare (X5), relaxed, n = 5, USD per site and window: 0.45 [-0.00, 0.90] /
  2.79 [0.61, 4.98] / 21.87 [12.12, 31.62] at 6 / 8 / 10 bikes. The set-up cost is 0.332, so the value goes from
  about 1.4x cost to about 66x cost.
- One more charger (X5): 0.07 [-0.08, 0.21] / 1.29 [0.20, 2.38] / 16.67 [7.20, 26.15]. Set-up cost 0.082.
- Written targets raise both values: at 6 bikes 1.04 / 0.46; at 10 bikes on seed 0, 36.58 / 35.13.
- Served share, ILP vs rule (X5): 0.875 vs 0.754, 0.866 vs 0.631, 0.872 vs 0.573. Stock-out counts do not track
  service, because the ILP runs stock to zero on purpose (84.4 vs 70.8 slot-sites at 6 bikes).
- Fleet × spare × pack sweep (X5; 48 orders, 0.6 kWh, seeds 0-1, n = 2; **corrected**):
  - ILP: within the tested grid (K 4-8, B 1-4) the cost-minimal design is K4 B2 = 1310.1 USD (served 0.698).
    An extra bike saves 73-75 USD (from K4) or 33-34 USD (from K6), against 88.94 USD allocated per bike-window.
    An extra spare beyond 2 per site has negative net value (-0.29 to -0.35 USD).
  - Rule: best design K8 B4 = 1587.7 USD (served 0.990), 17.5 % above the ILP design (per seed 13.0 / 21.3 %).
  - At matched service (ILP K8 B2, 1448.8 USD, served 0.969) the ILP is 8.75 % cheaper.
  - Both optima lie on the edge of the grid.
  - Spares are not always the cheaper lever: for the rule at K4 B2 a spare has a net value of -9.33 (0.5 kWh) or
    -5.19 USD (0.6 kWh), while a bike saves 169-175 USD.
  - Pack size changes the rule's best system cost by about 100 USD (1587.7-1688.3).
- Station levers (X5; 8 bikes, n = 3; ILP):
  - Removing on-site charging (P = 0) raises cost by +79.23 USD [18.95, 139.50] (at least 51.8 on every seed).
    A demand charge would need at least 6,217 USD/kW-month to make P = 0 optimal.
  - Faster chargers (-5.00 [-14.57, 4.57]), a second swap position (-2.16 [-11.30, 6.99]) and lock-out of 1 or 2
    spares (-1.55 and -2.01) are all within the reference MIP gap (9.3 USD mean).
- Boundary (X5; **corrected scope**):
  - At 6 bikes the price of recovery is 3.20 USD [0.18, 6.21] = 0.38 % [0.02, 0.74] (mean proven lower bound 0.65).
    The gap moves by 0.22 [0.03, 0.40] pts.
  - M1 grid cells solved on all 3 seeds: at most 4.38 USD mean.
  - The price grows with fleet size: seed 0 gives 11.63 USD (1.17 %) at 8 bikes and 29.41 USD (true value in
    [0, 50.96]) at 10 bikes.
  - Periodic seed 2: proven price at least 11.73 USD.

Sources: X5 report §1-4 and Appendix B, `r5_x5_stress/figs/x5_frontier.csv`, `x5_per_instance.csv`; X2 report;
X1 Table 1.

## RQ4. Where to site stations (X6, with X2 for hub separation)

**Answer.** Layout rankings depend on how riders are operated. The truncated bi-level search did not beat rule siting
under its own ILP follower, so the manuscript cannot yet claim that bi-level siting beats rules. What it can claim is
that a layout chosen for a coordinated follower ranks differently under rule or selfish followers.

- Bi-level greedy + local search (k_screen 2, budget 125 min) priced only 4 layouts. It found nothing at m = 1 and
  returned M06:SC:B4:C2 + M12:S:B3:C0 (103,950 USD) at m = 2-4. M08, the densest cell, was never screened.
- Under the ILP follower with written targets, at m = 2:
  - Bi-level V = 703.1 vs CSCD (M08 + M09) 676.6 USD.
  - Paired gap -3.99 % [-8.74, 0.77]; per scenario -5.52 / -4.60 / -1.84.
  - Against the bi-level MIP lower bounds: -2.82 % [-5.00, -0.65].
  - On the relaxed control the two tie (675.01 vs 674.96). The whole difference is the recovery cost of the
    swap-only site M12:S (28.1 vs 1.6 USD).
- Follower dependence at m = 2 (**corrected**):
  - Under rule r2, bi-level is +12.73 % [9.86, 15.61] cheaper (12.0-14.1 % per scenario).
  - Under the selfish follower it is +5.69 % [-4.90, 16.28] cheaper. It is cheaper in all 3 scenarios but not
    significantly, and one comparator equilibrium did not converge.
  - Under the ILP it is dearer only with written targets.
- Capacity matched against the present-day proxy (M03 + M08, same 103,950 USD): ILP +2.79 % [-2.36, 7.94], r2 +7.07 %,
  selfish +2.31 %. None is significant.
- Marginal capacity at the bi-level layout (**corrected**):
  - Under the ILP, a spare at M06 changes V by -19.7 [-34.8, -4.6] USD (-12.1 [-15.8, -8.4] vs the lower bounds);
    a charger at M06 by -21.1 [-42.1, -0.0]. Both are negative in all 3 scenarios.
  - A second swap position gives no ILP gain beyond the MIP gap.
  - Under the selfish follower: spare +103.4 [-270.8, 477.6], charger +47.7 [-204.1, 299.4]. Every interval
    includes zero and the means are driven by scenario 0, so a Braess-type capacity paradox is suggested, not shown.
- Policy-aware (selfish-follower) siting ran out of its 30.7-min budget after 399 rule screens. It returned M07 at
  every budget. Its selfish V of 1224.4 [1184.4, 1264.5] is worse than the bi-level layout (1057.5) and CSCD m = 4
  (955.5).
- Hub separation (X2, usd4h, relaxed):
  - Separating hubs costs exactly the hub fixed charge: 29.00 USD [28.53, 29.48] vs 29.19 (1 hub) and
    58.04 [57.39, 58.70] vs 58.38 (2 hubs). The operating part is not significant.
  - Under written targets without transfers it costs 52.98 / 81.89 USD; with cyclic transfers 36.57 / 64.50 USD.
  - Siting chargers away from swap sites only pays if end-of-window recovery is enforced and transfers are cheap.

Sources: X6 Tables 1-6, Appendix B; X2 report; `r5_x6_manhattan/chosen_layout.json`.

## RQ5. Robustness to rider behaviour

**Answer.** The value of coordination needs riders to follow the plan, and the gain grows faster than
proportionally with compliance. When riders follow rule r2 or a selfish equilibrium on the same bi-level layout, V is
1020.8 or 1057.5 USD against 703.1 USD under the ILP (45-50 % more), and layout rankings change. The coordination gap is robust to the choice of rule
family: the per-instance best of r2 / r5_range already costs 1.9 pts of gap on usd4h, and no rule variant or
learned station layer closes the gap.

Compliance (X6, bi-level layout, written targets, 3 scenarios × 3 draws; **corrected**):
- V(alpha_c) for alpha_c = 0 / .25 / .5 / .75 / 1: 1165.0 [762.9, 1567.1] / 1081.1 [862.9, 1299.3] /
  998.6 [865.7, 1131.6] / 849.1 [640.8, 1057.4] / 703.1 [630.2, 776.0] USD.
- Share of the gap closed: 18.2 / 36.0 / 68.4 / 100 %. The mean curve is concave: savings accelerate with
  compliance.
- Scenario 1 is not monotone (1050.8 → 1059.9 from 0 to 0.25).
- The mean crosses the free-station selfish equilibrium (1057.5) at about alpha_c = 0.32 (between 0.25 and 0.5)
  and rule r2 (1020.8) at about 0.43.
- alpha_c = 0 (1165.0) costs more than the free-station selfish equilibrium, because the planned station inventory
  is wrong for non-compliant riders.
- Price of decentralisation (selfish - ILP written) on the bi-level layout: 354.3 [276.7, 432.0] USD per window.

Rule variants:
- The best rule is r5_range in 23/40 X1 cells.
- The r5 selfish variant is no better than best_rule (X7 nyc4h_stress2: 1009.40 vs 964.37; r5_stress4h: 1483.77 vs
  1441.08).

The rule baseline is not monotone in resources (X5; **corrected**): with P = 0 the rule's cost falls on all 3 seeds
(-209.8 [-448.2, 28.6]) while its served share falls from 0.635 to 0.448. Lock-out lowers its cost on 2 of 3 seeds.
None of this is significant at n = 3. The cause is that a late-served order costs about as much as an unserved one
(about 29.6 vs 29.9 USD).

Learned station control on rule riders: see the RL comparator below.

Sources: X6 Table 7 and Table 6; X7 Table 1; X5 levers table.

---

## Network value (X4)

Home charging (eBaaS-style, 125-min recharge) vs the swap network, best rule vs ILP, same demand, relaxed:
- Total effect (home + best rule → network + ILP): 474.3 USD [390.3, 558.3] = 44.3 % [39.6, 49.1] (usd4h_ebaas,
  n = 10); 822.2 [632.5, 1011.8] = 49.6 % [42.7, 56.6] (r5_stress4h, n = 5).
- Shapley split, usd4h_ebaas: network 175.1 [104.5, 245.6] (37 %), coordination 299.3 [247.0, 351.5] (63 %).
  r5_stress4h: 249.2 [93.2, 405.1] (30 %) and 573.0 [464.3, 681.7] (70 %).
- Coordination minus network: 124 [33, 216] USD (8/10 seeds) and 324 [133, 514] (5/5 seeds).
- Value of the network under the ILP (recommended headline): 17.7 % [16.2, 19.2] = 125.1 USD (10/10 seeds positive)
  and 22.5 % [19.4, 25.5] = 238.1 USD (5/5).
- Value of the network under the best rule: 20.4 % [7.5, 33.3], negative on seed 8 (-179.9 USD); and 15.3 %
  [-1.4, 31.9], not significant.
- Interaction (best rule): -99.9 [-242.6, 42.8] and -22.1 [-300.6, 256.3]. It cannot be told from zero.
- Productivity under the ILP: orders per rider-hour 1.43 [1.39, 1.47] vs 0.99 [0.93, 1.05] and 1.75 vs 1.00.
  Served share 0.953 vs 0.658 and 0.875 vs 0.500.
- Empty km per rider-hour rises, not falls: 0.75 vs 0.28 and 0.80 vs 0.30. The network buys rider time, not
  distance.
- Price of recovery on the network: 0.40 USD [0.30, 0.51] (0.07 %) and 3.22 [0.20, 6.24] (0.38 %, an upper bound;
  3/5 TL).
- **Corrected:** the X4 value of coordination on the network (28.37 % [21.01, 35.72]) is the X1 usd4h x1 cell again.
  Against the matched round-3 x1 instances (31.18 % ± 9.05) it is -2.82 ± 3.20 pts (p = 0.08, 7/10 lower). This is
  not significant, but it is a reduction in the point estimate, not agreement.

Source: X4 Tables 1-5, `r5_x4_network/figs/x4_decomposition_final.csv`.

## Transfers (X2)

- Relaxed targets: transfers are worth 0.00 USD in all 6 layout × timetable cells. 45/45 optima buy 0 kWh and move
  0 batteries. Pooled gap vs best rule: 20.98 % [16.59, 25.36] (n = 15), the same with or without transfers.
- Written targets, separated layouts, M8 cyclic tours: value of transfers 16.40 [8.46, 24.35] USD (1 hub) and
  17.39 [10.69, 24.09] (2 hubs), i.e. 2.64 % and 2.68 % of ILP(none), positive on 5/5 seeds. Every optimum uses one
  leg carrying two batteries. Co-located layouts: 0.
- r3 shuttles: incumbent values 3.56 [-0.70, 7.82] and 3.09 [-0.60, 6.78] USD; bound-based upper limits 15.18 and
  15.58. On 10/15 runs the r3 solve stopped at TL.
- Transfers cut the ILP price of recovery from 24.28 / 24.15 USD (none) to 7.87 [6.98, 8.77] / 6.75 [5.92, 7.59]
  USD (cyclic).
- Cyclic vs r3 (ILP, written): -12.84 [-17.15, -8.53] and -14.30 [-18.00, -10.61] USD on incumbents. The provable
  part is only -1.23 [-1.92, -0.53] and -1.81 [-2.77, -0.86] (cyclic incumbent minus r3 bound). The advantage
  mostly reflects the split fare (C_reb 22 USD per r3 shuttle vs 7 / 6 per cyclic leg).
- Policy transfer rules never beat the no-transfer rule r2: each is strictly cheaper than r2 in 0 of 60 cells.
  - On r3, REORDER_POINT loses 122.52 / 116.21 / 115.96 USD and COST_AWARE (M3) 50.60 / 62.52 / 70.50.
  - On cyclic tours (separated), REORDER_POINT loses 10.48 / 10.56 USD and COST_AWARE 31.88 / 24.86.
- Conclusion: transfers are a second-order lever at this scale, active only under enforced recovery. A
  battery-binding instance (for example r5_stress4h_k8) is needed to test them as a first-order lever.

Source: X2 report, `r5_x2_transfers/figs/x2_per_instance_wide.csv`, `figs/tables.json`.

## RL comparator (X7)

PPO-clip agent controlling station charging on top of R2 or R5 rule riders. 200,704 steps, one PPO seed, test seeds
0-9.
- PPO gap vs the relaxed ILP: nyc4h_stress2 33.51 ± 6.26 % (R2 riders) and 31.77 ± 8.12 % (R5); r5_stress4h
  42.85 ± 2.15 % (R2) and 34.69 ± 2.33 % (R5). The best rule's gaps are 28.97 ± 7.27 and 41.30 ± 2.61 %.
- nyc4h_stress2 (**corrected**):
  - PPO minus own rule: R2 +22.07 ± 25.89 USD, R5 -8.38 ± 18.87. Not significant.
  - PPO serves fewer orders than its own rule: -3.61 ± 3.11 pts (p = 0.03) and -5.56 ± 3.63 pts (p = 0.007). It
    buys 1.0-1.5 kWh less.
  - PPO minus best_rule: +61.01 ± 65.38 and +46.34 ± 47.92. Not cheaper, and not significantly dearer.
  - PPO minus never-charge: -108.44 ± 77.55 (R2, p = 0.01) and -109.31 ± 128.82 (R5, p = 0.09).
- r5_stress4h: PPO(R5) - best_rule = -149.69 ± 58.13 USD (10/10 seeds), but this is the never-charge outcome.
  - PPO(R5) - never-charge(R5) = +0.03 ± 0.07 (max 0.33). PPO(R2) equals never-charge(R2) to 2e-13.
  - Served share falls: 58.5 % vs 74.6 % (best rule) and 85.4 % (ILP).
  - Never charging wins only because a dropped order (30 USD) costs less than the response plus lateness of the very
    late orders the rules accept (lateness 137.7 vs 303.9 USD; unserved 597.0 vs 366.0 USD).
- Training (**corrected**): the raw first-100 → last-100 means (1123.7 → 1065.7, 1170.0 → 894.8, 1428.0 → 1584.7,
  1277.0 → 1280.5) are confounded by instance mix. The mix alone shifts the last block by +20.0 / -110.8 / +200.5 /
  +53.6 USD. With instance fixed effects the change is -82.8 [-99.1, -66.5] / -175.0 [-198.9, -151.0] /
  -46.6 [-50.7, -42.4] / -53.1 [-57.8, -48.4] USD. The OLS intervals are too narrow, because episodes are
  autocorrelated. So the stochastic policy improved in all four runs (3-4 % on r5_stress4h), but the deterministic
  r5_stress4h policy still behaves as never-charge.
- Price of recovery: 0.33 ± 0.54 USD (nyc4h_stress2, all OPT); 4.74 ± 4.98 USD (r5_stress4h, both ILPs certified on
  only 1/10 seeds; unresolved).
- Defensible claim: learned station control on rule riders stays 31.8-42.9 % above the coordinated ILP, close to the
  rules (29.0-41.3 %). It beats the rules only by refusing service.

Source: X7 Tables 1-4, `r5_x7_rl/figs/x7_tables.json`, `models/*/monitor.csv`.

---

## Figures for the paper (PDF paths; PNG at 300 dpi alongside)

All paths are under `/Users/yuanmingchen/Desktop/Research/OR Model-Battery Swap/ebike_swap_sim/outputs/`.

1. `r5_x1_headline/figs/x1_survival_waterfall.pdf` (7.2 in). *Survival of the coordination gain from round 3 to the
   round-5 headline: Shapley contributions of (a) eBaaS energy calibration, (b) per-instance best-rule baseline,
   (c1) relaxed end targets and (c2) end-state adjustment, for (a) usd4h (n = 30) and (b) nyc4h (n = 10). End bars:
   mean gap with 95 % Student-t CI.* (RQ1)
2. `r5_x1_headline/figs/x1_gap_by_demand.pdf` (3.5 in). *Gap to the best rule by demand multiplier: round 3 (legacy
   energy, r2 rule; squares) vs round-5 headline (eBaaS energy, best rule, relaxed targets, end-adjusted; circles).
   Mean with 95 % t-CI (n = 10 per group); dots are instances.* (RQ1, RQ3)
3. `r5_x1_headline/figs/x1_component_decomposition.pdf` (3.5 in). *Decomposition of the headline saving (best rule
   minus ILP, USD per 4-h window, end-adjusted) by cost component; mean with 95 % t-CI.* (RQ1)
4. `r5_x1_headline/figs/x1_metric_pack.pdf` (7.2 in, appendix). *Operating metrics for the best rule and the ILP
   (relaxed targets, eBaaS): served share, BSR, mean SBUR, station time, outage rate, empty km per bike-hour,
   network peak load and energy bought; mean with 95 % t-CI. The ILP's lower in-window energy and peak load reflect
   recharging deferred past the window (R_end = 0); outage and station time count planned reserve dips and planned
   waiting.* Use only with this caption, or after the outage and station-time metrics are redefined.
5. `r5_x3_rolling/figs/fig_x3_cost_by_method.pdf` (7.2 × 2.7 in). *End-adjusted cost per 4-h window by method,
   relaxed targets. Grey lines: seeds (paired). Markers: means; error bars: exact 95 % t-CI of the paired difference
   to the offline ILP. (a) usd4h with eBaaS calibration, n = 10; (b) r5_stress4h, 6 bikes, n = 5. Rolling: W = 24,
   k = 6 slots, lookahead lambda in min; Roll.+fc.: rolling with the bootstrap-forecast battery plan.* (RQ2)
6. `r5_x3_rolling/figs/fig_x3_decomposition.pdf` (7.2 × 2.6 in). *Decomposition of the offline gap (best rule -
   offline ILP; dashed line, shaded 95 % CI) into foresight (rolling - offline, hatched) and online coordination
   (best rule - rolling, solid), as shares of the best-rule cost, for lookahead 0/10/20 min and the forecast policy.
   Error bars: exact 95 % t-CIs. (a) usd4h_ebaas, n = 10; (b) r5_stress4h, n = 5. Online values use an unpriced
   terminal fallback and are therefore upper bounds on what is retained online.* (RQ2)
7. `r5_x5_stress/figs/fig_x5_gap_vs_fleet.pdf` (7.2 in). *Gap of the ILP vs the best rule against fleet size.
   (a) Stressed family, orders = 8 per bike, relaxed targets: mean with exact-t 95 % CI (n = 5) and seeds; the 8-h
   window at 6 bikes is shown as its mean (n = 3); open circles: written-target seeds; grey band: round-3 usd4h
   mean ± SD. (b) Fixed demand (48 orders, 0.6 kWh), one line per number of spares per site (n = 2).* (RQ1, RQ3)
8. `r5_x5_stress/figs/fig_x5_shadow_prices.pdf` (7.2 in). *Battery-side scarcity against fleet size (stressed 4-h
   family, relaxed targets, n = 5): (a) LP operating value of one more spare and one more charger per site, USD per
   window (symlog axis; dotted lines: set-up costs; open markers: written-target seeds); (b) stock-out slot-sites per
   window, best rule vs ILP.* (RQ3)
9. `r5_x5_stress/figs/fig_x5_isocost_heatmap.pdf` (7.2 in). *System cost (operating cost incl. end adjustment and
   spare set-up + 88.94 USD per bike and window) over fleet size × spares per site, seed means at 48 orders:
   (a)-(c) best rule at 0.5/0.75/1.0 kWh (n = 3), (d) best rule at 0.6 kWh (n = 2), (e) ILP at 0.6 kWh (n = 2), same
   colour scale; outlined cell: cost-minimal design within the tested grid; n/a: not run.* (RQ3)
10. `r5_x5_stress/figs/fig_x5_levers.pdf` (7.2 in, or as a table, see T6). *Operating levers on the 8-bike stressed
    instance (relaxed, n = 3): change in cost vs the reference, (a) ILP (grey band: mean reference MIP gap,
    9.3 USD), (b) best rule; mean with exact-t 95 % CI and seeds. No rule response is significant at n = 3.* (RQ3)
11. `r5_x4_network/figs/fig_x4_2x2_decomposition.pdf` (7.2 in). *Value of the swap network and of coordination.
    (a, b) Mean cost per 4-h window in the 2 × 2 design (home charging vs swap network × best rule vs ILP) for
    usd4h_ebaas (n = 10) and r5_stress4h (n = 5), relaxed targets, exact-t 95 % CIs in brackets; (c) value of the
    network under each policy and value of coordination under each infrastructure, with 95 % t-CI error bars.*
    (network value)
12. `r5_x4_network/figs/fig_x4_ebaas_metrics.pdf` (7.2 in). *(a) Orders served per rider-hour and (b) empty km per
    rider-hour for the four cells, means with exact-t 95 % CIs, relaxed targets.* (network value)
13. `r5_x2_transfers/figs/fig_x2_cost_layout_timetable_switch.pdf` (7.2 in). *Total cost per 4-h window by layout,
    timetable (r3 shuttles vs M8 cyclic tours) and transfer switch, usd4h seeds 0-4: (a) relaxed targets, (b)
    written targets; filled: ILP, open: best rule; (c, d) paired ILP(free) - ILP(none); open triangles: bound-based
    limits for time-limited transfers-free runs. Exact-t 95 % CIs.* (transfers, RQ4)
14. `r5_x2_transfers/figs/fig_x2_transfer_rule_loss.pdf` (7.2 in, appendix). *Policy cost above the no-transfer rule
    r2 for REORDER_POINT and COST_AWARE (M3) transfer rules on r3 shuttles (filled) and cyclic tours (open), by
    layout: (a) relaxed, (b) written targets; exact-t 95 % CIs over seeds 0-4.* (transfers)
15. `r5_x6_manhattan/figs/fig_x6_map.pdf` (7.2 in). *Manhattan south of 110th St: 15 candidate sites (circle area ∝
    restaurants at the node), six bridge/tunnel rider depots, and the sites chosen by each method at budgets m = 1-4
    (markers offset from their site).* (RQ4)
16. `r5_x6_manhattan/figs/fig_x6_V_vs_budget.pdf` (7.2 in). *Expected cost V per 4-h window against budget per siting
    method under (a) the ILP, (b) rule r2 and (c) the selfish follower, written targets; mean over 3 scenarios with
    95 % t-intervals that mostly reflect demand variation shared by all methods. No bi-level layout exists at m = 1;
    the bi-level search was truncated.* (RQ4)
17. `r5_x6_manhattan/figs/fig_x6_headline_gaps.pdf` (3.5 in). *Gap of the ILP vs the best operating rule per layout:
    relaxed control (filled) and written targets (open), mean and 95 % t-interval over 3 scenarios; dashed line:
    round-3/4 nyc4h mean (31.8 %).* (RQ1, RQ4)
18. `r5_x6_manhattan/figs/fig_x6_compliance.pdf` (3.5 in). *Compliance sweep at the bi-level layout: (a) V and (b)
    served share against the share alpha_c of riders following the ILP plan; mean with 95 % t-band over 3 scenarios
    (dots: scenario means over 3 draws). Dashed: selfish equilibrium; dotted: rule r2. The mean curve is concave and
    crosses the selfish equilibrium near alpha_c = 0.32.* (RQ5)
19. `r5_x6_manhattan/figs/fig_x6_levers.pdf` (3.5 in, appendix). *Marginal levers at the bi-level layout: change in V
    under the ILP follower (blue) and the selfish follower (vermillion); bars: means, dots: scenarios. Shuttle and grid
    were not priced under the ILP. Selfish-follower intervals include zero (n = 3).* (RQ4, RQ5)
20. `r5_x7_rl/figs/x7_cost_by_method.pdf` (7.2 in). *End-adjusted cost per 4-h window by method, relaxed control,
    mean with exact-t 95 % CI over test seeds 0-9 (dots: seeds): (a) nyc4h_stress2, (b) r5_stress4h. Best rule =
    per-seed minimum over R2 and R5_range; PPO controls only station charging on top of the named rider layer.* (RL)
21. `r5_x7_rl/figs/x7_service_cost_tradeoff.pdf` (3.5 in). *Share of orders served vs end-adjusted cost (mean with
    95 % t-CI on both axes, n = 10): (a) nyc4h_stress2, (b) r5_stress4h. On r5_stress4h the PPO policies (hollow)
    coincide with never-charge: they are cheaper than the rules only because they serve fewer orders.* (RL)
22. `r5_x7_rl/figs/x7_training_curves.pdf` (7.2 in, appendix). *PPO training on seeds 1000-1019: episode cost Phi_H -
    Phi_0 (USD), 100-episode rolling mean (thick) and episodes (faint); horizontal lines: test-seed means of the rule
    station layer, never-charge and the deterministic PPO policy. Training instances are drawn in blocks of 16
    episodes, so the raw curve mixes learning with instance difficulty; with instance fixed effects cost falls in all
    four runs (-83, -175, -47, -53 USD).* An instance-adjusted replot would be better: residuals from instance means
    can be computed with the reconstruction in the X7 digest correction.

## Tables for the paper

- **T1 Headline survival** (X1 Tables 1-2 plus the corrected Shapley-uncertainty table): S0-S4 per group, Shapley
  terms with CIs, survival ratio, paired S4 - S0.
- **T2 Cross-family headline** (RQ1 table above): gap vs best rule, relaxed, end-adjusted, with n and ILP status, for
  usd4h, nyc4h, the stressed family (6/8/10 bikes, 8 h), X7 families and Manhattan.
- **T3 Saving by cost component** (X1 Table 4): lateness / response / unserved / travel / electricity / end
  adjustment, usd4h and nyc4h.
- **T4 Foresight vs coordination** (X3 T1 + T2 rows at lambda 0/10/20 and forecast): costs, VoI and coordination as
  % of best rule, retained share (mean of ratios and ratio of means), foresight share.
- **T5 2 × 2 network decomposition** (X4 Table 2, best-rule rows + Table 3 percentages + productivity rows of
  Table 5).
- **T6 Battery scarcity and levers** (X5 LP shadow-price table + `r5_x5_stress/figs/tab_x5_levers.tex`, booktabs).
- **T7 Fleet sizing** (X5 cost-minimal design table + matched-service row): ILP K4 B2 1310.1 (0.698); ILP K8 B2
  1448.8 (0.969); rule optima per pack.
- **T8 Transfers** (X2): value of transfers per layout × timetable × targets, price of recovery, policy-rule losses.
- **T9 Siting by follower** (X6 Table 2 at m = 2 plus the capacity-matched comparison and the compliance row
  V(alpha_c)).
- **T10 RL comparator** (X7 Table 1 compressed: ILP relaxed, best rule, never-charge, PPO R2/R5, served share; plus
  Table 2 paired rows).
- **Appendix:** price of recovery / boundary grid (X5 §2, X3 T5, X4 Table 4), coverage table above, X1 metric pack.

## Abstract numbers

Coordinating dispatch and swap timing cuts the end-adjusted cost of a 4-h delivery window by 27.2 % ± 6.0 (usd4h,
n = 30, all positive, all ILPs optimal) and by at least 27.4 % ± 7.1 (NYC-calibrated, n = 10) relative to the best
of several operator-grade rules. The gain rises with congestion: 9.8 %, 28.3 % and 43.5 % at 0.75×, 1× and 1.5×
demand, and 40-47 % on a battery-stressed family as the fleet grows from 6 to 10 bikes. It reaches 31.8-34.3 % on a
Manhattan-wide network. Over 99 % of the saving is service quality: late orders fall from about 14 to under 1 per
window. Without foresight, a rolling-horizon coordinator with a 10-min lookahead keeps 64-77 % of the gap and beats
the best rule on 15/15 instances. Swap network plus coordination together cut cost by 44-50 % relative to home
charging, and coordination accounts for 63-70 % of that effect (Shapley). Battery transfers matter only under
enforced end-of-window recovery, and there they save 2.6 %. Half compliance closes 36 % of the gap between no and
full compliance. A learned (PPO) station policy stays 32-43 % above the coordinated optimum.

## Caveats

1. **Objective calibration.** A served order's response plus lateness (about 29.6 USD under rules on the stressed
   family) is close to the 30 USD unserved penalty. Never-charge (X7), the rule's P = 0 response (X5), part of the
   online admission gain (X3), the negative rule-based network value on X4 seed 8, and the ILP's cost-minimal fleet
   (70 % served, X5) all depend on this. A service-level constraint or a higher penalty is needed before these are
   reported as findings.
2. **Metric definitions.** The ILP outage rate is mostly the reserve-breach flag. Constraint (9) imposes q_res only
   at the terminal certificate, so mid-horizon dips below the reserve are allowed. ILP station time counts planned
   waiting. Redefine both before publishing (X1 anomalies 1-2). Stock-out counts do not track service (X5).
3. **Deferred recharging.** Under relaxed targets the ILP's lower in-window energy and peak are largely deferred
   recharging (X1). They are not a grid benefit.
4. **Shared instances.** X1 usd4h x1, X3 usd4h_ebaas and X4 usd4h_ebaas network are the same 10 instances, and
   r5_stress4h 6 bikes appears in X3, X4, X5 and X7 (seeds 0-4). Do not count these as independent replications.
5. **Online upper bounds.** In 47/60 relaxed online runs the terminal fallback leaves (9) unpriced
   (C_dummy_terminal = 0). Retained shares are upper bounds, VoI is understated, and the online price of recovery
   is not measured.
6. **Time limits.** Incumbent-based gaps on time-limited cells: stressed 8/10 bikes and 8 h (X5), r5_stress4h in X7
   (7/10 relaxed), Manhattan written (18/66), X2 r3 written. Gaps vs proven bounds differ by at most 0.77 pts on
   average. Lever and price-of-recovery differences smaller than the MIP gap (about 9-15 USD) are noise. X5 lanes
   ran concurrently, so TL incumbents may depend on machine load.
7. **Pruning.** nyc4h and nyc4h_stress2 use PRUNING_NYC, which binds only the ILP, so their gaps are lower bounds.
8. **Small n.** r5_stress4h has n = 5, Manhattan n = 3 (t = 4.303), fleet sweep ILP n = 2 (no CIs), levers n = 3.
   Paired differences are the meaningful comparisons.
9. **Formulation change in S0.** S0 uses round-3 per-bike ILP rows and S1-S4 the aggregated flow. O1 equivalence was
   validated only on the toy and three E2u optima, so step (a) also contains the formulation change (both optimal,
   so this should be immaterial).
10. **No services.** Most families have no transport services (r5 = r5_range everywhere), so the shuttle layer is
    exercised only in X2 and the Manhattan layouts with shuttles.
11. **Siting is incomplete.** The bi-level search was truncated after 4 layouts, M08 was never screened, and the
    policy-aware search failed. The claim "bi-level siting beats rule siting" is not supported yet. The Manhattan
    geometry is a synthetic 150 m grid with real restaurant locations, and the present-day layout is a proxy.
12. **Selfish equilibrium.** 2 of 84 selfish equilibria (plus one relaxed-control copy) hit the 10-iteration MSA cap
    without converging, including the CSCD m = 2 scenario-2 comparator.
13. **Fleet sizing.** Fleet and demand are confounded on the core stressed axis (8 orders per bike). The fleet sweep
    optima lie on the edge of the tested grid.
14. **Single-refuter qualifiers.** These are not corrected in the reports, but must be worded carefully.
    - X3 C1: on usd4h_ebaas the retained share is not significantly above one half (CI lower bound 0.44; 3/10 seeds
      below 0.5).
    - X4 C3: the value of the network under the best rule is significant on usd4h_ebaas but negative on seed 8. On
      r5_stress4h its CI includes zero although 5/5 seeds are positive.
    - X5 C2: at 6 bikes the spare's LP value CI touches zero (median 0.32, about its cost).
    - X6 C2: the written-target disadvantage of the bi-level layout holds in all 3 scenarios, also against its MIP
      lower bounds (-2.82 % [-5.00, -0.65]); with relaxed targets the two layouts tie.
15. **RL.** One PPO seed, default hyper-parameters, 200 k steps. The deterministic r5_stress4h policy collapses to
    never-charge.
16. **Calibration comparisons.** usd4h_ebaas uses the eBaaS calibration (25 Wh/km, L 24). Comparisons with round-3
    numbers should use the matched x1 subset (31.18 % ± 9.05), not the pooled 29.55 %.
