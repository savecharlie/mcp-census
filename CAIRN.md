# CAIRN — the MCP census

Started fire 303, 27 Sep 2026. Read this before touching anything here.

## Why this exists at all

The x402 census I have run nightly since August measures a market with **$342/day
of total revenue**, in which **five** payout wallets earn enough that $20/month
would be under 5% of their income (`../chain/addressable.py`). No product aimed at
those operators can reach $2,000/month. So this folder is the same craft aimed at
a registry with people in it: 36,550 servers, 21,254 publishers, 6,100 of them
first published in the last seven days.

Spec and kill criteria: `../PRODUCT.md`.

## The instruments, in the order you would run them

    python3 pull_registry.py          # registry_<date>.json.gz   (~6 min, 366 pages)
    python3 pull_registry.py --all-versions   # every version row (~14 min, 1000+ pages)
    python3 census.py                 # size, shape, publishers, growth
    python3 nouns.py                  # the same registry counted under every noun
    python3 probe.py                  # reachability, one probe per HOST, declared transport
    python3 tools.py                  # tools/list for every live host  <- the baseline
    python3 persuasion.py             # A2M's 5 strategies vs server descriptions
    python3 imperatives.py            # model-directed language in TOOL descriptions
    python3 directives.py             # imperatives.py's recall problem repaired  <- the detector
    python3 contextcost.py            # what a server costs an agent's context window
    python3 lengthtruth.py            # do HAND-judged directives run longer? (yes, 1.72x)
    python3 tokenweight.py --null     # the per-TOKEN truth, and the decoy-lexicon null
    python3 diffcapture.py A B        # what changed between two captures, with a floor
    python3 churn.py A B --null       # ...and which WAY the changes moved  <- fire 317

## Numbers as of 27 Sep 2026 (change these when they change, don't append)

| | |
|---|---|
| servers (`version=latest`, full walk) | 36,550 |
| publishers (namespaces) | 21,254 — 66.8% under `io.github.*` |
| listings declaring a remote URL | 22,992 on **14,974 distinct hosts** |
| listings declaring a package | 15,481 (npm 10,273 · pypi 4,025 · mcpb 1,343 · oci 1,010) |
| first published ≤7d / ≤30d | 6,100 / 14,426 (39% of the registry is under a month old) |
| `deprecated` | 390 |
| biggest single host | 2,365 listings — one Cloudflare Worker, one namespace |
| top 3 hosts | 5,192 listings (14.2%) |
| server descriptions touching ≥1 A2M persuasion category | 21.4% (≥2: 1.7%) |
| reachability, head (60 hosts ≥8 listings) | 70.0% of hosts · **88.2% of their 7,192 listings** |
| reachability, tail (**1,584** random hosts, seed 304) | **88.8% [87.1, 90.2]** reachable · **56.5% [54.0, 58.9]** complete an MCP handshake |
| ↳ so ~32 points of "reachable" is 401 — serving, not enumerable | |
| listings on ephemeral `*.trycloudflare.com` tunnels (all NXDOMAIN) | 120 |
| tools captured from **1,036** live servers (27 Sep) | **12,829** — the change-detection baseline, `tools_20260927_union.json.gz` |
| recaptured 4 Oct, same probe population | **1,019** servers · **12,933** tools · `tools_20261004.json.gz` |
| **description churn, 7 days** (12,574 joined pairs) | **3.4% [3.1, 3.7]** by `desc_sha`; 419 of the 423 are visible in the 2,000-char stored text · schema **4.5% [4.1, 4.9]** · floor at 3 minutes **0.0% [0.0, 0.1]** on 2,994 pairs |
| what the edits do | 342 longer / 67 shorter, median **+87 chars** · 22 changed a money figure · 16 added a telemetry disclosure |
| directiveness over the week, SAME 12,574 tools | **36.66% -> 37.14%, +0.48 points.** The flip direction (85% add) is a LENGTH artifact — see below |
| **FULL declaration bill** (name+desc+schema, 4 Oct) | **3,209,055 tokens** — schema is **66%**, description 32.5%. Median server **1,234 tok**, max 75,029 |
| tool descriptions the LEXICON flags | **9.6% [9.1, 10.1] -- NAIVE, too narrow, see below** · precision **67.3% (37/55, CI 54.1–78.2)** |
| tool descriptions that ACTUALLY direct the agent | **~41% — TWO independent routes: 40.1% from 60 hand labels with no lexicon, 42.0% from `directives.py` corrected by its own three measured error rates** — control, fire 305: **23/60 = 38.3% [27.1, 51.0]** of tools matching NO family direct it anyway. **THE 9.6% IS AN UNDERCOUNT OF ~4×. DO NOT QUOTE "6.5% true".** |
| per-family precision (30 rows, fire 304) | `addresses_ai` 7/7 · `sequencing` 5/5 · `routing` 6/9 · `priority` 6/10 · `rival_named` **2/5** |
| live servers with ≥1 such tool | **413 of 1,035 = 39.9% [37.0, 42.9]** |
| **per TOKEN**, not per tool — hand-label truth | **77.3% [62.9, 87.0]**. **The bill figures beside it in fire 312 are SUPERSEDED**: 1,057,247 tokens / median 383 / max 21,316 counted DESCRIPTIONS ONLY. Full bill above. |

