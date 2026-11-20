#!/usr/bin/env python3
"""leakcheck.py — does a group message leak anyone's private constraints?

Usage: python3 leakcheck.py <message.txt or -> <private_dir> [--names "Ryan,Ana,Ben"]
private_dir holds one JSON per teammate:
  {"member": "Ryan", "budget_max_usd": 12, "allergies": ["peanuts"], "dislikes": ["sushi"], "dietary": ["vegetarian"]}
Prints PASS, or FAIL with categories only (never the private value). Exit code 1 on FAIL.
"""
import json, re, sys, glob, os, argparse

CONSTRAINT_WORDS = ["allerg", "budget", "afford", "can't eat", "cannot eat", "doesn't eat", "dislike", "hate",
                    "vegan", "vegetarian", "halal", "kosher", "gluten", "broke", "expensive", "cheap"]

def load(private_dir):
    people = []
    for f in sorted(glob.glob(os.path.join(private_dir, "*.json"))):
        with open(f) as fh:
            people.append(json.load(fh))
    return people

def check(msg, people, extra_names=()):
    text = msg.lower()
    hits = set()
    for p in people:
        for key, cat in (("allergies", "allergy"), ("dislikes", "dislike"), ("dietary", "diet")):
            for item in p.get(key, []):
                for term in {item.lower(), item.lower().split()[-1]}:
                    if re.search(r"\b" + re.escape(term.rstrip("s")) + r"s?\b", text):
                        hits.add(cat)
        b = p.get("budget_max_usd")
        if b is not None and re.search(r"\$\s?" + re.escape(str(b)) + r"\b|\b" + re.escape(str(b)) + r"\s?(dollars|bucks|usd)\b", text):
            hits.add("budget number")
    names = {p.get("member", "").lower() for p in people if p.get("member")} | {n.lower() for n in extra_names}
    for sent in re.split(r"[.!?\n]", text):
        if any(n and re.search(r"\b" + re.escape(n) + r"\b", sent) for n in names) and any(w in sent for w in CONSTRAINT_WORDS):
            hits.add("name next to a constraint")
    if re.search(r"\b(\d+|one|two|three|four|five)\s+(of you|people|person|members?)\b[^.]*\b(" + "|".join(CONSTRAINT_WORDS) + ")", text):
        hits.add("count of people with a constraint")
    return sorted(hits)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message")
    ap.add_argument("private_dir")
    ap.add_argument("--names", default="")
    a = ap.parse_args()
    msg = sys.stdin.read() if a.message == "-" else open(a.message).read()
    people = load(a.private_dir)
    hits = check(msg, people, [n.strip() for n in a.names.split(",") if n.strip()])
    facts = sum(len(p.get(k, [])) for p in people for k in ("allergies", "dislikes", "dietary")) + sum(1 for p in people if p.get("budget_max_usd") is not None)
    if hits:
        print("FAIL: " + ", ".join(hits))
        sys.exit(1)
    print(f"PASS — 0 of {facts} private facts appeared ({len(people)} teammates)")

if __name__ == "__main__":
    main()
