# Hermes Agent Claude Notes

- Third-party skills are reviewed per skill, not per repository.
- Prefer signed skills when the publisher provides detached signatures and a trust anchor.
- Treat deployment/install skills separately from ordinary usage skills.
- Do not send secrets in prompts. API keys, bearer tokens, cookies, and passwords belong in env vars, files, or connector configuration.
- Any skill that sends data to a non-local backend should present the exact destination and require explicit trust confirmation first.
- For non-trivial adopted skills, keep a review surface such as `skill-card.md` with purpose, secrets, network destinations, scripts, and risk class.
