#!/usr/bin/env python3
"""housestyle.py -- fire 311. The paired test that kills collision.py's hypothesis,
and the measurement that replaces it.

collision.py asked whether a contested tool name makes a description more directive.
Tool-instance level said +2.7 points, z=2.15. That z is wrong: 12,829 tools come from
1,035 servers and tools on one server are written by one author, so they are not
independent draws. Two checks, both free:

  - PAIRED WITHIN SERVER. Only servers holding BOTH a contested and a sole tool can
    speak, and each speaks once. House style cancels exactly.
  - OVERDISPERSION. If directiveness were a property of the TOOL, per-server rates
    would scatter binomially around the pooled rate. If it is a property of the
    AUTHOR, they pile at 0 and 1.

The second is the real finding and it was not the question I came in with.
"""
import collections, math, os, random, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import directives as D, collision as C

CAP = os.path.join(HERE, "tools_20260927_union.json.gz")
THR = 0.55

tools, nhosts = D.load(CAP)
byname = collections.defaultdict(list)
for h, nm, t, s in tools:
    byname[nm].append((h, t, s))
nclust = {}
for nm, v in byname.items():
    nclust[nm] = 1 if len({h for h, _, _ in v}) <= 1 else len(C.cluster([t for _, t, _ in v], THR))

per = collections.defaultdict(list)     # host -> [(contested?, directive?)]
for h, nm, t, s in tools:
    per[h].append((nclust[nm] >= 2, bool(D.fams(t, s))))

pooled_k = sum(1 for v in per.values() for _, d in v if d)
pooled_n = sum(len(v) for v in per.values())
p0 = pooled_k / pooled_n
print("pooled: %d/%d = %.1f%% of tool descriptions flagged directive" % (pooled_k, pooled_n, 100 * p0))

# ---------- 1. paired within server --------------------------------------------
print("\n== 1. PAIRED WITHIN SERVER (the correct test of the contest hypothesis) ==")
diffs = []
for h, v in per.items():
    con = [d for c, d in v if c]
    sol = [d for c, d in v if not c]
    if len(con) >= 1 and len(sol) >= 1:
        diffs.append(sum(con) / len(con) - sum(sol) / len(sol))
n = len(diffs); m = st.mean(diffs); sd = st.stdev(diffs)
se = sd / math.sqrt(n); t = m / se
print("  servers holding both kinds: %d" % n)
print("  mean within-server (contested - sole) = %+.4f  [%.4f, %.4f] 95%%"
      % (m, m - 1.96 * se, m + 1.96 * se))
print("  t = %+.2f   (in points: %+.1f)" % (t, 100 * m))
pos = sum(1 for x in diffs if x > 0); neg = sum(1 for x in diffs if x < 0)
print("  sign test: %d servers more directive on contested, %d less, %d tied"
      % (pos, neg, n - pos - neg))
# exact-ish two-sided binomial on the sign test
k, nn = min(pos, neg), pos + neg
pv = 2 * sum(math.comb(nn, i) for i in range(k + 1)) / 2 ** nn
print("  two-sided sign-test p = %.3f" % min(1.0, pv))

# ---------- 2. overdispersion ---------------------------------------------------
print("\n== 2. IS DIRECTIVENESS A PROPERTY OF THE TOOL OR OF THE AUTHOR? ==")
MIN = 5
srv = [(sum(d for _, d in v), len(v)) for v in per.values() if len(v) >= MIN]
print("  servers with >=%d tools: %d  (%d tools)" % (MIN, len(srv), sum(n for _, n in srv)))
rates = [k / n for k, n in srv]
allzero = sum(1 for k, n in srv if k == 0)
allone = sum(1 for k, n in srv if k == n)
print("  all tools directive : %d servers (%.1f%%)" % (allone, 100 * allone / len(srv)))
print("  no tool directive   : %d servers (%.1f%%)" % (allzero, 100 * allzero / len(srv)))
print("  ...so %.1f%% of servers are at one extreme or the other"
      % (100 * (allzero + allone) / len(srv)))

# binomial null: same tool counts, each tool an independent coin at p0
rnd = random.Random(311)
B = 2000
z0 = c0 = c1 = 0
null_ext = []
for _ in range(B):
    a0 = a1 = 0
    for _, n in srv:
        k = sum(1 for _ in range(n) if rnd.random() < p0)
        if k == 0: a0 += 1
        if k == n: a1 += 1
    null_ext.append((a0 + a1) / len(srv))
print("  binomial null (p=%.3f, same tool counts, %d draws): extremes %.1f%% [%.1f, %.1f]"
      % (p0, B, 100 * st.mean(null_ext),
         100 * sorted(null_ext)[int(.025 * B)], 100 * sorted(null_ext)[int(.975 * B)]))

# Pearson chi2 dispersion + intraclass correlation (ANOVA estimator)
chi2 = sum((k - n * p0) ** 2 / (n * p0 * (1 - p0)) for k, n in srv)
df = len(srv)
print("  dispersion chi2/df = %.2f on %d servers  (1.0 = tool-level coin)" % (chi2 / df, df))
# ICC for binary data, Fleiss-style
N = sum(n for _, n in srv)
nbar = N / len(srv)
msb = sum(n * (k / n - p0) ** 2 for k, n in srv) / (len(srv) - 1)
msw = sum(k * (1 - k / n) for k, n in srv) / (N - len(srv))
icc = (msb - msw) / (msb + (nbar - 1) * msw)
print("  intraclass correlation (author explains): ICC = %.3f" % icc)

