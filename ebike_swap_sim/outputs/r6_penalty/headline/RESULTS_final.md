# R6 headline: does the coordination gap survive the new order prices? (final report)

**Question.** Round 6 reprices every order. The unserved penalty rises from P = 30 to P = 60 USD, the lateness price
falls from v = 36 to v = 15 USD/h from the promise, and the response price stays at w = 18 USD/h from release. This
report asks whether the coordination gap of round 5 survives this change. It covers the families usd4h (demand
x0.75, x1, x1.5) and nyc4h. Below, "new prices" means (P 60, v 15) and "old prices" means (P 30, v 36).

**Sources.** New prices: `outputs/r6_penalty/headline/records.jsonl` (290 records, last record per key). Old prices:
`outputs/r5_x1_headline/records.jsonl`, rows with `calib == "ebaas"` (320 records). Every number below was
recomputed from these raw records by `figs/r6_headline_tables.py`. That script writes `per_instance_final.csv` and
`summary_final.json`. The figures come from `figs/r6_headline_figs.py`. No solver was run for this report.

**Conventions.**
- The best rule is the per-instance minimum of the end-adjusted total over r2, M2 and M2+M3, on both target copies.
  M3 alone needs service stations, and no instance has any.
- ILP means the aggregated E2 ILP with relaxed end targets. Where the written-target ILP was also solved (usd4h x1),
  the cheaper of the two by raw objective is used. That was the relaxed solve on 40/40 instances in both rounds.
- Gap = 100 (best rule − ILP) / best rule, computed on end-adjusted totals for each instance and then averaged.
- "± h" is the half-width of the exact Student-t 95 % CI over seeds, t(0.975, n−1) s / √n.
- Every comparison is paired per seed: the per-seed difference is formed first, then its mean and CI.
- Costs are in USD per 4-h window.
- The nyc4h gaps are lower bounds, as in round 5, because the facility pruning `PRUNING_NYC` restricts only the ILP.

---

## 1. Problems and anomalies

1. **The percentage gap at usd4h x1.5 falls by 5.0 points, but the USD saving does not change.**
   - The gap is 38.42 % under new prices against 43.45 % under old prices. The paired difference is −5.03 ± 3.08
     points, lower on 9/10 seeds (paired t p = 0.005).
   - The saving in USD is unchanged: 805.74 against 796.06 USD, paired +9.69 ± 72.84 (p = 0.77).
   - The best rule costs +294.90 ± 67.22 USD more per window. Its unserved term rises by +507.00 because its 17.6
     dropped orders now cost 60 USD each. Its lateness term falls by −232.20.
   - The ILP costs +285.21 ± 31.37 USD more.
   - The fall is therefore a denominator effect. The percentage gap depends on the price level of orders that
     neither method can serve. Report the USD saving next to the percentage.
2. **3/10 relaxed ILPs at usd4h x1.5 hit the 300 s time limit.**
   - These are seeds 0, 5 and 8, with MIP gaps 1.07 %, 0.33 % and 0.91 %. Seed 2 reached OPTIMAL at 299.6 s.
   - In round 5 all 10 were OPTIMAL. The mean runtime was 53.9 s then and is 215.5 s now, so the new prices make
     x1.5 about 4 times slower.
   - Effect on the result: the gap computed with the ILP bound, an upper limit, is 38.63 ± 3.09 % against
     38.42 ± 3.07 %. The paired change against old prices is −4.81 ± 3.10 points with the bound, against −5.03.
     The conclusion does not change.
   - If the x1.5 gap goes into the paper, re-solve these 3 cells at 600 s.
3. **The ILP now accepts more lateness.** This is the intended effect of cheaper lateness, not an error.
   - Late orders per window under new and old prices: 3.1 against 0.6 (usd4h x1), 8.4 against 0.3 (x1.5) and 4.4
     against 0.8 (nyc4h).
   - The largest ILP lateness is 45 min under new prices. Under old prices it was at most 15 min, because the
     total lateness of any old window was at most 15 min.
   - The 45-min maximum is on a single row, usd4h x1.5 relaxed seed 8, which is a TIME_LIMIT incumbent (MIP gap
     0.91 %), not a proven optimum. Every OPTIMAL ILP row is at most 35 min late (usd4h x1 seed 8 on both target
     copies, nyc4h seed 8). n = 50 ILP rows: 47 OPTIMAL, 3 TIME_LIMIT.
   - No ILP order is more than 60 min late in either round (0 on 50/50 new-price ILP rows). At most 2 ILP orders
     per window are more than 30 min late.
   - Among the 240 rule rows (all POLICY), orders more than 60 min late occur only at usd4h x1.5 (n = 10 seeds per
     rule), on the same rows for relaxed and written targets: r2 on seed 8 (1 order, 65 min), and M2 and M2+M3 on
     seeds 5 (2 orders, 65 min), 6 (2 orders, 70 min) and 8 (1 order, 65 min). M2+M3 is identical to M2 (item 5).
     Under new prices the best rule is r2 on all three seeds, so it has exactly one such order over the 40
     instances (seed 8, 65 min; 0.1 per window at x1.5). Under old prices the best rule was M2 on seeds 5 and 8
     (3 orders, 0.3 per window; Table 3.5).
   - The rules' own lateness does not change (item 4).
