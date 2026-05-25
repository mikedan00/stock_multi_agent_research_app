from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import json
import math
import pandas as pd
import yfinance as yf

from .indicators import compute_technical_indicators
from .ticker_resolver import resolve_stock_symbol, normalize_ticker


def _json_safe(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (pd.DataFrame,)):
        return value.fillna("").astype(str).to_dict()
    if isinstance(value, (pd.Series,)):
        return value.dropna().astype(str).to_dict()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _small_table(df: pd.DataFrame, max_rows: int = 18, max_cols: int = 6) -> dict:
    if df is None or df.empty:
        return {}
    out = df.copy()
    out = out.iloc[:max_rows, :max_cols]
    out.columns = [str(c)[:10] for c in out.columns]
    return _json_safe(out)


@dataclass
class StockDataPackage:
    input_ticker: str
    ticker: str
    resolved_name: str | None
    resolution_method: str
    resolution_candidates: list[Dict[str, Any]]
    market: str
    period: str
    info: Dict[str, Any]
    technical: Dict[str, Any]
    financials: Dict[str, Any]
    balance_sheet: Dict[str, Any]
    cashflow: Dict[str, Any]
    quarterly_financials: Dict[str, Any]
    history_tail: Dict[str, Any]
    warnings: list[str]

    def to_context_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    def to_context_json(self, max_chars: int = 14000) -> str:
        text = json.dumps(self.to_context_dict(), ensure_ascii=False, indent=2)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...TRUNCATED..."
        return text


def _fetch_history(symbol: str, period: str) -> tuple[pd.DataFrame, str | None]:
    try:
        hist = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        if hist is None:
            hist = pd.DataFrame()
        return hist, None
    except Exception as exc:
        return pd.DataFrame(), str(exc)


def _alternate_krx_suffix(symbol: str) -> str | None:
    if symbol.endswith(".KS") and len(symbol) == 9 and symbol[:6].isdigit():
        return symbol[:6] + ".KQ"
    if symbol.endswith(".KQ") and len(symbol) == 9 and symbol[:6].isdigit():
        return symbol[:6] + ".KS"
    return None


def fetch_stock_data(ticker: str, market: str = "AUTO", period: str = "1y") -> tuple[StockDataPackage, pd.DataFrame]:
    resolution = resolve_stock_symbol(ticker, market)
    normalized = normalize_ticker(resolution.ticker, market)
    warnings: list[str] = list(resolution.warnings)

    history, hist_error = _fetch_history(normalized, period)
    if hist_error:
        warnings.append(f"가격 데이터 수집 실패({normalized}): {hist_error}")

    # KRX 종목명 조회는 시장 구분이 없을 수 있습니다. AUTO일 때 .KS가 비면 .KQ로 재시도합니다.
    if (history is None or history.empty) and (market or "AUTO").upper() == "AUTO":
        alt = _alternate_krx_suffix(normalized)
        if alt:
            alt_history, alt_error = _fetch_history(alt, period)
            if alt_history is not None and not alt_history.empty:
                warnings.append(f"KRX 시장 접미사 자동 보정: {normalized} → {alt}")
                normalized = alt
                resolution.ticker = alt
                history = alt_history
            elif alt_error:
                warnings.append(f"대체 접미사 가격 데이터 수집 실패({alt}): {alt_error}")

    if history is None or history.empty:
        warnings.append("가격 데이터가 비어 있습니다. 종목명/티커/거래소 접미사를 확인하세요.")

    yf_ticker = yf.Ticker(normalized)

    info: Dict[str, Any] = {}
    try:
        info = yf_ticker.info or {}
    except Exception as exc:
        warnings.append(f"info 수집 실패: {exc}")

    try:
        financials = _small_table(yf_ticker.financials)
    except Exception as exc:
        financials = {}
        warnings.append(f"손익계산서 수집 실패: {exc}")

    try:
        balance_sheet = _small_table(yf_ticker.balance_sheet)
    except Exception as exc:
        balance_sheet = {}
        warnings.append(f"재무상태표 수집 실패: {exc}")

    try:
        cashflow = _small_table(yf_ticker.cashflow)
    except Exception as exc:
        cashflow = {}
        warnings.append(f"현금흐름표 수집 실패: {exc}")

    try:
        quarterly_financials = _small_table(yf_ticker.quarterly_financials)
    except Exception as exc:
        quarterly_financials = {}
        warnings.append(f"분기 재무 수집 실패: {exc}")

    technical = compute_technical_indicators(history)
    history_tail = {}
    if not history.empty:
        keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in history.columns]
        history_tail = _json_safe(history[keep_cols].tail(30))

    package = StockDataPackage(
        input_ticker=ticker,
        ticker=normalized,
        resolved_name=resolution.resolved_name,
        resolution_method=resolution.method,
        resolution_candidates=resolution.candidates,
        market=market,
        period=period,
        info={k: info.get(k) for k in [
            "longName", "shortName", "symbol", "quoteType", "currency", "exchange", "sector", "industry",
            "country", "website", "longBusinessSummary", "marketCap", "enterpriseValue", "currentPrice",
            "regularMarketPrice", "previousClose", "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda",
            "profitMargins", "operatingMargins", "grossMargins", "returnOnEquity", "returnOnAssets",
            "revenueGrowth", "earningsGrowth", "totalDebt", "totalCash", "debtToEquity", "freeCashflow",
            "operatingCashflow", "targetMeanPrice", "recommendationMean", "recommendationKey",
            "numberOfAnalystOpinions", "beta", "dividendYield", "payoutRatio", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        ] if k in info},
        technical=technical,
        financials=financials,
        balance_sheet=balance_sheet,
        cashflow=cashflow,
        quarterly_financials=quarterly_financials,
        history_tail=history_tail,
        warnings=warnings,
    )
    return package, history
