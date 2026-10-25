# Recalibrating the unserved-order penalty P_i and the lateness price v (NYC e-bike food delivery, USD 2025-2026)

All findings were verified on 2026-10-18. Brackets give the finding id. "Assumption" marks our own modelling choice, and "derived" marks our own arithmetic on sourced figures. The model currently runs `usd_sunk`: P_i = 30, w = 18 USD/h from order placement r_i, v = 36 USD/h from the promise b_i. The generator sets b_i = a_i + 25 min, so the promise falls 45-60 min after placement.

## 1. Summary

1. No platform pays a per-minute late price. Published late compensation is a flat, one-off credit of 5-10 USD, triggered at the promised time or 10 min after it, with no slope [doordash-premium-late-credit, doordash-vip-late-credit, grubhub_nyc-01, grubhub_nyc-02, ubereats-01]. Uber has removed its automatic 5-unit credit in Canada, Australia and Chile [ubereats-03, ubereats-04, ubereats-05], and probably in the US as well [ubereats-02, ubereats-06]. Standard DoorDash orders get only discretionary credits [doordash-standard-late-no-fixed-credit].
2. An order that is never delivered costs the platform much more than a late one. The customer is refunded and pays nothing [ubereats-09, ubereats-11, doordash-late-refunds-absorbed-by-platform, grubhub_nyc-03], yet the merchant is still paid for food it prepared [doordash-merchant-paid-cancelled-after-prep, ubereats-10, ubereats-11]. The platform also loses its fees and commission, about 13.97 USD per NYC delivery in Q4 2025 [grubhub_nyc-09].
3. On the newest DCWP data, the platform's cash loss on a prepared-but-undelivered NYC order is about 38 USD (derived). The full customer ticket is 42.08 USD [grubhub_nyc-09], already above the current P = 30.
4. Under the current pricing (w = 18, v = 36, P = 30), dropping an order beats serving it once the order is more than about 13-18 min late. A 60-90 min late order costs 67-99 USD to serve, 2.2-3.3 times P. The model therefore drops orders that every real platform would deliver.
5. We recommend a new base of **P_i = 60 USD** (system view, consistent with w being a customer time value), with low 40 (platform cash only) and high 80. We also recommend **v = 15 USD/h from b_i**. This is the least-squares linear fit to a 5 USD credit plus about 2 USD churn at 10 min late, rising about 9 USD/h after that.
6. With the new values, a 60 min late order costs 46.5-51 USD against P = 60, so serving is clearly preferred. Serving and dropping break even at about 76-85 min late, close to where real practice cancels or refunds late orders: 60 min in Cosmi et al. [literature-cosmi2025-rome], about 70 min in the Uber merchant rule [ubereats-13], and 30 min past ETA at Grubhub [grubhub_nyc-05].
7. Churn evidence is weak. No platform publishes a per-event effect. The usable anchors are a 5-10 % spending loss after one late Uber ride [industry-uber-late-trip-spend], an upper-bound slope from Hangzhou 2015 data [literature-mao2025-late-churn], and DoorDash's contribution profit of 1.53 USD per order [industry-doordash-contribution-per-order]. Every churn value below is therefore an assumption bounded by these figures.

## 2. Late-order compensation by platform

