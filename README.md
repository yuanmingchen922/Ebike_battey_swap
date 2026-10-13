# E-bike battery swapping for food delivery in New York City

## 1. What this project is

Food-delivery riders in New York City ride electric bikes. When a battery runs low the rider goes to a station and swaps it for a full one. The station then charges the empty battery, and sometimes a shuttle moves batteries between stations.

We built a computer model that plans all of this at once for a whole evening: which rider takes which order, when each rider swaps, when each station charges, and when batteries are shipped between stations. The model picks the plan with the lowest total cost (customer waiting, late deliveries, dropped orders, electricity, riding, shuttles, station rent). We then compared this coordinated plan with a simple "nearest rider takes the order, swap when low" rule, on the same orders and the same bikes, to measure how much coordination is worth.

**Headline (final, round 3):** over 30 synthetic Manhattan-like evenings the coordinated plan is 29.6 % cheaper than the simple rule (95 % confidence interval +/- 5.6 points) and cheaper on every single evening; on 10 evenings built from real Midtown restaurant and census data it is 31.8 % cheaper (+/- 8.2). Almost all of the saving is punctuality: the simple rule delivers 16-18 orders late per evening, the coordinated plan 1-2. Spare batteries, chargers and shuttles turn out to matter very little at this scale; the plan itself is what matters.

## 2. What is in this repository

| Folder / file | What it is, in plain words | When to open it |
|---|---|---|
| `README.md` (this file) | The overview, glossary, final results and how-to. | Start here. |
| `notes/SUMMARY.md` | The full project summary for rounds 1 and 2: method, results, what changed between rounds, open decisions. The round-3 results are in the reports below and in Section 6 of this file. | If you want the detailed story. |
| `notes/DECISIONS.md` | Every modelling choice we had to make where the supervisor's write-up left room (timing rules, defaults, cost units, baseline rules, the round-3 service rule and solver protocol). Binding for the code. | Before changing the model or arguing about a number. |
| `notes/understanding.md` | Our reading notes on the four supervisor documents (proposal deck, first model, extended model "E2", worked toy example). | To understand where the model comes from. |
| `notes/datasets.md` | What public data exists, how big it is, and what it can and cannot be used for. | When you want to know why we used a dataset. |
| `notes/literature_demand_model.md` | How three published studies were turned into "which neighbourhoods order more food" weights. | When you care about the demand side. |
| `notes/cost_calibration.md` | Where every dollar figure comes from (rider pay, electricity price, battery price, station rent), with sources. | When you doubt a cost number. |
| `notes/data/*.json`, `*.csv`, `*.md` | Machine-readable versions of the costs, the Kaggle order statistics and the neighbourhood weights. | When running or editing the code. |
| `notes/verify/` | Two stand-alone scripts that rebuild the supervisor's toy example and check the battery-conservation identities by hand. | To convince yourself the equations were read correctly. |
| `data/raw/` and `data/MANIFEST.md` | The downloaded public data (restaurants, census tables, crash grid, bike counters) and a manifest with sizes, checksums and the exact download commands. | To check the data or re-download it. |
| `ebike_swap_sim/` | The code: model, simple rule, instance generator, NYC data loader, cost checker. Its own `README.md` and `CONTRACT.md` describe the modules. | If you want to run or extend anything. |
| `ebike_swap_sim/experiments/` | One script per experiment and round (E1 toy check; E2u, E3u, E4u and E8 with their `*_round3.py` versions, which are the final ones). | To re-run an experiment. |
| `ebike_swap_sim/outputs/e1/RESULTS.md` and `outputs/*_round3/RESULTS_final.md` | The final result reports, one per experiment, with tables and figures, plus the raw `records.jsonl` and `results.csv` they were built from. **These are the deliverables.** The round-1 and round-2 folders (`e2_coord*`, `e2u_coord_usd`, `e3`, `e3u`, `e4_sizing`, `e4u_sizing_usd`, `e8_nyc_fixed`) are kept for provenance. | To read the numbers. |
| `ebike_swap_sim/tests/` | 136 automated checks that the code still matches the written model and that the round-3 scripts behave. | After changing code. |
| `food_order.csv` | The Kaggle "FoodHub" order dataset (1,898 orders) used to calibrate preparation times and cuisine shares. | Rarely. |

**Not included:** the supervisor's four PDFs (the proposal deck `Ebike Battery Swap.pdf`, the first model `Battery_Swap.pdf`, the extended model `E2.pdf`, and `E2+Example.pdf` with the worked toy example) and their extracted text and page images (`notes/extracted/`, `notes/figs/`), the full texts of the three papers in `notes/literature/` (copyright); the Chinese-language companion notes (`*_zh.md`); the per-run instance dumps (`ebike_swap_sim/outputs/*/instances/`, large, regenerated from the seed by every script); the internal workflow logs (`notes/workflow*.json`); and the solver log. Our notes quote the equation numbers of `E2.pdf`; the papers are cited in Section 8 with links.

