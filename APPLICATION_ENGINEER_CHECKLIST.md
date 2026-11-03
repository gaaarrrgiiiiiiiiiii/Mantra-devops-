# Application engineer completion checklist

Owner: application engineer (Ayush / Bazzin07). Reviewed: 4 November 2026, Asia/Kolkata.

Use this alongside [the original work allocation](MANTRA_DEVOPS_PLAN.md), [platform evidence](PLATFORM_VERIFICATION.md) and [access and remote acceptance](TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md). A checked box means the stated evidence exists; an unchecked box is pending acceptance, not necessarily missing code.

## What is already submitted

- [x] Application work is submitted in [PR #3](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/3), branch `ayush/application-devops`, author `Bazzin07`, reviewed head `4dce2fa1a21ff1348e4a03d17e11391a2aa4c349`.
- [x] Its [CI run 41189460509](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/actions/runs/41189460509) passed frontend build, pytest and Docker validation. The workflow supplies a real pgvector PostgreSQL service and enables the PostgreSQL tests. The production endpoint job was skipped on the PR event; this is not deployment evidence.
- [x] PR includes upload/document/auth/copilot tests, OpenAPI checks, PostgreSQL persistence tests, frontend delivery and database initialization changes. Review and reuse this work rather than creating a duplicate implementation.
- [ ] Update PR against current canonical `main`, review overlapping platform changes, and rerun integrated checks. Preserve Caddy authentication/TLS, server-side API-key injection, non-root runtime, security scans, immutable ECR delivery and Ansible deployment. GitHub did not report a definite mergeability result during inspection; conflicts have not been established.
- [ ] Obtain review, merge, and verify the merged release on EC2. PR #3 was still open at inspection.

## 1. Own computer, repository and access

- [ ] Clone the canonical [deployment repository](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-) or use a fork with that repository as `upstream`. Confirm PR base is its `main`. A push only to `Bazzin07/Mantra` does not deploy this platform.
- [ ] Use a personal GitHub identity and feature branch; keep changes reviewable through PRs. Agree which repository paths each engineer reviews.
- [ ] Create a private local `.env` from `.env.example`; use local test database/bucket settings and separate credentials. Never copy production `.env`, private keys or Jenkins credentials into Git.
- [ ] Install project dependencies and document exact local startup, test and frontend build commands. Demonstrate a fresh clone works without files from the platform owner's laptop.
- [ ] Install AWS CLI and Session Manager plugin on the teammate's computer, use the existing application IAM identity, and perform the sign-in checks in the access guide. Report identity/session ID, never access keys.
- [ ] Confirm `whoami` is `mantra-app`, workspace is `/home/mantra-app/work`, and production secrets, Docker socket and sudo are inaccessible. This own-device confirmation is still pending.

## 2. Original application DevOps contract

### Backend and configuration

- [ ] Verify documented FastAPI routes and response/error contracts, including invalid input and missing resources. Keep OpenAPI examples accurate.
- [x] Platform now supplies liveness and dependency-aware readiness: database/Redis failures produce readiness failure while liveness remains available; existing five tests and live recovery checks passed.
- [ ] Preserve and rerun these health tests after integrating the PR. Confirm `/metrics` remains scrapeable on the private network, with request/status/latency metrics and no document contents or credentials in labels.
- [ ] Keep configuration environment-driven; document required/optional variables, defaults, validation and operating modes. Keep `.env.example` free of real secrets.
- [ ] Test S3 upload/download and error handling with the AWS default credential chain. Production uses the instance role; no static AWS keys embedded in app/image/frontend. Use a disposable test prefix, not production document deletion.
- [ ] Test Redis use, dependency failures and recovery; define whether cache failure is fatal or degraded for each feature.

### Database and retrieval: current release blocker

The live PostgreSQL `document_chunks` table has `embedding_json`, but lacks `embedding` and `ts_content`, which `_postgres_hybrid_search` expects. The pgvector extension is installed; extension presence alone does not establish the required application schema. No `alembic_version` table was found. The application README's migration/vector-index claims therefore exceed the observed deployment. PR #3 adds startup schema initialization, but is not deployed.

- [ ] Integrate and validate the PR's schema correction against the current platform; demonstrate native PostgreSQL retrieval actually executes rather than silently falling back.
- [ ] Supply versioned migrations for a new database and an existing populated database. Package `alembic.ini` and migrations in the backend image so the existing Ansible migration hook can run `alembic upgrade head`.
- [ ] Define extension/DDL privileges, vector dimensions and indexes; ensure documented HNSW/GIN claims match the actual schema. Test upgrading existing rows and backfilling vectors/search text.
- [ ] Disable automatic schema creation when migrations become authoritative. Document migration failure handling, data backup and rollback/forward-repair procedure; do not test destructive changes against production.
- [ ] Run real PostgreSQL tests for ingestion, persistence after restart, retrieval ranking, filters, citations and semantic cache. Record executed test counts and skips; a green SQLite-only run is insufficient.

### Containers, frontend and dependency delivery

- [x] Platform supplies production frontend container/gateway routing, a Python 3.11 backend running as a non-root user, persistent database/cache configuration and isolated production ports.
- [ ] Validate application changes in those actual images; package runtime data files and any parser/OCR binaries required by supported formats.
- [ ] Pin/reconcile backend and frontend dependencies and lockfiles. Build from a clean checkout; confirm no local virtual environment or untracked asset is required.
- [ ] Maintain a usable local Compose setup and `.env.example`, with dependency readiness and persistent storage. Coordinate production Compose changes with platform owner; keep production database/cache ports unpublished.
- [ ] Build the React production bundle and test direct SPA routes, API base URL/proxy behavior, loading/empty/error states and browser authentication through the gateway. Never put the master API key or cloud credentials in a `VITE_*` variable or browser storage.
- [ ] Check CPU/memory/disk and request timeouts on the current single EC2 host. Provide application resource needs and external model/API dependencies to the platform owner.

### Tests and handoff

- [ ] Run all tests on the integrated PR commit, including the real PostgreSQL job, frontend build and Docker checks. Attach exact CI run and commit, with intentional skips explained.
- [ ] Cover upload, document list/detail/raw, duplicate files, malformed/empty/oversize input, authentication failures and successful retrieval/copilot citations. PR #3 already supplies much of this; review coverage before adding more.
- [ ] Verify rate limits through the real proxy, content/type/size validation, safe raw-document handling and absence of sensitive error output. Test concurrent clients where behavior matters.
- [ ] Document API examples, supported formats, operating modes, migration commands, environment contract, startup commands and known limitations.
- [ ] Submit application changes through GitHub. Let Jenkins deploy the accepted merge; avoid editing `/opt/mantra` manually or deploying from a teammate's laptop.

## 3. Product acceptance beyond the original DevOps contract

These checks establish whether advertised application features work. They are not all requirements of the original narrow DevOps plan. Agree release scope explicitly and record deferred items rather than calling them complete.

- [ ] Ingestion: supported PDF/text/etc. extraction, metadata/chunk boundaries, storage and retrieval, duplicates, invalid files, repeat upload and failure recovery all demonstrated with representative fixtures.
- [ ] Copilot: ask and streaming flows, answer grounding, document/page citations, no-result behavior, provider errors, disconnect handling and cache correctness demonstrated.
- [ ] Knowledge graph, equipment views, root-cause analysis, maintenance predictions/clusters, compliance status/gaps/audit evidence, incident/failure analysis, lessons and admin operations: each in-scope screen/API has an acceptance fixture and expected result. Endpoint existence is insufficient.
- [ ] Authorization for destructive/admin operations is defined and tested. Current gateway authentication is shared access, not per-user role authorization.
- [ ] Decide whether hashing embeddings and deterministic answers are an accepted demonstration mode or whether a real embedding/LLM provider is required. The observed deployment uses `hashing` / `deterministic`; label this honestly and test quality against agreed questions.
- [ ] If asynchronous ingestion is in scope, deliver worker/job status, retry/idempotency, failures and restart recovery tests. Otherwise record synchronous ingestion as an explicit limitation and defer worker delivery with an owner.
- [ ] Evaluate agreed representative documents/questions for answer accuracy, retrieval quality, latency and resource use. Passing infrastructure probes does not measure these outcomes.

## 4. Final joint acceptance

- [ ] Approved PR merged into canonical `main`; latest required checks passed on the integrated source.
- [ ] Jenkins build succeeds for that exact merged commit; ECR tag/digest and running backend image agree. Confirm frontend/platform files also came from that release.
- [ ] Migration head/schema match application expectations and existing documents remain usable.
- [ ] Platform owner runs platform verification; application owner runs agreed functional acceptance against deployed HTTPS using a disposable test dataset; remove only test data.
- [ ] Record task IDs, PR, merged SHA, CI run, Jenkins build, ECR digest, running image, migration version, functional results, reviewer and date using the acceptance record in the access guide.
- [ ] Both owners sign off against the agreed scope. Submitted, CI-passing, merged, deployed and functionally accepted are separate states.
