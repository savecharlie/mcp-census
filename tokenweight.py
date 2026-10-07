#!/usr/bin/env python3
"""tokenweight.py -- the two-stratum TOKEN-weighted directive rate.

Fire 312. Fire 310 produced the per-tool truth: of 12,829 tool descriptions,
53.2% [44.7, 62.5] speak to the agent rather than about the tool, from a precision
of 39/40 on what `directives.py` flags and a floor of 11/40 on what it misses.

That is a rate per TOOL. An agent pays per TOKEN. This computes the same two-stratum
estimate with tokens as the weight, which is the quantity that decides how much of a
context window is instruction aimed at the model.

WHY IT IS NOT JUST THE DETECTOR'S OWN TOKEN RATE. The detector reports 36.8% of tools
and 53.8% of tokens, a gap of +17.1 points -- and **71% of that gap is reproduced by a
content-free word list at matched prevalence** (`--null`): any regex selects long text,
because long text has more places for a word to be. So a lexicon cannot measure this.
The hand labels can, and they say the effect is real: inside the stratum where the
detector fires on NOTHING, descriptions that genuinely direct the agent still run
1.72x longer (Mann-Whitney z = +2.93, n = 161).

The precision sample is RECONSTRUCTED. `labels_precision_20260930.jsonl` recorded 39 of
its 40 rows with empty host/tool, which would have made it unusable here; it does record
its sampling procedure (`random.Random(310).shuffle(hits)[:40]`), so the sample is
regenerated and verified against the one row that does carry identifiers -- P18,
`trend @ api.kadec0.xyz` -- and against the recorded reasons. See DON'T in CAIRN.md.

    python3 tokenweight.py [--null] [--boot 20000]
"""
from __future__ import annotations
import argparse, json, math, os, random, statistics, sys
import tiktoken
from directives import load, fams

HERE = os.path.dirname(os.path.abspath(__file__))
E = tiktoken.get_encoding("o200k_base")
CAP = "tools_20260927_union.json.gz"


def toklen(name, desc):
    return len(E.encode((name or "") + "\n" + (desc or "")))


def build():
    tools, nsrv = load(os.path.join(HERE, CAP))
    flagged = [t for t in tools if fams(t[2], t[3])]
    missed = [t for t in tools if not fams(t[2], t[3])]

    # --- flagged sample, reconstructed from the recorded procedure
    s = flagged[:]
    random.Random(310).shuffle(s)
    psamp = s[:40]
    plabs = [json.loads(l) for l in open(os.path.join(HERE, "labels_precision_20260930.jsonl"))
             if l.strip() and "verdict" in json.loads(l)]
    assert len(plabs) == 40, len(plabs)
    # verify: the single row carrying identifiers must land where it was recorded
    chk = [r for r in plabs if r.get("host")]
    for r in chk:
        h, n, _, _ = psamp[r["n"] - 1]
        assert (h, n) == (r["host"], r["tool"]), f"reconstruction FAILED at P{r['n']}"
    prec = [(toklen(psamp[r["n"] - 1][1], psamp[r["n"] - 1][2]),
             r["verdict"] == "true_positive", psamp[r["n"] - 1][0]) for r in plabs]

    # --- missed sample, joined on (host, tool) as recorded
    idx = {(t[0], t[1]): t for t in missed}
    flo = []
    for l in open(os.path.join(HERE, "labels_floor_postfix_20260930.jsonl")):
        if not l.strip():
            continue
        r = json.loads(l)
        if "verdict" not in r:
            continue
        k = (r.get("host"), r.get("tool"))
        if k not in idx:
            continue
        t = idx[k]
        flo.append((toklen(t[1], t[2]), r["verdict"] == "true_positive", t[0]))
    return tools, nsrv, flagged, missed, prec, flo