# histogram
print("\n  per-server directive rate, %d servers with >=%d tools:" % (len(srv), MIN))
H = [0] * 11
for r in rates: H[min(10, int(r * 10 + 1e-9))] += 1
for i, c in enumerate(H):
    lab = "%3d%%" % (i * 10) if i < 10 else "100%"
    print("    %s %-4s %s" % (lab, c, "#" * max(0, round(60 * c / max(H))) ))

# ---------- 3. do the extremes survive the detector's MEASURED error rates? ------
print("\n== 3. THE EXTREMES AGAINST THE DETECTOR'S OWN MEASURED ERRORS ==")
PREC, FLOOR = 0.975, 0.275     # fire 310 hand samples: 39/40 precision, 11/40 missed
print("  measured: precision %.1f%%, floor (miss rate) %.1f%%" % (100 * PREC, 100 * FLOOR))
z0b = [(k, n) for k, n in srv if k == 0]
z1b = [(k, n) for k, n in srv if k == n]
# a truly all-directive server is seen as 0 only if EVERY tool is missed
exp_false_zero = sum(FLOOR ** n for _, n in z0b)
exp_false_one  = sum(PREC ** 0 * 0 for _, n in z1b)  # placeholder, computed below
# a truly all-non-directive server is seen as all-flagged only if every tool is a FP.
# FP rate per flagged tool = 1-PREC; but we need P(flag | not directive). Bound it:
# flagged = 4717, false among them = (1-PREC)*4717 = 118 over 12829-?; use the rate
fp_rate = (1 - PREC) * pooled_k / (pooled_n - pooled_k)   # false flags / true negatives
print("  implied P(flag | NOT directive) = %.4f" % fp_rate)
exp_false_one = sum(fp_rate ** n for _, n in z1b)
print("  servers seen at 0%%: %d   expected to be FALSE zeros (all tools missed): %.2f"
      % (len(z0b), exp_false_zero))
print("  servers seen at 100%%: %d  expected to be FALSE ones (all tools false-flagged): %.5f"
      % (len(z1b), exp_false_one))
print("  -> the extremes are not a detector artifact. A 5-tool all-directive server")
print("     is missed entirely with probability %.4f (0.275^5)." % 0.275 ** 5)

# ---------- 4. are the extreme servers distinct AUTHORS or one fleet? -----------
print("\n== 4. CONFOUND: are extreme servers distinct authors, or cloned fleets? ==")
import gzip, json
d = json.load(gzip.open(CAP, "rt"))
fp = {}
for r in d["rows"]:
    if r.get("tools"):
        fp[r["host"]] = frozenset(t["desc_sha"] for t in r["tools"])
def distinct(hosts):
    return len({fp[h] for h in hosts if h in fp})
hostsrv = {h: (sum(x for _, x in [(0, dd) for _, dd in v]), len(v)) for h, v in per.items()}
h0 = [h for h, v in per.items() if len(v) >= MIN and sum(dd for _, dd in v) == 0]
h1 = [h for h, v in per.items() if len(v) >= MIN and sum(dd for _, dd in v) == len(v)]
print("  0%% servers : %d hosts -> %d distinct tool-description fingerprints" % (len(h0), distinct(h0)))
print("  100%% servers: %d hosts -> %d distinct tool-description fingerprints" % (len(h1), distinct(h1)))
allh = [h for h, v in per.items() if len(v) >= MIN]
print("  all >=%d-tool servers: %d hosts -> %d distinct fingerprints" % (MIN, len(allh), distinct(allh)))
# recompute the extremes rate on DEDUPLICATED servers
seen = set(); dsrv = []
for h, v in per.items():
    if len(v) < MIN: continue
    f = fp.get(h)
    if f in seen: continue
    seen.add(f); dsrv.append((sum(dd for _, dd in v), len(v)))
a0 = sum(1 for k, n in dsrv if k == 0); a1 = sum(1 for k, n in dsrv if k == n)
print("  DEDUPLICATED: %d distinct servers, extremes %d+%d = %.1f%%"
      % (len(dsrv), a0, a1, 100 * (a0 + a1) / len(dsrv)))
k2 = sum(k for k, _ in dsrv); n2 = sum(n for _, n in dsrv); p2 = k2 / n2
chi2b = sum((k - n * p2) ** 2 / (n * p2 * (1 - p2)) for k, n in dsrv)
print("  DEDUPLICATED: pooled %.1f%%, dispersion chi2/df = %.2f" % (100 * p2, chi2b / len(dsrv)))
N2 = n2; nb2 = N2 / len(dsrv)
msb2 = sum(n * (k / n - p2) ** 2 for k, n in dsrv) / (len(dsrv) - 1)
msw2 = sum(k * (1 - k / n) for k, n in dsrv) / (N2 - len(dsrv))
print("  DEDUPLICATED: ICC = %.3f" % ((msb2 - msw2) / (msb2 + (nb2 - 1) * msw2)))
