# Implementation decisions for the E2 model (resolved 2026-10-11)

Source documents: `notes/extracted/E2.txt` (model, eq. numbers below refer to it), `notes/extracted/E2_Example.txt` pp.10-15 (toy), `notes/extracted/Battery_Swap.txt` (predecessor), `notes/extracted/ebike.txt` (simulator deck).
Audit details: `notes/workflow1_result.json` (keys `audit.issues`, `identities`, `plan`). Verified reproduction: `notes/verify/toy_e2_example.py` (J = 12.5), `notes/verify/identity_checks.py` (all tables / identities pass).

## Timing conventions (Section 5, verified against toy tables)
- `n[j][q][t]` = stock at boundary t AFTER transport arrivals at t, BEFORE swaps / charging starts / departures at t. Index t = 0..H.
- Transported battery arriving at t is usable at t (swap issue, charging in slot t, re-shipment at t).
- Battery returned by a bike in a swap starting at t enters stock at t+1 (`s[j][q][t]` appears in the balance for n[t+1]).
- Charging in slot t finishes at t+1.
- With sigma_j > 1 the exchange is recorded at the swap start l_a; bike and one swap position stay busy over [l_a, u_a).
- Balance (13): `n[j][q][t+1] = n[j][q][t] - c[j][q][t] + c[j][q-1][t] + s[j][q][t] - 1{q=L} S[j][t] - D[j][q][t] + A[j][q][t+1]`, with fixed zeros `c[j][-1][t] = c[j][L][t] = 0`, `s[j][L][t] = 0`, no c outside C, no s/S outside S. Do not create variables for fixed zeros.
- Joint availability (14): `c[j][q][t] + D[j][q][t] <= n[j][q][t]` (q < L); `S[j][t] + D[j][L][t] <= n[j][L][t]`. Zero-dwell transshipment (arrive at t, depart at t) is allowed as written.
- Storage (15) checked at every boundary t = 0..H: `sum_q n[j][q][t] <= K_j y_j`.
- Initial stock (16): all initial spares full: `n[j][L][0] = B_j`, others 0.
- End targets: (17) `n[j][L][H] >= R_end_j y_j` for j in S only; (18) `sum_{j in N} n[j][L][H] >= rho * sum_j B_j` (sum over ALL facilities, as toy (47)).
- In-transit count m_t = sum over services with l_e < t < u_e (strict), used only as a post-solve check: `sum_j N_jt + m_t = sum_j B_j` for all t.

## Bike arcs (Section 3, toy p.11)
- States (v, t, q), v in V, t = 0..H, q = 0..L. Source s_k = (v0_k, 0, q0_k); one sink z_k per bike.
- Wait: (v,t,q) -> (v,t+1,q), t < H. Energy 0.
- Reposition (route r: tau_r >= 1 for u != v, g_r >= 0, d_r): (v,t,q) -> (v',t+tau_r,q-g_r) if q >= g_r and t+tau_r <= H.
- Deliver (order i, routes r: v->o_i, r': o_i->d_i): u_a = max(t+tau_r, a_i) + hp_i + tau_r' + hd_i; g_a, d_a per energy-rounding option (below); create iff t >= r_i, q >= g_a, u_a <= H. theta_ia = w_i*Delta*(u_a - r_i) + v_i*Delta*max(u_a - b_i, 0). Delivery arcs may start from any v in V (toy p.11) — pruning options restrict this.
- Dominance pruning (optional, lossless): drop delivery arcs with t + tau_r < a_i when t >= r_i (the later start max(r_i, a_i - tau_r) dominates); default ON.
- Swap at facility j in S (keyed by facility, not node): (v_j,t,q) -> (v_j,t+sigma_j,L) for q in 0..L-1 (optionally q <= swap_q_max), t + sigma_j <= H.
- Terminal: (v,H,q) -> z_k labelled j in S iff q >= gbar(v,j) + q_res, with x_ka <= y_j. gbar(v,j) = shortest path over the route library with weights g_r (Dijkstra on levels). If a bike has NO reachable terminal node the instance is infeasible: builder must pre-check and report; optional penalised dummy terminal arc (cost Pi_term) as a switch (default OFF so the written model is reproduced).
- Energy rounding option `energy_rounding`: `'per_leg'` (document (1)-(3): tau_r = ceil(T_r/Delta), g_r = ceil(E_r/eps), g_a = g_r + g_r') is the DEFAULT; `'concat'` (g_a = ceil((E_r+E_r')/eps), tau likewise on the concatenated time) is an option for sensitivity (E6). Toy instance has integer units so both give the same answer.

## Facility / logistics / capacity
- (7)-(8): 0 <= B_j <= K_j y_j; 0 <= C_j <= min(Cbar_j, K_j) y_j; C_j = 0 if j not in C; C_j >= y_j if j in C \ S. Optional flags `battery_swap_v1_bounds` adding y_j <= B_j and C_j <= B_j (Sep-29 model) — default OFF.
- (10): h_e <= sum_q z_eq <= U_e h_e; h_e <= y_{o_e}; h_e <= y_{d_e}. z_eq integer for q = 0..L. D/A from (11) are linear expressions, not variables.
- (20): sum_{q<L} c[j][q][t] <= C_j; p_ch * sum_{q<L} c[j][q][t] <= P_j y_j, j in C; p_ch = eps/(eta*Delta) kW. (21): per grid group g and slot t, p_ch * sum_{j in C, gamma(j)=g} sum_q c <= P_grid[g][t].
- (22): for each j in S and slot tau: sum of x over swap arcs at j with l_a <= tau < u_a <= M_j y_j.
- Objective (26)-(32) exactly; C_setup is a constant when facilities are fixed (report it anyway). v_reb_eq may depend on q (store as per-service vector; default scalar).
- Optional (33): budget sum_j (Fhat_j y_j + bhat_j B_j + chat_j C_j) <= Budget; service share sum_i (1-u_i) >= zeta |I|; lexicographic service-first (min sum u_i, fix, min cost) as a switch.
- Model switches: `no_transfers` (h = z = 0), `colocated` (every facility gets both roles, S = C = N), `fixed_facilities` (y, B, C fixed from data), `budget`, `zeta`, `lexicographic`.

## Baseline policy (must run on the SAME Instance and arc library)
Nearest-feasible-rider dispatch (order FIFO by release), threshold swap rule, FCFS swap service with occupancy, ASAP charging (HIGH_FIRST), no transfers by default (optional reorder-point rule), departures/charging drawn from beginning stock, inventory stepped with (13). Report (not enforce) violations of (9), (17), (18). Full pseudo-code: `notes/workflow1_result.json` -> plan.baseline_policy_spec. Baseline schedule is also injected as a Gurobi MIP start to prove feasibility and warm start.

## Default discretisation for synthetic experiments
Delta = 5 min (1/12 h); H = 24 (2 h window) for the main runs, 36-48 for sensitivity; battery 600 Wh; L = 12, eps = 50 Wh (0.05 kWh); eta = 0.9 -> p_ch = 0.667 kW; hp = 1 slot, hd = 1 slot (config 3.0 / 1.5 min); promise b_i = r_i + 9 slots; prep a_i = r_i + ceil(U(10,25) min / Delta); q_res = 1; R_end_j = 1; rho = 0.5.
Route quantities from `GridNetwork.route`: T_r = length_m / speed_m_per_min (250 m/min), E_r = 12 Wh/km * km + 0.6 Wh/m * climb + 0.4 Wh * lights (config.py).
Costs in toy units: kappa = 1 /km, pi = 2 /kWh, P_i = 100, w_i = 12 /h, v_i = 24 /h, f_e = 5, v_reb = 0.2, F_j = 20, bB = 3, bC = 2 per horizon.
Reproducibility: Instance fully JSON-serialisable with seed; ILP and baseline consume byte-identical instances.

## Open questions for the supervisor (do not block; defaults above)
Response reference (u_a - r_i as written vs u_a - a_i); rho/R_end/q_res defaults; dummy terminal arc vs hard infeasibility; zero-dwell transshipment; service timetable generation; swap at q = L-1 allowed; facilities fixed vs free in the first experiments; recovery window after last promise; one vs several routes per OD pair; Delta/L/eps calibration against real chargers.

---

# Round 2 decisions (2026-10-12) — approved by the user after the first experiment round

The E2 mathematics is NOT changed by any item below: only data, parameters and the comparison (baseline) policy change.

## R2.1 Cost units: USD (sources in `notes/cost_calibration.md`, machine values in `notes/data/cost_calibration_usd.json`)
- Three named variants must be selectable by one switch (`cost_variant`):
  - `toy` — E2 p.14 units (kappa 1, pi 2, P 100, w 12, v 24, f 5, v_reb 0.2, F 20, bB 3, bC 2), kept for continuity with round 1.
  - `usd_A` — the calibration agent's base: kappa 0.50 $/km (wear + 25 % labour), w 40 $/h (rider pay 22 + customer 18), v 80, P 30, pi 0.32, f_e 20, v_reb 1.0, F 12.0 / F_hub 29.2, bB 0.332, bC 0.082 per 4 h window.
  - `usd_sunk` — DEFAULT. E2 p.9 states "initial delivery-bike batteries and operators are given fleet resources", so rider labour is sunk and must not be priced per order or per km: kappa 0.12 $/km (wear only), w 18 $/h (customer value of waiting only), v 36 $/h, P 30, all other coefficients as usd_A. Reason: with usd_A the unavoidable response cost of a typical order (prep ~27 min + handling 10 min + ride ~10 min at 40 $/h = ~$31) exceeds P = 30, so "drop every order" would be optimal — a degenerate objective, not a finding.
  - also expose `usd_B` (kappa 1.60 full labour per km, w 18) and the low/high envelopes as sensitivity variants.
- F, F_hub, bB, bC scale linearly with the window length (values above are per 4 h; 8 h -> x2). kappa, pi, w, v, P, f_e, v_reb do not scale.
- Budget coefficients (33): Fhat 50,000, bhat 450, chat 400 USD.

## R2.2 Instance family ("usd4h" main, "usd8h" sensitivity)
- Window 4 h (H = 48 at Delta = 5 min), dinner 17:00-21:00; 8 h (H = 96, 14:00-22:00) as sensitivity only if solvable (else rolling horizon, to be reported as a limitation).
- Every co-located site: B_j = 3 spares by default (sweep 2-3), C_j = 2, K_j = 8, M_j = 1, sigma_j = 1, P_j = 4 kW; grid group 8 kW (6 kW 18-20 h). Swap-only sites in separated layouts: B_j = 3, C_j = 0.
- Bikes start with q0 ~ U{ceil(0.3 L) .. floor(0.6 L)} (L = 12 -> 4..7 levels).
- Demand volume: orders per bike-hour is the scenario knob (base 1.5 orders per bike per hour -> 10 bikes x 4 h = 60 orders; the integrate step may reduce bikes/orders to keep single ILP solves under ~5 min at Threads 3 and must report the sizes used).
- Order attributes from Kaggle calibration (`notes/data/kaggle_calibration.json`): prep time ~ DiscreteUniform{20..35} min -> a_i = r_i + ceil(prep/Delta); promise b_i = a_i + ceil(25 min / Delta) (Kaggle delivery-time centre; weekday/weekend variants optional); cuisine shares = Kaggle order shares; restaurant popularity Zipf s = 1.0 within cuisine.
- Time-of-day profile (declared assumption, no paper supports a profile; see `notes/literature_demand_model.md`): lunch 11:30-14:00 = 28 % of daily orders, dinner 17:30-21:30 = 45 %, late 21:30-01:00 = 12 %, rest 15 %; weekend volume x1.15. Stored in one config block flagged `assumption`.
- Response time reference stays u_a - r_i as written in (31) (user decision).
- Energy rounding stays per-leg as written in (1)-(3) (user did not change it); end targets stay rho = 0.5, R_end = 1 (user did not change them); report the relaxed control as before.

## R2.3 Baseline (comparison policy) changes — user-approved
- `stock_aware_site = True` by default: a bike needing a swap goes to the nearest OPEN site with at least one full battery (station lists are public information); falls back to the nearest site if none has stock.
- New `charge_rule = 'DEMAND_AWARE'` (default): at each boundary a charge-capable site charges only as many batteries as needed to keep (full stock + batteries finishing within the lead time) >= forecast swaps in the next lead window + reserve, where forecast = swaps observed at that site in the last `lookback` slots scaled to the lead window (information available at t only), reserve = R_end_j; HIGH_FIRST ordering among the batteries that are charged; `ASAP`/`HIGH_FIRST` remains available as the round-1 rule. Parameters lead = 12 slots (one full charge from empty), lookback = 12 slots.
- Round-1 fixes stay on by default (just-in-time dispatch, dead-zone rule); the legacy flags remain for reproducibility.
- Everything else as in the round-1 baseline spec (nearest feasible rider FIFO, threshold q_thr = ceil(0.25 L), FCFS swap service with occupancy, no transfers by default / REORDER_POINT optional, (9)/(17)/(18) reported not enforced).

## R2.4 Real data (downloaded to `data/raw/`, manifest in `data/MANIFEST.md`)
- Restaurants: DOHMH deduplicated table (27,030 usable rows: bbox + cuisine + inspected). Map the 90 `cuisine_description` values to the 14 Kaggle classes + `other` (declared mapping table in code); sample cuisine by Kaggle order share, then a restaurant of that cuisine within radius R = 2.5 km of the customer (expand if < 3 candidates) with weight rank^-1.0 (rank assigned once per seed within cuisine).
- Zone weights: the literature formula (`notes/literature_demand_model.md`, "weight formula"): w_z = N_z x M_age x M_eth x M_sex x M_inc x M_kid x M_alone x M_stu, with the rate ratios 3.4/3.0/1.9/1.0 (age 18-29/30-44/45-59/60+), 1.17 NH Black, 1.26 Hispanic, 1.12 other, 0.91 female, 1.17 adequate income, 1.22 child 0-5, 1.29 child 6-17, 1.10 living alone, 1.12 student; M_FI (SNAP, 1.38) OFF by default. Needs ACS 5-year NTA tables (being acquired into `data/raw/acs/`; see MANIFEST section 5). FALLBACK if those tables are absent: GeoDa 2008-12 NTA counts (poptot, popover18, male16to19 + femal16_19 as the only age proxy, bachelor) with the formula reduced to N_z x (1 + 2.4 x youth16_19_share) and a loud warning in the instance meta; never use GeoDa medianinco/medianage/popdty (corrupt sums).
- Geometry: no real road network yet (NYC LION/CSCL not downloaded). A "semi-real" NYC instance = real restaurants, real zone weights and real candidate-site coordinates projected onto the synthetic GridNetwork: local equirectangular metres (1 deg lat = 111.0 km, 1 deg lon = 84.3 km at 40.7 N), rotated by -29 deg (Manhattan street-grid azimuth) and snapped to 150 m blocks inside a study box (default Midtown/Chelsea/Flatiron: lat 40.735-40.770, lon -74.005 to -73.965). Elevation and signals remain synthetic. State this clearly in every output.
- Crash grid and bike-counter profile: loaders only (risk layer and profile cross-check); not in the objective in this round.
- Point-in-polygon for NTA lookup: pure-python ray casting on `data/raw/nycnhood_acs.geojson` (no shapely).


---

# R2 implementation notes (integrate step, 2026-10-12)

Code state: `ebike_swap_sim/` full suite 118 tests green; `experiments/e1_toy.py` re-run: ILP 12.5 / 11.2 / 106 reproduced, baseline NONE 108 and REORDER_POINT 14.5 unchanged under the round-2 rules (R2.3) and identical for the `round1` / `legacy` variants (old-vs-new table in `outputs/e1/RESULTS.md`, section "Baseline rules: round 1 vs round 2"). E2 semantics (`ilp.py`, `arcs.py`, `evaluate.py`) untouched.

## Sizes chosen (R2.2 "report the sizes used"); probe `experiments/r2_size_probe.py`, Threads 3, TimeLimit 300 s, records in `outputs/r2_probe/`
- `usd4h` = **6 bikes / 36 orders / H 48 / L 12**, 3 co-located sites (B 3, C 2), `usd_sunk`. Probe (seeds 0, 1): default pruning 1.92 M / 1.86 M arcs (= binaries + 39), library 2.0-2.5 s, model 4.6-4.8 s, OPTIMAL (gap 0) in 95 s / 74 s, ILP 615.15 / 659.60 vs baseline 733.10 / 973.24 USD; reachable pruning 1.15 M / 1.11 M arcs, OPTIMAL in 87 s / 71 s with identical optima (lossless). MIP start accepted on both seeds (seed 1 needed the `baseline_round1` fallback schedule because the DEMAND_AWARE default violated (18)).
- `usd4h_large` = the R2.2 nominal 10 bikes / 60 orders (3.91 M arcs default, 2.66 M reachable); 8 bikes / 48 orders = 2.82 M / 1.80 M arcs. Their ILP runs were still executing when this note was written (the background probe appends to `outputs/r2_probe/usd4h.jsonl`); if 8 bikes reaches <= 1 % gap on both seeds, promote it to `usd4h` (one-line change in `experiments/common.py`).
- `usd8h` = 6 bikes, H 96, 72 orders, registered with `rolling_horizon_only: True` (`meta['rolling_horizon_only']`); the single-ILP probe (`--family usd8h --bikes 6`) has NOT been run yet, so it is a limitation until verified.
- `nyc4h` (R2.4 semi-real) = 6 bikes / 36 orders / H 48 with `PRUNING_NYC` (moves only into facility / depot nodes + reachable pruning): 0.75 M arcs (8 bikes 1.55 M, 10 bikes 2.64 M) against 36 M under the plan pruning; ILP solve not yet probed.
- Threads: `experiments/common.THREADS = 3` (round-1 outputs were produced with 4 and are not re-run).

## Deviations / cross-module resolutions
- R2.3 spec gap: `forecast_swaps_j` is identically 0 at charge-only hubs (j in C \ S), so the literal DEMAND_AWARE rule never recharges batteries shipped to a hub in separated layouts (toy REORDER_POINT would give 14.4 with (18) violated). `baseline.py` therefore applies `hub_charge_rule='HIGH_FIRST'` at hubs by default (the literal reading is selectable). Adopted.
- The DEMAND_AWARE reserve covers (17) only, as R2.3 states; the default baseline may report (18) and is then rejected as a MIP start. `experiments.common.feasible_mip_start` injects the first clean schedule among `baseline_round1`, `baseline_reserve` and records `mip_start_variant`; baseline columns still describe the policy under test.
- `experiments/common.BASELINE_VARIANTS`: `baseline` = round-2 rules, `baseline_round1` / `baseline_legacy` = `baseline.BASELINE_VARIANTS['round1'/'legacy']`; `baseline_informed` is now redundant with the default. Stored round-1 outputs (`outputs/e2_coord*`, `e3`, `e4_sizing`) correspond to today's `baseline_round1` / `baseline_legacy` names.
- `data_nyc.make_nyc_instance` now defaults to `acs_weights.ACSZoneWeights` (NTA-2020 codes, `zone_weights_source='acs_2020_24_literature'`, `zw.meta()` merged into `meta`) with the GeoDa fallback when the ACS files are absent; `data_nyc.cost_variant_params` delegates to `costs.load_cost_calibration` (ValueError kept). `ebike_swap_sim.__init__` exposes `costs`, `data_nyc`, `acs_weights` lazily. `e3_transfers_separation.py --family` excludes the round-2 families.
- Not done in this step: the cost-variant drop-share run of R2.1 (`experiments/r2_cost_variants.py --family usd4h --seed 0 --variants usd_sunk usd_A toy`, writes `outputs/r2_costs/`) and the usd8h / nyc4h solve probes; `data/MANIFEST.md` section 5 wording on the children share (acs_weights uses FamChU18E/HH1E split by OChU6E:OCh6t17E) and `notes/data/cost_calibration_usd.json` F 12.03 / F_hub 29.19 vs the 12.0 / 29.2 quoted in R2.1 (rounding) were left as is.


---

# Round 3 decisions (2026-10-12) — user decisions after the round-2 review

The E2 mathematics is unchanged. Only the service-level variant, the solver protocol and the coverage change.

## R3.1 Service level: hard service-share constraint (33), lexicographic variant dropped
- The lexicographic (service-first) rows of round 2 are NOT continued. The service level is imposed with (33) `sum_i (1 - u_i) >= zeta |I|`, `zeta = 0.90` as the MAIN setting (`ilp_zeta90`) and `zeta = 0.85` as sensitivity (`ilp_zeta85`); the user rejected 0.95 as too strict. `zeta` is passed to `ilp.build_model(zeta=...)` (`experiments.common.run_zeta_case`).
- If a zeta instance is INFEASIBLE (structurally unservable orders, or more orders than the fleet can serve), the row records status INFEASIBLE AND the maximum feasible served share from one `min sum_i u_i` solve (`experiments.common.max_service_share`: the lexicographic stage 1 alone; incumbent share, Gurobi bound share, certified flag).
- If the certified written-model optimum already serves >= zeta |I| orders, the zeta cell is recorded without a solve (`solve_mode = implied_by_written`: adding a satisfied constraint cannot change the optimum); `--no-imply` forces the solve.

## R3.2 End-of-horizon targets unchanged
- rho = 0.5 / R_end_j = 1 stay as written (`ilp`); the relaxed control (rho 0, R_end 0, `ilp_relaxed`) is kept.

## R3.3 Coverage and solver protocol (experiments/e2u_round3.py, e3u_round3.py, e4u_round3.py, e8_round3.py)
- Every ILP cell that round 2 skipped (wall budget) is solved; round-2 rows are reused only when solved to OPTIMAL or within 1 % MIP gap (`common.reusable_ilp_row`); the 4 E3u separated / written / transfers-free cells that stopped at 300 s with 2 % gap are re-solved with 600 s (that cell type gets 600 s on every seed).
- Seeds: E2u 0-9, E3u 0-4, E4u 0-5 (default size, B sweep, free-size run; P sweep and off-line B x C cells filled on seeds 0-2 / 0), E8 0-9.
- Gurobi: OutputFlag 0, Threads 3, TimeLimit 300 s (600 s as above), `Seed = 0` (`common.ILP_PARAMS_R3`); each script has a wall budget (E2u 5 h, E3u 4 h, E4u 4 h, E8 2 h) and records what it could not start as `SKIPPED_BUDGET`; records are appended to `outputs/<exp>_round3/records.jsonl` and `results.csv` is refreshed after every run; `--dry-run` / `--smoke` / `--analyse` modes, covered by `tests/test_round3.py`.
- Baseline rows are recomputed in round 3 where cheap (E3u, E4u: milliseconds, same code path as round 2, totals asserted against the stored written rows); E2u / E8 reuse the stored policy rows.


---

# E9 relaunch decisions (2026-10-14) — after the first bi-level launch produced degenerate results

The E2 mathematics is unchanged. Only the siting family, the search heuristic's rules and the
reposition-target convention of the lower-level libraries change. First-attempt outputs are kept in
`outputs/e9_bilevel/_first_attempt/` (its `README.md` lists the four failures with evidence).

## E9R.1 Root causes found in the first attempt (code references are to the pre-fix files)
- `roles/` S_SC and S_C_SC "no feasible layout": the 4500 s wall budget was exhausted after the SC_only search
  (wall_min 103.9 at its chosen rows); every later lower-level price returned `SKIPPED_BUDGET`
  (`bilevel.py` `evaluate_scenario` 517-523, not cached, no record), `evaluate` set `V = None` (605-607),
  `value()` mapped `None` to `+inf` (638-641), the greedy's `price` (922-923) therefore saw every move as
  infeasible, stopped (956-958) and reported "no feasible layout" (973-975). Same mechanism in
  `access/no_access` step 2 and in the SC_only second step.