4. **The best rule changes identity on 9/40 instances, but no rule schedule changes.**
   - On this stage the rule schedules are unchanged by the new prices. All 240 rule rows (r2, M2, M2+M3 × 2 target
     copies × 40 instances; usd4h n = 30, nyc4h n = 10; status POLICY in both rounds) are physically identical in
     both rounds. The maximum absolute difference is exactly 0 in served orders, late orders, swaps, bike-km, kWh,
     travel, electricity, end adjustment, mean response and mean lateness. Only the price terms change: the
     unserved cost is exactly 2 × and the lateness cost exactly 15/36 × the old value on every row.
   - This holds by construction on these instances, not as a general property of the rules. r2 and M2 (dispatch,
     charging and range rules) read no order prices. The only price-dependent rule component is the M3 stock-out
     value (mean P_i × orders per stock-out, `baseline.stockout_value`), and it is inert here because no instance
     has transfer services (n_services = 0, item 5). On layouts with services, M2+M3 schedules could depend on P.
   - Only the ranking of the rules changes: M2 to r2 on 8 instances and r2 to M2 on 1.
   - So on these 9 instances the paired comparison sets the ILP against a different rule schedule. Section 3.6
     explains why.
5. **M3 is never active.**
   - n_services = 0 on every instance, so M2+M3 equals M2 on 80/80 rows. The best rule is in effect the minimum of
     r2 and M2.
   - Rule totals are identical on the written and relaxed target copies (120/120 pairs). Both facts hold in round 5
     as well.
   - The auto-generated `RESULTS.md` still lists M3 and uses the internal label "M2M3".
6. **The served share counts unservable orders in its denominator.**
   - 13/40 instances have one order that cannot be served at all (`n_unservable` = 1).
   - The ILP serves every servable order on nyc4h (10/10 instances), usd4h x0.75 (10/10) and usd4h x1 (8/10). On x1
     seeds 2 and 3 it leaves one servable order unserved.
   - Section 3.4 also reports the served share of servable orders.
7. **Some old-price lateness figures are reconstructed.**
   - The round-5 records do not have per-order lateness: no count of orders more than 30 or 60 min late, and no
     maximum lateness.
   - For the old best rule these figures are read from the new-price row of the same rule and target copy. This is
     exact by item 4.
   - For the old ILP only a bound is available: total late minutes = lateness USD / 36 × 60, which is at most
     15 min per window. Its counts of orders more than 30 and 60 min late are therefore exactly 0, but its maximum
     lateness is only bounded (≤ 15 min).
8. **The end-adjusted price of recovery is slightly negative** (−0.05 ± 0.08 USD), as in round 5.
   - The relaxed ILP minimises the raw objective, not the end-adjusted one. The size is 0.009 % of the ILP cost and
     is negligible.
   - For the same reason, an old ILP plan repriced at the new prices can beat the new ILP by up to 0.12 USD on the
     end-adjusted total. This happens on 2 instances. On the raw objective it never does.
9. **The written ILP rejects its MIP start on 6/10 usd4h x1 seeds** (start `r2_unclean`). Round 5 was the same
   (4/10 accepted). All 10 written solves are OPTIMAL, so this has no effect.
10. **Notes on the auto-generated `RESULTS.md`.** Its numbers are correct: gap means, CIs and n match this
    recomputation to at least 4 decimals, and the other key columns match to 2 decimals. Its labels mislead in
    three places.
    - Its `ilp_max_lateness_min` is the seed mean of each window's maximum (14 / 3 / 13.5 / 22 min), not a
      maximum. The overall maxima are 35 / 10 / 35 / 45 min.
    - Its `ilp_mip_gap` of "0.00" at x1.5 is a seed mean and hides the three gaps of 0.33-1.07 %. Its anomaly
      line does report them.
    - It has no round-5 comparison, no cost components and no rule identity.

## 2. Coverage

| Item | Value |
|---|---|
| Records / unique keys | 290 / 290 (no duplicates); written 10:38-11:46 on 2026-10-18; wall time 68.1 min of a 150 min budget |
| Rule rows | 240 POLICY = 4 groups × 10 seeds × 2 target copies × 3 rules (r2, M2, M2+M3) |
| ILP rows, relaxed | 40: 37 OPTIMAL, 3 TIME_LIMIT (usd4h x1.5 seeds 0 / 5 / 8, MIP gap 1.07 / 0.33 / 0.91 %) |
| ILP rows, written (usd4h x1 only, by design) | 10: 10 OPTIMAL (max MIP gap 9.9e-5) |
| Max MIP gap of the OPTIMAL rows | 9.2e-5 |
| Skipped / errors | 0 SKIPPED_BUDGET, 0 ERROR. No solve was budget-shortened (time limit 300 s = requested on 50/50). No rows copied from other stages |
| Solver settings | aggregated ILP (single commodity), Threads 3, Gurobi Seed 0, TimeLimit 300 s, on all 50 ILP rows |
| Integrity | ILP objective = `evaluate.cost` on 50/50 rows. `check_ok` on 50/50. Library price check (`check_lib_prices`) on every row, 78-162 arcs checked |
| Pricing | P 60, w 18, v 15 on 290/290 rows (`cost_variant` usd_r6) |
| Same instances as round 5 | demand and order hashes equal on 290/290 keys. The round-5 headline gap is reproduced from its records with a max difference of 3.6e-15 points |
| Reproduction of the old prices with the round-6 code | the vsweep bridge cell (P 30, v 36; `outputs/r6_penalty/vsweep/records.jsonl`) reproduces the 40 round-5 usd4h x1 rows exactly, except one relaxed ILP (seed 0, both OPTIMAL) that is 0.045 USD higher, within the MIP tolerance |

Relaxed ILP runtime in seconds (mean / max):

| Group | New prices | Old prices |
|---|---|---|
| usd4h x0.75 | 24.5 / 41.8 | 19.5 / 27.1 |
| usd4h x1 | 43.5 / 144.8 | 39.1 / 111.9 |
| usd4h x1 (written) | 54.2 / 176.4 | 66.6 / 206.3 |
| usd4h x1.5 | 215.5 / 300.0 | 53.9 / 89.3 |
| nyc4h | 29.3 / 67.3 | 13.6 / 19.5 |

