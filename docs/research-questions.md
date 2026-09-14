# Research questions — UK food hygiene ratings

## The spine

A food hygiene rating is a regulator's verdict on a specific shop on a specific
day, displayed in the window and published on a national website. The Food
Standards Agency publishes **the current rating and the date it was given** —
`RatingValue` and `RatingDate` — and nothing else.

There is no history field in the record. There is no previous-rating endpoint.
The Internet Archive holds **zero** captures of the bulk data files. So when an
establishment is re-inspected, the rating it used to hold is **gone**, and an
establishment that went 5 → 1 → 5 is indistinguishable from one that has always
been 5.

That is the whole reason this archive exists.

## Why this register and not another

It was screened cohort-first, which is the check the sibling repository
[wss-sponsor-licences](https://github.com/q3dresearch/wss-sponsor-licences)
failed. That one watches **68** entities and can therefore only ever produce a
single base rate.

| | wss-sponsor-licences | this |
| --- | --- | --- |
| entities watched | 68 | **613,146** |
| events per year | ~68 | **~226,000** |
| identity | name + town, no id | **FHRSID, publisher-minted** |
| comparison groups | none with power | **363 local authorities** |

## Two schemes, and they are never averaged

| scheme | authorities | values | component scores |
| --- | --- | --- | --- |
| FHRS | 331 | `0`–`5`, `Exempt`, `AwaitingInspection` | Hygiene, Structural, ConfidenceInManagement |
| FHIS (Scotland) | 32 | `Pass`, `Improvement Required`, `Pass and Eat Safe`, `Awaiting Inspection` | **none** |

A mean rating computed across both is meaningless. `rating` travels verbatim as
a state, `scheme` rides on every establishment, and no numeric rating is ever
emitted for a FHIS record.

## The questions

One status — `source not yet added` — is the only one that justifies another
registry entry.

| # | question | cohort | needs | status |
| --- | --- | --- | --- | --- |
| F1 | **Does a bad rating get fixed, or does the business close?** | establishments rated 0–2 | ~12 months | **the founding question.** Unanswerable from any single capture and from any other source: the FSA publishes today's rating, never the path to it. An establishment that improves and one that disappears look identical in a snapshot |
| F2 | How long does a 1 stay a 1? | establishments rated 0–2 | ~12 months | needs the archive. `RatingDate` gives the age of the *current* rating, so one capture already says how long the present state has stood — but not what preceded it, and not when it ends |
| F3 | **Do some local authorities rate harder than others?** | 363 authorities | partly answerable now | the distribution by authority is visible in one capture, but a distribution is not a judgement: a council with more low ratings may have worse food or a harder marker. Separating the two needs the same businesses observed across time |
| F4 | Is the rating distribution drifting upward? | all | ~24 months | needs the archive. If the national share of 5s rises with no change in inspection volume, that is grade inflation and nobody is positioned to see it |
| F5 | **How long do new businesses wait for a first inspection?** | `AwaitingInspection` / `Awaiting Inspection` | ~12 months | needs the archive to measure the wait, but the backlog is already visible and uneven — Glasgow City carries 2,044 awaiting inspection against 6,632 establishments |
| F6 | Is re-inspection cadence collapsing in some councils? | 363 authorities | partly answerable now | the median age of the current rating is computable per authority today, and already ranges from ~1.4 years to ~3.6 years. Whether it is *worsening* needs the series |
| F7 | Does a business with a bad rating reappear under a new FHRSID? | establishments rated 0–2 | ≥2 captures | **the phoenix question, and the one nothing else can ask.** FHRSID is minted per registration, so a closure and a fresh registration at the same address reset the rating. Same postcode district + same business type + a disappearance followed by a new id is the signal |
| F8 | Do chains and independents differ? | `BusinessName` repeated across authorities | partly answerable now | a chain is a name occurring many times; no ownership field exists. Weak identity, so any finding is soft and must be labelled as a name heuristic |

## Who acts on these, and what changes

| who | questions | the decision it changes |
| --- | --- | --- |
| **An environmental health team** | F3, F5, F6 | whether their own backlog and rating distribution is normal for their size. Nobody currently publishes the comparison |
| **Someone choosing between two takeaways** | F1, F2 | both show 5 today. One has held it for four years; the other was a 1 last year. Only the archive can tell them apart |
| **A journalist covering council capacity** | F5, F6 | whether inspection backlogs are growing, and where. The current snapshot shows the level, never the trend |
| **Food safety researchers** | F1, F4, F7 | recovery rates and re-registration behaviour, neither of which is published anywhere |
| **The FSA itself** | F4, F7 | whether its own scheme is being gamed by re-registration |

## What would make this worth stopping

1. **The FSA publishes rating history.** Then F1, F2 and F4 are citations and
   this becomes a larder. Watch for a `history` field appearing in the record.
2. **F7 comes back empty.** If no establishment ever reappears under a new
   FHRSID at the same address, the phoenix question is answered *no* and one of
   the two novel questions is gone. That is still worth recording.
3. **Twelve months with no observed rating recovery.** That would mean a bad
   rating is terminal, which is worth knowing and worth saying.
