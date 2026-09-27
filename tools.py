#!/usr/bin/env python3
"""tools.py -- capture the TOOL metadata a live MCP server actually serves.

Fire 303, and the reason it exists tonight rather than next week: A2M
(arXiv:2609.26761) optimises a tool's NAME AND DESCRIPTION to get itself
selected, and neither of those is in the registry. The registry carries a
SERVER description; the tool-level pair `(name, description)` only exists in the
server's own `tools/list` reply. So the attack surface that paper measures is one
probe deeper than any registry census can see, and the only way to know whether
that surface CHANGES is to have written it down before it changed.

**A baseline captured a week late is not a baseline.** That is the whole argument
for doing this in the same fire that read the paper.

Stores, per tool: name, description, a sha256 of the input schema, and a sha256
of the description. A diff next week is then exact and cheap, and a changed
description is detectable even if the name is unchanged -- which is the direction
that matters, because the name is what a human remembers and the description is
what the model reads.

PROTOCOL, the parts that bite:
  * streamable-http is THREE requests, not one: POST `initialize`, then POST the
    `notifications/initialized` notification carrying the `Mcp-Session-Id`
    header the server handed back, then POST `tools/list` with the same header.
    Skip the notification and conforming servers answer "Received request before
    initialization was complete".
  * the reply may be JSON or an SSE frame (`event: message\\ndata: {...}`)
    depending on the server, on the SAME endpoint. Parse both.
  * `sse`-type remotes need a GET stream and a separate POST endpoint; they are
    SKIPPED here and counted, rather than guessed at. A skipped row is honest; a
    guessed one is a fake baseline.

    python3 tools.py                      # every host the last probe found live
    python3 tools.py --hosts a.com,b.com
"""
from __future__ import annotations

import argparse
import datetime
import glob
import gzip
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "iris-mcp-census/0.1 (+https://github.com/savecharlie)"
PROTO = "2025-06-18"


def sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def newest(pat: str) -> str | None:
    c = sorted(p for p in glob.glob(os.path.join(HERE, pat)) if "allver" not in p)
    return c[-1] if c else None


def post(url, payload, session=None, timeout=20.0, notify=False):
    h = {"User-Agent": UA, "Content-Type": "application/json",
         "Accept": "application/json, text/event-stream"}
    if session:
        h["Mcp-Session-Id"] = session
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        sid = r.headers.get("Mcp-Session-Id") or session
        if notify:
            return {}, sid
        body = r.read(400_000).decode("utf-8", "replace")
        return parse(body), sid


def parse(body: str):
    """JSON, or the data: line of an SSE frame. Same endpoint serves either."""
    b = body.strip()
    if b.startswith("{"):
        return json.loads(b)
    for line in b.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except Exception:
                continue
    raise ValueError("unparseable body: " + b[:80])


def fetch(url: str, timeout: float):
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": PROTO, "capabilities": {},
                       "clientInfo": {"name": "iris-mcp-census", "version": "0.1"}}}
    d, sid = post(url, init, timeout=timeout)
    info = ((d.get("result") or {}).get("serverInfo") or {})
    try:
        post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"},
             session=sid, timeout=timeout, notify=True)
    except Exception:
        pass
    d2, _ = post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list",
                       "params": {}}, session=sid, timeout=timeout)
    if "error" in d2:
        return info, None, str(d2["error"])[:120]
    return info, ((d2.get("result") or {}).get("tools") or []), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default=None)
    ap.add_argument("--hosts", default=None)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.hosts:
        jobs = [{"host": h, "url": "https://" + h, "declared_type": "streamable-http",
                 "listings": 0} for h in a.hosts.split(",")]
    else:
        p = a.probe or newest("probe_2*.json.gz")
        if not p:
            sys.exit("no probe file; run probe.py first")
        pd = json.load(gzip.open(p, "rt"))
        jobs = [r for r in pd["rows"] if r["verdict"] == "live"]
        print(f"# from {os.path.basename(p)}: {len(jobs)} live hosts")

    sse = [j for j in jobs if j.get("declared_type") == "sse"]
    jobs = [j for j in jobs if j.get("declared_type") != "sse"]
    print(f"  {len(jobs)} streamable-http, {len(sse)} sse SKIPPED (not guessed)")

    def one(j):
        row = {"host": j["host"], "url": j["url"], "listings": j.get("listings", 0)}
        try:
            info, tools, err = fetch(j["url"], a.timeout)
            row["server_name"] = info.get("name", "")
            row["server_version"] = info.get("version", "")
            if tools is None:
                row["error"] = err
                return row
            row["tools"] = [{"name": t.get("name", ""),
                             "desc": (t.get("description") or "")[:2000],
                             "desc_sha": sha(t.get("description") or ""),
                             "schema_sha": sha(json.dumps(
                                 t.get("inputSchema") or {}, sort_keys=True))}
                            for t in tools]
            row["n_tools"] = len(row["tools"])
        except urllib.error.HTTPError as e:
            row["error"] = f"http {e.code}"
        except Exception as e:
            row["error"] = type(e).__name__ + ": " + str(e)[:90]
        return row

    out = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, r in enumerate(ex.map(one, jobs), 1):
            out.append(r)
            if i % 20 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)

    ok = [r for r in out if "tools" in r]
    ntools = sum(r["n_tools"] for r in ok)
    print(f"\n{len(ok)} of {len(jobs)} hosts served a tool list; {ntools:,} tools")
    if ok:
        big = sorted(ok, key=lambda r: -r["n_tools"])[:8]
        for r in big:
            print(f"  {r['n_tools']:>4} tools  {r['host']}  ({r['listings']} listings)")
    errs = {}
    for r in out:
        if "error" in r:
            errs[r["error"][:40]] = errs.get(r["error"][:40], 0) + 1
    for k, v in sorted(errs.items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {v:>4}  {k}")

    stamp = datetime.date.today().strftime("%Y%m%d")
    outp = a.out or os.path.join(HERE, f"tools_{stamp}.json.gz")
    with gzip.open(outp, "wt") as f:
        json.dump({"when": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "sse_skipped": [j["host"] for j in sse], "rows": out}, f)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
