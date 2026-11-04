"""Collect non-secret deployed release evidence; run as the platform operator on EC2."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import socket
import ssl
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--expected-commit', required=True)
parser.add_argument('--require-application', action='store_true')
parser.add_argument('--expected-migration', default='0002_native_retrieval')
parser.add_argument('--output', default='/var/log/mantra-release-evidence.json')
args = parser.parse_args()
if not re.fullmatch(r'[a-f0-9]{40}', args.expected_commit):
    raise SystemExit('Expected a full Git commit SHA.')
os.chdir('/opt/mantra')


def run(argv):
    return subprocess.check_output(argv, text=True).strip()


compose = ['docker', 'compose', '--env-file', '.env']
container_id = run(compose + ['ps', '-q', 'backend'])
reference = run(['docker', 'inspect', '--format', '{{.Config.Image}}', container_id])
image_id = run(['docker', 'inspect', '--format', '{{.Image}}', container_id])
digests = json.loads(run(['docker', 'image', 'inspect', '--format', '{{json .RepoDigests}}', image_id]))
registry = re.fullmatch(r'([0-9]{12})\.dkr\.ecr\.([a-z0-9-]+)\.amazonaws\.com/([a-z0-9_/-]+)(?::[a-f0-9]{40}|@sha256:[a-f0-9]{64})', reference)
if not registry:
    raise SystemExit('Running backend must use an immutable project ECR reference.')
expected_digest = run(['aws', 'ecr', 'describe-images', '--registry-id', registry[1],
                       '--region', registry[2], '--repository-name', registry[3],
                       '--image-ids', 'imageTag=' + args.expected_commit,
                       '--query', 'imageDetails[0].imageDigest', '--output', 'text'])
repository = f'{registry[1]}.dkr.ecr.{registry[2]}.amazonaws.com/{registry[3]}'
expected_reference = repository + '@' + expected_digest
values = {}
for line in Path('.env').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key] = shlex.split(value)[0] if value else ''

schema_sql = """SELECT json_build_object(
 'native_retrieval_columns', (SELECT count(*)=2 FROM information_schema.columns WHERE table_schema='public' AND table_name='document_chunks' AND column_name IN ('embedding','ts_content')),
 'alembic_version_table', to_regclass('public.alembic_version') IS NOT NULL
);"""
schema = json.loads(run(compose + ['exec', '-T', 'db', 'psql', '-U', 'mantra_user', '-d', 'mantra_db', '-Atc', schema_sql]))
migration_version = None
if schema['alembic_version_table']:
    migration_version = run(compose + ['exec', '-T', 'db', 'psql', '-U', 'mantra_user', '-d', 'mantra_db', '-Atc', 'SELECT version_num FROM alembic_version ORDER BY version_num;'])
backups = json.loads(run([
    'aws', 's3api', 'list-objects-v2', '--bucket', values['IKI_S3_BUCKET'],
    '--prefix', 'backups/', '--query', 'Contents[].{key:Key,modified:LastModified,size:Size}', '--output', 'json',
])) or []
backups = [item for item in backups if item['size'] > 0]
latest = max(backups, key=lambda item: item['modified']) if backups else None
now = datetime.now(timezone.utc)
backup_age = (now - datetime.fromisoformat(latest['modified'].replace('Z', '+00:00'))).total_seconds() / 3600 if latest else None
site = values['MANTRA_SITE_ADDRESS']
with socket.create_connection((site, 443), timeout=10) as stream:
    with ssl.create_default_context().wrap_socket(stream, server_hostname=site) as secured:
        certificate = secured.getpeercert()
expiry = datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate['notAfter']), timezone.utc)
checks = {
    'backend_commit_matches': reference in {repository + ':' + args.expected_commit, expected_reference},
    'registry_digest_matches_commit': expected_reference in (digests or []),
    'backup_within_36_hours': backup_age is not None and backup_age < 36,
    'https_valid_more_than_24_hours': (expiry - now).total_seconds() > 86400,
}
application_checks = {
    'native_retrieval_schema_present': schema['native_retrieval_columns'],
    'migration_matches_release': migration_version == args.expected_migration,
}
result = {
    'observed_at_utc': now.isoformat(), 'expected_commit': args.expected_commit,
    'running_backend_reference': reference, 'registry_digests': digests,
    'expected_registry_digest': expected_digest,
    'platform_checks': checks, 'application_schema_checks': application_checks,
    'migration_version': migration_version,
    'latest_backup': latest, 'backup_age_hours': round(backup_age, 2) if backup_age is not None else None,
    'tls_expires_utc': expiry.isoformat(),
    'functional_acceptance': 'Pending application-owner fixtures and joint sign-off; schema checks alone are insufficient',
}
serialized = json.dumps(result, indent=2)
Path(args.output).write_text(serialized + '\n')
print(serialized)
if not all(checks.values()) or (args.require_application and not all(application_checks.values())):
    raise SystemExit(1)
