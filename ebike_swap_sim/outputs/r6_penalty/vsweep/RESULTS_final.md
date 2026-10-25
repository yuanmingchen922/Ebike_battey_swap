# R6 vsweep: lateness price sweep at the new penalty, and the old-price bridge (final report)

Stage: `vsweep` of `experiments/r6_penalty.py`. Family usd4h (6 bikes, 36 orders, 4-h window, eBaaS energy
calibration), demand x1, seeds 0-9. Prices: unserved penalty P = 60 USD, response price w = 18 USD/h from release,
lateness price v in {8, 15, 25, 36} USD/h from the promise ("new prices" = P 60, v 15), plus the bridge (P 30, v 36) =
the "old prices" of round 5 on the same instances.

Sources: `vsweep/records.jsonl` (200 records, 200 unique keys, last record per key); round 5:
`outputs/r5_x1_headline/records.jsonl` (usd4h, eBaaS, x1); for the old-to-new split only: `psweep/records.jsonl`
(usd4h x1, P 30, v 15). Every number below was recomputed from the records by `figs/vsweep_final.py`, which writes
`per_instance_final.csv`, `summary_final.csv`, `paired_final.csv`, `envelope_final.csv`, `v0_bound_final.csv`,
`split_old_new_final.csv`, `bridge_vs_r5_final.csv`, `analysis_final.log` and the three figures. The auto-generated
`RESULTS.md` was checked against this recomputation (section 1, item 2).

Conventions. Best rule = per-instance minimum of the end-adjusted total over r2, M2 and M2+M3 (relaxed targets).
ILP = relaxed-target aggregated ILP (Threads 3, Gurobi Seed 0, TimeLimit 300 s). Gap = 100 (best rule - ILP) / best
rule per instance on end-adjusted totals, then averaged. "± h" is the exact Student-t 95 % half-width over seeds
(t_{0.975, n-1} s / sqrt n). Differences are paired per seed first. USD are per 4-h window.

## Summary

- At P 60 the gap rises with the lateness price on every seed: 25.80 ± 5.39 % (v 8), 27.34 ± 5.65 % (v 15),
  29.47 ± 6.08 % (v 25), 31.65 ± 6.56 % (v 36; two seeds use the best known schedule, so this is a lower bound).
  Slope 2.09 ± 0.75 points per 10 USD/h (n = 10, 10/10 seeds positive). On the 8 seeds solved to optimality at every
  v: 24.96 / 26.31 / 28.22 / 30.18 %, slope 1.87 ± 0.85.
- The ILP keeps lateness low at every v: 2.8-4.2 late orders per window, 0.7-1.1 min per served order, no order more
  than 60 min late, served share 0.986-0.992. The best rule does not react to v at all (its schedules are identical
  across v): 13.7-13.9 late orders, 6.4-6.5 min per served order, served share 0.925. The gap grows with v because the
  rule's fixed lateness (3.56-3.58 h per window) is priced higher, not because the ILP changes much.
- The bridge (P 30, v 36) reproduces round 5 on the same 10 instances: 28.28 ± 7.36 % in both rounds; paired
  difference -0.0012 ± 0.0025 points, largest single-seed difference 0.009 points.
- New vs old prices: 27.34 vs 28.28 %, paired -0.93 ± 4.86 points (n = 10, 5/10 seeds lower). The near-equality is a
  cancellation: lowering v from 36 to 15 lowers the gap by 5.05 ± 1.86 points (10/10 seeds), raising P from 30 to 60
  raises it by 4.12 ± 3.51 points (7/10).
- The headline is not driven by the lateness price. Lateness is 19 % of the coordination saving at the new prices
  (50 % at the old prices); the unserved penalty is 58 %. With no lateness price at all (v = 0) the gap is still at
  least 23.90 ± 5.15 % (raw totals; rigorous lower bound from the recorded schedules), so at most 3.54 ± 1.43 of the
  27.44 % (raw) base gap needs v > 0.
- Data problem: the two v 36 ILP cells for seeds 5 and 6 are not real solves. The laptop slept during them, Gurobi's
  wall-clock limit ran out, and the rows hold the rule MIP start (gap 0.00 %). The auto `RESULTS.md` v 36 row is
  therefore wrong (gap 24.14 ± 10.87 %). The resume logic will not re-solve these rows.

## 1. Problems and anomalies

