![Defuse](logo.png)

# Defuse — plan the meetup, keep the awkward part private

Defuse is five Grok Bots that plan student meetups (group-project work sessions, study groups, club meetings, founder coffee chats) without anyone having to say the awkward stuff out loud. Each person tells their own **Defuse Intake** bot privately: budget, allergies, foods they avoid or dislike, health needs, preferences, free times. The bots use only the pooled limits, with no names and no counts. The group only ever sees options that already fit everyone.

**Track:** Best Student Use Case · Berkeley x Stanford Grok Bot Hackathon, 19 Nov 2026

## Bot templates (manager + 4 workers)
- Defuse Manager (manager): https://x.ai/bot/7CjzM6TXBdIC9V3iGZtN2
- Defuse Intake: https://x.ai/bot/AaJU8T-TamXRhTq5PPZhl
- Defuse Venue Scout: https://x.ai/bot/qHLhEyaXdHSSSVH-Ck0EC
- Defuse Scheduler: https://x.ai/bot/_ExVWIJd7JkV0F2JdZUhW
- Defuse Leak Checker: https://x.ai/bot/uEsQrxJg7LTdtOZ8ZeQeQ

## Inspiration
Every student group ends up planning around food, and someone always quietly can't afford the place, can't eat half the menu, or is avoiding something for a reason they don't want to explain. Nobody says it, so plans take longer and someone ends up uncomfortable. We wanted a way for every limit to count without anyone having to say it out loud.

## What it does
- **Intake** (one private thread per person) collects budget, allergies, dislikes, health needs, preferences and free times, and passes on only the pooled limits: the lowest budget, every exclusion, the shared time window.
- **Venue Scout** searches for real places that fit every pooled limit. Anything excluded never appears.
- **Scheduler** picks a time everyone can make and splits the work (each owner replies accept or swap).
- **Leak Checker** blocks any group message that would reveal a private fact: no name next to a limit, no budget numbers, no allergies or diets, no counts, nothing that was filtered out.
- **Manager** coordinates the four workers and posts one plan the whole group can say yes to, with only generic reasons ("fits the group's budget", "options for everyone"). When someone adds a limit privately, it re-plans and posts "Options updated." with no reason.

## How we built it (tech stack)
- Five Grok Bot templates (one manager, four workers) with a shared spec of the pooled data shape and the leak rules.
- Grok Bot's browser and computer for live venue search and hours.
- Deterministic fallbacks the bots can run on their computer: `pool.py` (pools private limits with no names), `filter_venues.py` (keeps only places that fit), `leakcheck.py` (fails any message that leaks a private fact). Python standard library only.
- A web demo page that visualizes the pipeline (Intake → Pool → Venue Scout → Scheduler → Leak Checker → Manager → Group).
- An optional iMessage bridge (`imessage/bridge.py`) so each person's private thread can be a text conversation.

## Challenges we ran into
- Pooling limits without making them guessable: with only two or three people, even showing "$12 budget" points at someone, so the Manager never shows pooled numbers, counts or what was removed.
- Making the leak check catch paraphrases and names near limit words, not just exact matches.
- We changed the product direction mid-event and had to re-spec quickly.

## Accomplishments
- All five bots built and published as installable templates, coordinated by a manager bot.
- In our worked examples, Venue Scout returned only places that fit every pooled limit, and the Leak Checker blocked every leaky draft we wrote while passing the clean plans.
- The leak check passes clean plans and blocks leaky drafts (names next to limits, budget numbers, allergies, diets, counts).

## What we learned
The hard part isn't planning; it's what you're allowed to say while planning. Separating private input from pooled output, plus a checker in between, is a pattern that works for any group decision.

## What's next
- Silent bill-splitting at the lowest budget.
- Recurring weekly sessions with saved limits.
- iMessage as the default private thread.
- Study rooms and free campus spaces when the budget is $0.

## How Grok Bot helped build it
- Grok Bot created and published all five templates from our spec and set up the Defuse group chat.
- Venue Scout and Scheduler were built and tested inside Grok Bot on our worked example.
- Our Grok Bot session export (names, emails, phone numbers and keys removed) is being sent to the organizers.

## How to run it
1. Install the five templates above.
2. Each person messages **Defuse Intake** privately with anything to plan around.
3. Ask **Defuse Manager**: "Plan a session for [project] this week near [place]."
4. Vote on the options; reply accept or swap on your task.
5. Optional local checks: `python3 pool.py private/ -o pooled.json --check`, `python3 filter_venues.py pooled.json venues.json`, `python3 leakcheck.py draft.txt private/`.

Built at the event with Grok Bot. Venue prices in the demo page's recorded run are sample estimates; the live bots search real places.

**Live demo page:** https://claude.ai/artifact/RdiQiADDhjWBBzWXNWmPfp  
**Video:** https://youtu.be/kzFrdj0pZvY
