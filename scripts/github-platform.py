"""Inspect/enforce platform GitHub controls using private existing authentication."""
import argparse
import json
import os
from pathlib import Path
import ssl
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPOSITORY = 'gaaarrrgiiiiiiiiiii/Mantra-devops-'
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['audit', 'protect'])
parser.add_argument('--output', type=Path)
args = parser.parse_args()
token = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
if not token:
    result = subprocess.run(
        ['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
        capture_output=True, text=True, check=True,
    )
    token = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line).get('password')
if not token:
    raise SystemExit('No existing GitHub credential available; configure a private credential flow.')
context = ssl.create_default_context()
if os.name == 'nt':
    # Respect the Windows trust store as well as Python's bundled roots.
    for store in ('ROOT', 'CA'):
        for certificate, encoding, trust in ssl.enum_certificates(store):
            if encoding == 'x509_asn' and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(certificate))


def api(path, body=None, method=None):
    request = Request(
        'https://api.github.com/repos/' + REPOSITORY + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'Mantra-platform-audit',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urlopen(request, context=context, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        # Never include request headers, credential-helper output or token in errors.
        raise SystemExit(f'GitHub {method or "GET"} {path}: HTTP {error.code}') from None


if args.action == 'protect':
    api('/branches/main/protection', {
        'required_status_checks': {
            'strict': True,
            'checks': [{'context': name, 'app_id': 15368} for name in ['test', 'docker-build', 'frontend-build', 'schema-contract']],
        },
        'enforce_admins': True,
        'required_pull_request_reviews': {
            'dismiss_stale_reviews': True,
            'require_code_owner_reviews': True,
            'required_approving_review_count': 1,
        },
        'restrictions': None,
        'required_conversation_resolution': True,
        'required_linear_history': False,
        'allow_force_pushes': False,
        'allow_deletions': False,
    }, 'PUT')

branch = api('/branches/main')
protection = api('/branches/main/protection') if branch['protected'] else None
pull = api('/pulls/3')
checks = api('/commits/' + branch['commit']['sha'] + '/check-runs?per_page=100')
permission = api('/collaborators/Bazzin07/permission')
result = {
    'repository': REPOSITORY,
    'main_sha': branch['commit']['sha'],
    'protected': branch['protected'],
    'protection': protection,
    'application_repository_permission': permission['permission'],
    'application_pr': {
        'url': pull['html_url'], 'state': pull['state'], 'merged': pull['merged'],
        'head_sha': pull['head']['sha'], 'head_repository': pull['head']['repo']['full_name'],
        'head_branch': pull['head']['ref'], 'mergeable': pull['mergeable'],
        'mergeable_state': pull['mergeable_state'],
    },
    'main_checks': [
        {key: check[key] for key in ['name', 'status', 'conclusion', 'head_sha']}
        | {'app_id': check['app']['id']} for check in checks['check_runs']
    ],
}
serialized = json.dumps(result, indent=2)
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized + '\n', encoding='utf-8')
print(serialized)
