#!/usr/bin/env python3
"""contextcost.py -- what connecting an MCP server costs an agent's context window.

Fire 312. Every measurement in this folder so far is a RATE PER TOOL: 9.6% of tool
descriptions match the lexicon, ~41% actually direct the agent, 39.9% of servers carry
at least one. Fire 311 found that the per-tool unit was wrong for CONFIDENCE (twelve
descriptions by one author are not twelve opinions). This asks the other half of the
same question: the per-tool unit is also wrong for WEIGHT.

An agent does not pay per tool. It pays per token. A tool declaration enters the
context window before the agent does anything, and it stays there. So the quantity
that decides whether directive text actually reaches a model is not "what fraction of
tools contain an instruction" -- it is "what fraction of the TOKENS I am made to read
are instruction". Those two numbers are the same only if directive descriptions are
the same length as the rest, and there is no reason to assume that.

WHAT THIS CANNOT SEE, stated before any number:
  * `tools.py` stored only a sha256 of each inputSchema, so the schema half of the
    bill is INVISIBLE here. Every token figure below is a FLOOR on the real cost.
    (Fixed for the Oct 4 recapture -- tools.py now records schema token counts.)
  * `tools.py` truncates descriptions at 2000 chars. The length distribution is
    right-censored; the script reports how many rows sit on the cap.
  * There is no public Claude tokenizer and the API key has no credit, so the unit is
    `o200k_base`. The script measures how much the answer moves under a different
    tokenizer, so the unit's own slop is on the record rather than assumed away.

    python3 contextcost.py [capture.json.gz]
"""
from __future__ import annotations
import collections, gzip, json, math, os, statistics, sys

import tiktoken
from directives import load, fams, wilson

