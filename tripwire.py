#!/usr/bin/env python3
"""tripwire.py -- Tier 1: what a named MCP server DECLARES, and when it changes.

PRODUCT.md section 6b split Tripwire's alarm set in two. Tier 2 -- the tool
descriptions, the alarm with teeth -- is sealed behind a 401 for 28 of the 32
vendor servers a paying team actually names, so it needs the customer's own
credential. Tier 1 needs NOTHING: no probe, no token, no permission. It is a
diff of two registry snapshots on the fields that constitute a server's
identity. Section 6d item 2 has said "cheap; the snapshots already exist" since
27 September and no fire took it, because it is the less exciting half.

This is that half, and it answers the question the exciting half cannot:
HOW OFTEN DOES ANY OF THIS ACTUALLY MOVE, for the servers anyone depends on?
A monitoring product has to state its own base rate or it is selling a feeling.

THE SIX TIER-1 SIGNALS, from the schema as it actually is (checked, not
remembered -- `_meta."io.modelcontextprotocol.registry/official"` carries status
and the timestamps; `server.packages[].identifier` carries the package owner):

    version     server.version changed
    remote      a declared remote URL added, removed or changed host
    package     a package identifier, registry or owner added/removed/changed
    repo        server.repository.url changed
    status      _meta status changed (-> deprecated / deleted)
    delisted    the name is gone from the newer snapshot entirely

A seventh, LIVENESS, is a probe and lives in probe.py; a 401 is a HEALTHY
response there and must never be folded into an unreachable count.

WHY IT FOLLOWS NAMES AND NOT BRANDS. A customer writes down a server, not a
company. So the cohort is resolved ONCE from the OLDER snapshot -- that is the
list they would have written on day zero -- and those exact registry names are
then looked up in the newer one. Re-resolving per snapshot would silently swap
which listing is being watched and call the swap a change.

    python3 tripwire.py A.json.gz B.json.gz            cohort + population
    python3 tripwire.py A.json.gz B.json.gz --names-file list.txt
    python3 tripwire.py A.json.gz B.json.gz --json out.json

Iris (Opus 5), 8 Oct 2026.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OFFICIAL = "io.modelcontextprotocol.registry/official"


def load(path):
    rows = json.load(gzip.open(path, "rt"))
    out = {}
    for r in rows:
        s = r.get("server") or {}
        nm = s.get("name")
        if nm:
            out[nm] = r
    return out


def host(url):
    return (url or "").split("//")[-1].split("/")[0].lower()


def ident(row):
    """The identity of a listing: everything a dependant is trusting."""
    s = row.get("server") or {}
    m = (row.get("_meta") or {}).get(OFFICIAL) or {}
    rem = sorted((x.get("type") or "", x.get("url") or "")
                 for x in (s.get("remotes") or []))
    pkg = sorted((p.get("registryType") or "", p.get("registryBaseUrl") or "",
                  p.get("identifier") or "")
                 for p in (s.get("packages") or []))
    return {
        "version": s.get("version"),
        "remotes": rem,
        "hosts": sorted({host(u) for _, u in rem if u}),
        "packages": pkg,
        "repo": ((s.get("repository") or {}).get("url") or "").lower(),
        "status": m.get("status"),
        "updatedAt": m.get("updatedAt"),
    }


def _repo_org(u):
    """host + first path element, i.e. who owns the source."""
    parts = [x for x in (u or "").split("//")[-1].split("/") if x]
    return "/".join(parts[:2]) if len(parts) >= 2 else (u or "")


def _devers(text, *versions):
    """Remove any declared version string from a package identifier."""
    out = text or ""
    for v in versions:
        if not v:
            continue
        for form in (v, v.lstrip("vV")):
            if form:
                out = out.replace(form, "<V>")
    return out


def _pkg_keys(pkgs, *versions):
    return sorted((t, b, _devers(i, *versions)) for t, b, i in pkgs)


def _owners(pkgs):
    """Best effort at WHO publishes the artifact -- the thing a supply-chain
    alarm is actually about. npm `@scope/name` -> `@scope`; an OCI
    `registry/owner/name:tag` -> `registry/owner`; a URL -> host + first path."""
    out = set()
    for _, _, ident_ in pkgs:
        if not ident_:
            continue
        x = ident_.split("://")[-1].split(":")[0]
        parts = [q for q in x.split("/") if q]
        if ident_.startswith("@"):
            out.add(ident_.split("/")[0])
        elif len(parts) >= 2:
            out.add("/".join(parts[:2]))
        elif parts:
            out.add(parts[0])
    return out


SIGNALS = ("version", "remote", "package", "repo-removed", "repo-added",
           "repo-renamed", "repo-reowned", "status", "delisted")

# The subset a security alarm should actually wake someone for. Everything else
# in SIGNALS is either news the package registry already sends you (version) or
# a publishing artifact (a dropped repository field, a remote appearing for the
# first time, a repo renamed inside the same org).
TEETH = ("package", "repo-reowned", "status", "delisted")


def compare(a_row, b_row):
    """-> list of (signal, detail). Empty list means nothing declared moved."""
    if b_row is None:
        return [("delisted", "name absent from the newer snapshot")]
    A, B = ident(a_row), ident(b_row)
    out = []
    if A["version"] != B["version"]:
        out.append(("version", f"{A['version']} -> {B['version']}"))
    if A["remotes"] != B["remotes"]:
        # ADDED IS NOT MOVED. The first run printed
        # `firecrawl host moved: [] -> ['mcp.firecrawl.dev']`, which is wrong in
        # a way that matters: that server had NO declared remote and now has
        # one, so a dependant who was running it locally is now offered a cloud
        # endpoint. That is a different event from a host being swapped under
        # you, and a product that calls them both "moved" is lying in the
        # direction that sounds more alarming.
        ga, gb = set(A["hosts"]), set(B["hosts"])
        if not ga and gb:
            kind = f"remote ADDED: {sorted(gb)}"
        elif ga and not gb:
            kind = f"remote REMOVED: was {sorted(ga)}"
        elif ga != gb:
            kind = f"host MOVED: {sorted(ga)} -> {sorted(gb)}"
        else:
            kind = f"url/type changed: {A['remotes']} -> {B['remotes']}"
        out.append(("remote", kind))
    if A["packages"] != B["packages"]:
        # A PACKAGE CHANGE THAT IS ONLY THE VERSION IS NOT AN INDEPENDENT ALARM.
        # First run of this file reported "package 3" for the vendor cohort and
        # every one of the three was a version string living INSIDE the
        # identifier: `ghcr.io/github/github-mcp-server:1.12.2` -> `:2.0.2`,
        # `docker.io/grafana/mcp-grafana:1.6.0` -> `:2.0.1`, and an mcpb release
        # URL carrying `mcpb-v4.1.1` -> `mcpb-v4.2.0`. No owner moved, no
        # registry moved. Counting those as package alarms double-counts the
        # version bump and inflates the rate by exactly the servings that
        # publish containers. Strip the declared versions out of the
        # identifiers; if that makes them identical, it WAS the version.
        ka = _pkg_keys(A["packages"], A["version"], B["version"])
        kb = _pkg_keys(B["packages"], A["version"], B["version"])
        if ka != kb:
            oa, ob = _owners(A["packages"]), _owners(B["packages"])
            out.append(("package",
                        f"owner {sorted(oa)} -> {sorted(ob)}" if oa != ob
                        else f"{sorted(ka)} -> {sorted(kb)}"))
    if A["repo"] != B["repo"]:
        # REMOVED IS NOT RETARGETED. 645 servers fired this signal over the
        # 11-day window and 490 of them simply DROPPED the repository field --
        # a publishing artifact, not a supply-chain event. 73 added it. Of the
        # 82 genuine URL changes only 12 land on a different host+org, which is
        # the only variant a security alarm should wake anyone for. Reporting
        # 1.77% as "the source moved" would have been off by 54x.
        ra, rb = A["repo"], B["repo"]
        if ra and not rb:
            out.append(("repo-removed", f"was {ra}"))
        elif rb and not ra:
            out.append(("repo-added", rb))
        elif _repo_org(ra) != _repo_org(rb):
            out.append(("repo-reowned", f"{ra} -> {rb}"))
        else:
            out.append(("repo-renamed", f"{ra} -> {rb}"))
    if A["status"] != B["status"]:
        out.append(("status", f"{A['status']} -> {B['status']}"))
    return out


def wilson(k, n, z=1.96):
    """95% CI for a proportion. 6/42 without an interval is not a measurement."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def rate(n, d):
    if not d:
        return f"{n}/{d}"
    lo, hi = wilson(n, d)
    return (f"{n}/{d} ({100.0*n/d:.1f}%, 95% CI "
            f"[{100*lo:.1f}, {100*hi:.1f}])")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--names-file")
    ap.add_argument("--json")
    ap.add_argument("--quiet-population", action="store_true")
    a = ap.parse_args()

    A, B = load(a.old), load(a.new)
    print(f"{os.path.basename(a.old)}  {len(A):,} servers")
    print(f"{os.path.basename(a.new)}  {len(B):,} servers")
    print(f"paired by name: {len(set(A) & set(B)):,}   "
          f"new in the newer snapshot: {len(set(B)-set(A)):,}   "
          f"gone: {len(set(A)-set(B)):,}\n")

    # ---- the cohort a customer would have written down -------------------
    if a.names_file:
        names = [l.strip() for l in open(a.names_file) if l.strip()
                 and not l.startswith("#")]
        label = os.path.basename(a.names_file)
    else:
        from vendors import resolve   # resolve ONCE, on the OLDER snapshot
        found, _ = resolve([A[n] for n in A])
        names = [v["name"] for v in found.values()]
        label = f"vendors.py cohort resolved on {os.path.basename(a.old)}"
    names = [n for n in names if n in A]
    print(f"=== COHORT: {label} ===")
    print(f"{len(names)} named servers present in the older snapshot\n")

    fired, counts = [], collections.Counter()
    for n in sorted(names):
        ch = compare(A[n], B.get(n))
        if ch:
            fired.append((n, ch))
            for sig, _ in ch:
                counts[sig] += 1
    if fired:
        for n, ch in fired:
            print(f"  {n}")
            for sig, det in ch:
                print(f"      [{sig}] {det}")
    else:
        print("  (nothing fired)")
    nonver = sum(1 for _, ch in fired
                 if any(sig != "version" for sig, _ in ch))
    print(f"\n  servers with ANY Tier-1 change: {rate(len(fired), len(names))}")
    for s in SIGNALS:
        print(f"    {s:9s} {counts.get(s, 0):4d}")
    # THE NUMBER THAT IS ACTUALLY THE PRODUCT. A version bump is news npm
    # already sends you; it is not a security alarm, and it is the large
    # majority of all firings. Tripwire's teeth are the rest.
    print(f"\n  ...excluding bare version bumps: {rate(nonver, len(names))}")
    teeth = sum(1 for _, ch in fired
                if any(sig in TEETH or (sig == "remote" and "MOVED" in det)
                       for sig, det in ch))
    print(f"  ...security-relevant only {TEETH} + host MOVED:"
          f" {rate(teeth, len(names))}")

    # ---- the same measurement on the whole registry ----------------------
    # Without this the cohort number is uninterpretable: 2 of 40 means one
    # thing if the population is at 1% and the opposite if it is at 30%.
    pop = None
    if not a.quiet_population:
        paired = sorted(set(A) & set(B))
        pc, pfired = collections.Counter(), 0
        for n in paired:
            ch = compare(A[n], B[n])
            if ch:
                pfired += 1
                for sig, _ in ch:
                    pc[sig] += 1
        print(f"\n=== POPULATION, same six signals, same window ===")
        print(f"  paired servers: {len(paired):,}")
        print(f"  servers with ANY Tier-1 change: {rate(pfired, len(paired))}")
        for s in SIGNALS:
            if s == "delisted":
                continue
            print(f"    {s:9s} {pc.get(s,0):6d}  ({100.0*pc.get(s,0)/len(paired):.2f}%)")
        print(f"    {'delisted':9s} {len(set(A)-set(B)):6d}  "
              f"({100.0*len(set(A)-set(B))/len(A):.2f}% of the older snapshot)")
        pteeth = sum(1 for n in paired
                     if any(sig in TEETH or (sig == "remote" and "MOVED" in det)
                            for sig, det in compare(A[n], B[n])))
        pnv = sum(1 for n in paired
                  if any(sig != "version" for sig, _ in compare(A[n], B[n])))
        print(f"\n  ...excluding bare version bumps: {rate(pnv, len(paired))}")
        import math
        print(f"  ...security-relevant only: {rate(pteeth, len(paired))}")
        # IS THE COHORT SAYING ANYTHING THE POPULATION DOES NOT? With n=42 the
        # answer is usually no, and saying so is the difference between a
        # measurement and a flattering coincidence. Expected firings in the
        # cohort if it behaved exactly like the population, and the Poisson
        # probability of seeing what was seen.
        import math
        for what, k, prate in (("non-version", nonver, pnv / len(paired)),
                               ("security-relevant", teeth, pteeth / len(paired))):
            lam = len(names) * prate
            pk = math.exp(-lam) * lam ** k / math.factorial(k)
            print(f"\n  cohort vs population, {what}: observed {k} of"
                  f" {len(names)}, expected {lam:.2f} at the population rate")
            print(f"    P(observe exactly {k} | population rate) = {pk:.2f}"
                  f"  -> {'cohort adds no information' if pk > 0.05 else 'COHORT DIFFERS'}")
        print("\n  events per named dependency per YEAR (window scaled by 365/11):")
        for nm, k, d, what in (("cohort", nonver, len(names), "non-version"),
                               ("population", pnv, len(paired), "non-version"),
                               ("cohort", teeth, len(names), "security-relevant"),
                               ("population", pteeth, len(paired), "security-relevant")):
            print(f"    {nm:11s} {what:18s} {365.0/11.0*k/d:6.2f}")
        pop = {"paired": len(paired), "any": pfired,
               "nonversion": pnv, "teeth": pteeth,
               "by_signal": dict(pc), "delisted": len(set(A) - set(B))}

    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"when": dt.datetime.now(dt.timezone.utc).isoformat(),
                       "old": os.path.basename(a.old),
                       "new": os.path.basename(a.new),
                       "cohort_label": label, "cohort_n": len(names),
                       "cohort_fired": [{"name": n, "changes": ch}
                                        for n, ch in fired],
                       "cohort_by_signal": dict(counts),
                       "population": pop}, fh, indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
