from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import traceback
import pandas as pd

from .agent_loader import AgentSpec, load_agents
from .data_fetcher import fetch_stock_data
from .llm_clients import BaseLLMClient, NoLLMClient, LLMError
from .report_templates import build_fallback, recommendation


PIPELINE_STAGE1 = ["company-overview-agent", "industry-analysis-agent", "momentum-analysis-agent"]
PIPELINE_STAGE2 = ["financial-analysis-agent"]
PIPELINE_STAGE3 = ["risk-analysis-agent"]
PIPELINE_STAGE4 = ["recommendation-agent"]


@dataclass
class AgentRunResult:
    agent_name: str
    output: str
    used_llm: bool
    error: str | None = None


@dataclass
class StockAnalysisResult:
    ticker: str
    input_ticker: str
    company_name: str
    report: str
    agent_outputs: Dict[str, AgentRunResult]
    data_context: Dict[str, Any]
    history: pd.DataFrame
    warnings: List[str] = field(default_factory=list)


class StockAnalysisOrchestrator:
    def __init__(self, agent_dir: str | Path = "agents", llm_client: BaseLLMClient | None = None, parallel: bool = True):
        self.agent_dir = Path(agent_dir)
        self.agents = load_agents(self.agent_dir)
        self.llm_client = llm_client or NoLLMClient()
        self.parallel = parallel

    def _build_user_prompt(self, agent: AgentSpec, data_json: str, previous_outputs: Dict[str, str]) -> str:
        prev = "\n\n".join([f"# Previous output: {k}\n{v}" for k, v in previous_outputs.items()])
        return f"""다음 주식 데이터와 이전 에이전트 결과를 바탕으로, 당신의 역할에 맞는 섹션만 작성하세요.

규칙:
- 한국어로 작성하세요.
- 확인되지 않은 수치는 만들지 말고 `데이터 확인 필요`라고 표시하세요.
- 표를 적극적으로 사용하세요.
- 투자 권유가 아닌 정보 정리임을 유지하세요.

# Stock data JSON
```json
{data_json}
```

# Prior agent outputs
{prev if prev else '이전 에이전트 결과 없음'}
"""

    def run_agent(self, agent_name: str, data_context: Dict[str, Any], previous_outputs: Dict[str, str]) -> AgentRunResult:
        data_json = json.dumps(data_context, ensure_ascii=False, indent=2)
        if len(data_json) > 14000:
            data_json = data_json[:14000] + "\n...TRUNCATED..."
        agent = self.agents.get(agent_name)
        if not agent:
            return AgentRunResult(agent_name, f"## {agent_name}\n\n에이전트 파일을 찾을 수 없습니다.", False, "missing agent")
        user_prompt = self._build_user_prompt(agent, data_json, previous_outputs)
        try:
            output = self.llm_client.generate(agent.prompt, user_prompt, model_hint=agent.model, temperature=0.15, max_tokens=2600)
            if not output.strip():
                raise LLMError("empty LLM output")
            return AgentRunResult(agent_name, output.strip(), True, None)
        except Exception as exc:
            fallback = build_fallback(agent_name, data_context, previous_outputs)
            return AgentRunResult(agent_name, fallback, False, f"{type(exc).__name__}: {exc}")

    def analyze_one(self, ticker: str, market: str = "AUTO", period: str = "1y") -> StockAnalysisResult:
        package, history = fetch_stock_data(ticker, market=market, period=period)
        context = package.to_context_dict()
        info = context.get("info", {}) or {}
        company_name = info.get("longName") or info.get("shortName") or package.ticker
        outputs: Dict[str, AgentRunResult] = {}
        previous: Dict[str, str] = {}

        # Stage 1: parallel or sequential
        if self.parallel and len(PIPELINE_STAGE1) > 1:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(self.run_agent, name, context, previous): name for name in PIPELINE_STAGE1}
                for fut in as_completed(futures):
                    result = fut.result()
                    outputs[result.agent_name] = result
            for name in PIPELINE_STAGE1:
                previous[name] = outputs[name].output
        else:
            for name in PIPELINE_STAGE1:
                result = self.run_agent(name, context, previous)
                outputs[name] = result
                previous[name] = result.output

        for stage in [PIPELINE_STAGE2, PIPELINE_STAGE3, PIPELINE_STAGE4]:
            for name in stage:
                result = self.run_agent(name, context, previous)
                outputs[name] = result
                previous[name] = result.output

        report = self.compose_report(package.ticker, company_name, context, outputs)
        return StockAnalysisResult(
            ticker=package.ticker,
            input_ticker=ticker,
            company_name=company_name,
            report=report,
            agent_outputs=outputs,
            data_context=context,
            history=history,
            warnings=package.warnings,
        )

    def compose_report(self, ticker: str, company_name: str, context: Dict[str, Any], outputs: Dict[str, AgentRunResult]) -> str:
        info = context.get("info", {}) or {}
        tech = context.get("technical", {}) or {}
        current = tech.get("current_price") or info.get("currentPrice") or info.get("regularMarketPrice")
        currency = info.get("currency", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        provider = getattr(self.llm_client, "provider_name", "unknown")
        error_notes = []
        for name, result in outputs.items():
            if result.error:
                error_notes.append(f"- {name}: LLM 미사용/오류 → 규칙 기반 템플릿 사용 ({result.error})")
        sections = []
        for name in [
            "company-overview-agent",
            "financial-analysis-agent",
            "industry-analysis-agent",
            "momentum-analysis-agent",
            "risk-analysis-agent",
            "recommendation-agent",
        ]:
            if name in outputs:
                sections.append(outputs[name].output)
        price_text = "데이터 확인 필요"
        if current is not None:
            try:
                price_text = f"{float(current):,.2f} {currency}".strip()
            except Exception:
                price_text = str(current)
        header = f"""# 📊 {company_name} ({ticker}) 투자 리서치 리포트

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  
**현재가:** {price_text}  
**리포트 작성일:** {now}  
**데이터 기간:** {context.get('period')}  
**LLM Provider:** {provider}  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        if context.get("warnings"):
            header += "## 데이터 수집 경고\n" + "\n".join([f"- {w}" for w in context.get("warnings", [])]) + "\n\n"
        if error_notes:
            header += "## 실행 참고사항\n" + "\n".join(error_notes) + "\n\n"
        footer = "\n\n---\n⚠️ 본 리포트는 AI 기반 정보 정리이며 투자 권유가 아닙니다. 실제 투자 결정은 공인 금융투자전문가와 상담 후 본인 책임 하에 진행하시기 바랍니다. 과거 수익률이 미래 수익률을 보장하지 않습니다.\n"
        return header + "\n\n".join(sections) + footer

    def analyze_many(self, tickers: List[str], market: str = "AUTO", period: str = "1y") -> List[StockAnalysisResult]:
        results = []
        for ticker in tickers:
            results.append(self.analyze_one(ticker, market=market, period=period))
        return results


def compare_summary(results: List[StockAnalysisResult]) -> str:
    rows = ["| 종목 | 티커 | 현재가 | 추세 | PER | PBR | ROE | 의견 참고 |", "|---|---|---:|---|---:|---:|---:|---|"]
    for r in results:
        info = r.data_context.get("info", {}) or {}
        tech = r.data_context.get("technical", {}) or {}
        current = tech.get("current_price") or info.get("currentPrice")
        currency = info.get("currency", "")
        price = "데이터 확인 필요" if current is None else f"{float(current):,.2f} {currency}".strip()
        rec = r.agent_outputs.get("recommendation-agent")
        opinion = "리포트 참조"
        if rec:
            for key in ["STRONG BUY", "BUY", "HOLD", "SELL", "AVOID"]:
                if key in rec.output:
                    opinion = key
                    break
        rows.append(f"| {r.company_name} | {r.ticker} | {price} | {tech.get('trend', 'N/A')} | {info.get('trailingPE', 'N/A')} | {info.get('priceToBook', 'N/A')} | {info.get('returnOnEquity', 'N/A')} | {opinion} |")
    return "\n".join(rows)
