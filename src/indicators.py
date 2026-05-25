from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_last(series: pd.Series):
    if series is None or len(series.dropna()) == 0:
        return None
    value = series.dropna().iloc[-1]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return float(value)


def compute_technical_indicators(history: pd.DataFrame) -> dict:
    if history is None or history.empty or "Close" not in history.columns:
        return {"status": "가격 데이터 확인 필요"}

    df = history.copy()
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float) if "Volume" in df.columns else pd.Series(index=df.index, dtype=float)

    for window in [5, 20, 60, 120, 200]:
        df[f"MA{window}"] = close.rolling(window).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    ma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    upper = ma20 + 2 * std20
    lower = ma20 - 2 * std20

    current = _safe_last(close)
    vol20 = volume.rolling(20).mean()
    volume_ratio = None
    if _safe_last(vol20) and _safe_last(volume):
        volume_ratio = _safe_last(volume) / _safe_last(vol20)

    def pct_return(days: int):
        if len(close.dropna()) <= days:
            return None
        try:
            return float(close.iloc[-1] / close.iloc[-days - 1] - 1)
        except Exception:
            return None

    high_52w = float(close.tail(252).max()) if len(close) else None
    low_52w = float(close.tail(252).min()) if len(close) else None
    position_52w = None
    if current and high_52w and low_52w and high_52w != low_52w:
        position_52w = (current - low_52w) / (high_52w - low_52w)

    above = {}
    for w in [20, 60, 120, 200]:
        ma = _safe_last(df[f"MA{w}"])
        above[f"above_ma{w}"] = None if current is None or ma is None else current > ma

    trend_score = 0
    for k, v in above.items():
        if v is True:
            trend_score += 1
        elif v is False:
            trend_score -= 1

    if trend_score >= 3:
        trend = "상승추세"
    elif trend_score <= -3:
        trend = "하락추세"
    else:
        trend = "중립/횡보"

    return {
        "status": "ok",
        "current_price": current,
        "ma5": _safe_last(df["MA5"]),
        "ma20": _safe_last(df["MA20"]),
        "ma60": _safe_last(df["MA60"]),
        "ma120": _safe_last(df["MA120"]),
        "ma200": _safe_last(df["MA200"]),
        "rsi14": _safe_last(rsi),
        "macd": _safe_last(macd),
        "macd_signal": _safe_last(macd_signal),
        "bollinger_upper": _safe_last(upper),
        "bollinger_middle": _safe_last(ma20),
        "bollinger_lower": _safe_last(lower),
        "volume_ratio_20d": volume_ratio,
        "return_1m": pct_return(21),
        "return_3m": pct_return(63),
        "return_6m": pct_return(126),
        "return_12m": pct_return(252),
        "return_ytd": float(close.iloc[-1] / close[close.index.year == close.index[-1].year].iloc[0] - 1) if len(close[close.index.year == close.index[-1].year]) else None,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "position_52w": position_52w,
        "trend": trend,
        **above,
    }
