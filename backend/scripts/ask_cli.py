"""Phase 3 full-pipeline test script -- no HTTP layer.

Usage: python -m scripts.ask_cli "If I can run a half marathon in 1:30 but smoke a pack
a day, what does that say about my health?"
"""

from __future__ import annotations

import asyncio
import sys

from app.llm.factory import get_llm_provider
from app.pipeline.orchestrator import run_pipeline


async def run(question: str) -> None:
    llm = get_llm_provider()
    async for event in run_pipeline(llm, question):
        if event.type == "decomposition":
            print("=== Sub-topics ===")
            for st in event.data["subtopics"]:
                print(f"- {st['label']}: {st['search_query']}\n  ({st['rationale']})")
            print()
        elif event.type == "sources":
            print(f"=== {len(event.data['papers'])} papers retrieved ===\n")
        elif event.type == "token":
            print(event.data["text"], end="", flush=True)
        elif event.type == "done":
            print("\n\n=== Citations ===")
            for c in event.data["citations"]:
                print(f"[{c['key']}] {c['title']} ({c['year']}) {c['link']} -- {len(c['excerpts'])} excerpt(s)")
                for e in c["excerpts"]:
                    print(f"    ({e['section']}) {e['text'][:120]}...")
        elif event.type == "error":
            print(f"\n[ERROR] {event.data['message']}")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or (
        "If I can run a half marathon in 1:30 but I smoke a pack of cigarettes a day, "
        "how is this going to impact my health?"
    )
    asyncio.run(run(question))