| Platform | Program | Amount | Threshold | Cap | Eligibility | Source (date, URL) |
|---|---|---|---|---|---|---|
| DoorDash US | Premium Delivery on-time guarantee | 10 USD credit, automatic, flat | >= 10 min after the latest delivery time shown at checkout | none stated (the 10 USD/month cap belongs to a different benefit) | select DashPass members; "limited-duration test"; void if the address changes | [doordash-premium-late-credit] undated page, (c) 2026, fetched 2026-10-18, help.doordash.com/en-us/consumers/article/premium-delivery-terms-and-conditions |
| DoorDash US | VIP Delivery / DashPass VIP | 10 USD credit, automatic | >= 10 min after the latest time in the window | none stated | select DashPass members; subtotal >= 12 USD; VIP status ran to 2026-06-30, so may have expired | [doordash-vip-late-credit] help.doordash.com/en-us/consumers/article/vip-delivery-terms-and-conditions |
| DoorDash US | standard orders | no published amount; discretionary via "Order Arrived late" | none | n/a | all | [doordash-standard-late-no-fixed-credit] help.doordash.com/en-us/consumers/article/what-can-i-do-if-my-food-was-delivered-late |
| DoorDash US | merchant side | late-delivery refunds paid by DoorDash, "typically" not charged to the merchant | n/a | n/a | n/a | [doordash-late-refunds-absorbed-by-platform] page updated 2026-10-18 |
| Grubhub | Grubhub Guarantee, On-Time | Perk worth >= 5 USD, Grubhub-funded, no cash | any delivery after the latest estimated range (no buffer) | none for lateness (the 15 USD cap applies to the price guarantee) | claim within 48 h; Perk expires in 30 days; **Seamless orders excluded** | [grubhub_nyc-01] terms effective 2025-10-28, lp.grubhub.com/legal/ghgterms; [grubhub_nyc-02] business.grubhub.com/blog/introducing-the-grubhub-guarantee/ |
| Uber Eats US | Uber One Promise (launch, 2021) | 5 USD Uber Cash, flat | Latest Arrival estimate missed | none stated | Uber One members, eligible deliveries | [ubereats-01] 2021-11-17 press release; [ubereats-02] third-party, 2023-11-19 |
| Uber Eats CA / AU / CL | same benefit, removed | 5 CAD (removed 2024-02-05), 5 AUD (removed 2024-11-19), 2,500 CLP (removed 2024-09-23) | n/a | n/a | n/a | [ubereats-03] news, [ubereats-04] third party, [ubereats-05] news |
| Uber Eats (US-oriented) | ad hoc support credit | anecdotes of 5-6 USD (about 15 %); 20 % of the order to keep a late order instead of cancelling | after Latest Arrival By; "often 45 min or more" | n/a | on request within 48 h; third-party guides | [ubereats-06] 2026-08-06; [ubereats-07] 2024-03-03 |
| Uber Eats US | merchant side | refunds for courier-caused lateness are not charged to the merchant; own-delivery merchants are charged at about 70 min past their ETA | ~70 min (own delivery only) | n/a | n/a | [ubereats-12], [ubereats-13] merchants.ubereats.com/us/en/order-errors/ |
| Instacart (grocery, context only) | 100 % satisfaction guarantee | up to total fees paid; FTC says late orders typically get a small future credit | outside the delivery window | fees | discretionary | [grubhub_nyc-07] (page 404; FTC complaint quote), [grubhub_nyc-08] FTC 2025-12-18 |
| Benchmark: how often lateness occurs | Intouch mystery shops, US, no paid tiers | 2025: 38 % of orders late vs the in-app estimate, average 10 min 16 s; Uber Eats 45 %, DoorDash 35 %, Grubhub 33 % | late by even 1 min | n/a | n/a | [industry-intouch-2025-late-share], [doordash-intouch-late-share] (corrected to the primary report) |

## 3. Cancelled or undelivered orders: who pays what

