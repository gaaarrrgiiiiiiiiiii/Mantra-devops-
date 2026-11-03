"""Rotate exposed credentials on the existing host without printing secrets.

Run as root on EC2 after taking a verified backup, immediately before Ansible
deployment. Existing runtime configuration is saved in a root-only directory.
"""
import argparse
import crypt
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess


parser = argparse.ArgumentParser()
parser.add_argument("--image", required=True)
parser.add_argument("--site", default="32.193.54.28")
parser.add_argument("--email", required=True)
args = parser.parse_args()
if os.geteuid() != 0:
    raise SystemExit("Run with sudo on the EC2 host")
root = Path("/opt/mantra")
os.chdir(root)
compose = ["docker", "compose"]
config = json.loads(subprocess.check_output(compose + ["config", "--format", "json"]))
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
rollback = root / ".platform-rollback" / stamp
rollback.mkdir(parents=True, mode=0o700)
rollback.parent.chmod(0o700)
for name in ["docker-compose.yml", ".env", "prometheus", "grafana"]:
    source = root / name
    if source.is_dir():
        shutil.copytree(source, rollback / name)
    elif source.exists():
        shutil.copy2(source, rollback / name)
        (rollback / name).chmod(0o600)

db_password = secrets.token_hex(24)
api_key = secrets.token_hex(32)
grafana_password = secrets.token_urlsafe(32)
web_password = secrets.token_urlsafe(32)
backend_env = config["services"]["backend"]["environment"]
env = {
    "AWS_REGION": "us-east-1",
    "IKI_S3_BUCKET": backend_env.get("IKI_S3_BUCKET", "mantra-industrial-docs-657157860151"),
    "IKI_API_KEY": api_key,
    "POSTGRES_PASSWORD": db_password,
    "GRAFANA_ADMIN_USER": "admin",
    "GRAFANA_ADMIN_PASSWORD": grafana_password,
    "MANTRA_WEB_USER": "mantra",
    "MANTRA_WEB_PASSWORD_HASH": crypt.crypt(web_password, crypt.mksalt(crypt.METHOD_BLOWFISH)),
    "MANTRA_SITE_ADDRESS": args.site,
    "MANTRA_ACME_EMAIL": args.email,
    "MANTRA_TLS_SERVER_NAME": args.site,
    "MANTRA_GRAFANA_ROOT_URL": "http://localhost:3000/grafana/",
    "MANTRA_BACKEND_IMAGE": args.image,
}
# Keep password bytes out of process arguments and command output.
subprocess.run(
    compose + ["exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", "mantra_user", "-d", "mantra_db"],
    input=f"ALTER ROLE mantra_user PASSWORD '{db_password}';\n", text=True, check=True,
    stdout=subprocess.DEVNULL,
)
temporary = root / ".env.platform-new"
temporary.write_text("".join(f"{key}='{value}'\n" for key, value in env.items()))
temporary.chmod(0o600)
temporary.replace(root / ".env")
access = Path("/root/mantra-access.json")
access.write_text(json.dumps({
    "web_username": "mantra", "web_password": web_password,
    "grafana_username": "admin", "grafana_password": grafana_password,
    "rollback_directory": str(rollback),
}, indent=2))
access.chmod(0o600)
print("Production .env prepared with rotated credentials; access details are in /root/mantra-access.json")