## 3. The idea in plain words

**Time is cut into 5-minute steps.** A 4-hour dinner window is 48 steps. **A battery is cut into 12 levels**; one level is 50 Wh, so a full 600 Wh battery is level 12. Charging adds one level per step.

**Each rider follows a path.** Think of a board game. A rider's position on the board is "where am I, what time is it, how full is my battery". Each move is one action: wait one step; ride somewhere; deliver an order (ride to the restaurant, wait for the food, ride to the customer); or swap at a station (jump to a full battery). The model lists every legal move for every rider in advance (several hundred thousand to a million and a half of them) and picks exactly one path per rider.

**Stations keep a battery ledger.** For every station, every step and every battery level, the ledger says how many batteries are sitting there. A swap takes one full battery out and puts one low battery in. Charging moves a battery up one level. A shuttle takes batteries out at one station and puts them in at another a few steps later. The ledger must never go negative and must never exceed the shelf space.

**The solver picks the cheapest combination.** All the paths and ledgers are tied together by rules (every order is either delivered once or dropped; a station cannot hand out a battery it does not have; a charger cannot charge two batteries at once; the power drawn from the grid stays under its limit). A commercial solver (Gurobi) searches over all combinations that obey the rules and returns the one with the lowest total cost. Because it sees the whole evening at once, it can send a rider to swap early, or hold an order for a better rider, which a myopic rule cannot do. Since round 3 the model can also be told "serve at least 90 % of the orders, whatever it costs" as a hard rule.

**The simple rule we compare against.** Orders are handled first-come first-served. Each order goes to the nearest rider that has enough battery and is free. When a rider's battery drops to 3 of 12 levels, the rider goes to the nearest open station that has a full battery. Stations serve riders in arrival order and charge only as many batteries as they expect to need in the next hour. By default this rule never ships batteries between stations. It uses only information available at the moment, like a real dispatcher without a crystal ball. Both the model and the rule are priced with the same cost function on the same instance, so the comparison is fair.

## 4. Glossary

### 4.1 Parameters (inputs we set)

| Symbol | Plain meaning | Typical value (rounds 2-3) | Where it is set |
|---|---|---|---|
| Delta | Length of one time step | 5 min | `experiments/common.py` (families), `or_instance.Discretisation` |
| H | Number of steps in the planning window | 48 (4 h, 17:00-21:00); 24 in round 1 | `experiments/common.py` |
| L | Number of battery levels | 12 | `experiments/common.py` |
| eps | Energy in one battery level | 50 Wh (0.05 kWh) | `experiments/common.py`, `config.py` (600 Wh battery) |
| eta | Charging efficiency (share of grid energy that ends up in the battery) | 0.9 | `or_instance.Discretisation` |
| p_ch | Power one charger draws; follows from eps, eta and Delta | 0.667 kW | computed in `or_instance.py` |
| kappa | Cost of riding one kilometre (bike wear only; rider pay is treated as already paid) | 0.12 $/km | `notes/data/cost_calibration_usd.json` via `costs.py` |
| pi | Electricity price | 0.32 $/kWh | same |
| P_i | Penalty for dropping an order | 30 $ | same |
| w_i | Cost of customer waiting, per hour from order placement to delivery | 18 $/h | same |
| v_i | Extra cost per hour of lateness beyond the promised time | 36 $/h | same |
| f_e | Fixed cost of running one shuttle trip | 20 $ | same |
| v_reb | Cost per battery carried on a shuttle | 1 $ | same |
| F_j | Rent of a swap station for the 4-hour window (charging hub: 29.19) | 12.03 $ | same |
| b^B, b^C | Holding cost of one spare battery / one charger per window | 0.332 $ / 0.082 $ | same |
| K_j | Shelf space: maximum batteries a station can hold | 8 (hub 30) | `generator.py` `DEFAULT_FACILITIES_SPEC_R2` |
| C_j bound | Maximum number of chargers a station may have | 6 (hub 20) | same |
| M_j | Number of swap bays (riders served at the same time) | 1 | same |
| sigma_j | Time a swap takes | 1 step | same |
| P_j | Maximum charging power of one station | 4 kW (hub 12 kW) | same |
| P_grid | Power limit shared by all stations on the same grid feeder | 8 kW; 6 kW from 18:00 to 20:00 | same |
| q_res | Battery levels a rider must keep at the end to reach a station | 1 level | `generator.py` `DEFAULT_COSTS` |
| rho | Share of all spare batteries that must be full again at the end of the window | 0.5 | same |
| R_end | Full batteries each swap station must hold at the end of the window | 1 | same |
| zeta | Minimum share of orders that must be served (a hard rule rather than a penalty; equation (33)) | 0.90 in the main round-3 run, 0.85 as a sensitivity; not used in rounds 1-2 | `ilp.build_model(zeta=...)`, `Instance.zeta`, `experiments/e2u_round3.py` |
| q0 | A rider's battery level at the start | random, 4 to 7 of 12 | `generator.py` round-2 mode |
| r_i, a_i, b_i | Order placed / food ready / promised delivery time | ready = placed + 20-35 min; promise = ready + 25 min | `generator.py` from `notes/data/kaggle_calibration.json` |
| h^p, h^d | Handling time at the restaurant / at the customer | 1 step each | `experiments/common.py` |
| Fhat, bhat, chat | Investment prices for the optional budget rule (station, battery, charger) | 50,000 / 450 / 400 $ | `notes/data/cost_calibration_usd.json` (not used in the experiments) |

