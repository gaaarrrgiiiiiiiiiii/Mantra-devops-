#!/usr/bin/env bash
# Test the exact release image against an isolated PostgreSQL/pgvector service.
set -euo pipefail
image=${1:?Supply the exact backend image reference}
test_id="mantra-ci-$(cat /proc/sys/kernel/random/uuid | cut -c1-12)"
db_name="${test_id}-db"
cleanup() {
    docker rm -f "$db_name" >/dev/null 2>&1 || true
    docker network rm "$test_id" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker network create "$test_id" >/dev/null
docker run -d --name "$db_name" --network "$test_id" --network-alias test-db \
    -e POSTGRES_USER=mantra_test -e POSTGRES_PASSWORD=ci-only-password \
    -e POSTGRES_DB=mantra_test pgvector/pgvector:pg16 >/dev/null
ready=false
for attempt in $(seq 1 60); do
    if docker exec "$db_name" pg_isready -U mantra_test -d mantra_test >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
if [ "$ready" != true ]; then
    echo 'Disposable PostgreSQL did not become ready' >&2
    exit 1
fi
docker run --rm --network "$test_id" -v "$PWD/tests:/tests:ro" \
    -e IKI_ENVIRONMENT=test -e IKI_REQUIRE_API_KEY=false \
    -e IKI_REPOSITORY_BACKEND=memory -e IKI_LOCAL_STORAGE_PATH=/tmp/test-storage \
    -e MANTRA_TEST_POSTGRES_URL=postgresql+asyncpg://mantra_test:ci-only-password@test-db:5432/mantra_test \
    "$image" python -m pytest /tests -v -p no:cacheprovider
