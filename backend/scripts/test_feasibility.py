# Script manual untuk menguji F-02 Goal Feasibility Check.
# Jalankan dari folder backend/: python scripts/test_feasibility.py

import asyncio
import logging
import sys
from pathlib import Path

# Tambahkan root backend ke sys.path agar `app` bisa di-import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.feasibility import FeasibilityRequest  # noqa: E402
from app.services.feasibility_service import (  # noqa: E402
    check_feasibility_with_meta,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Tiga skenario uji.
TEST_CASES = [
    {
        "name": "Test 1 — Mandarin HSK 4 in 6 months (expected: REALISTIC_WITH_NOTES)",
        "request": FeasibilityRequest(
            topic="Mandarin Chinese",
            current_level="Absolute beginner",
            target="HSK 4 with a score of 250",
            deadline_months=6,
            work_hours_start="09:00",
            work_hours_end="18:00",
            work_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            preferred_study_time="evening",
            max_session_minutes=90,
        ),
    },
    {
        "name": "Test 2 — Mandarin HSK 6 in 1 month (expected: UNREALISTIC + recommendations)",
        "request": FeasibilityRequest(
            topic="Mandarin Chinese",
            current_level="Absolute beginner",
            target="HSK 6",
            deadline_months=1,
            work_hours_start="09:00",
            work_hours_end="18:00",
            work_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            preferred_study_time="evening",
            max_session_minutes=90,
        ),
    },
    {
        "name": "Test 3 — Python basics in 2 months (expected: REALISTIC)",
        "request": FeasibilityRequest(
            topic="Python programming",
            current_level="No programming experience",
            target="Comfortable writing basic scripts (variables, loops, functions, files)",
            deadline_months=2,
            work_hours_start="09:00",
            work_hours_end="18:00",
            work_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
            preferred_study_time="morning",
            max_session_minutes=60,
        ),
    },
]


async def run_case(case: dict) -> None:
    print("\n" + "=" * 70)
    print(case["name"])
    print("=" * 70)
    request: FeasibilityRequest = case["request"]
    print("REQUEST:", request.model_dump())

    response, meta = await check_feasibility_with_meta(request)

    print("\nRESPONSE:")
    print(response.model_dump_json(indent=2))
    print("\nMETA:")
    print("  model:", meta.model)
    print("  latency_ms:", meta.latency_ms)
    print("  usage:", meta.usage.model_dump())


async def main() -> None:
    for case in TEST_CASES:
        await run_case(case)
    print("\nDone. All test cases finished without exception.")


if __name__ == "__main__":
    asyncio.run(main())
