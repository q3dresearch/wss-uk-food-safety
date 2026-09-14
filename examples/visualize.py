#!/usr/bin/env python3
"""Render charts from derived/observations/*.csv.gz as SVG.

    python examples/visualize.py

  nothing-is-kept.svg       613,146 ratings, no history anywhere, and the
                            cohort that makes the questions answerable
  inspection-recency.svg    every authority's median rating age, named at
                            both ends, within one scheme
  what-it-can-answer.svg    what the cohort size actually buys, and when

Reads the derived table, never the raw archive. Stdlib only, deterministic
output: the same observations always produce the same bytes.

Only the authority-level aggregates are in git; the per-establishment series
is withheld to object storage (see the registry's `publish: aggregates`). Every
chart here is therefore drawn from what a reader of the repo can also see.
"""

from __future__ import annotations

import collections
import csv
import datetime
import glob
import gzip
import io
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "examples" / "charts"
TODAY = datetime.date(2026, 9, 14)

SURFACE = "#fcfcfb"; INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"
GRID = "#e1e0d9"; BASELINE = "#c3c2b7"; HUE = "#2a78d6"; HUE_SOFT = "#9ec5f4"
ACCENT = "#eb6834"; DEAD = "#b8b6ad"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# The two schemes are told apart by the words only FHIS uses. Testing for FHRS
# membership instead splits them 358/5 rather than 331/32, because both schemes
# spell "awaiting inspection" and the register is inconsistent about the space.
# A discriminator has to be built from values the other side CANNOT have.
FHIS_ONLY = {"Pass", "Improvement Required", "Pass and Eat Safe"}


def T(x, y, t, size=12, fill=INK, anchor="start", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family=\'{FONT}\' font-size="{size}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{escape(str(t))}</text>')


def R(x, y, w, h, fill, rx=0):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" '
            f'height="{max(h,0):.1f}" fill="{fill}" rx="{rx}"/>')


def L(x1, y1, x2, y2, stroke=GRID, width=1):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width}"/>')


def C(cx, cy, r, fill, opacity=1.0):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" '
            f'fill-opacity="{opacity}"/>')


def head(w, h, title, sub, note=""):
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         R(0, 0, w, h, SURFACE), T(56, 48, title, 20, INK, weight="600"),
         T(56, 74, sub, 13, INK2)]
    for i, line in enumerate(l for l in ([note] if isinstance(note, str) else note) if l):
        p.append(T(56, 96 + i * 16, line, 12, MUTED))
    return p


def save(parts, name, w, h):
    OUT.mkdir(parents=True, exist_ok=True)
    svg = "\n".join(parts) + "\n</svg>\n"
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"  wrote examples/charts/{name}")


def load():
    """Authority-level aggregates, keyed by authority code."""
    auth: dict[str, dict] = collections.defaultdict(dict)
    ratings: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    rated: dict[str, dict] = collections.defaultdict(dict)
    for path in sorted(glob.glob(str(REPO / "derived" / "observations" / "*.csv*"))):
        with io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                eid = r["entity_id"]
                if not eid.startswith("authority:"):
                    continue
                code = eid.split(":")[1]
                if ":rating:" in eid:
                    if r["metric"] == "establishments_listed":
                        ratings[code][eid.split(":rating:")[1]] += int(r["value"])
                elif ":rated:" in eid:
                    rated[code][eid.split(":rated:")[1]] = int(r["value"])
                elif ":type:" not in eid:
                    # A SUFFIX TEST THAT LISTS TWO OF THE THREE SUB-ENTITIES IS A
                    # TRAP. ":rated:<YYYY-MM>" contains neither ":rating:" nor
                    # ":type:", so it fell through to here and its monthly bucket
                    # overwrote the authority's establishments_listed -- the
                    # national total read 4,399 instead of 613,146. Every new
                    # sub-entity the parser emits must be handled here explicitly.
                    auth[code][r["metric"]] = r["value"]
    return auth, ratings, rated


