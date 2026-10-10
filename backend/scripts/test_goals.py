# Script manual untuk menguji F-01 Goals (CRUD + ownership).
# Jalankan dari folder backend/: python scripts/test_goals.py

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


def register(name: str) -> str:
    email = f"goals+{uuid.uuid4().hex[:8]}@example.com"
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
    "unavailable_days": ["sunday"],
}


def main() -> None:
    token_a = register("User A")
    token_b = register("User B")

    # Create goal sebagai User A
    r = client.post("/api/goals", json=GOAL_PAYLOAD, headers=auth(token_a))
    check("A create goal -> 201", r.status_code == 201, f"status={r.status_code}")
    goal = r.json() if r.status_code == 201 else {}
    goal_id = goal.get("id")
    check("A create goal punya status default 'active'", goal.get("status") == "active")
    check("A create goal menyimpan unavailable_days", goal.get("unavailable_days") == ["sunday"])

    # List goal User A
    r = client.get("/api/goals", headers=auth(token_a))
    check("A list goals -> 200", r.status_code == 200)
    check("A list berisi goal yang dibuat", any(g["id"] == goal_id for g in r.json()))

    # Get goal User A
    r = client.get(f"/api/goals/{goal_id}", headers=auth(token_a))
    check("A get goal -> 200", r.status_code == 200)
    check("A get goal topic sesuai", r.json().get("topic") == "Python programming")

    # Update goal User A
    r = client.patch(f"/api/goals/{goal_id}", json={"target": "Build 3 small projects", "status": "archived"}, headers=auth(token_a))
    check("A patch goal -> 200", r.status_code == 200)
    check("A patch target berubah", r.json().get("target") == "Build 3 small projects")
    check("A patch status berubah", r.json().get("status") == "archived")

    # User B tidak boleh akses goal User A -> 404 (bukan 403)
    r = client.get(f"/api/goals/{goal_id}", headers=auth(token_b))
    check("B get goal A -> 404", r.status_code == 404, f"status={r.status_code}")
    r = client.patch(f"/api/goals/{goal_id}", json={"topic": "hacked"}, headers=auth(token_b))
    check("B patch goal A -> 404", r.status_code == 404, f"status={r.status_code}")
    r = client.delete(f"/api/goals/{goal_id}", headers=auth(token_b))
    check("B delete goal A -> 404", r.status_code == 404, f"status={r.status_code}")

    # List goal User B tidak berisi goal A
    r = client.get("/api/goals", headers=auth(token_b))
    check("B list tidak berisi goal A", all(g["id"] != goal_id for g in r.json()))

    # Tanpa auth -> 401
    r = client.get("/api/goals")
    check("list goals tanpa token -> 401", r.status_code == 401, f"status={r.status_code}")

    # Delete goal User A -> 204
    r = client.delete(f"/api/goals/{goal_id}", headers=auth(token_a))
    check("A delete goal -> 204", r.status_code == 204, f"status={r.status_code}")
    r = client.get(f"/api/goals/{goal_id}", headers=auth(token_a))
    check("A get goal setelah delete -> 404", r.status_code == 404, f"status={r.status_code}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [name for name, ok, _ in results if not ok]
    print(f"\nSUMMARY: {passed} passed, {len(failed)} failed, {len(results)} total")
    for name in failed:
        print(f"  - FAILED: {name}")


if __name__ == "__main__":
    main()
