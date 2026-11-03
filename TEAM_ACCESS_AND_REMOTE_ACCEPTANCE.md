# Team access and remote completion checks

Reviewed 4 November 2026, Asia/Kolkata. Platform owner: Gargi. Application owner: Ayush / Bazzin07.

Each engineer keeps a separate clone, dependencies and private `.env` on their own computer. GitHub shares committed/pushed files; it does not expose uncommitted files, ignored configuration or an entire teammate computer. IAM controls AWS API access, Linux permissions control files on EC2, and GitHub permissions control repository access. These are separate permission systems.

## Access now provisioned

| Resource | Application engineer | Platform engineer |
|---|---|---|
| Local computers | Own local files and credentials | Own local files and credentials |
| GitHub | Fork/feature branch and PR workflow; collaborator rights depend on repository settings | Review/integrate platform and application changes; administer only with assigned GitHub role |
| EC2 session | Existing IAM user `mantra-engineer1-app-owner`; Session Manager to this instance using the approved document | Existing operator SSH and administration |
| EC2 Linux account | `mantra-app`; `/home/mantra-app/work`, home/work mode 0700 | `ubuntu` with sudo; can inspect server files as administrator |
| Production secrets and deployment | No production `.env`, sudo, Docker socket or Jenkins administration | Protected runtime configuration and CI deployment |
| AWS project data/logs | Existing project-bucket object permissions and log-read policy retained | Infrastructure management through platform identity/role |

The application IAM policy already existed for project S3/log access, but EC2 session access was missing. Terraform now attaches SSM agent permissions to the EC2 role, creates `mantra-application-shell`, a 14-day session log group, and a user policy scoped to this instance and document. Sessions run as `mantra-app`, with 20-minute idle and 60-minute maximum limits. The default administrator session document is explicitly denied. No `SendCommand`, EC2 termination or IAM tagging permissions were granted.

The Ansible access playbook created the non-admin Linux account, removed the generated `mantra-eng1` key from shared `ubuntu` access, and blocks that user's access to instance metadata credentials. Sharing the old `ubuntu` key would defeat this separation; do not use it for the application role. No new access keys, console password or GitHub invitation were generated.

Existing S3 permissions include object deletion in the project bucket. This is consequential data access, not read-only access: use a test prefix, and review a narrower prefix policy if production document management is unnecessary. GitHub collaborator access normally exposes the repository, not individual private folders; use separate repositories if file-read isolation is required. CODEOWNERS/reviews govern changes, not secret file visibility.

### Verified versus pending

- EC2 `i-0d04109a558f3d149`, `us-east-1`, reports **Online** in Systems Manager; approved document is **Active**.
- IAM simulation allows the actual target and custom document, explicitly denies the default shell document, and denies remote command, termination and IAM tagging actions.
- Linux account probes passed: production environment unreadable, production Compose unwritable, Docker socket inaccessible, sudo unavailable and instance metadata token request blocked.
- Terraform refresh/plan reported **no changes** after provisioning. Live platform verification still passes, including backend role-based S3 put/get/delete, readiness, authentication, monitoring and private Jenkins.
- **Pending:** teammate's actual IAM sign-in and interactive session from their own computer, plus confirmation that that session's CloudWatch transcript is delivered. Policy simulation and local account probes do not prove that full user journey.

### Teammate: connect from your own computer

Install AWS CLI and the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html). Use your existing privately issued application IAM credentials or organization-approved credential flow. If no credentials were delivered, the platform owner must arrange private issuance/reset; do not request keys in a GitHub issue or chat. `aws configure --profile mantra-app` can store issued keys locally when that is the agreed credential method. This policy does not create an AWS console login.

```bash
aws sts get-caller-identity --profile mantra-app
aws ssm start-session --target i-0d04109a558f3d149 --document-name mantra-application-shell --region us-east-1 --profile mantra-app
```

Expected identity ARN ends in `user/mantra-engineer1-app-owner`. Inside the session:

```bash
whoami                            # mantra-app
pwd                               # /home/mantra-app/work
id                                # no sudo/docker/lxd membership
test ! -r /opt/mantra/.env && echo 'production secrets protected'
sudo -n true                      # must fail
exit
```

Send the platform owner only the non-secret identity ARN, session ID and test outcomes. They can verify session metadata in Systems Manager and the transcript under `/mantra/application-sessions`. SSM uses the agent's outbound connection and does not require opening a new inbound SSH port for the teammate. See [AWS session access controls](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-examples.html).

## How the platform owner verifies work remotely

Yes: combine source review, CI/CD evidence and live feature tests from your own computer. Commit counts, a push or a green health endpoint cannot establish task completion.

