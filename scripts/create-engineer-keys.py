"""Create individual SSH keys in the operator's private SSH directory, once."""
import json
from pathlib import Path
import subprocess

ssh_dir = Path.home() / '.ssh'
ssh_dir.mkdir(exist_ok=True)
public_keys = []
for name in ['mantra-eng1', 'mantra-eng2']:
    key = ssh_dir / name
    if not key.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', name, '-f', str(key)], check=True)
    public_keys.append(key.with_suffix('.pub').read_text().strip())
root = Path(__file__).resolve().parents[1]
output = root / '.local' / 'engineer-keys.json'
output.write_text(json.dumps({'engineer_public_keys': public_keys}))
print('Individual private keys remain in the operator SSH directory; public-key inventory created.')
