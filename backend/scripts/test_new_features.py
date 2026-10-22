# Test fitur baru: OTP, re-scope, dan lazy next-month (LLM di-mock).
# Jalankan dari folder backend/: python scripts/test_new_features.py

import json
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.study_plan import StudyPlan  # noqa: E402
from app.models.user import User  # noqa: E402
from app.schemas.llm import LLMResponse, TokenUsage  # noqa: E402
from app.services import llm  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def _response(data: dict) -> LLMResponse:
    return LLMResponse(content=json.dumps(data), usage=TokenUsage(), model="fake", latency_ms=1.0, data=data)


async def fake_json(prompt, system=None, schema=None, **kwargs):
    name = getattr(schema, "__name__", "")
    if name == "_LLMRescopeOutput":
        return _response({
            "target": "HSK 3 (re-scoped)",
            "deadline_months": 12,
            "rationale": "More time is needed for a realistic pace.",
            "changes": ["Deadline extended to 12 months", "Target lowered to HSK 3"],
        })
    if name == "_LLMNextMonthOutput":
        return _response({
            "weeks": [
                {
                    "week": week,
                    "theme": f"Month 2 week {week}",
                    "days": [
                        {
                            "day": "Monday",
                            "date_offset": (week - 1) * 7,
                            "time": "19:00",
                            "topic": f"Topic week {week}",
                            "duration_minutes": 60,
                            "activities": ["Practice"],
                            "resources": [],
                        }
                    ],
                }
                for week in range(5, 9)
            ]
        })
    return _response({"message": "ok", "actions": []})


llm.chat_completion_json = fake_json  # type: ignore[assignment]

PLAN_DATA = {
    "goal_summary": "x",
    "total_weeks": 12,
    "milestones": [
        {"month": 1, "focus": "Basics", "target": "t1", "checkpoint": "c1"},
        {"month": 2, "focus": "Next", "target": "t2", "checkpoint": "c2"},
    ],
    "weekly_schedule": [
        {
            "week": week,
            "theme": f"Week {week}",
            "days": [
                {"day": "Monday", "date_offset": (week - 1) * 7, "time": "19:00", "topic": "x", "duration_minutes": 60, "activities": [], "resources": []}
            ],
        }
        for week in range(1, 5)
    ],
    "resources": [],
}


def main() -> None:
    # --- Password validation ---
    weak = client.post("/api/auth/signup", json={"email": f"weak+{uuid.uuid4().hex[:6]}@example.com", "password": "alllowercase1"})
    check("password tanpa huruf besar -> 400", weak.status_code == 400, f"status={weak.status_code}")

    # --- OTP flow ---
    email = f"otp+{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post("/api/auth/signup", json={"email": email, "password": "Supersecret123", "name": "OTP Tester"})
    check("signup -> 201", signup.status_code == 201, f"status={signup.status_code}")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        otp = user.otp_code if user else None
        verified_before = user.is_verified if user else None
    check("OTP 6 digit tersimpan", bool(otp) and len(otp) == 6, f"otp={otp}")
    check("user belum verified", verified_before is False)

    wrong = client.post("/api/auth/verify-otp", json={"email": email, "otp": "000000"})
    check("OTP salah -> 400", wrong.status_code == 400, f"status={wrong.status_code}")
    ok = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp})
    check("OTP benar -> 200 + token", ok.status_code == 200 and "access_token" in ok.json())
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        check("user terverifikasi", bool(user.is_verified))
    check("resend OTP -> 200", client.post("/api/auth/resend-otp", json={"email": email}).status_code == 200)

    # --- Re-scope ---
    goal_payload = {
        "topic": "Mandarin", "current_level": "Beginner", "target": "HSK 4",
        "deadline_months": 6, "work_hours_start": "09:00", "work_hours_end": "18:00",
        "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "preferred_study_time": "evening", "max_session_minutes": 60,
    }
    feasibility = {
        "feasible": False, "confidence": 0.9, "required_hours": 700,
        "available_hours": 274, "gap_hours": 426, "verdict": "UNREALISTIC",
        "analysis": "Too ambitious.", "recommendations": ["Extend deadline", "Lower target"],
        "benchmark_source": "estimate", "requires_manual_review": False,
    }
    rescope = client.post("/api/feasibility/rescope", json={"goal": goal_payload, "feasibility": feasibility})
    check("rescope -> 200", rescope.status_code == 200, f"status={rescope.status_code}")
    body = rescope.json()
    check("rescope menambah deadline", body.get("deadline_months", 0) >= 6, f"deadline={body.get('deadline_months')}")
    check("rescope punya changes", len(body.get("changes", [])) >= 1)
    check("rescope punya target baru", bool(body.get("target")))

    # --- Lazy next month ---
    token = ok.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=auth).json()["id"]
    goal = client.post("/api/goals", json=goal_payload | {"topic": "Mandarin"}, headers=auth).json()
    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal["id"]), user_id=uuid.UUID(user_id), plan_data=PLAN_DATA, status="active", version=1, reason="initial")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    nxt = client.post(f"/api/plans/{plan_id}/generate-next-month", json={"language": "en"}, headers=auth)
    check("next-month -> 200", nxt.status_code == 200, f"status={nxt.status_code}")
    weeks = nxt.json().get("weekly_schedule", [])
    print("  weeks after next-month:", [w["week"] for w in weeks])
    check("total minggu menjadi 8", len(weeks) == 8, f"n={len(weeks)}")
    check("minggu 5-8 ditambahkan", [w["week"] for w in weeks] == list(range(1, 9)))
    check("next-month tanpa auth -> 401", client.post(f"/api/plans/{plan_id}/generate-next-month", json={}).status_code == 401)

    passed = sum(1 for _, ok_, _ in results if ok_)
    failed = [name for name, ok_, _ in results if not ok_]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