| Platform | Customer refund | Merchant payout | Lost platform fees | Other |
|---|---|---|---|---|
| DoorDash US | Customer-initiated, not late: full / partial / none depending on whether the restaurant confirmed and a Dasher was assigned [doordash-consumer-cancel-refund-table]. Terms: no contractual refund after merchant confirmation; credits are discretionary and expire in 6 months [doordash-terms-nonrefundable-discretionary]. DoorDash refunds late deliveries and no-shows itself [doordash-late-refunds-absorbed-by-platform] and has given voluntary credits for orders "cancelled by us or the merchant" [industry-doordash-credits-late-cancelled]. | Paid if cancelled after confirmation, the food was prepared and the merchant was not at fault; basis not stated [doordash-merchant-paid-cancelled-after-prep]. Merchant-fault errors are charged at 25-100 % of item price + tax [doordash-merchant-error-charges]. | Refunds and credits are booked against revenue, so each one reduces net revenue [doordash-10k-refunds-contra-revenue]. Costs of cancelled orders sit in cost of revenue, which totals 2.12 USD per order (derived; not broken out) [doordash-10k-cancelled-order-costs]. | Dasher: no fine for lateness or non-delivery, only contract violations [doordash-dasher-lateness-no-pay-penalty]. |
| Uber Eats | Free cancellation until the merchant accepts; afterwards the customer "may incur charges" [ubereats-09]. In a courier shortage the order is cancelled at no cost to the customer [ubereats-11]. A refund after Latest Arrival By is discretionary, not guaranteed [ubereats-08, corrected]. | Paid when the customer cancels after preparation, the courier cannot complete, or the order is never picked up [ubereats-10]. In a courier shortage the merchant is "refunded for the order" [ubereats-11]. | Customer refunds for undelivered or late Uber-courier orders are not charged to the merchant [ubereats-12]. Uber's company-wide line for consumer discounts, promotions, credits and refunds is 1.6 bn USD in FY2025, mostly promotions [ubereats-14]. | |
| Grubhub | Grubhub pays the refund when its courier is late or fails to arrive; amount not stated [grubhub_nyc-03]. Terms: refunds case by case [grubhub_nyc-06]. | Not explicit for Grubhub-courier failures (implied kept). Self-delivery merchants pay refunds when more than 30 min late or never delivered [grubhub_nyc-04], and since 2024-09-24 for cancellations more than 30 min past ETA [grubhub_nyc-05]. | | |
| NYC, all apps | Q4 2025 per delivery: subtotal 30.66, consumer fees 7.58, tip 1.12, tax 2.72, total 42.08; merchant fees 6.40 (20.9 %); platform fees + commission = 13.97 [grubhub_nyc-09]. 2025 full-year average 13.10; Q4 2024 revised to 12.63, not 13.25 [grubhub_nyc-10]. | Fee caps: 15 % delivery + 5 % basic or 20 % enhanced + 3 % payment [grubhub_nyc-12]. | | Riders must be paid the minimum rate (22.13 USD/h from 2026-04-01) for time on cancelled trips; Uber Eats paid 3.15 M USD restitution plus 0.35 M USD penalties and fees for not doing so [grubhub_nyc-13]. DCWP complaints are negligible: 37-40 non-delivery complaints a year [grubhub_nyc-14]. |
| Cancellation incidence | DoorDash goal for avoidable cancellations: under 1.1 % [doordash-avoidable-cancellation-target, industry-doordash-store-cancel-goal]. Otter: 1.5-3 % of restaurant digital sales lost to cancellations (global vendor data) [industry-otter-cancellation-share]. Zomato: more than 400,000 customer cancellations a month (India) [industry-zomato-cancelled-orders]. | | | |

## 4. Churn and customer value

| Quantity | Value | Source |
|---|---|---|
| DoorDash contribution profit per order (FY2025) | 1.53 USD (4.7 % of GOV) | [industry-doordash-contribution-per-order] (derived) |
| DoorDash Adjusted EBITDA per order | 0.88 USD (2.7 % of GOV) | [industry-doordash-ebitda-per-order] (derived) |
| Uber Delivery Adjusted EBITDA | 3.9 % of gross bookings, about 1.6 USD on a 40 USD ticket | [industry-uber-delivery-ebitda-margin] (derived) |
| DoorDash orders per MAU | about 5.4 per month, so contribution of about 8.2 USD per month or 99 USD per year per active user | [industry-doordash-mau-frequency] (derived) |
| Spending after one late ride (Uber, ride-hailing) | -5 to -10 % with no apology; a 5 USD coupon was the best apology; riders followed for 84 days | [industry-uber-late-trip-spend] (internal matching analysis, NBER WP; EJ 2022) |
| Lateness slope (Hangzhou 2015) | -2.70 orders per customer per month for each extra 10 min late (the printed coefficient implies 2.93); +0.74 for each extra 10 min early | [literature-mao2025-late-churn, industry-mao-late-future-orders, doordash-literature-late-churn-hangzhou]. Upper bound: 2.7 x 1.53 = about 4.1 USD per 10 min if the effect lasts one month (derived) |
| Shape of the effect | late lengthens interpurchase time more than early shortens it, and effects diminish with larger deviations (concave) | [industry-harter-qcommerce-repurchase] |
| Share of consumers ever late / cold / missing items | 50 / 50 / 44 % | [industry-chatmeter-2025-late-incidence] |
| Order frequency of US adults | 18.7 % order weekly or more; 38 % never | [industry-verasight-2026-frequency] |
| Uber One | about 2/3 of Delivery gross bookings; members become profitable after about 6 months | [ubereats-15] |
| DoorDash (qualitative) | operational mistakes lead to "worse customer retention and higher unit costs" | [doordash-q4-2025-letter-retention] |
| NYC scale | 3.3 M orders per week; tips 1.18 -> 2.29 USD after 2026-01-26 | [industry-nyc-dcwp-2026-orders, grubhub_nyc-11] |

