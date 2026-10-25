# Reading list: top-conference papers on battery swapping, siting and delivery optimisation

Our project plans NYC food-delivery e-bike operations with an integer program on a time-expanded network (riders over location x 5-min slot x battery level, swap stations with charge-level inventory, chargers under a grid limit, optional battery shuttles), compared against an event-driven nearest-rider baseline.
On top of it, a bi-level / two-stage stochastic siting model chooses station locations, roles (S / C / SC) and sizes (spares B_j, chargers C_j) under a budget, with the E2 operations IP as the lower level per demand scenario.

All papers below are peer-reviewed full papers at conferences (WWW, IJCAI, NeurIPS, IEEE ITSC). Metadata was checked against Crossref DOI records and the official proceedings pages (DBLP was blocked by a bot check during collection). The PDFs in this folder are personal study copies: `*.pdf` is gitignored in this repository and is never pushed.

## Summary table

| Rank | Paper | Venue / year | Topic | Overlap with our work | File or link |
|---|---|---|---|---|---|
| 1 | Ding et al., eBaaS: AIoT-Enabled eBike Battery-Swap as a Service for Last-Mile Delivery | WWW 2025 (ACM Web Conference), pp. 5045-5053 | Deployed battery-swap network for delivery riders; impact evaluation on 260k riders | Same application (delivery e-bikes + city-wide swap cabinets); no exact IP, no grid limit, no siting | Gold OA: https://doi.org/10.1145/3696410.3714503 (PDF not in the repository) |
| 2 | Li et al., Optimizing the Battery-Swapping Problem in Urban E-Bike Systems with Reinforcement Learning | IJCAI 2025 (AI4Tech track), pp. 9259-9267 | Station battery rebalancing for courier e-bikes as an MDP, solved with Wasserstein-PPO | Station inventory + vehicle rebalancing (our shuttle block); daily granularity, no riders/orders, no siting | `2_IJCAI2025_Li_BatterySwappingRL.pdf` |
| 3 | Xiong et al., Optimal Electric Vehicle Charging Station Placement | IJCAI 2015, pp. 2662-2668 | Bilevel charging-station placement with an equilibrium (congestion game) follower | Budgeted bilevel siting reduced to a single level; follower is selfish drivers, not a central operator | `3_IJCAI2015_Xiong_EVChargingStationPlacement.pdf` |
| 4 | Dumouchelle, Patel, Khalil, Bodur, Neur2SP: Neural Two-Stage Stochastic Programming | NeurIPS 2022, pp. 23992-24005 | Learned surrogate of the second-stage value function embedded in a MIP | Solution method for our two-stage stochastic siting MIP (integer recourse = E2 IP) | `4_NeurIPS2022_Dumouchelle_Neur2SP.pdf` |
| 5 | Luke, Salazar, Rajagopal, Pavone, Joint Optimization of Autonomous Electric Vehicle Fleet Operations and Charging Station Siting | IEEE ITSC 2021, pp. 3340-3347 (lower tier than 1-4) | Station sizing jointly with fleet flows on a (location, time, SoC) graph, with demand charges | Closest model: same expanded-graph idea and siting-with-operations; LP, single scenario, plug charging only | `5_ITSC2021_Luke_FleetChargingSiting.pdf` |

---

## 1. eBaaS: battery-swap as a service for last-mile delivery (WWW 2025)

