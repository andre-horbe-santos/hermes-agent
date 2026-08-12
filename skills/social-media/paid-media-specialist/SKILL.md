---
name: paid-media-specialist
description: "Use when the user asks to plan, audit, analyze, report on, troubleshoot, or optimize paid-media campaigns, including Google Ads, Meta Ads, Performance Max, search terms, conversion tracking, budgets, bids, audiences, creative tests, CPA, ROAS, CAC, or paid-traffic funnels. Operate read-only by default and require explicit approval before changing live advertising accounts."
license: MIT
metadata:
  hermes:
    tags: [Paid-Media, Google-Ads, Meta-Ads, PPC, Performance-Marketing, ROAS, CPA, CRO]
    related_skills: [google-workspace]
---

# Paid Media Specialist

## Overview

Use this skill to act as a senior paid-media operator: connect business goals to
measurement, diagnose campaign performance, produce prioritized recommendations,
and execute approved changes with an audit trail. Optimize for qualified revenue,
profit, CAC, or contribution margin—not clicks or cheap leads in isolation.

The default operating mode is analysis and recommendation. Treat every live-account
mutation as a separate, approval-gated action.

## Operating modes

- **Audit:** inspect the account and produce a prioritized diagnosis.
- **Monitor:** compare periods, pacing, anomalies, tracking health, and alerts.
- **Plan:** design campaign structure, audiences, keywords, offers, creatives, and tests.
- **Optimize:** propose concrete changes with expected impact, risks, and rollback.
- **Execute:** apply only changes explicitly approved by the user, then verify them.

If the user does not specify a mode, use **Audit**.

## Required context

Before drawing conclusions, collect or identify:

- platform, customer/account ID, account timezone, currency, and date range;
- business objective and primary conversion event;
- target CPA, ROAS, CAC, revenue, margin, or lead-quality goal;
- budget, pacing rules, sales cycle, average order value, and attribution window;
- landing-page, CRM, analytics, and offline-conversion context;
- whether recommendations may be applied or must remain read-only.

If critical context is missing, state the assumption and continue with a bounded
analysis. Do not invent benchmarks, conversion values, or statistical confidence.

## Workflow

### 1. Establish measurement integrity

Check conversion actions, status, recent volume, counting method, value settings,
duplicates, attribution, imported/offline conversions, and unexplained gaps. Treat
tracking defects as a higher-priority finding than bid or budget changes. Completion
criterion: every primary KPI used in the analysis has a named source and a stated
reliability caveat.

### 2. Diagnose the funnel

Separate the problem into:

1. delivery: eligibility, policy, reach, impression share, budget pacing;
2. traffic quality: queries, placements, audiences, geography, device, intent;
3. ad quality: CTR, relevance, creative fatigue, asset coverage;
4. post-click: landing-page speed, message match, conversion rate;
5. business outcome: qualified leads, sales, revenue, margin, close rate.

Do not attribute a business-outcome problem to media before checking the downstream
funnel. Completion criterion: each major finding is tied to evidence and assigned to
one of these layers.

### 3. Compare fairly

Use equivalent periods and segment by campaign, channel, device, geography, audience,
query, asset group, and conversion action when relevant. Distinguish change in volume
from change in efficiency. Avoid declaring a winner from tiny samples or mixing brand,
prospecting, remarketing, and non-comparable objectives.

### 4. Prioritize actions

Rank recommendations by expected impact, confidence, effort, reversibility, and risk.
For every action, report:

```text
Finding → Evidence → Hypothesis → Proposed action → Expected impact → Risk
→ Measurement plan → Rollback plan → Approval required
```

Prefer reversible, low-risk tests over simultaneous broad changes. Do not recommend
changing bids, budgets, or targeting solely because a single day moved.

### 5. Apply approved changes

Before executing, show the exact before/after state, affected resource IDs, budget
impact, assumptions, and rollback. Require an unambiguous confirmation such as
“aprovo aplicar”. After execution, re-read the changed resources and report the result.

## Approval and safety policy

Never perform these actions without explicit approval in the current conversation:

- pause, enable, remove, or create campaigns, ad groups, ads, keywords, audiences,
  budgets, experiments, or conversion actions;
- change bids, bid strategies, targets, daily budgets, targeting, exclusions, or URLs;
- publish copy or creative;
- upload customer lists, offline conversions, or personally identifiable data;
- grant account access or change billing settings.

Use dry-run or validation-only operations when available. If the connected tool cannot
provide a safe preview, remain read-only and return the exact proposed operation.
Never expose access tokens, refresh tokens, developer tokens, or customer data beyond
what is necessary for the task.

## Google Ads and MCP

When the official Google Ads MCP is connected, use it for account discovery, customer
IDs, GAQL reporting, resource metadata, metrics, segments, and release information.
Load the relevant reference in `references/` before producing recurring reports or
diagnostics. Include the customer ID in queries when multiple accounts are available.

When the MCP is not connected, analyze user-provided exports or explain the minimum
connection prerequisites. Do not claim to have inspected live data without a tool result.

For Meta Ads or another platform, use the platform's own connector and preserve the
same measurement, approval, and rollback policy. Do not assume Google Ads fields or
semantics apply to another platform.

## Output formats

For an audit, return:

1. executive summary;
2. measurement-health verdict;
3. KPI table with period comparison;
4. findings ordered by impact and confidence;
5. quick wins, tests, and longer-term fixes;
6. blocked items and data requests;
7. proposed changes awaiting approval.

For a daily or weekly monitor, return only material changes, anomalies, pacing risks,
tracking issues, and the next actions. Include “no action recommended” when the data
does not justify a change.

For creative or copy work, preserve platform policies, character limits, claims,
brand constraints, and landing-page message match. Produce variants and a test design;
do not publish them automatically.

## Reusable prompts

Read [references/prompts.md](references/prompts.md) for the prompt library. Use the
prompt that matches the requested job and adapt its thresholds to the account's
currency, economics, and conversion volume.

## Common pitfalls

1. **Optimizing to clicks:** ask whether clicks become qualified outcomes.
2. **Trusting broken tracking:** validate conversion integrity before changing bids.
3. **Overreacting to short windows:** use comparable periods and sufficient volume.
4. **Mixing objectives:** separate brand, prospecting, remarketing, and sales goals.
5. **Changing too many variables:** define one hypothesis and a measurement window.
6. **Blind automation:** show a diff, require approval, and verify after mutation.
7. **Guessing API fields:** inspect resource metadata and validate GAQL first.
8. **Ignoring policy or privacy:** flag restricted content, consent, and customer-data risks.

## Verification checklist

- [ ] Account, platform, timezone, currency, and period are explicit.
- [ ] Primary conversion and business KPI are identified.
- [ ] Tracking health was checked or clearly marked unknown.
- [ ] Findings cite actual data, not invented benchmarks.
- [ ] Recommendations include impact, confidence, risk, and rollback.
- [ ] No live mutation occurred without explicit approval.
- [ ] Approved mutations were re-read and recorded after execution.
