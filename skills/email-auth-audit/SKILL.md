---
name: email-auth-audit
description: Audit a domain's SPF, DKIM, and DMARC DNS configuration and explain deliverability or spoofing-protection findings. Use when checking email authentication, DNS mail records, DKIM selectors, DMARC policy, or an email domain's technical readiness.
metadata:
  short-description: Audit SPF, DKIM, and DMARC
---

# Email Authentication Audit

Run the deterministic auditor before interpreting results:

```bash
python scripts/audit_email_auth.py example.com --discover-common
```

If the user provides DKIM selectors, pass each one explicitly. Use `--json`
when structured output is useful. Resolve the script path relative to this
`SKILL.md`.

## Interpretation

- Separate DNS publication from end-to-end authentication. A published DKIM
  key does not prove outbound messages are signed; validate a real message's
  `Authentication-Results` header when available.
- Do not report DKIM as absent when no selector is known. Report it as
  unverified and ask for a selector or raw delivered-message headers.
- Treat multiple SPF records, malformed DMARC tags, invalid policies, SPF
  recursion cycles, and SPF lookup counts above 10 as errors.
- Treat `p=none`, SPF `~all`/`?all`, missing aggregate reporting, and RSA keys
  below 2048 bits as hardening warnings rather than syntax failures.
- Explain that SPF authenticates the envelope domain; DMARC requires alignment
  of SPF or DKIM with the visible `From` domain.
- Preserve current mail providers/includes. Never invent a replacement SPF
  record without resolving what the existing mechanisms authorize.

The auditor performs read-only DNS queries and never modifies DNS.
