"""
Matching Engine — Core logic for retrieval-driven triage analysis.

Finds relevant historical incidents, runbooks, and change correlations for a new alert
using a combination of exact matching, text similarity, and graph traversal.
"""

import re
from datetime import datetime, timezone
from typing import List

from app.config import get_settings
from app.graph import get_knowledge_graph
from app.models import (
    AlertRequest,
    ChangeCorrelation,
    IncidentMatch,
    OwnerSuggestion,
    RunbookSuggestion,
)


def extract_keywords(text: str) -> set[str]:
    """Extract simple lowercase keywords from text, ignoring common stop words."""
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "is", "are", "was", "were", "of"}
    words = re.findall(r'\b[a-zA-Z0-9_]{3,}\b', text.lower())
    return {w for w in words if w not in stop_words}


def compute_text_similarity(text1: str, text2: str) -> float:
    """Compute simple Jaccard similarity between two texts."""
    set1 = extract_keywords(text1)
    set2 = extract_keywords(text2)
    
    if not set1 or not set2:
        return 0.0
        
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union


def match_incidents(alert: AlertRequest) -> List[IncidentMatch]:
    """
    Find relevant historical incidents based on the incoming alert.
    Uses service matching, category matching, and text similarity.
    """
    graph = get_knowledge_graph()
    settings = get_settings()
    
    matches = []
    
    # 1. Direct service incidents
    for incident in graph.get_incidents_for_service(alert.service_id):
        score_breakdown = {}
        reasons = []
        
        # Base score for being the same service
        service_score = 0.5
        score_breakdown["service_match"] = service_score
        reasons.append("Affects the same service")
        
        # Category match
        category_score = 0.0
        if alert.category and incident.category == alert.category:
            category_score = 0.2
            score_breakdown["category_match"] = category_score
            reasons.append(f"Matches category: {alert.category.value}")
            
        # Text similarity score
        text_sim = compute_text_similarity(alert.error_message, incident.title + " " + incident.description)
        text_score = text_sim * 0.3
        score_breakdown["text_similarity"] = text_score
        if text_score > 0.1:
            reasons.append("High text similarity in error message")
            
        total_score = service_score + category_score + text_score
        
        if total_score >= settings.min_relevance_score:
            matches.append(
                IncidentMatch(
                    incident=incident,
                    relevance_score=total_score,
                    match_reasons=reasons,
                    score_breakdown=score_breakdown
                )
            )
            
    # 2. Dependency incidents (graph traversal)
    target_service = graph.get_service(alert.service_id)
    if target_service:
        for dep_id in target_service.dependencies:
            for incident in graph.get_incidents_for_service(dep_id):
                score_breakdown = {}
                reasons = []
                
                # Base score for being a dependency
                dep_score = 0.3
                score_breakdown["dependency_match"] = dep_score
                reasons.append(f"Incident on dependency: {dep_id}")
                
                # Category match
                category_score = 0.0
                if alert.category and incident.category == alert.category:
                    category_score = 0.1
                    score_breakdown["category_match"] = category_score
                    
                # Text similarity
                text_sim = compute_text_similarity(alert.error_message, incident.title + " " + incident.description)
                text_score = text_sim * 0.2
                score_breakdown["text_similarity"] = text_score
                
                total_score = dep_score + category_score + text_score
                
                if total_score >= settings.min_relevance_score:
                    matches.append(
                        IncidentMatch(
                            incident=incident,
                            relevance_score=total_score,
                            match_reasons=reasons,
                            score_breakdown=score_breakdown
                        )
                    )
                    
    # Sort by relevance and take top N
    matches.sort(key=lambda x: x.relevance_score, reverse=True)
    return matches[:settings.max_match_results]


def suggest_runbooks(alert: AlertRequest, matched_incidents: List[IncidentMatch]) -> List[RunbookSuggestion]:
    """Suggest runbooks based on service, category, and historical incident usage."""
    graph = get_knowledge_graph()
    
    suggestions_map = {}
    
    # 1. Look at runbooks from matched incidents
    for match in matched_incidents:
        if match.incident.runbook_id:
            rb_id = match.incident.runbook_id
            if rb_id not in suggestions_map:
                rb = graph.get_runbook(rb_id)
                if rb:
                    suggestions_map[rb_id] = RunbookSuggestion(
                        runbook=rb,
                        relevance_score=match.relevance_score * 0.9, # Slightly lower than the incident score
                        match_reasons=[f"Successfully resolved similar incident: {match.incident.id}"]
                    )
    
    # 2. Look for runbooks directly mapped to the service and category
    for rb in graph.get_all_runbooks():
        if rb.id in suggestions_map:
            continue
            
        score = 0.0
        reasons = []
        
        if alert.service_id in rb.service_ids:
            score += 0.6
            reasons.append("Directly mapped to affected service")
            
        if alert.category and alert.category.value in rb.categories:
            score += 0.3
            reasons.append(f"Mapped to alert category: {alert.category.value}")
            
        # Add a small boost for high historical success rate
        score += (rb.success_rate * 0.1)
        
        if score > 0.4:
            suggestions_map[rb.id] = RunbookSuggestion(
                runbook=rb,
                relevance_score=score,
                match_reasons=reasons
            )
            
    suggestions = list(suggestions_map.values())
    suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
    return suggestions[:5]