HERE = os.path.dirname(os.path.abspath(__file__))
O200K = tiktoken.get_encoding("o200k_base")
CL100K = tiktoken.get_encoding("cl100k_base")
CAP = 2000  # tools.py's truncation


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{100*k/n:.1f}% [{lo:.1f}, {hi:.1f}]"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "tools_20260927_union.json.gz")
    rowsd = json.load(gzip.open(path, "rt"))["rows"]
    tools, n_servers = load(path)
    print(f"capture {os.path.basename(path)}")
    print(f"{len(tools)} tools on {n_servers} live servers\n")

    # ---------------------------------------------------------------- gate 1
    print("=" * 72)
    print("GATE 1 -- does the tokenizer round-trip this corpus?")
    bad = 0
    for _, name, desc, _ in tools:
        s = name + "\n" + desc
        if O200K.decode(O200K.encode(s)) != s:
            bad += 1
    print(f"  descriptions that do not survive encode->decode: {bad}")
    if bad:
        print("  STOP. mojibake or a tokenizer bug; every count below is suspect.")
        return

    # ---------------------------------------------------------------- gate 2
    print("\nGATE 2 -- is the length distribution censored by tools.py's 2000-char cap?")
    at_cap = sum(1 for _, _, d, _ in tools if len(d) >= CAP)
    near = sum(1 for _, _, d, _ in tools if 1500 <= len(d) < CAP)
    print(f"  descriptions at/over the cap: {at_cap} ({100*at_cap/len(tools):.2f}%)")
    print(f"  descriptions 1500-1999 chars: {near}")
    print("  -> the right tail is censored; the mean is a LOWER bound by that much.")

    # ---------------------------------------------------------------- gate 3
    print("\nGATE 3 -- how much does the ANSWER move if the unit moves?")
    blob_o = sum(len(O200K.encode(n + "\n" + d)) for _, n, d, _ in tools)
    blob_c = sum(len(CL100K.encode(n + "\n" + d)) for _, n, d, _ in tools)
    chars = sum(len(n) + 1 + len(d) for _, n, d, _ in tools)
    print(f"  o200k_base total : {blob_o:,}")
    print(f"  cl100k_base total: {blob_c:,}  ({100*(blob_c-blob_o)/blob_o:+.1f}%)")
    print(f"  chars/4 heuristic: {chars//4:,}  ({100*(chars/4-blob_o)/blob_o:+.1f}%)")
    print("  -> the tokenizer choice is worth a few points. The heuristic is worse,")
    print("     and in the direction that would have flattered the finding.")

    # ---------------------------------------------------------------- the bill
    print("\n" + "=" * 72)
    print("THE DESCRIPTION BILL (floor: name + description, no schemas)\n")
    per_server = collections.defaultdict(int)
    per_server_n = collections.Counter()
    tok = {}
    for host, name, desc, sib in tools:
        t = len(O200K.encode(name + "\n" + desc))
        tok[(host, name)] = t
        per_server[host] += t
        per_server_n[host] += 1
    vals = sorted(per_server.values())
    q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
    print(f"  servers measured         {len(vals)}")
    print(f"  total description tokens {sum(vals):,}")
    print(f"  median server            {statistics.median(vals):,.0f} tokens"
          f"  ({statistics.median(per_server_n.values()):.0f} tools)")
    print(f"  mean server              {statistics.mean(vals):,.0f} tokens")
    for p in (0.25, 0.75, 0.90, 0.99):
        print(f"  p{int(p*100):<2d}                      {q(p):,} tokens")
    print(f"  max                      {max(vals):,} tokens"
          f"  ({max(per_server.items(), key=lambda kv: kv[1])[0]})")
    # how many servers cost more than a page of code
    for thresh in (1000, 5000, 10000, 25000):
        k = sum(1 for v in vals if v >= thresh)
        print(f"  servers >= {thresh:6,} tokens: {k:4d}  ({100*k/len(vals):.1f}%)")

    # ---------------------------------------------------------------- collision
    print("\n" + "=" * 72)
    print("THE COLLISION -- is directive text LONGER than the rest?\n")
    dlen, nlen, dtok, ntok = [], [], 0, 0
    per_server_d = collections.defaultdict(int)
    for host, name, desc, sib in tools:
        t = tok[(host, name)]
        if fams(desc, sib):
            dlen.append(t); dtok += t; per_server_d[host] += t
        else:
            nlen.append(t); ntok += t
    print(f"  directive tools      {len(dlen):5d}  median {statistics.median(dlen):6.0f} tok"
          f"  mean {statistics.mean(dlen):6.1f}")
    print(f"  non-directive tools  {len(nlen):5d}  median {statistics.median(nlen):6.0f} tok"
          f"  mean {statistics.mean(nlen):6.1f}")
    ratio = statistics.mean(dlen) / statistics.mean(nlen)
    print(f"  mean length ratio    {ratio:.2f}x")

    # Mann-Whitney U, normal approximation -- lengths are nowhere near normal
    allv = sorted([(v, 1) for v in dlen] + [(v, 0) for v in nlen])
    ranks, i = {}, 0
    rsum = 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + j + 1) / 2.0            # average rank for ties, 1-indexed
        for k in range(i, j):
            if allv[k][1] == 1:
                rsum += r
        i = j
    n1, n2 = len(dlen), len(nlen)
    u = rsum - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    print(f"  Mann-Whitney z       {(u-mu)/sd:+.1f}   (U={u:,.0f})")

    print("\n  the two rates, same corpus:")
    print(f"    per TOOL   {pct(len(dlen), len(tools))}")
    print(f"    per TOKEN  {100*dtok/(dtok+ntok):.1f}%")
    print(f"    difference {100*dtok/(dtok+ntok) - 100*len(dlen)/len(tools):+.1f} points")
    print("""
    *** DO NOT READ THAT GAP AS A FINDING. 71% of it is MECHANICAL. ***
    A prevalence-matched word list of content-free documentation nouns
    ("data", "value", "optional", "page"...) reproduces +12.0 of the +17.1
    points, because ANY regex selects long text: a longer description has
    more places for a word to occur. Measured in `tokenweight.py --null`,
    400 matched null lexicons, sd 1.9. The real detector is only +2.7 sd out.
    The effect is nonetheless REAL -- but only the hand labels can see it:
    inside the stratum where this detector fires on nothing, descriptions
    that genuinely direct the agent still run 1.72x longer (Mann-Whitney
    z = +2.93, n = 161). The token-weighted TRUTH is 77.3% [62.9, 87.0]
    and comes from `tokenweight.py`, not from this line.""")

    # cluster-correct: the per-server token-weighted rate, each server one vote
    srv = []
    for host, total in per_server.items():
        if total:
            srv.append(100 * per_server_d.get(host, 0) / total)
    print(f"\n  per-server token-weighted rate (one vote per server, n={len(srv)}):")
    print(f"    median {statistics.median(srv):.1f}%   mean {statistics.mean(srv):.1f}%"
          f"   servers at 0%: {sum(1 for v in srv if v == 0)}"
          f"   at 100%: {sum(1 for v in srv if v >= 99.999)}")
    print("    (fire 311: do NOT quote a tool-level CI on this corpus -- cluster or")
    print("     report the server-level number. This line is the server-level number.)")

    # ---------------------------------------------------------------- tail
    print("\n" + "=" * 72)
    print("WHO SPENDS THE MOST OF AN AGENT'S WINDOW\n")
    top = sorted(per_server.items(), key=lambda kv: -kv[1])[:12]
    for host, t in top:
        d = per_server_d.get(host, 0)
        print(f"  {t:7,} tok  {per_server_n[host]:4d} tools  "
              f"{100*d/t:5.1f}% directive  {host[:52]}")


if __name__ == "__main__":
    main()
