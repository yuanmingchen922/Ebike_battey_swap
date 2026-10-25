# R7 siting production plan (judge synthesis, 2026-10-21)

Inputs: three candidate plans ("certify", "accelerate", "deliverable") with one critique each; the server probe files
in `ebike_swap_sim/outputs/r7_siting_probe/server/` (re-read for this note); design `notes/siting_scaleup_design.md`
sections 2, 3, 7 and 8; `notes/DECISIONS.md` ("R7 siting scale-up", "R7 decisions of 2026-10-21"). No code was
edited. Step 2b (N = 59, S = 12) is still running (`step2b_setup.log` empty at the time of writing). Every N = 59
number below is therefore an extrapolation from N = 40, and the factors used are stated in section 7.

Prices for us-east-2 were confirmed today with the ec2.shop API (`curl 'ec2.shop?region=us-east-2&filter=...'`).
Vantage lists the same on-demand prices but does not name the region.

| Instance | vCPU / cores | RAM | On-demand USD/h | Spot USD/h (reclaim rate) |
|---|---|---|---|---|
| r7i.4xlarge (current) | 16 / 8 (SMT) | 128 GiB | 1.0584 | 0.374 (>20 %) |
| r7a.4xlarge | 16 / 16 (no SMT) | 128 GiB | 1.2172 | 0.396 (>20 %) |
| r7a.8xlarge | 32 / 32 | 256 GiB | 2.4344 (over the 16-vCPU on-demand quota) | 0.856 (>20 %) |

## 1. Scores

Each plan is scored 1-10 on five criteria. The cost row uses the numbers after the critic's corrections.

| Criterion | certify (N=40, S=10, cell-level B&B) | accelerate (N=59, S=12, full regional B&B) | deliverable (N=59, S=12, certified m=1 + heuristic m=2/3) |
|---|---|---|---|
| Validity of claims | 7: bounds valid; "S_LP = S because L_s is void" is wrong once C1 lands; m=1 pricing understated | 6: bounds valid; F1-F4 speed-ups unmeasured (x2.06 at most, not x2.3); "exact ILP price" wrong at 300 s; m=2 "0.5-2 %" not reachable | 7: bounds valid; misses the window rows (LB_2 weaker by about 12 USD); memory plan does not fit; escalations serial |
| Meets the author's requirements | 5: N=40 is the 40 southernmost ids (lat <= 40.7666, about 59th St) while demand covers the whole band south of 110th; drops 14 DOT sites; meets "40-60" by count only | 8: N=59, S=12, AWS; cost per batch missing | 9: N=59, S=12, AWS, cost stated; per-batch USD only partly given |
| Corrected cost | 7: 48.7 h / 51.5 USD (42-62 h) | 3: about 81 h / 86 USD (74-105 h), plus 25-45 h more if m=2 is to close | 7: 44 h / 47 USD with two extra code changes, 53 h / 56 USD without (44-59 h) |
| Risk | 6: fitted t(n) drives 19.5 h of bb2; ILP gaps at N=40 | 4: memory over the 96 GB guard at level 1; 200-node budget stops with the core open | 6: three memory errors (fixable); m=1 may not close at 1 % |
| What the paper can claim | 6: m=1 certified on a truncated instance; m=2 exclusion map | 6: m=1 certified; m=2 gap 2-4 % after 80+ h | 8: m=1 certified (epsilon) on the full band; m=2/3 gap 5-8.5 %; role table, out-of-sample, measured radius effect |
| **Overall** | **6.2** | **5.4** | **7.4** |

**Base: deliverable.** It is the only plan that meets the author's instance requirements (N = 59 real Manhattan
candidates, S = 12) at about the same cost as certify. Grafts from the other two plans:

- **From certify:**
  - L_s from the all-open free-size LP on all scenarios (C1);
  - batched escalation (C4);
  - explicit `--wall-*` per stage;
  - per-lane time limits;
  - the cell-level exclusion map, as an optional add-on costed at N = 59.
