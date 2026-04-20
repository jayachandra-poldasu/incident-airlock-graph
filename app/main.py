"""
FastAPI application — Incident Airlock Graph API.

Provides endpoints for alert triage, incident retrieval, and graph exploration.
"""

import uuid
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app import __app_name__, __version__
from app.ai import check_ai_health, generate_triage_summary
from app.config import get_settings
from app.engine import find_change_correlations, identify_owner, match_incidents, suggest_runbooks
from app.graph import get_knowledge_graph
from app.models import (
    AlertRequest,
    ChangeRecord,
    HealthResponse,
    IncidentRecord,
    RunbookEntry,
    ServiceInfo,
    TriageResult,
    TriageStatus,
)


settings = get_settings()

app = FastAPI(
    title=__app_name__,
    version=__version__,
    description=(
        "Retrieval-driven incident analysis system. Matches current alerts with "
        "historical incidents, runbooks, ownership, and change context."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize the graph on startup to fail fast if data is missing."""
    get_knowledge_graph()


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Health check endpoint with AI backend status and graph stats."""
    graph = get_knowledge_graph()
    return HealthResponse(
        status="healthy",
        version=__version__,
        ai_backend=settings.ai_backend.value,
        ai_available=check_ai_health(settings),
        services_loaded=len(graph.get_all_services()),
        incidents_loaded=len(graph.get_all_incidents()),
        runbooks_loaded=len(graph.get_all_runbooks()),
    )


# ── Triage ───────────────────────────────────────────────────────────────────

@app.post("/triage", response_model=TriageResult, tags=["Triage"])
def perform_triage(request: AlertRequest):
    """
    Perform a complete triage analysis on a new alert.
    
    This endpoint:
    1. Matches historical incidents
    2. Suggests runbooks
    3. Identifies the likely owner
    4. Finds correlated recent changes
    5. Generates an AI narrative summary
    """
    triage_id = str(uuid.uuid4())[:8]
    
    # 1. Match incidents
    matched_incidents = match_incidents(request)
    
    # 2. Suggest runbooks based on alert and matches
    runbooks = suggest_runbooks(request, matched_incidents)
    
    # 3. Identify owner
    owner = identify_owner(request, matched_incidents)
    
    # 4. Find changes
    changes = find_change_correlations(request)
    
    result = TriageResult(
        triage_id=triage_id,
        alert=request,
        status=TriageStatus.ANALYZING,
        matched_incidents=matched_incidents,
        runbook_suggestions=runbooks,
        likely_owner=owner,
        change_correlations=changes,
    )
    
    # 5. Generate summary
    summary = generate_triage_summary(result)
    result.ai_summary = summary
    result.status = TriageStatus.COMPLETE
    
    return result


# ── Graph Data Access Endpoints ──────────────────────────────────────────────

@app.get("/services", response_model=List[ServiceInfo], tags=["Graph"])
def list_services():
    """List all services in the dependency graph."""
    graph = get_knowledge_graph()
    return graph.get_all_services()


@app.get("/incidents", response_model=List[IncidentRecord], tags=["Graph"])
def list_incidents(service_id: str = Query(None, description="Filter by service ID")):
    """List historical incidents, optionally filtered by service."""
    graph = get_knowledge_graph()
    if service_id:
        return graph.get_incidents_for_service(service_id)
    return graph.get_all_incidents()


@app.get("/incidents/{incident_id}", response_model=IncidentRecord, tags=["Graph"])
def get_incident(incident_id: str):
    """Get a single historical incident by ID."""
    graph = get_knowledge_graph()
    incident = graph.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/runbooks", response_model=List[RunbookEntry], tags=["Graph"])
def list_runbooks(service_id: str = Query(None, description="Filter by service ID")):
    """List all runbooks, optionally filtered by applicable service."""
    graph = get_knowledge_graph()
    runbooks = graph.get_all_runbooks()
    
    if service_id:
        return [rb for rb in runbooks if service_id in rb.service_ids]
    return runbooks


@app.get("/changes", response_model=List[ChangeRecord], tags=["Graph"])
def list_changes(service_id: str = Query(None, description="Filter by service ID")):
    """List all recent changes, optionally filtered by service."""
    graph = get_knowledge_graph()
    changes = graph.get_all_changes()
    
    if service_id:
        return [c for c in changes if c.service_id == service_id]
    return changes