def ratio(sample):
    tt = sum(t for t, v, _ in sample if v)
    al = sum(t for t, _, _ in sample)
    return tt / al if al else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=20000)
    ap.add_argument("--null", action="store_true")
    a = ap.parse_args()

    tools, nsrv, flagged, missed, prec, flo = build()
    Tf = sum(toklen(n, d) for _, n, d, _ in flagged)
    Tm = sum(toklen(n, d) for _, n, d, _ in missed)
    T = Tf + Tm
    print(f"{len(tools)} tools on {nsrv} servers  |  {T:,} description tokens (o200k_base)")
    print(f"  flagged by directives.py : {len(flagged):6,} tools  {Tf:9,} tok  "
          f"({100*Tf/T:.1f}% of tokens, {100*len(flagged)/len(tools):.1f}% of tools)")
    print(f"  missed                   : {len(missed):6,} tools  {Tm:9,} tok")
    print(f"\n  precision sample  n={len(prec)}  hosts={len({h for _,_,h in prec})}  "
          f"count {sum(1 for _,v,_ in prec if v)}/{len(prec)}  token-weighted {100*ratio(prec):.1f}%")
    print(f"  floor sample      n={len(flo)}   hosts={len({h for _,_,h in flo})}  "
          f"count {sum(1 for _,v,_ in flo if v)}/{len(flo)}  token-weighted {100*ratio(flo):.1f}%")

    pt = (sum(1 for _, v, _ in prec if v) / len(prec) * len(flagged)
          + sum(1 for _, v, _ in flo if v) / len(flo) * len(missed)) / len(tools)
    tw = (ratio(prec) * Tf + ratio(flo) * Tm) / T
    print(f"\n  per-TOOL  true rate (fire 310's quantity, recomputed) {100*pt:.1f}%")
    print(f"  per-TOKEN true rate                                   {100*tw:.1f}%")

    random.seed(312)
    bs = []
    for _ in range(a.boot):
        p = [prec[random.randrange(len(prec))] for _ in prec]
        f = [flo[random.randrange(len(flo))] for _ in flo]
        bs.append((ratio(p) * Tf + ratio(f) * Tm) / T)
    bs.sort()
    lo, hi = bs[int(.025 * len(bs))], bs[int(.975 * len(bs))]
    print(f"  bootstrap 95% (row resample within stratum, {a.boot:,} draws): "
          f"[{100*lo:.1f}, {100*hi:.1f}]")
    print(f"\n  >>> the detector's own token rate is {100*(sum(toklen(n,d) for _,n,d,_ in flagged))/T:.1f}%,"
          f" which UNDER-states the truth by x{tw/(Tf/T):.2f}")

    if a.null:
        import re
        WORDS = ["data","return","value","number","list","name","file","text","result",
                 "optional","default","format","object","field","string","id","date","type",
                 "page","key","api","json","response","request","query","input","output",
                 "parameter","code","url","time","user","search","get","set","item","record",
                 "status","table","column"]
        rec = [(d, toklen(n, d)) for _, n, d, _ in tools]
        N = len(rec); TOT = sum(r[1] for r in rec)
        hits = {w: [bool(re.search(r"\b"+w+r"\b", d, re.I)) for d, _ in rec] for w in WORDS}
        target = 100 * len(flagged) / N
        real_gap = 100*Tf/T - target
        random.seed(312); gaps = []
        for _ in range(400):
            sel = [False]*N
            for w in random.sample(WORDS, len(WORDS)):
                cand = [x or y for x, y in zip(sel, hits[w])]
                if 100*sum(cand)/N > target + 1.5:
                    continue
                sel = cand
                if 100*sum(sel)/N >= target - 1.5:
                    break
            p = 100*sum(sel)/N
            if abs(p - target) > 1.5:
                continue
            gaps.append(100*sum(t for (d, t), x in zip(rec, sel) if x)/TOT - p)
        print(f"\n  NULL: prevalence-matched content-free word lists, n={len(gaps)}")
        print(f"    mean gap {statistics.mean(gaps):+.1f} pts (sd {statistics.stdev(gaps):.1f}) "
              f"vs the detector's {real_gap:+.1f}")
        print(f"    -> {100*statistics.mean(gaps)/real_gap:.0f}% of the detector's token gap is "
              f"MECHANICAL. A lexicon cannot measure this quantity.")


if __name__ == "__main__":
    main()
