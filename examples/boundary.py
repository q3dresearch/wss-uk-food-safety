#!/usr/bin/env python3
"""Cross-boundary rating comparison — writes examples/border_pairs.json.

    python examples/boundary.py

THE DESIGN. Two establishments within 150 m of each other on opposite sides of
a local authority line face near-identical trade, footfall and premises stock,
and are inspected by different regulators. A discontinuity across that line is
the council rather than the food. It needs ONE capture, not a series, which is
why D1 was mis-marked in the question table as needing twelve months.

WHY THIS IS A SEPARATE SCRIPT. It reads the PER-ESTABLISHMENT grain, which the
registry withholds to object storage, so it needs credentials that
visualize.py deliberately does not. Its output is checked in as
border_pairs.json so the chart stays reproducible from the repo alone.

An establishment's authority is recovered through the manifest: raw_ref names
the file it was parsed from, and that file's URL carries the authority code.
The parser does not put the authority on each establishment, and adding it
would cost 613,146 rows to repeat what the manifest already knows.
"""
from __future__ import annotations

import collections
import csv
import gzip
import io
import json
import math
import re
from pathlib import Path

from wss import capture, storage

REPO = Path(__file__).resolve().parents[1]
RADIUS_M = 150.0     # close enough to be the same parade of shops
CELL = 0.002         # ~222 m of latitude; neighbours are found in a 3x3 block
MIN_SIDE = 30        # below this a "mean rating" is not worth computing


def main() -> None:
    capture.load_env_file(REPO)
    ref_to_authority = {}
    for manifest in (REPO / "manifest").glob("*/*.csv"):
        for row in csv.DictReader(open(manifest)):
            code = re.search(r"FHRS(\d+)en-GB", row.get("url", ""))
            if code and row.get("raw_ref"):
                ref_to_authority[row["raw_ref"]] = code.group(1)

    source = type("S", (), {"storage": "object", "source_id": "fsa.fhrs.ratings"})()
    store = storage.store_for(source, REPO)
    names, points = {}, []
    for part in sorted((REPO / "derived" / "observations").glob("*.csv.gz")):
        for row in csv.DictReader(gzip.open(part, "rt")):
            eid = row["entity_id"]
            if eid.startswith("authority:") and row["metric"] == "name" \
                    and ":rating:" not in eid and ":type:" not in eid \
                    and ":rated:" not in eid:
                names[eid.split(":")[1]] = row["value"]

    latest = sorted((REPO / "derived" / "observations").glob("*.csv.gz"))[-1].name
    blob = store.read(f"derived/observations/{latest}")
    records: dict[str, dict] = collections.defaultdict(dict)
    with io.TextIOWrapper(gzip.open(io.BytesIO(blob), "rb"), encoding="utf-8",
                          newline="") as fh:
        for row in csv.DictReader(fh):
            eid = row["entity_id"]
            if eid.startswith("est:") and row["metric"] in (
                    "latitude", "longitude", "rating", "scheme"):
                rec = records[eid]
                rec[row["metric"]] = row["value"]
                rec["ref"] = row["raw_ref"]

    for rec in records.values():
        # FHIS has no numeric rating, so Scotland cannot join this comparison.
        if rec.get("scheme") != "FHRS" or not rec.get("rating", "").isdigit():
            continue
        if "latitude" not in rec:
            continue
        authority = ref_to_authority.get(rec.get("ref", ""))
        if authority:
            points.append((float(rec["latitude"]), float(rec["longitude"]),
                           int(rec["rating"]), authority))
    print(f"{len(points):,} FHRS establishments with rating, geocode and authority")

    grid = collections.defaultdict(list)
    for i, (lat, lon, _r, _a) in enumerate(points):
        grid[(int(lat / CELL), int(lon / CELL))].append(i)

    def metres(i: int, j: int) -> float:
        lat1, lon1 = points[i][0], points[i][1]
        lat2, lon2 = points[j][0], points[j][1]
        return math.hypot((lat1 - lat2) * 111320.0,
                          (lon1 - lon2) * 111320.0
                          * math.cos(math.radians((lat1 + lat2) / 2)))

    near_other = collections.defaultdict(set)
    for (gx, gy), cell in grid.items():
        block = [k for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 for k in grid.get((gx + dx, gy + dy), [])]
        for i in cell:
            for j in block:
                if j <= i or points[i][3] == points[j][3]:
                    continue
                if metres(i, j) <= RADIUS_M:
                    near_other[i].add(points[j][3])
                    near_other[j].add(points[i][3])
    print(f"{len(near_other):,} establishments within {RADIUS_M:.0f} m of another "
          f"authority's shop")

    sides = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, others in near_other.items():
        for other in others:
            sides[tuple(sorted((points[i][3], other)))][points[i][3]].append(points[i][2])

    out = []
    for pair, by_side in sides.items():
        if len(by_side) != 2:
            continue
        (a, ra), (b, rb) = by_side.items()
        if len(ra) < MIN_SIDE or len(rb) < MIN_SIDE:
            continue
        mean_a, mean_b = sum(ra) / len(ra), sum(rb) / len(rb)
        var_a = sum((x - mean_a) ** 2 for x in ra) / (len(ra) - 1)
        var_b = sum((x - mean_b) ** 2 for x in rb) / (len(rb) - 1)
        out.append({
            "a": names.get(a, a), "ma": mean_a, "na": len(ra),
            "b": names.get(b, b), "mb": mean_b, "nb": len(rb),
            "d": mean_a - mean_b,
            # Welch: the two sides have different n and different spread.
            "se": math.sqrt(var_a / len(ra) + var_b / len(rb)),
        })
    out.sort(key=lambda r: -abs(r["d"]))
    (REPO / "examples" / "border_pairs.json").write_text(json.dumps(out, indent=1))
    significant = [r for r in out if abs(r["d"]) - 1.96 * r["se"] > 0]
    print(f"{len(out)} pairs with >= {MIN_SIDE} on both sides; "
          f"{len(significant)} with a 95% interval excluding zero")
    print("NOTE: 19 tests, so expect ~1 false positive at 95%. "
          "Four of these survive a Bonferroni correction.")


if __name__ == "__main__":
    main()
