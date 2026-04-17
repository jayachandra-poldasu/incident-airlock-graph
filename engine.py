import json
import requests

def get_historical_evidence(current_alert):
    """Matches the current alert with the knowledge base."""
    with open('knowledge_base.json', 'r') as f:
        history = json.load(f)
    
    # Keyword-driven retrieval (RAG-lite)
    for entry in history:
        if entry['pattern'].lower() in current_alert.lower():
            return entry
    return None

def analyze_incident(alert, history=None):
    """Uses AI to summarize triage steps based on evidence."""
    context = f"History: {history}" if history else "No historical match found."
    
    prompt = f"""
    SRE TRIAGE ASSISTANT
    Context: {context}
    Current Incident: {alert}

    TASK: Provide an 'Evidence-Backed Triage Summary'.
    - If history exists, highlight the PROVEN REMEDIATION.
    - Identify the LIKELY OWNER based on metadata.
    - Format as clear bullet points for a fast-paced War Room.
    """
    
    try:
        response = requests.post("http://localhost:11434/api/generate", 
                                 json={"model": "llama3", "prompt": prompt, "stream": False})
        return response.json().get("response")
    except:
        return "AI Analysis Offline. Refer to historical record manually."