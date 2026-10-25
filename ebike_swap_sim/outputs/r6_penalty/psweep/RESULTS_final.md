# Round 6, stage psweep: how the gap, served shares and lateness depend on the unserved-order penalty P

Date: 2026-10-18. Question: how do the gap, the served shares and the lateness depend on P in {20, 30, 40, 60, 80}
USD per order at v = 15 USD/h (w = 18 USD/h unchanged) on usd4h x1 and stress4h (10 seeds each)? Where does the ILP
start or stop dropping orders, is the gap monotone in P, and what are the paired differences to P = 60 (new base)?

Every number below was recomputed from `records.jsonl` (no solves) by `figs/make_psweep_figs.py`
(`python3 make_psweep_figs.py --tables` prints every table of this report). The auto-generated `RESULTS.md` was
checked against the records (section 1, A3). Round-5 reference: `r5_x1_headline/results.csv` (usd4h x1),
`r5_x5_stress/records_core.jsonl` and `r5_x7_rl/records.jsonl` (stress4h).

Conventions. Relaxed end targets; end-adjusted totals; best rule = per-instance minimum over r2, M2, M2+M3;
gap = 100 (best rule - ILP) / best rule per instance, then averaged; means with exact Student-t 95 % half-widths
over seeds (`mean ± hw`, n = 10 unless stated); all differences paired per seed. "New prices" = v 15 at the stated
P (base P 60); "old prices" = P 30, v 36 (round 5).

**Best-known ILP (used for the headline numbers).** All five pricings of a seed share one instance and one model
(same arcs, binaries and rows, checked), and only the price of an unserved order changes. So every ILP schedule
of a seed is feasible at every P, and its cost at P is `total(P') + (P - P') x unserved orders(P')`, exactly. The
same holds for the end-adjusted total, because the end adjustment does not depend on order prices (checked). The
best-known ILP at P is the cheapest of the five repriced schedules. It differs from the recorded incumbent in 7 of
100 cells, all of them time-limited (section 1, A1 and A2). The best lower bound at P is the largest Gurobi bound
at any P' <= P, since the optimum is non-decreasing in P. Recorded values are shown next to best-known ones.

---

## 1. Problems and anomalies

**A1. A laptop sleep cut two ILP solves short. One of them was recorded as a "solved" cell with gap 0 %.**
- The macOS power log (`pmset -g log`) shows a clamshell sleep from 13:13:09 to 13:42:42, with only short dark wakes.
  Gurobi counts wall-clock time, and the process timer (`wall_s`) does not.
- **usd4h P 80 seed 0.** `runtime_s` 459 vs `wall_s` 44, status TIME_LIMIT, bound 34.30, MIP gap 94.3 %.
  - The incumbent is the MIP start (the r2 rule schedule, 599.14 USD), so the recorded cell gap is 0.00 %.
  - The same seed's ILP serves all 36 orders at P 20-60 for 532.60 USD. That schedule costs the same at P 80 and is
    optimal there, because the optimum cannot fall as P rises. The corrected cell gap is 10.98 %.
  - Effect: usd4h P 80 mean gap 29.56 ± 8.72 (recorded) → **30.66 ± 6.73** (best-known).
- **stress4h P 40 seed 9.** `runtime_s` 1093 vs `wall_s` 167, TIME_LIMIT at 0.27 %. The P 30 schedule, repriced, is
  1.51 USD cheaper (cell gap 37.13 → 37.25 %).
- The resume logic did not flag either row: the time limit used equals the one requested (300 s), and
  `budget_shortened` is False.
- **Other stages hit by the same sleep (outside this stage, flagged only):**
  - vsweep usd4h P 60 / v 36 seeds 5 and 6: runtime 949 and 460 s vs wall 22 and 44 s.
  - fleet r5_stress4h seed 2: two `ILP_tl600` rows, emitted 13:28:58 (runtime 991 s) and 13:42:46, both TIME_LIMIT.
- Suggested guard: treat any ILP row with `runtime_s > wall_s + 10` as not done, and run lanes under `caffeinate -i`.

**A2. On stress4h, solves get harder as P rises; at P 80 most are time-limited and some incumbents are far from
optimal.**
- OPTIMAL at the 300 s limit: 10, 7, 5, 4 and 2 of 10 at P 20, 30, 40, 60 and 80.
- Max MIP gap 1.12 % up to P 60, but 11.63 % at P 80 (seed 3; seeds 2, 5, 6, 7 at 3.0-4.7 %).
- At P 80, repricing the P 60 schedule beats the recorded incumbent on 4 seeds:

  | seed | recorded (USD) | best-known (USD) | served share, recorded → best-known |
  |---|---|---|---|
  | 2 | 1118.94 | 1093.76 | 0.917 → 0.917 |
  | 3 | 1114.56 | 997.11 | 0.938 → 0.958 |
  | 6 | 1178.27 | 1164.83 | 0.917 → 0.896 |
  | 7 | 933.56 | 911.58 | 0.979 → 0.979 |

