#!/usr/bin/env python3
"""Self-test for history-personalized-homepage (ALIGNMENT rule 97).

Run:  python self_test.py
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import homepage as hp  # noqa: E402

results = []
NOW = 1_800_000_000.0  # fixed clock for determinism


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))


def write_history(tmp, lines, name="h.jsonl"):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8") as fh:
        for ln in lines:
            fh.write(json.dumps(ln) + "\n")
    return p


# ------------------------------------------------------------- functional ---
def test_functional(tmp):
    day = 86400.0
    events = [
        {"ts": NOW - 0.5 * day, "url": "https://docs.example.com/api", "title": "API docs", "dwell_seconds": 300},
        {"ts": NOW - 1 * day, "url": "https://docs.example.com/guide", "title": "Guide", "dwell_seconds": 200},
        {"ts": NOW - 20 * day, "url": "https://news.old.com/x", "title": "Old news", "dwell_seconds": 60},
    ]
    path = write_history(tmp, events)

    events_loaded, skipped = hp.load_history(path)
    record("functional: 3 events loaded", len(events_loaded) == 3 and skipped == 0)

    scores = hp.score_domains(events_loaded, now=NOW)
    record("functional: recency weighting ranks recent domain first",
           max(scores, key=scores.get) == "docs.example.com")

    html_out = hp.build_html(events_loaded, top_n=2, now=NOW)
    record("functional: html contains top domain link", "docs.example.com" in html_out)
    record("functional: html is deterministic (same input, same output)",
           html_out == hp.build_html(events_loaded, top_n=2, now=NOW))
    record("functional: www prefix normalized",
           hp.domain_of("https://www.docs.example.com/x") == "docs.example.com")

    out = os.path.join(tmp, "index.html")
    stats = hp.build(path, out, top_n=2)
    record("functional: build writes file with stats",
           os.path.exists(out) and stats["events"] == 3)


# ----------------------------------------------------------- error paths ---
def test_errors(tmp):
    try:
        hp.load_history(os.path.join(tmp, "missing.jsonl"))
        record("error: missing history raises", False)
    except hp.HomepageError:
        record("error: missing history raises", True)

    try:
        hp.build("x", "y", top_n=0)
        record("error: top_n=0 raises", False)
    except hp.HomepageError:
        record("error: top_n=0 raises", True)

    bad = write_history(tmp, [
        {"ts": NOW, "url": "https://ok.com/a"},
        {"url": "https://no-ts.com"},        # missing ts
        {"ts": NOW},                          # missing url
        {"ts": "yesterday", "url": "https://bad-ts.com"},  # wrong type
    ], "bad.jsonl")
    events, skipped = hp.load_history(bad)
    record("error: 3 malformed lines skipped and counted",
           len(events) == 1 and skipped == 3)


# ------------------------------------------------------------ edge cases ---
def test_edges(tmp):
    # empty history -> placeholder
    empty = write_history(tmp, [], "empty.jsonl")
    out = os.path.join(tmp, "empty.html")
    stats = hp.build(empty, out)
    with open(out, encoding="utf-8") as fh:
        content = fh.read()
    record("edge: empty history -> placeholder page",
           stats["events"] == 0 and "Nothing here yet" in content)

    # future timestamps clamped (no negative age)
    future = write_history(tmp, [
        {"ts": NOW + 10 * 86400, "url": "https://timetravel.com/x"}], "future.jsonl")
    scores = hp.score_domains(hp.load_history(future)[0], now=NOW)
    record("edge: future timestamp clamped to age 0",
           0.99 < scores["timetravel.com"] <= 1.01)

    # huge history: 20k events
    big = write_history(tmp, [
        {"ts": NOW - i * 60, "url": f"https://site{i % 50}.com/p{i}",
         "title": f"page {i}"} for i in range(20_000)], "big.jsonl")
    out_big = os.path.join(tmp, "big.html")
    stats = hp.build(big, out_big, top_n=5)
    record("edge: 20k events -> 50 domains, top 5 rendered",
           stats["domains"] == 50 and out_big and "site" in open(out_big).read())

    # malformed garbage file (not JSONL at all)
    garbage = os.path.join(tmp, "garbage.jsonl")
    with open(garbage, "w", encoding="utf-8") as fh:
        fh.write("\x00\x01 not json\n second line also bad\n")
    events, skipped = hp.load_history(garbage)
    record("edge: binary garbage -> 0 events, 2 skipped",
           events == [] and skipped == 2)

    # XSS-ish title is escaped
    xss = write_history(tmp, [
        {"ts": NOW, "url": "https://evil.com/<script>", "title": "<script>alert(1)</script>"}],
        "xss.jsonl")
    content = hp.build_html(hp.load_history(xss)[0], now=NOW)
    record("edge: html-escaped titles (no raw <script>)",
           "<script>alert" not in content and "&lt;script&gt;" in content)

    # redact mode
    content_r = hp.build_html(hp.load_history(xss)[0], now=NOW, redact_titles=True)
    record("edge: redact-titles mode hides page titles", "alert" not in content_r)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        test_functional(tmp)
        test_errors(tmp)
        test_edges(tmp)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
