"""
AI Analysis Integration — Pluggable LLM capabilities for triage narrative generation.
"""

import logging
from typing import Optional
import requests

from app.config import AIBackend, Settings, get_settings
from app.models import TriageResult

logger = logging.getLogger(__name__)


def generate_triage_summary(triage_result: TriageResult, settings: Optional[Settings] = None) -> str:
    """Generate a narrative summary of the triage analysis using the configured AI backend."""
    if settings is None:
        settings = get_settings()

    if settings.ai_backend == AIBackend.NONE:
        return _deterministic_summary(triage_result)

    prompt = _build_prompt(triage_result)

    try:
        if settings.ai_backend == AIBackend.OLLAMA:
            return _call_ollama(prompt, settings)
        elif settings.ai_backend == AIBackend.OPENAI:
            return _call_openai(prompt, settings)
    except Exception as e:
        logger.warning(f"AI backend failed ({settings.ai_backend.value}): {e}")
        return _deterministic_summary(triage_result)

    return _deterministic_summary(triage_result)


def check_ai_health(settings: Optional[Settings] = None) -> bool:
    """Check if the configured AI backend is available."""
    if settings is None:
        settings = get_settings()

    if settings.ai_backend == AIBackend.NONE:
        return True

    try:
        if settings.ai_backend == AIBackend.OLLAMA:
            base_url = settings.ollama_url.replace("/api/generate", "")
            resp = requests.get(base_url, timeout=5)
            return resp.status_code == 200
        elif settings.ai_backend == AIBackend.OPENAI:
            return bool(settings.openai_api_key)
    except Exception:
        return False

    return False


def _build_prompt(tr: TriageResult) -> str:
    """Build a prompt string containing all the structured evidence."""
    
    prompt = f"""You are an expert SRE / Incident Commander performing alert triage.
    
    Analyze the following alert and retrieved evidence to write a concise, actionable triage summary.
    Keep the summary under 150 words. Focus on:
    1. The likely root cause based on history and changes.
    2. Who needs to be paged.
    3. What they should do first (runbooks).
    
    ALERT:
    Service: {tr.alert.service_id}
    Error: {tr.alert.error_message}
    Severity: {tr.alert.severity.value}
    
    """
    
    if tr.matched_incidents:
        prompt += "\nHISTORICAL MATCHES:\n"
        for i, m in enumerate(tr.matched_incidents[:2]):
            prompt += f"- Incident {m.incident.id}: {m.incident.title} (Cause: {m.incident.root_cause})\n"
            
    if tr.change_correlations:
        prompt += "\nRECENT CHANGES:\n"
        for i, c in enumerate(tr.change_correlations[:2]):
            prompt += f"- {c.change.change_type} on {c.change.service_id} ({int(c.time_delta_minutes)}m ago): {c.change.description}\n"
            
    if tr.likely_owner:
        prompt += f"\nLIKELY OWNER: {tr.likely_owner.recommended_owner} (Team: {tr.likely_owner.team})\n"
        
    return prompt


def _call_ollama(prompt: str, settings: Settings) -> str:
    response = requests.post(
        settings.ollama_url,
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=settings.ollama_timeout,
    )
    response.raise_for_status()
    return response.json().get("response", "").strip()


def _call_openai(prompt: str, settings: Settings) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are an expert SRE Incident Commander."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        },
        timeout=settings.openai_timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _deterministic_summary(tr: TriageResult) -> str:
    """Generate a structured summary when no AI is available."""
    
    summary = f"Deterministic Triage Summary for {tr.alert.service_id}:\n\n"
    
    if tr.likely_owner:
        summary += f"👨‍💻 Escalate to: {tr.likely_owner.recommended_owner} ({tr.likely_owner.team})\n"
        
    if tr.change_correlations:
        top_change = tr.change_correlations[0]
        summary += f"🔄 Suspected Change: {top_change.change.change_type} on {top_change.change.service_id} by {top_change.change.author} ({int(top_change.time_delta_minutes)} mins ago)\n"
        
    if tr.matched_incidents:
        top_incident = tr.matched_incidents[0]
        summary += f"🔍 Related History: Similar to {top_incident.incident.id} ({top_incident.incident.title})\n"
        
    if tr.runbook_suggestions:
        top_rb = tr.runbook_suggestions[0]
        summary += f"📖 Recommended Action: Run {top_rb.runbook.title} (Success Rate: {top_rb.runbook.success_rate*100}%)\n"
        
    if not (tr.likely_owner or tr.change_correlations or tr.matched_incidents or tr.runbook_suggestions):
        summary += "No strong correlations found. Treat as a novel incident and perform standard triage."
        
    return summary