def identify_owner(alert: AlertRequest, matched_incidents: List[IncidentMatch]) -> OwnerSuggestion:
    """Identify the likely owner/resolver based on service ownership and historical resolution patterns."""
    graph = get_knowledge_graph()
    
    service = graph.get_service(alert.service_id)
    if not service:
        return OwnerSuggestion(
            recommended_owner="Unknown",
            evidence=["Service not found in knowledge graph."]
        )
        
    # Gather candidate scores
    candidates = {}
    
    # 1. Base ownership
    if service.owner:
        candidates[service.owner] = {"score": 5.0, "evidence": ["Primary service owner"]}
        
    if service.on_call:
        if service.on_call in candidates:
            candidates[service.on_call]["score"] += 3.0
            candidates[service.on_call]["evidence"].append("Currently on-call")
        else:
            candidates[service.on_call] = {"score": 4.0, "evidence": ["Currently on-call"]}
            
    # 2. Historical resolvers from matched incidents
    for match in matched_incidents:
        resolver = match.incident.resolved_by
        if resolver:
            if resolver in candidates:
                candidates[resolver]["score"] += (match.relevance_score * 2.0)
                candidates[resolver]["evidence"].append(f"Resolved similar incident {match.incident.id}")
            else:
                candidates[resolver] = {
                    "score": match.relevance_score * 2.0,
                    "evidence": [f"Resolved similar incident {match.incident.id}"]
                }
                
    # Pick the top candidate
    if not candidates:
        return OwnerSuggestion(
            recommended_owner="Unknown",
            team=service.team,
            escalation_path=service.escalation_path
        )
        
    best_candidate = max(candidates.items(), key=lambda x: x[1]["score"])
    
    # Normalize confidence to 0-1 (roughly)
    confidence = min(best_candidate[1]["score"] / 10.0, 1.0)
    
    return OwnerSuggestion(
        recommended_owner=best_candidate[0],
        team=service.team,
        confidence=confidence,
        evidence=best_candidate[1]["evidence"],
        on_call=service.on_call,
        escalation_path=service.escalation_path
    )


def parse_iso_time(time_str: str) -> datetime:
    """Parse ISO 8601 string to aware datetime."""
    try:
        # Handle 'Z' suffix
        if time_str.endswith('Z'):
            time_str = time_str[:-1] + '+00:00'
        return datetime.fromisoformat(time_str)
    except ValueError:
        return datetime.now(timezone.utc)


def find_change_correlations(alert: AlertRequest) -> List[ChangeCorrelation]:
    """Find recent changes that might have caused the alert."""
    graph = get_knowledge_graph()
    settings = get_settings()
    
    alert_time = parse_iso_time(alert.timestamp)
    window_hours = settings.change_correlation_window_hours
    
    correlations = []
    
    # Target service and its dependencies
    relevant_services = {alert.service_id: True} # True = direct
    target_service = graph.get_service(alert.service_id)
    if target_service:
        for dep_id in target_service.dependencies:
            relevant_services[dep_id] = False # False = dependency
            
    for change in graph.get_all_changes():
        if change.service_id not in relevant_services:
            continue
            
        change_time = parse_iso_time(change.timestamp)
        
        # Calculate time delta in minutes
        delta = alert_time - change_time
        delta_minutes = delta.total_seconds() / 60.0
        
        # Check if within window (and not in the future)
        if 0 <= delta_minutes <= (window_hours * 60):
            is_direct = relevant_services[change.service_id]
            
            # Score based on recency and directness
            recency_factor = 1.0 - (delta_minutes / (window_hours * 60))
            directness_factor = 1.0 if is_direct else 0.6
            
            score = recency_factor * directness_factor
            
            evidence = []
            if is_direct:
                evidence.append(f"Direct change on affected service {int(delta_minutes)}m before alert")
            else:
                evidence.append(f"Change on dependency {change.service_id} {int(delta_minutes)}m before alert")
                
            correlations.append(
                ChangeCorrelation(
                    change=change,
                    correlation_score=score,
                    time_delta_minutes=delta_minutes,
                    evidence=evidence,
                    is_direct_dependency=is_direct
                )
            )
            
    correlations.sort(key=lambda x: x.correlation_score, reverse=True)
    return correlations
