from __future__ import annotations

import argparse
from dotenv import load_dotenv

from src.llm_clients import build_llm_client
from src.orchestrator import StockAnalysisOrchestrator, compare_summary
from src.exporters import save_markdown


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run multi-agent stock research analysis")
    parser.add_argument("--tickers", nargs="+", required=True, help="Stock names or tickers: 삼성전자 엔비디아 005930.KS NVDA. Use quotes for names with spaces.")
    parser.add_argument("--market", default="AUTO", choices=["AUTO", "KOSPI", "KOSDAQ"])
    parser.add_argument("--period", default="1y", choices=["6mo", "1y", "2y", "5y", "max"])
    parser.add_argument("--provider", default="none", choices=["none", "huggingface", "hf", "anthropic", "openai-compatible"])
    parser.add_argument("--api-key", default=None, help="HF_TOKEN, ANTHROPIC_API_KEY, or OpenAI-compatible API key. If omitted, .env/env vars are used.")
    parser.add_argument("--base-url", default=None, help="HF router URL, Anthropic messages URL, or OpenAI-compatible base URL.")
    parser.add_argument("--model", default=None, help="Model name. Example: google/gemma-4-26B-A4B-it")
    parser.add_argument("--hf-provider", default=None, help="HF Inference Provider routing. Example: auto, novita, deepinfra, hf-inference")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--no-parallel", action="store_true")
    args = parser.parse_args()

    client = build_llm_client(
        args.provider,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        hf_provider=args.hf_provider,
    )
    orchestrator = StockAnalysisOrchestrator(agent_dir="agents", llm_client=client, parallel=not args.no_parallel)
    results = orchestrator.analyze_many(args.tickers, market=args.market, period=args.period)

    if len(results) > 1:
        print("\n# 종목 비교 요약\n")
        print(compare_summary(results))

    for result in results:
        path = save_markdown(result.report, output_dir=args.output_dir, name_hint=result.ticker)
        print(f"\nSaved: {path}")
        print(result.report[:2000])
        print("\n...\n")


if __name__ == "__main__":
    main()
