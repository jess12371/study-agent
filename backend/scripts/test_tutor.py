# Script manual untuk menguji Socratic Tutor streaming + Quiz dari jadwal.
# LLM di-monkeypatch agar cepat & deterministik.
# Jalankan dari folder backend/: python scripts/test_tutor.py

import json
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.study_plan import StudyPlan  # noqa: E402
from app.schemas.llm import LLMResponse, TokenUsage  # noqa: E402
from app.services import tutor_service  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# --- Mock LLM ---
async def fake_stream(prompt, system=None, **kwargs):
    yield "Great question. "
    yield "What do you think happens first when the loop starts?"
    yield " Try tracing one iteration."


async def fake_json(prompt, system=None, schema=None, **kwargs):
    data = {
        "questions": [
            {"question": "What does range(3) produce?", "options": ["0,1,2", "1,2,3", "0,1,2,3", "3"], "correct_index": 0, "explanation": "range(3) yields 0, 1, 2."},
            {"question": "Which loop repeats while a condition holds?", "options": ["for", "while", "if", "try"], "correct_index": 1, "explanation": "A while loop repeats while its condition is true."},
            {"question": "What exits a loop early?", "options": ["continue", "pass", "break", "return"], "correct_index": 2, "explanation": "break exits the loop immediately."},
        ]
    }
    return LLMResponse(
        content=json.dumps(data),
        usage=TokenUsage(),
        model="fake",
        latency_ms=1.0,
        data=data,
    )


tutor_service.llm.chat_completion_stream = fake_stream  # type: ignore[assignment]
tutor_service.llm.chat_completion_json = fake_json  # type: ignore[assignment]

PLAN_DATA = {
    "goal_summary": "x",
    "total_weeks": 4,
    "milestones": [],
    "weekly_schedule": [
        {
            "week": 1,
            "theme": "Setup",
            "days": [
                {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "For loops in Python", "duration_minutes": 60, "activities": [], "resources": []},
                {"day": "Tuesday", "date_offset": 1, "time": "19:00", "topic": "While loops", "duration_minutes": 60, "activities": [], "resources": []},
            ],
        }
    ],
    "resources": [],
}


def parse_sse(text: str) -> list[str]:
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            break
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "delta" and event.get("content"):
            chunks.append(event["content"])
    return chunks


def main() -> None:
    # --- Chat streaming ---
    r = client.post(
        "/api/tutor/chat",
        json={"topic": "Python loops", "question": "Why does my for loop skip items?"},
    )
    check("POST chat -> 200", r.status_code == 200, f"status={r.status_code}")
    check("content-type text/event-stream", "text/event-stream" in r.headers.get("content-type", ""))
    joined = "".join(parse_sse(r.text))
    print("  tutor:", joined[:110])
    check("jawaban berisi pertanyaan pemandu", "?" in joined)
    check("ada [DONE]", r.text.rstrip().endswith("[DONE]"))

    bad = client.post("/api/tutor/chat", json={"topic": "", "question": ""})
    check("input kosong -> 400", bad.status_code == 400, f"status={bad.status_code}")

    # --- Quiz dari jadwal ---
    unauth = client.post(
        "/api/tutor/chat",
        json={"mode": "quiz_from_schedule", "plan_id": str(uuid.uuid4()), "week_number": 1, "day_name": "Monday"},
    )
    check("quiz tanpa auth -> 401", unauth.status_code == 401, f"status={unauth.status_code}")

    email = f"quiz+{uuid.uuid4().hex[:8]}@example.com"
    token = client.post("/api/auth/signup", json={"email": email, "password": "Supersecret123", "name": "Quiz Tester"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=auth).json()["id"]

    goal = client.post(
        "/api/goals",
        json={
            "topic": "Python loops",
            "current_level": "Beginner",
            "target": "Understand loops",
            "deadline_months": 1,
            "work_hours_start": "09:00",
            "work_hours_end": "18:00",
            "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "preferred_study_time": "evening",
            "max_session_minutes": 60,
        },
        headers=auth,
    ).json()

    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal["id"]), user_id=uuid.UUID(user_id), plan_data=PLAN_DATA, status="active", version=1, reason="initial")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    quiz = client.post(
        "/api/tutor/chat",
        json={"mode": "quiz_from_schedule", "plan_id": plan_id, "week_number": 1, "day_name": "Monday"},
        headers=auth,
    )
    check("POST quiz -> 200", quiz.status_code == 200, f"status={quiz.status_code}")
    body = quiz.json()
    print("  quiz topic:", body.get("topic"), "| questions:", len(body.get("questions", [])))
    check("quiz punya 3 soal", len(body.get("questions", [])) == 3)
    check("topic sesuai jadwal", body.get("topic") == "For loops in Python")
    if body.get("questions"):
        q = body["questions"][0]
        check("soal punya 4 opsi", len(q["options"]) == 4)
        check("correct_index valid", 0 <= q["correct_index"] < len(q["options"]))
        check("ada explanation", bool(q["explanation"]))

    wrong = client.post(
        "/api/tutor/chat",
        json={"mode": "quiz_from_schedule", "plan_id": plan_id, "week_number": 1, "day_name": "Sunday"},
        headers=auth,
    )
    check("sesi tidak ada -> 404", wrong.status_code == 404, f"status={wrong.status_code}")

    missing = client.post(
        "/api/tutor/chat",
        json={"mode": "quiz_from_schedule", "plan_id": plan_id, "week_number": 1},
        headers=auth,
    )
    check("parameter kurang -> 400", missing.status_code == 400, f"status={missing.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
