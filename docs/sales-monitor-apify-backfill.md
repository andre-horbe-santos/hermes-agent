# Sales Monitor — Apify engagement backfill

## Decision

Use Apify for LinkedIn reaction and comment author backfill, while retaining
Unipile for post-level counters, especially repost/share counts. Do not make
reposter identity a dependency: the two tested repost Actors returned zero
items for a post that Unipile reported with 87 reposts.

Use the existing Sales Monitor persistence path (`ssk_page_engagements`,
`ssk_engagements`, `ssk_leads`) with idempotent upserts. The existing
`backfill_page_engagements.py` remains the synchronization step into leads.

## Initial scope

Backfill active posts published in the last 7–30 days. Use short profile
output for comments and main profile resolution for reactions, because the
reaction Actor can otherwise return obfuscated `ACo...` identifiers. Enrich
only authors that pass the ICP/lead qualification step.
Do not invoke an LLM per raw reaction or comment.

Current database snapshot used for the estimate:

| Window | Active posts | Recorded reactions | Recorded comments | Recorded shares |
|---|---:|---:|---:|---:|
| 7 days | 25 | 1,994 | 206 | 160 |
| 30 days | 86 | 15,975 | 1,083 | 743 |

## Cost estimate

The current Apify Store prices are approximately US$0.002 per reaction result
and US$0.002 per comment result in the free tier. Therefore the expected
capture cost is:

| Window | Results to capture | Base Apify cost | With 20% retry margin |
|---|---:|---:|---:|
| 7 days | 2,200 | US$8.39 | US$10.07 |
| 30 days | 17,058 | US$66.07 | US$79.28 |

These figures include the current main-profile resolution surcharge for
reactions (US$0.002 per reaction) and exclude optional full-profile
enrichment. Main/short output returns name, profile URL, position and
reaction/comment metadata. Full profile enrichment can multiply the per-result
price and should be applied only after ICP qualification.

Shares are currently treated as a counter from Unipile, so they add no Apify
backfill cost. Repost Actors are not reliable enough for this workflow. If a
future test proves one usable, the observed Store prices range from about
US$0.00155 to US$0.005 per repost; the current 7/30-day counters would add
roughly US$0.25–0.80 / US$1.15–3.72, respectively.

## Infrastructure

No new database or always-on service is required initially. Add a bounded
worker/cron with:

- queue entries keyed by post URL/URN and signal type;
- checkpoint and retry state per post;
- concurrency limits to protect Apify and Unipile;
- upsert keys that prevent duplicate signals;
- a final synchronization pass into `ssk_leads` and `ssk_engagements`.

The 7-day run is the recommended first pilot: 25 posts, approximately 2,200
results and a budget of US$12 including retries. Expand to 30 days only after
checking deduplication and ICP enrichment behavior; budget approximately US$85
including retries and operational headroom.

## Recurring policy

Refresh only posts from the last 7 days on each cycle. Run a 30-day repair
window weekly or on demand. This avoids paying to re-read the full historical
corpus while preserving recent engagement signals.

## Status — 2026-07-25/26: pilot partially run, blocked by account plan

`APIFY_API_TOKEN` was only exported in the operator's shell profile, not in
`~/.hermes/.env` where `apify_backfill.py` actually reads it from — added
2026-07-26, same convention as every other credential in this project.

First execution attempt (`--dry-run`) ran the real Apify actors for 23
posts (7-day window) — **`--dry-run` in this script only skips the database
write, not the actual paid actor call** (see `_process()` in
`apify_backfill.py`). Real cost was incurred: 131 comments + 1136 accepted
reactions + 32 skipped = ~1,300 results, ~US$2.60. The immediate follow-up
real run (`--days 7`, no `--dry-run`) failed instantly with `403
platform-feature-disabled: Monthly usage hard limit exceeded` — this Apify
account is on a **free-tier plan capped at US$5.00/month**
(`maxMonthlyUsageUsd: 5`), not the ~US$8-12 this document assumed was
available. The dry-run's real spend alone pushed usage to US$5.07. Monthly
cycle resets 2026-08-12.

Because Apify retains completed run datasets for 7 days and dataset reads
don't count against the actor-compute usage cap, the 23 posts' worth of
comments/reactions already paid for in the dry-run were recovered from the
existing dataset IDs (no new actor invocation) and persisted — totals
matched the dry-run summary exactly (131/1136/32, `posts_not_found: 0`).
So today's ~US$2.60 spend is not wasted; it's the only data captured so far.

**Blocked until André decides**: upgrade the Apify plan (removes the hard
cap, unlocks the rest of the 7-day pilot + eventual 30-day expansion) or
wait for the 2026-08-12 reset. No further Apify calls should be made before
that decision — even `--dry-run` will fail identically until then.