def _scheme_map():
    """FHRS vs FHIS per authority, inferred from the rating vocabulary the
    authority actually uses. Inferred rather than hard-coded so the chart
    cannot drift from the data it is drawn from."""
    return None


def chart_nothing_is_kept(auth, ratings):
    w, h = 940, 500
    national = collections.Counter()
    for c in ratings.values():
        national.update(c)
    total = sum(national.values())
    bad = sum(national[k] for k in ("0", "1", "2"))
    improve = national.get("Improvement Required", 0)
    awaiting = national.get("AwaitingInspection", 0) + national.get("Awaiting Inspection", 0)

    p = head(w, h, f"{total:,} ratings, and no record of the one before",
             "The Food Standards Agency publishes the current rating and the date "
             "it was given. There is no history field anywhere in the record.",
             ["No previous-rating endpoint, and web.archive.org holds ZERO captures "
              "of the bulk data files.",
              "So an establishment that went 5, then 1, then 5 again reads exactly "
              "like one that has always been 5, and the 1 is gone."])

    # The 381,728 fives are deliberately NOT a bar. On one linear axis they
    # flatten the three cohorts this archive is actually about into slivers,
    # and a log axis would make the bars lie about their ratios.
    rows = [("awaiting a first inspection", awaiting, HUE,
             "how long have they waited? no published answer"),
            ("rated 0, 1 or 2 today", bad, ACCENT,
             "does it recover, or close? nothing records which"),
            ("Improvement Required (Scotland)", improve, ACCENT,
             "the FHIS equivalent, on its own scale")]
    x0, y0, row = 330, 176, 54
    widest = max(n for _, n, _, _ in rows)
    for i, (label, n, col, note) in enumerate(rows):
        y = y0 + i * row
        p.append(T(x0 - 16, y + 13, label, 12.5, INK, anchor="end", weight="600"))
        p.append(R(x0, y, max(420 * n / widest, 2), 17, col, rx=4))
        p.append(T(x0 + max(420 * n / widest, 2) + 10, y + 13, f"{n:,}", 12, INK, weight="600"))
        if note:
            p.append(T(x0, y + 32, note, 11, MUTED))
    y = y0 + len(rows) * row + 16
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, f"{bad + improve:,} establishments are carrying a bad rating right now, "
                      f"and {awaiting:,} have never been inspected.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               f"A further {national.get('5', 0):,} hold a 5 today. The record says "
               f"when it was given, never what it replaced.", 12, INK2))
    p.append(T(56, y + 46,
               "That is the cohort. The sibling repository wss-sponsor-licences "
               "watches 68 entities and can only ever", 12, INK2))
    p.append(T(56, y + 64,
               "produce one number; this one can answer questions about groups.",
               12, INK2))
    save(p, "nothing-is-kept.svg", w, h)


