#!/usr/bin/env python3
"""lengthtruth.py -- does a description that REALLY directs the agent run longer?

Fire 312. This is the instrument that decides whether the token-weighted directive
rate is a finding or an artifact, and it is the only one that can, because every
word-list answer to this question is contaminated: a regex selects long text by
construction, and a prevalence-matched list of content-free documentation nouns
reproduces 71% of the detector's apparent effect (`tokenweight.py --null`).

So ask the hand labels instead. Pool every labelled row in this folder that can be
joined back to the capture, attach its o200k token length, and split by the HUMAN
verdict -- in particular inside the stratum where the detector fires on NOTHING, where
the lexicon contributes nothing to the selection and cannot inflate the answer.

Mann-Whitney U with tie-corrected mid-ranks and a normal approximation; lengths are
nowhere near normal, so a t-test would be the wrong instrument.

    python3 lengthtruth.py
"""
from __future__ import annotations
import glob, json, math, os, statistics
import tiktoken
from directives import load, fams

HERE = os.path.dirname(os.path.abspath(__file__))
E = tiktoken.get_encoding("o200k_base")


def mw(a, b):
    """U and z for group a vs b, mid-ranks for ties."""
    allv = sorted([(v, 1) for v in a] + [(v, 0) for v in b])
    rs, i = 0.0, 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        r = (i + j + 1) / 2.0
        rs += r * sum(1 for k in range(i, j) if allv[k][1] == 1)
        i = j
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return 0.0, 0.0
    u = rs - n1 * (n1 + 1) / 2
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    return u, (u - n1 * n2 / 2) / sd


def main():
    tools, _ = load(os.path.join(HERE, "tools_20260927_union.json.gz"))
    idx = {(h, n): (d, s) for h, n, d, s in tools}
    rows, unjoined = [], {}
    for f in sorted(glob.glob(os.path.join(HERE, "labels_*.jsonl"))):
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "verdict" not in r:
                continue
            key = (r.get("host"), r.get("tool"))
            if key not in idx:
                unjoined[os.path.basename(f)] = unjoined.get(os.path.basename(f), 0) + 1
                continue
            d, s = idx[key]
            rows.append({"stratum": r.get("stratum", "?"),
                         "true": r["verdict"] == "true_positive",
                         "tok": len(E.encode((key[1] or "") + "\n" + d)),
                         "det": bool(fams(d, s)), "host": key[0]})
    print(f"labelled rows joined: {len(rows)}")
    if unjoined:
        print(f"UNJOINABLE (no host/tool recorded): {unjoined}")
        print("  -> a label file without (host, tool) is unusable by any later")
        print("     analysis. See the DON'T in CAIRN.md.\n")

    def rep(label, sub):
        t = [r["tok"] for r in sub if r["true"]]
        f = [r["tok"] for r in sub if not r["true"]]
        if not t or not f:
            print(f"  {label}  n={len(sub):3d}  -- one side empty, no test")
            return
        _, z = mw(t, f)
        print(f"  {label}  n={len(sub):3d}  "
              f"TRUE {len(t):3d}: med {statistics.median(t):4.0f} mean {statistics.mean(t):6.1f}  | "
              f"FALSE {len(f):3d}: med {statistics.median(f):4.0f} mean {statistics.mean(f):6.1f}  | "
              f"{statistics.mean(t)/statistics.mean(f):.2f}x  z={z:+.2f}")

    print("THE TEST -- token length of descriptions that a human judged DIRECTIVE")
    rep("all labelled rows        ", rows)
    rep("DETECTOR SAYS NO  <- key ", [r for r in rows if not r["det"]])
    rep("detector says yes        ", [r for r in rows if r["det"]])
    print("\nby stratum:")
    for st in sorted({r["stratum"] for r in rows}):
        rep(f"{st:26s}", [r for r in rows if r["stratum"] == st])
    neg = [r for r in rows if not r["det"]]
    print(f"\n  clustering: the key stratum is {len(neg)} rows on "
          f"{len({r['host'] for r in neg})} distinct hosts, so the fire-311 "
          f"pseudoreplication\n  correction is small here -- but it is not zero, and the "
          f"z above is uncorrected.")


if __name__ == "__main__":
    main()
