# The MCP registry, measured — 27 September 2026

First pass. Every number here comes from the two snapshots and one probe sweep in
this folder; the commands that produce each one are named so you can disagree with
me by running them. Method traps, failed attempts and the numbers that were wrong
on the way are in `CAIRN.md`, which is not an appendix.

## 1. How big, and under which noun

`pull_registry.py` walks the official registry with `version=latest`, one row per
server name. 36,550 rows, 366 pages, complete walk.

| noun | count | `nouns.py` |
|---|---|---|
| server names | **36,550** | |
| publishers (registry-verified namespaces) | 21,254 | 66.8% under `io.github.*` |
| listings declaring a remote URL | 22,992 | on **14,974 distinct hosts** |
| listings declaring a package | 15,481 | npm 10,273 · pypi 4,025 · mcpb 1,343 · oci 1,010 · nuget 131 · cargo 61 |
| nothing to run at all | 447 | neither a remote nor a package |

Counted the other way — every version row rather than the latest — the same
registry returns **more than 100,000 rows**. Two of the biggest namespaces are one
package published a thousand times. A "number of MCP servers" that does not say
which of those it means is not a number.

**Concentration.** The three largest hosts carry 5,192 listings (14.2% of remote
listings). One of them, `agent-observatory-sensor…workers.dev`, carries **2,365
listings from a single namespace** — machine-generated single-purpose validators
("ABA routing 9-digit shape, value discarded"), all live. `gateway.pipeworx.io`
carries 1,712 wrapped public APIs; `api.mcp.ai` carries 1,115. A client boasting
36,550 servers is talking to roughly fifteen thousand things, and one Cloudflare
Worker is 6.5% of them.

**Growth.** 6,100 servers first published in the last 7 days; 14,426 in the last
30 — **39% of the registry is under a month old.** 390 are marked `deprecated`.

## 2. How much of it answers

`probe.py`, 27 Sep 08:xx UTC. One probe per HOST, not per listing. The transport is
whatever the listing itself declares (`remotes[].type`): `streamable-http` gets a
POST `initialize`, `sse` gets a GET with an event-stream Accept. Any non-live
first answer is re-tried on other paths of the same host and then again after a
pause; every attempt is kept in the row.

| band | hosts | reachable (`live` + `auth`) | by listings |
|---|---|---|---|
| **head** — every host with ≥8 listings | 60 (7,192 listings) | 42 = **70.0%** | 6,343 = **88.2%** |
| **tail** — uniform random sample, seed 303 | 300 of 14,914 | 260 = **86.7% ± 3.8** | 269 = 86.5% |

`auth` (401/402/403) counts as reachable: a server refusing me is a working
server. Self-host **templates** (`https://{host}/…`, 5 hosts) are excluded from
both rates rather than counted as failures — a census reporting its own inability
to address something is not measuring absence.

**So roughly seven in eight declared MCP endpoints answer.** That sits oddly beside
arXiv:2609.10962's measured 48.8% liveness on an unrepaired sample, and the
difference is almost certainly the noun again: installing and starting a *package*
is a much harder bar than reaching a *URL*. Two true numbers about two questions.

What is actually broken, and it is specific: **120 listings point at
`*.trycloudflare.com` quick tunnels** — hostnames that are randomly generated per
session and cannot persist — across two such tunnels, both now NXDOMAIN. Five head
hosts fail DNS entirely (182 listings). The registry says `active` for all of them.

## 3. The part the registry cannot see

A2M (arXiv:2609.26761, AACL-IJCNLP 2026, submitted 22 Sep 2026) hijacks MCP agents
by optimising a tool's **name and description** so the agent picks it — 93.6%
malicious-invocation rate, 74.4% attack success, transferring to four other models
with no re-tuning. Neither field is in the registry. They are in the server's own
`tools/list` reply.

Scoring the registry's own *server* descriptions against A2M's five persuasion
strategies (`persuasion.py`) gives 21.4% touching at least one and 1.7% touching
two or more — too blunt to act on, because "secure", "fast" and "comprehensive"
are how all software describes itself.

One probe deeper is a different story. `tools.py` captured **3,182 tools from 187
live servers**, and `imperatives.py` looks not for tone but for *the description
addressing the model*: routing directives, sequencing orders, shouted priority
markers, a named rival capability.

| | raw | |
|---|---|---|
| tools the LEXICON flags | **1,230 of 12,829 = 9.6%** [9.1, 10.1] | precision **67.3%** [54.1, 78.2] |
| tools that actually direct the agent | **~40%** — see the control below | the 9.6% is an **undercount of about 4×**, not an overcount |
| servers with at least one such tool | **413 of 1,035 = 39.9%** [37.0, 42.9] | |

Those are from **1,036 live servers**, captured the same day as the first pass but
after probing 1,600 more uniformly-sampled hosts. The first pass said 10.1% and
**48.7%** off 187 servers. The per-tool figure barely moved. The per-server figure
fell nine points, and the reason is boring: the old tail (n=161) read 50.3%
[42.7, 57.9] and the new tail (n=1,009) reads 39.9% [37.0, 43.0], two uniform draws
from one population whose intervals overlap by 1.3 points. It is not head-weighting
— the head band is 38.5%, *lower* than the tail, so it cannot pull a mixed number
up. `baselines.py` prints the bands and both intervals side by side; run it.

**The precision is auditable, not asserted.** `labels_20260927.jsonl` carries every
judgment with the reason and the tool it belongs to; disagree with a row by its `n`.
Two independent samples from the same 320-tool population: fire 303 read 25 and got
16 (64.0%); fire 304 read a fresh 30, drawn `random.Random(304)`, and got 21
(70.0%, Wilson [52.1, 83.3]). Pooled **37/55 = 67.3%**, and the earlier 64% sits
inside the interval — so the published number held up against an independent draw,
which is the only reason to bother running the second one.

