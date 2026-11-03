# Mantra platform completion and verification

Verification date: **4 November 2026, Asia/Kolkata**.

Acceptance covers the two-engineer DevOps plan and the single-EC2 hardening tasks P1–P6. The deployed host is `i-0d04109a558f3d149`, Elastic IP `32.193.54.28`. EKS, RDS and autoscaling remain future architecture phases.

## Platform checklist

| Deliverable | Result | Evidence |
|---|---|---|
| VPC, subnet, internet routing, EC2 and permanent IP | Verified | Terraform refresh completed; subsequent plan reported **no changes**. EC2 was updated in place. |
| Encrypted remote state and locking | Verified | S3 state object reports AES256 encryption and a version ID. Terraform acquired/released the DynamoDB lock during plan/apply. |
| Private document bucket | Verified | Terraform manages encryption, versioning and public-access blocks. The running backend performed a real S3 put/get/delete using its instance role. |
| Scoped application engineer IAM access | Verified | Existing credential is active. IAM simulation allowed S3 Get/Put/Delete on the project bucket and denied EC2 termination and IAM user creation. |
| Individual SSH keys | Verified | Both `mantra-eng1` and `mantra-eng2` authenticated successfully. Private keys are in the operator's `.ssh` directory, outside this repository. |
| Network restrictions | Verified | SSH is restricted to the operator CIDR. Only gateway ports 80/443 are public; database/cache have no host ports; monitoring binds to loopback. |
| Instance-profile security | Verified | IMDSv2 is required with a container-compatible hop limit. Backend STS identity is the EC2 role. Jenkins ECR push permissions target the project repository. |
| Production container delivery | Verified | Eight-service isolated stack passed startup, SPA routing, authentication, pgvector, storage dependency failures and recovery checks. Backend runs as `appuser`. |
| Ansible deployment | Verified | Production deployment finished with zero failed tasks, preserved `mantra_pgdata`, pulled an exact ECR digest and verified actual database/Redis readiness. |
| Runtime credentials | Verified | Published API/database/Grafana credentials were rotated. Production `.env` is mode 0600. The gateway authenticates browser users and adds the backend key server-side. |
| HTTPS | Verified | Workstation and host requests passed normal certificate validation at `https://32.193.54.28/ready`. Let's Encrypt certificate expires 10 November 2026 at 16:29:42 IST; Caddy has automatic renewal configured and persistent certificate storage. |
| Frontend/gateway integration — P1 | Verified | Authenticated frontend and `/api/documents` work. Anonymous API access is rejected. Default SNI handles clients connecting by IP. |
| TLS entry point — P2 | Verified using the Elastic IP | A custom domain is optional and has not been configured. No private CA or certificate-verification bypass is required. |
| Prometheus/Grafana | Verified | Both scrape targets are UP; the overview dashboard is provisioned; login works with the rotated Grafana password. Existing Grafana content was preserved. |
| Alert routing — P3 | Verified end to end | Alertmanager reported one successful SNS notification and zero failures. The recipient confirmed both the subscription and receipt of the test email. |
| Alert rule correctness | Verified | `promtool test rules` passed downtime timing, a 10% error rate at low traffic, and a normal 1% error rate. The metric label is `status`. |
| CloudWatch collection | Verified | Agent is active; AWS shows host and Docker log streams with event timestamps. Log groups have 14-day retention. |
| CI security gates — P4 | Verified | Bandit passed. Jenkins snapshot build **#1 SUCCESS** and main build **#2 SUCCESS** ran build, five runtime tests and Trivy. The released image has **0 fixable high/critical findings, 0 critical findings, and 45 vendor-unpatched high OS findings** retained in the full report. |
| Jenkins on the application EC2 host | Verified | Native systemd service is active and bound to loopback. Authentication, required plugins, deployment credential, pinned host key and Jenkinsfile validation passed. |
| Main-branch delivery | Verified — Jenkins build #2 SUCCESS | Published commit `a48f9e94bc4b698979d9c1c5b863dea4c6b8dd17` was built, tested, scanned, pushed to ECR and deployed through the dedicated SSH credential. Ansible reported **30 ok, 0 failed**, and the optional migration step was correctly skipped. The live image reference matches that commit. SCM polling is enabled every five minutes. |
| GitHub Actions | Verified — SUCCESS | [Run 41713462946](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/actions/runs/41713462946) passed for the released source. |
| Backups and recovery — P5 | Verified | Daily backup cron is installed for 07:30 IST. A production pg_dump was uploaded to S3, downloaded and restored into a disposable database successfully. The backup also passed with a clean cron-style environment, and its CloudWatch log stream received events. Production data was preserved. |
| Host and network hardening — P6 | Verified | Direct public API, Grafana and Prometheus ingress was removed; database and Redis host bindings were removed. SSH host checking is enabled. |

## Evidence and repeatable checks

The host's successful check results are saved at `/var/log/mantra-platform-verification.json`. Runtime configuration is `/opt/mantra/.env`; current web/Grafana access details are `/root/mantra-access.json`. The Jenkins admin password is `/var/lib/jenkins/secrets/mantra-admin-password`. Retrieve credentials privately over SSH; do not place them in Git or chat.

Post-release checks passed against the image delivered by Jenkins. Workstation checks returned HTTPS readiness **200**, anonymous API access **401**, and public Grafana access **403**. Non-secret raw evidence is saved locally under `.local/verification/`, including live acceptance, post-release checks, the Jenkins build log and full Trivy JSON.

Useful commands from a Linux checkout or the EC2 verification directory:

```bash
python -m pytest tests -q
terraform fmt -check -recursive terraform
terraform -chdir=terraform validate
terraform -chdir=terraform plan
docker compose --env-file .env.example config --quiet
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml --syntax-check -e mantra_backend_image=ECR_COMMIT_TAG_OR_DIGEST
```

`scripts/validate-containers.sh` exercises a disposable stack. `scripts/verify-live.py --exercise-recovery --test-alert` checks the real deployment and intentionally sends a test alert. `prometheus/alert.rules.test.yml` verifies alert timing and thresholds. Jenkins archives `trivy-report.json` for each scan.

The runtime's unused pip installation was removed because its vendored inventory/code contained an older setuptools copy. The active setuptools and wheel installations were upgraded. Vendor-unpatched OS findings remain visible in the full scan report; the deployment must not be described as having zero vulnerabilities.

## Application engineer handoff

- [x] Frontend container, gateway integration, truthful readiness and server-side API-key delivery are now supplied.
- [ ] Supply and package Alembic migrations. Ansible detects `/app/alembic.ini` and runs `alembic upgrade head` when available; this path awaits the application's migration package. Disable automatic schema creation when adopting migrations.
- [ ] Expand document ingestion, retrieval, copilot/citation, authentication and rate-limit tests. The current five tests cover health and dependency readiness.
- [ ] Pin/reconcile backend dependencies for reproducible application builds.
- [ ] Add asynchronous ingestion workers and document job status.
- [ ] Arrange secure delivery of the application engineer's private SSH key and provide any additional operator CIDR needed for SSH access.

HTTPS for the Elastic IP uses Let's Encrypt's short-lived profile. References: [Let's Encrypt IP certificates](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability), [Caddy TLS configuration](https://caddyserver.com/docs/caddyfile/directives/tls), [Jenkins Linux installation](https://www.jenkins.io/doc/book/installing/linux/).