- Seed 3's recorded incumbent drops 3 orders at P 80 against 2 at P 60. An exact optimum cannot drop more orders at a
  higher P.
- The P 80 gap is therefore conservative: 43.71 ± 2.65 recorded, **44.61 ± 3.15** best-known, and at most
  45.44 ± 3.19 (gap against the best lower bound).
- All 100 incumbents pass `check_ok`, and the ILP objective equals `evaluate.cost` on all of them.

**A3. The auto-generated `RESULTS.md` reproduces the recorded numbers exactly, but four points mislead.**
- Its key table includes the cell cut short in A1 (usd4h P 80: 29.56 % and served share 0.992).
- Its paired usd4h P 80 row leaves out seed 0 (n = 9) because of the MIP-start rule, not because of the sleep. The
  same rule keeps stress4h P 40 seed 9, which started from a rule schedule.
- Its `ilp_mip_gap` column averages fractions: 0.03 means 2.9 %, and usd4h P 80's 0.09 comes from the single 94 % cell.
- Two columns are not what their names suggest:
  - `ilp_max_lateness_min` is the mean of the per-seed maxima, not the maximum.
  - `best_unserved` and `ilp_unserved` are in USD, not order counts.

**A4. The rule set is effectively min(r2, M2), and the rules do not react to P.**
- M2+M3 equals M2 on every cell: there are no services, so the M3 transfer value never acts.
- The rule schedules are identical across P (checked on all 60 rule × seed groups). Only the price of their unserved
  orders changes.
- So best-rule service and lateness move with P only when the best rule switches between r2 and M2. r2 is chosen
  more often at high P: 7/10 → 9/10 on usd4h and 2/10 → 6/10 on stress4h.

**A5. Five instances contain one order that cannot be served at all** (`n_unservable` = 1): usd4h seeds 5 and 6,
and stress4h seeds 1, 6 and 8. On those seeds the best possible served share is 35/36 or 47/48. "Dropping a
servable order" below excludes these orders.

**A6. Cross-stage check.** The rl stage re-solved the same stress4h P 60 instances under the same 300 s limit and
found slightly better incumbents on seed 5 (958.86 vs 959.10 USD) and seed 9 (898.48 OPTIMAL vs 899.82 TIME_LIMIT).
The difference is at most 1.34 USD, below 0.1 gap points. It is not used here, so that this report rests on the
psweep records alone.

**A7. The round-5 stress4h reference mixes two sources.**
- Seeds 0-4 come from X5 core: relaxed ILP, 300 s, all OPTIMAL.
- Seeds 5-9 come from X7: relaxed ILP, 120 s, all TIME_LIMIT; R5_DIGEST gives the X7 gap range as 0.13-1.64 %.
- X7 did not record lateness counts, so round-5 lateness comparisons on stress4h use seeds 0-4 only (n = 5).
- Rule rows match exactly between X5 and X7 on seeds 0-4.

**A8. Carried over from round 5, report-only.** 35 of 300 rule rows are flagged not clean (constraint family (9);
`ok_modulo_report_only` is true on all 300). 25 rule rows have one stranded bike.

## 2. Coverage

- **Records.** 400 records with 400 unique keys: 2 families × 5 values of P × 10 seeds × (r2, M2, M2+M3, relaxed ILP).
  - No ERROR or SKIPPED_BUDGET rows; no cell is missing.
  - The 40 usd4h P 60 rows were copied from the headline stage: same instance, same protocol, demand hash equal.
- **Run time.** 12,830 s (214 min) against a 360 min budget.
- **Instances.** Identical to round 5: the demand MD5 matches for all 20 family × seed instances.
- **ILP protocol.** Aggregated model, Threads 3, Seed 0, time limit 300 s (the requested limit was used everywhere).
  The MIP start was accepted on all 100 solves.
  - Starts came from the cheapest rule schedule, except the copied usd4h P 60 cells, which started from the written-ILP
    optimum.
  - Library price check passed on every cell.
- **Checks that pass.** Unserved cost = P × unserved orders; end-adjusted total = total + end adjustment; ILP
  objective = `evaluate.cost`.

ILP solve status:

| family | P | OPTIMAL | TIME_LIMIT | max MIP gap % | median runtime s | cells improved by repricing |
|---|---|---|---|---|---|---|
| usd4h | 20 | 10 | 0 | 0.00 | 34 | 0 |
| usd4h | 30 | 10 | 0 | 0.01 | 35 | 0 |
| usd4h | 40 | 10 | 0 | 0.00 | 28 | 0 |
| usd4h | 60 | 10 | 0 | 0.01 | 30 | 0 |
| usd4h | 80 | 9 | 1 | 94.28 (sleep, A1) | 32 | 1 |
| stress4h | 20 | 10 | 0 | 0.01 | 86 | 0 |
| stress4h | 30 | 7 | 3 | 0.58 | 140 | 1 (0.24 USD) |
| stress4h | 40 | 5 | 5 | 0.75 | 258 | 1 (sleep, A1) |
| stress4h | 60 | 4 | 6 | 1.12 | 300 | 0 |
| stress4h | 80 | 2 | 8 | 11.63 | 300 | 4 |