1. **Two v 36 cells were cut by system sleep, not by solver difficulty.** The usd4h P 60 / v 36 relaxed ILPs for seeds
   5 and 6 report TIME_LIMIT with MIP gaps 0.901 and 0.909. Evidence that they are not solves:
   - the incumbent equals the MIP start exactly: 956.58 (M2 schedule) and 1093.86 USD (r2 schedule);
   - one node was processed and the bound stayed at 95.07 and 99.03 USD, so the root LP never finished;
   - Gurobi runtime was 949 s and 460 s against a 300 s limit, while the process clock (`wall_s`, `time.perf_counter`)
     recorded only 21.9 s and 44.5 s;
   - the macOS power log shows "Entering Sleep state due to 'Clamshell Sleep'" at 13:13:09 (on battery), dark wakes at
     13:28:52 and 13:40:20, and a full wake at 13:42:42. The rows were written at 13:28:59 and 13:40:21.

   Consequences:
   - The auto key table's v 36 row is contaminated: gap 24.14 ± 10.87 %, ILP 689.45 USD, ILP served share 0.975, ILP
     mean lateness 2.45 min, ILP late orders 6.3 and ILP max lateness 15.5 min. All of these include two rule
     schedules.
   - The auto paired table already drops the two seeds (n_pairs 8, `n_excluded_start` 2), but for the wrong stated
     reason ("different MIP starts").
   - `budget_cut` treats both rows as complete, because `time_limit_s` = `time_limit_requested_s` = 300 and
     `budget_shortened` = False. A resume will not re-solve them; the two rows must be deleted or flagged by hand.

   In this report, v 36 is given three ways: on the 8 optimal seeds; on all 10 seeds with the best known schedule for
   seeds 5 and 6 (labelled "best known"); and "as solved", for reference only.

   The best known schedule for both seeds is the v 25 optimum repriced at v 36 (section 3.1). It is an upper bound on
   the true optimum: on the 8 optimal seeds this repriced schedule is optimal at v 36 on 6 seeds and within 3.45 USD on
   the other 2.
2. **The auto `RESULTS.md` is otherwise correct.** Recomputed from the records, the gaps match: 25.80 ± 5.39,
   27.34 ± 5.65, 29.47 ± 6.08, 24.14 ± 10.87 (as solved) and 28.28 ± 7.36 %. So do all paired rows for v 8, v 25 and
   the bridge, and the v 36 rows on n = 8. The base cells (v 15) are identical to the headline-stage usd4h x1 cells:
   largest per-seed gap difference 0.0.
3. **The same sleep hit other R6 stages** (any row written between 13:13 and 13:43 local time on 2026-10-18):
   - psweep r5_stress4h P 40 / v 15 seed 9: TIME_LIMIT, Gurobi runtime 1093 s;
   - psweep usd4h P 80 / v 15 seed 0: TIME_LIMIT, runtime 459 s, gap 0.943;
   - fleet r5_stress4h seed 2: two `ILP_tl600` rows, TIME_LIMIT with runtimes 991 s and 604 s.

   Separately, `wall_time.json` (2362 s) undercounts the stage. The clock time was 67.6 min (12:47:56 to 13:55:30),
   because `perf_counter` does not advance while the machine sleeps.
4. **The MIP-start family differs between cells.** The v 15 cells were copied from the headline stage and start from
   the written-target ILP optimum; every other cell starts from a rule schedule. All 48 cells used in the comparisons
   are OPTIMAL (MIP gap at most 9.1e-5), so the objectives are comparable. Alternative optima can still shift the
   lateness counts slightly. On the bridge versus round 5 (also different starts), the end-adjusted ILP differs by at
   most 0.08 USD, and the served counts and late counts are identical.
5. **The best rule is taken over the relaxed copy only.** vsweep runs the rules on the relaxed-target copy only,
   whereas round 5 and the headline stage took the minimum over both target copies. This makes no difference here:
   the bridge best rule equals the round-5 best rule on 10/10 seeds, with a difference of 0.00 USD.
6. **M2+M3 = M2 on all 50 cells.** M3 needs services and usd4h has none, so "best rule" is effectively min(r2, M2).
   The rule picked per pricing (r2 / M2) is 8/2 at v 8, 8/2 at v 15, 7/3 at v 25, 7/3 at v 36 and 6/4 at the bridge.
