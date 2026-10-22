# Script manual untuk menguji F-04 Progress Tracker.
# Plan di-seed langsung ke DB (tanpa LLM) supaya test cepat & deterministik.
# Jalankan dari folder backend/: python scripts/test_progress.py

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
    "topic": "Python programming",
    "current_level": "None",
    "target": "Write basic scripts",
    "deadline_months": 2,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "evening",
    "max_session_minutes": 60,
}

PLAN_DATA = {
    "goal_summary": "Seeded plan for progress testing.",
    "total_weeks": 2,
    "milestones": [{"month": 1, "focus": "Basics", "target": "t", "checkpoint": "c"}],
    "weekly_schedule": [
        {
            "week": 1,
            "theme": "Setup",
            "days": [
                {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "Install", "duration_minutes": 60, "activities": [], "resources": []},
                {"day": "Tuesday", "date_offset": 1, "time": "19:00", "topic": "Variables", "duration_minutes": 45, "activities": [], "resources": []},
            ],
        },
        {
            "week": 2,
            "theme": "Loops",
            "days": [
                {"day": "Monday", "date_offset": 7, "time": "19:00", "topic": "For loops", "duration_minutes": 30, "activities": [], "resources": []},
            ],
        },
    ],
    "resources": [],
}


def main() -> None:
    email = f"progress+{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post("/api/auth/signup", json={"email": email, "password": "Supersecret123", "name": "Progress Tester"})
    assert signup.status_code == 201, signup.text
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]
    auth = {"Authorization": f"Bearer {token}"}

    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth)
    assert goal.status_code == 201, goal.text
    goal_id = goal.json()["id"]

    # Seed plan langsung ke DB.
    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal_id), user_id=uuid.UUID(user_id), plan_data=PLAN_DATA, status="active")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    def mark(week, day, index, status, actual=None):
        return client.patch(
            f"/api/plans/{plan_id}/progress",
            json={"week_number": week, "day_name": day, "session_index": index, "status": status, "actual_duration": actual},
            headers=auth,
        )

    # Tandai 2 sesi completed.
    r1 = mark(1, "Monday", 0, "completed", 60)
    check("PATCH mark session -> 200", r1.status_code == 200, f"status={r1.status_code}")
    check("entry status completed", r1.json().get("status") == "completed")
    check("completed_at terisi", r1.json().get("completed_at") is not None)
    mark(1, "Tuesday", 1, "completed", 50)

    # Upsert (ubah sesi yang sama).
    r2 = mark(1, "Monday", 0, "completed", 65)
    check("upsert tidak membuat duplikat", r2.json().get("id") == r1.json().get("id"))

    # List.
    lst = client.get(f"/api/plans/{plan_id}/progress", headers=auth)
    check("GET list -> 200", lst.status_code == 200)
    check("list berisi 2 entry", len(lst.json()) == 2, f"n={len(lst.json())}")

    # Stats.
    stats = client.get(f"/api/plans/{plan_id}/progress/stats", headers=auth).json()
    print("  stats:", stats)
    check("total_sessions = 3", stats["total_sessions"] == 3)
    check("completed = 2", stats["completed"] == 2)
    check("pending = 1", stats["pending"] == 1)
    check("current_streak = 2", stats["current_streak"] == 2)
    check("longest_streak = 2", stats["longest_streak"] == 2)
    check("completion_rate ~ 0.667", abs(stats["completion_rate"] - 0.667) < 0.01)
    check("total_hours > 0", stats["total_hours"] > 0)

    # Skip sesi terakhir → streak reset.
    mark(2, "Monday", 0, "skipped")
    stats2 = client.get(f"/api/plans/{plan_id}/progress/stats", headers=auth).json()
    print("  stats after skip:", stats2)
    check("skipped = 1", stats2["skipped"] == 1)
    check("pending = 0", stats2["pending"] == 0)
    check("current_streak reset = 0", stats2["current_streak"] == 0)
    check("longest_streak tetap 2", stats2["longest_streak"] == 2)

    # Ownership: user lain tidak bisa akses.
    other = client.post("/api/auth/signup", json={"email": f"other+{uuid.uuid4().hex[:8]}@example.com", "password": "Supersecret123"}).json()["access_token"]
    r3 = client.get(f"/api/plans/{plan_id}/progress", headers={"Authorization": f"Bearer {other}"})
    check("user lain GET progress -> 404", r3.status_code == 404, f"status={r3.status_code}")

    # Reset.
    rst = client.post(f"/api/plans/{plan_id}/progress/reset", headers=auth)
    check("POST reset -> 204", rst.status_code == 204, f"status={rst.status_code}")
    stats3 = client.get(f"/api/plans/{plan_id}/progress/stats", headers=auth).json()
    check("setelah reset, completed = 0", stats3["completed"] == 0)
    check("setelah reset, completion_rate = 0", stats3["completion_rate"] == 0)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
