#!/usr/bin/env python3
"""merge_probes.py -- one probe row per HOST across several probe files.

Fire 304. The baseline for change-detection is only as good as the population it
covers, and a population can only be widened BEFORE the clock matters. Fire 303
started the clock on 187 tool-serving servers drawn from 49 head hosts plus 300
random tail hosts. This merges that run with a second, larger, uniform random draw
so the 7-day diff runs over as many servers as possible.

Rules, and they are the whole file:
  * one row per host. If two files probed the same host, keep the one whose
    RECOMPUTED verdict says more about it (verdict.py's ranking), and record that
    the host was seen twice with `n_files`.
  * never average, never overwrite. Both source files stay on disk; this writes a
    third.
  * record every input filename in the output. A merged artefact that cannot say
    what went into it is worse than two separate ones.

    python3 merge_probes.py probe_A.json.gz probe_B.json.gz -o probe_union.json.gz
"""
from __future__ import annotations

import argparse
import collections
import datetime
import gzip
import json
import os
import sys

import verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    best: dict[str, dict] = {}
    seen: collections.Counter = collections.Counter()
    meta = []
    for f in a.files:
        d = json.load(gzip.open(f, "rt"))
        meta.append({"file": os.path.basename(f), "rows": len(d["rows"]),
                     "when": d.get("when"), "seed": d.get("seed"),
                     "tail_sampled": d.get("tail_sampled"),
                     "head_min": d.get("head_min"),
                     "snapshot": d.get("snapshot")})
        for r in d["rows"]:
            h = r["host"]
            seen[h] += 1
            r = dict(r, verdict=verdict.row_verdict(r), source=os.path.basename(f))
            cur = best.get(h)
            if cur is None or verdict.rank(r["verdict"]) < verdict.rank(cur["verdict"]):
                best[h] = r
        print(f"  {os.path.basename(f)}: {len(d['rows']):,} rows", flush=True)

    for h, n in seen.items():
        best[h]["n_files"] = n

    rows = sorted(best.values(), key=lambda r: -r.get("listings", 0))
    tally = collections.Counter(r["verdict"] for r in rows)
    lt = collections.Counter()
    for r in rows:
        lt[r["verdict"]] += r.get("listings", 0)
    rated = [r for r in rows if r["verdict"] not in verdict.EXCLUDE_FROM_RATE]
    reach = [r for r in rated if r["verdict"] in verdict.REACHABLE]
    dup = sum(1 for n in seen.values() if n > 1)

    print(f"\nUNION  {len(rows):,} distinct hosts  ({dup:,} probed in more than one file)")
    for v, k in tally.most_common():
        print(f"  {v:9} {k:>6} hosts  {k/len(rows)*100:5.1f}%   {lt[v]:>7,} listings")
    print(f"\nreachable (live|auth|http-ok): {len(reach):,} of {len(rated):,} rated "
          f"= {len(reach)/len(rated)*100:.1f}%")
    print(f"live (completed an MCP handshake): {tally['live']:,} "
          f"= {tally['live']/len(rated)*100:.1f}% of rated hosts")

    with gzip.open(a.out, "wt") as f:
        json.dump({"when": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "merged_from": meta, "n_hosts": len(rows),
                   "note": "verdict recomputed by verdict.py; one row per host",
                   "rows": rows}, f)
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
