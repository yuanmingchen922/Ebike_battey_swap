# DOT-based candidate sites for the Manhattan siting study

Built 2026-10-21. Files:

- Data: `data/raw/dot_candidate_sites.csv`. It has 61 Manhattan sites, IDs D001-D061 ordered south to north. The columns are `id, name, address, lat, lon, site_type, operator, status_date, source_url, coord_method, verdict, angle, in_study_region`.
- Map: `notes/figs/dot_candidate_sites.png`
- Build scripts (outside the repo): `.../scratchpad/dotbuild/records.py`, `build.py`, `plot.py`

No optimisation was run.

## How the table was built

1. **Verification.** Five search angles produced the records: DOT pilot programme, NYSERDA/PEC shortlist, open data and laws, commercial operators, and Citi Bike charging. A verifier re-opened each record's source. The verifier also re-geocoded every coordinate by an independent method: OSM intersection nodes, NYC GeoSearch (PAD), US Census geocoder, or NYC CSCL/PLUTO. Where a record was corrected, the table uses the verifier's coordinates and fields.
2. **Manhattan filter.** A site is kept only if it lies inside the box lat 40.70-40.88, lon -74.02 to -73.91, **and** inside an `MN` polygon of `data/raw/nycnhood_acs.geojson` (ray casting). The box alone is not enough: Williamsburg and Long Island City fall inside it. Brooklyn, Queens, Bronx and Jersey City records were therefore excluded:
   - Willoughby St and Brooklyn Army Terminal pilots
   - PEC sites 07-10 (Bronx), 26-28 (Queens), 40-50 (Brooklyn)
   - Ebbets Field PopWheels
   - Swobbee 22 Smith St and Jersey City
   - 15 Brooklyn/Queens Citi Bike charging docks
   - Whizz Brooklyn store
3. **Deduplication within 80 m.** Records are first sorted by the loader's type priority (`pilot > installed > approved > revocable_consent > shortlist > application > citibike_charging > fdny_hub > depot > lot > other`) and then by source strength. A record within 80 m of one already kept is merged into it, and the merged record is named in `status_date`. Merges made by the script:
   - News "W 110th St & Amsterdam Ave" (65 m) and the Citi Bike dock "W 110 St & Amsterdam Ave" (29 m) were merged into **PEC Site 13 MN09** (DOT handout, 419 W 110th St). This is the same pattern as Site 16, which the news calls "106th & Amsterdam".
   - Citi Bike dock "Lenox Ave & W 126 St" (45 m) was merged into the PEC site W 126th St & Lenox Ave.

   Merges made before the script, because they are the same physical site:
   - The PEC Site 36 MN03 record (32A Cooper Sq) was folded into the Cooper Square pilot record.
   - PopWheels "286 Hudson St" was folded into 49 Dominick St (about 30 m apart, same tax block).
   - Swobbee "249 Broadway" was folded into the City Hall Park Deliverista Hub.
   - Records that appeared under several angles (for example PEC Sites 20, 21, 34, 35, 38, 39) were collapsed to one record each. Where coordinates differed, the corrected corner coordinate was used.
4. **`in_study_region`.** This flag is computed with the siting code's own test, `data_nyc.MANHATTAN_S110.in_band`: inside the box and south of the W 110th St / CPW boundary in the rotated grid frame. This guarantees that the flag matches what `sites_nyc` will keep.
   - PEC Site 13 is on the north block face of W 110th St and the loader's band excludes it (flag 0). It sits exactly on the boundary.
5. **Site types.** Only the loader's slugs are used: `pilot, installed, shortlist, citibike_charging, depot, other`. None of the verified Manhattan records qualified as `approved`, `revocable_consent`, `application`, `fdny_hub` or `lot` (see "Still missing").

## The sources

