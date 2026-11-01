# Security model

## Implemented foundation

- Every tenant-owned row has a tenant foreign key.
- Composite tenant/parent foreign keys prevent cross-tenant document uploaders,
  chunks, jobs, session owners, messages, search history and evaluation owners.
- Database check constraints reject invalid states, roles and negative indices.
- Settings redact secret values and reject unsafe production settings.
- Errors omit driver exceptions and Pydantic input values.
- Structured request logs exclude raw paths, query strings, bodies and credentials.
- Metrics use route templates, bounded HTTP methods and status codes.
- Containers expose API and monitoring only on loopback; data services are private
  unless the development override is explicitly selected.

## Remaining security work

Argon2 password hashing, JWT validation, RBAC, membership management, tenant-scoped
repositories, document access controls, safe upload/parsing, rate limiting and
prompt-injection resistance are not implemented in the foundation. Database
integrity tests do not prove HTTP or vector isolation. Those guarantees must be
tested at each service boundary before user documents can be accepted.

Document content will be treated as untrusted data. A system prompt alone cannot
guarantee prompt-injection immunity: tools must remain unavailable to the document
generation path, citations must be resolved against authorized retrieved chunks,
and unsupported claims must trigger abstention. Conflicting evidence requires
explicit handling rather than unsupported confidence claims.

Do not expose this foundation directly to the internet. Production requires ingress
access control for operational endpoints, TLS, service credentials, upload resource
limits, backup/restore tests and review of the deployment threat model.

## Reported generic-password finding (2026-11-02)

GitGuardian flagged a database URL template in commit `634cb65`. The displayed
expression interpolated the `POSTGRES_PASSWORD` environment variable at runtime;
the committed line did not contain a password value. The `.env` file is ignored and
was not tracked in that commit. The URL template has been removed from the current
Compose and example files. The application now assembles the URL from separate
settings, and a regression test verifies generated `.env` files work without a
committed credential URL. The historical commit still exists in Git history, so
the alert itself may remain open until classified in GitGuardian. Any separate
finding that shows an actual literal credential requires its own impact review and
rotation.
