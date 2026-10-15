# E2 formulation review: does the mathematics of E2.pdf need to change?

Synthesis of three experiment rounds (E2u / E3u / E4u / E8, rounds 1-3) and of 32 proposals from four review lenses (results-driven, modelling realism, computation and iteration, proposal-deck questions), each checked by two independent adversarial verdicts against the files listed in Section 8.

Status: 2026-10-13, after round 3. Equation numbers refer to `notes/extracted/E2.txt` (1)-(33).

## 1. Verdict

**No equation of E2 (1)-(33) needs to change on the evidence of rounds 1-3.** Of the 32 proposals, 23 were A-formula changes; every one of them was refuted by both verdicts, in each case for the same reason: the quantity the proposal wanted to fix is already a free parameter or a free data set of the written model, and the observed effect is produced by the parameter value the project chose, not by the formula. The three findings that looked like formula artefacts have exact parameter equivalents:

| Finding | Looked like | Is in fact |
|---|---|---|
| ILP drops more orders than the baseline (8/30 E2u, 5/20 E8); usd_A drop rates 83-86 % | (31) prices uncontrollable prep time | By (6) the a_i-referenced objective equals the written one with P_i := P^0_i + w_i Delta (a_i - r_i); (30) already indexes P_i by order |
| Transfers worth 8.6 USD written vs 0.00 relaxed (E3u, 15/15 pairs); baseline violates (17)/(18) | Hard end targets manufacture the transfer value | rho and R_end_j are declared parameters ("disabled by setting to zero", E2 p.6); R_end_j = 1 at swap-only sites is a data error, not a formula error |
| Chargers / grid / stock never bind; relaxed ILP buys 0 kWh in 20/20 E8 runs | Charging model (13)/(19) too fast, (16) all-full stock | (19) p_ch = eps/(eta Delta) is a derived quantity; E2's own toy already realises a 0.3 kW charger (eps = 0.02 kWh); 9 spares / 6 chargers for 6 bikes over 4 h is a capacity-ratio property of the data |

Two proposals survived: **L4-P6** (both verdicts kept; parameter-only: build an energy-stressed instance family) and **R6** (one verdict kept; scope extension: rolling-horizon wrapper to separate the value of coordination from the value of perfect information). The remaining work is therefore (B) calibration and instance design, (C) the extensions E2 itself lists on p.9, and three short *text* remarks next to (5), (31) and (4) that state identities already implied by the model.

## 2. How proposals were adjudicated

- A proposal is **dropped** when both refuters refuted it (the corrected proposal of the refuters is kept as a B or C item where it is actionable).
- **must_change** = both verdicts kept, high priority, formula change. Empty.
- **should_consider** = one verdict kept, or both kept but not a formula change, or a consensus corrected proposal that adds a *statement* to the paper (identity, lemma, remark) without changing any constraint or objective term.
- **parameter_only** and **scope_extensions** collect the corrected proposals.
- Duplicates merged: P1 = R2 (response reference); P2 = R5 = L3-P2(part) (end targets); P5 = R3 = L3-P7 = L4-P4(a) (energy rounding); P4 = L4-P2(a) (initial stock / periodicity); P6 = L3-P6 (servable set in (33)); R7 = L4-P7 (per-platform share); R4 = P8 (fleet capacity at x1.5); L3-P3 = L3-P8 (arc / route set); L4-P3 = L3-P4 (decoupled / reformulated solution methods).

## 3. Proposal-by-proposal table

