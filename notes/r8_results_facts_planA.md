# R8 fifteen-site study, plan A (all sites share one 2 kW supply): facts sheet for the paper (2026-10-30)

Purpose: every number the paper writer needs to explain the 15-site result, each traced to a file (section 7).
Runs read (downloaded, checksummed, server stopped): RUN = `cloud_results/ebike_swap_sim/outputs/r8_k15_n64/`
(64 riders), RUN48 = `cloud_results/ebike_swap_sim/outputs/r8_k15/` (48-rider dry run and the exact-ILP check).
Derived numbers come from `notes/verify/r8_facts.py` (read-only, about 10 s on the laptop; section labels [A]-[L]
below), which imports the paper's own map helpers from `paper_itsc/figs/src/make_figs.py` (version of 2026-10-30
15:02, the one with the fixed Roosevelt Island mask and the curated site names `SITE15`). Nothing in `paper_itsc` was
edited.

Conventions. USD per day = one 16:00-20:00 evening, allocated set-up included (13.19 USD/day per standard site).
In-sample = the 12 evenings of the final table; held-out = 12 other evenings; the search used 6 of the 12
(seeds 0, 2, 4, 6, 8, 10). "+-" = half-width of the stratified 95 % CI (paper eq. (35)); regrets are paired.
Areas: S14 = south of 14th St, 14-59 = 14th to 59th St, N59 = north of 59th St, split at the 14th and 59th St guide
lines of the map (rotated along-avenue coordinate of `make_figs.rot`). "Grid km" = distance along the street grid,
as the map computes it. Paper equation numbers are those of the compiled `paper_itsc/main.aux`.

---

## 0. Check of the lead facts