## 3. Answer: the gap survives the new prices

**Short answer.**
- The gap is positive on 40/40 instances.
- At usd4h x0.75 and x1 and on nyc4h it is statistically unchanged from round 5.
- At usd4h x1.5 it is 5 points lower but still 38 %. The USD saving is unchanged in every group.
- What changes is where the saving comes from. Under the new prices the ILP's main advantage is that it serves more
  orders, no longer that it avoids lateness.

### 3.1 Gap per family and demand level (new prices)

| Group | n | ILP status | Gap (%) | 95 % CI | Min-max (%) | > 0 | Gap with ILP bound (upper limit, %) | Gap vs r2 only (%) | Gap vs M2 only (%) |
|---|---|---|---|---|---|---|---|---|---|
| usd4h x0.75 | 10 | 10 OPT | **9.56 ± 2.83** | [6.73, 12.38] | 4.92-16.31 | 10/10 | 9.80 ± 2.82 | 12.02 ± 2.92 | 10.96 ± 3.32 |
| usd4h x1 | 10 | 10 OPT | **27.34 ± 5.65** | [21.69, 32.99] | 10.96-35.44 | 10/10 | 27.52 ± 5.63 | 27.45 ± 5.66 | 29.25 ± 6.50 |
| usd4h x1.5 | 10 | 7 OPT / 3 TL (≤ 1.07 %) | **38.42 ± 3.07** | [35.35, 41.49] | 28.26-45.35 | 10/10 | 38.63 ± 3.09 | 38.55 ± 3.06 | 39.39 ± 3.29 |
| nyc4h (lower bound) | 10 | 10 OPT | **27.88 ± 3.73** | [24.15, 31.61] | 19.78-34.00 | 10/10 | 28.05 ± 3.71 | 29.57 ± 5.00 | 30.06 ± 2.62 |
| usd4h pooled | 30 | 27 OPT / 3 TL | **25.10 ± 4.96** | [20.15, 30.06] | 4.92-45.35 | 30/30 | 25.32 ± 4.95 | 26.01 ± 4.61 | 26.53 ± 5.04 |

Costs in USD per window, end-adjusted:

| Group | n | Best rule | ILP | Saving (best rule − ILP) |
|---|---|---|---|---|
| usd4h x0.75 | 10 | 481.04 ± 20.60 | 434.37 ± 13.49 | 46.66 ± 15.01 |
| usd4h x1 | 10 | 838.50 ± 85.18 | 601.41 ± 28.71 | 237.09 ± 64.31 |
| usd4h x1.5 | 10 | 2081.28 ± 147.57 | 1275.53 ± 56.68 | 805.74 ± 112.16 |
| nyc4h | 10 | 863.66 ± 60.74 | 619.22 ± 19.05 | 244.44 ± 47.46 |
| usd4h pooled | 30 | 1133.61 ± 265.20 | 770.44 ± 139.38 | 363.17 ± 128.18 |

The gap still rises with demand, from 9.6 % to 27.3 % to 38.4 % on usd4h. In USD it rises from 47 to 237 to 806.

### 3.2 Paired comparison with round 5 (old prices), same instances

| Group | n | Gap, old prices (%) | Gap, new prices (%) | New − old (pts) | Paired t p | Seeds lower | Ratio of means | Saving old (USD) | Saving new (USD) | Saving new − old (USD) |
|---|---|---|---|---|---|---|---|---|---|---|
| usd4h x0.75 | 10 | 9.78 ± 2.88 | 9.56 ± 2.83 | −0.23 ± 2.55 | 0.85 | 7/10 | 0.98 | 47.74 ± 16.92 | 46.66 ± 15.01 | −1.07 ± 14.90 |
| usd4h x1 | 10 | 28.28 ± 7.36 | 27.34 ± 5.65 | −0.93 ± 4.86 | 0.67 | 5/10 | 0.97 | 248.87 ± 93.15 | 237.09 ± 64.31 | −11.78 ± 57.00 |
| usd4h x1.5 | 10 | 43.45 ± 5.86 | 38.42 ± 3.07 | **−5.03 ± 3.08** | 0.005 | 9/10 | 0.88 | 796.06 ± 181.03 | 805.74 ± 112.16 | +9.69 ± 72.84 |
| nyc4h | 10 | 27.37 ± 7.11 | 27.88 ± 3.73 | +0.51 ± 5.05 | 0.82 | 3/10 | 1.02 | 240.98 ± 95.41 | 244.44 ± 47.46 | +3.46 ± 67.86 |
| usd4h pooled | 30 | 27.17 ± 5.96 | 25.10 ± 4.96 | −2.06 ± 2.00 | 0.044 | 21/30 | 0.92 | 364.22 ± 133.98 | 363.17 ± 128.18 | −1.05 ± 27.45 |

- The old-price column reproduces the round-5 report (X1 Table 1, stage S4) exactly.
- The small pooled drop of −2.06 ± 2.00 points comes entirely from x1.5 (anomaly 1).
- The between-seed spread is smaller under the new prices at every demand level. For example, the CI half-width at
  x1 is 5.65 now against 7.36 before.

Cost change new − old at usd4h x1.5 (paired, USD per window):

| Term | Best rule | ILP |
|---|---|---|
| End-adjusted total | +294.90 ± 67.22 | +285.21 ± 31.37 |
| Unserved penalty | +507.00 ± 45.75 | +168.00 ± 56.51 |
| Lateness | −232.20 ± 73.32 | +22.35 ± 9.69 |
| Response | +20.25 ± 20.39 | +93.90 ± 35.08 |

