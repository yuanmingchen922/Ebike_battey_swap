# R8 fifteen-site study, plan B (each site its own 1.4 kW connection, shared limit lifted): facts sheet for the paper (2026-10-30)

Purpose: every number the paper writer needs to explain the 15-site result of record, each traced to a file (section 8).
Plan B is the result of record (author's decision 2026-10-30). Plan A (all sites share one 2 kW supply) keeps its own
sheet, `notes/r8_results_facts_planA.md`.

Run read: RUN = `cloud_results/ebike_swap_sim/outputs/r8_k15_sp/` (downloaded and complete: the exact check
`validate.json` finished at 20:51:21 UTC and is in the folder; section 5.1). Plan A = `.../r8_k15_n64/`; the 48-rider
run = `.../r8_k15/`.
Derived numbers come from `notes/verify/r8_facts.py`, now parameterized: `python3 -I notes/verify/r8_facts.py "$PWD"`
runs plan B (default), `... --run r8_k15_n64` runs plan A (read-only, about 10 s; section labels [A]-[P] below). It
reads each run's own `layout.json` (with `candidates_csv` pointed at the run's local `candidates.csv`) and imports the
paper's map helpers from `paper_itsc/figs/src/make_figs.py` (names `SITE15`). Nothing in `paper_itsc` was edited.

Conventions. USD per day = one 16:00-20:00 evening, allocated set-up included (13.19 USD/day per standard site).
In-sample = the 12 evenings of the final table; held-out = 12 other evenings; the search used 6 of the 12 (seeds 0, 2,
4, 6, 8, 10). "+-" = half-width of the stratified 95 % CI (paper eq. (35)); differences are paired by evening.
Areas: S14 = south of 14th St, 14-59 = 14th to 59th St, N59 = north of 59th St (guide lines of the map, rotated
along-avenue coordinate of `make_figs.rot`). "Grid km" = distance along the street grid. Paper equation numbers are
those of the compiled `paper_itsc/main.aux`: (9) rider flow, (10) terminal row, (15) chargers and site power,
(16) shared feeder, (34) regret, (35) stratified CI.

---

## 0. Check of the lead's headline numbers

| # | lead fact | verdict | evidence |
|---|---|---|---|
| 0.1 | each site its own 1.4 kW, shared limit lifted (`--grid-kw 1000`) | agree, with one precision | `layout.json` grid_kw 1000, site_kw 1.4; every stage's argv has `--grid-kw 1000`. Precision: a site has at most 2 chargers of 0.333 kW (0.67 kW), so its 1.4 kW connection never binds either; no power limit binds anywhere in plan B, only the two chargers per site do (never more than 2 charging steps per site and slot) [E] |
| 0.2 | best after the polish 9,081.4 [8,111.4, 10,051.3], 86.4 % served; held-out 9,234.6 | agree | held-out CI [8,926.8, 9,542.3], served 85.4 %; on the 6 search evenings 8,851.4 (`search_summary.json`) |
| 0.3 | sites and spares D05(B4) D07 D09 D12(B4) D18 D23 D28(B2) D34(B2) D35(B4) D38(B4) D41 D48 D49(B2) D50 D55(B2), 2 chargers each | agree | 45 spares, 30 chargers, 782,250 USD (`layout.json`). South-to-north map order differs from the id order: 1 D05, 2 D09, 3 D12, 4 D07, 5 D18, 6 D23, 7 D28, 8 D34, 9 D35, 10 D38, 11 D41, 12 D48, 13 D49, 14 D50, 15 D55 [A] |
| 0.4 | same sites with 3 spares each: +638.1 +- 167.7 | agree | held-out +801.3 +- 294.0 [H] |
| 0.5 | six regrets and served shares | agree, all six | recomputed with `stratified_ci` from the per-evening costs; all 19 regrets of `final_summary.json` reproduce (value and half-width) [H]. By size the order is spread < "15 units free" < k-median < coverage < DOT-first < access. Held-out, "15 units free" (+1,785.9) is cheaper than the spread rule (+2,145.2), but their difference is not significant (-359.4 +- 430.4) |
| 0.6 | cost versus number of sites (6 points) | numbers agree; "greedy path" is not one path | stitched from four search paths (section 4) |
| 0.7 | every site charges, busy 52-100 %, about 25.6 kWh and 79 swaps | agree | busy 51.8-99.7 %, 25.62 kWh, 79.19 swaps per evening; `site_stats.csv` reproduced from the cache to 5e-5 [C] |
| 0.8 | coverage-rule dry run: plan A 13,223.8, 62.6 %, median 3.0; plan B 12,337.3, 71.2 %, median 4.0 | agree | same layout and same 12 evenings in both runs, so the difference is paired: -886.5 +- 218.7 USD/day [M]; plan B median 4.02 swaps per site (`dryrun.json`) |
| 0.9 | compute plan B 1.61 h, 1.71 USD, exact check running | agreed then; superseded | the check has finished: `validate` ran 20:27:10-20:51:21 UTC, 0.403 h, 0.427 USD; plan B total now **2.015 h, 2.133 USD** (RESULTS.md cost table: 2.01 h, 2.13 USD) [K], section 7a |
| 0.10 | riders who end the evening "out of reach of an open site": fewer than plan A's 2.9 of 64? | **no, and the wording is wrong in both plans** | plan B 5.60 per evening in-sample (6.07 held-out) against plan A 2.93 (3.24). None of them is out of reach: every one of them (65 rider-evenings in-sample, 72 held-out) ends the evening standing at an open site with 0 or 1 of 24 battery levels, below the 2-level reserve, waiting for a charged battery since about 19:14 on average [J]. Plan A's riders are in the same state (33 and 38 rider-evenings, all at an open site) |
| 0.11 | "go: 48 riders / 240 orders" | present, stale | in plan B's `dryrun.json` `recommendation` and in RESULTS.md (dry-run line); hard-coded at `experiments/r8_k15.py` line 910; the run is 64 riders / 320 orders (`layout.json` n_bikes 64, n_orders 320; cost.jsonl argv `--n-bikes 64`) |
| 0.12 | RESULTS.md: "shared supply group of all sites" | number trap | `lanes.txt` and the driver call it "constraint (21)" (code E2 numbering); in the paper the shared feeder is **(16)** and (21) is the order price |
| 0.13 | exact check: all 9 integer programs optimal; rule 1.65-2.56 times the exact optimum (median 2.10); both lower levels rank the three 5-site layouts in the same order | agree | 9 of 9 OPTIMAL (gaps 0, 8.2e-5, 9.5e-5); ratio 1.650-2.558, median 2.099; means rule 2,467.5 < 2,675.3 < 3,075.0, exact 1,289.6 < 1,297.3 < 1,334.7; but the exact lower level separates the layouts far less (section 5.1) [P] |
| 0.14 | end-of-evening riders: could a charge for them change a comparison with the best? | checked: no, at one or two order prices | no comparison layout has more of them than the best; at 60 and 120 USD per rider every 15-site comparison keeps its sign and significance; only 20 vs 15 sites becomes significant held-out (section 5a) [O] |

---

## 1. The 15 sites, south to north

Map numbering (1-15 along the avenues) and names as `make_figs.SITE15` writes them (the same as the regenerated
`paper_itsc/figs/site_table.tex`). NTA = 2010 neighbourhood tabulation area that holds the site. Class: cabinet =
installed swap cabinet, dock = Citi Bike charging dock, pilot = DOT 2024 pilot hub, PEC = DOT public e-bike charging
proposed site (not final), grid = restaurant-dense grid cell (no address). Restaurants = DOHMH restaurants within
1 grid km (share of the 11,377 in the study box).

**Table 1a: where and what**

| No. | id | name (location) | class | DOT | NTA (code) | area | spares:chargers | restaurants <= 1 km | nearest entry point, grid km |
|---|---|---|---|---|---|---|---|---|---|
| 1 | D05 | City Hall Park cabinet (249 Broadway) | cabinet | no | SoHo-TriBeCa-Civic Center-Little Italy (MN24) | S14 | 4:2 | 634 (5.6 %) | Brooklyn Bridge 0.39 |
| 2 | D09 | Grid cell M04 (Bowery near Division St, Chinatown) | grid | no | Chinatown (MN27) | S14 | 3:2 | 778 (6.8 %) | Manhattan Bridge 0.29 |
| 3 | D12 | Essex Market pilot hub (88 Essex St) | pilot | yes | Chinatown (MN27); Lower East Side | S14 | 4:2 | 893 (7.8 %) | Williamsburg Bridge 0.26 |
| 4 | D07 | Grid cell M03 (6th Ave near Bleecker St) | grid | no | West Village (MN23); Greenwich Village | S14 | 3:2 | 975 (8.6 %) | Holland Tunnel 0.91 |
| 5 | D18 | Cooper Square pilot hub (also PEC Site 36) | pilot | yes | West Village (MN23); East Village / NoHo | S14 | 3:2 | 1,201 (10.6 %) | Manhattan Bridge 1.52 |
| 6 | D23 | PEC Site 34, 2nd Ave & E 13th St | PEC | yes | East Village (MN22) | S14 | 3:2 | 976 (8.6 %) | Manhattan Bridge 1.84 |
| 7 | D28 | Swobbee cabinets, 836 6th Ave | cabinet | no | Midtown-Midtown South (MN17); NoMad | 14-59 | 2:2 | 1,383 (12.2 %) | Lincoln Tunnel 1.96 |
| 8 | D34 | W 42nd St Citi Bike dock (W 42nd St & 6th Ave) | dock | no | Midtown-Midtown South (MN17) | 14-59 | 2:2 | 1,791 (15.7 %) | Lincoln Tunnel 1.10 |
| 9 | D35 | PEC Site 29, 9th Ave & W 42nd St | PEC | yes | Clinton (MN15); Hell's Kitchen | 14-59 | 4:2 | 1,077 (9.5 %) | Lincoln Tunnel 0.37 |
| 10 | D38 | Grid cell M09 (3rd Ave & E 53rd St) | grid | no | Turtle Bay-East Midtown (MN19) | 14-59 | 4:2 | 845 (7.4 %) | Queensboro Bridge 0.76 |
| 11 | D41 | Grid cell M10 (Broadway & 8th Ave at W 57th-58th St, just south of Columbus Circle) | grid | no | Midtown-Midtown South (MN17) | 14-59 | 3:2 | 727 (6.4 %) | Queensboro Bridge 1.81 |
| 12 | D48 | Grid cell M11 (2nd Ave near E 76th St) | grid | no | Lenox Hill-Roosevelt Island (MN31); Lenox Hill | N59 | 3:2 | 489 (4.3 %) | Queensboro Bridge 1.34 |
| 13 | D49 | Grid cell M12 (Amsterdam Ave & W 80th St) | grid | no | Upper West Side (MN12) | N59 | 2:2 | 356 (3.1 %) | Lincoln Tunnel 3.23 |
| 14 | D50 | W 92nd St Citi Bike dock (W 92nd St & Broadway) | dock | no | Upper West Side (MN12) | N59 | 3:2 | 218 (1.9 %) | Lincoln Tunnel 4.34 |
| 15 | D55 | E 95th St Citi Bike dock (E 95th St & 3rd Ave) | dock | no | Upper East Side-Carnegie Hill (MN40) | N59 | 2:2 | 287 (2.5 %) | Queensboro Bridge 3.15 |