def chart_inspection_recency(auth, ratings):
    """How old the current rating is, per authority, within ONE scheme.

    Scheme is inferred from the vocabulary each authority uses, not assumed:
    mixing FHRS and FHIS on one axis would compare two different inspection
    regimes and call the difference enforcement.
    """
    recs = []
    for code, a in auth.items():
        d = a.get("median_rating_date", "")
        if len(d) != 10:
            continue
        scheme = "FHIS" if set(ratings[code]) & FHIS_ONLY else "FHRS"
        years = (TODAY - datetime.date.fromisoformat(d)).days / 365
        recs.append((years, scheme, a.get("name", "?"),
                     int(a.get("establishments_listed", 0))))
    recs.sort()
    fhrs = [r for r in recs if r[1] == "FHRS"]
    fhis = [r for r in recs if r[1] == "FHIS"]

    w, h = 940, 560
    x0, x1 = 150, w - 150
    hi = math.ceil(max(r[0] for r in recs))
    p = head(w, h, "How long ago was the rating in the window actually given?",
             "Median age of the current rating, one dot per local authority. "
             "The two schemes are drawn apart, never averaged.",
             [f"Within FHRS alone \u2014 same scheme, same rules \u2014 the median "
              f"runs {fhrs[0][0]:.1f} to {fhrs[-1][0]:.1f} years. That is a "
              f"{fhrs[-1][0]/fhrs[0][0]:.0f}\u00d7 spread in how current a "
              f"published rating is.",
              "A rating is displayed in the window with no indication of its age."])

    def X(v):
        return x0 + v / hi * (x1 - x0)

    for tick in range(0, hi + 1):
        p.append(L(X(tick), 150, X(tick), 386, GRID))
        p.append(T(X(tick), 404, f"{tick}y", 10.5, MUTED, anchor="middle"))

    for band, (label, group, col, yy) in enumerate((
            (f"FHRS \u2014 {len(fhrs)} authorities", fhrs, HUE, 214),
            (f"FHIS \u2014 {len(fhis)} Scottish authorities", fhis, ACCENT, 330))):
        p.append(T(56, yy - 40, label, 12, INK, weight="600"))
        med = group[len(group) // 2][0]
        p.append(L(X(med), yy - 30, X(med), yy + 30, INK2, 1))
        # Below the dots: at band-title height it collides with the title,
        # which sits at the same y and runs past the median line.
        p.append(T(X(med), yy + 46, f"median {med:.1f}y", 10.5, INK2, anchor="middle"))
        for i, (years, _s, _n, count) in enumerate(group):
            # Area by establishment count: a 3-establishment port authority and
            # Birmingham must not be one dot each.
            p.append(C(X(years), yy + ((i * 37) % 23) - 11,
                       max(2.0, math.sqrt(count) / 14), col, 0.5))

    y = 440
    p.append(L(56, y, w - 56, y, GRID)); y += 26
    p.append(T(56, y, "Freshest and stalest, by scheme. Dot area is the number of "
                      "establishments.", 12, INK2))
    for col_i, (group, title) in enumerate(((fhrs, "FHRS"), (fhis, "FHIS"))):
        cx = 56 + col_i * 450
        for j, (years, _s, name, count) in enumerate(group[:2] + group[-2:]):
            stale = j >= 2
            p.append(T(cx, y + 26 + j * 17, f"{years:4.1f}y", 11,
                       ACCENT if stale else HUE, weight="600"))
            p.append(T(cx + 46, y + 26 + j * 17,
                       f"{name[:30]}  ({count:,})", 11, INK2))
    save(p, "inspection-recency.svg", w, h)


def _n_for(p_hat, half_width, z=1.96):
    return math.ceil(z * z * p_hat * (1 - p_hat) / (half_width ** 2))


def chart_what_it_can_answer(auth, ratings):
    """The check that killed the sibling repo's ambitions, run here first."""
    national = collections.Counter()
    for c in ratings.values():
        national.update(c)
    bad = sum(national[k] for k in ("0", "1", "2")) + national.get("Improvement Required", 0)
    awaiting = national.get("AwaitingInspection", 0) + national.get("Awaiting Inspection", 0)

    QS = [("What share of 0\u20132 rated shops recover within a year?", bad, 0.01),
          ("The same, split by business type", bad // 8, 0.02),
          ("How long do new registrations wait for a first inspection?", awaiting, 0.01),
          ("Do chains recover faster than independents?", bad // 2, 0.02)]

    w, h = 940, 470
    p = head(w, h, "The cohort is big enough to answer the questions",
             "Each question against the number of establishments actually in that "
             "state today, and the precision that buys after one year of capture.",
             ["The sibling repository wss-sponsor-licences watches 68 entities, so "
              "every group comparison there needs ~163 per arm and is five years away.",
              "This is the same arithmetic run BEFORE building rather than after."])
    x0 = 620
    for i, (q, cohort, want) in enumerate(QS):
        y = 180 + i * 52
        need = _n_for(0.25, want)
        ok = cohort >= need
        p.append(T(56, y, q, 12.5, INK, weight="600"))
        p.append(T(56, y + 18, f"cohort today: {cohort:,}   \u00b1{want:.0%} needs {need:,}",
                   11, MUTED))
        p.append(R(x0, y - 12, 190, 17, GRID, rx=4))
        p.append(R(x0, y - 12, min(190.0, 190 * need / max(cohort, 1)), 17,
                   HUE if ok else ACCENT, rx=4))
        p.append(T(x0 + 200, y + 1, "reachable" if ok else "underpowered", 11.5,
                   INK if ok else ACCENT, weight="600"))
    y = 180 + len(QS) * 52 + 16
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "Every question above clears its own sample size on the first "
                      "capture. What they need is time, not a bigger register.",
               14, INK, weight="600"))
    p.append(T(56, y + 24,
               "Bars show the share of the cohort the question consumes \u2014 shorter "
               "is more headroom. The binding constraint here is the twelve months "
               "of capture, nothing else.", 12, INK2))
    save(p, "what-it-can-answer.svg", w, h)


def chart_boundary(_auth=None, _ratings=None):
    """Two dots on a rating scale, not one gap on an abstract axis.

    The first version of this chart plotted only the DIFFERENCE between two
    authorities, with the actual ratings sitting in text down the side doing no
    visual work. A reader had to hold three numbers -- two means and a gap --
    and the mark showed only the third. Nobody could read it, which is a fault
    of the chart.

    Now each row is the two councils' mean ratings as two dots on the 0-5 scale
    everyone already understands, joined by the distance between them. The gap
    is the line's length; the levels are where the dots sit.
    """
    import json
    path = REPO / "examples" / "border_pairs.json"
    if not path.is_file():
        return
    rows = json.loads(path.read_text())
    sig = [r for r in rows if abs(r["d"]) - 1.96 * r["se"] > 0]
    sig.sort(key=lambda r: -abs(r["d"]))
    shown = sig[:6]

    w = 940
    top, rowh = 210, 54
    h = top + len(shown) * rowh + 196
    x0, x1 = 300, w - 250
    lo_r, hi_r = 3.6, 5.0

    def X(v):
        return x0 + (v - lo_r) / (hi_r - lo_r) * (x1 - x0)

    p = head(w, h, "The same street, rated half a star apart",
             "Mean hygiene rating of shops within 150 m of a council boundary, "
             "compared with the shops just across it.",
             ["Two premises 150 m apart share a high street, a customer base and a "
              "building stock. What differs is which council inspects them.",
              "Only pairs whose 95% interval excludes zero are shown; 19 pairs "
              "qualified for the test and 5 cleared it."])

    for tick in (3.6, 4.0, 4.4, 4.8):
        p.append(L(X(tick), top - 20, X(tick), top + len(shown) * rowh - 22, GRID))
        p.append(T(X(tick), top + len(shown) * rowh - 4, f"{tick:.1f}", 10.5,
                   MUTED, anchor="middle"))
    p.append(T((x0 + x1) / 2, top + len(shown) * rowh + 16,
               "mean rating of the shops beside that boundary", 11, MUTED,
               anchor="middle"))

    for i, r in enumerate(shown):
        y = top + i * rowh
        low, high = (r["a"], r["b"]) if r["ma"] < r["mb"] else (r["b"], r["a"])
        lowm, highm = (r["ma"], r["mb"]) if r["ma"] < r["mb"] else (r["mb"], r["ma"])
        ln, hn = (r["na"], r["nb"]) if r["ma"] < r["mb"] else (r["nb"], r["na"])
        p.append(L(X(lowm), y, X(highm), y, BASELINE, 3))
        p.append(C(X(lowm), y, 7, ACCENT))
        p.append(C(X(highm), y, 7, HUE))
        p.append(T(X(lowm) - 14, y + 4, f"{low[:26]} {lowm:.2f}", 11.5, ACCENT,
                   anchor="end", weight="600"))
        p.append(T(X(highm) + 14, y + 4, f"{high[:26]} {highm:.2f}", 11.5, HUE,
                   weight="600"))
        p.append(T(X((lowm + highm) / 2), y - 13,
                   f"{abs(r['d']):.2f} stars apart", 10.5, INK2, anchor="middle"))
        p.append(T(x0 - 14, y + 20, f"n={ln} vs {hn}", 9.5, MUTED, anchor="end"))

    y = top + len(shown) * rowh + 52
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "THE DECISION: a 4 in one borough is not a 4 in the next, and "
                      "the FSA calls this a national scheme.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "This is the calibration check nobody publishes. It names which "
               "authority pairs to send a joint inspection exercise to, and the "
               "component scores say what to", 12, INK2))
    p.append(T(56, y + 42,
               "calibrate on. Every pair here is in London because 150 m only finds "
               "cross-boundary neighbours where shops are dense.", 12, INK2))
    p.append(T(56, y + 66,
               "NOT CONTROLLED FOR: business-type mix. Matching on BusinessType is "
               "the next refinement; until then these gaps are suggestive.", 12, MUTED))
    save(p, "boundary-discontinuity.svg", w, h)


