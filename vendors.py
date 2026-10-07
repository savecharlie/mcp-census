#!/usr/bin/env python3
"""vendors.py -- the NAMED-DEPENDENCY cohort: servers a paying team actually depends on.

WHY THIS EXISTS, and it is a correction to my own census.

`probe.py` samples hosts two ways: the TOP hosts by listing count, plus a uniform
random tail. Every vendor publishes exactly ONE listing on ONE host, so no vendor
is ever in the top slice, and the tail sampled 1,058 of 14,974 hosts -- about 7%.
With ~18 vendor hosts in the registry the expected number reaching the sample is
1.3, and the 4 Oct capture got zero. The 3.4%/week tool-description churn rate is
therefore measured on 1,015 paired hosts of which NOT ONE is a server any team
pays for. Checked by hand: every apparent brand hit was a false positive --
`regsentry.com` (an unrelated company), `io.github.*` (hobbyist namespaces),
`*.supabase.co` and `*.vercel.app` (hobby deploys).

The number is not wrong. It is about a population that cannot contain the
customer's dependency. That is a sampling defect, and this file is the repair.

WHY THE COHORT IS HAND-NAMED, which looks like a weakness and is not.
There is no field in the registry that identifies a depended-upon server. No
downloads, no stars, no installs, no usage of any kind -- the registry does not
know which of its 36,550 servers anyone runs. I tested the one objective rule
available, "namespace is a DNS-verified company domain rather than io.github.*",
and it admits 12,135 listings whose random sample looks like
`com.abyssfallgame/mcp` and `com.aiurion/agentic-3d-printing`. Domain
verification proves somebody bought a domain for ten dollars.
So the cohort is a written-down list of brands, published so it can be argued
with -- which is exactly Tripwire's model, because only the customer knows what
they depend on.

WHAT THIS ANSWERS that the population number cannot:
  1. Is the vendor server even LISTED in the registry? (resolve against the snapshot)
  2. Does it answer an unauthenticated `tools/list`? If vendors all return 401,
     the flagship alarm -- *your dependency changed what its tools claim to do* --
     is UNDELIVERABLE for them without the customer's own credentials, and that is
     a product-defining fact worth one HTTP request each to learn.
  3. A dated baseline, so that in seven days there is a churn rate for the cohort
     that matters instead of one for the cohort that happened to be sampled.

    python3 vendors.py                      # resolve + probe, write vendors_<date>.json.gz
    python3 vendors.py --resolve-only       # just show what the registry has
    python3 vendors.py --diff A.json.gz B.json.gz
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tools import fetch, _tool_row, newest  # reuse the handshake, never rewrite it

# Hand-named. A brand belongs here if a real team would write it in a
# dependency list and be annoyed if it changed under them. Argue with it; that
# is the point of it being a file.
BRANDS = [
    "notion", "stripe", "linear", "atlassian", "paypal", "figma", "canva",
    "webflow", "vercel", "supabase", "grafana", "zapier", "monday", "airtable",
    "cloudflare", "sentry", "github", "gitlab", "huggingface", "deepwiki",
    "square", "shopify", "asana", "intercom", "box", "dropbox", "plaid",
    "clickup", "slack", "datadog", "mongodb", "elastic", "neon", "sanity",
    "contentful", "twilio", "sendgrid", "netlify", "railway", "render",
    "auth0", "okta", "workos", "clerk", "resend", "posthog", "amplitude",
    "segment", "snowflake", "databricks", "hasura", "prisma", "planetscale",
    "upstash", "pinecone", "weaviate", "qdrant", "exa", "perplexity", "brave",
    "firecrawl", "apify", "browserbase", "e2b", "modal", "replicate", "groq",
    "openrouter", "cohere", "jina", "llamaindex", "langchain", "sonarqube",
    "jfrog", "circleci", "pagerduty", "launchdarkly", "snyk", "wiz",
    "hubspot", "salesforce", "zendesk", "freshdesk", "docusign", "quickbooks",
    "xero", "ramp", "brex", "mercury", "wise", "coinbase", "alchemy", "infura",
]


def load_registry(path: str | None = None):
    path = path or newest(os.path.join(HERE, "registry_*.json.gz"))
    if not path:
        raise SystemExit("no registry_*.json.gz snapshot found")
    return path, json.load(gzip.open(path, "rt"))


# A host on one of these is a CUSTOMER'S project on the platform, never the
# platform's own server. `app.vercel.agent-svg-registry/mcp` is structurally
# identical to `com.cloudflare.mcp/mcp` and means the opposite thing; the host is
# what tells them apart. First pass resolved six of these as vendor servers.
PAAS = (".vercel.app", ".netlify.app", ".up.railway.app", ".workers.dev",
        ".supabase.co", ".fly.dev", ".onrender.com", ".herokuapp.com",
        ".pages.dev", ".streamlit.app", ".replit.app", ".koyeb.app",
        ".railway.app", ".deno.dev", ".glitch.me", ".github.io")

# Verified by hand against the printed resolution table and rejected. Each is a
# namespace that merely CONTAINS a brand word.
REJECT_NAMES = {
    "al.square/fiskalizimi",                      # Albanian ns, not Square
    "io.github.HOTAgithub/hailab-japan-company-api",
}

# Brand-owned hostnames that do not follow mcp.<brand>.<tld>.
EXTRA_HOSTS = {
    "github": ("api.githubcopilot.com",),
    "upstash": ("mcp.context7.com",),
    "neon": ("mcp.neon.tech",),
    "planetscale": ("mcp.pscale.dev",),
    "sentry": ("mcp.sentry.dev",),
    "huggingface": ("huggingface.co",),
    "gitlab": ("gitlab.com",),
}

TEMPLATE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}|myPlatform|YOUR_|<[a-z]+>")


def _ns_labels(ns):
    return ns.split(".")


def resolve(rows, brands=BRANDS):
    """Find the listing a brand OWNS, scoring candidates instead of taking the
    first match. Two proofs of ownership, and the HOST one outranks the namespace
    one because a namespace can be a project path on a platform the brand owns.

    Every candidate is kept so the chosen one can be audited; `--resolve-only`
    prints the runners-up with `--verbose`."""
    cands = {}
    for r in rows:
        s = r["server"]
        name = s.get("name") or ""
        low = name.lower()
        ns = low.split("/")[0]
        rem = [x for x in (s.get("remotes") or []) if x.get("url")]
        url = rem[0]["url"] if rem else ""
        host = url.split("//")[-1].split("/")[0].lower()
        if low in REJECT_NAMES:
            continue
        labels = _ns_labels(ns)
        for b in brands:
            hosts = tuple("mcp." + b + "." + t for t in
                          ("com", "ai", "dev", "app", "io", "co", "net", "tech"))
            hosts += (b + ".com", "api." + b + ".com", "mcp." + b)
            hosts += EXTRA_HOSTS.get(b, ())
            owned_host = host in hosts
            # namespace ownership: the brand must be the SECOND label of a
            # reversed domain (com.stripe, app.linear, ai.exa) and the whole
            # namespace at most 3 labels, so a 4-label PaaS project path
            # (app.railway.up.airy-enthusiasm-production) cannot qualify.
            owned_ns = (len(labels) >= 2 and labels[1] == b and len(labels) <= 3)
            if ns.startswith("io.github."):
                org = labels[2] if len(labels) > 2 else ""
                owned_ns = (org == b) and b != "github"
            if not (owned_host or owned_ns):
                continue
            if host and any(host.endswith(x) for x in PAAS) and not owned_host:
                continue  # customer project on a platform, not the platform
            meta = (r.get("_meta") or {}).get(
                "io.modelcontextprotocol.registry/official") or {}
            score = 0
            score += 10 if owned_host else 0
            score += 3 if owned_ns else 0
            score += 2 if url else 0
            score += 1 if meta.get("status") == "active" else 0
            score -= 8 if TEMPLATE.search(url) else 0
            cands.setdefault(b, []).append((score, {
                "brand": b, "name": s.get("name"), "version": s.get("version"),
                "url": url, "transport": rem[0].get("type") if rem else None,
                "title": s.get("title"), "status": meta.get("status"),
                "publishedAt": meta.get("publishedAt"),
                "updatedAt": meta.get("updatedAt"),
                "proof": "host" if owned_host else "namespace",
                "score": score,
            }))
    out, runners = {}, {}
    for b, lst in cands.items():
        lst.sort(key=lambda t: -t[0])
        if lst[0][0] <= 0:
            continue  # only a template or a rejected shape survived
        out[b] = lst[0][1]
        runners[b] = [c for _, c in lst[1:6]]
    return out, runners


def probe_one(v, timeout=20.0):
    row = dict(v)
    if not v.get("url"):
        row.update(verdict="no-remote", n_tools=None, tools=[], err=None)
        return row
    # AN SSE ENDPOINT IS NOT A BROKEN ONE. `fetch()` POSTs an initialize, which
    # the legacy SSE transport answers with 404 because it expects a GET that
    # holds the stream open. The first run of this file reported
    # `prisma http-404` and that was MY instrument, not their server. SSE hosts
    # cannot have their tools listed this way at all, so they are declared
    # unattempted and excluded from every rate rather than counted as failures.
    if (v.get("transport") or "") == "sse":
        row.update(verdict="sse-not-attempted", n_tools=None, tools=[],
                   err="declared sse; tools/list needs the GET-stream transport")
        return row
    try:
        info, tools, err = fetch(v["url"], timeout)
        row["server_name"] = info.get("name")
        row["server_version"] = info.get("version")
        if tools is None:
            row.update(verdict="init-ok-list-refused", n_tools=None,
                       tools=[], err=err)
        else:
            row.update(verdict="live", n_tools=len(tools),
                       tools=[_tool_row(t) for t in tools], err=None)
    except Exception as e:
        code = getattr(e, "code", None)
        if code in (401, 402, 403):
            vd = "auth"
        elif code:
            vd = f"http-{code}"
        else:
            vd = type(e).__name__
        row.update(verdict=vd, n_tools=None, tools=[],
                   err=str(e)[:140])
    return row


def diff(a_path, b_path):
    A = json.load(gzip.open(a_path, "rt"))
    B = json.load(gzip.open(b_path, "rt"))
    ai = {r["brand"]: r for r in A["rows"]}
    bi = {r["brand"]: r for r in B["rows"]}
    print(f"{A['when'][:10]} -> {B['when'][:10]}")
    paired = [b for b in bi if b in ai and ai[b]["verdict"] == "live"
              and bi[b]["verdict"] == "live"]
    print(f"paired live: {len(paired)}")
    nch = 0
    for b in sorted(paired):
        oa = {t["name"]: t["desc_sha"] for t in ai[b]["tools"]}
        ob = {t["name"]: t["desc_sha"] for t in bi[b]["tools"]}
        added = set(ob) - set(oa)
        gone = set(oa) - set(ob)
        moved = [n for n in set(oa) & set(ob) if oa[n] != ob[n]]
        if added or gone or moved:
            nch += 1
            print(f"  {b:14s} +{len(added)} -{len(gone)} ~{len(moved)}"
                  f"  ver {ai[b]['version']} -> {bi[b]['version']}")
    print(f"\ncohort churn: {nch}/{len(paired)} servers changed something")
    for b in sorted(set(bi) | set(ai)):
        va = ai.get(b, {}).get("verdict", "-")
        vb = bi.get(b, {}).get("verdict", "-")
        if va != vb:
            print(f"  VERDICT {b:14s} {va} -> {vb}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve-only", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--diff", nargs=2)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()

    if a.diff:
        return diff(*a.diff)

    rpath, rows = load_registry()
    found, runners = resolve(rows)
    missing = [b for b in BRANDS if b not in found]
    print(f"registry: {os.path.basename(rpath)}  ({len(rows):,} listings)")
    print(f"cohort named: {len(BRANDS)}   resolved: {len(found)}   "
          f"absent from registry: {len(missing)}")
    print(f"absent: {' '.join(missing)}\n")
    for b in sorted(found):
        v = found[b]
        print(f"  {b:13s} {str(v['name'])[:36]:36s} {v['proof']:9s} "
              f"{(v['url'] or '-')[:48]}")
    if a.verbose:
        print("\n--- runners-up (audit the choice) ---")
        for b in sorted(runners):
            for c in runners[b]:
                print(f"  {b:13s} {str(c['name'])[:40]:40s} "
                      f"{c['proof']:9s} s={c['score']:>3} {(c['url'] or '-')[:40]}")
    if a.resolve_only:
        return 0

    print(f"\nprobing {len(found)} hosts...\n")
    out = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(probe_one, v, a.timeout): b
                for b, v in sorted(found.items())}
        for f in cf.as_completed(futs):
            out.append(f.result())
    out.sort(key=lambda r: r["brand"])

    by = {}
    for r in out:
        by.setdefault(r["verdict"], []).append(r["brand"])
    print(f"{'brand':14s} {'verdict':22s} {'tools':>5s}  listing")
    for r in out:
        print(f"{r['brand']:14s} {r['verdict']:22s} "
              f"{('' if r['n_tools'] is None else r['n_tools']):>5}  "
              f"{str(r['name'])[:40]}")
    print()
    for v in sorted(by, key=lambda k: -len(by[k])):
        print(f"  {v:22s} {len(by[v]):3d}   {' '.join(sorted(by[v]))[:90]}")

    live = [r for r in out if r["verdict"] == "live"]
    ntools = sum(r["n_tools"] for r in live)
    # DENOMINATOR: only hosts that declare a streamable-http remote and were
    # actually attempted. `no-remote` listings are package-only (nothing to
    # probe) and `sse-not-attempted` is this instrument's limitation, not a
    # property of the server. Mixing either in would make the rate measure my
    # own coverage.
    attempted = [r for r in out
                 if r["verdict"] not in ("no-remote", "sse-not-attempted")]
    auth = [r for r in attempted if r["verdict"] == "auth"]
    print(f"\nattempted (declares streamable-http remote): {len(attempted)}"
          f" of {len(out)} resolved")
    print(f"  LIVE unauthenticated : {len(live):>3}/{len(attempted)}"
          f"   ({ntools} tool descriptions captured)")
    print(f"  401 auth required    : {len(auth):>3}/{len(attempted)}"
          f"   ({100*len(auth)/max(1,len(attempted)):.0f}%)")
    print(f"  package-only listings: {sum(1 for r in out if r['verdict']=='no-remote'):>3}"
          f"   (no remote to watch)")

    stamp = dt.date.today().isoformat().replace("-", "")
    path = os.path.join(HERE, f"vendors_{stamp}.json.gz")
    with gzip.open(path, "wt") as fh:
        json.dump({"when": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "registry": os.path.basename(rpath),
                   "brands_named": BRANDS, "n_resolved": len(found),
                   "absent": missing, "rows": out}, fh)
    print(f"wrote {os.path.basename(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
