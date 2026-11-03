"""Administer the private controller without placing its password in arguments."""
import argparse
import base64
from http.cookiejar import CookieJar
import json
import hashlib
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['status', 'disable', 'enable', 'validate', 'build', 'console', 'snapshot-build'])
parser.add_argument('--job', default='Mantra')
parser.add_argument('--file', default='Jenkinsfile')
parser.add_argument('--archive', default='/tmp/mantra-platform.tar.gz')
args = parser.parse_args()
password = Path('/var/lib/jenkins/secrets/mantra-admin-password').read_text().strip()
auth = 'Basic ' + base64.b64encode(('mantra-admin:' + password).encode()).decode()
opener = build_opener(HTTPCookieProcessor(CookieJar()))
base = 'http://127.0.0.1:8080'

def request(path, data=None, content_type=None):
    headers = {'Authorization': auth}
    if data is not None:
        crumb = json.loads(opener.open(Request(base + '/crumbIssuer/api/json', headers=headers)).read())
        headers[crumb['crumbRequestField']] = crumb['crumb']
    if content_type:
        headers['Content-Type'] = content_type
    return opener.open(Request(base + path, data=data, headers=headers), timeout=60).read()

if args.action == 'status':
    print(request('/api/json?tree=jobs[name,color,lastBuild[number,result,building]],quietingDown').decode())
elif args.action in ['disable', 'enable', 'build']:
    request('/job/' + args.job + '/' + args.action, data=b'')
    print(args.job + ': ' + args.action + ' requested')
elif args.action == 'validate':
    data = urlencode({'jenkinsfile': Path(args.file).read_text()}).encode()
    result = request('/pipeline-model-converter/validate', data, 'application/x-www-form-urlencoded').decode()
    print(result)
    if 'success' not in result.lower():
        raise SystemExit(1)
elif args.action == 'console':
    print(request('/job/' + args.job + '/lastBuild/consoleText').decode())
elif args.action == 'snapshot-build':
    archive = Path(args.archive)
    fingerprint = hashlib.sha256(archive.read_bytes()).hexdigest()
    directory = Path('/var/lib/jenkins/source-snapshots')
    directory.mkdir(exist_ok=True)
    snapshot = directory / (fingerprint + '.tar.gz')
    shutil.copy2(archive, snapshot)
    snapshot.chmod(0o644)
    script = Path(args.file).read_text().replace('checkout scm', 'deleteDir(); sh \'tar -xzf ' + str(snapshot) + ' -C "$WORKSPACE"\'')
    script = "env.GIT_COMMIT = '" + fingerprint[:40] + "'\nenv.GIT_BRANCH = 'platform-verification'\n" + script
    job = ET.Element('flow-definition', {'plugin': 'workflow-job'})
    ET.SubElement(job, 'description').text = 'Verification of supplied source archive ' + fingerprint + '; deployment stages disabled by branch condition.'
    definition = ET.SubElement(job, 'definition', {'class': 'org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition', 'plugin': 'workflow-cps'})
    ET.SubElement(definition, 'script').text = script
    ET.SubElement(definition, 'sandbox').text = 'true'
    body = ET.tostring(job, encoding='utf-8')
    name = 'Mantra-platform-verification'
    try:
        request('/job/' + name + '/config.xml', body, 'application/xml')
    except HTTPError as error:
        if error.code != 404:
            raise
        request('/createItem?' + urlencode({'name': name}), body, 'application/xml')
    request('/job/' + name + '/build', data=b'')
    print('Started verification of source archive ' + fingerprint)