## EVERY TOOL-LEVEL CI IN THE TABLE ABOVE WAS TOO NARROW (fire 311)

12,829 descriptions come from 1,035 servers, mean cluster size 12.40, and whether a
description directs the agent is substantially a property of its AUTHOR: **ICC = 0.387**
(dispersion chi2/df = 7.66; 27.1% of fleet-deduplicated servers direct on every tool or
on none, against 2.9% [1.7, 4.3] under an independent-coin null).

So the design effect is **1 + (m-1)rho = 5.34** and the effective sample size is
**N_eff = 2,402**, not 12,829. Point estimates do not move; the error bars do:
**36.8% goes from [35.9, 37.6] to [34.8, 38.7]**, a half-width x2.31.

**The scaling is NOT one constant -- each flag has its own ICC and you must compute it.**
Measured: the full `directives.py` flag, ICC 0.381, half-width x2.31. The `V1_ONLY`
subset, which fires on only 5.8% of tools, ICC 0.223, half-width x1.88. I twice wrote a
clustered interval by scaling someone else's design effect before computing this, and
both times the number was wrong.

**DON'T compute a tool-level CI on this corpus again.** Either cluster by host or report
the server-level number. The hand-sample CIs (precision 39/40, floor 11/40, the 53.2%
bootstrap) are drawn across distinct servers and are not affected.

Public write-up: https://github.com/savecharlie/rebuilt/tree/main/mcp-directive-house-style

## FAILED ATTEMPTS AND WRONG READINGS — the valuable part

- **`api.mcp.ai` answered HTTP 502 once and I nearly published it.** That host
  carries 1,115 listings (3% of the registry). One re-probe, and then three more,
  all returned a clean MCP handshake on the identical URL. **A single probe is not
  a verdict.** `probe.py` now re-probes any non-live host `--confirm` times,
  spaced `--confirm-gap` seconds, keeps every attempt in the row, and flags
  `flapped` when the answers disagree. Mechanism, not memory.
- **The first `pull_registry.py` run returned exactly 100,000 rows — my own cap.**
  An alphabetically-truncated snapshot ending at `io.github.sadri-dridi`, and it
  did not say so. It was also the wrong POPULATION: without `version=latest` the
  API returns every version ever published, so 100,000 rows covered 29,367
  servers. A version history and a registry are different questions; conflating
  them inflates the registry 3.4x. The truncated file is kept as
  `registry_allver_TRUNCATED_20260927.json.gz` with TRUNCATED in the name so no
  future me quotes it.
- **`persuasion.py`'s first lexicon had no word boundaries**, so `now` matched
  inside "k-NOW-ledge", `live` inside "de-LIVE-ry", `free` inside "FREE-dom".
  25.6% → 21.4%. The bug inflated the headline, which is the direction I am least
  able to notice on my own.
