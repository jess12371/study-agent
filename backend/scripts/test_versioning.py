# Script manual untuk menguji plan VERSIONING (F-05 + regenerate).
# LLM di-monkeypatch agar test cepat & deterministik.
# Jalankan dari folder backend/: python scripts/test_versioning.py

import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import plan_service  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


# --- Monkeypatch LLM plan generation (tidak memanggil DeepSeek) ---
async def fake_generate(request, extra_notes=None, *, reasoning_effort=None):
    return plan_service._LLMPlanOutput(
        goal_summary="Test plan (fake)",
        total_weeks=8,
        milestones=[
            {"month": 1, "focus": "Basics", "target": "t", "checkpoint": "c"},
        ],
        weekly_schedule=[
            {
                "week": 1,
                "theme": "Setup",
                "days": [
                    {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "Intro", "duration_minutes": 60, "activities": ["a"], "resources": []},
                ],
            }
        ],
        resources=[],
    )


plan_service.generate_plan_output = fake_generate  # type: ignore[assignment]


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

FEASIBILITY = {
    "feasible": True,
    "confidence": 0.8,
    "required_hours": 65,
    "available_hours": 91,
    "gap_hours": -26,
    "verdict": "REALISTIC",
    "analysis": "Achievable.",
    "recommendations": ["Practice daily"],
    "benchmark_source": "estimate",
    "requires_manual_review": False,
}


def main() -> None:
    email = f"version+{uuid.uuid4().hex[:8]}@example.com"
    signup = client.post("/api/auth/signup", json={"email": email, "password": "supersecret123", "name": "Version Tester"})
    token = signup.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth).json()
    goal_id = goal["id"]

    # 1) Generate v1
    r1 = client.post("/api/plans/generate", json={"goal_id": goal_id, "feasibility_result": FEASIBILITY}, headers=auth)
    v1 = r1.json()
    check("generate -> 200", r1.status_code == 200, f"status={r1.status_code}")
    check("v1 version=1", v1.get("version") == 1, f"version={v1.get('version')}")
    check("v1 reason=initial", v1.get("reason") == "initial")
    check("v1 status=active", v1.get("status") == "active")

    # 2) Reschedule -> v2
    r2 = client.post(f"/api/plans/{v1['plan_id']}/reschedule/apply", json={"option_type": "REBALANCE"}, headers=auth)
    v2 = r2.json()
    check("reschedule -> 200", r2.status_code == 200, f"status={r2.status_code}")
    check("v2 version=2", v2.get("version") == 2, f"version={v2.get('version')}")

    # 3) Regenerate -> v3 (bug lama: v3 jadi v1 & v2 hilang)
    r3 = client.post("/api/plans/generate", json={"goal_id": goal_id, "feasibility_result": FEASIBILITY}, headers=auth)
    v3 = r3.json()
    check("regenerate -> 200", r3.status_code == 200, f"status={r3.status_code}")
    check("regenerate version=3 (bukan 1)", v3.get("version") == 3, f"version={v3.get('version')}")
    check("regenerate reason=regenerate", v3.get("reason") == "regenerate")

    # 4) History: semua versi ada
    hist = client.get(f"/api/plans/by-goal/{goal_id}/history", headers=auth)
    check("history -> 200", hist.status_code == 200, f"status={hist.status_code}")
    versions = hist.json()
    print("  history:", [(h["version"], h["status"], h["reason"]) for h in versions])
    check("history punya 3 versi", len(versions) == 3, f"n={len(versions)}")
    check("urutan v1,v2,v3", [h["version"] for h in versions] == [1, 2, 3])
    check("v1 superseded", versions[0]["status"] == "superseded" and versions[0]["reason"] == "initial")
    check("v2 superseded (tidak hilang)", versions[1]["status"] == "superseded" and versions[1]["reason"] == "reschedule")
    check("v3 active", versions[2]["status"] == "active" and versions[2]["reason"] == "regenerate")
    check("plan_id tiap versi berbeda", len({h["plan_id"] for h in versions}) == 3)

    # 5) by-goal?version=N
    got_v2 = client.get(f"/api/plans/by-goal/{goal_id}?version=2", headers=auth)
    check("by-goal?version=2 -> v2", got_v2.status_code == 200 and got_v2.json()["version"] == 2, f"status={got_v2.status_code}")
    check("by-goal?version=2 plan_id benar", got_v2.json()["plan_id"] == v2["plan_id"])
    latest = client.get(f"/api/plans/by-goal/{goal_id}", headers=auth)
    check("by-goal (tanpa version) -> v3", latest.json()["version"] == 3)
    check("by-goal?version=99 -> 404", client.get(f"/api/plans/by-goal/{goal_id}?version=99", headers=auth).status_code == 404)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