7. **More than 60 min late is always zero.** No order is more than 60 min late under any method or pricing. Use the
   more-than-30-min count and mean lateness instead.
8. **Scope.** One family (usd4h), one demand level (x1) and 10 seeds. The between-seed spread is large (gap CIs ±5-8
   points), so effects of v are detectable only because every comparison is paired. The grace variant (v 17 from
   b_i + 10 min) was not run, by design (DECISIONS.md, R6 notes).
9. **Checks that pass:**
   - Cost identities hold on all 200 rows: total = parts; order cost = unserved + response + lateness;
     unserved = P x drops; lateness = v x the recorded late minutes; end-adjusted = total + end adjustment.
   - Demand hash and ILP arc/variable counts are identical across the 5 pricings of each seed.
   - Rule schedules (drops, response, late hours, other costs, end adjustment) are identical across v at P 60, and
     also between P 30 and P 60.
   - Objective = evaluated cost and the library price check pass on all 50 ILP rows.
   - Cross-pricing check: every ILP schedule found for a seed was repriced at every other pricing (9 schedules per seed,
     including 4 psweep pricings), giving 432 pairs on OPTIMAL cells. No repriced schedule beats a solved optimum by
     more than 0.045 USD (8.4e-5 relative), which is within the MIP tolerance.

## 2. Coverage

| item | value |
|---|---|
| records / unique keys / duplicates | 200 / 200 / 0 |
| cells | 5 pricings x 10 seeds; each cell has r2, M2, M2+M3 (POLICY) and the relaxed ILP |
| ILP status | 48 OPTIMAL, 2 TIME_LIMIT (P 60 / v 36, seeds 5 and 6, system sleep, item 1) |
| MIP gap of OPTIMAL rows | at most 9.1e-5 (v 8: 8.3e-5; v 15: 8.8e-5; v 25: 0; v 36: 9.1e-5; bridge: 8.4e-5) |
| ILP runtime mean / max (s) | v 8 57.2 / 226.0; v 15 43.5 / 144.8; v 25 47.5 / 102.7; v 36 OPTIMAL 43.2 / 91.2; bridge 53.7 / 187.8 |
| time limit | 300 s requested and applied on every row (`budget_shortened` False on all) |
| MIP starts | v 15: written-target ILP optimum (copied from headline, `reused_from` = headline, 40 rows); others: best rule schedule (r2 or M2, relaxed) |
| skipped / errors | 0 SKIPPED_BUDGET, 0 ERROR; nothing left unrun |
| solver settings | aggregated ILP, Threads 3, Gurobi Seed 0 (all 50 rows) |
| wall time | 67.6 min of clock time, of which 39.4 min of process time (2362 s in `wall_time.json`); the rest is the 13:13-13:42 sleep; budget 90 min |

## 3. Results

### 3.1 Gap and cost against the lateness price (Figure 1)

Table 1. End-adjusted gap and cost per window (mean ± 95 % CI). For the ILP, "OPT" counts the OPTIMAL rows.

| pricing | ILP status | gap, all 10 seeds (%) | min-max | gap > 0 | gap, 8 seeds optimal at every v (%) | best rule (USD) | ILP (USD) | saving (USD) |
|---|---|---|---|---|---|---|---|---|
| P 60, v 8 | 10 OPT | 25.80 ± 5.39 | 10.3-32.7 | 10/10 | 24.96 ± 6.77 | 813.42 ± 75.31 | 596.96 ± 26.14 | 216.46 ± 57.22 |
| P 60, v 15 (new prices) | 10 OPT | 27.34 ± 5.65 | 11.0-35.4 | 10/10 | 26.31 ± 6.98 | 838.50 ± 85.18 | 601.41 ± 28.71 | 237.09 ± 64.31 |
| P 60, v 25 | 10 OPT | 29.47 ± 6.08 | 12.0-39.1 | 10/10 | 28.22 ± 7.38 | 874.33 ± 100.30 | 606.69 ± 32.21 | 267.64 ± 76.01 |
| P 60, v 36, best known | 8 OPT + 2 best known | 31.65 ± 6.56 (lower bound) | 12.9-42.6 | 10/10 | 30.18 ± 7.86 | 913.51 ± 118.02 | 611.68 ± 35.51 | 301.83 ± 90.28 |
| P 60, v 36, as solved | 8 OPT + 2 TL (not solves) | 24.14 ± 10.87 | 0.0-40.0 | 8/10 | (same) | 913.51 ± 118.02 | 689.45 ± 133.53 | 224.06 ± 116.27 |
| P 30, v 36 (old prices, bridge) | 10 OPT | 28.28 ± 7.36 | 12.9-43.8 | 10/10 | 26.18 ± 8.55 | 830.91 ± 109.17 | 582.05 ± 18.40 | 248.86 ± 93.15 |

