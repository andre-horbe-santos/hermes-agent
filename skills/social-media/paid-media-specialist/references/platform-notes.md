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

### Hermes configuration

After configuring Google Ads credentials, add the server to the profile's
`config.yaml` under `mcp_servers` and restart Hermes:

```yaml
mcp_servers:
  google-ads:
    command: "uvx"
    args:
      - "--from"
      - "git+https://github.com/googleads/google-ads-mcp.git"
      - "google-ads-mcp"
    env:
      GOOGLE_APPLICATION_CREDENTIALS: "/absolute/path/to/google-ads-credentials.json"
      GOOGLE_PROJECT_ID: "your-google-cloud-project"
      GOOGLE_ADS_DEVELOPER_TOKEN: "your-developer-token"
      GOOGLE_ADS_LOGIN_CUSTOMER_ID: "your-manager-customer-id"
    timeout: 180
    connect_timeout: 90
```

The official server was smoke-tested from this checkout on 2026-08-12: `uvx`
successfully built and launched it over stdio. The test did not authenticate or
call a live customer account. Keep credentials in the profile's secret store or
`.env` workflow where possible; do not commit them to YAML.

The MCP server's default surface is primarily discovery and reporting. Treat any
future mutation-capable server as a separate security review: expose read-only
tools first, then enable only the smallest approved mutation set.

## Meta Ads and other platforms

Use the platform's native API or MCP connector. Map concepts explicitly: campaign,
ad set/ad group, ad, conversion, spend, reach, frequency, CPM, CTR, CPC, CPA, ROAS,
and attribution windows are not interchangeable across platforms.

## Data handling

Treat customer lists, hashed identifiers, CRM exports, conversion uploads, and account
credentials as sensitive. Minimize data passed to the model, avoid logging secrets,
and ask for confirmation before uploads or permission changes.
