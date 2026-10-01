# Security policy

Please report suspected vulnerabilities privately through GitHub's security-advisory feature. Do not include secrets, personal data, or exploit details in a public issue.

## Implemented controls

- API keys are stored as SHA-256 hashes and tenant identity comes from the authenticated server context.
- All document, search, query, and tool data access is tenant scoped.
- Agent tools are allowlisted, schema validated, read only, and audited.
- Document formats and sizes are validated before parsing.
- Retrieved prompt-injection phrases are filtered before answer construction.
- Redis applies a shared tenant request limit, with a documented availability-first failure policy.
- Events use a transactional outbox and idempotent consumer receipts.
- Browser-facing responses include restrictive content, framing, referrer, and cache headers.

These controls reduce risk but do not constitute a completed third-party security audit.
