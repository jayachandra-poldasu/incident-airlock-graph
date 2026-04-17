import streamlit as st
from engine import get_historical_evidence, analyze_incident

st.set_page_config(page_title="Incident Airlock", page_icon="🛡️")

st.title("🛡️ Incident Airlock Graph")
st.markdown("**AI-Powered Incident Memory & Evidence-Backed Triage**")
st.markdown("---")

# Input Section
alert_input = st.text_area("Paste Incoming Alert/Log:", placeholder="e.g. ERROR | Auth-Service | OutOfMemory in session_v1")

if st.button("🚀 Start Triage Analysis"):
    with st.spinner("Retrieving historical context..."):
        # 1. Match Evidence
        evidence = get_historical_evidence(alert_input)
        
        # 2. Generate Summary
        summary = analyze_incident(alert_input, evidence)
        
        # 3. UI Layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 AI Triage Summary")
            st.write(summary)
            
        with col2:
            st.subheader("📚 Historical Evidence")
            if evidence:
                st.success(f"Match Found: {evidence['id']}")
                st.json(evidence)
            else:
                st.warning("No historical match found. Performing Zero-Shot analysis.")

        # Metadata Footer
        st.markdown("---")
        if evidence:
            st.info(f"**Metadata Ownership:** Team: {evidence['team']} | Service: {evidence['service']}")