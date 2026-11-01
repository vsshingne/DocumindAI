# DocuMind implementation plan

## Scope and execution

Build a modular monolith with independently scalable Celery workers. PostgreSQL is
the source of truth; Qdrant is a rebuildable search index; Redis is a broker and
rate-limit store; document bytes live behind an object-storage interface. The API
never performs OCR or embedding work in a request. All factual answers must cite
retrieved evidence or explicitly abstain.

Each milestone must leave the repository runnable, add relevant tests, and record
actual command results in `progress.md`. Infrastructure that cannot be exercised
locally is explicitly unverified. No benchmark numbers or dashboard metrics may
be invented. Authentication and tenant constraints start in the foundation rather
than being retrofitted after ingestion.

## Milestones and acceptance gates

1. **Foundation:** typed settings; relational tenant/user/document/chunk/job/chat/
   evaluation schema; explicit Alembic migration; dependency-aware health endpoints;
   structured errors/logs/metrics; Docker Compose infrastructure; lint/type/test CI.
   Gate: unit tests, migration round trip, PostgreSQL integration tests and Compose
   startup when a Docker engine is available.
2. **Document intelligence:** authenticated uploads, hashing and duplicate handling,
   bounded format validation, local storage protocol, per-format parsers, PDF OCR
   with confidence/errors, tables/layout, labeled heuristic extraction, transactional
   job dispatch and bounded idempotent processing. Gate: parser/security tests and
   ingestion through workers, including crash recovery.
3. **Retrieval:** configurable source-preserving chunking; cached batched Sentence
   Transformers; named dense/sparse vectors in Qdrant; native RRF hybrid search;
   tenant/document/date filters and optional cross-encoder reranking. Gate: real
   Qdrant integration plus deterministic embedding doubles in CI.
4. **Grounded RAG:** provider protocol, local/OpenAI-compatible provider, versioned
   prompt, bounded context, server-owned citation metadata, citation and evidence
   checks, explicit abstention, persistent chats. Gate: deterministic end-to-end
   tests including invalid citations, conflicts, injection and unavailable provider.
5. **Security:** complete JWT/Argon2 authentication, RBAC, tenant-scoped repositories,
   Redis rate limiting, protected file access. Gate: adversarial cross-tenant tests
   for every resource, history, evaluations and vector queries.
6. **Frontend:** React/TypeScript/Vite/Tailwind/TanStack Query dashboard, upload and
   extraction inspection, chat with evidence cards, evaluation run views, accessible
   errors/loading/empty states. Gate: production build and browser workflows.
7. **Evaluation:** versioned synthetic corpus and direct/multi-page/table/cross-doc/
   ambiguous/conflicting/unanswerable cases; ranking metrics, explicit generation
   metric definitions, JSON/CSV reports, stage timing. Gate: reproducible measured
   reports, with unavailable judge metrics labeled unavailable.
8. **Hardening:** full monitoring dashboards, security/dependency checks, deployment
   runbooks, clean checkout and worker restart tests, complete definition-of-done
   audit. Gate: actual deployment evidence; local tests alone are not production
   readiness.

## Design decisions

- Python 3.12 is the container baseline; development also tests Python 3.13.
- SQLAlchemy synchronous transactions simplify worker/API transaction ownership.
  Blocking API work will run in FastAPI threadpool endpoints; health probes are async.
- UUID identifiers and composite tenant foreign keys prevent cross-tenant links at
  the relational layer. Authorization must additionally scope every read/write.
- PostgreSQL uniqueness resolves upload races. A job/outbox row is committed with
  the document; a dispatcher will retry broker publication. At-least-once delivery
  requires idempotent processing, leases and an attempt ceiling.
- Partial vectors must not be searchable until a document has completed processing;
  retrieval must intersect index hits with authorized completed relational records.
- Model identifiers, dimensions, credentials and thresholds belong in settings.
- No externally supplied tenant ID can grant membership. Registration will create a
  new tenant; joining an existing tenant requires an administrator-controlled flow.
- No production secrets or generated benchmark results belong in source control.
