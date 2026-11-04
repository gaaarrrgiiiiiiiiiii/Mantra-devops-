"""Representative demonstration flows; not a domain-quality certification."""
import json

import pytest

from app.config import Settings
from app.main import create_app

DOCUMENT = b'On 2026-10-01 Pump P-205B suffered bearing failure and vibration. SOP-101 requires lubrication inspection and bearing replacement. ISO 9001 maintenance records are incomplete. Technician Arun Kumar inspected the pump.'


def upload(client):
    result = client.post('/api/documents/upload', files={'file': ('incident.txt', DOCUMENT, 'text/plain')})
    assert result.status_code == 200, result.text
    return result.json()


def test_graph_equipment_and_maintenance_preserve_evidence(client):
    document = upload(client)
    graph = client.get('/api/knowledge-graph').json()
    assert graph['nodes'] and graph['edges']
    assert any(node['type'] == 'EQUIPMENT_TAG' for node in graph['nodes'])
    equipment = client.get('/api/knowledge-graph/equipment/P-205B')
    assert equipment.status_code == 200 and equipment.json()['nodes']
    health = client.get('/api/maintenance/health/P-205B').json()
    assert health['document_count'] == 1
    assert 'bearing failure' in health['failure_history']
    report = client.post('/api/maintenance/rca/P-205B')
    assert report.status_code == 200 and report.json()['narrative']
    assert report.json()['generation_status'] == 'deterministic'
    predictions = client.get('/api/maintenance/predictions').json()
    assert predictions and any(prediction['justification'] for prediction in predictions)
    investigation = client.post('/api/maintenance/investigate', json={'question': 'P-205B bearing failure'})
    assert investigation.status_code == 200 and investigation.json()['narrative']
    assert document['id'] in json.dumps(graph)


def test_compliance_outputs_expose_evidence_and_demo_limitations(client):
    upload(client)
    status = client.get('/api/compliance/status').json()
    assert status['regulations'] and status['framework_disclaimer']
    assert 0 <= status['overall_coverage_pct'] <= 100
    regulation = next(item['regulation'] for item in status['regulations'] if '9001' in item['regulation'])
    audit = client.post('/api/compliance/audit/' + regulation)
    assert audit.status_code == 200
    assert audit.json()['requirements'] and audit.json()['disclaimer']
    assert audit.json()['generation_status'] == 'deterministic'
    assert any(requirement['citations'] for requirement in audit.json()['requirements'])
    gaps = client.get('/api/compliance/gaps').json()
    assert gaps and all(gap['action_needed'] for gap in gaps)
    equipment = client.get('/api/compliance/equipment/P-205B')
    assert equipment.status_code == 200 and equipment.json()['equipment_tag'] == 'P-205B'


def test_incident_analysis_streaming_and_admin_counts(client):
    document = upload(client)
    document_id = document['id']
    incident = client.get('/api/failures/analysis/' + document_id).json()
    assert incident['document_id'] == document_id
    assert incident['affected_equipment'] and incident['root_cause_summary']
    similar = client.get('/api/failures/similar/' + document_id).json()
    assert similar['seed_document_id'] == document_id
    warning = client.post('/api/failures/analyze', params={'document_id': document_id})
    assert warning.status_code == 200 and 'risk_level' in warning.json()
    stream = client.post('/api/copilot/stream', json={'question': 'P-205B bearing failure'})
    assert stream.status_code == 200 and 'text/event-stream' in stream.headers['content-type']
    frames = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith('data: ')]
    assert any(frame['type'] == 'token' and frame['text'] for frame in frames)
    assert frames[-1]['type'] == 'done'
    assert frames[-1]['citations'][0]['document_id'] == document_id
    assert frames[-1]['generation_status'] == 'deterministic'
    assert frames[-1]['model_used'] is None
    assert incident['generation_status'] == 'deterministic'
    overview = client.get('/api/admin/overview').json()
    assert overview['documents']['total_documents'] == 1
    assert overview['pipeline']['documents_indexed'] == 1


@pytest.mark.parametrize('path', ['/api/maintenance/clusters', '/api/failures/patterns'])
def test_optional_clustering_reports_capability_honestly(client, path):
    upload(client)
    response = client.get(path)
    assert response.status_code == 200
    report = response.json()
    assert isinstance(report['available'], bool)
    if not report['available']:
        assert report['reason']


@pytest.mark.parametrize('path', ['/api/knowledge-graph', '/api/maintenance/health/P-205B', '/api/compliance/status', '/api/failures/patterns', '/api/admin/overview'])
def test_feature_families_require_authentication(client, path):
    client.headers.pop('X-API-Key')
    assert client.get(path).status_code == 401


def test_rate_limit_cannot_be_reset_with_untrusted_forwarded_headers(client, monkeypatch):
    settings = client.app.state.ingestion.settings
    monkeypatch.setattr(settings, 'rate_limit_per_minute', 2)
    monkeypatch.setattr(settings, 'trust_proxy_headers', False)
    for index, expected in enumerate([200, 200, 429]):
        response = client.get('/api/documents', headers={'X-Forwarded-For': '192.0.2.' + str(index + 1)})
        assert response.status_code == expected
    assert response.headers['retry-after'] == '60'
    assert client.get('/health').status_code == 200


def test_production_authentication_fails_closed():
    with pytest.raises(RuntimeError, match='Production requires'):
        create_app(Settings(_env_file=None, environment='production', repository_backend='memory', require_api_key=False, api_key=''))


def test_postgres_dimension_contract_rejects_incompatible_model():
    with pytest.raises(ValueError, match='768-dimensional'):
        Settings(_env_file=None, repository_backend='postgres', embedding_dimension=384)


@pytest.mark.parametrize('spelling', ['ISO 9001', 'ISO-9001', 'ISO9001'])
def test_regulation_spelling_does_not_hide_evidence(client, spelling):
    body = f'{spelling} quality management inspection finding documented in SOP-101 for Pump P-205B.'
    document = client.post('/api/documents/upload', files={'file': ('quality.txt', body.encode(), 'text/plain')}).json()
    audit = client.post('/api/compliance/audit/ISO-9001').json()
    assert audit['generation_status'] == 'deterministic'
    assert any(citation['document_id'] == document['id'] for requirement in audit['requirements'] for citation in requirement['citations'])
