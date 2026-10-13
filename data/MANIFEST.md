# data/ MANIFEST — real-data pull, 2026-10-12

Four datasets requested by the first-round data plan (`notes/datasets.md`). All pulled read-only via public
SODA (Socrata) endpoints or a static GeoDa zip; nothing under `ebike_swap_sim/` was touched.
Machine-readable copy: `manifest.json` (path, source_url, bytes, rows, md5, pulled_at, description).
Helper scripts used: `data/fetch_counters.py`, `data/validate.py` (copied from the session scratchpad).

| file | bytes | rows | md5 |
|---|---|---|---|
| raw/dohmh_restaurants.csv | 4,643,405 | 31,516 | dd26dec21a7f1270866fd775ffffd828 |
| raw/nycnhood_acs.zip | 1,265,653 | – | d919ad5378b02a634ed4ebaf20f93b42 |
| raw/nycnhood_acs/NYC_Nhood ACS2008_12.shp | 1,691,916 | 195 shapes | 37d5b99f3989f8976f55afe13118758e |
| raw/nycnhood_acs/NYC_Nhood ACS2008_12.shx | 1,660 | – | a3bdecbd5a8f57b5a13b8b16fb647639 |
| raw/nycnhood_acs/NYC_Nhood ACS2008_12.dbf | 317,314 | 195 | 6d2971fd9551cb9274accc7314db4b33 |
| raw/nycnhood_acs/NYC_Nhood ACS2008_12.prj | 143 | – | e729936bf5360b37a15365fc295a1901 |
| raw/nycnhood_acs_attributes.csv (derived) | 97,355 | 195 | 140f326093bc4563fa7cc7dc161612c9 |
| raw/nycnhood_acs.geojson (derived) | 4,694,543 | 195 features | cda3b1d35a7b26fb21361ec65804e76c |
| raw/cyclist_crash_grid_0005deg.csv | 129,742 | 2,251 | 533f8878f31b43d5413e3717fbd2e6e8 |
| raw/bike_counter_sites_raw.json | 9,084 | 41 | d57070f371c5ff05dec3364d2c46b67c |
| raw/bike_counter_sites.csv (derived) | 2,178 | 18 | dd70509a4e1a65e7fc79581165912777 |
| raw/bike_counter_dow_hour_raw.csv | 166,119 | 2,184 | adf58f888cd15f77046ac6e294f6bd16 |
| raw/bike_counter_hourly_profile.csv (derived) | 75,935 | 624 | adcb3cb37022ca75337af248e3955e01 |

## 1. DOHMH restaurants (43nn-pn8j), deduplicated by camis
Source: https://data.cityofnewyork.us/resource/43nn-pn8j.csv — one SODA request, grouped server-side, 31,516 rows < 50,000 limit, so no paging was needed.
```
curl -sS -L -o dohmh_restaurants.csv 'https://data.cityofnewyork.us/resource/43nn-pn8j.csv?$select=camis,min(dba)%20as%20r_dba,min(boro)%20as%20r_boro,min(zipcode)%20as%20r_zip,max(latitude)%20as%20r_lat,max(longitude)%20as%20r_lon,min(cuisine_description)%20as%20r_cuisine,min(community_board)%20as%20r_cb,min(nta)%20as%20r_nta,min(census_tract)%20as%20r_tract,max(inspection_date)%20as%20r_last_insp,count(*)%20as%20n_rows&$group=camis&$order=camis&$limit=50000'
```
Validation (validate.py): 31,516 rows = 31,516 distinct camis; sum(n_rows) = 296,623 = full source table.
lat/lon inside bbox (40.4–41.0, −74.3–−73.6): 30,713 (97.45 %). cuisine present: 27,630 (87.67 %). last inspection date present: 100 %.
Usable (bbox & cuisine & inspected): 27,030. Boro: Manhattan 12,584 (10,605 usable), Brooklyn 8,018, Queens 7,053, Bronx 2,641, Staten Island 1,125, "0" 95.
Top-20 cuisine_description: American 4,824; Chinese 2,277; Coffee/Tea 2,224; Pizza 1,615; Latin American 1,125; Mexican 1,116; Japanese 1,065; Italian 1,013; Bakery Products/Desserts 935; Chicken 740; Caribbean 739; Other 546; Donuts 546; Juice, Smoothies, Fruit Salads 540; Hamburgers 498; Asian/Asian Fusion 470; Spanish 465; Sandwiches 458; Korean 429; Frozen Desserts 387.