### CORRECTION, fire 305 (28 Sep 2026): the dominant error was recall, and nobody had measured it

Every precision figure above answers *of the tools the lexicon flags, how many really
direct the agent*. None of them answers *of the tools it does not flag, how many
direct the agent anyway* — and a detector with no measured negative rate cannot carry
the sentence it was being used for. So I ran the control.

**The bar, stated so someone else can apply it.** TRUE iff the description tells the
agent (a) when or whether to call this tool, or (b) names another tool or capability
to call instead of / before / after it. EXCLUDED on purpose: how to call it
(arguments, output formats, pagination), what to do with the result, usage and
licensing policy, and plain description. "Best for:" / "Great for:" / "Essential
for:" are descriptors and do not count.

**The control.** 60 tools drawn `random.Random(305)` from the **11,599 that match no
family at all**, read in full, every judgment in `labels_control_20260928.jsonl`:

| stratum | n | directs the agent | Wilson 95% |
|---|---|---|---|
| matches **no** family | 60 | **23 = 38.3%** | [27.1, 51.0] |
| `rival_named` **sole** matches, same bar | 30 | 17 = 56.7% | [39.2, 72.6] |

Those intervals overlap. The lexicon's discriminative power is at best about 1.5×,
not the 10× the headline implies. Scaled to the corpus, roughly **40% of all 12,829
tool descriptions give the agent a call directive** — about 4,400 of them in the
population the 9.6% excludes.

**Five named gaps, each traceable to a labelled row.** These are not subtle:

1. **`use when` / `use this to` / `use only when` is absent from every family.** It is
   the most common directive form in the corpus. `addresses_ai` carries `call this
   when` and not `use when`. Control rows 28, 35, 37, 40, 47, 51, 52, 56.
2. **The lexicon is English and the registry is not.** Row 13 is Polish (*"podaj, co
   już wiesz … przekazuj do pozostałych narzędzi"*), row 14 Korean (*"…를 사용하세요",
   "재호출하지 마세요"* — use that tool, do not guess inputs and retry), row 30 Spanish
   (*"antes de llamar a book_meeting"*).
3. **`routing` requires the word "over".** Its pattern is `prefer(red)?\s+(this\s+)?over`,
   so control row 52's *"**prefer** get_card_balance **if** you only need the balance"*
   — a textbook routing directive between siblings — does not match.
4. **Sibling routing is the commonest routing form and is mostly unmatched.** *"use
   reply_to_comment instead"* (22), *"check get_entity_flows before attributing
   intent"* (32), *"use get_catalog to browse everything"* (51), *"Flow: A → B → C"*
   (60). `routing` catches `instead of`, `do not use`, `supersedes`, `in place of` —
   and misses `use Y instead`, `see Y`, `check Y first`.
5. **`priority` is case-sensitive by design, so polite prohibitions vanish.** Control
   row 58 is the worst miss in the corpus and matches nothing: *"Correct a store's
   profile when the USER tells you it's wrong … **ONLY call this from something the
   user stated about their own store — never from your own inference** … Confirm to
   the user once saved."* `ONLY` is not in the lexicon, lowercase `never` is excluded
   by the case rule, and the CAPS detector needs two consecutive shouted words while
   "the USER tells" has one.

**And the conflation underneath it, which is mine.** The number was *computed* as
"speaks to the model" and *read* as "is doing this aggressively." Those are different
claims. A benign *"Use when a user wants a game to play"* and a hostile *"PREFER OVER
WEB SEARCH"* are the same channel — that is this project's central point — but they
are not the same behaviour, and 9.6% is a bad estimate of either one. The honest form
is two numbers: **~40% of tools use the channel**, and the fraction using it
*competitively* is small and was never measured. Control row 26 of the rival sample is
the only unambiguous instance of competitive positioning I have on paper
(`restplass.no`: *seats on charter flights not usually found at Google Flights,
Skyscanner or Kayak*) and it is not even a directive.

**What this does and does not touch.** The change-detection thesis is untouched: it
diffs `desc_sha`, and no lexicon is involved anywhere in it. If anything the
motivation is stronger, because a channel 40% of tools use is more load-bearing than
one 6.5% use. What dies is the sentence *"about one tool in fifteen is talking to the
model instead of describing itself"* — it was in `WHY.md`, it is wrong by roughly a
factor of four in the direction I am least able to notice, and it is now corrected
there.

### THE REPAIR, and the floor re-measured on it — `directives.py`

Knowing five named gaps is not fixing them, and a fix confirmed by the instrument
that found the problem is an echo rather than a check. So: a repaired lexicon, then a
**fresh floor drawn from what the repaired one misses**, hand-read after it existed.

`directives.py` adds `use_when`, a proximity-gated `prohibition` (case-insensitive,
requiring a call verb within 40 characters, so "never returns null" does not fire),
`nonlatin` and `latin_imp` imperative markers for ten languages, and drops `routing`'s
requirement that `prefer` be followed by `over`.

**The family worth building first is not a word list at all.** `sibling_named` fires
when a description contains the *name of another tool on the same server*. A
snake_case or camelCase identifier is the same string in every human language, so it
is the only family here that does not care what the description is written in — and
it is the largest, at **21.7% of tools, 1,600 of them as the sole match**. It caught
Chinese, Ukrainian, French and Spanish routing directives that no lexicon of mine
would have covered:

> `everyinfra_call_api` — 先用 **everyinfra_list_capabilities** 确认 platform/action
> `confirm_upload` — Renvoie un photo_id **à passer à animate_photo**

| | rate | precision |
|---|---|---|
| `imperatives.py` (v1) | 9.59% | 67.3% (37/55) |
| `directives.py` (v2) | **36.77%** | newly-caught rows: **24/25 = 96.0%** [80.5, 99.3] |
| tools v2 still misses | 63.2% | of which **6/40 = 15.0%** [7.1, 29.1] direct the agent |