**Table 1b: what each site does per evening (in-sample, p-weighted)**

| No. | id | swaps [95 % CI] | riders who swap there, by entry point | orders <= 1 km served / all | chargers busy | kWh | mean wait before a swap (min) | slots without a charged battery (of 48) | cost rise if closed, USD/day [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| 1 | D05 | 7.90 [7.67, 8.14] | Brooklyn Br 7.0 of 7.8 | 12.6 / 14.4 | 99 % | 2.35 | 60.0 | 37.2 | +1,236.2 [993.4, 1,479.0] |
| 2 | D09 | 6.52 [6.11, 6.94] | Manhattan Br 5.4 of 6.5 | 20.2 / 23.2 | 99 % | 2.21 | 41.6 | 35.1 | +966.1 [702.8, 1,229.4] |
| 3 | D12 | 8.14 [7.88, 8.40] | Williamsburg Br 7.3 of 8.1 | 23.1 / 26.6 | 98 % | 2.40 | 55.6 | 37.5 | +1,272.5 [1,040.0, 1,504.9] |
| 4 | D07 | 6.95 [6.84, 7.07] | Holland Tun 6.8 of 6.9 | 24.5 / 29.6 | 100 % | 2.40 | 78.8 | 39.8 | +1,184.8 [762.3, 1,607.4] |
| 5 | D18 | 5.76 [5.11, 6.41] | mixed (Williamsburg 1.8, Brooklyn 1.6, Manhattan 1.6) | 36.6 / 42.4 | 82 % | 1.88 | 32.3 | 28.8 | +617.2 [505.7, 728.7] |
| 6 | D23 | 4.57 [4.07, 5.07] | mixed (Manhattan 1.5, Williamsburg 1.0, Brooklyn 1.0) | 22.5 / 26.6 | 67 % | 1.52 | 16.7 | 24.8 | +497.3 [323.3, 671.3] |
| 7 | D28 | 2.88 [2.35, 3.41] | mixed (Manhattan 0.8, Williamsburg 0.7) | 26.9 / 32.3 | 56 % | 1.12 | 8.9 | 19.6 | +260.4 [33.7, 487.0] |
| 8 | D34 | 2.69 [2.40, 2.98] | mixed (Lincoln 0.8, Queensboro 0.5) | 38.7 / 45.3 | 62 % | 1.18 | 9.4 | 19.5 | +169.3 [9.6, 328.9] |
| 9 | D35 | 7.57 [7.13, 8.02] | Lincoln Tun 6.1 of 7.4 | 27.2 / 31.5 | 99 % | 2.24 | 31.1 | 34.5 | +753.2 [457.9, 1,048.6] |
| 10 | D38 | 7.95 [7.84, 8.07] | Queensboro Br 6.1 of 8.0 | 23.0 / 28.6 | 100 % | 2.33 | 32.5 | 33.9 | +628.4 [185.9, 1,071.0] |
| 11 | D41 | 3.93 [3.24, 4.62] | mixed (Queensboro 1.1, Holland 1.1, Lincoln 1.0) | 25.6 / 31.8 | 52 % | 1.14 | 2.5 | 13.0 | +280.8 [-173.4, 734.9] |
| 12 | D48 | 4.29 [3.45, 5.12] | mixed (Queensboro 1.9, Lincoln 1.0) | 30.6 / 33.6 | 62 % | 1.37 | 4.5 | 19.4 | +255.7 [-38.6, 550.0] |
| 13 | D49 | 2.83 [1.95, 3.71] | mixed (Queensboro 1.1, Lincoln 0.7) | 22.5 / 26.5 | 53 % | 1.08 | 4.9 | 18.1 | +230.3 [-50.9, 511.5] |
| 14 | D50 | 4.38 [3.94, 4.82] | mixed (Queensboro 1.9, Lincoln 1.7) | 15.6 / 18.5 | 64 % | 1.34 | 4.8 | 19.7 | +379.0 [170.5, 587.4] |
| 15 | D55 | 2.81 [2.19, 3.43] | mixed (Queensboro 1.3, Lincoln 0.8) | 17.7 / 19.7 | 54 % | 1.06 | 8.6 | 17.1 | +126.3 [-15.7, 268.2] |
| | all | 79.19 | 78.5 rider-site pairs | | | 25.62 | | | sum 8,857.4 |

Notes. "Orders <= 1 km" = orders whose restaurant lies within 7 blocks (about 1 km) of the site; an order counts at
every site within reach, so the column does not add up. "Chargers busy" = share of the 16 quarter-hours with at least
one charger running. "Cost rise if closed" = daily cost without the site minus with it, all other sites unchanged
(remove-one pass); **four intervals include zero: D41, D48, D49, D55**; D34 [9.6, 328.9] and D28 [33.7, 487.0] only
just exclude it. Rider origins are distinct riders who swapped at the site, by the entry point where they started [C].

**Counts.** DOT programme sites (2024 pilot or PEC): **4 of 15** (D12 Essex Market pilot, D18 Cooper Square pilot,
D23 PEC Site 34, D35 PEC Site 29). Listed sites (an address from DOT or operator records): **9**; grid cells: **6**
(D07, D09, D38, D41, D48, D49). By the paper's candidate classes: pilot 2 of 2, PEC 2 of 18, installed cabinet 2 of 5
(D05, D28), Citi Bike dock 3 of 14 (D34, D50, D55), operator depot 0 of 4, other 0 of 2, grid cell 6 of 14. The pool
is 20 DOT of 59 (34 %), 45 listed (76 %); the layout is 27 % DOT, 60 % listed. **Both pilot hubs are open.** The 1-3
site study's sites: its best single site, DOT Site 34 (D23), is one of the 15; of its best pair, D07 is in and D45 is
not (D38, 3rd Ave & E 53rd St, serves the Queensboro riders). Areas: 6 sites S14, 5 in 14-59, 4 N59 [A].

**Land beyond 14 blocks of every site** (as `fig_map15` computes it, 50 m land grid without Roosevelt Island):
**0.90 %** (136 of 15,135 points) in two strips: (i) the north end of Central Park and the blocks along W 110th St
(Central Park North) between Frederick Douglass Circle and Malcolm X Blvd, at the northern edge of the study area
(81 points); (ii) the Hudson waterfront of Chelsea west of 11th Ave between about W 14th and W 24th St (55 points)
[B, L]. Only **1.3 of the 320 orders per evening** have their customer more than 14 blocks from every open site (89 %
of them served), and 0.1 their restaurant [G]. The farthest land point is 2.53 grid km from a site; half the land is within 0.86 km; 61.7 % within 1 km [B].

---

## 2. Why the search put sites where it did, by area

Common set-up (the reasons below rest on these inputs; the rules are those of the 1-3 site study, at 64 riders,
without the shared supply):
- 64 riders: 11 each start at the Queensboro, Williamsburg, Manhattan and Brooklyn Bridges, 10 each at the Lincoln
  and Holland Tunnels, with a quarter to half a battery (6-12 of 24 levels). A rider swaps at 6 levels or below, or
  earlier when it is too low to take the next order and still reach a site afterwards (33.3 % of the swaps happen at
  7-12 levels). 27.2 riders make their first swap within the first hour, the average first swap comes 74 minutes
  into the evening, and 4.7 riders per evening never swap (4.2 held-out). When a swap starts the battery holds 5.1 of
  24 levels on average (about a fifth of a full battery; 5.0 held-out); 5.8 of the 79.2 swaps per evening start at 0 or
  1 level, which is allowed (the 2-level reserve applies only at the end of the evening) [D, O].
- Four of the six entry points are south of 14th St, so **43 of the 64 riders (67 %)** start there; the Lincoln
  Tunnel (W 40th St) is in 14-59 and the Queensboro Bridge sits on the 59th St line [A].
- A rider rides to a site only from within 14 blocks (2.1 km; paper Section II-B, except from its start).
- Charging: each site charges as many batteries as the swaps it saw in the last hour suggest, minus its charged
  stock (`baseline.py` `_step9_charging`), limited only by its 2 chargers: no power limit binds [E]. All 30 chargers
  together draw up to 10 kW (p-weighted evening peak 9.76 kW, evening mean 6.40 kW), five times plan A's 2 kW.
- Where orders are (the same 24 evenings as plan A; the instances were reused): of the 320 orders per evening,
  deliveries are 29.4 % S14, 30.0 % 14-59, **40.6 % N59**; pickups 29.8 % / 38.2 % / 32.0 %. Restaurants in the
  band south of 110th St: 36.1 % / 47.7 % / 16.2 % (3,998 / 5,283 / 1,789 of 11,070) [A, G].
- Swaps by area and hour (of 79.2 per evening): S14 39.9 (50 %), 14-59 25.0 (32 %), N59 14.3 (18 %); by hour 27.2,
  19.1, 14.2 and 18.7 swaps (16-17, 17-18, 18-19, 19-20 h) [D].
- **Every one of the six searched layouts** (four search starts, k-median, "15 units free") puts a site within
  0.94 grid km of each of the six entry points; the coverage, access and DOT-first rules leave the Brooklyn Bridge
  1.75-2.04 km from their nearest site, and the spread rule leaves the Lincoln Tunnel 1.09 km away [I].

**South of 14th St: 6 sites (D05, D09, D12, D07, D18, D23), 50 % of the swaps, 65 % of the removal value**
- Gateways: each of the four southern entry points has a site within 0.26-0.91 grid km (D12 0.26 Williamsburg, D09
  0.29 Manhattan, D05 0.39 Brooklyn, D07 0.91 Holland), and the riders who swap there come mostly from that entry
  point (7.3 of 8.1, 5.4 of 6.5, 7.0 of 7.8, 6.8 of 6.9 distinct riders) [A, C].
- Timing: 16.6 of the 27.2 swaps of the first hour (61 %) happen here [D].
- Restaurants do not explain the gateway sites: D05 has only 634 restaurants within 1 km and D09 778, yet they are
  among the busiest; the bridges do. D18 (Cooper Square, 1,201) and D23 (PEC Site 34, 976) sit in the dense East
  Village and serve riders mostly from the three East River bridges (mixed origins, 4.6-5.8 swaps).
- Power and stock: the four gateway sites run both chargers in 35-41 of 48 slots (charger use 83-90 %) and buy
  2.21-2.40 kWh each, yet they have no charged battery in 35-40 of 48 slots and riders wait 42-79 minutes on average
  before a swap there (D07 79 min). With its own connection, D12 (Williamsburg) now charges fully (2.40 kWh, 8.14
  swaps); the Williamsburg riders account for 14.2 rider-site pairs per evening (distinct riders swapping at a site),
  the second most of the six groups (plan A: 6.9, the fewest, when D12 was fourth in the charging order) [C, E].
- Size polish: D12 got a fourth spare by the D'Hondt rule (most swaps with 3 spares on the search evenings, 7.10) and
  D05 by a later transfer (from D49); with 3 spares they made 7.10 and 6.86 swaps per evening (12 in-sample evenings),
  with 4 spares 8.14 and 7.90, so the fourth spare is used every evening [C, `polish_log`].
- Value: the four largest removal values of all 15 sites (1,272 D12, 1,236 D05, 1,185 D07, 966 D09); the six sites
  together 5,774 USD/day of the 15-site total of 8,857.
- Robustness: D05 and D07 are in all six searched layouts; D23 in three; D09 and D12 in two (the other layouts use
  D11 Kenmare St, D13 or D14 for the Manhattan and Williamsburg Bridges); D18 only in the best [I].

**14th-59th St: 5 sites (D28, D34, D35, D38, D41), 32 % of the swaps, 24 % of the removal value**
- Gateways: D35 (PEC Site 29, 9th Ave & W 42nd St) is 0.37 km from the Lincoln Tunnel and D38 (3rd Ave & E 53rd St)
  0.76 km from the Queensboro Bridge; most of their riders come from that entry point (6.1 of 7.4 and 6.1 of 8.0).
  Both run their chargers 99-100 % of the evening and buy 2.24 and 2.33 kWh (plan A's gateway sites here got 0.03
  and 0.02 kWh); riders still wait 31-33 minutes and the shelves are empty in 34-35 of 48 slots [A, C, E].
- Restaurants: the densest area (48 % of the band's restaurants, 38 % of the pickups); D34 (W 42nd St dock) has the
  most restaurants within 1 km of all 15 sites (1,791) and D28 (836 6th Ave) the second most (1,383) [A, G].
- D28, D34 and D41 take riders from five or six entry points and are lightly used (2.7-3.9 swaps, chargers busy
  52-62 %).
- Size polish: D35 and D38 each got a fourth spare, taken from D28 and D34 (the sites with the fewest swaps here):
  D35 6.45 -> 7.57 and D38 6.88 -> 7.95 swaps; D28 4.00 -> 2.88 and D34 3.90 -> 2.69 [C].
- Value: removal 753 (D35), 628 (D38), 281 (D41, interval includes zero), 260 (D28), 169 (D34); 2,092 USD/day together.
- Robustness: D34, D35 and D41 are in all six searched layouts, D28 in three, D38 in two (others use D39 or D45 for
  the Queensboro Bridge) [I].

**North of 59th St: 4 sites (D48, D49, D50, D55), 18 % of the swaps, 11 % of the removal value**
- No entry point and few restaurants (16 % of the band's; 218-489 within 1 km of each site), but **41 % of the orders
  are delivered here** and 32 % are picked up here; riders follow the orders uptown [A, G].
- Their riders come from all six entry points, mostly Queensboro and Lincoln, and later in the evening: 8.8 of the
  area's 14.3 swaps are between 17:00 and 19:00 [C, D].
- Each site charges (1.06-1.37 kWh, chargers busy 53-64 %), starting at about 17:30-17:50, after the first swaps
  there (mean first charging slot 18-22 of 48) [E].
- Reach: with four sites (one fewer than plan A) the north end of Central Park and the blocks along W 110th St are
  beyond 14 blocks (81 land points; with the Chelsea waterfront strip, 0.90 % of the land and about 1.3 orders per
  evening delivered there) [B, G]. The best layout serves 85.1 % of the orders delivered north of 59th St, 84.6 %
  south of 14th St and 84.3 % in between [G].
- Size polish: D49 and D55 lost a spare (D55 by D'Hondt, fewest swaps with 3 spares, 3.10; D49 to D05); with 2 spares
  they make 2.83 and 2.81 swaps (3.60 and 3.38 with 3) [C].
- Value: removal 379 (D50), 256 (D48), 230 (D49), 126 (D55); 991 USD/day together; **three of the four intervals
  include zero** (D48, D49, D55). Individually each northern site is a near-tie; this says nothing about removing
  all four at once (not priced).
- Robustness: every searched layout has 4 or 5 sites north of 59th St; D49 is in all six, D55 in four, D48 and D50
  only in the best [I].

**In one line.** One site next to each of the six entry points (riders swap soon after entering; these six are the
busiest and most valuable sites and get the extra spares); the other nine split between the dense East Village and
Midtown (five) and north of 59th St (four), where 41 % of the orders end; with its own connection every site charges
during the evening.

---

## 3. Comparison rows (each layout: 15 sites, 782,250 USD, 3 spares and 2 chargers per site unless stated)

| layout (plain name) | how it picks the 15 sites | regret in-sample, USD/day | regret held-out | served in / out | unserved orders per evening (in) | land beyond 14 blocks |
|---|---|---|---|---|---|---|
| best found | the search, then the size polish | 0 | 0 | 86.4 % / 85.4 % | 48.9 | 0.90 % |
| same sites, 3 spares each | the best locations before the polish | +638.1 +- 167.7 | +801.3 +- 294.0 | 84.9 / 83.2 | 53.8 | 0.90 % |
| spread rule | spread evenly: start at the candidate nearest the middle, then always add the candidate farthest from those chosen | +1,526.6 +- 315.8 | +2,145.2 +- 352.9 | 80.0 / 76.9 | 70.7 | 0.0 % |
| "15 units free" | the same search without fixing the number of sites, free to spend 782,250 USD on sites, spares or chargers (from D07 + D45): it still opened 15 sites but gave 13 of them one charger (777,050 USD spent) | +1,881.0 +- 546.9 | +1,785.9 +- 568.2 | 77.3 / 76.0 | 78.8 | 0.0 % |
| k-median | the classic facility-location layout: the 15 sites that minimise the expected orders' restaurant-to-nearest-site grid distance | +2,107.3 +- 519.4 | +2,419.1 +- 521.9 | 78.1 / 75.2 | 76.2 | 0.0 % |
| coverage rule | the 15 sites with the most demand nearby (expected orders, restaurant or customer, within 14 blocks) | +3,255.9 +- 698.6 | +3,694.6 +- 657.7 | 71.2 / 67.8 | 97.4 | 34.2 % |
| DOT-first | DOT pilot hubs and PEC sites first, ranked by demand nearby, filled by demand (at 15 all 15 are DOT sites) | +3,339.3 +- 1,027.8 | +4,064.1 +- 374.0 | 71.9 / 67.1 | 97.0 | 18.0 % |
| access rule | the 15 sites with the best inverse-distance access to restaurants (each expected order adds 1 / (1 + distance in blocks)) | +3,738.3 +- 298.2 | +3,970.6 +- 429.9 | 68.6 / 66.2 | 106.4 | 19.0 % |

All five rule layouts are the same site sets as in plan A (they do not depend on power). Other starts of the search
(each ended at 15 sites with 3 spares each, not polished): from the earlier best pair D07 + D45 +826.5 +- 274.3
in-sample, +837.2 +- 209.6 held-out; from the spread rule's best pair +756.6 +- 178.7 / +944.3 +- 555.1; from nothing
+1,254.7 +- 398.0 / +1,283.5 +- 195.2. Against the best locations with 3 spares (both unpolished) the first two are
ties (+188.3 +- 262.6 and +118.5 +- 240.7 in-sample; +35.9 +- 285.7 and +143.1 +- 565.5 held-out); only the start
from nothing is worse (+616.6 +- 486.7; +482.2 +- 183.3). They share 9, 8 and 10 of the best's 15 sites [H, I].

Reading the rows. Two groups: spread, "15 units free" and k-median cover all the land and cost +1,527 to +2,107;
coverage, DOT-first and access leave 18-34 % of the land out of reach (each misses nearly all of the Upper West Side
and of Battery Park City and the Financial District) and cost +3,256 to +3,738 [B]. Inside a group most differences
are not significant (k-median vs spread +580.7 +- 638.1 in-sample, +273.9 +- 350.1 held-out; "free" vs spread
+354.5 +- 618.2, -359.4 +- 430.4; coverage vs DOT-first -83.4 +- 713.3; access vs coverage +482.3 +- 533.7), with one
exception: k-median is dearer than "15 units free" (+226.3 +- 113.1 in-sample, +633.2 +- 140.4 held-out) [H]. The
losses are spread over the whole island, not one area: the coverage rule serves 69-70 % of the orders in each of the
three areas, the best layout 84-85 % [G]. What the regrets are made of: unserved orders (60 USD each) are 78-96 % of
every rule layout's regret (coverage rule 2,912.9 of 3,255.9), lateness most of the rest (231-505 USD/day); response
cost differs little (-180 to +106 USD/day) [N]. Order cost (unserved + response + lateness) is 96-97.5 % of every
15-site layout's cost; for the best layout: response 5,063.4, unserved 2,931.4 (48.9 orders), lateness 732.8, travel
144.6, set-up 197.85 (2.2 %), electricity 11.3 USD/day (25.6 kWh at 0.442 USD/kWh) [N].

---

## 4. Cost versus the number of sites

All points use the standard unit (3 spares, 2 chargers) at every site. **The curve is stitched from four search
paths** (`experiments/r8_k15.py` lines 1191-1208): k = 1 is the first site chosen by the search started from nothing;
k = 2-14 come from the search started at the earlier best pair D07 + D45 (k = 2 is that pair); k = 15 is the best
layout's sites with 3 spares each, the end point of a different search (started at the coverage rule's best pair
D18 + D23); k = 16-20 add one site at a time to those 15 (no swap passes). At the six k of the table the
plotted layout is the cheapest that any search path reached at that k on the six search evenings, but between them
the paths cross: at k = 12 the path from the spread rule's pair reached 10,870.4 against 11,915.6 for the plotted
path, at k = 14 9,898.3 against 10,271.1 (`search_summary.json` `restarts.*.path_k`). So it is a search path, not the
best cost per k; only the six table points were re-priced on 12 + 12 evenings.

| k | sites | cost in-sample [95 % CI] | served | cost held-out (served) | swaps | kWh | unserved orders | land beyond 14 blocks |
|---|---|---|---|---|---|---|---|---|
| 1 | D30 (grid cell, 5th Ave & W 31st St) | 18,280.8 [18,097.6, 18,464.1] | 10.3 % | 18,434.6 (8.7 %) | 6.7 | 2.33 | 288.1 | 78.1 % |
| 1 (ref.) | D23, DOT Site 34 | 18,182.6 [17,878.4, 18,486.7] | 10.7 % | 18,426.7 (8.9 %) | 6.4 | 2.32 | 286.8 | 79.5 % |
| 2 | D07 + D45 (earlier best pair) | 17,608.2 [17,346.7, 17,869.7] | 19.4 % | 17,597.3 (19.1 %) | 14.4 | 4.86 | 260.0 | 61.8 % |
| 5 | D07, D13, D34, D45, D51 | 15,567.4 [15,159.5, 15,975.3] | 40.8 % | 15,943.7 (38.0 %) | 32.9 | 11.29 | 193.3 | 23.2 % |
| 10 | D07, D09, D13, D22, D28, D34, D41, D45, D51, D54 | 12,447.3 [11,856.4, 13,038.2] | 67.8 % | 12,900.6 (64.3 %) | 58.6 | 19.84 | 108.9 | 4.9 % |
| 15 | best sites, 3 spares each | 9,719.5 [8,619.4, 10,819.6] | 84.9 % | 10,035.8 (83.2 %) | 78.7 | 25.56 | 53.8 | 0.90 % |
| 15 | best (polished sizes) | 9,081.4 [8,111.4, 10,051.3] | 86.4 % | 9,234.6 (85.4 %) | 79.2 | 25.62 | 48.9 | 0.90 % |
| 20 | best sites + D58, D17, D53, D11, D44 | 8,761.3 [7,730.2, 9,792.3] | 89.9 % | 8,695.8 (90.0 %) | 89.0 | 26.92 | 37.0 | 0.0 % |

Paired steps, in-sample (held-out): 1 to 2 sites -672.6 +- 249.5 (-837.3 +- 107.2); 2 to 5 -2,040.8 +- 227.1
(-1,653.5 +- 293.6); 5 to 10 -3,120.1 +- 223.1 (-3,043.1 +- 243.7); 10 to 15 -2,727.8 +- 540.7 (-2,864.8 +- 301.6);
15 to 20 -958.2 +- 179.5 (-1,340.0 +- 708.8). Per added site: about 673, 680, 624, 546, 192 USD/day, against a set-up
of 13.19 USD/day per site [H]. On the six search evenings the path beyond 15 saved 118, 423, 236, 154 and 76 USD/day
for sites 16-20. Twenty sites beat the polished 15 in-sample (-320.1 +- 195.7) but **not significantly held-out
(-538.8 +- 548.6)**; held-out the interval misses excluding zero by only 9.8 USD, and a charge of 3 USD or more per
rider who ends the evening below the reserve makes it exclude zero (-671.6 +- 464.8 at one order price, 60 USD;
section 5a). Fifteen is a policy target, not the best number of sites. D23 and D30 are a tie at k = 1
(-98.3 +- 188.3).

What the curve shows about power: with no shared limit the charging energy grows with the sites (2.3, 4.9, 11.3,
19.8, 25.6, 26.9 kWh at 1, 2, 5, 10, 15, 20 sites) and so do the swaps (about 6.2, 5.1, 4.0 and 2.1 per added site
for 2-5, 5-10, 10-15 and 15-20 sites): each new site adds its own charging, not only its spares (plan A: energy flat
at 7.6-7.7 kWh from 5 sites on, about 3 swaps per added site). The 1- and 2-site points are identical in both plans
(2 or 4 chargers stay below plan A's 2 kW cap) [M].

---

## 5. Caveats

**5.1 Rule-based lower level: the exact check (plan B power model) [P].**
What was checked: three new evenings (seeds 0-2: weekday, 1.25 orders per rider-hour, equal weights) with 16 riders and
80 orders each, built for the check (`records.jsonl` instance_built val_s00-s02); three 5-site layouts, every site the
standard unit (3 spares, 2 chargers); the same power model as plan B (validate argv `--grid-kw 1000`; 1.4 kW per site).
The layouts: **greedy5** = D07, D13, D36, D45, D51, found by the rule-based search at 16 riders from the earlier best
pair D07 + D45 (it added D36, then D51, then D13; `records.jsonl` validate_greedy steps); the **coverage rule** at 5
sites = D18, D23, D28, D29, D30; the **spread rule** at 5 sites = D02, D21, D30, D47, D58. For each layout and evening
the exact lower level (the grouped integer program; cache `formulation` aggregated) was solved by Gurobi with 1,800 s
and 3 threads, starting from the rule's schedule (MIP start accepted in all 9). The stage ran 20:27:10-20:51:21 UTC.

| layout | evening | rule, USD | exact optimum, USD | MIP gap | rule / exact | served, rule | served, exact | solve |
|---|---|---|---|---|---|---|---|---|
| greedy5 | 0 | 2,494.5 | 1,320.6 | 0.008 % | 1.889 | 81.25 % | 97.50 % | 181 s |
| greedy5 | 1 | 2,127.9 | 1,289.8 | 0 | 1.650 | 91.25 % | 98.75 % | 411 s |
| greedy5 | 2 | 2,780.1 | 1,258.4 | 0 | 2.209 | 78.75 % | 100 % | 204 s |
| coverage rule | 0 | 3,453.5 | 1,349.9 | 0 | 2.558 | 56.25 % | 97.50 % | 643 s |
| coverage rule | 1 | 3,137.7 | 1,363.0 | 0 | 2.302 | 65.00 % | 98.75 % | 880 s |
| coverage rule | 2 | 2,633.7 | 1,291.2 | 0 | 2.040 | 81.25 % | 100 % | 642 s |
| spread rule | 0 | 2,522.1 | 1,328.2 | 0 | 1.899 | 80.00 % | 97.50 % | 165 s |
| spread rule | 1 | 2,716.6 | 1,294.0 | 0 | 2.099 | 82.50 % | 98.75 % | 311 s |
| spread rule | 2 | 2,787.1 | 1,269.7 | 0.009 % | 2.195 | 80.00 % | 100 % | 733 s |

- **Optimality: 9 of 9 solved to optimality** (Gurobi status OPTIMAL; gap 0 in seven cells, 8.2e-5 and 9.5e-5 in two,
  inside Gurobi's default tolerance of 1e-4); 165-880 s each, below the 1,800 s limit; 9.0-11.6 million arcs,
  287,131-391,449 binary variables and 47,085-55,160 rows per program.
- **Ratio rule / exact optimum: 1.650-2.558, median 2.099** (the median cell is the spread rule on evening 1). Against
  the solver's bound the ratios are the same to within 0.0003.
- **Ranking (means of the three evenings, equal weights, = `rule_values` / `ilp_values`): the same order under both.**
  Rule: greedy5 2,467.5 < spread rule 2,675.3 < coverage rule 3,075.0. Exact: greedy5 1,289.6 < spread rule 1,297.3 <
  coverage rule 1,334.7. The exact lower level separates the layouts far less: +7.7 and +45.1 USD/day above greedy5
  (0.6 % and 3.5 %), against +207.8 and +607.5 under the rule (8.4 % and 24.6 %). Evening by evening the exact order is
  the same on all three evenings, the rule's on two (on evening 2 the rule finds the coverage layout cheapest: 2,633.7
  against 2,780.1 and 2,787.1).
- **Served share at 16 riders** (mean of the three evenings): rule 83.75 % (greedy5), 67.50 % (coverage rule), 80.83 %
  (spread rule); exact **98.75 % for all three**: the exact program leaves unserved only the orders that no rider can
  serve at all (2, 1 and 0 on the three evenings, cache `n_unservable`), whatever the layout.
- Where the rule loses (means per evening; `records.jsonl` price15 rows tagged validate_rule / validate_ilp): unserved
  orders 13.0 / 26.0 / 15.3 (greedy5 / coverage / spread) against 1.0 for every layout under the exact program;
  lateness 242.1 / 255.4 / 287.1 against 4.6 / 16.2 / 5.4 USD; response 1,339.5 / 1,159.0 / 1,361.5 against 1,116.0 /
  1,143.5 / 1,119.5 USD. Unserved orders make 61 %, 86 % and 62 % of the rule-minus-exact gaps (1,177.9 / 1,740.3 /
  1,378.0 USD/day). Swaps per evening: rule 20.3 / 16.7 / 20.3, exact 19.7 / 25.7 / 23.3; kWh: rule 6.20 / 5.19 / 6.16,
  exact 2.00 / 5.01 / 4.36.
- End of the evening at 16 riders: no rider ends below the reserve in the 9 rule schedules (their check families are
  empty; in all 45 rule evaluations at 16 riders, search included, one rider in one cell: D07, D11, D36, D45, D51,
  evening 2), and all 9 exact schedules pass every check (`check_ok`). The 5.6 riders per evening of 5.3 are a 64-rider
  effect that this check does not see.
- Plan A's check (`r8_k15/validate.json`; `r8_k15_n64/validate.json` is a byte-identical copy, the plan A run has no
  validate stage of its own) used the same three evenings (same demand md5) and the same greedy5 and spread layouts (its
  coverage layout was D07, D18, D19, D22, D23), under the shared 2 kW supply. For those two layouts both checks agree to
  within 0.3 USD on every evening (exact means 1,289.6 and 1,297.3 in both), so at 16 riders and 5 sites the power
  model hardly matters; its three coverage cells stopped at the time limit (gaps 0.3-1.3 %), hence 6 of 9 optimal
  there (ratio 1.64-2.21, median 1.90), 9 of 9 here. Do not quote plan A's check for plan B.

What the paper can say: "On three test evenings with 16 riders and five sites, the exact lower level was solved to
optimality for three layouts. The rule-based riders cost 1.65 to 2.56 times the optimum (median 2.10), but rank the
three layouts in the same order." Limits to state with it: 16 riders, 5 sites, 3 evenings and 3 layouts; nothing is
solved exactly at 64 riders and 15 sites; and the exact lower level separates the layouts much less than the rule (7.7
and 45.1 against 207.8 and 607.5 USD/day, i.e. 4 % and 7 % of the rule's differences), so the rule's regrets of
section 3 should not be read as regrets under the exact lower level. The 15 sites stay "the best layout found under
rule-based riders".

**5.2 Three rule details that shape the per-site numbers.**
- Charging: each site charges by its own recent swaps, limited only by its 2 chargers; with no shared supply the
  rule's site-number order plays no role (plan A's artifact is gone) [E, F].
- Early swaps: 33 % of the swaps happen above a quarter of the battery, when a rider is too low to take the next order
  and still reach a site [D].
- Waiting: at the six gateway sites riders wait 31-79 minutes on average for a charged battery; two chargers and 3-4
  spares are the binding resources there, not power (shelves empty in 34-40 of 48 slots) [C].

**5.3 Riders who end the evening without the end-of-evening reserve (paper (10), terminal row).** In-sample 5.60 riders
per evening (2-10 on every one of the 12 evenings), held-out 6.07 (3-8, every evening); **more than plan A** (2.93 and
3.24). They are not out of reach of a site: every one of them ends the evening standing at an open site with 0 or 1 of
24 battery levels, below the 2-level reserve that a terminal arc needs, queued there since 19:14 on average (19:18
held-out) for a charged battery that did not come before 20:00; most at D12 Essex Market (1.4 per evening), D55 (0.6),
D18 (0.5), D07, D38, D35, D49 (0.4 each) [J]. More riders keep working into the last hour in plan B (18.7 swaps between
19:00 and 20:00, plan A 6.7) [D]. The rule reports this instead of preventing it (`ok_modulo_report_only` true in all
2,093 checked cells of the 24 evenings; 1,715 of them have such riders; at 16 riders 1 of the exact check's 45 rule
cells), and the cost does not charge it (`C_dummy_terminal` = 0). Write "checked against the same constraints; the
end-of-evening condition is reported, not enforced", not "feasible". Plan A's sheet calls these riders "out of reach of
an open site"; that wording is wrong there too (all 33 and 38 plan A riders also end at an open site with 0-1 levels).
No comparison layout has more such riders than the best, and charging them one or two order prices changes no
comparison with the best (section 5a).

**5.4 Power model.** Plan B gives each site its own 1.4 kW connection (paper (15)) and lifts the shared feeder (16) to
1000 kW. With at most 2 chargers per site (0.67 kW) neither limit binds, so plan B is in effect "power is not a limit;
each site has two chargers". The network draws up to 10 kW at once, five times the 2 kW of the 1-3 site study. The
paper's Section V-A still says "all sites share one 2 kW feeder" (paper not edited in this workflow).

**5.5 No bound.** C(59,15) = 39,895,566,894,540 location sets; no lower bound or optimality gap is claimed at 15
sites. Reported instead: the best layout found, the cost-versus-sites path, and paired regrets against rule layouts.

**5.6 Near-ties inside the intervals.**
- Two other search starts ended at 15-site layouts (8 and 9 sites shared) that, with 3 spares everywhere, tie with the
  best locations (+188.3 +- 262.6, +118.5 +- 240.7 in-sample). Only the best start's layout was size-polished, and the
  polish gives most of the lead (638.1 of the 757-827 USD/day by which the polished best beats those two layouts).
- The polish stopped at its limit of three transfer rounds while every round still improved (search evenings 9,395.1
  after the D'Hondt step, then 9,052.3, 8,964.8, 8,851.4; `--polish-rounds` default 3), so further spare moves might
  lower the cost; the layout was chosen on 6 evenings and re-costed on 12 + 12.
- Robust sites: D05, D07, D34, D35, D41 and D49 are in all six searched layouts; D18, D48 and D50 appear only in the
  best. Explain by cluster and area, not by corner (each gateway is served in every searched layout, by one of a few
  nearby candidates) [I].
- Removal intervals that include zero: D41, D48, D49, D55.
- 20 sites vs the polished 15: significant in-sample, not held-out (section 4); held-out it becomes significant once
  each rider who ends below the reserve costs 3 USD or more (section 5a). D23 vs D30 at one site: a tie.
- The best layout's own interval is wide (+-970.0); differences between layouts are paired and much tighter.

**5.7 USD not comparable with the 1-3 site study.** Eight times the riders and orders (64 vs 8 riders; 256-384 vs
32-48 orders); a rule-based lower level vs the exact integer program; and now a different power model (the 1-3 site
study shares one 2 kW feeder). The same layouts cost far more and serve far less: DOT Site 34 alone 1,085.87 USD/day,
77.5 % served (8 riders, exact) vs 18,182.6, 10.7 % (64 riders, rule); the best pair 716.85, 98.3 % vs 17,608.2,
19.4 %. Same prices (60 USD per unserved order, 18 USD/h response, 15 USD/h lateness), same set-up per site (13.19
USD/day), same candidates, data and entry points. Only differences inside one study mean something.

**5.8 Candidate realism.** Six sites are grid cells, not addresses (D07, D09, D38, D41, D48, D49). PEC sites are not
final (about 25 of 50 will be kept): **Community Board 4 "strongly" opposes PEC Site 29 = D35**, the Lincoln Tunnel
gateway (letter 2026-07-17), although D35 is in all six searched layouts; PEC Site 34 = D23 was presented to CB3
(2026-06-09) without a vote. The pilot hubs D12 (Essex Market) and D18 (Cooper Square) ran swapping until February
2025; their current status is unknown (Cooper Square's plaza is proposed again as PEC Site 36). The W 92nd St dock D50
is DOT-announced but not confirmed as charging (GBFS is_charging false on 2026-10-21). D05 opened in April 2026 and has
been fully operational since about June 2026; D28 (Swobbee, 836 6th Ave) is active (`data/raw/dot_candidate_sites.csv`).

**5.9 Reporting traps.** Do not copy "go: 48 riders / 240 orders" (0.11). Cite the feeder as (16), not (21) (0.12). In
`final_summary.json`, `regret_ci.mean` leaves out set-up differences (it differs from `regret` for the V(k), prod and
"15 units free" rows by the set-up gap); quote `regret` with `regret_ci.half`, as RESULTS.md does. RESULTS.md calls the
V(k) table a "greedy path"; it is stitched (section 4). The search stage ran with `--ignore-gates`, but no dry-run gate
failed, so it changed nothing. `paper_itsc/figs/map15/layout.json` now holds plan B: the old `r8_facts.py` read it and
would mix plan B's sites with plan A's cache (it now fails with a KeyError); the new script reads each run's own file.
The exact check builds its own 16-rider evenings with the seeds 0-2 of the final table: in `cache/index.jsonl` a row
with seed 0-2 and at most 5 sites may be a 16-rider cell (54 such rows, 9 of them exact solves); match rows by
`demand_md5`, as the script now does (no number reported earlier in this sheet changes). `r8_k15_n64/validate.json` is
a copy of the 48-rider run's check, not a plan A check of its own.

---

## 5a. Riders who end the evening below the reserve: every layout, and what charging for them would change

Why this matters: the rule lets some riders end the evening below the 2-level reserve of the paper's terminal row (10),
and the cost charges nothing for them (5.3). If the best layout had more of them than the layouts it is compared with,
part of its lead could come from this free pass.

How it was counted [O]: from the cached schedules of every layout of the final table, on the 12 in-sample and the 12
held-out evenings, a rider counts when it has no terminal arc at an open site (the check's end-of-evening family '(9)',
as in [J]). The count equals the cells' `check_families` count on all 24 evenings of all 20 rows, and in every layout
every such rider stands at an open site at 20:00 with 0 or 1 of 24 levels (no terminal arc at a closed site, no dummy
arc). A charge of c USD per such rider per evening is added to that evening's cost, on the same schedules: the riders
do not change what they do, so this is a charge after the fact, not a re-run with the reserve enforced. Regret = the
paired stratified difference against the best, as in RESULTS.md (`bilevel.stratified_ci`, 6 strata of 2 evenings).
c = P = 60 USD, the price of one unserved order (the paper's parameter table `tab:notation`, P_i = 60;
`components.unserved` / `n_unserved` in the cache), and c = 2 P = 120 USD.

**Table 5a-1. Per evening, p-weighted, in-sample / held-out.** "Never swap" = riders (of 64) without a swap all
evening; "level at a swap" = battery level (of 24) when a swap starts, averaged over the swaps.

| layout | below the reserve at 20:00 | never swap | swaps | level at a swap |
|---|---|---|---|---|
| **best** | **5.60 / 6.07** | **4.69 / 4.24** | 79.2 / 79.7 | **5.09 / 5.00** |
| same sites, 3 spares each (= search start D18 + D23 = 15 sites of the V(k) table) | 4.64 / 5.40 | 6.02 / 6.29 | 78.7 / 77.1 | 5.00 / 4.96 |
| search start D07 + D45 | 3.81 / 5.52 | 6.24 / 6.88 | 77.7 / 76.8 | 4.89 / 4.82 |
| search start D30 + D38 | 5.52 / 4.29 | 6.81 / 7.60 | 78.1 / 75.6 | 4.93 / 4.84 |
| search start from nothing | 5.60 / 5.48 | 8.57 / 8.50 | 76.1 / 75.5 | 5.04 / 4.98 |
| spread rule | 4.21 / 3.24 | 9.64 / 11.55 | 72.9 / 72.8 | 4.69 / 4.53 |
| "15 units free" | 4.19 / 4.45 | 14.00 / 13.90 | 65.9 / 66.4 | 5.03 / 4.85 |
| k-median | 4.83 / 3.67 | 13.02 / 14.10 | 71.4 / 70.3 | 4.78 / 4.69 |
| coverage rule | 1.45 / 1.40 | 12.48 / 15.12 | 67.4 / 64.9 | 5.21 / 5.14 |
| DOT-first | 2.95 / 1.24 | 17.69 / 20.98 | 67.4 / 64.2 | 4.50 / 4.41 |
| access rule | 2.57 / 2.43 | 19.38 / 20.79 | 63.5 / 61.9 | 4.87 / 4.72 |
| 20 sites (best sites + D58, D17, D53, D11, D44) | 3.43 / 3.86 | 4.12 / 3.90 | 89.0 / 89.6 | 4.86 / 4.66 |
| 10 sites | 3.81 / 4.50 | 14.83 / 16.29 | 58.6 / 57.0 | 5.25 / 5.15 |
| 5 sites | 1.19 / 0.76 | 32.29 / 34.14 | 32.9 / 32.1 | 6.01 / 6.42 |
| 2 sites D07 + D45 (= prod_m2) | 0.00 / 0.24 | 49.64 / 49.86 | 14.4 / 14.1 | 7.45 / 7.32 |
| 1 site D23, DOT Site 34 (prod_m1) | 1.50 / 1.43 | 57.57 / 57.50 | 6.4 / 6.5 | 5.58 / 5.72 |
| 1 site D30 | 4.60 / 5.26 | 57.31 / 57.45 | 6.7 / 6.5 | 5.36 / 5.77 |

Reading it: the best layout has the most such riders of all 15-site layouts (in-sample tied with the search start from
nothing at 5.60; held-out 6.07 against at most 5.52), so a charge for them can only narrow its lead. The rule layouts
have fewer of them (1.2-4.8) but two to five times as many riders who never swap (9.6-21.0 of 64, against 4.2-4.7).
The battery level at a swap hardly depends on the layout among the 15-site layouts (4.4-5.2 of 24, about a fifth of a
full battery); with 1-5 sites it is higher (5.4-7.5). In the best layout 66.7 % of the swaps (69.3 % held-out) start at
6 levels or fewer [D, O].

**Table 5a-2. Regret against the best, USD/day (+- half-width of the paired 95 % interval), with no charge, with P = 60
and with 2 P = 120 USD per rider below the reserve; and the charge per rider (USD) at which the mean regret would
reach zero and at which its interval would first include zero.** The "no charge" values reproduce RESULTS.md's regret
columns.

| layout | in-sample: none / P / 2 P | held-out: none / P / 2 P | mean reaches 0 at (in / out) | interval reaches 0 at (in / out) |
|---|---|---|---|---|
| same sites, 3 spares each | 638.1 +- 167.7 / 581.0 +- 286.4 / 523.8 +- 440.4 | 801.3 +- 294.0 / 761.3 +- 358.5 / 721.3 +- 437.1 | 670 / 1,202 | **143 / 252** |
| search start D07 + D45 | 826.5 +- 274.3 / 719.3 +- 264.6 / 612.2 +- 266.0 | 837.2 +- 209.6 / 804.3 +- 239.4 / 771.5 +- 317.1 | 463 / 1,529 | 283 / 313 |
| search start D30 + D38 | 756.6 +- 178.7 / 752.3 +- 155.0 / 748.0 +- 250.1 | 944.3 +- 555.1 / 837.2 +- 512.6 / 730.0 +- 476.7 | 10,593 / 529 | 323 / 291 |
| search start from nothing | 1,254.7 +- 398.0 / 1,254.7 +- 321.9 / 1,254.7 +- 263.0 | 1,283.5 +- 195.2 / 1,247.8 +- 214.7 / 1,212.1 +- 261.5 | never (same mean count) / 2,156 | 924 / 627 |
| spread rule | 1,526.6 +- 315.8 / 1,443.7 +- 328.7 / 1,360.9 +- 403.7 | 2,145.2 +- 352.9 / 1,975.2 +- 375.8 / 1,805.2 +- 413.0 | 1,105 / 757 | 389 / 481 |
| "15 units free" | 1,881.0 +- 546.9 / 1,796.8 +- 593.8 / 1,712.5 +- 654.9 | 1,785.9 +- 568.2 / 1,688.7 +- 495.3 / 1,591.6 +- 433.2 | 1,339 / 1,103 | 493 / 649 |
| k-median | 2,107.3 +- 519.4 / 2,061.6 +- 491.5 / 2,015.9 +- 468.3 | 2,419.1 +- 521.9 / 2,274.8 +- 531.0 / 2,130.5 +- 543.3 | 2,766 / 1,006 | 1,372 / 684 |
| coverage rule | 3,255.9 +- 698.6 / 3,007.4 +- 697.9 / 2,758.8 +- 715.4 | 3,694.6 +- 657.7 / 3,414.6 +- 659.0 / 3,134.6 +- 678.0 | 786 / 792 | 511 / 546 |
| DOT-first | 3,339.3 +- 1,027.8 / 3,180.7 +- 890.8 / 3,022.2 +- 774.3 | 4,064.1 +- 374.0 / 3,774.1 +- 343.9 / 3,484.1 +- 320.9 | 1,264 / 841 | 697 / 726 |
| access rule | 3,738.3 +- 298.2 / 3,556.8 +- 318.0 / 3,375.4 +- 347.1 | 3,970.6 +- 429.9 / 3,752.0 +- 370.1 / 3,533.5 +- 323.2 | 1,236 / 1,090 | 901 / 831 |
| 20 sites | -320.1 +- 195.7 / -450.1 +- 252.0 / -580.1 +- 353.9 | -538.8 +- 548.6 / **-671.6 +- 464.8 / -804.5 +- 412.7** | never (the lead of 20 sites grows) | in-sample significant up to 3,456; held-out **significant from 3** |
| 10 sites | 3,365.9 +- 409.0 / 3,258.8 +- 375.9 / 3,151.6 +- 350.7 | 3,666.1 +- 214.2 / 3,571.8 +- 265.2 / 3,477.5 +- 320.3 | 1,885 / 2,333 | 1,263 / 1,339 |
| 5 sites | 6,486.0 +- 570.5 / 6,221.7 +- 515.5 / 5,957.4 +- 470.8 | 6,709.2 +- 223.4 / 6,390.6 +- 188.5 / 6,072.0 +- 169.8 | 1,472 / 1,264 | 1,158 / 1,079 |
| 2 sites D07 + D45 | 8,526.8 +- 763.9 / 8,191.1 +- 701.6 / 7,855.4 +- 656.8 | 8,362.7 +- 404.8 / 8,012.7 +- 382.5 / 7,662.7 +- 364.2 | 1,524 / 1,434 | 1,158 / 1,295 |
| 1 site D23, DOT Site 34 | 9,101.2 +- 808.1 / 8,855.5 +- 715.2 / 8,609.7 +- 653.6 | 9,192.2 +- 425.7 / 8,913.6 +- 384.6 / 8,635.1 +- 348.5 | 2,222 / 1,980 | 1,380 / 1,688 |
| 1 site D30 | 9,199.4 +- 945.0 / 9,139.4 +- 834.6 / 9,079.4 +- 737.2 | 9,200.0 +- 329.6 / 9,151.4 +- 322.9 / 9,102.9 +- 352.9 | 9,199 / 11,365 | 2,866 / 3,487 |

**Answer: no, not at a plausible charge; one conclusion about the number of sites changes.**
- At P and at 2 P every 15-site layout of the table stays significantly dearer than the best, in-sample and held-out:
  no regret changes sign and no interval reaches zero (script: "comparisons whose sign or significance differs from
  pen 0: none", except 20 sites). Their regrets shrink by at most 497 USD/day in-sample (coverage rule at 2 P) and 580
  held-out (DOT-first at 2 P).
- To reverse a mean ranking the charge would have to be at least 463 USD per rider (7.7 unserved orders; the search
  start D07 + D45, in-sample); for the six rule layouts at least 757 USD (12.6 orders; the spread rule, held-out).
- The most fragile result is the gain of the size polish (the best against the same sites with 3 spares each): its
  interval first includes zero at 143 USD per rider in-sample (2.4 unserved orders) and 252 held-out (4.2). At 2 P it is
  523.8 +- 440.4 in-sample, so it still holds at two order prices, by 83 USD. The two other search starts that tie
  with the best sites (D07 + D45 and D30 + D38) lose significance against the best at 283-323 USD per rider in-sample
  and 291-313 held-out.
- Inside the groups: the six rule layouts keep their in-sample order at P and 2 P (spread < "15 units free" < k-median
  < coverage < DOT-first < access). Held-out at 2 P, DOT-first and the access rule swap places (access minus DOT-first
  -93.5 +- 369.8 with no charge, +49.3 +- 290.6 at 2 P: a tie either way), and the search starts D07 + D45 and D30 + D38
  swap places in both samples (in-sample +69.8 +- 168.9 with no charge, -135.9 +- 243.9 at 2 P: a tie). The one
  significant difference inside a group stays: k-median is dearer than "15 units free" (in-sample +264.8 +- 172.5 at P,
  +303.4 +- 271.2 at 2 P; held-out +586.1 +- 132.7 and +538.9 +- 202.3).
- **What changes: 20 sites against the polished 15.** Held-out the difference is -538.8 +- 548.6 with no charge (the
  interval misses excluding zero by 9.8 USD); with a charge of 3 USD or more per rider it excludes zero: -671.6 +- 464.8
  at P and -804.5 +- 412.7 at 2 P (in-sample -450.1 +- 252.0 and -580.1 +- 353.9). With any charge of 3 USD or more the
  20-site layout is significantly cheaper than the polished 15 in both samples, which strengthens "15 is a policy
  target, not the best number of sites" (section 4).
- Plan A (`--run r8_k15_n64`, same section [O]): no comparison changes sign or significance at P or 2 P either.

Sentence the paper could use: "Some rule-based riders end the evening below the battery reserve, waiting at a site for
a charged battery: 5.6 per evening with the best layout and 1.5 to 5.6 with the other 15-site layouts. Charging each of
them the price of one or two unserved orders changes none of the comparisons with the best layout."

---

## 6. Plan A versus plan B (what changes when every site has its own connection)

| | plan A (shared 2 kW) | plan B (own connection, result of record) | source |
|---|---|---|---|
| power that can charge at once | 2 kW = 6 of the 30 chargers; at the cap in 45-46 of 48 slots | no binding limit; up to 10 kW when all 30 chargers run (p-weighted evening peak 9.8 kW), evening mean 6.4 kW | [E] |
| coverage-rule layout (same 15 sites, same evenings) | 13,223.8 USD/day, 62.6 % served, median 3.0 swaps per site, 7.63 kWh | 12,337.3, 71.2 %, median 4.02, 20.70 kWh; paired -886.5 +- 218.7 | `dryrun.json`, [M] |
| the five rule layouts (same sites) | 11,878-13,751 USD/day, 59.5-70.4 % served | 788-1,270 USD/day cheaper each (every interval excludes zero), 7.6-9.6 points more served | [M] |
| same 5-site layout (D07, D13, D34, D45, D51) | 15,824.5, 36.2 % | 15,567.4, 40.8 %; paired -257.1 +- 52.5 | [M] |
| 1 and 2 sites | identical in both plans (2 or 4 chargers stay below 2 kW) | | [M] |
| best found | 11,210.5 [10,338.1, 12,082.9], 72.9 % (held-out 11,464.7, 70.3 %) | 9,081.4 [8,111.4, 10,051.3], 86.4 % (held-out 9,234.6, 85.4 %) | final_summary |
| its sites | 6 S14 / 4 in 14-59 / 5 N59 | 6 / 5 / 4; **6 sites in common** (D05, D07, D12, D38, D49, D55) | [A, I] |
| a site at each of the six entry points | yes, 0.26-0.91 km (Manhattan Br D11, Lincoln D33) | yes, 0.26-0.91 km (Manhattan Br D09, Lincoln D35) | [I] |
| swaps / riders never swapping / unserved orders | 56.7 / 16.5 / 92.9 per evening | 79.2 / 4.7 / 48.9 | [D, N] |
| charging energy | 7.68 kWh; 5 sites above 0.1 kWh, three (D05, D07, D11) buy 93 % | 25.62 kWh; all 15 sites charge (1.06-2.40 kWh each) | [C, E] |
| electricity cost | 3.4 USD/day | 11.3 USD/day | [N] |
| regret of the rule layouts against the best | +668 to +2,540 | +1,527 to +3,738 (1.5-2.7 times plan A's) | final_summary |
| riders ending without the reserve, queued at a site | 2.93 per evening (held-out 3.24) | 5.60 (6.07) | [J] |
| land beyond 14 blocks of the best | 0.04 % | 0.90 % | [B] |
| ranking of 19 layouts priced in both runs (6 search evenings) | | all cheaper in plan B (by 383-1,735 USD/day); Spearman rank correlation 0.865 | [M] |

**The plan A site-number artifact, seen in identical layouts.** Plan A's rule hands the shared 2 kW (exactly six
chargers, i.e. the chargers of three sites) to the open sites in id order. In the coverage-rule layout, under plan A
only the first three sites by id (D07, D13, D14) make about 7 swaps and buy 2.25-2.42 kWh; sites 4-15 hand out their
3 spares and buy at most 0.27 kWh. Under plan B the Lincoln Tunnel gateway D33 (12th by id) makes 6.83 swaps and buys
2.34 kWh (plan A: 3.00 and 0.07) and the Queensboro gateway D45 (15th) 7.24 and 2.43 (plan A: 3.00 and 0.03). In the
5-site layout the first three sites are identical in both plans, while D45 (4th by id) goes from 3.00 swaps and 0.21
kWh to 7.00 and 2.42 [M]. So plan A's "three southern sites charge, the others hand out spares" was the charging
order, not demand; plan B removes it, and the gateway pattern (one site per entry point) survives in both.

**Sentence the paper could use (power sensitivity).** "With one 2 kW supply shared by all fifteen sites, as in the
one-to-three-site study, the same rule-based layouts cost 790 to 1,270 USD per day more and serve 8 to 10 percentage
points fewer orders than with a separate connection at each site; because our rule-based riders hand a scarce shared
supply to the sites in a fixed order, part of this gap reflects that rule rather than the supply limit itself."
(Numbers: the five rule layouts in [M], in-sample, paired; each interval excludes zero. Do not compare the two best
layouts in this sentence: they come from two separate searches and are not paired.)

---

## 7. Draft interpretation paragraph (plain language, about 150 words)

> **Why these 15 sites.** Riders enter Manhattan over four bridges and through two tunnels with a quarter to half a
> battery, so many swap soon after they arrive. The best layout therefore puts a site within 1 km of every entry
> point: City Hall Park (Brooklyn Bridge), Chinatown (Manhattan Bridge), Essex Market (Williamsburg Bridge),
> Greenwich Village (Holland Tunnel), Ninth Avenue at 42nd Street (Lincoln Tunnel) and East 53rd Street (Queensboro
> Bridge). These six are the busiest sites (6.5 to 8 swaps each per evening); closing any one of them would add 630
> to 1,270 USD to the daily cost. The other nine follow the orders: 70 % of the deliveries end north of 14th Street,
> and riders ride to a site only from within 14 blocks, so five sites sit in the dense East Village and Midtown and
> four north of 59th Street. Every site has its own power connection, so all fifteen charge batteries during the
> evening.

(About 150 words. Numbers: entry-point distances 0.26-0.91 km, Table 1a; swaps 6.52-8.14 and removal 628-1,272,
Table 1b; 70.6 % of deliveries north of 14th St (30.0 % + 40.6 %), section 2; 14 blocks, paper Section II-B;
charging of every site, Table 1b and [E]. If the lead prefers to mention the spares: "the four busiest gateway sites
also get a fourth spare battery".)

---

## 7a. Compute of the useful runs (r7i.4xlarge on demand, 1.0584 USD/h)

| run | stage | hours | USD |
|---|---|---|---|
| plan B (r8_k15_sp) | instances: the 24 evenings of plan A reused (hard-linked, 0 built) | 0.0000 | 0.0001 |
| | dry run | 0.0482 | 0.0510 |
| | search: 1,578 lower-level evaluations (9,170 quick screening scores) | 1.2649 | 1.3388 |
| | final table, held-out, cost-versus-sites, remove-one: 468 evaluations | 0.2987 | 0.3162 |
| | exact check (validate): 3 evenings of 16 riders built, 45 rule evaluations, 9 exact solves; 20:27:10-20:51:21 UTC | 0.4030 | 0.4266 |
| plan B total | | **2.015** | **2.133** |
| plan A (r8_k15_n64) | | 2.734 | 2.894 |
| 48-rider run (r8_k15), where plan A's exact check ran | | 1.371 | 1.451 |
| plan A with the 48-rider run | | 4.106 | 4.345 |
| all three folders | | 6.120 | 6.478 |

In the plan B search, one lower-level evaluation took 17.8 s on average (longest 39.5 s, worker memory at most 2.3 GB).
In the exact check the 9 integer programs ran 4 at a time with 3 threads each, 165-880 s apiece (1,299 s for the batch,
worker memory at most 2.7 GB; `records.jsonl` cell_batch validate_ilp). RESULTS.md's cost table: 2.01 h, 2.13 USD.

---

## 8. Sources (one line per number group)

- S1 `cloud_results/ebike_swap_sim/outputs/r8_k15_sp/final_summary.json`: `in_sample` / `held_out` (every layout's V, CI, served, swaps `n_swaps_mean`, kWh `kwh_mean`, components; unserved orders = `components.unserved` / 60), `regret_in` / `regret_out` (`regret`, `regret_ci.half`), `vk`, `site_table` and `remove_one` (removal values and CIs), investment 782,250 and 777,050 ("15 units free").
- S2 `.../r8_k15_sp/RESULTS.md`: the same tables in readable form; power header (1000 kW, 1.4 kW); the stale "go: 48 riders / 240 orders" line; the exact-check table (nine rows, ratio median 2.099, 9 of 9 OPTIMAL); cost per batch (2.01 h, 2.13 USD).
- S3 `.../r8_k15_sp/site_stats.csv`: Table 1b swaps and CIs, orders <= 1 km, busy share, kWh, wait, slots without a charged battery, removal and CI; totals 79.19 swaps, 25.62 kWh, busy 0.518-0.997.
- S4 `.../r8_k15_sp/layout.json`: sites and sizes, grid_kw 1000, site_kw 1.4, n_bikes 64, n_orders 320, V 9,081.4 and CI, served 0.864, V_out 9,234.6 and CI, best restart CSCD_best2, V on the search evenings 8,851.4.
- S5 `.../r8_k15_sp/search_summary.json`: `restarts` (layouts, values and `path_k` of the four starts), `best_locations` 9,489.8 and `best` 8,851.4 (search evenings), `polish_log` (D'Hondt 9,395.1; transfers D34 to D38 9,052.3, D49 to D05 8,964.8, D28 to D35 8,851.4), `vk_layouts`, `extension_path` (9,489.8 to 8,482.8), `free`, `n_cells` 1,578, `proxy_calls` 9,170, `cell_s_mean` 17.83, `cell_s_max` 39.52, `worker_rss_gb_max` 2.31.
- S6 `.../r8_k15_sp/dryrun.json` (coverage-rule layout 12,337.3, served 0.712, median 4.02, gates, stale recommendation, `n_arcs` 266-680 million) and `.../r8_k15_n64/dryrun.json` (13,223.8, 0.626, median 3.0).
- S7 `.../r8_k15_sp/cost.jsonl` (end rows, the validate row included: hours and USD of 7a; argv `--grid-kw 1000`, `--n-bikes 64`, search `--ignore-gates`), `wall_time.json`, `records.jsonl` (`instances_plan` n_to_build 0; validate builds 3 instances of 16 riders), `cloud_lanes_k15sp/lanes.txt` (instances hard-linked from plan A; lane order; "constraint (21)").
- S8 `.../r8_k15_sp/candidates.csv` (byte-identical to plan A's): ids, classes, coordinates, labels (D18 also PEC Site 36; D50 "DOT-announced - UNCERTAIN"); `data/raw/dot_candidate_sites.csv` `status_date` for D004 (D05), D006 (D12), D014 (D18), D018 (D23), D022 (D28), D026 (D34), D029 (D35, CB4 letter), D039 (D55), D043 (D50).
- S9 `.../r8_k15_n64/` (plan A): `final_summary.json`, `site_stats.csv`, `dryrun.json` for the plan A column of section 6; `.../r8_k15/validate.json` for plan A's exact check.
- S10 `notes/verify/r8_facts.py` output for plan B (default run), by label: [A] Table 1a geography, entry-point distances, areas, classes and DOT counts, restaurants by area (box 11,377; band 11,070); [B] land beyond 14 blocks for every layout and k, the two uncovered strips of the best layout with their extent, distance statistics (2.53, 0.86, 0.617); [C] per-site rider origins, steps, the check against `site_stats.csv`, area sums (swaps 39.86 / 25.02 / 14.31, kWh 12.76 / 8.01 / 4.85, removal 5,774.1 / 2,092.1 / 991.2), the six gateway sites (45.05 swaps, 13.93 kWh, removal 6,041.3, wait 31.1-78.8 min, 33.9-39.8 empty slots), riders by entry point (Queensboro 15.02 ... Holland 11.50), swaps per site with 3 spares on 6 and 12 evenings; [D] swaps by hour and area, first swaps, never-swapping riders, swap levels and their mean; [E] power settings, network draw per evening, per-site steps, slots with one or both chargers running, first charging slot, sites that charge; [F] the small layouts D07 + D45 and V(k=5) (the order effect is reported only where a shared supply binds: plan A); [G] rebuilt orders (3,192 of 3,192 served deliveries match), pickups and deliveries by area, served share by area for eight layouts, orders delivered beyond 14 blocks of every open site; [H] paired stratified differences and the regret check (19 of 19 reproduce); [I] site overlap across searched layouts, sites by area, nearest site to each entry point for eleven layouts; [J] '(9)' riders per evening and per layout, their battery level, site and waiting time at 20:00, checked cells of the 24 evenings (2,093, 1,715 with '(9)') and of the exact check's evenings (45, 1); [K] cost rows of the three folders and C(59,15); [L] street hints for the grid cells and the uncovered strips; [M] the same layouts under both power models, per-site swaps and kWh by id position, rank correlation; [N] cost components and regret decomposition; [O] for every row of the final table, in-sample and held-out: riders below the reserve at 20:00 (schedule count = check_families count, all at an open site, level 0-1), riders who never swap, swaps, level at a swap, regrets against the best with no charge / P / 2 P, the charge per rider at which a mean regret reaches zero and at which its interval stops excluding zero, the order of the 15-site layouts, six pairs inside the groups; [P] the exact check: nine rows, ratio, gaps, solve times and sizes, means and order per evening under both lower levels, served shares, cost components, end-of-evening riders at 16 riders.
- S11 `notes/verify/r8_facts.py --run r8_k15_n64`: the plan A column of section 6 and the plan A side of [J] (33 and 38 rider-evenings, all at an open site) and [M]; every number of `notes/r8_results_facts_planA.md` derived by the old script reproduces.
- S12 code: `ebike_swap_sim/ebike_swap_sim/baseline.py` (`_step9_charging`: per-site cap min(C_j, floor(P_j / p_ch)), shared group "allocated in facility order"); `config.py` `energy_calibration('ebaas')` (p_ch 0.333 kW, 24 levels of 25 Wh, reserve 2 levels); `arcs.py` (terminal arc only if q >= g(v, j) + q_res); `evaluate.py` (`check` family '(9)', `site_metrics` definitions); `sites_nyc.py` (`MANHATTAN15_PARAMS` P_kw 1.4, grid_sites_kw 2.0; `SIZE_MENUS` SC spares 2-4, chargers 1-2; `scenario_design`); `experiments/r8_k15.py` (`--grid-kw` lines 545-548 and 1546-1547, `polish_sizes` lines 1026-1100, V(k) assembly lines 1191-1208, label line 910, `stage_validate` lines 936-1020).
- S14 exact check: `.../r8_k15_sp/validate.json` (nine rows: rule total, exact incumbent and bound, gap, status, ratio, served shares, solve time, arcs, binaries; `rule_values` / `ilp_values`; ratio and gap medians), `records.jsonl` validate rows (instance_built val_s00-s02; validate_greedy search steps from D07 + D45; validate_plan; price15 rows tagged validate_rule / validate_ilp with served share, swaps, kWh and cost components; cell_batch validate_ilp 1,299 s), `cache/index.jsonl` rows with policy ilp (formulation aggregated, MIP start = the rule schedule, accepted; check_ok; n_unservable; n_rows) and the 45 rule rows on the 16-rider evenings; `cost.jsonl` validate argv (`--grid-kw 1000`, `--validate-threads 3`, `--validate-workers 4`) and end row; plan A's check `.../r8_k15/validate.json` (byte-identical copy in `.../r8_k15_n64/`).
- S13 paper: `paper_itsc/sections/03_model.tex` (rows (9), (10), (15), (16); 14-block approach rule), `05_data.tex` (Section V-A: 2 kW feeder text, 0.442 USD/kWh), `06_results.tex` (1-3 site numbers 1,085.87 / 77.5 %, 716.85 / 98.3 %), `main.aux` (equation numbers); `paper_itsc/figs/site_table.tex` (regenerated for plan B, consistent with Table 1a-1b).
