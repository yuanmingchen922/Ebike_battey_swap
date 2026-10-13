# Kaggle FoodHub (`food_order.csv`) calibration tables

Source: Kaggle ahsan81 "Food Ordering and Delivery App Dataset", `food_order.csv`, 1,898 orders x 9 columns, no missing values. Machine-readable parameters: `kaggle_calibration.json` (same folder). Analysis: pandas/scipy, 2026-10-12.

## 1. Verification of `notes/datasets.md` claims

| Claim in datasets.md | Computed | Verdict |
|---|---|---|
| 1,898 orders x 9 columns | 1,898 x 9; 1,200 customers, 178 restaurants, 14 cuisines | OK |
| Prep time 20-35 min, approx uniform | min 20, max 35, mean 27.37, sd 4.63; chi-square vs discrete uniform p = 0.995 | OK (exactly uniform) |
| Delivery time 15-33 min, mean 24.2 | min 15, max 33, mean 24.16, sd 4.97, median 25 | OK |
| Cuisine: American 31%, Japanese 25%, Italian 16%, Chinese 11% | 30.8 / 24.8 / 15.7 / 11.3 % | OK |
| Top-5 restaurants = 33% | 33.4% (Shake Shack 219, Meatball Shop 132, Blue Ribbon Sushi 119, BR Fried Chicken 96, Parm 68) | OK |
| 71% weekend | 71.2% (1,351 Weekend / 547 Weekday) | OK |
| (not in notes) cost | mean 16.50, sd 7.48, median 14.14, IQR 12.08-22.30, range 4.47-35.41 | added |
| (not in notes) rating | 38.8% "Not given"; given ratings 3/4/5 = 188/386/588, mean 4.34 | added |

## 2. Fitted distributions (minutes)

### food_preparation_time (n=1898, mean 27.37, sd 4.63)

| Family | Parameters | KS stat | p | AIC |
|---|---|---|---|---|
| **Discrete uniform** | integers 20..35 | **0.015** | chi2 p = 0.995 | - |
| Normal | mu 27.37, sigma 4.63 | 0.094 | 5e-15 | 11209 |
| Lognormal | s 0.172, scale 26.97 | 0.098 | 2e-16 | 11220 |
| Gamma | k 34.3, theta 0.797 | 0.093 | 9e-15 | 11206 |

Recommendation: `DiscreteUniform(20, 35)`. Prep time is independent of cuisine (per-cuisine means 26.4-28.6), cost (r = 0.04), day type (Welch t = -0.95, p = 0.34) and delivery time (r = 0.01). This is a synthetic generator signature.

Histogram (value: count): 20:119, 21:135, 22:123, 23:123, 24:121, 25:113, 26:115, 27:123, 28:121, 29:109, 30:119, 31:116, 32:113, 33:118, 34:113, 35:117.

### delivery_time (n=1898, mean 24.16, sd 4.97)

| Family | Parameters | KS stat | p | AIC |
|---|---|---|---|---|
| Discrete uniform | integers 15..33 | 0.079 | chi2 p = 3e-39 | - |
| Normal | mu 24.16, sigma 4.97 | 0.096 | 1e-15 | 11478 |
| Lognormal | s 0.219, scale 23.61 | 0.130 | 3e-28 | 11623 |
| Gamma | k 22.0, theta 1.098 | 0.116 | 1e-22 | 11556 |

None of the pooled fits is acceptable because the marginal is a step-shaped mixture:

| Day type | n | range | mean | sd | chi2 vs discrete uniform | KS |
|---|---|---|---|---|---|---|
| Weekday | 547 | 24..33 | 28.34 | 2.89 | p = 0.077 | 0.033 |
| Weekend | 1351 | 15..30 | 22.47 | 4.63 | p = 0.998 | 0.007 |

Recommendation: `Weekday ~ DiscreteUniform(24,33)`, `Weekend ~ DiscreteUniform(15,30)`; or sample from the empirical histogram conditional on day type.

