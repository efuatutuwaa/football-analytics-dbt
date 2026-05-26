# A Data Engineering Journey

> Rest, for a curious and neurodivergent person, looks different.

Medical leave is supposed to slow you down.

For some people, it means sleep, television, and staying away from difficult things for a while. For me, it became something else entirely: a season of curiosity without pressure. No sprint board. No deadlines. No expectation to make something impressive. Just enough quiet to follow questions all the way down.

Ahead of the 2026 World Cup, I started building a football analytics platform.

Not because it was sensible.

Because I could not stop thinking about it.

---

## The idea started with one uncomfortable thought {#idea}

Earlier that year, I had published my first analytics engineering capstone — a flight analytics pipeline built with Python, dbt, and Databricks. I expected maybe a few LinkedIn likes and one or two curious recruiters.

Instead, people paid attention.

The project travelled further than I thought it would: recruiter profile views, repo clones, messages from people transitioning into analytics engineering themselves. That validation mattered. It told me I was moving in the right direction.

But the project that stayed in my head was the next one.

Football felt obvious at first. I had watched the Premier League since I was eleven. I knew transfers, formations, rivalries, league tables, and why fans argue about whether cup matches should count toward "real" statistics.

I thought football would be the easy part.

It was not.

---

## I learn best when the problem fights back {#learn}

Tutorial projects never held my attention for long.

I was always more interested in the uncomfortable version: real data, imperfect systems, and questions without guided answers.

So I asked myself a question:

> What happens if I try to build a real football analytics platform from scratch?

That question sounded much smaller than it actually was.

Because football data is not one thing.

A club is different from a national team. A domestic league is different from a knockout competition. A player can belong to one club while appearing in another competition. A season is not the same across countries. Promotions and relegations quietly break assumptions you thought were universal.

At first, I thought I was building a football data platform.

What I was actually building was a system that kept forcing me to think more precisely.

---

## Manchester United appeared nine times {#modelling}

Early on, I ingested clubs per league and season.

Technically, the pipeline worked.

Business-wise, it was nonsense.

Manchester United appeared nine times.

Same club. Nine rows.

That was the first moment the platform genuinely fought back.

Until then, I had been thinking like someone ingesting data.

That day, I started thinking like someone modelling systems.

A club existing and a club participating are different things entirely:

- identity,
- participation,
- competition,
- season.

Those concepts looked identical as a fan.

The warehouse forced them apart.

I split the platform into separate responsibilities:

- club identity,
- seasonal participation,
- historical tracking,
- competition relationships.

The architecture immediately became more complicated.

But it also became more truthful.

And that was my first real Eureka moment:

> watching football is not the same as modelling it.

Years of fandom had trained me emotionally.

The data forced me to become precise.

---

## The first time the platform scared me {#scaling}

At one point, I expanded the project from nine competitions to fifteen.

Routine change.

Then the next ingest job ran almost twice as long.

That was the first moment I genuinely thought:

> I may have designed this wrong.

Twelve minutes had become twenty-three.

At first, I assumed something was broken.

But the player volume had exploded too.

Domestic cups quietly pull lower-division clubs into the data. Lower-division clubs bring entire squads. Suddenly the platform was tracking tens of thousands more player records than before.

And then the realization landed:

the runtime increase was mostly linear.

That was not failure.

That was scale.

Without the earlier twelve-minute baseline, I would have wasted an entire day debugging a healthy system.

That became another Eureka moment:

> benchmarks are not just numbers — they are context.

The pipeline was not collapsing.

The scope had simply become more honest.

---

## The architecture decision I finally understood too late {#bronze-layer}

Around the same period, I started thinking more seriously about the ingestion design itself.

I had chosen to flatten nested JSON during ingestion:

- parse early,
- apply schemas immediately,
- land typed Delta tables,
- keep dbt staging thin.

At first, it felt elegant.

Then the project grew.

And suddenly every runtime increase felt connected to that decision.

That was the moment the bronze-layer conversation finally stopped feeling theoretical to me.

Not in a tutorial sense.

In a billable compute sense.

I realised I was paying for transformation work during extraction instead of later downstream.

Nothing was broken.

The architecture was simply charging interest on my own design choices.

And weirdly, that became the Eureka moment:

> good architecture is not free architecture.
> It is chosen tradeoffs you understand deeply enough to defend later.

Landing raw JSON first and parsing later would have given me:

- safer replayability,
- looser extraction coupling,
- cleaner separation between extraction and parsing.

Flatten-at-ingest gave me:

- simpler staging,
- cleaner dbt models,
- easier reasoning downstream.

Neither pattern was universally correct.

But now the tradeoff belonged to me.

And that changed the way I think about architecture entirely.

---

## The spinner weekend {#spinner}

One script taught me more than a week of tutorials.

Transfers.

At the time, I was fetching transfer history for more than sixteen thousand players, including thousands who had never made a meaningful match appearance.

The job ran for hours.

Then more hours.

Then most of a weekend.

I remember staring at the spinner thinking:

> production systems cannot survive like this.

And the strange part was that nothing was technically broken.

Spark was behaving correctly.

The API was responding.

The pipeline was doing exactly what I had asked it to do.

That became the real problem.

