# From the reading list to the model: what to adopt, modify and optimise

Date: 2026-10-16. Scope: the five papers in `reading/` (guide `reading/README.md`) read against our
current work: the E2 integer program (`notes/extracted/E2.txt`, (1)-(33); code `ilp.py`, `arcs.py`,
`evaluate.py`), the event-driven baseline (`baseline.py`), the instance and data pipeline
(`generator.py`, `data_nyc.py`, `acs_weights.py`, `costs.py`), experiment rounds 1-3 (E2u, E3u, E4u,
E8) and the E9 bi-level siting study (`bilevel.py`, `notes/bilevel_siting_design.md`,
`outputs/e9_bilevel/RESULTS_E9.md`). Issue numbers refer to the supervisor brief
(`paper/brief_issues.tex`, Issues 1-15).

## 1. Summary

* **No equation of E2 (1)-(33) needs to change.** Six equation changes were proposed from the papers
  (end-of-window boundary conditions three times, swap positions as a decision, a demand charge,
  multi-rate chargers). Each was checked by two independent refuters, and all six were refuted by
  both (keep count 0 of 2 in every case). Every one of them is either reproducible with existing
  parameters or a wrapper, or slack at our scale. They are written out in Section 5 as optional
  extensions, each with the condition under which it would become necessary. This confirms the
  verdict of `notes/E2_formulation_review.md`.
* **The papers matter mostly for parameters, baselines, instances and solvers.** The highest-value
  items are: a physical energy calibration (eBaaS), a stronger and fairer baseline (eBaaS, IJCAI-25,
  IJCAI-15), an aggregated-flow implementation of E2 plus an LP/Benders bound for E9 (ITSC-21), and,
  later, a learned surrogate for the siting upper level (Neur2SP).
* **Two papers explain our "negative" results.** IJCAI-25 explains why shuttles are worth nothing
  inside a window (swaps are 1:1 in place, so station counts drift only through transfers, and
  rebalancing gains vanish at 3-station clusters). ITSC-21 reports the same structure we see: the
  fleet, not the charging infrastructure, is the binding and dominant resource.
* **One paper gives an external benchmark for a second headline.** eBaaS measures the value of
  having a swap network at all (6.2 km of avoidable riding per rider per day, 20-28.5 % more orders);
  our 29.6 % measures the value of coordinating a given network. Reproducing their counterfactual
  inside our framework gives both numbers on the same instances.

## 2. Per-paper connection table

| # | Paper | What it does | Closest link to our work | Main use for us |
|---|---|---|---|---|
| 1 | Ding et al., eBaaS, WWW 2025 | Deployed AIoT battery-swap service for delivery e-bikes (Hangzhou Yugu): forecast-driven battery allocation, BMS lock-out, range prediction; EIEM counterfactual "ride home to charge" on 50,000 riders/day | Same application. Data for (1)-(3) (40 km/kWh), sigma_j and (22) (swap < 10 s), demand peaks 10-13 h and 17-18 h, 2 km cabinet coverage. No optimisation model | Energy calibration; value-of-network experiment; range-aware, reservation-based baseline rule; E9 instance redesign; motivation |
| 2 | Li et al., battery-swapping RL, IJCAI 2025 | Daily MDP of station stock on cyclic rebalancing routes, W-PPO policy; operator data (500k batteries, 30k stations) | Route vehicle = our transfer services (10)-(11); stock update = count-only, daily version of (13)-(14); overnight full recharge replaces (19)-(21) | Explains zero within-window transfer value; station KPIs (SBUR, BSR); cost-aware zero-sum transfer rule; cyclic-route timetable; RL as an online comparator |
| 3 | Xiong et al., EV charging station placement, IJCAI 2015 | Bi-level: planner places chargers under a budget, drivers form a congestion-game equilibrium; single-level MINLP via simple-deviation conditions; relax-and-round OCEAN-C | Closest precedent for E9 (budgeted leader, reacting follower). Our follower is system-optimal, so E9 collapses to a two-stage stochastic ILP; theirs collapses through equilibrium conditions | Self-interested station-choice follower; standard planner baselines (CSCD/CSTC/CSAV) and robustness sweep; relax-and-round screen; marginal-lever table |
| 4 | Dumouchelle et al., Neur2SP, NeurIPS 2022 | Learns the second-stage value of a two-stage stochastic program with a ReLU network and embeds it as a MIP | E9 is exactly a two-stage SIP with MIP recourse; our integrated model (algorithm A, 5.35 M variables) fails like their extensive form; our evaluator cache is their training set | Surrogate-based siting search, surrogate screen, approximate bounds, evaluation protocol; only on families where layouts differ by more than the surrogate error |
| 5 | Luke et al., AEV fleet operations and charging siting, ITSC 2021 | One LP on a (location, time, SoC) network jointly sizes chargers and plans an aggregated fleet flow; TOU price, demand charge, periodicity | Same time-expanded (v, t, q) network as E2; their aggregated flow vs our per-bike arc copies; their joint LP vs our failed integrated MIP | Aggregated integer flow (equivalent E2 implementation); LP/Benders bound for E9; capacity-matched siting baseline; TOU data; fleet x battery trade-off; periodicity as a parameter bracket |