| Source | What it is | Use here |
|---|---|---|
| NYC DOT, *Safer Charging, Safer Deliveries* (Nov 2024), `nycdot2024safer` (URL valid) | Final report of the 2024 public charging pilot. Five sites named by landmark only (no addresses). Pilot ran 2024-03-07 to 2024-09-07, with swapping extended to Feb 2025. 12,100 swaps and 1,300 dock sessions. | 3 Manhattan `pilot` rows (Cooper Sq, Essex Market, Plaza de las Americas) |
| NYC DOT *Sidewalk E-Bike Battery Swapping and Charging Cabinets 101* (Apr 2025), `nycdot2025cabinets` (URL valid) | Revocable-consent process under 34 RCNY 7-04(a)(38), effective 2025-02-01. Covers eligibility, dimensions and fees. | Process only; no site list |
| NYC DOT Public E-Bike Charging (PEC) programme: project page `nycdotprojects.info/project/1995`, Mayor's release 2026-04-17, DOT release 2025-11-18 | $3M NYSERDA Clean Mobility grant. 50 preliminary right-of-way sites, to be cut to about 25. Vendor RFP late 2026, cabinets in service 2028. Feedback deadline extended from 07-31 to 2026-08-31. | Programme facts and status wording |
| DOT PEC site sheets and decks: MN CB3 deck 2026-06-09; "Manhattan Proposed Sites" handout 2026-04-16 (pages hosted by CB8 and the Columbus-Amsterdam BID); MN CB4 letter 2026-07-17; CB8 posts, minutes and resolution (July 2026) | Primary DOT text giving site number, corner and address | Sites 13, 16, 20, 21, 22, 23, 29, 30, 34, 35, 38, 39 and the 1st Ave/E 103rd example site |
| Local news: Patch Harlem/UES (2026-04-21), West Side Rag, I Love the UWS, The Broadsheet | Intersections from DOT's preliminary list where no DOT sheet was found | 12 PEC rows (labelled "news only" in `status_date`) |
| Operator pages: swobbee.com/new-york and /deliverusa/us; getwhizz.com (PopWheels cabinet list); Settlement Housing Fund release; ridezoomo.com | Commercial cabinet and store addresses | 8 `installed`, 2 planned (`other`), 4 stores (`depot`) |
| Citi Bike GBFS v2.3 `station_information` (Lyft field `is_charging`, read 2026-10-21) and DOT release 2025-05-05 | Grid-connected Citi Bike docks: 32 citywide, 17 in Manhattan. Plus 2 DOT-named docks with `is_charging=false`. | 17 `citibike_charging` rows after merges |
| NYC Open Data | No e-bike cabinet, revocable-consent or charging-hub dataset exists. | Used only for coordinates: DOT pedestrian plazas (5dck-9m6g), NYCHA addresses (3ub5-4ph8), CSCL (inkn-q76z), MapPLUTO (64uk-42ks) |
| Con Edison release 2023-03-20 | NYCHA outdoor charging pilot at four developments, including De Hostos (Manhattan) | 1 `other` row; installation unconfirmed |

## Counts by type

| site_type | meaning | in study region | north of 110th | total |
|---|---|---|---|---|
| pilot | DOT 2024 pilot hub | 2 | 1 | 3 |
| installed | operating cabinet (Swobbee, PopWheels, City Hall hub) | 5 | 3 | 8 |
| shortlist | DOT PEC preliminary site (1 of 50) | 18 | 7 | 25 |
| citibike_charging | grid-connected Citi Bike dock | 14 | 3 | 17 |
| depot | operator store or hub, no public cabinet | 4 | 1 | 5 |
| other | planned Swobbee station, NYCHA pilot | 2 | 1 | 3 |
| **total** | | **45** | **16** | **61** |

Source quality:
- 12 of the 25 PEC rows rest on news only.
- Two Citi Bike rows (W 35 St & 9 Ave, W 92 St & Broadway) are flagged UNCERTAIN because the live feed shows `is_charging=false`.

## Verification outcome

All 61 kept rows were checked against an opened source. Verdicts: **43 confirmed, 18 corrected**. No record was refuted. The main corrections:

- **Coordinates moved to the stated corner or lot:**
  - PEC Site 34 is on the SE corner; 207 2nd Ave is the SW building, about 30 m off.
  - Site 35 SE corner: the address point was 100 m east.
  - Site 16 is mid-block west of Amsterdam, not at the corner.
  - Site 20 uses 1524 2nd Ave.
  - Plaza de las Americas: the earlier GeoSearch point was 145 m west of the plaza. Now taken from the DOT plaza dataset.
  - PopWheels Hudson Square: PLUTO lot for 49 Dominick St.
  - City Hall hub: park-side kiosk, not the 249 Broadway office building.
  - De Hostos: NYCHA dataset point.
- **Status:**
  - "Shortlist" is the taxonomy bucket only. DOT calls all 50 sites preliminary, and no final ~25 list exists as of 2026-10-20.
  - The "CB3 motion passed 30-1-3" claim was wrong. That vote belonged to another agenda item, and the PEC item was informational.
  - CB8's full board approved Sites 20 and 21 on 2026-07-15 (36-6-2).
  - The City Hall hub was unpowered at its 2026-04-07 unveiling and operational from about June 2026.
