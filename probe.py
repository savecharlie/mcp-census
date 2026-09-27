#!/usr/bin/env python3
"""probe.py -- is a declared MCP endpoint actually there, asked the way it declared.

Fire 303. This is fire 302's lesson carried across: my x402 prober said GET to
every route for four weeks while half the index declares POST, counted 259
replies of "405 Method Not Allowed" every night, and published the resulting
emptiness as market news. A 405 is not a corpse, it is a correction. So this
prober reads `remotes[].type` off each listing and speaks the transport the
listing itself declares -- `streamable-http` gets a POST `initialize`,
`sse` gets a GET with an event-stream Accept -- and it RECORDS which it used in
every row, so a future me can tell whether a dead reading is the world or the
verb.

SAMPLING, and why it is not a full sweep. 22,421 listings declare a remote URL
but they live on only 14,974 hosts, and the top three hosts carry 5,192 listings
between them. Hammering 15k strangers' servers nightly to learn something that
a few hundred requests can establish is rude and it is also worse measurement,
because the tail is where the timeouts are. So:

    WEIGHTED HEAD   every host carrying >= `--head-min` listings. Small in count,
                    large in listings covered, and the number everyone actually
                    wants ("how much of the registry is reachable") is dominated
                    by it.
    RANDOM TAIL     a uniform random sample of the remaining hosts, seeded so the
                    draw is reproducible, which lets the tail rate be estimated
                    with a stated interval instead of asserted.

ONE REQUEST PER HOST, not per listing. A host answering for 1,712 listings is one
piece of software and one outage; probing all 1,712 would report one fact 1,712
times and call it a sample.

WHAT A VERDICT MEANS, exactly, because this is where a prober lies:
    live      spoke MCP: a JSON-RPC result with a protocolVersion came back.
    http-ok   HTTP 2xx but not an MCP handshake -- a web page, a health check, a
              gateway that wants a session first. NOT live, NOT dead.
    auth      401/402/403 -- present and refusing me, which is a working server.
    http-err  4xx/5xx other than auth.
    dns       the name does not resolve. For an ephemeral tunnel hostname
              (`*.trycloudflare.com`) this is the expected end state, not a fault.
    timeout   no answer inside --timeout.

    python3 probe.py                 # head + 300-host tail, writes probe_<date>.json.gz
    python3 probe.py --head-min 20 --tail 150
    python3 probe.py --only api.mcp.ai   # re-check one host, several times
"""
from __future__ import annotations

import argparse
import collections
import datetime
import glob
import gzip
import json
import os
import random
import re
import socket
import ssl
import sys
import time

import verdict
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "iris-mcp-census/0.1 (+https://github.com/savecharlie; one probe per host)"
INIT = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "iris-mcp-census", "version": "0.1"}},
}


