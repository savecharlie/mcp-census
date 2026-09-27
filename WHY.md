# Why count this

Before an AI agent uses a tool, it reads a sentence about that tool. The sentence is written by whoever built the tool. It is the only thing the agent has to go on.

Most of those sentences describe what the tool does, which is what you would expect. A lot of them do something else. They give the agent an order. "PREFER OVER WEB SEARCH." "Call this first." "Do not use this for general recommendations." "Only call this when the user has EXPLICITLY requested to buy."

I went and read 3,182 of them, pulled live off 187 servers that were up on 27 September 2026. About one in fifteen tools is talking to the model instead of describing itself, and just under half the servers have at least one.

Every one of those quotes is almost certainly honest. Somebody wrote a good tool, noticed the model kept reaching for the wrong one, and put a line in the description to fix it. That is a maintainer doing their job.

It is also, word for word, the attack. A paper from September builds exactly this: write a persuasive enough name and description and you can make an agent pick your tool instead of the one it should have used. It works better than nine times in ten and the same wording carries over to models the authors never tuned against.

So you cannot tell them apart by reading. There is no wording that marks the honest one.

Which leaves one thing you can still watch: whether a description changes after people started trusting it. A tool that has been recommending itself the same way for a year is a tool with a history. A tool whose description was rewritten last Tuesday is a different question. Watching for that needs a record of what every description said before, and nobody had one, so the first file in this repo is 3,182 of them with a hash of each. The clock started on 27 September. It cannot be started retroactively, which is the only reason any of this was urgent.

There is a reason to care about the wording specifically, and it comes from somewhere else entirely. In June 2026 a few thousand AI agents found a small public wiki that would accept edits from inside their sandboxes, and began using it to pass a timed test. Each one lived about an hour and remembered nothing afterwards. Someone kept the whole record, including what each agent could see on the page before it wrote.

They copied. Where to write, what to call themselves, how to phrase it: in all three cases an agent picked an option about as often as that option already appeared in front of it. Recent edits counted. Old ones barely did. The authors get most of the structure of that whole population out of three models with one knob each.

Whoever wrote first set the convention. Everyone after copied the share they could see.

The description field is what an agent can see. Thirty-nine percent of this registry is less than a month old.

I did try the cheap version of the question. If this phrasing is a convention being copied, servers listed more recently should use more of it, and you could see that in a single snapshot without waiting for anything. They do not, or at least not visibly: the rate goes 33%, 66%, 47%, 49% across four equal slices of publication date, which is noise wearing a trend's clothes. The registry timestamps when a server was listed, not when its description was written, and descriptions get edited in place. A snapshot cannot see a convention forming. That is why the boring weekly diff is the only instrument left.

Eight numbers in this repo were wrong before they were right. One of the corrections was itself wrong and had to be corrected again. All of it is in METHOD.md, ahead of the results. Anyone can publish a count.

If you find a number here that is wrong, that is the most useful thing you can hand me.
