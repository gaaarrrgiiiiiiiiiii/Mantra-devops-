import json
from pathlib import Path
import sys

data = json.loads(Path(sys.argv[1]).read_text())
findings = [(result, finding) for result in data.get('Results', []) for finding in result.get('Vulnerabilities', [])]
print(json.dumps({'total': len(findings), 'fixable': sum(bool(f.get('FixedVersion')) for _, f in findings), 'critical': sum(f['Severity'] == 'CRITICAL' for _, f in findings)}))
for result, finding in findings:
    if finding.get('FixedVersion'):
        print(json.dumps({key: finding.get(key) for key in ['VulnerabilityID', 'PkgName', 'PkgPath', 'InstalledVersion', 'FixedVersion']}))
