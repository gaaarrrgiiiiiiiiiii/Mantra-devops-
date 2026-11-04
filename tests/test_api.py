from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


PAYLOAD = b"Pump P-205B bearing failure caused vibration. Replace the bearing and inspect lubrication."


def upload(client):
    return client.post(
        "/api/documents/upload", files={"file": ("work-order.txt", PAYLOAD, "text/plain")}
    )


def test_upload_retrieve_list_and_download(client):
    response = upload(client)
    assert response.status_code == 200
    document = response.json()
    assert document["status"] == "indexed"
    assert document["metadata"]["filename"] == "work-order.txt"
    assert document["chunks"][0]["content"] == PAYLOAD.decode()
    document_id = document["id"]
    fetched = client.get(f"/api/documents/{document_id}")
    assert fetched.status_code == 200
    persisted = fetched.json()
    # SQLite stores UTC timestamps without an offset; compare the same instant.
    created = datetime.fromisoformat(document["metadata"].pop("created_at"))
    stored = datetime.fromisoformat(persisted["metadata"].pop("created_at"))
    assert stored.replace(tzinfo=timezone.utc) == created
    assert persisted == document
    listed = client.get("/api/documents").json()
    assert len(listed) == 1 and listed[0]["id"] == document_id
    assert client.get("/api/documents", params={"document_type": "pdf"}).json() == []
    raw = client.get(f"/api/documents/{document_id}/raw")
    assert raw.status_code == 200
    assert raw.content == PAYLOAD
    assert "work-order.txt" in raw.headers["content-disposition"]


def test_duplicate_upload_does_not_add_a_document(client):
    original = upload(client).json()
    duplicate = upload(client).json()
    assert duplicate["status"] == "duplicate"
    assert duplicate["duplicate_of"] == original["id"]
    assert len(client.get("/api/documents").json()) == 1


@pytest.mark.parametrize(
    "filename,payload,status",
    [("empty.txt", b"", 400), ("large.txt", b"x" * 1025, 413), ("unsupported.exe", b"content", 415)],
)
def test_upload_rejects_bad_files(client, filename, payload, status):
    response = client.post("/api/documents/upload", files={"file": (filename, payload)})
    assert response.status_code == status
    assert response.json()["detail"]
    assert client.get("/api/documents").json() == []


def test_upload_requires_a_file(client):
    assert client.post("/api/documents/upload").status_code == 422


@pytest.mark.parametrize("suffix", ["", "/raw"])
def test_unknown_document_returns_404(client, suffix):
    assert client.get(f"/api/documents/unknown{suffix}").status_code == 404


def test_document_lookup_uses_repository(client, monkeypatch):
    document = upload(client).json()
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(client.app.state.repository, "get_document", lookup)
    response = client.get(f"/api/documents/{document['id']}")
    assert response.status_code == 404
    lookup.assert_awaited_once_with(document["id"])


def test_copilot_returns_cited_answer(client):
    document = upload(client).json()
    response = client.post("/api/copilot/ask", json={"question": "P-205B bearing failure", "limit": 3})
    assert response.status_code == 200
    answer = response.json()
    assert answer["answer"]
    assert answer["retrieved_chunk_count"] >= 1
    assert answer["citations"][0]["document_id"] == document["id"]
    assert answer["citations"][0]["filename"] == "work-order.txt"


def test_copilot_empty_database(client):
    response = client.post("/api/copilot/ask", json={"question": "bearing failure"})
    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert response.json()["retrieved_chunk_count"] == 0


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "pump", "limit": 0}, {"question": "pump", "limit": 11}])
def test_copilot_validates_request(client, payload):
    assert client.post("/api/copilot/ask", json=payload).status_code == 422


@pytest.mark.parametrize("key", [None, "incorrect"])
@pytest.mark.parametrize("path", ["/api/documents/upload", "/api/copilot/ask"])
def test_data_endpoints_require_api_key(client, key, path):
    client.headers.pop("X-API-Key")
    headers = {} if key is None else {"X-API-Key": key}
    response = client.post(path, headers=headers, json={"question": "pump"})
    assert response.status_code == 401
