# Project summary (2026-10-12): methods, results, recommended changes and iteration roadmap

## 1. What was done (methods)

**Step 1: understand and verify the documents.**
After extracting the full text of the four PDFs, the E2+Example toy example was rebuilt independently from the document rules (gurobipy), giving J = 12.5,
with the five cost components 4 + 0.1 + 0 + 6 + 2.4 matching the document; the conservation identities (23)–(25) were derived from the inventory balance (13) with sympy;
the three inventory tables (E2 Section 8, E2+Example p. 15, Battery_Swap p. 7) pass row-by-row constraint checks.
The formula audit has 24 records, **no errors found**; all are modelling choices or ambiguities, fixed as implementation decisions (`notes/DECISIONS.md`).

**Step 2: implement a general software package `ebike_swap_sim/`** (about 12,700 lines, 67 tests all passing):

| Module | Purpose |
|---|---|
| `or_instance.py` | Instance data structures (discretisation, route library, riders, orders, facilities, logistics services, grid groups), JSON I/O, toy example |
| `arcs.py` | Per-vehicle time-expanded network: wait/move/delivery/swap/terminal arcs, formulas (1)–(4), (9), with lossless pruning |
| `ilp.py` | Gurobi implementation of the full E2 model (5)–(22), (26)–(33), switches: no transfers, co-location, fixed facilities, budget, service rate, lexicographic |
| `baseline.py` | The naive policies from the proposal: nearest-feasible-rider dispatch + threshold swapping + FCFS + ASAP charging, optional reorder-point transfers |
| `evaluate.py` | Prices any solution with the same objective (26)–(32); solver-independent constraint checker; metrics |
| `generator.py` | Synthetic NYC-style instances: grid network + the proposal's three OD-generator sub-modules (time curve, demographic destinations, restaurant type) |

Key design: **the baseline and the ILP use the same discretised instance, the same arc library and the same pricing function**; every ILP solution must pass the independent checker,
and the Gurobi objective value must equal the pricing function's value; the baseline solution is also fed back to Gurobi as a MIP start as a "feasibility certificate".

**Step 3: experiments E1–E4**, then two review agents audited the code line by line against the formulas, found and fixed a fairness defect in the baseline, and the baseline was rerun on the same batch of instances.

## 2. Results

### E1 toy example (correctness benchmark)
ILP 12.5; ρ = 0 → 11.2; no transfers → 106; lexicographic → 12.5; the p. 15 inventory table and the Battery_Swap p. 7 table are both reproduced.

### E2 coordinated ILP vs naive baseline (10 vehicles, 2-hour evening peak, 3 co-located stations, 5 seeds)

| Demand multiplier | Orders | ILP cost reduction vs baseline (fixed baseline) | Before fix |
|---|---|---|---|
| ×0.75 | 22 | 4.3% ± 1.5 | 12.6% |
| ×1.0 | 30 | 29.6% ± 18.2 | 34.6% |
| ×1.5 | 45 | 38.2% ± 7.5 | 36.8% |
| Total | 15 instances | **24.0% ± 8.7** | 28.0% |

- **90% of the gap is unserved-order penalties** (P_i = 100), lateness 9%, travel 1%.
- Gain decomposition (chained): optimising only swapping/charging/transfers without touching dispatch → only 1.6%; re-timing only → 3%; **re-assigning orders → 95%**.
- In this instance family the ILP **never charges and never transfers**: 12 spare batteries are enough for 10 vehicles over 2 hours. No swap queues appear either.
- Solve size: 0.66–1.04 million binary variables, mostly optimal in 15–30 seconds; 1–4 minutes at 45 orders, 4/60 runs hit the 240-second limit (gap < 2.1%).

### E3 transfers and swap/charge separation (same total batteries and charging slots)

| Layout | ILP transfers allowed | ILP transfers forbidden | Value of transfers |
|---|---|---|---|
| (a) 3 co-located stations | 556 | 556 | 0 |
| (b) 3 swap stations + 1 charging hub | 611 | 868 | 257 |
| (c) 3 swap stations + 2 charging hubs | 654 | 908 | 254 |

