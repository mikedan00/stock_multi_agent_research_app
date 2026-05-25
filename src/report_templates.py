from __future__ import annotations

from typing import Any, Dict
import math


def fmt_num(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "데이터 확인 필요"
    try:
        v = float(value)
    except Exception:
        return str(value)
    if math.isnan(v) or math.isinf(v):
        return "데이터 확인 필요"
    abs_v = abs(v)
    if abs_v >= 1_000_000_000_000:
        return f"{v/1_000_000_000_000:,.2f}조{suffix}"
    if abs_v >= 100_000_000:
        return f"{v/100_000_000:,.1f}억{suffix}"
    if abs_v >= 1_000_000:
        return f"{v/1_000_000:,.1f}백만{suffix}"
    if abs_v >= 1000:
        return f"{v:,.0f}{suffix}"
    return f"{v:,.2f}{suffix}"


def fmt_pct(value: Any) -> str:
    if value is None or value == "":
        return "데이터 확인 필요"
    try:
        return f"{float(value)*100:,.2f}%"
    except Exception:
        return str(value)


def fmt_price(value: Any, currency: str = "") -> str:
    if value is None:
        return "데이터 확인 필요"
    try:
        return f"{float(value):,.2f} {currency}".strip()
    except Exception:
        return str(value)


def _info(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("info", {}) or {}


def _tech(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("technical", {}) or {}


def company_overview(data: Dict[str, Any]) -> str:
    info = _info(data)
    name = info.get("longName") or info.get("shortName") or data.get("ticker")
    summary = info.get("longBusinessSummary") or "기업 사업 설명 데이터 확인 필요"
    if len(summary) > 900:
        summary = summary[:900] + "..."
    return f"""## 1. 기업 개요

### 📌 기본 정보
| 항목 | 내용 |
|---|---|
| 회사명 | {name} |
| 티커 | {data.get('ticker')} |
| 거래소 | {info.get('exchange', '데이터 확인 필요')} |
| 섹터 | {info.get('sector', '데이터 확인 필요')} |
| 산업 | {info.get('industry', '데이터 확인 필요')} |
| 국가 | {info.get('country', '데이터 확인 필요')} |
| 시가총액 | {fmt_num(info.get('marketCap'))} |
| 웹사이트 | {info.get('website', '데이터 확인 필요')} |

### 🏢 비즈니스 모델
{summary}

### 🏆 경쟁 우위 추정
- 브랜드/기술/규모의 경제 여부는 사업 설명과 산업 구조를 기준으로 추가 검증이 필요합니다.
- 현재 자동 수집 데이터만으로는 시장점유율과 고객 락인 정도를 확정하기 어렵습니다.

### ⚔️ 경쟁사 현황
- 직접 경쟁사는 섹터·산업 기준으로 별도 피어 그룹 구성이 필요합니다.
- 앱 확장 시 동종 업계 티커 리스트를 입력받아 상대 비교하도록 개선할 수 있습니다.

### 📰 최근 주요 이슈
- 뉴스/공시 API를 연결하지 않은 경우 최근 이슈는 `데이터 확인 필요`입니다.
"""


def financial_analysis(data: Dict[str, Any]) -> str:
    info = _info(data)
    currency = info.get("currency", "")
    rows = [
        ("PER(TTM)", fmt_num(info.get("trailingPE")), "낮을수록 저평가 가능성이 있으나 성장률과 함께 판단"),
        ("Forward PER", fmt_num(info.get("forwardPE")), "예상 이익 기준 밸류에이션"),
        ("PBR", fmt_num(info.get("priceToBook")), "자본 대비 시장 평가"),
        ("EV/EBITDA", fmt_num(info.get("enterpriseToEbitda")), "현금창출력 대비 기업가치"),
        ("영업이익률", fmt_pct(info.get("operatingMargins")), "수익성 품질"),
        ("순이익률", fmt_pct(info.get("profitMargins")), "최종 이익률"),
        ("ROE", fmt_pct(info.get("returnOnEquity")), "자기자본 효율"),
        ("부채비율", fmt_num(info.get("debtToEquity")), "재무 레버리지"),
        ("현금성 자산", fmt_price(info.get("totalCash"), currency), "유동성 방어력"),
        ("잉여현금흐름", fmt_price(info.get("freeCashflow"), currency), "주주환원/투자 여력"),
    ]
    table = "| 지표 | 현재값 | 해석 |\n|---|---:|---|\n" + "\n".join([f"| {a} | {b} | {c} |" for a,b,c in rows])
    strengths = []
    weaknesses = []
    if info.get("profitMargins") is not None and info.get("profitMargins") > 0.1:
        strengths.append("순이익률이 두 자릿수로 확인되어 수익성 측면은 긍정적입니다.")
    if info.get("returnOnEquity") is not None and info.get("returnOnEquity") > 0.15:
        strengths.append("ROE가 15% 이상이면 자본 효율성이 양호한 편입니다.")
    if info.get("debtToEquity") is not None and info.get("debtToEquity") > 150:
        weaknesses.append("부채비율이 높은 편이므로 금리와 차환 리스크 확인이 필요합니다.")
    if info.get("trailingPE") is not None and info.get("trailingPE") > 40:
        weaknesses.append("PER이 높은 편이라 성장 기대가 둔화될 경우 밸류에이션 조정 위험이 있습니다.")
    return f"""## 2. 재무 분석

### 📈 핵심 재무·밸류에이션 지표
{table}

### 📄 재무제표 데이터 상태
- 손익계산서 수집 상태: {'확인됨' if data.get('financials') else '데이터 확인 필요'}
- 재무상태표 수집 상태: {'확인됨' if data.get('balance_sheet') else '데이터 확인 필요'}
- 현금흐름표 수집 상태: {'확인됨' if data.get('cashflow') else '데이터 확인 필요'}

### ✅ 주요 재무 강점
{chr(10).join('- ' + s for s in strengths) if strengths else '- 데이터 확인 필요 또는 뚜렷한 자동 감지 강점 없음'}

### ⚠️ 주요 재무 약점
{chr(10).join('- ' + s for s in weaknesses) if weaknesses else '- 데이터 확인 필요 또는 뚜렷한 자동 감지 약점 없음'}

**재무 종합 판단:** 자동 수집 지표 기준으로 수익성, 성장성, 부채 부담, 현금흐름을 추가 검증해야 합니다.
"""


def industry_analysis(data: Dict[str, Any]) -> str:
    info = _info(data)
    sector = info.get("sector", "데이터 확인 필요")
    industry = info.get("industry", "데이터 확인 필요")
    return f"""## 3. 산업 분석

### 🌐 산업 분류
| 항목 | 내용 |
|---|---|
| 섹터 | {sector} |
| 산업 | {industry} |
| 시장 규모 | 데이터 확인 필요 |
| 예상 CAGR | 데이터 확인 필요 |

### ⚡ 경쟁 구조: Porter's Five Forces
| 경쟁 요인 | 강도 | 근거 |
|---|---|---|
| 신규 진입 위협 | 데이터 확인 필요 | 산업 진입장벽, 규제, 자본집약도 확인 필요 |
| 공급자 교섭력 | 데이터 확인 필요 | 원재료/핵심 부품 공급망 확인 필요 |
| 구매자 교섭력 | 데이터 확인 필요 | 고객 집중도와 가격 결정력 확인 필요 |
| 대체재 위협 | 데이터 확인 필요 | 기술 변화와 대체 솔루션 확인 필요 |
| 기존 경쟁 강도 | 데이터 확인 필요 | 피어 그룹 비교 필요 |

### 📡 구조적 트렌드
- AI/자동화, 디지털 전환, 공급망 재편, 금리·환율 환경이 해당 기업에 미치는 영향을 별도 점검해야 합니다.
- 산업 사이클 위치는 매출 성장률, 재고, 가격, CAPEX 지표를 함께 확인해야 합니다.

### 🎯 기업 포지셔닝
- 시장점유율, 경쟁사 대비 마진 프리미엄, 기술 격차는 추가 데이터 확인 필요입니다.

**산업 매력도 종합:** 데이터 확인 필요
**해당 기업에 미치는 영향:** 중립, 단 추가 산업 데이터 확보 시 변경 가능
"""


def momentum_analysis(data: Dict[str, Any]) -> str:
    tech = _tech(data)
    currency = _info(data).get("currency", "")
    def signal_rsi(x):
        if x is None: return "데이터 확인 필요"
        if x >= 70: return "과매수권"
        if x <= 30: return "과매도권"
        return "중립권"
    macd_state = "데이터 확인 필요"
    if tech.get("macd") is not None and tech.get("macd_signal") is not None:
        macd_state = "상승 신호" if tech["macd"] > tech["macd_signal"] else "하락 신호"
    return f"""## 4. 모멘텀 분석

### 📉 주가 퍼포먼스
| 기간 | 수익률 |
|---|---:|
| 1개월 | {fmt_pct(tech.get('return_1m'))} |
| 3개월 | {fmt_pct(tech.get('return_3m'))} |
| 6개월 | {fmt_pct(tech.get('return_6m'))} |
| 12개월 | {fmt_pct(tech.get('return_12m'))} |
| YTD | {fmt_pct(tech.get('return_ytd'))} |

### 📊 기술적 신호
| 항목 | 현재값 | 해석 |
|---|---:|---|
| 현재가 | {fmt_price(tech.get('current_price'), currency)} | 기준 가격 |
| 20일선 | {fmt_price(tech.get('ma20'), currency)} | {'현재가 상회' if tech.get('above_ma20') else '현재가 하회 또는 확인 필요'} |
| 60일선 | {fmt_price(tech.get('ma60'), currency)} | {'현재가 상회' if tech.get('above_ma60') else '현재가 하회 또는 확인 필요'} |
| 120일선 | {fmt_price(tech.get('ma120'), currency)} | {'현재가 상회' if tech.get('above_ma120') else '현재가 하회 또는 확인 필요'} |
| RSI(14) | {fmt_num(tech.get('rsi14'))} | {signal_rsi(tech.get('rsi14'))} |
| MACD | {fmt_num(tech.get('macd'))} | {macd_state} |
| 52주 고점 | {fmt_price(tech.get('high_52w'), currency)} | 고점 대비 위치 확인 |
| 52주 저점 | {fmt_price(tech.get('low_52w'), currency)} | 저점 대비 위치 확인 |
| 거래량/20일 평균 | {fmt_num(tech.get('volume_ratio_20d'))} | 1 이상이면 평균 대비 거래 증가 |

**모멘텀 종합 시그널:** {tech.get('trend', '데이터 확인 필요')}  
**매매 타이밍:** 추세와 실적 확인 후 분할 접근 권장
"""


def risk_analysis(data: Dict[str, Any]) -> str:
    info = _info(data)
    tech = _tech(data)
    risks = []
    if info.get("trailingPE") is not None and info.get("trailingPE") > 40:
        risks.append(("밸류에이션 리스크", "PER이 높은 구간으로 실적 둔화 시 멀티플 축소 가능", "높음"))
    if info.get("debtToEquity") is not None and info.get("debtToEquity") > 150:
        risks.append(("재무 리스크", "부채비율이 높아 금리 상승·차환 부담에 민감", "중간~높음"))
    if tech.get("rsi14") is not None and tech.get("rsi14") >= 70:
        risks.append(("단기 과열 리스크", "RSI가 과매수권으로 단기 조정 가능성", "중간"))
    beta = info.get("beta")
    if beta is not None and beta > 1.5:
        risks.append(("시장 변동성 리스크", "베타가 높아 지수 하락 시 변동성 확대 가능", "중간"))
    if not risks:
        risks.append(("데이터 리스크", "무료 데이터 소스만으로는 핵심 리스크 정량화에 한계", "중간"))

    table = "| 리스크 유형 | 내용 | 영향도 | 관찰 지표 |\n|---|---|---|---|\n" + "\n".join(
        f"| {r[0]} | {r[1]} | {r[2]} | 실적, 밸류에이션, 주가 추세 |" for r in risks
    )
    return f"""## 5. 리스크 요인

### 🔴 핵심 리스크
{table}

### 📐 시나리오 분석
| 시나리오 | 확률 | 핵심 가정 | 주가 영향 |
|---|---:|---|---|
| Bull Case | 25% | 실적 개선 + 멀티플 유지/확장 | 상승 가능 |
| Base Case | 50% | 현재 실적 추세와 밸류에이션 유지 | 제한적 변동 |
| Bear Case | 25% | 실적 둔화 또는 리스크 현실화 | 하락 가능 |

### ⚠️ 투자 포기/재검토 조건
- 실적 발표에서 매출 성장률 또는 마진이 시장 기대를 지속적으로 하회
- 핵심 사업의 경쟁 강도 상승으로 가격 결정력 약화
- 부채 부담, 소송, 규제 이슈가 현금흐름에 직접적 악영향
- 주요 이동평균선 이탈과 거래량 동반 하락 지속
"""


def _score(data: Dict[str, Any]) -> Dict[str, Any]:
    info = _info(data)
    tech = _tech(data)
    score = {
        "business": 5,
        "financial": 5,
        "growth": 5,
        "valuation": 5,
        "momentum": 5,
        "risk": 5,
    }
    if info.get("profitMargins") is not None:
        score["financial"] += 1 if info["profitMargins"] > 0.1 else -1
    if info.get("returnOnEquity") is not None:
        score["financial"] += 1 if info["returnOnEquity"] > 0.15 else 0
    if info.get("revenueGrowth") is not None:
        score["growth"] += 2 if info["revenueGrowth"] > 0.15 else (1 if info["revenueGrowth"] > 0.05 else -1)
    if info.get("trailingPE") is not None:
        pe = info["trailingPE"]
        if pe < 10: score["valuation"] += 1
        elif pe > 40: score["valuation"] -= 2
        elif pe > 25: score["valuation"] -= 1
    if tech.get("trend") == "상승추세":
        score["momentum"] += 2
    elif tech.get("trend") == "하락추세":
        score["momentum"] -= 2
    if info.get("debtToEquity") is not None and info["debtToEquity"] > 150:
        score["risk"] -= 2
    if tech.get("rsi14") is not None and tech["rsi14"] >= 75:
        score["risk"] -= 1
    for k in score:
        score[k] = max(1, min(10, score[k]))
    total = score["business"]*0.20 + score["financial"]*0.25 + score["growth"]*0.20 + score["valuation"]*0.15 + score["momentum"]*0.10 + score["risk"]*0.10
    return {"parts": score, "total": total}


def recommendation(data: Dict[str, Any], previous_outputs: Dict[str, str] | None = None) -> str:
    info = _info(data)
    tech = _tech(data)
    currency = info.get("currency", "")
    current = tech.get("current_price") or info.get("currentPrice") or info.get("regularMarketPrice")
    scored = _score(data)
    total = scored["total"]
    if total >= 7.8:
        opinion = "BUY"
    elif total >= 5.3:
        opinion = "HOLD"
    else:
        opinion = "SELL / AVOID"
    target = None
    upside = None
    if current is not None:
        # Conservative rule-based target proxy, not a formal valuation.
        expected = (total - 5.0) / 10.0
        expected = max(-0.20, min(0.30, expected))
        target = current * (1 + expected)
        upside = expected
    p = scored["parts"]
    return f"""## 6. 종합 의견 & 추천픽

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  
🏆 **투자의견: {opinion}**  
🎯 **참고 목표가격 범위:** {fmt_price(target, currency)}  
📌 **현재가:** {fmt_price(current, currency)}  
📈 **참고 상승여력:** {fmt_pct(upside)}  
⏰ **투자 기간:** 6~12개월  
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 종합 점수표
| 항목 | 점수 / 10 |
|---|---:|
| 비즈니스 질 | {p['business']} |
| 재무 건전성 | {p['financial']} |
| 성장성 | {p['growth']} |
| 밸류에이션 매력 | {p['valuation']} |
| 모멘텀 | {p['momentum']} |
| 리스크 관리 가능성 | {p['risk']} |
| **가중 종합점수** | **{total:.2f}** |

### ✅ 핵심 투자 근거
1. **기업/산업 기반:** {info.get('sector', '섹터 데이터 확인 필요')} / {info.get('industry', '산업 데이터 확인 필요')} 내 포지셔닝을 추가 확인해야 하나, 현재 수집 데이터 기준으로 기본 분석 가능.
2. **재무 기반:** 순이익률 {fmt_pct(info.get('profitMargins'))}, ROE {fmt_pct(info.get('returnOnEquity'))}, 부채비율 {fmt_num(info.get('debtToEquity'))}를 중심으로 판단.
3. **모멘텀 기반:** 현재 기술적 추세는 `{tech.get('trend', '데이터 확인 필요')}`이며, RSI는 {fmt_num(tech.get('rsi14'))} 수준.

### ❌ 주요 리스크
1. 무료 데이터의 누락 가능성: DART/SEC/거래소 데이터로 교차 검증 필요.
2. 밸류에이션 리스크: PER/PBR/EV/EBITDA가 업종 평균 대비 높은지 확인 필요.
3. 이벤트 리스크: 실적 발표, 규제, 환율/금리, 공급망 이슈 발생 시 투자 논리 훼손 가능.

### 📋 매매 전략
- **진입 전략:** 단일 가격 일괄 매수보다 분할 접근.
- **1차 확인 구간:** 20일/60일 이동평균선 지지 여부.
- **손절/재검토 조건:** 주요 지지선 이탈 + 실적 추정치 하향 동시 발생.
- **추가 매수 조건:** 실적 개선 확인 + 거래량 동반 추세 회복.

### 🔍 모니터링 포인트
- 다음 실적 발표의 매출 성장률, 영업이익률, 가이던스
- 외국인/기관 수급, 거래량 증가 여부
- 섹터 내 경쟁사 대비 주가 상대강도
- 금리, 환율, 규제/정책 변화

---
⚠️ 본 분석은 AI 기반 정보 정리이며 투자 권유가 아닙니다. 최종 투자 결정은 본인 판단과 책임 하에 진행하시기 바랍니다.
"""


def build_fallback(agent_name: str, data: Dict[str, Any], previous_outputs: Dict[str, str] | None = None) -> str:
    mapping = {
        "company-overview-agent": company_overview,
        "financial-analysis-agent": financial_analysis,
        "industry-analysis-agent": industry_analysis,
        "momentum-analysis-agent": momentum_analysis,
        "risk-analysis-agent": risk_analysis,
        "recommendation-agent": lambda d: recommendation(d, previous_outputs),
    }
    fn = mapping.get(agent_name)
    if not fn:
        return f"## {agent_name}\n\n해당 에이전트의 규칙 기반 템플릿이 없습니다."
    return fn(data)
