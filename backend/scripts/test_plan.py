# Script manual untuk menguji F-03 Study Plan Generator (dengan auth + goals).
# Jalankan dari folder backend/: python scripts/test_plan.py

import json
import logging
import sys
import uuid
from pathlib import Path

# Tambahkan root backend ke sys.path agar `app` bisa di-import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

logging.basicConfig(level=logging.WARNING)

client = TestClient(app)

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def parse_plan_sse(text: str) -> dict | None:
    # Ambil frame {"type":"plan"} dari SSE response.
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
        if event.get("type") == "plan":
            return event["plan"]
    return None


def register(name: str) -> str:
    email = f"plan+{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/signup", json={"email": email, "password": "supersecret123", "name": name})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


GOAL_PAYLOAD = {
    "topic": "Python programming",
    "current_level": "No programming experience",
    "target": "Comfortable writing basic scripts",
    "deadline_months": 2,
    "work_hours_start": "09:00",
    "work_hours_end": "18:00",
    "work_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "preferred_study_time": "morning",
    "max_session_minutes": 60,
    "unavailable_days": [],
}


def create_goal(token: str) -> str:
    r = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def main() -> None:
    # Setup: user A + goal + feasibility.
    token_a = register("Plan User A")
    goal_id = create_goal(token_a)

    r = client.post("/api/feasibility/check", json=GOAL_PAYLOAD)
    check("feasibility check -> 200", r.status_code == 200, f"status={r.status_code}")
    feasibility_result = r.json()

    # Test 1 — generate plan dari goal_id (auth).
    plan_id = None
    try:
        r = client.post(
            "/api/plans/generate",
            json={"goal_id": goal_id, "feasibility_result": feasibility_result},
            headers=auth(token_a),
        )
        check("POST /plans/generate -> 200", r.status_code == 200, f"status={r.status_code}")
        check("content-type text/event-stream", "text/event-stream" in r.headers.get("content-type", ""))
        plan = parse_plan_sse(r.text) if r.status_code == 200 else None
        check("stream mengirim frame plan final", plan is not None)
        if plan:
            plan_id = plan["plan_id"]
            print("  plan_id:", plan_id)
            print("  goal_summary:", plan["goal_summary"][:200])
            print("  total_weeks:", plan["total_weeks"])
            print("  milestones:", len(plan["milestones"]))
            print("  weeks scheduled:", len(plan["weekly_schedule"]))
            print("  resources:", len(plan["resources"]))
            check("plan punya milestones", len(plan["milestones"]) >= 1)
            check("plan punya weekly_schedule", len(plan["weekly_schedule"]) >= 1)
    except Exception as exc:  # noqa: BLE001
        check("POST /plans/generate tanpa exception", False, str(exc))

    # Test 2 — fetch plan via GET.
    try:
        r = client.get(f"/api/plans/{plan_id}", headers=auth(token_a))
        check("GET /plans/{id} -> 200", r.status_code == 200, f"status={r.status_code}")
    except Exception as exc:  # noqa: BLE001
        check("GET plan tanpa exception", False, str(exc))

    # Test 3 — user A coba generate dengan goal milik user B -> 404.
    try:
        token_b = register("Plan User B")
        goal_b = create_goal(token_b)
        r = client.post(
            "/api/plans/generate",
            json={"goal_id": goal_b, "feasibility_result": feasibility_result},
            headers=auth(token_a),
        )
        check("generate plan dengan goal user lain -> 404", r.status_code == 404, f"status={r.status_code}")
    except Exception as exc:  # noqa: BLE001
        check("ownership check tanpa exception", False, str(exc))

    # Test 4 — generate plan tanpa auth -> 401.
    try:
        r = client.post("/api/plans/generate", json={"goal_id": goal_id})
        check("generate plan tanpa token -> 401", r.status_code == 401, f"status={r.status_code}")
    except Exception as exc:  # noqa: BLE001
        check("auth check tanpa exception", False, str(exc))

    # Test 5 — streaming SSE (auth).
    try:
        with client.stream(
            "POST",
            "/api/plans/generate/stream",
            json={"goal_id": goal_id, "feasibility_result": feasibility_result},
            headers=auth(token_a),
        ) as resp:
            check("POST /generate/stream -> 200", resp.status_code == 200, f"status={resp.status_code}")
            check("content-type text/event-stream", "text/event-stream" in resp.headers.get("content-type", ""))
            frames = 0
            last = ""
            for line in resp.iter_lines():
                if line:
                    frames += 1
                    last = line
            check("stream melihat [DONE]", last == "data: [DONE]", f"last={last!r}")
            print("  stream frames:", frames)
    except Exception as exc:  # noqa: BLE001
        check("stream tanpa exception", False, str(exc))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
