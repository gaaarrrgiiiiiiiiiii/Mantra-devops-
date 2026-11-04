# Application delivery and acceptance checklist

Updated 4 November 2026. The platform owner completed the remaining implementation. Teammate contributions from PR #3 were integrated through [PR #4](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/4), reviewed by Bazzin07, merged and deployed. See [RELEASE_ACCEPTANCE.md](RELEASE_ACCEPTANCE.md) for current production evidence and remaining scope limits.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) and [TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md](TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md).

## Implemented and tested candidate

- [x] Resolve application/platform conflicts while preserving Caddy TLS/authentication, private database/cache/monitoring ports, non-root runtime, protected credentials and exact-image Jenkins/Ansible delivery.
- [x] Package versioned Alembic migrations in the backend image: frozen legacy schema baseline, PostgreSQL vectors/search text, saved-vector backfills, GIN and HNSW indexes.
- [x] Test fresh PostgreSQL setup, both unversioned legacy schema variants, populated upgrades, repeated upgrade, document preservation and transaction rollback on incompatible vectors.
- [x] Make PostgreSQL schema migration-owned and reject startup without the matching migration revision; retain SQLite auto-creation for local development.
- [x] Verify 768-dimensional native PostgreSQL retrieval with fallback forbidden, native no-match behavior, exact/semantic cache and persistence after restart.
- [x] Fix zero-vector NaN retrieval scores, misleading external-model metadata in offline mode and regulation spelling differences that hid matching evidence.
- [x] Pin the Python 3.11/Linux runtime dependency graph in `backend/requirements.lock`; retain frontend npm lockfile and clean production image builds.
- [x] Package runtime data, Alembic files and OCR/system tools; exclude local secrets and generated artifacts from backend build context.
- [x] Test representative text, Markdown, CSV, email text, PDF, DOCX, XLSX, PPTX and image-OCR ingestion, raw retrieval and duplicate/error behavior.
- [x] Test manual ingestion failure recording/reprocessing and successful recovery.
- [x] Test graph/equipment views, maintenance RCA/health/predictions/investigation, compliance evidence/gaps, incident analysis, streaming citations and administration counts.
- [x] Cover authentication across feature families, production fail-closed behavior, request validation, dependency-aware readiness, liveness and metrics.
- [x] Bound application upload reads and gateway request bodies; expose a production rate limit and overwrite forwarded identity at the gateway.
- [x] Preserve operator-side S3 instance-role integration and the existing infrastructure health/security checks. The unchanged production storage path was verified separately by the platform audit.
- [x] Back up before migration, preserve protected previous configuration, and persist the new image only after successful migration.
- [x] Document migration/rollback commands, dependency lock, local setup, operating modes and current limitations.

The exact candidate image passed **68 tests**, including real PostgreSQL tests, before publication. Full-stack/security and latest-commit CI results are linked from PR #4 and the implementation record. These tests demonstrate representative behavior; they do not certify industrial decision quality or every possible input.

## Required before production completion

- [x] All four required checks pass on merged main: schema-contract, test, frontend-build and docker-build.
- [x] Independent writer Bazzin07 approved the source before merge.
- [x] Accepted source merged into protected main as `c4c3dcf`.
- [x] Jenkins #6 built/tested/scanned/published/deployed that exact commit and ran migrations.
- [x] Pre-migration backup, live revision, data preservation, gateway behavior and representative HTTPS acceptance passed; post-migration backup restoration passed.
- [x] Main SHA, Jenkins build, ECR digest and running image match; automated release evidence and reviewer acceptance are recorded.
- [ ] Independently review/merge the focused future-deployment automation repair in PR #5. The live gateway configuration has already been repaired and verified.

## Access handoff

- [x] Application IAM/SSM policy and non-admin `mantra-app` Linux account are provisioned and platform-tested.
- [x] Teammate accepted collaborator access; GitHub reports write permission and their PR #4 approval is recorded.
- [ ] Teammate confirms own-device SSM login and CloudWatch session transcript if they need server access. The platform owner cannot impersonate this user journey.
- [ ] Each developer keeps their own clone, test configuration and private credentials. Never share the operator administrator SSH key or production environment file.

## Explicit release limits and separately scoped work

- Current Compose release uses hashing embeddings and deterministic answers. Tests verify grounded/cited demonstration behavior, not production model accuracy. Real model-provider credentials, model quality benchmarks and external-provider acceptance require separate configuration and review.
- Clustering/pattern analysis correctly reports unavailable with hashing embeddings. Meaningful semantic clustering needs a real embedding model and optional ML dependencies; it is not falsely counted as complete.
- Gateway authentication is shared access. Per-user authorization/RBAC is not implemented.
- Ingestion is synchronous with manual failure reprocessing. Background workers, automatic retry scheduling and job queues remain future work unless explicitly added to release scope.
- Fixtures cover supported modern document formats. Legacy binary XLS, scanned-PDF OCR and complex/adversarial format fidelity need further parser work/acceptance; basic image OCR is tested.
- EKS, RDS and autoscaling remain future platform phases. Do not include them in current single-EC2 completion claims.
