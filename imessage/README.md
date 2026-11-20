# Defuse on iMessage — 5-minute setup

Your Mac (signed in to Messages) becomes the Defuse number. Each teammate's 1:1 iMessage thread with your Apple ID is their **private Intake**. They text their limits; anyone texts `plan`; everyone gets the plan 1:1. Pooling, venue filtering and the leak check are the same code as the kit (`pool.py`, `filter_venues.py`, `leakcheck.py`).

## Setup
1. **Full Disk Access for Terminal** (to read `~/Library/Messages/chat.db`): System Settings → Privacy & Security → Full Disk Access → turn on Terminal (or iTerm) → quit and reopen it.
2. `cd imessage && cp config.example.json config.json`, then put teammates' **phone numbers or iMessage emails** in `allowlist` and their names in `names`. Only these handles are ever read or messaged.
3. **Offline check:** `python3 bridge.py --selftest` → must print `SELFTEST PASS`.
4. **Dry run:** `python3 bridge.py --dry-run` → have a teammate text you `max $12, no peanuts, free 6-9pm`, then `plan`. It prints what it *would* send. Ctrl-C.
5. **Live:** `python3 bridge.py`. First send may pop a macOS prompt: "Terminal wants to control Messages" → Allow.

## What teammates text
- Their limits, any wording: `max $12, no peanuts, free 6-9pm` · `I'm vegetarian, budget ~$18, free after 6` · `I hate sushi`
- `plan` → everyone gets: time window, 3 places, generic reasons, task split
- `1` / `2` / `3` to vote · `accept` / `swap` for tasks
- Changing limits after a plan → everyone gets "Options updated." with no reason

## Rules built in
- Strangers are ignored; sends go only to the allowlist.
- Old messages are ignored; it starts from "now".
- No plan is sent unless `leakcheck.py` passes. Private files live in `imessage/private/` on your Mac only.

## Known risks
- Messages must be **you texting from a different Apple ID/phone**: if a teammate's handle is your own number, their texts show as `is_from_me` and are skipped.
- Group chat posting (`group_chat` = the chat's name) uses AppleScript `chat whose name is`; unnamed group chats can't be targeted — leave it empty and 1:1 sends still work.
- New macOS stores some texts only in `attributedBody`; the decoder is heuristic (tested on a synthetic blob, not a real one).
- Real sending and receiving were not testable in the cloud — run the dry run first.

## Fallback
If anything here fails in the first 5 minutes, stay on the Grok Bot threads (`bots/` + `INSTALL.md`). Pitch iMessage as "next".

## Let a judge text it live (join code)
In `config.json`, set `"join_code": "DEFUSE"` and `"max_guests": 3`. Anyone who texts exactly **DEFUSE** to the Mac's iMessage (your phone number or Apple ID email) becomes a guest. They get a private welcome, can text their limits, and receive the plan. Strangers who don't send the code are ignored. Remove `join_code` after the demo.
For a live demo somewhere else, point `"venues"` in `config.json` at a venues file for that area.