Correction to cost_calibration.md section 5: the old churn term used revenue of 4.3 USD per order. Contribution profit (1.53 USD) is the better value of a lost future order, which lowers churn estimates by a factor of about 2.8.

## 5. What published optimisation studies use

| Study | Unserved order | Lateness | Ratio / note |
|---|---|---|---|
| Reyes, Erera, Savelsbergh, Sahasrabudhe, O'Neil, "The Meal Delivery Routing Problem", Optimization Online preprint, 2018 (no DOI) [literature-reyes2018-mdrp]; Grubhub MDRP instances [grubhub_nyc-15] | no money penalty; at most 0.5 % unserved (tuning rule); dropping ranks below any feasible assignment | click-to-door overage beyond a 40 min target; 90 min maximum; courier pay 10 per order, 15 per hour minimum | effectively lexicographic: serve first |
| Yildiz & Savelsbergh, Transportation Science 53(5):1372-1388, 2019, doi 10.1287/trsc.2018.0887 [literature-yildiz-savelsbergh-2019] | forbidden (hard constraint); p1 + epsilon (p1 = 10) only as a phase-1 repair term | hard 90 min click-to-door | serving is mandatory |
| Ulmer, Thomas, Campbell, Woyak, Transportation Science 55(1):75-100, 2021, doi 10.1287/trsc.2020.1000 [literature-ulmer2021-rmdp] | no rejection | minimise expected delay against deadlines (minutes or count not verified) | |
| Neria, Hildebrandt, Tzur, Ulmer, Transportation Science 59(2):433-450, 2025, doi 10.1287/trsc.2024.0510 [literature-neria2025-ghostkitchen] | no rejection | linear minutes beyond a 30 min promise, uncapped; freshness <= 20 min as a constraint | maximum delays reach about 100 min |
| Cosmi, Oriolo, Piccialli, Ventura, Omega 133:103237, 2025, doi 10.1016/j.omega.2024.103237 [literature-cosmi2025-rome] | rejection cost 10 (unitless) | step: 0 up to target+15 min, then 1 / 2 / 3 per 15 min band; more than 60 min late is always rejected | rejection = 3.3 x the worst late band; modelled on vouchers proportional to delay |
| Cosmi, Nicosia, Pacifici, IFAC-PapersOnLine 52(13):511-516, 2019, doi 10.1016/j.ifacol.2019.11.117 [literature-cosmi2019-ifac] | a late order counts as cancelled (unit loss) | binary at +/- 15 min | late = lost |
| Jahanshahi et al., Knowledge-Based Systems 243:108489, 2022, doi 10.1016/j.knosys.2022.108489 [literature-jahanshahi2022-drl] | rejection reward -15 | reward 45 - delivery time (min) | break-even at 60 min delivery |
| Auad, Erera, Savelsbergh, Transportation Science 58(1):67-93, 2024, doi 10.1287/trsc.2022.0042 [literature-auad2024-dqn] | lost order -1 | binary: lost if it cannot meet placement + 40 min | 1 lost order = 5 one-hour courier blocks |
| Behrendt, Savelsbergh, Wang, Transportation Science 57(4):889-907, 2023, doi 10.1287/trsc.2022.1152 [literature-behrendt2023-expired] | 200 per expired order | no late delivery allowed | 10 x ad hoc courier pay |
| Mousavi, Bodur, Cevik, Roorda, Optimization Online preprint, 2021 [literature-mousavi2021-crowdship] | 10, matched to 6.99-11.99 CAD / 10 USD backup delivery price | deadline 1-3 h | 2.5-5 x per-order pay |
| Klapp, Erera, Toriello, Transportation Science 52(2):402-415, 2018, doi 10.1287/trsc.2016.0682 [literature-klapp2018-ddwp] | 0.25-1 x maximum distance | n/a | same-day delivery, not meals |
| Liang et al. (Meituan), INFORMS J. Applied Analytics 54(1):84-101, 2024, doi 10.1287/inte.2023.0084 [literature-meituan2024-dispatch] | no money weight; under scarce supply the objective switched to completing orders, tolerating lateness | "time score" for overtime severity | industry practice: serving late is preferred to dropping |

None of these studies prices drops in real USD for the US. All of them make dropping clearly worse than serving late: by a hard constraint, a lexicographic rule, or a drop/late ratio of 3 or more.