## 2. GeoDa NYC Neighborhoods ACS 2008-12
```
curl -sS -L -o nycnhood_acs.zip 'https://geodacenter.github.io/data-and-lab/data/nycnhood_acs.zip'   # 200, 1,265,653 bytes (matches expected)
mkdir -p nycnhood_acs && unzip -o -q nycnhood_acs.zip -x '__MACOSX/*' -d nycnhood_acs
pip install pyshp
python3 -I validate.py "$PWD/raw"    # reads .dbf/.shp with pyshp, writes nycnhood_acs_attributes.csv + nycnhood_acs.geojson
```
Validation: 195 records, shapeType POLYGON, 98 fields, CRS from .prj = GCS_WGS_1984 (EPSG:4326) → GeoJSON written in WGS84 lon/lat without reprojection. bbox lon −74.2556..−73.7000, lat 40.4961..40.9155. Boro counts: Queens 58, Brooklyn 51, Bronx 38, Manhattan 29, Staten Island 19. Two zero-population NTAs ("Airport", "park-cemetery-etc-Staten Island").
Fields: UEMPRATE, cartodb_id, borocode, withssi, withsocial, withpubass, struggling, profession, popunemplo, poptot, popover18, popinlabou, poororstru, poor, pacific*, other*, only*, okay, mixed*, master, male* (incl. male16to19), lessthan10, lessthanhi, households, hispanic*, highschool, field_1, female*/fem_* (incl. femal16_19), european*, doctorate, comm_* (commute bands), college, bachelor, asian*, american*, african*, ntaname, boroname, popdty, ntacode, medianinco, medianagem, medianagef, medianage, HHsize, gini.
Summary (195 NTAs): poptot mean 42,047 / median 36,676 / max 135,718; male16to19 mean 1,105 (max 3,412); femal16_19 mean 1,083 (max 3,856); bachelor mean 5,733 (max 33,730).
medianinco (172 non-null) mean 623,363, median 503,233, range 49,725–2,192,460; medianage (176 non-null) mean 398, median 342, range 29–1,086; popdty (192 non-null) mean 554,177, median 464,897, max 1,978,140.
**WARNING**: medianinco / medianage / popdty / HHsize / gini are stored as TEXT in the DBF and their magnitudes show they are SUMS of tract-level values over the tracts in each NTA (e.g. medianage 722.6 for BK45), not NTA medians. Use them only as rank-order proxies, or recompute: density = poptot / polygon area; income from Census ACS by tract.

## 3. Cyclist-involved crash grid (h9gi-nx95), 0.005° cells, since 2022-01-01
```
curl -sS -L -o cyclist_crash_grid_0005deg.csv -G 'https://data.cityofnewyork.us/resource/h9gi-nx95.csv' \
  --data-urlencode '$select=floor(latitude*200)/200 as lat_cell,floor(longitude*200)/200 as lon_cell,count(*) as cyc_crashes,sum(number_of_cyclist_injured) as cyc_inj,sum(number_of_cyclist_killed) as cyc_killed' \
  --data-urlencode "\$where=crash_date>='2022-01-01' AND (number_of_cyclist_injured>0 OR number_of_cyclist_killed>0) AND latitude>40.4 AND latitude<41.0 AND longitude>-74.3 AND longitude<-73.6" \
  --data-urlencode '$group=lat_cell,lon_cell' --data-urlencode '$order=lat_cell,lon_cell' --data-urlencode '$limit=50000'
```
Validation: 2,251 cells (< 50,000, no paging); total 20,999 crashes (expected ~20k), 21,259 cyclists injured, 100 killed. lat_cell 40.500–40.905, lon_cell −74.255–−73.705 (cell value = SW corner, floor()).
Top-10 cells (lat_cell, lon_cell, crashes): (40.720,−73.995) 87; (40.715,−73.995) 85; (40.715,−73.990) 85; (40.745,−73.975) 82; (40.755,−73.990) 81; (40.735,−73.985) 79 [1 killed]; (40.760,−73.965) 79; (40.740,−73.995) 73; (40.765,−73.985) 72; (40.720,−73.990) 70 — Lower East Side / Chinatown, Midtown East, Hell's Kitchen.

