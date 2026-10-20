# Script manual untuk menguji gamifikasi quiz (submit + history).
# Jalankan dari folder backend/: python scripts/test_quiz_history.py

import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.study_plan import StudyPlan  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


GOAL_PAYLOAD = {
    "topic": "Python loops",
    "current_level": "Beginner",
    "target": "Master loops",
    "deadline_months": 1,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "evening",
    "max_session_minutes": 60,
}


def main() -> None:
    email = f"gamify+{uuid.uuid4().hex[:8]}@example.com"
    token = client.post("/api/auth/signup", json={"email": email, "password": "supersecret123", "name": "Gamify Tester"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=auth).json()["id"]
    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth).json()

    with SessionLocal() as db:
        plan = StudyPlan(
            goal_id=uuid.UUID(goal["id"]),
            user_id=uuid.UUID(user_id),
            plan_data={"goal_summary": "x", "total_weeks": 4, "milestones": [], "weekly_schedule": [], "resources": []},
            status="active",
            version=1,
            reason="initial",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    # Submit 3/3
    r1 = client.post(
        "/api/quizzes/submit",
        json={"plan_id": plan_id, "week_number": 1, "day_name": "Monday", "score": 3, "total_questions": 3},
        headers=auth,
    )
    check("submit 3/3 -> 201", r1.status_code == 201, f"status={r1.status_code}")
    check("skor tersimpan 3/3", r1.json().get("score") == 3 and r1.json().get("total_questions") == 3)

    # Submit 2/3
    r2 = client.post(
        "/api/quizzes/submit",
        json={"plan_id": plan_id, "week_number": 1, "day_name": "Tuesday", "score": 2, "total_questions": 3},
        headers=auth,
    )
    check("submit 2/3 -> 201", r2.status_code == 201, f"status={r2.status_code}")

    # History + stats
    hist = client.get("/api/quizzes/history", headers=auth)
    check("history -> 200", hist.status_code == 200, f"status={hist.status_code}")
    body = hist.json()
    print("  history:", body.get("total_quizzes"), "quizzes | avg:", body.get("average_score"), "| best:", body.get("best_score"))
    check("total_quizzes = 2", body.get("total_quizzes") == 2)
    check("average_score = 83.3", abs(body.get("average_score", 0) - 83.3) < 0.2, f"avg={body.get('average_score')}")
    check("best_score = 100", body.get("best_score") == 100)
    check("attempts terbaru dulu", body["attempts"][0]["day_name"] == "Tuesday")
    check("goal_topic terisi", body["attempts"][0]["goal_topic"] == "Python loops")

    # Validasi
    bad = client.post(
        "/api/quizzes/submit",
        json={"plan_id": plan_id, "week_number": 1, "day_name": "Monday", "score": 5, "total_questions": 3},
        headers=auth,
    )
    check("score > total -> 400", bad.status_code == 400, f"status={bad.status_code}")

    # Ownership
    other = client.post("/api/auth/signup", json={"email": f"o+{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"}).json()["access_token"]
    other_auth = {"Authorization": f"Bearer {other}"}
    r_other = client.post(
        "/api/quizzes/submit",
        json={"plan_id": plan_id, "week_number": 1, "day_name": "Monday", "score": 1, "total_questions": 3},
        headers=other_auth,
    )
    check("plan user lain -> 404", r_other.status_code == 404, f"status={r_other.status_code}")
    check("history user lain kosong", client.get("/api/quizzes/history", headers=other_auth).json()["total_quizzes"] == 0)

    check("submit tanpa token -> 401", client.post("/api/quizzes/submit", json={"plan_id": plan_id, "week_number": 1, "day_name": "Monday", "score": 1, "total_questions": 3}).status_code == 401)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
