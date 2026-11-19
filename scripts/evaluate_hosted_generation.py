"""Capture real HTTPS traces; never turn fallback or fixtures into LLM evidence."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.evaluate_knowledge import (
    QUESTIONS,
)  # pylint: disable=wrong-import-position


def main():
    """Public hosted calls consume normal budgets and may cost money if enabled."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--origin", default="https://amman-app.134-209-120-185.sslip.io"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-paid-generation", action="store_true")
    args = parser.parse_args()
    if not args.origin.startswith("https://"):
        parser.error("Use a public HTTPS origin.")
    with httpx.Client(timeout=40, follow_redirects=False, trust_env=False) as client:
        sources = client.get(args.origin.rstrip("/") + "/api/knowledge/sources")
        sources.raise_for_status()
        state = sources.json()
        if state.get("generation_status") == "ready" and not args.allow_paid_generation:
            parser.error(
                "Generation is enabled; explicit --allow-paid-generation required."
            )
        results = []
        for index, question in enumerate(QUESTIONS, 1):
            response = client.post(
                args.origin.rstrip("/") + "/api/knowledge/query",
                json={"question": question},
            )
            results.append(
                {
                    "case": f"Q{index}",
                    "question": question,
                    "http_status": response.status_code,
                    "response": response.json(),
                }
            )
    live = all(
        r["http_status"] == 200
        and r["response"].get("mode") == "llm_generated"
        and r["response"].get("supported")
        for r in results[:4]
    )
    abstained = results[4]["http_status"] == 200 and not results[4]["response"].get(
        "supported"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "origin": args.origin,
                "sources": state,
                "results": results,
                "q1_q4_actual_llm_generation": live,
                "q5_abstained": abstained,
                "human_claim_support_review": "Pending. Schema and citation checks do not establish semantic correctness.",
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"Saved actual traces. Q1-Q4 LLM-generated: {live}; Q5 abstained: {abstained}"
    )
    if args.allow_paid_generation and not (live and abstained):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
