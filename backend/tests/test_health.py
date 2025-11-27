"""Health check endpoint tests."""

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"  # Endpoint returns "ok", not "healthy"
    assert "timestamp" in data



