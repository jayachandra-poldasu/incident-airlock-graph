from app.models import AlertRequest
from app.engine import match_incidents, suggest_runbooks, identify_owner, find_change_correlations, compute_text_similarity

def test_compute_text_similarity():
    sim = compute_text_similarity("Payment gateway timeout", "Gateway timeout on payment service")
    assert sim > 0.4
    
    sim2 = compute_text_similarity("CPU spike on database", "Memory leak in auth")
    assert sim2 < 0.2

def test_match_incidents(sample_alert):
    matches = match_incidents(sample_alert)
    assert len(matches) > 0
    # Top match should be the payment gateway timeout
    assert matches[0].incident.id == "inc-2023-01"
    assert "service_match" in matches[0].score_breakdown
    assert "category_match" in matches[0].score_breakdown
    
def test_suggest_runbooks(sample_alert):
    matches = match_incidents(sample_alert)
    runbooks = suggest_runbooks(sample_alert, matches)
    
    assert len(runbooks) > 0
    # Should suggest payment runbook
    assert any(rb.runbook.id == "rb-pay-01" for rb in runbooks)

def test_identify_owner(sample_alert):
    matches = match_incidents(sample_alert)
    owner = identify_owner(sample_alert, matches)
    
    # Alice Chen is owner and resolved past payment incidents
    assert owner.recommended_owner == "Alice Chen"
    assert "Currently on-call" in owner.evidence

def test_find_change_correlations():
    # Use the current change in the sample data (set for 2026-04)
    from datetime import datetime, timedelta
    
    # Create an alert right after the change
    alert_time = datetime.fromisoformat("2026-04-19T20:00:00Z") + timedelta(hours=1)
    
    alert = AlertRequest(
        service_id="payment-service",
        error_message="Timeout",
        timestamp=alert_time.isoformat()
    )
    
    changes = find_change_correlations(alert)
    
    assert len(changes) > 0
    assert changes[0].change.id == "chg-current-01"
    assert changes[0].is_direct_dependency