def chart_rating_age(rated):
    """How old is the sticker in the window?

    The single most decision-shaped number in this archive, and it needs one
    capture. A rating is displayed with no date on it, so a customer reading a 5
    cannot tell whether it was earned last month or in 2019.
    """
    import datetime
    months = collections.Counter()
    for per_auth in rated.values():
        for month, n in per_auth.items():
            months[month] += n
    total = sum(months.values())
    if not total:
        return

    def age(month):
        y, m = map(int, month.split("-"))
        return (TODAY - datetime.date(y, m, 15)).days / 365

    order = ["under 1 year", "1-2 years", "2-3 years", "3-5 years", "over 5 years"]
    cols = [HUE, HUE_SOFT, DEAD, ACCENT, ACCENT]
    buckets = collections.Counter()
    for month, n in months.items():
        a = age(month)
        buckets[order[0] if a < 1 else order[1] if a < 2 else order[2] if a < 3
                else order[3] if a < 5 else order[4]] += n

    stale = buckets["3-5 years"] + buckets["over 5 years"]
    w, h = 940, 516
    p = head(w, h, f"One in six window stickers is three years old or more",
             f"Age of the rating currently displayed, across {total:,} rated "
             f"establishments. The sticker carries no date.",
             ["A 5 awarded last month and a 5 awarded in 2019 are the same green "
              "sticker in the window, and the customer cannot tell them apart.",
              "Computed from RatingDate, which every record carries — one capture, "
              "no waiting."])

    x0, bar_w = 300, 470
    for i, label in enumerate(order):
        y = 176 + i * 40
        n = buckets[label]
        p.append(T(x0 - 16, y + 13, label, 12.5, INK, anchor="end",
                   weight="600" if i >= 3 else "normal"))
        p.append(R(x0, y, bar_w * n / total, 17, cols[i], rx=4))
        p.append(T(x0 + bar_w * n / total + 10, y + 13,
                   f"{n:,}  \u00b7  {n/total:.1%}", 11.5, INK2))

    y = 176 + len(order) * 40 + 18
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, f"{stale:,} establishments ({stale/total:.1%}) display a rating "
                      f"awarded three or more years ago.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               f"{buckets['over 5 years']:,} of them ({buckets['over 5 years']/total:.1%}) "
               f"are showing one earned more than five years ago.", 12, INK2))
    p.append(T(56, y + 46,
               "THE DECISION: whether the displayed rating should carry its date. "
               "That is an FSA scheme choice, and this is the number it turns on.",
               12, INK, weight="600"))
    save(p, "rating-age.svg", w, h)



def main():
    auth, ratings, rated = load()
    if not auth:
        raise SystemExit("no observations — run `wss derive` first")
    print(f"loaded {len(auth)} authorities, "
          f"{sum(int(a.get('establishments_listed', 0)) for a in auth.values()):,} establishments")
    chart_nothing_is_kept(auth, ratings)
    chart_inspection_recency(auth, ratings)
    chart_what_it_can_answer(auth, ratings)
    chart_boundary()
    chart_rating_age(rated)


if __name__ == "__main__":
    main()
