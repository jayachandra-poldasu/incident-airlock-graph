import os
import streamlit as st
import requests
import json
from datetime import datetime

# --- Configuration ---
API_URL = os.getenv("AIRLOCK_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Incident Airlock",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 4px solid #4CAF50;
    }
    .metric-card.critical { border-left-color: #F44336; }
    .metric-card.high { border-left-color: #FF9800; }
    .metric-card.medium { border-left-color: #FFEB3B; }
    
    .match-reason {
        display: inline-block;
        background-color: #2D3748;
        color: #E2E8F0;
        border-radius: 4px;
        padding: 2px 8px;
        margin: 2px;
        font-size: 0.8em;
    }
    .confidence-bar {
        height: 6px;
        border-radius: 3px;
        background-color: #333;
        margin-top: 5px;
    }
    .confidence-fill {
        height: 100%;
        border-radius: 3px;
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# --- State ---
if 'triage_result' not in st.session_state:
    st.session_state.triage_result = None

# --- Helpers ---
def fetch_services():
    try:
        response = requests.get(f"{API_URL}/services")
        if response.status_code == 200:
            return response.json()
    except Exception:
        return []
    return []

# --- Sidebar ---
with st.sidebar:
    st.title("🛡️ Incident Airlock")
    st.caption("Retrieval-driven Incident Analysis")
    
    st.markdown("### Demo Scenarios")
    
    if st.button("🔥 Simulate Payment Timeout", use_container_width=True):
        st.session_state.demo_alert = {
            "service_id": "payment-service",
            "error_message": "Payment gateway requests taking > 5s, multiple 504 Gateway Timeouts.",
            "severity": "high",
            "category": "latency"
        }
        
    if st.button("💾 Simulate DB CPU Spike", use_container_width=True):
        st.session_state.demo_alert = {
            "service_id": "database-primary",
            "error_message": "CPU utilization reached 98%. Active connections queueing.",
            "severity": "critical",
            "category": "capacity"
        }
        
    if st.button("💸 Simulate Order Errors", use_container_width=True):
        st.session_state.demo_alert = {
            "service_id": "order-service",
            "error_message": "Checkout failing with 500 Internal Server Error. Inventory sync suspected.",
            "severity": "critical",
            "category": "error_rate"
        }
        
    st.markdown("---")
    st.markdown("### System Health")
    try:
        health = requests.get(f"{API_URL}/health").json()
        st.success(f"API Connected (v{health['version']})")
        st.info(f"AI Backend: {health['ai_backend']}")
        st.caption(f"Graph: {health['services_loaded']} svcs | {health['incidents_loaded']} inc | {health['runbooks_loaded']} rbks")
    except Exception:
        st.error("API Disconnected")

# --- Main Content ---
st.title("Alert Triage")

services = fetch_services()
service_ids = [s["id"] for s in services] if services else ["payment-service", "order-service", "database-primary"]

# Initialize form values from demo if clicked
default_svc = "payment-service"
default_err = ""
default_sev = "high"
default_cat = "latency"

if hasattr(st.session_state, 'demo_alert'):
    default_svc = st.session_state.demo_alert["service_id"]
    default_err = st.session_state.demo_alert["error_message"]
    default_sev = st.session_state.demo_alert["severity"]
    default_cat = st.session_state.demo_alert["category"]

with st.form("alert_form"):
    st.subheader("Submit New Alert")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        service_id = st.selectbox("Affected Service", options=service_ids, index=service_ids.index(default_svc) if default_svc in service_ids else 0)
    
    with col2:
        severity = st.selectbox("Severity", options=["critical", "high", "medium", "low"], index=["critical", "high", "medium", "low"].index(default_sev))
        
    with col3:
        category = st.selectbox("Category Hint", options=["outage", "degradation", "latency", "error_rate", "capacity", "data_issue"], index=["outage", "degradation", "latency", "error_rate", "capacity", "data_issue"].index(default_cat))
        
    error_message = st.text_area("Alert / Error Message", value=default_err, height=100)
    
    submit = st.form_submit_button("Run Triage Analysis", type="primary")

if submit:
    with st.spinner("Traversing knowledge graph & generating AI summary..."):
        payload = {
            "service_id": service_id,
            "error_message": error_message,
            "severity": severity,
            "category": category
        }
        
        try:
            response = requests.post(f"{API_URL}/triage", json=payload)
            if response.status_code == 200:
                st.session_state.triage_result = response.json()
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Connection Error: {e}")

# --- Render Results ---
if st.session_state.triage_result:
    res = st.session_state.triage_result
    
    st.markdown("---")
    st.header("🧠 Triage Summary")
    
    # AI Summary Box
    st.info(res["ai_summary"])
    
    # Quick Facts Row
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if res["likely_owner"]:
            owner = res["likely_owner"]
            conf_pct = int(owner["confidence"] * 100)
            st.markdown(f"""
            <div class="metric-card">
                <small>RECOMMENDED OWNER</small>
                <h3>👨‍💻 {owner["recommended_owner"]}</h3>
                <p>Team: {owner["team"]}</p>
                <div class="confidence-bar"><div class="confidence-fill" style="width: {conf_pct}%"></div></div>
                <small>{conf_pct}% confidence</small>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Evidence"):
                for ev in owner["evidence"]:
                    st.markdown(f"- {ev}")
                if owner.get("on_call"):
                    st.markdown(f"**Current On-Call:** {owner['on_call']}")
        
    with col2:
        if res["change_correlations"]:
            top_change = res["change_correlations"][0]
            st.markdown(f"""
            <div class="metric-card">
                <small>SUSPECTED CHANGE</small>
                <h3>🔄 {top_change["change"]["change_type"]}</h3>
                <p>{top_change["change"]["service_id"]} ({int(top_change["time_delta_minutes"])}m ago)</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Change Details"):
                st.markdown(f"**Description:** {top_change['change']['description']}")
                st.markdown(f"**Author:** {top_change['change']['author']}")
                for ev in top_change["evidence"]:
                    st.markdown(f"- {ev}")
        else:
            st.markdown("""
            <div class="metric-card">
                <small>SUSPECTED CHANGE</small>
                <h3>✅ No recent changes</h3>
                <p>No correlations found within 48h</p>
            </div>
            """, unsafe_allow_html=True)
            
    with col3:
        if res["runbook_suggestions"]:
            top_rb = res["runbook_suggestions"][0]
            st.markdown(f"""
            <div class="metric-card">
                <small>TOP RUNBOOK</small>
                <h3>📖 {top_rb["runbook"]["id"]}</h3>
                <p>{top_rb["runbook"]["title"]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Steps"):
                for step in top_rb["runbook"]["steps"]:
                    st.markdown(step)
    
    # Detailed Matches
    st.markdown("### 🔍 Historical Incident Matches")
    
    if not res["matched_incidents"]:
        st.info("No highly relevant historical incidents found. This may be a novel issue.")
    
    for i, match in enumerate(res["matched_incidents"][:3]):
        inc = match["incident"]
        
        with st.container():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"#### {inc['title']} ({inc['id']})")
                st.markdown(f"**Service:** `{inc['service_id']}` | **Resolved by:** {inc['resolved_by']} | **MTTR:** {inc['mttr_minutes']}m")
                
                reasons_html = "".join([f'<span class="match-reason">{r}</span>' for r in match["match_reasons"]])
                st.markdown(reasons_html, unsafe_allow_html=True)
                
            with col_b:
                st.metric("Relevance Score", f"{match['relevance_score']:.2f}")
                
            with st.expander("Incident Post-Mortem"):
                st.markdown(f"**Issue:** {inc['description']}")
                st.markdown(f"**Root Cause:** {inc['root_cause']}")
                st.markdown(f"**Resolution:** {inc['resolution']}")
                if inc.get("runbook_id"):
                    st.markdown(f"**Runbook Used:** `{inc['runbook_id']}`")
                    
            st.markdown("---")