| Stage | What to inspect remotely | What it establishes |
|---|---|---|
| Submitted | Canonical repository PR files, author, head SHA, reviews and discussion | Shared implementation exists and is reviewable |
| Validated | Actions/check runs for the latest integrated source; logs, executed tests and skips | Those automated checks passed for that source |
| Integrated | PR merged state, merge commit and canonical `main` ancestry | Accepted changes reached the watched branch |
| Delivered | Jenkins build revision, stage logs, tests/scans, ECR commit tag and digest | CI built and deployed an identifiable artifact |
| Running | EC2 image reference/digest, service health, migration/schema and frontend revision | Intended release is actually on the host |
| Accepted | Deployed feature tests using representative fixtures, citations and persistence checks | Agreed behavior works in the deployed environment |

The GitHub commit graph does not necessarily retain every historical push event. PR timelines, CI history, and authorized audit logs/webhook records provide additional history where retained. Unpushed laptop work remains invisible. Request a PR or reproducible evidence rather than access to a teammate's private computer.

### Current source and release evidence

- Canonical deployment source: [gaaarrrgiiiiiiiiiii/Mantra-devops-](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-). Jenkins polls its `main` every five minutes. Pushing only to [Bazzin07/Mantra](https://github.com/Bazzin07/Mantra) does not deploy this host.
- Application [PR #3](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/pull/3) is **open**, with successful [run 41189460509](https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-/actions/runs/41189460509). It needs integration against the current platform and deployed acceptance. Do not call it incomplete code solely because it is not merged, or complete production work solely because CI passed.
- At inspection, canonical `main` was **unprotected**. Agree and configure branch rules requiring reviews and passing integrated checks, and blocking force pushes/deletion. Add CODEOWNERS for Terraform, Ansible, Jenkinsfile, workflows, gateway and production Compose; platform owner reviews those changes. These GitHub governance controls are still pending, not enforced by the new IAM policy.
- Live runtime inspection found missing native retrieval columns. Use [the application checklist](APPLICATION_ENGINEER_CHECKLIST.md) to close that gap; a healthy service is not proof of working PostgreSQL retrieval.

### Operator repeatable checks

From your own clone, inspect shared source:

```bash
git fetch origin --prune
git log origin/main --oneline -15
git log origin/main --author=Bazzin07 --oneline
git diff origin/main...origin/ayush/application-devops --stat
```

Author-name filtering is only a convenience, not proof of identity or completeness. Use PR review history and actual diffs. If using a fork, fetch the relevant remote/PR branch first.

Use your existing operator SSH key from your computer:

```bash
ssh -i ~/.ssh/mantra-key.pem ubuntu@32.193.54.28
cd /tmp/mantra-platform-verify
sudo python3 scripts/jenkins-admin.py status
sudo python3 scripts/verify-live.py
sudo python3 scripts/audit-application-runtime.py --require-retrieval-schema
cd /opt/mantra
sudo docker compose --env-file .env ps
sudo docker compose --env-file .env images
sudo docker inspect --format '{{.Config.Image}}' "$(sudo docker compose --env-file .env ps -q backend)"
```

For the authoritative registry digest, inspect the image separately:

```bash
container_id=$(sudo docker compose --env-file .env ps -q backend)
image_id=$(sudo docker inspect --format '{{.Image}}' "$container_id")
sudo docker image inspect --format '{{json .RepoDigests}}' "$image_id"
```

Do not dump the whole container inspect or expanded Compose configuration into chat: environment fields may contain secrets. The audit script reads only selected runtime modes and schema metadata; `--require-retrieval-schema` intentionally fails until the missing columns are supplied. It checks prerequisites, not retrieval quality. The temporary verification checkout must contain the current scripts; stage it with the existing packaging workflow when updating.

Plain `verify-live.py` checks infrastructure and performs a small disposable S3 object round trip. `--exercise-recovery --test-alert` additionally performs restore testing and sends an alert; use those only for a planned recovery/alert exercise. Alerts were already confirmed delivered to `gargith24@gmail.com` by the user.

From a local Terraform checkout with platform credentials, `terraform -chdir=terraform plan -detailed-exitcode` returns 0 for no changes, 2 for differences, 1 for an error. Review differences before any apply. Check CloudWatch current logs, Prometheus targets, backup freshness and TLS expiry alongside deployment evidence. Application feature tests need authenticated HTTPS access, a disposable dataset and explicit expected outcomes.

## Completion record: one per accepted release

```text
Scope/task IDs and deferred items:
Application owner / platform reviewer:
PR URL and approved integrated commit:
Merged main SHA:
Actions run URL, results and intentional skips:
Jenkins job/build URL and built SHA:
ECR image tag + sha256 digest:
Running backend image/digest and frontend release source:
Migration version + schema verification:
Platform checks + backup/monitoring evidence:
Functional fixtures, expected results and observed results:
Own-device access confirmation/session ID:
Acceptance date and both owners' sign-off:
```

Keep secret values out of this record. Record a failure or deferred item honestly; do not mark the whole application complete while any release-critical migration or feature check is pending.