### 3.3 Where the saving comes from (best rule − ILP, USD per window)

New prices, with the old-price share in brackets:

| Component | usd4h x0.75 | usd4h x1 | usd4h x1.5 | nyc4h | usd4h pooled (n = 30) |
|---|---|---|---|---|---|
| Unserved penalty | 18.00 ± 20.73 (38.6 %; old 12.6 %) | 138.00 ± 60.87 (58.2 %; old 14.5 %) | 546.00 ± 47.24 (67.8 %; old 26.0 %) | 156.00 ± 64.62 (63.8 %; old 16.2 %) | 234.00 ± 88.91 (64.4 %; old 22.8 %) |
| Response time | 20.85 ± 9.54 (44.7 %; old 47.4 %) | 52.80 ± 33.42 (22.3 %; old 35.2 %) | 104.55 ± 54.97 (13.0 %; old 22.4 %) | 45.00 ± 46.04 (18.4 %; old 34.3 %) | 59.40 ± 23.00 (16.4 %; old 26.4 %) |
| Lateness | 6.50 ± 4.82 (13.9 %; old 37.1 %) | 45.50 ± 21.71 (19.2 %; old 49.8 %) | 155.25 ± 45.34 (19.3 %; old 51.5 %) | 42.88 ± 27.39 (17.5 %; old 49.1 %) | 69.08 ± 28.07 (19.0 %; old 50.5 %) |
| Travel | 1.01 ± 0.61 | 0.68 ± 0.91 | −0.11 ± 0.59 | 0.53 ± 0.83 | 0.53 ± 0.40 |
| Electricity | 0.66 ± 0.08 | 0.60 ± 0.07 | 0.59 ± 0.12 | 0.60 ± 0.07 | 0.62 ± 0.05 |
| End-state adjustment | −0.35 ± 0.12 | −0.49 ± 0.14 | −0.54 ± 0.11 | −0.58 ± 0.06 | −0.46 ± 0.07 |
| Set-up, rebalancing, dummy terminal | 0 | 0 | 0 | 0 | 0 |
| **Total** | 46.66 ± 15.01 | 237.09 ± 64.31 | 805.74 ± 112.16 | 244.44 ± 47.46 | 363.17 ± 128.18 |

- The components sum to the total exactly; the check difference is below 1e-9.
- Service terms (unserved + response + lateness) make up at least 91.7 % of the saving on every instance. The
  minimum per group is 91.7 % (x0.75), 98.6 % (x1), 99.9 % (x1.5) and 98.3 % (nyc4h).
- Under old prices, lateness was the largest part of the saving (about half). Under new prices, the unserved penalty
  is the largest part: 58-68 % of the saving at x1, x1.5 and nyc4h.

### 3.4 Service quality under the new prices (best rule vs ILP)

Mean ± 95 % CI over 10 seeds. Each cell reads "best rule / ILP", then the paired ILP − rule difference in brackets.

| Metric | usd4h x0.75 | usd4h x1 | usd4h x1.5 | nyc4h |
|---|---|---|---|---|
| Served share | 0.981 / 0.993 (+0.011 ± 0.013) | 0.925 / 0.989 (+0.064 ± 0.028) | 0.674 / 0.843 (+0.169 ± 0.015) | 0.911 / 0.983 (+0.072 ± 0.030) |
| Served share of servable orders | 0.989 / 1.000 | 0.930 / 0.994 | 0.683 / 0.854 | 0.926 / 1.000 |
| Unserved orders | 0.5 / 0.2 (−0.3 ± 0.3) | 2.7 / 0.4 (−2.3 ± 1.0) | 17.6 / 8.5 (−9.1 ± 0.8) | 3.2 / 0.6 (−2.6 ± 1.1) |
| Late orders | 3.2 / 0.7 (−2.5 ± 1.2) | 13.9 / 3.1 (−10.8 ± 3.6) | 24.2 / 8.4 (−15.8 ± 3.2) | 14.9 / 4.4 (−10.5 ± 4.5) |
| Orders > 30 min late | 0 / 0 | 1.2 / 0.2 (−1.0 ± 1.3) | 11.2 / 0.2 (−11.0 ± 4.5) | 0.8 / 0.1 (−0.7 ± 1.4) |
| Orders > 60 min late | 0 / 0 | 0 / 0 | 0.1 / 0 (one order: seed 8, 65 min) | 0 / 0 |
| Mean lateness, all served orders (min) | 1.16 / 0.19 (−0.97 ± 0.71) | 6.47 / 0.93 (−5.54 ± 2.62) | 19.75 / 2.03 (−17.72 ± 5.40) | 6.32 / 1.15 (−5.17 ± 3.06) |
| Mean lateness, late orders only (min) | 8.48 / 2.58 | 14.06 / 7.87 | 28.24 / 10.45 | 12.65 / 8.27 |
| Max lateness per window, mean over seeds (min) | 11.5 / 3.0 (−8.5 ± 4.8) | 27.5 / 13.5 (−14.0 ± 6.3) | 52.0 / 22.0 (−30.0 ± 5.3) | 24.5 / 14.0 (−10.5 ± 2.6) |
| Max lateness over all 10 windows (min) | 30 / 10 | 40 / 35 | 65 / 45 (seed 8, TIME_LIMIT incumbent) | 40 / 35 |
| 90th-percentile lateness (min) | 3.9 / 0.2 | 18.9 / 1.9 | 40.9 / 8.0 | 17.0 / 3.8 |

### 3.5 Service quality, new − old prices (paired per instance)

