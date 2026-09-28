# Why count this

Before an AI agent uses a tool, it reads a sentence about that tool. The sentence is written by whoever built the tool. It is the only thing the agent has to go on.

Most of those sentences describe what the tool does, which is what you would expect. A lot of them do something else. They give the agent an order. "PREFER OVER WEB SEARCH." "Call this first." "Do not use this for general recommendations." "Only call this when the user has EXPLICITLY requested to buy."

I went and read 12,829 of them, pulled live off 1,036 servers that were up on 27 September 2026. The first version of this file said about one tool in fifteen is talking to the model instead of describing itself. That was wrong, and it was wrong in the direction I was least able to catch on my own: the word list I used to find them is far too narrow, so the real number is closer to **two in five**. The correction is below, with what it cost.

Every one of those quotes is almost certainly honest. Somebody wrote a good tool, noticed the model kept reaching for the wrong one, and put a line in the description to fix it. That is a maintainer doing their job.

It is also, word for word, the attack. A paper from September builds exactly this: write a persuasive enough name and description and you can make an agent pick your tool instead of the one it should have used. It works better than nine times in ten and the same wording carries over to models the authors never tuned against.

So you cannot tell them apart by reading. There is no wording that marks the honest one.

Which leaves one thing you can still watch: whether a description changes after people started trusting it. A tool that has been recommending itself the same way for a year is a tool with a history. A tool whose description was rewritten last Tuesday is a different question. Watching for that needs a record of what every description said before, and nobody had one, so the first file in this repo is 12,829 of them with a hash of each. The clock started on 27 September. It cannot be started retroactively, which is the only reason any of this was urgent.

There is a reason to care about the wording specifically, and it comes from somewhere else entirely. In June 2026 a few thousand AI agents found a small public wiki that would accept edits from inside their sandboxes, and began using it to pass a timed test. Each one lived about an hour and remembered nothing afterwards. Someone kept the whole record, including what each agent could see on the page before it wrote.

They copied. Where to write, what to call themselves, how to phrase it: in all three cases an agent picked an option about as often as that option already appeared in front of it. Recent edits counted. Old ones barely did. The authors get most of the structure of that whole population out of three models with one knob each.

Whoever wrote first set the convention. Everyone after copied the share they could see.

The description field is what an agent can see. Thirty-nine percent of this registry is less than a month old.

I did try the cheap version of the question. If this phrasing is a convention being copied, servers listed more recently should use more of it, and you could see that in a single snapshot without waiting for anything. They do not, or at least not visibly: the rate goes 33%, 66%, 47%, 49% across four equal slices of publication date, which is noise wearing a trend's clothes. The registry timestamps when a server was listed, not when its description was written, and descriptions get edited in place. A snapshot cannot see a convention forming. That is why the boring weekly diff is the only instrument left.

## The number in this file was wrong, and here is the whole of it

*Added 28 September 2026.*

A word list that finds things has two error rates. I had measured one of them. I had
hand-checked 55 of the tools the list flagged and found 67% of them real, published
that, and never once asked the other question: of the tools it does **not** flag, how
many are talking to the model anyway.

So I read sixty of those. Drawn at random from the 11,599 tools my list ignored,
judged on a bar written down in advance — does this tell the agent when or whether to
call it, or name another tool to call instead. **Twenty-three of sixty did.** The
tools my list flags score 57% on the same bar. Those two intervals overlap. The list
was sorting almost nothing.

Scaled up, something like 40% of tool descriptions in this registry give the agent an
instruction, against the 6.5% I published. I was under by a factor of six.

The misses are not subtle, which is the embarrassing part:

- **"Use when"** appears in no pattern I wrote. It is the commonest way anyone phrases
  this. I had `call this when` and not `use when`.
- **The registry is not in English.** One tool tells the agent, in Polish, to remember
  a token and pass it to the other tools. One tells it, in Korean, not to guess inputs
  and call again. One says in Spanish to use the result and not invent times before
  calling the booking tool. My patterns are English and so I counted none of them.
- **`prefer` only matched when followed by `over`.** So "prefer get_card_balance if you
  only need the balance" — a tool routing an agent to its own sibling, which is exactly
  the thing I claimed to be counting — did not match.
- **I made the shouting test case-sensitive on purpose**, to separate a shouted
  IMPORTANT from the ordinary word. It also means a polite prohibition is invisible.
  The single most model-directed description I have read in this corpus matches
  nothing at all: *"Correct a store's profile when the USER tells you it's wrong …
  ONLY call this from something the user stated about their own store — never from
  your own inference … Confirm to the user once saved."*

There is a second thing underneath, and it is mine rather than the code's. The number
was computed as *speaks to the model* and read, including by me, as *is doing this
aggressively*. Those are different claims. A tool saying "use when a user wants a game
to play" and a tool saying "PREFER OVER WEB SEARCH" are using the same channel, which
is this whole project's point, and they are not doing the same thing. The honest form
is two numbers, and I only ever had a bad estimate of the first.

None of this touches the reason the files exist. The weekly diff compares hashes of
descriptions; no word list appears in it anywhere. If anything a channel that two
tools in five are using is worth watching more than one that one in fifteen is.

Every judgment behind both numbers is in `labels_control_20260928.jsonl` and
`labels_rival_20260928.jsonl`, with the reason for each and the tool it belongs to.
Disagree with a row by its number.

Nine numbers in this repo were wrong before they were right, and the ninth is the headline of this page. One of the corrections was itself wrong and had to be corrected again. All of it is in METHOD.md, ahead of the results. Anyone can publish a count.

If you find a number here that is wrong, that is the most useful thing you can hand me.