| id | Equation(s) | Claimed category | Verdict 1 | Verdict 2 | Final class | Merged with |
|---|---|---|---|---|---|---|
| P1 | (30)-(31) response reference | A | refuted -> B | refuted -> B | parameter_only (+ text remark) | R2 |
| P2 | (17)-(18) end targets | A | refuted -> B | refuted -> B | parameter_only | R5, L3-P2 |
| P3 | (9) terminal certificate | A | refuted -> B | refuted -> B | parameter_only (q_res sensitivity) | - |
| P4 | (16) initial stock, single window | C | refuted -> B | refuted -> B | parameter_only (N^0_jq as data) / scope C | L4-P2 |
| P5 | (1),(3) per-leg rounding | A | refuted -> B | refuted -> B | parameter_only (E6) | R3, L3-P7, L4-P4 |
| P6 | (33) servable denominator | A | refuted -> B | refuted -> B | parameter_only (tail_slots) | L3-P6 |
| P7 | (27), instance ratios | B | refuted (B upheld) | refuted (B upheld) | parameter_only | L4-P6 |
| P8 | (6) order stacking | C | refuted -> C | refuted -> B | scope_extensions (low) | R4 |
| R1 | (13),(19),(20) charger step | A | refuted -> B | refuted -> B | parameter_only (eps = 25 Wh) | P5 |
| R2 | (31) | A | refuted -> B | refuted -> B | parameter_only | P1 |
| R3 | (3) | A | refuted -> B | refuted -> B | parameter_only | P5 |
| R4 | source node / (9) shifts | A | refuted -> B | refuted -> B | parameter_only (fleet sweep) | P8 |
| R5 | (16)-(18) energy target | A | refuted -> B | refuted -> B | parameter_only | P2 |
| R6 | Sec. 2 bullet 1, (4), (6) online | C | **kept** -> C | refuted -> C | **should_consider** (C) | L3-P2 |
| R7 | (30),(33) per platform | A | refuted -> B | refuted -> B | parameter_only | L4-P7 |
| R8 | homogeneous batteries | C | refuted -> B | refuted -> B | parameter_only (1 kWh variant) | - |
| L3-P1 | (5),(6),(9),(12),(22) aggregation | A | refuted -> B | refuted -> B | should_consider (text remark only) | - |
| L3-P2 | (16)-(18) rolling window | C | refuted -> C | refuted -> B | scope_extensions | R6 |
| L3-P3 | (2)-(4) arc rules | A | refuted -> B | refuted -> B | should_consider (lemma, no equation) | L3-P8 |
| L3-P4 | column generation | A | refuted -> B | refuted -> C | keep (optional method appendix) | - |
| L3-P5 | (10),(13) CG cut | A | refuted -> B | refuted -> B | parameter_only (solver protocol) | - |
| L3-P6 | (33) | A | refuted -> B | refuted -> B | parameter_only | P6 |
| L3-P7 | (1),(3) coarser L | B | refuted -> B | refuted -> B | parameter_only (E6) | P5 |
| L3-P8 | (2)-(4) several routes | A | refuted -> B | refuted -> B | parameter_only (route set is data) | L3-P3 |
| L4-P1 | (7)-(9),(27),(33) siting | C | refuted -> B | refuted -> B | parameter_only (run E5) | - |
| L4-P2 | (16)-(18),(28) periodic + TOU | A | refuted -> C | refuted -> C | scope_extensions | P4 |
| L4-P3 | station-level charging ILP | C | refuted -> B | refuted -> B | parameter_only (fix x, solve battery side) | - |
| L4-P4 | (1),(3),(29) routes + risk | A | refuted -> B | refuted -> B | parameter_only (E6) / scope (risk) | P5 |
| L4-P5 | Sec.1, (6),(12),(22) compliance | A | refuted -> C | refuted -> B | scope_extensions (variable fixing) | - |
| L4-P6 | data for (4),(15)-(16),(20) | B | **kept** (B) | **kept** (B) | **should_consider** (B, high) | P7 |
| L4-P7 | (26)-(32),(33) multi-objective | A | refuted -> B | refuted -> C | keep (scalar) + parameter (zeta sweep) | R7 |

## 4. must_change

None. No proposal was kept by both verdicts as a formula change. The inventory core (5)-(15), the logistics (10)-(11), (23)-(25), the capacity rows (15), (20)-(22), the objective (26)-(32) and the optional rows (33) all behaved as written in every experiment (LP relaxation tight: 26/30 E2u, 32/33 E3u, 37/40 E8 solves closed at the root; toy J = 12.5 reproduced; 0 infeasible instances).

## 5. should_consider

Each item below keeps every constraint and objective term of E2 as written. Items SC-1 and SC-2 are the two surviving proposals; SC-3 to SC-5 are consensus corrected proposals that add a *stated identity or remark* to the paper (no new variable, no new row) because the experiments showed readers of E2 will otherwise draw the wrong conclusion.

### SC-1 (L4-P6, both verdicts kept) - energy-stressed instance family. Category B, priority high