| Metric | Who | usd4h x0.75 | usd4h x1 | usd4h x1.5 | nyc4h |
|---|---|---|---|---|---|
| Served share | best rule | 0.981 → 0.981 (0) | 0.919 → 0.925 (+0.006 ± 0.013) | 0.661 → 0.674 (+0.013 ± 0.014) | 0.906 → 0.911 (+0.006 ± 0.013) |
| Served share | ILP | 0.989 → 0.993 (+0.004 ± 0.008) | 0.953 → 0.989 (**+0.036 ± 0.025**) | 0.789 → 0.843 (**+0.054 ± 0.020**) | 0.942 → 0.983 (**+0.042 ± 0.017**) |
| ILP − rule served-share advantage | both | 0.007 → 0.011 | 0.033 → 0.064 (+0.031 ± 0.029) | 0.128 → 0.169 (+0.041 ± 0.025) | 0.036 → 0.072 (+0.036 ± 0.013) |
| Unserved orders | ILP | 0.3 → 0.2 | 1.7 → 0.4 (−1.3 ± 0.9) | 11.4 → 8.5 (−2.9 ± 1.1) | 2.1 → 0.6 (−1.5 ± 0.6) |
| Late orders | best rule | 3.2 → 3.2 | 13.5 → 13.9 | 23.2 → 24.2 | 14.7 → 14.9 |
| Late orders | ILP | 0.3 → 0.7 (+0.4 ± 0.5) | 0.6 → 3.1 (+2.5 ± 1.9) | 0.3 → 8.4 (+8.1 ± 2.0) | 0.8 → 4.4 (+3.6 ± 1.5) |
| Mean lateness, served (min) | ILP | 0.06 → 0.19 | 0.09 → 0.93 (+0.84 ± 0.77) | 0.04 → 2.03 (+2.00 ± 0.85) | 0.13 → 1.15 (+1.02 ± 0.66) |
| Orders > 30 min late | ILP | 0 → 0 | 0 → 0.2 | 0 → 0.2 | 0 → 0.1 |
| Orders > 60 min late | best rule / ILP | 0 → 0 / 0 → 0 | 0 → 0 / 0 → 0 | 0.3 → 0.1 / 0 → 0 | 0 → 0 / 0 → 0 |
| Max lateness (min) | ILP | ≤ 5 → 10 | ≤ 10 → 35 | ≤ 5 → 45 | ≤ 15 → 35 |

The changes in the best rule come only from switching which rule is best (anomaly 4). The rule schedules themselves
are identical in both rounds on these instances, because M3, the only price-aware rule component, is inactive.

### 3.6 Which rule is the best rule

| Group | New prices: r2 / M2 | Old prices: r2 / M2 | Changed | r2 − M2 cost, new (USD) | r2 − M2 cost, old (USD) |
|---|---|---|---|---|---|
| usd4h x0.75 | 3 / 7 | 3 / 7 | 0 | +5.53 ± 20.33 | +8.15 ± 29.96 |
| usd4h x1 | 8 / 2 | 6 / 4 | 4 (3 M2 → r2, 1 r2 → M2) | −25.71 ± 26.56 | −6.66 ± 27.55 |
| usd4h x1.5 | 8 / 2 | 4 / 6 | 4 (M2 → r2) | −31.79 ± 29.84 | +18.03 ± 31.79 |
| nyc4h | 5 / 5 | 4 / 6 | 1 (M2 → r2) | +0.09 ± 46.77 | +18.89 ± 33.78 |
| all | **24 / 16** | 17 / 23 | 9 | | |

- M2 here always ties with M2+M3, because M3 has no services to act on.
- r2 serves more orders than M2: +0.6 per window at x1, +1.2 at x1.5 and +0.3 on nyc4h. It also has more response
  time and lateness. Under P 60 the extra served orders are worth 18-72 USD per window, so r2 becomes the cheaper
  rule at higher demand.

### 3.7 Price of recovery on usd4h x1 (written-target ILP − relaxed-target ILP)

| | New prices | Old prices | New − old (paired) |
|---|---|---|---|
| Raw total (USD) | 0.41 ± 0.13 (range 0.20 to 0.73) | 0.41 ± 0.10 | +0.003 ± 0.109 |
| End-adjusted total (USD) | −0.05 ± 0.08 (range −0.28 to +0.06) | −0.03 ± 0.06 | −0.03 ± 0.05 |
| Written ILP status | 10/10 OPTIMAL (max MIP gap 9.9e-5) | 10/10 OPTIMAL | |
| Served share, written − relaxed | 0.000 | | |
| Gap if the written ILP is the comparator | 27.35 ± 5.65 % | | |

Recovering the written end targets costs 0.41 USD per window, which is 0.07 % of the ILP cost. The price change does
not affect it.

### 3.8 Supporting check: how much the ILP adapts to the new prices

The order terms are linear in uniform prices (P per unserved order, v per late hour, w unchanged). The old-price ILP
plans can therefore be repriced exactly from their records. The formula reproduces the new-price rule rows to
1.1e-13 USD on the 31 instances whose best rule did not change.

| Group | Old ILP plan at new prices − new ILP (USD) | Gap if the ILP had kept its old plan (%) | Actual new gap (%) |
|---|---|---|---|
| usd4h x0.75 | 3.25 ± 7.18 | 8.93 ± 2.82 | 9.56 |
| usd4h x1 | 30.58 ± 18.87 | 23.89 ± 5.49 | 27.34 |
| usd4h x1.5 | 56.27 ± 22.95 | 35.77 ± 2.52 | 38.42 |
| nyc4h | 35.97 ± 10.71 | 23.76 ± 3.40 | 27.88 |