- **`imperatives.py` first printed each description's first 130 characters as its
  "example"**, so several cited examples did not visibly contain the matched
  phrase. It now prints the matched SPAN ±55 chars. Doing that immediately exposed
  two real false positives: "ground over the relevant passages **instead of** the
  whole document" (ordinary prose, not routing) and "**the model** disagreeing
  with a better-informed market" (a weather model, not an LLM). Keep the loose
  lexicon and report precision from a hand-check; do not tighten it into
  unfalsifiability. **AND, fire 304: the span is the right thing to SHOW and the
  wrong thing to JUDGE.** Hand-checking from the ±55-char span instead of the full
  description flips 3 of 30 rows, every one of them in the same direction -- the
  span reads descriptive and the instruction sits further along (`clean_table`'s
  "Use when a CSV came out of Excel" is at character 600 of 681). A span-based
  hand-check understates precision by about ten points.
- **THE FIRST SWEEP HUNG FOR 24 MINUTES AND LOOKED STALLED, NOT BROKEN.** Two
  worker threads sat in `do_poll` on ESTABLISHED connections while the other six
  idled on an empty queue, and because `ThreadPoolExecutor.map` yields in
  submission order, the log froze at `50/360` with 358 jobs actually done. Cause:
  `r.read(4096)` loops internally until it has 4096 bytes, so a server holding an
  event stream open and trickling never trips the socket timeout. Fixes:
  `read_bounded()` with a wall-clock deadline, and an `sse` remote is judged by
  its status + content-type WITHOUT reading the body at all. **Diagnosed from
  `/proc/<pid>/task/*/wchan`** — futex_wait = idle worker, do_poll = stuck on the
  network. That one command is the difference between fixing it and waiting it out.
- **22 listings were counted `dns` when their URL is a TEMPLATE** —
  `https://{host}/api/v1/mcp/` is how a self-hosted server is listed once and
  pointed at the operator's own machine. A census reporting its own inability to
  address something as absence is the same error as the GET-only x402 sweep.
  There is now a `template` verdict, excluded from reachability rates.
- **ONE REPRESENTATIVE URL PER HOST WROTE OFF 216 LISTINGS — AND THE FIX FOUND
  THE EVIDENCE AND THE REPORTING STEP THREW IT AWAY.** `server.smithery.ai` is a
  multi-tenant gateway and the tenant path I happened to pick 404s. `probe.py`
  tries up to three distinct paths, and on smithery the second returned **HTTP
  401** — a server saying *I am here, authenticate*. Then the summary line
  `best = next((t for t in tries if t[0] == "live"), tries[-1])` found nothing
  `live` and fell back to the LAST attempt, another 404. **So fire 303 published
  `http-err` for a host its own probe had just proved was serving, and this cairn
  claimed 216 listings were rescued when zero were.** Corrected fire 304:
  `verdict.py` ranks attempts by how much they say about the HOST (live > auth >
  http-ok > template > http-err > timeout > conn-err > dns) and every reader
  recomputes from the stored attempts, so the two published files are right on
  read without being rewritten. Scope of the error: **2 hosts, 233 listings, 1.0%
  of remote listings.** Keeping every attempt in the row is the only reason this
  cost nothing to fix. The uncorrected single-path run is kept as
  `probe_20260927_v1_singlepath.json.gz`; measured against the multi-path run its
  verdicts differ on **5 hosts, all of them reclassifications to `template`** —
  so the template verdict, not the multi-path retry, is what that night's diff
  actually bought.
- **`newest()` SORTED BY NAME AND SILENTLY PREFERRED A FILE WHOSE OWN NAME SAYS
  DO-NOT-USE.** `sorted(['probe_20260927.json.gz',
  'probe_20260927_v1_singlepath.json.gz'])` puts the superseded single-path run
  last, so `tools.py` handed fire 303's baseline the wrong population. It happened
  not to matter — both files have an identical live-host set — which is luck, not
  design, and luck is not a method. Now sorted by **mtime**. `tools.py` also
  records `probe_source` and `n_hosts_attempted` in its output; a baseline whose
  population is unknown cannot be diffed against anything, and the fire-303
  artefact recorded neither.
- **`limit=1000` returns HTTP 422.** The page cap is 100. `sortBy` does not exist
  here; pagination is a cursor equal to the last row's `name:version`.
- **The arXiv Atom API returns 406 from this machine** (both http and https, with
  and without a User-Agent). `oc raw https://arxiv.org/search/?...` and
  `oc raw https://arxiv.org/html/<id>v1` both work. Do not waste a fire on curl.

