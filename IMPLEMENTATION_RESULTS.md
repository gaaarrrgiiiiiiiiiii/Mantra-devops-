# Application/platform implementation results

Implementation date: 4 November 2026, Asia/Kolkata. Source: `platform/application-acceptance`, PR #4. Production promotion remains subject to independent review and the protected-main workflow.

Production update: PR #4 was approved by Bazzin07, merged as `c4c3dcf`, and deployed by Jenkins #6. Live migrations, application acceptance and backup restore passed. See [RELEASE_ACCEPTANCE.md](RELEASE_ACCEPTANCE.md); the pre-deployment requirements below are retained as implementation history.

## Delivered

- Packaged, versioned Alembic baseline and native retrieval migration, with 768-dimensional pgvector columns, generated full-text search, saved-vector/cache backfills and GIN/HNSW indexes. No existing documents or JSON embeddings are dropped.
- PostgreSQL startup requires the release's migration revision; automatic API schema creation is disabled for PostgreSQL. Migration failure leaves the previous image reference persisted and its running service available.
- Pre-migration backup and protected previous configuration support controlled recovery/rollback. Migrations are additive and forward-only; restore tests use a separate disposable database.
- Reproducible Python dependency lock and runtime OCR dependencies, plus secret exclusions in the backend Docker context.
- Fixed native zero-vector NaN matches, deterministic responses labelled as external LLM output, and ISO/OISD reference separator mismatches that hid evidence. Legacy stored reference spellings remain queryable.
- Bounded upload reads, gateway body limit and forwarded-header replacement, configurable production rate limiting, and preserved authentication/TLS/network isolation.
- Expanded acceptance tests for ingestion/formats/OCR, retry recovery, graph, maintenance, compliance, incident analysis, streaming citations, administration, authentication, readiness and PostgreSQL migrations/retrieval/cache/persistence.
- Release evidence now compares the running image's registry digest with ECR's digest for the expected commit and checks the expected migration revision, rather than accepting any nonempty digest/version.

## Verification evidence

- **68 tests passed** in the candidate runtime image against isolated fixtures and disposable PostgreSQL databases. This includes fresh/populated/unversioned upgrades, repeated migration, malformed-vector rollback, native retrieval with fallback forbidden and restart persistence.
- Candidate image built with the pinned dependency lock and OCR packages. Document fixtures for TXT, MD, CSV, EML text, PDF, DOCX, XLSX, PPTX and PNG OCR passed.
- The migration packaging contract passes locally. Python compilation and Git whitespace checks passed; Jenkinsfile syntax validation passed. Deployment syntax was checked separately from deployment execution.
- Full-stack validation is run using `scripts/validate-containers.sh` in `/tmp/mantra-application-verify`, separate from production. It checks migration, gateway/SPA/API authentication and rate limiting, dependency failure/recovery, PostgreSQL restore, Prometheus targets and service isolation. Raw operator evidence is kept under the implementation verification directory; final results are recorded in PR #4.
- Required GitHub Actions and Jenkins snapshot verification must be evaluated for the published candidate SHA. PR #4 provides the authoritative latest CI state; this file does not substitute for required checks.

## Deployment and acceptance still required

An independent writer/reviewer must approve the final source before protected-main merge. After merge, Jenkins must deploy the merged SHA; the operator then verifies backup, live migration version, ECR/running digest, platform checks and deployed application behavior. The current production baseline is not silently treated as the new application release.

The existing demonstration provider mode is retained. Meaningful ML clustering, real external-provider quality evaluation, per-user RBAC, asynchronous ingestion and broader industrial validation are explicitly outside this candidate's verified scope. See [APPLICATION_ENGINEER_CHECKLIST.md](APPLICATION_ENGINEER_CHECKLIST.md) for pending acceptance and access handoff.