## 3. Results

### 3.1 Gap vs P

Table 1. Gap (%), best-rule and ILP cost (USD per 4-h window), n = 10 per row.

| family | P | gap, recorded | **gap, best-known ILP** | gap vs best bound (upper limit) | best rule USD | ILP USD (best-known) | best rule = r2 / M2 |
|---|---|---|---|---|---|---|---|
| usd4h | 20 | 22.29 ± 6.41 | **22.29 ± 6.41** | 22.48 ± 6.39 | 728.3 ± 71.2 | 558.0 ± 9.8 | 7 / 3 |
| usd4h | 30 | 22.48 ± 5.25 | **22.48 ± 5.25** | 22.67 ± 5.23 | 757.3 ± 71.5 | 580.6 ± 18.4 | 7 / 3 |
| usd4h | 40 | 23.79 ± 5.01 | **23.79 ± 5.01** | 23.98 ± 4.99 | 784.5 ± 74.6 | 591.6 ± 24.4 | 8 / 2 |
| usd4h | 60 | 27.34 ± 5.65 | **27.34 ± 5.65** | 27.52 ± 5.63 | 838.5 ± 85.2 | 601.4 ± 28.7 | 8 / 2 |
| usd4h | 80 | 29.56 ± 8.72 | **30.66 ± 6.73** | 30.83 ± 6.71 | 891.8 ± 99.6 | 607.5 ± 32.0 | 9 / 1 |
| stress4h | 20 | 33.21 ± 2.48 | **33.21 ± 2.48** | 33.37 ± 2.47 | 1141.8 ± 54.9 | 760.4 ± 14.4 | 2 / 8 |
| stress4h | 30 | 33.64 ± 2.22 | **33.64 ± 2.22** | 33.87 ± 2.20 | 1263.8 ± 74.3 | 836.2 ± 30.5 | 2 / 8 |
| stress4h | 40 | 35.14 ± 2.17 | **35.15 ± 2.17** | 35.45 ± 2.24 | 1382.1 ± 94.8 | 893.5 ± 46.4 | 4 / 6 |
| stress4h | 60 | 39.70 ± 2.84 | **39.70 ± 2.84** | 40.03 ± 2.86 | 1614.1 ± 138.9 | 969.7 ± 75.5 | 4 / 6 |
| stress4h | 80 | 43.71 ± 2.65 | **44.61 ± 3.15** | 45.44 ± 3.19 | 1844.5 ± 185.7 | 1017.4 ± 99.5 | 6 / 4 |

The gap is positive on every one of the 100 cells once the A1 cell is corrected (smallest cell 9.85 %; recorded
smallest 0.00 %, the A1 cell). The upper-limit column assumes
an end adjustment of at least 0 (observed range 0.66-2.20 USD), so even fully optimal cells sit about 0.2 points
above the gap.

### 3.2 Paired differences to P = 60

Table 2. Each P minus P 60, per seed; n = 10 pairs. "Non-OPTIMAL pairs" counts pairs with at least one
time-limited side. ILP values are best-known.

| family | P | non-OPTIMAL pairs | gap pts (recorded) | **gap pts (best-known)** | seeds higher / lower than P 60 | ILP served share | best rule served share | ILP unserved orders | ILP late orders | ILP mean lateness min | ILP USD | best rule USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 20 | 0 | -5.05 ± 5.03 | **-5.05 ± 5.03** | 2 / 7 | -0.089 ± 0.031 | -0.006 ± 0.013 | +3.2 ± 1.1 | -3.1 ± 1.7 | -0.93 ± 0.74 | -43.4 ± 21.6 | -110.2 ± 46.5 |
| usd4h | 30 | 0 | -4.86 ± 3.36 | **-4.86 ± 3.36** | 1 / 7 | -0.031 ± 0.024 | -0.006 ± 0.013 | +1.1 ± 0.9 | -2.0 ± 1.8 | -0.75 ± 0.76 | -20.8 ± 12.9 | -81.2 ± 33.8 |
| usd4h | 40 | 0 | -3.55 ± 1.97 | **-3.55 ± 1.97** | 1 / 8 | -0.011 ± 0.014 | 0.000 ± 0.000 | +0.4 ± 0.5 | -0.9 ± 1.1 | -0.38 ± 0.49 | -9.8 ± 7.5 | -54.0 ± 22.4 |
| usd4h | 80 | 1 | +2.22 ± 3.61 | **+3.31 ± 1.66** | 8 / 0 | +0.003 ± 0.006 | +0.003 ± 0.006 | -0.1 ± 0.2 | +0.7 ± 1.6 | +0.15 ± 0.34 | +6.1 ± 6.9 | +53.2 ± 22.4 |
| stress4h | 20 | 6 | -6.49 ± 3.08 | **-6.49 ± 3.08** | 1 / 9 | -0.146 ± 0.017 | -0.013 ± 0.020 | +7.0 ± 0.8 | -10.9 ± 1.9 | -3.47 ± 0.89 | -209.3 ± 64.1 | -472.3 ± 100.8 |
| stress4h | 30 | 6 | -6.06 ± 2.37 | **-6.06 ± 2.37** | 1 / 9 | -0.069 ± 0.014 | -0.013 ± 0.020 | +3.3 ± 0.7 | -8.7 ± 2.1 | -3.08 ± 0.83 | -133.5 ± 46.9 | -350.3 ± 75.5 |
| stress4h | 40 | 7 | -4.56 ± 1.50 | **-4.55 ± 1.51** | 0 / 10 | -0.050 ± 0.013 | 0.000 ± 0.000 | +2.4 ± 0.6 | -6.9 ± 2.3 | -2.52 ± 0.71 | -76.1 ± 30.6 | -232.0 ± 50.6 |
| stress4h | 80 | 8 | +4.01 ± 1.50 | **+4.91 ± 0.71** | 10 / 0 | +0.015 ± 0.014 | +0.004 ± 0.006 | -0.7 ± 0.7 | +1.9 ± 2.8 | +1.27 ± 1.21 | +47.7 ± 25.2 | +230.4 ± 50.2 |