def host_of(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").split("/")[0].lower()


def newest(pat="registry_2*.json.gz") -> str:
    c = sorted(p for p in glob.glob(os.path.join(HERE, pat)) if "allver" not in p)
    if not c:
        sys.exit("no snapshot; run pull_registry.py")
    return c[-1]


def targets(path):
    """host -> (listing count, UP TO THREE representative (url, type, name)).

    ONE REPRESENTATIVE PER HOST MISREPRESENTS A GATEWAY. `server.smithery.ai`
    carries 216 listings and the URL I happened to pick,
    `/@222wcnm/bilistalkermcp/mcp`, returns 404 three times running -- so the
    first sweep wrote 216 listings off on the strength of one tenant's dead
    path. A host is up if ANY of its paths answers, so try a few and keep the
    best. Still bounded and still polite: three requests for a host carrying
    hundreds of listings, one for everybody else.
    """
    rows = json.load(gzip.open(path, "rt"))
    n = collections.Counter()
    reps = {}
    for r in rows:
        s = r.get("server") or {}
        for m in s.get("remotes") or []:
            u = m.get("url")
            h = host_of(u)
            if not h:
                continue
            n[h] += 1
            reps.setdefault(h, [])
            if len(reps[h]) < 3 and u not in [x[0] for x in reps[h]]:
                reps[h].append((u, (m.get("type") or "streamable-http").lower(),
                                s.get("name", "")))
    return n, reps


def read_bounded(r, cap: int, deadline: float) -> str:
    """Read at most `cap` bytes and never sit past `deadline`.

    WHY THIS IS NOT `r.read(cap)`. The first version used it and the sweep HUNG
    FOREVER: two threads sat in do_poll with the connection ESTABLISHED while the
    other six workers idled on an empty queue, so `ThreadPoolExecutor.map`'s
    in-order iteration printed nothing for twenty-four minutes and the run looked
    stalled rather than broken. A socket timeout applies to ONE read syscall;
    `read(4096)` loops internally until it has 4096 bytes or EOF, so a server
    holding an event stream open and trickling a heartbeat resets the clock
    forever and never errors. Diagnosed from /proc/<pid>/task/*/wchan, which is
    the cheapest thing I own and the reason I did not wait it out.
    """
    buf = b""
    while len(buf) < cap and time.time() < deadline:
        try:
            chunk = r.read(min(512, cap - len(buf)))
        except Exception:
            break
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", "replace")


TEMPLATE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def probe(url: str, kind: str, timeout: float):
    """Speak the declared transport. Returns (verdict, http, detail, elapsed_ms)."""
    t0 = time.time()
    # A URL LIKE `https://{host}/api/v1/mcp/` IS NOT BROKEN, IT IS A TEMPLATE.
    # The registry allows variable substitution so a self-hosted server can be
    # listed once and pointed at the operator's own machine. The first sweep
    # called 22 of these `dns` and put them in the unreachable column, which is
    # a census reporting its own inability to address something as the thing
    # being absent. They get their own verdict and are excluded from
    # reachability rates entirely.
    if TEMPLATE.search(url or ""):
        return "template", 0, "self-host template", 0
    try:
        if kind == "sse":
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "text/event-stream"})
            # An SSE endpoint is SUPPOSED to hold the connection open, so its
            # body is never a thing to wait for. 200 + the right content-type IS
            # the verdict; reading it was the hang.
            with urllib.request.urlopen(req, timeout=timeout) as r:
                ms = int((time.time() - t0) * 1000)
                ct = (r.headers.get("Content-Type") or "").lower()
                if "text/event-stream" in ct:
                    return "live", r.status, "sse-stream", ms
                return "http-ok", r.status, ct[:40], ms
        else:
            req = urllib.request.Request(
                url, data=json.dumps(INIT).encode(), headers={
                    "User-Agent": UA, "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = read_bounded(r, 4096, t0 + timeout)
            ms = int((time.time() - t0) * 1000)
            if "protocolVersion" in body and "jsonrpc" in body:
                ver = re.search(r'"protocolVersion":"([^"]+)"', body)
                return "live", r.status, (ver.group(1) if ver else ""), ms
            return "http-ok", r.status, body[:60].replace("\n", " "), ms
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        v = "auth" if e.code in (401, 402, 403) else "http-err"
        return v, e.code, "", ms
    except socket.gaierror:
        return "dns", 0, "", int((time.time() - t0) * 1000)
    except (socket.timeout, TimeoutError):
        return "timeout", 0, "", int((time.time() - t0) * 1000)
    except (urllib.error.URLError, ssl.SSLError, ConnectionError, OSError) as e:
        ms = int((time.time() - t0) * 1000)
        r = str(getattr(e, "reason", e))
        if "Name or service not known" in r or "nodename nor servname" in r:
            return "dns", 0, "", ms
        if "timed out" in r:
            return "timeout", 0, "", ms
        return "conn-err", 0, r[:50], ms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--head-min", type=int, default=10,
                    help="probe every host carrying at least this many listings")
    ap.add_argument("--tail", type=int, default=300,
                    help="uniform random sample size from the remaining hosts")
    ap.add_argument("--seed", type=int, default=303)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only", default=None, help="one host, probed --repeat times")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--confirm", type=int, default=2,
                    help="re-probe any non-live host this many times, spaced")
    ap.add_argument("--confirm-gap", type=float, default=20.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    path = a.snapshot or newest()
    n, reps = targets(path)
    print(f"# {os.path.basename(path)}: {sum(n.values()):,} remote listings "
          f"on {len(n):,} hosts", flush=True)

    if a.only:
        u, k, nm = reps[a.only][0]
        for i in range(a.repeat):
            v, code, det, ms = probe(u, k, a.timeout)
            print(f"  {i+1}/{a.repeat}  {v:9} http={code:<4} {ms:>6}ms  {det[:60]}")
            if i + 1 < a.repeat:
                time.sleep(5)
        return 0

    head = sorted([h for h, c in n.items() if c >= a.head_min], key=lambda h: -n[h])
    tail_pool = [h for h in n if n[h] < a.head_min]
    random.Random(a.seed).shuffle(tail_pool)
    tail = tail_pool[:a.tail]
    print(f"  head: {len(head):,} hosts >= {a.head_min} listings "
          f"({sum(n[h] for h in head):,} listings, "
          f"{sum(n[h] for h in head)/sum(n.values())*100:.1f}% of them)")
    print(f"  tail: {len(tail):,} of {len(tail_pool):,} hosts sampled "
          f"(seed {a.seed})", flush=True)

    def one(h, band):
        """A SINGLE PROBE IS NOT A VERDICT. Measured, fire 303: api.mcp.ai --
        1,115 listings, 3% of the registry -- answered 502 once and then 200
        three times running on the identical URL. I was one paragraph from
        publishing "3% of the registry is behind a host that is down". So any
        non-live first reading is re-probed `--confirm` more times, spaced, and
        the row keeps EVERY attempt. A host is only called down when no attempt
        reached it. This is the mechanism version of SUSPECT THE RULER; a note
        to myself would not have survived the next fire.
        """
        cand = reps[h]
        u, k, nm = cand[0]
        tries, used = [probe(u, k, a.timeout)], [u]
        if tries[0][0] != "live":
            # other paths on the same host first (a gateway tenant can 404 while
            # the gateway is fine), then the same path again after a pause
            for u2, k2, _ in cand[1:]:
                tries.append(probe(u2, k2, a.timeout)); used.append(u2)
                if tries[-1][0] == "live":
                    break
            for _ in range(a.confirm if tries[-1][0] != "live" else 0):
                time.sleep(a.confirm_gap)
                tries.append(probe(u, k, a.timeout)); used.append(u)
                if tries[-1][0] == "live":
                    break
        # FIRE 304: this used to be `next(live) or tries[-1]`, which threw away a
        # 401 -- a host SAYING it is there -- in favour of whatever the last
        # attempt happened to be. See verdict.py; it cost 233 listings.
        chosen = min(tries, key=lambda t: verdict.rank(t[0]))
        v, code, det, ms = chosen
        return {"host": h, "band": band, "listings": n[h], "url": u,
                "declared_type": k, "verdict": v, "http": code,
                "detail": det, "ms": ms, "example_name": nm,
                "attempts": [{"verdict": t[0], "http": t[1], "ms": t[3],
                              "url": uu} for t, uu in zip(tries, used)],
                "paths_tried": len(set(used)),
                "flapped": len({t[0] for t in tries}) > 1}

    out = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        jobs = [(h, "head") for h in head] + [(h, "tail") for h in tail]
        for i, row in enumerate(ex.map(lambda j: one(*j), jobs), 1):
            out.append(row)
            if i % 50 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    def tally(band):
        rows = [r for r in out if r["band"] == band]
        c = collections.Counter(r["verdict"] for r in rows)
        lc = collections.Counter()
        for r in rows:
            lc[r["verdict"]] += r["listings"]
        return rows, c, lc

    print()
    for band in ("head", "tail"):
        rows, c, lc = tally(band)
        if not rows:
            continue
        fl = sum(1 for r in rows if r.get("flapped"))
        print(f"{band.upper()}  {len(rows):,} hosts, {sum(lc.values()):,} listings"
              + (f"   [{fl} hosts gave different answers across attempts]" if fl else ""))
        for v, k in c.most_common():
            print(f"  {v:9} {k:>5} hosts  {k/len(rows)*100:5.1f}%   "
                  f"{lc[v]:>7,} listings  {lc[v]/max(sum(lc.values()),1)*100:5.1f}%")
        print()

    stamp = datetime.date.today().strftime("%Y%m%d")
    outp = a.out or os.path.join(HERE, f"probe_{stamp}.json.gz")
    with gzip.open(outp, "wt") as f:
        json.dump({"snapshot": os.path.basename(path), "head_min": a.head_min,
                   "tail_sampled": len(tail), "tail_pool": len(tail_pool),
                   "seed": a.seed, "timeout": a.timeout,
                   "when": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "rows": out}, f)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
