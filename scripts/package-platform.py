"""Package deployment sources without workstation secrets or generated output."""
from pathlib import Path
import tarfile


root = Path(__file__).resolve().parents[1]
output = root / ".local" / "mantra-platform.tar.gz"
output.parent.mkdir(exist_ok=True)
sources = [
    "backend", "frontend", "ansible", "prometheus", "grafana", "postgres", "jenkins", "scripts", "tests",
    "docker-compose.yml", "Caddyfile", "Jenkinsfile", ".env.example", "pytest.ini",
]
excluded = {"node_modules", "dist", "__pycache__", ".pytest_cache", ".local", ".git"}
with tarfile.open(output, "w:gz") as archive:
    for source in sources:
        path = root / source
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in files:
            relative = file.relative_to(root)
            if not file.is_file() or any(part in excluded for part in relative.parts):
                continue
            if file.name.startswith(".env") and file.name != ".env.example":
                continue
            if file.suffix in {".pyc", ".db", ".sqlite", ".pem"}:
                continue
            archive.add(file, arcname=relative.as_posix(), recursive=False)
print(output)