When P moves away from 60, the best rule's cost changes 2.3-8.7 times as much as the ILP's (the ratio of the two
USD columns). The best rule pays the penalty on its 11-12 (stress4h) or 2.6-2.9 (usd4h) dropped orders, while the
ILP partly avoids it by serving more.

### 3.3 Is the gap monotone in P?

Table 3. Change between consecutive values of P (paired, points). "Seeds up / down" counts changes beyond
±0.05 points.

| family | step | change, recorded | **change, best-known** | seeds up / down (best-known) |
|---|---|---|---|---|
| usd4h | 20 → 30 | +0.18 ± 1.83 | **+0.18 ± 1.83** | 5 / 4 |
| usd4h | 30 → 40 | +1.31 ± 1.45 | **+1.31 ± 1.45** | 7 / 2 |
| usd4h | 40 → 60 | +3.55 ± 1.97 | **+3.55 ± 1.97** | 8 / 1 |
| usd4h | 60 → 80 | +2.22 ± 3.61 | **+3.31 ± 1.66** | 8 / 0 |
| stress4h | 20 → 30 | +0.43 ± 0.78 | **+0.43 ± 0.78** | 8 / 2 |
| stress4h | 30 → 40 | +1.50 ± 0.89 | **+1.51 ± 0.89** | 8 / 1 |
| stress4h | 40 → 60 | +4.56 ± 1.50 | **+4.55 ± 1.51** | 10 / 0 |
| stress4h | 60 → 80 | +4.01 ± 1.50 | **+4.91 ± 0.71** | 10 / 0 |

- **On average, yes.** The mean gap rises at every step in both families.
  - The 20 → 30 step is flat; its CI covers 0 in both families.
  - From P 40 upwards every step is significantly positive (best-known values).
  - usd4h 30 → 40 is not significant.
- **Per seed, no.** Using best-known values, the gap falls at least once with P on 4 of 10 usd4h seeds (5, 6, 7, 8)
  and 2 of 10 stress4h seeds (5, 8). The recorded values add usd4h seed 0 (the A1 cell) and stress4h seed 3 (A2).
  - The falls happen at low P (20 → 30 or 30 → 40).
  - usd4h seed 7 falls all the way: 23.4, 20.3, 18.7, 18.5, 18.5 %. Its best rule drops no orders, while the ILP drops
    4 at P 20.
  - The four usd4h seeds with a fall (5-8) are exactly the seeds where the best rule drops fewer orders than the ILP at
    P 20.

### 3.4 Served shares: where the ILP starts and stops dropping orders

Table 4. Service per 4-h window (usd4h has 36 orders, stress4h 48). ILP values are best-known; the recorded mean
served share is the same to 3 decimals in every row.

