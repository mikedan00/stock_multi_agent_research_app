from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re


def slugify(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", text).strip("_")
    return text[:80] or "report"


def save_markdown(report: str, output_dir: str | Path = "outputs", name_hint: str = "stock_report") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{slugify(name_hint)}_{stamp}.md"
    path.write_text(report, encoding="utf-8")
    return path