- **Problem.** On usd4h / nyc4h the battery side never binds, so three deck questions (station queues, charging, swap-oriented assignment) have no content and the 29.6 % headline is a pure dispatch/lookahead effect.
- **Evidence.** E4u round 3: ILP total 614.2-618.0 USD over the 20-cell B x C grid (seed 0); marginal operational value of a spare +0.35 +/- 0.34 USD (1 -> 2), then <= 0.09; charger and kW marginal value 0.000; (21) peak 3.33 kW vs 6-8 kW. E8 round 3 anomaly 8: relaxed ILP buys 0 kWh in 20/20 runs. E2u round 3: electricity 0.5 USD of the 421 USD gap. Round 1 (toy, q0 3-6 of 12, 2 h): knee at 2 spares per station, 177 toy units for 1 -> 2 (SUMMARY sec. 2 E4), proving the model expresses the knee when the data are tight.
- **Proposed change (data, written out).** Stage 1 (H = 48, solvable today): |K| = 8, 48 orders (OPTIMAL in 137-171 s in `outputs/r2_probe/usd4h.jsonl`), q0_k ~ U{2..4} of L = 12, B_j = 1 (sum_j B_j = 3 < |K|), C_j = 1, P_j = 1.4 kW, grid group 4 kW. Stage 2: usd8h (H = 96) with the same ratios, rolling if a single solve exceeds 600 s. Fleet sweep |K| in {6,...,10} at x1.5 with zeta = 0.90 (R4/P8 merged).
- **Validation experiment.** Re-run E3u / E4u / E8 tables on the stressed family; success = at least one of (14), (20), (21) binds (positive dual / nonzero slack usage), marginal value of a spare > b^B_j = 0.332 USD, relaxed ILP purchases > 0 kWh, siting delta > 0.41 USD.
- **Cost.** None to the model; ILP size 1.7-2.8 M arcs at 8 bikes.

### SC-2 (R6, one verdict kept) - rolling-horizon wrapper around the unchanged ILP. Category C, priority high

- **Problem.** The headline 29.55 % +/- 5.61 (E2u, n = 30) and 31.8 % +/- 8.2 (E8, n = 10) compare a full-information offline optimum (all 36 orders known at t = 0, 27-30 min before they are ready) with an online rule (`baseline.py` enqueues at r_i). Per-instance gap tracks baseline lateness at r = 0.91 (E2u) / 0.98 (E8); composition 59 % lateness / 32 % response / 8 % unserved. The value of coordination and the value of foresight are confounded.
- **Formulation (wrapper; (1)-(33) unchanged inside each window).** Epochs t_0 = 0, k, 2k, ...; at each epoch solve E2 on [t_0, t_0 + W] with
  - order set I(t_0) = {i : r_i <= t_0 + lambda, not yet committed}, lambda = look-ahead (0 = strict online);
  - bike source s_k = (v_k(t_0), t_0, q_k(t_0)), or the end node of the committed in-progress arc (cost sunk);
  - station state n_{j q t_0} = simulated stock from (13) after executing the previous window, all levels q;
  - committed transfers with l_e < t_0 <= u_e enter (11) as constants;
  - non-anticipativity: x_ka fixed for arcs with l_a < t_0;
  - (9) and (16)-(18) imposed only in the final window; ex-post pricing with (26)-(32) over the whole day.
- **Validation experiment.** Planned E7 (`workflow1_result.json` plan.experiments[6]): report offline ILP (lower bound), rolling ILP at lambda in {0, 10, 20 min}, and baseline on the 30 E2u instances; the share of the 29.6 % that survives at lambda = 0 is the value of coordination proper.
- **Cost.** Stays an ILP per window; W = 12-24 slots gives sub-second to 30 s solves; sequential solves are an upper bound on the joint optimum and must be reported as such.

### SC-3 (P1 = R2 corrected) - response reference: state the identity and calibrate P_i. Category B, priority high

