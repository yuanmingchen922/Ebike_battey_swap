## Headline comparison and interpretation

**Headline = ILP vs ILP** (layout x transfer switch, same instances, same end targets (17)-(18)).
The baseline rows are context only: on every separated run and on co-located seed 1 the baseline
violates (17) (swap sites end without a full spare) and (18), so its point is infeasible for the model,
its MIP start is rejected, and "baseline gap" mixes policy quality with an infeasibility.

| quantity (3-seed mean, toy units) | (a) co-located | (b) 1 hub | (c) 2 hubs |
|---|---|---|---|
| ILP total, transfers free | 556.05 | 611.47 | 653.95 |
| ILP total, h = z = 0 | 556.05 | 868.43 | 908.43 |
| value of transfers = cost(h = z = 0) - cost(free) | **0.0** (seeds 0/0/0) | **257.0** (301.3 / 95.0 / 374.6) | **254.5** (297.6 / 93.5 / 372.3) |
| cost of separation vs (a), transfers free | - | +55.4 (= 40 setup (27) + 15.4 operations) | +97.9 (= 80 setup + 17.9 operations) |
| operational cost (total - C_setup), transfers free | 451.05 | 466.47 (+3.4 %) | 468.95 (+4.0 %) |
| served share, transfers free / h = z = 0 | 0.978 / 0.978 | 0.978 / 0.878 | 0.978 / 0.878 |
| transfers used / batteries moved (free) | 0 / 0 | 2.3 / 5.7 | 3.0 / 5.7 |
| grid-group peak kW (limit 8, 6 in peak) | 1.78 | 1.56 | 1.56 |
| baseline NONE / REORDER_POINT total | 1085.8 / 1091.2 | 1324.5 / 1209.8 | 1364.5 / 1143.9 |

1. **Co-location dominates at equal totals.** With 9 spares, 9 chargers and the same 8/6 kW grid
   group in every layout, the co-located layout is cheapest on every seed; one hub costs +55 (+10 %
   of total, +3.4 % of operational cost) and two hubs +98. Net of the horizon-allocated hub cost
   (27) the separation penalty is only 11-22 units per seed, which is essentially the shuttle fixed
   charges f_e = 5 per used service plus v_reb (C_reb = 11.0-21.8); travel, response and lateness
   are within a few units of (a). The separation penalty is certified: the 1-hub bounds
   (obj * (1 - gap) = 534.3 / 621.6 / 668.0) exceed the co-located optimum on every seed.
2. **Transfers are worth nothing when sites can charge, and everything when they cannot.** In (a)
   the site <-> site shuttles are offered on every seed and never used (identical objectives, 0
   transfers). In (b)/(c) the switch h = z = 0 loses 3-6 orders per seed (unserved 300-600 at
   P_i = 100): with no chargers at the swap sites the six site spares (2 + 2 + 2) are the only
   swap supply, and (17) R_end_j = 1 freezes one of them per site, so at most 3 swaps are possible
   (n_swaps = 3 on every h = z = 0 run). Transfers restore service to exactly the co-located served
   share on every seed (0.978 both) with 2-4 services and 3-9 batteries moved.
3. **Caveat: in this 2 h window the value of transfers is a recovery-target effect, not a
   replenishment effect.** The side run `relaxed_end_targets/` (seed 0, R_end = 0, rho = 0) gives
   co-located 481.50 and separated-1-hub 525.25 with zero transfers, zero charging and all 30
   orders served; 525.25 - 481.50 = 43.75 = 40 hub setup + 3.75 extra travel. With the end targets
   on, (b) needs transfers (539.44, 2 services, 5 batteries) purely to end with one full spare at
   each swap-only site and >= rho * 9 = 5 full batteries in the network. The plan's expectation that
   "the ILP times shipments right before predicted stock-outs" holds in the trajectories
   (seed 0, (b): S3 hits n_jLt = 0 at t = 4 and the 3-battery shipment lands at t = 6; see
   `fig_full_stock_seed0.png`), but the within-horizon stock-out itself is avoidable without
   transfers once the end targets are dropped. A 4 h horizon (plan: H = 48, |I| = 40) is needed to
   see replenishment value; at H = 36 / 45 orders the probe solved co-located in 160-195 s per run
   and the separated layouts did not finish in 300 s, outside the 45 min budget.
4. **The grid-group limit never binds.** Peak charging load is 0.67-2.67 kW against 6-8 kW. With
   p_ch = eps / (eta Delta) = 0.667 kW per charger (L = 12) a battery needs up to 12 slots = 60 min
   to refill, few batteries return within 2 h, and the 9 hub chargers never have more than 4
   batteries to charge, so the plan's expected "limit binds at the hub during the peak, shifting
   charging earlier" does not occur at this size (the hub charges only after t = 13).
5. **Baseline.** The baseline-vs-ILP gap (66-133 % of the ILP cost) is almost entirely P_i: on (a)
   the mean difference 529.7 decomposes into unserved +533.3, response -30.7, lateness +24.0,
   electricity +5.4, travel -2.3; on (b) with REORDER_POINT the difference 598.3 is unserved +600,
   C_reb +15.9, response -37.3, lateness +22.7. REORDER_POINT helps the separated layouts on seeds
   0-1 (1-2 fewer unserved, -115 to -220) but uses 4-8 services and 9-13 batteries where the ILP
   uses 2-4 and 3-9, and on seed 2 it is worse than NONE on (b) (+24.5: same unserved count, extra
   C_reb). The baseline MIP start is accepted only on co-located seeds 0 and 2 (reported families
   {}); elsewhere it reports (17)/(18) and is rejected, as expected. A rho = 0 / R_end = 0
   comparison on seed 0 (`relaxed_end_targets/`) accepts the start on both layouts and leaves the
   gap at 67 % (a) and 87 % (b, REORDER_POINT), so the inflation by (17)/(18) is small: the
   baseline's loss is dispatch/threshold quality, i.e. unserved orders.
6. **Solver.** 1.43-1.79 M binaries, 80-88 k rows. Co-located and all h = z = 0 runs solve to
   optimality in 14-67 s; the separated runs with transfers are the hard ones: 5 of 6 hit the 200 s
   limit at gaps 0.37-0.97 % (the sixth, (b) seed 2, is optimal in 157 s). Those gaps (<= 6 units)
   are below every reported difference except the per-seed operational separation penalty on
   seed 1 (11 units, still above the 5.4-unit gap). Wall time 29.3 min for the 36 runs plus ~4 min
   for the side check, single process, Threads = 4, while two other experiments shared the machine.

**Instance choice.** The generator defaults (12 spares, q0 ~ U{0.4L..L}) were probed first and are
degenerate for this question: 12 initially full spares cover every swap of a 2 h window, the ILP
never charges or transfers, and the layouts differ only by (27) (+40 per hub). The family used is
`large` (10 bikes, 30 orders, H = 24, L = 12, Delta = 5 min) with 9 spares (3+3+3 / 2+2+2 + hub 3 /
2+2+2 + hubs 2+1), 9 chargers (3+3+3 / hub 9 / hubs 5+4), q0 ~ U{4..7}, seeds 0-2; the H = 36 /
45-order variant was too slow (above). All 36 schedules pass `evaluate.check` with zero violations
(ILP) or only the report-only families (baseline), identity (24) holds everywhere, and
`obj == cost` for every ILP run.
