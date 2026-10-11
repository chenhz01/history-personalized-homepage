# Changelog

## v0.1.1 — 2026-10-11 (self-review revision, iteration 2)

### Added
- **XSS-hardening test**: title `<script>alert(1)</script>` must render
  HTML-escaped (`&lt;script&gt;`) — v0.1.0 escaped everything via
  `html.escape` but had no test proving it. Self-review against ALIGNMENT
  rule 85 (safety) flagged the untested security property. Test count 13 → 15.
- **Filter-bubble second-order effect** in README, with the concrete
  countermeasure (fixed unscored "explore" slot) — absent in v0.1.0.

### Improved (safety/completeness dimension)
- README: privacy priority moved to the front of Design Trade-offs; added
  the history-file-is-a-high-value-artifact warning to Limits.
- Removed a dead conditional from the functional test (clarity pass).

## v0.1.0 — 2026-10-11 (initial draft)

- Loader: JSONL events with per-line validation; malformed lines skipped
  and counted (never silent).
- Scorer: recency-weighted domain frequency, 7-day half-life, future
  timestamps clamped, `www.` normalized.
- Renderer: deterministic HTML, top-N links with score/age, HTML-escaped,
  `--redact-titles` mode, explicit empty-state placeholder.
- CLI: `homepage.py --history --out --top --redact-titles` (argparse).
- `self_test.py`: 13 tests across functional / error-path / extreme-edge
  (empty history, future timestamps, 20k events, binary garbage).
- README, LICENSE (MIT), initial alignment audit.
