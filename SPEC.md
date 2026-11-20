# Spec for Defuse

Status: v2, 2026-11-19 15:22 (hackathon-kit starter format). Everything here is a decision unless marked OPEN. Agents read this file, not the chat.
Track: **Best Student Use Case** (auto-considered for Best Overall). **Freeze 16:00.**

## 1. Thesis
A student group plans its project work sessions — when, where, what food, who does what — through bots that **keep the awkward things quiet**: each teammate tells their bot privately about allergies, foods they dislike, their real budget and their limits, and the group only ever sees plans that already fit everyone. Nobody has to say "I can't afford that" or "I'm allergic to that".
**Grok Bot plus one new ability:** a Grok Bot team that plans for a group **without ever revealing who needed what.**

## 2. The demo, start to finish
1. **0–10 s, wow:** the group thread shows three café options for tonight's work session. Caption: "Someone here has a nut allergy, someone's on a $12 budget, someone hates sushi. You can't tell who. Neither can we." — *built, live*
2. Each of us messages our **own** Intake bot privately (show one phone): budget, allergies, dislikes, free times. — *built, live*
3. Manager posts only the pooled plan: one time, 3 venues, task split. No reasons. — *built, live*
4. We vote; I tap the pick on camera (kit `demo-7`). — *built, live*
5. **Judge's pick (Ryan, 15:31):** a judge **joins as a teammate** and privately tells the Intake bot their secret limits. The Manager re-plans; the group's options change and the judge gets a task. Nobody — including us — can see why. — *built, live*
6. **Leak check:** `leakcheck.py` scans every group message against everyone's private notes: "0 of N private facts appeared." — *built, live*
Everything is real: our real constraints, real venues near campus/the venue (no fake data — grand prize rule).

## 3. Screens
**Screen-recorded, FoWorld-style; almost no on-camera footage (Ryan, 15:31: "not too much IRL recording at all, should mostly be screen filmed").**
No custom app. Left: the group thread (what everyone sees). Right: one person's private Intake thread (what only they see). The contrast is the demo (kit `ui-2`).

## 4. Data shapes (frozen 15:30, only the lead edits)
- **Private (never leaves Intake):** `private/<member>.json {member, budget_max_usd, allergies[], dislikes[], dietary[], free_times[], max_travel_min, notes}`
- **Pooled (the only thing Manager and other workers see):**
  `pooled.json {budget_cap_usd: min(budget_max), exclude_ingredients: union(allergies+dietary rules), exclude_cuisines/foods: union(dislikes), windows: intersection(free_times), max_travel_min: min(...), n_members}` — **no member ids, no per-person values, no counts per constraint.**
- `plan.json {when, venues[3] {name, address, price_level, why_it_fits_generic}, tasks[] {title, owner, due}}`

## 5. What the model may choose from (closed lists — kit `model-1`)
- Venue `price_level` ∈ {$, $$, $$$}; a venue is allowed only if its typical meal ≤ `budget_cap_usd`.
- Venue reasons ∈ {"open during your window", "within walking distance", "fits the group's budget", "options for everyone"} — **generic only.**
- Manager actions: `pool`, `propose`, `poll`, `replan`, `assign`, `ask_accept`.

## 6. Rules a model's output must pass (the Defuse rules)
1. **Never name a person next to a constraint.** "Because Ryan is vegan" is a hard fail.
2. **Never state a pooled value that points at someone** — no "$12 budget", no "nut-free because of an allergy". Just show options that fit.
3. **Never suggest an excluded thing,** not even as "maybe not this one". Excluded = invisible.
4. **No counts per constraint** ("2 people have allergies").
5. **Higher-budget people come down silently;** nobody is asked to justify a limit.
6. With ≤ 3 members, the Manager never reveals the pooled numbers at all — only options.
7. Before any group post, run the leak check; any hit → regenerate without that content.
8. Contacting real people is behind a switch, off by default, our team only (kit `model-3`).
Fallbacks (kit `model-2`): venue search fails → Venue Scout uses a cached list of real places pulled at 15:30; leak check fails to run → post nothing until it passes.

## 7. One worked example
Private: A `{budget_max_usd: 25, allergies: [], dislikes: ["sushi"]}` · B `{budget_max_usd: 12, allergies: ["peanuts","tree nuts"]}` · C `{budget_max_usd: 18, dietary: ["vegetarian"], free_times: ["Thu 18:00-21:00"]}`
Pooled: `{budget_cap_usd: 12, exclude: ["peanuts","tree nuts","sushi","meat-only"], windows: ["Thu 18:00-20:00"], n_members: 3}`
Group post:
```
Work session — Thu 6:00–8:00 PM
1) [Café, address] — $ — open during your window, options for everyone
2) [Place, address] — $ — within walking distance, fits the group's budget
3) [Place, address] — $ — options for everyone
Vote 1/2/3. Tasks: slides — A · analysis — B · write-up — C (reply accept or swap)
```
Leak check: 0 hits for "peanut", "nut", "allergy", "$12", "12", "sushi", "vegetarian", any name + constraint.

## 8. The replay path
None needed: every step runs live in under 90 s. If the venue search is slow, say "searching live" and fill the wait with the private-thread view.

## 9. Stages and events
`intake → pooled → proposed → voted → assigned`. Events: `INTAKE_DONE(member)` (no content), `POOLED`, `PLAN_POSTED`, `LEAK_CHECK(pass|fail)`, `VOTE`, `REPLAN`, `ACCEPTED`.

## 10. Not building today
Custom app · payments/splitting the bill · reservations · grades/peer evals · Canvas · anything that tells the group *why* an option was removed.

## 11. Open questions
- Can each teammate have a private 1:1 thread with the Intake bot (template share link per person)? Test at 15:25. Fallback: each person installs their own Intake template.
- Venue area: default near Berkeley campus (Ryan's 15:31 answer was about recording, not area — confirm).

## 12. Decision log
- 14:38 Track 2, group project.
- **15:31 (Ryan):** name **Defuse**; no mention or credit of any other project anywhere judges see; video mostly screen-recorded like FoWorld; judge's pick = joins as a teammate with private limits; freeze 16:00; Ryan commits from one working copy; contract frozen 15:32, lead-only edits.
- **15:18 Pivot (Ryan):** the core is keeping constraints private and never said out loud (allergies, dislikes, budgets) when planning group work sessions over food; Receipts features dropped to "next".
