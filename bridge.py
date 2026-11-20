#!/usr/bin/env python3
"""Defuse over iMessage — the shortest working path, run on a Mac signed in to Messages.

Each teammate's 1:1 iMessage thread with this Mac's Apple ID is their private Intake.
They text their limits ("max $12, no peanuts, free 6-9pm"). Anyone texts "plan" →
pool.py → filter_venues.py → compose → leakcheck must PASS → the plan goes to every
teammate 1:1 (and to a named group chat if config.group_chat is set).

Usage (from this folder):
  python3 bridge.py --dry-run          # reads chat.db, prints what it would send
  python3 bridge.py                    # live: sends via Messages (allowlisted handles only)
  python3 bridge.py --selftest         # offline test with a fake chat.db

Needs: Full Disk Access for the Terminal app (to read ~/Library/Messages/chat.db),
and Messages signed in. Python stdlib only. Run from ~/hackathon-kit/live/defuse/imessage.
"""
import argparse, json, os, re, sqlite3, subprocess, sys, time, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, KIT)
import pool as poolmod            # noqa: E402
import filter_venues as fv        # noqa: E402
import leakcheck as lc            # noqa: E402

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")
APPLE_EPOCH = 978307200  # 2001-01-01 UTC
PRIVATE_DIR = os.path.join(HERE, "private")
STATE = os.path.join(HERE, "state.json")

WELCOME = ("Hi, I'm Defuse. Anything I should quietly plan around? Budget for food, allergies or foods "
           "you avoid, foods you just don't like, when you're free tonight. Nobody else will see this. "
           "Text \"plan\" when the group is ready.")
ACK = "Got it. I'll plan around this. It stays between us."

# ---------- parsing (same rules as the demo page's parseLimits) ----------
ALLERGENS = ["peanut", "tree nut", "dairy", "gluten", "shellfish", "egg", "soy", "fish", "sesame"]
FOODS = ["sushi", "thai", "hot dogs", "burritos", "coffee", "boba", "spicy", "indian", "pizza"]
DIETS = ["vegetarian", "vegan", "halal", "kosher"]

def to24(h, pm_hint=True):
    h = int(h)
    return h + 12 if pm_hint and h < 12 else h

def parse_limits(text):
    t = text.lower()
    p = {"budget_max_usd": None, "allergies": [], "dislikes": [], "dietary": [], "free_times": []}
    m = re.search(r"\$\s?(\d+)", t) or re.search(r"(\d+)\s?(dollars|bucks)", t)
    if m:
        p["budget_max_usd"] = int(m.group(1))
    for a in ALLERGENS:
        if re.search(r"(no |allerg\w* to |can't (have|eat) |avoid )[^.]*\b" + a, t) or (a + "s are a no") in t or ("no " + a) in t:
            p["allergies"].append(a)
    for sent in re.split(r"[.!?\n;]", t):
        if re.search(r"allerg|are a no|is a no|can't (have|eat)|cannot (have|eat)|no ", sent):
            for a in ALLERGENS:
                if re.search(r"\b" + a, sent) and a not in p["allergies"]:
                    p["allergies"].append(a)
    for d in FOODS:
        if re.search(r"(don't|do not|hate|dislike|not a fan of)[^.]*" + d, t):
            p["dislikes"].append(d)
    for d in DIETS:
        if d in t:
            p["dietary"].append(d)
    f = re.search(r"(\d{1,2})\s?(?:pm)?\s?[–-]\s?(\d{1,2})\s?pm", t)
    a = re.search(r"after (\d{1,2})", t)
    if f:
        p["free_times"] = [[to24(f.group(1)), to24(f.group(2))]]
    elif a:
        p["free_times"] = [[to24(a.group(1)), 23]]
    return p

def has_limits(p):
    return p["budget_max_usd"] is not None or p["allergies"] or p["dislikes"] or p["dietary"] or p["free_times"]

# ---------- chat.db ----------
def decode_attributed_body(blob):
    """Newer macOS leaves message.text NULL and stores an NSAttributedString typedstream.
    Heuristic: the string follows 'NSString' then a 0x01 0x2b ('+') marker and a length byte."""
    if not blob:
        return None
    try:
        b = bytes(blob)
        i = b.find(b"NSString")
        if i < 0:
            return None
        j = b.find(b"\x01\x2b", i)
        if j < 0:
            return None
        j += 2
        n = b[j]; j += 1
        if n == 0x81:  # 2-byte little-endian length
            n = int.from_bytes(b[j:j + 2], "little"); j += 2
        elif n == 0x82:  # 3-byte
            n = int.from_bytes(b[j:j + 3], "little"); j += 3
        return b[j:j + n].decode("utf-8", errors="replace")
    except Exception:
        return None

