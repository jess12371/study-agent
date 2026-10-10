# Script manual untuk menguji F-05 Adaptive Reschedule.
# Plan di-seed langsung ke DB; apply akan memanggil LLM (re-generate plan).
# Jalankan dari folder backend/: python scripts/test_reschedule.py

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
    "topic": "Mandarin Chinese",
    "current_level": "Beginner",
    "target": "HSK 3",
    "deadline_months": 3,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "evening",
    "max_session_minutes": 60,
}

# 2 minggu x 4 sesi = 8 sesi (mudah untuk 3 consecutive skipped).
PLAN_DATA = {
    "goal_summary": "Reach HSK 3 from beginner in 12 weeks.",
    "total_weeks": 2,
    "milestones": [
        {"month": 1, "focus": "Pinyin & tones", "target": "Master pinyin", "checkpoint": "Read aloud"},
    ],
    "weekly_schedule": [
        {"week": 1, "theme": "Pinyin", "days": [
            {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "Tones", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Tuesday", "date_offset": 1, "time": "19:00", "topic": "Initials", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Wednesday", "date_offset": 2, "time": "19:00", "topic": "Finals", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Thursday", "date_offset": 3, "time": "19:00", "topic": "Review", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
        ]},
        {"week": 2, "theme": "Basics", "days": [
            {"day": "Monday", "date_offset": 7, "time": "19:00", "topic": "Greetings", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Tuesday", "date_offset": 8, "time": "19:00", "topic": "Numbers", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Wednesday", "date_offset": 9, "time": "19:00", "topic": "Verbs", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
            {"day": "Thursday", "date_offset": 10, "time": "19:00", "topic": "Review", "duration_minutes": 60, "activities": ["Practice"], "resources": []},
        ]},
    ],
    "resources": [{"type": "app", "name": "HelloChinese", "url": "https://hellochinese.cc", "for_skill": "general"}],
}


def main() -> None:
    email = f"resched+{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post("/api/auth/signup", json={"email": email, "password": "supersecret123", "name": "Resched Tester"})
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]
    auth = {"Authorization": f"Bearer {token}"}

    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth)
    goal_id = goal.json()["id"]
    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal_id), user_id=uuid.UUID(user_id), plan_data=PLAN_DATA, status="active", version=1)
        db.add(plan)
        db.commit()
        db.refresh(plan)
        old_plan_id = str(plan.id)

    # Tandai 3 sesi berurutan sebagai skipped.
    for day in ("Monday", "Tuesday", "Wednesday"):
        client.patch(
            f"/api/plans/{old_plan_id}/progress",
            json={"week_number": 1, "day_name": day, "session_index": {"Monday": 0, "Tuesday": 1, "Wednesday": 2}[day], "status": "skipped"},
            headers=auth,
        )

    # Analyze.
    analysis = client.get(f"/api/plans/{old_plan_id}/reschedule/analyze", headers=auth)
    check("GET analyze -> 200", analysis.status_code == 200, f"status={analysis.status_code}")
    a = analysis.json()
    print("  should_reschedule:", a.get("should_reschedule"), "| weeks_behind:", a.get("weeks_behind"))
    print("  options:", [o["type"] for o in a.get("options", [])])
    check("should_reschedule True", a.get("should_reschedule") is True)
    check("options = 4", len(a.get("options", [])) == 4)
    check("semua tipe opsi ada", {o["type"] for o in a.get("options", [])} == {"REBALANCE", "EXTEND", "REDUCE", "INTENSIFY"})
    check("reason terisi", bool(a.get("reason")))

    # Apply (LLM re-generate; lambat).
    applied = client.post(
        f"/api/plans/{old_plan_id}/reschedule/apply",
        json={"option_type": "REBALANCE"},
        headers=auth,
    )
    check("POST apply -> 200", applied.status_code == 200, f"status={applied.status_code}")
    r = applied.json()
    print("  new plan:", r.get("plan_id"), "| version:", r.get("version"))
    print("  changes:", r.get("changes"))
    check("plan_id baru != lama", r.get("plan_id") != old_plan_id)
    check("version = 2", r.get("version") == 2)
    check("changes tidak kosong", len(r.get("changes", [])) >= 1)

    # DB: plan lama superseded + menunjuk ke plan baru.
    with SessionLocal() as db:
        old = db.get(StudyPlan, uuid.UUID(old_plan_id))
        new = db.get(StudyPlan, uuid.UUID(r["plan_id"])) if r.get("plan_id") else None
        check("plan lama status=superseded", old.status == "superseded", f"status={old.status}")
        check("plan lama superseded_by = plan baru", str(old.superseded_by) == r.get("plan_id"))
        check("plan baru version=2", new is not None and new.version == 2)

    # GET by-goal sekarang mengembalikan plan v2.
    by_goal = client.get(f"/api/plans/by-goal/{goal_id}", headers=auth)
    check("by-goal -> 200 (v2)", by_goal.status_code == 200 and by_goal.json().get("version") == 2, f"version={by_goal.json().get('version') if by_goal.status_code==200 else by_goal.status_code}")

    # Ownership.
    other = client.post("/api/auth/signup", json={"email": f"other+{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"}).json()["access_token"]
    r_other = client.get(f"/api/plans/{old_plan_id}/reschedule/analyze", headers={"Authorization": f"Bearer {other}"})
    check("user lain analyze -> 404", r_other.status_code == 404, f"status={r_other.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
