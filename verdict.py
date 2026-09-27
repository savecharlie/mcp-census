#!/usr/bin/env python3
"""verdict.py -- pick a HOST's verdict from its several probe attempts.

Fire 304, and it is a correction to fire 303, not a new idea.

303 added multi-path probing because `server.smithery.ai` -- 216 listings, the
third-biggest host in the registry -- 404s on whichever tenant path you happen to
pick. The mechanism worked: the second path returned **HTTP 401**, which is a
server saying "I am here, authenticate." Then the summary line threw that away:

    best = next((t for t in tries if t[0] == "live"), tries[-1])

Nothing was `live`, so it took the LAST attempt, which was another 404. The probe
therefore recorded `http-err` for a host it had just proved was answering, and the
CAIRN went on to claim 216 listings had been rescued. They had not been. **The fix
went in and the reporting step discarded its result.**

Measured over `probe_20260927.json.gz`: 2 hosts, 233 listings (1.0% of the
registry's remote listings), both multi-tenant gateways.

Ranking, most informative first. The principle: an attempt that proves the host
is SERVING outranks one that merely failed to find a path on it, whatever order
they arrived in.
"""
from __future__ import annotations

# low number = more informative about the HOST
RANK = {
    "live": 0,       # completed an MCP handshake
    "auth": 1,       # 401/403 -- serving, not enumerable by us
    "http-ok": 2,    # answered HTTP, wrong content type
    "template": 3,   # URL is a self-host placeholder; not addressable, not absent
    "http-err": 4,   # 404/5xx on every path tried
    "timeout": 5,
    "conn-err": 6,
    "dns": 7,        # name does not resolve -- the strongest evidence of absence
}

REACHABLE = ("live", "auth", "http-ok")   # the host is running something
EXCLUDE_FROM_RATE = ("template",)


def rank(v: str) -> int:
    return RANK.get(v, 99)


def best(attempt_verdicts) -> str:
    """The host's verdict, from every attempt made against it."""
    vs = [v for v in attempt_verdicts if v]
    if not vs:
        return "dns"
    return min(vs, key=rank)


def row_verdict(row: dict) -> str:
    """Recompute a stored probe row's verdict. Safe on old files: every attempt
    was kept, which is the only reason this correction costs nothing."""
    att = row.get("attempts") or []
    if att:
        return best(a.get("verdict") for a in att)
    return row.get("verdict", "dns")
