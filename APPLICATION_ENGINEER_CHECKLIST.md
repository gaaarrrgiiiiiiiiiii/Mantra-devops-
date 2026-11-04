# Application delivery and acceptance checklist

Updated 4 November 2026. The platform owner has taken over the remaining implementation. Teammate contributions from PR #3 are preserved in [integration PR #4](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/4). Checkmarks below distinguish candidate implementation from deployed acceptance. Production remains on the previous platform release until review and promotion.

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

- [ ] All four required checks pass on the final integrated PR source: schema-contract, test, frontend-build and docker-build.
- [ ] Independent reviewer with repository write access reviews and approves the final PR. The implementation author cannot self-approve.
- [ ] Accepted source merges into protected canonical main.
- [ ] Jenkins builds/tests/scans that merged commit, publishes its immutable ECR image and deploys it with required migrations.
- [ ] Confirm pre-migration backup, live Alembic revision, existing-data integrity, gateway behavior and agreed functional acceptance on deployed HTTPS.
- [ ] Match main SHA, Jenkins build, ECR digest and running image; record final joint/reviewer acceptance.

## Access handoff

- [x] Application IAM/SSM policy and non-admin `mantra-app` Linux account are provisioned and platform-tested.
- [ ] Teammate accepts collaborator access if they will review or continue implementation; last API inspection reported read access.
- [ ] Teammate confirms own-device SSM login and CloudWatch session transcript if they need server access. The platform owner cannot impersonate this user journey.
- [ ] Each developer keeps their own clone, test configuration and private credentials. Never share the operator administrator SSH key or production environment file.

## Explicit release limits and separately scoped work

- Current Compose release uses hashing embeddings and deterministic answers. Tests verify grounded/cited demonstration behavior, not production model accuracy. Real model-provider credentials, model quality benchmarks and external-provider acceptance require separate configuration and review.
- Clustering/pattern analysis correctly reports unavailable with hashing embeddings. Meaningful semantic clustering needs a real embedding model and optional ML dependencies; it is not falsely counted as complete.
- Gateway authentication is shared access. Per-user authorization/RBAC is not implemented.
- Ingestion is synchronous with manual failure reprocessing. Background workers, automatic retry scheduling and job queues remain future work unless explicitly added to release scope.
- Fixtures cover supported modern document formats. Legacy binary XLS, scanned-PDF OCR and complex/adversarial format fidelity need further parser work/acceptance; basic image OCR is tested.
- EKS, RDS and autoscaling remain future platform phases. Do not include them in current single-EC2 completion claims.
