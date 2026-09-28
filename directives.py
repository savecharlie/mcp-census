#!/usr/bin/env python3
"""directives.py -- imperatives.py's recall problem, repaired and then re-floored.

Fire 305. The control (labels_control_20260928.jsonl) found that 38.3% of tools
matching NO imperatives.py family nonetheless direct the agent, so the published
9.6% was an undercount of about 4x. Five causes were named from labelled rows. This
is the repair, plus the thing the repair is worthless without: a FRESH floor, drawn
from what THIS detector misses, hand-read after it existed.

The five gaps and what each became:

  1. "use when" / "use this to" / "use only when" -- the commonest directive form in
     the corpus and in no v1 family.                            -> USE_WHEN
  2. The registry is not in English. Polish, Korean and Spanish directives sat in the
     control sample.                                            -> NONLATIN + LATIN_IMP
  3. `routing` required the word "over", so "prefer get_card_balance if you only need
     the balance" missed.                                       -> folded into ROUTE
  4. Sibling routing ("use Y instead", "check Y first", "Flow: A -> B -> C") is the
     commonest routing form and was mostly unmatched.           -> SIBLING_NAMED
  5. `priority` is case-sensitive by design, so a lowercase prohibition is invisible.
                                                                -> PROHIBITION

SIBLING_NAMED is the one I would build again first, and it is not a word list at all:
a description that names ANOTHER TOOL ON THE SAME SERVER is almost always routing,
and a snake_case identifier is the same in every language. It is the only family here
that does not care what human language the description is written in.

NOT A SCORE OF MALICE. Same caveat as imperatives.py: the honest and the hostile use
of this channel are lexically identical, which is the finding, not a limitation.

    python3 directives.py [capture.json.gz] [--sample-missed 40] [--sample-new 25]
"""
from __future__ import annotations
import argparse, collections, gzip, json, math, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
from imperatives import RX as V1RX, newest

CALLV = r"(call|use|invoke|run|query|pass|ask|infer|assume|guess|fetch|reach|retry)"
FAM = {
  # 1. when/whether to call. "use when", "use this to", "use only when", "read this to"
  "use_when":   re.compile(r"\b(use\s+(this|it|these|as)?\s*(tool\s+)?(when|if|only\s+when|whenever|to\s+(?:\w+|\S)|for\s+(?:\w+|\S)|before|after)"
                           r"|call\s+(this|it)\s+(when|if|first|before|after)"
                           r"|read\s+this\s+to|reach\s+for\s+this\s+when"
                           r"|(best|ideal|intended)\s+entry\s*point)\b", re.I),
  # 3+4. routing between capabilities, WITHOUT requiring the word "over"
  "route":      re.compile(r"\b(prefer(red)?\s+\w|instead\s+of|rather\s+than\s+(using|calling)|"
                           r"in\s+place\s+of|supersedes|do\s+not\s+use|don't\s+use|avoid\s+using|"
                           r"not\s+via|only\s+available\s+here|no\s+other\s+tool)\b", re.I),
  # 5. prohibition/obligation aimed at the caller, case-INsensitive, proximity-gated
  "prohibition":re.compile(r"\b(never|do\s+not|don'?t|must\s+not|should\s+not|only|always|must)\b"
                           r"[^.;]{0,40}?\b" + CALLV + r"\b|\b" + CALLV +
                           r"\b[^.;]{0,30}?\b(never|do\s+not|don'?t|must\s+not|only\s+when)\b", re.I),
  # v1's sequencing, kept
  "sequencing": re.compile(r"\b(call\s+(this|it)\s+(first|before|after)|must\s+be\s+called\s+(first|before)|"
                           r"before\s+(calling|using)\s+any|always\s+call\s+.{0,20}first|"
                           r"typical\s+workflow|flow\s*:|then\s+(call|poll)\b)", re.I),
  # 2a. non-Latin polite imperatives / prohibitions: ko, ja, zh, ru
  "nonlatin":   re.compile(r"(사용하세요|하세요|마세요|호출|해야\s*합니다|"
                           r"してください|使用してください|呼び出|しないでください|"
                           r"请使用|请调用|不要|应使用|必须|"
                           r"используйте|вызовите|не\s+используйте)"),
  # 2b. Latin-script non-English imperatives: es, pt, pl, de, fr, it, nl, no
  "latin_imp":  re.compile(r"\b(usar\s+(este|el|la|lo)|utilice|utiliza|antes\s+de\s+llamar|no\s+invent|"
                           r"use\s+esta|utilizar|"
                           r"u[zż]yj|podaj|przeka[zż]uj|zapami[eę]taj|nie\s+musisz|"
                           r"verwenden\s+sie|rufen\s+sie|nicht\s+verwenden|"
                           r"utilisez|appelez|n'utilisez\s+pas|"
                           r"usa\s+questo|utilizzare|"
                           r"gebruik\s+deze|bruk\s+denne)\b", re.I),
}
V1_ONLY = {k: V1RX[k] for k in ("priority", "addresses_ai", "rival_named")}

