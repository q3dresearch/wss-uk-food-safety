# Data shape

*Generated 2026-09-15T13:15:08Z by `wss schema` from the derived rows. Do not hand-edit — regenerate after any derive.*

**You should not need to download anything to read this.**

- **46,466 observations** across 5 partition(s), in **1 series**
  - `fsa.fhrs.ratings` — 46,466 rows, **39560 entities**
- Raw: 0 file(s), 0 bytes on disk, 1 capture date(s), 2026-09-14 → 2026-09-14

## Sources

| source | cadence | endpoints | storage | personal data | licence |
| --- | --- | ---: | --- | --- | --- |
| `fsa.fhrs.ratings` | monthly | 363 | object | parties_only | Open Government Licence v3.0 — https://www.nationalarchives. |

## Columns

```
series_id, entity_id, observed_at, captured_at, metric, value, unit, source_id, raw_ref, parser_version
```

`entity_id` looks like: **fsa.fhrs.ratings** `authority:021`, `authority:021:rated:2005-09`, `authority:021:rated:2006-03`

## Metrics

| metric | series | rows | entities | type | unit | distinct | range / samples |
| --- | --- | ---: | ---: | --- | --- | ---: | --- |
| `establishments_listed` | fsa.fhrs.ratings | 39,560 | 39560 | number | count | 1176 | `1` … `10221` |
| `extract_date` | fsa.fhrs.ratings | 363 | 363 | date | date | 20 | `2026-04-22` … `2026-09-13` |
| `median_rating_date` | fsa.fhrs.ratings | 363 | 363 | date | date | 187 | `2019-08-22` … `2026-02-18` |
| `name` | fsa.fhrs.ratings | 363 | 363 | text | text | 363 | `Aberdeen City`, `Aberdeenshire`, `Adur` |
| `new_rating_pending` | fsa.fhrs.ratings | 363 | 363 | number | count | 41 | `0` … `81` |
| `score_confidenceinmanagement_total` | fsa.fhrs.ratings | 1,818 | 1818 | number | count | 562 | `0` … `15565` |
| `score_hygiene_total` | fsa.fhrs.ratings | 1,818 | 1818 | number | count | 498 | `0` … `13635` |
| `score_structural_total` | fsa.fhrs.ratings | 1,818 | 1818 | number | count | 574 | `0` … `16325` |

## Partitions

- `derived/observations/2026-04.csv.gz`
- `derived/observations/2026-05.csv.gz`
- `derived/observations/2026-07.csv.gz`
- `derived/observations/2026-08.csv.gz`
- `derived/observations/2026-09.csv.gz`
