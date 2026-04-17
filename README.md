# 🛡️ Incident Airlock Graph
**AI-Powered Incident Memory & Evidence-Backed Triage Assistant.**

### 🔍 Overview
In high-velocity engineering environments, incident response often suffers from "Organizational Memory Loss." Teams solve the same problems repeatedly because historical knowledge is trapped in legacy tickets or transient Slack threads. 

**Incident Airlock Graph** acts as a retrieval-driven triage layer. It captures operational knowledge and matches incoming real-time alerts against a "Knowledge Base" of historical incidents, service dependencies, and proven remediation paths.

### 💡 Key Features
- **Retrieval-Augmented Triage:** Automatically matches current error patterns with historical incident records.
- **Evidence-Backed Summaries:** Uses a local LLM (Llama 3) to generate concise triage instructions based on past evidence.
- **Ownership Mapping:** Identifies likely service owners and team metadata instantly to reduce paging delays.
- **Operational Memory:** Centralizes "Proven Remediation Paths" to ensure consistency in incident response.

### 🛠️ Technical Stack
- **AI Engine:** Llama 3 (via Ollama) for reasoning and summarization.
- **Data Layer:** Structured JSON Knowledge Base (Modeled as an Operational Graph).
- **Interface:** Streamlit for a real-time, high-pressure "War Room" dashboard.
- **Language:** Python 3.x.

### 🚀 Getting Started

1. **Prerequisites:**
   - Ensure [Ollama](https://ollama.ai/) is installed and the `llama3` model is pulled:
     ```bash
     ollama pull llama3
     ```

2. **Installation:**
   ```bash
   git clone [https://github.com/your-username/incident-airlock-graph.git](https://github.com/your-username/incident-airlock-graph.git)
   cd incident-airlock-graph
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt