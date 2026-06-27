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
- `shared/governance/SKILLS-INTAKE.md`
- `shared/governance/SKILL-CARD-TEMPLATE.md`
- `scripts/verify_skill_signature.sh` when a detached signature exists

## Procedure

1. Review the skill as a unit:
   - `SKILL.md`
   - scripts
   - references
   - assets
   - network destinations
   - required secrets
2. Classify the skill:
   - `advisory`
   - `operational`
   - `deploy`
3. Search for risky patterns:
   - `subprocess`
   - `os.system`
   - `eval(`
   - `exec(`
   - `pip install`
   - `docker run`
   - `curl`
   - `wget`
4. Fill the skill card.
5. Verify signature if present.
6. Decide:
   - approve
   - approve with restrictions
   - reject

## Decision Rules

- Allowlist by skill, never by repository.
- Prefer signed skills when a publisher provides signatures and a trust anchor.
- Treat install/deploy helpers as higher risk than read-only skills.
- Require explicit trust confirmation for non-local endpoints.
- Never accept prompts that ask for API keys, bearer tokens, cookies, or passwords.

## Verification

- The skill card names the risk class and network surface.
- The trust decision is based on evidence, not brand name.
- Any external endpoint is documented before enablement.