- The cost of separation is small: only 55 more than co-location (40 of which is the hub's fixed cost, operations only 3–4% more), because the ILP uses 2–3 shuttle runs carrying 5–7 batteries to bring the service rate back to 97.8%.
- **Important finding**: with the end-of-horizon targets (17)(18) relaxed, the separated layouts serve all orders with **zero transfers** within the 2 hours. That is, in this short window the value of transfers comes almost entirely from the "restore full spare batteries at the end" constraint, not from genuine replenishment within the window.
- The grid-group limit never binds (peak 2.7 kW vs 6–8 kW cap), because a 0.667 kW charger takes 60 minutes to fill a battery and few batteries are returned within 2 hours.

### E4 station-sizing sensitivity (3 stations, 3 seeds)

- **Default state (initial vehicle charge 7.5–8.7/12)**: stations are not a bottleneck at all. Cost is perfectly flat beyond 2 spare batteries per station, the marginal value of charging slots and power is 0; when the ILP chooses sizes itself it buys only 1 battery per station and almost no charging slots.
- **Stressed state (initial charge 3–6/12)**: going from 1 to 2 batteries per station saves 177 (62 per battery), then flat; 1 charging slot per station suffices; the baseline needs >6 batteries per station to reach its cost knee, while the ILP's is at 2; the baseline never reaches the ILP's service rate no matter how many batteries are added.
- Conclusion: **the proposal's question "which stations queue, which stations idle" only has content in an energy-stressed state**; under default parameters all stations are idle.

### Code review conclusions

- ILP: checked line by line against (1)–(33), all correct; adversarial small instances verified (14) joint availability, (22) occupancy with σ > 1, the summation ranges of (17)/(18), terminal arcs x ≤ y, etc.
- Baseline: a high-priority fairness issue was found — the "dominance pruning" designed for the ILP (removing arcs that leave early and wait at the restaurant) made the greedy dispatcher pick a farther vehicle 23% of the time. Fixed (allow "wait until the exact departure" candidates). Also fixed a "battery dead zone" (vehicles rejected for insufficient charge that nevertheless did not go to swap).
- **The fixed baseline is not monotonically better**: 1–7% cheaper when energy is ample, but 2–8% more expensive when energy is tight (commits riders earlier, depletes station inventory sooner). Both versions are kept (`jit_dispatch` switch); recommend reporting both in the paper.

## 3. Plain-language explanation

1. **What the model computes**: each vehicle's "position, time, battery level" is drawn as a network, and the vehicle walks one path through it (deliver, swap, wait); station battery inventory is tracked per level per slot, and shuttles move batteries between stations. Gurobi picks one set of decisions for all vehicles, stations and shuttles **simultaneously** to minimise total cost.
2. **Why the ILP beats the baseline**: the baseline is "nearest goes, swap when low", and cannot see later orders; the ILP sees the whole day's orders and can send a vehicle to swap early or make it wait for a better-suited order. But the gain **shows up almost entirely as fewer missed orders**, not energy savings or shorter routes.
3. **Why the battery side is silent**: 2 hours is too short and 12 spare batteries are too many. The charging, transfer and grid constraints are written correctly but do not bind under this parameter set. To make them "speak", a longer window, fewer batteries and lower initial charge are needed.
4. **End-of-horizon targets are a hidden lever**: ρ and R_end decide "how many full batteries must remain at the station when the window ends". In E3 the value of transfers comes almost entirely from here. This is a modelling choice for the supervisor to decide.

## 4. What to change (by priority)

1. **Cost units**: P_i = 100 is too large, total cost equals "count the missed orders". Fix: calibrate in USD (rider wage → κ, w; battery depreciation → b^B; ConEd price → π), or use the minimum service-rate constraint of (33) / minimise missed orders first then cost (lexicographic switch already implemented).
2. **Time window and initial state**: switch to H = 48–96 (4–8 hours) or a rolling horizon, sample initial charge from a distribution (0.3–0.6), 2–3 spare batteries per station. Only then will the charging, transfer and grid constraints bind.
3. **End conditions**: clarify the meaning of ρ, R_end; better still, change to a "periodic condition" (end inventory state ≥ initial), to avoid artificially creating transfer demand with "must restore full charge by the deadline".
4. **Baseline policy**: the two new rules (JIT dispatch, dead-zone swapping) are harmful in stressed states and need redesign; add "choose a station with non-zero stock" and "demand-aware charging" (ASAP charging currently just spends more on electricity).
5. **Response-time reference**: θ is computed from the release time r_i, including uncontrollable prep waiting; recommend switching to a_i or reporting both (switch already provided).
6. **Energy rounding**: the document rounds up per leg, making energy per order almost independent of distance; recommend rounding over the whole route and quantifying the difference with E6.
7. **Real data**: next step is to connect DOHMH restaurants (27,030 with coordinates and cuisine), ACS zone weights, NYC LION road network + elevation + signals. Everything is synthetic at the moment.

## 5. How to iterate (suggested work loop)

Each round: **change one switch → run the toy example tests (must still be 12.5) → run a family of fixed-seed instances (ILP + baseline) → read the checker report and gap decomposition → decide the next step**.
The supporting tools are in place: `pytest tests` (67 tests), `experiments/e1_toy.py`, `run_pair`, `gap_definitions`, `relax_end_targets` in `experiments/common.py`.
Experiments not yet run: E5 siting and budget, E6 discretisation sensitivity, E7 scale limits and rolling horizon (plans in `workflow1_result.json` → plan.experiments).

## 6. How to add complexity later (from central decisions towards a more realistic system)

| Layer | What to add | Modelling approach | Code location |
|---|---|---|---|
| Information | Online / non-anticipative decisions | Rolling horizon: re-solve every k slots with known orders, compare with the offline lower bound | a rolling wrapper around `ilp.py`, carrying state (vehicle position/charge, inventory) into the next window |
| Uncertainty | Stochastic demand | Two-stage: first stage y, B, C, second stage operations; sample average approximation | multi-scenario sampling in `generator.py` + scenario-indexed ILP |
| Agents | Multiple platforms with their own objectives | Replace the common objective with per-platform costs + a coordination mechanism (bilevel / game / auction) | orders already carry the platform label φ(i), split the objective by platform |
| Agents | Riders choosing stations and swap thresholds autonomously | Behavioural model (logit station choice, heterogeneous thresholds), compliance-rate sweep, equilibrium | `BaselineParams` in `baseline.py` already has threshold and station-rule interfaces |
| Physics | Charging curves, degradation, heterogeneous batteries | Multi-slot charging steps (c_{jqt} completes at t+m, occupies [t,t+m)), indexing by battery type | rewrite (13)(20) in `ilp.py`, add battery types in `or_instance.py` |
| Logistics | Shuttle routes instead of fixed timetables | Coupled vehicle routing problem (VRP), or column generation producing candidate runs | the current Service table is already a "candidate column", generated by a subproblem |
| Grid | Time-of-use prices, group capacity, peak demand charges | time-varying π_jt, P^grid_gt by group, add a peak-demand charge | the data layer already supports a π dictionary and a P_grid list |
| Space | Real NYC road network and risk | LION network + DEM + signals → route library; crash density → risk-weighted routes | swap the implementation of the RoadNetwork interface in `network.py` |
| Scale | City level | Aggregate homogeneous riders into integer flows, column generation/Benders, rolling horizon | grouping in `arcs.py`, decomposition in `ilp.py` |

**File locations**: code `ebike_swap_sim/` (README.md, CONTRACT.md); experiment results `ebike_swap_sim/outputs/{e1, e2_coord, e2_coord_v2, e3, e4_sizing}/RESULTS*.md`
(`_v2` is the recomputation after the baseline fix); notes `notes/{understanding, datasets, DECISIONS, SUMMARY}.md`; audit and plan JSON `notes/workflow{1,2}_result.json`.

---

# Round 2 (2026-10-12): USD costs, 4-hour window, literature demand model, real data

Round 2 **did not change any of E2's mathematics** (`ilp.py`, `arcs.py`, `evaluate.py` are byte-identical to round 1, the toy example is still 12.5 / 11.2 / 106). Four things changed: cost units, instance family, the baseline rules used for comparison, and data sources. Decisions are recorded in `notes/DECISIONS.md` R2.1–R2.4; the review and fixes are in `notes/workflow6_round2_review.json`.

## 1. What was done

### 1.1 Cost calibration: from toy units to USD (R2.1, `notes/cost_calibration.md`)

Every objective coefficient was looked up against 2025–2026 New York prices (DCWP rider minimum pay, ConEd electricity prices, DoorDash/Grubhub lateness compensation, DOT swap-cabinet documents, battery market prices), with low / base / high values. The key ratios change as follows:

| Ratio | Toy units | USD base (usd_A) | USD usd_sunk (default) |
|---|---|---|---|
| Rejection penalty P ÷ (waiting price w × typical response 0.5 h) | **50** | 1.5 | 3.3 |
| Riding cost per order ÷ response cost | 0.67 | 0.07 | about 0.1 |
| One shuttle run f_e ÷ P | 0.05 | 0.67 | 0.67 |

**Why the default is `usd_sunk` rather than `usd_A`**: the E2 text says "the initial riders and vehicles are a given fleet resource", so rider wages are a **sunk cost** and should not be priced again per order or per km. Under usd_A (w = 40 $/h including rider wage), the unavoidable waiting of an ordinary order (prep about 27 min + pickup/drop-off 10 min + riding about 10 min) is worth about $31, more than P = 30, so "reject every order" becomes optimal — a degenerate objective, not a finding. `usd_sunk` puts only the **customer waiting value** (w = 18 $/h, v = 36 $/h) and vehicle wear (κ = 0.12 $/km) into the objective; the rest (P 30, π 0.32 $/kWh, f_e 20, F 12.03, b^B 0.332, b^C 0.082 per station per 4 h) is the same as usd_A. All three variants switch with one setting (`cost_variant`), and the E2u sensitivity experiment confirms the degeneracy argument (see 2.1).

### 1.2 Instance family `usd4h` (R2.2)

| Item | Round 1 | Round 2 `usd4h` |
|---|---|---|
| Time window | 2 h (H = 24 slots of 5 min) | **4 h**, 17:00–21:00 (H = 48) |
| Vehicles / orders | 10 vehicles / 30 orders (×1) | **6 vehicles / 36 orders** (1.5 orders per vehicle per hour; the nominal 10-vehicle 60-order size has 3.9 M arcs and does not solve within 5 minutes, hence reduced to 6 vehicles) |
| Initial charge q0 | 7.5–8.7 / 12 (ample) | **U{4..7} / 12 (30–60 %, tight)** |
| Spare batteries / charging slots per station | B 4 / C 2 | **B 3 / C 2**, K 8, M 1, σ 1, P_j 4 kW, grid group 8 kW (6 kW in 18–20 h) |
| Order attributes | synthetic | Kaggle-calibrated: prep U{20..35} min, promise = prep done + 25 min, 14 cuisine shares, Zipf s = 1 |
| Time-of-day curve | synthetic | declared assumption (dinner 17:30–21:30 at 45 %), piecewise step function |
| Binary variables | 0.66–1.04 M | 0.9–1.5 M (with lossless "reachability pruning") |

### 1.3 Baseline rule changes (R2.3)

Two new rules, both using only currently observable information:
- **Stock-aware station choice**: a vehicle needing a swap goes to the nearest open station **with a full battery** (station inventory is public information), falling back to the nearest station if none.
- **Demand-aware charging** (DEMAND_AWARE): at each boundary charge only the batteries needed for "expected swaps in the next 12 slots + reserve R_end", where the expected number = actual swaps at that station in the last 12 slots. Round 1's "charge ASAP" (ASAP) is kept as `baseline_round1`.

The round-1 fixes (JIT dispatch, dead-zone swapping) remain the default. Results show the two new rules make the baseline itself only **1.8 %** cheaper (±1.9) on usd4h, 0.0 % at ×1.5.

### 1.4 Literature demand model (`notes/literature_demand_model.md`)

The three papers cited on proposal p. 13 (Buettner 2023, US young adults weekly frequency Poisson regression; Bennett 2025, five-country adults online ordering logistic regression; Tahim 2024, Brazil app use and diet) are chained into "population at risk → participates or not → how often". Zone weight w_z = adult population × age factor × ethnicity × sex × income × children × living alone × student; age is the overwhelmingly dominant factor (18–29 vs 60+ about 3.4×), all other factors within ±10–30 %. Restaurants: cuisine drawn by Kaggle order share, then a restaurant within 2.5 km by Zipf popularity.

### 1.5 Data pipeline (R2.4, `data/MANIFEST.md`)

- 27,030 usable DOHMH restaurants (coordinates + cuisine + inspected), 90 cuisine descriptions mapped to 14 Kaggle classes + `other`; 4,607 inside the study box (Midtown/Chelsea/Flatiron), **26 % mapped to the non-samplable `other`** (cafes, bakeries, desserts).
- Zone weights use the ACS 2020–24 five-year NTA tables (262 NTAs), with GeoDa 2008–12 as a fallback with a warning.
- **Geometry is still synthetic**: real restaurants, zone weights and station coordinates are rotated by the Manhattan street-grid bearing (29°) and snapped to the 150 m synthetic grid; elevation, signals and routes are synthetic. There is no real road network.

### 1.6 Review and fixes (`notes/workflow6_round2_review.json`)

Two review agents (units/data, fairness) raised 15 findings in total, none of them an error in the E2 mathematics or the USD pricing (hand-computed objective, evaluation function and Gurobi objective agree to 1e-14). Both "medium" issues were fixed:
- **Units F1**: the time-of-day curve of the semi-real nyc4h was linearly interpolated as "on-the-hour intensities", smearing the 17:30 dinner step into a ramp starting at 17:00. After the fix E8 was **rerun**, the authoritative output is now `outputs/e8_nyc_fixed/` (`outputs/e8_nyc/` is superseded).
- **Fairness F1**: the "control instances" with relaxed end targets also set the baseline's charging reserve to 0, effectively swapping the comparison policy. After the fix the relaxed-target baseline rows of E3u were recomputed with the current package (only the 6 co-located-layout rows are affected, REORDER_POINT rows differ by at most 61 USD), and 18/18 fixed-variable certificates are feasible. E2u, E4u and E8 are unaffected.
- The remaining low-priority items (PRUNING_NYC constraining only the ILP, the hub charging rule, counting of unservable orders, pruning-fallback counts, swallowed exceptions, etc.) were fixed or declared in the reports. All 125 tests pass.

## 2. Results

All headline gaps are defined as **(baseline cost − ILP cost) ÷ baseline cost**; confidence intervals are 95 % t intervals (n ≥ 3).

### 2.1 E2u: value of coordination (6 vehicles, 4 h, 3 co-located stations, 5 seeds × 3 demand levels)

| Demand | Orders | Baseline R2.3 (USD/window) | ILP (USD/window) | gap | Round 1 (toy units) |
|---|---|---|---|---|---|
| ×0.75 | 27 | 502.7 | 466.9 | 6.9 % ± 4.9 | 4.3 % |
| ×1 | 36 | 822.9 | 638.3 | 21.3 % ± 11.3 | 29.6 % |
| ×1.5 | 54 | 1741.3 | 1074.3 | 37.3 % ± 10.8 | 38.2 % |
| Total | 15 instances | 1022.3 | 726.5 | **21.9 % ± 8.1** | 24.0 % ± 8.7 |

- Relative to the round-1-rule baseline: 23.4 % (±7.6); control ILP with relaxed end targets: 21.9 % (taking the better of written/relaxed; 19.0 % as recorded, because one solve stopped at the MIP start) → the end targets (17)(18) are worth only a few dollars on this family.
- **Gap composition** (296 USD per instance): lateness 160.8 (54 %), response time 73.2 (25 %), missed orders 60.0 (20 %), travel 1.4, electricity 0.4. Round 1 was 90 % missed orders.
- The ILP's advantage is **timing**, not volume: service rate 85.9 % vs 81.6 %, but late orders per instance 0.6 vs 12.5, mean response 49 vs 59 min; swaps 6.7 vs 7.2, electricity 1.1 vs 2.5 kWh.
- Cost-unit sensitivity (seeds 0–1, same batch of instances):

| Cost variant | ILP unserved rate ×0.75 / ×1 / ×1.5 | Baseline unserved rate | Note |
|---|---|---|---|
| usd_sunk | 3.7 / 8.3 / 25.9 % | 5.6 / 11.1 / 35.2 % | normal |
| usd_A | **85.2 / 86.1 / 83.3 %** | as above | serving an order costs more than P = 30 → degenerate |
| toy | 1.9 / 12.5 / 35.2 % | as above | 3 solves at ×1, ×1.5 timed out (gap 35–47 %), not comparable |

- Lexicographic (fewest missed orders first, then cheapest): 14.9 %, but only 5 of 15 instances have a proven-optimal first stage (100 s per stage is too short), **not citable yet**.
- Solving: 57 runs, Threads 3, 150 s limit; written models 23/27 optimal, average 90 s; all finished at the root node.

### 2.2 E3u: transfers and swap/charge separation (6 vehicles 36 orders, same totals of 9 batteries and 6 charging slots)

| Layout | ILP transfers allowed | ILP transfers forbidden | Value of transfers | Extra vs co-location | Round-1 value of transfers (toy) |
|---|---|---|---|---|---|
| (a) 3 co-located stations, written targets | 637.4 | 637.4 | 0.0 | — | 0 |
| (b) 3 swap stations + 1 hub, written | 689.8 | 696.4 | 6.6 (lower bound, upper 15–26) | +52.4 (29.2 is the hub fixed cost) | 257 |
| (c) 3 swap stations + 2 hubs, written | 719.1 | 710.3 (1 seed) | 12.6 (lower bound) | +81.7 (58.4 fixed) | 254.5 |
| (b) relaxed targets | 666.3 | 666.3 | **0.0** | +29.4 (= fixed cost + 0.2) | — |
| (c) relaxed targets | 673.3 | 673.3 | 0.0 | +58.8 (= fixed cost + 0.4) | — |

- ILP vs baseline (no transfers): 24 / 21 / 20 % (round 1: 48 / 37 / 36 %); vs the REORDER_POINT baseline 36.5 / 33.8 / 32.8 %.
- **The REORDER_POINT transfer rule is harmful across the board in USD**: in every layout and every seed it is 143–302 USD more expensive than no transfers (7–14 shuttle runs, missed orders unchanged). In round 1 it was beneficial in separated layouts by 115–220 toy units.
- Coverage shortfall: 15 of 36 ILP runs were skipped because of the 57-minute wall-clock budget (seed 2 entirely missing), 4 free-transfer solves of separated layouts with written targets timed out (300 s, gap about 2 %), so the ILP cells have only 1–2 seeds and no confidence intervals.
- The grid, charging and transfer machinery is correct but idle: hub peak 1.33 kW, stations ≤ 3.33 kW (caps 6–8 kW), electricity < 1 USD.

### 2.3 E4u: station sizing (B_j spare batteries, C_j charging slots, P_j power; 3 seeds)

| Batteries per station B_j | ILP total cost | ILP marginal value (USD/battery/window) | Baseline total cost | Baseline marginal value | gap |
|---|---|---|---|---|---|
| 1 | 637.6 | +0.14 ± 1.14 (1→2) | 1003.1 | **+48.5** (≈ 71k USD/battery/year) | 35.1 % |
| 2 | 637.1 | −0.26 | 857.6 | +8.5 | 24.4 % |
| 3 (default) | 637.9 | −0.25 | 832.2 | −0.27 | 22.5 % ± 21.3 |
| 4 | 638.7 | −0.31 | 833.0 | +2.44 | 22.5 % |
| 6 | 640.5 | — | 818.3 | — | 21.2 % |

- Letting the ILP choose sizes freely: it buys only 3–4 batteries and 2–3 charging slots network-wide (default 9 / 6), at least one station per seed gets no charging slot, but it saves only 1.3–1.6 USD/window — holding costs are small to begin with.
- **The marginal operating value of a charging slot is exactly 0** (ILP operating cost is identical for C_j = 1, 2, 3, 4); power caps of 1.4–4.2 kW are shown not to bind; one extra charging slot slightly hurts the baseline (buys more electricity for batteries it cannot use).
- Round 1 (toy units, stressed state) had an ILP knee at 2 batteries per station (62 toy units per battery); in round 2 **the knee disappears, 1 battery is enough**, and the knee moves to the baseline side. In 2 seeds the baseline never catches up with the ILP's service rate even at 6 batteries per station (0.806 vs 0.861 / 0.889).
- Unresolved: the ILP P sweep (replaced by a squeeze argument) and the 12 offline B×C cells (wall-clock budget).

### 2.4 E8: semi-real New York instance nyc4h (real restaurants + ACS zone weights + real station coordinates; 6 vehicles 36 orders, 3 seeds)

| Siting | Baseline (USD) | ILP | gap | Relaxed-target control |
|---|---|---|---|---|
| Busiest restaurant cells | 1100.3 | 679.6 | **36.5 % ± 29.3** | 36.5 % |
| Grid-connected landmarks (8th Ave/W 34th, Union Sq, Grand Central) | 1075.6 | 679.6 | 34.3 % ± 37.6 | 34.4 % |

- Gap composition (421 USD): lateness 61 %, response 36 %, missed orders 2.4 %; both methods serve about 84–85 %.
- **Siting has almost no effect on the ILP** (per seed change ≤ 0.25 USD, ≤ 0.04 %), while the baseline changes by −9 % to +4 %: coordinated scheduling absorbs differences in station location, the nearest-rider rule cannot.
- The demand side is more realistic than the synthetic family (L1 distance of cuisine shares to Kaggle 0.20 vs 0.31, 32 restaurants vs 8, 8–11 NTAs), but mean trip length is almost identical (1.76 vs 1.77 km) because the grid and physics are the same.
- Cheapest to solve: 0.58 M binary variables, 12/12 root-node optimal, average 41 s. Note PRUNING_NYC constrains only the ILP, so the gap is a **lower bound** on the value of coordination.

### 2.5 Round 1 vs round 2 comparison table

| Item | Round 1 (2026-10-11) | Round 2 (2026-10-12) |
|---|---|---|
| Cost units | toy: P 100, w 12/h, κ 1/km | USD usd_sunk: P 30, w 18 $/h, v 36, κ 0.12 $/km |
| P ÷ (w × 0.5 h) | 50 | 3.3 |
| Instances | 10 vehicles / 2 h / 30 orders, q0 7.5–8.7 | 6 vehicles / 4 h / 36 orders, q0 4–7 |
| Baseline rules | nearest station + charge ASAP | stock-aware station choice + demand-aware charging (only 1.8 % cheaper) |
| E2 total gap | 24.0 % ± 8.7 | 21.9 % ± 8.1 |
| E2 by demand ×0.75 / ×1 / ×1.5 | 4.3 / 29.6 / 38.2 % | 6.9 / 21.3 / 37.3 % |
| Gap composition | 90 % missed orders, 9 % lateness, 1 % travel | 54 % lateness, 25 % response, 20 % missed orders, <1 % travel + electricity |
| Price of end targets (17)(18) | all of the transfer value comes from them | a few USD per instance; transfer value = 0 when relaxed |
| E3 value of transfers (b) / (c) | 257 / 254.5 | 6.6 / 12.6 USD (written targets), 0 / 0 (relaxed) |
| E3 cost of separation (b) / (c) | +55.4 / +97.9 (40 fixed) | +52.4 / +81.7 USD (29 / 58 fixed) |
| E3 ILP vs baseline (a)/(b)/(c) | 48 / 37 / 36 % | 24 / 21 / 20 % |
| REORDER_POINT rule | beneficial in separated layouts 115–220 | harmful in all layouts +143 to +302 USD |
| E4 ILP battery knee | 2 per station (stressed state, 62 per battery) | no knee, 1 is enough (1→2 only +0.14 USD) |
| E4 baseline battery knee | > 6 | 2–3 (1→2 saves 48.5 USD/battery/window) |
| Marginal value of a charging slot | ILP 0; baseline +7.6 | ILP 0; baseline slightly negative |
| Real data | none | nyc4h: 36.5 % ± 29.3 / 34.3 % ± 37.6 |
| Solve size / time | 0.66–1.04 M binaries, 15–30 s (Threads 4) | 0.9–1.5 M, about 90 s; nyc4h 0.58 M, 41 s (Threads 3) |

## 3. Plain-language explanation: why the numbers changed

1. **The ratio of P to w decides "what the objective counts"**. In toy units rejecting one order = 50 orders' worth of waiting cost, so the objective is effectively "count missed orders first, then everything else", which is why 90 % of the round-1 gap was rejection penalties. In USD rejecting one order is worth only about 1.7 hours of waiting (P/w = 30/18), and lateness costs 36 USD per hour; both methods deliberately drop a few orders when busy, and the gap moves to **lateness and waiting**. The total percentage barely changed (24 → 22 %), but its meaning is completely different: now it is "the customers' on-time value", not "the number of missed orders".
2. **A 4-hour window + low initial charge makes charging actually happen**. In round 1 the ILP never charged; in round 2 the baseline uses 2.5 kWh per instance and the ILP 1.1 kWh, and the baseline misses the end inventory target in 4/6 of the nyc4h instances. But 9 spare batteries are still enough for 6 vehicles over 4 hours — the ILP with relaxed end targets does not buy a single kWh. So the charging, transfer and grid constraints are "correct but still not binding", just closer to binding than in round 1.
3. **The value of transfers shrinks 20-fold** because P fell from 100 to 30 while f_e rose from 5 to 20: one shuttle run equals 2/3 of an order, so it is only worth dispatching when it rescues ≥ 1 order. With written targets, the transfer value in separated layouts (0.6–12.6 USD) still comes entirely from the mechanism "keep 5 full batteries at the end" squeezing the number of swaps down to 4.
4. **Stock-aware station choice + demand-aware charging are worth only 1.8 %**: with co-located layouts and 3 spare batteries, the baseline rarely meets an empty station, so the new rules rarely change decisions; demand-aware charging saves only a few dollars of electricity. The root cause of the baseline's weakness is **dispatch that cannot see later orders**, not the swap rules.
5. **The ILP no longer needs a second battery** because it can schedule swaps at stations and times known to have stock (it tolerates more empty-station slots yet swaps less); the baseline relies on inventory as a safety net, so the marginal value moves to the baseline side. In other words: **station capital is not the lever, coordination is**.
6. **The New York instance has a higher gap (36 %) but a very wide interval**: in seed 0 the baseline's lateness cost reaches 447 USD (gap 48 %), and the 3-seed t interval is wider than the mean, so it can only be read as "the ILP's advantage still holds with real restaurant and customer geography", not as a precise percentage.

## 4. What to change (by priority)

1. **Fill in the unsolved cells**: all 12 E3u seed-2 runs + the 3 (c) seed-1 runs (about 1 h); the E4u ILP P sweep and the 12 offline B×C cells (60–90 min); raise the lexicographic stage-1 time limit from 100 s to ≥ 300 s or switch to the minimum service-rate constraint of (33). Otherwise E3u/E4u cannot give ILP confidence intervals and the lexicographic column cannot be cited.
2. **More seeds**: n = 3 for E8 (41 s each) and E4u is too few, the CI is wider than the mean; running nyc4h with 10 seeds takes only ~15 min. Also run the lossless-pruning probe for nyc4h (`e8_nyc_fixed.py --targets default`) to turn the PRUNING_NYC lower bound into an exact value.
3. **End conditions**: ρ / R_end remain the only source of transfer value. Switch to a "periodic condition" (end state ≥ initial state) or try 8 h / rolling horizon (solvability of usd8h has not been probed).
4. **Baseline transfer rule**: REORDER_POINT is harmful across the board in USD; either change it to a cost-aware trigger (dispatch only when a stock-out is forecast), or present it in the paper only as evidence that "naive rules are harmful".
5. **Rerun the toy variant** (300 s) to restore the unit comparison with round 1; currently 3/6 toy solves at ×1 / ×1.5 timed out and are invalid.
6. **Response-time reference**: in USD, pricing w from the release time r_i charges 20–35 min of prep waiting at 18 $/h (6–10 USD per order), pushing towards rejection; at least report the a_i-based numbers alongside.
7. **Minor script fixes**: E2u's CI uses 1.96 instead of t(14) = 2.145 (9 % underestimate); the E3u/E4u summaries count skipped rows in n; E8's served_share_servable column is exported only for the baseline; E4u's C_j = 4 cell shows a spurious jump because of a different seed set.
8. **Items outside the documents**: split b^B into holding (scales with window length) and initial charge (does not scale), otherwise 8 h instances over-count 0.213 USD per battery; DECISIONS/zone_weights_README must state that no group-quarters correction is applied, the one-sided PRUNING_NYC constraint, and that the old e8_nyc used the ramp curve.
9. **Cuisine mapping**: 26 % of restaurants in the box fall into the non-samplable `other`; `CUISINE_MAP_CAFES_AS_AMERICAN` can be used as a sensitivity (drops to 8.9 %).
10. **Real road network**: NYC LION/CSCL + elevation + signals are still not connected; all distances and energy come from the synthetic grid.

## 5. Decisions needed from you

1. Lexicographic column: rerun with a longer stage-1 limit, or switch to the minimum service-rate constraint ζ of (33)? Or not report service-first results in the paper?
2. Missing E3u / E4u ILP cells: spend 2–3 h filling them, or accept n = 1–2 with no confidence intervals?
3. End conditions: keep ρ = 0.5 / R_end = 1, switch to a periodic condition, or move to 8 h / rolling horizon? (This is the only switch that decides whether transfers have value.)
4. REORDER_POINT baseline rule: redesign, keep as evidence of a "harmful rule", or delete?
5. Response-time reference: keep r_i (as in the text), or switch to a_i / report both?
6. Number of seeds: increase E8 and E4u from 3 to 10? (E8 is cheap, E4u is 2–3 min per cell.)
7. nyc4h pruning: run the lossless probe to make the gap exact instead of a lower bound?
8. Rerun the toy variant (300 s) to keep the claim "comparable with round-1 units"?
9. Baseline end-target (18) violations in 3–4 of 6 runs are reported but not enforced: accept the "conservative headline", or use `baseline_reserve` (satisfies (18)) as the headline comparison?
10. May `notes/DECISIONS.md` and `notes/data/cost_calibration_usd.json` be modified (b^B split, group-quarters correction, PRUNING_NYC note)?
11. Cuisine mapping `other` at 26 %: accept, or adopt the cafe → American sensitivity mapping?
12. Confidence-interval convention for the paper: t distribution (RESULTS_final.md) or 1.96 (script figures)?
13. Old output directories (`outputs/e8_nyc`, the pre-fix relaxed-target baseline rows of E3u): delete, archive, or keep with a "superseded" label?

## 6. File locations

| Content | Path |
|---|---|
| Decisions (R2.1–R2.4 + implementation notes) | `notes/DECISIONS.md` |
| Cost calibration | `notes/cost_calibration.md`, `notes/data/cost_calibration_usd.json` |
| Literature demand model | `notes/literature_demand_model.md`, `notes/literature/` |
| Data manifest | `data/MANIFEST.md`, `data/raw/` |
| Review and fixes | `notes/workflow6_round2_review.json` |
| E2u value of coordination | `ebike_swap_sim/outputs/e2u_coord_usd/RESULTS_final.md` (records.jsonl, results.csv, 4 figures) |
| E3u transfers and separation | `ebike_swap_sim/outputs/e3u/RESULTS_final.md` (relaxed_baseline_recomputed.csv, relaxed_start_certificates.csv, 8 figures) |
| E4u station sizing | `ebike_swap_sim/outputs/e4u_sizing_usd/RESULTS_final.md` (results_baseline_fill.csv, 4 figures) |
| E8 New York semi-real | `ebike_swap_sim/outputs/e8_nyc_fixed/RESULTS_final.md` (4 figures, including map_seed0.png); `outputs/e8_nyc/` is superseded |
| Scale probe | `ebike_swap_sim/outputs/r2_probe/` |
| Experiment scripts | `ebike_swap_sim/experiments/{e2u_coord_usd,e3u_transfers_usd,e4u_sizing_usd,e8_nyc_fixed}.py` (`*_fixed.py` are the post-review copies) |
| Code | `ebike_swap_sim/` (README.md, CONTRACT.md, 125 tests) |

---

# Round 3 (2026-10-12/13): service-share constraint, filled cells, more seeds

Round 3 again **did not change any of E2's mathematics** (`ilp.py`, `arcs.py`, `evaluate.py` unchanged; toy 12.5 / 11.2 / 106 still reproduced). Three things changed: the service-level variant (the hard service-share constraint (33) replaces the lexicographic variant), the solver protocol (every cell skipped in round 2 is solved, with reuse rules), and the coverage (more seeds). Decisions are recorded in `notes/DECISIONS.md` R3.1-R3.3. The four experiments ran concurrently on one machine (Gurobi 13, OutputFlag 0, Threads 3, Seed 0, TimeLimit 300 s, 600 s for one E3u cell type) between 2026-10-12 21:59 and 2026-10-13 02:22; nothing was skipped for budget reasons.

## 1. What was done

### 1.1 Service level: constraint (33) with zeta = 0.90 (main) and 0.85 (sensitivity) (R3.1)

The round-2 lexicographic column (minimise unserved orders first, then cost) was not citable because only 5 of 15 stage-1 solves were certified. It is dropped. The service level is now imposed directly with (33) `sum_i (1 - u_i) >= zeta |I|` as a hard constraint on the written model: `zeta = 0.90` is the main setting (`ilp_zeta90`) and `zeta = 0.85` the sensitivity (`ilp_zeta85`); 0.95 was rejected by the user as too strict. Two protocol rules keep the solve budget down: if the certified written optimum already serves at least `zeta |I|` orders the zeta cell is recorded without a solve (`solve_mode = implied_by_written`; adding a satisfied constraint cannot change the optimum), and if a zeta instance is INFEASIBLE the record stores the maximum feasible served share from one `min sum_i u_i` solve (incumbent share, Gurobi bound share, certified flag; `experiments.common.max_service_share`), so that "infeasible" always comes with "how far from feasible".

### 1.2 End-of-horizon targets kept (R3.2)

rho = 0.5 / R_end_j = 1 stay as written; the relaxed control (rho 0, R_end 0, `ilp_relaxed`) is kept and is now solved to optimality everywhere, so the price of the end targets is an exact number this round.

### 1.3 Cells filled, seeds extended (R3.3)

- Every ILP cell that round 2 skipped for wall-clock reasons was solved. Round-2 rows are reused only when OPTIMAL or within 1 % MIP gap (`common.reusable_ilp_row`); the 4 E3u separated / written / transfers-free cells that stopped at 300 s with a 2 % gap were re-solved with 600 s, and that cell type gets 600 s on every seed.
- Seeds: E2u 0-9 (was 0-4), E3u 0-4 (was 0-1 with 15 cells missing), E4u 0-5 on the B sweep, the default size and the free-size run (was 0-2), plus the P sweep and the 12 off-line B x C cells that round 2 never solved, E8 0-9 (was 0-2).
- Scripts `experiments/{e2u,e3u,e4u,e8}_round3.py` with wall budgets (5 / 4 / 4 / 2 h), `SKIPPED_BUDGET` records for anything not started (none occurred), append-only `records.jsonl`, `results.csv` refreshed after every run, `--dry-run` / `--smoke` / `--analyse` modes covered by `tests/test_round3.py`. Baseline rows were recomputed where cheap (E3u, E4u: milliseconds, asserted against the stored round-2 rows, 0 mismatches) and reused in E2u / E8.

### 1.4 English-only repository preparation

The repository is being pushed to a public GitHub repository, so every deliverable is in English: the round-3 reports (`RESULTS_final.md` in each `outputs/*_round3/` directory), the script-written `RESULTS.md` files (the E8 one had a Chinese abstract, rewritten in English in place), this summary and the package README. Each round-3 directory was checked with `grep -P '[\x{4e00}-\x{9fff}]'` (0 matches). The Chinese companion note of rounds 1-2 is not part of the public repository.

## 2. Results

All gaps are **(baseline cost - ILP cost) / baseline cost** on the same instance; confidence intervals are 95 % Student-t intervals over seeds with exact t quantiles (the scripts' own `improvement.csv` / figures use z = 1.96 for n > 11, which narrows the pooled E2u half-width from +/- 5.61 to +/- 5.38; means are identical). Family `usd4h` throughout unless stated: 6 bikes, 4 h (H = 48), 3 co-located sites with B 3 / C 2, `usd_sunk` prices, R2.3 baseline.

### 2.1 E2u: value of coordination and the service-share constraint (10 seeds x 3 demand levels; `outputs/e2u_round3/RESULTS_final.md`)

**Headline:** the written E2 ILP is cheaper than the baseline on all 30 instances; gap **29.55 % +/- 5.61** (n = 30), minimum per-instance gap 3.7 %.

| comparison | demand | n | gap mean % | CI95 +/- | abs gain USD | baseline mean USD | ILP mean USD |
|---|---|---|---|---|---|---|---|
| ILP written vs baseline R2.3 [headline] | x0.75 | 10 | 15.36 | 7.28 | 97.3 | 577.4 | 480.1 |
| ILP written vs baseline R2.3 [headline] | x1 | 10 | 31.18 | 9.05 | 333.9 | 992.5 | 658.6 |
| ILP written vs baseline R2.3 [headline] | x1.5 | 10 | 42.11 | 5.66 | 831.8 | 1930.3 | 1098.4 |
| ILP written vs baseline R2.3 [headline] | all | 30 | **29.55** | **5.61** | 421.0 | 1166.7 | 745.7 |
| ILP written, seeds 0-4 (= round 2, reproduced exactly) | all | 15 | 21.86 | 8.13 | 295.9 | 1022.3 | 726.5 |
| ILP written, seeds 5-9 | all | 15 | 37.24 | 6.22 | 546.2 | 1311.2 | 765.0 |
| ILP + (33) zeta 0.90 vs baseline | x0.75 | 10 | 15.20 | 7.26 | 96.4 | 577.4 | 481.0 |
| ILP + (33) zeta 0.90 vs baseline | x1 | 10 | 27.76 | 8.66 | 296.6 | 992.5 | 696.0 |
| ILP + (33) zeta 0.90 vs baseline | x1.5 | 0 | infeasible 10/10 | - | - | - | - |
| ILP + (33) zeta 0.90 vs baseline | all | 20 | 21.48 | 5.91 | 196.5 | 785.0 | 588.5 |
| ILP + (33) zeta 0.85 vs baseline | x0.75 | 10 | 15.36 | 7.28 | 97.3 | 577.4 | 480.1 |
| ILP + (33) zeta 0.85 vs baseline | x1 | 10 | 30.58 | 8.59 | 326.0 | 992.5 | 666.6 |
| ILP + (33) zeta 0.85 vs baseline | x1.5 | 0 | infeasible 10/10 | - | - | - | - |
| ILP + (33) zeta 0.85 vs baseline | all | 20 | 22.97 | 6.25 | 211.6 | 785.0 | 573.3 |
| ILP relaxed (rho 0, R_end 0) vs baseline | x0.75 | 10 | 15.39 | 7.28 | 97.5 | 577.4 | 479.9 |
| ILP relaxed (rho 0, R_end 0) vs baseline | x1 | 10 | 31.22 | 9.03 | 334.3 | 992.5 | 658.2 |
| ILP relaxed (rho 0, R_end 0) vs baseline | x1.5 | 10 | 42.14 | 5.66 | 832.3 | 1930.3 | 1098.0 |
| ILP relaxed (rho 0, R_end 0) vs baseline | all | 30 | 29.58 | 5.61 | 421.4 | 1166.7 | 745.4 |

The written ILP on the same 20 instances where zeta 0.90 is feasible saves 23.27 % +/- 6.46, so the service guarantee costs about 1.8 points of the saving. Seeds 5-9 are much harder for the baseline than seeds 0-4 (baseline 1311 vs 1022 USD; ILP 765 vs 727 USD; Welch p = 0.004 on the gap): the round-2 CI understated the between-seed spread of the baseline. The ILP total is nearly deterministic (CV 4-5 %) while the baseline varies by 15-22 %, and the per-instance gap tracks the baseline's lateness cost (r = 0.91).

**Service-share constraint (33):**

| zeta | demand | feasible / 10 | implied by written | binding | premium vs written USD (CI95) | premium % | served zeta / written / baseline | unserved zeta / written / baseline | required served | max feasible share where infeasible |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.90 | x0.75 | 10 | 7 | 3 | 0.94 +/- 1.36 | 0.19 | 0.956 / 0.944 / 0.967 | 1.20 / 1.50 / 0.90 | 25 of 27 | - |
| 0.90 | x1 | 10 | 1 | 8 | 37.38 +/- 38.23 | 5.46 | 0.922 / 0.875 / 0.872 | 2.80 / 4.50 / 4.60 | 33 of 36 | - |
| 0.90 | x1.5 | 0 | 0 | - | - | - | - | written 0.698 / baseline 0.626 | 49 of 54 | certified 0.741 / 0.778 / 0.741 / 0.796 / 0.759 (seeds 3, 4, 7, 8, 9); upper bound 0.833 / 0.759 / 0.759 / 0.796 / 0.778 (seeds 0, 1, 2, 5, 6) |
| 0.85 | x0.75 | 10 | 10 | 0 | 0.00 | 0.00 | 0.944 / 0.944 / 0.967 | 1.50 / 1.50 / 0.90 | 23 of 27 | - |
| 0.85 | x1 | 10 | 7 | 2 | 7.99 +/- 17.34 | 1.11 | 0.886 / 0.875 / 0.872 | 4.10 / 4.50 / 4.60 | 31 of 36 | - |
| 0.85 | x1.5 | 0 | 0 (2 implied_by_max_service) | - | - | - | - | - | 46 of 54 | same bounds as zeta 0.90 (all <= 0.833 < 0.85) |

- zeta 0.90 at x1 binds on 8 of 10 seeds (premium 1.4-175.9 USD, median 32.6); it rescues 1.7 orders per instance at a net 22 USD per rescued order on top of the 30 USD penalty avoided, paid mostly in lateness (5.7 late deliveries vs 1.2 for the written ILP; baseline 16.5). zeta 0.85 binds on 2 of 20 feasible instances (seeds 6 and 8 at x1: 3.2 and 76.9 USD).
- At x1.5 (54 orders) no schedule can serve 85 %, let alone 90 %: 6 bikes in 4 h reach at most 0.74-0.80 served (certified on 5 seeds) and at most 0.76-0.83 by the Gurobi bound on the other 5; the cost-optimal ILP drops 16.3 orders (30 %), the baseline 20.2 (37 %). The script leaves 4 of these cells per zeta level as undecided (max-service solve at TIME_LIMIT without incumbent), but their dual bounds (at least 9 / 13 / 11 / 12 unserved on seeds 0, 1, 5, 6 vs 8 allowed at zeta 0.85 and 5 at 0.90) already prove infeasibility; `RESULTS_final.md` counts all 10 as infeasible by bound.

**Gap decomposition (baseline - ILP written, USD per instance):**

| decomposition | n | total gap USD | unserved (30) | response (31) | lateness (31) | travel (27) | electricity (28) |
|---|---|---|---|---|---|---|---|
| x0.75 | 10 | 97.3 | -18.0 (-18 %) | 51.5 (53 %) | 61.2 (63 %) | 2.1 | 0.6 |
| x1 | 10 | 333.9 | 3.0 (1 %) | 125.0 (37 %) | 203.1 (61 %) | 2.4 | 0.5 |
| x1.5 | 10 | 831.8 | 117.0 (14 %) | 229.9 (28 %) | 482.4 (58 %) | 2.2 | 0.3 |
| all | 30 | 421.0 | 34.0 (8 %) | 135.4 (32 %) | 248.9 (59 %) | 2.2 (1 %) | 0.5 (0 %) |

Drop rates (unserved / orders) at x0.75 / x1 / x1.5: baseline 3.3 / 12.8 / 37.4 %, ILP written 5.6 / 12.5 / 30.2 %, zeta 0.90 4.4 / 7.8 / -, zeta 0.85 5.6 / 11.4 / -. The ILP drops more orders than the baseline on 8 of 30 instances (by 1-5 orders) because at P = 30 USD a drop is cheaper than a late delivery; hence the negative unserved term at x0.75.

**Relaxed control:** 30/30 OPTIMAL, gap 29.58 % +/- 5.61 (15.39 / 31.22 / 42.14); the end targets (17)-(18) cost 0.34 USD per instance (0.17 / 0.36 / 0.48 by level, max 0.86). Round 2 had recorded 19.0 % because one cell was stuck at the MIP start; that cell is now OPTIMAL.

**Solver:** 0.89-1.58 M binaries, 57-69 k rows; written ILP 28/30 OPTIMAL (2 TIME_LIMIT with MIP gap 0.04 % / 0.11 %), mean 143 s on solved cells, 26/30 closed at the root; zeta 0.90 19 OPTIMAL / 9 TIME_LIMIT / 2 INFEASIBLE; zeta 0.85 20 / 6 / 4; relaxed 30/30 OPTIMAL; 25 of the 60 zeta cells settled without a solve (implied_by_written 8 + 17, implied_by_max_service 2); the MIP start was `none(start violates zeta)` on 29 zeta cells; wall 263.2 of 300 min.

### 2.2 E3u: transfers and swap/charge separation (seeds 0-4, all 60 ILP cells solved; `outputs/e3u_round3/RESULTS_final.md`)

Same totals in every layout (9 spares, 6 chargers); ILP transfers free unless stated; USD per 4 h, mean +/- 95 % t-CI, n = 5.

| layout | targets | ILP transfers free | ILP h = z = 0 | value of transfers (none - free) | upper bound | separation vs (a) | gap vs policy NONE % | gap vs REORDER_POINT % | status free / none |
|---|---|---|---|---|---|---|---|---|---|
| (a) co-located 3 sites | written | 638.2 +/- 28.7 | 638.2 +/- 28.7 | 0.01 +/- 0.03 | 0.02 | - | 21.3 +/- 11.3 | 37.4 +/- 7.3 | 5 OPT / 5 OPT |
| (a) co-located 3 sites | relaxed | 637.9 +/- 28.8 | 637.9 +/- 28.8 | 0.00 | 0.00 | - | 21.4 +/- 11.3 | 37.5 +/- 7.3 | 5 OPT / 5 OPT |
| (b) 3 swap sites + 1 hub | written | 690.5 +/- 29.0 | 699.1 +/- 29.7 | 8.6 +/- 10.1 (lower bound) | 22.2 +/- 9.8 | +52.2 +/- 1.6 (F_hub 29.19) | 18.4 +/- 10.6 | 32.0 +/- 5.6 | 5 TL (600 s) / 5 OPT |
| (b) 3 swap sites + 1 hub | relaxed | 667.1 +/- 28.7 | 667.1 +/- 28.7 | 0.00 | 0.01 | +29.3 +/- 0.2 | 21.2 +/- 10.2 | 34.3 +/- 5.3 | 5 OPT / 5 OPT |
| (c) 3 swap sites + 2 hubs | written | 719.7 +/- 29.0 | 728.3 +/- 29.6 | 8.6 +/- 10.1 (lower bound) | 22.2 +/- 9.6 | +81.4 +/- 1.6 (F_hub 58.38) | 17.8 +/- 10.4 | 31.1 +/- 5.5 | 5 TL (600 s) / 5 OPT |
| (c) 3 swap sites + 2 hubs | relaxed | 696.3 +/- 28.7 | 696.3 +/- 28.7 | 0.00 | 0.02 | +58.5 +/- 0.2 | 20.5 +/- 10.0 | 33.4 +/- 5.2 | 5 OPT / 5 OPT |

- Policy NONE 822.9 / 856.2 / 885.4 USD (a / b / c); REORDER_POINT 1029.8 / 1021.3 / 1050.0; paired REORDER_POINT - NONE +206.9 +/- 75.4 / +165.1 +/- 46.9 / +164.6 +/- 47.2 USD, worse on every layout and seed, unserved unchanged on 12/15 pairs.
- Mechanism unchanged on every seed: with h = z = 0 the separated written layouts are capped at 4 swaps and 0.822 served; one 2-battery shuttle (22 USD) restores 6 swaps and 0.894. Under relaxed targets 0 shuttles on all 15 pairs.
- The 600 s re-solves did not close the gaps: all 10 separated / written / transfers-free runs stop at 1.79-2.00 % after 63-143 nodes; the four round-2 incumbents improved by 0.00 / 0.00 / 0.23 / 0.32 USD; on seed 2 the free incumbent is 0.56 USD above the no-transfers optimum (reads as 0).
- Hub grid peak 1.33 kW, sites at most 3.33 kW vs 6-8 kW limits; electricity <= 0.82 USD per window. Round-3 OPTIMAL runs mean 79 s, 32/33 at the root; wall 150 of 240 min.

### 2.3 E4u: station sizing (seeds 0-5 on the B sweep / default / free-size; `outputs/e4u_round3/RESULTS_final.md`)

| quantity | round 3, n = 6 (seeds 0-5) | round 2, n = 3 |
|---|---|---|
| headline gap at default size (B 3, C 2, P 4 kW) | **24.6 % +/- 12.0** (per seed 16.1 / 32.2 / 19.1 / 29.0 / 10.3 / 41.1) | 22.5 % +/- 21.3 |
| ILP / baseline total, USD per window | 641.4 +/- 23.1 / 871.8 +/- 172.2 | 637.9 +/- 55.3 / 832.2 +/- 311.7 |
| served share ILP / baseline | 0.898 +/- 0.044 / 0.866 +/- 0.083 | 0.907 / 0.861 |
| gap components lateness / response / unserved / travel / electricity, USD | 127.0 / 66.8 / 35.0 / 1.3 / 0.4 | 97.0 / 45.5 / 50.0 / 1.3 / 0.4 |
| free sizing: batteries / chargers bought network-wide (default 9 / 6) | 3.5 +/- 0.6 / 2.8 +/- 0.8, saving 1.43 +/- 0.18 USD per window | 3-4 / 2-3, saving 1.3-1.6 |

B sweep (C_j = 2, P_j = 4 kW; n = 6; marginal = paired value of one more battery at one site):

| B_j | ILP total USD | ILP served | ILP stock-out slots | ILP marginal total / window | baseline total USD | baseline served | baseline marginal total / window | gap % |
|---|---|---|---|---|---|---|---|---|
| 1 | 640.6 +/- 22.6 | 0.894 | 105.3 | +0.02 +/- 0.34 | 1022.9 +/- 199.2 | 0.787 | **+44.2 +/- 21.6** (64,600 USD per battery-year) | 35.7 +/- 11.4 |
| 2 | 640.6 +/- 23.1 | 0.898 | 43.0 | -0.27 +/- 0.02 | 890.2 +/- 186.2 | 0.875 | +6.1 +/- 10.8 | 26.0 +/- 12.9 |
| 3 (default) | 641.4 +/- 23.1 | 0.898 | 21.3 | -0.25 +/- 0.01 | 871.8 +/- 172.2 | 0.866 | -0.7 +/- 1.1 | 24.6 +/- 12.0 |
| 4 | 642.1 +/- 23.2 | 0.898 | 3.2 | -0.31 +/- 0.03 | 873.9 +/- 172.9 | 0.870 | +1.1 +/- 3.5 | 24.7 +/- 12.1 |
| 6 | 644.0 +/- 23.2 | 0.898 | 0.0 | - | 867.3 +/- 167.8 | 0.870 | - | 24.0 +/- 11.7 |

- Chargers and power (seeds 0-2, now solved rather than bounded): ILP operational cost identical to 1e-9 across C_j = 1-4 and P_j = 1.4-4.2 kW (total +bC = 0.082 USD per charger per window); baseline -0.08 to -0.17 USD per charger, -0.02 per kW; (21) never binds (peak 3.33 kW).
- Seed-0 B x C grid complete (20/20 cells): ILP total 614.2-618.0 USD (minimum at B 2 / C 1), baseline 732.6-1011.1; gap 39 % at B 1, 20 % at B 2, 16 % at B >= 3, independent of C.
- Baseline at the ILP-chosen lean sizes collapses: served 0.796, 985 +/- 188 USD, gap 33.5 +/- 10.5 %; on seeds 1-3 the baseline never reaches the ILP's served share at any B_j <= 6.
- Solver: 72 ILP cells (29 reused + 43 new), 69 OPTIMAL, 3 TIME_LIMIT (all seed 0, B_j = 1, gap <= 0.29 %, rejected MIP start); mean 118 s; wall 96.7 of 240 min.

### 2.4 E8: semi-real NYC `nyc4h` (seeds 0-9, two sitings; `outputs/e8_round3/RESULTS_final.md`)

| siting | gap written ILP % | gap relaxed ILP % | baseline total USD | ILP total USD | relaxed total USD | saving USD | ILP - relaxed USD | gap range % | served base / ILP | late deliveries base / ILP | mean response h base / ILP |
|---|---|---|---|---|---|---|---|---|---|---|---|
| busiest (n = 10) | **31.8 +/- 8.2** | 31.9 +/- 8.2 | 1013.7 +/- 149.3 | 669.9 +/- 13.3 | 669.6 +/- 13.3 | 343.8 +/- 138.8 | 0.28 +/- 0.06 | 18.9 - 49.3 | 0.839 / 0.858 | 17.8 / 1.5 | 1.07 / 0.83 |
| grid (n = 10) | **30.5 +/- 8.6** | 30.6 +/- 8.6 | 997.1 +/- 153.4 | 669.9 +/- 13.3 | 669.6 +/- 13.3 | 327.2 +/- 144.2 | 0.27 +/- 0.05 | 17.7 - 50.9 | 0.853 / 0.858 | 18.4 / 1.5 | 1.06 / 0.83 |
| round 2, seeds 0-2 (n = 3) | 36.5 +/- 29.3 / 34.3 +/- 37.6 | 36.5 / 34.4 | 1100.3 / 1075.6 | 679.6 | 679.4 | - | 0.21 / 0.23 | - | 0.843 / 0.852 | 19.7 / 1.7 | 1.12 / 0.84 |

- Gap positive on 20/20 instances; the 7 new seeds alone give 29.8 +/- 10.8 % / 28.9 +/- 10.5 %. Decomposition (busiest): lateness 58.5 %, response 34.7 %, unserved 6.1 %, travel 0.5 %, electricity 0.15 %.
- Siting: the ILP optimum moves by at most 0.41 USD (0.063 %) on any seed; the baseline by -9.1 % to +5.8 % (mean -1.6 +/- 3.6 %, interval contains 0); gap difference grid - busiest -1.3 +/- 2.6 points (not significant).
- Relaxed ILP buys no electricity in 20/20 runs; the written ILP charges 0.82 kWh only to meet (17)-(18) at 0.27-0.28 USD. Per-instance gap tracks baseline lateness at r = 0.98; ILP CV 2.8 %.
- Demand realism vs synthetic `usd4h`: cuisine L1 to Kaggle 0.149 vs 0.277, about 32 restaurants per seed vs 8, 8-11 NTAs hit, zone-share L1 to the ACS law 0.14; route length 1.80 vs 1.86 km (same grid physics).
- Solver: 40/40 OPTIMAL, 553 k binaries, 45.5 +/- 3.2 s, 37/40 at the root; 25.3 min wall. PRUNING_NYC still restricts only the ILP, so the gaps remain lower bounds.

### 2.5 Round 1 / round 2 / round 3 comparison

| item | round 1 (2026-10-11) | round 2 (2026-10-12) | round 3 (2026-10-12/13) |
|---|---|---|---|
| cost units | toy: P 100, w 12/h, kappa 1/km | USD `usd_sunk`: P 30, w 18 $/h, v 36, kappa 0.12 $/km | unchanged |
| instances | 10 bikes / 2 h / 30 orders, q0 7.5-8.7 | 6 bikes / 4 h / 36 orders, q0 4-7 | unchanged family, seeds E2u 0-9, E3u 0-4, E4u 0-5, E8 0-9 |
| service-level variant | lexicographic (toy: 12.5) | lexicographic, 14.9 %, stage 1 certified on 5/15 (not citable) | (33) zeta 0.90 main / 0.85 sensitivity; zeta 0.90 premium 0.2 % (x0.75) / 5.5 % (x1), infeasible at x1.5 (max share 0.74-0.83) |
| E2 headline gap | 24.0 % +/- 8.7 (n = 15) | 21.9 % +/- 8.1 (n = 15) | **29.6 % +/- 5.6** (n = 30); seeds 0-4 reproduce 21.9 exactly, seeds 5-9 37.2 +/- 6.2 |
| E2 by demand x0.75 / x1 / x1.5 | 4.3 / 29.6 / 38.2 % | 6.9 / 21.3 / 37.3 % | 15.4 / 31.2 / 42.1 % |
| E2 mean totals baseline / ILP | - | 1022 / 727 USD | 1167 / 746 USD |
| gap composition | 90 % unserved, 9 % lateness, 1 % travel | 54 % lateness, 25 % response, 20 % unserved | 59 % lateness, 32 % response, 8 % unserved, < 1 % travel + electricity |
| price of end targets (17)-(18) | all of the transfer value | a few USD; relaxed control 19.0 % as recorded (one cell stuck) | 0.34 USD per instance (E2u), 0.27-0.28 (E8); relaxed control 29.6 %, 30/30 OPTIMAL |
| E3 value of transfers (b) / (c) | 257 / 254.5 toy units | 6.6 / 12.6 USD written (n = 1-2), 0 relaxed | 8.6 +/- 10.1 / 8.6 +/- 10.1 USD written (lower bounds, upper 22.2), 0.00 relaxed on 15/15 pairs (n = 5) |
| E3 cost of separation (b) / (c) | +55.4 / +97.9 (40 fixed) | +52.4 / +81.7 USD (29 / 58 fixed) | +52.2 +/- 1.6 / +81.4 +/- 1.6 written; +29.3 / +58.5 relaxed (= F_hub) |
| E3 ILP vs baseline NONE (a) / (b) / (c) | 48 / 37 / 36 % | 24 / 21 / 20 % (2 seeds) | 21.3 +/- 11.3 / 18.4 +/- 10.6 / 17.8 +/- 10.4 % (n = 5) |
| REORDER_POINT rule | beneficial in separated layouts (+115-220) | harmful everywhere, +143 to +302 USD | harmful everywhere, +165 to +207 USD mean, CIs exclude 0 |
| E4 ILP battery knee | 2 per site (stressed state) | none, 1 suffices (+0.14 USD for 1 -> 2) | none; +0.35 +/- 0.34 USD operational for 1 -> 2, then <= 0.09; total -0.25 to -0.31 beyond 2 |
| E4 baseline battery knee | > 6 | 2-3 (+48.5 USD for 1 -> 2, n.s.) | 2 (+44.2 +/- 21.6 USD for 1 -> 2, significant; +6.1 +/- 10.8 for 2 -> 3) |
| E4 headline gap at default size | - | 22.5 % +/- 21.3 (n = 3) | 24.6 % +/- 12.0 (n = 6) |
| E4 free sizing | buys 1 battery per site | 3-4 batteries / 2-3 chargers, saves 1.3-1.6 USD | 3.5 / 2.8, saves 1.43 +/- 0.18 USD; P sweep and 20-cell B x C grid solved (all flat) |
| E8 nyc4h gap (busiest / grid) | none | 36.5 % +/- 29.3 / 34.3 % +/- 37.6 (n = 3) | 31.8 % +/- 8.2 / 30.5 % +/- 8.6 (n = 10) |
| coverage | - | 15 E3u cells skipped, E4u P sweep and B x C cells unsolved | all cells solved, 0 SKIPPED_BUDGET in all four scripts |
| solver | 0.66-1.04 M binaries, 15-30 s (Threads 4) | 0.9-1.5 M, about 90 s at 150 s limit | 0.89-1.58 M, 143 s mean at 300 s limit (concurrent runs); E8 553 k, 46 s |

## 3. Interpretation

1. **The value of coordination is robust to the seed sample, and larger than round 2 said.** On 10 seeds the written E2 ILP saves 29.6 % +/- 5.6 of the rule baseline's cost per 4 h window and is cheaper on every one of the 30 instances. The jump from 21.9 % comes entirely from the baseline side: the round-2 subset is reproduced exactly, and the five new seeds are instances on which the myopic policy's lateness explodes (baseline CV 15-22 % vs ILP CV 4-5 %; gap vs baseline lateness r = 0.91). The same pattern appears in E8 (ILP CV 2.8 %, r = 0.98) and in E4u (baseline CI +/- 172 USD vs +/- 23 USD for the ILP). The composition is stable across E2u, E4u and E8: lateness about 59 %, response 32-35 %, unserved orders 6-8 %, travel plus electricity under 1 %. The ILP's lever is sequencing and dispatching, not coverage: both methods drop orders at P = 30 USD, and the ILP sometimes drops more (8 of 30 E2u instances, 5 of 20 E8 instances) because a drop is cheaper than a late delivery.
2. **The service level can now be stated cleanly.** A 90 % service guarantee costs 0.2 % of the optimal cost at x0.75 and 5.5 % at x1 (37 USD per instance, binding on 8 of 10 seeds), with the saving against the baseline still 27.8 % at x1; at zeta 0.85 the constraint is essentially free (binding on 2 of 20 feasible instances). At x1.5 both levels are infeasible on every seed because 54 orders in 4 h exceed what 6 bikes can deliver under any schedule (maximum feasible share 0.74-0.80 certified, at most 0.83 by bound). The lexicographic column of round 2 is superseded and should not be cited; where it was certified its solutions coincide with the zeta-0.90 cells.
3. **The end-of-horizon targets are worth almost nothing in the cost optimum** (0.34 USD per E2u instance, 0.27-0.28 USD in E8, relaxed control solved to optimality everywhere), so none of the coordination value comes from stock or energy management. Yet rho / R_end remain the only source of transfer value in E3u: under the written targets the separated layouts use exactly one 2-battery shuttle per run to lift the 4-swap cap imposed by (17)-(18) (8.6 +/- 10.1 USD, a lower bound); under relaxed targets 0 shuttles on all 15 pairs. The battery side of the model (charging, grid, transfers, station capital) is correct but still not binding on this family: hub peak 1.33 kW, sites at most 3.33 kW, electricity under 1 USD, the relaxed ILP never buys a kWh in E8, and the free-size ILP keeps 3-4 spares and 2-4 chargers network-wide for a 1.43 USD gain.
4. **Station capital is the baseline's lever, not the ILP's.** The first extra spare per site is worth 44.2 +/- 21.6 USD per window to the baseline (now significant with n = 6) and 0.35 USD to the ILP; chargers and site power are worth nothing to either; the gap is largest exactly where stations are lean (35.7 % at B_j = 1, 33.5 % at the ILP-chosen sizes), and on half the seeds the baseline never reaches the ILP's served share at any B_j <= 6.
5. **Round 3 changed coverage and certainty, not conclusions.** Every round-2 point estimate lies inside the new intervals (E3u separation cost within 1-2 USD, E8 36.5 % inside 31.8 +/- 8.2, E4u 22.5 % inside 24.6 +/- 12.0); the CIs halved or better; the layout ranking (a) < (b) < (c), the harmfulness of REORDER_POINT and the siting insensitivity of the ILP hold on every seed. The one solver-bound item is the separated / written / transfers-free E3u cell type, which stays at a 1.8-2.0 % gap after 600 s, so the written transfer value is an interval [8.6, 22.2] rather than a number.

## 4. What to change next (by priority)

1. **Fleet-size sweep at x1.5** (cheap): how many bikes make zeta 0.90 feasible at 54 orders and at what cost; this turns "infeasible with 6 bikes" into a capacity curve for the paper.
2. **Cheaper zeta design**: run `min sum u` first on every instance and skip the zeta solve whenever the target exceeds the certified bound; about 2.5 h of the 4.4 h E2u wall went to 18 x1.5 zeta solves that never found an incumbent (no MIP start satisfies (33)) followed by max-service solves. Also solve the relaxed-target maximum share (the current bound is for the written constraint set; the difference is unlikely to exceed one order).
3. **Certify the E3u written transfer value**: the separated / written / transfers-free cells do not close with more time (gap unchanged from 300 s to 600 s); a tighter formulation (e.g. valid inequalities on the swap cap, or fixing the single shuttle) is needed rather than more seeds or minutes.
4. **Fix the script conventions** before the paper tables are produced: exact t quantiles instead of z = 1.96 in `improvement.csv` / figures (E2u); `zeta_feasibility.csv` should count TIME_LIMIT max-service cells whose bound already exceeds the allowance as infeasible; the E3u `--analyse` crash (`int(NaN)` on reused rows); the E4u pooled C-sweep seed-set artefact; empty `served_share_servable` for ILP rows in E8.
5. **Larger instances** (8-10 bikes, usd4h_large) and the lossless `--targets default` probe for nyc4h, so that the station side can start to bind and the E8 gaps become exact instead of lower bounds.
6. **Complete the n = 3 sweeps**: E4u C and P sweeps on seeds 3-5 (cheap, both flat), to give every table the same seed set.
7. **Clean benchmark of solve times**: round-3 times were measured with four scripts running concurrently (E2u 143 s vs 90 s in round 2); rerun a handful of cells alone if solve time is quoted.
8. Carry-overs from round 2 that are still open: response-time reference (r_i vs a_i), periodic end condition vs rho / R_end, 8 h / rolling horizon, REORDER_POINT redesign, cuisine `other` mapping, real road network.

## 5. Decisions needed from the supervisor

1. Paper headline: quote 29.6 % +/- 5.6 (n = 30, 10 seeds) as the E2u value of coordination, with the per-level 15.4 / 31.2 / 42.1 %? The round-2 21.9 % is a subset of it, not a conflicting estimate.
2. Service level in the paper: present (33) at zeta 0.90 as a two-line statement (0.2 % premium at x0.75, 5.5 % at x1, unattainable at x1.5 with 6 bikes), with 0.85 as sensitivity? Drop the lexicographic variant entirely?
3. Fleet-size sweep at x1.5 (item 4.1): run it now, or leave x1.5 as "beyond fleet capacity"?
4. Baseline (17)/(18) violations (E2u 5-6 of 30 runs, E8 4-5 of 20) remain reported, not priced: accept the conservative headline, or switch the headline comparison to `baseline_reserve`?
5. E3u written transfer value: report the interval [8.6, 22.2] USD with the relaxed value 0, or invest in a tighter formulation to certify it?
6. Confidence-interval convention: exact t quantiles (all `RESULTS_final.md`) vs z = 1.96 (script figures); the figures would be regenerated if t is chosen.
7. Annualised values in E4u (x 1460 windows, every window like the dinner peak) are an upper-bound convention: keep, or scale by a daily profile?
8. Keep the round-2 output directories (`e2u_coord_usd`, `e3u`, `e4u_sizing_usd`, `e8_nyc_fixed`) in the public repository as superseded-but-reproducible, or archive them?
9. Still open from round 2: periodic end condition, r_i vs a_i response reference, 8 h / rolling horizon, REORDER_POINT redesign, DECISIONS / cost-calibration edits (bB split, group-quarters note).

## 6. File locations

| content | path |
|---|---|
| decisions (R3.1-R3.3, after R2 and the implementation notes) | `notes/DECISIONS.md` |
| round-3 report JSON (E3u / E4u / E8 headline numbers, anomalies, interpretation) | `notes/workflow8_round3_reports_a.json` |
| E2u coordination value + service-share constraint (10 seeds) | `ebike_swap_sim/outputs/e2u_round3/RESULTS_final.md` (records.jsonl, results.csv, improvement.csv, zeta_feasibility.csv, instances/, 4 figures: gap_by_demand, zeta_premium, cost_components, drop_rates) |
| E3u transfers and separation (5 seeds, 60/60 cells) | `ebike_swap_sim/outputs/e3u_round3/RESULTS_final.md` (records.jsonl, results.csv, 9 figures; report built by `experiments/e3u_round3_report.py`) |
| E4u station sizing (6 seeds, P sweep and B x C grid solved) | `ebike_swap_sim/outputs/e4u_round3/RESULTS_final.md` (records.jsonl, results.csv, summary_*.csv, spares_to_match.csv, gap_decomposition.csv, _analysis_final.json, 5 figures) |
| E8 NYC semi-real (10 seeds, 2 sitings) | `ebike_swap_sim/outputs/e8_round3/RESULTS_final.md` (records.jsonl, results.csv, per_instance.csv, siting.csv, demand_comparison.json, instances/, 4 figures incl. map_seed0.png) |
| experiment scripts | `ebike_swap_sim/experiments/{e2u_round3,e3u_round3,e4u_round3,e8_round3}.py`, `e3u_round3_report.py`; `experiments/common.py` (`ILP_PARAMS_R3`, `run_zeta_case`, `max_service_share`, `reusable_ilp_row`); tests in `ebike_swap_sim/tests/test_round3.py` |
| round-2 reports (superseded by the round-3 directories, kept for provenance) | `ebike_swap_sim/outputs/{e2u_coord_usd,e3u,e4u_sizing_usd,e8_nyc_fixed}/RESULTS_final.md` |
| code | `ebike_swap_sim/` (README.md, CONTRACT.md) |

The script-written `RESULTS.md` in each round-3 directory is intermediate (E3u: an English stub after the `--analyse` crash; E8: abstract rewritten in English); `RESULTS_final.md` is the deliverable in each.

---

# Round 4 (2026-10-14): bi-level station siting (E9)

Round 4 again **did not change any of E2's mathematics** (`ilp.py`, `arcs.py`, `evaluate.py` unchanged apart from the `model / prefix / facility_vars / set_objective` hooks of `ILPModel` that let several E2 sub-models share one Gurobi model; toy 12.5 / 11.2 / 106 still reproduced). It adds an upper level on top of E2: a planner that chooses station locations, roles and sizes, with the E2 operations ILP as the lower level. Design: `notes/bilevel_siting_design.md` (plus the relaunch addendum); binding conventions: `notes/DECISIONS.md`, "E9 relaunch decisions" (E9R.1-E9R.4). Code: `ebike_swap_sim/sites_nyc.py`, `ebike_swap_sim/bilevel.py`, `experiments/e9_bilevel_siting.py`, `tests/test_bilevel.py` (22 tests; 158 in the suite). Consolidated report: `ebike_swap_sim/outputs/e9_bilevel/RESULTS_E9.md`; authoritative numbers in the six sub-reports `outputs/e9_bilevel/{validate,sweep,roles,deck,access,cross}/RESULTS_final.md`. The first launch (`outputs/e9_bilevel/_first_attempt/`) is superseded; section 3 records what went wrong.

## 1. What was done

### 1.1 The question and the bi-level model

The proposal asks where in Midtown swap / charge stations should go, which kind, and how big, for a fleet whose daily operations are run by the E2 coordinator. Upper level (planner): among 12 candidate locations (`sites_nyc.candidate_sites()`: the six busiest restaurant cells L01-L06, three grid-connected landmarks L07-L09, three NTA zone centres L10-L12; `outputs/e9_bilevel/candidates.csv`), choose which to open, with which role (S swap-only, C charge-only hub, SC co-located) and size (B spares, C chargers), under the investment budget (33a) of m x 52,150 USD (one unit = Fhat 50,000 + 3 bhat 450 + 2 chat 400). Lower level (coordinator): the written E2 ILP with the facilities fixed, one solve per demand scenario (seed of the instance generator). Planner value `V = sum_j (F_j y_j + bB B_j + bC C_j) + sum_s p_s OPEX_s`, i.e. window-allocated setup plus expected operating cost. Because both levels minimise the same cost the problem is optimistic bi-level and collapses to one two-stage stochastic ILP (the exact benchmark); it is genuinely bi-level when the planner adds rows the operator does not price (the access row [U4]) or evaluates layouts under another operating policy (algorithm E).

### 1.2 Family `nyc4h_stress2` (E9R.2)

6 bikes / 36 orders / H 48 (4 h), `q0 ~ U{3..6}` of 12 levels (25-50 %), one spare / one charger / `Cbar 4` per default site, `P_j = 2.8 kW` per site, flat 4 kW grid group, `usd_sunk` prices, bikes start at the three busiest cells, demand byte-identical across layouts of a scenario. Size menu: S `B in {1, 2, 3}`, SC `B in {1, 2, 3} x C in {1, 2}`, hubs `C in {2, 4}`. Admissibility rule: a swap-only site only next to a charge-capable object (otherwise it is dead stock). Sanity bar: one SC:B3:C2 site serves >= 0.70 under the baseline policy (0.75-0.86 on seeds 0-2) and 0.85 under the ILP.

### 1.3 Algorithms and sub-experiments

(A) integrated stochastic ILP (shared `y, B, C`, one E2 sub-model per scenario); (B) exhaustive enumeration with a superset bound and scenario-by-scenario pruning; (C) greedy + local search: start = best singleton by lower-level V (per-role baseline screen keeping the top-5 moves per role, all priced by the ILP; exhaustive singletons as fallback), additions ranked by gain per investment dollar, local search with swap / size +-1 / role-flip moves (3 passes), a 50 % served-share guard, wall exhaustion reported as a status; (D) the proposal deck's spin-and-adjust heuristic (open the k = m sites with the most baseline swaps, size by swap demand, 3 iterations, no ILP during the search); (E) cross-evaluation of every chosen layout under the ILP, the baseline policy and the relaxed-target ILP on 5 seeds (0-2 in-sample, 3-4 out-of-sample). Access row [U4] (every NTA demand zone within D blocks of an open swap-capable site, D = 8 / 12 blocks = 1.2 / 1.8 km) in repair-and-report mode. Reposition targets: `all_candidates` libraries in the validation (so that (A) and (B) price the same arcs), per-layout `open_sites` libraries (E8 convention) in the search runs; every ILP value is therefore an upper bound on the written E2 optimum.

| sub-experiment | what | size | solver coverage | wall |
|---|---|---|---|---|
| E9.1 `validate/` | (B) vs (A) | 4 candidates L01-L04, 2 seeds, m = 1, menu B <= 2 | 8 layouts (6 solved, 2 pruned), 14 lower-level solves: 9 OPTIMAL, 5 TIME_LIMIT at 0.8-1.6 % gap; integrated 1.50 M variables, 600 s | 44.7 min |
| E9.2 `sweep/` | (C) per budget, Pareto curve, (A) as bound | 12 candidates, 3 seeds, m = 1..4, full menu | 29 layouts, 87 solves all OPTIMAL; 4 integrated runs at TIME_LIMIT (5.35 M variables, no usable bound) | 133 min |
| E9.3 `roles/` | role sets {SC}, {S, SC}, {S, C, SC} | 12 candidates, 3 seeds, m = 2, 3 | 28 layouts, 84 solves all OPTIMAL | 87 min |
| E9.4 `deck/` | (D) vs (C) | 12 candidates, 3 seeds, m = 1..4 | 10 baseline iterations, 12 ILP solves all OPTIMAL | 9.5 min |
| E9.5 `cross/` | (E) on 7 chosen layouts | 5 seeds | 105 evaluations; 66 of 70 ILP evaluations OPTIMAL, 4 TIME_LIMIT on L02:SC:B2:C1 | 56 min |
| E9.6 `access/` | [U4] at D = 8 / 12 | 12 candidates, 3 seeds, m = 2, 3 | 112 new solves (111 OPTIMAL); D = 8, m = 3 truncated by the 120 min wall | 140 min |

Gurobi 13, Threads 3, Seed 0, TimeLimit 300 s per lower-level solve (600 s with hubs), 600 s for the integrated model; shared lower-level cache (`outputs/e9_bilevel/cache/`, version `e9-2`, 2,329 schedule files); about 7.9 h in total, three processes in parallel. Baseline-policy screening runs take milliseconds (1,449 in the sweep, 1,446 in roles, 2,088 in access).

## 2. Results

Layout keys read `location:role:B<spares>:C<chargers>`; V in USD per 4 h window = allocated setup + expected opex over the scenarios.

### 2.1 E9.1 validation (`validate/RESULTS_final.md`)

| method | layout | V | note |
|---|---|---|---|
| exhaustive enumeration (B) | L02:SC:B2:C1 | 676.223 | 8 admissible single-site layouts, 6 solved on both seeds, 2 pruned by the superset bound |
| integrated stochastic ILP (A) | L02:SC:B2:C1 | 676.223 | agreement to 3e-13; bound 668.04 after 600 s (gap 1.21 %, one node, no improvement on the MIP start) |
| per-layout Gurobi bounds | - | optimum in [671.13, 676.22] | one-spare vs two-spare separation (>= 48 USD, served 0.68 vs 0.79-0.82) certified; ranking among L01 / L02 / L03 at two spares (676.2 / 679.6 / 680.9) inside the solver gaps |

E9.1 validates the machinery, not the number: on the full menu and five seeds L02:SC:B2:C1 is the worst of the seven chosen layouts (section 2.6).

### 2.2 E9.2 budget sweep (`sweep/RESULTS_final.md`; figures `map_sites_final.png`, `pareto_final.png`, `greedy_trajectory_final.png`)

| m | budget USD | layout | investment used | unspent | V | setup / opex | served share |
|---|---|---|---|---|---|---|---|
| 1 | 52,150 | L02:SC:B3:C2 | 52,150 (100 %) | 0 | 654.377 | 13.19 / 641.19 | 0.852 |
| 2 | 104,300 | L02:SC:B4:C2 | 52,600 (50 %) | 51,700 | 654.525 | 13.52 / 641.00 | 0.852 |
| 3 | 156,450 | L02:SC:B4:C2 | 52,600 (34 %) | 103,850 | 654.525 | 13.52 / 641.00 | 0.852 |
| 4 | 208,600 | L02:SC:B4:C2 | 52,600 (25 %) | 156,000 | 654.525 | 13.52 / 641.00 | 0.852 |

- L02 = busiest restaurant cell 2 (72 restaurants, W 29th-30th / 6th Ave, NoMad). Operating detail of the chosen layout: 30.67 of 36 orders served, 1.67 late (6 USD), unserved penalty 160 USD (5.33 x 30), response 462.5 USD, travel 11.9 USD, electricity 0.56-0.75 USD (1.7-2.4 kWh), no transfers; the site is out of full batteries 12-41 of 48 slots per scenario, yet the coordinator times its six swaps (one per bike) around the charging cycle.
- Why a second site never pays: 15-16 second-site additions to the best singleton L01:SC:B3:C2 (655.06) and 5 more next to L02:SC:B4:C2 all raised V, by +11.85 to +12.21 USD (S / SC) and +29.35 USD (hubs C = 2 at L02-L06); allocated setup of a second site 12.0-13.2 USD (S / SC) or 29.19 + 0.16 USD (hub); best operating saving of any second site 1.09 USD (0.17 %, L01:SC:B3:C2 + L10:SC:B3:C2, opex 640.78). Unserved (160 USD) and response (462.5 USD) are identical for every layout with B >= 3.
- Pareto curve of investment vs expected opex: one point plus the 450 USD fourth spare; doubling the investment from 52 k to 104 k USD buys at most 1.09 USD per window. A third charger or a fifth spare at L02 is idle (opex unchanged, setup +0.08 / +0.33 USD).
- Integrated model: 5.35 M variables (4.96 M binaries, 465 k rows), accepted the greedy's layout as incumbent at all four budgets, no usable bound in 600 s (`-inf` at m = 1 because the root LP did not finish, -12,549 at m = 2..4). The auto-generated `pareto.png` draws that meaningless bound; `pareto_final.png` omits it.

### 2.3 E9.3 role sets (`roles/RESULTS_final.md`; figures `roles_priced_moves.png`, `roles_components.png`, `roles_map.png`)

| role set | m = 2 | m = 3 | V | served | transfers used |
|---|---|---|---|---|---|
| {SC} | L02:SC:B4:C2 | L02:SC:B4:C2 | 654.525 | 0.852 | 0 |
| {S, SC} | L02:SC:B4:C2 | L02:SC:B4:C2 | 654.525 | 0.852 | 0 |
| {S, C, SC} | L02:SC:B4:C2 | L02:SC:B4:C2 | 654.525 | 0.852 | 0 |

Forcing co-location costs 0.00 USD, allowing hubs gains 0.00 USD. Hubs were priced five times and gave byte-identical opex to the parent (`transfers_used = 0` in all 84 solves although 14-16 shuttle services existed): a hub costs exactly its setup (+29.4 USD). Swap-only additions cost +12.4-13.0 USD and contribute only their 1-3 initial spares (worth 0.18-1.02 USD). The E3u finding "hub = +F_hub, transfers worth 0-9 USD" reappears in its extreme form (transfers worth exactly 0). The hub cost sensitivity (F_hub 12.03 instead of 29.19) was not run and is not needed: a hub with unchanged opex enters only at negative setup.

### 2.4 E9.4 deck heuristic regret (`deck/RESULTS_final.md`; figures `deck_vs_bilevel_final.png`, `map_deck_vs_bilevel.png`, `deck_demand_proxy.png`)

| m | deck layout | deck V | bi-level V | regret USD | regret % | extra setup of the deck |
|---|---|---|---|---|---|---|
| 1 | L01:SC:B3:C2 | 655.06 | 654.38 | 0.68 | 0.10 | 0.00 |
| 2 | L01:SC:B3:C1 + L02:SC:B4:C1 | 667.08 | 654.53 | 12.56 | 1.92 | 13.03 |
| 3 | L01:SC:B4:C1 + L02:SC:B4:C1 + L04:SC:B3:C1 | 680.06 | 654.53 | 25.53 | 3.90 | 26.47 |
| 4 | L01:SC:B4:C1 + L02:SC:B5:C1 + L04:SC:B3:C1 + L06:SC:B3:C1 | 693.31 | 654.53 | 38.78 | 5.93 | 39.91 |

At m = 1 the two planners agree on role and size and differ only between two adjacent cells (L01 vs L02, a tie on the demand proxy of 1.67 swaps each). From m = 2 the regret is the setup of the extra sites minus 0.5-1.1 USD of operating saving; served share, lateness and unserved penalty identical. Priced by the baseline policy the same deck layouts cost 1025-1072 USD (34-39 % more than under the ILP) and the policy ranks the two-site layout best, so a planner evaluating designs with the myopic policy over-builds.

### 2.5 E9.6 access row [U4] (`access/RESULTS_final.md`; figures `access_map.png`, `access_coverage.png`, `access.png`, `access_search.png`)

| m | variant | layout | investment | V | delta V | served | zones covered of 11 | mean / max blocks to site |
|---|---|---|---|---|---|---|---|---|
| 2, 3 | no access | L02:SC:B4:C2 | 52,600 | 654.525 | - | 0.852 | 5 (D 8) / 8 (D 12) | 11.65 / 22 |
| 2 | D = 8 | L02:SC:B4:C1 + L05:SC:B1:C1 | 103,050 | 666.605 | +12.08 (+1.85 %) | 0.852 | 8 | 8.52 / 15 |
| 3 | D = 8 (truncated) | L02:SC:B4:C2 + L05:SC:B1:C1 + L08:S:B1:C0 | 153,900 | 678.906 | +24.38 (+3.73 %) | 0.852 | 9 | 7.41 / 15 |
| 2, 3 | D = 12 | L02:SC:B4:C1 + L05:SC:B1:C1 | 103,050 | 666.605 | +12.08 (+1.85 %) | 0.852 | 11 | 8.52 / 15 |

The cost of access is the allocated fixed cost of each extra site (12.36-12.44 USD), of which 0.28-0.43 USD comes back as shorter rider detours; the served share does not move. At D = 12 (1.8 km) two sites cover all 11 zones and the third budget unit stays unspent. At D = 8 (1.2 km) zone MN0801 is beyond 8 blocks of every candidate (full coverage infeasible for every layout), MN0202 and MN0701 each have a single candidate in reach (L08, L06), and the m = 3 search was cut by the 120 min wall inside the second repair round with MN0701 still uncovered (the L06 option and the covering polish were never priced). Candidates that enter only because of the access row: L05 (Rockefeller south, always) and L08 (Union Square, D = 8, m = 3); no zone-centre candidate (L10-L12) is ever chosen.

### 2.6 E9.5 cross-evaluation (`cross/RESULTS_final.md`; figure `cross_eval_final.png`)

| layout | chosen by | V ILP | V baseline | regret ILP | regret baseline | ILP vs policy gap |
|---|---|---|---|---|---|---|
| L02:SC:B3:C2 | greedy + LS m = 1 | 654.49 | 1026.24 | 0.00 | 47.37 | 36.2 % |
| L01:SC:B3:C2 | deck m = 1 | 654.65 | 1022.26 | 0.16 | 43.39 | 36.0 % |
| L02:SC:B4:C2 | greedy + LS m = 2, 3; all role sets | 654.64 | 978.87 | 0.15 | 0.00 | 33.1 % |
| L01 + L02 (deck m = 2) | deck | 666.91 | 991.36 | 12.42 | 12.49 | 32.7 % |
| L01 + L02 + L04 (deck m = 3) | deck | 679.85 | 986.31 | 25.36 | 7.44 | 31.1 % |
| L01 + L02 + L04 + L06 (deck m = 4) | deck | 693.10 | 1006.16 | 38.61 | 27.29 | 31.1 % |
| L02:SC:B2:C1 | validate (restricted menu) | 662.79 | 1129.47 | 8.30 | 150.61 | 41.3 % |

- Location robust: every method and both policies put the single site at L02, with L01 a tie (+0.16 USD for the ILP, 4 USD better for the policy); among eight single sites priced as SC:B3:C2 the spread is 4.2 USD (0.6 %): L02 654.4, L01 655.1, L05 655.2, L07 655.7, L08 657.0, L11 658.5.
- Size not robust: the coordinator is indifferent between 3 and 4 spares (0.15 USD) while the policy values the fourth spare at 47.4 USD per window (4.8 %) because it runs the site dry; both agree two spares are too few (+8.3 / +150.6 USD). Cross-regret asymmetric: the policy's best layout costs the coordinator 0.15 USD, the coordinator's best costs the policy 47.4 USD.
- The ILP beats the baseline policy by 31.1-41.3 % of the policy's cost on every layout (306-467 USD per shift), 53-60 % of it lateness (15-18 late orders vs 1.4-1.8). In-sample (seeds 0-2) vs out-of-sample (seeds 3-4) ILP opex differs by -0.3 to +4.2 USD (no over-fit); the baseline swings by 74-128 USD between the subsets. Relaxed end-of-horizon targets are worth 0.02-0.42 USD on layouts with B >= 3 and 1.38 USD at B = 2.

### 2.7 Solver facts

- Lower-level E2 ILP (6 bikes, 0.5-0.8 M arcs with `open_sites` targets): OPTIMAL in 11-150 s on the search runs (sweep mean 29 s, max 75 s; roles mean 28 s, max 66 s; cross 11-148 s, growing with the number of open sites; access mean 35 s, max 185 s). Two-spare layouts are the slow ones: all 5 TIME_LIMIT solves of the validation and all 4 of the cross run are on B = 2 layouts. The 8-bike first-attempt family needed 2.2-2.4 M arcs and routinely hit 300 s.
- Integrated stochastic ILP: 1.50 M variables on the validation protocol (bound 668.04, gap 1.21 % in 600 s); 5.35 M variables at 12 candidates x 3 scenarios, where it returned only its warm start and no usable bound. At this size it is an incumbent checker, not a certifier.
- Coverage: no ERROR, no infeasible layout, no LOW_SERVICE row in any sub-experiment. Search limits: no three-site layout was ever priced by the greedy (no two-site layout beat the singleton), hubs with C = 4 and hubs at L07-L12 were never priced, and only the top-5 moves per role by the baseline screen reach the ILP (the screen ranks sizes the wrong way round: it prefers more spares and put the eventual best singleton L02 6th).

## 3. The first attempt and its lesson (superseded; `outputs/e9_bilevel/_first_attempt/README.md`, DECISIONS E9R.1)

The first launch ran on the 8-bike family `nyc4h_stress` (8 bikes / 48 orders, `q0 ~ U{2..4}`). Four failures: (i) the roles run reported "no feasible layout" for {S, SC} and {S, C, SC} because the 4500 s wall budget was exhausted after the {SC} search and every later lower-level price returned `SKIPPED_BUDGET`, which the greedy mapped to an infinite value; (ii) the access run reported "no feasible layout" because [U4] was enforced on every intermediate layout, including the singletons of the first step, and no single candidate covers all zones; (iii) the sweep and the no-access control chose L03:S:B1:C0, a swap-only site with one spare serving 7 % of the orders, because the baseline-policy screen (which serves orders at a loss where the ILP drops them) valued one-spare swap-only sites at 1462-1480 against 1631+ for co-located sites, so only S:B1 singletons were priced, and no served-share guard existed; (iv) lower-level solves of 2.2-2.4 M arcs hit 300 s. Only `validate/` (6 bikes, 4 candidates) was sound and agreed (A) = (B). Fixes (E9R.2-E9R.4): the lighter family `nyc4h_stress2`; swap-only sites admissible only next to a charge-capable object; start = best singleton by lower-level V with a per-role screen and a 50 % served-share guard; wall exhaustion reported as `wall budget exhausted` with `search_complete = False`, never as infeasibility; exceptions as `ERROR` rows; the access row as repair-and-report; per-layout `open_sites` libraries. All covered by regressions in `tests/test_bilevel.py`. **Lesson:** a cheap screening policy that values facilities differently from the ILP can silently steer the search, and every failure mode of the evaluator must be surfaced as a status, never folded into the objective.

## 4. Interpretation

1. **One well-stocked co-located station is the whole infrastructure on this family.** Every method (enumeration, integrated ILP, greedy + local search, all three role sets) opens a single SC site at L02 with 3-4 spares and 2 chargers, V about 654 USD per window, 85.2 % served; budgets beyond one unit stay unspent (51,700 / 103,850 / 156,000 USD). A second site of any role costs 11.9-12.2 USD (S / SC) or 29.4 USD (hub) of allocated setup against at most 1.09 USD of operating saving.
2. **The structural reason is that the fleet binds, not the batteries.** Under the ILP the served share is 0.852 (0.856 on five seeds), lateness 1.7-1.8 orders and the unserved penalty 160 USD for every layout with at least three spares, from one site to four; siting and sizing move only travel (11.8-12.4 USD) and electricity (0-0.8 USD). The family makes station siting bind for the myopic policy (47 USD for the fourth spare, 151 USD for the third) but still not for the coordinator, so the upper level carries little information beyond "one site, B >= 3".
3. **Hubs and swap-only satellites are never used** because the coordinator never moves a battery between stations within a 4 h window (0 transfers in 84 of 84 solves), consistent with E3u (transfers worth 0 under relaxed targets, at most 22 USD under written ones). A hub is priced exactly at its rent.
4. **The deck's one-station-per-budget-unit rule over-builds by its sunk cost** (regret 0.1 / 1.9 / 3.9 / 5.9 % at m = 1..4, almost exactly the setup of the extra sites), and a planner that prices layouts with the myopic policy over-builds further (the policy ranks the two-site layout best).
5. **Location is policy-robust, size is not.** Both operators put the station at L02 (L01 a tie); the coordinator values the fourth spare at 0.15 USD, the policy at 47.4 USD. Stations should be sized for the operator that will actually run the fleet.
6. **Spatial access is a planner's purchase, not a service lever**: every zone within 1.2-1.8 km of a swap point costs about 12 USD per window per extra site (L05, then L08), shortens rider detours (mean 11.6 -> 8.5 blocks) and leaves the served share unchanged.
7. **Certification is partial.** Exact agreement (A) = (B) holds on the small validation protocol; at full size the integrated model gives no bound, so the m = 2..4 answers are heuristic incumbents justified by the exhaustive pricing of every single-site move and the flat Pareto frontier, not by a gap.

## 5. Next steps (by value)

1. A deeper energy-stressed family in which the second site changes who gets served: more bikes per site, lower q0, a longer window, or fewer spares per site (B = 2 is the only size at which the ILP reacts).
2. More candidates across Manhattan: the Midtown box is 2 x 3.5 km, so every candidate is within one detour of every order.
3. A rolling-horizon or multi-day lower level, where charging turnover and end-of-day stock give chargers and hubs a role.
4. Policy-aware siting: the upper level evaluated under the policy that will run the fleet (algorithm E as the follower); and the integrated model with hard [U4] rows at D = 12, m = 2, warm-started from L02 + L05, as the exact access benchmark.
5. Cheap fixes: seed budget m's local search with the results of all lower budgets (removes the 0.15 USD non-monotonicity); canonical keys so that `SC:B1:C0` and `S:B1:C0` are priced once (6 wasted solves); price L02 + L05 + L06 and L02 + L06 + L08 directly to settle the D = 8, m = 3 question in six solves; persist local-search histories (now reconstructed from the logs); extend the enumeration menu to B = 4.

## 6. Decisions needed from the supervisor

1. Is "one co-located station at L02 with 3-4 spares and 2 chargers; nothing else pays" an acceptable answer to the proposal's siting question for the paper, with the structural explanation (fleet binds) stated alongside, or should the siting experiment be re-run on a family where the station side binds for the coordinator (item 5.1) before anything is written up?
2. Which operator should the station be sized for in the paper: the coordinator (3 spares, 654.38) or the rule-based policy (4 spares, 450 USD more, worth 47 USD per window to it)?
3. Report the m = 2..4 results as heuristic incumbents without a certified gap (current state), or invest in a bound (a decomposition of the integrated model, or an enumeration of all two-site layouts, about 66 x 3 solves)?
4. Access requirement: keep D = 12 (feasible, +12 USD, 11/11 zones) as the headline and report D = 8 as infeasible for full coverage, or run the exact integrated access benchmark (item 5.4)?
5. Should the deck heuristic comparison appear in the paper as the proposal's own planner (regret 0.1-5.9 %), or only in the notes?
6. Keep `outputs/e9_bilevel/_first_attempt/` in the public repository as a documented superseded run, or archive it outside the repository?
7. Carry-overs from rounds 2-3 still open: periodic end condition, r_i vs a_i response reference, 8 h / rolling horizon, REORDER_POINT redesign, fleet-size sweep at x1.5.

## 7. File locations

| content | path |
|---|---|
| design note (+ relaunch addendum) | `notes/bilevel_siting_design.md` |
| binding decisions E9R.1-E9R.4 | `notes/DECISIONS.md`, "E9 relaunch decisions" |
| consolidated report | `ebike_swap_sim/outputs/e9_bilevel/RESULTS_E9.md` |
| E9.1 validation | `ebike_swap_sim/outputs/e9_bilevel/validate/RESULTS_final.md` (records.jsonl, results.csv, agreement.json, layouts_m1.png, map_validate_m1.png, solve_times_m1.png) |
| E9.2 budget sweep | `ebike_swap_sim/outputs/e9_bilevel/sweep/RESULTS_final.md` (records.jsonl, results.csv, pareto.csv, map_sites_final.png, pareto_final.png, greedy_trajectory_final.png; `pareto.png` and `map_budget_*.png` are auto-generated and superseded for reading) |
| E9.3 role sets | `ebike_swap_sim/outputs/e9_bilevel/roles/RESULTS_final.md` (roles_priced_moves.png, roles_components.png, roles_map.png, roles.png) |
| E9.4 deck heuristic | `ebike_swap_sim/outputs/e9_bilevel/deck/RESULTS_final.md` (deck_vs_bilevel_final.png, map_deck_vs_bilevel.png, deck_demand_proxy.png) |
| E9.5 cross-evaluation | `ebike_swap_sim/outputs/e9_bilevel/cross/RESULTS_final.md` (cross_eval.csv, cross_eval_final.png) |
| E9.6 access row | `ebike_swap_sim/outputs/e9_bilevel/access/RESULTS_final.md` (access_map.png, access_coverage.png, access.png, access_search.png) |
| candidates, launch plan, logs, lower-level cache | `ebike_swap_sim/outputs/e9_bilevel/{candidates.csv, candidates.json, launch2.json, logs/, cache/}` |
| superseded first attempt | `ebike_swap_sim/outputs/e9_bilevel/_first_attempt/` (README.md lists the four failures) |
| code | `ebike_swap_sim/ebike_swap_sim/{sites_nyc, bilevel}.py`, `ebike_swap_sim/experiments/e9_bilevel_siting.py`, `ebike_swap_sim/tests/test_bilevel.py` |

The script-written `RESULTS.md` in each sub-folder is intermediate; `RESULTS_final.md` is the deliverable in each, and `RESULTS_E9.md` names the source of every consolidated number.
