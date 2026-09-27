#!/usr/bin/env python3
"""baselines.py -- compare two tool captures, with intervals, and say which one
supersedes the other and why.

Fire 304. Fire 303 published two numbers from 187 tool-serving servers found by
probing 49 head hosts (>=10 listings) plus 300 uniformly sampled tail hosts. The
public repo's own NEXT list asked for the same thing sampled properly and far
wider, because a change-detection baseline can only be widened BEFORE the clock
matters. 1,600 more uniform tail hosts later: 1,036 servers, 12,829 tools.

THE MISTAKE THIS FILE EXISTS TO STOP ME REPEATING. The per-server rate fell from
48.7% to 39.9%, and my first sentence about it was "big multi-listing hosts do it
more, which is why the old mixed number sat high." **The head band was in the same
output, at 38.5%, saying the opposite.** I had written the explanation I expected
before reading the row that tested it. So this script always prints the bands
beside the totals, and always prints both intervals, because the honest answer here
is dull: the head and the tail differ by 1.4 points, which cannot explain 9, and
two Wilson intervals that overlap in a 1.4-point sliver are a small sample and a
large one disagreeing about as much as chance allows.

    python3 baselines.py OLD.json.gz NEW.json.gz [--probe PROBE_UNION.json.gz]
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import os
import sys

import imperatives as I


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, c - h), min(1.0, c + h)


def score(path: str, band_of=None):
    d = json.load(gzip.open(path, "rt"))
    g = collections.defaultdict(lambda: {"hosts": 0, "pos": 0, "tools": 0, "hits": 0})
    for r in d["rows"]:
        t = r.get("tools") or []
        if not t:
            continue
        hits = sum(1 for x in t
                   if any(rx.search(x.get("desc") or "") for rx in I.RX.values()))
        keys = ["ALL"]
        if band_of:
            keys.append(band_of.get(r["host"]) or "unknown")
        for k in keys:
            gg = g[k]
            gg["hosts"] += 1
            gg["pos"] += hits > 0
            gg["tools"] += len(t)
            gg["hits"] += hits
    return d, g


def line(label, gg):
    lo, hi = wilson(gg["pos"], gg["hosts"])
    tlo, thi = wilson(gg["hits"], gg["tools"])
    print(f"  {label:26} {gg['hosts']:>6} servers  {gg['pos']:>5} with >=1 = "
          f"{gg['pos']/gg['hosts']*100:5.1f}% [{lo*100:4.1f},{hi*100:4.1f}]   "
          f"{gg['tools']:>6} tools  {gg['hits']/gg['tools']*100:5.1f}% "
          f"[{tlo*100:4.1f},{thi*100:4.1f}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--probe", default=None, help="union probe, for the band labels")
    a = ap.parse_args()

    band = {}
    if a.probe:
        for r in json.load(gzip.open(a.probe, "rt"))["rows"]:
            band[r["host"]] = r.get("band")

    print("TOOLS WHOSE DESCRIPTION SPEAKS TO THE MODEL — two captures, same day\n")
    for tag, p in (("OLD", a.old), ("NEW", a.new)):
        d, g = score(p, band)
        print(f"{tag}  {os.path.basename(p)}"
              + (f"   (probe: {d.get('probe_source')})" if d.get("probe_source") else ""))
        line("all servers", g["ALL"])
        for b in ("head", "tail", "unknown"):
            if g[b]["hosts"]:
                line(f"  band: {b}", g[b])
        print()

    _, go = score(a.old, band)
    _, gn = score(a.new, band)
    olo, ohi = wilson(go["ALL"]["pos"], go["ALL"]["hosts"])
    nlo, nhi = wilson(gn["ALL"]["pos"], gn["ALL"]["hosts"])
    overlap = min(ohi, nhi) - max(olo, nlo)
    print("VERDICT")
    print(f"  per-server intervals overlap by {overlap*100:+.1f} points "
          f"({'they disagree' if overlap < 0 else 'they are compatible'}).")
    if gn["head"]["hosts"] and gn["tail"]["hosts"]:
        hh = gn["head"]["pos"] / gn["head"]["hosts"]
        tt = gn["tail"]["pos"] / gn["tail"]["hosts"]
        print(f"  head minus tail in the NEW capture: {(hh-tt)*100:+.1f} points. "
              f"Head-weighting {'could' if abs(hh-tt) > 0.05 else 'CANNOT'} account "
              f"for a shift of {(go['ALL']['pos']/go['ALL']['hosts'] - tt)*100:+.1f}.")
    print(f"  The NEW capture is {gn['ALL']['hosts']/go['ALL']['hosts']:.1f}x larger and its "
          f"tail is a uniform random draw from all 14,925 low-listing hosts,")
    print(f"  so it supersedes. Report the tail band as the estimate for 'a randomly "
          f"chosen registry host'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
