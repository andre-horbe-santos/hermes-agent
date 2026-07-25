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

Backfill active posts published in the last 7–30 days, using short profile
output only. Enrich only authors that pass the ICP/lead qualification step.
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
| 7 days | 2,200 | US$4.40 | US$5.28 |
| 30 days | 17,058 | US$34.12 | US$40.94 |

These figures exclude optional full-profile enrichment. The short mode should
return name, profile URL, position and reaction/comment metadata. Full profile
enrichment can multiply the per-result price and should be applied only after
ICP qualification.

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
results and a budget of US$6 including retries. Expand to 30 days only after
checking deduplication and ICP enrichment behavior; budget approximately US$45
including retries and operational headroom.

## Recurring policy

Refresh only posts from the last 7 days on each cycle. Run a 30-day repair
window weekly or on demand. This avoids paying to re-read the full historical
corpus while preserving recent engagement signals.
