# Platform engineer implementation and acceptance record

Date: 4 November 2026, Asia/Kolkata. This record separates implemented platform controls from application-owner and joint acceptance dependencies.

Update: the platform owner has implemented the missing migration package and broader acceptance tests on PR #4. See [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) for current candidate results. Historical missing-schema observations below describe the existing production baseline; review, merge and deployed acceptance are still pending.

## Implemented platform controls

- Restricted application SSM access is provisioned; managed node is Online, approved document Active, dedicated user `mantra-app` has no sudo/Docker access, and host role credentials/production secrets are blocked. The retired application key is absent from `ubuntu`.
- `.github/CODEOWNERS` assigns infrastructure, pipeline, gateway, shared container and configuration changes to the platform owner. Bazzin07 has read access to the canonical repository and continues through fork PRs; no GitHub invitation or new credential was issued.
- `scripts/github-platform.py protect` applies required up-to-date GitHub Actions checks (`test`, `docker-build`, `frontend-build`, `schema-contract`), one approving review, code-owner review, stale-review dismissal and resolved conversations. Administrators are included; force pushes and branch deletion are disabled. `audit` retrieves actual settings and source/check evidence without printing credentials. Verify the saved audit rather than assuming file presence enforces a rule.
- CI builds the frontend, runs against a disposable pgvector PostgreSQL service, retains security scans and checks the migration delivery contract. Jenkins tests its exact runtime image against an isolated disposable database through `scripts/test-runtime-image.sh`; no production database is used by this test harness.
- Database initialization/model changes cannot pass the required `schema-contract` check without a versioned Alembic package and Dockerfile packaging. This is a packaging gate; application tests must also establish fresh/existing-data upgrade correctness.
- Ansible supports `-e mantra_require_migrations=true` for application promotion, and creates/uploads a backup before running packaged migrations. The existing platform-only deployment can still operate while the application's migration package is pending.
- `scripts/release-evidence.py --expected-commit FULL_SHA` checks the running commit, ECR digest presence, a nonempty backup less than 36 hours old and a trusted HTTPS certificate valid for more than 24 hours. It reports schema/migration prerequisites separately. `--require-application` fails when those prerequisites are missing; functional product acceptance remains a separate requirement.

No human acceptance or teammate sign-in is fabricated by these scripts. The application promotion gate must not be bypassed merely because platform health checks pass.

## Observed production baseline

Before this control update, Jenkins main build **#4 SUCCESS** deployed `313270fcedb1fc860d17b03eb19b678cb8bdde0c` with registry digest `sha256:fca812d7f5b1f164eed6ab7073c3b41e624e36c0f7efe84dfe4d48c14b13e926`. GitHub test/docker-build checks passed for that commit. The new exact-image harness also passed all five existing runtime tests against it.

The daily backup `backups/mantra_db_20261104T020001Z.sql.gz` was uploaded successfully, nonempty (567,803 bytes) and about 2.6 hours old during verification. HTTPS certificate validation succeeded; expiry is 10 November 2026 at 10:59:42 UTC. The latest release evidence is written to `/var/log/mantra-release-evidence.json`; a newer successful deployment supersedes this baseline.

## Application PR review and integration disposition

[PR #3](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/3), reviewed head `4dce2fa1a21ff1348e4a03d17e11391a2aa4c349`, had successful earlier CI, but is now confirmed conflicting with current `main`. Nine conflict paths cover `.env.example`, workflow, Jenkinsfile, README, backend Dockerfile/main.py, Compose and frontend Dockerfile/.dockerignore.

An isolated `platform/application-acceptance` candidate integrates the teammate's submitted tests, API documentation/security schema and startup schema correction while preserving current Caddy/authentication, private ports, exact-image delivery, fail-closed production authentication and the existing database/Redis readiness checks. It is for review, not authorization to deploy unfinished application work. The original teammate PR is not silently overwritten.

Release blockers remain:

1. PR #3 provides startup ALTER TABLE operations, not a packaged/versioned migration history or populated-database backfill/upgrade tests. The live database still lacks native retrieval columns and has no Alembic revision.
2. Application owner must demonstrate agreed retrieval/citations and other release features on representative fixtures, including the limits of hashing embeddings/deterministic responses.
3. Teammate must sign in from their own computer using their privately issued IAM credentials; platform owner then confirms transcript delivery under `/mantra/application-sessions`. No session transcript existed at the baseline check.
4. Both engineers must sign the final acceptance record. If the platform owner authors a PR, another reviewer with repository write rights is needed for its required approval. The current read-only teammate role does not supply that review capability.

## Operator completion procedure

```bash
# Own computer, existing private GitHub authentication:
python scripts/github-platform.py audit --output .local/verification/github-controls.json

# EC2, platform operator:
cd /tmp/mantra-platform-verify
sudo python3 scripts/jenkins-admin.py status
sudo python3 scripts/verify-live.py
sudo python3 scripts/release-evidence.py --expected-commit FULL_MERGED_SHA

# Application promotion: only once migrations/tests/review are accepted:
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml \
  -e mantra_backend_image=ECR_FULL_COMMIT_OR_DIGEST -e mantra_require_migrations=true
sudo python3 scripts/release-evidence.py --expected-commit FULL_MERGED_SHA --require-application
```

Compare Actions, Jenkins built SHA, running reference/digest and schema evidence, then execute agreed application feature tests. Use the sign-off template in [TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md](TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md). Continue monitoring backup freshness, alert delivery, disk capacity and automatic certificate renewal; a one-time successful check is not ongoing monitoring.
