#!/usr/bin/env bash
# Usage: bash scripts/run-ansible-wsl.sh /mnt/c/.../.ssh/key.pem /mnt/c/.../.ssh/known_hosts playbook.yml [args...]
set -euo pipefail
ssh_key=${1:?Supply the existing SSH key path}
known_hosts=${2:?Supply the trusted known_hosts path}
shift 2
eval "$(ssh-agent -s)" >/dev/null
trap 'ssh-agent -k >/dev/null' EXIT
ssh-add - < "$ssh_key" >/dev/null 2>&1
export ANSIBLE_HOST_KEY_CHECKING=True
export ANSIBLE_SSH_ARGS='-o ControlMaster=no -o ControlPersist=no -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=2'
ansible-playbook -i ansible/inventory/hosts.ini --ssh-common-args="-o UserKnownHostsFile=$known_hosts" "$@"
