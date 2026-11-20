#!/usr/bin/env python3
"""pool.py — combine teammates' private limits into pooled.json with no names and no counts.
Usage: python3 pool.py private/ [-o pooled.json] [--check]
"""
import json, glob, os, re, sys, argparse

DAY = r"(?:mon|tue|wed|thu|fri|sat|sun)\w*\s+"

def parse_window(w):
    if isinstance(w, (list, tuple)) and len(w) == 2:
        return float(w[0]), float(w[1])
    m = re.search(r"(?:" + DAY + r")?(\d{1,2})(?::(\d{2}))?\s*-\s*(\d{1,2})(?::(\d{2}))?", str(w).lower())
    if not m:
        return None
    return int(m[1]) + int(m[2] or 0) / 60, int(m[3]) + int(m[4] or 0) / 60

def hhmm(h):
    return f"{int(h):02d}:{int(round((h % 1) * 60)):02d}"

def pool(people):
    budgets = [p["budget_max_usd"] for p in people if p.get("budget_max_usd") is not None]
    ex = set()
    for p in people:
        ex.update(x.lower() for x in p.get("allergies", []) + p.get("dislikes", []))
        for d in p.get("dietary", []):
            ex.add("meat-only" if d.lower() in ("vegetarian", "vegan") else d.lower())
    lo, hi = 0.0, 24.0
    for p in people:
        ws = [parse_window(w) for w in p.get("free_times", [])]
        ws = [w for w in ws if w]
        if ws:  # use the person's widest window overlap with current
            best = max(ws, key=lambda w: min(hi, w[1]) - max(lo, w[0]))
            lo, hi = max(lo, best[0]), min(hi, best[1])
    windows = [[hhmm(lo), hhmm(hi)]] if hi - lo >= 2 else []
    travel = [p["max_travel_min"] for p in people if p.get("max_travel_min") is not None]
    return {"budget_cap_usd": min(budgets) if budgets else None, "exclude": sorted(ex),
            "windows": windows, "max_travel_min": min(travel) if travel else None, "n_members": len(people)}

def check(pooled, people):
    out = json.dumps(pooled).lower()
    assert set(pooled) == {"budget_cap_usd", "exclude", "windows", "max_travel_min", "n_members"}, "unexpected fields"
    for p in people:
        n = p.get("member", "").lower()
        assert not (n and re.search(r"\b" + re.escape(n) + r"\b", out)), "member name leaked"
        b = p.get("budget_max_usd")
        if b is not None:
            assert b >= pooled["budget_cap_usd"], "cap is not the lowest budget"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("private_dir"); ap.add_argument("-o", "--out", default="pooled.json"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    people = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(a.private_dir, "*.json")))]
    if not people:
        sys.exit("no private/*.json files")
    pooled = pool(people)
    if a.check:
        check(pooled, people); print("CHECK PASS — no names, no non-cap budgets, no per-person fields")
    json.dump(pooled, open(a.out, "w"), indent=2)
    print(json.dumps(pooled, indent=2))

if __name__ == "__main__":
    main()