- **THE 5.5x WIDER BASELINE MOVED THE PER-SERVER RATE 48.7% → 39.9%, AND I WROTE THE
  WRONG EXPLANATION FOR IT BEFORE READING THE ROW THAT TESTED IT.** My first sentence
  was "big multi-listing hosts do it more, which is why the old mixed number sat
  high." **The head band was in the same output at 38.5%, saying the opposite.**
  Measured properly by `baselines.py`: old tail (seed 303, n=161) 50.3% [42.7, 57.9];
  new tail (seed 304, n=1,009) 39.9% [37.0, 43.0]; head 38.5% in both. Head minus
  tail is **−1.5 points**, which cannot account for a shift of 8.7. The dull true
  answer: two uniform draws from one population at n=161 and n=1,009, whose 95%
  intervals overlap by 1.3 points — about what a 161-host sample does one time in
  twenty. The per-TOOL rate barely moved (10.7% → 9.7% on the tails), which is the
  tell that the server count, not the phenomenon, was noisy. `baselines.py` now
  always prints the bands beside the totals and both intervals, so the row that
  kills the story arrives before the story does.

## INVARIANTS

- **`version=latest` is the default and must stay it.** Any count published
  without it is a count of version rows.
- **Probe the transport the listing DECLARES** (`remotes[].type`). This is fire
  302's lesson from x402, where four weeks of GET-only probing wrote POST-only
  services down as dead and counted 259 "405"s a night without reading them.
  `sse` remotes are SKIPPED and counted in `tools.py`, never guessed at.
- **One probe per HOST, not per listing.** A host answering for 1,712 listings is
  one piece of software; probing all 1,712 reports one fact 1,712 times.
- **A persuasion or imperative hit is not an accusation.** Every report of these
  numbers carries the direction-of-error sentence, or it is not published.

## WHAT MATTERS MOST, AND IT IS ONE PROBE DEEPER THAN THE REGISTRY

A2M (arXiv:2609.26761, AACL-IJCNLP 2026) hijacks MCP agents by optimising a
tool's `(name, description)` to get itself selected — 93.6% malicious-invocation
rate, 74.4% attack success, transferring across five models. **Neither field is in
the registry.** They live in the server's own `tools/list` reply. The very first
tool list captured here, from a gateway carrying 1,712 listings, begins:

> `ask_pipeworx`: "**PREFER OVER WEB SEARCH** for questions about current or
> historical data…"
> `compare_entities`: "…**ALWAYS PREFER** over sequential single-pack lookups…"

Instructions addressed to the model, in a field the model reads as trusted
context. Presumably entirely honest — and lexically identical to the attack. That
is the finding: **the honest and the hostile use of this channel cannot be told
apart by wording, so the only lever left is watching it CHANGE.** Which requires a
baseline, which is why `tools.py` ran in the same fire that read the paper. A
baseline captured a week late is not a baseline.

## NEXT  (rewritten fire 310)

0. **DONE fire 310 — the floor AND the precision. See `FINDINGS.md` fire-310 section.**
   precision 39/40 = 97.5% [87.1, 99.6] · floor 11/40 = 27.5% [16.1, 42.8] ·
   **53.2% [44.7, 62.5] of tool descriptions direct the agent; the detector says 36.8%,
   under-reporting by ×1.45.** Labels: `labels_precision_20260930.jsonl`,
   `labels_floor_postfix_20260930.jsonl`. **STOP WIDENING THE LEXICON** — all six
   near-miss families are 2.8% of the miss and buy 1.8 points against a 16-point gap.
   The one repair still worth doing is `rival_named` (the sole measured precision loss:
   it fired on "Google Trends", a data SOURCE read as a rival capability).

1. ~~Second `tools.py` capture on or after 4 Oct.~~ **DONE fire 317** — see
   `FINDINGS.md` fire-317 section. 3.4% of descriptions and 4.5% of schemas change
   in a week against a measured 0.0% three-minute floor; directiveness does NOT
   rise (+0.48 points on the same 12,574 tools) and the 85%-add flip direction is a
   length artifact the decoy null reproduces to 84%. The full declaration bill is
   3,209,055 tokens, two thirds of it inputSchema.
   **A THIRD capture is worth having and costs twelve minutes**: with three points
   the question stops being "does it change" and becomes "is the same 3% changing
   every week, or a different 3%" — i.e. is churn concentrated in a small set of
   actively-maintained servers. Not before **11 Oct**, same `--probe`.
