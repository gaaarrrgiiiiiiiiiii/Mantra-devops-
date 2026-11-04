"""Reproduce an atomic file-bind update and exercise the shared activation tasks."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='mantra-gateway-regression-') as directory:
    work = Path(directory)
    (work / '.env').write_text('')
    config = work / 'Caddyfile'
    config.write_text(':80 {\n respond "before"\n}\n')
    (work / 'docker-compose.yml').write_text(
        'services:\n  gateway:\n    image: caddy:2.11.7-alpine\n'
        f'    ports: ["127.0.0.1:{port}:80"]\n'
        '    volumes: ["./Caddyfile:/etc/caddy/Caddyfile:ro"]\n'
    )
    compose = ['docker', 'compose', '--env-file', '.env']

    def body():
        with urlopen(f'http://127.0.0.1:{port}', timeout=3) as response:
            return response.read().decode()

    try:
        subprocess.run(compose + ['up', '-d'], cwd=work, check=True, capture_output=True)
        for attempt in range(30):
            try:
                assert body() == 'before'
                break
            except Exception:
                if attempt == 29:
                    raise
                time.sleep(1)
        replacement = work / 'Caddyfile.new'
        replacement.write_text(':80 {\n respond "after"\n}\n')
        os.replace(replacement, config)
        assert body() == 'before', 'Expected to reproduce the stale mounted-inode behavior'
        (work / 'inventory.ini').write_text('[app_servers]\nlocalhost ansible_connection=local\n')
        (work / 'activate.yml').write_text(
            '- hosts: app_servers\n  become: true\n  vars:\n'
            f'    app_dir: {json.dumps(str(work))}\n'
            '    backend_image: unused\n    deployment_configuration: {changed: false}\n'
            '  tasks:\n    - ansible.builtin.import_tasks: '
            + json.dumps(str(root / 'ansible/tasks/activate-gateway.yml')) + '\n'
        )
        command = ['ansible-playbook', '-i', 'inventory.ini', 'activate.yml']
        first = subprocess.run(command, cwd=work, text=True, capture_output=True)
        if first.returncode:
            raise RuntimeError(first.stdout + first.stderr)
        assert body() == 'after', 'Activation did not load the newly mounted configuration'
        second = subprocess.run(command, cwd=work, text=True, capture_output=True)
        assert second.returncode == 0 and 'changed=0' in second.stdout, second.stdout + second.stderr
        print(json.dumps({'stale_mount_reproduced': True, 'new_routing_activated': True, 'second_run_idempotent': True}))
    finally:
        subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], cwd=work, capture_output=True, check=True)