**Citation.** Donghui Ding, Zhao Li, Jiarun Zhang, Xuanwu Liu, Ji Zhang, Yuchen Li, Peng Cai, Jianxun Liu, Guodong Long. "eBaaS: AIoT-Enabled eBike Battery-Swap as a Service for Last-Mile Delivery." Proceedings of the ACM Web Conference 2025 (WWW '25), pp. 5045-5053. https://doi.org/10.1145/3696410.3714503 (ACM gold open access).

**File status.** The paper is gold open access (DOI link above); a local study copy exists but, like all PDFs here, is not in the repository. The notes below were written from the published abstract and bibliographic records before that copy was obtained. Check the details below against the PDF before citing specific numbers beyond the abstract.

**Why it matters for us.** It is the closest real-world counterpart of our setting at a top venue: on-demand delivery riders in China ride e-bikes, run out of battery, and use a city-wide network of swap cabinets. It gives deployment-scale evidence that a swap network reduces non-productive riding and raises orders per rider, which is the motivation for our objective (lateness + unserved orders + travel).

**Problem setting.** Delivery riders with limited battery capacity and long charging times lose working time to recharging or to detours for swaps. The operator runs distributed swap cabinets across the city and needs to (i) keep charged batteries available where riders need them, (ii) detect faulty batteries, (iii) predict remaining range, and (iv) quantify the system's impact.

**Model / method (from the abstract).** A system paper, not an optimisation-model paper. Components: edge-cloud collaboration between cabinets and the cloud, battery resource allocation across cabinets, battery anomaly detection, and battery range prediction (learned models). Impact is measured with the eBaaS Impact Evaluation Method (EIEM), a data-driven before/after style evaluation on rider trajectories. There is no explicit time-expanded integer program, no charger or grid-capacity model and no station-siting decision.

**Data and scale.** About 260,000 delivery riders and about 5 million riding trajectories from the operator.

**Main findings (abstract).** Average invalid (non-delivery) mileage reduced by about 6 km per rider per day; daily order volume per rider up by more than 20% on average; about 2.74 million kg of CO2 avoided per year across 260,000 riders.

**What we can borrow.**
- Motivation and an empirical yardstick: compare its 6 km/day detour reduction and +20% orders with our NYC numbers (swap detour km, served orders, late orders) for the IP vs the nearest-rider baseline.
- Its cross-cabinet battery allocation is the industrial counterpart of our station inventory by charge level and our shuttle-transfer variables.
- The EIEM idea (evaluate a policy on the same rider trajectories with and without the service) matches our paired comparison of the IP against the baseline on identical orders and bikes.

**Limitations vs our setting.** No exact joint optimisation of rider routing, swaps and station charging; no grid limit; no siting; China-specific operating data that we cannot access. Same industrial group (Zhao Li, Xuanwu Liu; Hangzhou Yugu / Zhejiang Lab) as paper 2 and reserve 2: cite the three together as the delivery e-bike battery-swap line.

---

## 2. Battery-Swapping Problem for urban e-bikes with RL (IJCAI 2025)

**Citation.** Wenjing Li, Zhao Li, Xuanwu Liu, Ruihao Zhu, Zhenzhe Zheng, Fan Wu. "Optimizing the Battery-Swapping Problem in Urban E-Bike Systems with Reinforcement Learning." Proceedings of IJCAI-25, Special Track on AI4Tech, pp. 9259-9267. https://doi.org/10.24963/ijcai.2025/1029. PDF: https://www.ijcai.org/proceedings/2025/1029.pdf

**Why it matters for us.** The only top-AI-venue paper found that optimises swap-station operations for delivery-courier e-bikes with real operator data. It is a learned counterpart to our station inventory and shuttle blocks, and a natural RL baseline to contrast with our exact time-expanded IP.

**Problem setting.** Couriers swap batteries at stations; a battery taken at one station is often returned at another, so stations drift into surplus or shortage of charged batteries (supply-and-demand imbalance). Stations are clustered into non-intersecting cyclic routes; one vehicle per route circulates and picks up or drops off batteries to rebalance stocks. Batteries left in stations are assumed fully charged overnight.

**Model.**
- Network G = (C, R): stations C_i with slot count X_i, users Y_i^t, stock B_i^t, demand D_i^t (daily swap orders), returns L_i^t (modelled as normal). Stock update B_i^t = max(B_i^{t-1} - D_i^t, 0) + L_i^t + x_j^t, where x_j^t is the (signed) number of batteries moved by the route vehicle.
- Formulated as a discrete-time MDP whose step is a day (states cycle Night -> Morning -> next Night). Action per route: integer pick-up / drop-off per station, summing to zero over the route, bounded by a range such as [-7, 7].
- Reward: minimum over stations of the Shared Battery Utilisation Ratio SBUR_i^t = D_i^t / B_i^t. A second KPI, the Battery Supply Ratio BSR_i^t = Y_i^t / ((1 + SBUR_i^t) X_i), measures how many riders the stock can support.
- Method: PPO whose KL penalty is replaced by a 1-D Wasserstein (earth mover's) distance between old and new policies, with an adaptive penalty weight (W-PPO). Baselines: SAC, PPO without penalty, PPO-KL, PPO-clip.

**Data and scale.** Operator data on more than 500,000 batteries and 30,000 stations in more than 80 cities; experiments use one month (31 days) of daily station data; KNN clustering into routes of 3 to 11 stations; most stations hold 10 to 20 batteries.

**Main findings.** W-PPO is best for routes of 5 and 7 stations (PPO without penalty wins at 3 stations). The best configuration (7 stations per route, action range [-7, 7]) gives +30.59% average SBUR and +16.09% BSR; with Shanghai data this translates into 45.55% more riders served for the same battery stock, or 3,972 batteries saved. Larger routes degrade because the area exceeds an efficient delivery range.

**What we can borrow.**
- SBUR and BSR as extra station-side KPIs for our station inventory (by charge level) and transfer block, reported next to cost.
- Their route-based vehicle rebalancing is a coarse version of our shuttle transfers; W-PPO (or plain PPO) can be cited, or re-implemented on our simulator, as a learning baseline against the IP.
- Their finding that per-route cluster size has a sweet spot is a useful qualitative check for our candidate-site spacing in the siting study.

**Limitations vs our setting.** Daily time step (we use 5-minute slots); no individual riders, orders, lateness or battery charge levels; charging is implicit (overnight full charge), with no charger count or grid limit; results reported as percentage improvements without cost; no siting; the method is hyperparameter-sensitive (stated by the authors).

---

## 3. Optimal EV charging station placement (IJCAI 2015)

**Citation.** Yanhai Xiong, Jiarui Gan, Bo An, Chunyan Miao, Ana L. C. Bazzan. "Optimal Electric Vehicle Charging Station Placement." Proceedings of IJCAI-15, pp. 2662-2668. https://www.ijcai.org/Abstract/15/377. PDF: https://www.ijcai.org/Proceedings/15/Papers/377.pdf

**Why it matters for us.** A top-AI-venue precedent for budgeted bilevel station siting in which the lower level determines service quality, and for turning the bilevel model into a single-level program. No top-conference paper on swap-station placement was found, so this is the siting anchor for the upper level of our model.

**Problem setting.** A government places charging stations (number of chargers per zone) in Singapore under a budget. EV drivers choose where to charge to minimise their own time cost (travel time with congestion + queueing at the station); their choices change road congestion and queues. The planner minimises total social cost at equilibrium.

**Model.**
- Decision variables: upper level x_i = integer number of chargers in zone i with sum x_i <= B; lower level p_ij = mixed strategy of EVs resident in zone i to charge in adjacent zone j.
- Costs: travel f_ij = lambda d_ij alpha_ij with congestion alpha_ij = alpha0_ij + k_ij y_ij / tau; queueing g_i = y_i / (mu tau x_i) (proportional to peak-hour arrivals over charger capacity).
- Formulation: bilevel program (P1) whose follower is a congestion game with Nash equilibrium constraints. Using the quadratic structure of each player's cost change, they show that checking only "simple deviations" (moving probability between two choices) is enough, giving a finite set of equilibrium conditions xi_ih >= xi_il when p_il > 0. The result (P3, OCEAN) is a single-level mixed-integer nonlinear program solved with KNITRO.
- OCEAN-C heuristic: relax x to continuous, solve, round, then re-solve with x fixed.

**Data and scale.** Singapore split into 23 zones; vehicle counts proportional to residents (5% EVs, 10% of them charging at stations); peak-hour congestion from Google Maps travel times; budget of 300 chargers; exact OCEAN tested on 6 to 10 merged zones.

**Main findings.** OCEAN-C reaches the same social cost and solution as OCEAN on the small instances with much lower and slower-growing run time; on 23 zones it beats demand-proportional, congestion-based and uniform allocations for every budget and demand level, and stays best when drivers deviate by 10% from equilibrium. Allowing charging two zones away changes the cost by less than 0.001 out of about 4,300.

**What we can borrow.**
- The budgeted bilevel structure and the single-level reformulation argument to position our upper level (location, role S/C/SC, B_j, C_j) and to explain why our model collapses to a two-stage stochastic MIP: our follower is a central coordinator minimising the same cost as the planner, not selfish drivers.
- The exact-plus-heuristic pairing (OCEAN vs OCEAN-C) mirrors our integrated stochastic MIP vs greedy + local search; their relax-round-fix scheme is a cheap extra heuristic for our sizes B_j, C_j.
- Their baselines (demand-proportional, uniform allocation) are simple planner rules we can add next to our "deck heuristic".

**Limitations vs our setting.** Static peak-hour model with no time dimension, no battery levels and no inventory; private cars rather than a coordinated delivery fleet; follower is a user equilibrium; zone-level resolution; plug charging, not swapping.

---

## 4. Neur2SP: neural two-stage stochastic programming (NeurIPS 2022)

**Citation.** Justin Dumouchelle, Rahul Patel, Elias B. Khalil, Merve Bodur. "Neur2SP: Neural Two-Stage Stochastic Programming." Advances in Neural Information Processing Systems 35 (NeurIPS 2022), pp. 23992-24005. https://doi.org/10.52202/068431-1742. PDF: https://proceedings.neurips.cc/paper_files/paper/2022/file/9793671e4be9858a69a32545204d59d1-Paper-Conference.pdf (also arXiv 2205.12006). Author order: the paper PDF lists Dumouchelle and Patel first with equal contribution; the Crossref record lists Patel first. Use the order on the PDF.

**Why it matters for us.** Our integrated siting benchmark is exactly a two-stage stochastic integer program: first stage y, role, B, C; second stage one copy of the E2 operations IP per demand scenario. Neur2SP is the most directly usable top-venue method for making that tractable as the number of scenarios grows, and its benchmarks include two-stage capacitated facility location.

**Problem setting.** min_x c'x + E_xi[Q(x, xi)] where Q is the optimal value of a MIP or NLP second stage. The extensive form grows linearly in the number of scenarios and becomes intractable with integer recourse.

**Method.**
- Train a ReLU network offline to predict the second-stage cost. NN-E predicts the expected cost of a whole scenario set (scenarios are embedded with a DeepSets-style encoder and mean pooling, so only one network copy enters the MIP); NN-P predicts the cost of a single scenario (one copy per scenario).
- Data: sample random feasible first-stage decisions, solve the second-stage problems (parallel, under 2 s per sample), about 5,000 samples suffice.
- Embed the trained network into a MIP with the big-M ReLU encoding (one binary per hidden unit) and solve the surrogate "MIP-NN" with Gurobi; then optionally recompute the true second stage for the chosen x.

**Data and scale.** Synthetic benchmarks: capacitated facility location (up to 50 facilities x 50 customers, 100 to 1,000 scenarios), stochastic server location (SIPLIB), an investment problem (up to 10,000 scenarios) and a pooling problem.

**Main findings.** NN-E solves every surrogate in 0.11 to 1.66 s, independent of the number of scenarios; the extensive form often hits the 3-hour limit and, on the largest facility-location and server-location instances, ends with solutions 10% to more than 100% worse than NN-E. NN-P is cheaper to train but scales poorly in the number of scenarios. Offline data generation plus training takes from minutes to about 3 hours.

**What we can borrow.**
- A learned upper-level solver: train NN-E mapping (y_j, role, B_j, C_j) plus a scenario-set embedding of the demand seeds to the expected E2 operating cost, using the lower-level solves we already cache, then embed it in the budgeted siting MIP and compare with the integrated stochastic MIP (algorithm A), enumeration (B) and greedy + local search (C).
- The paper also gives the standard argument for why the extensive form fails with integer recourse, which supports reporting our algorithm A only on small instances.

**Limitations vs our setting.** Heuristic with no optimality guarantee; needs thousands of lower-level E2 solves for training, each far more expensive than their second stages; no mobility or energy application; assumes the planner and operator share one objective (if they diverge, see Neur2BiLO in the reserves).

---

## 5. Joint fleet operations and charging station siting (IEEE ITSC 2021)

**Citation.** Justin Luke, Mauro Salazar, Ram Rajagopal, Marco Pavone. "Joint Optimization of Autonomous Electric Vehicle Fleet Operations and Charging Station Siting." 2021 IEEE International Intelligent Transportation Systems Conference (ITSC), pp. 3340-3347. https://doi.org/10.1109/ITSC48978.2021.9565089. PDF: https://arxiv.org/pdf/2107.00165. Note: ITSC is a lower-tier venue than 1-4; it is included because its model is the closest to ours.

**Why it matters for us.** Methodologically the closest conference model to our full pipeline: it sizes charging stations at candidate sites jointly with fleet routing and charging on a graph expanded over (location, time step, battery level), with time-of-use energy prices and demand charges in the objective.

**Problem setting.** An autonomous electric ride-hailing fleet must serve all San Francisco travel demand on a weekday. The operator chooses fleet size, the number of plugs of each charging rate at each zone, and the routing / rebalancing / charging of the fleet, minimising total cost.

**Model.**
- Expanded multigraph with vertices (location, time step, SoC level); travel arcs (time and SoC move by the trip's duration and energy), idle arcs and charging arcs (one step, any rate up to the station rating, allowing charge throttling).
- Decision variables: vehicle flow f on each arc, plugs per station type S_(v, delta), peak power P_max_v per location, fleet size n_fleet.
- Constraints: every request served exactly (hard), flow conservation, periodicity (end state = start state), peak-power definition, and nested plug-capacity constraints that let slower charging use spare faster plugs.
- Objective: energy cost with TOU prices + demand charge on peak load + distance-based maintenance + fleet procurement + station procurement (amortised).
- Formulation type: one linear program (flows fractional, integer plugs relaxed), solved with Gurobi; no upper/lower level split, single deterministic demand scenario.

**Data and scale.** StreetLight 2019 weekday OD demand aggregated to 25 city zones + 3 pass-through zones (2.89 million requests); 96 fifteen-minute steps; SoC 0.2 to 0.8 in 0.74 kWh steps (23 to 62 levels); four station types (7.7 / 16.8 / 50 / 150 kW); PG&E business EV tariff. The Leaf S instance has 5.3 million variables and solves in 2.33 h.

**Main findings.** The smallest, most efficient EV gives the lowest total cost; fleet procurement dominates (78% to 84% of cost) and charging is shifted away from the 4-9 pm peak price. Versus a scaled-up present-day layout, the optimised layout is more spatially spread, uses mostly 16.8 kW Level 2 plugs (64% less DC fast capacity), and cuts total cost by 9.6%, station cost by 31%, rebalancing distance by 11% and peak charging load by 10%.

**What we can borrow.**
- The (location x time x SoC) expanded graph with travel, idle and charging arcs is a direct, citable precedent for our time-expanded rider network.
- The demand-charge term (peak kW per site priced in the objective) complements our hard grid limit; it can be added to our electricity cost as a sensitivity.
- The nested multi-rate plug constraints suggest a way to offer several charger types at a site in our size menu (C_j).
- Their "optimised vs scaled-up present-day layout" experiment is the template for our comparison of the bi-level choice against the deck heuristic and the landmark siting.
- Their result that a distributed, mostly slow-charger layout wins is a comparison point for our finding that one combined SC site dominates under fixed-cost pressure.

**Limitations vs our setting.** Macroscopic fractional flows (thousands of cars), so no individual riders, orders, lateness or unserved orders; plug charging only, no swap inventory by charge level and no battery shuttles; single deterministic scenario; LP relaxation of integer sizes; no explicit grid capacity, only a demand charge.

---

## Reserves

- Dumouchelle, Julien, Kurtz, Khalil, "Neur2BiLO: Neural Bilevel Optimization", NeurIPS 2024, pp. 86688-86719, https://doi.org/10.52202/079017-2752: the bilevel counterpart of Neur2SP (learned lower-level value function in a single-level MIP), to use if planner and operator objectives diverge.
- Li, Liu, Yang, Dai, Zhang, Jiao, "Talking Trails: LLM-Enhanced Spatiotemporal Trajectory Modeling for E-Bike Delivery Route Planning", AAAI 2026 (IAAI deployed applications), pp. 40054-40062, https://doi.org/10.1609/aaai.v40i47.41440: rider-level delivery routing with swap insertion and energy feasibility from the same operator as eBaaS; learning-based, no station inventory or siting.
- Du, Tong, Zhou, Tao, Zhou, "Demand-Aware Charger Planning for Electric Vehicle Sharing", KDD 2018, pp. 1330-1338, https://doi.org/10.1145/3219819.3220032: budgeted siting and charger sizing for a shared fleet with a submodular greedy (1 - 1/e) guarantee, a counterpart of our greedy + local search; no time-expanded operations.

## Suggested reading order

1. Paper 5 (ITSC 2021): closest model; read Section II next to our E2 formulation and the siting design note.
2. Paper 2 (IJCAI 2025): the same application on the station side; note the KPIs and the rebalancing action.
3. Paper 1 (WWW 2025): download from the DOI link in a browser; read for motivation numbers and the impact-evaluation method.
4. Paper 3 (IJCAI 2015): bilevel siting precedent; read Sections 3-4 for the single-level reformulation.
5. Paper 4 (NeurIPS 2022): solution method for the two-stage siting MIP; read Sections 2 and 4 before deciding whether to add a learned upper-level solver.
