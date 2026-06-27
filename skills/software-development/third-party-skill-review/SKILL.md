---
name: third-party-skill-review
description: Use when reviewing external skills for trust and fit.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, security, governance, supply-chain, review]
    related_skills: [hermes-agent-skill-authoring, requesting-code-review]
---

# Third-Party Skill Review

Review external skills as individual supply-chain artifacts. Confirm what the skill does, what it can access, and whether it is safe to enable. Do not trust a whole repository because some skills look useful.

## When to Use

- User wants to evaluate a third-party skill repository
- User asks whether a vendor skill is safe to install or enable
- User wants a comparison between an external skill set and Hermes/Koncepto
- User asks for a skill-card, signing, or trust policy for skills

## Prerequisites

- Access to the skill repository or extracted skill directory
- `references/policy.md`
- `shared/governance/SKILL-CARD-TEMPLATE.md`
- `scripts/verify_skill_signature.sh` when a detached signature exists

## Procedure

1. Read `references/policy.md`.
2. Review the skill as a unit.
3. Classify the risk.
4. Fill the skill card.
5. Verify signature if present.
6. Decide: approve, approve with restrictions, or reject.

## Verification

- The skill card names the risk class and network surface.
- The trust decision is based on evidence, not brand name.
- Any external endpoint is documented before enablement.