Re-optimising for the new prices is worth 3-56 USD per window, or 0.6-4.1 points of gap. The ILP's decisions change
mainly by serving more orders.

## 4. Figures (`figs/`, vector PDF and 300-dpi PNG; script `figs/r6_headline_figs.py`)

- `r6_gap_old_vs_new.{pdf,png}` (6.0 in wide). Gap per family and demand level under old prices (hollow) and new
  prices (filled), with mean ± 95 % t-CI. Grey lines join the two values of each seed. The paired difference and n
  are printed above each group.
- `r6_saving_components.{pdf,png}` (6.0 in). Saving of the ILP over the best rule, stacked by component (unserved
  penalty, response time, lateness, and travel + electricity + end state), old and new prices side by side. The
  black marker is the total, mean ± 95 % CI. The grey "other" component is under 3 % of the saving in every group and barely visible.
- `r6_service_quality.{pdf,png}` (7.2 in, four panels): served share, late orders per window, orders more than
  30 min late per window, and mean lateness of served orders. Orange = best rule, blue = ILP; hollow = old prices,
  filled = new prices. The old ILP value in panel (c) is derived (anomaly 7). Orders more than 60 min late are not
  plotted because they are 0 for the ILP everywhere and at most 0.3 per window for the rule (Table 3.5).

## 5. Interpretation

**What the records show.**
- The coordination gap survives the recalibrated prices. It is positive on all 40 instances.
- At usd4h x0.75, usd4h x1 and nyc4h it is statistically indistinguishable from round 5: 9.6 %, 27.3 % and 27.9 %,
  with paired changes of −0.2, −0.9 and +0.5 points. All three CIs include 0.
- At usd4h x1.5 the percentage falls from 43.5 % to 38.4 %, but the USD saving is unchanged (806 against
  796 USD). The fall comes from the larger cost of orders that neither method serves (anomaly 1), not from a
  smaller advantage of coordination.
- The USD saving is unchanged in every group. Pooled usd4h: −1.05 ± 27.45 USD.
- The headline therefore did not depend on cheap order dropping. With dropping twice as expensive and lateness less
  than half as expensive:
  - The ILP serves more orders. Its served share is 98.9 % against 95.3 % at x1 and 98.3 % against 94.2 % on
    nyc4h.
  - Its served-share advantage over the best rule grows from +3.3 to +6.4 points at x1, from +12.8 to +16.9 at
    x1.5 and from +3.6 to +7.2 on nyc4h.
  - It is late more often but never badly: at most 45 min (a TIME_LIMIT incumbent; at most 35 min on OPTIMAL
    rows), and no order more than 60 min late. The best rule keeps
    11.2 orders per window more than 30 min late at x1.5.
- The saving is still almost entirely service quality (at least 91.7 % on every instance), but its make-up flips.
  The unserved penalty now gives 64 % of the pooled usd4h saving (was 23 %), and lateness gives 19 % (was 51 %).
- On these instances the rule schedules do not react to the prices: r2 and M2 read no order prices, and M3, the
  only price-aware part, is inactive without services. Only their ranking moves: r2 is now the best rule on 24/40
  instances, against 17/40 before.
- The price of recovery stays negligible (0.41 USD raw).

**What the records suggest but do not show.**
- That the gap is robust to the order prices in general. Only two price points are compared here. The psweep and
  vsweep stages test the gap along each price axis.
- That the 15 % of orders the ILP still leaves unserved at x1.5 reflects fleet capacity (6 bikes, 54 orders in 4 h)
  or the end of the window, rather than pricing.
  - The promise falls 45-60 min after release (9-12 slots in the usd4h x1.5 seed-0 instance).
  - Serving an order on time therefore costs about 16 USD of response. Each further hour of delay costs 33 USD
    (w + v).
  - Dropping an order becomes cheaper only once it is about 1.3 h late, while the ILP's largest lateness is 45 min.
  - Some promises fall after the 4-h window (latest promise slot 50, horizon 48).
  - These records do not separate the two causes.
- That a price-aware rule would narrow the gap. The rules (r2, M2) ignore order prices, and M3, the only
  price-aware part, is inactive without services. Part of the remaining gap may be what a price-aware admission rule
  could recover. Not tested here.
- That the x1.5 percentage gap would be a little higher with the three time-limited cells solved to optimality. The
  bound allows at most +0.21 points on the group mean.

**For the manuscript.** Report the gap in both percent and USD per window. State that the composition of the saving
depends on the order prices while its size does not. Keep the demand gradient (9.6 / 27.3 / 38.4 %), which survives
the recalibration. Re-solve usd4h x1.5 seeds 0, 5 and 8 at 600 s before quoting the x1.5 gap.

## Appendix A. Per-instance values (new prices unless stated; costs end-adjusted, USD per window)

