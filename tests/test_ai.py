from unittest.mock import patch
from app.ai import check_ai_health, generate_triage_summary
from app.models import TriageResult

@patch('requests.get')
def test_check_ai_health_ollama(mock_get, test_settings):
    test_settings.ai_backend = "ollama"
    mock_get.return_value.status_code = 200
    
    assert check_ai_health(test_settings) is True
    
def test_check_ai_health_none(test_settings):
    test_settings.ai_backend = "none"
    assert check_ai_health(test_settings) is True

def test_deterministic_summary(test_settings, sample_alert):
    # Just need a basic object
    tr = TriageResult(
        triage_id="test",
        alert=sample_alert
    )
    
    summary = generate_triage_summary(tr, test_settings)
    assert "Deterministic Triage Summary for payment-service" in summary