### 4.2 Variables (choices the model makes)

| Symbol | Plain meaning | Type |
|---|---|---|
| x | For every rider and every legal move: is this move taken? | yes/no |
| u | For every order: is it dropped? | yes/no |
| y | For every candidate station: is it open? | yes/no (fixed to "open" in our experiments) |
| B | Spare batteries placed at a station at the start | whole number (3 per site by default; free in the E4 "what would the planner buy" run) |
| C | Chargers installed at a station | whole number (2 per site by default) |
| n | Batteries at a station, per level, at every step (the ledger) | whole number |
| c | Batteries being charged one level up at a station in a step | whole number |
| h | Is a given shuttle trip used? | yes/no |
| z | Batteries carried on that shuttle, per level | whole number |
| s, S (derived) | Batteries returned by swapping riders per level / full batteries handed out | computed from x |
| D, A (derived) | Batteries leaving / arriving by shuttle at a station | computed from z |
| m_t (derived) | Batteries on the road at step t; used to check that no battery is lost | computed from z |

### 4.3 Knobs of the simple rule (baseline)

| Knob | Plain meaning | Default |
|---|---|---|
| `q_thr` | Battery level at or below which an idle rider goes to swap | 3 of 12 (a quarter) |
| `stock_aware_site` | Go to the nearest station that actually has a full battery (station stock is public) | on |
| `charge_rule = DEMAND_AWARE` | Charge only what the station expects to need in the next 12 steps (based on the last 12 steps) plus the end-of-window reserve | on; `HIGH_FIRST` = "charge everything as soon as possible" is the round-1 rule |
| `jit_dispatch` | A rider may wait and leave "just in time" instead of arriving early at a restaurant | on |
| `transfer_rule` | `NONE` (no shuttles) or `REORDER_POINT` (ship batteries when a station runs low) | `NONE` |

## 5. What we did, step by step

**Round 1 (2026-10-11): build and verify.** We extracted the model from the supervisor's PDFs, rebuilt the worked toy example by hand and got the documented answer (cost 12.5). We then wrote the package `ebike_swap_sim/`: the rider path network, the station ledger, the solver model, the simple rule, a cost checker that prices any plan with the same formula, and a generator of synthetic Manhattan-like instances. Two reviewers compared the code line by line with the equations and found no error in the model; they found a fairness flaw in the simple rule (it was denied an "arrive just in time" move that the model had), which we fixed. We ran experiments E1-E4 in the paper's toy cost units (dropping an order cost 100, waiting 12 per hour) on a 2-hour window with 10 riders.

**Round 2 (2026-10-12): real dollars, longer window, real data.** The model itself did not change. We replaced the toy costs with dollar figures from 2025-2026 New York sources (rider minimum pay, Con Edison tariffs, battery prices, station rents), moved to a 4-hour dinner window with 6 riders and 36 orders, started riders at 30-60 % battery, improved the simple rule (stock-aware station choice, demand-aware charging), and re-ran E2, E3 and E4 as E2u, E3u, E4u. We added E8, a "semi-real" Manhattan instance built from real data:

- **NYC restaurant inspections (DOHMH):** 27,030 restaurants with coordinates and cuisine; 4,607 inside our Midtown/Chelsea/Flatiron study box.
- **Census neighbourhood tables (DCP, ACS 2020-2024, 262 neighbourhoods):** population by age, ethnicity, income, children, living alone, students, turned into "how much this neighbourhood orders" weights with the formula from three published studies.
- **Cyclist crash grid and bicycle counters (NYC Open Data):** downloaded and loaded as a risk layer and a cross-check of the evening peak; not used inside the cost yet.
- **Kaggle FoodHub orders:** preparation time (uniform 20-35 min), delivery promise (25 min), cuisine shares, restaurant popularity (Zipf law).
- **Three papers** (Section 8) on who orders food delivery: age is the dominant factor (18-29 year olds order about 3.4 times as often as 60+).

