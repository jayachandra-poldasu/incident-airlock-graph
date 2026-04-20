
def test_health_check(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services_loaded"] > 0
    
def test_list_services(api_client):
    response = api_client.get("/services")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "payment-service" in [s["id"] for s in data]

def test_perform_triage(api_client, sample_alert):
    response = api_client.post("/triage", json=sample_alert.model_dump())
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "complete"
    assert "ai_summary" in data
    assert len(data["matched_incidents"]) > 0
    assert len(data["runbook_suggestions"]) > 0
    assert data["likely_owner"] is not None
    
def test_list_incidents(api_client):
    response = api_client.get("/incidents?service_id=payment-service")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for inc in data:
        assert inc["service_id"] == "payment-service"

def test_get_incident(api_client):
    response = api_client.get("/incidents/inc-2023-01")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "inc-2023-01"

def test_get_incident_not_found(api_client):
    response = api_client.get("/incidents/unknown-id")
    assert response.status_code == 404