| family | P | best rule served | ILP served | ILP − best rule (paired) | seeds ILP > / = / < rule | best rule unserved | ILP unserved | ILP: servable orders dropped | seeds where the ILP drops a servable order | seeds where the ILP serves every order |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 20 | 0.919 ± 0.037 | 0.900 ± 0.033 | **-0.019 ± 0.041** | 3 / 3 / 4 | 2.9 ± 1.3 | 3.6 ± 1.2 | 3.4 ± 1.1 | 9/10 | 1/10 |
| usd4h | 30 | 0.919 ± 0.037 | 0.958 ± 0.025 | +0.039 ± 0.044 | 7 / 1 / 2 | 2.9 ± 1.3 | 1.5 ± 0.9 | 1.3 ± 0.9 | 7/10 | 3/10 |
| usd4h | 40 | 0.925 ± 0.031 | 0.978 ± 0.016 | +0.053 ± 0.036 | 7 / 2 / 1 | 2.7 ± 1.1 | 0.8 ± 0.6 | 0.6 ± 0.5 | 5/10 | 4/10 |
| usd4h | 60 | 0.925 ± 0.031 | 0.989 ± 0.010 | +0.064 ± 0.028 | 8 / 2 / 0 | 2.7 ± 1.1 | 0.4 ± 0.4 | 0.2 ± 0.3 | 2/10 | 6/10 |
| usd4h | 80 | 0.928 ± 0.031 | 0.992 ± 0.010 | +0.064 ± 0.031 | 8 / 2 / 0 | 2.6 ± 1.1 | 0.3 ± 0.3 | 0.1 ± 0.2 | 1/10 | 7/10 |
| stress4h | 20 | 0.746 ± 0.055 | 0.798 ± 0.038 | +0.052 ± 0.032 | 8 / 1 / 1 | 12.2 ± 2.6 | 9.7 ± 1.8 | 9.4 ± 1.6 | 10/10 | 0/10 |
| stress4h | 30 | 0.746 ± 0.055 | 0.875 ± 0.037 | +0.129 ± 0.031 | 10 / 0 / 0 | 12.2 ± 2.6 | 6.0 ± 1.8 | 5.7 ± 1.5 | 10/10 | 0/10 |
| stress4h | 40 | 0.758 ± 0.053 | 0.894 ± 0.033 | +0.135 ± 0.042 | 10 / 0 / 0 | 11.6 ± 2.5 | 5.1 ± 1.6 | 4.8 ± 1.3 | 10/10 | 0/10 |
| stress4h | 60 | 0.758 ± 0.053 | 0.944 ± 0.029 | +0.185 ± 0.038 | 10 / 0 / 0 | 11.6 ± 2.5 | 2.7 ± 1.4 | 2.4 ± 1.1 | 9/10 | 1/10 |
| stress4h | 80 | 0.762 ± 0.052 | 0.958 ± 0.026 | +0.196 ± 0.032 | 10 / 0 / 0 | 11.4 ± 2.5 | 2.0 ± 1.3 | 1.7 ± 1.1 | 8/10 | 2/10 |

Lowest P in the grid from which the ILP drops no servable order at that P or any higher one (per seed, best-known):

| family | ≤ 20 | 30 | 40 | 60 | 80 | still dropping at 80 |
|---|---|---|---|---|---|---|
| usd4h | 1 (s0) | 2 (s4, s9) | 2 (s1, s6) | 3 (s5, s7, s8) | 1 (s3) | 1 (s2: one order) |
| stress4h | 0 | 0 | 0 | 1 (s0) | 1 (s9) | 8 (1-4 orders each) |

- **Below P 30, cheap dropping returns on usd4h.** At P 20 the ILP serves fewer orders than the best rule on 4 of 10
  usd4h seeds. The mean served share is lower too (−0.019 ± 0.041; the CI covers 0).
- **Above P 30 the ILP serves more.** From P 30 on usd4h, and at every P on stress4h, the ILP serves more orders
  than the best rule. On stress4h it is ahead on all 10 seeds from P 30, by 0.13-0.20.
- **On usd4h the ILP mostly stops dropping between P 40 and P 60.** At P 60 it drops a servable order on 2 of 10
  seeds, at P 80 on 1.
- **On stress4h no threshold appears within the grid.** The ILP still drops 2.4 ± 1.1 servable orders per window at
  P 60 and 1.7 ± 1.1 at P 80. Most of these cells are time-limited (A2).
- **The best rule barely moves.** Its served share stays at 0.919-0.928 (usd4h) and 0.746-0.762 (stress4h). It
  changes only when the best rule switches (A4).

### 3.5 Lateness

Table 5. Late orders per 4-h window (lateness > 0), plus the mean lateness over served orders and the per-seed
maximum (minutes). ILP values are best-known.

