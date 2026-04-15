from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from examples.production_coding_agent.app.benchmark import run_benchmark


async def main() -> None:
    results = await run_benchmark()
    passed = sum(1 for item in results if item.passed)
    total = len(results)
    print(f"[BENCHMARK] passed={passed}/{total}")
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"\n[{status}] {item.task_id}")
        print(f"  summary: {item.summary}")
        print(f"  matched_files: {item.matched_files}")
        print(f"  artifacts: {item.artifacts}")
        if item.notes:
            print("  notes:")
            for note in item.notes:
                print(f"    - {note}")


if __name__ == "__main__":
    asyncio.run(main())
