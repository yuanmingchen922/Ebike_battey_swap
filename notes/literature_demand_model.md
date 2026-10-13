# Literature-driven demand model: Demographic Destination Sampler + Restaurant Type Sampler

Date: 2026-10-12. Sources: the three papers cited on proposal p. 13 (`ebike.txt`; full texts stored in `notes/literature/`), the Kaggle calibration table `notes/data/kaggle_calibration.{md,json}`, the dataset conclusions in `notes/datasets.md`. This file gives only the **numbers and formulas needed for implementation**; every number is annotated with the paper and table it comes from and with the conversion we applied.

**One-sentence conclusion**: only two of the three papers actually estimate "who orders delivery" (Bennett 2025 estimates *participation*, Buettner 2023 estimates *weekly frequency*); the third (Tahim 2024) uses "app use or not" as an exposure variable to explain diet, and can only provide directional support and cuisine tendencies. Chaining the logic of the first two gives exactly the structure the simulator needs:

> Expected orders in a zone = adult population base × participation propensity (age, sex, income, ethnicity, children) × user frequency (ethnicity, living alone, student, subjective status)

Age is the overwhelmingly dominant factor (participation rate ratio of about 3.4 for ages 18–29 vs 60+); all other factors stay within ±10–30%.

---

## 1. The three papers: methods and logic (one paragraph each)

### 1.1 Buettner, Pasch & Poulos (2023), *J Community Health*, PMC10163566 — US ages 18–25, weekly use frequency

**Method**: Qualtrics online panel, January–April 2022 (Omicron peak), US nationwide young adults aged 18–25, n = 1,576, oversampled by ethnicity (about 30% Black, 30% Hispanic), no sampling weights. The outcome is a single item, "on average how many times per week in the past month did you order through a delivery app (DoorDash/Grubhub/UberEATS)", recoded to an approximate count of 0/1.5/3.5/5.5/7/8 times per week, sample mean 1.8 per week (SD 1.46). A **multivariable Poisson regression** on this count with eight predictors entered simultaneously: age, sex, ethnicity, MacArthur subjective social status ladder (1–10), living alone/with others, food insecurity (Hunger Vital Sign), whether they pay their own credit-card bill, full-time student status. Only β and SE are reported, no IRR/CI; we take exp(β) as the rate ratio (IRR).
**Logic**: the authors treat 18–25 as a "heterogeneous transition period" (school/work/family formation), so frequency varies within this age band too; the mechanisms are convenience value, affordability (apps cost more than in-store) and substitution by whether someone at home cooks. The ethnicity effect is interpreted as higher fast-food density in residential areas (explicitly a spatial/supply-side explanation); the student effect as campus "food deserts". Key results (Table 2): Hispanic β = 0.35 (IRR 1.42), Black 0.21 (1.23), food insecure 0.32 (1.38), subjective status 0.08 per rung (1.083), pays own bill 0.21 (1.23), full-time student 0.11 (1.12), living with others −0.09 (i.e. living alone ×1.10), age 0.02 per year, **sex not significant** (β −0.04). Note: the outcome includes 0 (non-users), so the IRR is the **total rate ratio** of "participation × frequency", not pure user frequency.

### 1.2 Bennett et al. (2025), *Int J Obesity*, PMC12283340 — adults in five countries, online ordering in the past 30 days

**Method**: 2022 International Food Policy Study, adults (18+) in Australia/Canada/Mexico/UK/US from the Nielsen online panel, n = 19,877 (US 3,731), **post-stratification weighted** to each country's population (age, sex, region, ethnicity, education). Five binary outcomes modelled separately; the relevant one for us is "ordered food from a restaurant or takeaway via a website/app in the past 30 days" (including pickup and restaurant-owned apps). Weighted multivariable logistic regression with nine covariates entered simultaneously: sex, generation (18–29/30–44/45–59/60+), age of the youngest child at home, whether income is perceived as adequate, ethnic minority/majority, BMI, self-rated cooking skills, nutrition knowledge, weekly home-cooking frequency. Adjusted ORs with 95% CIs are reported. US weighted participation 34.36% (32.65–36.14).
**Logic**: the authors treat online ordering as an individual choice determined by socio-demographic position and food behaviour; age is the main effect (Gen Z OR 6.10, Millennial 4.83, Gen X 2.33 vs 60+), explained as early technology adoption and "willingness to pay for convenience". Having children (OR 1.55–1.87) is explained by **time poverty** (dual-earner parents); adequate income (OR 1.21) by the delivery-fee threshold; men more than women (female OR 0.81) by gendered household labour; minorities (OR 1.19) by poorer residential food environments, with online as the substitute. The reading of the behavioural variables is "convenience, not inability": users rate themselves as able to cook and nutrition-literate, but home-cooking frequency has **no effect** on restaurant ordering (OR 1.01). The paper answers WHO participates, not how often or where.