Best known schedules for v 36: seed 5 = 645.02 USD raw (TL incumbent 956.58), gap 32.47 %; seed 6 = 626.90 USD raw
(TL incumbent 1093.86), gap 42.63 %. Both come from the v 25 optimum repriced at v 36.

Table 2. Paired differences of the gap (points; per seed, then mean ± 95 % CI; "+k/-m" = seeds up / down).

| comparison | all 10 seeds (v 36 best known) | n | sign | 8 seeds optimal everywhere | n |
|---|---|---|---|---|---|
| v 8 - v 15 | -1.54 ± 0.61 (p = 0.0003) | 10 | +0/-10 | -1.35 ± 0.66 | 8 |
| v 25 - v 15 | +2.13 ± 0.75 (p = 0.0001) | 10 | +10/-0 | +1.90 ± 0.85 | 8 |
| v 36 - v 25 | +2.18 ± 0.78 | 10 | +10/-0 | +1.96 ± 0.91 | 8 |
| v 36 - v 15 | +4.31 ± 1.53 (p = 0.0001) | 10 | +10/-0 | +3.87 ± 1.76 (p = 0.001) | 8 |
| v 36 - v 8 | +5.85 ± 2.12 | 10 | +10/-0 | +5.22 ± 2.40 | 8 |
| OLS slope over v per seed (points per 10 USD/h) | 2.09 ± 0.75 | 10 | 10 > 0 | 1.87 ± 0.85 | 8 |

The gap is monotone increasing in v on every one of the 10 seeds (per-seed table in the appendix).

Cost response, v 36 - v 8 (paired, n = 10):
- best rule +100.09 ± 50.20 USD; this is exactly the rule's late hours x 28 USD/h, since its schedules do not change;
- ILP +14.72 ± 11.15 USD.

Late hours per window:
- best rule: 3.58 / 3.58 / 3.58 / 3.56 h at v 8 / 15 / 25 / 36;
- ILP: 0.67 / 0.55 / 0.51 / 0.42 h (v 36 - v 8 = -0.25 ± 0.28 h, not significant; 5 of 10 seeds change).

### 3.2 Lateness and service against v (Figure 2)

Table 3. Lateness and service per 4-h window (mean ± 95 % CI over seeds where shown; n = 10; v 36 ILP = best known).
Per-late-order minutes are pooled (total late minutes / total late orders). Max = largest single-order lateness over
the 10 seeds.

| pricing | method | late orders | > 30 min | > 60 min | min late per served order | min per late order | max (min) | served share | dropped orders |
|---|---|---|---|---|---|---|---|---|---|
| P 60, v 8 | ILP | 4.20 ± 2.40 | 0.1 | 0 | 1.12 ± 0.79 | 9.5 | 35 | 0.992 ± 0.010 | 0.3 |
| P 60, v 15 | ILP | 3.10 ± 1.67 | 0.2 | 0 | 0.93 ± 0.74 | 10.6 | 35 | 0.989 ± 0.010 | 0.4 |
| P 60, v 25 | ILP | 2.80 ± 1.71 | 0.2 | 0 | 0.85 ± 0.71 | 10.9 | 35 | 0.989 ± 0.010 | 0.4 |
| P 60, v 36 | ILP | 2.80 ± 1.71 | 0 | 0 | 0.71 ± 0.49 | 8.9 | 30 | 0.986 ± 0.011 | 0.5 |
| P 30, v 36 (old) | ILP | 0.60 ± 0.50 | 0 | 0 | 0.09 ± 0.07 | 5.0 | 5 | 0.953 ± 0.027 | 1.7 |
| P 60, v 8 / v 15 | best rule | 13.90 ± 4.67 | 1.2 | 0 | 6.47 ± 3.17 | 15.5 | 40 | 0.925 ± 0.031 | 2.7 |
| P 60, v 25 / v 36 | best rule | 13.70 ± 4.92 | 1.2 | 0 | 6.45 ± 3.19 / 6.42 ± 3.20 | 15.7 / 15.6 | 40 | 0.925 ± 0.031 | 2.7 |
| P 30, v 36 (old) | best rule | 13.50 ± 5.05 | 1.2 | 0 | 6.31 ± 3.26 | 15.5 | 40 | 0.919 ± 0.037 | 2.9 |