| Family | Demand | Seed | Best rule (new / old) | Best rule, new (USD) | ILP, new (USD) | ILP status (MIP gap) | Gap new (%) | Gap old (%) | New − old (pts) | Served share, best rule / ILP, new | ILP late orders, new / old |
|---|---|---|---|---|---|---|---|---|---|---|---|
| usd4h | x0.75 | 0 | M2 / M2 | 457.43 | 433.78 | OPTIMAL | 5.17 | 6.33 | −1.16 | 0.963 / 0.963 | 0 / 0 |
| usd4h | x0.75 | 1 | r2 / r2 | 502.56 | 420.57 | OPTIMAL | 16.31 | 12.93 | +3.38 | 0.963 / 1.000 | 0 / 0 |
| usd4h | x0.75 | 2 | M2 / M2 | 447.74 | 425.73 | OPTIMAL | 4.92 | 5.29 | −0.37 | 1.000 / 1.000 | 0 / 0 |
| usd4h | x0.75 | 3 | M2 / M2 | 533.25 | 471.48 | OPTIMAL | 11.58 | 7.06 | +4.53 | 0.926 / 0.963 | 0 / 0 |
| usd4h | x0.75 | 4 | M2 / M2 | 475.50 | 410.17 | OPTIMAL | 13.74 | 8.29 | +5.45 | 0.963 / 1.000 | 0 / 0 |
| usd4h | x0.75 | 5 | M2 / M2 | 521.04 | 456.92 | OPTIMAL | 12.31 | 17.96 | −5.66 | 1.000 / 1.000 | 3 / 1 |
| usd4h | x0.75 | 6 | M2 / M2 | 460.32 | 435.24 | OPTIMAL | 5.45 | 6.86 | −1.42 | 1.000 / 1.000 | 1 / 1 |
| usd4h | x0.75 | 7 | r2 / r2 | 479.17 | 445.92 | OPTIMAL | 6.94 | 8.18 | −1.24 | 1.000 / 1.000 | 2 / 1 |
| usd4h | x0.75 | 8 | r2 / r2 | 474.83 | 425.41 | OPTIMAL | 10.41 | 13.47 | −3.06 | 1.000 / 1.000 | 1 / 0 |
| usd4h | x0.75 | 9 | M2 / M2 | 458.55 | 418.52 | OPTIMAL | 8.73 | 11.43 | −2.70 | 1.000 / 1.000 | 0 / 0 |
| usd4h | x1 | 0 | r2 / M2 | 599.96 | 534.18 | OPTIMAL | 10.96 | 12.88 | −1.91 | 1.000 / 1.000 | 0 / 0 |
| usd4h | x1 | 1 | r2 / r2 | 886.04 | 592.47 | OPTIMAL | 33.13 | 29.71 | +3.43 | 0.889 / 1.000 | 3 / 0 |
| usd4h | x1 | 2 | r2 / M2 | 824.24 | 618.13 | OPTIMAL | 25.01 | 19.99 | +5.02 | 0.889 / 0.972 | 3 / 1 |
| usd4h | x1 | 3 | r2 / r2 | 902.18 | 614.48 | OPTIMAL | 31.89 | 31.79 | +0.10 | 0.889 / 0.972 | 2 / 1 |
| usd4h | x1 | 4 | r2 / M2 | 716.97 | 545.80 | OPTIMAL | 23.87 | 13.98 | +9.90 | 0.917 / 1.000 | 1 / 1 |
| usd4h | x1 | 5 | M2 / M2 | 875.41 | 634.99 | OPTIMAL | 27.46 | 31.97 | −4.51 | 0.917 / 0.972 | 4 / 0 |
| usd4h | x1 | 6 | r2 / r2 | 956.87 | 617.76 | OPTIMAL | 35.44 | 41.39 | −5.95 | 0.917 / 0.972 | 4 / 2 |
| usd4h | x1 | 7 | r2 / r2 | 749.38 | 610.67 | OPTIMAL | 18.51 | 27.84 | −9.33 | 1.000 / 1.000 | 5 / 0 |
| usd4h | x1 | 8 | r2 / r2 | 994.81 | 667.31 | OPTIMAL | 32.92 | 43.83 | −10.91 | 0.944 / 1.000 | 8 / 0 |
| usd4h | x1 | 9 | M2 / r2 | 879.18 | 578.31 | OPTIMAL | 34.22 | 29.39 | +4.83 | 0.889 / 1.000 | 1 / 1 |
| usd4h | x1.5 | 0 | M2 / M2 | 1735.86 | 1091.37 | TIME_LIMIT (1.07 %) | 37.13 | 37.79 | −0.66 | 0.741 / 0.907 | 7 / 0 |
| usd4h | x1.5 | 1 | r2 / r2 | 2105.87 | 1296.20 | OPTIMAL | 38.45 | 44.38 | −5.94 | 0.667 / 0.833 | 6 / 0 |
| usd4h | x1.5 | 2 | r2 / r2 | 1801.71 | 1292.62 | OPTIMAL | 28.26 | 24.53 | +3.73 | 0.648 / 0.815 | 6 / 0 |
| usd4h | x1.5 | 3 | M2 / M2 | 2168.43 | 1329.91 | OPTIMAL | 38.67 | 46.17 | −7.50 | 0.648 / 0.815 | 7 / 0 |
| usd4h | x1.5 | 4 | r2 / M2 | 1975.56 | 1219.23 | OPTIMAL | 38.28 | 40.11 | −1.83 | 0.685 / 0.852 | 7 / 0 |
| usd4h | x1.5 | 5 | r2 / M2 | 2195.16 | 1302.78 | TIME_LIMIT (0.33 %) | 40.65 | 47.66 | −7.00 | 0.667 / 0.852 | 11 / 1 |
| usd4h | x1.5 | 6 | r2 / r2 | 2389.23 | 1305.71 | OPTIMAL | 45.35 | 54.42 | −9.07 | 0.648 / 0.852 | 13 / 0 |
| usd4h | x1.5 | 7 | r2 / r2 | 2217.07 | 1370.15 | OPTIMAL | 38.20 | 47.96 | −9.76 | 0.667 / 0.796 | 7 / 1 |
| usd4h | x1.5 | 8 | r2 / M2 | 2249.85 | 1324.35 | TIME_LIMIT (0.91 %) | 41.14 | 49.32 | −8.18 | 0.667 / 0.852 | 14 / 1 |
| usd4h | x1.5 | 9 | r2 / M2 | 1974.01 | 1223.01 | OPTIMAL | 38.04 | 42.11 | −4.06 | 0.704 / 0.852 | 6 / 0 |
| nyc4h | x1 | 0 | r2 / M2 | 963.49 | 653.43 | OPTIMAL | 32.18 | 44.19 | −12.01 | 1.000 / 1.000 | 7 / 1 |
| nyc4h | x1 | 1 | M2 / M2 | 890.58 | 647.39 | OPTIMAL | 27.31 | 27.21 | +0.10 | 0.889 / 0.972 | 5 / 1 |
| nyc4h | x1 | 2 | r2 / r2 | 776.05 | 619.07 | OPTIMAL | 20.23 | 17.90 | +2.33 | 0.917 / 0.972 | 3 / 0 |
| nyc4h | x1 | 3 | M2 / M2 | 943.51 | 636.08 | OPTIMAL | 32.58 | 19.44 | +13.14 | 0.806 / 0.972 | 6 / 2 |
| nyc4h | x1 | 4 | M2 / M2 | 935.73 | 631.91 | OPTIMAL | 32.47 | 32.85 | −0.38 | 0.889 / 0.972 | 3 / 1 |
| nyc4h | x1 | 5 | M2 / M2 | 800.19 | 574.96 | OPTIMAL | 28.15 | 23.67 | +4.48 | 0.917 / 1.000 | 2 / 1 |
| nyc4h | x1 | 6 | r2 / r2 | 758.99 | 608.88 | OPTIMAL | 19.78 | 17.88 | +1.90 | 0.917 / 0.972 | 3 / 1 |
| nyc4h | x1 | 7 | r2 / r2 | 863.09 | 615.68 | OPTIMAL | 28.67 | 27.47 | +1.20 | 0.889 / 0.972 | 3 / 0 |
| nyc4h | x1 | 8 | M2 / M2 | 951.81 | 628.19 | OPTIMAL | 34.00 | 43.44 | −9.44 | 0.944 / 1.000 | 8 / 0 |
| nyc4h | x1 | 9 | r2 / r2 | 753.18 | 576.66 | OPTIMAL | 23.44 | 19.61 | +3.82 | 0.944 / 1.000 | 4 / 1 |

