# history-personalized-homepage

Regenerate your homepage from the browsing history already on your machine: local JSONL events in, a ranked quick-links page out, deterministically. The cheapest personalization corpus you own is the one you never had to instrument for. If your tool, dashboard, or agent workspace opens a static start page, this makes it reorganize itself daily from real usage; if your history is thin or you never look at start pages, skip it.

## Problem

New-tab and start pages have barely changed in a decade: a static bookmark grid someone configured once. Meanwhile one product showed the alternative — an LLM agent regenerating the page daily from the user's browsing history: history → profile → today's homepage [unverified claim about the specific project — see source link]. The mechanism underneath needs no model at all: history is the cheapest personalization signal, it is already local, and a deterministic scorer can produce most of the value with none of the privacy cost of shipping that history to a cloud model.

The overlooked angle: the UI becomes an *output* — a generated artifact from a log — instead of a configuration surface nobody maintains.

## How it works

1. **Input**: one JSONL event per visit — `{ts, url, title?, dwell_seconds?}`. Malformed lines are skipped and counted, never silently dropped.
2. **Profile**: each event scores its domain by recency-weighted frequency — `2^(-age_days / 7-day half-life)`. Future timestamps clamp to age 0; `www.` is normalized away. The profile is a plain dict: inspectable, dumpable, deletable.
3. **Render**: top-N domains become links (with score and last-visit age), plus an activity summary line. Everything is HTML-escaped; `--redact-titles` renders "visited page" instead of titles.
4. **Determinism**: same history + same clock → byte-identical page. The generator is testable, cacheable, and diff-able.

Quickstart (~5 min):

```bash
# 1. Self-test (~3 s)
python self_test.py

# 2. Make a tiny history and build (~10 s)
echo '{"ts": 1800000000, "url": "https://docs.example.com/api", "title": "API", "dwell_seconds": 120}' > h.jsonl
echo '{"ts": 1799900000, "url": "https://news.example.org/x"}' >> h.jsonl
python homepage.py --history h.jsonl --out index.html --top 5
# -> wrote index.html (2 events, 2 domains, 0 skipped)
```

Schedule the last line daily (cron/Task Scheduler) and the page reorganizes itself.

## Why not X

| Alternative | Why not |
|---|---|
| LLM-regenerated homepage (cloud) | Ships your browsing history to a third party on every regeneration, costs per day, and is non-deterministic — two builds from the same history differ. The local scorer gets the ranking; add an LLM later only for the summary text. |
| Static bookmarks / speed dial | Zero adaptation: configured once, then drifts from what you actually use. This page re-ranks itself every build from real events. |
| Full analytics stacks (self-hosted) | Built for teams and dashboards; a personal homepage needs one scorer and one template, not an event warehouse. |
| Browser "most visited" built-ins | Black-box ranking, no control over the half-life, no export, no redaction — and you cannot compose it into your own page. |

## Minimal Fallback

No Python at all? Keep the concept, drop the tool:

- `jq -r .url h.jsonl | sed 's|https\?://([^/]*).*|\1|' | sort | uniq -c | sort -rn | head` gives the ranked-domain list; paste it into any HTML page or pin it as browser links.
- In Python stdlib without this repo, `collections.Counter` over `urlparse(url).netloc` in ten lines gives unweighted frequency; you lose recency weighting, HTML escaping, and the malformed-line counter.

## Design Trade-offs

Priorities: **privacy > determinism > simplicity > personalization depth.**

- Pure-local scoring, no network calls anywhere: the history never leaves the machine, even though an LLM summary would be "nicer".
- Frequency × recency with a fixed half-life instead of learned weights: one interpretable knob beats an opaque model nobody can audit.
- Titles are rendered escaped and optional: the tool treats page titles as the most sensitive field by default (`--redact-titles` for screens others can see).
- No dwell-time weighting in the score (dwell is recorded but informational): self-reported or poorly-measured dwell is noisy, and a noisy weight silently biases the whole page.

## Limits & Second-order Effects

- Ranking quality is capped by history richness: a fresh or sparse log yields a boring page. The empty state is explicit, not faked.
- Second-order effect: a self-reinforcing loop — the homepage promotes what you already visit, so you visit it more, so it gets promoted more. Filter-bubble dynamics on a small scale; consider pinning a fixed "explore" slot outside the scored ranking.
- The history file is a high-value privacy artifact on disk. This tool reads it; it does not protect it. Encrypt or rotate it as you would any sensitive log.

## FAQ

**Where does the history file come from?**
You. Any exporter that writes `{ts, url}` JSONL works — browser extensions, proxy logs, agent task logs. The tool defines the contract, not the collector.

**When should you NOT use this tool?**
Shared/machine accounts (the "personalization" leaks one user's habits to another), single-visitor sites where ranking is trivial, and any context where the history file itself cannot be kept local.

**Can I add an LLM summary on top?**
Yes — feed `build_html` output or the profile dict to your model, but keep the ranking deterministic. Ranking from a model is non-reproducible; summaries are fine.

## Core Assumptions

1. Recent visits predict near-future relevance well enough that a fixed half-life is useful (7 days, adjustable in one constant).
2. Domain-level granularity is the right trade-off between personalization and churn — page-level ranking is noisier and more privacy-sensitive.
3. The history log is trustworthy enough to score (garbage in is skipped, but a systematically wrong collector still yields a wrong page).
4. The tool runs where the history lives; nothing in the pipeline sends data anywhere.

Confidence: **High** that deterministic recency-weighted ranking reproduces sensible homepages from event logs (all ranking, escaping, and edge behaviors are test-covered — reproduce with `python self_test.py`). Confidence: **Medium** that daily regeneration meaningfully outperforms static bookmarks in practice — mechanism is sound, no longitudinal user study [estimated].

The half-life constant and event caps are design values, current **as of 2026-10-11**.

Source inspiration (structural restatement only): https://github.com/ThariqS/ai-newtab — daily LLM-regenerated new-tab page from browsing history.

License: MIT. Contact: hcac4735@agent.qq.com