Paired ILP differences at P 60 (n = 10, v 36 best known):
- **Against v 15, nothing in the ILP's lateness or service is significant.**
  - v 8 - v 15: late orders +1.10 ± 1.60 (p = 0.15); mean lateness +0.19 ± 0.34 min; served share +0.003 ± 0.006.
  - v 36 - v 15: late orders -0.30 ± 0.48; mean lateness -0.22 ± 0.27 min (p = 0.11); served share -0.003 ± 0.006;
    drops +0.10 ± 0.23.
  - Most seeds do not change their ILP lateness at all between neighbouring v values; 3 of 10 seeds change between
    v 8 and v 15.
- **The rule's numbers in Table 3 move only because the argmin between r2 and M2 switches** on 1-2 seeds. The rule
  schedules themselves are fixed.

Old vs new prices (bridge minus base, ILP, n = 10):
- At the old prices the ILP drops more orders and is late less often: served share -0.036 ± 0.025 (p = 0.009, 7/10
  seeds lower), drops +1.30 ± 0.90 per window, late orders -2.50 ± 1.86 (p = 0.014), mean lateness -0.84 ± 0.77 min.
- This is round-5 artefact (e) in small form: under P 30 / v 36 a late order costs more than dropping it once it is
  about 13-18 min late. The new prices remove that incentive.

### 3.3 Where the saving comes from (Figure 3)

Table 4. Saving = best rule - ILP by cost term, USD per window (mean ± 95 % CI, n = 10; share = ratio of means;
v 36 ILP = best known).

| pricing | unserved penalty | response time | lateness | travel + energy + end state | total |
|---|---|---|---|---|---|
| P 60, v 8 | 144.00 ± 64.62 (66.5 %) | 48.45 ± 35.17 (22.4 %) | 23.33 ± 11.32 (10.8 %) | 0.68 (0.3 %) | 216.46 ± 57.22 |
| P 60, v 15 | 138.00 ± 60.87 (58.2 %) | 52.80 ± 33.42 (22.3 %) | 45.50 ± 21.71 (19.2 %) | 0.79 (0.3 %) | 237.09 ± 64.31 |
| P 60, v 25 | 138.00 ± 60.87 (51.6 %) | 52.20 ± 32.98 (19.5 %) | 76.67 ± 36.79 (28.6 %) | 0.76 (0.3 %) | 267.64 ± 76.01 |
| P 60, v 36 | 132.00 ± 63.34 (43.7 %) | 55.95 ± 36.93 (18.5 %) | 113.10 ± 56.74 (37.5 %) | 0.79 (0.3 %) | 301.83 ± 90.28 |
| P 30, v 36 (old) | 36.00 ± 47.24 (14.5 %) | 87.60 ± 57.81 (35.2 %) | 123.90 ± 66.31 (49.8 %) | 1.35 (0.5 %) | 248.86 ± 93.15 |

Mean of per-seed lateness shares: 10.6 ± 4.1, 18.4 ± 6.3, 27.0 ± 8.6, 34.6 ± 11.1 and 43.4 ± 11.3 %. The round-5 X1
value for pooled usd4h (x0.75 / x1 / x1.5) was 50.5 %.

### 3.4 Gap without any lateness price (v = 0)

Rule schedules do not depend on v, so the best rule at v = 0 is exact: the minimum over r2, M2 and M2+M3 of
(total - lateness). For the ILP at v = 0, every ILP schedule recorded for the seed (9 schedules per seed) was repriced
at v = 0 and the cheapest one taken. That is an upper bound on the true v = 0 optimum, so the gap below is a lower
bound. It is stated on raw totals, which keeps the bound rigorous. The end-adjusted analogue is 23.80 ± 5.16 %.

