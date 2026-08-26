#!/usr/bin/env python3
"""Read-only SPF, DKIM, and DMARC DNS auditor using the local `dig` command."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field

COMMON_SELECTORS = ("google", "selector1", "selector2", "default", "k1", "s1", "s2", "smtp")
LOOKUP_MECHANISMS = {"a", "mx", "include", "exists", "redirect"}


@dataclass
class Finding:
    severity: str
    code: str
    message: str


@dataclass
class Audit:
    domain: str
    records: dict[str, object] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str) -> None:
        self.findings.append(Finding(severity, code, message))


def txt_records(name: str) -> list[str]:
    proc = subprocess.run(
        ["dig", "+short", "+time=3", "+tries=2", "TXT", name],
        check=False, capture_output=True, text=True, timeout=10,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"dig failed for {name}")
    records = []
    for line in proc.stdout.splitlines():
        chunks = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
        records.append("".join(chunks) if chunks else line.strip())
    return [record for record in records if record]


def normalize_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".").removeprefix("@")
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("invalid internationalized domain") from exc
    labels = domain.split(".")
    if not domain or len(domain) > 253 or any(
        not label or len(label) > 63
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        raise ValueError("invalid domain name")
    return domain


def parse_tags(record: str) -> tuple[dict[str, str], list[str]]:
    tags: dict[str, str] = {}
    duplicates: list[str] = []
    for part in record.split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            tags[f"__malformed_{len(tags)}"] = part.strip()
            continue
        key, value = (piece.strip() for piece in part.split("=", 1))
        key = key.lower()
        if key in tags:
            duplicates.append(key)
        tags[key] = value
    return tags, duplicates


def audit_spf(audit: Audit) -> None:
    roots = [r for r in txt_records(audit.domain) if r.lower().startswith("v=spf1")]
    audit.records["spf"] = {"domain": audit.domain, "records": roots, "dns_lookups": None}
    if not roots:
        audit.add("error", "spf_missing", "No SPF record was found at the root domain.")
        return
    if len(roots) > 1:
        audit.add("error", "spf_multiple", "Multiple SPF records were published; SPF returns PermError.")
        return

    visited: set[str] = set()
    active: set[str] = set()
    lookup_count = 0

    def inspect(domain: str, record: str) -> None:
        nonlocal lookup_count
        if domain in active:
            audit.add("error", "spf_cycle", f"SPF include/redirect cycle detected at {domain}.")
            return
        if domain in visited:
            return
        visited.add(domain)
        active.add(domain)
        for term in record.split()[1:]:
            raw = term.lstrip("+~-?")
            mechanism, _, argument = raw.partition(":")
            mechanism = mechanism.split("/", 1)[0].lower()
            if mechanism in LOOKUP_MECHANISMS:
                lookup_count += 1
            if mechanism in {"ip4", "ip6"} and argument:
                try:
                    ipaddress.ip_network(argument, strict=False)
                except ValueError:
                    audit.add("error", "spf_invalid_ip", f"Invalid {mechanism} network: {argument}.")
            if mechanism in {"include", "redirect"} and argument:
                children = [r for r in txt_records(argument) if r.lower().startswith("v=spf1")]
                if len(children) != 1:
                    audit.add("error", "spf_dependency", f"{mechanism} target {argument} has {len(children)} SPF records.")
                else:
                    inspect(argument, children[0])
        active.remove(domain)

    inspect(audit.domain, roots[0])
    audit.records["spf"]["dns_lookups"] = lookup_count
    if lookup_count > 10:
        audit.add("error", "spf_lookup_limit", f"SPF uses at least {lookup_count} DNS-query mechanisms; the limit is 10.")
    if not re.search(r"(?:^|\s)[+~?-]?all(?:\s|$)", roots[0], re.I):
        audit.add("warning", "spf_no_all", "The root SPF record has no explicit all mechanism.")
    elif re.search(r"(?:^|\s)~all(?:\s|$)", roots[0], re.I):
        audit.add("warning", "spf_softfail", "SPF ends in ~all (softfail); review whether -all is appropriate.")
    elif re.search(r"(?:^|\s)\?all(?:\s|$)", roots[0], re.I):
        audit.add("warning", "spf_neutral", "SPF ends in ?all and provides little enforcement.")


def audit_dmarc(audit: Audit) -> None:
    name = f"_dmarc.{audit.domain}"
    records = [r for r in txt_records(name) if r.lower().startswith("v=dmarc1")]
    audit.records["dmarc"] = {"name": name, "records": records}
    if not records:
        audit.add("error", "dmarc_missing", "No DMARC record was found.")
        return
    if len(records) > 1:
        audit.add("error", "dmarc_multiple", "Multiple DMARC records were published.")
        return
    tags, duplicates = parse_tags(records[0])
    audit.records["dmarc"]["tags"] = tags
    if duplicates:
        audit.add("error", "dmarc_duplicate_tags", f"Duplicate DMARC tags: {', '.join(sorted(set(duplicates)))}.")
    if any(key.startswith("__malformed_") for key in tags):
        audit.add("error", "dmarc_malformed", "DMARC contains a segment without tag=value syntax.")
    policy = tags.get("p", "").lower()
    if policy not in {"none", "quarantine", "reject"}:
        audit.add("error", "dmarc_policy", "DMARC p must be none, quarantine, or reject.")
    elif policy == "none":
        audit.add("warning", "dmarc_monitoring", "DMARC is monitoring only (p=none); spoofed mail is not rejected by policy.")
    try:
        pct = int(tags.get("pct", "100"))
        if not 0 <= pct <= 100:
            raise ValueError
        if pct < 100:
            audit.add("warning", "dmarc_partial", f"DMARC applies to only pct={pct}% of messages.")
    except ValueError:
        audit.add("error", "dmarc_pct", "DMARC pct must be an integer from 0 through 100.")
    if "rua" not in tags:
        audit.add("warning", "dmarc_no_rua", "No aggregate report destination (rua) is configured.")
    if tags.get("sp", policy).lower() == "none" and policy != "none":
        audit.add("warning", "dmarc_subdomain_monitoring", "DMARC sp=none leaves subdomains in monitoring-only mode.")


def audit_dkim(audit: Audit, selectors: list[str]) -> None:
    results = []
    unique_selectors = list(dict.fromkeys(s.strip().lower() for s in selectors if s.strip()))
    for selector in unique_selectors:
        name = f"{selector}._domainkey.{audit.domain}"
        dkim_records = [r for r in txt_records(name) if "p=" in r.lower()]
        item: dict[str, object] = {"selector": selector, "name": name, "records": dkim_records}
        if dkim_records:
            tags, duplicates = parse_tags(dkim_records[0])
            item["tags"] = tags
            if len(dkim_records) > 1 or duplicates:
                audit.add("error", "dkim_multiple", f"Selector {selector} has ambiguous or duplicate DKIM data.")
            public_key = re.sub(r"\s+", "", tags.get("p", ""))
            if not public_key:
                audit.add("warning", "dkim_revoked", f"Selector {selector} has an empty p= value (revoked key).")
            else:
                key_type = tags.get("k", "rsa").lower()
                if key_type == "rsa" and shutil.which("openssl"):
                    try:
                        key_der = base64.b64decode(public_key, validate=True)
                        proc = subprocess.run(
                            ["openssl", "pkey", "-pubin", "-inform", "DER", "-text", "-noout"],
                            input=key_der, capture_output=True, timeout=5,
                        )
                        match = re.search(rb"Public-Key:\s*\((\d+) bit\)", proc.stdout)
                        if match:
                            key_bits = int(match.group(1))
                            item["key_bits"] = key_bits
                            if key_bits < 2048:
                                audit.add("warning", "dkim_short_key", f"Selector {selector} uses a {key_bits}-bit RSA key; 2048 bits is preferred.")
                    except (ValueError, subprocess.TimeoutExpired):
                        audit.add("warning", "dkim_key_parse", f"Selector {selector} has a p= value that could not be parsed as an RSA public key.")
        results.append(item)
    audit.records["dkim"] = results
    if unique_selectors and not any(item["records"] for item in results):
        audit.add("warning", "dkim_unverified", "No key was found for tested selectors; this does not prove DKIM is absent.")
    elif not unique_selectors:
        audit.add("info", "dkim_selector_needed", "DKIM was not checked because DNS has no selector index.")


def render_text(audit: Audit) -> str:
    lines = [f"Email authentication audit: {audit.domain}"]
    spf = audit.records.get("spf", {})
    lines.append(f"SPF: {', '.join(spf.get('records', [])) or 'not found'}")
    if spf.get("dns_lookups") is not None:
        lines.append(f"SPF DNS-query mechanisms (conservative): {spf['dns_lookups']}")
    dmarc = audit.records.get("dmarc", {})
    lines.append(f"DMARC: {', '.join(dmarc.get('records', [])) or 'not found'}")
    dkim = audit.records.get("dkim", [])
    if dkim:
        lines.append("DKIM selectors: " + ", ".join(
            f"{item['selector']}={'found' if item['records'] else 'not found'}" for item in dkim
        ))
    lines.append("Findings:")
    lines.extend(
        (f"  {finding.severity.upper()}: [{finding.code}] {finding.message}" for finding in audit.findings),
    )
    if not audit.findings:
        lines.append("  PASS: no issues found in the checks performed")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain")
    parser.add_argument("--selector", action="append", default=[], help="DKIM selector; repeat as needed")
    parser.add_argument("--discover-common", action="store_true", help="Probe common DKIM selector names")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args()
    if not shutil.which("dig"):
        parser.error("dig is required")
    try:
        domain = normalize_domain(args.domain)
        selectors = args.selector + (list(COMMON_SELECTORS) if args.discover_common else [])
        audit = Audit(domain)
        audit_spf(audit)
        audit_dmarc(audit)
        audit_dkim(audit, selectors)
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(audit), ensure_ascii=False, indent=2) if args.json else render_text(audit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
