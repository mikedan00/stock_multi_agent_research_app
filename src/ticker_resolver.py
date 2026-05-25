from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
import re
import unicodedata

import pandas as pd
import requests


@dataclass
class TickerResolution:
    original_input: str
    ticker: str
    resolved_name: str | None = None
    method: str = "direct"
    market: str = "AUTO"
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_input": self.original_input,
            "ticker": self.ticker,
            "resolved_name": self.resolved_name,
            "method": self.method,
            "market": self.market,
            "candidates": self.candidates[:10],
            "warnings": self.warnings,
        }


# 자주 쓰는 종목명/별칭은 오프라인에서도 즉시 변환되도록 기본 내장합니다.
# 더 넓은 한국 종목명은 KRX 상장회사 목록을 온라인으로 조회하고,
# 미국/해외 종목명은 Yahoo Finance search endpoint로 보조 조회합니다.
KNOWN_ALIASES: Dict[str, Dict[str, str]] = {
    # Korea - KOSPI
    "삼성전자": {"ticker": "005930.KS", "name": "삼성전자"},
    "삼전": {"ticker": "005930.KS", "name": "삼성전자"},
    "삼성전자우": {"ticker": "005935.KS", "name": "삼성전자우"},
    "sk하이닉스": {"ticker": "000660.KS", "name": "SK하이닉스"},
    "하이닉스": {"ticker": "000660.KS", "name": "SK하이닉스"},
    "현대차": {"ticker": "005380.KS", "name": "현대차"},
    "현대자동차": {"ticker": "005380.KS", "name": "현대차"},
    "기아": {"ticker": "000270.KS", "name": "기아"},
    "네이버": {"ticker": "035420.KS", "name": "NAVER"},
    "naver": {"ticker": "035420.KS", "name": "NAVER"},
    "카카오": {"ticker": "035720.KS", "name": "카카오"},
    "lg에너지솔루션": {"ticker": "373220.KS", "name": "LG에너지솔루션"},
    "엘지에너지솔루션": {"ticker": "373220.KS", "name": "LG에너지솔루션"},
    "lg화학": {"ticker": "051910.KS", "name": "LG화학"},
    "엘지화학": {"ticker": "051910.KS", "name": "LG화학"},
    "삼성sdi": {"ticker": "006400.KS", "name": "삼성SDI"},
    "삼성바이오로직스": {"ticker": "207940.KS", "name": "삼성바이오로직스"},
    "셀트리온": {"ticker": "068270.KS", "name": "셀트리온"},
    "posco홀딩스": {"ticker": "005490.KS", "name": "POSCO홀딩스"},
    "포스코홀딩스": {"ticker": "005490.KS", "name": "POSCO홀딩스"},
    "현대모비스": {"ticker": "012330.KS", "name": "현대모비스"},
    "kb금융": {"ticker": "105560.KS", "name": "KB금융"},
    "신한지주": {"ticker": "055550.KS", "name": "신한지주"},
    "하나금융지주": {"ticker": "086790.KS", "name": "하나금융지주"},
    "두산에너빌리티": {"ticker": "034020.KS", "name": "두산에너빌리티"},
    "한화에어로스페이스": {"ticker": "012450.KS", "name": "한화에어로스페이스"},
    "삼성중공업": {"ticker": "010140.KS", "name": "삼성중공업"},
    "현대건설": {"ticker": "000720.KS", "name": "현대건설"},
    "lg전자": {"ticker": "066570.KS", "name": "LG전자"},
    "엘지전자": {"ticker": "066570.KS", "name": "LG전자"},
    "한미반도체": {"ticker": "042700.KS", "name": "한미반도체"},
    "hd현대일렉트릭": {"ticker": "267260.KS", "name": "HD현대일렉트릭"},
    # Korea - KOSDAQ
    "에코프로비엠": {"ticker": "247540.KQ", "name": "에코프로비엠"},
    "에코프로": {"ticker": "086520.KQ", "name": "에코프로"},
    "알테오젠": {"ticker": "196170.KQ", "name": "알테오젠"},
    "hlb": {"ticker": "028300.KQ", "name": "HLB"},
    "리가켐바이오": {"ticker": "141080.KQ", "name": "리가켐바이오"},
    "레인보우로보틱스": {"ticker": "277810.KQ", "name": "레인보우로보틱스"},
    "jyp": {"ticker": "035900.KQ", "name": "JYP Ent."},
    "jyp ent": {"ticker": "035900.KQ", "name": "JYP Ent."},
    "에스엠": {"ticker": "041510.KQ", "name": "에스엠"},
    "sm엔터": {"ticker": "041510.KQ", "name": "에스엠"},
    # US
    "엔비디아": {"ticker": "NVDA", "name": "NVIDIA"},
    "nvidia": {"ticker": "NVDA", "name": "NVIDIA"},
    "테슬라": {"ticker": "TSLA", "name": "Tesla"},
    "tesla": {"ticker": "TSLA", "name": "Tesla"},
    "애플": {"ticker": "AAPL", "name": "Apple"},
    "apple": {"ticker": "AAPL", "name": "Apple"},
    "마이크로소프트": {"ticker": "MSFT", "name": "Microsoft"},
    "ms": {"ticker": "MSFT", "name": "Microsoft"},
    "microsoft": {"ticker": "MSFT", "name": "Microsoft"},
    "구글": {"ticker": "GOOGL", "name": "Alphabet"},
    "알파벳": {"ticker": "GOOGL", "name": "Alphabet"},
    "alphabet": {"ticker": "GOOGL", "name": "Alphabet"},
    "아마존": {"ticker": "AMZN", "name": "Amazon"},
    "amazon": {"ticker": "AMZN", "name": "Amazon"},
    "메타": {"ticker": "META", "name": "Meta Platforms"},
    "meta": {"ticker": "META", "name": "Meta Platforms"},
    "넷플릭스": {"ticker": "NFLX", "name": "Netflix"},
    "netflix": {"ticker": "NFLX", "name": "Netflix"},
    "amd": {"ticker": "AMD", "name": "Advanced Micro Devices"},
    "인텔": {"ticker": "INTC", "name": "Intel"},
    "intel": {"ticker": "INTC", "name": "Intel"},
    "브로드컴": {"ticker": "AVGO", "name": "Broadcom"},
    "broadcom": {"ticker": "AVGO", "name": "Broadcom"},
    "마이크론": {"ticker": "MU", "name": "Micron"},
    "micron": {"ticker": "MU", "name": "Micron"},
    "팔란티어": {"ticker": "PLTR", "name": "Palantir"},
    "palantir": {"ticker": "PLTR", "name": "Palantir"},
    "tsmc": {"ticker": "TSM", "name": "TSMC"},
    "asml": {"ticker": "ASML", "name": "ASML"},
    "코카콜라": {"ticker": "KO", "name": "Coca-Cola"},
    "coca cola": {"ticker": "KO", "name": "Coca-Cola"},
    "버크셔": {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
    "버크셔해서웨이": {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
}


DIRECT_TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-_=^/]{0,20}$")
KRX_CODE_RE = re.compile(r"^\d{6}$")


def _compact(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    text = text.replace("㈜", "").replace("주식회사", "")
    return text


def normalize_ticker(ticker: str, market: str = "AUTO") -> str:
    t = (ticker or "").strip().upper()
    market = (market or "AUTO").upper()
    if not t:
        raise ValueError("Ticker is empty")
    if t.endswith((".KS", ".KQ", ".T", ".HK", ".SS", ".SZ", ".L", ".TO", ".AX")):
        return t
    if KRX_CODE_RE.match(t):
        if market == "KOSDAQ":
            return f"{t}.KQ"
        return f"{t}.KS"
    return t


def _looks_like_direct_ticker(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if KRX_CODE_RE.match(q):
        return True
    if any("가" <= ch <= "힣" for ch in q):
        return False
    # 영문 회사명은 보통 공백이 들어가므로 ticker로 보지 않습니다.
    if " " in q:
        return False
    return bool(DIRECT_TICKER_RE.match(q))


def _alias_lookup(query: str) -> Optional[Dict[str, str]]:
    key = _compact(query)
    if key in KNOWN_ALIASES:
        return KNOWN_ALIASES[key]
    # 한글/영문 사이 공백을 보존한 키도 일부 대응
    lower = unicodedata.normalize("NFKC", query or "").strip().lower()
    return KNOWN_ALIASES.get(lower)


def load_krx_listing(cache_dir: str | Path = ".cache", max_age_days: int = 7) -> pd.DataFrame:
    """Load Korean listed-company names from KRX/KIND.

    The KIND download endpoint occasionally changes or blocks requests. This
    function therefore uses a local cache and fails quietly in the caller.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "krx_company_list.csv"
    if cache_path.exists():
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mtime < timedelta(days=max_age_days):
            try:
                return pd.read_csv(cache_path, dtype={"code": str})
            except Exception:
                pass

    url = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    try:
        tables = pd.read_html(BytesIO(resp.content), encoding="euc-kr")
    except Exception:
        tables = pd.read_html(BytesIO(resp.content))
    if not tables:
        raise RuntimeError("KRX company table not found")
    raw = tables[0]
    cols = {str(c).strip(): c for c in raw.columns}
    name_col = cols.get("회사명") or cols.get("종목명") or raw.columns[0]
    code_col = cols.get("종목코드") or cols.get("코드") or raw.columns[1]
    out = pd.DataFrame({
        "name": raw[name_col].astype(str).str.strip(),
        "code": raw[code_col].astype(str).str.extract(r"(\d+)")[0].str.zfill(6),
    }).dropna()
    out = out[out["code"].str.match(r"^\d{6}$", na=False)].drop_duplicates("code")
    out.to_csv(cache_path, index=False, encoding="utf-8-sig")
    return out


def search_krx_by_name(query: str, market: str = "AUTO") -> Optional[TickerResolution]:
    try:
        df = load_krx_listing()
    except Exception as exc:
        return TickerResolution(
            original_input=query,
            ticker=query,
            method="krx_lookup_failed",
            market=market,
            warnings=[f"KRX 종목명 조회 실패: {exc}"],
        )

    q = _compact(query)
    if not q:
        return None
    df = df.copy()
    df["compact_name"] = df["name"].map(_compact)
    exact = df[df["compact_name"] == q]
    if exact.empty:
        exact = df[df["compact_name"].str.contains(re.escape(q), na=False)]
    if exact.empty:
        return None

    exact = exact.head(10)
    suffix = ".KQ" if (market or "AUTO").upper() == "KOSDAQ" else ".KS"
    first = exact.iloc[0]
    candidates = [
        {
            "name": row["name"],
            "ticker_kospi_guess": f"{row['code']}.KS",
            "ticker_kosdaq_guess": f"{row['code']}.KQ",
        }
        for _, row in exact.iterrows()
    ]
    warnings: List[str] = []
    if len(exact) > 1:
        names = ", ".join([str(x) for x in exact["name"].head(5).tolist()])
        warnings.append(f"종목명 후보가 여러 개입니다. 첫 번째 후보를 사용했습니다: {names}")
    if (market or "AUTO").upper() == "AUTO":
        warnings.append("KRX 종목명 조회는 시장 구분이 불완전할 수 있어 먼저 .KS로 시도하고 실패하면 .KQ로 자동 재시도합니다.")
    return TickerResolution(
        original_input=query,
        ticker=f"{first['code']}{suffix}",
        resolved_name=str(first["name"]),
        method="krx_name_lookup",
        market=market,
        candidates=candidates,
        warnings=warnings,
    )


def search_yahoo_symbol(query: str, market: str = "AUTO") -> Optional[TickerResolution]:
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 8, "newsCount": 0, "enableFuzzyQuery": "true"}
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return TickerResolution(
            original_input=query,
            ticker=query,
            method="yahoo_lookup_failed",
            market=market,
            warnings=[f"Yahoo 종목명 조회 실패: {exc}"],
        )

    quotes = data.get("quotes", []) or []
    usable = []
    for q in quotes:
        symbol = q.get("symbol")
        quote_type = q.get("quoteType") or q.get("typeDisp")
        if not symbol:
            continue
        if quote_type and str(quote_type).upper() not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
            continue
        usable.append(q)
    if not usable:
        return None
    first = usable[0]
    candidates = [
        {
            "symbol": q.get("symbol"),
            "shortname": q.get("shortname") or q.get("longname"),
            "exchange": q.get("exchange"),
            "quoteType": q.get("quoteType"),
        }
        for q in usable[:8]
    ]
    return TickerResolution(
        original_input=query,
        ticker=str(first.get("symbol")).upper(),
        resolved_name=first.get("shortname") or first.get("longname"),
        method="yahoo_search",
        market=market,
        candidates=candidates,
        warnings=[] if len(usable) == 1 else ["Yahoo 검색 후보가 여러 개입니다. 첫 번째 후보를 사용했습니다."],
    )


def resolve_stock_symbol(query: str, market: str = "AUTO") -> TickerResolution:
    original = (query or "").strip()
    if not original:
        raise ValueError("종목명/티커가 비어 있습니다.")

    alias = _alias_lookup(original)
    if alias:
        return TickerResolution(
            original_input=original,
            ticker=normalize_ticker(alias["ticker"], market=market),
            resolved_name=alias.get("name"),
            method="built_in_alias",
            market=market,
        )

    if _looks_like_direct_ticker(original):
        return TickerResolution(
            original_input=original,
            ticker=normalize_ticker(original, market=market),
            resolved_name=None,
            method="direct_ticker",
            market=market,
        )

    # 한글 입력은 KRX 검색을 먼저 시도합니다.
    krx_result = search_krx_by_name(original, market=market)
    if krx_result and krx_result.method == "krx_name_lookup":
        return krx_result

    yahoo_result = search_yahoo_symbol(original, market=market)
    if yahoo_result and yahoo_result.method == "yahoo_search":
        return yahoo_result

    warnings: List[str] = []
    for result in [krx_result, yahoo_result]:
        if result:
            warnings.extend(result.warnings)
    warnings.append("종목명 자동 변환에 실패했습니다. 입력값을 티커로 간주하고 실행합니다.")
    return TickerResolution(
        original_input=original,
        ticker=normalize_ticker(original, market=market),
        method="fallback_as_ticker",
        market=market,
        warnings=warnings,
    )