- `access/` D8 and D12 "no feasible layout": `ok()` (919-920) required `layout_covers` on every intermediate
  layout, including the singletons of the first step; no single candidate covers all 12 zones (MN0202/MN0203 need
  L08, MN0601 needs L10), so `adds` was empty at the first step (942-945) and the search never started.
- `access/no_access` and `sweep/` chose L03:S:B1:C0 (served share 0.069): the baseline screen (`_screen`
  888-892, called at 946 with `k_screen 5`) ranks ALL moves of the step together; the baseline policy values
  one-spare swap-only sites at 1462-1480 and co-located sites at 1631+ (it serves orders at a loss where the
  ILP drops them), so only S:B1:C0 singletons were priced and the best of them (ILP 1398) started the search;
  at the first step the gain was `-V` (951, `v_lam = inf`), so the ratio was not the culprit, the screen was;
  no served-share guard existed.
- Lower-level solves of 2.2-2.4 M arcs (8 bikes, reposition targets = all 12 candidates + depots) hit 300 s.

## E9R.2 Family `nyc4h_stress2` (default of `experiments/e9_bilevel_siting.py`; `nyc4h_stress` selectable)
- 6 bikes / 36 orders / H 48, `q0 ~ U{3..6}` of 12, one spare / one charger / `Cbar 4` per default site, flat
  4 kW grid group, `P_j = 2.8 kW` per site (so a hub can run its 4 chargers, `4 x 0.667 kW`; with 1.4 kW the
  `C = 4` option would be dominated; the 4 kW group still caps the network at 6 simultaneous charges).
- Size menu (`sites_nyc.SIZE_MENUS['nyc4h_stress2']`): `S: B in {1, 2, 3}`, `SC: B in {1, 2, 3} x C in {1, 2}`,
  hubs `C in {2, 4}`. Budget unit unchanged (52,150 USD = Fhat + 3 bhat + 2 chat).
- Rule "swap-only sites only next to a charge-capable object": an S object holds at most 3 full batteries and
  cannot recharge; without a C / SC object nothing is ever resupplied, so an S-only layout is a dead stock, not a
  design. Implemented as `sites_nyc.layout_admissible(s_needs_charge=True)` in the greedy, the enumeration and
  as the rows `y_(l,S) <= sum_l' (y_(l',C) + y_(l',SC))` of the integrated model; `--allow-s-only` lifts it.
- Sanity check (seeds 0-2, baseline policy): a single L03:SC:B3:C2 serves 0.86 / 0.75 / 0.86 of the orders
  (>= 0.70 required), L03:SC:B2:C1 0.69 / 0.67 / 0.75; lower-level ILP of L03:SC:B3:C2 on seeds 0, 1: OPTIMAL
  in 37 s / 17 s, served 0.85, V 664.3 (`tests/test_bilevel.py::test_stress2_family_is_stressed_but_sane`).

## E9R.3 Greedy + local search (algorithm C) rules
- Start = the best singleton by lower-level V (never by gain per dollar, never decided by the baseline screen):
  the baseline screen keeps the `k_screen` best singletons PER ROLE, all of them are priced by the ILP, the
  cheapest usable one starts; if none is usable, every remaining admissible singleton is priced (exhaustive
  singletons). "no feasible layout" is reported only when no singleton is feasible with enough service, with
  the status counts of everything priced (`reasons`).
- A move is usable only when its lower level is feasible on every scenario AND its expected served share is at
  least `--min-served` (0.5); feasible moves below that are recorded `LOW_SERVICE` and discarded. The gain per
  investment dollar ranks only the additions after the start.
- `SKIPPED_BUDGET` (wall budget) stops the search and is reported as status `wall budget exhausted` with
  `search_complete = False`; it is never treated as infeasibility. Exceptions inside a lower-level evaluation
  become `ERROR` rows with the message (recorded in `records.jsonl`, not cached) and count as non-usable moves.
- Access row [U4]: `--access-mode repair` (default) never restricts the search; after the local search of a
  budget level the greedy adds / flips swap-capable items that cover the most still-coverable uncovered zones
  (usable moves only, within the budget) and repeats the local search without losing coverage; the zones still
  uncovered are REPORTED (`uncovered_zones`), not enforced. `report` only reports; `enforce` is the first-attempt
  behaviour (kept for reference). The integrated model keeps [U4] as hard rows (the exact benchmark of the
  requirement where it is affordable).

## E9R.4 Reposition targets (lower-level libraries)
- `sites_nyc.siting_pruning(inst, targets=...)`: `all_candidates` (moves into every candidate node + depots; one
  template per scenario, every layout a sub-library) or `open_sites` (open facility nodes + depots, the E8
  `targets = 'facilities'` convention). `LowerLevelEvaluator(reposition=...)` records the mode in the cache key.
- `--validate` (E9.1) keeps `all_candidates`: the integrated model (A) and the exhaustive enumeration (B) share the
  same per-layout libraries (sub-libraries of the all-candidates template), so their optimal values are
  comparable exactly. The search sub-commands (`--sweep --roles --deck --cross --access`) use `open_sites`
  (0.5-0.7 M arcs at 6 bikes, built in ~1 s per layout instead of 11 s subset extractions from a 3.2 M template);
  an `open_sites` value is an upper bound on the `all_candidates` value of the same layout (fewer move arcs), and
  both remain upper bounds on the written optimum (E8 convention). The superset bound and the integrated model
  always use the all-candidates template; integrated schedules are certified on the template sub-library.
- Cache version bumped to `e9-2` (first-attempt cache moved to `_first_attempt/cache/`).


---

# R5 implementation notes (integrate step, 2026-10-17) — reading list to model, round 5

Plan: `notes/reading_to_model.md` (A1-A7 adopt, M1-M10 modify, O1 optimise), built from the five papers in
`reading/`. **No E2 equation changed** (`notes/extracted/E2.txt` (1)-(33)): every item is a parameter, data, policy,
wrapper or solver option. Code state: `ebike_swap_sim/` full suite **307 tests green** (158 before the round);
toy invariants ILP 12.5 / rho = 0 11.2 / `no_transfers` 106 hold with the per-bike model (557 variables) and with the
aggregated flow (172 variables); every round-1..4 family regenerates byte-identically (`tests/test_r5_instances.py`
asserts the md5s of 21 family / seed pairs; the R2.3 baseline variants reproduce their schedules and costs bit for bit).

## What was implemented, per item
- **A1 energy calibration** (`config.ENERGY_CALIBRATIONS['ebaas']`, `config.energy_calibration`): 25 Wh/km (eBaaS
  40 km/kWh), 0 Wh per signal, 0.6 Wh per metre of climb, eps 25 Wh, L 24 (0.6 kWh pack), `energy_rounding = concat`,
  q_res 50 Wh = 2 levels, sigma 1 slot (swap < 10 s). Opt-in (`make_synthetic_instance(energy_calibration=...)`),
  recorded in `meta['energy_calibration']`; old families are not routed through it.
- **A2** narrative only (paper text; nothing in code).
- **A3 metric pack** (`evaluate.metric_pack`, `metrics(...)['r5']`, `common.flatten_r5` -> `baseline_r5_*` /
  `ilp_r5_*` columns of `run_pair`): SBUR, BSR (and BSR without blocked waits), batteries saved (exact certificate
  for (13)-(16)), rider station time and detour, outage / stranding / energy-refused orders, empty km, peak kW and kWh
  by price period.
- **A4 siting baselines and levers** (`bilevel.rule_layout` / `rule_baselines` CSCD / CSTC / CSAV,
  `capacity_matched_layout`, `present_day_sites`, `lever_table`; `e9_bilevel_siting.py --baselines / --levers`).
- **A5 value of the network** (`generator.home_charging_counterfactual`, `make_synthetic_instance(home_charging=...)`):
  one swap-only `HOMEn` per depot, sigma = ceil((L - ceil(0.25 L)) eps / eta / 0.24 kW / Delta) = 25 slots, (18) slack.
- **A6 fleet x spare x pack** (`costs.allocate_per_window`, `allocated_bike_cost` (bike 1,600 USD over 3 y + rider
  22.13 USD/h, assumptions), `pack_cost_scaling`; `generator.fleet_spare_pack_grid` (48 cells),
  `make_fleet_sweep_instance`).
- **A7 RL comparator** (`rl_env.StationEnv`, `experiments/a7_rl.py`): PPO-clip on the station layer (charging +
  loads), rider layer = R2.3 baseline (or `r5`); reward = minus the (26) increment of the partial schedule plus the
  M1 adjustment at H (same reference price as `evaluate.end_reference_price`, unified in this step).
- **M1 boundary conditions by parameters** (`common.end_target_copy`, `boundary_grid` (rho in {0, 0.25, 0.5, 1} x
  R_end_j in {0, 1} + periodic rho = 1, R_end_j = B_j), R_end_j = 0 at swap-only sites; `relax_end_targets` = the
  `rho0_R0` cell, identical results to before) and the end-state adjustment (`evaluate.end_state_adjustment`;
  `cost(...)['C_end_adjust', 'total_end_adjusted']`; `total` = (26) unchanged).
- **M2 range-aware + reservation swap rule**, **M3 cost-aware zero-sum transfer rule**, **M4 logit station choice /
  selfish equilibrium / compliance** (`baseline.py`: `swap_rule='RANGE'`, `reservation`, `transfer_rule='COST_AWARE'`,
  `site_choice='LOGIT'`, `run_selfish_equilibrium`, `simulate_compliance`; variants `r5_range`, `r5_transfer`,
  `r5_selfish`, `r5`; registered in `common.BASELINE_VARIANTS` as `baseline_r5*`). Defaults reproduce round 2 bit for
  bit; every rule is non-anticipative (tested). Follower E of E9 = `bilevel.POLICIES` `'selfish'`.
- **M5 stressed family** (`generator.R5_TIME_PROFILE`: operating day 08-22 h, peaks 10-13 h and 17-18 h, peak / off-peak
  ratio 2 = assumption; `R5_FAMILIES` `r5_stress4h`, `r5_stress8h`; `costs.load_tariff('tou')`: pi 0.132, pi_peak
  0.442 $/kWh in 08-22 h).
- **M6 Manhattan-wide siting** (`data_nyc.MANHATTAN_S110`, `MANHATTAN_ENTRY_POINTS`; `sites_nyc.R5_MANHATTAN_FAMILY`
  `r5_manhattan`, 2 km lattice candidates (15), riders entering at 6 bridge / tunnel points, access radius from the
  eBaaS 2 km coverage = 14 blocks; `e9_bilevel_siting.py --manhattan`).
- **M7 rolling horizon** (`rolling.rolling_horizon`, `BootstrapForecast`, `forecast_facility_plan`,
  `offline_vs_online`; `experiments/rolling_horizon.py` = E7). Windows solve the unchanged E2 ILP; the carried state
  enters as RHS / bounds; the stitched day is priced and checked by `evaluate`.
- **M8 cyclic tours** (`services_spec={'mode': 'cyclic', ...}`), **M9 lock-out** (`generator.add_battery_lockout`),
  **M10 levers** (`swap_position_variants`, `site_power_cap_sweep` + `costs.demand_charge_proxy`,
  `charger_speed_variants`).
- **O1 aggregated integer flow** (`aggregate.py`, `ilp.build_model(aggregate=True)`, `ilp.build_submodel`, used by
  `bilevel.integrated_stochastic_ilp` and `LowerLevelEvaluator(aggregate=...)`): identical optima on the toy and on
  three saved E2u instances (615.1464 / 659.6011 / 638.9789), identical LP bound, 6.45x fewer x variables, 7-11x
  faster. The 30 E2u and 40 E8 optima were not all re-validated.

## Cross-module fixes made in this step
- M9 lock-out end to end: `ilp.build_model` now fixes `options['forced_transfers']` itself (`h_e >= 1`, `z_eq >= 1` for
  a given level; variable bounds of (10), `switches['forced_transfers']`; skipped and counted under `no_transfers`);
  the baseline executes the forced services (`_step8_forced`, `flags['forced_transfers']`: lowest-level battery
  first, or the given level) and its REORDER_POINT / COST_AWARE / PLAN rules never touch them; `rl_env` runs them as
  data too; `evaluate.metrics(...)['lockout']` reports stock and recovery without the dummy sink ((18) as written
  counts it). `generator.apply_forced_transfers` stays as an idempotent helper.
- `rl_env._StationRun.station_external`: full batteries are drawn through `_avail_full`, so batteries reserved by
  bikes (M2) never leave on an agent's load; forced transfers are skipped as agent decisions.
- `ilp.extract_schedule` (aggregated branch): the path decomposition now rounds flows within Gurobi's `IntFeasTol`
  (1.01 x 1e-5); before, a flow of 1.999998 on `r5_stress8h` (6 bikes) raised `AggregationError`.
- `rl_env.end_state_adjustment` uses `evaluate.end_reference_price` (mean pi over C x T) instead of the price at
  `H - 1`; identical for flat and in-peak tariffs, one M1 convention for A7 and the E2 tables.
- `experiments/rolling_horizon.py` and `rolling.offline_vs_online`: with `--aggregate` / `aggregate=True` the offline
  reference is now solved with the aggregated flow as well (recorded as `offline_aggregate` / `aggregate`); before, the
  per-bike offline solve of `r5_stress8h` stopped at 2942.10 USD (TIME_LIMIT) and made the value of information
  negative (-882 USD).
- `ebike_swap_sim.__init__`: `aggregate`, `rolling`, `rl_env` are lazy attributes.
- `experiments/common.py`: R5 sizes registered (`builder: 'r5'` -> `generator.make_r5_instance`), `R5_PRUNING`
  (reachable pruning for round-5 synthetic instances only), `baseline_r5*` variants; `R2_FAMILIES` includes the R5
  names (so `e3_transfers_separation.py --family` keeps excluding them).

## Sizes chosen (probe: seed 0, Threads 3, TimeLimit 300 s, Seed 0, reachable pruning, MIP start = first clean baseline schedule)
Battery-binding test: LP-relaxation shadow price of the fixed spare / charger counts (`-RC(B_j) + bB_j`, `-RC(C_j) +
bC_j`, USD per window and site), ILP stock-out slots, baseline served share, and the ILP with one extra spare per site
(B 3).

| cell | arcs (per bike) | aggregated ILP (O1) | per-bike ILP | LP spare / charger value | B 3 vs B 2 (ILP) | baseline r2 |
|---|---|---|---|---|---|---|
| r5_stress4h 6 bikes / 48 orders | 3.14 M | OPTIMAL 750.21 in 75 s (512 k vars, 231 k bin, build 4.3 s) | TIME_LIMIT 1133.73, gap 33.8 % (3.15 M vars) | 0.27-0.28 / 0.00 | 750.92 OPTIMAL (+0.71 incl. +1.00 setup: 0.28 operating saving) | 1134.20, served 0.896, 54 stock-out slots |
| r5_stress4h 8 bikes / 64 orders | 4.83 M | TIME_LIMIT 1007.38, gap 1.39 % (583 k vars) | TIME_LIMIT 1958.92 (drop-all incumbent), gap 108 % | 7.6-8.5 / 7.2-11.1 | 1017.56, gap 2.7 % (inconclusive at 300 s) | 1813.36, served 0.688, 87 |
| r5_stress4h 10 bikes / 80 orders | 6.93 M | TIME_LIMIT 1256.66, gap 3.45 % (672 k vars) | TIME_LIMIT 2440.11 (drop-all), gap 108 % (7.0 GB) | 35.6-37.2 / 33.5-38.4 | 1204.08, gap 1.3 % (-52.6 USD) | 2215.06, served 0.675, 92 |
| r5_stress8h 8 bikes / 128 orders | 11.25 M | TIME_LIMIT 3891.83 (incumbent serves 1.6 %), gap 48.5 % (1.36 M vars) | not attempted | 28.7-29.9 / 78.4-85.1 | - | 5132.25, served 0.641, 232 |
| r5_stress8h 6 bikes / 96 orders | 6.98 M | TIME_LIMIT 1526.57, gap 1.86 %, served 0.917 (1.13 M vars, 504 k bin) | not attempted | 0.29-0.34 / 0.00 | - | 2470.03, served 0.823, 193 |
| r5_stress8h 10 bikes / 160 orders | 16.72 M | no incumbent after 300 s (1.61 M vars; LP 2561.74 in 49 s) | not attempted | 61.8-62.8 / 174.7-183.7 | - | 6201.58, served 0.538, 229 |

- **`r5_stress4h` (6 bikes / 48 orders / H 48 / L 24) is the round-5 single-ILP family**: solved to optimality with the
  aggregated flow in about 60-75 s; the battery side binds (positive LP shadow price of a spare 0.27-0.28 USD per site,
  55 stock-out slot-sites in the optimum, baseline served share 0.896 < 0.95, one more spare per site saves the
  baseline 77 USD), but only weakly for the coordinator. Use `R5_ILP_KWARGS = {'aggregate': True}`; the per-bike model is
  not usable at this size (gap 33.8 % after 300 s).
- **`r5_stress4h_k8` (8 bikes / 64 orders) is the battery-binding headline** for A6, M9, M10 and A5: LP shadow prices of
  7.6-8.5 USD per spare and 7.2-11.1 USD per charger per site, baseline served 0.688 against ILP 0.953; the ILP needs
  TimeLimit 600 s and its gap must be reported (1.39 % at 300 s). No clean MIP start exists at 8 and 10 bikes (every
  fallback baseline violates (17)/(18)); run these cells on the M1 relaxed control (`relax_end_targets`) as the
  headline and the written targets as the price of recovery.
- `r5_stress4h_k10` (10 bikes / 80 orders): A6 fleet cell only (gap 3.45 % at 300 s; strongly battery-bound: LP
  35.6-37.2 USD per spare, +1 spare per site lowers the incumbent by 52.6 USD).
- **`r5_stress8h` (6 bikes / 96 orders / H 96) stays flagged rolling-horizon only** (M7 is its operating mode), but
  the single aggregated ILP at 6 bikes is usable as the offline reference of E7: 1526.57 USD, gap 1.86 % after 300 s
  (use 600 s and report the gap). At 8 bikes the aggregated ILP keeps a 48.5 % gap (its incumbent drops 98 % of the
  orders) and at 10 bikes it finds no incumbent, so larger 8 h fleets are rolling only. The first 6-bike attempt crashed
  in the path decomposition (fractional flow 1.999998, fixed below). Rolling horizon (W 24, k 6, lambda 10 min,
  aggregated windows) on seed 0: 2060.01 / 2139.22 USD in two runs (120-121 s, 16 windows, 72-73 s of window solves;
  the runs differ because some window solves hit their 60 s limit under machine load) against the baseline 2470.03 and
  the aggregated offline reference 1526.57 (gap 1.86 %): value of information 613 USD (40 %), share of the coordination
  gap surviving online 0.35 (one seed).
- **`r5_manhattan` (E9, M6) at 8 bikes / 40 orders / H 48 / L 24**, seed 0, open-sites libraries, aggregated ILP:
  `M08:SC:B3:C2` 1.43 M arcs, OPTIMAL 782.03 in 32 s, served 0.700 (baseline 1344.74, served 0.475);
  `M04/M08/M10:SC:B2:C1` 2.10 M arcs, TIME_LIMIT 677.30, gap 1.59 %, served 0.925 (baseline 1118.47, served 0.775).
  Layouts differ by about 100 USD per window, so siting matters here (unlike `nyc4h_stress2`). Base instance build
  21 s per seed.
- Rolling horizon on `usd4h` seed 0 (W 24, k 6, aggregated windows, 8 windows): offline 615.18 OPTIMAL in 115 s;
  lambda 0 / 10 / 20 min: 801.70 / 715.04 / 751.04 USD in 17.2 / 22.4 / 24.5 s (window solves 9.2 / 11.1 / 13.4 s);
  baseline 733.10. Value of information is not monotone in the lookahead on one seed (myopic windows); E7 needs seeds
  0-4.
- RL (A7) on `nyc4h_stress2`: 4,096 PPO steps in 8.3 s of training (about 490 steps/s, 16 s with set-up), so the
  planned 200 k steps take about 7 min plus the evaluation; the 4 k-step policy is worse than the baseline (1219 vs
  1143 USD on seeds 0-1) as expected for a smoke run; replay parity with the baseline holds exactly.

## Deviations and open points
- The plan's M2 target (outage rate about 50 % below the q_thr rule) is not demonstrated; smoke runs are mixed.
- O1 validation covers the toy and three E2u optima, not all 30 E2u / 40 E8 optima.
- The full A7 training (200 k steps, 10 seeds with the ILP) and the E7 seeds 0-4 were not run in this step.
- `r5_stress8h` per-bike ILP and the 10-bike 8 h cell were not solved to a useful gap; they are not needed because the
  family is rolling-horizon only.
- In a lock-out instance (18) as written counts locked batteries; report it with rho = 0 or use
  `metrics(...)['lockout']['end_share_excl_sink']`.

# R6 implementation notes (2026-10-18) — order prices recalibrated as data

Source: `notes/penalty_calibration.md` sections 1, 6, 7. New base pricing P_i = 60 USD, w = 18 USD/h from r_i
(unchanged), v = 15 USD/h from b_i; every other coefficient as `usd_sunk` with the eBaaS energy calibration. No E2
equation changes; (31) keeps its form.

- `costs.py`: variant `usd_r6` (= `usd_sunk` with P 60, v 15; also in `data_nyc.COST_VARIANTS`); `R6_PRICING`,
  `LEGACY_PRICING`; `reprice_orders(inst, P, w, v)` returns a copy with every order repriced, `meta['costs']` and every
  `demand_spec` dict in meta updated, `meta['cost_variant']` relabelled (`usd_r6` / `usd_sunk` when exact, else
  `<variant>@P.._w.._v..`; the generated one kept in `cost_variant_generated`) and `meta['pricing']` = {P, w, v, source,
  label, changed, previous, library_rebuild_required}. Generating usd4h with `cost_variant='usd_r6'` gives the same
  instance content as repricing the `usd_sunk` one (tested).
- theta (31) is stored on the arcs at build time: `check_lib_prices(inst, lib)` compares up to 3 delivery arcs per
  order with `Instance.theta` and raises `PricingMismatchError`; `ilp.build_model` calls it (O(|I|)), and `ilp.solve`
  still asserts objective == `evaluate.cost`. A change of P alone keeps a library valid.
- Consumers checked: `evaluate.cost` reads o.P / o.w / o.v at evaluation time (response and lateness from the orders,
  not from the arcs); the ILP reads o.P for u_i and arc theta for deliveries (hence the check); rule policies use the
  prices only in the M3 stock-out value (mean P_i, read from the instance); logit (M4), dispatch and charging rules do
  not use prices; `rolling._shift_order` derives P' = P - w Delta (t0 - r)^+ from the (repriced) day orders and every
  window library is built from the window instance; `rl_env` rewards are `evaluate.cost` increments (instance prices);
  the M1 end-state adjustment and the A3 metric pack do not depend on order prices; `bilevel.LowerLevelEvaluator`
  cache and bound keys now include `costs.pricing_cache_component` (the order-price MD5 for repriced scenarios, `None`
  for instances priced as generated, so earlier keys are unchanged).
- Experiments: `experiments/r6_penalty.py` (stages headline, psweep, vsweep, network, rolling, levers, fleet, rl;
  round-5 builders and protocol, repriced after generation, libraries built on the repriced copy and price-checked);
  lanes `outputs/r6_lanes/lane_1..4.sh` + `launch.json`. Tests: `tests/test_r6_pricing.py`, `tests/test_r6_penalty.py`.
