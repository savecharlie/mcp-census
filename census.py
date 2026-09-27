#!/usr/bin/env python3
"""census.py -- read one MCP-registry snapshot and answer three questions.

Fire 303. These three, and no others, because each one can kill a product idea
on its own and I would rather be killed cheaply:

  1. HOW BIG is the registry, and how much of it is reachable-in-principle --
     a remote URL I can probe, versus a package I would have to install.
  2. HOW CONCENTRATED are the publishers. A registry that is 90% one vendor is
     one vendor's changelog, not a market.
  3. HOW OFTEN DOES A SERVER CHANGE after publication. This is the one that
     decides whether a *change monitor* has any reason to exist: if servers are
     write-once, nobody needs to be told they moved. Measured from each row's
     own `publishedAt` / `updatedAt` / version, which means I get churn out of a
     single snapshot instead of waiting a week for a second one.

WHAT THIS IS NOT. It does not probe anything. Every number here is the
registry's claim about itself, which is exactly the class of claim that was
wrong about my own server for forty-five days (`status: active`, unstartable).
Probing is a separate instrument and a separate honesty; do not let a count of
declarations be reported as a count of working software.

    python3 census.py [registry_YYYYMMDD.json.gz]
"""
from __future__ import annotations

import collections
import datetime
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def newest() -> str:
    c = sorted(glob.glob(os.path.join(HERE, "registry_2*.json.gz")))
    if not c:
        sys.exit("no snapshot; run pull_registry.py")
    return c[-1]


def load(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def parse(ts):
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else newest()
    rows = load(path)
    print(f"# {os.path.basename(path)}   {len(rows):,} rows")

    srv = [r.get("server") or {} for r in rows]
    meta = [(r.get("_meta") or {}).get(
        "io.modelcontextprotocol.registry/official") or {} for r in rows]

    names = [s.get("name", "") for s in srv]
    latest = [i for i, m in enumerate(meta) if m.get("isLatest")]
    print(f"  distinct names: {len(set(names)):,}   "
          f"rows flagged isLatest: {len(latest):,}")

    # ---- 1. shape ----------------------------------------------------------
    remote = sum(1 for s in srv if s.get("remotes"))
    pkg = sum(1 for s in srv if s.get("packages"))
    both = sum(1 for s in srv if s.get("remotes") and s.get("packages"))
    neither = sum(1 for s in srv if not s.get("remotes") and not s.get("packages"))
    print()
    print("SHAPE (of all rows)")
    print(f"  declares a remote URL:      {remote:,}  <- probeable without installing")
    print(f"  declares a package:         {pkg:,}")
    print(f"  both:                       {both:,}")
    print(f"  neither (nothing to run):   {neither:,}")
    reg = collections.Counter()
    for s in srv:
        for p in s.get("packages") or []:
            reg[p.get("registryType") or p.get("registry_name") or "?"] += 1
    print("  package registries: " + ", ".join(f"{k} {v:,}" for k, v in reg.most_common()))

    # ---- 2. concentration --------------------------------------------------
    # the name is a reverse-DNS namespace; the owner is everything before the '/'
    owner = collections.Counter(n.split("/")[0] for n in names if n)
    print()
    print(f"PUBLISHERS ({len(owner):,} distinct namespaces)")
    top = owner.most_common(10)
    for k, v in top:
        print(f"  {v:>6,}  {v/len(names)*100:5.1f}%  {k}")
    half = 0, 0.0
    run = 0
    for i, (_, v) in enumerate(owner.most_common(), 1):
        run += v
        if run >= len(names) / 2:
            print(f"  -> top {i} namespaces of {len(owner):,} hold half the listings.")
            break
    gh = sum(v for k, v in owner.items() if k.startswith("io.github."))
    print(f"  io.github.* (an individual's GitHub account): {gh:,}"
          f"  ({gh/len(names)*100:.1f}%)")

    # ---- 3. churn ----------------------------------------------------------
    now = datetime.datetime.now(datetime.timezone.utc)
    pub = [parse(m.get("publishedAt")) for m in meta]
    upd = [parse(m.get("updatedAt")) for m in meta]
    vers = collections.Counter(names)
    multi = sum(1 for n, c in vers.items() if c > 1)
    print()
    print("CHURN -- does a listing ever change after it is published?")
    print(f"  names with more than one version row: {multi:,} of {len(vers):,}"
          f"  ({multi/len(vers)*100:.1f}%)")
    moved = sum(1 for p, u in zip(pub, upd) if p and u and (u - p).total_seconds() > 60)
    print(f"  rows whose updatedAt is >60s after publishedAt: {moved:,}"
          f"  ({moved/len(rows)*100:.1f}%)")
    for d in (7, 30, 90):
        n = sum(1 for u in upd if u and (now - u).days <= d)
        p = sum(1 for x in pub if x and (now - x).days <= d)
        print(f"  touched in last {d:>2}d: {n:>6,}   first published in last {d:>2}d: {p:>6,}")
    st = collections.Counter(m.get("status", "?") for m in meta)
    print("  status field: " + ", ".join(f"{k} {v:,}" for k, v in st.most_common()))
    oldest = min((x for x in pub if x), default=None)
    print(f"  oldest publishedAt: {oldest.date() if oldest else '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
