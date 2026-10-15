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