| family | P | best rule late orders | ILP late orders | best rule > 30 min | ILP > 30 min | > 60 min, total over 10 seeds (rule / ILP) | best rule mean lateness | ILP mean lateness | ILP per-seed max (mean) | worst seed max (rule / ILP) |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 20 | 13.7 ± 4.8 | **0.0** | 1.2 ± 1.7 | 0.0 | 0 / 0 | 6.36 ± 3.23 | 0.00 | 0.0 | 40 / 0 |
| usd4h | 30 | 13.7 ± 4.8 | 1.1 ± 0.6 | 1.2 ± 1.7 | 0.0 | 0 / 0 | 6.36 ± 3.23 | 0.17 ± 0.10 | 4.5 ± 2.0 | 40 / 10 |
| usd4h | 40 | 13.9 ± 4.7 | 2.2 ± 1.0 | 1.2 ± 1.7 | 0.0 | 0 / 0 | 6.47 ± 3.17 | 0.54 ± 0.32 | 11.5 ± 6.3 | 40 / 30 |
| usd4h | 60 | 13.9 ± 4.7 | 3.1 ± 1.7 | 1.2 ± 1.7 | 0.2 ± 0.5 | 0 / 0 | 6.47 ± 3.17 | 0.93 ± 0.74 | 13.5 ± 7.5 | 40 / 35 |
| usd4h | 80 | 14.1 ± 4.8 | 3.8 ± 2.1 | 1.2 ± 1.7 | 0.2 ± 0.5 | 0 / 0 | 6.74 ± 3.26 | 1.08 ± 0.74 | 14.5 ± 7.2 | 40 / 35 |
| stress4h | 20 | 21.2 ± 1.8 | **0.0** | 6.5 ± 2.2 | 0.0 | 2 / 0 | 14.41 ± 2.82 | 0.00 | 0.0 | 65 / 0 |
| stress4h | 30 | 21.2 ± 1.8 | 2.2 ± 0.8 | 6.5 ± 2.2 | 0.0 | 2 / 0 | 14.41 ± 2.82 | 0.39 ± 0.16 | 9.0 ± 2.8 | 65 / 15 |
| stress4h | 40 | 21.8 ± 2.0 | 4.0 ± 1.4 | 6.7 ± 2.4 | 0.0 | 1 / 0 | 14.63 ± 2.95 | 0.95 ± 0.47 | 16.0 ± 5.8 | 65 / 30 |
| stress4h | 60 | 21.8 ± 2.0 | 10.9 ± 1.9 | 6.7 ± 2.4 | 1.1 ± 0.9 | 1 / 0 | 14.63 ± 2.95 | 3.47 ± 0.89 | 37.5 ± 9.0 | 65 / 60 |
| stress4h | 80 | 22.7 ± 2.0 | 12.8 ± 1.9 | 6.9 ± 2.4 | 2.2 ± 1.6 | 1 / 0 | 15.08 ± 3.06 | 4.74 ± 1.72 | 43.5 ± 10.1 | 65 / 60 |

- **At P 20 the ILP never delivers late** (0 late orders on all 20 instances; this holds for the recorded rows too).
  It drops orders instead.
- **As P rises, the ILP trades drops for late deliveries.** Late orders go 0 → 3.8 on usd4h and 0 → 12.8 on stress4h,
  and the mean lateness reaches 1.1 and 4.7 min.
- **The ILP never exceeds 60 min late in any cell** (worst case exactly 60 min, stress4h P 60 and 80). The best rule
  reaches 65 min, with 1-2 orders over 60 min across the 10 stress4h seeds.
- The recorded P 80 stress4h incumbents show 13.4 late orders and 5.35 min mean lateness; the best-known schedules
  show 12.8 and 4.74.

### 3.6 What the saving is made of

Table 6. Best rule minus ILP, USD per window (mean over seeds), with each component's share of the sum of the three
order-related terms. Travel, energy, set-up and end adjustment are omitted: at most 5.5 USD on any instance, 0.85
on average.

| family | pricing | unserved orders | response time | lateness | total saving, end-adjusted (± CI) |
|---|---|---|---|---|---|
| usd4h | old prices (P 30, v 36), round 5 | 36.0 (15 %) | 87.6 (35 %) | 123.9 (50 %) | n/a in this table |
| usd4h | P 20 | -14.0 (-8 %) | 129.0 (77 %) | 52.8 (31 %) | 170.3 ± 63.8 |
| usd4h | P 30 | 42.0 (24 %) | 82.2 (47 %) | 51.2 (29 %) | 176.7 ± 55.6 |
| usd4h | P 40 | 76.0 (40 %) | 66.9 (35 %) | 49.0 (26 %) | 192.9 ± 54.8 |
| usd4h | **P 60** | 138.0 (58 %) | 52.8 (22 %) | 45.5 (19 %) | 237.1 ± 64.3 |
| usd4h | P 80 | 184.0 (65 %) | 53.0 (19 %) | 46.6 (16 %) | 284.2 ± 79.9 |
| stress4h | old prices (P 30, v 36), round 5 | 156.0 (26 %) | 141.3 (24 %) | 302.4 (50 %) | n/a in this table |
| stress4h | P 20 | 50.0 (13 %) | 202.1 (53 %) | 126.6 (33 %) | 381.4 ± 45.1 |
| stress4h | P 30 | 186.0 (44 %) | 118.5 (28 %) | 122.6 (29 %) | 427.6 ± 49.6 |
| stress4h | P 40 | 260.0 (53 %) | 106.7 (22 %) | 121.4 (25 %) | 488.6 ± 56.8 |
| stress4h | **P 60** | 534.0 (83 %) | 18.8 (3 %) | 92.4 (14 %) | 644.4 ± 85.1 |
| stress4h | P 80 | 752.0 (91 %) | -5.8 (-1 %) | 81.9 (10 %) | 827.1 ± 115.6 |

## 4. Comparison with round 5 (old prices P 30, v 36) on the same instances

Same 20 instances (demand MD5 equal), same rules, best rule taken over the relaxed copy. For usd4h x1 that agrees
with the round-5 headline definition (both copies): 28.28 % either way.

