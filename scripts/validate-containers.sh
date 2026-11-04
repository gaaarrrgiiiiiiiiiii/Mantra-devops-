#!/usr/bin/env bash
# Run from an extracted source package, separate from /opt/mantra.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$PWD" = /opt/mantra ]; then
    echo 'Run validation from an isolated source directory.' >&2
    exit 1
fi
python3 - <<'PY'
from pathlib import Path
import secrets
import crypt
web_password = secrets.token_hex(24)
values = {
    'IKI_API_KEY': secrets.token_hex(32),
    'POSTGRES_PASSWORD': secrets.token_hex(24),
    'GRAFANA_ADMIN_PASSWORD': secrets.token_hex(24),
    'IKI_S3_BUCKET': 'mantra-platform-validation',
    'IKI_STORAGE_BACKEND': 'local',
    'MANTRA_BIND_ADDRESS': '127.0.0.1',
    'MANTRA_HTTP_PORT': '18080',
    'MANTRA_HTTPS_PORT': '18443',
    'MANTRA_PROMETHEUS_PORT': '19090',
    'MANTRA_GRAFANA_PORT': '13000',
    'MANTRA_ALERTMANAGER_PORT': '19093',
    'MANTRA_SITE_ADDRESS': ':80',
    'MANTRA_ACME_EMAIL': 'operator@example.com',
    'MANTRA_BACKEND_IMAGE': 'mantra-backend:platform-validation',
    'MANTRA_WEB_USER': 'mantra',
    'MANTRA_WEB_PASSWORD': web_password,
    'MANTRA_WEB_PASSWORD_HASH': crypt.crypt(web_password, crypt.mksalt(crypt.METHOD_BLOWFISH)),
}
path = Path('.env')
path.write_text(''.join(f"{key}='{value}'\n" for key, value in values.items()))
path.chmod(0o600)
PY
compose() { docker compose -p mantra-platform-verify --env-file .env "$@"; }
cleanup() { compose down --volumes --remove-orphans; }
trap cleanup EXIT
compose config --quiet
if [ "${MANTRA_VALIDATION_REUSE_IMAGES:-0}" = 1 ]; then
    # Only for rerunning checks against images already built from this checkout.
    docker image inspect mantra-backend:platform-validation mantra-platform-verify-frontend >/dev/null
else
    compose build backend frontend
fi
compose run --rm --no-deps -e IKI_ENVIRONMENT=test -e IKI_REQUIRE_API_KEY=false -e IKI_REPOSITORY_BACKEND=memory -e IKI_REDIS_URL= -e IKI_STORAGE_BACKEND=local -e IKI_LOCAL_STORAGE_PATH=/tmp/test-storage -v "$PWD/tests:/tests:ro" backend python -m pytest /tests -q -p no:cacheprovider
compose run --rm --no-deps --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
compose run --rm --no-deps --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
compose run --rm --no-deps --entrypoint caddy gateway validate --config /etc/caddy/Caddyfile
compose up -d --wait db redis
compose run --rm --no-deps backend alembic upgrade head
compose up -d --no-build
for attempt in {1..30}; do
    if curl --fail --silent http://127.0.0.1:18080/ready >/dev/null; then break; fi
    sleep 2
done
curl --fail --silent http://127.0.0.1:18080/ready
python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json
import base64
env = dict(line.split('=', 1) for line in Path('.env').read_text().splitlines())
env = {key: value.strip("'") for key, value in env.items()}
base = 'http://127.0.0.1:18080'
authorization = 'Basic ' + base64.b64encode((env['MANTRA_WEB_USER'] + ':' + env['MANTRA_WEB_PASSWORD']).encode()).decode()
for route in ['/', '/client-side-route', '/api/health']:
    assert urlopen(Request(base + route, headers={'Authorization': authorization})).status == 200, route
try:
    urlopen(base + '/api/documents')
    raise AssertionError('Unauthenticated API request succeeded')
except HTTPError as exc:
    assert exc.code == 401, exc.code
request = Request(base + '/api/documents', headers={'Authorization': authorization})
assert isinstance(json.load(urlopen(request)), list)
print('Gateway, SPA routing, authenticated API and unauthorized rejection passed')
# The gateway must replace client-supplied forwarding headers, so rotating
# spoofed X-Forwarded-For addresses cannot evade the configured per-client limit.
limited = False
for index in range(125):
    try:
        urlopen(Request(base + '/api/documents', headers={'Authorization': authorization, 'X-Forwarded-For': f'192.0.2.{index + 1}'}))
    except HTTPError as exc:
        assert exc.code == 429, exc.code
        assert exc.headers['Retry-After'] == '60'
        limited = True
        break
assert limited, 'Proxy-backed application rate limit was bypassed'
print('Rate limit enforced through the real gateway despite spoofed forwarding headers')
PY
compose exec -T db psql -v ON_ERROR_STOP=1 -U mantra_user -d mantra_db -Atc "SELECT extversion FROM pg_extension WHERE extname='vector';"
compose exec -T redis redis-cli ping
compose stop redis
test "$(curl --silent -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/ready)" = 503
compose start redis
compose stop db
test "$(curl --silent -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/ready)" = 503
compose start db
for attempt in {1..20}; do
    if curl --fail --silent http://127.0.0.1:18080/ready >/dev/null; then break; fi
    sleep 2
done
curl --fail --silent http://127.0.0.1:18080/ready
compose exec -T db pg_dump -U mantra_user mantra_db > platform-backup.sql
compose exec -T db createdb -U mantra_user mantra_restore_test
compose exec -T db psql -v ON_ERROR_STOP=1 -U mantra_user -d mantra_restore_test < platform-backup.sql >/dev/null
compose exec -T db dropdb -U mantra_user mantra_restore_test
for attempt in {1..20}; do
    targets=$(compose exec -T prometheus wget -qO- http://localhost:9090/api/v1/targets)
    if printf '%s' "$targets" | python3 -c 'import json,sys; data=json.load(sys.stdin); sys.exit(0 if len(data["data"]["activeTargets"]) == 2 and all(t["health"] == "up" for t in data["data"]["activeTargets"]) else 1)'; then break; fi
    sleep 2
done
printf '%s' "$targets" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert all(t["health"] == "up" for t in data["data"]["activeTargets"]); print("Prometheus scrape targets UP")'
compose ps --format json | python3 -c 'import json,sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; assert len(rows)==8; assert all(row["State"] == "running" for row in rows); assert all(not p.get("PublishedPort",0) or p.get("URL") == "127.0.0.1" for row in rows if row["Service"] != "gateway" for p in (row.get("Publishers") or [])); print("All eight services running; monitoring ports are loopback-only")'
echo 'Container validation, dependency failure probes and database restore passed.'