| quantity (P 60, n = 10) | value |
|---|---|
| best rule at v = 0 (USD, end-adjusted) | 783.50 ± 64.87 |
| ILP at v = 0, upper bound (USD, end-adjusted) | 591.64 ± 23.20 |
| gap at v = 0, lower bound (raw, %) | **23.90 ± 5.15** (min 9.60, 10/10 > 0) |
| gap at v 15 (raw, %) | 27.44 ± 5.64 |
| gap(v 15) - lower bound of gap(v 0), paired (points) | 3.54 ± 1.43 (range 0.63-6.43) |

So at most about 3.5 points, roughly 13 % of the new-price headline, depend on lateness being priced at all.

### 3.5 Bridge (P 30, v 36) against round 5 on the same instances

Table 5. Round 6 bridge versus round-5 X1 (usd4h, eBaaS, x1, relaxed targets, seeds 0-9). Both rounds: Threads 3,
Seed 0, 300 s, all 20 ILPs OPTIMAL (MIP gaps at most 8.4e-5 and 6.1e-5).

| check | result |
|---|---|
| demand hash equal | 10/10 seeds |
| rule end-adjusted totals (r2, M2, M2+M3) | identical, largest difference 0.00 USD |
| best rule | identical on 10/10 (round 5 also looked at the written-target copy; it never won) |
| ILP objective | identical on 9/10; seed 0 +0.045 USD (within the 1e-4 MIP tolerance) |
| ILP end-adjusted total | differences -0.036 to +0.080 USD (alternative optima; round 5 started from the written ILP, round 6 from rules) |
| ILP served share, late orders | identical on 10/10 (0.953; 0.6 late orders per window) |
| gap | round 6 **28.28 ± 7.36 %**, round 5 **28.28 ± 7.36 %**; paired -0.0012 ± 0.0025 points; largest single-seed difference 0.009 |

The bridge reproduces round 5 exactly. So the R6 re-pricing pipeline (repricing, library rebuild, price check) adds no
drift, and every difference between old and new prices in this report is due to prices.

### 3.6 Old to new prices: how much is P and how much is v

This section uses one extra cell outside vsweep: usd4h x1 at (P 30, v 15) from psweep (10/10 OPTIMAL, same
instances). With it, the old-to-new change can be split along both paths. The Shapley value is the average of the two
paths. Per seed, then mean ± 95 % CI, n = 10 (v 36 at P 60 best known).

| quantity (gap points) | value | seeds > 0 |
|---|---|---|
| gap at (P 30, v 15) | 22.48 ± 5.25 % | 10/10 |
| total change, old (P 30, v 36) to new (P 60, v 15) | -0.93 ± 4.86 | 5/10 |
| v effect (v 36 to 15), Shapley | **-5.05 ± 1.86** | 0/10 |
| ... at P 30 / at P 60 | -5.80 ± 2.23 / -4.31 ± 1.53 | 0/10, 0/10 |
| P effect (P 30 to 60), Shapley | **+4.12 ± 3.51** | 7/10 |
| ... at v 36 / at v 15 | +3.38 ± 3.70 / +4.86 ± 3.36 | 8/10, 8/10 |
| same on the 8 optimal seeds: total / v / P | +0.14 ± 6.06 / -4.56 ± 2.22 / +4.70 ± 4.50 | |

## 4. Interpretation

### Shown (by the records)

- **Gap against v at P 60:** the gap increases with v on every seed, by about 2 points per 10 USD/h, from 25.8 % at
  v 8 to at least 31.7 % at v 36. Over this 4.5-fold range of v it stays between 25 and 32 % on average and is
  positive on every instance.
- **Lateness against v:** the ILP's lateness and service hardly respond to v. It has 3-4 late orders per window of
  about 10 min each, no order more than 60 min late, and serves 98.6-99.2 % of orders. The rules do not respond to v
  at all. The rising gap is the price of the rules' fixed lateness (about 3.6 h per window).
- **Bridge:** on the same instances, (P 30, v 36) gives 28.28 ± 7.36 %, identical to round 5 to within 0.01 points
  per seed.
- **Old vs new headline:** the new-price headline (27.34 %) and the old one (28.28 %) are statistically
  indistinguishable (paired -0.93 ± 4.86). Their composition differs: lateness was 50 % of the saving at the old
  prices and is 19 % at the new prices. The unserved penalty rose from 14 % to 58 %, because the ILP now serves
  98.9 % of orders against the best rule's 92.5 %.