The R6 vsweep "bridge" cell, which re-runs (P 30, v 36), reproduces the round-5 usd4h rule totals exactly and the
ILP end-adjusted totals within 0.09 USD (alternative optima). The pipeline therefore reproduces round 5.

Table 7. Round 5, old prices.

| family | n | ILP status | gap | best rule served | ILP served | best rule unserved | ILP unserved | best rule late | ILP late | ILP mean lateness min |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | 10 | 10 OPTIMAL (X1) | 28.28 ± 7.36 | 0.919 ± 0.037 | 0.953 ± 0.027 | 2.9 ± 1.3 | 1.7 ± 1.0 | 13.5 ± 5.0 | 0.6 ± 0.5 | 0.09 ± 0.07 |
| stress4h | 10 | 5 OPTIMAL (X5, 300 s) + 5 TIME_LIMIT (X7, 120 s) | 41.38 ± 2.71 | 0.746 ± 0.055 | 0.854 ± 0.038 | 12.2 ± 2.6 | 7.0 ± 1.8 | 20.8 ± 2.4 (n = 5) | 0.4 ± 0.7 (n = 5) | 0.05 ± 0.08 (n = 5) |

Table 8. New pricing minus old prices, paired per seed (ILP best-known; n = 10 unless stated).

| family | new pricing | gap pts | ILP served | best rule served | ILP unserved orders | ILP late orders | ILP mean lateness min |
|---|---|---|---|---|---|---|---|
| usd4h | P 20, v 15 | -5.98 ± 1.40 | -0.053 ± 0.022 | 0.000 | +1.9 ± 0.8 | -0.6 ± 0.5 | -0.09 ± 0.07 |
| usd4h | P 30, v 15 (only v changes) | **-5.80 ± 2.23** | +0.006 ± 0.008 | 0.000 | -0.2 ± 0.3 | +0.5 ± 0.4 | +0.09 ± 0.07 |
| usd4h | P 40, v 15 | -4.49 ± 3.31 | +0.025 ± 0.015 | +0.006 ± 0.013 | -0.9 ± 0.5 | +1.6 ± 1.0 | +0.46 ± 0.34 |
| usd4h | **P 60, v 15 (new base)** | **-0.93 ± 4.86** | **+0.036 ± 0.025** | +0.006 ± 0.013 | -1.3 ± 0.9 | +2.5 ± 1.9 | +0.84 ± 0.77 |
| usd4h | P 80, v 15 | +2.38 ± 6.23 | +0.039 ± 0.025 | +0.008 ± 0.013 | -1.4 ± 0.9 | +3.2 ± 2.2 | +0.99 ± 0.77 |
| stress4h | P 20, v 15 | -8.18 ± 0.64 | -0.056 ± 0.010 | 0.000 | +2.7 ± 0.5 | -0.4 ± 0.7 (n = 5) | -0.05 ± 0.08 (n = 5) |
| stress4h | P 30, v 15 (only v changes) | **-7.75 ± 0.58** | +0.021 ± 0.010 | 0.000 | -1.0 ± 0.5 | +0.8 ± 0.6 (n = 5) | +0.16 ± 0.16 (n = 5) |
| stress4h | P 40, v 15 | -6.23 ± 1.34 | +0.040 ± 0.016 | +0.013 ± 0.020 | -1.9 ± 0.8 | +2.4 ± 1.1 (n = 5) | +0.58 ± 0.27 (n = 5) |
| stress4h | **P 60, v 15 (new base)** | **-1.68 ± 2.76** | **+0.090 ± 0.016** | +0.013 ± 0.020 | -4.3 ± 0.8 | +10.4 ± 3.4 (n = 5) | +3.26 ± 1.29 (n = 5) |
| stress4h | P 80, v 15 | +3.23 ± 3.36 | +0.104 ± 0.020 | +0.017 ± 0.020 | -5.0 ± 1.0 | +11.8 ± 3.7 (n = 5) | +3.94 ± 2.50 (n = 5) |

On stress4h, part of the old-price ILP comes from 120 s time-limited solves (seeds 5-9). The old-price gap there is
therefore slightly conservative, which makes the new-minus-old differences slightly too negative.

## 5. Interpretation

### What the records show

1. **The gap rises with P on average, so it is not a pricing artefact in either direction.**
   - Between P 20 and P 80 it rises from 22.3 to 30.7 % (usd4h) and from 33.2 to 44.6 % (stress4h).
   - At the new base P 60 it is 27.34 ± 5.65 % and 39.70 ± 2.84 %.
   - It is positive on every instance and every P (best-known), including P 20, where the ILP is allowed to drop
     orders cheaply.
2. **Against P 60, lower P cuts the gap and higher P raises it.**
   - P 20, 30 and 40 cut it by 5.1, 4.9 and 3.6 points (usd4h) and by 6.5, 6.1 and 4.6 points (stress4h). Every one of
     these differences is significant; usd4h P 20 only just (CI −10.1 to −0.0).
   - P 80 raises it by 3.3 ± 1.7 (usd4h) and 4.9 ± 0.7 points (stress4h).
