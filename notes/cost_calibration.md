# USD cost calibration of the E2 objective (26)–(32) (NYC e-bike food delivery, 2025–2026 prices)

Machine-readable parameters: `notes/data/cost_calibration_usd.json` (base/low/high per symbol, in model units: Δ = 5 min, 4 h planning window, H = 48; the keys of the `generator_overrides` block match `DEFAULT_COSTS` / `DEFAULT_DEMAND_SPEC` / `DEFAULT_SERVICES_SPEC` in `ebike_swap_sim.generator` and can be passed directly as `costs=` / `demand_spec=` / `services_spec=`). All arithmetic of the generating script is written in the JSON's `derivation` field. Date: 2026-10-12.

Objective (`notes/extracted/E2.txt` p. 9):
min C_setup + C_elec + C_travel + C_orders + C_reb,
C_setup = Σ_j (F_j y_j + b^B_j B_j + b^C_j C_j); C_elec = Σ π_jt (ε/η) Σ_q c_jqt; C_travel = κ Σ d_a x_ka;
C_orders = Σ P_i u_i + Σ θ_ia x_ka, θ_ia = w_i Δ (u_a − r_i) + v_i Δ [u_a − b_i]_+; C_reb = Σ_e (f_e h_e + Σ_q v^reb_eq z_eq);
budget (33): Σ_j (F̂_j y_j + b̂_j B_j + ĉ_j C_j) ≤ B.

---

## 0. Summary table

| Symbol | Meaning | Model unit | Low | **Base** | High | Confidence |
|---|---|---|---|---|---|---|
| κ | riding cost (29) | $/km | 0.12 (pure wear) | **0.50** (wear + 25% of labour not covered by w_i) | 1.60 (labour + wear in full) | medium |
| w_i | response-time price (31) | $/h (×1/12 per slot) | 22 (2026 minimum wage) | **40** (rider 22 + customer 18) | 60 (active-time rate 36.9 + customer 24) | medium |
| v_i | lateness-beyond-promise price (31) | $/h | 40 | **80** (= 2 w) | 120 (= 3 w) | low–medium |
| P_i | unserved-order penalty (30) | $/order | 15 (platform fee revenue only) | **30** (platform 13.25 + restaurant increment 5.3 + churn 10) | 60 (full ticket 40.15 + churn 20) | medium |
| π_jt | electricity price (28) | $/kWh | 0.22 (NY State commercial average) | **0.32** (ConEd SC2 supply 12.06¢ + delivery 17.19¢, ×1.08 taxes/fees) | 0.40 (summer) | high |
| π TOU variant | peak / off-peak | $/kWh | off-peak 0.13 | peak 0.44 (Oct–May) | peak 0.74 (Jun–Sep) | high |
| f_e | shuttle start-up (32) | $/run | 12 | **20** (cargo bike 35 min × $33/h) | 35 (cargo van + $9 congestion charge) | medium |
| v^reb | per transported battery (32) | $/battery | 0.5 | **1.0** | 2.5 | low |
| F_j | swap station, allocated to a 4 h window (27) | $/station/4 h | 4.0 | **12.0** (17,319/yr → 48.1/day × 4/16) | 29.0 | low |
| F_hub | charging hub, same rule | $/station/4 h | 12.4 | **29.2** | 63.8 | low |
| b^B_j | spare battery (incl. initial full charge) (27) | $/battery/4 h | 0.21 | **0.33** (holding 0.12 + initial charge 0.21) | 0.55 | medium |
| b^C_j | charging slot (27) | $/slot/4 h | 0.015 | **0.08** | 0.23 | low |
| F̂_j | station investment (33) | $/station | 20,000 | **50,000** | 130,000 | low |
| b̂_j | battery investment (33) | $/battery (600 Wh) | 300 | **450** (1 kWh class: 400/600/800) | 700 | medium |
| ĉ_j | charging-slot investment (33) | $/slot | 100 | **400** | 900 | low |