SKIP_SELF = re.compile(r"[^a-z0-9_]")


def load(path):
    d = json.load(gzip.open(path, "rt"))
    rows = [r for r in d["rows"] if r.get("tools")]
    out = []
    for r in rows:
        names = {t.get("name", "") for t in r["tools"]}
            # a sibling name has to be long enough not to collide with English, and
        # CAMELCASE COUNTS. Requiring an underscore made every getPoolOHLCV-style
        # name invisible; floor row M14 was missed for exactly that reason.
        sib = {n for n in names
               if len(n) >= 7 and ("_" in n or re.search(r"[a-z][A-Z]", n))}
        for t in r["tools"]:
            me = t.get("name", "")
            text = t.get("desc") or ""
            others = sib - {me}
            hit_sib = None
            for n in others:
                if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", text):
                    hit_sib = n
                    break
            out.append((r["host"], me, text, hit_sib))
    return out, len(rows)


def fams(text, sib):
    f = {k for k, rx in FAM.items() if rx.search(text)}
    f |= {k for k, rx in V1_ONLY.items() if rx.search(text)}
    if sib:
        f.add("sibling_named")
    return f


def wilson(k, n, z=1.96):
    if not n: return (0.0, 0.0)
    p = k/n; d = 1+z*z/n; c = p+z*z/(2*n)
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d*100, (c+h)/d*100)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", nargs="?", default=None)
    ap.add_argument("--sample-missed", type=int, default=0)
    ap.add_argument("--sample-new", type=int, default=0)
    ap.add_argument("--seed", type=int, default=3051)
    a = ap.parse_args()
    path = a.capture or newest()
    tools, nsrv = load(path)
    n = len(tools)
    v2 = [(h, nm, tx, sb, fams(tx, sb)) for h, nm, tx, sb in tools]
    v1 = [bool({k for k, rx in V1RX.items() if rx.search(tx)}) for h, nm, tx, sb in tools]
    hit = [t for t in v2 if t[4]]
    print(f"# {os.path.basename(path)}  {nsrv:,} servers, {n:,} tools")
    print(f"  v1 (imperatives.py): {sum(v1):,}  ({sum(v1)/n*100:.2f}%)")
    print(f"  v2 (this):           {len(hit):,}  ({len(hit)/n*100:.2f}%)")
    newly = [t for t, o in zip(v2, v1) if t[4] and not o]
    print(f"  newly caught:        {len(newly):,}  ({len(newly)/n*100:.2f}%)")
    print("\n  family            fires   %tools    SOLE")
    allf = list(FAM) + ["sibling_named"] + list(V1_ONLY)
    for k in allf:
        fs = [t for t in hit if k in t[4]]
        sole = [t for t in fs if len(t[4]) == 1]
        print(f"  {k:<16} {len(fs):>6,} {len(fs)/n*100:>7.2f}% {len(sole):>7,}")
    srv = len({t[0] for t in hit})
    print(f"\n  servers with >=1: {srv:,} of {nsrv:,} ({srv/nsrv*100:.1f}%)")

    rng = random.Random(a.seed)
    if a.sample_missed:
        missed = [t for t in v2 if not t[4]]
        pick = missed[:]; rng.shuffle(pick)
        print(f"\n### THE NEW FLOOR: {len(missed):,} tools v2 misses. "
              f"Sampling {a.sample_missed}, seed {a.seed}.")
        for i, (h, nm, tx, sb, _) in enumerate(pick[:a.sample_missed], 1):
            print(f"\n--- M{i} :: {h} :: {nm}  [{len(tx)}]")
            print("    " + " ".join(tx.split())[:780])
    if a.sample_new:
        pick = newly[:]; rng.shuffle(pick)
        print(f"\n### NEWLY CAUGHT, precision check: sampling {a.sample_new}, seed {a.seed}.")
        for i, (h, nm, tx, sb, f) in enumerate(pick[:a.sample_new], 1):
            print(f"\n--- N{i} :: {h} :: {nm}  {sorted(f)}" + (f"  sib={sb}" if sb else ""))
            print("    " + " ".join(tx.split())[:780])
    return 0


if __name__ == "__main__":
    sys.exit(main())