- **v = 0 bound:** with no lateness price at all, the gap is at least 23.9 % on average and at least 9.6 % on every
  seed.

### Suggested (not shown)

- **Seeds 5 and 6 at v 36:** the best known values are probably close to optimal. On the 8 optimal seeds the same
  repriced v 25 schedule is optimal or within 3.45 USD, about 0.3 gap points. A re-solve is needed to show it.
- **The ILP's small lateness response:** the drop in ILP late orders from v 8 to v 36 (4.2 to 2.8) points in the
  expected direction but is not significant with n = 10.
- **Beyond this family:** nothing here tests nyc4h, other demand levels or the stressed family. Whether the gap's
  v-slope stays near 2 points per 10 USD/h there is untested.
- **Where the sensitivity now sits:** because the new headline leans on the unserved penalty (58 % of the saving, and
  +4.1 points from doubling P), its sensitivity has moved from v to P. The psweep report is the place to judge that.

### Answer to the question

At P 60, the gap rises steadily with v: 25.8, 27.3, 29.5 and at least 31.7 % at v 8, 15, 25 and 36, about 2 points
per 10 USD/h on every seed.

Lateness is nearly insensitive to v:
- ILP: 2.8-4.2 late orders per window and about 1 min per served order;
- best rule: about 14 late orders and 6.5 min per served order, unchanged by v;
- neither has any order more than 60 min late.

The bridge (P 30, v 36) gives 28.28 ± 7.36 % on the same usd4h x1 instances, exactly the round-5 value.

The headline is not driven by the lateness price:
- lateness is only 19 % of the saving at the new prices;
- removing the lateness price entirely leaves a gap of at least 23.9 % on average;
- moving v from 8 to 36 USD/h shifts the gap by only -1.5 to +4.3 points relative to v 15.

The near-equality of the old and new headlines is, however, partly a coincidence: a 5-point loss from cheaper
lateness is offset by a 4-point gain from the higher unserved penalty.

## 5. Figures

All figures are in `figs/`, as PDF and 300-dpi PNG, made by `figs/vsweep_final.py`.

- `fig1_gap_vs_v` (a) shows the gap against v at P 60: the mean ± 95 % CI, single seeds, the mean over the 8 seeds
  optimal at every v, the bridge (P 30, v 36) and the round-5 value. (b) shows the end-adjusted cost per window of
  the best rule and the ILP against v, with the v = 0 point (rule exact, ILP upper bound).
- `fig2_lateness_vs_v` shows mean lateness per served order, late orders per window and served share against v, for
  the best rule and the ILP, with old prices as hollow markers.
- `fig3_saving_components` shows the saving per window split into the unserved penalty, response time and lateness,
  with the lateness share of the total, at each pricing.

In all three figures, v 36 uses the best known schedule on seeds 5 and 6.

## Appendix. Per-seed gaps (%, end-adjusted; v 36 seeds 5 and 6 best known)

| seed | v 8 | v 15 | v 25 | v 36 | P 30, v 36 (old) | round 5 |
|---|---|---|---|---|---|---|
| 0 | 10.29 | 10.96 | 11.96 | 12.88 | 12.88 | 12.88 |
| 1 | 31.87 | 33.13 | 34.83 | 36.58 | 29.71 | 29.71 |
| 2 | 24.06 | 25.01 | 26.29 | 27.63 | 19.99 | 19.99 |
| 3 | 30.68 | 31.89 | 34.37 | 36.91 | 31.80 | 31.79 |
| 4 | 23.58 | 23.87 | 24.28 | 24.64 | 13.98 | 13.98 |
| 5 | 25.74 | 27.46 | 29.89 | 32.47 (best known; as solved 0.00) | 31.96 | 31.97 |
| 6 | 32.59 | 35.44 | 39.10 | 42.63 (best known; as solved 0.00) | 41.38 | 41.39 |
| 7 | 16.37 | 18.51 | 21.31 | 24.43 | 27.84 | 27.84 |
| 8 | 30.16 | 32.92 | 36.41 | 39.97 | 43.83 | 43.83 |
| 9 | 32.68 | 34.22 | 36.30 | 38.40 | 29.39 | 29.39 |

Reproduce: `python3 outputs/r6_penalty/vsweep/figs/vsweep_final.py`, run from `ebike_swap_sim/`. It is read-only on
the records, needs no solver and runs in a few seconds.
