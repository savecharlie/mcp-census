#!/usr/bin/env python3
"""persuasion.py -- how much of the MCP registry already talks like an attack.

WHY. arXiv:2609.26761 (A2M, AACL-IJCNLP 2026, submitted 22 Sep 2026, read fire
303) hijacks MCP agents in two phases. Phase I, "Attraction", optimises a tool's
NAME AND DESCRIPTION to maximise the probability an agent selects it, using five
named persuasion strategies: **Authority, Urgency, Comprehensiveness, Resource
Optimality, Security**. It reports a 93.6% malicious-invocation rate on
LiveMCPBench and 74.4% mean attack success, transferring to four other models
without re-optimisation. The paper's own closing line asks for "stronger tool
vetting".

The obvious vetting idea is to flag listings whose metadata reads persuasive.
This script exists to check whether that idea can possibly work, BEFORE anyone
builds it, by measuring how common that vocabulary already is among 36,550 real
listings nobody is accusing of anything.

WHAT IT IS. A transparent keyword lexicon per A2M category, applied to the
registry's own `description` field. The lexicon is in this file, unweighted and
auditable, because a black-box score would make the result unfalsifiable.

WHAT IT IS NOT, and this is the whole point: **a high score is not evidence of
malice and must never be reported as one.** "Official", "secure", "complete",
"fast", "real-time" are how honest software describes itself. If the measurement
comes back saying most of the registry scores, the correct conclusion is that
persuasion vocabulary CANNOT separate attacker from vendor -- a negative result
about the defence, not an accusation against anybody. The direction of error is
stated here so the number cannot be quoted the other way round.

LIMIT OF THE POPULATION. The registry publishes a SERVER description. A2M
optimises TOOL name and description, which live in the server's own `tools/list`
response and are not in the registry at all. So this measures the surface a
census can see, and the surface that matters most is one probe deeper. Said out
loud rather than smoothed over.

    python3 persuasion.py [registry_YYYYMMDD.json.gz] [--examples 3]
"""
from __future__ import annotations

import argparse
import collections
import glob
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# A2M's five strategies. Terms chosen as the plain-language markers of each
# strategy, not as a trained classifier. Word-boundary matched, case-folded.
LEX = {
    "authority": r"official|authoritative|certified|verified|trusted|canonical|"
                 r"enterprise[- ]grade|industry[- ]standard|endorsed|recommended",
    "urgency": r"real[- ]?time|instant(ly)?|immediate(ly)?|live|up[- ]to[- ]the[- ]minute|"
               r"latest|now|urgent|without delay|as it happens",
    "comprehensiveness": r"comprehensive|complete|all[- ]in[- ]one|full(y)? (support|coverage)|"
                         r"everything|any\b|exhaustive|end[- ]to[- ]end|unified|one[- ]stop",
    "resource_optimality": r"fast(est)?|efficient|low[- ]latency|cheap(est)?|free|optimi[sz]ed|"
                           r"lightweight|minimal|zero[- ]config|no setup|token[- ]efficient",
    "security": r"secure(ly)?|safe(ly)?|privacy|private|encrypted|read[- ]only|sandbox(ed)?|"
                r"compliant|audited|no data (is )?(stored|retained)",
}
# WORD BOUNDARIES ARE LOAD-BEARING. The first run compiled these bare and
# `now` matched inside "k-NOW-ledge", `live` inside "de-LIVE-ry", `free` inside
# "FREE-dom", `safe` inside "un-SAFE". Every one inflates the count in the
# direction that makes the finding louder, which is exactly the direction I am
# least able to notice. 25.6% became 21.4% once the boundaries went on (and "any category" fell by 1,543
# listings), so the bug was worth about a fifth of the headline.
RX = {k: re.compile(r"\b(?:" + v + r")\b", re.I) for k, v in LEX.items()}


def newest() -> str:
    c = sorted(p for p in glob.glob(os.path.join(HERE, "registry_2*.json.gz"))
               if "allver" not in p)
    if not c:
        sys.exit("no snapshot; run pull_registry.py")
    return c[-1]


def score(text: str):
    return {k for k, r in RX.items() if r.search(text or "")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", nargs="?", default=None)
    ap.add_argument("--examples", type=int, default=2)
    a = ap.parse_args()
    path = a.snapshot or newest()
    rows = json.load(gzip.open(path, "rt"))
    print(f"# {os.path.basename(path)}   {len(rows):,} listings")
    print("# lexicon: A2M's five persuasion strategies (arXiv:2609.26761 §4.2)")

    hits = collections.Counter()
    ncat = collections.Counter()
    # two classes of publisher, because the registry verifies them differently:
    # a namespace under io.github.* proves control of a GitHub account; any other
    # namespace proves control of a DNS name.
    cls_tot, cls_hit = collections.Counter(), collections.Counter()
    ex = collections.defaultdict(list)
    for r in rows:
        s = r.get("server") or {}
        d = s.get("description") or ""
        name = s.get("name", "")
        cls = "github-account" if name.startswith("io.github.") else "dns-verified"
        cls_tot[cls] += 1
        got = score(d)
        ncat[len(got)] += 1
        if got:
            cls_hit[cls] += 1
        for k in got:
            hits[k] += 1
            if len(ex[k]) < a.examples:
                ex[k].append((name, d[:110]))

    n = len(rows)
    print("\nPREVALENCE -- listings whose own description uses the vocabulary")
    for k in LEX:
        print(f"  {k:<20} {hits[k]:>6,}  {hits[k]/n*100:5.1f}%")
    print()
    for i in sorted(ncat):
        print(f"  touches {i} of 5 categories: {ncat[i]:>6,}  {ncat[i]/n*100:5.1f}%")
    any_hit = n - ncat[0]
    print(f"  -> ANY category: {any_hit:,} of {n:,} ({any_hit/n*100:.1f}%)")

    print("\nBY HOW THE PUBLISHER WAS VERIFIED")
    for c in cls_tot:
        print(f"  {c:<16} {cls_hit[c]:>6,} of {cls_tot[c]:>6,} "
              f"({cls_hit[c]/max(cls_tot[c],1)*100:5.1f}%)")

    print("\nEXAMPLES (these are ordinary listings; the point is that they score)")
    for k in LEX:
        for nm, d in ex[k]:
            print(f"  [{k}] {nm}\n      {d}")

    print("\nREAD THIS BEFORE QUOTING ANY NUMBER ABOVE: a hit means a description")
    print("uses the same vocabulary A2M's Attraction phase optimises toward. It is")
    print("NOT a finding about any listed server. The interesting direction is the")
    print("opposite one -- if the honest majority already scores, then persuasive")
    print("metadata cannot be a vetting signal, and vetting has to look at")
    print("BEHAVIOUR instead of at copy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
