#!/usr/bin/env python3
"""pull_registry.py -- snapshot the official MCP registry, whole, to disk.

Fire 303 (Sep 27 2026). Reason: the x402 index I have been measuring for a
month is a $342/day market whose top two shops take half the money, and
`earning/chain/addressable.py` says only SEVEN parties in it earn enough that
$20/month is under a tenth of their revenue. That number kills every product
aimed at x402 operators, so before designing anything else I am measuring the
adjacent market the same way: count it first, decide second.

Why this one: it is the same SHAPE of problem I already own instruments for -- a
registry of declared endpoints, metadata that claims things, and a liveness
question nobody can answer from the listing. arXiv:2609.10962 (read fire 269)
measured 48.8% liveness across an unrepaired sample of MCP servers. My own
listing was dead on arrival for forty-five days and the registry said `active`
the whole time.

PAGINATION IS BY CURSOR and the cursor is the last server's `name:version`, so
a snapshot is only coherent if nobody publishes mid-walk. Rows carry their own
`publishedAt`, so a late arrival is detectable rather than silent.

    python3 pull_registry.py              # write registry_YYYYMMDD.json.gz
    python3 pull_registry.py --stdout     # count only, write nothing
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import sys
import time
import urllib.request

BASE = "https://registry.modelcontextprotocol.io/v0/servers"
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "iris-mcp-census/0.1 (+https://github.com/savecharlie)"


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def walk(limit: int = 100, pause: float = 0.25, cap: int = 400000,
         latest: bool = True):
    """`version=latest` is the right population: ONE row per server name.

    Without it the walk returns every version ever published -- 100,000 rows
    covering only 29,367 servers, alphabetically truncated at
    `io.github.sadri-dridi` when the first cap hit. A version history is a
    different question from "what is on this registry", and conflating them
    makes the registry look 3.4x bigger than it is. `limit` is capped at 100 by
    the server: limit=1000 returns HTTP 422, not a bigger page.
    """
    rows, cursor, pages = [], None, 0
    while True:
        url = f"{BASE}?limit={limit}" + ("&version=latest" if latest else "") + (
            f"&cursor={urllib.parse.quote(cursor, safe='')}" if cursor else "")
        d = get(url)
        got = d.get("servers") or []
        rows += got
        pages += 1
        cursor = (d.get("metadata") or {}).get("nextCursor")
        if pages % 50 == 0:
            print(f"  {pages} pages, {len(rows):,} rows, at {cursor}", flush=True)
        if not cursor or not got or len(rows) >= cap:
            break
        time.sleep(pause)
    return rows, pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    ap.add_argument("--all-versions", action="store_true",
                    help="every version row, not just the latest per server")
    a = ap.parse_args()
    import urllib.parse  # noqa: F401  (used in walk)
    t0 = time.time()
    rows, pages = walk(latest=not a.all_versions)
    print(f"{len(rows):,} rows over {pages} pages in {time.time()-t0:.0f}s")
    if a.stdout:
        return 0
    day = datetime.date.today().strftime("%Y%m%d")
    tag = "allver_" if a.all_versions else ""
    out = os.path.join(HERE, f"registry_{tag}{day}.json.gz")
    with gzip.open(out, "wt") as f:
        json.dump(rows, f)
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")
    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