- **Problem.** (31) prices u_a - r_i; the food-preparation wait a_i - r_i (U{20..35} min, mean 29.2 min on E8) is uncontrollable, so the effective rejection threshold is P_i - w_i Delta (a_i - r_i) ~ 30 - 8.8 = 21 USD at w = 18 $/h, and under usd_A (w = 40 $/h) it is negative: ILP drops 85.2 / 86.1 / 83.3 % at x0.75 / x1 / x1.5 vs baseline 5.6 / 11.1 / 35.2 % (`outputs/e2u_coord_usd/RESULTS_final.md`). Round 3 still has the ILP dropping more orders than the baseline on 8/30 E2u and 5/20 E8 instances, unserved gap component -18.0 USD at x0.75.
- **Why not a formula change.** By (6), sum_k sum_a x_ka = 1 - u_i, so for every order w_i Delta (u_a - r_i) = w_i Delta (u_a - a_i) + w_i Delta (a_i - r_i) (1 - u_i); the a_i-referenced model is the written model with P_i replaced by P_i + w_i Delta (a_i - r_i) and a constant shift. Same optimal schedules.
- **Proposed change (data + one sentence).** Data: P_i := P^0_i + w_i Delta (a_i - r_i) with P^0_i = 30 USD base (15 / 60 envelope), optionally + w_i Delta (h^p_i + h^d_i). Text after (31): "Because of (6), measuring response from the food-ready time a_i instead of r_i is equivalent to replacing P_i by P_i + w_i Delta (a_i - r_i); the dispatcher-controllable response u_a - a_i is reported alongside u_a - r_i."
- **Validation experiment.** Re-run E2u x1 (10 seeds) with the shifted P_i; success = ILP unserved count <= baseline unserved count on every instance where the baseline is feasible, unserved gap component >= 0, headline gap reported with both P_i conventions.

### SC-4 (P2 = R5 = L3-P2 corrected) - end-of-horizon targets: fix R_end_j at swap-only sites, make the relaxed control the like-for-like headline. Category B, priority high

- **Problem.** With R_end_j = 1 at swap-only sites (C_j = 0) and rho = 0.5, (17)-(18) cap the separated layouts at 4 of 9 swaps when h = z = 0 (sum_j B_j - ceil(rho sum_j B_j) = 4), which is the entire transfer value: 8.65 +/- 10.12 USD written vs 0.00 on 15/15 pairs relaxed (E3u round 3); one 22 USD shuttle with 2 batteries restores 6 swaps (served 0.822 -> 0.894). In co-located layouts the price of the targets is 0.34 USD per instance (E2u, max 0.86) and 0.26-0.28 USD (E8). The baseline cannot be forced to satisfy a hard terminal target: (18) violated on 6/30 E2u, 4/20 E8 and every separated E3u NONE run; MIP starts rejected 10/60 in E3u, 7 in E4u (3 TIME_LIMIT cells from the cold start).
- **Proposed change (parameters).** R_end_j = 0 for j in S \ C (audit I7 / open question 1); rho and R_end_j reported as a sensitivity grid rho in {0, 0.25, 0.5, 1} x R_end_j in {0, 1}; relaxed control (rho = R_end = 0, E2 p.6) as the headline against the rule baseline; written targets reported as "price of recovery". Optionally the "count-periodic" setting rho = 1, R_end_j = B_j as the upper bracket.
- **Validation experiment.** E3u seeds 0-4 with R_end_j = 0 at swap-only sites: expected transfer value falls to the operational part (0.08 USD relaxed) and the TIME_LIMIT cells close, because the fixed-charge gap of (10) (13.33 USD = f_e (1 - 2/U_e)) no longer has a 2-battery shuttle to pay for.

### SC-5 (L3-P1 + L3-P3 corrected) - two computational remarks, no equation. Category B, priority medium

- **Remark after (5) (identical-bike aggregation).** "Bikes with identical (v0_k, q0_k) may be merged into one integer flow of value m_c: 0 <= x_ca <= m_c, right-hand sides +/- m_c in (5), x_ca <= m_c y_j in (9); the optimum and the LP bound are unchanged, and bike schedules are recovered by path decomposition." Evidence: 29 redundant identical-bike copies in the 30 saved E2u instances (`outputs/e2u_round3/instances`); the usd4h generator has at most 8 classes (2 depots x q0 in {4..7}). Note from the verdicts: the observed TIME_LIMIT cells were not caused by bike symmetry (788-node cell has six distinct bikes), so this is a presolve for the 20-50-bike regime, not a fix for round 3.
- **Remark after (4) (lossless arc elimination).** "A delivery arc is created only for t >= max(r_i, a_i - tau_r) (earlier starts are dominated by free waiting, audit I11); reposition arcs target facility and depot nodes only; both are lossless when the route library satisfies the triangle inequality in (tau, g, d), which holds with 0 violations on all saved usd4h / nyc4h instances." Evidence: reachable pruning 1.92 M -> 1.15 M arcs with identical optima 615.15 / 659.60 (`outputs/r2_probe/usd4h.jsonl`); default pruning gives 36,068,620 arcs at 10 bikes (`workflow5_round2_partial.json`). PRUNING_NYC (pre-positioning forbidden) is *not* proven lossless and should be replaced by the two rules above before E8 gaps are quoted as exact.
- **Validation experiment.** Solve the 30 E2u instances with aggregation on/off and with the written arc set vs the two-rule set; success = identical objective to 1e-6 on all 30 and a build-time reduction at 10 bikes.

