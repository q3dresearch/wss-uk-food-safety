# Research questions — UK food safety ratings

## The spine

A food hygiene rating is a regulator's verdict on one shop on one day, displayed
in the window and published nationally. The Food Standards Agency publishes
**the current rating and the date it was given** — `RatingValue` and
`RatingDate` — and nothing else.

There is no history field in the record, no previous-rating endpoint, and
**web.archive.org holds zero captures of the bulk data files**. Backfill was
attempted and failed: 13 per-establishment records survive in the archive out of
613,146, which is 0.002%, and the API ignores date parameters. So when an
establishment is re-inspected the rating it used to hold is **gone**, and one
that went 5 → 1 → 5 is indistinguishable from one that has always been 5.

## What the capture actually contains

**613,146 establishments, 363 local authorities, all four UK nations.**

| field | why it matters |
| --- | --- |
| `FHRSID` | publisher-minted stable id — no name matching, no rename ambiguity |
| `RatingValue` | 0–5 (FHRS) or `Pass`/`Improvement Required` (FHIS). Never averaged across schemes |
| `RatingDate` | **the field that makes one capture useful** — see "answerable today" |
| `Scores` | Hygiene, Structural, ConfidenceInManagement, separately (FHRS only). **The scale is INVERTED — a higher score is worse.** Reading it the other way flips every conclusion drawn from it |
| `BusinessType` | 14 types, smallest 912 establishments — every one a usable cohort |
| `Geocode` | lat/long, which makes boundary designs possible |
| `NewRatingPending` | a forward-looking flag |
| `LocalAuthorityCode` | 363 units, a real control set |

| business type | establishments | | business type | establishments |
| --- | --- | --- | --- | --- |
| Restaurant/Cafe/Canteen | 141,044 | | Mobile caterer | 31,330 |
| Retailers – other | 120,571 | | Supermarkets | 15,934 |
| Other catering premises | 76,031 | | Hotel/B&B | 14,561 |
| Takeaway/sandwich shop | 63,114 | | Manufacturers/packers | 12,136 |
| Pub/bar/nightclub | 50,577 | | Distributors | 4,708 |
| Hospitals/Childcare/Caring | 43,337 | | Farmers/growers | 2,907 |
| School/college/university | 35,984 | | Importers/Exporters | 912 |

## Answerable TODAY, from one capture

`RatingDate` is the reason. Every establishment carries the date its current
rating was set, so the **age distribution of current ratings is a survival
curve**: counting establishments by the month they were last rated recovers
inspection volume going backwards, censored only by the inspections that have
since been superseded. The rate at which that curve decays *is* the
re-inspection hazard.

| # | question | status |
| --- | --- | --- |
| **A1** | **What is the national inspection volume, month by month?** | **answered.** ~20,000 a month, across 344 distinct months back to December 1993. 9.9% of standing ratings predate 2022 |
| **A2** | **Is inspection seasonal?** | **answered, and strongly.** Over 2022–2025, **November is 1.8× April** (37,622 vs 20,390); the autumn peak is Sep–Nov. Each month-of-year draws on the same four years, so censoring is balanced across the comparison |
| **A3** | **How current is a published rating, by authority?** | **answered.** Within FHRS alone — same scheme, same rules — the median runs 0.6 years (Stafford) to 3.3 years (Liverpool, 4,601 establishments). Scotland's FHIS runs to 7.1 years (Highland) |
| **A4** | **How stale are the authority extracts themselves?** | **answered.** 11 of 363 files were not regenerated in the capture month. Dumfries and Galloway's 2,719 establishments are served as current from a May extract, and nothing on the FSA site says so |
| **A5** | Which component drives a low rating — Hygiene, Structural, or Confidence in Management? | **partly, and suggestive.** In the authority sampled, establishments rated 1 average Hygiene 10.0, Structural 5.0 and **Confidence in Management 20.0** — management is the outlier. n=3, so this is a hint, not a finding. Needs a per-authority aggregate the parser does not yet emit; no new source required |

## Needs the archive

Cohort counted first, per the fleet's screening step 5 — a question whose
cohort cannot support it is marked so here rather than discovered later.