- Not run on purpose: the grace variant of penalty_calibration.md section 7 item 3 (v 17 USD/h from b_i + 10 min). It
  needs a pricing-only grace parameter in (31); R6 keeps (31) in its form, so vsweep covers v in {8, 15, 25, 36} at
  P 60 plus the (P 30, v 36) bridge only (also stated in the vsweep RESULTS.md).
- Review fixes (2026-10-18): (i) resume — an ILP row that is not OPTIMAL and whose time limit the wall budget cut below
  the requested one (`budget_shortened`, or `time_limit_s < time_limit_requested_s`) is not done: grid stages re-solve
  it and never copy it from headline, network re-plans it (with the implied home written row), rl re-solves it (X7
  `_ilp_done` wrapped); (ii) a grid stage whose budget is gone emits SKIPPED_BUDGET ILP rows for the remaining cells
  without building them, and `summary_key.csv` / RESULTS use only seeds with a relaxed ILP row (`n_seeds`, plus
  `n_seeds_with_rules`); (iii) network and rl rows carry the lateness columns (`n_late_over_60min`, ...) and P / w / v
  (`lateness.csv` per stage); (iv) levers / fleet take every `best_rule_*` metric from the end-adjusted argmin rule
  (`best_rule_end_adjusted_rule`), not X5's raw-total argmin row; (v) `paired_vs_ref.csv` leaves out, for the
  ILP-dependent metrics, a seed whose two relaxed solves are not comparable (one not OPTIMAL and different MIP-start
  families: the reused headline reference starts from the written ILP optimum) and counts them (`n_excluded_start`);
  (vi) the rl relaxed-ILP limit is 300 s (round 5: 120 s; the full-size r5_stress4h relaxed ILP takes about 100 s at
  P 60 / v 15), rl budget 270 min, expected 120 min.

## O2 conventions (certified siting bound, 2026-10-18)

Design: `notes/o2_siting_bound_design.md` (critique section C1-C16). No E2 equation changes; the LP relaxation of the
operations model is used for bounds only and every incumbent is priced by the unchanged operations ILP.

- Certificates use all-candidates pricing (`LowerLevelEvaluator(reposition='all_candidates')`); `open_sites` values are
  upper bounds only and never enter a lower bound.
- Bound LP per scenario = aggregated E2 sub-model on the all-candidates template (`ilp.build_submodel(...,
  keep_rows=True)`; `keep_rows` defaults to False, default path unchanged), free copies of (y, B, C) pinned by fixing
  rows, plus artificial source -> SINK columns (one per commodity and source state, bounds [0, supply]) and bounded
  slacks on (17)-(18), all at M_el = 1e4 USD per unit (complete recourse); target switch written <-> relaxed by
  coefficient changes. Elastic columns never enter the pricing ILP.
- LP optimality cuts are safe Lagrangian bounds: sign-projected row duals, exact reduced costs,
  `c0 = Pi h + sum_v min(rc_v l_v, rc_v u_v)`, `beta = -T^T Pi`; valid for every first-stage value whatever the solver
  accuracy (no ObjVal-based constants).
- Scenario lower bound of a priced layout = `row.bound - row.C_setup` (Gurobi ObjBound includes C_setup); value =
  `row.opex`. `ILPModel.solve` now records ObjBound also without an incumbent (statistics only). The evaluator takes
  `best_bd_stop` (Gurobi BestBdStop on the full objective; not part of the cache key; such rows are never reused as
  completed solves) and a per-call `time_limit` (escalation).
- Integer cuts: classic L-shaped and lifted (LP cut + Delta on the Hamming distance) per scenario; no-goods for
  INFEASIBLE_ILP, terminal cover cuts for INFEASIBLE_TERMINAL; a-priori cover rows from template reachability.
- Tolerance `max(0.25 % UB, 1 USD)`; nested budgets (a priced layout updates the UB of every budget it fits; LB_m is
  taken as the max over larger budgets); LP pruning compares with the largest UB among the budgets the layout fits (C5).
- Cut pool `cuts.jsonl` with a signature (scenarios, demand, order prices, spec, pruning, M_el); cuts are tagged by
  target and imported one way only, relaxed -> written.
- Greedy `screen` accepts a callable (`benders.LPScreen`); default `True` (baseline screen) unchanged.


---

# R6 decision: the paper's main specification uses the recalibrated prices (2026-10-18)

User decision (chat, 2026-10-18): the manuscript's main specification switches to the recalibrated order
prices P_i = 60 USD, w = 18 USD/h from release, v = 15 USD/h from the promise (cost variant `usd_r6`,
source `notes/penalty_calibration.md`); the former prices (P 30, v 36, `usd_sunk`) become a sensitivity
row (the old-price bridge of `outputs/r6_penalty/vsweep`). Consequences:
- every experiment that the paper reports must be re-run under `usd_r6` before the manuscript is updated:
  transfers (X2), stress K10 and stress8h, the end-target boundary grid and LP shadow prices, pack sizes,
  rolling lambda 0 / 20 and the forecast plan, the price of recovery outside usd4h x1, the Manhattan siting
  (O2 certification, running), the selfish follower, levers and compliance on the certified Manhattan layout,
  and the cells truncated by the laptop sleep of 2026-10-18 13:13-13:42 (psweep usd4h P 80 s0, stress4h P 40
  s9; vsweep v 36 s5, s6; fleet K 10 / B 1-2 s2; headline usd4h x1.5 s0, s5, s8 at 600 s; levers reference);
- the paper's tables and figures that depend on prices are rewritten from the R6 reports (list in
  `outputs/R6_DIGEST.md`, section "paper impact");
- `experiments/common.py` default cost variant stays `usd_sunk` for reproducibility of rounds 2-5; R6 scripts
  reprice explicitly with `costs.reprice_orders`.

# R6 fill-in script and the retry rule (2026-10-18)

`experiments/r6_fill.py` (imports `r6_penalty`; tests `tests/test_r6_fill.py`) closes the gaps that
`outputs/R6_DIGEST.md` sections 8-9 list at the recalibrated prices:
- `--retry-unsolved [--time-limit S]` on `headline`, `psweep`, `vsweep`, `fleet`, `levers`: every ILP row
  (last per key) that is not OPTIMAL, or that the laptop sleep truncated (`runtime_s > wall_s + 10`, or
  `wall_s` below the requested limit while TIME_LIMIT; X5 rows without `wall_s`: `runtime_s > limit + 10`),
  is re-solved (defaults 600 s; levers 1800 s) from the cheapest clean start among the saved incumbent and
  the rules; the new row is appended under the SAME key (last row wins in every `--analyse`) with
  `retry_of` (record index), `retry_of_status`, `retry_reason`, `retry_time_limit_s`; `retries.csv` per stage.
  `r6_penalty.GridRunner.prior_incumbent` offers the saved incumbent of a cell as a start candidate.
- new stages under `outputs/r6_fill/`: `transfers` (X2 design, usd4h seeds 0-4), `stress` (K10, stress8h,
  K6 written, boundary grid, LP shadow prices), `rolling_ext` (lambda 0 / 20, forecast plan), `pack`
  (rule-only pack cells joined to the fleet grid), `levers_ext` (eps 50, M 2, 1-spare lock-out, demand-charge
  proxy from the reference / P0 rows), `compliance` (M4 sweep, selfish equilibrium, r2 on the O2 best written
  m=2 layout and on the round-5 layout `M06:SC:B4:C2|M12:S:B3:C0`; private copy of the O2 cache), `rl_seeds`
  (PPO seeds 1 and 2, one X7 folder per seed, rows appended with `ppo_seed`).
- lanes `outputs/r6_fill_lanes/lane_1..4.sh` (caffeinate -i; compliance last in lane 3 after
  `--check-o2`; rl_seeds alone in lane 4); to be started after the O2 Manhattan run has finished.

Review fixes (2026-10-18, before the lanes start):
- `stress`: the boundary reference `rho0_R0` (= the relaxed K6 cell) is ONE case per seed 0-2 carrying both
  the LP and the 300 s ILP (`r5_x5_stress.Runner.note_case` dedups on (sub, cell, seed, target, key), so the
  earlier split -- an LP-only note first, the boundary ILP later -- left the ILP row out of `cases.jsonl` and
  the boundary price of recovery empty); `r6_penalty.StressRunner.note_case` is now phase-aware (a cell noted
  without an ILP is noted again when planned with one) and `wide_r6` prefers the note naming an ILP method.
- X5 retries (`fleet`, `levers`): `r6_penalty.StressRunner` saves every ILP incumbent under
  `<stage>/schedules/<key_md5>_<method>.json` and offers it as `prior_incumbent` when the key is solved again
  (the rows solved before this change have none: their first retry starts from the rules); every start
  candidate with transfers is also offered with them stripped (`no_transfer_variants`, label suffix
  `|no_transfers`), so the lock-out incumbent can seed the reference cell (`mip_start_variant` records it);
  a re-solve that ends NOT OPTIMAL with a worse total than the replaced row is appended marked `retry_worse`
  and ignored by `last_done_rows` / `wide_r6` / the retry selection (the earlier row stays, its incumbent is
  not overwritten); a plain TIME_LIMIT row (not sleep-truncated) is re-solved only at a limit above its own
  (`skipped_same_limit` in the dry run; four fleet rows at 600 s are skipped at the default 600 s).
- every R6 table that joins the headline / psweep relaxed-ILP rows (`r6_penalty --stage rolling --analyse`,
  `rolling_ext`, `stress`) must be re-run after a retry; the lanes' final analyse step now includes
  `r6_penalty.py --stage rolling --analyse` (network and rl do not join those rows).
- lane 3 waits for the O2 written m=2 result at most 12 h (144 polls); on a timeout compliance runs on the
  round-5 layout only (`--layout-key`), so the lane's analyse still runs; the O2 `records.jsonl` /
  `cache/index.jsonl` are read leniently (a half-written last line is skipped) while O2 keeps appending.

## O2 second pass (2026-10-19)

First pass (`outputs/r6_o2/manhattan/`, 9 h + 10 h walls) ended with `LB None` at every budget: the warm-started dual
simplex re-solves took 160-1,360 s per layout (cold barrier 16 s), the enumeration solved every layout's LP before
pruning, and no master solve ran before the wall. Diagnosis and the second-pass plan: `notes/o2_manhattan_first_pass.md`.
Conventions from here on:

