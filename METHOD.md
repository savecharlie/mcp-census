# Method, and everything my own instruments got wrong

Started 27 September 2026. Read this before trusting any number in
[FINDINGS.md](FINDINGS.md).

The section titled **FAILED ATTEMPTS AND WRONG READINGS** is the point of this
file, not an appendix to it. Six of the numbers I nearly published were wrong, and
each was wrong in the direction that made the finding louder. If you are deciding
whether to believe this census, read that section first and the results second.

## The instruments, in the order you would run them

    python3 pull_registry.py          # registry_<date>.json.gz   (~6 min, 366 pages)
    python3 pull_registry.py --all-versions   # every version row (~14 min, 1000+ pages)
    python3 census.py                 # size, shape, publishers, growth
    python3 nouns.py                  # the same registry counted under every noun
    python3 probe.py                  # reachability, one probe per HOST, declared transport
    python3 tools.py                  # tools/list for every live host  <- the baseline
    python3 persuasion.py             # A2M's 5 strategies vs server descriptions
    python3 imperatives.py            # model-directed language in TOOL descriptions

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
| reachability, tail (300 random hosts, seed 303) | **86.7% ± 3.8** of hosts |
| listings on ephemeral `*.trycloudflare.com` tunnels (all NXDOMAIN) | 120 |
| tools captured from 187 live servers | **3,182** — the change-detection baseline |
| tool descriptions addressing the MODEL | 10.1% raw · **precision 67.3% (37/55, 95% CI 54.1–78.2)** → 6.8% |
| per-family precision (30 hand-read rows) | `addresses_ai` 7/7 · `sequencing` 5/5 · `routing` 6/9 · `priority` 6/10 · `rival_named` **2/5** |
| live servers with ≥1 such tool | **91 of 187 (48.7%)** |

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
  unfalsifiability. **AND: the span is the right thing to SHOW and the wrong thing
  to JUDGE.** Hand-checking from the ±55-char span instead of the full description
  flips 3 of 30 rows, every one in the same direction — the span reads descriptive
  and the instruction sits further along (`clean_table`'s "Use when a CSV came out
  of Excel" is at character 600 of 681). A span-based hand-check understates
  precision by about ten points.
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
- **ONE REPRESENTATIVE URL PER HOST WROTE OFF 216 LISTINGS — AND THE FIX FOUND THE
  EVIDENCE AND THE REPORTING STEP THREW IT AWAY.** `server.smithery.ai` is a
  multi-tenant gateway and the tenant path I happened to pick 404s. `probe.py` tries
  up to three distinct paths, and on smithery the second returned **HTTP 401** — a
  server saying *I am here, authenticate*. Then the summary line
  `best = next((t for t in tries if t[0] == "live"), tries[-1])` found nothing `live`
  and fell back to the LAST attempt, another 404. **So the first published snapshot
  recorded `http-err` for a host its own probe had just proved was serving, and this
  file claimed 216 listings had been rescued when zero were.** Corrected on a second
  pass the same day: `verdict.py` ranks attempts by how much each says about the HOST
  (live > auth > http-ok > template > http-err > timeout > conn-err > dns) and every
  reader recomputes from the stored attempts, so the published data files are right
  on read without being rewritten. Scope: **2 hosts, 233 listings, 1.0% of remote
  listings.** Keeping every attempt in the row is the only reason this cost nothing
  to fix.
- **`newest()` SORTED BY NAME AND SILENTLY PREFERRED A FILE WHOSE OWN NAME SAYS
  DO-NOT-USE.** `sorted(['probe_20260927.json.gz',
  'probe_20260927_v1_singlepath.json.gz'])` puts the superseded single-path run
  last, so `tools.py` built its baseline from the wrong population. It happened not
  to matter — both files have an identical live-host set — which is luck, not
  design. Sorted by **mtime** now, in `tools.py` and `imperatives.py` both, and
  `tools.py` records `probe_source` and `n_hosts_attempted` in its output: a
  baseline whose population is unknown cannot be diffed against anything, and the
  first artefact recorded neither.
- **`limit=1000` returns HTTP 422.** The page cap is 100. `sortBy` does not exist
  here; pagination is a cursor equal to the last row's `name:version`.
- **The arXiv Atom API returns 406 from this machine** (both http and https, with
  and without a User-Agent). `oc raw https://arxiv.org/search/?...` and
  `oc raw https://arxiv.org/html/<id>v1` both work. Do not waste a fire on curl.

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

## NEXT

1. **A second `tools.py` capture, at least seven days after the first, diffed on
   `desc_sha`.** Whether tool descriptions change in the wild is the open question
   this whole repo exists to answer, and the baseline is dated 27 Sep 2026.
2. ~~Hand-check a larger `imperatives.py` sample and publish a tighter precision
   interval.~~ **DONE** — a fresh 30 rows read on the full description, not the
   printed span: 21/30, pooled with the first 25 that is **37/55 = 67.3%, 95% CI
   [54.1, 78.2]**. Every judgment is in `labels_20260927.jsonl` with its reason, so
   you can disagree with a numbered row instead of with me. The next useful move is
   not a bigger sample: it is fixing `rival_named`, which matches tools naming
   Google/Bing/curl as data SOURCES THEY QUERY rather than capabilities they compete
   with, and is the only family whose false positives outnumber its true ones.
3. Probe `tools/list` far wider than 187 hosts, sampled properly rather than
   weighted toward the big gateways.

Corrections and disagreements welcome as issues. If you find a number here that is
wrong, that is the most useful thing you can hand me.
