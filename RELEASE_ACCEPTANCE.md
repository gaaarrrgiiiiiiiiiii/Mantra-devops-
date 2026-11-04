# Mantra production release acceptance

Verified 4 November 2026, Asia/Kolkata. Scope: the current single-EC2 demonstration deployment.

## Accepted source and delivery

- PR #4 merged into protected main as `c4c3dcf492ede56ae9d7103546a9d98e39ba22b5` after Bazzin07's approval. The teammate now has write access; required reviews/checks and administrator enforcement remain enabled.
- All four merged-main checks passed in [Actions run 41782595814](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/actions/runs/41782595814).
- Jenkins **Mantra #6 SUCCESS** built, tested, scanned, pushed and deployed the merged commit.
- Running backend: `657157860151.dkr.ecr.us-east-1.amazonaws.com/mantra-backend:c4c3dcf492ede56ae9d7103546a9d98e39ba22b5`.
- Running/ECR registry digest matches: `sha256:91f3545f725d85d7ccc47fa9312b777f3ddb7bdfa9da283c023cfc31f084af32`.
- Live Alembic revision is `0002_native_retrieval`; native vectors/search text, GIN/HNSW indexes and migration-owned schema startup are present. `auto_create_schema` is false.

## Live verification

- All eight services are running. HTTPS certificate validation, readiness, gateway authentication, anonymous rejection, SPA routes, authenticated Swagger/OpenAPI/ReDoc, private ports and secret permissions passed.
- Live HTTPS fixtures passed S3-backed ingestion/raw retrieval/persistence/deduplication; native PostgreSQL copilot citations, cache and streaming; graph/equipment/maintenance flows; compliance evidence, incident analysis and admin counts.
- Both uniquely identified test documents and their current S3 objects were removed. Pre-existing documents were preserved, and a subsequent query did not return stale test citations. Audit history and S3 version history were not erased.
- Prometheus targets, provisioned Grafana, private Jenkins and CloudWatch collection passed. Previously confirmed email alert delivery was not unnecessarily repeated.
- A pre-migration backup was uploaded at `backups/mantra_db_20261104T061211Z.sql.gz`.
- A fresh post-migration backup at `backups/mantra_db_20261104T061858Z.sql.gz` was downloaded and restored successfully into a disposable database. Production data was preserved.
- The deployed image passed 68 tests against disposable PostgreSQL. The corrected runtime harness passed the same 68 tests while leaving the Docker volume inventory unchanged.

## Deployment repairs

The deployed host's Caddyfile and gateway-mounted file initially had different checksums because atomic host-file replacement left the old bind mount active. The reviewed configuration was validated and activated by recreating only the gateway. Live HTTPS acceptance then passed, and mounted/host checksums match.

[PR #5](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/5) automates this repair for future releases: detect stale/changed configuration, validate before activation, recreate only when needed, and remain idempotent on a second unchanged run. A focused Docker/Ansible regression reproduced the original problem and verified the repair. It also removes disposable PostgreSQL anonymous volumes during runtime-test cleanup; a before/after volume comparison verified no leak.

The operational gateway repair is complete. Merging the automation follow-up still requires independent review and passing checks under the existing repository rules.

## Security and operational limits

The archived Jenkins scan has **0 fixable HIGH/CRITICAL findings**, **1 vendor-unpatched CRITICAL** and **82 vendor-unpatched HIGH** findings. This satisfies the configured `--ignore-unfixed` gate; it does not mean zero vulnerabilities.

The critical finding is `CVE-2026-6653` in Debian's `libxml2`. Debian lists the installed stable/trixie package as affected, with no stable security update, and classifies the XML-triggered denial-of-service issue as minor/no-DSA. The fixed version is available in newer development distributions; the running image has not been switched to an unreviewed distribution or had the finding hidden. Track the [Debian advisory](https://security-tracker.debian.org/tracker/CVE-2026-6653) and refresh the pinned image/dependencies when a suitable update is available.

Disk cache cleanup retained the live and previous rollback image. Older local commit-image caches were removed only after confirming their artifacts remain in ECR. Database volumes and production containers were preserved. Disk capacity remains an ongoing operational concern for repeated large image builds.

Hashing embeddings/deterministic answers remain the existing demonstration baseline, not evidence of production model quality. Real-provider evaluation, meaningful semantic clustering, per-user RBAC, asynchronous ingestion, advanced format fidelity and future EKS/RDS/autoscaling phases remain separately scoped. Teammate-specific SSM sign-in still requires confirmation from that person's computer; it does not block this accepted deployment.

Non-secret raw evidence is stored in the operator's ignored `.local/verification/` directory and in `/var/log/mantra-release-evidence.json`, `/var/log/mantra-functional-acceptance.json`, `/var/log/mantra-platform-verification.json` and Jenkins archived reports on EC2. No password or access key belongs in this record.
