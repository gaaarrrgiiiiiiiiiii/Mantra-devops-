# Mantra frontend

## Verify the production build

Use Node.js 24 LTS (also used by Docker and GitHub Actions):

```sh
cd frontend
npm ci
npm run build
```

The build type-checks TypeScript and writes static assets to `dist/`.
A bundle-size warning does not fail the build. GitHub Actions and Jenkins
now run this command before the Docker build/deployment stages. Jenkins agents
must have Node.js 24 and npm installed.

## Serve on port 80 with Nginx

From the repository root, copy `.env.example` to `.env` and set `IKI_API_KEY`
to a unique random hexadecimal value (generate one with `openssl rand -hex 32`).
Then run:

```sh
docker compose up -d --build
```

Open `http://localhost/` (or the EC2 address on port 80). The frontend image
builds with Node.js, then serves `dist/` with Nginx. Nginx forwards `/api/` to
`backend:8000` and adds `X-API-Key` on the server. No API key is embedded in
browser JavaScript. Leave `VITE_API_URL` unset for this same-origin setup.
Streaming responses have proxy buffering disabled. SPA routes fall back to
`index.html`.

The existing Compose backend uses PostgreSQL, Redis, and S3. The deployed
EC2 instance needs access to the configured S3 bucket through its IAM role;
port 80 must be reachable and available on the host. This command also starts
the existing Prometheus and Grafana services.

The gateway provides API access to everyone who can reach port 80, including
administration routes, using the shared backend key. It is suitable for the
existing shared-access demo model. Restrict network access for private data;
per-user authentication/authorization and HTTPS remain deployment work.

## API review/demo

Backend Swagger UI is `/docs` on port 8000. Click **Authorize** and enter
`IKI_API_KEY`, upload a document using `POST /api/documents/upload`, then ask
`POST /api/copilot/ask` with:

```json
{"question": "What caused the P-205B bearing failure?", "limit": 4}
```

`/api/copilot/query` is not a route in this repository. Swagger groups routes
by feature, describes their behavior, exposes request/response schemas, and
supports API-key authorization. `/api/copilot/stream` documents its SSE format.

`/health` is a dependency-independent liveness check. Document counts remain
available through `/api/admin/overview`; `/health` no longer queries/counts
documents. `/ready` checks the repository and configured Redis connection,
returns 503 for a failed check, and reports Redis as `disabled` when no URL
is configured. Each dependency check has a two-second timeout.

## Backend tests

From the repository root, use Python 3.11:

```sh
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

Tests create a temporary SQLite database and local storage for each case,
use deterministic model providers, and test mocked database/cache failures.
They do not need production credentials, PostgreSQL, Redis, S3, or an LLM key.
Passing every test means a 100% pass rate, not 100% code coverage.

The PostgreSQL regression test is opt-in locally: set `MANTRA_TEST_POSTGRES_URL`
to a pgvector PostgreSQL connection with CREATE DATABASE and extension rights.
It creates and drops a randomly named database, tests startup/upload/query/cache,
and leaves existing tables untouched. GitHub Actions provisions a disposable
PostgreSQL service and runs this test automatically. Without that URL, this one
test is skipped. Jenkins agents may set the same variable to enable it.
