#!/usr/bin/env python3
"""convention.py -- does model-directed tool language spread like a CONVENTION?

Fire 304. Two papers read the same afternoon set this up.

arXiv:2609.09150 (Copying explains the collective behavior of AI agents in the
wild) follows thousands of one-hour, memoryless agents that found a public wiki and
used it to coordinate. The rule for all three decisions they had to make: **an agent
takes an option with probability close to that option's share of what it can SEE**,
weighted toward the page in front of it, then the recent stream, only weakly
anything older. Its closing line is the one that matters here: *whoever writes
first, or writes while the others are quiet, sets the convention for everyone who
comes later.*

arXiv:2609.26761 (A2M) says the field an MCP agent reads before choosing a tool is
its `description`, and that optimising it steers selection 93.6% of the time.

Put together, a prediction that is testable with the snapshot already on disk:
if "PREFER OVER WEB SEARCH", "call this first", "Use when the user asks" are a
CONVENTION being copied rather than independent good practice, then **servers
published more recently should use that language more**, because each new publisher
copies the share of it visible in what they looked at.

If the rate is flat in publication date, the convention story is not supported and
the language is just how people have always documented tools.

WHAT WILL BREAK THIS MEASUREMENT, and both are handled:
  * ONE PUBLISHER CAN BE THE WHOLE EFFECT. A host carrying 1,712 listings whose
    house style shouts would move a per-tool rate on its own. So the unit is the
    HOST, each counted once, and the per-tool numbers are printed beside it only
    for contrast.
  * The tool capture covers 187 hosts, so the bins are small. Every rate below
    carries a Wilson interval and no claim is made that the intervals do not
    support.

    python3 convention.py
"""
from __future__ import annotations

import collections
import datetime
import glob
import gzip
import json
import math
import os
import sys

import imperatives as I

HERE = os.path.dirname(os.path.abspath(__file__))


def newest(pat):
    c = [p for p in glob.glob(os.path.join(HERE, pat)) if "allver" not in p
         and "TRUNCATED" not in p]
    c.sort(key=os.path.getmtime)
    return c[-1]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z / (1 + z * z / n) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, c - h), min(1.0, c + h)


def main() -> int:
    reg = json.load(gzip.open(newest("registry_2*.json.gz"), "rt"))
    # earliest publication date seen for each remote HOST, and its namespace
    first = {}
    ns_of = {}
    for row in reg:
        srv = row.get("server") or {}
        meta = (row.get("_meta") or {}).get(
            "io.modelcontextprotocol.registry/official") or {}
        pub = meta.get("publishedAt")
        if not pub:
            continue
        d = pub[:10]
        for rem in srv.get("remotes") or []:
            u = rem.get("url") or ""
            if "://" not in u:
                continue
            h = u.split("://", 1)[1].split("/")[0].lower()
            if "{" in h:
                continue
            if h not in first or d < first[h]:
                first[h] = d
                ns_of[h] = (srv.get("name") or "").split("/")[0]

    tp = newest("tools_2*.json.gz")
    td = json.load(gzip.open(tp, "rt"))
    print(f"# {os.path.basename(tp)}  x  registry publication dates\n")

    per_host = []
    for r in td["rows"]:
        tools = r.get("tools") or []
        if not tools:
            continue
        h = r["host"]
        if h not in first:
            continue
        hits = 0
        for t in tools:
            desc = t.get("desc") or ""
            if any(rx.search(desc) for rx in I.RX.values()):
                hits += 1
        per_host.append({"host": h, "first": first[h], "ns": ns_of.get(h, ""),
                         "n_tools": len(tools), "hits": hits,
                         "any": hits > 0, "listings": r.get("listings", 0)})

    print(f"hosts with a tool list AND a publication date: {len(per_host)}")
    per_host.sort(key=lambda r: r["first"])
    print(f"publication dates span {per_host[0]['first']} .. {per_host[-1]['first']}\n")

    # split into quantile bins by first-publication date, so bins are equal-sized
    B = 4
    n = len(per_host)
    bins = [per_host[i * n // B:(i + 1) * n // B] for i in range(B)]
    print(f"{'bin':>3}  {'first published':>23}  {'hosts':>5}  "
          f"{'hosts w/ >=1':>12}  {'95% CI':>16}   {'tools':>6}  {'tool rate':>9}")
    for i, b in enumerate(bins, 1):
        k = sum(1 for r in b if r["any"])
        lo, hi = wilson(k, len(b))
        nt = sum(r["n_tools"] for r in b)
        nh = sum(r["hits"] for r in b)
        print(f"{i:>3}  {b[0]['first']} .. {b[-1]['first']}  {len(b):>5}  "
              f"{k:>4} = {k/len(b)*100:5.1f}%  [{lo*100:5.1f},{hi*100:5.1f}]   "
              f"{nt:>6}  {nh/nt*100:8.1f}%")

    # the confound, stated: is any single namespace carrying a bin?
    print("\nnamespace concentration per bin (a convention story dies if one "
          "publisher is the effect):")
    for i, b in enumerate(bins, 1):
        c = collections.Counter(r["ns"] for r in b if r["any"])
        top = ", ".join(f"{ns or '?'}x{k}" for ns, k in c.most_common(3))
        print(f"  bin {i}: {len(c)} distinct namespaces among the positives; top: {top}")

    # and the same question with no binning at all: a rank correlation
    xs = [datetime.date.fromisoformat(r["first"]).toordinal() for r in per_host]
    ys = [1.0 if r["any"] else 0.0 for r in per_host]
    def spearman(a, b):
        def rank(v):
            s = sorted(range(len(v)), key=lambda i: v[i])
            rk = [0.0] * len(v)
            i = 0
            while i < len(s):
                j = i
                while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                    j += 1
                avg = (i + j) / 2 + 1
                for t in range(i, j + 1):
                    rk[s[t]] = avg
                i = j + 1
            return rk
        ra, rb = rank(a), rank(b)
        ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
        num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
        den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
        return num / den if den else float("nan")
    rho = spearman(xs, ys)
    z = rho * math.sqrt(len(xs) - 1)
    print(f"\nSpearman rho(first-published, has >=1 model-directed tool) = {rho:+.3f}"
          f"   n={len(xs)}, z={z:+.2f}")
    print("  |z| < 1.96 means this snapshot does not support a trend either way.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
