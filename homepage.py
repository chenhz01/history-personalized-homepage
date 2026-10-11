#!/usr/bin/env python3
"""history-personalized-homepage: regenerate your homepage from local history.

Reads a JSONL activity log ({ts, url, title?, dwell_seconds?}), scores
domains by recency-weighted frequency, and renders a deterministic HTML
homepage — top sites as quick links, activity summary as sections. All data
stays local; the "profile" is a plain dict you can inspect and delete.

The UI is model output, not configuration: same history in, same page out.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from collections import defaultdict
from urllib.parse import urlparse

DEFAULT_TOP = 8
MAX_EVENTS = 1_000_000
MAX_TITLE = 300
RECENCY_HALF_LIFE_DAYS = 7.0


class HomepageError(Exception):
    pass


def load_history(path: str) -> tuple[list[dict], int]:
    """Returns (events, skipped). Malformed lines skipped and counted."""
    events, skipped = [], 0
    if not os.path.exists(path):
        raise HomepageError(f"history file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if not isinstance(ev.get("url"), str) or not ev["url"].strip():
                    raise ValueError("missing url")
                if not isinstance(ev.get("ts"), (int, float)):
                    raise ValueError("missing ts")
                ev["title"] = str(ev.get("title", ""))[:MAX_TITLE]
                ev["dwell_seconds"] = max(0, int(ev.get("dwell_seconds", 0)))
                events.append(ev)
            except (json.JSONDecodeError, ValueError):
                skipped += 1
    return events, skipped


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def score_domains(events: list[dict], now: float | None = None,
                  half_life_days: float = RECENCY_HALF_LIFE_DAYS) -> dict[str, float]:
    """Recency-weighted visit score: each event adds 2^(-age_days/half_life).
    Future timestamps are clamped to age 0 (never negative weight)."""
    now = time.time() if now is None else now
    hl = max(half_life_days, 0.001)
    scores: dict[str, float] = defaultdict(float)
    for ev in events:
        d = domain_of(ev["url"])
        if not d:
            continue
        age_days = max(0.0, (now - ev["ts"]) / 86400.0)
        scores[d] += 2.0 ** (-age_days / hl)
    return dict(scores)


def _fmt_age(days: float) -> str:
    if days < 1:
        return "today"
    if days < 30:
        return f"{int(days)}d ago"
    if days < 365:
        return f"{int(days // 30)}mo ago"
    return f"{int(days // 365)}y ago"


def build_html(events: list[dict], top_n: int = DEFAULT_TOP,
               now: float | None = None, redact_titles: bool = False) -> str:
    now = time.time() if now is None else now
    e = html.escape

    if not events:
        return ("<!doctype html><html><head><meta charset='utf-8'>"
                "<title>Home</title></head><body>"
                "<h1>Nothing here yet</h1><p>No history events were found. "
                "This placeholder page is the deterministic empty-state "
                "output of history-personalized-homepage.</p></body></html>")

    scores = score_domains(events, now)
    top = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    latest: dict[str, tuple[str, str, float]] = {}
    for ev in events:
        d = domain_of(ev["url"])
        if not d:
            continue
        age = max(0.0, (now - ev["ts"]) / 86400.0)
        if d not in latest or age < latest[d][2]:
            title = "visited page" if redact_titles or not ev["title"] else ev["title"]
            latest[d] = (ev["url"], title, age)

    total_dwell = sum(ev["dwell_seconds"] for ev in events)
    n_domains = len(scores)

    links = "\n".join(
        f"<li><a href='{e(latest[d][0])}'>{e(latest[d][1])}</a> "
        f"<small>{e(d)} · {e(_fmt_age(latest[d][2]))} · score {s:.2f}</small></li>"
        for d, s in top)

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Home</title>
<style>body{{font-family:sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}}
li{{margin:.5rem 0}} small{{color:#666}}</style></head><body>
<h1>Your day, regenerated from {len(events)} local events</h1>
<p>Top {len(top)} of {n_domains} domains · total dwell {int(total_dwell // 60)} min ·
generated deterministically from local history (nothing left this machine).</p>
<ul>
{links}
</ul>
</body></html>"""


def build(history_path: str, out_path: str, top_n: int = DEFAULT_TOP,
          redact_titles: bool = False) -> dict:
    if not 1 <= top_n <= 100:
        raise HomepageError("top_n must be between 1 and 100")
    events, skipped = load_history(history_path)
    if len(events) > MAX_EVENTS:
        events = events[:MAX_EVENTS]
    page = build_html(events, top_n, redact_titles=redact_titles)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return {"events": len(events), "skipped": skipped,
            "domains": len(score_domains(events)), "out": out_path}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="homepage",
        description="Regenerate a homepage from a local JSONL history log.")
    ap.add_argument("--history", required=True)
    ap.add_argument("--out", default="index.html")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--redact-titles", action="store_true",
                    help="render 'visited page' instead of page titles")
    args = ap.parse_args(argv)
    try:
        stats = build(args.history, args.out, args.top, args.redact_titles)
        print(f"wrote {stats['out']} "
              f"({stats['events']} events, {stats['domains']} domains, "
              f"{stats['skipped']} skipped)")
        return 0
    except (HomepageError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