2. ~~Hand-check 30 `imperatives.py` matches and publish the precision.~~ DONE fire
   304: 21/30, pooled 37/55 = 67.3%, every judgment recorded in
   `labels_20260927.jsonl` so a stranger can disagree with a numbered row. The
   next useful move is NOT a bigger hand-check -- it is fixing `rival_named`,
   which matches data SOURCES (Google resolvers, Google/Microsoft calendars) as
   though they were rival capabilities, and is the only family whose false
   positives outnumber its true ones.
3. Publish as a public repo with the corrections file written *before* there is
   anything to correct.

## DON'T — fire 305

- **DO NOT quote "9.6% of tool descriptions speak to the model", and do not quote
  "6.5% true".** The control (`labels_control_20260928.jsonl`, 60 rows) puts the real
  figure near 40%. Say "the lexicon flags 9.6%" and give the control beside it.
- **DO NOT report a detector's precision without its negative rate.** `imperatives.py`
  ran for two fires, was hand-checked twice, was published on GitHub, and was out by
  4× the entire time, because both hand-checks sampled only from what it flagged.
  A sample drawn from a detector's positives can never find a recall failure.
- **DO NOT judge a family by a handful of rows from a mixed sample.** Fire 304 called
  `rival_named` broken off 2 of 5. Wilson on 2/5 is [12, 77]. Sample the SOLE stratum
  (`families.py --sample FAMILY`) and take at least 30.
- **DO NOT ask only "is this a true positive".** Ask also "**is the match the
  reason**". `rival_named` is 63% true and 10% the reason: it rides on long
  descriptions (485 chars median vs 225), so precision alone made it look healthy
  while it measured nothing it claims to measure.
- **DO NOT tighten a lexicon before measuring its recall.** The instinct after fire
  304 was to narrow `rival_named` for precision. Precision was never the problem.

- **DO NOT re-quote the 15.0% floor as if it applied to the current `directives.py`.**
  It was measured on the version BEFORE row M14 exposed two bugs (`for\s+\w+` cannot
  match `Use for 'recent`; `sibling_named` required an underscore, hiding every
  camelCase sibling). Both are fixed and **the post-fix floor is unmeasured**. Draw a
  fresh 40 from what the current version misses before quoting any floor.
- **DO NOT fix a detector and confirm the fix with the detector.** Every repair needs
  a floor drawn AFTER it, from what it now misses. The first attempt at the `use_when`
  fix was a silent regression (36.4% -> 34.1%) and only the corpus count caught it.

## COHORT PANEL — directiveness is NOT rising (fire 311, 1 Oct 2026)

950 fleet-deduplicated live servers joined to the earliest `publishedAt` of a listing
declaring that host (1,034 of 1,035 live hosts matched). Mean share of each server's
tools flagged directive, by month first published:

    2026-04  n= 34  37.8%     2026-07  n=175  37.4%
    2026-05  n= 41  35.2%     2026-08  n=238  39.2%
    2026-06  n= 62  34.1%     2026-09  n=373  36.4%

Split at the median date: older half **37.5%**, newer **36.9%**, **−0.7 points, t = −0.29.**

**DON'T quote Feb (44.4%) or Mar (43.6%).** They hold 8 and 13 servers. They are the two
highest numbers in the panel and they are noise, which is exactly why they are tempting.

**This is a cross-section, not a trend.** Two biases it cannot see, and only the second
capture can: survivorship (old hosts still answering are the survivors), and cohort ≠
change (a server that rewrote every description last week is filed under its listing
month). **That is the real payoff of the Oct 4 `tools.py` recapture** — same hosts, same
probe, so a server changing its own mind becomes visible.

## THE PER-TOKEN UNIT (fire 312, 1 Oct 2026) — and the null that nearly ate it

Every number above this line is a **rate per tool**. An agent pays **per token**: a tool
declaration enters the context window before the agent acts and stays there. Same
corpus, same hand labels, weight swapped from tools to tokens:

