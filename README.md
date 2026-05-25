# 주식 멀티 에이전트 리서치 앱

Claude Code의 `.claude/agents/*.md` 서브에이전트 문서 구조를 그대로 참조하면서, 같은 오케스트레이션을 로컬 VS Code와 Streamlit에서 실행할 수 있도록 만든 Python 프로젝트입니다.

## 핵심 기능

- Claude Code 호환 에이전트 프롬프트 포함: `.claude/agents/`
- Streamlit 웹앱: `app.py`
- CLI 실행: `run_analysis.py`
- 병렬 + 순차 멀티 에이전트 오케스트레이션
  - 1단계 병렬: 기업 개요 / 산업 분석 / 모멘텀 분석
  - 2단계 순차: 재무 분석
  - 3단계 순차: 리스크 분석
  - 4단계 최종 합성: 추천 의견
- yfinance 기반 가격/재무/기업 데이터 수집
- LLM API 없이도 규칙 기반 리포트 생성 가능
- LLM Provider 선택 가능
  - `none`: API 없이 fallback 리포트
  - `huggingface`: `HF_TOKEN` + Hugging Face Router / Inference Providers
  - `anthropic`: Anthropic Messages API
  - `openai-compatible`: OpenAI, OpenRouter, DeepInfra, Novita 등 `/chat/completions` 호환 API
- Hugging Face 기본 모델: `google/gemma-4-26B-A4B-it`
- 한국 주식 `.KS`, `.KQ` 티커 입력 지원
- Markdown 리포트 다운로드 지원

> 주의: 이 앱은 투자 판단 보조용 정보 정리 도구입니다. 실제 매수/매도 권유가 아니며, 최종 투자 책임은 사용자에게 있습니다.

---

## 1. 폴더 구조

```text
stock_multi_agent_research_app/
├── app.py                         # Streamlit 앱
├── run_analysis.py                # CLI 실행 파일
├── requirements.txt
├── .env.example
├── agents/                        # 앱이 읽는 에이전트 프롬프트
├── .claude/agents/                # Claude Code 호환 에이전트 프롬프트
├── src/
│   ├── agent_loader.py
│   ├── data_fetcher.py
│   ├── indicators.py
│   ├── llm_clients.py             # HF / Anthropic / OpenAI-compatible 클라이언트
│   ├── orchestrator.py
│   ├── report_templates.py
│   └── exporters.py
├── .vscode/
│   ├── launch.json
│   └── tasks.json
├── .streamlit/
│   └── config.toml
└── scripts/
    ├── install_windows.ps1
    └── run_streamlit.ps1
```

---

## 2. Windows + VS Code 설치

PowerShell에서 실행합니다.

```powershell
cd C:\0MyWork1
Expand-Archive .\stock_multi_agent_research_app.zip -DestinationPath .
cd .\stock_multi_agent_research_app

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell 실행 정책 때문에 venv 활성화가 막히면 아래를 한 번 실행합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\venv\Scripts\Activate.ps1
```

---

## 3. Streamlit 실행

```powershell
streamlit run app.py
```

브라우저에서 아래 주소가 열립니다.

```text
http://localhost:8501
```

---

## 4. `.env` 설정

`.env.example`을 복사해서 `.env`로 만듭니다.

```powershell
copy .env.example .env
notepad .env
```

예시:

```env
# Hugging Face
HF_TOKEN=hf_xxxxxxxxxxxxxxxxx
HF_MODEL=google/gemma-4-26B-A4B-it
HF_BASE_URL=https://router.huggingface.co/v1
HF_INFERENCE_PROVIDER=auto

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-sonnet-4-5

# OpenAI-compatible
OPENAI_COMPATIBLE_API_KEY=xxxxxxxxxxxxxxxxx
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_MODEL=gpt-4.1-mini
```

Streamlit 사이드바에 직접 입력한 API 키가 있으면 `.env`보다 우선합니다.

---

## 5. Hugging Face HF_TOKEN + Gemma 4 사용

### Streamlit UI에서 사용

1. 사이드바 `LLM Provider`에서 `huggingface` 선택
2. `HF 모델 선택`에서 `google/gemma-4-26B-A4B-it` 선택
3. `HF Inference Provider`는 우선 `auto` 권장
4. `HF_TOKEN` 입력 또는 `.env`에 저장
5. `연결 테스트` 클릭
6. 정상 연결되면 종목 입력 후 `분석 실행`

### CLI에서 사용

```powershell
$env:HF_TOKEN="hf_xxxxxxxxxxxxxxxxx"
python run_analysis.py --tickers NVDA --provider huggingface --model google/gemma-4-26B-A4B-it --period 1y
```

특정 HF Inference Provider를 강제하려면:

```powershell
python run_analysis.py --tickers NVDA --provider huggingface --model google/gemma-4-26B-A4B-it --hf-provider novita
```

또는 모델명에 suffix를 직접 붙일 수 있습니다.

```powershell
python run_analysis.py --tickers NVDA --provider huggingface --model google/gemma-4-26B-A4B-it:novita
```

