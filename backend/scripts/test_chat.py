# Script manual untuk menguji F-11 Agent Dialog.
# LLM di-monkeypatch agar cepat & deterministik.
# Jalankan dari folder backend/: python scripts/test_chat.py

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
from app.models.resource import Resource  # noqa: E402
from app.models.study_plan import StudyPlan  # noqa: E402
from app.schemas.llm import LLMResponse, TokenUsage  # noqa: E402
from app.services import llm, plan_service  # noqa: E402

logging.basicConfig(level=logging.WARNING)
client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


with SessionLocal() as db:
    resource = db.scalar(select(Resource).limit(1))
    RESOURCE_ID = str(resource.id) if resource else None
    RESOURCE_NAME = resource.name if resource else None

GOAL_PAYLOAD = {
    "topic": "IELTS",
    "current_level": "Beginner",
    "target": "Band 7.0",
    "deadline_months": 3,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "evening",
    "max_session_minutes": 60,
}


# --- Monkeypatch LLM (chat + plan) ---
async def fake_json(prompt, system=None, schema=None, **kwargs):
    data = {
        "message": "Week 3 feels hard because it introduces full writing tasks. Keep sessions short and review.",
        "actions": [
            {"type": "modify_plan", "label": "Extend deadline", "payload": {"option": "extend"}},
            {"type": "view_resource", "label": "See a resource", "payload": {"resource_id": RESOURCE_ID}},
        ],
    }
    return LLMResponse(content=json.dumps(data), usage=TokenUsage(), model="fake", latency_ms=1.0, data=data)


async def fake_plan(request, extra_notes=None, *, reasoning_effort=None):
    return plan_service._LLMPlanOutput(
        goal_summary="Adapted IELTS plan",
        total_weeks=12,
        milestones=[{"month": 1, "focus": "f", "target": "t", "checkpoint": "c"}],
        weekly_schedule=[{"week": 1, "theme": "t", "days": [
            {"day": "Monday", "date_offset": 0, "time": "19:00", "topic": "x", "duration_minutes": 60, "activities": [], "resources": []}
        ]}],
        resources=[],
    )


llm.chat_completion_json = fake_json  # type: ignore[assignment]
plan_service.generate_plan_output = fake_plan  # type: ignore[assignment]


def parse_sse(text: str) -> list[dict]:
    frames = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            payload = line[6:]
            if payload == "[DONE]":
                break
            frames.append(json.loads(payload))
    return frames


def main() -> None:
    check("ada resource ter-seed untuk action", RESOURCE_ID is not None)

    email = f"chat+{uuid.uuid4().hex[:8]}@example.com"
    token = client.post("/api/auth/signup", json={"email": email, "password": "supersecret123", "name": "Chat Tester"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=auth).json()["id"]
    goal = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth).json()
    goal_id = goal["id"]

    with SessionLocal() as db:
        plan = StudyPlan(goal_id=uuid.UUID(goal_id), user_id=uuid.UUID(user_id), plan_data={"goal_summary": "x", "total_weeks": 12, "milestones": [], "weekly_schedule": [], "resources": []}, status="active", version=1, reason="initial")
        db.add(plan)
        db.commit()
        db.refresh(plan)
        plan_id = str(plan.id)

    # History kosong
    h0 = client.get(f"/api/goals/{goal_id}/chat", headers=auth)
    check("GET history awal -> 200 & kosong", h0.status_code == 200 and h0.json()["messages"] == [])

    # Kirim pesan (SSE)
    r = client.post(f"/api/goals/{goal_id}/chat", json={"message": "Why is Week 3 hard?"}, headers=auth)
    check("POST chat -> 200", r.status_code == 200, f"status={r.status_code}")
    check("content-type text/event-stream", "text/event-stream" in r.headers.get("content-type", ""))
    frames = parse_sse(r.text)
    deltas = [f for f in frames if f.get("type") == "delta"]
    final = [f for f in frames if f.get("type") == "message"]
    check("ada delta frames", len(deltas) > 0, f"n={len(deltas)}")
    check("ada frame message final", len(final) == 1)
    if final:
        check("message punya content", bool(final[0]["message"]["content"]))
        check("message punya 2 actions", len(final[0]["message"]["actions"]) == 2)
        print("  assistant:", final[0]["message"]["content"][:80])
        print("  actions:", [a["label"] for a in final[0]["message"]["actions"]])

    # History bertambah
    h1 = client.get(f"/api/goals/{goal_id}/chat", headers=auth).json()["messages"]
    check("history berisi 2 pesan", len(h1) == 2, f"n={len(h1)}")
    check("urutan user lalu assistant", h1[0]["role"] == "user" and h1[1]["role"] == "assistant")

    # Pesan bahasa Mandarin diterima
    r_cn = client.post(f"/api/goals/{goal_id}/chat", json={"message": "请解释我的计划"}, headers=auth)
    check("POST chat (Chinese) -> 200", r_cn.status_code == 200)
    check("history bertambah jadi 4", len(client.get(f"/api/goals/{goal_id}/chat", headers=auth).json()["messages"]) == 4)

    # Action: view_resource
    ra = client.post(f"/api/goals/{goal_id}/chat/action", json={"action_type": "view_resource", "payload": {"resource_id": RESOURCE_ID}}, headers=auth)
    check("action view_resource -> 200", ra.status_code == 200, f"status={ra.status_code}")
    check("view_resource mengembalikan nama", ra.json().get("data", {}).get("name") == RESOURCE_NAME)

    # Action: modify_plan (rebalance) -> plan versi baru
    rm = client.post(f"/api/goals/{goal_id}/chat/action", json={"action_type": "modify_plan", "payload": {"option": "rebalance"}}, headers=auth)
    check("action modify_plan -> 200", rm.status_code == 200, f"status={rm.status_code}")
    check("modify_plan menghasilkan v2", rm.json().get("data", {}).get("version") == 2)
    with SessionLocal() as db:
        old = db.get(StudyPlan, uuid.UUID(plan_id))
        check("plan lama superseded", old.status == "superseded", f"status={old.status}")

    # Action tidak dikenal -> 400
    check("action tidak dikenal -> 400", client.post(f"/api/goals/{goal_id}/chat/action", json={"action_type": "nope", "payload": {}}, headers=auth).status_code == 400)

    # Clear
    check("DELETE chat -> 204", client.delete(f"/api/goals/{goal_id}/chat", headers=auth).status_code == 204)
    check("history kosong setelah clear", client.get(f"/api/goals/{goal_id}/chat", headers=auth).json()["messages"] == [])

    # Ownership & auth
    check("chat tanpa token -> 401", client.get(f"/api/goals/{goal_id}/chat").status_code == 401)
    other = client.post("/api/auth/signup", json={"email": f"o+{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123"}).json()["access_token"]
    check("chat goal user lain -> 404", client.get(f"/api/goals/{goal_id}/chat", headers={"Authorization": f"Bearer {other}"}).status_code == 404)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