- **Unsupported labels removed:**
  - Inferred PEC map numbers for news-only sites.
  - "Swobbee US Corp" (the pages name only Swobbee/Swobbee GmbH).
  - "Charging, not swapping" for the City Hall hub (Tribeca Trib reports swaps with Swobbee batteries).

## Still missing

- **About 14 of DOT's 34 Manhattan PEC sites.** DOT's numbered map shows Manhattan as sites 1-6, 11-25, 29-39 and 42-43, but only 20 Manhattan sites are located.
  - Missing completely: CB12 (sites 1-4, "four hubs"), CB2/CB5/CB6 (31-33, 37) and others.
  - The full "Manhattan Proposed Sites" handout is not online. The feedback form is closed and gives no list.
- **DOT's final ~25-site selection and the RFP vendor:** not published.
- **Revocable-consent cabinets:** no published petitions, approvals or installed RC cabinets. Streetsblog (Oct 2025, news) reported zero applications in progress. The `approved`, `revocable_consent` and `application` classes are therefore empty.
- **FDNY-approved hubs:** FDNY approves cabinet models, not sites, and publishes no site list. The `fdny_hub` class is empty.
- **Commercial network lists:**
  - PopWheels reports 30-50 cabinets but only 4 Manhattan addresses were found. popwheels.com was unreachable.
  - JOCO claims 50+ hubs but publishes no list.
  - No NYC operator called "Swap Energy" was found.
- **Pilot sites:**
  - Exact cabinet positions are not given; coordinates are plaza or building level (±30-50 m).
  - Whether the pilot cabinets still exist after Feb 2025 is unknown. They are absent from Swobbee's current list.
- **NYCHA:** no list for the RAISE-grant programme (about 173 stations at 53 developments). De Hostos installation is unconfirmed.
- **Citi Bike:** how many docks per station charge, and the charging power, are not published.

## Recommendation for the 40-60 candidate set

Build the set in labelled tiers. The loader already merges by type priority and keeps the type in `dot_type`, so the tiers survive into the results.

1. **Tier A, "real" candidates: 25 sites in the study region.**
   - Pilot: 2 (Cooper Sq, Essex Market)
   - Installed: 5 (Hudson Square, City Hall hub, Swobbee 836 6th Ave, Swobbee 124 W 31st St, Two Bridges Tower)
   - DOT PEC preliminary: 18

   These are places where DOT or an operator has put, or proposed, a cabinet. The installed and pilot sites have proven power and some demand evidence: Cooper Sq had 59% of pilot transactions. The PEC sites already passed DOT's clearance screen. Caveats:
   - PEC sites are not final, and about half could be dropped. CB4 opposes Sites 22 and 29.
   - Two Bridges is resident-only.
   - Use Tier A as the main set and test robustness by dropping the CB4-opposed and news-only PEC rows.
2. **Tier B, grid proxies: 14 Citi Bike charging docks in the study region.** These have proven Con Edison grid hookups on the sidewalk or in the curb lane. They are plausible charge-only or hub locations (the loader marks `citibike_charging` as hub-capable), but nobody has proposed a cabinet there. Label them as proxies. Tiers A and B give 39 sites.
3. **Tier C, optional: 6 operator stores and planned sites** (`depot` 4, `other` 2: Movin, Zoomo, Whizz Union, JOCO 259 Bowery, Swobbee 139 Charles St, De Hostos). These are weak as public swap sites but useful as depot or charge-only options. Including them gives 45.
4. **Tier D, restaurant-density lattice cells to fill gaps.** Add M01-M15 cells that have no Tier A or B site within about 500 m, up to 50-60 sites in total. Label them `lattice`; the loader's `cls` is then `lattice` or `both`. Coverage gaps visible on the map are Tribeca/SoHo west, Murray Hill/Gramercy, the Upper East Side between E 79th and E 95th St, and Central Park West.

**What is real and what is a proxy.**
- Only `pilot` and `installed` are observed infrastructure.
- `shortlist` is a real public proposal with DOT siting logic, but it has not been decided.
- `citibike_charging` shows grid access, not demand or a cabinet decision.
- `depot` and `other` are operator footprints of mixed relevance.
- Lattice cells are purely a demand proxy.

Results should be reported by tier, for example the share of opened sites that come from Tier A.

**Boundary note.** 16 sites lie north of 110th St. They include 3 installed East Harlem cabinets (Swobbee 2274 1st Ave, PopWheels 402 E 115th St and 148 E 123rd St), 7 PEC sites in Harlem, and Site 13 on W 110th St itself. Extending the region to about 125th St would add a dense cluster of real candidates; that is worth considering as a sensitivity run.
