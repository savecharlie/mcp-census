#!/usr/bin/env python3
"""nouns.py -- the MCP registry counted under every noun, not one.

Fire 303. This is `earning/chain/reconcile.py`'s lesson carried into a second
registry: three agents published three counts of the x402 index within twelve
days -- 14,652, 28,650, 17,620 -- and the 2x spread was never the world, it was
the NOUN. Nobody had said whether they meant a listing, a route, a host or an
offer. The same trap is sitting unremarked in the MCP registry and it is worse
here, because two of the largest publishers are GATEWAYS.

Measured on the first snapshot (27 Sep 2026), in an alphabetical prefix of the
registry:

    io.github.pipeworx-io      4,986 listings   1,712 names   1 host
                               every one a path on gateway.pipeworx.io
    io.github.mcp-dir          1,117 listings   1,113 names   1 host
                               every one a path on api.mcp.ai
    io.github.brilliantdir..   1,177 listings       1 name    1 npm package
                               one package, published 1,177 times

So "the registry has N servers" can differ by an order of magnitude depending on
whether N counts rows, names, publishers, or things that can independently break.
Each rung below is a defensible answer to a DIFFERENT question, and the point of
printing them together is that nobody can quote one without seeing the others.

    INSTALL TARGET is the rung I care about most and the one nobody publishes: the
    host of a remote URL, or the package identifier. It answers "how many distinct
    pieces of software are actually here", which is the only rung that says
    anything about redundancy. If one gateway is 1,712 listings, a client that
    'supports 1,712 MCP servers' supports one HTTP host.

THE LADDER IS NOT A FUNNEL, and the first run proved it: install targets (37,523)
came out HIGHER than distinct server names (29,367), because one server may
declare several remote URLs and several packages, and each is a separate thing
that can break. So these are not nested subsets shrinking as you go down -- they
are answers on different axes, and calling them a funnel would be the same error
as calling them one number. Printed in the order a reader is likely to want them,
not in size order.

NO PROBING. Every number is the registry's own claim.

    python3 nouns.py [registry_YYYYMMDD.json.gz]
"""
from __future__ import annotations

import collections
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def newest(pat="registry_2*.json.gz") -> str:
    c = sorted(glob.glob(os.path.join(HERE, pat)))
    if not c:
        sys.exit("no snapshot; run pull_registry.py")
    return c[-1]


def host_of(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").split("/")[0].lower()


def scope_of(ident: str) -> str:
    """npm scope, or the bare package name when unscoped."""
    i = (ident or "").strip()
    return i.split("/")[0] if i.startswith("@") else i


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else newest()
    rows = json.load(gzip.open(path, "rt"))
    srv = [r.get("server") or {} for r in rows]
    print(f"# {os.path.basename(path)}")

    listings = len(rows)
    names = {s.get("name", "") for s in srv}
    spaces = {n.split("/")[0] for n in names if n}

    hosts, pkgs, scopes, targets = set(), set(), set(), set()
    per_host = collections.Counter()
    per_target = collections.Counter()
    for s in srv:
        t = set()
        for m in s.get("remotes") or []:
            h = host_of(m.get("url"))
            if h:
                hosts.add(h); t.add("host:" + h); per_host[h] += 1
        for p in s.get("packages") or []:
            ident = (p.get("identifier") or "").strip().lower()
            if ident:
                pkgs.add(ident); scopes.add(scope_of(ident)); t.add("pkg:" + ident)
        targets |= t
        for x in t:
            per_target[x] += 1

    ladder = [
        ("LISTING       rows the API returns", listings),
        ("SERVER NAME   distinct `name` values", len(names)),
        ("PUBLISHER     distinct namespaces (registry-verified owner)", len(spaces)),
        ("INSTALL TARGET remote host OR package identifier", len(targets)),
        ("  ...of which remote hosts", len(hosts)),
        ("  ...of which packages", len(pkgs)),
        ("  ...package owners (npm scope / bare name)", len(scopes)),
    ]
    w = max(len(k) for k, _ in ladder)
    print()
    for k, v in ladder:
        print(f"  {k:<{w}}  {v:>8,}")
    if names:
        print(f"\n  spread between the largest and smallest defensible count: "
              f"{listings / max(len(targets), 1):.1f}x")

    print("\nLARGEST INSTALL TARGETS -- one thing, many listings")
    print(f"  {'listings':>8}  target")
    for t, n in per_target.most_common(12):
        print(f"  {n:>8,}  {t}")
    conc = sum(n for _, n in per_target.most_common(10))
    print(f"  top 10 targets carry {conc:,} of {listings:,} listings "
          f"({conc/listings*100:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
