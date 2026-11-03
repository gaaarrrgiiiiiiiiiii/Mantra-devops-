#!/usr/bin/env bash
# Restore into a disposable database, never into mantra_db.
set -euo pipefail
cd /opt/mantra
backup_uri=${1:?Usage: verify-backup-restore.sh s3://bucket/backups/file.sql.gz}
backup_file=$(mktemp /tmp/mantra-restore-XXXXXXXX.sql.gz)
restore_db="mantra_restore_$(date -u +%s)"
cleanup() {
    docker compose --env-file .env exec -T db dropdb -U mantra_user --if-exists "$restore_db" || true
    rm -f "$backup_file"
}
trap cleanup EXIT
aws s3 cp "$backup_uri" "$backup_file"
gzip -t "$backup_file"
docker compose --env-file .env exec -T db createdb -U mantra_user "$restore_db"
gzip -dc "$backup_file" | docker compose --env-file .env exec -T db psql -v ON_ERROR_STOP=1 -U mantra_user -d "$restore_db" >/dev/null
docker compose --env-file .env exec -T db psql -U mantra_user -d "$restore_db" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
printf 'Backup restore verified in disposable database %s\n' "$restore_db"
