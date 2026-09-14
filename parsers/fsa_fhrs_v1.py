"""fsa-fhrs.v1 — every UK food hygiene rating, and the one that was there before.

WHAT PERISHES. The record carries `RatingValue` and `RatingDate` and nothing
else: what the rating is now, and when it was set. There is no history,
previous, prior or former field anywhere in the API, and web.archive.org holds
no capture of these bulk files at all. So an establishment that went 5 to 1 to 5
reads exactly like one that has always been 5, and the 1 is unrecoverable.

ONE FILE PER AUTHORITY, SO THERE IS NO NATIONAL FEED OBSERVATION HERE. `parse`
is called once per endpoint, 363 times a capture. Emitting `feed:fsa_fhrs` with
`establishments_listed` would write 363 rows that each claim to be the national
total and differ from one another -- the same grain mistake that has bitten this
fleet three times. Totals belong to whoever reads the table and sums the
authorities; this parser only ever speaks for the authority in front of it.

TWO SCHEMES THAT MUST NOT BE AVERAGED. 331 authorities run FHRS and score 0 to 5
with Hygiene, Structural and ConfidenceInManagement components. 32 Scottish
authorities run FHIS, whose values are Pass, Improvement Required, Pass and Eat
Safe and Awaiting Inspection, with no component scores at all. A mean across
both is meaningless, so `rating` travels VERBATIM as a state and no numeric
rating is ever emitted for FHIS. `scheme` rides on every establishment so no
downstream reader can merge them by accident.

THE FILE CHECKS ITSELF AND SO DOES THIS PARSER. Each extract opens with a
Header carrying ExtractDate, ItemCount and ReturnCode. The count parsed is
compared against the count the publisher declared, because a loop that silently
read half a file is indistinguishable from an authority that shrank -- and a
ReturnCode that is not Success means the extract failed however well-formed the
XML is.

OBSERVED AT THE EXTRACT DATE, NOT THE FETCH. ExtractDate is when the FSA built
the file, which is what the ratings are true as of. Using the fetch time would
date every reading to whenever the cron happened to run.

ADDRESSES ARE READ AND DELIBERATELY NOT EMITTED. AddressLine1/3/4 and PostCode
are in the raw file and a home-based caterer's business address is their home
address. The raw capture keeps them because capture is the irreversible step;
the derived table keys on FHRSID and carries only the postcode DISTRICT, which
is the geography the questions need and not a doorstep.
"""

import collections
import re
import xml.etree.ElementTree as ET

from wss import derive

PARSER_VERSION = "1"

# FHRS scores where a rating is numeric; FHIS records carry no Scores element.
_SCORES = ("Hygiene", "Structural", "ConfidenceInManagement")
# Outward code only: "SW1A 1AA" -> "SW1A". Never the full postcode.
_OUTWARD = re.compile(r"^\s*([A-Z]{1,2}\d[A-Z\d]?)\s*\d[A-Z]{2}\s*$", re.I)


def _text(node, tag: str) -> str:
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def parse(body: bytes, ctx: derive.ParseContext):
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"fsa-fhrs.v1: not well-formed XML -- {exc}")

    header = root.find("Header")
    if header is None:
        raise ValueError("fsa-fhrs.v1: no <Header>. Every FSA extract carries "
                         "one with ExtractDate, ItemCount and ReturnCode")
    code = _text(header, "ReturnCode")
    if code != "Success":
        raise ValueError(
            f"fsa-fhrs.v1: the publisher says this extract failed -- "
            f"ReturnCode={code!r}. The XML can be perfectly well-formed and "
            f"still be an error document")
    extract_date = _text(header, "ExtractDate")
    declared = _text(header, "ItemCount")
    observed_at = f"{extract_date}T00:00:00Z" if len(extract_date) == 10 else None

    ests = root.findall(".//EstablishmentDetail")
    if declared.isdigit() and int(declared) != len(ests):
        raise ValueError(
            f"fsa-fhrs.v1: parsed {len(ests)} establishments but the Header "
            f"declares ItemCount={declared}. A half-read file and a shrinking "
            f"authority look identical without this check")

    authority = authority_code = ""
    by_rating: collections.Counter = collections.Counter()
    by_type: collections.Counter = collections.Counter()
    pending = 0
    ages: list[str] = []

    for est in ests:
        fhrsid = _text(est, "FHRSID")
        if not fhrsid:
            continue
        authority = authority or _text(est, "LocalAuthorityName")
        authority_code = authority_code or _text(est, "LocalAuthorityCode")
        scheme = _text(est, "SchemeType") or "unknown"
        rating = _text(est, "RatingValue") or "unknown"
        rated_on = _text(est, "RatingDate")
        btype = _text(est, "BusinessType") or "unknown"

        by_rating[rating] += 1
        by_type[btype] += 1
        if _text(est, "NewRatingPending").lower() == "true":
            pending += 1
        if len(rated_on) == 10:
            ages.append(rated_on)

        eid = f"est:{fhrsid}"
        # VERBATIM. "5" and "Pass" and "Awaiting Inspection" are all real values
        # from two different schemes; the parser does not rank them.
        yield derive.Observation(eid, "rating", rating, "state", observed_at=observed_at)
        yield derive.Observation(eid, "scheme", scheme, "state", observed_at=observed_at)
        yield derive.Observation(eid, "business_type", btype, "state", observed_at=observed_at)
        if rated_on:
            # The whole reason an unchanged rating still carries information:
            # this says how long the current rating has stood.
            yield derive.Observation(eid, "rating_date", rated_on, "date",
                                     observed_at=observed_at)
        postcode = _text(est, "PostCode")
        outward = _OUTWARD.match(postcode)
        if outward:
            yield derive.Observation(eid, "postcode_district", outward.group(1).upper(),
                                     "text", observed_at=observed_at)

        scores = est.find("Scores")
        if scores is not None:
            for tag in _SCORES:
                value = _text(scores, tag)
                if value.isdigit():
                    yield derive.Observation(eid, f"score_{tag.lower()}", int(value),
                                             "count", observed_at=observed_at)

    if not authority_code:
        raise ValueError("fsa-fhrs.v1: no LocalAuthorityCode on any record")

    # The authority is the largest grain this parser is entitled to speak for.
    aid = f"authority:{authority_code}"
    yield derive.Observation(aid, "name", authority, "text", observed_at=observed_at)
    yield derive.Observation(aid, "establishments_listed", len(ests), "count",
                             observed_at=observed_at)
    yield derive.Observation(aid, "new_rating_pending", pending, "count",
                             observed_at=observed_at)
    yield derive.Observation(aid, "extract_date", extract_date, "date",
                             observed_at=observed_at)
    if ages:
        ages.sort()
        yield derive.Observation(aid, "median_rating_date", ages[len(ages) // 2],
                                 "date", observed_at=observed_at)
    for rating, n in sorted(by_rating.items()):
        # Keyed by authority AND rating, because a bare `rating:5` entity would
        # be written 363 times a capture with 363 different values.
        yield derive.Observation(f"{aid}:rating:{rating}", "establishments_listed",
                                 n, "count", observed_at=observed_at)
    for btype, n in sorted(by_type.items()):
        yield derive.Observation(f"{aid}:type:{btype}", "establishments_listed",
                                 n, "count", observed_at=observed_at)


derive.register("fsa-fhrs.v1", parse, PARSER_VERSION)
