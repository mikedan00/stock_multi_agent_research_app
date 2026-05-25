from __future__ import annotations

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.llm_clients import build_llm_client
from src.orchestrator import StockAnalysisOrchestrator, compare_summary
from src.agent_loader import load_agents, agent_inventory_markdown

load_dotenv()

st.set_page_config(page_title="주식 멀티 에이전트 리서치", page_icon="📊", layout="wide")

st.title("📊 주식 멀티 에이전트 리서치 앱")
st.caption("Claude Code subagent 문서 구조를 로컬 VS Code/Streamlit에서 실행하는 멀티 에이전트 분석 앱")

HF_MODEL_DEFAULT = os.getenv("HF_MODEL", "google/gemma-4-26B-A4B-it")
HF_BASE_URL_DEFAULT = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1")

with st.sidebar:
    st.header("실행 설정")
    provider = st.selectbox(
        "LLM Provider",
        ["none", "huggingface", "anthropic", "openai-compatible"],
        index=0,
        help="none은 API 없이 규칙 기반 템플릿으로 실행합니다.",
    )

    model = ""
    base_url = ""
    api_key = ""
    hf_provider = "auto"

    if provider == "huggingface":
        st.subheader("Hugging Face 설정")
        hf_model_mode = st.selectbox(
            "HF 모델 선택",
            [
                "google/gemma-4-26B-A4B-it",
                "google/gemma-4-26B-A4B-it:novita",
                "google/gemma-4-26B-A4B-it:deepinfra",
                "직접 입력",
            ],
            index=0,
            help="provider suffix(:novita 등)를 붙이면 HF Router가 해당 provider로 라우팅합니다.",
        )
        if hf_model_mode == "직접 입력":
            model = st.text_input("HF Model ID", value=HF_MODEL_DEFAULT, key="hf_model_custom")
        else:
            model = hf_model_mode

        hf_provider = st.selectbox(
            "HF Inference Provider",
            ["auto", "novita", "deepinfra", "nebius", "together", "hf-inference", "groq", "fireworks-ai", "cerebras"],
            index=0,
            help="모델 ID에 이미 :novita 같은 suffix가 있으면 이 값은 추가로 붙지 않습니다. auto는 HF 설정에 따라 자동 라우팅합니다.",
        )
        base_url = st.text_input("HF Router Base URL", value=HF_BASE_URL_DEFAULT)
        api_key = st.text_input("HF_TOKEN", value="", type="password", help="입력하지 않으면 .env 또는 환경변수 HF_TOKEN을 사용합니다.")

    elif provider == "anthropic":
        st.subheader("Anthropic 설정")
        model = st.text_input("Anthropic Model", value=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
        base_url = st.text_input("Anthropic Messages URL", value=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages"))
        api_key = st.text_input("ANTHROPIC_API_KEY", value="", type="password", help="입력하지 않으면 .env 또는 환경변수를 사용합니다.")

    elif provider == "openai-compatible":
        st.subheader("OpenAI-compatible 설정")
        preset = st.selectbox(
            "Base URL 프리셋",
            ["OpenAI", "OpenRouter", "DeepInfra", "Novita", "직접 입력"],
            index=0,
        )
        preset_urls = {
            "OpenAI": "https://api.openai.com/v1",
            "OpenRouter": "https://openrouter.ai/api/v1",
            "DeepInfra": "https://api.deepinfra.com/v1/openai",
            "Novita": "https://api.novita.ai/v3/openai",
        }
        if preset == "직접 입력":
            base_url = st.text_input("Base URL", value=os.getenv("OPENAI_COMPATIBLE_BASE_URL", "https://api.openai.com/v1"))
        else:
            base_url = st.text_input("Base URL", value=os.getenv("OPENAI_COMPATIBLE_BASE_URL", preset_urls[preset]))
        model = st.text_input("Model", value=os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4.1-mini"))
        api_key = st.text_input("API Key", value="", type="password", help="입력하지 않으면 .env 또는 환경변수를 사용합니다.")

    else:
        st.info("LLM 없이 yfinance 데이터 + 규칙 기반 fallback 템플릿으로 실행합니다.")

    if provider != "none":
        test_col1, test_col2 = st.columns([1, 1])
        with test_col1:
            test_llm = st.button("🔌 연결 테스트", use_container_width=True)
        with test_col2:
            st.caption("소량 토큰 사용")
        if test_llm:
            try:
                test_client = build_llm_client(
                    provider=provider,
                    api_key=api_key or None,
                    base_url=base_url or None,
                    model=model or None,
                    hf_provider=hf_provider,
                )
                msg = test_client.generate(
                    "You are a concise connection tester. Reply in Korean.",
                    "주식 분석 멀티 에이전트 앱의 LLM 연결이 정상인지 한 문장으로 답하세요.",
                    temperature=0,
                    max_tokens=80,
                )
                st.success(msg or "연결 성공")
            except Exception as exc:
                st.error(f"연결 실패: {exc}")

    market = st.selectbox("한국 6자리 코드 기본 시장", ["AUTO", "KOSPI", "KOSDAQ"], index=0)
    period = st.selectbox("가격 데이터 기간", ["6mo", "1y", "2y", "5y", "max"], index=1)
    parallel = st.checkbox("1단계 에이전트 병렬 실행", value=True)

    st.divider()
    st.subheader("에이전트 목록")
    try:
        agents = load_agents("agents")
        st.markdown(agent_inventory_markdown(agents))
    except Exception as exc:
        st.error(f"에이전트 로드 실패: {exc}")

input_text = st.text_input(
    "분석할 종목 티커를 입력하세요",
    value="005930.KS, NVDA",
    help="예: 005930.KS, 000660.KS, NVDA, TSLA / 6자리 한국 코드는 시장 선택에 따라 .KS 또는 .KQ 자동 부착",
)

col_a, col_b = st.columns([1, 3])
with col_a:
    run = st.button("🚀 분석 실행", type="primary", use_container_width=True)
with col_b:
    st.info("HF_TOKEN, Anthropic API, OpenAI-compatible API 중 하나를 선택해서 LLM을 연결할 수 있습니다. API 키가 없어도 provider=none으로 규칙 기반 리포트가 생성됩니다.")

if run:
    tickers = [x.strip() for x in input_text.replace("\n", ",").split(",") if x.strip()]
    if not tickers:
        st.warning("종목 티커를 입력하세요.")
        st.stop()

    client = build_llm_client(
        provider=provider,
        api_key=api_key or None,
        base_url=base_url or None,
        model=model or None,
        hf_provider=hf_provider,
    )
    orchestrator = StockAnalysisOrchestrator(agent_dir="agents", llm_client=client, parallel=parallel)

    results = []
    progress = st.progress(0)
    status = st.empty()
    for i, t in enumerate(tickers, start=1):
        status.write(f"분석 중: {t} ({i}/{len(tickers)})")
        try:
            results.append(orchestrator.analyze_one(t, market=market, period=period))
        except Exception as exc:
            st.error(f"{t} 분석 실패: {exc}")
        progress.progress(i / len(tickers))
    status.write("분석 완료")

    if len(results) > 1:
        st.subheader("📌 종목 비교 요약")
        st.markdown(compare_summary(results))

    for result in results:
        st.markdown("---")
        st.header(f"{result.company_name} ({result.ticker})")
        if result.warnings:
            with st.expander("데이터 수집 경고"):
                for w in result.warnings:
                    st.warning(w)

        tabs = st.tabs(["최종 리포트", "차트", "에이전트별 출력", "데이터 미리보기", "다운로드"])
        with tabs[0]:
            st.markdown(result.report)
        with tabs[1]:
            hist = result.history
            if hist is not None and not hist.empty:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"],
                    name="Price"
                ))
                for w in [20, 60, 120]:
                    ma = hist["Close"].rolling(w).mean()
                    fig.add_trace(go.Scatter(x=hist.index, y=ma, mode="lines", name=f"MA{w}"))
                fig.update_layout(height=520, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("차트 데이터가 없습니다.")
        with tabs[2]:
            for name, out in result.agent_outputs.items():
                with st.expander(f"{name} | LLM 사용: {out.used_llm}", expanded=False):
                    if out.error:
                        st.caption(f"오류/대체 실행: {out.error}")
                    st.markdown(out.output)
        with tabs[3]:
            st.json(result.data_context, expanded=False)
            if result.history is not None and not result.history.empty:
                st.dataframe(result.history.tail(50), use_container_width=True)
        with tabs[4]:
            st.download_button(
                label="Markdown 리포트 다운로드",
                data=result.report.encode("utf-8"),
                file_name=f"{result.ticker}_research_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
else:
    st.markdown("""
### 사용 순서
1. 사이드바에서 먼저 `provider=none`으로 테스트합니다.
2. LLM을 연결하려면 `huggingface`, `anthropic`, `openai-compatible` 중 하나를 선택합니다.
3. Hugging Face는 `HF_TOKEN`과 `google/gemma-4-26B-A4B-it` 모델을 기본값으로 사용할 수 있습니다.
4. 종목 티커를 입력합니다. 예: `005930.KS, NVDA`
5. **분석 실행**을 누르면 오케스트레이터가 6개 전문 에이전트를 실행합니다.

### 오케스트레이션 구조
```text
사용자 요청
  ↓
[병렬] 기업 개요 / 산업 분석 / 모멘텀 분석
  ↓
[순차] 재무 분석
  ↓
[순차] 리스크 분석
  ↓
[최종] 종합 의견 & 추천픽
```
""")
