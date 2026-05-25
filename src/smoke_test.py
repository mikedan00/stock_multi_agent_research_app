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


def test_builtin_name_resolver():
    from .ticker_resolver import resolve_stock_symbol

    assert resolve_stock_symbol("삼성전자").ticker == "005930.KS"
    assert resolve_stock_symbol("엔비디아").ticker == "NVDA"