- The first-pass folder is read-only. A later pass takes `--source-dir` (records, pool, cache copied once into
  `--out-dir`; cached rows' `schedule_path` rewritten to the copy) and writes only into `--out-dir`.
- Scenario LPs are solved cold with barrier + crossover on every point (`ScenarioLP(method='barrier')`, `LPWarmStart 0`;
  `--lp-method dual` keeps the old warm dual simplex with `LPWarmStart 2`, `concurrent` is Method 3). The cut is the safe
  Lagrangian cut of C1 whatever the method; `lp_layout` records carry `method`, `runtime_s`, `iterations`.
  Defaults `--lp-workers 3 --lp-threads 3 --master-threads 2`.
- Enumeration prunes with the cut envelope before any LP (`lp_pruned` with `by = envelope`), orders layouts
  location-major / envelope-ascending, prunes again before every pricing, and raises `LB` to the enumeration floor
  `min_l max(envelope, v_LP, lower)` over the complete layout list at any exit (wall included).
- Every target closes with a bound-only master solve per budget over the full pool (`final_bound`, 120 s limit);
  `LB = max(LB so far, master ObjBound, superset trivial bound, enumeration floor)`, nested over budgets; `budget_result`
  rows carry `LB_kind` and `LB_parts`; `LB` is never `None`.
- Resume: `--resume-open` ignores `target_done` rows unless every requested budget is certified AND the budget-free
  configuration hash `config_md5_core` (stored in `plan` / `target_done`) matches (else a `target_not_skipped` record
  and the target runs again), and restores `lp_memo` (from the pool's `lp` cuts with `meta.tag = layout`), `priced`
  (`price` records) and `lp_pruned` of the target; `--certify-budgets`, `--skip-enumeration`, `--enum-limit`.
- Enumeration escalates its own open pricing gaps (pass 3 of `certify_by_enumeration`: priced layouts with
  `max(envelope, v_LP, lower) < UB - tol`, lowest first, one scenario per `escalate()` call, until closed or the levels
  are used up); the budget closes as `gap` or `enumerated (open pricing gaps: n ...)`. The integer phase skips closed
  budgets, so this is the only place the step-1 command can escalate.
- `LB = inf` (master infeasible, no admissible layout within the budget) is reported as `LB None` with
  `close_reason = master infeasible (no admissible layout)` and is certified only when `UB` is `None` too; a finite
  `LB` above `UB` is clamped to `UB` in the row (`LB_raw`). Hour estimates for the second pass presuppose a machine
  that is not paging (check `sysctl vm.swapusage` before step 1).
- `--bound-from-cuts` reports LB / best priced UB / gap / bound kind / ranked proposals from a stored pool without any
  LP or ILP solve (`BOUND.md`, `bound_from_cuts.jsonl`); it reproduces the certifier's `LB` after a full run (toy test).
- First-pass certificate (from the pool): relaxed m = 1 LB 1037.83 vs UB 1052.995 (gap 1.44 %), m = 2-4 674.83 vs
  700.11 (3.61 %); written m = 1 1037.83 vs 1132.39 (8.35 %), m = 2 674.83 vs 706.26 (4.45 %), m = 3-4 674.83 vs
  703.61 (4.09 %). The m >= 2 bound is the trivial one (superset + cheapest two-site setup): the stored LP cuts bind only
  at layouts with the same open sites, so the second pass certifies m = 1 (pruned enumeration, about 1-3 h per target)
  and reports the Benders bound for m >= 2 without expecting a certificate.

Smoke fixes (2026-10-19, lanes still not started):
- `r6_penalty.StressRunner.emit` creates `sub_rows[sub]` on first use: `r5_x5_stress.Runner` keys that dict by its
  own SUBS (core / boundary / fleet / levers), so the r6_fill X5-style stages `stress`, `pack`, `levers_ext` raised
  KeyError on their first row (and again on the error row). r6_penalty's `levers` stage was unaffected by luck.
- `tests/test_r6_fill.py::test_retry_grid_smoke_appends_a_marked_row`: a retry run ends with `analyse_retry`, which
  writes `retries.csv` (as every stage's run writes its RESULTS); the test wrongly asserted the file absent; it now
  checks `retries_table` is pure and that the run and `--analyse` both write the file.
- `run_compliance` validates every layout key against the evaluator's candidates before writing a row (a foreign key,
  e.g. a Manhattan key under `--smoke` whose evaluator is the toy one with T1..T4, exits with a message instead of
  ERROR rows). Note `--smoke` never reads the O2 records: the default O2 read is covered by the non-smoke dry run.
- Verified: R6_FILL_SMOKE=1 tests/test_r6_fill.py 24 passed; full tests/ passed (6 memory-gated skips); a --smoke run of
  every stage and of the five retries (one faked sleep-truncated row each) wrote records with no error row and
  obj_eq_eval True on every ILP row; lanes regenerated unchanged (EST_MIN untouched).

Fleet retry "reused" on the server (2026-10-19, fixed before the lane is re-run):
- Symptom: `r6_fill.py --retry-unsolved --stage fleet` on the AWS instance selected the 16 ILP rows, then printed
  `"reused": true` for every case, finished in 6 s and wrote `retries.csv` with 0 rows; the levers retry on the laptop
  re-solved its rows with the same code.
- Cause: `RetryStressRunner.case_status` matched the forced rows `{(key_md5, method)}` only by `key_md5 ==` the
  content key recomputed from the rebuilt instance (`r5_x5_stress.content_key`: an md5 over every float of
  `Instance.to_dict()`). The fleet records were written on the laptop (arm64 macOS); rebuilt on the x86-64 Linux
  server the floats that pass through libm (`math.cos`/`sin` of the grid azimuth, `hypot` in the projection, numpy's
  vectorised transcendental kernels) are not guaranteed bit-identical, so no key matched, `_cur` stayed None, the
  override returned an empty todo and `X5.Runner.run_case` reported the case `reused` (6 s = 16 instance builds, no
  library). On the laptop every recomputed key equals the recorded one (checked for all 16 fleet and 6 levers cases),
  which is why the local levers retry worked. Neither `_is_done` nor `reusable_ilp_row` was involved: the forced todo
  already bypasses them. Side effect of the failed run: `X5.Runner.run_case` notes the case before it finds nothing
  to do, so the server's `fleet/cases.jsonl` gained 16 notes under the drifted keys with `ilp_method ILP_tl600`;
  `wide_r6` prefers a note naming an ILP method, so those notes would have hidden the 16 cells from the analysis.
- Fix (`experiments/r6_fill.py`): a forced row is matched by content key, else by `(cell, seed, target)`
  (`case_id_of`); on such a drift `instance_drift` compares `orders_md5`, `demand_md5`, `n_bikes`, `n_orders`, `H`, `L`
  of the rebuilt instance with the replaced row (hashes of ids / nodes / slots: machine-independent) -- equal: the
  retry row keeps the RECORDED `key_md5` (it must supersede the old row under `last_done_rows`) and carries
  `key_md5_rebuilt`; the saved incumbent is looked up under the recorded key; different: the case is reported
  `RETRY_SKIPPED` with the differing fields and nothing is emitted. `RetryStressRunner.note_case` is a no-op (a retry
  never adds a case note), a case that ends without its forced method is reported `RETRY_SKIPPED` instead of `reused`,
  and forced rows left un-solved are listed as a WARNING at the end. `prune_orphan_case_notes` moves notes whose key
  has no row while another note of the same cell has rows to `cases_orphans.jsonl` (the dry run reports them as
  `n_orphan_case_notes`; the run prunes them first). The `ilp_method` monkey-patch is the context manager
  `ilp_method_override`. The selection itself is unchanged: both reasons (`not_optimal`, `sleep_truncated`) are
  honoured, a TIME_LIMIT row within the 1 % reuse gap is still re-solved when selected, `retry_worse` protection and
  the levers behaviour are unchanged; the four plain 600 s TIME_LIMIT fleet rows (K8_B1 s1, K10_B2 s2, K8_B1 s2,
  K8_B2 s2) remain `skipped_same_limit` at the default 600 s and are included by `--time-limit 1800` (20 rows,
  about 9 h at Threads 3).
- Tests (`tests/test_r6_fill.py`): a TIME_LIMIT row at a 0.5 % gap is forced (and skipped only as a blind re-run at
  its own limit); a `RetryStressRunner.run_plan` on the smoke levers reference case with the solver stubbed
  (`common.run_ilp_case` returns the MIP start) and a recorded key that differs from the content key appends one
  retry row (recorded key, `key_md5_rebuilt`, `retry_of 0`, OPTIMAL, no `reused`), adds no case note, saves the
  incumbent under the recorded key, and skips a forced row whose `orders_md5` differs; `prune_orphan_case_notes`.
- Known limitation left as is: `content_key` / `arc_signature` are not portable across machines, so an X5-style
  stage resumed on another machine re-solves every case (keys differ) instead of resuming; the new r6_fill stages
  start on the server from empty records, so only the fleet / levers retries were affected.

## R7 siting scale-up (2026-10-20)

Implements `notes/siting_scaleup_design.md` section 4 as corrected by section 7 (the critic pass overrides the
earlier sections wherever they differ). No E2 equation (1)-(33) changes; the lower level is the unchanged
operations ILP priced through `bilevel.LowerLevelEvaluator`; the LP relaxation is used for bounds only. Defaults are
unchanged: with the new flags off the 15-candidate run is reproduced byte for byte (checked below). Code:
`ebike_swap_sim/{sites_nyc.py, bilevel.py, benders.py, arcs.py}`, `experiments/r7_siting.py`,
`experiments/r6_o2_siting.py` (thread cap only), `tests/test_r7_siting.py`, `outputs/r7_siting/figs/siting_map.py`,
`deploy/aws/sync_down.sh`. English only.

Instance (`sites_nyc.py`):
- Family `manhattan_dot` (`MANHATTAN_DOT_FAMILY`, parameters `R5_MANHATTAN_PARAMS`, same `SITING_POST` energy
  calibration and tariff, depots = the six entry points, access D = 14 blocks). `dot_candidates(path, region=
  'manhattan_s110', merge_m=80, cap=60)`: rows with numeric `lat`/`lon` inside the region band; the type is read from
  `site_type` (or `type`), unknown values become `other`; a rejecting `verdict` drops the row -- fixer pass: whole
  tokens only (`DOT_REJECT_VERDICTS` = drop / dropped / reject / rejected / exclude / excluded / nogo / out / outside /
  remove / removed as the FIRST word, or `no go` / `out of` as the first two words; `No objection`, `not sure`,
  `outstanding candidate` are kept), every verdict-dropped row and every kept verdict string is listed in the plan
  record (`dot_info.verdict_dropped`, `dot_info.verdicts_kept`) so the author sees them before stage setup; duplicate
  ids are suffixed `~2`, `~3`, ... and a DOT id spelled like a lattice id gets `~dot` (`dot_info.renamed_ids`), and the
  merge test keys the projected points by row object, never by id string (two rows with one id 3 km apart were
  merged before, as was a DOT row `M01` with lattice cell `M01`); snapping to the 150 m rotated grid with `snap_m`
  recorded; merge when raw points are closer than 80 m OR the
  snapped nodes coincide; survivor by `(type priority, restaurants at the node, input order)`, type priority
  `DOT_TYPE_PRIORITY` = pilot > installed > approved > revocable_consent > shortlist > application >
  citibike_charging > fdny_hub > depot > lot > other > lattice (the hub slots use their own order,
  `DOT_HUB_PRIORITY`, see "R7 decisions of 2026-10-21"); union with the 15 lattice candidates by the same rule
  (lattice below every DOT type; the survivor keeps `lattice_id` and `cls` in {dot, lattice, both}); ids `D01..` south
  -> north, west -> east by lattice cell then node (the order of the lattice ids, so a 15-point fixture gives the
  15 lattice nodes in order); cap at 60 by dropping `other` then `lot` rows with the fewest restaurants within 4
  blocks (`candidates_dropped.csv` lists every dropped / capped row with the reason). The file
  `data/raw/dot_candidate_sites.csv` is produced by a parallel task and was ABSENT when this was written: the loader
  tolerates a missing file (the family then holds the 15 lattice candidates only, flagged `file_present: false` in the
  plan record), missing columns and unknown types; the tests use a synthetic CSV of the announced schema (`id, name,
  address, lat, lon, site_type, operator, status_date, source_url, coord_method, verdict, angle`).
- Hub-capable set (design 7.4 item 19): DOT types `depot`, `lot`, `citibike_charging`, `fdny_hub`
  (`DOT_HUB_TYPES`); if fewer than 4 qualify, the 8 lattice candidates with most restaurants are added
  (`hub_fallback_lattice` in the plan); at most 12. Roles are per candidate (`candidate_roles`,
  `LowerLevelEvaluator.roles_of`): `C` only at hub-capable locations; `all_candidates_instance` and the template hold a
  hub object there only, so no hub can be priced or screened elsewhere (the paper must say so).
- Reduced size menu `SIZE_MENUS['manhattan_dot']`: SC B in {2, 3, 4} x C in {1, 2}; S B in {2, 3} (admissible only
  next to a charge-capable object); C hubs C in {2, 4}. `--menu full` keeps the `r5_manhattan` menu (reproduction run
  and the "reduced menu loses at most x" sub-result). Transfer services within `max_pair_km = 2.0`
  (`FAMILY_SPEC_OVERRIDES`, in the spec, hence in every cache key of the new family only). Consequence (fixer pass,
  review item 8): the `manhattan_dot` cache keys and pool signature differ from the `r5_manhattan` ones by the family
  name and `max_pair_km` (and the transfer pairs), so design 5.1 step 2 ("identical keys again" from a 15-point
  fixture) cannot hold and is replaced by the candidate-node identity check
  `test_lattice_fixture_reproduces_the_15_candidate_nodes`; the transplanted 15-candidate optima of stage
  `comparison` are re-priced on the new family (two to three full pricings, budgeted in that stage), never cache hits.
- Approach radius (design 1.4): `siting_pruning(..., approach_radius_blocks=N)` -> arc-builder option
  `reposition_target_radius {node: blocks}` in `arcs._template_specs` (a move route `(v, w)` into a candidate node
  `w` is skipped when `manhattan_blocks(v, w) > N`; depots unrestricted). The radius enters `pruning_signature` and
  the cache key ONLY when set (`None` adds no key), so every existing key and `config_md5` is unchanged; the
  default of `r7_siting.py` is `None` (the lane plan passes `--approach-radius 14`; its effect is measured by the
  validation of design 5.1 step 3 before any production stage). Every ILP value remains an upper bound on the
  unrestricted optimum (PRUNING_NYC caveat, now also for the radius).
- Scenario design `scenario_design(S, held_out)`: 6 strata = demand level {1.00, 1.25, 1.50 orders per bike-hour
  = 32 / 40 / 48 orders} x {weekday, weekend}; weights 5/7 and 2/7 x 1/3; two seeds per stratum at S = 12 (`p_s` =
  stratum weight / 2, sum 1); S = 6 (one seed per stratum), 10 (weekday strata x 2 seeds, weekend mid level x 4),
  15 (three seeds per weekday stratum) also supported; seeds 0-11 in-sample, 100-111 held out. Weekend scenarios use
  the generator's `weekend` hourly profile (`demand_spec.profile`, `day_type='weekend'` recorded through
  `data_nyc.make_nyc_instance`); weekday scenarios keep the family profile. `lp_scenario_subset` = the first seed
  of every stratum = the `S_LP = 6` scenarios of the branch-and-bound. `demand_md5` is asserted layout-independent
  per scenario in stage `setup`.

Algorithm (`benders.py`, `bilevel.py`):
- Regional subset bound as corrected in 7.1 item 1: `ScenarioLP.solve_subset(A)` opens every role object of every
  location in A (`y = 1`) with FREE sizes (`B` in `[0, K]`, `C` in `[c_min, min(Cbar, K)]`, the box of
  `superset_bound`), closes everything else, relaxed targets only (asserted); the `B`/`C` fixing rows of A are made
  vacuous and the copies bounded, restored after the solve. Safe value = box minimum of the C1 Lagrangian cut over the
  free copies (`Qs = c0 + sum_A beta_y + sum_A min(beta_B lb, beta_B ub) + sum_A min(beta_C lb, beta_C ub)`),
  valid for any multipliers. The max-size point of the first draft is NOT used (a toy with transfers and K near
  B_max shows it can exceed the value of a layout inside A; the free-size point never does: test
  `test_free_size_point_is_valid_with_transfers_at_K_equal_Bmax`). The bound enters the master as the combinatorial
  cut `theta_s >= LBA_s - (LBA_s - L_s) sum_{l not in A} sum_o w_{l,o}` (`Cut.kind = 'subset'`, `meta.atoms`,
  relaxed target only; written runs import it one-way as a valid relaxed floor). `A = all` reproduces the superset
  bound `L_s` (checked in stage `setup`: `all_open_equals_superset_max_abs`).
- `setup_min(k, A, inv_lo, inv_hi)` (7.1 item 3, corrected by the fixer pass) = cheapest allocated set-up of an
  admissible layout with EXACTLY k open locations inside A whose investment lies in `(inv_lo, inv_hi]` (multisets of
  menu options; a swap object; S only beside a charge-capable object; hubs at most the hub-capable count). The
  certificate of budget m is `benders.certify_bnb`: every layout within `budget_m` either has investment `<=
  budget_{m-1}` (value `>= LB_{m-1}`) or lies in the window `(budget_{m-1}, budget_m]` with `k = 1..m` open
  locations; the window is bounded per k (k = 1: windowed enumeration of the one-site layouts above `budget_{m-1}`
  -- envelope prune, LP, price; k >= 2: one `SubsetBranchAndBound` pass with the window in `setup_min`, for k = m
  this only tightens the set-up term) and `LB_m = min(LB_{m-1}, min_k floor_k)` (`bnb_certificate` record with
  `floors_by_k`). The earlier statement "layouts with fewer open locations belong to the smaller budgets" was wrong
  whenever a size option exceeds the budget unit (`SC:B4:C1` 52,200 / `SC:B4:C2` 52,600 > 52,150; `B3:C2 + B4:C2`
  104,750 > 104,300); the review's toy (UNIT = 125, F = 30: optimum 126.0 by `T2:SC:B2:C1`, old certificate 129.0)
  is now a test.
- `SubsetBranchAndBound(certifier, k, budget, levels, S_LP, node_budget, lb_smaller, inv_lo, max_level, update_lb)`
  = ONE pass of `certify_bnb` (exactly k open locations, investment window); levels = coarse regions
  (three adjacent lattice cells, south -> north) -> lattice cells -> single candidates (cells without candidates
  absent; every finer atom nested in one coarser atom, checked). Node = <= m atoms of one level; bound =
  `setup_min + sum_s p_s LBA_s` with the subset LP on the `S_LP` scenarios and `L_s` elsewhere (design 2.7: valid,
  weaker); pruned at `>= UB_m - tol`; refined into the finer atom sets touching each of its atoms; a leaf (m single
  candidates) is re-solved on all S, then its admissible size combinations are ranked envelope-ascending (larger B
  first), pruned by the master envelope or priced exactly on all S (`price(lp=False)`, `max_leaf_combos` 64).
  `LB_floor_m` = min over pruned bounds, open nodes' parent bounds and leaf floors; `LB = min(lb_smaller,
  LB_floor_m)`, nested through `_nested_lb`. Records `subset_bound` (atoms, level, bound, lba, scenarios used,
  pruned) and `bnb_done` (open nodes, leaves, stop reason); resume = `SitingCertifier.restore` (subset cuts from the
  pool, pricings from the records) so memoised values are never solved again; node budgets 200 (m = 2) and 100
  (m = 3) per pass; `--bnb-levels-m3 2` now really stops the m = 3 passes below level 2 (`max_level`: unrefined nodes
  stay open at their own bound, `n_unrefined` in `bnb_done`; the plan record's `levels` lists the levels visited),
  so m = 3 is reported as bound + incumbent without leaf pricing unless the switch is raised.
- m = 1: `certify_by_enumeration(force_lp_per_location=True)`: one LP per location (representative option
  `rep_option()` = SC:B3:C2 when in the menu) before any envelope prune, so every candidate has an LP value
  (`lp_location` records feed the map); then the second-pass enumeration (envelope prune, pricing, escalations).
- Scenario-parallel pricing `price_layout_parallel` (7.2 item 7; waves by the fixer pass): pass 1 runs in waves of
  `workers` scenarios, largest `p_s` first; each wave's `BestBdStop` uses the need computed from the bounds known
  when the wave starts, and the prune test `setup + sum_s p_s lb_s >= target` is applied before every wave (the
  remaining scenarios are then not started, as in the sequential loop); pass 2 re-solves sequentially the rows
  stopped by `BestBdStop` whose bound falls short of the updated need; the rows are folded in scenario order.
  Contract against `price_layout`, stated honestly: same status, every scenario bound at least the sequential one,
  `PRICED` results identical (rows included); `PRUNED_BY_BOUND` results may hold MORE and STRONGER rows than the
  sequential loop (the scenarios of a wave the sequential loop would have skipped, rows solved to OPTIMAL where the
  sequential stop fired first), hence possibly another feasible `V` and other cache rows. The earlier claim "the
  PriceResult has the sequential semantics" was wrong (26 of 84 toy cases differed under the all-at-once pass 1);
  the test now iterates over several thresholds. The `BestBdStop` savings of the cost table hold per wave
  (`workers` = 4 on the 16-vCPU lanes: three waves over S = 12). The evaluator's caches and `append_jsonl` are
  locked. `--price-workers` x `--threads` <= `--max-threads`.
- Two-tier pricing (7.4 item 18): `price(tier='open_sites')` prices on the evaluator's `open_sites` sibling
  (`derive(reposition='open_sites')`), returns an upper bound only: never a cut, never `LBIP`, never `priced`, never a
  comparison row (`note` on the record). Every layout of the certificate and of every comparison table is priced
  `all_candidates`; `open_sites` is reserved for greedy moves (optional stage F, not in the lane plan).
- Thread budget: the hard-coded laptop cap `lp_workers x lp_threads + master_threads <= 12` of `r6_o2_siting.py` is
  replaced by `--max-threads` (`check_thread_budget`, default `default_max_threads()` = the `run_lanes.sh` rule,
  1.5 threads per physical core, at most nproc - 1); `r7_siting.py` applies the same rule to both the LP and the
  pricing pools.
- Variants: `P_kw` = `{role: kW}` added to `bilevel.apply_variant` (site power cap of (20) per role object; data
  only) for the hub-economics setting (i); it enters the cache key like every variant.

CLI `experiments/r7_siting.py` (stages `setup, comparison, m1, bb2, bb3, polish, written, oos, compliance, hubecon,
analyse`; `--stage all` runs them in order; every stage appends to `records.jsonl`, `cuts.jsonl`, `cache/` and is
skipped when a `stage_done` record with the same `config_md5` exists, `--redo` reruns):
- `setup` = candidates (`candidates.csv`, `candidates_dropped.csv`), plan record (classes, hub-capable, scenarios and
  weights, demand hashes, menu, binaries, atoms, access zones), templates, LP sizes, z-column count, RSS, superset
  bound and the four LP timings of the size dry run (one-site, two-site, one-cell free-size, all-open free-size).
- `comparison` = rule layouts CSCD / CSTC / CSAV at every budget on the N candidates, the capacity-matched DOT pilot
  proxy (`present_day_sites` with the pilot rows of the DOT CSV as a source), the all-pilot layout (its own budget
  row), the transplanted 15-candidate optima; all on the `all_candidates` tier.
- `m1`, `bb2`, `bb3` as above; `polish` = Benders integer phase on the open budgets (fixed wall); `restricted`
  (fixer pass, design 2.6 / section 4 item 4, `--restrict dot`) = the DOT-only run: the master with the lattice-only
  candidates fixed closed (`Master.restrict(ids)`; same template, cuts and cache), per budget one bound-only solve
  (a valid lower bound on `V*_DOT >= V*_full`, raised to the full LB), the restricted incumbent (best priced layout
  inside the DOT set, else the master proposal priced exactly, then a second bound solve with its cuts), reported
  with the full bounds and the certified price range `[LB_DOT - UB_full, UB_DOT - LB_full]` as `restricted_result`
  records and table T3; the restriction is lifted before any full bound is computed (the full `budget_result`
  records are not touched; a restricted incumbent below the full one is flagged as a stale full UB); `written` = the
  best / rule / DOT layouts priced under written targets (8 layouts, escalations; relaxed LB reported beside as the
  valid floor); `oos` = the same layouts on the 12 held-out scenarios with a second evaluator sharing the cache
  directory (keys carry `demand_md5`), `V_out - V_in` with stratified and plain paired CIs; `compliance` = followers
  r2 / selfish at the best layouts (`cross_evaluate`) and the compliance sweep on the chosen m = 2 layout; `hubecon`
  = LP screen of the hub additions at the hub-capable sites only, then settings (i) `P_kw` 0.7 kW at SC / 2.8 kW at
  hubs and (ii) `F_hub` 12.03 (hub priced like a site; OPEX rows reused, set-up recomputed); `analyse` =
  `RESULTS.md` T1-T9 (bounds, regret intervals with both CIs, DOT-only vs full, role table best / best S-containing
  / best hub-containing, followers and compliance, out-of-sample, hub sensitivity, sizes and timings, written) and
  `map_data.csv`.
- `--dry-run` (plan and sizes, no solve), `--smoke` (toy, Threads 1), `--reduced N` (first N candidates of the real
  family: the 6-candidate server smoke), `--wall-<stage>` hours, `--max-rss-gb` (abort before a solve),
  `--write-lanes --vcpu 16|32` -> `outputs/cloud_lanes_siting/lanes.txt` + `lanes.json` in the `run_lanes.sh`
  format (name, threads, after, command) with the worker counts fitted to the budget (16 vCPU: 12 threads = 5 x 2 + 2
  LP workers, 4 x 3 pricing workers; 32 vCPU: 24 threads = 11 x 2 + 2 and 8 x 3) -- fixer pass (review item 2): the
  post-polish lanes that run side by side (`restricted`, `written`, `oos`, `compliance`, `hubecon`) each carry their
  OWN `--max-threads` and worker counts fitted to it (4 threads at 16 vCPU: `--lp-workers 1 --price-workers 1`), so a
  lane never opens pools larger than the threads it declares (before: 12-thread pools declared as 4, up to 36 solver
  threads at once); `--out-dir` relative to the package root, order setup -> comparison -> m1 -> bb2 -> bb3 -> polish
  -> (restricted | written | oos | compliance | hubecon) -> analyse; start with `LANES_DIR=ebike_swap_sim/outputs/cloud_lanes_siting deploy/aws/run_lanes.sh start
  ebike_swap_sim/outputs/cloud_lanes_siting/lanes.txt --max-threads N`. `sync_down.sh` now includes
  `outputs/r7_siting` and `outputs/cloud_lanes_siting`.
- Map figure `outputs/r7_siting/figs/siting_map.py` (NTA polygons, candidates by class / DOT type, depots, one-site
  LP landscape, best layouts m = 1-3 sized by B, CSCD m = 2, DOT pilot sites; second panel = the m = 2 B&B pruning
  map from the `subset_bound` records) -> `fig_dot_map.pdf/.png`, `map_summary.json`.

Validation done on the laptop (no production stage started; nothing run on the server for this step):
- `tests/test_r7_siting.py`: DOT loader (snapping, 80 m merge with priority, lattice union, cap, hub fallback, the
  15-point fixture reproduces M01..M15), pruning signature unchanged without a radius and the library byte-identical
  when the radius does not bind, scenario strata and weights, CI helpers against a hand computation, parallel pricing
  against sequential (same status, scenario bounds at least the sequential ones, PRICED results identical; corrected
  by the fixer pass), subset bound valid / monotone / equal to the superset at A = all
  against exhaustive toy values, the free-size point valid where the max-size point fails (transfers, K = B_max),
  `setup_min` hand values, `Master.restrict`, B&B = exhaustive optimum at m = 1, 2 with resume (and, fixer pass, LB <= exhaustive optimum with UNIT = 125 below
  the largest one-site investment, m = 2 and m = 3 windows), two-tier pricing
  never feeds cuts or `priced`, one LP per location once, the CLI smoke of every stage plus the lane writer, lane
  worker fitting for 16 / 32 vCPU, the r6_o2 thread budget, the `P_kw` variant: all pass at Threads 1; the opt-in
  `R7_REPRO=1` test rebuilds the `r5_manhattan` scenarios through the new code path.
- Reproduction of the 15-candidate study as a special case (design 5.1 steps 1 and 4): `--family r5_manhattan --menu
  full --scenarios 0 --seeds 0 1 2` (no radius) reproduces the three `demand_md5` and all 149 cache keys of
  `outputs/r6_o2/manhattan_pass2/cache/index.jsonl` (45 relaxed ILP, 62 written ILP, 21 baseline, 21 selfish rows);
  `r6_o2_siting.py --bound-from-cuts --no-cover` on the copied pool gives relaxed m = 1 UB = LB = 1052.995, m = 2-4
  UB 700.113 / LB 675.740, written m = 1 1131.800 / 1115.251, m = 2 699.957 / 676.240 (unchanged).
- Not done here (needs the server): the size dry run timings, the approach-radius validation (5.1 step 3), the
  subset-LP timing (5.1 step 5). The lane plan's `--approach-radius 14` must be confirmed by that validation (or
  raised to 20) before stage `comparison` starts.
- Fixer pass (2026-10-20, after the adversarial review): blocker (B&B budget-window hole) and majors (lane thread
  declarations, DOT loader id aliasing, verdict prefixes, parallel-pricing contract) fixed as described in the
  bullets above; minors: `--bnb-levels-m3` now effective (`max_level`), `--restrict dot` wired (stage `restricted`,
  T3), design 5.1 step 2 restated. Cost note: the k = 1 window of the m = 2 certificate is ~2 N one-site layouts
  (`SC:B4:C1`, `SC:B4:C2` per candidate; expected LP-free through the m = 1 LP cuts), the k = 2 window of the m = 3
  certificate re-uses the m = 2 subset LPs (memoised) and prices only the large-size pairs that the envelope does not
  close; both are counted in the `bnb_certificate` record (`passes`) so that the dry run on the server shows them.
  Suite after the fixes (2026-10-21, nice -n 15, Threads 1, laptop): 422 passed, 7 skipped (six r6_fill solver
  smokes gated on free swap, the opt-in `R7_REPRO=1` reproduction), 0 failed. `tests/test_r6_fill.py::test_lane_writer`
  failed before (lane balance 470 - 214 >= 90) because its retry counts were read from the live r6 records (most
  retries have since run); the test now monkeypatches `RECORDS` so the plan uses the digest counts it was written
  for (lanes 528 / 521 / 550 min); `experiments/r6_fill.py` itself is unchanged.
- Laptop dry run of the 6-candidate reduced family (`--family manhattan_dot --reduced 6 --scenarios 12 --held-out
  --approach-radius 14 --stage setup,comparison,m1,bb2 --dry-run`, DOT CSV absent): 6 lattice candidates (ids D01..),
  12 + 12 scenarios with 12 distinct demand hashes each, weights sum 1, orders 32 / 40 / 48, `S_LP = [0, 2, 4, 6, 8,
  10]`, 10 menu options / 56 master binaries, hub fallback = 8 lattice cells, the radius present in the pruning
  signature; `--stage analyse` and `siting_map.py` run on it (empty tables, map with NTA polygons and depots).

### R7 decisions of 2026-10-21 (main loop)

* **DOT candidate table built** (`data/raw/dot_candidate_sites.csv`, `notes/dot_candidate_sites.md`,
  `notes/figs/dot_candidate_sites.png`): 183 site records from five searches, each checked by an independent
  verifier (181 confirmed or corrected, 2 unverifiable and dropped); 61 Manhattan sites after an 80 m merge, 45 south
  of 110th Street. The loader gives N = 59 candidates (45 DOT + 14 lattice-only cells, one lattice cell merged).
  Empty classes: revocable-consent approvals and applications, FDNY sites, lots (nothing is published).
* **Hub slots** (`sites_nyc.DOT_HUB_PRIORITY`): the `max_hub = 12` hub-capable slots are filled depot (operator
  stores and hubs), lot, fdny_hub, then citibike_charging. Before, `DOT_TYPE_PRIORITY` put the 12 Citi Bike docks
  first and dropped the 4 operator stores; an indoor store with owner consent is a more credible charging hub than
  a sidewalk dock, which is only a proxy for a power connection. Result: 4 depots + 8 docks.
* **Approach-radius exemption** (`arcs` option `reposition_radius_exempt_states`, set by
  `sites_nyc._with_radius` to the start states `(v0, q0)` of the scenario's bikes whenever the radius is set; in
  the pruning signature only then): the laptop probe found one-site layouts that became INFEASIBLE_TERMINAL under
  the 14-block radius because a bike starting 51 blocks from the site with q0 = 8 had only a two-hop path whose
  'concat' rounding lost the last level. A move out of a start state (any t) ignores the radius, so a bike's first
  approach is one arc; every other tail state obeys it. The set is bike-independent (one per scenario), so it is
  applied identically to the LP template and every pricing ILP (same `siting_pruning` path per scenario); older
  families unchanged (radius unset). The first version (same day) exempted whole depot and start-node tails at
  every (t, q); review A showed it gave back 27-39 % of the radius saving, so it was narrowed. Check on the reduced
  6-candidate `manhattan_dot` family, seeds 0-7, library builds only: the terminal-infeasible bikes of every
  one-site layout (template sub-library and `open_sites` library) equal those without the radius; template arcs at
  seed 0: 2,063,565 without the radius, 1,845,391 radius without exemption, 1,930,091 tail exemption, 1,860,100
  start-state exemption (radius saving 9.9-12.3 % over the seeds, against 10.6-12.8 % without exemption and
  6.5-9.1 % with the tail exemption). The option values are normalised on read (a JSON round-trip of tuple nodes
  gives lists).
* **Hub-capable set in the run keys** (review A, major): `LowerLevelEvaluator.roles_signature()` (the per-location
  role lists) enters `benders.pool_signature`, the superset-bound key (`superset_bound_key_parts`) and
  `r7_siting.Ctx.config_md5` ONLY when some location lacks the hub role, so the keys of `r5_manhattan` and older
  families stay byte-identical; a `manhattan_dot` directory created before the hub-priority change no longer
  resumes old cuts, bounds or stage records.
* **Hub type through the 80 m merge**: the hub slot rank of a merged survivor is the best `DOT_HUB_PRIORITY` type
  among the rows it absorbed (an operator store merged into a pilot row keeps a depot's rank). No effect on the
  current CSV (its only merge is a shortlist row with a lattice cell).
* **Size cap before the hub cap** (adversarial review, minor): `dot_candidates` now applies the 60-candidate cap
  (drop `other`, then `lot`) BEFORE filling the 12 hub slots, so a lot removed by the cap can no longer hold a hub
  slot and silently leave fewer than 12 hubs (lots rank second in `DOT_HUB_PRIORITY`). The cap does not read hub
  capability, so nothing else changes; the current CSV (no cap victims, no lots) gives the identical 59 candidates
  and 12 hubs (checked byte for byte). Test `test_capped_lot_never_holds_a_hub_slot`.
* **Probe setup timings and summary** (adversarial review, minors): the representative one-site / two-site layouts
  of stage `setup` must be terminal-feasible in EVERY scenario the timings solve (all S; before, only `S_LP[0]`,
  the lowest-demand weekday scenario); `r7_probe.py summary` reads only the driver's `dot_N<N>_S<SCEN>` dirs,
  tags each with its radius convention (`exempt_states`; runs without exemption or with the whole-tail
  exemption are listed in `setup_stale`), and drops per-scenario fixed-layout times whose LP has `artificial > 0`
  from the subset / two-site ratios.
* **Idle watchdog**: the nohup copy did not survive the overnight stop/start; it is now started by an `@reboot`
  crontab entry with a 60-minute threshold and a flock guard.

### R7 production code (2026-10-21)

#### Core lane: plan section 5 items 1-4 (`benders.py`, `bilevel.py`, `experiments/r7_siting.py`, `tests/test_r7_siting.py`)

No E2 equation changes. Every new switch is off for the older families: `--superset`, `--root-merge`,
`--lp-lifecycle` and `--escalate-batch` take `auto` = on for `manhattan_dot` (non-smoke), off for the toy and
`r5_manhattan`. With these defaults the `r5_manhattan` cache keys are unchanged (`R7_REPRO=1` test green, 149 keys).
The pool signature is unchanged (`ed744dafc64e8f7e7384606bc0fd5c42`, both targets), and so is the `bound.json` key
(`b4126f130f070b38f7998bc96ef73895`). New core options default to the old behaviour: `SitingCertifier(...,
escalate_batch=False, lazy_lps=False)`, `certify_by_enumeration(..., skip_locations=None, release_lps=False)`, and
`LowerLevelEvaluator.max_templates = None`.

* **Item 1, root bound.**
  * New stage `rootlp` (`--root-scenarios s ...`, default all, longest stratum first by `root_order`: demand level
    descending, weekday before weekend). Per scenario it builds the template and ONE `ScenarioLP`, releases the LP's
    library reference, evicts the template, solves `solve_subset(all ids)`, then disposes the LP.
  * The safe value `max(0, Qs)` (box minimum of the C1 cut, valid for any multipliers) is written to
    `root_lp/root_s<NN>.json` in the `bound.json` form: `key` (md5 of the pool signature and the atom set), `bound`
    (this scenario's entry, `None` elsewhere) and `rows`.
  * The stage never writes the shared `cuts.jsonl`, because three such processes run at once and a race on the pool
    header would be possible.
  * The solving stages merge on load (`Ctx.superset` -> `merge_root`): `L_s = max(L_s, value)` over the root files
    with this key and the pool `subset` cuts whose atoms contain every candidate (e.g. the `all_open_free` timing of
    stage setup). File values are then added to the pool as `subset` cuts (`tag root`), so the B&B memo sees them.
    Record `root_bound_merged` (before / after / missing scenarios).
  * Valid for written targets through the one-way import.
  * `--superset off` (auto in production) skips the per-bike superset LP: `L_s = 0` before the merge, which is valid
    because every cost coefficient is nonnegative. It returned 0 at LP_TIME_LIMIT in all six N = 40 scenarios anyway.
  * `--root-import <cuts.jsonl>` turns the all-open subset cuts of another pool with the same signature (the step-2b
    probe pool) into root files. A pool with another signature is refused.
  * Lanes: `--write-lanes --lanes rootlp` writes `lanes_rootlp.txt`, one lane per scenario in `--root-concurrency 3`
    chains (lane i after lane i - 3, so at most 3 run at once). Each lane declares `--lp-threads`.
  * Toy check: the merged `L` equals the per-bike superset bound (51.0 / 129.5) to 1e-6.
* **Item 2, memory lifecycle.**
  * `LowerLevelEvaluator.evict_template(s)` drops a template and its derived layout libraries. `template(s)` rebuilds
    them deterministically, so the values and cache rows are identical. The test re-prices five layouts with eviction
    between every pricing and a 1-template LRU, and finds the same rows and cache rows. `max_templates` is an optional
    LRU cap (`--max-templates`), and the template dict is an `OrderedDict` shared with `derive` siblings.
  * `ScenarioLP.release_library()` drops `sub.lib`, `sub.lib_original` and `sub.agg.lib`. The LP keeps a reference to
    the per-bike library otherwise, so evicting the template alone would free nothing.
  * `benders.ScenarioLPSet` is a lazy LP container: `get(s)` builds on first use, `dispose()` frees, the next use
    rebuilds with identical solves (test), and `evict_templates` evicts after each build.
  * `SitingCertifier` accepts it (or `lazy_lps=True`). Only built LPs get their target set, `lp_at_x` builds all S in
    the main thread, `subset_bound` builds only the scenarios it solves (`S_LP`), and `release_lps()` disposes them.
  * With `--lp-lifecycle`:
    * `Ctx.scenario_lps` returns the lazy set (record `lp_built` per LP with the RSS and resident templates).
    * Stage m1 disposes the LPs between pass 1 (LPs) and pass 2 (pricing): `certify_by_enumeration(release_lps=True)`.
      Pass 2 and the escalations use `lp_memo` and the cuts only.
    * Stages comparison and restricted run with `pricing_only` (`cert.price(lp=False)`: master envelope as prior
      bounds, `full` pricing anyway), so they build no LP. Stage oos never did.
  * `--evict-templates` (off by default) evicts after each LP build. It is not used in m1 by default: the warm-start
    pricings right after the LP builds would rebuild every template (about 10 min at N = 59) for no peak saving,
    since templates + LPs is the plan's 85 GB peak either way.
  * Stages feas and rootlp always evict the template once they are done with a scenario.
* **Item 3, batched escalation.**
  * With `escalate_batch` (`--escalate-batch`, auto on in production) `SitingCertifier.escalate` re-prices every open
    scenario of the layout whose next level raises its limit in ONE `price` call (`price_layout_parallel` waves of
    `price_workers`), grouped by time limit.
  * Levels are still counted per (layout, scenario), and the pricing is the same `full` / longer-limit / warm-start
    solve. Only the number of calls changes. The per-layout LP is not rebuilt (`lp` only when the layout is in
    `lp_memo`).
  * Records: `escalate` with `scenarios`, `levels`, `batched`; counter `escalation_waves` (present only when batching
    ran).
  * `--max-escalations` default raised 2 -> 3, with new `--escalate-factor` (3) and `--escalate-cap-s` (1,800).
    Note: with base 300 s, factor 3 and cap 1,800 s, level 3 equals level 2 and is skipped as a wasted level. Raising
    the default costs nothing and takes effect if the cap is raised or a lower base limit is used.
* **Item 4, feasibility skip list and window rows.**
  * New stage `feas` (stage A; `--feas-scenarios`, default all; `--write-lanes --lanes feas` writes
    `--feas-processes 4` disjoint groups). It derives the one-site `SC` layout library at every location from each
    scenario's template, with no solve, and writes `feas_one_site_<tag>.json`: the rows of `r7_probe.py feas` plus
    `signature = benders.feasibility_signature(ev)` (pool signature and candidate nodes), seeds and demand hashes.
  * The solving stages read every `feas_one_site*.json` of `--out-dir` (or `--feas-json`). A claim is used only with a
    proof for THIS evaluator: the same signature, or else one library build (`benders.verify_terminal_infeasible`)
    re-proves it. Probe files, which carry no signature, are always re-proved, and unconfirmed claims are dropped and
    listed (record `feas_skip_list`).
  * `SitingCertifier.mark_terminal_infeasible(loc, s)` stores every menu size option of `loc:SC` as `INFEASIBLE`
    (INFEASIBLE_TERMINAL, `V = inf`, `n_solves 0`, `price` record tag `feas_skip` so that `restore` keeps it), without
    an LP or an ILP.
  * Validity for all sizes: under the all-candidates convention `subset_library` keeps the swap / terminal arcs of the
    open swap objects only, and B, C enter neither the arcs nor the reachability pass. Test: every SC size of a K = 4,
    Cbar = 2 menu, both targets, two toy worlds incl. a radius-0 far start, and the evaluator's status agrees.
  * Stage m1 passes the locations as `skip_locations`, so they get no forced LP.
  * Row decision: the master row added is the existing terminal row of `_integer_cuts` (the other swap objects sum to
    >= 1), not the plan's literal `y_l <= sum_{l' != l} y_l'`.
    * The terminal row implies the plan's row under the master's structural rows (a swap object; S only beside a
      charge object), and the test checks the plan's row at every admissible layout.
    * It is also stronger: it excludes `l:SC` with charge-only hubs elsewhere, which is infeasible by the same argument
      (a hub adds no swap or terminal arc).
    * It is role-exact, whereas the literal row over all options of `l` would be invalid for an S-only layout if
      `s_needs_charge` were off.
    * It lives in the pool (target `both`), so bb2 / bb3 and the final master (`LB_2`) use it.
  * Test: against the exhaustive values of every toy layout within 3 units, every layout the rows newly exclude has
    `V = inf`.
  * Interaction with the budget-window passes (test with UNIT = 125, F = 2 / 30, m = 1-3):
    * The k = 1 window enumeration skips the marked layouts as resolved (envelope `inf`, counted `n_infeasible`), with
      no LP and no pricing.
    * `setup_min` of the k >= 2 node bounds ignores the rows, which makes it weaker but never invalid.
    * B&B leaves filter combinations by `in_master`.
    * `LB_m <= V*_m = UB_m` at m = 1, 2, 3.
  * Not done: the held-out out-of-sample layouts' check (stage I) belongs to `r7_search.py`.
* **Thread check.** Runs of only `feas` / `rootlp` check `lp_threads <= --max-threads` instead of the LP / pricing
  pool rule, so the rootlp lanes declare exactly the LP's threads.
* **Laptop checks** (nice -n 15, Gurobi Threads 1):
  * `tests/test_r7_siting.py`, `tests/test_bilevel.py`, `tests/test_o2_benders.py`: all pass (one skip, the opt-in
    reproduction). The 8 new tests are listed in the test file under "R7 production code".
  * `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced`: pass.
  * Smoke `--stage all` with the defaults, and again with every switch on: acceptance ok at m = 1, 2.
  * Reduced-6 `manhattan_dot` (radius 14, seed 0): the dry run passes. `feas` found 0 infeasible one-site layouts
    (start-state exemption), 17 s. `rootlp` gave all-open LP 845.506 in 33 s (1 thread), RSS 1.8 GB.
  * Reduced-6 `m1` with every production default (`--budgets 1 --time-limit 30 --tol-rel 0.01`):
    * superset skipped; `L` merged 0 -> 845.506 from the root file;
    * empty skip list; 1 lazy LP built, then released before pricing;
    * one batched escalation; certified, gap 0.009 %;
    * 152 s, peak RSS 2.7 GB.
* **Markers for the `STALE CODE` check of the upload** (plan item 10): `def stage_rootlp`, `def stage_feas`,
  `class ScenarioLPSet`, `def mark_terminal_infeasible`, `def _escalate_batch`, `def evict_template`.

#### Drivers lane: plan section 5 items 5-7 (`experiments/r7_siting.py` comparison + CLI, `experiments/r7_search.py`, `experiments/r7_cost.py`, `deploy/aws`, `tests/test_r7_search.py`)

No core module changed (`benders.py`, `bilevel.py`, `sites_nyc.py`, `arcs.py` untouched in this lane). Older
families: same cache keys, pruning and pool signatures (`r5_manhattan` pool signature recomputed through the r7
path: `ed744dafc64e8f7e7384606bc0fd5c42` for both targets; `R7_REPRO=1 ... -k reproduced` green). Every new
default keeps the old behaviour for the toy and `r5_manhattan`.

* **Item 5, comparison filter** (`stage_comparison`).
  * `--comparison-rules` takes `NAME` or `NAME@m1,m2` tokens (NAME in CSCD, CSTC, CSAV, dot_pilot_proxy,
    dot_all_pilot, transplant); `--comparison-budgets m ...` is the default m set of the per-budget rows named
    without `@`. The rows with their own budget (dot_all_pilot, transplant) are kept at any m unless `@` restricts
    them. Neither flag = every row (old behaviour). Production: `CSCD@1,2,3 CSAV@2 dot_all_pilot dot_pilot_proxy@2`.
  * `--comparison-time-limits m:seconds ...` sets the per-row ILP limit; `auto` = `2:600` for `manhattan_dot`, none
    for the toy and `r5_manhattan`. A row priced earlier at a shorter limit is re-priced (final cached rows
    reused, TIME_LIMIT rows re-solved warm); the `baseline` record carries `time_limit`.
  * The stage now restores the prior `budget_result` LB of every budget before `finish`
    (`restore_prior_lb`, as bb / polish already did). Reason: the production order runs comparison AFTER m1, and
    without it the comparison's `budget_result` (the master's pool bound, no enumeration floor) would become the
    last one of budget 1 and RESULTS would show m = 1 as not certified. Only raises LB (valid).
* **m1 warm start in production** (`m1_warm_layouts`, manhattan_dot only). Found while costing batch 2: the m1
  certifier has the single budget b1, so a warm layout above b1 gets `ub_ref = -inf`, which `price_layout`
  treats as "no incumbent" and prices IN FULL, after 12 forced LPs. The warm list holds the rule layouts of
  m = 2, 3 and the DOT pilot, i.e. about 7 layouts x (12 LPs + 12 ILPs), roughly 3.5 h of batch 2 that the
  m = 1 certificate never uses. Production now warm-starts with the warm layouts within b1 plus a one-site
  layout at each location of the transplanted optima (plan stage B: "the transplanted sites first for UB_1");
  record `m1_warm`. The toy and `r5_manhattan` keep the unfiltered list.
* **Item 6, `experiments/r7_search.py`** (same configuration flags, records, pool and cache as `r7_siting.py`;
  record stages `search_<stage>`; every stage resumes from `stage_done`, the restored prices and the memoised
  subset bounds; `--redo` reruns without re-solving what is stored).
  * Bounds of a location set A at budget m (`set_bound`, S_LP rule: subset LPs on S_LP, `L_s` elsewhere):
    `bound_exact = setup_min(|A|, A, inv <= b_m) + sum_s p_s LBA_s` is valid for every layout whose open set is
    exactly A, all sizes; `bound_window = min_k setup_min(k, A, (b_{m-1}, b_m]) + ...` for every layout inside A in
    the window (budget-window rule). A pair is reported `excluded` only when `bound_exact >= UB_2 - tol`.
    Toy test: both bounds below the exhaustive value of every covered layout at m = 2, 3.
  * `pairs` (stage E): seeds = `--pair-seeds` (`A+B`; `|` would be a pipe in the lane command), the
    transplanted pairs, the two best m = 1 locations, coverage complements (a location infeasible alone + the
    best m = 1 location whose infeasible bikes are disjoint from its own in every scenario; from the stage-A
    files, seeds only), relax-and-round seeds; then 1-swaps of the best seed over the `--pair-swap-pool` best
    m = 1 locations, up to `--pair-screens 16`; the best `--pair-price 4` non-excluded pairs priced (BestBdStop
    against UB_2, `lp=False`: the subset cut is the prior).
  * Decision: relax-and-round rounds the MASTER LP point at budget 2 (with the pool's cuts), not the all-open LP
    usage. `solve_subset` returns no usage and stage rootlp stores none; an extra all-open LP with usage would cost
    1.6-3.4 h per scenario at N = 59. Storing the usage is a 3-line core change, left out because core modules
    are frozen in this lane.
  * Decision: the layout priced for a location set is chosen by `pick_layout` (sizes nearest each location's
    one-site best, SC + SC first, ties by the envelope). The envelope alone picks the cheapest set-up, because
    every size combination of a set shares the subset cut; on reduced-6 it priced `D05:S:B2:C0|D06:SC:B2:C1` at
    V = 1,615 against UB 1,217. Heuristic only: no bound depends on it.
  * `m3` (stage F): the best two-site layout (the m = 2 incumbent, else the best two-site layout with a value),
    at the sizes nearest B4:C2, and plus each of the `--m3-thirds 2` best m = 1 locations (SC at the
    representative size, else the cheapest SC that fits); optional triple screen `--m3-screen n`. The claim
    stays "no layout found", not proved.
  * `roles` (stage H, `--role-budgets 2`): best S-containing layout at the incumbent's and the best screened
    pairs; hub screen = `subset_bound({h} + incumbent sites)` on `--hub-scenarios 3` (S_LP in root order) for
    every hub-capable site, the best `--role-hub-price 2` priced at the hub limit (full); record `role_row`
    with the price of S and of a hub.
  * `oos-feas` / `oos` (stage I): the list `best@m1 best@m2 CSCD@m2 dot_all_pilot` (names resolved from the
    records, rules from `rule_layouts` when no comparison record exists); every (layout, held-out scenario)
    checked by a library build first (records `oos_feas`, resumable); a layout with a bike without a terminal arc
    is reported `INFEASIBLE_OUT_OF_SAMPLE` and not priced; the others priced full (records `oos_result`, read by
    RESULTS T6). Batch 1 runs the check for the layouts known then (CSCD@m2, DOT all-pilot); oos re-checks the rest.
  * `noradius` (stage R): every m = 1 layout PRICED within `--near-tie 3 %` of UB_1 plus best@m2 and best@m3 on
    an evaluator with the radius unset (same scenarios, spec, protocol and cache; cache keys differ by the radius
    only); scenario-major with `--noradius-group 4` templates resident and evicted per group; the radius
    schedule of the same cell is the MIP start (feasible: the radius only removes arcs). Layouts whose lower
    bound lies in the band but have no exact V are listed (`unpriced_in_band`), not re-priced.
    `noradius_summary` gives the order with and without the radius and the m = 1 vs m = 2/3 effect.
  * `price-list`: `--layouts` / `--layouts-file` on `--evaluator in | out | noradius`.
  * `calib` (stage P): one 12-cell pricing (templates timed first; utilisation and overhead per cell), one
    one-cell free-size LP with crossover and with `Crossover 0` (set on the model for the timing only; plan
    item 9 keeps it if it saves >= 15 %), and 8 one-site LPs as 3 x 3 against 4 x 2. Decision: the layout must be
    terminal-feasible in every in-sample scenario (library builds, at most 8 tries). The transplanted M09 = D38,
    the first choice, is infeasible alone in one N = 59 scenario, and its pricing would measure nothing.
  * `report`: `SEARCH.md`.
* **Item 7, cost per batch** (`experiments/r7_cost.py`).
  * Every `r7_siting.py` / `r7_search.py` invocation with an out-dir appends `{stage, start, end, start_epoch,
    end_epoch, wall_h, instance, usd_per_h, usd, batch, script, status, dry_run, host, pid, argv}` to
    `cost.jsonl`. The row is written in a `finally`, so it is also written for a failed run (`status error: ...`).
  * Instance and price come from `R7_INSTANCE` / `R7_USD_PER_H` (defaults r7i.4xlarge, 1.0584); the batch comes
    from `R7_BATCH`. `--write-lanes` writes no row.
  * `summarise` gives per batch the plain sum and the union of the time intervals (lanes that overlap on one
    instance are counted once). RESULTS.md and SEARCH.md carry the table; `python3 experiments/r7_cost.py <dir>`
    prints it.
* **Production lane plan** (`r7_search.py --write-lanes` -> `outputs/cloud_lanes_siting_prod/lanes.txt` + `.json`;
  r7i.4xlarge, budget 12 threads, `--max-rss-gb 110`, `--tol-rel 0.01 --tol-abs 1`, radius 14, S = 12 + 12
  held out, out-dir `outputs/r7_siting`).
  * 26 lanes in the six batches of plan 2.2, chained by `after`. Every command is prefixed with
    `R7_BATCH=<n> R7_INSTANCE=r7i.4xlarge R7_USD_PER_H=1.0584`.
  * Batch 1 (3.8 h): calib (12 threads), then 4 feas processes (1 thread each, about 26 GB each), then the
    held-out check.
  * Batch 2 (13.9 h): m1 with `--wall-m1 13`, LP pool 3 x 3 + 2, pricing pool 4 x 3.
  * Batch 3 (13.5 h): 12 rootlp lanes, longest stratum first, in 3 chains of 4 threads. The first lane passes
    `--root-import outputs/r7_siting_probe/dot_Nall_S12/cuts.jsonl` (step 2b; refused and recorded if the
    signature differs).
  * Batch 4 (9.2 h): pairs (`--pair-seeds D30+D38 D09+D38`, 16 screens, 4 priced), m3, roles.
  * Batch 5 (5.6 h): filtered comparison, restricted, oos.
  * Batch 6 (4.0 h): noradius (3 x 3 threads, groups of 4).
  * Total about 50 h = 52.9 USD (plan 49.9 h / 52.8 USD; rounding). Analysis stays on the laptop.
  * `deploy/aws/sync_up.sh` now uploads the two plan files (`lanes.txt`, `lanes.json`; never the status files);
    `README_AWS.md` section 9.1 has the commands.
  * Test: every lane command parses with its script's parser, satisfies its own thread check and declares
    exactly its `--max-threads`; dependencies come first; at most 3 root LPs run at once; `run_lanes.sh start
    --dry-run` accepts the file.
* **Markers for the `STALE CODE` check** (plan item 10, drivers lane): `def comparison_filter`,
  `def m1_warm_layouts`, `class CostLog`, `def stage_pairs`, `def stage_noradius`, `def write_prod_lanes`.
* **Laptop checks, drivers lane** (nice -n 15, Gurobi Threads 1; no ssh):
  * Tests: `tests/test_r7_search.py` (7 new tests), `test_r7_siting.py`, `test_bilevel.py` and `test_o2_benders.py`
    all pass, with one skip (the opt-in reproduction). `R7_REPRO=1 ... -k reproduced` also passes.
  * Toy, production order (feas, rootlp, m1 -> calib, pairs, m3, roles -> filtered comparison, restricted ->
    oos, noradius, price-list -> analyse):
    * every `budget_result` has LB <= V* <= UB against the exhaustive optimum at m = 1, 2, 3;
    * the m = 1 certificate survives the later stages;
    * the comparison rows are exactly CSCD m = 1-3, CSAV m = 2 and dot_pilot_proxy m = 2 (the toy has no
      pilot site);
    * the infeasible `T4:SC:B2:C1` is reported infeasible out of sample and not priced;
    * there is one `cost.jsonl` row per invocation;
    * a rerun skips the 5 done stages, and `--redo` re-solves no stored price or subset LP.
  * Production-size dry run of every search stage (N = 59, S = 12 + 12 held out, radius 14): passes.
    * Building the context takes about 11 min on the laptop, which is 24 scenario instances.
    * Seeds: D30|D38, D09|D38 and the two best m = 1 locations.
    * Hub screen: 12 hub sites on scenarios 4, 10 and 2.
    * Held-out check at batch 1: CSCD@m2 = `D18:SC:B3:C2|D19:SC:B3:C2` and the DOT all-pilot layout
      `D12:SC:B3:C2|D18:SC:B3:C2`.
  * Reduced-6 `manhattan_dot` (seeds 0 1, radius 14, `--time-limit 30`, budgets 1-3):
    * m1 certified: UB 1,216.73, LB 1,210.02, gap 0.55 %. The production warm start was `D06:SC:B3:C2`,
      `D05:SC:B3:C2`.
    * pairs: 5 screened (coverage complements and one relax-and-round seed); 1 excluded.
    * m3: `pair_max_sizes` priced at 1,524.80. No third site was tried: the other locations are infeasible
      alone on these seeds.
    * Filtered comparison: CSCD m = 2 = `D05:SC:B3:C2|D06:SC:B3:C2` at V = 942.42, the m = 2 incumbent;
      LB_2 = 853.32, gap 9.5 %.
    * noradius: re-priced the m = 1 tie and best@m2 on the no-radius library (2,063,565 arcs against
      1,860,100). Both values equal the radius values: at 30 s the warm radius schedule is not improved.
    * Wall time 0.43 h in total, and the cost table is in RESULTS.md and SEARCH.md.
  * Laptop artifact worth knowing: the same pair was V = 1,281.57 at the 30 s limit (pairs stage) and 942.42 at
    60 s (comparison, warm re-solve). Values priced at short limits are poor incumbents. Production prices at
    300 s with escalation, and the m = 2 comparison rows at 600 s.

#### Fixer pass: the two reviews of 2026-10-21 (core + drivers)

No E2 equation changed, and no bound rule changed (safe Lagrangian cuts, relaxed-only subset bounds, budget-window
rule, S_LP rule, two tiers). Every change either chooses WHICH cells or layouts are solved, or changes bookkeeping.
For `r5_manhattan` and the toy every new default keeps the old behaviour: the cap is off and `--max-escalations` is 2.
The one exception is the template-sharing rule of `derive`, which never changes a cache key. The `R7_REPRO=1` check
passes and the pool signature is unchanged (`ed744dafc64e8f7e7384606bc0fd5c42`).

* **Batched escalation waves** (`benders.price_layout_parallel`, review 1 major).
  * Problem: with `scenarios=` given, the waves were cut from the p_s order of ALL scenarios. The open cells of a
    layout therefore ran in up to ceil(S / workers) waves one after another.
  * Fix: the cached rows of the scenarios outside `scenarios` are taken first, and the waves are cut from the
    scenarios that may still need a solve. Nothing changes for `scenarios=None`.
  * Test: two open scenarios with workers = 2 start within 0.3 s of each other (one wave).
* **Escalation cap at levels >= 2** (`SitingCertifier(escalate_batch_max=...)`, `--escalate-batch-max`, review 1
  major).
  * Default `auto`: `--price-workers` (4, one wave) for `manhattan_dot`; unlimited for the older families, as
    before.
  * At level 1 the batch still takes every open scenario. At level >= 2 (the 900-1,800 s limits) it takes the open
    scenarios by largest p_s x gap_s, and stops once their weighted gaps cover the layout's deficit
    `(UB_ref - tol) - lower`, or at the cap.
  * The scenarios left out keep their level. The next `escalate` call takes them; the callers re-test the gap after
    every call. Counter: `escalation_cells_deferred`.
  * Re-cost of stage C: about one wave (4 cells x about 1,881 s, about 0.5 h) per level-2 layout. Two layouts come
    to about 1.0 h, against the plan's 0.8 h for "the 4-8 worst cells". The uncapped batch needed about 3.1 h.
* **m1 warm start memory** (`SitingCertifier.warm_start(release_lps=True, before_pricing=...)`, review 1 major).
  * The new order in production (`--lp-lifecycle`):
    1. solve the warm layouts' LPs;
    2. dispose the lazy LPs;
    3. run the RSS guard;
    4. price (lp from `lp_memo`; no LP rebuilt).
  * The 12 LPs (about 30 GB) and the 4 pricing ILPs (about 20 GB) are therefore never resident together on top of
    the templates (about 55 GB). Pass 1 of the enumeration rebuilds the LPs lazily.
  * Records `m1_warm_memory` (RSS before, after release, after pricing).
  * Test: event order `lp_layout, lp_layout, lp_release, price, price`; no LP built by the pricings; the values
    equal the interleaved order.
* **Cost rows of stopped / killed lanes** (`r7_cost.py`, both reviews).
  * A `start` row is written when the invocation begins, and the end row when it ends.
  * `CostLog.install_signal_handlers()` (both mains): SIGTERM (`run_lanes.sh stop`) and SIGHUP (`tmux
    kill-session`) write the end row with status `killed: SIG...` and then `os._exit(128 + signum)`.
    * Decision: exit at once, as the default handler does, instead of raising SystemExit. A `finally` would wait
      for the Gurobi solves in flight (thread pool shutdown), up to a full time limit.
    * Records and cuts are appended line by line and root files are written atomically, so nothing is left
      half-written.
  * A start row without an end row (SIGKILL, OOM, instance stop) is counted as `unfinished` in `summarise` and the
    cost table. While the pid is alive on this host, its interval runs to now; otherwise it is empty and only
    counted.
  * Test: SIGTERM, SIGHUP and SIGKILL of a child.
* **Laptop analysis rows** (both reviews).
  * `--stage analyse` (r7_siting) and `--stage report` (r7_search) write no cost row.
  * Rows without `R7_BATCH` are listed as "unbatched, not in total" and left out of the total whenever batched rows
    exist.
* **Records of another instance** (review 1 minor).
  * Every record now carries `instance_md5`: `config_md5` without the budget list, because a `budget_result`
    carries its own budget, and runs with another `--budgets` (e.g. m1 with `--budgets 1`) must still share bounds.
  * `Run.load()` drops records stamped with another instance. Every restore goes through it: `last_results`,
    `restore_prior_lb`, `priced_layouts`, `SitingCertifier.restore` and analyse.
  * A `--reduced` run or another radius written into `outputs/r7_siting` can therefore never import a foreign LB.
  * Records from before the stamp carry none and are kept.
* **`--max-escalations` default** (review 1 minor): `auto` gives 3 for `manhattan_dot` and 2 (the old default) for
  the toy and `r5_manhattan`.
* **No-radius effect at equal limits** (review 1 minor; `--noradius-time-limit match`, the default).
  * Each no-radius cell is solved at the time limit of the radius row of the same cell (at least the base limit).
  * `noradius_result` records both limit lists and `limits_equal`.
  * With `base`, the old behaviour, the record says that the effect is a lower bound.
* **Template sharing in `derive`** (review 1 minor; `bilevel.py`).
  * Problem: the template instance is built from the whole spec (`facility`: K, Cbar, M, sigma, P_kw, F, F_hub,
    R_end; `_finish`: services, grid).
  * Fix: siblings share the template dict only when the spec dicts are equal, not just sigma and max_pair_km.
  * Consequence: hubecon (other F_hub) builds its own templates (time and memory only, at its stage). Cache keys are
    unchanged. Siblings' layout libraries are still not evicted together (not reachable in the production plan).
* **Relative `LANES_DIR`** (review 2 major; `deploy/aws/run_lanes.sh`, `sync_down.sh`, README 9.1, lanes header).
  * `run_lanes.sh` makes `LANES_DIR` absolute (relative to the directory the command is run from) and passes it
    explicitly into the dispatcher's tmux command. A running tmux server, e.g. the probe's, does not hand the
    environment to a new session.
  * The header and README use `LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod`.
  * `sync_down.sh` fetches that folder (status files and lane logs).
* **Stale m = 2 incumbent** (review 2 major).
  * `stage_restricted` now ends with `restore_prior_lb` + `cert.finish()`. A restricted layout is a full-problem
    layout, so its price is a valid full UB; `finish` writes a `budget_result` with the restriction lifted.
  * `best_known()` (r7_search) and analyse T1 take the better of the last `budget_result` UB and the best priced
    layout. T1 marks the layout "(later)", recomputes the gap with the run's tolerance, and lists the case under
    Problems.
* **Pair pricing** (review 2 major; decision).
  * The first try of a non-excluded pair is still the SC + SC layout at the sizes nearest the one-site bests.
  * When a try comes back PRUNED_BY_BOUND or INFEASIBLE, `pair_next_layout` takes the untried layout of the same
    pair with the lowest master envelope, re-read after every pricing, so SC + S and smaller sizes are included.
    It stops when one is PRICED, when the lowest remaining envelope reaches UB_2 - tol (the pair is then resolved),
    or after `--pair-tries 4`.
  * Only PRICED pairs count against `--pair-price`. All pairs together use at most `--pair-price x --pair-tries`
    pricing calls (16).
  * Toy production order: the second try of {T1, T2} prices `T1:S:B1:C0|T2:SC:B1:C1` at V = 95.50 = V*_2, and m = 2
    is certified from the pairs stage on. Before, the pair search missed the optimum, and the role table gave
    price_of_S = +4.25; it now gives 0.
  * Heuristic choice only: no bound depends on it.
* **Analysis and map read the production records** (review 2 major).
  * When the records have no `plan` record, analyse emits one from the context (`instance_plan`, source
    "analyse"). It writes `candidates.csv` when it is missing, because the production lanes never run stage setup.
  * New RESULTS section "Certificate details (plan section 3)":
    * the skip list (count and locations);
    * the merged root values and the missing scenarios;
    * epsilon_1, the achieved incumbent MIP gap of the m = 1 layout, `(V - lower) / V`, with the worst scenario;
    * the near-tie set at m = 1 (`--near-tie`, 3 %).
  * Problems also lists: unconfirmed feasibility claims, missing root scenarios, a refused `--root-import`, and an
    incomplete rootlp.
  * `map_data.csv` gains `terminal_infeasible`, `near_tie_m1` and `pair_status`.
  * `siting_map.py`:
    * panel 1 marks terminal-infeasible sites with a red cross;
    * without bb2 records, panel 2 shows the m = 2 search and the feasibility screen: infeasible alone, in the
      m = 2 incumbent, near tie, in a screened pair, only in excluded pairs.
  * Test: the toy production order plus the map gives `panel2 = production`, with T4 terminal-infeasible.
* **Calibration timing** (review 2 minor). Stage calib evicts every template and layout library after the
  feasibility check of the calibration layout, so part (a) times the template builds and the cells build their
  libraries.
* **`--held-out`** (review 2 minor).
  * Only `b1_oos_feas` and `b5_oos` pass it. Before, all 26 lanes passed it, and each built 12 more N = 59 instances
    at start-up (15-28 s each; about 1.2-2.2 h of instance time in all).
  * The flag changes no key and no `config_md5` / `instance_md5`. Batch hours are unchanged: the plan costed only
    6 start-ups for item J.
* **rootlp exit code** (review 2 minor). A rootlp lane with a requested scenario that has no finite value (RSS guard
  or a non-OPTIMAL LP) emits `rootlp_incomplete`, writes no `stage_done` and exits 3. The dispatcher marks the lane
  failed, and it can be re-run. Test with `--max-rss-gb 0.0001`.
* **STALE CODE gate** (review 2 minor).
  * New first lane `b0_gate`: 1 thread, `python3 experiments/r7_gate.py`, the after-dependency of `b1_calib`.
  * It checks 17 markers and exits 2 on a miss: the 12 markers of the two lanes plus `escalate_batch_max`,
    `def install_signal_handlers`, `def instance_md5`, `def instance_plan` and `def pair_next_layout`.
  * The lane plan now has 27 lanes.
* **Probe precondition** (review 2 minor).
  * The lanes header and README 9.1 now say: start only when `tmux ls` shows no probe session and `probe.log` ends
    with "probe done", or the probe was stopped by hand.
  * Reason: the 110 GB guard is per process, so nothing would stop batch 1 running beside the probe.
* **Not done** (review 1, optional): `evict_template` still clears only the evicting sibling's layout libraries.
* **Laptop checks of the fixer pass** (nice -n 15, Gurobi Threads 1; toy, reduced-6 and `--write-lanes` only; no
  ssh):
  * Full suite: 453 passed, 7 skipped, 0 failed. The skips are the six r6_fill smokes and the opt-in reproduction.
    There are 9 new tests: 4 in `test_r7_siting.py` (waves, cap, warm start, derive) and 5 in `test_r7_search.py`
    (signals, unbatched total, instance filter, max-escalations default, rootlp exit). The e2e and lane-plan tests
    were extended.
  * `R7_REPRO=1 ... -k reproduced`: pass. The `r5_manhattan` pool signature, recomputed through the r7 path, is
    `ed744dafc64e8f7e7384606bc0fd5c42` for both targets; `max_escalations` 2, cap off.
  * Toy production order:
    * m = 1-3 are certified at V* (98.00 / 95.50 / 95.50);
    * the last `budget_result` of m = 2 holds V*_2;
    * the map runs with the production panel;
    * one cost row per billed invocation, and none for analyse.
  * Reduced-6 `m1` with the production defaults (`feas,rootlp,m1`, `--time-limit 30 --tol-rel 0.01`):
    * the warm LPs were solved and released before the warm pricing (RSS 1.8 -> 2.0 GB);
    * one batched level-1 escalation;
    * certified, gap 0.009 %, UB 1,172.69;
    * 3.5 min.
  * `outputs/cloud_lanes_siting_prod/lanes.txt` / `.json` were rewritten: 27 lanes, about 50.0 h = 52.9 USD.

#### Gate: plan section 5 item 10 (`deploy/aws/r7_prod_check.sh`, `r7_code.zip`)

* **New `deploy/aws/r7_prod_check.sh` instead of new markers in `r7_probe.sh`.** The step-2b probe is executing
  `r7_probe.sh` on the server and bash reads a running script lazily, so that file stays byte-identical. The new
  script greps 42 fixed-string markers (each tagged with its change: 1 root bound 5, 2 memory lifecycle 5,
  3 batched escalation 2, 4 feasibility skip list 5, 5 comparison filter 3, 6 search driver 12, 7 cost per batch
  3, fixer 2, gate 1, tests 4). It also checks that the lane plan is present with `b0_gate` first, and that the
  probe has finished (no tmux session `probe`, `probe.log` ends with "probe done"). Exit codes: 0 ok, 2 stale code
  or missing plan, 3 probe running; `--root DIR --no-probe` checks a local tree. `experiments/r7_gate.py` (lane
  `b0_gate`, 17 markers) is unchanged, so the lane plan and its test are unchanged.
* **`r7_code.zip` contents**: as the 10:54 build (paths relative to the project root:
  `data/raw/dot_candidate_sites.csv`, `deploy/aws/*`, `ebike_swap_sim/{CONTRACT.md,README.md,pytest.ini}`, the
  `*.py` of the package, `experiments` and `tests`), plus `outputs/cloud_lanes_siting_prod/lanes.txt` and
  `lanes.json`, plus the new `watch.sh` and `r7_prod_check.sh`. Left out: `aws_env.sh` and `aws_env.example.sh`,
  licence, keys, `__pycache__`, every other output.
* **`README_AWS.md` left out of the zip** (it was in the 10:54 build). It has 64 lines with Chinese console labels
  (the CJK scan of the upload must be clean) and the server never reads it; the laptop copy keeps it.
* **Unpack only after the probe**: the zip replaces `r7_probe.sh` and the package that the probe's later step-2b
  sub-steps (`step2b_price`, `step2b_feas`) import, so `unzip` waits for "probe done".
* **Per-batch start** with `run_lanes.sh start ... --only <batch lanes>` (commands in the plan, section 8): each
  batch can be checked (memory plan, step-2b factors, cost) before the next starts. Dependencies across batches are
  read from the lane status files in the same `LANES_DIR`. Each selection passes `--dry-run` locally.
* **Laptop gate results** (nice -n 15, Threads 1): full suite 453 passed, 7 skipped, 0 failed (12.1 min; the skips are the six r6_fill smokes and the opt-in reproduction); `R7_REPRO=1 ... -k reproduced`
  1 passed (149 keys); pool signature `ed744dafc64e8f7e7384606bc0fd5c42` (both targets); lane plan re-written to
  scratch and identical; zip 103 files, all md5-identical to the tree, 0 CJK, no secrets.

### R7 re-plan after batch 2 (2026-10-23)

Plan: `notes/siting_production_replan_m1.md` sections 2-7, with the critic corrections K1-K7 overriding it. Main
loop decision: no concurrent C0 lane beside batch 3; every new step runs after batch 3 (about 11:00 UTC) at the
full 12-thread budget (4 x 3 pricing). All production commands use `--tol-rel 0.01`; the analyse stage reports the
open-sites gap with tol = 0 (K2.2).

#### Core lane: changes 1, 4, 5, 6 (with K2 / K3)

Files: `ebike_swap_sim/benders.py`, `ebike_swap_sim/bilevel.py`, the m1 path of `experiments/r7_siting.py`, new
`tests/test_r7_replan.py` (14 tests). E2 equations unchanged. Every new switch defaults to the old behaviour.

* **Change 1, restore of `price_open`** (`SitingCertifier.restore` / `_restore_open`).
  * `price_open` records of the certifier's target go into `priced_open`. Per layout, the record with the lowest
    `V` is kept (else the last one).
  * Their `V` updates `UB` / `best` for in-menu layouts only.
  * They never enter `priced`, the cut pool, `LBIP`, the enumeration floor or `enum_open_priced`.
  * The restored result keeps no all-candidates bound. Its `lb` is the record's `lb_open` (open-sites follower
    only) or `L`.
  * `_price_open` records now also carry `lb_open` / `lower_open`, named so that nothing reads them as an
    all-candidates bound (K2.7). The open-sites certificate of change 8 can use them.
  * K2.7 in `result()`: when the incumbent is an open-sites pricing, `best_lb` is `None`, and `best_tier` /
    `best_lb_open` are added. Before, the open-sites ILP bounds would have shown up as `best_lb`.
  * `restored` gains `priced_open`, only when such records exist.
* **Change 4, warm all-candidates from open_sites.**
  * `price_layout(..., warm_tier='open_sites')` (also `price_layout_parallel`, `SitingCertifier.price`).
  * Each all-candidates solve gets one schedule to offer: the lower-total of the cached row's own schedule and the
    open-sites sibling's cached schedule of the same cell (`_warm_pick`). The sibling is looked up with the base
    Gurobi params, under which its rows were solved.
  * The evaluator still materialises and `check`s the offered schedule, and keeps the rule start when that is
    cheaper (`mip_start_variant` = `warm_parent` only when better).
  * With `warm_source` set, a row records `warm_source`, `warm_available`, `warm_materialised`,
    `warm_check_ok` and `warm_obj`. Rows priced without the switch are unchanged (same row fields, same records).
  * After such a pricing the certifier emits `ub_check_all_candidates` (`source = pricing_warm_start`): per cell
    materialised / check / cost against the open-sites total.
  * M6 is `SitingCertifier.ub_check_all_candidates(layout)` (module function of the same name). It materialises
    the 12 open-sites schedules on the all-candidates layout library (this builds the templates), runs `check` and
    `cost`, and emits the record with `V_checked` and `V_open`. The UB is not changed (the open-sites V already is
    one); the record is its validity proof (K3.5).
* **Change 5.**
  * `certify_by_enumeration(price_pass=False)` is `--m1-pass2 off`. Pass 2 applies the envelope and v_LP prunes
    but prices nothing, pass 3 (escalation) is skipped, and the floor is computed as before.
  * The record lists `unpriced` (key, v_LP). The budget closes as "enumerated without pricing (--m1-pass2 off:
    N layouts ...)" unless the gap itself closes.
  * Stage m1 with `--m1-pass2 off` skips the warm pricing (record `m1_warm_skipped`) and the smoke acceptance
    (which evaluates every layout).
  * It runs even when m1 has a `stage_done` record. It is an explicit resume pass; without this, the plan's M4
    command, which has no `--redo`, would have been skipped by batch 2's `stage_done`. Its `stage_done` carries
    `m1_pass2 = off`.
  * K3.1: `strict_scenarios=True` with `scenarios=` (`price_layout`, `_price_plan`, the parallel waves, and
    `SitingCertifier.price`) skips an uncached cell outside the filter. There is no solve and the bound stays
    `lb0`, i.e. the LP `Qs`.
    * The result is `UNRESOLVED` with `skipped`. Its `lower` enters the floor (valid), and its `lshaped` /
      `lifted` cuts are at least LP-valued (valid).
    * Without the switch, such cells are still solved (old behaviour). Test: `n_solves == len(cells)`.
  * `ilp_params`: solves run on `evaluator.derive(params=...)`. The params enter every cache key, so these are new
    rows by design.
    * `parse_ilp_params` refuses Threads / TimeLimit / BestBdStop.
    * `parse_cells` takes `LOC:s`, `LOC:0-5`, `LOC:2+5` or `KEY@s`. `cells_for_layout` maps cells to a layout.
    * The `--cells` / `--ilp-params` / `--warm-tier` CLI flags of `price-list` belong to the r7_search lane. They
      should call `cert.price(lay, full=True, scenarios=cells_for_layout(...), strict_scenarios=True,
      warm_tier=..., ilp_params=...)`.
  * `derive` no longer inherits the `_open_sites_sibling` / `_params_siblings` caches of its parent. Before, a
    written-target or no-radius sibling derived after the parent's open-sites sibling existed would have priced
    open_sites on the parent's settings.
  * Cached siblings now follow the parent's `wall` and `verify_checked_starts` on every use. Before, a sibling
    kept the wall of the certifier that created it.
* **Change 6, verification of the MIP start** (`LowerLevelEvaluator.verify_checked_starts`, CLI
  `--verify-start {always,unchecked}`, default `always`).
  * With `unchecked`, a start that already passed `check` is passed to `run_ilp_case` with `verify_start=False`.
    That is a clean rule start (the default schedule with no family reported, or a returned fallback variant) or
    a checked warm schedule.
  * Not in any key or md5. The row records `verify_start: false` (only then). `mip_start_accepted` then comes
    from the first incumbent, as `ilp.py` already does.
  * Production lanes must pass `--verify-start unchecked` (the lane writer of change 9 adds it).
* **Resume validity.**
  * `instance_md5` 815886906f1a6cc2e6437e6de890f891 and `config_md5` 8c9cfcddf7846e6b36ee0d2a72027769,
    recomputed with the new code and the production flags, equal the batch-2 records. Nothing new enters
    `instance_md5`, `config_md5`, the pool signature or a cache key, except `--ilp-params` rows, which are new by
    design. So `outputs/r7_siting` resumes as it is.
  * r5_manhattan pool signature through the r7 path: `ed744dafc64e8f7e7384606bc0fd5c42` (both targets).
* **Laptop checks** (nice -n 15, Threads 1; toy, reduced-6 and dry runs only; no ssh).
  * Suites `test_r7_siting.py`, `test_r7_search.py`, `test_bilevel.py`, `test_o2_benders.py`, `test_r7_replan.py`:
    all pass, 1 skipped (the opt-in reproduction), 8.1 min. `R7_REPRO=1 ... -k reproduced`: pass.
  * Batch-2 snapshot dry run (no template, LP or ILP; cover rows off): restore gives 65 LP layouts, 220 price
    records, UB 1347.61.
    * Injected `price_open` at D29 = LP x 1.04 (1075.45) and D30 = 1257.21 give UB 1075.45, `best_tier`
      open_sites, D29 not in `priced`, floor 1034.0855 unchanged.
    * M4 pass 1 then needs no LP: 81 layouts envelope-pruned.
    * 7 B3:C2 layouts stay unpriced below UB - tol: D29, D28, D34, D33, D37, D23, D24. D30 and D38 are priced.
    * Without the injected UB, 26 B2 layouts would need an LP. So M4 is LP-free only while the best V_open stays
      below about 1176 (K2.4).
  * Reduced-6 resume smoke (lattice candidates via a missing `--dot-csv`). All 6 DOT candidates of
    `--reduced 6` are terminal-infeasible at one site under the radius, so the DOT subset has no feasible m = 1
    layout.
    * Ran feas + rootlp, location LPs, open-sites pricing of D06:SC:B3:C2 (V_open 1136.09; 12 rows with
      `verify_start: false`), then `--stage m1 --m1-pass2 off --max-escalations 0`.
    * Result: 0 ILP and 0 LP solves, 9 smaller sizes envelope-pruned, 3 B3:C2 layouts unpriced, LB = floor
      1093.50.
    * That floor equals the floor before the resume, with or without the `price_open` record. UB 1136.09 is
      `best_tier` open_sites. Gap 3.7 % at 1 %.
    * A no-UB run of the same pass spent more than 1.5 h on one LP of a small layout (killed). That is the same
      M4 caveat: the UB must come first.
    * Reference: a full m1 run (`--redo`, pricing on) from the same state certifies V* in
      [1111.15, 1120.81] (D06:SC:B3:C2, gap 0.86 % at 1 %). This is consistent with the resume pair
      [1093.50, 1136.09].
    * There, the all-candidates 30 s pricing of D06 first gave 1145.20, above V_open 1136.09: at short limits the
      open-sites follower finds the better schedule.

#### Drivers lane: changes 2, 3, 7, 8, 9 (with K2 / K3)

Files: `experiments/r7_search.py`, the comparison / restricted / analyse paths of `experiments/r7_siting.py`,
`experiments/r7_gate.py`, `deploy/aws/r7_prod_check.sh`, new `tests/test_r7_replan_drivers.py` (5 tests), new
`outputs/cloud_lanes_siting_prod/lanes_r2.txt` / `.json` and `lanes_r2_tier2.txt` / `.json`. `lanes.txt` / `.json` are
unchanged (md5 3016eb45... / 1254cdda...). E2 equations, `benders.py` and `bilevel.py` unchanged. Every new switch
defaults to the old behaviour; only the r2 lanes pass them. `--tol-rel 0.01` in every lane; the analyse stage reports
the open-sites gap with tol 0 (K2.2).

* **Change 2, `price-list --tier open_sites`.** Full pricing on the open-sites library (`price_open` records, no cut,
  never `priced`). A layout with a final open-sites pricing (PRICED / INFEASIBLE, rows at least at the asked limit) is
  not priced again (resume = 0 solves). The list rule `--layouts m1-lp-order --lp-order-below 1075` takes every m = 1
  layout with a known all-candidates lower bound (LP / `lp_pruned` envelope / all-candidates pricing; `m1_lower_table`),
  lowest first. `--extend-below-ub on` (M1-rest, merged into M1 since there is no C0) then prices the next layouts in
  that order while their lower bound is below the best open-sites value at m = 1, with tol 0, so that the open-sites
  certificate can be complete (K2.2, K2.4). On the batch-2 snapshot the rule gives exactly the plan's 12 (D29 ... D22;
  D30 / D38 enter at their priced lower 1055.39 / 1059.87). The next ones are D31, D19, D18, D16, D26, D07, ...
* **`--cover-rows off`** (new, list-pricing lanes M1 / M3 / M5 only). The certifier is built without cover rows, so no
  all-candidates template is built at start-up; that is about 0.4 h per lane at N = 59 (K5). The master bound is
  weaker, but `restore_prior_lb` keeps the m1 certificate in `budget_result`.
* **Change 5 CLI** (core lane's functions): `--cells` (strict, K3.1), `--warm-tier open_sites`, `--ilp-params` on
  `price-list --tier all_candidates`; with `--tier open_sites` they are refused. `--time-limit-many-sites K:SEC`
  (shared parser) gives layouts with K or more sites their own limit (5:900, re-plan section 3).
* **Change 3, `--stage import-records --from DIR`.** Appends the `price_open` / `price` records with this
  `instance_md5`. Each record carries `import_id` = md5 of the source record, so a second import appends nothing.
  `budget_result` / `final_bound` / `stage_done` and every other kind stay out (K3.4). The stage also appends the
  `cache/index.jsonl` rows whose key is absent, copies their schedule files and rewrites `schedule_path`. It is kept
  and tested, but no lane uses it (there is no C0).
* **Change 7, `--price-tier {all_candidates,open_sites}`** (pairs, m3, roles, oos, noradius in `r7_search.py`;
  comparison, restricted in `r7_siting.py`).
  * Open-sites pricing is always full (K2.7: a bound-stopped open-sites pricing proves nothing).
  * Every all-candidates lower bound comes only from envelope / LP / an all-candidates pricing
    (`all_candidates_lower`; out-of-menu layouts have no envelope). Open-sites ILP bounds are kept as `lower_open` /
    `lb_open` (also in `list_price` of `--evaluator out|noradius`).
  * Comparison rows carry `V` = UB_rule, `LB_rule`, `lb_open`, `tier`. T2 then gives the regret interval
    [LB_rule - UB*_m, UB_rule - LB*_m], and the paired CIs compare open-sites values of the row and of the best layout
    (none when the best layout has no open-sites pricing).
  * Restricted: the incumbent may come from `priced_open`, and the proposal is priced open_sites. Its LB stays the
    master / prior certificate.
  * Pairs / m3 / roles: the role row's V values are open-sites only (one follower on both sides of `price_of_S` /
    `price_of_hub`) with an all-candidates `*_lower` column. m1_rank, best@mK, best_with_sites and size targets read
    the open-sites values only under `--price-tier open_sites`.
  * oos: held-out and in-sample both on the open-sites siblings (V_out - V_in under one follower). noradius:
    open_sites with radius against open_sites without radius, warm from the radius schedules, `exact` only when both
    sides have 12 OPTIMAL cells (K5). The open-sites libraries are per layout, so no template eviction is needed.
* **Change 8, analyse `m1_dual_statement`** (record and RESULTS.md section).
  * All-candidates follower: V*_1 in [last m1 LB (floor), best UB of either tier]. It lists the locations whose best
    known lower bound is below UB (tol 0), plus a count of layouts without any bound.
  * Open-sites follower (tol 0): UB_open, and LB_open = min over the admissible m = 1 layouts of max(lower,
    `lower_open`). A layout counts as infeasible when it is a skip-list location or priced INFEASIBLE; an open-sites
    INFEASIBLE never claims all-candidates infeasibility. It also reports the gap. The certificate is `complete` only
    when no layout below UB_open is left without an open-sites pricing and none is without a bound.
  * It shows the M6 record and an open-sites ranking table.
  * Other tables: T1 gains a "UB tier" column, T3 a tier, T4b gives the open-sites role rows, T6 a tier. The
    epsilon_1 line falls back to the open-sites gap of an open-sites incumbent (labelled). The near-tie line marks
    open-sites values.
  * Fixed in the reduced-6 smoke: the open-sites near-tie label had crashed analyse (the `map_data.csv` step).
* **M6, `--stage ub-check`** (`r7_search.py`, `--layouts best@m1`). It calls `benders.ub_check_all_candidates`
  directly, with no certifier and `--max-templates 2`. It emits `ub_check_all_candidates` (`source = check`,
  `V_checked`, `V_open`, `same_value`) and skips a layout already checked ok with the same V_open.
* **Change 9, lanes.**
  * Lanes are written with `r7_search.py --write-lanes --lanes-plan r2`. Names carry the prefix `r2_` / `r2t2_`,
    because the status files share LANES_DIR with `lanes.txt`. Each file is one chain and starts with its gate.
  * `r7_gate.py --cost-dir outputs/r7_siting` writes a cost row ("every lane writes cost rows"). The gate has 18 new
    markers.
  * Every pricing lane passes `--verify-start unchecked`.
  * Batch 2b:
    * r2_m1_ub: 12 threads, 4 x 3 pricing, 600 s, wall 6.
    * r2_m3probe_a, then r2_m3probe_b: D29 s5 + s2, all_candidates, warm from open_sites, 1,200 s, 2 x 4 (K3.6);
      variant b adds `Method=2`.
    * r2_m4: `--m1-pass2 off --max-escalations 0`, 3 x 3 LPs in case the UB is above about 1176 (K2.4).
    * r2_m6: 3 threads.
  * Batches 4-6 pass `--price-tier open_sites --time-limit 600 --time-limit-many-sites 5:900` with the re-plan walls
    (pairs 4, m3 1, roles 2.5, comparison 2, restricted 1, oos 1, noradius 2). noradius now runs at 4 x 3, since no
    templates are resident.
  * Tier 2 (`lanes_r2_tier2.txt`) is not chained: r2t2_m5 (D29 / D28 / D34 s0-5, 1,200 s, 2 x 4; regenerate with
    `--ilp-params Method=2` if variant b wins), then r2t2_m4. Start it by hand only if M3 shows a mean lift >= 1 %.
  * `r7_prod_check.sh`: 69 markers (27 new). It needs all six lane files with their gates first. It refuses r2
    pricing lanes without `--tol-rel 0.01` / `--verify-start unchecked`, batch 4-6 lanes without open_sites, and lane
    names shared with `lanes.txt`. Negative cases were checked on a doctored copy.
* **Hours and USD** (r7i.4xlarge, 1.0584 USD/h):

  | Block | Hours | USD | Range |
  |---|---|---|---|
  | Batch 2b (gate, M1 + M1-rest, M3 a / b, M4, M6) | 4.86 | 5.1 | 3.25-8.5 h |
  | Batch 4 | 6.8 | 7.2 | |
  | Batch 5 | 3.2 | 3.4 | |
  | Batch 6 | 1.7 | 1.8 | |
  | **lanes_r2 total** | **16.6** | **17.5** | 12.8-24.1 h = 13.6-25.5 USD |
  | Tier 2 | 3.7 | 3.9 | |

  * Batches 4-6 equal the re-plan's 11.7 h, including the 10 % contingency.
  * M1 central is 3.3 h (2.0-6.5): 144 cells x about 300 s / 4 workers, plus the extension. Without C0 this is about
    2.6 h more than K6's post-batch-3 Tier 1 (2.2 h).
  * Study total: about 33.2 spent + 13.2 for the rest of batch 3 + 17.5 = **about 64 USD**, or 68 with Tier 2. That
    is all in October, so about 14 (18) USD over the 50 USD/month line.
* **Laptop checks** (nice -n 15, Threads 1; toy, reduced-6 and dry runs only; no ssh).
  * Suites `test_r7_siting.py`, `test_r7_search.py`, `test_bilevel.py`, `test_o2_benders.py`, `test_r7_replan.py`,
    `test_r7_replan_drivers.py`: all pass, 1 skipped, 9.9 min. `R7_REPRO=1 ... -k reproduced`: pass.
  * r5_manhattan pool signature through the r7 path: ed744dafc64e8f7e7384606bc0fd5c42 (both targets).
  * Toy:
    * open-sites price-list: no new cut, re-run 0 new cache rows.
    * Open-sites certificate equals the exhaustive open-sites optimum (complete, gap 0).
    * All budget_results hold V*.
    * Every comparison regret interval holds the exhaustive regret.
    * import-records gives the same UB and only cache hits.
    * Probe: n_solves = 1 with the other cell skipped; the `Method=2` row is new.
    * ub-check: ok and V_checked = V_open.
  * Batch-2 snapshot copy, dry runs of every r2 lane command (no solve):
    * the records are visible, so `instance_md5` matches;
    * M1 list = the plan's 12, extension D31, D19, D18, D16, ...;
    * probe plan D29 with `Method=2`; M4 plan; M6 resolves best@m1 (D30 today);
    * pairs seeds D30+D38, D09+D38, D28+D29 (m1_top2) and coverage complements; comparison / restricted / oos /
      noradius plans.
  * Reduced-6 resume (core lane's lattice state, `price_open` removed, 30 s limits) ran M1 -> M3a -> M3b -> M4 -> M6 ->
    analyse -> report:
    * M1: D06 from cache (1136.09), the extension priced D03 (1147.06) and D05 (1160.38), 12 solves each, and stopped
      with the list exhausted. The re-run resumed everything.
    * M3a / M3b: 2 solves each, 10 cells skipped, warm_parent starts, check ok. The floor rose from 1093.50 to
      1094.61, then 1094.91.
    * M4: 0 ILP, 0 LP, 9 envelope prunes, LB 1094.91, UB 1136.09 (open_sites).
    * M6: 12 / 12 cells ok, V_checked = V_open.
    * Analyse: all-candidates [1094.91, 1136.09] (3.62 %), 3 locations not excluded; open-sites [1109.42, 1136.09]
      (2.35 %, complete). The open-sites gap is the open-sites ILP gap at 30 s, not zero.
  * Analyse on a copy of the batch-2 snapshot (no solve):
    * As the records stand: all-candidates [1034.09, 1347.61] (23.3 %), 23 locations not excluded, no open-sites
      value.
    * With injected `price_open` records (D29 / D28 / D34 at LP x 1.04, D30 1257.21): [1034.09, 1075.45], 3.85 %,
      `UB_tier` open_sites, 12 locations not excluded (D29 ... D22). The open-sites certificate is incomplete: it
      lists the 8 B3:C2 layouts still to price, D33 ... D22.
    * In both cases it reports 27 layouts without any bound. These are the smaller sizes that batch 2 neither LP-solved
      nor envelope-pruned (no `lp_pruned` record). M4 writes their envelope records once UB_open < about 1176 (K2.4),
      so **analyse states the m = 1 pair only after M4**.
  * `outputs/r7_siting_probe/upload/r7_code_r2.zip`: the 10:54 selection re-globbed (109 files), plus the four r2 lane
    files and both re-plan test files. All files are md5-identical to the tree, 0 CJK, no secrets. Unpacked, it passes
    `r7_prod_check.sh --no-probe` (69 markers) and `r7_gate.py` (35 markers). It must be rebuilt if the core lane edits
    again.
  * CJK scan of every edited file: clean.

#### Review fixes of the r2 code and lanes (validity and end-to-end reviews)

Both reviews found no blocker or major issue and no validity defect. Every minor finding was applied as below. No
cache key, `CACHE_VERSION`, `pool_signature`, instance_md5 or config_md5 changed, so the records of batches 1-3 stay
valid and `outputs/r7_siting` resumes. Settings: `--tol-rel 0.01` throughout; analyse reports the open-sites gap
with tol = 0.

* **`m1_lower_table` docstring** (doc only, no behaviour change): only two things set `lower = inf`: a
  terminal-infeasible skip-list location, or an all-candidates `price` record with status INFEASIBLE. An open-sites
  INFEASIBLE sets only `infeasible_open`. It never makes an all-candidates claim.
* **M4 record labels** (`benders.py`, labels only, no bound changes). `n_unpriced_with_open_price` now counts only
  `priced_open` entries that are PRICED and have a value; a new helper `_n_priced_on_open` does the count. The close
  reason now says "... not priced on the all-candidates tier (k of them priced on open_sites)".
* **`noradius_evaluator`** now copies `verify_checked_starts` from `ctx.ev`, so `--verify-start unchecked` also
  reaches the no-radius side and its open-sites sibling. This setting is not in the cache key, so time is the only
  effect.
* **Lane order (`lanes_r2.txt`)**. The chain is now gate -> M1 -> M4 -> M6 -> batch 4-6. Both M3 probes hang off M6
  as a side branch (`after = r2_m6`), and so does `r2_b4_pairs`.
  * A failed probe now blocks nothing.
  * The official m = 1 pair is no longer delayed by about 0.86 h. K2.6 says M3 moves the floor by 0, and M4 now runs
    before the probes, so its floor cannot depend on them.
  * Each probe takes 8 threads and the dispatcher starts lanes in file order, so the probes run one at a time before
    batch 4.
* **Cover rows**. `--cover-rows` moved from `r7_search.py` into `r7_siting.build_parser`, so both scripts accept it.
  The default is `on`, the old behaviour. Choices per lane:
  * Off for `r2_b4_m3` (pricing only, `--m3-screen 0`) and `r2_b5_comparison` (pricing only, `restore_prior_lb`).
    These lanes no longer build the 12 all-candidates templates (about 0.2-0.4 h and about 41 GB each). The master
    bound is weaker, which is valid, and the prior LBs are restored, so no reported LB falls.
  * Kept for `r2_b4_pairs` and `r2_b4_roles` (the subset-LP screens need the templates) and for `r2_b5_restricted`
    (its master bound inside the DOT set is a reported number).
  * Each of these three lanes now has a 0.3 h (0.2-0.4) set-up term in `R2_HOURS`. Batches 4-6 rise from 11.7 h to
    12.6 h, and the total from about 16.6 h = 17.5 USD to about 17.5 h = 18.5 USD (range 13.4-25.3 h). Tier 2 is
    unchanged at 3.7 h = 3.9 USD.
* **Tier 2 decision as a record**. A `--cells` price-list run now ends with a `probe_summary` record, and `r7_search.py
  --stage report` shows the same table. The record is reporting only: nothing in it enters a bound.
  * One row per cell and variant (the variant is labelled by its `ilp_params`), with LP `Qs`, the ILP OPEX bound
    (`max(Qs, bound - C_setup)`, as the pricing uses), lift %, status, node count, runtime and time limit.
  * Per variant: the mean lift.
  * The verdict: Tier 2 runs only if the better variant has a mean lift of at least 1 % and every one of its cells ran
    with a limit of at least 1,200 s. If the better variant is Method 2, the verdict also gives the command to
    regenerate the lanes.
  * The probe rows now also carry `node_count` and `build_time_s` (`_WARM_ROW_KEYS`, only for warm-tier pricing, so
    the older families are unchanged).
  * The solver wrapper does not record the root LP time, so the summary says so.
  * Not done: the optional per-scenario max over several all-candidates price records of one layout on restore. M4 now
    runs before the probes, and `m1_lower_table` already takes the max over all records.
* **Dual statement**. When no layout gives an open-sites LB, `argmin` is None and RESULTS.md says "LB unknown: N
  layouts without any bound". It no longer names a layout.
* **Upload timing** (lane header): run `sync_up` / unzip `r7_code_r2.zip` only after the 12 `b3_rootlp` lanes are done.
* `outputs/r7_siting_probe/upload/r7_code_r2.zip` was rebuilt from the same file selection.
* New tests in `tests/test_r7_replan_drivers.py`: probe-summary lift and verdict, the `_n_priced_on_open` label, the
  LB-unknown line, and the no-radius evaluator with `--verify-start`. `test_r2_lanes_plan` now checks the new order,
  the dependencies, the cover-row choices, the upload line and 12.6 h for batches 4-6. The smoke probe test checks the
  `probe_summary` record.

#### Gate of the r2 code before upload (2026-10-23, about 05:35 UTC)

* **Laptop checks** (nice -n 15, Threads 1; no ssh, nothing uploaded): full suite 482 passed, 1 skipped (the opt-in
  reproduction), 0 failed, 15.6 min; `R7_REPRO=1 ... -k reproduced` 1 passed (149 keys); r5_manhattan pool signature
  through the r7 path `ed744dafc64e8f7e7384606bc0fd5c42` (both targets); production `instance_md5`
  815886906f1a6cc2e6437e6de890f891 and `config_md5` 8c9cfcddf7846e6b36ee0d2a72027769 equal the batch-2 records, so
  `outputs/r7_siting` resumes. `--tol-rel 0.01` throughout; analyse reports the open-sites gap with tol = 0.
* **`outputs/r7_siting_probe/upload/r7_code.zip` rebuilt** from the current tree with the r2 selection (109 files,
  md5 `9ced13a0b5e3e7d60d04b7612e402307`): file contents equal to `r7_code_r2.zip`, all md5-identical to the tree,
  0 CJK, no secrets, `aws_env*.sh` and `README_AWS.md` left out. The unzipped copy passes `r7_prod_check.sh
  --no-probe` (69 markers), `r7_gate.py` (35 markers) and a `run_lanes.sh start lanes_r2.txt --dry-run`.
* **Server order**: batch 3 done (12 `b3_rootlp` lanes) -> `run_lanes.sh stop all` (old dispatcher; only after every
  b3 lane is done, and before the unzip because bash reads `run_lanes.sh` lazily) -> `unzip -o r7_code.zip` ->
  `r7_prod_check.sh --no-probe` -> `run_lanes.sh start lanes_r2.txt --max-threads 12`. Exact commands:
  `notes/siting_production_replan_m1.md`, "Re-plan code status (2026-10-23)".

### R7 production analysis on the laptop (2026-10-24)

* Ran `r7_siting.py --stage analyse` and `r7_search.py --stage report` on the downloaded records in
  `ebike_swap_sim/outputs/r7_prod_final/r7_siting`. Flags: the production ones (`--family manhattan_dot --scenarios
  12 --approach-radius 14 --tol-rel 0.01 --tol-abs 1 --restrict dot --held-out`) with 1-thread worker settings. No
  solve was run. `cost.jsonl` is unchanged (md5 1d885b17...): analyse and report are unbilled stages.
* Analyse appended its own records 1008-1011 (`plan`, `m1_dual_statement`, 2 x `role_table`).
* No analysis, report or map script was edited.
* New figure script `outputs/r7_prod_final/figs/final_map.py`. It shows the rule layouts, the 23 feasible single
  sites and the pilot sites, which the standard `siting_map.py` does not mark. It imports `nta_polygons` from
  `siting_map.py`.
* Final write-up: `outputs/r7_prod_final/RESULTS_final.md`.
* Non-blocking reporting issues, left as they are and documented in RESULTS_final caveats:
  * `RESULTS.md` T4 (all-candidates role table) names D30 as "best" at every m, because D30 is the only layout priced
    on that tier. T4b is the correct table.
  * The m = 2 incumbent D07+D45 improved from 718.91 to 716.85 through the oos stage's in-sample warm re-solve
    (cache rows 409-410). No `price_open` record was written, so `budget_result` still shows 718.91.
  * All `oos_result` records are SKIPPED_BUDGET (V_out null). The weekday held-out values were recomputed from the
    cache rows.

## R8 fifteen-site study (2026-10-28)

### L3 map lane: `fig_map15` and the 15-row companion table (2026-10-28)

* Prototype `scratchpad/map15/map15_prototype.py` moved into `paper_itsc/figs/src/make_figs.py` as
  `fig_map15(layout_json, site_stats_csv)` with the layers of `siting15_design.md` section 6 (NTA land, DOHMH restaurant
  density, cached OSM major streets, hatched land beyond 14 blocks of every site, unchosen candidates, six entry depots,
  15 numbered sites with class shapes, marker size = swaps per evening, red ring = DOT programme site, leader lines for
  close pairs, scale bar, north arrow, legend). Companion table emitter `site_table15` writes `figs/site_table.tex`.
  No package file was touched. Input contract (layout.json / site_stats.csv schemas) is in `siting15_design.md` 6.1 and
  in the docstring block above `LAYOUT15_SCHEMA` in `make_figs.py`; the driver lane logs exactly those fields.
* OSM extract cached as `data/raw/osm_major_roads_manhattan.json` (thinned from the 5.3 MB Overpass answer to 1.1 MB:
  id, highway, name, rounded geometry; licence and timestamp kept). Credit "streets (c) OpenStreetMap contributors
  (ODbL)" is printed on the figure and must stay in the caption.
* Site numbers are derived (south -> north by the along-avenue coordinate), not logged, so map and table always agree.
* Label placement is automatic (collision-aware greedy; numbers before depot names; close pairs < 300 m get leaders;
  leaders never cross another marker) because the real layout is unknown until the run.
* Density ramp lightened (#f4f3f0 -> #c8822f) so the blue markers with their white rings read in greyscale; the earlier
  #a85c14 end had the same luminance as the marker blue.
* Table CIs are shown as +- half-widths (the bracketed form was 74 pt too wide for the IEEEtran text width at
  scriptsize); site names longer than 30 characters are cut with an ellipsis.
* DEMO: `make_figs.py map15_demo` renders a CSCD-15 rule layout (weights = restaurants within 14 blocks, a stand-in for
  the scenario demand) with synthetic statistics, stamped DEMO on the map, in the legend title and in the table caption;
  inputs in `figs/map15_demo/`. The published `figs/fig_map15.*` and `figs/site_table.tex` are that DEMO until the R8
  driver writes `figs/map15/`. A CSAV-15 variant was rendered to the scratchpad to check a spread layout (0 % uncovered).
* Render time 1.7 s per map on the laptop; PDF 0.73 MB (density layer rasterised at 300 dpi, streets vector).

### L1 union (bike-class) arc library (lane L1, 2026-10-28)

Implements `notes/siting15_design.md` sections 2-3 as corrected by section 12 (critic C2: reachability in one
time-ordered bitmask sweep, never a per-class DFS).  E2 equations unchanged; the default path is byte-identical
(no new key in `DEFAULT_OPTIONS`, no instance JSON, pruning signature or cache key changes; `R7_REPRO=1 ...
-k reproduced` passes, 149 keys).  Code: `ebike_swap_sim/arcs.py` (new `UnionArcLibrary`, `build_union_arcs`,
`reach_sweep`, `coreach_sweep`, `library_mode`; `_template_specs` / `_delivery_specs` became list wrappers of
generators with the same order), `ebike_swap_sim/aggregate.py` (fast path `_init_union`), `ebike_swap_sim/evaluate.py`
(two guarded lines in `metric_pack`), `tests/test_union_arcs.py` (38 tests).  English only.

Decisions:
- Switch: arc-builder option `library_mode` (`'per_bike'` default when absent, `'union'`), read by `build_arcs`
  from `inst.options` or a keyword override (`build_arcs(inst, library_mode='union', **pruning)`); `lib.options`
  of a union library carries the key so that `ilp`'s co-located rebuild stays in union mode.  The key is NOT in
  `DEFAULT_OPTIONS` and NOT in `bilevel.pruning_signature`, so older families' keys are untouched; the new
  `manhattan15` family may set it on its saved scenario instances (then `LowerLevelEvaluator.layout_pair` on the
  open-sites tier builds union libraries without any change in `bilevel.py`).
- Storage: the bike-independent template (wait, move, deliver, swap, term specs in the generator's order) as numpy
  columns (kind int8, src/dst int32 dense state ids `nidx[v]*(H+2)*(L+1) + t*(L+1) + q`, l/u/g int32, d_km/theta
  float64, order/facility indices int32) emitted block-wise by `_union_columns` (no per-spec Python object), CSR by
  tail state (template order within a state) for `find` / `out_arcs`.  Bikes with the same `(v0, q0)` form a class
  (at most depots x levels); per class a rank/select bit vector (`_BitRank`, about 1 MB per million specs) gives
  the per-bike view; ids are `offset_k + rank_c(spec)`, i.e. IDENTICAL to `build_arcs` ids (bike after bike,
  template order, unreachable specs skipped under `reachable_pruning`), so schedules, `evaluate.check` / `cost` /
  `metric_pack`, `portable_schedule`, MIP starts and `costs.check_lib_prices` (`lib._deliv` is a lazy mapping) work
  unchanged.  `lib.arcs` is a lazy sequence (`len`, `[id]`, iteration).
- Reachability: `reach_sweep` processes the arcs by tail time level with one `uint64` word per 64 classes
  (`np.bitwise_or.at`), zero-duration arcs iterated to a fixpoint within a level; equals `_reachable` (DFS) for
  every class (asserted on every toy option set including a zero-duration fixture and on both families).  Under
  `reachable_pruning` a light first pass (src/dst/kind only) feeds the sweep and the stored columns keep only the
  specs reachable by at least one class (16 % at 48 riders; views and ids unchanged because unreachable specs are
  in no bike's set).  Without pruning all specs are stored (ids need them).
- Aggregation: `AggregatedNetwork` on a union library builds the same network as on the per-bike library (union
  order = first-copy-wins over bikes, each in template order; classes closed by construction; co-reachability by
  `coreach_sweep`; same `ub`, `term_ub`, `n_dropped`, commodities; `arcs` lazy, `arc_ids` ranges).  Gurobi model
  fingerprints of the aggregated ILP are identical on both families; per-bike ILP (`aggregate=False`) also works
  (iterates the lazy `lib.arcs`).
- `evaluate.metric_pack`: the unserved-order index `need[(k, v, t)]` is taken from `lib.delivery_need(...)` when
  the library has it (vectorised per class) instead of `lib.delivery_arcs(i)` over all bikes; output identical
  (asserted), 159 s -> 2.8 s at 48 riders.  Per-bike libraries take the old branch.

Measured on the laptop (nice -n 15, Threads 1, numpy 1.26, Python 3.12; `outputs/union_library/*.json` and the
session scratchpad `union/m_*.json`):
- reduced-6 `manhattan_dot`, seed 0, 8 riders / 40 orders, two SC:B3:C2 sites, open-sites tier, radius 14: template
  1.00 M specs, 160 k stored (reachable by some class), 1.22 M per-bike arcs; union build 0.13 s (per-bike 2.4 s),
  arrays 10 MB (per-bike library about 440 MB RSS); r2 baseline 18 ms, check 4 ms, aggregated network 10 ms
  (per-bike path 0.9 s), 92,383 aggregated arcs; arcs, schedules, costs, check reports, metric packs and the
  aggregated model fingerprint identical; a 60 s aggregated solve gives the same incumbent and bound (1178.54 /
  1098.49).
- `r5_manhattan`, seed 0, 8 riders, M08:SC:2:1 on the open-sites tier: 1.12 M template specs, 184 k stored, 1.43 M
  per-bike arcs; union 0.14 s vs per-bike 2.9 s; identical as above.
- reduced-6 `manhattan_dot` at 48 riders / 240 orders (instance 376 nodes, 141 k routes, built once in 269 s and
  saved per critic C3): 15.8 M template specs, 2.46 M stored, 109 M virtual per-bike arcs, 28 classes; union build
  3.3-3.4 s (light pass 1.1, sweep 0.8, compacted pass 1.0, index 0.4, gbar 0.1), arrays 142 MB, process RSS
  +0.3 GB for a second build (+0.95 GB for the first, allocator cache included), peak process RSS 1.3-1.5 GB with
  the instance; r2 baseline 0.09 s (198 of 240 orders unserved under this two-site layout), check 0.02 s,
  metric_pack 2.8 s; cell = 3.5 s on the laptop, i.e. about 9 s with the 2.5x server factor, under the 45 s / 4 GB
  gates.  The per-bike library for this cell would hold 109 M `Arc` objects (about 25 GB) and was not built.
- synthetic 48-rider toy grid (`usd4h` knobs, 240 orders, 26 nodes): 726 k specs, 34.7 M virtual arcs, build 0.3 s,
  cell 0.4 s, peak RSS 248 MB; the 8-rider slice has the same template and identical per-bike views.

Open points for lane L2 (driver): the union library is read-only after the build and must be built inside each
worker process (fork after the scenario instances are loaded; never pickle a library); `lib.arcs_of(k)`,
`lib.arcs` iteration and `lib.delivery_arcs(i)` with `k=None` materialise `Arc` objects lazily (O(bikes x specs)),
so avoid them in cells; the all-candidates template tier (`evaluator.template(s)`, `subset_library`) works through
the generic interface but is slow on a union template and stays out of the k15 stage (critic C5).

### L2 driver lane: `experiments/r8_k15.py`, exactly-k search, per-site metrics (lane L2, 2026-10-28)

Implements `notes/siting15_design.md` sections 3-6 as corrected by section 12 (C1 process pool, C2 union library,
C3 instances built once and saved, C4 `n_bikes` gives the orders, C5 open-sites tier only with the 45 s / 4 GB /
3-swaps gates, C6 ratio-with-gaps validation).  E2 equations unchanged; no cache key, pruning signature or pool
signature of an older family changes (`R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced` passes; the full
suite is green).  English only.  Code: `ebike_swap_sim/sites_nyc.py` (family `manhattan15`), `ebike_swap_sim/evaluate.py`
(`site_metrics`, `metric_pack['per_site']`), `ebike_swap_sim/bilevel.py` (`SERVICE_GATE` / `service_gate`,
`ProxyScreen`, `greedy_local_search(force_k, swap_neighbourhood, min_served_share=None)`, `k_median_layout`,
`dot_first_layout`, `top_sites`, `LowerLevelEvaluator.store_external_row`, the `prefetch` hook), `experiments/common.py`
(`unservable_orders` reads the id index), `experiments/r8_k15.py` (new driver), `tests/test_r8_k15.py` (11 tests + one
`R8_HEAVY=1` probe).

Decisions:
- Family `manhattan15` = the `manhattan_dot` data (DOT candidates, six entry depots, eBaaS energy, TOU tariff, R5
  profile, `max_pair_km` 2 km, reduced SC menu) with `n_bikes = 48`; the stratified levels 1.0 / 1.25 / 1.5 give
  192 / 240 / 288 orders (C4).  A new family name, so every `manhattan_dot` key is untouched.
- Stage `instances` builds the 12 in-sample + 12 held-out scenario instances (and the 16-rider validation
  instances) once, one process per scenario, with `Instance.save` (route library included) plus a pickle twin for
  fast worker loads; `options['library_mode'] = 'union'` is set on the saved instances (L1's switch), a manifest
  with per-file signatures makes the stage resumable (C3).
- Process pool (C1): `multiprocessing` (fork where available, spawn-safe) with persistent workers that load the
  saved scenario instance from disk on first use (LRU of 2), build the layout instance and its union library,
  run the r2 rule follower through `LowerLevelEvaluator.evaluate_scenario` on a SINGLE-scenario evaluator,
  certify with `evaluate.check`, measure `site_metrics`, and return one small dict plus the portable schedule.
  The parent holds LIGHT instances (routes stripped) in an `OfflineEvaluator` that never solves: it computes the
  cache keys (identical to the worker's single-scenario key, asserted on every row), stores the rows with
  `store_external_row` (`cache/index.jsonl` + `schedules/`), and `greedy_local_search` reads them as cache hits
  after a `prefetch` of every screened layout (one pool batch per search step).  Resume = the cache.
- Exactly-k mode `force_k`: forward selection accepts the lowest-V addition at every step even when V rises
  (the greedy path gives V(k)); add / drop are disabled in the local search; the per-policy service gate is 0 for
  the simulator (served share reported on every record), 0.5 for the ILP as before; the swap neighbourhood is the
  3 nearest closed candidates of a site plus the 5 best closed candidates by the proxy; 3 layouts priced per
  step.  The proxy is library-free (p-weighted order penalty x grid distance from the restaurant to the nearest
  open swap-capable site + allocated set-up; milliseconds); the lower level alone decides acceptance.
- Warm starts / comparison rows: CSCD-k, CSTC-k (inverse-distance access weights, no isolation pricings), CSAV-k,
  k-median-k (one small MIP on the proxy objective; greedy fallback without gurobipy), DOT-first-k (pilot +
  shortlist sites by demand, filled by CSCD); restarts from the m = 2 production incumbent, from the best two
  sites (by demand weight) of CSCD-k and CSAV-k, and from empty; 'k units free' = the same search without
  `force_k` on the full menu; size polish at the best locations and fixed investment (D'Hondt by swaps per site
  within the menu, then one-for-one spare / charger transfers from the least to the most used sites); the V(k)
  path continued to k = 20 from the best found; k = 1 is the best proxy-screened singleton of the empty restart,
  and the production m = 1 / m = 2 incumbents (D23; D07 + D45) are re-priced at the new fleet as reference rows
  (12.2: every V(k) point at the same fleet and follower).
- Final stage: every layout on 12 in-sample + 12 held-out scenarios, stratified 95 % CIs (`bilevel.stratified_ci`
  on the per-scenario opex; paired regret against the best), the remove-one pass (marginal value = V without the
  site - V with it, positive = the site saves money, paired CI), per-site statistics p-weighted over the
  in-sample scenarios (swaps with CI, orders within 7 blocks = 1 km served / total, distinct riders, charger-busy
  and idle shares over 15-min periods, kWh bought, mean wait, stock-out slots); outputs `layout.json` (schema
  `map15.layout/1`) and `site_stats.csv` (exactly `SITE_STATS15_COLUMNS`) next to the records = the `fig_map15`
  input contract (section 6.1); `RESULTS.md` with the paper tables.
- Dry run (stage `dryrun`): CSCD-k on all in-sample scenarios; gates cell <= 45 s, worker RSS <= 4 GB, median
  open site >= 3 swaps per evening -> `dryrun.json` with `escalate`; the search refuses to start on a failed gate
  (`--ignore-gates` overrides); the escalation (64 riders / 320 orders) is a decision for the author, not automatic.
- Validation (stage `validate`, C6): 16 riders / 80 orders (level 1.25, seeds 0-2), 5-site layouts (the greedy
  best at that fleet under the rule follower, CSCD-5, CSAV-5), exact aggregated ILP at 1,800 s / Threads 3 in 4
  worker processes, reported as rule / incumbent ratio per cell with the MIP gap and status; no rank statistic.
- Lanes: `--write-lanes` -> `outputs/cloud_lanes_k15/lanes.txt` (+ `.json`), one chain instances -> dryrun ->
  validate -> search -> final -> report, 8 worker processes (8 threads declared), 4 x 3 threads for the ILP
  check, `--max-threads 12`, `--max-rss-gb 110`, `R7_BATCH=k15` and the instance price on every command
  (`cost.jsonl`); about 6 h = 6.4 USD before contingency (design 12.4: about 7 h = 7.5 USD).  Accepted by
  `deploy/aws/run_lanes.sh start --dry-run`.
- Fix found by the probe: `common.unservable_orders` materialised `lib.delivery_arcs(i)` over every bike (160 M
  virtual arcs at 48 riders x 15 sites: 190 s per cell); it now reads the id index `lib._deliv` (same emptiness
  test on both library kinds, asserted in the tests): the cell is 3 s.

Measured on the laptop (nice -n 15, Threads 1):
- toy smoke of every stage (`--smoke --stage all`, 4 candidates, k = 2, 2 + 2 scenarios, 2 worker processes):
  1.5-2.2 s wall, 74 cells, 0.07 GB per worker; the exactly-k search reaches the exhaustive optimum at k = 1, 2, 3
  with and without the proxy screen; the k-median equals the enumerated proxy minimum; `tests/test_r8_k15.py`
  11 passed in 9 s.
- one real cell (`manhattan15` scenario 0, 48 riders / 192 orders, CSCD-15 at SC:B3:C2, open-sites tier, radius
  14): instance build 219-240 s (343 nodes, 117 k routes, 15.5 MB JSON), union library 2.75 s (13.4 M template
  specs, 3.39 M stored, 160.9 M virtual arcs, 192 MB), rule follower + check + cost + metrics 0.24 s, cell 3.0 s
  end to end in the worker, worker RSS 1.07-1.36 GB; served 0.89, 50 swaps at the 15 sites (1-7 each, median 3
  on this level-1.0 scenario).  With the 2.5x server factor: about 8 s per cell, far under the 45 s gate; the
  median-swaps gate is the one the server dry run decides.
- full test suite: green (`tests/` in four chunks of 2.7-5.9 min; `test_r7_siting.py` 49 passed; `R7_REPRO=1 -k
  reproduced` passed).

Open points for the author: the AWS run itself (user starts the instance; about 7 h = 7.5 USD on the r7i.4xlarge,
November unless decided otherwise); the 48/240 vs 64/320 decision after the dry run; the paper lane copies
`layout.json` + `site_stats.csv` to `paper_itsc/figs/map15/` and runs `make_figs.py map15`.

### R8 fixer pass after the two reviews (2026-10-28)

Reviews: (a) library + follower reviewer (one major, six minor), (b) end-to-end and cost reviewer (seven minor).
Every blocker/major and every cheap minor was applied; nothing was skipped. E2 equations, cache keys, pruning
and pool signatures of the older families are untouched (the changes are in the R8 driver, the per-site metric
rows, one `_BitRank` guard and one `_prefetch` call).

Major (a1), `bilevel.greedy_local_search`: the `start` layout was priced without `_prefetch(evaluator, [start])`,
so on the driver's `OfflineEvaluator` (never solves in the parent) the start became an ERROR row and every restart
from a layout (m2 incumbent D07|D45, CSCD_best2, CSAV_best2, the "k units free" search, the validate-stage greedy)
silently collapsed into the singleton search from empty. Fix: `_prefetch` before `price(start)`; `stage_search`
prices every restart's start in one pool batch (`tag="starts"`) before the loop, records `start_status` per
restart and REFUSES (SystemExit, `search_blocked` record) a restart whose start step is ERROR instead of
continuing from empty. The smoke now exercises the path: smoke mode gets a two-site start (`T1|T4`) and two toy
reference layouts, and the test asserts the start step is OK for every restart and that no restart ever reads an
ERROR start. New test `test_restart_from_an_unpriced_start_is_ok_on_the_offline_evaluator` (an OfflineEvaluator
whose pricer stores single-scenario rows, as the pool does).

Minor, applied:
- `arcs._BitRank.rank(n)` / `test(n)`: guarded at `i >= n` (`rank(n)` = the count; before, `n` a multiple of 64
  indexed one word past the end, reachable through `_LazyIds` when the deliver block is the last stored block).
  Test extended with n = 64, 128.
- One in-memory cache per process: `ev_search`, `ev_out` and the validate-stage `ev_val` share `ctx.ev.cache`
  (keys differ by seed / demand hash where the scenarios differ), so a cell priced by the search is a hit for the
  final / remove-one stages and `index.jsonl` carries no duplicate rows (smoke: 74 rows, 46 distinct before; now
  every key once, asserted by the smoke test).
- `polish_sizes`: `if sw and (len(Bs) > 1 or len(Cs) > 1)` (the `and`/`or` precedence ran the D'Hondt step on an
  empty per-site table); an empty table is logged as a skipped D'Hondt step.
- `evaluate.site_metrics`: open charge-only hubs (role C) are rows too (swaps 0, riders 0), so the kWh per site
  sums to `kwh_purchased` for every layout; the R8 search is SC-only, so no R8 number changes. New test with a
  `T4:C:B0:C1` hub under the r2 follower and the exact ILP (Gurobi), kWh sum and swap sum asserted.
- Worker instance reloads: cells of a batch are now sent scenario-major with a chunk of consecutive jobs per
  worker (`chunksize = min(n_layouts, n_jobs // (4 x workers), 8)`), so a worker's LRU (`--worker-keep 2`) is hit
  by the next job; the instance-load time is logged per cell (`instance_load_s`, inside `cell_wall_s`, so the
  45 s gate still sees it) and per batch (`instance_load_s_sum`, `instance_loads`).
- 48-rider feasibility of the single sites and the pair (unverified in the review): the dry run now prices the
  reference layouts D23, D07|D45, D07, D45 and the search start on all 12 in-sample scenarios in one extra batch
  (`dryrun_refs`), echoes one `dryrun_ref` record each and stores them in `dryrun.json["reference_layouts"]`
  (status, V, served share, per-scenario statuses), so an INFEASIBLE_TERMINAL singleton is known before the
  search is paid for. `stage_search` already continues with the restarts that reached k; it now also emits
  `vk_missing` (the k values with no usable layout) and stores it in `search_summary.json` instead of leaving
  the gap silent; it still stops only when no restart reached k.
- Lanes: `outputs/cloud_lanes_k15/lanes.txt` + `lanes.json` are written to the repository path (they existed only
  in a test tmp dir); `k15_search` now waits for `k15_dryrun` only (the optional ILP check cannot block the study;
  the 12-thread budget still serialises it behind validate); accepted by `run_lanes.sh start --max-threads 12
  --dry-run`.
- `main --max-threads`: `need = max(workers if a pool stage, validate_workers x validate_threads if validate, 0)`
  (the old expression dropped the validate term whenever a pool stage was also requested).
- `--max-rss-gb` is now a machine budget: parent RSS + workers x the largest worker RSS of the previous cell
  batch (first batch: parent only); the lanes header says so, the help text too.
- Design note section 8: the 15-site row of tab:bounds is "best found, no bound (rule follower)" unless the
  optional LP lane runs; the page budget uses the built map size (7.2 x 2.74 in after the tight bounding box of
  the 7.16 x 2.7 in figure; width is scaled by `\figfile`, the height is +0.2 in against the first estimate).
- `make_figs.py --help` / an unknown name prints the figure names and exits 2 (KeyError before).

Not changed (by design): the per-worker `keep` stays 2 (12 x 0.5 GB per worker would break the 4 GB gate; the
scenario-major chunks are the fix); no LP lane added.

Checks on the laptop (nice -n 15, Threads 1): `make_figs.py map15_demo` renders fig_map15 + site_table.tex in
1.7 s; toy smoke `--smoke --stage all` rc 0 with the m2 restart, reference layouts and duplicate-free cache.
Verification pass of the fixer (2026-10-28, laptop, nice -n 15, Gurobi Threads 1, every run under 10 min): each fix
re-checked in the code; full suite green file by file (27 files, 0 failures, skips only the opt-in heavy/repro tests;
longest file test_r7_siting 240 s); `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced` passed (53 s);
`tests/test_r8_k15.py` 13 passed, 1 skipped (`R8_HEAVY`); toy smoke `--smoke --stage all` rc 0 in 2.2 s, 225 MB RSS,
cache/index.jsonl 50 rows = 50 distinct keys, every restart's start step OK (m2_incumbent, CSCD_best2, CSAV_best2,
free, extend, validate_greedy), `vk_missing` empty, four dry-run reference layouts OK; a second invocation skipped
five stages and added no cache row; `make_figs.py map15_demo` 2.0 s, site_table.tex byte-identical; `make_figs.py
--help` exits 2 with the figure list; `run_lanes.sh start --max-threads 12 --dry-run` accepts the six lanes
(k15_search after k15_dryrun). Note: `--write-lanes` always writes `outputs/cloud_lanes_k15/` and bakes `--out-dir`
into the commands, so regenerate it without `--out-dir` (as now on disk: `--out-dir outputs/r8_k15`).

### R8 gate before the server run (2026-10-28)

Gate of `siting15_design.md` section 13 (full record there). Laptop only (nice -n 15, Gurobi Threads 1, every run
under 10 min, RSS under 8 GB); nothing uploaded, the instance not touched; no package, experiment or test file changed.

Checks:
- Full suite, one pytest process per file (27 files): 535 collected = 527 passed, 8 skipped (opt-in: six r6_fill solver
  smokes, `R8_HEAVY`, `R7_REPRO`), 0 failed, 0 errors. `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced`:
  1 passed (56 s, 149 keys), so the older families' cache keys, pruning and pool signatures are unchanged.
- Lane plan `outputs/cloud_lanes_k15/lanes.txt` / `lanes.json` regenerated with `--write-lanes` into a scratch dir and
  diffed: identical apart from the scratch path line; `run_lanes.sh start ... --max-threads 12 --dry-run` on the
  unzipped copy accepts the six lanes (only `k15_instances` starts, the rest queue in the chain).

Decisions:
- New `deploy/aws/r8_prod_check.sh` (separate from `r7_prod_check.sh`, which stays byte-identical): 47 fixed-string
  markers of L1 / L2 / the fixer pass, 4 negative markers (critic C1: no `ThreadPoolExecutor`; C5: no `.template(`,
  `superset_bound`, `subset_library` in the driver), lane-plan checks (six lanes in order, `k15_search` after
  `k15_dryrun`, `manhattan15`, `R7_BATCH=k15`, `--workers 8`, `--out-dir outputs/r8_k15`, no `--n-bikes` /
  `--n-orders` (C4) / `--ignore-gates`), refusal while a `lanes_dispatch` tmux session runs (the session name is
  shared by every lane plan), optional `--smoke` (toy run of every stage with `env.sh` sourced). Exit 0 / 2 / 3 / 4;
  exits 0 and 2 (missing marker, forbidden thread pool, `--n-bikes` in the lanes) were exercised on an unzipped copy.
- `ebike_swap_sim/outputs/r8_upload/r8_code.zip`: 109 files, 1,303,490 bytes, md5 `ab8cca8a5f45166112877cd0897ba188`;
  same selection rule as `r7_code.zip` with the k15 lane plan instead of the R7 lane plans; md5-identical to the tree,
  0 CJK, no secret pattern, modes kept. No new data file: the instances are built on the server from the R7 data
  already there; the OSM extract is used only by `make_figs.py` on the laptop and is not shipped.
- Measured the largest scenario before costing (scratch probe, not a project file): level 1.5 weekend, 288 orders,
  450 nodes, 202 k routes, build 414 s laptop (17 min server at 2.5x), cells 6.7-7.9 s laptop (CSCD-15, CSAV-15,
  CSCD-20), worker RSS 1.7-2.1 GB, median open-site swaps 3 (the gate is at its threshold; served share 0.53-0.70).
- Corrected server estimate: 4.3-5.0 h + 30 % = about 5.5-6.5 h = 6-7 USD on the r7i.4xlarge on-demand (4-4.5 USD
  without the optional ILP check, `--only` without `k15_validate`); escalation to 64 / 320 adds 3-4.5 USD. Replaces
  the 7 h / 7.5 USD of design 12.4 and the lane plan's 6.0 h before contingency. Lanes run serially under the 12-thread
  budget, so the wall time is the sum of the stages. Spend goes to November unless the author decides otherwise.
- Server commands (unzip, pre-flight, start, status, cost) are in design section 13.6. Gate result: PASS.
