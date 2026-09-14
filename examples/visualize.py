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
    """Same high street, different council.

    Computed by examples/boundary.py from the per-establishment geocodes, which
    live in object storage; the result is checked in as border_pairs.json so this
    chart is reproducible from the repo alone.

    THE DESIGN: two establishments within 150 m of each other, on opposite sides
    of a local authority line, face near-identical trade, footfall and premises
    stock and are inspected by different regulators. A discontinuity across that
    line is the council, not the food. It needs ONE capture, not a series.

    WHAT IT DOES NOT CONTROL FOR, said plainly: business-type mix. If one side of
    a boundary is takeaways and the other is supermarkets, that alone moves the
    mean. Matching on BusinessType is the next refinement and until it is done
    these gaps are suggestive, not attributable.
    """
    import json
    path = REPO / "examples" / "border_pairs.json"
    if not path.is_file():
        return
    rows = json.loads(path.read_text())
    sig = [r for r in rows if abs(r["d"]) - 1.96 * r["se"] > 0]
    sig.sort(key=lambda r: -abs(r["d"]))
    shown = sig[:8]
    w = 940
    top, rowh = 214, 46
    h = top + len(shown) * rowh + 190
    x0, x1 = 380, w - 150
    hi = max(abs(r["d"]) + 1.96 * r["se"] for r in shown) * 1.08

    p = head(w, h, "Same high street, different council, half a star apart",
             "Mean rating either side of a local authority boundary, using only "
             "establishments within 150 m of a shop in the other authority.",
             [f"{len(rows)} boundary pairs had at least 30 such establishments on "
              f"both sides; {len(sig)} have a 95% interval excluding zero.",
              "Two shops 150 m apart face the same trade and the same premises "
              "stock. What differs is who inspects them."])

    def X(v):
        return x0 + v / hi * (x1 - x0)

    for tick in (0, 0.2, 0.4, 0.6, 0.8):
        if tick > hi:
            continue
        p.append(L(X(tick), top - 18, X(tick), top + len(shown) * rowh - 18, GRID))
        p.append(T(X(tick), top + len(shown) * rowh - 2, f"{tick:.1f}", 10.5,
                   MUTED, anchor="middle"))
    p.append(T((x0 + x1) / 2, top + len(shown) * rowh + 18,
               "difference in mean rating (stars)", 11, MUTED, anchor="middle"))

    for i, r in enumerate(shown):
        y = top + i * rowh
        lo = max(abs(r["d"]) - 1.96 * r["se"], 0)
        h_ = abs(r["d"]) + 1.96 * r["se"]
        low, high = (r["a"], r["b"]) if r["ma"] < r["mb"] else (r["b"], r["a"])
        lowm, highm = (r["ma"], r["mb"]) if r["ma"] < r["mb"] else (r["mb"], r["ma"])
        ln, hn = (r["na"], r["nb"]) if r["ma"] < r["mb"] else (r["nb"], r["na"])
        p.append(T(x0 - 16, y - 4, f"{low[:22]}  {lowm:.2f}", 11.5, ACCENT,
                   anchor="end", weight="600"))
        p.append(T(x0 - 16, y + 11, f"{high[:22]}  {highm:.2f}", 11.5, HUE,
                   anchor="end"))
        p.append(T(x0 - 16, y + 25, f"n={ln} vs {hn}", 10, MUTED, anchor="end"))
        p.append(L(X(lo), y + 4, X(h_), y + 4, INK2, 2))
        for end in (lo, h_):
            p.append(L(X(end), y, X(end), y + 8, INK2, 2))
        p.append(R(X(abs(r["d"])) - 4.5, y - 0.5, 9, 9, INK, rx=2))
        p.append(T(X(h_) + 12, y + 8, f"{abs(r['d']):.2f}", 11.5, INK, weight="600"))

    y = top + len(shown) * rowh + 52
    p.append(L(56, y, w - 56, y, GRID)); y += 28
    p.append(T(56, y, "Every pair above is in London, and that is the method, not "
                      "a finding about London.", 14, INK, weight="600"))
    p.append(T(56, y + 24,
               "150 m only finds neighbours across a boundary where shops are "
               "dense, so the design currently reaches inner-city borders and "
               "almost nowhere else.", 12, INK2))
    p.append(T(56, y + 46,
               "NOT CONTROLLED FOR: business-type mix. If one side is takeaways "
               "and the other supermarkets, that alone moves the mean.", 12, INK2))
    p.append(T(56, y + 64,
               "Matching on BusinessType is the next refinement; until then these "
               "gaps are suggestive, not attributable. See D1.", 12, INK2))
    save(p, "boundary-discontinuity.svg", w, h)


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


if __name__ == "__main__":
    main()