### 1.3 Tahim, Verde, Maia & Bezerra (2024), *IJERPH* 21(5):568, PMC11121648 — Fortaleza, Brazil, app use and diet

**Method**: Google Forms snowball sampling in June 2020 (pandemic lockdown), n = 2,113 adults, 79% female, over half with postgraduate education, 78% app users. **App use is the exposure**, outcomes are the frequencies of VIGITEL dietary markers (beans, fruit, vegetables, burgers/cold cuts, sugary drinks, instant noodles/snacks, desserts), each modelled by logistic regression adjusted for age, sex and education. Who uses apps is described only in Table 1 with chi-squared tests: users are younger (34.6 vs 42.6 years, p < 0.001), sex not significant (p = 0.13), income not significant (p = 0.84), postgraduate education is associated with **less** use (crude OR 0.78), having adolescents at home with less use (crude OR 0.78), 89.8% of non-users cook daily vs 74.4% of users (crude OR 0.33).
**Logic**: digital food environment (DFE) framework — platforms carry far more ultra-processed than fresh food and promote it, so app users eat more burgers (adjusted OR 1.73), sugary drinks (1.76), desserts (1.42), and fewer daily fruit (0.60), vegetables (0.50), beans (0.44). This supports two statements on proposal p. 13, "fast food / sugary drink consumption correlates with online ordering" and "people who cook less order more", plus "users are younger"; it does **not** support income, sex, ethnicity, student or food-insecurity effects, and contradicts "higher education orders more". Use for the simulator: (a) a third independent confirmation of the age direction; (b) the Restaurant Type Sampler's cuisine tendency should be skewed towards fast food/American rather than proportional to DOHMH restaurant counts.

---

## 2. Assembling the logic of the three papers into one model

The reasoning chain in the papers is "**population at risk → participates or not → how often participants order**". We define the expected order rate of zone z along this chain:

```
E[orders_z] = N_z × P_z × F_z
  N_z  = resident population aged 18+ (population at risk; Bennett's sample definition)
  P_z  = share participating in online ordering in the past 30 days (Bennett logistic: age, sex, income, ethnicity, children)
  F_z  = relative frequency among participants (Buettner Poisson: ethnicity, living alone, student, subjective status; Bennett's frequency is binarised and cannot be used)
```

The implementation does not need to keep P and F separate: convert both sets of effects into "rate ratios RR of expected orders per adult" and multiply them under the mixing rule of Section 4 below. None of the three papers has spatial variables, so all RRs are **individual effects applied to a zone's population composition** (ecological inference; risks discussed in Section 7).

---

## 3. Pooled factor table

