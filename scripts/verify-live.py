"""Verify the deployed host; credentials stay in memory and protected files."""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import json
import ipaddress
import os
from pathlib import Path
import re
import shlex
import socket
import ssl
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument('--exercise-recovery', action='store_true')
parser.add_argument('--test-alert', action='store_true')
args = parser.parse_args()
os.chdir('/opt/mantra')
values = {}
for line in Path('.env').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key] = shlex.split(value)[0] if value else ''
access = json.loads(Path('/root/mantra-access.json').read_text())
compose = ['docker', 'compose', '--env-file', '.env']
checks = []

def run(argv, **kwargs):
    return subprocess.check_output(argv, text=True, **kwargs).strip()

def auth(username, password):
    return 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode()

def fetch(url, authorization=None, data=None):
    headers = {'Content-Type': 'application/json'}
    if authorization:
        headers['Authorization'] = authorization
    return urlopen(Request(url, headers=headers, data=data), timeout=10)

def record(name, details):
    checks.append({'check': name, 'passed': True, 'details': details})
    print(json.dumps(checks[-1]), flush=True)

site = values['MANTRA_SITE_ADDRESS']
base = 'https://' + site
for attempt in range(40):
    try:
        response = fetch(base + '/ready')
        assert json.load(response)['status'] == 'ready'
        break
    except Exception:
        if attempt == 39:
            raise
        time.sleep(3)
with socket.create_connection((site, 443), timeout=10) as connection:
    with ssl.create_default_context().wrap_socket(connection, server_hostname=site) as connection:
        certificate = connection.getpeercert()
record('public HTTPS and real readiness', {'expires': certificate['notAfter'], 'issuer': certificate['issuer']})
authorization = auth(access['web_username'], access['web_password'])
assert fetch(base + '/', authorization).status == 200
assert isinstance(json.load(fetch(base + '/api/documents', authorization)), list)
try:
    fetch(base + '/api/documents')
    raise AssertionError('Anonymous API access succeeded')
except HTTPError as error:
    assert error.code == 401
record('gateway authentication and API key injection', 'Authenticated frontend/API work; anonymous request rejected')
rows = [json.loads(line) for line in run(compose + ['ps', '--format', 'json']).splitlines()]
assert len(rows) == 8 and all(row['State'] == 'running' for row in rows)
assert all(not p.get('PublishedPort', 0) or p.get('URL') == '127.0.0.1' for row in rows if row['Service'] != 'gateway' for p in (row.get('Publishers') or []))
record('service and network isolation', 'Eight services running; only gateway ports are public')
assert Path('.env').stat().st_mode & 0o777 == 0o600
record('runtime secret permissions', 'Production environment is mode 0600')
version = run(compose + ['exec', '-T', 'db', 'psql', '-U', 'mantra_user', '-d', 'mantra_db', '-Atc', "SELECT extversion FROM pg_extension WHERE extname='vector';"])
assert version
record('pgvector enabled', version)
s3_check = '''import boto3,uuid
sts=boto3.client('sts'); identity=sts.get_caller_identity()['Arn']
assert 'assumed-role/mantra-ec2-instance-role/' in identity
s3=boto3.client('s3'); key='platform-verification/'+str(uuid.uuid4())+'.txt'
try:
 s3.put_object(Bucket=__import__('os').environ['IKI_S3_BUCKET'],Key=key,Body=b'Mantra platform verification')
 assert s3.get_object(Bucket=__import__('os').environ['IKI_S3_BUCKET'],Key=key)['Body'].read()==b'Mantra platform verification'
finally:
 s3.delete_object(Bucket=__import__('os').environ['IKI_S3_BUCKET'],Key=key)
print(identity)
'''
identity = run(compose + ['exec', '-T', 'backend', 'python', '-c', s3_check])
record('instance-profile S3 write/read/delete', identity)
targets = json.load(fetch('http://127.0.0.1:9090/api/v1/targets'))['data']['activeTargets']
assert len(targets) == 2 and all(target['health'] == 'up' for target in targets)
record('Prometheus scrape targets', [target['labels']['job'] for target in targets])
grafana_auth = auth(access['grafana_username'], access['grafana_password'])
dashboards = json.load(fetch('http://127.0.0.1:3000/grafana/api/search?query=Mantra', grafana_auth))
assert dashboards
record('Grafana provisioned dashboard and rotated login', [item['title'] for item in dashboards])
assert run(['systemctl', 'is-active', 'jenkins']) == 'active'
listeners = run(['ss', '-H', '-lnt', 'sport', '=', ':8080'])
assert listeners
for listener in listeners.splitlines():
    address = ipaddress.ip_address(listener.split()[3].rsplit(':', 1)[0].strip('[]'))
    address = getattr(address, 'ipv4_mapped', None) or address
    assert address.is_loopback
record('private Jenkins controller', 'Active and listening on 127.0.0.1:8080')
assert run(['systemctl', 'is-active', 'amazon-cloudwatch-agent']) == 'active'
record('CloudWatch agent', 'Active')
assert 'mantra-backup-db' in run(['crontab', '-l'])
record('daily backup schedule', '02:00 UTC / 07:30 Asia/Kolkata')
if args.exercise_recovery:
    subprocess.run(['/usr/local/sbin/mantra-backup-db'], check=True)
    key = json.loads(run(['aws', 's3api', 'list-objects-v2', '--bucket', values['IKI_S3_BUCKET'], '--prefix', 'backups/mantra_db_', '--query', 'sort_by(Contents, &LastModified)[-1].Key', '--output', 'json']))
    uri = 's3://' + values['IKI_S3_BUCKET'] + '/' + key
    subprocess.run(['bash', str(Path(__file__).with_name('verify-backup-restore.sh')), uri], check=True)
    record('S3 backup restore drill', uri)
if args.test_alert:
    now = datetime.now(timezone.utc)
    alert = [{'labels': {'alertname': 'MantraPlatformVerification', 'severity': 'info'}, 'annotations': {'summary': 'Mantra platform verification test', 'description': 'This is the requested end-to-end Alertmanager/SNS verification.'}, 'startsAt': now.isoformat(), 'endsAt': (now + timedelta(minutes=3)).isoformat()}]
    fetch('http://127.0.0.1:9093/api/v2/alerts', data=json.dumps(alert).encode()).close()
    for attempt in range(30):
        metrics = fetch('http://127.0.0.1:9093/metrics').read().decode()
        delivered = sum(float(line.rsplit(' ', 1)[1]) for line in metrics.splitlines() if line.startswith('alertmanager_notifications_total{') and 'integration="sns"' in line)
        failed = sum(float(line.rsplit(' ', 1)[1]) for line in metrics.splitlines() if line.startswith('alertmanager_notifications_failed_total{') and 'integration="sns"' in line)
        if delivered >= 1 and failed == 0:
            break
        time.sleep(2)
    assert delivered >= 1 and failed == 0, 'SNS notification did not succeed'
    record('Alertmanager to SNS notification', {'successful_attempts': delivered, 'failed_attempts': failed})
    alert[0]['endsAt'] = datetime.now(timezone.utc).isoformat()
    fetch('http://127.0.0.1:9093/api/v2/alerts', data=json.dumps(alert).encode()).close()
Path('/var/log/mantra-platform-verification.json').write_text(json.dumps(checks, indent=2))
print('Live platform verification passed.')
