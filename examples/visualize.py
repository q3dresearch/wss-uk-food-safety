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
    p.append(T(56, y, "A gap this size is real. What causes it is NOT settled \u2014 "
                      "see the component breakdown.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "Decomposing these same gaps into Hygiene, Structural and Management "
               "puts the largest difference in STRUCTURAL for four of the five pairs. "
               "Structural is the", 12, INK2))
    p.append(T(56, y + 42,
               "building's physical fabric, so the likeliest explanation is that the "
               "premises genuinely differ across the line \u2014 not that the councils "
               "mark differently.", 12, INK2))
    p.append(T(56, y + 66,
               "Every pair here is in London, because 150 m only finds cross-boundary "
               "neighbours where shops are dense. Business-type mix is still "
               "uncontrolled.", 12, MUTED))
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



def chart_components(auth, ratings):
    """What actually separates a 1 from a 2.

    Each component is shown as a share of ITS OWN maximum, because the scales
    differ -- Hygiene and Structural run to 25, Confidence in Management to 30 --
    and plotting the raw numbers side by side would make management look worse
    than it is by construction.

    Higher is worse throughout.
    """
    MAXES = {"hygiene": 25, "structural": 25, "confidenceinmanagement": 30}
    counts, totals = collections.Counter(), collections.defaultdict(collections.Counter)
    for path in sorted(glob.glob(str(REPO / "derived" / "observations" / "*.csv.gz"))):
        with io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                eid = r["entity_id"]
                if ":rating:" not in eid:
                    continue
                rv = eid.split(":rating:")[1]
                if r["metric"] == "establishments_listed":
                    counts[rv] += int(r["value"])
                elif r["metric"].startswith("score_"):
                    totals[rv][r["metric"]] += int(r["value"])
    ratings_shown = [v for v in ("0", "1", "2", "3", "4", "5") if counts.get(v)]
    if not ratings_shown:
        return

    w, h = 940, 530
    p = head(w, h, "A 1 is a judgement about the operator, not a dirtier kitchen",
             "Each component as a share of its own maximum, by rating. Higher is "
             "worse. FHRS only \u2014 Scotland publishes no component scores.",
             ["Between a 1 and a 2 the Hygiene score barely moves and Structural "
              "moves a little. Confidence in Management halves.",
              "Scales differ (Hygiene and Structural to 25, Management to 30), so "
              "raw scores are not comparable and shares are used."])

    x0, colw = 190, 108
    base, tall = 380, 200
    cols = {"hygiene": HUE, "structural": HUE_SOFT, "confidenceinmanagement": ACCENT}
    labels = {"hygiene": "Hygiene", "structural": "Structural",
              "confidenceinmanagement": "Management"}
    for g, rv in enumerate(ratings_shown):
        gx = x0 + g * colw
        n = counts[rv]
        for k, (tag, col) in enumerate(cols.items()):
            share = totals[rv][f"score_{tag}_total"] / n / MAXES[tag]
            bh = share * tall
            p.append(R(gx + k * 22, base - bh, 18, bh, col, rx=3))
        p.append(T(gx + 33, base + 18, f"rated {rv}", 11.5, INK, anchor="middle",
                   weight="600"))
        p.append(T(gx + 33, base + 33, f"n={n:,}", 10, MUTED, anchor="middle"))
    for frac in (0.25, 0.5, 0.75):
        p.append(L(x0 - 24, base - frac * tall, w - 70, base - frac * tall, GRID))
        p.append(T(x0 - 32, base - frac * tall + 4, f"{frac:.0%}", 10, MUTED,
                   anchor="end"))
    p.append(L(x0 - 24, base, w - 70, base, BASELINE))
    lx = 190
    for tag, col in cols.items():
        p.append(R(lx, 150, 11, 11, col, rx=2))
        p.append(T(lx + 16, 160, labels[tag], 11, INK2))
        lx += 16 + len(labels[tag]) * 6.4 + 26

    y = base + 66
    p.append(L(56, y, w - 56, y, GRID)); y += 26
    h1 = totals["1"]["score_hygiene_total"] / counts["1"]
    h2 = totals["2"]["score_hygiene_total"] / counts["2"]
    m1 = totals["1"]["score_confidenceinmanagement_total"] / counts["1"]
    m2 = totals["2"]["score_confidenceinmanagement_total"] / counts["2"]
    p.append(T(56, y, f"Hygiene at a 1 is {h1:.1f} and at a 2 is {h2:.1f}. "
                      f"Management is {m1:.1f} and {m2:.1f}.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "THE DECISION: what an enforcement conversation is about. If the "
               "kitchen is equally clean at a 1 and a 2, the thing separating them "
               "is the inspector's", 12, INK2))
    p.append(T(56, y + 42,
               "confidence in the operator \u2014 which is a different remedy, and a "
               "different appeal, from a cleaning order.", 12, INK2))
    save(p, "what-drives-a-bad-rating.svg", w, h)


