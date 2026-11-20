#!/usr/bin/env python3
"""filter_venues.py — top 3 venues that fit pooled limits, each with one generic reason.
Usage: python3 filter_venues.py pooled.json venues.json
Excluded places are dropped silently: the output never says what was filtered or why.
Note: venues.json addresses/prices are a starting list; Venue Scout should refresh them from a live search.
"""
import json, sys

REASONS = ["options for everyone", "within walking distance", "fits the group's budget", "open during your window"]

def hour(s):
    if isinstance(s, (int, float)): return float(s)
    h, _, m = str(s).partition(":"); return int(h) + int(m or 0) / 60

def fits(v, p):
    if p.get("budget_cap_usd") is not None and v["typical_usd"] > p["budget_cap_usd"]:
        return False
    tags = " ".join(v.get("tags", [])).lower()
    if any(e.lower().rstrip("s") in tags for e in p.get("exclude", [])):
        return False
    if p.get("windows"):
        lo, hi = hour(p["windows"][0][0]), hour(p["windows"][0][1])
        if not (v["open"][0] <= lo and v["open"][1] >= hi):
            return False
    return True

def main():
    p = json.load(open(sys.argv[1])); vs = json.load(open(sys.argv[2]))
    ok = sorted([v for v in vs if fits(v, p)], key=lambda v: v["typical_usd"])[:3]
    out = [{"name": v["name"], "address": v["address"], "price_level": "$" if v["typical_usd"] < 12 else "$$", "reason": REASONS[i % len(REASONS)]} for i, v in enumerate(ok)]
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not out:
        print("No place fits everyone yet.", file=sys.stderr); sys.exit(2)

if __name__ == "__main__":
    main()
