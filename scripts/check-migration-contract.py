"""Require packaged, versioned migrations when a release changes database setup."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--base', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
changed = subprocess.check_output(
    ['git', '-c', 'safe.directory=' + root.as_posix(), 'diff', '--name-only', args.base + '...HEAD', '--',
     'backend/app/database.py', 'backend/app/db_models.py'], cwd=root, text=True,
).splitlines()
if not changed:
    print('No database setup/model changes; migration contract unchanged.')
    raise SystemExit(0)
required = [root / 'backend/alembic.ini', root / 'backend/migrations/env.py']
missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
if not list((root / 'backend/migrations/versions').glob('*.py')):
    missing.append('backend/migrations/versions/<revision>.py')
dockerfile = (root / 'backend/Dockerfile').read_text()
if 'alembic.ini' not in dockerfile or 'migrations' not in dockerfile:
    missing.append('Dockerfile packaging for alembic.ini and migrations/')
if missing:
    print('Database change cannot be promoted without versioned migrations:')
    for item in missing:
        print(' - ' + item)
    raise SystemExit(1)
print('Versioned migration files and Dockerfile packaging declarations found.')
print('Fresh/populated database upgrade tests are still required in application acceptance.')
