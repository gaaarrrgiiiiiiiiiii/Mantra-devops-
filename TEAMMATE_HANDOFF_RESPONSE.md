# Mantra platform handoff

The earlier handoff contained published production passwords and historical verification claims. Those values must not be reused. Current runtime credentials belong in the protected host configuration and must be retrieved privately.

Use [README.md](README.md) for architecture, access and deployment, and [PLATFORM_VERIFICATION.md](PLATFORM_VERIFICATION.md) for observed results and remaining work. The application owner should use the gateway URL and its user credentials; the master backend API key stays on the server.

The platform owner supplies scoped IAM access, individual SSH public-key authorization, the document bucket, runtime infrastructure, deployment and monitoring. The application owner supplies migrations, broader document/copilot/security tests and background ingestion. Platform deployment must not claim those application deliverables are complete merely because the service health checks pass.
