#!/usr/bin/env bash
set -euo pipefail
cd /opt/mantra
printf 'SSH_SOURCE=%s\n' "${SSH_CONNECTION%% *}"
df -h / /tmp
docker compose version
sudo docker compose ps --format '{{.Service}} {{.State}} {{.Health}}'
sudo docker compose exec -T db psql -U mantra_user -d mantra_db -Atc "SELECT 'postgres_ok'; SELECT extname FROM pg_extension;" </dev/null
sudo docker compose exec -T redis redis-cli ping </dev/null
curl --fail --silent http://localhost:8000/ready
printf '\n'
sudo stat -c 'env_permissions=%a owner=%U' .env
printf 'jenkins='; systemctl is-active jenkins || true
printf 'ansible='; command -v ansible-playbook || true
printf 'aws='; command -v aws || true
printf 'cron='; sudo crontab -l 2>/dev/null | grep -c mantra || true
printf 'authorized_key_count='; grep -c '^ssh-' ~/.ssh/authorized_keys || true