- **From accelerate:**
  - all-open root LPs in separate per-scenario processes, at most 3 concurrent, longest stratum first;
  - a short server calibration before production;
  - weekday-first early exit in the m=1 enumeration (optional, not credited);
  - barrier without crossover tested but not credited, because the laptop showed it negligible.
- **From the critics:**
  - template eviction and the LP lifecycle;
  - master rows that exclude infeasible one-site layouts;
  - a filter for the comparison stage;
  - the no-radius re-pricing of the whole near-tie set;
  - a held-out feasibility check;
  - the probe batches stated in the cost.

## 2. Recommended plan

- **Instance.** N = 59 (`manhattan_dot`, all of `manhattan_s110`, 45 DOT + 14 lattice-only, 12 hub-capable).
- **Scenarios.** S = 12 in-sample (2 seeds x 6 strata), S_LP = 6 for screens, 12 held-out scenarios for out-of-sample.
- **Follower.** Relaxed targets, all-candidates follower, radius 14 with the start-state exemption.
- **Machine.** Current r7i.4xlarge on-demand.
- **Lanes.**
  - LP: 3 workers x 3 threads plus master 2.
  - Pricing: 4 workers x 3 threads.
  - `--max-threads 12`, `--max-rss-gb 110`.
- **Tolerance.** `--tol-rel 0.01 --tol-abs 1`.

Unit times, all from N = 40, S = 6 (`dot_N40_S6/records.jsonl`, `price_probe.json`, `feas_one_site.json`):

| Quantity | N = 40 value | N = 59 assumption |
|---|---|---|
| Fixed one-site LP | 76.5 s | x1.6 |
| Two-site LP | 121.5 s | x1.6 |
| One-cell free LP (9 locations) | 266-387 s | x1.6 |
| All-open free LP | 2,209-4,757 s (sum over 6 scenarios 21,073 s) | x2.6 |
| Pricing cell (300 s cap + library 30.6 s + build 23.4 s) | 354 s | 381 s (overhead x1.5) |
| One-site feasibility check | 25.2 s | 38 s |

### 2.1 Stages (r7i.4xlarge on-demand, 1.0584 USD/h)

