# Project understanding notes: NYC e-bike food-delivery battery swapping

Documents (chronological):

| File | Date | Content |
|---|---|---|
| `Ebike Battery Swap.pdf` | 9/4 | Project proposal slides: motivation, simulator architecture, research directions, public datasets |
| `Battery_Swap.pdf` | 9/29 | First MILP: rider routing + swap-station (swap and charging co-located) inventory, no inter-station transfers |
| `E2.pdf` | 10/5 | Extended ILP: swap facilities and charging facilities separated, battery logistics transfers, grid supply groups, platform labels |
| `E2+Example.pdf` | 10/7 | E2 text + toy example on pp. 10–15 (2 vehicles, 3 nodes, 3 orders, optimum J = 12.5) |

---

## 1. Proposal slides (Ebike Battery Swap.pdf)

**Motivation**: build a modular, data-driven agent-based simulator of the battery-swapping process for NYC e-bike food-delivery riders.
Platform (Grubhub, Uber Eats) order/trajectory data are unavailable, so only public data (population, land use, road network)
are used to generate demand, routes and charging/swapping behaviour. Core modules are pluggable: demand generation, rider behaviour, station siting, inventory/transfers, queueing/service, policy constraints.

**Research directions**: station siting (of interest to NYC DOT), battery-charging optimisation, swap-aware routing/dispatch, rider behaviour change.

**Simulator structure**: `OD Generator → Dispatch Model → Rider List / Station List`.

- The OD generator has three sub-modules:
  1. Time-dependent generator: order intensity by day of week and time of day, then sampling;
  2. Demographic destination sampling: destinations drawn by population, income, population type;
  3. Restaurant-type sampling: draw a cuisine first, then a restaurant within the area.
- Naive Dispatch: zone queues, assign to the nearest available rider.
- Naive Rider: state = availability, battery level, remaining delivery time. After accepting an order, go straight to the restaurant then to the destination; when battery is below a threshold go to a station to swap, wait if no battery is available.
  Assumes the threshold suffices to finish the longest OD and reach a station. Energy use depends on route length, grade and number of traffic lights.
- Naive Station: state = number of full batteries, remaining charging time of each battery. FCFS; queue if no full battery; a returned battery's charging time depends on its level, charged at maximum power.
- Expected output: given a station layout, run the simulation, identify stations with long queues and idle stations, iterate on the layout.
- Visualisation sketch (p. 10): riders coloured by battery level on a Manhattan map; a list of slot states for stations S1, S2 on the right.

**Dataset assessment**:

| Dataset | Verdict |
|---|---|
| Kaggle Food Ordering and Delivery App | Too sparse (1,898 orders, 71% weekend), no timestamps/locations; only usable to calibrate prep-time and delivery-time distributions |
| NYC DOHMH restaurant inspections | Precise coordinates and cuisine; suitable for the restaurant side of OD generation |
| NYC Neighborhoods ACS 2008-12 (GeoDa) | Combined with the delivery-user profile from the literature (ages 18–25, high income, students, male, minorities, time-pressed) to build zone demand weights |
| Motor Vehicle Collisions | Extract bicycle crashes for risk-aware routing |
| Bicycle Counters | Too few sites (e.g. Brooklyn Bridge) |
| Citi Bike tripdata / GBFS | Completely different distribution, useless for delivery research; usable if studying commuters, need to check how many docks are off-grid |

---

## 2. First model (Battery_Swap.pdf)

**Problem**: where to open swap stations, how many spare batteries and charging slots per station, how to schedule riders and charging to serve orders. Offline model (orders and traffic known).

**Basic assumptions**: riders are centrally dispatched, one order at a time, no swapping mid-delivery; batteries are homogeneous, each rider always carries one, only full batteries are issued;
charging adds one level per slot and can be paused; no inter-station transfers, no degradation, no failures.

**Notation**: riders k∈K, orders i∈I, candidate stations j∈J; time boundaries t=0..H, slots T={0..H−1}, slot length Δ hours;
battery levels q=0..L, each level ε kWh; station road-network node v_j.

**Rider actions** (state node (v,t,q), start (v_k^0,0,q_k^0)):

| Action | Transition |
|---|---|
| Wait | (v,t,q)→(v,t+1,q) |
| Reposition | (u,t,q)→(v,t+τ_p, q−g_p), u≠v, q≥g_p |
| Deliver | (v,t,q)→(d_i, u_a, q−g_a), includes travel to restaurant, pickup, drop-off |
| Swap | (v_j,t,q)→(v_j, t+σ_j, L), q<L, σ_j≥1 |

