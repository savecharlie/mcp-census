#!/usr/bin/env python3
"""collision.py -- is a directive what a FLAT NAMESPACE under competition produces?

Fire 311. Every previous question of this corpus has been a LEVEL: what fraction of
tool descriptions direct the agent (53.2%, fire 310). This asks a mechanism instead.

MCP's premise is composability: an agent loads several servers at once. But the tool
names land in one flat list in the model's context, so two vendors who both call their
tool `search` are competing for a single slot, and the DESCRIPTION is the only thing
that can win it. If that is what is happening, directiveness is not sloppiness -- it is
what the namespace shape rewards -- and the prediction is directional and falsifiable:

    tools whose name is contested by another VENDOR are more directive
    than tools that hold their name alone.

THE RULER THAT LIED FIRST. desc_sha looked like the discriminator between a clone and
a contest. It is not: a fleet template interpolates its own brand, so `dataset_top`
appears with 28 distinct descriptions on 28 hosts that are all one operator -- "The
highest rows of the Depreo dataset", "...of the Kbasevo dataset". 585 of 627 shared
names came out "genuine" under desc_sha and that number is fiction.

So: cluster the descriptions of each shared name by token-set similarity and count
CLUSTERS, not hashes. Validated against four known answers before it is allowed to
report anything (--validate): dataset_top and enquiry_describe must collapse to one,
search and fetch must not collapse.

NOT A SCORE OF MALICE -- same caveat as directives.py. An honest vendor fighting for a
contested slot writes the same sentence as a hostile one. That is the finding.
"""
import argparse, collections, gzip, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import directives as D

WORD = re.compile(r"[a-z0-9]+")


def toks(s):
    return set(WORD.findall((s or "").lower()))


def jac(a, b):
    if not a or not b:
        return 1.0 if a == b else 0.0
    return len(a & b) / len(a | b)


def cluster(descs, thr):
    """single-linkage on token Jaccard. descs: list of strings. -> list of lists of idx"""
    n = len(descs)
    T = [toks(d) for d in descs]
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if jac(T[i], T[j]) >= thr:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    g = collections.defaultdict(list)
    for i in range(n):
        g[find(i)].append(i)
    return list(g.values())


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d * 100, (c + h) / d * 100)