| # | lead fact | verdict | evidence |
|---|---|---|---|
| 0.1 | lower level = rule-based rider module, r2; take next reachable order; swap below a quarter at the nearest open site with a charged battery; charge ahead of expected demand; no transfers | agree, with three precisions | (a) the swap trigger is "at or below 6 of 24 levels", and also earlier when a rider is too low to take the next order and still reach a site afterwards: 34.4 % of the swaps happen at 7-12 levels [D]; (b) "charge ahead of demand" = each site charges as many batteries as the swaps it saw in the last hour suggest, minus its charged stock, and the shared 2 kW is handed out to the sites **in the order of their site numbers** (`baseline.py` `_step9_charging`: "allocated in facility order"; facilities are id-sorted by `sites_nyc.layout_items`); (c) see 0.2 |
| 0.2 | every schedule is checked against the same constraints and costed with the same cost function | agree on "checked", but not every check passes | the end-of-evening rule (paper (9)-(10): a rider's path ends with a terminal arc at an open site, with a reserve) is only reported for the rule module: in 23 of the 24 best-layout evenings 1-6 riders (2.93 per evening, in-sample) end without it, and 1,596 of the 2,027 checked evenings of the run have at least one [J]; no cost is charged for it (`C_dummy_terminal` = 0). Write "checked against the same constraints; the end-of-evening condition is reported, not enforced", not "feasible" |
| 0.3 | exact integer program cannot be solved at this size | agree | 94 % gap after 240 s already at 8 riders / 80 orders / 15 sites (design note section 2); at 64 riders the union arc network has 266-680 million (virtual) arcs per evening (RUN `dryrun.json` `n_arcs`) |
| 0.4 | fleet 64 riders, 320 orders on average, 12 + 12 evenings, search on 6 | agree | orders 256 / 320 / 384 (1.0 / 1.25 / 1.5 per rider-hour x 64 x 4 h; weekday weight 5/7, weekend 2/7; mean 320); riders are dealt round-robin to the six entry points: 11 each at Queensboro, Williamsburg, Manhattan and Brooklyn Bridges, 10 each at the Lincoln and Holland Tunnels (`data_nyc.py` line 1303 `depots[k % len(depots)]`) |
| 0.5 | 48 riders first: coverage-rule median site 2.5 swaps < 3, so 64 riders, where it is 3.0 | agree | RUN48 `dryrun.json`: median 2.5, gate 3.0, escalate true; RUN `dryrun.json`: median 3.0 (exactly at the gate). Trap: RUN `dryrun.json` and RESULTS.md say "recommendation: go: 48 riders / 240 orders"; that text is hard-coded in `experiments/r8_k15.py` line 910; the run is 64 riders / 320 orders (`layout.json` `n_bikes` 64, `n_orders` 320; cost.jsonl argv `--n-bikes 64`). Never copy it |
| 0.6 | budget 15 standard units, 52,150 USD each, 782,250 USD; polish 4 spares at D05, D07, D11, 2 at D40, D54, D58; saves 389.1 +- 271.8 | agree | the polish keeps the 45 spares and 30 chargers (investment unchanged, 782,250 USD) and gives spares in proportion to swaps; D40, D54, D58 had the fewest swaps at 3 spares (2.71, 2.90, 2.90 on the search evenings); three one-for-one spare moves tried afterwards (D12 to D55, D49, D46) were all worse (`search_summary.json` `polish_log`). Held-out gain 416.6 +- 155.7 |
| 0.7 | best 11,210.5 [10,338.1, 12,082.9], 72.9 % served; held-out 11,464.7 | agree | held-out CI [10,923.7, 12,005.6], served 70.3 % |
| 0.8 | site list "south to north roughly" | order differs at 12-14 | the map numbers sites by the along-avenue coordinate: ... 11 D46, **12 D49, 13 D54, 14 D55**, 15 D58 (lead had D54, D55, D49) [A] |
| 0.9 | site descriptions | agree, with details | D05 is a Worker's Justice Project "Deliverista Hub" on a Parks site with 2 Swobbee cabinets, unveiled 2026-04-07, running from about June 2026; it is not a DOT pilot or PEC site. D30's "2,329 restaurants" is the count of its 2 km grid square; within 1 km (grid) it has 1,554. Grid cells sit at: D07 6th Ave near Bleecker St, D30 5th Ave & W 31st St, D38 3rd Ave & E 53rd St, D49 Amsterdam Ave & W 80th St, D54 2nd Ave near E 83rd St [L] |
| 0.10 | comparisons (in-sample regret, served) | agree; all exclude zero in-sample and held-out | DOT-first: all 15 of its sites are DOT pilot or PEC sites (20 such candidates exist), so the "filled by demand" step never applied at 15 |
| 0.11 | cost versus sites (greedy path) | numbers agree; "greedy path" is not one path | k = 1 is the first pick of the search started from nothing (D30); k = 2-14 come from the search started at the earlier best pair D07 + D45; k = 15 is the best layout's sites with 3 spares each; k = 16-20 extend those sites (`experiments/r8_k15.py` lines 1191-1208). At k = 10 another start reached 13,402.1 on the search evenings vs 13,713.7 for the plotted one, so the curve is a search path, not the best cost per k. D23 (18,182.6) and D30 (18,280.8) are a tie at k = 1: -98.3 +- 188.3 [H] |
| 0.12 | shared power: one 2 kW group, "constraint (21)" | number differs | in the paper the feeder row is **(16)**, `\eqref{eq:feeder}`; (21) is the code's E2 number and in the paper (21) is the order price (`main.aux`) |
| 0.13 | charging adds up to "about 7.8 kWh" of 8 | differs | **7.68 kWh** per evening (in-sample 7.679, held-out 7.687; 7.61-7.69 per evening); the feeder runs at its 2 kW cap (6 chargers at once) in 45-46 of the 48 five-minute slots of every in-sample evening [E] |
| 0.14 | D05, D07, D11 chargers busy 99-100 %, about 8 swaps; the other twelve barely charge, 2-3 swaps = spares | agree on the numbers; the reason is not demand alone | "busy" = at least one charger running in a 15-min period; in charger-slots they use 85-88 of 96 (about 90 %). Which sites get the power follows the rule's site-number order: in all 498 cached 15-site evenings the first three sites by number take 88 % of the energy (positions 1-3: 2.21, 2.31, 2.21 kWh; position 4: 0.38; positions 6-15: under 0.1) [F]. The Queensboro gateway D45 charges fully (2.43 kWh, 7.24 swaps) when it is second of two sites (D07 + D45) but gets 0.21 kWh and 3.00 swaps when it is fourth of five (k = 5) [F]. In the best layout the Lincoln and Queensboro gateway sites D33 and D38 (8th and 9th by number) get 0.03 and 0.02 kWh |
| 0.15 | rule vs exact at 16 riders / 5 sites: 1.64-2.21, median 1.90, 6 of 9 optimal, gap <= 1.3 %; best of three layouts the same | agree | the other two swap places (rule: coverage 2,612.1 < spread 2,675.2; exact: spread 1,297.3 < coverage 1,460.3); the rule serves 73-84 % of the 80 orders, the exact plan 98-99 % (`validate.json`); the check is at 16 riders and 80 orders, not 64 |
| 0.16 | no bound: C(59,15) = 4.0e13 | agree | 39,895,566,894,540 |
| 0.17 | compute about 4.1 h, 4.3 USD | agree | 4.106 h, 4.345 USD [K] |
| 0.18 | 15-site USD not comparable with the 1-3 site study | agree | reasons in 5.6 |

---

## 1. The 15 sites, south to north

Map numbering (1-15, along the avenues) and names as `make_figs.SITE15` writes them; NTA = the 2010 neighbourhood
tabulation area that holds the site. Class: cabinet = installed swap cabinet, dock = Citi Bike charging dock,
pilot = DOT 2024 pilot hub, PEC = DOT public e-bike charging proposed site (not final), depot = operator store,
grid = restaurant-dense grid cell (no address). Restaurants = DOHMH restaurants within 1 grid km, share of the
11,377 in the study box.

**Table 1a: where and what**

| No. | id | name (location) | class | DOT | NTA (code) | area | spares:chargers | restaurants <= 1 km | nearest entry point, grid km |
|---|---|---|---|---|---|---|---|---|---|
| 1 | D05 | City Hall Park cabinet (249 Broadway) | cabinet | no | SoHo-TriBeCa-Civic Center-Little Italy (MN24) | S14 | 4:2 | 634 (5.6 %) | Brooklyn Bridge 0.39 |
| 2 | D11 | Kenmare St Citi Bike dock (Kenmare & Elizabeth St) | dock | no | SoHo-TriBeCa-Civic Center-Little Italy (MN24) | S14 | 4:2 | 1,211 (10.6 %) | Manhattan Bridge 0.50 |
| 3 | D12 | Essex Market pilot hub (88 Essex St) | pilot | yes | Chinatown (MN27); Lower East Side | S14 | 3:2 | 893 (7.8 %) | Williamsburg Bridge 0.26 |
| 4 | D07 | Grid cell M03 (6th Ave near Bleecker St) | grid | no | West Village (MN23); Greenwich Village | S14 | 4:2 | 975 (8.6 %) | Holland Tunnel 0.91 |
| 5 | D19 | PEC Site 38, 1st Ave & E 5th St | PEC | yes | East Village (MN22) | S14 | 3:2 | 1,152 (10.1 %) | Williamsburg Bridge 1.14 |
| 6 | D16 | Whizz store, 229 W 13th St | depot | no | West Village (MN23) | S14 | 3:2 | 847 (7.4 %) | Holland Tunnel 1.98 |
| 7 | D30 | Grid cell M08 (5th Ave & W 31st St) | grid | no | Midtown-Midtown South (MN17) | 14-59 | 3:2 | 1,554 (13.7 %) | Lincoln Tunnel 2.00 |
| 8 | D33 | Zoomo store, 252 W 38th St | depot | no | Midtown-Midtown South (MN17); Garment District | 14-59 | 3:2 | 1,568 (13.8 %) | Lincoln Tunnel 0.83 |
| 9 | D38 | Grid cell M09 (3rd Ave & E 53rd St) | grid | no | Turtle Bay-East Midtown (MN19) | 14-59 | 3:2 | 845 (7.4 %) | Queensboro Bridge 0.76 |
| 10 | D40 | PEC Site 22, 9th Ave & W 55th St | PEC | yes | Clinton (MN15); Hell's Kitchen | 14-59 | 2:2 | 805 (7.1 %) | Lincoln Tunnel 1.36 |
| 11 | D46 | PEC Site 21, 1st Ave & E 73rd St | PEC | yes | Lenox Hill-Roosevelt Island (MN31); Lenox Hill | N59 | 3:2 | 399 (3.5 %) | Queensboro Bridge 1.27 |
| 12 | D49 | Grid cell M12 (Amsterdam Ave & W 80th St) | grid | no | Upper West Side (MN12) | N59 | 3:2 | 356 (3.1 %) | Lincoln Tunnel 3.23 |
| 13 | D54 | Grid cell M13 (2nd Ave near E 83rd St) | grid | no | Yorkville (MN32) | N59 | 2:2 | 491 (4.3 %) | Queensboro Bridge 1.94 |
| 14 | D55 | E 95th St Citi Bike dock (E 95th St & 3rd Ave) | dock | no | Upper East Side-Carnegie Hill (MN40) | N59 | 3:2 | 287 (2.5 %) | Queensboro Bridge 3.15 |
| 15 | D58 | PEC Site 16, W 106th St (also grid cell M14) | PEC | yes | Upper West Side (MN12) | N59 | 2:2 | 232 (2.0 %) | Lincoln Tunnel 5.38 |

**Table 1b: what each site does per evening (in-sample, p-weighted)**

| No. | id | swaps [95 % CI] | riders who swap there, by entry point | orders <= 1 km served / all | chargers busy | kWh | mean wait before a swap (min) | slots without a charged battery (of 48) | cost rise if closed, USD/day [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| 1 | D05 | 7.90 [7.74, 8.07] | Brooklyn Br 6.9 of 7.9 | 10.4 / 14.4 | 99 % | 2.37 | 58.7 | 37.9 | +837.9 [646.0, 1,029.7] |
| 2 | D11 | 7.76 [7.35, 8.17] | Manhattan Br 6.2 of 7.8 | 28.0 / 38.9 | 99 % | 2.34 | 47.9 | 36.7 | +728.4 [357.2, 1,099.6] |
| 3 | D12 | 3.05 [2.93, 3.16] | Williamsburg Br 3.05 of 3.05 | 19.2 / 26.6 | 34 % | 0.30 | 10.2 | 44.2 | +512.6 [136.0, 889.2] |
| 4 | D07 | 8.00 [8.00, 8.00] | Holland Tun 7.6 of 8.0 | 20.4 / 29.6 | 100 % | 2.45 | 62.3 | 38.9 | +791.2 [551.8, 1,030.6] |
| 5 | D19 | 3.00 | mixed (Williamsburg 1.0, Manhattan 0.9) | 25.2 / 36.2 | 11 % | 0.14 | 1.8 | 33.4 | +476.5 [214.9, 738.0] |
| 6 | D16 | 3.00 | mixed (all six) | 16.0 / 22.5 | 3 % | 0.02 | 0.4 | 17.4 | +472.9 [150.3, 795.6] |
| 7 | D30 | 3.00 | mixed (Lincoln 0.9, Williamsburg 0.8) | 24.4 / 34.5 | 1 % | 0.01 | 0.4 | 19.7 | +292.0 [112.4, 471.7] |
| 8 | D33 | 3.00 | Lincoln Tun 3.0 of 3.0 | 22.5 / 31.5 | 7 % | 0.03 | 5.0 | 44.0 | +480.0 [222.1, 737.8] |
| 9 | D38 | 3.00 | Queensboro Br 3.0 of 3.0 | 19.3 / 28.6 | 3 % | 0.02 | 4.5 | 42.7 | +264.9 [105.9, 424.0] |
| 10 | D40 | 2.00 | mixed (Queensboro 0.8, Lincoln 0.7) | 22.0 / 32.4 | 0 % | 0.00 | 0.4 | 29.0 | +238.4 [-54.9, 531.6] |
| 11 | D46 | 3.00 | mixed (Queensboro 0.8, Lincoln 0.8) | 22.5 / 30.5 | 0 % | 0.00 | 0.0 | 17.1 | +285.3 [143.0, 427.5] |
| 12 | D49 | 3.00 | mixed (Queensboro 1.3, Lincoln 0.7) | 20.0 / 26.5 | 0 % | 0.00 | 0.4 | 18.0 | +424.4 [149.9, 698.9] |
| 13 | D54 | 2.00 | mixed (Queensboro 1.3, Lincoln 0.5) | 25.0 / 33.7 | 0 % | 0.00 | 0.3 | 18.1 | +191.2 [102.9, 279.4] |
| 14 | D55 | 2.95 [2.84, 3.07] | mixed (Queensboro 1.7, Lincoln 0.6) | 14.8 / 19.7 | 0 % | 0.00 | 0.4 | 14.0 | +283.0 [139.8, 426.2] |
| 15 | D58 | 2.00 | mixed (Lincoln 1.1, Queensboro 0.7) | 7.6 / 11.7 | 0 % | 0.00 | 0.6 | 24.6 | +314.5 [31.6, 597.5] |
| | all | 56.67 | | | | 7.68 | | | |

Notes. Swaps without a CI have zero spread over the 12 evenings. "Orders <= 1 km" = orders whose restaurant lies
within 7 blocks (about 1 km) of the site; an order counts at every site within reach, so the column does not add up.
"Chargers busy" = share of the 16 quarter-hours with at least one charger running. "Cost rise if closed" = daily
cost without the site minus with it, all other sites unchanged (remove-one pass); only D40's interval includes zero.
Rider origins are distinct riders who swapped at the site, by the entry point where they started [C].

**Counts.** DOT programme sites (2024 pilot or PEC): **5 of 15** (D12 pilot; PEC Sites 38, 22, 21, 16 = D19, D40,
D46, D58). Listed sites (an address from DOT or operator records): **10**; grid cells: **5** (D07, D30, D38, D49,
D54). By the paper's candidate classes (Table `tab:candidates`): pilot 1 of 2, PEC 4 of 18 (D58 is also grid cell
M14), installed cabinet 1 of 5, Citi Bike dock 2 of 14, operator depot 2 of 4, other 0 of 2, grid cell 5 of 14. The
pool is 20 DOT of 59 (34 %), 45 listed (76 %); the layout is 33 % DOT, 67 % listed. Only one of the two pilot hubs is
open (Essex Market; Cooper Square is not, PEC Site 38 is about 450 m east of it). The 1-3 site study's sites: Site
34 (D23) is the first site added beyond 15 (16 sites); of the best pair, D07 is in and D45 is not (D38, 3rd Ave & E
53rd St, serves the same Queensboro riders).

**Land beyond 14 blocks of every site** (as `fig_map15` computes it, 50 m grid of land points without Roosevelt
Island): **0.04 %** (6 of 15,135 points; the legend rounds to 0 %), a sliver of the Chelsea waterfront along 12th
Ave near W 24th St [L]. The farthest land point is 2.17 grid km from a site; half the land is within 0.85 km; 62.9 %
within 1 km [B].

---

## 2. Why the search put sites where it did, by area

Common set-up (the reasons below rest on these inputs; the rules are those of the 1-3 site study, now at 64 riders):
- Riders start the evening at the six bridge and tunnel entry points with a quarter to half a battery (6-12 of 24
  levels) and swap at 6 levels or below; so a rider's first swap comes soon after entering: 26.1 of the 64 riders
  make their first swap within the first hour, the average first swap comes 61 minutes into the evening, and 16.5
  riders per evening never swap [D].
- Four of the six entry points are south of 14th St (Brooklyn, Manhattan and Williamsburg Bridges, Holland
  Tunnel), so **43 of the 64 riders (67 %)** start there; the Lincoln Tunnel (W 40th St, 10 riders) is in 14-59 and
  the Queensboro Bridge (E 59th St, 11 riders) sits on the 59th St line [A].
- A rider may ride to a site only from within 14 blocks (2.1 km; paper Section II-B, rider moves; except from its
  start).
- All sites share one 2 kW supply, i.e. six chargers at once (paper (16); Section V-A); with 30 chargers open it runs
  at its cap in 45-46 of 48 slots [E].
- Where orders are: of the 320 orders per evening, deliveries are 29.4 % S14, 30.0 % 14-59, **40.6 % N59**; pickups
  29.8 % / 38.2 % / 32.0 % (restaurants are drawn near the customer). Restaurants in the band south of 110th St:
  36.1 % / 47.7 % / 16.2 % (3,998 / 5,283 / 1,789 of 11,070) [A, G].

**South of 14th St: 6 sites (D05, D11, D12, D07, D19, D16), 58 % of the swaps**
- Gateways: each of the four southern entry points has a site within 0.26-0.91 grid km (D12 0.26 Williamsburg,
  D05 0.39 Brooklyn, D11 0.50 Manhattan, D07 0.91 Holland), and the riders who swap there come almost only from that
  entry point (6.9 of 7.9, 7.6 of 8.0, 6.2 of 7.8, 3.05 of 3.05) [A, C].
- Timing: 17.2 of the 26.1 swaps of the first hour (66 %) happen here; 32.7 of the 56.7 swaps per evening [D].
- Restaurants do not explain D05: it has only 634 restaurants within 1 km, yet it is the busiest site but one; the
  bridge does. D11 (1,211) and D19 (1,152) sit in dense blocks.
- Power: D05, D07, D11 hold 6 chargers, exactly the 2 kW supply; they keep a charger running 99-100 % of the
  evening and buy 7.16 of the 7.68 kWh (93 %), yet riders still wait 48-62 minutes there on average and the shelves
  are empty of charged batteries in 37-39 of 48 slots. D12 is fourth in the rule's charging order and gets 0.30
  kWh, so it hands out little more than its 3 spares, and the Williamsburg riders swap least of all six groups (6.9
  rider-swaps per evening for 11 riders; 8.7-10.6 for the other entry points) [C].
- D19 (PEC Site 38, East Village) and D16 (Whizz store, West Village) serve riders from all entry points with their
  spares.
- Size polish: these three busy sites got a fourth spare each (from D40, D54, D58); with 3 spares they made
  6.88-7.00 swaps per evening, with 4 spares 7.76-8.00, so the fourth spare is used every evening, while D40, D54
  and D58 did not use all 3 (2.83-2.95) [`polish_log`, C].
- Value: the three largest removal values (838, 791, 728 USD/day); the six sites together 3,820 USD/day of the
  15-site total of 6,593.
- Robustness: D05, D07, D11 are in all six searched layouts (four search starts, k-median, "15 units free") [I].

**14th-59th St: 4 sites (D30, D33, D38, D40), 19 % of the swaps**
- Gateways: D33 (Zoomo store, W 38th St) is 0.83 km from the Lincoln Tunnel and D38 (3rd Ave & E 53rd St) 0.76 km
  from the Queensboro Bridge; all their swaps are by riders from that entry point (3.0 and 3.0) [A, C].
- But they get almost no power (0.03 and 0.02 kWh; they are 8th and 9th in the charging order) and run out of
  charged batteries early (44.0 and 42.7 of 48 slots without one); 7.0 of this area's 11.0 swaps come in the first
  hour [C, D].
- Restaurants: the densest area (48 % of the band's restaurants); D33 and D30 have the most restaurants within 1 km
  of all 15 sites (1,568 and 1,554); 38 % of the pickups are here [A, G].
- D30 (5th Ave & W 31st St) and D40 (PEC Site 22, Hell's Kitchen) take riders from all entry points.
- Value: removal 480 (D33), 292 (D30), 265 (D38), 238 (D40, interval includes zero); 1,275 USD/day together. D40
  lost a spare in the polish (fewest swaps with 3 spares on the search evenings, 2.71).

**North of 59th St: 5 sites (D46, D49, D54, D55, D58), 23 % of the swaps**
- No entry point and few restaurants (16 % of the band's; 232-491 within 1 km of each site), but **41 % of the
  orders are delivered here** and 32 % are picked up here; riders follow the orders uptown [A, G].
- Their riders come from all six entry points, mostly Queensboro and Lincoln, and later in the evening: 9.4 of
  the area's 12.95 swaps are between 17:00 and 19:00 [C, D].
- No power reaches them (0.00 kWh); each hands out its spares (3, 3, 2, 3, 2) [C].
- Reach: with these five sites 0.04 % of the land is more than 14 blocks from a site; the rule layouts with one to
  three sites north of 59th St leave 18-34 % of the land out of reach, nearly all of the Upper West Side, and cost
  2,000-2,540 USD/day more (section 3) [B].
- The best layout serves 71.2 % of the orders delivered north of 59th St, the same as south of 14th St (71.3 %) and
  in between (70.3 %) [G].
- Value: removal 424 (D49), 315 (D58), 285 (D46), 283 (D55), 191 (D54); 1,498 USD/day together; all intervals
  above zero.
- Robustness: every searched layout (four search starts, k-median, "15 units free") has exactly 5 sites north of
  59th St; D49 is in all six, D54 in five [I].

**In one line.** One site next to each of the six entry points (riders swap soon after entering), the rest spread
so that no rider who follows the orders uptown is more than 14 blocks from a site; with one shared 2 kW supply,
added sites mostly add charged spares, not charging.

---

## 3. Comparison rows (each layout: 15 sites, 782,250 USD, 3 spares and 2 chargers per site unless stated)

| layout (plain name) | how it picks the 15 sites | regret in-sample, USD/day | regret held-out | served in / out | unserved orders per evening (in) | land beyond 14 blocks |
|---|---|---|---|---|---|---|
| best found | the search, then the size polish | 0 | 0 | 72.9 % / 70.3 % | 92.9 | 0.04 % |
| same sites, 3 spares each | best locations before the polish | +389.1 +- 271.8 | +416.6 +- 155.7 | 71.4 / 69.0 | 96.9 | 0.04 % |
| spread rule | spread evenly: start at the candidate nearest the middle, then always add the candidate farthest from those chosen | +667.7 +- 308.9 | +1,011.1 +- 385.7 | 70.4 / 67.1 | 101.3 | 0.0 % |
| "15 units free" | the same search without fixing the number of sites, free to spend 782,250 USD on sites, spares or chargers (from D07 + D45): it still opened 15 sites but gave 13 of them one charger (777,050 USD spent) | +697.4 +- 329.8 | +814.1 +- 418.2 | 70.3 / 67.5 | 101.4 | 0.0 % |
| k-median | classic facility location: the 15 sites that minimise the expected orders' restaurant-to-nearest-site grid distance | +1,028.6 +- 344.0 | +1,143.9 +- 98.4 | 68.9 / 66.5 | 105.1 | 0.0 % |
| DOT-first | DOT pilot hubs and PEC sites first, ranked by demand nearby, filled by demand (at 15 all 15 are DOT sites) | +1,998.1 +- 961.0 | +2,497.8 +- 504.1 | 64.3 / 60.1 | 120.8 | 18.0 % |
| coverage rule | the 15 sites with the most expected orders (restaurant or customer) within 14 blocks | +2,013.3 +- 710.2 | +2,205.9 +- 853.6 | 62.6 / 59.8 | 125.0 | 34.2 % |
| access rule | the 15 sites with the best inverse-distance access to restaurants (each expected order adds 1 / (1 + distance in blocks)) | +2,540.1 +- 266.2 | +2,497.1 +- 532.0 | 59.5 / 57.9 | 134.9 | 19.0 % |

Other starts of the search (each ended at 15 sites with 3 spares each): from the coverage rule's best pair +349.0
+- 241.6 in-sample, +224.5 +- 371.1 held-out (interval includes zero; 9 of its 15 sites are the best's); from the
earlier best pair D07 + D45 +684.8 +- 453.7 / +915.8 +- 520.9; from the spread rule's best pair +731.2 +- 482.5 /
+731.0 +- 307.7.

Reading the rows. The rules fall in two groups: spread, "15 units free" and k-median cover all the land and cost
+668 to +1,029; coverage, DOT-first and access leave 18-34 % of the land out of reach (each misses nearly all of the
Upper West Side and of Battery Park City and the Financial District) and cost +1,998 to +2,540. Inside a group the
differences are not significant (k-median vs spread +360.9 +- 356.7 in-sample, +132.8 +- 369.7 held-out; coverage vs
DOT-first +15.3 +- 592.8; access vs coverage +526.8 +- 560.5) [H]. The losses are spread over the whole island, not
one area: the coverage rule serves 59-63 % of the orders in each of the three areas, the best layout 70-71 % [G].
Almost all of every regret is unserved orders (60 USD each) plus waiting: 97-98 % of every 15-site layout's cost is
order cost; set-up is 197.85 USD/day (1.8 %) and electricity 3.4 USD/day.

---

## 4. Cost versus the number of sites

All points use the standard unit (3 spares, 2 chargers) at every site. Path: k = 1 is the first site of the search
started from nothing; k = 2-14 the search started at D07 + D45; k = 15 the best layout's sites; k = 16-20 adds sites
to those 15. It is a search path, not the best layout per k (0.11).

| k | sites | cost in-sample [95 % CI] | served | cost held-out (served) | swaps | kWh | unserved orders | land beyond 14 blocks |
|---|---|---|---|---|---|---|---|---|
| 1 | D30 | 18,280.8 [18,097.6, 18,464.1] | 10.3 % | 18,434.6 (8.7 %) | 6.7 | 2.33 | 288.1 | 78.1 % |
| 1 (ref.) | D23, DOT Site 34 | 18,182.6 [17,878.4, 18,486.7] | 10.7 % | 18,426.7 (8.9 %) | 6.4 | 2.32 | 286.8 | 79.5 % |
| 2 | D07 + D45 (earlier best pair) | 17,608.2 [17,346.7, 17,869.7] | 19.4 % | 17,597.3 (19.1 %) | 14.4 | 4.86 | 260.0 | 61.8 % |
| 5 | D07, D13, D34, D45, D51 | 15,824.5 [15,450.1, 16,199.0] | 36.2 % | 16,120.9 (34.3 %) | 27.1 | 7.57 | 207.6 | 23.2 % |
| 10 | D05, D07, D13, D28, D34, D40, D45, D48, D51, D55 | 13,760.4 [13,185.5, 14,335.3] | 54.8 % | 14,116.1 (52.4 %) | 41.8 | 7.64 | 149.5 | 2.5 % |
| 15 | best sites, 3 spares each | 11,599.6 [10,582.9, 12,616.3] | 71.4 % | 11,881.3 (69.0 %) | 56.4 | 7.68 | 96.9 | 0.04 % |
| 15 | best (polished sizes) | 11,210.5 [10,338.1, 12,082.9] | 72.9 % | 11,464.7 (70.3 %) | 56.7 | 7.68 | 92.9 | 0.04 % |
| 20 | best sites + D23, D35, D34, D51, D44 | 10,486.3 [9,210.8, 11,761.7] | 80.0 % | 10,682.1 (78.8 %) | 69.6 | 7.68 | 69.7 | 0.04 % |

Paired steps, in-sample (held-out): 1 to 2 sites -672.6 +- 249.5 (-837.3 +- 107.2); 2 to 5 -1,783.7 +- 217.2
(-1,476.4 +- 300.9); 5 to 10 -2,064.1 +- 339.4 (-2,004.8 +- 123.3); 10 to 15 -2,160.8 +- 505.8 (-2,234.8 +- 412.8);
15 to 20 -1,113.3 +- 359.4 (-1,199.2 +- 248.9). Per added site: about 673, 595, 413, 432, 223 USD/day, against a
set-up of 13.19 USD/day per site [H]. On the six search evenings the path beyond 15 saved 536, 221, 245, 171 and
only 25 USD/day for sites 16-20, so the curve is flattening near 20, but 20 sites still beat the polished 15 by
724.2 +- 435.9 (held-out 782.6 +- 160.0). Fifteen is a policy target, not the best number of sites.

What the curve shows about power: the charging energy reaches 7.57 kWh at 5 sites and stays at 7.64-7.68 from 10 to
20 sites, while the swaps grow by about 3 per added site (2.95, 2.91, 2.66 per site for 5-10, 10-15, 15-20), i.e. by
the three charged spares each new site starts with.

---

## 5. Caveats

**5.1 Rule-based lower level.** The 15 sites are the best layout found under rule-based riders, not under the
exact lower level. At 16 riders, 80 orders and 5 sites, the rule's cost is 1.64-2.21 times the exact optimum (median
1.90; 6 of 9 evenings solved to optimality, largest MIP gap 1.3 %); the rule serves 73-84 % of the orders where the
exact plan serves 98-99 %. Of the three 5-site layouts tested, the best one is the same under both, but the other
two swap places (rule: coverage rule cheaper than spread rule; exact: the reverse). No check exists at 64 riders.

**5.2 Three rule details that shape the per-site numbers.**
- Power order: each 5-minute slot the rule gives the shared 2 kW to the open sites in the order of their site
  numbers, which run roughly from south to north (by 2 km rows of the candidate grid). The first three sites by number take 88
  % of the energy in all 498 cached 15-site evenings [F]. So "the three southern sites charge, the others hand out
  spares" is partly this order, not only demand; the run cannot separate the two. The exact lower level would share
  the power optimally.
- Early swaps: 34 % of the swaps happen above a quarter of the battery, when a rider is too low to take the next
  order and still reach a site [D].
- End of the evening: on average 2.9 of the 64 riders end the evening out of reach of an open site with the
  reserve (paper (9)-(10)); the rule reports this instead of preventing it, and the cost does not charge it [J].

**5.3 Shared 2 kW supply.** Inherited unchanged from the 1-3 site study (`sites_nyc.R5_MANHATTAN_PARAMS`
`grid_sites_kw` = 2.0; paper (16) and Section V-A). The best layouts of the 1-3 site study had at most four chargers
(1.33 kW, below the cap); at 15 sites (30 chargers) it allows six chargers at once and binds in 45-46 of 48 slots. Charging power,
not the number of sites, limits the network; each extra site mainly adds its charged spares. A run without the
shared cap was not made (the driver has a `--grid-kw` option since 2026-10-30; RUN did not use it).

**5.4 No bound.** C(59,15) = 39,895,566,894,540 location sets; no lower bound or optimality gap is claimed at 15
sites. Reported instead: the best layout found, the cost-versus-sites path, and paired regrets against rule layouts.

**5.5 Near-ties inside the intervals.**
- The search start from the coverage rule's best pair ended at a different 15-site layout (9 sites shared) that,
  with 3 spares everywhere, is as good as the best sites with 3 spares (-40.1 +- 356.2 in-sample, -192.1 +- 523.7
  held-out); only the size polish separates them, and the polished best's held-out lead over it (224.5 +- 371.1)
  includes zero. The best layout was chosen on 6 evenings and re-costed on 12 + 12.
- Robust sites: D05, D07, D11 and D49 are in all six searched layouts, D54 in five; D19, D33 and D58 appear only in
  the best (nearby alternatives take their place elsewhere). Explain by cluster and area, not by corner.
- Single site at 64 riders: D23 vs D30 is a tie (-98.3 +- 188.3).
- D40's removal interval includes zero.
- The best layout's own interval is wide (+-872.4); differences between layouts are paired and much tighter.

**5.6 USD not comparable with the 1-3 site study.** Eight times the riders and orders (64 vs 8 riders; 256-384 vs
32-48 orders); a rule-based lower level costing 1.6-2.2 times the exact plan vs the exact integer program; the shared
2 kW supply binds at 15 sites, while the 1-3 site study's best layouts stayed below it. The same layouts cost far more and serve far less: DOT Site 34
alone 1,085.87 USD/day, 77.5 % served (8 riders, exact) vs 18,182.6, 10.7 % (64 riders, rule); the best pair 716.85,
98.3 % vs 17,608.2, 19.4 %. Same prices (60 USD per unserved order, 18 USD/h response, 15 USD/h lateness), same
set-up per site (13.19 USD/day), same candidates, data and entry points. Only differences inside one study mean
something.

**5.7 Candidate realism.** Five sites are grid cells, not addresses. D16 and D33 are operator stores without a swap
cabinet. PEC sites are not final (about 25 of 50 will be kept): Community Board 4 opposes Site 22 = D40 (letter
2026-07-17, vote 40-0-1); Community Board 8 supports Site 21 = D46 (36-6-2, 2026-07-15). D05 opened in 2026; whether
the Essex Market pilot cabinets still exist after February 2025 is unknown (`data/raw/dot_candidate_sites.csv`).

**5.8 Reporting traps.** Do not copy "go: 48 riders / 240 orders" (0.5). Cite the feeder as (16), not (21). The
total charging is 7.68 kWh, not 7.8. `site_table.tex` in `paper_itsc/figs/` was still the DEMO when this sheet was
written; regenerate from `figs/map15/` before quoting it.

---

## 6. Draft interpretation paragraph (plain language, about 150 words)

> **Why these 15 sites.** Riders enter Manhattan over the bridges and through the tunnels, and four of the six entry
> points are south of 14th Street. Two thirds of the 64 riders start there with a quarter to half a battery and swap
> soon after they arrive, so the best layout has a site within 1 km of every entry point: City Hall Park, Kenmare
> Street, Essex Market, Greenwich Village, West 38th Street and East 53rd Street. The other nine sites follow the
> riders: 41 % of the orders are delivered north of 59th Street, and a rider can reach a site only within 14 blocks,
> so the sites spread until almost no land is farther away. All sites share one 2 kW supply. Our rule-based lower
> level hands it out in a fixed, roughly south-to-north order, so three southern entry sites use nearly all of it;
> the other twelve mainly hand out their two or three charged spares.

(About 155 words. Entry points in the same order: Brooklyn Bridge, Manhattan Bridge, Williamsburg Bridge,
Holland Tunnel, Lincoln Tunnel, Queensboro Bridge. Numbers: 43 of 64 riders, section 2; site distances, Table 1a; 40.6 % of deliveries and 0.04 % of
the land, sections 1-2; 7.16 of 7.68 kWh, section 2. If the lead prefers not to name the charging order here, end
with "...the three southern entry sites use nearly all of it" and keep the order in the caveats, 5.2.)

---

## 6a. Compute of the useful runs (r7i.4xlarge on demand, 1.0584 USD/h)

| run | stage | hours | USD |
|---|---|---|---|
| RUN48 (48 riders) | build 24 evenings | 0.545 | 0.576 |
| | dry run (gate failed: median 2.5 swaps) | 0.027 | 0.029 |
| | exact-ILP check, 16 riders, 9 solves of at most 30 min | 0.799 | 0.845 |
| | search start refused by the gate (3 s) | 0.001 | 0.001 |
| RUN (64 riders) | build 24 evenings | 0.848 | 0.898 |
| | dry run | 0.053 | 0.057 |
| | search: 1,512 lower-level evaluations (8,793 quick screening scores) | 1.459 | 1.544 |
| | final table, held-out, cost-versus-sites, remove-one: 468 evaluations | 0.374 | 0.396 |
| total | | **4.106** | **4.345** |

The 64-rider study alone: 2.734 h, 2.894 USD. In the search, one lower-level evaluation took 21.4 s on average
(longest 42.5 s, worker memory at most 2.4 GB).

---

## 7. Sources (one line per number group)

- S1 `cloud_results/ebike_swap_sim/outputs/r8_k15_n64/final_summary.json`: `best`, `best_out` (V, CI, served, kWh 7.679 / 7.687, swaps 56.67, components: set-up 197.85, electricity 3.39, order cost 10,885.36, unserved 5,572.86 = 92.9 orders x 60 USD, investment 782,250); `in_sample` / `held_out` (every layout's V, CI, served, swaps, kWh, components; unserved orders = `components.unserved` / 60); `regret_in` / `regret_out` (all regrets and half-widths); `vk`; `site_table` (removal values and CIs).
- S2 `.../r8_k15_n64/RESULTS.md`: the same tables in readable form (dry run, ILP check, search restarts, final table, V(k), per-site statistics, cost per batch).
- S3 `.../r8_k15_n64/site_stats.csv`: Table 1b swaps and CIs, orders <= 1 km, busy share, kWh, wait, stock-out slots, removal and CI.
- S4 `.../r8_k15_n64/layout.json` (and its copy `paper_itsc/figs/map15/layout.json` with the local `candidates_csv` path): sites, sizes B:C, n_bikes 64, n_orders 320, V, CIs, investment.
- S5 `.../r8_k15_n64/search_summary.json`: restarts and their forward paths (`path_k`), `extension_path` (search-evening values 11,456.0 to 10,257.8), `vk_layouts`, `polish_log`, `free` (15 sites, C1 at 13), `n_cells` 1,512, `proxy_calls` 8,793, `cell_s_mean` 21.37, `cell_s_max` 42.52, `worker_rss_gb_max` 2.45.
- S6 `.../r8_k15_n64/dryrun.json` (median 3.0, gates, stale recommendation text, `n_arcs`) and `.../r8_k15/dryrun.json` (median 2.5, escalate true).
- S7 `.../r8_k15_n64/validate.json` (= `.../r8_k15/validate.json`, identical): 9 rows, ratios 1.636-2.209, median 1.899, 6 OPTIMAL, gap max 0.0131, rule / ILP values per layout, served shares.
- S8 `.../r8_k15/cost.jsonl` and `.../r8_k15_n64/cost.jsonl` ("end" rows): hours and USD of section 6a; `wall_time.json` for the evaluation counts (60, 1,512, 468).
- S9 `.../r8_k15_n64/candidates.csv` (byte-identical to `ebike_swap_sim/outputs/r7_prod_final/r7_siting/candidates.csv`): ids, classes, coordinates, grid-square labels (2,329 for D30); `data/raw/dot_candidate_sites.csv` `status_date`: D05 opening, Essex Market status, CB4 and CB8 positions on Sites 22 and 21.
- S10 `notes/verify/r8_facts.py` output, by label: [A] Table 1a geography, entry-point distances and areas, restaurants by area (box 11,377; band 11,070), Cooper Square to PEC Site 38 (0.44 km straight, 0.49 grid km); [B] land beyond 14 blocks for every layout and k, the NTAs the weak rules leave out of reach (Upper West Side 86-100 %, Battery Park City-Lower Manhattan 87-93 %), distance statistics; [C] per-site rider origins, charging steps and the reproduction of `site_stats.csv`, rider-swaps by entry point (Holland 10.62 ... Williamsburg 6.88), swaps per site with 3 spares each (6 search evenings and 12 in-sample evenings); [D] swaps by hour and area, first swaps, never-swapping riders, swap levels; [E] 6 charging steps (2 kW) per slot, slots at the cap, kWh per evening; [F] kWh by position in the site-number order, D07 + D45 and k = 5 layouts; [G] rebuilt orders (2,674 of 2,674 served deliveries match the cached schedules), pickups and deliveries by area, served share by area for six layouts; [H] paired stratified differences; [I] site overlap across searched layouts; [J] end-of-evening reports; [K] cost sums and C(59,15); [L] street hints for the grid cells and the uncovered land.
- S11 code (rules and set-up): `ebike_swap_sim/ebike_swap_sim/data_nyc.py` (entry points lines 1401-1408, initial charge 25-50 % and round-robin riders lines 1299-1303, 48 slots of 5 min); `sites_nyc.py` (`R5_MANHATTAN_PARAMS`: 4 h window, 1.25 orders per rider-hour, `grid_sites_kw` 2.0, `P_kw` 1.4; `MANHATTAN15_PARAMS`; `spec_from_instance` maps `grid_sites_kw` to the layout's shared cap and `_finish` line 679 sets `P_grid` for every layout; `layout_items` sorts sites by id; `scenario_design` levels 1.0 / 1.25 / 1.5 and weights 5/7, 2/7; `access_radius_blocks` = 14); `config.py` `energy_calibration('ebaas')` (0.6 kWh pack, 24 levels of 25 Wh, 0.333 kW per charger); `baseline.py` (`BaselineParams`: threshold 0.25, demand-aware charging with a 1 h look-back, reach-guard swaps, no transfers; `_step9_charging` "allocated in facility order"); `evaluate.py` (`site_metrics` definitions: 7-block radius, 15-min busy periods, kWh = steps x 25 Wh / 0.9; `check` family '(9)'); `costs.py` `R6_PRICING` (60 / 18 / 15); `bilevel.py` (`demand_weights`, `access_weights`, `_spread_order`, `k_median_layout`, `dot_first_layout`, `stratified_ci`); `experiments/r8_k15.py` (`rule_layouts`, `polish_sizes`, V(k) assembly lines 1191-1208, label line 910, `--grid-kw` lines 545-548).
- S12 paper: `paper_itsc/sections/05_data.tex` (Section V-A: 2 kW supply, six chargers, quarter-to-half battery, 32-48 orders; Section V-B classes), `06_results.tex` (1-3 site numbers 1,085.87 / 77.5 %, 716.85 / 98.3 %), `03_model.tex` (14-block approach rule), `main.aux` (equation numbers: (16) feeder, (9)-(10) rider paths and terminal row, (34) regret, (35) stratified CI).
- S13 notes: `notes/siting15_design.md` sections 0-3, 5, 12.2, 12.3 (study design, 94 % ILP gap, gate at 3 swaps, no-bound statement); `notes/dot_candidate_sites.md` (pilot and PEC programme facts).
