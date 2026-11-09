# Completion runs of the one-to-three-site study (4-9 November 2026)

Written by `notes/verify/r7_completion_facts.py` from `records.jsonl` and `cache_index.jsonl` in this folder
(the server's `outputs/r7_siting/records.jsonl` and `cache/index.jsonl` after the last run). All values are USD
per day with the evening's set-up share, for open-sites riders. `RESULTS_final.md` of the production run
(`../r7_prod_final/`) has the same point values with the earlier, narrower intervals (6 degrees of freedom) and
held-out values for six weekday evenings only.

## Layouts

| Layout | Key | Cost | Set-up | Open-sites lower bound | Orders served | Evenings at the time limit | Transfer cost |
|---|---|---|---|---|---|---|---|
| DOT Site 34 | `D23:SC:B3:C2` | 1,085.87 | 13.19 | 1,084.31 | 77.5 % | 1 of 12 | 0.00 |
| Cooper Square (coverage rule, one site) | `D18:SC:B3:C2` | 1,118.68 | 13.19 | 1,118.68 | 75.3 % | 0 of 12 | 0.00 |
| Citi Bike dock E 14th St & 1st Ave | `D24:SC:B3:C2` | 1,087.74 | 13.19 | 1,087.74 | 77.3 % | 0 of 12 | 0.00 |
| Best pair (Greenwich Village cell + E 62nd St dock) | `D07:SC:B3:C2|D45:SC:B3:C2` | 716.85 | 26.38 | 712.40 | 98.3 % | 4 of 12 | 0.00 |
| Listed-site pair (Site 34 + E 62nd St dock) | `D23:SC:B3:C2|D45:SC:B3:C2` | 719.60 | 26.38 | 713.09 | 98.4 % | 4 of 12 | 0.00 |
| Cabinet at E 14th St dock + full site at E 62nd St dock | `D24:S:B3:C0|D45:SC:B3:C2` | 758.34 | 26.22 | 754.53 | 96.9 % | 1 of 12 | 0.00 |
| Spread rule (two sites) | `D30:SC:B3:C2|D58:SC:B3:C2` | 808.56 | 26.38 | 805.94 | 94.6 % | 2 of 12 | 0.00 |
| DOT 2024 pilot pair | `D12:SC:B3:C2|D18:SC:B3:C2` | 851.27 | 26.38 | 847.71 | 91.6 % | 2 of 12 | 0.00 |
| Coverage rule (two sites) | `D18:SC:B3:C2|D19:SC:B3:C2` | 858.33 | 26.38 | 853.04 | 91.4 % | 5 of 12 | 0.00 |
| Full site at the cell + hub W 13th St | `D07:SC:B3:C2|D16:C:B0:C4` | 1,158.39 | 42.71 | 1,129.56 | 76.7 % | 9 of 12 | 28.00 |
| Full site at the cell + hub Bowery | `D07:SC:B3:C2|D13:C:B0:C4` | 1,160.44 | 42.71 | 1,140.68 | 75.6 % | 8 of 12 | 14.00 |
| Full site at the cell + hub Kenmare St | `D07:SC:B3:C2|D11:C:B0:C4` | 1,163.01 | 42.71 | 1,141.44 | 75.3 % | 7 of 12 | 14.00 |
| Cabinet at the cell + hub W 13th St | `D07:S:B3:C0|D16:C:B0:C4` | 1,335.95 | 42.54 | 1,335.94 | 69.6 % | 0 of 12 | 85.52 |
| Cabinet at the cell + hub Bowery | `D07:S:B3:C0|D13:C:B0:C4` | 1,375.96 | 42.54 | 1,375.95 | 67.1 % | 0 of 12 | 83.38 |
| Cabinet at the cell + hub Kenmare St | `D07:S:B3:C0|D11:C:B0:C4` | 1,375.94 | 42.54 | 1,375.92 | 67.1 % | 0 of 12 | 82.43 |
| Cabinet at the cell + hub W 92nd St (out of range) | `D07:S:B3:C0|D50:C:B0:C4` | 1,445.77 | 42.54 | 1,445.76 | 58.0 % | 0 of 12 | 0.00 |
| Cabinet at the cell + hub W 42nd St (out of range) | `D07:S:B3:C0|D34:C:B0:C4` | 1,445.77 | 42.54 | 1,445.77 | 58.0 % | 0 of 12 | 0.00 |
| Cabinet at E 62nd St dock + hub E 72nd St | `D45:S:B3:C0|D47:C:B0:C4` | infeasible (stopped at the first infeasible evening) | | | | | |
| Full site at E 62nd St dock + hub E 72nd St | `D45:SC:B3:C2|D47:C:B0:C4` | infeasible (stopped at the first infeasible evening) | | | | | |
| Best pair, four spares each | `D07:SC:B4:C2|D45:SC:B4:C2` | 709.98 | 27.04 | 709.96 | 98.5 % | 0 of 12 | 0.00 |
| Listed-site pair, four spares each | `D23:SC:B4:C2|D45:SC:B4:C2` | 709.84 | 27.04 | 708.76 | 98.6 % | 1 of 12 | 0.00 |
| Best pair + Site 34 | `D07:SC:B3:C2|D23:SC:B3:C2|D45:SC:B3:C2` | 718.80 | 39.57 | 718.79 | 98.6 % | 0 of 12 | 0.00 |
| Best pair + E 14th St dock | `D07:SC:B3:C2|D24:SC:B3:C2|D45:SC:B3:C2` | 717.55 | 39.57 | 717.54 | 98.6 % | 0 of 12 | 0.00 |
| Coverage rule (three sites) | `D18:SC:B3:C2|D19:SC:B3:C2|D23:SC:B3:C2` | 830.96 | 39.57 | 830.96 | 93.6 % | 0 of 12 | 0.00 |
| Best pair + hub W 13th St (third unit) | `D07:SC:B3:C2|D16:C:B0:C4|D45:SC:B3:C2` | 746.83 | 55.90 | 740.79 | 98.3 % | 4 of 12 | 0.00 |
| Best pair + hub Bowery (third unit) | `D07:SC:B3:C2|D13:C:B0:C4|D45:SC:B3:C2` | 745.71 | 55.90 | 741.69 | 98.3 % | 3 of 12 | 0.00 |
| Best pair + hub Kenmare St (third unit) | `D07:SC:B3:C2|D11:C:B0:C4|D45:SC:B3:C2` | 746.38 | 55.90 | 742.27 | 98.3 % | 3 of 12 | 0.00 |
| Best pair + hub E 72nd St (third unit) | `D07:SC:B3:C2|D45:SC:B3:C2|D47:C:B0:C4` | 745.29 | 55.90 | 740.66 | 98.3 % | 3 of 12 | 0.00 |

Transfer cost: weighted mean of the van-trip and per-battery charges; 0.00 means no battery moved between sites.

## Extra cost of a layout over its reference (mean and half-width of the paired 95 % interval)

| Layout | Reference | 12 planning evenings | 12 held-out evenings | Proven range |
|---|---|---|---|---|
| Cooper Square (coverage rule, one site) | DOT Site 34 | +32.81 ± 40.64 | +38.11 ± 33.31 | [32.81, 34.37] |
| Citi Bike dock E 14th St & 1st Ave | DOT Site 34 | +1.87 ± 11.91 | +8.17 ± 14.44 | [1.87, 3.43] |
| DOT Site 34 | Best pair (Greenwich Village cell + E 62nd St dock) | +369.02 ± 112.83 | +385.40 ± 84.22 | [367.46, 415.64] |
| Listed-site pair (Site 34 + E 62nd St dock) | Best pair (Greenwich Village cell + E 62nd St dock) | +2.75 ± 24.36 | -0.31 ± 2.53 | [-3.77, 49.37] |
| Cabinet at E 14th St dock + full site at E 62nd St dock | Best pair (Greenwich Village cell + E 62nd St dock) | +41.49 ± 14.92 | +32.05 ± 14.33 | [37.68, 88.11] |
| Spread rule (two sites) | Best pair (Greenwich Village cell + E 62nd St dock) | +91.70 ± 75.33 | +60.30 ± 55.66 | [89.09, 138.33] |
| DOT 2024 pilot pair | Best pair (Greenwich Village cell + E 62nd St dock) | +134.42 ± 55.41 | +130.72 ± 123.75 | [130.86, 181.04] |
| Coverage rule (two sites) | Best pair (Greenwich Village cell + E 62nd St dock) | +141.48 ± 53.09 | +129.91 ± 122.02 | [136.19, 188.10] |
| Full site at the cell + hub W 13th St | Best pair (Greenwich Village cell + E 62nd St dock) | +441.54 ± 91.46 | +459.55 ± 218.84 | [412.71, 488.16] |
| Full site at the cell + hub Bowery | Best pair (Greenwich Village cell + E 62nd St dock) | +443.59 ± 88.96 | +460.01 ± 209.27 | [423.83, 490.21] |
| Full site at the cell + hub Kenmare St | Best pair (Greenwich Village cell + E 62nd St dock) | +446.16 ± 82.86 | +459.01 ± 217.39 | [424.59, 492.78] |
| Cabinet at the cell + hub W 13th St | Best pair (Greenwich Village cell + E 62nd St dock) | +619.10 ± 89.55 | +638.93 ± 162.99 | [619.09, 665.72] |
| Cabinet at the cell + hub Bowery | Best pair (Greenwich Village cell + E 62nd St dock) | +659.11 ± 81.71 | +675.45 ± 163.23 | [659.10, 705.73] |
| Cabinet at the cell + hub Kenmare St | Best pair (Greenwich Village cell + E 62nd St dock) | +659.09 ± 80.90 | +674.79 ± 166.64 | [659.07, 705.71] |
| Cabinet at the cell + hub W 92nd St (out of range) | Best pair (Greenwich Village cell + E 62nd St dock) | +728.92 ± 124.87 | +731.45 ± 189.53 | [728.91, 775.54] |
| Cabinet at the cell + hub W 42nd St (out of range) | Best pair (Greenwich Village cell + E 62nd St dock) | +728.92 ± 124.87 | +731.15 ± 188.48 | [728.92, 775.54] |
| Cabinet at E 62nd St dock + hub E 72nd St | Best pair (Greenwich Village cell + E 62nd St dock) | infeasible | | |
| Full site at E 62nd St dock + hub E 72nd St | Best pair (Greenwich Village cell + E 62nd St dock) | infeasible | | |
| Best pair, four spares each | Best pair (Greenwich Village cell + E 62nd St dock) | -6.87 ± 5.32 | -3.12 ± 3.10 |  |
| Listed-site pair, four spares each | Listed-site pair (Site 34 + E 62nd St dock) | -9.76 ± 13.64 | -3.54 ± 3.85 |  |
| Listed-site pair, four spares each | Best pair, four spares each | -0.14 ± 5.33 | -0.73 ± 3.37 | [-1.22, 39.61] |
| Best pair + Site 34 | Best pair, four spares each | +8.82 ± 9.12 | +7.79 ± 3.36 | [8.81, 48.57] |
| Best pair + E 14th St dock | Best pair, four spares each | +7.56 ± 10.27 | +7.90 ± 3.30 | [7.56, 47.32] |
| Coverage rule (three sites) | Best pair, four spares each | +120.98 ± 45.09 | +90.23 ± 47.14 | [120.98, 160.73] |
| Best pair + hub W 13th St (third unit) | Best pair (Greenwich Village cell + E 62nd St dock) | +29.98 ± 5.15 | +28.65 ± 2.10 |  |
| Best pair + hub Bowery (third unit) | Best pair (Greenwich Village cell + E 62nd St dock) | +28.86 ± 3.63 | +27.73 ± 4.09 |  |
| Best pair + hub Kenmare St (third unit) | Best pair (Greenwich Village cell + E 62nd St dock) | +29.53 ± 4.63 | +31.95 ± 34.42 |  |
| Best pair + hub E 72nd St (third unit) | Best pair (Greenwich Village cell + E 62nd St dock) | +28.44 ± 7.91 | +27.53 ± 4.20 |  |
| Best pair + hub W 13th St (third unit) | Best pair, four spares each | +36.85 ± 8.76 | +31.77 ± 5.94 | [30.80, 76.60] |
| Best pair + hub Bowery (third unit) | Best pair, four spares each | +35.73 ± 3.27 | +30.85 ± 6.86 | [31.71, 75.48] |
| Best pair + hub Kenmare St (third unit) | Best pair, four spares each | +36.40 ± 0.98 | +35.06 ± 37.68 | [32.29, 76.15] |
| Best pair + hub E 72nd St (third unit) | Best pair, four spares each | +35.31 ± 6.20 | +30.65 ± 10.08 | [30.67, 75.06] |

The proven range is given where the reference is the best layout found at that budget.
