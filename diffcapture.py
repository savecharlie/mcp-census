#!/usr/bin/env python3
"""diffcapture.py -- what CHANGED between two tools.py captures.

Every other number in this census is a cross-section, and a cross-section
cannot see a server changing its own mind. Fire 311's cohort panel is flat at
~37% from April to September, and it is flat for a reason that has nothing to
do with whether directiveness is rising: a server that rewrote all of its
descriptions last Tuesday is still filed under the month its listing first
appeared. The only cure is the SAME hosts, twice, with a hash written down
before anything happened to them.

POPULATION -- the thing that decides whether the answer means anything.
Only hosts that returned a tools list in BOTH captures. A host that was live in
September and errors today is attrition, not change, and mixing the two gives a
"churn rate" that mostly measures outages. Printed as its own line, never
folded in.

THE FLOOR. A 7-day change rate is uninterpretable without the 0-day change
rate. Some servers mint descriptions dynamically; a re-probe five minutes apart
can differ for reasons that have nothing to do with anyone editing anything.
`--floor N` re-probes N of today's own hosts a second time, right now, and
reports the same-day churn. Subtract that, or at minimum print it beside the
headline. (verify skill, law 1: measure the floor on input that cannot contain
the thing.)

    python3 diffcapture.py OLD.json.gz NEW.json.gz
    python3 diffcapture.py OLD NEW --floor 120 --examples 12
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    return json.load(gzip.open(p, "rt"))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100*k/n:.1f}% [{100*lo:.1f}, {100*hi:.1f}] ({k}/{n})"


def index(cap):
    """host -> {tool name -> row}. Only hosts that actually served a list.

    Duplicate tool names inside one server are kept as a count and the FIRST
    row wins, because a name is how a diff joins and a server serving the same
    name twice has already broken that join itself. Reported, not hidden.
    """
    out, dupes = {}, 0
    for r in cap["rows"]:
        if r.get("error") or "tools" not in r:
            continue
        d = {}
        for t in r["tools"]:
            if t["name"] in d:
                dupes += 1
                continue
            d[t["name"]] = t
        out[r["host"]] = d
    return out, dupes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--examples", type=int, default=8)
    ap.add_argument("--seed", type=int, default=317)
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args()

    O, Od = load(a.old), None
    N = load(a.new)
    oi, od = index(O)
    ni, nd = index(N)

    both = sorted(set(oi) & set(ni))
    only_old = sorted(set(oi) - set(ni))
    only_new = sorted(set(ni) - set(oi))

    print(f"# {os.path.basename(a.old)}  ->  {os.path.basename(a.new)}")
    print(f"  captured {O.get('when','?')}  ->  {N.get('when','?')}")
    print(f"  hosts serving a tools list: {len(oi)} -> {len(ni)}")
    print(f"  PANEL (both):      {len(both)}")
    print(f"  attrition (old only): {len(only_old)}   new only: {len(only_new)}")
    print(f"  duplicate tool names dropped: old {od}, new {nd}")
    print()

    # ---- tool-level, within the panel ----
    same_desc = chg_desc = same_sch = chg_sch = 0
    added = removed = 0
    srv_any_desc = srv_any = 0
    changed_rows = []           # (host, name, old, new)
    added_rows, removed_rows = [], []
    for h in both:
        o, n = oi[h], ni[h]
        ok, nk = set(o), set(n)
        inter = ok & nk
        add = nk - ok
        rem = ok - nk
        added += len(add)
        removed += len(rem)
        for k in sorted(add):
            added_rows.append((h, k, n[k]))
        for k in sorted(rem):
            removed_rows.append((h, k, o[k]))
        hit = False
        for k in sorted(inter):
            if o[k]["desc_sha"] == n[k]["desc_sha"]:
                same_desc += 1
            else:
                chg_desc += 1
                hit = True
                changed_rows.append((h, k, o[k], n[k]))
            if o[k]["schema_sha"] == n[k]["schema_sha"]:
                same_sch += 1
            else:
                chg_sch += 1
        srv_any += 1
        if hit or add or rem:
            srv_any_desc += 1

    pairs = same_desc + chg_desc
    print("## tools present under the same name on the same host, both captures")
    print(f"  joined pairs                 {pairs}")
    print(f"  DESCRIPTION changed          {pct(chg_desc, pairs)}")
    print(f"  input SCHEMA changed         {pct(chg_sch, pairs)}")
    print(f"  tools ADDED (panel hosts)    {added}")
    print(f"  tools REMOVED (panel hosts)  {removed}")
    print(f"  servers with ANY change      {pct(srv_any_desc, srv_any)}")
    print()

    # ---- is the change cosmetic? ----
    def norm(s):
        return " ".join((s or "").split())

    cosmetic = subst = 0
    grew = shrank = 0
    dch = []
    for h, k, o, n in changed_rows:
        if norm(o.get("desc")) == norm(n.get("desc")):
            cosmetic += 1
        else:
            subst += 1
        a_ = o.get("desc_chars", len(o.get("desc", "")))
        b_ = n.get("desc_chars", len(n.get("desc", "")))
        dch.append(b_ - a_)
        if b_ > a_:
            grew += 1
        elif b_ < a_:
            shrank += 1
    if changed_rows:
        print("## of the changed descriptions")
        print(f"  whitespace-only (cosmetic)   {pct(cosmetic, len(changed_rows))}")
        print(f"  substantive                  {pct(subst, len(changed_rows))}")
        print(f"  got longer / shorter / same  {grew} / {shrank} / {len(changed_rows)-grew-shrank}")
        dch.sort()
        print(f"  median char delta            {dch[len(dch)//2]:+d}")
        print()

        rnd = random.Random(a.seed)
        samp = rnd.sample(changed_rows, min(a.examples, len(changed_rows)))
        print(f"## {len(samp)} changed descriptions, drawn at random (seed {a.seed})")
        print("   shown from the FIRST POINT OF DIVERGENCE, not from the head --")
        print("   `imperatives.py` printed the first 130 chars as its example for two")
        print("   fires and several cited examples did not visibly contain the thing")
        print("   being cited. The same bug here would show two identical openings.")
        for h, k, o, n in samp:
            A_, B_ = norm(o.get("desc")), norm(n.get("desc"))
            j = 0
            while j < min(len(A_), len(B_)) and A_[j] == B_[j]:
                j += 1
            s = max(0, j - 40)
            print(f"  --- {h}  ::  {k}   (diverges at char {j} of {len(A_)}/{len(B_)})")
            print(f"      OLD ...{A_[s:j]}>>>{A_[j:j+150]}")
            print(f"      NEW ...{B_[s:j]}>>>{B_[j:j+150]}")
        print()

    if a.json_out:
        json.dump({"panel": both, "changed": [(h, k, o.get("desc"), n.get("desc"))
                                              for h, k, o, n in changed_rows],
                   "added": [(h, k) for h, k, _ in added_rows],
                   "removed": [(h, k) for h, k, _ in removed_rows]},
                  gzip.open(a.json_out, "wt"))
        print(f"wrote {a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