def open_db(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)

def fetch_new(db_path, after_rowid, handles, join_code=None):
    """Incoming 1:1 messages from allowlisted handles with ROWID > after_rowid.
    If join_code is set, a message from an unknown handle that is exactly the code is returned too (opt-in join)."""
    con = open_db(db_path)
    try:
        rows = con.execute(
            """SELECT m.ROWID, h.id, m.text, m.attributedBody, m.date
               FROM message m JOIN handle h ON m.handle_id = h.ROWID
               WHERE m.ROWID > ? AND m.is_from_me = 0
               ORDER BY m.ROWID""", (after_rowid,)).fetchall()
    finally:
        con.close()
    out = []
    norm = {norm_handle(x): x for x in handles}
    for rowid, hid, text, body, date in rows:
        who = norm.get(norm_handle(hid))
        txt = text if text else decode_attributed_body(body)
        if not who:
            if join_code and txt and txt.strip().upper() == join_code.upper():
                out.append((rowid, "JOIN:" + hid, txt.strip()))
            continue
        if txt:
            out.append((rowid, who, txt.strip()))
    return out, (rows[-1][0] if rows else after_rowid)

def max_rowid(db_path):
    con = open_db(db_path)
    try:
        r = con.execute("SELECT COALESCE(MAX(ROWID),0) FROM message").fetchone()[0]
    finally:
        con.close()
    return r

def norm_handle(h):
    h = (h or "").strip().lower()
    if "@" in h:
        return h
    d = re.sub(r"\D", "", h)
    return d[-10:]  # US numbers: compare last 10 digits

