# Install Defuse in Grok Bot (about 10 minutes)

Files: `bots/1-manager.md` … `bots/5-leak-checker.md`, plus `pool.py`, `filter_venues.py`, `leakcheck.py`, `venues.json`, `example/`.

## 1. Create the 5 bots (≈6 min)
For each file in `bots/`, in this order: **2-intake → 1-manager → 3-venue-scout → 4-scheduler → 5-leak-checker**
1. In Grok Bot, create a new bot.
2. Paste the **Name** block into the name, the **Description** block into the description, and the **Instructions** block into the instructions.
3. Upload or paste the matching fallback script onto that bot's computer: Intake → `pool.py`; Venue Scout → `filter_venues.py` + `venues.json`; Leak Checker → `leakcheck.py`.
4. Copy the bot's **template share link** into the README's "How to run it" list. (Track 2 needs a link for every bot.)

## 2. Wire the handoffs (≈1 min)
Put all 5 bots in one group with the Manager as coordinator. Handoff order:
`Intake (private) → pooled.json → Manager → Venue Scout + Scheduler → Manager draft → Leak Checker PASS → group post → votes/accept → re-plan if limits change`.

## 3. Private-thread test (≈1 min) — everything depends on this
- Teammate A messages **Defuse Intake** directly. Teammate B messages it directly.
- Check: B cannot see A's message anywhere, and the group thread shows nothing.
- If threads are shared: each teammate installs their own copy of Intake from its share link, and each copy saves to the same `private/` folder (or forwards only pooled.json).

## 4. 60-second smoke test with the example files
On any bot's computer (or a laptop) with the kit:
```
python3 pool.py example/private -o pooled.json --check   # expect: CHECK PASS, budget_cap_usd 12, window 18:00–21:00
python3 filter_venues.py pooled.json venues.json          # expect: 3 places, none with peanuts, sushi or meat-only
python3 leakcheck.py example/good.txt example/private     # expect: PASS — 0 of 7 private facts
python3 leakcheck.py example/bad.txt example/private      # expect: FAIL (allergy, budget number, name next to a constraint)
```
Then in Grok Bot: tell the Manager "Plan a 2-hour work session tonight near campus" and check that the post passes Leak Checker.

## 5. Real run (for the live demo)
Each teammate sends real limits to Intake privately → Manager posts → vote and accept on camera → a judge joins, tells Intake their limits privately → "Options updated."
