# Platform Notes

## Google Ads

Use GAQL and the Google Ads resource metadata to discover compatible fields rather
than guessing field names. Include the customer ID when working across a manager
account hierarchy. Prefer `Search`/`SearchStream` for reporting and validation-only
operations before mutation.

The official `googleads/google-ads-mcp` project exposes account search, customer
discovery, resource metadata, metrics, segments, release notes, and an
`account-performance-diagnostics` agent skill. It is an execution dependency, not a
replacement for this skill's approval policy.

## Meta Ads and other platforms

Use the platform's native API or MCP connector. Map concepts explicitly: campaign,
ad set/ad group, ad, conversion, spend, reach, frequency, CPM, CTR, CPC, CPA, ROAS,
and attribution windows are not interchangeable across platforms.

## Data handling

Treat customer lists, hashed identifiers, CRM exports, conversion uploads, and account
credentials as sensitive. Minimize data passed to the model, avoid logging secrets,
and ask for confirmation before uploads or permission changes.
