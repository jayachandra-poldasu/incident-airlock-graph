import pytest
from pydantic import ValidationError
from app.models import AlertRequest, Severity

def test_alert_request_validation():
    # Valid
    alert = AlertRequest(
        service_id="test",
        error_message="error"
    )
    assert alert.severity == Severity.HIGH
    
    # Invalid missing required
    with pytest.raises(ValidationError):
        AlertRequest(service_id="test")
        
    # Invalid enum
    with pytest.raises(ValidationError):
        AlertRequest(service_id="test", error_message="err", severity="invalid")