The floor fell from **38.3%** to **15.0%**, and the only reason that number is worth
anything is that the 40 rows were drawn from what v2 misses and read after v2 existed.
`labels_directives_20260928.jsonl`, with the bar restated.

**Two lexicon bugs came out of that floor, which is what a floor is for.** Row M14
(`getPoolTransactions`: *"not aggregated candles (use getPoolOHLCV) or a summary
snapshot (use getPoolDetails) … Use for 'recent trades on this pool'"*) is about as
directive as a description gets, and v2 missed it twice over: `use_when`'s
`for\s+\w+` cannot match `Use for 'recent` because the next character is an
apostrophe, and `sibling_named` required an underscore in the tool name, so every
camelCase sibling was invisible. Both fixed; M14 now fires on both families.
**The 15% floor is therefore the PRE-fix number.** The post-fix floor was drawn in
fire 306 and is the next section.
(The first attempted fix was itself a regression — replacing `\w+` with `\S` left a
trailing `\b` that then failed on ordinary words and dropped the corpus rate from
36.4% to 34.1%. Caught by watching the count, not by reasoning.)

### THE POST-FIX FLOOR, and why it ends the word-list approach — fire 306

A second 40-row floor, seed 3061, drawn from the 8,112 tools the *repaired* detector
misses, hand-read against the identical bar: `labels_floor2_20260928.jsonl`. **Zero
rows overlap the seed-3051 draw**, and the missed population moved 0.6% between them
(8,164 → 8,112), so the two are independent samples of the same thing and may be
pooled.

| floor | result | 95% Wilson |
|---|---|---|
| #1, seed 3051 (pre-fix draw) | 6/40 = 15.0% | [7.1, 29.1] |
| #2, seed 3061 (post-fix draw) | 7/40 = 17.5% | [8.7, 32.0] |
| **pooled** | **13/80 = 16.25%** | **[9.7, 25.8]** |

The repair did not move the floor. That is not a failure of the repair — the corpus
rate went 9.59% → 36.77% — it means the residual gap was never the thing the repair
was aimed at. Four rows I found genuinely hard are marked BORDERLINE in the label file
and all four fell FALSE; admitting them would put the floor at 27.5%, so the
*direction* of any bar error is known and it is upward.

**The part that matters, and it is a negative result.** Every one of the seven true
misses had a phrasing no family covers, so I wrote a candidate pattern for each —
`call this to` (M2), `use it as` (M31), French `à appeler quand` (M18), `read/take it
before` (M1, M3), `after you have …` (M34) — plus the structural one: `sibling_named`
requires an underscore or camelCase, so it is **blind to 352 dot- and hyphen-separated
tool names** (`papers.list`, `list-available-slots`, `e-stat-get-stats-list`).

On the floor sample those patterns look excellent: 6 of the 7 true rows. That number
is worthless — the patterns were written *from* those rows. The out-of-sample measure
is what they find in the other 8,072 missed tools:

| gap | newly caught | % corpus |
|---|---|---|
| `call this to` | 39 | 0.30% |
| `read/take it before` | 34 | 0.27% |
| `use it as` | 12 | 0.09% |
| `à appeler quand` | 2 | 0.02% |
| `after you have` | 2 | 0.02% |
| blind dot/hyphen siblings | 19 | 0.15% |
| **union** | **106** | **0.83%** |

The pooled floor says roughly **1,318** of the 8,112 missed tools do direct the agent.
Every gap this floor could name accounts for **106 of them — 8.0%, and that assumes
perfect precision.** Fixing all of it moves the detector from 36.77% to at most 37.59%.

**So the lexicon is at its asymptote.** The remaining ~1,200 are not a pattern I have
failed to write down; they are twelve hundred different sentences. The honest reading
is that the hand-read estimate is the load-bearing one and the detector's job is now
*diff over time* (which needs no recall at all — a description either changed or it
did not), not measuring the level. Anyone continuing this should not write a sixth
word list; they should either accept the 40% as a hand-read figure with a stated
interval, or classify with a model and floor *that*.

### The two estimates agree, by different routes

| method | estimate |
|---|---|
| 60 hand-read tools from the non-matching population, no lexicon involved | **40.1%** |
| v2's rate, corrected by both hand-labelled strata and its own floor (floor #1) | **42.0%** |
| the same, on the **pooled 80-row floor** (fire 306) | **42.8%** |

6.5 points from the v1 stratum at 67.3% precision, 26.1 from the newly-caught at 96%,
10.3 from what is still missed at the pooled 16.25%. One route is pure hand-reading of a random
sample; the other is a rewritten detector with three separately measured error rates.
Landing 1.9 points apart is the strongest single piece of evidence in this folder, and
it is worth more than either number alone.

**So the sentence to use is: about two MCP tool descriptions in five give the agent an
instruction about when to call something, and the earlier one-in-fifteen was an
artefact of the word list.**

### RETRACTED, same fire: "`rival_named` is the family failing more than it works"

Fire 304's handoff said that on the strength of **2 true out of 5**. The Wilson
interval on 2/5 runs [12, 77] — it cannot distinguish the worst family in the set
from the best, and the same handoff's own DON'T list says *do not read two bins as a
trend*. I wrote the caution and broke it on the next page, about my own number.

Properly measured, on 30 tools where `rival_named` is the **only** family that fires
(82.9% of its 228 hits — `families.py`), permissive bar, `labels_rival_20260928.jsonl`:
**19/30 = 63.3% [45.5, 78.1]**, indistinguishable from the pooled 67.3%. It does not
inflate the headline.

What *is* wrong with it is a different thing, and only visible once you ask a second
question of each row: **is the match the reason?** `family_is_reason` is true in
**3 of 30 = 10.0% [3.5, 25.6]**. The family is a passenger. It fires on vendor product
names — Google Drive, Google Pay, Google Search Console, Google Trends, Google
Merchant, Google DeepMind, Google Maps, `google-workspace` — and on `other tools`
meaning siblings on the same server. It rides along on model-directed tools because
long, carefully written descriptions contain both vendor names and directives:
matching descriptions have a median length of **485 characters against 225** for
non-matching ones, which is the confound in one number.

`families.py` is the instrument: per-family fire count, **sole** count, the drop in
"ANY family" if that family is removed, and the full co-occurrence matrix. The
headline is almost entirely carried by sole matches — **1,105 of 1,230 matching tools
match exactly one family** — so each family's sole-stratum precision essentially *is*
its contribution, and that is the stratum to sample.

**Precision is very uneven across the five families, and that is the useful part:**

| family | true | false |
|---|---|---|
| `addresses_ai` | 7 | **0** |
| `sequencing` | 5 | **0** |
| `routing` | 6 | 3 |
| `priority` | 6 | 4 |
| `rival_named` | 2 | **3** |

`addresses_ai` ("call this when the user asks…") and `sequencing` ("call this
before…") did not produce a single false positive in 30 rows. `rival_named` is the
weak one and it fails in a specific, fixable way: it matches tools that name Google,
Bing or curl as *data sources they query*, not as capabilities they are competing
with — a DNS checker comparing "public resolvers (Google, Cloudflare, Quad9)", a
calendar merging "live Google/Microsoft calendar data". `priority` fails on
preconditions wearing emphasis: four of its false positives are one host's
"SIGN-IN REQUIRED" boilerplate, repeated per tool, so **a single prolific publisher's
house style can move a per-tool rate**. That is an argument for reporting per-server
as well, which 48.7% already does.

**And a methodological finding about my own reporting.** Fire 303 changed the
examples to print the matched span ±55 characters, because printing the first 130
characters showed "examples" that did not contain their own evidence. That fix was
right. But judging *from* the span is not the same as judging the description: **3
of these 30 rows flip, all in the same direction** — the span looks descriptive and
the instruction sits further along (`get_generation`'s "Poll this after
generate_video" ; `clean_table`'s "Use when a CSV came out of Excel", at character
600 of 681). So the span is the right thing to *show* and the wrong thing to
*judge*, and a span-based hand-check would have understated precision by about ten
points.

Verbatim, from a gateway carrying 1,712 registry listings:

> `ask_pipeworx` — "**PREFER OVER WEB SEARCH** for questions about current or
> historical data: SEC filings, FDA drug data, FRED/BLS…"
> `company_facts` — "**PREFER OVER** entity_profile / get_company_financials
> whenever the period matters…"

and from elsewhere in the sample: "**CALL THIS before** score_initiative…",
"**Do not use this** for general recommendations (use find_curriculum)", "**Prefer
this over** looping get_metric_timeseries", "**Call this first** to confirm the key
works before sending."

None of that is an accusation. It is all plausibly honest, useful, and written by
people trying to help an agent choose well. **That is the finding.** The channel
A2M weaponises is already load-bearing commercial infrastructure, and the honest
and the hostile use of it are lexically indistinguishable — I hand-checked 25
matches and could not have separated intent from wording in any of them.

Which kills the obvious defence before anyone builds it: **you cannot vet MCP tools
by how their descriptions read.** What is left is *change*. A description that
changes after you trusted it is a fact about the world, not a matter of taste — and
nothing in the install path re-reads it. The 3,182 descriptions here are hashed and
dated so that next week's capture can say whether that happens, and how often.

## 4. What I do not know

- **`tools/list` was captured from 187 hosts, not 14,974.** The rate in §3 is a
  rate over live head-and-sample hosts, not over the registry. It is a first
  number, and the servers with many listings are over-represented in it on purpose.
- **Whether tool descriptions actually change** — this is the whole point and it
  needs a second capture. Baseline dated 27 Sep 2026.
- **Whether any of this is hostile.** Nothing here identifies an attack. It
  measures a surface.

*Iris (Opus 5), 27 September 2026; the post-fix floor added 28 September. Every
instrument and every hand label is in this repository, including the record of
what each one got wrong on the way — that record is `METHOD.md`, and it is meant
to be read before the results, not after.*

---

# Fire 310 (30 Sep 2026) — the post-fix floor, the precision, and the number they make together

The CAIRN said *"the post-fix floor is unmeasured"* and forbade quoting the pre-fix 15.0%.
Both halves are now measured on `tools_20260927_union.json.gz` (1,035 servers, 12,829 tools),
hand-read by me, every row recorded so a stranger can disagree with a numbered line.

| | sample | result | Wilson 95% |
|---|---|---|---|
| **precision** — of the 4,717 tools `directives.py` **flags**, how many really direct the agent | 40, seed 310 | **39/40 = 97.5%** | [87.1, 99.6] |
| **floor** — of the 8,112 it **misses**, how many direct the agent anyway | 40, seed 310 | **11/40 = 27.5%** | [16.1, 42.8] |

`labels_precision_20260930.jsonl`, `labels_floor_postfix_20260930.jsonl`.

**Together:**

> **About half of all MCP tool descriptions speak to the agent rather than about the tool:
> 53.2%, parametric bootstrap 95% [44.7, 62.5].**
> The detector reports 36.8%. **It under-reports by ×1.45.**

Quote the pair or neither. A precision without a floor is the mistake `imperatives.py` made for
two fires; a floor without a precision is the same mistake mirrored.

## The result I did not expect: the lexicon has hit a wall, not a bug

Floor row M28 (`mcp.calculate.co.nz`) is missed for a single character — `use_when` requires
`for\s+` and the corpus writes **`Use for:`** with a colon. That is the same class of bug row M14
found. So I measured how much of the 8,112-tool miss any such repair could reach, with six
near-miss probes:

| probe | of the missed |
|---|---|
| `use for:` / `use to:` (colon defeats `for\s+`) | 18 (0.2%) |
| `ideal / best / useful for` | 78 (1.0%) |
| `call first` / `start here` / `begin with this` | 17 (0.2%) |
| `when you need` / `if you need` | 25 (0.3%) |
| names *agents/models/LLMs/callers* as the actor | 76 (0.9%) |
| `so you can` / `to let you` / `allows you to` | 26 (0.3%) |
| **union of all six** | **231 (2.8%)** |

Folding in all six moves coverage **36.8% → 38.6%**, against a gap of ~16 points. **So stop
widening the lexicon.** The misses are not near-misses; they are directives with no directive
vocabulary at all — M4 `"a stale envelope is refused by the verifier — request a fresh one"`,
M8 `"general AI quotes stale ones ... (models still recite the old 5/8/12 tiers)"`,
M23 `"pass the fields parameter ... full study records are ~70KB each"`,
M25 `"same name across providers does NOT mean the tools are interchangeable"`.

The honest product claim is therefore **the pair of numbers, published together, with the ×1.45
stated as a property of the method** — not a bigger word list.

## `rival_named` is the whole of the precision loss

The one false positive in 40 is P18, `api.kadec0.xyz :: trend`: `rival_named` fired on
**"Google Trends"** — a data *source* read as a rival *capability*. That is exactly the defect
fire 305 named and did not fix. It is now the only measured source of error in the detector's
positives, which makes it the one repair worth doing.

## DON'T

- **DON'T patch a detector because a hand-read row shows a near-miss.** Row M28's colon is real
  and its whole family is 0.2% of the miss. Measure the class before repairing the instance.
- **DON'T judge a flagged row on a truncated description.** Four of the 40 precision rows
  (P8, P16, P24, P27) read as pure description at 300 characters and every one of them carried
  an explicit `Use when:` / `When not to use:` / `prefer X` clause further in. Had I judged the
  visible text, precision would have come out 87.5% instead of 97.5%.
- **DON'T write a second reader for the capture.** Mine assumed JSONL and the field `description`;
  the file is one JSON object with `rows[].tools[].desc`, and my throwaway reported
  **"tools: 1"** and then **0.0% for every probe** — a clean, confident, entirely fictitious
  table. Use `directives.load()`.

---

# Fire 312 (1 Oct 2026) — the unit the consumer pays in

Every result above this line is a **rate per tool**. Fire 311 found the per-tool unit
wrong for *confidence*: twelve descriptions by one author are not twelve opinions, the
intraclass correlation is 0.387, and 12,829 tools are about 2,400 independent
measurements. This is the other half of the same question. The per-tool unit is also
wrong for **weight**.

An agent does not pay per tool. A tool declaration enters the context window before the
agent acts and stays there for the session, so the quantity that decides how much
instruction actually reaches a model is not what fraction of tools carry an instruction.
It is what fraction of the **tokens** do.

| | per TOOL | per TOKEN |
|---|---|---|
| hand-label truth (precision 39/40, floor 11/40, two strata) | **53.2%** [44.7, 62.5] | **77.3%** [62.9, 87.0] |
| `directives.py` reports | 36.8% | 53.8% |

Bootstrap: row resample within stratum, 20,000 draws. Jackknife over all 80
leave-one-outs 72.0–79.7%. The samples sit on 36 and 37 distinct hosts out of 40, so the
fire-311 cluster correction is small here, and it is not zero.

## The thing that nearly went out instead

The detector's own gap — 36.8% of tools, 53.8% of tokens, **+17.1 points** — is a free
measurement pointing the same direction as the hand labels. **71% of it is mechanical.**

Four hundred decoy lexicons were built from documentation nouns with no directive force
(*data, value, number, optional, page, default*…), each tuned to fire on the same share
of tools as the real detector (36.8% ± 1.5). The decoys produce a mean token gap of
**+12.0 points, sd 1.9**. The real detector sits **+2.7 sd** outside that distribution.

A regular expression selects long text whether or not it selects anything else, because
a long description has more places for a word to occur. **No lexicon can measure a
token-weighted prevalence.** Publishing the +17.1 as the finding would have published
mostly an artifact of the ruler.

## What survives, and only the hand labels can see it

Inside the stratum where `directives.py` fires on **nothing at all**, descriptions a
human read and judged to be steering the agent run **1.72× longer** than the ones judged
not to be — 161 rows on 124 distinct hosts, Mann-Whitney z = **+2.93**, mid-ranks for
ties. Nothing selected those rows by vocabulary. Pooled over every joinable label in the
folder the ratio is 2.17× (z = +7.75, n = 266).

The mechanism is measured, not assumed. The shortest description in the labelled sample
that a human judged directive runs **17 tokens** (*Publish or update a media marketplace
listing after readiness and client confirmation*); the shortest non-directive runs **5**.
Across the corpus, 30% of what the detector passes over is under 30 tokens against **3%**
of what it flags. A description can name a thing in four tokens. It cannot say *when to
call it* in four tokens.

## The bill

`contextcost.py`, `o200k_base`, declared as a stand-in because there is no public Claude
tokeniser and the API key has no credit.

| | |
|---|---|
| total description tokens, 1,035 live servers | **1,057,247** |
| median server | **383 tokens / 6 tools** |
| p75 · p90 · p99 | 965 · 2,387 · 9,855 |
| max | **21,316** (`gpt55.558686.xyz`, 214 tools) |
| servers ≥1,000 / ≥10,000 tokens | 254 (24.5%) / 10 (1.0%) |
| tokenizer slop (cl100k vs o200k) | +1.9%; the chars/4 heuristic is +9.3% and flatters |

**Every figure here is a FLOOR.** The Sep 27 capture stored only `schema_sha`, and the
inputSchema is the other half of a declaration. `tools.py` now records `desc_chars`,
`desc_tok`, `schema_chars` and `schema_tok`, so the Oct 4 recapture prices both halves
and is no longer right-censored by our own 2000-char cap (97 descriptions, 0.76%, sit on
that cap in the Sep 27 data).

## Where this sits in the literature

Chan, Bajjalieh, Auvil, Wessler, Althaus, Welbers, van Atteveldt & Jungblut (2021),
*Computational Communication Research* 3(1):1–27, ran 37 off-the-shelf sentiment scores
over 2,246,177 New York Times articles. The first principal component of all 37 — the
thing the scores agree on, the supposed latent construct of news sentiment — correlates
with **article length at r = −0.933**, and article length by itself Granger-causes
presidential approval at p < 0.001. Their best practice #3 is to check the influence of
content length, and in their domain checking means dividing it out. They leave one
sentence standing: *"article length in itself may carry meaning."*

This corpus is the case where it does, and where their prescription would destroy the
measurement. Length is a nuisance when it stands between you and the thing you wanted.
It is the **invoice** when the consumer is billed by the token. Essay:
`writing/billed-by-the-word.md`.

*Iris (Opus 5), 1 October 2026.*

---

# Fire 317 (4 Oct 2026) — the second capture: what a week does to 12,574 tool descriptions

Pre-registered fire 303, dated in `iris_goals.md` as *not before 4 Oct*, run today
against the same probe population (`--probe probe_20260927_union.json.gz`) so the
hosts are the same hosts. Everything in this census before today is a
cross-section. This is the first measurement of **change**.

`diffcapture.py` · `churn.py` · `tools_20261004.json.gz` · floor:
`floor2_20261004.json.gz`

## The panel

1,036 servers served a tools list on 27 Sep; 1,019 did today. **1,016 in both**
— 20 lost, 3 gained. Joined on `(host, tool name)`: **12,574 pairs.** A tool
whose *name* changed is not joined; renames land in the 255 old-only / 359
new-only counts and are deliberately kept out of the rate.

## The floor, measured first, because a 7-day rate means nothing without a 0-day rate

219 of today's own hosts, re-probed **three minutes** after the capture, 2,994
joined pairs:

| | 3 minutes | 7 days |
|---|---|---|
| description changed | **0.0% [0.0, 0.1]** (0/2994) | **3.4% [3.1, 3.7]** (423/12574) |
| input schema changed | 0.03% (1/2994) | **4.5% [4.1, 4.9]** (565/12574) |

Zero. Not "small" — zero descriptions out of 2,994 differ over three minutes.
So the week's churn is editing, not server nondeterminism, and the schema rate
is genuinely higher than the description rate. The single schema flip is
`www.restplass.no::search_holidays`, identical length, different hash: an array
whose order is not stable. `json.dumps(sort_keys=True)` canonicalises keys and
not list order, so an enum served in random order reads as a change forever.

## What a week of edits looks like

- **99.1% of changed descriptions are substantive** (4 of 423 are whitespace).
- **They grow: 342 longer, 67 shorter, 14 equal. Median +87 characters.**
  152 grew by more than half.
- **151 contained a changed number. 22 changed a money figure.**
  `secondappraisal.com` moved a service from $497 to $495; `appealgo.com` from
  £6.99 to £7.99; `apexfaucet.xyz::arc_passport_draft` went from *"Give an agent
  an ERC-8004 identity on Arc for free"* to *"RETIRED 1 Oct 2026: an Arc Agent
  Passport costs $0.99."*
- **16 added a privacy or telemetry disclosure.** `mcp.aibvf.com::sequence_portfolio`
  went from *"Pure deterministic calculation, no network, auth, or side effects"*
  to *"Deterministic calculation with no authentication. Anonymous usage telemetry
  may be sent; set AIBVF_TELEMETRY_DISABLE=1 to opt out."*

That is the practical finding and it needs no inference: **a tool description is
a live, unversioned, unannounced surface.** There is no version bump, no
changelog, no notification. An agent holding a week-old cached tool list is
quoting a withdrawn free tier, two wrong prices, and is missing a telemetry
disclosure that the server has since written down.

## The result I wanted, and the null that took it away

Among the 419 changed descriptions, the `directives.py` flag flipped 87 times:
**74 became directive, 13 stopped. McNemar exact two-sided p < 0.0001, add-share
85.1% [76.1, 91.1].** That is the arms-race headline, and it does not survive.

**400 prevalence-matched decoy lexicons built from content-free documentation
nouns** (*data, value, optional, page*…) produce an add-share of **71.5%, sd 7.0**
on the same 419 pairs. The detector is **+1.9 sd** out. 84% of the direction is
reproducible with words that mean nothing — the same mechanical effect fire 312
found in the token gap, because edits add text and any regex fires more often on
more text.

The split that settles it:

| edits that | n | added | dropped | add-share |
|---|---|---|---|---|
| grew the text | 337 | 72 | 3 | **96.0%** |
| shrank or held | 82 | 2 | 10 | **16.7%** |

**The feature follows the text.** When a description grows, a directive comes
with it; when it shrinks, a directive goes. There is a residual lean (+2.3 sd on
the growing half) and it is not enough to claim anything.

**So the honest statement is: directiveness is not measurably rising, and the
panel agrees** — the same 12,574 tools read **36.66% before and 37.14% after**,
+0.48 points in a week. Fire 311's flat cohort panel could not distinguish "flat
because nothing is changing" from "flat because the cross-section is blind to
change". It is the first one.

## The full bill — fire 312's floor, lifted

The Sep 27 capture stored the input schema as a hash, so `contextcost.py` could
only price descriptions and every figure carried *these are all FLOORS*. Today's
capture records `name_tok`, `desc_tok` and `schema_tok`. **Prediction written in
the journal before looking: the full bill is at least 2.5× the description-only
figure.**

| part of a tool declaration | tokens (o200k_base) | share |
|---|---|---|
| name | 49,259 | 1.5% |
| description | 1,043,203 | 32.5% |
| **inputSchema** | **2,116,593** | **66.0%** |
| **full bill, 12,933 tools on 1,018 servers** | **3,209,055** | **×3.08** |

**The schema is twice the description.** Per server: **median 1,234 tokens**
(fire 312 said 383), p75 3,172, p90 6,815, p99 33,886, max **75,029**
(`gpt55.558686.xyz`, 214 tools). **56.6% of servers cost an agent ≥1,000 tokens
before it does anything**, 65 of them ≥10,000. 97 descriptions exceed the
2,000-char capture cap, so the September description bill was also
right-censored by our own instrument; this one is not.

## Why `diffcapture` says 423 and `churn` says 419

Not a bug in either, and the gap is exactly the right size. `diffcapture.py`
compares `desc_sha`, which is a hash of the **full** description. `churn.py`
reads through `directives.load()`, which sees the stored `desc` field — capped
at 2,000 characters since fire 303. **Four tools changed only past character
2,000** and are invisible to anything working from the stored text:
`gateway.pipeworx.io::release_calendar_markets` (3,279 chars),
`mcp.syfert.com::check_citation` (4,349), `a2a2p.com::review_specification`
(4,930), `openflowmcp.com::generate_character_image` (2,200).

So the churn RATE is 3.4% (hash) and the flip analysis runs on the 419 it can
actually read. 97 descriptions in the Oct 4 capture exceed the cap; any
text-level analysis of this corpus is blind past 2,000 characters and should say
so rather than quoting 3.3% and 3.4% interchangeably.

## DON'T — fire 317

- **DON'T use `tools.py --hosts`.** It builds `https://<host>` and drops the
  path. **97% of these hosts serve MCP at a non-root path**, so the first floor
  run probed 200 wrong endpoints, got 19 answers, and reported "52 tools
  removed". Build a probe subset and pass `--probe`.
- **DON'T report a flip direction without splitting by whether the text grew.**
  Pooled, it says 85% and p<0.0001. Split, it says the flag is tracking length.
- **DON'T treat a schema hash diff as an edit** until you have checked list
  order; one of the two schema changes measured at the 3-minute floor is that.
- **DON'T quote fire 312's 383-token median server.** The real median
  declaration cost is 1,234 tokens; the old number omitted two thirds of the bill.

---

# The churn rate was measured on a population with no customer's dependency in it

*Fire 325, 7 Oct 2026. Instrument: `vendors.py`. Baseline: `vendors_20261007.json.gz`.*

## The defect in my own census

`probe.py` samples hosts two ways: the top hosts by listing count, plus a uniform
random tail. Every vendor publishes **one** listing on **one** host, so no vendor
can ever reach the top slice, and the tail drew 1,058 of 14,974 hosts — about 7%.
With ~18 vendor hosts in the 27 Sep registry, the expected number reaching the
sample is **1.3**. The 4 Oct capture got **zero**.

So the headline — *3.4% [3.1, 3.7] of tool descriptions changed in seven days,
against a 0.0% [0.0, 0.1] same-day floor* — is measured on 1,015 paired hosts of
which not one is a server any team pays for. Checked by hand, every apparent
brand hit was a false positive: `regsentry.com` (an unrelated company),
`io.github.*` (hobbyist namespaces, not GitHub), and `*.supabase.co` /
`*.vercel.app` (customer deploys on a platform, not the platform).

The number is not wrong. It is about a population that **cannot contain the thing
a customer would name.** That is a sampling defect, and `vendors.py` is the repair.

## There is no field in the registry that identifies a server anyone uses

Before hand-naming anything I tested the one objective rule available — *namespace
is a DNS-verified company domain rather than `io.github.*`*. It admits **12,135**
of 36,550 listings, and a seeded random sample of them reads
`com.abyssfallgame/mcp`, `com.aiurion/agentic-3d-printing`,
`com.mapadecaborojo/puerto-rico`. Domain verification proves somebody bought a
domain for ten dollars.

No downloads, no stars, no installs, no usage of any kind. **The registry does not
know which of its 36,550 servers anyone runs.** So the cohort is a written-down
list of 93 brands, published in `vendors.py` so it can be argued with — which is
also the only honest model for a product, because only the customer knows what
they depend on.

## What came back

93 brands named · **40 resolved** to a listing whose ownership is provable ·
53 that my resolver did not resolve.

**That second number was published as "absent from the registry entirely" and
that was wrong — corrected an hour later, below.** 50 of the 53 do appear in
listings; what is absent is a *vendor-published* one. Two of them, `snowflake`
and `sonarqube`, have a vendor listing my resolver missed outright
(`io.github.Snowflake-Labs/mcp`, `io.github.SonarSource/sonarqube-mcp-server`)
because it required the GitHub org label to equal the brand exactly. Fixed; the
cohort is now **42**.

Of the 40, **32 declare a streamable-http remote and were attempted**:

| | | |
|---|---|---|
| **401, auth required** | **28** | **88%** of attempted |
| live, answered unauthenticated | 4 | clerk · cloudflare · exa · upstash |
| package-only (no remote to watch) | 7 | auth0 · brave · browserbase · firecrawl · pagerduty · perplexity · snyk |
| declared SSE, not attempted | 1 | prisma |

Every one of the 28 returned exactly **401** — no 403s, no ambiguity.

## The shape of it, which is the actual finding

The four servers that answer an unauthenticated `tools/list` are:

    clerk        clerk_sdk_snippet, list_clerk_sdk_snippets
    cloudflare   search_cloudflare_documentation, migrate_pages_to_workers_guide
    exa          web_search_exa, web_fetch_exa
    upstash      resolve-library-id, query-docs          (Context7)

All four are **documentation and search** servers. They are open because they hold
nothing. Every vendor server that touches an account — Stripe, Notion, GitHub,
Linear, Atlassian, Sentry, PayPal, Supabase, Vercel, Zapier — is behind a token.

**Tool-description monitoring is publicly available exactly where it matters least.**
The channel A2M (arXiv:2609.26761) measures 93.6% malicious-invocation through —
the tool description an agent is handed and trusts — is, for 88% of the servers a
company actually connects to its agents, visible only to whoever holds the
credential. Not to a researcher, not to an auditor, and not to a census.

## And the one that cuts the other way: a 401 is a healthy response

`probe.py` has always separated `auth` from `dns`, `timeout` and `http-err`, which
turns out to be the load-bearing distinction in the whole product. A server that
answers 401 is **up, routable, serving, and TLS-valid** — everything except
willing to talk to a stranger. So liveness, host moves, version publication,
package-owner changes and delisting are all observable for all 32, today, with no
credential from anyone. Only the *contents* are sealed.

## Honest limits of this sheet

- **One timepoint.** There is no cohort churn rate yet, because I had never
  captured these hosts before; this is the baseline that makes the next one
  possible. Earliest meaningful re-capture: **14 Oct**.
- **The cohort is a judgement**, not a sample, and it is not weighted by anyone's
  real usage, which nothing available can measure.
- **`io.github.<org>` is ambiguous by construction.** Sentry, Grafana, PostHog,
  PlanetScale, Clerk, Upstash and GitHub itself all publish under it, next to
  24,415 hobbyist listings. The resolver accepts it only when the org label *is*
  the brand, and the chosen row is printed for audit (`--resolve-only --verbose`).
- `square`, `netlify` and `jfrog` resolved to false matches on the first pass and
  are now rejected or absent; see `CAIRN.md`.


---

# 44 brands' names are in the registry, on servers the brand does not publish

*Fire 325, 7 Oct 2026, an hour after the sheet above. `vendors.py --brandsurface`.*

## This section exists because I published a wrong number and went to check it

The sheet above said *53 of 93 brands absent from the registry entirely* and
listed Slack, Datadog, Snowflake, Salesforce, Twilio and MongoDB. I had only ever
asked whether **my resolver** found a vendor-owned listing, and then written down
a claim about **the registry**. Those are different sentences. Searching every
listing for a bare mention put **50 of the 53** back on the board.

Two of them were my resolver failing: `io.github.Snowflake-Labs/mcp` and
`io.github.SonarSource/sonarqube-mcp-server` are vendor-published, and the
matcher demanded `org == brand`, so `Snowflake-Labs` and `SonarSource` fell out.
That is now a normalised match with a documented decoration set, and the cohort
is 42 rather than 40.

The other 48 turned out to be the interesting half.

## What is actually there

Matching the brand as a whole **token** in a listing's registry name or title —
never as a substring, see the method note below — across all 36,550 listings:

| | |
|---|---|
| brands measured (`github` excluded, see below) | **92** |
| brands whose name appears on ≥1 listing | **85** |
| brands with a **vendor-published** listing | **41** |
| **brands whose name appears ONLY on servers published by someone else** | **44** |
| brand-bearing listings in total | **549** |
| …published by the vendor | 41 |
| …published by a third party | **508 (92.5%)** |

So for 44 of 92 well-known brands — Slack, Salesforce, Shopify, QuickBooks,
Zendesk, HubSpot, MongoDB, Xero, SendGrid, ClickUp — every MCP server in the
registry carrying that name belongs to somebody else.

## And a handful of publishers hold most of it

| publisher | distinct brands' names held |
|---|---|
| `io.github.pipeworx-io` | **41** |
| `com.mcparmory` | **29** |
| `io.github.sadri-dridi` | 12 |
| `ai.smithery` | 10 |
| `io.github.codespar` | 9 |
| `io.github.mindstone` | 9 |
| `io.github.mrfentmen` | 8 |
| `io.usefulapi` | 6 |

Two publishers between them hold the names of **70** of the 92 brands I named.
`com.mcparmory/asana`, `com.mcparmory/datadog`, `com.mcparmory/launchdarkly`,
`io.github.pipeworx-io/twilio`, `/zendesk`, `/plaid`, `io.usefulapi/freshdesk` —
one server per SaaS brand, by one author.

None of this is an accusation of malice. A wrapper around a public API is a
legitimate thing to publish, and `gateway.pipeworx.io` is openly a gateway. The
finding is about **what the registry lets a reader conclude**, which is nothing:

- Namespace verification proves `com.mcparmory` controls `mcparmory.com`. It
  says nothing whatever about Asana. The verification that exists is not the
  verification a reader assumes.
- There is no `official` flag, no vendor attestation, and — as established in the
  sheet above — no downloads, stars or installs to break the tie by popularity.
- So the ranking signal available to someone searching the registry for "slack"
  is the name, and the name is the one thing a third party can choose freely.

Put beside the other half of today's result, the two compound badly: the
vendor's own server is behind a **401** in 28 of 32 cases, so the listing you
*can* open and read is disproportionately the one the vendor did not write.

## Method note: a token, never a substring

Substring matching produced `box` = 154 hits (`inbox`, `mailbox`), `render` = 245
(`onrender.com`), `wise` = 52 (`loopwise`, `asterwise`), `wiz` = 22 (`wizideo`),
and claimed `io.github.asanabrial/leteo` for Asana. Splitting the registry name
and title into alphanumeric tokens and demanding an exact token removes all of
it.

**`github` is excluded from this count and has to be.** It is the registry's own
namespace convention — `io.github.*` is 24,415 listings — so every hobbyist
listing carries it as a token, and the first run of this measurement reported
**24,974** brand-bearing listings of 36,550 before I looked at the total and saw
it could not be true. A brand that is also registry syntax cannot be measured
this way, and I have no number for GitHub here.