## 4. Bicycle counters hourly profile (smn3-rzf9 sites, uczf-rk3c counts), calendar 2024
```
curl -sS -L -o bike_counter_sites_raw.json 'https://data.cityofnewyork.us/resource/smn3-rzf9.json?$limit=50'      # 41 sites
# probe: date_extract_dow is supported server-side
curl -sS -G 'https://data.cityofnewyork.us/resource/uczf-rk3c.json' --data-urlencode '$select=date_extract_dow(date) as dow,date_extract_hh(date) as hh,sum(counts) as c,count(*) as n' --data-urlencode "\$where=id='100057316' AND date between '2024-01-01T00:00:00' and '2024-12-31T23:59:59'" --data-urlencode '$group=dow,hh' --data-urlencode '$order=dow,hh' --data-urlencode '$limit=200'
python3 -I fetch_counters.py "$PWD/raw"     # 18 requests (one per selected site), each ≤ 7.4 kB, 168 groups max
```
Site selection rule: name contains any of Ave/St/Greenway/Columbus/Amsterdam/Broadway/Prospect/Kent and not 'Bridge' and not 'Peds' → 18 sites. 'Staten Island Ferry' slipped in via 'St' in 'Staten' (kept, flagged). Five selected sites returned 0 rows for 2024 (Broadway at 50th St 100057318, Kent Ave btw South 6th 100058279, 2nd Avenue–26th St S 100009424, 1st Avenue–26th St N 100010020, Hunts Point Ave Station 300054793) → 13 counters in the profile.
Weekday/weekend split done server-side via `date_extract_dow` (0 = Sunday … 6 = Saturday; weekend = {0,6}); summed to hour in pandas.
Validation: share_of_day sums to 1.0 for all 26 (counter, daytype) groups (min 0.9999999999999987); every group has 24 hours.
Evening-peak hour (max share within 15–22 h), weekday / weekend: 8th Ave @ 50th 18 / 18; Amsterdam Ave @ 86th 19 / 19; Columbus Ave @ 86th 18 / 18; Kent Ave N 8th 18 / 15; Ocean Pkwy @ Ave J 17 / 15; Prospect Park West 17 / 15; 111th St @ 50th Ave 18 / 17; Willis Ave 16 / 16; Emmons Ave 17 / 15; Fountain Ave 15 / 15; Staten Island Ferry 17 / 17.
Overall daily peak is 17–19 h on weekdays for all Manhattan/Brooklyn avenue counters (shares 9–11 %); weekend peaks shift to 12–15 h for park/waterfront counters (Emmons, Prospect Park West, Kent Ave).
2024 totals (weekday / weekend): Willis Ave 1,118,423 / 378,686; Kent Ave N 882,924 / 396,238; 8th Ave 730,178 / 260,306; Amsterdam 678,685 / 256,992; Columbus 458,237 / 182,011; Prospect Park West 413,230 / 175,669; Fountain Ave only 4,552 / 3,418 (too sparse to use).

## Hash / size commands
```
md5 raw/*.csv raw/*.json raw/*.geojson raw/*.zip raw/nycnhood_acs/*
ls -la raw raw/nycnhood_acs
```