Pooled histogram: 15:87, 16:90, 17:78, 18:83, 19:90, 20:88, 21:81, 22:85, 23:77, 24:162, 25:120, 26:141, 27:138, 28:148, 29:148, 30:133, 31:41, 32:59, 33:49.

### cost_of_the_order (USD)

Gamma(k 4.89, theta 3.38) KS 0.077; lognormal KS 0.092; normal KS 0.137. All rejected at n=1898; use the 2-USD-bin empirical histogram in the JSON.

## 3. Cuisine mix (shares of orders)

| Cuisine | Share | Cuisine | Share |
|---|---|---|---|
| American | 0.3077 | Middle Eastern | 0.0258 |
| Japanese | 0.2476 | Mediterranean | 0.0242 |
| Italian | 0.1570 | Thai | 0.0100 |
| Chinese | 0.1133 | French | 0.0095 |
| Mexican | 0.0406 | Southern | 0.0090 |
| Indian | 0.0385 | Korean | 0.0068 |
| | | Spanish | 0.0063 |
| | | Vietnamese | 0.0037 |

## 4. Restaurant popularity (178 restaurants)

| Top-k | Share of orders |
|---|---|
| 1 (Shake Shack) | 11.5% |
| 5 | 33.4% |
| 10 | 46.7% |
| 20 | 62.9% |

Gini of order counts = 0.707. Count-frequency: 50 restaurants with 1 order, 23 with 2, 23 with 3; max 219.

| Rank-size (Zipf) OLS on log count vs log rank | slope | R^2 |
|---|---|---|
| all 178 | -1.294 | 0.950 |
| counts >= 5 (69 restaurants) | -1.005 | 0.968 |
| top 50 | -0.918 | 0.974 |
| Clauset discrete power-law MLE on counts, xmin=1 | alpha = 1.48 | - |

The full-range slope is steepened by the long tail of singletons (a truncation artefact of a 1,898-order sample). Recommendation: Zipf exponent s ~ 1.0 (classic Zipf) for the body; `weight(rank) ∝ rank^-1.0`, then optionally thin the tail. Lognormal on counts (s 1.26, scale 3.93) is rejected (KS p = 0.001).

## 5. Weekday vs weekend

| | Weekday | Weekend |
|---|---|---|
| orders | 547 (28.8%) | 1351 (71.2%) |
| delivery_time mean (sd) | 28.34 (2.89) | 22.47 (4.63) |
| prep_time mean | 27.2 | 27.4 |
| cost mean | 16.31 | 16.58 |

Welch t = 33.3, p = 2.6e-184 (Mann-Whitney p = 7e-119): weekday deliveries are 5.9 min slower. Prep time and cost do not differ by day type. The 71% weekend share is a composition of the sample, not a demand rate (a 7-day week with 2 weekend days would imply weekend days carry 6.2x the weekday daily volume, which is implausible).

## 6. Customer repeat distribution (1,200 customers)

| Orders per customer | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| customers | 784 | 267 | 83 | 33 | 19 | 6 | 4 | 1 | 1 | 1 | 1 |

Mean 1.58 orders/customer; 65% of customers order once; 58.7% of orders come from repeat customers.

## Caveats

- Synthetic teaching data for a fictional platform (FoodHub); exactly uniform prep times and the clean two-range delivery-time mixture confirm a hand-built generator. Use only as a shape prior.
- No timestamps, coordinates, courier IDs or distances: nothing here calibrates hour-of-day demand, trip length, speed or spatial demand. delivery_time cannot be decomposed into travel vs waiting.
- Only 178 restaurants (Manhattan-style names) vs 27k DOHMH restaurants; cuisine labels are 14 coarse classes vs DOHMH's 90.
- Weekend share and weekday/weekend delivery-time gap are sample artefacts and should not be read as NYC behaviour.
