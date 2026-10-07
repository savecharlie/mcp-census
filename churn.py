#!/usr/bin/env python3
"""churn.py -- when a server rewrites a tool description, which way does it move?

Fire 311's cohort panel is flat: ~37% of tools direct the agent, April through
September, slope -0.7 points. I wrote under it that a cross-section cannot see
a server changing its own mind, because a server that rewrote every description
last Tuesday is filed under the month its listing first appeared. This is the
instrument that can see it, and it only exists because fire 303 wrote down a
hash of all 12,829 descriptions before anything happened to them.

PAIRED, WITHIN TOOL. Each row is one (host, tool name) that served a
description in both captures. The comparison is that tool against ITSELF, so
the population cannot drift, the authors cannot change, and the host-level
clustering that forced fire 311 to widen every tool-level CI by x2.31 does not
enter: a tool is its own control. The test is McNemar's on the discordant
pairs, which is the right test for a before/after on the same units and the
only one whose null ("edits are as likely to remove a directive as add one")
is the thing actually in question.

WHAT IT CANNOT SEE: tools whose NAME changed are not joined, so a rename plus
rewrite reads as one removal and one addition. Counted and printed, not folded
into the rate.

    python3 churn.py OLD.json.gz NEW.json.gz
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import math
import os
import re
import sys

import directives as D

MONEY = re.compile(r"[$£€¥]\s?\d|\b\d+(?:\.\d+)?\s?(?:USD|EUR|GBP|usd|eur|gbp)\b")
NUM = re.compile(r"\d+(?:\.\d+)?")
DISCLOSE = re.compile(r"telemetry|analytics|opt[- ]?out|privacy|we (?:do not |don't )?(?:store|log|retain)|data retention", re.I)


def index(path):
    """(host, name) -> (text, sib) for everything that served a list."""
    rows, nsrv = D.load(path)
    out = {}
    for host, name, text, sib in rows:
        out.setdefault((host, name), (text, sib))
    return out, nsrv


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h) * 100, min(1, c + h) * 100)


def mcnemar(b, c):
    """Exact two-sided binomial on the discordant pairs. b+c is often small and
    the chi-square version is wrong there; this one is never wrong."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--examples", type=int, default=6)
    ap.add_argument("--null", action="store_true")
    a = ap.parse_args()

    O, _ = index(a.old)
    N, _ = index(a.new)
    keys = set(O) & set(N)
    print(f"# {os.path.basename(a.old)} -> {os.path.basename(a.new)}")
    print(f"  joined (host, tool) pairs: {len(keys)}")
    print(f"  old-only {len(set(O)-set(N))}   new-only {len(set(N)-set(O))}"
          "   <- renames land here, not in the rate")

    changed = [k for k in keys if O[k][0] != N[k][0]]
    print(f"  descriptions changed: {len(changed)}  "
          f"({100*len(changed)/max(len(keys),1):.1f}%)")
    print()

    # ---- directive flag, paired ----
    both = neither = added = dropped = 0
    add_rows, drop_rows = [], []
    for k in changed:
        fo = D.fams(O[k][0], O[k][1])
        fn = D.fams(N[k][0], N[k][1])
        if fo and fn:
            both += 1
        elif not fo and not fn:
            neither += 1
        elif fn and not fo:
            added += 1
            add_rows.append((k, O[k][0], N[k][0], sorted(fn - fo)))
        else:
            dropped += 1
            drop_rows.append((k, O[k][0], N[k][0], sorted(fo - fn)))

    # THE SPLIT THAT DECIDES WHETHER ANY OF THIS MEANS ANYTHING.
    # Edits lengthen descriptions 5:1. A lexicon fires more often on more text,
    # so an add-direction among flips can be pure accretion. Splitting by
    # whether the edit grew or shrank the text separates the two, and on the
    # Sep 27 -> Oct 4 pair it is decisive in the direction I did not want:
    # longer edits add a directive 96% of the time, shorter edits add one 17%
    # of the time and DROP one in 10 of their 12 flips. The feature follows the
    # text. Report the split, never the pooled number alone.
    longer = [k for k in changed if len(N[k][0]) > len(O[k][0])]
    shorter = [k for k in changed if len(N[k][0]) <= len(O[k][0])]

    print("## among the CHANGED descriptions: did the directive flag flip?")
    print(f"  directive both before and after   {both}")
    print(f"  directive neither before nor after {neither}")
    print(f"  BECAME directive                  {added}")
    print(f"  STOPPED being directive           {dropped}")
    p = mcnemar(added, dropped)
    print(f"  McNemar exact, two-sided, on {added+dropped} discordant pairs: p = {p:.4f}")
    if added + dropped:
        lo, hi = wilson(added, added + dropped)
        print(f"  share of flips that ADD a directive: "
              f"{100*added/(added+dropped):.1f}% [{lo:.1f}, {hi:.1f}]")
    print()

    print("## the same flip count, split by whether the edit grew or shrank the text")
    for lab, sub in (("grew", longer), ("shrank or held", shorter)):
        aa = dd = 0
        for k in sub:
            fo = bool(D.fams(O[k][0], O[k][1]))
            fn = bool(D.fams(N[k][0], N[k][1]))
            if fn and not fo:
                aa += 1
            elif fo and not fn:
                dd += 1
        sh = f"{100*aa/(aa+dd):.1f}%" if aa + dd else "n/a"
        print(f"  {lab:<16} n={len(sub):4d}  added {aa:3d}  dropped {dd:3d}  "
              f"add-share {sh}  McNemar p={mcnemar(aa, dd):.4f}")
    print("  >>> if these two rows disagree, the flag is tracking LENGTH, not intent.")
    print()

    # ---- the base rate, for scale: directive share before and after, same units ----
    do = sum(1 for k in keys if D.fams(O[k][0], O[k][1]))
    dn = sum(1 for k in keys if D.fams(N[k][0], N[k][1]))
    print("## the same panel's overall directive share, before and after")
    print(f"  before {100*do/len(keys):.2f}%   after {100*dn/len(keys):.2f}%   "
          f"delta {100*(dn-do)/len(keys):+.2f} points over 7 days")
    print(f"  (net movement is {dn-do:+d} tools out of {len(keys)}; a flat panel can"
          " still be churning underneath, which is the whole point)")
    print()

    # ---- what KIND of edit ----
    kinds = collections.Counter()
    money_rows = []
    for k in changed:
        o, n = O[k][0], N[k][0]
        if MONEY.search(o) or MONEY.search(n):
            if set(NUM.findall(o)) != set(NUM.findall(n)):
                kinds["price or money figure changed"] += 1
                money_rows.append((k, o, n))
            else:
                kinds["money mentioned, figures unchanged"] += 1
        if DISCLOSE.search(n) and not DISCLOSE.search(o):
            kinds["privacy/telemetry disclosure ADDED"] += 1
        if DISCLOSE.search(o) and not DISCLOSE.search(n):
            kinds["privacy/telemetry disclosure REMOVED"] += 1
        if set(NUM.findall(o)) != set(NUM.findall(n)):
            kinds["any number changed"] += 1
        if len(n) > len(o) * 1.5:
            kinds["grew by >50%"] += 1
    print("## kinds of edit (categories overlap on purpose)")
    for k, v in kinds.most_common():
        print(f"  {v:5d}  {k}")
    print()

    def show(title, rows, lim):
        if not rows:
            return
        print(f"## {title} ({len(rows)}; first {min(lim,len(rows))})")
        for (h, nm), o, n, *rest in rows[:lim]:
            j = 0
            while j < min(len(o), len(n)) and o[j] == n[j]:
                j += 1
            extra = f"   +{rest[0]}" if rest and rest[0] else ""
            print(f"  --- {h} :: {nm}{extra}")
            print(f"      OLD ...{o[max(0,j-30):j]}>>>{o[j:j+140]}")
            print(f"      NEW ...{n[max(0,j-30):j]}>>>{n[j:j+140]}")
        print()

    # ---- the null the whole result lives or dies on ----
    # Fire 312: ANY regex selects long text, and 71% of the detector's apparent
    # token gap was reproducible with content-free documentation nouns. Edits
    # here LENGTHEN descriptions 5:1 (median +87 chars), so a lexicon that fires
    # more often after than before may be measuring nothing but length. The test
    # is the same one: prevalence-matched decoy lexicons, same 419 changed pairs,
    # same paired flip count. If decoys also add 85% of the time, this finding is
    # mechanical and must not be reported.
    if a.null:
        import random as _r
        import statistics
        WORDS = ["data","return","value","number","list","name","file","text","result",
                 "optional","default","format","object","field","string","id","date","type",
                 "page","key","api","json","response","request","query","input","output",
                 "parameter","code","url","time","user","search","get","set","item","record",
                 "status","table","column"]
        pairs = [(O[k][0], N[k][0]) for k in changed]
        allk = list(keys)
        hits_all = {w: [bool(re.search(r"\b" + w + r"\b", O[k][0], re.I)) for k in allk]
                    for w in WORDS}
        hitsO = {w: [bool(re.search(r"\b" + w + r"\b", o, re.I)) for o, _ in pairs]
                 for w in WORDS}
        hitsN = {w: [bool(re.search(r"\b" + w + r"\b", n, re.I)) for _, n in pairs]
                 for w in WORDS}
        target = 100 * do / len(allk)      # the detector's own prevalence, old capture
        _r.seed(317)
        shares, adds, drops = [], [], []
        for _ in range(400):
            sel = []
            cov = [False] * len(allk)
            for w in _r.sample(WORDS, len(WORDS)):
                cand = [x or y for x, y in zip(cov, hits_all[w])]
                if 100 * sum(cand) / len(allk) > target + 1.5:
                    continue
                cov = cand
                sel.append(w)
                if 100 * sum(cov) / len(allk) >= target - 1.5:
                    break
            if abs(100 * sum(cov) / len(allk) - target) > 1.5 or not sel:
                continue
            fo = [any(hitsO[w][i] for w in sel) for i in range(len(pairs))]
            fn = [any(hitsN[w][i] for w in sel) for i in range(len(pairs))]
            ad = sum(1 for x, y in zip(fo, fn) if y and not x)
            dr = sum(1 for x, y in zip(fo, fn) if x and not y)
            if ad + dr == 0:
                continue
            shares.append(100 * ad / (ad + dr))
            adds.append(ad); drops.append(dr)
        print(f"## NULL: {len(shares)} prevalence-matched content-free lexicons "
              f"(target {target:.1f}% of all {len(allk)} tools)")
        if shares:
            m, s = statistics.mean(shares), statistics.stdev(shares)
            real = 100 * added / max(added + dropped, 1)
            print(f"  decoy add-share: mean {m:.1f}%  sd {s:.1f}  "
                  f"range [{min(shares):.0f}, {max(shares):.0f}]")
            print(f"  decoy discordant pairs: median added {statistics.median(adds):.0f}, "
                  f"dropped {statistics.median(drops):.0f}")
            print(f"  the detector: {real:.1f}%  -> {(real-m)/s:+.1f} sd out")
            print(f"  >>> {m/real*100:.0f}% of the add-direction is reproducible with "
                  "words that mean nothing.")
        print()

    show("edits that ADDED a directive", add_rows, a.examples)
    show("edits that REMOVED a directive", drop_rows, a.examples)
    show("edits that changed a money figure", money_rows, a.examples)
    return 0


if __name__ == "__main__":
    sys.exit(main())
