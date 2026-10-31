def test_swagger_and_documented_routes(client):
    assert client.get("/docs").status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            assert operation["tags"], path
            assert operation["summary"], path
            assert operation["description"], path
    upload = schema["paths"]["/api/documents/upload"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    assert upload["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("DocumentResponse")
    ask = schema["paths"]["/api/copilot/ask"]["post"]
    assert ask["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("CopilotQuery")
    assert ask["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("CopilotResponse")
    assert schema["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "X-API-Key"
    assert ask["security"] == [{"APIKeyHeader": []}]
    assert "503" in schema["paths"]["/ready"]["get"]["responses"]
    assert "text/event-stream" in schema["paths"]["/api/copilot/stream"]["post"]["responses"]["200"]["content"]
