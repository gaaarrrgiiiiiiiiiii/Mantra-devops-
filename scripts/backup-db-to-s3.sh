#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/mantra
cd "$APP_DIR"
set -a
# The deployment file is root-readable only; it supplies the bucket name.
source "$APP_DIR/.env"
set +a

backup_file=$(mktemp /tmp/mantra-db-XXXXXXXX.sql.gz)
trap 'rm -f "$backup_file"' EXIT
timestamp=$(date -u +%Y%m%dT%H%M%SZ)

docker compose --env-file .env exec -T db pg_dump -U mantra_user mantra_db | gzip > "$backup_file"
gzip -t "$backup_file"
aws s3 cp "$backup_file" "s3://${IKI_S3_BUCKET}/backups/mantra_db_${timestamp}.sql.gz" --sse AES256