| Factor | Papers (effect as reported) | Consensus direction | Pooled RR used (vs reference) | ACS 5-yr table / share x_fz | Confidence |
|---|---|---|---|---|---|
| Age 18–29 | Bennett OR 6.10 (5.34–7.00) vs 60+; Buettner +0.02/yr within 18–25; Tahim users 34.6 vs 42.6 yr | strongly more | **3.4** | B01001: (18–19,20,21,22–24,25–29 M+F) / pop 18+ | high |
| Age 30–44 | Bennett OR 4.83 (4.25–5.50) | more | **3.0** | B01001 30–34,35–39,40–44 | high |
| Age 45–59 | Bennett OR 2.33 (2.05–2.64) | more | **1.9** | B01001 45–49,50–54,55–59 | high |
| Age 60+ | reference | — | 1.0 | B01001 60+ | — |
| Female | Bennett OR 0.81 (0.75–0.88); Buettner IRR 0.96 n.s.; Tahim p = 0.13 | weakly less | **0.91** | B01001 female 18+ / pop 18+ | medium (null-ish, low leverage) |
| Hispanic | Buettner IRR 1.42 (18–25 only); Bennett "minority" OR 1.19 | more | **1.26** | B03002_012 / B03002_001 | medium |
| NH Black | Buettner IRR 1.23; Bennett minority OR 1.19 | more | **1.17** | B03002_004 / B03002_001 | medium |
| NH Asian / other | Buettner IRR 1.13 n.s.; Bennett minority OR 1.19 | weakly more | **1.12** | 1 − (white+Black+Hispanic shares) | low-medium |
| NH White | reference | — | 1.0 | B03002_003 | — |
| Income adequate (≥200% poverty) | Bennett OR 1.21 (1.10–1.32); Buettner SSS +0.08/rung (≈1.22 for 2.5 rungs); Tahim null (p = 0.84) | mildly more | **1.17** | C17002: (C17002_008 ≥2.00) / C17002_001 | medium-low |
| Food insecure / SNAP | Buettner IRR 1.38 (1.27–1.49); others n/a; opposite sign to income | contested | **1.0 default**; switch `food_insecurity=1.38^s_SNAP` for sensitivity | B22010_002 / B22010_001 | low |
| HH with child 0–5 | Bennett OR 1.55 (1.38–1.75); Tahim children n.s. (1.12), adolescents 0.78 crude | more | **1.22** | B11003 own children <6 (incl. <6 & 6–17) / B11003_001 | medium |
| HH with child 6–17 only | Bennett OR 1.87 / 1.66 (geo-mean 1.76); Tahim adolescents 0.78 crude | more | **1.29** | B11003 own children 6–17 only / B11003_001 | medium |
| Living alone | Buettner living-with-someone IRR 0.91 → alone 1.10 (1.01–1.18) | more | **1.10** | B11001_008 / B11001_001 | low-medium |
| Full-time college student | Buettner IRR 1.12 (1.03–1.21) | more | **1.12** | B14007_017+018 / pop 18+ (cap group-quarters tracts via B26001) | low-medium |
| Pays own credit-card bill | Buettner IRR 1.23 | more | **1.0** (no ACS counterpart) | — | low |
| Education (graduate) | Tahim crude OR 0.78 (less); deck says more; Bennett/Buettner not measured | contradictory | **1.0** | B15003 (not used) | low |
| Cooks less / time-poor | Tahim daily cooks OR 0.33 crude; Bennett cooking freq. OR 1.01 n.s. for restaurants | positive but unmeasurable | **1.0** (absorbed by living-alone and children terms) | — | low |
| Fast food / SSB consumption | Tahim OR 1.73 / 1.76 (diet outcome) | positive | not a zone weight; drives cuisine mix (Sec. 5.2) | CDC PLACES optional | low |
| BMI | Bennett 0.96/1.05 n.s.; Tahim p = 0.97 | null | 1.0 | — | — |

---

## 4. Effect-size conversion: OR → RR, share mixing, shrinkage