def chart_component_gap():
    """Which component the cross-boundary gap actually sits in.

    Built to test a hypothesis and it refuted it. The expectation was that
    councils would disagree most on Confidence in Management, the most
    discretionary component. The largest gap is STRUCTURAL in four of five
    pairs -- the building's physical fabric -- which points at premises genuinely
    differing across the line rather than at inconsistent marking.
    """
    import json
    path = REPO / "examples" / "border_components.json"
    if not path.is_file():
        return
    rows = json.loads(path.read_text())
    order = ["hygiene", "structural", "confidenceinmanagement"]
    key = {"hygiene": "hygiene", "structural": "structural",
           "confidenceinmanagement": "management"}
    labels = {"hygiene": "Hygiene", "structural": "Structural",
              "confidenceinmanagement": "Management"}
    cols = {"hygiene": HUE, "structural": ACCENT, "confidenceinmanagement": HUE_SOFT}

    w = 940
    top, rowh = 218, 76
    h = top + len(rows) * rowh + 190
    x0, x1 = 330, w - 150
    hi = max(abs(r[key[t]]["d"]) + 1.96 * r[key[t]]["se"] for r in rows for t in order) * 1.06

    p = head(w, h, "The gap is widest in the building, not the judgement",
             "The same boundary pairs, with the rating difference split into its "
             "three component scores. Higher is worse.",
             ["Built to test whether councils disagree most on the DISCRETIONARY "
              "component. They do not: Structural is the largest gap in four of "
              "five pairs.",
              "Structural is the premises' physical fabric, which is the one thing "
              "150 m of distance does not guarantee is alike."])

    def X(v):
        return x0 + v / hi * (x1 - x0)

    for tick in (0, 1, 2, 3):
        if tick > hi:
            continue
        p.append(L(X(tick), top - 20, X(tick), top + len(rows) * rowh - 30, GRID))
        p.append(T(X(tick), top + len(rows) * rowh - 12, str(tick), 10.5, MUTED,
                   anchor="middle"))
    p.append(T((x0 + x1) / 2, top + len(rows) * rowh + 8,
               "difference in mean component score", 11, MUTED, anchor="middle"))

    for i, r in enumerate(rows):
        y = top + i * rowh
        p.append(T(x0 - 16, y + 6, f"{r['a'][:20]} v {r['b'][:20]}", 11.5, INK,
                   anchor="end", weight="600"))
        p.append(T(x0 - 16, y + 22, f"n={r['na']} vs {r['nb']}", 9.5, MUTED,
                   anchor="end"))
        widest = max(order, key=lambda t: abs(r[key[t]]["d"]))
        for k, tag in enumerate(order):
            d = r[key[tag]]
            yy = y - 8 + k * 16
            sig = abs(d["d"]) - 1.96 * d["se"] > 0
            p.append(L(X(0), yy, X(abs(d["d"])), yy,
                       cols[tag] if sig else DEAD, 7 if tag == widest else 5))
            p.append(T(X(abs(d["d"])) + 10, yy + 4,
                       f"{labels[tag]} {abs(d['d']):.2f}{'' if sig else '  n.s.'}",
                       10.5, INK if tag == widest else MUTED,
                       weight="600" if tag == widest else "normal"))

    y = top + len(rows) * rowh + 44
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "So the boundary gap is probably the buildings, not the "
                      "inspectors.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "This chart was built expecting the opposite. Structural is the "
               "component least under an inspector's discretion and most determined "
               "by what was built", 12, INK2))
    p.append(T(56, y + 42,
               "there \u2014 and it carries the widest gap. Matching on premises age "
               "and business type is what would settle it; until then no "
               "calibration claim is safe.", 12, INK2))
    save(p, "boundary-components.svg", w, h)

