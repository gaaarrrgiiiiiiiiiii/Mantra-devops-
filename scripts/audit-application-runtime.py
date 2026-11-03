"""Read deployment identity and schema metadata without exposing credentials."""
import argparse
import json
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--require-retrieval-schema', action='store_true')
args = parser.parse_args()
os.chdir('/opt/mantra')
compose = ['docker', 'compose', '--env-file', '.env']

def run(argv):
    return subprocess.check_output(argv, text=True).strip()

rows = [json.loads(line) for line in run(compose + ['ps', '--format', 'json']).splitlines()]
backend = next(row for row in rows if row['Service'] == 'backend')
sql = """SELECT json_build_object(
 'chunk_columns', (SELECT json_agg(column_name ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema='public' AND table_name='document_chunks'),
 'chunk_indexes', (SELECT json_agg(indexdef) FROM pg_indexes WHERE schemaname='public' AND tablename='document_chunks'),
 'alembic_version_table', to_regclass('public.alembic_version') IS NOT NULL
);"""
schema = json.loads(run(compose + ['exec', '-T', 'db', 'psql', '-U', 'mantra_user', '-d', 'mantra_db', '-Atc', sql]))
mode_code = "from app.config import get_settings; import json; s=get_settings(); print(json.dumps({key:getattr(s,key) for key in ['environment','repository_backend','embedding_backend','llm_provider','auto_create_schema']}))"
modes = json.loads(run(compose + ['exec', '-T', 'backend', 'python', '-c', mode_code]))
columns = set(schema.get('chunk_columns') or [])
result = {
    'backend_image': backend['Image'],
    'runtime_modes': modes,
    'schema': schema,
    'native_retrieval_columns_present': {'embedding', 'ts_content'}.issubset(columns),
    'application_feature_acceptance': 'Requires application tests and domain evaluation; health checks alone do not establish completion',
}
print(json.dumps(result, indent=2))
if args.require_retrieval_schema and not result['native_retrieval_columns_present']:
    raise SystemExit(1)