**(a) OR → rate ratio RR (Bennett's participation model)**. Bennett reports ORs, while the weights need ratios of expected orders per adult. At a reference participation rate p_ref, RR = OR / (1 − p_ref + p_ref·OR). For the single factors (sex, income, ethnicity, children) take p_ref = US overall 0.3436: OR 0.81 → RR 0.87; 1.21 → 1.13; 1.19 → 1.12; 1.55 → 1.30; 1.76 → 1.40. The four age groups are mutually exclusive categories, so solve one mixing equation directly: with the US adult age composition (18–29 at 0.21, 30–44 at 0.26, 45–59 at 0.24, 60+ at 0.29) and the four ORs, find the logit intercept that gives an overall participation of 0.3436, giving intercept −1.73, p(60+) = 0.151, p(18–29) = 0.520, p(30–44) = 0.462, p(45–59) = 0.293, i.e. RR = 3.45 / 3.06 / 1.94 / 1. Insensitive to the age-composition assumption (±0.1). **Do not use OR 6.10 directly as a multiplier** — that would overstate the weight of young zones by nearly a factor of two.

**(b) Use IRR directly (Buettner's Poisson model)**. exp(β) is already a rate ratio, but the sample covers only ages 18–25. Factors with an all-age anchor (ethnicity) are shrunk 50% (on the log scale) towards Bennett's RR 1.12: Black 1.23 → 1.17, Hispanic 1.42 → 1.26, other 1.13 → 1.12. Factors without an anchor (living alone 1.10, student 1.12) are used as reported and flagged low-confidence.

**(c) Handling disagreements**. Sex: geometric mean of Bennett RR 0.87 and Buettner 0.96 (n.s.) gives 0.91. Income: Bennett RR 1.13, Buettner subjective status 2.5 rungs ≈ 1.22, Tahim null (saturated high-income sample, treated as uninformative) → 1.17. Children: Bennett RR 1.30/1.40 contradicted by Tahim crude OR 0.78 (adolescents), shrunk 25% towards 1 → 1.22/1.29. Food insecurity (1.38) has the opposite sign to the income effect, and at zone level the SNAP share is nearly collinear with the income ranking, so entering both would cancel mechanically; it is OFF by default and kept as a sensitivity switch.

**(d) Share-mixing rule**. Under the individual rate model rate_i = RR_{g(i)}, a zone's expected orders is a sum over people, so **within one factor the mix is an arithmetic weighted average**, not exp(β·share): Σ_l s_l·RR_l for mutually exclusive categories; 1 + s·(RR − 1) for binary factors. The two forms coincide when RR is near 1 (for every factor except age the difference is <2%), but not for age: for a zone with 40% aged 18–29, arithmetic mixing gives 1.98, exp(0.4·ln 3.4) only 1.64. **Different factors are multiplied**, which assumes independence of the factors within a zone (consistent with the structure of both papers, where covariates enter simultaneously with multiplicative effects).

---

## 5. Zone-weight formula and sampling steps

### 5.1 Demographic Destination Sampler (exact formula)

For each zone z (census tract; if the network is coarse, aggregate to NTA — compute w by tract first, then sum):

```
w_z = N_z · M_age,z · M_eth,z · M_sex,z · M_inc,z · M_kid,z · M_alone,z · M_stu,z

N_z        = pop 18+                                     (B01001)
M_age,z    = 3.4·s18_29 + 3.0·s30_44 + 1.9·s45_59 + 1.0·s60p      (shares of pop 18+, sum to 1)
M_eth,z    = 1.0·s_white + 1.17·s_black + 1.26·s_hisp + 1.12·s_other   (shares of total pop, sum to 1)
M_sex,z    = 1 + (0.91−1)·s_female          = 1 − 0.09·s_female
M_inc,z    = 1 + (1.17−1)·s_adequate         = 1 + 0.17·s_adequate       (share ≥200% poverty, C17002)
M_kid,z    = 1 + 0.22·h_pre + 0.29·h_school                              (household shares, B11003)
M_alone,z  = 1 + 0.10·s_alone                                             (one-person HH / HH, B11001)
M_stu,z    = 1 + 0.12·s_student                                           (college-enrolled / pop 18+, B14007)
[optional sensitivity]  M_FI,z = 1 + 0.38·s_SNAP   (B22010)   default OFF

π_z = w_z / Σ_z' w_z'        ← destination sampling probability
```

Examples (hypothetical shares, for orders of magnitude only): a young Manhattan zone (40% aged 18–29, 50% living alone, 85% income-adequate) has a per-adult multiplier of 3.46; an older outer-borough zone (15% aged 18–29, 35% aged 60+) 2.70; a low-income Black/Hispanic zone 3.28. Age accounts for almost the whole difference (2.69 vs 2.05 vs 2.39); the ethnicity and children terms each contribute ±8–19%.

**Absolute volume**: π_z gives relative weights only. The total order volume Λ (orders/day) is a scenario parameter. Rough plausibility check: NYC about 6.6M adults × 34% participation × Buettner magnitude 1–2 per week ≈ 300–650k orders/day, the same order of magnitude as industry estimates for NYC; the simulation window (2 hours, one area) is scaled by Λ × time-of-day share × Σπ_z within the area.

**Group-quarters correction**: in college-dormitory tracts s_student and s18_29 both jump to 0.8+; use B26001 (group quarters) to replace N_z with the non-group-quarters population, or cap M_stu at 1.10.

### 5.2 Restaurant Type Sampler

1. **Cuisine**: the target cuisine distribution π_c is the Kaggle 14-class order share (American 0.308, Japanese 0.248, Italian 0.157, Chinese 0.113, Mexican 0.041, Indian 0.039, Middle Eastern 0.026, Mediterranean 0.024, Thai 0.010, French 0.010, Southern 0.009, Korean 0.007, Spanish 0.006, Vietnamese 0.004). Map DOHMH's 90 `cuisine_description` values to these 14 classes (the mapping table is a declared assumption; unmapped ones go to "American/other"), then draw the cuisine **by order share rather than by restaurant count**. Tahim's diet results (burgers OR 1.73, sugary drinks 1.76) are the qualitative basis for using "order share skewed to fast food" instead of "proportional to restaurant count".
2. **Candidate set**: DOHMH restaurants of that cuisine (deduplicated by camis, with coordinates, inspected) within radius R (default 2.5 km, declared assumption) of destination z. If fewer than 3, enlarge R.
3. **Restaurant choice**: sample candidates by Zipf popularity, weight ∝ rank^(−1.0) (Kaggle calibration: slope −1.005 for restaurants with ≥5 orders, R² 0.968; the full-sample −1.29 is an artefact of the single-order tail truncation). The rank is assigned randomly once within each cuisine and fixed for the whole simulation (declared assumption: Kaggle has no name–coordinate correspondence). Optional distance decay exp(−d/d0) as a switch, OFF by default.
4. Restaurant coordinate = order origin o_i, destination point = order end d_i, snapped to the nearest road-network node.

### 5.3 Complete sampling steps (per order)

```
0. Preprocessing (once): Census API ACS5 2019–2023 by tract, pull B01001, B03002, C17002, B11003, B11001, B14007, B22010, B26001
   → compute shares → w_z, π_z; DOHMH deduplicated restaurant table → cuisine mapping → Zipf rank per cuisine.
1. Time generator: r_i ~ non-homogeneous Poisson, intensity Λ · f_day(d) · f_hour(h) (Section 6; synthetic).
2. Destination z ~ Categorical(π_z); point within the zone ~ uniform over the tract polygon (or residential land) → d_i (synthetic).
3. Cuisine c ~ Categorical(π_c) (Kaggle).
4. Restaurant r ~ Zipf(s=1.0) over the candidate set (c, radius R of d_i) (Kaggle shape + synthetic rank) → o_i.
5. Prep time prep_i ~ DiscreteUniform(20, 35) min (Kaggle, exactly uniform, independent of cuisine/cost) → a_i = r_i + ⌈prep_i/Δ⌉.
6. Promised time b_i = a_i + ⌈τ_promise/Δ⌉, τ_promise ~ DiscreteUniform(15, 30) weekend / (24, 33) weekday (Kaggle delivery_time
   conditional distribution by day type), or fixed 25 min; the travel time itself comes from the road network, not from Kaggle.
7. Optional: cost_i ~ Gamma(k 4.89, θ 3.38) or a $2-binned histogram (Kaggle), only for heterogeneous order priority / penalty P_i, not used by default.
```

**What stays synthetic (no source for any of it)**: the hourly curve and day-type ratio (Section 6), the absolute order volume Λ, the point within a zone, the candidate radius R and distance decay, the Zipf rank assignment, repeat customers (not modelled), daytime workplace-population destinations (the papers only cover residence).

---

## 6. Time-of-day recommendation

**None of the three papers has any evidence on meal time, weekday/weekend or late night** (Buettner is "times per week", Bennett binarises frequency, Tahim has only rarely/weekly/daily). Kaggle's 71% weekend is sample composition, not a demand ratio. The hourly curve is therefore a **declared external assumption**; recommended sources in order of priority:

1. **NYC DCWP (2022) "A Minimum Pay Rate for App-Based Restaurant Delivery Workers in NYC"**: uses real trip data from Uber Eats/DoorDash/Grubhub/Relay and reports trip distributions by hour and day of week; digitise its hourly chart as f_hour.
2. Cross-check: the shape of the avenue bicycle counters in `datasets.md` (8th Ave @ 50th etc.) — no morning peak, 17–20h peak.
3. Placeholder (until 1 is done): a double-peak curve, lunch 11:30–14:00 at 28%, dinner 17:30–21:30 at 45%, late night 21:30–01:00 at 12%, remaining hours 15%; evening peak ≈ 1.6 × lunch peak; weekend daily volume = 1.15 × weekday daily volume, with a wider evening peak and a later lunch peak (brunch) on weekends. All flagged as assumption, placed in a separate `time_profile` block in the config.

---

## 7. Disagreements, gaps and risks

1. **Sex**: Bennett says men participate more (OR 1.23), Buettner is not significant after controlling for other variables, Tahim not significant. "Males order more" on proposal p. 13 has only one supporting paper, and the zone-level sex share barely varies (0.48–0.55); the 0.91 is retained only formally.
2. **Income/status**: both Bennett and Buettner's subjective status are positive, and Buettner's food insecurity is also positive (the authors themselves acknowledge the contradiction, hinting at unmeasured confounding), Tahim is zero. The "education" part of the proposal's "higher income and education" has no support at all, and Tahim even points the other way. We keep only a mild income term of 1.17.
3. **Children**: Bennett (weighted, n ≈ 20k) positive vs Tahim (snowball, crude OR) negative for adolescents; by evidence quality we take Bennett and shrink by 25%.
4. **Ethnicity**: both papers are positive, but Buettner interprets it as residential fast-food density (supply side), so it may partly be a spatial effect; if DOHMH restaurant density is later added as a zone variable, the ethnicity coefficient should be lowered to avoid double counting.
5. **Frequency vs participation**: Buettner's Poisson includes zeros, so the IRR is already the total effect "participation × frequency"; factors present in both papers (ethnicity, sex, income) can only use one source or a merged value, never a product (handled in Section 4(c)). There is no source for user frequency by age; we assume participant frequency is independent of age — which probably understates young zones (they may both participate more often and order more often).
6. **Ecological inference**: all coefficients are individual effects applied to tract composition, assuming independent factors within a zone with no interactions (neither Bennett nor Buettner estimated interactions). Campus, large group-quarters and nursing-home tracts will show extreme values and need the B26001 correction.
7. **Destination ≠ residence**: all three papers infer by respondent residence; office lunch, hotel and park orders have no source; a daytime weight layer from LEHD LODES workplace population can be added later (declared extension).
8. **External validity**: Bennett is a five-country pooled coefficient (the US country effect vs Australia has OR 0.99, so the pooled coefficients are reasonably applicable to the US); Buettner is a 2022 Omicron-period national non-probability panel of ages 18–25; Tahim is Brazil's 2020 lockdown. All three predate 2026 NYC penetration; the intercept (Λ) should be re-scaled with local data.
9. **Factors in the proposal without a source**: financial responsibility (paying one's own bill) has no ACS counterpart; subjective social status is proxied by income; food insecurity is proxied by SNAP and OFF by default.
10. **Kaggle's limits**: synthetic teaching data, provides shape priors only (uniform prep time, Zipf s≈1, cuisine shares); no timestamps/coordinates, cannot calibrate any spatial or time-of-day structure.

---

## Appendix A: ACS variable list (Census API, acs/acs5, tract, NY state 36, counties 005/047/061/081/085)

| Share | Numerator | Denominator |
|---|---|---|
| N_z (pop 18+) | B01001_001 − (B01001_003..006 + B01001_027..030) | — |
| s18_29 | B01001_007..011 + B01001_031..035 | pop 18+ |
| s30_44 | B01001_012..014 + B01001_036..038 | pop 18+ |
| s45_59 | B01001_015..017 + B01001_039..041 | pop 18+ |
| s60p | 1 − s18_29 − s30_44 − s45_59 | — |
| s_female | B01001_026 − (B01001_027..030) | pop 18+ |
| s_white / s_black / s_hisp | B03002_003 / B03002_004 / B03002_012 | B03002_001 |
| s_other | 1 − s_white − s_black − s_hisp | — |
| s_adequate | C17002_008 (≥ 2.00) | C17002_001 |
| h_pre | B11003 (own children under 6 only + under 6 and 6–17), married + male HH + female HH | B11003_001 |
| h_school | B11003 (own children 6–17 only), all three family types | B11003_001 |
| s_alone | B11001_008 | B11001_001 |
| s_student | B14007_017 + B14007_018 | pop 18+ |
| s_SNAP (optional) | B22010_002 | B22010_001 |
| group quarters | B26001_001 | subtract from N_z or cap M_stu ≤ 1.10 |

The GeoDa ACS 2008-12 NTA file lacks the 18–25 age band and the student-enrolment variable, and uses 2010 NTAs; not recommended (see `datasets.md`).

## Appendix B: reference implementation (Python)

```python
RR_AGE = {"s18_29": 3.4, "s30_44": 3.0, "s45_59": 1.9, "s60p": 1.0}
RR_ETH = {"s_white": 1.0, "s_black": 1.17, "s_hisp": 1.26, "s_other": 1.12}
RR_BIN = {"s_female": 0.91, "s_adequate": 1.17, "s_alone": 1.10, "s_student": 1.12}
RR_KID = {"h_pre": 1.22, "h_school": 1.29}
RR_FI  = {"s_SNAP": 1.38}          # sensitivity switch, default off

def zone_weight(z, food_insecurity=False):
    m = sum(z[k] * RR_AGE[k] for k in RR_AGE) * sum(z[k] * RR_ETH[k] for k in RR_ETH)
    for k, rr in RR_BIN.items():
        m *= 1 + z[k] * (rr - 1)
    m *= 1 + sum(z[k] * (rr - 1) for k, rr in RR_KID.items())
    if food_insecurity:
        m *= 1 + z["s_SNAP"] * (RR_FI["s_SNAP"] - 1)
    return z["pop18"] * m
# pi = w / w.sum()
```