## 5. ACS (DCP / Open Data) — ACS 2020-2024 5-year profiles by NTA-2020, pulled 2026-10-12
Source discovery: the human page https://www.nyc.gov/content/planning/pages/resources/datasets/american-community-survey is JS-rendered; its real content (with download links) comes from `https://apps.nyc.gov/content-api/v1/content/planning/resources/datasets/american-community-survey`. Old URL `.../data-maps/open-data/census-data.page` → 404. Latest release listed there: **2024 ACS 5-Year (= 2020-2024)**, files `{Dem,Soc,Econ,Hous}_2024ACS5YR_{NTA,CDTA,CCD}.xlsx` (Last-Modified 2026-07-02/13). Previous releases are zips: `https://s-media.nyc.gov/agencies/dcp/assets/files/zip/data-tools/population/american-community-survey/5-yr-ACS-2023.zip` (2019-2023, 9,587,994 B, not downloaded), `5-yr-ACS-2022.zip`, `5-yr-ACS-2010.zip`.
Census API without key: `https://api.census.gov/data/2023/acs/acs5?get=NAME,B01001_001E&for=tract:*&in=state:36%20county:061` → HTTP 302 to an HTML page titled "Missing Key" (api.census.gov now requires a key; no data returned). NYC Open Data Socrata search only has old DCP NTA profiles (8cwr-7pqn = ACS 2012-2016 zip, 5.2 MB; rnsn-acs2 = decennial 2000/2010 pop) — not used.
```
B=https://s-media.nyc.gov/agencies/dcp/assets/files/excel/data-tools/population/american-community-survey
for f in Dem_2024ACS5YR_NTA.xlsx Soc_2024ACS5YR_NTA.xlsx Econ_2024ACS5YR_NTA.xlsx Hous_2024ACS5YR_NTA.xlsx; do
  curl -sS -L -A "Mozilla/5.0" --max-filesize 15000000 -o raw/acs/$f "$B/$f"; done        # all HTTP 200
curl -sS -L -A "Mozilla/5.0" -o raw/acs/nta2020.geojson 'https://data.cityofnewyork.us/api/geospatial/9nt8-h7nd?method=export&format=GeoJSON'
```
| file | bytes | md5 | rows |
|---|---|---|---|
| raw/acs/Dem_2024ACS5YR_NTA.xlsx  | 802,138   | 4f6f369857008b6ff5797991f962723a | 262 NTAs x 535 cols (sheet DemData) |
| raw/acs/Soc_2024ACS5YR_NTA.xlsx  | 3,316,837 | 41e914c83245faeb1c471ee9d881e951 | 262 x 2280 (SocData) |
| raw/acs/Econ_2024ACS5YR_NTA.xlsx | 1,841,929 | 6a3643b5660a274dd96d312146a5e9ed | 262 x 660 (EconData) |
| raw/acs/Hous_2024ACS5YR_NTA.xlsx | 838,723   | 01fa7c091af0f95c752d78f97ef24f51 | 262 x 520 (HousData) |
| raw/acs/nta2020.geojson          | 4,589,227 | 64606516a4ab9698e73dbe97f13bd293 | 262 features (WGS84) |

Layout (all four workbooks): sheets `<X>Data`, `Data Dictionary`, `About`. Id columns `GeoType` (always `NTA2020`), `NTAType` (0 = residential 197; 5 Rikers 1; 6 other special 8; 7 cemetery 14; 8 airport 2; 9 park 40), `GeogName`, `GeoID` (e.g. `BX0101`), `Borough`. Every variable `V` has five columns `VE` estimate, `VM` MOE (90 %), `VC` CV, `VP` percent, `VZ` percent MOE. Sources per variable in the dictionary (DP02/DP03/DP05, B01001, B03001, B11001, B11003, B17024, …). `GeoID` is identical across the four files and equals `nta2020` in the GeoJSON; 48 NTAs have Pop_1E = 0.
Validation (pandas, estimates): age bands sum exactly to Pop_1E − PopU181E; 8 race/Hispanic groups sum exactly to Pop_1E; 12 poverty-ratio bands sum exactly to PopPvU2E; HH1E (Soc) == HH2E (Econ). Citywide Pop_1E = 8,483,844; pop 18+ = 6,771,234 (CvPop18plE 6,767,670); GQ pop = Pop_1E − HHPopE = 217,235 (max 11,828).
Derivations for the demand-model weights (see loader notes in the project): pop18 = Pop_1E − PopU181E; a15_17 = PopU181E − PopU5E − Pop5t9E − Pop10t14E; a18_19 = Pop15t19E − a15_17 (≥ 0 in all NTAs); 18-29 = a18_19 + Pop20t24E + Pop25t29E; 30-44 = Pop30t34E+Pop35t39E+Pop40t44E; 45-59 = Pop45t49E+Pop50t54E+Pop55t59E; 60+ = Pop60t64E + Pop65pl1E. Race: WtNHE, BlNHE, Hsp1E, other = Pop_1E − those three. ≥200 % poverty = (Pv200t299E+Pv300t399E+Pv400t499E+Pv500plE)/PopPvU2E. One-person HH = NFamAE/HH1E. College/grad enrolment share of 18+ = SE_ClgGScE/pop18. SNAP = Inc_SNAPE/HH2E. Children: B11003 is only available as FamChU18E (own children < 18, any age); the under-6 / 6-17 split exists only as *persons* (DP03 OChU6E, OCh6t17E), so use OChU6E/HH1E and OCh6t17E/HH1E (children per household) or FamChU18E/HH1E as the household share.
