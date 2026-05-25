from .agent_loader import load_agents


def test_load_agents():
    agents = load_agents("agents")
    required = [
        "stock-analyst-orchestrator",
        "company-overview-agent",
        "financial-analysis-agent",
        "industry-analysis-agent",
        "momentum-analysis-agent",
        "risk-analysis-agent",
        "recommendation-agent",
    ]
    missing = [x for x in required if x not in agents]
    assert not missing, f"Missing agents: {missing}"