| # | Stage | What runs | Unit-cost basis | Hours (central / range) |
|---|---|---|---|---|
| 0 | Step 2b (already running, probe) | sizes, fixed and one-cell LP times at N=59; all-open on 3 S_LP scenarios if it survives the kill at 100 GB | `r7_probe.sh` step 2b, `R7_SIZE_ALL_OPEN_MAX_SCEN=3` | probe, see section 3 |
| P | Calibration (0.7 h) | One 12-cell pricing at N=59 (GIL serialisation of library builds?). One one-cell LP with and without crossover. 8 one-site LPs as 3x3 against 4x2. | Replaces the x1.6 / x2.6 / 381 s assumptions | 0.7 |
| A | One-site feasibility screen | `r7_probe.py feas`, 59 x 12 in-sample in 4 processes x 3 scenarios; plus the 4 out-of-sample layouts on the held-out scenarios | 708 x 38 s / 4 + start-up; held-out +0.3 h | 2.4 (1.7-2.6) |
| B | m=1 LP pass | `certify_by_enumeration(force_lp_per_location)` at the locations feasible in all 12 scenarios (skip list). The transplanted D30 and D38 and the best feasible LP site are priced first for UB_1. | 28 feasible locations (18-35) x 12 x 76.5 s x 1.6 / 2.5 effective workers = 4.8 h; extra size options at competitive locations +2.5 h | 7.3 (3.5-8.6) |
| C | m=1 pricing + escalation (batched) | Price the open set (6-10 layouts, 300 s). Incumbent and runner-up on all 12 scenarios at 900 s; 1,800 s on the 4-8 worst cells. `--wall-m1 6`. | 8 x 12 x 381 / 4 = 2.5 h; 2 x 12 x 981 / 4 = 1.6 h; 6 x 1,881 / 4 = 0.8 h | 5.0 (3.5-7.5) |
| D | All-open root LPs, all 12 scenarios | `ScenarioLP.solve_subset(all ids)`, one process per scenario, 3 concurrent, longest stratum first (weekday 1.5 first); minus the ones step 2b delivers | 2 x 21,073 s x 2.6 / (3 x 0.85) = 11.9 h | 11.9 (9.2-16.0) |
| E | m=2 search | Seeds: D30\|D38, D09\|D38, relax-and-round on the all-open usage, stage-A coverage complements. 16 two-location subset screens on S_LP = 6 (valid pair bounds over all sizes). Price the top 4. | 16 x 2 waves x 270 x 1.15 / 3,600 = 2.5 h + 4 x 0.32 h | 4.0 (4.0-4.8) |
| F | m=3 check | Best pair at B4:C2 sizes; best pair + best third site (2 variants); priced | 3-5 x 0.32 h | 1.3 (1.0-1.6) |
| G | Comparisons (filtered) | CSCD m=1-3, CSAV m=2, DOT all-pilot, DOT pilot proxy m=2. The m=2 rows at 600 s. DOT-only restricted master + up to 2 pricings. | 6 x 0.32 h + 3 x (681-381) x 12 / 4 / 3,600 + 0.7 h | 3.3 (2.6-4.0) |
| H | Role table at m=2 | SC+SC, SC+S, hub+S. Hub screen: 12 x 3-location subset LPs on 3 scenarios; 2 hub layouts at the 600 s hub limit | 1.2 + 0.3 + 1.14 h | 2.7 |
| I | Out-of-sample | 4 layouts (best m=1, best m=2, CSCD m=2, DOT all-pilot) x 12 held-out scenarios | 48 x 381 / 4 + templates | 1.5 |
| R | No-radius re-pricing | Every m=1 layout within 3 % of UB_1 (assumed 4), the best m=2 and the best m=3; radius unset; 3 workers with template eviction | 72 cells x about 450 s / 3 + templates 0.3 h | 3.3 (2.6-4.5) |
| J | Process start-ups | 6 invocations x (templates + LP build + Ctx init) | about 0.33 h each | 2.0 |
| | Subtotal | | | 45.4 |
| | Overhead 10 % (master solves, I/O, one restart, watchdog gaps) | | | 4.5 |
| | **Total production** | | | **49.9 h = 52.8 USD** (40.4 h / 42.7 USD to 64.2 h / 67.9 USD) |

Analysis (tables, map, RESULTS) runs on the laptop: 0 server hours.

### 2.2 Batches (each invocation is one batch for the cost report)

| Batch | Stages | Hours incl. start-up and 10 % | USD on r7i.4xlarge OD | Memory plan (123 GB, guard 110) |
|---|---|---|---|---|
| 1 | P + A | 3.8 | 4.0 | A: 4 processes x about 26 GB; `keep_libraries 1` |
| 2 | B + C | 13.9 | 14.7 | B: 12 LPs + templates about 85 GB, then templates evicted after the LP build; LPs disposed before the pricing pass (C: templates + 4 ILPs about 75 GB) |
| 3 | D | 13.5 | 14.3 | 3 per-scenario processes x (template 4.6 + LP 2.5 + factor about 17 GB) = about 72 GB |
| 4 | E + F + H | 9.2 | 9.7 | 6 S_LP LPs resident (about 15 GB) + templates; pricing as in C |
| 5 | G + I | 5.6 | 5.9 | pricing only; no LPs built |
| 6 | R | 4.0 | 4.2 | no-radius templates x1.9: evict per scenario batch of 4 |
| | **Total** | **49.9** | **52.8** | |

On top of production:

| Item | Hours | USD |
|---|---|---|
| Today's probe batches (13:42-21:06 UTC uptime) | about 7.4 | about 7.8 |
| Step 2b | about 4-6 | about 4-6.5 |
| EBS gp3, all month | | 0.08 USD/GB-month x volume size |
| **Study total, central** | | **about 66 USD + EBS** |

This exceeds the 50 USD/month line, which the author has allowed for this study. It must be reported as such.

### 2.3 Optional add-ons (not in the total)

