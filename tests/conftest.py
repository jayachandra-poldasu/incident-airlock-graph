"""
Shared test fixtures for the Incident Airlock Graph test suite.
"""

import os
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset the settings cache before each test."""
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings():
    """Settings configured for testing (no AI backend)."""
    with patch.dict(os.environ, {
        "AIRLOCK_AI_BACKEND": "none",
        "AIRLOCK_DEBUG": "true",
    }):
        from app.config import get_settings
        get_settings.cache_clear()
        settings = get_settings()
        yield settings
        get_settings.cache_clear()


@pytest.fixture
def api_client(test_settings):
    """FastAPI test client."""
    from app.main import app
    client = TestClient(app)
    yield client


@pytest.fixture
def sample_alert():
    from app.models import AlertRequest, Severity, IncidentCategory
    return AlertRequest(
        service_id="payment-service",
        error_message="Payment gateway requests taking > 5s, multiple 504 Gateway Timeouts.",
        severity=Severity.HIGH,
        category=IncidentCategory.LATENCY
    )

@pytest.fixture
def sample_db_alert():
    from app.models import AlertRequest, Severity, IncidentCategory
    return AlertRequest(
        service_id="database-primary",
        error_message="CPU utilization reached 98%. Active connections queueing.",
        severity=Severity.CRITICAL,
        category=IncidentCategory.CAPACITY
    )
