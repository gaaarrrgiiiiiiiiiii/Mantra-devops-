"""Apply the rotated password to an existing Grafana data volume."""
from pathlib import Path
import shlex
import subprocess

root = Path('/opt/mantra')
values = {}
for line in (root / '.env').read_text().splitlines():
    if line.strip() and not line.lstrip().startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key] = shlex.split(value)[0] if value else ''
subprocess.run(
    ['docker', 'compose', '--env-file', '.env', 'exec', '-T', 'grafana',
     'grafana', 'cli', 'admin', 'reset-admin-password', '--password-from-stdin'],
    cwd=root, input=values['GRAFANA_ADMIN_PASSWORD'] + '\n', text=True,
    check=True, stdout=subprocess.DEVNULL,
)
print('Grafana admin password synchronized with the protected production configuration')
