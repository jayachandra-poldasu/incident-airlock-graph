"""
Pydantic models for API request/response schemas.

Defines the data contracts for the Incident Airlock Graph API, including
alert triage, incident matching, runbook retrieval, and owner identification.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    """Alert and incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentCategory(str, Enum):
    """Categories of incidents."""
    OUTAGE = "outage"
    DEGRADATION = "degradation"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    DATA_ISSUE = "data_issue"
    SECURITY = "security"
    CAPACITY = "capacity"
    DEPLOYMENT = "deployment"


class ChangeType(str, Enum):
    """Types of changes/deployments."""
    DEPLOYMENT = "deployment"
    CONFIG_CHANGE = "config_change"
    INFRA_CHANGE = "infra_change"
    DATABASE_MIGRATION = "database_migration"
    SCALING = "scaling"
    ROLLBACK = "rollback"


class TriageStatus(str, Enum):
    """Status of a triage analysis."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ESCALATED = "escalated"


# ── Core Data Models ────────────────────────────────────────────────────────


class ServiceInfo(BaseModel):
    """Information about a service in the dependency graph."""
    id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Human-readable service name")
    team: str = Field(default="", description="Owning team")
    owner: str = Field(default="", description="Primary owner")
    on_call: str = Field(default="", description="Current on-call engineer")
    escalation_path: list[str] = Field(
        default_factory=list,
        description="Escalation chain",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Service IDs this service depends on",
    )
    dependents: list[str] = Field(
        default_factory=list,
        description="Service IDs that depend on this service",
    )
    tier: str = Field(default="tier-2", description="Service tier (tier-1/2/3)")
    description: str = Field(default="", description="Service description")


class IncidentRecord(BaseModel):
    """A historical incident record."""
    id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title")
    service_id: str = Field(..., description="Affected service ID")
    severity: Severity = Field(..., description="Incident severity")
    category: IncidentCategory = Field(..., description="Incident category")
    description: str = Field(default="", description="Incident description")
    root_cause: str = Field(default="", description="Root cause analysis")
    resolution: str = Field(default="", description="How the incident was resolved")
    runbook_id: str = Field(default="", description="Runbook used during resolution")
    resolved_by: str = Field(default="", description="Engineer who resolved it")
    mttr_minutes: int = Field(default=0, description="Mean time to resolve in minutes")
    started_at: str = Field(default="", description="Incident start timestamp")
    resolved_at: str = Field(default="", description="Incident resolution timestamp")
    tags: list[str] = Field(default_factory=list, description="Incident tags/keywords")
    related_change_id: str = Field(
        default="",
        description="ID of change that may have caused this incident",
    )


class RunbookEntry(BaseModel):
    """A runbook for incident remediation."""
    id: str = Field(..., description="Unique runbook identifier")
    title: str = Field(..., description="Runbook title")
    service_ids: list[str] = Field(
        default_factory=list,
        description="Services this runbook applies to",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Incident categories this runbook addresses",
    )
    steps: list[str] = Field(default_factory=list, description="Remediation steps")
    last_updated: str = Field(default="", description="Last update timestamp")
    success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Historical success rate",
    )
    estimated_time_minutes: int = Field(
        default=0,
        description="Estimated time to complete in minutes",
    )
    tags: list[str] = Field(default_factory=list, description="Runbook tags/keywords")


class ChangeRecord(BaseModel):
    """A change or deployment record."""
    id: str = Field(..., description="Unique change identifier")
    service_id: str = Field(..., description="Service this change affects")
    change_type: ChangeType = Field(..., description="Type of change")
    description: str = Field(default="", description="Change description")
    author: str = Field(default="", description="Who made the change")
    timestamp: str = Field(default="", description="When the change was made")
    risk_level: str = Field(default="low", description="Risk level of the change")
    rollback_available: bool = Field(
        default=False,
        description="Whether rollback is possible",
    )


# ── Request Models ───────────────────────────────────────────────────────────


class AlertRequest(BaseModel):
    """Request payload for alert triage."""
    service_id: str = Field(
        ...,
        description="ID of the affected service",
        examples=["payment-service"],
    )
    error_message: str = Field(
        ...,
        min_length=1,
        description="Error message or alert description",
        examples=["Connection timeout to payment gateway"],
    )
    severity: Severity = Field(
        default=Severity.HIGH,
        description="Alert severity level",
    )
    category: Optional[IncidentCategory] = Field(
        default=None,
        description="Optional incident category hint",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Alert timestamp (ISO 8601)",
    )


# ── Response Models ──────────────────────────────────────────────────────────


class IncidentMatch(BaseModel):
    """A matched historical incident with relevance scoring."""
    incident: IncidentRecord = Field(
        ..., description="The matched incident record"
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall relevance score (0.0 to 1.0)",
    )
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Why this incident was matched",
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension score breakdown",
    )


class RunbookSuggestion(BaseModel):
    """A suggested runbook with relevance context."""
    runbook: RunbookEntry = Field(
        ..., description="The suggested runbook"
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score for this suggestion",
    )
    match_reasons: list[str] = Field(
        default_factory=list,
        description="Why this runbook was suggested",
    )


class OwnerSuggestion(BaseModel):
    """Suggested incident owner with evidence."""
    recommended_owner: str = Field(
        ..., description="Recommended owner name"
    )
    team: str = Field(default="", description="Owner's team")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this recommendation",
    )
    on_call: str = Field(
        default="",
        description="Current on-call engineer for the service",
    )
    escalation_path: list[str] = Field(
        default_factory=list,
        description="Escalation chain",
    )


class ChangeCorrelation(BaseModel):
    """A correlated change that may have caused the incident."""
    change: ChangeRecord = Field(
        ..., description="The correlated change record"
    )
    correlation_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How likely this change caused the issue",
    )
    time_delta_minutes: float = Field(
        default=0.0,
        description="Time between change and alert in minutes",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence of correlation",
    )
    is_direct_dependency: bool = Field(
        default=False,
        description="Whether the change is on a direct dependency",
    )


class TriageResult(BaseModel):
    """Complete triage analysis result."""
    triage_id: str = Field(..., description="Unique triage ID")
    alert: AlertRequest = Field(..., description="Original alert")
    status: TriageStatus = Field(
        default=TriageStatus.COMPLETE,
        description="Triage status",
    )
    matched_incidents: list[IncidentMatch] = Field(
        default_factory=list,
        description="Historical incidents ranked by relevance",
    )
    runbook_suggestions: list[RunbookSuggestion] = Field(
        default_factory=list,
        description="Suggested runbooks",
    )
    likely_owner: Optional[OwnerSuggestion] = Field(
        default=None,
        description="Most likely incident owner",
    )
    change_correlations: list[ChangeCorrelation] = Field(
        default_factory=list,
        description="Correlated recent changes",
    )
    ai_summary: str = Field(
        default="",
        description="AI-generated triage narrative",
    )
    triage_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the triage was performed",
    )


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str
    ai_backend: str
    ai_available: bool
    services_loaded: int = 0
    incidents_loaded: int = 0
    runbooks_loaded: int = 0