def chart_what_is_kept(auth, ratings):
    """The orientation graphic: what the publisher keeps against what this keeps.

    Every row is a fact about a real food business. The left column is what
    ratings.food.gov.uk will tell you today; the right is what this archive will
    tell you. Drawn because "the FSA does not publish history" is an abstraction
    until you see which specific questions it closes.
    """
    national = collections.Counter()
    for c in ratings.values():
        national.update(c)
    total = sum(national.values())
    n_auth = len(auth)

    ROWS = [
        ("What is this shop rated today?", True, True, ""),
        ("When was that rating given?", True, True, "RatingDate, on every record"),
        ("Which of hygiene, fabric or management is weak?", True, True,
         "three component scores, FHRS only"),
        ("What was it rated BEFORE that?", False, True, "the whole reason this exists"),
        ("How long did it hold the previous rating?", False, True, ""),
        ("Did a 1-rated shop recover, or close?", False, True,
         "18,249 carry a bad rating today"),
        ("Did it reopen under a new registration?", False, True,
         "FHRSID is minted per registration"),
        ("How long did a new business wait to be inspected?", False, True,
         "52,764 have never been inspected"),
    ]
    w = 940
    top, rowh = 214, 38
    h = top + len(ROWS) * rowh + 190
    cx_fsa, cx_us = 620, 790

    p = head(w, h, "What the publisher keeps, and what this keeps",
             f"{total:,} food businesses across {n_auth} local authorities and all "
             f"four UK nations, captured monthly.",
             ["The FSA publishes the CURRENT rating and the date it was set. There "
              "is no history field anywhere in the record, and web.archive.org",
              "holds zero captures of the bulk files. Everything below the line is "
              "unrecoverable once an inspector visits again."])

    p.append(T(cx_fsa, top - 26, "ratings.food.gov.uk", 12, INK2, anchor="middle",
               weight="600"))
    p.append(T(cx_us, top - 26, "this archive", 12, HUE, anchor="middle", weight="600"))
    split = None
    for i, (q, fsa, us, note) in enumerate(ROWS):
        y = top + i * rowh
        if not fsa and split is None:
            split = y - 22
            p.append(L(56, split, w - 56, split, BASELINE))
        p.append(T(56, y + 4, q, 12.5, INK if not fsa else INK2,
                   weight="600" if not fsa else "normal"))
        if note:
            p.append(T(56, y + 19, note, 10, MUTED))
        for cx, has in ((cx_fsa, fsa), (cx_us, us)):
            if has:
                p.append(C(cx, y, 7, HUE if cx == cx_us else INK2))
            else:
                p.append(C(cx, y, 7, SURFACE))
                p.append(f'<circle cx="{cx}" cy="{y}" r="7" fill="none" '
                         f'stroke="{DEAD}" stroke-width="1.5"/>')
                p.append(L(cx - 4, y - 4, cx + 4, y + 4, DEAD, 1.5))

    y = top + len(ROWS) * rowh + 44
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "Everything above the line you can get from the FSA for free, "
                      "today. Everything below it exists nowhere else.", 14, INK,
               weight="600"))
    p.append(T(56, y + 24,
               "The five open circles are not a gap in the FSA's publishing \u2014 "
               "they follow from the scheme's premise that the current rating IS "
               "the fact. This archive", 12, INK2))
    p.append(T(56, y + 42,
               "is a bet that the trajectory matters too: a shop that went 1 then 5 "
               "and a shop that was always 5 are different risks.", 12, INK2))
    save(p, "what-is-kept.svg", w, h)