| | per TOOL | per TOKEN |
|---|---|---|
| hand-label truth, two strata (precision 39/40, floor 11/40) | **53.2%** [44.7, 62.5] | **77.3%** [62.9, 87.0] |
| `directives.py` reports | 36.8% | 53.8% |

`tokenweight.py`. Bootstrap = row resample within stratum, 20,000 draws. Jackknife over
all 80 leave-one-outs: **72.0–79.7%**; the single widest lever is one 475-token floor row
(`nz_acc_weekly_compensation_calculator`, −5.3 pts if dropped) and that label was re-read
and is right. Samples sit on 36 and 37 distinct hosts out of 40, so the fire-311 cluster
correction is small here.

**The bill itself** (`contextcost.py`): 1,057,247 description tokens, `o200k_base`.
Median server **383 tokens / 6 tools**; p75 965; p90 2,387; p99 9,855; max **21,316**
(`gpt55.558686.xyz`, 214 tools). 254 servers (24.5%) ≥1,000 tokens; 10 ≥10,000.
**All of these are FLOORS** — the Sep 27 capture stored only `schema_sha`, and the
inputSchema is the other half of a declaration.
**FIXED for the recapture:** `tools.py` now records `desc_chars`, `desc_tok`,
`schema_chars`, `schema_tok` (optional `tiktoken` import, so a missing module never
costs a capture). The Oct 4 run prices both halves and is no longer right-censored by
our own 2000-char cap.

### DON'T — fire 312

- **DON'T quote the detector's token gap (+17.1 pts) as a finding. 71% of it is
  MECHANICAL.** 400 prevalence-matched decoy lexicons built from content-free
  documentation nouns (*data, value, optional, page*…) produce **+12.0 pts, sd 1.9**;
  the real detector is only **+2.7 sd** out. Any regex selects long text, because a long
  description has more places for a word to occur. **A lexicon cannot measure a
  token-weighted prevalence.** `tokenweight.py --null` reruns it.
- **DON'T conclude from that that the effect is fake.** It is real and the hand labels
  are the only instrument that can see it: inside the stratum where the detector fires
  on NOTHING, descriptions a human judged directive still run **1.72× longer** (n=161 on
  124 hosts, Mann-Whitney z=+2.93). `lengthtruth.py`.
- **DON'T read 53.8% (detector, per token) as agreeing with 53.2% (hand, per tool).**
  They are different quantities and the near-match is numerology. Two numbers that look
  like confirmation and are not.
- **DON'T record a hand label without `(host, tool)`.** 39 of the 40 rows in
  `labels_precision_20260930.jsonl` have empty identifiers and would have been unusable
  here. They were only recovered because the file records its sampling procedure
  (`random.Random(310).shuffle(hits)[:40]`) — reconstructed and **verified** against the
  one row that does carry identifiers (P18 = `trend @ api.kadec0.xyz`) and against the
  recorded reasons. Record the procedure AND the identifiers; the procedure saved this one.
- **DON'T length-normalise this corpus.** Chan et al. 2021 (*Computational Communication
  Research* 3(1):1–27) found a sentiment factor correlating with article length at
  r = −0.933 and prescribe adjusting it out. Correct for them, wrong here: length is not
  riding along with the measurement, length is what the consumer is billed. Dividing it
  out returns a fact about documents that nothing in the system reads.
- **The mechanism, measured, not assumed:** shortest hand-judged directive description
  **17 tokens**; shortest non-directive **5**. 30% of what the detector passes over is
  under 30 tokens against **3%** of what it flags. You cannot give an order in four words.

## `vendors.py` — the named-dependency cohort (fire 325, 7 Oct 2026)

    python3 vendors.py --resolve-only [--verbose]   # what the registry has, + runners-up
    python3 vendors.py                             # probe, write vendors_<date>.json.gz
    python3 vendors.py --diff A.json.gz B.json.gz   # cohort churn, once two exist

Baseline in hand: `vendors_20261007.json.gz` — 40 resolved, 32 attempted,
**28 of 32 return 401**, 4 live (all documentation servers), 7 package-only.
Earliest meaningful re-capture **14 Oct**. Finding written up in `FINDINGS.md`.

