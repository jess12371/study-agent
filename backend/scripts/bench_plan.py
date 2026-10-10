# Benchmark latency + token usage untuk plan generation (F-03 / F-05 apply).
# Jalankan dari folder backend/: python scripts/bench_plan.py

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.feasibility import FeasibilityRequest, FeasibilityResponse  # noqa: E402
from app.schemas.plan import PlanRequest  # noqa: E402
from app.services import llm, plan_service  # noqa: E402


def build_request() -> PlanRequest:
    goal = FeasibilityRequest(
        topic="Python programming",
        current_level="No programming experience",
        target="Comfortable writing basic scripts",
        deadline_months=3,
        work_hours_start="09:00",
        work_hours_end="18:00",
        work_days=["monday", "tuesday", "wednesday", "thursday", "friday"],
        preferred_study_time="evening",
        max_session_minutes=60,
    )
    feasibility = FeasibilityResponse(
        feasible=True,
        confidence=0.85,
        required_hours=80,
        available_hours=91,
        gap_hours=-11,
        verdict="REALISTIC",
        analysis="80 hours needed vs 91 available; achievable with steady practice.",
        recommendations=["Practice 5 sessions/week", "Build small projects"],
        benchmark_source="estimate",
    )
    return PlanRequest(goal=goal, feasibility_result=feasibility)


async def main() -> None:
    request = build_request()
    max_tokens = getattr(plan_service, "PLAN_MAX_TOKENS", None)
    reasoning = getattr(plan_service, "PLAN_REASONING_EFFORT", "high")
    detailed_weeks = getattr(plan_service, "DETAILED_WEEKS", "?")
    print(
        f"config: DETAILED_WEEKS={detailed_weeks} PLAN_MAX_TOKENS={max_tokens} "
        f"reasoning_effort={reasoning}"
    )

    start = time.perf_counter()
    response = await llm.chat_completion_json(
        plan_service._build_user_prompt(request),
        system=plan_service._build_system_prompt(),
        schema=plan_service._LLMPlanOutput,
        temperature=0.7,
        max_tokens=max_tokens,
        reasoning_effort=reasoning,
        thinking=True,
    )
    latency = time.perf_counter() - start
    output = plan_service._LLMPlanOutput.model_validate(response.data)

    print(f"latency_seconds={latency:.1f}")
    print(f"finish_reason={response.finish_reason}")
    print(f"usage={response.usage.model_dump()}")
    print(
        f"output: total_weeks={output.total_weeks} milestones={len(output.milestones)} "
        f"weeks_detailed={len(output.weekly_schedule)} resources={len(output.resources)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
