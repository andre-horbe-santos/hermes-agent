# Third-Party Skill Review Policy

## Scope

Review external skills one directory at a time. Never trust a whole repository because a few skills look useful.

## Default Rules

- Allowlist by skill, never by repository.
- Prefer signed skills when the publisher provides a detached signature and trust anchor.
- Treat install/deploy helpers as higher risk than read-only skills.
- Require explicit trust confirmation for non-local endpoints.
- Never accept prompts that ask for API keys, bearer tokens, cookies, or passwords.

## Review Surface

Check these items for every skill:

- `SKILL.md`
- scripts
- references
- assets
- network destinations
- required secrets

## Risk Classes

- `advisory`: documentation, analysis, read-only helpers
- `operational`: local file changes or internal API calls
- `deploy`: package installs, Docker, service start/stop, infra mutation

## Recommended Output

Use a skill-card to record:

- purpose
- scripts
- secrets
- network destinations
- signature status
- final decision