In this table M2 stands for M2 = M2+M3; the two tie on every instance. Round-5 ILP status: OPTIMAL on all 40
instances.

## Verification corrections (R6)

Two claims were refuted by at least one of two independent refuters. Both were recomputed from
`outputs/r6_penalty/headline/records.jsonl` and `outputs/r5_x1_headline/records.jsonl` (calib ebaas). No number in
the report changed, no table value changed, and no figure is affected. The corrections narrow the scope or add
missing status and detail.

| Claim | Refuter 1 | Refuter 2 | Recomputed (this check) | Decision | What changed |
|---|---|---|---|---|---|
| C3: rule schedules do not depend on order prices; all 240 rule rows are physically identical between round 5 and round 6 | not refuted (suggests narrower wording) | refuted (scope only; numbers reproduce) | 240/240 rule keys match one-to-one, status POLICY in both rounds, max abs. difference exactly 0 on all ten physical fields; unserved = 2 × old and lateness = 15/36 × old on 240/240 rows; n_services = 0 and transfers_used = 0 on 240/240; M2+M3 = M2 on 80/80 instance-target pairs. Code: `baseline.stockout_value` reads mean P_i (M3), and `transfer_rule` is forced to NONE when an instance has no services | Numbers correct. Refuter 2 is right that the opening sentence was too general: M2+M3 reads P through the M3 stock-out value whenever services exist | Anomaly 4 now scopes the statement to this stage, gives n, families and status, states the exact ×2 and ×15/36 repricing, and explains that independence holds by construction because M3 is inert (n_services = 0). Same scoping added to the note under Table 3.5 and to the Section 5 bullet on rule reaction |
| C5: no ILP order > 60 min late (max 45 min, usd4h x1.5); rule rows > 60 min only at usd4h x1.5 (M2 seeds 5, 6, 8; r2 seed 8); best rule has one such order (seed 8, 65 min) | refuted (incomplete list; no status) | refuted (same two points; substance holds) | ILP: n = 50 (47 OPTIMAL, 3 TIME_LIMIT), 0 orders > 60 min on 50/50, max 45 min on one row only: usd4h x1.5 relaxed seed 8, TIME_LIMIT, MIP gap 0.91 %; max on OPTIMAL rows 35 min; max orders > 30 min per window 2. Rules: 14 rows with orders > 60 min, all usd4h x1.5, identical on both target copies: r2 s8 (1, 65 min); M2 and M2+M3 s5 (2, 65 min), s6 (2, 70 min), s8 (1, 65 min). Best rule is r2 on s5, s6, s8 (2195.16 / 2389.23 / 2249.85 USD vs M2 2247.95 / 2476.16 / 2265.64), so 1 order in total (s8, 65 min) | Both refuters right on wording; all numbers reproduce. The rule-row list omitted M2+M3 (which equals M2) and the per-seed counts, and the 45-min ILP maximum was not flagged as a TIME_LIMIT incumbent | Anomaly 3 now gives n and status of the ILP rows, flags the 45-min maximum as a TIME_LIMIT incumbent (0.91 %) with 35 min as the OPTIMAL-row maximum, and lists every rule row with orders > 60 min, including M2+M3, with counts and the best-rule identity under both prices. Table 3.4 marks the 45-min cell as a TIME_LIMIT incumbent. Section 5 adds the same qualifier |

Verification script (not part of the pipeline): the join and filters above were run directly on the two
`records.jsonl` files; the report tables (`figs/r6_headline_tables.py`, `per_instance_final.csv`,
`summary_final.json`) and figures (`figs/r6_headline_figs.py`) were not regenerated, because no value they contain
changed.