## 6. Mapping to the model

### 6.1 P_i component build-up (USD per order, NYC Q4 2025 basis)

| Component | Low (platform cash) | Base (system) | High (system + heavy churn) | Borne by | Source |
|---|---|---|---|---|---|
| Lost consumer fees | 7.58 | 7.58 | 7.58 | platform | [grubhub_nyc-09] |
| Lost merchant commission | 6.40 | 6.40 | 6.40 | platform | [grubhub_nyc-09] |
| Merchant payout for prepared food = subtotal 30.66 - merchant fees 6.40 | 24.26 | 24.26 | 24.26 | platform (merchant made whole) | [ubereats-10, ubereats-11, doordash-merchant-paid-cancelled-after-prep]; payout basis is our assumption, since no page states it |
| **Platform cash loss (sub-total)** | **38.24** | 38.24 | 38.24 | platform | derived |
| Tax + tip on the refunded ticket (2.72 + 1.12) | 0 | 3.84 | 3.84 | state / rider (system only) | [grubhub_nyc-09] |
| = full ticket (lower bound on the customer's lost meal value) | n/a | 42.08 | 42.08 | system | [grubhub_nyc-09] |
| Customer's wasted wait before cancellation, w x 30 / 60 min | 0 | 9.0 | 18.0 | customer (system) | assumption; w = 18 from current calibration; cancellation timing anchored on [grubhub_nyc-05, ubereats-13, literature-cosmi2025-rome] |
| Churn (lost future contribution) | ~2 | 5 | 20 | platform | assumption. Base: 2-4 x the late-event loss of 1.1-2.3 USD (5-10 % of 84-day contribution of 22.8 USD) [industry-uber-late-trip-spend, industry-doordash-mau-frequency]. High: 20 % of 99 USD annual contribution |
| Rounding (unpriced consumer surplus or goodwill credit) | 0 | ~4 | 0 | | assumption |
| **P_i** | **40** | **60** | **80** | | |

Low (40) is the platform-only view: everything the platform loses in cash on a prepared order that is never delivered. Base (60) and high (80) are system views. They count the customer's lost meal (at least the ticket) and wasted waiting, which is consistent with the current w = 18 USD/h being a customer time value rather than a platform cost. A floor case of about 15-20 applies when an order is declined before the restaurant prepares it: lost fees of 13.10-13.97 USD plus minor churn; no merchant payout, because the customer cancels before acceptance [doordash-consumer-cancel-refund-table, ubereats-09, ubereats-10]. That floor is relevant only if the planner's drop decision is read as declining at placement.

### 6.2 Lateness cost

- **Evidence shape:** a one-off step of 5-10 USD at the promise or at promise + 10 min, with no slope and no cap [doordash-premium-late-credit, grubhub_nyc-01, ubereats-01]. A 5 USD coupon is also the best apology in Uber's experiment [industry-uber-late-trip-spend]. Churn grows with minutes late [literature-mao2025-late-churn] but with diminishing returns [industry-harter-qcommerce-repurchase].
- **Target function (assumption built from these):** zero within 10 min of b_i. At b_i + 10 min, a step of about 7 USD: an expected credit of 5 plus about 2 USD churn [industry-uber-late-trip-spend, derived]. After that, +9 USD/h. The 9 USD/h is our assumption, about 1/3 of the derived Hangzhou upper bound of ~25 USD/h (2.7 orders per 10 min x 1.53 USD, assuming the effect lasts one month).
- **Implied per-hour values:** the step alone, read as a rate over a 10 min band, is 30-60 USD/h (5-10 USD per 10 min). The marginal slope is 9 USD/h (range 4-25). The current v = 36 USD/h roughly matches the step band but wrongly keeps growing at that rate forever: at 60 min late it charges 36 USD, against about 14.5 USD on the target.
- **Model approximation:** least-squares fits over 10-90 min late. A single linear **v = 14.4, rounded to 15 USD/h, from b_i** fits better than a v from b_i + 10 min (fit 16.9 USD/h). Errors from b_i are -4.6 USD at 10 min late and +2.7 USD at 90 min late; from b_i + 10 the error is -7 USD at 10 min late. Recommendation: v = 15 USD/h from b_i, which needs no code change. The step is lost, so slightly-late orders are under-priced by about 5 USD.

### 6.3 Served-but-very-late vs dropped

Cost of serving = w (T + L) / 60 + v L / 60, where T is the promise in minutes after placement and L is the minutes late.

| Promise T | L late | Current (w 18, v 36) | Current P | Recommended (w 18, v 15) | Recommended P |
|---|---|---|---|---|---|
| 45 | 60 | 67.5 | 30 | 46.5 | 60 |
| 45 | 90 | 94.5 | 30 | 63.0 | 60 |
| 50 | 60 | 69.0 | 30 | 48.0 | 60 |
| 50 | 90 | 96.0 | 30 | 64.5 | 60 |
| 60 | 60 | 72.0 | 30 | 51.0 | 60 |
| 60 | 90 | 99.0 | 30 | 67.5 | 60 |
| break-even lateness | | 13-18 min | | 76-85 min | |

Under the current calibration, serving costs as much as dropping at about 16 min late (T = 50); this is the "about 29.6 vs 30" case. At 60-90 min late, serving costs 2.2-3.3 x P, so dropping always wins.

Under the recommendation, a 60 min late order costs 46.5-51 USD, which is 9-13.5 USD (15-22 %) below P = 60, so the two are no longer about equal. At 90 min late they are still roughly equal: serving is 3-7.5 USD (5-13 %) above P. That is intended. At that point real platforms have usually refunded or cancelled the order (Cosmi rejects beyond 60 min [literature-cosmi2025-rome]; the Uber merchant-charge line is about 70 min [ubereats-13]). For a typical late order of about 10 min [industry-intouch-2025-late-share], serving costs about 21 USD against P = 60.

## 7. Recommended sensitivity runs

1. **New base:** P = 60, w = 18 from r_i, v = 15 USD/h from b_i, all other `usd_sunk` values unchanged.
2. P sweep at v = 15: P = 20 (decline-before-preparation floor), 30 (legacy), 40 (platform cash), 60, 80.
3. Lateness structure at P = 60: v = 8 / 15 / 25 / 36 (legacy) from b_i; and v = 17 from b_i + 10 min (grace threshold; needs a pricing-only grace parameter rather than moving the reported promise).
4. Bridge run: legacy P = 30, v = 36, so the existing headline can be compared directly.
5. For every run, report: served share, number of late orders, number of orders more than 60 min late, rule-vs-ILP gap. The 29.6 % headline is mostly punctuality, and lowering v from 36 to 15 will probably shrink it.
6. Optional: P_i varying by customer frequency (weekly users about 19 % of adults [industry-verasight-2026-frequency]), for example P = 80 for frequent users and 50 for others.

## 8. Limitations and what could not be verified

- No finding was dropped, but several were corrected:
  - Intouch late shares moved to the primary-report figures [doordash-intouch-late-share].
  - The Grubhub guarantee excludes Seamless orders, which matters in NYC [grubhub_nyc-01].
  - The 15 USD cap in cost_calibration.md section 4 belongs to the price guarantee, not to lateness [grubhub_nyc-02].
  - Q4 2024 DCWP figures were revised, so platform revenue was 12.63, not 13.25 [grubhub_nyc-10].
  - "Full refund" claims are not stated on the Grubhub and Uber pages [grubhub_nyc-03, grubhub_nyc-04, ubereats-08].
  - The Mao coefficient implies 2.93, not 2.70 [industry-mao-late-future-orders].
- Not found or unverifiable:
  - the payout basis for cancelled-after-preparation orders (gross or net of commission) at any platform;
  - the current US status of the Uber One late credit, and DoorDash VIP after 2026-06-30;
  - Grubhub Perk claim rates;
  - any platform-wide cancellation, defect or never-delivered rate;
  - any measured churn effect of a failed (not late) food order;
  - Delivery-only refund totals for DoorDash or Uber;
  - NYC data on late deliveries or cancellations (DCWP collects trips_cancelled but does not publish it);
  - effect sizes in Harter et al. and in the published JOM version of Mao et al.;
  - lateness weights in Steever et al. 2019, Liu 2019, Liu-He-Shen 2021, and Dayarian & Savelsbergh 2020.
- The churn, wasted-wait, credit-expectation and 9 USD/h slope values are our assumptions. The Hangzhou and Uber-ride evidence comes from other markets or services.
- The ratios of drop cost to late cost from published studies are in abstract units. None is a USD calibration for NYC.