def host_ns(registry):
    """host -> set of registry namespaces declaring a remote on it"""
    m = collections.defaultdict(set)
    for row in json.load(gzip.open(registry, "rt")):
        s = row.get("server", {})
        ns = (s.get("name") or "").split("/")[0]
        for r in s.get("remotes", []) or []:
            u = r.get("url") or ""
            mm = re.match(r"https?://([^/:]+)", u)
            if mm and ns:
                m[mm.group(1).lower()].add(ns)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", nargs="?",
                    default=os.path.join(HERE, "tools_20260927_union.json.gz"))
    ap.add_argument("--registry", default=os.path.join(HERE, "registry_20260927.json.gz"))
    ap.add_argument("--thr", type=float, default=0.55)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--sample", type=int, default=0, help="emit N contested + N sole rows for hand labelling")
    ap.add_argument("--seed", type=int, default=311)
    a = ap.parse_args()

    tools, nhosts = D.load(a.capture)
    print("capture: %d tools from %d live servers" % (len(tools), nhosts))

    byname = collections.defaultdict(list)   # name -> [(host, text, sib)]
    for host, name, text, sib in tools:
        byname[name].append((host, text, sib))

    # ---- cluster every shared name -------------------------------------------
    nclust = {}
    for name, v in byname.items():
        hosts = {h for h, _, _ in v}
        if len(hosts) <= 1:
            nclust[name] = 1
            continue
        nclust[name] = len(cluster([t for _, t, _ in v], a.thr))

    if a.validate:
        print("\n-- clusterer validation (thr=%.2f) --" % a.thr)
        exp = {"dataset_top": 1, "enquiry_describe": 1, "submit_enquiry": 1}
        ok = True
        for nm, want in exp.items():
            got = nclust.get(nm)
            good = got == want
            ok &= good
            print("  %-20s hosts=%-3d clusters=%-3s expect %d  %s"
                  % (nm, len({h for h, _, _ in byname.get(nm, [])}), got, want,
                     "OK" if good else "FAIL"))
        for nm, lo in (("search", 15), ("fetch", 10)):
            got = nclust.get(nm)
            good = got is not None and got >= lo
            ok &= good
            print("  %-20s hosts=%-3d clusters=%-3s expect >=%d %s"
                  % (nm, len({h for h, _, _ in byname.get(nm, [])}), got, lo,
                     "OK" if good else "FAIL"))
        print("  VALIDATION:", "PASS" if ok else "FAIL")
        if not ok:
            print("  -> refusing to report. fix the clusterer or the threshold.")
            return 1

    # ---- contested vs sole ----------------------------------------------------
    contested, sole = [], []
    for host, name, text, sib in tools:
        (contested if nclust[name] >= 2 else sole).append((host, name, text, sib))
    print("\ntool instances: %d contested (name held by >=2 distinct offerings), %d sole  [%.1f%% contested]"
          % (len(contested), len(sole), 100 * len(contested) / len(tools)))
    nc = sum(1 for n in nclust if nclust[n] >= 2)
    print("names contested: %d of %d distinct names" % (nc, len(nclust)))

    # ---- the comparison ------------------------------------------------------
    def rate(group):
        k = sum(1 for _, _, t, s in group if D.fams(t, s))
        return k, len(group), 100 * k / len(group) if group else 0.0

    print("\n-- directive rate, detector as-is (under-reports by x1.45 overall) --")
    rows = []
    for label, g in (("contested", contested), ("sole", sole)):
        k, n, p = rate(g)
        lo, hi = wilson(k, n)
        rows.append((label, k, n, p, lo, hi))
        print("  %-10s %5d/%-6d = %5.1f%%  [%.1f, %.1f]" % (label, k, n, p, lo, hi))
    d = rows[0][3] - rows[1][3]
    print("  difference: %+.1f points" % d)

    # two-proportion z
    k1, n1 = rows[0][1], rows[0][2]
    k2, n2 = rows[1][1], rows[1][2]
    pp = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    z = (k1 / n1 - k2 / n2) / se if se else 0.0
    print("  two-proportion z = %.2f" % z)

    # ---- dose: does it scale with HOW contested? -----------------------------
    print("\n-- dose-response: directive rate by number of rival offerings --")
    bins = [(1, 1), (2, 2), (3, 4), (5, 9), (10, 10 ** 6)]
    for lo_, hi_ in bins:
        g = [(h, nm, t, s) for h, nm, t, s in tools if lo_ <= nclust[nm] <= hi_]
        if not g:
            continue
        k, n, p = rate(g)
        wl, wh = wilson(k, n)
        lab = "%d" % lo_ if lo_ == hi_ else ("%d+" % lo_ if hi_ > 10 ** 5 else "%d-%d" % (lo_, hi_))
        print("  rivals=%-6s %5d/%-6d = %5.1f%%  [%.1f, %.1f]" % (lab, k, n, p, wl, wh))

    # ---- confound check: does one fleet carry it? ---------------------------
    print("\n-- confound: contested instances by host, top 10 --")
    hc = collections.Counter(h for h, _, _, _ in contested)
    for h, c in hc.most_common(10):
        print("  %4d  %s" % (c, h))
    print("  top-10 hosts are %.1f%% of contested instances"
          % (100 * sum(c for _, c in hc.most_common(10)) / len(contested)))

    # same comparison with the 10 biggest contested hosts removed
    drop = {h for h, _ in hc.most_common(10)}
    c2 = [x for x in contested if x[0] not in drop]
    s2 = [x for x in sole if x[0] not in drop]
    print("\n-- the comparison again, 10 biggest contested hosts removed --")
    for label, g in (("contested", c2), ("sole", s2)):
        k, n, p = rate(g)
        lo, hi = wilson(k, n)
        print("  %-10s %5d/%-6d = %5.1f%%  [%.1f, %.1f]" % (label, k, n, p, lo, hi))

    # one host, one vote: does a server's MEAN directive rate move with contest?
    print("\n-- per-server (one host one vote), split by share of its tools contested --")
    per = collections.defaultdict(lambda: [0, 0, 0])   # host -> [direct, tools, contested]
    for h, nm, t, s in tools:
        per[h][1] += 1
        if D.fams(t, s):
            per[h][0] += 1
        if nclust[nm] >= 2:
            per[h][2] += 1
    hi_g = [v[0] / v[1] for v in per.values() if v[1] >= 3 and v[2] / v[1] >= 0.5]
    lo_g = [v[0] / v[1] for v in per.values() if v[1] >= 3 and v[2] / v[1] == 0.0]
    import statistics as st
    for lab, g in (("mostly contested", hi_g), ("no contested tool", lo_g)):
        if g:
            print("  %-18s n=%-4d mean %.1f%%  median %.1f%%"
                  % (lab, len(g), 100 * st.mean(g), 100 * st.median(g)))

    # ---- namespace cross-check ---------------------------------------------
    if os.path.exists(a.registry):
        hn = host_ns(a.registry)
        print("\n-- cross-check: do clusters track distinct PUBLISHERS? --")
        for nm in ("search", "fetch", "dataset_top", "enquiry_describe"):
            v = byname.get(nm) or []
            ns = set()
            for h, _, _ in v:
                ns |= hn.get(h, set())
            print("  %-18s hosts=%-3d clusters=%-3s distinct namespaces=%d"
                  % (nm, len({h for h, _, _ in v}), nclust.get(nm), len(ns)))

    # ---- hand-label sample --------------------------------------------------
    if a.sample:
        import random
        rnd = random.Random(a.seed)
        out = os.path.join(HERE, "labels_collision_%s.txt" % a.seed)
        with open(out, "w") as f:
            for label, g in (("CONTESTED", contested), ("SOLE", sole)):
                for h, nm, t, s in rnd.sample(g, min(a.sample, len(g))):
                    f.write("### %s  %s :: %s\n%s\n\n" % (label, h, nm, (t or "").strip()))
        print("\nwrote %s (%d+%d rows, seed %d)" % (out, a.sample, a.sample, a.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
