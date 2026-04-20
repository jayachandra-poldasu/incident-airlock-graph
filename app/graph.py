"""
Knowledge Graph Loader — loads and indexes the static JSON datasets.

Simulates a knowledge graph by building in-memory dictionaries and relationship
maps between services, incidents, runbooks, and changes.
"""

import json
import logging
import os
from typing import Dict, List, Optional

from app.config import get_settings
from app.models import ChangeRecord, IncidentRecord, RunbookEntry, ServiceInfo

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """In-memory knowledge graph of operational data."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.services: Dict[str, ServiceInfo] = {}
        self.incidents: Dict[str, IncidentRecord] = {}
        self.runbooks: Dict[str, RunbookEntry] = {}
        self.changes: Dict[str, ChangeRecord] = {}
        self._load_data()

    def _load_data(self):
        """Load all JSON files into memory."""
        try:
            # Create data dir if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Load Services
            services_path = os.path.join(self.data_dir, "services.json")
            if os.path.exists(services_path):
                with open(services_path, "r") as f:
                    data = json.load(f)
                    self.services = {item["id"]: ServiceInfo(**item) for item in data}
            
            # Load Incidents
            incidents_path = os.path.join(self.data_dir, "incidents.json")
            if os.path.exists(incidents_path):
                with open(incidents_path, "r") as f:
                    data = json.load(f)
                    self.incidents = {item["id"]: IncidentRecord(**item) for item in data}
                    
            # Load Runbooks
            runbooks_path = os.path.join(self.data_dir, "runbooks.json")
            if os.path.exists(runbooks_path):
                with open(runbooks_path, "r") as f:
                    data = json.load(f)
                    self.runbooks = {item["id"]: RunbookEntry(**item) for item in data}
                    
            # Load Changes
            changes_path = os.path.join(self.data_dir, "changes.json")
            if os.path.exists(changes_path):
                with open(changes_path, "r") as f:
                    data = json.load(f)
                    self.changes = {item["id"]: ChangeRecord(**item) for item in data}
                    
            logger.info(
                f"Knowledge Graph loaded: {len(self.services)} services, "
                f"{len(self.incidents)} incidents, {len(self.runbooks)} runbooks, "
                f"{len(self.changes)} changes."
            )
        except Exception as e:
            logger.error(f"Failed to load knowledge graph data: {e}")

    # --- Accessors ---

    def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        return self.services.get(service_id)

    def get_all_services(self) -> List[ServiceInfo]:
        return list(self.services.values())

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        return self.incidents.get(incident_id)

    def get_all_incidents(self) -> List[IncidentRecord]:
        return list(self.incidents.values())

    def get_runbook(self, runbook_id: str) -> Optional[RunbookEntry]:
        return self.runbooks.get(runbook_id)

    def get_all_runbooks(self) -> List[RunbookEntry]:
        return list(self.runbooks.values())

    def get_change(self, change_id: str) -> Optional[ChangeRecord]:
        return self.changes.get(change_id)

    def get_all_changes(self) -> List[ChangeRecord]:
        return list(self.changes.values())

    # --- Graph Traversal ---

    def get_service_dependencies(self, service_id: str) -> List[ServiceInfo]:
        """Get all services that the given service depends on."""
        service = self.get_service(service_id)
        if not service:
            return []
        return [self.services[dep_id] for dep_id in service.dependencies if dep_id in self.services]

    def get_service_dependents(self, service_id: str) -> List[ServiceInfo]:
        """Get all services that depend on the given service."""
        service = self.get_service(service_id)
        if not service:
            return []
        return [self.services[dep_id] for dep_id in service.dependents if dep_id in self.services]

    def get_incidents_for_service(self, service_id: str) -> List[IncidentRecord]:
        """Get all historical incidents for a given service."""
        return [inc for inc in self.incidents.values() if inc.service_id == service_id]


# Singleton instance
_graph_instance: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    """Get or create the singleton KnowledgeGraph instance."""
    global _graph_instance
    if _graph_instance is None:
        settings = get_settings()
        _graph_instance = KnowledgeGraph(settings.data_dir)
    return _graph_instance
