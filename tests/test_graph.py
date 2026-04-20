from app.graph import get_knowledge_graph

def test_knowledge_graph_loads_data():
    graph = get_knowledge_graph()
    
    services = graph.get_all_services()
    assert len(services) > 0
    
    incidents = graph.get_all_incidents()
    assert len(incidents) > 0
    
    runbooks = graph.get_all_runbooks()
    assert len(runbooks) > 0
    
    changes = graph.get_all_changes()
    assert len(changes) > 0

def test_graph_traversal():
    graph = get_knowledge_graph()
    
    deps = graph.get_service_dependencies("order-service")
    dep_ids = [d.id for d in deps]
    assert "payment-service" in dep_ids
    assert "inventory-service" in dep_ids
    
    dependents = graph.get_service_dependents("database-primary")
    dep_ids = [d.id for d in dependents]
    assert "payment-service" in dep_ids
    assert "order-service" in dep_ids
