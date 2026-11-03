#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
image=${1:?Usage: scripts/deploy-ec2.sh ECR_IMAGE_REFERENCE [ansible arguments]}
shift
exec ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/deploy.yml -e "mantra_backend_image=$image" "$@"