## 6. parameter_only (all refuted-as-formula items, merged)

| # | Source | Equation kept | Data / protocol change | Evidence (report) | Expected effect |
|---|---|---|---|---|---|
| B1 | P1, R2, R7 | (30)-(31) | P_i := P^0_i + w_i Delta (a_i - r_i); P in {15, 30, 60} envelope; optional P_{phi(i)} = fee 13.25 + commission 5.27 + goodwill 10 | e2u_round3: 8/30 ILP drops more; e2u_coord_usd: 83-86 % under usd_A | Serve/reject margin becomes P^0_i; drop asymmetry disappears |
| B2 | P2, R5, L3-P2 | (16)-(18) | R_end_j = 0 at swap-only sites; rho x R_end sensitivity; relaxed control as headline; baseline_reserve variant | e3u_round3: 8.6 vs 0.00 USD; e2u: 0.34 USD; e8: 0.26-0.28 USD | Transfer value in E3u drops to operational part; MIP starts accepted |
| B3 | P3 | (9) | q_res in {0, 1, 2} sensitivity (toy uses 0, all runs use 1); report `ArcLibrary.infeasible_bikes` (0 on every instance) and stranded policy bikes | audit I2 (J 12.5 -> 206.5 at q_res = 1, L = 2); e8: stranded baseline bikes 4/20 | Bounded by bikes ending at floor level 2 (1-4 of 6 per seed) |
| B4 | P4, L4-P2(a) | (16) | n_jq0 = N^0_jq as instance data (sum_q N^0_jq = B_j); if used with B_j free, split b^B_j = b^hold_j + b^init_j | e8: 0 kWh relaxed 20/20; e2u ends 1.3-2.4 full of 9 | Makes charging bind within 4 h without a periodic formulation |
| B5 | P5, R1, R3, L3-P7, L4-P4 | (1)-(3), (19)-(20) | eps = 25 Wh, L = 24, Delta = 5 min, eta = 0.9 -> p_ch = 0.333 kW (48 V 5 A charger, as E2's toy does with eps = 0.02 kWh); consumption 12 vs 20 Wh/km; energy_rounding per_leg vs concat (existing switch); run E6 | 86-94 % of routes round to 1 level; 64.4 model levels vs 27.8 physical per E8 window (2.3x); seed 0 x1 concat: 615.146 vs 615.362 USD, 10 vs 10 swaps | Swaps per window fall from ~6.6 toward ~2-3; charger occupancy 2.5 h per pack; headline gap unchanged within CI |
| B6 | P6, L3-P6 | (33), (4) | tail_slots >= max prep (7) + h^p + h^d + max ride (~12-14 slots instead of 8) so I^serv = I; or pre-filter arc-less orders; solve min sum u_i first and skip zeta cells whose bound certifies infeasibility; warm-start zeta solves from the max-service incumbent | 15/540 unservable at x1.5; 14 x1.5 zeta solves at 300 s without incumbent (2.5 h of 4.4 h wall) | Same optima; 2.5 h of wasted solves removed |
| B7 | P7, L4-P6 | (27), (15), (20)-(22) | b^B_j = b^hold_j (171.5 USD/yr / 360 d x window share: 0.119 for 4 h) + b^init_j (eps L pi / eta); bikes per site 8-10; B_j = 0.3-0.5 |K| / |S|; C_j = B_j; H = 96 | e4u: -0.25 to -0.31 USD per battery beyond 2 (= -b^B + ~0); free sizing 3.5 batteries | Sizing result becomes a day-level result instead of one-window accounting |
| B8 | R4, P8 | s_k, (9), (33) | Fleet-size sweep |K| in {6,...,10} at x1.5 (54 orders), 10 seeds, lossless reachable pruning, 300-600 s; report smallest |K| with zeta = 0.90 feasible and implied throughput vs DCWP 2.53 deliveries per trip-hour | e2u: zeta 0.90/0.85 infeasible 10/10 at x1.5; max share 0.741-0.796 certified | Capacity curve replaces "infeasible with 6 bikes" |
| B9 | R8 | (12)-(14), (22) | 1 kWh-class pack sensitivity: L = 20 (eps = 50 Wh) or L = 24 (1.2 kWh), b^B = 0.50 USD per site per 4 h | battery side never binds (e8 0 kWh, e4u flat) | Nil on headline; needed for NYC realism |
| B10 | L3-P5 | (10), (13), (17)-(18) | Certify E3u written transfer value by a dichotomy: solve with sum_e h_e = 0 (already certified, e.g. 681.06 on (b) seed 0) and with sum_e h_e >= 1 (LP-tight); or BranchPriority on h_e; or quote the residual gap as the fixed-charge relaxation f_e (1 - 2/U_e) = 13.33 USD | e3u T8: absolute gaps 13.23-14.29 USD on all 10 TIME_LIMIT cells, every incumbent 1 shuttle x 2 batteries | 10 TIME_LIMIT cells closed without touching the model |
| B11 | L3-P8, L4-P4(b) | (2)-(4) | Route set R(v,w) is data; keep Pareto set in rounded (tau, g, d); cap at 2 routes per OD pair (time-minimal, energy-minimal) only when LION + DEM + signals replace the synthetic grid | usd4h 650 = 26 x 25 single routes; nyc4h 4160 | None until a real road layer exists |
| B12 | L4-P1 | (7)-(9), (27), (33) | Run E5 (never run) with fixed_facilities = False: y_j, B_j, C_j free, Fhat 50,000 / bhat 450 / chat 400 USD, Budget in {1,2,3,4} x (Fhat + 3 bhat + 2 chat), zeta = 0.90, 6-8 candidate sites, 10 seeds nyc4h | e8: siting delta <= 0.41 USD (0.063 %) for the ILP, -9.1 to +5.8 % for the baseline; F_j = 12.03 USD per window | First siting result with y_j free; expect cheapest certificate-satisfying set unless demand is stressed (SC-1) |
| B13 | L4-P3 | (12)-(14), (20)-(21), (28) | Operations-only special case: fix x_ka (from simulator or solved instance), which fixes s_jqt and S_jt via (12), and solve the remaining (n, c, h, z) program; feed TOU pi_jt through the existing dict in `or_instance.py` | round-1 chained decomposition 1.6 / 3.1 / 95.3 % | Station-level charging study at city scale without a new model |
| B14 | L4-P7, R7 | (26)-(33) | zeta sweep {0.80, 0.85, 0.90, certified max} as a cost-vs-service front; report (27)-(32) split by stakeholder as E2 p.9 asks | zeta 0.90 premium 0.94 USD (0.19 %) at x0.75, 37.4 USD (5.5 %) at x1 | Replaces the single weighted number |
| B15 | L3-P4 | (5)-(6), (9), (12), (22) | Set Gurobi root LP method explicitly; measure LP vs tree time before any reformulation | LP bound 0.014 % below optimum at 1.15 M columns, 0.04 % at 2.64 M | Decides whether branch-and-price is ever needed |

## 7. scope_extensions (new formulations, outside (1)-(33); E2 p.9 lists the first and fourth)

| # | Source | Extension | Sketch of formulation | Validation |
|---|---|---|---|---|
| C1 | R6, L3-P2 | Real-time information (rolling horizon) | SC-2 above; windows with carried state, non-anticipativity, (9)/(16)-(18) only in the last window | E7 on the 30 E2u instances, lambda in {0, 10, 20 min} |
| C2 | L4-P2, P4(b), R5 | Repeatable daily operation | n_jq0 as variables with sum_q n_jq0 = B_j and n_jqH = n_jq0 (strict periodicity) or the energy-periodic pair n_jLH >= n_jL0, sum_q q n_jqH >= sum_q q n_jq0; fleet closure sum_k sum_{a terminal from (v,H,q)} q x_ka >= sum_k q0_k; night window with I = empty; (28) with TOU pi_jt and a demand charge Pi_g >= p_ch sum_{j in g} sum_{q<L} c_jqt for all t | Only after SC-1 shows the battery side can bind; compare with the rho/R_end sensitivity of B2 |
| C3 | L4-P5 | Rider behaviour / partial control | No new rows: for k in K^n fix x_ka = xbar_ka (LB = UB, the mechanism of `verify_mip_start`); sweep compliance alpha = |K^c| / |K| in {0, 1/6, ..., 1}; behavioural arc restrictions swap_q_max = q_thr, no idle wait arcs at sites | Value-of-coordination vs compliance curve on E2u seeds 0-4 |
| C4 | P8 | Order stacking (2-3 orders per delivery action) | Multi-order arcs with completion times from (2) applied along the sequence; (6) becomes sum_k sum_{a : i in S_a} x_ka + u_i = 1; (30) sums theta over S_a | Low priority; run the fleet sweep B8 first, since bikes (not batteries) are the binding resource at x1.5 |
| C5 | L4-P1 | Scenario-robust siting for NYDOT | Two-stage: first stage y, B, C under (7)-(8) and the budget row; second-stage copies of (5)-(6), (9)-(22) per demand scenario s with probability p_s; optional access row sum_{j : g(v_z, j) <= gbar} y_j >= 1 per zone z | Enumerate C(6,3) = 20 subsets x 10 seeds x ~45 s on nyc4h after B12 |
| C6 | R8 | Brand-locked / heterogeneous batteries | Type index b: n_jqtb, c_jqtb, z_eqb, swap arcs only at S_{beta(k)}; (13)-(14), (16)-(18) per type, (15), (20)-(22) summed | Documented only; not for the current paper |
| C7 | L3-P4 | Branch-and-price solution method | Dantzig-Wolfe master over bike paths with shortest-path pricing on the acyclic (v,t,q) network; same LP bound as (5)-(22) | Only for 20-50 bikes / 8 h (~21 M arcs); not supported by round-3 timings |

## 8. keep_as_is

(1)-(4) arc labels and construction (route set and rounding are data; see B5, B11); (5) flow conservation; (6) assignment; (7)-(8) opening logic; (9) terminal certificate (q_res is data); (10)-(11) transfers; (12)-(14) swap/charge/inventory balance; (15) site capacity; (16) initial stock (N^0_jq may be given as data); (17)-(18) recovery targets (rho, R_end_j are data); (19) charger power as a derived quantity; (20)-(21) charger and grid limits; (22) swap positions; (23)-(25) transport-vehicle load conventions; (26)-(32) scalar objective with per-order P_i, w_i, v_i; (33) budget and service-share rows. Section 1 scope statement ("strategic behaviour not assumed") and Section 2 assumptions stay, with the five listed extensions (real-time information, FCFS, transport routing, degradation, repeatable operation) as the scope roadmap.

## 9. Suggested next round (round 4)

1. **Calibration pass (B1, B2, B5, B6; one week).** Shift P_i by the prep constant; R_end_j = 0 at swap-only sites; eps = 25 Wh / L = 24 / p_ch = 0.333 kW; tail_slots >= 12. Re-run the 30 E2u instances and the 15 E3u pairs. Report the headline with both P_i conventions and both end-target settings. This is the E6 that was planned in round 1 and never run.
2. **Energy-stressed family (SC-1 / L4-P6; two weeks).** |K| = 8, 48 orders, q0 ~ U{2..4}, B_j = C_j = 1, P_j = 1.4 kW; re-run E3u / E4u / E8 tables; then the usd8h single-ILP probe and the fleet sweep B8.
3. **Rolling-horizon wrapper (SC-2 / E7; two weeks, no change to ilp.py).** Separate coordination from foresight on the E2u instances; this is the number the paper should headline.
4. **E5 siting with y_j free (B12)** on nyc4h once step 2 shows a non-flat objective.
5. **Paper text.** Add the three remarks of SC-3 and SC-5 (after (31), (5), (4)); state that rho, R_end_j, q_res, eps, L and the route set are data; present (17)-(18) with their relaxed control. No equation of E2.pdf is rewritten.

Sources: `notes/extracted/E2.txt`, `notes/extracted/E2_Example.txt` pp.10-15, `notes/SUMMARY.md` (rounds 1-3), `notes/DECISIONS.md`, `notes/workflow1_result.json` (audit I2, I6, I7, I10, I11, I15, I23), `notes/workflow5_round2_partial.json`, `ebike_swap_sim/outputs/{e2u_round3,e3u_round3,e4u_round3,e8_round3}/RESULTS_final.md`, `ebike_swap_sim/outputs/{e2_coord,e3,e4_sizing}/RESULTS_v2.md`, `ebike_swap_sim/outputs/e2u_coord_usd/RESULTS_final.md`, `ebike_swap_sim/outputs/r2_probe/`, `notes/cost_calibration.md`.