# ---------- sending ----------
def as_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def send(handle, text, cfg, dry):
    if norm_handle(handle) not in {norm_handle(h) for h in cfg["allowlist"]}:
        print(f"[blocked] {handle} is not on the allowlist"); return False
    if dry:
        print(f"\n--- would send to {handle} ---\n{text}\n"); return True
    script = ('tell application "Messages"\n'
              '  set svc to 1st account whose service type = iMessage\n'
              f'  send {as_quote(text)} to participant {as_quote(handle)} of svc\n'
              'end tell')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        # older Messages scripting dictionary
        script2 = ('tell application "Messages" to send ' + as_quote(text) + ' to buddy ' + as_quote(handle) +
                   ' of (service 1 whose service type is iMessage)')
        r = subprocess.run(["osascript", "-e", script2], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[send failed] {handle}: {r.stderr.strip()}"); return False
    return True

def send_group(name, text, cfg, dry):
    if not name:
        return
    if dry:
        print(f"\n--- would send to group chat '{name}' ---\n{text}\n"); return
    script = ('tell application "Messages"\n'
              f'  set c to first chat whose name is {as_quote(name)}\n'
              f'  send {as_quote(text)} to c\n'
              'end tell')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[group send failed] {r.stderr.strip()}")

# ---------- people ----------
def pfile(handle):
    return os.path.join(PRIVATE_DIR, re.sub(r"[^a-z0-9@._+-]", "_", norm_handle(handle)) + ".json")

def load_people(cfg):
    people = []
    for h in cfg["allowlist"]:
        f = pfile(h)
        if os.path.exists(f):
            people.append(json.load(open(f)))
    return people

def save_limits(handle, name, new):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    f = pfile(handle)
    cur = json.load(open(f)) if os.path.exists(f) else {"member": name, "budget_max_usd": None, "allergies": [],
                                                         "dislikes": [], "dietary": [], "free_times": []}
    if new["budget_max_usd"] is not None:
        cur["budget_max_usd"] = new["budget_max_usd"]
    for k in ("allergies", "dislikes", "dietary"):
        cur[k] = sorted(set(cur.get(k, [])) | set(new[k]))
    if new["free_times"]:
        cur["free_times"] = new["free_times"]
    json.dump(cur, open(f, "w"), indent=1)
    return cur

# ---------- plan ----------
def fmt_h(hm):
    h = int(str(hm).split(":")[0]) if isinstance(hm, str) else int(hm)
    return f"{(h % 12) or 12} {'PM' if h >= 12 else 'AM'}"

def compose_plan(people, venues, tasks, member_names):
    pooled = poolmod.pool(people)
    poolmod.check(pooled, people)
    ok = sorted([v for v in venues if fv.fits(v, pooled)], key=lambda v: v["typical_usd"])[:3]
    if not pooled["windows"] or not ok:
        return pooled, "Defuse: no time or place fits everyone yet. I'll keep looking quietly. (Update your limits any time, privately.)"
    w = pooled["windows"][0]
    lines = [f"Defuse plan: work session {fmt_h(w[0])} to {fmt_h(w[1])}"]
    for i, v in enumerate(ok):
        lines.append(f"{i + 1}) {v['name']}, {v['address']} ({fv.REASONS[i % len(fv.REASONS)]})")
    lines.append("Reply 1, 2 or 3 to vote.")
    if tasks:
        lines.append("Tasks (reply accept or swap): " + "; ".join(f"{t} - {n}" for t, n in zip(tasks, member_names)))
    return pooled, "\n".join(lines)

def safe_plan(people, cfg, venues):
    names = [p.get("member", "") for p in people]
    pooled, text = compose_plan(people, venues, cfg.get("tasks", []), names)
    hits = lc.check(text, people, [])
    # task lines put names next to task words only; recheck without them as a sanity guard
    if hits:
        text = text.split("\nTasks")[0]
        hits = lc.check(text, people, [])
    return (None, hits) if hits else (text, [])

# ---------- loop ----------
def handle_message(who, text, cfg, venues, dry, st):
    name = cfg["names"].get(who, who)
    low = text.lower().strip()
    if low in ("plan", "plan it", "go"):
        people = load_people(cfg)
        if not people:
            send(who, "Nobody has told me their limits yet. Text me yours privately first.", cfg, dry); return
        text_out, hits = safe_plan(people, cfg, venues)
        if hits:
            print(f"[leak check FAIL: {', '.join(hits)}] plan held back")
            send(who, "Held back a draft that wasn't private enough. Trying again quietly.", cfg, dry); return
        print(f"[leak check PASS] sending plan to {len(cfg['allowlist'])} teammates")
        for h in cfg["allowlist"]:
            send(h, text_out, cfg, dry)
        send_group(cfg.get("group_chat"), text_out, cfg, dry)
        st["plan_sent"] = True; return
    if low in ("1", "2", "3"):
        st.setdefault("votes", {})[who] = low
        send(who, f"Vote {low} counted.", cfg, dry); return
    if low in ("accept", "swap"):
        send(who, "Noted. Thanks.", cfg, dry); return
    new = parse_limits(text)
    if has_limits(new):
        save_limits(who, name, new)
        send(who, ACK, cfg, dry)
        if st.get("plan_sent"):  # someone changed limits after a plan → re-plan silently
            people = load_people(cfg)
            text_out, hits = safe_plan(people, cfg, venues)
            if text_out:
                for h in cfg["allowlist"]:
                    send(h, "Options updated.\n" + text_out, cfg, dry)
        return
    if not st.setdefault("welcomed", {}).get(who):
        st["welcomed"][who] = True
        send(who, WELCOME, cfg, dry)

def run(cfg, dry, db_path=CHAT_DB, once=False):
    venues = json.load(open(cfg.get("venues", os.path.join(KIT, "venues.json"))))
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if "last_rowid" not in st:
        st["last_rowid"] = max_rowid(db_path)  # start from now; ignore history
        print(f"Starting after message #{st['last_rowid']} (old messages ignored)")
    print(f"Defuse bridge {'(DRY RUN) ' if dry else ''}watching {len(cfg['allowlist'])} teammates. Ctrl-C to stop.")
    for g in st.get("guests", []):  # guests who joined earlier this session
        if g not in cfg["allowlist"]: cfg["allowlist"].append(g)
        cfg["names"].setdefault(g, f"Guest {st['guests'].index(g)+1}")
    code = cfg.get("join_code")
    if code: print(f"Join code ON: anyone who texts '{code}' joins (max {cfg.get('max_guests', 3)} guests).")
    while True:
        msgs, last = fetch_new(db_path, st["last_rowid"], cfg["allowlist"], code)
        for rowid, who, text in msgs:
            if who.startswith("JOIN:"):
                h = who[5:]; guests = st.setdefault("guests", [])
                if h not in guests and len(guests) < cfg.get("max_guests", 3):
                    guests.append(h); cfg["allowlist"].append(h); cfg["names"][h] = f"Guest {len(guests)}"
                    print(f"[join] a guest joined with the code ({len(guests)}/{cfg.get('max_guests', 3)})")
                    send(h, "You're in. " + WELCOME, cfg, dry)
                last = rowid  # re-read anything the guest sent right after joining
                break
            print(f"[in] {cfg['names'].get(who, who)}: (private message, {len(text)} chars)")
            handle_message(who, text, cfg, venues, dry, st)
        st["last_rowid"] = last
        json.dump(st, open(STATE, "w"))
        if once:
            return st
        time.sleep(2)

# ---------- offline self-test ----------
def make_fake_db(path, msgs):
    con = sqlite3.connect(path)
    con.executescript("""
      CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);
      CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, chat_identifier TEXT, display_name TEXT);
      CREATE TABLE message (ROWID INTEGER PRIMARY KEY, text TEXT, attributedBody BLOB, handle_id INTEGER,
                            is_from_me INTEGER, date INTEGER);""")
    hid = {}
    for h, _, _ in msgs:
        if h not in hid:
            con.execute("INSERT INTO handle(id, service) VALUES (?, 'iMessage')", (h,))
            hid[h] = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    for h, text, attributed in msgs:
        ns = int((time.time() - APPLE_EPOCH) * 1e9)
        if attributed:
            raw = text.encode()
            blob = b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01\x2b" + bytes([len(raw)]) + raw + b"\x86\x84\x02iI"
            con.execute("INSERT INTO message(text, attributedBody, handle_id, is_from_me, date) VALUES (NULL, ?, ?, 0, ?)", (blob, hid[h], ns))
        else:
            con.execute("INSERT INTO message(text, attributedBody, handle_id, is_from_me, date) VALUES (?, NULL, ?, 0, ?)", (text, hid[h], ns))
    con.commit(); con.close()

def selftest():
    global PRIVATE_DIR, STATE
    tmp = tempfile.mkdtemp()
    PRIVATE_DIR, STATE = os.path.join(tmp, "private"), os.path.join(tmp, "state.json")
    db = os.path.join(tmp, "chat.db")
    make_fake_db(db, [])
    cfg = {"allowlist": ["+15105550101", "+15105550102", "sriram@example.com"],
           "names": {"+15105550101": "Ryan", "+15105550102": "Tushar", "sriram@example.com": "Sriram"},
           "tasks": ["Slides", "Data analysis", "Write-up"], "group_chat": ""}
    st = run(cfg, True, db, once=True)  # sets last_rowid = 0
    con = sqlite3.connect(db); con.execute("DELETE FROM message"); con.commit(); con.close()
    make_fake_db_append(db, [
        ("+1 (510) 555-0101", "Up to $25 is fine. I really don't like sushi. Free 5-10pm.", False),
        ("sriram@example.com", "Keep it around $12 if we can. Peanuts and tree nuts are a no for me. Free 6-9pm.", True),
        ("+15105550102", "I'm vegetarian, budget ~$18. Free after 6.", False),
        ("+15105559999", "spam from a stranger", False),
        ("+15105550102", "plan", False),
    ])
    st = run(cfg, True, db, once=True)
    people = load_people(cfg)
    assert len(people) == 3, people
    assert any(p["budget_max_usd"] == 12 for p in people), "attributedBody text not decoded"
    pooled = poolmod.pool(people)
    assert pooled["budget_cap_usd"] == 12 and "peanut" in pooled["exclude"] and "meat-only" in pooled["exclude"], pooled
    text, hits = safe_plan(people, cfg, json.load(open(os.path.join(KIT, "venues.json"))))
    assert text and not hits, hits
    for bad in ["$12", "peanut", "sushi", "vegetarian", "Sriram is allergic"]:
        assert bad.lower() not in text.lower(), bad
    assert st.get("plan_sent"), "plan not sent"
    print("\nSELFTEST PASS — 3 private intakes (one via attributedBody), stranger ignored, plan passed leak check, no private facts in the plan")
    shutil.rmtree(tmp)

def make_fake_db_append(path, msgs):
    con = sqlite3.connect(path)
    for h, text, attributed in msgs:
        r = con.execute("SELECT ROWID FROM handle WHERE id=?", (h,)).fetchone()
        if not r:
            con.execute("INSERT INTO handle(id, service) VALUES (?, 'iMessage')", (h,))
            r = con.execute("SELECT last_insert_rowid()").fetchone()
        ns = int((time.time() - APPLE_EPOCH) * 1e9)
        if attributed:
            raw = text.encode()
            blob = b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01\x2b" + bytes([len(raw)]) + raw + b"\x86\x84\x02iI"
            con.execute("INSERT INTO message(text, attributedBody, handle_id, is_from_me, date) VALUES (NULL, ?, ?, 0, ?)", (blob, r[0], ns))
        else:
            con.execute("INSERT INTO message(text, attributedBody, handle_id, is_from_me, date) VALUES (?, NULL, ?, 0, ?)", (text, r[0], ns))
    con.commit(); con.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not os.path.exists(a.config):
        sys.exit("No config.json. Copy config.example.json to config.json and fill in teammates' handles.")
    cfg = json.load(open(a.config))
    try:
        open_db(CHAT_DB).execute("SELECT 1 FROM message LIMIT 1")
    except Exception as e:
        sys.exit(f"Can't read {CHAT_DB} ({e}). Give your Terminal app Full Disk Access: System Settings → Privacy & Security → Full Disk Access, then restart Terminal.")
    try:
        run(cfg, a.dry_run)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