| Add-on | Gain | Hours | USD |
|---|---|---|---|
| m=2 cell-level exclusion map (certify's bb2 at N=59): 15 cells, 116 nodes (7 multi-location cells + 105 pairs, largest 18 locations); two-stage S_LP=6, then all 12 for survivors | "The optimal pair lies in the listed 2-km cell pairs" + LB_2 up 1-3 points | about 49 (37.5k LP-s per scenario at N=40 sizes x1.2, 6 scen / 2.5 workers = 30 h, + 30 % completion 14 h, +10 %) | about 52 |
| Comparison m=2 rows at 900 s instead of 600 s | fewer inconclusive regret intervals | +1.3 | +1.4 |
| Written-target sensitivity, compliance, fleet 12-bike, hub economics, CSTC, m=4 | dropped (design 3.3 cut order) | | |

### 2.4 On the r7a.4xlarge (if the author switches)

The switch is the same EBS volume and the same 16-vCPU quota, with a console stop/start (new public IP). The speed-up
is not measured. The LP stages (B, D, the screens in E and H, 22.9 h) would gain from 16 physical cores; pricing stays
memory-bound at 4 workers.

| Assumed speed-up (LP / other) | Hours | USD |
|---|---|---|
| 1.3 / 1.1 | 41.9 | 51.0 |
| 1.5 / 1.15 | 38.3 | 46.6 |
| 1.6 / 1.2 | 36.4 | 44.3 |

Break-even is 1.15x. The case for switching is 8-13 h less wall-clock, at the same or slightly lower cost. Gate: stage
P run on the r7a; stay on it only if one-site LPs are at least 1.3x faster than on r7i.

Spot is not recommended: the reclaim rate is >20 % on both types, and a single N=59 all-open LP takes 1.6-3.5 h.

## 3. Certificates and what the paper can claim

**Scope of every claim:** N = 59 candidates in Manhattan south of 110th St, the 12-scenario stratified SAA (in
sample), relaxed targets, 8 bikes, and the all-candidates follower with the 14-block approach radius and start-state
exemption. The radius is applied identically to the LP template and the pricing ILPs.

- **m = 1: epsilon-optimal by pruned enumeration.**
  - Every one-site layout falls in one of three groups:
    - proven terminal-infeasible (stage A library check; V = infinity, independent of size, by toy test);
    - pruned by its 12-scenario LP cut against UB_1 - tol;
    - priced.
  - epsilon = max(1 %, the incumbent's achieved weighted MIP gap after escalation). Expected 1-1.5 %: D38 was at 1.6 % after 300 s at node 1, and M09 at 1.4 % after 900 s on 15 candidates.
  - The near-tie set (all sites within epsilon) is published with the map.
- **m = 2: incumbent + valid lower bound.**
  - LB_2 = min(LB_1, setup_min(2) + sum_s p_s L_s plus the cut pool, from the final master). It uses the window rows that exclude one-site layouts at infeasible locations.
  - Expected gap 5-8.5 %. At N=40: sum p L = 669.7, setup about 25, the D30|D38 LP 725.0, and the ILP about 731-737.
  - The 16 screened pairs carry their own valid pair bounds over all size combinations.
- **m = 3:** incumbent + the same kind of bound. "A third site does not pay at 8 bikes" is stated only as "no layout found", not proved.
- **Comparisons:** paired differences with stratified and plain CIs (6 and 11 df) and regret intervals [V_rule - UB, V_rule - LB]. Single-site rule or pilot layouts that are infeasible alone are reported as "infeasible alone" (for example D12, and D38 = M09 in scenario 4).
- **Role table:** the price of separating a charging hub from swapping, against co-located SC. Hubs are allowed only at the 12 hub-capable sites.
- **Out of sample:** V_out - V_in for 4 layouts on 12 held-out scenarios.
- **Radius effect:** measured, from stage R, on every headline layout (section 4).

**Cannot claim:**
- a certified two- or three-site optimum;
- optimality without the radius (only the measured effect on the re-priced layouts);
- written-target, compliance or fleet results.

## 4. Radius decision

**Keep 14 blocks with the start-state exemption as part of the model definition.** This is an explicit author override
of the pre-registered verdict "raise" (radius.json: one-site M09 +2.42 to +2.87 %, +6.7 % in scenario 1; pairs +0.31
to +1.39 %; threshold 1 %), and it must be recorded in DECISIONS.

Reasons:
- It is an arc-library restriction applied identically to the LP template and every pricing ILP, so every bound is valid for the restricted model.
- Feasibility does not depend on it (19/45 infeasible on the 15-candidate family, with and without the radius).
- Radius 20 is unmeasured at N = 59. Laptop library builds at N = 40 give x1.22 arcs, about x1.19 LP time, roughly +6-8 h. Nothing shows that 20 brings the effect under 1 %.

Conditions:
- Stage R re-prices the whole m=1 near-tie set (within 3 % of UB_1) and the m=2 and m=3 incumbents without the radius.
- If R changes the m=1 order, the paper calls the m=1 ranking library-conditional.
- The paper states the bias across budgets: one-site values are raised about 1-2.5 points more than two-site values.

## 5. Code changes before production (ordered; laptop, Threads 1)

1. **Root bound L_s (required; every other graft depends on it).**
   - Compute L_s = max(0, safe Qs of `ScenarioLP.solve_subset(all ids)`) for all 12 scenarios.
   - Run one process per scenario, at most 3 concurrent, longest stratum first. Store the results in `bound.json`.
   - On restore, set `SitingCertifier.L[s] = max(L[s], all-open value)`.
   - Skip the per-bike `superset_bound` in production: it returned 0 (LP_TIME_LIMIT) in all 6 N=40 scenarios at 600 s.
   - Test: the existing `all_open_equals_superset`.
2. **Memory lifecycle (required).**
   - Build ScenarioLP objects lazily.
   - Evict `LowerLevelEvaluator._templates` per scenario where the stage no longer needs them.
   - Dispose of the LPs between enumeration pass 1 (LPs) and pass 2 (pricing).
   - Pricing-only stages (comparison, oos, R) never build LPs.
   - Check: peak RSS in each batch under the 110 GB guard (section 2.2).
3. **Batched escalation (required).** `SitingCertifier.escalate` re-prices all open scenarios of a layout in one `price_layout_parallel` wave (today one scenario per call: 8.6 h serial against 2.4 h). Raise `--max-escalations`.
4. **Feasibility skip list and window rows (required).**
   - The enumeration reads the stage-A JSON. A location with a terminal-infeasible bike in any scenario gets INFEASIBLE_TERMINAL (V = infinity) for all its size options, without an LP.
   - The master gets y_l <= sum_{l' != l} y_l' for those locations, so the m=2 window bound uses the two-site setup.
   - Toy test: terminal feasibility of a one-site layout does not depend on (B, C).
5. **Comparison filter (required).** `--comparison-rules` and `--comparison-budgets` for `stage_comparison`; a per-row time limit for the m=2 rows (600 s).
6. **New driver `experiments/r7_search.py` (required; no change to the core modules).**
   - m=2 seeds and 1-swap pair screens via `cert.subset_bound([a, b], S_LP)`, memoised in `cuts.jsonl`;
   - m=3 additions;
   - role-table hub screen and pricing;
   - a list-pricing entry point, including an evaluator with the radius unset (stage R);
   - the out-of-sample layout list (4 layouts).
7. **Cost per batch (required by the author).** Every invocation appends {batch, stages, wall_h, instance, USD/h, USD} to `cost.jsonl`; RESULTS sums it.
8. **Weekday-first early exit in pass 1 (optional, not credited).**
   - Prune a location after the weekday wave only if its safe partial bound, with the other scenarios at L_s, is at least UB_1 - tol.
   - Never prune because the LP has artificial > 0 at the representative option.
9. **LP method `barrier-nox` (optional, not credited).** Crossover 0 is valid through `cut_from_pi`. Keep it only if stage P shows at least 15 % saving at N=59.
10. **Gate before upload.** pytest green, and the `R7_REPRO` reproduction (149 keys, bounds unchanged) green on the laptop. Rebuild `r7_code.zip`. The `STALE CODE` markers must cover changes 1-7.

Only if the exclusion-map add-on is chosen: certify's C2, C3, C5 and C8:
- per-pass `--bnb-levels`;
- an incomplete level 0 enters at the root bound;
- `--bnb-max-level`;
- two-stage S_LP completion.

Wall flags per invocation:

| Flag | Hours |
|---|---|
| `--wall-m1` | 13 (B + C) |
| `--wall-setup` | 13 (D) |
| `--wall-comparison` | 4 |
| `--wall-oos` | 2 |

Each new driver stage takes its own `--wall`.

## 6. Decisions for the author (recommended default in bold)

1. **Candidate set.** **N = 59 (full band south of 110th St)**. Do not use `--reduced 40`: it is the 40 southernmost ids with demand from the whole band. A spatially balanced 40 is possible but saves little once the B&B is dropped.
2. **Scenarios.** **S = 12 in-sample + 12 held-out for 4 layouts.** S = 10 saves about 15 % on scenario-proportional stages, but it folds the weekend levels into one stratum.
3. **Radius.** **Keep 14 + start-state exemption, with the stage R re-pricing** (an override of "raise", recorded in DECISIONS). The alternative is 20 blocks: unmeasured, about +6-8 h, and a new size probe.
4. **m=1 tolerance.** **1 %, with the near-tie set published.** 0.25 % only if the escalations close; otherwise report the achieved epsilon.
5. **m=2 claim.** **Incumbent + trivial-plus-pool bound (gap 5-8.5 %) + screened pair bounds.** The add-on is the cell-level exclusion map: about 49 h and 52 USD more. Decide after batch 4 shows the gap.
6. **Instance.** **Stay on the r7i.4xlarge on-demand** (every unit time measured there). Alternative: r7a.4xlarge after stage P calibration, for 8-13 h less wall-clock at about the same cost. No Spot.
7. **Budget.** **Approve about 53 USD for production (range 43-68) + about 13 USD of probes + EBS**, i.e. about 66 USD for the study, over the 50 USD/month line.
8. **Step 2b.** **Let it run.** The driver kills it cleanly at 100 GB, and any all-open bounds it finishes are reused (config_md5 does not depend on the time limit). Stop it by hand if it is still in the all-open wave 6 h after start.
9. **Comparison set.** **CSCD m=1-3, CSAV m=2, DOT all-pilot, DOT pilot proxy m=2, DOT-only restricted.** Dropped: CSTC, written targets, compliance, fleet 12, hub economics, MRP, m=4.
10. **Code changes.** **Approve changes 1-7 and 10** (laptop tests first); 8-9 optional.

## 7. Assumptions to update when step 2b (N = 59, S = 12) finishes

| Assumption | Value used | Source of the value | Replace with (from step 2b records) | Affects |
|---|---|---|---|---|
| Fixed-layout LP factor N=59 / N=40 | x1.6 (1.4-1.8) | arcs^0.84 gives 1.40; columns^1.76 gives 1.8 | `sizes.timings.one_site` / `two_site` runtimes vs 76.5 / 121.5 s | B, E, H screens |
| All-open LP factor | x2.6 (2.0-3.5) | (59/40)^1.62 x 1.40 | `subset_lp` all_open runtimes (if it survives) | D (11.9 h) |
| Subset-LP location exponent | 1.6 above 9 locations | 314 s at 9 vs 3,512 s at 40 | one-cell LP at N=59 (fixed template, different cell) | E, H, add-on |
| Template arcs and build | x1.5, about 50 s | 0.281 M arcs per candidate | `sizes.templates` n_arcs, build_s | A, J, R |
| Memory per scenario (template + LP) | 4.6 + 2.5 GB | 28.6 GB / 6 at N=40 x1.5 | `rss_gb_after_lps`, peak RSS, kill point | batches 2-4, 6 lane counts |
| Pricing cell | 381 s at 300 s cap | 354 s x overhead 1.5 | stage P pricing at N=59 | C, E-I, R |
| One-site feasible locations at S=12 | 28 (18-35) | 24/40 feasible on 3 weekday scenarios | stage A count (not step 2b) | B, C |
| m=1 ILP gap at 900 / 1,800 s | 1-1.5 % | 1.6 % at 300 s (N=40), 1.4 % at 900 s (N=15) | stage C escalation records | epsilon, C hours |
| Effective LP workers | 2.5 (3 x 0.83) | measured wave utilisation 0.78-0.88 | stage P 3x3 vs 4x2 | B, D, E, H |
| Number of L_s still to compute in D | 12 | 2b likely killed before all-open | 12 minus the all-open records in 2b `cuts.jsonl` | D (-1 h per delivered scenario) |

When step 2b reports, recompute the stage table with `hours = basis x new factor`, update the totals in sections 2.1
and 2.2, and re-check the memory plan of each batch before batch 2 starts.

## 8. Production code status (2026-10-21)

Details and decisions: `notes/DECISIONS.md`, "R7 production code (2026-10-21)" (core lane, drivers lane, fixer
pass, gate). No E2 equation and no bound rule changed (safe Lagrangian cuts, relaxed-only subset bounds,
budget-window rule, S_LP rule, two tiers). Every new switch is `auto` = on for `manhattan_dot` only, so the toy and
`r5_manhattan` keep their cache keys, pruning and pool signature.

**Implemented** (section 5):

| # | Change | Where | Status |
|---|---|---|---|
| 1 | Root bound L_s: stage `rootlp`, one process per scenario, `root_lp/root_sNN.json`, merge on load, `--root-import` of the step-2b pool, `--superset off` | `experiments/r7_siting.py` | done |
| 2 | Memory lifecycle: lazy `ScenarioLPSet`, `evict_template`, `release_library`, LPs disposed before pricing, pricing-only stages | `benders.py`, `bilevel.py`, `r7_siting.py` | done |
| 3 | Batched escalation, `--max-escalations` 3, level->=2 cap `--escalate-batch-max` | `benders.py` | done |
| 4 | Stage `feas` (stage A), skip list with re-proof, terminal master rows (stronger than the plan's literal row) | `benders.py`, `r7_siting.py` | done |
| 5 | Comparison filter, per-row limits (`2:600`), prior-LB restore | `r7_siting.py` | done |
| 6 | `experiments/r7_search.py`: calib, pairs, m3, roles, oos-feas, oos, noradius, price-list, report, `--write-lanes` | `r7_search.py` | done |
| 7 | `cost.jsonl` per invocation (start / end rows, killed lanes), cost table in RESULTS / SEARCH | `r7_cost.py` | done |
| 8 | Weekday-first early exit in pass 1 | | not done (optional, not credited) |
| 9 | LP method `barrier-nox` | | not done; stage P only times `Crossover 0` |
| 10 | Gate: `r7_gate.py` (lane `b0_gate`, 17 markers) and `deploy/aws/r7_prod_check.sh` (42 markers over changes 1-7, the fixer pass and the tests; lane plan; probe precondition) | `experiments/`, `deploy/aws/` | done |

**Laptop gate of 2026-10-21** (nice -n 15, Gurobi Threads 1; no ssh, nothing uploaded):

* Full suite `python3 -m pytest -q tests/`: 453 passed, 7 skipped, 0 failed (12.1 min; the skips are the six r6_fill smokes and the opt-in reproduction).
* `R7_REPRO=1 pytest tests/test_r7_siting.py -k reproduced`: 1 passed (149 cache keys of `r6_o2/manhattan_pass2`,
  both targets; 56 s). Pool signature through the r7 path: `ed744dafc64e8f7e7384606bc0fd5c42` (relaxed and written).
* Lane plan re-written to a scratch folder with `r7_search.py --write-lanes`: identical to
  `outputs/cloud_lanes_siting_prod/lanes.txt` / `.json` (27 lanes, 6 batches, about 50.0 h = 52.9 USD).
  `run_lanes.sh start ... --dry-run` accepts the whole file and each batch selection below.
* `outputs/r7_siting_probe/upload/r7_code.zip` rebuilt (md5 `908abb1bd27a8226f1d112a4220a9a7b`, 1.19 MB): 103 files (code, tests, `deploy/aws` without
  `aws_env*.sh` and `README_AWS.md`, `data/raw/dot_candidate_sites.csv`, the lane plan). Every entry is
  byte-identical to the tree (md5), no licence / key / `.pyc`, 0 files with CJK characters.
  `r7_prod_check.sh --root <unzipped> --no-probe`: 42 / 42 markers, exit 0; with one marker removed: exit 2; with a
  `probe.log` that does not end with "probe done": exit 3. `r7_gate.py` on the unzipped tree: 17 / 17.

**Open items**

* Step 2b (N = 59, S = 12) has not reported: section 7 assumptions are still N = 40 extrapolations. Re-cost
  sections 2.1 / 2.2 and re-check each batch's memory plan before batch 2 (the lane `--wall-*` values come from
  the current table).
* Unpack the zip on the server only after the probe has finished ("probe done" in `probe.log`): it replaces
  `deploy/aws/r7_probe.sh` and the package that the probe's later step-2b sub-steps import.
* Stage P (batch 1) decides the r7a switch (one-site LPs >= 1.3x faster) and `Crossover 0` (>= 15 % saving); both
  need a code / plan change only if they pass.
* Batch order: m1 (batch 2) runs before the all-open root LPs (batch 3), as in plan 2.2. m1 is certified by
  pruned enumeration and does not need L_s; LB_2 and the pair bounds of batch 4 do.
* Decision 5 (exclusion-map add-on, about 49 h / 52 USD) waits for the m = 2 gap of batch 4.
* Upload is the author's step (`deploy/aws/sync_up.sh --code-only`, or `r7_code.zip`); nothing was uploaded.

**Commands on the server** (project root `~/battery_swap`; each batch after the previous one shows `done` in
`status` and its dispatcher has exited; `--dry-run` first is recommended):

```bash
cd ~/battery_swap
unzip -o r7_code.zip                     # only after 'probe done'; r7_code.zip copied to ~/battery_swap
bash deploy/aws/r7_prod_check.sh         # exit 0 required (2 = stale code / lane plan, 3 = probe still running)
export LANES_DIR=$PWD/ebike_swap_sim/outputs/cloud_lanes_siting_prod
LF=ebike_swap_sim/outputs/cloud_lanes_siting_prod/lanes.txt

# batch 1 (P + A, about 3.8 h = 4.0 USD)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b0_gate,b1_calib,b1_feas_1,b1_feas_2,b1_feas_3,b1_feas_4,b1_oos_feas
# batch 2 (B + C, about 13.9 h = 14.7 USD)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b2_m1
# batch 3 (D, about 13.5 h = 14.3 USD; s04 imports the step-2b pool)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b3_rootlp_s04,b3_rootlp_s05,b3_rootlp_s10,b3_rootlp_s11,b3_rootlp_s02,b3_rootlp_s03,b3_rootlp_s08,b3_rootlp_s09,b3_rootlp_s00,b3_rootlp_s01,b3_rootlp_s06,b3_rootlp_s07
# batch 4 (E + F + H, about 9.2 h = 9.7 USD)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b4_pairs,b4_m3,b4_roles
# batch 5 (G + I, about 5.6 h = 5.9 USD)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b5_comparison,b5_restricted,b5_oos
# batch 6 (R, about 4.0 h = 4.2 USD)
bash deploy/aws/run_lanes.sh start $LF --max-threads 12 --only b6_noradius

# all six batches unattended (chained by 'after') instead of one by one:
bash deploy/aws/run_lanes.sh start $LF --max-threads 12
# watch / stop / cost
bash deploy/aws/run_lanes.sh status $LF
bash deploy/aws/run_lanes.sh stop all
cd ebike_swap_sim && python3 experiments/r7_cost.py outputs/r7_siting
```

Analysis on the laptop after `deploy/aws/sync_down.sh`: `r7_siting.py --stage analyse` and `r7_search.py --stage
report` with the lane flags (no cost row).
