# Script manual untuk menguji F-08 Export (PDF + ICS).
# Plan di-seed langsung ke DB (tanpa LLM) supaya test cepat.
# Jalankan dari folder backend/: python scripts/test_export.py

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
    "goal_summary": "Learn Python basics in 8 weeks with evening practice.",
    "total_weeks": 8,
    "milestones": [
        {"month": 1, "focus": "Syntax & variables", "target": "Write simple scripts", "checkpoint": "Build a calculator"},
        {"month": 2, "focus": "Files & functions", "target": "Handle files", "checkpoint": "Build a to-do list"},
    ],
    "weekly_schedule": [
        {
            "week": 1,
            "theme": "Setup and basics",
            "days": [
                {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "Install Python", "duration_minutes": 60, "activities": ["Install Python", "Write hello world"], "resources": [{"type": "website", "name": "Python.org", "url": "https://python.org", "for_skill": "setup"}]},
                {"day": "Tuesday", "date_offset": 1, "time": "19:30", "topic": "Variables", "duration_minutes": 45, "activities": ["Learn types"], "resources": []},
            ],
        },
        {
            "week": 2,
            "theme": "Loops",
            "days": [
                {"day": "Monday", "date_offset": 7, "time": "19:00", "topic": "For loops", "duration_minutes": 30, "activities": ["Practice loops"], "resources": []},
            ],
        },
    ],
    "resources": [
        {"type": "website", "name": "Python for Everybody", "url": "https://py4e.com", "for_skill": "general"},
    ],
}


def main() -> None:
    email = f"export+{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post("/api/auth/signup", json={"email": email, "password": "Supersecret123", "name": "Export Tester"})
    assert signup.status_code == 201, signup.text
    token = signup.json()["access_token"]
    user_id = signup.json()["user"]["id"]
    auth = {"Authorization": f"Bearer {token}"}

    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth)
    assert goal.status_code == 201, goal.text
    goal_id = goal.json()["id"]

    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal_id), user_id=uuid.UUID(user_id), plan_data=PLAN_DATA, status="active")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    # --- PDF ---
    pdf = client.get(f"/api/plans/{plan_id}/export/pdf", headers=auth)
    check("GET export/pdf -> 200", pdf.status_code == 200, f"status={pdf.status_code}")
    check("content-type application/pdf", "application/pdf" in pdf.headers.get("content-type", ""))
    check("body mulai dengan %PDF", pdf.content[:4] == b"%PDF", f"head={pdf.content[:4]!r}")
    check("PDF punya ukuran wajar", len(pdf.content) > 1500, f"bytes={len(pdf.content)}")
    check("Content-Disposition attachment", "attachment" in pdf.headers.get("content-disposition", ""))

    # --- ICS ---
    ics = client.get(f"/api/plans/{plan_id}/export/ics", headers=auth)
    check("GET export/ics -> 200", ics.status_code == 200, f"status={ics.status_code}")
    check("content-type text/calendar", "text/calendar" in ics.headers.get("content-type", ""))
    text = ics.text
    check("ICS punya BEGIN:VCALENDAR", "BEGIN:VCALENDAR" in text)
    check("ICS punya VEVENT", "BEGIN:VEVENT" in text)
    check("ICS punya VERSION:2.0", "VERSION:2.0" in text)
    check("jumlah VEVENT = 3", text.count("BEGIN:VEVENT") == 3, f"n={text.count('BEGIN:VEVENT')}")
    check("VEVENT punya SUMMARY sesi", "[Study] Install Python" in text)
    check("VEVENT punya DTSTART", "DTSTART" in text)

    # Alias endpoint sesuai spesifikasi: /export-ics
    ics_alias = client.get(f"/api/plans/{plan_id}/export-ics", headers=auth)
    check("GET export-ics (alias) -> 200", ics_alias.status_code == 200, f"status={ics_alias.status_code}")
    check("alias mengembalikan iCalendar", "BEGIN:VCALENDAR" in ics_alias.text)

    # --- Error handling ---
    other = client.post("/api/auth/signup", json={"email": f"other+{uuid.uuid4().hex[:8]}@example.com", "password": "Supersecret123"}).json()["access_token"]
    r_other = client.get(f"/api/plans/{plan_id}/export/pdf", headers={"Authorization": f"Bearer {other}"})
    check("user lain export -> 404", r_other.status_code == 404, f"status={r_other.status_code}")
    r_missing = client.get(f"/api/plans/{uuid.uuid4()}/export/pdf", headers=auth)
    check("plan tidak ada -> 404", r_missing.status_code == 404, f"status={r_missing.status_code}")
    r_noauth = client.get(f"/api/plans/{plan_id}/export/pdf")
    check("tanpa token -> 401", r_noauth.status_code == 401, f"status={r_noauth.status_code}")

    # Simpan file contoh untuk inspeksi manual.
    out_dir = Path(__file__).resolve().parents[1] / "scripts" / "output"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "sample-plan.pdf").write_bytes(pdf.content)
    (out_dir / "sample-plan.ics").write_text(text, encoding="utf-8")
    print(f"  sample files saved to {out_dir}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