| # | question | cohort today | needs | status |
| --- | --- | --- | --- | --- |
| **B1** | **Does a bad rating get fixed, or does the business close?** | 18,249 rated 0–2 or *Improvement Required* | ~12 months | **the founding question.** Recovery and closure are identical in a snapshot. ±1 point needs ~9,600 outcomes; the cohort clears it |
| **B2** | How long does a 1 stay a 1? | 6,613 rated 1 | ~12 months | time-to-recovery, by authority and type. Clears its own sample size |
| **B3** | Do some business types recover faster? | smallest type 912 | ~18 months | 14 groups, every one large enough for a rate; the smallest needs longer |
| **B4** | Do establishments oscillate, or recover once? | 18,249 | ~24 months | needs three or more observations per establishment |
| **C1** | **Does a bad-rated business reappear under a new FHRSID at the same address?** | 18,249 | ≥2 captures | **the phoenix question, and nothing else can ask it.** FHRSID is minted per registration, so closing and re-registering resets the rating. Signal is: disappearance, then a new id at the same postcode and business type |
| **C2** | Does the re-registered business get a better rating? | subset of C1 | ≥3 captures | conditional on C1 returning anything at all |
| **D1** | **Do neighbouring authorities rate the same high street differently?** | 363 authorities, `Geocode` on every record | ~12 months | **the strongest identification strategy here.** Establishments within a short distance of an authority boundary face near-identical conditions and different regulators. A cross-boundary discontinuity in rating or in inspection cadence is the council, not the food |
| **D2** | Is re-inspection cadence collapsing in some councils? | 363 authorities | ~12 months | A3 gives the level today; whether it is *worsening* needs the series |
| **D3** | Does the awaiting-inspection backlog grow? | 52,764 never inspected | ~12 months | and how long the wait actually is, which nothing publishes |
| **E1** | Is the national rating distribution drifting upward? | 613,146 | ~24 months | grade inflation is invisible without a baseline, and this is the baseline |
| **E2** | Does Confidence in Management predict future failure better than Hygiene? | 18,249 | ~18 months | the genuinely predictive question: a management score is about the operator, a hygiene score about one day |
| **F1** | Do chains differ from independents? | `BusinessName` repeats | ~12 months | a chain is a name occurring many times; **no ownership field exists**, so this is a name heuristic and any finding is soft |

## Needs a source this repository does not have

| # | question | status |
| --- | --- | --- |
| **G1** | Do ratings track deprivation? | **`source not yet added`** — needs an IMD lookup joined on postcode district. The join key exists on both sides; measure the overlap before believing it |
| **G2** | Does inspection volume track council funding or EHO headcount? | **`source not yet added`** — MHCLG local authority finance and staffing. Would turn D2 from a description into an explanation |
| **G3** | Do rating changes follow outbreaks? | **not observable** — UKHSA does not publish outbreaks at premises level, and will not |
| **G4** | How many workers or customers does a closure affect? | **not observable** — the register names premises, never headcount or turnover |

## Who acts on these, and what changes

| who | questions | the decision it changes |
| --- | --- | --- |
| **An environmental health team** | A3, A4, D1, D2, D3 | whether their backlog and cadence are normal for their size. Nobody publishes the comparison, and A4 says some teams do not even know their own published file is four months old |
| **Someone choosing between two takeaways** | A3, B1, B2 | both show 5 today; one has held it nine months, the other four years. Only the archive separates them |
| **A journalist covering council capacity** | A2, A4, D2, D3 | where inspection is thinning, with named authorities and a denominator |
| **The FSA** | C1, C2, E1 | whether its own scheme is being reset by re-registration, and whether the grade distribution is drifting |
| **Food safety researchers** | B1–B4, E2 | recovery rates and the predictive value of the management score, neither published anywhere |

## What would make this worth stopping

1. **The FSA publishes rating history.** Then A1–A5 and B1–B4 are citations and
   this becomes a larder. Watch for a `history` field appearing in the record.
2. **C1 comes back empty.** If no establishment ever reappears under a new
   FHRSID at the same address, the phoenix question is answered *no* — a real
   negative result, and one of the two novel questions gone.
3. **Twelve months with no observed recovery from a 0–2 rating.** That would
   mean a bad rating is terminal, which is worth knowing and worth saying.