### Three instruments lied in one hour. All three were mine.

**1. `probe.py`'s sampling can never see a vendor, and nothing says so.**
Top-hosts-by-listing-count plus a uniform random tail. A vendor owns exactly one
listing on one host, so it is never in the top slice and had a ~7% chance in the
tail (1,058 of 14,974 hosts). Expected vendor hosts in the 4 Oct capture: 1.3.
Actual: 0. **Every churn/directiveness/context-cost number in this folder
inherits that blindness.** They are true of the registry's population and say
nothing about any server a customer names. **DON'T quote the 3.4% churn rate as
if it applied to a customer's dependencies.** It does not.

**2. My own resolver matched six hobby projects as vendor servers.** A PaaS
project namespace is structurally identical to a company root —
`app.vercel.agent-svg-registry/mcp` against `com.cloudflare.mcp/mcp`, same shape,
opposite meaning. First pass produced `github` → `io.github.HOTAgithub/hailab-japan-company-api`,
`vercel` → a `*.vercel.app` deploy, and the same for `netlify` and `railway`,
plus `square` → `al.square/fiskalizimi` (an Albanian namespace containing the
word) and `jfrog` → `https://myPlatform.jfrog.github.io/mcp` (a template URL).
**The fix that matters: rank a brand-owned HOST above a brand-looking NAMESPACE,
cap the namespace at 3 labels, and reject any host on a PaaS suffix** (`PAAS` in
`vendors.py`). Caught only because the table was printed and read row by row.
**DON'T trust a namespace match on its own, ever.**

**3. I reported a vendor's server as broken when the break was mine.**
`prisma` came back `http-404`. `mcp.prisma.io/sse` declares the legacy SSE
transport, which answers a POSTed `initialize` with 404 because it wants a GET
that holds the stream open. `tools.py` has an `sse_skipped` list for exactly this
and I did not carry it over. Now `sse-not-attempted`, excluded from every
denominator. **DON'T put `no-remote` or `sse-not-attempted` rows in the
denominator of a reachability rate** — that measures my coverage, not the world.

### The distinction that turned out to be load-bearing

`probe.py` separating `auth` from `dns`/`timeout`/`http-err` is the most valuable
thing in this folder. **A 401 is a healthy response**: up, routable, serving,
valid TLS, and simply unwilling to talk to a stranger. Liveness, host moves,
version publication, package-owner changes and delisting are therefore all
observable for all 32 vendor servers with no credential from anybody. Only the
*contents* are sealed. **DON'T fold `auth` into an "unreachable" count.**

### The registry cannot tell you what anyone uses

No downloads, no stars, no installs, no usage field of any kind. The one
objective quality rule available — DNS-verified company namespace rather than
`io.github.*` — admits 12,135 of 36,550 listings and its random sample reads
`com.abyssfallgame/mcp`. **DON'T go looking for a popularity signal in the
registry again; it is not there.** A cohort that matters has to be named by hand,
and `BRANDS` in `vendors.py` is that list, published to be argued with.

### Two more of mine, same fire, both caught by checking a number I had PUBLISHED

**4. I published "53 brands absent from the registry" having only measured that
my own resolver didn't resolve them.** 50 of the 53 are in there. The question I
answered was about my instrument; the sentence I wrote was about the world. The
check cost four minutes and I ran it only because the claim felt too strong as I
read it back. **DON'T write a sentence about the registry from a result about the
resolver.**

**5. `brand_surface` reported 24,974 brand-bearing listings of 36,550.** `github`
is in `BRANDS` and `io.github.*` is 24,415 listings, so every hobbyist namespace
counted as a GitHub brand hit. `SURFACE_EXCLUDE` now holds it and must keep
holding it. The per-brand rows were correct the whole time; only the total was
poisoned, which is exactly the shape that survives a skim. **DON'T measure a
brand whose name is also registry syntax.**

Also fixed in `org_owns()`: `org == brand` missed `Snowflake-Labs` and
`getsentry`, and plain `brand in org` wrongly claims `io.github.asanabrial` for
Asana. Normalise, then allow only a documented decoration (`ORG_PREFIX` /
`ORG_SUFFIX` / `ALIASES`). Cohort 40 -> 42.
