# Mantra platform handoff

The earlier handoff contained published production passwords and historical verification claims. Those values must not be reused. Current runtime credentials belong in the protected host configuration and must be retrieved privately.

Use [README.md](README.md) for architecture, access and deployment, and [PLATFORM_VERIFICATION.md](PLATFORM_VERIFICATION.md) for observed results and remaining work. The application owner should use the gateway URL and its user credentials; the master backend API key stays on the server.

The platform owner supplies scoped IAM/Session Manager access as the non-admin `mantra-app` account, the document bucket, runtime infrastructure, deployment and monitoring. The application owner supplies migrations, application behavior and acceptance tests; any background ingestion work must have an agreed scope. Platform deployment must not claim those application deliverables are complete merely because service health checks pass.

Follow [APPLICATION_ENGINEER_CHECKLIST.md](APPLICATION_ENGINEER_CHECKLIST.md) for the complete task list and [TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md](TEAM_ACCESS_AND_REMOTE_ACCEPTANCE.md) for own-computer sign-in and joint completion checks. PR #3 already contains application work with passing CI, but remains open. The live native retrieval schema still needs correction and acceptance. Do not share the platform owner's administrator SSH key.