## 3. Shared findings that the papers confirm or explain

| Our finding | Paper evidence | Consequence |
|---|---|---|
| Coordination saves about 30 %, mostly punctuality; gap rises with demand (15.4 / 31.2 / 42.1 %) | eBaaS: savings larger at peak (6.59 km, +560 m) | Same qualitative pattern; report peak vs off-peak split |
| Stations, chargers, transfers barely bind at 6 bikes / 4 h | ITSC-21: fleet procurement 78-84 % of cost, same fleet for all EV models; eBaaS riders ride about 8.6 km per rider-hour vs our 4.0-4.8 km per bike-hour | Our instances are under-stressed per bike-hour; the battery side needs a data-grounded multi-swap day, not arbitrary q0 cuts |
| Shuttle value 8.6 USD only because of end targets (17)-(18); 0.00 USD relaxed | IJCAI-25: imbalance comes from batteries returned at a different station; gains at 3-station routes only 0.36-4.62 % | Structural explanation: conservation (23) + 1:1 in-place swaps + small clusters |
| E9 picks one co-located site with 3-4 spares | eBaaS: 2 km cabinet coverage radius, value driven by rider home locations | The Midtown box (2 x 3.5 km) with riders starting at the sites suppresses multi-site value |
| Integrated E9 MIP gives no usable bound | Neur2SP: extensive form intractable with MIP recourse; ITSC-21: 5.3 M-variable LP solved in 2.33 h | Use LP relaxation of an aggregated model as a bound; learned surrogate for search |

## 4. Recommendations

Each item lists its source paper(s), the exact target in our work, the effort, and the brief issue it
addresses. Items are deduplicated across papers and ranked by priority, then impact.

### 4.1 Adopt (take over as is)