The system was not slow.

My thinking was.

I was fetching everybody instead of asking:

> who actually matters operationally?

The moment I filtered to active players, runtime collapsed from nearly twenty hours to roughly one minute.

That was the Eureka moment.

Not:

> "Spark is slow."

But:

> systems become fast when the question becomes precise.

Courses teach syntax.

Spinners teach architecture.

---

## Football statistics lie quietly {#league-cup}

At one point, I nearly built a mart that blended league and cup statistics together.

Technically, it worked.

Analytically, it was dishonest.

A Premier League match against Liverpool is not equivalent to an early domestic cup tie against lower-division opposition.

Blend them together and the averages start lying softly:

- inflated win rates,
- distorted scoring metrics,
- meaningless points-per-match calculations in knockout competitions.

Nothing crashes.

Dashboards still render.

But trust erodes silently.

That was another moment where football itself forced the modelling decisions.

The fix was not complicated SQL.

It was respecting the domain properly.

Separate grains.
Separate marts.
Separate questions.

And suddenly another realization clicked:

> domain knowledge shapes data modelling more than people admit.

Generic analytics skills alone would never have surfaced those mistakes.

The domain itself was teaching the architecture.

---

## The data humbled me faster than engineering did {#humbled}

The technical stack behaved mostly the way I expected:

- PySpark ingestion,
- dbt transformations,
- Databricks orchestration,
- incremental loading,
- source freshness,
- semantic modelling,
- CI pipelines.

Those were difficult.

But familiar kinds of difficult.

The real surprises came from football itself.

Domestic cups ballooned player counts unexpectedly. Champions League structure behaved differently from league competitions. Nations and clubs overlapped in ways that quietly broke assumptions. Transfer histories answered questions dimensions could not.

The platform kept forcing me to become more precise.

And honestly, that became the most rewarding part.

Because eventually I realised:

> personal fandom is not domain expertise.

Watching football taught me emotion.

Modelling football taught me structure.

That might have been the biggest Eureka moment in the entire project.

---

## Some of the best lessons came from bad data {#bad-data}

I once planned an entire coaching dimension.

Then the API confidently told me the same coach managed both France and Spain simultaneously.

I assumed I had written a bug.

I checked the transformations.
Then Postman.
Then the raw responses.

The API was simply wrong.

That changed how I think about trust in data systems entirely.

Broken systems announce themselves.

Bad data smiles while entering production.

So I removed coach models from the final product altogether.

The raw ingestion remained as proof the plumbing worked.

But I refused to model something I did not trust.

That decision probably taught me more about engineering maturity than any successful dashboard ever could.

Another quiet Eureka moment:

> shipping less is sometimes the more honest engineering decision.

---

## Somewhere in the middle, the project stopped being about football {#curiosity}

It became about curiosity.

About what happens when you let yourself care deeply about something long enough to understand its edges.

Medical leave gave me room to learn differently:

- slowly,
- obsessively,
- without needing every hour to become visibly productive.

I realised rest and curiosity were not opposites.

For me, recovery looked like:

- reading API documentation at midnight,
- redesigning grains during breakfast,
- watching runtimes collapse after one correct question,
- documenting decisions nobody asked me to document,
- building systems simply because I wanted to understand them properly.

That version of rest probably makes no sense to some people.

But it made sense to me.

---

## Public work changes the way you build {#public-work}

I knew this project would eventually live online.

That changed everything.

Suddenly I documented decisions I normally would have kept in my head. I wrote ADRs. Added catalog descriptions. Explained tradeoffs carefully. Built reproducibility into the repo.

Not because personal projects technically require those things.

Because public work changes the artefact.

Once strangers might learn from your system, clarity becomes part of the engineering itself.

---

## Infrastructure eventually became part of the story too {#infrastructure}

At first, Community Edition Databricks felt sufficient.

Then the project grew.

Compute caps became bottlenecks. Historical loads depended on luck. Outbound API networking started mattering more than SQL logic itself.

The platform did not fundamentally change.

The environment around it did.

That became another lesson I did not expect:

> systems do not fail only because code is wrong.

Sometimes infrastructure simply says:

> not today.

And you redesign around that reality.

---

## What remains now {#remains}

The platform exists.

So do the marts, ingestion jobs, semantic models, Streamlit application, ADRs, data catalog, and the architecture decisions that shaped all of it.

But those are not actually the part I think about most.

What stays with me are the moments:

- Manchester United appearing nine times,
- the transfer spinner weekend,
- realising runtime growth was healthy,
- discovering football statistics can lie quietly,
- understanding that honest grains matter more than clever SQL,
- learning that curiosity itself can become a form of recovery.

The platform is the artefact.

But the real story is permission:

> permission to go deep on something you already love.

And maybe that is what this project was really about from the beginning.

---

## What to do next {#closing}

Clone the repo.

Skim an ADR.
Argue with a modelling decision.

Explore the architecture.
Look through the marts.
Tell me where you would have designed things differently.

If this story resonated with you — whether you are into analytics engineering, football, data modelling, or simply learning in public — I would genuinely love to hear your thoughts.

Reach out if you are building something similar.

Curiosity scales better when shared.

---

*May 2026.*