3. **Monotone in the mean, not per seed.**
   - The P 20 → 30 step is flat in both families.
   - Per seed, the gap falls with P on 4/10 usd4h and 2/10 stress4h seeds, all at low P.
4. **The ILP's dropping depends on P; the best rule's does not.**
   - At P 20 the ILP drops 3.6 (usd4h) and 9.7 (stress4h) orders per window and never delivers late. On usd4h it
     serves fewer orders than the best rule on 4/10 seeds.
   - By P 60 it serves 0.989 and 0.944 of orders.
   - On usd4h it stops dropping servable orders on most seeds between P 40 and P 60.
   - On stress4h it is still dropping 1.7-2.4 servable orders per window at P 60-80.
   - The best rule's service is fixed by its rule: 0.92-0.93 and 0.75-0.76.
5. **The ILP turns drops into short late deliveries.**
   - ILP late orders rise from 0 (P 20) to 3.1 / 10.9 (P 60) and 3.8 / 12.8 (P 80).
   - The ILP is never more than 60 min late; the best rule has 14-23 late orders per window and up to 65 min.
6. **New base vs old prices: the headline gap is about the same, but it now rests on different savings.**
   - P 60 / v 15 minus P 30 / v 36: −0.9 ± 4.9 points (usd4h) and −1.7 ± 2.8 (stress4h).
   - Changing only v (36 → 15 at P 30) costs 5.8 ± 2.2 and 7.8 ± 0.6 points.
   - Doubling P (30 → 60) gives back 4.9 and 6.1 points.
   - The composition shifts: unserved orders make up 58 % (usd4h) and 83 % (stress4h) of the saving at the new base,
     against 15 % and 26 % at old prices. Lateness drops from 50 % to 19 % and 14 %.

### What is suggested but not shown

- **Why the gap rises with P.** Locally, d(gap)/dP has the sign of U_B / B − U_I / I: the best rule's dropped orders
  per USD of cost against the ILP's.
  - The best rule drops 2.6-2.9 (usd4h) and 11.4-12.2 (stress4h) orders whatever P is, while the ILP's drops fall
    with P. So the gap rises wherever the rule drops relatively more.
  - The local sign at the start of each step matches the observed direction on 32 of 35 (usd4h) and 31 of 39
    (stress4h) non-flat steps.
  - This is a first-order identity checked at five grid points, not a proof for the whole step.
- **The stress4h threshold.** The ILP's remaining drops at P 80 may partly come from time-limited incumbents (8/10
  TIME_LIMIT). Whether the ILP would serve every servable order at some P ≤ 80 on stress4h needs longer solves.
- **How much to trust the headline at P 60.** On stress4h, 83 % of the P 60 saving prices orders the rule drops at
  60 USD each. The headline therefore rests directly on the calibrated P (see `notes/penalty_calibration.md`).
  - The sensitivity is about 0.25 gap points per USD of P around P 60 (stress4h), or 0.17 (usd4h).
  - A ± 20 USD error in P moves the stress4h gap by about ± 5 points.
- **Round-5 artefact "dropping orders was cheap"** (context items a and e). In this sweep the problem reappears only
  for P ≤ 20-30:
  - at P 20 the ILP serves fewer orders than the best rule on 4/10 usd4h seeds and delivers no order late;
  - at the new base the ILP serves more orders than the best rule on 18 of 20 instances and as many on the other 2.
  - This concerns the offline ILP vs the rules only. The RL, rolling-horizon and fleet artefacts belong to other
    stages.

## 6. Figures (`figs/`, PDF and 300-dpi PNG)

- `fig1_gap_vs_P` shows the gap vs P for each family.
  - Mean ± 95 % CI with thin per-seed lines (best-known ILP).
  - On stress4h, a dashed upper limit (gap against the best lower bound).
  - The round-5 old-price gap as an open diamond, drawn just right of P 30.
- `fig2_service_vs_P` shows served share (top row) and late orders per window (bottom row), for the ILP
  (best-known) and the best rule, against the servable maximum. Round-5 values are open diamonds; on stress4h the
  round-5 late orders cover seeds 0-4 only.
- `fig3_saving_components` shows best rule minus ILP (USD per window), stacked by unserved orders, response time and
  lateness, with the end-adjusted total ± 95 % CI.

Colours: blue = ILP and orange = best rule (palette slots 1-2); the cost components use a separate aqua / violet /
yellow trio. Adjacent pairs were checked for colour-blind separation with the palette validator.

## 7. Reproduction

```
cd "ebike_swap_sim/outputs/r6_penalty/psweep/figs"
python3 make_psweep_figs.py --tables   # prints every table above, writes the figures and two CSVs
```

Data files written by the script: `figs/psweep_final_per_instance.csv` (one row per family × P × seed: rules, best
rule, recorded and best-known ILP, bounds, gaps) and `figs/psweep_final_r5_reference.csv` (round-5 reference per
seed).