| Rank | Item | Source | Target | Effort | Issues |
|---|---|---|---|---|---|
| A1 | **Physical energy calibration.** Set `config.wh_per_km = 25` (eBaaS 40 km/kWh) together with the planned de-rounding B5 (eps = 25 Wh, L = 24, `energy_rounding = concat`). Cite eBaaS Table 1a (linear coefficient model, MAE 1.35 km vs 1.12 km for a Transformer) for the linear energy model, and Fig. 1 (swap < 10 s) for sigma_j = 1 slot. Report swaps per window under old and new calibration | eBaaS | `generator.py`/config, (1)-(3), sigma_j in (22) | low | 11, 2 |
| A2 | **Narrative positioning.** Cite eBaaS and IJCAI-25 together as the delivery e-bike swap line; eBaaS measures the value of the network, we measure the value of coordinating it (dispatch + swaps + charging + transfers under grid limits). Use IJCAI-25 to explain the zero within-window transfer value. Frame V_policy / V_ILP (1.31-1.41 in E9.5) as a price of decentralisation relative to a myopic rule (IJCAI-15). Cite ITSC-21 for "the fleet binds" | eBaaS, IJCAI-25, IJCAI-15, ITSC-21 | paper introduction, related work, E3u/E9 discussion | low | 3, 13 |
| A3 | **Metric pack** computed from existing schedules, no change to optima: (a) SBUR_j = full batteries issued / B_j and min_j SBUR_j, swaps per storage slot, batteries saved vs default sizing; (b) rider station time per swap (detour + wait); (c) outage/stranding rate (bike-windows with a stranded bike or refused swap); (d) empty (reposition) km per bike-hour; (e) peak kW per site and kWh by price period | IJCAI-25 Def. 1-2; IJCAI-15 Eq. 3/7; eBaaS Sec. 2.4; ITSC-21 Table II, Fig. 3 | `evaluate.py` metrics; E3u/E4u/E9 tables | low | 2, 13 |
| A4 | **Siting baseline set and lever table for E9.** (i) Capacity-matched "present-day" layout (existing Midtown cabinet locations if a list can be compiled, else the deck's demand-proportional layout) rescaled to the same total B and C, operations optimised on both; (ii) CSCD (demand-proportional), CSTC (inverse distance-weighted access) and CSAV (uniform) at equal budget, with V vs budget m and vs demand multiplier; (iii) one marginal-lever table at the chosen layout (+1 spare, +1 charger, +1 swap position, one shuttle, +10 % grid) under each follower. All reuse the `LowerLevelEvaluator` cache | ITSC-21 Sec. III-B; IJCAI-15 Sec. 5.1-5.2, Table 1 | `bilevel.py` deck/cross sub-experiments, `RESULTS_E9.md` | low | 13, 14 |
| A5 | **Value-of-the-network experiment (new E10).** Reproduce eBaaS's EIEM counterfactual: on E2u/E8 instances replace the swap network by a home-charging facility at each depot (sigma_j = full charge, about 12-24 slots; M_j = B_j = abs(K); F_j = 0), solve with ILP and baseline, report invalid km per bike-hour and orders given up. Report value of network, value of coordination (29.6 %) and their sum | eBaaS Sec. 3.3-3.4, eq. 3-5, Table 1b | new experiment script; `evaluate.py` | medium | 1 (context), headline |
| A6 | **Fleet x spare x pack trade-off.** Sweep abs(K) in {4, 6, 8, 10}, B in {1..4}, pack size L*eps in {0.5, 0.75, 1.0} kWh at the E9 layout; price an allocated bike/rider cost; report the iso-cost frontier "one more bike vs one more spare" and served share. Subsumes the fleet sweep the brief asks for at 1.5x demand | ITSC-21 Table I; formulation review B8 | experiment (data only: abs(K), L, eps) | medium | 4, 13, 2 |
| A7 | **Online learned comparator (RL).** Wrap `baseline.py` as a gym environment controlling only the station layer (charging + transfers), PPO-clip, seed-level CIs; run only on the stressed family. Expected near-zero gain on current instances | IJCAI-25 Sec. 4.1 protocol | planned E7 table | high | 1 |

### 4.2 Modify (change an existing component, no E2 equation change)

| Rank | Item | Source | Target | Effort | Issues |
|---|---|---|---|---|---|
| M1 | **Boundary conditions through parameters only** (the refuters' consensus for IJCAI25-5, IJCAI25-6, L5-3): set R_end_j = 0 at swap-only sites; report a grid rho in {0, 0.25, 0.5, 1} x R_end_j in {0, 1}; add a periodic bracket rho = 1, R_end_j = B_j at every swap-capable site (hubs keep B_j = 0), which with (16) and (24) forces n_jqH = n_jq0 exactly; use the relaxed control (rho = R_end = 0) as the headline and the written targets as "price of recovery". Add an end-state adjustment in `evaluate.py`, applied identically to ILP and baseline: pi (eps/eta) [sum_j sum_q (L - q) n_jqH + sum_k (q0_k - q_k(H))^+] | IJCAI-25 Sec. 3.1; ITSC-21 (3i); refuter verdicts | (17)-(18) parameters; `evaluate.py` | low | 3, 7 |
| M2 | **Range-aware, reservation-based swap rule in the baseline.** Replace q <= q_thr = 3/12 by: swap when level < g(next order) + g(v, nearest stocked site) + margin T (T = mean remaining level at swap); on deciding, decrement the reservable full stock at the chosen site. Validation target: outage rate about 50 % below the q_thr rule | eBaaS Sec. 2.4, 3.2 | `baseline.py` trigger, `stock_aware_site`, new reservation flag | medium | 1, 12 |
| M3 | **Cost-aware, zero-sum transfer rule in the baseline.** At each service departure move min(surplus at origin, forecast deficit at destination, U_e), only if P_i * Pr(stock-out before u_e) * load > f_e + v_reb * load; cap loads at about 7 of 10-20 slots. Replaces REORDER_POINT, which is dominated by NONE (+165 to +207 USD) | IJCAI-25 Sec. 3.1 action design | `baseline.py` `_step8_transfers`, `TRANSFER_RULES` | medium | 3, 7 |
| M4 | **Self-interested station-choice follower.** Rider picks the open swap site minimising travel slots + expected wait (arrivals / (M_j / sigma_j)) + stock-out wait; variant (a) logit, variant (b) iterated best response over simulated days (equilibrium). Use it as E9 algorithm E follower and in the cross-evaluation; this answers the deck topic "rider behaviour change". Also gives the compliance sweep (fraction of bikes following the follower) | IJCAI-15 Sec. 3.2-3.4 | `baseline.py` `_go_swap`/`stock_aware_site`; `bilevel.py` follower E | medium | 13, 1 |
| M5 | **Data-grounded energy-stressed family.** Demand peaks 10-13 h and 17-18 h within 08:00-22:00 (replace the undocumented 28/45/12 % curve); riding intensity towards about 120 km per rider-day (about 3 kWh at 25 Wh/km); lunch + dinner instance (8 h) via the rolling wrapper; report gap at peak vs off-peak. Add a commercial TOU price (`pi_peak`, `price_peak_hours`, currently None in all R2.1 variants) once a 24 h or 8 h window exists | eBaaS Sec. 1, 4.1-4.2; ITSC-21 Sec. III-A-b | `generator.py` demand curve, H, SC-1; `costs.py` | high | 2, 10, 13 |
| M6 | **E9 instance redesign.** Candidate region beyond the Midtown box (Manhattan below 110th St tiled in 2 km cells); rider depots at outer-borough entry points (bridges, 125th St) instead of at the sites; access radius D anchored to the 2 km coverage. Deploy the surrogate (O3) only here, where layouts differ by more than its error | eBaaS Sec. 4.2.1, Fig. 4c-d; Neur2SP (N6) | `sites_nyc.py`, `data_nyc.py` depots, access row [U4] | medium | 13 |
| M7 | **Rolling horizon with forecast-based battery plan.** Battery-side decisions (B_j, transfers, charging) planned on forecast scenarios from the generator; rider dispatch sees only released orders (lookahead 0 / 10 / 20 min). Splits the value of perfect information into battery-side and rider-side parts | eBaaS Sec. 2.2 | rolling wrapper (SC-2 / E7) | high | 1 |
| M8 | **Cyclic-route transfer timetable.** Chain services C_m -> C_{m+1} with l_{e_{m+1}} = u_{e_m}, U_e = Cap, closing the cycle; intra-window tours every 60 min and one night tour. No change to (10)-(11): batteries can stay on board through stops by E2's event order; mind K_j in (15) at stops. Gate: only after the stressed family makes stock bind | IJCAI-25 Sec. 2 | `generator.py` `DEFAULT_SERVICES_SPEC`, `add_services` | medium | 3 |
| M9 | **Battery lock-out robustness.** Remove 2-5 % of batteries at random times through data-fixed transfers to a dummy sink (h_e, z_eq fixed to 1), re-run the chosen E9 layout and the E4u spare sweep | eBaaS Sec. 2.3 | instance data; E4u/E9 | low | 13 |
| M10 | **Gated sizing and tariff levers as data.** (a) Swap positions: add role variants such as SC-M2 (M_j = 2, F_j and Fhat_j raised by the position cost) to the size menu, after first reporting peak LHS(22)/M_j and the LP dual of (22); (b) demand charge: sweep P_j over {0, p_ch, ..., C_j p_ch} and report V(P_j) + p_dem P_j (exact per metered site); (c) charger speed: run B5 (p_ch 0.333 vs 0.667 kW) as a sensitivity and add a text remark that C_j counts unit-rate plug equivalents | IJCAI-15 (X7); ITSC-21 (L5-5, L5-8); refuter verdicts | `sites_nyc.py`/`bilevel.py` menu; E4u sweeps; E2 text remark next to (19)-(20) | low | 2, 9 |

### 4.3 Optimise (solver and implementation; same optimum or better search)

| Rank | Item | Source | Target | Effort | Issues |
|---|---|---|---|---|---|
| O1 | **Aggregated integer flow.** Replace the per-bike arc copies by one integer flow x_a >= 0 on the union (v, t, q) network: supply at (v0, 0, q0) = number of bikes starting there, all terminal arcs into one sink with demand abs(K); (6) gives x_a <= 1 on order arcs; (12), (22), (29), (30) are already sums over k; (9) becomes x_a <= U_a y_j. Recover bike schedules by integer path decomposition (exact because no cost or parameter depends on k; verify that no instance option is bike-specific). LP bound is unchanged; variable count and bike-permutation symmetry drop (expected 4-6x fewer x). Validate against the toy (12.5 / 11.2 / 106) and the 30 E2u and 40 E8 optima. This is an equivalent implementation of E2, not an equation change | ITSC-21 Sec. II-c | `arcs.py`, `ilp.py`, `bilevel.py` `integrated_stochastic_ilp` | medium | 14, 4, 6 |
| O2 | **LP bound, Benders and LP-based screen for E9.** Solve the aggregated two-stage model with x, n, c, z, B, C continuous (barrier, no crossover) for a lower bound at every budget m; L-shaped Benders with (y, B, C) and (33) in the master and per-scenario operations-LP cuts; replace the baseline-policy screen by a relax-and-round shortlist from the LP (top-k candidates by swap volume S_j*, B rounded down/up, C = ceil(C_j*), round on usage not on y_j). Operations LP is tight at the root (26/30 E2u, 37/40 E8), so the bound should be useful | ITSC-21 Sec. II comments, III-C; IJCAI-15 OCEAN-C (Alg. 1) | `bilevel.py` `superset_bound`, algorithm A, `_screen` | medium | 14, 15 |
| O3 | **Neur2SP surrogate pipeline for the siting upper level.** (a) Training set: cached OPTIMAL ILP rows (e9-2, open_sites; no all_candidates rows) plus 1,500-3,000 stratified random layouts x 3 seeds (about 11-22 h on 3 processes); target = residual opex minus scenario base, with served share as auxiliary output; hold out seeds 3-4. (b) Surrogate screen in `_screen(..., screen='surrogate')`. (c) Surrogate MIP: per-seed NN-P copies (2 hidden layers 32/16, 144 binaries), upper-level rows [U1]-[U4] and (33), pool of 20 layouts re-priced by the true ILP. (d) Evaluation: E9.1 must return L02:SC:B2:C1 at 676.22; Spearman rho on the singleton ranking; regret vs deck heuristic; "time for A to reach the same quality". (e) Approximate bounds: quantile/conformal lower surrogate floored at the superset LP bound, candidate pruning, reduced exact algorithm A on 3-4 surviving candidates | Neur2SP Sec. 4.1-4.3, 5-6, App. D | `bilevel.py` new algorithm F, `export_training_set`, `_screen`; new E9.7 | high | 14, 15, 13 |
| O4 | **Static aggregate surrogate for city-wide candidate sets.** NTA zones with peak swap demand, candidates within D blocks, travel + queue (y_j / (mu M_j)) + fluid stock-out term, investment (33) + F_j y_j; relax and round to shortlist, then exact E2 pricing. Validate against the Midtown ranking (L02 ~ L01 < L05 < L07 < L08 < L11) before use | IJCAI-15 P3, Eq. 3, 10 | `bilevel.py` upper-level shortlist | medium | 13 |
| O5 | **Policy-aware and robust siting.** Second surrogate on baseline-policy labels (about 6 ms each, 50,000+ labels in minutes) embedded beside the ILP surrogate: policy-aware, robust (min max) or regret-constrained layouts | Neur2SP + IJCAI-15 follower view | `bilevel.py` cross_evaluate / follower E | medium | 13 |

*O2 status (2026-10-18):* implemented as designed in `notes/o2_siting_bound_design.md` (corrections C1-C16):
`ebike_swap_sim/benders.py` (safe Lagrangian LP cuts from per-scenario aggregated LPs with artificial columns, integer
master over menu binaries, integer and combinatorial cuts, exact pricing with BestBdStop, relax-and-round screen,
LP screen for the greedy), runner `experiments/r6_o2_siting.py` (`--smoke`, `--midtown-validate`, `--manhattan`,
`--analyse`), tests `tests/test_o2_benders.py` (toy, Threads 1). Midtown validation and Manhattan runs are pending
until the round-6 lanes finish.

## 5. E2 verdict and optional extensions

### 5.1 Verdict

No E2 equation changes. The six proposed changes and the refuters' findings:

| Proposal | Source | Refuter 1 | Refuter 2 | Why not now |
|---|---|---|---|---|
| Day-boundary count target with overnight charge capacity, replacing (17)-(18), plus night energy in (28) | IJCAI-25 | optional extension | optional extension | Paper supports only a count target; (17b)-(17c) and the night price are additions; on our data the rows are redundant or slack; the count effect is available by setting R_end_j and rho |
| Learned terminal value of end stock, replacing hard targets | IJCAI-25 | optional extension | optional extension | Flat price means betas are near zero (at most about 0.21 USD per empty battery); chargers have 0.000 marginal value; the paper's critic is a PPO baseline, not a terminal value |
| Swap positions m_j as a sizing variable in (22), (27), (33) | IJCAI-15 | solver/wrapper | parameter/data | (22) never binds; the E9 upper level already sizes from a menu, so M_j can be a menu attribute |
| Periodic boundary conditions replacing (16)-(18) | ITSC-21 | optional extension | parameter/data | With all-full start (16), rho = 1 and R_end_j = B_j already give strict periodicity; the 4 h window cannot be periodic for bikes anyway |
| Demand charge (peak-power variable) in (21), (28) | ITSC-21 | optional extension | optional extension | Peak takes only multiples of p_ch, so a sweep over P_j prices it exactly; worth about 0.03 USD per window at our caps |
| Multi-rate chargers with throttling in (13), (14), (19), (20), (27), (28) | ITSC-21 | optional extension | optional extension | E2 already throttles (charging may pause); chargers are idle; B5 already calibrates p_ch |

None of the current research questions (brief Issues 1-15) needs any of them: Issue 1 is a wrapper
question, Issues 2, 4 and 13 are instance questions, Issue 3 is a parameter choice, Issues 14-15 are
solver questions. Two text remarks (not equation changes) are recommended for E2.pdf: next to
(17)-(18), state that rho = 1 and R_end_j = B_j with (16) and (24) give a periodic stock; next to
(19)-(20), state that C_j counts unit-rate plug equivalents and that pausing gives any average rate
up to C_j p_ch. The aggregated flow (O1) should be documented as an equivalent implementation.

### 5.2 Optional extensions (written out, with the trigger condition)

Notation follows E2; new symbols are defined in each block.

**OE1. Terminal value of end-of-window stock** (source: IJCAI-25 critic, ADP view).
For j in S and m = 1..K_j, add omega_jm in [0, 1] and

    (17v)  sum_{m=1}^{K_j} omega_jm <= n_jLH            (or <= (1/L) sum_q q n_jqH, energy-weighted)
    (26')  min C_setup + C_elec + C_travel + C_orders + C_reb - sum_{j in S} sum_{m=1}^{K_j} beta_jm omega_jm,
           beta_j1 >= beta_j2 >= ... >= 0 (given), rho = R_end_j = 0 in (17)-(18) (or a small floor).

Betas are inputs refreshed between windows (LP duals of (16) in the next window, or a fitted value).
*Necessary when:* a rolling horizon or a multi-window day (Issue 1, scope C2) runs on instances
where end stock has real next-window value, i.e. chargers or stock bind (stressed family) or prices
vary by time (TOU), so the betas are clearly nonzero. Until then the evaluate.py end-state
adjustment (M1) gives the same accounting.

**OE2. Periodic boundary conditions with endogenous start stock** (source: ITSC-21 (3i)).

    (16p)  n_jq0 in Z>=0 for all q,  sum_q n_jq0 = B_j            (j in N)       [replaces (16)]
    (17p)  n_jqH = n_jq0                                          (j in N, all q) [strict], or
    (17e)  sum_q n_jqH = sum_q n_jq0,  sum_q q n_jqH >= sum_q q n_jq0  (j in N)  [energy form]
    (18p)  sum_k sum_{a terminal from (v,H,q)} q x_ka >= sum_k q0_k                [fleet energy closure]

rho and R_end_j drop out; in (27) b^B_j loses its initial-charge component. In the aggregated form
(O1) the start supplies sigma_vq >= 0 with sum sigma_vq = abs(K) become variables and terminal inflow
at (v, H, q) equals sigma_vq.
*Necessary when:* a 24 h horizon with a night period is solved (after O1/O2 make 288 slots
tractable) and the start stock is allowed to be partly charged, or bike start states are decisions.
With an all-full start, the parameter bracket in M1 is already exact.

**OE3. Overnight day-boundary target** (source: IJCAI-25 Sec. 3.1). With N^night overnight slots
(N^night >= L) and night price pi^night, for j in S cap C:

    (17a)  sum_{q=0}^{L} n_jqH >= R_end_j y_j
    (17b)  sum_{q<L} (L - q) n_jqH <= N^night C_j
    (17c)  p_ch sum_{q<L} (L - q) n_jqH <= N^night P_j y_j
    (18')  sum_{j in S cap C} sum_q n_jqH + sum_{j in S\C} n_jLH >= rho sum_j B_j
    (28')  C_elec += sum_{j in C} pi^night (eps/eta) sum_{q<L} (L - q) n_jqH

Swap-only sites keep (17) as written.
*Necessary when:* separated layouts with charge-limited sites are studied over consecutive days and
overnight charger capacity, not in-window charging, decides the morning stock. Lowest priority. Both
refuters found it redundant on current data, and OE2 covers the same need more cleanly.

**OE4. Swap positions as a sizing variable** (source: IJCAI-15 service capacity x_i).

    m_j in Z>=0 (j in S),  y_j <= m_j <= Mbar_j y_j
    (22')  sum_k sum_{a in A^sw_k(j): l_a <= tau < u_a} x_ka <= m_j        (j in S, tau in T)
    (27')  C_setup = sum_j (F_j y_j + b^B_j B_j + b^C_j C_j + b^M_j m_j)
    (33')  sum_j (Fhat_j y_j + bhat_j B_j + chat_j C_j + mhat_j m_j) <= B

With m_j = M_j y_j this is the current E2.
*Necessary when:* the diagnostic in M10(a) shows a positive LP dual on (22), which is likely only under
the self-interested follower (M4) or 8-10 bikes per site, and the size menu becomes too large to
enumerate role variants. Before that, menu variants such as SC-M2 are the preferred route.

**OE5. Demand charge** (source: ITSC-21 (3b), (3j)).

    Pi_g >= 0 per supply group g
    (21d)  Pi_g >= p_ch sum_{j in C: gamma(j)=g} sum_{q<L} c_jqt              (g in G, t in T)
    (28')  C_elec = sum_{j,t} pi_jt (eps/eta) sum_{q<L} c_jqt + sum_g p^dem_g Pi_g

p^dem_g is the monthly tariff rescaled to the horizon. Caps (20)-(21) stay.
*Necessary when:* all three of the following hold: (i) a 24 h horizon; (ii) chargers bind; (iii) a
material NYC demand tariff applies, with several sites behind a shared meter so that the exact P_j
sweep in M10(b) becomes multidimensional.

**OE6. Multi-rate chargers with throttling** (source: ITSC-21 Sec. II-a, Eq. 2). Charger types r with
rate m_r levels per slot, counts C_jr, variables c_jqmt (q -> q + m):

    (13')  ... - sum_m c_jqmt + sum_m c_{j,q-m,m,t} ...                     [charging terms of (13)]
    (14')  sum_m c_jqmt + D_jqt <= n_jqt                                   (q < L)
    (20')  sum_{i>=r} ( sum_q sum_{m in (m_{i-1}, m_i]} c_jqmt - C_{j,i} ) <= 0   (r in R_j, j in C, t)
           sum_q sum_m m (eps/(eta Delta)) c_jqmt <= P_j y_j, and analogously in (21)
    (7')   sum_r C_jr <= K_j y_j;  (27') sum_r b^C_jr C_jr;  (28') pi_jt (eps/eta) sum_q sum_m m c_jqmt

*Necessary when:* (20) or (21) binds (stressed or 24 h family) and fast chargers would face fewer than
m non-full batteries in stock, so plug-equivalents (M10(c)) stop being exact, or per-kW prices
differ non-linearly between charger types.

## 6. Prioritised next steps

| Step | What (items) | Effort | Brief issues addressed |
|---|---|---|---|
| 1 | **Calibration and accounting package**: A1 (25 Wh/km with B5), M1 (R_end_j = 0 at swap-only sites, rho x R_end grid, periodic bracket, end-state adjustment), A3 (metric pack). Re-run E2u x1 and E3u on seeds 0-4 | low (2-3 days, mostly cached runs) | 3, 7, 11, 2 |
| 2 | **Fair baseline**: M2 (range-aware + reservation swap rule), M3 (cost-aware zero-sum transfer rule); re-run the E2u/E8 headline and E3u separated layouts; report how much of 29.6 % survives against an operator-grade rule | medium (1 week) | 1, 3, 12 |
| 3 | **Aggregated E2 and an E9 bound**: O1 (aggregated integer flow, equivalence check on toy, E2u, E8), then O2 (LP bound + Benders + LP screen) at every budget; makes the lossless pruning run (Issue 6) and the 6-10 bike fleet sweep (Issue 4, A6) cheaper | medium (1-2 weeks) | 14, 15, 6, 4 |
| 4 | **Stressed, data-grounded family**: M5 (eBaaS demand peaks, 120 km/day intensity, 8 h lunch + dinner, TOU once 8-24 h), A6 (fleet x spare x pack), M6 (E9 region and depots redesign); success = a battery constraint with a positive shadow price | high (2-3 weeks) | 2, 4, 10, 13 |
| 5 | **Information and behaviour**: M7 (rolling horizon with forecast battery plan, lookahead 0/10/20 min), M4 (self-interested follower, compliance sweep), A5 (value-of-network E10) | high (3 weeks) | 1, 13 |
| 6 | **Siting at scale** (only after step 4 makes layouts differ): A4 baselines, O3 Neur2SP pipeline with E9.7 evaluation, O4 city-wide aggregate shortlist; optional O5 and A7 | high (3-4 weeks incl. about 20 h of label generation) | 13, 14, 15 |

Gated items (run only when their condition is met): M8 cyclic routes and M9 lock-out (after step 4),
M10 levers (after the (22)/(20) diagnostics), OE1-OE6 (Section 5.2 triggers).

## 7. Mapping onto the supervisor brief

| Brief issue | Items from the reading | Effect |
|---|---|---|
| 1 Foresight vs coordination | M7, M2, M4, A7, OE1 (if needed), A5 for context | Splits 29.6 % into foresight, coordination and baseline-strength parts; RL as an online comparator |
| 2 Battery side never binds | A1, M5, A6, A3, M10 | Data-grounded intensity (eBaaS) instead of arbitrary cuts; fleet vs battery frontier |
| 3 End targets create shuttle value | M1, M3, A2, M8 | Parameter route confirmed; structural explanation from IJCAI-25; fair transfer rule |
| 4 90 % service infeasible | A6, O1 | Fleet sweep becomes cheaper and answers "how many bikes" |
| 5 Drop penalty vs waiting | none of the papers | Stays a parameter decision (waiting charged from food-ready time) |
| 6 NYC pruning restricts only the plan | O1 | Aggregation makes the lossless variant affordable |
| 7 Solver gap in E3u | M1, O1 | R_end_j = 0 at swap-only sites removes the shuttle; smaller model |
| 8 Synthetic geometry | none | Unchanged |
| 9 Low-confidence prices | M10, M5 (TOU) | Tariff and charger-speed sensitivities as data |
| 10 Demand inputs partly assumed | M5 | eBaaS peaks and operating day replace the assumed hourly curve |
| 11 Energy rounding | A1 | De-rounding with physically grounded 25 Wh/km keeps a realistic swap rate |
| 12 Wide intervals, weak rule | M2, M3 | Stronger rule should reduce the rule's 4x cost variance |
| 13 Fleet binds in siting | M6, M4, A4, A6, O4, M9 | Instances where siting can matter; behavioural follower; standard baselines |
| 14 No certified gap | O2, O1, O3(e), A4 | LP/Benders bound; approximate bounds with stated coverage |
| 15 Search artefacts | O2 (LP screen), O3 (surrogate screen and MIP) | Screens that rank like the ILP; full-menu search |