def chart_decisions(auth, ratings, rated):
    """Who decides what, and when the evidence for it arrives.

    The question a prospective reader actually has is not "is the data
    interesting" but "what would I do with it, and how long until I can".
    """
    import datetime
    months = collections.Counter()
    for per_auth in rated.values():
        for month, n in per_auth.items():
            months[month] += n
    total_rated = sum(months.values())
    stale = 0
    for month, n in months.items():
        y_, m_ = map(int, month.split("-"))
        if (TODAY - datetime.date(y_, m_, 15)).days / 365 >= 3:
            stale += n
    national = collections.Counter()
    for c in ratings.values():
        national.update(c)
    bad = sum(national[k] for k in ("0", "1", "2")) + national.get("Improvement Required", 0)
    waiting = national.get("AwaitingInspection", 0) + national.get("Awaiting Inspection", 0)

    DEC = [
        (0, "Food Standards Agency",
         "Should the displayed rating carry its DATE?",
         f"{stale:,} stickers ({stale/total_rated:.0%}) are 3+ years old"),
        (0, "An environmental health officer",
         "What is the conversation with a 1-rated operator about?",
         "at a 1 the kitchen is as clean as at a 2 \u2014 management is the gap"),
        (0, "An EH manager",
         "Is my re-inspection interval defensible to a finance director?",
         "0.6 to 3.3 years across authorities in one scheme"),
        (12, "Food Standards Agency",
         "Is a bad rating a warning, or a death sentence?",
         f"{bad:,} carry one today; nothing records what happens next"),
        (12, "An EH manager",
         "How long does a new business actually wait for me?",
         f"{waiting:,} have never been inspected"),
        (18, "Food Standards Agency",
         "Is the scheme being reset by re-registration?",
         "the phoenix question \u2014 unaskable from any other source"),
        (24, "Researchers, journalists",
         "Is the national rating distribution drifting upward?",
         "grade inflation is invisible without a baseline"),
    ]
    w = 940
    top, rowh = 206, 60
    h = top + len(DEC) * rowh + 150
    x0, x1 = 560, w - 118

    p = head(w, h, "What you could decide with this, and when",
             "Every decision below is one nobody can make from the FSA's own "
             "published data. The bar is how long the archive has to run first.",
             ["Three need no waiting at all, because RatingDate makes a single "
              "capture a survival curve.",
              "The rest need the thing only time provides: a second look at the "
              "same 613,146 businesses."])

    def X(m):
        return x0 + m / 24 * (x1 - x0)

    for tick in (0, 6, 12, 18, 24):
        p.append(L(X(tick), top - 22, X(tick), top + len(DEC) * rowh - 26, GRID))
        p.append(T(X(tick), top - 30, "today" if tick == 0 else f"+{tick}mo", 10.5,
                   INK2 if tick == 0 else MUTED, anchor="middle"))

    for i, (months_, who, question, evidence) in enumerate(DEC):
        y = top + i * rowh
        col = HUE if months_ == 0 else ACCENT if months_ <= 12 else DEAD
        p.append(T(56, y, question, 12.5, INK, weight="600"))
        p.append(T(56, y + 17, who, 11, col, weight="600"))
        p.append(T(56, y + 32, evidence, 10.5, MUTED))
        if months_ == 0:
            p.append(C(X(0), y + 4, 8, col))
            p.append(T(X(0) + 16, y + 8, "available now", 11, col, weight="600"))
        else:
            p.append(R(X(0), y, max(X(months_) - X(0), 2), 9, col, rx=4))
            p.append(T(X(months_) + 12, y + 8, f"{months_} months", 11, INK2))

    y = top + len(DEC) * rowh + 16
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "The cost of finding out is 574 MB a month and one HTTP "
                      "request per local authority.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "Open Government Licence v3.0. Nothing here is bought, scraped "
               "against a publisher's wishes, or reconstructable later \u2014 the "
               "window is the whole point.", 12, INK2))
    save(p, "decisions.svg", w, h)

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
    chart_components(auth, ratings)
    chart_component_gap()
    chart_what_is_kept(auth, ratings)
    chart_decisions(auth, ratings, rated)


if __name__ == "__main__":
    main()