> 참고: Hugging Face Router에서 모델이 지원되는 provider, 사용자의 Inference Providers 권한, 모델 라이선스 동의 여부에 따라 호출 가능 여부가 달라질 수 있습니다. 오류가 나면 HF Playground에서 해당 모델/provider 조합이 가능한지 먼저 확인하세요.

---

## 6. Anthropic API 사용

```powershell
$env:ANTHROPIC_API_KEY="sk-ant-..."
python run_analysis.py --tickers NVDA --provider anthropic --model claude-sonnet-4-5 --period 1y
```

Streamlit UI에서는 `LLM Provider = anthropic`을 선택하고 `ANTHROPIC_API_KEY`를 입력하면 됩니다.

---

## 7. OpenAI-compatible API 사용

OpenAI, OpenRouter, DeepInfra, Novita 등 `/chat/completions` 호환 엔드포인트를 연결할 수 있습니다.

```powershell
$env:OPENAI_COMPATIBLE_API_KEY="..."
python run_analysis.py --tickers NVDA --provider openai-compatible --base-url https://api.openai.com/v1 --model gpt-4.1-mini
```

예시:

```powershell
# OpenRouter
python run_analysis.py --tickers NVDA --provider openai-compatible --base-url https://openrouter.ai/api/v1 --model openai/gpt-4.1-mini

# DeepInfra
python run_analysis.py --tickers NVDA --provider openai-compatible --base-url https://api.deepinfra.com/v1/openai --model meta-llama/Meta-Llama-3.1-70B-Instruct

# Novita
python run_analysis.py --tickers NVDA --provider openai-compatible --base-url https://api.novita.ai/v3/openai --model your-model-id
```

---

## 8. CLI 기본 실행

API 키 없이 규칙 기반 리포트를 만들려면:

```powershell
python run_analysis.py --tickers 005930.KS NVDA --provider none --period 1y
```

---

## 9. 한국 주식 입력 예시

| 입력 | 설명 |
|---|---|
| `005930.KS` | 삼성전자, KOSPI |
| `000660.KS` | SK하이닉스, KOSPI |
| `035720.KS` | 카카오, KOSPI |
| `247540.KQ` | 에코프로비엠, KOSDAQ |
| `005930` + 시장 `KOSPI` | 앱에서 자동으로 `.KS` 부착 |

---

## 10. Claude Code에서도 사용하기

이 프로젝트에는 `.claude/agents/`가 이미 포함되어 있습니다. Claude Code에서 프로젝트 루트로 이동한 뒤 실행하면 프로젝트 레벨 subagent로 인식됩니다.

```powershell
cd C:\0MyWork1\stock_multi_agent_research_app
claude
```

Claude Code 안에서:

```text
stock-analyst-orchestrator를 사용해서 삼성전자와 SK하이닉스를 비교 분석해줘.
```

---

## 11. Streamlit Cloud 배포 시 Secrets

Streamlit Cloud에서는 `.env` 파일 대신 **App settings → Secrets**에 넣는 것을 권장합니다.

```toml
HF_TOKEN="hf_xxxxxxxxxxxxxxxxx"
HF_MODEL="google/gemma-4-26B-A4B-it"
HF_BASE_URL="https://router.huggingface.co/v1"
HF_INFERENCE_PROVIDER="auto"

ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxxx"
ANTHROPIC_MODEL="claude-sonnet-4-5"

OPENAI_COMPATIBLE_API_KEY="xxxxxxxxxxxxxxxxx"
OPENAI_COMPATIBLE_BASE_URL="https://api.openai.com/v1"
OPENAI_COMPATIBLE_MODEL="gpt-4.1-mini"
```

앱 화면에서 직접 API 키를 입력하는 방식도 지원합니다.

---

## 12. 투자 리포트 출력 구조

```text
1. 기업 개요
2. 재무 분석
3. 산업 분석
4. 모멘텀 분석
5. 리스크 요인
6. 종합 의견 & 추천픽
```

최종 리포트에는 다음이 포함됩니다.

- 투자의견
- 목표주가 또는 시나리오 가격 범위
- 핵심 투자 근거
- 주요 리스크
- 손절/재검토 조건
- 모니터링 지표
- 면책 문구

---

## 13. 한계

- 무료 데이터 소스는 항목 누락, 지연, 오류가 있을 수 있습니다.
- yfinance의 한국 주식 재무 데이터는 종목별로 제한적일 수 있습니다.
- LLM Provider의 모델 지원 여부, rate limit, 과금 정책은 provider별로 다릅니다.
- 목표주가 계산은 데이터 품질이 충분할 때만 보조지표로 사용해야 합니다.
- 앱의 출력은 금융투자업 인가를 받은 투자 자문이 아닙니다.

---

## 14. 권장 개선

- KRX/pykrx 수급 데이터 연동
- DART OpenAPI 재무제표 연동
- SEC 10-K/10-Q 파싱
- 리포트 PDF 출력
- LangGraph 기반 상태 그래프화
- 종목 스크리너/랭킹 기능 강화
