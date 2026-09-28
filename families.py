#!/usr/bin/env python3
"""families.py -- what each imperative family CONTRIBUTES, not just how often it fires.

Fire 305. My own fire-304 handoff said: "`rival_named` is the fixable family. 2/5
precision, and its misses are all one shape." Two of five. The Wilson interval on
2/5 runs 12%-77%, which cannot distinguish the worst family in the set from the
best. The same handoff's DON'T section says "DON'T read two bins as a trend." I
wrote the caution and broke it on the next page, about my own number.

So before touching a regex: what does a family contribute ALONE? A tool matching
`rival_named` AND `routing` is carried by `routing` -- its precision is whatever
`routing`'s is. A family earns its place in the headline only through the tools
where it is the SOLE reason the tool counted. That is the marginal sample, it is
the one that can inflate the 9.6%, and it is a different population from a
random draw over all matches.

    python3 families.py [capture.json.gz] [--sample FAMILY] [--n 30] [--seed 305]

Imports RX/CAPS/FAM from imperatives.py on purpose -- never re-implement the
filter you are auditing (fire 304: my hand-check sample included a family the
published number excludes, because I copied the logic instead of calling it).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import os
import sys

from imperatives import FAM, RX, newest

HERE = os.path.dirname(os.path.abspath(__file__))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d * 100, (c + h) / d * 100)


def load(path: str):
    d = json.load(gzip.open(path, "rt"))
    rows = [r for r in d["rows"] if r.get("tools")]
    out = []
    for r in rows:
        for t in r["tools"]:
            text = t.get("desc") or ""
            fams = frozenset(k for k, rx in RX.items() if rx.search(text))
            out.append((r["host"], t.get("name", ""), text, fams))
    return out, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", nargs="?", default=None)
    ap.add_argument("--sample", default=None, help="print SOLE matches of this family")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=305)
    a = ap.parse_args()
    path = a.capture or newest()
    tools, n_srv = load(path)
    n = len(tools)
    hit = [t for t in tools if t[3]]
    print(f"# {os.path.basename(path)}  --  {n_srv:,} servers, {n:,} tools")
    print(f"  ANY family: {len(hit):,}  ({len(hit)/n*100:.2f}%)")

    print("\nFAMILY: fires / SOLE (only reason this tool counted) / marginal loss if removed")
    print(f"  {'family':<14} {'fires':>7} {'%tools':>7} {'SOLE':>7} {'%of fires':>10} {'ANY drops to':>13}")
    for k in FAM:
        fires = [t for t in hit if k in t[3]]
        sole = [t for t in fires if len(t[3]) == 1]
        without = len([t for t in hit if t[3] - {k}])
        print(f"  {k:<14} {len(fires):>7,} {len(fires)/n*100:>6.2f}% {len(sole):>7,} "
              f"{(len(sole)/max(1,len(fires))*100):>9.1f}% {without/n*100:>12.2f}%")

    print("\nCO-OCCURRENCE (rows = family, cols = share of its fires also matching col)")
    ks = list(FAM)
    print("  " + " " * 14 + "".join(f"{k[:7]:>9}" for k in ks))
    for k in ks:
        fires = [t for t in hit if k in t[3]]
        cells = "".join(
            f"{(sum(1 for t in fires if j in t[3]) / max(1,len(fires)) * 100):>8.0f}%" for j in ks)
        print(f"  {k:<14}{cells}")

    sizes = collections.Counter(len(t[3]) for t in hit)
    print("\n  families per matching tool: " + ", ".join(
        f"{i}:{sizes[i]:,}" for i in sorted(sizes)))

    if a.sample:
        import random
        fam = a.sample
        if fam not in FAM:
            sys.exit(f"unknown family {fam}")
        sole = [t for t in hit if t[3] == frozenset({fam})]
        print(f"\n### SOLE matches of {fam}: {len(sole):,} "
              f"({len(sole)/n*100:.2f}% of all tools). "
              f"Sampling {min(a.n,len(sole))} with seed {a.seed}.")
        rng = random.Random(a.seed)
        pick = sole[:]
        rng.shuffle(pick)
        for i, (host, name, text, _) in enumerate(pick[:a.n], 1):
            m = RX[fam].search(text)
            print(f"\n--- {i} :: {host} :: {name}   [match: {m.group(0)!r} @ {m.start()}/{len(text)}]")
            print("    " + " ".join(text.split())[:1400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