Allocation rule (see §8): annual cost = capex × CRF(r, lifetime) + annual opex; cost per window = annual cost / 12 / 30 days × window length / daily operating hours (16 h). F, F_hub, b^B, b^C scale linearly with the window length (2 h window ×0.5, 8 h window ×2); κ, π, w, v, P, f, v^reb do not depend on the window length.

---

## 1. Labour-time and speed facts

| Fact | Value | Source |
|---|---|---|
| NYC DCWP delivery-worker minimum pay (on-call time basis, excluding tips) | 2024-04-01 $19.56; 2025-04-01 **$21.44**; 2026-04-01 **$22.13** | [DCWP Minimum Pay Rate](https://www.nyc.gov/site/dca/workers/Delivery-Worker-Public-Hearing-Minimum-Pay-Rate.page), [DCWP Delivery Workers](https://www.nyc.gov/site/dca/workers/workersrights/Delivery-Workers.page) |
| Alternative method (pay only trip time) rate = standard rate / 0.60 | 2025 $35.73; 2026 $36.88 | same (60% utilisation) |
| DCWP 2024 Q4 actuals (weekly averages): trip hours 888k, on-call 186k, total pay $21.2M, deliveries 2.72M | pay per trip hour **$23.87**; trip time per delivery **19.6 min**; deliveries per hour 2.53 | [DCWP Q4 2024](https://home4.nyc.gov/assets/dca/downloads/pdf/workers/Restaurant-Delivery-App-Data-Q4-2024.pdf) |
| E-bike speed limit 15 mph (from 2025-10-24) | cruising ≤ 24 km/h, effective **~15 km/h** including red lights/stops (config 250 m/min) | [Electrek 2025-06](https://electrek.co/2025/06/05/its-official-nyc-will-impose-a-new-15-mph-speed-limit-on-electric-bikes/), [NYU C2SMART/NYSERDA 25-38](https://c2smart.engineering.nyu.edu/wp-content/uploads/2026/04/25-38-NYC-Delivery-Worker-Data-Collection-and-Research-Report.pdf) |
| Rider hours: 73.7% work ≥ 7 h per day, 86% work > 5 days per week | used for the 16 h daily operating-hours allocation assumption | C2SMART report §3.2.2 |

---

## 2. κ: riding cost ($/km)

Split into (a) labour time = wage / speed, (b) vehicle wear.

| Component | Low | Base | High | Formula / source |
|---|---|---|---|---|
| Labour $/km | 1.13 | **1.48** | 3.07 | 21.44/19 ; **22.13/15** ; 36.88/12 |
| Whole-vehicle depreciation $/km | 0.060 | **0.080** | 0.162 | bike price $1,490–1,949 (Whizz Storm-2 $1,490, Arrow $1,500–1,800, Fly $1,949) / lifetime 25k–12k km; [Whizz vs Arrow](https://www.getwhizz.com/blog/how-to-choose/whizz-or-arrow), C2SMART Appendix A.3 |
| Maintenance $/km | 0.025 | **0.045** | 0.075 | $300–600/yr ÷ 8k–12k km/yr; [RideshareGuy courier example 6¢/mi](https://therideshareguy.com/you-cant-claim-standard-mileage-on-an-e-bike-what-couriers-should-track-instead/), [Hovsco](https://hovsco.com/blogs/news/what-are-e-bike-annual-maintenance-costs) |
| **Pure wear κ_wear** | 0.085 | **0.125** | 0.237 | |
| **Full κ_full = labour + wear** | 1.21 | **1.60** | 3.31 | |

**Which one to use?** w_i prices (u_a − r_i) of every served order, and the riding time on a delivery arc (to the restaurant + to the customer) falls entirely inside that window; if w_i already includes the rider wage, charging full labour again in κ is double counting. But riding that is **not inside any order response window** (to a swap station, empty repositioning, end-of-horizon return) can only be priced through κ. In the toy example that share is 1/4 (1 km of 4 km); in real delivery operations the empty-riding share is also 15–30%. Therefore:

- **Recommended (option A, default)**: κ = κ_wear + 0.25 × labour = 0.125 + 0.37 ≈ **0.50 $/km**, with w_i including the rider wage (§3).
- low = pure wear 0.12 (assumes all riding is inside response windows); high = full 1.60 (assumes a lot of empty riding, or option B).
- **Option B (clean split, JSON `variants.option_B_clean_split`)**: κ = 1.60 prices labour on all arcs, w_i contains only the customer waiting value (18 $/h). Advantage: does not price prep waiting (a_i − r_i, when the rider is not actually present) as rider time; disadvantage: the hp+hd pickup/drop-off slots of labour (about 4.5 min ≈ $1.7/order) are priced nowhere.
- If the implementation allows κ by arc type: 0.12 on delivery arcs, 1.60 on repositioning/swap arcs — this is the most accurate approach.

Addendum: cycle wear of the rider's on-board battery is about 12 Wh/km × $0.83/kWh ≈ $0.01/km, already counted for system batteries through b^B / π_eff (§5), so it is not put into κ.

---

## 3. w_i: response-time price ($/h)

| Component | Low | Base | High | Source |
|---|---|---|---|---|
| Rider time (platform marginal cost) | 22.13 | **22.13** | 36.88 (alternative method, trip time only) | DCWP |
| Customer waiting value | 0 | **18** | 24 | DoorDash Express $1.99–2.99 for "front of the queue" (saves about 5–10 min) → 12–36 $/h ([Ridester](https://www.ridester.com/is-doordash-cheaper-than-uber-eats)); Uber Eats Priority $0.99–2 for about 5 min → 12–24 $/h ([Tecnoblog reporting Uber's announcement](https://tecnoblog.net/345906/uber-eats-tera-taxa-para-receber-delivery-mais-rapido/)); Tillster survey: 30% willing to pay more for faster delivery ([Restaurant Dive](https://www.restaurantdive.com/news/majority-of-qsr-fast-casual-diners-would-pay-up-to-5-in-delivery-fees/551257/)); USDOT local personal travel time value $13.6/h (2015 USD, [FAA reprint](https://www.faa.gov/regulations_policies/policy_guidance/benefit_cost/econ-value-section-1-tx-time.pdf)) ≈ $18/h (2025 USD) |
| **w_i** | **22** | **40** | **60** | per slot wΔ = 1.83 / **3.33** / 5.00 |

A preliminary Bocconi study of Italian platforms claims "each minute of waiting is worth about 15% of the order value", which converts to >$200/h; treated as an outlier and not used.

## 4. v_i: lateness-beyond-promise price ($/h)

| Evidence | Conversion |
|---|---|
| DashPass Premium: automatic $10 credit when ≥ 10 min later than the latest delivery time ([DoorDash terms](https://help.doordash.com/es-us/consumers/article/premium-delivery-terms-and-conditions)) | about 60 $/h (step function) |
| Grubhub Guarantee: ≥ $5 Perks for lateness, capped at $15 ([Restaurant Dive](https://www.restaurantdive.com/news/grubhub-gives-diners-perks-to-offset-late-deliveries-lower-competitor-pric/603163/)) | 20–30 $/h |
| Uber Eats: Uber Cash worth 20% of the order for lateness ($29 subtotal → $5.8, third-party guides) | about 25–35 $/h |
| 2/3 of respondents say they stop ordering from a platform after a late delivery (stated intention, [Circuit 2022](https://getcircuit.com/route-planner/blog/expectations-of-delivery)) | churn risk, supports v > compensation |

Take **v_i = 2 w = 80 $/h** (low 40 ≈ Grubhub $5/15 min + rider wage; high 120 = 3 w). Per slot vΔ = 3.33 / **6.67** / 10.0.

## 5. P_i: unserved-order penalty ($/order)

DCWP 2024 Q4 NYC weekly averages: order subtotal **$29.04**, consumer fees $7.55, merchant commission $5.70 (19.6% of subtotal), tip $0.99, full ticket $40.15.

| Component | $ | Note |
|---|---|---|
| Platform fee revenue (consumer fees + merchant commission) | 13.25 | rider pay is a given resource in E2 (paid by on-call time) and treated as sunk, so the platform loses its full revenue |
| Restaurant incremental contribution | 5.27 | 29.04 × (1 − 0.196 commission − 0.32 food − 0.03 packaging) = 13.18 gross contribution × 40% incremental share ([Lightspeed restaurant margins](https://www.lightspeedhq.com/blog/complete-guide-to-restaurant-profit-margins/); delivery is only 30–50% incremental) |
| Customer churn | 10 | churn probability ~20% × future platform gross profit ~$50/yr (DoorDash 2025: net revenue margin 13.4%, GOV/order ≈ $32 → $4.3/order, [DoorDash 10-K FY2025](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm)) |
| **Total → P_i base** | 28.5 → **30** | low 15 (platform revenue only); high 60 (full ticket 40.15 + churn 20) |

## 6. π_jt: electricity price ($/kWh)

Con Edison small-commercial SC2, NYC Zone J ([trailing 12-month supply price PDF](https://www.coned.com/-/media/files/coned/documents/business-partners/escos-news/con-edison-trailing-12-month-average-supply-prices.pdf), 2025-07 to 2026-06; [TOU delivery page](https://www.coned.com/en/accounts-billing/your-bill/time-of-use)):

| Item | ¢/kWh |
|---|---|
| Supply Rate I (flat) | 12.06 |
| Supply Rate II peak / off-peak | 14.09 / 10.25 |
| Standard delivery summer (Jun–Sep) / other | 20.38 / 17.19 |
| TOU delivery peak (Mon–Fri 8:00–22:00) summer / other; off-peak | 54.43 / 26.80; 1.99 |
| Monthly basic charge standard / TOU | $33 / $34 |

- **Flat base = (12.06 + 17.19) × 1.08 (sales tax + GRT etc.) = 0.316 → 0.32 $/kWh**; summer 0.35; ConEd's own example (600 kWh monthly bill $202.44 ≈ 33.7¢, [About rates](https://coned.com/en/accounts-billing/your-bill/about-con-edisons-rates)) agrees. low 0.22 = NY State commercial average (EIA/NYSERDA, 2025-01 20.4¢, 2026-01 22.3¢, [NYSERDA](https://www.nyserda.ny.gov/Energy-Prices/Electricity/Monthly-Avg-Electricity-Commercial)).
- **TOU variant**: peak (14.09 + 26.80) × 1.08 = **0.44** (Oct–May) / (14.09 + 54.43) × 1.08 = **0.74** (Jun–Sep); off-peak (10.25 + 1.99) × 1.08 = **0.13**. The dinner window lies entirely in the peak period, so when the generator uses TOU, `peak_hours` should be (8, 22) rather than (18, 20).
- In-model cost per level step π ε/η = 0.32 × 0.05/0.9 = **$0.018**; charging one 600 Wh battery fully **$0.21**. Electricity is almost negligible in the USD system (see §9).
- **Battery cycle wear** is not in (28), but its magnitude is 2.6× the electricity price: $450 / (900 cycles × 0.6 kWh) = **$0.83/kWh**. To include it, set π_eff = 0.32 + 0.83 = 1.15 $/kWh (JSON `variants.pi_with_battery_cycle_wear`).

## 7. f_e, v^reb: battery transfers

| Component | Low | Base | High | Source |
|---|---|---|---|---|
| Transfer-worker wage | 22.06 | 24.0 | 25.0 | BLS OEWS 43-5021 couriers, NYC metro mean $22.06/h (2023-05); 53-3033 light-truck drivers NY State $22.92 ([BLS](https://www.bls.gov/oes/2023/may/oes435021.htm)) |
| With taxes/benefits factor ×1.3 + cargo e-bike ($7,000/3 yr + $1,000/yr maintenance ÷ 2,000 h) $1.83/h | 30.5 $/h | **33.0 $/h** | 32.5 $/h (van driver) | |
| One-way 20–30 min + loading/unloading 10 min (generator `handling_min` = 10) | 25 min | **35 min** | 40 min | |
| Vehicle increment | – | – | van $0.83/mi × 3 mi + Manhattan congestion charge $9 ([E-Transit TCO](https://caredge.com/ford/e-transit-350-cargo-van), [congestion charge](https://ecommercefastlane.com/best-courier-services-new-york-city/)) | |
| **f_e** | 12.7 → **12** | 19.3 → **20** | 33.2 → **35** | market check: Metrobi local delivery $10–15/stop |
| **v^reb** | **0.5** | **1.0** | **2.5** | per battery 2 × 0.5–1 min handling × $33/h ≈ 0.55–1.1, plus opportunity cost of payload |

## 8. F_j, b^B_j, b^C_j and F̂, b̂, ĉ: facilities

**Capital recovery factor** CRF(r, n) = r(1+r)^n / ((1+r)^n − 1): CRF(7%,10 y) = 0.1424, CRF(7%,3 y) = 0.3811, CRF(7%,5 y) = 0.2439; low uses 5%, high uses 10%.

**Allocation rule**: cost per window = (capex × CRF + annual opex) / 12 / 30 days × window length h / 16 operating hours per day. 4 h window = daily cost × 0.25.

### 8.1 Swap station F_j (16-slot sidewalk cabinet)

| Component | Low | Base | High | Source |
|---|---|---|---|---|
| Cabinet | 5k | 15k | 30k | Chinese manufacturers bare cabinet $1,890–2,130 ([HelloSwap](https://m.made-in-china.com/company-hellopower/)); V-Green with 11 batteries $8,235 ([Vietnam News](https://vietnamnews.vn/economy/1724555/v-green-launches-battery-swapping-cabinet-franchise-model.html)); US UL/FDNY-certified cabinets have no public price, take 3–6× |
| Electrical connection + construction | 10k | 25k | 90k | DOT: NYSERDA $3M / 25 right-of-way sites ≈ $120k/site, "mostly for laying the electrical connection" ([East Side Feed](https://eastsidefeed.com/odds-and-ends/two-upper-east-side-locations-made-the-citys-e-bike-charging-shortlist-and-the-clock-is-ticking-to-weigh-in/)); private lots/sidewalk RC are connected by the owner, far cheaper |
| Design, permits | 5k | 10k | 10k | RC application fee $750 + public-notice advertising $1,250 + deposit $3,000 (refundable) + PE/RA drawings + PDC review ([DOT Cabinets 101, 2025-04](https://www.nyc.gov/html/dot/downloads/pdf/sidewalk-e-bike-battery-swapping-charging-cabinets-101.pdf)) |
| **F̂_j capex** | **20k** | **50k** | **130k** | |
| Annual opex: site compensation/rent | 25 (RC annual fee $25) | 4,800 ($400/month, one parking-space-sized private site) | 12,000 | DOT 101; Manhattan retail rents of $400–700/ft²/yr do not apply to a 1 m² cabinet |
| Insurance, maintenance/communications | 2,000 + 1,200 | 3,000 + 2,400 | 5,000 + 3,600 | DOT 101 requires insurance; PopWheels self-operated maintenance |
| **Annual cost** | 5,815 | **17,319** | 41,757 | |
| **F_j (4 h window)** | **4.0** | **12.0** | **29.0** | 17,319/360 = 48.1 $/day × 4/16 |
| **F_hub (charging hub, 2 cabinets + site)** | 12.4 | **29.2** | 63.8 | capex 50k/100k/250k, opex 11.4k/27.8k/51.2k |

Cross-check: PopWheels charges riders **$75/month** for unlimited swaps (early $65–95; [TechCrunch](https://techcrunch.com/?p=3085306), [Canary Media](https://www.canarymedia.com/articles/food-and-farms/startup-helps-food-carts-switch-to-batteries)), and active users in the DOT pilot swap 8–14 batteries per week ([Safer Charging, Safer Deliveries](https://www.nyc.gov/html/dot/downloads/pdf/safer-charging-safer-deliveries.pdf)) → about $1.5–2 revenue per swap; a 16-slot cabinet does 30–60 swaps per day → $50–100 daily revenue, consistent in magnitude with the base daily cost of $48 + batteries/electricity, so the F_j base is credible.

### 8.2 Spare battery b^B_j

| Item | Low | Base | High | Source |
|---|---|---|---|---|
| 1 kWh class (48 V 20 Ah) UL2271 battery price | 400 | 600 | 800 | Whizz Storm-2 battery $500 (1.2 kWh), used $200 (C2SMART Appendix A.3.2); EM3ev 48 V $500–800 ([Leoguar](https://leoguarbikes.com/blogs/news/electric-bike-battery-replacement-cost)); Radio Flyer 48 V 15 Ah UL2271 $499 ([Radio Flyer](https://radioflyer.com/products/spare-battery-via-via-pro)); BNEF 2025 NMC large-pack $128/kWh as lower bound ([BNEF](https://about.bnef.com/insights/clean-transport/lithium-ion-battery-pack-pr)) |
| Model 600 Wh battery price **b̂_j** | 300 | **450** | 700 | scaled at ≈ $625/kWh, UL-certified small packs have a price floor |
| Cycle life / calendar life (swap service about 1 cycle/day) | 1000 / 4 y | 900 / 3 y | 800 / 2 y | JRC 2026 commercial e-bike batteries 400 cycles <10% fade ([JRC144270](https://publications.jrc.ec.europa.eu/repository/handle/JRC144270)); DCWP survey: riders replace batteries every 1.74 years (C2SMART Appendix E) |
| Holding cost / 4 h | 0.059 | 0.119 | 0.280 | 450 × 0.3811 = 171.5/yr → 0.476/day × 0.25 |
| Initial full charge (E2: counted in b^B) | 0.147 | 0.213 | 0.267 | 0.6/0.9 × π |
| **b^B_j** | **0.21** | **0.33** | **0.55** | 1 kWh battery variant: 0.31 / 0.50 / 0.75 |

### 8.3 Charging slot b^C_j

48 V 5 A UL charger $50–100 ([EbikeKit dealer price $52](https://dealers.ebikekit.com/products/48v-charger-dealer)) + allocated in-cabinet slot electronics/structure → slot capex **ĉ_j = 100 / 400 / 900**; lifetime 7/5/4 years, plus 5% annual maintenance → **b^C_j = 0.015 / 0.08 / 0.23 $/slot/4 h**. Note the SC2 small-commercial rate requires demand ≤ 10 kW; 16 slots × 0.667 kW = 10.7 kW already exceeds it, and real operators use trickle/staggered charging (PopWheels trickles after 90%, stops at 95%).

---

## 9. Toy units vs USD: how the ratios change

Toy units (E2 p.14 + `DECISIONS.md`): κ = 1/km, π = 2/kWh, P = 100, w = 12/h (wΔ = 1), v = 24/h, f = 5, v^reb = 0.2, F = 20, b^B = 3, b^C = 2 (per 2 h horizon).

| Ratio | Toy | USD base (option A) | USD option B | USD P low / w high | USD P high / w low |
|---|---|---|---|---|---|
| **P_i / (w_i × typical response time)** | **50** (100 / (1 × 2 slots)) | **1.5** (30 / (40 × 0.5 h)) | 3.3 (30 / (18 × 0.5)) | 0.5 | 5.5 |
| κ d / (w × response) (riding per order vs response) | 0.67 (1.33 km) | 0.07 (0.5 × 3 km / 20) | 0.53 (1.6 × 3 / 9) | 0.05 | 0.13 |
| f_e / P_i | 0.05 | 0.67 | 0.67 | 1.33 | 0.33 |
| F_j / P_i (per window) | 0.20 (2 h) | 0.40 (4 h) | 0.40 | 0.80 | 0.20 |
| b^B / P_i | 0.030 | 0.011 | 0.011 | 0.022 | 0.006 |
| b^C / P_i | 0.020 | 0.003 | 0.003 | 0.006 | 0.001 |
| Full charge of one battery / P_i | 0.001 | 0.007 | 0.007 | | |

**Key conclusion: P_i / (w_i × response) falls from 50 to about 1.5.** In toy units rejecting an order costs 50 times one order's response cost, so the objective is effectively "count unserved orders first, then operating cost" (lexicographic). Under the USD calibration:

- Serving one order costs ≈ w × (u_a − r_i) + κ d ≈ 40 × 0.5 + 1.5 = $21.5, rejecting it $30: serving only pays off when the response can be kept **within 45 min** (P/w = 0.75 h, minus riding and lateness penalties). Prep waiting alone (a_i − r_i ≈ 17.5 min) consumes $11.7, leaving only about 27 min of budget for pickup and drop-off.
- The USD objective is therefore a genuine "operating cost" objective: at 1.5× demand the ILP will **actively reject orders** rather than make riders detour or be late; part of the gap between the baseline (serve on acceptance) and the ILP will show up as service rate rather than cost. To keep the "service rate first" semantics, enable `lexicographic` or the `zeta` constraint (E2 (33)), or use the P high (60) / w low (22) combination (ratio 5.5, still far below 50).
- The response reference r_i vs a_i (open in `DECISIONS.md`) matters more in USD: w based on r_i prices uncontrollable prep time at $40/h, pushing towards rejection.
- Riding vs response: under option A riding cost is almost negligible relative to response (0.07), so the model is insensitive to route length; option B (κ = 1.6, w = 18) restores the toy magnitude (0.53). Both should be run as sensitivity comparisons in E2–E4.
- Transfers: f_e / P rises from 0.05 to 0.67 — one shuttle run is worth about 2/3 of an order, so it is only worth dispatching when it saves ≥ 1 order or ≥ 30 min of cumulative response; transfers that were almost free in the toy are strongly suppressed in USD.
- Facilities: F_j / P is of similar magnitude (0.2 → 0.4), b^B and b^C are relatively cheaper (×0.4, ×0.15): in USD the ILP is more willing to place spare batteries/charging slots and open fewer stations.
- Electricity remains negligible ($0.018 per level); merging battery cycle wear into π_eff ≈ 1.15 $/kWh gives $0.064 per level, $0.77 per battery, still only 2.6% of P.

---

## 10. Caveats

1. There are no public US quotes for cabinets, electrical connection or site rent; the F_j range (4–29 $/station/4 h) was cross-checked in magnitude against PopWheels subscription revenue, but confidence is low.
2. The customer part of w_i comes from the implied value of priority-delivery fees (stated preference + a minority of urgent customers); the average customer's time value may be lower; option A's w_i includes the rider wage and prices prep waiting as rider time (see §2 option B).
3. The v_i compensation policies are step functions (compensation only after ≥ 10–15 min); the model approximates them with a linear slope.
4. The churn term in P_i ($10) is an assumption: churn probability 20% × annual platform gross profit $50; no platform publishes CLV/CAC data.
5. BLS wages are 2023-05 metro means, projected about +8% to 2025–26; the 2025-05 OEWS metro table could not be fetched.
6. Battery holding cost is allocated by calendar life; allocating by cycles would price cost per swap/charge (π_eff variant), which differs from the form of (28).
7. All prices are nominal 2025–2026 USD; the DCWP minimum pay is CPI-adjusted every April 1.
8. Swap-service batteries are 1 kWh class (PopWheels about 1.25 kWh per battery), whereas `DECISIONS.md` defaults to 600 Wh (L = 12, ε = 50 Wh); b^B and b̂ in the JSON are for 600 Wh, with a 1 kWh variant given.