Discretisation of time/energy for a route p: τ_p=⌈T_p/Δ⌉, g_p=⌈E_p/ε⌉.
Delivery arc: u_a = max{t+τ_p, a_i} + h_i^p + τ_{p'} + h_i^d, g_a=g_p+g_{p'}, d_a=d_p+d_{p'};
created only when t≥r_i, q≥g_a, u_a≤H. The promised time b_i is a soft deadline (objective penalty).

**Decision variables**: x_{ka}∈{0,1} rider picks arc; u_i∈{0,1} order unserved; y_j open station; B_j, C_j∈Z≥0 spare batteries, charging slots;
n_{jqt} inventory (at boundary t before new actions); c_{jqt} number charged q→q+1 in slot t.

**Constraints**:
- (4) one source-to-sink flow path per rider;
- (5) each order served exactly once or marked unserved;
- (6) y_j ≤ B_j ≤ B̄_j y_j, 0 ≤ C_j ≤ C̄_j y_j, C_j ≤ B_j (an open station has at least one spare battery, charging slots ⊆ storage slots);
- (7) terminal arcs: (v,H,q)→z_k only if q ≥ g(v,j)+q_res, and x_{ka} ≤ y_j (proof that an open station is reachable at the end of the horizon);
- (8) s_{jqt}=number of swaps returning a level-q battery, S_{jt}=number of full batteries issued;
- (9)–(11) per-level inventory balance: n_{j,0,t+1}=n_{j0t}−c_{j0t}+s_{j0t}; intermediate levels +c_{j,q−1,t}; full level n_{j,L,t+1}=n_{jLt}+c_{j,L−1,t}−S_{jt};
- (12) c_{jqt} ≤ n_{jqt}, S_{jt} ≤ n_{jLt} (a just-returned battery cannot be charged immediately, a just-filled battery cannot be issued immediately);
- (13) n_{jL0}=B_j, all others 0; n_{jLH} ≥ ρ_j B_j;
- (14)–(15) charging power p^ch=ε/(ηΔ), Σ_q c_{jqt} ≤ C_j, p^ch Σ c ≤ P_j^max y_j;
- (16) swap-bay occupancy: all in-progress swaps (ℓ_a ≤ τ < u_a) ≤ M_j y_j;
- (17)–(18) consistency: Σ_q n_{jqt} = B_j always; change in stored energy at a station = charging gain − net swap output.

**Objective** (19)–(23): min C_setup + C_elec + C_travel + C_orders,
C_setup=Σ(F_j y_j + b^B_j B_j + b^C_j C_j), C_elec=Σ π_{jt}(ε/η)Σ_q c_{jqt}, C_travel=κ Σ d_a x_{ka},
C_orders=Σ P_i u_i + Σ[w_i Δ(u_a−r_i) + v_i Δ[u_a−b_i]_+] x_{ka}.
Optional (24): investment budget, minimum service rate ζ.

Example on p. 7: single station L=2, B=C=M=1, σ=1; after a swap at t=0, the returned battery starts charging at t=1, is full at t=3, next swap earliest at t=3.
**Suggested comparison**: baseline = nearest-feasible-rider dispatch + FCFS swapping + fixed charging rule, compared with coordinated scheduling under the same orders and initial conditions.

---

## 3. Extended model (E2.pdf)

**Changes**: a single "system coordinator" jointly decides station opening, charging slots, initial spare-battery placement, rider scheduling, charging and battery transfers.
Offline system-planning benchmark; platforms share order information. Entities: delivery vehicles (vehicle + fixed rider), swap facilities S, charging facilities C (co-location S∩C allowed),
battery logistics (fixed-timetable services e∈E), orders (platform label φ(i)), grid (supply group γ(j), prices and supply caps are exogenous inputs).

**New/modified sets and variables**:
- j∈N=S∪C; p∈P platforms; g∈G supply groups;
- h_e∈{0,1} service e used; z_{eq}∈Z≥0 number of level-q batteries on service e (including full q=L);
- dispatch/arrival counts D_{jqt}=Σ_{e: o_e=j, ℓ_e=t} z_{eq}, A_{jqt}=Σ_{e: d_e=j, u_e=t} z_{eq};
- facility constraints (7)–(8): 0≤B_j≤K_j y_j, 0≤C_j≤C̄_j y_j, C_j≤K_j y_j; C_j=0 (j∉C); C_j≥y_j (j∈C\S).
  **Differs from the first version**: an open station may start with no batteries (B_j is initial placement, not capacity), C_j≤B_j no longer required;
- terminal arcs (9) may only point to **swap** facilities (a charging-only station cannot provide the reachability proof).

**Transfer services** (10): h_e ≤ Σ_q z_{eq} ≤ U_e h_e, h_e ≤ y_{o_e}, h_e ≤ y_{d_e}.
Service timetable is exogenous, 0≤ℓ_e<u_e≤H; goods in transit are not charged and keep their level on arrival.

**Event order at boundary t** (Section 5, the key timing convention):
1. n_{jqt} includes transported batteries arriving at t (before new swaps/charging/dispatch);
2. dispatch and charging can only use this opening inventory; swaps issue a full battery and receive the old one immediately;
3. a battery returned by a rider at t is usable at t+1; a transported battery arriving at t is usable at t;
4. charging in slot t completes at t+1.

**Inventory balance** (13), for j∈N, q=0..L, t∈T:
n_{j,q,t+1} = n_{jqt} − c_{jqt} + c_{j,q−1,t} + s_{jqt} − 1{q=L} S_{jt} − D_{jqt} + A_{j,q,t+1}.

**Joint availability** (14): c_{jqt}+D_{jqt} ≤ n_{jqt} (q<L); S_{jt}+D_{jLt} ≤ n_{jLt}. Must be a joint constraint, otherwise one battery could be used twice.

**Storage/initial/end** (15)–(18): Σ_q n_{jqt} ≤ K_j y_j; n_{jL0}=B_j; n_{jLH} ≥ R_j^end y_j (j∈S); Σ_j n_{jLH} ≥ ρ Σ_j B_j.

**Charging and grid** (19)–(21): p^ch=ε/(ηΔ); Σ_{q<L} c_{jqt} ≤ C_j; p^ch Σ c ≤ P_j y_j; supply group Σ_{j∈C:γ(j)=g} p^ch Σ c ≤ P^grid_{gt}.
**Swap bays** (22) as in the first version.

**Conservation** (23)–(25): N_{jt}=Σ_q n_{jqt}, N_{j,t+1}−N_{jt} = −Σ_q D_{jqt} + Σ_q A_{j,q,t+1};
in-transit count m_t = Σ_{e: ℓ_e<t<u_e} Σ_q z_{eq}, Σ_j N_{jt} + m_t = Σ_j B_j; total batteries |K|+Σ_j B_j.
Section 8 example: A swap-only, B charge-only, L=2, H=5, capacity 1 per station, two initially full spare batteries, two services (depart t=1 arrive t=3, A→B empty, B→A full).

**Objective** (26)–(32): min C_setup + C_elec + C_travel + C_orders + C_reb,
C_reb = Σ_e [f_e h_e + Σ_q v^reb_{eq} z_{eq}].
Full problem: min (26) s.t. (5)–(9), (10)–(18), (20)–(22). Integer linear program.
Optional (33): investment budget B, minimum service rate ζ; or first min Σu_i then min cost.
**Special cases and evaluation**: h=z=0 → no transfers; S=C=N → co-location. Compare under the same demand and initial conditions; report service rate, response, lateness, riding distance, transfer volume, grid energy and cost separately.

---

## 4. Toy example (E2+Example.pdf, pp. 10–15)

- Road network chain B—A—C, A = restaurant + swap station, C = charging station, B = customer. Each edge 1 slot, 1 energy level, 1 km.
- K={1,2}, V={A,B,C}, S={A}, C={C}, H=8, Δ=1/12 h (40 minutes), L=2, ε=0.02 kWh, η=0.8, p^ch=0.3 kW.
  Both vehicles start at (A,0,2).
- Orders: 1 and 2 released at t=0 (promise 2), 3 released at t=4 (promise 6); all from A to B; h^p=1, h^d=0.
- Facilities: A open, B_A=0, K_A=1, no charging, M_A=1, σ_A=1; C open, B_C=1, K_C=1, C_C=1, 0.3 kW limit.
  q_res=0, R^end_A=0, ρ=1 (at least one spare battery full at the end).
- Transport: service 1 C→A departs 1 arrives 3 capacity 1; service 2 A→C departs 4 arrives 6 capacity 1.
- Costs: κ=1/km, π=2/kWh (0.05 per charge step), P_i=100, w_iΔ=1, v_iΔ=2, f_e=1, v^reb=0.2.
- Arc construction: Wait; Move; delivery arcs (v,t,q)→(B, t+δ(v,A)+2, q−δ(v,A)−1) (t≥r_i, q≥δ(v,A)+1, u_a≤8);
  swap arcs (A,t,q)→(A,t+1,2), q∈{0,1}; terminal arcs (v,8,q)→z_k if q≥δ(v,A).
- Optimal solution J=12.5: vehicle 1 delivers order 1 (0→2), returns to A (2→3), swaps (3→4), delivers order 3 (4→6), waits; vehicle 2 delivers order 2 (0→2) then waits.
  h_1=h_2=1, z_{1,2}=1 (full C→A), z_{2,0}=1 (empty A→C), c_{C,0,6}=c_{C,1,7}=1.
  J = 4 (travel) + 0.1 (charging) + 0 + 6 (response) + 2.4 (transport) = 12.5.
- Optimality argument: rejecting an order ≥100; response ≥2 per order → ≥6; delivery ≥3 km; a vehicle serving two orders must return to A ≥1 km; two orders plus the return need 3 levels > 2, so a swap is required;
  A has no inventory and cannot charge, it can only receive a full battery via service 1; restoring a full spare battery at the end requires service 2 + two charge steps → ≥2.5. Total ≥12.5.

---

## 5. Independent verification results (2026-10-11)

- **Toy example reproduction**: `notes/verify/toy_e2_example.py` rebuilds the model with gurobipy purely from the document rules (235 arcs per vehicle: 72 wait, 78 move, 62 delivery, 16 swap, 7 terminal; 551 variables, 322 constraints), optimum J = 12.5,
  the five cost components 4 + 0.1 + 0 + 6 + 2.4 match the document; inventory table and h/z/c decisions match exactly; vehicle/order labels are interchangeable (the document also notes the optimum is not unique).
  What-if: no transport services → J = 106 (one order unserved); ρ = 0 → J = 11.2 (second transport and charging saved); storage capacity raised to 2 → still 12.5.
- **Identities and tables**: `notes/verify/identity_checks.py` derives (23), (25) from (13) with sympy; the strict inequality ℓ_e < t < u_e in (24) is correct (the non-strict version gives 4 ≠ 2 at t=1 in the Section 8 table);
  the E2 Section 8 table, the E2+Example p. 15 table and the Battery_Swap p. 7 table pass row-by-row checks of (13)/(14)/(15)/(20)/(22); every step of the p. 15 optimality lower-bound argument holds.
- **Formula audit**: 24 records, **no errors**; all are modelling choices, ambiguities or differences from the first version. Key implementation decisions are fixed in `notes/DECISIONS.md`, main points:
  - n_{jqt} = inventory at boundary t after transport arrivals and before swaps/charging/dispatch; returned batteries usable at t+1; arriving goods usable at t;
  - (14) must be a joint constraint; (15) only needs to be checked at each boundary; (17) only over S, (18) sums over all N;
  - (9) terminal reachability is a hard constraint (via flow conservation), can cause infeasibility or force stations open; a penalised virtual-terminal-arc switch is provided;
  - θ_ia is based on the release time r_i (includes uncontrollable prep waiting), an a_i-based switch is provided;
  - delivery arcs with "leave early and wait at the restaurant" are dominated by later-departure arcs and can be pruned losslessly;
  - energy rounding: the document rounds up per leg g_a = g_r + g_r' (default), concatenated rounding as a sensitivity option.
- **Questions for the supervisor**: response-time reference (r_i vs a_i), default values of ρ/R^end/q_res, whether terminal unreachability may be hard-infeasible, whether zero-dwell transfers are allowed, how logistics timetables are generated, whether swapping at q = L−1 is allowed, whether facilities are fixed in the first round of experiments, length of the recovery window, one or several routes per OD pair, calibration of Δ/L/ε against real chargers.

## 6. Experiment plan (first round)

| Experiment | Question | Method |
|---|---|---|
| E1 toy example | Does the general implementation reproduce J = 12.5 and the behaviour of each switch | full ILP / h=z=0 / ρ=0 / lexicographic; baseline policy; baseline as MIP start |
| E2 coordination vs baseline | Gain of offline coordination over naive policies, and where it comes from | synthetic medium instances, demand 0.75/1/1.5×, 5 seeds; baseline, baseline + opportunistic swapping, ILP, fixed dispatch optimising only swapping/charging |
| E3 transfers and facility separation | Value of battery transfers and swap/charge separation | 3 co-located stations vs 3 swap stations + 1/2 charging hubs; transfers on/off; shuttle every 30 min |
| E4 station sizing | Marginal value of B_j, C_j, P_j | one-at-a-time sweeps + ILP freely choosing B, C |
| E5–E7 (later) | Siting and budget; discretisation sensitivity; scale limits and rolling horizon | see `workflow1_result.json` → plan.experiments |

Size estimates: toy ~900 binary variables, milliseconds; medium instances (|K|=10, |V|≈28, H=24–48, L=8–12) about 0.5–1M binaries after pruning, Gurobi in minutes;
city scale (30, 100, 96, 6, 200) cannot be solved as a single ILP, needs rolling horizon/decomposition.

Baseline policies and the ILP share the same discretised instance and arc library (same pruning) and are priced with the same objective; violations of (9)/(17)/(18) are reported, not enforced.
Default discretisation: Δ = 5 min, H = 24 (2-hour window), 600 Wh battery, L = 12 (ε = 50 Wh), η = 0.9 → p^ch = 0.667 kW.

Dataset conclusions are in `notes/datasets.md`.