What is still **synthetic**: the street grid (150 m blocks rotated to Manhattan's 29-degree street angle; real restaurants and neighbourhood polygons are snapped onto it), the hills and traffic lights, and the hour-by-hour demand curve (lunch 28 %, dinner 45 %, late 12 %; declared as an assumption because no paper gives one).

**Round 3 (2026-10-12 to 2026-10-13): more evenings, a hard service rule, every cell filled.** The model and the costs did not change; this round was about certainty. Three things were done. (1) Round 2 had tried a two-step variant ("first serve as many orders as possible, then minimise cost") whose answers the solver could not certify, so it was dropped and replaced by a hard service rule written into the model as constraint (33): at least 90 % of the orders must be served (the main setting), with 85 % as a sensitivity check. When the rule cannot be met, the scripts also compute the largest share of orders that any schedule could serve at all, so that "impossible" comes with a number. The end-of-window battery targets were kept as written, together with the "targets switched off" control. (2) Every solver cell that round 2 had skipped for lack of time was solved (round-2 solutions were reused only when they had been proven optimal or were within 1 % of optimal), and the four E3u cells that had stopped at a 2 % solver gap were re-run with a doubled time limit. (3) The random evenings were extended: E2u from 5 to 10 seeds (30 instances), E3u from 2 to 5, E4u from 3 to 6, E8 from 3 to 10. Same solver settings everywhere (3 threads, 300 s per solve, fixed solver seed); about 9 hours of solver time in total, nothing skipped. On the seeds that round 2 had already run, round 3 reproduces the round-2 numbers exactly, so every change in the headline figures comes from the new evenings, not from code changes. Scripts: `experiments/e2u_round3.py`, `e3u_round3.py`, `e4u_round3.py`, `e8_round3.py`; protocol in `notes/DECISIONS.md` (R3.1-R3.3).

## 6. Results and outputs

All percentages below are **gap = (cost of the simple rule - cost of the model) / cost of the simple rule**, i.e. how much cheaper the coordinated plan is. "+/-" is a 95 % confidence interval (Student t) over random evenings ("seeds"); a wide interval means few seeds or very different evenings. Costs are dollars per 4-hour window per 3-station area. The numbers in the tables are the final (round-3) ones; the earlier round-2 run is mentioned for comparison only.

### 6.1 Round 1 to round 3: what changed

| Item | Round 1 (2026-10-11) | Round 2 (2026-10-12) | Round 3 (2026-10-13, final) |
|---|---|---|---|
| Cost units | Toy: drop 100, waiting 12/h, riding 1/km | Dollars: drop 30 $, waiting 18 $/h, lateness 36 $/h, riding 0.12 $/km | unchanged |
| Drop penalty divided by half an hour of waiting | 50 | 3.3 | 3.3 |
| Instance | 10 riders, 2 h, 30 orders, batteries 60-70 % full | 6 riders, 4 h, 36 orders, batteries 30-60 % full | unchanged |
| Random evenings (seeds) per experiment E2 / E3 / E4 / E8 | 5 / 2 / 3 / - | 5 / 2 / 3 / 3 | 10 / 5 / 6 / 10, every solver cell filled |
| Simple rule | Nearest station, charge everything at once | Station with stock, charge on demand (only 1.8 % cheaper) | unchanged |
| Service-level rule | none | "serve first, then minimise cost" two-step variant (could not be certified) | hard rule: at least 90 % served (85 % as sensitivity) |
| E2 overall gap | 24.0 % +/- 8.7 | 21.9 % +/- 8.1 (15 instances) | **29.6 % +/- 5.6** (30 instances, cheaper on all 30) |
| E2 gap at low / normal / high demand | 4.3 / 29.6 / 38.2 % | 6.9 / 21.3 / 37.3 % | 15.4 / 31.2 / 42.1 % |
| What the gap is made of | 90 % dropped orders, 9 % lateness | 54 % lateness, 25 % waiting, 20 % dropped orders, <1 % riding + electricity | 59 % lateness, 32 % waiting, 8 % dropped orders, <1 % riding + electricity |
| Cost of a 90 % service guarantee | - | - | 0.2 % of the model's cost at low demand, 5.5 % at normal demand, impossible at high demand with 6 riders |
| Value of end-of-window battery targets | All of the transfer value came from them | A few dollars per instance | 0.34 $ per instance (E2u), 0.27 $ (E8) |
| E3 value of shuttles, 1 hub / 2 hubs | 257 / 254.5 toy units | 6.6 / 12.6 $ (0 once end targets are relaxed) | 8.6 / 8.6 $ +/- 10.1, a lower bound (0 once end targets are relaxed) |
| E3 extra cost of separate charging hubs | +55 / +98 toy units | +52 / +82 $ (29 / 58 of it hub rent) | +52.2 / +81.4 $ +/- 1.6 (29 / 58 of it hub rent) |
| E3 model vs rule, layouts a / b / c | 48 / 37 / 36 % | 24 / 21 / 20 % | 21 / 18 / 18 % (+/- 10-11) |
| "Ship when low" shuttle rule for the simple rule | Helped in separated layouts | Hurts everywhere: +143 to +302 $ | Hurts everywhere: +165 to +207 $ on average, on every seed |
| E4 batteries the model needs per station | 2 (under stress) | 1 is enough | 1 is enough (now proven by solves, not bounds) |
| E4 batteries the simple rule needs | more than 6 | 2-3 | 2 (the second battery is worth 44 $ +/- 22 per evening) |
| Real data | none | Manhattan instance: 36.5 % +/- 29.3 | Manhattan instance: **31.8 % +/- 8.2**, positive on 20 of 20 instances |
| Solver size and time | 0.7-1.0 M yes/no variables, 15-30 s | 0.9-1.5 M, about 90 s; NYC 0.58 M, 41 s | 0.9-1.6 M, 80-240 s per solve; NYC 0.55 M, 45 s |

### 6.2 E1: does the code reproduce the supervisor's toy example?

**Question:** when we feed the model the 2-rider, 3-order example from the write-up, do we get the documented answers?

| Case | Expected | We got |
|---|---|---|
| Full model | 12.5 | 12.5 |
| No end-of-window battery target | 11.2 | 11.2 |
| Shuttles forbidden | 106 | 106 |
| Simple rule, no shuttles / with shuttles | 108 / 14.5 | 108 / 14.5 |

Every ledger table printed in the documents is reproduced step by step, and the solver's cost always equals our independent cost checker. **Meaning:** the code is a faithful copy of the written model. Open `ebike_swap_sim/outputs/e1/RESULTS.md` and `inventory_toy.png`.

### 6.3 E2u: what is coordination worth?

**Question:** on the same orders, how much cheaper is the coordinated plan than the nearest-rider rule? (6 riders, 4 h, 3 stations, 10 seeds x 3 demand levels = 30 evenings)

| Demand | Orders | Simple rule, $ | Model, $ | Gap |
|---|---|---|---|---|
| x0.75 (quiet) | 27 | 577 | 480 | 15.4 % +/- 7.3 |
| x1 (normal) | 36 | 993 | 659 | 31.2 % +/- 9.1 |
| x1.5 (busy) | 54 | 1,930 | 1,098 | 42.1 % +/- 5.7 |
| All 30 evenings | | 1,167 | 746 | **29.6 % +/- 5.6** |

The model is cheaper on all 30 evenings (smallest saving 3.7 %, largest 51.8 %). The earlier run (round 2, the first 5 seeds only) gave 21.9 % +/- 8.1 with 6.9 / 21.3 / 37.3 % by demand level; those 15 evenings are reproduced exactly inside the new set, and the five new seeds alone give 37.2 % +/- 6.2. The headline went up only because the new evenings are harder for the simple rule (its average cost 1,311 $ versus 1,022 $ on the old seeds) while the model's cost barely moves (765 $ versus 727 $): the model's cost varies by only 4-5 % from evening to evening, the simple rule's by 15-22 %.

**With a hard service guarantee.** Round 3 adds the rule "serve at least a fixed share of the orders" and asks what it costs:

| Minimum share served | Demand | Possible? | Extra cost over the plain model | Share actually served: with rule / plain model / simple rule | Gap vs simple rule |
|---|---|---|---|---|---|
| 90 % (main) | x0.75 | yes, 10 of 10 | 0.9 $ (0.2 %); only 3 of 10 evenings need any change | 95.6 / 94.4 / 96.7 % | 15.2 % +/- 7.3 |
| 90 % (main) | x1 | yes, 10 of 10 | 37.4 $ (5.5 %); 8 of 10 evenings change, 1.4 to 176 $ | 92.2 / 87.5 / 87.2 % | 27.8 % +/- 8.7 |
| 90 % (main) | x1.5 | no, 0 of 10 | not defined: the most any schedule can serve is 74-80 % of the 54 orders where proven (at most 83 % by the solver's bound), below the 49 orders (90 %) required | plain model 69.8 %, simple rule 62.6 % | - |
| 85 % (sensitivity) | x0.75 | yes, 10 of 10 | 0 (the plain model already serves enough on every evening) | 94.4 / 94.4 / 96.7 % | 15.4 % +/- 7.3 |
| 85 % (sensitivity) | x1 | yes, 10 of 10 | 8.0 $ (1.1 %); 2 of 10 evenings change | 88.6 / 87.5 / 87.2 % | 30.6 % +/- 8.6 |
| 85 % (sensitivity) | x1.5 | no, 0 of 10 | not defined: needs 46 of 54 served, the ceiling is 40-43 orders where proven and at most 45 by the bound | plain model 69.8 %, simple rule 62.6 % | - |

Pooled over the 20 evenings where the rule can be met, the model with the 90 % rule is 21.5 % +/- 5.9 cheaper than the simple rule (plain model on the same 20 evenings: 23.3 % +/- 6.5); with the 85 % rule, 23.0 % +/- 6.3. **Meaning:** a 90 % service promise is almost free on a quiet evening, costs about 5 % on a normal one (the model rescues 1.7 extra orders per evening and pays for it mostly with a few late deliveries: 5.7 per evening instead of 1.2), and simply cannot be kept on a busy evening with 6 riders, because 54 orders in 4 hours is more than 6 bikes can deliver under any plan. That is a fleet-size question, not a scheduling one.

**Where the saving comes from.** Over the 30 evenings the simple rule spends 421 $ more per evening than the model: 59 % of that is late deliveries, 32 % is customers waiting longer, 8 % is dropped orders, and riding distance plus electricity are under 1 %. On a normal evening the model delivers 1.2 orders late against 16.5 for the simple rule, with an average order-to-door time of 50 min versus 63 min, while serving the same share of orders (87.5 % versus 87.2 %). On quiet evenings the model actually drops slightly more orders than the rule (1.5 versus 0.9 of 27), because at a 30 $ penalty a drop is cheaper than a late delivery; it then makes that back several times over in punctuality. Switching off the end-of-window battery targets changes the model's cost by 0.34 $ per evening, so none of the advantage comes from battery housekeeping. A side check from round 2 still holds: if rider wages are charged per order (variant `usd_A`), serving an order costs more than dropping it and the model drops 85 % of orders, which is a degenerate objective, not a finding. Open `ebike_swap_sim/outputs/e2u_round3/RESULTS_final.md`, `gap_by_demand.png`, `zeta_premium.png`, `cost_components.png`, `drop_rates.png`.

### 6.4 E3u: are battery shuttles and separate charging hubs worth it?

**Question:** if charging happens at a separate hub instead of at the swap station, how much does it cost, and how much do shuttles help? (same 9 batteries and 6 chargers in every layout; 5 seeds, all 60 solver cells solved)

| Layout | Model, shuttles allowed | Model, shuttles forbidden | Value of shuttles | Extra cost vs co-located | Gap vs simple rule |
|---|---|---|---|---|---|
| (a) 3 stations that swap and charge | 638 +/- 29 | 638 +/- 29 | 0 | - | 21.3 % +/- 11.3 |
| (b) 3 swap stations + 1 charging hub | 690 +/- 29 | 699 +/- 30 | 8.6 +/- 10.1 (lower bound; at most 22) | +52.2 +/- 1.6 (29.2 is hub rent) | 18.4 % +/- 10.6 |
| (c) 3 swap stations + 2 hubs | 720 +/- 29 | 728 +/- 30 | 8.6 +/- 10.1 (lower bound; at most 22) | +81.4 +/- 1.6 (58.4 is hub rent) | 17.8 % +/- 10.4 |

The earlier run (round 2, 2 seeds and 15 of 36 cells unsolved) had 637 / 690 / 719 $, shuttle values 0 / 6.6 / 12.6 $ and gaps 24 / 21 / 20 %; all of those sit inside the new intervals.

**Meaning:** separating charging from swapping costs about 23 $ of operations per evening plus the hub rent, and the ranking co-located < 1 hub < 2 hubs holds on every seed. Shuttles are worth very little (one 2-battery shuttle trip per evening in the separated layouts, used only to top up the stations before closing time), and nothing at all once we drop the rule that stations must end the evening with full batteries: with the targets switched off the model uses zero shuttles on all 15 layout-and-seed pairs and the extra cost of separation is exactly the hub rent plus at most 0.4 $. In other words, in a 4-hour window the 9 spare batteries never run out, so the only reason to ship batteries is to be tidy at closing time. The "ship when low" rule for the simple dispatcher is harmful on every layout and every seed (+165 to +207 $ on average) because each of its 5-14 trips costs 20 $ and rescues at most one order. Caveat: the "shuttles allowed" cells of the separated layouts are the one cell type the solver cannot close; even with a doubled time limit (600 s) they stop at a 1.8-2.0 % solver gap, so the shuttle values for (b) and (c) are lower bounds with an upper bound of about 22 $. Open `ebike_swap_sim/outputs/e3u_round3/RESULTS_final.md`, `fig_cost_by_layout.png`, `fig_transfer_value.png`, `fig_gap_by_layout.png`.

### 6.5 E4u: how big should a station be?

**Question:** what happens to cost when we change spare batteries (B), chargers (C) and power (P) per station? (6 seeds for the battery sweep and the free-sizing run; 3 seeds for the charger and power sweeps; the full 20-cell battery-by-charger grid solved on seed 0)

| Spare batteries per station | Model, $ | Simple rule, $ | Saving per extra battery, simple rule |
|---|---|---|---|
| 1 | 641 | 1,023 | 44.2 $ +/- 21.6 per evening (1 to 2) |
| 2 | 641 | 890 | 6.1 $ +/- 10.8 (2 to 3), not significant |
| 3 (default) | 641 | 872 | about 0 |
| 4 | 642 | 874 | about 0 |
| 6 | 644 | 867 | - |

Headline gap at the default size: 24.6 % +/- 12.0 (6 seeds; the earlier 3-seed run gave 22.5 % +/- 21.3, and the three new seeds bracket the old ones).

**Meaning:** for the coordinated plan, one spare battery per station is already enough: a second one is worth 0.35 $ of operations per evening, and every battery beyond the second costs more to hold than it saves. Chargers and station power are worth exactly nothing to it (the model's operating cost is the same number at 1, 2, 3 or 4 chargers and at 1.4 to 4.2 kW, now shown by solving every cell rather than by bounds). For the simple rule the second battery per station is worth about 44 $ per evening (about 65,000 $ per battery per year if every window looked like dinner), the third almost nothing, and even six batteries per station do not bring it to the model's service level: on three of the six seeds the rule tops out at 81-83 % of orders served against 86-89 % for the model, and on no seed does its cost come within 70 $ of the model's. Left to choose freely, the planner buys only 3-4 batteries and 2-4 chargers for the whole area instead of the default 9 and 6, saving 1.4 $ per evening; at those lean sizes the simple rule collapses (80 % served, gap 33.5 % +/- 10.5), so the value of coordination is largest exactly where a planner would size the stations. Open `ebike_swap_sim/outputs/e4u_round3/RESULTS_final.md`, `cost_vs_B.png`, `cost_vs_C.png`, `cost_vs_P.png`, `heatmap_BxC.png`, `free_sizing.png`.

### 6.6 E8: does the advantage survive real Manhattan data?

**Question:** with real restaurants, real neighbourhood demand weights and real candidate station locations in Midtown, is the model still better? (6 riders, 36 orders, 10 seeds, two station placements)

| Station placement | Simple rule, $ | Model, $ | Gap |
|---|---|---|---|
| Busiest restaurant cells | 1,014 | 670 | **31.8 % +/- 8.2** |
| Grid-connected landmarks (8th Ave/W 34th, Union Square, Grand Central) | 997 | 670 | 30.5 % +/- 8.6 |

The gap is positive on all 20 instances (range 18-51 %). The earlier 3-seed run gave 36.5 % +/- 29.3 and 34.3 % +/- 37.6; those point estimates lie inside the new intervals, and the seven new seeds alone average 29.8 % / 28.9 %, so the first three evenings were on the optimistic side.

**Meaning:** yes. The model's cost barely moves when the stations are relocated (at most 0.41 $ on any seed), while the simple rule swings by -9 % to +6 % with no consistent direction: a coordinated plan absorbs where the stations are, a myopic rule does not. The model serves 85.8 % of orders against 83.9 % for the rule, delivers 1.5 orders late per evening against 17.8, gets the food to the door in 0.83 h instead of 1.07 h on average, rides 95 km instead of 110 and buys a third of the electricity. The gap is 59 % lateness, 35 % waiting and 6 % dropped orders, the same shape as on the synthetic evenings. Switching the end-of-window battery targets off changes the model's cost by 0.27 $, so again none of the advantage is battery housekeeping; in fact the "targets off" model buys no electricity at all in 20 of 20 runs, which says that with 9 spare batteries for 6 riders the charging side of the problem never binds in a 4-hour window. The gap is a lower bound, because the NYC instance restricts the model's repositioning moves but not the rule's. All 40 solves finished to proven optimality in 28-64 s. Open `ebike_swap_sim/outputs/e8_round3/RESULTS_final.md`, `map_seed0.png` (the study box with restaurants, neighbourhood heat map, both station placements and rider paths), `gap_by_seed.png`, `cost_components.png`, `demand_comparison.png`. Ignore `outputs/e8_nyc/`, an earlier run with a flawed demand curve.

## 7. How to run it, and the limits

**Install.** Python 3.12 with `numpy`, `pandas`, `networkx`, `matplotlib`, `pytest`, `openpyxl`, and `gurobipy` 13 with a licence (free academic licences exist). Everything except the solver runs without Gurobi.

```bash
cd ebike_swap_sim
export PYTHONPATH=$PWD
python3 -m pytest tests -q                 # 136 checks, about 90 s
python3 experiments/e1_toy.py              # toy check -> outputs/e1/
python3 experiments/e8_round3.py --smoke   # one cheap NYC cell (seed 3, busiest placement), 30 s solver limit
python3 experiments/e8_round3.py --seeds 3 --time-limit 300     # one NYC seed, both placements, all methods
python3 experiments/e2u_round3.py --dry-run                     # print the full E2u plan without solving
python3 experiments/e2u_round3.py --analyse                     # rebuild tables and figures from records.jsonl
```

Each `*_round3.py` script appends one line per solver run to `records.jsonl` in its `outputs/<exp>_round3/` folder, refreshes `results.csv` after every run, records anything it could not start within its wall budget as `SKIPPED_BUDGET`, and has `--dry-run`, `--smoke` and `--analyse` modes. The `RESULTS_final.md` files are the hand-checked reports built from those records. A full round-3 rerun of all four experiments takes about 9 hours of solver time on 3 threads.

**Limits to keep in mind.**

- The street network is a synthetic grid with synthetic hills and traffic lights. Real restaurants and neighbourhoods are snapped onto it. Distances and energy use are therefore approximate.
- The window is 4 hours with 6 riders and 36 orders, the largest size the solver finishes in a few minutes. A real fleet is much bigger; the method scales by rolling the window or decomposing, not yet implemented.
- Costs are estimates with sources (see `notes/cost_calibration.md`), each with a low/base/high range. The choice to treat rider wages as already paid is a modelling decision, not a fact.
- The rule that stations must end the evening with half their spare batteries full is the only reason shuttles have any value in E3. Change that rule and the transfer results change.
- With 9 spare batteries for 6 riders, the battery side of the model (charging slots, station queues, grid limits) never binds in a 4-hour window, so these experiments say nothing about when it would. Larger fleets or longer windows are needed for that.
- Sample sizes are 10 seeds (E2u, E8), 6 (E4u battery sweep) and 5 (E3u); the charger and power sweeps of E4u still rest on 3 seeds, although their values are flat to 0.1 $. The simple rule's cost varies a lot from evening to evening (its intervals are 7 times wider than the model's), so every gap is computed evening by evening and the intervals on the gap stay at +/- 6 to 12 points.
- Three solver cells are not closed: the E3u "separated layout, shuttles allowed, targets as written" cells stop at a 1.8-2.0 % solver gap, so the value of shuttles there is a lower bound; two E2u cells and three E4u cells stopped within 0.3 % of optimal, which changes nothing.
- The 90 % service rule is impossible at 1.5 times normal demand with 6 riders; how many riders would make it possible, and at what cost, has not been run.
- The E8 gap is a lower bound because the NYC instance restricts the model's repositioning moves but not the rule's; the lossless check has not been run.

## 8. Data sources, licences and references

| Data | Source | Terms |
|---|---|---|
| Restaurant inspections | NYC Open Data, DOHMH dataset `43nn-pn8j` | NYC Open Data terms of use (free to use and share) |
| Cyclist crashes | NYC Open Data, Motor Vehicle Collisions `h9gi-nx95` | same |
| Bicycle counters | NYC Open Data `smn3-rzf9`, `uczf-rk3c` | same |
| Neighbourhood (NTA 2020) census profiles | NYC Department of City Planning, ACS 2020-2024 5-year tables; polygons from NYC Open Data `9nt8-h7nd` | Public US Census data, free to use |
| Neighbourhood ACS 2008-2012 (fallback only) | GeoDa Center sample data `nycnhood_acs` | Free for research and teaching |
| FoodHub orders (`food_order.csv`) | Kaggle, "Food Ordering and Delivery App Dataset" (ahsan81) | CC0 public domain |

Exact download commands, file sizes and checksums are in `data/MANIFEST.md`.

**Papers used for the demand model** (full texts not included; all are open access):

1. Buettner, S. A., Pasch, K. E., & Poulos, N. S. (2023). Factors associated with food delivery app use among young adults. *Journal of Community Health*. https://doi.org/10.1007/s10900-023-01229-1 (PMC10163566)
2. Bennett, R., Gomez-Donoso, C., Zorbas, C., Sacks, G., White, C. M., Hammond, D., Gupta, A., Cameron, A. J., Vanderlee, L., Contreras-Manzano, A., & Backholer, K. (2025). Prevalence of online food delivery platforms, meal kit delivery, and online grocery use in five countries: an analysis of survey data from the 2022 International Food Policy Study. *International Journal of Obesity*, 49(7), 1307-. https://doi.org/10.1038/s41366-025-01771-z (PMC12283340)
3. Tahim, J. C., Verde, S. M. M. L., Maia, C. S. C., & Bezerra, I. N. (2024). Consumption of food offered by delivery applications (apps). *International Journal of Environmental Research and Public Health*, 21(5), 568. https://doi.org/10.3390/ijerph21050568 (PMC11121648)

The optimisation model itself is the supervisor's "E2" formulation (unpublished working documents, 2026); the implementation conventions are recorded in `notes/DECISIONS.md`.
