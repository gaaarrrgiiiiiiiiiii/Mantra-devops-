#!/usr/bin/env bash
set -euo pipefail
cd /opt/mantra
bucket=${1:?Supply the document/backup bucket name}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 0700 /var/backups/mantra
backup_file="/var/backups/mantra/pre-platform-${stamp}.sql.gz"
umask 077
docker compose exec -T db pg_dump -U mantra_user mantra_db | gzip > "$backup_file"
gzip -t "$backup_file"
restore_db="mantra_preflight_$(date -u +%s)"
cleanup() { docker compose exec -T db dropdb -U mantra_user --if-exists "$restore_db"; }
trap cleanup EXIT
docker compose exec -T db createdb -U mantra_user "$restore_db"
gzip -dc "$backup_file" | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U mantra_user -d "$restore_db" >/dev/null
aws s3 cp "$backup_file" "s3://${bucket}/backups/pre-platform-${stamp}.sql.gz" --sse AES256 --only-show-errors
aws s3api head-object --bucket "$bucket" --key "backups/pre-platform-${stamp}.sql.gz" --query '{Bytes:ContentLength,Encryption:ServerSideEncryption}'
echo "Verified pre-deployment backup: s3://${bucket}/backups/pre-platform-${stamp}.sql.gz"
