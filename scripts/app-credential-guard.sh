#!/usr/bin/env bash
set -euo pipefail
# The application shell must use its own IAM identity, not the host's CI role.
app_uid=$(id -u mantra-app)
if ! /usr/sbin/iptables -C OUTPUT -d 169.254.169.254/32 -m owner --uid-owner "$app_uid" -j REJECT 2>/dev/null; then
    /usr/sbin/iptables -I OUTPUT 1 -d 169.254.169.254/32 -m owner --uid-owner "$app_uid" -j REJECT
fi
